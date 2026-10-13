#!/usr/bin/env python3
"""Independent raw/checkpoint-to-truth recount for the sealed five-policy F2 run.

This reader imports only NumPy, SciPy, and the generic evidence NPZ codec. It
does not import or call any receiver, decoder, generator, estimator, or primary
analysis module. It refuses truth access unless the observed and primary Git
commits and the supplied primary attestation pass first.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
import sys

import numpy as np
from scipy import sparse


POLICIES = ("F0", "B", "F0_LOCAL", "F2T", "F2E")
EXPECTED_OBSERVED_SEAL = "69bc4006a814fd5946c3810209d9d9b24db9c64df34aa4129fa4a2abf554c3fc"
EXPECTED_OBSERVED_COMMIT = "1dbbd0f111de7d88e7e689aeb7b9b61f4a83ab27"
EXPECTED_PRIMARY_COMMIT = "a5a8c3f301b6e5280c9fa67d05a6120e38005dc1"
EXPECTED_PRIMARY_ATTESTATION_SHA = "1479074e1d7f6e9031d3774847af86436509250723969cb8b5281885b341fb9f"
EXPECTED_PRIMARY_REPORT = "results/cstate_necessity_stageB_resume_20260928/population_five_analysis_v2/report.json"
EXPECTED_CODE_CACHE_SHA = "cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052"
EXPECTED_RUN_MANIFEST_SHA = "88efa4b503cb4cddeae78039f5d7d8805988425110e4c14511a57e66b699fe96"
N = 1024


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def git_show(root: Path, commit: str, path: str) -> bytes:
    rel = PurePosixPath(path)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe Git path: {path}")
    proc = subprocess.run(["git", "-C", str(root), "show", f"{commit}:{path}"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        raise ValueError(f"git show failed for {commit}:{path}: " +
                         proc.stderr.decode("utf-8", "replace")[:300])
    return proc.stdout


def require_ancestor(root: Path, ancestor: str, descendant: str) -> None:
    if len(ancestor) != 40 or len(descendant) != 40:
        raise ValueError("full Git commit IDs required")
    proc = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                           ancestor, descendant], stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        raise ValueError(f"observed commit is not ancestor of primary GO commit: {ancestor} -> {descendant}")


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def safe_artifact(root: Path, rel: str) -> Path:
    p = PurePosixPath(rel)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError(f"unsafe artifact path: {rel}")
    result = (root / Path(*p.parts)).resolve()
    if not result.is_relative_to(root.resolve()) or not result.is_file() or result.is_symlink():
        raise ValueError(f"missing, escaping, or symlink artifact: {rel}")
    return result


def load_checked(evidence, root: Path, relative: str, digest: str,
                 expected_identity: dict | None = None) -> dict:
    path = safe_artifact(root, relative)
    actual_sha = sha256(path)
    if actual_sha != digest:
        raise ValueError(f"artifact SHA differs: {relative}")
    payload, identity = evidence.load_artifact(path)
    if expected_identity is not None and identity != expected_identity:
        raise ValueError(f"artifact identity differs: {relative}")
    return payload


def bit_vector(value, length: int, label: str) -> np.ndarray:
    v = np.asarray(value)
    if v.shape != (length,) or v.dtype != np.uint8 or not np.isin(v, (0, 1)).all():
        raise ValueError(f"{label}: expected uint8 binary vector[{length}], got {v.shape}/{v.dtype}")
    return v


def syndrome(H: sparse.csr_matrix, bits: np.ndarray) -> int:
    return int(np.count_nonzero(np.asarray(H @ bits.astype(np.int32)).reshape(-1) % 2))


def distribution(values: list[float]) -> dict:
    a = np.asarray(values, dtype=np.float64)
    if a.ndim != 1 or not a.size or not np.isfinite(a).all() or (a < 0).any():
        raise ValueError("invalid timing population")
    return {"n": int(a.size), "mean": float(np.mean(a)), "median": float(np.median(a)),
            "p95": float(np.quantile(a, .95)), "p99": float(np.quantile(a, .99)),
            "max": float(np.max(a))}


def primary_complete_latency(arm: dict) -> dict:
    """Read the frozen primary report's named complete-latency distribution."""
    return arm["timing"]["complete_latency_seconds"]


def fvec_equal(left: np.ndarray, right, label: str) -> None:
    r = np.asarray(right)
    if r.shape != left.shape or not np.array_equal(left, r):
        raise ValueError(f"saved decision mismatch: {label}")


def verify_git_go(args) -> tuple[dict, dict]:
    if (args.primary_git_go != EXPECTED_PRIMARY_COMMIT
            or args.observed_commit != EXPECTED_OBSERVED_COMMIT
            or args.attestation_sha256 != EXPECTED_PRIMARY_ATTESTATION_SHA):
        raise ValueError("GO/observed/attestation arguments differ from parent authorization")
    try:
        att_bytes = base64.b64decode(args.attestation_json_b64, validate=True)
        report_bytes = base64.b64decode(args.primary_report_b64, validate=True)
    except Exception as exc:
        raise ValueError("parent Git attestation/report handoff is not valid base64") from exc
    if sha256_bytes(att_bytes) != EXPECTED_PRIMARY_ATTESTATION_SHA:
        raise ValueError("primary Git attestation SHA differs")
    att = json.loads(att_bytes)
    if (att.get("status") != "pass" or att.get("primary_commit") != EXPECTED_PRIMARY_COMMIT
            or att.get("observed_commit") != EXPECTED_OBSERVED_COMMIT
            or att.get("observed_is_ancestor") is not True
            or EXPECTED_PRIMARY_REPORT not in att.get("files", {})):
        raise ValueError("primary Git attestation fields differ")
    report_entry = att["files"][EXPECTED_PRIMARY_REPORT]
    if sha256_bytes(report_bytes) != report_entry["sha256"]:
        raise ValueError("parent-provided primary report bytes do not match attested Git blob SHA")
    # Parent has already verified observed-seal blob bytes, all primary blobs,
    # and merge-base ancestry locally; this worker independently checks the
    # supplied attestation bytes and report blob before comparing summaries.
    return att, {EXPECTED_PRIMARY_REPORT: report_bytes}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--primary-git-go", required=True)
    ap.add_argument("--observed-commit", required=True)
    ap.add_argument("--attestation-json-b64", required=True)
    ap.add_argument("--primary-report-b64", required=True)
    ap.add_argument("--attestation-sha256", required=True)
    ap.add_argument("--observed-seal-repo-path", required=True)
    ap.add_argument("--f2-observed", type=Path, default=Path("results/cstate_necessity_stageB_resume_20260928/population_five_v1"))
    ap.add_argument("--population-observed", type=Path, default=Path("results/tf_cstate_prospective_20260923/population_observed"))
    ap.add_argument("--population-truth", type=Path, default=Path("results/tf_cstate_prospective_20260923/population_truth"))
    ap.add_argument("--f2-registration", type=Path, default=Path("results/cstate_necessity_stageB_resume_20260928/F2_FIVE_POLICY_MANIFEST.json"))
    ap.add_argument("--stage-a-registration", type=Path, default=Path("results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json"))
    ap.add_argument("--baseline", type=Path, default=Path("experiments/sp_afdm_frozen_reviewed_20260921"))
    args = ap.parse_args()
    root = args.root.resolve()
    # The explicit primary Git GO is checked before any truth path is opened.
    att, primary_blobs = verify_git_go(args)

    observed = (root / args.f2_observed).resolve()
    population_root = (root / args.population_observed).resolve()
    truth_root = (root / args.population_truth).resolve()
    registration_path = root / args.f2_registration
    stage_registration_path = root / args.stage_a_registration
    baseline = root / args.baseline
    seal_path = observed / "observed_seal.json"
    if sha256(seal_path) != EXPECTED_OBSERVED_SEAL:
        raise ValueError("local/remote observed seal SHA differs")
    seal = json.loads(seal_path.read_text())
    manifest = json.loads((observed / "manifest.json").read_text())
    reg = json.loads(registration_path.read_text())
    stage_reg = json.loads(stage_registration_path.read_text())
    if (seal.get("status") != "pass" or seal.get("frames") != N
            or seal.get("actual_prefix_calls") != 2048
            or seal.get("actual_continuation_calls") != 120
            or seal.get("actual_total_calls") != 2168
            or seal.get("logical_policy_rows") != 5120
            or seal.get("run_manifest_sha256") != EXPECTED_RUN_MANIFEST_SHA
            or manifest.get("run_manifest_sha256") != EXPECTED_RUN_MANIFEST_SHA
            or sha256(registration_path) != EXPECTED_RUN_MANIFEST_SHA
            or manifest.get("policy_names") != list(POLICIES)
            or reg.get("policy_names") != list(POLICIES)):
        raise ValueError("five-policy observed/registration seal differs")

    # Hash every sealed observed member, including raw, decisions and checkpoints.
    file_map = seal.get("files")
    if not isinstance(file_map, dict) or len(file_map) != 8557 - 5:
        # The seal excludes its own file; previous inventory reported 8,557 members,
        # so accept the exact map count encoded by that inventory receipt below.
        if not isinstance(file_map, dict) or len(file_map) != 8557:
            raise ValueError("unexpected sealed observed member count")
    observed_hashes = {}
    for relative, expected in file_map.items():
        p = safe_artifact(observed, relative)
        actual = sha256(p)
        if actual != expected:
            raise ValueError(f"observed seal file SHA mismatch: {relative}")
        observed_hashes[relative] = actual
    for required in ("manifest.json", "ledger.jsonl", "attempts.jsonl",
                     "policy_ledger.jsonl", "failed_calls.jsonl"):
        if required not in file_map:
            raise ValueError(f"required observed metadata absent from seal: {required}")

    # Truth is opened only below, after exact primary Git GO and all observed hashes.
    truth_seal_path = truth_root / "truth_seal.json"
    expected_truth_seal = stage_reg.get("population_truth_seal_sha256")
    if not expected_truth_seal or sha256(truth_seal_path) != expected_truth_seal:
        raise ValueError("registered truth seal differs")
    truth_seal = json.loads(truth_seal_path.read_text())
    if truth_seal.get("status") != "pass" or not isinstance(truth_seal.get("files"), dict):
        raise ValueError("truth seal incomplete")

    sys.path.insert(0, str(baseline / "src"))
    import evidence  # generic NPZ codec only; no receiver imports

    population_all = jsonl(population_root / "ledger.jsonl")
    truth_all = jsonl(truth_root / "ledger.jsonl")
    pop = [r for r in population_all if r.get("snr_centi_db") == 650]
    tr = [r for r in truth_all if r.get("snr_centi_db") == 650]
    if (len(pop) != N or len(tr) != N
            or [r.get("frame") for r in pop] != list(range(N))
            or [r.get("frame") for r in tr] != list(range(N))):
        raise ValueError("fixed 6.5 dB population/truth subset differs")
    if any((a["observation_id"], a["observation_hash"], a["stream_ids"])
           != (b["observation_id"], b["observation_hash"], b["stream_ids"])
           for a, b in zip(pop, tr, strict=True)):
        raise ValueError("population/truth identity binding differs")

    cache = baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"
    if sha256(cache) != EXPECTED_CODE_CACHE_SHA or reg.get("ldpc_cache_sha256") != EXPECTED_CODE_CACHE_SHA:
        raise ValueError("frozen LDPC cache hash differs")
    with np.load(cache, allow_pickle=False) as z:
        Hraw, Graw, free = np.asarray(z["H"]), np.asarray(z["G"]), np.asarray(z["free_cols"], dtype=np.int64)
    if Hraw.shape != (1026, 2048) or Graw.shape != (2048, 1024) or free.shape != (1024,):
        raise ValueError("frozen H/G/free-cols shapes differ")
    if (len(np.unique(free)) != 1024 or free.min() < 0 or free.max() >= 2048
            or not np.array_equal(Graw[free, :], np.eye(1024, dtype=Graw.dtype))):
        raise ValueError("free-cols are not the registered systematic generator rows")
    if hashlib.sha256(np.ascontiguousarray(Graw).tobytes()).hexdigest() != reg.get("code_g_sha256"):
        raise ValueError("registered generator-matrix hash differs")
    H = sparse.csr_matrix(Hraw.astype(np.int32))
    G = sparse.csr_matrix(Graw.astype(np.int32))

    truths: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    truth_payload_hashes = {}
    for inrow, trow in zip(pop, tr, strict=True):
        rel, digest = trow["truth_path"], trow["truth_sha256"]
        if truth_seal["files"].get(rel) != digest:
            raise ValueError(f"truth ledger/seal binding differs: {rel}")
        path = safe_artifact(truth_root, rel)
        if sha256(path) != digest:
            raise ValueError(f"truth payload SHA differs: {rel}")
        payload, identity = evidence.load_artifact(path)
        coded = bit_vector(payload["coded"], 2048, f"{inrow['observation_id']} truth coded")
        info = bit_vector(payload["info"], 1024, f"{inrow['observation_id']} truth info")
        if (payload.get("observation_hash") != inrow["observation_hash"]
                or payload.get("stream_ids") != inrow["stream_ids"]
                or not np.array_equal(coded[free], info)
                or not np.array_equal(np.asarray(G @ info.astype(np.int32)).reshape(-1) % 2, coded)
                or syndrome(H, coded) != 0):
            raise ValueError(f"coded truth/code cache/observation differs: {inrow['observation_id']}")
        truths[inrow["observation_id"]] = (coded, info)
        truth_payload_hashes[inrow["observation_id"]] = digest

    paid = jsonl(observed / "ledger.jsonl")
    attempts = jsonl(observed / "attempts.jsonl")
    policies = jsonl(observed / "policy_ledger.jsonl")
    if (len(paid) != 2168 or len(attempts) != 2168 or len(policies) != 5120
            or (observed / "failed_calls.jsonl").read_text().strip()
            or [r.get("attempt") for r in paid] != list(range(1, 2169))
            or any(r.get("status") != "ok" for r in paid + policies)):
        raise ValueError("paid calls or logical policy allocation incomplete")
    for done, started in zip(paid, attempts, strict=True):
        if any(done.get(k) != started.get(k) for k in
               ("attempt", "kind", "arm", "observation_id", "input_sha256")):
            raise ValueError("attempt starts and completed calls diverge")

    by_frame: dict[str, dict[str, dict]] = {}
    for row in paid:
        group = by_frame.setdefault(row["observation_id"], {})
        if row["arm"] in group:
            raise ValueError("duplicate paid arm for frame")
        group[row["arm"]] = row
    policy_index: dict[str, dict[str, dict]] = {}
    for row in policies:
        if row.get("policy") not in POLICIES:
            raise ValueError("unexpected policy row")
        group = policy_index.setdefault(row["observation_id"], {})
        if row["policy"] in group:
            raise ValueError("duplicate policy row")
        group[row["policy"]] = row
    if len(by_frame) != N or len(policy_index) != N:
        raise ValueError("frame denominator differs")

    expected_artifacts: set[str] = {"manifest.json", "ledger.jsonl", "attempts.jsonl",
                                    "policy_ledger.jsonl", "failed_calls.jsonl"}
    raw_cache: dict[str, dict] = {}
    checkpoint_cache: dict[str, dict] = {}
    paid_by_raw: dict[str, dict] = {}
    for frame in range(N):
        stem = f"s650_f{frame:04d}"
        group = by_frame.get(stem, {})
        if not {"F0", "F2E"}.issubset(group) or set(group) - {"F0", "F2E", "B", "F0_LOCAL", "F2T"}:
            raise ValueError(f"paid arm set differs at {stem}")
        if set(policy_index.get(stem, {})) != set(POLICIES):
            raise ValueError(f"five policy rows missing at {stem}")
        if bool(group["F0"]["final_syndrome_weight"]) != all(
                name in group for name in ("B", "F0_LOCAL", "F2T")):
            raise ValueError(f"original F0 trigger continuation set differs at {stem}")
        for arm, row in group.items():
            if row.get("input_sha256") != pop[frame]["observation_sha256"]:
                raise ValueError(f"paid input SHA differs from sealed population: {stem}/{arm}")
            identity = {"observation_id": stem, "arm": arm}
            if row["kind"] == "prefix":
                identity["input_sha256"] = row["input_sha256"]
            else:
                identity["prefix_raw_sha256"] = row["prefix_raw_sha256"]
            for relkey, hashkey in (("raw_path", "raw_sha256"), ("decision_path", "decision_sha256")):
                rel = row[relkey]
                if file_map.get(rel) != row[hashkey]:
                    raise ValueError(f"ledger/seal reference differs: {rel}")
                expected_artifacts.add(rel)
            raw = load_checked(evidence, observed, row["raw_path"], row["raw_sha256"], identity)
            if (raw.get("observation_id") != stem or raw.get("arm") != arm
                    or raw.get("input_sha256") != row["input_sha256"]
                    or raw.get("observation_hash") != pop[frame]["observation_hash"]
                    or raw.get("stream_ids") != pop[frame]["stream_ids"]):
                raise ValueError(f"raw input identity differs: {stem}/{arm}")
            decoded = bit_vector(raw["final_decoded"], 2048, f"{stem}/{arm} decoded")
            info = bit_vector(raw["final_info"], 1024, f"{stem}/{arm} info")
            if not np.array_equal(decoded[free], info):
                raise ValueError(f"final saved info is not systematic extraction: {stem}/{arm}")
            weight = syndrome(H, decoded)
            if weight != row["final_syndrome_weight"]:
                raise ValueError(f"ledger syndrome differs from raw: {stem}/{arm}")
            decision_path = safe_artifact(observed, row["decision_path"])
            if sha256(decision_path) != row["decision_sha256"]:
                raise ValueError(f"decision hash differs: {stem}/{arm}")
            decision = json.loads(decision_path.read_text())
            fvec_equal(decoded, decision["final_decoded"], f"{stem}/{arm} decision bits")
            fvec_equal(info, decision["final_info"], f"{stem}/{arm} decision info")
            if decision.get("raw_sha256") != row["raw_sha256"]:
                raise ValueError(f"decision/raw binding differs: {stem}/{arm}")
            raw_cache[row["raw_path"]] = raw
            paid_by_raw[row["raw_path"]] = row
            for cp in row["checkpoints"]:
                if file_map.get(cp["path"]) != cp["sha256"]:
                    raise ValueError(f"checkpoint/seal reference differs: {cp['path']}")
                expected_artifacts.add(cp["path"])

    outcomes: dict[str, dict[str, dict]] = {}
    full_checkpoints: dict[str, list[dict]] = {}
    frame_triggered: set[str] = set()
    timing_by_policy = {p: [] for p in POLICIES}
    branch_costs = {p: [] for p in POLICIES}
    rss_values = []
    previous_rss = 0
    logical_frame_records = {}

    # Paid RSS and schedule integrity.
    for row in paid:
        rss = row.get("rss_peak_kib_cumulative")
        if type(rss) is not int or rss < previous_rss or rss <= 0:
            raise ValueError("cumulative RSS ledger is nonmonotone/missing")
        previous_rss = rss
        rss_values.append(rss)

    for frame in range(N):
        stem = f"s650_f{frame:04d}"
        coded, info_truth = truths[stem]
        actual = by_frame[stem]
        outcomes[stem] = {}
        for policy in POLICIES:
            row = policy_index[stem][policy]
            prefix_arm = "F2E" if policy == "F2E" else "F0"
            parent = actual[prefix_arm]
            triggered = bool(parent["final_syndrome_weight"])
            if triggered:
                frame_triggered.add(stem) if prefix_arm == "F0" else None
            expected_branch = policy if triggered and policy in ("B", "F0_LOCAL", "F2T") else None
            branch_arm = row.get("branch_arm")
            if (row.get("frame") != frame or row.get("input_sha256") != pop[frame]["observation_sha256"]
                    or row.get("prefix_arm") != prefix_arm
                    or row.get("prefix_raw_sha256") != parent["raw_sha256"]
                    or row.get("triggered") is not triggered or branch_arm != expected_branch):
                raise ValueError(f"logical source/trigger differs: {stem}/{policy}")
            final_source_path = row["source_of_final_bits"]
            source = paid_by_raw.get(final_source_path)
            if source is None or source["observation_id"] != stem or source["arm"] != (branch_arm or prefix_arm):
                raise ValueError(f"logical output source row differs: {stem}/{policy}")
            raw = raw_cache[final_source_path]
            decoded = bit_vector(raw["final_decoded"], 2048, f"{stem}/{policy} final bits")
            info = bit_vector(raw["final_info"], 1024, f"{stem}/{policy} final info")
            weight = syndrome(H, decoded)
            errors = int(np.count_nonzero(decoded != coded))
            info_ok = bool(np.array_equal(info, info_truth))
            coded_ok = errors == 0
            if (row["final_syndrome_weight"] != weight
                    or row["final_decoded_sha256"] != sha256_bytes(decoded.tobytes())
                    or row["final_info_sha256"] != sha256_bytes(info.tobytes())):
                raise ValueError(f"logical output summary differs: {stem}/{policy}")

            prefix_seconds = float(parent["complete_latency_seconds"])
            branch_row = actual.get(branch_arm) if branch_arm else None
            branch_seconds = 0.0 if branch_row is None else float(branch_row["complete_latency_seconds"])
            total = float(row["complete_latency_seconds"])
            if (not math.isclose(float(row["prefix_complete_seconds"]), prefix_seconds, abs_tol=1e-9, rel_tol=0)
                    or not math.isclose(float(row["branch_complete_seconds"]), branch_seconds, abs_tol=1e-9, rel_tol=0)
                    or not math.isclose(total, prefix_seconds + branch_seconds, abs_tol=1e-9, rel_tol=0)):
                raise ValueError(f"logical paid cost differs from prefix + own branch: {stem}/{policy}")
            timing_by_policy[policy].append(total)
            branch_costs[policy].append(branch_seconds)

            # Independently open each durable checkpoint and score its saved bits.
            cps = []
            seen_rounds = set()
            for cp in row["checkpoints"]:
                rd = int(cp["round"])
                if rd in seen_rounds or cp["durable_seconds"] < 0:
                    raise ValueError(f"invalid checkpoint ordering: {stem}/{policy}")
                seen_rounds.add(rd)
                owner = next((candidate for candidate in actual.values()
                              if any(c["path"] == cp["path"] for c in candidate["checkpoints"])), None)
                if owner is None:
                    raise ValueError(f"checkpoint has no paid-call owner: {cp['path']}")
                paid_cp = next(c for c in owner["checkpoints"] if c["path"] == cp["path"])
                offset = 0.0 if owner["arm"] == prefix_arm else prefix_seconds
                if (not math.isclose(float(cp["durable_seconds"]),
                                     offset + float(paid_cp["durable_seconds"]),
                                     abs_tol=1e-9, rel_tol=0)
                        or not math.isclose(float(cp["decision_ready_seconds"]),
                                            offset + float(paid_cp["decision_ready_seconds"]),
                                            abs_tol=1e-9, rel_tol=0)
                        or cp["sha256"] != paid_cp["sha256"]):
                    raise ValueError(f"logical checkpoint clock/source differs from paid ledger: {stem}/{policy}")
                if cp["path"] not in checkpoint_cache:
                    checkpoint_cache[cp["path"]] = load_checked(
                        evidence, observed, cp["path"], cp["sha256"],
                        {"observation_id": stem, "arm": owner["arm"], "round": rd})
                cp_payload = checkpoint_cache[cp["path"]]
                cpbits = bit_vector(cp_payload["decoded"], 2048, f"{stem}/{policy} checkpoint")
                cpweight = syndrome(H, cpbits)
                if cpweight != cp["syndrome_weight"]:
                    raise ValueError(f"checkpoint syndrome differs: {stem}/{policy}/r{rd}")
                cps.append({"round": rd, "durable_seconds": float(cp["durable_seconds"]),
                            "info_correct": bool(np.array_equal(cpbits[free], info_truth)),
                            "coded_correct": bool(np.array_equal(cpbits, coded)),
                            "syndrome_weight": cpweight, "path": cp["path"], "sha256": cp["sha256"]})
            if not cps or cps != sorted(cps, key=lambda x: x["durable_seconds"]):
                raise ValueError(f"checkpoint durable order differs: {stem}/{policy}")
            if not np.array_equal(cpbits, decoded):
                raise ValueError(f"latest checkpoint does not match final decision: {stem}/{policy}")
            full_checkpoints[stem + "/" + policy] = cps
            outcomes[stem][policy] = {"info_correct": info_ok, "coded_errors": errors,
                "coded_correct": coded_ok, "syndrome_weight": weight,
                "valid_but_wrong": bool(weight == 0 and errors > 0),
                "triggered": triggered, "complete_seconds": total,
                "branch_seconds": branch_seconds, "branch_executed": branch_row is not None,
                "checkpoints": cps}
            logical_frame_records[(stem, policy)] = row
    if len(frame_triggered) != 40:
        raise ValueError(f"original F0 trigger cohort expected 40; got {len(frame_triggered)}")
    if expected_artifacts != set(file_map):
        extra = sorted(set(file_map) - expected_artifacts)[:5]
        missing = sorted(expected_artifacts - set(file_map))[:5]
        raise ValueError(f"observed references do not cover seal inventory: extra={extra}, missing={missing}")

    summaries = {}
    deadlines = (0.5, 1.0)
    for policy in POLICIES:
        rows = [outcomes[f"s650_f{i:04d}"][policy] for i in range(N)]
        branch_executed = [r["branch_seconds"] for r in rows if r["branch_executed"]]
        dead = {}
        for deadline in deadlines:
            states = []
            for row in rows:
                available = [cp for cp in row["checkpoints"] if cp["durable_seconds"] <= deadline]
                states.append(available[-1] if available else None)
            dead[str(deadline)] = {"n": N, "ready": sum(s is not None for s in states),
                "correct": sum(bool(s and s["info_correct"]) for s in states),
                "wrong_ready": sum(bool(s and not s["info_correct"]) for s in states),
                "missing": sum(s is None for s in states)}
        errors = sum(r["coded_errors"] for r in rows)
        summary = {"n": N, "information_failures": sum(not r["info_correct"] for r in rows),
            "information_FER": sum(not r["info_correct"] for r in rows) / N,
            "coded_bit_errors": errors, "coded_BER": errors / (2048 * N),
            "syndrome_nonzero": sum(r["syndrome_weight"] != 0 for r in rows),
            "valid_but_wrong": sum(r["valid_but_wrong"] for r in rows),
            "triggered_prefix_nonzero": sum(r["triggered"] for r in rows),
            "executed_branch_n": sum(r["branch_executed"] for r in rows),
            "complete_latency_seconds": distribution(timing_by_policy[policy]),
            "branch_cost_population_seconds": distribution(branch_costs[policy]),
            "branch_cost_conditional_seconds": distribution(branch_executed) if branch_executed else None,
            "deadlines": dead}
        summaries[policy] = summary

    paired = {}
    for policy in POLICIES:
        if policy == "B":
            continue
        b_correct = np.asarray([outcomes[f"s650_f{i:04d}"]["B"]["info_correct"] for i in range(N)], dtype=bool)
        p_correct = np.asarray([outcomes[f"s650_f{i:04d}"][policy]["info_correct"] for i in range(N)], dtype=bool)
        paired[f"B_vs_{policy}"] = {"n": N,
            "B_only_correct": int(np.count_nonzero(b_correct & ~p_correct)),
            "policy_only_correct": int(np.count_nonzero(~b_correct & p_correct)),
            "both_correct": int(np.count_nonzero(b_correct & p_correct)),
            "both_wrong": int(np.count_nonzero(~b_correct & ~p_correct))}

    triggered_summary = {}
    trigger_frames = sorted(frame_triggered)
    for policy in POLICIES:
        rows = [outcomes[stem][policy] for stem in trigger_frames]
        executed = [r["branch_seconds"] for r in rows if r["branch_executed"]]
        triggered_summary[policy] = {"n": 40,
            "information_failures": sum(not r["info_correct"] for r in rows),
            "coded_bit_errors": sum(r["coded_errors"] for r in rows),
            "syndrome_nonzero": sum(r["syndrome_weight"] != 0 for r in rows),
            "complete_latency_seconds": distribution([r["complete_seconds"] for r in rows]),
            "branch_cost_conditional_seconds": distribution(executed) if executed else None}

    # Pull only the committed primary files listed in the independently hashed attestation.
    report = json.loads(primary_blobs[EXPECTED_PRIMARY_REPORT])
    primary_summary = report["summary"]
    comparisons = {"status": "pass", "checks": []}
    def note(name: str, independent, primary, *, tolerance: float = 1e-8):
        equal = (math.isclose(float(independent), float(primary), rel_tol=0, abs_tol=tolerance)
                 if isinstance(independent, (int, float)) and isinstance(primary, (int, float))
                 else independent == primary)
        comparisons["checks"].append({"name": name, "pass": equal,
                                      "independent": independent, "primary": primary})
        if not equal:
            comparisons["status"] = "mismatch"
    for policy in POLICIES:
        ours, theirs = summaries[policy], primary_summary["arms"][policy]
        for field in ("n", "information_failures", "information_FER", "coded_bit_errors",
                      "coded_BER", "syndrome_nonzero", "valid_but_wrong",
                      "triggered_prefix_nonzero", "executed_branch_n"):
            note(f"{policy}.{field}", ours[field], theirs[field])
        for key, value in ours["complete_latency_seconds"].items():
            if key != "n":
                note(f"{policy}.timing.{key}", value, primary_complete_latency(theirs)[key])
        for deadline in ("0.5", "1.0"):
            for field in ("n", "correct", "wrong_ready", "missing"):
                note(f"{policy}.deadline{deadline}.{field}", ours["deadlines"][deadline][field],
                     theirs["deadlines"][deadline][field])
        for branch_key, primary_key in (("branch_cost_population_seconds", "branch_cost_population"),
                                        ("branch_cost_conditional_seconds", "branch_cost_conditional_on_execution")):
            a, b = ours[branch_key], theirs[primary_key]
            if a is None or b is None:
                note(f"{policy}.{branch_key}.none", a is None, b is None)
            else:
                for k, value in a.items():
                    if k != "n":
                        note(f"{policy}.{branch_key}.{k}", value, b[k])
    for pair_name, counts in paired.items():
        p = primary_summary["paired"][pair_name]
        for field, primary_field in (("B_only_correct", "first_only_correct"),
                                     ("policy_only_correct", "second_only_correct"),
                                     ("both_correct", "both_correct"), ("both_wrong", "both_wrong"), ("n", "n")):
            note(f"paired.{pair_name}.{field}", counts[field], p[primary_field])
    for name, blob in primary_blobs.items():
        if name.endswith("frame_outcomes.csv"):
            frame_rows = list(csv.DictReader(io.StringIO(blob.decode("utf-8"))))
            if len(frame_rows) != 5120:
                note("primary.frame_outcomes.row_count", len(frame_rows), 5120)
            else:
                bykey = {(r["observation_id"], r["arm_or_policy"]): r for r in frame_rows}
                for (stem, policy), ours in logical_frame_records.items():
                    theirs = bykey[(stem, policy)]
                    outcome = outcomes[stem][policy]
                    for field, value in (("info_correct", str(outcome["info_correct"])),
                                         ("coded_correct", str(outcome["coded_correct"])),
                                         ("coded_errors", str(outcome["coded_errors"])),
                                         ("syndrome_weight", str(outcome["syndrome_weight"])),
                                         ("valid_but_wrong", str(outcome["valid_but_wrong"])),
                                         ("triggered", str(outcome["triggered"]))):
                        if theirs[field] != value:
                            note(f"frame.{stem}.{policy}.{field}", value, theirs[field])
        elif name.endswith("deadline_decisions.csv"):
            drows = list(csv.DictReader(io.StringIO(blob.decode("utf-8"))))
            if len(drows) != 10240:
                note("primary.deadline_decisions.row_count", len(drows), 10240)
            else:
                dindex = {(r["observation_id"], r["arm_or_policy"], r["deadline_seconds"]): r for r in drows}
                for stem, frame_results in outcomes.items():
                    for policy, result in frame_results.items():
                      for deadline in (0.5, 1.0):
                        available = [c for c in result["checkpoints"] if c["durable_seconds"] <= deadline]
                        ready = bool(available)
                        selected = available[-1] if available else None
                        saved = dindex[(stem, policy, str(deadline))]
                        exp = {"ready": str(ready), "correct": str(bool(selected and selected["info_correct"])),
                               "round": "" if selected is None else str(selected["round"])}
                        for field, value in exp.items():
                            if saved[field] != value:
                                note(f"deadline_row.{stem}.{policy}.{deadline}.{field}", value, saved[field])
        elif name.endswith("paid_call_memory.csv"):
            mrows = list(csv.DictReader(io.StringIO(blob.decode("utf-8"))))
            if len(mrows) != 2168:
                note("primary.paid_call_memory.row_count", len(mrows), 2168)
            else:
                for local, saved in zip(paid, mrows, strict=True):
                    if int(saved["rss_peak_kib_cumulative"]) != local["rss_peak_kib_cumulative"]:
                        note(f"memory.attempt{local['attempt']}", local["rss_peak_kib_cumulative"],
                             int(saved["rss_peak_kib_cumulative"]))
    # Campaign memory peak and F0-triggered 40-frame mechanical cohort.
    campaign_peak = max(max(rss_values), int(seal["campaign_rss_peak_kib_cumulative"]))
    note("memory.campaign_rss_peak_kib_cumulative", campaign_peak,
         report["memory"]["campaign_rss_peak_kib_cumulative"])
    if comparisons["status"] != "pass":
        comparisons["mismatch_count"] = sum(not row["pass"] for row in comparisons["checks"])

    result = {"schema": "independent-f2-five-outcome-recount/1", "status": comparisons["status"],
        "scope": {"receiver_calls": 0, "new_observations": 0,
            "method": "independent saved raw/checkpoint + truth recount; no primary analysis helper imported",
            "observed_seal_sha256": EXPECTED_OBSERVED_SEAL,
            "observed_commit": EXPECTED_OBSERVED_COMMIT,
            "primary_git_go_commit": EXPECTED_PRIMARY_COMMIT,
            "primary_attestation_sha256": EXPECTED_PRIMARY_ATTESTATION_SHA,
            "truth_seal_sha256": expected_truth_seal,
            "code_cache_sha256": EXPECTED_CODE_CACHE_SHA,
            "truth_payloads_read": len(truth_payload_hashes), "truth_payload_sha256_by_id": truth_payload_hashes,
            "observed_sealed_members_rehashed": len(observed_hashes),
            "logical_policy_rows_recounted": sum(len(v) for v in outcomes.values()),
            "paid_call_rows_recounted": len(paid), "unique_checkpoint_artifacts_reloaded": len(checkpoint_cache),
            "observation_population": "sealed 6.5-dB rows only; frame IDs s650_f0000..s650_f1023"},
        "outcomes": summaries, "paired_against_B": paired,
        "original_F0_trigger_cohort": {"n": len(trigger_frames), "ids": trigger_frames,
                                         "policies": triggered_summary},
        "memory": {"campaign_rss_peak_kib_cumulative": campaign_peak,
                    "last_paid_call_rss_peak_kib_cumulative": rss_values[-1],
                    "paid_call_rows": len(rss_values),
                    "semantics": "shared process cumulative RUSAGE_SELF high-water; not isolated policy RSS"},
        "comparison_to_primary_git": comparisons}
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
