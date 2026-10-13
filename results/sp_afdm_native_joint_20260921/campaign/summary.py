"""Offline paired, cost, CE and exact path-Gram summaries; no receiver calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta

from common import attach, identity, unbits
from gate import decision_error
from verify import validate_run


def cp_interval(successes, trials, confidence):
    alpha = 1 - confidence
    if trials == 0:
        return [0., 1.]
    low = 0. if successes == 0 else float(beta.ppf(alpha / 2, successes, trials - successes + 1))
    high = 1. if successes == trials else float(beta.ppf(1 - alpha / 2, successes + 1, trials - successes))
    return [low, high]


def paired(left, right, deadline):
    frames = sorted(set(left) & set(right))
    rescue = harm = 0
    for frame in frames:
        a, b = decision_error(left[frame], deadline), decision_error(right[frame], deadline)
        rescue += int(a == 0 and b == 1)
        harm += int(a == 1 and b == 0)
    n, discordant = len(frames), rescue + harm
    ri, hi = cp_interval(rescue, n, .975), cp_interval(harm, n, .975)
    return {"n": n, "rescues": rescue, "harms": harm, "net_rescues": rescue - harm,
            "delta_fer_ep_minus_tf": (rescue - harm) / n,
            "rescue_given_discordance_cp95": cp_interval(rescue, discordant, .95),
            "delta_fer_bonferroni_cp97_5_components": [ri[0] - hi[1], ri[1] - hi[0]],
            "interval_note": "conservative at least 95% coverage; pair is a frame"}


def full_h_nmse(truth, snapshot, n, c1, c2):
    from physical import Channel
    from twofft import TimePathOps
    delays = np.r_[truth["l_i"], snapshot["delays"]]
    dopplers = np.r_[truth["k_real"], snapshot["dopplers"]]
    gains = np.r_[truth["g_i"], -snapshot["gains"]]
    error_power = TimePathOps(Channel(n, c1, c2, delays, dopplers, gains)).power(gains)
    truth_gains = truth["g_i"]
    truth_power = TimePathOps(Channel(n, c1, c2, truth["l_i"], truth["k_real"], truth_gains)).power(truth_gains)
    return float(error_power / truth_power)


def summarize(run, source, baseline, gate_path):
    evidence = attach(source, baseline)
    checked = validate_run(run, source, baseline, require_complete=True)
    gate = json.loads(gate_path.read_text())
    stage = checked["manifest"]["stage"]
    d = gate["deadline_seconds"]
    ep = gate["selected_ep"]
    if stage == "A" and checked["run_identity_sha256"] != gate["stage_a_run_identity_sha256"]:
        raise ValueError("Stage A gate/run identity differs")
    if stage == "B" and checked["manifest"]["gate_sha256"] != evidence.artifact_sha256(gate_path):
        raise ValueError("Stage B fixed gate hash differs")
    header = json.loads((run / "context_header.json").read_text())
    n = header["system"]["n_total"]
    c1, c2 = header["system"]["c1"], header["system"]["c2"]
    by_cell = {}
    truth_cache = {}
    for row in checked["records"]:
        snr, frame, arm = row["snr_centi_db"], row["frame"], row["arm"]
        by_cell.setdefault(snr, {}).setdefault(arm, {})[frame] = row
        key = (snr, frame)
        if key not in truth_cache:
            truth_cache[key] = evidence.load_artifact(run / "frames" / f"s{snr}_f{frame:03d}_truth.npz",
                identity(checked["run_identity_sha256"], "frame_truth", snr, frame))[0]
    cells = {}
    audit_canaries = []
    for snr, arms in sorted(by_cell.items()):
        cell = {"arms": {}, "paired": {}}
        for arm, framed in sorted(arms.items()):
            rows = [framed[f] for f in sorted(framed)]
            seconds = np.asarray([r["seconds"] for r in rows])
            metrics = {"frames": sorted(framed), "attempts": len(rows),
                       "complete_seconds_sum": float(seconds.sum()),
                       "median_seconds": float(np.median(seconds)),
                       "p90_seconds_linear": float(np.quantile(seconds, .9, method="linear")),
                       "latency_cdf_seconds_sorted": sorted(float(x) for x in seconds),
                       "unrestricted_frame_errors": sum(decision_error(r) for r in rows),
                       "deadline_frame_errors": {str(factor): sum(decision_error(r, factor*d) for r in rows)
                                                 for factor in (1, 1.5, 2)},
                       "numerical_failures": sum(r["status"] != "ok" for r in rows),
                       "info_bit_errors": sum(r["info_errors"] or 0 for r in rows),
                       "coded_bit_errors": sum(r["coded_errors"] or 0 for r in rows),
                       "info_bits_with_decision": sum(truth_cache[(snr, r["frame"])]["info"]["length"]
                                                      for r in rows if r["checkpoints"]),
                       "coded_bits_with_decision": sum(truth_cache[(snr, r["frame"])]["coded"]["length"]
                                                       for r in rows if r["checkpoints"]),
                       "code_valid_wrong": sum(bool(r["checkpoints"] and
                          r["checkpoints"][-1]["syndrome_weight"] == 0 and
                          r["checkpoints"][-1]["info_errors"] > 0) for r in rows),
                       "stage_seconds": {"ce": 0., "inference": 0., "decoder": 0.,
                                         "complete_minus_named_stages": 0.},
                       "counts": {"ce_objective_evaluations": 0, "ce_reported_fft": 0,
                                  "tf_inner_reported_fft": 0, "decoder_iterations": 0},
                       "nmse_by_frame_last_checkpoint": {},
                       "ce_gamma_trace": [], "ce_gamma_offdiag_ratio": [],
                       "ce_objective_first_last": [], "tf_conditioning_floor_events": 0}
            for row in rows:
                stage_total = 0.
                for cp in row["checkpoints"]:
                    event = cp["event"]
                    for name in ("ce", "inference", "decoder"):
                        value = float(event[name])
                        metrics["stage_seconds"][name] += value
                        stage_total += value
                    metrics["counts"]["ce_objective_evaluations"] += int(event["ce_evaluations"])
                    metrics["counts"]["ce_reported_fft"] += int(event["ce_fft_count"])
                    metrics["counts"]["tf_inner_reported_fft"] += int(event.get("inference_fft_count", 0))
                    metrics["counts"]["decoder_iterations"] += int(event["decoder_iterations"])
                    snapshot = evidence.load_artifact(run / cp["path"])[0]["snapshot"]
                    gamma = np.asarray(snapshot["ce_gamma"])
                    trace = float(np.trace(gamma).real)
                    metrics["ce_gamma_trace"].append(trace)
                    metrics["ce_gamma_offdiag_ratio"].append(float(np.linalg.norm(gamma - np.diag(np.diag(gamma))) / max(1., np.linalg.norm(gamma))))
                    history = np.asarray(snapshot["ce_history"])
                    metrics["ce_objective_first_last"].append([float(history[0]), float(history[-1])])
                    metrics["tf_conditioning_floor_events"] += sum(int(t["data_precision_floor"] or t["gain_precision_floor"])
                        for t in snapshot["inference_trace"] if "data_precision_floor" in t)
                metrics["stage_seconds"]["complete_minus_named_stages"] += row["seconds"] - stage_total
                if row["checkpoints"]:
                    last = evidence.load_artifact(run / row["checkpoints"][-1]["path"])[0]["snapshot"]
                    metrics["nmse_by_frame_last_checkpoint"][str(row["frame"])] = full_h_nmse(
                        truth_cache[(snr, row["frame"])], last, n, c1, c2)
                    if row["frame"] in (0, 1) and arm == "TF_J20_R2":
                        from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix
                        true = truth_cache[(snr, row["frame"])]
                        htrue = physical_channel_matrix(n,c1,c2,true["l_i"],true["k_real"],true["g_i"],prefix_length=102)
                        hhat = physical_channel_matrix(n,c1,c2,last["delays"],last["dopplers"],last["gains"],prefix_length=102)
                        dense = float(np.linalg.norm(htrue-hhat)**2/np.linalg.norm(htrue)**2)
                        gram = metrics["nmse_by_frame_last_checkpoint"][str(row["frame"])]
                        if abs(dense-gram) > 1e-7*max(1., dense):
                            raise ValueError("path-Gram full-H NMSE disagrees with audit dense canary")
                        audit_canaries.append({"snr_centi_db": snr, "frame": row["frame"],
                                               "dense_nmse": dense, "gram_nmse": gram})
            metrics["info_ber_decided_only"] = (metrics["info_bit_errors"] / metrics["info_bits_with_decision"]
                if metrics["info_bits_with_decision"] else None)
            metrics["coded_ber_decided_only"] = (metrics["coded_bit_errors"] / metrics["coded_bits_with_decision"]
                if metrics["coded_bits_with_decision"] else None)
            cell["arms"][arm] = metrics
        if "TF_J20_R2" in arms and ep in arms:
            for factor in (1, 1.5, 2):
                cell["paired"][str(factor)] = paired(arms["TF_J20_R2"], arms[ep], factor*d)
            cell["paired"]["unrestricted"] = paired(arms["TF_J20_R2"], arms[ep], None)
        cells[str(snr)] = cell
    memory = max((r["memory_after"]["high_water_kib"] or 0) for r in checked["records"])
    return {"stage": stage, "source_commit": checked["manifest"]["source_commit"],
            "run_identity_sha256": checked["run_identity_sha256"], "selected_ep": ep,
            "deadline_seconds_from_A": d, "cells": cells, "audit_nmse_canaries": audit_canaries,
            "shared_process_high_water_kib": memory,
            "memory_scope": "one sequential multi-arm process including model and prior arms; not isolated receiver peak",
            "cost_scope": "complete online seconds include pilot initialization, refit, inference, decoder, callbacks; named stages exclude pilot/callback; CE FFT and TF-inner FFT are partial reported logical counts, not entire receiver transforms; static context/code setup and warmup are outside calls"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("summary output already exists")
    result = summarize(args.run, args.source, args.baseline, args.gate)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"stage": result["stage"], "cells": list(result["cells"]),
                      "run_identity_sha256": result["run_identity_sha256"]}))
