"""Offline Stage-A paired analysis of sealed outputs; never calls a receiver."""

from __future__ import annotations

import argparse
import csv
import hashlib
from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
from scipy.stats import beta, binomtest


ARMS = ("A", "B", "C", "D")
N_FRAMES = 1024
DEADLINES = (0.5, 1.0)


def _binary(value: Any) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != (N_FRAMES,) or array.dtype.kind != "b":
        raise ValueError("expected exactly 1024 boolean outcomes")
    return array


def _binary_subset(value: Any) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != 1 or array.size == 0 or array.dtype.kind != "b":
        raise ValueError("expected a nonempty boolean outcome vector")
    return array


def cp_lower(count: int, total: int, *, tail: float = 0.025) -> float:
    if not 0 <= count <= total or total <= 0:
        raise ValueError("invalid binomial count")
    return 0.0 if count == 0 else float(beta.ppf(tail, count, total - count + 1))


def cp_upper(count: int, total: int, *, tail: float = 0.025) -> float:
    if not 0 <= count <= total or total <= 0:
        raise ValueError("invalid binomial count")
    return 1.0 if count == total else float(beta.ppf(1 - tail, count + 1, total - count))


def paired_table(first: Any, second: Any) -> dict[str, Any]:
    """Signed delta is FER_first − FER_second; second-only correct is rescue."""
    a, b = _binary_subset(first), _binary_subset(second)
    if a.shape != b.shape:
        raise ValueError("paired outcome lengths differ")
    both = int(np.count_nonzero(a & b))
    first_only = int(np.count_nonzero(a & ~b))
    second_only = int(np.count_nonzero(~a & b))
    neither = int(np.count_nonzero(~a & ~b))
    n = int(a.size)
    discordant = first_only + second_only
    return {
        "n": n,
        "both_correct": both,
        "first_only_correct": first_only,
        "second_only_correct": second_only,
        "both_wrong": neither,
        "fer_first_minus_second": (second_only - first_only) / n,
        "fer_second_minus_first": (first_only - second_only) / n,
        "upper_95_fer_first_minus_second": (
            cp_upper(second_only, n) - cp_lower(first_only, n)
        ),
        "upper_95_fer_second_minus_first": (
            cp_upper(first_only, n) - cp_lower(second_only, n)
        ),
        "mcnemar_exact_two_sided_p": (
            float(binomtest(first_only, discordant, 0.5).pvalue)
            if discordant else 1.0
        ),
    }


def all_pairwise(outcomes: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if set(outcomes) != set(ARMS):
        raise ValueError("A/B/C/D outcomes required")
    for value in outcomes.values():
        _binary(value)
    return {f"{a}_vs_{b}": paired_table(outcomes[a], outcomes[b])
            for a, b in combinations(ARMS, 2)}


def distribution(values: Any, *, expected: int | None = None) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0 or (expected is not None and arr.size != expected):
        raise ValueError("invalid distribution size")
    if not np.isfinite(arr).all() or (arr < 0).any():
        raise ValueError("nonfinite or negative elapsed value")
    return {"n": int(arr.size), "mean": float(np.mean(arr)),
            "median": float(np.median(arr)), "p95": float(np.quantile(arr, 0.95)),
            "p99": float(np.quantile(arr, 0.99)), "max": float(np.max(arr))}


def latest_ready(checkpoints: list[dict[str, Any]], deadline: float) -> dict[str, Any]:
    if deadline not in DEADLINES:
        raise ValueError("unregistered deadline")
    seen = set()
    ordered = []
    for row in checkpoints:
        round_id, elapsed = row["round"], float(row["ready_seconds"])
        if round_id in seen or not np.isfinite(elapsed) or elapsed < 0:
            raise ValueError("invalid checkpoint")
        seen.add(round_id)
        ordered.append((elapsed, row))
    if not ordered or ordered != sorted(ordered, key=lambda item: item[0]):
        raise ValueError("checkpoint order differs")
    ready = [row for elapsed, row in ordered if elapsed <= deadline]
    if not ready:
        return {"ready": False, "correct": False, "round": None}
    last = ready[-1]
    return {"ready": True, "correct": bool(last["info_correct"]),
            "round": last["round"]}


def deadline_summary(rows: list[list[dict[str, Any]]]) -> dict[str, dict[str, int]]:
    if len(rows) != N_FRAMES:
        raise ValueError("full denominator required")
    return {str(deadline): {
        "correct": sum(latest_ready(frame, deadline)["correct"] for frame in rows),
        "missing": sum(not latest_ready(frame, deadline)["ready"] for frame in rows),
        "wrong_or_missing": sum(not latest_ready(frame, deadline)["correct"] for frame in rows),
    } for deadline in DEADLINES}


def fixed_gates(outcomes: dict[str, Any], old_b_only_rescues: Any,
                mean_latency: dict[str, float], p95_latency: dict[str, float]) -> dict[str, Any]:
    """Only K and incremental-effect predicates are numerically preregistered."""
    arrays = {arm: _binary(value) for arm, value in outcomes.items()}
    if set(arrays) != set(ARMS):
        raise ValueError("A/B/C/D outcomes required")
    original = np.asarray(old_b_only_rescues)
    if original.shape != (N_FRAMES,) or original.dtype.kind != "b" or int(original.sum()) != 34:
        raise ValueError("the original 34 B-only rescues must be bound")
    cb = paired_table(arrays["C"], arrays["B"])
    cd = paired_table(arrays["C"], arrays["D"])
    absorbed = int(np.count_nonzero(arrays["C"] & original))
    k_parts = {
        "absorbed_at_least_26_of_34": absorbed >= 26,
        "C_minus_B_upper_below_1pp": cb["upper_95_fer_first_minus_second"] < 0.01,
        "D_gain_upper_below_1pp": cd["upper_95_fer_first_minus_second"] < 0.01,
        "C_mean_no_more_than_B": mean_latency["C"] <= mean_latency["B"],
        "C_p95_no_more_than_B": p95_latency["C"] <= p95_latency["B"],
    }
    return {"original_B_only_rescues_absorbed_by_C": absorbed,
            "K_tested_regime_pass": all(k_parts.values()), "K_parts": k_parts,
            "incremental_D_over_C_effect_upper_below_zero":
                cd["upper_95_fer_second_minus_first"] < 0,
            "categorical_S_or_E": "not_auto_adjudicated_no_frozen_numeric_threshold",
            "overall_auto_verdict": "K" if all(k_parts.values()) else "U"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def _safe(root: Path, relative: str) -> Path:
    name = Path(relative)
    if name.is_absolute() or ".." in name.parts:
        raise ValueError("artifact path escapes its sealed root")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("artifact symlink escapes its sealed root")
    return path


def _verify_file_inventory(root: Path, seal_name: str) -> dict[str, Any]:
    seal = _json(root / seal_name)
    if seal.get("status") != "pass":
        raise ValueError(f"incomplete seal: {root}")
    actual = {str(path.relative_to(root)): sha256(path) for path in root.rglob("*")
              if path.is_file() and path.name != seal_name}
    if actual != seal.get("files"):
        raise ValueError(f"sealed artifact inventory differs: {root}")
    return seal


def _git_blob_equals(repo: Path, commit: str, relative: str, path: Path) -> None:
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise ValueError("full Git commit hash required")
    name = Path(relative)
    if name.is_absolute() or ".." in name.parts:
        raise ValueError("invalid Git-relative seal path")
    proc = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{relative}"],
                          capture_output=True, check=False)
    if proc.returncode or proc.stdout != path.read_bytes():
        raise ValueError("committed observed seal differs from on-disk bytes")


def _verify_git_attestation(path: Path, *, registration_commit: str,
                            observed_commit: str, seal_repo_path: str,
                            registration_sha256: str, seal_path: Path,
                            expected_sha256: str) -> str:
    """Consume a local Git verification receipt when the analysis host lacks .git."""
    if sha256(path) != expected_sha256:
        raise ValueError("transferred local Git attestation SHA differs")
    if any(len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit)
           for commit in (registration_commit, observed_commit)):
        raise ValueError("full registration and observed Git commits required")
    name = Path(seal_repo_path)
    if name.is_absolute() or ".." in name.parts:
        raise ValueError("invalid Git-relative seal path")
    attestation = _json(path)
    seal_bytes = seal_path.read_bytes()
    seal_sha = hashlib.sha256(seal_bytes).hexdigest()
    blob_oid = hashlib.sha1(
        f"blob {len(seal_bytes)}\0".encode() + seal_bytes
    ).hexdigest()
    expected = {
        "schema": "cstate-necessity-stage-a/git-attestation/1",
        "registration_commit": registration_commit,
        "observed_commit": observed_commit,
        "seal_repo_path": seal_repo_path,
        "registration_sha256": registration_sha256,
        "seal_sha256": seal_sha,
        "git_blob_oid": blob_oid,
        "git_blob_size_bytes": len(seal_bytes),
        "git_blob_sha256": seal_sha,
        "merge_base_is_ancestor": True,
        "checked_by": "local_git_show_and_merge_base",
    }
    if any(attestation.get(key) != value for key, value in expected.items()):
        raise ValueError("local Git attestation differs from bound seal or registration")
    return sha256(path)


def _artifact(evidence: Any, root: Path, relative: str, expected_hash: str,
              identity: dict[str, Any] | None = None) -> dict[str, Any]:
    path = _safe(root, relative)
    if sha256(path) != expected_hash:
        raise ValueError(f"artifact SHA differs: {relative}")
    payload, actual_identity = evidence.load_artifact(path)
    if identity is not None and actual_identity != identity:
        raise ValueError(f"artifact identity differs: {relative}")
    return payload


def _code_arrays(cache: Path, registration: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if sha256(cache) != registration["ldpc_cache_sha256"]:
        raise ValueError("registered LDPC cache differs")
    with np.load(cache, allow_pickle=False) as saved:
        H = np.asarray(saved["H"], dtype=np.int32)
        raw_G = np.asarray(saved["G"])
        G = raw_G.astype(np.int32)
        free = np.asarray(saved["free_cols"], dtype=np.int64)
    if (H.shape != (1026, 2048) or G.shape != (2048, 1024)
            or free.shape != (1024,) or len(np.unique(free)) != 1024
            or hashlib.sha256(np.ascontiguousarray(raw_G).tobytes()).hexdigest()
            != registration["code_g_sha256"]):
        raise ValueError("registered G/H/free_cols differs")
    return H, G, free


def _bits(value: Any, length: int) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != (length,) or array.dtype != np.uint8 or not np.isin(array, (0, 1)).all():
        raise ValueError("saved bit vector shape/dtype/value differs")
    return array


def _syndrome(H: np.ndarray, decoded: np.ndarray) -> int:
    return int(np.count_nonzero((H @ decoded.astype(np.int32)) % 2))


def _validate_truth(tagged: dict[str, Any], H: np.ndarray, G: np.ndarray,
                    free: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    coded, info = _bits(tagged["coded"], 2048), _bits(tagged["info"], 1024)
    if (not np.array_equal(coded[free], info)
            or not np.array_equal((G @ info.astype(np.int32)) % 2, coded)
            or _syndrome(H, coded) != 0):
        raise ValueError("truth differs from registered systematic LDPC code")
    return coded, info


def _same_saved(left: Any, right: Any, name: str = "") -> None:
    if isinstance(left, dict):
        if not isinstance(right, dict) or set(left) != set(right):
            raise ValueError(f"paired F1 prefix inventory differs: {name}")
        for key in left:
            _same_saved(left[key], right[key], f"{name}/{key}")
    elif isinstance(left, (list, tuple)):
        if not isinstance(right, type(left)) or len(left) != len(right):
            raise ValueError(f"paired F1 prefix sequence differs: {name}")
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            _same_saved(a, b, f"{name}/{index}")
    elif isinstance(left, np.ndarray):
        other = np.asarray(right)
        if left.shape != other.shape or left.dtype != other.dtype:
            raise ValueError(f"paired F1 prefix array metadata differs: {name}")
        if name.endswith("decoded") or not np.issubdtype(left.dtype, np.number):
            equal = np.array_equal(left, other)
        else:
            equal = np.allclose(left, other, atol=2e-10, rtol=0)
        if not equal:
            raise ValueError(f"paired F1 prefix array differs: {name}")
    elif isinstance(left, (int, float, complex, np.number)) and not isinstance(left, bool):
        if not np.isclose(left, right, atol=2e-10, rtol=0):
            raise ValueError(f"paired F1 prefix scalar differs: {name}")
    elif left != right:
        raise ValueError(f"paired F1 prefix value differs: {name}")


def _old_outcomes(path: Path, expected_sha: str) -> dict[str, dict[str, Any]]:
    if sha256(path) != expected_sha:
        raise ValueError("historical outcome CSV SHA differs")
    with path.open(newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row["snr_centi_db"] == "650"]
    old = {row["observation_id"]: row for row in rows}
    if len(rows) != N_FRAMES or len(old) != N_FRAMES:
        raise ValueError("historical 6.5-dB outcomes are incomplete")
    return old


def verify_pretruth(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]],
                                                       dict[str, dict[str, Any]]]:
    observed = args.observed.resolve()
    output = args.out.resolve()
    if args.out.exists() or any(output.is_relative_to(root.resolve()) for root in
                                (observed, args.population_observed, args.population_truth,
                                 args.historical_observed)):
        raise ValueError("analysis output exists or would mutate a sealed tree")
    registration = _json(args.registration)
    if registration.get("schema") != "cstate-necessity-stage-a/1" or registration.get("status") != "locked":
        raise ValueError("Stage-A registration is not locked")
    stage_seal = _verify_file_inventory(observed, "observed_seal.json")
    _verify_file_inventory(args.population_observed, "observed_seal.json")
    _verify_file_inventory(args.population_truth, "truth_seal.json")
    _verify_file_inventory(args.historical_observed, "observed_seal.json")
    if (stage_seal.get("registration_sha256") != sha256(args.registration)
            or stage_seal.get("observations") != N_FRAMES
            or stage_seal.get("primary_calls") != 4 * N_FRAMES
            or sha256(args.population_observed / "observed_seal.json")
            != registration["population_observed_seal_sha256"]
            or sha256(args.population_truth / "truth_seal.json")
            != registration["population_truth_seal_sha256"]
            or sha256(args.historical_observed / "observed_seal.json")
            != registration["historical_observed_seal_sha256"]):
        raise ValueError("Stage-A observed/population/historical seal binding differs")
    manifest = _json(observed / "manifest.json")
    if (manifest["registration_sha256"] != sha256(args.registration)
            or manifest["source_hashes"] != registration["source_hashes"]):
        raise ValueError("Stage-A producer manifest differs from registration")
    if args.git_attestation is not None:
        _verify_git_attestation(args.git_attestation,
            registration_commit=manifest["registration_commit"],
            observed_commit=args.observed_commit,
            seal_repo_path=args.seal_repo_path,
            registration_sha256=sha256(args.registration),
            seal_path=observed / "observed_seal.json",
            expected_sha256=args.git_attestation_sha256)
    else:
        _git_blob_equals(args.evidence_git, args.observed_commit,
                         args.seal_repo_path, observed / "observed_seal.json")
        ancestry = subprocess.run(["git", "-C", str(args.evidence_git), "merge-base",
                                   "--is-ancestor", manifest["registration_commit"],
                                   args.observed_commit], capture_output=True, check=False)
        if ancestry.returncode:
            raise ValueError("observed seal commit does not descend from registration commit")
    observed_rows = _jsonl(observed / "ledger.jsonl")
    attempts = _jsonl(observed / "attempts.jsonl")
    if (len(observed_rows) != len(attempts)
            or len(observed_rows) != stage_seal.get("attempts")
            or any(row["status"] != "ok" for row in observed_rows)
            or [row["attempt_index"] for row in observed_rows]
            != list(range(1, len(observed_rows) + 1))):
        raise ValueError("Stage-A attempt ledger incomplete or nonsequential")
    for complete, started in zip(observed_rows, attempts, strict=True):
        if any(complete[key] != started[key] for key in
               ("attempt_index", "observation_id", "arm", "input_sha256")):
            raise ValueError("durable starts differ from complete calls")
    population_rows = [row for row in _jsonl(args.population_observed / "ledger.jsonl")
                       if row["snr_centi_db"] == 650]
    if (len(population_rows) != N_FRAMES
            or [row["frame"] for row in population_rows] != list(range(N_FRAMES))):
        raise ValueError("full fixed population identity differs")
    historical = _old_outcomes(args.historical_outcomes,
                               registration["historical_frame_outcomes_sha256"])
    parity = _jsonl(observed / "historical_parity.jsonl")
    if (len(parity) != 2 * N_FRAMES or
            {(row["observation_id"], row["arm"]) for row in parity} !=
            {(row["observation_id"], arm) for row in population_rows for arm in ("A", "B")} or
            any(row["final_bits_equal"] is not True or
                not 0 <= row["max_array_difference"] <= 2e-10 for row in parity)):
        raise ValueError("historical A/B exact-bit and 2e-10 array parity gate incomplete")
    return registration, population_rows, historical


def _decision(evidence: Any, root: Path, row: dict[str, Any], H: np.ndarray,
              free: np.ndarray, coded: np.ndarray, info: np.ndarray) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = {"schema": "cstate-necessity-stage-a/1",
                "observation_id": row["observation_id"], "arm": row["arm"],
                "input_sha256": row["input_sha256"]}
    raw = _artifact(evidence, root, row["raw_path"], row["raw_sha256"], identity)
    decision_path = _safe(root, row["decision_path"])
    if sha256(decision_path) != row["decision_sha256"]:
        raise ValueError("decision JSON SHA differs")
    saved = _json(decision_path)
    decoded = _bits(raw["final_decoded"], 2048)
    extracted = _bits(raw["final_info"], 1024)
    syndrome = _syndrome(H, decoded)
    if (raw["observation_id"] != row["observation_id"] or raw["arm"] != row["arm"]
            or raw["input_sha256"] != row["input_sha256"]
            or raw["stream_ids"] != row["stream_ids"]
            or raw["triggered"] != row["triggered"]
            or raw["baseline_syndrome_weight"] != row["baseline_syndrome_weight"]
            or not np.array_equal(decoded[free], extracted)
            or not np.array_equal(np.asarray(saved["final_decoded"]), decoded)
            or not np.array_equal(np.asarray(saved["final_info"]), extracted)
            or saved["observation_id"] != row["observation_id"]
            or saved["arm"] != row["arm"]
            or saved["input_sha256"] != row["input_sha256"]
            or saved["triggered"] != row["triggered"]
            or saved["final_decoded_sha256"] != row["final_decoded_sha256"]
            or saved["raw_sha256"] != row["raw_sha256"]
            or saved["checkpoints"] != row["checkpoints"]
            or saved["final_syndrome_weight"] != row["final_syndrome_weight"]
            or syndrome != row["final_syndrome_weight"]
            or row["final_decoded_sha256"] != hashlib.sha256(decoded.tobytes()).hexdigest()):
        raise ValueError("Stage-A raw/decision/ledger bits or identity differ")
    checkpoints = []
    if len(row["checkpoints"]) != (3 if row["triggered"] else 2):
        raise ValueError("decision checkpoint count differs")
    for round_index, cp in enumerate(row["checkpoints"]):
        if (cp["round"] != round_index or cp["decision_ready_seconds"] > cp["ready_seconds"]
                or cp["ready_seconds"] > row["complete_latency_seconds"]):
            raise ValueError("checkpoint round/clock differs")
        payload = _artifact(evidence, root, cp["path"], cp["artifact_sha256"],
                            dict(identity, round=round_index))
        bits = _bits(payload["decoded"], 2048)
        if (_syndrome(H, bits) != cp["syndrome_weight"]
                or not np.array_equal(bits, np.asarray(payload["event"]["snapshot"]["decoded"]))):
            raise ValueError("checkpoint bits/syndrome differ")
        checkpoints.append(dict(round=round_index, ready_seconds=float(cp["ready_seconds"]),
                                info_correct=bool(np.array_equal(bits[free], info)),
                                coded_correct=bool(np.array_equal(bits, coded)),
                                syndrome_weight=int(cp["syndrome_weight"])))
    if (not np.array_equal(decoded, bits)
            or raw["baseline_syndrome_weight"] != row["checkpoints"][1]["syndrome_weight"]
            or not np.array_equal(_bits(raw["baseline_arrays"]["r1_decoded"], 2048),
                                  np.asarray(raw["native_decoder"]["decoded"]))):
        raise ValueError("final/native/checkpoint decision differs")
    timing_names = ("complete_latency_seconds", "acquisition_seconds", "refit_seconds",
                    "tf_seconds", "decoder_seconds", "branch_seconds",
                    "raw_serialization_seconds", "decision_record_seconds")
    timing = {name: float(row[name]) for name in timing_names}
    if any(not np.isfinite(value) or value < 0 for value in timing.values()):
        raise ValueError("invalid saved component latency")
    result = dict(info_correct=bool(np.array_equal(extracted, info)),
                  coded_correct=bool(np.array_equal(decoded, coded)),
                  info_errors=int(np.count_nonzero(extracted != info)),
                  coded_errors=int(np.count_nonzero(decoded != coded)),
                  syndrome_weight=syndrome, valid_but_wrong=syndrome == 0 and
                  not np.array_equal(decoded, coded),
                  triggered=bool(row["triggered"]), checkpoints=checkpoints,
                  timing=timing)
    return result, raw


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("empty analysis table")
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    registration, population, historical = verify_pretruth(args)
    sys.path.insert(0, str(args.baseline / "src"))
    import evidence  # type: ignore[import-not-found]  # read-only archive codec

    cache = (args.baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
             "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    H, G, free = _code_arrays(cache, registration)
    truth_rows = {row["observation_id"]: row for row in
                  _jsonl(args.population_truth / "ledger.jsonl") if row["snr_centi_db"] == 650}
    if len(truth_rows) != N_FRAMES:
        raise ValueError("1024 bound truth identities required")
    observed_rows = _jsonl(args.observed / "ledger.jsonl")
    by_frame: dict[str, dict[str, dict[str, Any]]] = {}
    for row in observed_rows:
        if row["arm"] not in (*ARMS, "E") or row["observation_id"] not in historical:
            raise ValueError("unexpected Stage-A arm or population ID")
        group = by_frame.setdefault(row["observation_id"], {})
        if row["arm"] in group:
            raise ValueError("duplicate saved frame/arm")
        group[row["arm"]] = row
    if len(by_frame) != N_FRAMES:
        raise ValueError("full 1024-frame saved coverage required")
    outcomes = {arm: np.zeros(N_FRAMES, dtype=bool) for arm in ARMS}
    original_rescues = np.zeros(N_FRAMES, dtype=bool)
    times = {arm: {key: [] for key in ("complete_latency_seconds", "acquisition_seconds",
                                       "refit_seconds", "tf_seconds", "decoder_seconds",
                                       "branch_seconds", "raw_serialization_seconds",
                                       "decision_record_seconds")} for arm in (*ARMS, "E")}
    checkpoints = {arm: [] for arm in (*ARMS, "E")}
    frame_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    structure_rows: list[dict[str, Any]] = []
    deadline_rows: list[dict[str, Any]] = []
    local_D, local_E = [], []
    coded_error_counts = {arm: 0 for arm in ARMS}
    trigger_counts = {arm: 0 for arm in (*ARMS, "E")}
    for frame, input_row in enumerate(population):
        stem = input_row["observation_id"]
        old = historical[stem]
        truth_row = truth_rows[stem]
        if (input_row["observation_hash"] != truth_row["observation_hash"]
                or input_row["stream_ids"] != truth_row["stream_ids"]):
            raise ValueError("observed/truth/registered frame identity differs")
        tagged = _artifact(evidence, args.population_truth, truth_row["truth_path"],
                           truth_row["truth_sha256"])
        if (tagged["observation_hash"] != input_row["observation_hash"]
                or tagged["stream_ids"] != input_row["stream_ids"]):
            raise ValueError("truth payload does not match observed identity")
        coded, info = _validate_truth(tagged, H, G, free)
        arm_rows = by_frame[stem]
        if not set(ARMS).issubset(arm_rows):
            raise ValueError("A/B/C/D frame incomplete")
        decisions: dict[str, dict[str, Any]] = {}
        native_slot_counts = {}
        f1_prefix = None
        f1_initial = None
        f1_syndrome = None
        c_native_trigger = None
        for arm in (*ARMS, "E"):
            if arm not in arm_rows:
                continue
            row = arm_rows[arm]
            if (row["frame"] != frame or row["input_sha256"] != input_row["observation_sha256"]
                    or row["observation_hash"] != input_row["observation_hash"]
                    or row["stream_ids"] != input_row["stream_ids"]):
                raise ValueError("Stage-A saved arm/input identity differs")
            decision, raw = _decision(evidence, args.observed, row, H, free, coded, info)
            decisions[arm] = decision
            native_slot_counts[arm] = len(np.asarray(raw["baseline_arrays"]["r0_delays"]))
            native_trigger = row["baseline_syndrome_weight"] != 0
            if arm in ("C", "D", "E"):
                if f1_prefix is None:
                    f1_prefix = raw["baseline_arrays"]
                    f1_initial = raw["initial_geometry"]
                    f1_syndrome = row["baseline_syndrome_weight"]
                else:
                    _same_saved(f1_prefix, raw["baseline_arrays"])
                    _same_saved(f1_initial, raw["initial_geometry"])
                    if f1_syndrome != row["baseline_syndrome_weight"]:
                        raise ValueError("F1 C/D/E native syndrome differs")
                if arm == "C":
                    c_native_trigger = native_trigger
            expected_branch = ((arm in ("B", "D") and native_trigger)
                               or arm == "E")
            if decision["triggered"] != expected_branch or (arm == "E" and not native_trigger):
                raise ValueError("CSTATE/LOCAL trigger rule differs")
            if arm == "E" and (raw["geometry_result"] is None
                               or raw["geometry_result"]["edits"]):
                raise ValueError("LOCAL control contains a global edit")
            trigger_counts[arm] += int(decision["triggered"])
            checkpoints[arm].append(decision["checkpoints"])
            for deadline_value in DEADLINES:
                deadline_rows.append(dict(observation_id=stem, frame=frame, arm=arm,
                                          deadline_seconds=deadline_value,
                                          **latest_ready(decision["checkpoints"], deadline_value)))
            for key, value in decision["timing"].items():
                times[arm][key].append(value)
            timing_rows.append(dict(observation_id=stem, frame=frame, arm=arm,
                                    **decision["timing"]))
            if arm in ARMS:
                outcomes[arm][frame] = decision["info_correct"]
                coded_error_counts[arm] += decision["coded_errors"]
            if arm in ("C", "D", "E"):
                geometry = raw["initial_geometry"]
                if geometry is None:
                    raise ValueError("F1 geometry trace missing")
                acquisition = raw["acquisition"]
                if acquisition is None:
                    raise ValueError("F1 acquisition diagnostic missing")
                counters = acquisition["counters"]
                delays = np.asarray(geometry["delays"], dtype=np.int64)
                initial_multiplicity = int(len(delays) - len(np.unique(delays)))
                entering = raw["entering_geometry"]
                entering_delays = np.asarray(entering["delays"], dtype=np.int64)
                edits = [] if raw["geometry_result"] is None else raw["geometry_result"]["edits"]
                structure_rows.append(dict(observation_id=stem, frame=frame, arm=arm,
                    initial_slots=len(delays), initial_same_delay_extra_slots=initial_multiplicity,
                    entering_slots=len(entering_delays),
                    entering_same_delay_extra_slots=int(len(entering_delays)-len(np.unique(entering_delays))),
                    acquisition_stop=acquisition["stopping_reason"],
                    bank_scans=counters["bank_scans"], bank_scores=counters["bank_scores"],
                    newton_steps=counters["newton_steps"],
                    coordinate_visits=counters["coordinate_visits"],
                    accepted_coordinates=counters["accepted_coordinates"],
                    joint_solves=counters["joint_solves"],
                    global_edits=len(edits),
                    edit_new_delay=sum(int(e["new"]["delay"] not in entering_delays) for e in edits),
                    edit_existing_delay=sum(int(e["new"]["delay"] in entering_delays) for e in edits),
                    edit_same_delay=sum(int(e["new"]["delay"] == e["old"]["delay"]) for e in edits),
                    physical_capture_sufficiency="unknown_no_frozen_threshold"))
        if c_native_trigger is None or ("E" in arm_rows) != c_native_trigger:
            raise ValueError("LOCAL does not cover exactly all C-triggered frames")
        if "E" in arm_rows:
            local_D.append(decisions["D"]["info_correct"])
            local_E.append(decisions["E"]["info_correct"])
        if (str(old["tf_correct"]) != str(decisions["A"]["info_correct"])
                or str(old["combined_correct"]) != str(decisions["B"]["info_correct"])):
            raise ValueError("new A/B final correctness differs from historical seal")
        if (old["rescue"] == "True") != (old["tf_correct"] == "False" and
                                           old["combined_correct"] == "True"):
            raise ValueError("historical B-only rescue label differs from A/B bits")
        original_rescues[frame] = old["rescue"] == "True"
        frame_rows.append(dict(observation_id=stem, frame=frame,
            original_B_only_rescue=int(original_rescues[frame]),
            **{f"{arm}_info_correct": int(decisions[arm]["info_correct"]) for arm in ARMS},
            **{f"{arm}_coded_correct": int(decisions[arm]["coded_correct"]) for arm in ARMS},
            **{f"{arm}_final_syndrome_weight": decisions[arm]["syndrome_weight"] for arm in ARMS},
            **{f"{arm}_coded_errors": decisions[arm]["coded_errors"] for arm in ARMS},
            **{f"{arm}_info_errors": decisions[arm]["info_errors"] for arm in ARMS},
            **{f"{arm}_triggered": int(decisions[arm]["triggered"]) for arm in ARMS},
            **{f"{arm}_valid_but_wrong": int(decisions[arm]["valid_but_wrong"]) for arm in ARMS},
            **{f"{arm}_r0_TF_entering_slots": native_slot_counts[arm] for arm in ARMS},
            E_run=int("E" in decisions), E_info_correct=("" if "E" not in decisions else
                                                   int(decisions["E"]["info_correct"]))))
    if (len(local_E) != trigger_counts["E"] or trigger_counts["E"] !=
            sum(row["E_run"] for row in frame_rows)):
        raise ValueError("LOCAL call count differs from saved trigger population")
    expected_order = []
    for frame, input_row in enumerate(population):
        stem = input_row["observation_id"]
        expected_order.extend((stem, arm) for arm in ARMS[frame % 4:] + ARMS[:frame % 4])
        if frame_rows[frame]["E_run"]:
            expected_order.append((stem, "E"))
    if ([(row["observation_id"], row["arm"]) for row in observed_rows] != expected_order
            or len(observed_rows) != 4 * N_FRAMES + len(local_E)):
        raise ValueError("balanced A-D rotation or E call allocation differs")
    pairwise = all_pairwise(outcomes)
    complete = {arm: distribution(times[arm]["complete_latency_seconds"], expected=N_FRAMES)
                for arm in ARMS}
    gates = fixed_gates(outcomes, original_rescues,
                        {arm: complete[arm]["mean"] for arm in ARMS},
                        {arm: complete[arm]["p95"] for arm in ARMS})
    deadline = {arm: deadline_summary(checkpoints[arm]) for arm in ARMS}
    report = dict(schema="cstate-necessity-stage-a-analysis/1",
                  status="complete_developmental_not_fresh_confirmation",
                  population_frames=N_FRAMES, stage_a_observed_commit=args.observed_commit,
                  git_verification_mode=("local_attestation_consumed" if args.git_attestation
                                         is not None else "direct_local_git"),
                  observed_seal_sha256=sha256(args.observed / "observed_seal.json"),
                  truth_seal_sha256=sha256(args.population_truth / "truth_seal.json"),
                  information_fer={arm: dict(errors=N_FRAMES-int(outcomes[arm].sum()),
                                             rate=1-float(outcomes[arm].mean())) for arm in ARMS},
                  coded_ber={arm: dict(errors=coded_error_counts[arm],
                                       rate=coded_error_counts[arm] / (N_FRAMES * 2048))
                             for arm in ARMS},
                  pairwise=pairwise, gates=gates,
                  local_on_C_triggered=(paired_table(np.array(local_D, bool),
                                                      np.array(local_E, bool)) if local_E else None),
                  local_triggered_count=len(local_E), trigger_counts=trigger_counts,
                  timing={arm: {key: distribution(value) for key, value in times[arm].items()
                                if value} for arm in (*ARMS, "E")},
                  deadline=deadline,
                  physical_capture_sufficiency="unknown_no_frozen_threshold")
    args.out.mkdir(parents=True)
    _write_csv(args.out / "frame_outcomes.csv", frame_rows)
    _write_csv(args.out / "component_timing.csv", timing_rows)
    _write_csv(args.out / "structural_diagnostics.csv", structure_rows)
    _write_csv(args.out / "deadline_decisions.csv", deadline_rows)
    (args.out / "report.json").write_text(json.dumps(report, sort_keys=True,
                                                   indent=2, allow_nan=False) + "\n")
    receipt = dict(schema=report["schema"], observed_commit=args.observed_commit,
                   git_attestation_sha256=(sha256(args.git_attestation)
                                           if args.git_attestation is not None else None),
                   reader_sha256=sha256(Path(__file__)),
                   report_sha256=sha256(args.out / "report.json"),
                   tables={name: sha256(args.out / name) for name in
                           ("frame_outcomes.csv", "component_timing.csv",
                            "structural_diagnostics.csv", "deadline_decisions.csv")})
    (args.out / "analysis_receipt.json").write_text(json.dumps(receipt, sort_keys=True,
                                                               indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("registration", "observed", "population-observed", "population-truth",
                 "historical-observed", "historical-outcomes", "baseline", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    git_source = parser.add_mutually_exclusive_group(required=True)
    git_source.add_argument("--evidence-git", type=Path)
    git_source.add_argument("--git-attestation", type=Path)
    parser.add_argument("--git-attestation-sha256")
    parser.add_argument("--observed-commit", required=True)
    parser.add_argument("--seal-repo-path", required=True)
    args = parser.parse_args()
    if bool(args.git_attestation) != bool(args.git_attestation_sha256):
        parser.error("--git-attestation requires --git-attestation-sha256, and vice versa")
    analyze(args)
