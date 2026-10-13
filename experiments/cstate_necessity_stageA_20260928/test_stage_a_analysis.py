"""Synthetic tests for the frozen Stage-A statistical signs and deadlines."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from analyze_stage_a import (
    N_FRAMES, all_pairwise, cp_lower, cp_upper, deadline_summary,
    fixed_gates, paired_table, latest_ready, _decision,
    _verify_file_inventory, _verify_git_attestation,
)


def _bits(indices):
    out = np.zeros(N_FRAMES, dtype=bool)
    out[list(indices)] = True
    return out


def test_paired_signed_effects_and_exact_discordance():
    a = _bits((0, 1))
    b = _bits((0, 2))
    pair = paired_table(a, b)
    assert (pair["both_correct"], pair["first_only_correct"],
            pair["second_only_correct"], pair["both_wrong"]) == (1, 1, 1, 1021)
    assert pair["fer_first_minus_second"] == 0
    assert pair["mcnemar_exact_two_sided_p"] == 1
    better = paired_table(_bits(()), _bits((0, 1, 2, 3)))
    assert better["fer_first_minus_second"] == 4 / N_FRAMES
    assert better["fer_second_minus_first"] == -4 / N_FRAMES
    assert better["mcnemar_exact_two_sided_p"] == 0.125
    assert better["upper_95_fer_first_minus_second"] > 0
    local = paired_table(np.array([False, True]), np.array([True, True]))
    assert local["n"] == 2 and local["fer_first_minus_second"] == 0.5
    assert cp_lower(0, N_FRAMES) == 0
    assert cp_upper(N_FRAMES, N_FRAMES) == 1


def test_six_pairs_and_full_deadline_denominator():
    outcomes = {arm: _bits(range(index)) for index, arm in enumerate("ABCD")}
    assert len(all_pairwise(outcomes)) == 6
    checkpoints = [[{"round": 1, "ready_seconds": 0.6,
                     "info_correct": index % 2 == 0}]
                   for index in range(N_FRAMES)]
    deadline = deadline_summary(checkpoints)
    assert deadline["0.5"] == {"correct": 0, "missing": N_FRAMES,
                               "wrong_or_missing": N_FRAMES}
    assert deadline["1.0"] == {"correct": N_FRAMES // 2, "missing": 0,
                               "wrong_or_missing": N_FRAMES // 2}


def test_fixed_gate_does_not_invent_s_or_e_threshold():
    base = _bits(range(N_FRAMES))
    original = _bits(range(34))
    report = fixed_gates({arm: base.copy() for arm in "ABCD"}, original,
                         {arm: 1.0 for arm in "ABCD"},
                         {arm: 1.0 for arm in "ABCD"})
    assert report["original_B_only_rescues_absorbed_by_C"] == 34
    assert report["categorical_S_or_E"].startswith("not_auto")
    assert not report["incremental_D_over_C_effect_upper_below_zero"]


def test_saved_artifact_and_durable_checkpoint_contract(tmp_path):
    project = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project / "experiments/sp_afdm_frozen_20260920/src"))
    import evidence

    stem, arm, input_sha = "s650_f0000", "A", "0" * 64
    identity = dict(schema="cstate-necessity-stage-a/1",
                    observation_id=stem, arm=arm, input_sha256=input_sha)
    decoded = np.zeros(2048, np.uint8)
    info = np.zeros(1024, np.uint8)
    checkpoints = []
    (tmp_path / "checkpoints").mkdir()
    (tmp_path / "raw").mkdir()
    (tmp_path / "decisions").mkdir()
    for index, ready in enumerate((0.2, 0.7)):
        relative = f"checkpoints/{stem}_{arm}_r{index}.npz"
        digest = evidence.save_artifact(tmp_path / relative,
            dict(event=dict(round=index, snapshot=dict(decoded=decoded)), decoded=decoded),
            dict(identity, round=index))
        checkpoints.append(dict(round=index, path=relative, artifact_sha256=digest,
            decision_ready_seconds=ready - .01, ready_seconds=ready, syndrome_weight=0))
    raw_path = f"raw/{stem}_{arm}.npz"
    raw_sha = evidence.save_artifact(tmp_path / raw_path,
        dict(observation_id=stem, arm=arm, input_sha256=input_sha, stream_ids={},
             triggered=False, baseline_syndrome_weight=0,
             final_decoded=decoded, final_info=info,
             baseline_arrays=dict(r1_decoded=decoded),
             native_decoder=dict(decoded=decoded)), identity)
    bits_sha = hashlib.sha256(decoded.tobytes()).hexdigest()
    decision_path = f"decisions/{stem}_{arm}.json"
    (tmp_path / decision_path).write_text(json.dumps(dict(
        observation_id=stem, arm=arm, input_sha256=input_sha, triggered=False,
        final_decoded_sha256=bits_sha, final_decoded=decoded.tolist(),
        final_info=info.tolist(), raw_sha256=raw_sha,
        checkpoints=checkpoints, final_syndrome_weight=0)))
    from analyze_stage_a import sha256
    row = dict(observation_id=stem, arm=arm, input_sha256=input_sha, stream_ids={},
               triggered=False, baseline_syndrome_weight=0, final_syndrome_weight=0,
               final_decoded_sha256=bits_sha, checkpoints=checkpoints,
               raw_path=raw_path, raw_sha256=raw_sha,
               decision_path=decision_path,
               decision_sha256=sha256(tmp_path / decision_path),
               complete_latency_seconds=.9, acquisition_seconds=.1, refit_seconds=.1,
               tf_seconds=.2, decoder_seconds=.2, branch_seconds=0.,
               raw_serialization_seconds=.1, decision_record_seconds=.1)
    result, _ = _decision(evidence, tmp_path, row, np.zeros((1, 2048), np.int32),
                          np.arange(1024), decoded, info)
    assert result["info_correct"] and result["coded_correct"]
    assert latest_ready(result["checkpoints"], .5)["round"] == 0
    assert latest_ready(result["checkpoints"], 1.)["round"] == 1


def test_remote_git_attestation_and_input_inventory_fail_closed(tmp_path):
    root = tmp_path / "observed"
    root.mkdir()
    (root / "ledger.jsonl").write_text('{"status":"ok"}\n')
    seal = root / "observed_seal.json"
    content_hash = hashlib.sha256((root / "ledger.jsonl").read_bytes()).hexdigest()
    seal.write_text(json.dumps({"status": "pass", "files": {"ledger.jsonl": content_hash}}))
    _verify_file_inventory(root, "observed_seal.json")
    (root / "ledger.jsonl").write_text('{"status":"changed"}\n')
    with pytest.raises(ValueError, match="inventory differs"):
        _verify_file_inventory(root, "observed_seal.json")

    seal_bytes = seal.read_bytes()
    observed_commit, registration_commit = "a" * 40, "b" * 40
    repo_path = "project/results/stage_a/observed_seal.json"
    registration_hash = "c" * 64
    attestation = dict(
        schema="cstate-necessity-stage-a/git-attestation/1",
        registration_commit=registration_commit, observed_commit=observed_commit,
        seal_repo_path=repo_path, registration_sha256=registration_hash,
        seal_sha256=hashlib.sha256(seal_bytes).hexdigest(),
        git_blob_oid=hashlib.sha1(f"blob {len(seal_bytes)}\0".encode() + seal_bytes).hexdigest(),
        git_blob_size_bytes=len(seal_bytes),
        git_blob_sha256=hashlib.sha256(seal_bytes).hexdigest(),
        merge_base_is_ancestor=True, checked_by="local_git_show_and_merge_base")
    path = tmp_path / "git_attestation.json"
    path.write_text(json.dumps(attestation))
    assert _verify_git_attestation(path, registration_commit=registration_commit,
        observed_commit=observed_commit, seal_repo_path=repo_path,
        registration_sha256=registration_hash, seal_path=seal,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest()) == hashlib.sha256(path.read_bytes()).hexdigest()
    attestation["merge_base_is_ancestor"] = False
    path.write_text(json.dumps(attestation))
    with pytest.raises(ValueError, match="attestation differs"):
        _verify_git_attestation(path, registration_commit=registration_commit,
            observed_commit=observed_commit, seal_repo_path=repo_path,
            registration_sha256=registration_hash, seal_path=seal,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="transferred local Git attestation SHA differs"):
        _verify_git_attestation(path, registration_commit=registration_commit,
            observed_commit=observed_commit, seal_repo_path=repo_path,
            registration_sha256=registration_hash, seal_path=seal,
            expected_sha256="0" * 64)
