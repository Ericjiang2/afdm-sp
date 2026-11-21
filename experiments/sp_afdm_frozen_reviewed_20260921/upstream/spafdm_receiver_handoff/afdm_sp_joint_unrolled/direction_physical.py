"""Frozen observed-only physical refits; no simulator truth or terminal decode.

The system supplies geometry constants and Dirichlet weights only. Returned
coefficients remain aligned to the supplied support, including zero entries.
"""
from __future__ import annotations
import numpy as np
from afdm_sp_joint_unrolled.direction_structure import fit, _ids, _fit_ls, _svd
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import physical_cluster_weights

ARMS = ('m-group', 'm-param-budget', 'm-param-reference', 'm-soft')
GRID = np.arange(-4, 5, dtype=float)/8
SOFT_LAMBDAS = (0., .001, .01, .1, 1.)


def resolve_soft_lambda(arm, value):
    if value is None:
        return .01 if arm == 'm-soft' else None
    if (arm != 'm-soft' or isinstance(value, (bool, np.bool_)) or
            not isinstance(value, (int, float, np.integer, np.floating)) or
            not np.isfinite(value) or float(value) not in SOFT_LAMBDAS):
        raise ValueError('normalized soft lambda must be a frozen m-soft value')
    return float(value)


def _centers(ids, gains, width, kmax):
    selected = []
    # Sorting magnitude is equivalent to squared magnitude, without overflow.
    for index in np.lexsort((ids, -np.abs(gains))):
        atom = int(ids[index])
        delay, doppler = atom//width, atom % width-kmax
        if any(delay == d and abs(doppler-k) <= 1 for _, d, k in selected):
            continue
        selected.append((atom, delay, doppler))
        if len(selected) == 8:
            break
    return selected


def _search(system, y, A, ids, centers, reference):
    delays = np.array([d for _, d, _ in centers], dtype=int)
    base = np.array([k for _, _, k in centers], dtype=float)
    lower, upper = np.maximum(base-.5, -2), np.minimum(base+.5, 2)
    limit = 3243 if reference else 73
    queries = []
    runs = []

    def evaluate(locations):
        if len(queries) >= limit:
            raise RuntimeError(f'physical query cap exhausted: {limit}; trace={queries}')
        attempt=dict(query=len(queries)+1, locations=locations.tolist(), status='started')
        queries.append(attempt)
        try:
            W = physical_cluster_weights(system, dict(taps=len(base), l_i=delays, k_real=locations))[ids]
            if not np.isfinite(W).all():
                raise FloatingPointError('nonfinite physical template')
            latent, details = _fit_ls(A@W, y)
            coefficients = W@latent
            objective = float(np.linalg.norm(y-A@coefficients)**2)
            if not np.isfinite(objective) or not np.isfinite(coefficients).all():
                raise FloatingPointError('nonfinite physical fit')
        except Exception as exc:
            attempt.update(status='failed', error=repr(exc))
            raise RuntimeError(f'physical query failed; attempted trace={queries}') from exc
        attempt.update(status='complete', residual_squared=objective, **details)
        return dict(locations=locations.copy(), coefficients=coefficients, basis=W,
                    objective=objective, details=details, query=len(queries))

    best_run = None
    for offset in ((0., -.25, .25) if reference else (0.,)):
        current = evaluate(np.clip(base+offset, lower, upper))
        sweeps = []
        stationary = False
        for sweep in range(15 if reference else 1):
            changed = False
            coordinates = []
            for j in range(len(base)):
                before = current
                best = current
                for value in np.unique(np.clip(base[j]+GRID, lower[j], upper[j])):
                    proposal = before['locations'].copy()
                    proposal[j] = value
                    trial = evaluate(proposal)
                    if trial['objective'] < best['objective']:
                        best = trial
                accepted = not np.array_equal(best['locations'], before['locations'])
                changed |= accepted
                current = best
                coordinates.append(dict(center=j, accepted=bool(accepted), before=before['objective'],
                                        after=current['objective'], selected_query=current['query']))
            sweeps.append(dict(sweep=sweep+1, coordinates=coordinates))
            if not changed:
                stationary = True
                break
        runs.append(dict(initial_offset=offset, sweeps=sweeps, stationary=stationary,
                         stop_reason='grid-coordinate-stationary' if stationary else 'sweep-cap',
                         residual_squared=current['objective'], selected_query=current['query']))
        if best_run is None or current['objective'] < best_run['objective']:
            best_run = current
    diagnostics = dict(query_count=len(queries), query_limit=limit, query_trace=queries,
                       initializations=runs, iterations=sum(len(r['sweeps']) for r in runs),
                       converged=all(r['stationary'] for r in runs),
                       convergence_scope='registered finite-grid coordinate stationarity only',
                       selected_query=best_run['query'], locations=best_run['locations'].tolist(),
                       reference_unconverged=bool(reference and not all(r['stationary'] for r in runs)))
    return best_run, diagnostics


def fit_physical_observed(system, y, A, support, gains, sigma_terminal, arm,
                          *, soft_lambda_normalized=None):
    """Return coefficients, diagnostics and (for physical arms) restricted basis."""
    soft_lambda_normalized = resolve_soft_lambda(arm, soft_lambda_normalized)
    ids = _ids(support)
    A, y, gains = np.asarray(A, complex), np.asarray(y, complex), np.asarray(gains, complex)
    if (arm not in ARMS or len(ids) > 40 or y.ndim != 1 or A.shape != (len(y), len(ids))
            or gains.shape != (len(ids),) or not np.isfinite(A).all()
            or not np.isfinite(y).all() or not np.isfinite(gains).all()
            or np.ndim(sigma_terminal) != 0 or np.iscomplexobj(sigma_terminal)
            or not np.isfinite(sigma_terminal) or sigma_terminal <= 0):
        raise ValueError('invalid observed physical inputs/arm/capacity/variance')
    # This experiment's immutable dictionary domain, not physical path count.
    if system.k_max_cap != 2 or system.l_max_cap != 102:
        raise ValueError('physical refit requires registered delay102/Doppler2 domain')
    diagnostic = dict(arm=arm, atom_ids=ids.tolist(), coefficient_dimension=len(ids),
                      truth_access='none', fallback=None, query_count=0)
    if arm == 'm-soft':
        diagnostic['soft_lambda_normalized'] = soft_lambda_normalized
    if not len(ids):
        diagnostic.update(rank=0, basis_rank=0, iterations=0, converged=True,
                          zero_model=True, residual_squared=float(np.linalg.norm(y)**2))
        return dict(coefficients=np.zeros(0, complex), diagnostics=diagnostic,
                    basis=np.zeros((0, 0), complex))
    width = 2*system.k_max_cap+1
    if arm == 'm-group':
        labels = ids//width
        incidence = labels[:, None] == np.unique(labels)[None, :]
        result = fit(y, A, ids, 'group', incidence=incidence, sigma_terminal=sigma_terminal)
        result['diagnostics'].update(diagnostic)
        result['diagnostics']['group_labels'] = np.unique(labels).tolist()
        return result
    centers = _centers(ids, gains, width, system.k_max_cap)
    diagnostic['center_atom_ids'] = [atom for atom, _, _ in centers]
    selected, search = _search(system, y, A, ids, centers, arm == 'm-param-reference')
    diagnostic.update(search)
    W = selected['basis']
    u, singular, _, rank, threshold = _svd(W)
    diagnostic.update(basis_rank=rank, basis_singular_values=singular.tolist(),
                      basis_rank_threshold=float(threshold), zero_basis=rank == 0,
                      zero_basis_slots=np.flatnonzero(~np.any(W != 0, axis=0)).tolist(),
                      basis_overlap_rows=int(np.count_nonzero(np.count_nonzero(W, axis=1) > 1)),
                      latent_slots=W.shape[1], **selected['details'])
    coefficients = selected['coefficients']
    if arm == 'm-soft':
        complement = np.eye(len(ids))-u[:, :rank]@u[:, :rank].conj().T
        lam = float(soft_lambda_normalized*np.linalg.norm(A, 'fro')**2/len(ids))
        if lam == 0:
            coefficients, details = _fit_ls(A, y)
        else:
            augmented = np.vstack((A, np.sqrt(lam)*complement))
            coefficients, details = _fit_ls(augmented, np.concatenate((y, np.zeros(len(ids)))))
        diagnostic.update(soft_lambda=lam, soft_solve=details,
                          soft_penalty_squared=float(np.linalg.norm(complement@coefficients)**2),
                          soft_objective=float(np.linalg.norm(y-A@coefficients)**2+lam*np.linalg.norm(complement@coefficients)**2),
                          fallback='zero-basis-ridge' if rank == 0 and lam > 0 else None)
    if not np.isfinite(coefficients).all():
        raise FloatingPointError('nonfinite final physical coefficients')
    diagnostic['residual_squared'] = float(np.linalg.norm(y-A@coefficients)**2)
    return dict(coefficients=coefficients, diagnostics=diagnostic, basis=W)
