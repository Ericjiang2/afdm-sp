#!/usr/bin/env python
"""measure_runtime.py — wall-clock + peak-memory benchmark for §IV-F.

Times each enabled receiver on each problem size N, for `frames` frames per
cell, and writes `outputs_complexity/runtime_table.csv`. Channel generation
and data prep are NOT counted; only receiver invocation.

Usage:
    python measure_runtime.py \
        --N-list 512 1024 2048 \
        --frames 50 \
        --receivers classical-numpy classical-torch learned \
        --learned-ckpt afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
        --out afdm_sp_joint_unrolled/outputs_complexity

Receiver names:
    classical-numpy   joint_omp_mp_iterative from afdm_baselines (CPU NumPy)
    classical-torch   ClassicalJointUnrolled with no learned heads (torch port)
    learned           ClassicalJointUnrolled with C2-rel head loaded from --learned-ckpt
    qing              Zheng 2025 SP-AFDM receiver in its native setup (N=512,
                      alpha_max=2, l_max=1, M+1=16). Runs once regardless of
                      --N-list because Zheng's pilot scheme requires Q+1 << N.
                      §IV-F reports a single Qing row with a footnote.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import statistics
import sys
import time

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
PROJ = HERE.parent
sys.path.insert(0, str(PROJ.parent))

from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch


def _fast_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4, damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                              threshold=threshold, damp=damp, device=dev,
                              return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp

from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig,
    ClassicalJointUnrolled,
)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    QPSK,
    _make_system_variable_N,
)


def _build_system(N: int, p_paths: int, tau_spread: float, v_mean: float, fs_factor: float):
    sys_obj = _make_system_variable_N(N)
    sys_obj.P_paths = int(p_paths)
    sys_obj.tau_spread = float(tau_spread)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.v_mean = float(v_mean)
    if abs(fs_factor - 2.0) > 1e-9:
        sys_obj.B = 4e3
        sys_obj.fs = float(fs_factor) * sys_obj.B
        sys_obj.Ts = 1.0 / sys_obj.fs
    v_max = sys_obj.v_mean + 3.0 * 0.5
    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    sys_obj.k_max_cap = max(int(np.ceil(N * d_norm)), 1)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
    return sys_obj


def _build_torch_module(sys_obj, N: int, learned_heads: tuple, ckpt_path: str | None,
                        device: torch.device, dtype: torch.dtype):
    rdtype = torch.float32 if dtype == torch.complex64 else torch.float64
    cfg = ClassicalJointConfig(
        N=N, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        c1=sys_obj.c1, c2=sys_obj.c2, rho=float(sys_obj.rho),
        mp_mode='bp', pic_damp=0.5, n_paths=int(sys_obj.P_paths),
        n_outer_iter=5, pic_iter=20, update_sigma2=True,
        early_stop=False, eps_stop_rel=-1.0,
        dtype=dtype, rdtype=rdtype, device=str(device),
    )
    soft_eval = bool(learned_heads)  # learned -> soft, classical-torch -> hard
    module = ClassicalJointUnrolled(cfg, learnable_heads=learned_heads, use_soft_decisions=soft_eval)
    if ckpt_path:
        ckpt = torch.load(ckpt_path, map_location=cfg.device, weights_only=False)
        sd = ckpt.get('state_dict') or ckpt.get('module') or ckpt
        module.load_state_dict(sd)
    module = module.to(cfg.device).eval()
    return module, cfg


def _gen_frame(sys_obj, N: int, snr_db: float, rng: np.random.Generator):
    H_true, _, _ = sys_obj.generate_channel_matrix()
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    data_idx = rng.integers(0, 4, size=N)
    data_qam = QPSK[data_idx]
    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    sigma2 = 1.0 / (10 ** (snr_db / 10.0))
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    y_daft = H_true @ x_sp + np.sqrt(sigma2) * noise
    return y_daft, pilot_scaled, sigma2, np.sqrt(P_d) * QPSK


def _time_classical_numpy(sys_obj, N, snr_db, frames, seed):
    rng = np.random.default_rng(seed)
    times_ms = []
    for _ in range(frames):
        y, x_pil, sigma2, const = _gen_frame(sys_obj, N, snr_db, rng)
        t0 = time.perf_counter()
        joint_omp_mp_iterative(
            y, x_pil, N, sys_obj.c1, sys_obj.c2,
            sys_obj.l_max_cap, sys_obj.k_max_cap,
            sigma2, const,
            n_paths=int(getattr(sys_obj, '_P_actual', sys_obj.P_paths)),
            n_outer_iter=5, rho=float(sys_obj.rho),
            pic_iter=20, pic_damp=0.5, mp_mode='bp',
            gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
            tau_h_factor=0.01, tau_h_sigma_factor=0.1, threshold_mp=1e-4,
            k_leak=2, update_sigma2=True, phase_convention='python',
            eps_stop_rel=-1.0,
        )
        times_ms.append(1000.0 * (time.perf_counter() - t0))
    return times_ms, 0  # NumPy → no GPU peak


def _time_torch_module(module, cfg, sys_obj, N, snr_db, frames, seed, device: torch.device):
    rng = np.random.default_rng(seed)
    times_ms = []
    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats(device)
    rho = float(sys_obj.rho); P_d = 1.0 - rho
    const_t = torch.tensor(np.sqrt(P_d) * QPSK, dtype=cfg.dtype, device=cfg.device)
    for _ in range(frames):
        y, x_pil, sigma2, _ = _gen_frame(sys_obj, N, snr_db, rng)
        y_t = torch.tensor(y, dtype=cfg.dtype, device=cfg.device)
        x_pil_t = torch.tensor(x_pil, dtype=cfg.dtype, device=cfg.device)
        sigma2_t = torch.tensor(sigma2, dtype=cfg.rdtype, device=cfg.device)
        if device.type == 'cuda':
            torch.cuda.synchronize(device)
        t0 = time.perf_counter()
        with torch.no_grad():
            module(y_t, x_pil_t, sigma2_t, const_t)
        if device.type == 'cuda':
            torch.cuda.synchronize(device)
        times_ms.append(1000.0 * (time.perf_counter() - t0))
    peak_mb = 0
    if device.type == 'cuda':
        peak_mb = torch.cuda.max_memory_allocated(device) / (1024 * 1024)
    return times_ms, int(peak_mb)


def _time_qing_native(frames: int, seed: int):
    """Run Zheng 2025 SP-AFDM receiver in its native setup; ignore outer N.

    Native setup mirrors qing_baseline/test_qing_consistency.py: N=512,
    alpha_max=2, l_max=1, P=3, M+1=16 pilots, SNR_p=50 dB, SNR_d=21 dB,
    n_iter=2. Same channel + data generation pipeline as the consistency test
    so timing is on the production receiver path (no debug branches).
    """
    from afdm_sp_joint_unrolled.qing_baseline.qing_sp_afdm import (
        QPSK_CONST, build_theta_list, qing_pilot, qing_receiver,
    )
    from afdm_sp_joint_unrolled.qing_baseline.test_qing_consistency import (
        _build_daft,
    )
    N = 512
    alpha_max, l_max, P = 2, 1, 3
    M = 15  # M+1 = 16 pilots
    snr_d_db, snr_p_db = 21.0, 50.0
    N0 = 1.0
    Q_plus_1 = (l_max + 1) * (2 * alpha_max + 1)
    c1 = (2 * alpha_max + 1) / (2 * N)
    c2 = 1.0 / (4.0 * N)
    A, A_H = _build_daft(N, c1, c2)
    sigma_p_sq = N0 * 10 ** (snr_p_db / 10.0)
    sigma_p = np.sqrt(sigma_p_sq)
    sigma_d_sq = N0 * 10 ** (snr_d_db / 10.0)
    x_p, _ = qing_pilot(N, alpha_max, l_max, M=M, sigma_p=sigma_p)
    theta_list = build_theta_list(N, alpha_max, l_max, c1, c2, A, A_H)
    rng_master = np.random.default_rng(seed)
    times_ms = []
    for _ in range(frames):
        rng = np.random.default_rng(int(rng_master.integers(0, 2**31)))
        idx = rng.choice(Q_plus_1, size=P, replace=False)
        h_true = np.zeros(Q_plus_1, dtype=complex)
        h_true[idx] = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P)
        H_eff_true = sum(h_t * Theta for (h_t, Theta) in zip(h_true, theta_list))
        data_idx = rng.integers(0, 4, N)
        x_d = QPSK_CONST[data_idx] * np.sqrt(sigma_d_sq)
        noise = np.sqrt(N0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
        y = H_eff_true @ (x_p + x_d) + noise
        t0 = time.perf_counter()
        qing_receiver(y, x_p, N, alpha_max, l_max, c1, c2, A, A_H,
                      sigma_p_sq=sigma_p_sq, sigma_d_sq=sigma_d_sq,
                      N0=N0, n_iter=2)
        times_ms.append(1000.0 * (time.perf_counter() - t0))
    return times_ms, 0  # NumPy → no GPU peak


def _summarize(times_ms):
    if not times_ms:
        return {'mean_ms': float('nan'), 'median_ms': float('nan'), 'p95_ms': float('nan')}
    s = sorted(times_ms)
    return {
        'mean_ms': statistics.fmean(times_ms),
        'median_ms': s[len(s) // 2],
        'p95_ms': s[min(len(s) - 1, int(0.95 * len(s)))],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N-list', nargs='+', type=int, default=[512, 1024, 2048])
    ap.add_argument('--frames', type=int, default=50)
    ap.add_argument('--snr', type=float, default=20.0)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--tau-spread', type=float, default=0.010)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--fs-factor', type=float, default=2.0)
    ap.add_argument('--receivers', nargs='+',
                    choices=['classical-numpy', 'classical-torch', 'learned', 'qing'],
                    default=['classical-numpy', 'classical-torch'])
    ap.add_argument('--learned-ckpt', default=None,
                    help='Required if "learned" is in --receivers')
    ap.add_argument('--learned-variant', default='C2-rel')
    ap.add_argument('--cdtype', choices=['complex64', 'complex128'], default='complex64')
    ap.add_argument('--seed', type=int, default=20260506)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    if 'learned' in args.receivers and not args.learned_ckpt:
        raise SystemExit('--learned-ckpt is required when "learned" is in --receivers')

    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    cdtype = torch.complex64 if args.cdtype == 'complex64' else torch.complex128
    print(f'[device] {device}  cdtype={cdtype}', flush=True)

    rows = []
    for N in args.N_list:
        sys_obj = _build_system(N, args.p_paths, args.tau_spread, args.v_mean, args.fs_factor)
        for receiver in args.receivers:
            try:
                if receiver == 'classical-numpy':
                    t_ms, peak_mb = _time_classical_numpy(sys_obj, N, args.snr, args.frames, args.seed)
                elif receiver == 'classical-torch':
                    module, cfg = _build_torch_module(sys_obj, N, learned_heads=(),
                                                      ckpt_path=None, device=device, dtype=cdtype)
                    t_ms, peak_mb = _time_torch_module(module, cfg, sys_obj, N, args.snr,
                                                      args.frames, args.seed, device)
                elif receiver == 'learned':
                    module, cfg = _build_torch_module(sys_obj, N, learned_heads=('cand_active_rel',),
                                                      ckpt_path=args.learned_ckpt, device=device,
                                                      dtype=cdtype)
                    t_ms, peak_mb = _time_torch_module(module, cfg, sys_obj, N, args.snr,
                                                      args.frames, args.seed, device)
                elif receiver == 'qing':
                    if N != args.N_list[0]:
                        # Qing's pilot scheme requires Q+1 << N. We time it
                        # once at its native N=512 regardless of outer N-list.
                        continue
                    t_ms, peak_mb = _time_qing_native(args.frames, args.seed)
                    stats = _summarize(t_ms)
                    rows.append({'receiver': 'qing (native N=512)', 'N': 512,
                                 'frames': args.frames, 'peak_mem_MB': peak_mb,
                                 **stats})
                    print(f'[{"qing-native":>16s} N= 512] mean={stats["mean_ms"]:.2f} ms '
                          f'median={stats["median_ms"]:.2f} ms p95={stats["p95_ms"]:.2f} ms '
                          f'peak={peak_mb} MB  ({len(t_ms)} frames)', flush=True)
                    continue
                else:
                    raise ValueError(f'unknown receiver: {receiver}')
                stats = _summarize(t_ms)
                rows.append({'receiver': receiver, 'N': N, 'frames': args.frames,
                             'peak_mem_MB': peak_mb, **stats})
                print(f'[{receiver:>16s} N={N:>4d}] mean={stats["mean_ms"]:.2f} ms '
                      f'median={stats["median_ms"]:.2f} ms p95={stats["p95_ms"]:.2f} ms '
                      f'peak={peak_mb} MB  ({len(t_ms)} frames)', flush=True)
            except Exception as e:
                print(f'[{receiver:>16s} N={N:>4d}] FAILED: {type(e).__name__}: {e}', flush=True)
                rows.append({'receiver': receiver, 'N': N, 'frames': args.frames,
                             'peak_mem_MB': 0, 'mean_ms': float('nan'),
                             'median_ms': float('nan'), 'p95_ms': float('nan'),
                             'error': f'{type(e).__name__}: {e}'})

    csv_path = out / 'runtime_table.csv'
    fields = ['receiver', 'N', 'frames', 'mean_ms', 'median_ms', 'p95_ms', 'peak_mem_MB', 'error']
    with open(csv_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    json_path = out / 'runtime_table.json'
    with open(json_path, 'w') as f:
        json.dump({'config': vars(args), 'rows': rows}, f, indent=2)
    print(f'[done] wrote {csv_path} and {json_path}', flush=True)


if __name__ == '__main__':
    main()
