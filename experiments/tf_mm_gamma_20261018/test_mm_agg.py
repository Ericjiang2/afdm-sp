#!/usr/bin/env python
"""Self-test of mm_agg.py on synthetic rows (no receiver, no data): verdict boundaries, every verdict branch (CODE-CONSISTENT, SUSPECT, INCONCLUSIVE in three
ways), R-averaging, cluster structure, D_real independent of the verdict, EIV violation counts, integrity blocking, E-3 bit-identity comparison, determinism.
Usage: python test_mm_agg.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mm_agg as agg  # noqa: E402

EIV_OK = dict(n_points=101, n_viol=0, max_rel_drop=0.0, L_first=-10., L_last=10., n_prune_events=0, monotone=True)


def variant(nmse_db, n_pair=0, eiv=None):
    pairs = [dict(delay=10, dnu=.25, dn=.9, true_delay=True)] * n_pair
    return dict(n_atoms=8, atoms=[[10, .5, .3]], n_pair=n_pair, pairs=pairs, nmse=float(10 ** (nmse_db / 10)),
                sbl=dict(max_iter=100, iterations=100, converged=False, n_start=600, n_final=600, beta=5., jitter_events=0), eiv=eiv or dict(EIV_OK), seconds=2.5)


def make_rows(d_syn=-.5, d_real=.3, noise=.05, seed=1, reps=3, base_db=-12., eiv_viol_in=None, aux_reps=None):
    """Per-key synthetic D drawn around d_syn (key-level sd = noise), rep-level jitter 0 mean."""
    rng = np.random.default_rng(seed)
    rows = []
    for f in range(*agg.FRAMES):
        for sc in agg.SCENARIOS:
            cluster_shift = rng.normal() * noise
            for snr in agg.SNRS:
                key_d = d_syn + cluster_shift + rng.normal() * noise
                key_dr = d_real + rng.normal() * noise
                base = base_db + rng.normal() * .5
                syn = []
                for r in range(reps):
                    jit = rng.normal() * .2
                    syn.append(dict(rep=r, x_stats=dict(dev_ratio=1., frac_differs_from_hard=.1),
                                    **{'S-diag': variant(base + jit, 5), 'S-cov': variant(base + jit + key_d, 2), 'S-hard': variant(base - .3, 1), 'S-genie': variant(base - 3., 1)}))
                for s in syn:
                    if aux_reps is not None and s['rep'] >= aux_reps:
                        s.pop('S-hard'), s.pop('S-genie')
                row = dict(family='P1', scenario=sc, rho_permille=300, snr_centi_db=snr, frame=f, reps=reps,
                           stage1=dict(atoms=[[1, .5, .1]]), round1=dict(decoded_sha256='sha'), n_candidates_stage2=600, gamma_diag_rel_err=1e-16,
                           real={'S-diag': variant(base, 5), 'S-cov': variant(base + key_dr, 2)}, syn=syn, gen_seconds=.1,
                           seconds=dict(stage1_screen=.1, stage1_sbl=.4, round1_detect=.1, round1_decode=.03, stage2_screen=.3, total=36.))
                rows.append(row)
    if eiv_viol_in is not None:
        rows[eiv_viol_in]['real']['S-cov']['eiv'] = dict(EIV_OK, n_viol=3, max_rel_drop=1e-4, monotone=False)
        rows[eiv_viol_in]['syn'][1]['S-diag']['eiv'] = dict(EIV_OK, n_viol=1, max_rel_drop=2e-9, monotone=False)
    return rows


GATES = dict(all_pass=True)


def run(rows, gates=GATES, **kw):
    return agg.analyse(rows, gates, n_boot=2000, **kw)


def test_verdict_boundaries():
    V = agg.verdict
    assert V(-1., 0.) == 'CODE-CONSISTENT' and V(-1., -1e-12) == 'CODE-CONSISTENT'          # CI_hi <= 0 (non-strict)
    assert V(-1., 1e-12) == 'INCONCLUSIVE'
    assert V(.2 + 1e-12, 1.) == 'SUSPECT' and V(.2, 1.) == 'INCONCLUSIVE'                     # CI_lo > .2 (strict)
    assert V(.05, .15) == 'INCONCLUSIVE' and V(-.1, .5) == 'INCONCLUSIVE'
    assert V(.3, .1) in ('SUSPECT', 'INCONCLUSIVE')                                           # malformed CI never gives CODE-CONSISTENT
    assert V(-3., -2.) == 'CODE-CONSISTENT' and V(1., 2.) == 'SUSPECT'


def test_branches():
    r = run(make_rows(d_syn=-.6))
    assert r['interpretable'] and r['final_verdict'] == 'CODE-CONSISTENT' and r['quantities']['D']['ci_hi'] <= 0, r['quantities']['D']
    r = run(make_rows(d_syn=+.7))
    assert r['final_verdict'] == 'SUSPECT' and r['quantities']['D']['ci_lo'] > .2
    r = run(make_rows(d_syn=0., noise=.4))                                                   # CI straddles 0
    assert r['final_verdict'] == 'INCONCLUSIVE' and r['quantities']['D']['contains_0']
    r = run(make_rows(d_syn=+.1, noise=.02))                                                 # tight, positive but below the .2 dB bar
    q = r['quantities']['D']
    assert r['final_verdict'] == 'INCONCLUSIVE' and q['ci_lo'] > 0 and q['ci_hi'] < .2
    r = run(make_rows(d_syn=+.3, noise=.6))                                                  # point above .2 but CI_lo below
    q = r['quantities']['D']
    assert r['final_verdict'] == 'INCONCLUSIVE' and q['point'] > .2 and q['ci_lo'] <= .2


def test_report_items_do_not_enter_the_verdict():
    a = run(make_rows(d_syn=-.6, d_real=+.5))
    b = run(make_rows(d_syn=-.6, d_real=-.5))
    assert a['final_verdict'] == b['final_verdict'] == 'CODE-CONSISTENT'
    assert a['D_real_reproduces_E3_direction'] and not b['D_real_reproduces_E3_direction']
    assert a['quantities']['D_real']['point'] > .3 and b['quantities']['D_real']['point'] < -.3


def test_r_average_and_clusters():
    rows = make_rows(d_syn=-.2, reps=3)
    # replace the three draws of key 0 by known values: D per draw = 1.0, 2.0, 6.0  -> R-average 3.0
    for s, extra in zip(rows[0]['syn'], (1., 2., 6.)):
        s['S-diag'] = variant(-10.)
        s['S-cov'] = variant(-10. + extra)
    rows_s, syn_db, syn_pair, real_db, real_pair = agg.per_key_values(rows)
    i = [agg.key_of(r) for r in rows_s].index(agg.key_of(rows[0]))
    assert abs((syn_db['S-cov'] - syn_db['S-diag'])[i] - 3.0) < 1e-9
    q = agg.quantities(rows, n_boot=500)
    assert q['n_clusters'] == 100 and q['n_keys'] == 300 and q['n_boot'] == 500 and q['seed'] == 20261018
    assert 'U_600' in q['by_cell'] and q['by_cell']['G_800']['n'] == 50


def test_eiv_counts():
    r = run(make_rows(eiv_viol_in=3))
    t = r['eiv_monotonicity']
    assert t['real:S-cov']['runs_with_violation'] == 1 and t['real:S-cov']['violating_transitions'] == 3 and t['real:S-diag']['runs_with_violation'] == 0
    assert t['syn:S-diag']['runs_with_violation'] == 1 and t['syn:S-diag']['runs'] == 900 and t['real:S-cov']['runs'] == 300
    assert r['final_verdict'] in ('CODE-CONSISTENT', 'INCONCLUSIVE', 'SUSPECT')              # violations are reported, not a stop
    clean = run(make_rows())['eiv_monotonicity']
    assert all(x['violating_transitions'] == 0 for x in clean.values())


def test_integrity_blocks():
    rows = make_rows()
    for bad, why in ((rows[1:], 'missing key'), (rows + [rows[0]], 'duplicate')):
        r = run(bad)
        assert not r['interpretable'] and r['final_verdict'] is None and 'quantities' not in r, why
    err = make_rows()
    err[5] = dict(family='P1', scenario=err[5]['scenario'], rho_permille=300, snr_centi_db=err[5]['snr_centi_db'], frame=err[5]['frame'], status='error', error='boom')
    r = run(err)
    assert not r['interpretable'] and r['integrity']['n_error_rows'] == 1
    sm = make_rows()
    sm[0]['smoke'] = True
    assert not run(sm)['interpretable']
    miss = make_rows()
    miss[2]['syn'] = miss[2]['syn'][:2]
    assert not run(miss)['interpretable']
    bad_g = make_rows()
    bad_g[0]['gamma_diag_rel_err'] = 1e-3
    assert not run(bad_g)['interpretable']
    assert not run(make_rows(), gates=dict(all_pass=False))['interpretable']
    assert not run(make_rows(), gates=None)['interpretable']
    ok = run(make_rows())
    assert ok['interpretable'] and ok['integrity']['ok']
    # the operational tables are still produced for a blocked aggregate (cost, EIV) but nothing about D
    r = run(rows[1:])
    assert 'cost' in r and 'eiv_monotonicity' in r and 'quantities' not in r


def test_e3_match_and_determinism():
    rows = make_rows()
    row = rows[0]
    e3 = dict(stage1=dict(atoms=row['stage1']['atoms']), round1=dict(decoded_sha256='sha'), n_candidates_stage2=600,
              variants={'L-diag': dict(atoms=row['real']['S-diag']['atoms'], nmse=row['real']['S-diag']['nmse'], n_pair=5,
                                       sbl=dict(iterations=100, beta=5., converged=False)),
                        'L-cov': dict(atoms=row['real']['S-cov']['atoms'], nmse=row['real']['S-cov']['nmse'], n_pair=2,
                                      sbl=dict(iterations=100, beta=5., converged=False))})
    assert all(agg.e3_match(row, e3).values())
    e3['variants']['L-cov']['atoms'] = [[10, .5, float(np.nextafter(.3, 1.))]]                # one ulp apart is not "bit-identical"
    m = agg.e3_match(row, e3)
    assert m['S-cov_atoms'] is False and m['S-diag_atoms'] is True
    a, b = run(make_rows(), e3_rows={agg.key_of(row): e3}), run(make_rows(), e3_rows={agg.key_of(row): e3})
    assert a['quantities'] == b['quantities'] and a['reproduction_of_E3_rows']['keys_compared'] == 1


def test_aux_reps():
    rows = make_rows(d_syn=-.6, aux_reps=1)
    assert not run(rows)['interpretable']                                                    # the design (S-hard / S-genie on all draws) is violated
    r = agg.analyse(rows, GATES, n_boot=500, aux_reps=1)
    assert r['interpretable'] and r['final_verdict'] == 'CODE-CONSISTENT'
    assert r['census']['syn:S-genie']['runs'] == 300 and r['census']['syn:S-diag']['runs'] == 900
    assert r['eiv_monotonicity']['syn:S-hard']['runs'] == 300
    # the criterion only uses S-diag / S-cov: identical with and without the auxiliary draws
    full = agg.analyse(make_rows(d_syn=-.6), GATES, n_boot=500)
    assert full['quantities']['D'] == r['quantities']['D']
    bad = make_rows(d_syn=-.6, aux_reps=1)
    bad[0]['syn'][0].pop('S-genie')
    assert not agg.analyse(bad, GATES, n_boot=500, aux_reps=1)['interpretable']


def test_render():
    r = run(make_rows(d_syn=-.6, eiv_viol_in=2))
    md = agg.render_md(r)
    assert 'CODE-CONSISTENT' in md and 'EIV EM lower bound' in md
    blocked = agg.render_md(run(make_rows()[1:]))
    assert 'refuses interpretation' in blocked


if __name__ == '__main__':
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=HERE / 'out' / 'unit')
    a = ap.parse_args()
    passed = []
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
            passed.append(name)
            print('PASS', name)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'test_mm_agg.json').write_text(json.dumps(dict(passed=passed, all_pass=True), indent=1) + '\n')
    print('ALL AGG TESTS PASS')
