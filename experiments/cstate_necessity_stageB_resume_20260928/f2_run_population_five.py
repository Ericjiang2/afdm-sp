"""Five admitted F2 policies on the complete sealed 6.5-dB population.

The frozen seven-policy producer supplies only its paid-call and artifact
primitives. This entry point owns its registration, schedule and denominator.
No truth, generator, or offline analysis is imported.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

import numpy as np

import f2_run_population as base

SCHEMA = "f2-stage-b-five-policy/1"
POLICIES = ("F0", "B", "F0_LOCAL", "F2T", "F2E")
EXCLUDED = {"F2E_LOCAL": "not_admitted_frozen_interface",
            "F2E_CSTATE": "not_admitted_frozen_interface"}
PRODUCER_FILES = ("f2_estimator.py", "f2_receiver.py", "f2_run_population.py",
                  "f2_run_population_five.py")
RESULTS = base.PROJECT / "results/cstate_necessity_stageB_resume_20260928"


def preflight(args: argparse.Namespace) -> dict:
    if args.out.exists() or not args.out.resolve().is_relative_to(
            Path("/data/guoyikun").resolve()):
        raise ValueError("new output root must be below /data/guoyikun")
    if any(os.environ.get(key) != "1" for key in
           ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")):
        raise ValueError("one CPU thread environment required")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("CUDA must be hidden")
    if base.sha256(args.manifest) != args.manifest_sha256:
        raise ValueError("locked five-policy manifest SHA differs")
    manifest = json.loads(args.manifest.read_text())
    if (manifest.get("schema") != SCHEMA or manifest.get("status") != "locked"
            or manifest.get("frames") != 1024
            or manifest.get("policy_names") != list(POLICIES)
            or manifest.get("excluded_policies") != EXCLUDED
            or manifest.get("maximum_prefix_calls") != 2048
            or manifest.get("maximum_f0_continuations") != 120
            or manifest.get("maximum_f2e_continuations") != 0
            or manifest.get("maximum_total_calls") != 2168
            or manifest.get("truth_used") is not False
            or manifest.get("new_observations") != 0
            or manifest.get("output_relative_path") != str(
                args.out.resolve().relative_to(base.PROJECT.resolve()))
            or manifest.get("maximum_wall_seconds") != 259200
            or manifest.get("outer_hard_wall_seconds") != 259500):
        raise ValueError("five-policy allocation or existing 72-hour caps differ")
    caps = manifest.get("per_call_cap_seconds")
    if (caps != {"F0": 120, "F2E": 120, "B": 900,
                 "F0_LOCAL": 900, "F2T": 120}):
        raise ValueError("frozen per-call caps differ")
    hashes = manifest.get("producer_source_hashes")
    if (not isinstance(hashes, dict) or set(hashes) != set(PRODUCER_FILES)
            or any(hashes[name] != base.sha256(base.HERE / name)
                   for name in PRODUCER_FILES)
            or manifest.get("launcher_sha256") != base.sha256(
                base.HERE / "f2_launch_population_five_once.sh")):
        raise ValueError("five-policy producer/launcher source differs")
    protocol_files = {
        "method_sha256": RESULTS / "F2_METHOD_CONTRACT.md",
        "numerical_amendment_sha256": RESULTS / "F2_NUMERICAL_AMENDMENT.md",
        "population_protocol_sha256": RESULTS / "F2_FIVE_POLICY_PROTOCOL.md",
        "population_budget_sha256": RESULTS / "F2_FIVE_POLICY_BUDGET.md",
        "authorization_sha256": RESULTS / "F2_FIVE_POLICY_AUTHORIZATION.json",
        "small_reference_qualification_sha256": RESULTS / "F2_SMALL_REFERENCE_QUALIFICATION.md",
        "domain_recovery_proposal_sha256": RESULTS / "F2_DOMAIN_RECOVERY_PROPOSAL.md",
    }
    if any(manifest.get(key) != base.sha256(path)
           for key, path in protocol_files.items()):
        raise ValueError("frozen F2 or domain-recovery contract differs")
    dependencies = manifest.get("dependency_source_hashes")
    required = {"cstate_necessity_stageA_20260928/run_stage_a.py",
                "tf_cstate_validation_20260922/run_validation.py",
                "tf_cstate_validation_20260922/geometry_validation.py",
                "tf_cstate_validation_20260922/compact_state.py",
                "tf_geometry_reopen_20260922/geometry_reopen.py",
                "tf_production_gap_audit_20260922/audit_io.py"}
    if not isinstance(dependencies, dict) or not required.issubset(dependencies):
        raise ValueError("dependency source bindings missing")
    for relative, digest in dependencies.items():
        path = Path(relative)
        resolved = (base.EXPERIMENTS / path).resolve()
        if (path.is_absolute() or ".." in path.parts or not path.parts
                or not resolved.is_relative_to(base.EXPERIMENTS.resolve())
                or base.sha256(resolved) != digest):
            raise ValueError(f"dependency source differs: {relative}")
    qualification = args.branch_qualification
    branch_seal = base.verify_inventory(
        qualification, "observed_seal.json",
        allowed_status=("pass", "partial_qualified"))
    if (base.sha256(qualification / "observed_seal.json") !=
            manifest.get("branch_qualification_seal_sha256") or
            branch_seal.get("schema") != "f2-three-branch-qualification/1" or
            branch_seal.get("truth_values_read") is not False or
            branch_seal.get("run_manifest_sha256") !=
                manifest.get("branch_qualification_manifest_sha256") or
            not isinstance(branch_seal.get("qualified_arms"), list) or
            "f0044_F2T" not in branch_seal["qualified_arms"]):
        raise ValueError("saved F2T branch qualification differs")
    population_seal = base.verify_inventory(args.population_observed, "observed_seal.json")
    historical_seal = base.verify_inventory(args.historical_observed, "observed_seal.json")
    if (base.sha256(args.population_observed / "observed_seal.json") !=
            manifest.get("population_observed_seal_sha256") or
            base.sha256(args.historical_observed / "observed_seal.json") !=
            manifest.get("stage_a_observed_seal_sha256")):
        raise ValueError("sealed developmental input binding differs")
    rows = base.select_650_rows([json.loads(line) for line in
        (args.population_observed / "ledger.jsonl").read_text().splitlines()])
    if any(population_seal["files"].get(row["observation_path"]) !=
           row["observation_sha256"] for row in rows):
        raise ValueError("population row/file binding differs")
    old_rows = [json.loads(line) for line in
                (args.historical_observed / "ledger.jsonl").read_text().splitlines()]
    previous_f0 = {row["observation_id"]: row for row in old_rows
                   if row.get("arm") == "A"}
    if len(previous_f0) != 1024 or sum(
            row["baseline_syndrome_weight"] > 0 for row in previous_f0.values()) != 40:
        raise ValueError("old F0 1024/40 reference differs")
    for row in rows:
        previous = previous_f0[row["observation_id"]]
        if (historical_seal["files"].get(previous["raw_path"]) != previous["raw_sha256"]
                or previous["frame"] != row["frame"]
                or previous["input_sha256"] != row["observation_sha256"]
                or previous["observation_hash"] != row["observation_hash"]
                or previous["stream_ids"] != row["stream_ids"]):
            raise ValueError("old F0 and current input identities differ")
    evidence = base.attach(args.source, args.baseline)
    if (evidence.source_hashes(args.source) != manifest.get("native_source_hashes")
            or evidence.source_hashes(args.baseline) != manifest.get("baseline_source_hashes")):
        raise ValueError("frozen source hashes differ")
    cache = args.baseline / (
        "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
        "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    if base.sha256(cache) != manifest.get("ldpc_cache_sha256"):
        raise ValueError("frozen code cache differs")
    from receiver import context, extract_info  # noqa: PLC0415
    import native_twofft as native  # noqa: PLC0415
    import geometry_validation as kernel  # noqa: PLC0415
    from run_validation import _branch  # noqa: PLC0415
    from f2_receiver import receive_f2e, continue_f2t  # noqa: PLC0415
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


def continuation_plan(f0_syndrome: int, trigger_ordinal: int) -> tuple[str, ...]:
    if f0_syndrome < 0 or trigger_ordinal < 0:
        raise ValueError("invalid F0 trigger state")
    return base.rotate(("B", "F0_LOCAL", "F2T"), trigger_ordinal) if f0_syndrome else ()


def call_budget_seconds(started: float, campaign_cap: int, call_cap: int) -> float:
    """Bound the next paid call by both registered deadlines."""
    remaining = campaign_cap - (time.perf_counter() - started)
    if remaining <= 0:
        raise TimeoutError("locked campaign wall cap reached")
    return min(float(call_cap), remaining)


def run(args: argparse.Namespace) -> None:
    bound = preflight(args)
    out = args.out
    out.mkdir(parents=True)
    for folder in ("raw", "checkpoints", "decisions"):
        (out / folder).mkdir()
    base.write_json(out / "manifest.json", {
        "schema": SCHEMA, "status": "running", "run_manifest_sha256": args.manifest_sha256,
        "source_hashes": bound["manifest"]["producer_source_hashes"],
        "population_observed_seal_sha256": bound["manifest"]["population_observed_seal_sha256"],
        "stage_a_observed_seal_sha256": bound["manifest"]["stage_a_observed_seal_sha256"],
        "policy_names": list(POLICIES), "excluded_policies": EXCLUDED,
        "runtime_environment": bound["environment"],
        "schedule": "F0/F2E alternating; original F0 trigger rotates B/F0_LOCAL/F2T",
        "timing_boundary": "per-call origin before durable attempt journal; through durable raw and decision; analysis/parity overhead excluded",
        "cost_rule": "logical prefix plus own branch; other branches excluded",
        "memory_rule": "Linux RUSAGE_SELF cumulative whole-process peak after each paid call; campaign high-water at sealing; isolated policy peaks unavailable",
        "failure_rule": "any failure stops invalid_partial; no subset FER or retry",
        "created_epoch": time.time(), "pid": os.getpid(), "args": sys.argv[:]})
    for name in ("attempts.jsonl", "ledger.jsonl", "policy_ledger.jsonl",
                 "failed_calls.jsonl"):
        (out / name).touch(exist_ok=False)
    prefixes_done = continuations_done = f0_trigger_frames = 0
    current = None
    started = time.perf_counter()
    signal.signal(signal.SIGALRM, base._timeout)
    try:
        for frame, row in enumerate(bound["rows"]):
            current = row["observation_id"]
            if time.perf_counter() - started >= bound["manifest"]["maximum_wall_seconds"]:
                raise TimeoutError("locked campaign wall cap reached")
            prefixes = {}
            branches = {}
            for arm in base.schedule(frame):
                old_arrays = None
                if arm == "F0":
                    previous = bound["previous_f0"][current]
                    old, _ = bound["evidence"].load_artifact(
                        args.historical_observed / previous["raw_path"])
                    old_arrays = old["baseline_arrays"]
                limit = call_budget_seconds(started, bound["manifest"]["maximum_wall_seconds"],
                                            bound["manifest"]["per_call_cap_seconds"][arm])
                origin = time.perf_counter()
                attempt = prefixes_done + continuations_done + 1
                try:
                    signal.setitimer(signal.ITIMER_REAL, limit)
                    prefixes[arm] = base._prefix(out, args, bound, row, arm,
                                                 attempt, old_arrays)
                except BaseException as exc:
                    base.record_failed_call(out, attempt=attempt, kind="prefix", arm=arm,
                                            observation_id=current, origin=origin, error=exc)
                    raise
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                prefixes_done += 1
            f0_syndrome = prefixes["F0"]["record"]["final_syndrome_weight"]
            if f0_syndrome != bound["previous_f0"][current]["baseline_syndrome_weight"]:
                raise ValueError("F0 historical trigger parity differs")
            if f0_syndrome:
                f0_trigger_frames += 1
                if f0_trigger_frames > 40:
                    raise ValueError("more than historical 40 F0 trigger frames")
            for policy in continuation_plan(f0_syndrome, f0_trigger_frames):
                limit = call_budget_seconds(started, bound["manifest"]["maximum_wall_seconds"],
                                            bound["manifest"]["per_call_cap_seconds"][policy])
                origin = time.perf_counter()
                attempt = prefixes_done + continuations_done + 1
                try:
                    signal.setitimer(signal.ITIMER_REAL, limit)
                    branches[policy] = base._branch(out, bound, row, prefixes["F0"],
                                                    policy, attempt)
                except BaseException as exc:
                    base.record_failed_call(out, attempt=attempt, kind="continuation",
                                            arm=policy, observation_id=current,
                                            origin=origin, error=exc)
                    raise
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                continuations_done += 1
                if continuations_done > 120:
                    raise ValueError("F0 continuation allocation exceeded")
            for policy in POLICIES:
                parent = prefixes["F2E" if policy == "F2E" else "F0"]
                branch = branches.get(policy)
                if f0_syndrome and policy in ("B", "F0_LOCAL", "F2T") and branch is None:
                    raise ValueError("required F0 continuation missing")
                logical = base._policy_row(frame, row, policy, parent, branch)
                logical["schema"] = SCHEMA
                base.append_json(out / "policy_ledger.jsonl", logical)
        if prefixes_done != 2048 or continuations_done != 120 or f0_trigger_frames != 40:
            raise ValueError("complete 2168-call five-policy allocation differs")
        files = {str(path.relative_to(out)): base.sha256(path) for path in out.rglob("*")
                 if path.is_file() and path.name != "observed_seal.json"}
        base.write_json(out / "observed_seal.json", {
            "schema": SCHEMA, "status": "pass", "files": files,
            "run_manifest_sha256": args.manifest_sha256,
            "frames": 1024, "actual_prefix_calls": prefixes_done,
            "actual_continuation_calls": continuations_done,
            "actual_total_calls": prefixes_done + continuations_done,
            "f0_trigger_frames": f0_trigger_frames,
            "f2e_trigger_frames": None,
            "logical_policy_rows": 5120, "excluded_policies": EXCLUDED,
            "truth_values_read": False,
            "campaign_rss_peak_kib_cumulative": resource.getrusage(
                resource.RUSAGE_SELF).ru_maxrss,
            "elapsed_campaign_seconds": time.perf_counter() - started})
    except BaseException as exc:
        attempts = len((out / "attempts.jsonl").read_text().splitlines())
        failed = [json.loads(line) for line in
                  (out / "failed_calls.jsonl").read_text().splitlines()]
        base.write_json(out / "failure.json", {
            "schema": SCHEMA, "status": "invalid_partial",
            "current_observation_id": current,
            "completed_prefix_calls": prefixes_done,
            "completed_continuation_calls": continuations_done,
            "attempt_journal_entries": attempts,
            "failed_call": None if not failed else failed[-1],
            "truth_values_read": False, "error": repr(exc),
            "campaign_rss_peak_kib_cumulative": resource.getrusage(
                resource.RUSAGE_SELF).ru_maxrss,
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
