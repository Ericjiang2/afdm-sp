#!/usr/bin/env python3
"""Independently recount sealed-table D/A/Q and saved-vector transport metrics.

This script reads already saved analysis vectors and hash-bound raw observed NPZs.
It does not load truth, import the producer/JVP, or call a receiver/decoder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OBS = ROOT / "results/tf_cgr_mechanism_20260923_v2/observed"
ANALYSIS = ROOT / "results/tf_cgr_offline_mechanism_20260923/analysis"
WITNESS_MANIFEST = ROOT / "results/tf_cgr_mechanism_20260923_v2/witnesses/witness_manifest.json"
TRUTH_ROOT = ROOT / "results/tf_cgr_mechanism_20260923/witnesses"
SEAL_SHA256 = "42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43"
SEAL_COMMIT = "dc228d7254274f3be3403514fc75f0758aacc15c"
TARGETS = {
    "s650_f0390", "s650_f0415", "s650_f0718", "s650_f0720",
    "s650_f0770", "s650_f0996", "s600_f0600", "s700_f0732",
}
ARMS = ("CGR", "SHAM")
META = "__evidence_metadata__"
ARRAY_REF = "__evidence_array__"
TUPLE_REF = "__evidence_tuple__"


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def compare(pred: np.ndarray, actual: np.ndarray) -> dict[str, Any]:
    pred = np.asarray(pred, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    require(pred.shape == actual.shape and pred.ndim == 1, "prediction/actual vector shape differs")
    require(np.isfinite(pred).all() and np.isfinite(actual).all(), "nonfinite comparison vector")
    actual_norm = float(np.linalg.norm(actual))
    predicted_norm = float(np.linalg.norm(pred))
    error = float(np.linalg.norm(pred - actual))
    return {
        "actual_norm": actual_norm,
        "predicted_norm": predicted_norm,
        "normalized_error": error / actual_norm if actual_norm else None,
        "error_to_zero_predictor": error / actual_norm if actual_norm else None,
        "zero_predictor_normalized_error": 1.0 if actual_norm else None,
        "improvement_over_zero_fraction": 1.0 - error / actual_norm if actual_norm else None,
        "beats_zero_predictor": bool(error < actual_norm) if actual_norm else None,
        "cosine": float(np.dot(pred, actual) / (predicted_norm * actual_norm))
        if predicted_norm and actual_norm else None,
    }


def ref_value(tree: Any, arrays: dict[str, np.ndarray]) -> Any:
    if isinstance(tree, dict) and set(tree) == {ARRAY_REF}:
        return arrays[tree[ARRAY_REF]]
    if isinstance(tree, dict) and set(tree) == {TUPLE_REF}:
        return tuple(ref_value(x, arrays) for x in tree[TUPLE_REF])
    if isinstance(tree, dict):
        return {k: ref_value(v, arrays) for k, v in tree.items()}
    if isinstance(tree, list):
        return [ref_value(x, arrays) for x in tree]
    return tree


def load_raw(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        require(META in archive.files, f"missing raw evidence metadata: {path}")
        raw_meta = np.asarray(archive[META])
        require(raw_meta.dtype == np.uint8 and raw_meta.ndim == 1, f"bad evidence metadata: {path}")
        envelope = json.loads(raw_meta.tobytes().decode("utf-8"))
        require(envelope.get("format_version") == 2, f"raw evidence version differs: {path}")
        tree = envelope.get("payload")
        refs = set()

        def collect(node):
            if isinstance(node, dict):
                if set(node) == {ARRAY_REF}:
                    refs.add(node[ARRAY_REF])
                elif set(node) == {TUPLE_REF}:
                    for child in node[TUPLE_REF]:
                        collect(child)
                else:
                    for child in node.values():
                        collect(child)
            elif isinstance(node, list):
                for child in node:
                    collect(child)

        collect(tree)
        require(refs == set(archive.files) - {META}, f"raw NPZ array inventory differs: {path}")
        arrays = {key: np.asarray(archive[key]).copy() for key in refs}
        require(all(not arr.dtype.hasobject for arr in arrays.values()), f"object array in raw NPZ: {path}")
    return ref_value(tree, arrays)


def load_coded_truth(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Read only the hash-bound coded-bit array; leave all other truth arrays unopened."""
    with np.load(path, allow_pickle=False) as archive:
        require(META in archive.files, f"missing truth evidence metadata: {path}")
        metadata = np.asarray(archive[META])
        require(metadata.dtype == np.uint8 and metadata.ndim == 1, f"bad truth metadata: {path}")
        envelope = json.loads(metadata.tobytes().decode("utf-8"))
        require(envelope.get("format_version") == 2, f"truth evidence version differs: {path}")
        identity = envelope.get("identity") or {}
        tree = envelope.get("payload") or {}
        coded_ref = tree.get("coded") if isinstance(tree, dict) else None
        require(isinstance(coded_ref, dict) and set(coded_ref) == {ARRAY_REF},
                f"truth payload lacks direct coded-bit array: {path}")
        coded = np.asarray(archive[coded_ref[ARRAY_REF]]).copy()
        require(coded.dtype == np.uint8 and coded.shape == (2048,) and np.isin(coded, [0, 1]).all(),
                f"coded-bit array schema differs: {path}")
    return coded, identity


def logscore(llr: np.ndarray, coded: np.ndarray) -> dict[str, Any]:
    llr = np.asarray(llr, dtype=np.float64)
    coded = np.asarray(coded, dtype=np.uint8)
    require(llr.shape == coded.shape == (2048,) and np.isfinite(llr).all(), "logscore vectors differ")
    signed = (1.0 - 2.0 * coded.astype(np.float64)) * llr
    wrong = signed < 0
    wrong_confidence = -signed[wrong]
    return {
        "mean_bit_log_loss": float(np.logaddexp(0.0, -signed).mean()),
        "wrong_sign_bits": int(wrong.sum()),
        "wrong_confidence_sum": float(wrong_confidence.sum()),
        "wrong_confidence_mean": float(wrong_confidence.mean()) if wrong.any() else 0.0,
    }


def close(actual: float, expected: float, tol: float = 2e-10) -> bool:
    return abs(actual - expected) <= tol * max(1.0, abs(expected))


def clip_jvp(base: np.ndarray, slope: np.ndarray) -> tuple[np.ndarray, int]:
    """Apply the declared one-sided derivative of clip(-20, 20) to saved JVP."""
    result = np.asarray(slope, dtype=np.float64).copy()
    base = np.asarray(base, dtype=np.float64)
    result[(base > 20) | (base < -20)] = 0
    result[(base == 20) & (result > 0)] = 0
    result[(base == -20) & (result < 0)] = 0
    return result, int(np.count_nonzero(np.abs(base) == 20))


def run(output: Path) -> dict[str, Any]:
    seal_path = OBS / "observed_seal.json"
    seal_bytes = seal_path.read_bytes()
    seal_sha = hashlib.sha256(seal_bytes).hexdigest()
    require(seal_sha == SEAL_SHA256, "observed seal SHA differs")
    repo = ROOT.parents[1]
    repo_seal_path = "00_Inbox/AFDM-channel-estimation/results/tf_cgr_mechanism_20260923_v2/observed/observed_seal.json"
    committed = subprocess.run(["git", "-C", str(repo), "show", f"{SEAL_COMMIT}:{repo_seal_path}"],
                               check=True, capture_output=True).stdout
    require(committed == seal_bytes, "observed seal commit blob differs")
    seal = json.loads(seal_bytes)
    file_hashes = seal["files"]
    witness_manifest_sha = sha256(WITNESS_MANIFEST)
    require(witness_manifest_sha == seal["witness_manifest_sha256"], "witness manifest SHA differs from seal")
    witness_manifest = json.loads(WITNESS_MANIFEST.read_text())
    truth_entries = {
        entry["observation_id"]: next(item for item in entry["files"] if item["kind"] == "truth")
        for entry in witness_manifest["entries"]
    }

    transport_path = ANALYSIS / "transport.json"
    finite_path = ANALYSIS / "finite_panel.json"
    transport = json.loads(transport_path.read_text())
    finite = json.loads(finite_path.read_text())
    require(len(transport) == 8, f"transport row count differs: {len(transport)}")
    require({row["observation_id"] for row in transport} == TARGETS, "transport target cohort differs")
    require(len(finite) == 160, f"finite panel row count differs: {len(finite)}")
    finite_keys = [(row["observation_id"], row["iteration"]) for row in finite]
    require(len(set(finite_keys)) == 160, "duplicate finite-panel frame/iteration")
    require(set(f for f, _ in finite_keys) == TARGETS, "finite-panel target cohort differs")
    d_aq_residuals = []
    finite_frames = []
    for frame in sorted(TARGETS):
        rows = sorted((r for r in finite if r["observation_id"] == frame), key=lambda x: x["iteration"])
        require(len(rows) == 20 and [r["iteration"] for r in rows] == list(range(20)),
                f"finite panel missing 20 indexed rows: {frame}")
        for row in rows:
            d, q, a = (float(row[key]) for key in ("finite_D", "quadratic_Q", "first_order_A"))
            require(np.isfinite([d, q, a]).all(), f"nonfinite D/A/Q: {frame}/{row['iteration']}")
            d_aq_residuals.append(d - (a - q))
        finite_frames.append({
            "observation_id": frame,
            "iterations": 20,
            "sum_finite_D": float(sum(r["finite_D"] for r in rows)),
            "sum_first_order_A": float(sum(r["first_order_A"] for r in rows)),
            "sum_quadratic_Q": float(sum(r["quadratic_Q"] for r in rows)),
            "positive_D_rows": int(sum(r["finite_D"] > 0 for r in rows)),
            "positive_A_rows": int(sum(r["first_order_A"] > 0 for r in rows)),
        })
    max_d_aq = float(np.max(np.abs(d_aq_residuals)))
    require(max_d_aq <= 1e-12, f"D=A-Q identity exceeds tolerance: {max_d_aq}")

    ledger = [json.loads(line) for line in (OBS / "ledger.jsonl").read_text().splitlines()]
    ledger_by_pair = {(row["observation_id"], row["arm"]): row for row in ledger}
    require(len(ledger_by_pair) == 100, "sealed ledger row count differs")
    raw_cache: dict[tuple[str, str], dict[str, Any]] = {}
    raw_hashes: dict[str, str] = {}

    def raw(stem: str, arm: str) -> dict[str, Any]:
        key = (stem, arm)
        if key not in raw_cache:
            row = ledger_by_pair[key]
            rel = row["raw_path"]
            require(rel in file_hashes and file_hashes[rel] == row["raw_sha256"],
                    f"ledger raw SHA not sealed: {rel}")
            path = OBS / rel
            actual_sha = sha256(path)
            require(actual_sha == file_hashes[rel], f"raw SHA mismatch: {rel}")
            raw_hashes[rel] = actual_sha
            raw_cache[key] = load_raw(path)
        return raw_cache[key]

    per_frame = []
    pooled_vectors: dict[str, dict[str, list[np.ndarray]]] = {
        mode: {arm: [[], []] for arm in ARMS} for mode in ("unclipped", "clipped")
    }
    metric_reconciliation_max = 0.0
    actual_shift_reconciliation_max = 0.0
    decoder_clip_reconciliation_max = 0.0
    checked_cases = 0
    truth_hashes = {}
    truth_registration_hashes = set()
    pooled_scores: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ("BASE", "CGR", "SHAM", "BLOCK")}
    for frame_row in transport:
        stem = frame_row["observation_id"]
        raw_base = raw(stem, "BASE")
        base_detector = raw_base["branch_detector"]
        base_extrinsic = np.asarray(base_detector["extrinsic"], dtype=np.float64)
        require(base_extrinsic.shape == (2048,), f"BASE extrinsic shape differs: {stem}")
        base_clip = np.clip(base_extrinsic, -20, 20)
        base_decoder = np.asarray(raw_base["branch_decoder"]["incoming_llr"], dtype=np.float64)
        decoder_clip_reconciliation_max = max(decoder_clip_reconciliation_max,
            float(np.max(np.abs(base_clip - base_decoder))))
        frame_result = {"observation_id": stem, "arms": {}}
        for arm in ARMS:
            section = frame_row["predictions"][arm]
            pred = np.asarray(section["predicted_terminal_llr"], dtype=np.float64)
            actual_table = np.asarray(section["actual_terminal_llr_shift"], dtype=np.float64)
            require(pred.shape == actual_table.shape == (2048,), f"saved vector dimensions differ: {stem}/{arm}")
            require(np.isfinite(pred).all() and np.isfinite(actual_table).all(),
                    f"nonfinite saved vector: {stem}/{arm}")
            raw_arm = raw(stem, arm)
            arm_extrinsic = np.asarray(raw_arm["branch_detector"]["extrinsic"], dtype=np.float64)
            require(arm_extrinsic.shape == (2048,), f"arm extrinsic shape differs: {stem}/{arm}")
            actual_from_raw = arm_extrinsic - base_extrinsic
            actual_diff = float(np.max(np.abs(actual_table - actual_from_raw)))
            actual_shift_reconciliation_max = max(actual_shift_reconciliation_max, actual_diff)
            require(actual_diff <= 1e-12, f"table actual shift differs from sealed raw extrinsic: {stem}/{arm}")

            pred_clip, boundary_count = clip_jvp(base_extrinsic, pred)
            actual_clip = np.clip(arm_extrinsic, -20, 20) - base_clip
            raw_arm_decoder = np.asarray(raw_arm["branch_decoder"]["incoming_llr"], dtype=np.float64)
            decoder_clip_reconciliation_max = max(decoder_clip_reconciliation_max,
                float(np.max(np.abs(np.clip(arm_extrinsic, -20, 20) - raw_arm_decoder))))
            require(boundary_count == section["clip_boundary_count"],
                    f"clipping boundary count differs: {stem}/{arm}")

            computed = {"unclipped": compare(pred, actual_from_raw),
                        "clipped": compare(pred_clip, actual_clip)}
            for mode in ("unclipped", "clipped"):
                saved_summary = section[mode]
                for field in ("actual_norm", "predicted_norm", "normalized_error", "error_to_zero_predictor", "cosine"):
                    value = computed[mode][field]
                    expected = saved_summary[field]
                    if value is None or expected is None:
                        require(value is expected, f"null metric differs: {stem}/{arm}/{mode}/{field}")
                    else:
                        delta = abs(value - float(expected))
                        metric_reconciliation_max = max(metric_reconciliation_max, delta)
                        require(close(value, float(expected), 5e-10),
                                f"saved metric differs: {stem}/{arm}/{mode}/{field}: {value} vs {expected}")
                pooled_vectors[mode][arm][0].append(pred if mode == "unclipped" else pred_clip)
                pooled_vectors[mode][arm][1].append(actual_from_raw if mode == "unclipped" else actual_clip)
            per_frame_arm = {
                "unclipped": computed["unclipped"],
                "clipped": computed["clipped"],
                "raw_actual_shift_max_abs_delta": actual_diff,
                "branch_decoder_equals_clipped_extrinsic_max_abs": float(np.max(np.abs(
                    np.clip(arm_extrinsic, -20, 20) - raw_arm_decoder))),
                "clip_boundary_count": boundary_count,
            }
            frame_result["arms"][arm] = per_frame_arm
            checked_cases += 1

        truth_entry = truth_entries[stem]
        truth_rel = Path(truth_entry["relative_path"])
        require(not truth_rel.is_absolute() and ".." not in truth_rel.parts, "unsafe truth witness path")
        truth_path = TRUTH_ROOT / truth_rel
        truth_digest = sha256(truth_path)
        require(truth_digest == truth_entry["sha256"], f"coded truth witness SHA mismatch: {stem}")
        coded, truth_identity = load_coded_truth(truth_path)
        truth_registration_hashes.add(truth_identity.get("registration_sha256"))
        truth_hashes[stem] = {"relative_path": str(truth_rel), "sha256": truth_digest,
                              "coded_dtype": str(coded.dtype), "coded_shape": list(coded.shape),
                              "identity_registration_sha256": truth_identity.get("registration_sha256")}
        saved_scores = frame_row.get("logscore")
        require(isinstance(saved_scores, dict), f"transport missing saved logscore: {stem}")
        computed_scores = {}
        for score_arm in ("BASE", "CGR", "SHAM", "BLOCK"):
            raw_output = raw(stem, score_arm)
            decoder_llr = np.asarray(raw_output["branch_decoder"]["incoming_llr"], dtype=np.float64)
            score = logscore(decoder_llr, coded)
            saved = saved_scores[score_arm]
            for metric, value in score.items():
                if metric == "wrong_sign_bits":
                    require(value == int(saved[metric]), f"logscore wrong-sign count differs: {stem}/{score_arm}")
                else:
                    require(close(value, float(saved[metric]), 5e-12),
                            f"logscore {metric} differs: {stem}/{score_arm}")
            computed_scores[score_arm] = score
            pooled_scores[score_arm].append(score)
        frame_result["logscore"] = computed_scores
        per_frame.append(frame_result)

    require(truth_registration_hashes == {"246b1a2f03fb1f8030f662123416384a9792720f369fff16d00aabe70622ea96"},
            "target truth payload registration identity differs")
    score_totals = {}
    for arm, records in pooled_scores.items():
        score_totals[arm] = {
            "frames": len(records),
            "mean_bit_log_loss_equal_frame_weight": float(np.mean([r["mean_bit_log_loss"] for r in records])),
            "wrong_sign_bits_total_descriptive": int(sum(r["wrong_sign_bits"] for r in records)),
            "wrong_confidence_sum_descriptive": float(sum(r["wrong_confidence_sum"] for r in records)),
            "independence_note": "bit totals are descriptive; bits are not independent experimental units",
        }

    pooled = {}
    for mode in ("unclipped", "clipped"):
        pooled[mode] = {}
        for arm in ARMS:
            pred = np.concatenate(pooled_vectors[mode][arm][0])
            actual = np.concatenate(pooled_vectors[mode][arm][1])
            frame_errors = [item["arms"][arm][mode]["normalized_error"] for item in per_frame]
            pooled[mode][arm] = {
                "coordinates": int(pred.size),
                "metrics": compare(pred, actual),
                "frames_better_than_zero": int(sum(
                    item["arms"][arm][mode]["beats_zero_predictor"] is True for item in per_frame)),
                "frames": len(per_frame),
                "per_frame_normalized_error_min": float(min(frame_errors)),
                "per_frame_normalized_error_max": float(max(frame_errors)),
            }
    require(checked_cases == 16, f"transport case count differs: {checked_cases}")
    require(actual_shift_reconciliation_max <= 1e-12, "raw actual shifts do not match saved analysis vectors")
    require(decoder_clip_reconciliation_max <= 1e-12,
            "saved decoder LLR is not raw extrinsic clipped to [-20,20]")

    result = {
        "schema": "tf-cgr-analysis-independent-recount/1",
        "receiver_calls": 0,
        "decoder_calls": 0,
        "truth_payloads_opened": True,
        "truth_scope": "coded-bit labels for the eight target frames only; no truth channel/gain/observation arrays were opened",
        "truth_artifacts": {"witness_manifest_sha256": witness_manifest_sha,
                            "coded_payloads_hashed_and_read": len(truth_hashes),
                            "registration_sha256": sorted(x for x in truth_registration_hashes if x),
                            "files": truth_hashes},
        "observed_seal": {"sha256": seal_sha, "commit": SEAL_COMMIT,
                          "raw_target_files_rehashed": len(raw_hashes),
                          "raw_target_files": raw_hashes},
        "inputs": {
            "transport_path": str(transport_path.relative_to(ROOT)),
            "transport_sha256": sha256(transport_path),
            "transport_bytes": transport_path.stat().st_size,
            "finite_panel_path": str(finite_path.relative_to(ROOT)),
            "finite_panel_sha256": sha256(finite_path),
            "finite_panel_bytes": finite_path.stat().st_size,
            "offline_source_path": "experiments/tf_cgr_offline_mechanism_20260923/run_offline.py",
            "offline_source_sha256": sha256(ROOT / "experiments/tf_cgr_offline_mechanism_20260923/run_offline.py"),
        },
        "finite_panel_recount": {
            "rows": len(finite), "frames": len(finite_frames), "iterations_per_frame": 20,
            "D_equals_A_minus_Q_max_abs_residual": max_d_aq,
            "identity_tolerance": 1e-12,
            "per_frame": finite_frames,
        },
        "transport_recount": {
            "frames": len(transport), "target_ids": sorted(TARGETS),
            "arm_comparisons": checked_cases, "vector_length_each": 2048,
            "comparison_summary_max_abs_metric_delta": metric_reconciliation_max,
            "actual_shift_vs_sealed_raw_max_abs_delta": actual_shift_reconciliation_max,
            "decoder_input_vs_clipped_raw_extrinsic_max_abs_delta": decoder_clip_reconciliation_max,
            "pooled": pooled,
            "per_frame": per_frame,
            "logscore_summary_descriptive": score_totals,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "analysis_table_recount.json")
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({
        "output": str(args.output),
        "finite_rows": result["finite_panel_recount"]["rows"],
        "D_equals_A_minus_Q_max_abs_residual": result["finite_panel_recount"][
            "D_equals_A_minus_Q_max_abs_residual"],
        "transport_frames": result["transport_recount"]["frames"],
        "arm_comparisons": result["transport_recount"]["arm_comparisons"],
        "actual_shift_vs_sealed_raw_max_abs_delta": result["transport_recount"][
            "actual_shift_vs_sealed_raw_max_abs_delta"],
        "comparison_summary_max_abs_metric_delta": result["transport_recount"][
            "comparison_summary_max_abs_metric_delta"],
        "receiver_calls": 0,
        "truth_payloads_opened": True,
        "coded_truth_payloads_read": result["truth_artifacts"]["coded_payloads_hashed_and_read"],
        "logscore_summaries_checked": 32,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
