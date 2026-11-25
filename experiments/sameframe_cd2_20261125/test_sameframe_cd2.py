"""Unit tests for sameframe_cd2.py P1' verdict rules, joint bootstrap, and 5-arm timing rotation."""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'data_pilot_fer_20261121'))

import sameframe_cd2 as sc  # noqa: E402
import stageA2  # noqa: E402


def _make_fail(curves: dict[int, list[float]], n: int = 200, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    u = rng.random((n, 2))
    rhos = sorted(curves)
    n_s = len(next(iter(curves.values())))
    out = np.zeros((n, 2, len(rhos), n_s), dtype=bool)
    for ri, r in enumerate(rhos):
        for si in range(2):
            for ji, p in enumerate(curves[r]):
                out[:, si, ri, ji] = u[:, si] < p
    return out


def test_p1p_verdict_boundaries():
    assert sc.p1p_verdict(0.5, 0.9) == 'DOPPLER-LINE'
    assert sc.p1p_verdict(0.501, 0.9) == 'DOPPLER-LINE'
    assert sc.p1p_verdict(0.1, 0.499) == 'STOP-LINE'
    assert sc.p1p_verdict(-0.2, 0.499) == 'STOP-LINE'
    assert sc.p1p_verdict(0.499, 0.5) == 'INCONCLUSIVE'
    assert sc.p1p_verdict(-math.inf, math.inf) == 'INCONCLUSIVE'


def test_analyze_partA_and_rotation():
    snrs_a = (300, 400, 500, 600, 700)
    snrs_a3 = (200, 250, 300, 400, 500, 600, 700)
    c_cd2 = {100: [0.8, 0.4, 0.05, 0.005, 0.0], 150: [0.5, 0.2, 0.02, 0.002, 0.0], 200: [0.4, 0.1, 0.005, 0.0, 0.0], 250: [0.5, 0.2, 0.01, 0.0, 0.0]}
    c_s100 = {100: [0.6, 0.2, 0.05, 0.005, 0.0, 0.0, 0.0], 150: [0.7, 0.3, 0.08, 0.01, 0.0, 0.0, 0.0], 200: [0.8, 0.4, 0.1, 0.02, 0.005, 0.0, 0.0]}
    fail_by_arm = {
        'CD2': ((100, 150, 200, 250), snrs_a, _make_fail(c_cd2, seed=2)),
        'HG': ((100, 150, 200, 250), snrs_a, _make_fail(c_cd2, seed=2)),
        's100': ((100, 150, 200), snrs_a3, _make_fail(c_s100, seed=2)),
    }
    res = sc.analyze_partA(fail_by_arm, False, stageA2.crossing, {}, boot_draws=200, boot_seed=20261125)
    assert res['primary_P1_prime']['verdict'] == 'DOPPLER-LINE'
    assert res['secondary_contrasts']['CD2_minus_HG']['ci95_db'] == [0.0, 0.0]

    # Censored CD2 everywhere -> point_db is a 2-element list, must format cleanly without TypeError
    c_rc = {r: [0.9, 0.8, 0.6, 0.4, 0.2] for r in (100, 150, 200, 250)}
    fail_rc = dict(fail_by_arm, CD2=((100, 150, 200, 250), snrs_a, _make_fail(c_rc, seed=2)))
    res_rc = sc.analyze_partA(fail_rc, False, stageA2.crossing, {}, boot_draws=200, boot_seed=20261125)
    assert isinstance(res_rc['primary_P1_prime']['point_db'], list)
    assert res_rc['primary_P1_prime']['ci95_db'][1] == '+inf'
    assert res_rc['primary_P1_prime']['verdict'] == 'DOPPLER-LINE'

    # Verify per-scenario 5-arm rotation puts each arm first exactly 10 times for U and 10 times for G
    first_counts = {'U': {}, 'G': {}}
    scen_pos = {'U': 0, 'G': 0}
    for i in range(100):
        s = 'U' if i % 2 == 0 else 'G'
        off = scen_pos[s] % len(sc.TIMING_BRANCHES)
        scen_pos[s] += 1
        first = sc.TIMING_BRANCHES[off]
        first_counts[s][first] = first_counts[s].get(first, 0) + 1
    assert all(len(d) == 5 and all(v == 10 for v in d.values()) for d in first_counts.values()), first_counts


if __name__ == '__main__':
    test_p1p_verdict_boundaries()
    test_analyze_partA_and_rotation()
    print('ALL_SAMEFRAME_CD2_UNIT_TESTS_PASS')
