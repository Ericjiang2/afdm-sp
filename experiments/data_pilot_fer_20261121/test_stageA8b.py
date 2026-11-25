"""Unit tests for stageA8b.py: SNR grid merging, Haldane floor sensitivity, budget fallback, and stageA8 parity."""
from __future__ import annotations

import math
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stageA2  # noqa: E402
import stageA8  # noqa: E402
import stageA8b as a8b  # noqa: E402


def test_merge_rho_snrs_and_overlap_guard():
    base_snrs = (300, 400, 450, 500)
    new_snrs = (350, 375)
    b_arr = np.zeros((10, 2, 4), dtype=bool)
    b_arr[:, :, 0] = True
    n_arr = np.zeros((10, 2, 2), dtype=bool)
    n_arr[:5, :, 0] = True
    n_arr[:1, :, 1] = True

    m_snrs, m_arr = a8b.merge_rho_snrs(base_snrs, b_arr, new_snrs, n_arr)
    assert m_snrs == (300, 350, 375, 400, 450, 500)
    assert m_arr.shape == (10, 2, 6)
    assert np.array_equal(m_arr[:, :, 0], b_arr[:, :, 0])
    assert np.array_equal(m_arr[:, :, 1], n_arr[:, :, 0])
    assert np.array_equal(m_arr[:, :, 2], n_arr[:, :, 1])
    assert not m_arr[:, :, 3:].any()

    # Single-SNR fallback merge (375,)
    m1_snrs, m1_arr = a8b.merge_rho_snrs(base_snrs, b_arr, (375,), n_arr[:, :, 1:])
    assert m1_snrs == (300, 375, 400, 450, 500)
    assert m1_arr.shape == (10, 2, 5)

    try:
        a8b.merge_rho_snrs((300, 400), b_arr[:, :, :2], (350, 400), n_arr)
        raise AssertionError('Expected ValueError on overlapping SNRs')
    except ValueError:
        pass


def test_budget_cap_and_candidate_fallback():
    cap_nominal = a8b.compute_effective_run_cap_hours(0.03)
    assert cap_nominal == a8b.STAGE_CAP_HOURS
    assert a8b.PRIOR_CUMULATIVE_HOURS + 0.03 + cap_nominal < a8b.TOTAL_TASK_CAP_HOURS

    # When gate uses 0.55 h (hypothetical), remaining cap shrinks below STAGE_CAP_HOURS to protect 10.0 h ceiling
    cap_tight = a8b.compute_effective_run_cap_hours(0.55)
    assert cap_tight < a8b.STAGE_CAP_HOURS
    assert abs((a8b.PRIOR_CUMULATIVE_HOURS + 0.55 + cap_tight + a8b.SAFETY_RESERVE_HOURS) - 10.0) < 1e-12

    # Fast keys -> selects (350, 375); formula check: raw_h * 1.3 + 0.08
    cands_fast, sel_fast = a8b.select_candidate_snrs({350: 3.5, 375: 3.5}, effective_cap_hours=2.45)
    assert sel_fast is not None and sel_fast['new_snrs'] == [350, 375]
    exp_raw = (3.5 * 800 * 2) / 3600.0
    assert abs(cands_fast[0]['projected_hours_with_margin'] - (exp_raw * 1.3 + 0.08)) < 1e-12

    # Slower keys -> drops 350 and selects single-SNR fallback [375]
    _, sel_mid = a8b.select_candidate_snrs({350: 6.5, 375: 6.0}, effective_cap_hours=2.45)
    assert sel_mid is not None and sel_mid['new_snrs'] == [375]

    # Too slow even for [375] -> None (gate fails cleanly)
    _, sel_none = a8b.select_candidate_snrs({350: 12.0, 375: 12.0}, effective_cap_hours=2.45)
    assert sel_none is None


def test_crossing_haldane_and_empirical_brackets():
    snrs = (300, 350, 375, 400)
    fer_nz = np.array([0.50, 0.04, 0.005, 0.0])
    c_std = stageA2.crossing(fer_nz, snrs)
    c_hal = a8b.crossing_haldane(fer_nz, snrs)
    assert abs(c_std - c_hal) < 1e-14
    assert a8b.empirical_bracket_db(fer_nz, snrs) == [3.5, 3.75]

    fer_z = np.array([0.50, 0.04, 0.0, 0.0])
    c_std_z = stageA2.crossing(fer_z, snrs)
    c_hal_z = a8b.crossing_haldane(fer_z, snrs)
    assert 3.5 < c_std_z < c_hal_z < 3.75

    assert a8b.empirical_bracket_db(np.array([0.005, 0.0, 0.0, 0.0]), snrs) == ['-inf', 3.0]
    assert a8b.empirical_bracket_db(np.array([0.5, 0.2, 0.05, 0.02]), snrs) == [4.0, '+inf']
    assert math.isinf(a8b.crossing_haldane(np.array([0.005, 0.0, 0.0, 0.0]), snrs))
    assert math.isinf(a8b.crossing_haldane(np.array([0.5, 0.2, 0.05, 0.02]), snrs))


def test_parity_with_stageA8_and_cliff_falsification():
    n_f = 400
    base_snrs = (300, 400, 450, 500)
    dens_snrs = (300, 350, 375, 400, 450, 500)

    cd2 = np.zeros((n_f, 2, 4, 4), dtype=bool)
    cd2[:, :, :, 0] = True
    cd2[:32, :, :, 1] = True
    cd2[:3, :, 2, 2] = True
    cd2[:20, :, 0, 2] = True
    cd2[:12, :, 1, 2] = True
    cd2[:6, :, 3, 2] = True

    sbdop = np.zeros((n_f, 2, 2, 4), dtype=bool)
    sbdop[:, :, :, 0] = True
    sbdop[:20, :, :, 1] = True
    sbdop[:3, :, 1, 2] = True
    sbdop[:10, :, 0, 2] = True

    sbg_a8 = np.zeros((n_f, 2, 2, 4), dtype=bool)
    sbg_a8[:220, :, 0, 0] = True
    sbg_a8[:330, :, 1, 0] = True
    sbg_a8[:5, :, 1, 1] = True

    ldop_a2 = np.zeros((n_f, 2, 3, 4), dtype=bool)
    ldop_a2[:180, :, :, 0] = True

    res8 = stageA8.analyze_stageA8(
        {
            'CD2': ((100, 150, 200, 250), base_snrs, cd2),
            'SBdop': ((100, 150), base_snrs, sbdop),
            'SBGdop': ((100, 150), base_snrs, sbg_a8),
            'ldop': ((100, 150, 200), base_snrs, ldop_a2),
        },
        stageA2.crossing,
        {},
        boot_draws=200,
        boot_seed=20261125,
    )

    new_ok = np.zeros((n_f, 2, 2), dtype=bool)
    new_ok[:12, :, 0] = True
    new_ok[:1, :, 1] = True
    _, m_sbg_ok = a8b.merge_rho_snrs(base_snrs, sbg_a8[:, :, 0, :], (350, 375), new_ok)
    _, m_ld_ok = a8b.merge_rho_snrs(base_snrs, ldop_a2[:, :, 0, :], (350, 375), new_ok)

    grids_ok = {
        'CD2': a8b.to_rho_grid_map((100, 150, 200, 250), base_snrs, cd2),
        'SBdop': a8b.to_rho_grid_map((100, 150), base_snrs, sbdop),
        'SBGdop_A8': a8b.to_rho_grid_map((100, 150), base_snrs, sbg_a8),
        'SBGdop_dens': {100: (dens_snrs, m_sbg_ok), 150: (base_snrs, sbg_a8[:, :, 1, :])},
        'ldop_dens': {100: (dens_snrs, m_ld_ok), 150: (base_snrs, ldop_a2[:, :, 1, :]), 200: (base_snrs, ldop_a2[:, :, 2, :])},
    }
    diag_stub = {
        'rho100_densified_curve': {
            '350': dict(
                snr_db=3.5, source='stageA8b_new',
                sbg_doppler_mean=0.045, sbg_doppler_mean_U=0.044, sbg_doppler_mean_G=0.046,
                sbg_outlier_frac=0.10, sbg_outlier_frac_U=0.09, sbg_outlier_frac_G=0.11,
                sbg_U_f0_fail=20, sbg_U_fin_fail=12, sbg_G_f0_fail=20, sbg_G_fin_fail=12,
                sbg_total_f0_fer=0.05, sbg_total_fin_fer=0.03,
                ldop_U_f0_fail=15, ldop_U_fin_fail=12, ldop_G_f0_fail=15, ldop_G_fin_fail=12,
                ldop_total_f0_fer=0.0375, ldop_total_fin_fer=0.03,
                paired_vs_ldop=dict(
                    ldop_ok_sbg_fail=0, ldop_ok_sbg_fail_U=0, ldop_ok_sbg_fail_G=0,
                    ldop_fail_sbg_ok=0, ldop_fail_sbg_ok_U=0, ldop_fail_sbg_ok_G=0,
                    both_fail=24, both_ok=776,
                ),
            )
        }
    }
    res8b_ok = a8b.analyze_stageA8b(grids_ok, stageA2.crossing, diag_stub, boot_draws=200, boot_seed=20261125)
    ref_c8 = res8['primary']
    ref_c8b = res8b_ok['secondary_contrasts']['CD2_minus_SBGdop_A8_ref']
    assert abs(ref_c8['point_db'] - ref_c8b['point_db']) < 1e-15
    assert abs(ref_c8['ci95_db'][0] - ref_c8b['ci95_db'][0]) < 1e-15
    assert res8b_ok['primary']['verdict'] == 'GO'

    new_cliff = np.zeros((n_f, 2, 2), dtype=bool)
    new_cliff[:100, :, 0] = True
    new_cliff[:24, :, 1] = True
    _, m_sbg_cliff = a8b.merge_rho_snrs(base_snrs, sbg_a8[:, :, 0, :], (350, 375), new_cliff)
    grids_cliff = dict(grids_ok, SBGdop_dens={100: (dens_snrs, m_sbg_cliff), 150: (base_snrs, sbg_a8[:, :, 1, :])})
    res8b_cliff = a8b.analyze_stageA8b(grids_cliff, stageA2.crossing, diag_stub, boot_draws=200, boot_seed=20261125)
    assert res8['primary']['verdict'] == 'GO'
    assert res8b_cliff['primary']['verdict'] == 'STOP'

    md = a8b.render_results_md(dict(
        _config=dict(freeze_commit='c' * 40, new_snrs=[350, 375], merged_rho100_snrs=list(dens_snrs)),
        runtime=dict(total_core_hours=1.45, cumulative_task_core_hours=8.51, wall_seconds=180.0, cpu_cap_core_hours=2.45),
        analysis=res8b_ok,
    ))
    assert 'GO' in md and '3.50' in md and 'Sensitivity `SBGdop_dens(100) − ldop_dens(100)`' in md


if __name__ == '__main__':
    test_merge_rho_snrs_and_overlap_guard()
    test_budget_cap_and_candidate_fallback()
    test_crossing_haldane_and_empirical_brackets()
    test_parity_with_stageA8_and_cliff_falsification()
    print('ALL_STAGEA8B_UNIT_TESTS_PASS')
