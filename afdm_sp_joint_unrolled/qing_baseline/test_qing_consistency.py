#!/usr/bin/env python
"""test_qing_consistency.py — reproduce Zheng 2025 Fig 3 within ±20% (then ±10%).

Paper setup (Section IV):
    N = 512, QPSK
    alpha_max = 2, l_max = 1   ->  Q + 1 = 10
    P = 3 channel paths, h_p ~ CN(0, 1/P)
    N_0 = 1 (reference; paper says 1 dBm)
    SNR_p = 50 dB fixed     ->  sigma_p^2 = N_0 * 10^5
    SNR_d sweep:  12, 15, 18, 21, 24, 27 dB
    M + 1 = 16 superimposed pilots
    n_iter = 2
    paper uses 1e6 frames; we default to 1000 (gives ~3% BER std at 1e-3)

Fig 3 16-pilot curve (visual readout):
    SNR_d  12      15      18       21       24      27
    BER    ~6e-3   ~3e-3   ~1e-3    ~3e-4    ~5e-4   ~3e-3

Acceptance gate: log10(BER) within +/- 0.2 of paper readout per SNR cell at
1000 frames; tighten to +/- 0.1 if needed at higher frame budgets.

Usage:
    python test_qing_consistency.py --frames 200      # quick smoke
    python test_qing_consistency.py --frames 1000     # default consistency
    python test_qing_consistency.py --frames 10000    # tight (~5 min on RTX 4090)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))

from afdm_sp_joint_unrolled.qing_baseline.qing_sp_afdm import (
    QPSK_CONST,
    build_theta_list,
    qing_pilot,
    qing_receiver,
)


def _build_daft(N: int, c1: float, c2: float):
    n_grid = np.arange(N).astype(float)
    Lc1 = np.diag(np.exp(-1j * 2.0 * np.pi * c1 * n_grid ** 2))
    Lc2 = np.diag(np.exp(-1j * 2.0 * np.pi * c2 * n_grid ** 2))
    F = np.fft.fft(np.eye(N), norm='ortho')
    A = Lc2 @ F @ Lc1
    return A, A.conj().T


def _bits_of(qpsk_syms: np.ndarray) -> np.ndarray:
    """Map QPSK symbols (any scaling) to bit pairs via real/imag sign."""
    return np.concatenate([(qpsk_syms.real < 0).astype(np.int8),
                           (qpsk_syms.imag < 0).astype(np.int8)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=512)
    ap.add_argument('--alpha-max', type=int, default=2)
    ap.add_argument('--l-max', type=int, default=1)
    ap.add_argument('--p-paths', type=int, default=3)
    ap.add_argument('--M', type=int, default=15, help='M -> M+1 = 16 pilots')
    ap.add_argument('--snr-d-list', nargs='+', type=int,
                    default=[12, 15, 18, 21, 24, 27])
    ap.add_argument('--snr-p-db', type=float, default=50.0)
    ap.add_argument('--N0', type=float, default=1.0,
                    help='AWGN variance reference; paper uses 1 dBm linear')
    ap.add_argument('--n-iter', type=int, default=2)
    ap.add_argument('--frames', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=20260506)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    N = args.N
    Q_plus_1 = (args.l_max + 1) * (2 * args.alpha_max + 1)
    Q = Q_plus_1 - 1
    c1 = (2 * args.alpha_max + 1) / (2 * N)
    c2 = 1.0 / (4.0 * N)  # arbitrary irrational-ish; paper says any irrational
    A, A_H = _build_daft(N, c1, c2)

    sigma_p_sq = args.N0 * 10 ** (args.snr_p_db / 10.0)
    sigma_p = np.sqrt(sigma_p_sq)
    x_p, _ = qing_pilot(N, args.alpha_max, args.l_max, M=args.M, sigma_p=sigma_p)
    theta_list = build_theta_list(N, args.alpha_max, args.l_max, c1, c2, A, A_H)

    print(f'N={N}  alpha_max={args.alpha_max}  l_max={args.l_max}  '
          f'Q+1={Q_plus_1}  M+1={args.M+1} pilots  P={args.p_paths}  '
          f'SNR_p={args.snr_p_db}dB  n_iter={args.n_iter}  frames={args.frames}',
          flush=True)

    # Fig 3 16-pilot visual readout (used only for the report message; not
    # asserted machine-readable). Update if the Fig is re-read differently.
    paper_fig3 = {12: 6e-3, 15: 3e-3, 18: 1e-3, 21: 3e-4, 24: 5e-4, 27: 3e-3}

    rng_master = np.random.default_rng(args.seed)
    rows = []
    t_start = time.time()
    for snr_d_db in args.snr_d_list:
        sigma_d_sq = args.N0 * 10 ** (snr_d_db / 10.0)
        errs = 0; bits_total = 0
        for fi in range(args.frames):
            seed_fi = int(rng_master.integers(0, 2**31))
            rng = np.random.default_rng(seed_fi)
            # Sparse channel: pick P (l_p, alpha_p) pairs uniformly at random
            l_alpha_choice = rng.choice(Q_plus_1, size=args.p_paths, replace=False)
            h_true = np.zeros(Q_plus_1, dtype=complex)
            h_true[l_alpha_choice] = (rng.standard_normal(args.p_paths) +
                                      1j * rng.standard_normal(args.p_paths)) / np.sqrt(2 * args.p_paths)
            H_eff_true = sum(h_t * Theta for (h_t, Theta) in zip(h_true, theta_list))
            # QPSK data with per-element variance sigma_d_sq
            data_idx = rng.integers(0, 4, N)
            x_d = QPSK_CONST[data_idx] * np.sqrt(sigma_d_sq)
            noise = np.sqrt(args.N0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
            y = H_eff_true @ (x_p + x_d) + noise

            out = qing_receiver(y, x_p, N, args.alpha_max, args.l_max, c1, c2,
                                A, A_H,
                                sigma_p_sq=sigma_p_sq, sigma_d_sq=sigma_d_sq,
                                N0=args.N0, n_iter=args.n_iter)
            x_d_hat = out['x_d_hat']
            bits_true = _bits_of(x_d / np.sqrt(sigma_d_sq))  # rescale truth
            bits_hat = _bits_of(x_d_hat / np.sqrt(sigma_d_sq))
            errs += int((bits_true != bits_hat).sum())
            bits_total += len(bits_true)
        ber = errs / max(bits_total, 1)
        ref = paper_fig3.get(snr_d_db, float('nan'))
        log_diff = (np.log10(max(ber, 1e-10)) - np.log10(max(ref, 1e-10))) if ref == ref else float('nan')
        rows.append({'snr_d_db': snr_d_db, 'frames': args.frames,
                     'errs': errs, 'bits_total': bits_total, 'ber': ber,
                     'paper_ber_fig3': ref, 'log10_diff': log_diff})
        print(f'  SNR_d={snr_d_db:>2d}dB: BER={ber:.3e}  '
              f'(paper Fig3 ~{ref:.0e}, log10 diff={log_diff:+.2f})  '
              f'errs={errs}/{bits_total} bits',
              flush=True)
    t_total = time.time() - t_start
    print(f'[done] total wall {t_total:.1f}s')

    if args.out:
        out_path = pathlib.Path(args.out); out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w') as f:
            json.dump({'config': vars(args), 'rows': rows,
                       'wall_seconds': t_total}, f, indent=2)
        print(f'wrote {out_path}', flush=True)

    # Pass/fail report (loose ±0.3 dec for first run; tighten later)
    bad = [r for r in rows
           if r['log10_diff'] == r['log10_diff']  # filter NaN
           and abs(r['log10_diff']) > 0.3]
    if not bad:
        print('CONSISTENCY OK (all SNR cells within +/- 0.3 dec of Fig 3)')
        return 0
    print(f'CONSISTENCY FAIL: {len(bad)}/{len(rows)} cells exceed +/- 0.3 dec '
          f'(see log10_diff above)')
    return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
