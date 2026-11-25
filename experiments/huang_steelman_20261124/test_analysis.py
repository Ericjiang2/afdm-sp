"""Synthetic unit tests for analysis.py and arms.match_paths_1to1 (boundary/censoring/tie cases)."""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hs_analysis as an  # noqa: E402
import hs_arms as ar  # noqa: E402


def _make_rows(curves: dict[tuple[str, int, str], list[float]], n: int = 200, seed: int = 7):
    rng = np.random.default_rng(seed)
    u = rng.random((n, 2))
    rhos = sorted({r for _, r, _ in curves})
    arms = tuple(sorted({a for _, _, a in curves}))
    snrs = (300, 400, 500, 600, 700, 800)
    rows = {}
    for s_i, s in enumerate(('U', 'G')):
        for rho in rhos:
            for j, snr in enumerate(snrs):
                for f in range(n):
                    arm_recs = {}
                    for a in arms:
                        err = int(u[f, s_i] < curves[(s, rho, a)][j])
                        arm_recs[a] = dict(errors=err, decoded_sha='x')
                    if 'HG' in arm_recs and 'HG1' in arm_recs:
                        arm_recs['HG']['passes_used'] = 1 if arm_recs['HG1']['errors'] == 0 else 2
                    rows[(s, rho, snr, f)] = dict(
                        scenario=s, rho_permille=rho, snr_centi_db=snr, frame=f,
                        triggered=bool(arm_recs['F0']['errors'] > 0), arms=arm_recs,
                    )
    return rows, tuple(arms), tuple(rhos), snrs, tuple(range(n))


def test_identical_arms_with_tied_rhos_and_censoring():
    # Tied optimal rho (250 & 300 identical), and rho=150 right-censored everywhere
    c_opt = [0.5, 0.2, 0.05, 0.005, 0.0, 0.0]
    c_mid = [0.6, 0.3, 0.10, 0.02, 0.005, 0.0]
    c_rc = [0.9, 0.8, 0.6, 0.4, 0.2, 0.1]  # never <= 0.01 -> right-censored
    curves = {}
    for s in ('U', 'G'):
        for a in ('F0', 'CD', 'Z', 'HG', 'HG1'):
            curves[(s, 150, a)] = c_rc
            curves[(s, 250, a)] = c_opt
            curves[(s, 300, a)] = c_opt
            curves[(s, 500, a)] = c_mid
    rows, arms, rhos, snrs, frames = _make_rows(curves, n=200)
    res = an.analyze(rows, arms, rhos, snrs, frames, boot_draws=2000, boot_seed=1)
    q2 = res['primary']['Q2']
    q3 = res['primary']['Q3']
    assert q2['ci_projected_db'] == [0.0, 0.0], q2
    assert q2['verdict'] == 'EQUIVALENT', q2
    assert q3['ci_projected_db'] == [0.0, 0.0], q3
    assert q3['verdict'] == 'Z_EQUIVALENT', q3
    assert not q3['strictly_nonzero'], q3


def test_both_right_censored_all_rhos():
    c_rc = [0.9, 0.8, 0.6, 0.4, 0.2, 0.1]
    curves = {(s, r, a): c_rc for s in ('U', 'G') for r in (150, 300) for a in ('F0', 'CD', 'Z', 'HG', 'HG1')}
    rows, arms, rhos, snrs, frames = _make_rows(curves, n=100)
    res = an.analyze(rows, arms, rhos, snrs, frames, boot_draws=1000, boot_seed=2)
    assert res['primary']['Q2']['ci_projected_db'] == ['-inf', '+inf']
    assert res['primary']['Q2']['verdict'] == 'INCONCLUSIVE'
    assert res['primary']['Q3']['ci_projected_db'] == ['-inf', '+inf']
    assert res['primary']['Q3']['verdict'] == 'Z_INCONCLUSIVE'


def test_hg_all_right_censored_cd_finite():
    c_good = [0.5, 0.2, 0.04, 0.005, 0.0, 0.0]
    c_rc = [0.9, 0.8, 0.6, 0.4, 0.2, 0.1]
    curves = {}
    for s in ('U', 'G'):
        for r in (150, 300):
            curves[(s, r, 'F0')] = c_rc
            curves[(s, r, 'HG')] = c_rc
            curves[(s, r, 'HG1')] = c_rc
            curves[(s, r, 'CD')] = c_good
            curves[(s, r, 'Z')] = c_good
    rows, arms, rhos, snrs, frames = _make_rows(curves, n=200)
    res = an.analyze(rows, arms, rhos, snrs, frames, boot_draws=1000, boot_seed=3)
    q2 = res['primary']['Q2']
    assert q2['ci_projected_db'][1] == '+inf'
    assert isinstance(q2['ci_projected_db'][0], float) and q2['ci_projected_db'][0] > 1.0
    assert q2['verdict'] == 'CD_AHEAD', q2


def test_left_censoring_and_rebound():
    # First-crossing rebound: FER hits 0.005 at index 1 then rebounds to 0.02 at index 2
    fer = np.array([[0.10, 0.005, 0.02, 0.001]])
    b = an._crossing(fer, 200, (300, 400, 500, 600))
    assert math.isfinite(b.lower[0]) and 3.0 < b.lower[0] < 4.0 and b.lower[0] == b.upper[0]
    # Left censored at lowest SNR
    fer_low = np.array([[0.005, 0.001, 0.0, 0.0]])
    bl = an._crossing(fer_low, 200, (300, 400, 500, 600))
    assert np.isneginf(bl.lower[0]) and bl.upper[0] == 3.0


def test_verdict_boundaries():
    # Q2 boundaries
    assert an.verdict_q2(0.5, 0.5, 0.01, 0.9)['verdict'] == 'CD_AHEAD'
    assert an.verdict_q2(0.5, 0.5, 0.01, 0.9)['strict_gt_0p5_db'] is False
    assert an.verdict_q2(0.8, 0.8, 0.51, 1.1)['strict_gt_0p5_db'] is True
    assert an.verdict_q2(0.499, 0.499, 0.01, 0.8)['verdict'] == 'CD_SLIGHT'
    assert an.verdict_q2(0.2, 0.2, 0.05, 0.30)['verdict'] == 'CD_SLIGHT'
    assert an.verdict_q2(-0.15, -0.15, -0.30, -0.05)['verdict'] == 'HG_AHEAD'
    assert an.verdict_q2(0.0, 0.0, -0.5, 0.5)['verdict'] == 'EQUIVALENT'
    assert an.verdict_q2(0.0, 0.0, 0.0, 0.5)['verdict'] == 'EQUIVALENT'
    assert an.verdict_q2(0.0, 0.0, -0.5, 0.0)['verdict'] == 'EQUIVALENT'
    assert an.verdict_q2(0.1, 0.1, -0.1, 0.51)['verdict'] == 'INCONCLUSIVE'
    assert an.verdict_q2(-0.1, -0.1, -0.51, 0.1)['verdict'] == 'INCONCLUSIVE'
    assert an.verdict_q2(-math.inf, math.inf, -math.inf, math.inf)['verdict'] == 'INCONCLUSIVE'

    # Q3 boundaries
    assert an.verdict_q3(-0.5, 0.5)['verdict'] == 'Z_EQUIVALENT'
    assert an.verdict_q3(0.05, 0.20)['verdict'] == 'Z_EQUIVALENT'
    assert an.verdict_q3(0.05, 0.20)['strictly_nonzero'] is True
    assert an.verdict_q3(0.05, 0.80)['verdict'] == 'CD_NEEDED'
    assert an.verdict_q3(0.05, 0.80)['strict_gt_0p5_db'] is False
    assert an.verdict_q3(0.55, 0.90)['strict_gt_0p5_db'] is True
    assert an.verdict_q3(-0.80, -0.05)['verdict'] == 'Z_BETTER'
    assert an.verdict_q3(-0.10, 0.60)['verdict'] == 'Z_INCONCLUSIVE'
    assert an.verdict_q3(-math.inf, math.inf)['verdict'] == 'Z_INCONCLUSIVE'


def test_match_paths_1to1():
    # Two true paths at same delay: stronger g=1.0 at nu=0.2, weaker g=0.3 at nu=0.4.
    # Single fitted path at nu=0.35 (within 0.5 of BOTH) must match stronger true path!
    truth = dict(
        l_i=np.array([5, 5, 10]),
        k_real=np.array([0.2, 0.4, -1.0]),
        g_i=np.array([1.0 + 0j, 0.3 + 0j, 0.5 + 0j]),
    )
    m = ar.match_paths_1to1([5, 10], [0.35, -0.5], truth)
    assert m['matched_count'] == 2 and m['total_true'] == 3
    expected_pw = (1.0**2 + 0.5**2) / (1.0**2 + 0.3**2 + 0.5**2)
    assert abs(m['matched_power_frac'] - expected_pw) < 1e-12, (m, expected_pw)
    # Exact boundary |dk| == 0.5 matches; |dk| > 0.5 (even 0.5 + 1e-12) must NOT match
    m2 = ar.match_paths_1to1([10], [-0.499999999999], truth)
    assert m2['matched_count'] == 0
    # Strict lexicographic power priority even when two true powers are almost equal
    truth_close = dict(
        l_i=np.array([5, 5]),
        k_real=np.array([0.0, 0.3]),
        g_i=np.array([1.0 + 1e-9, 1.0]),
    )
    mc = ar.match_paths_1to1([5], [0.3], truth_close)
    assert mc['matched_count'] == 1
    assert abs(mc['matched_power'] - (1.0 + 1e-9) ** 2) < 1e-12


def test_identical_arms_heavy_right_censoring_yields_unbounded():
    # Identical arms where EVERY rho has right-censored bootstrap draws exceeding tail rank -> [-inf, +inf]
    c_edge = [0.5, 0.2, 0.1, 0.05, 0.04, 0.03]  # empirical FER at top SNR ~0.03 > 0.01 -> heavy right censoring
    curves = {(s, r, a): c_edge for s in ('U', 'G') for r in (150, 300) for a in ('F0', 'CD', 'Z', 'HG', 'HG1')}
    rows, arms, rhos, snrs, frames = _make_rows(curves, n=100, seed=11)
    res = an.analyze(rows, arms, rhos, snrs, frames, boot_draws=2000, boot_seed=5)
    assert res['primary']['Q3']['censored_draw_fraction'] > 0.2, res['primary']['Q3']
    assert res['primary']['Q3']['ci_projected_db'] == ['-inf', '+inf'], res['primary']['Q3']
    assert res['primary']['Q3']['verdict'] == 'Z_INCONCLUSIVE', res['primary']['Q3']


if __name__ == '__main__':
    test_identical_arms_with_tied_rhos_and_censoring()
    test_both_right_censored_all_rhos()
    test_hg_all_right_censored_cd_finite()
    test_left_censoring_and_rebound()
    test_verdict_boundaries()
    test_match_paths_1to1()
    test_identical_arms_heavy_right_censoring_yields_unbounded()
    print('ALL_UNIT_TESTS_PASS')
