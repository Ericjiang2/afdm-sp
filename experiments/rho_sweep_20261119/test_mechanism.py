"""Saved first-exchange versus bypass and decoding-discordance contracts."""

from copy import deepcopy

import numpy as np
import pytest

from mechanism import read_first_exchange, summarize


def _traces():
    paths = [dict(delay=3, doppler=.1), dict(delay=4, doppler=-.1), dict(delay=5, doppler=0.)]
    bank = dict(candidate_delays=np.array([3, 3, 7, 7, 8]),
                candidate_dopplers=np.array([0., .25, -.25, 0., 0.]),
                entering_paths=paths)
    scores = np.full((3, 5), 10.)
    valid = np.ones_like(scores, dtype=bool)
    # The weakest slot has no legal phantom, so the other survivor-compatible slot is selected.
    valid[1, :2] = False
    return {
        'A2': dict(**bank, valid=valid, scores=scores,
                   accepted=dict(slot=2, new=dict(delay=3, doppler=0.))),
        'CD': dict(**bank, valid=valid.copy(), scores=scores.copy(),
                   accepted=dict(slot=2, new=dict(delay=7, doppler=-.25))),
    }


def _truth():
    return dict(l_i=np.array([3, 3, 4, 7, 8]), k_real=np.array([.1, .3, -.1, -.2, 0.]),
                g_i=np.array([5., 1j, 3., 2., 1.]))


def test_common_legal_pair_is_fixed_and_scored_by_both_arms():
    traces = _traces()
    traces['A2']['scores'][2, :4] = [1., 0., 2., -1.]
    traces['CD']['scores'][2, :4] = [5., 0., 2., -2.]
    value = read_first_exchange(traces, _truth(), [3., 1., 2.])
    assert value['first_edit'] == {'A2': 'phantom', 'CD': 'true_delay'}
    assert value['true_codelay'] == {'A2': True, 'CD': False}
    pair = value['paired_candidates']
    assert pair['slot'] == 2
    assert pair['phantom'] == {'delay': 3, 'doppler': 0.}
    assert pair['true_delay'] == {'delay': 7, 'doppler': -.25}
    assert pair['by_arm']['A2'] == dict(phantom_objective=1., true_delay_objective=2., winner='phantom')
    assert pair['by_arm']['CD'] == dict(phantom_objective=5., true_delay_objective=2., winner='true_delay')


def test_no_bracketed_pair_and_other_edit_are_explicit():
    traces = _traces()
    traces['A2']['accepted'] = None
    traces['CD']['accepted'] = dict(slot=0, new=dict(delay=3, doppler=.25))
    truth = dict(l_i=np.array([3, 4]), k_real=np.array([.1, -.1]), g_i=np.array([5., 3.]))
    value = read_first_exchange(traces, truth, [3., 1., 2.])
    assert value['first_edit'] == {'A2': 'no_edit', 'CD': 'other'}
    assert value['true_codelay'] == {'A2': False, 'CD': False}
    assert value['paired_candidates'] is None


def test_unavailable_slots_and_score_ties():
    traces = _traces()
    value = read_first_exchange(traces, _truth(), [3., 1., 2.])
    assert value['paired_candidates']['by_arm']['A2']['winner'] == 'tie'
    for arm in traces.values():
        arm['valid'][2, :2] = False
    assert read_first_exchange(traces, _truth(), [3., 1., 2.])['paired_candidates'] is None


@pytest.mark.parametrize('field', ['entering_paths', 'candidate_delays', 'candidate_dopplers', 'valid'])
def test_different_candidate_problem_is_rejected(field):
    traces = deepcopy(_traces())
    trace = traces['CD']
    if field == 'valid':
        trace[field][0, 0] = False
    else:
        trace[field] = trace[field][::-1].copy()
    with pytest.raises(ValueError, match='same entering support and legal bank'):
        read_first_exchange(traces, _truth(), [3., 1., 2.])


def test_nonfinite_legal_cost_is_rejected():
    traces = _traces()
    traces['CD']['scores'][2, 0] = np.nan
    with pytest.raises(ValueError, match='Nonfinite legal first-exchange scores'):
        read_first_exchange(traces, _truth(), [3., 1., 2.])


def _row(frame, errors, diagnostic, scenario='U', snr=500):
    return dict(frame=frame, scenario=scenario, rho_permille=300, snr_centi_db=snr,
                triggered=diagnostic is not None, syndrome=int(diagnostic is not None),
                arms={a: dict(errors=n) for a, n in zip(('F0', 'A2', 'CD'), errors, strict=True)},
                mechanism=diagnostic)


def test_cell_counts_distinguish_triggers_edits_and_pairwise_preference():
    both_scores = read_first_exchange(_traces(), _truth(), [3., 1., 2.])
    no_edit = dict(first_edit={'A2': 'no_edit', 'CD': 'no_edit'},
                   true_codelay={'A2': False, 'CD': False}, paired_candidates=None)
    cells = summarize([_row(1, (1, 0, 1), both_scores), _row(2, (0, 1, 0), no_edit),
                       _row(3, (0, 0, 0), None), _row(1, (0, 0, 0), None, scenario='G'),
                       _row(1, (0, 0, 0), None, snr=600)])
    cell = cells['U/300/500']
    assert cell['trigger_rate'] == 2 / 3
    a2, cd = cell['arms']['A2'], cell['arms']['CD']
    assert (a2['rescues_per_trigger'], a2['harms_per_trigger']) == (.5, .5)
    assert a2['first_edits']['counts'] == dict(phantom=1, true_delay=0, other=0, no_edit=1)
    assert a2['first_edits']['shares_of_accepted']['phantom'] == 1.
    assert a2['first_edits']['phantom_on_true_codelay'] == 1
    assert a2['common_pair']['eligible_triggers'] == 1
    assert a2['common_pair']['shares']['tie'] == 1.
    assert cd['first_edits']['shares_of_accepted']['true_delay'] == 1.
    for value in (cells['G/300/500'], cells['U/300/600']):
        arm = value['arms']['A2']
        assert value['trigger_rate'] == 0.
        assert arm['rescues_per_trigger'] is None
        assert arm['first_edits']['shares_of_accepted']['phantom'] is None
        assert arm['common_pair']['shares']['phantom'] is None


def test_bypass_identity_missing_mechanism_and_duplicate_fail_closed():
    row = _row(1, (0, 0, 0), None)
    with pytest.raises(ValueError, match='Duplicate mechanism row'):
        summarize([row, row])
    row['arms']['A2']['decoded_sha'] = 'wrong'
    with pytest.raises(ValueError, match='must match F0'):
        summarize([row])
    row['triggered'] = True
    with pytest.raises(ValueError, match='disagreement with syndrome'):
        summarize([row])
    row['syndrome'] = 1
    with pytest.raises(ValueError, match='present exactly for triggers'):
        summarize([row])
