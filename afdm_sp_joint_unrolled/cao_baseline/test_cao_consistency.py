"""
test_cao_consistency.py — reproduce Cao 2024 ICCT Fig 3 / Fig 4 BER curves.

Setup matched to Cao paper Section IV:
  - N = 512 subcarriers
  - BPSK modulation (ISP scheme; QPSK is for EPA in Fig 3 SE-matching)
  - P = 3 channel paths
  - Channel coefficients h_i ~ CN(0, 1/P) i.i.d.
  - INTEGER Doppler (paper assumes l_i ∈ [0, l_max], α_i ∈ [-α_max, α_max])
  - Pilot power λ = 0.5, data power φ = 0.5 (paper-optimal per their Fig 2)
  - SNR = φ / σ² (Section IV)
  - Termination: ||ĥ^(n) − ĥ^(n−1)|| ≤ 1e-6 or 10 iters (paper convention)
  - Two regimes: (l_max=4, α_max=4) for Fig 3, (l_max=8, α_max=8) for Fig 4

Not matched (cannot match without re-implementing the simulator):
  - Pilot vector: we use the project's ZC sequence (generic SP); paper does
    not state pilot specifics for ISP — just that the SP framework supports
    arbitrary p. Should not materially affect BER for ISP since OMP works
    on any well-conditioned Φ_p.
  - Detector: we use mp_detect_bp_torch (Raviteja-style MP-PIC); paper says
    "MP detector" without specifics, citing the same Raviteja reference [9].

Reference numbers from Cao Fig 3 (l_max=4, α_max=4, ISP curve, BPSK):
  SNR=8 dB  → BER ≈ 6e-2
  SNR=10 dB → BER ≈ 2e-2
  SNR=12 dB → BER ≈ 7e-3
  SNR=14 dB → BER ≈ 1.5e-3
  SNR=16 dB → BER ≈ 4e-4

Reference numbers from Cao Fig 4 (l_max=8, α_max=8, ISP curve, BPSK):
  SNR=8 dB  → BER ≈ 7e-2
  SNR=10 dB → BER ≈ 2.5e-2
  SNR=12 dB → BER ≈ 1e-2
  SNR=14 dB → BER ≈ 3e-3
  SNR=16 dB → BER ≈ 1e-3

Pass criterion: ours-basis BER within ±0.3 decade of paper at ≥3/5 SNR
points. (Cao's own 16-pilot consistency test uses ±0.3 dec with 3/6 pass.)

Run from project root:
    conda activate AFDM
    python afdm_sp_joint_unrolled/cao_baseline/test_cao_consistency.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.cao_baseline.cao_isp_receiver import cao_isp_receiver  # noqa: E402
from afdm_sp_joint_unrolled.afdm_baselines import reconstruct_H_from_omp  # noqa: E402
from afdm_sp_joint_unrolled.run_classical_baselines_python import _make_system_variable_N  # noqa: E402


# Cao paper reference numbers (from Fig 3 and Fig 4 visually read off curves).
PAPER_REF_FIG3 = {  # (l_max=4, α_max=4)
    8:  6.0e-2,
    10: 2.0e-2,
    12: 7.0e-3,
    14: 1.5e-3,
    16: 4.0e-4,
}
PAPER_REF_FIG4 = {  # (l_max=8, α_max=8)
    8:  7.0e-2,
    10: 2.5e-2,
    12: 1.0e-2,
    14: 3.0e-3,
    16: 1.0e-3,
}


# BPSK constellation: real ±1 only
BPSK = np.array([+1.0, -1.0], dtype=complex)


def setup_cao_system(N=512, l_max=4, k_max=4):
    sys_obj = _make_system_variable_N(N)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.l_max_cap = int(l_max)
    sys_obj.k_max_cap = int(k_max)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
    return sys_obj


def generate_cao_channel(P, l_max, k_max, rng):
    """Generate integer-Doppler channel realization per Cao paper.

    P paths drawn uniformly: l_i ∈ [0, l_max], α_i ∈ [-α_max, α_max].
    Coefficients h_i ~ CN(0, 1/P) i.i.d.

    Returns dict with l_i, k_i (alpha indices, integer), g_i (gains).
    """
    l_i = rng.integers(0, l_max + 1, size=P).astype(int)
    k_i = rng.integers(-k_max, k_max + 1, size=P).astype(int)
    g_real = rng.standard_normal(P) / np.sqrt(2 * P)
    g_imag = rng.standard_normal(P) / np.sqrt(2 * P)
    g_i = (g_real + 1j * g_imag).astype(complex)
    return dict(l_i=l_i, k_i=k_i, g_i=g_i)


def build_h_eff_integer(N, channel, k_max, l_max, c1, c2):
    """Build H_eff via our reconstruct_H_from_omp from integer (l, α) taps."""
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    h_sparse = np.zeros(Q, dtype=complex)
    for l, k, g in zip(channel['l_i'], channel['k_i'], channel['g_i']):
        col = int(l) * K + (int(k) + k_max)
        h_sparse[col] += g
    return reconstruct_H_from_omp(N, h_sparse, k_max, l_max, c1, c2,
                                   threshold=0.0)


def bpsk_bits(symbols):
    """Real-part hard slicing for BPSK at unit-power scale."""
    return (symbols.real < 0).astype(np.float32)


def run_consistency(N, l_max, k_max, P, snr_list, n_frames, seed,
                     basis='ours', max_iter=10, tol=1e-6, verbose=True):
    sys_obj = setup_cao_system(N=N, l_max=l_max, k_max=k_max)
    c1, c2 = sys_obj.c1, sys_obj.c2
    pilot = sys_obj._zc_seq.copy()

    rng_master = np.random.default_rng(seed)

    results = {}
    print(f"\n  basis={basis}  N={N}  l_max={l_max}  α_max={k_max}  P={P}  "
          f"frames={n_frames}/SNR")
    print(f"  {'SNR':>4} | {'BER':>10}  {'errs':>6}/{'bits':>7}  {'paper':>9}  {'log10 Δ':>8}")
    print(f"  {'-'*4}-+-{'-'*10}--{'-'*6}-/{'-'*7}--{'-'*9}--{'-'*8}")
    for snr_db in snr_list:
        sigma2 = 0.5 / (10 ** (snr_db / 10.0))           # SNR_d = φ/σ², φ=0.5
        errs = 0
        bits_total = 0
        t0 = time.time()
        for fi in range(n_frames):
            seed_fi = int(rng_master.integers(0, 2**31))
            rng = np.random.default_rng(seed_fi)
            channel = generate_cao_channel(P, l_max, k_max, rng)
            H_true = build_h_eff_integer(N, channel, k_max, l_max, c1, c2)
            data_idx = rng.integers(0, 2, size=N)             # BPSK
            data = BPSK[data_idx]
            bits_true = (data.real < 0).astype(np.float32)    # bits before scaling
            x = np.sqrt(0.5) * pilot + np.sqrt(0.5) * data
            noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
            y = H_true @ x + np.sqrt(sigma2) * noise

            res = cao_isp_receiver(
                y, pilot, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
                P=P, sigma2=sigma2, constellation=BPSK,
                lam=0.5, phi=0.5, sum_betas=1.0,
                basis=basis, max_iter=max_iter, tol=tol)
            d_hat = res['d_hat']
            # Un-scale by √φ then BPSK-slice
            b_hat = bpsk_bits(d_hat / np.sqrt(0.5))
            errs += int((b_hat != bits_true).sum())
            bits_total += N

        ber = errs / max(bits_total, 1)
        elapsed = time.time() - t0
        # Paper reference lookup
        paper_ref = (PAPER_REF_FIG3 if (l_max == 4 and k_max == 4) else
                      PAPER_REF_FIG4 if (l_max == 8 and k_max == 8) else
                      None)
        if paper_ref and snr_db in paper_ref:
            log_diff = np.log10(max(ber, 1e-30)) - np.log10(paper_ref[snr_db])
            tag = ('PASS' if abs(log_diff) <= 0.3 else
                   'WARN' if abs(log_diff) <= 0.6 else 'FAIL')
            print(f"  {snr_db:>4} | {ber:>10.3e}  {errs:>6}/{bits_total:>7}  "
                  f"{paper_ref[snr_db]:>9.1e}  {log_diff:>+8.2f} dec  {tag}  [{elapsed:.0f}s]")
        else:
            print(f"  {snr_db:>4} | {ber:>10.3e}  {errs:>6}/{bits_total:>7}  "
                  f"  —     no ref       [{elapsed:.0f}s]")
        results[str(snr_db)] = dict(ber=ber, errs=errs, bits_total=bits_total,
                                     paper_ref=(paper_ref.get(snr_db) if paper_ref else None),
                                     elapsed_sec=elapsed)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--regime', choices=['fig3', 'fig4'], default='fig3')
    ap.add_argument('--basis',  choices=['ours', 'paper'], default='ours')
    ap.add_argument('--frames', type=int, default=200)
    ap.add_argument('--seed',   type=int, default=20260507)
    ap.add_argument('--snr-list', nargs='+', type=int, default=[8, 10, 12, 14, 16])
    ap.add_argument('--out', type=str, default=None,
                     help='Optional JSON output path')
    args = ap.parse_args()

    if args.regime == 'fig3':
        l_max, k_max = 4, 4
    else:
        l_max, k_max = 8, 8

    print("=" * 70)
    print(f"Cao 2024 ICCT consistency test — Fig {3 if args.regime=='fig3' else 4} regime")
    print(f"  N=512  l_max={l_max}  α_max={k_max}  P=3  BPSK  λ=φ=0.5")
    print(f"  basis={args.basis}  frames={args.frames}/SNR  seed={args.seed}")
    print("=" * 70)

    results = run_consistency(
        N=512, l_max=l_max, k_max=k_max, P=3,
        snr_list=args.snr_list, n_frames=args.frames, seed=args.seed,
        basis=args.basis)

    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(dict(
            regime=args.regime, basis=args.basis, frames=args.frames,
            seed=args.seed, l_max=l_max, k_max=k_max, P=3,
            results=results), indent=2))
        print(f"\n[saved] {out_path}")


if __name__ == '__main__':
    main()
