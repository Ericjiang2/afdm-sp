"""
test_pbigabp_smoke.py — synthetic 2-path channel smoke test for PBiGaBP.

Validates that the per-edge BP receiver:
1. Recovers the correct sparse support (top-K heat by |h̃| matches true taps)
2. Achieves negative NMSE on H_eff at SNR=20 dB
3. Detects QPSK data with BER ≤ 1e-3 on a clean 2-path channel

Run:
    python afdm_sp_joint_unrolled/pbigabp_baseline/test_pbigabp_smoke.py
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver import (  # noqa: E402
    pbigabp_receiver,
)
from afdm_sp_joint_unrolled.afdm_baselines import reconstruct_H_from_omp  # noqa: E402


def main():
    print("=" * 68)
    print("test_pbigabp_smoke.py — synthetic 2-path SP-AFDM smoke test")
    print("=" * 68)

    rng = np.random.default_rng(20260508)
    N = 256
    c1 = 1.0 / (2.0 * N)
    c2 = 0.0
    l_max = 4
    k_max = 2
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    rho = 0.5
    P_d = 1 - rho

    chosen = [(1, 1), (3, -1)]
    h_true = np.zeros(Q, dtype=complex)
    for (l_p, k_p) in chosen:
        col = l_p * K + (k_p + k_max)
        h_true[col] = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0)
    H_true = reconstruct_H_from_omp(N, h_true, k_max, l_max, c1, c2, threshold=0.0)

    zc = np.exp(-1j * np.pi * 7 * np.arange(N) ** 2 / N)
    pilot = np.sqrt(rho) * zc
    QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
    data_qam = QPSK[rng.integers(0, 4, size=N)]
    x_sp = pilot + np.sqrt(P_d) * data_qam
    y_clean = H_true @ x_sp
    snr_db = 20
    sigma2 = 10.0 ** (-snr_db / 10.0)
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    y = y_clean + np.sqrt(sigma2) * noise

    out = pbigabp_receiver(
        y, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
        pilot=pilot, sigma2=sigma2, rho=rho,
        sigma2_h=1.0, beta_x=0.3, beta_h=0.3,
        i_max=40, eps_tol=1e-4, return_trajectory=False)

    nmse_h = ((np.abs(out['H_eff'] - H_true) ** 2).sum()
              / (np.abs(H_true) ** 2).sum())
    h_hat = out['h_hat']
    top_idx = np.argsort(-np.abs(h_hat))[:4]
    true_idx = [l * K + (k + k_max) for (l, k) in chosen]

    def to_bits(z):
        return np.concatenate([
            (z.real < 0).astype(np.float32),
            (z.imag < 0).astype(np.float32),
        ])
    d_hat_unscaled = out['d_hat'] / np.sqrt(P_d)
    ber = float(np.mean(to_bits(d_hat_unscaled) != to_bits(data_qam)))

    print(f"  iters_used         : {out['iter_done']}/40")
    print(f"  converged          : {out['converged']}")
    print(f"  H_eff NMSE         : {nmse_h:.3e}  ({10*np.log10(nmse_h):+.2f} dB)")
    print(f"  Top-4 h indices    : {list(top_idx)}")
    print(f"  Top-4 |h_hat|      : {[f'{x:.3f}' for x in np.abs(h_hat[top_idx])]}")
    print(f"  True path indices  : {true_idx}")
    print(f"  True |h|           : {[f'{abs(h_true[i]):.3f}' for i in true_idx]}")
    print(f"  BER @ SNR=20 dB    : {ber:.3e}")

    nmse_pass = nmse_h < 1e-2     # require < -20 dB
    support_pass = all(t in top_idx[:2].tolist() for t in true_idx)
    ber_pass = ber <= 1e-3

    print()
    print(f"  NMSE PASS (<-20 dB)        : {'PASS' if nmse_pass else 'FAIL'}")
    print(f"  Support recovered (top-2)  : {'PASS' if support_pass else 'FAIL'}")
    print(f"  BER PASS (<=1e-3)          : {'PASS' if ber_pass else 'FAIL'}")

    overall_pass = nmse_pass and support_pass and ber_pass
    print()
    print(f"  Overall: {'PASS' if overall_pass else 'FAIL'}")
    return overall_pass


if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
