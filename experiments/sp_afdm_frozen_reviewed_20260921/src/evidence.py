"""Shared fail-closed contracts for run identity and numeric evidence artifacts."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
from pathlib import Path

import numpy as np


FORMAT_VERSION = 2
METADATA_KEY = "__evidence_metadata__"
ARRAY_SENTINEL = "__evidence_array__"
TUPLE_SENTINEL = "__evidence_tuple__"
IDENTITY_FIELDS = (
    "format_version",
    "phase",
    "source_hashes",
    "cells",
    "configurations",
    "frames",
    "environment",
    "seed_contract",
)
SEED_ENTROPY_PREFIX = (20260920, 480017)
FRAME_SEED_COMPONENTS = {
    "channel_seed": 1,
    "information_bits": 2,
    "thermal_noise": 3,
}
PHASE_CODES = {"development": 1, "confirmation": 2}
STAGE_TIME_FIELDS = (
    "front_seconds",
    "refit_seconds",
    "detector_seconds",
    "decoder_seconds",
    "instrumentation_seconds",
)


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_hash(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def seed_contract(phase_code):
    if type(phase_code) is not int or phase_code not in PHASE_CODES.values():
        raise ValueError("phase seed code is invalid")
    return {
        "generator": "numpy.random.default_rng(numpy.random.SeedSequence(entropy))",
        "entropy_prefix": list(SEED_ENTROPY_PREFIX),
        "phase_code": phase_code,
        "components": dict(FRAME_SEED_COMPONENTS),
        "make_frame_replicate": 0,
        "make_frame_split": 2,
    }


def frame_seed_descriptor(contract, cell, frame):
    if type(cell) is not int or type(frame) is not int or cell < 0 or frame < 0:
        raise ValueError("frame seed coordinates must be nonnegative integers")
    expected = seed_contract(contract.get("phase_code") if isinstance(contract, dict) else None)
    if contract != expected:
        raise ValueError("frame seed contract differs from the executable contract")
    components = {}
    for name, component in FRAME_SEED_COMPONENTS.items():
        entropy = [*SEED_ENTROPY_PREFIX, contract["phase_code"], cell, frame, component]
        components[name] = {"component_id": component, "entropy": entropy}
    channel_seed = int(np.random.default_rng(
        np.random.SeedSequence(components["channel_seed"]["entropy"])
    ).integers(0, 2**31))
    return {
        "cell": cell,
        "frame": frame,
        "make_frame_replicate": contract["make_frame_replicate"],
        "make_frame_split": contract["make_frame_split"],
        "components": components,
        "channel_seed": channel_seed,
    }


def artifact_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload)
    os.replace(temporary, path)


def source_hashes(root):
    root = Path(root)
    hashes = {}
    for folder in ("src", "tests", "docs", "protocol", "upstream"):
        for path in sorted((root / folder).rglob("*")):
            relative = path.relative_to(root)
            if (not path.is_file() or path.suffix == ".pyc" or "__pycache__" in relative.parts
                    or path.name.startswith("e1_ldpc_code_")):
                continue
            hashes[str(relative)] = artifact_sha256(path)
    return hashes


def bind_runtime_environment():
    import torch

    required = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    if any(os.environ.get(key) != "1" for key in required):
        raise ValueError("all BLAS/OpenMP thread environment variables must equal one")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("CUDA_VISIBLE_DEVICES must be the empty string")
    if torch.cuda.is_available():
        raise ValueError("CUDA must be unavailable when hidden for the CPU protocol")
    pre_context_threads = torch.get_num_threads()
    pre_context_interop_threads = torch.get_num_interop_threads()
    if pre_context_threads != 1:
        raise ValueError("Torch intra-op threads must follow the single-thread environment")
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "hostname": platform.node(),
        "machine": platform.machine(),
        "numpy": np.__version__,
        "scipy": importlib.metadata.version("scipy"),
        "torch": importlib.metadata.version("torch"),
        "matplotlib": importlib.metadata.version("matplotlib"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "torch_cuda_available": torch.cuda.is_available(),
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "torch_pre_context_num_threads": pre_context_threads,
        "torch_pre_context_num_interop_threads": pre_context_interop_threads,
        "torch_binding_authority": "receiver context build; verified before first receiver run",
        "thread_environment": {key: os.environ[key] for key in required},
    }


def verify_runtime_binding():
    import torch

    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
        raise ValueError("receiver context did not bind effective Torch threads to one")
    if torch.cuda.is_available():
        raise ValueError("receiver context unexpectedly exposed CUDA")


def validate_environment(environment):
    required = ("python", "platform", "hostname", "machine", "numpy", "scipy", "torch", "matplotlib")
    if any(not isinstance(environment.get(key), str) or not environment[key] for key in required):
        raise ValueError("environment versions and hardware identity must be recorded")
    threads = environment.get("thread_environment")
    names = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    if not isinstance(threads, dict) or any(threads.get(key) != "1" for key in names):
        raise ValueError("saved BLAS/OpenMP thread environment is not single-threaded")
    if environment.get("torch_num_threads") != 1 or environment.get("torch_num_interop_threads") != 1:
        raise ValueError("saved effective Torch thread counts are not single-threaded")
    if environment.get("cuda_visible_devices") != "" or environment.get("torch_cuda_available") is not False:
        raise ValueError("saved run was not CPU-only with CUDA hidden")
    return environment


def manifest_identity(manifest):
    missing = [field for field in IDENTITY_FIELDS if field not in manifest]
    if missing:
        raise ValueError(f"manifest identity missing fields: {missing}")
    identity = {field: manifest[field] for field in IDENTITY_FIELDS}
    if identity["format_version"] != FORMAT_VERSION:
        raise ValueError("unsupported evidence format version")
    if identity["phase"] not in ("development", "confirmation"):
        raise ValueError("invalid run phase")
    if type(identity["frames"]) is not int or identity["frames"] < 1:
        raise ValueError("frames must be a positive integer")
    if not isinstance(identity["source_hashes"], dict) or not identity["source_hashes"]:
        raise ValueError("source hashes must be nonempty")
    if not isinstance(identity["cells"], list) or not identity["cells"]:
        raise ValueError("cells must be nonempty")
    cell_ids = [cell.get("id") for cell in identity["cells"] if isinstance(cell, dict)]
    if len(cell_ids) != len(identity["cells"]) or len(cell_ids) != len(set(cell_ids)):
        raise ValueError("cell identities must be present and unique")
    if not isinstance(identity["configurations"], dict) or not identity["configurations"]:
        raise ValueError("configurations must be nonempty")
    if not isinstance(identity["environment"], dict) or not identity["environment"]:
        raise ValueError("environment identity must be nonempty")
    validate_environment(identity["environment"])
    expected_phase_code = PHASE_CODES[identity["phase"]]
    if identity["seed_contract"] != seed_contract(expected_phase_code):
        raise ValueError("seed contract differs from the run phase")
    canonical_json(identity)
    return identity


def _array_key(prefix):
    if not prefix or prefix == METADATA_KEY:
        raise ValueError("invalid artifact array key")
    return prefix


def _pack(value, prefix, arrays):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            raise TypeError("object arrays are forbidden in evidence artifacts")
        key = _array_key(prefix)
        if key in arrays:
            raise ValueError(f"duplicate flattened array key: {key}")
        arrays[key] = value
        return {ARRAY_SENTINEL: key}
    if isinstance(value, np.generic):
        return _pack(value.item(), prefix, arrays)
    if isinstance(value, complex):
        return _pack(np.asarray(value), prefix, arrays)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite metadata is forbidden")
        return value
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("evidence metadata keys must be strings")
            child = f"{prefix}_{key}" if prefix else key
            result[key] = _pack(item, child, arrays)
        return result
    if isinstance(value, tuple):
        items = [_pack(item, f"{prefix}_{index}", arrays) for index, item in enumerate(value)]
        return {TUPLE_SENTINEL: items}
    if isinstance(value, list):
        return [_pack(item, f"{prefix}_{index}", arrays) for index, item in enumerate(value)]
    raise TypeError(f"unsupported evidence value: {type(value).__name__}")


def _array_references(tree):
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            return {tree[ARRAY_SENTINEL]}
        if set(tree) == {TUPLE_SENTINEL}:
            tree = tree[TUPLE_SENTINEL]
        refs = set()
        for value in tree.values() if isinstance(tree, dict) else tree:
            refs.update(_array_references(value))
        return refs
    if isinstance(tree, list):
        refs = set()
        for value in tree:
            refs.update(_array_references(value))
        return refs
    return set()


def _unpack(tree, arrays):
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            return arrays[tree[ARRAY_SENTINEL]].copy()
        if set(tree) == {TUPLE_SENTINEL}:
            return tuple(_unpack(value, arrays) for value in tree[TUPLE_SENTINEL])
        return {key: _unpack(value, arrays) for key, value in tree.items()}
    if isinstance(tree, list):
        return [_unpack(value, arrays) for value in tree]
    return tree


def save_artifact(path, payload, identity):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    canonical_json(identity)
    arrays = {}
    tree = _pack(payload, "", arrays)
    envelope = {"format_version": FORMAT_VERSION, "identity": identity, "payload": tree}
    arrays[METADATA_KEY] = np.frombuffer(canonical_json(envelope).encode("utf-8"), dtype=np.uint8)
    temporary = path.with_name(f".{path.stem}.tmp-{os.getpid()}.npz")
    np.savez_compressed(temporary, **arrays)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return artifact_sha256(path)


def load_artifact(path, expected_identity=None):
    path = Path(path)
    try:
        with np.load(path, allow_pickle=False) as archive:
            if METADATA_KEY not in archive.files:
                raise ValueError("artifact lacks evidence metadata")
            raw = np.asarray(archive[METADATA_KEY])
            if raw.dtype != np.uint8 or raw.ndim != 1:
                raise ValueError("artifact metadata encoding is invalid")
            envelope = json.loads(raw.tobytes().decode("utf-8"))
            if envelope.get("format_version") != FORMAT_VERSION:
                raise ValueError("artifact format version differs")
            identity = envelope.get("identity")
            if expected_identity is not None and identity != expected_identity:
                raise ValueError("artifact identity differs")
            refs = _array_references(envelope.get("payload"))
            actual = set(archive.files) - {METADATA_KEY}
            if refs != actual:
                raise ValueError("artifact array inventory differs from metadata")
            arrays = {key: np.asarray(archive[key]) for key in refs}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        raise ValueError(f"invalid evidence artifact {path}: {exc}") from exc
    return _unpack(envelope["payload"], arrays), identity


def expected_keys(manifest):
    identity = manifest_identity(manifest)
    return [
        (cell["id"], frame, arm)
        for cell in identity["cells"]
        for frame in range(identity["frames"])
        for arm in identity["configurations"]
    ]


def _validate_time(value, label, *, required=True):
    if value is None and not required:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and nonnegative")


def _validate_nested_times(value, label):
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{label}.{key}"
            if key == "seconds" or key.endswith("_seconds"):
                _validate_time(item, child, required=False)
            _validate_nested_times(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_nested_times(item, f"{label}[{index}]")


def _validate_record_times(record, key):
    complete = record["seconds"]
    for field in (*STAGE_TIME_FIELDS, "failed_round_seconds"):
        if field not in record:
            raise ValueError(f"missing {field} for {key}")
        _validate_time(record[field], f"{field} for {key}", required=False)
    if record["status"] == "ok" and record["front_seconds"] is None:
        raise ValueError(f"successful record lacks front time for {key}")
    if record["status"] == "numerical_failure":
        if any(record[field] is not None for field in STAGE_TIME_FIELDS):
            raise ValueError(f"failed record claims an unavailable stage split for {key}")
        if record["failed_round_seconds"] != complete:
            raise ValueError(f"failed record cost differs from complete time for {key}")
        if not isinstance(record.get("stage_timing_scope"), str):
            raise ValueError(f"failed record lacks timing scope for {key}")

    known_total = sum(value for value in (
        *(record[field] for field in STAGE_TIME_FIELDS), record["failed_round_seconds"]
    ) if value is not None)
    tolerance = max(1e-9, complete * 1e-9)
    if known_total > complete + tolerance:
        raise ValueError(f"stage times exceed complete time for {key}")

    rounds = record.get("round_timings")
    if not isinstance(rounds, list):
        raise ValueError(f"round timings must be a list for {key}")
    for index, timing in enumerate(rounds):
        if not isinstance(timing, dict) or timing.get("round") != index:
            raise ValueError(f"round timing order differs for {key}")
        if timing.get("status") not in ("ok", "numerical_failure"):
            raise ValueError(f"round timing status differs for {key}")
        _validate_time(timing.get("seconds"), f"round complete time for {key}")
        for field in STAGE_TIME_FIELDS[1:]:
            if field not in timing:
                raise ValueError(f"round timing lacks {field} for {key}")
            _validate_time(timing[field], f"round {field} for {key}", required=False)
        if timing["status"] == "ok" and any(timing[field] is None for field in STAGE_TIME_FIELDS[1:]):
            raise ValueError(f"completed round lacks a stage time for {key}")
        if timing["status"] == "numerical_failure" and any(
                timing[field] is not None for field in STAGE_TIME_FIELDS[1:]):
            raise ValueError(f"failed round claims an unavailable stage split for {key}")
    events = record.get("events")
    if not isinstance(events, list):
        raise ValueError(f"events must be a list for {key}")
    _validate_nested_times(rounds, f"round timings for {key}")
    _validate_nested_times(events, f"events for {key}")


def _validate_frame_seed(input_payload, truth_payload, identity, cell, frame):
    expected = frame_seed_descriptor(identity["seed_contract"], cell, frame)
    if (not isinstance(input_payload, dict) or not isinstance(truth_payload, dict)
            or input_payload.get("seed") != expected or truth_payload.get("seed") != expected):
        raise ValueError(f"frame seed provenance differs for {(cell, frame)}")


def _validate_record(record, expected, run_dir, run_hash, input_cache, truth_cache):
    key = (record.get("cell"), record.get("frame"), record.get("arm"))
    if key not in expected["keys"]:
        raise ValueError(f"ledger key outside manifest: {key}")
    if record.get("status") not in ("ok", "numerical_failure"):
        raise ValueError(f"invalid record status for {key}")
    if type(record.get("info_errors")) is not int or record["info_errors"] < 0:
        raise ValueError(f"invalid info error count for {key}")
    _validate_time(record.get("seconds"), f"complete time for {key}")
    _validate_record_times(record, key)
    timeline = record.get("timeline", [])
    if not isinstance(timeline, list):
        raise ValueError(f"invalid timeline for {key}")
    last = -1.0
    for event in timeline:
        if not isinstance(event, dict):
            raise ValueError(f"invalid timeline event for {key}")
        elapsed = event.get("elapsed")
        _validate_time(elapsed, f"timeline time for {key}")
        if elapsed < last or elapsed > record["seconds"]:
            raise ValueError(f"timeline order exceeds complete time for {key}")
        if type(event.get("info_errors")) is not int or event["info_errors"] < 0:
            raise ValueError(f"invalid timeline errors for {key}")
        last = elapsed
    for field in ("artifact_sha256", "input_sha256", "truth_sha256"):
        value = record.get(field)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"missing {field} for {key}")
    cell, frame, arm = key
    stem = f"c{cell:02d}_f{frame:05d}"
    marker = run_dir / "arrays" / f"{stem}_{arm}.npz"
    marker_identity = {
        "kind": "arm",
        "cell": cell,
        "frame": frame,
        "arm": arm,
        "status": record["status"],
        "run_identity_sha256": run_hash,
    }
    load_artifact(marker, expected_identity=marker_identity)
    if artifact_sha256(marker) != record["artifact_sha256"]:
        raise ValueError(f"arm artifact hash differs for {key}")
    frame_key = (cell, frame)
    input_path = run_dir / "arrays" / f"{stem}_input.npz"
    truth_path = run_dir / "truth" / f"{stem}.npz"
    if frame_key not in input_cache:
        input_payload, _ = load_artifact(input_path, expected_identity={
            "kind": "input", "cell": cell, "frame": frame, "run_identity_sha256": run_hash})
        truth_payload, _ = load_artifact(truth_path, expected_identity={
            "kind": "truth", "cell": cell, "frame": frame, "run_identity_sha256": run_hash})
        _validate_frame_seed(input_payload, truth_payload, expected["identity"], cell, frame)
        input_cache[frame_key] = artifact_sha256(input_path)
        truth_cache[frame_key] = artifact_sha256(truth_path)
    if input_cache[frame_key] != record["input_sha256"] or truth_cache[frame_key] != record["truth_sha256"]:
        raise ValueError(f"input/truth hash differs for {key}")
    return key


def validate_run(run_dir, expected_identity=None, *, require_complete=False, reconcile_orphans=False):
    run_dir = Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid run manifest: {exc}") from exc
    identity = manifest_identity(manifest)
    if expected_identity is not None and identity != manifest_identity(expected_identity):
        raise ValueError("run identity differs from requested identity")
    run_hash = canonical_hash(identity)
    ordered = expected_keys(identity)
    expected = set(ordered)
    validation_context = {"keys": expected, "identity": identity}
    ledger_path = run_dir / "ledger.jsonl"
    try:
        lines = ledger_path.read_text().splitlines() if ledger_path.exists() else []
        records = [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid run ledger: {exc}") from exc
    index = {}
    input_cache = {}
    truth_cache = {}
    for record in records:
        key = _validate_record(record, validation_context, run_dir, run_hash, input_cache, truth_cache)
        if key in index:
            raise ValueError(f"duplicate ledger key: {key}")
        index[key] = record
    orphaned = []
    for key in ordered:
        if key in index:
            continue
        cell, frame, arm = key
        marker = run_dir / "arrays" / f"c{cell:02d}_f{frame:05d}_{arm}.npz"
        if not marker.exists():
            continue
        marker_identity = {
            "kind": "arm",
            "cell": cell,
            "frame": frame,
            "arm": arm,
            "status": "ok",
            "run_identity_sha256": run_hash,
        }
        try:
            _, actual_identity = load_artifact(marker)
        except ValueError as exc:
            raise ValueError(f"invalid orphan artifact {marker}: {exc}") from exc
        if actual_identity not in (marker_identity, dict(marker_identity, status="numerical_failure")):
            raise ValueError(f"orphan artifact identity differs for {key}")
        stem = f"c{cell:02d}_f{frame:05d}"
        input_payload, _ = load_artifact(run_dir / "arrays" / f"{stem}_input.npz", expected_identity={
            "kind": "input", "cell": cell, "frame": frame, "run_identity_sha256": run_hash})
        truth_payload, _ = load_artifact(run_dir / "truth" / f"{stem}.npz", expected_identity={
            "kind": "truth", "cell": cell, "frame": frame, "run_identity_sha256": run_hash})
        _validate_frame_seed(input_payload, truth_payload, identity, cell, frame)
        if not reconcile_orphans:
            raise ValueError(f"orphan artifact without ledger row: {key}")
        digest = artifact_sha256(marker)
        orphan_dir = run_dir / "orphans"
        orphan_dir.mkdir(exist_ok=True)
        preserved = orphan_dir / f"{marker.stem}.orphan-{digest[:12]}.npz"
        if preserved.exists():
            raise ValueError(f"orphan preservation target already exists: {preserved}")
        os.replace(marker, preserved)
        with (orphan_dir / "orphaned.jsonl").open("a") as handle:
            handle.write(json.dumps({"key": key, "sha256": digest, "preserved": preserved.name}) + "\n")
        orphaned.append(str(preserved))
    pending = [key for key in ordered if key not in index]
    if require_complete and pending:
        raise ValueError(f"incomplete run: expected {len(ordered)} records, got {len(index)}")
    return {
        "manifest": manifest,
        "identity": identity,
        "run_identity_sha256": run_hash,
        "records": records,
        "index": index,
        "pending": pending,
        "orphaned": orphaned,
    }
