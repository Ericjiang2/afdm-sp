"""Fixture-only schedule, resource admission and paired-inference contracts."""
import copy
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tail_terminal_run_v1 import planned, engineering_quote
from tail_terminal_analyze_v1 import paired_analysis


def fixture_rows(limits=None):
    limits = limits or {'ORIGINAL': {7: 16, 8: 16}, 'TAIL': {7: 4, 8: 4}, 'RIDGE_T': {7: 12, 8: 12}}
    return [dict(block=b, snr=s, arm=a, physical_record_sha256='physical-'+str(b),
        scores=dict(FER=int(b < limits[a][s]), info_bit_errors=int(b < limits[a][s]),
                    info_bits=1024, H_NMSE=.1, response_NMSE=.1))
        for b in range(32) for s in (7, 8) for a in ('ORIGINAL', 'TAIL', 'RIDGE_T')]


def test_schedule_baseline_replay_precedes_new_methods_and_never_repeats_engineering():
    engineering, development = planned('engineering'), planned('development')
    assert engineering[:4] == [(b, s, 'ORIGINAL') for b in (0, 20) for s in (7, 8)]
    assert len(engineering) == 12 and len(development) == 120
    assert not set(engineering).intersection(development)
    combined = engineering + development
    assert len(set(combined)) == 132
    assert sum(a == 'ORIGINAL' for _, _, a in combined) == 4
    assert sum(a == 'RIDGE_T' for _, _, a in combined) == 64


def test_quote_accounts_for_saved_record_steps_and_rejects_excess():
    producer = dict(step_times=[dict(arm=a, seconds=2., artifact_bytes=20*2**20)
        for a in ('ORIGINAL', 'TAIL', 'RIDGE_T') for _ in range(4)])
    auditor = dict(step_times=[dict(arm='any', seconds=1., artifact_bytes=2**16) for _ in range(12)])
    q = engineering_quote(producer, auditor, 100., 200*2**20)
    assert q['predicted_campaign_seconds'] == 100 + 2*(60*4 + 120) + 180
    assert q['GO']
    slow = copy.deepcopy(producer)
    slow['step_times'][4]['seconds'] = 60.
    assert not engineering_quote(slow, auditor, 100., 200*2**20)['GO']
    huge = copy.deepcopy(producer)
    huge['step_times'][4]['artifact_bytes'] = 2**30
    assert not engineering_quote(huge, auditor, 100., 200*2**20)['bytes_go']
    with pytest.raises(ValueError):
        engineering_quote(producer, dict(step_times=[]), 0., 0)


def test_bootstrap_retains_physical_cluster_across_both_snrs():
    result = paired_analysis(fixture_rows())
    assert result['full_feedback_development_GO']
    values = np.r_[np.zeros(4), -np.ones(12), np.zeros(16)]
    draws = np.random.default_rng(202609160701).integers(0, 32, size=(20000, 32))
    expected = np.quantile(values[draws].mean(axis=1), [.0125, .9875])
    np.testing.assert_array_equal(result['primary_endpoints']['TAIL_minus_ORIGINAL']['simultaneous_95_percentile'], expected)
    assert result['primary_endpoints']['TAIL_minus_ORIGINAL']['mean'] == -12/32


def test_good_baseline_comparison_does_not_hide_stronger_ordinary_reference():
    rows = fixture_rows({'ORIGINAL': {7: 16, 8: 16}, 'TAIL': {7: 4, 8: 4}, 'RIDGE_T': {7: 0, 8: 0}})
    result = paired_analysis(rows)
    assert not result['full_feedback_development_GO']
    assert result['primary_endpoints']['TAIL_minus_RIDGE_T']['mean'] > 0


def test_cross_snr_average_cannot_hide_an_increased_error_count():
    rows = fixture_rows({'ORIGINAL': {7: 4, 8: 16}, 'TAIL': {7: 5, 8: 0}, 'RIDGE_T': {7: 4, 8: 16}})
    result = paired_analysis(rows)
    assert result['significant_against_both']
    assert not result['no_per_snr_worsening']
    assert not result['full_feedback_development_GO']


def test_partial_duplicate_and_wrong_physical_pair_reject():
    rows = fixture_rows()
    with pytest.raises(ValueError):
        paired_analysis(rows[:-1])
    with pytest.raises(ValueError):
        paired_analysis(rows + [rows[0]])
    rows[-1]['physical_record_sha256'] = 'wrong-physical-source'
    with pytest.raises(ValueError):
        paired_analysis(rows)
