"""Focused zero-receiver check of the separate local-trial audit."""

from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE),
                str(HERE.parent/'sp_afdm_native_joint_20260921'/'src'),
                str(HERE.parent/'sp_afdm_frozen_20260920'/'src')]
import audit_local_trials as audit  # noqa: E402


def test_postqualification_local_trials_are_checked_at_original_tolerance():
    paths = [dict(delay=2, doppler=.25)]
    trace = dict(pass_index=0, slot=0, accepted=False, trial_count=2,
        rejected_duplicate_trials=1, local_phase_entering_paths=paths,
        center=.25, bounds=(-.5, 1.), start=paths[0], endpoint=paths[0],
        start_objective=3., endpoint_objective=3., trials=[
            dict(doppler=.2, valid=True, score=3.1),
            dict(doppler=.25, valid=False, score=None)])
    saved = dict(local_trace=[deepcopy(trace)], paths=paths,
                 gains=np.array([1+2j]), objective_after=3.)
    actual = SimpleNamespace(local_trace=[deepcopy(trace)],
        paths=[audit.kernel.Path(2, .25)], gains=np.array([1+2j]),
        objective_after=3.)
    check = audit.compare_local('frame/LOCAL20', actual, saved)
    assert check['local_coordinates'] == 1 and check['local_trials'] == 2
    actual.local_trace[0]['trials'][0]['score'] += 3e-10
    with pytest.raises(AssertionError, match='trial0/score'):
        audit.compare_local('frame/LOCAL20', actual, saved)
