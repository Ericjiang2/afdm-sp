#!/usr/bin/env python3
"""Cross-check the independent sealed truth recount against Sol's report."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OBSERVED_REPORT = ROOT / "results/tf_cgr_mechanism_20260923/independent/v2_observed_verification.json"
TRUTH_REPORT = ROOT / "results/tf_cgr_mechanism_20260923/independent/v2_truth_recount.json"
MAIN = ROOT / "results/tf_cgr_mechanism_20260923_v2/analysis"
WITNESS_MANIFEST = ROOT / "results/tf_cgr_mechanism_20260923_v2/witnesses/witness_manifest.json"
SEAL = ROOT / "results/tf_cgr_mechanism_20260923_v2/observed/observed_seal.json"
OUT = ROOT / "results/tf_cgr_mechanism_20260923/independent/v2_truth_recount_receipt.json"
ARMS = ("BASE", "CGR", "SHAM", "BLOCK")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def require(ok: bool, message: str):
    if not ok:
        raise ValueError(message)


def main():
    observed = load(OBSERVED_REPORT)
    truth = load(TRUTH_REPORT)
    result = truth["truth_analysis"]
    main_report = load(MAIN / "report.json")
    main_decisions = load(MAIN / "decisions.json")
    main_deadlines = load(MAIN / "deadline.json")
    manifest = load(WITNESS_MANIFEST)
    roles = {entry["observation_id"]: entry["role"] for entry in manifest["entries"]}
    require(observed["truth_values_read"] is False and
            observed["observed_seal_sha256"] == sha(SEAL),
            "observed-only evidence report is not bound to the current seal")
    require(truth["truth_values_read"] is True and
            truth["truth_gates"]["committed_seal_gate"] == "passed" and
            truth["truth_gates"]["exact_bit_recount"] == "passed" and
            truth["truth_gates"]["deadline_recount"] == "passed",
            "truth report does not document the post-seal gate")
    require(result["truth_payloads_read_after_commit_gate"] == 25 and
            result["truth_codeword_encodings_verified"] == 25,
            "truth packet/codeword verification is incomplete")
    require(len(roles) == 25 and len(main_decisions) == 100,
            "witness or main decision population is incomplete")

    rows = {(item["observation_id"], item["arm"]): item for item in main_decisions}
    require(len(rows) == 100, "main decision key is not unique")
    per_call_mismatches = []
    for obs_id, metrics in result["decision_recounts"].items():
        for arm in ARMS:
            key = (obs_id, arm)
            m = rows[key]
            comparisons = (
                ("info_errors", metrics["info_errors"][arm]),
                ("coded_errors", metrics["coded_errors"][arm]),
                ("syndrome_weight", metrics["syndrome_weight"][arm]),
                ("valid_but_wrong", metrics["valid_wrong"][arm]),
                ("correct", metrics["info_errors"][arm] == 0),
            )
            for field, actual in comparisons:
                if m[field] != actual:
                    per_call_mismatches.append((obs_id, arm, field, actual, m[field]))
    require(not per_call_mismatches,
            f"independent per-call recount differs from main: {per_call_mismatches[:4]}")

    deadline_rows = {(row["observation_id"], row["arm"], str(row["seconds"])): row
                     for row in main_deadlines}
    require(len(deadline_rows) == 200, "main deadline population is incomplete")
    deadline_mismatches = []
    for obs_id, metrics in result["decision_recounts"].items():
        for arm in ARMS:
            for seconds, d in metrics["correct_available_by_deadline"][arm].items():
                m = deadline_rows[(obs_id, arm, seconds)]
                for field in ("available", "correct", "ready_seconds", "round"):
                    if d[field] != m[field]:
                        deadline_mismatches.append((obs_id, arm, seconds, field,
                                                    d[field], m[field]))
    require(not deadline_mismatches,
            f"independent deadline rows differ from main: {deadline_mismatches[:4]}")

    full25 = {
        arm: sum(result["decision_recounts"][obs]["info_errors"][arm] == 0
                 for obs in roles)
        for arm in ARMS
    }
    targets = {obs for obs, role in roles.items()
               if role == "target_remaining_failure"}
    target8 = {
        arm: sum(result["decision_recounts"][obs]["info_errors"][arm] == 0
                 for obs in targets)
        for arm in ARMS
    }
    require(full25 == {"BASE": 14, "CGR": 18, "SHAM": 11, "BLOCK": 7},
            f"unexpected full-25 exact information-word counts: {full25}")
    require(target8 == main_report["target_correct"],
            "target-8 correct counts differ from main report")
    rescue_ids = sorted(obs for obs in targets
                        if result["decision_recounts"][obs]["info_errors"]["BASE"] > 0
                        and result["decision_recounts"][obs]["info_errors"]["CGR"] == 0)
    target_loss_ids = sorted(obs for obs in targets
                             if result["decision_recounts"][obs]["info_errors"]["BASE"] == 0
                             and result["decision_recounts"][obs]["info_errors"]["CGR"] > 0)
    rescued_harm_ids = sorted(
        obs for obs, role in roles.items()
        if role == "matched_rescued_control"
        and result["decision_recounts"][obs]["info_errors"]["BASE"] == 0
        and result["decision_recounts"][obs]["info_errors"]["CGR"] > 0)
    new_valid_wrong_ids = sorted(
        obs for obs in roles
        if result["decision_recounts"][obs]["valid_wrong"]["CGR"]
        and not result["decision_recounts"][obs]["valid_wrong"]["BASE"])
    require(rescue_ids == sorted(main_report["cgr_rescues"]),
            "CGR target rescue identities differ from main")
    require(target_loss_ids == [], "CGR introduced a target loss")
    require(rescued_harm_ids == sorted(main_report["rescued_control_harms"]),
            "rescued-control harm identities differ from main")
    require(new_valid_wrong_ids == sorted(main_report["new_valid_but_wrong"]),
            "new valid-wrong identities differ from main")

    deadline_counts = result["deadline_correctness"]
    require(deadline_counts == main_report["deadline"],
            "independent deadline aggregate differs from main summary")
    pairwise_checks = {}
    for key, ours in result["pairwise_correctness_overlaps"].items():
        left, right = key.split("__")
        m = main_report["paired_outcomes"][left][right]
        expected = {
            "both_correct": m["both_correct"],
            "left_only_correct": m["left_only"],
            "right_only_correct": m["right_only"],
            "neither_correct": m["neither_correct"],
        }
        require(ours == expected, f"pairwise outcome differs from main: {key}")
        pairwise_checks[key] = "match"

    receipt = {
        "schema": "tf-cgr-independent-truth-recount-receipt/1",
        "status": "pass",
        "observed_only_report_sha256": sha(OBSERVED_REPORT),
        "truth_recount_report_sha256": sha(TRUTH_REPORT),
        "observed_seal_sha256": observed["observed_seal_sha256"],
        "seal_commit": main_report["seal_git"]["commit"],
        "witness_manifest_sha256": sha(WITNESS_MANIFEST),
        "truth_registration_sha256": result["truth_registration_sha256"],
        "code_identity": observed["code"],
        "truth_payloads_read_after_seal_gate": result["truth_payloads_read_after_commit_gate"],
        "truth_codeword_encodings_verified": result["truth_codeword_encodings_verified"],
        "full_population_correct_info_words_n25": full25,
        "target_correct_info_words_n8": target8,
        "target_cgr_rescues": rescue_ids,
        "target_cgr_losses": target_loss_ids,
        "rescued_control_cgr_harms": rescued_harm_ids,
        "new_valid_but_wrong_cgr_outputs": new_valid_wrong_ids,
        "deadline_correct_wrong_missing": deadline_counts,
        "all_six_pairwise_overlaps": result["pairwise_correctness_overlaps"],
        "main_crosscheck": {
            "decision_rows_compared": 100,
            "decision_field_mismatches": 0,
            "deadline_rows_compared": 200,
            "deadline_field_mismatches": 0,
            "pairwise_arm_pairs_compared": len(pairwise_checks),
            "pairwise_mismatches": 0,
            "target_counts_and_rescues_match": True,
            "control_harms_and_new_valid_wrong_match": True,
        },
        "historical_base_final_bits": {
            "main_reported_matched": main_report.get("historical_base_bits_matched"),
            "independently_recounted_here": False,
            "historical_llr_parity": "not covered",
        },
        "physical_operator_diagnostic": "not evaluated by requested exact-bit/deadline recount scope",
    }
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(OUT),
                      "full25": full25, "target8": target8,
                      "decision_mismatches": 0, "deadline_mismatches": 0},
                     sort_keys=True))


if __name__ == "__main__":
    main()
