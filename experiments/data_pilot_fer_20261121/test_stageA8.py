"""Unit tests for stageA8.py: 0.5 dB lower-bound verdict, exact bootstrap parity with stageA6, and paired accounting."""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stageA2  # noqa: E402
import stageA6  # noqa: E402
import stageA8 as a8  # noqa: E402


def test_verdict_a8_boundaries():
    assert a8.verdict_a8(0.50) == 'GO'
    assert a8.verdict_a8(0.5001) == 'GO'
    assert a8.verdict_a8(math.inf) == 'GO'
    assert a8.verdict_a8(0.4999) == 'STOP'
    assert a8.verdict_a8(0.0) == 'STOP'
    assert a8.verdict_a8(-math.inf) == 'STOP'


def test_bootstrap_exact_parity_with_stageA6_and_go_branch():
    rng = np.random.default_rng(123)
    n_f = 100
    snrs = (300, 400, 450, 500)
    rhos_cd2 = (100, 150, 200, 250)
    rhos_sb = (100, 150)

    def make_grid(rhos, cross_by_rho):
        arr = np.zeros((n_f, 2, len(rhos), len(snrs)), dtype=bool)
        for ri, rho in enumerate(rhos):
            c_db = cross_by_rho[rho]
            for si, snr in enumerate(snrs):
                s_db = snr / 100.0
                if s_db < c_db:
                    arr[:15, :, ri, si] = True
                elif s_db == c_db:
                    arr[:1, :, ri, si] = True
        return arr

    cd2_g = make_grid(rhos_cd2, {100: 5.0, 150: 4.5, 200: 4.5, 250: 5.0})
    sb_g = make_grid(rhos_sb, {100: 4.5, 150: 4.5})
    sbg_g = make_grid(rhos_sb, {100: 3.5, 150: 4.0})
    pw_g = make_grid(rhos_sb, {100: 4.5, 150: 4.5})
    s050_g = make_grid((100, 150, 200), {100: 3.5, 150: 4.0, 200: 4.0})
    s100_g = make_grid((100, 150, 200), {100: 4.0, 150: 4.0, 200: 4.5})
    ldop_g = make_grid((50, 100, 150, 200), {50: 3.0, 100: 3.5, 150: 4.0, 200: 4.0})

    fail_a6 = {
        'CD2': (rhos_cd2, snrs, cd2_g),
        'SBdop': (rhos_sb, snrs, sb_g),
        'PWdop': (rhos_sb, snrs, pw_g),
        's050': ((100, 150, 200), snrs, s050_g),
        's100': ((100, 150, 200), snrs, s100_g),
        'ldop': ((50, 100, 150, 200), snrs, ldop_g),
    }
    fail_a8 = dict(fail_a6, SBGdop=(rhos_sb, snrs, sbg_g))

    res6 = stageA6.analyze_stageA6(fail_a6, stageA2.crossing, {}, boot_draws=200, boot_seed=20261125)
    res8 = a8.analyze_stageA8(fail_a8, stageA2.crossing, {}, boot_draws=200, boot_seed=20261125)

    # Exact parity on CD2 - SBdop contrast
    c6 = res6['primary']
    c8 = res8['secondary_contrasts']['CD2_minus_SBdop']
    assert abs(c6['point_db'] - c8['point_db']) < 1e-15
    assert abs(c6['ci95_db'][0] - c8['ci95_db'][0]) < 1e-15
    assert abs(c6['ci95_db'][1] - c8['ci95_db'][1]) < 1e-15

    # Primary CD2 - SBGdop should be GO
    assert res8['primary']['verdict'] == 'GO'
    assert res8['primary']['ci95_db'][0] >= 0.5


def test_paired_diagnostics_and_render():
    snrs = (300, 400)
    rows = []
    a6_map = {}
    # Create 4 keys per cell: 1 rescued, 1 regressed, 1 both_fail, 1 both_ok
    cases = [(True, False), (False, True), (True, True), (False, False)]
    for rho in (100, 150):
        for snr in snrs:
            for idx, (sb_f, sbg_f) in enumerate(cases):
                f = 41000 + idx
                s = 'U' if idx < 2 else 'G'
                a6_map[(f, s, rho, snr)] = dict(
                    sb_metric=0.08,
                    arms=dict(SBdop=dict(errors=10 if sb_f else 0)),
                )
                rows.append(dict(
                    frame=f, scenario=s, rho=rho, snr=snr,
                    sbg_cpu=2.0, sbg_metric=0.04, sbg_outlier_frac=0.0, sbg_abs_err=[0.04] * 8,
                    arms=dict(SBGdop=dict(syndrome=1 if sbg_f else 0, f0_errors=5 if sbg_f else 0, errors=5 if sbg_f else 0)),
                ))
    diag = a8.summarize_diagnostics(rows, snrs, a6_map)
    pt = diag['paired_vs_sbdop_totals']
    assert pt['n_keys'] == 16
    assert pt['rescued_sb_fail_to_sbg_ok'] == 4
    assert pt['regressed_sb_ok_to_sbg_fail'] == 4
    assert pt['both_fail'] == 4
    assert pt['both_ok'] == 4

    # Check censored '+inf' rendering
    sb_all_fail = np.ones((4, 2, 2, 2), dtype=bool)
    cd2_ok = np.zeros((4, 2, 4, 2), dtype=bool)
    cd2_ok[:, :, :, 0] = True
    an_res = a8.analyze_stageA8(
        {'CD2': ((100, 150, 200, 250), snrs, cd2_ok), 'SBGdop': ((100, 150), snrs, sb_all_fail), 'SBdop': ((100, 150), snrs, sb_all_fail)},
        stageA2.crossing,
        diag,
        boot_draws=20,
        boot_seed=20261125,
    )
    assert an_res['primary']['verdict'] == 'STOP'
    md = a8.render_results_md(dict(
        _config=dict(freeze_commit='b' * 40, rhos=[100, 150], snrs=list(snrs)),
        runtime=dict(total_core_hours=2.5, wall_seconds=300.0, cpu_cap_core_hours=8.2),
        analysis=an_res,
    ))
    assert 'STOP' in md and '+1' in md


if __name__ == '__main__':
    test_verdict_a8_boundaries()
    test_bootstrap_exact_parity_with_stageA6_and_go_branch()
    test_paired_diagnostics_and_render()
    print('ALL_STAGEA8_UNIT_TESTS_PASS')
