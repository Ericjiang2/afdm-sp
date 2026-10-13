"""Small shared identity, pairing and serialization contract for this ticket."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SCHEMA = "spafdm-native-joint-compact/1"
RUNNER_FILES = ("plan.json", "common.py", "run.py", "run_stage.sh")


def attach(source, baseline):
    source, baseline = Path(source).resolve(), Path(baseline).resolve()
    sys.path[:0] = [str(source / "src"), str(baseline / "src"),
                    str(baseline / "upstream" / "spafdm_receiver_handoff")]
    import evidence
    return evidence


def plan():
    value = json.loads(Path(__file__).with_name("plan.json").read_text())
    if value.get("schema") != "spafdm-native-joint-campaign/1":
        raise ValueError("campaign plan schema differs")
    if value["stage_a"]["receiver_calls"] != 70 or value["stage_b"]["receiver_calls"] != 112:
        raise ValueError("campaign call budget differs")
    return value


def script_hashes():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in RUNNER_FILES}


def expected(stage, decision=None):
    cfg = plan()
    if stage == "A":
        for frame in range(12):
            arms = list(cfg["stage_a"]["all_12"])
            if frame < 6:
                arms += cfg["stage_a"]["first_6"]
            if frame < 4:
                arms += cfg["stage_a"]["first_4"]
            for arm in arms:
                yield 650, frame, arm
    elif stage == "B":
        if decision is None or decision.get("decision") != "advance":
            raise ValueError("Stage B requires a passing fixed Stage A gate")
        selected = decision["selected_ep"]
        for cell in cfg["stage_b"]["cells"]:
            snr = cell["snr_centi_db"]
            for frame in range(cell["frames"]):
                arms = ["TF_J20_R2", selected]
                if snr == 650 and frame < 8:
                    arms += cfg["stage_b"]["extra_first_8_at_650"]
                for arm in arms:
                    yield snr, frame, arm
    else:
        raise ValueError("stage must be A or B")


def entropy(stage, snr_centi, frame, component):
    if stage == "A":
        if snr_centi != 650 or not 0 <= frame < 12:
            raise ValueError("Stage A seed coordinate differs")
        return [20260921, 940317, 0, frame, component]
    if stage == "B":
        if (snr_centi, frame) not in ({(650, j) for j in range(32)} |
                                      {(800, j) for j in range(16)}):
            raise ValueError("Stage B seed coordinate differs")
        return [20260921, 940317, 1, snr_centi, frame, component]
    raise ValueError("invalid stage")


def seed_descriptor(stage, snr_centi, frame):
    component = {"message": 0, "channel": 1, "noise": 2}
    tuples = {name: entropy(stage, snr_centi, frame, value)
              for name, value in component.items()}
    channel_seed = int(np.random.default_rng(np.random.SeedSequence(
        tuples["channel"])).integers(0, 2**31))
    return {"stage": stage, "snr_centi_db": snr_centi, "frame": frame,
            "entropy": tuples, "channel_seed": channel_seed,
            "baseline_make_frame_component_map": {"1": 1, "2": 0, "3": 2}}


def historical_channel_seeds():
    result = set()
    for index in range(20):
        result.add(int(np.random.default_rng(np.random.SeedSequence(
            [20260921, 935170, index, 1])).integers(0, 2**31)))
    for index in range(1, 9):
        result.add(int(np.random.default_rng(np.random.SeedSequence(
            [20260921, 935171, index, 1])).integers(0, 2**31)))
    return result


def bits(value):
    array = np.asarray(value)
    if array.ndim != 1 or not np.isin(array, [0, 1]).all():
        raise ValueError("binary vector required")
    return {"length": int(array.size), "packed": np.packbits(array.astype(np.uint8))}


def unbits(value, length=None):
    if not isinstance(value, dict) or type(value.get("length")) is not int:
        raise ValueError("invalid packed bits")
    raw = np.asarray(value.get("packed"))
    count = value["length"]
    if (count < 0 or raw.dtype != np.uint8 or raw.ndim != 1
            or raw.size != (count + 7) // 8 or (length is not None and count != length)):
        raise ValueError("packed bit length differs")
    unpacked = np.unpackbits(raw)
    if np.any(unpacked[count:] != 0):
        raise ValueError("nonzero packed padding")
    return unpacked[:count].copy()


def array_hash(value):
    value = np.asarray(value)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode())
    digest.update(json.dumps(value.shape).encode())
    digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def observation_hash(observation):
    return hashlib.sha256("|".join(array_hash(observation[name])
             for name in ("y", "pilot", "sigma2")).encode()).hexdigest()


def finite_seconds(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite nonnegative seconds")
    return float(value)


def append_jsonl(path, item):
    with Path(path).open("a") as handle:
        handle.write(json.dumps(item, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def identity(run_hash, kind, snr_centi, frame, arm=None, round_index=None):
    value = {"schema": SCHEMA, "run_identity_sha256": run_hash,
             "kind": kind, "snr_centi_db": snr_centi, "frame": frame}
    if arm is not None:
        value["arm"] = arm
    if round_index is not None:
        value["round"] = round_index
    return value


def byte_count(path):
    return sum(item.stat().st_size for item in Path(path).rglob("*") if item.is_file())
