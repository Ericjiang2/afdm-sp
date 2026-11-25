"""Unit tests for stageA7.py: 4-way verdict logic, ratio cluster bootstrap, fast NLL/gradient exactness, and rendering."""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stageA5  # noqa: E402
import stageA7 as a7  # noqa: E402


def _st(pt: float, lo: float, hi: float) -> dict:
    return dict(hits=int(round(pt * 38)), n=38, unique_frames=35, point=pt, ci95=[lo, hi])


def test_verdict_a7_all_four_branches():
    # 1. SEARCH: f_SB >= 0.80 (lb > 0.50) AND f_SBG_rescue >= 0.70 (lb > 0.50)
    assert a7.verdict_a7(
        _st(0.95, 0.85, 1.00),
        _st(0.85, 0.72, 0.95),
        _st(0.90, 0.78, 0.98),
        _st(1.00, 1.00, 1.00),
        _st(1.00, 1.00, 1.00),
    ) == 'SEARCH'

    # Boundary miss on SEARCH rescue lower bound -> UNCLEAR (neither MODEL nor INFO)
    assert a7.verdict_a7(
        _st(0.95, 0.85, 1.00),
        _st(0.71, 0.49, 0.85),
        _st(0.90, 0.78, 0.98),
        _st(1.00, 1.00, 1.00),
        _st(1.00, 1.00, 1.00),
    ) == 'UNCLEAR'

    # 2a. MODEL via low f_SB <= 0.50 while KD & code prefer truth >= 0.80 (lb > 0.50)
    assert a7.verdict_a7(
        _st(0.40, 0.25, 0.55),
        _st(0.20, 0.08, 0.35),
        _st(0.80, 0.65, 0.92),
        _st(0.95, 0.85, 1.00),
        _st(0.92, 0.80, 1.00),
    ) == 'MODEL'

    # 2b. MODEL via deeper non-PW SB sidelobe (f_SB high vs PW, but SBG reaches <= tbox+0.1 on >=50% yet rescues <=30%)
    assert a7.verdict_a7(
        _st(0.90, 0.78, 0.98),
        _st(0.25, 0.12, 0.40),
        _st(0.75, 0.60, 0.88),
        _st(0.95, 0.85, 1.00),
        _st(0.90, 0.76, 0.98),
    ) == 'MODEL'

    # Contrast: SBG fails to rescue AND fails to reach tbox (incomplete global search, NOT model flaw!) -> UNCLEAR
    assert a7.verdict_a7(
        _st(0.90, 0.78, 0.98),
        _st(0.25, 0.12, 0.40),
        _st(0.30, 0.15, 0.45),
        _st(0.95, 0.85, 1.00),
        _st(0.90, 0.76, 0.98),
    ) == 'UNCLEAR'

    # 3. INFO: KD <= 0.50 (ub < 0.75) OR code <= 0.50 (ub < 0.75)
    assert a7.verdict_a7(
        _st(0.30, 0.15, 0.45),
        _st(0.10, 0.02, 0.22),
        _st(0.50, 0.34, 0.66),
        _st(0.42, 0.26, 0.58),
        _st(0.39, 0.24, 0.55),
    ) == 'INFO'


def test_cluster_ratio_bootstrap_and_empty_guard():
    # Variable cluster sizes: frame 41000 has 3 keys (all hit), frames 41001..41019 have 1 key each (15 hit, 4 miss)
    rows = [dict(frame=41000, ok=True) for _ in range(3)]
    for f in range(41001, 41016):
        rows.append(dict(frame=f, ok=True))
    for f in range(41016, 41020):
        rows.append(dict(frame=f, ok=False))
    st = a7.cluster_ratio_bootstrap(rows, lambda r: r['ok'], boot_draws=500, boot_seed=20261125)
    assert st['hits'] == 18 and st['n'] == 22 and st['unique_frames'] == 20
    assert abs(st['point'] - 18.0 / 22.0) < 1e-12
    assert 0.5 < st['ci95'][0] <= st['point'] <= st['ci95'][1] <= 1.0

    try:
        a7.cluster_ratio_bootstrap([], lambda r: True)
        raise AssertionError('Expected ValueError on empty rows')
    except ValueError:
        pass


def test_fast_nll_and_grad_exactness_and_fallbacks():
    rng = np.random.default_rng(42)
    c1 = 0.00439453125
    # Test 1: Standard N=1024 distinct delays (activates fast block-tridiagonal path)
    n = 1024
    delays = np.array([5, 18, 31, 44, 59, 72, 86, 97], dtype=np.int64)
    geom = stageA5.precompute_delay_geometry(delays, n, c1)
    fgeom = a7.prepare_fast_geom(geom)
    assert fgeom['fast_ok'] is True
    p_t = rng.normal(0.0, 0.2, n) + 1j * rng.normal(0.0, 0.2, n)
    r = rng.normal(0.0, 1.0, n) + 1j * rng.normal(0.0, 1.0, n)
    spt = p_t[geom['cols']]
    th = np.concatenate([rng.uniform(-2.5, 2.5, 8), rng.normal(0.0, 0.3, 16)])
    vd, s2 = 0.85, 0.40

    nll_ref, gr_ref = stageA5.sb_nll_and_grad(th, geom, spt, r, vd, s2)
    nll_only = a7.sb_nll_only_fast(stageA5, th[:8], th[8:16] + 1j * th[16:24], fgeom, spt, r, vd, s2)
    # Poison _Cinv with NaNs before calling sb_nll_and_grad_fast to prove zero reads outside written cyclic-band blocks
    fgeom['_Cinv'].fill(np.nan + 1j * np.nan)
    nll_fg, gr_fg = a7.sb_nll_and_grad_fast(th, fgeom, spt, r, vd, s2, stageA5)
    assert abs(nll_only - nll_ref) < 1e-11
    assert abs(nll_fg - nll_ref) < 1e-11
    assert np.max(np.abs(gr_fg - gr_ref)) < 1e-11

    # Test 2: Co-delay pairs + small B < 64 (checks b_blk = max(B, 64) padding)
    delays_cd = np.array([12, 12, 19, 25, 25, 30, 33, 40], dtype=np.int64)
    geom_cd = stageA5.precompute_delay_geometry(delays_cd, n, c1)
    fgeom_cd = a7.prepare_fast_geom(geom_cd)
    assert fgeom_cd['fast_ok'] is True
    spt_cd = p_t[geom_cd['cols']]
    nll_ref2, gr_ref2 = stageA5.sb_nll_and_grad(th, geom_cd, spt_cd, r, vd, s2)
    nll_only2 = a7.sb_nll_only_fast(stageA5, th[:8], th[8:16] + 1j * th[16:24], fgeom_cd, spt_cd, r, vd, s2)
    nll_fg2, gr_fg2 = a7.sb_nll_and_grad_fast(th, fgeom_cd, spt_cd, r, vd, s2, stageA5)
    assert abs(nll_only2 - nll_ref2) < 1e-11
    assert abs(nll_fg2 - nll_ref2) < 1e-11
    assert np.max(np.abs(gr_fg2 - gr_ref2)) < 1e-11

    # Test 3: B == 0 fallback (all paths share single delay) and tiny N fallback
    geom_b0 = stageA5.precompute_delay_geometry(np.array([15, 15, 15], dtype=np.int64), 128, c1)
    fgeom_b0 = a7.prepare_fast_geom(geom_b0)
    assert fgeom_b0['fast_ok'] is False
    th3 = np.concatenate([rng.uniform(-1.5, 1.5, 3), rng.normal(0.0, 0.3, 6)])
    spt3 = p_t[:128][geom_b0['cols']]
    r3 = r[:128]
    nr3, gr3 = stageA5.sb_nll_and_grad(th3, geom_b0, spt3, r3, vd, s2)
    no3 = a7.sb_nll_only_fast(stageA5, th3[:3], th3[3:6] + 1j * th3[6:9], fgeom_b0, spt3, r3, vd, s2)
    nf3, gf3 = a7.sb_nll_and_grad_fast(th3, fgeom_b0, spt3, r3, vd, s2, stageA5)
    assert abs(no3 - nr3) < 1e-12 and abs(nf3 - nr3) < 1e-12 and np.max(np.abs(gf3 - gr3)) < 1e-12


def test_bits_to_qpsk_and_analyze_render():
    bits = np.array([0, 1, 0, 1, 0, 0, 1, 1], dtype=np.uint8)
    sym = a7.bits_to_qpsk(bits, vd=0.90)
    assert sym.shape == (4,)
    assert abs(np.mean(np.abs(sym) ** 2) - 0.90) < 1e-14

    # Synthetic 38-key confirmation readout -> SEARCH
    rows = []
    for i in range(38):
        rows.append(dict(
            frame=41000 + i,
            scenario='U' if i % 2 == 0 else 'G',
            rho=100 if i < 31 else 150,
            snr=450 if i % 3 != 0 else 500,
            total_cpu=8.0,
            sbg_cpu=2.5,
            sb_replay_diff=1e-12,
            sb_metric=0.08,
            sb_outlier_frac=0.25,
            sb_max_err=2.5,
            sbg_metric=0.04,
            sbg_outlier_frac=0.0,
            sbg_max_err=0.09,
            nll_sb=dict(at_sb=1150.0, at_tbox=1110.0, at_tfree=1110.0, at_sbg=1110.0,
                        delta_sb_minus_tbox=40.0, delta_sb_minus_sbg=40.0, delta_sbg_minus_tbox=0.0),
            nll_kd=dict(at_sb_box=1250.0, at_true_box=1000.0, at_kd_free=1000.0,
                        delta_sbbox_minus_tbox=250.0, kd_free_max_err=0.03),
            receiver=dict(
                sbdop=dict(f0_syndrome=10, f0_errors=50, final_syndrome=8, errors=40, joint_coded_nll=1300.0),
                sbgdop=dict(f0_syndrome=0, f0_errors=0, final_syndrome=0, errors=0 if i < 34 else 20, joint_coded_nll=1000.0),
                tbox=dict(f0_syndrome=0, f0_errors=0, final_syndrome=0, errors=0 if i < 35 else 20, joint_coded_nll=1000.0),
                ldop=dict(f0_syndrome=0, f0_errors=0, final_syndrome=0, errors=0, joint_coded_nll=999.0),
            ),
            indicators=dict(
                sb_prefers_tbox=True,
                sbg_rescues=(i < 34),
                sbg_reaches_tbox=True,
                kd_prefers_tbox=True,
                code_prefers_truth=True,
            ),
        ))
    an = a7.analyze_stageA7(rows, boot_draws=200, boot_seed=20261125)
    assert an['verdict'] == 'SEARCH'
    md = a7.render_results_md(dict(
        _config=dict(freeze_commit='a' * 40, conf_snrs=[450, 500]),
        runtime=dict(total_core_hours=0.12, wall_seconds=18.0, cpu_cap_core_hours=1.0),
        analysis=an,
    ))
    assert 'SEARCH' in md and '34/38' in md


if __name__ == '__main__':
    test_verdict_a7_all_four_branches()
    test_cluster_ratio_bootstrap_and_empty_guard()
    test_fast_nll_and_grad_exactness_and_fallbacks()
    test_bits_to_qpsk_and_analyze_render()
    print('ALL_STAGEA7_UNIT_TESTS_PASS')
