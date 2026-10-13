#!/usr/bin/env python3
"""Matched 64-frame F0/Cref/Ccompat timing after frozen 1024-frame F1 parity.

The three complete receiver calls per archived observation use one process and
six rotating arm orders. This script never loads truth or changes any receiver.
"""
from __future__ import annotations

import argparse
from itertools import permutations
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent.parent
STAGE_A = EXPERIMENTS / "cstate_necessity_stageA_20260928"
COMPAT = EXPERIMENTS / "cstate_necessity_stageB_resume_20260928"
sys.path[:0] = [str(EXPERIMENTS / "tf_cstate_prospective_20260923"),
                str(EXPERIMENTS / "tf_cstate_validation_20260922"),
                str(EXPERIMENTS / "tf_production_gap_audit_20260922"),
                str(STAGE_A), str(COMPAT)]
from audit_io import load_bound, sha256  # noqa: E402
from run_stage_a import _compare_saved, _syndrome, append_json, write_json_exclusive  # noqa: E402
import f1_run_compat as legacy  # noqa: E402


SCHEMA = "f1-final-matched64-timing/1"
ARMS = ("F0", "Cref", "Ccompat")
SOURCE_NAMES = ("f1_matched_timing.py", "f1_matched_timing_launch.sh")
SUBSET = "frame_index%16==0"
EXPECTED_COMPAT_CALLS = 2112
EXPECTED_FAST_CALLS = 1024
EXPECTED_MATCHED_CALLS = 192
SECONDS_LIMIT = 900.0
CALL_LIMIT = 30.0


def schedule(ordinal: int) -> tuple[str, str, str]:
    if not 0 <= ordinal < 64:
        raise ValueError("matched frame ordinal outside 0..63")
    return tuple(permutations(ARMS))[ordinal % 6]


def _require_hash(path: Path, expected: str, label: str) -> None:
    if sha256(path) != expected:
        raise ValueError(f"{label} SHA differs")


def verify_full_equivalence(args, registration: dict) -> dict:
    """Admit timing only after the previously completed full F1 gate is bound."""
    for key, path in (("compat_registration_sha256", args.compat_registration),
                      ("compat_observed_seal_sha256", args.compat_observed / "observed_seal.json"),
                      ("compat_equivalence_receipt_sha256", args.compat_equivalence_receipt),
                      ("independent_rehash_receipt_sha256", args.independent_rehash_receipt)):
        _require_hash(path, registration[key], key)
    old_registration = json.loads(args.compat_registration.read_text())
    old_receipt = json.loads(args.compat_equivalence_receipt.read_text())
    seal = json.loads((args.compat_observed / "observed_seal.json").read_text())
    if (old_registration.get("status") != "locked"
            or old_registration.get("source_hashes") != {
                name: sha256(COMPAT / name) for name in legacy.SOURCE_NAMES}
            or old_receipt.get("status") != "producer_gates_pass_observed_git_sealed"
            or old_receipt.get("counts", {}).get("arms") != {
                "B": 1024, "Ccompat": 1024, "Cref": 64}
            or old_receipt.get("counts", {}).get("complete_ok") != EXPECTED_COMPAT_CALLS
            or old_receipt.get("counts", {}).get("failed") != 0
            or not old_receipt.get("checks")
            or not all(old_receipt["checks"].values())
            or old_receipt.get("checks", {}).get("producer_reference_max_difference_zero_2112") is not True
            or old_receipt.get("checks", {}).get("schedule_exact") is not True
            or old_receipt.get("observed_seal_git_blob_verified") is not True
            or seal.get("status") != "pass" or seal.get("calls") != EXPECTED_COMPAT_CALLS
            or seal.get("files", {}).get("manifest.json") != sha256(
                args.compat_observed / "manifest.json")
            or seal.get("files", {}).get("ledger.jsonl") != sha256(args.compat_observed / "ledger.jsonl")
            or old_receipt.get("input_sha256", {}).get(
                "observed_f1_compat_v1/observed_seal.json") != sha256(
                args.compat_observed / "observed_seal.json")):
        raise ValueError("frozen full F1 equivalence proof differs")
    rows = [json.loads(line) for line in (args.compat_observed / "ledger.jsonl").read_text().splitlines()]
    fast = [row for row in rows if row.get("arm") == "Ccompat"]
    if (len(rows) != EXPECTED_COMPAT_CALLS or len(fast) != EXPECTED_FAST_CALLS
            or any(row.get("status") != "ok" for row in rows)
            or any(row.get("reference_max_difference") != 0 for row in fast)
            or [row.get("observation_id") for row in fast] != [
                f"s650_f{i:04d}" for i in range(1024)]):
        raise ValueError("frozen full F1 ledger gate differs")
    independent = json.loads(args.independent_rehash_receipt.read_text())
    counts = independent.get("counts", {})
    if (independent.get("schema") != "f1-ccompat-stagea-raw-equivalence-recount/1"
            or independent.get("status") != "pass"
            or independent.get("n") != EXPECTED_FAST_CALLS
            or any(counts.get(key) != EXPECTED_FAST_CALLS for key in (
                "frames_compared", "frames_exact_discrete_pass",
                "frames_continuous_tolerance_pass", "frames_final_decoded_exact_pass"))
            or counts.get("raw_files_rehashed_per_side") != EXPECTED_FAST_CALLS
            or independent.get("all_exact_discrete_pass") is not True
            or independent.get("all_within_tolerance_pass") is not True
            or independent.get("all_final_decoded_exact_pass") is not True
            or independent.get("first_mismatch_observation_ids") != []
            or independent.get("mismatch_observation_ids") != []
            or independent.get("mismatch_count") != 0
            or any(independent.get(key) != 0 for key in (
                "receiver_calls", "decoder_calls", "truth_reads"))
            or independent.get("stage_a_observed_seal_sha256") != sha256(
                args.stage_a_observed / "observed_seal.json")
            or independent.get("stage_a_registration_sha256") != sha256(
                args.stage_a_registration)
            or independent.get("ccompat_registration_sha256") != sha256(
                args.compat_registration)
            or independent.get("ccompat_observed_seal_sha256") != sha256(
                args.compat_observed / "observed_seal.json")):
        raise ValueError("independent full F1 rehash receipt differs")
    contract = independent.get("contract", {})
    if (contract.get("continuous_atol") != 2e-10
            or contract.get("continuous_rtol") != 0
            or contract.get("final_bits") != "exact numpy.array_equal"
            or contract.get("reference_fields") != list(legacy.REFERENCE_FIELDS)):
        raise ValueError("independent full F1 comparison contract differs")
    return dict(producer_checked_fast_calls=len(fast),
                independent_checked_fast_calls=counts["frames_compared"],
                compat_observed_seal_sha256=sha256(args.compat_observed / "observed_seal.json"))


def preflight(args) -> dict:
    if args.out.exists():
        raise FileExistsError("matched timing output exists; no overwrite or resume")
    if not re.fullmatch(r"[0-9a-f]{40}", args.registration_commit):
        raise ValueError("full registration commit required")
    _require_hash(args.registration, args.registration_sha256, "matched timing registration")
    registration = json.loads(args.registration.read_text())
    if (registration.get("schema") != SCHEMA or registration.get("status") != "locked"
            or registration.get("expected_calls") != EXPECTED_MATCHED_CALLS
            or registration.get("subset") != SUBSET
            or registration.get("seconds_limit") != SECONDS_LIMIT
            or registration.get("per_call_cap_seconds") != CALL_LIMIT
            or registration.get("cpu_id") != 64
            or os.sched_getaffinity(0) != {64}
            or registration.get("source_hashes") != {
                name: sha256(HERE / name) for name in SOURCE_NAMES}
            or registration.get("protocol_sha256") != sha256(args.protocol)
            or registration.get("stage_a_registration_sha256") != sha256(args.stage_a_registration)
            or registration.get("stage_a_observed_seal_sha256") != sha256(
                args.stage_a_observed / "observed_seal.json")
            or registration.get("population_observed_seal_sha256") != sha256(
                args.population_observed / "observed_seal.json")):
        raise ValueError("matched timing registration or source binding differs")
    gate = verify_full_equivalence(args, registration)
    old_manifest = json.loads((args.compat_observed / "manifest.json").read_text())
    old_args = argparse.Namespace(
        out=args.out, registration=args.compat_registration,
        registration_commit=old_manifest["registration_commit"],
        protocol=args.compat_protocol, stage_a_registration=args.stage_a_registration,
        stage_a_observed=args.stage_a_observed, population_observed=args.population_observed,
        source=args.source, baseline=args.baseline, seconds_limit=2400.0)
    bound = legacy.preflight(old_args)
    environment_keys = (
        "python", "numpy", "scipy", "torch", "matplotlib",
        "cuda_visible_devices", "torch_cuda_available", "thread_environment",
        "torch_num_threads", "torch_num_interop_threads",
        "torch_pre_context_num_threads", "torch_pre_context_num_interop_threads",
        "machine", "platform", "hostname")
    previous_environment = old_manifest["runtime_environment"]
    if any(bound["environment"].get(key) != previous_environment.get(key)
           for key in environment_keys):
        raise ValueError("matched timing runtime environment differs from frozen F1 campaign")
    selected = bound["selected"][::16]
    if (len(selected) != 64 or [row["observation_id"] for row in selected] != [
            f"s650_f{i:04d}" for i in range(0, 1024, 16)]):
        raise ValueError("matched 64 observation identities differ")
    bound.update(registration=registration, selected=selected, full_gate=gate)
    return bound


def _alarm(_signum, _frame):
    raise TimeoutError("matched timing call/remaining campaign cap reached")


def call_allowance(origin: float, began: float, now: float) -> float:
    campaign_remaining = SECONDS_LIMIT - (now - began)
    measured_remaining = CALL_LIMIT - (now - origin)
    if campaign_remaining <= 0 or measured_remaining <= 0:
        raise TimeoutError("matched timing cap reached after attempt reservation")
    return min(campaign_remaining, measured_remaining)


def run(args) -> None:
    began = time.perf_counter()
    bound = preflight(args)
    if time.perf_counter() - began >= SECONDS_LIMIT:
        raise TimeoutError("matched timing cap reached in preflight")
    out = args.out
    out.mkdir(parents=True)
    for folder in ("checkpoints", "raw", "decisions"):
        (out / folder).mkdir()
    write_json_exclusive(out / "manifest.json", dict(
        schema=SCHEMA, status="running", registration_sha256=sha256(args.registration),
        registration_commit=args.registration_commit, source_hashes=bound["registration"]["source_hashes"],
        compatibility_source_hashes=json.loads(args.compat_registration.read_text())["source_hashes"],
        full_equivalence_gate=bound["full_gate"], runtime_environment=bound["environment"],
        subset=SUBSET, observation_ids=[r["observation_id"] for r in bound["selected"]],
        expected_calls=EXPECTED_MATCHED_CALLS,
        timing_boundary="before durable attempt journal and observed input load through durable decision write; ledger append and reference comparison excluded",
        branch_policy="F0 only, no CSTATE; F1 arms have no branch",
        setup_seconds=bound["setup_seconds"], args=sys.argv[:], pid=os.getpid()))
    ledger, attempts = out / "ledger.jsonl", out / "attempts.jsonl"
    ledger.touch(exist_ok=False)
    attempts.touch(exist_ok=False)
    calls = 0
    prior_alarm = signal.signal(signal.SIGALRM, _alarm)
    try:
        for ordinal, input_row in enumerate(bound["selected"]):
            for arm in schedule(ordinal):
                remaining = SECONDS_LIMIT - (time.perf_counter() - began)
                if remaining <= 0 or calls >= EXPECTED_MATCHED_CALLS:
                    raise TimeoutError("matched timing registered allocation/cap exhausted")
                calls += 1
                stem = input_row["observation_id"]
                origin = time.perf_counter()
                identity = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                                input_sha256=input_row["observation_sha256"])
                row = dict(status="inflight", attempt_index=calls, observation_id=stem,
                           frame=input_row["frame"], arm=arm,
                           input_sha256=input_row["observation_sha256"],
                           observation_hash=input_row["observation_hash"],
                           stream_ids=input_row["stream_ids"], receiver_started=False,
                           checkpoints=[])
                append_json(attempts, dict(attempt_index=calls, observation_id=stem,
                                           arm=arm, started_epoch=time.time()))
                rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                def sink(event, decoded, *, row=row, origin=origin, stem=stem,
                         arm=arm, identity=identity):
                    round_index = int(event["round"])
                    if round_index != len(row["checkpoints"]):
                        raise ValueError("checkpoint order differs")
                    ready = time.perf_counter() - origin
                    path = out / "checkpoints" / f"{stem}_{arm}_r{round_index}.npz"
                    digest = bound["evidence"].save_artifact(
                        path, dict(event=event, decoded=np.asarray(decoded).copy()),
                        dict(identity, round=round_index))
                    row["checkpoints"].append(dict(round=round_index,
                        path=str(path.relative_to(out)), artifact_sha256=digest,
                        decision_ready_seconds=ready,
                        ready_seconds=time.perf_counter() - origin,
                        syndrome_weight=_syndrome(bound["H"], decoded)))

                try:
                    signal.setitimer(signal.ITIMER_REAL,
                                     call_allowance(origin, began, time.perf_counter()))
                    payload = load_bound(bound["evidence"],
                        args.population_observed / input_row["observation_path"],
                        input_row["observation_sha256"])
                    if (payload["observation_id"] != stem
                            or payload["observation_hash"] != input_row["observation_hash"]
                            or payload["stream_ids"] != input_row["stream_ids"]):
                        raise ValueError("matched observed input identity differs")
                    observation = payload["observation"]
                    if set(observation) != {"y", "pilot", "sigma2"}:
                        raise ValueError("matched observed input inventory differs")
                    row["receiver_started"] = True
                    receiver_start = time.perf_counter()
                    if arm == "F0":
                        decoder, arrays, timing = bound["native"].receive(
                            observation, bound["system"], bound["code"], rounds=2,
                            iterations=20, ce_mode="soft", gain_mode="joint",
                            checkpoint_sink=sink)
                    elif arm == "Cref":
                        decoder, arrays, timing = bound["receive_f1"](
                            observation, bound["system"], bound["code"], checkpoint_sink=sink)
                    else:
                        decoder, arrays, timing = bound["receive_f1_fast"](
                            observation, bound["system"], bound["code"], checkpoint_sink=sink)
                    native_end = time.perf_counter()
                    if (len(row["checkpoints"]) != 2
                            or not np.array_equal(decoder["decoded"], arrays["r1_decoded"])):
                        raise ValueError("two-round native output incomplete")
                    from receiver import extract_info  # noqa: PLC0415
                    final_decoded = np.asarray(decoder["decoded"], np.uint8).copy()
                    final_info = np.asarray(extract_info(bound["code"], final_decoded), np.uint8)
                    if final_info.shape != (1024,):
                        raise ValueError("information output shape differs")
                    syndrome = _syndrome(bound["H"], final_decoded)
                    raw_start = time.perf_counter()
                    raw_path = out / "raw" / f"{stem}_{arm}.npz"
                    raw = dict(observation_id=stem, arm=arm,
                               input_sha256=input_row["observation_sha256"],
                               stream_ids=input_row["stream_ids"], baseline_arrays=arrays,
                               native_events=timing["events"],
                               native_timing={k: v for k, v in timing.items() if k != "acquisition"},
                               acquisition=None if "acquisition" not in timing else {
                                   k: v for k, v in timing["acquisition"].items() if k != "channel"},
                               native_decoder=decoder, triggered=False,
                               baseline_syndrome_weight=syndrome,
                               initial_geometry=timing.get("initial_geometry"),
                               entering_geometry=timing.get("entering_geometry"),
                               final_decoded=final_decoded, final_info=final_info)
                    raw_hash = bound["evidence"].save_artifact(raw_path, raw, identity)
                    raw_ready = time.perf_counter() - origin
                    decision_path = out / "decisions" / f"{stem}_{arm}.json"
                    decision = dict(schema=SCHEMA, observation_id=stem, arm=arm,
                                    input_sha256=input_row["observation_sha256"],
                                    triggered=False, final_syndrome_weight=syndrome,
                                    final_decoded_sha256=hashlib.sha256(final_decoded.tobytes()).hexdigest(),
                                    final_decoded=final_decoded.astype(int).tolist(),
                                    final_info=final_info.astype(int).tolist(),
                                    checkpoints=row["checkpoints"],
                                    raw_path=str(raw_path.relative_to(out)), raw_sha256=raw_hash,
                                    source_hashes=bound["registration"]["source_hashes"])
                    decision_start = time.perf_counter()
                    decision_hash = write_json_exclusive(decision_path, decision)
                    complete = time.perf_counter() - origin
                    if complete > CALL_LIMIT:
                        raise TimeoutError("matched timing complete latency exceeds per-call cap")
                    # Reference checks are outside complete latency and its per-call cap.
                    campaign_remaining = SECONDS_LIMIT - (time.perf_counter() - began)
                    if campaign_remaining <= 0:
                        raise TimeoutError("matched timing campaign cap reached before reference check")
                    signal.setitimer(signal.ITIMER_REAL, campaign_remaining)
                    old = bound["reference"][stem, "B" if arm == "F0" else "C"]
                    if arm == "F0":
                        old_raw = load_bound(bound["evidence"],
                                             args.stage_a_observed / old["raw_path"], old["raw_sha256"])
                        largest = _compare_saved(old_raw["baseline_arrays"], arrays)
                        if not np.array_equal(old_raw["native_decoder"]["decoded"], final_decoded):
                            raise ValueError("F0 native decoded bits differ from Stage-A B prefix")
                    else:
                        largest = legacy._compare_reference(
                            bound["evidence"], args.stage_a_observed, old, raw, arm)
                    row.update(status="ok", triggered=False,
                               baseline_syndrome_weight=syndrome,
                               final_syndrome_weight=syndrome,
                               final_decoded_sha256=decision["final_decoded_sha256"],
                               complete_latency_seconds=complete,
                               acquisition_seconds=timing["pilot_seconds"],
                               native_seconds=native_end-receiver_start,
                               refit_seconds=sum(event["ce"] for event in timing["events"]),
                               tf_seconds=sum(event["inference"] for event in timing["events"]),
                               decoder_seconds=sum(event["decoder"] for event in timing["events"]),
                               raw_serialization_seconds=raw_ready-(raw_start-origin),
                               decision_record_seconds=complete-(decision_start-origin),
                               raw_artifact_ready_seconds=raw_ready,
                               reference_max_difference=largest,
                               reference_raw_sha256=old["raw_sha256"],
                               raw_path=str(raw_path.relative_to(out)), raw_sha256=raw_hash,
                               decision_path=str(decision_path.relative_to(out)),
                               decision_sha256=decision_hash,
                               rss_peak_kib_before=rss_before,
                               rss_peak_kib_after=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                    append_json(ledger, row)
                except BaseException as error:
                    row.update(status="failed", error=repr(error),
                               traceback=traceback.format_exc(),
                               charged_seconds=time.perf_counter()-origin)
                    append_json(ledger, row)
                    raise
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
        if calls != EXPECTED_MATCHED_CALLS:
            raise ValueError("matched timing complete-call allocation differs")
        if time.perf_counter() - began >= SECONDS_LIMIT:
            raise TimeoutError("matched timing campaign cap reached before sealing")
        files = {str(path.relative_to(out)): sha256(path) for path in out.rglob("*")
                 if path.is_file() and path.name != "observed_seal.json"}
        write_json_exclusive(out / "observed_seal.json", dict(
            schema=SCHEMA, status="pass", files=files, observations=64,
            calls=calls, attempts=calls, subset=SUBSET,
            registration_sha256=sha256(args.registration),
            full_equivalence_gate=bound["full_gate"]))
    except BaseException as error:
        write_json_exclusive(out / "invalid_partial.json", dict(
            status="invalid_partial", error=repr(error),
            traceback=traceback.format_exc(), attempts=calls,
            elapsed_seconds=time.perf_counter()-began))
        raise
    finally:
        signal.signal(signal.SIGALRM, prior_alarm)


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("registration", "protocol", "compat-registration", "compat-protocol",
                 "compat-observed", "compat-equivalence-receipt", "independent-rehash-receipt",
                 "stage-a-registration", "stage-a-observed", "population-observed",
                 "source", "baseline", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--registration-commit", required=True)
    parser.add_argument("--registration-sha256", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
