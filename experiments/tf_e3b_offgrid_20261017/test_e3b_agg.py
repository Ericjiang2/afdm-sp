#!/usr/bin/env python
"""Self-test of e3b_agg.py on synthetic rows (no receiver, no data): every branch of the frozen verdict (REVERSED, VANISHED, REDUCED, PERSISTS, MIXED),
the boundary behaviour of verdict(), the order of precedence, integrity blocking, rendering.   Usage: python test_e3b_agg.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3b_agg as agg  # noqa: E402
import e3b_lib as lib  # noqa: E402

ATOMS = [[10, .25, .5], [10, 1.5, .2]]
BASE_ON = {'L-hard': .12, 'L-diag': .110, 'L-cov': .149, 'L-genie': .10}


def refine_ok(o):
    zero_v = o in ('hard-off', 'genie-off')
    return dict(n_coord=6, n_accept=4, accepted_by_pass=[2, 1, 1], evals=60, max_evals_coord=16, n_moved=2, shift_abs_max=.1, shift_abs_mean=.05, monotone=True,
                value_recheck_equal=True, in_bounds=True, in_window=True, value_before=2.0, value_after=1.5, cond_Q=10.,
                gamma_abs_max=0.0 if zero_v else 1.0, gamma_offdiag_abs_max=0.0 if o != 'cov-off' else .3, gamma_diag_rel_err=None if zero_v else 1e-16)


def make(p_off, p_on=BASE_ON, seed=1, indep=False):
    """Synthetic E-3b rows and E-3 slim rows for the 2400 keys.  FERs are nested thresholds of one uniform per key (identical keys -> exactly paired);
    indep = independent uniforms for diag-off and cov-off."""
    rng = np.random.default_rng(seed)
    rows, on = [], {}
    for sc, rho, snr, f in lib.main_keys():
        u = rng.random()
        u2 = rng.random()
        key = (sc, rho, snr, f)
        variants = {}
        for o in lib.OFF:
            uu = u2 if (indep and o == 'cov-off') else u
            variants[o] = dict(info_errors=5 if uu < p_off[o] else 0, fer=int(uu < p_off[o]), n_atoms=2, atoms_ongrid=ATOMS, atoms=[[10, .3, .4], [10, 1.4, .1]],
                               n_pair=1, pairs=[dict(delay=10, dnu=1.1, dn=.1, true_delay=True)], nmse=.01, gamma_mode='full',
                               sbl=dict(iterations=40, converged=True, jitter_events=0), refine=refine_ok(o),
                               seconds=dict(columns=.1, sbl=1., refine=1., detect=.1, decode=.02, total=2.5))
        rows.append(dict(family='P1', scenario=sc, rho_permille=rho, snr_centi_db=snr, frame=f, variants=variants, n_candidates_stage2=600, gamma_diag_rel_err=1e-16,
                         stage1=dict(nmse=.05, jitter_events=0, converged=False, atoms=[[10, .5, .3]]), round1=dict(info_errors=3, decoded_sha256=f'sha-{key}'),
                         gen_seconds=.1, seconds=dict(stage1_screen=.1, stage1_sbl=.1, round1_detect=.1, round1_decode=.02, stage2_screen=.3, total=10.)))
        on[key] = dict(stage1_atoms=[[10, .5, .3]], round1_sha=f'sha-{key}', n_cand2=600,
                       variants={v: dict(fer=int(u < p_on[v]), info_errors=0, n_pair=1, nmse=.02, atoms=ATOMS, decoded_sha256='x', n_atoms=2) for v in lib.ONGRID.values()})
    return rows, on


def run(p_off, p_on=BASE_ON, **kw):
    rows, on = make(p_off, p_on, **kw)
    return agg.analyse(rows, on, None, n_boot=1000)


def off(hard=.12, diag=.110, cov=.149, genie=.10):
    return {'hard-off': hard, 'diag-off': diag, 'cov-off': cov, 'genie-off': genie}


def test_verdict_function():
    V = agg.verdict
    ci = lambda lo, hi: dict(ci_lo=lo, ci_hi=hi)
    pos, neg0 = ci(.001, .02), ci(-.001, .02)
    assert V(ci(-.05, -.001), pos) == 'REVERSED' and V(ci(-.05, 0.0), pos) == 'MIXED'                 # CI_hi(A_off) < 0 strictly
    assert V(ci(-.05, -.001), neg0) == 'MIXED'                                                         # needs CI_lo(Delta) > 0
    assert V(ci(-.004, .004), pos) == 'VANISHED' and V(ci(-.01, .01), pos) == 'VANISHED'                # closed interval [-.01, .01]
    assert V(ci(-.0101, .004), pos) == 'MIXED' and V(ci(-.004, .0101), pos) == 'MIXED'
    assert V(ci(-.004, .004), neg0) == 'MIXED'
    assert V(ci(.002, .03), pos) == 'REDUCED' and V(ci(.0, .03), pos) == 'MIXED'                       # CI_lo(A_off) > 0 strictly
    assert V(ci(.002, .03), neg0) == 'PERSISTS' and V(ci(.002, .03), ci(0.0, .02)) == 'PERSISTS'       # CI_lo(Delta) <= 0
    assert V(ci(-.005, .03), neg0) == 'MIXED' and V(ci(-.02, .02), pos) == 'MIXED'
    # precedence: REVERSED before VANISHED (CI inside the tolerance but entirely negative); VANISHED before REDUCED (CI_lo > 0 but inside the band)
    assert V(ci(-.009, -.001), pos) == 'REVERSED' and V(ci(.002, .009), pos) == 'VANISHED' and V(ci(.002, .0101), pos) == 'REDUCED'
    # exclusivity: every combination of a small grid yields exactly one label
    labels = {V(ci(a, b), ci(c, d)) for a in (-.05, -.01, 0., .002) for b in (-.002, .004, .01, .03) if a < b for c in (-.01, 0., .01) for d in (.02,) if c < d}
    assert labels <= {'REVERSED', 'VANISHED', 'REDUCED', 'PERSISTS', 'MIXED'} and len(labels) == 5


def test_branches():
    # A_on = +.039 in all cases below
    r = run(off(hard=.12, diag=.12, cov=.08))
    assert r['verdict'] == 'REVERSED' and r['quantities']['A_off']['ci_hi'] < 0 and r['quantities']['Delta']['ci_lo'] > 0 and 'SUPPORTED' in r['reading']
    r = run(off(diag=.110, cov=.110))
    assert r['verdict'] == 'VANISHED' and abs(r['quantities']['A_off']['point']) < 1e-12 and r['quantities']['Delta']['ci_lo'] > 0
    r = run(off(diag=.110, cov=.125))
    assert r['verdict'] == 'REDUCED' and r['quantities']['A_off']['ci_lo'] > 0 and r['quantities']['Delta']['ci_lo'] > 0 and 'PARTLY' in r['reading']
    r = run(off())
    assert r['verdict'] == 'PERSISTS' and r['quantities']['A_off']['ci_lo'] > 0 and r['quantities']['Delta']['ci_lo'] <= 0 and 'REJECTED' in r['reading']
    # MIXED (a): no advantage on-grid either -> A_off inside the band but Delta not > 0
    r = run(off(diag=.13, cov=.13), p_on={**BASE_ON, 'L-diag': .13, 'L-cov': .13})
    assert r['verdict'] == 'MIXED' and r['quantities']['Delta']['ci_lo'] <= 0
    # MIXED (b): noisy A_off (independent draws) straddling 0 and wider than the tolerance band
    r = run(off(diag=.110, cov=.110), indep=True)
    assert r['verdict'] == 'MIXED' and r['quantities']['A_off']['contains_0'] and (r['quantities']['A_off']['ci_hi'] > .01 or r['quantities']['A_off']['ci_lo'] < -.01)
    # points and pairing
    r = run(off())
    q = r['quantities']
    assert abs(q['A_on']['point'] - .039) < .01 and abs(q['A_off']['point'] - q['A_on']['point']) < 1e-12 and q['Delta']['point'] == 0.0
    assert r['mcnemar']['diag_off_better_than_cov_off']['log10_p'] < -5 and r['mcnemar']['cov_off_better_than_diag_off']['log10_p'] > -1
    assert r['n_units'] == 2400 and r['interpretable'] and r['final_verdict'] == 'PERSISTS' and r['integrity']['ok']
    # census / refinement / tables / crossings / cost are filled
    assert r['census']['off']['cov-off']['frac_pairs_dnu_lt_0p1'] == 0.0 and r['census']['off']['cov-off']['hist_dnu']['[1,inf)'] == 2400
    assert abs(r['refinement']['cov-off']['acceptance_rate'] - 4 / 6) < 1e-12 and set(r['crossings']) == {'U_300', 'G_300'}
    assert abs(r['cost']['total_core_hours'] - 2400 * 10.1 / 3600) < 1e-9
    assert len(agg.render_md(r)) > 1000


def test_integrity_blocking():
    rows, on = make(off())
    expected = set(lib.main_keys())

    def blocked(rows_, on_=on, **kw):
        res = agg.analyse(rows_, on_, None, n_boot=200, **kw)
        return (not res['interpretable']) and res['final_verdict'].startswith('NOT_INTERPRETABLE')

    assert agg.analyse(rows, on, None, n_boot=200)['interpretable']
    assert blocked(rows + [rows[0]])                                                                    # duplicate row
    assert blocked(rows[1:])                                                                            # missing key
    bad = [dict(r) for r in rows]
    bad[0] = dict(status='error', error='LinAlgError', scenario=rows[0]['scenario'], rho_permille=300, snr_centi_db=rows[0]['snr_centi_db'], frame=rows[0]['frame'])
    assert blocked(bad)                                                                                 # error row
    bad = [dict(r) for r in rows]
    bad[0]['variants'] = {k: v for k, v in rows[0]['variants'].items() if k != 'genie-off'}
    assert blocked(bad)                                                                                 # missing variant
    bad = [dict(r) for r in rows]
    bad[0]['smoke'] = True
    assert blocked(bad)                                                                                 # smoke row
    assert blocked(rows, {k: v for k, v in on.items() if k != lib.key_of(rows[0])})                     # no E-3 row for a key
    for field, change in (('stage1', lambda r: r['stage1'].__setitem__('atoms', [[1, 0., 0.]])),
                          ('round1', lambda r: r['round1'].__setitem__('decoded_sha256', 'other')),
                          ('atoms_ongrid', lambda r: r['variants']['cov-off'].__setitem__('atoms_ongrid', [[10, .25, .5]]))):
        bad = [dict(r) for r in rows]
        bad[0] = {**rows[0], 'stage1': dict(rows[0]['stage1']), 'round1': dict(rows[0]['round1']), 'variants': {k: dict(v) for k, v in rows[0]['variants'].items()}}
        change(bad[0])
        assert blocked(bad), field                                                                      # on-grid stage differs from the E-3 row
    for field, value in (('monotone', False), ('max_evals_coord', 17), ('in_bounds', False), ('in_window', False), ('value_recheck_equal', False)):
        bad = [dict(r) for r in rows]
        bad[0] = {**rows[0], 'variants': {k: {**v, 'refine': dict(v['refine'])} for k, v in rows[0]['variants'].items()}}
        bad[0]['variants']['diag-off']['refine'][field] = value
        assert blocked(bad), field                                                                      # refinement invariants
    bad = [dict(r) for r in rows]
    bad[0] = {**rows[0], 'variants': {k: {**v, 'refine': dict(v['refine'])} for k, v in rows[0]['variants'].items()}}
    bad[0]['variants']['hard-off']['refine']['gamma_abs_max'] = 1e-9                                    # hard / genie must have gamma exactly 0
    assert blocked(bad)
    bad = [dict(r) for r in rows]
    bad[0] = {**rows[0], 'variants': {k: {**v, 'refine': dict(v['refine'])} for k, v in rows[0]['variants'].items()}}
    bad[0]['variants']['diag-off']['refine']['gamma_offdiag_abs_max'] = 1e-9                             # diag mode keeps no off-diagonal
    assert blocked(bad)
    assert blocked(rows, manifest_bad=['rows_shard000.jsonl.gz']) and blocked(rows, e3_manifest_bad=['rows_shard003.jsonl.gz'])
    res = agg.analyse(rows, on, dict(all_pass=False), n_boot=200)                                        # gates not all passed
    assert not res['interpretable'] and res['final_verdict'].startswith('NOT_INTERPRETABLE') and res['verdict'] == 'PERSISTS'
    assert agg.analyse(rows, on, dict(all_pass=True), n_boot=200)['interpretable']


def test_determinism_and_boot():
    a, b = run(off(diag=.110, cov=.125)), run(off(diag=.110, cov=.125))
    assert a['quantities'] == b['quantities']                                                            # seed fixed -> identical CI
    assert a['quantities']['n_clusters'] == 400 and a['quantities']['seed'] == 20261017


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
            print(f'{name}: ok')
