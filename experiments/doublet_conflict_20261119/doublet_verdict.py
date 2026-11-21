"""Paired 600-frame compatibility verdict from DRAFT §2."""

from pathlib import Path
import sys

import numpy as np
from scipy.special import betaincinv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tf_covariance_audit_20261018'))
from sampling import bootstrap_means, interval


N_FRAMES = 600
N_BOOT = 20_000
SEED = 20261120
MARGIN = .01
MIN_DISCORDANT = 5


def _cp95_upper(count):
    # Called only for the rare branch, so count < N_FRAMES.
    return float(betaincinv(count + 1, N_FRAMES - count, .95))


def _classify(ci_lo, ci_hi):
    if ci_hi <= MARGIN:
        return 'compatible', ci_lo > 0
    if ci_lo > 0:
        return 'conflict', False
    return 'uncertain', False


def evaluate(fer_u, fer_cd, frames):
    """Score aligned U/CD frame-failure indicators, with one pair per frame."""
    frames = np.asarray(frames)
    if (frames.shape != (N_FRAMES,) or not np.issubdtype(frames.dtype, np.integer)
            or np.unique(frames).size != N_FRAMES):
        raise ValueError(f'Expected {N_FRAMES} unique integer frame IDs')
    u = np.asarray(fer_u)
    cd = np.asarray(fer_cd)
    if any(v.shape != frames.shape or not np.isin(v, (0, 1)).all() for v in (u, cd)):
        raise ValueError('Each arm must have one binary outcome per frame')

    differences = u.astype(np.int8) - cd.astype(np.int8)
    u_only = int(np.count_nonzero(differences == 1))
    cd_only = int(np.count_nonzero(differences == -1))
    discordant = u_only + cd_only
    if discordant >= MIN_DISCORDANT:
        draws, _ = bootstrap_means({'delta': differences}, frames, n_boot=N_BOOT, seed=SEED)
        limits = interval(draws['delta'])
        ci_lo, ci_hi = limits['ci_lo'], limits['ci_hi']
        method = 'paired frame percentile bootstrap, 95%'
    else:
        # Delta = p(U-only) - p(CD-only). Each endpoint separately
        # bounds Delta with at least 95% coverage. There is no joint claim.
        ci_lo, ci_hi = -_cp95_upper(cd_only), _cp95_upper(u_only)
        method = 'one-sided 95% Clopper–Pearson bounds'

    verdict, small_detectable_harm = _classify(ci_lo, ci_hi)
    return dict(delta=(u_only - cd_only) / N_FRAMES, ci_lo=ci_lo, ci_hi=ci_hi,
                n_frames=N_FRAMES, margin=MARGIN, method=method, verdict=verdict,
                small_detectable_harm=small_detectable_harm, discordant=discordant,
                u_only_failures=u_only, cd_only_failures=cd_only)
