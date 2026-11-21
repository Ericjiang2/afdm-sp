#!/usr/bin/env python
"""Self-test of e1_agg.py on synthetic rows (no receiver, no data): primitives, the section-10 verdict rule (KILL via J3a, KILL via
J3b, J1, J2, MIXED, >1% degenerate resamples), integrity/gate blocking, per-cell reverse flags, secondary subset.
Usage: python test_e1_agg.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e1_agg as agg  # noqa: E402

SNRS = (450, 500, 550, 600, 650, 700, 750, 800)


def make_rows(rates, n_per_cell=300, seed=1):
    """rates: arm -> success probability.  Arms succeed iff a shared uniform u < rate, so lower-rate arms are nested in higher-rate ones
    (one-sided discordance); every frame is its own cluster."""
    rng = np.random.default_rng(seed)
    rows, frame = [], 0
    for scenario, rho in agg.CELLS:
        for i in range(n_per_cell):
            u = rng.random()
            frame += 1
            arms = {}
            for a in agg.ARMS:
                ok = u < rates[a]
                arms[a] = dict(status='ok', info_errors=0 if ok else 7, n_support_changes=int(not ok), n_delay_replacements=0, n_edits=0,
                               edits=[], top5_step1=[], seconds=.1, seconds_minus_f0=-.2 if a == 'A7' else 0.,
                               stages=dict(tf=.04, ldpc=.01, geometry_setup=.0, message_handling=.0, y_transform=.0, channel_construction=.0))
            rows.append(dict(scenario=scenario, rho_permille=rho, snr_centi_db=SNRS[i % len(SNRS)], frame=frame, g4a_ok=True, g5_ok=True,
                             f0_matches_ledger=True, a1_matches_ledger=True, f0=dict(info_errors=5, seconds=.3), gen_seconds=.15, arms=arms))
    return rows


def test_primitives():
    x = np.array([1] * 8 + [0] * 2 + [1] * 5, bool)
    y = np.array([0] * 8 + [1] * 2 + [1] * 5, bool)
    r = agg.mcnemar_greater(x, y)
    assert (r['b'], r['c'], r['discordant']) == (8, 2, 10)
    assert abs(r['p'] - 56 / 1024) < 1e-15, r
    assert agg.mcnemar_greater(x, x)['p'] == 1.0
    assert agg.mcnemar_greater(y, x)['p'] > .9
    assert np.allclose(agg.holm([.01, .04, .03, .5]), [.04, .09, .09, .5])
    # ratio quantities: ladder shares telescope to 1 (point and per resample); NaN where Delta_geo <= 0
    R = dict(A1=.9, A2=.8, A3=.7, A4=.6, A5=.3, A6=.5, A7=.6)
    st = agg.ratio_stats(R)
    assert abs(st['S_swap'] + st['S_local'] + st['S_refit'] - 1) < 1e-12
    assert abs(st['S_Gamma'] - .1 / .6) < 1e-12 and abs(st['F5'] - .6 / .9) < 1e-12 and abs(st['F7'] - .3 / .9) < 1e-12
    assert abs(st['S_Gamma_noswap'] - .1 / .6) < 1e-12
    Rv = {k: np.array([v, v, v]) for k, v in R.items()}
    Rv['A5'] = np.array([.3, .95, .3])  # second resample: Delta_geo < 0 (F5 <= 0 is defined; S_Gamma and the ladder are not)
    Rv['A1'] = np.array([.9, .9, .0])   # third resample: R_A1 = 0 (F5, F7 undefined; Delta_geo <= 0)
    sv = agg.ratio_stats(Rv)
    assert np.isfinite(sv['F5'][0]) and sv['F5'][1] < 0 and np.isfinite(sv['F7'][1]) and np.isnan(sv['S_Gamma'][1]) and np.isnan(sv['S_swap'][1])
    assert np.isnan(sv['F5'][2]) and np.isnan(sv['F7'][2]) and np.isnan(sv['S_Gamma'][2])
    # bootstrap: fixed seed reproducible; identical arms -> degenerate difference CI exactly [0, 0]
    s = {a: np.zeros(240, bool) for a in agg.ARMS}
    s['A1'][:216] = True
    s['A2'][:60] = True
    for a in ('A3', 'A4', 'A5', 'A6', 'A7'):
        s[a] = s['A2'].copy()
    ids = [str(i // 2) for i in range(240)]
    b1 = agg.bootstrap_summary(s, ids, 2000, 3)
    b2 = agg.bootstrap_summary(s, ids, 2000, 3)
    assert b1 == b2
    d = b1['differences']['A2-A5']
    assert d['ci_contains_0'] and d['ci_lo'] == 0 == d['ci_hi']
    d = b1['differences']['A1-A2']
    assert not d['ci_contains_0'] and d['ci_lo'] < d['diff'] < d['ci_hi'] and abs(d['diff'] - 156 / 240) < 1e-12


def test_verdict_rule():
    def rat(s_gamma, f5, f7):
        return {'S_Gamma': dict(ci_lo=s_gamma[0], ci_hi=s_gamma[1]), 'F5': dict(ci_lo=0., ci_hi=f5), 'F7': dict(ci_lo=0., ci_hi=f7)}
    sig = lambda *ks: {k: k in ks for k in ('K1', 'K2', 'K3')}  # noqa: E731
    v = agg.verdict(sig('K1', 'K2', 'K3'), rat((.2, .5), .9, .08), True, True)
    assert v['verdict'] == 'KILL' and v['fired'] == ['J3b'] and v['J3b'] and not v['J3a'] and v['J1'] is None and v['J2'] is None
    v = agg.verdict(sig('K1', 'K2', 'K3'), rat((.2, .5), .099, .9), True, True)
    assert v['verdict'] == 'KILL' and v['fired'] == ['J3a']
    v = agg.verdict(sig(), rat((.0, .0), .05, .05), True, True)
    assert v['verdict'] == 'KILL' and v['fired'] == ['J3a', 'J3b']
    assert agg.verdict(sig('K1', 'K2'), rat((.10, .5), .9, .9), True, True)['verdict'] == 'J1'      # CI_lower(S_Gamma) >= delta
    assert agg.verdict(sig('K1', 'K2'), rat((.09, .5), .9, .9), True, True)['verdict'] == 'MIXED'
    assert agg.verdict(sig('K1'), rat((.2, .5), .9, .9), True, True)['verdict'] == 'MIXED'           # K2 missing
    assert agg.verdict(sig('K2', 'K3'), rat((-.1, .0999), .9, .9), True, True)['verdict'] == 'J2'    # CI_upper(S_Gamma) < delta
    assert agg.verdict(sig('K2', 'K3'), rat((-.1, .10), .9, .9), True, True)['verdict'] == 'MIXED'
    assert agg.verdict(sig('K2'), rat((-.1, .05), .9, .9), True, True)['verdict'] == 'MIXED'         # K3 missing
    # KILL needs only kill_evaluable: S_Gamma/ladder not evaluable does not block it
    k = agg.verdict(sig(), rat((None, None), .0, .9), True, False)
    assert k['verdict'] == 'KILL' and k['fired'] == ['J3a'] and not k['sgamma_evaluable']
    # kill not evaluable -> MIXED with a note naming the kill criteria, even if the (undefined) CIs would say KILL
    nk = agg.verdict(sig('K1', 'K2', 'K3'), rat((.2, .5), .01, .01), False, True)
    assert nk['verdict'] == 'MIXED' and nk['J3'] is None and 'kill criteria' in nk['note'] and 'S_Gamma' not in nk['note']
    # kill evaluable but not fired, S_Gamma not evaluable -> MIXED naming S_Gamma
    ns = agg.verdict(sig('K1', 'K2', 'K3'), rat((.2, .5), .9, .9), True, False)
    assert ns['verdict'] == 'MIXED' and ns['J3'] is False and ns['J1'] is None and 'S_Gamma' in ns['note'] and 'kill criteria' not in ns['note']
    both = agg.verdict(sig(), rat((.2, .5), .9, .9), False, False)
    assert both['verdict'] == 'MIXED' and 'kill criteria' in both['note'] and 'S_Gamma' in both['note']


def run(rates, **kw):
    return agg.analyse(make_rows(rates), n_boot=kw.pop('n_boot', 1000), **kw)


def test_end_to_end():
    base = dict(A1=.95, A2=.70, A3=.6, A4=.5, A5=.3, A6=.4, A7=.4)
    j1 = run(base)
    assert j1['criteria']['verdict'] == 'J1' and j1['final_verdict'] == 'J1' and j1['interpretable'], j1['criteria']
    assert j1['primary_mcnemar']['K1']['significant'] and j1['primary_mcnemar']['K2']['significant']
    assert j1['primary_mcnemar']['K4']['b'] > 0  # K4 reported
    # J2: A1 == A2 >> A5, A7
    j2 = run({**base, 'A2': .95})
    assert j2['criteria']['verdict'] == 'J2', j2['criteria']
    # KILL via J3a: A1 barely above A5 but robustly > 0 (Delta_geo CI excludes 0), A7 clearly lower
    k5 = run(dict(A1=.90, A2=.80, A3=.88, A4=.8, A5=.86, A6=.86, A7=.5))
    assert k5['criteria']['verdict'] == 'KILL' and k5['criteria']['fired'] == ['J3a'], (k5['criteria'], k5['bootstrap']['ratios'])
    # KILL via J3b: A7 (third F0 round) matches A1, A5 far lower
    k7 = run(dict(A1=.90, A2=.80, A3=.7, A4=.6, A5=.3, A6=.4, A7=.86))
    assert k7['criteria']['verdict'] == 'KILL' and k7['criteria']['fired'] == ['J3b'], (k7['criteria'], k7['bootstrap']['ratios'])
    # MIXED: S_Gamma point = delta, CI straddles it
    mixed = run(dict(A1=.90, A2=.84, A3=.7, A4=.6, A5=.3, A6=.4, A7=.4))
    assert mixed['criteria']['verdict'] == 'MIXED' and mixed['criteria']['kill_evaluable'] and mixed['criteria']['sgamma_evaluable'], (mixed['criteria'], mixed['bootstrap']['ratios']['S_Gamma'])
    # Delta_geo == 0 in every resample (A1 == A5, R_A1 > 0): F5 = 0 -> KILL via J3a; S_Gamma is not evaluable but does not block KILL
    deg = run(dict(A1=.5, A2=.5, A3=.5, A4=.5, A5=.5, A6=.5, A7=.4))
    assert deg['bootstrap']['delta_nonpos_fraction'] == 1.0 and not deg['bootstrap']['sgamma_evaluable'] and deg['bootstrap']['kill_evaluable']
    assert deg['bootstrap']['ratios']['F5']['ci_lo'] == 0 == deg['bootstrap']['ratios']['F5']['ci_hi']
    assert deg['criteria']['verdict'] == 'KILL' and deg['criteria']['fired'] == ['J3a'], deg['criteria']
    # R_A1 = 0: F5/F7 undefined -> kill not evaluable -> MIXED (and Delta_geo <= 0 as well)
    zero = run(dict(A1=0., A2=0., A3=0., A4=0., A5=0., A6=0., A7=0.))
    assert zero['bootstrap']['r1_zero_fraction'] == 1.0 and not zero['bootstrap']['kill_evaluable']
    assert zero['criteria']['verdict'] == 'MIXED' and 'kill criteria' in zero['criteria']['note'], zero['criteria']
    # partial: R_A1 ~ 1.7% (20 successes), 3 discordant units (A1 ok, A5 fail) -> ~exp(-3) = 5% of resamples have Delta_geo <= 0 -> S_Gamma not
    # evaluable; F5 = 3/20 with CI_upper >= delta, F7 = 1 -> no KILL -> MIXED naming S_Gamma
    rows = make_rows(dict.fromkeys(agg.ARMS, 0.))
    for r in rows[:20]:
        for a in ('A1', 'A2', 'A3', 'A4', 'A6'):
            r['arms'][a]['info_errors'] = 0
        if r is not rows[0] and r is not rows[1] and r is not rows[2]:
            r['arms']['A5']['info_errors'] = 0
    part = agg.analyse(rows, n_boot=2000)
    pb = part['bootstrap']
    assert pb['Delta_geo']['point'] > 0 and .01 < pb['delta_nonpos_fraction'] < .15 and pb['r1_zero_fraction'] <= .01, (pb['delta_nonpos_fraction'], pb['r1_zero_fraction'])
    assert pb['kill_evaluable'] and not pb['sgamma_evaluable'] and pb['ratios']['F5']['ci_hi'] >= agg.DELTA
    assert part['criteria']['verdict'] == 'MIXED' and part['criteria']['J3'] is False and 'S_Gamma' in part['criteria']['note'], part['criteria']
    # integrity failure and failing gates block interpretation
    rows = make_rows(base)
    rows[3]['g5_ok'] = False
    bad = agg.analyse(rows, n_boot=200)
    assert not bad['interpretable'] and bad['final_verdict'].startswith('NOT_INTERPRETABLE') and bad['integrity']['checks']['g5_ok'] == 1
    gated = agg.analyse(make_rows(base), gates=dict(all_pass=False), n_boot=200)
    assert not gated['interpretable']
    # per-cell reverse effect flag
    rows = make_rows(dict.fromkeys(agg.ARMS, .5))
    for r in rows:
        if r['scenario'] == 'U' and r['rho_permille'] == 300:
            r['arms']['A1']['info_errors'] = 9
            r['arms']['A5']['info_errors'] = 0
    rev = agg.analyse(rows, n_boot=200)
    assert 'K3' in rev['per_cell']['U_rho300']['significant_reverse_effect']
    # per-SNR table and secondary subset (same rules)
    both = agg.analyse_both(make_rows(base), n_boot=300)
    assert set(both['per_snr']) == {str(s) for s in SNRS} and all(set(x['rates']) == set(agg.ARMS) for x in both['per_snr'].values())
    sec = both['secondary_snr_6p5_to_8p0']
    assert sec['n_units'] == sum(1 for r in make_rows(base) if r['snr_centi_db'] in agg.SECONDARY_SNR) and set(sec['per_snr']) == {'650', '700', '750', '800'}
    md = agg.render_md(both)
    assert agg.NOTE_CI0 in md and 'PRIMARY' in md and 'SECONDARY' in md and 'A7 - F0' in md
    assert both['cost']['A7']['mean_seconds_minus_f0_third_round_increment'] == -.2


if __name__ == '__main__':
    test_primitives()
    test_verdict_rule()
    test_end_to_end()
    print('test_e1_agg: ALL PASS')
