"""Saved-row pilot economy and October common-failure readouts."""

import importlib.util
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from common import read_rows, wilson


SLOT_RUN = "slot_mismatch_20261019/out/main_20261118"
P1_RUN = "tcom_reference_frame_20261015/out/p1"
GS_RUN = "tcom_genie_support_20261016/out/main"
SCENARIOS = ("G", "U")
RHOS = (300, 500)
CROSSING_SHA256 = "43b98016a398aa9cb1a24f8921162f9da1d967546ef594ceb86500095742d94e"


def crossing_routine():
    here = Path(__file__).resolve().parent
    # The frozen utility is staged beside this script for the remote run.
    path = here / "phase3_crossings.py"
    if not path.is_file():
        path = here.parent / "slot_mismatch_20261019" / path.name
    if sha256(path.read_bytes()).hexdigest() != CROSSING_SHA256:
        raise ValueError(f"Frozen crossing source digest differs: {path}")
    spec = importlib.util.spec_from_file_location("phase3_crossings", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def db_bounds(low, high):
    if low == high:
        return f"{low:.3f}"
    return f"[{low:.3f}, {high:.3f}]"


def pilot_economy(root, rng, draws):
    crossing = crossing_routine()
    n_frames = 1000
    snrs = list(crossing.SNR_CENTI_DB)
    arms = ("F0", "B_8", "A3")
    failures = np.full(
        (n_frames, len(SCENARIOS), len(RHOS), len(arms), len(snrs)), -1, dtype=np.float32
    )
    truth_delays = {}
    for row in read_rows(root / SLOT_RUN):
        if row["family"] != "M":
            continue
        frame = row["frame"]
        scenario = row["scenario"]
        point = snrs.index(row["snr_centi_db"])
        if not 10000 <= frame < 10000 + n_frames:
            raise ValueError(f"Unexpected family M frame {frame}")
        cells = failures[frame - 10000, SCENARIOS.index(scenario), RHOS.index(row["rho_permille"])]
        if cells[0, point] != -1:
            raise ValueError(f"Duplicate family M key in {row}")
        delays = row["truth"]["delays"]
        frame_key = (frame, scenario)
        if truth_delays.setdefault(frame_key, delays) != delays:
            raise ValueError(f"Unpaired family M truth delays for {frame_key}")
        saved = row["s"]["8"]
        selected = saved["arms"]["A1c"] if saved["triggered"] else saved["f0"]
        cells[:, point] = [arm["info_errors"] > 0 for arm in (saved["f0"], selected, row["A3"])]

    if np.any(failures < 0):
        raise ValueError("Incomplete family M paired frame/SNR grid")
    counts = failures.sum(axis=0, dtype=np.int64)
    observed = crossing.crossing_bounds(counts, n_frames)
    matrix = failures.reshape(n_frames, -1)
    probability = np.full(n_frames, 1 / n_frames)
    boot = np.empty((draws, *observed.shape))
    for start in range(0, draws, 512):
        weights = rng.multinomial(n_frames, probability, size=min(512, draws - start))
        boot_counts = (weights.astype(np.float32) @ matrix).reshape(-1, *counts.shape)
        boot[start:start + len(weights)] = crossing.crossing_bounds(boot_counts, n_frames)

    lines = [
        "The 32,000 family-M rows contain 1,000 physical frames (10000–10999),",
        "shared across both scenarios, both pilot fractions and all eight SNR points (4.5–8.0 dB).",
        f"The 95% percentile intervals use {draws:,} frame-bootstrap replicates with one",
        "shared resample across every curve. The frozen routine interpolates the first 1%",
        "crossing on log FER (frame error rate) and retains unbounded endpoints when the",
        "crossing is outside the grid. Crossing, gap and contrast units are dB.",
        "",
        "| Scenario | ρ | Arm | 1% crossing | 95% interval |",
        "|---|---:|---|---:|---|",
    ]
    cells = {}
    for sc_i, scenario in enumerate(SCENARIOS):
        cells[scenario] = {}
        for rho_i, rho in enumerate(RHOS):
            by_arm = {}
            for arm_i, arm in enumerate(arms):
                point = observed[sc_i, rho_i, arm_i]
                samples = boot[:, sc_i, rho_i, arm_i]
                ci = crossing.paired_ci(samples)
                by_arm[arm] = dict(
                    crossing=crossing.bounds_json(point), ci95=crossing.bounds_json(ci),
                    snr_centi_db=[int(x) for x in snrs], error_counts=counts[sc_i, rho_i, arm_i].tolist(),
                    bootstrap_left=int(np.isneginf(samples[:, 0]).sum()),
                    bootstrap_right=int(np.isposinf(samples[:, 1]).sum()),
                )
                lines.append(
                    f"| {scenario} | {rho / 1000:.1f} | {arm} | {db_bounds(*point)} | {db_bounds(*ci)} |"
                )
            cells[scenario][str(rho)] = by_arm

    lines.extend([
        "",
        "| Scenario | Arm | Gap at ρ=.3 (95% interval) | Gap at ρ=.5 (95% interval) | Δ | 95% interval for Δ | Rule |",
        "|---|---|---|---|---:|---|---|",
    ])
    deltas, outcomes, headlines = {}, [], []
    for sc_i, scenario in enumerate(SCENARIOS):
        raw = observed[sc_i].reshape(-1, 2)
        samples = boot[:, sc_i].reshape(draws, -1, 2)
        deltas[scenario] = {}
        headline_parts = []
        for arm_i, arm in enumerate(arms[:2]):
            gap_intervals, gap_data = [], {}
            for rho_i, rho in enumerate(RHOS):
                offset = len(arms) * rho_i
                positive, negative = [offset + arm_i], [offset + 2]
                point = crossing.contrast_bounds(raw, positive, negative)
                ci = crossing.paired_ci(crossing.contrast_bounds(samples, positive, negative))
                gap_intervals.append(f"{db_bounds(*point)} ({db_bounds(*ci)})")
                gap_data[str(rho)] = dict(value=crossing.bounds_json(point), ci95=crossing.bounds_json(ci))
            positive, negative = [arm_i, 5], [2, 3 + arm_i]
            point = crossing.contrast_bounds(raw, positive, negative)
            ci = crossing.paired_ci(crossing.contrast_bounds(samples, positive, negative))
            passed = bool(ci[0] > .5 if arm == "F0" else ci[1] < .75)
            deltas[scenario][arm] = dict(
                gap=gap_data, value=crossing.bounds_json(point), ci95=crossing.bounds_json(ci),
                passes=passed,
            )
            outcomes.append(passed)
            label = "pass" if passed else "fail"
            lines.append(
                f"| {scenario} | {arm} | {' | '.join(gap_intervals)} | {db_bounds(*point)} | "
                f"{db_bounds(*ci)} | {label} |"
            )
            headline_parts.append(db_bounds(*ci))
        headlines.append(f"{scenario} Δ CIs F0/B_8 {' / '.join(headline_parts)} dB")
    lines.extend([
        "",
        "Both scenarios must meet Δ_F0 lower >0.50 dB and Δ_B_8 upper <0.75 dB.",
    ])
    return dict(
        source=f"`{SLOT_RUN}/rows_shard*.jsonl.gz`",
        fields=(
            "`family`, `frame`, `scenario`, `rho_permille`, `snr_centi_db`, "
            "`truth.delays` for pairing, `s['8'].f0.info_errors`, `s['8'].triggered`, "
            "`s['8'].arms.A1c.info_errors`, and `A3.info_errors`."
        ),
        outcome="Survives" if all(outcomes) else "Does not survive",
        headline=" | ".join(headlines), report="\n".join(lines),
        n_frames=n_frames, crossings=cells, deltas=deltas,
    )


def october_rescue(root):
    p1_dir, gs_dir = root / P1_RUN, root / GS_RUN
    p1_cfg, gs_cfg = [
        json.loads((directory / "config_shard000.json").read_text())["_config"]
        for directory in (p1_dir, gs_dir)
    ]
    if (
        (p1_cfg["ENTROPY_HEX"], p1_cfg["DOMAIN"]) != (gs_cfg["entropy"], gs_cfg["domain"])
        or any(p1_cfg[key] != gs_cfg[key] for key in ("frames", "frame_offset", "scenarios", "rho_list"))
        or p1_cfg["source_md5"]["p1_driver"] != gs_cfg["source_md5"]["p1_driver"]
        or (p1_cfg["source_md5"]["gen_fixed"], gs_cfg["source_md5"]["gen_fixed"])
        != ("cb9be5ea91c0a9b1863758ed598de1c6", "9a3a987e0a1aaecde33018da5f38c74c")
    ):
        raise ValueError("October producer configurations do not match the reviewed pairing")
    frames = range(p1_cfg["frame_offset"], p1_cfg["frame_offset"] + p1_cfg["frames"])
    expected = {(scenario, rho, frame) for scenario in SCENARIOS for rho in RHOS for frame in frames}
    sources = []
    for directory in (p1_dir, gs_dir):
        rows = {}
        for row in read_rows(directory):
            if row["snr_centi_db"] != 500:
                continue
            key = (row["scenario"], row["rho_permille"], row["frame"])
            if key in rows:
                raise ValueError(f"Duplicate October key {key} in {directory}")
            rows[key] = row
        if rows.keys() != expected:
            raise ValueError(f"Unexpected October 5 dB key coverage for {directory}")
        sources.append(rows)
    p1, gs = sources

    for key, row in p1.items():
        oracle = gs[key]
        if (
            sorted(row["truth_l"]) != sorted(oracle["arms"]["GS-multi"]["delays"])
            or sorted(set(row["truth_l"])) != sorted(oracle["arms"]["GS-set"]["delays"])
        ):
            raise ValueError(f"October oracle delays disagree with P1 truth for {key}")
    fingerprint_fields = ("channel_seed", "physical_gains_sha256", "info_sha256", "noise_sha256")
    lines = [
        "At 5 dB the October runs contain 2,000 physical frames per scenario and pilot",
        "fraction. The validated join is on (scenario, pilot fraction, physical frame).",
        "P1 hashes match across both fractions for the gains, information bits and noise,",
        "and the two archives agree on the true delay multiset and set at every joined key.",
        "The producer configurations share frame entropy, domain and P1 driver digest.",
        "Their generator digests straddle commit `d727b09e`, which extended scenario S with",
        "optional delay scaling and truncation. The U/G defaults execute the same draws.",
        "Rescue rates use F0 failure at both fractions as the denominator and report 95%",
        "Wilson intervals. The Astra rule compares low-ρ GS-set and high-ρ A3.",
        "",
        "| Scenario | Common F0 failures | ρ | Arm | Rescued | Rate | 95% interval |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    rates = {}
    for scenario in SCENARIOS:
        common = []
        for frame in frames:
            low, high = (p1[(scenario, rho, frame)] for rho in RHOS)
            if any(low[field] != high[field] for field in fingerprint_fields):
                raise ValueError(f"October P1 pairing disagrees for {scenario}/{frame}")
            if low["arms"]["F0"]["info_errors"] > 0 and high["arms"]["F0"]["info_errors"] > 0:
                common.append(frame)

        rates[scenario] = {}
        for rho in RHOS:
            rates[scenario][str(rho)] = {}
            for arm, rows in (("GS-set", gs), ("A3", p1)):
                success = sum(rows[(scenario, rho, frame)]["arms"][arm]["info_errors"] == 0 for frame in common)
                share = success / len(common)
                lo, hi = wilson(success, len(common))
                rates[scenario][str(rho)][arm] = dict(
                    n=len(common), rescues=success, rate=share, ci95=[lo, hi],
                )
                lines.append(
                    f"| {scenario} | {len(common)} | {rho / 1000:.1f} | {arm} | {success} | "
                    f"{share:.1%} | [{lo:.1%}, {hi:.1%}] |"
                )

    outcomes = {}
    headlines = []
    for low_arm, high_arm in (("GS-set", "A3"), ("GS-set", "GS-set"), ("A3", "A3")):
        label = f"{low_arm} low / {high_arm} high"
        outcomes[label] = all(
            rates[scenario]["300"][low_arm]["ci95"][0] > .75
            and rates[scenario]["500"][high_arm]["ci95"][1] < .10
            for scenario in SCENARIOS
        )
    low_arm, high_arm = "GS-set", "A3"
    for scenario in SCENARIOS:
        low, high = rates[scenario]["300"][low_arm], rates[scenario]["500"][high_arm]
        headlines.append(f"{scenario} low {low['rate']:.1%}, high {high['rate']:.1%}")
    lines.extend([
        "",
        "Thresholds are low-ρ 95% lower >75% and high-ρ 95% upper <10% in both scenarios.",
    ])
    for label, passed in outcomes.items():
        lines.append(f"- {label} {'passes' if passed else 'fails'}.")
    return dict(
        source=f"`{P1_RUN}/rows_shard*.jsonl.gz` and `{GS_RUN}/rows_shard*.jsonl.gz`",
        fields=(
            "`scenario`, `rho_permille`, `snr_centi_db`, `frame`, "
            "`arms.F0.info_errors`, `arms.A3.info_errors`, and `arms['GS-set'].info_errors`. "
            "Pairing uses P1 truth and stream fingerprints and saved GS delay lists."
        ),
        outcome="Survives" if outcomes[f"{low_arm} low / {high_arm} high"] else "Does not survive",
        headline=f"GS-set low / A3 high: {', '.join(headlines)}",
        report="\n".join(lines), rescue_rates=rates, threshold_outcomes=outcomes,
    )


def run(root, rng, draws):
    return {"R-A": pilot_economy(root, rng, draws), "R-D": october_rescue(root)}
