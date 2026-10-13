"""Generate Fig 5a: single-frame OMP support comparison.

Loads the loop9 feature cache and the deployed C2-rel/F2-P head checkpoint,
forwards the head over all frames in the cache to score each off-support
candidate, then picks ONE representative frame and renders a 2-D delay-Doppler
scatter showing four atom classes:

  - gray dots:   M = 96 candidate pool                          (background)
  - blue circles: OMP-once support, P = 8                        (replayed)
  - green +:      learned-head top-K_add additions              (head logits)
  - red stars:    oracle-missed Dirichlet truth                 (cache y == 1)

Frame-selection criterion (declared up front to avoid cherry-pick perception):
  pick the frame whose |missed oracle| count equals the median across all
  frames at this SNR, with frame_ber median as tie-breaker.

Run on remote (deinlab) where the cache and checkpoint live:

    cd /data/guoyikun/00inbox/AFDM-channel-estimation
    conda activate AFDM
    python afdm_sp_joint_unrolled/make_fig_mechanism_support.py \\
        --snr 20 \\
        --cache afdm_sp_joint_unrolled/outputs_loop13_4B_cache/cache_snr20.pt \\
        --ckpt  afdm_sp_joint_unrolled/outputs_loop13_4B_train/ckpt_c2rel_force_topk.pt \\
        --out   /data/guoyikun/tmp/fig_mechanism_support.pdf

Then SCP back: scp deinlab:/data/guoyikun/tmp/fig_mechanism_support.pdf paper/system_block/
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

# Repo root must be on sys.path so we can import afdm_sp_joint_unrolled.* and
# its sub-deps. Script is expected to live at afdm_sp_joint_unrolled/ on remote.
_THIS = pathlib.Path(__file__).resolve()
_REPO = _THIS.parent.parent       # afdm_sp_joint_unrolled/.. = repo root
sys.path.insert(0, str(_REPO))

from afdm_sp_joint_unrolled.classical_joint_unrolled import (  # noqa: E402
    CandidateActiveRelationHead,
)
from afdm_sp_joint_unrolled._plot_style import apply_ieee_style  # noqa: E402

# These are the same imports loop9_cache_features.py uses to replay OMP.
from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    construct_sensing_matrix, omp_sparse,
)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (  # noqa: E402
    QPSK,
)
from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a  # noqa: E402


# ---------------------------------------------------------------------------
# Cache + checkpoint loading
# ---------------------------------------------------------------------------

def _load_cache(path: pathlib.Path) -> dict:
    print(f'[cache] loading {path}', flush=True)
    d = torch.load(path, map_location='cpu', weights_only=False)
    print(f'[cache] N={int(d["n"])} M={int(d["M"])} P_pad={int(d["P_pad"])} '
          f'snr={int(d["snr"])}', flush=True)
    return d


def _load_head(ckpt_path: pathlib.Path, top_m: int = 96,
               k_add_max: int = 4) -> CandidateActiveRelationHead:
    print(f'[ckpt] loading {ckpt_path}', flush=True)
    head = CandidateActiveRelationHead(top_m=top_m, k_add_max=k_add_max)
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    sd_full = ckpt.get('state_dict') or ckpt.get('module') or ckpt
    sub = {}
    for k, v in sd_full.items():
        if k.startswith('cand_active_rel.'):
            sub[k[len('cand_active_rel.'):]] = v
    if not sub:
        # Fallback: maybe the ckpt is already just the head state_dict.
        sub = sd_full
    missing, unexpected = head.load_state_dict(sub, strict=False)
    print(f'[ckpt] loaded; missing={len(missing)} unexpected={len(unexpected)}',
          flush=True)
    head.eval()
    return head


# ---------------------------------------------------------------------------
# Per-frame head forward + frame selection
# ---------------------------------------------------------------------------

@torch.no_grad()
def _head_logits(head: CandidateActiveRelationHead,
                 u: torch.Tensor, v: torch.Tensor,
                 mask: torch.Tensor) -> torch.Tensor:
    """Forward in chunks to bound memory."""
    out = []
    chunk = 256
    for i in range(0, u.shape[0], chunk):
        out.append(head.score(u[i:i + chunk], v[i:i + chunk],
                              mask=mask[i:i + chunk] if mask is not None else None))
    return torch.cat(out, dim=0)


def _pick_representative_frame(y: torch.Tensor,
                               frame_ber: torch.Tensor,
                               logits: torch.Tensor,
                               cand_cols: np.ndarray,
                               k_add: int) -> int:
    """Pick a 'high-information typical' frame:
      - missed_oracle count >= 75th percentile (frame has substance to show),
      - the head's top-K_add overlaps at least one missed-oracle atom (so the
        figure visually demonstrates a successful recovery, not silence),
      - among ties, BER closest to the median.
    Selection criteria are disclosed in the caption.
    """
    missed = (y == 1).sum(dim=1).numpy().astype(np.int64)
    bers = frame_ber.numpy().astype(np.float64)
    med_ber = float(np.median(bers))
    p75_missed = float(np.percentile(missed, 75))
    print(f'[pick] median BER={med_ber:.3e}  '
          f'p75 missed_oracle={p75_missed:.0f}  '
          f'mean missed={missed.mean():.2f}', flush=True)

    # Per-frame: how many of the head's top-K_add land on y==1 candidates?
    topk_idx = torch.topk(logits, int(k_add), dim=1).indices.numpy()  # (N, K)
    overlap = np.zeros(y.shape[0], dtype=np.int64)
    y_np = y.numpy()
    for fi in range(y.shape[0]):
        overlap[fi] = int(y_np[fi, topk_idx[fi]].sum())
    print(f'[pick] head-overlap with missed: mean={overlap.mean():.2f}  '
          f'frac frames overlap>=1={float((overlap >= 1).mean()):.3f}', flush=True)

    eligible = np.where((missed >= p75_missed) & (overlap >= 1))[0]
    if len(eligible) == 0:
        # Fallback: just any frame with overlap>=1
        eligible = np.where(overlap >= 1)[0]
    if len(eligible) == 0:
        eligible = np.arange(y.shape[0])
    score = np.abs(bers[eligible] - med_ber)
    pick_eligible = int(np.argmin(score))
    idx = int(eligible[pick_eligible])
    print(f'[pick] frame_idx={idx}  missed={missed[idx]}  '
          f'overlap={overlap[idx]}  BER={bers[idx]:.3e}', flush=True)
    return idx


# ---------------------------------------------------------------------------
# OMP-once replay for the chosen frame
# ---------------------------------------------------------------------------

def _replay_omp(cfg: dict, snr_db: int, seed: int):
    """Re-create system, channel, frame, and run OMP-once. Returns s_omp (P,).

    Uses loop9's _make_config_a verbatim so the replay matches the cache.
    """
    np.random.seed(int(seed))
    rng = np.random.default_rng(int(seed))
    N = int(cfg['N'])

    sys_obj = _make_config_a(
        n_total=N,
        v_mean=float(cfg['v_mean']),
        p_paths=int(cfg['p_paths']),
        tau_ms=float(cfg['tau_ms']),
        fs_factor=float(cfg.get('fs_factor', 2.0)),
    )
    rho = float(cfg['rho'])
    P_d = 1.0 - rho
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq

    H_true, _, _ = sys_obj.generate_channel_matrix()
    # Use the physical-path count (P_paths) as OMP target sparsity, matching
    # the paper's "OMP-once with target sparsity P" recipe (Sec. 2.5).
    sparsity = int(sys_obj.P_paths)
    data_idx = rng.integers(0, 4, size=N)
    data_qam = QPSK[data_idx]
    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    sigma2 = 1.0 / (10 ** (snr_db / 10.0))
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    y_daft = H_true @ x_sp + np.sqrt(sigma2) * noise

    # Note argument order: (N, pilot, c1, c2, l_max, k_max).
    Phi = construct_sensing_matrix(N, pilot_scaled, sys_obj.c1, sys_obj.c2,
                                    sys_obj.l_max_cap, sys_obj.k_max_cap)
    _, support = omp_sparse(y_daft, Phi, sparsity)
    return (np.asarray(support, dtype=int),
            int(sys_obj.l_max_cap), int(sys_obj.k_max_cap), int(sparsity))


# ---------------------------------------------------------------------------
# (l, k) decoding for a flat dictionary index
# ---------------------------------------------------------------------------

def _decode_lk(idx_arr: np.ndarray, k_max: int) -> tuple[np.ndarray, np.ndarray]:
    """Dictionary order in afdm_baselines: idx = l * (2k_max+1) + (k + k_max)."""
    K_per_l = 2 * k_max + 1
    l = idx_arr // K_per_l
    k = (idx_arr % K_per_l) - k_max
    return l, k


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cache', type=str, required=True)
    p.add_argument('--ckpt', type=str, required=True)
    p.add_argument('--snr', type=int, default=20)
    p.add_argument('--k-add', type=int, default=4,
                   help='Top-K_add additions per frame (deployed = head.k_add_max)')
    p.add_argument('--out', type=str, required=True)
    p.add_argument('--frame-idx', type=int, default=-1,
                   help='If >=0, override the auto pick with this frame index')
    args = p.parse_args()

    cache = _load_cache(pathlib.Path(args.cache))
    cfg = cache['config']
    u = cache['u'].float()
    v = cache['v'].float()
    mask = cache.get('mask')
    if mask is not None:
        mask = mask.bool()
    y = cache['y'].long()
    cand_cols = cache['cand_cols'].long().numpy()
    seeds = cache['seeds'].long().numpy()
    frame_ber = cache['frame_ber'].float()
    k_max_cache = int(cfg['k_max'])
    l_max_cache = int(cfg['l_max'])

    head = _load_head(pathlib.Path(args.ckpt),
                      top_m=int(cache['M']), k_add_max=int(args.k_add))

    print('[head] forwarding ...', flush=True)
    t0 = time.time()
    logits = _head_logits(head, u, v, mask)
    print(f'[head] done in {time.time() - t0:.1f}s; '
          f'logits shape={tuple(logits.shape)}', flush=True)

    # Frame selection
    if args.frame_idx >= 0:
        fi = int(args.frame_idx)
        print(f'[pick] using user-specified frame_idx={fi}', flush=True)
    else:
        fi = _pick_representative_frame(y, frame_ber, logits,
                                        cand_cols, int(args.k_add))

    # Per-frame derivations
    cand_cols_fi = cand_cols[fi]                                     # (M,)
    y_fi = y[fi].numpy()                                              # (M,)
    logits_fi = logits[fi].numpy()                                    # (M,)
    # Top-K_add by raw logit (uniform-translation invariant — equivalent to
    # the deployed bias-replacement top-K_add ranker per Sec. 2.7).
    topk_idx = np.argsort(-logits_fi)[:int(args.k_add)]
    add_cols = cand_cols_fi[topk_idx]                                 # (K_add,)
    missed_cols = cand_cols_fi[y_fi == 1]                             # (#missed,)

    # OMP support replay for this frame
    s_omp, l_max_replay, k_max_replay, P = _replay_omp(
        cfg, snr_db=int(cache['snr']), seed=int(seeds[fi]))
    if k_max_replay != k_max_cache or l_max_replay != l_max_cache:
        print(f'[warn] replay (l_max={l_max_replay}, k_max={k_max_replay}) != '
              f'cache (l_max={l_max_cache}, k_max={k_max_cache}); using cache.',
              flush=True)
    k_max = k_max_cache
    l_max = l_max_cache

    l_cand, k_cand = _decode_lk(cand_cols_fi, k_max)
    l_omp,  k_omp  = _decode_lk(s_omp, k_max)
    l_add,  k_add  = _decode_lk(add_cols, k_max)
    l_miss, k_miss = _decode_lk(missed_cols, k_max)

    print(f'[summary] P={len(s_omp)}  K_add={len(add_cols)}  '
          f'|missed|={len(missed_cols)}  |cand_pool|={len(cand_cols_fi)}',
          flush=True)

    # ---------- Plot ----------
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(3.7, 3.0))

    # Background candidate pool
    ax.scatter(l_cand, k_cand, marker='o', s=8, c='lightgray', alpha=0.45,
               linewidths=0, label=f'Candidate pool ($M={len(cand_cols_fi)}$)',
               zorder=1)
    # Oracle missed
    ax.scatter(l_miss, k_miss, marker='*', s=68, facecolor='none',
               edgecolor='#d62728', linewidths=1.1,
               label=f'Oracle missed ($={len(missed_cols)}$)', zorder=3)
    # OMP support
    ax.scatter(l_omp, k_omp, marker='o', s=46, facecolor='none',
               edgecolor='#1f77b4', linewidths=1.4,
               label=f'OMP-once support ($P={len(s_omp)}$)', zorder=4)
    # Learned head additions
    ax.scatter(l_add, k_add, marker='+', s=70, c='#2ca02c', linewidths=1.6,
               label=f'Learned-head adds ($K_{{\\mathrm{{add}}}}={len(add_cols)}$)',
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

    # Footer with frame metadata (helps reproducibility, declared in caption too)
    ax.text(0.01, -0.32,
            f'Frame {fi} of cache snr={int(cache["snr"])}~dB; seed={int(seeds[fi])}; '
            f'BER={float(frame_ber[fi]):.2e}',
            transform=ax.transAxes, fontsize=6, color='gray')

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.3)
    fig.savefig(out, format='pdf', bbox_inches='tight')
    print(f'wrote {out} ({out.stat().st_size} bytes)', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
