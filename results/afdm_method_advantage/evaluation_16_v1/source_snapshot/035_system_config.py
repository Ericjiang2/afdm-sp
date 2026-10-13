"""Shared system construction formerly imported from archived experiment scripts.

Keep the historical mixin order and N=512 configuration unchanged so baseline
evaluation no longer depends on the missing verify_oamp/teacher-export modules.
"""
from __future__ import annotations

import math
import pickle
from pathlib import Path

import numpy as np

from .afdm_env import AFDMEnvMixin
from .afdm_models import AFDMModelsMixin
from .afdm_trainer import AFDMTrainerMixin
from .afdm_baselines import AFDMBaselinesMixin


class AFDMSystem(AFDMEnvMixin, AFDMModelsMixin, AFDMTrainerMixin, AFDMBaselinesMixin):
    """Historical AFDM system composition, without an experiment entry point."""


def _make_system():
    """Preserve the N=512 baseline configuration from the archived verifier."""
    sys_obj = AFDMSystem(N=16, M=32, rho=0.5)
    new_lmax = int(math.ceil(50 * 512 * sys_obj.delta_f / sys_obj.fs / 5.0)) * 5
    sys_obj.l_max_cap = max(new_lmax, 15)
    sys_obj.k_max_cap = 2
    k_factor = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + k_factor * sys_obj.l_max_cap
    sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
    sys_obj.max_delay_idx_bar_supported = (
        int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1
    )
    sys_obj.P_paths = 5
    sys_obj.use_frac_doppler = True
    sys_obj.k_leak = 2
    sys_obj.frac_prune_rel_thres = 0.01
    return sys_obj


def _sync_l_max_cap(sys_obj, ckpt_dir):
    """Load optional historical scalers; retain the configured delay cap.

    The legacy function name is retained for its callers. Its historical
    behavior loads normalization statistics, not a new delay cap.
    """
    stats_path = Path(ckpt_dir) / 'global_stats.pkl'
    if stats_path.exists():
        with stats_path.open('rb') as handle:
            stats = pickle.load(handle)
        sys_obj.global_std_X = stats.get('std_X', 1.0)
        sys_obj.global_std_y = stats.get('std_y', 1.0)
    return sys_obj
