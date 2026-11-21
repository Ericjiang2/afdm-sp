"""Phase 1b schedule for the frozen unified-covariance SBL receiver."""

from hashlib import sha256
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
import sys
import time
from types import FunctionType, SimpleNamespace

import numpy as np
from scipy.linalg import eigvalsh


FROZEN_DIR = Path(__file__).resolve().parents[1] / 'unified_cov_prospective_20261119'
FROZEN_SOURCES = {
    'sbl.py': 'be8afdbb11c278b182185d21ca3e7e7e92d23adf405bd97b2beb52c8b8658b80',
    'projector.py': '600da7cdd837452c8df049fd19745f9fce441b5b30a234a7364d4c908ac4b4e8',
}
sys.path.insert(0, str(FROZEN_DIR))


def _load_frozen(name):
    spec = find_spec(name)
    path = FROZEN_DIR / f'{name}.py'
    if spec is None or Path(spec.origin).resolve() != path:
        raise RuntimeError(f'Unexpected frozen source origin for {name}')
    if sha256(path.read_bytes()).hexdigest() != FROZEN_SOURCES[path.name]:
        raise RuntimeError(f'Frozen source hash mismatch: {path}')
    return import_module(name)


projector = _load_frozen('projector')
frozen = _load_frozen('sbl')
if frozen.low_projector is not projector.low_projector:
    raise RuntimeError('Frozen SBL bound a different low projector')

ARMS = ('R0', 'U2', 'K', 'M', 'KM')
SHARED_EM = {'M': 'U2', 'KM': 'K'}
K_PSD_TOL = 1e-10
SMOKE_KEYS = frozenset(frozen.e3c.lib.smoke_keys())
ARCHIVE_KEYS = frozenset(
    (scenario, 300, snr, frame)
    for frame in range(4400, 4600)
    for scenario in ('U', 'G')
    for snr in (600, 700, 800, 900, 1000, 1100)
)


class _ObserveEigenpairs:
    """Observe exactly the eigenpairs used to build the frozen S-lo ridge."""

    def __init__(self):
        self.pairs = []
        self.linalg = SimpleNamespace(eigh=self.eigh)

    def __getattr__(self, name):
        return getattr(np, name)

    def eigh(self, matrix):
        pair = np.linalg.eigh(matrix)
        self.pairs.append(pair)
        return pair


def _settings_with_pairs(v, sigma2, delays, dopplers, c1):
    spectral = frozen.spectral
    observer = _ObserveEigenpairs()
    ridges = spectral.spectral_ridges
    observed_ridges = FunctionType(ridges.__code__, dict(ridges.__globals__, np=observer))
    settings = spectral.arm_settings
    observed_settings = FunctionType(
        settings.__code__, dict(settings.__globals__, spectral_ridges=observed_ridges)
    )
    return observed_settings(v, sigma2, delays, dopplers, c1, True), observer.pairs


class KCovariancePSDViolation(RuntimeError):
    """The capped full covariance fails the protocol's PSD gate."""


def require_k_psd(covariance, u, key):
    """Check the full initial K matrix under the frozen EM Hermitian convention."""
    hermitian = (covariance + covariance.conj().T) / 2
    minimum = float(eigvalsh(hermitian, subset_by_index=(0, 0))[0])
    if minimum < -K_PSD_TOL * u:
        raise KCovariancePSDViolation(
            f'K full initial EM covariance fails PSD on {key}: '
            f'lambda_min={minimum:.17g}, minimum_allowed={-K_PSD_TOL * u:.17g}, u={u:.17g}'
        )
    return dict(lambda_min=minimum, lambda_min_over_u=minimum / u if u else None,
                relative_tolerance=K_PSD_TOL, u=u)


def _cap_covariance(exact, unified, delays, u, blocks, pairs, *, key, verify=False):
    """Cap the exact high modes in the U2 EM covariance once, on the full candidate set."""
    removed = np.zeros_like(unified)
    count = blocks_capped = 0
    for ((ix, _, _, _), (values, vectors)) in zip(blocks, pairs, strict=True):
        high = values > 1.
        n_capped = int(np.count_nonzero(high))
        if n_capped:
            basis = vectors[:, high]
            removed[ix] = u * ((basis * (values[high] - 1.)) @ basis.conj().T)
            count += n_capped
            blocks_capped += int(len(values) > 1)
    capped = unified.copy()
    same_delay = delays[:, None] == delays[None, :]
    capped[same_delay] -= removed[same_delay]
    psd = require_k_psd(capped, u, key)
    census = dict(blocks_total=sum(len(values) > 1 for values, _ in pairs), blocks_capped=blocks_capped,
                  eigenvalues_total=len(delays), eigenvalues_capped=count,
                  trace_removed=float(np.trace(removed).real),
                  trace_exact=float(np.trace(exact).real),
                  trace_u2=float(np.trace(unified).real))
    checks = _check_cap(exact, unified, capped, same_delay, u, blocks, pairs, census) if verify else None
    return capped, removed, census, checks, psd


def _check_cap(exact, unified, capped, same_delay, u, blocks, pairs, census):
    # The unchanged low modes include the added projector and can exceed one.
    # Check the cap on the original high eigenspace of each actual K block.
    spectral = frozen.spectral
    tolerance = spectral.TOL
    high_max = 0.
    block_error = 0.
    scale = u or 1.
    if u:
        for ((ix, _, _, _), (values, basis)) in zip(blocks, pairs, strict=True):
            actual = basis.conj().T @ (capped[ix] / scale) @ basis
            low = values < spectral.TAU
            expected = np.diag(np.where(low, 1. + values, np.minimum(values, 1.)))
            block_error = max(block_error, spectral.matrix_error(actual, expected))
            if np.any(~low):
                high = actual[np.ix_(~low, ~low)]
                high_max = max(high_max, float(np.linalg.eigvalsh((high + high.conj().T) * .5)[-1]))
    else:
        block_error = spectral.matrix_error(capped, exact)
    cross_delay_unchanged = np.array_equal(capped[~same_delay], exact[~same_delay])
    trace_error = abs(float(np.trace(unified - capped).real) - census['trace_removed']) / scale
    if (not cross_delay_unchanged or high_max > 1. + tolerance
            or not np.isfinite(block_error) or block_error > tolerance
            or not np.isfinite(trace_error) or trace_error > tolerance):
        raise AssertionError(f'K EM cap failed: {block_error=}, {high_max=}, {trace_error=}, '
                             f'{cross_delay_unchanged=}')
    return dict(high_eigenvalue_max=high_max, block_error=block_error, trace_error=trace_error,
                cross_delay_unchanged=cross_delay_unchanged, tolerance=tolerance)


def synthetic_cap_gate():
    delays = np.array([0, 0, 1, 2])
    dopplers = np.array([-.1, .15, .4, -1.])
    variance = (np.arange(32) + 4) / 256
    receipts = {}
    for label, v in (('positive_variance', variance), ('zero_variance', np.zeros_like(variance))):
        (specs, matrices, _, blocks, _), pairs = _settings_with_pairs(v, .05, delays, dopplers, .13)
        exact = matrices['R1']
        _, _, census, checks, psd = _cap_covariance(
            exact, matrices['S-lo'], delays, specs['R1']['sum_vec'], blocks, pairs, key=label, verify=True
        )
        if label == 'positive_variance' and (
            census['blocks_capped'] != 1 or census['trace_removed'] <= 0
            or not np.any(np.abs(exact[delays[:, None] != delays[None, :]]) > 0)
            or not any(np.any((value > 0) & (value < frozen.spectral.TAU)) for value, _ in pairs)
        ):
            raise AssertionError('Synthetic fixture must exercise one capped block, low and cross-delay modes')
        receipts[label] = dict(census=census, psd=psd, **checks)

    # An originally positive covariance can fail after its same-delay high
    # mode is reduced, because the independent delay block keeps its coupling.
    exact = np.array([[1., .9, .85], [.9, 1., .85], [.85, .85, 1.]], dtype=complex)
    delays = np.array([0, 0, 1])
    spectral = frozen.spectral
    ridges, blocks, _ = spectral.spectral_ridges(exact, delays, 1., 1.)
    unified = exact + ridges['S-lo']
    pairs = [np.linalg.eigh((d + d.conj().T) / 2) for _, d, _, _ in blocks]
    unified_psd = require_k_psd(unified, 1., 'synthetic uncapped predecessor')
    try:
        _cap_covariance(exact, unified, delays, 1., blocks, pairs,
                        key='synthetic cross-delay coupling', verify=True)
    except KCovariancePSDViolation as error:
        receipts['indefinite_cross_delay_rejected'] = dict(
            rejected=True, uncapped_psd=unified_psd, detail=str(error)
        )
    else:
        raise AssertionError('K PSD gate accepted a synthetic indefinite cross-delay covariance')
    return receipts


def _fingerprint(values):
    return tuple(frozen.e3c.array_sha(value) for value in values)


def process_key(ctx, cache, grid, key, *, cap=True, verify_controls=False):
    """Reproduce R0/U2 on archived keys and qualify all five arms on smoke keys."""
    smoke = key in SMOKE_KEYS
    if not smoke and (key not in ARCHIVE_KEYS or verify_controls or not cap):
        raise ValueError(f'Phase 1 key or control disallowed: {key}')
    selected = ARMS if smoke else ARMS[:2]
    spectral = frozen.spectral
    refinements = []
    controls = {}
    em_fingerprints, reference_inputs, scalar_results = {}, {}, {}
    census_k = psd_k = None

    def settings(v, sigma2, delays, dopplers, c1, _smoke):
        nonlocal census_k, psd_k
        if smoke and cap:
            (specs, matrices, ridges, blocks, census), pairs = _settings_with_pairs(
                v, sigma2, delays, dopplers, c1
            )
            matrices['K'], removed, census_k, check, psd_k = _cap_covariance(
                matrices['R1'], matrices['S-lo'], delays, specs['R1']['sum_vec'],
                blocks, pairs, key=key, verify=verify_controls
            )
            ridges['K'] = ridges['S-lo'] - removed
            if verify_controls:
                controls['cap'] = check
        else:
            specs, matrices, ridges, blocks, census = spectral.arm_settings(v, sigma2, delays, dopplers, c1, True)
            if smoke:
                matrices['K'] = matrices['S-lo']
                ridges['K'] = ridges['S-lo']
        specs['U2'] = dict(specs['R1'], mode='unified')
        matrices['U2'] = matrices['S-lo']
        ridges['U2'] = ridges['S-lo']
        if smoke:
            for name, source in SHARED_EM.items():
                matrices[name] = matrices[source]
                ridges[name] = ridges[source]
        ranks = [int(np.rint(np.trace(block[2]).real)) for block in blocks]
        census = dict(census, projector_rank=sum(ranks), projector_nonempty_blocks=sum(rank > 0 for rank in ranks))
        return specs, matrices, ridges, blocks, census

    def fit(results, name, B, Y, beta0, gamma, max_iter):
        nonlocal current
        # The frozen loop schedules an R1 prefit only for T0 and R1; neither is emitted here.
        if name == 'R1':
            return None
        current = name
        if name in SHARED_EM:
            source = SHARED_EM[name]
            results[name] = results[source]
            if verify_controls:
                actual = _fingerprint((B, Y, beta0, gamma, max_iter, *results[name].values()))
                controls[f'{name.lower()}_em_bit_identical'] = (
                    actual == em_fingerprints[source] and results[name] is results[source]
                )
            return results[name]
        result = spectral.fit_sbl(results, name, B, Y, beta0, gamma, max_iter)
        if verify_controls and name in SHARED_EM.values():
            em_fingerprints[name] = _fingerprint((B, Y, beta0, gamma, max_iter, *result.values()))
            if name == 'K' and not cap:
                controls['k_uncapped_em_bit_identical'] = em_fingerprints['K'] == em_fingerprints['U2']
        return result

    def refine(Y, xt, v, delays, dopplers, c1, c2, ridge, mode):
        nonlocal u2_refine_fingerprint
        started = time.process_time()
        inputs = (Y, xt, v, delays, dopplers, c1, c2, ridge)
        if mode == 'unified':
            result = frozen._refine_u2(*inputs, force_empty=False)
        else:
            result = frozen.ref.refine(*inputs, mode)
        refinements.append(time.process_time() - started)
        if verify_controls and current in SHARED_EM.values():
            reference_inputs[current] = inputs
        if verify_controls and not cap and current in ('U2', 'K'):
            fingerprint = _fingerprint((*inputs, *result.values()))
            if current == 'U2':
                u2_refine_fingerprint = fingerprint
            else:
                controls['k_uncapped_refine_bit_identical'] = fingerprint == u2_refine_fingerprint
        if verify_controls and current in SHARED_EM:
            scalar_results[current] = inputs, mode, result
        return result

    current = u2_refine_fingerprint = None
    # Rebind the arm schedule and stage hooks in a private namespace. The
    # frozen main loop has no dispatch arguments for new arms or P1 smoke keys.
    run = frozen.frozen_main.process_main_key
    scope = dict(run.__globals__, main_budgets=lambda _key: (100,), MAIN_ARMS={100: selected},
                 arm_settings=settings, fit_sbl=fit, time=SimpleNamespace(perf_counter=time.process_time),
                 REFINEMENT=dict(R0='R0', U2='U2', K='U2', M='R0', KM='R0'),
                 ref=SimpleNamespace(refine=refine))
    row = FunctionType(run.__code__, scope)(ctx, cache, grid, key)
    row['variants'] = row.pop('budgets')['100']['variants']
    for (name, score), elapsed in zip(row['variants'].items(), refinements, strict=True):
        score['seconds']['refinement'] = elapsed
        if name in ('U2', 'K'):
            score['added_trace_refinement'] = score['refine'].get('projector_trace_added', 0.)
        if name in SHARED_EM:
            score['seconds']['sbl'] = 0.
    if census_k is not None:
        row['k_census'] = census_k
        row['k_psd'] = psd_k
    if verify_controls:
        scalar_mode = 'diag'
        for name, source in SHARED_EM.items():
            expected_inputs = (*reference_inputs[source][:-1], row['sigma2'])
            expected = frozen.ref.refine(*expected_inputs, scalar_mode)
            inputs, mode, actual = scalar_results[name]
            controls[f'{name.lower()}_refine_input_bit_identical'] = (
                _fingerprint(inputs) == _fingerprint(expected_inputs) and mode == scalar_mode
            )
            controls[f'{name.lower()}_refine_bit_identical'] = (
                actual.keys() == expected.keys() and _fingerprint(actual.values()) == _fingerprint(expected.values())
            )
        if not all(controls.values()):
            raise AssertionError(f'SBL control failed on {key}: {controls}')
        row['controls'] = controls
    return row
