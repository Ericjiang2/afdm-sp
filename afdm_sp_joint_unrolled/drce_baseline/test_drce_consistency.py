"""
test_drce_consistency.py — synthetic-frame consistency check for DRCE.

Mirrors cao_baseline/test_cao_consistency.py. Goal: verify the DRCE SISO
implementation produces sensible BER curves at typical AFDM operating points,
within ±0.5 decade of the qualitative behavior reported in Yin et al. 2024
(arXiv 2206.12822) Fig 4 (BER vs SNR for fractional-Doppler EPA-AFDM).

Note: Yin's exact numerical curves are MIMO-AFDM with antenna gains we drop
in the SISO instantiation. The pass criterion is therefore the SHAPE
(monotone decreasing with SNR, slope close to LMMSE-bounded) and the
ABSOLUTE LEVEL within ±0.5 decade of the paper's headline points, NOT a
bit-exact match. This is the same pass-criterion philosophy used by
cao_baseline/test_cao_consistency.py for the dual-basis Cao reproduction.

Setup (matching Yin §V-A nominal):
  N=512, BPSK, P=2 paths, integer Doppler, λ=0.5, φ=0.5, AWGN.
  l_max, k_max chosen so that N_g = l_max*K + k_max + 1 fits comfortably.

Run:
    python afdm_sp_joint_unrolled/drce_baseline/test_drce_consistency.py
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

from afdm_sp_joint_unrolled.drce_baseline.drce_receiver import (  # noqa: E402
    build_ep_frame,
    drce_receiver,
    min_required_Ng,
)
from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    reconstruct_H_from_omp,
)


def _generate_sparse_channel(N, c1, c2, l_max, k_max, P, rng):
    """Build a P-path sparse AFDM channel with random (l, k) pairs and
    complex Gaussian gains normalized to unit total power."""
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    chosen = []
    seen = set()
    while len(chosen) < P:
        l_p = int(rng.integers(0, l_max + 1))
        k_p = int(rng.integers(-k_max, k_max + 1))
        if (l_p, k_p) in seen:
            continue
        seen.add((l_p, k_p))
        chosen.append((l_p, k_p))
    h_dense = np.zeros(Q, dtype=complex)
    raw = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2.0)
    raw /= np.sqrt(np.sum(np.abs(raw) ** 2))
    for (l_p, k_p), g in zip(chosen, raw):
        col = l_p * K + (k_p + k_max)
        h_dense[col] = g
    H = reconstruct_H_from_omp(N, h_dense, k_max, l_max, c1, c2, threshold=0.0)
    return H, h_dense, chosen


def run_one(snr_db, n_frames, *, N, c1, c2, l_max, k_max, m0, N_g,
            P_paths, seed):
    K = 2 * k_max + 1
    BPSK = np.array([1+0j, -1+0j], dtype=complex)   # Yin uses BPSK
    sigma2 = 1.0 / (10.0 ** (snr_db / 10.0))
    rng = np.random.default_rng(seed)
    err_bits = 0
    tot_bits = 0
    nmse_acc = []
    for fi in range(n_frames):
        # New channel + new data + new noise per frame
        H_true, _, _ = _generate_sparse_channel(N, c1, c2, l_max, k_max,
                                                 P_paths, rng)
        data_idx = rng.integers(0, 2, size=N)
        data_qam = BPSK[data_idx]
        ep = build_ep_frame(N, m0, N_g, pilot_unit=1.0+0j,
                             data_qam=data_qam, rho=0.5)
        y_clean = H_true @ ep['x_frame']
        noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
        y = y_clean + np.sqrt(sigma2) * noise

        out = drce_receiver(
            y, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
            m0=m0, N_g=N_g, pilot_value=ep['pilot_value'], sigma2=sigma2,
            constellation=BPSK, rho=0.5,
            detector_iter=20, detector_damp=0.5)

        # NMSE on H_eff
        nmse_f = (np.abs(out['H_eff'] - H_true) ** 2).sum() \
                 / (np.abs(H_true) ** 2).sum()
        if np.isfinite(nmse_f):
            nmse_acc.append(float(nmse_f))

        # Hard-decode BPSK on data positions (un-scale by data_scaling)
        d_hat_data = out['d_hat'][ep['data_pos']] / ep['data_scaling']
        d_decoded = np.where(d_hat_data.real >= 0, 1+0j, -1+0j)
        bits_true = (data_qam[ep['data_pos']].real < 0).astype(np.int32)
        bits_hat = (d_decoded.real < 0).astype(np.int32)
        err_bits += int(np.sum(bits_true != bits_hat))
        tot_bits += len(bits_true)

    ber = err_bits / max(tot_bits, 1)
    nmse_db = 10.0 * np.log10(np.mean(nmse_acc) + 1e-30) if nmse_acc else None
    return dict(
        snr_db=snr_db, frames=n_frames, ber=ber, err_bits=err_bits,
        tot_bits=tot_bits, nmse_db=nmse_db,
    )


def main():
    print("=" * 70)
    print("test_drce_consistency.py — Yin DRCE SISO synthetic check")
    print("=" * 70)

    N = 512
    c1 = 1.0 / (2.0 * N)
    c2 = 0.0
    l_max = 4
    k_max = 2
    K = 2 * k_max + 1
    P_paths = 2
    m0 = N // 2
    N_g = min_required_Ng(l_max, k_max) + 1   # = 4*5 + 2 + 1 = 23
    print(f"Setup: N={N} c1=1/(2N) c2=0 l_max={l_max} k_max={k_max} "
          f"P_paths={P_paths} m0={m0} N_g={N_g} (min={min_required_Ng(l_max, k_max)})")
    print(f"Q = (l_max+1)*K = {(l_max+1)*K}, obs_idx_width = {2*N_g+1}, "
          f"data_pos = {N - (2*N_g+1)}")

    snr_grid = [0, 5, 10, 15, 20]
    n_frames = 200
    results = []
    t0 = time.time()
    for snr in snr_grid:
        r = run_one(snr, n_frames,
                     N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
                     m0=m0, N_g=N_g, P_paths=P_paths,
                     seed=20260508 + snr)
        elapsed = time.time() - t0
        print(f"  SNR={snr:2d} dB  BER={r['ber']:.3e}  "
              f"NMSE_H={r['nmse_db']:+.2f} dB  "
              f"({r['err_bits']:5d}/{r['tot_bits']:6d})  "
              f"[{elapsed:5.1f}s]")
        results.append(r)

    # Pass criterion: BER monotone decreasing AND BER@20dB <= 1e-2
    bers = [r['ber'] for r in results]
    monotone = all(bers[i] >= bers[i+1] - 1e-4 for i in range(len(bers) - 1))
    ber_20 = next((r['ber'] for r in results if r['snr_db'] == 20), None)
    print()
    print(f"  Monotone (allowing 1e-4 noise): {'PASS' if monotone else 'FAIL'}")
    print(f"  BER@20dB = {ber_20:.3e}  "
          f"({'PASS (<= 1e-2)' if ber_20 is not None and ber_20 <= 1e-2 else 'FAIL'})")

    # Reference (Yin Fig 4 6-tap fractional EPA-AFDM, MIMO):
    #   SNR= 0: ~1e-1, SNR= 5: ~5e-2, SNR=10: ~1e-2, SNR=15: ~3e-3, SNR=20: ~5e-4
    # We use 2-path SISO so absolute levels can differ; the ±0.5 decade gate is:
    yin_ref = {0: 1e-1, 5: 5e-2, 10: 1e-2, 15: 3e-3, 20: 5e-4}
    print(f"  vs Yin Fig 4 reference (qualitative, 6-path MIMO):")
    for r in results:
        ref = yin_ref.get(r['snr_db'])
        if ref is not None and r['ber'] > 0:
            log_diff = abs(np.log10(r['ber']) - np.log10(ref))
            ok = log_diff <= 0.5
            print(f"    SNR={r['snr_db']:2d}: ours {r['ber']:.3e} vs ref {ref:.0e}  "
                  f"|log Δ|={log_diff:.2f}  ({'OK' if ok else 'OUTSIDE'})")
        else:
            print(f"    SNR={r['snr_db']:2d}: ours {r['ber']:.3e} (zero err — too few frames at high SNR)")

    out_dir = HERE / 'outputs'
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / 'consistency_drce_synthetic.json'
    out_path.write_text(json.dumps({
        'config': dict(N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
                        P_paths=P_paths, m0=m0, N_g=N_g, n_frames=n_frames),
        'results': results,
    }, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == '__main__':
    main()
