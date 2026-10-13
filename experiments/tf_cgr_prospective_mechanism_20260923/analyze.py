"""Truth-dependent, sealed-artifact-only CGR prospective analysis.

This module never imports a receiver, generator, decoder, optimizer, or JVP.
The fixed numerical functions below are testable without any experiment data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback
from typing import Any

import numpy as np
from scipy.stats import beta, binom

from common import (ARMS as REGISTERED_ARMS, FRAMES, RESULT, SCHEMA,
                    TASK_PROTOCOL, frame_id, git_ancestor, git_blob, git_relative,
                    observation_hash, read_jsonl, registration, sha256,
                    verify_seal, write_json)


ARMS = REGISTERED_ARMS
ALPHA = 0.05
TIE_RELATIVE = 1e-10
BOOTSTRAP_REPLICATES = 20_000


def _vector(value: object, *, length: int = 2048) -> np.ndarray:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (length,) or not np.isfinite(vector).all():
        raise ValueError(f"finite real vector of length {length} required")
    return vector


def norm_comparison(prediction: object, actual: object) -> dict:
    """Unscaled vector error and orientation; undefined zero norms stay null."""
    predicted = _vector(prediction)
    observed = _vector(actual)
    actual_norm = float(np.linalg.norm(observed))
    predicted_norm = float(np.linalg.norm(predicted))
    error_norm = float(np.linalg.norm(predicted - observed))
    return dict(
        actual_norm=actual_norm,
        predicted_norm=predicted_norm,
        error_norm=error_norm,
        normalized_error=error_norm / actual_norm if actual_norm else None,
        cosine=(float(np.dot(predicted, observed)) / (predicted_norm * actual_norm)
                if predicted_norm and actual_norm else None),
        beats_zero=error_norm < actual_norm if actual_norm else None,
    )


def contrast(prediction: object, actual: object, swapped: object) -> dict:
    """Own-versus-zero and own-versus-swapped squared-error contrasts."""
    predicted = _vector(prediction)
    observed = _vector(actual)
    other = _vector(swapped)
    q_own = float(np.vdot(observed - predicted, observed - predicted).real)
    q_zero = float(np.vdot(observed, observed).real)
    q_swap = float(np.vdot(observed - other, observed - other).real)
    return dict(q_own=q_own, q_zero=q_zero, q_swap=q_swap,
                zero_minus_own=q_zero - q_own,
                swap_minus_own=q_swap - q_own)


def exact_sign_test(rows: list[dict], reference: str) -> dict:
    """One-sided sign tail after the frozen scale-aware numerical tie rule."""
    if reference not in ("zero", "swap"):
        raise ValueError("reference must be zero or swap")
    q_ref_key = "q_zero" if reference == "zero" else "q_swap"
    difference_key = "zero_minus_own" if reference == "zero" else "swap_minus_own"
    wins = losses = ties = 0
    for row in rows:
        own, comparison = float(row["q_own"]), float(row[q_ref_key])
        difference = float(row[difference_key])
        if (not np.isfinite([own, comparison, difference]).all() or
                own < 0 or comparison < 0):
            raise ValueError("nonfinite or negative squared error")
        tolerance = TIE_RELATIVE * max(1.0, own, comparison)
        if abs(difference) <= tolerance:
            ties += 1
        elif difference > 0:
            wins += 1
        else:
            losses += 1
    nontied = wins + losses
    pvalue = float(binom.sf(wins - 1, nontied, 0.5)) if nontied else 1.0
    return dict(wins=wins, losses=losses, ties=ties, nontied=nontied,
                one_sided_p=pvalue)


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values, valid under test dependence."""
    names = list(pvalues)
    if len(names) != 4 or any(not 0 <= pvalues[name] <= 1 for name in names):
        raise ValueError("exactly four finite p-values in [0,1] required")
    order = sorted(names, key=lambda name: pvalues[name])
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, name in enumerate(order):
        running = max(running, (len(order) - rank) * pvalues[name])
        adjusted[name] = min(1.0, running)
    return {name: adjusted[name] for name in names}


def coded_logscore(incoming_llr: object, coded: object) -> dict:
    """Actual clipped decoder-input bit score; bits are not sample units."""
    llr = _vector(incoming_llr)
    bits = np.asarray(coded)
    if bits.shape != llr.shape or not np.isin(bits, (0, 1)).all():
        raise ValueError("coded truth must be a grouped binary 2048-vector")
    signed = (1.0 - 2.0 * bits.astype(float)) * llr
    wrong = signed < 0
    return dict(mean_bit_log_loss=float(np.logaddexp(0.0, -signed).mean()),
                wrong_sign_bits=int(wrong.sum()),
                wrong_confidence_sum=float((-signed[wrong]).sum()),
                wrong_confidence_mean=(float((-signed[wrong]).mean())
                                       if wrong.any() else 0.0))


def frame_decision(decoded: object, info: object, coded: object,
                   H: np.ndarray, free_cols: np.ndarray) -> dict:
    """Use actual systematic free columns and separately count code errors."""
    word = np.asarray(decoded)
    message = np.asarray(info)
    codeword = np.asarray(coded)
    if (H.ndim != 2 or H.shape[1] != 2048 or
            free_cols.ndim != 1 or len(np.unique(free_cols)) != len(free_cols) or
            np.any(free_cols < 0) or np.any(free_cols >= 2048) or
            word.shape != (2048,) or codeword.shape != (2048,) or
            message.shape != (len(free_cols),) or
            not np.isin(word, (0, 1)).all() or
            not np.isin(message, (0, 1)).all() or
            not np.isin(codeword, (0, 1)).all()):
        raise ValueError("decoded, coded, or information bits differ from registered code")
    if not np.array_equal(codeword[free_cols], message):
        raise ValueError("tagged coded truth disagrees with registered free columns")
    syndrome = (H.astype(np.int32) @ word.astype(np.int32)) % 2
    information_errors = int(np.count_nonzero(word[free_cols] != message))
    coded_errors = int(np.count_nonzero(word != codeword))
    syndrome_weight = int(np.count_nonzero(syndrome))
    return dict(info_errors=information_errors, coded_errors=coded_errors,
                syndrome_weight=syndrome_weight,
                info_correct=information_errors == 0,
                coded_correct=coded_errors == 0,
                valid_but_wrong=syndrome_weight == 0 and information_errors > 0)


def paired_table(base: list[dict], comparison: list[dict]) -> dict:
    """Full information-word paired 2×2 table and auxiliary exact p-value."""
    if len(base) != len(comparison):
        raise ValueError("paired outcome lengths differ")
    both_correct = base_only = comparison_only = both_wrong = 0
    for b, a in zip(base, comparison):
        bc, ac = bool(b["info_correct"]), bool(a["info_correct"])
        if bc and ac:
            both_correct += 1
        elif bc:
            base_only += 1
        elif ac:
            comparison_only += 1
        else:
            both_wrong += 1
    n = len(base)
    discordant = base_only + comparison_only
    comparison_better_p = (float(binom.sf(comparison_only - 1, discordant, 0.5))
                           if discordant else 1.0)
    base_better_p = (float(binom.sf(base_only - 1, discordant, 0.5))
                     if discordant else 1.0)
    # Conservative one-sided 95% paired-effect upper bound, descriptive here.
    effect_upper = None
    if n:
        harm_upper = (float(beta.ppf(0.975, base_only + 1, n - base_only))
                      if base_only < n else 1.0)
        rescue_lower = (float(beta.ppf(0.025, comparison_only, n - comparison_only + 1))
                        if comparison_only else 0.0)
        effect_upper = harm_upper - rescue_lower
    return dict(n=n, both_correct=both_correct, base_only_correct=base_only,
                comparison_only_correct=comparison_only, both_wrong=both_wrong,
                harms=base_only, rescues=comparison_only,
                delta_fer=(base_only - comparison_only) / n if n else None,
                exact_one_sided_mcnemar_p_comparison_better=comparison_better_p,
                exact_one_sided_mcnemar_p_base_better=base_better_p,
                conservative_effect_upper_95=effect_upper)


def frame_bootstrap(values: list[float], seed: int,
                    replicates: int = BOOTSTRAP_REPLICATES) -> dict:
    """Paired-frame percentile interval for a precomputed framewise difference."""
    vector = np.asarray(values, dtype=float)
    if (vector.ndim != 1 or not np.isfinite(vector).all() or
            type(seed) is not int or not 0 <= seed < 2**64 or
            type(replicates) is not int or replicates < 1):
        raise ValueError("invalid frame-bootstrap inputs")
    if not len(vector):
        return dict(n=0, mean=None, percentile_95=None, replicates=replicates)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(vector), size=(replicates, len(vector)))
    means = vector[draws].mean(axis=1)
    bounds = np.asarray(np.quantile(means, [0.025, 0.975])).reshape(-1)
    return dict(n=len(vector), mean=float(vector.mean()),
                percentile_95=[float(bounds[0]), float(bounds[1])],
                replicates=replicates)


def evaluate_science(frames: list[dict], *, analysis_seed: int,
                     integrity_passed: bool) -> dict[str, Any]:
    """Evaluate the frozen I/M/U/L gates on complete sealed frame records.

    Each record contains exactly one frame's BASE/CGR/SHAM terminal fields,
    decoded-word recount, clipped-input scores, and precommitted prediction.
    This function never chooses or changes the cohort from intervention data.
    """
    if len(frames) != 256 or {row["frame"] for row in frames} != set(range(256)):
        raise ValueError("registered 256-frame population is incomplete")
    if type(analysis_seed) is not int or not 0 <= analysis_seed < 2**64:
        raise ValueError("registered analysis seed differs")
    ordered = sorted(frames, key=lambda row: row["frame"])
    cohort = [row for row in ordered if row["eligible"]]
    triggered = [row for row in ordered if row["arms"]["BASE"]["triggered"]]
    frame_transport = []
    contrast_rows: dict[str, list[dict]] = {arm: [] for arm in ARMS[1:]}
    pooled: dict[str, dict[str, list[np.ndarray]]] = {
        arm: {key: [] for key in ("prediction", "actual", "clipped_prediction",
                                  "clipped_actual", "swapped_prediction",
                                  "clipped_swapped_prediction")}
        for arm in ARMS[1:]
    }
    for row in cohort:
        frame_result = {"frame": row["frame"], "observation_id": row["observation_id"]}
        base = row["arms"]["BASE"]
        for arm in ARMS[1:]:
            other = "SHAM" if arm == "CGR" else "CGR"
            terminal = row["arms"][arm]
            predicted = _vector(row["prediction"][arm]["unclipped"])
            predicted_clip = _vector(row["prediction"][arm]["clipped"])
            swapped = _vector(row["prediction"][other]["unclipped"])
            swapped_clip = _vector(row["prediction"][other]["clipped"])
            actual = _vector(terminal["extrinsic"]) - _vector(base["extrinsic"])
            actual_clip = (_vector(terminal["incoming_llr"]) -
                           _vector(base["incoming_llr"]))
            result = dict(unclipped=norm_comparison(predicted, actual),
                          clipped=norm_comparison(predicted_clip, actual_clip),
                          own_vs_zero_and_swap=contrast(predicted, actual, swapped))
            frame_result[arm] = result
            contrast_rows[arm].append(result["own_vs_zero_and_swap"])
            for key, vector in (("prediction", predicted), ("actual", actual),
                                ("clipped_prediction", predicted_clip),
                                ("clipped_actual", actual_clip),
                                ("swapped_prediction", swapped),
                                ("clipped_swapped_prediction", swapped_clip)):
                pooled[arm][key].append(vector)
        frame_transport.append(frame_result)

    exact: dict[str, dict] = {}
    for arm in ARMS[1:]:
        for reference in ("zero", "swap"):
            exact[f"{arm}_own_vs_{reference}"] = exact_sign_test(contrast_rows[arm], reference)
    adjusted = holm_adjust({name: row["one_sided_p"] for name, row in exact.items()})
    for name, pvalue in adjusted.items():
        exact[name]["holm_adjusted_p"] = pvalue

    pooled_results: dict[str, dict | None] = {}
    adverse = False
    for arm in ARMS[1:]:
        item = pooled[arm]
        if not item["actual"]:
            pooled_results[arm] = None
            continue
        vectors = {key: np.concatenate(parts) for key, parts in item.items()}
        own = norm_comparison_any_length(vectors["prediction"], vectors["actual"])
        own_clip = norm_comparison_any_length(vectors["clipped_prediction"],
                                              vectors["clipped_actual"])
        swapped_metric = norm_comparison_any_length(vectors["swapped_prediction"],
                                                     vectors["actual"])
        swapped_clipped_metric = norm_comparison_any_length(
            vectors["clipped_swapped_prediction"], vectors["clipped_actual"])
        pooled_results[arm] = dict(unclipped=own, clipped=own_clip,
                                   swapped_unclipped=swapped_metric,
                                   swapped_clipped=swapped_clipped_metric)
        if (own["normalized_error"] is not None and own["normalized_error"] >= 1 or
                own["cosine"] is not None and own["cosine"] < 0 or
                own["error_norm"] >= swapped_metric["error_norm"] or
                own_clip["normalized_error"] is not None and
                own_clip["normalized_error"] >= 1 or
                own_clip["error_norm"] >= swapped_clipped_metric["error_norm"]):
            adverse = True
    enough = len(cohort) >= 8 and all(row["nontied"] >= 8 for row in exact.values())
    signs_pass = all(row["holm_adjusted_p"] <= ALPHA for row in exact.values())
    pooled_pass = len(pooled_results) == 2 and all(
        result is not None and
        result["unclipped"]["normalized_error"] is not None and
        result["unclipped"]["normalized_error"] < 1 and
        result["unclipped"]["cosine"] is not None and
        result["unclipped"]["cosine"] > 0 and
        result["clipped"]["normalized_error"] is not None and
        result["clipped"]["normalized_error"] < 1 and
        result["clipped"]["cosine"] is not None and
        result["clipped"]["cosine"] > 0 and
        result["clipped"]["error_norm"] < result["swapped_clipped"]["error_norm"]
        for result in pooled_results.values())
    mechanism_pass = enough and signs_pass and pooled_pass
    mechanism_status = ("pass" if mechanism_pass else
                        "adverse" if adverse else "insufficient_support")

    outcomes = {arm: [row["arms"][arm]["decision"] for row in ordered] for arm in ARMS}
    tables = {f"BASE_vs_{arm}": paired_table(outcomes["BASE"], outcomes[arm])
              for arm in ARMS[1:]}
    tables["CGR_vs_SHAM"] = paired_table(outcomes["CGR"], outcomes["SHAM"])
    cgr = tables["BASE_vs_CGR"]
    sham = tables["BASE_vs_SHAM"]
    cgr_new_valid_wrong = sum(
        row["arms"]["CGR"]["decision"]["valid_but_wrong"] and
        not row["arms"]["BASE"]["decision"]["valid_but_wrong"]
        for row in ordered)
    safety_pass = (cgr["rescues"] >= 2 and cgr["harms"] == 0 and
                   cgr_new_valid_wrong == 0 and
                   cgr["rescues"] - cgr["harms"] > sham["rescues"] - sham["harms"])
    safety_status = ("pass" if safety_pass else
                     "insufficient_recovery_evidence" if sum(
                         not row["info_correct"] for row in outcomes["BASE"]) < 2
                     else "fail")

    subsets = {"all": ordered, "triggered": triggered, "eligible": cohort}
    calibration: dict[str, dict] = {}
    for ordinal, (name, subset) in enumerate(subsets.items()):
        arm_means = {arm: (float(np.mean([
            row["arms"][arm]["logscore"]["mean_bit_log_loss"] for row in subset]))
                           if subset else None) for arm in ARMS}
        differences = {
            "CGR_minus_BASE": [row["arms"]["CGR"]["logscore"]["mean_bit_log_loss"] -
                               row["arms"]["BASE"]["logscore"]["mean_bit_log_loss"]
                               for row in subset],
            "CGR_minus_SHAM": [row["arms"]["CGR"]["logscore"]["mean_bit_log_loss"] -
                               row["arms"]["SHAM"]["logscore"]["mean_bit_log_loss"]
                               for row in subset],
        }
        calibration[name] = dict(
            arm_mean_bit_log_loss=arm_means,
            paired_differences={
                pair: frame_bootstrap(values, (analysis_seed + 2 * ordinal + offset) % 2**64)
                for offset, (pair, values) in enumerate(differences.items())
            })
    eligible_loss = calibration["eligible"]["paired_differences"]
    all_loss = calibration["all"]["paired_differences"]
    calibration_pass = (eligible_loss["CGR_minus_BASE"]["mean"] is not None and
                        eligible_loss["CGR_minus_BASE"]["mean"] < 0 and
                        eligible_loss["CGR_minus_SHAM"]["mean"] is not None and
                        eligible_loss["CGR_minus_SHAM"]["mean"] < 0 and
                        all_loss["CGR_minus_BASE"]["mean"] <= 0)
    return dict(
        counts=dict(population=len(ordered), base_triggered=len(triggered), eligible=len(cohort)),
        cohort=[dict(frame=row["frame"], observation_id=row["observation_id"],
                     eligible=bool(row["eligible"]),
                     exclusion_reason=row["exclusion_reason"]) for row in ordered],
        transport=dict(framewise=frame_transport, pooled=pooled_results,
                       exact_sign_tests=exact),
        outcomes=dict(paired_tables=tables, cgr_new_valid_wrong=cgr_new_valid_wrong,
                      valid_but_wrong_by_arm={arm: sum(row["valid_but_wrong"] for row in records)
                                              for arm, records in outcomes.items()},
                      base_info_failures=sum(not row["info_correct"] for row in outcomes["BASE"]),
                      framewise=[dict(frame=row["frame"], observation_id=row["observation_id"],
                                      arms={arm: dict(decision=row["arms"][arm]["decision"],
                                                      logscore=row["arms"][arm]["logscore"])
                                            for arm in ARMS}) for row in ordered]),
        calibration=calibration,
        gates=dict(I="pass" if integrity_passed else "invalid",
                   M=mechanism_status, U=safety_status,
                   L="pass" if calibration_pass else "fail"),
        prospective_mechanism_supported=bool(integrity_passed and mechanism_pass),
        bounded_continue=bool(integrity_passed and mechanism_pass and
                              safety_pass and calibration_pass),
    )


def norm_comparison_any_length(prediction: np.ndarray, actual: np.ndarray) -> dict:
    """The same fixed metrics for concatenated complete-frame vectors."""
    if (prediction.ndim != 1 or actual.shape != prediction.shape or
            not np.isfinite(prediction).all() or not np.isfinite(actual).all()):
        raise ValueError("pooled vectors differ")
    actual_norm = float(np.linalg.norm(actual))
    predicted_norm = float(np.linalg.norm(prediction))
    error_norm = float(np.linalg.norm(prediction - actual))
    return dict(actual_norm=actual_norm, predicted_norm=predicted_norm,
                error_norm=error_norm,
                normalized_error=error_norm / actual_norm if actual_norm else None,
                cosine=(float(np.dot(prediction, actual)) / (predicted_norm * actual_norm)
                        if predicted_norm and actual_norm else None),
                beats_zero=error_norm < actual_norm if actual_norm else None)


def _safe_artifact(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("unsafe sealed artifact path")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("artifact escapes sealed root")
    return resolved


def _load_bound(evidence, root: Path, relative: str, expected: str) -> dict:
    path = _safe_artifact(root, relative)
    if sha256(path) != expected:
        raise ValueError(f"sealed artifact hash differs: {relative}")
    return evidence.load_artifact(path)[0]


def _indexed_ledger(root: Path, expected: int, *, arm_phase: bool = False) -> dict:
    rows = read_jsonl(root / "ledger.jsonl")
    if len(rows) != expected or {row["frame"] for row in rows} != set(range(FRAMES)):
        raise ValueError(f"sealed ledger population differs: {root}")
    if arm_phase:
        keys = [(row["frame"], row["arm"]) for row in rows]
        if len(set(keys)) != expected or any(row["status"] != "ok" for row in rows):
            raise ValueError(f"arm ledger incomplete or duplicated: {root}")
        return {(row["frame"], row["arm"]): row for row in rows}
    if len({row["frame"] for row in rows}) != expected:
        raise ValueError(f"generation or prediction ledger duplicated: {root}")
    return {row["frame"]: row for row in rows}


def verify_pretruth(args: argparse.Namespace) -> tuple[dict, dict]:
    """Hash and Git-bind every observed artifact before opening any truth NPZ."""
    if args.protocol.resolve() != TASK_PROTOCOL.resolve():
        raise ValueError("supplied protocol is not the frozen task protocol")
    root = args.root.resolve()
    protocol = root / "protocol"
    lock_path = protocol / "registration.json"
    lock = registration(lock_path, args.source, args.baseline)
    reg_commit = args.registration_commit
    pred_commit = args.prediction_commit
    observed_commit = args.observed_commit
    git_ancestor(reg_commit, pred_commit)
    git_ancestor(pred_commit, observed_commit)
    for path in (lock_path, protocol / "random_namespace.json",
                 protocol / "source_bindings.json",
                 args.protocol):
        git_blob(reg_commit, git_relative(path), path)
    from attest import verify_prediction_handoff, verify_registration_attestation

    verify_registration_attestation(protocol / "registration_attestation.json",
                                    lock_path, reg_commit)
    population = root / "observed/population"
    base = root / "observed/base"
    prediction = root / "prediction"
    interventions = root / "observed/interventions"
    observed = root / "observed"
    truth = root / "truth"
    for folder, seal_name in ((population, "observed_seal.json"),
                              (base, "observed_seal.json"),
                              (prediction, "prediction_seal.json"),
                              (interventions, "observed_seal.json"),
                              (observed, "observed_seal.json")):
        verify_seal(folder, seal_name)
    prediction_handoff = verify_prediction_handoff(
        protocol / "prediction_handoff.json", protocol, prediction, base)
    if (prediction_handoff["registration_commit"] != reg_commit or
            prediction_handoff["prediction_commit"] != pred_commit):
        raise ValueError("prediction Git handoff commits differ")
    pred_seal = prediction / "prediction_seal.json"
    base_seal = base / "observed_seal.json"
    observed_seal = observed / "observed_seal.json"
    truth_seal = truth / "truth_seal.json"
    git_blob(pred_commit, git_relative(pred_seal), pred_seal)
    git_blob(pred_commit, git_relative(base_seal), base_seal)
    git_blob(observed_commit, git_relative(observed_seal), observed_seal)
    # Only after the committed complete observed seal is proven may truth bytes
    # be inspected, even for hashing/inventory validation.
    verify_seal(truth, "truth_seal.json")
    git_blob(observed_commit, git_relative(truth_seal), truth_seal)
    combined = json.loads(observed_seal.read_text())
    required = dict(population_seal_sha256=sha256(population / "observed_seal.json"),
                    base_seal_sha256=sha256(base_seal),
                    intervention_seal_sha256=sha256(interventions / "observed_seal.json"),
                    prediction_seal_sha256=sha256(pred_seal),
                    truth_seal_sha256=sha256(truth_seal),
                    registration_sha256=sha256(lock_path),
                    prediction_commit=pred_commit, completed_calls=768)
    if any(combined.get(key) != value for key, value in required.items()):
        raise ValueError("final observed seal chain differs")
    handoff_path = protocol / "observed_handoff.json"
    handoff = json.loads(handoff_path.read_text())
    handoff_required = dict(
        schema=SCHEMA, kind="observed_git_handoff",
        registration_commit=reg_commit, prediction_commit=pred_commit,
        observed_commit=observed_commit,
        observed_seal_sha256=sha256(observed_seal),
        truth_seal_sha256=sha256(truth_seal),
        prediction_seal_sha256=sha256(pred_seal),
        registration_sha256=sha256(lock_path),
        observed_seal_git_path=git_relative(observed_seal),
        truth_seal_git_path=git_relative(truth_seal))
    if any(handoff.get(key) != value for key, value in handoff_required.items()):
        raise ValueError("final observed Git handoff differs")
    # Structural completeness is checked before truth payload access too.
    population_rows = _indexed_ledger(population, FRAMES)
    base_rows = _indexed_ledger(base, FRAMES, arm_phase=True)
    intervention_rows = _indexed_ledger(interventions, 2 * FRAMES, arm_phase=True)
    prediction_rows = _indexed_ledger(prediction, FRAMES)
    expected_base = {(frame, "BASE") for frame in range(FRAMES)}
    expected_intervention = {(frame, arm) for frame in range(FRAMES)
                             for arm in ("CGR", "SHAM")}
    if set(base_rows) != expected_base or set(intervention_rows) != expected_intervention:
        raise ValueError("three-arm registered allocation differs")
    if ([(row["frame"], row["arm"]) for row in read_jsonl(base / "ledger.jsonl")] !=
            [(frame, "BASE") for frame in range(FRAMES)] or
            [(row["frame"], row["arm"]) for row in
             read_jsonl(interventions / "ledger.jsonl")] !=
            [(item["frame"], arm) for item in lock["schedule"]
             for arm in item["arms"]]):
        raise ValueError("sealed phase execution order differs")
    calls = [*base_rows.values(), *intervention_rows.values()]
    if {row["call_index"] for row in calls} != set(range(1, 769)):
        raise ValueError("global attempt index or budget differs")
    for frame, scheduled in enumerate(lock["schedule"]):
        if scheduled["frame"] != frame:
            raise ValueError("registered intervention schedule differs")
        actual = [row["arm"] for row in sorted(
            (intervention_rows[frame, arm] for arm in ("CGR", "SHAM")),
            key=lambda row: row["call_index"])]
        if actual != scheduled["arms"]:
            raise ValueError("intervention order differs from registered stream")
    if any(row["call_index"] != frame + 1 for frame, row in
           ((frame, base_rows[frame, "BASE"]) for frame in range(FRAMES))):
        raise ValueError("BASE phase call order differs")
    if len(prediction_rows) != FRAMES:
        raise ValueError("prediction ledger incomplete")
    return lock, dict(population=population_rows, base=base_rows,
                      intervention=intervention_rows, prediction=prediction_rows,
                      observed_commit=observed_commit,
                      prediction_commit=pred_commit,
                      registration_commit=reg_commit)


def _code_arrays(baseline: Path, lock: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    path = (baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
            "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    if sha256(path) != lock["code_cache_sha256"]:
        raise ValueError("registered code cache differs")
    with np.load(path, allow_pickle=False) as archive:
        H = np.asarray(archive["H"], dtype=np.int32)
        G = np.asarray(archive["G"])
        free = np.asarray(archive["free_cols"], dtype=np.int64)
    if (H.shape != (1026, 2048) or G.shape != (2048, 1024) or
            free.shape != (1024,) or len(np.unique(free)) != 1024 or
            hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest() !=
            lock["code_g_sha256"]):
        raise ValueError("actual registered H/G/free_cols differ")
    return H, G, free


def _verify_coded_truth(coded: np.ndarray, info: np.ndarray, H: np.ndarray,
                        G: np.ndarray, free: np.ndarray) -> None:
    if (coded.shape != (2048,) or info.shape != (1024,) or
            not np.isin(coded, (0, 1)).all() or not np.isin(info, (0, 1)).all() or
            not np.array_equal(coded[free], info) or
            not np.array_equal((G.astype(np.int32) @ info.astype(np.int32)) % 2,
                               coded.astype(np.int32)) or
            np.any((H @ coded.astype(np.int32)) % 2)):
        raise ValueError("tagged truth differs from registered G/H/free_cols")


def _ledger_artifact(evidence, root: Path, row: dict, path_key: str,
                     sha_key: str) -> dict:
    return _load_bound(evidence, root, row[path_key], row[sha_key])


def _decision_row(evidence, root: Path, row: dict, raw: dict, H: np.ndarray,
                  free: np.ndarray, coded: np.ndarray, info: np.ndarray) -> tuple[dict, dict]:
    from branch import hash_value

    decision_path = _safe_artifact(root, row["decision_path"])
    if sha256(decision_path) != row["decision_sha256"]:
        raise ValueError("sealed decision JSON differs")
    decision = json.loads(decision_path.read_text())
    decoded = np.asarray(raw["final_decoded"])
    expected_sha = hashlib.sha256(decoded.tobytes()).hexdigest()
    if (decision["final_decoded_sha256"] != expected_sha or
            row["final_decoded_sha256"] != expected_sha or
            decision["raw_sha256"] != row["raw_sha256"] or
            decision["raw_path"] != row["raw_path"] or
            decision["input_sha256"] != row["input_sha256"] or
            raw["input_sha256"] != row["input_sha256"] or
            raw["triggered"] != row["triggered"] or
            raw["numerical_failure"] != row["numerical_failure"] or
            row["numerical_failure"] is not None):
        raise ValueError("decision/raw/ledger identity or numerical status differs")
    result = frame_decision(decoded, info, coded, H, free)
    if result["syndrome_weight"] != decision["final_syndrome_weight"]:
        raise ValueError("saved final syndrome differs")
    native = raw["native_decoder"]
    branch = raw["branch_detector"]
    if raw["triggered"]:
        if (branch is None or raw["branch_decoder"] is None or
                raw["entering"] is None or len(branch["states"]) != 20 or
                any(np.asarray(state["x"]).shape != (1024,) or
                    np.asarray(state["mu"]).shape != (1024,) or
                    np.asarray(state["v"]).shape != (1024,) or
                    np.asarray(state["s"]).shape != (1024,)
                    for state in branch["states"])):
            raise ValueError("triggered arm lacks complete twenty-vector trace")
        extrinsic = _vector(branch["extrinsic"])
        incoming = _vector(raw["branch_decoder"]["incoming_llr"])
        if not np.array_equal(incoming, np.clip(extrinsic, -20, 20)):
            raise ValueError("actual decoder input differs from clipped extrinsic")
        if row["entering_sha256"] != hash_value(raw["entering"]):
            raise ValueError("post-refit entering hash differs")
    else:
        if branch is not None or raw["branch_decoder"] is not None:
            raise ValueError("native bypass contains a fabricated final branch")
        incoming = _vector(native["incoming_llr"])
        extrinsic = None
    checkpoint_decisions = []
    if len(row["checkpoints"]) != (3 if raw["triggered"] else 2):
        raise ValueError("native/final checkpoint count differs")
    for checkpoint in row["checkpoints"]:
        payload = _ledger_artifact(evidence, root, checkpoint, "path", "artifact_sha256")
        bits = np.asarray(payload["decoded"])
        count = frame_decision(bits, info, coded, H, free)
        if count["syndrome_weight"] != checkpoint["syndrome_weight"]:
            raise ValueError("checkpoint syndrome differs")
        checkpoint_decisions.append(dict(round=checkpoint["round"],
                                         decision_ready_seconds=checkpoint["decision_ready_seconds"],
                                         **count))
    if (not np.array_equal(decoded, np.asarray(payload["decoded"])) or
            decision["final_decision_ready_seconds"] !=
            row["final_decision_ready_seconds"] or
            decision["checkpoints"] != row["checkpoints"] or
            row["triggered"] != (checkpoint_decisions[1]["syndrome_weight"] != 0)):
        raise ValueError("final/native checkpoint readiness differs")
    if raw["triggered"] and not np.array_equal(
            decoded, np.asarray(raw["branch_decoder"]["decoded"])):
        raise ValueError("final branch decision differs")
    return (dict(decision=result, logscore=coded_logscore(incoming, coded),
                 incoming_llr=incoming, extrinsic=extrinsic,
                 triggered=bool(raw["triggered"]),
                 complete_latency_seconds=float(row["complete_latency_seconds"]),
                 branch_complete_seconds=float(row["branch_complete_seconds"]),
                 checkpoints=checkpoint_decisions),
            dict(native_arrays=raw["native_arrays"], entering=raw["entering"],
                 entering_sha256=row["entering_sha256"], raw=raw))


def _prediction_row(evidence, root: Path, row: dict, base_row: dict,
                    base_raw: dict, input_row: dict, rho: float) -> dict:
    prediction = _ledger_artifact(evidence, root, row, "vector_path", "vector_sha256")
    if (prediction["frame"] != row["frame"] or
            prediction["observation_id"] != row["observation_id"] or
            prediction["input_sha256"] != input_row["observation_sha256"] or
            prediction["base_raw_sha256"] != base_row["raw_sha256"] or
            prediction["eligible"] != row["eligible"] or
            prediction["exclusion_reason"] != row["exclusion_reason"] or
            not prediction["final_gain_impulse_zero"]):
        raise ValueError("prediction identity/cohort differs from sealed BASE")
    if base_raw["triggered"]:
        R = np.asarray(base_raw["gram"]["R"])
        reaction = float(np.max(abs(R - np.eye(R.shape[0]))))
        if abs(reaction - float(prediction["reaction_max"])) > 1e-10:
            raise ValueError("sealed reaction statistic differs")
    else:
        reaction = 0.0
    a = float(np.sqrt((1 - rho) / 2))
    result = {}
    for arm in ARMS[1:]:
        unclipped = _vector(prediction[f"predicted_{arm}_unclipped_llr_shift"])
        clipped = _vector(prediction[f"predicted_{arm}_clipped_llr_shift"])
        natural = np.asarray(prediction[f"predicted_{arm}_natural_field_shift"])
        if (natural.shape != (1024,) or not np.isfinite(natural).all() or
                not np.allclose(natural, (unclipped[:1024] + 1j * unclipped[1024:]) /
                                (4 * a), rtol=1e-12, atol=1e-12)):
            raise ValueError("predicted natural field and LLR disagree")
        expected_norm = float(np.linalg.norm(unclipped))
        if abs(expected_norm - float(prediction[f"predicted_{arm}_norm"])) > 1e-8:
            raise ValueError("predicted norm differs")
        if base_raw["triggered"]:
            base_llr = _vector(base_raw["branch_detector"]["extrinsic"])
            derivative_clip = unclipped.copy()
            outward = ((base_llr == 20) & (unclipped > 0)) | (
                (base_llr == -20) & (unclipped < 0))
            derivative_clip[(abs(base_llr) > 20) | outward] = 0
            if not np.array_equal(clipped, derivative_clip):
                raise ValueError("sealed prediction is not one-sided derivative-clipped")
        if not base_raw["triggered"] and (np.any(unclipped) or np.any(clipped)):
            raise ValueError("bypass has nonzero invented prediction")
        result[arm] = dict(unclipped=unclipped, clipped=clipped)
    expected_eligible = (bool(base_raw["triggered"]) and reaction > 1e-10 and
                         all(np.linalg.norm(result[arm]["unclipped"]) > 1e-8
                             for arm in ARMS[1:]))
    expected_reason = (None if expected_eligible else
                       "native_bypass" if not base_raw["triggered"] else
                       "zero_physical_reaction" if reaction <= 1e-10 else
                       "numerical_zero_prediction")
    if (bool(prediction["eligible"]) != expected_eligible or
            prediction["exclusion_reason"] != expected_reason):
        raise ValueError("cohort E differs from frozen pre-intervention criterion")
    return dict(eligible=expected_eligible,
                exclusion_reason=prediction["exclusion_reason"], arms=result,
                clip_boundary_count=int(prediction["clip_boundary_count"]),
                floor_boundary_count=int(prediction["floor_boundary_count"]))


def _distribution(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    return dict(n=len(array), mean=float(array.mean()) if len(array) else None,
                p95=float(np.percentile(array, 95)) if len(array) else None,
                max=float(array.max()) if len(array) else None)


def analyze(args: argparse.Namespace) -> dict:
    if args.out.exists():
        raise FileExistsError(args.out)
    root_resolved = args.root.resolve()
    out_resolved = args.out.resolve()
    if any(out_resolved.is_relative_to((root_resolved / subdir).resolve())
           for subdir in ("observed", "truth", "prediction")):
        raise ValueError("analysis output cannot mutate a sealed observed/truth/prediction tree")
    lock, ledgers = verify_pretruth(args)
    root = args.root.resolve()
    H, G, free = _code_arrays(args.baseline, lock)
    from common import PROJECT
    sys.path.insert(0, str(PROJECT / "experiments/tf_production_gap_audit_20260922"))
    from audit_io import attach

    evidence = attach(args.source, args.baseline)
    observed_root = root / "observed"
    truth_root = root / "truth"
    truth_rows = _indexed_ledger(truth_root, FRAMES)
    from branch import hash_value

    frames = []
    deadline_rows = []
    for frame in range(FRAMES):
        stem = frame_id(frame)
        observation_row = ledgers["population"][frame]
        truth_row = truth_rows[frame]
        if (observation_row["observation_id"] != stem or
                truth_row["observation_id"] != stem or
                observation_row["observation_hash"] != truth_row["observation_hash"] or
                observation_row["stream_ids"] != truth_row["stream_ids"]):
            raise ValueError("observed/truth frame identity differs")
        observed = _ledger_artifact(evidence, observed_root / "population",
                                    observation_row, "observation_path", "observation_sha256")
        tagged = _ledger_artifact(evidence, truth_root, truth_row,
                                  "truth_path", "truth_sha256")
        if (observed["observation_id"] != stem or
                observed["observation_hash"] != observation_row["observation_hash"] or
                observation_hash(observed["observation"]) != observation_row["observation_hash"] or
                tagged["observation_hash"] != observation_row["observation_hash"] or
                observed["stream_ids"] != tagged["stream_ids"]):
            raise ValueError("saved observed/truth payload pairing differs")
        coded = np.asarray(tagged["coded"])
        info = np.asarray(tagged["info"])
        _verify_coded_truth(coded, info, H, G, free)
        arm_records = {}
        raw_records = {}
        for arm in ARMS:
            phase = "base" if arm == "BASE" else "intervention"
            ledger = ledgers[phase][frame, arm]
            phase_root = observed_root / ("base" if arm == "BASE" else "interventions")
            raw = _ledger_artifact(evidence, phase_root, ledger, "raw_path", "raw_sha256")
            if (ledger["frame"] != frame or ledger["observation_id"] != stem or
                    ledger["input_sha256"] != observation_row["observation_sha256"] or
                    raw["observation_id"] != stem or raw["arm"] != arm):
                raise ValueError("arm/input identity differs")
            arm_records[arm], raw_records[arm] = _decision_row(
                evidence, phase_root, ledger, raw, H, free, coded, info)
        reference = raw_records["BASE"]
        for arm in ARMS[1:]:
            other = raw_records[arm]
            if (hash_value(other["native_arrays"]) != hash_value(reference["native_arrays"]) or
                    other["entering_sha256"] != reference["entering_sha256"] or
                    arm_records[arm]["triggered"] != arm_records["BASE"]["triggered"]):
                raise ValueError("paired native prefix or entering state differs")
        prediction = _prediction_row(evidence, root / "prediction",
                                     ledgers["prediction"][frame],
                                     ledgers["base"][frame, "BASE"],
                                     reference["raw"], observation_row,
                                     float(json.loads((observed_root / "population/manifest.json").read_text())["system"]["rho"]))
        frames.append(dict(frame=frame, observation_id=stem,
                           eligible=prediction["eligible"],
                           exclusion_reason=prediction["exclusion_reason"],
                           prediction=prediction["arms"], arms=arm_records,
                           boundary_counts=dict(clip=prediction["clip_boundary_count"],
                                                floor=prediction["floor_boundary_count"])))
        for arm in ARMS:
            states = arm_records[arm]["checkpoints"]
            for deadline in (0.5, 1.0):
                ready = [item for item in states if item["decision_ready_seconds"] <= deadline]
                latest = ready[-1] if ready else None
                deadline_rows.append(dict(frame=frame, arm=arm, deadline_seconds=deadline,
                                          ready=latest is not None,
                                          round=None if latest is None else latest["round"],
                                          info_correct=None if latest is None else latest["info_correct"],
                                          syndrome_weight=None if latest is None else latest["syndrome_weight"]))
    science = evaluate_science(frames, analysis_seed=lock["analysis_seed"],
                               integrity_passed=True)
    timing = {arm: dict(complete=_distribution([
        row["arms"][arm]["complete_latency_seconds"] for row in frames]),
        branch=_distribution([row["arms"][arm]["branch_complete_seconds"]
                              for row in frames if row["arms"][arm]["triggered"]]))
        for arm in ARMS}
    for name, location in (("population", observed_root / "population/manifest.json"),
                           ("base", observed_root / "base/manifest.json"),
                           ("interventions", observed_root / "interventions/manifest.json"),
                           ("prediction", root / "prediction/manifest.json")):
        manifest = json.loads(location.read_text())
        timing[f"{name}_setup_seconds"] = manifest.get("setup_seconds")
    timing["prediction_elapsed_seconds"] = json.loads(
        (root / "prediction/prediction_seal.json").read_text())["elapsed_seconds"]
    result = dict(schema=SCHEMA, source_reader_sha256=sha256(Path(__file__)),
                  integrity=dict(status="pass", registration_commit=ledgers["registration_commit"],
                                 prediction_commit=ledgers["prediction_commit"],
                                 observed_commit=ledgers["observed_commit"],
                                 observed_seal_sha256=sha256(observed_root / "observed_seal.json"),
                                 truth_seal_sha256=sha256(truth_root / "truth_seal.json"),
                                 total_attempts=3 * FRAMES),
                  science=science, timing=timing,
                  deadlines=dict(rows=deadline_rows,
                                 summaries={arm: {str(deadline): dict(
                                     ready=sum(1 for row in deadline_rows
                                               if row["arm"] == arm and row["deadline_seconds"] == deadline
                                               and row["ready"] is True),
                                     correct=sum(1 for row in deadline_rows
                                                 if row["arm"] == arm and row["deadline_seconds"] == deadline
                                                 and row["info_correct"] is True))
                                     for deadline in (0.5, 1.0)} for arm in ARMS}))
    args.out.mkdir(parents=True)
    write_json(args.out / "report.json", result)
    write_json(args.out / "analysis_receipt.json", dict(
        schema=SCHEMA, source_reader_sha256=sha256(Path(__file__)),
        registration_sha256=sha256(root / "protocol/registration.json"),
        observed_seal_sha256=sha256(observed_root / "observed_seal.json"),
        truth_seal_sha256=sha256(truth_root / "truth_seal.json"),
        report_sha256=sha256(args.out / "report.json")))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=RESULT)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=TASK_PROTOCOL)
    parser.add_argument("--registration-commit", required=True)
    parser.add_argument("--prediction-commit", required=True)
    parser.add_argument("--observed-commit", required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        print(json.dumps(analyze(arguments)["science"]["gates"], sort_keys=True))
    except BaseException as error:
        print(f"offline analysis stopped: {error}\n{traceback.format_exc()}", file=sys.stderr)
        raise
