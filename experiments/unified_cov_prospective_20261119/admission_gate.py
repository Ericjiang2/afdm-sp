"""Isolated two-support admission-law check for DRAFT §10.7."""

import numpy as np

import cstate


def _closed_rewards(z, energy, total_v, ridge, b2):
    # Phase-aligned pair b is b(1,z). Its sum/difference projections have
    # squared norms |b|²(1±z)²/2. Each mirror replaces one CD curvature by
    # the scalar curvature of that mode, with the singleton unchanged.
    loading = energy + total_v
    t = loading + ridge
    low, high = t - loading * z, t + loading * z
    cd = b2 * z**2 * ridge**2 / (t * (t**2 - (loading * z)**2))
    a2 = b2 * z**2 * (total_v + ridge)**2 / (t * (t**2 - (energy * z)**2))
    mirror_shift = total_v * z
    return {
        'A2': a2,
        'CD': cd,
        'U': cd - b2 * total_v * (1 - z)**2 / (2 * low * (low + total_v)),
        'C-hi': cd - b2 * mirror_shift * (1 - z)**2 / (2 * low * (low + mirror_shift)),
        'C-lo': cd + b2 * mirror_shift * (1 + z)**2 / (2 * high * (high - mirror_shift)),
    }


def _fitted_reduction(response, y, gamma, ridge):
    b = response.conj().T @ y
    q = response.conj().T @ response + gamma + ridge * np.eye(len(b))
    gains = np.linalg.solve(q, b)
    return float(np.vdot(b, gains).real)


def synthetic_gate(full, cd):
    """Measure the pair-minus-singleton reward independently for each arm."""
    n, energy, total_v, ridge, c1, c2 = 1024, 3., 2., .5, .02, .01
    variances = np.full(n, total_v / n)
    xt = np.full(n, np.sqrt(energy / n), dtype=complex)
    anchor = full.Path(0, 0.)
    singleton = full._responses(xt, [anchor], c1, c2)
    y = singleton[:, 0] / energy
    rows = []
    for delta in (.25, .5):
        dopplers = np.array([0., delta])
        delays = np.zeros(2, dtype=int)
        # Constant-modulus time-domain columns give κ=D. The support
        # covariances use the same complex phases as the response Gram.
        pair = full._responses(xt, [anchor, full.Path(0, delta)], c1, c2)
        z = float(abs(np.sinc(delta) / np.sinc(delta / n)))
        if 1 - z >= cstate.TAU:
            raise AssertionError('Admission-law slice requires an active low mode')
        predicted = _closed_rewards(z, energy, total_v, ridge, b2=1.)
        for arm, expected in predicted.items():
            gamma_single = cstate.support_covariance(
                full, cd, variances, delays[:1], dopplers[:1], c1, arm=arm)
            gamma_pair = cstate.support_covariance(
                full, cd, variances, delays, dopplers, c1, arm=arm)
            single_fit = _fitted_reduction(singleton, y, gamma_single, ridge)
            pair_fit = _fitted_reduction(pair, y, gamma_pair, ridge)
            measured = pair_fit - single_fit
            error = abs(measured - expected) / abs(expected)
            if not np.isfinite(error) or error > 1e-8:
                raise AssertionError(f'{arm} at {delta} bin: relative admission reward error {error:.3g}')
            rows.append(dict(arm=arm, delta_bin=delta, coherence=z,
                             singleton_reduction=single_fit, pair_reduction=pair_fit,
                             measured_reward=measured, closed_reward=expected, relative_error=error))
    return dict(passed=True, max_relative_error=max(row['relative_error'] for row in rows),
                rtol=1e-8, slices=rows)
