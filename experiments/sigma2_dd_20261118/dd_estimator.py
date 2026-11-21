"""One observed-input DD update in per-complex-sample variance units."""

import numpy as np


def estimate_dd(obs, system, mu, variance, delays, dopplers, gains):
    from physical import projected_variance, regressors

    y = obs['y']
    matrix = regressors(obs['pilot'] + mu, delays, dopplers, system.c1, system.c2)
    residual = y - matrix @ gains
    gamma = projected_variance(variance, delays, dopplers, system.c1)
    residual_power = np.vdot(residual, residual).real / len(y)
    uncertainty_power = np.vdot(gains, gamma @ gains).real / len(y)
    raw = float(residual_power - uncertainty_power)
    if not np.isfinite(raw):
        raise ValueError('Nonfinite DD noise variance')
    return dict(estimate=max(.001, raw), raw=raw, clipped=raw < .001,
                residual_power=float(residual_power), uncertainty_power=float(uncertainty_power))
