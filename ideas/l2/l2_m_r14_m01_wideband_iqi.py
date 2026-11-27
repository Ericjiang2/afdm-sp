#!/usr/bin/env python3
"""
Round-14 Authorized Startup-Gate Sample-Size Expansion Wrapper (v2) for Card I-20261126-m01:
Wideband Frequency-Selective Joint Tx+Rx IQI Zero-Preamble Initialization & Recovery in EP-AFDM.

Source & Zero-Modification Invariant (CLAUDE.md D18 & Round-14 §2 Task ②):
  - Imports ALL algorithms, channel models, rivals (Huang / Narasimhan / ablations / gold oracle),
    throughput accounting, and primary verdict logic (`P1_Rivals`, `P1_FloorPersists_5dB`,
    `P2_SingleMech`, `PASS_PRIMARY`) VERBATIM from untouched Round-13 frozen script
    `ideas/l2/l2_m_r13_m01_wideband_iqi.py` (cryptographic MD5 fail-fast verified BEFORE any
    gate execution: `d38c944e9b529ec1ab8f81085db5497a`).
  - Hard-guards `--out` against overwriting Round-13 early-abort artifact
    `ideas/l2/out_m_r13_m01/summary_m_r13_m01.json` (or any file inside `out_m_r13_m01/`).
  - Changes ONLY the authorized random-Rayleigh startup-gate sample sizes & disjoint fresh
    startup-gate seed block (`GATE_SBASE = 2032050000`), keeping EVERY threshold in ALL 5 startup
    gates 100% IDENTICAL to Round-13:
      * G_R1_Huang_Fig4:      n_huang =  24 (UNCHANGED; fresh seeds 2032060000..2032060023)
      * G_R1_Narasimhan_OFDM: n_nar   = 256 (expanded from 16; fresh seeds 2032070000..2032070255;
                              ALL 6 thresholds incl. mobile QPSK 25 dB < 1.0% UNCHANGED;
                              SE / 1-sided 95% bounds logged diagnostically only)
      * G_ZeroIQI_Health:     n_zero  = 128 (expanded from 20 per Round-14 §1.3; fresh seeds
                              2032080000..2032080127; ALL 6 arms' < 1% & < -20 dB UNCHANGED)
  - ALL 640 virgin formal target burst seeds (`2032100000..2032600059`) & `AUX_Timing` (`2032090000`)
    remain 100% BIT-FOR-BIT IDENTICAL to Round-13 `PREDICTIONS_m_r13_m01.md`.
"""
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys, time, json, math, argparse, hashlib
import numpy as np
from multiprocessing import Pool
from scipy.stats import t as student_t

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)
import l2_m_r13_m01_wideband_iqi as m13

FROZEN_R13_MD5 = "d38c944e9b529ec1ab8f81085db5497a"
PROTECTED_R13_DIR = os.path.realpath(os.path.join(THIS_DIR, "out_m_r13_m01"))
PROTECTED_R13_JSON = os.path.realpath(os.path.join(PROTECTED_R13_DIR, "summary_m_r13_m01.json"))


def validate_out_path_not_r13(out_path: str) -> str:
    """Hard guard: refuse any `--out` targeting Round-13 abort artifact or `out_m_r13_m01/`."""
    abs_p = os.path.abspath(out_path)
    real_p = os.path.realpath(abs_p)
    base = os.path.basename(abs_p)
    if (
        base == "summary_m_r13_m01.json"
        or real_p == PROTECTED_R13_JSON
        or real_p == PROTECTED_R13_DIR
        or real_p.startswith(PROTECTED_R13_DIR + os.sep)
        or "out_m_r13_m01" in abs_p.split(os.sep)
    ):
        raise ValueError(
            f"Refusing to overwrite protected Round-13 artifact path: {out_path} (resolved: {real_p})"
        )
    return abs_p


class _GatePoolProxy:
    """Thin parent-process proxy capturing raw `_worker_nar_ofdm` per-frame tuple list
    while forwarding all calls verbatim to `pool.map` with zero code duplication."""
    def __init__(self, pool):
        self._pool = pool
        self.nar_res = None

    def map(self, func, iterable):
        res = self._pool.map(func, iterable)
        if func is m13._worker_nar_ofdm:
            self.nar_res = res
        return res


def run_r14_startup_gates(pool, gate_seed_base=2032050000, n_huang=24, n_nar=256, n_zero=128):
    mod_path = os.path.abspath(m13.__file__)
    with open(mod_path, "rb") as fp:
        actual_md5 = hashlib.md5(fp.read()).hexdigest()
    md5_ok = (actual_md5 == FROZEN_R13_MD5)
    md5_gate = {
        "path": mod_path,
        "expected_md5": FROZEN_R13_MD5,
        "actual_md5": actual_md5,
        "pass": bool(md5_ok),
    }
    # Fail-fast BEFORE touching any startup-gate seed if frozen Round-13 module changed!
    if not md5_ok:
        return {
            "GATES_OK": False,
            "G_Frozen_R13_MD5": md5_gate,
            "aborted_before_gates": True,
        }

    proxy = _GatePoolProxy(pool)
    gates = m13.run_startup_gates(
        proxy,
        seed_base=gate_seed_base,
        n_huang=n_huang,
        n_nar=n_nar,
        n_zero=n_zero,
    )
    nar_res = proxy.nar_res
    assert nar_res is not None and len(nar_res) == n_nar, (
        f"Expected {n_nar} Narasimhan gate rows, got {None if nar_res is None else len(nar_res)}"
    )

    # Diagnostic dispersion logging ONLY — ALL 6 Narasimhan thresholds remain 100% UNCHANGED from m13!
    mob_vals = np.array([r[2] for r in nar_res], dtype=float)
    stat_vals = np.array([r[0] for r in nar_res], dtype=float)
    mob_mean = float(np.mean(mob_vals))
    mob_sd = float(np.std(mob_vals, ddof=1)) if n_nar > 1 else 0.0
    mob_se = float(mob_sd / math.sqrt(n_nar)) if n_nar > 1 else 0.0
    t95_1s = float(student_t.ppf(0.95, df=max(n_nar - 1, 1))) if n_nar > 1 else 0.0
    stat_mean = float(np.mean(stat_vals))
    stat_se = float(np.std(stat_vals, ddof=1) / math.sqrt(n_nar)) if n_nar > 1 else 0.0

    nar_ofdm = gates["G_R1_Narasimhan_OFDM"]
    assert abs(mob_mean - nar_ofdm["ser_mobile005_qpsk25_strong13"]) < 1e-15
    assert abs(stat_mean - nar_ofdm["ser_static_16qam30_strong13"]) < 1e-15
    nar_ofdm["ser_static_16qam30_strong13_se"] = stat_se
    nar_ofdm["ser_mobile005_qpsk25_strong13_sd"] = mob_sd
    nar_ofdm["ser_mobile005_qpsk25_strong13_se"] = mob_se
    nar_ofdm["ser_mobile005_qpsk25_strong13_1s95_lo_diag"] = float(mob_mean - t95_1s * mob_se)
    nar_ofdm["ser_mobile005_qpsk25_strong13_1s95_hi_diag"] = float(mob_mean + t95_1s * mob_se)

    gates["G_Frozen_R13_MD5"] = md5_gate
    gates["G_ZeroIQI_Health"]["n_trials"] = int(n_zero)
    gates["GATES_OK"] = bool(md5_ok and gates["GATES_OK"])
    return gates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    if args.out is None:
        args.out = ("/data/guoyikun/tmp/funnel_m_r14/smoke_m_r14_m01.json" if args.smoke
                    else "/data/guoyikun/tmp/funnel_m_r14/summary_m_r14_m01.json")
    out_abs = validate_out_path_not_r13(args.out)

    print(f"Python: {sys.executable}", flush=True)
    t0 = time.perf_counter()

    # Exact physical L_cpp = 8 accounting (verbatim formula from frozen m13)
    N, Nd, L_cpp, xp_pow, K = 256, 161, 8, 50.0, 4
    A_acc = m13.daft_matrix(N, 7.0 / (2 * N), 1.0 / (2 * np.sqrt(2) * N))
    xp1_acc, xp2_acc = m13.build_narasimhan_scheme_a_preambles(N)
    nar_pfx_e = float(
        np.sum(np.abs((A_acc.conj().T @ xp1_acc)[-L_cpp:]) ** 2)
        + np.sum(np.abs((A_acc.conj().T @ xp2_acc)[-L_cpp:]) ** 2)
    )
    cu_prop = K * (N + L_cpp); cu_huang = (K + 1) * (N + L_cpp); cu_nar = (K + 2) * (N + L_cpp)
    e_prop_pfx = K * (Nd + xp_pow) * (N + L_cpp) / float(N)
    e_huang_pfx = e_prop_pfx + (N + L_cpp)
    e_nar_pfx = e_prop_pfx + 2 * N + nar_pfx_e
    eb_delta_huang = 10.0 * math.log10(e_huang_pfx / e_prop_pfx)  # +1.1505 dB
    eb_delta_nar = 10.0 * math.log10(e_nar_pfx / e_prop_pfx)      # +2.1466 dB
    throughput_accounting = {
        "N": N, "Nd": Nd, "guard_plus_pilot": N - Nd, "xp_pow": xp_pow, "L_cpp": L_cpp, "K_burst": K,
        "prop_net_sym_per_cu": (K * Nd) / cu_prop,
        "huang_net_sym_per_cu": (K * Nd) / cu_huang,
        "narasimhan_net_sym_per_cu": (K * Nd) / cu_nar,
        "prop_eq_net_thru_sym_per_cu": (K * 129) / cu_prop,
        "prop_spectral_eff_gain_vs_huang": cu_huang / cu_prop,
        "nar_two_preambles_cpp_energy": nar_pfx_e,
        "huang_excess_eb_db": eb_delta_huang,
        "narasimhan_excess_eb_db_with_prefix": eb_delta_nar,
    }

    if args.smoke:
        n_huang, n_nar, n_zero = 12, 64, 8
        n_r1, n_r2, n_scope = 8, 16, 8
        SBASE = 2122000000
        GATE_SBASE = 2122050000
    else:
        n_huang, n_nar, n_zero = 24, 256, 128
        n_r1, n_r2, n_scope = 60, 340, 60
        SBASE = 2032000000       # UNCHANGED untouched virgin formal target seeds 2032100000..2032600059 & 2032090000!
        GATE_SBASE = 2032050000  # Fresh disjoint startup-gate block (2032050001..2032080127), zero overlap with R13!

    seed_meta = {
        "gate_seed_base": GATE_SBASE,
        "target_seed_base": SBASE,
        "n_huang_gate": n_huang,
        "n_nar_gate": n_nar,
        "n_zero_gate": n_zero,
        "frozen_r13_script": "l2_m_r13_m01_wideband_iqi.py",
        "frozen_r13_md5_expected": FROZEN_R13_MD5,
        "preserved_r13_abort_summary": "ideas/l2/out_m_r13_m01/summary_m_r13_m01.json",
    }

    with Pool(min(args.workers, 8)) as pool:
        print(f"\n[1/7] Running R14 Startup Gates (GATE_SBASE={GATE_SBASE}, n_huang={n_huang}, n_nar={n_nar}, n_zero={n_zero})...", flush=True)
        gates = run_r14_startup_gates(pool, gate_seed_base=GATE_SBASE, n_huang=n_huang, n_nar=n_nar, n_zero=n_zero)
        if gates.get("aborted_before_gates", False):
            print("  FATAL: Frozen R13 MD5 mismatch — aborting BEFORE running any startup gates!", flush=True)
        else:
            nar_g = gates["G_R1_Narasimhan_OFDM"]
            print(
                f"  GATES_OK = {gates['GATES_OK']} | MD5_OK = {gates['G_Frozen_R13_MD5']['pass']} | "
                f"Huang Fig4 BER={gates['G_R1_Huang_Fig4']['fig4_ber_huang_comp']:.4e} vs noIQ={gates['G_R1_Huang_Fig4']['fig4_ber_no_iqimb']:.4e} | "
                f"Nar OFDM stat={nar_g['ser_static_16qam30_strong13']:.4e}, mob={nar_g['ser_mobile005_qpsk25_strong13']:.4e} "
                f"(se={nar_g['ser_mobile005_qpsk25_strong13_se']:.4e})",
                flush=True,
            )

        if not gates["GATES_OK"]:
            print("  ABORTING BEFORE FORMAL TARGET SEEDS: GATES_OK == False!", flush=True)
            summary = {
                "script": os.path.basename(__file__), "python": sys.executable, "smoke": bool(args.smoke),
                "seed_meta": seed_meta, "elapsed_s": float(time.perf_counter() - t0),
                "throughput_accounting": throughput_accounting,
                "verdicts": {"GATES_OK": False, "P1_Rivals": False, "P1_FloorPersists_5dB": False, "P2_SingleMech": False, "PASS_PRIMARY": False},
                "gates": gates,
            }
            os.makedirs(os.path.dirname(out_abs), exist_ok=True)
            with open(out_abs, "w") as f:
                json.dump(summary, f, indent=2, allow_nan=False)
            return

        print(f"\n[2/7] Running R1_Mod18_30dB (n={n_r1}, virgin seeds {SBASE+100000}+, with burst-paired zero-IQI decomp)...", flush=True)
        r1_30 = m13.summarize_regime(pool.map(m13._worker_burst, [(SBASE + 100000 + i, "mod18", 64, 30.0, False, False, 0.0, 0.0, None, True) for i in range(n_r1)]), 20.0, False)
        print(f"  R1_30: huang={r1_30['mean_ser']['huang_blind']:.4e} (zeroIQI={r1_30['Paired_ZeroIQI_Decomp']['huang_zero_iqi_ser']:.4e}), nar={r1_30['mean_ser']['narasimhan_b2']:.4e} (zeroIQI={r1_30['Paired_ZeroIQI_Decomp']['narasimhan_zero_iqi_ser']:.4e}), prop={r1_30['mean_ser']['prop_full']:.4e}, both_pass={r1_30['P1_both_formal_rivals_pass']}", flush=True)

        print(f"\n[3/7] Running R1_Mod18_35dB (n={n_r1}, virgin seeds {SBASE+200000}+, with burst-paired zero-IQI decomp)...", flush=True)
        r1_35 = m13.summarize_regime(pool.map(m13._worker_burst, [(SBASE + 200000 + i, "mod18", 64, 35.0, False, False, 0.0, 0.0, None, True) for i in range(n_r1)]), 20.0, False)
        print(f"  R1_35: huang={r1_35['mean_ser']['huang_blind']:.4e} (zeroIQI={r1_35['Paired_ZeroIQI_Decomp']['huang_zero_iqi_ser']:.4e}), nar={r1_35['mean_ser']['narasimhan_b2']:.4e}, prop={r1_35['mean_ser']['prop_full']:.4e}, both_pass={r1_35['P1_both_formal_rivals_pass']}", flush=True)

        print(f"\n[4/7] Running R2_Strong13_32dB (n={n_r2}, virgin seeds {SBASE+300000}+, full zero-confounder ablations)...", flush=True)
        r2 = m13.summarize_regime(pool.map(m13._worker_burst, [(SBASE + 300000 + i, "strong13", 64, 32.0, False, True, 0.0, 0.0, None, False) for i in range(n_r2)]), 20.0, True)
        p2a = r2["P2a_PureU0_StrictZeroHDiff"]; p2b = r2["P2b_FullNullInit_Package"]
        print(f"  R2_32: huang={r2['mean_ser']['huang_blind']:.4e}, nar={r2['mean_ser']['narasimhan_b2']:.4e}, z0={r2['mean_ser']['zero_u0_same_sig2']:.4e}, u0_only={r2['mean_ser']['prop_u0_only']:.4e}, prop={r2['mean_ser']['prop_full']:.4e}, gold={r2['mean_ser']['oracle_phys_gold']:.4e}", flush=True)
        print(f"  P2a PureU0   : z0={p2a['fail_count_zero_u0']}/{n_r2} vs u0={p2a['fail_count_u0_only']}/{n_r2}, Tango=[{p2a['ci_lo']*100:.2f},{p2a['ci_hi']*100:.2f}]pp, hw_frac={p2a['hw_frac_vs_5pp']}", flush=True)
        print(f"  P2b FullInit : z0={p2b['fail_count_zero_u0']}/{n_r2} vs pf={p2b['fail_count_prop_full']}/{n_r2}, Tango=[{p2b['ci_lo']*100:.2f},{p2b['ci_hi']*100:.2f}]pp, hw_frac={p2b['hw_frac_vs_10pp']}", flush=True)

        print(f"\n[5/7] Running Non-Gating Scope Readouts (ContDoppler + Equal-Eb/N0 + Equal-Net-Thru, n={n_scope})...", flush=True)
        sc_cd = m13.summarize_regime(pool.map(m13._worker_burst, [(SBASE + 400000 + i, "strong13", 16, 28.0, True, False, 0.0, 0.0, None, False) for i in range(n_scope)]), 5.0, False)
        sc_eq_eb = m13.summarize_regime(pool.map(m13._worker_burst, [(SBASE + 500000 + i, "mod18", 64, 30.0, False, False, -eb_delta_huang, -eb_delta_nar, None, False) for i in range(n_scope)]), 20.0, False)
        sc_eq_th = m13.summarize_regime(pool.map(m13._worker_burst, [(SBASE + 600000 + i, "mod18", 64, 30.0, False, False, 0.0, 0.0, 63, False) for i in range(n_scope)]), 20.0, False)

    print("\n[6/7] Running Non-Gating Auxiliary Vectorized+Cached Banded Timing (1-core)...", flush=True)
    aux_timing = m13.run_aux_timing(SBASE + 90000)

    floor_persists = bool(r1_35["mean_ser"]["huang_blind"] >= 0.5 * r1_30["mean_ser"]["huang_blind"])
    p1_rivals_ok = bool(
        r1_30["P1_both_formal_rivals_pass"]
        and r1_35["P1_both_formal_rivals_pass"]
        and r2["P1_both_formal_rivals_pass"]
        and floor_persists
    )
    p2_singlemech_ok = bool(r2["P2_SingleMech_PASS"])
    pass_primary = bool(gates["GATES_OK"] and p1_rivals_ok and p2_singlemech_ok)

    summary = {
        "script": os.path.basename(__file__), "python": sys.executable, "smoke": bool(args.smoke),
        "seed_meta": seed_meta, "elapsed_s": float(time.perf_counter() - t0),
        "throughput_accounting": throughput_accounting,
        "verdicts": {
            "GATES_OK": gates["GATES_OK"], "P1_Rivals": p1_rivals_ok,
            "P1_FloorPersists_5dB": floor_persists, "P2_SingleMech": p2_singlemech_ok,
            "PASS_PRIMARY": pass_primary,
        },
        "gates": gates, "R1_Mod18_30dB": r1_30, "R1_Mod18_35dB": r1_35, "R2_Strong13_32dB": r2,
        "SCOPE_ContDoppler_16QAM_28dB": sc_cd, "SCOPE_EqualEbN0_Mod18_30dB": sc_eq_eb,
        "SCOPE_EqualNetThru_Mod18_30dB": sc_eq_th, "AUX_Timing_1core": aux_timing,
    }
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    with open(out_abs, "w") as f:
        json.dump(summary, f, indent=2, allow_nan=False)
    with open(out_abs, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    print(f"\n[7/7] === DONE in {summary['elapsed_s']:.1f}s | PASS_PRIMARY={pass_primary} | MD5={md5} ===", flush=True)
    print(json.dumps(summary["verdicts"], indent=2), flush=True)


if __name__ == "__main__":
    main()
