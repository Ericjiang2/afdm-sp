"""Stein-closure noise rule on the frozen sigma2_dd receiver.

Source: ../sigma2_dd_20261118 (dd_estimator, native_dd, receiver_study), reused by import. Only the single
post-round-1 noise value changes: native_dd binds `estimate_dd` at import, so `load(patch=True)` replaces that
one name with `estimate_stein`. Everything else (timing, A1c routing, A3 use of the estimate) is unchanged.
"""
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
DD_DIR = HERE.parent / 'sigma2_dd_20261118'
sys.path.insert(0, str(DD_DIR))
import dd_estimator  # noqa: E402
import receiver_study as rs  # noqa: E402


def stein(r, nu):
    """External closed-loop formula (RULES of stein_sigma2_readout_20261120): positive root of r = (s^2+nu^2)/(s+nu)."""
    arg = r * r + 4 * nu * (r - nu)
    return (r + math.sqrt(max(0.0, arg))) / 2, arg < 0


def estimate_stein(obs, system, mu, variance, delays, dopplers, gains):
    d = dd_estimator.estimate_dd(obs, system, mu, variance, delays, dopplers, gains)
    raw, sqrt_clipped = stein(d['residual_power'], d['uncertainty_power'])
    return dict(d, dd_raw=d['raw'], raw=raw, estimate=max(.001, raw), clipped=raw < .001, sqrt_clipped=sqrt_clipped)


def load(frozen_slot, patch=True):
    study = rs.load(frozen_slot)
    if patch:
        study[3].estimate_dd = estimate_stein
    return study
