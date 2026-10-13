"""Synthetic-only independent recount and Git-seal boundary tests."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.stats import beta

from verify_prospective import (bit_recount, check_clock, counts_from_rows,
    inverse_cp_lower, inverse_cp_upper, latest_ready, paired_table,
    pretruth_gate, sha256)


def test_binomial_inversion_matches_exact_cp_without_primary_function():
    for n in (1, 10, 1024):
        for k in (0, 1, n // 2, n - 1, n):
            if not 0 <= k <= n:
                continue
            lower = 0. if k == 0 else beta.ppf(.025, k, n - k + 1)
            upper = 1. if k == n else beta.ppf(.975, k + 1, n - k)
            assert inverse_cp_lower(k, n) == pytest.approx(lower, abs=1e-12)
            assert inverse_cp_upper(k, n) == pytest.approx(upper, abs=1e-12)
    assert inverse_cp_upper(0, 1024) - inverse_cp_lower(23, 1024) < 0
    assert inverse_cp_upper(0, 1024) - inverse_cp_lower(0, 1024) > 0


def test_sparse_parity_recount_distinguishes_valid_wrong_from_correct():
    H = np.zeros((1026, 2048), np.uint8)
    H[0, :2] = 1
    H[1, 2:4] = 1
    rows, columns = np.nonzero(H)
    free = np.arange(1024)
    truth = np.zeros(2048, np.uint8)
    decoded = truth.copy()
    decoded[:2] = 1
    result = bit_recount(decoded, np.zeros(1024, np.uint8), truth,
                         rows, columns, free, H.shape[0])
    assert result == dict(info_errors=2, coded_errors=2, syndrome_weight=0)
    decoded[1] = 0
    assert bit_recount(decoded, np.zeros(1024, np.uint8), truth,
                       rows, columns, free, H.shape[0])['syndrome_weight'] == 1


def test_deadline_missing_and_paired_denominator_are_not_filtered():
    decisions = [dict(round=0, decision_ready_seconds=.2),
                 dict(round=1, decision_ready_seconds=.49),
                 dict(round=2, decision_ready_seconds=.8)]
    assert latest_ready(decisions)['round'] == 1
    assert latest_ready(decisions, .1) is None
    table = paired_table([True, False, False], [True, True, False])
    assert table == dict(both_correct=1, tf_only_correct=0,
                         combined_only_correct=1, neither_correct=1)
    with pytest.raises(ValueError):
        paired_table([True, False], [True])


def test_complete_clock_includes_raw_and_decision_record_once():
    from verify_prospective import STAGES
    stages = {name: 0. for name in STAGES}
    stages.update(message_handling=.01, tf=.02, ldpc=.03,
                  checkpoint_write=.04, raw_serialization_hash=.05)
    row = dict(branch_exclusive_stages=stages, triggered=True,
               branch_complete_seconds=.15, branch_decision_seconds=.06,
               input_load_seconds=.01, before_native_bookkeeping_seconds=.01,
               native_two_rounds_seconds=.2,
               before_trigger_bookkeeping_seconds=.01, trigger_seconds=.01,
               before_branch_bookkeeping_seconds=.01,
               post_trigger_output_seconds=.15,
               before_decision_record_bookkeeping_seconds=.01,
               decision_record_write_seconds=.02,
               complete_latency_seconds=.43, native_checkpoint_write_seconds=.03,
               raw_artifact_ready_seconds=.4,
               ledger_append_included_in_latency=False)
    check_clock(row)
    with pytest.raises(ValueError, match='complete receiver clock'):
        check_clock(dict(row, complete_latency_seconds=.42))
    with pytest.raises(ValueError, match='branch clocks'):
        check_clock(dict(row, branch_complete_seconds=.14))


def test_recount_summary_keeps_nontrigger_undetected_and_deadline_missing():
    def arm(info, coded, syndrome, *, missing=False):
        return dict(final=dict(info_errors=info, coded_errors=coded,
                               syndrome_weight=syndrome),
                    deadline_error=bool(missing or info),
                    deadline_missing=missing,
                    deadline_ready_wrong=bool(info and not missing),
                    fallback=False, complete_latency_seconds=.1)
    rows = [dict(triggered=False, TF=arm(1, 2, 0), TF_CSTATE=arm(1, 2, 0)),
            dict(triggered=True, TF=arm(1, 3, 2, missing=True),
                 TF_CSTATE=arm(0, 0, 0))]
    result = counts_from_rows(rows)
    assert result['triggers'] == 1
    assert result['rescues'] == 1
    assert result['remaining_triggered_failures'] == 0
    assert result['valid_but_wrong'] == {'TF': 1, 'TF_CSTATE': 1}
    assert result['deadline_missing'] == {'TF': 1, 'TF_CSTATE': 0}
    assert result['deadline_paired']['combined_only_correct'] == 1


def _git(repo: Path, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def _json(path: Path, value):
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


def test_actual_git_seal_is_required_before_truth_access(tmp_path, monkeypatch):
    import verify_prospective as verifier
    class DummyEvidence:
        @staticmethod
        def source_hashes(_root):
            return {}
        @staticmethod
        def canonical_hash(value):
            import hashlib
            return hashlib.sha256(json.dumps(value, sort_keys=True,
                separators=(',', ':')).encode()).hexdigest()
    monkeypatch.setattr(verifier, 'attach', lambda _source, _baseline: DummyEvidence())
    protocol = tmp_path / 'protocol'
    protocol.mkdir()
    (protocol / 'PROTOCOL.md').write_text('synthetic fixed protocol\n')
    _json(protocol / 'random_namespace.json', {'entropy_hex': '01' * 32})
    _json(protocol / 'local_git_binding.json', {'fixture': True})
    registration = protocol / 'registration.json'
    _json(registration, dict(schema='tf-cstate-prospective/1', status='locked',
        protocol_sha256=sha256(protocol / 'PROTOCOL.md'),
        random_namespace_sha256=sha256(protocol / 'random_namespace.json'),
        registration_source_hashes={}, native_source_hashes={},
        baseline_source_hashes={}, receiver_config={},
        cells=[{'snr_centi_db': snr, 'frames': 1024}
               for snr in (600, 650, 700)],
        streams={'entropy_hex': '01' * 32,
                 'algorithm': 'numpy.SeedSequence(8 entropy uint32 words, CSTA domain, snr_centi_db, frame, component)'},
        original_manifest_sha256=
        'de69da6d945cd56f84eb69cc5df814088885c9d28b9375015599c99abefab7d9'))
    repo = tmp_path / 'evidence_git'
    repo.mkdir()
    _git(repo, 'init', '-q')
    _git(repo, 'config', 'user.name', 'synthetic')
    _git(repo, 'config', 'user.email', 'synthetic@example.invalid')
    shutil.copytree(protocol, repo / 'registration')
    _git(repo, 'add', 'registration')
    _git(repo, 'commit', '-qm', 'preregister')
    prereg = _git(repo, 'rev-parse', 'HEAD')
    population, observed = tmp_path / 'population', tmp_path / 'observed'
    population.mkdir()
    observed.mkdir()
    _json(population / 'manifest.json', dict(schema='tf-cstate-prospective/1',
        registration_commit=prereg, registration_sha256=sha256(registration),
        protocol_sha256=sha256(protocol / 'PROTOCOL.md'), source_hashes={}))
    (population / 'ledger.jsonl').write_text('synthetic ledger\n')
    _json(population / 'generation_receipt.json', dict(status='pass',
        observations=3072, cells=[{'snr_centi_db': x, 'frames': 1024}
                                  for x in (600, 650, 700)],
        registration_sha256=sha256(registration),
        registration_commit=prereg,
        protocol_sha256=sha256(protocol / 'PROTOCOL.md'),
        random_namespace_sha256=sha256(protocol / 'random_namespace.json'),
        source_hashes_sha256=DummyEvidence.canonical_hash({}),
        observed_ledger_sha256=sha256(population / 'ledger.jsonl'),
        generation_seconds=.1))
    _json(population / 'observed_seal.json', dict(schema='tf-cstate-prospective/1',
        status='pass', observations=3072,
        files={p.name: sha256(p) for p in population.iterdir()}))
    _json(observed / 'manifest.json', dict(schema='tf-cstate-prospective/1',
        registration_commit=prereg, registration_sha256=sha256(registration),
        protocol_sha256=sha256(protocol / 'PROTOCOL.md'), source_hashes={},
        source_hashes_sha256=DummyEvidence.canonical_hash({}),
        receiver_config={},
        receiver_config_sha256=DummyEvidence.canonical_hash({}),
        population_observed_seal_sha256=sha256(
            population / 'observed_seal.json')))
    _json(observed / 'observed_seal.json', dict(schema='tf-cstate-prospective/1',
        status='pass', receiver_calls=6144,
        files={'manifest.json': sha256(observed / 'manifest.json')}))
    truth_root = tmp_path / 'truth'
    truth_root.mkdir()
    (truth_root / 'truth_seal.json').write_text('{"fixture":true}\n')
    (repo / 'observed').mkdir()
    shutil.copy2(observed / 'observed_seal.json', repo / 'observed' / 'observed_seal.json')
    shutil.copy2(truth_root / 'truth_seal.json', repo / 'population_truth_seal.json')
    _git(repo, 'add', 'observed', 'population_truth_seal.json')
    _git(repo, 'commit', '-qm', 'seal')
    seal_commit = _git(repo, 'rev-parse', 'HEAD')
    args = SimpleNamespace(registration=registration, observed=observed,
        population_observed=population, truth_root=truth_root, evidence_git=repo,
        registration_commit=prereg, seal_commit=seal_commit,
        source=tmp_path / 'source', baseline=tmp_path / 'baseline')
    _, _, _, seal_hash = pretruth_gate(args)
    assert seal_hash == sha256(observed / 'observed_seal.json')
    (truth_root / 'truth_seal.json').write_text('{"fixture":false}\n')
    with pytest.raises(ValueError, match='committed truth inventory'):
        pretruth_gate(args)
    (truth_root / 'truth_seal.json').write_text('{"fixture":true}\n')
    (observed / 'observed_seal.json').write_text('{}\n')
    with pytest.raises(ValueError, match='actual Git observed seal'):
        pretruth_gate(args)


def test_analysis_schema_crosscheck_on_complete_synthetic_population(tmp_path):
    import audit_io
    import analyze_prospective as analyzer
    from verify_prospective import _compare_csv, _compare_summary, STAGES

    observed = tmp_path / 'observed'
    observed.mkdir()
    (observed / 'observed_seal.json').write_text('{}\n')
    truth_root = tmp_path / 'truth'
    truth_root.mkdir()
    (truth_root / 'truth_seal.json').write_text('{}\n')
    protocol = tmp_path / 'protocol'
    protocol.mkdir()
    registration = protocol / 'registration.json'
    registration.write_text('{}\n')
    analysis = tmp_path / 'analysis'
    analysis.mkdir()
    args = SimpleNamespace(analysis=analysis, observed=observed,
        truth_root=truth_root,
        registration=registration, registration_commit='a' * 40,
        seal_commit='b' * 40)
    per_cell, by_key = {}, {}
    frame_csv, arm_csv, stage_csv = [], [], []
    for snr in (600, 650, 700):
        per_cell[snr] = []
        for frame in range(1024):
            stem = f's{snr}_f{frame:04d}'
            trigger = frame == 0
            tf_errors = int(trigger)
            stages = {key: 0. for key in STAGES}
            if trigger:
                stages['message_handling'] = .1
            by_key[stem, 'TF_CSTATE'] = dict(
                branch_complete_seconds=.1 if trigger else 0.,
                branch_exclusive_stages=stages,
                checkpoints=[{}, {}, {}] if trigger else [{}, {}])
            by_key[stem, 'TF'] = dict(checkpoints=[{}, {}])
            tf = dict(final=dict(info_errors=tf_errors,
                                 coded_errors=tf_errors,
                                 syndrome_weight=tf_errors),
                      checkpoint_recounts=[dict(info_errors=tf_errors,
                          coded_errors=tf_errors, syndrome_weight=tf_errors)] * 2,
                      deadline_error=bool(tf_errors), deadline_missing=False,
                      deadline_round=1,
                      deadline_ready_wrong=bool(tf_errors), fallback=False,
                      complete_latency_seconds=.1)
            combined = dict(final=dict(info_errors=0, coded_errors=0,
                                       syndrome_weight=0),
                            checkpoint_recounts=[dict(info_errors=tf_errors,
                                coded_errors=tf_errors,
                                syndrome_weight=tf_errors)] * 2 +
                                ([dict(info_errors=0, coded_errors=0,
                                       syndrome_weight=0)] if trigger else []),
                            deadline_error=False, deadline_missing=False,
                            deadline_round=1,
                            deadline_ready_wrong=False, fallback=False,
                            complete_latency_seconds=.2 if trigger else .1)
            pair = dict(observation_id=stem, triggered=trigger,
                        TF=tf, TF_CSTATE=combined)
            per_cell[snr].append(pair)
            frame_row = dict(observation_id=stem, snr_centi_db=snr,
                trigger=trigger, tf_correct=not trigger,
                combined_correct=True, tf_info_errors=tf_errors,
                combined_info_errors=0, tf_coded_errors=tf_errors,
                combined_coded_errors=0, tf_undetected=False,
                combined_undetected=False,
                tf_syndrome_zero_coded_wrong=False,
                combined_syndrome_zero_coded_wrong=False,
                tf_info_correct_coded_wrong=False,
                combined_info_correct_coded_wrong=False,
                tf_deadline_correct=not trigger,
                tf_final_syndrome_weight=tf_errors,
                combined_final_syndrome_weight=0,
                combined_deadline_correct=True, tf_deadline_missing=False,
                combined_deadline_missing=False,
                tf_deadline_ready_wrong=trigger,
                combined_deadline_ready_wrong=False,
                tf_deadline_ready_round=1, combined_deadline_ready_round=1,
                rescue=trigger, harm=False,
                remaining_triggered_failure=False, both_wrong=False,
                tf_latency_seconds=.1,
                combined_latency_seconds=.2 if trigger else .1,
                combined_fallback=False,
                combined_added_branch_seconds=.1 if trigger else 0.,
                combined_stages=stages)
            frame_csv.append(frame_row)
            stage_csv.append(dict(observation_id=stem, snr_centi_db=snr,
                trigger=trigger, complete_branch_seconds=.1 if trigger else 0.,
                **stages))
            for arm, value in (('TF', tf), ('TF_CSTATE', combined)):
                arm_csv.append(dict(observation_id=stem, arm=arm,
                    final_info_errors=value['final']['info_errors'],
                    final_coded_errors=value['final']['coded_errors'],
                    final_syndrome_weight=value['final']['syndrome_weight'],
                    syndrome_zero_coded_wrong=False,
                    info_correct_coded_wrong=False,
                    deadline_missing=False,
                    deadline_system_failure=value['deadline_error'],
                    checkpoint_info_errors=[x['info_errors'] for x in
                                            value['checkpoint_recounts']],
                    checkpoint_coded_errors=[x['coded_errors'] for x in
                                             value['checkpoint_recounts']],
                    checkpoint_syndrome_weights=[x['syndrome_weight'] for x in
                                                 value['checkpoint_recounts']]))
    audit_io.write_csv(analysis / 'frame_outcomes.csv', frame_csv)
    audit_io.write_csv(analysis / 'arm_outcomes.csv', arm_csv)
    audit_io.write_csv(analysis / 'stage_times.csv', stage_csv)
    cells = {str(snr): analyzer.summarize_cell(
        frame_csv[index * 1024:(index + 1) * 1024], primary=snr == 650)
        for index, snr in enumerate((600, 650, 700))}
    stage_summaries = {str(snr): analyzer.stage_summary(
        frame_csv[index * 1024:(index + 1) * 1024])
        for index, snr in enumerate((600, 650, 700))}
    audit_io.write_json(analysis / 'stage_summary.json', stage_summaries)
    audit_io.write_json(analysis / 'summary.json', dict(status='complete',
        evidence_integrity='pass', cells=cells,
        git_seal=dict(commit=args.seal_commit),
        git_registration=dict(preregistration_commit=args.registration_commit),
        truth_seal_sha256=sha256(truth_root / 'truth_seal.json'),
        primary_pass=cells['650']['paired_inference']['primary_pass'],
        receiver_calls_recounted=6144, observations_recounted=3072,
        checkpoints_recounted=12291))
    audit_io.write_json(analysis / 'receipt.json', dict(status='complete',
        evidence_integrity='pass', observed_seal_sha256=sha256(
            observed / 'observed_seal.json'), seal_commit=args.seal_commit,
        preregistration_commit=args.registration_commit,
        registration_sha256=sha256(registration),
        truth_seal_sha256=sha256(truth_root / 'truth_seal.json'),
        primary_pass=cells['650']['paired_inference']['primary_pass'],
        files={p.name: sha256(p) for p in analysis.iterdir() if p.is_file()}))
    _compare_csv(args, per_cell, by_key)
    computed = {str(snr): counts_from_rows(per_cell[snr])
                for snr in (600, 650, 700)}
    h, r = computed['650']['paired']['tf_only_correct'], \
           computed['650']['paired']['combined_only_correct']
    upper_h, lower_r = inverse_cp_upper(h, 1024), inverse_cp_lower(r, 1024)
    _compare_summary(args, per_cell, by_key, computed,
                     upper_h, lower_r, upper_h - lower_r)
    frame_csv[0]['tf_info_errors'] = 99
    audit_io.write_csv(analysis / 'frame_outcomes.csv', frame_csv)
    with pytest.raises(ValueError, match='analysis error count differs'):
        _compare_csv(args, per_cell, by_key)
