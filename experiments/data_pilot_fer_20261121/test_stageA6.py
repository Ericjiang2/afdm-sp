"""Unit tests for stageA6.py: verdict thresholds, joint paired bootstrap, and outlier classification."""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stageA2  # noqa: E402
import stageA6 as a6  # noqa: E402


def test_verdict_boundaries():
    assert a6.verdict_a6(0.50, 0.90) == 'GO'
    assert a6.verdict_a6(0.5001, 0.80) == 'GO'
    assert a6.verdict_a6(0.4999, 0.80) == 'ERIC'
    assert a6.verdict_a6(0.10, 0.30) == 'ERIC'
    assert a6.verdict_a6(0.10, 0.2999) == 'STOP'
    assert a6.verdict_a6(-math.inf, 0.20) == 'STOP'
    assert a6.verdict_a6(-math.inf, math.inf) == 'ERIC'
    assert a6.verdict_a6(0.60, math.inf) == 'GO'
    assert a6._to_float_bound('+inf') == math.inf
    assert a6._to_float_bound('inf') == math.inf
    assert a6._to_float_bound('-inf') == -math.inf


def test_censored_and_empty_render():
    # Verify '+inf' censored CI handling in analyze_stageA6 and None-safe render_results_md
    n_f = 20
    snrs = (250, 300, 400)
    rhos = (100, 150)
    # SBdop never reaches <= 1% FER (all failures -> right-censored '+inf')
    sb_g = np.ones((n_f, 2, 2, 3), dtype=bool)
    cd2_g = np.zeros((n_f, 2, 4, 3), dtype=bool)
    cd2_g[:, :, :, 0] = True
    fail_by_arm = {
        'CD2': ((100, 150, 200, 250), snrs, cd2_g),
        'SBdop': (rhos, snrs, sb_g),
        'PWdop': (rhos, snrs, sb_g),
        's050': ((100, 150, 200), snrs, cd2_g[:, :, :3, :]),
        's100': ((100, 150, 200), snrs, cd2_g[:, :, :3, :]),
        'ldop': ((50, 100, 150, 200), snrs, cd2_g),
    }
    rows = [
        dict(
            frame=41000, scenario='U', rho=rho, snr=snr, pw_cpu=0.03, sb_cpu=9.0,
            sb_metric=0.05, sb_outlier_frac=0.0, pw_metric=0.09, pw_outlier_frac=0.0,
            sb_abs_err=[0.05] * 8, truth_power=[0.125] * 8,
            arms=dict(SBdop=dict(syndrome=0, f0_errors=0, errors=0), PWdop=dict(syndrome=0, f0_errors=0, errors=0)),
        )
        for rho in rhos for snr in snrs
    ]
    diag = a6.summarize_diagnostics(rows, snrs)
    an_res = a6.analyze_stageA6(fail_by_arm, stageA2.crossing, diag, boot_draws=50, boot_seed=20261125)
    assert an_res['primary']['verdict'] == 'STOP'
    md = a6.render_results_md(dict(
        _config=dict(freeze_commit='0' * 40, rhos=list(rhos), snrs=list(snrs)),
        runtime=dict(total_core_hours=1.0, wall_seconds=60.0, cpu_cap_core_hours=40.0),
        analysis=an_res,
    ))
    assert 'N/A' in md and 'STOP' in md


def test_joint_bootstrap_and_contrasts():
    # Synthetic 100-frame grid where CD2 crosses at 4.5 dB and SBdop crosses at 3.5 dB -> D = +1.0 dB -> GO
    n_f = 100
    snrs_cd2 = (300, 400, 450, 500)
    snrs_sb = (250, 300, 400, 450, 500)
    rhos_cd2 = (100, 150, 200, 250)
    rhos_sb = (100, 150)

    def make_grid(rhos, snrs, cross_by_rho):
        arr = np.zeros((n_f, 2, len(rhos), len(snrs)), dtype=bool)
        for ri, rho in enumerate(rhos):
            c_db = cross_by_rho[rho]
            for si, snr in enumerate(snrs):
                s_db = snr / 100.0
                # Exact 10% FER below cross, 0.1% (=0/100 -> floored 1e-4) above cross
                if s_db < c_db:
                    arr[:10, :, ri, si] = True
                elif s_db == c_db:
                    arr[:1, :, ri, si] = True
        return arr

    cd2_g = make_grid(rhos_cd2, snrs_cd2, {100: 5.0, 150: 4.5, 200: 4.5, 250: 5.0})
    sb_g = make_grid(rhos_sb, snrs_sb, {100: 3.5, 150: 4.0})
    pw_g = make_grid(rhos_sb, snrs_sb, {100: 4.0, 150: 4.0})
    s050_g = make_grid((100, 150, 200), snrs_sb, {100: 3.5, 150: 4.0, 200: 4.0})
    s100_g = make_grid((100, 150, 200), snrs_sb, {100: 4.0, 150: 4.0, 200: 4.5})
    ldop_g = make_grid((50, 100, 150, 200), snrs_sb, {50: 3.0, 100: 3.5, 150: 4.0, 200: 4.0})

    fail_by_arm = {
        'CD2': (rhos_cd2, snrs_cd2, cd2_g),
        'SBdop': (rhos_sb, snrs_sb, sb_g),
        'PWdop': (rhos_sb, snrs_sb, pw_g),
        's050': ((100, 150, 200), snrs_sb, s050_g),
        's100': ((100, 150, 200), snrs_sb, s100_g),
        'ldop': ((50, 100, 150, 200), snrs_sb, ldop_g),
    }
    res = a6.analyze_stageA6(fail_by_arm, stageA2.crossing, {}, boot_draws=200, boot_seed=20261125)
    # Confirm ldop ignores rho=50 and takes min over 100..200 (matching sameframe_cd2)
    assert res['best_rho']['ldop'] == 100
    assert res['primary']['verdict'] == 'GO'
    assert res['primary']['point_db'] > 0.7


def test_outlier_diagnostics():
    rows = [
        # Weak-only outlier (bottom 4 powers have error 0.5, top 4 have 0.02), F0 fail
        dict(
            frame=41000, scenario='U', rho=100, snr=400, pw_cpu=0.03, sb_cpu=9.0,
            sb_metric=0.04, sb_outlier_frac=0.125, pw_metric=0.09, pw_outlier_frac=0.25,
            sb_abs_err=[0.02, 0.02, 0.02, 0.02, 0.50, 0.01, 0.01, 0.01],
            truth_power=[0.4, 0.25, 0.15, 0.10, 0.04, 0.03, 0.02, 0.01],
            arms=dict(SBdop=dict(syndrome=5, f0_errors=10, errors=0), PWdop=dict(syndrome=5, f0_errors=10, errors=5)),
        ),
        # Strong outlier, F0 fail
        dict(
            frame=41001, scenario='G', rho=100, snr=400, pw_cpu=0.03, sb_cpu=11.0,
            sb_metric=0.12, sb_outlier_frac=0.125, pw_metric=0.14, pw_outlier_frac=0.25,
            sb_abs_err=[0.40, 0.02, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01],
            truth_power=[0.4, 0.25, 0.15, 0.10, 0.04, 0.03, 0.02, 0.01],
            arms=dict(SBdop=dict(syndrome=8, f0_errors=15, errors=12), PWdop=dict(syndrome=8, f0_errors=15, errors=15)),
        ),
        # No outlier, F0 pass
        dict(
            frame=41000, scenario='U', rho=150, snr=400, pw_cpu=0.03, sb_cpu=8.0,
            sb_metric=0.02, sb_outlier_frac=0.0, pw_metric=0.06, pw_outlier_frac=0.0,
            sb_abs_err=[0.02] * 8,
            truth_power=[0.4, 0.25, 0.15, 0.10, 0.04, 0.03, 0.02, 0.01],
            arms=dict(SBdop=dict(syndrome=0, f0_errors=0, errors=0), PWdop=dict(syndrome=0, f0_errors=0, errors=0)),
        ),
    ]
    diag = a6.summarize_diagnostics(rows, (400,))
    f0f = diag['sb_outlier_breakdown']['f0_errors_gt0_all_snrs']
    assert f0f['n'] == 2
    assert abs(f0f['any_outlier'] - 1.0) < 1e-12
    assert abs(f0f['weak_outlier'] - 0.5) < 1e-12
    assert abs(f0f['weak_only_outlier'] - 0.5) < 1e-12
    assert abs(f0f['strong_outlier'] - 0.5) < 1e-12
    f0ok = diag['sb_outlier_breakdown']['f0_errors_eq0_all_snrs']
    assert f0ok['n'] == 1 and f0ok['any_outlier'] == 0.0


if __name__ == '__main__':
    test_verdict_boundaries()
    test_censored_and_empty_render()
    test_joint_bootstrap_and_contrasts()
    test_outlier_diagnostics()
    print('ALL_STAGEA6_UNIT_TESTS_PASS')
