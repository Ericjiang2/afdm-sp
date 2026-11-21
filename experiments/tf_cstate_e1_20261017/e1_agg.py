#!/usr/bin/env python
"""E-1 aggregation with the statistics frozen in PROTOCOL.md sections 5 and 10 (no scipy; numpy + math only).

Unit = triggered key (scenario, rho, snr, frame).  Success of an arm = 0 information-bit errors versus truth.  Arms A1..A7.
Primary unit set = all triggered keys on the full P1 grid; pre-declared secondary = the SNR {6.5..8.0} subset, same rules.
Tests: exact one-sided McNemar K1 A1>A2, K2 A2>A5, K3 A1>A5 (alpha .05 each), K4 A1>A7 (reported).
CIs: cluster bootstrap (cluster = (scenario, rho, frame), 20000 resamples, seed 20261017, percentile), ratios computed per resample.
Verdict (section 10 O3): delta = .10; Delta_geo = R1-R5; S_Gamma = (R1-R2)/Delta_geo; F5 = (R1-R5)/R1; F7 = (R1-R7)/R1.
  KILL = CI_upper(F5) < delta (J3a) or CI_upper(F7) < delta (J3b); J1 = not KILL, K1 and K2 significant, CI_lower(S_Gamma) >= delta;
  J2 = not KILL, CI_upper(S_Gamma) < delta, K2 and K3 significant; else MIXED.  Evaluability is split by denominator:
  F5/F7 divide by R1 (kill_evaluable = point R1 > 0 and <= 1% of resamples with R1 = 0; CIs over resamples with R1 > 0; Delta_geo <= 0 is
  NOT degenerate for them: F5 <= 0 means J3a), S_Gamma and the ladder divide by Delta_geo (sgamma_evaluable = point Delta_geo > 0 and
  <= 1% of resamples with Delta_geo <= 0; CIs over resamples with Delta_geo > 0).
  Order: KILL if kill_evaluable and (J3a or J3b); else MIXED if not kill_evaluable or not sgamma_evaluable (note says which); else J1/J2/MIXED.
Usage: python e1_agg.py --rows out/main --keys out/select/triggered_keys.json [--gates out/gate/gates.json] --out out/main/analysis
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from math import comb
from pathlib import Path

import numpy as np

ARMS = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7')
BOOT_PAIRS = (('A1', 'A2'), ('A2', 'A5'), ('A1', 'A5'), ('A1', 'A3'), ('A2', 'A4'), ('A3', 'A6'), ('A6', 'A5'), ('A1', 'A7'))
K_TESTS = {'K1': ('A1', 'A2'), 'K2': ('A2', 'A5'), 'K3': ('A1', 'A5'), 'K4': ('A1', 'A7')}
VERDICT_K = ('K1', 'K2', 'K3')  # K4 is reported, not part of the verdict
ALPHA = .05
DELTA = .10
DEGENERATE_LIMIT = .01
N_BOOT = 20000
SEED = 20261017
CELLS = (('U', 300), ('U', 500), ('G', 300), ('G', 500))
SECONDARY_SNR = (650, 700, 750, 800)
RATIO_NAMES = ('S_Gamma', 'F5', 'F7', 'S_swap', 'S_local', 'S_refit', 'S_Gamma_noswap')
NOTE_CI0 = 'CI contains 0: not significant != equivalent'


# ----------------------------------------------------------------------------- statistics
def mcnemar_greater(x, y):
    """Exact one-sided McNemar for H1: P(x succeeds) > P(y succeeds); x, y boolean success vectors over the same units.
    b = #(x ok, y fail), c = #(x fail, y ok); p = P(Binomial(b + c, .5) >= b)."""
    x, y = np.asarray(x, bool), np.asarray(y, bool)
    b, c = int(np.sum(x & ~y)), int(np.sum(~x & y))
    n = b + c
    p = 1.0 if n == 0 else sum(comb(n, i) for i in range(b, n + 1)) / 2 ** n
    return dict(b=b, c=c, discordant=n, p=float(p))


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.
    for rank, i in enumerate(order):
        running = max(running, min(1., (len(p) - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def ratio_stats(R):
    """Section 10 O3 quantities from a dict of success rates (scalars or equal-length arrays).  F5/F7 divide by R_A1 and are NaN where
    R_A1 = 0; S_Gamma and the ladder shares divide by Delta_geo and are NaN where Delta_geo <= 0."""
    d = np.asarray(R['A1'] - R['A5'], float)
    with np.errstate(divide='ignore', invalid='ignore'):
        ok = d > 0
        safe = np.where(ok, d, np.nan)
        r1 = np.where(np.asarray(R['A1'], float) > 0, np.asarray(R['A1'], float), np.nan)
        return dict(Delta_geo=d,
                    S_Gamma=(R['A1'] - R['A2']) / safe, F5=d / r1, F7=(R['A1'] - R['A7']) / r1,
                    S_swap=(R['A1'] - R['A3']) / safe, S_local=(R['A3'] - R['A6']) / safe, S_refit=(R['A6'] - R['A5']) / safe,
                    S_Gamma_noswap=(R['A3'] - R['A4']) / safe)


def bootstrap_rates(success, cluster_ids, n_boot=N_BOOT, seed=SEED):
    """Resampled success rates of every arm: clusters drawn with replacement (multinomial counts), fixed seed."""
    arms = list(success)
    ids, inverse = np.unique(np.asarray(cluster_ids, object).astype(str), return_inverse=True)
    m = len(ids)
    cs = np.zeros((m, len(arms)))
    for j, a in enumerate(arms):
        cs[:, j] = np.bincount(inverse, weights=np.asarray(success[a], float), minlength=m)
    cn = np.bincount(inverse, minlength=m).astype(float)
    rng = np.random.default_rng(seed)
    out = {a: [] for a in arms}
    done = 0
    while done < n_boot:
        size = min(500, n_boot - done)
        counts = rng.multinomial(m, np.full(m, 1. / m), size=size).astype(float)
        num, den = counts @ cs, counts @ cn
        for j, a in enumerate(arms):
            out[a].append(num[:, j] / den)
        done += size
    return {a: np.concatenate(v) for a, v in out.items()}, m


def ci(values):
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return None
    lo, hi = np.percentile(v, [2.5, 97.5])
    return float(lo), float(hi)


def bootstrap_summary(success, cluster_ids, n_boot=N_BOOT, seed=SEED):
    """Difference CIs for BOOT_PAIRS and ratio CIs for section-10 quantities; degenerate-resample fraction and evaluability."""
    rates, m = bootstrap_rates(success, cluster_ids, n_boot, seed)
    point = {a: float(np.mean(success[a])) for a in success}
    diffs = {}
    for x, y in BOOT_PAIRS:
        lo, hi = ci(rates[x] - rates[y])
        diffs[f'{x}-{y}'] = dict(diff=point[x] - point[y], ci_lo=lo, ci_hi=hi, ci_width=hi - lo, ci_contains_0=bool(lo <= 0 <= hi),
                                 n_clusters=int(m), n_boot=int(n_boot), seed=int(seed))
    boot_r, pt_r = ratio_stats(rates), ratio_stats(point)
    r1_zero = float(np.mean(~(rates['A1'] > 0)))             # R_A1 = 0 (denominator of F5, F7)
    delta_nonpos = float(np.mean(~(boot_r['Delta_geo'] > 0)))  # Delta_geo <= 0 (denominator of S_Gamma and the ladder)
    kill_ok = bool(point['A1'] > 0 and r1_zero <= DEGENERATE_LIMIT)
    sg_ok = bool(pt_r['Delta_geo'] > 0 and delta_nonpos <= DEGENERATE_LIMIT)
    ratios = {}
    for name in RATIO_NAMES:
        by_r1 = name in ('F5', 'F7')
        c = ci(boot_r[name])  # NaN entries (undefined denominator) are dropped
        pt_defined = bool(point['A1'] > 0) if by_r1 else bool(pt_r['Delta_geo'] > 0)
        ratios[name] = dict(denominator='R_A1' if by_r1 else 'Delta_geo', point=float(pt_r[name]) if pt_defined else None,
                            ci_lo=None if c is None else c[0], ci_hi=None if c is None else c[1],
                            ci_width=None if c is None else c[1] - c[0])
    dg = ci(boot_r['Delta_geo'])
    return dict(rates_point=point, differences=diffs, ratios=ratios,
                Delta_geo=dict(point=float(pt_r['Delta_geo']), ci_lo=dg[0], ci_hi=dg[1]),
                r1_zero_fraction=r1_zero, delta_nonpos_fraction=delta_nonpos, kill_evaluable=kill_ok, sgamma_evaluable=sg_ok,
                n_clusters=int(m), n_boot=int(n_boot), seed=int(seed))


def verdict(k_sig, ratios, kill_evaluable, sgamma_evaluable):
    """Frozen rule (PROTOCOL.md section 10 O3, with the pre-run evaluability correction).  ratios: name -> dict with ci_lo/ci_hi (or None).
    1. kill_evaluable and (J3a or J3b) -> KILL (J3a: CI_upper(F5) < delta; J3b: CI_upper(F7) < delta).
    2. else if not kill_evaluable or not sgamma_evaluable -> MIXED, the note says which flag failed.
    3. else J1 (K1, K2 significant, CI_lower(S_Gamma) >= delta) / J2 (CI_upper(S_Gamma) < delta, K2, K3 significant) / MIXED."""
    out = dict(J3a=None, J3b=None, J3=None, J1=None, J2=None, kill_evaluable=bool(kill_evaluable), sgamma_evaluable=bool(sgamma_evaluable),
               fired=None, verdict='MIXED', note=None)
    if kill_evaluable:
        out['J3a'] = bool(ratios['F5']['ci_hi'] < DELTA)
        out['J3b'] = bool(ratios['F7']['ci_hi'] < DELTA)
        out['J3'] = out['J3a'] or out['J3b']
        out['fired'] = [n for n, f in (('J3a', out['J3a']), ('J3b', out['J3b'])) if f] or None
        if out['J3']:
            out['verdict'] = 'KILL'
            return out
    failed = [n for n, ok in (('kill criteria (F5/F7 divide by R_A1: point R_A1 = 0 or >1% of resamples with R_A1 = 0)', kill_evaluable),
                              ('S_Gamma/ladder (divide by Delta_geo: point Delta_geo <= 0 or >1% of resamples with Delta_geo <= 0)', sgamma_evaluable))
              if not ok]
    if failed:
        out['note'] = 'not evaluable: ' + '; '.join(failed)
        return out
    out['J1'] = bool(k_sig['K1'] and k_sig['K2'] and ratios['S_Gamma']['ci_lo'] >= DELTA)
    out['J2'] = bool(ratios['S_Gamma']['ci_hi'] < DELTA and k_sig['K2'] and k_sig['K3'])
    out['verdict'] = 'J1' if out['J1'] else 'J2' if out['J2'] else 'MIXED'
    return out


# ----------------------------------------------------------------------------- loading and integrity
def load_rows(rows_dir):
    rows = []
    for p in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as handle:
            rows += [json.loads(line) for line in handle if line.strip()]
    return rows


def key_of(r):
    return (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])


def integrity(rows, keys):
    want = {(u['scenario'], u['rho_permille'], u['snr_centi_db'], u['frame']) for u in keys} if keys is not None else None
    got = [key_of(r) for r in rows]
    problems = []
    if len(set(got)) != len(got):
        problems.append('duplicate rows')
    if want is not None and set(got) != want:
        problems.append(f'row/key mismatch: {len(set(got) ^ want)} keys differ')
    bad = lambda f: sum(1 for r in rows if not f(r))  # noqa: E731
    checks = dict(
        g4a_ok=bad(lambda r: r['g4a_ok']), f0_matches_ledger=bad(lambda r: r['f0_matches_ledger']),
        a1_matches_ledger=bad(lambda r: r['a1_matches_ledger']), g5_ok=bad(lambda r: r.get('g5_ok')),
        arms_not_ok=bad(lambda r: all(r['arms'].get(a, {}).get('status') == 'ok' for a in ARMS)),
        units_with_nonzero_syndrome_not_failing_f0=sum(1 for r in rows if r['f0']['info_errors'] == 0))
    for name in ('g4a_ok', 'f0_matches_ledger', 'a1_matches_ledger', 'g5_ok', 'arms_not_ok'):
        if checks[name]:
            problems.append(f'{name}: {checks[name]} units fail')
    fallbacks = {a: sum(1 for r in rows if r['arms'].get(a, {}).get('numerical_fallback')) for a in ARMS}
    return dict(n_rows=len(rows), n_keys=None if want is None else len(want), checks=checks, numerical_fallbacks=fallbacks,
                problems=problems, ok=not problems)


# ----------------------------------------------------------------------------- analysis
def success_matrix(rows):
    return {a: np.array([r['arms'][a]['info_errors'] == 0 for r in rows], bool) for a in ARMS}


def per_arm_summary(rows, success):
    f0_ok = np.array([r['f0']['info_errors'] == 0 for r in rows], bool)
    out = {}
    for a in ARMS:
        s = success[a]
        out[a] = dict(n=len(rows), success=int(s.sum()), rate=float(s.mean()), rescued_vs_f0=int(np.sum(s & ~f0_ok)),
                      harmed_vs_f0=int(np.sum(~s & f0_ok)))
    return out


def per_snr_table(rows, success):
    snr = np.array([r['snr_centi_db'] for r in rows])
    out = {}
    for s in sorted(set(snr.tolist())):
        idx = snr == s
        out[str(s)] = dict(n=int(idx.sum()), rates={a: float(success[a][idx].mean()) for a in ARMS},
                           success={a: int(success[a][idx].sum()) for a in ARMS})
    return out


def cell_analysis(rows, success):
    res = {}
    for scenario, rho in CELLS:
        idx = np.array([r['scenario'] == scenario and r['rho_permille'] == rho for r in rows], bool)
        res[f'{scenario}_rho{rho}'] = dict(
            n=int(idx.sum()), success={a: int(success[a][idx].sum()) for a in ARMS},
            forward={k: mcnemar_greater(success[x][idx], success[y][idx]) for k, (x, y) in K_TESTS.items()},
            reverse={k: mcnemar_greater(success[y][idx], success[x][idx]) for k, (x, y) in K_TESTS.items()})
    names = list(res)
    for k in K_TESTS:
        for direction in ('forward', 'reverse'):
            adj = holm([res[c][direction][k]['p'] for c in names])
            for c, a in zip(names, adj):
                res[c][direction][k]['p_holm'] = a
    for c in names:
        res[c]['significant_reverse_effect'] = [k for k in K_TESTS if res[c]['reverse'][k]['p_holm'] < ALPHA]
    return res


def support_and_cost(rows):
    out = dict(support={}, cost={})
    non_geo = ('message_handling', 'y_transform', 'channel_construction', 'tf', 'ldpc', 'receive_rounds3')
    for a in ARMS:
        recs = [r['arms'][a] for r in rows]
        out['support'][a] = dict(mean_n_support_changes=float(np.mean([x['n_support_changes'] for x in recs])),
                                 mean_n_delay_replacements=float(np.mean([x['n_delay_replacements'] for x in recs])),
                                 mean_n_edits=float(np.mean([x['n_edits'] for x in recs])),
                                 frac_units_support_changed=float(np.mean([x['n_support_changes'] > 0 for x in recs])))
        sec = np.array([x['seconds'] for x in recs])
        out['cost'][a] = dict(mean_seconds=float(sec.mean()), median_seconds=float(np.median(sec)),
                              mean_tf_seconds=float(np.mean([x['stages'].get('tf', 0.) for x in recs])),
                              mean_ldpc_seconds=float(np.mean([x['stages'].get('ldpc', 0.) for x in recs])),
                              mean_geometry_seconds=float(np.mean([sum(v for k, v in x['stages'].items() if k not in non_geo) for x in recs])))
    out['cost']['A7']['mean_seconds_minus_f0_third_round_increment'] = float(np.mean([r['arms']['A7']['seconds_minus_f0'] for r in rows]))
    out['cost']['F0'] = dict(mean_seconds=float(np.mean([r['f0']['seconds'] for r in rows])))
    a1, a2 = [r['arms']['A1'] for r in rows], [r['arms']['A2'] for r in rows]
    same_edits = [[e['new'] for e in x['edits']] == [e['new'] for e in y['edits']] for x, y in zip(a1, a2)]
    same_top1 = [(x['top5_step1'][:1] == y['top5_step1'][:1]) for x, y in zip(a1, a2)]
    out['a1_vs_a2'] = dict(frac_same_accepted_edits=float(np.mean(same_edits)), frac_same_top1_candidate=float(np.mean(same_top1)))
    out['unit_core_seconds'] = dict(
        mean_gen=float(np.mean([r['gen_seconds'] for r in rows])), mean_f0=float(np.mean([r['f0']['seconds'] for r in rows])),
        mean_all_seven_arms=float(np.mean([sum(r['arms'][a]['seconds'] for a in ARMS) for r in rows])),
        total_core_hours=float(sum(r['gen_seconds'] + r['f0']['seconds'] + sum(r['arms'][a]['seconds'] for a in ARMS) for r in rows) / 3600))
    return out


def analyse(rows, keys=None, gates=None, n_boot=N_BOOT, seed=SEED):
    integ = integrity(rows, keys)
    gates_ok = None if gates is None else bool(gates.get('all_pass'))
    success = success_matrix(rows)
    cluster_ids = [f"{r['scenario']}|{r['rho_permille']}|{r['frame']}" for r in rows]
    k_res = {k: mcnemar_greater(success[x], success[y]) for k, (x, y) in K_TESTS.items()}
    for k in k_res:
        k_res[k]['significant'] = bool(k_res[k]['p'] < ALPHA)
    boot = bootstrap_summary(success, cluster_ids, n_boot, seed)
    desc = {}
    for x, y in BOOT_PAIRS:
        up, down = mcnemar_greater(success[x], success[y]), mcnemar_greater(success[y], success[x])
        desc[f'{x}-{y}'] = dict(b=up['b'], c=up['c'], p_two_sided=float(min(1., 2 * min(up['p'], down['p']))))
    v = verdict({k: k_res[k]['significant'] for k in VERDICT_K}, boot['ratios'], boot['kill_evaluable'], boot['sgamma_evaluable'])
    interpretable = bool(integ['ok'] and gates_ok is not False)
    return dict(n_units=len(rows), n_boot=int(n_boot), seed=int(seed), integrity=integ, gates_all_pass=gates_ok, interpretable=interpretable,
                per_arm=per_arm_summary(rows, success), per_snr=per_snr_table(rows, success), primary_mcnemar=k_res, bootstrap=boot,
                pairwise_mcnemar_descriptive=desc, criteria=v,
                final_verdict=v['verdict'] if interpretable else 'NOT_INTERPRETABLE (integrity/gates)',
                per_cell=cell_analysis(rows, success), note_ci0=NOTE_CI0, **support_and_cost(rows))


def analyse_both(rows, keys=None, gates=None, n_boot=N_BOOT, seed=SEED):
    """Primary = all rows; pre-declared secondary = SNR {6.5..8.0} subset, same rules."""
    res = analyse(rows, keys, gates, n_boot, seed)
    sub = [r for r in rows if r['snr_centi_db'] in SECONDARY_SNR]
    sub_keys = None if keys is None else [u for u in keys if u['snr_centi_db'] in SECONDARY_SNR]
    res['secondary_snr_6p5_to_8p0'] = analyse(sub, sub_keys, gates, n_boot, seed) if sub else None
    return res


def _fmt(x, spec='+.4f'):
    return 'n/a' if x is None else format(x, spec)


def render_block(res, title):
    L = [f'# {title}', '', f"units: {res['n_units']}  interpretable: {res['interpretable']}  FINAL: **{res['final_verdict']}**", '',
         f"integrity: {json.dumps(res['integrity'], default=str)}", f"gates_all_pass: {res['gates_all_pass']}", '',
         '## Per-arm success (0 info-bit errors)', '', '| arm | success | rate | rescued vs F0 | harmed vs F0 |', '|---|---|---|---|---|']
    for a, x in res['per_arm'].items():
        L.append(f"| {a} | {x['success']}/{x['n']} | {x['rate']:.4f} | {x['rescued_vs_f0']} | {x['harmed_vs_f0']} |")
    L += ['', '## Exact one-sided McNemar (alpha .05 each, pooled; K4 reported only)', '', '| test | b | c | p | significant |', '|---|---|---|---|---|']
    for k, x in res['primary_mcnemar'].items():
        L.append(f"| {k} {K_TESTS[k][0]}>{K_TESTS[k][1]} | {x['b']} | {x['c']} | {x['p']:.3g} | {x['significant']} |")
    b = res['bootstrap']
    L += ['', f"## Cluster-bootstrap 95% CI of rate difference ({res['n_boot']} resamples, seed {res['seed']}); {NOTE_CI0}", '',
          '| pair | diff | CI | width | contains 0 |', '|---|---|---|---|---|']
    for k, x in b['differences'].items():
        L.append(f"| {k} | {x['diff']:+.4f} | [{x['ci_lo']:+.4f}, {x['ci_hi']:+.4f}] | {x['ci_width']:.4f} | {x['ci_contains_0']}"
                 + (f" ({NOTE_CI0})" if x['ci_contains_0'] else '') + ' |')
    dg = b['Delta_geo']
    L += ['', f"## Ratio criteria (delta = {DELTA}); Delta_geo = R_A1 - R_A5 = {_fmt(dg['point'])} CI [{_fmt(dg['ci_lo'])}, {_fmt(dg['ci_hi'])}]",
          f"fraction of resamples with R_A1 = 0: {b['r1_zero_fraction']:.4f} -> kill_evaluable: {b['kill_evaluable']}; "
          f"with Delta_geo <= 0: {b['delta_nonpos_fraction']:.4f} -> sgamma_evaluable: {b['sgamma_evaluable']} (limit {DEGENERATE_LIMIT} each)", '',
          '| quantity (denominator) | point | CI | width |', '|---|---|---|---|']
    for name, x in b['ratios'].items():
        L.append(f"| {name} ({x['denominator']}) | {_fmt(x['point'])} | [{_fmt(x['ci_lo'])}, {_fmt(x['ci_hi'])}] | {_fmt(x['ci_width'], '.4f')} |")
    c = res['criteria']
    L += ['', f"J3a={c['J3a']} J3b={c['J3b']} (fired: {c['fired']}) J1={c['J1']} J2={c['J2']} -> **{c['verdict']}**" + (f" ({c['note']})" if c['note'] else ''),
          '', '## Per SNR (success rate R_x)', '', '| snr (centi-dB) | n | ' + ' | '.join(ARMS) + ' |', '|---|---|' + '---|' * len(ARMS)]
    for s, x in res['per_snr'].items():
        L.append(f"| {s} | {x['n']} | " + ' | '.join(f"{x['rates'][a]:.3f}" for a in ARMS) + ' |')
    L += ['', '## Per cell (Holm over 4 cells)', '', '| cell | n | succ A1..A7 | K1 p_holm | K2 p_holm | K3 p_holm | K4 p_holm | reverse effects |',
          '|---|---|---|---|---|---|---|---|']
    for name, x in res['per_cell'].items():
        L.append(f"| {name} | {x['n']} | {','.join(str(x['success'][a]) for a in ARMS)} | "
                 + ' | '.join(f"{x['forward'][k]['p_holm']:.3g}" for k in K_TESTS) + f" | {x['significant_reverse_effect'] or 'none'} |")
    L += ['', '## Cost (mean seconds per unit; A7 total is a from-scratch rounds=3 run, A7 - F0 is the third-round increment)', '',
          '| arm | mean s | A7-F0 |', '|---|---|---|']
    for a in ARMS:
        L.append(f"| {a} | {res['cost'][a]['mean_seconds']:.4f} | "
                 + (f"{res['cost']['A7']['mean_seconds_minus_f0_third_round_increment']:.4f}" if a == 'A7' else '') + ' |')
    L += [f"| F0 | {res['cost']['F0']['mean_seconds']:.4f} | |", '',
          '## Support changes and totals', '', json.dumps(dict(support=res['support'], a1_vs_a2=res['a1_vs_a2'], unit_core_seconds=res['unit_core_seconds']), indent=1)]
    return '\n'.join(L) + '\n'


def render_md(res):
    out = render_block(res, 'E-1 aggregate: PRIMARY (all triggered keys, full P1 grid)')
    if res.get('secondary_snr_6p5_to_8p0'):
        out += '\n\n' + render_block(res['secondary_snr_6p5_to_8p0'], 'E-1 aggregate: PRE-DECLARED SECONDARY (SNR 6.5..8.0 dB subset)')
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--keys', type=Path)
    p.add_argument('--gates', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--boot', type=int, default=N_BOOT)
    a = p.parse_args()
    rows = load_rows(a.rows)
    keys = json.loads(a.keys.read_text())['units'] if a.keys else None
    gates = json.loads(a.gates.read_text()) if a.gates else None
    res = analyse_both(rows, keys, gates, a.boot)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'e1_summary.json').write_text(json.dumps(res, indent=1, default=str) + '\n')
    (a.out / 'e1_summary.md').write_text(render_md(res))
    print(render_md(res))


if __name__ == '__main__':
    main()
