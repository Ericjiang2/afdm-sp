"""Compact, independently validated evidence for the bounded staged campaign.

This schema deliberately differs from the frozen full-array run schema. It uses that
package's numeric NPZ serialization and source hashing, but never calls its full-raw
validator or confirmation/seal machinery.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


SCHEMA = "sp-afdm-staged-compact-v1"
ARM_STATUS = {"ok", "numerical_failure"}


def attach_source(source_root):
    import sys

    root = Path(source_root).resolve()
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "upstream" / "spafdm_receiver_handoff"))
    import evidence
    return evidence


def plan_path():
    return Path(__file__).with_name("plan.json")


def load_plan():
    plan = json.loads(plan_path().read_text())
    if plan.get("schema") != "sp-afdm-staged-plan-v1":
        raise ValueError("unsupported staged plan")
    stage1 = plan["stage1"]
    stage2 = plan["stage2"]
    if (len(stage1["arms"]) != 13 or len(stage1["cells"]) != 2
            or stage1["frames_per_cell"] != 10 or stage2["frames_per_cell"] != 32
            or stage1["max_receiver_calls"] != 260 or stage2["max_receiver_calls"] != 320
            or plan["confirmation_allowed"] is not False):
        raise ValueError("staged plan exceeds frozen bounds")
    return plan


def campaign_hashes():
    from hashlib import sha256

    names = ("plan.json", "compact.py", "run_stage.py", "select_stage.py", "verify_stage.py",
             "run_stage.sh")
    root = Path(__file__).parent
    return {name: sha256((root / name).read_bytes()).hexdigest() for name in names}


def pack_bits(bits):
    vector = np.asarray(bits)
    if vector.ndim != 1 or not np.isin(vector, [0, 1]).all():
        raise ValueError("only one-dimensional binary evidence can be packed")
    return {"length": int(vector.size), "bytes": np.packbits(vector.astype(np.uint8))}


def unpack_bits(packed):
    if not isinstance(packed, dict) or type(packed.get("length")) is not int:
        raise ValueError("invalid packed-bit descriptor")
    length = packed["length"]
    raw = np.asarray(packed.get("bytes"))
    if length < 0 or raw.dtype != np.uint8 or raw.ndim != 1 or len(raw) != (length + 7) // 8:
        raise ValueError("packed-bit byte count differs")
    values = np.unpackbits(raw)
    if np.any(values[length:] != 0):
        raise ValueError("nonzero packed-bit padding")
    return values[:length].copy()


def array_hash(value):
    value = np.asarray(value)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode())
    digest.update(json.dumps(value.shape).encode())
    digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def observed_hash(observed):
    digest = hashlib.sha256()
    for name in ("y", "pilot", "sigma2"):
        digest.update(name.encode())
        digest.update(array_hash(observed[name]).encode())
    return digest.hexdigest()


def finite_seconds(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return float(value)


def validate_timeline(timeline, complete_seconds):
    if not isinstance(timeline, list):
        raise ValueError("decision timeline must be a list")
    previous = 0.0
    for item in timeline:
        if not isinstance(item, dict):
            raise ValueError("decision checkpoint must be an object")
        elapsed = finite_seconds(item.get("elapsed"), "checkpoint elapsed")
        if elapsed < previous or elapsed > complete_seconds + 1e-9:
            raise ValueError("decision timeline is out of order or after complete time")
        if type(item.get("info_errors")) is not int or not 0 <= item["info_errors"] <= 1024:
            raise ValueError("checkpoint information-bit errors are invalid")
        previous = elapsed
    return timeline


def process_memory_kib():
    result = {"rss_kib": None, "high_water_kib": None}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            result["rss_kib"] = int(line.split()[1])
        elif line.startswith("VmHWM:"):
            result["high_water_kib"] = int(line.split()[1])
    return result


def append_jsonl(path, row):
    with Path(path).open("a") as handle:
        handle.write(json.dumps(row, allow_nan=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def compact_events(events):
    """Keep only scalar event metadata; the fixed audit retains full traces."""
    def scalar(value):
        if isinstance(value, np.generic):
            value = value.item()
        return value if value is None or isinstance(value, (str, int, float, bool)) else None

    result = []
    for event in events:
        if not isinstance(event, dict):
            continue
        item = {key: scalar(value) for key, value in event.items()}
        item = {key: value for key, value in item.items() if value is not None}
        if "events" in event:
            item["events"] = compact_events(event["events"])
        if "metadata" in event and isinstance(event["metadata"], dict):
            item["metadata"] = {key: scalar(value) for key, value in event["metadata"].items()
                                if scalar(value) is not None}
        result.append(item)
    return result


def directory_bytes(path):
    return sum(item.stat().st_size for item in Path(path).rglob("*") if item.is_file())


def artifact_identity(run_hash, kind, cell, frame, arm=None):
    value = {"schema": SCHEMA, "run_identity_sha256": run_hash,
             "kind": kind, "cell": cell, "absolute_frame": frame}
    if arm is not None:
        value["arm"] = arm
    return value


def expected_coordinates(manifest):
    return [(cell["id"], frame, arm)
            for cell in manifest["cells"]
            for frame in manifest["absolute_frames"]
            for arm in manifest["arms"]]


def validate_manifest(manifest, plan, source_root, evidence):
    if manifest.get("schema") != SCHEMA or manifest.get("phase") != "development":
        raise ValueError("invalid compact manifest schema/phase")
    stage = manifest.get("stage")
    if stage not in (1, 2):
        raise ValueError("invalid compact stage")
    contract = plan[f"stage{stage}"]
    if manifest.get("plan_sha256") != evidence.artifact_sha256(plan_path()):
        raise ValueError("plan hash differs")
    if manifest.get("campaign_hashes") != campaign_hashes():
        raise ValueError("campaign runner hashes differ")
    if manifest.get("receiver_commit") != plan["receiver_commit"]:
        raise ValueError("receiver commit differs")
    if manifest.get("receiver_source_hashes") != evidence.source_hashes(source_root):
        raise ValueError("frozen receiver source hashes differ")
    if manifest.get("seed_contract") != evidence.seed_contract(1):
        raise ValueError("stage seed contract differs")
    frames = list(range(contract["first_absolute_frame"],
                        contract["first_absolute_frame"] + contract["frames_per_cell"]))
    if manifest.get("absolute_frames") != frames:
        raise ValueError("stage frame coordinates differ")
    cells = manifest.get("cells")
    arms = manifest.get("arms")
    if stage == 1:
        if cells != contract["cells"] or arms != contract["arms"]:
            raise ValueError("Stage 1 cells/arms differ from frozen plan")
        if manifest.get("selection_gate_sha256") is not None:
            raise ValueError("Stage 1 cannot bind a selection gate")
    else:
        if not isinstance(cells, list) or not cells or len(cells) > contract["max_cells"]:
            raise ValueError("Stage 2 cell count exceeds gate")
        if not isinstance(arms, list) or len(arms) > contract["max_arms"]:
            raise ValueError("Stage 2 arm count exceeds gate")
        gate_path = manifest.get("selection_gate_path")
        if not isinstance(gate_path, str) or not isinstance(manifest.get("selection_gate_sha256"), str):
            raise ValueError("Stage 2 lacks frozen Stage 1 gate")
        from select_stage import build_gate

        gate_file = Path(gate_path)
        gate = json.loads(gate_file.read_text())
        if evidence.artifact_sha256(gate_file) != manifest["selection_gate_sha256"]:
            raise ValueError("Stage 2 gate hash differs")
        if gate != build_gate(gate["source_run_dir"], source_root) or gate["decision"] != "advance":
            raise ValueError("Stage 2 gate no longer validates against Stage 1")
        if cells != gate["stage2_cells"] or arms != gate["stage2_arms"]:
            raise ValueError("Stage 2 coordinates differ from fixed gate")
        old = json.loads((Path(gate["source_run_dir"]) / "manifest.json").read_text())
        if old["receiver_source_hashes"] != manifest["receiver_source_hashes"]:
            raise ValueError("Stage 1 and Stage 2 receiver sources differ")
    if len(expected_coordinates(manifest)) > contract["max_receiver_calls"]:
        raise ValueError("campaign call count exceeds frozen limit")
    catalog = json.loads((Path(source_root) / "protocol" / "configurations.json").read_text())
    if any(arm not in catalog for arm in arms):
        raise ValueError("unregistered campaign arm")
    if manifest.get("configurations") != {arm: catalog[arm] for arm in arms}:
        raise ValueError("catalog configuration differs")
    if manifest.get("heavy_cap_bytes") != plan["heavy_cap_bytes"]:
        raise ValueError("heavy storage cap differs")
    evidence.validate_environment(manifest.get("environment", {}))
    if manifest.get("selection_gate_path") is not None and stage == 1:
        raise ValueError("Stage 1 cannot bind a gate path")
    return manifest


def _record_payload(run_dir, row, manifest, evidence, run_hash):
    cell, frame, arm = row["cell"], row["absolute_frame"], row["arm"]
    path = Path(run_dir) / "compact" / f"c{cell:02d}_f{frame:06d}_{arm}.npz"
    expected = artifact_identity(run_hash, "arm", cell, frame, arm)
    payload, _ = evidence.load_artifact(path, expected)
    if evidence.artifact_sha256(path) != row.get("artifact_sha256"):
        raise ValueError("compact arm artifact hash differs")
    if payload.get("status") != row.get("status"):
        raise ValueError("compact arm status differs")
    return payload


def validate_run(run_dir, source_root, *, require_complete=False):
    """Validate compact identity, paired coordinates, hashes and all saved bits."""
    evidence = attach_source(source_root)
    plan = load_plan()
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    validate_manifest(manifest, plan, source_root, evidence)
    identity = {key: value for key, value in manifest.items() if key != "header"}
    run_hash = evidence.canonical_hash(identity)
    expected = set(expected_coordinates(manifest))
    rows = [json.loads(line) for line in (run_dir / "ledger.jsonl").read_text().splitlines()
            if line.strip()] if (run_dir / "ledger.jsonl").exists() else []
    index = {}
    frame_cache = {}
    all_seeds = set()
    if manifest["stage"] == 2:
        gate = json.loads(Path(manifest["selection_gate_path"]).read_text())
        all_seeds.update(gate["stage1_channel_seeds"])
    from afdm_sp_joint_unrolled.e1_ldpc import build_code, extract_info

    code = build_code(2048, d_v=3, d_c=6, seed=20260726)
    for row in rows:
        key = (row.get("cell"), row.get("absolute_frame"), row.get("arm"))
        if key not in expected or key in index:
            raise ValueError(f"extra or duplicate compact record: {key}")
        if row.get("status") not in ARM_STATUS:
            raise ValueError(f"invalid compact status: {key}")
        finite_seconds(row.get("seconds"), f"complete seconds {key}")
        validate_timeline(row.get("timeline"), row["seconds"])
        for field in ("front_seconds", "refit_seconds", "detector_seconds", "decoder_seconds",
                      "instrumentation_seconds", "failed_round_seconds", "scoring_storage_seconds"):
            if row.get(field) is not None:
                finite_seconds(row[field], f"{field} {key}")
        if row.get("status") == "ok":
            completed = sum(row.get(field) or 0 for field in
                            ("front_seconds", "refit_seconds", "detector_seconds",
                             "decoder_seconds", "instrumentation_seconds", "failed_round_seconds"))
            if completed > row["seconds"] + max(0.05, row["seconds"] * 0.05):
                raise ValueError(f"stage times exceed complete time: {key}")
        if row.get("input_hash") is None or row.get("truth_sha256") is None:
            raise ValueError(f"missing paired input/truth binding: {key}")
        frame_key = key[:2]
        if frame_key not in frame_cache:
            cell, frame = frame_key
            path = run_dir / "compact" / f"c{cell:02d}_f{frame:06d}_truth.npz"
            truth, _ = evidence.load_artifact(path, artifact_identity(run_hash, "truth", cell, frame))
            seed = evidence.frame_seed_descriptor(manifest["seed_contract"], cell, frame)
            if truth.get("seed") != seed or seed["channel_seed"] in all_seeds:
                raise ValueError("frame seed differs or repeats")
            all_seeds.add(seed["channel_seed"])
            info, coded = unpack_bits(truth["info"]), unpack_bits(truth["coded"])
            if len(info) != 1024 or len(coded) != 2048:
                raise ValueError("truth bit lengths differ")
            frame_cache[frame_key] = (truth, info, coded, evidence.artifact_sha256(path))
        truth, info, coded, truth_hash = frame_cache[frame_key]
        if row["truth_sha256"] != truth_hash or row["input_hash"] != truth["input_hash"]:
            raise ValueError("paired frame hash differs")
        payload = _record_payload(run_dir, row, manifest, evidence, run_hash)
        audit = key[1] == manifest["audit_absolute_frame"]
        if row["status"] == "ok" and audit and row.get("heavy_sha256") is None:
            raise ValueError("predesignated audit arm lacks heavy evidence")
        if row["status"] == "numerical_failure":
            exception = run_dir / "heavy" / f"c{key[0]:02d}_f{key[1]:06d}_{key[2]}_exception.json"
            if not exception.exists() or evidence.artifact_sha256(exception) != row.get("exception_sha256"):
                raise ValueError("numerical failure exception evidence hash differs")
        if row.get("heavy_sha256") is not None:
            heavy = run_dir / "heavy" / f"c{key[0]:02d}_f{key[1]:06d}_{key[2]}.npz"
            heavy_payload, _ = evidence.load_artifact(
                heavy, artifact_identity(run_hash, "heavy_arm", *key))
            if evidence.artifact_sha256(heavy) != row["heavy_sha256"]:
                raise ValueError("heavy arm hash differs")
            if row["status"] == "ok" and not np.array_equal(
                    np.asarray(heavy_payload["decoded"]), unpack_bits(payload["decoded"])):
                raise ValueError("heavy and compact decoded bits differ")
        if row["status"] == "ok":
            decoded = unpack_bits(payload["decoded"])
            if len(decoded) != len(coded):
                raise ValueError("decoded length differs")
            info_hat = extract_info(code, decoded)
            info_errors = int(np.count_nonzero(info_hat != info))
            coded_errors = int(np.count_nonzero(decoded != coded))
            if row.get("info_errors") != info_errors or row.get("coded_errors") != coded_errors:
                raise ValueError("saved bit error recount differs")
            if len(payload["checkpoints"]) != len(row.get("timeline", [])):
                raise ValueError("checkpoint count differs")
            for item, ledger_item in zip(payload["checkpoints"], row["timeline"]):
                checkpoint = unpack_bits(item["decoded"])
                if len(checkpoint) != len(coded):
                    raise ValueError("checkpoint bit length differs")
                if (item["elapsed"] != ledger_item["elapsed"]
                        or int(np.count_nonzero(extract_info(code, checkpoint) != info)) != ledger_item["info_errors"]):
                    raise ValueError("checkpoint recount differs")
        else:
            if payload.get("decoded") is not None or row.get("info_errors") is not None:
                raise ValueError("failed arm invented decoded bits")
        index[key] = row
    pending = expected - set(index)
    for (cell, frame), (truth, _, _, _) in frame_cache.items():
        if frame != manifest["audit_absolute_frame"]:
            continue
        for kind in ("input", "truth"):
            path = run_dir / "heavy" / f"c{cell:02d}_f{frame:06d}_{kind}.npz"
            heavy_payload, _ = evidence.load_artifact(
                path, artifact_identity(run_hash, f"heavy_{kind}", cell, frame))
            if kind == "input" and observed_hash(heavy_payload) != truth["input_hash"]:
                raise ValueError("heavy and compact observed input differ")
            if kind == "truth" and any(not np.array_equal(
                    np.asarray(heavy_payload[name]), unpack_bits(truth[name]))
                    for name in ("info", "coded")):
                raise ValueError("heavy and compact truth bits differ")
    if directory_bytes(run_dir) >= manifest["heavy_cap_bytes"]:
        raise ValueError("compact storage exceeded frozen cap")
    if require_complete and pending:
        raise ValueError(f"incomplete compact run: {len(pending)} pending")
    return {"manifest": manifest, "records": rows, "index": index,
            "pending": sorted(pending), "run_identity_sha256": run_hash,
            "frame_cache": frame_cache}
