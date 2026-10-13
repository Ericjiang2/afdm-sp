"""Independent, offline recount helpers for the frozen 256-frame CGR study.

This module consumes saved evidence only. It must never import receiver,
decoder, channel-generator, optimizer, or producer modules.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

EVIDENCE_METADATA_KEY = "__evidence_metadata__"
EVIDENCE_ARRAY_SENTINEL = "__evidence_array__"
EVIDENCE_TUPLE_SENTINEL = "__evidence_tuple__"
EVIDENCE_FORMAT_VERSION = 2

FRAMES = 256
ARMS = ("BASE", "CGR", "SHAM")
CONTRASTS = (
    ("CGR", "zero"),
    ("CGR", "swapped"),
    ("SHAM", "zero"),
    ("SHAM", "swapped"),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_inventory(root: Path, seal_path: Path) -> dict[str, Any]:
    """Require the seal's exact relative-path -> SHA256 inventory."""
    root, seal_path = Path(root), Path(seal_path)
    seal = json.loads(seal_path.read_text())
    expected = seal.get("files")
    if not isinstance(expected, dict):
        raise ValueError("seal must contain a files mapping")
    actual = {
        str(path.relative_to(root)): sha256_file(path)
        for path in root.rglob("*")
        if path.is_file() and path.resolve() != seal_path.resolve()
    }
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(k for k in set(actual) & set(expected) if actual[k] != expected[k])
        raise ValueError(f"sealed inventory mismatch: missing={missing[:5]}, extra={extra[:5]}, changed={changed[:5]}")
    return {"status": "pass", "files": len(actual), "bytes": sum((root / k).stat().st_size for k in actual)}


def git_blob_sha256(repo: Path, commit: str, path: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40,64}", commit) is None:
        raise ValueError("commit must be a full lowercase Git object ID")
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=repo,
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return sha256_bytes(result.stdout)


def verify_git_chain(repo: Path, stages: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Verify committed file bytes and ordered ancestor binding.

    Each stage has exactly ``name``, ``commit``, ``path`` and ``sha256``;
    stage order is registration, population, BASE, prediction, interventions.
    """
    repo = Path(repo)
    checked = []
    previous = None
    for stage in stages:
        name, commit, path, wanted = (stage[k] for k in ("name", "commit", "path", "sha256"))
        actual = git_blob_sha256(repo, commit, path)
        if actual != wanted:
            raise ValueError(f"Git-committed blob SHA256 mismatch at {name}: {path}")
        if previous is not None:
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", previous, commit], cwd=repo,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                raise ValueError(f"Git seal chain is not ancestor ordered: {previous} -> {commit}")
        checked.append({"name": name, "commit": commit, "path": path, "sha256": actual})
        previous = commit
    return {"status": "pass", "stages": checked}


def _evidence_refs(tree: Any) -> set[str]:
    if isinstance(tree, dict):
        if set(tree) == {EVIDENCE_ARRAY_SENTINEL}:
            value = tree[EVIDENCE_ARRAY_SENTINEL]
            if not isinstance(value, str):
                raise ValueError("invalid evidence array reference")
            return {value}
        if set(tree) == {EVIDENCE_TUPLE_SENTINEL}:
            return _evidence_refs(tree[EVIDENCE_TUPLE_SENTINEL])
        refs: set[str] = set()
        for value in tree.values():
            refs.update(_evidence_refs(value))
        return refs
    if isinstance(tree, list):
        refs: set[str] = set()
        for value in tree:
            refs.update(_evidence_refs(value))
        return refs
    return set()


def _evidence_unpack(tree: Any, arrays: Mapping[str, np.ndarray]) -> Any:
    if isinstance(tree, dict):
        if set(tree) == {EVIDENCE_ARRAY_SENTINEL}:
            return arrays[tree[EVIDENCE_ARRAY_SENTINEL]].copy()
        if set(tree) == {EVIDENCE_TUPLE_SENTINEL}:
            return tuple(_evidence_unpack(v, arrays) for v in tree[EVIDENCE_TUPLE_SENTINEL])
        return {k: _evidence_unpack(v, arrays) for k, v in tree.items()}
    if isinstance(tree, list):
        return [_evidence_unpack(v, arrays) for v in tree]
    return tree


def load_sealed_artifact(path: Path, expected_sha256: str, expected_identity: Mapping[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
    """Safely parse the frozen evidence envelope (NumPy allow_pickle=False)."""
    path = Path(path)
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha256:
        raise ValueError(f"artifact SHA256 mismatch: {path}")
    try:
        with np.load(path, allow_pickle=False) as archive:
            if EVIDENCE_METADATA_KEY not in archive.files:
                raise ValueError(f"evidence metadata missing: {path}")
            metadata_array = np.asarray(archive[EVIDENCE_METADATA_KEY])
            if metadata_array.dtype != np.uint8 or metadata_array.ndim != 1:
                raise ValueError(f"evidence metadata encoding invalid: {path}")
            envelope = json.loads(metadata_array.tobytes().decode("utf-8"))
            if envelope.get("format_version") != EVIDENCE_FORMAT_VERSION:
                raise ValueError(f"evidence format version invalid: {path}")
            identity = envelope.get("identity")
            if not isinstance(identity, dict):
                raise ValueError(f"evidence identity invalid: {path}")
            if expected_identity is not None and identity != dict(expected_identity):
                raise ValueError(f"evidence identity differs: {path}")
            refs = _evidence_refs(envelope.get("payload"))
            if refs != set(archive.files) - {EVIDENCE_METADATA_KEY}:
                raise ValueError(f"evidence array inventory differs: {path}")
            arrays = {key: np.asarray(archive[key]) for key in refs}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as error:
        raise ValueError(f"cannot parse saved evidence artifact {path}: {error}") from error
    return _evidence_unpack(envelope["payload"], arrays), identity


def load_truth_after_observed_commit(
    repo: Path,
    git_stages: Sequence[Mapping[str, str]],
    truth_artifact: Path,
    truth_sha256: str,
    expected_identity: Mapping[str, Any] | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Truth gate: prove protocol/registration/prediction/observed Git chain first."""
    required = ("protocol", "registration", "prediction", "observed")
    names = [stage["name"] for stage in git_stages]
    positions = [names.index(name) for name in required if name in names]
    if len(positions) != len(required) or positions != sorted(positions) or names[-1] != "observed":
        raise ValueError("truth gate requires ordered protocol, registration, prediction, observed commits")
    proof = verify_git_chain(repo, git_stages)
    payload, identity = load_sealed_artifact(truth_artifact, truth_sha256, expected_identity)
    proof["truth_authorized_after_observed_seal"] = True
    proof["truth_artifact_sha256"] = truth_sha256
    return payload, {"identity": identity, "proof": proof}


def verify_stream_freshness(new_stream_ids: Iterable[str], old_stream_ids: Iterable[str]) -> dict[str, int]:
    new_values, old_values = list(new_stream_ids), list(old_stream_ids)
    new, old = set(new_values), set(old_values)
    if len(new) != len(new_values):
        raise ValueError("new stream identity list contains duplicates")
    collisions = sorted(new & old)
    if collisions:
        raise ValueError(f"random stream namespace collides with old population: {collisions[:5]}")
    return {"new_streams": len(new), "old_streams": len(old), "collisions": 0}


def _exact_row_order(rows: Sequence[Mapping[str, Any]], expected: Sequence[tuple[int, str]], label: str) -> None:
    actual = [(int(row["frame_index"]), str(row["arm"])) for row in rows]
    if actual != list(expected):
        raise ValueError(f"{label} call order/cardinality differs")
    if any(row.get("status") != "ok" for row in rows):
        raise ValueError(f"{label} contains a failed or incomplete attempt")


def verify_call_ledgers(
    base_rows: Sequence[Mapping[str, Any]],
    intervention_rows: Sequence[Mapping[str, Any]],
    intervention_arm_order: Sequence[str],
) -> dict[str, Any]:
    """Recount fixed BASE-first / paired intervention order and frame bindings."""
    if len(intervention_arm_order) != FRAMES or any(x not in (("CGR", "SHAM"), ("SHAM", "CGR")) for x in intervention_arm_order):
        raise ValueError("registered intervention schedule must contain one two-arm order per frame")
    base_expected = [(i, "BASE") for i in range(FRAMES)]
    intervention_expected = [
        (i, arm) for i, pair in enumerate(intervention_arm_order) for arm in pair
    ]
    _exact_row_order(base_rows, base_expected, "BASE")
    _exact_row_order(intervention_rows, intervention_expected, "intervention")
    all_rows = list(base_rows) + list(intervention_rows)
    if [int(row["call_index"]) for row in all_rows] != list(range(1, 769)):
        raise ValueError("global call_index must be contiguous 1..768 with BASE phase first")
    cgr_first = sum(pair[0] == "CGR" for pair in intervention_arm_order)
    sham_first = FRAMES - cgr_first
    if (cgr_first, sham_first) != (128, 128):
        raise ValueError("intervention order is not balanced 128/128")
    base_inputs = {int(row["frame_index"]): row["input_sha256"] for row in base_rows}
    for row in intervention_rows:
        if row["input_sha256"] != base_inputs[int(row["frame_index"])]:
            raise ValueError("arm input identity differs from its BASE observation")
    return {
        "frames": FRAMES,
        "calls": len(base_rows) + len(intervention_rows),
        "base_calls": len(base_rows),
        "intervention_calls": len(intervention_rows),
        "cgr_first_pairs": cgr_first,
        "sham_first_pairs": sham_first,
    }


def verify_prediction_cohort(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Re-derive the sealed E mask and enforce explicit zero predictions.

    Normalized prediction rows use: frame_index, base_triggered,
    base_branch_success, max_abs_R_minus_I, predicted_norms, eligible,
    predicted and predicted_clipped (each keyed CGR/SHAM).
    """
    if len(rows) != FRAMES or [int(row["frame_index"]) for row in rows] != list(range(FRAMES)):
        raise ValueError("prediction cohort table must have ordered frames 0..255")
    members, exclusions = [], []
    for row in rows:
        triggered = bool(row["base_triggered"])
        branch_ok = bool(row["base_branch_success"])
        reaction = float(row["max_abs_R_minus_I"])
        norms = {arm: float(row["predicted_norms"][arm]) for arm in ("CGR", "SHAM")}
        if not math.isfinite(reaction) or any(not math.isfinite(n) or n < 0 for n in norms.values()):
            raise ValueError("reaction and predicted norms must be finite and nonnegative")
        expected = triggered and branch_ok and reaction > 1e-10 and all(n > 1e-8 for n in norms.values())
        if bool(row["eligible"]) != expected:
            raise ValueError(f"sealed eligibility differs from exact threshold rule at frame {row['frame_index']}")
        if not expected:
            exclusions.append(int(row["frame_index"]))
        else:
            members.append(int(row["frame_index"]))
        if not triggered or not branch_ok or reaction <= 1e-10:
            for kind in ("predicted", "predicted_clipped"):
                for arm in ("CGR", "SHAM"):
                    vector = _vector(row[kind][arm], name=f"frame {row['frame_index']} {kind}/{arm}")
                    if np.any(vector != 0):
                        raise ValueError(f"nonzero prediction for bypass/failed/zero-reaction frame {row['frame_index']}")
        for arm in ("CGR", "SHAM"):
            vector = _vector(row["predicted"][arm], name=f"{arm} predicted")
            if not np.isclose(np.linalg.norm(vector), norms[arm], rtol=1e-12, atol=1e-12):
                raise ValueError(f"predicted norm metadata differs at frame {row['frame_index']}/{arm}")
    return {"frames": FRAMES, "eligible_count": len(members), "eligible_frame_indices": members,
            "excluded_frame_indices": exclusions, "mask": [i in set(members) for i in range(FRAMES)]}


def _vector(value: Any, *, name: str, size: int = 2048) -> np.ndarray:
    result = np.asarray(value)
    if result.dtype != np.dtype(np.float64) or result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"{name} must be a finite float64[{size}] vector; got {result.dtype}/{result.shape}")
    return result


def _sign_test(wins: int, losses: int) -> float:
    """Exact one-sided P[Binomial(wins+losses,.5) >= wins]."""
    n = wins + losses
    if n == 0:
        return 1.0
    return math.fsum(math.comb(n, k) for k in range(wins, n + 1)) / (2 ** n)


def holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    if not p_values:
        return {}
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    m = len(ordered)
    adjusted_sorted = []
    running = 0.0
    for index, (name, p_value) in enumerate(ordered):
        running = max(running, min(1.0, (m - index) * float(p_value)))
        adjusted_sorted.append((name, running))
    return dict(adjusted_sorted)


def transport_recount(frames: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Recompute framewise own/zero/swapped scores and the four Holm tests.

    Input rows have frame_index, eligible, predicted/actual and their clipped
    variants keyed by CGR and SHAM. Vectors are complete 2048-coordinate LLRs.
    """
    if len(frames) != FRAMES or [int(x["frame_index"]) for x in frames] != list(range(FRAMES)):
        raise ValueError("transport table must contain all 256 ordered frames")
    eligible = [row for row in frames if row["eligible"]]
    normalized = []
    q_by_contrast: dict[str, list[tuple[float, float, float]]] = {f"{a}_{b}": [] for a, b in CONTRASTS}
    for row in eligible:
        predicted = {arm: _vector(row["predicted"][arm], name=f"{arm} predicted") for arm in ("CGR", "SHAM")}
        actual = {arm: _vector(row["actual"][arm], name=f"{arm} actual") for arm in ("CGR", "SHAM")}
        frame_record = {"frame_index": int(row["frame_index"]), "contrasts": {}}
        for arm, reference in CONTRASTS:
            observed = actual[arm]
            own = predicted[arm]
            reference_prediction = np.zeros_like(observed) if reference == "zero" else predicted["SHAM" if arm == "CGR" else "CGR"]
            q_own = float(np.dot(observed - own, observed - own))
            q_ref = float(np.dot(observed - reference_prediction, observed - reference_prediction))
            difference = q_ref - q_own
            tie_threshold = 1e-10 * max(1.0, q_own, q_ref)
            outcome = "tie" if abs(difference) <= tie_threshold else ("win" if difference > 0 else "loss")
            name = f"{arm}_{reference}"
            q_by_contrast[name].append((q_own, q_ref, difference))
            frame_record["contrasts"][name] = {
                "q_own": q_own, "q_reference": q_ref,
                "reference_minus_own": difference, "tie_threshold": tie_threshold,
                "outcome": outcome,
            }
        normalized.append(frame_record)

    tests = {}
    for name, values in q_by_contrast.items():
        wins = sum(x[2] > 1e-10 * max(1.0, x[0], x[1]) for x in values)
        losses = sum(x[2] < -1e-10 * max(1.0, x[0], x[1]) for x in values)
        ties = len(values) - wins - losses
        tests[name] = {"wins": wins, "losses": losses, "ties": ties,
                       "nontied": wins + losses, "p_one_sided": _sign_test(wins, losses)}
    adjusted = holm_adjust({name: test["p_one_sided"] for name, test in tests.items()})
    for name, test in tests.items():
        test["p_holm"] = adjusted[name]

    pooled = {}
    for arm in ("CGR", "SHAM"):
        p_parts, a_parts = [], []
        cp_parts, ca_parts = [], []
        for row in eligible:
            p_parts.append(_vector(row["predicted"][arm], name=f"{arm} predicted"))
            a_parts.append(_vector(row["actual"][arm], name=f"{arm} actual"))
            cp_parts.append(_vector(row["predicted_clipped"][arm], name=f"{arm} predicted clipped"))
            ca_parts.append(_vector(row["actual_clipped"][arm], name=f"{arm} actual clipped"))
        pooled[arm] = {
            "unclipped": _pooled_transport(np.concatenate(p_parts), np.concatenate(a_parts)),
            "derivative_clipped": _pooled_transport(np.concatenate(cp_parts), np.concatenate(ca_parts)),
        }
    # Derivative-clipped predictions are compared against zero and swapped too.
    clipped_contrasts = {}
    for arm in ("CGR", "SHAM"):
        q_own = q_zero = q_swap = dot_own = norm_p = norm_a = 0.0
        for row in eligible:
            a = _vector(row["actual_clipped"][arm], name=f"{arm} actual clipped")
            p = _vector(row["predicted_clipped"][arm], name=f"{arm} predicted clipped")
            ps = _vector(row["predicted_clipped"]["SHAM" if arm == "CGR" else "CGR"], name="swapped clipped prediction")
            q_own += float(np.dot(a - p, a - p))
            q_zero += float(np.dot(a, a))
            q_swap += float(np.dot(a - ps, a - ps))
            dot_own += float(np.dot(a, p))
            norm_p += float(np.dot(p, p))
            norm_a += float(np.dot(a, a))
        clipped_contrasts[arm] = {
            "q_own": q_own, "q_zero": q_zero, "q_swapped": q_swap,
            "beats_zero": q_own < q_zero, "beats_swapped": q_own < q_swap,
            "cosine": dot_own / math.sqrt(norm_a * norm_p) if norm_a > 0 and norm_p > 0 else None,
        }
    holm_gate = bool(tests) and all(test["nontied"] >= 8 and test["p_holm"] <= .05 for test in tests.values())
    pooled_gate = bool(eligible) and all(
        pooled[arm]["unclipped"]["normalized_error"] < 1 and pooled[arm]["unclipped"]["cosine"] is not None and pooled[arm]["unclipped"]["cosine"] > 0
        and pooled[arm]["derivative_clipped"]["normalized_error"] < 1 and pooled[arm]["derivative_clipped"]["cosine"] is not None and pooled[arm]["derivative_clipped"]["cosine"] > 0
        and clipped_contrasts[arm]["beats_zero"] and clipped_contrasts[arm]["beats_swapped"]
        for arm in ("CGR", "SHAM")
    )
    return {
        "eligible_frames": len(eligible), "framewise": normalized,
        "sign_tests": tests, "pooled": pooled,
        "derivative_clipped_pairwise": clipped_contrasts,
        "holm_gate": holm_gate, "pooled_transport_gate": pooled_gate,
        "transport_gate": len(eligible) >= 8 and holm_gate and pooled_gate,
    }


def _pooled_transport(predicted: np.ndarray, actual: np.ndarray) -> dict[str, float | None]:
    error = predicted - actual
    p_norm = float(np.linalg.norm(predicted))
    a_norm = float(np.linalg.norm(actual))
    e_norm = float(np.linalg.norm(error))
    return {
        "predicted_norm": p_norm, "actual_norm": a_norm,
        "error_norm": e_norm,
        "normalized_error": e_norm / a_norm if a_norm > 0 else None,
        "cosine": float(np.dot(predicted, actual) / (p_norm * a_norm)) if p_norm > 0 and a_norm > 0 else None,
    }


def _binom_tail_geq(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    if k <= 0:
        return 1.0
    return math.fsum(math.comb(n, j) for j in range(k, n + 1)) / (2 ** n)


def _wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total == 0:
        return None
    p = successes / total
    z2 = z * z
    denominator = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denominator
    half = z * math.sqrt((p * (1 - p) / total) + z2 / (4 * total * total)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def verify_code_bundle(H: Any, G: Any, free_cols: Any,
                      truth_coded: Any, truth_info: Any) -> dict[str, Any]:
    Hm, Gm = np.asarray(H), np.asarray(G)
    cols = np.asarray(free_cols)
    coded, info = np.asarray(truth_coded), np.asarray(truth_info)
    if (Hm.ndim != 2 or Hm.shape[1] != 2048 or not np.isin(Hm, (0, 1)).all()
            or cols.ndim != 1 or not np.issubdtype(cols.dtype, np.integer)
            or len(np.unique(cols)) != len(cols) or np.any(cols < 0) or np.any(cols >= 2048)
            or Gm.shape != (2048, len(cols)) or not np.isin(Gm, (0, 1)).all()
            or coded.dtype != np.dtype(np.uint8) or coded.shape != (2048,)
            or info.dtype != np.dtype(np.uint8) or info.shape != (len(cols),)
            or not np.isin(coded, (0, 1)).all() or not np.isin(info, (0, 1)).all()):
        raise ValueError("registered H/G/free_cols and truth dimensions/types differ")
    if not np.array_equal(Gm[cols, :], np.eye(len(cols), dtype=Gm.dtype)):
        raise ValueError("registered N-by-K G is not systematic on actual free_cols")
    if not np.array_equal((Gm.astype(np.int64) @ info.astype(np.int64)) & 1, coded):
        raise ValueError("coded truth does not equal registered info @ G over GF(2)")
    if not np.array_equal(coded[cols], info):
        raise ValueError("coded truth differs from registered info on free_cols")
    if np.any((Hm.astype(np.int64) @ coded.astype(np.int64)) & 1):
        raise ValueError("tagged truth coded word is not valid under registered H")
    return {"H_shape": list(Hm.shape), "G_shape": list(Gm.shape), "free_cols": len(cols),
            "truth_coded_bits": len(coded), "truth_info_bits": len(info), "status": "pass"}


def outcome_recount(
    frame_rows: Sequence[Mapping[str, Any]], H: Any, G: Any, free_cols: Any,
) -> dict[str, Any]:
    """Recompute exact information/coded errors and pairwise tables from bits."""
    if len(frame_rows) != FRAMES or [int(row["frame_index"]) for row in frame_rows] != list(range(FRAMES)):
        raise ValueError("outcome table must contain all 256 ordered frames")
    Hm = np.asarray(H, dtype=np.uint8)
    Gm = np.asarray(G)
    raw_cols = np.asarray(free_cols)
    if not np.issubdtype(raw_cols.dtype, np.integer):
        raise ValueError("free_cols must have an integer dtype")
    cols = raw_cols.astype(np.int64, copy=False)
    if Hm.ndim != 2 or Hm.shape[1] != 2048 or cols.ndim != 1 or len(np.unique(cols)) != len(cols) or np.any(cols < 0) or np.any(cols >= 2048):
        raise ValueError("actual H/free_cols dimensions or indices invalid")
    assessed = []
    for row in frame_rows:
        truth = np.asarray(row["truth_coded"])
        if truth.dtype != np.dtype(np.uint8) or truth.shape != (2048,) or not np.isin(truth, (0, 1)).all():
            raise ValueError("truth_coded must be binary[2048]")
        truth_info = np.asarray(row["truth_info"])
        verify_code_bundle(Hm, Gm, cols, truth, truth_info)
        arm_out = {}
        for arm in ARMS:
            decoded = np.asarray(row["decoded"][arm])
            if decoded.dtype != np.dtype(np.uint8) or decoded.shape != (2048,) or not np.isin(decoded, (0, 1)).all():
                raise ValueError(f"{arm} decoded must be binary[2048]")
            syndrome = (Hm.astype(np.int64) @ decoded.astype(np.int64)) & 1
            info_wrong = not np.array_equal(decoded[cols], truth_info)
            coded_wrong = not np.array_equal(decoded, truth)
            arm_out[arm] = {
                "info_wrong": info_wrong,
                "info_bit_errors": int(np.count_nonzero(decoded[cols] != truth_info)),
                "coded_wrong": coded_wrong,
                "coded_bit_errors": int(np.count_nonzero(decoded != truth)),
                "syndrome_weight": int(np.count_nonzero(syndrome)),
                "valid_but_wrong": bool(np.count_nonzero(syndrome) == 0 and info_wrong),
            }
        assessed.append({"frame_index": int(row["frame_index"]), "arms": arm_out})

    pairwise = {}
    for left, right in (("BASE", "CGR"), ("BASE", "SHAM"), ("CGR", "SHAM")):
        both_correct = left_only = right_only = both_wrong = 0
        for row in assessed:
            le, re_ = row["arms"][left]["info_wrong"], row["arms"][right]["info_wrong"]
            if not le and not re_: both_correct += 1
            elif not le and re_: left_only += 1
            elif le and not re_: right_only += 1
            else: both_wrong += 1
        discordant = left_only + right_only
        # d=+1 means the second arm fixes an error made by the first;
        # d=-1 means the reverse. This paired score retains concordant frames.
        paired_differences = [
            int(row["arms"][left]["info_wrong"]) - int(row["arms"][right]["info_wrong"])
            for row in assessed
        ]
        paired_mean = sum(paired_differences) / FRAMES
        paired_ss = sum(x * x for x in paired_differences)
        paired_variance = max(0.0, (paired_ss - FRAMES * paired_mean * paired_mean) / (FRAMES - 1))
        paired_half = 1.959963984540054 * math.sqrt(paired_variance / FRAMES)
        pairwise[f"{left}_vs_{right}"] = {
            "both_correct": both_correct, "left_only_correct": left_only,
            "right_only_correct": right_only, "both_wrong": both_wrong,
            "n": FRAMES, "discordant": discordant,
            "p_second_arm_better_one_sided": _binom_tail_geq(right_only, discordant),
            "second_arm_rescue_fraction_among_discordant_wilson95": _wilson_interval(right_only, discordant),
            "paired_info_FER_difference_second_minus_first": -paired_mean,
            "paired_info_FER_difference_wald95": [max(-1.0, -paired_mean - paired_half), min(1.0, -paired_mean + paired_half)],
        }
    base_failures = sum(row["arms"]["BASE"]["info_wrong"] for row in assessed)
    rescue_harm = {}
    for arm in ("CGR", "SHAM"):
        rescue_harm[arm] = {
            "rescued": sum(row["arms"]["BASE"]["info_wrong"] and not row["arms"][arm]["info_wrong"] for row in assessed),
            "harmed": sum(not row["arms"]["BASE"]["info_wrong"] and row["arms"][arm]["info_wrong"] for row in assessed),
            "net_rescues": sum(row["arms"]["BASE"]["info_wrong"] and not row["arms"][arm]["info_wrong"] for row in assessed) - sum(not row["arms"]["BASE"]["info_wrong"] and row["arms"][arm]["info_wrong"] for row in assessed),
            "valid_but_wrong": sum(row["arms"][arm]["valid_but_wrong"] for row in assessed),
            "new_valid_but_wrong_vs_BASE": sum(row["arms"][arm]["valid_but_wrong"] and not row["arms"]["BASE"]["valid_but_wrong"] for row in assessed),
            "info_bit_errors": sum(row["arms"][arm]["info_bit_errors"] for row in assessed),
            "coded_frame_errors": sum(row["arms"][arm]["coded_wrong"] for row in assessed),
            "coded_bit_errors": sum(row["arms"][arm]["coded_bit_errors"] for row in assessed),
            "syndrome_nonzero_frames": sum(row["arms"][arm]["syndrome_weight"] > 0 for row in assessed),
        }
    rescue_gate = (
        base_failures >= 2 and rescue_harm["CGR"]["rescued"] >= 2
        and rescue_harm["CGR"]["harmed"] == 0
        and rescue_harm["CGR"]["new_valid_but_wrong_vs_BASE"] == 0
        and rescue_harm["CGR"]["net_rescues"] >= rescue_harm["SHAM"]["net_rescues"] + 1
    )
    return {
        "frames": assessed, "base_info_failures": base_failures,
        "pairwise": pairwise, "rescue_harm": rescue_harm,
        "info_FER_by_arm": {
            arm: {
                "errors": sum(row["arms"][arm]["info_wrong"] for row in assessed),
                "total": FRAMES,
                "estimate": sum(row["arms"][arm]["info_wrong"] for row in assessed) / FRAMES,
                "wilson95": _wilson_interval(sum(row["arms"][arm]["info_wrong"] for row in assessed), FRAMES),
            }
            for arm in ARMS
        },
        "recovery_status": "insufficient" if base_failures < 2 else ("pass" if rescue_gate else "fail"),
        "recovery_gate": rescue_gate,
    }


def frame_logloss(coded_truth: Any, clipped_llr: Any) -> dict[str, float | int]:
    truth = np.asarray(coded_truth)
    llr = _vector(clipped_llr, name="clipped final decoder input")
    if truth.dtype != np.dtype(np.uint8) or truth.shape != (2048,) or not np.isin(truth, (0, 1)).all():
        raise ValueError("coded truth must be binary[2048]")
    signed = (1.0 - 2.0 * truth.astype(np.float64)) * llr
    loss = float(np.logaddexp(0.0, -signed).mean())
    wrong = signed < 0
    wrong_confidence = float(np.abs(llr[wrong]).sum())
    wrong_count = int(np.count_nonzero(wrong))
    return {
        "mean_logloss": loss,
        "wrong_sign_bits": wrong_count,
        "wrong_confidence_sum": wrong_confidence,
        "wrong_confidence_mean": wrong_confidence / wrong_count if wrong_count else 0.0,
    }


def logloss_recount(
    frame_rows: Sequence[Mapping[str, Any]], *, analysis_seed: int,
    bootstrap_resamples: int = 20000,
) -> dict[str, Any]:
    if len(frame_rows) != FRAMES or [int(row["frame_index"]) for row in frame_rows] != list(range(FRAMES)):
        raise ValueError("logloss input must contain all 256 ordered frames")
    losses = {arm: np.empty(FRAMES, dtype=np.float64) for arm in ARMS}
    wrong = {arm: {"count": 0, "confidence_sum": 0.0} for arm in ARMS}
    for index, row in enumerate(frame_rows):
        truth = np.asarray(row["truth_coded"])
        if truth.dtype != np.dtype(np.uint8):
            raise ValueError("truth_coded must retain uint8 dtype")
        for arm in ARMS:
            detail = frame_logloss(truth, row["clipped_final_llr"][arm])
            losses[arm][index] = detail["mean_logloss"]
            wrong[arm]["count"] += detail["wrong_sign_bits"]
            wrong[arm]["confidence_sum"] += detail["wrong_confidence_sum"]
    e_indices = np.asarray([i for i, row in enumerate(frame_rows) if row.get("eligible")], dtype=np.int64)
    t_indices = np.asarray([i for i, row in enumerate(frame_rows) if row.get("base_triggered")], dtype=np.int64)
    def paired_bootstrap(left: np.ndarray, right: np.ndarray, indices: np.ndarray,
                         *, seed: int) -> dict[str, Any]:
        if len(indices) == 0:
            return {"n": 0, "mean_difference": None, "ci95_percentile": None}
        d = left[indices] - right[indices]
        rng = np.random.default_rng(int(seed))
        picks = rng.integers(0, len(indices), size=(bootstrap_resamples, len(indices)))
        boot = d[picks].mean(axis=1)
        return {"n": len(indices), "mean_difference": float(d.mean()),
                "ci95_percentile": [float(x) for x in np.quantile(boot, [.025, .975])],
                "resamples": bootstrap_resamples}
    comparisons = {}
    for left, right, label, offset in (("CGR", "BASE", "CGR_minus_BASE", 0), ("CGR", "SHAM", "CGR_minus_SHAM", 1)):
        # Match the frozen analyzer's registered deterministic seed schedule:
        # all, T, E; each paired contrast has a separate deterministic stream.
        comparisons[label] = {
            "all256": paired_bootstrap(losses[left], losses[right], np.arange(FRAMES),
                                          seed=int(analysis_seed) + offset),
            "T": paired_bootstrap(losses[left], losses[right], t_indices,
                                    seed=int(analysis_seed) + 2 + offset),
            "E": paired_bootstrap(losses[left], losses[right], e_indices,
                                    seed=int(analysis_seed) + 4 + offset),
        }
    all_cgr_base = comparisons["CGR_minus_BASE"]["all256"]["mean_difference"]
    l_gate = (
        comparisons["CGR_minus_BASE"]["E"]["mean_difference"] is not None
        and comparisons["CGR_minus_BASE"]["E"]["mean_difference"] < 0
        and comparisons["CGR_minus_SHAM"]["E"]["mean_difference"] is not None
        and comparisons["CGR_minus_SHAM"]["E"]["mean_difference"] < 0
        and all_cgr_base is not None and all_cgr_base <= 0
    )
    return {
        "n_all": FRAMES, "n_triggered": int(len(t_indices)), "n_eligible": int(len(e_indices)),
        "mean_by_arm": {arm: float(values.mean()) for arm, values in losses.items()},
        "triggered_mean_by_arm": {arm: float(losses[arm][t_indices].mean()) if len(t_indices) else None for arm in ARMS},
        "eligible_mean_by_arm": {arm: float(losses[arm][e_indices].mean()) if len(e_indices) else None for arm in ARMS},
        "wrong_sign_and_confidence": wrong, "paired_comparisons": comparisons,
        "analysis_seed": int(analysis_seed), "bootstrap_resamples": bootstrap_resamples,
        "logloss_gate": bool(l_gate),
    }


def compose_final_gates(
    integrity_checks: Mapping[str, bool],
    transport: Mapping[str, Any],
    outcomes: Mapping[str, Any],
    logloss: Mapping[str, Any],
    *,
    unexpected_fallbacks: int,
) -> dict[str, Any]:
    """Apply protocol I/M/U/L meanings without trusting a producer summary."""
    failed_checks = sorted(name for name, passed in integrity_checks.items() if not passed)
    if unexpected_fallbacks < 0:
        raise ValueError("unexpected fallback count cannot be negative")
    if unexpected_fallbacks:
        failed_checks.append("zero_unexpected_numerical_fallbacks")
    i_gate = not failed_checks
    m_gate = bool(transport["transport_gate"])
    u_gate = bool(outcomes["recovery_gate"])
    l_gate = bool(logloss["logloss_gate"])
    return {
        "I": {"pass": i_gate, "failed_checks": failed_checks,
              "unexpected_fallbacks": unexpected_fallbacks},
        "M": {"pass": m_gate, "eligible_frames": transport["eligible_frames"],
              "sign_tests": transport["sign_tests"], "pooled": transport["pooled"]},
        "U": {"pass": u_gate, "recovery_status": outcomes["recovery_status"],
              "base_info_failures": outcomes["base_info_failures"],
              "rescue_harm": outcomes["rescue_harm"], "pairwise": outcomes["pairwise"]},
        "L": {"pass": l_gate, "paired_comparisons": logloss["paired_comparisons"],
              "mean_by_arm": logloss["mean_by_arm"],
              "wrong_sign_and_confidence": logloss["wrong_sign_and_confidence"]},
        "prospective_mechanism_supported": bool(i_gate and m_gate),
        "bounded_continue": bool(i_gate and m_gate and u_gate and l_gate),
    }


def synthetic_self_check() -> dict[str, Any]:
    """Small deterministic checks for exact tails, Holm, and tie handling."""
    if _sign_test(4, 0) != 1 / 16:
        raise AssertionError("exact sign tail changed")
    adjusted = holm_adjust({"p1": .01, "p2": .04, "p3": .03, "p4": .20})
    if adjusted != {"p1": .04, "p3": .09, "p2": .09, "p4": .20}:
        raise AssertionError(f"Holm adjustment changed: {adjusted}")
    zeros = np.zeros(2048, dtype=np.float64)
    rows = []
    for i in range(FRAMES):
        p = np.ones(2048) if i % 2 == 0 else zeros.copy()
        a = np.ones(2048)
        rows.append({"frame_index": i, "eligible": True,
            "predicted": {"CGR": p, "SHAM": zeros}, "actual": {"CGR": a, "SHAM": a},
            "predicted_clipped": {"CGR": p, "SHAM": zeros},
            "actual_clipped": {"CGR": a, "SHAM": a}})
    result = transport_recount(rows)
    if result["eligible_frames"] != FRAMES or result["sign_tests"]["CGR_zero"]["nontied"] != FRAMES // 2:
        raise AssertionError("transport frame recount changed")

    schedule = [("CGR", "SHAM")] * 128 + [("SHAM", "CGR")] * 128
    base_ledger = [{"call_index": i + 1, "frame_index": i, "arm": "BASE", "status": "ok", "input_sha256": f"h{i}"} for i in range(FRAMES)]
    intervention_ledger = [
        {"call_index": 257 + 2 * i + offset, "frame_index": i, "arm": arm, "status": "ok", "input_sha256": f"h{i}"}
        for i, pair in enumerate(schedule) for offset, arm in enumerate(pair)
    ]
    counts = verify_call_ledgers(base_ledger, intervention_ledger, schedule)
    if counts["calls"] != 768 or counts["cgr_first_pairs"] != 128 or counts["sham_first_pairs"] != 128:
        raise AssertionError("attempt ledger recount changed")

    H = np.zeros((1, 2048), dtype=np.uint8)
    free_cols = np.arange(4)
    G = np.zeros((4, 2048), dtype=np.uint8)
    G[np.arange(4), free_cols] = 1
    truth = np.zeros(2048, dtype=np.uint8)
    outcome_rows = []
    llr_rows = []
    for i in range(FRAMES):
        base, cgr, sham = (truth.copy() for _ in range(3))
        if i in (0, 1):
            base[0] = 1
        if i == 1:
            sham[1] = 1
        outcome_rows.append({"frame_index": i, "truth_coded": truth, "truth_info": np.zeros(4, dtype=np.uint8),
            "decoded": {"BASE": base, "CGR": cgr, "SHAM": sham}})
        llr_rows.append({"frame_index": i, "eligible": i < 8, "base_triggered": i < 16,
            "truth_coded": truth,
            "clipped_final_llr": {"BASE": np.full(2048, .1), "CGR": np.full(2048, .2), "SHAM": np.full(2048, .05)}})
    outcomes = outcome_recount(outcome_rows, H, G, free_cols)
    if outcomes["base_info_failures"] != 2 or outcomes["rescue_harm"]["CGR"]["rescued"] != 2 or not outcomes["recovery_gate"]:
        raise AssertionError("outcome-bit recount changed")
    logloss = logloss_recount(llr_rows, analysis_seed=9182, bootstrap_resamples=100)
    if not logloss["logloss_gate"]:
        raise AssertionError("coded-bit logloss recount changed")
    if verify_stream_freshness(["n1", "n2"], ["o1", "o2"])["collisions"] != 0:
        raise AssertionError("namespace collision check changed")
    return {"status": "pass", "checks": [
        "exact_sign_tail", "holm", "transport_arrays", "fixed_frame_denominator",
        "256_plus_512_attempt_order", "exact_information_and_coded_bit_counts",
        "one_sided_pairwise_tables", "clipped_coded_bit_logloss_bootstrap", "stream_collision_check",
    ]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("production adapter will be added after the frozen saved-output schema is issued")
    print(json.dumps(synthetic_self_check(), sort_keys=True, indent=2))
