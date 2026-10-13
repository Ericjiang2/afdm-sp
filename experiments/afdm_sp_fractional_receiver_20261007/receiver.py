"""Observed-only uncoded VB backends, after independently paid F1 acquisition.

receive(observation, *, c1, c2, initial_slots, mode, quadrature='fixed') accepts exactly y/pilot/
sigma2 and delays/dopplers/gains. The harness supplies slots computed from that
same observation and pays its own F1/runtime/serialization costs. The original
point/continuous modes execute 20 gain -> Doppler -> gain -> data sweeps.
The two registered local modes execute five sweeps; collapsed coordinates
refit gain analytically and recover each winner before the three data steps.
No LDPC is imported/called.

Outputs are working-model probabilities, not exact SP marginals/extrinsic LLRs.
CoreFailure.evidence preserves partial trace and costs on numerical failure.
Phase tables and incremental coordinate coefficients are cached; PathMoments
construction and direct objective rechecks are deliberately not optimized away.
"""
import time

import numpy as np
from scipy.linalg import solve_triangular as solve_triangular  # Existing observer alias.
from scipy.special import logsumexp

from experiments.afdm_sp_fractional_20261007.moments import PathMoments, real_scalar, vector
from experiments.sp_afdm_frozen_20260920.src.messages import alphabet
from .adaptive import AdaptiveIntegrator
from .continuous import (ContinuousIntegrator, CoreFailure as CoreFailure, PointOptimizer, count,
                         finite, point_factor, raise_with_evidence, rectangular_nodes)
from .data_step import DATA_POWER, DataStepper, data_moments
from .gaussian_gain import solve_gain
from .collapsed_gain import CollapsedGain
from . import local_search

SWEEPS = 20
DATA_STEPS = 3
MODES = ('vb_point', 'vb_continuous', 'vb_local_point', 'vb_collapsed_point')


def _inputs(observation, c1, c2, initial_slots, mode):
    if set(observation) != {'y', 'pilot', 'sigma2'}:
        raise ValueError('only y/pilot/sigma2 observed fields are accepted')
    if set(initial_slots) != {'delays', 'dopplers', 'gains'}:
        raise ValueError('only F1 delays/dopplers/gains are accepted')
    if mode not in MODES:
        raise ValueError('unregistered receiver mode')
    raw_y = np.asarray(observation['y'])
    if raw_y.ndim != 1 or len(raw_y) < 2:
        raise ValueError('one dimensional observation, N >= 2 required')
    n = len(raw_y)
    y, pilot = vector(raw_y, n, 'y'), vector(observation['pilot'], n, 'pilot')
    sigma2 = real_scalar(observation['sigma2'], 'sigma2', positive=True)
    c1, c2 = real_scalar(c1, 'c1'), real_scalar(c2, 'c2')
    delays = np.asarray(initial_slots['delays'])
    if (delays.ndim != 1 or not 1 <= len(delays) <= 8 or
            not np.issubdtype(delays.dtype, np.integer) or
            np.any(delays < 0) or np.any(delays > min(102, n-1))):
        raise ValueError('one to eight integer F1 delay slots within public bounds required')
    dopplers = vector(initial_slots['dopplers'], len(delays), 'initial Dopplers', real=True)
    if np.any(abs(dopplers) > 3):
        raise ValueError('initial Dopplers outside uniform working support')
    gains = vector(initial_slots['gains'], len(delays), 'initial gains')
    for i in range(len(delays)):
        for j in range(i):
            if delays[i] == delays[j] and abs(dopplers[i]-dopplers[j]) < 1e-6:
                raise ValueError('near-coincident F1 slots')
    return n, y, pilot, sigma2, c1, c2, delays.copy(), dopplers, gains


class MomentFactory:
    def __init__(self, n, c1, c2, delays, counts):
        self.n, self.c1, self.c2, self.delays = n, c1, c2, delays
        self.counts, self.work = counts, []

    def build(self, factors, mean, covariance):
        nodes, weights = rectangular_nodes(factors, self.counts)
        count(self.counts, 'path_moment_builds_started')
        op = PathMoments(self.n, self.c1, self.c2, self.delays, nodes, weights, mean, covariance)
        self.work.append(op.work_counts)
        count(self.counts, 'path_moment_builds_completed')
        count(self.counts, 'path_moment_phase_entries_completed', nodes.size*self.n)
        return op

    def snapshot(self):
        result = dict(self.counts)
        keys = dict.fromkeys(('forward_daft_vectors', 'inverse_daft_vectors', 'ordinary_fft_vectors'))
        for work in self.work:
            keys.update(dict.fromkeys(work))
        for key in keys:
            result[key] = sum(work.get(key, 0) for work in self.work)
        return result


def _source(op, pilot, log_q, counts):
    _, mean, variance = data_moments(log_q)
    count(counts, 'source_preparations')
    return op.prepare_source(pilot, mean, variance)


def gain_update(op, y, pilot, log_q, sigma2, counts):
    """Full CN(0,I/P) update; no diagonalization, projection or jitter."""
    count(counts, 'gain_updates_started')
    source = _source(op, pilot, log_q, counts)
    count(counts, 'gain_statistics_calls')
    gram, matched = op.gain_statistics(y, source)
    count(counts, 'gain_statistics_pair_terms_completed', op.p*(op.p-1)*op.n)
    return solve_gain(gram, matched, sigma2, counts)


def doppler_sweep(op, factors, y, pilot, log_q, sigma2, optimizer, counts, trace):
    """Reuse canonical coefficients and R_ji for sequential delta-phi updates."""
    source = _source(op, pilot, log_q, counts)
    count(counts, 'coordinate_coefficients_calls')
    coefficients = op.coordinate_coefficients(y, source)
    count(counts, 'coordinate_pair_terms_completed', op.p*(op.p-1)*op.n)
    phi = op.phi.copy()
    updated = list(factors)
    for i in range(op.p):
        count(counts, 'doppler_coordinates_started')
        if isinstance(optimizer, ContinuousIntegrator):
            factor = optimizer.from_coefficients(coefficients[i], sigma2)
            detail = factor.record()
        else:
            factor, detail = optimizer.update(coefficients[i], sigma2, float(factors[i].nodes[0]))
        delta = factor.phi-phi[i]
        phi[i] = factor.phi
        updated[i] = factor
        trace.append(dict(slot=i, result=detail))
        # Only later coordinates will be read again in this ordered sweep.
        for j in range(i+1, op.p):
            count(counts, 'incremental_cross_source_calls')
            cross = op._cross_source(source, j, i)
            coefficients[j] -= op.second[j, i]*cross*delta.conj()
            count(counts, 'incremental_coefficient_terms', op.n)
        finite(coefficients, 'incremental coordinate coefficients')
        count(counts, 'doppler_coordinates_completed')
    return updated


def collapsed_sweep(factory, factors, mean, covariance, y, pilot, log_q, sigma2, counts, trace):
    """Each coordinate owns fresh canonical moments; only its winner restores full C."""
    updated = list(factors)
    for i in range(len(updated)):
        count(counts, 'doppler_coordinates_started')
        op = factory.build(updated, mean, covariance)
        source = _source(op, pilot, log_q, counts)
        model = CollapsedGain(op, source, y, sigma2, counts)
        prepared = model.prepare(i)
        detail = dict(slot=i, preparation=prepared.detail, score_evaluations=[], status='started')
        trace.append(detail)

        def score(value):
            candidate = prepared.evaluate(value, score_only=True)
            detail['score_evaluations'].append(candidate)
            return candidate['J']

        selected, search = local_search.maximize(score, float(updated[i].nodes[0]), counts)
        detail['search'] = search
        count(counts, 'collapsed_winner_full_evaluations_started')
        winner = prepared.evaluate(selected)
        count(counts, 'collapsed_winner_full_evaluations_completed')
        if winner['J'] != search['selected_score']:
            raise CoreFailure('full winner score differs from selected score', dict(search=search, winner=winner))
        detail.update(status='completed', winner=winner)
        updated[i] = point_factor(selected, op.n, counts)
        mean, covariance = winner['mean'], winner['covariance']
        count(counts, 'doppler_coordinates_completed')
    return updated, mean, covariance


def receive(observation, *, c1, c2, initial_slots, mode, quadrature='fixed'):
    start = time.perf_counter()
    counts = dict(decoder_calls=0)
    trace, initial_factors, factory = [], [], None
    try:
        n, y, pilot, sigma2, c1, c2, delays, dopplers, mean = _inputs(
            observation, c1, c2, initial_slots, mode)
        if quadrature not in ('fixed', 'adaptive') or (mode != 'vb_continuous' and quadrature != 'fixed'):
            raise ValueError('quadrature must be fixed, or adaptive in continuous mode')
        factory = MomentFactory(n, c1, c2, delays, counts)
        covariance = np.eye(len(delays), dtype=complex)/len(delays)
        log_q = np.full((n, 4), -np.log(4.))
        if mode == 'vb_continuous':
            optimizer = AdaptiveIntegrator(n, counts) if quadrature == 'adaptive' else ContinuousIntegrator(n, counts)
            factors = []
            for center in dopplers:
                factors.append(optimizer.initial(float(center)))
                initial_factors.append(factors[-1].record())
        else:
            optimizer = (local_search.LocalPointOptimizer(n, counts) if mode == 'vb_local_point'
                         else None if mode == 'vb_collapsed_point' else PointOptimizer(n, counts))
            factors = [point_factor(float(center), n, counts) for center in dopplers]
            initial_factors = [factor.record() for factor in factors]
        sweeps = local_search.SWEEPS if mode in ('vb_local_point', 'vb_collapsed_point') else SWEEPS
        for sweep in range(sweeps):
            sweep_start = time.perf_counter()
            event = dict(sweep=sweep, doppler=[], data=[])
            trace.append(event)
            if mode == 'vb_collapsed_point':
                factors, mean, covariance = collapsed_sweep(
                    factory, factors, mean, covariance, y, pilot, log_q, sigma2, counts, event['doppler'])
            else:
                op = factory.build(factors, mean, covariance)
                mean, covariance, event['gain_before_doppler'] = gain_update(
                    op, y, pilot, log_q, sigma2, counts)
                op = factory.build(factors, mean, covariance)
                factors = doppler_sweep(op, factors, y, pilot, log_q, sigma2,
                                        optimizer, counts, event['doppler'])
                op = factory.build(factors, mean, covariance)
                mean, covariance, event['gain_after_doppler'] = gain_update(
                    op, y, pilot, log_q, sigma2, counts)
            op = factory.build(factors, mean, covariance)
            stepper = DataStepper(op, y, pilot, sigma2, log_q, counts)
            for _ in range(DATA_STEPS):
                log_q, detail = stepper.step()
                event['data'].append(detail)
            count(counts, 'sweeps_completed')
            event.update(log_q=log_q.copy(), counts=factory.snapshot(),
                         seconds=time.perf_counter()-sweep_start)
        probabilities, data_mean, data_variance = data_moments(log_q)
        _, bits = alphabet(DATA_POWER)
        count(counts, 'bit_marginal_logsumexp_rows', 4*n)
        bit_llr = np.concatenate([
            logsumexp(log_q[:, bits[:, j] == 0], axis=1)-
            logsumexp(log_q[:, bits[:, j] == 1], axis=1) for j in (0, 1)])
        finite(bit_llr, 'uncoded working-model bit LLR')
        count(counts, 'probability_export_entries', probabilities.size)
        result = dict(mode=mode, log_q=log_q, probabilities=probabilities,
                      bit_llr=bit_llr, hard_bits=(bit_llr < 0).astype(np.uint8),
                      data_mean=data_mean, data_variance=data_variance,
                      gain_mean=mean, gain_covariance=covariance, delays=delays,
                      doppler_factors=[factor.record() for factor in factors],
                      initial_doppler_factors=initial_factors, trace=trace,
                      exponentiation_zeros=int(np.count_nonzero(probabilities == 0)),
                      counts=factory.snapshot(), sweeps=sweeps, data_steps_per_sweep=DATA_STEPS,
                      scope='backend_after_F1; add F1/setup/serialization cost in harness',
                      llr_semantics='working QPSK bit marginals; all-I then all-Q; positive means zero',
                      decoder_calls=0)
        if quadrature == 'adaptive':
            result.update(quadrature=quadrature, adaptive_rule_validation=optimizer.rule_validation)
        result['seconds'] = time.perf_counter()-start
        return result
    except Exception as error:
        evidence = dict(mode=mode, quadrature=quadrature, trace=trace, initial_doppler_factors=initial_factors,
                        counts=dict(counts) if factory is None else factory.snapshot(),
                        seconds=time.perf_counter()-start,
                        cause_type=type(error).__name__, cause_message=str(error))
        raise_with_evidence(error, 'receiver core failed: ', evidence)
