"""Standalone reader for evidence NPZ files in the discovery pack.

Usage: python3 read_artifact.py tf_traces/s650_f0000.npz
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ARRAY = "__evidence_array__"
TUPLE = "__evidence_tuple__"
METADATA = "__evidence_metadata__"


def load(path: str | Path) -> tuple[object, dict]:
    with np.load(path, allow_pickle=False) as archive:
        raw = np.asarray(archive[METADATA])
        if raw.dtype != np.uint8 or raw.ndim != 1:
            raise ValueError("invalid evidence metadata")
        envelope = json.loads(raw.tobytes().decode("utf-8"))
        if envelope.get("format_version") != 2:
            raise ValueError("unsupported evidence format")
        used = set()

        def unpack(tree):
            if isinstance(tree, dict):
                if set(tree) == {ARRAY}:
                    key = tree[ARRAY]
                    used.add(key)
                    return np.asarray(archive[key]).copy()
                if set(tree) == {TUPLE}:
                    return tuple(unpack(item) for item in tree[TUPLE])
                return {key: unpack(item) for key, item in tree.items()}
            if isinstance(tree, list):
                return [unpack(item) for item in tree]
            return tree

        payload = unpack(envelope["payload"])
        if used != set(archive.files) - {METADATA}:
            raise ValueError("evidence array inventory differs")
        return payload, envelope["identity"]


if __name__ == "__main__":
    payload, identity = load(sys.argv[1])
    print(json.dumps({"identity": identity, "payload_keys": sorted(payload)}, indent=2))
