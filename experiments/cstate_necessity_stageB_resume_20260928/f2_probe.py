"""One hash-bound, observed-only F2E N1024 probe; never a population result.

The separate run manifest must be Git-frozen before this script is deployed.
This file has no truth path, generator, or F2T/branch entry point.
"""

from __future__ import annotations

import argparse
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
sys.path[:0] = [str(EXPERIMENTS / "tf_production_gap_audit_20260922")]
from audit_io import attach  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _timeout(_signum, _frame):
    raise TimeoutError("frozen F2E probe exceeded in-process 110-second guard")


def run(args) -> None:
    started = time.perf_counter()
    if args.out.exists() or not args.out.resolve().is_relative_to(
            Path("/data/guoyikun").resolve()):
        raise ValueError("probe output must be new and under /data/guoyikun")
    if any(os.environ.get(key) != "1" for key in
           ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")):
        raise ValueError("one CPU thread environment required")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("CUDA must be hidden")
    if sha256(args.manifest) != args.manifest_sha256:
        raise ValueError("frozen probe manifest SHA differs")
    manifest = json.loads(args.manifest.read_text())
    if (manifest.get("schema") != "f2e-first-frame-probe/1"
            or manifest.get("status") != "locked"
            or manifest.get("observation_id") != "s650_f0000"
            or manifest.get("maximum_complete_calls") != 1
            or manifest.get("maximum_wall_seconds") != 120
            or manifest.get("truth_used") is not False):
        raise ValueError("F2E probe scope differs")
    names = ("f2_estimator.py", "f2_receiver.py", "f2_probe.py")
    if set(manifest.get("source_hashes", {})) != set(names) or any(
            manifest["source_hashes"][name] != sha256(HERE / name) for name in names):
        raise ValueError("F2 probe producer source changed")
    dependencies = manifest.get("dependency_source_hashes")
    if not isinstance(dependencies, dict) or not dependencies:
        raise ValueError("probe dependency hashes missing")
    for relative, digest in dependencies.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("probe dependency path escapes experiments")
        resolved = (EXPERIMENTS / path).resolve()
        if (not resolved.is_relative_to(EXPERIMENTS.resolve())
                or sha256(resolved) != digest):
            raise ValueError(f"probe dependency source differs: {relative}")
    if manifest["population_observed_seal_sha256"] != sha256(
            args.population_observed / "observed_seal.json"):
        raise ValueError("sealed observed population differs")
    seal = json.loads((args.population_observed / "observed_seal.json").read_text())
    for name in ("manifest.json", "ledger.jsonl"):
        if seal.get("files", {}).get(name) != sha256(args.population_observed / name):
            raise ValueError(f"population {name} inventory differs")
    rows = [json.loads(line) for line in
            (args.population_observed / "ledger.jsonl").read_text().splitlines()]
    matched = [row for row in rows if row.get("observation_id") == "s650_f0000"]
    if len(matched) != 1 or matched[0].get("frame") != 0:
        raise ValueError("one fixed first-frame observation required")
    row = matched[0]
    path = args.population_observed / row["observation_path"]
    if (row["observation_sha256"] != manifest["input_sha256"]
            or seal["files"].get(row["observation_path"]) != sha256(path)
            or row["observation_sha256"] != sha256(path)):
        raise ValueError("first-frame artifact SHA differs")
    evidence = attach(args.source, args.baseline)
    if (evidence.source_hashes(args.source) != manifest["native_source_hashes"]
            or evidence.source_hashes(args.baseline) != manifest["baseline_source_hashes"]):
        raise ValueError("frozen native/baseline source hashes differ")
    from receiver import context  # noqa: PLC0415 - import after source binding
    from f2_receiver import receive_f2e  # noqa: PLC0415 - no call before journal
    environment = evidence.bind_runtime_environment()
    system, _, code, header = context()
    evidence.verify_runtime_binding()
    if (system.N_total != 1024 or system.rho != 0.5
            or system.l_max_cap != 102
            or header["code_g_sha256"] != manifest["code_g_sha256"]):
        raise ValueError("probe system/code context differs")
    payload, _ = evidence.load_artifact(path)
    if (payload["observation_id"] != "s650_f0000"
            or payload["observation_hash"] != row["observation_hash"]
            or payload["stream_ids"] != row["stream_ids"]):
        raise ValueError("probe observation semantic identity differs")
    observation = payload["observation"]
    if set(observation) != {"y", "pilot", "sigma2"}:
        raise ValueError("unapproved probe observation fields")

    args.out.mkdir(parents=True)
    (args.out / "checkpoints").mkdir()
    manifest_digest = write_json(args.out / "manifest.json", {
        "schema": "f2e-first-frame-probe-output/1", "status": "attempt_started",
        "probe_manifest_sha256": args.manifest_sha256,
        "observation_id": "s650_f0000", "input_sha256": row["observation_sha256"],
        "source_hashes": manifest["source_hashes"],
        "runtime_environment": environment,
        "scope": "one complete F2E wrapper, zero truth/generation/F2T"})
    journal = args.out / "attempts.jsonl"
    journal.touch(exist_ok=False)
    append_json(journal, {"attempt": 1, "observation_id": "s650_f0000",
                          "input_sha256": row["observation_sha256"],
                          "started_epoch": time.time()})
    checkpoints: list[dict] = []

    def sink(event, decoded):
        index = len(checkpoints)
        if index not in (0, 1) or event["round"] != index:
            raise ValueError("unexpected F2E checkpoint order")
        target = args.out / "checkpoints" / f"s650_f0000_F2E_r{index}.npz"
        digest = evidence.save_artifact(target,
            {"event": event, "decoded": np.asarray(decoded, np.uint8)},
            {"observation_id": "s650_f0000", "round": index})
        checkpoints.append({"round": index, "path": str(target.relative_to(args.out)),
                            "sha256": digest, "ready_seconds": event["ready_seconds"],
                            "durable_seconds": time.perf_counter() - started})

    before_call = time.perf_counter() - started
    call_started = time.perf_counter()
    try:
        if before_call >= 110:
            raise TimeoutError("probe preflight exhausted in-process time cap")
        signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(max(1, 110 - int(before_call)))
        decoder, arrays, detail = receive_f2e(
            observation, system, code, checkpoint_sink=sink)
        if len(checkpoints) != 2:
            raise ValueError("F2E did not complete both coded checkpoints")
        front = detail["estimator"]
        channel = front["channel"]
        summary = {key: value for key, value in front.items() if key != "channel"}
        summary["channel"] = {"delays": channel.delays,
                              "dopplers": channel.dopplers,
                              "gains": channel.gains}
        raw = args.out / "raw.npz"
        raw_digest = evidence.save_artifact(raw, {
            "observation_id": "s650_f0000", "input_sha256": row["observation_sha256"],
            "final_decoded": np.asarray(decoder["decoded"], np.uint8),
            "coded_arrays": arrays, "front": summary, "timing": detail["timing"]},
            {"observation_id": "s650_f0000", "arm": "F2E"})
        receipt = {"schema": "f2e-first-frame-probe-result/1", "status": "ok",
                   "observation_id": "s650_f0000", "complete_calls": 1,
                   "truth_values_read": False, "checkpoints": checkpoints,
                   "raw_sha256": raw_digest, "manifest_sha256": manifest_digest,
                   "receiver_seconds": time.perf_counter() - call_started,
                   "complete_seconds": time.perf_counter() - started,
                   "estimator_component_timing": front["timing"],
                   "peak_rss_kib_cumulative": resource.getrusage(
                       resource.RUSAGE_SELF).ru_maxrss}
        write_json(args.out / "receipt.json", receipt)
        signal.alarm(0)
    except Exception as exc:
        signal.alarm(0)
        write_json(args.out / "failure.json", {
            "schema": "f2e-first-frame-probe-failure/1", "status": "failed",
            "observation_id": "s650_f0000", "attempted_calls": 1,
            "truth_values_read": False, "checkpoints": checkpoints,
            "elapsed_seconds": time.perf_counter() - started,
            "error": repr(exc), "traceback": traceback.format_exc()})
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("manifest", "source", "baseline", "population-observed", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
