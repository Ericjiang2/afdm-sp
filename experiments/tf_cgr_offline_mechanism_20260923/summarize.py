"""Deterministic summary of the completed sealed-data offline panels."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "results/tf_cgr_offline_mechanism_20260923/analysis"
OLD = ROOT / "results/tf_cgr_mechanism_20260923_v2/analysis_r2/report.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((PANEL / name).read_text())


def metrics(pred, actual):
    pred, actual = np.asarray(pred, float), np.asarray(actual, float)
    target = float(np.linalg.norm(actual))
    proposed = float(np.linalg.norm(pred))
    error = float(np.linalg.norm(pred - actual))
    return dict(actual_norm=target, predicted_norm=proposed,
                normalized_error=error / target if target else None,
                zero_predictor_error_ratio=error / target if target else None,
                beats_zero_predictor=bool(error < target) if target else None,
                cosine=float(np.dot(pred, actual) / (proposed * target))
                if proposed and target else None)


def main():
    target = PANEL / "report.json"
    if target.exists():
        raise FileExistsError(target)
    source = json.loads(OLD.read_text())
    if source["candidate_pass"] is not False:
        raise ValueError("original candidate gate differs")
    transport = read("transport.json")
    finite = read("finite_panel.json")
    block = read("block_metric_covariance.json")
    domain = read("block_domain_reconciliation.json")
    if len(transport) != 8 or len(finite) != 160 or len(block) != 160 or len(domain) != 18:
        raise ValueError("offline panel counts differ")
    pooled, orientation = {}, {}
    for arm in ("CGR", "SHAM"):
        pred = np.concatenate([row["predictions"][arm]["predicted_terminal_llr"] for row in transport])
        actual = np.concatenate([row["predictions"][arm]["actual_terminal_llr_shift"] for row in transport])
        per_frame = [row["predictions"][arm]["unclipped"] for row in transport]
        pooled[arm] = dict(**metrics(pred, actual),
                           frame_errors_below_zero=sum(row["beats_zero_predictor"] for row in per_frame),
                           frames=8,
                           rescued_frame_errors=[row["normalized_error"] for sample, row in zip(transport, per_frame)
                                                 if sample["rescued"]])
        orientation[arm] = {
            comparison: metrics(pred, np.concatenate([
                row["predictions"][comparison]["actual_terminal_llr_shift"] for row in transport]))
            for comparison in ("CGR", "SHAM")
        }
    by_frame = []
    for row in transport:
        frame = row["observation_id"]
        physical = [item for item in finite if item["observation_id"] == frame]
        if len(physical) != 20:
            raise ValueError("20 finite rows absent")
        predictions = row["predictions"]
        cross = {
            arm: {
                actual_arm: metrics(predictions[arm]["predicted_terminal_llr"],
                                    predictions[actual_arm]["actual_terminal_llr_shift"])
                for actual_arm in ("CGR", "SHAM")
            }
            for arm in ("CGR", "SHAM")
        }
        by_frame.append(dict(observation_id=frame, rescued=row["rescued"],
                             finite_D_sum=float(sum(item["finite_D"] for item in physical)),
                             first_order_A_sum=float(sum(item["first_order_A"] for item in physical)),
                             quadratic_Q_sum=float(sum(item["quadratic_Q"] for item in physical)),
                             finite_positive_steps=sum(item["finite_D"] > 0 for item in physical),
                             first_order_positive_steps=sum(item["first_order_A"] > 0 for item in physical),
                             cgr=row["predictions"]["CGR"]["unclipped"],
                             sham=row["predictions"]["SHAM"]["unclipped"],
                             clipped_cgr=row["predictions"]["CGR"]["clipped"],
                             clipped_sham=row["predictions"]["SHAM"]["clipped"],
                             orientation_crosscheck=cross,
                             logscore=row["logscore"]))
    block_by_frame = []
    for frame in [r["observation_id"] for r in transport]:
        items = [row for row in block if row["observation_id"] == frame]
        block_by_frame.append(dict(observation_id=frame,
                                   maximum_modal_ratio=max(max(row["modal_amplification"]) for row in items),
                                   maximum_metric_only_physical_motion=max(row["metric_only_physical_motion"] for row in items),
                                   maximum_covariance_action_norm=max(row["covariance_action_norm"] for row in items)))
    report = dict(
        schema="tf-cgr-zero-receiver-mechanism/1",
        status="complete",
        authorized_receiver_calls=0,
        performed_receiver_calls=0,
        performed_decoder_calls=0,
        original_candidate_pass=source["candidate_pass"],
        original_attempted_receiver_calls=101,
        finite_effect_sums_are_descriptive=True,
        finite_effect_sum_scope="20 different saved BASE states; not a telescoping or causal CGR trajectory sum; not a new gate",
        verdict="unidentifiable from the archive",
        verdict_reason=("BASE-only tangent shifts beat zero and distinguish CGR from SHAM, "
                        "but finite rescued-frame errors remain material; BLOCK uses a mixed "
                        "time/AF observation-response interface, so its harm cannot be attributed "
                        "to the gain metric alone, and controls lack per-step vector/covariance states."),
        target_transport_pooled=pooled,
        orientation_crosscheck=orientation,
        frames=by_frame,
        block_targets=block_by_frame,
        block_domain=dict(triggered_observations=len(domain),
                          response_mismatch_relative_min=min(row["response_domain_mismatch_relative"] for row in domain),
                          response_mismatch_relative_max=max(row["response_domain_mismatch_relative"] for row in domain),
                          source_residual_max=max(max(row["base_source_s_error"], row["block_source_s_error"])
                                                  for row in domain if row["full_state_vectors"]),
                          full_vector_observations=sum(row["full_state_vectors"] for row in domain)),
        provenance=dict(observed_seal_sha256="42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43",
                        observed_seal_commit="dc228d7254274f3be3403514fc75f0758aacc15c",
                        source_bound_r2_report_sha256=sha(OLD),
                        inputs_sha256={name: sha(PANEL / name) for name in (
                            "transport.json", "finite_panel.json", "block_metric_covariance.json",
                            "block_domain_reconciliation.json", "state_reconciliation.json", "impulses.json")}),
    )
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("sealed offline mechanism summary: complete; verdict unidentifiable")


if __name__ == "__main__":
    main()
