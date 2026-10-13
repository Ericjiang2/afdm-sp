"""Independent mechanical recount of sealed Stage-A saved outputs.

This module never imports a receiver, generator, decoder, or the primary
analysis module.  It refuses truth access unless the caller explicitly marks
the primary analysis as frozen/authorized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

import numpy as np


SCHEMA = "cstate-necessity-stage-a/1"
ARMS = ("A", "B", "C", "D")
N_FRAMES = 1024
MAX_E_CALLS = 1024
EVIDENCE_METADATA = "__evidence_metadata__"
ARRAY_SENTINEL = "__evidence_array__"
TUPLE_SENTINEL = "__evidence_tuple__"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_BINDING = PROJECT_ROOT / ".trellis/tasks/09-22-tf-production-gap-audit/research/stageA-input-binding.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        raise ValueError(f"sealed path escapes root: {relative}")
    return candidate


def _sealed_inventory(root: Path, seal_name: str, expected_schema: str | None = None) -> dict[str, Any]:
    seal_path = root / seal_name
    seal = _json(seal_path)
    if seal.get("status") != "pass":
        raise ValueError(f"{seal_name} status is not pass")
    if expected_schema is not None and seal.get("schema") != expected_schema:
        raise ValueError(f"{seal_name} schema differs")
    files = seal.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"{seal_name} has no file inventory")
    actual_names = {str(p.relative_to(root)) for p in root.rglob("*")
                    if p.is_file() and p.name != seal_name}
    if actual_names != set(files):
        missing, extra = sorted(set(files) - actual_names), sorted(actual_names - set(files))
        raise ValueError(f"{seal_name} inventory names differ: missing={missing[:3]} extra={extra[:3]}")
    for relative, expected in files.items():
        path = _safe_child(root, relative)
        if sha256(path) != expected:
            raise ValueError(f"sealed SHA-256 differs: {relative}")
    return seal


def _references(tree: Any) -> set[str]:
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            key = tree[ARRAY_SENTINEL]
            if not isinstance(key, str):
                raise ValueError("invalid evidence array reference")
            return {key}
        if set(tree) == {TUPLE_SENTINEL}:
            return _references(tree[TUPLE_SENTINEL])
        result: set[str] = set()
        for value in tree.values():
            result.update(_references(value))
        return result
    if isinstance(tree, list):
        result: set[str] = set()
        for value in tree:
            result.update(_references(value))
        return result
    return set()


def _unpack(tree: Any, arrays: dict[str, np.ndarray]) -> Any:
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            return arrays[tree[ARRAY_SENTINEL]].copy()
        if set(tree) == {TUPLE_SENTINEL}:
            return tuple(_unpack(item, arrays) for item in tree[TUPLE_SENTINEL])
        return {key: _unpack(value, arrays) for key, value in tree.items()}
    if isinstance(tree, list):
        return [_unpack(value, arrays) for value in tree]
    return tree


def read_artifact(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Decode the numeric evidence envelope directly, without project helpers."""
    with np.load(path, allow_pickle=False) as archive:
        if EVIDENCE_METADATA not in archive.files:
            raise ValueError(f"artifact lacks metadata: {path}")
        raw = np.asarray(archive[EVIDENCE_METADATA])
        if raw.dtype != np.uint8 or raw.ndim != 1:
            raise ValueError(f"invalid metadata encoding: {path}")
        envelope = json.loads(raw.tobytes().decode("utf-8"))
        if envelope.get("format_version") != 2:
            raise ValueError(f"unsupported evidence envelope: {path}")
        payload_tree = envelope.get("payload")
        refs = _references(payload_tree)
        actual = set(archive.files) - {EVIDENCE_METADATA}
        if refs != actual:
            raise ValueError(f"artifact array inventory differs: {path}")
        arrays = {key: np.asarray(archive[key]) for key in refs}
    payload = _unpack(payload_tree, arrays)
    identity = envelope.get("identity")
    if not isinstance(payload, dict) or not isinstance(identity, dict):
        raise ValueError(f"invalid evidence payload/identity: {path}")
    return payload, identity


def _binary_vector(value: Any, size: int, label: str) -> np.ndarray:
    arr = np.asarray(value)
    if arr.shape != (size,) or arr.dtype.kind not in "biu" or not np.isin(arr, (0, 1)).all():
        raise ValueError(f"{label} is not a binary vector of length {size}")
    return arr.astype(np.uint8, copy=False)


def _syndrome_weight(H: np.ndarray, bits: np.ndarray) -> int:
    return int(np.count_nonzero((H @ bits.astype(np.int64)) % 2))


def _deep_equal(left: Any, right: Any, *, atol: float = 2e-10, path: str = "") -> float:
    """Frozen C/D/E native-prefix parity; categorical/bits exact, numeric absolute."""
    if isinstance(left, dict):
        if not isinstance(right, dict) or set(left) != set(right):
            raise ValueError(f"native prefix keys differ at {path}")
        return max((_deep_equal(left[k], right[k], atol=atol, path=f"{path}/{k}") for k in left), default=0.)
    if isinstance(left, (list, tuple)):
        if not isinstance(right, type(left)) or len(left) != len(right):
            raise ValueError(f"native prefix sequence differs at {path}")
        return max((_deep_equal(a, b, atol=atol, path=f"{path}/{i}")
                    for i, (a, b) in enumerate(zip(left, right))), default=0.)
    if isinstance(left, np.ndarray):
        a, b = np.asarray(left), np.asarray(right)
        if a.shape != b.shape or a.dtype != b.dtype:
            raise ValueError(f"native prefix shape/dtype differs at {path}")
        if a.dtype.kind in "biuSU":
            if not np.array_equal(a, b):
                raise ValueError(f"native prefix exact field differs at {path}")
            return 0.
        if not np.issubdtype(a.dtype, np.number) or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError(f"native prefix has unsupported/nonfinite field at {path}")
        delta = float(np.max(np.abs(a - b))) if a.size else 0.
        if delta > atol:
            raise ValueError(f"native prefix numeric field differs at {path}: {delta}")
        return delta
    if isinstance(left, (int, float, complex)) and not isinstance(left, bool):
        if not np.isclose(left, right, atol=atol, rtol=0):
            raise ValueError(f"native prefix scalar differs at {path}")
        return float(abs(left - right))
    if left != right:
        raise ValueError(f"native prefix value differs at {path}")
    return 0.


def _binding_rows(binding: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = binding.get("input_hashes_and_old_AB_artifacts")
    if not isinstance(rows, list) or len(rows) != N_FRAMES:
        raise ValueError("input binding must contain exactly 1024 frame rows")
    result = {}
    for row in rows:
        stem = row.get("observation_id")
        if stem in result or row.get("snr_centi_db") != 650:
            raise ValueError("input binding has duplicate or non-6.5-dB frame")
        result[stem] = row
    expected = {f"s650_f{i:04d}" for i in range(N_FRAMES)}
    if set(result) != expected:
        raise ValueError("input binding frame identity set differs")
    return result


def _load_code_cache(path: Path, expected_sha: str) -> tuple[np.ndarray, np.ndarray]:
    if sha256(path) != expected_sha:
        raise ValueError("registered code cache SHA differs")
    with np.load(path, allow_pickle=False) as cache:
        if not {"H", "free_cols"}.issubset(cache.files):
            raise ValueError("code cache lacks H/free_cols")
        H = np.asarray(cache["H"])
        free_cols = np.asarray(cache["free_cols"])
    if H.shape != (1026, 2048) or H.dtype.kind not in "biu" or not np.isin(H, (0, 1)).all():
        raise ValueError("registered H shape/type differs")
    if free_cols.shape != (1024,) or free_cols.dtype.kind not in "iu" or len(set(map(int, free_cols))) != 1024:
        raise ValueError("registered information-coordinate map differs")
    if (free_cols < 0).any() or (free_cols >= 2048).any():
        raise ValueError("information-coordinate index outside codeword")
    return H.astype(np.uint8, copy=False), free_cols.astype(np.int64, copy=False)


def _truth_index(truth_root: Path, binding: dict[str, Any], input_rows: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    population = binding["population"]
    expected_seal_sha = population.get("truth_seal_sha256")
    if not expected_seal_sha or sha256(truth_root / "truth_seal.json") != expected_seal_sha:
        raise ValueError("truth seal does not match the previously bound population")
    seal = _json(truth_root / "truth_seal.json")
    if seal.get("status") != "pass" or seal.get("schema") != "tf-cstate-prospective/1":
        raise ValueError("truth seal status/schema differs")
    files = seal.get("files")
    if not isinstance(files, dict) or files.get("ledger.jsonl") != sha256(truth_root / "ledger.jsonl"):
        raise ValueError("truth ledger is not seal-bound")
    if files.get("manifest.json") != sha256(truth_root / "manifest.json"):
        raise ValueError("truth manifest is not seal-bound")
    actual_names = {str(path.relative_to(truth_root)) for path in truth_root.rglob("*")
                    if path.is_file() and path.name != "truth_seal.json"}
    if actual_names != set(files):
        raise ValueError("truth artifact names differ from sealed inventory")
    ledger = _jsonl(truth_root / "ledger.jsonl")
    indexed = {row["observation_id"]: row for row in ledger if row.get("snr_centi_db") == 650}
    if len(indexed) != N_FRAMES or set(indexed) != set(input_rows):
        raise ValueError("sealed truth ledger does not contain the exact 6.5-dB cohort")
    return indexed, files


def _latest_at(checkpoints: list[dict[str, Any]], deadline: float, info: np.ndarray,
               free_cols: np.ndarray) -> dict[str, Any]:
    ready = [cp for cp in checkpoints if cp["ready_seconds"] <= deadline]
    if not ready:
        return {"ready": False, "correct": False, "round": None}
    cp = max(ready, key=lambda x: (x["ready_seconds"], x["round"]))
    decoded = cp["decoded"]
    decoded_info = decoded[free_cols]
    return {"ready": True, "correct": bool(np.array_equal(decoded_info, info)),
            "round": cp["round"]}


def _new_structure_accumulator() -> dict[str, Any]:
    return {"initial_path_counts": {}, "entering_path_counts": {},
            "same_delay_initial": 0, "same_delay_entering": 0, "f1_frames": 0,
            "initial_delay_multiplicity_histogram": {},
            "entering_delay_multiplicity_histogram": {},
            "edits": {"accepted_edits": 0, "delay_changed": 0,
                      "new_delay_present_on_entry": 0, "new_delay_absent_on_entry": 0,
                      "same_delay_doppler_change": 0},
            "nearest_separations": []}


def _add_structure(acc: dict[str, Any], stem: str, arm: str,
                   raw: dict[str, Any], row: dict[str, Any]) -> None:
    if arm not in ("C", "D"):
        return
    initial, entering = raw.get("initial_geometry"), raw.get("entering_geometry")
    if not isinstance(initial, dict) or not isinstance(entering, dict):
        raise ValueError(f"F1 geometry missing for {stem} {arm}")
    initial_delays = np.asarray(initial["delays"], dtype=np.int64)
    initial_dopplers = np.asarray(initial["dopplers"], dtype=np.float64)
    delays = np.asarray(entering["delays"], dtype=np.int64)
    dopplers = np.asarray(entering["dopplers"], dtype=np.float64)
    if initial_delays.ndim != 1 or initial_delays.shape != initial_dopplers.shape:
        raise ValueError(f"invalid initial F1 geometry for {stem} {arm}")
    if delays.ndim != 1 or delays.shape != dopplers.shape:
        raise ValueError(f"invalid entering F1 geometry for {stem} {arm}")
    if arm == "C":
        acc["f1_frames"] += 1
        key = str(len(initial_delays))
        acc["initial_path_counts"][key] = acc["initial_path_counts"].get(key, 0) + 1
        key = str(len(delays))
        acc["entering_path_counts"][key] = acc["entering_path_counts"].get(key, 0) + 1
        for delay, count in zip(*np.unique(initial_delays, return_counts=True)):
            key = str(int(count))
            hist = acc["initial_delay_multiplicity_histogram"]
            hist[key] = hist.get(key, 0) + 1
        for delay, count in zip(*np.unique(delays, return_counts=True)):
            key = str(int(count))
            hist = acc["entering_delay_multiplicity_histogram"]
            hist[key] = hist.get(key, 0) + 1
        acc["same_delay_initial"] += int(len(np.unique(initial_delays)) < len(initial_delays))
        acc["same_delay_entering"] += int(len(np.unique(delays)) < len(delays))
    if arm != "D" or not row["triggered"]:
        return
    result = raw.get("geometry_result")
    if not isinstance(result, dict) or not isinstance(result.get("edits"), list):
        raise ValueError(f"triggered F1 CSTATE geometry edits missing for {stem}")
    active_delays, active_dopplers = delays.copy(), dopplers.copy()
    entering_delay_set = set(map(int, delays))
    for edit in result["edits"]:
        old, new = edit.get("old"), edit.get("new")
        if not isinstance(old, dict) or not isinstance(new, dict):
            raise ValueError(f"malformed CSTATE edit for {stem}")
        old_delay, new_delay = int(old["delay"]), int(new["delay"])
        old_nu, new_nu = float(old["doppler"]), float(new["doppler"])
        slot = int(edit["slot"])
        if not 0 <= slot < len(active_delays):
            raise ValueError(f"CSTATE edit slot outside entering geometry for {stem}")
        counts = acc["edits"]
        counts["accepted_edits"] += 1
        counts["delay_changed"] += int(old_delay != new_delay)
        present = new_delay in entering_delay_set
        counts["new_delay_present_on_entry"] += int(present)
        counts["new_delay_absent_on_entry"] += int(not present)
        counts["same_delay_doppler_change"] += int(old_delay == new_delay and old_nu != new_nu)
        alternatives = np.abs(active_dopplers[(active_delays == new_delay) &
                                               (np.arange(len(active_delays)) != slot)] - new_nu)
        if alternatives.size:
            acc["nearest_separations"].append(float(np.min(alternatives)))
        active_delays[slot], active_dopplers[slot] = new_delay, new_nu


def _finish_structure(acc: dict[str, Any]) -> dict[str, Any]:
    values = acc["nearest_separations"]
    nearest = {"n": len(values), "min": min(values) if values else None,
               "median": float(np.median(values)) if values else None,
               "max": max(values) if values else None, "threshold_applied": False}
    return {"f1_C_frames": acc["f1_frames"],
            "initial_path_count_distribution": acc["initial_path_counts"],
            "entering_path_count_distribution": acc["entering_path_counts"],
            "initial_delay_multiplicity_histogram": acc["initial_delay_multiplicity_histogram"],
            "entering_delay_multiplicity_histogram": acc["entering_delay_multiplicity_histogram"],
            "frames_with_same_delay_multiplicity_initial": acc["same_delay_initial"],
            "frames_with_same_delay_multiplicity_entering": acc["same_delay_entering"],
            "triggered_D_edit_counts": acc["edits"],
            "nearest_same_delay_doppler_separation": nearest,
            "physical_capture_sufficiency": "unknown; no frozen capture threshold"}


def recount(observed_root: Path, truth_root: Path, code_cache: Path,
            input_binding_path: Path) -> dict[str, Any]:
    observed_root, truth_root = Path(observed_root), Path(truth_root)
    input_binding = _json(input_binding_path)
    if input_binding.get("schema") != "stageA-input-binding/1":
        raise ValueError("stageA input binding schema differs")
    input_rows = _binding_rows(input_binding)
    seal = _sealed_inventory(observed_root, "observed_seal.json", SCHEMA)
    if seal.get("observations") != N_FRAMES or seal.get("primary_calls") != 4096:
        raise ValueError("observed seal population/call count differs")
    if (observed_root / "invalid_partial.json").exists():
        raise ValueError("sealed run contains invalid_partial marker")
    manifest = _json(observed_root / "manifest.json")
    if manifest.get("schema") != SCHEMA:
        raise ValueError("observed manifest schema differs")
    if manifest.get("registration_sha256") != seal.get("registration_sha256"):
        raise ValueError("observed registration hash differs between manifest and seal")
    if manifest.get("population_observed_seal_sha256") != seal.get("population_observed_seal_sha256"):
        raise ValueError("population seal hash differs between manifest and seal")
    if manifest.get("population_observed_seal_sha256") != input_binding["population"]["population_seal_sha256"]:
        raise ValueError("Stage-A population seal binding differs")
    H, free_cols = _load_code_cache(Path(code_cache), manifest["code_cache_sha256"])
    truth_rows, truth_files = _truth_index(truth_root, input_binding, input_rows)

    attempts = _jsonl(observed_root / "attempts.jsonl")
    ledger = _jsonl(observed_root / "ledger.jsonl")
    if len(attempts) != seal.get("attempts") or len(ledger) != seal.get("attempts"):
        raise ValueError("attempt journal/ledger count differs from seal")
    if len(attempts) > 4096 + MAX_E_CALLS or len(ledger) > 4096 + MAX_E_CALLS:
        raise ValueError("attempt budget exceeded")
    if any(row.get("status") != "ok" for row in ledger):
        raise ValueError("failed ledger row makes the run U; no subset FER recount")
    if len(ledger) < 4096:
        raise ValueError("incomplete A-D primary denominator")
    if seal.get("local_calls") != len(ledger) - 4096 or seal.get("attempts") != 4096 + seal.get("local_calls"):
        raise ValueError("primary/local call accounting differs")
    if seal.get("local_calls") > MAX_E_CALLS:
        raise ValueError("E local-call budget exceeded")

    if [row.get("attempt_index") for row in attempts] != list(range(1, len(attempts) + 1)):
        raise ValueError("attempt journal indices are not contiguous")
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    expected_sequence = []
    for frame in range(N_FRAMES):
        expected_sequence.extend((f"s650_f{frame:04d}", arm) for arm in (ARMS[frame % 4:] + ARMS[:frame % 4]))
        stem = f"s650_f{frame:04d}"
        row = input_rows[stem]
        for old in row.get("old_AB", []):
            if old.get("arm") not in ("TF", "TF_CSTATE") or old.get("status") != "ok":
                raise ValueError(f"old A/B input binding malformed: {stem}")
        # E is appended after A-D iff C's native second-round syndrome triggers.
        c_row = next((item for item in ledger if item.get("observation_id") == stem and item.get("arm") == "C"), None)
        if c_row is None:
            raise ValueError(f"missing C row before E allocation check: {stem}")
        if int(c_row["baseline_syndrome_weight"]) != 0:
            expected_sequence.append((stem, "E"))

    if len(expected_sequence) != len(ledger):
        raise ValueError("ledger length differs from full expected frame/arm schedule")
    structure_acc = _new_structure_accumulator()
    prefix_stem: str | None = None
    prefix_reference: tuple[dict[str, Any], dict[str, Any]] | None = None
    cached_truth_stem: str | None = None
    cached_truth_info: np.ndarray | None = None
    cached_truth_coded: np.ndarray | None = None
    outcomes: dict[str, list[bool]] = {arm: [] for arm in (*ARMS, "E")}
    valid_wrong: dict[str, list[bool]] = {arm: [] for arm in (*ARMS, "E")}
    rescues = {arm: 0 for arm in (*ARMS, "E")}
    harms = {arm: 0 for arm in (*ARMS, "E")}
    triggers = {arm: 0 for arm in (*ARMS, "E")}
    latency: dict[str, list[float]] = {arm: [] for arm in (*ARMS, "E")}
    deadline_counts = {arm: {"0.5": {"correct": 0, "missing": 0, "wrong_or_missing": 0},
                             "1.0": {"correct": 0, "missing": 0, "wrong_or_missing": 0}}
                       for arm in (*ARMS, "E")}
    max_array_delta = 0.
    c_native_trigger_count = 0

    for position, (attempt, row, expected) in enumerate(zip(attempts, ledger, expected_sequence)):
        stem, arm = expected
        key = (stem, arm)
        if (attempt.get("attempt_index"), attempt.get("observation_id"), attempt.get("arm"), attempt.get("input_sha256")) != (
                row.get("attempt_index"), stem, arm, input_rows[stem]["observation_sha256"]):
            raise ValueError(f"attempt journal/ledger/source binding differs: {key}")
        if (key in by_key or row.get("observation_id") != stem or row.get("arm") != arm or
                row.get("frame") != int(stem[-4:])):
            raise ValueError(f"duplicate/wrong scheduled ledger identity: {key}")
        if row.get("input_sha256") != input_rows[stem]["observation_sha256"]:
            raise ValueError(f"input SHA differs from frozen cohort binding: {key}")
        if row.get("observation_hash") != input_rows[stem]["observation_hash"] or row.get("stream_ids") != input_rows[stem]["stream_ids"]:
            raise ValueError(f"observation identity/streams differ from frozen cohort: {key}")
        if row.get("receiver_started") is not True:
            raise ValueError(f"receiver call was not recorded as started: {key}")
        if len(row.get("checkpoints", [])) not in (2, 3):
            raise ValueError(f"expected two native CPs plus optional triggered branch CP: {key}")
        if arm == "E" and not row.get("triggered"):
            raise ValueError("E arm must be a triggered local continuation")
        if arm not in ("B", "D", "E") and row.get("triggered"):
            raise ValueError(f"unexpected trigger in arm {arm}: {stem}")
        if arm in ("B", "D") and bool(row.get("triggered")) != (int(row["baseline_syndrome_weight"]) != 0):
            raise ValueError(f"CSTATE trigger does not match native syndrome: {key}")
        if arm == "E" and (int(row.get("baseline_syndrome_weight", 0)) == 0):
            raise ValueError(f"E did not follow a nonzero native syndrome: {stem}")
        if bool(row.get("triggered")) != (len(row["checkpoints"]) == 3):
            raise ValueError(f"trigger/branch checkpoint inventory differs: {key}")
        if arm == "C" and int(row["baseline_syndrome_weight"]) != 0:
            c_native_trigger_count += 1
        latency[arm].append(float(row["complete_latency_seconds"]))
        triggers[arm] += int(bool(row.get("triggered")))
        raw_path = _safe_child(observed_root, row["raw_path"])
        decision_path = _safe_child(observed_root, row["decision_path"])
        if seal["files"].get(row["raw_path"]) != row["raw_sha256"]:
            raise ValueError(f"raw SHA differs: {key}")
        if seal["files"].get(row["decision_path"]) != row["decision_sha256"]:
            raise ValueError(f"decision SHA differs: {key}")
        raw, identity = read_artifact(raw_path)
        if identity.get("schema") != SCHEMA or identity.get("observation_id") != stem or identity.get("arm") != arm or identity.get("input_sha256") != row["input_sha256"]:
            raise ValueError(f"raw artifact identity differs: {key}")
        decision = _json(decision_path)
        if decision.get("observation_id") != stem or decision.get("arm") != arm or decision.get("input_sha256") != row["input_sha256"]:
            raise ValueError(f"decision identity differs: {key}")
        if (decision.get("raw_path") != row["raw_path"] or
                decision.get("raw_sha256") != row["raw_sha256"] or
                decision.get("checkpoints") != row["checkpoints"] or
                decision.get("triggered") != row["triggered"] or
                raw.get("triggered") != row["triggered"] or
                int(raw.get("baseline_syndrome_weight")) != int(row["baseline_syndrome_weight"])):
            raise ValueError(f"ledger/raw/decision cross-bindings differ: {key}")
        final_bits = _binary_vector(raw["final_decoded"], 2048, f"{key} final_decoded")
        final_info = _binary_vector(raw["final_info"], 1024, f"{key} final_info")
        if not np.array_equal(final_info, final_bits[free_cols]):
            raise ValueError(f"saved final_info differs from systematic decoded coordinates: {key}")
        if not np.array_equal(_binary_vector(decision["final_decoded"], 2048, f"{key} decision decoded"), final_bits):
            raise ValueError(f"raw/decision decoded vectors differ: {key}")
        if not np.array_equal(_binary_vector(decision["final_info"], 1024, f"{key} decision info"), final_info):
            raise ValueError(f"raw/decision information vectors differ: {key}")
        if hashlib.sha256(final_bits.tobytes()).hexdigest() != row.get("final_decoded_sha256") or decision.get("final_decoded_sha256") != row.get("final_decoded_sha256"):
            raise ValueError(f"final decoded hash differs: {key}")
        if cached_truth_stem != stem:
            truth_row = truth_rows[stem]
            truth_path = _safe_child(truth_root, truth_row["truth_path"])
            expected_truth_sha = truth_row["truth_sha256"]
            if truth_files.get(truth_row["truth_path"]) != expected_truth_sha:
                raise ValueError(f"truth ledger/seal SHA mismatch: {stem}")
            if sha256(truth_path) != expected_truth_sha:
                raise ValueError(f"truth payload SHA differs: {stem}")
            truth, truth_identity = read_artifact(truth_path)
            if truth_identity.get("observation_id") != stem or truth_identity.get("kind") != "truth":
                raise ValueError(f"truth artifact identity differs: {stem}")
            if truth.get("observation_hash") != row["observation_hash"] or truth.get("stream_ids") != row["stream_ids"]:
                raise ValueError(f"truth/observed semantic identity differs: {stem}")
            info = _binary_vector(truth["info"], 1024, f"{stem} truth info")
            coded = _binary_vector(truth["coded"], 2048, f"{stem} truth coded")
            if not np.array_equal(coded[free_cols], info) or _syndrome_weight(H, coded) != 0:
                raise ValueError(f"truth coded/info/H consistency differs: {stem}")
            cached_truth_stem, cached_truth_info, cached_truth_coded = stem, info, coded
        info, coded = cached_truth_info, cached_truth_coded
        if info is None or coded is None:
            raise AssertionError("truth cache initialization failed")
        errors = int(np.count_nonzero(final_info != info))
        syndrome = _syndrome_weight(H, final_bits)
        if syndrome != int(row["final_syndrome_weight"]) or syndrome != int(decision["final_syndrome_weight"]):
            raise ValueError(f"final syndrome weight differs: {key}")
        outcomes[arm].append(errors == 0)
        valid_wrong[arm].append(errors > 0 and syndrome == 0)
        final_correct = errors == 0
        checkpoints = []
        cp_rounds = []
        for cp in row["checkpoints"]:
            cp_round = int(cp["round"])
            cp_rounds.append(cp_round)
            cp_path = _safe_child(observed_root, cp["path"])
            if seal["files"].get(cp["path"]) != cp["artifact_sha256"]:
                raise ValueError(f"checkpoint SHA differs: {key} round {cp_round}")
            cp_payload, cp_identity = read_artifact(cp_path)
            if cp_identity.get("observation_id") != stem or cp_identity.get("arm") != arm or cp_identity.get("round") != cp_round:
                raise ValueError(f"checkpoint identity differs: {key} round {cp_round}")
            cp_bits = _binary_vector(cp_payload["decoded"], 2048, f"{key} round {cp_round} decoded")
            if cp_round in (0, 1):
                array_key = f"r{cp_round}_decoded"
                if array_key not in raw["baseline_arrays"] or not np.array_equal(
                        _binary_vector(raw["baseline_arrays"][array_key], 2048, f"{key} {array_key}"), cp_bits):
                    raise ValueError(f"native checkpoint/raw saved bits differ: {key} round {cp_round}")
            elif cp_round == 2 and not np.array_equal(cp_bits, final_bits):
                raise ValueError(f"branch checkpoint/final saved bits differ: {key}")
            cp_syndrome = _syndrome_weight(H, cp_bits)
            if cp_syndrome != int(cp["syndrome_weight"]):
                raise ValueError(f"checkpoint syndrome differs: {key} round {cp_round}")
            if cp_round == 1 and cp_syndrome != int(row["baseline_syndrome_weight"]):
                raise ValueError(f"baseline syndrome differs from second native checkpoint: {key}")
            event_ready = float(cp_payload["event"]["ready"])
            if (not np.isfinite(float(cp["ready_seconds"])) or float(cp["ready_seconds"]) < 0 or
                    not np.isfinite(float(cp["decision_ready_seconds"])) or
                    float(cp["decision_ready_seconds"]) < 0 or
                    event_ready < 0 or event_ready > float(cp["decision_ready_seconds"]) or
                    float(cp["decision_ready_seconds"]) > float(cp["ready_seconds"])):
                raise ValueError(f"checkpoint durable/decision timing differs: {key} round {cp_round}")
            checkpoints.append({"round": cp_round, "ready_seconds": float(cp["ready_seconds"]),
                                "decoded": cp_bits, "correct": bool(np.array_equal(cp_bits[free_cols], info))})
        if cp_rounds != [0, 1] + ([2] if row["triggered"] else []):
            raise ValueError(f"checkpoint rounds/order differ: {key}")
        if [cp["ready_seconds"] for cp in checkpoints] != sorted(cp["ready_seconds"] for cp in checkpoints):
            raise ValueError(f"checkpoint durable-ready times are not ordered: {key}")
        rescues[arm] += int(not checkpoints[1]["correct"] and final_correct)
        harms[arm] += int(checkpoints[1]["correct"] and not final_correct)
        for deadline in (0.5, 1.0):
            result = _latest_at(checkpoints, deadline, info, free_cols)
            label = str(deadline)
            deadline_counts[arm][label]["correct"] += int(result["ready"] and result["correct"])
            deadline_counts[arm][label]["missing"] += int(not result["ready"])
            deadline_counts[arm][label]["wrong_or_missing"] += int(not result["correct"])
        by_key[key] = row
        _add_structure(structure_acc, stem, arm, raw, row)
        if arm in ("C", "D", "E"):
            if prefix_reference is None:
                prefix_stem = stem
                prefix_reference = (raw["baseline_arrays"], raw["initial_geometry"])
            elif prefix_stem != stem:
                raise ValueError("F1 prefix cache crossed frame boundary")
            else:
                delta = _deep_equal(prefix_reference[0], raw["baseline_arrays"], path=f"{stem}/{arm}/baseline_arrays")
                max_array_delta = max(max_array_delta, delta)
                delta = _deep_equal(prefix_reference[1], raw["initial_geometry"], path=f"{stem}/{arm}/initial_geometry")
                max_array_delta = max(max_array_delta, delta)
        next_stem = expected_sequence[position + 1][0] if position + 1 < len(expected_sequence) else None
        if next_stem != stem:
            if prefix_stem != stem:
                raise ValueError(f"frame lacks a C/D/E prefix comparison: {stem}")
            prefix_stem, prefix_reference = None, None

    for arm in (*ARMS, "E"):
        expected_n = N_FRAMES if arm in ARMS else c_native_trigger_count
        if len(outcomes[arm]) != expected_n:
            raise ValueError(f"{arm} denominator differs: {len(outcomes[arm])} != {expected_n}")
    if seal.get("local_calls") != c_native_trigger_count or triggers["E"] != c_native_trigger_count:
        raise ValueError("E allocation must equal every nonzero-syndrome C observation")

    # Historical raw artifacts are not assumed local. Verify exact links and
    # producer parity records against the frozen metadata; do not claim raw-array
    # parity unless those old payload bytes are independently present.
    parity_path = observed_root / "historical_parity.jsonl"
    parity_records = _jsonl(parity_path)
    if len(parity_records) != 2 * N_FRAMES:
        raise ValueError("historical A/B parity receipt count differs")
    parity_index = {(r["observation_id"], r["arm"]): r for r in parity_records}
    if len(parity_index) != 2 * N_FRAMES:
        raise ValueError("duplicate historical parity receipts")
    history_checked = 0
    for stem, input_row in input_rows.items():
        for new_arm, old_arm in (("A", "TF"), ("B", "TF_CSTATE")):
            old = next((x for x in input_row["old_AB"] if x["arm"] == old_arm), None)
            new = by_key[stem, new_arm]
            parity = parity_index[stem, new_arm]
            if (not old or old.get("input_sha256") != new["input_sha256"] or
                    old.get("final_decoded_sha256") != new.get("final_decoded_sha256") or
                    parity.get("old_raw_sha256") != old.get("raw_sha256") or
                    parity.get("new_raw_sha256") != new.get("raw_sha256") or
                    parity.get("final_bits_equal") is not True or
                    float(parity.get("max_array_difference")) > 2e-10):
                raise ValueError(f"historical A/B declared parity linkage differs: {stem} {new_arm}")
            history_checked += 1

    latency_summary = {}
    for arm, values in latency.items():
        if not values:
            latency_summary[arm] = {"n": 0, "mean": None, "p95": None, "max": None}
            continue
        arr = np.asarray(values, dtype=np.float64)
        if not np.isfinite(arr).all() or np.any(arr < 0):
            raise ValueError(f"invalid complete latency in {arm}")
        latency_summary[arm] = {"n": int(arr.size), "mean": float(arr.mean()),
                                "p95": float(np.quantile(arr, .95)), "max": float(arr.max())}
    arm_summary = {}
    for arm in (*ARMS, "E"):
        values = outcomes[arm]
        arm_summary[arm] = {"n": len(values), "info_errors": len(values) - int(sum(values)),
                            "info_correct": int(sum(values)), "valid_wrong_words": int(sum(valid_wrong[arm])),
                            "triggered": triggers[arm], "native_r1_to_final_rescues": rescues[arm],
                            "native_r1_to_final_harms": harms[arm],
                            "deadlines": deadline_counts[arm], "complete_latency": latency_summary[arm]}
    structure = _finish_structure(structure_acc)
    paired_effects = {}
    for first, second in (("A", "B"), ("C", "D"), ("A", "C"), ("B", "D"), ("A", "D"), ("B", "C")):
        a = np.asarray(outcomes[first], dtype=bool)
        b = np.asarray(outcomes[second], dtype=bool)
        paired_effects[f"{first}_vs_{second}"] = {
            "n": N_FRAMES,
            "first_only_wrong_second_correct_rescues": int(np.count_nonzero(~a & b)),
            "first_correct_second_only_wrong_harms": int(np.count_nonzero(a & ~b)),
            "both_correct": int(np.count_nonzero(a & b)),
            "both_wrong": int(np.count_nonzero(~a & ~b)),
        }
    e_mask = np.asarray([int(by_key[(f"s650_f{i:04d}", "C")]["baseline_syndrome_weight"]) != 0
                         for i in range(N_FRAMES)], dtype=bool)
    c_subset = np.asarray(outcomes["C"], dtype=bool)[e_mask]
    e_subset = np.asarray(outcomes["E"], dtype=bool)
    paired_effects["C_vs_E_on_C_native_trigger_subset"] = {
        "n": int(e_mask.sum()),
        "C_wrong_E_correct_rescues": int(np.count_nonzero(~c_subset & e_subset)),
        "C_correct_E_wrong_harms": int(np.count_nonzero(c_subset & ~e_subset)),
        "both_correct": int(np.count_nonzero(c_subset & e_subset)),
        "both_wrong": int(np.count_nonzero(~c_subset & ~e_subset)),
        "population_interpretation": "C-triggered subset only; not a fifth-arm FER",
    }
    return {"schema": "independent-stage-a-recount/1", "status": "PASS",
            "scope": "saved-output-only; no receiver/generator/decoder calls",
            "observed_seal_sha256": sha256(observed_root / "observed_seal.json"),
            "truth_seal_sha256": sha256(truth_root / "truth_seal.json"),
            "input_binding_sha256": sha256(input_binding_path),
            "code_cache_sha256": sha256(code_cache),
            "producer_source_hashes": manifest.get("source_hashes"),
            "deadline_clock": "latest durable checkpoint ready_seconds, full A-D denominator; E is the C-triggered subset only",
            "frames": N_FRAMES, "primary_calls": 4096,
            "local_calls": int(seal["local_calls"]), "attempts": int(seal["attempts"]),
            "ledger_rows": len(ledger), "attempt_rows": len(attempts),
            "seal_file_count": len(seal["files"]), "C_native_trigger_count": c_native_trigger_count,
            "E_coverage_exact": triggers["E"] == c_native_trigger_count,
            "F1_C_D_E_prefix_max_abs_delta": max_array_delta,
            "historical_A_B_parity_link_rows": history_checked,
            "historical_old_payload_reloaded": False,
            "historical_array_parity_status": "producer receipt SHA/metric links verified; old raw arrays not independently reloaded",
            "arms": arm_summary, "paired_effects": paired_effects, "structure": structure,
            "truth_payloads_read": len(truth_rows)}


def self_test() -> None:
    """Small synthetic envelope and counting test; no project data is opened."""
    with tempfile.TemporaryDirectory(prefix="stage-a-verifier-") as temp:
        path = Path(temp) / "toy.npz"
        payload_tree = {"bits": {ARRAY_SENTINEL: "bits"}, "round": 0}
        envelope = {"format_version": 2, "identity": {"observation_id": "toy"},
                    "payload": payload_tree}
        metadata = np.frombuffer(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode(), dtype=np.uint8)
        np.savez_compressed(path, __evidence_metadata__=metadata, bits=np.array([0, 1, 1], dtype=np.uint8))
        read, identity = read_artifact(path)
        assert identity["observation_id"] == "toy"
        assert np.array_equal(read["bits"], np.array([0, 1, 1], dtype=np.uint8))
        H = np.array([[1, 0, 1], [0, 1, 1]], dtype=np.uint8)
        assert _syndrome_weight(H, np.array([1, 1, 0], dtype=np.uint8)) == 2
        cp = [{"round": 0, "ready_seconds": .2, "decoded": np.array([1, 0, 1])},
              {"round": 1, "ready_seconds": .7, "decoded": np.array([0, 1, 0])}]
        truth = np.array([0, 1], dtype=np.uint8)
        free = np.array([0, 1], dtype=np.int64)
        assert _latest_at(cp, .5, truth, free) == {"ready": True, "correct": False, "round": 0}
        assert _latest_at(cp, 1., truth, free) == {"ready": True, "correct": True, "round": 1}
        assert _deep_equal({"a": np.array([1., 2.])}, {"a": np.array([1., 2. + 1e-10])}) > 0
        acc = _new_structure_accumulator()
        geometry = {"delays": np.array([1, 1, 4]), "dopplers": np.array([-.4, .8, 1.2])}
        _add_structure(acc, "toy", "C", {"initial_geometry": geometry,
                    "entering_geometry": geometry}, {"triggered": False})
        branch = {"initial_geometry": geometry, "entering_geometry": geometry,
                  "geometry_result": {"edits": [
                      {"slot": 2, "old": {"delay": 4, "doppler": 1.2},
                       "new": {"delay": 1, "doppler": .2}}]}}
        _add_structure(acc, "toy", "D", branch, {"triggered": True})
        structural = _finish_structure(acc)
        assert structural["f1_C_frames"] == 1
        assert structural["initial_delay_multiplicity_histogram"] == {"1": 1, "2": 1}
        assert structural["triggered_D_edit_counts"]["delay_changed"] == 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--observed-root", type=Path)
    parser.add_argument("--truth-root", type=Path)
    parser.add_argument("--code-cache", type=Path)
    parser.add_argument("--input-binding", type=Path, default=DEFAULT_INPUT_BINDING)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--primary-analysis-frozen", action="store_true",
                        help="explicit gate: truth payload access is authorized only after parent confirms freeze")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"self_test": "PASS", "real_data_opened": False}, sort_keys=True))
        return
    if not args.primary_analysis_frozen:
        parser.error("refusing truth-dependent recount until --primary-analysis-frozen is explicitly supplied")
    required = (args.observed_root, args.truth_root, args.code_cache, args.output)
    if any(value is None for value in required):
        parser.error("--observed-root, --truth-root, --code-cache, and --output are required")
    receipt = recount(args.observed_root, args.truth_root, args.code_cache, args.input_binding)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": receipt["status"], "output": str(args.output),
                      "arms": receipt["arms"]}, sort_keys=True))


if __name__ == "__main__":
    main()
