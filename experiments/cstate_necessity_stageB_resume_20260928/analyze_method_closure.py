"""Read-only, post-Git analysis of the F1 and F2 developmental campaigns.

This module imports the Stage-A evidence/statistics helpers, never a receiver,
decoder, generator, or optimizer.  Each campaign is analyzed separately, and
truth is first opened after that campaign's observed Git gate has passed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from itertools import combinations, permutations
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cstate_necessity_stageA_20260928"))
import analyze_stage_a as stage_a  # noqa: E402

N = 1024
F1_ARMS = ("B", "Cref", "Ccompat")
F2_PREFIXES = ("F0", "F2E")
DEADLINES = (0.5, 1.0)


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def _subset(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) != 3 * N:
        raise ValueError("expected full three-SNR sealed population")
    chosen = [row for row in rows if row["snr_centi_db"] == 650]
    if (len(chosen) != N or
            [row["frame"] for row in chosen] != list(range(N)) or
            [row["observation_id"] for row in chosen] !=
            [f"s650_f{i:04d}" for i in range(N)]):
        raise ValueError("fixed 6.5-dB 1024-ID subset differs")
    return chosen


def _attest(observed: Path, registration: Path, attestation: Path,
            attestation_sha: str, registration_commit: str,
            observed_commit: str, seal_repo_path: str) -> dict[str, Any]:
    seal = json.loads((observed / "observed_seal.json").read_text())
    if seal.get("status") != "pass":
        raise ValueError("incomplete observed seal")
    stage_a._verify_git_attestation(
        attestation, registration_commit=registration_commit,
        observed_commit=observed_commit, seal_repo_path=seal_repo_path,
        registration_sha256=stage_a.sha256(registration),
        seal_path=observed / "observed_seal.json",
        expected_sha256=attestation_sha)
    return seal


def _inventory(root: Path, seal: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Hash each sealed file once, recording its remote path and both digests."""
    expected = seal.get("files")
    if not isinstance(expected, dict):
        raise ValueError("observed seal file map missing")
    actual: dict[str, dict[str, Any]] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.name == "observed_seal.json":
            continue
        relative = str(path.relative_to(root))
        if relative not in expected or path.is_symlink():
            raise ValueError(f"unsealed file or symlink: {relative}")
        sha, md5 = hashlib.sha256(), hashlib.md5()  # noqa: S324 - secondary inventory only
        size = 0
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                sha.update(chunk)
                md5.update(chunk)
                size += len(chunk)
        if sha.hexdigest() != expected[relative]:
            raise ValueError(f"observed file hash differs: {relative}")
        actual[relative] = {"sha256": sha.hexdigest(), "md5": md5.hexdigest(),
                            "size_bytes": size, "path": str(path.resolve())}
    if set(actual) != set(expected):
        raise ValueError("observed sealed inventory incomplete")
    return actual


def verify_pretruth(args: argparse.Namespace) -> tuple[dict, dict, list[dict], list[dict]]:
    """Fail before reading even the truth seal unless this observed Git gate passes."""
    out = args.out.resolve()
    observed = args.f1_observed if args.campaign == "f1" else args.f2_observed
    roots = (observed, args.population_observed, args.population_truth)
    if args.out.exists() or any(out.is_relative_to(root.resolve()) for root in roots):
        raise ValueError("analysis output exists or would mutate sealed evidence")
    registration = args.f1_registration if args.campaign == "f1" else args.f2_registration
    reg = json.loads(registration.read_text())
    stage_reg = json.loads(args.stage_a_registration.read_text())
    schema = ("cstate-necessity-stage-b-f1-compat/1" if args.campaign == "f1"
              else "f2-stage-b-shared-prefix/1")
    if reg.get("schema") != schema or reg.get("status") != "locked" or \
            stage_reg.get("status") != "locked":
        raise ValueError("locked source-bound registrations required")
    manifest = json.loads((observed / "manifest.json").read_text())
    if args.campaign == "f1":
        seal = _attest(observed, registration, args.f1_git_attestation,
                       args.f1_git_attestation_sha256,
                       manifest["registration_commit"], args.f1_observed_commit,
                       args.f1_seal_repo_path)
        if (seal.get("schema") != schema or seal.get("calls") != 2112
                or seal.get("attempts") != 2112 or seal.get("observations") != N
                or seal.get("registration_sha256") != stage_a.sha256(registration)
                or manifest.get("source_hashes") != reg.get("source_hashes")):
            raise ValueError("F1 observed identity differs")
    else:
        seal = _attest(observed, registration, args.f2_git_attestation,
                       args.f2_git_attestation_sha256,
                       args.f2_registration_commit, args.f2_observed_commit,
                       args.f2_seal_repo_path)
        if (seal.get("schema") != schema or seal.get("frames") != N
                or seal.get("actual_prefix_calls") != 2048
                or seal.get("run_manifest_sha256") != stage_a.sha256(registration)
                or manifest.get("source_hashes") != reg.get("producer_source_hashes")
                or manifest.get("policy_names") != reg.get("policy_names")
                or seal.get("logical_policy_rows") != N * len(reg["policy_names"])
                or seal.get("truth_values_read") is not False):
            raise ValueError("F2 observed identity differs")
    if (seal.get("files", {}).get("ledger.jsonl") !=
            stage_a.sha256(observed / "ledger.jsonl")):
        raise ValueError("observed seal/manifest/registration identity differs")
    observed_inventory = _inventory(observed, seal)
    names = (("f1_fast_compat.py", "f1_fast_compat_native.py",
              "f1_run_compat.py", "f1_launch_compat_once.sh") if args.campaign == "f1"
             else ("f2_estimator.py", "f2_receiver.py", "f2_run_population.py"))
    key = "source_hashes" if args.campaign == "f1" else "producer_source_hashes"
    if set(reg[key]) != set(names) or any(
            stage_a.sha256(HERE / name) != reg[key][name] for name in names):
        raise ValueError("registered producer source bytes differ")
    if args.campaign == "f2" and reg.get("launcher_sha256") != stage_a.sha256(
            HERE / "f2_launch_population_once.sh"):
        raise ValueError("F2 population launcher source differs")
    if (reg.get("population_observed_seal_sha256") !=
            stage_a.sha256(args.population_observed / "observed_seal.json")):
        raise ValueError("paired observation population differs")
    stage_a._verify_file_inventory(args.population_observed, "observed_seal.json")
    population = _subset(_jsonl(args.population_observed / "ledger.jsonl"))
    # Truth bytes are first accessed after both observed Git attestations above.
    if stage_a.sha256(args.population_truth / "truth_seal.json") != \
            stage_reg["population_truth_seal_sha256"]:
        raise ValueError("registered truth seal differs")
    stage_a._verify_file_inventory(args.population_truth, "truth_seal.json")
    truth_rows = _subset(_jsonl(args.population_truth / "ledger.jsonl"))
    for observed_row, truth_row in zip(population, truth_rows, strict=True):
        if (observed_row["observation_hash"] != truth_row["observation_hash"]
                or observed_row["stream_ids"] != truth_row["stream_ids"]):
            raise ValueError("observed/truth semantic identity differs")
    return seal, observed_inventory, population, truth_rows


def _bits(raw: dict, decision: dict, H: np.ndarray,
          free: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    decoded = stage_a._bits(raw["final_decoded"], 2048)
    info = stage_a._bits(raw["final_info"], 1024)
    weight = stage_a._syndrome(H, decoded)
    if (not np.array_equal(decoded[free], info)
            or not np.array_equal(decoded, np.asarray(decision["final_decoded"]))
            or not np.array_equal(info, np.asarray(decision["final_info"]))
            or weight != decision["final_syndrome_weight"]):
        raise ValueError("raw/decision/systematic bits differ")
    return decoded, info, weight


def _checkpoint(load_artifact: Any, cp: dict, H: np.ndarray,
                free: np.ndarray, info: np.ndarray, *, clock_key: str,
                coded: np.ndarray) -> dict[str, Any]:
    digest = cp.get("artifact_sha256", cp.get("sha256"))
    artifact = load_artifact(cp["path"], digest)
    bits = stage_a._bits(artifact["decoded"], 2048)
    if stage_a._syndrome(H, bits) != cp["syndrome_weight"]:
        raise ValueError("checkpoint syndrome differs")
    elapsed = float(cp[clock_key])
    if not np.isfinite(elapsed) or elapsed < 0:
        raise ValueError("invalid durable checkpoint clock")
    return {"round": cp["round"], "ready_seconds": elapsed,
            "info_correct": bool(np.array_equal(bits[free], info)),
            "coded_correct": bool(np.array_equal(bits, coded)),
            "syndrome_weight": cp["syndrome_weight"]}


def _result(decoded: np.ndarray, info: np.ndarray, weight: int,
            coded_truth: np.ndarray, info_truth: np.ndarray,
            checkpoints: list[dict], components: dict[str, float],
            triggered: bool) -> dict[str, Any]:
    if any(not np.isfinite(value) or value < 0 for value in components.values()):
        raise ValueError("invalid component time")
    if (not checkpoints or checkpoints != sorted(
            checkpoints, key=lambda cp: cp["ready_seconds"])):
        raise ValueError("durable checkpoint order differs")
    return {"info_correct": bool(np.array_equal(info, info_truth)),
            "coded_correct": bool(np.array_equal(decoded, coded_truth)),
            "coded_errors": int(np.count_nonzero(decoded != coded_truth)),
            "syndrome_weight": weight,
            "valid_but_wrong": bool(weight == 0 and not np.array_equal(decoded, coded_truth)),
            "triggered": triggered, "checkpoints": checkpoints,
            "components": components}


def _f1_schedule(index: int) -> tuple[str, ...]:
    if index % 16 == 0:
        return tuple(permutations(F1_ARMS))[(index // 16) % 6]
    ordinal = index - 1 - index // 16
    return ("B", "Ccompat") if ordinal % 2 == 0 else ("Ccompat", "B")


def _index_f1(rows: list[dict]) -> dict[str, dict[str, dict]]:
    if len(rows) != 2112 or any(row.get("status") != "ok" for row in rows):
        raise ValueError("F1 2112-call full coverage required")
    grouped: dict[str, dict[str, dict]] = {}
    for index, row in enumerate(rows, 1):
        if row["attempt_index"] != index:
            raise ValueError("F1 attempt order differs")
        group = grouped.setdefault(row["observation_id"], {})
        if row["arm"] in group:
            raise ValueError("duplicate F1 arm")
        group[row["arm"]] = row
    if len(grouped) != N:
        raise ValueError("F1 frame denominator differs")
    actual = [(row["observation_id"], row["arm"]) for row in rows]
    expected = [(f"s650_f{i:04d}", arm) for i in range(N)
                for arm in _f1_schedule(i)]
    if actual != expected:
        raise ValueError("F1 fixed matched schedule differs")
    return grouped


def _index_f2(ledger: list[dict], policies: list[dict],
              names: list[str], seal: dict) -> dict[str, dict[str, dict]]:
    if (len(policies) != N * len(names)
            or len(ledger) != seal["actual_total_calls"]
            or any(row.get("status") != "ok" for row in ledger + policies)
            or len({row["attempt"] for row in ledger}) != len(ledger)
            or sorted(row["attempt"] for row in ledger) != list(range(1, len(ledger) + 1))):
        raise ValueError("F2 actual-call/policy allocation incomplete")
    by_frame: dict[str, dict[str, dict]] = {}
    for row in policies:
        group = by_frame.setdefault(row["observation_id"], {})
        if row["policy"] in group:
            raise ValueError("duplicate F2 logical policy")
        group[row["policy"]] = row
    if (len(by_frame) != N or any(set(by_frame[f"s650_f{i:04d}"]) != set(names)
                               for i in range(N))):
        raise ValueError("F2 1024 rows per admitted policy required")
    return by_frame


def _summarize(records: dict[str, dict[str, dict]]) -> dict[str, Any]:
    names = sorted({name for frame in records.values() for name in frame})
    arms = {}
    for name in names:
        selected = [records[stem][name] for stem in sorted(records)
                    if name in records[stem]]
        n = len(selected)
        if n not in (64, N):
            raise ValueError("unsupported outcome denominator")
        fields = sorted({field for row in selected for field in row["components"]})
        times = {field: stage_a.distribution(
            [row["components"].get(field, 0.0) for row in selected], expected=n)
                 for field in fields}
        deadlines = {}
        for deadline in DEADLINES:
            states = [stage_a.latest_ready(row["checkpoints"], deadline)
                      for row in selected]
            deadlines[str(deadline)] = {
                "n": n, "correct": sum(state["correct"] for state in states),
                "wrong_ready": sum(state["ready"] and not state["correct"]
                                   for state in states),
                "missing": sum(not state["ready"] for state in states)}
        executed_branch_costs = [row["components"].get("branch_complete_seconds", 0.0)
                                 for row in selected
                                 if row["components"].get("branch_complete_seconds", 0.0) > 0]
        arms[name] = {"n": n,
                      "information_FER": 1 - sum(row["info_correct"] for row in selected)/n,
                      "coded_BER": sum(row["coded_errors"] for row in selected)/(2048*n),
                      "information_failures": sum(not row["info_correct"] for row in selected),
                      "coded_bit_errors": sum(row["coded_errors"] for row in selected),
                      "syndrome_nonzero": sum(row["syndrome_weight"] != 0 for row in selected),
                      "valid_but_wrong": sum(row["valid_but_wrong"] for row in selected),
                      "triggered_prefix_nonzero": sum(row["triggered"] for row in selected),
                      "executed_branch_n": len(executed_branch_costs),
                      "numerical_failures": 0, "timing": times,
                      "branch_cost_conditional_on_execution": (
                          stage_a.distribution(executed_branch_costs)
                          if executed_branch_costs else None),
                      "branch_cost_population": stage_a.distribution(
                          [row["components"].get("branch_complete_seconds", 0.0)
                           for row in selected], expected=n),
                      "deadlines": deadlines}
    pairs = {}
    for left, right in combinations(names, 2):
        common = [stem for stem in sorted(records)
                  if left in records[stem] and right in records[stem]]
        a = np.asarray([records[stem][left]["info_correct"] for stem in common], dtype=bool)
        b = np.asarray([records[stem][right]["info_correct"] for stem in common], dtype=bool)
        pairs[f"{left}_vs_{right}"] = stage_a.paired_table(a, b)
    return {"arms": arms, "paired": pairs}


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    seal, observed_inventory, population, truth_rows = verify_pretruth(args)
    sys.path.insert(0, str(args.baseline / "src"))
    import evidence  # type: ignore[import-not-found]  # evidence codec only
    observed = args.f1_observed if args.campaign == "f1" else args.f2_observed
    artifact_cache: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}

    def load_observed(relative: str, digest: str,
                      identity: dict[str, Any] | None = None) -> dict[str, Any]:
        if observed_inventory.get(relative, {}).get("sha256") != digest:
            raise ValueError(f"raw/checkpoint hash differs: {relative}")
        if relative not in artifact_cache:
            path = stage_a._safe(observed, relative)
            artifact_cache[relative] = evidence.load_artifact(path)
        payload, actual_identity = artifact_cache[relative]
        if identity is not None and actual_identity != identity:
            raise ValueError(f"raw/checkpoint semantic identity differs: {relative}")
        return payload
    cache = (args.baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
             "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    stage_reg = json.loads(args.stage_a_registration.read_text())
    H, G, free = stage_a._code_arrays(cache, stage_reg)
    if args.campaign == "f1":
        f1rows = _jsonl(args.f1_observed / "ledger.jsonl")
        f1_attempts = _jsonl(args.f1_observed / "attempts.jsonl")
        if (len(f1_attempts) != len(f1rows) or
                any(any(row[key] != started[key] for key in
                        ("attempt_index", "observation_id", "arm", "input_sha256"))
                    for row, started in zip(f1rows, f1_attempts, strict=True))):
            raise ValueError("F1 durable attempt journal differs")
        f1by = _index_f1(f1rows)
    else:
        f2rows = _jsonl(args.f2_observed / "ledger.jsonl")
        f2attempts = _jsonl(args.f2_observed / "attempts.jsonl")
        f2policies = _jsonl(args.f2_observed / "policy_ledger.jsonl")
        f2manifest = json.loads((args.f2_observed / "manifest.json").read_text())
        names = f2manifest["policy_names"]
        if (len(f2rows) != len(f2attempts)
                or any(row["attempt"] != started["attempt"] or
                       row["arm"] != started["arm"] or
                       row["observation_id"] != started["observation_id"]
                       for row, started in zip(f2rows, f2attempts, strict=True))
                or (args.f2_observed / "failed_calls.jsonl").read_text().strip()):
            raise ValueError("F2 durable attempts or failure ledger differs")
        f2by = _index_f2(f2rows, f2policies, names, seal)
        actual_f2 = {(row["observation_id"], row["arm"]): row for row in f2rows}
        if len(actual_f2) != len(f2rows):
            raise ValueError("duplicate actual F2 continuation")
    f1out: dict[str, dict[str, dict]] = {}
    f2out: dict[str, dict[str, dict]] = {}
    frame_table = []
    deadline_table = []
    components_table = []
    for frame, (input_row, truth_row) in enumerate(zip(population, truth_rows, strict=True)):
        stem = input_row["observation_id"]
        tagged = stage_a._artifact(evidence, args.population_truth,
                                   truth_row["truth_path"], truth_row["truth_sha256"])
        if (tagged["observation_hash"] != input_row["observation_hash"]
                or tagged["stream_ids"] != input_row["stream_ids"]):
            raise ValueError("truth artifact is not this observation")
        coded, info = stage_a._validate_truth(tagged, H, G, free)
        f1out[stem] = {}
        for arm, row in (f1by[stem].items() if args.campaign == "f1" else ()):
            if (row["input_sha256"] != input_row["observation_sha256"]
                    or row["observation_hash"] != input_row["observation_hash"]
                    or row["stream_ids"] != input_row["stream_ids"]
                    or row["frame"] != frame):
                raise ValueError("F1 row input differs")
            raw = load_observed(row["raw_path"], row["raw_sha256"],
                {"schema": "cstate-necessity-stage-b-f1-compat/1",
                 "observation_id": stem, "arm": arm,
                 "input_sha256": row["input_sha256"]})
            if (raw["observation_id"] != stem or raw["arm"] != arm
                    or raw["input_sha256"] != row["input_sha256"]
                    or raw["stream_ids"] != input_row["stream_ids"]):
                raise ValueError("F1 raw semantic identity differs")
            decision = json.loads((args.f1_observed / row["decision_path"]).read_text())
            if observed_inventory.get(row["decision_path"], {}).get("sha256") != row["decision_sha256"]:
                raise ValueError("F1 decision hash differs")
            decoded, extracted, weight = _bits(raw, decision, H, free)
            if (decision["raw_sha256"] != row["raw_sha256"]
                    or row["final_decoded_sha256"] != hashlib.sha256(decoded.tobytes()).hexdigest()
                    or weight != row["final_syndrome_weight"]
                    or decision["checkpoints"] != row["checkpoints"]
                    or len(row["checkpoints"]) != 2 + int(row["triggered"])
                    or [cp["round"] for cp in row["checkpoints"]] !=
                       list(range(len(row["checkpoints"])))
                    or row["triggered"] != (arm == "B" and
                         row["checkpoints"][1]["syndrome_weight"] != 0)):
                raise ValueError("F1 raw/decision/ledger binding differs")
            cps = [_checkpoint(load_observed, cp, H, free, info,
                               clock_key="ready_seconds", coded=coded)
                   for cp in row["checkpoints"]]
            if not np.array_equal(
                    load_observed(row["checkpoints"][-1]["path"],
                                  row["checkpoints"][-1]["artifact_sha256"])["decoded"], decoded):
                raise ValueError("F1 last durable bits differ from final decision")
            if (not np.array_equal(stage_a._bits(raw["baseline_arrays"]["r1_decoded"], 2048),
                                   load_observed(row["checkpoints"][1]["path"],
                                                 row["checkpoints"][1]["artifact_sha256"])["decoded"])
                    or row["checkpoints"][-1]["ready_seconds"] > row["complete_latency_seconds"]):
                raise ValueError("F1 native/checkpoint clock differs")
            fields = ("complete_latency_seconds", "acquisition_seconds",
                      "native_seconds", "refit_seconds", "tf_seconds",
                      "decoder_seconds", "branch_seconds", "raw_serialization_seconds",
                      "decision_record_seconds")
            component = {key: float(row[key]) for key in fields}
            component["branch_complete_seconds"] = (
                component["complete_latency_seconds"] -
                float(row["checkpoints"][1]["ready_seconds"])
                if row["triggered"] else 0.0)
            f1out[stem][arm] = _result(decoded, extracted, weight, coded, info,
                                        cps, component, bool(row["triggered"]))
        f2out[stem] = {}
        actual = {}
        for (other_stem, arm), row in (actual_f2.items() if args.campaign == "f2" else ()):
            if other_stem != stem:
                continue
            if (row["input_sha256"] != input_row["observation_sha256"]
                    or row["observation_hash"] != input_row["observation_hash"]
                    or row["stream_ids"] != input_row["stream_ids"]):
                raise ValueError("F2 actual input differs")
            expected_identity = {"observation_id": stem, "arm": arm,
                                 "input_sha256": row["input_sha256"]}
            if row["kind"] == "continuation":
                expected_identity = {"observation_id": stem, "arm": arm,
                                     "prefix_raw_sha256": row["prefix_raw_sha256"]}
            raw = load_observed(row["raw_path"], row["raw_sha256"], expected_identity)
            if (raw["observation_id"] != stem or raw["arm"] != arm
                    or raw["input_sha256"] != row["input_sha256"]
                    or raw["observation_hash"] != input_row["observation_hash"]
                    or raw["stream_ids"] != input_row["stream_ids"]):
                raise ValueError("F2 raw semantic identity differs")
            decision_path = args.f2_observed / row["decision_path"]
            if observed_inventory.get(row["decision_path"], {}).get("sha256") != row["decision_sha256"]:
                raise ValueError("F2 actual decision hash differs")
            decision = json.loads(decision_path.read_text())
            decoded, extracted, weight = _bits(raw, decision, H, free)
            if (row["raw_sha256"] != decision["raw_sha256"]
                    or row["final_syndrome_weight"] != weight
                    or row["checkpoints"] != decision["checkpoints"]):
                raise ValueError("F2 actual raw/decision/ledger differs")
            actual[arm] = (row, decoded, extracted, raw)
        if args.campaign == "f2" and set(F2_PREFIXES) - set(actual):
            raise ValueError("F2 paid prefix missing")
        used_actual = set(F2_PREFIXES) if args.campaign == "f2" else set()
        for policy, row in (f2by[stem].items() if args.campaign == "f2" else ()):
            parent = "F2E" if policy.startswith("F2E") else "F0"
            parent_row = actual[parent][0]
            branch = row["branch_arm"]
            if (row["input_sha256"] != input_row["observation_sha256"]
                    or row["prefix_arm"] != parent
                    or row["prefix_raw_sha256"] != parent_row["raw_sha256"]
                    or row["triggered"] != (parent_row["final_syndrome_weight"] != 0)
                    or row["frame"] != frame):
                raise ValueError("F2 logical parent/trigger differs")
            if branch is None:
                if row["triggered"] and policy not in F2_PREFIXES:
                    raise ValueError("triggered F2 continuation missing")
                source = parent
                branch_cost = 0.0
            else:
                if not row["triggered"] or branch != policy or branch not in actual:
                    raise ValueError("F2 branch source differs")
                source = branch
                used_actual.add(branch)
                branch_cost = actual[branch][0]["complete_latency_seconds"]
            source_row, decoded, extracted, source_raw = actual[source]
            if (row["source_of_final_bits"] != source_row["raw_path"]
                    or row["final_decoded_sha256"] != hashlib.sha256(decoded.tobytes()).hexdigest()
                    or row["final_info_sha256"] != hashlib.sha256(extracted.tobytes()).hexdigest()
                    or row["final_syndrome_weight"] != source_row["final_syndrome_weight"]
                    or not np.isclose(row["complete_latency_seconds"],
                                      parent_row["complete_latency_seconds"] + branch_cost,
                                      rtol=0, atol=1e-9)):
                raise ValueError("F2 logical decision/cost differs")
            cps = [_checkpoint(load_observed, cp, H, free, info,
                               clock_key="durable_seconds", coded=coded)
                   for cp in row["checkpoints"]]
            if not np.array_equal(
                    load_observed(row["checkpoints"][-1]["path"],
                                  row["checkpoints"][-1]["sha256"])["decoded"], decoded):
                raise ValueError("F2 last durable bits differ from final decision")
            if (len(cps) != (3 if branch else 2)
                    or cps[-1]["ready_seconds"] > row["complete_latency_seconds"]):
                raise ValueError("F2 logical checkpoint allocation differs")
            expected_cp = parent_row["checkpoints"] + (
                [] if branch is None else actual[branch][0]["checkpoints"])
            for saved, logical in zip(expected_cp, row["checkpoints"], strict=True):
                offset = 0.0 if saved in parent_row["checkpoints"] else \
                    parent_row["complete_latency_seconds"]
                if (saved["path"] != logical["path"] or
                        saved["sha256"] != logical["sha256"] or
                        not np.isclose(logical["durable_seconds"],
                                       offset + saved["durable_seconds"], rtol=0, atol=1e-9)):
                    raise ValueError("F2 durable clock/source differs")
            parent_raw = actual[parent][3]
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
                    actual[branch][0]["branch_setup_and_deepcopy_seconds"])),
                "branch_receiver_seconds_including_checkpoint": (0.0 if branch is None else float(
                    actual[branch][0]["receiver_seconds_including_checkpoint"])),
                "branch_post_receiver_serialization_and_validation_seconds": (
                    0.0 if branch is None else float(actual[branch][0][
                        "post_receiver_serialization_and_validation_seconds"])),
                "branch_checkpoint_serialization_nested_seconds": (0.0 if branch is None else float(
                    actual[branch][0]["checkpoint_serialization_seconds"])),
            }
            if parent == "F2E":
                for key, value in parent_raw["front"]["timing"]["component_seconds"].items():
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
                raise ValueError("F2 mutually exclusive wall components do not close")
            f2out[stem][policy] = _result(decoded, extracted,
                source_row["final_syndrome_weight"], coded, info, cps,
                components, bool(row["triggered"]))
        if args.campaign == "f2" and used_actual != set(actual):
            raise ValueError("F2 paid call lacks a registered logical policy")
        campaign_rows = f1out[stem] if args.campaign == "f1" else f2out[stem]
        campaign = args.campaign.upper()
        for name, result in campaign_rows.items():
            frame_table.append({"campaign": campaign, "observation_id": stem,
                "frame": frame, "arm_or_policy": name,
                "info_correct": result["info_correct"],
                "coded_correct": result["coded_correct"],
                "coded_errors": result["coded_errors"],
                "syndrome_weight": result["syndrome_weight"],
                "valid_but_wrong": result["valid_but_wrong"],
                "triggered": result["triggered"]})
            components_table.append({"campaign": campaign,
                "observation_id": stem, "frame": frame, "arm_or_policy": name,
                **result["components"]})
            for deadline in DEADLINES:
                state = stage_a.latest_ready(result["checkpoints"], deadline)
                deadline_table.append({"campaign": campaign,
                    "observation_id": stem, "frame": frame, "arm_or_policy": name,
                    "deadline_seconds": deadline, "ready": state["ready"],
                    "correct": state["correct"], "round": state["round"]})
        artifact_cache.clear()  # Shared checkpoints within one frame, bounded RAM overall.
    if args.campaign == "f2" and sum(f2out[stem]["F0"]["triggered"] for stem in f2out) != 40:
        raise ValueError("historical 40 F0 trigger cohort differs")
    summary = _summarize(f1out if args.campaign == "f1" else f2out)
    report = {"schema": "method-closure-offline-analysis/1",
              "status": "pass", "campaign": args.campaign,
              "population": "sealed exposed 6.5-dB developmental 1024",
              "input_sha256": {"observed_seal": stage_a.sha256((args.f1_observed if args.campaign == "f1" else args.f2_observed) / "observed_seal.json"),
                               "truth_seal": stage_a.sha256(args.population_truth / "truth_seal.json"),
                               "ledger": stage_a.sha256((args.f1_observed if args.campaign == "f1" else args.f2_observed) / "ledger.jsonl")},
              "git_attestation_verified_before_truth": True,
              "summary": summary,
              "timing_boundary": "F1 and F2 clocks are distinct campaigns; no raw seconds pooled",
              "component_semantics": (
                  "F1 branch_seconds is producer branch stage; branch_complete_seconds "
                  "is full completion minus durable native-r1 checkpoint, including "
                  "branch and final raw/decision serialization. F2 input/receiver/"
                  "post-receiver clocks are exclusive within each call; checkpoint, "
                  "front, and exclusive-stage fields are nested in receiver and "
                  "must not be added again"),
              "population_numerical_failures": 0}
    args.out.mkdir(parents=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (args.out / "observed_file_inventory.json").write_text(
        json.dumps(observed_inventory, indent=2, sort_keys=True) + "\n")
    for filename, rows in (("frame_outcomes.csv", frame_table),
                           ("deadline_decisions.csv", deadline_table),
                           ("component_timing.csv", components_table)):
        with (args.out / filename).open("x", newline="") as stream:
            csv_fields = sorted({key for row in rows for key in row})
            writer = csv.DictWriter(stream, fieldnames=csv_fields, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", choices=("f1", "f2"), required=True)
    for name in ("f1-observed", "f2-observed", "population-observed",
                 "population-truth", "stage-a-registration", "f1-registration",
                 "f2-registration", "baseline", "f1-git-attestation",
                 "f2-git-attestation", "out"):
        parser.add_argument("--" + name, type=Path)
    for name in ("f1-git-attestation-sha256", "f2-git-attestation-sha256",
                 "f1-observed-commit", "f2-observed-commit",
                 "f1-seal-repo-path", "f2-seal-repo-path",
                 "f2-registration-commit"):
        parser.add_argument("--" + name)
    args = parser.parse_args()
    common = ("population_observed", "population_truth", "stage_a_registration",
              "baseline", "out")
    specific = (("f1_observed", "f1_registration", "f1_git_attestation",
                 "f1_git_attestation_sha256", "f1_observed_commit", "f1_seal_repo_path")
                if args.campaign == "f1" else
                ("f2_observed", "f2_registration", "f2_git_attestation",
                 "f2_git_attestation_sha256", "f2_observed_commit", "f2_seal_repo_path",
                 "f2_registration_commit"))
    for name in (*common, *specific):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required for {args.campaign}")
    analyze(args)


if __name__ == "__main__":
    main()
