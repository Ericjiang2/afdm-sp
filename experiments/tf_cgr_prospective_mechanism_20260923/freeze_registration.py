"""Construct the one-time prospective namespace and reviewed source lock.

Run only after code review; commit all three files before any generation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets

import numpy as np

from common import (ARMS, DOMAIN, FRAMES, PROJECT, SCHEMA, SNR_CENTI_DB,
                    TASK_PROTOCOL, order, sha256, source_files, write_json)


OLD_REGISTRATION = (PROJECT / "results/tf_cstate_prospective_20260923/"
                    "registration/registration.json")


def freeze(source: Path, baseline: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError(out)
    old_entropy = None
    if OLD_REGISTRATION.exists():
        old = json.loads(OLD_REGISTRATION.read_text())
        old_entropy = old.get("streams", {}).get("entropy_hex")
    entropy = secrets.token_hex(32)
    if entropy == old_entropy:
        raise ValueError("random namespace collision")
    paths = source_files(source, baseline)
    hashes = {name: sha256(path) for name, path in paths.items()}
    with np.load(paths["code_cache"], allow_pickle=False) as code:
        G = np.asarray(code["G"])
        H = np.asarray(code["H"])
        free = np.asarray(code["free_cols"])
    if G.shape != (2048, 1024) or H.shape != (1026, 2048) or free.shape != (1024,):
        raise ValueError("frozen code cache shape differs")
    namespace = dict(schema=SCHEMA, campaign="tf_cgr_prospective_mechanism_20260923",
                     domain=DOMAIN, entropy_hex=entropy,
                     algorithm="numpy.SeedSequence(8 little-endian entropy uint32 + CGRP domain + 650 + frame + component)",
                     components=dict(channel=1, message=2, noise=3, schedule=4))
    out.mkdir(parents=True)
    write_json(out / "random_namespace.json", namespace)
    write_json(out / "source_bindings.json", hashes)
    lock = dict(schema=SCHEMA, status="locked", population=dict(snr_centi_db=SNR_CENTI_DB,
                     frames=FRAMES), arms=list(ARMS), domain=DOMAIN,
                schedule=order(entropy), analysis_seed=secrets.randbits(63),
                protocol_sha256=sha256(TASK_PROTOCOL),
                namespace_sha256=sha256(out / "random_namespace.json"),
                source_bindings_sha256=sha256(out / "source_bindings.json"),
                code_g_sha256=hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest(),
                code_cache_sha256=hashes["code_cache"],
                prior_campaign_attempts=101, new_attempt_cap=3 * FRAMES)
    write_json(out / "registration.json", lock)
    return lock


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(freeze(arguments.source, arguments.baseline, arguments.out),
                     sort_keys=True))
