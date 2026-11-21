#!/usr/bin/env python
"""Aggregation of the model-matched Gamma check: the frozen verdict of design.md section 5.  numpy only (statistics primitives from the frozen e1_agg.py).

Unit = key (scenario, rho .3, SNR in {6, 7, 8} dB, frame 4000..4049), 300 keys.  NMSE_dB = 10 log10(channel NMSE) of the output atoms against the true channel.
  D       = NMSE_dB(S-cov) - NMSE_dB(S-diag) on the SYNTHETIC observations, averaged over the R draws per key first (a paired difference in dB)
  CI      cluster bootstrap over clusters (scenario, frame) (SNR merged), 20000 resamples, seed 20261018, percentile 95% CI
  verdict CODE-CONSISTENT  CI_hi(D) <= 0     (with the model correct, the full Gamma is not worse than the scalar: the real-data reversal is not a code defect)
          SUSPECT          CI_lo(D) > .2 dB  (with the model correct, the full Gamma is still worse: Gamma usage / interaction must be investigated)
          INCONCLUSIVE     otherwise
Report-only: D_real (real observation, expected > 0 to reproduce E-3), NMSE of S-hard / S-genie, EIV-bound monotonicity violations, same-delay census,
reproduction of the E-3 rows (bit-identical atoms) for the real-observation runs.
Usage: python mm_agg.py --rows out/main --gates out/gate/gates.json [--e3-rows <E-3 out/main>] --out out/analysis
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tf_cstate_e1_20261017'))
import e1_agg  # noqa: E402  (frozen E-1 statistics primitives: bootstrap_rates, ci)

VARIANTS = ('S-diag', 'S-cov', 'S-hard', 'S-genie')
CORE_VARIANTS = ('S-diag', 'S-cov')
REAL_VARIANTS = ('S-diag', 'S-cov')
SCENARIOS = ('U', 'G')
RHO_PM = 300
SNRS = (600, 700, 800)
FRAMES = (4000, 4050)
SEED, N_BOOT = 20261018, 20000
SUSPECT_DB = .2
REPS = 3
NOTE_CI0 = 'CI contains 0: not significant != equivalent'
COST_CAP_CORE_HOURS = 3.0


def expected_keys():
    return {(sc, RHO_PM, snr, f) for sc in SCENARIOS for snr in SNRS for f in range(*FRAMES)}


def key_of(r):
    return (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])


def db(x):
    return 10.0 * np.log10(np.maximum(np.asarray(x, dtype=float), 1e-30))


# ----------------------------------------------------------------------------- verdict (frozen)
def verdict(ci_lo, ci_hi):
    """Design section 5: CODE-CONSISTENT iff CI_hi <= 0; SUSPECT iff CI_lo > .2 dB (strict); otherwise INCONCLUSIVE."""
    if ci_hi <= 0:
        return 'CODE-CONSISTENT'
    if ci_lo > SUSPECT_DB:
        return 'SUSPECT'
    return 'INCONCLUSIVE'


# ----------------------------------------------------------------------------- loading, integrity
def load_rows(rows_dir):
    rows = []
    for p in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as handle:
            rows += [json.loads(line) for line in handle if line.strip()]
    return rows


def load_e3_rows(rows_dir, wanted):
    """E-3 main rows (dict keyed by (scenario, rho_permille, snr_centi_db, frame)) restricted to ``wanted``."""
    out = {}
    for p in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        op = gzip.open if p.endswith('.gz') else open
        with op(p, 'rt') as handle:
            for line in handle:
                if line.strip():
                    r = json.loads(line)
                    if 'variants' in r and key_of(r) in wanted:
                        out[key_of(r)] = r
    return out


def e3_match(row, e3_row):
    """Bit-for-bit comparison (JSON round trip of float64 is exact) of the shared pipeline and the real-observation S-diag / S-cov with the E-3 row of the same key."""
    res = dict(stage1_atoms=row['stage1']['atoms'] == e3_row['stage1']['atoms'], round1_sha=row['round1']['decoded_sha256'] == e3_row['round1']['decoded_sha256'],
               n_candidates=row['n_candidates_stage2'] == e3_row['n_candidates_stage2'])
    for mine, theirs in (('S-diag', 'L-diag'), ('S-cov', 'L-cov')):
        a, b = row['real'][mine], e3_row['variants'][theirs]
        res[f'{mine}_atoms'] = a['atoms'] == b['atoms']
        res[f'{mine}_nmse'] = a['nmse'] == b['nmse']
        res[f'{mine}_sbl'] = (a['sbl']['iterations'], a['sbl']['beta'], a['sbl']['converged']) == (b['sbl']['iterations'], b['sbl']['beta'], b['sbl']['converged'])
        res[f'{mine}_pairs'] = a['n_pair'] == b['n_pair']
    return res


def integrity(rows, want, reps=REPS, aux_reps=None):
    errors = [r for r in rows if r.get('status') == 'error']
    good = [r for r in rows if 'real' in r]
    got = [key_of(r) for r in rows]
    problems = []
    if len(set(got)) != len(got):
        problems.append('duplicate rows')
    if want is not None and set(got) != want:
        problems.append(f'row/key mismatch: {len(set(got) ^ want)} keys differ')
    if errors:
        problems.append(f'{len(errors)} error rows')
    if any(r.get('smoke') for r in rows):
        problems.append('smoke rows present')
    bad_real = sum(1 for r in good if set(r['real']) != set(REAL_VARIANTS))
    if bad_real:
        problems.append(f'{bad_real} rows without both real variants')
    aux = reps if aux_reps is None else aux_reps
    bad_syn = sum(1 for r in good if len(r['syn']) != reps or [s['rep'] for s in r['syn']] != list(range(reps))
                  or any(set(VARIANTS if s['rep'] < aux else CORE_VARIANTS) - set(s) for s in r['syn']))
    if bad_syn:
        problems.append(f'{bad_syn} rows without all {reps} synthetic draws x variants (S-hard / S-genie on the first {aux})')
    gd = [r['gamma_diag_rel_err'] for r in good if 'gamma_diag_rel_err' in r]
    if gd and max(gd) >= 1e-10:
        problems.append(f'diag(Gamma) != sum(v): worst {max(gd)}')
    jit = sum(v['sbl']['jitter_events'] for r in good for v in list(r['real'].values()) + [s[n] for s in r['syn'] for n in VARIANTS if n in s])
    return dict(n_rows=len(rows), n_keys=None if want is None else len(want), n_error_rows=len(errors), worst_gamma_diag_rel_err=max(gd) if gd else None,
                cholesky_jitter_events=int(jit), problems=problems, ok=not problems)


# ----------------------------------------------------------------------------- statistics
def eiv_table(rows):
    """Monotonicity of the EIV EM lower bound: per world ('real', 'syn') and variant."""
    out = {}
    for world in ('real', 'syn'):
        names = REAL_VARIANTS if world == 'real' else VARIANTS
        for v in names:
            runs = [r['real'][v]['eiv'] for r in rows] if world == 'real' else [s[v]['eiv'] for r in rows for s in r['syn'] if v in s]
            out[f'{world}:{v}'] = dict(runs=len(runs), runs_with_violation=int(sum(e['n_viol'] > 0 for e in runs)), violating_transitions=int(sum(e['n_viol'] for e in runs)),
                                       worst_rel_drop=float(max([e['max_rel_drop'] for e in runs] or [0.])), prune_events=int(sum(e['n_prune_events'] for e in runs)),
                                       mean_points=float(np.mean([e['n_points'] for e in runs] or [0.])))
    return out


def per_key_values(rows):
    """Per-key arrays (rows sorted by key): rep-averaged synthetic NMSE_dB and n_pair per variant, real NMSE_dB / n_pair."""
    rows = sorted(rows, key=key_of)
    syn_db = {v: np.array([np.mean([db(s[v]['nmse']) for s in r['syn'] if v in s]) for r in rows]) for v in VARIANTS}
    syn_pair = {v: np.array([np.mean([s[v]['n_pair'] for s in r['syn'] if v in s]) for r in rows]) for v in VARIANTS}
    real_db = {v: np.array([float(db(r['real'][v]['nmse'])) for r in rows]) for v in REAL_VARIANTS}
    real_pair = {v: np.array([r['real'][v]['n_pair'] for r in rows], float) for v in REAL_VARIANTS}
    return rows, syn_db, syn_pair, real_db, real_pair


def quantities(rows, n_boot=N_BOOT, seed=SEED):
    rows, syn_db, syn_pair, real_db, real_pair = per_key_values(rows)
    vals = {'D': syn_db['S-cov'] - syn_db['S-diag'], 'D_real': real_db['S-cov'] - real_db['S-diag']}
    for v in VARIANTS:
        vals[f'syn_db_{v}'] = syn_db[v]
        vals[f'syn_pair_{v}'] = syn_pair[v]
    for v in ('S-hard', 'S-genie'):
        vals[f'D_vs_diag_{v}'] = syn_db[v] - syn_db['S-diag']
    for v in ('S-diag', 'S-cov', 'S-hard'):
        vals[f'E_syn_{v}'] = syn_pair[v] - syn_pair['S-genie']
    for v in REAL_VARIANTS:
        vals[f'real_db_{v}'] = real_db[v]
        vals[f'real_pair_{v}'] = real_pair[v]
    ids = [f"{r['scenario']}_{r['frame']}" for r in rows]
    rates, m = e1_agg.bootstrap_rates(vals, ids, n_boot, seed)

    def entry(name):
        lo, hi = e1_agg.ci(rates[name])
        return dict(point=float(np.mean(vals[name])), ci_lo=lo, ci_hi=hi, contains_0=bool(lo <= 0 <= hi))
    q = {k: entry(k) for k in vals}
    q['n_clusters'], q['n_boot'], q['seed'], q['n_keys'] = int(m), int(n_boot), int(seed), len(rows)
    q['frac_keys_D_negative'] = float(np.mean(vals['D'] < 0))
    q['by_cell'] = {f'{sc}_{snr}': dict(n=int(sum(1 for r in rows if r['scenario'] == sc and r['snr_centi_db'] == snr)),
                                        D_point=float(np.mean([vals['D'][i] for i, r in enumerate(rows) if r['scenario'] == sc and r['snr_centi_db'] == snr])),
                                        D_real_point=float(np.mean([vals['D_real'][i] for i, r in enumerate(rows) if r['scenario'] == sc and r['snr_centi_db'] == snr])))
                    for sc in SCENARIOS for snr in SNRS if any(r['scenario'] == sc and r['snr_centi_db'] == snr for r in rows)}
    return q


def census(rows):
    out = {}
    for world in ('real', 'syn'):
        for v in (REAL_VARIANTS if world == 'real' else VARIANTS):
            runs = [r['real'][v] for r in rows] if world == 'real' else [s[v] for r in rows for s in r['syn'] if v in s]
            pairs = [p for x in runs for p in x['pairs']]
            out[f'{world}:{v}'] = dict(runs=len(runs), mean_n_pair=float(np.mean([x['n_pair'] for x in runs])), frac_runs_with_pair=float(np.mean([x['n_pair'] > 0 for x in runs])),
                                       pairs=len(pairs), frac_pairs_on_true_delay=(None if not pairs else float(np.mean([bool(p['true_delay']) for p in pairs]))),
                                       mean_n_atoms=float(np.mean([x['n_atoms'] for x in runs])), median_abs_dnu=(None if not pairs else float(np.median([p['dnu'] for p in pairs]))),
                                       sbl_hit_iteration_cap=float(np.mean([not x['sbl']['converged'] for x in runs])))
    return out


def cost_table(rows):
    keys = ('stage1_screen', 'stage1_sbl', 'round1_detect', 'round1_decode', 'stage2_screen', 'total')
    sbl_s = [v['seconds'] for r in rows for v in r['real'].values()] + [s[n]['seconds'] for r in rows for s in r['syn'] for n in VARIANTS if n in s]
    return dict(keys=len(rows), per_key={k: float(np.mean([r['seconds'][k] for r in rows])) for k in keys}, gen_seconds_per_key=float(np.mean([r.get('gen_seconds', 0.) for r in rows])),
                mean_sbl_seconds=float(np.mean(sbl_s)), sbl_runs_per_key=len(sbl_s) / len(rows),
                total_core_hours=float(sum(r['seconds']['total'] + r.get('gen_seconds', 0.) for r in rows) / 3600), cap_core_hours=COST_CAP_CORE_HOURS)


def reproduction(rows, e3_rows):
    """Real-observation S-diag / S-cov vs the E-3 L-diag / L-cov rows of the same keys: counts of bit-identical results."""
    per = {}
    for r in rows:
        if key_of(r) in e3_rows:
            for name, ok in e3_match(r, e3_rows[key_of(r)]).items():
                per.setdefault(name, []).append(bool(ok))
    return dict(keys_compared=max([len(v) for v in per.values()] or [0]), identical={n: int(sum(v)) for n, v in per.items()})


def analyse(rows, gates, e3_rows=None, n_boot=N_BOOT, want='main', reps=REPS, aux_reps=None):
    want = expected_keys() if want == 'main' else want
    integ = integrity(rows, want, reps, aux_reps)
    gates_ok = bool(gates and gates.get('all_pass'))
    res = dict(integrity=integ, gates_all_pass=gates_ok, interpretable=bool(integ['ok'] and gates_ok), n_units=len(rows))
    good = [r for r in rows if 'real' in r]
    if good:
        res['eiv_monotonicity'] = eiv_table(good)
        res['cost'] = cost_table(good)
    if not res['interpretable']:
        res['final_verdict'] = None
        return res
    q = quantities(rows, n_boot)
    d = q['D']
    res.update(quantities=q, final_verdict=verdict(d['ci_lo'], d['ci_hi']), census=census(rows))
    res['D_real_reproduces_E3_direction'] = bool(q['D_real']['point'] > 0)
    if e3_rows is not None:
        res['reproduction_of_E3_rows'] = reproduction(rows, e3_rows)
    return res


# ----------------------------------------------------------------------------- rendering
def _ci(x, fmt='+.4f'):
    return f"{x['point']:{fmt}} [{x['ci_lo']:{fmt}}, {x['ci_hi']:{fmt}}]" + (f"  ({NOTE_CI0})" if x['contains_0'] else '')


def render_md(res):
    L = ['# Model-matched Gamma check: aggregate', '', f"interpretable: {res['interpretable']}; gates_all_pass: {res['gates_all_pass']}; units: {res['n_units']}", '',
         f"integrity: {json.dumps(res['integrity'], default=str)}", '']
    if res.get('eiv_monotonicity'):
        L += ['## EIV EM lower bound: monotonicity violations (tolerance 1e-9 relative; transitions across atom pruning excluded)', '',
              '| world:variant | runs | runs with violation | violating transitions | worst relative drop | prune events |', '|---|---|---|---|---|---|']
        for k, x in res['eiv_monotonicity'].items():
            L.append(f"| {k} | {x['runs']} | {x['runs_with_violation']} | {x['violating_transitions']} | {x['worst_rel_drop']:.3g} | {x['prune_events']} |")
        L.append('')
    if not res['interpretable']:
        L += ['Aggregate refuses interpretation (integrity or gates).', '', '## Cost', '', json.dumps(res.get('cost'), indent=1)]
        return '\n'.join(L) + '\n'
    q = res['quantities']
    d = q['D']
    L += [f"## Verdict: **{res['final_verdict']}**", '',
          f"D = NMSE_dB(S-cov) - NMSE_dB(S-diag), synthetic, R-averaged per key: {_ci(d)}   (cluster bootstrap over (scenario, frame): {q['n_clusters']} clusters, {q['n_boot']} resamples, seed {q['seed']}; "
          f"CODE-CONSISTENT iff CI_hi <= 0; SUSPECT iff CI_lo > {SUSPECT_DB} dB)", '',
          f"fraction of keys with D < 0: {q['frac_keys_D_negative']:.3f}", '',
          '## Report-only', '', f"D_real = NMSE_dB(S-cov) - NMSE_dB(S-diag), REAL observation: {_ci(q['D_real'])}; reproduces the E-3 direction (point > 0): {res['D_real_reproduces_E3_direction']}", '',
          '| quantity (dB) | mean [95% CI] |', '|---|---|']
    for v in VARIANTS:
        L.append(f"| synthetic NMSE_dB {v} | {_ci(q['syn_db_' + v])} |")
    for v in REAL_VARIANTS:
        L.append(f"| real NMSE_dB {v} | {_ci(q['real_db_' + v])} |")
    for v in ('S-hard', 'S-genie'):
        L.append(f"| synthetic NMSE_dB {v} - S-diag | {_ci(q['D_vs_diag_' + v])} |")
    L += ['', '| cell | keys | D (synthetic) | D_real |', '|---|---|---|---|']
    for k, x in q['by_cell'].items():
        L.append(f"| {k} | {x['n']} | {x['D_point']:+.4f} | {x['D_real_point']:+.4f} |")
    L += ['', '## Same-delay census (output atoms; pair = two atoms with equal delay)', '', '| world:variant | runs | mean n_pair | runs with pair | pairs | pairs on true delay | mean atoms | median |dnu| | SBL at iteration cap |',
          '|---|---|---|---|---|---|---|---|---|']
    for k, x in res['census'].items():
        L.append(f"| {k} | {x['runs']} | {x['mean_n_pair']:.4f} | {x['frac_runs_with_pair']:.4f} | {x['pairs']} | {x['frac_pairs_on_true_delay'] if x['frac_pairs_on_true_delay'] is None else format(x['frac_pairs_on_true_delay'], '.4f')} | "
                 f"{x['mean_n_atoms']:.2f} | {x['median_abs_dnu'] if x['median_abs_dnu'] is None else format(x['median_abs_dnu'], '.3f')} | {x['sbl_hit_iteration_cap']:.3f} |")
    L += ['', 'Phantom excess vs S-genie (synthetic, mean n_pair difference): ' + '; '.join(f"{v} {_ci(q['E_syn_' + v])}" for v in ('S-diag', 'S-cov', 'S-hard')), '']
    if 'reproduction_of_E3_rows' in res:
        L += ['## Real-observation runs vs the E-3 rows of the same keys (bit-identical counts)', '', json.dumps(res['reproduction_of_E3_rows'], indent=1), '']
    L += ['## Cost', '', json.dumps(res['cost'], indent=1)]
    return '\n'.join(L) + '\n'


def smoke_counts(rows):
    """Counts and timing of a few smoke rows (SMOKE ONLY; no differences, no CI, no verdict)."""
    good = [r for r in rows if 'real' in r]
    out = dict(rows=len(rows), error_rows=len(rows) - len(good), keys=sorted(str(key_of(r)) for r in rows))
    if not good:
        return out
    out['seconds_per_key'] = dict(total=float(np.mean([r['seconds']['total'] + r.get('gen_seconds', 0.) for r in good])),
                                  **{k: float(np.mean([r['seconds'][k] for r in good])) for k in ('stage1_screen', 'stage1_sbl', 'round1_detect', 'round1_decode', 'stage2_screen')},
                                  gamma=float(np.mean([r['gamma_seconds'] for r in good])), gen=float(np.mean([r.get('gen_seconds', 0.) for r in good])))
    out['sbl_runs_per_key'] = sum(len([n for n in VARIANTS if n in s]) for s in good[0]['syn']) + len(REAL_VARIANTS)
    out['mean_sbl_seconds'] = cost_table(good)['mean_sbl_seconds']
    out['mean_v'] = float(np.mean([r['mean_v'] for r in good]))
    out['n_candidates_stage2'] = float(np.mean([r['n_candidates_stage2'] for r in good]))
    out['round1_info_errors'] = [r['round1']['info_errors'] for r in good]
    out['x_stats'] = dict(mean_dev_ratio=float(np.mean([s['x_stats']['dev_ratio'] for r in good for s in r['syn']])),
                          mean_frac_differs_from_hard=float(np.mean([s['x_stats']['frac_differs_from_hard'] for r in good for s in r['syn']])))
    out['census'] = {k: dict(mean_n_pair=x['mean_n_pair'], mean_n_atoms=x['mean_n_atoms'], sbl_hit_iteration_cap=x['sbl_hit_iteration_cap']) for k, x in census(good).items()}
    out['nmse_db_median'] = {f'{w}:{v}': float(np.median([float(db(x['nmse'])) for x in ([r['real'][v] for r in good] if w == 'real' else [s[v] for r in good for s in r['syn']])]))
                             for w, names in (('real', REAL_VARIANTS), ('syn', VARIANTS)) for v in names}
    out['eiv_monotonicity'] = eiv_table(good)
    out['cholesky_jitter_events'] = integrity(rows, None)['cholesky_jitter_events']
    out['max_gamma_diag_rel_err'] = float(max(r['gamma_diag_rel_err'] for r in good))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--gates', type=Path)
    p.add_argument('--e3-rows', type=Path, help='E-3 out/main (rows_shard*.jsonl.gz) for the full reproduction count')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--boot', type=int, default=N_BOOT)
    p.add_argument('--reps', type=int, default=REPS)
    p.add_argument('--aux-reps', type=int, default=None, help='S-hard / S-genie were run on the first AUX_REPS draws only (default = reps)')
    p.add_argument('--smoke-counts', action='store_true', help='print counts and timing of smoke rows only (no verdict)')
    a = p.parse_args()
    rows = load_rows(a.rows)
    if a.smoke_counts:
        res = smoke_counts(rows)
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / 'smoke_counts.json').write_text(json.dumps(res, indent=1, default=str) + '\n')
        print(json.dumps(res, indent=1, default=str))
        return
    e3 = load_e3_rows(a.e3_rows, {key_of(r) for r in rows}) if a.e3_rows else None
    res = analyse(rows, json.loads(a.gates.read_text()) if a.gates else None, e3, a.boot, reps=a.reps, aux_reps=a.aux_reps)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'mm_summary.json').write_text(json.dumps(res, indent=1, default=str) + '\n')
    (a.out / 'mm_summary.md').write_text(render_md(res))
    print(render_md(res))


if __name__ == '__main__':
    main()
