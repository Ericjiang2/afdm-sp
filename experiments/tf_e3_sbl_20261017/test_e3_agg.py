#!/usr/bin/env python
"""Self-test of e3_agg.py and e3_calib.py on synthetic rows (no receiver, no data): primitives, calibration rule, every branch of the five-way
verdict (ABSENT, NO-FIX, MECHANISM-ONLY, GENERAL, HARD-ONLY), X2 not evaluated without X1-diag, X3 needing both conditions, census, crossings,
integrity blocking.   Usage: python test_e3_agg.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3_agg as agg  # noqa: E402
import e3_calib  # noqa: E402

SNRS = (800, 900, 1000)
BASE_P = dict.fromkeys(agg.VARIANTS, .10)                 # probability of one same-delay pair per unit (nested via a shared uniform)
BASE_F = dict.fromkeys(agg.VARIANTS, .20)                 # FER (nested)


def make_rows(p, f, n_frames=300, seed=1, jitter=0, nonconv=0):
    rng = np.random.default_rng(seed)
    rows, frame = [], 4000
    for sc, rho in agg.CELLS:
        for i in range(n_frames):
            frame += 1
            w, u = rng.random(), rng.random()
            for snr in SNRS:
                variants = {}
                for v in agg.VARIANTS:
                    has = w < p[v]
                    pairs = [dict(delay=10, dnu=.05, dn=.99, true_delay=True)] if has else []
                    variants[v] = dict(info_errors=5 if u < f[v] else 0, fer=int(u < f[v]), n_atoms=8, atoms=[], n_pair=len(pairs), pairs=pairs, nmse=.01,
                                       sbl=dict(iterations=40, converged=True, n_start=300, n_final=9, beta=10., jitter_events=jitter),
                                       seconds=dict(columns=.01, sbl=.2, detect=.1, decode=.02, total=.4))
                rows.append(dict(family='P1', scenario=sc, rho_permille=rho, snr_centi_db=snr, frame=frame, variants=variants, n_candidates_stage2=600,
                                 stage1=dict(nmse=.05, jitter_events=0, converged=False, atoms=[[10, .5, .3]]),
                                 round1=dict(info_errors=3, decoded_sha256=f'sha-{sc}-{rho}-{snr}-{frame}'), gamma_diag_rel_err=1e-16, gen_seconds=.1,
                                 seconds=dict(stage1_screen=.1, stage1_sbl=.1, round1_detect=.1, round1_decode=.02, stage2_screen=.3, total=1.5)))
    return rows


def run(p, f, **kw):
    rows = make_rows(p, f, **kw)
    return agg.analyse(rows, None, None, n_boot=1000, expected={agg.key_of(r) for r in rows})


def with_(base, **over):
    return {**base, **over}


def test_primitives():
    x = np.array([1] * 8 + [0] * 2 + [1] * 5, bool)
    y = np.array([0] * 8 + [1] * 2 + [1] * 5, bool)
    m = agg.mcnemar(x, y)
    assert (m['b'], m['c']) == (8, 2) and abs(10 ** m['log10_p'] - 56 / 1024) < 1e-12 and not m['significant']
    assert -910 < agg.mcnemar_log10p(3094, 10) < -900 and agg.mcnemar_log10p(0, 0) == 0.0
    # verdict ordering and exclusivity
    V = agg.verdict
    assert V(False, False, None, False) == 'ABSENT' and V(False, True, None, True) == 'HARD-ONLY'
    assert V(True, False, False, True) == 'NO-FIX' and V(True, True, False, False) == 'NO-FIX' and V(True, False, None, True) == 'NO-FIX'
    assert V(True, False, True, False) == 'MECHANISM-ONLY' and V(True, True, True, False) == 'MECHANISM-ONLY'
    assert V(True, False, True, True) == 'GENERAL' and V(True, True, True, True) == 'GENERAL'
    # crossings
    assert agg.crossing([8., 9., 10.], [.5, .05, .0], [100, 100, 100]) is not None and 9.0 < agg.crossing([8., 9., 10.], [.5, .05, .0], [100, 100, 100]) < 10.0
    assert abs(agg.crossing([8., 9.], [.1, .001], [100000, 100000]) - 8.5) < 1e-9          # log-linear: 1e-1 -> 1e-3 crosses 1e-2 half way
    assert agg.crossing([8., 9.], [.005, .001], [100, 100]) == '<=8.0' and agg.crossing([8., 9.], [.5, .2], [100, 100]) is None


def test_calibration_rule():
    mono = {s: max(0., 1.0 - .12 * (s - 3)) for s in e3_calib.CAL_SNRS}      # 0.88 at 4 dB -> falls below .9 at 4 dB
    assert e3_calib.decide_grid(mono)['s0'] == 4 and e3_calib.decide_grid(mono)['grid_db'] == [4, 5, 6, 7, 8, 9]
    late = {s: (1.0 if s < 11 else .8) for s in e3_calib.CAL_SNRS}
    assert e3_calib.decide_grid(late) == dict(status='OK', s0=11, grid_db=[11, 12, 13, 14])     # truncated at 14 dB
    edge = {s: (1.0 if s < 14 else .9) for s in e3_calib.CAL_SNRS}
    assert e3_calib.decide_grid(edge) == dict(status='OK', s0=14, grid_db=[14])              # FER exactly .9 is informative
    dead = {s: 1.0 for s in e3_calib.CAL_SNRS}
    assert e3_calib.decide_grid(dead) == dict(status='UNINFORMATIVE', s0=None, grid_db=[])
    dead2 = {**dead, 14: .901}
    assert e3_calib.decide_grid(dead2)['status'] == 'UNINFORMATIVE'
    wiggle = {**{s: 1.0 for s in e3_calib.CAL_SNRS}, 5: .85, 14: .5}
    assert e3_calib.decide_grid(wiggle)['s0'] == 5                                          # literal smallest SNR with FER <= .9


def test_verdict_branches():
    # ABSENT: identical pair counts in every variant -> E_v = 0 exactly, CI [0, 0] contains 0
    absent = run(BASE_P, BASE_F)
    assert absent['criteria']['verdict'] == 'ABSENT' and absent['final_verdict'] == 'ABSENT' and absent['criteria']['X2'] is None
    assert absent['quantities']['E']['L-diag']['contains_0'] and agg.NOTE_CI0 in agg.render_md(absent)
    # HARD-ONLY: only the hard-decision dictionary produces phantoms
    hard = run(with_(BASE_P, **{'L-hard': .30}), BASE_F)
    assert hard['criteria']['verdict'] == 'HARD-ONLY' and hard['criteria']['X1_hard'] and not hard['criteria']['X1_diag'] and hard['criteria']['X2'] is None
    # NO-FIX: the full Gamma leaves the phantoms (R_ph = 1)
    nofix = run(with_(BASE_P, **{'L-diag': .30, 'L-cov': .30}), BASE_F)
    assert nofix['criteria']['verdict'] == 'NO-FIX' and nofix['criteria']['X1_diag'] and nofix['criteria']['X2'] is False
    # MECHANISM-ONLY: phantoms removed by the full Gamma (R_ph = 0) but FER unchanged
    mech = run(with_(BASE_P, **{'L-diag': .30}), BASE_F)
    assert mech['criteria']['verdict'] == 'MECHANISM-ONLY' and mech['criteria']['X2'] is True and mech['criteria']['X3'] is False
    # GENERAL: phantoms removed and FER improved (L-cov better than L-diag)
    general = run(with_(BASE_P, **{'L-diag': .30}), with_(BASE_F, **{'L-diag': .30, 'L-hard': .30}))
    assert general['criteria']['verdict'] == 'GENERAL' and general['criteria']['X3'] and general['criteria']['X3_mcnemar_significant']
    assert general['mcnemar']['cov_better_than_diag']['b'] > 0 and general['mcnemar']['cov_better_than_diag']['c'] == 0
    # X2 limit: R_ph exactly at the boundary .25 passes, above fails (E_cov = .25 E_diag  <=> p_cov = p_genie + .25 (p_diag - p_genie))
    edge = run(with_(BASE_P, **{'L-diag': .50, 'L-cov': .20}), BASE_F)       # E_diag = .40, E_cov = .10 -> .25 (sampling noise: CI upper > .25 is allowed to fail)
    assert edge['criteria']['X1_diag'] and edge['quantities']['R_ph']['evaluable']
    over = run(with_(BASE_P, **{'L-diag': .50, 'L-cov': .30}), BASE_F)        # ratio .5
    assert over['criteria']['X2'] is False and over['criteria']['verdict'] == 'NO-FIX'
    # X3 needs BOTH conditions
    q = dict(E={'L-diag': dict(ci_lo=.1), 'L-hard': dict(ci_lo=-.1)}, R_ph=dict(evaluable=True, ci_hi=.1),
             fer_diff_diag_minus_cov=dict(ci_lo=.01))
    ok = agg.criteria(q, dict(significant=True))
    assert ok['X3'] and ok['verdict'] == 'GENERAL'
    assert not agg.criteria(q, dict(significant=False))['X3'] and agg.criteria(q, dict(significant=False))['verdict'] == 'MECHANISM-ONLY'
    q2 = {**q, 'fer_diff_diag_minus_cov': dict(ci_lo=-.001)}
    assert not agg.criteria(q2, dict(significant=True))['X3'] and agg.criteria(q2, dict(significant=True))['verdict'] == 'MECHANISM-ONLY'
    q3 = {**q, 'R_ph': dict(evaluable=False, ci_hi=None)}
    assert agg.criteria(q3, dict(significant=True))['X2'] is False and agg.criteria(q3, dict(significant=True))['verdict'] == 'NO-FIX'
    # exclusivity of the five labels over a grid of boolean inputs
    labels = {agg.verdict(a, b, c, d) for a in (False, True) for b in (False, True) for c in (None, False, True) for d in (False, True)}
    assert labels == {'ABSENT', 'NO-FIX', 'MECHANISM-ONLY', 'GENERAL', 'HARD-ONLY'}


def test_census_integrity():
    out = run(with_(BASE_P, **{'L-diag': .30}), BASE_F)
    c = out['census']
    assert c['L-diag']['mean_n_pair'] > c['L-genie']['mean_n_pair'] and abs(c['L-cov']['excess_vs_genie']) < 1e-12 and abs(c['L-diag']['excess_vs_genie'] - .2) < .05
    assert c['L-diag']['hist_abs_DN']['[.8,1]'] == c['L-diag']['pairs'] and c['L-diag']['frac_pairs_on_true_delay'] == 1.0
    assert out['interpretable'] and not out['integrity']['problems'] and out['integrity']['n_rows'] == len(make_rows(BASE_P, BASE_F))
    assert set(out['crossings']) == {'U_300', 'U_500', 'G_300', 'G_500'} and all(set(v) == set(agg.VARIANTS) for v in out['crossings'].values())
    # grid-based expected keys and integrity blocking
    grid = dict(cells={'U_300': dict(status='OK', grid_db=[8, 9, 10]), 'U_500': dict(status='UNINFORMATIVE', grid_db=[]),
                       'G_300': dict(status='OK', grid_db=[8]), 'G_500': dict(status='OK', grid_db=[14])})
    k = agg.expected_keys(grid)
    assert len(k) == 400 * (3 + 0 + 1 + 1) and ('U', 300, 900, 4000) in k and ('U', 500, 800, 4000) not in k and ('G', 500, 1400, 4399) in k
    rows = make_rows(BASE_P, BASE_F, n_frames=5)
    want = {agg.key_of(r) for r in rows}
    bad = agg.analyse(rows[:-1], None, None, n_boot=100, expected=want)
    assert not bad['interpretable'] and bad['final_verdict'].startswith('NOT_INTERPRETABLE')
    rows[2]['gamma_diag_rel_err'] = 1e-3
    assert not agg.analyse(rows, None, None, n_boot=100, expected=want)['interpretable']
    rows = make_rows(BASE_P, BASE_F, n_frames=5)
    rows[1] = dict(family='P1', scenario='U', rho_permille=300, snr_centi_db=800, frame=4001, status='error', error='x')
    assert not agg.analyse(rows, None, None, n_boot=100, expected={agg.key_of(r) for r in rows})['interpretable']
    rows = make_rows(BASE_P, BASE_F, n_frames=5)
    assert not agg.analyse(rows, None, dict(all_pass=False), n_boot=100, expected={agg.key_of(r) for r in rows})['interpretable']



def test_iter_cap_diagnostics():
    rows = make_rows(BASE_P, BASE_F, n_frames=10)
    for i, r in enumerate(rows):
        r['stage1']['converged'] = (i % 4 == 0)                       # 25% of stage-1 runs meet the stop rule
        r['variants']['L-diag']['sbl']['converged'] = (i % 2 == 0)     # 50% for L-diag, 100% for the others
    out = agg.analyse(rows, None, None, n_boot=100, expected={agg.key_of(r) for r in rows})
    ic = out['iter_cap']
    assert abs(ic['stage1'] - .75) < 1e-12 and abs(ic['stage2']['L-diag'] - .5) < 1e-12 and ic['stage2']['L-cov'] == 0.0 and ic['stage2']['L-hard'] == 0.0
    assert 'SBL runs hitting max_iter' in agg.render_md(out)


def test_riter_sample():
    cal = e3_calib
    grid = {f'{sc}_{rho}': [8, 9, 10, 11, 12, 13] for sc, rho in agg.CELLS}
    keys = cal.riter_sample(grid)
    assert len(keys) == 200 and len(set(keys)) == 200 and keys == cal.riter_sample(grid)
    assert all(4000 <= k[3] < 4400 for k in keys)
    per = {}
    for k in keys:
        per[(k[0], k[1], k[2])] = per.get((k[0], k[1], k[2]), 0) + 1
    assert len(per) == 24 and set(per.values()) == {8, 9} and sum(1 for v in per.values() if v == 9) == 8      # 200 = 24 * 8 + 8
    assert keys != cal.riter_sample(grid, seed=1) and len(cal.riter_sample(grid, seed=1)) == 200
    assert agg.expected_keys(dict(cells={k: dict(status='OK', grid_db=v) for k, v in grid.items()})) >= set(keys)
    # an UNINFORMATIVE cell has no strata: 18 strata -> 200 = 18 * 11 + 2
    g2 = {**grid, 'U_500': []}
    k2 = cal.riter_sample(g2)
    assert len(k2) == 200 and not any(k[0] == 'U' and k[1] == 500 for k in k2)
    c2 = {}
    for k in k2:
        c2[(k[0], k[1], k[2])] = c2.get((k[0], k[1], k[2]), 0) + 1
    assert len(c2) == 18 and set(c2.values()) == {11, 12}
    assert cal.riter_sample({}) == []


def test_riter_flag_and_analysis():
    f = agg.riter_flag
    assert f(.30, .14) == 'budget-dependent' and f(.30, .1499) == 'budget-dependent'
    assert f(.30, .15) == 'not budget-dependent'                       # exactly 50% is not "< 50%"
    assert f(.30, .20) == 'not budget-dependent' and f(.30, .35) == 'not budget-dependent' and f(.30, -.01) == 'budget-dependent'
    assert f(0.0, 0.0).startswith('not applicable') and f(-.2, -.3).startswith('not applicable')
    # side-by-side analysis on synthetic rows
    p_main = with_(BASE_P, **{'L-diag': .30})                        # 100-iteration L-diag excess .20
    main = make_rows(p_main, BASE_F, n_frames=40)
    keys = {agg.key_of(r) for r in main}
    sub_keys = sorted(keys)[:120]

    def riter(p400, mutate=None):
        rows = [r for r in make_rows(with_(p_main, **p400), BASE_F, n_frames=40) if agg.key_of(r) in set(sub_keys)]
        for r in rows:
            r['variants'] = {v: x for v, x in r['variants'].items() if v in ('L-diag', 'L-cov')}
            for x in r['variants'].values():
                x['sbl']['iterations'], x['sbl']['converged'] = 400, False
            r['riter'] = True
        if mutate:
            mutate(rows)
        return rows
    flagged = agg.analyse_riter(main, riter({'L-diag': .15}))        # excess drops from .20 to .05 (< 50%)
    assert flagged['flag'] == 'budget-dependent' and flagged['x1_diag_label'] == 'budget-dependent' and flagged['n_matched'] == 120 and flagged['reused_pipeline_mismatches'] == 0
    d = flagged['variants']['L-diag']
    assert abs(d['iter100']['genie_excess'] - .20) < .06 and d['iter400']['genie_excess'] < .5 * d['iter100']['genie_excess']
    assert d['iter400']['cap_share'] == 1.0 and d['iter100']['cap_share'] == 0.0 and d['iter400']['mean_iterations'] == 400
    kept = agg.analyse_riter(main, riter({'L-diag': .30}))             # unchanged excess
    assert kept['flag'] == 'not budget-dependent' and kept['x1_diag_label'] is None
    mism = agg.analyse_riter(main, riter({}, mutate=lambda rows: rows[0]['round1'].update(decoded_sha256='other')))
    assert mism['reused_pipeline_mismatches'] == 1
    none = agg.analyse_riter(main, [])
    assert none['flag'].startswith('not applicable')
    # integrated into analyse() and rendered
    out = agg.analyse(main, None, None, n_boot=100, expected=keys, riter_rows=riter({'L-diag': .15}))
    assert out['riter']['flag'] == 'budget-dependent' and 'R-iter robustness check' in agg.render_md(out) and 'budget-dependent' in agg.render_md(out)
    assert 'riter' not in agg.analyse(main, None, None, n_boot=100, expected=keys)


if __name__ == '__main__':
    test_primitives()
    test_calibration_rule()
    test_verdict_branches()
    test_census_integrity()
    test_iter_cap_diagnostics()
    test_riter_sample()
    test_riter_flag_and_analysis()
    print('test_e3_agg: ALL PASS')
