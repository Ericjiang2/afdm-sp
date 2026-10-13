#!/usr/bin/env python3
"""Measure one Part-A arm in one fresh process on saved E1 D frame 650/0.

Invoke separately for all four arms. Each invocation makes exactly one warmup
and one measured receiver call; neither call generates a radio observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from common import append_jsonl, attach, bits, finite_seconds, observation_hash, plan, unbits


ARMS = {
    "TF_J20_R2": ("tf", 20, "soft"),
    "EP2_MEAN_R2": ("ep", 2, "mean"),
    "EP4_MEAN_R2": ("ep", 4, "mean"),
    "PBI8_SOFT_R2": ("pbi", 8, "soft"),
}
SCHEMA = "spafdm-pd1q-isolated-memory/1"
E1_SCHEMA = "spafdm-native-direction-compact/1"
SNR, FRAME = 650, 0


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--source", type=Path, required=True)
    value.add_argument("--baseline", type=Path, required=True)
    value.add_argument("--e1-root", type=Path, required=True,
                       help="saved E1 D run directory containing manifest.json and frames/")
    value.add_argument("--out", type=Path, required=True,
                       help="new, arm-specific output directory")
    value.add_argument("--arm", choices=tuple(ARMS), required=True)
    return value


def process_memory():
    fields = {"rss_kib": None, "high_water_kib": None}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            fields["rss_kib"] = int(line.split()[1])
        elif line.startswith("VmHWM:"):
            fields["high_water_kib"] = int(line.split()[1])
    if None in fields.values():
        raise RuntimeError("Linux RSS/HWM process counters unavailable")
    return fields


def storage_inventory(value):
    """Deduplicate visible NumPy views by their backing ndarray per sample."""
    seen_objects, storages = set(), {}

    def visit(item, depth=0):
        if depth > 3 or id(item) in seen_objects:
            return
        seen_objects.add(id(item))
        if isinstance(item, np.ndarray):
            owner = item
            while isinstance(owner.base, np.ndarray):
                owner = owner.base
            storages[id(owner)] = owner.nbytes
        elif isinstance(item, dict):
            for member in item.values():
                visit(member, depth + 1)
        elif isinstance(item, (list, tuple)):
            for member in item:
                visit(member, depth + 1)

    visit(value)
    return storages


class VisibleArrays:
    """Return-boundary snapshots; never presented as a total process allocation."""

    FUNCTIONS = frozenset(("pilot_front", "time_refine", "scalar_joint", "ep_t",
                           "pbigabp", "receive", "receive_control"))

    def __init__(self, static_storage_ids):
        self.static_storage_ids = static_storage_ids
        self.max_bytes = 0
        self.by_function = {}
        self.samples = 0
        self.callback_seconds = 0.0

    def callback(self, frame, event, _argument):
        if event != "return" or frame.f_code.co_name not in self.FUNCTIONS:
            return
        began = time.perf_counter()
        inventory = storage_inventory(frame.f_locals)
        size = sum(size for key, size in inventory.items()
                   if key not in self.static_storage_ids)
        name = frame.f_code.co_name
        self.max_bytes = max(self.max_bytes, size)
        self.by_function[name] = max(self.by_function.get(name, 0), size)
        self.samples += 1
        self.callback_seconds += time.perf_counter() - began

    def report(self):
        return {"max_visible_bytes_at_sample": self.max_bytes,
                "max_visible_bytes_by_function": self.by_function,
                "sampled_function_returns": self.samples,
                "callback_seconds_lower_bound": self.callback_seconds,
                "scope": "New NumPy arrays visible at selected Python returns, excluding observed input/static code storage and deduplicating shared backing storage per sample; lower bound only; excludes hidden BLAS/Torch/native workspaces"}


def main():
    args = parser().parse_args()
    args.source, args.baseline, args.e1_root, args.out = (
        item.resolve() for item in (args.source, args.baseline, args.e1_root, args.out))
    cfg = plan()
    if args.source.name != cfg["source_root_name"]:
        raise ValueError("memory source root differs from frozen Part A plan")
    if args.out.exists():
        raise ValueError("isolated process output already exists")
    evidence = attach(args.source, args.baseline)
    from receiver import context
    from native_twofft import receive
    from native_controls import receive_control
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info

    old_path = args.e1_root / "manifest.json"
    if evidence.artifact_sha256(old_path) != cfg["e1_manifest_sha256"]:
        raise ValueError("saved E1 D manifest differs")
    old_manifest = json.loads(old_path.read_text())
    if old_manifest["stage"] != "D" or old_manifest["source_commit"] != cfg["source_commit"]:
        raise ValueError("saved E1 D source/stage differs")
    source_hashes = evidence.source_hashes(args.source)
    baseline_hashes = evidence.source_hashes(args.baseline)
    if (old_manifest["source_hashes"] != source_hashes or
            old_manifest["baseline_source_hashes"] != baseline_hashes):
        raise ValueError("numerical source differs from saved E1 D")
    handoff_sha = source_hashes.get("docs/CODEX_HANDOFF.md")
    if handoff_sha is None or handoff_sha != cfg["handoff_sha256"] or handoff_sha != evidence.artifact_sha256(
            args.source / "docs" / "CODEX_HANDOFF.md"):
        raise ValueError("canonical numerical handoff is absent from source identity")
    old_hash = evidence.canonical_hash(old_manifest)
    def old_identity(kind):
        return {"schema": E1_SCHEMA, "run_identity_sha256": old_hash,
                "kind": kind, "snr_centi_db": SNR, "frame": FRAME}

    input_path = args.e1_root / "frames" / "s650_f000_input.npz"
    truth_path = args.e1_root / "frames" / "s650_f000_truth.npz"
    observed, _ = evidence.load_artifact(input_path, old_identity("frame_input"))
    truth, _ = evidence.load_artifact(truth_path, old_identity("frame_truth"))
    if observation_hash(observed) != truth["input_hash"]:
        raise ValueError("saved E1 input/truth pairing differs")
    truth_info = unbits(truth["info"], cfg["source_scope"]["code_k"])
    truth_coded = unbits(truth["coded"], cfg["source_scope"]["code_n"])
    observed = {name: observed[name] for name in ("y", "pilot", "sigma2")}
    system, _model, code, header = context()
    evidence.verify_runtime_binding()
    system.P_paths = cfg["source_scope"]["paths"]
    system.rho = cfg["source_scope"]["rho"]
    if header["code_g_sha256"] != cfg["generator_sha256"]:
        raise ValueError("actual code generator differs")

    run = {"schema": SCHEMA, "arm": args.arm, "source_commit": cfg["source_commit"],
           "source_hashes": source_hashes, "baseline_source_hashes": baseline_hashes,
           "handoff_sha256": handoff_sha,
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "plan_sha256": evidence.artifact_sha256(Path(__file__).with_name("plan.json")),
           "e1_manifest_sha256": cfg["e1_manifest_sha256"],
           "e1_run_identity_sha256": old_hash,
           "e1_input_sha256": evidence.artifact_sha256(input_path),
           "e1_truth_sha256": evidence.artifact_sha256(truth_path),
           "input_hash": observation_hash(observed),
           "environment": evidence.bind_runtime_environment(),
           "pid": os.getpid(), "process_started_unix": time.time(),
           "receiver_calls_planned": 2,
           "scope": "one warmup and one measured call, same saved E1 D 650/0 observation"}
    run_hash = evidence.canonical_hash(run)
    args.out.mkdir(parents=True)
    (args.out / "checkpoints").mkdir()
    (args.out / "attempts").mkdir()
    evidence.write_json_atomic(args.out / "manifest.json", run)
    baseline = process_memory()  # Imports, static context and saved input are already resident.
    evidence.write_json_atomic(args.out / "baseline_memory.json", baseline)
    static_storage_ids = set(storage_inventory(
        {"observed": observed, "code": code, "system": vars(system)}))

    for label in ("warmup", "measured"):
        checkpoints = []
        storage_seconds = 0.0
        def checkpoint_sink(event, decoded):
            nonlocal storage_seconds
            began = time.perf_counter()
            round_index = event["round"]
            metadata = {key: value for key, value in event.items() if key != "snapshot"}
            payload = {"event": metadata, "decoded": bits(decoded),
                       "snapshot": event["snapshot"]}
            path = args.out / "checkpoints" / f"{label}_r{round_index}.npz"
            checkpoint_id = {"schema": SCHEMA, "run_identity_sha256": run_hash,
                             "kind": "checkpoint", "arm": args.arm,
                             "attempt": label, "round": round_index}
            digest = evidence.save_artifact(path, payload, checkpoint_id)
            checkpoints.append({"round": round_index, "path": str(path.relative_to(args.out)),
                                "artifact_sha256": digest,
                                "decoded": np.asarray(decoded).copy(), "event": metadata})
            storage_seconds += time.perf_counter() - began

        visible = VisibleArrays(static_storage_ids)
        started = time.perf_counter()
        status, result, exception = "ok", None, None
        sys.setprofile(visible.callback)
        try:
            if args.arm == "TF_J20_R2":
                result = receive(observed, system, code, rounds=2, iterations=20,
                                 ce_mode="soft", gain_mode="joint",
                                 checkpoint_sink=checkpoint_sink, record_states=False)
            else:
                kind, iterations, ce_mode = ARMS[args.arm]
                result = receive_control(observed, system, code, kind=kind,
                    iterations=iterations, ce_mode=ce_mode,
                    checkpoint_sink=checkpoint_sink)
        except (np.linalg.LinAlgError, FloatingPointError) as error:
            status, exception = "numerical_failure", traceback.format_exc()
            error_data = {"type": type(error).__name__, "message": str(error),
                          "traceback": exception}
        except Exception as error:
            status, exception = "integrity_failure", traceback.format_exc()
            error_data = {"type": type(error).__name__, "message": str(error),
                          "traceback": exception}
        finally:
            sys.setprofile(None)
            probe_seconds = finite_seconds(time.perf_counter() - started, "probe wall")
        after = process_memory()
        if status == "ok" and (len(checkpoints) != 2 or
                               not np.array_equal(result[0]["decoded"], checkpoints[-1]["decoded"])):
            raise ValueError("receiver result/checkpoints differ")

        scored = []
        for checkpoint in checkpoints:
            decoded = checkpoint.pop("decoded")
            scored.append({"round": checkpoint["round"], "path": checkpoint["path"],
                           "artifact_sha256": checkpoint["artifact_sha256"],
                           "event": checkpoint["event"],
                           "info_errors": int(np.count_nonzero(extract_info(code, decoded) != truth_info)),
                           "coded_errors": int(np.count_nonzero(decoded != truth_coded))})
        record = {"attempt": label, "status": status, "probe_wall_seconds": probe_seconds,
                  "receiver_reported_seconds": None if result is None else result[2]["seconds"],
                  "pilot_seconds": None if result is None else result[2]["pilot_seconds"],
                  "checkpoint_storage_seconds": storage_seconds,
                  "visible_arrays": visible.report(), "memory_after": after,
                  "checkpoints": scored, "exception": exception,
                  "memory_scope": "VmHWM is cumulative process peak through this attempt, including static context and warmup; probe wall includes instrumentation and checkpoint persistence; not ordinary latency"}
        marker = args.out / "attempts" / f"{label}.npz"
        evidence.save_artifact(marker, record,
            {"schema": SCHEMA, "run_identity_sha256": run_hash,
             "kind": "attempt", "arm": args.arm, "attempt": label})
        append_jsonl(args.out / "ledger.jsonl", record)
        if status != "ok":
            evidence.write_json_atomic(args.out / "failure.json", error_data)
            raise RuntimeError(f"{label} {status} saved; stop isolated calls")

    evidence.write_json_atomic(args.out / "memory_summary.json", {
        "schema": SCHEMA, "arm": args.arm, "baseline_current_rss_kib": baseline["rss_kib"],
        "total_process_peak_rss_kib": process_memory()["high_water_kib"],
        "scope": "total fresh process high-water including imports, static context, warmup, measured call and probe; visible online arrays separately in ledger"})


if __name__ == "__main__":
    main()
