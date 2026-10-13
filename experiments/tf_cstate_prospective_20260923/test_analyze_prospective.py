"""Synthetic-only prospective analysis contracts; no generated frame access."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_prospective import (_git_committed_seal, _git_committed_truth_seal,
                                 _git_registration, distribution, error_flags,
                                 latest_ready, paired_counts, paired_latency,
                                 recount, summarize_cell, stage_summary, STAGES,
                                 _report)


def test_paired_latency_keeps_delta_ratio_and_ratio_of_means_distinct():
    result = paired_latency([1., 3.], [2., 3.])
    assert result['paired_delta_seconds']['mean_seconds'] == .5
    assert result['paired_ratio']['mean'] == 1.5
    assert result['ratio_of_means'] == 1.25
    assert result['tf']['median_seconds'] == 2.
    assert result['combined']['p95_seconds'] == pytest.approx(2.95)
    assert distribution([0., 2.])['mean_seconds'] == 1.
    with pytest.raises(ValueError):
        paired_latency([0., 1.], [1., 2.])


def test_deadline_retains_latest_ready_and_full_n_missing_as_failure():
    decisions = [dict(round=0, decision_ready_seconds=.2),
                 dict(round=1, decision_ready_seconds=.45),
                 dict(round=2, decision_ready_seconds=.7)]
    assert latest_ready(decisions)['round'] == 1
    assert latest_ready(decisions, .1) is None
    rows = [dict(tf=True, combined=True),
            dict(tf=True, combined=False),
            dict(tf=False, combined=True),
            dict(tf=False, combined=False)]
    assert paired_counts(rows, 'tf', 'combined') == dict(
        both_correct=1, tf_only_correct=1,
        combined_only_correct=1, neither_correct=1)
    with pytest.raises(ValueError, match='explicit booleans'):
        paired_counts([dict(tf=True, combined=None)], 'tf', 'combined')


def test_independent_recount_keeps_info_codeword_syndrome_distinct():
    H = np.array([[1, 1, 0, 0], [0, 0, 1, 1]], np.uint8)
    truth = np.array([0, 0, 0, 0], np.uint8)
    decoded = np.array([1, 1, 0, 0], np.uint8)
    result = recount(decoded, np.array([0, 0], np.uint8), truth, H,
                     np.array([0, 2]))
    assert result == dict(info_errors=1, coded_errors=2, syndrome_weight=0)
    assert error_flags(result) == dict(undetected=True,
        syndrome_zero_coded_wrong=True, info_correct_coded_wrong=False)
    coded_only = recount(np.array([0, 1, 0, 0], np.uint8),
                         np.array([0, 0], np.uint8), truth, H,
                         np.array([0, 2]))
    assert error_flags(coded_only) == dict(undetected=False,
        syndrome_zero_coded_wrong=False, info_correct_coded_wrong=True)


def test_git_show_binds_actual_seal_bytes(tmp_path):
    repo = tmp_path/'evidence_git'
    repo.mkdir()
    subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.invalid'], check=True)
    committed = repo/'observed'/'observed_seal.json'
    committed.parent.mkdir()
    committed.write_text('{"status":"pass"}\n')
    subprocess.run(['git', '-C', str(repo), 'add', 'observed/observed_seal.json'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'seal'], check=True)
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    actual = tmp_path/'observed_seal.json'
    actual.write_bytes(committed.read_bytes())
    result = _git_committed_seal(repo, commit, actual, 'observed/observed_seal.json')
    assert result['commit'] == commit
    assert result['committed_at']
    actual.write_text('{"status":"tampered"}\n')
    with pytest.raises(ValueError, match='committed observed seal bytes'):
        _git_committed_seal(repo, commit, actual, 'observed/observed_seal.json')


def test_committed_truth_seal_rejects_joint_disk_truth_rewrite(tmp_path):
    repo = tmp_path/'evidence_git'
    repo.mkdir()
    subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.invalid'], check=True)
    (repo/'population_truth_seal.json').write_text('{"files":{"truth/x":"original"}}\n')
    subprocess.run(['git', '-C', str(repo), 'add', 'population_truth_seal.json'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'observed and truth seal'], check=True)
    commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                                     text=True).strip()
    truth_root = tmp_path/'population_truth'
    truth_root.mkdir()
    (truth_root/'truth_seal.json').write_bytes(
        (repo/'population_truth_seal.json').read_bytes())
    assert len(_git_committed_truth_seal(repo, commit, truth_root)) == 64
    # Disk seal can be made internally consistent with tampered truth, but it
    # still cannot pass the pre-truth Git-object gate.
    (truth_root/'truth_seal.json').write_text('{"files":{"truth/x":"tampered"}}\n')
    with pytest.raises(ValueError, match='committed population truth seal bytes'):
        _git_committed_truth_seal(repo, commit, truth_root)


def test_remote_preregistration_is_ancestral_and_bytes_match(tmp_path):
    repo = tmp_path/'evidence_git'
    repo.mkdir()
    subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.invalid'], check=True)
    local = tmp_path/'protocol'
    local.mkdir()
    remote = repo/'registration'
    remote.mkdir()
    for name in ('registration.json','PROTOCOL.md','random_namespace.json',
                 'local_git_binding.json'):
        (local/name).write_text(name)
        (remote/name).write_bytes((local/name).read_bytes())
    subprocess.run(['git', '-C', str(repo), 'add', 'registration'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'preregister'], check=True)
    prereg = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                                     text=True).strip()
    (repo/'observed').mkdir()
    (repo/'observed'/'observed_seal.json').write_text('{}\n')
    subprocess.run(['git', '-C', str(repo), 'add', 'observed'], check=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'seal'], check=True)
    seal = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                                  text=True).strip()
    epoch = int(subprocess.check_output(['git', '-C', str(repo), 'show', '-s',
          '--format=%ct', seal], text=True).strip())
    result = _git_registration(repo, prereg, seal, local/'registration.json',
                               epoch, epoch)
    assert result['preregistration_commit'] == prereg
    (local/'PROTOCOL.md').write_text('tampered')
    with pytest.raises(ValueError, match='preregistered Git blob differs'):
        _git_registration(repo, prereg, seal, local/'registration.json', epoch, epoch)


def _frame(*, trigger=False, tf_correct=True, combined_correct=True):
    tf_errors = 0 if tf_correct else 2
    combined_errors = 0 if combined_correct else 3
    return dict(trigger=trigger, tf_correct=tf_correct,
        combined_correct=combined_correct, tf_info_errors=tf_errors,
        combined_info_errors=combined_errors, tf_coded_errors=tf_errors*2,
        combined_coded_errors=combined_errors*2, tf_undetected=False,
        combined_undetected=False, tf_deadline_correct=tf_correct,
        tf_syndrome_zero_coded_wrong=False,
        combined_syndrome_zero_coded_wrong=False,
        tf_info_correct_coded_wrong=False,
        combined_info_correct_coded_wrong=False,
        combined_deadline_correct=combined_correct, tf_deadline_missing=False,
        combined_deadline_missing=False,
        tf_deadline_ready_wrong=not tf_correct,
        combined_deadline_ready_wrong=not combined_correct,
        tf_latency_seconds=1., combined_latency_seconds=1.1,
        combined_fallback=False, combined_added_branch_seconds=.2 if trigger else 0.,
        combined_stages={name:(.2 if trigger and name==STAGES[0] else 0.)
                         for name in STAGES})


def test_triggered_remaining_excludes_nontrigger_valid_but_wrong():
    rows = [_frame() for _ in range(1020)] + [
        _frame(trigger=False, tf_correct=False, combined_correct=False),
        _frame(trigger=True, tf_correct=False, combined_correct=False),
        _frame(trigger=True, tf_correct=False, combined_correct=True),
        _frame(trigger=True, tf_correct=True, combined_correct=False)]
    rows[-4]['tf_syndrome_zero_coded_wrong'] = True
    rows[0]['combined_coded_errors'] = 1
    rows[0]['combined_info_correct_coded_wrong'] = True
    result = summarize_cell(rows, primary=True)
    assert result['trigger_count'] == 3
    assert result['trigger_fraction'] == 3/1024
    assert result['remaining_triggered_failure_count'] == 2
    assert result['both_wrong_count'] == 2
    assert result['rescue_count'] == 1
    assert result['harm_count'] == 1
    assert result['paired_table']['neither_correct'] == 2
    assert result['coded_bit_errors_tf'] == 12
    assert result['coded_bit_errors_combined'] == 19
    assert result['coded_ber_combined'] == 19/(1024*2048)
    assert result['syndrome_zero_coded_wrong_tf_count'] == 1
    assert result['info_correct_coded_wrong_combined_count'] == 1
    assert result['deadline_0p5']['tf_system_failure_count'] == 3
    assert stage_summary(rows)['nontrigger']['stages'][STAGES[0]]['mean_seconds'] == 0.
    summary = dict(evidence_integrity='pass',
        git_seal=dict(commit='a'*40, committed_at='2026-09-23T00:00:00+00:00',
                      seal_sha256='b'*64),
        committed_truth_seal_sha256='c'*64,
        cells={str(snr):summarize_cell(rows, primary=snr==650)
               for snr in (600,650,700)})
    report = _report(summary, {str(snr):stage_summary(rows)
                               for snr in (600,650,700)})
    assert 'Remaining triggered failures' in report
    assert 'Both wrong (all frames)' in report
    assert 'coded bit errors / BER' in report
    assert 'Zero syndrome but coded word wrong' in report
    assert 'Paired ratio' in report
    assert STAGES[-1] in report
