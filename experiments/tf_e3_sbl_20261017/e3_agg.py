#!/usr/bin/env python
"""E-3 aggregation: the frozen criteria X1-X3 and the five-way verdict (design.md section 5), the co-delay census with the genie excess,
FER crossings, NMSE and cost.  numpy + math only (statistics primitives from the frozen e1_agg.py).

Unit = key (cell, SNR, frame) of the main run, all frames (unconditional FER, not conditioned on F0).  Variants: L-hard, L-diag, L-cov, L-genie.
Cluster for the bootstrap = (scenario, rho, frame); 20000 resamples, seed 20261017, percentile 95% CI.
  excess      E_v = mean(n_pair | v) - mean(n_pair | L-genie), n_pair = number of same-delay pairs among the output atoms (per frame)
  X1-diag     CI_lo(E_L-diag) > 0          X1-hard  CI_lo(E_L-hard) > 0       X1 = X1-diag (hard reported separately)
  X2          R_ph = E_L-cov / E_L-diag has CI_hi <= .25; evaluated only when X1-diag holds (E_L-diag > 0 in every needed resample)
  X3          exact one-sided McNemar (L-cov better than L-diag) significant at .05 AND CI_lo(FER_L-diag - FER_L-cov) > 0
  verdict     1 ABSENT (neither X1-diag nor X1-hard)  2 NO-FIX (X1-diag, not X2)  3 MECHANISM-ONLY (X1-diag, X2, not X3)
              4 GENERAL (X1-diag, X2, X3)  5 HARD-ONLY (only X1-hard)
Always printed with CI-contains-0 results: "not significant != equivalent".
Diagnostics (PROTOCOL.md section 11 O3): per-variant share of SBL runs that hit max_iter (stop rule not met), stage 1 and stage 2 separately.
R-iter check (O2, report-only, separate section; --riter DIR): the frozen 200 keys re-run with max_iter = 400 for L-diag and L-cov, side by side with
the 100-iteration main rows on the same keys; FLAG: if L-diag's genie excess at 400 iterations is < 50% of its 100-iteration excess on the same keys,
X1-diag must be labelled "budget-dependent".
Usage: python e3_agg.py --rows out/main --grid out/calibrate/GRID.json [--gates out/gate/gates.json] [--riter out/riter] --out out/analysis
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

sys.path.insert(0, str(HERE))
import e3_calib  # noqa: E402

VARIANTS = ('L-hard', 'L-diag', 'L-cov', 'L-genie')
CELLS = (('U', 300), ('U', 500), ('G', 300), ('G', 500))
MAIN_FRAMES = (4000, 4400)
SEED, N_BOOT, LIMIT = e1_agg.SEED, e1_agg.N_BOOT, e1_agg.DEGENERATE_LIMIT
R_PH_LIMIT = .25
ALPHA = .05
NOTE_CI0 = 'CI contains 0: not significant != equivalent'
BINS = ((0., .2), (.2, .5), (.5, .8), (.8, 1.0001))
BIN_NAMES = ('[0,.2)', '[.2,.5)', '[.5,.8)', '[.8,1]')
CROSS_LEVEL = 1e-2
RITER_FLAG_FRACTION = .5


def cell_name(scenario, rho_permille):
    return f'{scenario}_{rho_permille}'


# ----------------------------------------------------------------------------- statistics
def mcnemar_log10p(b, c):
    n = b + c
    if n == 0:
        return 0.0
    return log10(sum(comb(n, i) for i in range(b, n + 1))) - n * log10(2)


def mcnemar(x, y):
    """Exact one-sided McNemar for H1: P(x succeeds) > P(y succeeds) (x, y boolean success vectors)."""
    x, y = np.asarray(x, bool), np.asarray(y, bool)
    b, c = int(np.sum(x & ~y)), int(np.sum(~x & y))
    lp = mcnemar_log10p(b, c)
    return dict(b=b, c=c, log10_p=lp, significant=bool(lp < log10(ALPHA)))


def quantities(vals, cluster_ids, n_boot=N_BOOT, seed=SEED):
    """Bootstrap means of per-unit values; vals: name -> per-unit array (n_pair differences, FER indicators)."""
    rates, m = e1_agg.bootstrap_rates(vals, cluster_ids, n_boot, seed)
    point = {k: float(np.mean(v)) for k, v in vals.items()}

    def ci_of(x):
        lo, hi = e1_agg.ci(x)
        return dict(ci_lo=lo, ci_hi=hi, ci_width=hi - lo, contains_0=bool(lo <= 0 <= hi))
    out = dict(n_clusters=int(m), n_boot=int(n_boot), seed=int(seed), point=point,
               E={v: dict(point=point[f'E_{v}'], **ci_of(rates[f'E_{v}'])) for v in ('L-hard', 'L-diag', 'L-cov')},
               fer={v: dict(point=point[f'fer_{v}'], **ci_of(rates[f'fer_{v}'])) for v in VARIANTS},
               fer_diff_diag_minus_cov=dict(point=point['fer_L-diag'] - point['fer_L-cov'], **ci_of(rates['fer_L-diag'] - rates['fer_L-cov'])),
               fer_diff_hard_minus_cov=dict(point=point['fer_L-hard'] - point['fer_L-cov'], **ci_of(rates['fer_L-hard'] - rates['fer_L-cov'])))
    den, num = rates['E_L-diag'], rates['E_L-cov']
    nonpos = float(np.mean(~(den > 0)))
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(den > 0, num / np.where(den > 0, den, 1.), np.nan)
    c = e1_agg.ci(ratio)
    d_p = point['E_L-diag']
    out['R_ph'] = dict(point=(point['E_L-cov'] / d_p if d_p > 0 else None), ci_lo=None if c is None else c[0], ci_hi=None if c is None else c[1],
                       denominator_nonpositive_fraction=nonpos, evaluable=bool(d_p > 0 and nonpos <= LIMIT and c is not None))
    return out


def verdict(x1_diag, x1_hard, x2, x3):
    """Five-way verdict (design section 5), in order, mutually exclusive.  x2 / x3 may be None (not evaluable) -> treated as not holding."""
    if not x1_diag and not x1_hard:
        label = 'ABSENT'
    elif x1_diag and not x2:
        label = 'NO-FIX'
    elif x1_diag and x2 and not x3:
        label = 'MECHANISM-ONLY'
    elif x1_diag and x2 and x3:
        label = 'GENERAL'
    else:
        label = 'HARD-ONLY'
    return label


def criteria(q, mc_cov_diag):
    x1_diag = bool(q['E']['L-diag']['ci_lo'] > 0)
    x1_hard = bool(q['E']['L-hard']['ci_lo'] > 0)
    r = q['R_ph']
    x2 = None if not x1_diag else bool(r['evaluable'] and r['ci_hi'] <= R_PH_LIMIT)
    fd = q['fer_diff_diag_minus_cov']
    x3 = bool(mc_cov_diag['significant'] and fd['ci_lo'] > 0)
    return dict(X1_diag=x1_diag, X1_hard=x1_hard, X2=x2, X3=x3, X3_mcnemar_significant=bool(mc_cov_diag['significant']), X3_fer_diff_ci_lo_positive=bool(fd['ci_lo'] > 0),
                verdict=verdict(x1_diag, x1_hard, x2, x3))


# ----------------------------------------------------------------------------- loading, integrity
def load_rows(rows_dir):
    rows = []
    for p in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as handle:
            rows += [json.loads(line) for line in handle if line.strip()]
    return rows


def key_of(r):
    return (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])


def expected_keys(grid):
    keys = set()
    for sc, rho in CELLS:
        e = grid['cells'][cell_name(sc, rho)]
        if e['status'] == 'OK':
            keys |= {(sc, rho, int(s * 100), f) for s in e['grid_db'] for f in range(*MAIN_FRAMES)}
    return keys


def integrity(rows, want):
    errors = [r for r in rows if r.get('status') == 'error']
    good = [r for r in rows if 'variants' in r]
    got = [key_of(r) for r in rows]
    problems = []
    if len(set(got)) != len(got):
        problems.append('duplicate rows')
    if want is not None and set(got) != want:
        problems.append(f'row/key mismatch: {len(set(got) ^ want)} keys differ')
    if errors:
        problems.append(f'{len(errors)} error rows')
    miss = sum(1 for r in good if set(r['variants']) != set(VARIANTS))
    if miss:
        problems.append(f'{miss} rows without all four variants')
    gd = [r['gamma_diag_rel_err'] for r in good if 'gamma_diag_rel_err' in r]
    if gd and max(gd) >= 1e-10:
        problems.append(f'diag(Gamma) != sum(v): worst {max(gd)}')
    jit = sum(v['sbl']['jitter_events'] for r in good for v in r['variants'].values()) + sum(r['stage1']['jitter_events'] for r in good)
    return dict(n_rows=len(rows), n_keys=None if want is None else len(want), n_error_rows=len(errors), worst_gamma_diag_rel_err=max(gd) if gd else None,
                cholesky_jitter_events=int(jit), non_converged_sbl=sum(1 for r in good for v in r['variants'].values() if not v['sbl']['converged']),
                problems=problems, ok=not problems)


# ----------------------------------------------------------------------------- census, crossings, tables
def dn_bin(v):
    for i, (lo, hi) in enumerate(BINS):
        if lo <= v < hi:
            return i
    raise ValueError(v)


def rate(k, n):
    return None if n == 0 else k / n


def census(rows):
    out = {}
    genie = np.array([r['variants']['L-genie']['n_pair'] for r in rows], float)
    for v in VARIANTS:
        npair = np.array([r['variants'][v]['n_pair'] for r in rows], float)
        pairs = [p for r in rows for p in r['variants'][v]['pairs']]
        hist = [0] * len(BINS)
        for p in pairs:
            hist[dn_bin(p['dn'])] += 1
        out[v] = dict(units=len(rows), frac_units_with_pair=float(np.mean(npair > 0)), mean_n_pair=float(npair.mean()),
                      excess_vs_genie=float(npair.mean() - genie.mean()), pairs=len(pairs), hist_abs_DN=dict(zip(BIN_NAMES, hist)),
                      frac_pairs_on_true_delay=rate(sum(1 for p in pairs if p['true_delay']), len(pairs)),
                      mean_n_atoms=float(np.mean([r['variants'][v]['n_atoms'] for r in rows])),
                      median_abs_dnu=(float(np.median([p['dnu'] for p in pairs])) if pairs else None))
    return out


def crossing(snrs, fers, n_per_point, level=CROSS_LEVEL):
    """SNR (dB) at which the FER curve first reaches ``level`` (linear interpolation of log10 FER between grid points; FER = 0 is floored
    at 0.5/n).  Returns '<=s_min' if the first grid point is already below, None if never reached."""
    if not snrs:
        return None
    floor = .5 / max(n_per_point)
    lf = [np.log10(max(f, floor)) for f in fers]
    ll = np.log10(level)
    if fers[0] <= level:
        return f'<={snrs[0]}'
    for i in range(1, len(snrs)):
        if fers[i] <= level:
            t = (lf[i - 1] - ll) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.0
            return float(snrs[i - 1] + t * (snrs[i] - snrs[i - 1]))
    return None


def tables(rows):
    out = dict(per_cell={}, crossings={})
    for sc, rho in CELLS:
        sub = [r for r in rows if r['scenario'] == sc and r['rho_permille'] == rho]
        if not sub:
            continue
        snrs = sorted({r['snr_centi_db'] for r in sub})
        cell = {}
        for s in snrs:
            ss = [r for r in sub if r['snr_centi_db'] == s]
            cell[str(s)] = dict(n=len(ss), fer={v: float(np.mean([r['variants'][v]['fer'] for r in ss])) for v in VARIANTS},
                                mean_n_pair={v: float(np.mean([r['variants'][v]['n_pair'] for r in ss])) for v in VARIANTS},
                                nmse_db_median={v: float(10 * np.log10(np.median([r['variants'][v]['nmse'] for r in ss]))) for v in VARIANTS},
                                stage1_nmse_db_median=float(10 * np.log10(np.median([r['stage1']['nmse'] for r in ss]))),
                                round1_fer=float(np.mean([r['round1']['info_errors'] > 0 for r in ss])))
        out['per_cell'][cell_name(sc, rho)] = cell
        xs = [s / 100 for s in snrs]
        n_pt = [cell[str(s)]['n'] for s in snrs]
        out['crossings'][cell_name(sc, rho)] = {v: crossing(xs, [cell[str(s)]['fer'][v] for s in snrs], n_pt) for v in VARIANTS}
    return out


def cost_table(rows):
    keys = ('stage1_screen', 'stage1_sbl', 'round1_detect', 'round1_decode', 'stage2_screen', 'total')
    out = dict(keys=len(rows), per_key={k: float(np.mean([r['seconds'][k] for r in rows])) for k in keys},
               gen_seconds_per_key=float(np.mean([r.get('gen_seconds', 0.) for r in rows])), variants={})
    for v in VARIANTS:
        out['variants'][v] = {k: float(np.mean([r['variants'][v]['seconds'][k] for r in rows])) for k in ('columns', 'sbl', 'detect', 'decode', 'total')}
        out['variants'][v]['sbl_iterations_mean'] = float(np.mean([r['variants'][v]['sbl']['iterations'] for r in rows]))
        out['variants'][v]['sbl_start_atoms_mean'] = float(np.mean([r['variants'][v]['sbl']['n_start'] for r in rows]))
    out['total_core_hours'] = float((sum(r['seconds']['total'] + r.get('gen_seconds', 0.) for r in rows)) / 3600)
    return out


def iter_cap_share(rows):
    """Share of SBL runs that hit max_iter (the 1e-4 stop rule was not met), stage 1 and stage 2 per variant (PROTOCOL.md section 11 O3)."""
    n = len(rows)
    out = dict(runs=n, stage1=float(np.mean([not r['stage1']['converged'] for r in rows])), stage2={})
    for v in VARIANTS:
        out['stage2'][v] = float(np.mean([not r['variants'][v]['sbl']['converged'] for r in rows]))
    return out


def riter_flag(excess_100, excess_400):
    """Frozen rule: X1-diag is "budget-dependent" iff the genie excess of L-diag at 400 iterations is < 50% of its 100-iteration excess on the same keys.
    Not applicable when the 100-iteration excess is not positive."""
    if not excess_100 > 0:
        return 'not applicable (100-iteration excess <= 0)'
    return 'budget-dependent' if excess_400 < RITER_FLAG_FRACTION * excess_100 else 'not budget-dependent'


def analyse_riter(main_rows, riter_rows):
    """Side-by-side 100- vs 400-iteration comparison on the riter keys (L-diag, L-cov); genie stays at its 100-iteration value."""
    main = {key_of(r): r for r in main_rows if 'variants' in r}
    ok = [r for r in riter_rows if 'variants' in r]
    pairs = [(main[key_of(r)], r) for r in ok if key_of(r) in main]
    out = dict(n_riter_rows=len(riter_rows), n_error_rows=len(riter_rows) - len(ok), n_matched=len(pairs), n_unmatched=len(ok) - len(pairs))
    if not pairs:
        out['flag'] = 'not applicable (no matched keys)'
        return out
    mism = [key_of(r) for m, r in pairs if m['round1']['decoded_sha256'] != r['round1']['decoded_sha256'] or m['stage1']['atoms'] != r['stage1']['atoms']
            or m['n_candidates_stage2'] != r['n_candidates_stage2']]
    out['reused_pipeline_mismatches'] = len(mism)
    genie = float(np.mean([m['variants']['L-genie']['n_pair'] for m, _ in pairs]))
    out['genie_mean_n_pair_100'] = genie
    out['variants'] = {}
    for v in ('L-diag', 'L-cov'):
        n100 = np.array([m['variants'][v]['n_pair'] for m, _ in pairs], float)
        n400 = np.array([r['variants'][v]['n_pair'] for _, r in pairs], float)
        out['variants'][v] = dict(
            iter100=dict(mean_n_pair=float(n100.mean()), genie_excess=float(n100.mean() - genie), fer=float(np.mean([m['variants'][v]['fer'] for m, _ in pairs])),
                         cap_share=float(np.mean([not m['variants'][v]['sbl']['converged'] for m, _ in pairs]))),
            iter400=dict(mean_n_pair=float(n400.mean()), genie_excess=float(n400.mean() - genie), fer=float(np.mean([r['variants'][v]['fer'] for _, r in pairs])),
                         cap_share=float(np.mean([not r['variants'][v]['sbl']['converged'] for _, r in pairs])),
                         mean_iterations=float(np.mean([r['variants'][v]['sbl']['iterations'] for _, r in pairs]))))
    d = out['variants']['L-diag']
    out['flag'] = riter_flag(d['iter100']['genie_excess'], d['iter400']['genie_excess'])
    out['x1_diag_label'] = 'budget-dependent' if out['flag'] == 'budget-dependent' else None
    out['flag_rule'] = f'L-diag genie excess at 400 iterations < {RITER_FLAG_FRACTION:.0%} of its 100-iteration excess on the same keys -> X1-diag labelled "budget-dependent"'
    return out


def analyse(rows, grid=None, gates=None, n_boot=N_BOOT, seed=SEED, expected=None, riter_rows=None):
    gate_ok = None if gates is None else bool(gates.get('all_pass'))
    want = expected if expected is not None else (None if grid is None else expected_keys(grid))
    integ = integrity(rows, want)
    good = [r for r in rows if 'variants' in r]
    res = dict(integrity=integ, gates_all_pass=gate_ok, interpretable=bool(integ['ok'] and gate_ok is not False), n_units=len(good), grid=grid)
    if not good:
        return res
    npair = {v: np.array([r['variants'][v]['n_pair'] for r in good], float) for v in VARIANTS}
    fer = {v: np.array([r['variants'][v]['fer'] for r in good], float) for v in VARIANTS}
    vals = {f'E_{v}': npair[v] - npair['L-genie'] for v in ('L-hard', 'L-diag', 'L-cov')}
    vals.update({f'fer_{v}': fer[v] for v in VARIANTS})
    ids = [f"{r['scenario']}|{r['rho_permille']}|{r['frame']}" for r in good]
    q = quantities(vals, ids, n_boot, seed)
    mc_cov_diag = mcnemar(fer['L-cov'] == 0, fer['L-diag'] == 0)
    mc_cov_hard = mcnemar(fer['L-cov'] == 0, fer['L-hard'] == 0)
    crit = criteria(q, mc_cov_diag)
    res.update(quantities=q, criteria=crit, final_verdict=crit['verdict'] if res['interpretable'] else 'NOT_INTERPRETABLE (integrity/gates)',
               mcnemar=dict(cov_better_than_diag=mc_cov_diag, cov_better_than_hard=mc_cov_hard,
                            diag_better_than_cov=mcnemar(fer['L-diag'] == 0, fer['L-cov'] == 0)),
               fer_sanity=dict(genie=q['fer']['L-genie']['point'], note='L-genie FER is the grid-mismatch baseline (no data uncertainty)'),
               census=census(good), nmse_db_median={v: float(10 * np.log10(np.median([r['variants'][v]['nmse'] for r in good]))) for v in VARIANTS},
               stage1_nmse_db_median=float(10 * np.log10(np.median([r['stage1']['nmse'] for r in good]))),
               round1_fer=float(np.mean([r['round1']['info_errors'] > 0 for r in good])), note_ci0=NOTE_CI0, cost=cost_table(good), iter_cap=iter_cap_share(good), **tables(good))
    if riter_rows is not None:
        res['riter'] = analyse_riter(good, riter_rows)
    return res


def _f(x, spec='+.4f'):
    return 'n/a' if x is None else format(x, spec)


def render_md(res):
    L = ['# E-3 aggregate', '', f"interpretable: {res['interpretable']}; gates_all_pass: {res['gates_all_pass']}; units: {res['n_units']}", '',
         f"integrity: {json.dumps(res['integrity'], default=str)}", '']
    if 'criteria' not in res:
        return '\n'.join(L) + '\n'
    c, q = res['criteria'], res['quantities']
    L += [f"## Verdict: **{res['final_verdict']}**", '', f"X1-diag={c['X1_diag']}  X1-hard={c['X1_hard']}  X2={c['X2']}  X3={c['X3']} "
          f"(McNemar significant: {c['X3_mcnemar_significant']}, FER-diff CI_lo > 0: {c['X3_fer_diff_ci_lo_positive']})", '',
          f"## Phantom excess E_v = mean(n_pair | v) - mean(n_pair | L-genie) (cluster bootstrap {q['n_boot']} resamples, seed {q['seed']}); {NOTE_CI0}", '',
          '| variant | E_v | 95% CI | width | contains 0 |', '|---|---|---|---|---|']
    for v, x in q['E'].items():
        L.append(f"| {v} | {x['point']:+.5f} | [{x['ci_lo']:+.5f}, {x['ci_hi']:+.5f}] | {x['ci_width']:.5f} | {x['contains_0']}" + (f" ({NOTE_CI0})" if x['contains_0'] else '') + ' |')
    r = q['R_ph']
    L += ['', f"R_ph = E_L-cov / E_L-diag: {_f(r['point'])} CI [{_f(r['ci_lo'])}, {_f(r['ci_hi'])}] (limit {R_PH_LIMIT}); denominator<=0 fraction {r['denominator_nonpositive_fraction']:.4f}; "
              f"evaluable {r['evaluable']}", '', '## FER (unconditional)', '', '| variant | FER | 95% CI |', '|---|---|---|']
    for v, x in q['fer'].items():
        L.append(f"| {v} | {x['point']:.5f} | [{x['ci_lo']:.5f}, {x['ci_hi']:.5f}] |")
    for key, label in (('fer_diff_diag_minus_cov', 'FER(L-diag) - FER(L-cov)'), ('fer_diff_hard_minus_cov', 'FER(L-hard) - FER(L-cov)')):
        x = q[key]
        L.append(f"\n{label}: {x['point']:+.5f} [{x['ci_lo']:+.5f}, {x['ci_hi']:+.5f}]" + (f"  ({NOTE_CI0})" if x['contains_0'] else ''))
    m = res['mcnemar']
    L += ['', '## Exact one-sided McNemar (log10 p)', '', '| test | b | c | log10 p |', '|---|---|---|---|']
    for k, x in m.items():
        L.append(f"| {k} | {x['b']} | {x['c']} | {x['log10_p']:.1f} |")
    L += ['', '## Co-delay census (final output atoms; pair = two atoms with equal delay)', '',
          '| variant | units with pair | mean n_pair | excess vs genie | pairs | |D_N| hist [0,.2)/[.2,.5)/[.5,.8)/[.8,1] | pairs on true delay | mean atoms | median |dnu| |', '|---|---|---|---|---|---|---|---|---|']
    for v, x in res['census'].items():
        L.append(f"| {v} | {x['frac_units_with_pair']:.4f} | {x['mean_n_pair']:.4f} | {x['excess_vs_genie']:+.4f} | {x['pairs']} | "
                 + '/'.join(str(x['hist_abs_DN'][b]) for b in BIN_NAMES) + f" | {_f(x['frac_pairs_on_true_delay'], '.4f')} | {x['mean_n_atoms']:.2f} | {_f(x['median_abs_dnu'], '.3f')} |")
    L += ['', f"NMSE (dB, median over units): stage 1 {res['stage1_nmse_db_median']:.2f}; " + '; '.join(f"{v} {x:.2f}" for v, x in res['nmse_db_median'].items()),
          f"round-1 FER (shared): {res['round1_fer']:.5f}", '', f"## FER crossing of {CROSS_LEVEL:g} (dB, per cell; interpolation of log10 FER)", '', '| cell | ' + ' | '.join(VARIANTS) + ' |', '|---|' + '---|' * len(VARIANTS)]
    for cname, x in res['crossings'].items():
        L.append(f"| {cname} | " + ' | '.join('never' if x[v] is None else (x[v] if isinstance(x[v], str) else f'{x[v]:.2f}') for v in VARIANTS) + ' |')
    L += ['', '## Per cell and SNR: FER / mean n_pair / median NMSE dB', '']
    for cname, cell in res['per_cell'].items():
        L += [f'### {cname}', '', '| snr (centi-dB) | n | FER ' + ' / '.join(VARIANTS) + ' | n_pair ' + ' / '.join(VARIANTS) + ' | NMSE dB ' + ' / '.join(VARIANTS) + ' |', '|---|---|---|---|---|']
        for s, x in cell.items():
            L.append(f"| {s} | {x['n']} | " + ' / '.join(f"{x['fer'][v]:.4f}" for v in VARIANTS) + ' | ' + ' / '.join(f"{x['mean_n_pair'][v]:.3f}" for v in VARIANTS)
                     + ' | ' + ' / '.join(f"{x['nmse_db_median'][v]:.1f}" for v in VARIANTS) + ' |')
        L.append('')
    ic = res['iter_cap']
    L += ['## SBL runs hitting max_iter (stop rule 1e-4 not met within 100 iterations)', '', f"stage 1 (shared): {ic['stage1']:.4f}; stage 2: " + '; '.join(f"{v} {x:.4f}" for v, x in ic['stage2'].items()), '']
    if 'riter' in res:
        rt = res['riter']
        L += ['## R-iter robustness check (report-only, pre-registered): 100 vs 400 iterations on the frozen keys', '',
              f"keys: {rt['n_matched']} matched ({rt['n_riter_rows']} riter rows, {rt['n_error_rows']} errors); reused-pipeline mismatches vs main rows: {rt.get('reused_pipeline_mismatches')}"]
        if 'variants' in rt:
            L += [f"genie mean n_pair (100 iterations, unchanged): {rt['genie_mean_n_pair_100']:.4f}", '',
                  '| variant | iters | mean n_pair | genie excess | FER | share at iteration cap |', '|---|---|---|---|---|---|']
            for v, x in rt['variants'].items():
                for k, label in (('iter100', 100), ('iter400', 400)):
                    y = x[k]
                    L.append(f"| {v} | {label} | {y['mean_n_pair']:.4f} | {y['genie_excess']:+.4f} | {y['fer']:.4f} | {y['cap_share']:.4f} |")
        L += ['', f"FLAG: **{rt['flag']}**  ({rt.get('flag_rule', '')})", '']
    L += ['## Cost (mean seconds per key)', '', json.dumps(res['cost'], indent=1)]
    if res.get('grid'):
        L += ['', '## Calibrated SNR grid (frozen rule, L-hard only)', '', json.dumps({k: v for k, v in res['grid'].items() if k != 'rows_md5'}, indent=1)]
    return '\n'.join(L) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--grid', type=Path)
    p.add_argument('--gates', type=Path)
    p.add_argument('--riter', type=Path, help='out/riter rows of the R-iter check (report-only section)')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--boot', type=int, default=N_BOOT)
    a = p.parse_args()
    grid = json.loads(a.grid.read_text()) if a.grid else None
    res = analyse(load_rows(a.rows), grid, json.loads(a.gates.read_text()) if a.gates else None, a.boot, riter_rows=load_rows(a.riter) if a.riter else None)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'e3_summary.json').write_text(json.dumps(res, indent=1, default=str) + '\n')
    (a.out / 'e3_summary.md').write_text(render_md(res))
    print(render_md(res))


if __name__ == '__main__':
    main()
