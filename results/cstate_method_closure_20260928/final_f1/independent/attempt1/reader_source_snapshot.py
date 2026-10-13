#!/usr/bin/env python3
"""Independent saved-raw parity check for Stage-A C vs Stage-B Ccompat.

Reads only the two already-sealed observed raw trees. It does not import project
receiver, decoder, or comparison helpers, and does not read truth artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "f1-ccompat-stagea-raw-equivalence-recount/1"
STAGE_A_SEAL_SHA256 = "eb261e6183b8266220eb2abb7faec5bdf65ba253959374bed121f34523d65afa"
CCOMPAT_SEAL_SHA256 = "067fa733bbc1ecf26fe25b843f95d556f191bebb9d7b2ce4fcd3dae67f0cebdb"
STAGE_A_REGISTRATION_SHA256 = "d5acad64b60afb13c39a359400aecb8a7726f1f112f9174dce410a0d960c264f"
CCOMPAT_REGISTRATION_SHA256 = "4e039bacbef589b47219f7c0173de1f0209363c2768283dc36a21a01498dd643"
REFERENCE_FIELDS = (
    "delays",
    "dopplers",
    "gains",
    "bank_centers",
    "stopping_reason",
    "objective_history",
    "counters",
    "pilot_energy",
    "last_coordinate_gain",
)
METADATA_KEY = "__evidence_metadata__"
ARRAY_SENTINEL = "__ndarray_ref__"
TUPLE_SENTINEL = "__tuple__"
ATOL = 2e-10
RTOL = 0.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def unpack_tree(tree: Any, arrays: dict[str, np.ndarray]) -> Any:
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_SENTINEL}:
            key = tree[ARRAY_SENTINEL]
            if not isinstance(key, str) or key not in arrays:
                raise ValueError("invalid evidence array reference")
            return arrays[key].copy()
        if set(tree) == {TUPLE_SENTINEL}:
            return tuple(unpack_tree(value, arrays) for value in tree[TUPLE_SENTINEL])
        return {key: unpack_tree(value, arrays) for key, value in tree.items()}
    if isinstance(tree, list):
        return [unpack_tree(value, arrays) for value in tree]
    return tree


def load_evidence_npz(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    with np.load(path, allow_pickle=False) as archive:
        if METADATA_KEY not in archive.files:
            raise ValueError(f"missing evidence envelope: {path}")
        encoded = np.asarray(archive[METADATA_KEY])
        if encoded.dtype != np.uint8 or encoded.ndim != 1:
            raise ValueError(f"invalid evidence envelope bytes: {path}")
        envelope = json.loads(encoded.tobytes().decode("utf-8"))
        if envelope.get("format_version") != 2:
            raise ValueError(f"unsupported evidence format: {path}")
        tree = envelope.get("payload")
        refs: set[str] = set()

        def collect(node: Any) -> None:
            if isinstance(node, dict):
                if set(node) == {ARRAY_SENTINEL}:
                    key = node[ARRAY_SENTINEL]
                    if not isinstance(key, str):
                        raise ValueError("invalid evidence array reference")
                    refs.add(key)
                elif set(node) == {TUPLE_SENTINEL}:
                    for item in node[TUPLE_SENTINEL]:
                        collect(item)
                else:
                    for item in node.values():
                        collect(item)
            elif isinstance(node, list):
                for item in node:
                    collect(item)

        collect(tree)
        actual = set(archive.files) - {METADATA_KEY}
        if refs != actual:
            raise ValueError(f"evidence array inventory mismatch: {path}")
        arrays = {key: np.asarray(archive[key]) for key in refs}
    payload = unpack_tree(tree, arrays)
    identity = envelope.get("identity")
    if not isinstance(payload, dict) or not isinstance(identity, dict):
        raise ValueError(f"invalid evidence payload/identity: {path}")
    return payload, identity


class Comparison:
    def __init__(self) -> None:
        self.numeric_max: dict[str, float] = {}
        self.numeric_nodes: dict[str, int] = {}
        self.exact_nodes: dict[str, int] = {}
        self.issues: list[str] = []
        self.exact_issues: list[str] = []
        self.numeric_issues: list[str] = []
        self.final_bits_equal = True

    def _issue(self, path: str, reason: str, *, numeric: bool = False) -> None:
        issue = f"{path or '<root>'}: {reason}"
        self.issues.append(issue)
        (self.numeric_issues if numeric else self.exact_issues).append(issue)

    def compare(self, left: Any, right: Any, path: str = "") -> None:
        if isinstance(left, dict):
            if not isinstance(right, dict) or set(left) != set(right):
                self._issue(path, "mapping keys/type differ")
                return
            for key in left:
                self.compare(left[key], right[key], f"{path}/{key}" if path else key)
            return
        if isinstance(left, (tuple, list)):
            if type(left) is not type(right) or len(left) != len(right):
                self._issue(path, "sequence type/length differs")
                return
            for index, (a, b) in enumerate(zip(left, right)):
                self.compare(a, b, f"{path}/{index}" if path else str(index))
            return
        if isinstance(left, np.ndarray):
            if not isinstance(right, np.ndarray):
                self._issue(path, "array/non-array differs")
                return
            if left.shape != right.shape or left.dtype != right.dtype:
                self._issue(path, "array shape/dtype differs")
                return
            if path.endswith("decoded") or not np.issubdtype(left.dtype, np.number):
                self.exact_nodes[path] = self.exact_nodes.get(path, 0) + 1
                if not np.array_equal(left, right):
                    self._issue(path, "exact array differs")
                return
            delta = float(np.max(np.abs(left - right))) if left.size else 0.0
            self.numeric_nodes[path] = self.numeric_nodes.get(path, 0) + 1
            self.numeric_max[path] = max(self.numeric_max.get(path, 0.0), delta)
            if not np.allclose(left, right, atol=ATOL, rtol=RTOL):
                self._issue(path, f"numeric array exceeds tolerance (max_abs={delta!r})", numeric=True)
            return
        if isinstance(left, (int, float, complex, np.number)) and not isinstance(left, bool):
            delta = float(abs(left - right))
            self.numeric_nodes[path] = self.numeric_nodes.get(path, 0) + 1
            self.numeric_max[path] = max(self.numeric_max.get(path, 0.0), delta)
            if not np.isclose(left, right, atol=ATOL, rtol=RTOL):
                self._issue(path, f"numeric scalar exceeds tolerance (abs_delta={delta!r})", numeric=True)
            return
        self.exact_nodes[path] = self.exact_nodes.get(path, 0) + 1
        if left != right:
            self._issue(path, "exact value differs")


def safe_member(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe artifact path: {relative}")
    path = root / rel
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def index_arm(root: Path, seal: dict[str, Any], arm: str, expected_n: int) -> dict[str, dict[str, Any]]:
    ledger_path = root / "ledger.jsonl"
    if seal.get("files", {}).get("ledger.jsonl") != sha256_file(ledger_path):
        raise ValueError(f"ledger hash differs from seal: {root}")
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("arm") != arm:
            continue
        if row.get("status") != "ok":
            raise ValueError(f"non-ok {arm} row: {row.get('observation_id')}")
        stem = row.get("observation_id")
        if not isinstance(stem, str) or stem in selected:
            raise ValueError(f"invalid/duplicate observation id in {arm}: {stem}")
        rel = row.get("raw_path")
        raw_sha = row.get("raw_sha256")
        if not isinstance(rel, str) or not isinstance(raw_sha, str):
            raise ValueError(f"missing raw binding for {stem}/{arm}")
        if seal.get("files", {}).get(rel) != raw_sha:
            raise ValueError(f"ledger raw hash not equal to seal for {stem}/{arm}")
        selected[stem] = row
    if len(selected) != expected_n:
        raise ValueError(f"expected {expected_n} {arm} rows, found {len(selected)}")
    return selected


def compare_frame(old_payload: dict[str, Any], new_payload: dict[str, Any], stem: str) -> Comparison:
    result = Comparison()
    old_acq, new_acq = old_payload.get("acquisition"), new_payload.get("acquisition")
    if not isinstance(old_acq, dict) or not isinstance(new_acq, dict):
        result._issue("acquisition", "missing acquisition mapping")
    else:
        if set(old_acq) != set(new_acq):
            result._issue("acquisition", "acquisition key inventory differs")
        for field in REFERENCE_FIELDS:
            if field not in old_acq or field not in new_acq:
                result._issue(f"acquisition/{field}", "required reference field missing")
            else:
                result.compare(old_acq[field], new_acq[field], f"acquisition/{field}")
    for field in ("initial_geometry", "entering_geometry", "baseline_arrays"):
        if field not in old_payload or field not in new_payload:
            result._issue(field, "required raw payload field missing")
        else:
            result.compare(old_payload[field], new_payload[field], field)
    old_final = old_payload.get("final_decoded")
    new_final = new_payload.get("final_decoded")
    if not isinstance(old_final, np.ndarray) or not isinstance(new_final, np.ndarray):
        result._issue("final_decoded", "missing decoded array")
    else:
        result.exact_nodes["final_decoded"] = result.exact_nodes.get("final_decoded", 0) + 1
        if not np.array_equal(old_final, new_final):
            result._issue("final_decoded", "final decoded bits differ")
            result.final_bits_equal = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--stage-a", default="results/cstate_necessity_stageA_20260928/observed")
    parser.add_argument("--ccompat", default="results/cstate_necessity_stageB_resume_20260928/observed_f1_compat_v1")
    args = parser.parse_args()
    project = args.root.resolve(strict=True)
    stage_a_root = (project / args.stage_a).resolve(strict=True)
    ccompat_root = (project / args.ccompat).resolve(strict=True)
    if project not in stage_a_root.parents or project not in ccompat_root.parents:
        raise ValueError("observed roots escaped project root")

    stage_a_seal_path = stage_a_root / "observed_seal.json"
    ccompat_seal_path = ccompat_root / "observed_seal.json"
    stage_a_seal_sha = sha256_file(stage_a_seal_path)
    ccompat_seal_sha = sha256_file(ccompat_seal_path)
    stage_a_seal = read_json(stage_a_seal_path)
    ccompat_seal = read_json(ccompat_seal_path)
    integrity: list[str] = []
    for label, seal, actual_sha, expected_sha, registration_sha in (
        ("stage_a", stage_a_seal, stage_a_seal_sha, STAGE_A_SEAL_SHA256, STAGE_A_REGISTRATION_SHA256),
        ("ccompat", ccompat_seal, ccompat_seal_sha, CCOMPAT_SEAL_SHA256, CCOMPAT_REGISTRATION_SHA256),
    ):
        if actual_sha != expected_sha:
            integrity.append(f"{label} observed seal SHA differs from frozen value")
        if seal.get("status") != "pass" or seal.get("observations") != 1024:
            integrity.append(f"{label} seal status/count is not complete 1024")
        if seal.get("registration_sha256") != registration_sha:
            integrity.append(f"{label} registration SHA differs from frozen value")
    stage_a_rows = index_arm(stage_a_root, stage_a_seal, "C", 1024)
    ccompat_rows = index_arm(ccompat_root, ccompat_seal, "Ccompat", 1024)
    if set(stage_a_rows) != set(ccompat_rows):
        integrity.append("Stage-A C and Ccompat observation ID sets differ")
    expected_ids = {f"s650_f{i:04d}" for i in range(1024)}
    if set(stage_a_rows) != expected_ids or set(ccompat_rows) != expected_ids:
        integrity.append("one or both observed arm ID sets are not canonical s650_f0000..1023")

    numeric_max: dict[str, float] = {}
    numeric_nodes: dict[str, int] = {}
    exact_nodes: dict[str, int] = {}
    per_frame: list[dict[str, Any]] = []
    stage_a_bytes_hashed = 0
    ccompat_bytes_hashed = 0
    stage_a_raw_hash_matches = 0
    ccompat_raw_hash_matches = 0
    mismatch_ids: list[str] = []
    exact_pass_ids: list[str] = []
    numeric_pass_ids: list[str] = []
    final_bit_pass_ids: list[str] = []
    frames_compared = 0
    input_hash_equal_n = 0
    raw_hash_records: dict[str, list[tuple[str, str]]] = {"stage_a": [], "ccompat": []}

    for stem in sorted(set(stage_a_rows) & set(ccompat_rows)):
        old_row, new_row = stage_a_rows[stem], ccompat_rows[stem]
        if old_row.get("input_sha256") != new_row.get("input_sha256"):
            integrity.append(f"paired input SHA differs: {stem}")
        else:
            input_hash_equal_n += 1
        old_path = safe_member(stage_a_root, old_row["raw_path"])
        new_path = safe_member(ccompat_root, new_row["raw_path"])
        old_size, new_size = old_path.stat().st_size, new_path.stat().st_size
        stage_a_bytes_hashed += old_size
        ccompat_bytes_hashed += new_size
        old_hash, new_hash = sha256_file(old_path), sha256_file(new_path)
        if old_hash == old_row["raw_sha256"] == stage_a_seal["files"].get(old_row["raw_path"]):
            stage_a_raw_hash_matches += 1
        else:
            integrity.append(f"Stage-A raw SHA mismatch: {stem}")
        if new_hash == new_row["raw_sha256"] == ccompat_seal["files"].get(new_row["raw_path"]):
            ccompat_raw_hash_matches += 1
        else:
            integrity.append(f"Ccompat raw SHA mismatch: {stem}")
        raw_hash_records["stage_a"].append((stem, old_hash))
        raw_hash_records["ccompat"].append((stem, new_hash))

        old_payload, old_identity = load_evidence_npz(old_path)
        new_payload, new_identity = load_evidence_npz(new_path)
        for side, identity in (("stage_a", old_identity), ("ccompat", new_identity)):
            if "observation_id" in identity and identity["observation_id"] != stem:
                integrity.append(f"{side} NPZ identity mismatch: {stem}")
        result = compare_frame(old_payload, new_payload, stem)
        frames_compared += 1
        for field, value in result.numeric_max.items():
            numeric_max[field] = max(numeric_max.get(field, 0.0), value)
            numeric_nodes[field] = numeric_nodes.get(field, 0) + result.numeric_nodes[field]
        for field, count in result.exact_nodes.items():
            exact_nodes[field] = exact_nodes.get(field, 0) + count
        if result.issues:
            mismatch_ids.append(stem)
            per_frame.append({"observation_id": stem, "issues": result.issues})
        if not result.exact_issues:
            exact_pass_ids.append(stem)
        if not result.numeric_issues:
            numeric_pass_ids.append(stem)
        if result.final_bits_equal:
            final_bit_pass_ids.append(stem)

    status = "pass" if not integrity and not mismatch_ids and frames_compared == 1024 else "mismatch"
    def hash_record_rows(rows: list[tuple[str, str]]) -> str:
        return hashlib.sha256("".join(f"{stem}\t{digest}\n" for stem, digest in rows).encode()).hexdigest()

    result = {
        "schema": SCHEMA,
        "status": status,
        "n": 1024,
        "stage_a_observed_root": str(stage_a_root),
        "ccompat_observed_root": str(ccompat_root),
        "stage_a_observed_seal_sha256": stage_a_seal_sha,
        "ccompat_observed_seal_sha256": ccompat_seal_sha,
        "stage_a_registration_sha256": stage_a_seal.get("registration_sha256"),
        "ccompat_registration_sha256": ccompat_seal.get("registration_sha256"),
        "stage_a_ledger_sha256": sha256_file(stage_a_root / "ledger.jsonl"),
        "ccompat_ledger_sha256": sha256_file(ccompat_root / "ledger.jsonl"),
        "stage_a_raw_inventory_sha256": hash_record_rows(raw_hash_records["stage_a"]),
        "ccompat_raw_inventory_sha256": hash_record_rows(raw_hash_records["ccompat"]),
        "counts": {
            "frames_compared": frames_compared,
            "input_sha_equal_frames": input_hash_equal_n,
            "frames_exact_discrete_pass": len(exact_pass_ids),
            "frames_continuous_tolerance_pass": len(numeric_pass_ids),
            "frames_final_decoded_exact_pass": len(final_bit_pass_ids),
            "raw_files_rehashed_per_side": 1024,
            "stage_a_raw_hash_matches_seal": stage_a_raw_hash_matches,
            "ccompat_raw_hash_matches_seal": ccompat_raw_hash_matches,
        },
        "all_exact_discrete_pass": len(exact_pass_ids) == 1024,
        "all_within_tolerance_pass": len(numeric_pass_ids) == 1024,
        "all_final_decoded_exact_pass": len(final_bit_pass_ids) == 1024,
        "first_mismatch_observation_ids": mismatch_ids[:10],
        "mismatch_observation_ids": mismatch_ids,
        "mismatch_count": len(mismatch_ids),
        "integrity_errors": integrity,
        "per_frame_mismatch_details": per_frame[:20],
        "per_field_max_abs_delta": numeric_max,
        "per_field_numeric_node_count": numeric_nodes,
        "per_field_exact_node_count": exact_nodes,
        "bytes_read": {
            "stage_a_raw_npz": stage_a_bytes_hashed,
            "ccompat_raw_npz": ccompat_bytes_hashed,
            "compressed_npz_payload_total": stage_a_bytes_hashed + ccompat_bytes_hashed,
            "hash_then_npz_load_disk_read_estimate": 2 * (stage_a_bytes_hashed + ccompat_bytes_hashed),
        },
        "contract": {
            "continuous_atol": ATOL,
            "continuous_rtol": RTOL,
            "final_bits": "exact numpy.array_equal",
            "reference_fields": list(REFERENCE_FIELDS),
            "additional_raw_fields": ["initial_geometry", "entering_geometry", "baseline_arrays"],
        },
        "source_contract": {
            "stage_b_comparator": "experiments/cstate_necessity_stageB_20260928/f1_run_stage_b.py:39-41,154-178",
            "stage_a_compare_saved": "experiments/cstate_necessity_stageA_20260928/run_stage_a.py:72-101",
            "evidence_npz_envelope": "experiments/cstate_necessity_stageA_20260928/verify_stage_a.py:108-141",
            "stage_b_source_sha256": "fc1ed8087533f916d5892764f1a04d15168bf52c37ec4f83178de773ab7c1566",
            "stage_a_source_sha256": "6f6ae9eb7490a352fb5ac63b9844733e1873b1a7f969c6f08a060e8bb1faff17",
        },
        "receiver_calls": 0,
        "decoder_calls": 0,
        "truth_reads": 0,
        "integrity_failure_count": len(integrity),
    }
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
