"""
test_lmmse_smoke.py — synthetic 2-path SP-AFDM smoke test for LMMSE-SP.

Pass: NMSE < -15 dB, BER < 1e-2 at SNR=20 dB.
"""
from __future__ import annotations

import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.afdm_baselines import reconstruct_H_from_omp  # noqa: E402
from afdm_sp_joint_unrolled.lmmse_baseline.lmmse_receiver import (  # noqa: E402
    lmmse_sp_receiver,
)


def main():
    print("=" * 78)
    print("test_lmmse_smoke.py — synthetic 2-path SP-AFDM smoke for LMMSE-SP")
    print("=" * 78)

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

    print()
    print("Iter sweep at SNR=20 (n_iter=1 vanilla / n_iter=3 default):")
    sigma2 = 10.0 ** (-20.0 / 10.0)
    rng2 = np.random.default_rng(20260508 + 20 * 1009)
    noise = (rng2.standard_normal(N) + 1j * rng2.standard_normal(N)) / np.sqrt(2.0)
    y20 = y_clean + np.sqrt(sigma2) * noise

    def to_bits(z):
        return np.concatenate([
            (z.real < 0).astype(np.float32),
            (z.imag < 0).astype(np.float32),
        ])

    for ni in (1, 2, 3, 5):
        t0 = time.time()
        out = lmmse_sp_receiver(
            y20, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
            pilot=pilot, sigma2=sigma2, rho=rho, sigma2_h=1.0,
            n_iter=ni, bp_n_iter=20, bp_damp=0.5)
        wall = (time.time() - t0) * 1000
        nmse = ((np.abs(out['H_eff'] - H_true) ** 2).sum()
                / (np.abs(H_true) ** 2).sum())
        d_unit = out['d_hat'] / np.sqrt(P_d)
        ber = float(np.mean(to_bits(d_unit) != to_bits(data_qam)))
        print(f"  n_iter={ni} | NMSE={10*np.log10(nmse):+.2f} dB | "
              f"BER={ber:.3e} | wall={wall:.0f} ms")

    print()
    print("SNR sweep at default n_iter=3:")
    for snr_db in (10, 15, 20):
        sigma2 = 10.0 ** (-snr_db / 10.0)
        rng2 = np.random.default_rng(20260508 + snr_db * 1009)
        noise = (rng2.standard_normal(N) + 1j * rng2.standard_normal(N)) / np.sqrt(2.0)
        y = y_clean + np.sqrt(sigma2) * noise

        t0 = time.time()
        out = lmmse_sp_receiver(
            y, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
            pilot=pilot, sigma2=sigma2, rho=rho, sigma2_h=1.0,
            n_iter=3, bp_n_iter=20, bp_damp=0.5)
        wall = time.time() - t0

        nmse_h = ((np.abs(out['H_eff'] - H_true) ** 2).sum()
                  / (np.abs(H_true) ** 2).sum())
        d_hat_unit = out['d_hat'] / np.sqrt(P_d)
        ber = float(np.mean(to_bits(d_hat_unit) != to_bits(data_qam)))

        print(f"  SNR={snr_db:>2} dB | NMSE={10*np.log10(nmse_h):+.2f} dB"
              f" | BER={ber:.3e} | wall={wall*1000:.1f} ms")

    # Pass gates at SNR=20, n_iter=3 (deployable LMMSE)
    print()
    print("Pass gates (n_iter=3 default):")
    sigma2 = 10.0 ** (-20.0 / 10.0)
    rng2 = np.random.default_rng(20260508 + 20 * 1009)
    noise = (rng2.standard_normal(N) + 1j * rng2.standard_normal(N)) / np.sqrt(2.0)
    y = y_clean + np.sqrt(sigma2) * noise
    out_n3 = lmmse_sp_receiver(
        y, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
        pilot=pilot, sigma2=sigma2, rho=rho, sigma2_h=1.0,
        n_iter=3, bp_n_iter=20, bp_damp=0.5)
    nmse_n3 = ((np.abs(out_n3['H_eff'] - H_true) ** 2).sum()
                / (np.abs(H_true) ** 2).sum())
    d_n3 = out_n3['d_hat'] / np.sqrt(P_d)
    ber_n3 = float(np.mean(to_bits(d_n3) != to_bits(data_qam)))

    g1 = 10 * np.log10(nmse_n3) < -15.0
    g2 = ber_n3 < 1e-2
    print(f"  G1: NMSE < -15 dB at SNR=20: "
          f"{'PASS' if g1 else 'FAIL'} (val: {10*np.log10(nmse_n3):+.2f} dB)")
    print(f"  G2: BER < 1e-2 at SNR=20: "
          f"{'PASS' if g2 else 'FAIL'} (val: {ber_n3:.3e})")
    print()
    print(f"  Overall: {'PASS' if (g1 and g2) else 'FAIL'}")
    return g1 and g2


if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
