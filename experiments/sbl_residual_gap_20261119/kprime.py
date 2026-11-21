"""Apply the §8 global cap at the frozen receiver's initial covariance step."""

from statistics import median
from types import FunctionType

import numpy as np
from scipy.linalg import eigvalsh

import gap_receiver as original

CAP_KIND = 'full-initial-exact-spectrum-at-u'
CAP_TOL = 1e-12
CENSUS_COUNTS = ('eigenvalues_total', 'eigenvalues_capped')
CENSUS_MEASURES = ('trace_removed', 'trace_exact', 'trace_u2', 'removed_frobenius_squared',
                   'removed_codelay_frobenius_squared')


def _settings(v, sigma2, delays, dopplers, c1):
    settings = original.frozen.spectral.arm_settings(v, sigma2, delays, dopplers, c1, True)
    return settings, settings[2]['S-lo']


def cap_covariance(exact, unified, delays, u, _blocks, ridge, *, key, verify=False):
    hermitian = (exact + exact.conj().T) * .5
    values, vectors = np.linalg.eigh(hermitian)
    above = values > u
    limited = np.minimum(values, u)
    capped_exact = (vectors * limited) @ vectors.conj().T
    capped = capped_exact + ridge
    psd = original.require_k_psd(capped, u, key)
    cap_check = None
    if verify:
        top = float(eigvalsh((capped_exact + capped_exact.conj().T) * .5,
                              subset_by_index=(len(values) - 1, len(values) - 1))[0])
        bound = u * (1 + CAP_TOL)
        if not top <= bound:
            raise AssertionError(f'K prime exact cap exceeded on {key}: {top:.17g} > {bound:.17g}')
        cap_check = dict(capped_exact_lambda_max=top, upper_bound=bound, relative_tolerance=CAP_TOL)

    # Form the removed component directly from the discarded mode energies.
    excess = values[above] - u
    basis = vectors[:, above]
    removed = (basis * excess) @ basis.conj().T
    same_delay = delays[:, None] == delays[None, :]
    co_delay = removed[same_delay]
    squared = float(np.vdot(removed, removed).real)
    within = float(np.vdot(co_delay, co_delay).real)
    census = dict(eigenvalues_total=len(values), eigenvalues_capped=int(np.count_nonzero(above)),
                  trace_removed=float(np.sum(excess)), trace_exact=float(np.trace(exact).real),
                  trace_u2=float(np.trace(unified).real), removed_frobenius_squared=squared,
                  removed_codelay_frobenius_squared=within,
                  removed_codelay_share=within / squared if squared else None)
    psd['cap_kind'] = CAP_KIND
    return capped, removed, census, cap_check, psd


def bind_key(full_arm_keys):
    # The old adapter exposes no covariance callback. Bind its two private
    # covariance hooks and allowlist while reusing the qualified stage loop.
    base = original.process_key
    return FunctionType(base.__code__, dict(base.__globals__, SMOKE_KEYS=full_arm_keys,
                                            _settings_with_pairs=_settings, _cap_covariance=cap_covariance))


def summarize_census(records):
    total = {name: sum(row[name] for row in records) for name in (*CENSUS_COUNTS, *CENSUS_MEASURES)}
    shares = [row['removed_codelay_share'] for row in records if row['removed_codelay_share'] is not None]
    u2_trace, trimmed = total['trace_u2'], total['removed_frobenius_squared']
    return dict(**total, trace_removed_share_of_U2=total['trace_removed'] / u2_trace if u2_trace else None,
                pooled_removed_codelay_share=total['removed_codelay_frobenius_squared'] / trimmed if trimmed else None,
                median_per_key_removed_codelay_share=median(shares) if shares else None,
                per_key_share_count=len(shares))


def synthetic_gate():
    delays = np.array([0, 0, 1, 2])
    dopplers = np.array([-.1, .15, .4, -1.])
    v = (np.arange(32) + 4) / 256
    cases = {}
    for label, variance in (('positive_variance', v), ('zero_variance', np.zeros_like(v))):
        settings, ridge = _settings(variance, .05, delays, dopplers, .13)
        specs, matrices, _, blocks, _ = settings
        cases[label] = (matrices['R1'], matrices['S-lo'], delays, specs['R1']['sum_vec'], blocks, ridge)

    # Two atoms at one delay couple strongly to a third at another delay.
    # This synthetic fixture was used to check rejection of the old block cap.
    exact = np.array([[1., .9, .85], [.9, 1., .85], [.85, .85, 1.]], dtype=complex)
    delays = np.array([0, 0, 1])
    ridges, blocks, _ = original.frozen.spectral.spectral_ridges(exact, delays, 1., 1.)
    ridge = ridges['S-lo']
    cases['strong_cross_delay_resonance'] = (exact, exact + ridge, delays, 1., blocks, ridge)

    receipts = {}
    for name, args in cases.items():
        exact, _, delays, u, _, ridge = args
        capped, removed, census, spectrum, psd = cap_covariance(*args, key=name, verify=True)
        scale = u or 1.
        error = float(np.max(np.abs(capped - (exact - removed + ridge))) / scale)
        if not error <= CAP_TOL:
            raise AssertionError(f'K prime subtraction identity failed on {name}: {error}')
        if name == 'strong_cross_delay_resonance' and not (
            census['eigenvalues_capped'] > 0 and 0 < census['removed_codelay_share'] < 1
        ):
            raise AssertionError('Resonance fixture must exercise trimming across delays')
        receipts[name] = dict(spectrum=spectrum, psd=psd, census=census, identity_error=error)
    return receipts
