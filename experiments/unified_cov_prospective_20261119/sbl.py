"""E-3c with the qualified spectral-split controls and U2 Doppler refinement."""
from hashlib import sha256
from pathlib import Path
import sys
import time
from types import FunctionType, SimpleNamespace

import numpy as np

EXPERIMENTS = Path(__file__).resolve().parents[1]
SPECTRAL = EXPERIMENTS / 'sbl_spectral_split_20261119'
sys.path.insert(0, str(SPECTRAL))
import main_receiver as frozen_main

from projector import low_projector

spectral = frozen_main.phase1
e3c, ref = spectral.e3c, spectral.ref
GATE_ARMS = ('R0', 'R1', 'S-lo', 'S-hi', 'S-isolo')
ARMS = (*GATE_ARMS, 'U2')


def _verify_source(actual, relative, expected):
    actual = Path(actual).resolve()
    if actual != (EXPERIMENTS / relative).resolve() or sha256(actual.read_bytes()).hexdigest() != expected:
        raise RuntimeError(f'Frozen SBL source differs: {actual}')


_verify_source(frozen_main.__file__, 'sbl_spectral_split_20261119/main_receiver.py',
               '13a4222f7112a172e740a7c24c2b9f48e4f2cac505d26b7a3cf26d688ce025a8')
_verify_source(ref.__file__, 'tf_e3b_offgrid_20261017/offgrid_refine.py',
               '419f0a56fc90bd41377e907cec963bb23c5556ea1ae48af039cb38fa808ff7e4')
_verify_source(ref._system.__code__.co_filename, 'tf_cstate_e1_20261017/geometry_reopen_variant.py',
               '0e75438bdf33f1ec730c6111871b921b64cca1dee5811799474b47da18d0abb8')


def _refine_u2(Y, xt, v, delays, dopplers, c1, c2, ridge, force_empty):
    # Source: E-3b offgrid_refine.refine, with a pass-start frozen covariance and pass-local score reset because the source has no pass or system hook.
    centers = [float(nu) for nu in dopplers]
    nus = centers.copy()
    paths_delays = [int(delay) for delay in delays]
    u = float(np.sum(v))
    ranks, values_before, values_after, accepted_by_pass = [], [], [], []
    evals_total = max_evals_coord = 0
    apply_projector = not force_empty and u > 0

    system_source = ref._system
    full_covariance = system_source.__globals__['projected_variance']

    def covariance(variances, ls, ns, chirp):
        gamma = full_covariance(variances, ls, ns, chirp)
        return gamma + penalty if rank else gamma

    # Bind only the covariance call in a private namespace. The E-1 solve,
    # response construction and numerical checks follow the exact frozen route.
    bound_system = FunctionType(
        system_source.__code__, dict(system_source.__globals__, projected_variance=covariance),
        argdefs=system_source.__defaults__,
    )

    def system(values):
        return bound_system(Y, xt, v, [ref.Path(l, nu) for l, nu in zip(paths_delays, values)],
                            c1, c2, ridge, 'full')

    for _ in range(ref.PASSES):
        rank = 0
        if apply_projector:
            projector = low_projector(delays, nus, len(v))
            rank = int(np.rint(np.trace(projector).real))
            penalty = u * projector
        ranks.append(rank)
        value = system(nus)[4]
        values_before.append(value)
        accepted = 0
        for k, center in enumerate(centers):
            lo = max(ref.DOPPLER[0], center - ref.HALF_WIDTH)
            hi = min(ref.DOPPLER[1], center + ref.HALF_WIDTH)
            best = [value, nus[k]]
            count = 0

            def objective(nu):
                nonlocal count
                trial = list(nus)
                trial[k] = float(nu)
                score = system(trial)[4]
                count += 1
                if score < best[0]:
                    best[:] = score, float(nu)
                return score

            ref.minimize_scalar(objective, bounds=(lo, hi), method='bounded',
                                options=dict(xatol=ref.XATOL, maxiter=ref.MAX_EVALS))
            evals_total += count
            max_evals_coord = max(max_evals_coord, count)
            if best[0] < value:
                value, nus[k] = best
                accepted += 1
        fixed_pass_endpoint = system(nus)[4]
        if fixed_pass_endpoint != value or fixed_pass_endpoint > values_before[-1]:
            raise AssertionError('U2 fixed-projector refinement did not descend')
        accepted_by_pass.append(accepted)
        values_after.append(value)

    # Use the last pass's projector for the E-3b final gain evaluation.
    _, Q, _, gains, value_after, gamma = system(nus)
    offdiag = gamma - np.diag(np.diag(gamma))
    shift = np.abs(np.asarray(nus) - centers)
    final_dopplers = np.asarray(nus, dtype=float)
    result = dict(
        dopplers=final_dopplers, gains=gains,
        value_before=float(values_before[0]), value_after=float(value_after),
        monotone=bool(all(after <= before for after, before in zip(values_after, values_before))
                      and value_after <= values_after[-1]),
        value_recheck_equal=bool(value_after == value), n_coord=ref.PASSES * len(nus),
        n_accept=sum(accepted_by_pass), accepted_by_pass=accepted_by_pass,
        evals=evals_total, max_evals_coord=max_evals_coord,
        shift_abs_max=float(shift.max()), shift_abs_mean=float(shift.mean()),
        n_moved=int(np.count_nonzero(shift > 0)),
        in_bounds=bool(np.all((final_dopplers >= ref.DOPPLER[0]) & (final_dopplers <= ref.DOPPLER[1]))),
        in_window=bool(np.all(shift <= ref.HALF_WIDTH + 1e-12)),
        gamma_abs_max=float(np.max(np.abs(gamma))), gamma_offdiag_abs_max=float(np.max(np.abs(offdiag))),
        gamma_diag_rel_err=float(np.max(np.abs(np.diag(gamma).real - u)) / u) if u > 0 else None,
        cond_Q=float(np.linalg.cond(Q)),
    )
    if apply_projector:
        result.update(projector_rank_by_pass=ranks, value_before_by_pass=values_before,
                      value_after_by_pass=values_after, projector_trace_added=float(np.trace(penalty).real))
    return result


def process_key(ctx, cache, grid, key, *, include_u2=True, force_empty=False):
    """Run the six matched arms at 100 iterations, sharing the S-lo/U2 EM fit."""
    selected = ARMS if include_u2 else GATE_ARMS
    refinement_times = []

    def settings(v, sigma2, delays, dopplers, c1, smoke):
        specs, matrices, ridges, blocks, census = spectral.arm_settings(v, sigma2, delays, dopplers, c1, smoke)
        ranks = [int(np.rint(np.trace(block[2]).real)) for block in blocks]
        census = dict(census, projector_rank=sum(ranks), projector_nonempty_blocks=sum(rank > 0 for rank in ranks))
        specs['U2'] = dict(specs['R1'], mode='unified')
        matrices['U2'] = matrices['S-lo']
        ridges['U2'] = ridges['S-lo']
        return specs, matrices, ridges, blocks, census

    def fit(results, name, B, Y, beta0, gamma, max_iter):
        if name == 'U2':
            results[name] = results['S-lo']
            return results[name]
        if name == 'R1' and name in results:
            return results[name]
        return spectral.fit_sbl(results, name, B, Y, beta0, gamma, max_iter)

    def refine(Y, xt, v, delays, dopplers, c1, c2, ridge, mode):
        started = time.process_time()
        if mode == 'unified':
            result = _refine_u2(Y, xt, v, delays, dopplers, c1, c2, ridge, force_empty)
        else:
            result = ref.refine(Y, xt, v, delays, dopplers, c1, c2, ridge, mode)
        refinement_times.append(time.process_time() - started)
        return result

    # The frozen main runner hardcodes its arm/budget table and has no dispatch
    # argument. Rebind only per-call global entries and reuse its complete loop.
    run = frozen_main.process_main_key
    namespace = dict(run.__globals__, main_budgets=lambda _key: (100,),
                     MAIN_ARMS={100: selected}, arm_settings=settings, fit_sbl=fit,
                     time=SimpleNamespace(perf_counter=time.process_time),
                     REFINEMENT=dict(spectral.REFINEMENT, U2='U2'),
                     ref=type(ref)('unified_sbl_refinement'))
    namespace['ref'].refine = refine
    row = FunctionType(run.__code__, namespace)(ctx, cache, grid, key)
    budget = row.pop('budgets')['100']
    row['variants'] = budget['variants']
    # The frozen schedule precomputes R1 for T0. Reuse that R1 fit and charge
    # its measured duration to R1 rather than to shared preparation.
    r1_sbl_seconds = budget['seconds']['r1_sbl_only']
    r1_seconds = row['variants']['R1']['seconds']
    r1_seconds['sbl'] += r1_sbl_seconds
    r1_seconds['total'] += r1_sbl_seconds
    for score, seconds in zip(row['variants'].values(), refinement_times, strict=True):
        score['seconds']['refinement'] = seconds
    if include_u2:
        u2 = row['variants']['U2']
        u2['seconds']['shared_slo_sbl'] = row['variants']['S-lo']['seconds']['sbl']
        u2['seconds']['sbl'] = 0.
        u2['added_trace_refinement'] = u2['refine'].get('projector_trace_added', 0.)
    return row
