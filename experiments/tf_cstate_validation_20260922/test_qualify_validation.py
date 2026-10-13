"""Meaningful Stage-0 contracts without a receiver or production observation."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

EXPERIMENTS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(EXPERIMENTS/'sp_afdm_frozen_20260920'/'src'),
                str(EXPERIMENTS/'sp_afdm_native_joint_20260921'/'src'),
                str(Path(__file__).resolve().parent)]
import geometry_validation as kernel
import qualify_validation as qualification
from qualify_validation import compare_final, compare_trace, near_tie_fixture


def _trace():
    scores = np.array([[1., 3.], [2., 4.]])
    candidates = np.array([1, 2], dtype=np.int32)
    return dict(candidate_delays=candidates, candidate_dopplers=np.array([0., 0.]),
                valid=np.ones((2, 2), bool), scores=scores,
                selected=dict(slot=0, replacement=dict(delay=1, doppler=0.)),
                top_k=[dict(rank=1, slot=0,
                            replacement=dict(delay=1, doppler=0.),
                            paths=[dict(delay=1, doppler=0.), dict(delay=3, doppler=0.)],
                            frozen_score=1.)],
                accepted=dict(slot=0, new=dict(delay=1, doppler=0.), direct_score=1.5),
                entering_objective=5.)


def test_complete_grid_acceptance_and_direct_optimum_bound():
    saved = _trace()
    actual = copy.deepcopy(saved)
    result = compare_trace('fixture', actual, saved)
    assert result['valid_slot_tests'] == 4
    assert result['accepted']
    actual['scores'][1, 1] += 3e-10
    with pytest.raises(AssertionError, match='scores'):
        compare_trace('fixture', actual, saved)
    actual = copy.deepcopy(saved)
    actual['accepted']['direct_score'] += 3e-10
    with pytest.raises(AssertionError, match='direct_refit_optimum'):
        compare_trace('fixture', actual, saved)


def test_mask_and_no_improvement_are_discrete_contracts():
    saved = _trace()
    actual = copy.deepcopy(saved)
    actual['valid'][0, 1] = False
    with pytest.raises(AssertionError, match='validity mask'):
        compare_trace('fixture', actual, saved)
    actual = copy.deepcopy(saved)
    actual['accepted'] = None
    with pytest.raises(AssertionError, match='accepted/no-improvement'):
        compare_trace('fixture', actual, saved)


def test_only_valid_scores_but_every_retained_top_candidate_are_checked():
    saved = _trace()
    saved['valid'][1, 1] = False
    actual = copy.deepcopy(saved)
    actual['scores'][1, 1] += 10.
    compare_trace('fixture', actual, saved)
    actual['top_k'][0]['paths'][1]['delay'] = 4
    with pytest.raises(AssertionError, match='top20'):
        compare_trace('fixture', actual, saved)


def test_final_geometry_checks_continuous_and_discrete_endpoint():
    path = dict(delay=2, doppler=.25)
    edit = dict(slot=0, new=path)
    saved = dict(paths=[path], gains=np.array([1+2j]),
                 objective_before=5., objective_after=4., edits=[edit], global_trace=[{}])
    actual = SimpleNamespace(paths=[kernel.Path(2, .25)], gains=np.array([1+2j]),
                             objective_before=5., objective_after=4., edits=[edit], global_trace=[{}],
                             diagnostics=dict(stage_timing=dict(total_seconds=.2)))
    assert compare_final('fixture', actual, saved)['accepted_edits'] == 1
    actual.paths = [kernel.Path(2, .250000001)]
    with pytest.raises(AssertionError, match='final_dopplers'):
        compare_final('fixture', actual, saved)


def test_executed_near_tie_order_and_guard():
    fixture = near_tie_fixture(kernel)
    assert fixture['selected_slot'] == 1
    assert fixture['winner_flat_index'] == 2


def test_input_binding_failure_leaves_explicit_failed_receipt():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        args = SimpleNamespace(run=root/'run', source=root/'source',
            baseline=root/'baseline', a_receipt=root/'A.json',
            prior_observed=root/'prior', out=root/'qualification')
        with patch.object(qualification, '_bound_inputs', side_effect=ValueError('bad seal')):
            with pytest.raises(ValueError, match='bad seal'):
                qualification.qualify(args)
        receipt = qualification.json.loads((args.out/'receipt.json').read_text())
        assert receipt['status'] == 'fail'
        assert receipt['receiver_calls'] == 0
        assert receipt['failed_stage'] == 'input_binding'


def test_prior_manifest_binds_original_ledger_and_context(tmp_path):
    run = tmp_path/'run'
    run.mkdir()
    (run/'ledger.jsonl').write_text('{}\n')
    (run/'context_header.json').write_text('{"system":{}}\n')
    manifest = dict(original_ledger_sha256=qualification.audit_io.sha256(run/'ledger.jsonl'),
                    original_context_header_sha256=qualification.audit_io.sha256(run/'context_header.json'))
    qualification._assert_original_file_hashes(manifest, run)
    (run/'context_header.json').write_text('{"system":{"c1":0}}\n')
    with pytest.raises(ValueError, match='context'):
        qualification._assert_original_file_hashes(manifest, run)
    (run/'context_header.json').write_text('{"system":{}}\n')
    (run/'ledger.jsonl').write_text('{"changed":true}\n')
    with pytest.raises(ValueError, match='ledger'):
        qualification._assert_original_file_hashes(manifest, run)
