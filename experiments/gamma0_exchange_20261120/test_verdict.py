"""Synthetic checks of the pre-freeze verdict and secondary readouts."""

from copy import deepcopy

import numpy as np
import pytest

import verdict as v


@pytest.mark.parametrize(('interval', 's', 'cd', 'expected'), [
    ((.0, .10), (.80, .95), (.0, .05), 'SUPPORTED'),
    ((.30, .50), (.80, .95), (.0, .05), 'REFUTED'),
    ((.09, .25), (.80, .95), (.0, .05), 'INCONCLUSIVE'),
    ((.29, .31), (.80, .95), (.0, .05), 'INCONCLUSIVE'),
    ((.0, .10), (.799, .95), (.0, .05), 'ANCHOR_FAIL'),
    ((.30, .50), (.80, .95), (.0, .051), 'ANCHOR_FAIL'),
    (None, None, None, 'ANCHOR_FAIL'),
])
def test_phantom_verdict(interval, s, cd, expected):
    assert v.phantom_verdict(interval, s, cd) == expected


def test_scalar_anchor_can_use_predefined_archive_floor():
    assert v.phantom_verdict((0., .1), (.77, .85), (0., .05), s_anchor_floor=.77) == 'SUPPORTED'
    assert v.phantom_verdict((0., .1), (.77, .85), (0., .05), s_anchor_floor=.78) == 'ANCHOR_FAIL'


@pytest.mark.parametrize(('interval', 'expected'), [
    ((-.03, .03), 'EQUIVALENT'),
    ((-.05, -.031), 'CD_BETTER'),
    ((.031, .05), 'Z_BETTER'),
    ((-.05, -.03), 'INCONCLUSIVE'),
    ((.03, .05), 'INCONCLUSIVE'),
    ((-.04, .04), 'INCONCLUSIVE'),
    (None, 'INCONCLUSIVE'),
])
def test_rescue_verdict(interval, expected):
    assert v.rescue_verdict(interval) == expected


def arm(delays, errors=1, gains=None, edits=(), syndrome=2):
    return dict(paths=[[delay, 0.] for delay in delays],
                gains=gains or [[1., 0.] for _ in delays],
                errors=errors, syndrome=syndrome, edits=list(edits), decoded_sha='synthetic')


def edit(delay, doppler=.1):
    return dict(slot=1, old=dict(delay=2, doppler=0.), new=dict(delay=delay, doppler=doppler))


def panel(triggers):
    rows = []
    for frame, count in triggers.items():
        for scenario, rho in v.CELLS:
            for offset, snr in enumerate(v.GRID[rho]):
                triggered = (scenario, rho) == ('U', 300) and offset < count
                f0 = arm([0, 2], syndrome=2 if triggered else 0)
                arms = dict.fromkeys(v.ARMS, f0)
                if triggered:
                    cd = arm([0, 1], gains=[[.75, 0.], [2., 0.]], edits=[edit(1)])
                    z = (arm([0, 3], errors=0, gains=[[3., 4.], [1., 0.]], edits=[edit(3)])
                         if frame == min(triggers) and not offset else cd)
                    # H creates a phantom on its first edit and repairs it on its second.
                    h = arm([0, 1], errors=0, edits=[edit(0), dict(
                        slot=1, old=dict(delay=0, doppler=.1), new=dict(delay=1, doppler=0.))])
                    h['paths'][1][1] = .5
                    arms.update(CD=cd, Z=z, H=h, S=arm([0, 0], edits=[edit(0, doppler=.25)]))
                    arms['Z-sel'] = z | {'errors': 1}
                identity = dict.fromkeys(('info', 'coded', 'noise', 'pilot', 'data'),
                                         f'{scenario}-{rho}-{frame}')
                rows.append(dict(scenario=scenario, rho_permille=rho, snr_centi_db=snr, frame=frame,
                                 syndrome=f0['syndrome'], arms=arms, inputs=identity,
                                 truth=dict(delays=[0, 1], gains=[[2., 0.], [4., 0.]])))
    return rows


def test_pooled_trigger_rates_and_shared_frame_draws():
    frames = [1, 2, 3]
    rows = panel({1: 2, 2: 1, 3: 1})
    result = v.analyze(reversed(rows), frames)
    assert (result['frames'], result['keys'], result['triggered']) == (3, 102, 4)
    assert result['bootstrap'] == dict(draws=20_000, seed=20261126, draws_without_triggers=0)
    assert result['p_a']['verdict'] == {'Z': 'SUPPORTED', 'H': 'REFUTED'}
    assert result['p_a']['first_edit_phantom_rate']['S']['interval95'] == [1., 1.]
    assert result['p_b']['verdict'] == 'INCONCLUSIVE'
    delta = result['p_b']['z_minus_cd']
    assert delta['point'] == .25 and delta['direction'] == 'Z'
    assert delta['discordance'] == {'Z': 1, 'CD': 0}
    # Select frame identities independently of the code's per-frame row construction.
    weights = np.random.default_rng(20261126).multinomial(3, [1/3] * 3, size=20_000)
    expected = np.sort(weights[:, 0] / (weights[:, 0] + 3))
    assert delta['interval95'] == [expected[499], expected[19499]]
    secondary = result['secondary']
    assert secondary['h_minus_cd_rescue']['point'] == 1.
    assert secondary['h_minus_cd_rescue']['discordance'] == {'H': 4, 'CD': 0}
    assert secondary['first_step']['CD']['categories']['true_restoration'] == dict(keys=4, proportion=1.)
    assert secondary['first_step']['Z']['categories']['other'] == dict(keys=1, proportion=.25)
    assert secondary['first_step']['S']['categories']['phantom'] == dict(keys=4, proportion=1.)
    assert secondary['first_step']['S']['near_phantom_fraction'] == 1.
    assert secondary['final_phantom_rate']['H']['keys'] == 0
    assert secondary['first_to_final_phantom']['H']['first_phantom'] == {
        'final_phantom': 0, 'final_nonphantom': 4}
    assert secondary['first_to_final_phantom']['S']['first_phantom'] == {
        'final_phantom': 4, 'final_nonphantom': 0}
    geometry = secondary['exchange_geometry_agreement_vs_cd']
    assert geometry['Z']['first_edit_agreement'] == dict(keys=3, both_no_edit=0, proportion=.75)
    assert geometry['Z']['refined_doppler_agreement']['exact_keys'] == 3
    assert geometry['H']['refined_doppler_agreement'] == dict(
        equal_delay_multiset_keys=4, exact_keys=0, exact_fraction=0., median_abs_gap_bins=.25)
    assert secondary['delay_multiset_agreement'] == {
        'Z': dict(keys=3, proportion=.75), 'H': dict(keys=4, proportion=1.)}
    assert secondary['z_sel']['minus_z']['point'] == -.25
    assert secondary['z_sel']['minus_z']['discordance'] == {'Z-sel': 0, 'Z': 1}
    assert secondary['z_sel']['minus_cd']['point'] == 0.
    fer = secondary['full_grid_fer_difference_vs_cd']['Z']
    assert fer['point'] == -1/102
    assert (fer['only_arm_failed'], fer['only_cd_failed']) == (0, 1)
    cell = secondary['cells']['U_300']
    assert cell['failures']['Z'][500] == 2
    assert cell['crossing_difference_vs_cd']['Z']['point_interval_db'] == ['-inf', '+inf']
    mechanism = secondary['mechanism']
    assert mechanism['disagreement_keys'] == 1
    cd, z = (mechanism['arms'][a] for a in ('CD', 'Z'))
    assert cd['nontrue_atoms'] == 0 and cd['nontrue_atoms_per_key_histogram'] == {0: 1}
    assert z['nontrue_atoms'] == 1 and z['nontrue_atoms_per_key_histogram'] == {1: 1}
    assert cd['matched_gain_magnitude_ratio']['median'] == (.375 + .5) / 2
    assert z['matched_gain_magnitude_ratio']['median'] == 2.5


def test_trigger_free_draws_are_observable():
    result = v.analyze(panel({1: 1, 2: 0}), [1, 2])
    assert 0 < result['bootstrap']['draws_without_triggers'] < v.BOOT_DRAWS
    assert result['p_a']['verdict'] == {'Z': 'ANCHOR_FAIL', 'H': 'ANCHOR_FAIL'}
    assert result['p_a']['first_edit_phantom_rate']['S']['point'] == 1.
    assert result['p_a']['first_edit_phantom_rate']['S']['interval95'] is None
    assert result['p_b']['verdict'] == 'INCONCLUSIVE'
    assert result['p_b']['z_minus_cd']['point'] == 1.
    assert result['secondary']['full_grid_fer_difference_vs_cd']['Z']['point'] == -1/68


def test_no_triggered_keys():
    result = v.analyze(panel({1: 0}), [1])
    assert result['triggered'] == 0
    assert result['p_b']['z_minus_cd'] == dict(
        point=None, interval95=None, direction=None, discordance={'Z': 0, 'CD': 0})
    secondary = result['secondary']
    assert secondary['mechanism']['disagreement_keys'] == 0
    assert secondary['mechanism']['arms']['Z']['matched_gain_magnitude_ratio']['median'] is None
    assert secondary['full_grid_fer_difference_vs_cd']['Z']['interval95'] == [0., 0.]


@pytest.mark.parametrize(('failure_counts', 'point', 'bounds', 'censored'), [
    ((0, 0), 5., ['-inf', 5.], (2, 0)),
    ((8, 3), 6., [6., '+inf'], (0, 2)),
    ((8, 1), 5 + 2/3, [5+2/3, 5+2/3], (0, 0)),
    ((8, 0), 5.5, [5.5, 5.5], (0, 0)),
])
def test_crossing_and_censoring(failure_counts, point, bounds, censored):
    failed = np.arange(200)[:, None] < np.asarray(failure_counts)
    readout, _, _ = v.crossing_readout(failed, [500, 600], np.ones((2, 200)))
    assert readout['clipped_point_db'] == pytest.approx(point)
    for actual, expected in zip(readout['point_interval_db'], bounds, strict=True):
        assert actual == (pytest.approx(expected) if isinstance(expected, float) else expected)
    assert (readout['left_censored_draws'], readout['right_censored_draws']) == censored


def test_first_step_uses_retained_slots_and_true_delay_coverage():
    entering = [[0, 0.], [2, 0.]]
    assert v.first_step(entering, [], [0, 1]) == ('no_edit', None, None)
    assert v.first_step(entering, [edit(2)], [0, 2])[0] == 'other'
    assert v.first_step(entering, [edit(0)], [0, 1]) == ('phantom', (1, 0, .1), .1)
    assert v.first_step(entering, [edit(1)], [0, 1])[0] == 'true_restoration'
    with pytest.raises(ValueError, match='entering slot'):
        v.first_step(entering, [edit(1) | {'slot': 0}], [0, 1])


def test_exact_panel_contract():
    rows = panel({1: 1})
    with pytest.raises(ValueError, match='missing keys'):
        v.ordered_rows(rows[1:], [1])
    with pytest.raises(ValueError, match='duplicate'):
        v.ordered_rows(rows + rows[:1], [1])
    wrong_inputs = deepcopy(rows)
    wrong_inputs[1]['inputs']['noise'] = 'wrong'
    with pytest.raises(ValueError, match='identity changes'):
        v.ordered_rows(wrong_inputs, [1])
    wrong_truth = deepcopy(rows)
    wrong_truth[0]['truth']['delays'] = [0, 0]
    with pytest.raises(ValueError, match='non-distinct'):
        v.ordered_rows(wrong_truth, [1])
    wrong_passthrough = deepcopy(rows)
    wrong_passthrough[1]['arms']['H'] = arm([0, 0])
    with pytest.raises(ValueError, match='does not pass F0 through'):
        v.ordered_rows(wrong_passthrough, [1])
    wrong_z_sel = deepcopy(rows)
    wrong_z_sel[0]['arms']['Z-sel'] = arm([0, 0])
    with pytest.raises(ValueError, match='does not use Z support'):
        v.ordered_rows(wrong_z_sel, [1])
