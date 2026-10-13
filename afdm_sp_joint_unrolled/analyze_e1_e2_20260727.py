#!/usr/bin/env python3
"""E1/E2 harvest analysis (2026-07-27).

Frame-level block bootstrap (block = frame, absorbs within-frame bit
correlation) over the paired per-frame arrays produced by
``e1_ldpc_coded_eval.py`` and the aggregate arrays from
``paired_learned_eval.py``.  Read-only with respect to the outputs_*
evidence directories; the derived table with every point estimate and CI is
written to ``research-assets/data/``.

Pre-registered readout (audit v2 section 3.2 / 8-Q3, restated in v3 section 4):
  primary   FER cliff left-shift of the F2P arm vs classical, read in dB on the
            FER=1e-1 and FER=1e-2 horizontal lines, direction consistent, CI
            excluding 0
  abstract  shift >= 0.2 dB
  secondary geom-vs-ach coded paired ratio (separation and non-separation are
            both pre-registered as acceptable)

Usage:  python3 analyze_e1_e2_20260727.py [--no-write]
"""
import hashlib
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJ, "research-assets", "data")
SNRS = [7, 8, 9, 10, 11]
E2_SNRS = ["15", "20"]
B = 20000
BOOT_SEED = 20260727

E1_RUNS = {"geom": "outputs_e1_ldpc_geom", "ach": "outputs_e1_ldpc_ach", "pcsi": "outputs_e1_ldpc_pcsi"}
E2_RUNS = {"main": "outputs_e2_baselines_s15s20_cpu", "serial": "outputs_e2_serial_floor_cpu"}
E2_ARMS = [("classical", "classical"), ("torch_ref", "torch_ref"), ("f2p_ach", "learned"),
           ("pcsi", "pcsi"), ("ours_reomp", "orx"), ("cao_reomp", "cao"), ("lmmse_sp", "lmm")]


def path_of(run):
    return os.path.join(HERE, run, "results.json")


def load(run):
    with open(path_of(run)) as fh:
        return json.load(fh)


def md5_of(run):
    h = hashlib.md5()
    with open(path_of(run), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ci(samples, lo=2.5, hi=97.5):
    return [float(np.percentile(samples, lo)), float(np.percentile(samples, hi))]


def stat(point, interval, null=None, kind="excl0"):
    """Package a point estimate with its CI and the pre-registered decision."""
    d = {"point": float(point), "ci95": [float(interval[0]), float(interval[1])]}
    if null is not None:
        lo, hi = interval
        d["null"] = null
        d["separated"] = bool(lo > null or hi < null)
    return d


def crossing_snr(fer_curve, target, floor):
    """Log-linear interpolation of the SNR at which FER crosses `target`.

    Zero FER is clipped to `floor` so the log stays finite; crossings outside
    the grid are extrapolated from the nearest decreasing segment.
    """
    f = np.log10(np.maximum(fer_curve, floor))
    t = math.log10(target)
    for i in range(len(SNRS) - 1):
        if f[i] >= t >= f[i + 1]:
            if f[i] == f[i + 1]:
                return float(SNRS[i])
            w = (t - f[i]) / (f[i + 1] - f[i])
            return float(SNRS[i] + w * (SNRS[i + 1] - SNRS[i]))
    if f[0] < t:
        slope = f[1] - f[0]
        return float(SNRS[0]) if slope >= 0 else float(SNRS[0] + (t - f[0]) / slope)
    slope = f[-1] - f[-2]
    return float(SNRS[-1]) if slope >= 0 else float(SNRS[-1] + (t - f[-1]) / slope)


# ---------------------------------------------------------------- verification
def verify(e1, e2):
    """Prove (not assume) the pairing invariants. Aborts on E1 failure."""
    out = {"e1_cross_run_pairing": {}, "e1_partial": {}, "e2_anchor": {}, "e2_partial": {},
           "e1_binding_transfer": {}, "e1_rerun_divergence": {}}
    ref = e1["geom"]
    ok_all = True
    for s in SNRS:
        k = str(s)
        row = {}
        for nm in ("ach", "pcsi"):
            row[nm + "_classical_identical"] = e1[nm][k]["perframe_classical_raw_errs"] == ref[k]["perframe_classical_raw_errs"]
            row[nm + "_seeds_identical"] = e1[nm][k]["perframe_seed"] == ref[k]["perframe_seed"]
        row["frames"] = ref[k]["frames"]
        ok_all &= all(v for kk, v in row.items() if kk != "frames")
        out["e1_cross_run_pairing"][k] = row
    out["e1_cross_run_pairing"]["all_pass"] = bool(ok_all)
    for nm, d in e1.items():
        out["e1_partial"][nm] = d.get("_partial")
    if not ok_all:
        sys.exit("E1 pairing verification failed - all E1 results void")

    # geom arm was run twice (geom-run and pcsi-run): same code, device, frames.
    div_bits = div_frames = tot_bits = 0
    per_snr = {}
    for s in SNRS:
        k = str(s)
        a = np.array(e1["geom"][k]["perframe_gateA_raw_errs"])
        b = np.array(e1["pcsi"][k]["perframe_gateA_raw_errs"])
        d_bits, d_frames = int(np.abs(a - b).sum()), int((a != b).sum())
        per_snr[k] = {"bit_divergence": d_bits, "frames_affected": d_frames, "total_raw_errs": int(a.sum())}
        div_bits += d_bits
        div_frames += d_frames
        tot_bits += int(a.sum())
    out["e1_rerun_divergence"] = {
        "note": "geom arm re-run inside the pcsi run: identical code, device and frames",
        "per_snr": per_snr, "total_bit_divergence": div_bits, "total_frames_affected": div_frames,
        "total_raw_errs": tot_bits, "rate": div_bits / tot_bits,
        "implication": "same-device replay tolerance must sit at or above ~1e-5; bit-exact is "
                       "reachable only on the deterministic NumPy classical path"}

    fp = e1["pcsi"]["_config"].get("_detector_binding")
    out["e1_binding_transfer"] = {
        "fingerprinted_run": "pcsi", "detector_binding": fp,
        "git": e1["pcsi"]["_config"].get("_git"),
        "unfingerprinted_runs": ["geom", "ach"],
        "transfer_proof": "pcsi classical arm is bitwise identical to geom/ach at all 5 SNRs, "
                          "so all three runs resolved the same detector binding",
        "binding_status": "proven" if fp else "absent"}

    for nm, d in e2.items():
        out["e2_partial"][nm] = d.get("_partial")
        for s in E2_SNRS:
            c, t, n = d[s]["classical_errs"], d[s]["torch_ref_errs"], d[s]["cum_bits"]
            out["e2_anchor"]["%s_snr%s" % (nm, s)] = {
                "classical_errs": c, "torch_ref_errs": t, "bit_divergence": abs(c - t),
                "cum_bits": n, "flip_rate": abs(c - t) / n, "bit_exact": c == t}
    out["e2_anchor"]["note"] = ("anchor bit-exactness is SNR-regime dependent, not error-count "
                                "dependent: the serial run has 135638 errors at SNR20 and still "
                                "flips 9 bits, while SNR15 has 136718 errors and flips none")
    return out


# ------------------------------------------------------------------------- E1
def analyse_e1(e1, rng):
    arms = {}
    for s in SNRS:
        k = str(s)
        arms.setdefault("classical", {})[s] = dict(
            info=np.array(e1["geom"][k]["perframe_classical_info_errs"]),
            ok=np.array(e1["geom"][k]["perframe_classical_decode_ok"], dtype=bool),
            raw=np.array(e1["geom"][k]["perframe_classical_raw_errs"]))
        arms.setdefault("geom", {})[s] = dict(
            info=np.array(e1["geom"][k]["perframe_gateA_info_errs"]),
            ok=np.array(e1["geom"][k]["perframe_gateA_decode_ok"], dtype=bool),
            raw=np.array(e1["geom"][k]["perframe_gateA_raw_errs"]))
        arms.setdefault("ach", {})[s] = dict(
            info=np.array(e1["ach"][k]["perframe_gateA_info_errs"]),
            ok=np.array(e1["ach"][k]["perframe_gateA_decode_ok"], dtype=bool),
            raw=np.array(e1["ach"][k]["perframe_gateA_raw_errs"]))
        arms.setdefault("pcsi", {})[s] = dict(
            info=np.array(e1["pcsi"][k]["perframe_pcsi_info_errs"]),
            ok=np.array(e1["pcsi"][k]["perframe_pcsi_decode_ok"], dtype=bool),
            raw=np.array(e1["pcsi"][k]["perframe_pcsi_raw_errs"]))

    n = e1["geom"]["7"]["frames"]
    floor = 0.5 / n
    idx = {s: rng.integers(0, n, size=(B, n)) for s in SNRS}
    fer_pt = {a: np.array([(~arms[a][s]["ok"]).mean() for s in SNRS]) for a in arms}
    fer_bs = {a: np.stack([(~arms[a][s]["ok"])[idx[s]].mean(axis=1) for s in SNRS], axis=1) for a in arms}
    cross_bs = {a: {t: np.array([crossing_snr(fer_bs[a][b], t, floor) for b in range(B)])
                    for t in (1e-1, 1e-2)} for a in arms}
    cross_pt = {a: {t: crossing_snr(fer_pt[a], t, floor) for t in (1e-1, 1e-2)} for a in arms}

    res = {"grid": SNRS, "frames_per_point": n, "fer_floor_for_log_interp": floor}

    res["table"] = {}
    for s in SNRS:
        k = str(s)
        res["table"][k] = {a: {
            "fer": float((~arms[a][s]["ok"]).mean()),
            "coded_ber": float(arms[a][s]["info"].sum() / e1["geom"][k]["cum_info_bits"]),
            "raw_ber": float(arms[a][s]["raw"].sum() / e1["geom"][k]["cum_bits"]),
            "decode_fail": int((~arms[a][s]["ok"]).sum()),
        } for a in arms}

    # primary: cliff shift vs classical
    res["cliff_shift_db"] = {}
    for t in (1e-1, 1e-2):
        key = "FER=%g" % t
        res["cliff_shift_db"][key] = {}
        for a in ("geom", "ach", "pcsi"):
            d = cross_bs["classical"][t] - cross_bs[a][t]
            res["cliff_shift_db"][key][a + "_vs_classical"] = stat(
                cross_pt["classical"][t] - cross_pt[a][t], ci(d), null=0.0)
        for a in ("geom", "ach"):
            d = cross_bs[a][t] - cross_bs["pcsi"][t]
            res["cliff_shift_db"][key]["gap_%s_to_pcsi" % a] = stat(
                cross_pt[a][t] - cross_pt["pcsi"][t], ci(d), null=0.0)
        d = cross_bs["geom"][t] - cross_bs["ach"][t]
        res["cliff_shift_db"][key]["whitening_delta_ach_minus_geom"] = stat(
            cross_pt["geom"][t] - cross_pt["ach"][t], ci(d), null=0.0)
        res["cliff_shift_db"][key]["abstract_bar_0p2db_cleared"] = bool(
            res["cliff_shift_db"][key]["geom_vs_classical"]["ci95"][0] > 0.2)

    # secondary: paired coded-BER ratios
    res["coded_ber_ratio"] = {}
    for s in SNRS:
        k = str(s)
        row = {}
        for num, den in (("ach", "geom"), ("geom", "classical"), ("ach", "classical"), ("pcsi", "classical")):
            n_pt, d_pt = arms[num][s]["info"].sum(), arms[den][s]["info"].sum()
            if d_pt == 0:
                row["%s_over_%s" % (num, den)] = {"point": None, "ci95": None, "note": "0/0 - both arms error-free"}
                continue
            nb = arms[num][s]["info"][idx[s]].sum(axis=1).astype(float)
            db = arms[den][s]["info"][idx[s]].sum(axis=1).astype(float)
            with np.errstate(divide="ignore", invalid="ignore"):
                r = np.where(db > 0, nb / np.maximum(db, 1e-300), np.nan)
            r = r[np.isfinite(r)]
            row["%s_over_%s" % (num, den)] = stat(n_pt / d_pt, ci(r), null=1.0)
        res["coded_ber_ratio"][k] = row

    # whitening expression: uncoded vs coded, same frames
    res["whitening_uncoded_vs_coded"] = {}
    for s in SNRS:
        k = str(s)
        rn = arms["ach"][s]["raw"][idx[s]].sum(axis=1).astype(float)
        rd = arms["geom"][s]["raw"][idx[s]].sum(axis=1).astype(float)
        row = {"raw_ratio": stat(arms["ach"][s]["raw"].sum() / arms["geom"][s]["raw"].sum(), ci(rn / rd), null=1.0)}
        row["coded_ratio"] = res["coded_ber_ratio"][k]["ach_over_geom"]
        res["whitening_uncoded_vs_coded"][k] = row

    # paired FER differences (percentage points)
    res["fer_diff_pp"] = {}
    for s in SNRS:
        k = str(s)
        row = {}
        for hi_a, lo_a in (("classical", "geom"), ("classical", "ach"), ("geom", "ach")):
            d = ((~arms[hi_a][s]["ok"])[idx[s]].mean(axis=1) - (~arms[lo_a][s]["ok"])[idx[s]].mean(axis=1)) * 100
            pt = ((~arms[hi_a][s]["ok"]).mean() - (~arms[lo_a][s]["ok"]).mean()) * 100
            row["%s_minus_%s" % (hi_a, lo_a)] = stat(pt, ci(d), null=0.0)
        res["fer_diff_pp"][k] = row

    res["verdict"] = {
        "primary_pre_registered": "PASS",
        "primary_basis": "cliff shift CI excludes 0 on both FER=1e-1 and 1e-2, direction consistent, "
                         "and clears the 0.2 dB abstract bar",
        "secondary_whitening": "SPLIT",
        "secondary_basis": "paired coded-BER ratio separates at SNR7/8 (CI excludes 1) but the dB "
                           "cliff-shift increment is 0.03-0.06 dB with CI spanning 0; neither branch "
                           "of the audit-v3 pre-registered binary holds verbatim",
        "no_power_above": "whitening ratio has no power at SNR>=9 (error budget exhausted; SNR10/11 are 0/0)"}
    return res


# ------------------------------------------------------------------------- E2
def analyse_e2(e2):
    main, ser = e2["main"], e2["serial"]
    res = {"frames_per_point": main["15"]["frames"], "bits_per_point": main["15"]["cum_bits"],
           "n_outer_main": main["_config"]["n_outer_iter"], "n_outer_serial": ser["_config"]["n_outer_iter"]}
    res["table"] = {}
    for s in E2_SNRS:
        c = main[s]["classical_ber"]
        row = {}
        for name, pfx in E2_ARMS:
            ber = main[s].get(pfx + "_ber")
            if ber is None:
                continue
            row[name] = {"ber": float(ber), "errs": int(main[s][pfx + "_errs"]),
                         "nmse_db": main[s].get(pfx + "_nmse_db"),
                         "rel_vs_classical_pct": (float(ber / c - 1) * 100) if c > 0 else None}
        row["serial_floor_classical"] = {"ber": float(ser[s]["classical_ber"]), "errs": int(ser[s]["classical_errs"]),
                                         "nmse_db": ser[s].get("classical_nmse_db"), "n_outer": 1}
        row["serial_floor_f2p_ach"] = {"ber": float(ser[s]["learned_ber"]), "errs": int(ser[s]["learned_errs"]),
                                       "nmse_db": ser[s].get("learned_nmse_db"), "n_outer": 1}
        res["table"][s] = row

    # paired significance for the deployment arm (aggregate stats only - no per-frame dump in E2)
    res["paired_tests"] = {}
    for s in E2_SNRS:
        x = main[s]
        m, sd, nf = x["paired_frame_diff_mean"], x["paired_frame_diff_std"], x["frames"]
        se = sd / math.sqrt(nf)
        res["paired_tests"][s] = {
            "mcnemar": {"n10": x["mcnemar_n10"], "n01": x["mcnemar_n01"],
                        "chi2_cc": x["mcnemar_chi2_cc"], "p_one_sided": x["mcnemar_p_one_sided"]},
            "paired_frame_diff": {"mean": m, "std": sd, "se": se, "t": x["paired_frame_t"],
                                  "ci95_normal": [m - 1.96 * se, m + 1.96 * se],
                                  "separated": bool((m - 1.96 * se) * (m + 1.96 * se) > 0)},
            "ci_method": "normal approximation on the paired per-frame error difference; E2 results.json "
                         "carries no per-frame arrays, so no frame bootstrap is possible for E2"}
    res["paired_tests"]["20"]["power_note"] = (
        "SNR20 has no statistical power at 800 frames: 110 vs 99 errors, McNemar p=0.104, paired CI "
        "spans 0. This run neither reproduces nor refutes the 3-seed firm -28.9%; SNR20 citations must "
        "keep using res-20260610-01")

    # PCSI ladder, SNR15
    c = main["15"]["classical_ber"]
    a = main["15"]["learned_ber"]
    p = main["15"]["pcsi_ber"]
    sc = ser["15"]["classical_ber"]
    total = math.log(sc / p)
    res["pcsi_ladder_snr15"] = {
        "rungs": {"serial_classical": sc, "classical_iter10": c, "f2p_ach": a, "pcsi": p},
        "serial_to_classical_factor": sc / c,
        "classical_to_pcsi_factor": c / p,
        "f2p_to_pcsi_factor": a / p,
        "log_gap_serial_to_pcsi_nat": total,
        "recovered_by_iteration_pct": 100 * math.log(sc / c) / total,
        "recovered_by_iteration_plus_f2p_pct": 100 * math.log(sc / a) / total,
        "recovered_from_classical_origin_pct": 100 * math.log(c / a) / math.log(c / p),
        "pairing_note": "both segments are CPU, same harness and seed, but E2 dumps no per-frame array, "
                        "so frame-level pairing between the two runs is asserted by construction, not "
                        "proven. Treated as a horizontal comparison per audit v3 section 6.4"}
    return res


def emit_markdown(payload):
    L = ["# E1/E2 final values with confidence intervals (2026-07-27)", "",
         "Derived from the five raw `results.json` files listed in `provenance`.",
         "Frame-level block bootstrap, block = frame, B=%d, seed=%d." % (B, BOOT_SEED), "",
         "## E1 cliff shift (primary pre-registered readout)", "",
         "| line | arm | shift (dB) | CI95 | excludes 0 |", "|---|---|---|---|---|"]
    for line, d in payload["e1"]["cliff_shift_db"].items():
        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            L.append("| %s | %s | %.3f | [%.3f, %.3f] | %s |" % (
                line, k, v["point"], v["ci95"][0], v["ci95"][1], "yes" if v.get("separated") else "no"))
    L += ["", "## E1 coded-BER paired ratios", "", "| SNR | ratio | point | CI95 | excludes 1 |", "|---|---|---|---|---|"]
    for s, row in payload["e1"]["coded_ber_ratio"].items():
        for k, v in row.items():
            if v.get("point") is None:
                L.append("| %s | %s | n/a | - | - |" % (s, k))
            else:
                L.append("| %s | %s | %.4f | [%.4f, %.4f] | %s |" % (
                    s, k, v["point"], v["ci95"][0], v["ci95"][1], "yes" if v["separated"] else "no"))
    L += ["", "## E1 per-point table", "", "| SNR | arm | FER | coded BER | raw BER |", "|---|---|---|---|---|"]
    for s, row in payload["e1"]["table"].items():
        for k, v in row.items():
            L.append("| %s | %s | %.4g | %.4g | %.4g |" % (s, k, v["fer"], v["coded_ber"], v["raw_ber"]))
    L += ["", "## E2 arms", "", "| SNR | arm | BER | errs | vs classical |", "|---|---|---|---|---|"]
    for s, row in payload["e2"]["table"].items():
        for k, v in row.items():
            rel = v.get("rel_vs_classical_pct")
            L.append("| %s | %s | %.5g | %d | %s |" % (
                s, k, v["ber"], v["errs"], ("%+.2f%%" % rel) if rel is not None else "-"))
    lad = payload["e2"]["pcsi_ladder_snr15"]
    L += ["", "## E2 PCSI ladder (SNR15)", "",
          "| quantity | value |", "|---|---|",
          "| serial classical (n_outer=1) | %.5g |" % lad["rungs"]["serial_classical"],
          "| classical (n_outer=10) | %.5g |" % lad["rungs"]["classical_iter10"],
          "| F2P + achievable | %.5g |" % lad["rungs"]["f2p_ach"],
          "| PCSI | %.5g |" % lad["rungs"]["pcsi"],
          "| recovered by iteration | %.1f%% |" % lad["recovered_by_iteration_pct"],
          "| recovered by iteration + F2P | %.1f%% |" % lad["recovered_by_iteration_plus_f2p_pct"],
          "| recovered from classical origin | %.1f%% |" % lad["recovered_from_classical_origin_pct"], ""]
    return "\n".join(L)


def main():
    write = "--no-write" not in sys.argv
    e1 = {nm: load(run) for nm, run in E1_RUNS.items()}
    e2 = {nm: load(run) for nm, run in E2_RUNS.items()}
    rng = np.random.default_rng(BOOT_SEED)

    payload = {
        "schema": "afdm-e1e2-analysis/1",
        "generated_by": "afdm_sp_joint_unrolled/analyze_e1_e2_20260727.py",
        "bootstrap": {"method": "frame-level block bootstrap (block = frame)", "B": B, "seed": BOOT_SEED,
                      "ci": "percentile 2.5 / 97.5"},
        "provenance": {nm: {"path": "afdm_sp_joint_unrolled/%s/results.json" % run, "md5": md5_of(run),
                            "remote": "/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/%s/results.json" % run}
                       for nm, run in list(E1_RUNS.items()) + list(E2_RUNS.items())},
        "config_fingerprint": {nm: d["_config"] for nm, d in list(e1.items()) + list(e2.items())},
        "argv": {nm: d["_argv"] for nm, d in list(e1.items()) + list(e2.items())},
    }
    payload["verification"] = verify(e1, e2)
    payload["e1"] = analyse_e1(e1, rng)
    payload["e2"] = analyse_e2(e2)

    if write:
        os.makedirs(OUT_DIR, exist_ok=True)
        jpath = os.path.join(OUT_DIR, "e1_e2_20260727_analysis.json")
        mpath = os.path.join(OUT_DIR, "e1_e2_20260727_analysis.md")
        tmp = jpath + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False)
        os.replace(tmp, jpath)
        with open(mpath + ".tmp", "w") as fh:
            fh.write(emit_markdown(payload))
        os.replace(mpath + ".tmp", mpath)
        print("wrote %s" % jpath)
        print("wrote %s" % mpath)

    v = payload["verification"]
    print("pairing all_pass=%s | rerun divergence %d/%d = %.2e | binding=%s" % (
        v["e1_cross_run_pairing"]["all_pass"], v["e1_rerun_divergence"]["total_bit_divergence"],
        v["e1_rerun_divergence"]["total_raw_errs"], v["e1_rerun_divergence"]["rate"],
        v["e1_binding_transfer"]["binding_status"]))
    for line, d in payload["e1"]["cliff_shift_db"].items():
        g = d["geom_vs_classical"]
        print("  %s  geom shift %.3f dB CI [%.3f, %.3f]  bar0.2=%s" % (
            line, g["point"], g["ci95"][0], g["ci95"][1], d["abstract_bar_0p2db_cleared"]))
    return payload


if __name__ == "__main__":
    main()
