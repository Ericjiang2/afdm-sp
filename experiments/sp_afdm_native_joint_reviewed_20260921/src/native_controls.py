"""Thin observed-only EP/PBi controls with the same frozen time-domain refit.

This lifts the already qualified fair-control loop out of a historical screen;
it does not change the comparator inference or CE settings.
"""
import time
import numpy as np

from receiver import pilot_front, decoder_messages
from messages import moments
from structured_ep import ep_t
from bilinear import pbigabp
from twofft import time_refine


def receive_control(observation, system, code, *, kind, iterations, ce_mode,
                    checkpoint_sink=None):
    if kind not in ('ep', 'pbi') or iterations not in (2, 4, 8):
        raise ValueError('unregistered native control')
    if (kind == 'pbi') != (iterations == 8):
        raise ValueError('native control iteration budget differs')
    if ce_mode not in ('soft', 'mean') or (kind == 'pbi' and ce_mode != 'soft'):
        raise ValueError('native control CE mode differs')
    if set(observation) - {'y', 'pilot', 'sigma2'}:
        raise ValueError('native controls accept observed input only')
    if checkpoint_sink is not None and not callable(checkpoint_sink):
        raise TypeError('checkpoint sink must be callable')
    started = time.perf_counter()
    state = pilot_front(observation, system, code)
    pilot_seconds = time.perf_counter() - started
    arrays, events = {}, []
    for round_index in range(2):
        began = time.perf_counter()
        channel, detail = time_refine(
            observation['y'], observation['pilot'], state['mu'], state['v'],
            state['delays'], state['dopplers'], state['gains'], system.c1,
            system.c2, observation['sigma2'], mode=ce_mode, max_paths=8, rounds=2)
        ce_seconds = time.perf_counter() - began
        began = time.perf_counter()
        if kind == 'ep':
            inferred = ep_t(observation['y'] - channel.apply(observation['pilot']),
                            channel, observation['sigma2'], prior=state['prior'],
                            iterations=iterations)
        else:
            inferred = pbigabp(observation['y'], observation['pilot'], channel,
                               observation['sigma2'], prior=state['prior'],
                               iterations=iterations)
        inference_seconds = time.perf_counter() - began
        began = time.perf_counter()
        decoded = decoder_messages(code, np.clip(inferred['extrinsic'], -20, 20),
                                   maxiter=50)
        decoder_seconds = time.perf_counter() - began
        state['mu'], state['v'], _ = moments(np.clip(decoded['raw_app'], -20, 20),
                                            1 - system.rho)
        state['prior'] = np.clip(decoded['raw_check_extrinsic'], -20, 20)
        state['delays'], state['dopplers'] = channel.delays, channel.dopplers
        state['gains'] = inferred.get('gains', channel.gains)
        event = dict(round=round_index, ce=ce_seconds, inference=inference_seconds,
                     decoder=decoder_seconds, ready=time.perf_counter() - started,
                     decoder_iterations=int(decoded['iterations']),
                     inference_iterations=iterations,
                     ce_evaluations=detail['evaluations'],
                     ce_fft_count=detail['fft_count'])
        events.append(event)
        snapshot = dict(decoded=decoded['decoded'],
                        input_llr=decoded['incoming_llr'], app=decoded['raw_app'],
                        check=decoded['raw_check_extrinsic'], delays=channel.delays,
                        dopplers=channel.dopplers, gains=state['gains'],
                        ce_gains=channel.gains, ce_history=np.asarray(detail['history']),
                        ce_gamma=detail['gamma'], mu=inferred['mu'],
                        variance=inferred['variance'],
                        inference_trace=inferred.get('trace', []))
        if 'gain_variance' in inferred:
            snapshot['gain_variance'] = inferred['gain_variance']
        arrays.update({f'r{round_index}_{key}': value for key, value in snapshot.items()})
        if checkpoint_sink is not None:
            checkpoint_sink(dict(event, snapshot=snapshot), decoded['decoded'].copy())
    return decoded, arrays, dict(seconds=time.perf_counter() - started,
                                 pilot_seconds=pilot_seconds, events=events)
