#!/usr/bin/env python
"""Loop-13 new baselines eval: OMP+MP-serial + PCSI+MMSE.

Runs two additional baselines at the Loop-12-locked system config so the
results can be overlaid with the existing pooled classical-BP / learned
curves:

  - omp_mp_serial: one-shot OMP channel estimation + one MP(BP) detection.
    No outer iteration, no DA-LS refinement (unlike joint_omp_mp_iterative).
    This is the classical non-iterative benchmark.

  - pcsi_mmse   : one-shot MMSE equalizer using the TRUE channel H_true.
    This is the physical lower bound for a linear MMSE receiver — no
    estimation error, only thermal noise + data interference. Useful as
    a soft lower bound on the waterfall.

Both arms are evaluated on the SAME per-frame channels / data / noise
(paired), so differences are directly attributable to the detector rather
than Monte-Carlo variance.

Optional --fs-factor lets us swap the sampling rate (default 2·B Nyquist
→ 4·B for the 4× oversampling sensitivity test).

Usage (remote):
    python afdm_sp_joint_unrolled/loop13_new_baselines_eval.py \
        --n-total 1024 --v-mean 2.0 --p-paths 8 --tau-spread 0.010 \
        --rho 0.5 --snr-list 0 5 10 15 20 25 \
        --frames-per-snr 400 --target-errors 300 --min-frames 50 \
        --mp-mode bp --seed 20260425 \
        --out afdm_sp_joint_unrolled/outputs_loop13_new_baselines
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.afdm_baselines import (
    construct_sensing_matrix,
    omp_sparse,
    reconstruct_H_from_omp,
)
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    QPSK,
    _bits_of_symbol,
    _make_system_variable_N,
)


def _torch_bp(y, H, sigma2, const, n_iter=20, damp=0.5, device=None):
    dev = device if device is not None else torch.device(
        'cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y, H, sigma2, const, n_iter=n_iter,
                               threshold=1e-4, damp=damp, device=dev,
                               return_numpy=True, return_soft=False)


def _mmse_detect(y_data, H, sigma2, P_d):
    """Linear MMSE detector given an effective channel H.

    With perfect CSI (H = H_true) this is the Wiener-filter lower bound
    for linear equalization at signal power P_d and noise variance sigma2.
    """
    N = H.shape[0]
    HtH = H.conj().T @ H
    reg = (sigma2 / max(P_d, 1e-12)) * np.eye(N)
    return np.linalg.solve(HtH + reg, H.conj().T @ y_data)


def _omp_channel_estimate(sys_obj, y_daft, pilot_scaled):
    """One-shot OMP channel estimate (no joint iteration)."""
    N = sys_obj.N_total
    Phi = construct_sensing_matrix(
        N, pilot_scaled, sys_obj.c1, sys_obj.c2,
        sys_obj.l_max_cap, sys_obj.k_max_cap)
    n_paths_omp = int(getattr(sys_obj, 'P_paths', 10))
    h_omp, _ = omp_sparse(y_daft, Phi, n_paths_omp)
    return reconstruct_H_from_omp(
        N, h_omp, sys_obj.k_max_cap, sys_obj.l_max_cap,
        sys_obj.c1, sys_obj.c2)


def _rebuild_sys_with_fs_factor(sys_obj, fs_factor):
    """Swap sys_obj.fs = fs_factor * B and refresh dependent fields.

    Notes
    -----
    fs enters the channel only through the Doppler normalisation
    `D_vals = doppler_a * fc / fs` (see afdm_env.generate_channel_matrix).
    Delay bins are tied to 1/(N*delta_f), so fs swaps shift the effective
    Doppler spread (in bins) but leave the delay grid intact.  k_max_cap
    is recomputed so the dictionary re-covers the new (smaller) Doppler
    shell.
    """
    sys_obj.B = 4e3
    sys_obj.fs = float(fs_factor) * sys_obj.B
    sys_obj.Ts = 1.0 / sys_obj.fs
    # Rebuild k_max_cap with the new fs.
    v_max = float(getattr(sys_obj, 'v_mean', 2.0)) + 3.0 * 0.5
    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    sys_obj.k_max_cap = max(int(np.ceil(sys_obj.N_total * d_norm)), 1)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--tau-spread', type=float, default=0.010,
                    help='Delay spread in seconds (default 10 ms).')
    ap.add_argument('--rho', type=float, default=0.5)
    ap.add_argument('--snr-list', nargs='+', type=int,
                    default=[0, 5, 10, 15, 20, 25])
    ap.add_argument('--frames-per-snr', type=int, default=400)
    ap.add_argument('--target-errors', type=int, default=300,
                    help='Adaptive early-stop once OMP+MP-serial has this many '
                         'bit errors (0 disables).')
    ap.add_argument('--min-frames', type=int, default=50)
    ap.add_argument('--mp-mode', choices=['bp'], default='bp',
                    help='Detector backend for OMP+MP-serial (torch BP only '
                         'for speed on the GPU).')
    ap.add_argument('--damp', type=float, default=0.5)
    ap.add_argument('--fs-factor', type=float, default=2.0,
                    help='Sampling rate fs = fs_factor * B (default 2, i.e. '
                         'Nyquist). Set 4 for the 4B oversampling test.')
    ap.add_argument('--seed', type=int, default=20260425)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sys_obj = _make_system_variable_N(args.n_total)
    sys_obj.P_paths = int(args.p_paths)
    sys_obj.tau_spread = float(args.tau_spread)
    sys_obj.rho = float(args.rho)
    sys_obj.v_mean = float(args.v_mean)
    sys_obj.gen_h_daft_convention = 'python'
    sys_obj.baseline_phase_convention = 'python'

    if abs(args.fs_factor - 2.0) > 1e-9:
        _rebuild_sys_with_fs_factor(sys_obj, args.fs_factor)
    else:
        # Default: rebuild k_max_cap / chirp in case v_mean changed.
        v_max = sys_obj.v_mean + 3.0 * 0.5
        d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
        sys_obj.k_max_cap = max(int(np.ceil(args.n_total * d_norm)), 1)
        K = 2 * sys_obj.k_max_cap + 1
        sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
        sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
        sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()

    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[LOOP13_CONFIG] N={args.n_total} v={sys_obj.v_mean} "
          f"P={sys_obj.P_paths} tau={sys_obj.tau_spread*1e3:.2f}ms "
          f"rho={sys_obj.rho} fs={sys_obj.fs/1e3:.1f}kHz "
          f"(fs_factor={args.fs_factor}) B={sys_obj.B/1e3:.1f}kHz "
          f"k_max_cap={sys_obj.k_max_cap} l_max_cap={sys_obj.l_max_cap} "
          f"SNRs={args.snr_list} frames={args.frames_per_snr} seed={args.seed} "
          f"device={dev}",
          flush=True)

    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq

    results = {}
    t0 = time.time()
    rng_master = np.random.default_rng(args.seed)
    for snr in args.snr_list:
        errs_omp = 0       # OMP+MP-serial bit errors
        errs_pcsi = 0      # PCSI+MMSE bit errors
        bits_tot = 0
        nmse_omp = []
        per_frame_errs_omp = []
        per_frame_errs_pcsi = []
        for fi in range(args.frames_per_snr):
            seed_fi = int(rng_master.integers(0, 2**31))
            np.random.seed(seed_fi)
            rng = np.random.default_rng(seed_fi)
            H_true, _, _ = sys_obj.generate_channel_matrix()
            data_idx = rng.integers(0, 4, size=args.n_total)
            data_qam = QPSK[data_idx]
            bits_true = np.concatenate([
                (data_qam.real < 0).astype(np.float32),
                (data_qam.imag < 0).astype(np.float32),
            ])
            x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
            y = H_true @ x_sp
            sigma2 = 1.0 / (10 ** (snr / 10.0))
            noise = (rng.standard_normal(args.n_total) +
                     1j * rng.standard_normal(args.n_total)) / np.sqrt(2.0)
            y_daft = y + np.sqrt(sigma2) * noise

            # ── Arm 1: OMP + MP(BP) serial ───────────────────────────────
            H_omp = _omp_channel_estimate(sys_obj, y_daft, pilot_scaled)
            y_data_omp = y_daft - H_omp @ pilot_scaled
            x_omp = _torch_bp(y_data_omp, H_omp, sigma2, const_data,
                               n_iter=20, damp=args.damp, device=dev)
            b_omp = _bits_of_symbol(x_omp / np.sqrt(P_d), args.n_total)
            e_omp = int((b_omp != bits_true).sum())
            nmse = float((np.abs(H_omp - H_true) ** 2).sum() /
                         (np.abs(H_true) ** 2).sum())
            if np.isfinite(nmse):
                nmse_omp.append(nmse)

            # ── Arm 2: PCSI + MMSE ──────────────────────────────────────
            y_data_pcsi = y_daft - H_true @ pilot_scaled
            x_pcsi = _mmse_detect(y_data_pcsi, H_true, sigma2, P_d)
            b_pcsi = _bits_of_symbol(x_pcsi / np.sqrt(P_d), args.n_total)
            e_pcsi = int((b_pcsi != bits_true).sum())

            errs_omp += e_omp
            errs_pcsi += e_pcsi
            bits_tot += 2 * args.n_total
            per_frame_errs_omp.append(e_omp)
            per_frame_errs_pcsi.append(e_pcsi)

            if (args.target_errors > 0 and errs_omp >= args.target_errors
                    and (fi + 1) >= args.min_frames):
                print(f"  [snr={snr:2d} early-stop] omp-serial cum errs "
                      f"{errs_omp} >= target {args.target_errors} at fi={fi+1}",
                      flush=True)
                break
            if fi % 10 == 0:
                print(f"  [snr={snr:2d} fi={fi:3d}]  omp_serial="
                      f"{errs_omp/max(bits_tot,1):.3e} ({errs_omp})  "
                      f"pcsi_mmse={errs_pcsi/max(bits_tot,1):.3e} "
                      f"({errs_pcsi})  [{time.time()-t0:.0f}s]",
                      flush=True)

        ber_omp = errs_omp / max(bits_tot, 1)
        ber_pcsi = errs_pcsi / max(bits_tot, 1)
        actual_frames = len(per_frame_errs_omp)
        results[str(snr)] = dict(
            frames=int(actual_frames),
            cum_bits=int(bits_tot),
            omp_serial_errs=int(errs_omp),
            omp_serial_ber=float(ber_omp),
            pcsi_mmse_errs=int(errs_pcsi),
            pcsi_mmse_ber=float(ber_pcsi),
            omp_serial_nmse_db=(float(10 * np.log10(np.mean(nmse_omp) + 1e-30))
                                 if nmse_omp else None),
            per_frame_errs_omp=[int(e) for e in per_frame_errs_omp],
            per_frame_errs_pcsi=[int(e) for e in per_frame_errs_pcsi],
        )

    results['_config'] = dict(
        N=args.n_total, v_mean=args.v_mean, P_paths=int(sys_obj.P_paths),
        tau_spread_ms=sys_obj.tau_spread * 1e3, rho=sys_obj.rho,
        fs_kHz=sys_obj.fs / 1e3, fs_factor=args.fs_factor,
        B_kHz=sys_obj.B / 1e3, mp_mode=args.mp_mode, damp=args.damp,
        frames=args.frames_per_snr, seed=args.seed,
        k_max_cap=sys_obj.k_max_cap, l_max_cap=sys_obj.l_max_cap,
    )
    (out / 'results.json').write_text(json.dumps(results, indent=2))

    md = ['# Loop-13 new baselines',
          f'N={args.n_total} v={sys_obj.v_mean} P={sys_obj.P_paths} '
          f'tau={sys_obj.tau_spread*1e3:.1f}ms rho={sys_obj.rho} '
          f'fs={sys_obj.fs/1e3:.1f}kHz fs_factor={args.fs_factor}',
          '',
          '| SNR | frames | bits | OMP+MP-serial BER | PCSI+MMSE BER | OMP NMSE (dB) |',
          '|---:|---:|---:|---:|---:|---:|']
    for s in args.snr_list:
        r = results[str(s)]
        nmse_str = (f"{r['omp_serial_nmse_db']:+.2f}"
                    if r['omp_serial_nmse_db'] is not None else '—')
        md.append(f"| {s} | {r['frames']} | {r['cum_bits']} | "
                  f"{r['omp_serial_ber']:.3e} | {r['pcsi_mmse_ber']:.3e} | "
                  f"{nmse_str} |")
    (out / 'results.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'[done] wrote {out}')


if __name__ == '__main__':
    main()
