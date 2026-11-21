#!/usr/bin/env python
"""E-2 aggregation: the frozen criteria D1-D3 (design.md section 5), the information gate, the co-delay census in both families
(same definitions as tf_cstate_e1_20261017/posthoc_doublet.py), per-SNR tables, costs.  numpy + math only (statistics primitives from the
frozen e1_agg.py).

Units = triggered keys (F0 final syndrome != 0).  Success = 0 information-bit errors.  Families: R (P1 generator, frames 3000..3999),
C (Jakes-4 same-delay clusters).  Cluster for the bootstrap = (family, scenario, rho, frame); 20000 resamples, seed 20261017, percentile CI.
  D1  (R, all triggered units) PASS iff (a) CI_lo(F5) >= .10 and CI_lo(F7) >= .10, (b) CI_lo(S_Gamma) > 1, (c) CI_lo(S_swap) >= .5,
      (d) point share of units with a final doublet: A2 >= .80 and A1 <= .05.   Otherwise FAIL (every item reported).
      F5 = (R1-R5)/R1, F7 = (R1-R7)/R1, S_Gamma = (R1-R2)/(R1-R5), S_swap = (R1-R3)/(R1-R5).
  D2  (R) G = (R_A2g - R_A2)/(R_A1 - R_A2):  PHANTOM-FULL if CI_lo >= .90; else PHANTOM-PARTIAL if CI_lo > .10; else PHANTOM-NONE if
      CI_hi <= .10; else MIXED.  Reported: G_n = (R_A2n - R_A2)/(R_A1 - R_A2), R_A1 - R_A1g.
  D3  (C, after the information gate: A1 rescues (A1 success where F0 had >= 1 info-bit error) among C triggered units >= 100, else UNINFORMATIVE)
      D3a = R: CI(R_A1 - R_A1g) inside [-.01, .01]; D3b = C: CI_lo(R_A1 - R_A1g) > 0; D3c = C: CI_lo(R_A1 - R_A2g) > 0.
      PRINCIPLE = D3a and D3b and D3c; HEURISTIC-SUFFICES = CI_C(R_A1 - R_A2g) inside [-.01, .01] and not D3b; else MIXED.
A ratio is evaluable iff its point denominator > 0 and at most 1% of resamples have a non-positive denominator; a criterion that needs a
non-evaluable ratio is NOT satisfied (and is reported as such).  "CI contains 0" is always printed with: not significant != equivalent.
Usage: python e2_agg.py --rows-R out/main_R --rows-C out/main_C --grid out/calibrate/GRID.json --gates out/gate/gates.json --out out/analysis
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from math import comb, log10
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tf_cstate_e1_20261017'))
import e1_agg  # noqa: E402  (frozen E-1 statistics primitives)

ARMS = ('A1', 'A2', 'A3', 'A1g', 'A2g', 'A2n', 'A5', 'A7')
GUARDED = {'A1g': 'all', 'A2g': 'all', 'A2n': 'neardup'}
N = 1024
NOTE_CI0 = 'CI contains 0: not significant != equivalent'
SEED, N_BOOT, LIMIT = e1_agg.SEED, e1_agg.N_BOOT, e1_agg.DEGENERATE_LIMIT
INFO_GATE_MIN = 100
BINS = ((0., .2), (.2, .5), (.5, .8), (.8, 1.0001))
BIN_NAMES = ('[0,.2)', '[.2,.5)', '[.5,.8)', '[.8,1]')
R_SNRS = (450, 500, 550, 600, 650, 700, 750, 800)
R_FRAMES = (3000, 4000)
C_FRAMES = (0, 1000)
CONTRASTS = (('A1', 'A2'), ('A2g', 'A2'), ('A1', 'A2g'), ('A1', 'A1g'), ('A2n', 'A2'), ('A2n', 'A2g'), ('A1', 'A3'), ('A1', 'A5'), ('A1', 'A7'),
             ('A1g', 'A2g'))


# ----------------------------------------------------------------------------- exact McNemar (log10 p, no float underflow)
def mcnemar_log10p(b, c):
    """log10 of the exact one-sided p = P(Binomial(b + c, .5) >= b) (None when there is no discordant pair)."""
    n = b + c
    if n == 0:
        return 0.0
    tail = sum(comb(n, i) for i in range(b, n + 1))
    return log10(tail) - n * log10(2)


def mcnemar(x, y):
    x, y = np.asarray(x, bool), np.asarray(y, bool)
    b, c = int(np.sum(x & ~y)), int(np.sum(~x & y))
    lp = mcnemar_log10p(b, c)
    return dict(b=b, c=c, log10_p=lp, p=float(10 ** lp) if lp > -300 else 0.0, significant=bool(lp < log10(.05)))


# ----------------------------------------------------------------------------- bootstrap quantities
def quantities(success, cluster_ids, n_boot=N_BOOT, seed=SEED):
    """Point values and bootstrap CIs of every quantity used by D1-D3 (plus the reported ones)."""
    arms = [a for a in ARMS if a in success]
    rates, m = e1_agg.bootstrap_rates({a: success[a] for a in arms}, cluster_ids, n_boot, seed)
    point = {a: float(np.mean(success[a])) for a in arms}
    out = dict(n_clusters=int(m), n_boot=int(n_boot), seed=int(seed), rates_point=point, diff={}, ratio={})
    for a, b in {(a, b) for a, b in CONTRASTS} | {('A1', 'A5'), ('A2', 'A5'), ('A1', 'A7')}:
        lo, hi = e1_agg.ci(rates[a] - rates[b])
        out['diff'][f'{a}-{b}'] = dict(point=point[a] - point[b], ci_lo=lo, ci_hi=hi, ci_width=hi - lo, contains_0=bool(lo <= 0 <= hi))

    def ratio(name, numer, denom):
        # numer, denom: dict arm -> sign  (a linear combination of rates)
        def comb_(r):
            return sum(s * r[a] for a, s in numer.items()), sum(s * r[a] for a, s in denom.items())
        n_b, d_b = comb_(rates)
        n_p, d_p = comb_(point)
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = np.where(d_b > 0, n_b / np.where(d_b > 0, d_b, 1.), np.nan)
        nonpos = float(np.mean(~(d_b > 0)))
        c = e1_agg.ci(vals)
        ev = bool(d_p > 0 and nonpos <= LIMIT and c is not None)
        out['ratio'][name] = dict(point=(float(n_p / d_p) if d_p > 0 else None), ci_lo=None if c is None else c[0], ci_hi=None if c is None else c[1],
                                  ci_width=None if c is None else c[1] - c[0], denominator_nonpositive_fraction=nonpos, evaluable=ev,
                                  denominator_point=float(d_p))
    ratio('F5', {'A1': 1, 'A5': -1}, {'A1': 1})
    ratio('F7', {'A1': 1, 'A7': -1}, {'A1': 1})
    ratio('S_Gamma', {'A1': 1, 'A2': -1}, {'A1': 1, 'A5': -1})
    ratio('S_swap', {'A1': 1, 'A3': -1}, {'A1': 1, 'A5': -1})
    ratio('G', {'A2g': 1, 'A2': -1}, {'A1': 1, 'A2': -1})
    ratio('G_n', {'A2n': 1, 'A2': -1}, {'A1': 1, 'A2': -1})
    return out


# ----------------------------------------------------------------------------- frozen criteria (pure functions of the quantities)
def d1_verdict(q, doublet_share):
    """q: quantities() of family R.  doublet_share: dict(A1=..., A2=...) point shares of units with a final doublet."""
    r = q['ratio']
    items = {}

    def item(name, ok, detail):
        items[name] = dict(satisfied=bool(ok), **detail)
    f5, f7 = r['F5'], r['F7']
    item('a_F5_F7_ci_lo_ge_.10', f5['evaluable'] and f7['evaluable'] and f5['ci_lo'] >= .10 and f7['ci_lo'] >= .10,
         dict(F5_ci_lo=f5['ci_lo'], F7_ci_lo=f7['ci_lo'], evaluable=bool(f5['evaluable'] and f7['evaluable'])))
    sg = r['S_Gamma']
    item('b_S_Gamma_ci_lo_gt_1', sg['evaluable'] and sg['ci_lo'] > 1., dict(ci_lo=sg['ci_lo'], evaluable=sg['evaluable']))
    sw = r['S_swap']
    item('c_S_swap_ci_lo_ge_.5', sw['evaluable'] and sw['ci_lo'] >= .5, dict(ci_lo=sw['ci_lo'], evaluable=sw['evaluable']))
    item('d_doublet_share_A2_ge_.80_A1_le_.05', doublet_share['A2'] >= .80 and doublet_share['A1'] <= .05,
         dict(A2=doublet_share['A2'], A1=doublet_share['A1']))
    ok = all(v['satisfied'] for v in items.values())
    return dict(verdict='PASS' if ok else 'FAIL', items=items, failed=[k for k, v in items.items() if not v['satisfied']])


def d2_verdict(q):
    g = q['ratio']['G']
    if not g['evaluable']:
        return dict(verdict='MIXED', note='G not evaluable (R_A1 - R_A2 <= 0 in the point estimate or in more than 1% of resamples)', G=g)
    lo, hi = g['ci_lo'], g['ci_hi']
    if lo >= .90:
        v = 'PHANTOM-FULL'
    elif lo > .10:
        v = 'PHANTOM-PARTIAL'
    elif hi <= .10:
        v = 'PHANTOM-NONE'
    else:
        v = 'MIXED'
    return dict(verdict=v, note=None, G=g)


def d3_verdict(qR, qC, n_a1_success_C):
    if qC is None or n_a1_success_C is None:
        return dict(verdict='UNINFORMATIVE', note='no informative C-family rho / no C rows', info_gate=dict(a1_rescued_units=n_a1_success_C, minimum=INFO_GATE_MIN))
    gate = dict(a1_rescued_units=int(n_a1_success_C), minimum=INFO_GATE_MIN, passed=bool(n_a1_success_C >= INFO_GATE_MIN))
    d_r, d_c = qR['diff']['A1-A1g'], qC['diff']['A1-A1g']
    d_cg = qC['diff']['A1-A2g']
    d3a = bool(d_r['ci_lo'] >= -.01 and d_r['ci_hi'] <= .01)
    d3b = bool(d_c['ci_lo'] > 0)
    d3c = bool(d_cg['ci_lo'] > 0)
    inside = bool(d_cg['ci_lo'] >= -.01 and d_cg['ci_hi'] <= .01)
    detail = dict(D3a=d3a, D3b=d3b, D3c=d3c, C_A1_minus_A2g_inside_pm_0p01=inside, R_A1_minus_A1g=d_r, C_A1_minus_A1g=d_c, C_A1_minus_A2g=d_cg, info_gate=gate)
    if not gate['passed']:
        return dict(verdict='UNINFORMATIVE', note='information gate failed', **detail)
    if d3a and d3b and d3c:
        v = 'PRINCIPLE'
    elif inside and not d3b:
        v = 'HEURISTIC-SUFFICES'
    else:
        v = 'MIXED'
    return dict(verdict=v, note=None, **detail)


# ----------------------------------------------------------------------------- co-delay census (posthoc_doublet.py definitions)
def dn(dnu):
    x = abs(dnu)
    return 1.0 if x == 0 else abs(float(np.sin(np.pi * x) / (N * np.sin(np.pi * x / N))))


def bin_of(v):
    for i, (lo, hi) in enumerate(BINS):
        if lo <= v < hi:
            return i
    raise ValueError(v)


def doublets(delays, dopplers):
    by = {}
    for d, nu in zip(delays, dopplers):
        by.setdefault(int(d), []).append(float(nu))
    return [(d, dn(nus[i] - nus[j]), abs(nus[i] - nus[j])) for d, nus in by.items() for i in range(len(nus)) for j in range(i + 1, len(nus))]


def classify_edits(r1_delays, edits, truth_set):
    cur = [int(d) for d in r1_delays]
    out = []
    for e in sorted(edits, key=lambda x: x['step']):
        slot, new = int(e['slot']), int(e['new']['delay'])
        others = cur[:slot] + cur[slot + 1:]
        cat = 'shares' if new in others else 'same_slot' if new == cur[slot] else 'new'
        out.append(dict(category=cat, delay=new, in_truth=new in truth_set))
        cur[slot] = new
    return out


def truth_delay_set(row):
    t = row['truth']
    return set(t['tap_delays']) if 'tap_delays' in t else set(int(d) for d in t['delays'])


def multi_ray_delays(row):
    t = row['truth']
    if 'rays_per_tap' not in t:
        return set()
    return {d for d, r in zip(t['tap_delays'], t['rays_per_tap']) if r >= 2}


def rate(k, n):
    return None if n == 0 else k / n


def census(units, family):
    """Pre-registered readout: co-delay census of the final geometries of the triggered units of one family."""
    n = len(units)
    out = dict(n_units=n, r1_duplicate_delay_units=sum(1 for u in units if len(set(u['r1']['delays'])) != len(u['r1']['delays'])), arms={}, edits={})
    for a in ARMS:
        pairs_by_unit = [doublets(u['arms'][a]['final_delays'], u['arms'][a]['final_dopplers']) for u in units]
        pairs = [p for x in pairs_by_unit for p in x]
        hist = [0] * len(BINS)
        for p in pairs:
            hist[bin_of(p[1])] += 1
        entry = dict(units_with_doublet=sum(1 for x in pairs_by_unit if x), frac_units_with_doublet=rate(sum(1 for x in pairs_by_unit if x), n),
                     pairs=len(pairs), mean_pairs_per_unit=(len(pairs) / n if n else None), hist_abs_DN=dict(zip(BIN_NAMES, hist)),
                     final_delay_set_equals_truth_set=rate(sum(1 for u in units if set(u['arms'][a]['final_delays']) == truth_delay_set(u)), n))
        if a in ('A1', 'A2', 'A1g', 'A2g', 'A2n'):
            ec = [c for u in units for c in classify_edits(u['r1']['delays'], u['arms'][a]['edits'], truth_delay_set(u))]
            m = len(ec)
            cnt = {k: sum(1 for e in ec if e['category'] == k) for k in ('shares', 'same_slot', 'new')}
            out['edits'][a] = dict(accepted_edits=m, counts=cnt, fractions={k: rate(v, m) for k, v in cnt.items()},
                                   new_delay_in_truth=sum(1 for e in ec if e['category'] == 'new' and e['in_truth']),
                                   new_delay_not_in_truth=sum(1 for e in ec if e['category'] == 'new' and not e['in_truth']))
        if family == 'C' and a in ('A1', 'A2', 'A1g', 'A2g', 'A2n'):
            on_multi = sum(1 for u, x in zip(units, pairs_by_unit) for p in x if p[0] in multi_ray_delays(u))
            units_on_multi = sum(1 for u, x in zip(units, pairs_by_unit) if any(p[0] in multi_ray_delays(u) for p in x))
            entry.update(doublet_pairs_on_true_multiray_tap=on_multi, frac_doublet_pairs_on_true_multiray_tap=rate(on_multi, len(pairs)),
                         units_with_doublet_on_true_multiray_tap=units_on_multi,
                         frac_doublet_units_on_true_multiray_tap=rate(units_on_multi, entry['units_with_doublet']))
        out['arms'][a] = entry
    out['units_with_truth_duplicate_delays'] = sum(1 for u in units if len(set(u['truth']['delays'])) != len(u['truth']['delays']))
    if family == 'C':
        out['units_with_true_multiray_tap'] = sum(1 for u in units if multi_ray_delays(u))
    return out


# ----------------------------------------------------------------------------- loading, integrity, tables
def load_rows(rows_dir):
    rows = []
    for p in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as handle:
            rows += [json.loads(line) for line in handle if line.strip()]
    return rows


def key_of(r):
    return (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])


def expected_keys(family, grid=None):
    if family == 'R':
        return {(s, rho, snr, f) for s in ('U', 'G') for rho in (300, 500) for snr in R_SNRS for f in range(*R_FRAMES)}
    keys = set()
    for rho_s, e in grid['rho'].items():
        if e['status'] == 'OK':
            keys |= {('J4', int(round(float(rho_s) * 1000)), int(round(s * 100)), f) for s in e['grid_db'] for f in range(*C_FRAMES)}
    return keys


def integrity(rows, want):
    got = [key_of(r) for r in rows]
    problems = []
    if len(set(got)) != len(got):
        problems.append('duplicate rows')
    if want is not None and set(got) != want:
        problems.append(f'row/key mismatch: {len(set(got) ^ want)} keys differ')
    trig = [r for r in rows if r['triggered']]
    bad = lambda f, xs=trig: sum(1 for r in xs if not f(r))  # noqa: E731
    checks = dict(f0_syndrome_consistent=sum(1 for r in rows if (r['f0']['syndrome'] != 0) != r['triggered']),
                  g5_ok=bad(lambda r: r.get('g5_ok')), guard_ok=bad(lambda r: r.get('guard_ok')),
                  arms_not_ok=bad(lambda r: all(r['arms'].get(a, {}).get('status') == 'ok' for a in ARMS)),
                  triggered_with_f0_success=sum(1 for r in trig if r['f0']['info_errors'] == 0))
    for name in ('f0_syndrome_consistent', 'g5_ok', 'guard_ok', 'arms_not_ok'):
        if checks[name]:
            problems.append(f'{name}: {checks[name]} fail')
    fallbacks = {a: sum(1 for r in trig if r['arms'].get(a, {}).get('numerical_fallback')) for a in ARMS}
    return dict(n_rows=len(rows), n_keys=None if want is None else len(want), n_triggered=len(trig), checks=checks, numerical_fallbacks=fallbacks,
                problems=problems, ok=not problems)


def success_matrix(units):
    return {a: np.array([u['arms'][a]['info_errors'] == 0 for u in units], bool) for a in ARMS}


def per_snr(units, success):
    snr = np.array([u['snr_centi_db'] for u in units])
    return {str(s): dict(n=int((snr == s).sum()), rates={a: float(success[a][snr == s].mean()) for a in ARMS}) for s in sorted(set(snr.tolist()))}


def per_rho(units, success):
    rho = np.array([u['rho_permille'] for u in units])
    return {str(s): dict(n=int((rho == s).sum()), rates={a: float(success[a][rho == s].mean()) for a in ARMS}) for s in sorted(set(rho.tolist()))}


def cost(rows):
    trig = [r for r in rows if r['triggered']]
    out = dict(keys=len(rows), triggered=len(trig), mean_f0_seconds=float(np.mean([r['f0']['seconds'] for r in rows])) if rows else None,
               mean_gen_seconds_per_key=float(np.mean([r['gen_seconds'] for r in rows])) if rows else None, arms={})
    for a in ARMS:
        s = [u['arms'][a]['seconds'] for u in trig]
        out['arms'][a] = dict(mean_seconds=float(np.mean(s)) if s else None)
    out['arms']['A7']['mean_seconds_minus_f0'] = float(np.mean([u['arms']['A7']['seconds_minus_f0'] for u in trig])) if trig else None
    out['total_core_hours'] = float((sum(r['gen_seconds'] + r['f0']['seconds'] for r in rows) + sum(u['arms'][a]['seconds'] for u in trig for a in ARMS)) / 3600)
    return out


def analyse_family(rows, family, want_keys, n_boot=N_BOOT, seed=SEED):
    units = [r for r in rows if r['triggered']]
    integ = integrity(rows, want_keys)
    res = dict(family=family, integrity=integ, n_units=len(units), n_keys=len(rows))
    if not units:
        res['note'] = 'no triggered units'
        return res
    success = success_matrix(units)
    ids = [f"{family}|{u['scenario']}|{u['rho_permille']}|{u['frame']}" for u in units]
    q = quantities(success, ids, n_boot, seed)
    f0_fail = np.array([u['f0']['info_errors'] > 0 for u in units], bool)
    res.update(success={a: int(success[a].sum()) for a in ARMS}, rescued={a: int(np.sum(success[a] & f0_fail)) for a in ARMS}, quantities=q, per_snr=per_snr(units, success), per_rho=per_rho(units, success),
               mcnemar={f'{a}>{b}': mcnemar(success[a], success[b]) for a, b in CONTRASTS}, census=census(units, family), cost=cost(rows),
               note_ci0=NOTE_CI0)
    return res


def analyse(rows_R, rows_C, grid=None, gates=None, cgates=None, n_boot=N_BOOT, seed=SEED, expected=None):
    """expected: optional (keys_R, keys_C) override of the frozen key sets (synthetic tests only)."""
    gate_ok = None if gates is None else bool(gates.get('all_pass'))
    cgate_ok = None if cgates is None else bool(cgates.get('all_pass'))
    want_R = expected_keys('R') if expected is None else expected[0]
    want_C = (None if grid is None else expected_keys('C', grid)) if expected is None else expected[1]
    R = analyse_family(rows_R, 'R', want_R, n_boot, seed)
    C = analyse_family(rows_C, 'C', want_C, n_boot, seed) if rows_C else None
    interpretable = bool(R['integrity']['ok'] and (C is None or C['integrity']['ok']) and gate_ok is not False and cgate_ok is not False)
    out = dict(R=R, C=C, grid=grid, gates_all_pass=gate_ok, cgates_all_pass=cgate_ok, interpretable=interpretable)
    if 'quantities' not in R:
        out['verdicts'] = dict(note='no R units')
        return out
    cq = None if C is None or 'quantities' not in C else C['quantities']
    n_a1 = None if cq is None else C['rescued']['A1']   # information gate counts rescues: A1 succeeds where F0 had >= 1 information-bit error
    share = {a: R['census']['arms'][a]['frac_units_with_doublet'] for a in ('A1', 'A2')}
    out['verdicts'] = dict(D1=d1_verdict(R['quantities'], share), D2=d2_verdict(R['quantities']), D3=d3_verdict(R['quantities'], cq, n_a1))
    if not interpretable:
        out['verdicts_note'] = 'NOT INTERPRETABLE: integrity or gates failed'
    return out


def _f(x, spec='+.4f'):
    return 'n/a' if x is None else format(x, spec)


def render_family(res):
    if 'quantities' not in res:
        return f"## Family {res['family']}: no triggered units; integrity {json.dumps(res['integrity'])}\n"
    q = res['quantities']
    L = [f"## Family {res['family']}: {res['n_units']} triggered units of {res['n_keys']} keys", '', f"integrity: {json.dumps(res['integrity'], default=str)}", '',
         '| arm | success | rate |', '|---|---|---|']
    for a in ARMS:
        L.append(f"| {a} | {res['success'][a]}/{res['n_units']} | {q['rates_point'][a]:.4f} |")
    L += ['', f"### Differences of success rate (cluster bootstrap {q['n_boot']} resamples, seed {q['seed']}); {NOTE_CI0}", '', '| pair | diff | 95% CI | width |', '|---|---|---|---|']
    for k, v in q['diff'].items():
        L.append(f"| {k} | {v['point']:+.4f} | [{v['ci_lo']:+.4f}, {v['ci_hi']:+.4f}] | {v['ci_width']:.4f} |" + (f"  ({NOTE_CI0})" if v['contains_0'] else ''))
    L += ['', '### Ratios', '', '| quantity | point | 95% CI | den<=0 fraction | evaluable |', '|---|---|---|---|---|']
    for k, v in q['ratio'].items():
        L.append(f"| {k} | {_f(v['point'])} | [{_f(v['ci_lo'])}, {_f(v['ci_hi'])}] | {v['denominator_nonpositive_fraction']:.4f} | {v['evaluable']} |")
    L += ['', '### Exact one-sided McNemar (reported; b = first arm only, c = second only)', '', '| test | b | c | log10 p |', '|---|---|---|---|']
    for k, v in res['mcnemar'].items():
        L.append(f"| {k} | {v['b']} | {v['c']} | {v['log10_p']:.1f} |")
    L += ['', '### Per SNR (success rate)', '', '| snr (centi-dB) | n | ' + ' | '.join(ARMS) + ' |', '|---|---|' + '---|' * len(ARMS)]
    for s, x in res['per_snr'].items():
        L.append(f"| {s} | {x['n']} | " + ' | '.join(f"{x['rates'][a]:.3f}" for a in ARMS) + ' |')
    L += ['', '### Per rho (success rate)', '', '| rho (permille) | n | ' + ' | '.join(ARMS) + ' |', '|---|---|' + '---|' * len(ARMS)]
    for s, x in res['per_rho'].items():
        L.append(f"| {s} | {x['n']} | " + ' | '.join(f"{x['rates'][a]:.3f}" for a in ARMS) + ' |')
    c = res['census']
    L += ['', '### Co-delay census (pre-registered readout; final geometry; doublet = two paths with equal delay)', '',
          '| arm | units with doublet | frac | pairs | |D_N| hist [0,.2) / [.2,.5) / [.5,.8) / [.8,1] | final delay set == truth set |', '|---|---|---|---|---|---|']
    for a, x in c['arms'].items():
        L.append(f"| {a} | {x['units_with_doublet']} | {_f(x['frac_units_with_doublet'], '.4f')} | {x['pairs']} | "
                 + ' / '.join(str(x['hist_abs_DN'][b]) for b in BIN_NAMES) + f" | {_f(x['final_delay_set_equals_truth_set'], '.4f')} |")
    L += ['', f"r1 duplicate-delay units: {c['r1_duplicate_delay_units']}; units whose truth has duplicate delays (rays): {c['units_with_truth_duplicate_delays']}", '',
          '| arm | edits | shares | same_slot | new | new in truth | new not in truth |', '|---|---|---|---|---|---|---|']
    for a, x in c['edits'].items():
        cn = x['counts']
        L.append(f"| {a} | {x['accepted_edits']} | {cn['shares']} | {cn['same_slot']} | {cn['new']} | {x['new_delay_in_truth']} | {x['new_delay_not_in_truth']} |")
    if res['family'] == 'C':
        L += ['', f"units with a true multi-ray tap: {c['units_with_true_multiray_tap']}", '', '| arm | doublet pairs on true multi-ray tap | frac of pairs | doublet units on true multi-ray tap | frac of doublet units |', '|---|---|---|---|---|']
        for a in ('A1', 'A2', 'A1g', 'A2g', 'A2n'):
            x = c['arms'][a]
            L.append(f"| {a} | {x['doublet_pairs_on_true_multiray_tap']} | {_f(x['frac_doublet_pairs_on_true_multiray_tap'], '.4f')} | "
                     f"{x['units_with_doublet_on_true_multiray_tap']} | {_f(x['frac_doublet_units_on_true_multiray_tap'], '.4f')} |")
    L += ['', '### Cost (mean seconds; A7 total is a from-scratch rounds=3 run)', '', json.dumps(res['cost'], indent=1)]
    return '\n'.join(L) + '\n'


def render_md(res):
    L = ['# E-2 aggregate', '', f"interpretable: {res['interpretable']}; gates_all_pass: {res['gates_all_pass']}; cgates_all_pass: {res['cgates_all_pass']}", '']
    v = res.get('verdicts', {})
    if 'D1' in v:
        d1, d2, d3 = v['D1'], v['D2'], v['D3']
        L += [f"**D1 (replication, family R): {d1['verdict']}**  failed items: {d1['failed'] or 'none'}", '', '```', json.dumps(d1['items'], indent=1, default=str), '```', '',
              f"**D2 (guard recovery share, family R): {d2['verdict']}**" + (f"  ({d2['note']})" if d2['note'] else ''), '',
              f"**D3 (principle vs heuristic, family C): {d3['verdict']}**" + (f"  ({d3['note']})" if d3.get('note') else ''), '', '```',
              json.dumps({k: x for k, x in d3.items() if k not in ('verdict', 'note')}, indent=1, default=str), '```', '']
    if res.get('verdicts_note'):
        L.append(res['verdicts_note'] + '\n')
    L.append(render_family(res['R']))
    if res['C']:
        L.append(render_family(res['C']))
    if res.get('grid'):
        L += ['## Calibrated C-family SNR grid (frozen rule, F0 only)', '', json.dumps({k: v for k, v in res['grid'].items() if k != 'rows_md5'}, indent=1), '']
    return '\n'.join(L) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows-R', type=Path, required=True)
    p.add_argument('--rows-C', type=Path)
    p.add_argument('--grid', type=Path)
    p.add_argument('--gates', type=Path)
    p.add_argument('--cgates', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--boot', type=int, default=N_BOOT)
    a = p.parse_args()
    grid = json.loads(a.grid.read_text()) if a.grid else None
    res = analyse(load_rows(a.rows_R), load_rows(a.rows_C) if a.rows_C else [], grid,
                  json.loads(a.gates.read_text()) if a.gates else None, json.loads(a.cgates.read_text()) if a.cgates else None, a.boot)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'e2_summary.json').write_text(json.dumps(res, indent=1, default=str) + '\n')
    (a.out / 'e2_summary.md').write_text(render_md(res))
    print(render_md(res))


if __name__ == '__main__':
    main()
