"""
test_pbigabp_consistency.py — paper-faithful Fig 4 reproduction at Ranasinghe's
exact regime to validate v2 implementation.

Paper Fig 4 setup (extracted from arXiv 2405.16945 line 727 + accompanying text):
  N = 128, AFDM single-pilot QPSK
  Block size B = 32 (1 pilot + 31 null guard)
  l_max ≈ 10 (from max range 75 m at fs=20 MHz)
  k_max ≈ 1 (from max velocity 602 km/h at fc=70 GHz, T_frame=N/fs)
  Q = (l_max+1)·(2k_max+1) = 11·3 = 33
  P = 8 paths, σ²_h = 1, E_S = 1, β=0.3, imax=40

EP frame: pilot at m_0 with energy ρ·N, data at remaining positions with
unit energy. Yin-style matched-energy convention with ρ = (1+B-1)/N would
make pilot+guard length 32 = B (this matches the paper's [22] reference).

Pass gates (paper Fig 4 visual estimate):
  BER monotonic decrease with SNR
  BER < 5e-2 at SNR=20 dB
  NMSE < -15 dB at SNR=20 dB
  These are PAPER-faithful gates; if v2 fails them at paper's regime,
  v2 has a bug. If passes, v2 is correct and our SP+UWA failure is regime
  mismatch, not implementation.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    construct_sensing_matrix, reconstruct_H_from_omp,
)
from afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver_v2_ep import (  # noqa: E402
    pbigabp_receiver_v2_ep,
)


def build_paper_ep_frame(N, B, m0, rng):
    """Paper Fig 4 [22] / Bemani convention: 1 pilot at m_0 with |pilot|² = N
    (NOT ρ·N — that's Yin's matched-energy for EP-DRCE, different paper).
    B-1 null guards adjacent, N-B data symbols at remaining positions
    (QPSK, unit energy).
    """
    pilot_value = np.sqrt(float(N)) * np.exp(1j * 0.0)   # |pilot|² = N per Bemani 2021
    # Place pilot at m_0; guards at m_0+1 .. m_0+B-1 (cyclic)
    guard_idx = ((m0 + np.arange(1, B)) % N).astype(np.int64)
    pilot_idx = int(m0)
    all_pg = np.concatenate(([pilot_idx], guard_idx))
    data_idx = np.setdiff1d(np.arange(N), all_pg, assume_unique=True).astype(np.int64)
    # Data symbols: unit-energy QPSK
    QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2.0)
    data_qam = QPSK[rng.integers(0, 4, size=len(data_idx))]
    # Build full frame
    x_frame = np.zeros(N, dtype=np.complex128)
    x_frame[pilot_idx] = pilot_value
    x_frame[data_idx] = data_qam
    # guards stay at 0
    return x_frame, pilot_value, pilot_idx, guard_idx, data_idx, data_qam


def make_paper_channel(N, l_max, k_max, P_paths, c1, c2, sigma2_h, rng):
    """Random P-path channel with delays in [0, l_max], Doppler in [-k_max, k_max],
    iid Gaussian gains with variance σ²_h per path. Returns h_true (Q,) and H_eff (N,N).
    """
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    h_true = np.zeros(Q, dtype=np.complex128)
    chosen = []
    for _ in range(P_paths):
        l = int(rng.integers(0, l_max + 1))
        k = int(rng.integers(-k_max, k_max + 1))
        col = l * K + (k + k_max)
        chosen.append((l, k, col))
    # Sum gains (in case of duplicates)
    for (l, k, col) in chosen:
        gain = (rng.standard_normal() + 1j * rng.standard_normal()) * np.sqrt(sigma2_h / 2.0)
        h_true[col] += gain
    H_true = reconstruct_H_from_omp(N, h_true, k_max, l_max, c1, c2, threshold=0.0)
    return h_true, H_true, chosen


def run_one_snr(snr_db, n_frames, *, N=128, B=32, l_max=10, k_max=1, P_paths=8,
                sigma2_h=1.0, beta=0.3, imax=40, seed_base=20260508):
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    c1 = 1.0 / (2.0 * N)
    c2 = 0.0
    sigma2 = 10.0 ** (-snr_db / 10.0)

    nmse_list = []
    bit_err_total = 0
    bit_total = 0
    iter_used_list = []

    for f in range(n_frames):
        rng = np.random.default_rng(seed_base + f * 7919 + snr_db * 31)
        # Build EP frame
        x_frame, pilot_value, pilot_idx, guard_idx, data_idx, data_qam = \
            build_paper_ep_frame(N, B, m0=N // 2, rng=rng)
        # Build channel
        h_true, H_true, chosen = make_paper_channel(
            N, l_max, k_max, P_paths, c1, c2, sigma2_h, rng)
        # Receive: y = H @ x + noise
        y_clean = H_true @ x_frame
        noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
        y = y_clean + np.sqrt(sigma2) * noise

        # PBiGaBP v2 EP
        out = pbigabp_receiver_v2_ep(
            y, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
            pilot_value=pilot_value, pilot_idx=pilot_idx,
            guard_idx=guard_idx, data_idx=data_idx,
            sigma2=sigma2, sigma2_h=sigma2_h, E_S=1.0,
            beta_x=beta, beta_h=beta, i_max=imax, eps_tol=1e-4)

        nmse = ((np.abs(out['H_eff'] - H_true) ** 2).sum()
                / max((np.abs(H_true) ** 2).sum(), 1e-30))
        nmse_list.append(nmse)
        iter_used_list.append(out['iter_done'])

        # BER on data positions only
        d_hat_data = out['d_hat'][data_idx]

        def to_bits(z):
            return np.concatenate([
                (z.real < 0).astype(np.float32),
                (z.imag < 0).astype(np.float32),
            ])
        bits_hat = to_bits(d_hat_data)
        bits_true = to_bits(data_qam)
        bit_err_total += int((bits_hat != bits_true).sum())
        bit_total += int(len(bits_hat))

    nmse_mean = float(np.mean(nmse_list))
    nmse_db = 10 * np.log10(nmse_mean)
    ber = float(bit_err_total / max(bit_total, 1))
    return dict(snr_db=snr_db, n_frames=n_frames, nmse=nmse_mean, nmse_db=nmse_db,
                ber=ber, iter_mean=float(np.mean(iter_used_list)),
                iter_max=int(max(iter_used_list)), bits_tot=bit_total,
                bits_err=bit_err_total)


def main():
    print("=" * 78)
    print("test_pbigabp_consistency.py — paper-faithful Fig 4 reproduction")
    print("=" * 78)
    print()

    snrs = [0, 5, 10, 15, 20]
    n_frames = 100   # paper uses ~10^4 frames; 100 should give visual-quality estimate

    # Paper-faithful: β=0.3, imax=40, |pilot|²=N per Bemani 2021 [22] convention
    config = dict(N=128, B=32, l_max=10, k_max=1, P_paths=8,
                  sigma2_h=1.0, beta=0.3, imax=40, seed_base=20260508)
    print(f"Config: {config}")
    print()

    results = []
    t0 = time.time()
    for snr in snrs:
        r = run_one_snr(snr, n_frames=n_frames, **config)
        results.append(r)
        print(f"  SNR={snr:>2} dB | NMSE={r['nmse_db']:+6.2f} dB | "
              f"BER={r['ber']:.3e} ({r['bits_err']}/{r['bits_tot']}) | "
              f"iter avg={r['iter_mean']:.1f} | wall={time.time()-t0:.1f}s")

    print()
    print("=" * 78)
    print("Pass gates (paper Fig 4 visual estimate):")
    print("=" * 78)

    # Gate 1: monotone NMSE
    nmse_db = [r['nmse_db'] for r in results]
    monotone = all(nmse_db[i+1] <= nmse_db[i] + 0.5 for i in range(len(nmse_db)-1))
    print(f"  G1. NMSE monotone decreasing in SNR: {'PASS' if monotone else 'FAIL'} "
          f"(values: {[f'{x:+.1f}' for x in nmse_db]})")

    # Gate 2: BER < 5e-2 at SNR=20
    ber_20 = next(r['ber'] for r in results if r['snr_db'] == 20)
    g2 = ber_20 < 5e-2
    print(f"  G2. BER < 5e-2 at SNR=20 dB: {'PASS' if g2 else 'FAIL'} "
          f"(value: {ber_20:.3e})")

    # Gate 3: NMSE < -15 dB at SNR=20
    nmse_20 = next(r['nmse_db'] for r in results if r['snr_db'] == 20)
    g3 = nmse_20 < -15.0
    print(f"  G3. NMSE < -15 dB at SNR=20 dB: {'PASS' if g3 else 'FAIL'} "
          f"(value: {nmse_20:+.2f} dB)")

    overall = monotone and g2 and g3
    print()
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    print()
    print(f"  Total wall time: {time.time()-t0:.1f}s")

    # Save
    out_dir = HERE / 'outputs_consistency'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'consistency_paper_fig4.json'
    with open(out_path, 'w') as f:
        json.dump({
            'config': config,
            'results': results,
            'gates': {'G1_monotone': monotone, 'G2_ber_at_20': bool(g2),
                       'G3_nmse_at_20': bool(g3), 'overall': bool(overall)},
        }, f, indent=2, default=str)
    print(f"  Saved: {out_path}")
    return overall


if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
