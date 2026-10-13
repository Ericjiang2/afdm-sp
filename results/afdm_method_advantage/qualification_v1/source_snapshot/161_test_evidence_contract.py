"""Synthetic evidence-boundary regressions; no receiver performance evidence."""
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evidence import (  # noqa: E402
    artifact_sha256,
    bind_runtime_environment,
    canonical_hash,
    frame_seed_descriptor,
    load_artifact,
    save_artifact,
    seed_contract,
    source_hashes,
    validate_run,
    write_json_atomic,
)
import run_local  # noqa: E402
from seal import deadline_error  # noqa: E402


payload = {
    "array": np.arange(4, dtype=np.int16),
    "scalar": np.float64(1.25),
    "text": "decoder",
    "flag": True,
    "nested": [{"iteration": 3, "raw": np.array([1.0, -2.0])}],
}
identity = {"kind": "unit", "cell": 0, "frame": 0, "arm": "A"}
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "payload.npz"
    digest = save_artifact(path, payload, identity)
    restored, restored_identity = load_artifact(path, expected_identity=identity)
    assert digest == artifact_sha256(path)
    assert restored_identity == identity
    assert np.array_equal(restored["array"], payload["array"])
    assert restored["scalar"] == payload["scalar"]
    assert restored["text"] == payload["text"] and restored["flag"] is True
    assert restored["nested"][0]["iteration"] == 3
    assert np.array_equal(restored["nested"][0]["raw"], payload["nested"][0]["raw"])


def make_manifest(arms):
    environment = {
        "python": "synthetic", "platform": "synthetic", "hostname": "synthetic",
        "machine": "synthetic", "numpy": "synthetic", "scipy": "synthetic",
        "torch": "synthetic", "matplotlib": "synthetic", "cuda_visible_devices": "",
        "torch_cuda_available": False, "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "thread_environment": {key: "1" for key in
                               ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
    }
    return {
        "format_version": 2,
        "phase": "development",
        "source_hashes": {"src/example.py": "a" * 64},
        "cells": [{"id": 0, "snr_db": 7}],
        "configurations": {arm: {"family": "synthetic"} for arm in arms},
        "frames": 1,
        "environment": environment,
        "seed_contract": seed_contract(1),
    }


def frame_seed(manifest, cell=0, frame=0):
    return frame_seed_descriptor(manifest["seed_contract"], cell, frame)


def success_times():
    return {
        "front_seconds": 0.2,
        "refit_seconds": 0.2,
        "detector_seconds": 0.2,
        "decoder_seconds": 0.2,
        "instrumentation_seconds": 0.0,
        "failed_round_seconds": 0.0,
        "round_timings": [],
        "events": [],
    }


with tempfile.TemporaryDirectory() as tmp:
    run_dir = Path(tmp)
    (run_dir / "arrays").mkdir()
    (run_dir / "truth").mkdir()
    manifest = make_manifest(["A"])
    run_hash = canonical_hash(manifest)
    write_json_atomic(run_dir / "manifest.json", manifest)
    input_path = run_dir / "arrays" / "c00_f00000_input.npz"
    truth_path = run_dir / "truth" / "c00_f00000.npz"
    marker_path = run_dir / "arrays" / "c00_f00000_A.npz"
    input_payload = {"y": np.ones(2), "pilot": np.zeros(2), "sigma2": 1.0,
                     "seed": frame_seed(manifest)}
    truth_payload = {"info": np.array([0, 1], dtype=np.uint8), "seed": frame_seed(manifest)}
    input_hash = save_artifact(input_path, input_payload,
                               {"kind": "input", "cell": 0, "frame": 0, "run_identity_sha256": run_hash})
    truth_hash = save_artifact(truth_path, truth_payload,
                               {"kind": "truth", "cell": 0, "frame": 0, "run_identity_sha256": run_hash})
    marker_hash = save_artifact(marker_path, {"decoded": np.array([0, 1], dtype=np.uint8)},
                                {"kind": "arm", "cell": 0, "frame": 0, "arm": "A",
                                 "status": "ok", "run_identity_sha256": run_hash})
    record = {
        "cell": 0,
        "frame": 0,
        "arm": "A",
        "status": "ok",
        "seconds": 1.0,
        "info_errors": 0,
        "timeline": [{"elapsed": 0.5, "info_errors": 0}],
        "artifact_sha256": marker_hash,
        "input_sha256": input_hash,
        "truth_sha256": truth_hash,
        **success_times(),
    }
    (run_dir / "ledger.jsonl").write_text(json.dumps(record) + "\n")
    before = (input_path.stat().st_mtime_ns, truth_path.stat().st_mtime_ns, marker_path.stat().st_mtime_ns)
    checked = validate_run(run_dir, expected_identity=manifest, require_complete=True)
    after = (input_path.stat().st_mtime_ns, truth_path.stat().st_mtime_ns, marker_path.stat().st_mtime_ns)
    assert before == after and checked["pending"] == [] and len(checked["records"]) == 1
    mismatch = dict(manifest, frames=2)
    try:
        validate_run(run_dir, expected_identity=mismatch)
    except ValueError as exc:
        assert "identity" in str(exc).lower()
    else:
        raise AssertionError("resume accepted a mismatched manifest")
    record["decoder_seconds"] = -1.0
    (run_dir / "ledger.jsonl").write_text(json.dumps(record) + "\n")
    try:
        validate_run(run_dir)
    except ValueError as exc:
        assert "decoder_seconds" in str(exc)
    else:
        raise AssertionError("negative stage time was accepted")
    record.update(success_times())
    input_payload["seed"] = dict(input_payload["seed"], channel_seed=input_payload["seed"]["channel_seed"] + 1)
    record["input_sha256"] = save_artifact(input_path, input_payload,
        {"kind": "input", "cell": 0, "frame": 0, "run_identity_sha256": run_hash})
    (run_dir / "ledger.jsonl").write_text(json.dumps(record) + "\n")
    try:
        validate_run(run_dir)
    except ValueError as exc:
        assert "seed provenance" in str(exc)
    else:
        raise AssertionError("mismatched frame seed provenance was accepted")


with tempfile.TemporaryDirectory() as tmp:
    run_dir = Path(tmp)
    (run_dir / "arrays").mkdir()
    (run_dir / "truth").mkdir()
    manifest = make_manifest(["A"])
    run_hash = canonical_hash(manifest)
    write_json_atomic(run_dir / "manifest.json", manifest)
    save_artifact(run_dir / "arrays" / "c00_f00000_input.npz",
                  {"y": np.ones(2), "pilot": np.zeros(2), "sigma2": 1.0,
                   "seed": frame_seed(manifest)},
                  {"kind": "input", "cell": 0, "frame": 0, "run_identity_sha256": run_hash})
    save_artifact(run_dir / "truth" / "c00_f00000.npz",
                  {"info": np.array([0, 1], dtype=np.uint8), "seed": frame_seed(manifest)},
                  {"kind": "truth", "cell": 0, "frame": 0, "run_identity_sha256": run_hash})
    orphan = run_dir / "arrays" / "c00_f00000_A.npz"
    orphan_hash = save_artifact(orphan, {"decoded": np.array([0, 1], dtype=np.uint8)},
                                {"kind": "arm", "cell": 0, "frame": 0, "arm": "A",
                                 "status": "ok", "run_identity_sha256": run_hash})
    checked = validate_run(run_dir, expected_identity=manifest, reconcile_orphans=True)
    assert checked["pending"] == [(0, 0, "A")]
    assert len(checked["orphaned"]) == 1 and not orphan.exists()
    preserved = Path(checked["orphaned"][0])
    assert preserved.exists() and artifact_sha256(preserved) == orphan_hash


assert deadline_error({"status": "numerical_failure", "seconds": None, "info_errors": 1,
                       "timeline": [{"elapsed": 0.5, "info_errors": 0}]}, 1.0) == 0
for invalid in (math.nan, math.inf, -1.0):
    try:
        deadline_error({"status": "ok", "seconds": invalid, "info_errors": 0, "timeline": []}, 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid complete time was accepted")


protocol = json.loads((ROOT / "protocol" / "protocol.json").read_text())
catalog = json.loads((ROOT / "protocol" / "configurations.json").read_text())
environment = bind_runtime_environment()
current = source_hashes(ROOT)
zero_args = SimpleNamespace(phase="development", lock=None, frames=0, arms=[next(iter(catalog))], cell=0)
try:
    run_local.resolve_plan(zero_args, protocol, catalog, current, environment)
except ValueError as exc:
    assert "positive" in str(exc)
else:
    raise AssertionError("--frames 0 did not fail before receiver context")


with tempfile.TemporaryDirectory() as tmp:
    run_dir = Path(tmp) / "complete"
    (run_dir / "arrays").mkdir(parents=True)
    (run_dir / "truth").mkdir()
    arm = next(iter(catalog))
    args = SimpleNamespace(phase="development", lock=None, frames=1, arms=[arm], cell=0)
    planned, _ = run_local.resolve_plan(args, protocol, catalog, current, environment)
    write_json_atomic(run_dir / "manifest.json", planned)
    run_hash = canonical_hash(planned)
    input_path = run_dir / "arrays" / "c00_f00000_input.npz"
    truth_path = run_dir / "truth" / "c00_f00000.npz"
    marker_path = run_dir / "arrays" / f"c00_f00000_{arm}.npz"
    input_hash = save_artifact(input_path, {"y": np.ones(2), "pilot": np.zeros(2), "sigma2": 1.0,
                                                   "seed": frame_seed(planned)},
                               {"kind": "input", "cell": 0, "frame": 0, "run_identity_sha256": run_hash})
    truth_hash = save_artifact(truth_path, {"info": np.array([0, 1], dtype=np.uint8),
                                            "seed": frame_seed(planned)},
                               {"kind": "truth", "cell": 0, "frame": 0, "run_identity_sha256": run_hash})
    marker_hash = save_artifact(marker_path, {"decoded": np.array([0, 1], dtype=np.uint8)},
                                {"kind": "arm", "cell": 0, "frame": 0, "arm": arm,
                                 "status": "ok", "run_identity_sha256": run_hash})
    record = {"cell": 0, "frame": 0, "arm": arm, "status": "ok", "seconds": 1.0,
              "info_errors": 0, "timeline": [{"elapsed": 1.0, "info_errors": 0}],
              "artifact_sha256": marker_hash, "input_sha256": input_hash,
              "truth_sha256": truth_hash, **success_times()}
    (run_dir / "ledger.jsonl").write_text(json.dumps(record) + "\n")
    before = tuple(path.stat().st_mtime_ns for path in (input_path, truth_path, marker_path))
    original_context = run_local.context
    run_local.context = lambda: (_ for _ in ()).throw(AssertionError("receiver context executed"))
    try:
        run_local.main(["--phase", "development", "--out", str(run_dir), "--frames", "1",
                        "--arms", arm, "--cell", "0"])
    finally:
        run_local.context = original_context
    after = tuple(path.stat().st_mtime_ns for path in (input_path, truth_path, marker_path))
    assert before == after

print("PASS evidence identity, lossless payload, orphan recovery, deadline, and no-op resume contracts")
