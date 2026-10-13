"""Fail-closed identities and file contracts for the frozen CGR prospective study."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import numpy as np


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
RESULT = PROJECT / "results/tf_cgr_prospective_mechanism_20260923"
TASK_PROTOCOL = PROJECT / ".trellis/tasks/09-22-tf-production-gap-audit/cgr-prospective-mechanism.md"
SCHEMA = "tf-cgr-prospective-mechanism/1"
DOMAIN = 0x43475250  # "CGRP", separate from older CSTA and frozen streams.
SNR_CENTI_DB = 650
FRAMES = 256
ARMS = ("BASE", "CGR", "SHAM")
COMPONENTS = {"channel": 1, "message": 2, "noise": 3, "schedule": 4}
DATA_CAP = 8 * 1024**3
SECONDS = {"generation": 900, "base": 900, "prediction": 600,
           "interventions": 1800}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def append_jsonl(path: Path, value: object) -> None:
    with Path(path).open("a") as stream:
        stream.write(canonical(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def size(*roots: Path) -> int:
    return sum(file.stat().st_size for root in roots for file in root.rglob("*")
               if file.is_file())


def frame_id(index: int) -> str:
    if type(index) is not int or not 0 <= index < FRAMES:
        raise ValueError("frame index outside registered allocation")
    return f"cgrp_s650_f{index:04d}"


def seed_words(entropy_hex: str, frame: int, component: int) -> list[int]:
    if (re.fullmatch(r"[0-9a-f]{64}", entropy_hex) is None or
            type(frame) is not int or not 0 <= frame < FRAMES or
            component not in COMPONENTS.values()):
        raise ValueError("unregistered random stream coordinate")
    words = np.frombuffer(bytes.fromhex(entropy_hex), dtype="<u4")
    return [int(word) for word in words] + [DOMAIN, SNR_CENTI_DB, frame, component]


def stream_ids(entropy_hex: str, frame: int) -> dict[str, str]:
    return {name: canonical_hash(seed_words(entropy_hex, frame, component))
            for name, component in COMPONENTS.items() if name != "schedule"}


def order(entropy_hex: str) -> list[dict]:
    # One registered schedule stream: a random permutation fixes which 128
    # frame indices are CGR-first, without reference to any observed outcome.
    random = np.random.default_rng(np.random.SeedSequence(seed_words(
        entropy_hex, 0, COMPONENTS["schedule"])))
    first = set(int(index) for index in random.permutation(FRAMES)[: FRAMES // 2])
    return [dict(frame=frame, arms=["CGR", "SHAM"] if frame in first
                 else ["SHAM", "CGR"]) for frame in range(FRAMES)]


def observation_hash(observation: dict) -> str:
    if set(observation) != {"y", "pilot", "sigma2"}:
        raise ValueError("observation fields differ")
    parts = []
    for key in ("y", "pilot", "sigma2"):
        value = np.asarray(observation[key])
        digest = hashlib.sha256()
        digest.update(str(value.dtype).encode())
        digest.update(json.dumps(value.shape).encode())
        digest.update(np.ascontiguousarray(value).tobytes())
        parts.append(digest.hexdigest())
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def source_files(source: Path, baseline: Path) -> dict[str, Path]:
    """Exact executable identity, including old reviewed dependencies."""
    files: dict[str, Path] = {}
    for label, root in (("native", source), ("baseline", baseline)):
        for folder in ("src", "upstream"):
            for path in sorted((root / folder).rglob("*.py")):
                if "__pycache__" not in path.parts and path.name != "block_bilinear.py":
                    files[f"{label}/{path.relative_to(root)}"] = path
    files["code_cache"] = (baseline / "upstream/spafdm_receiver_handoff/"
                            "afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    for directory in ("tf_production_gap_audit_20260922", "tf_cstate_validation_20260922",
                      "tf_geometry_reopen_20260922"):
        for path in sorted((PROJECT / "experiments" / directory).glob("*.py")):
            files[f"support/{directory}/{path.name}"] = path
    for name in ("tf_base.py", "tf_cgr.py", "tf_sham.py", "generate_variants.py"):
        files[f"reviewed_cgr/{name}"] = (PROJECT / "experiments/tf_cgr_mechanism_20260923_v2" / name)
    for name in ("tangent.py", "test_tangent.py"):
        files[f"reviewed_jvp/{name}"] = (PROJECT / "experiments/tf_cgr_offline_mechanism_20260923" / name)
    # Production/admission code freezes before intervention. The later truth
    # reader is separately source-bound in its analysis receipt.
    for name in ("common.py", "branch.py", "freeze_registration.py", "generate.py",
                 "attest.py", "run_phase.py", "predict.py", "finalize.py",
                 "test_campaign.py"):
        files[f"campaign/{name}"] = HERE / name
    return files


def check_sources(source: Path, baseline: Path, expected: dict[str, str]) -> None:
    files = source_files(source, baseline)
    actual = {name: sha256(path) for name, path in files.items()}
    if actual != expected:
        changed = sorted(set(actual) ^ set(expected) |
                         {name for name in set(actual) & set(expected)
                          if actual[name] != expected[name]})
        raise ValueError(f"frozen source inventory differs: {changed[:8]}")


def registration(path: Path, source: Path, baseline: Path) -> dict:
    value = json.loads(Path(path).read_text())
    namespace = path.parent / "random_namespace.json"
    bindings = path.parent / "source_bindings.json"
    if (value.get("schema") != SCHEMA or value.get("status") != "locked" or
            value.get("protocol_sha256") != sha256(TASK_PROTOCOL) or
            value.get("namespace_sha256") != sha256(namespace) or
            value.get("source_bindings_sha256") != sha256(bindings) or
            value.get("population") != dict(snr_centi_db=SNR_CENTI_DB, frames=FRAMES) or
            value.get("arms") != list(ARMS) or
            value.get("domain") != DOMAIN):
        raise ValueError("frozen CGR prospective registration differs")
    lock = json.loads(namespace.read_text())
    entropy = lock.get("entropy_hex")
    if (lock.get("schema") != SCHEMA or lock.get("domain") != DOMAIN or
            lock.get("campaign") != "tf_cgr_prospective_mechanism_20260923" or
            not isinstance(entropy, str) or
            re.fullmatch(r"[0-9a-f]{64}", entropy) is None or
            value.get("schedule") != order(entropy)):
        raise ValueError("fresh namespace/schedule differs")
    check_sources(source, baseline, json.loads(bindings.read_text()))
    return value


def git_blob(commit: str, relative: str, path: Path) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("full Git commit required")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError("unsafe Git blob path")
    repo = PROJECT.parent.parent
    got = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{rel.as_posix()}"],
                         capture_output=True, check=True).stdout
    if got != path.read_bytes():
        raise ValueError("committed Git blob differs from supplied file")


def git_ancestor(older: str, newer: str) -> None:
    if any(re.fullmatch(r"[0-9a-f]{40}", commit) is None for commit in (older, newer)):
        raise ValueError("full Git commits required")
    subprocess.run(["git", "-C", str(PROJECT.parent.parent), "merge-base", "--is-ancestor",
                    older, newer], check=True)


def git_relative(path: Path) -> str:
    resolved = Path(path).resolve()
    repo = PROJECT.parent.parent.resolve()
    if not resolved.is_relative_to(repo):
        raise ValueError("evidence file outside Git repository")
    return resolved.relative_to(repo).as_posix()


def seal(root: Path, name: str, fields: dict) -> Path:
    root = Path(root)
    path = root / name
    if path.exists():
        raise FileExistsError(path)
    files = {file.relative_to(root).as_posix(): sha256(file)
             for file in sorted(root.rglob("*")) if file.is_file()}
    write_json(path, dict(schema=SCHEMA, status="pass", **fields, files=files))
    verify_seal(root, name)
    return path


def verify_seal(root: Path, name: str) -> dict:
    root = Path(root)
    path = root / name
    saved = json.loads(path.read_text())
    actual = {file.relative_to(root).as_posix(): sha256(file)
              for file in sorted(root.rglob("*")) if file.is_file() and file != path}
    if saved.get("schema") != SCHEMA or saved.get("status") != "pass" or saved.get("files") != actual:
        raise ValueError(f"sealed file inventory differs: {root}")
    return saved
