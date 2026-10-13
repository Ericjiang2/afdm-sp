"""At most three saved-state, observed-only F2 continuation qualifications.

No prefix, observation generation, truth or population policy result is run.
Requires a separately Git-frozen manifest and new remote output directory.
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
sys.path[:0] = [str(EXPERIMENTS / "tf_production_gap_audit_20260922"),
                str(EXPERIMENTS / "tf_cstate_validation_20260922")]
from audit_io import attach  # noqa: E402


ARMS = ("f0044_F2T", "f0000_F2E_LOCAL", "f0000_F2E_CSTATE")
CAPS = (120, 900, 900)


def select_650_rows(rows: list[dict]) -> list[dict]:
    selected = [row for row in rows if row["snr_centi_db"] == 650]
    if (len(rows) != 3072 or len(selected) != 1024 or
            [row["frame"] for row in selected] != list(range(1024)) or
            [row["observation_id"] for row in selected] !=
                [f"s650_f{i:04d}" for i in range(1024)]):
        raise ValueError("fixed 6.5-dB 1024-frame cohort differs")
    return selected


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict) -> str:
    with path.open("x") as stream:
        json.dump(payload, stream, allow_nan=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return sha256(path)


def append_json(path: Path, payload: dict) -> None:
    with path.open("a") as stream:
        json.dump(payload, stream, allow_nan=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _timeout(_signum, _frame):
    raise TimeoutError("frozen F2 continuation cap reached")


def _front_summary(front: dict) -> dict:
    channel = front["channel"]
    return {**{key: value for key, value in front.items() if key != "channel"},
            "channel": {"delays": channel.delays, "dopplers": channel.dopplers,
                        "gains": channel.gains}}


def preflight(args):
    if args.out.exists() or not args.out.resolve().is_relative_to(
            Path("/data/guoyikun").resolve()):
        raise ValueError("qualification output must be new under /data/guoyikun")
    if any(os.environ.get(key) != "1" for key in
           ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")):
        raise ValueError("single-thread CPU required")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("CUDA must be hidden")
    if sha256(args.manifest) != args.manifest_sha256:
        raise ValueError("Git-frozen branch manifest SHA differs")
    manifest = json.loads(args.manifest.read_text())
    if (manifest.get("schema") != "f2-three-branch-qualification/1"
            or manifest.get("status") != "locked"
            or manifest.get("arms") != list(ARMS)
            or manifest.get("caps_seconds") != list(CAPS)
            or manifest.get("maximum_continuation_calls") != 3
            or manifest.get("input_selection") !=
                "sealed 3072-row ledger; snr_centi_db=650; canonical 1024 frames"
            or manifest.get("output_relative_path") != str(
                args.out.resolve().relative_to(EXPERIMENTS.parent.resolve()))
            or manifest.get("truth_used") is not False):
        raise ValueError("three-call scope differs")
    report_root = EXPERIMENTS.parent / (
        "results/cstate_necessity_stageB_resume_20260928")
    if (sha256(report_root / "F2_BRANCH_QUALIFICATION_PLAN_v2.md") !=
            manifest.get("plan_sha256") or
            sha256(report_root / "F2_METHOD_CONTRACT.md") !=
            manifest.get("method_sha256") or
            sha256(report_root / "F2_NUMERICAL_AMENDMENT.md") !=
            manifest.get("numerical_amendment_sha256")):
        raise ValueError("frozen branch plan or F2 method differs")
    names = ("f2_estimator.py", "f2_receiver.py", "f2_qualify_branches_v2.py")
    if set(manifest.get("source_hashes", {})) != set(names) or any(
            manifest["source_hashes"][name] != sha256(HERE / name) for name in names):
        raise ValueError("qualification source bytes differ")
    dependencies = manifest.get("dependency_source_hashes")
    required_dependencies = {
        "tf_cstate_validation_20260922/run_validation.py",
        "tf_cstate_validation_20260922/geometry_validation.py",
        "tf_cstate_validation_20260922/compact_state.py",
        "tf_geometry_reopen_20260922/geometry_reopen.py",
        "tf_production_gap_audit_20260922/audit_io.py",
    }
    if (not isinstance(dependencies, dict) or
            not required_dependencies.issubset(dependencies)):
        raise ValueError("dependency inventory missing")
    for relative, digest in dependencies.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("dependency path escapes experiments")
        resolved = (EXPERIMENTS / path).resolve()
        if not resolved.is_relative_to(EXPERIMENTS.resolve()) or sha256(resolved) != digest:
            raise ValueError(f"dependency source differs: {relative}")
    if (sha256(args.population_observed / "observed_seal.json") !=
            manifest.get("population_observed_seal_sha256") or
            sha256(args.f2e_prefix / "raw.npz") != manifest.get("f2e_prefix_raw_sha256") or
            sha256(args.f0_prefix) != manifest.get("f0_prefix_raw_sha256")):
        raise ValueError("saved population or prefix SHA differs")
    if (sha256(args.f2e_prefix / "receipt.json") !=
            manifest.get("f2e_prefix_receipt_sha256") or
            sha256(args.f0_prefix.parents[1] / "observed_seal.json") !=
            manifest.get("stage_a_observed_seal_sha256")):
        raise ValueError("saved prefix parent receipt/seal differs")
    f2_receipt = json.loads((args.f2e_prefix / "receipt.json").read_text())
    stage_a_seal = json.loads((args.f0_prefix.parents[1] / "observed_seal.json").read_text())
    if (f2_receipt.get("status") != "ok" or f2_receipt.get("complete_calls") != 1
            or f2_receipt.get("raw_sha256") != manifest["f2e_prefix_raw_sha256"]
            or len(f2_receipt.get("checkpoints", [])) != 2
            or stage_a_seal.get("files", {}).get(
                str(args.f0_prefix.relative_to(args.f0_prefix.parents[1]))) !=
                manifest["f0_prefix_raw_sha256"]):
        raise ValueError("saved prefix completion/inventory differs")
    stage_a_ledger = args.f0_prefix.parents[1] / "ledger.jsonl"
    if (sha256(stage_a_ledger) != manifest.get("stage_a_ledger_sha256") or
            stage_a_seal["files"].get("ledger.jsonl") !=
                manifest["stage_a_ledger_sha256"]):
        raise ValueError("Stage-A observed ledger differs")
    first_failed_f0 = next((row for line in stage_a_ledger.read_text().splitlines()
                            if (row := json.loads(line)).get("arm") == "A"
                            and row.get("status") == "ok"
                            and row.get("baseline_syndrome_weight", 0) > 0), None)
    if (manifest.get("f0_selection_rule") !=
            "first Stage-A A/status-ok/nonzero-syndrome by ledger order" or
            first_failed_f0 is None or
            first_failed_f0["observation_id"] != "s650_f0044" or
            first_failed_f0["raw_sha256"] != manifest["f0_prefix_raw_sha256"] or
            first_failed_f0["input_sha256"] != manifest["f0044_input_sha256"]):
        raise ValueError("f0044 pilot/trigger choice was not observed-only")
    seal = json.loads((args.population_observed / "observed_seal.json").read_text())
    if any(seal.get("files", {}).get(name) != sha256(args.population_observed / name)
           for name in ("manifest.json", "ledger.jsonl")):
        raise ValueError("population manifest/ledger changed below seal")
    rows = select_650_rows([json.loads(line) for line in
            (args.population_observed / "ledger.jsonl").read_text().splitlines()])
    index = {row["observation_id"]: row for row in rows}
    for stem, expected in (("s650_f0000", manifest.get("f0000_input_sha256")),
                           ("s650_f0044", manifest.get("f0044_input_sha256"))):
        row = index[stem]
        if row["observation_sha256"] != expected:
            raise ValueError("qualification observation ID/SHA differs")
        path = args.population_observed / row["observation_path"]
        if seal["files"].get(row["observation_path"]) != sha256(path):
            raise ValueError("qualification observation artifact differs")
    evidence = attach(args.source, args.baseline)
    if (evidence.source_hashes(args.source) != manifest.get("native_source_hashes")
            or evidence.source_hashes(args.baseline) !=
                manifest.get("baseline_source_hashes")):
        raise ValueError("native/baseline source bytes differ")
    from receiver import context, extract_info  # noqa: PLC0415 - bound source first
    import native_twofft as native  # noqa: PLC0415
    import geometry_validation as kernel  # noqa: PLC0415
    from run_validation import _branch  # noqa: PLC0415
    from f2_receiver import continue_f2t  # noqa: PLC0415
    environment = evidence.bind_runtime_environment()
    system, _, code, header = context()
    evidence.verify_runtime_binding()
    if (system.N_total != 1024 or system.rho != .5 or system.l_max_cap != 102
            or header["code_g_sha256"] != manifest.get("code_g_sha256")):
        raise ValueError("qualification code/system context differs")
    cache = args.baseline / (
        "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
        "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    if sha256(cache) != manifest.get("ldpc_cache_sha256"):
        raise ValueError("qualification LDPC cache differs")
    with np.load(cache, allow_pickle=False) as saved:
        H = np.asarray(saved["H"])

    def load_observation(stem):
        row = index[stem]
        payload, _ = evidence.load_artifact(
            args.population_observed / row["observation_path"])
        if (payload["observation_id"] != stem or
                payload["observation_hash"] != row["observation_hash"] or
                payload["stream_ids"] != row["stream_ids"] or
                set(payload["observation"]) != {"y", "pilot", "sigma2"}):
            raise ValueError("saved observation identity differs")
        return payload["observation"]

    f2_raw, _ = evidence.load_artifact(args.f2e_prefix / "raw.npz")
    f0_raw, _ = evidence.load_artifact(args.f0_prefix)
    if (f2_raw["observation_id"] != "s650_f0000" or
            f2_raw["input_sha256"] != manifest["f0000_input_sha256"] or
            f0_raw["observation_id"] != "s650_f0044" or
            f0_raw["input_sha256"] != manifest["f0044_input_sha256"]):
        raise ValueError("saved prefix semantic identity differs")
    f2_arrays = f2_raw["coded_arrays"]
    f0_arrays = f0_raw["baseline_arrays"]
    if (len(f2_arrays["r1_delays"]) != 155 or
            not np.array_equal(f2_arrays["r1_decoded"], f2_raw["final_decoded"])):
        raise ValueError("saved F2E P155 prefix incomplete")
    f2_syndrome = int(np.count_nonzero((H @ np.asarray(f2_raw["final_decoded"], np.uint8)) % 2))
    f0_syndrome = int(np.count_nonzero((H @ np.asarray(f0_raw["final_decoded"], np.uint8)) % 2))
    if f2_syndrome <= 0 or f0_syndrome != 68:
        raise ValueError("saved legal branch trigger differs")
    return dict(manifest=manifest, evidence=evidence, native=native, kernel=kernel,
                branch=_branch, continue_f2t=continue_f2t,
                extract_info=extract_info, system=system, code=code, H=H,
                environment=environment,
                observations={"s650_f0000": load_observation("s650_f0000"),
                              "s650_f0044": load_observation("s650_f0044")},
                arrays={"s650_f0000": f2_arrays, "s650_f0044": f0_arrays},
                syndromes={"s650_f0000": f2_syndrome,
                           "s650_f0044": f0_syndrome})


def run(args) -> None:
    import copy  # noqa: PLC0415 - deep-copy immutable saved prefixes per branch
    bound = preflight(args)
    out = args.out
    out.mkdir(parents=True)
    for folder in ("raw", "checkpoints"):
        (out / folder).mkdir()
    write_json(out / "manifest.json", {
        "schema": "f2-three-branch-qualification/1", "status": "running",
        "run_manifest_sha256": args.manifest_sha256,
        "source_hashes": bound["manifest"]["source_hashes"],
        "runtime_environment": bound["environment"],
        "arms": list(ARMS), "caps_seconds": list(CAPS),
        "truth_values_read": False, "created_epoch": time.time()})
    (out / "attempts.jsonl").touch(exist_ok=False)
    (out / "ledger.jsonl").touch(exist_ok=False)
    current = None
    completed = 0
    run_start = time.perf_counter()
    current_start = None
    current_checkpoints: list[dict] = []
    try:
        for current, cap in zip(ARMS, CAPS, strict=True):
            stem = "s650_f0044" if current == "f0044_F2T" else "s650_f0000"
            observation = bound["observations"][stem]
            start = time.perf_counter()
            current_start = start
            current_checkpoints = []
            arrays = copy.deepcopy(bound["arrays"][stem])
            append_json(out / "attempts.jsonl", {
                "attempt": completed + 1, "arm": current, "observation_id": stem,
                "input_sha256": bound["manifest"]["f0044_input_sha256"] if stem.endswith(
                    "0044") else bound["manifest"]["f0000_input_sha256"],
                "started_epoch": time.time()})
            checkpoints = current_checkpoints

            def sink(event, decoded, *, checkpoints=checkpoints, start=start,
                     current=current, stem=stem):
                if checkpoints:
                    raise ValueError("more than one qualification continuation checkpoint")
                decision_ready = time.perf_counter() - start
                path = out / "checkpoints" / f"{current}_r2.npz"
                digest = bound["evidence"].save_artifact(path,
                    {"event": event, "decoded": np.asarray(decoded, np.uint8)},
                    {"arm": current, "observation_id": stem, "round": 2})
                checkpoints.append({"path": str(path.relative_to(out)),
                                    "sha256": digest,
                                    "decision_ready_seconds": decision_ready,
                                    "durable_seconds": time.perf_counter() - start})

            signal.signal(signal.SIGALRM, _timeout)
            signal.alarm(cap)
            try:
                if current == "f0044_F2T":
                    decoder, coded_arrays, detail = bound["continue_f2t"](
                        observation, bound["system"], bound["code"],
                        native_app=arrays["r1_app"], native_check=arrays["r1_check"],
                        native_syndrome_weight=bound["syndromes"][stem],
                        checkpoint_sink=sink)
                    front = detail["estimator"]
                    if front["channel"].p != 155:
                        raise ValueError("F2T silently changed top155 communications paths")
                    raw_payload = {"coded_arrays": coded_arrays,
                                   "front": _front_summary(front),
                                   "timing": detail["timing"],
                                   "initial_data": detail["initial_data"]}
                else:
                    mode = "LOCAL20" if current.endswith("LOCAL") else "CSTATE20"
                    branch = bound["branch"](
                        observation, bound["system"], bound["code"],
                        bound["native"], bound["kernel"], arrays, mode)
                    decoder = branch["decoder"]
                    if len(branch["result"].paths) != 155:
                        raise ValueError("frozen geometry branch truncated F2 paths")
                    sink({"round": 2,
                          "exclusive_stages": branch["exclusive_stages"],
                          "geometry_evaluations": branch["result"].evaluations},
                         decoder["decoded"])
                    raw_payload = {"geometry_result": asdict(branch["result"]),
                                   "detector": branch["detector"],
                                   "decoder": decoder,
                                   "exclusive_stages": branch["exclusive_stages"]}
                if len(checkpoints) != 1:
                    raise ValueError("qualification continuation checkpoint missing")
                bits = np.asarray(decoder["decoded"], np.uint8)
                info = np.asarray(bound["extract_info"](bound["code"], bits), np.uint8)
                if bits.shape != (2048,) or info.shape != (1024,):
                    raise ValueError("qualification decoded shape differs")
                syndrome = int(np.count_nonzero((bound["H"] @ bits) % 2))
                raw_payload.update(observation_id=stem, arm=current,
                                   final_decoded=bits, final_info=info,
                                   final_syndrome_weight=syndrome)
                path = out / "raw" / f"{current}.npz"
                digest = bound["evidence"].save_artifact(path, raw_payload,
                    {"arm": current, "observation_id": stem})
                complete = time.perf_counter() - start
                append_json(out / "ledger.jsonl", {
                    "status": "ok", "attempt": completed + 1,
                    "arm": current, "observation_id": stem,
                    "raw_path": str(path.relative_to(out)), "raw_sha256": digest,
                    "checkpoints": checkpoints,
                    "complete_latency_seconds": complete,
                    "final_syndrome_weight": syndrome,
                    "rss_peak_kib_cumulative": resource.getrusage(
                        resource.RUSAGE_SELF).ru_maxrss})
                completed += 1
            finally:
                signal.alarm(0)
        files = {str(path.relative_to(out)): sha256(path) for path in out.rglob("*")
                 if path.is_file() and path.name != "observed_seal.json"}
        write_json(out / "observed_seal.json", {
            "schema": "f2-three-branch-qualification/1", "status": "pass",
            "files": files, "completed_continuations": completed,
            "qualified_arms": list(ARMS),
            "truth_values_read": False,
            "run_manifest_sha256": args.manifest_sha256})
    except Exception as exc:
        numerical_failure = isinstance(
            exc, (TimeoutError, FloatingPointError, np.linalg.LinAlgError))
        optional_failure = current == ARMS[-1] and completed == 2 and numerical_failure
        write_json(out / "failure.json", {
            "schema": "f2-three-branch-qualification/1",
            "status": "optional_arm_not_qualified" if optional_failure else "invalid_partial",
            "current_arm": current,
            "completed_continuations": completed, "truth_values_read": False,
            "numerical_failure": numerical_failure,
            "failed_attempt": None if current is None else completed + 1,
            "failed_attempt_elapsed_seconds": None if current_start is None else
                time.perf_counter() - current_start,
            "failed_attempt_checkpoints": current_checkpoints,
            "total_elapsed_seconds": time.perf_counter() - run_start,
            "error": repr(exc), "traceback": traceback.format_exc()})
        if optional_failure:
            files = {str(path.relative_to(out)): sha256(path) for path in out.rglob("*")
                     if path.is_file() and path.name != "observed_seal.json"}
            write_json(out / "observed_seal.json", {
                "schema": "f2-three-branch-qualification/1",
                "status": "partial_qualified", "files": files,
                "completed_continuations": completed,
                "qualified_arms": list(ARMS[:completed]),
                "excluded_arm": current,
                "truth_values_read": False,
                "run_manifest_sha256": args.manifest_sha256})
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("manifest", "source", "baseline", "population-observed",
                 "f2e-prefix", "f0-prefix", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
