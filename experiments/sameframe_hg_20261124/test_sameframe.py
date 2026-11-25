"""Unit tests for sameframe.py P1/P2 crossing, censoring, joint bootstrap, and verdict rules."""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'data_pilot_fer_20261121'))

import sameframe as sf  # noqa: E402
import stageA2  # noqa: E402


def _make_fail_array(curves: dict[int, list[float]], n_frames: int = 200, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    u = rng.random((n_frames, 2))
    rhos = sorted(curves)
    n_snrs = len(next(iter(curves.values())))
    out = np.zeros((n_frames, 2, len(rhos), n_snrs), dtype=bool)
    for ri, r in enumerate(rhos):
        for si in range(2):
            for ji, p in enumerate(curves[r]):
                out[:, si, ri, ji] = u[:, si] < p
    return out


def test_verdict_boundaries():
    assert sf.p1_verdict(0.5, 0.9) == 'DOPPLER-LINE'
    assert sf.p1_verdict(0.51, 0.9) == 'DOPPLER-LINE'
    assert sf.p1_verdict(0.1, 0.499) == 'WRITE-A'
    assert sf.p1_verdict(-0.2, 0.499) == 'WRITE-A'
    assert sf.p1_verdict(0.499, 0.5) == 'INCONCLUSIVE'
    assert sf.p1_verdict(-math.inf, math.inf) == 'INCONCLUSIVE'

    assert sf.p2_verdict(0.201, 0.8) == 'STILL_BEHIND'
    assert sf.p2_verdict(0.2, 0.8) == 'MIXED'
    assert sf.p2_verdict(-0.3, 0.199) == 'CATCHES_UP'
    assert sf.p2_verdict(-0.3, 0.2) == 'MIXED'
    assert sf.p2_verdict(-math.inf, math.inf) == 'MIXED'


def test_p1_joint_bootstrap_and_censoring():
    snrs_a = (300, 400, 500, 600, 700)
    snrs_a3 = (200, 250, 300, 400, 500, 600, 700)
    # Identical curves shifted by 1.0 dB -> D = +1.0 dB -> DOPPLER-LINE
    c_hg = {100: [0.8, 0.4, 0.05, 0.005, 0.0], 150: [0.5, 0.2, 0.02, 0.002, 0.0], 200: [0.4, 0.1, 0.005, 0.0, 0.0], 250: [0.5, 0.2, 0.01, 0.0, 0.0]}
    c_s100 = {100: [0.6, 0.2, 0.05, 0.005, 0.0, 0.0, 0.0], 150: [0.7, 0.3, 0.08, 0.01, 0.0, 0.0, 0.0], 200: [0.8, 0.4, 0.1, 0.02, 0.005, 0.0, 0.0]}
    fail_by_arm = {
        'HG': ((100, 150, 200, 250), snrs_a, _make_fail_array(c_hg, seed=1)),
        'HG1': ((100, 150, 200, 250), snrs_a, _make_fail_array(c_hg, seed=1)),
        's100': ((100, 150, 200), snrs_a3, _make_fail_array(c_s100, seed=1)),
    }
    res = sf.analyze_part1(fail_by_arm, (100, 150, 200, 250), False, stageA2.crossing, boot_draws=200, boot_seed=42)
    p1 = res['primary_P1']
    assert p1['verdict'] == 'DOPPLER-LINE', p1
    assert p1['censored_draw_fraction'] == 0.0
    assert p1['ci95_db'][0] >= 0.5

    # Right-censored HG everywhere -> conservative interval [+inf] upper, finite positive lower
    c_rc = {r: [0.9, 0.8, 0.6, 0.4, 0.2] for r in (100, 150, 200, 250)}
    fail_rc = dict(fail_by_arm, HG=((100, 150, 200, 250), snrs_a, _make_fail_array(c_rc, seed=1)))
    res_rc = sf.analyze_part1(fail_rc, (100, 150, 200, 250), False, stageA2.crossing, boot_draws=200, boot_seed=42)
    assert res_rc['primary_P1']['ci95_db'][1] == '+inf'
    assert res_rc['primary_P1']['verdict'] == 'DOPPLER-LINE'


if __name__ == '__main__':
    test_verdict_boundaries()
    test_p1_joint_bootstrap_and_censoring()
    print('ALL_SAMEFRAME_UNIT_TESTS_PASS')
