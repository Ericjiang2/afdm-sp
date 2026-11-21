"""Synthetic checks for the sweep's frame pairing and all verdict branches."""
import numpy as np
import pytest

from analysis import (
    ARMS,
    KEY_FIELDS,
    RHOS,
    SCENARIOS,
    Bounds,
    _crossings,
    _crossing,
    _difference,
    _joint_crossing_rectangle,
    _optimum_sets,
    analyze,
    confirmatory,
)


def exact(values):
    values = np.asarray(values, dtype=float)
    return Bounds(values, values)


def test_stage3_crossing_first_hit_and_censoring():
    bounds = _crossing(
        [[.01, .03, 0], [.07, .03, .02], [.04, .01, .05], [.04, 0, .02]],
        400,
        [500, 550, 600],
    )
    interpolated = 5 + .5 * np.log10(.01 / .04) / np.log10((.5 / 400) / .04)
    np.testing.assert_allclose(bounds.lower, [-np.inf, 6, 5.5, interpolated])
    np.testing.assert_allclose(bounds.upper, [5, np.inf, 5.5, interpolated])
    unresolved_zero = _crossing([[.1, 0]], 20, [500, 550])
    np.testing.assert_allclose(unresolved_zero.lower, [5.5])
    np.testing.assert_allclose(unresolved_zero.upper, [5.5])


def test_difference_retains_one_sided_bounds_and_simultaneous_censoring():
    baseline = Bounds(np.array([-np.inf, 8, 9, -np.inf]), np.array([5, np.inf, 9, 5]))
    candidate = Bounds(np.array([6, 6, -np.inf, -np.inf]), np.array([6, np.inf, 5, 5]))
    delta = _difference(baseline, candidate)
    np.testing.assert_array_equal(delta.lower, [-np.inf, -np.inf, 4, -np.inf])
    np.testing.assert_array_equal(delta.upper, [-1, np.inf, np.inf, np.inf])


def repeated(low, high):
    return Bounds(np.full(201, low), np.full(201, high))


def paired_scenarios(curves):
    return {(scenario, *unit): bounds for scenario in SCENARIOS for unit, bounds in curves.items()}


def test_primary_retains_decisive_one_sided_confirmations():
    curves = {(300, 'F0'): repeated(8, 8), (500, 'F0'): repeated(7, 7),
              (300, 'CD'): repeated(-np.inf, 5), (500, 'CD'): repeated(7, 7)}
    result = confirmatory(paired_scenarios(curves), (300, 500))
    assert result['P1']['ci98_33_db'] == [3, '+inf']
    assert result['P1']['verdict'] == 'supported'
    assert result['P2']['ci98_33_db'] == ['-inf', -2]
    assert result['P2']['verdict'] == 'supported'
    assert result['P3']['ci98_33_db'] == [2, '+inf']
    assert result['P3']['verdict'] == 'ahead'
    assert all(report['censored_draw_fraction'] == 1 for report in result.values())


def test_primary_retains_decisive_one_sided_refutations():
    curves = {(300, 'F0'): repeated(-np.inf, 4), (500, 'F0'): repeated(7, 7),
              (300, 'CD'): repeated(8, np.inf), (500, 'CD'): repeated(6, 6)}
    result = confirmatory(paired_scenarios(curves), (300, 500))
    assert result['P1']['ci98_33_db'] == ['-inf', -5]
    assert result['P1']['verdict'] == 'refuted'
    assert result['P2']['ci98_33_db'] == [2, '+inf']
    assert result['P2']['verdict'] == 'refuted'
    assert result['P3']['ci98_33_db'] == ['-inf', -2]
    assert result['P3']['verdict'] == 'not_ahead'


def test_primary_zero_remains_inconclusive_except_p3_not_ahead():
    curves = {(rho, arm): repeated(6, 6) for rho in (300, 500) for arm in ('F0', 'CD')}
    result = confirmatory(paired_scenarios(curves), (300, 500))
    assert all(report['ci98_33_db'] == [0, 0] for report in result.values())
    assert [result[key]['verdict'] for key in ('P1', 'P2', 'P3')] == [
        'inconclusive', 'inconclusive', 'not_ahead',
    ]


def test_primary_simultaneous_right_censoring_is_inconclusive():
    curves = {(rho, arm): repeated(12, np.inf) for rho in (300, 500) for arm in ('F0', 'CD')}
    result = confirmatory(paired_scenarios(curves), (300, 500))
    assert all(report['ci98_33_db'] == ['-inf', '+inf'] for report in result.values())
    assert all(report['verdict'] == 'inconclusive' for report in result.values())


def test_p1_and_p2_use_the_exact_bonferroni_tails():
    # The adverse sign in 1% of draws enters the 98.333..% interval,
    # although it would fall outside an unadjusted central 95% interval.
    p2_cd_300 = exact([5] + [5] * 19_800 + [8] * 200)
    curves = {(300, 'F0'): exact([7] * 20_001), (500, 'F0'): exact([7] * 20_001),
              (300, 'CD'): p2_cd_300, (500, 'CD'): exact([6] * 20_001)}
    result = confirmatory(paired_scenarios(curves), (300, 500))
    assert result['P1']['ci98_33_db'] == [-2, 1]
    assert result['P2']['ci98_33_db'] == [-1, 2]
    assert result['P1']['verdict'] == result['P2']['verdict'] == 'inconclusive'


def test_p3_uses_grid_minima_with_opposite_rectangle_endpoints():
    curves = {(300, 'F0'): repeated(6, 9), (500, 'F0'): repeated(7, 8),
              (300, 'CD'): repeated(5, 7), (500, 'CD'): repeated(6, 6.5)}
    result = confirmatory(paired_scenarios(curves), (300, 500))
    assert result['P3']['point_db'] == result['P3']['ci98_33_db'] == [-.5, 3]
    assert result['P3']['verdict'] == 'inconclusive'


def test_rectangular_bands_keep_rare_compatible_optima_across_both_arms():
    # The two-ratio proxy retains the six-ratio tail threshold, below .1%.
    curves = {(300, 'F0'): exact([8] + [4] * 20 + [8] * 19_980),
              (500, 'F0'): exact([7] * 20_001),
              (300, 'CD'): exact([5] * 20_001), (500, 'CD'): exact([6] * 20_001)}
    rectangle = _joint_crossing_rectangle(curves, (300, 500))
    result = _optimum_sets(rectangle, (300, 500))
    assert result['crossing_bounds_db']['300']['F0'] == [4, 8]
    assert result['compatible_rho_permille'] == {'CD': [300], 'F0': [300, 500]}
    assert result['cd_set_strictly_below_f0'] is False
    assert confirmatory(paired_scenarios(curves), (300, 500))['P3']['ci98_33_db'] == [-1, 2]


def test_optimum_sets_keep_exact_ties_and_remove_dominated_censoring():
    curves = {(300, 'F0'): repeated(7, np.inf), (500, 'F0'): repeated(6, 6),
              (300, 'CD'): repeated(5, 5), (500, 'CD'): repeated(5, 5)}
    rectangle = _joint_crossing_rectangle(curves, (300, 500))
    result = _optimum_sets(rectangle, (300, 500))
    assert result['compatible_rho_permille'] == {'CD': [300, 500], 'F0': [500]}
    assert result['cd_set_strictly_below_f0'] is False
    curves[500, 'CD'] = repeated(6, np.inf)
    rectangle = _joint_crossing_rectangle(curves, (300, 500))
    result = _optimum_sets(rectangle, (300, 500))
    assert result['compatible_rho_permille'] == {'CD': [300], 'F0': [500]}
    assert result['cd_set_strictly_below_f0'] is True


def test_sample_size_projection_uses_actual_point_and_projected_draw_zero_floor():
    grid = {('U', 300): (500, 600)}
    frames = tuple(range(50))
    indexed = {(scenario, rho, snr, frame): {arm: int(snr == 500) for arm in ARMS}
               for (scenario, rho), snrs in grid.items() for snr in snrs for frame in frames}
    curves, _ = _crossings(indexed, grid, frames, sample_size=100)
    curve = curves['U', 300, 'CD']
    assert curve.lower[0] == curve.upper[0] == 6
    expected = 5 + np.log10(.01) / np.log10(.5 / 100)
    np.testing.assert_allclose(curve.lower[1:], expected)
    np.testing.assert_allclose(curve.upper[1:], expected)


def test_shared_frame_counts_keep_independently_ordered_rows_paired():
    snrs = (400, 500, 600, 700)
    grid = {(scenario, rho): snrs for scenario in SCENARIOS for rho in RHOS}
    frames = range(100)
    rows = []
    for scenario, rho in grid:
        for snr, failures in zip(snrs, (35, 9, 1, 0), strict=True):
            for frame in frames:
                key = (scenario, rho, snr, frame)
                rows.append(dict(zip(KEY_FIELDS, key, strict=True),
                                 arms={arm: {'errors': int(frame < failures)} for arm in ARMS}))
    result = analyze(reversed(rows), grid, frames)
    assert result['verdicts']['P1']['ci98_33_db'] == [0, 0]
    assert result['verdicts']['P2']['ci98_33_db'] == [0, 0]
    assert result['exploratory']['V1']['ci95_db'] == [0, 0]
    assert result['exploratory']['V4']['ci95_db'] == [0, 0]
    assert result['supplement']['half_width_db'] > 0
    with pytest.raises(ValueError, match='Duplicate row'):
        analyze(rows + rows[:1], grid, frames)
    with pytest.raises(ValueError, match='1 missing'):
        analyze(rows[1:], grid, frames)
    with pytest.raises(ValueError, match='distinct physical frame'):
        analyze(rows, grid, [*frames, 0])
    with pytest.raises(ValueError, match='distinct SNR'):
        analyze(rows, {**grid, ('U', 300): (*snrs, 400)}, frames)


def test_sweep_reports_scenario_reversal_and_mechanism_with_no_exploratory_verdict():
    snrs = tuple(range(400, 1100, 100))
    grid = {(scenario, rho): snrs for scenario in SCENARIOS for rho in RHOS}
    frames = range(10)
    thresholds = {
        ('U', 300): (800, 800, 600), ('U', 500): (700, 800, 700), ('U', 150): (800, 800, 700),
        ('G', 300): (700, 800, 800), ('G', 500): (800, 800, 700), ('G', 150): (800, 800, 900),
    }
    rows = []
    for scenario, rho in grid:
        for snr in snrs:
            counts = {arm: int(snr < threshold) for arm, threshold in zip(
                ARMS, thresholds.get((scenario, rho), (800, 800, 800)), strict=True)}
            triggered = len(set(counts.values())) > 1
            diagnostic = dict(first_edit={'A2': 'phantom', 'CD': 'true_delay'},
                              true_codelay={'A2': False, 'CD': False}, paired_candidates=None)
            for frame in frames:
                key = (scenario, rho, snr, frame)
                rows.append(dict(
                    zip(KEY_FIELDS, key, strict=True),
                    arms={arm: {'errors': count} for arm, count in counts.items()},
                    triggered=triggered, mechanism=diagnostic if triggered else None,
                ))
    result = analyze(rows, grid, frames)
    assert result['verdicts']['P1']['point_db'] == [0, 0]
    assert result['verdicts']['P2']['point_db'] == [0, 0]
    by_scene = result['exploratory']['by_scenario']
    assert by_scene['U']['primary_contrasts']['P1']['point_db'] == [2, 2]
    assert by_scene['G']['primary_contrasts']['P1']['point_db'] == [-2, -2]
    assert by_scene['U']['primary_contrasts']['P2']['point_db'] == [-1, -1]
    assert by_scene['G']['primary_contrasts']['P2']['point_db'] == [1, 1]
    assert 'verdict' not in by_scene['U']['primary_contrasts']['P1']
    assert 'verdict' not in result['exploratory']['V1']
    assert 'verdict' not in result['exploratory']['V4']
    direction = result['exploratory']['below_300']['150']['crossing_change_vs_300']
    assert direction['CD']['point_db'] == [1, 1]
    rescue = result['mechanism']['U/300/700']
    assert rescue['trigger_rate'] == 1
    assert rescue['arms']['CD']['rescues_per_trigger'] == 1
    assert rescue['arms']['A2']['first_edits']['shares_of_accepted']['phantom'] == 1
    del rows[0]['mechanism']
    with pytest.raises(ValueError, match='every row'):
        analyze(rows, grid, frames)
