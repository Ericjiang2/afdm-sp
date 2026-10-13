#!/usr/bin/env python3
"""Independent read-only recount of a sealed TF-CGR observed run.

This verifier never imports the receiver or the producer.  Its default mode
opens only observed-run artifacts and witness observations.  Truth payloads
are read only with ``--truth-analysis`` after ``--seal-commit`` resolves to a
real Git object containing the exact observed seal bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments"
RESULTS = ROOT / "results/tf_cgr_mechanism_20260923_v2"
INDEPENDENT = ROOT / "results/tf_cgr_mechanism_20260923/independent"
SCHEMA = "tf-cgr-observed/1"
ARMS = ("BASE", "CGR", "SHAM", "BLOCK")
METADATA = "__evidence_metadata__"
ARRAY_SENTINEL = "__evidence_array__"
TUPLE_SENTINEL = "__evidence_tuple__"
TARGET_IDS = frozenset(("s650_f0390", "s650_f0415", "s650_f0718",
                        "s650_f0720", "s650_f0770", "s650_f0996",
                        "s600_f0600", "s700_f0732"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    require(not rel.is_absolute() and ".." not in rel.parts,
            f"unsafe relative path: {relative}")
    candidate = root / rel
    require(not candidate.is_symlink(), f"symlink artifact rejected: {relative}")
    resolved = candidate.resolve()
    require(resolved.is_relative_to(root.resolve()),
            f"artifact escapes its root: {relative}")
    require(resolved.is_file(), f"artifact is missing: {relative}")
    return resolved


def _refs(tree: Any) -> set[str]:
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            key = tree[ARRAY_SENTINEL]
            require(isinstance(key, str) and key, "invalid evidence array reference")
            return {key}
        if set(tree) == {TUPLE_SENTINEL}:
            tree = tree[TUPLE_SENTINEL]
        values = tree.values() if isinstance(tree, dict) else tree
        out: set[str] = set()
        for value in values:
            out.update(_refs(value))
        return out
    if isinstance(tree, list):
        out: set[str] = set()
        for value in tree:
            out.update(_refs(value))
        return out
    return set()


def _unpack(tree: Any, arrays: dict[str, np.ndarray]) -> Any:
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            return arrays[tree[ARRAY_SENTINEL]].copy()
        if set(tree) == {TUPLE_SENTINEL}:
            return tuple(_unpack(value, arrays) for value in tree[TUPLE_SENTINEL])
        return {key: _unpack(value, arrays) for key, value in tree.items()}
    if isinstance(tree, list):
        return [_unpack(value, arrays) for value in tree]
    return tree


def load_artifact(path: Path, expected_identity: dict[str, Any] | None = None):
    """Decode evidence v2 without importing its producer implementation."""
    try:
        with np.load(path, allow_pickle=False) as archive:
            require(METADATA in archive.files, f"missing evidence metadata: {path}")
            raw = np.asarray(archive[METADATA])
            require(raw.dtype == np.uint8 and raw.ndim == 1,
                    f"invalid evidence metadata encoding: {path}")
            envelope = json.loads(raw.tobytes().decode("utf-8"))
            require(envelope.get("format_version") == 2,
                    f"unsupported evidence format: {path}")
            identity = envelope.get("identity")
            if expected_identity is not None:
                require(identity == expected_identity,
                        f"artifact identity mismatch: {path}")
            tree = envelope.get("payload")
            refs = _refs(tree)
            actual = set(archive.files) - {METADATA}
            require(refs == actual, f"evidence array inventory mismatch: {path}")
            arrays = {key: np.asarray(archive[key]) for key in refs}
            require(all(not arr.dtype.hasobject for arr in arrays.values()),
                    f"object array forbidden: {path}")
        return _unpack(tree, arrays), identity
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        raise ValueError(f"invalid evidence artifact {path}: {exc}") from exc


def _json(path: Path):
    return json.loads(path.read_text())


def _hash_value(value: Any) -> str:
    """Independent reproduction of the producer's entering-dict digest."""
    digest = hashlib.sha256()

    def visit(item):
        if isinstance(item, dict):
            for key in sorted(item):
                digest.update(key.encode())
                visit(item[key])
        elif isinstance(item, (list, tuple)):
            digest.update(str(len(item)).encode())
            for child in item:
                visit(child)
        elif isinstance(item, np.ndarray):
            arr = np.ascontiguousarray(item)
            digest.update(str(arr.dtype).encode())
            digest.update(json.dumps(arr.shape).encode())
            digest.update(arr.tobytes())
        else:
            digest.update(json.dumps(item, sort_keys=True, allow_nan=False).encode())

    visit(value)
    return digest.hexdigest()


def build_calls(entries: list[dict[str, Any]]):
    require(len(entries) == 25, "witness frame count differs from locked 25")
    ids = [entry["observation_id"] for entry in entries]
    require(len(set(ids)) == 25, "witness observation IDs are not unique")
    roles = [entry["role"] for entry in entries]
    expected_roles = {
        "target_remaining_failure": 8,
        "matched_rescued_control": 7,
        "matched_easy_control": 7,
        "distinct_delay_failure_specificity": 3,
    }
    require({role: roles.count(role) for role in expected_roles} == expected_roles,
            "witness role allocation differs from 8+7+7+3")
    require({entry["observation_id"] for entry in entries
             if entry["role"] == "target_remaining_failure"} == TARGET_IDS,
            "target witness identity differs")
    return [(entry, arm) for index, entry in enumerate(entries)
            for arm in ARMS[index % 4:] + ARMS[:index % 4]]


def _source_files(args) -> dict[str, Path]:
    files = {
        "geometry_validation": args.geometry / "geometry_validation.py",
        "compact_state": args.geometry / "compact_state.py",
        "geometry_reopen": EXP / "tf_geometry_reopen_20260922/geometry_reopen.py",
        "audit_io": EXP / "tf_production_gap_audit_20260922/audit_io.py",
        "code_cache": args.code_cache,
    }
    for label, root in (("native", args.source), ("baseline", args.baseline)):
        for folder in ("src", "upstream"):
            for path in sorted((root / folder).rglob("*.py")):
                if "__pycache__" not in path.parts:
                    files[f"{label}/{path.relative_to(root)}"] = path
    cgr = args.producer
    for name in ("run_observed.py", "generate_variants.py", "tf_base.py",
                 "tf_cgr.py", "tf_sham.py", "tf_block.py"):
        files[f"cgr/{name}"] = cgr / name
    return files


def _validate_source_and_code(args, run_manifest, witness_manifest):
    bindings = _json(args.source_bindings)
    require(sha256(args.source_bindings) == run_manifest["source_bindings_sha256"],
            "source bindings file SHA differs from run manifest")
    require(bindings == run_manifest["source_hashes"],
            "run manifest source hashes differ from the frozen source binding")
    actual = {}
    for name, path in _source_files(args).items():
        require(path.is_file(), f"bound source missing: {name}")
        actual[name] = sha256(path)
    require(actual == bindings, "local production source binding differs")
    require(sha256(args.witness_manifest) == run_manifest["witness_manifest_sha256"],
            "witness manifest SHA differs")
    require(sha256(args.witness_receipt) == run_manifest["witness_receipt_sha256"],
            "witness receipt SHA differs")
    require(sha256(args.registration) == run_manifest["registration_sha256"],
            "registration SHA differs")
    require(sha256(args.qualification) == run_manifest["qualification_sha256"],
            "qualification SHA differs")
    require(witness_manifest.get("schema") == "coherent-gain-witness-request/1" and
            witness_manifest.get("n_frames") == 25, "witness manifest schema differs")
    registration = _json(args.registration)
    qualification = _json(args.qualification)
    require(registration.get("schema") == "tf-cgr-registration/1" and
            registration.get("status") == "locked" and
            registration.get("truth_online") is False,
            "registration is not the locked observed-only protocol")
    require(qualification.get("status") == "synthetic_pass" and
            qualification.get("source_sha256") == actual.get("native/src/twofft.py"),
            "synthetic qualification does not bind current native TF")
    with np.load(args.code_cache, allow_pickle=False) as archive:
        require({"H", "G", "free_cols"}.issubset(archive.files),
                "frozen code cache lacks H/G/free_cols")
        H = np.asarray(archive["H"]).copy()
        G = np.asarray(archive["G"]).copy()
        free = np.asarray(archive["free_cols"]).copy()
    require(H.shape == (1026, 2048) and G.shape == (2048, 1024) and
            free.shape == (1024,), "actual H/G/free_cols dimensions differ")
    require(np.isin(H, [0, 1]).all() and np.isin(G, [0, 1]).all(),
            "H/G are not exact binary arrays")
    require(np.issubdtype(free.dtype, np.integer) and
            np.all((free >= 0) & (free < 2048)) and len(np.unique(free)) == 1024,
            "free_cols are not 1024 unique in-range codeword positions")
    require(hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest() ==
            run_manifest["code_g_sha256"], "actual G data SHA differs")
    # uint8 accumulates modulo 256; because 256 is even, its parity is still
    # exactly the GF(2) dot product and avoids a multi-gigabyte int64 product.
    require(not np.any((H.astype(np.uint8) @ G.astype(np.uint8)) & 1),
            "frozen H@G is nonzero over GF(2)")
    require(np.array_equal(G[free], np.eye(1024, dtype=G.dtype)),
            "free_cols do not select the exact systematic information bits")
    return H, G, free, actual


def _inventory_files(run: Path, seal: dict[str, Any]):
    declared = seal.get("files")
    require(isinstance(declared, dict) and declared,
            "observed seal has no file inventory")
    actual_paths = set()
    actual_hashes = {}
    for path in run.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"symlink in sealed output: {path}")
        if path.is_file() and path.name != "observed_seal.json":
            relative = str(path.relative_to(run))
            actual_paths.add(relative)
            actual_hashes[relative] = sha256(path)
    require(actual_paths == set(declared),
            "sealed output file inventory differs (missing/extra files)")
    require(actual_hashes == declared, "sealed output SHA inventory differs")
    return actual_hashes


def _bits(value, label):
    arr = np.asarray(value)
    require(arr.ndim == 1 and arr.shape == (2048,) and
            np.isin(arr, [0, 1]).all(), f"invalid 2048-bit decision at {label}")
    return arr.astype(np.uint8, copy=False)


def _syndrome(H, bits):
    return int(np.count_nonzero((H.astype(np.int64) @ bits.astype(np.int64)) % 2))


def _recursive_equal(left: Any, right: Any, *, atol=0.0, rtol=0.0):
    """Return equality and largest absolute numeric discrepancy."""
    max_abs = 0.0
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return False, math.inf
        for key in left:
            ok, err = _recursive_equal(left[key], right[key], atol=atol, rtol=rtol)
            max_abs = max(max_abs, err)
            if not ok:
                return False, max_abs
        return True, max_abs
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            return False, math.inf
        for a, b in zip(left, right):
            ok, err = _recursive_equal(a, b, atol=atol, rtol=rtol)
            max_abs = max(max_abs, err)
            if not ok:
                return False, max_abs
        return True, max_abs
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        a, b = np.asarray(left), np.asarray(right)
        if a.shape != b.shape:
            return False, math.inf
        if a.dtype.kind in "biu" and b.dtype.kind in "biu":
            return bool(np.array_equal(a, b)), float(np.max(np.abs(a.astype(float) - b.astype(float)), initial=0.0))
        try:
            err = float(np.max(np.abs(a - b), initial=0.0))
            return bool(np.allclose(a, b, atol=atol, rtol=rtol, equal_nan=False)), err
        except (TypeError, ValueError):
            return False, math.inf
    if isinstance(left, (float, int, complex, np.number)) and isinstance(
            right, (float, int, complex, np.number)):
        err = float(abs(left - right))
        return bool(np.isclose(left, right, atol=atol, rtol=rtol)), err
    return left == right, 0.0 if left == right else math.inf


def _percentiles(values):
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return {"n": 0, "mean": None, "p95": None, "max": None}
    require(np.isfinite(arr).all() and np.all(arr >= 0),
            "latency series is nonfinite/negative")
    return {"n": int(arr.size), "mean": float(np.mean(arr)),
            "p95": float(np.percentile(arr, 95, method="linear")),
            "max": float(np.max(arr))}


def _load_decision_bits(run, row, H):
    result = {}
    for cp in row["checkpoints"]:
        number = cp["round"]
        path = safe_path(run, cp["path"])
        require(sha256(path) == cp["artifact_sha256"],
                f"checkpoint SHA differs for call {row['call_index']} round {number}")
        ident = {"schema": SCHEMA, "observation_id": row["observation_id"],
                 "arm": row["arm"], "round": number}
        payload, identity = load_artifact(path, ident)
        bits = _bits(payload.get("decoded"), f"{path}:decoded")
        syndrome = _syndrome(H, bits)
        require(syndrome == cp["syndrome_weight"],
                f"checkpoint syndrome differs for {path}")
        require(number not in result, "duplicate checkpoint round")
        result[number] = bits
    require(sorted(result) in ([0, 1], [0, 1, 2]),
            f"checkpoint rounds are not native prefix plus optional branch: {row['observation_id']} {row['arm']}")
    return result


def verify_observed(args):
    run = args.run.resolve()
    require(run.is_dir(), f"observed run directory is missing: {run}")
    seal_path = run / "observed_seal.json"
    require(seal_path.is_file(), "observed seal is absent; only complete sealed runs qualify")
    seal = _json(seal_path)
    run_manifest = _json(run / "manifest.json")
    witness_manifest = _json(args.witness_manifest)
    require(run_manifest.get("schema") == SCHEMA and
            run_manifest.get("expected_calls") == 100 and
            run_manifest.get("arms") == list(ARMS), "observed run manifest differs")
    require(seal.get("schema") == SCHEMA and seal.get("status") == "pass" and
            seal.get("completed_calls") == 100, "observed seal is incomplete")
    require(seal.get("witness_manifest_sha256") == run_manifest.get("witness_manifest_sha256") and
            seal.get("source_bindings_sha256") == run_manifest.get("source_bindings_sha256"),
            "observed seal identity differs from run manifest")
    inventory = _inventory_files(run, seal)
    H, G, free, source_hashes = _validate_source_and_code(args, run_manifest,
                                                           witness_manifest)
    calls = build_calls(witness_manifest["entries"])
    ledger_path = run / "ledger.jsonl"
    require(sha256(ledger_path) == inventory.get("ledger.jsonl"),
            "ledger does not match the sealed inventory")
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    require(len(rows) == 100, "ledger does not contain exactly 100 calls")
    by_observation: dict[str, dict[str, dict[str, Any]]] = {}
    loaded_raw: dict[tuple[str, str], dict[str, Any]] = {}
    checkpoint_bits: dict[tuple[str, str], dict[int, np.ndarray]] = {}
    for index, ((entry, arm), row) in enumerate(zip(calls, rows), 1):
        obs_id = entry["observation_id"]
        require(row.get("status") == "ok" and row.get("call_index") == index and
                row.get("observation_id") == obs_id and row.get("role") == entry["role"] and
                row.get("arm") == arm, f"immutable call order differs at ledger row {index}")
        require(row.get("receiver_started") is True,
                f"receiver was not started for a sealed call {index}")
        obs_files = [f for f in entry["files"] if f.get("kind") == "observation"]
        require(len(obs_files) == 1, f"observation binding ambiguous for {obs_id}")
        obs_path = safe_path(args.witness_root, obs_files[0]["relative_path"])
        require(sha256(obs_path) == obs_files[0]["sha256"] == row.get("input_sha256"),
                f"input NPZ SHA differs for {obs_id}")
        require(row.get("triggered") == (row.get("baseline_syndrome_weight") != 0),
                f"trigger flag differs from baseline syndrome for {obs_id}/{arm}")
        require(row.get("final_syndrome_weight") >= 0 and
                row.get("final_syndrome_weight") == int(row["final_syndrome_weight"]),
                f"invalid final syndrome count for {obs_id}/{arm}")
        require(row.get("complete_latency_seconds", -1) >= 0 and
                row.get("final_decision_ready_seconds", math.inf) >= 0 and
                row["final_decision_ready_seconds"] <= row["complete_latency_seconds"],
                f"invalid final readiness/complete timing for {obs_id}/{arm}")
        triggered = bool(row["triggered"])
        require((row.get("branch_complete_seconds", -1) > 0) == triggered,
                f"branch completion charge differs from trigger for {obs_id}/{arm}")
        require(row.get("branch_elapsed_seconds", -1) >= 0,
                f"invalid branch elapsed time for {obs_id}/{arm}")
        raw_path = safe_path(run, row["raw_path"])
        require(sha256(raw_path) == row["raw_sha256"] ==
                inventory.get(str(raw_path.relative_to(run))),
                f"raw NPZ SHA differs for {obs_id}/{arm}")
        raw, raw_identity = load_artifact(raw_path,
            {"schema": SCHEMA, "observation_id": obs_id, "arm": arm})
        require(raw.get("observation_id") == obs_id and raw.get("arm") == arm and
                raw.get("input_sha256") == row["input_sha256"],
                f"raw payload identity differs for {obs_id}/{arm}")
        require(raw.get("trace_origin") ==
                "newly instrumented replay of frozen observed witness",
                f"trace origin differs for {obs_id}/{arm}")
        require(bool(raw.get("triggered")) == triggered and
                raw.get("numerical_failure") == row.get("numerical_failure"),
                f"raw trigger/failure fields differ for {obs_id}/{arm}")
        final_bits = _bits(raw["final_decoded"], f"{obs_id}/{arm}:final")
        final_syndrome = _syndrome(H, final_bits)
        require(final_syndrome == row["final_syndrome_weight"],
                f"final raw syndrome differs for {obs_id}/{arm}")
        require(hashlib.sha256(final_bits.tobytes()).hexdigest() ==
                row["final_decoded_sha256"],
                f"final decoded SHA differs for {obs_id}/{arm}")
        raw_cp = _load_decision_bits(run, row, H)
        require(len(row["checkpoints"]) == len(raw_cp),
                f"checkpoint count differs for {obs_id}/{arm}")
        require(row["baseline_syndrome_weight"] ==
                next(cp["syndrome_weight"] for cp in row["checkpoints"]
                     if cp["round"] == 1),
                f"baseline syndrome differs from native round 1 checkpoint for {obs_id}/{arm}")
        require(np.array_equal(raw_cp[0], raw["native_arrays"]["r0_decoded"]) and
                np.array_equal(raw_cp[1], raw["native_arrays"]["r1_decoded"]),
                f"native checkpoint prefix differs from raw arrays for {obs_id}/{arm}")
        require(np.array_equal(raw["native_decoder"]["decoded"], raw_cp[1]),
                f"native decoder output differs from round 1 for {obs_id}/{arm}")
        if row.get("branch_decision_seconds") is None:
            require(raw.get("branch_decoder") is None and 2 not in raw_cp,
                    f"missing-branch accounting differs for {obs_id}/{arm}")
            require(np.array_equal(final_bits, raw_cp[1]) and
                    row["final_decision_ready_seconds"] ==
                    next(cp["decision_ready_seconds"] for cp in row["checkpoints"]
                         if cp["round"] == 1),
                    f"fallback final decision/readiness differs from native round 1 for {obs_id}/{arm}")
        else:
            require(raw.get("branch_decoder") is not None and 2 in raw_cp and
                    np.array_equal(raw_cp[2], raw["branch_decoder"]["decoded"]),
                    f"saved branch checkpoint differs for {obs_id}/{arm}")
            require(np.array_equal(final_bits, raw_cp[2]) and
                    row["final_decision_ready_seconds"] ==
                    next(cp["decision_ready_seconds"] for cp in row["checkpoints"]
                         if cp["round"] == 2),
                    f"branch final decision/readiness differs for {obs_id}/{arm}")
            require(row["branch_complete_seconds"] >= row["branch_decision_seconds"],
                    f"branch serialized completion precedes branch decision for {obs_id}/{arm}")
        decision_rel = row.get("decision_path")
        decision_path = safe_path(run, decision_rel)
        require(sha256(decision_path) == row.get("decision_sha256") ==
                inventory.get(decision_rel), f"decision record SHA differs for {obs_id}/{arm}")
        decision = _json(decision_path)
        require(decision.get("schema") == SCHEMA and
                decision.get("observation_id") == obs_id and decision.get("arm") == arm and
                decision.get("input_sha256") == row["input_sha256"] and
                decision.get("triggered") == triggered and
                decision.get("numerical_failure") == row.get("numerical_failure") and
                decision.get("baseline_syndrome_weight") == row["baseline_syndrome_weight"] and
                decision.get("raw_path") == row["raw_path"] and
                decision.get("raw_sha256") == row["raw_sha256"] and
                decision.get("final_decoded_sha256") == row["final_decoded_sha256"] and
                decision.get("final_syndrome_weight") == row["final_syndrome_weight"] and
                decision.get("final_decision_ready_seconds") ==
                    row["final_decision_ready_seconds"] and
                decision.get("checkpoints") == row["checkpoints"] and
                decision.get("entering_sha256") == row.get("entering_sha256"),
                f"decision record disagrees with ledger/raw for {obs_id}/{arm}")
        entering = raw.get("entering")
        if entering is None:
            require(row.get("entering_sha256") is None and not triggered,
                    f"triggered call lacks refit entering state: {obs_id}/{arm}")
        else:
            computed = _hash_value(entering)
            require(computed == row.get("entering_sha256") == decision.get("entering_sha256"),
                    f"post-refit entering hash differs for {obs_id}/{arm}")
            require(set(entering) == {"app", "check", "ce_mu", "ce_variance",
                    "initial_delays", "initial_dopplers", "delays", "dopplers", "gains"},
                    f"post-refit entering fields differ for {obs_id}/{arm}")
            require(len(entering["delays"]) == len(entering["dopplers"]) ==
                    len(entering["gains"]), f"post-refit path slots differ for {obs_id}/{arm}")
        by_observation.setdefault(obs_id, {})[arm] = row
        loaded_raw[(obs_id, arm)] = raw
        checkpoint_bits[(obs_id, arm)] = raw_cp

    # The native two-round prefix and post-refit state must be bit-identical
    # across the four deliberately interleaved wrappers.
    prefix_checks = {"frames": 0, "round0_bit_mismatches": 0,
                     "round1_bit_mismatches": 0, "entering_mismatches": 0}
    distinct_frames = []
    for entry in witness_manifest["entries"]:
        obs_id = entry["observation_id"]
        raw_base = loaded_raw[(obs_id, "BASE")]
        base_cp = checkpoint_bits[(obs_id, "BASE")]
        base_entering = raw_base.get("entering")
        prefix_checks["frames"] += 1
        for arm in ARMS[1:]:
            raw_arm = loaded_raw[(obs_id, arm)]
            cp_arm = checkpoint_bits[(obs_id, arm)]
            same0 = np.array_equal(base_cp[0], cp_arm[0])
            same1 = np.array_equal(base_cp[1], cp_arm[1])
            prefix_checks["round0_bit_mismatches"] += int(not same0)
            prefix_checks["round1_bit_mismatches"] += int(not same1)
            require(same0 and same1,
                    f"first two native checkpoints differ: {obs_id} BASE/{arm}")
            # The complete native arrays are the independently saved prefix trace.
            equal, _ = _recursive_equal(raw_base["native_arrays"],
                                        raw_arm["native_arrays"])
            require(equal, f"native arrays differ across arms: {obs_id} BASE/{arm}")
            entering_arm = raw_arm.get("entering")
            equal_entering = ((base_entering is None and entering_arm is None) or
                              (base_entering is not None and entering_arm is not None and
                               _hash_value(base_entering) == _hash_value(entering_arm)))
            prefix_checks["entering_mismatches"] += int(not equal_entering)
            require(equal_entering,
                    f"post-refit entering states differ: {obs_id} BASE/{arm}")
        if base_entering is not None and len(set(np.asarray(base_entering["delays"]).tolist())) == len(base_entering["delays"]):
            distinct_frames.append(obs_id)

    # Keep these raw artifacts out of any truth-dependent operation.
    timing = {}
    numerical_failures = {}
    branch_counts = {}
    checkpoint_counts = {}
    for arm in ARMS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        require(len(arm_rows) == 25,
                f"arm {arm} does not have exactly 25 calls")
        checkpoint_counts[arm] = sum(len(row["checkpoints"]) for row in arm_rows)
        timing[arm] = {
            "complete_latency_seconds": _percentiles(
                [row["complete_latency_seconds"] for row in arm_rows]),
            "final_decision_ready_seconds": _percentiles(
                [row["final_decision_ready_seconds"] for row in arm_rows]),
            "branch_complete_seconds_all_calls": _percentiles(
                [row["branch_complete_seconds"] for row in arm_rows]),
            "branch_complete_seconds_triggered": _percentiles(
                [row["branch_complete_seconds"] for row in arm_rows if row["triggered"]]),
            "branch_decision_seconds_successful": _percentiles(
                [row["branch_decision_seconds"] for row in arm_rows
                 if row["branch_decision_seconds"] is not None]),
            "by_deadline": {
                str(deadline): sum(row["final_decision_ready_seconds"] <= deadline
                                   for row in arm_rows)
                for deadline in (0.5, 1.0)},
        }
        numerical_failures[arm] = sum(row.get("numerical_failure") is not None
                                      for row in arm_rows)
        branch_counts[arm] = {"triggered": sum(row["triggered"] for row in arm_rows),
                              "successful": sum(row.get("branch_decision_seconds") is not None
                                                for row in arm_rows)}
        require(numerical_failures[arm] == 0,
                f"unexpected numerical fallback in observed arm {arm}")
        require(branch_counts[arm]["successful"] == branch_counts[arm]["triggered"],
                f"a triggered call lacks a completed branch in observed arm {arm}")

    report = {
        "schema": "tf-cgr-independent-observed-verification/1",
        "status": "pass",
        "truth_values_read": False,
        "run_root": str(run),
        "observed_seal_sha256": sha256(seal_path),
        "sealed_files": len(inventory),
        "calls": len(rows),
        "source_file_hashes_verified": len(source_hashes),
        "code": {"H_shape": list(H.shape), "G_shape": list(G.shape),
                 "free_cols_count": int(len(free)),
                 "code_cache_file_sha256": source_hashes.get("code_cache"),
                 "H_array_sha256": hashlib.sha256(
                     np.ascontiguousarray(H).tobytes()).hexdigest(),
                 "G_array_sha256": hashlib.sha256(
                     np.ascontiguousarray(G).tobytes()).hexdigest(),
                 "free_cols_array_sha256": hashlib.sha256(
                     np.ascontiguousarray(free).tobytes()).hexdigest(),
                 "code_g_sha256": run_manifest["code_g_sha256"],
                 "H_G_GF2_zero": True, "free_cols_exact_systematic_identity": True},
        "prefix_identity": prefix_checks,
        "distinct_delay_entering_observations": distinct_frames,
        "trigger_and_branch_counts": branch_counts,
        "checkpoint_counts": checkpoint_counts,
        "checkpoint_total": sum(checkpoint_counts.values()),
        "numerical_fallbacks": numerical_failures,
        "timing": timing,
        "truth_gates": "not evaluated; requires committed-seal truth gate",
    }
    if args.truth_analysis:
        require(args.seal_commit,
                "truth analysis requires the main-session observed-seal commit")
        check_seal_commit(args.repo, args.seal_commit, args.seal_repo_path, seal_path)
        report["truth_analysis"] = analyze_truth(args, rows, loaded_raw,
                                                  checkpoint_bits, H, G, free,
                                                  witness_manifest)
        report["truth_values_read"] = True
        report["truth_gates"] = {
            "committed_seal_gate": "passed",
            "exact_bit_recount": "passed",
            "deadline_recount": "passed",
            "physical_diagnostic": ("not_evaluated_by_requested_scope"
                                    if args.skip_physical_diagnostic else "evaluated"),
        }
    out = args.out.resolve()
    require(not out.is_relative_to(run), "verification output must live outside sealed run")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return report


def check_seal_commit(repo: Path, commit: str, repo_path: str, local_seal: Path):
    """Require a real Git commit containing byte-identical observed seal."""
    resolved = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify",
                               f"{commit}^{{commit}}"], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True).stdout.strip()
    require(resolved == commit or len(commit) >= 7,
            "seal commit must resolve to a real commit object")
    blob = subprocess.run(["git", "-C", str(repo), "show", f"{resolved}:{repo_path}"],
                          check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout
    local = local_seal.read_bytes()
    require(hashlib.sha256(blob).digest() == hashlib.sha256(local).digest(),
            "committed Git seal bytes differ from local observed seal")
    subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                    resolved, "HEAD"], check=True, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)


def _truth_record(args, entry):
    match = [item for item in entry["files"] if item.get("kind") == "truth"]
    require(len(match) == 1, f"truth payload binding ambiguous: {entry['observation_id']}")
    path = safe_path(args.witness_root, match[0]["relative_path"])
    require(sha256(path) == match[0]["sha256"],
            f"truth payload SHA differs: {entry['observation_id']}")
    payload, identity = load_artifact(path)
    require(identity.get("kind") == "truth" and
            identity.get("schema") == "tf-cstate-prospective/1" and
            identity.get("observation_id") == entry["observation_id"] and
            identity.get("registration_sha256") == args.truth_registration_sha256,
            f"truth artifact identity differs: {entry['observation_id']}")
    return payload


def _qpsk_dense_matrix(n, c1, c2, delays, dopplers, gains):
    """Small independent dense action used only for the saved truth diagnostic."""
    indices = np.arange(n)
    basis = np.eye(n, dtype=np.complex128)

    def daft(x, inverse=False):
        phase1 = np.exp(2j * np.pi * c1 * indices * indices)
        phase2 = np.exp(2j * np.pi * c2 * indices * indices)
        if inverse:
            return phase1.conj()[:, None] * np.fft.ifft(
                phase2.conj()[:, None] * x, axis=0) * np.sqrt(n)
        return phase2[:, None] * np.fft.fft(phase1[:, None] * x,
                                             axis=0) / np.sqrt(n)

    time_basis = daft(basis, inverse=True)
    propagated = np.zeros((n, n), dtype=np.complex128)
    for delay, doppler, gain in zip(delays, dopplers, gains):
        shift = indices - int(delay)
        cp = np.where(shift < 0,
                      np.exp(2j * np.pi * c1 * (n * n + 2 * n * shift)), 1.0)
        phase = np.exp(2j * np.pi * indices * float(doppler) / n)
        propagated += complex(gain) * cp[:, None] * phase[:, None] * \
            time_basis[(shift % n), :]
    return daft(propagated)


def analyze_truth(args, rows, raw_by_key, checkpoints, H, G, free,
                  witness_manifest):
    """Truth-dependent exact decision recount and registered five gate counts."""
    truth_by_id = {}
    truth_keys = {}
    for entry in witness_manifest["entries"]:
        truth = _truth_record(args, entry)
        require(set(truth) >= {"coded", "info", "g_i", "l_i", "k_real"},
                f"truth payload keys differ: {entry['observation_id']}")
        coded = np.asarray(truth["coded"])
        info = np.asarray(truth["info"])
        require(coded.shape == (2048,) and info.shape == (1024,) and
                np.isin(coded, [0, 1]).all() and np.isin(info, [0, 1]).all(),
                f"truth bit dimensions differ: {entry['observation_id']}")
        coded, info = coded.astype(np.uint8), info.astype(np.uint8)
        require(np.array_equal(coded[free], info),
                f"truth information mapping differs: {entry['observation_id']}")
        encoded = ((G.astype(np.uint8) @ info.astype(np.uint8)) & 1).astype(np.uint8)
        require(np.array_equal(encoded, coded),
                f"truth coded word differs from exact frozen G encoding: {entry['observation_id']}")
        require(_syndrome(H, coded) == 0, f"truth coded word has nonzero syndrome: {entry['observation_id']}")
        truth_by_id[entry["observation_id"]] = dict(payload=truth, coded=coded, info=info,
            target=entry["role"] == "target_remaining_failure",
            rescued=entry["role"] == "matched_rescued_control",
            distinct_delay_specificity=entry["role"] == "distinct_delay_failure_specificity")
        truth_keys[entry["observation_id"]] = {
            "info_errors": {}, "coded_errors": {}, "valid_wrong": {},
            "syndrome_weight": {}, "correct_available_by_deadline": {},
        }

    correctness = {obs_id: {} for obs_id in truth_by_id}
    for row in rows:
        obs_id, arm = row["observation_id"], row["arm"]
        truth = truth_by_id[obs_id]
        raw = raw_by_key[(obs_id, arm)]
        final = _bits(raw["final_decoded"], f"truth recount {obs_id}/{arm}")
        syndrome = _syndrome(H, final)
        info_errors = int(np.count_nonzero(final[free] != truth["info"]))
        coded_errors = int(np.count_nonzero(final != truth["coded"]))
        # The locked outcome metric uses the exact information coordinates;
        # retain the full coded-word Hamming count as a separate field.
        valid_wrong = syndrome == 0 and info_errors > 0
        correct = info_errors == 0
        require(syndrome == row["final_syndrome_weight"],
                f"truth-gated final syndrome differs {obs_id}/{arm}")
        require(hashlib.sha256(final.tobytes()).hexdigest() == row["final_decoded_sha256"],
                f"truth-gated final bits differ {obs_id}/{arm}")
        correctness[obs_id][arm] = dict(correct=correct, info_errors=info_errors,
            coded_errors=coded_errors, syndrome=syndrome, valid_wrong=valid_wrong)
        deadlines = {}
        for threshold in (0.5, 1.0):
            eligible = [cp for cp in row["checkpoints"]
                        if cp["decision_ready_seconds"] <= threshold]
            chosen = eligible[-1] if eligible else None
            available = chosen is not None
            bits = (checkpoints[(obs_id, arm)][chosen["round"]]
                    if available else None)
            deadline_info_errors = (int(np.count_nonzero(bits[free] != truth["info"]))
                                    if available else None)
            deadline_correct = bool(available and deadline_info_errors == 0)
            deadlines[str(threshold)] = {
                "available": available,
                "correct": deadline_correct,
                "correct_available": deadline_correct,
                "info_errors": deadline_info_errors,
                "ready_seconds": None if chosen is None else chosen["decision_ready_seconds"],
                "round": None if chosen is None else chosen["round"],
            }
        truth_keys[obs_id]["info_errors"][arm] = info_errors
        truth_keys[obs_id]["coded_errors"][arm] = coded_errors
        truth_keys[obs_id]["valid_wrong"][arm] = valid_wrong
        truth_keys[obs_id]["syndrome_weight"][arm] = syndrome
        truth_keys[obs_id]["correct_available_by_deadline"][arm] = deadlines

    # Every unordered two-arm pair, over the complete 25-frame population.
    pairwise = {}
    for i, left in enumerate(ARMS):
        for right in ARMS[i + 1:]:
            rows4 = {"both_correct": 0, "left_only_correct": 0,
                     "right_only_correct": 0, "neither_correct": 0}
            for obs_id in correctness:
                a = correctness[obs_id][left]["correct"]
                b = correctness[obs_id][right]["correct"]
                rows4["both_correct"] += int(a and b)
                rows4["left_only_correct"] += int(a and not b)
                rows4["right_only_correct"] += int(b and not a)
                rows4["neither_correct"] += int(not a and not b)
            require(sum(rows4.values()) == 25, f"pairwise denominator differs {left}/{right}")
            pairwise[f"{left}__{right}"] = rows4

    targets = [key for key, value in truth_by_id.items() if value["target"]]
    rescued_controls = [key for key, value in truth_by_id.items() if value["rescued"]]
    target_cgr_rescues = sum(correctness[k]["CGR"]["correct"] and
                             not correctness[k]["BASE"]["correct"] for k in targets)
    target_cgr_losses = sum(correctness[k]["BASE"]["correct"] and
                            not correctness[k]["CGR"]["correct"] for k in targets)
    rescued_losses = sum(correctness[k]["BASE"]["correct"] and
                         not correctness[k]["CGR"]["correct"] for k in rescued_controls)
    new_valid_wrong = sum(correctness[k]["CGR"]["valid_wrong"] and
                          not correctness[k]["BASE"]["valid_wrong"]
                          for k in correctness)

    # Numerical identity on distinct-delay refit geometries. The continuous
    # arrays use the stated qualification tolerance; final bits remain exact.
    identity_rows = []
    for obs_id in sorted(raw_by_key[k]["observation_id"] for k in raw_by_key
                         if k[1] == "BASE"):
        b = raw_by_key[(obs_id, "BASE")]
        entering = b.get("entering")
        if entering is None or len(set(np.asarray(entering["delays"]).tolist())) != len(entering["delays"]):
            continue
        c = raw_by_key[(obs_id, "CGR")]
        eq, err = _recursive_equal(b.get("branch_detector"), c.get("branch_detector"),
                                   atol=1e-8, rtol=1e-8)
        bits_eq = np.array_equal(b["final_decoded"], c["final_decoded"])
        identity_rows.append({"observation_id": obs_id, "max_abs_error": err,
                              "detector_within_tolerance": eq,
                              "final_bits_equal": bool(bits_eq)})
    identity_failures = sum(not x["detector_within_tolerance"] or not x["final_bits_equal"]
                            for x in identity_rows)

    # Recompute the saved BASE common-state correction formula for every row;
    # dense physical mismatch is performed only for the final TF state of each
    # target, using the packet's truth path arrays after the seal gate.
    physical = {}
    for obs_id in (targets if not args.skip_physical_diagnostic else []):
        raw = raw_by_key[(obs_id, "BASE")]
        if raw.get("base_common_state") is None or raw.get("entering") is None:
            physical[obs_id] = {"status": "unavailable_no_base_trace"}
            continue
        entering = raw["entering"]
        delays = np.asarray(entering["delays"], dtype=int)
        dopplers = np.asarray(entering["dopplers"], dtype=float)
        state_rows = raw["base_common_state"]
        require(state_rows, f"BASE common-state trace empty: {obs_id}")
        last_delta = state_rows[-1]
        detector_states = raw["branch_detector"].get("states")
        require(detector_states and len(detector_states) == len(state_rows),
                f"BASE common-state and detector state counts differ: {obs_id}")
        state = detector_states[-1]
        gram = raw["gram"]
        R = np.asarray(gram["R"])
        hbar = np.asarray(state["hbar"])
        P = len(hbar)
        expected_dh = (-float(state["alpha"]) * len(entering["app"]) *
                       float(state["vx"]) /
                       (P + 1.0 / float(state["vq"]))) * ((R - np.eye(P)) @ hbar)
        saved_dh = np.asarray(last_delta["dh"])
        require(np.allclose(expected_dh, saved_dh, atol=1e-10, rtol=1e-10),
                f"saved common-state formula differs: {obs_id}")
        physical_norm = float(np.vdot(saved_dh, R @ saved_dh).real)
        require(np.isclose(physical_norm, last_delta["physical_norm_squared"],
                           atol=1e-9, rtol=1e-9),
                f"saved physical correction norm differs: {obs_id}")
        truth = truth_by_id[obs_id]["payload"]
        truth_gains = np.asarray(truth["g_i"], dtype=np.complex128)
        truth_delays = np.asarray(truth["l_i"], dtype=int)
        truth_dopplers = np.asarray(truth["k_real"], dtype=float)
        n = len(entering["app"]) // 2
        c1, c2 = args.physical_c1, args.physical_c2
        true_matrix = _qpsk_dense_matrix(n, c1, c2, truth_delays,
                                         truth_dopplers, truth_gains)
        base_h = np.asarray(state["h"])
        require(base_h.shape == saved_dh.shape and len(delays) == len(base_h),
                f"BASE physical state path slots differ: {obs_id}")
        base_matrix = _qpsk_dense_matrix(n, c1, c2, delays, dopplers, base_h)
        reacted_matrix = _qpsk_dense_matrix(n, c1, c2, delays, dopplers,
                                             base_h + saved_dh)
        base_error = float(np.linalg.norm(true_matrix - base_matrix, "fro") ** 2)
        reacted_error = float(np.linalg.norm(true_matrix - reacted_matrix, "fro") ** 2)
        physical[obs_id] = {
            "last_iteration": int(last_delta["iteration"]),
            "formula_max_abs_error": float(np.max(np.abs(expected_dh - saved_dh))),
            "physical_delta_norm_squared": physical_norm,
            "baseline_operator_error_squared": base_error,
            "reacted_operator_error_squared": reacted_error,
            "signed_physical_improvement": base_error - reacted_error,
        }

    gate3_net = sum(correctness[k]["CGR"]["correct"] for k in targets) - \
                sum(correctness[k]["SHAM"]["correct"] for k in targets)
    signed = [row["signed_physical_improvement"] for row in physical.values()
              if "signed_physical_improvement" in row]
    triggered_rows = {(row["observation_id"], row["arm"]): row for row in rows}
    base_branch = [triggered_rows[(k, "BASE")]["branch_complete_seconds"]
                   for k in correctness if triggered_rows[(k, "BASE")]["triggered"]]
    cgr_branch = [triggered_rows[(k, "CGR")]["branch_complete_seconds"]
                  for k in correctness if triggered_rows[(k, "CGR")]["triggered"]]
    branch_ratio = float(np.mean(cgr_branch) / np.mean(base_branch))
    block_net = sum(correctness[k]["BLOCK"]["correct"] for k in targets) - \
                sum(correctness[k]["CGR"]["correct"] for k in targets)
    full_population_correct = {
        arm: sum(correctness[obs_id][arm]["correct"] for obs_id in correctness)
        for arm in ARMS
    }

    five_gates = {
        "target_rescue_and_control_harm": {
            "target_cgr_rescues_vs_base": target_cgr_rescues,
            "target_cgr_losses_vs_base": target_cgr_losses,
            "already_rescued_control_losses": rescued_losses,
            "new_valid_but_wrong_outputs": new_valid_wrong,
            "pass": target_cgr_rescues >= 2 and rescued_losses == 0 and new_valid_wrong == 0,
        },
        "distinct_delay_identity": {
            "observations": len(identity_rows), "failures": identity_failures,
            "rows": identity_rows, "pass": bool(identity_rows) and identity_failures == 0,
        },
        "aligned_cgr_vs_sham_and_physical_direction": {
            "target_net_correct_advantage": int(gate3_net),
            "physical_targets_with_positive_signed_improvement": sum(x > 0 for x in signed),
            "physical_targets_with_nonpositive_signed_improvement": sum(x <= 0 for x in signed),
            "mean_signed_physical_improvement": float(np.mean(signed)) if signed else None,
            "physical_direction_supported": (None if args.skip_physical_diagnostic else
                bool(signed) and float(np.mean(signed)) > 0),
            "pass": (None if args.skip_physical_diagnostic else
                gate3_net >= 1 and bool(signed) and float(np.mean(signed)) > 0),
            "physical_check": ("skipped_by_requested_recount_scope"
                if args.skip_physical_diagnostic else "computed"),
        },
        "added_branch_mean_cost": {
            "base_triggered_mean_seconds": float(np.mean(base_branch)),
            "cgr_triggered_mean_seconds": float(np.mean(cgr_branch)),
            "cgr_to_base_ratio": branch_ratio,
            "max_allowed_ratio": 1.10,
            "pass": branch_ratio <= 1.10,
        },
        "block_outperformance_stop": {
            "block_net_correct_advantage_vs_cgr_targets": int(block_net),
            "candidate_claim_fails": block_net >= 2,
            "pass": block_net < 2,
        },
    }
    return {
        "truth_payloads_read_after_commit_gate": len(truth_by_id),
        "truth_codeword_encodings_verified": len(truth_by_id),
        "truth_registration_sha256": args.truth_registration_sha256,
        "decision_recounts": truth_keys,
        "pairwise_correctness_overlaps": pairwise,
        "deadline_correctness": {
            str(deadline): {
                arm: {
                    "n": 25,
                    "correct": sum(truth_keys[k]["correct_available_by_deadline"][arm]
                                   [str(deadline)]["correct"] for k in correctness),
                    "wrong_ready": sum(
                        truth_keys[k]["correct_available_by_deadline"][arm]
                        [str(deadline)]["available"] and not
                        truth_keys[k]["correct_available_by_deadline"][arm]
                        [str(deadline)]["correct"] for k in correctness),
                    "missing": sum(not truth_keys[k]["correct_available_by_deadline"][arm]
                                   [str(deadline)]["available"] for k in correctness),
                }
                for arm in ARMS
            }
            for deadline in (0.5, 1.0)
        },
        "target_and_control_correct_counts": {
            cohort: {arm: sum(correctness[k][arm]["correct"] for k in keys)
                     for arm in ARMS}
            for cohort, keys in {
                "target_remaining_failure": targets,
                "matched_rescued_control": rescued_controls,
                "matched_easy_control": [k for k, v in truth_by_id.items()
                                          if not v["target"] and not v["rescued"] and
                                          not v["distinct_delay_specificity"]],
                "distinct_delay_failure_specificity": [k for k, v in truth_by_id.items()
                                                       if v["distinct_delay_specificity"]],
            }.items()
        },
        "full_population_correct_counts": full_population_correct,
        "physical_common_state_diagnostic": (None if args.skip_physical_diagnostic
                                               else physical),
        "five_interpretation_gates": five_gates,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True,
                        help="complete observed run directory (contains observed_seal.json)")
    parser.add_argument("--witness-root", type=Path,
                        default=RESULTS / "witnesses")
    parser.add_argument("--witness-manifest", type=Path,
                        default=RESULTS / "witnesses/witness_manifest.json")
    parser.add_argument("--witness-receipt", type=Path,
                        default=RESULTS / "witness_receipt.json")
    parser.add_argument("--source-bindings", type=Path,
                        default=RESULTS / "qualification/source_bindings_v1.json")
    parser.add_argument("--registration", type=Path, default=RESULTS / "registration.json")
    parser.add_argument("--qualification", type=Path,
                        default=RESULTS / "qualification/local_v1/qualification.json")
    parser.add_argument("--source", type=Path,
                        default=EXP / "sp_afdm_native_joint_20260921")
    parser.add_argument("--baseline", type=Path,
                        default=EXP / "sp_afdm_frozen_20260920")
    parser.add_argument("--geometry", type=Path,
                        default=EXP / "tf_cstate_validation_20260922")
    parser.add_argument("--producer", type=Path,
                        default=EXP / "tf_cgr_mechanism_20260923_v2")
    parser.add_argument("--code-cache", type=Path, default=EXP /
        "sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/"
        "afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    parser.add_argument("--out", type=Path,
                        default=INDEPENDENT / "v2_observed_verification.json")
    parser.add_argument("--truth-analysis", action="store_true",
                        help="read truth only after verifying the real seal commit")
    parser.add_argument("--repo", type=Path, default=ROOT,
                        help="Git repository used for seal object attestation")
    parser.add_argument("--seal-commit", help="commit that contains the exact observed seal")
    parser.add_argument("--seal-repo-path", default=None,
                        help="repo-relative seal path; defaults from --run")
    parser.add_argument("--truth-registration-sha256", default=None,
                        help="prospective source-registration SHA from each truth identity")
    parser.add_argument("--physical-c1", type=float, default=None,
                        help="exact c1 from the frozen receiver context, supplied after seal")
    parser.add_argument("--physical-c2", type=float, default=None,
                        help="exact c2 from the frozen receiver context, supplied after seal")
    parser.add_argument("--skip-physical-diagnostic", action="store_true",
                        help="recount exact truth bits/deadlines without adding an operator diagnostic")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.truth_analysis:
        require(args.seal_commit is not None,
                "truth analysis requires --seal-commit from the main session")
        require(args.truth_registration_sha256 is not None and
                len(args.truth_registration_sha256) == 64,
                "truth analysis requires the truth producer registration SHA")
        if not args.skip_physical_diagnostic:
            require(args.physical_c1 is not None and args.physical_c2 is not None,
                    "truth physical diagnostic requires exact frozen-context c1/c2 values")
        if args.seal_repo_path is None:
            args.seal_repo_path = str(args.run.resolve().relative_to(args.repo.resolve()) /
                                      "observed_seal.json")
    report = verify_observed(args)
    print(json.dumps({"status": report["status"],
                      "truth_values_read": report["truth_values_read"],
                      "calls": report["calls"],
                      "seal_sha256": report["observed_seal_sha256"],
                      "output": str(args.out.resolve())}, sort_keys=True))


if __name__ == "__main__":
    main()
