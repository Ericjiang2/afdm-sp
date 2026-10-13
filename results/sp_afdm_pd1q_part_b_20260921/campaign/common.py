"""Small shared identity, pairing and serialization contract for this ticket."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np


SCHEMA = "spafdm-pd1q-partb-compact/1"
RUNNER_FILES = ("plan.json", "common.py", "preflight.py", "run.py", "verify.py",
                "recount.py", "run_chain.sh", "inventory.py", "analyze.py")


def attach(source, baseline):
    source, baseline = Path(source).resolve(), Path(baseline).resolve()
    sys.path[:0] = [str(source / "src"), str(baseline / "src"),
                    str(baseline / "upstream" / "spafdm_receiver_handoff")]
    import evidence
    return evidence


def plan():
    value = json.loads(Path(__file__).with_name("plan.json").read_text())
    if value.get("schema") != "spafdm-pd1q-partb-plan/1":
        raise ValueError("Part B plan schema differs")
    if (value["cells"] != [600, 650, 700] or value["frames_per_cell"] != 1024
            or value["point_first_n"] != 128 or value["pbi_first_n"] != 32
            or value["total_observations"] != 3072
            or value["total_receiver_calls"] != 9696
            or len(list(expected(value))) != 9696):
        raise ValueError("Part B fixed allocation differs")
    return value


def script_hashes():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in RUNNER_FILES}


def expected(cfg=None):
    if cfg is None:
        cfg = plan()
    cells = cfg["cells"]
    for frame in range(cfg["frames_per_cell"]):
        for cell_index in [(frame + shift) % len(cells) for shift in range(len(cells))]:
            snr = cells[cell_index]
            arms = list(cfg["primary_arms"])
            if frame < cfg["point_first_n"]:
                arms.append("TF_POINT20_R2")
            if frame < cfg["pbi_first_n"]:
                arms.append("PBI8_SOFT_R2")
            offset = (frame + cell_index) % len(arms)
            for arm in arms[offset:] + arms[:offset]:
                yield snr, frame, arm


def entropy(snr_centi, frame, component):
    if snr_centi not in (600, 650, 700) or not 0 <= frame < 1024 or component not in (0, 1, 2):
        raise ValueError("Part B seed coordinate differs")
    return [20260921, 941001, 0, snr_centi, frame, component]


def seed_descriptor(snr_centi, frame):
    component = {"message": 0, "channel": 1, "noise": 2}
    tuples = {name: entropy(snr_centi, frame, value)
              for name, value in component.items()}
    channel_seed = int(np.random.default_rng(np.random.SeedSequence(
        tuples["channel"])).integers(0, 2**31))
    return {"stage": "PartB", "snr_centi_db": snr_centi, "frame": frame,
            "entropy": tuples, "channel_seed": channel_seed,
            "baseline_make_frame_component_map": {"1": 1, "2": 0, "3": 2}}


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
