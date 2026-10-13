"""Independent saved-output recount for the matched Stage-B F1 comparison.

This reader imports no receiver, decoder, generator, producer, or primary
analysis module. Truth is opened only when the caller supplies the explicit
post-freeze gate and a committed-seal attestation.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np


SCHEMA = "cstate-necessity-stage-b-f1/1"
ATTESTATION_SCHEMA = "cstate-necessity-stage-b-f1/git-attestation/1"
SOURCE_NAMES = ("f1_fast.py", "f1_fast_native.py", "f1_run_stage_b.py",
                "f1_launch_once.sh")
N_FRAMES = 1024
EXPECTED_CALLS = 2112
EVIDENCE_METADATA = "__evidence_metadata__"
ARRAY_SENTINEL = "__evidence_array__"
TUPLE_SENTINEL = "__evidence_tuple__"
REFERENCE_FIELDS = (
    "delays", "dopplers", "gains", "bank_centers", "stopping_reason",
    "objective_history", "counters", "pilot_energy", "last_coordinate_gain",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"non-object JSONL row {line_no}: {path}")
        rows.append(row)
    return rows


def _safe_child(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    base = root.resolve()
    if candidate == base or base not in candidate.parents:
        raise ValueError(f"sealed path escapes its root: {relative}")
    return candidate


def _verify_seal(root: Path, seal_name: str, schema: str) -> tuple[dict[str, Any], dict[str, str]]:
    seal_path = root / seal_name
    seal = _json(seal_path)
    if seal.get("schema") != schema or seal.get("status") != "pass":
        raise ValueError(f"{seal_name} schema/status differs")
    files = seal.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"{seal_name} has no sealed inventory")
    actual = {str(p.relative_to(root)) for p in root.rglob("*")
              if p.is_file() and p.name != seal_name}
    if actual != set(files):
        raise ValueError(f"{seal_name} inventory names differ")
    for relative, expected in files.items():
        if sha256(_safe_child(root, relative)) != expected:
            raise ValueError(f"sealed SHA differs: {relative}")
    return seal, files


def _references(tree: Any) -> set[str]:
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            key = tree[ARRAY_SENTINEL]
            if not isinstance(key, str):
                raise ValueError("invalid array reference")
            return {key}
        if set(tree) == {TUPLE_SENTINEL}:
            return _references(tree[TUPLE_SENTINEL])
        refs: set[str] = set()
        for value in tree.values():
            refs.update(_references(value))
        return refs
    if isinstance(tree, list):
        refs: set[str] = set()
        for value in tree:
            refs.update(_references(value))
        return refs
    return set()


def _unpack(tree: Any, arrays: dict[str, np.ndarray]) -> Any:
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            return arrays[tree[ARRAY_SENTINEL]]
        if set(tree) == {TUPLE_SENTINEL}:
            return tuple(_unpack(value, arrays) for value in tree[TUPLE_SENTINEL])
        return {key: _unpack(value, arrays) for key, value in tree.items()}
    if isinstance(tree, list):
        return [_unpack(value, arrays) for value in tree]
    return tree


def read_artifact(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    with np.load(path, allow_pickle=False) as archive:
        if EVIDENCE_METADATA not in archive.files:
            raise ValueError(f"evidence metadata absent: {path}")
        metadata = np.asarray(archive[EVIDENCE_METADATA])
        if metadata.dtype != np.uint8 or metadata.ndim != 1:
            raise ValueError(f"invalid evidence metadata: {path}")
        envelope = json.loads(metadata.tobytes().decode("utf-8"))
        if envelope.get("format_version") != 2:
            raise ValueError(f"unsupported evidence format: {path}")
        tree = envelope.get("payload")
        refs = _references(tree)
        if refs != set(archive.files) - {EVIDENCE_METADATA}:
            raise ValueError(f"evidence array inventory differs: {path}")
        arrays = {key: np.asarray(archive[key]) for key in refs}
    payload = _unpack(tree, arrays)
    identity = envelope.get("identity")
    if not isinstance(payload, dict) or not isinstance(identity, dict):
        raise ValueError(f"invalid evidence envelope: {path}")
    return payload, identity


def _bits(value: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(value)
    if arr.shape != (size,) or arr.dtype.kind not in "biu" or not np.isin(arr, (0, 1)).all():
        raise ValueError(f"{label} is not a binary vector of length {size}")
    return arr.astype(np.uint8, copy=False)


def _syndrome_weight(H: np.ndarray, bits: np.ndarray) -> int:
    return int(np.count_nonzero((H.astype(np.int64) @ bits.astype(np.int64)) % 2))


def _deep_compare(left: Any, right: Any, *, atol: float = 2e-10, path: str = "") -> float:
    """Exact structure/dtype/category and bits; numeric values use atol, rtol=0."""
    if isinstance(left, dict):
        if not isinstance(right, dict) or set(left) != set(right):
            raise ValueError(f"mapping keys differ at {path}")
        return max((_deep_compare(left[key], right[key], atol=atol,
                                  path=f"{path}/{key}") for key in left), default=0.0)
    if isinstance(left, (tuple, list)):
        if not isinstance(right, type(left)) or len(left) != len(right):
            raise ValueError(f"sequence differs at {path}")
        return max((_deep_compare(a, b, atol=atol, path=f"{path}/{i}")
                    for i, (a, b) in enumerate(zip(left, right))), default=0.0)
    if isinstance(left, np.ndarray):
        a, b = np.asarray(left), np.asarray(right)
        if a.shape != b.shape or a.dtype != b.dtype:
            raise ValueError(f"array shape/dtype differs at {path}")
        if a.dtype.kind in "biuSU":
            if not np.array_equal(a, b):
                raise ValueError(f"exact array differs at {path}")
            return 0.0
        if not np.issubdtype(a.dtype, np.number) or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError(f"nonfinite/nonnumeric array at {path}")
        delta = float(np.max(np.abs(a - b))) if a.size else 0.0
        if delta > atol:
            raise ValueError(f"numeric array differs at {path}: {delta}")
        return delta
    if isinstance(left, (int, float, complex, np.number)) and not isinstance(left, bool):
        if not np.isclose(left, right, atol=atol, rtol=0):
            raise ValueError(f"numeric scalar differs at {path}")
        return float(abs(left - right))
    if left != right:
        raise ValueError(f"value differs at {path}")
    return 0.0


def _attest(observed_root: Path, manifest: dict[str, Any], seal: dict[str, Any],
            registration: dict[str, Any], attestation_path: Path,
            observed_commit: str, git_repo: Path | None) -> dict[str, Any]:
    att = _json(attestation_path)
    seal_bytes = (observed_root / "observed_seal.json").read_bytes()
    seal_sha = hashlib.sha256(seal_bytes).hexdigest()
    blob_oid = hashlib.sha1(f"blob {len(seal_bytes)}\0".encode() + seal_bytes).hexdigest()
    relative = att.get("seal_repo_path")
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("invalid attested seal path")
    expected = {
        "schema": ATTESTATION_SCHEMA,
        "registration_commit": manifest.get("registration_commit"),
        "observed_commit": observed_commit,
        "seal_sha256": seal_sha,
        "git_blob_sha256": seal_sha,
        "git_blob_oid": blob_oid,
        "git_blob_size_bytes": len(seal_bytes),
        "registration_sha256": sha256(registration["_path"]),
        "merge_base_is_ancestor": True,
        "checked_by": "local_git_show_and_merge_base",
    }
    if any(att.get(key) != value for key, value in expected.items()):
        raise ValueError("Git attestation differs from registration/observed seal")
    if seal.get("registration_sha256") != expected["registration_sha256"]:
        raise ValueError("seal/registration SHA differs")
    if git_repo is not None:
        shown = subprocess.run(["git", "-C", str(git_repo), "show",
                                f"{observed_commit}:{relative}"],
                               capture_output=True, check=False)
        if shown.returncode or shown.stdout != seal_bytes:
            raise ValueError("git show does not return the local observed seal bytes")
        ancestry = subprocess.run(["git", "-C", str(git_repo), "merge-base",
                                   "--is-ancestor", str(manifest["registration_commit"]),
                                   observed_commit], capture_output=True, check=False)
        if ancestry.returncode:
            raise ValueError("observed commit is not descended from registration commit")
    return {"attestation_sha256": sha256(attestation_path),
            "attestation_schema": att["schema"], "seal_repo_path": relative,
            "observed_commit": observed_commit,
            "direct_git_object_check": git_repo is not None}


def _schedule(frame: int) -> tuple[str, ...]:
    if frame % 16 == 0:
        permutations = tuple(itertools.permutations(("B", "Cref", "Cfast")))
        return permutations[(frame // 16) % len(permutations)]
    ordinal = frame - 1 - frame // 16
    return ("B", "Cfast") if ordinal % 2 == 0 else ("Cfast", "B")


def _load_population(population_root: Path, expected_seal_sha: str) -> dict[str, dict[str, Any]]:
    seal_path = population_root / "observed_seal.json"
    if sha256(seal_path) != expected_seal_sha:
        raise ValueError("population observed seal SHA differs from Stage-B manifest")
    seal = _json(seal_path)
    if seal.get("status") != "pass" or seal.get("files", {}).get("ledger.jsonl") != sha256(population_root / "ledger.jsonl"):
        raise ValueError("population observed ledger is not seal-bound")
    rows = [row for row in _jsonl(population_root / "ledger.jsonl")
            if row.get("snr_centi_db") == 650]
    if len(rows) != N_FRAMES or [row.get("frame") for row in rows] != list(range(N_FRAMES)):
        raise ValueError("population is not the registered 6.5 dB 1,024-frame cohort")
    by_id = {row["observation_id"]: row for row in rows}
    if len(by_id) != N_FRAMES:
        raise ValueError("duplicate population observation IDs")
    return by_id


def _load_truth(truth_root: Path, frame_ids: set[str],
                expected_seal_sha: str | None) -> dict[str, tuple[np.ndarray, np.ndarray, str, list[int]]]:
    seal_path = truth_root / "truth_seal.json"
    if expected_seal_sha and sha256(seal_path) != expected_seal_sha:
        raise ValueError("truth seal SHA differs from registered population")
    seal, files = _verify_seal(truth_root, "truth_seal.json", "tf-cstate-prospective/1")
    ledger = _jsonl(truth_root / "ledger.jsonl")
    rows = {row["observation_id"]: row for row in ledger if row.get("snr_centi_db") == 650}
    if set(rows) != frame_ids:
        raise ValueError("truth ledger IDs differ from the observed cohort")
    result = {}
    for stem in sorted(frame_ids):
        row = rows[stem]
        rel = row["truth_path"]
        if files.get(rel) != row["truth_sha256"]:
            raise ValueError(f"truth ledger/seal hash differs: {stem}")
        payload, identity = read_artifact(_safe_child(truth_root, rel))
        if identity.get("observation_id") != stem or identity.get("kind") != "truth":
            raise ValueError(f"truth artifact identity differs: {stem}")
        if (row.get("observation_hash") != payload.get("observation_hash")
                or row.get("stream_ids") != payload.get("stream_ids")):
            raise ValueError(f"truth ledger/payload identity differs: {stem}")
        result[stem] = (_bits(payload["info"], 1024, f"{stem} truth info"),
                        _bits(payload["coded"], 2048, f"{stem} truth coded"),
                        str(payload["observation_hash"]), list(payload["stream_ids"]))
    return result


def _latest_checkpoint(checkpoints: list[dict[str, Any]], deadline: float,
                       truth_info: np.ndarray, free_cols: np.ndarray) -> dict[str, Any]:
    ready = [cp for cp in checkpoints if cp["ready_seconds"] <= deadline]
    if not ready:
        return {"ready": False, "correct": False, "round": None}
    cp = max(ready, key=lambda item: (item["ready_seconds"], item["round"]))
    return {"ready": True,
            "correct": bool(np.array_equal(cp["decoded"][free_cols], truth_info)),
            "round": cp["round"]}


def _summary(values: list[float]) -> dict[str, Any]:
    data = np.asarray(values, dtype=np.float64)
    if not data.size or not np.isfinite(data).all() or np.any(data < 0):
        raise ValueError("invalid timing sample")
    return {"n": int(data.size), "mean": float(data.mean()),
            "p95": float(np.quantile(data, .95)), "max": float(data.max())}


def recount_failed_attempt(args: argparse.Namespace) -> dict[str, Any]:
    """Count/hash only the partial-run receipts; never inspect truth or payloads."""
    root = args.observed_root
    file_hashes = {}
    for name in ("manifest.json", "attempts.jsonl", "ledger.jsonl",
                 "invalid_partial.json", "observed_seal.json"):
        path = root / name
        if path.is_file():
            file_hashes[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    if not {"manifest.json", "attempts.jsonl", "ledger.jsonl"} <= set(file_hashes):
        raise ValueError("partial-run small receipts are incomplete")
    manifest = _json(root / "manifest.json")
    attempts = _jsonl(root / "attempts.jsonl")
    ledger = _jsonl(root / "ledger.jsonl")
    status_counts: dict[str, int] = {}
    for row in ledger:
        status = str(row.get("status", "missing"))
        status_counts[status] = status_counts.get(status, 0) + 1
    attempt_indices = [row.get("attempt_index") for row in attempts]
    sequential = attempt_indices == list(range(1, len(attempts) + 1))
    ledger_by_index = {row.get("attempt_index"): row for row in ledger}
    identity_mismatches = []
    unpaired_attempt_indices = []
    for attempt in attempts:
        index = attempt.get("attempt_index")
        row = ledger_by_index.get(index)
        if row is None:
            unpaired_attempt_indices.append(index)
        if row is not None and any(attempt.get(key) != row.get(key) for key in
                                   ("attempt_index", "observation_id", "arm", "input_sha256")):
            identity_mismatches.append(index)
    failed_rows = [row for row in ledger if row.get("status") == "failed"]
    inflight_rows = [row for row in ledger if row.get("status") == "inflight"]
    last_attempt = attempts[-1] if attempts else None
    last_failed = failed_rows[-1] if failed_rows else None
    return {
        "schema": "cstate-necessity-stage-b-f1-failure-recount/1",
        "status": "partial_failure_only",
        "scope": "small manifest/attempt/ledger/failure/seal receipts only; no truth or NPZ payloads opened",
        "manifest_schema": manifest.get("schema"),
        "manifest_status": manifest.get("status"),
        "expected_calls": manifest.get("expected_calls"),
        "started_attempts": len(attempts),
        "ledger_rows": len(ledger),
        "ledger_status_counts": status_counts,
        "successful_ledger_rows": status_counts.get("ok", 0),
        "failed_rows": len(failed_rows),
        "inflight_rows": len(inflight_rows),
        "attempt_indices_sequential": sequential,
        "attempt_ledger_identity_mismatches": identity_mismatches,
        "attempts_without_ledger_rows": unpaired_attempt_indices,
        "last_attempt": None if last_attempt is None else {
            key: last_attempt.get(key) for key in
            ("attempt_index", "observation_id", "arm", "input_sha256")},
        "last_failed": None if last_failed is None else {
            key: last_failed.get(key) for key in
            ("attempt_index", "observation_id", "arm", "input_sha256", "error")},
        "observed_seal_present": "observed_seal.json" in file_hashes,
        "small_file_hashes": file_hashes,
        "truth_payloads_opened": 0,
        "raw_checkpoint_decision_payloads_opened": 0,
        "complete_cohort_error_or_latency_claims": False,
        "limitations": ["No BER/FER, pairing, checkpoint, or timing metrics are produced from a partial run."]
    }


def recount(args: argparse.Namespace) -> dict[str, Any]:
    observed = args.observed_root
    if (observed / "invalid_partial.json").exists():
        raise ValueError("invalid_partial marker forbids a complete cohort recount")
    seal, sealed_files = _verify_seal(observed, "observed_seal.json", SCHEMA)
    if (seal.get("observations") != N_FRAMES or seal.get("calls") != EXPECTED_CALLS
            or seal.get("attempts") != EXPECTED_CALLS or seal.get("reference_subset_calls") != 64):
        raise ValueError("Stage-B seal allocation differs")
    manifest = _json(observed / "manifest.json")
    registration = _json(args.registration)
    registration["_path"] = args.registration
    if (registration.get("schema") != SCHEMA or registration.get("status") != "locked"
            or registration.get("expected_calls") != EXPECTED_CALLS
            or set(registration.get("source_hashes", {})) != set(SOURCE_NAMES)
            or sha256(args.registration) != manifest.get("registration_sha256")
            or manifest.get("registration_sha256") != seal.get("registration_sha256")
            or manifest.get("stage_a_registration_sha256") != sha256(args.stage_a_registration)):
        raise ValueError("Stage-B manifest/registration binding differs")
    stage_a_reg = _json(args.stage_a_registration)
    if (registration.get("stage_a_registration_sha256") != sha256(args.stage_a_registration)
            or registration.get("stage_a_observed_seal_sha256") !=
                sha256(args.stage_a_observed_root / "observed_seal.json")
            or registration.get("population_observed_seal_sha256") !=
                sha256(args.population_observed_root / "observed_seal.json")
            or manifest.get("protocol_sha256") != registration.get("protocol_sha256")
            or manifest.get("stage_a_source_hashes") != stage_a_reg.get("source_hashes")):
        raise ValueError("Stage-B protocol/population/Stage-A registration binding differs")
    if stage_a_reg.get("ldpc_cache_sha256") != sha256(args.code_cache):
        raise ValueError("LDPC cache SHA differs from Stage-A registration")
    if manifest.get("source_hashes") != registration.get("source_hashes"):
        raise ValueError("manifest source hashes differ from locked registration")
    for name, digest in registration.get("source_hashes", {}).items():
        if sha256(_safe_child(args.source_root, name)) != digest:
            raise ValueError(f"registered source SHA differs: {name}")
    git_record = _attest(observed, manifest, seal, registration,
                         args.git_attestation, args.observed_commit, args.git_repo)

    stage_a_root = args.stage_a_observed_root
    stage_a_seal = _json(stage_a_root / "observed_seal.json")
    if (stage_a_seal.get("status") != "pass"
            or sha256(stage_a_root / "observed_seal.json") != manifest.get("stage_a_observed_seal_sha256")):
        raise ValueError("Stage-A reference seal is not pass")
    stage_a_ledger = _jsonl(stage_a_root / "ledger.jsonl")
    old = {}
    for row in stage_a_ledger:
        if row.get("arm") in ("B", "C"):
            key = (row["observation_id"], row["arm"])
            if (key in old or row.get("status") != "ok"
                    or stage_a_seal.get("files", {}).get(row["raw_path"]) != row["raw_sha256"]):
                raise ValueError(f"Stage-A reference row/hash differs: {key}")
            old[key] = row
    if len(old) != 2 * N_FRAMES:
        raise ValueError("Stage-A B/C reference count differs")

    population = _load_population(args.population_observed_root,
                                  manifest["population_observed_seal_sha256"])
    expected = []
    for frame, stem in enumerate(population):
        input_row = population[stem]
        for arm in _schedule(frame):
            expected.append((frame, stem, arm, input_row))
    if len(expected) != EXPECTED_CALLS:
        raise AssertionError("internal registered schedule count differs")

    attempts = _jsonl(observed / "attempts.jsonl")
    ledger = _jsonl(observed / "ledger.jsonl")
    if len(attempts) != EXPECTED_CALLS or len(ledger) != EXPECTED_CALLS:
        raise ValueError("attempt/ledger row count differs from allocation")
    for i, ((frame, stem, arm, input_row), attempt, row) in enumerate(
            zip(expected, attempts, ledger, strict=True), 1):
        identity = (i, stem, arm, input_row["observation_sha256"])
        if (attempt.get("attempt_index"), attempt.get("observation_id"),
                attempt.get("arm"), attempt.get("input_sha256")) != identity:
            raise ValueError(f"attempt sequence/source differs at {i}")
        if (row.get("status"), row.get("attempt_index"), row.get("frame"),
                row.get("observation_id"), row.get("arm"), row.get("input_sha256")) != (
                "ok", i, frame, stem, arm, input_row["observation_sha256"]):
            raise ValueError(f"ledger sequence/source differs at {i}")

    with np.load(args.code_cache, allow_pickle=False) as code:
        H = np.asarray(code["H"], dtype=np.uint8)
        free_cols = np.asarray(code["free_cols"], dtype=np.int64)
    if H.shape != (1026, 2048) or free_cols.shape != (1024,) or len(np.unique(free_cols)) != 1024 or np.any((free_cols < 0) | (free_cols >= 2048)):
        raise ValueError("code cache H/free_cols shape or range differs")
    truths = _load_truth(args.truth_root, set(population),
                         stage_a_reg.get("population_truth_seal_sha256"))
    for stem, (info, coded, truth_observation_hash, truth_stream_ids) in truths.items():
        if not np.array_equal(coded[free_cols], info) or _syndrome_weight(H, coded) != 0:
            raise ValueError(f"truth coded/info/H consistency differs: {stem}")
        source = population[stem]
        if (truth_observation_hash != source.get("observation_hash")
                or truth_stream_ids != source.get("stream_ids")):
            raise ValueError(f"truth/population semantic identity differs: {stem}")

    counts = {arm: {"frames": 0, "info_errors": 0, "info_bit_errors": 0,
                    "native_r1_syndrome_nonzero": 0, "branch_triggers": 0,
                    "final_syndrome_weight_sum": 0,
                    "rescued_vs_r1": 0, "harmed_vs_r1": 0}
              for arm in ("B", "Cfast", "Cref")}
    timing = {arm: {"acquisition": [], "complete": []}
              for arm in ("B", "Cfast", "Cref")}
    deadlines = {arm: {str(d): {"correct": 0, "missing": 0, "wrong_or_missing": 0}
                       for d in (.5, 1.0)} for arm in counts}
    outputs: dict[tuple[str, str], dict[str, Any]] = {}
    reference_checks = {"B": 0, "Cfast": 0, "Cref": 0}
    max_reference_delta = {"Cfast": 0.0, "Cref": 0.0}

    for (frame, stem, arm, input_row), attempt, row in zip(expected, attempts, ledger, strict=True):
        raw_rel, dec_rel = row["raw_path"], row["decision_path"]
        raw_path = _safe_child(observed, raw_rel)
        decision_path = _safe_child(observed, dec_rel)
        if (sealed_files.get(raw_rel) != row.get("raw_sha256")
                or sha256(raw_path) != row.get("raw_sha256")
                or sealed_files.get(dec_rel) != row.get("decision_sha256")
                or sha256(decision_path) != row.get("decision_sha256")):
            raise ValueError(f"raw/decision SHA differs: {stem} {arm}")
        raw, raw_id = read_artifact(raw_path)
        decision = _json(decision_path)
        if (raw_id.get("schema"), raw_id.get("observation_id"), raw_id.get("arm"), raw_id.get("input_sha256")) != (SCHEMA, stem, arm, input_row["observation_sha256"]):
            raise ValueError(f"raw identity differs: {stem} {arm}")
        if (decision.get("observation_id"), decision.get("arm"), decision.get("input_sha256"),
                decision.get("raw_path"), decision.get("raw_sha256")) != (
                stem, arm, input_row["observation_sha256"], raw_rel, row["raw_sha256"]):
            raise ValueError(f"decision identity differs: {stem} {arm}")
        if (raw.get("input_sha256") != input_row["observation_sha256"]
                or raw.get("stream_ids") != input_row["stream_ids"]
                or row.get("observation_hash") != input_row["observation_hash"]
                or row.get("stream_ids") != input_row["stream_ids"]):
            raise ValueError(f"raw source identity differs: {stem} {arm}")

        final_bits = _bits(raw["final_decoded"], 2048, f"{stem} {arm} final bits")
        final_info = _bits(raw["final_info"], 1024, f"{stem} {arm} final info")
        if not np.array_equal(final_info, final_bits[free_cols]):
            raise ValueError(f"final info differs from free coordinates: {stem} {arm}")
        if not np.array_equal(_bits(decision["final_decoded"], 2048, "decision bits"), final_bits) or not np.array_equal(_bits(decision["final_info"], 1024, "decision info"), final_info):
            raise ValueError(f"raw/decision final bits differ: {stem} {arm}")
        bits_sha = hashlib.sha256(final_bits.tobytes()).hexdigest()
        if bits_sha != row.get("final_decoded_sha256") or bits_sha != decision.get("final_decoded_sha256"):
            raise ValueError(f"final bits hash differs: {stem} {arm}")

        computed_base_syndrome = _syndrome_weight(H, _bits(raw["baseline_arrays"]["r1_decoded"], 2048, "native r1"))
        final_syndrome = _syndrome_weight(H, final_bits)
        triggered = bool(arm == "B" and computed_base_syndrome != 0)
        if (row.get("triggered") != triggered or decision.get("triggered") != triggered
                or raw.get("triggered") != triggered
                or int(row["baseline_syndrome_weight"]) != computed_base_syndrome
                or int(row["final_syndrome_weight"]) != final_syndrome
                or int(decision["final_syndrome_weight"]) != final_syndrome):
            raise ValueError(f"trigger/syndrome differs: {stem} {arm}")

        cp_rows = row.get("checkpoints", [])
        expected_rounds = [0, 1, 2] if triggered else [0, 1]
        if [cp.get("round") for cp in cp_rows] != expected_rounds or decision.get("checkpoints") != cp_rows:
            raise ValueError(f"checkpoint sequence differs: {stem} {arm}")
        checkpoints = []
        for cp in cp_rows:
            cp_path = _safe_child(observed, cp["path"])
            if sealed_files.get(cp["path"]) != cp.get("artifact_sha256") or sha256(cp_path) != cp.get("artifact_sha256"):
                raise ValueError(f"checkpoint SHA differs: {stem} {arm} r{cp['round']}")
            cp_payload, cp_id = read_artifact(cp_path)
            if (cp_id.get("schema"), cp_id.get("observation_id"), cp_id.get("arm"), cp_id.get("round"), cp_id.get("input_sha256")) != (SCHEMA, stem, arm, cp["round"], input_row["observation_sha256"]):
                raise ValueError(f"checkpoint identity differs: {stem} {arm}")
            decoded = _bits(cp_payload["decoded"], 2048, "checkpoint decoded")
            if int(cp["round"]) in (0, 1):
                baseline_key = f"r{cp['round']}_decoded"
                if not np.array_equal(decoded, _bits(raw["baseline_arrays"][baseline_key], 2048, baseline_key)):
                    raise ValueError(f"native checkpoint differs from raw: {stem} {arm}")
            elif not np.array_equal(decoded, final_bits):
                raise ValueError(f"branch checkpoint differs from final bits: {stem}")
            event = cp_payload["event"]
            decision_ready, ready = float(cp["decision_ready_seconds"]), float(cp["ready_seconds"])
            event_ready = float(event["ready"])
            if not (0 <= event_ready <= decision_ready <= ready) or not np.isfinite([event_ready, decision_ready, ready]).all():
                raise ValueError(f"checkpoint time ordering invalid: {stem} {arm}")
            cp_syndrome = _syndrome_weight(H, decoded)
            if cp_syndrome != int(cp["syndrome_weight"]):
                raise ValueError(f"checkpoint syndrome differs: {stem} {arm}")
            checkpoints.append({"round": int(cp["round"]), "ready_seconds": ready,
                                "decoded": decoded})
        if (not np.array_equal(checkpoints[-1]["decoded"], final_bits)
                or bool(raw.get("triggered")) != triggered):
            raise ValueError(f"last durable checkpoint does not resolve to final decision: {stem} {arm}")
        cp_ready = [cp["ready_seconds"] for cp in checkpoints]
        complete_latency = float(row["complete_latency_seconds"])
        if cp_ready != sorted(cp_ready) or cp_ready[-1] > complete_latency:
            raise ValueError(f"checkpoint-ready/complete timing order differs: {stem} {arm}")

        truth_info, _, truth_observation_hash, truth_stream_ids = truths[stem]
        if (truth_observation_hash != row.get("observation_hash")
                or truth_stream_ids != row.get("stream_ids")):
            raise ValueError(f"truth/observed row identity differs: {stem} {arm}")
        bit_errors = int(np.count_nonzero(final_info != truth_info))
        final_correct = bit_errors == 0
        r1_correct = bool(np.array_equal(checkpoints[1]["decoded"][free_cols], truth_info))
        key_arm = arm
        counts[key_arm]["frames"] += 1
        counts[key_arm]["info_errors"] += int(not final_correct)
        counts[key_arm]["info_bit_errors"] += bit_errors
        counts[key_arm]["native_r1_syndrome_nonzero"] += int(computed_base_syndrome != 0)
        counts[key_arm]["branch_triggers"] += int(triggered)
        counts[key_arm]["final_syndrome_weight_sum"] += final_syndrome
        counts[key_arm]["rescued_vs_r1"] += int(not r1_correct and final_correct)
        counts[key_arm]["harmed_vs_r1"] += int(r1_correct and not final_correct)
        for deadline in (.5, 1.0):
            result = _latest_checkpoint(checkpoints, deadline, truth_info, free_cols)
            out = deadlines[arm][str(deadline)]
            out["correct"] += int(result["ready"] and result["correct"])
            out["missing"] += int(not result["ready"])
            out["wrong_or_missing"] += int(not result["correct"])
        timing[arm]["complete"].append(float(row["complete_latency_seconds"]))
        timing[arm]["acquisition"].append(float(row["acquisition_seconds"]))
        if not (row.get("ledger_append_included_in_latency") is False):
            raise ValueError(f"timing boundary marker differs: {stem} {arm}")

        old_arm = "B" if arm == "B" else "C"
        old_row = old.get((stem, old_arm))
        if old_row is None:
            raise ValueError(f"Stage-A reference missing: {stem} {old_arm}")
        old_path = _safe_child(stage_a_root, old_row["raw_path"])
        if sha256(old_path) != old_row["raw_sha256"]:
            raise ValueError(f"Stage-A reference raw SHA differs: {stem} {old_arm}")
        old_raw, old_identity = read_artifact(old_path)
        if (old_identity.get("observation_id") != stem or old_identity.get("arm") != old_arm
                or old_identity.get("input_sha256") != input_row["observation_sha256"]):
            raise ValueError(f"Stage-A raw identity differs: {stem} {old_arm}")
        if not np.array_equal(final_bits, _bits(old_raw["final_decoded"], 2048, "Stage-A final bits")):
            raise ValueError(f"final bits differ from Stage-A {old_arm}: {stem} {arm}")
        delta = 0.0
        if arm != "B":
            if not isinstance(old_raw.get("acquisition"), dict) or not isinstance(raw.get("acquisition"), dict):
                raise ValueError(f"F1 acquisition record missing: {stem} {arm}")
            if set(old_raw["acquisition"]) != set(raw["acquisition"]):
                raise ValueError(f"F1 acquisition schema differs: {stem} {arm}")
            delta = _deep_compare(
                {field: old_raw["acquisition"][field] for field in REFERENCE_FIELDS},
                {field: raw["acquisition"][field] for field in REFERENCE_FIELDS})
            delta = max(delta, _deep_compare(old_raw["initial_geometry"], raw["initial_geometry"]))
            delta = max(delta, _deep_compare(old_raw["entering_geometry"], raw["entering_geometry"]))
            delta = max(delta, _deep_compare(old_raw["baseline_arrays"], raw["baseline_arrays"]))
            max_reference_delta[arm] = max(max_reference_delta[arm], delta)
        else:
            if bool(old_raw["triggered"]) != bool(raw["triggered"]):
                raise ValueError(f"B trigger differs from Stage-A B: {stem}")
            for bit_key in ("r0_decoded", "r1_decoded"):
                if not np.array_equal(old_raw["baseline_arrays"][bit_key], raw["baseline_arrays"][bit_key]):
                    raise ValueError(f"B native bits differ from Stage-A B: {stem} {bit_key}")
            if triggered and not np.array_equal(old_raw["branch_decoder"]["decoded"], raw["branch_decoder"]["decoded"]):
                raise ValueError(f"B branch bits differ from Stage-A B: {stem}")
        if abs(float(row["reference_max_difference"]) - delta) > 1e-15 or row.get("reference_raw_sha256") != old_row["raw_sha256"]:
            raise ValueError(f"producer reference receipt differs from independent comparison: {stem} {arm}")
        reference_checks["Cfast" if arm == "Cfast" else "Cref" if arm == "Cref" else "B"] += 1
        outputs[stem, arm] = {"correct": final_correct, "info_bit_errors": bit_errors,
                              "syndrome_weight": final_syndrome,
                              "acquisition_seconds": float(row["acquisition_seconds"]),
                              "complete_latency_seconds": float(row["complete_latency_seconds"])}

    if {arm: counts[arm]["frames"] for arm in counts} != {"B": 1024, "Cfast": 1024, "Cref": 64}:
        raise ValueError("per-arm denominators differ from 1024/1024/64")
    paired = {"n": N_FRAMES, "B_wrong_Cfast_correct": 0,
              "B_correct_Cfast_wrong": 0, "both_correct": 0, "both_wrong": 0}
    for stem in population:
        b, fast = outputs[stem, "B"]["correct"], outputs[stem, "Cfast"]["correct"]
        paired["B_wrong_Cfast_correct"] += int(not b and fast)
        paired["B_correct_Cfast_wrong"] += int(b and not fast)
        paired["both_correct"] += int(b and fast)
        paired["both_wrong"] += int(not b and not fast)

    matched = []
    for frame, stem in enumerate(population):
        if frame % 16 == 0:
            fast_acq = outputs.get((stem, "Cfast"))
            ref_acq = outputs.get((stem, "Cref"))
            if fast_acq is None or ref_acq is None:
                raise ValueError(f"matched Cfast/Cref frame missing: {stem}")
            fast_times = outputs[stem, "Cfast"]
            ref_times = outputs[stem, "Cref"]
            matched.append({"observation_id": stem,
                "fast_acquisition_seconds": fast_times["acquisition_seconds"],
                "reference_acquisition_seconds": ref_times["acquisition_seconds"],
                "fast_complete_seconds": fast_times["complete_latency_seconds"],
                "reference_complete_seconds": ref_times["complete_latency_seconds"],
                "acquisition_ratio_fast_over_ref": fast_times["acquisition_seconds"] / ref_times["acquisition_seconds"],
                "complete_ratio_fast_over_ref": fast_times["complete_latency_seconds"] / ref_times["complete_latency_seconds"]})
    ratios = {}
    for name in ("acquisition", "complete"):
        vals = [item[f"{name}_ratio_fast_over_ref"] for item in matched]
        fast_field = f"fast_{name}_seconds"
        ref_field = f"reference_{name}_seconds"
        ratios[name] = {"n": len(vals), "mean_of_paired_ratios": float(np.mean(vals)),
                        "ratio_of_means": float(np.mean([item[fast_field] for item in matched]) /
                                                 np.mean([item[ref_field] for item in matched]))}

    return {
        "schema": "cstate-necessity-stage-b-f1-independent-recount/1",
        "status": "pass",
        "opened_truth_payloads": len(truths),
        "observed": {"observed_seal_sha256": sha256(observed / "observed_seal.json"),
                     "manifest_sha256": sha256(observed / "manifest.json"),
                     "ledger_sha256": sha256(observed / "ledger.jsonl"),
                     "attempts_sha256": sha256(observed / "attempts.jsonl"),
                     "sealed_file_count": len(sealed_files),
                     "calls": len(ledger), "attempts": len(attempts),
                     "arm_counts": {arm: counts[arm]["frames"] for arm in counts}},
        "git_attestation": git_record,
        "source_hashes": registration["source_hashes"],
        "independent_stage_a_reference_checks": reference_checks,
        "max_reference_numeric_delta": max_reference_delta,
        "arms": {arm: {**counts[arm], "FER": counts[arm]["info_errors"] / counts[arm]["frames"],
                        "BER": counts[arm]["info_bit_errors"] / (1024 * counts[arm]["frames"]),
                        "timing": {metric: _summary(timing[arm][metric])
                                   for metric in ("acquisition", "complete")},
                        "deadlines": deadlines[arm]} for arm in counts},
        "paired_B_vs_Cfast": paired,
        "matched_64_Cfast_over_Cref": ratios,
        "limitations": ["No coded-bit BER was calculated.",
                        "No primary-analysis summary was read or used."]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-root", type=Path, required=True)
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--stage-a-registration", type=Path)
    parser.add_argument("--stage-a-observed-root", type=Path)
    parser.add_argument("--population-observed-root", type=Path)
    parser.add_argument("--truth-root", type=Path)
    parser.add_argument("--code-cache", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--git-attestation", type=Path)
    parser.add_argument("--observed-commit")
    parser.add_argument("--git-repo", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--failure-only", action="store_true",
                        help="count/hash partial-run JSON receipts only; do not open NPZ payloads")
    parser.add_argument("--primary-analysis-frozen", action="store_true")
    args = parser.parse_args()
    if args.failure_only:
        receipt = recount_failed_attempt(args)
    else:
        if not args.primary_analysis_frozen:
            parser.error("truth payload access requires the parent-confirmed frozen-analysis gate")
        required = (args.registration, args.stage_a_registration, args.stage_a_observed_root,
                    args.population_observed_root, args.truth_root, args.code_cache,
                    args.source_root, args.git_attestation, args.observed_commit)
        if any(value is None for value in required):
            parser.error("full recount requires all registration, source, Git, truth, and code paths")
        receipt = recount(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
