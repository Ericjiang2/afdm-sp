#!/usr/bin/env python
"""Loop 9 — cache (u, v, labels, frame_ber) tensors for C2-rel training.

Per Oracle R1 recipe:
  - Cache 60k frames mixed 1:2:2 over SNR in {10, 15, 20} (default 12k/24k/24k).
  - For each frame: draw channel/data/noise with a fresh seed, run classical
    OMP+LS+BP, collect the top-M=48 off-support candidates by pre-LS pilot MF,
    compute u_j (7) and v_{j,s} (M, P=10, 6), plus binary labels y_j.
  - Also store the classical frame's BER so the trainer can weight frames 2x
    when the classical path made any bit errors (focus training on hard frames).

Output format: a single torch .pt with:
  {
    'u':           tensor (N, M, 7) float32
    'v':           tensor (N, M, P, 6) float32
    'y':           tensor (N, M) int8  (1 if candidate in missed support)
    'frame_ber':   tensor (N,) float32  (classical per-frame BER)
    'snr':         tensor (N,) int8
    'cand_cols':   tensor (N, M) int32  (debug, not used in training)
    'config': dict, 'seeds': tensor(int64)
  }
  split by SNR label. The trainer does its own train/val split.

Config A: N=1024 v=2 P=10 tau=10ms rho=0.5.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Fast BP shim (so classical path matches torch baseline)
from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch


def _fast_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4,
             damp=0.5, return_soft=False, graph_observer=None):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                               threshold=threshold, damp=damp, device=dev,
                               return_numpy=True, return_soft=return_soft, graph_observer=graph_observer)


_afb.mp_detect_bp = _fast_bp

from afdm_sp_joint_unrolled.afdm_baselines import (
    construct_sensing_matrix, joint_omp_mp_iterative, omp_sparse,
)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    _bits_of_symbol, _make_system_variable_N, QPSK,
)


def _make_config_a(n_total, v_mean, p_paths, tau_ms, fs_factor=2.0):
    sys_obj = _make_system_variable_N(n_total)
    sys_obj.P_paths = int(p_paths)
    sys_obj.gen_h_daft_convention = 'python'
    sys_obj.baseline_phase_convention = 'python'
    sys_obj.v_mean = float(v_mean)
    sys_obj.tau_spread = float(tau_ms) * 1e-3
    if abs(fs_factor - 2.0) > 1e-9:
        sys_obj.B = 4e3
        sys_obj.fs = float(fs_factor) * sys_obj.B
        sys_obj.Ts = 1.0 / sys_obj.fs
    v_max = sys_obj.v_mean + 3.0 * 0.5
    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    sys_obj.k_max_cap = max(int(np.ceil(n_total * d_norm)), 1)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
    return sys_obj


def _merged_dictionary_coefficients(channel_params, k_max, K_per_l):
    """All merged complex coefficients, including exact cancellation to zero."""
    l_exp = np.asarray(channel_params['l_exp'], dtype=int)
    k_exp = np.asarray(channel_params['k_exp'], dtype=int)
    g_exp = np.asarray(channel_params['chan_coef_exp'], dtype=complex)
    mask = np.abs(k_exp) <= k_max
    l_v = l_exp[mask]; k_v = k_exp[mask]; g_v = g_exp[mask]
    if len(l_v) == 0:
        return np.array([], dtype=int), np.array([], dtype=complex)
    cols = l_v * K_per_l + (k_v + k_max)
    uniq, inv = np.unique(cols, return_inverse=True)
    g_sum = np.zeros(len(uniq), dtype=complex)
    np.add.at(g_sum, inv, g_v)
    return uniq, g_sum


def _oracle_dictionary_support(channel_params, k_max, K_per_l, top_count,
                                 return_gains=False):
    """Legacy top-count magnitude labels from the complete complex merge."""
    uniq, g_sum = _merged_dictionary_coefficients(channel_params, k_max, K_per_l)
    order = np.argsort(np.abs(g_sum))[::-1]
    cols_top = uniq[order][:top_count].astype(int)
    if return_gains:
        gains_top = np.abs(g_sum[order][:top_count])
        return cols_top, gains_top
    return cols_top


def _build_features_np(Phi, col_norms, y_daft, s_omp, g_ls, sigma2,
                       l_max, k_max, K_per_l, M):
    """Compute per-frame (u, v, cand_cols) via NumPy. Mirrors the torch head
    feature layout exactly.

    Returns:
        u         (M, 7) float32
        v         (M, P, 6) float32
        cand_cols (M,) int
    Returns (None, None, None) if insufficient off-support candidates.
    """
    P = len(s_omp)
    Q = Phi.shape[1]
    phi_proj_y = Phi.conj().T @ y_daft                       # (Q,) complex
    phi_proj_y_abs = np.abs(phi_proj_y)
    mag = phi_proj_y_abs.copy()
    if P > 0:
        mag[s_omp] = -1.0
    topM = int(min(M, np.sum(mag > 0)))
    if topM <= 0:
        return None, None, None
    cand_idx = np.argpartition(-mag, topM - 1)[:topM]
    order = np.argsort(-mag[cand_idx])
    cand_cols = cand_idx[order].astype(int)

    # u_j (M, 7)
    l_c = cand_cols // K_per_l
    k_c = (cand_cols % K_per_l) - k_max
    log_mf = np.log(phi_proj_y_abs[cand_cols] + 1e-30)
    margin_ref = phi_proj_y_abs[s_omp[-1]] if P > 0 else 1.0
    margin = log_mf - np.log(max(margin_ref, 1e-30))

    l_s = s_omp // K_per_l
    k_s = (s_omp % K_per_l) - k_max
    dl_mat = np.abs(l_c[:, None] - l_s[None, :])
    dk_mat = np.abs(k_c[:, None] - k_s[None, :])
    d_sum = dl_mat + dk_mat
    j_nn = d_sum.argmin(axis=1)
    d_l_nn = dl_mat[np.arange(topM), j_nn]
    d_k_nn = dk_mat[np.arange(topM), j_nn]
    log_sig = np.log(max(sigma2, 1e-30))
    u = np.stack([
        log_mf.astype(np.float32),
        margin.astype(np.float32),
        l_c.astype(np.float32) / max(l_max, 1),
        k_c.astype(np.float32) / max(k_max, 1),
        d_l_nn.astype(np.float32) / max(l_max, 1),
        d_k_nn.astype(np.float32) / max(k_max, 1),
        np.full(topM, log_sig, dtype=np.float32),
    ], axis=1)

    # v (M, P, 6)
    phi_c = Phi[:, cand_cols]
    phi_s = Phi[:, s_omp]
    cn = col_norms[cand_cols].clip(min=1e-30)
    sn = col_norms[s_omp].clip(min=1e-30)
    gram = phi_c.conj().T @ phi_s
    coh = np.abs(gram) / (cn[:, None] * sn[None, :])
    alpha_coh = np.abs(g_ls)[None, :] * coh
    log_alpha_coh = np.log(alpha_coh + 1e-30)
    dl_n = dl_mat.astype(np.float32) / max(l_max, 1)
    dk_n = dk_mat.astype(np.float32) / max(k_max, 1)
    ind_dl0 = (dl_mat == 0).astype(np.float32)
    ind_dk_le2 = (dk_mat <= 2).astype(np.float32)
    v = np.stack([coh.astype(np.float32),
                   log_alpha_coh.astype(np.float32),
                   dl_n, dk_n, ind_dl0, ind_dk_le2], axis=-1)

    return u, v, cand_cols


def _harvest_frame(sys_obj, n_total, sigma2, Phi, col_norms, K_per_l, M,
                    seed, compute_frame_ber: bool = True):
    """Returns dict with u, v, y (label), cand_cols, frame_ber. Or None on failure."""
    rng = np.random.default_rng(seed)
    np.random.seed(seed)
    H_true, _, channel_params = sys_obj.generate_channel_matrix()
    sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
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

    # Classical OMP + LS (matches joint_omp_mp_iterative first iter for support)
    _, support = omp_sparse(y_daft, Phi, sparsity)
    s_omp = np.array(support, dtype=int)
    Phi_S = Phi[:, s_omp]
    g_ls, *_ = np.linalg.lstsq(Phi_S, y_daft, rcond=None)

    # Oracle support + per-atom |gain| (for soft-label supervision).
    s_oracle, g_oracle = _oracle_dictionary_support(
        channel_params, sys_obj.k_max_cap, K_per_l, sparsity, return_gains=True)
    missed = set(int(x) for x in s_oracle) - set(int(x) for x in s_omp)
    # Map column → |gain| for fast soft-label lookup
    gain_per_col = {int(s_oracle[i]): float(g_oracle[i])
                    for i in range(len(s_oracle))}

    # Classical BER for frame weighting (full joint OMP+MP+BP pipeline)
    const_data = np.sqrt(P_d) * QPSK
    frame_ber = 0.0
    if compute_frame_ber:
        try:
            x_hat, _ = joint_omp_mp_iterative(
                y_daft, pilot_scaled, n_total, sys_obj.c1, sys_obj.c2,
                sys_obj.l_max_cap, sys_obj.k_max_cap,
                sigma2, const_data, n_paths=sparsity, n_outer_iter=5,
                rho=float(sys_obj.rho), pic_iter=20, pic_damp=0.5,
                mp_mode='bp',
                gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
                tau_h_factor=0.01, tau_h_sigma_factor=0.1, threshold_mp=1e-4,
                k_leak=2, update_sigma2=True, phase_convention='python',
                eps_stop_rel=-1.0,
            )
            x_norm = x_hat / np.sqrt(P_d)
            bits_pred = _bits_of_symbol(x_norm, n_total)
            bits_true = np.zeros(2 * n_total, dtype=np.float32)
            bits_true[:n_total] = (data_qam.real < 0).astype(np.float32)
            bits_true[n_total:] = (data_qam.imag < 0).astype(np.float32)
            frame_ber = float(np.mean(bits_pred != bits_true))
        except Exception:
            frame_ber = 0.0

    # Features
    u, v, cand_cols = _build_features_np(Phi, col_norms, y_daft,
                                           s_omp, g_ls, sigma2,
                                           sys_obj.l_max_cap,
                                           sys_obj.k_max_cap, K_per_l, M)
    if u is None:
        return None
    y_lbl = np.array([1 if int(c) in missed else 0 for c in cand_cols],
                     dtype=np.int8)
    # Soft labels: per-cand soft target = |gain_oracle[c]| / max_gain_in_frame
    # for c in (oracle ∩ cand_cols missed by OMP), else 0. Range [0, 1].
    # Used by training when --use-soft-labels is set; head's BCE then puts
    # higher weight on high-|gain| missed atoms (the "truly useful" ones).
    if gain_per_col:
        max_g = max(gain_per_col.values())
    else:
        max_g = 1.0
    y_soft = np.zeros(len(cand_cols), dtype=np.float32)
    for i, c in enumerate(cand_cols):
        c_int = int(c)
        if c_int in missed:
            y_soft[i] = gain_per_col.get(c_int, 0.0) / max(max_g, 1e-30)
    return dict(u=u, v=v, y=y_lbl, y_soft=y_soft,
                cand_cols=cand_cols.astype(np.int32),
                frame_ber=frame_ber, p_real=int(v.shape[1]))


def _pad_v_to(v_raw, p_pad):
    """Pad v (M, P_real, 6) to (M, p_pad, 6). Also return mask (M, p_pad) bool."""
    M, P_real, D = v_raw.shape
    if P_real >= p_pad:
        v_out = v_raw[:, :p_pad, :]
        mask = np.ones((M, p_pad), dtype=bool)
    else:
        v_out = np.zeros((M, p_pad, D), dtype=v_raw.dtype)
        v_out[:, :P_real, :] = v_raw
        mask = np.zeros((M, p_pad), dtype=bool)
        mask[:, :P_real] = True
    return v_out, mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--p-paths', type=int, default=10)
    ap.add_argument('--tau-ms', type=float, default=10.0)
    ap.add_argument('--fs-factor', type=float, default=2.0,
                    help='Sampling rate fs=fs_factor*B. 2.0=Nyquist (default), '
                         '4.0=2x oversampling (shrinks Doppler dictionary).')
    ap.add_argument('--M', type=int, default=48)
    ap.add_argument('--p-pad', type=int, default=64,
                    help='pad v to this P dimension with zeros + mask')
    ap.add_argument('--skip-frame-ber', action='store_true',
                    help='skip full classical joint BP per frame '
                         '(faster cache; all frame_ber set to 0)')
    # Oracle R1: 60k frames, mix 1:2:2 over {10, 15, 20}
    ap.add_argument('--n-10', type=int, default=12000)
    ap.add_argument('--n-15', type=int, default=24000)
    ap.add_argument('--n-20', type=int, default=24000)
    ap.add_argument('--n-25', type=int, default=0,
                    help='Optional SNR=25 frames (Loop-13 4B add-on). '
                         'Default 0 = skip.')
    ap.add_argument('--seed-base', type=int, default=2026042201)
    ap.add_argument('--out', type=str, required=True)
    ap.add_argument('--print-every', type=int, default=200)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    sys_obj = _make_config_a(args.n_total, args.v_mean, args.p_paths,
                              args.tau_ms, fs_factor=args.fs_factor)
    print(f'[cache] CONFIG A: N={args.n_total} v={sys_obj.v_mean} '
          f'P={sys_obj.P_paths} tau={sys_obj.tau_spread*1e3:.2f}ms '
          f'rho={sys_obj.rho} l_max={sys_obj.l_max_cap} '
          f'k_max={sys_obj.k_max_cap} '
          f'fs={sys_obj.fs/1e3:.1f}kHz (fs_factor={args.fs_factor})',
          flush=True)
    print(f'[cache] cache sizes: SNR10={args.n_10} SNR15={args.n_15} '
          f'SNR20={args.n_20}  total={args.n_10+args.n_15+args.n_20}  '
          f'M={args.M}  seed_base={args.seed_base}', flush=True)

    rho = float(sys_obj.rho); P_d = 1.0 - rho
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    K_per_l = 2 * sys_obj.k_max_cap + 1
    Phi = construct_sensing_matrix(args.n_total, pilot_scaled, sys_obj.c1,
                                    sys_obj.c2, sys_obj.l_max_cap,
                                    sys_obj.k_max_cap)
    col_norms = np.linalg.norm(Phi, axis=0)

    snr_list = [(10, args.n_10), (15, args.n_15), (20, args.n_20)]
    if int(getattr(args, 'n_25', 0)) > 0:
        snr_list.append((25, int(args.n_25)))
    rng_master = np.random.default_rng(args.seed_base)
    t0 = time.time()

    for snr, n_req in snr_list:
        if int(n_req) <= 0:
            print(f'\n[snr={snr}] target=0 → skipping (leaving any existing '
                  f'cache file untouched)', flush=True)
            continue
        sigma2 = 10 ** (-snr / 10.0)
        out_file = Path(args.out) / f'cache_snr{snr}.pt'
        print(f'\n[snr={snr}] target={n_req}  out={out_file}', flush=True)
        # Pre-allocate with expected M=args.M, P=args.p_pad (variable real P
        # per frame padded to args.p_pad with zero rows + mask).
        M = int(args.M); P_pad = int(args.p_pad)
        u_buf = np.empty((n_req, M, 7), dtype=np.float32)
        v_buf = np.zeros((n_req, M, P_pad, 6), dtype=np.float32)
        mask_buf = np.zeros((n_req, M, P_pad), dtype=bool)
        y_buf = np.empty((n_req, M), dtype=np.int8)
        y_soft_buf = np.zeros((n_req, M), dtype=np.float32)
        cand_buf = np.empty((n_req, M), dtype=np.int32)
        ber_buf = np.empty(n_req, dtype=np.float32)
        seed_buf = np.empty(n_req, dtype=np.int64)
        preal_buf = np.empty(n_req, dtype=np.int32)

        kept = 0; tries = 0
        while kept < n_req and tries < n_req * 3:
            seed_fi = int(rng_master.integers(0, 2**31))
            tries += 1
            r = _harvest_frame(sys_obj, args.n_total, sigma2, Phi,
                                col_norms, K_per_l, M, seed_fi,
                                compute_frame_ber=not args.skip_frame_ber)
            if r is None:
                continue
            if r['p_real'] > P_pad:
                # Skip frames whose raw OMP support exceeds padding budget.
                continue
            v_pad, mask = _pad_v_to(r['v'], P_pad)
            u_buf[kept] = r['u']
            v_buf[kept] = v_pad
            mask_buf[kept] = mask
            y_buf[kept] = r['y']
            y_soft_buf[kept] = r.get('y_soft', np.zeros(M, dtype=np.float32))
            cand_buf[kept] = r['cand_cols']
            ber_buf[kept] = r['frame_ber']
            seed_buf[kept] = seed_fi
            preal_buf[kept] = r['p_real']
            kept += 1
            if kept % args.print_every == 0 or kept == n_req:
                pos = int(y_buf[:kept].sum())
                bad = float(np.mean(ber_buf[:kept] > 0))
                avg_p = float(np.mean(preal_buf[:kept]))
                print(f'  [snr={snr} kept={kept}/{n_req} tries={tries} '
                      f'dt={time.time()-t0:.0f}s] pos_rate='
                      f'{pos/max(kept*M,1):.4f} '
                      f'frame_bad_rate={bad:.3f} avg_p_real={avg_p:.1f}',
                      flush=True)

        if kept < n_req:
            print(f'WARN: only harvested {kept}/{n_req} at SNR={snr}', flush=True)
            u_buf = u_buf[:kept]; v_buf = v_buf[:kept]
            mask_buf = mask_buf[:kept]; y_buf = y_buf[:kept]
            y_soft_buf = y_soft_buf[:kept]
            cand_buf = cand_buf[:kept]; ber_buf = ber_buf[:kept]
            seed_buf = seed_buf[:kept]; preal_buf = preal_buf[:kept]

        torch.save(dict(
            u=torch.from_numpy(u_buf),
            v=torch.from_numpy(v_buf),
            mask=torch.from_numpy(mask_buf),
            y=torch.from_numpy(y_buf),
            y_soft=torch.from_numpy(y_soft_buf),
            cand_cols=torch.from_numpy(cand_buf),
            frame_ber=torch.from_numpy(ber_buf),
            seeds=torch.from_numpy(seed_buf),
            p_real=torch.from_numpy(preal_buf),
            snr=int(snr), n=int(kept), M=int(M), P_pad=int(P_pad),
            config=dict(
                N=args.n_total, v_mean=args.v_mean, p_paths=args.p_paths,
                tau_ms=args.tau_ms, rho=rho,
                l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
                fs_factor=args.fs_factor,
                fs_kHz=sys_obj.fs / 1e3,
            ),
        ), out_file)
        print(f'[snr={snr}] saved {out_file}  kept={kept}', flush=True)

    print('\n[cache] DONE total_time=%ds' % int(time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
