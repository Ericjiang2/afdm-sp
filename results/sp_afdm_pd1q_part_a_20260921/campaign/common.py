"""Fixed Part-A allocation and evidence identity; observations come from E1 D."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

SCHEMA = "spafdm-pd1q-parta-compact/1"
RUNNER_FILES = ("plan.json", "common.py", "run.py", "controls.py", "run_stage.sh")


def attach(source, baseline):
    source, baseline = Path(source).resolve(), Path(baseline).resolve()
    sys.path[:0] = [str(source / "src"), str(baseline / "src"),
                    str(baseline / "upstream" / "spafdm_receiver_handoff")]
    import evidence
    return evidence


def plan():
    value = json.loads(Path(__file__).with_name("plan.json").read_text())
    if value["schema"] != "spafdm-pd1q-parta-plan/1":
        raise ValueError("Part A plan schema differs")
    if len(list(expected(value))) != 91 or value["memory_receiver_calls"] != 8:
        raise ValueError("Part A receiver budget differs")
    return value


def expected(cfg):
    for snr in cfg["cells"]:
        for frame in range(16):
            if frame == 0:
                yield snr, frame, "TF_REPLAY"
            if frame >= 8:
                yield snr, frame, "TF_POINT20_R2"
            yield snr, frame, "TF_FIXED20_R2"
            if snr == 650 and frame < 8:
                yield snr, frame, "TF_NO_FEEDBACK20_R2"
                yield snr, frame, "TF_NO_GEOMETRY20_R2"


def script_hashes():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in RUNNER_FILES}


def bits(value):
    array = np.asarray(value)
    if array.ndim != 1 or not np.isin(array, [0, 1]).all():
        raise ValueError("binary vector required")
    return {"length": int(array.size), "packed": np.packbits(array.astype(np.uint8))}


def unbits(value, length=None):
    raw = np.asarray(value["packed"])
    count = value["length"]
    if (type(count) is not int or count < 0 or raw.dtype != np.uint8 or raw.ndim != 1
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
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
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
