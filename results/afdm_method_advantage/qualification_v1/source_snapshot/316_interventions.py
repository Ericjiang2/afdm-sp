"""Scoped, single-process receiver interventions for the TF production-gap audit.

The native receiver is deliberately left untouched.  A scoped replacement of its
module-level hooks is safe only while no other receiver uses that module.  Every
replacement delegates to the original unless the named intervention needs it.
Truth is confined to the explicitly named geometry and full-channel callers;
``run_fixed_channel`` itself accepts an already constructed Channel only.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import threading
import time

import numpy as np


_PATCH_LOCK = threading.Lock()


@dataclass
class InterventionResult:
    decoder: dict
    arrays: dict
    timing: dict
    trace: dict


def _copy_state(state):
    return {key: value.copy() if isinstance(value, np.ndarray) else value
            for key, value in state.items()}


def _new_trace(trace, arm):
    if trace is None:
        trace = {}
    if trace:
        raise ValueError("trace must be empty at receiver start")
    trace.update(arm=arm, acquisition=None, acquisition_seconds=None,
                 initial_override=None, refits=[], events=[], checkpoints=[],
                 first_decoder_ready=None, complete_seconds=None)
    return trace


def _checkpoint(trace, external_sink):
    def sink(event, decoded):
        record = dict(event)
        record['decoded'] = np.asarray(decoded).copy()
        trace['checkpoints'].append(record)
        trace['events'].append({key: value for key, value in event.items()
                                if key != 'snapshot'})
        if trace['first_decoder_ready'] is None:
            trace['first_decoder_ready'] = float(event['ready'])
        if external_sink is not None:
            external_sink(event, decoded)
    return sink


@contextmanager
def _hooks(native, *, front=None, refine=None):
    if not _PATCH_LOCK.acquire(blocking=False):
        raise RuntimeError("concurrent instrumented receiver execution is forbidden")
    old_front, old_refine = native.pilot_front, native.time_refine
    try:
        if front is not None:
            native.pilot_front = front
        if refine is not None:
            native.time_refine = refine
        yield
    finally:
        native.pilot_front, native.time_refine = old_front, old_refine
        _PATCH_LOCK.release()


def _selected_refit_input(args, kwargs):
    """Describe the frozen refit's actual nominated delays and Doppler bounds."""
    _, _, mu, variance, ls, ks, gs, *_ = args
    ls = np.asarray(ls, int)
    ks = np.asarray(ks, float)
    gs = np.asarray(gs, complex)
    cap = kwargs.get('max_paths', 8)
    unique = np.unique(ls)
    energy = np.array([np.sum(abs(gs[ls == d]) ** 2) for d in unique])
    chosen = unique[np.argsort(-energy)[:cap]]
    centers = np.array([ks[np.flatnonzero(ls == d)[np.argmax(abs(gs[ls == d]))]]
                        for d in chosen])
    bounds = np.column_stack((np.maximum(-3., centers - .75),
                              np.minimum(3., centers + .75)))
    return dict(input_delays=ls.copy(), input_dopplers=ks.copy(),
                input_gains=gs.copy(), input_mu=np.asarray(mu).copy(),
                input_variance=np.asarray(variance).copy(),
                selected_delays=chosen.copy(), centers=centers,
                bounds=bounds, mode=kwargs.get('mode', 'soft'))


def _instrumented(native, observation, system, code, *, arm, rounds,
                  iterations, gain_mode='joint', front_override=None,
                  refine_override=None, checkpoint_sink=None, trace=None,
                  record_states=False):
    trace = _new_trace(trace, arm)
    original_front, original_refine = native.pilot_front, native.time_refine
    start = time.perf_counter()

    def front(*args, **kwargs):
        begun = time.perf_counter()
        try:
            state = original_front(*args, **kwargs)
        finally:
            trace['acquisition_seconds'] = time.perf_counter() - begun
        trace['acquisition'] = _copy_state(state)
        if front_override is not None:
            begun = time.perf_counter()
            try:
                state, detail = front_override(state, *args, **kwargs)
            except BaseException as exc:
                trace['initial_override'] = dict(status='failed',
                                                 seconds=time.perf_counter()-begun,
                                                 error=repr(exc))
                raise
            trace['initial_override'] = dict(detail, status='ok',
                                             seconds=time.perf_counter()-begun)
        trace['initial_state'] = _copy_state(state)
        return state

    def refine(*args, **kwargs):
        entry = _selected_refit_input(args, kwargs)
        begun = time.perf_counter()
        try:
            channel, detail = (original_refine if refine_override is None else refine_override)(*args, **kwargs)
        except BaseException as exc:
            entry['seconds'] = time.perf_counter() - begun
            entry['status'] = 'failed'
            entry['error'] = repr(exc)
            trace['refits'].append(entry)
            raise
        entry.update(seconds=time.perf_counter() - begun, status='ok',
                     output_delays=channel.delays.copy(),
                     output_dopplers=channel.dopplers.copy(),
                     output_gains=channel.gains.copy(),
                     evaluations=int(detail['evaluations']),
                     history=np.asarray(detail['history']).copy(),
                     fft_count=int(detail['fft_count']))
        if arm == 'true_geometry':
            entry['selected_delays'] = channel.delays.copy()
            entry['centers'] = channel.dopplers.copy()
            entry['bounds'] = np.column_stack((channel.dopplers, channel.dopplers))
        elif arm == 'fixed_tf20r2':
            entry['selected_delays'] = channel.delays.copy()
            entry['centers'] = channel.dopplers.copy()
            entry['bounds'] = None
            entry['kind'] = 'fixed_channel_pass_through'
        trace['refits'].append(entry)
        return channel, detail

    try:
        with _hooks(native, front=front, refine=refine):
            decoder, arrays, timing = native.receive(
                observation, system, code, rounds=rounds, iterations=iterations,
                ce_mode='soft', gain_mode=gain_mode,
                checkpoint_sink=_checkpoint(trace, checkpoint_sink),
                record_states=record_states)
        trace['events'] = timing['events']
        trace['complete_seconds'] = float(timing['seconds'])
        if arm == 'fixed_tf20r2':
            trace['channel_fit_evaluations'] = 0
            trace['channel_adaptation'] = False
            trace['gain_mode'] = 'fixed'
            timing['channel_fit_evaluations'] = 0
            timing['channel_adaptation'] = False
        return InterventionResult(decoder, arrays, timing, trace)
    finally:
        if trace['complete_seconds'] is None:
            trace['complete_seconds'] = time.perf_counter() - start


def run_instrumented_baseline(observation, system, code, native, *,
                              checkpoint_sink=None, trace=None,
                              record_states=False):
    """Replay the unmodified J20R2 computation with passive state capture."""
    return _instrumented(native, observation, system, code, arm='baseline_replay',
                         rounds=2, iterations=20, checkpoint_sink=checkpoint_sink,
                         trace=trace, record_states=record_states)


def run_more_work(observation, system, code, native, *, arm,
                  checkpoint_sink=None, trace=None, record_states=False):
    """Run the native implementation unchanged at J40R2 or J20R3."""
    schedules = {'J40R2': (2, 40), 'J20R3': (3, 20)}
    if arm not in schedules:
        raise ValueError('arm must be J40R2 or J20R3')
    rounds, iterations = schedules[arm]
    return _instrumented(native, observation, system, code, arm=arm,
                         rounds=rounds, iterations=iterations,
                         checkpoint_sink=checkpoint_sink, trace=trace,
                         record_states=record_states)


def _geometry(delays, dopplers, n):
    ls = np.asarray(delays)
    ks = np.asarray(dopplers)
    if (ls.ndim != 1 or ks.shape != ls.shape or len(ls) == 0 or
            not np.issubdtype(ls.dtype, np.integer) or
            np.any(ls < 0) or np.any(ls >= n) or not np.isfinite(ks).all() or
            np.any(ks < -3) or np.any(ks > 3)):
        raise ValueError('invalid fixed delay/Doppler geometry')
    return ls.astype(int, copy=True), ks.astype(float, copy=True)


def _fixed_geometry_ridge(y, pilot, mu, variance, delays, dopplers,
                          c1, c2, noise):
    """Baseline soft ridge score at fixed geometry; one gain solve, no truth."""
    from physical import Channel

    n = len(y)
    ls, ks = _geometry(delays, dopplers, n)
    if (np.asarray(pilot).shape != (n,) or np.asarray(mu).shape != (n,) or
            np.asarray(variance).shape != (n,) or noise <= 0 or
            not np.isfinite(noise) or not np.isfinite(y).all() or
            not np.isfinite(pilot).all() or not np.isfinite(mu).all() or
            not np.isfinite(variance).all() or np.any(np.asarray(variance) < 0)):
        raise ValueError('invalid observed soft ridge input')
    template = Channel(n, c1, c2, ls, ks, np.zeros(len(ls), complex))
    A = template.regressors(np.asarray(pilot) + np.asarray(mu))
    gamma = template.gamma(variance)
    Q = A.conj().T @ A + gamma + noise * np.eye(len(ls))
    b = A.conj().T @ np.asarray(y)
    h = np.linalg.solve(Q, b)
    objective = float((np.vdot(y, y) - np.vdot(b, h)).real)
    if not np.isfinite(h).all() or not np.isfinite(objective):
        raise FloatingPointError('nonfinite fixed-geometry ridge solution')
    channel = Channel(n, c1, c2, ls, ks, h)
    return channel, dict(history=[objective], objective=objective, gamma=gamma,
                         evaluations=1, fft_count=len(ls) + 2)


def run_true_geometry(observation, system, code, native, *, delays,
                      dopplers, checkpoint_sink=None, trace=None,
                      record_states=False):
    """Diagnostic geometry oracle: only delays/Dopplers enter, never gains/data.

    Every round estimates gains from y, pilot and current APP soft moments.  It
    keeps all supplied path slots, including repeated delays.  Scalar-joint
    retains its original CN(0,I/P) gain prior and 20 iterations per round.
    """
    ls, ks = _geometry(delays, dopplers, len(observation['y']))

    def front(state, observed, model, _code):
        acquired_paths = len(state['delays'])
        acquired_distinct = len(np.unique(state['delays']))
        fit_started = time.perf_counter()
        c, detail = _fixed_geometry_ridge(observed['y'], observed['pilot'],
                                          state['mu'], state['v'], ls, ks,
                                          model.c1, model.c2, observed['sigma2'])
        gain_fit_seconds = time.perf_counter() - fit_started
        state.update(delays=c.delays, dopplers=c.dopplers, gains=c.gains)
        return state, dict(kind='observed_initial_gain_fit',
                           evaluations=int(detail['evaluations']),
                           gain_fit_seconds=gain_fit_seconds,
                           fft_count=int(detail['fft_count']),
                           objective=float(detail['objective']),
                           acquired_path_count=acquired_paths,
                           acquired_distinct_delay_count=acquired_distinct,
                           geometry_path_count=len(ls),
                           geometry_distinct_delay_count=len(np.unique(ls)),
                           ridge_penalty='noise*I',
                           scalar_joint_gain_prior='CN(0,I/P)',
                           scalar_joint_prior_variance=1/len(ls))

    def refine(y, pilot, mu, v, _ls, _ks, _gs, c1, c2, noise, **_kwargs):
        return _fixed_geometry_ridge(y, pilot, mu, v, ls, ks, c1, c2, noise)

    return _instrumented(native, observation, system, code, arm='true_geometry',
                         rounds=2, iterations=20, front_override=front,
                         refine_override=refine, checkpoint_sink=checkpoint_sink,
                         trace=trace, record_states=record_states)


def _validate_fixed_channel(observation, system, channel):
    if (channel.n != len(observation['y']) or channel.c1 != system.c1 or
            channel.c2 != system.c2):
        raise ValueError('fixed channel does not match observation/system')
    if set(observation) != {'y', 'pilot', 'sigma2'}:
        raise ValueError('fixed detector accepts observed inputs only')


def run_fixed_channel(observation, system, code, native, *, channel,
                      detector='tf', checkpoint_sink=None, trace=None,
                      record_states=False, ep_detector=None):
    """Decode with a supplied immutable H and observed y/pilot only.

    For ``tf`` the native fixed-gain scalar-joint path consumes this H in each
    round.  For ``ep`` each round cancels the same H*p before calling EP8.
    Neither branch refits or updates channel gains.
    """
    _validate_fixed_channel(observation, system, channel)
    if detector not in ('tf', 'ep'):
        raise ValueError('detector must be tf or ep')
    if detector == 'ep':
        return _run_fixed_ep(observation, system, code, native, channel,
                             checkpoint_sink=checkpoint_sink, trace=trace,
                             ep_detector=ep_detector)

    def front(state, _observed, _system, _code):
        state.update(delays=channel.delays.copy(),
                     dopplers=channel.dopplers.copy(), gains=channel.gains.copy())
        return state, dict(kind='fixed_channel_injection', evaluations=0,
                           channel_fit=False, channel_adaptation=False,
                           gain_mode='fixed', channel_path_count=channel.p)

    def refine(*_args, **_kwargs):
        return channel, dict(history=[], objective=None, gamma=None,
                             evaluations=0, fft_count=0)

    return _instrumented(native, observation, system, code, arm='fixed_tf20r2',
                         rounds=2, iterations=20, gain_mode='fixed',
                         front_override=front, refine_override=refine,
                         checkpoint_sink=checkpoint_sink, trace=trace,
                         record_states=record_states)


def _run_fixed_ep(observation, system, code, native, channel, *,
                  checkpoint_sink, trace, ep_detector):
    if ep_detector is None:
        from structured_ep import ep_t as ep_detector
    trace = _new_trace(trace, 'fixed_ep8r2')
    start = time.perf_counter()
    sink = _checkpoint(trace, checkpoint_sink)
    try:
        with _hooks(native):
            # The original pilot acquisition remains in the complete intervention cost.
            begun = time.perf_counter()
            state = native.pilot_front(observation, system, code)
            pilot_seconds = time.perf_counter() - begun
            trace['acquisition'] = _copy_state(state)
            state.update(delays=channel.delays.copy(),
                         dopplers=channel.dopplers.copy(), gains=channel.gains.copy())
            trace['initial_state'] = _copy_state(state)
            prior = state['prior']
            arrays, events = {}, []
            from messages import moments
            for r in range(2):
                begun = time.perf_counter()
                ydata = observation['y'] - channel.apply(observation['pilot'])
                cancellation_seconds = time.perf_counter() - begun
                begun = time.perf_counter()
                out = ep_detector(ydata, channel, observation['sigma2'], pd=1-system.rho,
                                  prior=prior, iterations=8)
                inference_seconds = time.perf_counter() - begun + cancellation_seconds
                begun = time.perf_counter()
                decoded = native.decoder_messages(code, np.clip(out['extrinsic'], -20, 20),
                                                  maxiter=50)
                decoder_seconds = time.perf_counter() - begun
                prior = np.clip(decoded['raw_check_extrinsic'], -20, 20)
                mu, variance, _ = moments(np.clip(decoded['raw_app'], -20, 20),
                                          1-system.rho)
                event = dict(round=r, ce=0., inference=inference_seconds,
                             decoder=decoder_seconds, ready=time.perf_counter()-start,
                             decoder_iterations=int(decoded['iterations']),
                             inference_iterations=8, ce_evaluations=0,
                             inference_fft_count=None, ce_fft_count=0,
                             cancellation_seconds=cancellation_seconds)
                events.append(event)
                snapshot = dict(decoded=decoded['decoded'], input_llr=decoded['incoming_llr'],
                                app=decoded['raw_app'], check=decoded['raw_check_extrinsic'],
                                delays=channel.delays, dopplers=channel.dopplers,
                                gains=channel.gains, mu=out['mu'],
                                variance=out['variance'], inference_trace=out['trace'],
                                feedback_mu=mu, feedback_variance=variance)
                arrays.update({f'r{r}_{key}': value for key, value in snapshot.items()})
                sink(dict(event, snapshot=snapshot), decoded['decoded'].copy())
        timing = dict(seconds=time.perf_counter()-start,
                      pilot_seconds=pilot_seconds, events=events)
        trace['events'] = events
        trace['complete_seconds'] = timing['seconds']
        return InterventionResult(decoded, arrays, timing, trace)
    finally:
        if trace['complete_seconds'] is None:
            trace['complete_seconds'] = time.perf_counter() - start
