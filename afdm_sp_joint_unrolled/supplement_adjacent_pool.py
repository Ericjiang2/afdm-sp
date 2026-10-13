"""Observed-only bounded geometry pools and single-use coded likelihood scores."""
from __future__ import annotations

import hashlib
import json
import time

import numpy as np

from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix, omp_sparse
from afdm_sp_joint_unrolled.afdm_env import AFDMEnvMixin
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash, physical_cluster_weights
from afdm_sp_joint_unrolled.direction_data import validate_observed
from afdm_sp_joint_unrolled.direction_physical import _centers
from afdm_sp_joint_unrolled.direction_structure import _fit_ls
from afdm_sp_joint_unrolled.e1_ldpc import encode, qpsk_map

ROLES = ('hard', 'multistart-1', 'multistart-2', 'candidate-1', 'candidate-2')
POOLS = {'proposed': ('hard', 'candidate-1', 'candidate-2'),
         'multistart': ('hard', 'multistart-1', 'multistart-2')}
OFFSETS = np.array([-.25, 0., .25])


class PoolSearchError(ValueError):
    """A failed observed query, including every attempted query up to failure."""
    def __init__(self, message, query_trace):
        super().__init__(message)
        self.query_trace = query_trace


def candidate_signature(delays, locations, weights):
    hashes = dict(delays=array_hash(np.asarray(delays)), locations=array_hash(np.asarray(locations)),
                  weights=array_hash(np.asarray(weights)))
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def search_pools(y, dictionary, geometry, centers):
    """One base sweep and four equally bounded branch sweeps on observations."""
    y, dictionary = np.asarray(y, complex), np.asarray(dictionary, complex)
    if (y.ndim != 1 or dictionary.shape != (len(y), 515) or not 1 <= len(centers) <= 8
            or not np.isfinite(dictionary).all() or not np.isfinite(y).all()):
        raise ValueError('invalid observed dictionary or estimated center set')
    delays = np.array([int(row[1]) for row in centers], dtype=np.int64)
    base = np.array([float(row[2]) for row in centers])
    if np.any(delays < 0) or np.any(delays > 102) or np.any(np.abs(base) > 2):
        raise ValueError('estimated geometry outside dictionary domain')
    lower, upper = np.maximum(base-.5, -2.), np.minimum(base+.5, 2.)
    trace, stage_times = [], {}

    def sweep(seed, stage):
        started = time.perf_counter()
        tried = []

        def evaluate(locations):
            if len(tried) >= 25 or len(trace) >= 125:
                raise ValueError('registered geometry query cap exceeded')
            record = dict(query=len(trace)+1, stage=stage, locations=locations.tolist(), status='started')
            trace.append(record)
            try:
                weights = physical_cluster_weights(geometry,
                    dict(taps=len(delays), l_i=delays, k_real=locations))
                active = np.flatnonzero(np.any(weights != 0, axis=1))
                if not len(active) or len(active) > 40:
                    raise ValueError('invalid physical template support')
                design = dictionary[:, active] @ weights[active]
                if not np.isfinite(design).all() or not np.any(design):
                    raise ValueError('all-zero or nonfinite observed physical basis')
                latent, details = _fit_ls(design, y)
                coefficients = weights @ latent
                objective = float(np.linalg.norm(y-design@latent)**2)
                if not np.isfinite(objective) or not np.isfinite(coefficients).all():
                    raise FloatingPointError('nonfinite bounded physical fit')
                candidate = dict(delays=delays.copy(), locations=locations.copy(), weights=weights,
                    pilot_coefficients=coefficients, pilot_residual_squared=objective,
                    pilot_rank=details['rank'], signature=candidate_signature(delays, locations, weights))
            except Exception as error:
                record.update(status='failed', error=type(error).__name__+': '+str(error))
                raise PoolSearchError(str(error), trace) from error
            tried.append(candidate)
            record.update(status='complete', residual_squared=objective, rank=details['rank'],
                singular_values=details['singular_values'], signature=candidate['signature'])
            return candidate

        current = evaluate(np.clip(np.asarray(seed, float), lower, upper))
        for coordinate in range(len(base)):
            anchor = current['locations'].copy()
            best = current
            for value in np.unique(np.clip(anchor[coordinate]+OFFSETS, lower[coordinate], upper[coordinate])):
                trial = anchor.copy()
                trial[coordinate] = value
                fitted = evaluate(trial)
                if fitted['pilot_residual_squared'] < best['pilot_residual_squared']:
                    best = fitted
            current = best
        stage_times[stage] = time.perf_counter()-started
        return current, tried

    hard, base_trials = sweep(base, 'hard')
    alternatives = []
    seen = {hard['signature']}
    for candidate in sorted(base_trials, key=lambda item: item['pilot_residual_squared']):
        if candidate['signature'] not in seen:
            alternatives.append(candidate)
            seen.add(candidate['signature'])
    candidates = {'hard': hard}
    duplicate_seeds = []
    for number in (1,2):
        if number <= len(alternatives):
            seed = alternatives[number-1]['locations']
        else:
            seed = hard['locations']
            duplicate_seeds.append(f'candidate-{number}')
        candidates[f'candidate-{number}'], _ = sweep(seed, f'candidate-{number}')
    for number, offset in ((1, -.25), (2, .25)):
        candidates[f'multistart-{number}'], _ = sweep(np.clip(base+offset, lower, upper), f'multistart-{number}')
    counts = {role: sum(row['stage'] == role for row in trace) for role in ROLES}
    for roles in POOLS.values():
        if sum(counts[role] for role in roles) > 75:
            raise ValueError('strategy query budget exceeded')
    return dict(candidates=candidates, query_trace=trace, query_counts=counts,
        stage_seconds=stage_times, duplicate_alternative_seeds=duplicate_seeds,
        distinct_hypotheses={name:len({candidates[role]['signature'] for role in roles}) for name,roles in POOLS.items()},
        geometry_scope='observed center delays; bounded Doppler templates; not a complete posterior mode catalogue')


def nominate(observed, geometry):
    """Public entry: no frame object, truth, support labels or decoder outcomes."""
    y, pilot, sigma, const = validate_observed(observed, 1024)
    started = time.perf_counter()
    dictionary = construct_sensing_matrix(1024, pilot, geometry.c1, geometry.c2, 102, 2)
    coefficients, support = omp_sparse(y, dictionary, 24)
    if len(support) != len(set(support)) or not support:
        raise ValueError('observed OMP produced an invalid support')
    ids = np.asarray(support, dtype=np.int64)
    centers = _centers(ids, coefficients[ids], 5, 2)
    common_seconds = time.perf_counter()-started
    pools = search_pools(y, dictionary, geometry, centers)
    pools.update(observed_hashes={key:array_hash(np.asarray(value)) for key,value in observed.items()},
        dictionary_sha256=array_hash(dictionary), omp_support=support,
        omp_coefficients_sha256=array_hash(coefficients), centers=centers,
        common_nomination_seconds=common_seconds, total_nomination_seconds=time.perf_counter()-started,
        strategy_nomination_seconds={name:common_seconds+sum(pools['stage_seconds'][role] for role in roles)
            for name,roles in POOLS.items()}, truth_access='none', F=0)
    return pools


class FixedGeometryRefit:
    """Commit one complete physical model on the actual active I1 dictionary."""
    def __init__(self, geometry, candidate):
        weights = np.asarray(candidate['weights'])
        delays, locations = np.asarray(candidate['delays']), np.asarray(candidate['locations'])
        if (delays.ndim != 1 or not 1 <= len(delays) <= 8 or locations.shape != delays.shape
                or weights.shape != (515, len(delays)) or not np.isfinite(weights).all()
                or candidate_signature(delays, locations, weights) != candidate['signature']):
            raise ValueError('invalid or mutated fixed geometry candidate')
        self.geometry, self.candidate = geometry, candidate

    def __call__(self, *, y, pilot, H, x_soft, support, gains, sigma_base):
        geometry = self.geometry
        ids = np.asarray(support)
        if (ids.ndim != 1 or ids.dtype.kind not in 'iu' or len(ids) > 40
                or len(ids) != len(set(ids.tolist())) or np.any(ids < 0)
                or np.any(ids >= 515) or not np.isfinite(sigma_base) or sigma_base <= 0):
            raise ValueError('invalid observed terminal support or variance')
        ids = ids.astype(np.int64)
        weights = self.candidate['weights'][ids]
        dictionary = construct_sensing_matrix(1024, np.asarray(pilot)+np.asarray(x_soft),
            geometry.c1, geometry.c2, 102, 2)[:, ids]
        design = dictionary @ weights
        if not np.isfinite(design).all() or not np.any(design):
            raise ValueError('fixed candidate has an all-zero or nonfinite active basis')
        latent, details = _fit_ls(design, np.asarray(y))
        fitted = weights @ latent
        channel = AFDMEnvMixin.gen_h_daft(geometry, fitted, ids//5, ids%5-2)
        if not np.isfinite(fitted).all() or not np.isfinite(channel).all():
            raise FloatingPointError('nonfinite physical terminal refit')
        return dict(H=channel, gains=fitted, diagnostics=dict(
            candidate_signature=self.candidate['signature'],
            delays=self.candidate['delays'], locations=self.candidate['locations'],
            weights_on_active_support=weights, active_support=ids,
            fitted_latent=latent, residual_squared=float(np.linalg.norm(np.asarray(y)-design@latent)**2),
            rank=details['rank'], singular_values=details['singular_values'],
            rank_threshold=details['rank_threshold'], latent_slots=weights.shape[1],
            zero_slots=int(np.count_nonzero(~np.any(weights != 0, axis=0))),
            truth_access='none', input_model='pilot+x_soft, already power-scaled',
            variance_policy='unchanged I1 terminal scale',
            geometry_scope='fixed physical template restricted to I1 active dictionary; not globally complete geometry'))


def codeword_score(observed, channel, info_hat, code):
    """One observed likelihood at a legal codeword; no posterior multiplication."""
    y, pilot, sigma, const = validate_observed(observed)
    channel, info = np.asarray(channel), np.asarray(info_hat)
    if (channel.shape != (len(y),len(y)) or code['n'] != 2*len(y)
            or info.shape != (code['k'],) or np.any((info != 0) & (info != 1))
            or not np.isfinite(channel).all()
            or not np.allclose(const, np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))):
        raise ValueError('invalid coded likelihood input or data power')
    word = encode(code, info)
    symbols = qpsk_map(word, scale=np.sqrt(.5))
    residual = y-channel@(pilot+symbols)
    nll = float(np.vdot(residual,residual).real/sigma)
    if not np.isfinite(nll):
        raise FloatingPointError('nonfinite coded likelihood')
    return dict(nll=nll, codeword=word, symbols=symbols,
        codeword_sha256=array_hash(word), observed_residual_sha256=array_hash(residual),
        sigma2=sigma, likelihood_evaluations=1,
        kind='plug-in legal-codeword likelihood; not integrated model evidence or posterior probability')
