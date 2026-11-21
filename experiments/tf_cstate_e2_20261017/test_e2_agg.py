#!/usr/bin/env python
"""Self-test of e2_agg.py on synthetic rows (no receiver, no data): primitives, every verdict branch of D1 (PASS and each FAIL item),
D2 (FULL / PARTIAL / NONE / MIXED / not evaluable), D3 (PRINCIPLE / HEURISTIC-SUFFICES / MIXED / UNINFORMATIVE via the information gate
and via missing C rows), census (incl. C true-multi-ray taps), integrity blocking.   Usage: python test_e2_agg.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2_agg as agg  # noqa: E402
import e2_calib  # noqa: E402

BASE = dict(A1=.60, A2=.10, A3=.35, A1g=.58, A2g=.55, A2n=.40, A5=.30, A7=.30)   # nested thresholds; PASS-shaped D1, PARTIAL-shaped D2


def make_units(rates, family='R', n_per_cell=400, seed=1, a2_doublet=.95, a1_doublet=.01, snrs=(450, 550, 650)):
    """Triggered rows only.  An arm succeeds iff a shared uniform u < rate (nested arms).  Doublet shares are controlled per arm."""
    rng = np.random.default_rng(seed)
    cells = (('U', 300), ('U', 500), ('G', 300), ('G', 500)) if family == 'R' else (('J4', 300), ('J4', 500))
    rows, frame = [], 3000 if family == 'R' else 0
    for scenario, rho in cells:
        for i in range(n_per_cell):
            u, v = rng.random(), rng.random()
            frame += 1
            r1d = [10, 20, 30, 40]
            arms = {}
            for a in agg.ARMS:
                ok = u < rates[a]
                fd, fn = list(r1d), [0., .5, 1., -1.]
                share = a2_doublet if a in ('A2', 'A2g') else a1_doublet if a == 'A1' else 0.
                if a in ('A2', 'A1') and v < share:
                    fd, fn = [10, 10, 30, 40], [0., .05, 1., -1.]          # doublet with |dnu| = .05 -> |D_N| ~ 1
                arms[a] = dict(status='ok', info_errors=0 if ok else 5, final_delays=fd, final_dopplers=fn, edits=[], seconds=.1, seconds_minus_f0=-.2,
                               **({'guard_ok': True} if a in agg.GUARDED else {}))
            truth = dict(delays=[10, 20, 30, 40], dopplers=[0., .5, 1., -1.])
            if family == 'C':
                truth = dict(delays=[10, 10, 20, 30, 40], dopplers=[0., .3, .5, 1., -1.], rays_per_tap=[2, 1, 1, 1], tap_delays=[10, 20, 30, 40])
            rows.append(dict(family=family, scenario=scenario, rho=rho / 1000, rho_permille=rho, snr_centi_db=snrs[i % len(snrs)], frame=frame,
                             triggered=True, f0=dict(syndrome=7, info_errors=5, seconds=.3), gen_seconds=.1, r1=dict(delays=r1d, dopplers=[0., .5, 1., -1.]),
                             truth=truth, arms=arms, g5_ok=True, guard_ok=True))
    return rows


def keys_of(rows):
    return {agg.key_of(r) for r in rows}


def run(rates_R, rates_C=None, **kw):
    R = make_units(rates_R, 'R', **{k: v for k, v in kw.items() if k in ('n_per_cell', 'a2_doublet', 'a1_doublet')})
    C = [] if rates_C is None else make_units(rates_C, 'C', seed=2)
    grid = None
    return agg.analyse(R, C, grid, n_boot=kw.get('n_boot', 1000), expected=(keys_of(R), keys_of(C) if C else None))


def with_rates(**over):
    return {**BASE, **over}


def test_primitives():
    x = np.array([1] * 8 + [0] * 2 + [1] * 5, bool)
    y = np.array([0] * 8 + [1] * 2 + [1] * 5, bool)
    m = agg.mcnemar(x, y)
    assert (m['b'], m['c']) == (8, 2) and abs(m['p'] - 56 / 1024) < 1e-12 and not m['significant']
    big = agg.mcnemar_log10p(3094, 10)
    assert -910 < big < -900   # the E-1 pooled K1: no float underflow
    assert agg.mcnemar_log10p(0, 0) == 0.0
    assert np.allclose(agg.e1_agg.holm([.01, .04, .03, .5]), [.04, .09, .09, .5])
    # census primitives: |D_N|, doublets, edit classes
    assert agg.dn(0.) == 1.0 and abs(agg.dn(.5) - abs(np.sin(np.pi * .5) / (1024 * np.sin(np.pi * .5 / 1024)))) < 1e-15
    assert agg.doublets([5, 5, 7], [0., 1., 2.])[0][0] == 5 and len(agg.doublets([5, 5, 5], [0., 1., 2.])) == 3
    cls = agg.classify_edits([10, 20, 30], [dict(step=0, slot=0, new=dict(delay=20, doppler=0.)), dict(step=1, slot=2, new=dict(delay=30, doppler=1.)),
                                            dict(step=2, slot=1, new=dict(delay=44, doppler=0.))], {20, 44})
    assert [c['category'] for c in cls] == ['shares', 'same_slot', 'new'] and cls[2]['in_truth'] and cls[0]['in_truth']


def test_calibration_rule():
    mono = {6: 1.0, 8: .99, 10: .93, 12: .6, 14: .3, 16: .1, 18: .05, 20: .02}
    assert e2_calib.decide_grid(mono) == dict(status='OK', s0=10, grid_db=[10, 12, 14, 16])
    late = {6: 1., 8: 1., 10: 1., 12: 1., 14: 1., 16: .99, 18: .9, 20: .8}
    assert e2_calib.decide_grid(late) == dict(status='OK', s0=18, grid_db=[18, 20])        # 20, 22, 24 capped at 20 and merged
    edge = {6: 1., 8: 1., 10: 1., 12: 1., 14: 1., 16: 1., 18: 1., 20: .95}
    assert e2_calib.decide_grid(edge) == dict(status='OK', s0=20, grid_db=[20])           # FER exactly .95 is informative
    dead = {6: 1., 8: 1., 10: 1., 12: 1., 14: 1., 16: 1., 18: 1., 20: .951}
    assert e2_calib.decide_grid(dead) == dict(status='UNINFORMATIVE', s0=None, grid_db=[])
    wiggle = {6: .94, 8: 1., 10: 1., 12: 1., 14: 1., 16: .9, 18: .5, 20: .1}
    assert e2_calib.decide_grid(wiggle)['s0'] == 6                                         # literal smallest SNR with FER <= .95
    early = {6: .5, 8: .4, 10: .3, 12: .2, 14: .1, 16: .1, 18: .1, 20: .1}
    assert e2_calib.decide_grid(early) == dict(status='OK', s0=6, grid_db=[6, 8, 10, 12])


def test_d1():
    out = run(BASE)
    d1 = out['verdicts']['D1']
    assert d1['verdict'] == 'PASS' and not d1['failed'], d1
    # (a) fails: A7 almost as good as A1 -> F7 CI_lo < .10
    d1 = run(with_rates(A7=.58))['verdicts']['D1']
    assert d1['verdict'] == 'FAIL' and d1['failed'] == ['a_F5_F7_ci_lo_ge_.10'], d1
    # (b) fails: A2 not below A5
    d1 = run(with_rates(A2=.40))['verdicts']['D1']
    assert d1['verdict'] == 'FAIL' and 'b_S_Gamma_ci_lo_gt_1' in d1['failed'], d1['failed']
    # (c) fails: swaps are not where the gain is (A3 close to A1)
    d1 = run(with_rates(A3=.57))['verdicts']['D1']
    assert d1['verdict'] == 'FAIL' and d1['failed'] == ['c_S_swap_ci_lo_ge_.5'], d1['failed']
    # (d) fails: A2 does not create doublets
    d1 = run(BASE, a2_doublet=.5)['verdicts']['D1']
    assert d1['verdict'] == 'FAIL' and d1['failed'] == ['d_doublet_share_A2_ge_.80_A1_le_.05'], d1['failed']
    # (d) fails: A1 creates too many
    d1 = run(BASE, a1_doublet=.2)['verdicts']['D1']
    assert d1['verdict'] == 'FAIL' and d1['failed'] == ['d_doublet_share_A2_ge_.80_A1_le_.05'], d1['failed']
    # not evaluable (R_A1 == R_A5): every ratio item unsatisfied, FAIL
    d1 = run(with_rates(A5=.60))['verdicts']['D1']
    assert d1['verdict'] == 'FAIL' and 'b_S_Gamma_ci_lo_gt_1' in d1['failed'] and 'c_S_swap_ci_lo_ge_.5' in d1['failed']


def test_d2():
    assert run(with_rates(A2g=.60))['verdicts']['D2']['verdict'] == 'PHANTOM-FULL'            # G = 1
    assert run(with_rates(A2g=.35))['verdicts']['D2']['verdict'] == 'PHANTOM-PARTIAL'         # G = .5
    assert run(with_rates(A2g=.10))['verdicts']['D2']['verdict'] == 'PHANTOM-NONE'            # identical vectors: G = 0, CI [0, 0]
    mixed = run(with_rates(A2g=.15), n_per_cell=400)['verdicts']['D2']                        # G = .1: CI straddles .10
    assert mixed['verdict'] == 'MIXED' and mixed['note'] is None, mixed
    over = run(with_rates(A2g=.70))['verdicts']['D2']                                          # guard better than full Gamma: G > 1 reported as is
    assert over['verdict'] == 'PHANTOM-FULL' and over['G']['point'] > 1
    ne = run(with_rates(A2=.60))['verdicts']['D2']                                              # R_A1 == R_A2: denominator zero
    assert ne['verdict'] == 'MIXED' and 'not evaluable' in ne['note']
    # pure-function branches
    def qG(lo, hi):
        return {'ratio': {'G': dict(evaluable=True, ci_lo=lo, ci_hi=hi, point=.5)}}
    assert agg.d2_verdict(qG(.90, 1.2))['verdict'] == 'PHANTOM-FULL' and agg.d2_verdict(qG(.89, 1.2))['verdict'] == 'PHANTOM-PARTIAL'
    assert agg.d2_verdict(qG(.11, .5))['verdict'] == 'PHANTOM-PARTIAL' and agg.d2_verdict(qG(.10, .5))['verdict'] == 'MIXED'
    assert agg.d2_verdict(qG(-.2, .10))['verdict'] == 'PHANTOM-NONE' and agg.d2_verdict(qG(-.2, .11))['verdict'] == 'MIXED'


def test_d3():
    R_free = with_rates(A1g=.60)                      # guard costs nothing without true co-delay rays: R_A1 - R_A1g == 0 exactly
    C_cost = with_rates(A1g=.40, A2g=.45)             # in C the guard costs (A1g < A1) and full Gamma beats the guard (A2g < A1)
    principle = run(R_free, C_cost)['verdicts']['D3']
    assert principle['verdict'] == 'PRINCIPLE' and principle['D3a'] and principle['D3b'] and principle['D3c'], principle
    C_same = with_rates(A1g=.60, A2g=.60)             # guard as good as full Gamma in C: identical vectors
    heur = run(R_free, C_same)['verdicts']['D3']
    assert heur['verdict'] == 'HEURISTIC-SUFFICES' and not heur['D3b'], heur
    R_cost = with_rates(A1g=.45)                      # D3a false: guard already costs in R
    mixed = run(R_cost, C_cost)['verdicts']['D3']
    assert mixed['verdict'] == 'MIXED' and not mixed['D3a'], mixed
    C_mid = with_rates(A1g=.60, A2g=.45)              # D3b false (no cost of the guard) but A2g is far below A1: neither principle nor heuristic
    assert run(R_free, C_mid)['verdicts']['D3']['verdict'] == 'MIXED'
    # information gate: A1 succeeds in fewer than 100 C units -> UNINFORMATIVE although the contrasts would say PRINCIPLE
    C_tiny = with_rates(A1=.03, A1g=.02, A2g=.01, A2=.0, A3=.0, A5=.0, A7=.0, A2n=.0)
    gated = run(R_free, C_tiny)['verdicts']['D3']
    assert gated['verdict'] == 'UNINFORMATIVE' and gated['info_gate']['passed'] is False and gated['info_gate']['a1_rescued_units'] < 100, gated
    # no C rows at all (both rho UNINFORMATIVE in the calibration)
    assert run(R_free, None)['verdicts']['D3']['verdict'] == 'UNINFORMATIVE'


def test_census_and_integrity():
    out = run(BASE)
    cen = out['R']['census']
    assert cen['r1_duplicate_delay_units'] == 0 and cen['units_with_truth_duplicate_delays'] == 0
    assert .9 < cen['arms']['A2']['frac_units_with_doublet'] <= 1. and cen['arms']['A1']['frac_units_with_doublet'] < .05
    assert cen['arms']['A2']['hist_abs_DN']['[.8,1]'] == cen['arms']['A2']['pairs'] and cen['arms']['A5']['units_with_doublet'] == 0
    C = run(BASE, BASE)['C']
    a1 = C['census']['arms']['A1']
    assert a1['pairs'] > 0 and a1['frac_doublet_pairs_on_true_multiray_tap'] == 1.0 and a1['frac_doublet_units_on_true_multiray_tap'] == 1.0   # delay 10 is the 2-ray tap
    assert C['census']['units_with_truth_duplicate_delays'] == C['n_units'] and C['census']['units_with_true_multiray_tap'] == C['n_units']
    assert out['interpretable'] and not out['R']['integrity']['problems']
    # integrity: missing guard flag / failing g5 / key mismatch block interpretation
    R = make_units(BASE, 'R', n_per_cell=20)
    R[3]['guard_ok'] = False
    bad = agg.analyse(R, [], None, n_boot=100, expected=(keys_of(R), None))
    assert not bad['interpretable'] and bad['R']['integrity']['checks']['guard_ok'] == 1
    R2 = make_units(BASE, 'R', n_per_cell=20)
    R2[0]['g5_ok'] = False
    assert not agg.analyse(R2, [], None, n_boot=100, expected=(keys_of(R2), None))['interpretable']
    R3 = make_units(BASE, 'R', n_per_cell=20)
    assert not agg.analyse(R3[:-1], [], None, n_boot=100, expected=(keys_of(R3), None))['interpretable']
    assert not agg.analyse(R3, [], None, gates=dict(all_pass=False), n_boot=100, expected=(keys_of(R3), None))['interpretable']
    md = agg.render_md(out)
    assert agg.NOTE_CI0 in md and 'D1' in md and 'D2' in md and 'D3' in md and 'Co-delay census' in md


def test_expected_keys():
    assert len(agg.expected_keys('R')) == 2 * 2 * 8 * 1000
    grid = dict(rho={'0.3': dict(status='OK', grid_db=[8, 10, 12, 14]), '0.5': dict(status='UNINFORMATIVE', grid_db=[])})
    k = agg.expected_keys('C', grid)
    assert len(k) == 4 * 1000 and all(x[1] == 300 for x in k) and ('J4', 300, 800, 0) in k


if __name__ == '__main__':
    test_primitives()
    test_calibration_rule()
    test_expected_keys()
    test_d1()
    test_d2()
    test_d3()
    test_census_and_integrity()
    print('test_e2_agg: ALL PASS')
