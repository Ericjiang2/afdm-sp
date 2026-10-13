"""Observed-only shared-prefix Stage-B F2 developmental campaign.

One paid F0 prefix and one paid F2E prefix per sealed observation. Failed
prefixes fork only from immutable saved APP/check arrays. Logical policy costs
charge their whole prefix plus their own branch, while actual calls are counted
separately. No truth, generator, or analysis module is imported here.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
PROJECT = EXPERIMENTS.parent
sys.path[:0] = [str(EXPERIMENTS / "tf_production_gap_audit_20260922"),
                str(EXPERIMENTS / "tf_cstate_validation_20260922"),
                str(EXPERIMENTS / "cstate_necessity_stageA_20260928")]
from audit_io import attach, load_bound  # noqa: E402


SCHEMA = "f2-stage-b-shared-prefix/1"
POLICIES = ("F0", "B", "F0_LOCAL", "F2T", "F2E", "F2E_LOCAL", "F2E_CSTATE")
REQUIRED_POLICIES = set(POLICIES) - {"F2E_CSTATE"}
PRODUCER_FILES = ("f2_estimator.py", "f2_receiver.py", "f2_run_population.py")


def _timeout(_signum, _frame):
    raise TimeoutError("locked F2 population wrapper cap reached")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> str:
    with path.open("x") as stream:
        json.dump(payload, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return sha256(path)


def append_json(path: Path, payload: dict) -> None:
    with path.open("a") as stream:
        json.dump(payload, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def record_failed_call(out: Path, *, attempt: int, kind: str, arm: str,
                       observation_id: str, origin: float,
                       error: BaseException) -> None:
    checkpoints = sorted(str(path.relative_to(out)) for path in
                         (out / "checkpoints").glob(f"{observation_id}_{arm}_r*.npz"))
    append_json(out / "failed_calls.jsonl", {
        "status": "failed", "attempt": attempt, "kind": kind,
        "arm": arm, "observation_id": observation_id,
        "charged_seconds": time.perf_counter() - origin,
        "saved_checkpoint_paths": checkpoints,
        "error": repr(error)})


def verify_inventory(root: Path, seal_name: str,
                     *, allowed_status: tuple[str, ...] = ("pass", "complete")) -> dict:
    seal_path = root / seal_name
    seal = json.loads(seal_path.read_text())
    files = seal.get("files")
    if seal.get("status") not in allowed_status or not isinstance(files, dict):
        raise ValueError(f"invalid sealed input inventory: {root}")
    actual = {str(path.relative_to(root)): sha256(path) for path in root.rglob("*")
              if path.is_file() and path.name != seal_name}
    if actual != files:
        raise ValueError(f"sealed input file inventory differs: {root}")
    return seal


def syndrome(H: np.ndarray, decoded: np.ndarray) -> int:
    bits = np.asarray(decoded, dtype=np.uint8)
    if bits.shape != (2048,) or not np.isin(bits, (0, 1)).all():
        raise ValueError("invalid saved coded decision")
    return int(np.count_nonzero((H @ bits) % 2))


def select_650_rows(rows: list[dict]) -> list[dict]:
    selected = [row for row in rows if row["snr_centi_db"] == 650]
    if (len(rows) != 3072 or len(selected) != 1024 or
            [row["frame"] for row in selected] != list(range(1024)) or
            [row["observation_id"] for row in selected] !=
                [f"s650_f{i:04d}" for i in range(1024)]):
        raise ValueError("fixed 6.5-dB 1024-frame cohort differs")
    return selected


def schedule(frame: int) -> tuple[str, str]:
    """Alternate the two paid prefixes; continuation order is set later."""
    prefixes = ("F0", "F2E") if frame % 2 == 0 else ("F2E", "F0")
    return prefixes


def rotate(names: tuple[str, ...], ordinal: int) -> tuple[str, ...]:
    offset = (ordinal - 1) % len(names)
    return names[offset:] + names[:offset]


def preflight(args):
    if args.out.exists() or not args.out.resolve().is_relative_to(
            Path("/data/guoyikun").resolve()):
        raise ValueError("new output root must be below /data/guoyikun")
    if any(os.environ.get(key) != "1" for key in
           ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")):
        raise ValueError("one CPU thread environment required")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("CUDA must be hidden")
    if sha256(args.manifest) != args.manifest_sha256:
        raise ValueError("locked manifest SHA differs")
    manifest = json.loads(args.manifest.read_text())
    listed = manifest.get("policy_names")
    if (manifest.get("schema") != SCHEMA or manifest.get("status") != "locked"
            or manifest.get("frames") != 1024
            or manifest.get("maximum_prefix_calls") != 2048
            or manifest.get("maximum_f0_continuations") != 120
            or manifest.get("maximum_f2e_continuations") != 2048
            or manifest.get("output_relative_path") != str(
                args.out.resolve().relative_to(PROJECT.resolve()))
            or type(manifest.get("maximum_wall_seconds")) is not int
            or manifest["maximum_wall_seconds"] <= 0
            or type(manifest.get("outer_hard_wall_seconds")) is not int
            or not manifest["maximum_wall_seconds"] <
                manifest["outer_hard_wall_seconds"] <= 604800
            or manifest.get("truth_used") is not False
            or not isinstance(listed, list) or set(listed) not in
                (REQUIRED_POLICIES, set(POLICIES)) or len(listed) != len(set(listed))
            or listed != [name for name in POLICIES if name in listed]):
        raise ValueError("developmental allocation differs")
    caps = manifest.get("per_call_cap_seconds")
    if (not isinstance(caps, dict) or set(caps) != {"F0", "F2E"} | set(listed)
            or any(type(value) is not int or value <= 0 for value in caps.values())):
        raise ValueError("per-call operational caps not frozen")
    if set(manifest.get("producer_source_hashes", {})) != set(PRODUCER_FILES) or any(
            manifest["producer_source_hashes"][name] != sha256(HERE / name)
            for name in PRODUCER_FILES):
        raise ValueError("producer source differs")
    if (manifest.get("launcher_sha256") !=
            sha256(HERE / "f2_launch_population_once.sh")):
        raise ValueError("population launcher source differs")
    root = PROJECT / "results/cstate_necessity_stageB_resume_20260928"
    protocol_files = {
        "method_sha256": root / "F2_METHOD_CONTRACT.md",
        "numerical_amendment_sha256": root / "F2_NUMERICAL_AMENDMENT.md",
        "population_protocol_sha256": root / "F2_POPULATION_PROTOCOL.md",
        "population_budget_sha256": root / "F2_POPULATION_BUDGET.md",
        "small_reference_qualification_sha256": root / "F2_SMALL_REFERENCE_QUALIFICATION.md",
    }
    if any(sha256(path) != manifest.get(key) for key, path in protocol_files.items()):
        raise ValueError("frozen F2 method/protocol qualification binding differs")
    dependencies = manifest.get("dependency_source_hashes")
    required_dependencies = {
        "cstate_necessity_stageA_20260928/run_stage_a.py",
        "tf_cstate_validation_20260922/run_validation.py",
        "tf_cstate_validation_20260922/geometry_validation.py",
        "tf_cstate_validation_20260922/compact_state.py",
        "tf_geometry_reopen_20260922/geometry_reopen.py",
        "tf_production_gap_audit_20260922/audit_io.py",
    }
    if (not isinstance(dependencies, dict) or
            not required_dependencies.issubset(dependencies)):
        raise ValueError("dependency source bindings missing")
    for relative, digest in dependencies.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("dependency path escapes experiments")
        resolved = (EXPERIMENTS / path).resolve()
        if not resolved.is_relative_to(EXPERIMENTS.resolve()) or sha256(resolved) != digest:
            raise ValueError(f"dependency source differs: {relative}")
    population_seal = verify_inventory(args.population_observed, "observed_seal.json")
    historical_seal = verify_inventory(args.historical_observed, "observed_seal.json")
    branch_seal = verify_inventory(
        args.branch_qualification, "observed_seal.json",
        allowed_status=("pass", "partial_qualified"))
    if (sha256(args.branch_qualification / "observed_seal.json") !=
            manifest.get("branch_qualification_seal_sha256") or
            branch_seal.get("schema") != "f2-three-branch-qualification/1" or
            branch_seal.get("truth_values_read") is not False):
        raise ValueError("saved-state branch qualification seal differs")
    qualified = branch_seal.get("qualified_arms")
    mandatory = ["f0044_F2T", "f0000_F2E_LOCAL"]
    if (not isinstance(qualified, list) or qualified[:2] != mandatory or
            branch_seal.get("completed_continuations") != len(qualified) or
            branch_seal.get("run_manifest_sha256") !=
                manifest.get("branch_qualification_manifest_sha256")):
        raise ValueError("mandatory saved-state continuations not qualified")
    optional = "F2E_CSTATE" in listed
    if branch_seal["status"] == "pass":
        if qualified != mandatory + ["f0000_F2E_CSTATE"] or not optional:
            raise ValueError("qualified optional policy omitted or mismatched")
    else:
        if (qualified != mandatory or optional or
                branch_seal.get("excluded_arm") != "f0000_F2E_CSTATE"):
            raise ValueError("nonqualified CSTATE policy cannot enter campaign")
        failure = json.loads((args.branch_qualification / "failure.json").read_text())
        if (failure.get("status") != "optional_arm_not_qualified" or
                failure.get("current_arm") != branch_seal["excluded_arm"] or
                failure.get("numerical_failure") is not True):
            raise ValueError("optional qualification failure is not numerical")
    branch_rows = [json.loads(line) for line in
                   (args.branch_qualification / "ledger.jsonl").read_text().splitlines()]
    branch_attempts = [json.loads(line) for line in
                       (args.branch_qualification / "attempts.jsonl").read_text().splitlines()]
    if ([row.get("arm") for row in branch_rows] != qualified or
            any(row.get("status") != "ok" for row in branch_rows) or
            [row.get("arm") for row in branch_attempts] !=
                ["f0044_F2T", "f0000_F2E_LOCAL", "f0000_F2E_CSTATE"]):
        raise ValueError("branch qualification ledger/attempt sequence differs")
    if (sha256(args.population_observed / "observed_seal.json") !=
            manifest.get("population_observed_seal_sha256") or
            sha256(args.historical_observed / "observed_seal.json") !=
            manifest.get("stage_a_observed_seal_sha256")):
        raise ValueError("sealed developmental input binding differs")
    rows = select_650_rows([json.loads(line) for line in
            (args.population_observed / "ledger.jsonl").read_text().splitlines()])
    for row in rows:
        if (population_seal["files"].get(row["observation_path"]) !=
                row["observation_sha256"]):
            raise ValueError("population row/file binding differs")
    old_rows = [json.loads(line) for line in
                (args.historical_observed / "ledger.jsonl").read_text().splitlines()]
    previous_f0 = {row["observation_id"]: row for row in old_rows
                   if row.get("arm") == "A"}
    if len(previous_f0) != 1024 or sum(
            row["baseline_syndrome_weight"] > 0 for row in previous_f0.values()) != 40:
        raise ValueError("old F0 1024/40 reference differs")
    if any(historical_seal["files"].get(row["raw_path"]) != row["raw_sha256"]
           for row in previous_f0.values()):
        raise ValueError("old F0 raw binding differs")
    for input_row in rows:
        previous = previous_f0[input_row["observation_id"]]
        if (previous["frame"] != input_row["frame"] or
                previous["input_sha256"] != input_row["observation_sha256"] or
                previous["observation_hash"] != input_row["observation_hash"] or
                previous["stream_ids"] != input_row["stream_ids"]):
            raise ValueError("old F0 and current input identities differ")
    evidence = attach(args.source, args.baseline)
    if (evidence.source_hashes(args.source) != manifest.get("native_source_hashes")
            or evidence.source_hashes(args.baseline) != manifest.get("baseline_source_hashes")):
        raise ValueError("frozen source hashes differ")
    cache = args.baseline / (
        "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
        "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    if sha256(cache) != manifest.get("ldpc_cache_sha256"):
        raise ValueError("frozen code cache differs")
    from receiver import context  # noqa: PLC0415 - after source hashes
    import native_twofft as native  # noqa: PLC0415
    import geometry_validation as kernel  # noqa: PLC0415
    from run_validation import _branch  # noqa: PLC0415
    from f2_receiver import receive_f2e, continue_f2t  # noqa: PLC0415
    from receiver import extract_info  # noqa: PLC0415
    environment = evidence.bind_runtime_environment()
    system, _, code, header = context()
    evidence.verify_runtime_binding()
    if (system.N_total != 1024 or system.rho != 0.5 or system.l_max_cap != 102
            or header["code_g_sha256"] != manifest.get("code_g_sha256")):
        raise ValueError("system or code generator differs")
    with np.load(cache, allow_pickle=False) as saved:
        H = np.asarray(saved["H"])
    return dict(manifest=manifest, rows=rows, previous_f0=previous_f0,
                evidence=evidence, native=native, kernel=kernel, branch=_branch,
                receive_f2e=receive_f2e, continue_f2t=continue_f2t,
                extract_info=extract_info, system=system, code=code, H=H,
                environment=environment)


def _front_summary(front: dict) -> dict:
    channel = front["channel"]
    return {**{key: value for key, value in front.items() if key != "channel"},
            "channel": {"delays": channel.delays, "dopplers": channel.dopplers,
                        "gains": channel.gains}}


def _input(bound: dict, args, row: dict) -> dict:
    payload = load_bound(bound["evidence"],
                         args.population_observed / row["observation_path"],
                         row["observation_sha256"])
    if (payload["observation_id"] != row["observation_id"]
            or payload["observation_hash"] != row["observation_hash"]
            or payload["stream_ids"] != row["stream_ids"]
            or set(payload["observation"]) != {"y", "pilot", "sigma2"}):
        raise ValueError("sealed observation semantic identity differs")
    return payload["observation"]


def _prefix(out: Path, args, bound: dict, input_row: dict,
            arm: str, attempt: int, old_arrays: dict | None = None) -> dict:
    """Persist a complete paid prefix before any branch may inspect its state."""
    stem = input_row["observation_id"]
    evidence = bound["evidence"]
    origin = time.perf_counter()
    append_json(out / "attempts.jsonl", {
        "attempt": attempt, "kind": "prefix", "arm": arm,
        "observation_id": stem, "input_sha256": input_row["observation_sha256"],
        "started_epoch": time.time()})
    observation = _input(bound, args, input_row)
    input_seconds = time.perf_counter() - origin
    checkpoints: list[dict] = []
    cp_serialization = 0.0

    def sink(event, decoded):
        nonlocal cp_serialization
        index = len(checkpoints)
        if index > 1 or int(event["round"]) != index:
            raise ValueError("prefix checkpoint order differs")
        ready = time.perf_counter() - origin
        before = time.perf_counter()
        path = out / "checkpoints" / f"{stem}_{arm}_r{index}.npz"
        digest = evidence.save_artifact(path,
            {"event": event, "decoded": np.asarray(decoded, np.uint8)},
            {"observation_id": stem, "arm": arm, "round": index})
        cp_serialization += time.perf_counter() - before
        checkpoints.append({"round": index, "path": str(path.relative_to(out)),
                            "sha256": digest, "decision_ready_seconds": ready,
                            "durable_seconds": time.perf_counter() - origin,
                            "syndrome_weight": syndrome(bound["H"], decoded)})

    receiver_start = time.perf_counter()
    if arm == "F0":
        decoded, arrays, timing = bound["native"].receive(
            observation, bound["system"], bound["code"], rounds=2,
            iterations=20, ce_mode="soft", gain_mode="joint", checkpoint_sink=sink)
        raw_payload = {"native_arrays": arrays, "native_timing": timing}
    elif arm == "F2E":
        decoded, arrays, detail = bound["receive_f2e"](
            observation, bound["system"], bound["code"], checkpoint_sink=sink)
        if detail["estimator"]["channel"].p != 155:
            raise ValueError("F2E changed frozen top155 communications support")
        timing = detail["timing"]
        raw_payload = {"coded_arrays": arrays, "front": _front_summary(detail["estimator"]),
                       "timing": timing}
    else:
        raise ValueError("unknown prefix")
    receiver_seconds = time.perf_counter() - receiver_start
    if len(checkpoints) != 2 or not np.array_equal(
            np.asarray(decoded["decoded"], np.uint8),
            np.asarray(arrays["r1_decoded"], np.uint8)):
        raise ValueError("two-round prefix decision incomplete")
    final_bits = np.asarray(decoded["decoded"], np.uint8).copy()
    final_info = np.asarray(bound["extract_info"](bound["code"], final_bits), np.uint8)
    if final_info.shape != (1024,):
        raise ValueError("prefix information extraction differs")
    final_syndrome = syndrome(bound["H"], final_bits)
    if final_syndrome != checkpoints[-1]["syndrome_weight"]:
        raise ValueError("prefix syndrome/checkpoint differs")
    raw_payload.update(observation_id=stem, arm=arm,
                       input_sha256=input_row["observation_sha256"],
                       observation_hash=input_row["observation_hash"],
                       stream_ids=input_row["stream_ids"],
                       final_decoded=final_bits, final_info=final_info)
    path = out / "raw" / f"{stem}_{arm}.npz"
    raw_sha = evidence.save_artifact(path, raw_payload,
        {"observation_id": stem, "arm": arm,
         "input_sha256": input_row["observation_sha256"]})
    decision_path = out / "decisions" / f"{stem}_{arm}.json"
    decision_sha = write_json(decision_path, {
        "observation_id": stem, "arm": arm, "raw_sha256": raw_sha,
        "final_decoded": final_bits.tolist(), "final_info": final_info.tolist(),
        "final_syndrome_weight": final_syndrome, "checkpoints": checkpoints})
    complete = time.perf_counter() - origin
    post_receiver_seconds = complete - input_seconds - receiver_seconds
    if post_receiver_seconds < 0:
        raise ValueError("prefix mutually exclusive wall components differ")
    if arm == "F0":
        previous = bound["previous_f0"][stem]
        if old_arrays is None:
            raise ValueError("frozen F0 parity state missing")
        from run_stage_a import _compare_saved  # noqa: PLC0415 - frozen parity helper
        _compare_saved(old_arrays, arrays)
        if (previous["baseline_syndrome_weight"] != final_syndrome
                or not np.array_equal(old_arrays["r1_decoded"], final_bits)):
            raise ValueError("new F0 native differs from sealed Stage-A A")
    record = {"status": "ok", "kind": "prefix", "attempt": attempt,
              "observation_id": stem, "arm": arm,
              "input_sha256": input_row["observation_sha256"],
              "observation_hash": input_row["observation_hash"],
              "raw_path": str(path.relative_to(out)), "raw_sha256": raw_sha,
              "decision_path": str(decision_path.relative_to(out)),
              "decision_sha256": decision_sha,
              "checkpoints": checkpoints, "final_syndrome_weight": final_syndrome,
              "input_seconds": input_seconds,
              "receiver_seconds_including_checkpoint": receiver_seconds,
              "post_receiver_serialization_and_validation_seconds":
                  post_receiver_seconds,
              "checkpoint_serialization_seconds": cp_serialization,
              "complete_latency_seconds": complete,
              "historical_parity_outside_clock": arm == "F0",
              "rss_peak_kib_cumulative": resource.getrusage(
                  resource.RUSAGE_SELF).ru_maxrss}
    append_json(out / "ledger.jsonl", record)
    return {"record": record, "observation": observation, "arrays": arrays,
            "final_bits": final_bits, "final_info": final_info}


def _branch(out: Path, bound: dict, input_row: dict, prefix: dict,
            policy: str, attempt: int) -> dict:
    """Only an independent continuation; wait for no other policy is charged."""
    import copy  # noqa: PLC0415 - snapshot before each fork
    stem = input_row["observation_id"]
    evidence = bound["evidence"]
    origin = time.perf_counter()
    append_json(out / "attempts.jsonl", {
        "attempt": attempt, "kind": "continuation", "arm": policy,
        "observation_id": stem, "input_sha256": input_row["observation_sha256"],
        "prefix_raw_sha256": prefix["record"]["raw_sha256"],
        "started_epoch": time.time()})
    arrays = copy.deepcopy(prefix["arrays"])
    checkpoints: list[dict] = []
    cp_serialization = 0.0

    def sink(event, decoded, *, ready_override: float | None = None):
        nonlocal cp_serialization
        if checkpoints or int(event["round"]) not in (0, 2):
            raise ValueError("continuation checkpoint order differs")
        ready = time.perf_counter() - origin if ready_override is None else ready_override
        if not 0 <= ready <= time.perf_counter() - origin:
            raise ValueError("branch decision-ready timestamp differs")
        before = time.perf_counter()
        path = out / "checkpoints" / f"{stem}_{policy}_r2.npz"
        digest = evidence.save_artifact(path,
            {"event": event, "decoded": np.asarray(decoded, np.uint8)},
            {"observation_id": stem, "arm": policy, "round": 2})
        cp_serialization += time.perf_counter() - before
        checkpoints.append({"round": 2, "path": str(path.relative_to(out)),
                            "sha256": digest, "decision_ready_seconds": ready,
                            "durable_seconds": time.perf_counter() - origin,
                            "syndrome_weight": syndrome(bound["H"], decoded)})

    receiver_start = time.perf_counter()
    branch_setup_seconds = receiver_start - origin
    if policy == "F2T":
        if prefix["record"]["arm"] != "F0":
            raise ValueError("F2T needs original F0 prefix")
        decoder, coded_arrays, detail = bound["continue_f2t"](
            prefix["observation"], bound["system"], bound["code"],
            native_app=arrays["r1_app"], native_check=arrays["r1_check"],
            native_syndrome_weight=prefix["record"]["final_syndrome_weight"],
            checkpoint_sink=sink)
        if detail["estimator"]["channel"].p != 155:
            raise ValueError("F2T changed frozen top155 communications support")
        raw_payload = {"coded_arrays": coded_arrays,
                       "front": _front_summary(detail["estimator"]),
                       "timing": detail["timing"],
                       "initial_data": detail["initial_data"]}
    else:
        mode = "LOCAL20" if policy.endswith("LOCAL") else "CSTATE20"
        branch = bound["branch"](prefix["observation"], bound["system"],
                                  bound["code"], bound["native"], bound["kernel"],
                                  arrays, mode)
        result, decoder = branch["result"], branch["decoder"]
        sink({"round": 2, "exclusive_stages": branch["exclusive_stages"],
              "geometry_evaluations": result.evaluations,
              "inference_iterations": 20,
              "decoder_iterations": int(decoder["iterations"])},
             decoder["decoded"],
             ready_override=branch["decision_ready_at"] - origin)
        raw_payload = {"geometry_result": asdict(result),
                       "detector": branch["detector"],
                       "decoder": decoder, "exclusive_stages": branch["exclusive_stages"]}
    receiver_seconds = time.perf_counter() - receiver_start
    if len(checkpoints) != 1:
        raise ValueError("continuation decision checkpoint missing")
    final_bits = np.asarray(decoder["decoded"], np.uint8).copy()
    final_info = np.asarray(bound["extract_info"](bound["code"], final_bits), np.uint8)
    if final_info.shape != (1024,) or syndrome(bound["H"], final_bits) != \
            checkpoints[0]["syndrome_weight"]:
        raise ValueError("continuation final/checkpoint identity differs")
    raw_payload.update(observation_id=stem, arm=policy,
                       input_sha256=input_row["observation_sha256"],
                       observation_hash=input_row["observation_hash"],
                       stream_ids=input_row["stream_ids"],
                       prefix_raw_sha256=prefix["record"]["raw_sha256"],
                       final_decoded=final_bits, final_info=final_info)
    path = out / "raw" / f"{stem}_{policy}.npz"
    raw_sha = evidence.save_artifact(path, raw_payload,
        {"observation_id": stem, "arm": policy,
         "prefix_raw_sha256": prefix["record"]["raw_sha256"]})
    decision_path = out / "decisions" / f"{stem}_{policy}.json"
    decision_sha = write_json(decision_path, {
        "observation_id": stem, "arm": policy, "raw_sha256": raw_sha,
        "final_decoded": final_bits.tolist(), "final_info": final_info.tolist(),
        "final_syndrome_weight": checkpoints[0]["syndrome_weight"],
        "checkpoints": checkpoints})
    complete = time.perf_counter() - origin
    post_receiver_seconds = complete - branch_setup_seconds - receiver_seconds
    if post_receiver_seconds < 0:
        raise ValueError("continuation mutually exclusive wall components differ")
    record = {"status": "ok", "kind": "continuation", "attempt": attempt,
              "observation_id": stem, "arm": policy,
              "input_sha256": input_row["observation_sha256"],
              "observation_hash": input_row["observation_hash"],
              "stream_ids": input_row["stream_ids"],
              "prefix_raw_sha256": prefix["record"]["raw_sha256"],
              "raw_path": str(path.relative_to(out)), "raw_sha256": raw_sha,
              "decision_path": str(decision_path.relative_to(out)),
              "decision_sha256": decision_sha, "checkpoints": checkpoints,
              "final_syndrome_weight": checkpoints[0]["syndrome_weight"],
              "receiver_seconds_including_checkpoint": receiver_seconds,
              "branch_setup_and_deepcopy_seconds": branch_setup_seconds,
              "post_receiver_serialization_and_validation_seconds":
                  post_receiver_seconds,
              "checkpoint_serialization_seconds": cp_serialization,
              "complete_latency_seconds": complete,
              "rss_peak_kib_cumulative": resource.getrusage(
                  resource.RUSAGE_SELF).ru_maxrss}
    append_json(out / "ledger.jsonl", record)
    return {"record": record, "final_bits": final_bits, "final_info": final_info}


def _policy_row(frame: int, input_row: dict, policy: str, prefix: dict,
                branch: dict | None) -> dict:
    parent = prefix["record"]
    final = prefix if branch is None else branch
    checkpoints = [{"round": cp["round"],
                    "decision_ready_seconds": cp["decision_ready_seconds"],
                    "durable_seconds": cp["durable_seconds"],
                    "path": cp["path"], "sha256": cp["sha256"],
                    "syndrome_weight": cp["syndrome_weight"]}
                   for cp in parent["checkpoints"]]
    if branch is not None:
        for cp in branch["record"]["checkpoints"]:
            checkpoints.append({"round": 2,
                "decision_ready_seconds": parent["complete_latency_seconds"] +
                    cp["decision_ready_seconds"],
                "durable_seconds": parent["complete_latency_seconds"] +
                    cp["durable_seconds"], "path": cp["path"],
                "sha256": cp["sha256"],
                "syndrome_weight": cp["syndrome_weight"]})
    complete = parent["complete_latency_seconds"] + (
        0.0 if branch is None else branch["record"]["complete_latency_seconds"])
    if any(checkpoints[i]["durable_seconds"] > checkpoints[i + 1]["durable_seconds"]
           for i in range(len(checkpoints) - 1)):
        raise ValueError("logical durable checkpoint order differs")
    bits = np.asarray(final["final_bits"], np.uint8)
    info = np.asarray(final["final_info"], np.uint8)
    return {"schema": SCHEMA, "status": "ok", "frame": frame,
            "observation_id": input_row["observation_id"], "policy": policy,
            "input_sha256": input_row["observation_sha256"],
            "triggered": parent["final_syndrome_weight"] != 0,
            "prefix_arm": parent["arm"], "prefix_raw_sha256": parent["raw_sha256"],
            "prefix_complete_seconds": parent["complete_latency_seconds"],
            "branch_arm": None if branch is None else branch["record"]["arm"],
            "branch_raw_sha256": None if branch is None else branch["record"]["raw_sha256"],
            "branch_complete_seconds": 0.0 if branch is None else
                branch["record"]["complete_latency_seconds"],
            "complete_latency_seconds": complete, "checkpoints": checkpoints,
            "final_syndrome_weight": parent["final_syndrome_weight"] if branch is None
                else branch["record"]["final_syndrome_weight"],
            "final_decoded_sha256": hashlib.sha256(bits.tobytes()).hexdigest(),
            "final_info_sha256": hashlib.sha256(info.tobytes()).hexdigest(),
            "source_of_final_bits": parent["raw_path"] if branch is None else
                branch["record"]["raw_path"],
            "clock_rule": "prefix full durable cost + own branch full durable cost; other branches excluded"}


def run(args) -> None:
    bound = preflight(args)
    out = args.out
    out.mkdir(parents=True)
    for folder in ("raw", "checkpoints", "decisions"):
        (out / folder).mkdir()
    write_json(out / "manifest.json", {
        "schema": SCHEMA, "status": "running",
        "run_manifest_sha256": args.manifest_sha256,
        "source_hashes": bound["manifest"]["producer_source_hashes"],
        "population_observed_seal_sha256": bound["manifest"]["population_observed_seal_sha256"],
        "stage_a_observed_seal_sha256": bound["manifest"]["stage_a_observed_seal_sha256"],
        "policy_names": bound["manifest"]["policy_names"],
        "runtime_environment": bound["environment"],
        "schedule": "prefix F0/F2E alternating; F0 branches rotate B/F0_LOCAL/F2T; F2E branches alternate",
        "timing_boundary": "per-prefix or per-branch origin before durable attempt journal; through durable raw and decision; analysis/parity overhead excluded from per-policy clocks",
        "cost_rule": "every logical policy pays complete immutable prefix and own complete branch; actual calls separately recorded",
        "failure_rule": "any failure stops invalid_partial; preserve attempts/checkpoints, no subset FER",
        "created_epoch": time.time(), "pid": os.getpid(), "args": sys.argv[:]})
    for name in ("attempts.jsonl", "ledger.jsonl", "policy_ledger.jsonl",
                 "failed_calls.jsonl"):
        (out / name).touch(exist_ok=False)
    prefixes_done = 0
    continuations_done = 0
    f0_trigger_frames = 0
    f2e_trigger_frames = 0
    current = None
    started = time.perf_counter()
    signal.signal(signal.SIGALRM, _timeout)
    try:
        for frame, row in enumerate(bound["rows"]):
            current = row["observation_id"]
            if time.perf_counter() - started >= bound["manifest"]["maximum_wall_seconds"]:
                raise TimeoutError("locked campaign wall cap reached")
            prefix_order = schedule(frame)
            prefix_by_arm = {}
            branch_by_policy = {}
            for arm in prefix_order:
                old_arrays = None
                if arm == "F0":
                    previous = bound["previous_f0"][current]
                    old, _ = bound["evidence"].load_artifact(
                        args.historical_observed / previous["raw_path"])
                    old_arrays = old["baseline_arrays"]
                call_origin = time.perf_counter()
                call_attempt = prefixes_done + continuations_done + 1
                try:
                    signal.alarm(bound["manifest"]["per_call_cap_seconds"][arm])
                    prefix = _prefix(out, args, bound, row, arm,
                                     call_attempt, old_arrays)
                except BaseException as exc:
                    record_failed_call(out, attempt=call_attempt, kind="prefix",
                                       arm=arm, observation_id=current,
                                       origin=call_origin, error=exc)
                    raise
                finally:
                    signal.alarm(0)
                prefixes_done += 1
                prefix_by_arm[arm] = prefix
            fork_plan = []
            if prefix_by_arm["F0"]["record"]["final_syndrome_weight"] != 0:
                f0_trigger_frames += 1
                if f0_trigger_frames > 40:
                    raise ValueError("more than historical 40 F0 trigger frames")
                fork_plan.append(("F0", rotate(("B", "F0_LOCAL", "F2T"),
                                                f0_trigger_frames)))
            if prefix_by_arm["F2E"]["record"]["final_syndrome_weight"] != 0:
                f2e_trigger_frames += 1
                ordered = rotate(("F2E_LOCAL", "F2E_CSTATE"), f2e_trigger_frames)
                fork_plan.append(("F2E", tuple(name for name in ordered if name in
                                                 bound["manifest"]["policy_names"])))
            if frame % 2:
                fork_plan.reverse()
            for arm, ordered in fork_plan:
                for policy in ordered:
                    if time.perf_counter() - started >= bound["manifest"]["maximum_wall_seconds"]:
                        raise TimeoutError("locked campaign wall cap reached")
                    call_origin = time.perf_counter()
                    call_attempt = prefixes_done + continuations_done + 1
                    try:
                        signal.alarm(bound["manifest"]["per_call_cap_seconds"][policy])
                        branch_by_policy[policy] = _branch(
                            out, bound, row, prefix_by_arm[arm], policy,
                            call_attempt)
                    except BaseException as exc:
                        record_failed_call(out, attempt=call_attempt,
                                           kind="continuation", arm=policy,
                                           observation_id=current,
                                           origin=call_origin, error=exc)
                        raise
                    finally:
                        signal.alarm(0)
                    continuations_done += 1
                    if continuations_done > 120 + 2048:
                        raise ValueError("continuation attempt allocation exceeded")
            if prefix_by_arm["F0"]["record"]["final_syndrome_weight"] != \
                    bound["previous_f0"][current]["baseline_syndrome_weight"]:
                raise ValueError("F0 historical trigger parity differs")
            for policy in bound["manifest"]["policy_names"]:
                parent = prefix_by_arm["F2E" if policy.startswith("F2E") else "F0"]
                branch = branch_by_policy.get(policy)
                if (parent["record"]["final_syndrome_weight"] != 0
                        and policy not in ("F0", "F2E") and branch is None):
                    raise ValueError("required triggered continuation missing")
                append_json(out / "policy_ledger.jsonl",
                            _policy_row(frame, row, policy, parent, branch))
        if (prefixes_done != 2048 or f0_trigger_frames != 40 or
                continuations_done > bound["manifest"]["maximum_f0_continuations"]
                + bound["manifest"]["maximum_f2e_continuations"]):
            raise ValueError("complete developmental allocation differs")
        files = {str(path.relative_to(out)): sha256(path) for path in out.rglob("*")
                 if path.is_file() and path.name != "observed_seal.json"}
        write_json(out / "observed_seal.json", {
            "schema": SCHEMA, "status": "pass", "files": files,
            "run_manifest_sha256": args.manifest_sha256,
            "frames": 1024, "actual_prefix_calls": prefixes_done,
            "actual_continuation_calls": continuations_done,
            "actual_total_calls": prefixes_done + continuations_done,
            "f0_trigger_frames": f0_trigger_frames,
            "f2e_trigger_frames": f2e_trigger_frames,
            "logical_policy_rows": 1024 * len(bound["manifest"]["policy_names"]),
            "truth_values_read": False,
            "elapsed_campaign_seconds": time.perf_counter() - started})
    except BaseException as exc:
        attempt_entries = len((out / "attempts.jsonl").read_text().splitlines())
        failed_rows = [json.loads(line) for line in
                       (out / "failed_calls.jsonl").read_text().splitlines()]
        write_json(out / "failure.json", {
            "schema": SCHEMA, "status": "invalid_partial",
            "current_observation_id": current,
            "completed_prefix_calls": prefixes_done,
            "completed_continuation_calls": continuations_done,
            "attempt_journal_entries": attempt_entries,
            "failed_call": None if not failed_rows else failed_rows[-1],
            "truth_values_read": False, "error": repr(exc),
            "traceback": traceback.format_exc(),
            "elapsed_campaign_seconds": time.perf_counter() - started})
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("manifest", "source", "baseline", "population-observed",
                 "historical-observed", "branch-qualification", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
