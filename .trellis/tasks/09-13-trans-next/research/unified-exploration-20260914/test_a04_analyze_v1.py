from a04_analyze_v1 import candidate_decision


def contrasts(mean, interval, usable=True):
    return [dict(pilot=pilot, snr=snr, mean=mean, simultaneous_95=interval,
                 inference_usable=usable)
            for _ in range(4) for pilot in ('p0', 'pZ') for snr in (10, 20)]


def test_ber_gain_does_not_pass_when_full_cost_exceeds_frozen_limit():
    values = contrasts(-.02, [-.03, -.01])
    decision = candidate_decision(values, 1.26, 1000)
    assert decision['benefit_ber_gate'] and not decision['usable']
    assert decision['status'] == 'NOT_SUPPORTED'


def test_equivalence_needs_both_events_and_actual_reduction():
    values = contrasts(0., [-.003, .003])
    assert not candidate_decision(values, .7, 99)['usable']
    assert not candidate_decision(values, .76, 1000)['usable']
    assert candidate_decision(values, .7, 1000)['usable']


def test_degenerate_intervals_cannot_admit_even_with_zero_difference():
    decision = candidate_decision(contrasts(0., None, False), .5, 1000)
    assert not decision['usable'] and decision['status'] == 'STATISTICALLY_UNCERTAIN'


def test_main_gain_does_not_hide_other_endpoint_deterioration():
    values = contrasts(-.02, [-.03, -.01])
    values[0].update(mean=.02, simultaneous_95=[.011, .029])
    decision = candidate_decision(values, 1., 1000)
    assert decision['primary_effect_gate'] and not decision['other_endpoint_gate'] and not decision['usable']
