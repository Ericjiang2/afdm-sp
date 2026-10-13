"""Default-off observed-only adapter for the frozen single-pass pair detector."""
import time

import numpy as np


def _native():
    import native_twofft
    return native_twofft


def _candidate():
    from experiments.afdm_structured_inference_20261003 import gaussian_pair
    return gaussian_pair


def receive(observation, system, code, *, enabled=False, rounds=2,
            iterations=20, block_size=2):
    if type(enabled) is not bool:
        raise TypeError('enabled must be an explicit boolean')
    if set(observation) != {'y', 'pilot', 'sigma2'}:
        raise ValueError('only y, pilot and sigma2 are accepted')
    if system.N_total != 1024 or system.rho != .5:
        raise ValueError('frozen N1024 rho0.5 interface')
    for key in ('y', 'pilot'):
        value = np.asarray(observation[key])
        if value.shape != (1024,) or not np.isfinite(value).all():
            raise ValueError('finite DAFT-domain observation vectors required')
    noise = observation['sigma2']
    if (not np.isscalar(noise) or np.iscomplexobj(noise)
            or not np.isfinite(noise) or noise <= 0):
        raise ValueError('finite positive real noise variance required')
    if type(rounds) is not int or rounds < 1 or type(iterations) is not int or iterations < 1:
        raise ValueError('positive integer schedule required')
    native = _native()
    if not enabled:
        # No candidate import, transformation, copy or output reconstruction.
        return native.receive(observation, system, code, rounds=rounds, iterations=iterations)
    if rounds != 1 or iterations != 20:
        raise ValueError('candidate supports only the frozen one-pass schedule')
    if type(block_size) is not int or block_size not in (1, 2):
        raise ValueError('candidate block size must be one or two')
    candidate = _candidate()
    started = time.perf_counter()
    state = native.pilot_front(observation, system, code)
    pilot_seconds = time.perf_counter() - started
    t = time.perf_counter()
    channel, detail = native.time_refine(
        observation['y'], observation['pilot'], state['mu'], state['v'],
        state['delays'], state['dopplers'], state['gains'], system.c1, system.c2,
        noise, mode='soft', max_paths=8, rounds=2)
    ce_seconds = time.perf_counter() - t
    t = time.perf_counter()
    model = candidate.CollapsedModel(channel, np.zeros(channel.p),
                                     np.eye(channel.p) / channel.p, noise)
    detector = candidate.gaussian_pair_pass(
        model, observation['y'], observation['pilot'], np.zeros(2048),
        block_size=block_size, external_variance=.5)
    inference_seconds = time.perf_counter() - t
    t = time.perf_counter()
    decoder = native.decoder_messages(code, np.clip(detector['extrinsic'], -20, 20), maxiter=50)
    decoder_seconds = time.perf_counter() - t
    arrays = dict(r0_decoded=decoder['decoded'], r0_input_llr=decoder['incoming_llr'],
                  r0_app=decoder['raw_app'], r0_check=decoder['raw_check_extrinsic'],
                  r0_detector_app=detector['app'], r0_detector_extrinsic=detector['extrinsic'],
                  r0_delays=channel.delays, r0_dopplers=channel.dopplers,
                  r0_ce_gains=channel.gains, r0_ce_history=np.array(detail['history']),
                  r0_ce_gamma=detail['gamma'])
    event = dict(round=0, ce=ce_seconds, inference=inference_seconds, decoder=decoder_seconds,
                 ce_evaluations=detail['evaluations'], ce_fft_count=detail['fft_count'],
                 inference_fft_count=detector['fft_count'], blocks=detector['blocks'],
                 likelihood_evaluations=detector['likelihood_evaluations'],
                 decoder_iterations=int(decoder['iterations']))
    return decoder, arrays, dict(seconds=time.perf_counter()-started, pilot_seconds=pilot_seconds,
                                events=[event], schedule='single pass, no feedback',
                                gain_output='CE geometry initialization only; no gain posterior')
