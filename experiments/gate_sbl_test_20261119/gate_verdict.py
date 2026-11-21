"""Paired frame-cluster and resolution-loss decisions for PROTOCOL §3 and §8."""

from pathlib import Path
import sys

import numpy as np
from scipy.special import betaincinv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tf_covariance_audit_20261018'))
from sampling import bootstrap_means, interval

N_BOOT = 20_000
SEED = 20261123
S_MARGIN = 0.01
X_MARGIN = 0.05
X_MIN_FRAMES = 74


def _binary_vector(values, name):
    values = np.asarray(values)
    if values.ndim != 1 or not values.size or not np.isin(values, (0, 1)).all():
        raise ValueError(f'{name} must be a nonempty binary vector')
    return values.astype(bool)


def paired_interval(difference, frames):
    """Estimate a pooled per-key contrast, resampling whole physical frames."""
    draws, n_frames = bootstrap_means({'difference': difference}, frames, n_boot=N_BOOT, seed=SEED)
    return dict(point=float(np.mean(difference)), **interval(draws['difference']),
                n_frame_clusters=n_frames, bootstrap=dict(draws=N_BOOT, seed=SEED))


def s_leg(g_failed, slo_failed, frames, same_projectors):
    """Use matched keys with a projector-equality flag per initial grid."""
    g_failed = _binary_vector(g_failed, 'G failures')
    slo_failed = _binary_vector(slo_failed, 'S-lo failures')
    same_projectors = _binary_vector(same_projectors, 'projector equality')
    if g_failed.shape != slo_failed.shape or g_failed.shape != same_projectors.shape:
        raise ValueError('S leg requires matched G, S-lo and projector-equality keys')

    result = paired_interval(g_failed.astype(int) - slo_failed, frames)
    lo, hi = result['ci_lo'], result['ci_hi']
    same_count = int(same_projectors.sum())
    n_keys = len(g_failed)
    # More than 95% invalidates the S leg. Exactly 95% is valid.
    valid = 20 * same_count <= 19 * n_keys
    if not valid:
        verdict = 'uninformative'
    elif hi < S_MARGIN:
        verdict = 'pass'
    elif lo > S_MARGIN:
        verdict = 'fail'
    else:
        verdict = 'uncertain'
    return dict(result, verdict=verdict, margin=S_MARGIN, n_keys=n_keys, valid=valid,
                same_projector_keys=same_count, same_projector_fraction=same_count / n_keys,
                lower_positive=lo > 0, upper_negative=hi < 0,
                equivalent=-S_MARGIN <= lo <= hi <= S_MARGIN)


def _x_verdict(lo, hi, enough_leverage):
    if enough_leverage and hi < X_MARGIN:
        return 'pass'
    if lo >= X_MARGIN:
        return 'fail'
    return 'uncertain'


def x_leg(cd_resolved, gate_resolved):
    """Estimate G-ex loss conditional on CD resolving the 0.35-bin pair."""
    cd_resolved = _binary_vector(cd_resolved, 'CD resolution')
    gate_resolved = _binary_vector(gate_resolved, 'G-ex resolution')
    if cd_resolved.shape != gate_resolved.shape:
        raise ValueError('X leg requires one matched CD and G-ex resolution outcome per frame')

    resolved = int(cd_resolved.sum())
    lost = int(np.count_nonzero(cd_resolved & ~gate_resolved))
    result = dict(n_frames=len(cd_resolved), cd_resolved_frames=resolved, lost_frames=lost,
                  margin=X_MARGIN, leverage_insufficient=resolved < X_MIN_FRAMES)
    if not resolved:
        return dict(result, point=None, ci_lo=None, ci_hi=None, verdict='uncertain')

    lo = float(betaincinv(lost, resolved - lost + 1, .025)) if lost else 0.
    hi = float(betaincinv(lost + 1, resolved - lost, .975)) if lost < resolved else 1.
    return dict(result, point=lost / resolved, ci_lo=lo, ci_hi=hi,
                verdict=_x_verdict(lo, hi, resolved >= X_MIN_FRAMES))


def _joint_verdict(s, x):
    if s == x == 'pass':
        return 'supported'
    if 'fail' in (s, x):
        return 'not_supported'
    return 'uncertain'


def readout(g_failed, slo_failed, frames, same_projectors, cd_resolved, gate_resolved):
    """Evaluate both legs from aligned rows whose keys the caller has validated."""
    s = s_leg(g_failed, slo_failed, frames, same_projectors)
    x = x_leg(cd_resolved, gate_resolved)
    return dict(s_leg=s, x_leg=x, joint=_joint_verdict(s['verdict'], x['verdict']))
