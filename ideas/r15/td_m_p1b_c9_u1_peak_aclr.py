#!/usr/bin/env python3
"""
Round 15 Phase 1B — Candidate C9 Wildcard U1 Fast Teardown (`td_m_p1b_c9_u1_peak_aclr.py`):
Joint Hard Peak-Amplitude (`|s_os[n]| <= V_sat`, PAPR ~ 3 dB) + Strict Out-of-Band Spectral Mask
(`ACLR <= -40 dB` evaluated on oversampled TX output!) + Low TX EVM (<= 8%) for 64-QAM AFDM / OTFS.

Sol Call 2 C9 Prescription:
  - Test pre-factorized, over-relaxed, warm-started ADMM + safeguarded Anderson(m=3) vs Armstrong ICF
    at SAME CPU wall-clock latency (6-8 iters vs 200 iters converged Oracle!), measuring BOTH constraint pass rate
    (peak <= V_sat AND ACLR <= -40 dB AND EVM <= 8%) AND exact 99th-percentile CPU latency (ms)!
  - Also test `Steelman_S`: DFT-s-OFDM / SC-FDE (naturally lower PAPR + pulse shaping) at equal net rate & BW!
"""
import argparse
import json
import math
import os
import time

import numpy as np
from scipy.fft import fft, ifft


def gray_qam(M: int) -> np.ndarray:
    ms = int(round(math.sqrt(M)))
    b = np.arange(ms); g = b ^ (b >> 1); lut = np.argsort(g); lv = 2 * lut - (ms - 1)
    pts = np.array([lv[i] + 1j * lv[q] for q in range(ms) for i in range(ms)], dtype=np.complex128)
    return pts / math.sqrt(float(np.mean(np.abs(pts) ** 2)))


def daft_mat(N: int, c1: float, c2: float) -> np.ndarray:
    n = np.arange(N, dtype=float); m = np.arange(N, dtype=float)
    W = np.exp(-1j * 2.0 * np.pi * np.outer(m, n) / N) / math.sqrt(N)
    return (np.exp(-1j * 2.0 * np.pi * c2 * (m ** 2))[:, None] * W) * np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))[None, :]


def eval_metrics(s_os: np.ndarray, s_ref_inband_f: np.ndarray, in_mask: np.ndarray, oob_mask: np.ndarray, V_sat: float):
    """Exact oversampled metrics: Peak amplitude, OOB ACLR (dB), and In-band TX EVM (%)."""
    peak = float(np.max(np.abs(s_os)))
    S_f = fft(s_os) / math.sqrt(len(s_os))
    p_in = float(np.sum(np.abs(S_f[in_mask]) ** 2))
    p_oob = float(np.sum(np.abs(S_f[oob_mask]) ** 2))
    aclr_db = 10.0 * math.log10(max(p_oob, 1e-18) / max(p_in, 1e-18))
    # Optimal scalar gain alpha minimizing EVM to reference in-band spectrum
    alpha = np.vdot(s_ref_inband_f[in_mask], S_f[in_mask]) / max(float(np.sum(np.abs(s_ref_inband_f[in_mask]) ** 2)), 1e-12)
    err_in = float(np.sum(np.abs(S_f[in_mask] - alpha * s_ref_inband_f[in_mask]) ** 2))
    evm_pct = 100.0 * math.sqrt(err_in / max(float(np.sum(np.abs(alpha * s_ref_inband_f[in_mask]) ** 2)), 1e-12))
    papr_db = 10.0 * math.log10(max(peak ** 2, 1e-18) / max(float(np.mean(np.abs(s_os) ** 2)), 1e-18))
    return {"peak": peak, "papr_db": papr_db, "aclr_db": aclr_db, "evm_pct": evm_pct, "p_in": p_in}


def solve_admm_peak_aclr(s0_os, in_mask, oob_mask, V_sat, aclr_target_db, n_iters, rho=1.5, relax=1.6, anderson=False):
    """
    Pre-factorized Over-Relaxed ADMM (exact O(M log M) FFT per step!) solving:
      min_s  0.5 ||P_in (F s - F s0)||^2   s.t.  |s[n]| <= V_sat  AND  ||P_oob F s||^2 <= eps_oob * ||P_in F s0||^2
    Note: Exact closed-form projections onto BOTH time-domain amplitude ball AND freq-domain OOB Euclidean ball!
    """
    t0 = time.perf_counter()
    M = len(s0_os)
    S0_f = fft(s0_os) / math.sqrt(M)
    p_in0 = float(np.sum(np.abs(S0_f[in_mask]) ** 2))
    # Target OOB norm radius (with 1.5 dB safety margin for -40 dB)
    rad_oob = math.sqrt(p_in0 * (10.0 ** ((aclr_target_db - 1.0) / 10.0)))

    # Splitting: s (time peak-constrained) = z (freq OOB-constrained + inband fidelity)
    # Wait: s-update = projection onto |s| <= V_sat (closed-form!)
    # z-update = min_z 0.5 ||P_in(Fz - S0)||^2 + (rho/2) ||Fz - F(s+u)||^2  s.t. ||P_oob Fz|| <= rad_oob (closed-form in F-domain!)
    s = s0_os.copy()
    z = s0_os.copy()
    u = np.zeros(M, dtype=np.complex128)
    g_hist, f_hist = [], []

    for it in range(n_iters):
        # s-update: hard time-domain clip |s| <= V_sat
        v_s = z - u
        mag = np.abs(v_s)
        s = np.where(mag > V_sat, v_s * (V_sat / np.maximum(mag, 1e-12)), v_s)

        # Over-relaxation
        s_hat = relax * s + (1.0 - relax) * z

        # z-update in FFT domain (exact closed-form!)
        V_f = fft(s_hat + u) / math.sqrt(M)
        Z_f = V_f.copy()
        Z_f[in_mask] = (S0_f[in_mask] + rho * V_f[in_mask]) / (1.0 + rho)
        oob_norm = float(np.linalg.norm(Z_f[oob_mask]))
        if oob_norm > rad_oob:
            Z_f[oob_mask] *= (rad_oob / oob_norm)
        z_new = ifft(Z_f) * math.sqrt(M)

        u_new = u + (s_hat - z_new)

        if anderson:
            cur = np.concatenate([z, u])
            nxt = np.concatenate([z_new, u_new])
            fv = nxt - cur
            g_hist.append(nxt); f_hist.append(fv)
            if len(g_hist) > 5:
                g_hist.pop(0); f_hist.pop(0)
            m = min(len(f_hist) - 1, 3)
            if m > 0:
                dF = np.column_stack([f_hist[-m + j] - f_hist[-m + j - 1] for j in range(m)])
                dG = np.column_stack([g_hist[-m + j] - g_hist[-m + j - 1] for j in range(m)])
                try:
                    gam = np.linalg.solve(dF.conj().T @ dF + 1e-6 * np.eye(m), dF.conj().T @ fv)
                    cand = nxt - dG @ gam
                    if np.linalg.norm(cand - cur) <= 2.5 * np.linalg.norm(fv) + 1e-8:
                        z_new, u_new = cand[:M], cand[M:]
                except np.linalg.LinAlgError:
                    pass
        z, u = z_new, u_new

    # Final projection onto strict peak cap |s| <= V_sat (physical PA ceiling!)
    mag = np.abs(s)
    s_out = np.where(mag > V_sat, s * (V_sat / np.maximum(mag, 1e-12)), s)
    return s_out, (time.perf_counter() - t0) * 1000.0


def solve_icf(s0_os, in_mask, oob_mask, V_sat, n_iters):
    """Textbook Armstrong Iterative Clipping & Filtering (ICF)."""
    t0 = time.perf_counter()
    M = len(s0_os)
    s = s0_os.copy()
    for _ in range(n_iters):
        mag = np.abs(s)
        s = np.where(mag > V_sat, s * (V_sat / np.maximum(mag, 1e-12)), s)
        Sf = fft(s) / math.sqrt(M)
        Sf[oob_mask] = 0.0
        s = ifft(Sf) * math.sqrt(M)
    # Physical clip at PA input (note: re-clipping regrows OOB!)
    mag = np.abs(s)
    s_out = np.where(mag > V_sat, s * (V_sat / np.maximum(mag, 1e-12)), s)
    return s_out, (time.perf_counter() - t0) * 1000.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=40)
    ap.add_argument("--out", type=str, default="ideas/r15/out_p1b_c9_u1_peak_aclr.json")
    args = ap.parse_args()

    const = gray_qam(64)
    N = 128; Q_os = 4; M = N * Q_os
    U_afdm = daft_mat(N, 5.0 / (2.0 * N), 1.0 / (2.0 * math.pi * N))
    # Main band = N bins ([-N/2..N/2-1]), Guard = 4 bins each side, OOB = remaining bins
    in_mask = np.zeros(M, dtype=bool)
    in_mask[: N // 2] = True; in_mask[M - N // 2 :] = True
    oob_mask = np.ones(M, dtype=bool)
    oob_mask[: N // 2 + 4] = False; oob_mask[M - N // 2 - 4 :] = False

    results = {}
    for wf in ["AFDM", "SC-FDE"]:
        for papr_cap_db in [3.5, 2.5]:
            V_sat = 10.0 ** (papr_cap_db / 20.0)
            key = f"{wf}_PAPRcap{papr_cap_db}dB_ACLRm40"
            arms = {
                "Pub_ICF_3": [], "SM_ICF_8": [], "SM_ADMM_6": [], "SM_ADMM_8": [],
                "SM_ADMM_AA3_8": [], "Oracle_ADMM_200": [],
            }
            for t in range(args.trials):
                rng = np.random.default_rng(900000 + t)
                x = const[rng.integers(0, len(const), size=N)]
                s_base = (U_afdm.conj().T @ x) if wf == "AFDM" else x
                # Oversampled bandlimited reference waveform (unit RMS!)
                S_f = np.zeros(M, dtype=np.complex128)
                X_f = fft(s_base) / math.sqrt(N)
                S_f[: N // 2] = X_f[: N // 2]
                S_f[M - N // 2 :] = X_f[N // 2 :]
                s0_os = ifft(S_f) * math.sqrt(M)
                s0_os /= math.sqrt(float(np.mean(np.abs(s0_os) ** 2)))
                S0_ref = fft(s0_os) / math.sqrt(M)

                for aname, fn in [
                    ("Pub_ICF_3", lambda: solve_icf(s0_os, in_mask, oob_mask, V_sat, 3)),
                    ("SM_ICF_8", lambda: solve_icf(s0_os, in_mask, oob_mask, V_sat, 8)),
                    ("SM_ADMM_6", lambda: solve_admm_peak_aclr(s0_os, in_mask, oob_mask, V_sat, -40.0, 6, 1.5, 1.6, False)),
                    ("SM_ADMM_8", lambda: solve_admm_peak_aclr(s0_os, in_mask, oob_mask, V_sat, -40.0, 8, 1.5, 1.6, False)),
                    ("SM_ADMM_AA3_8", lambda: solve_admm_peak_aclr(s0_os, in_mask, oob_mask, V_sat, -40.0, 8, 1.5, 1.6, True)),
                    ("Oracle_ADMM_200", lambda: solve_admm_peak_aclr(s0_os, in_mask, oob_mask, V_sat, -40.0, 200, 1.5, 1.6, False)),
                ]:
                    s_out, ms = fn()
                    m = eval_metrics(s_out, S0_ref, in_mask, oob_mask, V_sat)
                    m["ms"] = ms
                    m["pass_all"] = (m["aclr_db"] <= -40.0 and m["evm_pct"] <= 8.0 and m["peak"] <= V_sat + 1e-6)
                    arms[aname].append(m)

            agg = {}
            print(f"\n=== {key} (n={args.trials}) ===")
            for aname, lst in arms.items():
                agg[aname] = {
                    "aclr_db": float(np.mean([x["aclr_db"] for x in lst])),
                    "evm_pct": float(np.mean([x["evm_pct"] for x in lst])),
                    "pass_rate": float(np.mean([x["pass_all"] for x in lst])),
                    "ms_mean": float(np.mean([x["ms"] for x in lst])),
                    "ms_p99": float(np.percentile([x["ms"] for x in lst], 99)),
                }
                v = agg[aname]
                print(f"  {aname:18s}: ACLR={v['aclr_db']:6.2f} dB | EVM={v['evm_pct']:5.2f}% | Pass={v['pass_rate']*100:5.1f}% | {v['ms_mean']:.3f} ms (p99 {v['ms_p99']:.3f} ms)")
            results[key] = agg

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
