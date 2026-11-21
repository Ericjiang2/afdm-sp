#!/usr/bin/env python
"""E-3b aggregation: the frozen verdict of design.md section 3 plus the pre-registered readings.  numpy + math only (statistics primitives from the
frozen e3_agg.py / e1_agg.py).

Unit = key (scenario, rho .3, SNR 6..11 dB, frame 4000..4199), 2400 keys, unconditional FER.  Cluster for the bootstrap = (scenario, frame); 20000 resamples,
seed 20261017, percentile 95% CI, one paired resample for every quantity.
  A_on  = FER(L-cov)   - FER(L-diag)    (E-3 rows, same keys)         A_off = FER(cov-off) - FER(diag-off)        Delta = A_on - A_off
Verdict, first match wins (mutually exclusive):
  1 REVERSED  CI_hi(A_off) < 0                       and CI_lo(Delta) > 0     full Gamma better after refinement: interpolation explanation supported
  2 VANISHED  CI(A_off) inside [-.01, .01]           and CI_lo(Delta) > 0     advantage gone: interpolation explanation supported
  3 REDUCED   CI_lo(A_off) > 0                       and CI_lo(Delta) > 0     advantage smaller but present: explains part of it
  4 PERSISTS  CI_lo(A_off) > 0                       and CI_lo(Delta) <= 0    advantage unaffected: interpolation explanation rejected
  5 MIXED     none of the above
Also reported (not part of the verdict): exact one-sided McNemar diag-off vs cov-off (log10 p), per-variant on-grid / off-grid FER and 1e-2 crossings, the
same-delay census (n_pair is unchanged by the refinement because delays are fixed; |Delta nu| distribution after refinement), NMSE, refinement acceptance,
cost.  "CI contains 0" is always annotated: not significant != equivalent.
Aggregation refuses interpretation (interpretable = false) when: the row set differs from the frozen 2400 keys, any error row, a row without all four variants,
a missing / mismatching E-3 row (pairing), the on-grid stage differs from the E-3 row (stage-1 atoms, round-1 sha, candidate count, SBL output atoms), a
refinement invariant fails (monotone value, <= 16 evaluations, bounds, window), a gamma structure check fails, a smoke row is present, a manifest md5 differs,
or the gates are not all passed.
Usage: python e3b_agg.py --rows out/main --e3-rows ../tf_e3_sbl_20261017/out/main --gates out/gate/gates.json --out out/analysis
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3b_lib as lib  # noqa: E402

import e3_agg as base  # noqa: E402  (frozen E-3 aggregator: mcnemar, crossing, load_rows, primitives)

e1_agg = base.e1_agg
OFF, ONGRID = lib.OFF, lib.ONGRID
ON = tuple(ONGRID.values())
CELLS = (('U', 300), ('G', 300))
SEED, N_BOOT = e1_agg.SEED, e1_agg.N_BOOT
TOL = .01
NOTE_CI0 = 'CI contains 0: not significant != equivalent'
DNU_BINS = ((0., 1e-6), (1e-6, .1), (.1, .25), (.25, .5), (.5, 1.), (1., 99.))
DNU_NAMES = ('[0,1e-6)', '[1e-6,.1)', '[.1,.25)', '[.25,.5)', '[.5,1)', '[1,inf)')
READING = dict(REVERSED='post-hoc interpolation explanation SUPPORTED (after refinement the full Gamma is better than the scalar Gamma)',
               VANISHED='post-hoc interpolation explanation SUPPORTED (the scalar-Gamma advantage vanishes with continuous refinement)',
               REDUCED='post-hoc interpolation explanation PARTLY supported (the advantage shrinks but remains)',
               PERSISTS='post-hoc interpolation explanation REJECTED (the advantage is not affected by refinement)',
               MIXED='no determination under the frozen rules')


# ----------------------------------------------------------------------------- verdict
def verdict(a_off, delta):
    """Design section 3, in order.  a_off / delta: dicts with ci_lo, ci_hi."""
    if a_off['ci_hi'] < 0 and delta['ci_lo'] > 0:
        return 'REVERSED'
    if a_off['ci_lo'] >= -TOL and a_off['ci_hi'] <= TOL and delta['ci_lo'] > 0:
        return 'VANISHED'
    if a_off['ci_lo'] > 0 and delta['ci_lo'] > 0:
        return 'REDUCED'
    if a_off['ci_lo'] > 0 and delta['ci_lo'] <= 0:
        return 'PERSISTS'
    return 'MIXED'


def _ci(x):
    lo, hi = e1_agg.ci(x)
    return dict(ci_lo=lo, ci_hi=hi, ci_width=hi - lo, contains_0=bool(lo <= 0 <= hi))


def quantities(vals, ids, n_boot=N_BOOT, seed=SEED):
    """vals: name -> per-unit array (FER indicators of the 4 on-grid and 4 off-grid variants).  One paired cluster bootstrap for everything."""
    rates, m = e1_agg.bootstrap_rates(vals, ids, n_boot, seed)
    point = {k: float(np.mean(v)) for k, v in vals.items()}
    a_on_b = rates['on_L-cov'] - rates['on_L-diag']
    a_off_b = rates['off_cov-off'] - rates['off_diag-off']
    out = dict(n_clusters=int(m), n_boot=int(n_boot), seed=int(seed), point=point,
               fer_on={v: dict(point=point[f'on_{v}'], **_ci(rates[f'on_{v}'])) for v in ON},
               fer_off={v: dict(point=point[f'off_{v}'], **_ci(rates[f'off_{v}'])) for v in OFF},
               A_on=dict(point=point['on_L-cov'] - point['on_L-diag'], **_ci(a_on_b)),
               A_off=dict(point=point['off_cov-off'] - point['off_diag-off'], **_ci(a_off_b)),
               Delta=dict(point=(point['on_L-cov'] - point['on_L-diag']) - (point['off_cov-off'] - point['off_diag-off']), **_ci(a_on_b - a_off_b)),
               off_minus_on={f'{o}': dict(point=point[f'off_{o}'] - point[f'on_{ONGRID[o]}'], **_ci(rates[f'off_{o}'] - rates[f'on_{ONGRID[o]}'])) for o in OFF})
    return out


# ----------------------------------------------------------------------------- integrity
def integrity(rows, on, expected, manifest_bad=None, e3_manifest_bad=None):
    errors = [r for r in rows if r.get('status') == 'error']
    good = [r for r in rows if 'variants' in r]
    got = [lib.key_of(r) for r in rows]
    problems = []
    if len(set(got)) != len(got):
        problems.append('duplicate rows')
    if set(got) != expected:
        problems.append(f'row/key mismatch: {len(set(got) ^ expected)} keys differ')
    if errors:
        problems.append(f'{len(errors)} error rows (first: {errors[0].get("error")})')
    if sum(1 for r in good if set(r['variants']) != set(OFF)):
        problems.append('rows without all four off-grid variants')
    if sum(1 for r in good if r.get('smoke')):
        problems.append('smoke rows present')
    missing_on = [lib.key_of(r) for r in good if lib.key_of(r) not in on]
    if missing_on:
        problems.append(f'{len(missing_on)} keys without an E-3 row')
    mism = dict(stage1_atoms=0, round1_sha=0, n_cand2=0, atoms_ongrid=0)
    inv = dict(monotone=0, recheck=0, evals=0, bounds=0, window=0, gamma_zero=0, gamma_diag_only=0, gamma_diag_sum_v=0)
    jitter = nonconv = 0
    for r in good:
        e = on.get(lib.key_of(r))
        if e is not None:
            mism['stage1_atoms'] += r['stage1']['atoms'] != e['stage1_atoms']
            mism['round1_sha'] += r['round1']['decoded_sha256'] != e['round1_sha']
            mism['n_cand2'] += r['n_candidates_stage2'] != e['n_cand2']
            mism['atoms_ongrid'] += sum(r['variants'][o]['atoms_ongrid'] != e['variants'][ONGRID[o]]['atoms'] for o in OFF if o in r['variants'])
        if 'gamma_diag_rel_err' in r and r['gamma_diag_rel_err'] >= 1e-10:
            inv['gamma_diag_sum_v'] += 1
        jitter += r['stage1']['jitter_events']
        for o in OFF:
            x = r['variants'].get(o)
            if x is None:
                continue
            f = x['refine']
            inv['monotone'] += not f['monotone']
            inv['recheck'] += not f['value_recheck_equal']
            inv['evals'] += f['max_evals_coord'] > 16
            inv['bounds'] += not f['in_bounds']
            inv['window'] += not f['in_window']
            if o in ('hard-off', 'genie-off'):
                inv['gamma_zero'] += f['gamma_abs_max'] != 0.0
            else:
                inv['gamma_diag_sum_v'] += not (f['gamma_diag_rel_err'] is not None and f['gamma_diag_rel_err'] < 1e-10)
            if o == 'diag-off':
                inv['gamma_diag_only'] += f['gamma_offdiag_abs_max'] != 0.0
            jitter += x['sbl']['jitter_events']
            nonconv += not x['sbl']['converged']
    if any(mism.values()):
        problems.append(f'on-grid stage differs from E-3 rows: {mism}')
    if any(inv.values()):
        problems.append(f'refinement / gamma invariants violated: {inv}')
    if manifest_bad:
        problems.append(f'E-3b row md5 manifest mismatch: {manifest_bad[:3]}')
    if e3_manifest_bad:
        problems.append(f'E-3 row md5 manifest mismatch: {e3_manifest_bad[:3]}')
    return dict(n_rows=len(rows), n_keys=len(expected), n_error_rows=len(errors), e3_pairing_missing=len(missing_on), ongrid_mismatches=mism, invariant_violations=inv,
                cholesky_jitter_events=int(jitter), non_converged_sbl_stage2=int(nonconv), problems=problems, ok=not problems)


# ----------------------------------------------------------------------------- readings
def census(good, on):
    out = dict(off={}, on={})
    genie_off = np.array([r['variants']['genie-off']['n_pair'] for r in good], float)
    genie_on = np.array([on[lib.key_of(r)]['variants']['L-genie']['n_pair'] for r in good], float)
    for o in OFF:
        npair = np.array([r['variants'][o]['n_pair'] for r in good], float)
        dnu = [p['dnu'] for r in good for p in r['variants'][o]['pairs']]
        hist = [0] * len(DNU_BINS)
        for d in dnu:
            for i, (lo, hi) in enumerate(DNU_BINS):
                if lo <= d < hi:
                    hist[i] += 1
                    break
        out['off'][o] = dict(units=len(good), frac_units_with_pair=float(np.mean(npair > 0)), mean_n_pair=float(npair.mean()), excess_vs_genie=float(npair.mean() - genie_off.mean()),
                             pairs=len(dnu), hist_dnu=dict(zip(DNU_NAMES, hist)), frac_pairs_dnu_lt_0p1=(sum(1 for d in dnu if d < .1) / len(dnu) if dnu else None),
                             frac_pairs_coincident_lt_1e6=(sum(1 for d in dnu if d < 1e-6) / len(dnu) if dnu else None),
                             median_dnu=float(np.median(dnu)) if dnu else None, mean_n_atoms=float(np.mean([r['variants'][o]['n_atoms'] for r in good])))
    for v in ON:
        npair = np.array([on[lib.key_of(r)]['variants'][v]['n_pair'] for r in good], float)
        out['on'][v] = dict(mean_n_pair=float(npair.mean()), excess_vs_genie=float(npair.mean() - genie_on.mean()))
    return out


def refinement_stats(good):
    out = {}
    for o in OFF:
        f = [r['variants'][o]['refine'] for r in good]
        coords = sum(x['n_coord'] for x in f)
        per_pass = [sum(x['accepted_by_pass'][p] for x in f) for p in range(len(f[0]['accepted_by_pass']))]
        atoms = sum(r['variants'][o]['n_atoms'] for r in good)
        rel = [(x['value_before'] - x['value_after']) / x['value_before'] for x in f if x['value_before'] > 0]
        out[o] = dict(coordinates=int(coords), accepted=int(sum(x['n_accept'] for x in f)), acceptance_rate=sum(x['n_accept'] for x in f) / coords,
                      acceptance_by_pass=[p / (coords / len(per_pass)) for p in per_pass], mean_evals_per_coordinate=sum(x['evals'] for x in f) / coords,
                      max_evals_any_coordinate=max(x['max_evals_coord'] for x in f), atoms_moved_share=sum(x['n_moved'] for x in f) / atoms,
                      mean_abs_shift=float(np.mean([x['shift_abs_mean'] for x in f])), max_abs_shift=float(max(x['shift_abs_max'] for x in f)),
                      mean_relative_value_decrease=float(np.mean(rel)) if rel else None, cond_Q_median=float(np.median([x['cond_Q'] for x in f])),
                      cond_Q_max=float(max(x['cond_Q'] for x in f)))
    return out


def tables(good, on):
    out = dict(per_cell={}, crossings={})
    for sc, rho in CELLS:
        sub = [r for r in good if r['scenario'] == sc]
        if not sub:
            continue
        snrs = sorted({r['snr_centi_db'] for r in sub})
        cell = {}
        for s in snrs:
            ss = [r for r in sub if r['snr_centi_db'] == s]
            cell[str(s)] = dict(n=len(ss),
                                fer_on={v: float(np.mean([on[lib.key_of(r)]['variants'][v]['fer'] for r in ss])) for v in ON},
                                fer_off={v: float(np.mean([r['variants'][v]['fer'] for r in ss])) for v in OFF},
                                nmse_db_on={v: float(10 * np.log10(np.median([on[lib.key_of(r)]['variants'][v]['nmse'] for r in ss]))) for v in ON},
                                nmse_db_off={v: float(10 * np.log10(np.median([r['variants'][v]['nmse'] for r in ss]))) for v in OFF})
        out['per_cell'][f'{sc}_{rho}'] = cell
        xs = [s / 100 for s in snrs]
        n_pt = [cell[str(s)]['n'] for s in snrs]
        out['crossings'][f'{sc}_{rho}'] = {**{v: base.crossing(xs, [cell[str(s)]['fer_on'][v] for s in snrs], n_pt) for v in ON},
                                           **{v: base.crossing(xs, [cell[str(s)]['fer_off'][v] for s in snrs], n_pt) for v in OFF}}
    return out


def cost_table(good):
    keys = ('stage1_screen', 'stage1_sbl', 'round1_detect', 'round1_decode', 'stage2_screen', 'total')
    out = dict(keys=len(good), per_key={k: float(np.mean([r['seconds'][k] for r in good])) for k in keys},
               gen_seconds_per_key=float(np.mean([r.get('gen_seconds', 0.) for r in good])), variants={})
    for o in OFF:
        out['variants'][o] = {k: float(np.mean([r['variants'][o]['seconds'][k] for r in good])) for k in ('columns', 'sbl', 'refine', 'detect', 'decode', 'total')}
    out['total_core_hours'] = float(sum(r['seconds']['total'] + r.get('gen_seconds', 0.) for r in good) / 3600)
    return out


# ----------------------------------------------------------------------------- analysis
def analyse(rows, on, gates=None, n_boot=N_BOOT, seed=SEED, expected=None, manifest_bad=None, e3_manifest_bad=None):
    expected = set(lib.main_keys()) if expected is None else expected
    gate_ok = None if gates is None else bool(gates.get('all_pass'))
    integ = integrity(rows, on, expected, manifest_bad, e3_manifest_bad)
    good = sorted((r for r in rows if 'variants' in r and set(r['variants']) == set(OFF) and lib.key_of(r) in on), key=lib.key_of)
    res = dict(integrity=integ, gates_all_pass=gate_ok, interpretable=bool(integ['ok'] and gate_ok is not False), n_units=len(good))
    if not good:
        return res
    vals = {f'on_{v}': np.array([on[lib.key_of(r)]['variants'][v]['fer'] for r in good], float) for v in ON}
    vals.update({f'off_{o}': np.array([r['variants'][o]['fer'] for r in good], float) for o in OFF})
    ids = [f"{r['scenario']}|{r['frame']}" for r in good]
    q = quantities(vals, ids, n_boot, seed)
    label = verdict(q['A_off'], q['Delta'])
    mc_off = base.mcnemar(vals['off_diag-off'] == 0, vals['off_cov-off'] == 0)       # H1: diag-off succeeds more often than cov-off
    mc_off_rev = base.mcnemar(vals['off_cov-off'] == 0, vals['off_diag-off'] == 0)
    mc_on = base.mcnemar(vals['on_L-diag'] == 0, vals['on_L-cov'] == 0)
    res.update(quantities=q, verdict=label, reading=READING[label], final_verdict=label if res['interpretable'] else 'NOT_INTERPRETABLE (integrity/gates)',
               mcnemar=dict(diag_off_better_than_cov_off=mc_off, cov_off_better_than_diag_off=mc_off_rev, diag_on_better_than_cov_on=mc_on),
               census=census(good, on), refinement=refinement_stats(good), note_ci0=NOTE_CI0, cost=cost_table(good),
               nmse_db_median=dict(on={v: float(10 * np.log10(np.median([on[lib.key_of(r)]['variants'][v]['nmse'] for r in good]))) for v in ON},
                                   off={o: float(10 * np.log10(np.median([r['variants'][o]['nmse'] for r in good]))) for o in OFF}),
               stage1_nmse_db_median=float(10 * np.log10(np.median([r['stage1']['nmse'] for r in good]))), **tables(good, on))
    return res


def _f(x, spec='+.4f'):
    return 'n/a' if x is None else format(x, spec)


def render_md(res):
    L = ['# E-3b aggregate', '', f"interpretable: {res['interpretable']}; gates_all_pass: {res['gates_all_pass']}; units: {res['n_units']}", '',
         f"integrity: {json.dumps(res['integrity'], default=str)}", '']
    if 'quantities' not in res:
        return '\n'.join(L) + '\n'
    q = res['quantities']
    L += [f"## Verdict: **{res['final_verdict']}**", '', res['reading'], '',
          f"A_on = FER(L-cov) - FER(L-diag); A_off = FER(cov-off) - FER(diag-off); Delta = A_on - A_off  (paired cluster bootstrap, {q['n_boot']} resamples, seed {q['seed']}, "
          f"{q['n_clusters']} clusters, percentile 95% CI); {NOTE_CI0}", '', '| quantity | point | 95% CI | contains 0 |', '|---|---|---|---|']
    for k in ('A_on', 'A_off', 'Delta'):
        x = q[k]
        L.append(f"| {k} | {x['point']:+.5f} | [{x['ci_lo']:+.5f}, {x['ci_hi']:+.5f}] | {x['contains_0']}" + (f" ({NOTE_CI0})" if x['contains_0'] else '') + ' |')
    L += ['', '## FER (unconditional)', '', '| variant | on-grid (E-3) | 95% CI | off-grid (E-3b) | 95% CI | off - on | 95% CI |', '|---|---|---|---|---|---|---|']
    for o in OFF:
        a, b, d = q['fer_on'][ONGRID[o]], q['fer_off'][o], q['off_minus_on'][o]
        L.append(f"| {o} / {ONGRID[o]} | {a['point']:.5f} | [{a['ci_lo']:.5f}, {a['ci_hi']:.5f}] | {b['point']:.5f} | [{b['ci_lo']:.5f}, {b['ci_hi']:.5f}] | "
                 f"{d['point']:+.5f} | [{d['ci_lo']:+.5f}, {d['ci_hi']:+.5f}] |")
    L += ['', '## Exact one-sided McNemar (log10 p)', '', '| test | b | c | log10 p |', '|---|---|---|---|']
    for k, x in res['mcnemar'].items():
        L.append(f"| {k} | {x['b']} | {x['c']} | {x['log10_p']:.1f} |")
    L += ['', '## Same-delay census (n_pair is unchanged by the refinement: delays are fixed)', '',
          '| variant | units with pair | mean n_pair | excess vs genie | pairs | |dnu| hist ' + '/'.join(DNU_NAMES) + ' | share |dnu|<.1 | share <1e-6 | median |dnu| |', '|---|---|---|---|---|---|---|---|---|']
    for o, x in res['census']['off'].items():
        L.append(f"| {o} | {x['frac_units_with_pair']:.4f} | {x['mean_n_pair']:.4f} | {x['excess_vs_genie']:+.4f} | {x['pairs']} | "
                 + '/'.join(str(x['hist_dnu'][b]) for b in DNU_NAMES) + f" | {_f(x['frac_pairs_dnu_lt_0p1'], '.4f')} | {_f(x['frac_pairs_coincident_lt_1e6'], '.4f')} | {_f(x['median_dnu'], '.3f')} |")
    L += ['', 'on-grid (E-3 rows): ' + '; '.join(f"{v} n_pair {x['mean_n_pair']:.4f} (excess {x['excess_vs_genie']:+.4f})" for v, x in res['census']['on'].items()), '',
          '## Refinement', '', '| variant | coordinates | accepted | acceptance | by pass | evals/coord | atoms moved | mean abs shift | max abs shift | rel. value decrease | cond(Q) median / max |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for o, x in res['refinement'].items():
        L.append(f"| {o} | {x['coordinates']} | {x['accepted']} | {x['acceptance_rate']:.4f} | " + '/'.join(f'{p:.3f}' for p in x['acceptance_by_pass'])
                 + f" | {x['mean_evals_per_coordinate']:.2f} | {x['atoms_moved_share']:.4f} | {x['mean_abs_shift']:.4f} | {x['max_abs_shift']:.4f} | "
                 + f"{_f(x['mean_relative_value_decrease'], '.5f')} | {x['cond_Q_median']:.3g} / {x['cond_Q_max']:.3g} |")
    n = res['nmse_db_median']
    L += ['', f"NMSE (dB, median): stage 1 {res['stage1_nmse_db_median']:.2f}; on-grid " + '; '.join(f'{v} {x:.2f}' for v, x in n['on'].items())
          + '; off-grid ' + '; '.join(f'{v} {x:.2f}' for v, x in n['off'].items()), '', f"## FER crossing of {base.CROSS_LEVEL:g} (dB, per cell)", '',
          '| cell | ' + ' | '.join(ON + OFF) + ' |', '|---|' + '---|' * 8]
    for cname, x in res['crossings'].items():
        L.append(f'| {cname} | ' + ' | '.join('never' if x[v] is None else (x[v] if isinstance(x[v], str) else f'{x[v]:.2f}') for v in ON + OFF) + ' |')
    L += ['', '## Per cell and SNR: FER on-grid / off-grid (order hard, diag, cov, genie)', '']
    for cname, cell in res['per_cell'].items():
        L += [f'### {cname}', '', '| snr (centi-dB) | n | FER on-grid | FER off-grid |', '|---|---|---|---|']
        for s, x in cell.items():
            L.append(f"| {s} | {x['n']} | " + ' / '.join(f"{x['fer_on'][v]:.4f}" for v in ON) + ' | ' + ' / '.join(f"{x['fer_off'][v]:.4f}" for v in OFF) + ' |')
        L.append('')
    L += ['## Cost (mean seconds per key)', '', json.dumps(res['cost'], indent=1)]
    return '\n'.join(L) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', type=Path, required=True, help='E-3b main rows directory (rows_shard*.jsonl[.gz], REMOTE_ROWS_MD5.txt)')
    p.add_argument('--e3-rows', type=Path, default=lib.E3_ROWS)
    p.add_argument('--gates', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--boot', type=int, default=N_BOOT)
    a = p.parse_args()
    rows = base.load_rows(a.rows)
    own_bad = lib.verify_manifest(a.rows)[1] if (a.rows / 'REMOTE_ROWS_MD5.txt').exists() else None
    try:
        on, info = lib.load_e3_rows(a.e3_rows, lib.main_keys(), verify=True)
        e3_bad = info['mismatches']
    except RuntimeError as error:
        on, e3_bad = {}, [str(error)]
    res = analyse(rows, on, json.loads(a.gates.read_text()) if a.gates else None, a.boot, manifest_bad=own_bad, e3_manifest_bad=e3_bad)
    res['provenance'] = dict(e3_rows_dir=str(a.e3_rows), e3_rows_manifest_md5=lib.md5_file(a.e3_rows / 'REMOTE_ROWS_MD5.txt'), e3_manifest_files=info['files'] if on else None,
                             gates_md5=lib.md5_file(a.gates) if a.gates else None, e3b_rows_dir=str(a.rows), n_pairing_rows=len(on),
                             fingerprints=sorted({json.dumps(r.get('_config', {}).get('own_md5'), sort_keys=True) for r in rows if '_config' in r}))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'e3b_summary.json').write_text(json.dumps(res, indent=1, default=str) + '\n')
    (a.out / 'e3b_summary.md').write_text(render_md(res))
    print(render_md(res))


if __name__ == '__main__':
    main()
