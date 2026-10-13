"""Generate the single-frame OMP support figure with paper-canonical parameters.

Differs from make_fig_mechanism_support.py in two ways: it does NOT use the
loop9 cache (which was harvested with M=48, P_paths=10); instead it replays
new frames online with the paper-canonical configuration

    Ppath = 8     (Section 3 Table 2)
    M     = 96    (Section 2.6 line 182, deployed top-M)
    Kadd  = 4     (head.k_add_max default; see Section 2.7)

so the figure axes / legend are exactly consistent with the paper.

Loops over a fixed candidate-seed range, scores every frame with the deployed
checkpoint, and picks the representative frame by the disclosed rule
(above-median oracle-missed count, head additions overlap with at least one
oracle-missed atom, BER closest to the median).

Run remotely (deinlab) where the deployed checkpoint lives:

    python afdm_sp_joint_unrolled/make_fig_singleframe_canonical.py \\
        --snr 20 \\
        --ckpt afdm_sp_joint_unrolled/outputs_loop13_4B_train/ckpt_c2rel_force_topk.pt \\
        --out /data/guoyikun/tmp/fig_singleframe_canonical.pdf
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch

_THIS = pathlib.Path(__file__).resolve()
_REPO = _THIS.parent.parent  # afdm_sp_joint_unrolled/.. = repo root
sys.path.insert(0, str(_REPO))

from afdm_sp_joint_unrolled.classical_joint_unrolled import (  # noqa: E402
    CandidateActiveRelationHead,
)
from afdm_sp_joint_unrolled._plot_style import apply_ieee_style  # noqa: E402
from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    construct_sensing_matrix, omp_sparse, joint_omp_mp_iterative,
)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (  # noqa: E402
    _bits_of_symbol, QPSK,
)
from afdm_sp_joint_unrolled.loop9_cache_features import (  # noqa: E402
    _make_config_a, _build_features_np, _oracle_dictionary_support, _pad_v_to,
)


# ---------------------------------------------------------------------------
# Per-frame replay with canonical (M, P) parameters
# ---------------------------------------------------------------------------

def _replay_one_frame(sys_obj, n_total, sigma2, Phi, col_norms,
                      K_per_l, M, p_pad, seed, compute_ber=True):
    """Replays one frame with the given seed; returns the dict of cached
    features PLUS the OMP support indices for this frame."""
    rng = np.random.default_rng(int(seed))
    np.random.seed(int(seed))
    H_true, _, channel_params = sys_obj.generate_channel_matrix()
    sparsity = int(sys_obj.P_paths)  # canonical: P_paths (= 8 in paper)
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    data_idx = rng.integers(0, 4, size=n_total)
    data_qam = QPSK[data_idx]
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    y_clean = H_true @ x_sp
    noise = (rng.standard_normal(n_total)
             + 1j * rng.standard_normal(n_total)) / np.sqrt(2.0)
    y_daft = y_clean + np.sqrt(sigma2) * noise

    _, support = omp_sparse(y_daft, Phi, sparsity)
    s_omp = np.array(support, dtype=int)
    Phi_S = Phi[:, s_omp]
    g_ls, *_ = np.linalg.lstsq(Phi_S, y_daft, rcond=None)

    # Use the FULL Dirichlet-expanded virtual-tap oracle (no top-K cap), to
    # match the paper's "S_oracle effective size p_real ~ 28" narrative
    # (Sec. 3.4, App. C). _oracle_dictionary_support's `top_count` argument
    # caps the oracle by aggregated gain; we set it large enough to keep all
    # virtual taps with |k| <= k_max.
    s_oracle = _oracle_dictionary_support(
        channel_params, sys_obj.k_max_cap, K_per_l, top_count=10**9,
    )
    missed = set(int(x) for x in s_oracle) - set(int(x) for x in s_omp)

    frame_ber = 0.0
    if compute_ber:
        const_data = np.sqrt(P_d) * QPSK
        try:
            x_hat, _ = joint_omp_mp_iterative(
                y_daft, pilot_scaled, n_total, sys_obj.c1, sys_obj.c2,
                sys_obj.l_max_cap, sys_obj.k_max_cap,
                sigma2, const_data, n_paths=sparsity, n_outer_iter=5,
                rho=rho, pic_iter=20, pic_damp=0.5, mp_mode='bp',
                gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
                tau_h_factor=0.01, tau_h_sigma_factor=0.1,
                threshold_mp=1e-4, k_leak=2, update_sigma2=True,
                phase_convention='python', eps_stop_rel=-1.0,
            )
            x_norm = x_hat / np.sqrt(P_d)
            bits_pred = _bits_of_symbol(x_norm, n_total)
            bits_true = np.zeros(2 * n_total, dtype=np.float32)
            bits_true[:n_total] = (data_qam.real < 0).astype(np.float32)
            bits_true[n_total:] = (data_qam.imag < 0).astype(np.float32)
            frame_ber = float(np.mean(bits_pred != bits_true))
        except Exception:
            frame_ber = 0.0

    u, v_raw, cand_cols = _build_features_np(
        Phi, col_norms, y_daft, s_omp, g_ls, sigma2,
        sys_obj.l_max_cap, sys_obj.k_max_cap, K_per_l, M,
    )
    if u is None:
        return None
    y_lbl = np.array([1 if int(c) in missed else 0 for c in cand_cols],
                      dtype=np.int64)
    v_pad, mask = _pad_v_to(v_raw, p_pad)
    return dict(u=u, v=v_pad, mask=mask, y=y_lbl, cand_cols=cand_cols,
                s_omp=s_omp, frame_ber=frame_ber, seed=int(seed))


# ---------------------------------------------------------------------------
# Head loading + scoring
# ---------------------------------------------------------------------------

def _load_head(ckpt_path: pathlib.Path, top_m: int = 96,
                k_add_max: int = 4) -> CandidateActiveRelationHead:
    head = CandidateActiveRelationHead(top_m=top_m, k_add_max=k_add_max)
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    sd_full = ckpt.get('state_dict') or ckpt.get('module') or ckpt
    sub = {k[len('cand_active_rel.'):]: v for k, v in sd_full.items()
            if k.startswith('cand_active_rel.')}
    if not sub:
        sub = sd_full
    head.load_state_dict(sub, strict=False)
    head.eval()
    return head


@torch.no_grad()
def _score(head, u_np, v_np, mask_np):
    u_t = torch.from_numpy(u_np).float().unsqueeze(0)
    v_t = torch.from_numpy(v_np).float().unsqueeze(0)
    mask_t = torch.from_numpy(mask_np).bool().unsqueeze(0)
    return head.score(u_t, v_t, mask=mask_t).squeeze(0).numpy()


# ---------------------------------------------------------------------------
# Decoding and plotting
# ---------------------------------------------------------------------------

def _decode_lk(idx_arr, k_max):
    K_per_l = 2 * k_max + 1
    l = idx_arr // K_per_l
    k = (idx_arr % K_per_l) - k_max
    return l, k


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ckpt', required=True)
    p.add_argument('--snr', type=int, default=20)
    p.add_argument('--p-paths', type=int, default=8,
                    help='Canonical P (paper Sec. 3 Table 2).')
    p.add_argument('--m', type=int, default=96,
                    help='Canonical top-M (paper Sec. 2.6).')
    p.add_argument('--k-add', type=int, default=4,
                    help='Top-Kadd ranker budget.')
    p.add_argument('--p-pad', type=int, default=64)
    p.add_argument('--n-total', type=int, default=1024)
    p.add_argument('--v-mean', type=float, default=2.0)
    p.add_argument('--tau-ms', type=float, default=10.0)
    p.add_argument('--fs-factor', type=float, default=4.0)
    p.add_argument('--n-seeds', type=int, default=300,
                    help='Number of candidate seeds to scan.')
    p.add_argument('--master-seed', type=int, default=20260423)
    p.add_argument('--out', required=True)
    args = p.parse_args()

    print(f'[setup] P={args.p_paths} M={args.m} Kadd={args.k_add} '
          f'fs_factor={args.fs_factor} SNR={args.snr} dB', flush=True)

    sys_obj = _make_config_a(
        n_total=args.n_total, v_mean=args.v_mean, p_paths=args.p_paths,
        tau_ms=args.tau_ms, fs_factor=args.fs_factor,
    )
    sigma2 = 1.0 / (10 ** (args.snr / 10.0))
    pilot_scaled = np.sqrt(float(sys_obj.rho)) * sys_obj._zc_seq
    Phi = construct_sensing_matrix(args.n_total, pilot_scaled,
                                    sys_obj.c1, sys_obj.c2,
                                    sys_obj.l_max_cap, sys_obj.k_max_cap)
    col_norms = np.linalg.norm(Phi, axis=0)
    K_per_l = 2 * sys_obj.k_max_cap + 1
    print(f'[setup] l_max={sys_obj.l_max_cap}  k_max={sys_obj.k_max_cap}  '
          f'Q={Phi.shape[1]}  K_per_l={K_per_l}', flush=True)

    head = _load_head(pathlib.Path(args.ckpt), top_m=args.m,
                      k_add_max=args.k_add)
    print('[ckpt] loaded', flush=True)

    # Scan seeds
    rng = np.random.default_rng(args.master_seed)
    seeds = rng.integers(1, 2**31, size=args.n_seeds).tolist()

    results = []
    t0 = time.time()
    for i, seed in enumerate(seeds, 1):
        info = _replay_one_frame(sys_obj, args.n_total, sigma2, Phi,
                                  col_norms, K_per_l, args.m, args.p_pad,
                                  seed, compute_ber=True)
        if info is None:
            continue
        logits = _score(head, info['u'], info['v'], info['mask'])
        topk = np.argsort(-logits)[:args.k_add]
        overlap = int(info['y'][topk].sum())
        missed = int((info['y'] == 1).sum())
        results.append(dict(seed=seed, missed=missed, overlap=overlap,
                            ber=info['frame_ber'], info=info, topk=topk))
        if i % 30 == 0:
            print(f'[scan] {i}/{args.n_seeds}  ({time.time() - t0:.0f}s)',
                  flush=True)
    print(f'[scan] done in {time.time() - t0:.0f}s; usable={len(results)}',
          flush=True)

    missed_arr = np.array([r['missed'] for r in results])
    bers = np.array([r['ber'] for r in results])
    med_missed = float(np.median(missed_arr))
    med_ber = float(np.median(bers))
    print(f'[stats] median missed={med_missed:.1f}  median BER={med_ber:.3e}'
          f'  mean overlap={np.mean([r["overlap"] for r in results]):.2f}',
          flush=True)

    # Apply selection rule
    eligible = [r for r in results
                 if r['missed'] >= med_missed and r['overlap'] >= 1]
    if not eligible:
        eligible = [r for r in results if r['overlap'] >= 1]
    if not eligible:
        eligible = results
    eligible.sort(key=lambda r: abs(r['ber'] - med_ber))
    pick = eligible[0]
    print(f'[pick] seed={pick["seed"]}  missed={pick["missed"]}  '
          f'overlap={pick["overlap"]}  BER={pick["ber"]:.3e}', flush=True)

    info = pick['info']
    cand_cols = info['cand_cols']
    s_omp = info['s_omp']
    add_cols = cand_cols[pick['topk']]
    missed_cols = cand_cols[info['y'] == 1]
    k_max = sys_obj.k_max_cap
    l_max = sys_obj.l_max_cap

    l_cand, k_cand = _decode_lk(cand_cols, k_max)
    l_omp,  k_omp  = _decode_lk(s_omp, k_max)
    l_add,  k_add_lk = _decode_lk(add_cols, k_max)
    l_miss, k_miss = _decode_lk(missed_cols, k_max)

    # Plot
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(3.7, 3.0))
    ax.scatter(l_cand, k_cand, marker='o', s=8, c='lightgray', alpha=0.45,
                linewidths=0,
                label=f'Candidate pool ($M = {len(cand_cols)}$)', zorder=1)
    ax.scatter(l_miss, k_miss, marker='*', s=68, facecolor='none',
                edgecolor='#d62728', linewidths=1.1,
                label=f'Oracle missed ($={len(missed_cols)}$)', zorder=3)
    ax.scatter(l_omp, k_omp, marker='o', s=46, facecolor='none',
                edgecolor='#1f77b4', linewidths=1.4,
                label=f'OMP-once support ($P = {len(s_omp)}$)', zorder=4)
    ax.scatter(l_add, k_add_lk, marker='+', s=70, c='#2ca02c', linewidths=1.6,
                label=f'Learned-head adds ($K_{{\\mathrm{{add}}}} = {len(add_cols)}$)',
                zorder=5)
    ax.set_xlabel(r'Delay bin $l$')
    ax.set_ylabel(r'Doppler bin $k$')
    ax.set_xlim([-2, l_max + 2])
    ax.set_ylim([-k_max - 1, k_max + 1])
    ax.set_yticks(range(-k_max, k_max + 1))
    ax.grid(True, alpha=0.3, linewidth=0.6)
    ax.legend(loc='upper right', fontsize=6.5, framealpha=0.95,
                borderpad=0.4, handlelength=1.2, handletextpad=0.4,
                labelspacing=0.25)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.3)
    fig.savefig(out, format='pdf', bbox_inches='tight')
    print(f'wrote {out} ({out.stat().st_size} bytes)', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
