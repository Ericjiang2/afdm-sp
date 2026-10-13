"""Offline analysis of sealed F1-fast Stage-B outputs; never imports a receiver."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

STAGE_A = Path(__file__).resolve().parents[1] / "cstate_necessity_stageA_20260928"
sys.path.insert(0, str(STAGE_A))
from analyze_stage_a import (  # noqa: E402
    _artifact, _bits, _code_arrays, _json, _jsonl, _safe, _syndrome,
    _validate_truth, _verify_file_inventory, distribution, latest_ready,
    paired_table, sha256,
)

SCHEMA = "cstate-necessity-stage-b-f1/1"
ARMS = ("B", "Cfast", "Cref")
COMPONENTS = ("complete_latency_seconds", "native_seconds", "acquisition_seconds",
              "refit_seconds", "tf_seconds", "decoder_seconds", "branch_seconds",
              "raw_serialization_seconds", "decision_record_seconds")


def schedule(frame: int) -> tuple[str, ...]:
    if frame % 16 == 0:
        from itertools import permutations
        return tuple(permutations(("B", "Cref", "Cfast")))[(frame // 16) % 6]
    ordinal = frame - 1 - frame // 16
    return ("B", "Cfast") if ordinal % 2 == 0 else ("Cfast", "B")


def _git_gate(args: argparse.Namespace, registration_sha: str, seal: Path,
              registration_commit: str) -> str:
    if any(len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value)
           for value in (registration_commit, args.observed_commit)):
        raise ValueError("full commit hashes required")
    if sha256(args.git_attestation) != args.git_attestation_sha256:
        raise ValueError("transferred local Git attestation SHA differs")
    receipt = _json(args.git_attestation)
    raw = seal.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    expected = {
        "schema": "cstate-necessity-stage-b-f1/git-attestation/1",
        "registration_commit": registration_commit,
        "observed_commit": args.observed_commit,
        "seal_repo_path": args.seal_repo_path,
        "registration_sha256": registration_sha,
        "seal_sha256": digest,
        "git_blob_oid": blob,
        "git_blob_size_bytes": len(raw),
        "git_blob_sha256": digest,
        "merge_base_is_ancestor": True,
        "checked_by": "local_git_show_and_merge_base",
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("local Git attestation differs from bound seal")
    return "local_git_attestation_consumed"


def _pretruth(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any],
                                                   list[dict[str, Any]]]:
    roots = (args.observed, args.population_observed, args.population_truth,
             args.stage_a_observed)
    if args.out.exists() or any(args.out.resolve().is_relative_to(root.resolve())
                                for root in roots):
        raise ValueError("analysis output exists or would mutate a sealed tree")
    registration = _json(args.registration)
    old_registration = _json(args.stage_a_registration)
    if (registration.get("schema") != SCHEMA or registration.get("status") != "locked"
            or old_registration.get("status") != "locked"):
        raise ValueError("locked registrations required")
    new_seal = _verify_file_inventory(args.observed, "observed_seal.json")
    if (args.observed / "invalid_partial.json").exists():
        raise ValueError("invalid-partial attempt cannot be analyzed as complete")
    _verify_file_inventory(args.population_observed, "observed_seal.json")
    _verify_file_inventory(args.stage_a_observed, "observed_seal.json")
    manifest = _json(args.observed / "manifest.json")
    if (new_seal.get("status") != "pass" or new_seal.get("observations") != 1024
            or new_seal.get("calls") != 2112 or new_seal.get("attempts") != 2112
            or new_seal.get("reference_subset_calls") != 64
            or new_seal.get("registration_sha256") != sha256(args.registration)
            or manifest.get("registration_sha256") != sha256(args.registration)
            or manifest.get("source_hashes") != registration.get("source_hashes")
            or manifest.get("protocol_sha256") != registration.get("protocol_sha256")
            or registration.get("stage_a_registration_sha256") != sha256(args.stage_a_registration)
            or new_seal.get("stage_a_observed_seal_sha256")
            != sha256(args.stage_a_observed / "observed_seal.json")
            or new_seal.get("population_observed_seal_sha256")
            != sha256(args.population_observed / "observed_seal.json")):
        raise ValueError("Stage-B registration/observed/old truth seal binding differs")
    mode = _git_gate(args, sha256(args.registration),
                     args.observed / "observed_seal.json",
                     manifest["registration_commit"])
    _verify_file_inventory(args.population_truth, "truth_seal.json")
    if (old_registration.get("population_truth_seal_sha256")
            != sha256(args.population_truth / "truth_seal.json")):
        raise ValueError("registered truth seal differs after observed Git gate")
    rows = _jsonl(args.observed / "ledger.jsonl")
    attempts = _jsonl(args.observed / "attempts.jsonl")
    if (len(rows) != 2112 or len(attempts) != 2112
            or any(row.get("status") != "ok" for row in rows)
            or [row["attempt_index"] for row in rows] != list(range(1, 2113))):
        raise ValueError("full 2112-call ledger required")
    for row, attempt in zip(rows, attempts, strict=True):
        if any(row[key] != attempt[key] for key in
               ("attempt_index", "observation_id", "arm", "input_sha256")):
            raise ValueError("durable attempt/complete ledger differs")
    old_rows = _jsonl(args.stage_a_observed / "ledger.jsonl")
    old_hashes = {(row["observation_id"], row["arm"]): row["raw_sha256"]
                  for row in old_rows if row["arm"] in ("B", "C")}
    if len(old_hashes) != 2048:
        raise ValueError("complete old B/C reference inventory required")
    for row in rows:
        old_arm = "B" if row["arm"] == "B" else "C"
        if row["reference_raw_sha256"] != old_hashes[row["observation_id"], old_arm]:
            raise ValueError("producer parity reference SHA differs")
    population = [row for row in _jsonl(args.population_observed / "ledger.jsonl")
                  if row["snr_centi_db"] == 650]
    if (len(population) != 1024 or
            [row["frame"] for row in population] != list(range(1024))):
        raise ValueError("full fixed population differs")
    registration["git_verification_mode"] = mode
    return registration, old_registration, population


def _read_call(evidence: Any, root: Path, row: dict[str, Any], H: np.ndarray,
               free: np.ndarray, coded: np.ndarray, info: np.ndarray) -> dict[str, Any]:
    identity = dict(schema=SCHEMA, observation_id=row["observation_id"], arm=row["arm"],
                    input_sha256=row["input_sha256"])
    raw = _artifact(evidence, root, row["raw_path"], row["raw_sha256"], identity)
    decision_path = _safe(root, row["decision_path"])
    if sha256(decision_path) != row["decision_sha256"]:
        raise ValueError("decision SHA differs")
    decision = _json(decision_path)
    bits = _bits(raw["final_decoded"], 2048)
    extracted = _bits(raw["final_info"], 1024)
    if (raw["observation_id"] != row["observation_id"] or raw["arm"] != row["arm"]
            or raw["input_sha256"] != row["input_sha256"]
            or raw["stream_ids"] != row["stream_ids"]
            or raw["triggered"] != row["triggered"]
            or not np.array_equal(bits[free], extracted)
            or not np.array_equal(bits, np.asarray(decision["final_decoded"]))
            or not np.array_equal(extracted, np.asarray(decision["final_info"]))
            or decision["raw_sha256"] != row["raw_sha256"]
            or decision["checkpoints"] != row["checkpoints"]
            or hashlib.sha256(bits.tobytes()).hexdigest() != row["final_decoded_sha256"]
            or _syndrome(H, bits) != row["final_syndrome_weight"]):
        raise ValueError("raw/decision/ledger identity or bits differ")
    expected_count = 3 if row["triggered"] else 2
    if len(row["checkpoints"]) != expected_count:
        raise ValueError("checkpoint count differs")
    checkpoints = []
    previous_ready = -1.0
    for index, checkpoint in enumerate(row["checkpoints"]):
        if checkpoint["round"] != index:
            raise ValueError("checkpoint round differs")
        ready = float(checkpoint["ready_seconds"])
        if (not np.isfinite(ready) or ready < previous_ready
                or checkpoint["decision_ready_seconds"] > ready
                or ready > row["complete_latency_seconds"]):
            raise ValueError("durable checkpoint clock differs")
        previous_ready = ready
        payload = _artifact(evidence, root, checkpoint["path"],
                            checkpoint["artifact_sha256"], dict(identity, round=index))
        cp_bits = _bits(payload["decoded"], 2048)
        if (_syndrome(H, cp_bits) != checkpoint["syndrome_weight"]
                or not np.array_equal(cp_bits, payload["event"]["snapshot"]["decoded"])):
            raise ValueError("checkpoint bits or syndrome differs")
        checkpoints.append(dict(round=index, ready_seconds=ready,
                                info_correct=bool(np.array_equal(cp_bits[free], info)),
                                coded_correct=bool(np.array_equal(cp_bits, coded))))
    if (not np.array_equal(bits, cp_bits)
            or row["baseline_syndrome_weight"] != row["checkpoints"][1]["syndrome_weight"]
            or row["triggered"] != (row["arm"] == "B" and
                                    row["baseline_syndrome_weight"] != 0)):
        raise ValueError("final/native trigger or bits differ")
    timing = {name: float(row[name]) for name in COMPONENTS}
    if any(not np.isfinite(value) or value < 0 for value in timing.values()):
        raise ValueError("invalid component clock")
    difference = float(row["reference_max_difference"])
    if not np.isfinite(difference) or difference < 0 or difference > 2e-10:
        raise ValueError("producer reference parity gate differs")
    return dict(info_correct=bool(np.array_equal(extracted, info)),
                coded_errors=int(np.count_nonzero(bits != coded)),
                info_errors=int(np.count_nonzero(extracted != info)),
                syndrome_weight=_syndrome(H, bits), triggered=bool(row["triggered"]),
                checkpoints=checkpoints, timing=timing,
                reference_max_difference=difference)


def _csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("empty output table")
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    registration, old_registration, population = _pretruth(args)
    sys.path.insert(0, str(args.baseline / "src"))
    import evidence  # type: ignore[import-not-found]  # archived codec only

    cache = (args.baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
             "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    H, G, free = _code_arrays(cache, old_registration)
    truth = {row["observation_id"]: row for row in
             _jsonl(args.population_truth / "ledger.jsonl") if row["snr_centi_db"] == 650}
    if len(truth) != 1024:
        raise ValueError("full bound truth ledger required")
    rows = _jsonl(args.observed / "ledger.jsonl")
    expected = [(input_row["observation_id"], arm)
                for frame, input_row in enumerate(population) for arm in schedule(frame)]
    if [(row["observation_id"], row["arm"]) for row in rows] != expected:
        raise ValueError("prespecified 2112-call schedule differs")
    calls: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    timing_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    for frame, input_row in enumerate(population):
        stem = input_row["observation_id"]
        tagged_row = truth[stem]
        if (tagged_row["observation_hash"] != input_row["observation_hash"]
                or tagged_row["stream_ids"] != input_row["stream_ids"]):
            raise ValueError("sealed observed/truth identity differs")
        tagged = _artifact(evidence, args.population_truth, tagged_row["truth_path"],
                           tagged_row["truth_sha256"])
        if (tagged["observation_hash"] != input_row["observation_hash"]
                or tagged["stream_ids"] != input_row["stream_ids"]):
            raise ValueError("truth payload identity differs")
        coded, info = _validate_truth(tagged, H, G, free)
        group = rows[sum(len(schedule(i)) for i in range(frame)):
                     sum(len(schedule(i)) for i in range(frame + 1))]
        decisions = {}
        for row in group:
            if (row["frame"] != frame or row["input_sha256"] != input_row["observation_sha256"]
                    or row["observation_hash"] != input_row["observation_hash"]
                    or row["stream_ids"] != input_row["stream_ids"]):
                raise ValueError("saved call/input identity differs")
            result = _read_call(evidence, args.observed, row, H, free, coded, info)
            calls[row["arm"]].append(result)
            decisions[row["arm"]] = result
            timing_rows.append(dict(frame=frame, observation_id=stem, arm=row["arm"],
                                    **result["timing"]))
        frame_rows.append(dict(frame=frame, observation_id=stem,
                               B_info_correct=int(decisions["B"]["info_correct"]),
                               Cfast_info_correct=int(decisions["Cfast"]["info_correct"]),
                               Cref_info_correct=(int(decisions["Cref"]["info_correct"])
                                                  if "Cref" in decisions else ""),
                               B_coded_errors=decisions["B"]["coded_errors"],
                               Cfast_coded_errors=decisions["Cfast"]["coded_errors"]))
    if {arm: len(calls[arm]) for arm in ARMS} != {"B": 1024, "Cfast": 1024, "Cref": 64}:
        raise ValueError("full arm denominators differ")
    b = np.asarray([row["info_correct"] for row in calls["B"]], dtype=bool)
    fast = np.asarray([row["info_correct"] for row in calls["Cfast"]], dtype=bool)
    subset = [frame for frame in range(1024) if frame % 16 == 0]
    ref = np.asarray([row["info_correct"] for row in calls["Cref"]], dtype=bool)
    subset_fast = fast[subset]
    times = {arm: {name: distribution([row["timing"][name] for row in calls[arm]])
                   for name in COMPONENTS} for arm in ARMS}
    old_rows = _jsonl(args.stage_a_observed / "ledger.jsonl")
    old_c = [row for row in old_rows if row["arm"] == "C"]
    if len(old_c) != 1024:
        raise ValueError("old full C reference denominator differs")
    old_clock = distribution([row["complete_latency_seconds"] for row in old_c])
    ref_acq = times["Cref"]["acquisition_seconds"]["mean"]
    fast_subset_acq = float(np.mean([calls["Cfast"][frame]["timing"]["acquisition_seconds"]
                                     for frame in subset]))
    b_subset_acq = float(np.mean([calls["B"][frame]["timing"]["acquisition_seconds"]
                                  for frame in subset]))
    excess = ref_acq - b_subset_acq
    excess_removed = ((ref_acq - fast_subset_acq) / excess if excess > 0 else None)
    fast_subset_complete = float(np.mean(
        [calls["Cfast"][frame]["timing"]["complete_latency_seconds"] for frame in subset]))
    reference_complete = times["Cref"]["complete_latency_seconds"]["mean"]
    if reference_complete <= 0:
        raise ValueError("nonpositive matched reference complete clock")
    latency_reduction = ((times["Cref"]["complete_latency_seconds"]["mean"]
                          - fast_subset_complete)
                         / reference_complete)
    python_bound = (excess_removed is not None and excess_removed > 0.5
                    and latency_reduction >= 0.10)
    deadline: dict[str, dict[str, dict[str, int]]] = {}
    for arm in ARMS:
        deadline[arm] = {}
        for limit in (0.5, 1.0):
            evaluated = [latest_ready(row["checkpoints"], limit) for row in calls[arm]]
            correct = sum(item["correct"] for item in evaluated)
            missing = sum(not item["ready"] for item in evaluated)
            deadline[arm][str(limit)] = dict(n=len(evaluated), correct=correct,
                wrong_ready=len(evaluated)-correct-missing, missing=missing,
                wrong_or_missing=len(evaluated)-correct)
    report = dict(schema="cstate-necessity-stage-b-f1-analysis/1",
        status="complete_developmental_not_fresh_confirmation",
        observed_commit=args.observed_commit,
        git_verification_mode=registration["git_verification_mode"],
        observed_seal_sha256=sha256(args.observed / "observed_seal.json"),
        population_frames=1024, calls=2112,
        information_fer={
            arm: dict(n=len(calls[arm]),
                      errors=len(calls[arm])-sum(row["info_correct"] for row in calls[arm]),
                      rate=1-float(np.mean([row["info_correct"] for row in calls[arm]])))
            for arm in ARMS},
        coded_ber={
            arm: dict(n_bits=len(calls[arm])*2048,
                      errors=sum(row["coded_errors"] for row in calls[arm]),
                      rate=sum(row["coded_errors"] for row in calls[arm])/(len(calls[arm])*2048))
            for arm in ARMS},
        paired_B_vs_Cfast=paired_table(b, fast),
        paired_Cref_vs_Cfast_subset=paired_table(ref, subset_fast),
        Cfast_minus_B_upper_95_fer=(paired_table(b, fast)[
            "upper_95_fer_second_minus_first"]),
        Cfast_one_percentage_point_noninferiority=(paired_table(b, fast)[
            "upper_95_fer_second_minus_first"] < 0.01),
        deadline=deadline, timing=times,
        old_stage_a_C_complete_latency=dict(old_clock, source="archived_separate_run"),
        matched64=dict(n=64, excess_denominator_seconds=excess,
                       acquisition_excess_removed_ratio=excess_removed,
                       complete_latency_reduction_ratio=latency_reduction,
                       python_bound_operational_label=python_bound,
                       operational_verdict=("F1-PYTHON-BOUND" if python_bound
                                            else "F1-UNRESOLVED")),
        f2_replacement="unresolved_no_qualified_f2_run")
    args.out.mkdir(parents=True)
    _csv(args.out / "F1_FAST_TIMING.csv", timing_rows)
    _csv(args.out / "frame_outcomes.csv", frame_rows)
    (args.out / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2,
                                                     allow_nan=False) + "\n")
    (args.out / "analysis_receipt.json").write_text(json.dumps(dict(
        schema=report["schema"], reader_sha256=sha256(Path(__file__)),
        observed_seal_sha256=report["observed_seal_sha256"],
        report_sha256=sha256(args.out / "report.json"),
        timing_sha256=sha256(args.out / "F1_FAST_TIMING.csv"),
        outcomes_sha256=sha256(args.out / "frame_outcomes.csv")),
        sort_keys=True, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("registration", "stage-a-registration", "observed", "population-observed",
                 "population-truth", "stage-a-observed", "baseline", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--git-attestation", required=True, type=Path)
    parser.add_argument("--git-attestation-sha256", required=True)
    parser.add_argument("--observed-commit", required=True)
    parser.add_argument("--seal-repo-path", required=True)
    arguments = parser.parse_args()
    analyze(arguments)
