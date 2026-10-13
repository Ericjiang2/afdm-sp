"""Pure synthetic statistics qualification; no observations or receiver calls."""
from __future__ import annotations

import numpy as np

from analyze import (coded_logscore, contrast, exact_sign_test, frame_bootstrap,
                     frame_decision, holm_adjust, norm_comparison, paired_table,
                     evaluate_science, _verify_coded_truth)


def padded(*values: float) -> np.ndarray:
    array = np.zeros(2048)
    array[:len(values)] = values
    return array


def test_tagged_truth_uses_actual_generator_and_checks() -> None:
    H = np.zeros((1026, 2048), np.int32)
    G = np.zeros((2048, 1024), np.int32)
    free = np.arange(1024)
    G[:1024] = np.eye(1024, dtype=np.int32)
    info = np.zeros(1024, np.uint8)
    info[0] = 1
    coded = np.zeros(2048, np.uint8)
    coded[0] = 1
    _verify_coded_truth(coded, info, H, G, free)
    H[0, 0] = 1
    try:
        _verify_coded_truth(coded, info, H, G, free)
    except ValueError:
        pass
    else:
        raise AssertionError("noncodeword tagged truth accepted")


def test_unscaled_transport_and_ties() -> None:
    own = contrast(padded(1), padded(1), padded(-1))
    assert own["q_own"] == 0 and own["q_zero"] == 1 and own["q_swap"] == 4
    metric = norm_comparison(padded(1), padded(1))
    assert metric["normalized_error"] == 0 and metric["cosine"] == 1
    assert norm_comparison(padded(0), padded(0))["normalized_error"] is None
    tied = dict(q_own=1.0, q_zero=1.0 + 1e-12,
                q_swap=4.0, zero_minus_own=1e-12, swap_minus_own=3.0)
    results = exact_sign_test([own] * 8 + [tied], "zero")
    assert (results["wins"], results["losses"], results["ties"],
            results["nontied"]) == (8, 0, 1, 8)
    assert results["one_sided_p"] == 1 / 256
    adjusted = holm_adjust({"CGR_zero": 1 / 256, "CGR_swap": 1 / 256,
                            "SHAM_zero": 1 / 256, "SHAM_swap": 1 / 256})
    assert all(value == 1 / 64 for value in adjusted.values())


def test_truth_score_and_information_mapping() -> None:
    llr = padded(2, -3, 1)
    coded = np.zeros(2048, dtype=np.uint8)
    coded[1] = 1
    result = coded_logscore(llr, coded)
    signed = (1 - 2 * coded.astype(float)) * llr
    assert abs(result["mean_bit_log_loss"] - np.logaddexp(0, -signed).mean()) < 1e-15
    assert result["wrong_sign_bits"] == 0
    H = np.zeros((1, 2048), dtype=np.uint8)
    H[0, 0:2] = 1
    free = np.array([0, 2], dtype=np.int64)
    message = np.array([0, 0], dtype=np.uint8)
    codeword = np.zeros(2048, dtype=np.uint8)
    word = codeword.copy()
    word[0] = 1
    wrong = frame_decision(word, message, codeword, H, free)
    assert wrong["info_errors"] == 1 and wrong["coded_errors"] == 1
    assert wrong["syndrome_weight"] == 1 and not wrong["valid_but_wrong"]
    word[1] = 1
    valid_wrong = frame_decision(word, message, codeword, H, free)
    assert valid_wrong["valid_but_wrong"] and valid_wrong["info_errors"] == 1


def test_paired_table_and_frame_bootstrap() -> None:
    base = [dict(info_correct=value) for value in (True, False, False, True)]
    arm = [dict(info_correct=value) for value in (True, True, False, True)]
    table = paired_table(base, arm)
    assert (table["both_correct"], table["base_only_correct"],
            table["comparison_only_correct"], table["both_wrong"]) == (2, 0, 1, 1)
    assert (table["delta_fer"] == -0.25 and
            table["exact_one_sided_mcnemar_p_comparison_better"] == 0.5)
    first = frame_bootstrap([-1, 0, 1], 77, replicates=200)
    assert first == frame_bootstrap([-1, 0, 1], 77, replicates=200)
    assert first["mean"] == 0 and first["percentile_95"][0] <= 0 <= first["percentile_95"][1]
    assert frame_bootstrap([], 77, replicates=200)["percentile_95"] is None


def test_fixed_gate_separation_on_synthetic_frames() -> None:
    zero = padded(0)
    plus = padded(1)
    minus = padded(-1)
    frames = []
    for index in range(256):
        eligible = index < 8
        arms = {}
        for arm in ("BASE", "CGR", "SHAM"):
            llr = (plus if arm == "CGR" else minus if arm == "SHAM" else zero) if eligible else zero
            score = .2 if arm == "CGR" and eligible else .4 if arm == "SHAM" and eligible else .3
            arms[arm] = dict(extrinsic=llr, incoming_llr=llr, triggered=eligible,
                             decision=dict(info_correct=True, valid_but_wrong=False),
                             logscore=dict(mean_bit_log_loss=score))
        frames.append(dict(frame=index, observation_id=f"synthetic_{index}",
                           eligible=eligible,
                           exclusion_reason=None if eligible else "bypass",
                           arms=arms,
                           prediction={"CGR": dict(unclipped=plus, clipped=plus),
                                       "SHAM": dict(unclipped=minus, clipped=minus)}))
    result = evaluate_science(frames, analysis_seed=20260923, integrity_passed=True)
    assert result["counts"] == dict(population=256, base_triggered=8, eligible=8)
    assert result["gates"] == dict(I="pass", M="pass", U="insufficient_recovery_evidence",
                                   L="pass")
    assert result["prospective_mechanism_supported"] is True
    assert result["bounded_continue"] is False
    assert all(row["holm_adjusted_p"] == 1 / 64
               for row in result["transport"]["exact_sign_tests"].values())
    for row in frames[:2]:
        row["arms"]["BASE"]["decision"]["info_correct"] = False
        row["arms"]["SHAM"]["decision"]["info_correct"] = False
    supported = evaluate_science(frames, analysis_seed=20260923, integrity_passed=True)
    assert supported["gates"] == dict(I="pass", M="pass", U="pass", L="pass")
    assert supported["bounded_continue"] is True
