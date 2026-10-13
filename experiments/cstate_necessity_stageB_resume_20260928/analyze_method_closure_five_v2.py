"""Postfailure five-policy reader with one explicit prefix-ledger schema repair.

The original registered reader and its failed attempt remain unchanged. This
reader requires a separately hash-bound analysis erratum before truth access.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

import analyze_method_closure as shared
import f2_run_population_five as producer
from f2_run_population_five import EXCLUDED, POLICIES, PRODUCER_FILES, SCHEMA

stage_a = shared.stage_a
N = 1024
ERRATUM_SCHEMA = "method-closure-five-policy-analysis-erratum/1"


def verify_erratum(args: argparse.Namespace) -> str:
    """Bind the original failed reader, this repair and its test before truth."""
    root = Path(__file__).resolve().parent
    project = root.parent.parent
    results = project / "results/cstate_necessity_stageB_resume_20260928"
    digest = stage_a.sha256(args.analysis_erratum)
    if digest != args.analysis_erratum_sha256:
        raise ValueError("analysis-only erratum transfer SHA differs")
    erratum = json.loads(args.analysis_erratum.read_text())
    expected = {
        "schema": ERRATUM_SCHEMA,
        "status": "locked",
        "change_scope": "prefix ledger lacks stream_ids; continuation ledger and every raw artifact retain exact stream identity validation",
        "original_reader_sha256": stage_a.sha256(root / "analyze_method_closure_five.py"),
        "recovery_reader_sha256": stage_a.sha256(Path(__file__)),
        "recovery_test_sha256": stage_a.sha256(root / "test_analyze_method_closure_five_v2.py"),
        "original_failed_log_sha256": stage_a.sha256(
            results / "population_five_analysis_run_v1.log"),
        "original_failed_exit_code_sha256": stage_a.sha256(
            results / "population_five_analysis_exit_code.txt"),
        "registration_sha256": stage_a.sha256(args.f2_registration),
        "observed_seal_sha256": stage_a.sha256(args.f2_observed / "observed_seal.json"),
        "observed_git_attestation_sha256": stage_a.sha256(args.f2_git_attestation),
        "registration_commit": args.f2_registration_commit,
        "observed_commit": args.f2_observed_commit,
        "output_relative_path": str(args.out.resolve().relative_to(project)),
    }
    if any(erratum.get(key) != value for key, value in expected.items()):
        raise ValueError("analysis-only erratum/source/failure binding differs")
    if (results / "population_five_analysis_exit_code.txt").read_text() != "1\n":
        raise ValueError("original analysis failure exit receipt differs")
    return digest


def validate_paid_input(row: dict, input_row: dict) -> None:
    """Match the two actual paid-ledger schemas without inventing missing data."""
    if (row["input_sha256"] != input_row["observation_sha256"]
            or row["observation_hash"] != input_row["observation_hash"]):
        raise ValueError("paid arm input identity differs")
    if row["kind"] == "prefix":
        if "stream_ids" in row:
            raise ValueError("prefix paid ledger schema unexpectedly changed")
    elif row["kind"] == "continuation":
        if row.get("stream_ids") != input_row["stream_ids"]:
            raise ValueError("continuation stream identity differs")
    else:
        raise ValueError("unknown paid call kind")


def validate_raw_input(raw: dict, row: dict, stem: str, input_row: dict) -> None:
    if (raw["observation_id"] != stem or raw["arm"] != row["arm"]
            or raw["input_sha256"] != row["input_sha256"]
            or raw["observation_hash"] != input_row["observation_hash"]
            or raw["stream_ids"] != input_row["stream_ids"]):
        raise ValueError("paid arm raw semantic identity differs")


def verify_pretruth(args: argparse.Namespace) -> tuple[dict, dict, list[dict], list[dict]]:
    """Do every registration, observed file and Git check before touching truth."""
    verify_erratum(args)
    observed = args.f2_observed.resolve()
    registration = args.f2_registration.resolve()
    out = args.out.resolve()
    if args.out.exists() or any(out.is_relative_to(root.resolve()) for root in
                                (observed, args.population_observed, args.population_truth)):
        raise ValueError("analysis output exists or would mutate sealed evidence")
    reg = json.loads(registration.read_text())
    stage_reg = json.loads(args.stage_a_registration.read_text())
    if (reg.get("schema") != SCHEMA or reg.get("status") != "locked"
            or stage_reg.get("status") != "locked"
            or reg.get("policy_names") != list(POLICIES)
            or reg.get("excluded_policies") != EXCLUDED):
        raise ValueError("locked five-policy registration required")
    manifest = json.loads((observed / "manifest.json").read_text())
    seal = shared._attest(observed, registration, args.f2_git_attestation,
                          args.f2_git_attestation_sha256,
                          args.f2_registration_commit, args.f2_observed_commit,
                          args.f2_seal_repo_path)
    if (seal.get("schema") != SCHEMA or seal.get("frames") != N
            or seal.get("actual_prefix_calls") != 2048
            or seal.get("actual_continuation_calls") != 120
            or seal.get("actual_total_calls") != 2168
            or seal.get("f0_trigger_frames") != 40
            or seal.get("logical_policy_rows") != 5120
            or seal.get("excluded_policies") != EXCLUDED
            or seal.get("truth_values_read") is not False
            or seal.get("run_manifest_sha256") != stage_a.sha256(registration)
            or manifest.get("schema") != SCHEMA
            or manifest.get("run_manifest_sha256") != stage_a.sha256(registration)
            or manifest.get("source_hashes") != reg.get("producer_source_hashes")
            or manifest.get("policy_names") != list(POLICIES)
            or manifest.get("excluded_policies") != EXCLUDED):
        raise ValueError("five-policy observed seal/registration identity differs")
    if seal.get("files", {}).get("ledger.jsonl") != stage_a.sha256(observed / "ledger.jsonl"):
        raise ValueError("observed ledger seal differs")
    inventory = shared._inventory(observed, seal)
    root = Path(__file__).resolve().parent
    producer = reg.get("producer_source_hashes")
    if (not isinstance(producer, dict) or set(producer) != set(PRODUCER_FILES)
            or any(producer[name] != stage_a.sha256(root / name)
                   for name in PRODUCER_FILES)
            or reg.get("launcher_sha256") != stage_a.sha256(
                root / "f2_launch_population_five_once.sh")):
        raise ValueError("registered five-policy producer source bytes differ")
    analysis = reg.get("analysis_source_hashes")
    expected_analysis = {
        "cstate_necessity_stageB_resume_20260928/analyze_method_closure.py":
            root / "analyze_method_closure.py",
        "cstate_necessity_stageB_resume_20260928/analyze_method_closure_five.py":
            root / "analyze_method_closure_five.py",
        "cstate_necessity_stageA_20260928/analyze_stage_a.py":
            root.parent / "cstate_necessity_stageA_20260928/analyze_stage_a.py",
    }
    if (not isinstance(analysis, dict) or set(analysis) != set(expected_analysis)
            or any(analysis[name] != stage_a.sha256(path)
                   for name, path in expected_analysis.items())):
        raise ValueError("registered five-policy analysis source bytes differ")
    if reg.get("population_observed_seal_sha256") != stage_a.sha256(
            args.population_observed / "observed_seal.json"):
        raise ValueError("paired observed population differs")
    stage_a._verify_file_inventory(args.population_observed, "observed_seal.json")
    population = shared._subset(shared._jsonl(args.population_observed / "ledger.jsonl"))
    # No truth path, seal or ledger was opened above this point.
    if stage_a.sha256(args.population_truth / "truth_seal.json") != \
            stage_reg["population_truth_seal_sha256"]:
        raise ValueError("registered truth seal differs")
    stage_a._verify_file_inventory(args.population_truth, "truth_seal.json")
    truth = shared._subset(shared._jsonl(args.population_truth / "ledger.jsonl"))
    if any(a["observation_hash"] != b["observation_hash"] or
           a["stream_ids"] != b["stream_ids"]
           for a, b in zip(population, truth, strict=True)):
        raise ValueError("observed/truth semantic identity differs")
    return seal, inventory, population, truth


def expected_paid_schedule(ledger: list[dict]) -> list[tuple[str, str, str]]:
    """Reconstruct the frozen paid-call sequence from saved observed F0 syndromes."""
    grouped: dict[str, dict[str, dict]] = {}
    for row in ledger:
        group = grouped.setdefault(row["observation_id"], {})
        if row["arm"] in group:
            raise ValueError("duplicate paid arm")
        group[row["arm"]] = row
    expected: list[tuple[str, str, str]] = []
    ordinal = 0
    for frame in range(N):
        stem = f"s650_f{frame:04d}"
        group = grouped.get(stem)
        if group is None or not {"F0", "F2E"}.issubset(group):
            raise ValueError("missing paid prefix")
        expected.extend((stem, "prefix", arm) for arm in producer.base.schedule(frame))
        if group["F0"]["final_syndrome_weight"]:
            ordinal += 1
            expected.extend((stem, "continuation", arm)
                            for arm in producer.continuation_plan(1, ordinal))
    if ordinal != 40 or len(expected) != 2168:
        raise ValueError("original F0 40-trigger paid schedule differs")
    return expected


def memory_ledger(ledger: list[dict], seal: dict) -> tuple[list[dict], int]:
    """Validate cumulative process RSS without assigning isolated arm peaks."""
    rows = []
    previous = 0
    for expected_attempt, paid in enumerate(ledger, 1):
        rss = paid.get("rss_peak_kib_cumulative")
        if (type(rss) is not int or rss <= 0 or rss < previous
                or paid.get("attempt") != expected_attempt):
            raise ValueError("paid-call cumulative RSS or attempt order differs")
        rows.append({"attempt": expected_attempt,
                     "observation_id": paid["observation_id"],
                     "kind": paid["kind"], "arm": paid["arm"],
                     "rss_peak_kib_cumulative": rss})
        previous = rss
    campaign_peak = seal.get("campaign_rss_peak_kib_cumulative")
    if type(campaign_peak) is not int or campaign_peak < previous:
        raise ValueError("campaign RSS high-water is below a paid-call peak")
    return rows, campaign_peak


def validate_logical_cost(row: dict, parent: dict, branch: dict | None) -> float:
    """Bind each logical policy to its paid source rows and exclusive cost."""
    branch_cost = 0.0 if branch is None else branch["complete_latency_seconds"]
    if (row["prefix_raw_sha256"] != parent["raw_sha256"]
            or row["branch_raw_sha256"] != (
                None if branch is None else branch["raw_sha256"])
            or not np.isclose(row["prefix_complete_seconds"],
                              parent["complete_latency_seconds"], atol=1e-9, rtol=0)
            or not np.isclose(row["branch_complete_seconds"],
                              branch_cost, atol=1e-9, rtol=0)
            or not np.isclose(row["complete_latency_seconds"],
                              parent["complete_latency_seconds"] + branch_cost,
                              atol=1e-9, rtol=0)):
        raise ValueError("logical prefix/branch source or complete cost differs")
    return branch_cost


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    seal, inventory, population, truth = verify_pretruth(args)
    sys.path.insert(0, str(args.baseline / "src"))
    import evidence  # type: ignore[import-not-found]  # codec only

    observed = args.f2_observed
    cache: dict[str, tuple[dict, dict]] = {}

    def load_observed(relative: str, digest: str, identity: dict | None = None) -> dict:
        if inventory.get(relative, {}).get("sha256") != digest:
            raise ValueError(f"raw/checkpoint hash differs: {relative}")
        if relative not in cache:
            cache[relative] = evidence.load_artifact(stage_a._safe(observed, relative))
        payload, actual_identity = cache[relative]
        if identity is not None and actual_identity != identity:
            raise ValueError(f"raw/checkpoint semantic identity differs: {relative}")
        return payload

    code_cache = (args.baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
                  "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    stage_reg = json.loads(args.stage_a_registration.read_text())
    H, G, free = stage_a._code_arrays(code_cache, stage_reg)
    ledger = shared._jsonl(observed / "ledger.jsonl")
    attempts = shared._jsonl(observed / "attempts.jsonl")
    policies = shared._jsonl(observed / "policy_ledger.jsonl")
    if (len(ledger) != 2168 or len(attempts) != 2168 or len(policies) != 5120
            or (observed / "failed_calls.jsonl").read_text().strip()
            or any(row["attempt"] != started["attempt"] or
                   row["arm"] != started["arm"] or
                   row["kind"] != started["kind"] or
                   row["observation_id"] != started["observation_id"]
                   for row, started in zip(ledger, attempts, strict=True))):
        raise ValueError("five-policy durable attempt allocation differs")
    if ([(row["observation_id"], row["kind"], row["arm"]) for row in ledger] !=
            expected_paid_schedule(ledger)):
        raise ValueError("five-policy interleaved paid schedule differs")
    paid_memory, campaign_rss = memory_ledger(ledger, seal)
    by_frame = shared._index_f2(ledger, policies, list(POLICIES), seal)
    actual_index: dict[str, dict[str, dict]] = {}
    for row in ledger:
        group = actual_index.setdefault(row["observation_id"], {})
        if row["arm"] in group:
            raise ValueError("duplicate paid arm")
        group[row["arm"]] = row
    outcomes: dict[str, dict[str, dict]] = {}
    frame_table: list[dict] = []
    deadline_table: list[dict] = []
    components_table: list[dict] = []
    for frame, (input_row, truth_row) in enumerate(zip(population, truth, strict=True)):
        stem = input_row["observation_id"]
        tagged = stage_a._artifact(evidence, args.population_truth,
                                   truth_row["truth_path"], truth_row["truth_sha256"])
        if (tagged["observation_hash"] != input_row["observation_hash"]
                or tagged["stream_ids"] != input_row["stream_ids"]):
            raise ValueError("truth artifact belongs to another observation")
        coded, info = stage_a._validate_truth(tagged, H, G, free)
        actual = {}
        paid = actual_index.get(stem, {})
        if set(paid) - set(POLICIES) or not {"F0", "F2E"}.issubset(paid):
            raise ValueError("five-policy paid arm set differs")
        for arm, row in paid.items():
            validate_paid_input(row, input_row)
            identity = {"observation_id": stem, "arm": arm}
            identity.update(prefix_raw_sha256=row["prefix_raw_sha256"]
                            if row["kind"] == "continuation" else None)
            if row["kind"] == "prefix":
                identity.pop("prefix_raw_sha256")
                identity["input_sha256"] = row["input_sha256"]
            raw = load_observed(row["raw_path"], row["raw_sha256"], identity)
            validate_raw_input(raw, row, stem, input_row)
            if inventory.get(row["decision_path"], {}).get("sha256") != row["decision_sha256"]:
                raise ValueError("paid arm decision hash differs")
            decision = json.loads((observed / row["decision_path"]).read_text())
            decoded, extracted, weight = shared._bits(raw, decision, H, free)
            if (row["raw_sha256"] != decision["raw_sha256"] or
                    row["final_syndrome_weight"] != weight or
                    row["checkpoints"] != decision["checkpoints"]):
                raise ValueError("paid arm raw/decision/ledger differs")
            actual[arm] = (row, decoded, extracted, raw)
        if bool(actual["F0"][0]["final_syndrome_weight"]) != \
                all(name in actual for name in ("B", "F0_LOCAL", "F2T")):
            raise ValueError("F0 continuation set differs")
        outcomes[stem] = {}
        used_actual = {"F0", "F2E"}
        for policy in POLICIES:
            row = by_frame[stem][policy]
            if row.get("schema") != SCHEMA:
                raise ValueError("five-policy logical row schema differs")
            parent = "F2E" if policy == "F2E" else "F0"
            parent_row = actual[parent][0]
            branch = row["branch_arm"]
            triggered = parent_row["final_syndrome_weight"] != 0
            if (row["input_sha256"] != input_row["observation_sha256"]
                    or row["prefix_arm"] != parent
                    or row["prefix_raw_sha256"] != parent_row["raw_sha256"]
                    or row["triggered"] != triggered or row["frame"] != frame
                    or branch != (policy if triggered and policy not in ("F0", "F2E")
                                  else None)):
                raise ValueError("five-policy logical parent/branch differs")
            source = branch or parent
            used_actual.add(source)
            source_row, decoded, extracted, source_raw = actual[source]
            branch_cost = validate_logical_cost(
                row, parent_row, None if branch is None else source_row)
            if (row["source_of_final_bits"] != source_row["raw_path"]
                    or row["final_decoded_sha256"] != hashlib.sha256(decoded.tobytes()).hexdigest()
                    or row["final_info_sha256"] != hashlib.sha256(extracted.tobytes()).hexdigest()
                    or row["final_syndrome_weight"] != source_row["final_syndrome_weight"]):
                raise ValueError("five-policy logical decision/cost differs")
            checkpoints = [shared._checkpoint(load_observed, cp, H, free, info,
                           clock_key="durable_seconds", coded=coded)
                           for cp in row["checkpoints"]]
            if (len(checkpoints) != (3 if branch else 2)
                    or checkpoints[-1]["ready_seconds"] > row["complete_latency_seconds"]
                    or not np.array_equal(load_observed(
                        row["checkpoints"][-1]["path"],
                        row["checkpoints"][-1]["sha256"])["decoded"], decoded)):
                raise ValueError("logical checkpoint allocation differs")
            expected = parent_row["checkpoints"] + (
                [] if branch is None else source_row["checkpoints"])
            for saved, logical in zip(expected, row["checkpoints"], strict=True):
                offset = 0.0 if saved in parent_row["checkpoints"] else \
                    parent_row["complete_latency_seconds"]
                if (saved["path"] != logical["path"] or saved["sha256"] != logical["sha256"]
                        or not np.isclose(logical["durable_seconds"],
                                          offset + saved["durable_seconds"], atol=1e-9, rtol=0)):
                    raise ValueError("logical checkpoint source/clock differs")
            components = {
                "complete_latency_seconds": float(row["complete_latency_seconds"]),
                "prefix_complete_seconds": float(parent_row["complete_latency_seconds"]),
                "branch_complete_seconds": float(branch_cost),
                "prefix_input_seconds": float(parent_row["input_seconds"]),
                "prefix_receiver_seconds_including_checkpoint": float(
                    parent_row["receiver_seconds_including_checkpoint"]),
                "prefix_post_receiver_serialization_and_validation_seconds": float(
                    parent_row["post_receiver_serialization_and_validation_seconds"]),
                "prefix_checkpoint_serialization_nested_seconds": float(
                    parent_row["checkpoint_serialization_seconds"]),
                "branch_setup_and_deepcopy_seconds": (0.0 if branch is None else float(
                    source_row["branch_setup_and_deepcopy_seconds"])),
                "branch_receiver_seconds_including_checkpoint": (0.0 if branch is None else float(
                    source_row["receiver_seconds_including_checkpoint"])),
                "branch_post_receiver_serialization_and_validation_seconds": (
                    0.0 if branch is None else float(source_row[
                        "post_receiver_serialization_and_validation_seconds"])),
                "branch_checkpoint_serialization_nested_seconds": (0.0 if branch is None else float(
                    source_row["checkpoint_serialization_seconds"])),
            }
            if parent == "F2E":
                for key, value in actual[parent][3]["front"]["timing"]["component_seconds"].items():
                    components[f"prefix_front_{key}_nested_seconds"] = float(value)
            if branch == "F2T":
                for key, value in source_raw["front"]["timing"]["component_seconds"].items():
                    components[f"branch_front_{key}_nested_seconds"] = float(value)
            elif branch is not None:
                for key, value in source_raw["exclusive_stages"].items():
                    components[f"branch_{key}_nested_seconds"] = float(value)
            if (not np.isclose(components["prefix_complete_seconds"],
                    components["prefix_input_seconds"] +
                    components["prefix_receiver_seconds_including_checkpoint"] +
                    components["prefix_post_receiver_serialization_and_validation_seconds"],
                    atol=1e-9, rtol=0)
                    or not np.isclose(components["branch_complete_seconds"],
                    components["branch_setup_and_deepcopy_seconds"] +
                    components["branch_receiver_seconds_including_checkpoint"] +
                    components["branch_post_receiver_serialization_and_validation_seconds"],
                    atol=1e-9, rtol=0)):
                raise ValueError("five-policy mutually exclusive clocks differ")
            result = shared._result(decoded, extracted,
                source_row["final_syndrome_weight"], coded, info, checkpoints,
                components, triggered)
            outcomes[stem][policy] = result
            frame_table.append({"campaign": "F2", "observation_id": stem,
                "frame": frame, "arm_or_policy": policy,
                "info_correct": result["info_correct"], "coded_correct": result["coded_correct"],
                "coded_errors": result["coded_errors"],
                "syndrome_weight": result["syndrome_weight"],
                "valid_but_wrong": result["valid_but_wrong"],
                "triggered": result["triggered"]})
            components_table.append({"campaign": "F2", "observation_id": stem,
                                     "frame": frame, "arm_or_policy": policy, **components})
            for deadline in shared.DEADLINES:
                state = stage_a.latest_ready(checkpoints, deadline)
                deadline_table.append({"campaign": "F2", "observation_id": stem,
                    "frame": frame, "arm_or_policy": policy,
                    "deadline_seconds": deadline, "ready": state["ready"],
                    "correct": state["correct"], "round": state["round"]})
        if used_actual != set(actual):
            raise ValueError("paid F2 call lacks a five-policy row")
        cache.clear()
    if sum(outcomes[stem]["F0"]["triggered"] for stem in outcomes) != 40:
        raise ValueError("historical 40 F0 trigger cohort differs")
    summary = shared._summarize(outcomes)
    if set(summary["arms"]) != set(POLICIES):
        raise ValueError("five-policy summary incomplete")
    report = {"schema": "method-closure-five-policy-analysis/1", "status": "pass",
              "campaign": "f2", "population": "sealed 6.5-dB developmental 1024",
              "git_attestation_verified_before_truth": True,
              "analysis_recovery": {
                  "schema": ERRATUM_SCHEMA,
                  "erratum_sha256": args.analysis_erratum_sha256,
                  "original_attempt": "exit1 schema failure; preserved without overwrite",
                  "repair": "prefix paid ledger has no stream_ids; continuation ledger and all raw stream IDs verified"},
              "input_sha256": {
                  "observed_seal": stage_a.sha256(observed / "observed_seal.json"),
                  "truth_seal": stage_a.sha256(args.population_truth / "truth_seal.json"),
                  "ledger": stage_a.sha256(observed / "ledger.jsonl")},
              "summary": summary, "excluded_policies": EXCLUDED,
              "excluded_policy_outcomes": {name: "unavailable" for name in EXCLUDED},
              "population_numerical_failures": 0,
              "memory": {
                  "campaign_rss_peak_kib_cumulative": campaign_rss,
                  "last_paid_call_rss_peak_kib_cumulative": paid_memory[-1][
                      "rss_peak_kib_cumulative"],
                  "paid_call_rows": len(paid_memory),
                  "units": "KiB on registered Linux host",
                  "semantics": "RUSAGE_SELF shared-process cumulative high-water, including F2E 155-slot downstream TF/refit/decoder and durable serialization; isolated per-policy peaks unavailable"},
              "component_semantics": "exclusive call parts sum to full cost; checkpoint/front/geometry stages are nested",
              "historical_failed_attempt": "separate invalid_partial 19-call campaign; no rows reused"}
    args.out.mkdir(parents=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (args.out / "observed_file_inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    for filename, rows in (("frame_outcomes.csv", frame_table),
                           ("deadline_decisions.csv", deadline_table),
                           ("component_timing.csv", components_table),
                           ("paid_call_memory.csv", paid_memory)):
        with (args.out / filename).open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=sorted(
                {key for row in rows for key in row}), extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("f2-observed", "population-observed", "population-truth",
                 "stage-a-registration", "f2-registration", "baseline",
                 "f2-git-attestation", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("f2-git-attestation-sha256", "f2-observed-commit",
                 "f2-seal-repo-path", "f2-registration-commit",
                 "analysis-erratum-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--analysis-erratum", type=Path, required=True)
    analyze(parser.parse_args())


if __name__ == "__main__":
    main()
