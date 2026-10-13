"""Synthetic contract tests; these are not receiver-performance observations."""
from pathlib import Path
from types import SimpleNamespace
import sys
import time

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'sp_afdm_frozen_20260920' / 'src'))

from physical import Channel
from interventions import (_fixed_geometry_ridge, run_fixed_channel,
                           run_instrumented_baseline, run_more_work,
                           run_true_geometry)


def fixture():
    n = 8
    system = SimpleNamespace(c1=1 / (2*n), c2=1/(3*n), rho=.5)
    pilot = np.exp(2j*np.pi*np.arange(n)/n) / 2
    target = Channel(n, system.c1, system.c2, [1, 1], [.3, -.4],
                     [.6+.1j, -.2+.3j])
    observation = dict(y=target.apply(pilot), pilot=pilot,
                       sigma2=.1)
    return observation, system, target


def fake_native(system, *, fail_round=None):
    native = SimpleNamespace()

    def front(observation, _system, _code):
        n = len(observation['y'])
        return dict(delays=np.array([0, 1]), dopplers=np.array([0., 0.]),
                    gains=np.array([1.+0j, .5+0j]), mu=np.zeros(n, complex),
                    v=np.full(n, .5), prior=np.zeros(2*n))

    def refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise,
               mode='soft', max_paths=8, rounds=2):
        channel = Channel(len(y), c1, c2, ls, ks, gs)
        return channel, dict(history=[1.], evaluations=3, fft_count=2,
                             gamma=np.eye(len(ls)))

    def decoder(_code, llr, maxiter=50):
        assert maxiter == 50
        return dict(decoded=(llr < 0).astype(np.uint8), incoming_llr=llr.copy(),
                    raw_app=llr.copy(), raw_check_extrinsic=llr.copy(),
                    iterations=2)

    def receive(observation, system, code, rounds=2, iterations=20,
                ce_mode='soft', gain_mode='joint', checkpoint_sink=None,
                record_states=False):
        start = time.perf_counter()
        state = native.pilot_front(observation, system, code)
        arrays, events = {}, []
        for r in range(rounds):
            channel, detail = native.time_refine(
                observation['y'], observation['pilot'], state['mu'], state['v'],
                state['delays'], state['dopplers'], state['gains'], system.c1,
                system.c2, observation['sigma2'], mode=ce_mode,
                max_paths=8, rounds=2)
            if r == fail_round:
                raise FloatingPointError('synthetic later failure')
            llr = np.full(2*channel.n, float(iterations-r))
            dec = native.decoder_messages(code, llr, maxiter=50)
            event = dict(round=r, ready=time.perf_counter()-start,
                         ce_evaluations=detail['evaluations'])
            events.append(event)
            arrays[f'r{r}_gains'] = channel.gains.copy()
            state.update(delays=channel.delays, dopplers=channel.dopplers,
                         gains=channel.gains)
            if checkpoint_sink is not None:
                checkpoint_sink(dict(event, snapshot={'decoded':dec['decoded']}),
                                dec['decoded'].copy())
        return dec, arrays, dict(seconds=time.perf_counter()-start,
                                 pilot_seconds=0., events=events)

    native.pilot_front = front
    native.time_refine = refine
    native.decoder_messages = decoder
    native.receive = receive
    return native


def test_baseline_and_work_schedules_preserve_raw_output_and_hooks():
    obs, system, _ = fixture()
    native = fake_native(system)
    front, refine = native.pilot_front, native.time_refine
    direct_dec, direct_arrays, _ = native.receive(obs, system, None)
    baseline = run_instrumented_baseline(obs, system, None, native)
    np.testing.assert_array_equal(baseline.decoder['decoded'], direct_dec['decoded'])
    np.testing.assert_array_equal(baseline.arrays['r1_gains'], direct_arrays['r1_gains'])
    assert baseline.trace['first_decoder_ready'] == baseline.timing['events'][0]['ready']
    assert len(baseline.trace['checkpoints']) == 2
    assert baseline.trace['refits'][0]['evaluations'] == 3
    assert native.pilot_front is front and native.time_refine is refine
    forty = run_more_work(obs, system, None, native, arm='J40R2')
    three = run_more_work(obs, system, None, native, arm='J20R3')
    assert forty.decoder['incoming_llr'][0] == 39
    assert len(three.trace['checkpoints']) == 3
    with pytest.raises(ValueError):
        run_more_work(obs, system, None, native, arm='unknown')


def test_hooks_restore_after_failure_and_keep_completed_checkpoint():
    obs, system, _ = fixture()
    native = fake_native(system, fail_round=1)
    front, refine = native.pilot_front, native.time_refine
    trace = {}
    with pytest.raises(FloatingPointError):
        run_instrumented_baseline(obs, system, None, native, trace=trace)
    assert native.pilot_front is front and native.time_refine is refine
    assert len(trace['checkpoints']) == 1
    assert trace['complete_seconds'] > 0
    assert trace['first_decoder_ready'] is not None


def test_true_geometry_keeps_multiplicity_and_estimates_observed_gains():
    obs, system, truth = fixture()
    native = fake_native(system)
    result = run_true_geometry(obs, system, None, native,
                               delays=truth.delays, dopplers=truth.dopplers)
    assert result.trace['initial_state']['delays'].tolist() == [1, 1]
    initial = result.trace['initial_override']
    assert initial['kind'] == 'observed_initial_gain_fit'
    assert initial['evaluations'] == 1
    assert initial['gain_fit_seconds'] > 0
    assert initial['seconds'] >= initial['gain_fit_seconds']
    assert result.trace['acquisition_seconds'] is not None
    assert initial['acquired_path_count'] == 2
    assert initial['geometry_path_count'] == 2
    assert initial['geometry_distinct_delay_count'] == 1
    assert initial['ridge_penalty'] == 'noise*I'
    assert initial['scalar_joint_gain_prior'] == 'CN(0,I/P)'
    assert initial['scalar_joint_prior_variance'] == .5
    assert result.trace['refits'][0]['selected_delays'].tolist() == [1, 1]
    assert result.trace['refits'][0]['evaluations'] == 1
    assert result.trace['refits'][0]['bounds'].shape == (2, 2)
    expected, detail = _fixed_geometry_ridge(
        obs['y'], obs['pilot'], np.zeros(8, complex), np.full(8, .5),
        truth.delays, truth.dopplers, system.c1, system.c2, obs['sigma2'])
    np.testing.assert_allclose(result.arrays['r0_gains'], expected.gains)
    assert detail['evaluations'] == 1
    assert not np.array_equal(expected.gains, truth.gains)
    with pytest.raises(ValueError):
        run_true_geometry(obs, system, None, native, delays=[1.2], dopplers=[0.])


def test_fixed_tf_uses_supplied_channel_without_refit():
    obs, system, channel = fixture()
    native = fake_native(system)
    result = run_fixed_channel(obs, system, None, native, channel=channel)
    assert len(result.trace['refits']) == 2
    assert all(record['evaluations'] == 0 for record in result.trace['refits'])
    assert all(record['bounds'] is None for record in result.trace['refits'])
    assert all(record['kind'] == 'fixed_channel_pass_through'
               for record in result.trace['refits'])
    assert result.trace['initial_override']['evaluations'] == 0
    assert result.trace['channel_fit_evaluations'] == 0
    assert result.trace['channel_adaptation'] is False
    assert result.trace['gain_mode'] == 'fixed'
    assert result.timing['channel_fit_evaluations'] == 0
    assert result.timing['channel_adaptation'] is False
    np.testing.assert_array_equal(result.arrays['r1_gains'], channel.gains)
    assert result.trace['initial_state']['delays'].tolist() == [1, 1]
    with pytest.raises(ValueError):
        run_fixed_channel(dict(obs, true_bits=np.zeros(16)), system, None,
                          native, channel=channel)


def test_fixed_ep_cancels_same_channel_and_carries_decoder_prior():
    obs, system, channel = fixture()
    native = fake_native(system)
    calls = []

    def ep(ydata, c, noise, pd, prior, iterations):
        np.testing.assert_allclose(ydata, obs['y']-channel.apply(obs['pilot']))
        assert c is channel and noise == obs['sigma2']
        assert pd == .5 and iterations == 8
        calls.append(prior.copy())
        return dict(extrinsic=np.ones(16), mu=np.zeros(8, complex),
                    variance=np.full(8, .5), trace=[{'iteration': 0}])

    result = run_fixed_channel(obs, system, None, native, channel=channel,
                               detector='ep', ep_detector=ep)
    assert len(calls) == 2
    np.testing.assert_array_equal(calls[1], np.ones(16))
    assert result.trace['first_decoder_ready'] == result.timing['events'][0]['ready']
    assert result.timing['events'][0]['ce_evaluations'] == 0
    assert len(result.trace['checkpoints']) == 2
