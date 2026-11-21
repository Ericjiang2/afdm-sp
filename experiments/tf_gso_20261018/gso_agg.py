#!/usr/bin/env python
"""GSO aggregation: strict complete-set reader, frozen verdict rule, report items.  numpy + stdlib only (no receiver imports).

Statistics (frozen in design.md): paired cluster bootstrap, cluster = RNG frame (entropy/domain/frame; all scenarios and SNRs of one frame form ONE cluster,
100 clusters of 12 rows), 20000 multinomial resamples, seed 20261018, percentile 95% CI.  All arms and all contrasts are resampled with the same draws.
Contrasts are bootstrapped as per-row paired differences (integers for FER), so a CI endpoint that is zero in exact arithmetic is exactly 0.0 and the strict
inequalities of the rule cannot be flipped by float cancellation.

Verdict (design.md "冻结判据"), with d1 = FER(C-ls0) - FER(C-sbl) and d2 = FER(C-ls0) - FER(D-sbl):
  BIAS-SUPPORTED      CI_hi(d1) < 0  and  CI_hi(d2) <= .01
  VARIANCE-SUPPORTED  CI_lo(d1) > 0
  MIXED               otherwise.
Any integrity failure makes the run not interpretable: no FER, no contrast and no verdict is produced.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from math import comb, log10
from pathlib import Path
import re
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gso_lib as lib  # noqa: E402

ARMS = ('D-sbl', 'C-sbl', 'C-ls0', 'D-ls0', 'Z-sbl', 'Z-ls0')
BASELINE_ARMS = ('D-sbl', 'C-sbl')
N_BOOT = 20000
SEED = 20261018
DELTA = .01                                             # non-inferiority margin of the BIAS-SUPPORTED rule
LS0_TOL = 1e-10                                         # the gate G2 tolerance (LS0 vs independent numpy solve, relative)
EPS = 2.220446049250313e-16
LS0_COND_SLACK = 64.0                                   # main-run integrity bound: max(LS0_TOL, 64 eps cond(Q)); a wrong solve is orders of magnitude above it
PRIMARY = (('C-ls0', 'C-sbl'), ('C-ls0', 'D-sbl'))     # d1, d2 of the verdict
REPORT = (('D-ls0', 'D-sbl'), ('Z-sbl', 'D-sbl'), ('Z-ls0', 'Z-sbl'))
CONTEXT = (('C-sbl', 'D-sbl'),)                         # the E-3 reversal itself (not a criterion)
CONTRASTS = PRIMARY + REPORT + CONTEXT


class NotInterpretable(RuntimeError):
    pass


def fail(message):
    raise NotInterpretable(message)


# ----------------------------------------------------------------------------- statistics
def mcnemar_log10p(k, n):
    """log10 of the exact one-sided tail P(Bin(n, 1/2) >= k) (n discordant pairs); n = 0 -> 0."""
    if n == 0:
        return 0.0
    return min(0.0, log10(sum(comb(n, i) for i in range(k, n + 1))) - n * log10(2))


def mcnemar(fail_left, fail_right):
    """Exact one-sided McNemar on frame-failure indicators: b = left fails only, c = right fails only.  ``left_better`` tests H1: left fails less often (tail of
    c), ``right_better`` the opposite.  Rows are treated as independent pairs (clustering ignored) -- a report item, not part of the frozen criterion."""
    x, y = np.asarray(fail_left, bool), np.asarray(fail_right, bool)
    b, c = int(np.sum(x & ~y)), int(np.sum(~x & y))
    n = b + c
    return dict(left_only_fail=b, right_only_fail=c, discordant=n, log10_p_left_better=mcnemar_log10p(c, n), log10_p_right_better=mcnemar_log10p(b, n))


def verdict(d1, d2):
    """The frozen rule.  d1 / d2 are CI dicts with ci_lo / ci_hi (d1 = C-ls0 - C-sbl, d2 = C-ls0 - D-sbl, FER differences).  Strict inequalities exactly as
    frozen: ci_hi(d1) < 0, ci_hi(d2) <= .01, ci_lo(d1) > 0."""
    if d1['ci_hi'] < 0 and d2['ci_hi'] <= DELTA:
        return 'BIAS-SUPPORTED'
    if d1['ci_lo'] > 0:
        return 'VARIANCE-SUPPORTED'
    return 'MIXED'


# ----------------------------------------------------------------------------- strict reader
def config_path_of(rows_path):
    return rows_path.parent / (rows_path.name.split('.jsonl')[0].replace('rows_', 'config_') + '.json')


def ls0_bound(q_cond):
    """Rounding differences between a Cholesky and an LU solve scale with cond(Q); the main-run reader tolerates max(1e-10, 64 eps cond(Q))."""
    return max(LS0_TOL, LS0_COND_SLACK * EPS * float(q_cond))


def check_arm(a, x, key):
    if x['fer'] not in (0, 1) or not isinstance(x['info_errors'], int) or x['info_errors'] < 0 or x['fer'] != int(x['info_errors'] > 0):
        fail(f'invalid FER/info_errors {key} {a}')
    if not isinstance(x['nmse'], (int, float)) or not np.isfinite(x['nmse']) or x['nmse'] < 0:
        fail(f'invalid NMSE {key} {a}')
    if not (isinstance(x['decoded_sha256'], str) and len(x['decoded_sha256']) == 64):
        fail(f'invalid decoded sha {key} {a}')
    if x['n_atoms'] < 1 or x['n_atoms'] != len(x['atoms']) or x['n_pair'] != len(x['pairs']):
        fail(f'invalid atom/pair census {key} {a}')
    s = x['sbl']
    if s['cap_hit'] != (not s['converged']) or s['iterations'] > s['max_iter'] or (s['converged'] is False and s['iterations'] != s['max_iter']):
        fail(f'inconsistent SBL iteration-cap record {key} {a}')
    if x['gamma_var'] != a.split('-')[0] or x['gain'] != a.split('-')[1]:
        fail(f'arm label mismatch {key} {a}')
    if a.endswith('ls0'):
        c = x.get('ls0_check')
        if c is None or not np.isfinite(c['rel_err_numpy']) or not np.isfinite(c['q_cond']) or c['rel_err_numpy'] > ls0_bound(c['q_cond']):
            fail(f'LS0 solution not equal to the independent numpy solve (<= max({LS0_TOL}, {LS0_COND_SLACK:g} eps cond Q)) {key} {a}')
    elif 'ls0_check' in x:
        fail(f'unexpected ls0_check on {key} {a}')


def read_rows(directory, expected_keys, smoke=False):
    """(rows ordered by key, sources identity dict).  Fail closed (NotInterpretable) on: missing/foreign/duplicate keys, failed rows, smoke/main mixing, missing
    arms, invalid per-arm records, a failed E-3 replay, a different support in a -sbl/-ls0 pair, mixed source snapshots or inconsistent exogenous hashes."""
    directory = Path(directory)
    want = set(expected_keys)
    rows, sources = {}, None
    paths = sorted(directory.glob('rows_shard*.jsonl*'))
    if not paths:
        fail('no row files')
    for path in paths:
        op = gzip.open if path.suffix == '.gz' else open
        cfg = config_path_of(path)
        if not cfg.exists():
            fail(f'missing config for {path.name}')
        envelope = json.loads(cfg.read_text())
        if not isinstance(envelope.get('_argv'), list) or not envelope['_argv']:
            fail('missing full argv')
        config = envelope['_config']
        if sources is None:
            sources = config['sources_sha256']
        if config['sources_sha256'] != sources:
            fail('mixed source snapshots')
        if bool(config.get('smoke', False)) != smoke or tuple(config['arms']) != ARMS:
            fail('config smoke flag / arm list mismatch')
        if not smoke and (config['e3_manifest'] is None or config['e3_manifest']['mismatches'] or not config['e3_manifest']['files']):
            fail('E-3 rows manifest not verified')
        sha = hashlib.sha256(cfg.read_bytes()).hexdigest()
        declared = {tuple(k) for k in config['keys']}
        observed = set()
        with op(path, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                key = lib.key_of(r)
                if r.get('status') != 'ok':
                    fail(f'failed row {key}')
                if key in rows or key not in want or key not in declared:
                    fail(f'duplicate/unexpected key {key}')
                if r.get('config_sha256') != sha:
                    fail(f'config identity mismatch {key}')
                if bool(r.get('smoke', False)) != smoke or r.get('zero_v'):
                    fail('smoke / zero-v evidence mixed with main evidence')
                if tuple(sorted(r['variants'])) != tuple(sorted(ARMS)):
                    fail(f'incomplete arms {key}')
                if not smoke and not r['baseline_check']['all']:
                    fail(f'E-3 replay failed {key}')
                for a in ARMS:
                    check_arm(a, r['variants'][a], key)
                for kind in ('D', 'C', 'Z'):
                    sup = [[(p[0], p[1]) for p in r['variants'][f'{kind}-{g}']['atoms']] for g in ('sbl', 'ls0')]
                    if sup[0] != sup[1]:
                        fail(f'{kind}-sbl / {kind}-ls0 support differs {key}')
                observed.add(key)
                rows[key] = r
        if observed != declared:
            fail(f'incomplete shard {path.name}: {len(observed)}/{len(declared)} keys')
    if set(rows) != want:
        fail(f'incomplete key set: {len(rows)}/{len(want)}')
    ordered = [rows[k] for k in sorted(want)]
    shared = {}
    for r in ordered:                                    # exogenous inputs are shared by every row of one RNG frame
        cluster = (r['rng_entropy'], r['rng_domain'], r['frame'])
        fingerprint = tuple(r['pairing'][k] for k in ('noise_sha256', 'physical_gains_sha256', 'coded_sha256', 'info_sha256'))
        if shared.setdefault(cluster, fingerprint) != fingerprint:
            fail(f'exogenous cluster hash mismatch {cluster}')
    return ordered, sources


# ----------------------------------------------------------------------------- summary
def cluster_ids(rows):
    return [f"{r['rng_entropy']}:{r['rng_domain']}:{r['frame']}" for r in rows]


def contrast_name(left, right):
    return f'{left} - {right}'


def summarize(rows, n_boot=N_BOOT, seed=SEED):
    samp = lib.sampling()
    fer = {a: np.array([r['variants'][a]['fer'] for r in rows], float) for a in ARMS}
    nmse = {a: np.array([r['variants'][a]['nmse'] for r in rows], float) for a in ARMS}
    values = {}
    for a in ARMS:
        values['fer/' + a] = fer[a]
        values['nmse/' + a] = nmse[a]
    for left, right in CONTRASTS:
        values[f'fer/{contrast_name(left, right)}'] = fer[left] - fer[right]
        values[f'nmse/{contrast_name(left, right)}'] = nmse[left] - nmse[right]
    draws, n_clusters = samp.bootstrap_means(values, cluster_ids(rows), n_boot=n_boot, seed=seed)
    point = {k: float(np.mean(v)) for k, v in values.items()}

    def stat(name):
        return dict(point=point[name], **samp.interval(draws[name]))
    arms = {}
    for a in ARMS:
        xs = [r['variants'][a] for r in rows]
        pairs = [p for x in xs for p in x['pairs']]
        arms[a] = dict(fer=stat('fer/' + a), n_fail=int(fer[a].sum()), nmse=stat('nmse/' + a),
                       n_atoms_total=sum(x['n_atoms'] for x in xs), n_atoms_mean=float(np.mean([x['n_atoms'] for x in xs])),
                       n_pair_total=len(pairs), n_pair_true_delay=sum(bool(p['true_delay']) for p in pairs), n_pair_false_delay=sum(not p['true_delay'] for p in pairs),
                       keys_with_pair=sum(x['n_pair'] > 0 for x in xs),
                       sbl_cap_hit_keys=sum(bool(x['sbl']['cap_hit']) for x in xs), sbl_iterations_mean=float(np.mean([x['sbl']['iterations'] for x in xs])),
                       sbl_jitter_events=sum(x['sbl']['jitter_events'] for x in xs))
    contrasts = {}
    for left, right in CONTRASTS:
        name = contrast_name(left, right)
        contrasts[name] = dict(fer=stat(f'fer/{name}'), nmse=stat(f'nmse/{name}'), mcnemar=mcnemar(fer[left] > 0, fer[right] > 0),
                               role='primary' if (left, right) in PRIMARY else ('context' if (left, right) in CONTEXT else 'report'))
    d1 = contrasts[contrast_name(*PRIMARY[0])]['fer']
    d2 = contrasts[contrast_name(*PRIMARY[1])]['fer']
    label = verdict(d1, d2)
    cells = {}
    for sc in lib.SCENARIOS:
        for snr in lib.SNRS:
            sel = [i for i, r in enumerate(rows) if r['scenario'] == sc and r['snr_centi_db'] == snr]
            cells[f'{sc}/{snr}'] = dict(n=len(sel), n_fail={a: int(fer[a][sel].sum()) for a in ARMS})
    elapsed = [r['elapsed_seconds'] for r in rows]
    ls0 = [r['variants'][a]['ls0_check'] for r in rows for a in ARMS if a.endswith('ls0')]
    return dict(status='draft', interpretable=True, n_keys=len(rows), n_clusters=int(n_clusters), n_boot=int(n_boot), seed=int(seed),
                cluster='RNG entropy/domain/frame; all scenarios and SNRs of one frame are one cluster', arms=arms, contrasts=contrasts,
                verdict=dict(label=label, d1=dict(name=contrast_name(*PRIMARY[0]), **d1), d2=dict(name=contrast_name(*PRIMARY[1]), **d2), delta=DELTA,
                             rule='BIAS-SUPPORTED: ci_hi(d1) < 0 and ci_hi(d2) <= .01; VARIANCE-SUPPORTED: ci_lo(d1) > 0; else MIXED'),
                cells=cells, cost=dict(core_seconds=float(sum(elapsed)), core_hours=float(sum(elapsed)) / 3600, seconds_per_key_mean=float(np.mean(elapsed)),
                                       seconds_per_key_max=float(max(elapsed))),
                ls0=dict(max_rel_err_numpy=max(c['rel_err_numpy'] for c in ls0), max_q_cond=max(c['q_cond'] for c in ls0), tol=LS0_TOL, n=len(ls0)),
                interpretation='draft: bias (Berkson) vs variance (regularisation) reading of the full-Gamma gain penalty; descriptive intervention outcome, no causal certification')


def analyze(rows_dir, keys=None, gates_path=None, n_boot=N_BOOT, seed=SEED):
    """Never raises on bad evidence: returns dict(interpretable=False, reason=...) with no numbers at all."""
    keys = lib.main_keys() if keys is None else keys
    try:
        rows, sources = read_rows(rows_dir, keys)
        if gates_path is not None:
            gates = json.loads(Path(gates_path).read_text())
            if gates.get('all_pass') is not True:
                fail('gates.json is not all_pass')
            if gates.get('sources_sha256') != sources:
                fail('gates / main source snapshot mismatch')
        if keys == lib.main_keys() and len(set(cluster_ids(rows))) != lib.N_FRAMES:
            fail(f'expected {lib.N_FRAMES} frame clusters, found {len(set(cluster_ids(rows)))}')
        result = summarize(rows, n_boot=n_boot, seed=seed)
        result['sources_sha256'] = sources
        return result
    except NotInterpretable as exc:
        return dict(status='draft', interpretable=False, reason=str(exc), verdict=None)


# ----------------------------------------------------------------------------- reports
def fmt_ci(s, scale=1.0, digits=4):
    return f"{s['point'] * scale:+.{digits}f} [{s['ci_lo'] * scale:+.{digits}f}, {s['ci_hi'] * scale:+.{digits}f}]"


def markdown(res):
    if not res.get('interpretable'):
        return f"# GSO summary\n\nNOT INTERPRETABLE: {res.get('reason')}\n\nNo FER, contrast or verdict is reported.\n"
    v = res['verdict']
    lines = ['# GSO summary (draft)', '', f"keys {res['n_keys']}, clusters (frames) {res['n_clusters']}, bootstrap {res['n_boot']} (seed {res['seed']}), 95% percentile CI.", '',
             f"## Verdict: {v['label']}", '', f"- d1 = {v['d1']['name']}: {fmt_ci(v['d1'])}", f"- d2 = {v['d2']['name']}: {fmt_ci(v['d2'])}", f"- rule: {v['rule']}", '',
             '## Arms', '', '| arm | FER [CI] | failures | NMSE mean | atoms | same-delay pairs (true/false delay) | SBL cap-hit keys |', '|---|---|---|---|---|---|---|']
    for a in ARMS:
        x = res['arms'][a]
        lines.append(f"| {a} | {x['fer']['point']:.4f} [{x['fer']['ci_lo']:.4f}, {x['fer']['ci_hi']:.4f}] | {x['n_fail']} | {x['nmse']['point']:.4g} | {x['n_atoms_mean']:.2f} | "
                     f"{x['n_pair_total']} ({x['n_pair_true_delay']}/{x['n_pair_false_delay']}) | {x['sbl_cap_hit_keys']} |")
    lines += ['', '## Contrasts (left - right)', '', '| contrast | role | FER diff [CI] | NMSE diff [CI] | McNemar b/c | log10 p (left better) | log10 p (right better) |', '|---|---|---|---|---|---|---|']
    for name, c in res['contrasts'].items():
        m = c['mcnemar']
        lines.append(f"| {name} | {c['role']} | {fmt_ci(c['fer'])} | {fmt_ci(c['nmse'], digits=5)} | {m['left_only_fail']}/{m['right_only_fail']} | "
                     f"{m['log10_p_left_better']:.2f} | {m['log10_p_right_better']:.2f} |")
    lines += ['', f"cost {res['cost']['core_hours']:.3f} core-h ({res['cost']['seconds_per_key_mean']:.2f} s/key); LS0 vs numpy max rel err {res['ls0']['max_rel_err_numpy']:.2e} (tol {res['ls0']['tol']:.0e}).", '',
              '(McNemar treats rows as independent pairs; the frozen criterion is the cluster bootstrap.)', '']
    return '\n'.join(lines)


def smoke_counts(rows_dir):
    """Counts only (engineering smoke on frames >= 8500): rows, errors, cap hits, atoms, pairs, LS0 error, timing.  No FER / NMSE contrast."""
    rows, errors, sources = [], 0, set()
    for path in sorted(Path(rows_dir).glob('rows_shard*.jsonl*')):
        op = gzip.open if path.suffix == '.gz' else open
        with op(path, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if r.get('status') == 'ok':
                    rows.append(r)
                else:
                    errors += 1
        sources.add(json.dumps(json.loads(config_path_of(path).read_text())['_config']['sources_sha256'], sort_keys=True))
    out = dict(smoke_only=True, rows_ok=len(rows), rows_error=errors, keys=[[r['scenario'], r['snr_centi_db'], r['frame']] for r in rows],
               all_smoke_flagged=all(r.get('smoke') for r in rows), min_frame=min([r['frame'] for r in rows] or [0]), source_snapshots=len(sources), arms={})
    for a in ARMS:
        xs = [r['variants'][a] for r in rows]
        out['arms'][a] = dict(n_atoms_mean=float(np.mean([x['n_atoms'] for x in xs] or [0])), n_pair_total=sum(x['n_pair'] for x in xs),
                              sbl_cap_hit_keys=sum(bool(x['sbl']['cap_hit']) for x in xs), sbl_jitter_events=sum(x['sbl']['jitter_events'] for x in xs),
                              sbl_iterations_mean=float(np.mean([x['sbl']['iterations'] for x in xs] or [0])), n_decoded_clean=sum(x['info_errors'] == 0 for x in xs),
                              gain_seconds_mean=float(np.mean([x['seconds']['gain'] for x in xs] or [0])), sbl_seconds_mean=float(np.mean([x['seconds']['sbl_shared'] for x in xs] or [0])))
    ls0 = [r['variants'][a]['ls0_check'] for r in rows for a in ARMS if a.endswith('ls0')]
    out['ls0_max_rel_err_numpy'] = max([c['rel_err_numpy'] for c in ls0] or [0.0])
    out['seconds_per_key'] = [r['elapsed_seconds'] for r in rows]
    out['shared_stage_seconds_mean'] = {k: float(np.mean([r['seconds'][k] for r in rows] or [0])) for k in ('stage1_screen', 'stage1_sbl', 'round1_detect', 'round1_decode', 'stage2_screen')}
    out['n_candidates_stage2_mean'] = float(np.mean([r['n_candidates_stage2'] for r in rows] or [0]))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--gates', type=Path, default=None, help='gates.json (must be all_pass with the same source snapshot as the rows)')
    p.add_argument('--smoke-counts', action='store_true')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.smoke_counts:
        res = smoke_counts(a.rows)
        (a.out / 'smoke_counts.json').write_text(json.dumps(res, indent=1, sort_keys=True, allow_nan=False) + '\n')
        print(json.dumps({k: res[k] for k in ('rows_ok', 'rows_error')}))
        return 0
    target = a.out / 'gso_summary.json'
    if target.exists():
        raise FileExistsError(target)
    res = analyze(a.rows, gates_path=a.gates)
    target.write_text(json.dumps(res, indent=1, sort_keys=True, allow_nan=False) + '\n')
    (a.out / 'gso_summary.md').write_text(markdown(res))
    print(json.dumps(dict(interpretable=res['interpretable'], verdict=(res['verdict'] or {}).get('label') if res['interpretable'] else None, reason=res.get('reason'))))
    return 0 if res['interpretable'] else 2


if __name__ == '__main__':
    sys.exit(main())
