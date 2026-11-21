"""Paired frame-cluster readouts for the grid-spacing protocol."""

from collections import Counter
from itertools import product
from pathlib import Path
import sys

import numpy as np

from exchange import ARMS as X_ARMS, DELTAS
from sbl_grid import ARMS as S_ARMS, ETAS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tf_covariance_audit_20261018"))
from sampling import bootstrap_means, interval

DRAWS = 20_000
SEED = 20261124


def classify(x, a2_change, s4_minus_2, s8_minus_4, s8_minus_2):
    xlo, xhi = x["ci_lo"], x["ci_hi"]
    if xlo > 0 and a2_change["ci_lo"] > 0:
        direction = "supported"
    else:
        direction = "opposite" if xhi < 0 else "uncertain"
    quantity = "supported" if xlo >= .10 else "refuted" if xhi < .10 else "uncertain"
    monotone = s4_minus_2["ci_lo"] > 0 and s8_minus_4["ci_lo"] > 0

    def equivalent(metric):
        return metric["ci_lo"] >= -.015 and metric["ci_hi"] <= .015

    endpoint = equivalent(s8_minus_2)
    insensitive = endpoint and equivalent(s4_minus_2) and equivalent(s8_minus_4)
    decreases = -s8_minus_2["ci_hi"] > 0
    if monotone:
        s = "monotone_supported"
    elif insensitive:
        s = "insensitive"
    else:
        s = "endpoint_equivalent" if endpoint else "uncertain"
    if direction == "opposite" or decreases:
        joint = "opposite_prediction"
    elif direction == "supported" and monotone:
        joint = "both_directions_supported"
    else:
        joint = "uncertain"
    return dict(X_direction=direction, X_quantity=quantity, S=s, S_monotone=monotone,
                S_insensitive=insensitive, S_endpoint_equivalent=endpoint,
                S_decreases=decreases, joint=joint)


def index_rows(rows, key_of, expected):
    indexed = {}
    for row in rows:
        key = key_of(row)
        if key in indexed or key not in expected:
            raise ValueError(f"Duplicate or out-of-protocol key: {key}")
        indexed[key] = row
    if indexed.keys() != expected:
        raise ValueError(f"Missing paired rows: {sorted(expected - indexed.keys())[:5]}")
    return indexed


def indicator(values):
    if any(type(value) is not bool for value in values):
        raise ValueError("Per-key preferences and frame errors must be Boolean")
    return np.asarray(values, dtype=int)


def summarize(x_rows, s_rows, *, x_frames, s_frames, snrs, s_arms=S_ARMS):
    """Require the separately frozen schedule and resample frames once per leg."""
    x_frames, s_frames, snrs, s_arms = map(tuple, (x_frames, s_frames, snrs, s_arms))
    if s_arms not in (S_ARMS, ("R0", "R1")):
        raise ValueError(f"Invalid S arm schedule: {s_arms}")
    x_by_frame = index_rows(x_rows, lambda r: r["frame"], set(x_frames))
    s_keys = tuple((s, 300, snr, frame) for s, snr, frame in product("UG", snrs, s_frames))
    s_by_key = index_rows(s_rows, lambda r: (tuple(r["key"]), r["eta"]),
                          set(product(s_keys, ETAS)))
    if any(set(row["variants"]) != set(s_arms) for row in s_by_key.values()):
        raise ValueError("S row arms differ from the frozen schedule")

    included = [frame for frame in x_frames if not x_by_frame[frame].get("exclusions")]
    excluded = Counter(reason for row in x_by_frame.values()
                       for reason in set(row.get("exclusions", {}).values()))
    if not included:
        raise ValueError("All X frames were excluded")
    q = {(arm, delta): indicator([
        x_by_frame[frame]["deltas"][str(delta)]["arms"][arm]["Q"] for frame in included])
         for arm, delta in product(X_ARMS, DELTAS)}
    wide, _, close = DELTAS
    x_metrics = {arm: q[arm, close] - q[arm, wide] for arm in X_ARMS}
    x_metrics["interaction"] = x_metrics["A2"] - x_metrics["CODELAY"]
    x_draws, n_x = bootstrap_means(x_metrics, included, n_boot=DRAWS, seed=SEED)
    changes = {arm: dict(point=float(x_metrics[arm].mean()), **interval(x_draws[arm]))
               for arm in X_ARMS}
    x = dict(point=float(x_metrics["interaction"].mean()), **interval(x_draws["interaction"]),
             clusters=n_x, excluded_frames=len(x_frames) - len(included), exclusions_by_reason=dict(excluded),
             changes=changes, preferences={arm: {str(delta): float(q[arm, delta].mean()) for delta in DELTAS}
                                           for arm in X_ARMS})

    fer = {(arm, eta): indicator([
        s_by_key[key, eta]["variants"][arm]["frame_error"] for key in s_keys])
           for arm, eta in product(s_arms, ETAS)}
    gap = {eta: fer["R1", eta] - fer["R0", eta] for eta in ETAS}
    contrasts = {"4_minus_2": gap[4] - gap[2], "8_minus_4": gap[8] - gap[4],
                 "8_minus_2": gap[8] - gap[2], "2_minus_8": gap[2] - gap[8]}
    slo_gap = {eta: fer["S-lo", eta] - fer["R0", eta] for eta in ETAS} if "S-lo" in s_arms else None
    if slo_gap:
        contrasts["slo_8_minus_2"] = slo_gap[8] - slo_gap[2]
    draws, n_s = bootstrap_means(contrasts, [key[3] for key in s_keys], n_boot=DRAWS, seed=SEED)
    estimates = {name: dict(point=float(values.mean()), **interval(draws[name]))
                 for name, values in contrasts.items()}
    grids = {}
    for eta in ETAS:
        group = [s_by_key[key, eta] for key in s_keys]
        ranks = {(row["grid_low_modes_per_delay"], row["grid_low_modes"]) for row in group}
        if len(ranks) != 1:
            raise ValueError(f"Inconsistent full-grid low-mode count at eta={eta}")
        per_delay, total = ranks.pop()
        grid = grids[eta] = dict(
            low_modes_per_delay=per_delay, full_grid_low_modes_total=total,
            screened_block_rank_sum_mean=float(np.mean([sum(r["screened_block_ranks"]) for r in group])),
            candidate_low_modes_mean=float(np.mean([r["census"]["projector_rank"] for r in group])),
            R1_minus_R0=float(gap[eta].mean()), arms={})
        if slo_gap:
            grid["S_lo_minus_R0"] = float(slo_gap[eta].mean())
        for name in s_arms:
            arm = [row["variants"][name] for row in group]
            grid["arms"][name] = dict(
                fer=float(fer[name, eta].mean()),
                beta_mean=float(np.mean([a["sbl"]["beta"] for a in arm])),
                convergence_rate=float(np.mean([a["sbl"]["converged"] for a in arm])),
                output_co_delay_pairs_mean=float(np.mean([a["n_pair"] for a in arm])),
                added_penalty_trace_total=float(sum(a["added_trace_sbl"] for a in arm)))
    slopes = {"R1": estimates["8_minus_2"]["point"] / 6}
    if slo_gap:
        slopes["S-lo"] = estimates["slo_8_minus_2"]["point"] / 6
    return dict(X=x, S=dict(clusters=n_s, eta=grids, contrasts=estimates, slope_by_arm=slopes),
                verdict=classify(x, changes["A2"], estimates["4_minus_2"],
                                 estimates["8_minus_4"], estimates["8_minus_2"]),
                _argv=sys.argv, _config=dict(x_frames=x_frames, s_frames=s_frames, snrs=snrs,
                                             s_arms=s_arms, seed=SEED, draws=DRAWS, cluster="physical_frame"))
