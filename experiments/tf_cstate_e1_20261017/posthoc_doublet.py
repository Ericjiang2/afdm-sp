#!/usr/bin/env python
"""POST HOC, EXPLORATORY: same-delay doublets in the final geometries of the existing E-1 main rows (no new simulation).

Definitions (coordinator, 2026-10-17): doublet = two paths of a final geometry with equal integer delay; dnu = their Doppler difference;
|D_N(dnu)| = |sin(pi dnu) / (N sin(pi dnu / N))|, N = 1024 (= len(y); system.N_total) and |D_N(0)| = 1.
Tables P1-P5 on the primary set (all triggered keys) and the 6.5-8.0 dB subset.  Nothing here is part of the frozen verdict.
Usage: python posthoc_doublet.py --rows out/main --out out/main/posthoc
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from math import pi, sin, sqrt
from pathlib import Path

LABEL = 'post hoc, exploratory'
N = 1024
BINS = ((0., .2), (.2, .5), (.5, .8), (.8, 1.0001))
BIN_NAMES = ('[0,.2)', '[.2,.5)', '[.5,.8)', '[.8,1]')
SECONDARY_SNR = (650, 700, 750, 800)
ARMS_CENSUS = ('A1', 'A2', 'A3', 'A4', 'A5', 'A7')


def dn(dnu):
    x = abs(dnu)
    return 1.0 if x == 0 else abs(sin(pi * x) / (N * sin(pi * x / N)))


def bin_of(v):
    for i, (lo, hi) in enumerate(BINS):
        if lo <= v < hi:
            return i
    raise ValueError(v)


def doublets(delays, dopplers):
    """Pairs of paths sharing an integer delay: list of (delay, |D_N(dnu)|, |dnu|)."""
    by = {}
    for d, nu in zip(delays, dopplers):
        by.setdefault(int(d), []).append(float(nu))
    out = []
    for d, nus in by.items():
        for i in range(len(nus)):
            for j in range(i + 1, len(nus)):
                out.append((d, dn(nus[i] - nus[j]), abs(nus[i] - nus[j])))
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0., c - h), min(1., c + h)]


def rate(k, n):
    return None if n == 0 else k / n


def classify_edits(r1_delays, edits, truth_set):
    """Replay accepted edits on the r1 slot order.  Category per edit: 'shares' (replacement delay equals the delay of ANOTHER current
    path -> a doublet is created), 'same_slot' (keeps the replaced slot's own delay, Doppler-only move), 'new' (a delay absent from the
    current set).  Returns (list of dict(category, delay, in_truth), final delay list)."""
    cur = [int(d) for d in r1_delays]
    out = []
    for e in sorted(edits, key=lambda x: x['step']):
        slot, new = int(e['slot']), int(e['new']['delay'])
        if cur[slot] != int(e['old']['delay']):
            raise ValueError('edit replay: old delay differs from tracked slot')
        others = cur[:slot] + cur[slot + 1:]
        cat = 'shares' if new in others else 'same_slot' if new == cur[slot] else 'new'
        out.append(dict(category=cat, delay=new, in_truth=new in truth_set))
        cur[slot] = new
    return out, cur


def load(rows_dir):
    units = []
    for p in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as handle:
            for line in handle:
                if not line.strip():
                    continue
                r = json.loads(line)
                truth_set = set(int(d) for d in r['truth']['delays'])
                u = dict(snr=r['snr_centi_db'], r1_delays=[int(d) for d in r['r1']['delays']], truth_delays=[int(d) for d in r['truth']['delays']],
                         truth_set=truth_set, arms={})
                for a, x in r['arms'].items():
                    u['arms'][a] = dict(ok=x['info_errors'] == 0, delays=[int(d) for d in x['final_delays']],
                                        dopplers=[float(v) for v in x['final_dopplers']], edits=x.get('edits', []))
                    u['arms'][a]['doublets'] = doublets(u['arms'][a]['delays'], u['arms'][a]['dopplers'])
                    if a in ('A1', 'A2'):
                        cls, replay = classify_edits(u['r1_delays'], u['arms'][a]['edits'], truth_set)
                        u['arms'][a]['edit_classes'] = cls
                        u['arms'][a]['replay_ok'] = sorted(replay) == sorted(u['arms'][a]['delays'])
                units.append(u)
    return units


def hist(values):
    h = [0] * len(BINS)
    for v in values:
        h[bin_of(v)] += 1
    return dict(zip(BIN_NAMES, h))


def analyse(units):
    n = len(units)
    res = dict(label=LABEL, n_units=n, N=N)
    # r1 uniqueness
    res['r1_unique_delays'] = dict(units_with_duplicate_r1_delays=sum(1 for u in units if len(set(u['r1_delays'])) != len(u['r1_delays'])))
    res['edit_replay_consistent_units'] = {a: sum(1 for u in units if u['arms'][a]['replay_ok']) for a in ('A1', 'A2')}
    # ---- P1 census
    census = {}
    for a in ARMS_CENSUS:
        d = [u['arms'][a]['doublets'] for u in units]
        pairs = [p for x in d for p in x]
        census[a] = dict(units_with_doublet=sum(1 for x in d if x), frac_units_with_doublet=rate(sum(1 for x in d if x), n),
                         doublet_pairs_total=len(pairs), mean_pairs_per_unit=len(pairs) / n, max_pairs_in_a_unit=max(len(x) for x in d),
                         hist_abs_DN=hist([p[1] for p in pairs]))
    res['P1_census'] = census
    edit_stats = {}
    for a in ('A1', 'A2'):
        edits = [c for u in units for c in u['arms'][a]['edit_classes']]
        m = len(edits)
        cnt = {c: sum(1 for e in edits if e['category'] == c) for c in ('shares', 'same_slot', 'new')}
        edit_stats[a] = dict(accepted_edits=m, counts=cnt, fractions={c: rate(v, m) for c, v in cnt.items()},
                             new_delay_in_truth=sum(1 for e in edits if e['category'] == 'new' and e['in_truth']),
                             new_delay_not_in_truth=sum(1 for e in edits if e['category'] == 'new' and not e['in_truth']),
                             shares_delay_in_truth=sum(1 for e in edits if e['category'] == 'shares' and e['in_truth']),
                             shares_delay_not_in_truth=sum(1 for e in edits if e['category'] == 'shares' and not e['in_truth']))
    res['P1_edit_categories'] = edit_stats
    # ---- P2
    p2 = {}
    for a in ('A2', 'A1'):
        t = dict(doublet_success=0, doublet_fail=0, nodoublet_success=0, nodoublet_fail=0)
        for u in units:
            x = u['arms'][a]
            t[('doublet_' if x['doublets'] else 'nodoublet_') + ('success' if x['ok'] else 'fail')] += 1
        t['fail_rate_with_doublet'] = rate(t['doublet_fail'], t['doublet_success'] + t['doublet_fail'])
        t['fail_rate_without_doublet'] = rate(t['nodoublet_fail'], t['nodoublet_success'] + t['nodoublet_fail'])
        p2[f'{a}_doublet_x_success'] = t
    harm = [u for u in units if u['arms']['A5']['ok'] and not u['arms']['A2']['ok']]
    both_ok = [u for u in units if u['arms']['A5']['ok'] and u['arms']['A2']['ok']]
    harm_dbl = sum(1 for u in harm if u['arms']['A2']['doublets'])
    harm_share_edit = sum(1 for u in harm if any(c['category'] == 'shares' for c in u['arms']['A2']['edit_classes']))
    p2['A2_harm_units'] = dict(
        definition='A5 success and A2 fail', n=len(harm), with_A2_doublet=harm_dbl, frac_with_A2_doublet=rate(harm_dbl, len(harm)),
        with_A2_edit_sharing_a_delay=harm_share_edit, frac_with_A2_edit_sharing_a_delay=rate(harm_share_edit, len(harm)),
        comparator_A5_ok_and_A2_ok=dict(n=len(both_ok), frac_with_A2_doublet=rate(sum(1 for u in both_ok if u['arms']['A2']['doublets']), len(both_ok))),
        comparator_all_units_frac_with_A2_doublet=rate(sum(1 for u in units if u['arms']['A2']['doublets']), n),
        hist_abs_DN_of_doublets_in_harm_units=hist([p[1] for u in harm for p in u['arms']['A2']['doublets']]),
        harm_units_without_A2_doublet_with_support_change=sum(1 for u in harm if not u['arms']['A2']['doublets']
                                                              and set(u['arms']['A2']['delays']) != set(u['r1_delays'])))
    rescue = [u for u in units if u['arms']['A1']['ok'] and not u['arms']['A2']['ok']]
    intro_true = sum(1 for u in rescue if any(c['category'] == 'new' and c['in_truth'] for c in u['arms']['A1']['edit_classes']))
    intro_false = sum(1 for u in rescue if any(c['category'] == 'new' and not c['in_truth'] for c in u['arms']['A1']['edit_classes']))
    intro_none = sum(1 for u in rescue if not any(c['category'] == 'new' for c in u['arms']['A1']['edit_classes']))
    intro_only_true = sum(1 for u in rescue if any(c['category'] == 'new' for c in u['arms']['A1']['edit_classes'])
                          and all(c['in_truth'] for c in u['arms']['A1']['edit_classes'] if c['category'] == 'new'))
    p2['A1_only_rescues'] = dict(
        definition='A1 success and A2 fail', n=len(rescue),
        A1_introduced_new_delay_in_truth_set_ge1=intro_true, A1_introduced_new_delay_not_in_truth_set_ge1=intro_false,
        A1_introduced_no_new_delay=intro_none, A1_introduced_new_delays_all_in_truth=intro_only_true,
        frac_ge1_in_truth=rate(intro_true, len(rescue)), frac_ge1_not_in_truth=rate(intro_false, len(rescue)),
        A1_with_doublet=sum(1 for u in rescue if u['arms']['A1']['doublets']))
    res['P2'] = p2
    # ---- P3
    p3 = {}
    for a in ('A2', 'A1'):
        rows = {name: [0, 0] for name in BIN_NAMES}  # [fail, n]
        for u in units:
            x = u['arms'][a]
            if not x['doublets']:
                continue
            b = BIN_NAMES[bin_of(max(p[1] for p in x['doublets']))]
            rows[b][1] += 1
            rows[b][0] += int(not x['ok'])
        tot_f, tot_n = sum(v[0] for v in rows.values()), sum(v[1] for v in rows.values())
        p3[a] = dict(by_max_abs_DN_bin={b: dict(n=v[1], fail=v[0], fail_rate=rate(v[0], v[1]), wilson95=wilson(v[0], v[1])) for b, v in rows.items()},
                     all_units_with_doublet=dict(n=tot_n, fail=tot_f, fail_rate=rate(tot_f, tot_n), wilson95=wilson(tot_f, tot_n)))
    res['P3'] = p3
    # ---- P3b: |dnu| of the doublets (what "large |D_N|" means in Doppler terms)
    p3b = {}
    for a in ('A2', 'A1'):
        v = sorted(p[2] for u in units for p in u['arms'][a]['doublets'])
        m = len(v)
        q = (lambda x: None if not m else v[min(m - 1, int(x * m))])
        p3b[a] = dict(pairs=m, abs_dnu_quantiles={'p10': q(.1), 'p50': q(.5), 'p90': q(.9), 'max': None if not m else v[-1]},
                      frac_abs_dnu_le_0p25=rate(sum(1 for x in v if x <= .25 + 1e-9), m), frac_abs_dnu_le_0p5=rate(sum(1 for x in v if x <= .5 + 1e-9), m),
                      frac_abs_dnu_ge_1=rate(sum(1 for x in v if x >= 1.), m), frac_abs_DN_ge_0p9=rate(sum(1 for u in units for p in u['arms'][a]['doublets'] if p[1] >= .9), m))
    res['P3b_abs_dnu_of_doublets'] = p3b
    # ---- P4
    dup_truth = sum(1 for u in units if len(set(u['truth_delays'])) != len(u['truth_delays']))
    pairs2 = [(u, p) for u in units for p in u['arms']['A2']['doublets']]
    in_truth = sum(1 for u, p in pairs2 if p[0] in u['truth_set'])
    truth_mult2 = sum(1 for u, p in pairs2 if u['truth_delays'].count(p[0]) >= 2)
    pairs1 = [(u, p) for u in units for p in u['arms']['A1']['doublets']]
    res['P4'] = dict(
        units_with_duplicate_truth_delays=dup_truth,
        A2_doublet_pairs=len(pairs2), A2_doublet_shared_delay_in_truth_set=in_truth, frac_A2_doublet_delay_in_truth=rate(in_truth, len(pairs2)),
        A2_doublet_shared_delay_has_two_truth_paths=truth_mult2,
        A1_doublet_pairs=len(pairs1), A1_doublet_shared_delay_in_truth_set=sum(1 for u, p in pairs1 if p[0] in u['truth_set']),
        final_delay_set_equals_truth_set={a: dict(units=sum(1 for u in units if set(u['arms'][a]['delays']) == u['truth_set']),
                                                   frac=rate(sum(1 for u in units if set(u['arms'][a]['delays']) == u['truth_set']), n))
                                           for a in ARMS_CENSUS},
        r1_delay_set_equals_truth_set=dict(units=sum(1 for u in units if set(u['r1_delays']) == u['truth_set']),
                                           frac=rate(sum(1 for u in units if set(u['r1_delays']) == u['truth_set']), n)))
    # ---- P5
    p5 = {}
    for s in sorted({u['snr'] for u in units}):
        sub = [u for u in units if u['snr'] == s]
        h = [u for u in sub if u['arms']['A5']['ok'] and not u['arms']['A2']['ok']]
        k = sum(1 for u in h if u['arms']['A2']['doublets'])
        p5[str(s)] = dict(n_units=len(sub), n_A2_harm=len(h), A2_harm_with_doublet=k, frac=rate(k, len(h)),
                          frac_all_units_with_A2_doublet=rate(sum(1 for u in sub if u['arms']['A2']['doublets']), len(sub)))
    res['P5_per_snr'] = p5
    return res


def f(x, spec='.4f'):
    return 'n/a' if x is None else format(x, spec)


def render(res, title):
    L = [f'# {title} ({LABEL})', '', f"units: {res['n_units']}; N = {res['N']}; r1 duplicate-delay units: {res['r1_unique_delays']['units_with_duplicate_r1_delays']}; "
         f"edit replay consistent (A1, A2): {res['edit_replay_consistent_units']}", '',
         '## P1 doublet census (final geometry; pairs of equal-delay paths)', '',
         '| arm | units with doublet | frac | pairs total | mean pairs/unit | |D_N| hist [0,.2) / [.2,.5) / [.5,.8) / [.8,1] |', '|---|---|---|---|---|---|']
    for a, x in res['P1_census'].items():
        h = x['hist_abs_DN']
        L.append(f"| {a} | {x['units_with_doublet']} | {f(x['frac_units_with_doublet'])} | {x['doublet_pairs_total']} | {x['mean_pairs_per_unit']:.4f} | "
                 + ' / '.join(str(h[b]) for b in BIN_NAMES) + ' |')
    L += ['', 'Accepted edits by replacement type (shares = replacement delay equals another current path\'s delay -> doublet created; same_slot = Doppler-only move; new = delay absent from the current set):', '',
          '| arm | edits | shares | same_slot | new | new in truth set | new not in truth | shares in truth | shares not in truth |', '|---|---|---|---|---|---|---|---|---|']
    for a, x in res['P1_edit_categories'].items():
        c, fr = x['counts'], x['fractions']
        L.append(f"| {a} | {x['accepted_edits']} | {c['shares']} ({f(fr['shares'])}) | {c['same_slot']} ({f(fr['same_slot'])}) | {c['new']} ({f(fr['new'])}) | "
                 f"{x['new_delay_in_truth']} | {x['new_delay_not_in_truth']} | {x['shares_delay_in_truth']} | {x['shares_delay_not_in_truth']} |")
    p2 = res['P2']
    L += ['', '## P2 outcome versus doublet', '', '| arm | doublet & success | doublet & fail | no doublet & success | no doublet & fail | fail rate with / without doublet |', '|---|---|---|---|---|---|']
    for a in ('A2', 'A1'):
        t = p2[f'{a}_doublet_x_success']
        L.append(f"| {a} | {t['doublet_success']} | {t['doublet_fail']} | {t['nodoublet_success']} | {t['nodoublet_fail']} | "
                 f"{f(t['fail_rate_with_doublet'])} / {f(t['fail_rate_without_doublet'])} |")
    h = p2['A2_harm_units']
    L += ['', f"A2 harm units (A5 success, A2 fail): n = {h['n']}; with A2 doublet = {h['with_A2_doublet']} ({f(h['frac_with_A2_doublet'])}); "
          f"with an A2 edit that shares a delay = {h['with_A2_edit_sharing_a_delay']} ({f(h['frac_with_A2_edit_sharing_a_delay'])}); "
          f"comparators: A5-ok & A2-ok units with A2 doublet = {f(h['comparator_A5_ok_and_A2_ok']['frac_with_A2_doublet'])} (n = {h['comparator_A5_ok_and_A2_ok']['n']}), "
          f"all units = {f(h['comparator_all_units_frac_with_A2_doublet'])}; |D_N| hist of their doublets: {h['hist_abs_DN_of_doublets_in_harm_units']}; "
          f"harm units without doublet but with a changed delay set: {h['harm_units_without_A2_doublet_with_support_change']}", '']
    r = p2['A1_only_rescues']
    L += [f"A1-only rescues (A1 success, A2 fail): n = {r['n']}; A1 introduced >=1 new delay in the truth set: {r['A1_introduced_new_delay_in_truth_set_ge1']} ({f(r['frac_ge1_in_truth'])}); "
          f">=1 new delay not in the truth set: {r['A1_introduced_new_delay_not_in_truth_set_ge1']} ({f(r['frac_ge1_not_in_truth'])}); no new delay: {r['A1_introduced_no_new_delay']}; "
          f"all new delays in truth: {r['A1_introduced_new_delays_all_in_truth']}; A1 with a final doublet: {r['A1_with_doublet']}", '',
          '## P3 failure rate among units with >=1 doublet, by max |D_N| (Wilson 95%)', '', '| arm | bin | n | fail | fail rate | Wilson 95% |', '|---|---|---|---|---|---|']
    for a in ('A2', 'A1'):
        for b, x in res['P3'][a]['by_max_abs_DN_bin'].items():
            w = x['wilson95']
            L.append(f"| {a} | {b} | {x['n']} | {x['fail']} | {f(x['fail_rate'])} | {'n/a' if w is None else f'[{w[0]:.4f}, {w[1]:.4f}]'} |")
        x = res['P3'][a]['all_units_with_doublet']
        w = x['wilson95']
        L.append(f"| {a} | all | {x['n']} | {x['fail']} | {f(x['fail_rate'])} | {'n/a' if w is None else f'[{w[0]:.4f}, {w[1]:.4f}]'} |")
    for a, x in res['P3b_abs_dnu_of_doublets'].items():
        L.append(f"|dnu| of {a} doublets: pairs {x['pairs']}; quantiles {x['abs_dnu_quantiles']}; frac |dnu|<=0.25: {f(x['frac_abs_dnu_le_0p25'])}, <=0.5: {f(x['frac_abs_dnu_le_0p5'])}, "
                 f">=1: {f(x['frac_abs_dnu_ge_1'])}; frac |D_N|>=0.9: {f(x['frac_abs_DN_ge_0p9'])}")
    L.append('')
    q = res['P4']
    L += ['', '## P4 truth check', '',
          f"units whose truth geometry has duplicate delays: {q['units_with_duplicate_truth_delays']}; A2 doublet pairs: {q['A2_doublet_pairs']}, shared delay in truth set: "
          f"{q['A2_doublet_shared_delay_in_truth_set']} ({f(q['frac_A2_doublet_delay_in_truth'])}), shared delay with two truth paths: {q['A2_doublet_shared_delay_has_two_truth_paths']}; "
          f"A1 doublet pairs: {q['A1_doublet_pairs']}, shared delay in truth set: {q['A1_doublet_shared_delay_in_truth_set']}", '',
          '| final delay set == truth delay set | units | frac |', '|---|---|---|', f"| r1 (before any branch) | {q['r1_delay_set_equals_truth_set']['units']} | {f(q['r1_delay_set_equals_truth_set']['frac'])} |"]
    for a, x in q['final_delay_set_equals_truth_set'].items():
        L.append(f"| {a} | {x['units']} | {f(x['frac'])} |")
    L += ['', '## P5 per SNR: fraction of A2 harm units with an A2 doublet', '', '| snr (centi-dB) | units | A2 harm | harm with doublet | frac | frac of all units with A2 doublet |', '|---|---|---|---|---|---|']
    for s, x in res['P5_per_snr'].items():
        L.append(f"| {s} | {x['n_units']} | {x['n_A2_harm']} | {x['A2_harm_with_doublet']} | {f(x['frac'])} | {f(x['frac_all_units_with_A2_doublet'])} |")
    return '\n'.join(L) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    units = load(a.rows)
    out = dict(label=LABEL, primary=analyse(units),
               secondary_snr_6p5_to_8p0=analyse([u for u in units if u['snr'] in SECONDARY_SNR]))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'posthoc_doublet.json').write_text(json.dumps(out, indent=1) + '\n')
    md = f'# E-1 doublet analysis ({LABEL}; descriptive, not part of the frozen verdict)\n\n' + render(out['primary'], 'PRIMARY (all triggered keys)') \
        + '\n\n' + render(out['secondary_snr_6p5_to_8p0'], 'SECONDARY (SNR 6.5..8.0 dB)')
    (a.out / 'posthoc_doublet.md').write_text(md)
    print(md)


if __name__ == '__main__':
    main()
