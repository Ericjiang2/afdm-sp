#!/usr/bin/env python
"""Split-principle prospective test: aggregation.  Strict complete-set readers, the frozen predictions P1-P4, the ordered verdict, report items.  numpy + stdlib only
(no receiver imports).

Statistics (frozen in design.md): paired cluster bootstrap; cluster = RNG frame (entropy/domain/frame; every scenario, rho and SNR row of both families that shares a
frame is ONE cluster; 200 clusters per family); 20000 multinomial resamples, seed 20261018, percentile 95% CI.  Contrasts are bootstrapped as per-row paired differences
(integers), so a CI endpoint that is zero in exact arithmetic is exactly 0.0 and the strict inequalities cannot be flipped by float cancellation.
  S family (FER over all 2400 keys):       d1 = FER(S-H) - FER(S-C),  d2 = FER(S-H) - FER(S-D).
  K family (rescue rate over triggered units): R(arm) = sum_rows [triggered and 0 information-bit errors] / sum_rows [triggered], a ratio of the SAME resampled totals over
  all 6400 keys (every frame is resampled, including frames with no triggered unit); r3a = R(K-diag-isofix) - R(K-diag-fullfix) (A2 geometry: close same-delay pairs, the
  discriminating test), r3b = R(K-isofix) - R(K-fullfix) (A1 geometry: well separated paths, the principle predicts equivalence), r4 = R(K-prod) - R(K-diag).
  ``ratio_summary`` of the frozen sampling module marks a contrast unevaluable if more than 1% of resamples have a nonpositive denominator (then P3a / P3b / P4 are not
  established and a K-side REFUTED cannot be declared).

Predictions (design.md with pre-freeze amendment A1):
  P1: ci_hi(d1) < 0.   P2: ci_hi(d2) <= .01.   P3a: ci_lo(r3a) > 0.   P3b: -.01 <= ci_lo(r3b) and ci_hi(r3b) <= .01.   P4: ci_lo(r4) > 0.
Verdict, first rule that holds:
  1. REFUTED    ci_lo(d1) > 0   or   ci_hi(r3a) < 0           (a significant reversal of an estimation prediction)
  2. CONFIRMED  P1 and P2 and P3a and P3b and P4
  3. PARTIAL    P1 and P3a, but at least one of P2, P3b, P4 fails
  4. MIXED      anything else
Any integrity failure makes the run not interpretable: no FER, no rescue rate, no contrast and no verdict is produced.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from math import comb, log10
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sp_lib as lib  # noqa: E402

S_ARMS, K_ARMS = lib.S_ARMS, lib.K_ARMS
N_BOOT = 20000
SEED = 20261018
DELTA = .01                                              # non-inferiority margin of P2
NUM_TOL = 1e-10                                          # the gate G2 tolerance (kernel vs independent numpy ridge solve, relative)
EPS = 2.220446049250313e-16
COND_SLACK = 64.0                                        # main-run bound max(NUM_TOL, 64 eps cond(Q)); a wrong solve is orders of magnitude above it
EVAL_LIMIT = .01                                         # unevaluable ratio if > 1% of resamples have a nonpositive denominator
S_PRIMARY = (('S-H', 'S-C'), ('S-H', 'S-D'))             # d1, d2
S_REPORT = (('S-C', 'S-D'),)                             # the E-3 reversal itself (context, not a criterion)
K_PRIMARY = (('K-diag-isofix', 'K-diag-fullfix'), ('K-isofix', 'K-fullfix'), ('K-prod', 'K-diag'))   # r3a, r3b, r4
K_REPORT = (('K-fullfix', 'K-prod'), ('K-isofix', 'K-prod'), ('K-diag-fullfix', 'K-diag'), ('K-diag-isofix', 'K-diag'))
EQUIV = .01                                              # P3b equivalence margin
ARM_FIELDS = {'S-D': ('D', 'sbl'), 'S-C': ('C', 'sbl'), 'S-H': ('C', 'iso')}


class NotInterpretable(RuntimeError):
    pass


def fail(message):
    raise NotInterpretable(message)


def num_bound(q_cond):
    return max(NUM_TOL, COND_SLACK * EPS * float(q_cond))


# ----------------------------------------------------------------------------- statistics
def mcnemar_log10p(k, n):
    """log10 of the exact one-sided tail P(Bin(n, 1/2) >= k) (n discordant pairs); n = 0 -> 0."""
    if n == 0:
        return 0.0
    return min(0.0, log10(sum(comb(n, i) for i in range(k, n + 1))) - n * log10(2))


def mcnemar(bad_left, bad_right):
    """Exact one-sided McNemar on per-row 'bad' indicators (S: frame failure; K: not rescued).  b = left bad only, c = right bad only.  ``left_better`` tests H1: left is
    bad less often (tail of c).  Rows are treated as independent pairs (clustering ignored): a report item, not part of the frozen criterion."""
    x, y = np.asarray(bad_left, bool), np.asarray(bad_right, bool)
    b, c = int(np.sum(x & ~y)), int(np.sum(~x & y))
    n = b + c
    return dict(left_only_bad=b, right_only_bad=c, discordant=n, log10_p_left_better=mcnemar_log10p(c, n), log10_p_right_better=mcnemar_log10p(b, n))


def verdict(d1, d2, r3a, r3b, r4):
    """The frozen ordered rule (design.md with amendment A1).  d1 / d2: dicts with ci_lo / ci_hi (FER differences S-H - S-C, S-H - S-D).  r3a / r3b / r4: ratio dicts with
    ci_lo / ci_hi / evaluable (rescue-rate differences K-diag-isofix - K-diag-fullfix, K-isofix - K-fullfix, K-prod - K-diag).  Strict inequalities exactly as frozen; P3b
    is the closed equivalence interval [-.01, .01].  Returns dict(label, P1, P2, P3a, P3b, P4, refuted_by)."""
    def ev(r):
        return bool(r.get('evaluable', True)) and r['ci_lo'] is not None and r['ci_hi'] is not None
    p = {'P1': bool(d1['ci_hi'] < 0), 'P2': bool(d2['ci_hi'] <= DELTA), 'P3a': bool(ev(r3a) and r3a['ci_lo'] > 0),
         'P3b': bool(ev(r3b) and -EQUIV <= r3b['ci_lo'] and r3b['ci_hi'] <= EQUIV), 'P4': bool(ev(r4) and r4['ci_lo'] > 0)}
    refuted_by = [name for name, hit in (('S: ci_lo(d1) > 0', d1['ci_lo'] > 0), ('K: ci_hi(r3a) < 0', ev(r3a) and r3a['ci_hi'] < 0)) if hit]
    if refuted_by:
        label = 'REFUTED'
    elif all(p.values()):
        label = 'CONFIRMED'
    elif p['P1'] and p['P3a']:
        label = 'PARTIAL'
    else:
        label = 'MIXED'
    return dict(label=label, refuted_by=refuted_by, **p)


# ----------------------------------------------------------------------------- strict readers
def config_path_of(rows_path):
    return rows_path.parent / (rows_path.name.split('.jsonl')[0].replace('rows_', 'config_') + '.json')


def check_common(a, x, key):
    if x['fer'] not in (0, 1) or not isinstance(x['info_errors'], int) or x['info_errors'] < 0 or x['fer'] != int(x['info_errors'] > 0):
        fail(f'invalid FER/info_errors {key} {a}')
    if not (isinstance(x['decoded_sha256'], str) and len(x['decoded_sha256']) == 64):
        fail(f'invalid decoded sha {key} {a}')
    if x['n_pair'] != len(x['pairs']):
        fail(f'invalid atom/pair census {key} {a}')


def check_arm_s(a, x, key):
    check_common(a, x, key)
    if not isinstance(x['nmse'], (int, float)) or not np.isfinite(x['nmse']) or x['nmse'] < 0:
        fail(f'invalid NMSE {key} {a}')
    if x['n_atoms'] < 1 or x['n_atoms'] != len(x['atoms']):
        fail(f'invalid atom/pair census {key} {a}')
    s = x['sbl']
    if s['cap_hit'] != (not s['converged']) or s['iterations'] > s['max_iter'] or (s['converged'] is False and s['iterations'] != s['max_iter']):
        fail(f'inconsistent SBL iteration-cap record {key} {a}')
    if (x['gamma_var'], x['gain']) != ARM_FIELDS[a]:
        fail(f'arm label mismatch {key} {a}')
    if a == 'S-H':
        c = x.get('iso_check')
        if c is None or not np.isfinite(c['rel_err_numpy']) or not np.isfinite(c['q_cond']) or c['rel_err_numpy'] > num_bound(c['q_cond']):
            fail(f'S-H gains not equal to the independent numpy ridge solve (<= max({NUM_TOL}, {COND_SLACK:g} eps cond Q)) {key}')
    elif 'iso_check' in x:
        fail(f'unexpected iso_check on {key} {a}')


def check_arm_k(a, x, key):
    check_common(a, x, key)
    if x.get('status') != 'ok':
        fail(f'arm record not ok {key} {a}')
    if len(x['final_delays']) < 1 or len(x['final_delays']) != len(x['final_dopplers']):
        fail(f'invalid final paths {key} {a}')


def read_common(cfg, family, smoke, sources):
    """Shared per-shard config checks; returns (sources identity, config)."""
    envelope = json.loads(cfg.read_text())
    if not isinstance(envelope.get('_argv'), list) or not envelope['_argv']:
        fail('missing full argv')
    config = envelope['_config']
    if sources is None:
        sources = config['sources_sha256']
    if config['sources_sha256'] != sources:
        fail('mixed source snapshots')
    if bool(config.get('smoke', False)) != smoke or config.get('family') != family or tuple(config['s_arms']) != S_ARMS or tuple(config['k_arms']) != K_ARMS:
        fail('config smoke flag / family / arm list mismatch')
    return sources, config


def read_family(directory, family, expected_keys, smoke=False, sources=None):
    """(rows ordered by key, sources identity).  Fail closed (NotInterpretable) on: missing/foreign/duplicate keys, failed rows, smoke/main mixing, missing or surplus arms,
    invalid per-arm records, a different support in S-H and S-C, K arms with different final paths, an F0 trigger flag that contradicts the F0 syndrome, a fixed-gain
    arm whose gains differ from result.gains / from the independent ridge solve, mixed source snapshots."""
    directory = Path(directory)
    want = set(expected_keys)
    rows = {}
    paths = sorted(directory.glob(f'rows_{family}_shard*.jsonl*'))
    if not paths:
        fail(f'no {family} row files')
    for path in paths:
        op = gzip.open if path.suffix == '.gz' else open
        cfg = config_path_of(path)
        if not cfg.exists():
            fail(f'missing config for {path.name}')
        sources, config = read_common(cfg, family, smoke, sources)
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
                if bool(r.get('smoke', False)) != smoke or r.get('zero_v') or r.get('gate_kind') or r.get('family') != family:
                    fail('smoke / gate / zero-v evidence mixed with main evidence')
                if family == 'S':
                    check_row_s(r, key)
                else:
                    check_row_k(r, key)
                observed.add(key)
                rows[key] = r
        if observed != declared:
            fail(f'incomplete shard {path.name}: {len(observed)}/{len(declared)} keys')
    if set(rows) != want:
        fail(f'incomplete {family} key set: {len(rows)}/{len(want)}')
    return [rows[k] for k in sorted(want)], sources


def check_row_s(r, key):
    if tuple(sorted(r['variants'])) != tuple(sorted(S_ARMS)):
        fail(f'incomplete arms {key}')
    for a in S_ARMS:
        check_arm_s(a, r['variants'][a], key)
    sup = {a: [(p[0], p[1]) for p in r['variants'][a]['atoms']] for a in ('S-C', 'S-H')}
    if sup['S-C'] != sup['S-H']:
        fail(f'S-C / S-H support differs {key}')
    if r['variants']['S-C']['sbl'] != r['variants']['S-H']['sbl']:
        fail(f'S-C / S-H SBL record differs {key}')


def check_row_k(r, key):
    syn = r['f0']['syndrome']
    if not isinstance(syn, int) or syn < 0 or r['triggered'] is not (syn != 0):
        fail(f'trigger flag contradicts the F0 syndrome {key}')
    if not r['triggered']:
        if r['arms']:
            fail(f'untriggered row carries arms {key}')
        return
    if tuple(sorted(r['arms'])) != tuple(sorted(K_ARMS)):
        fail(f'incomplete arms {key}')
    for a in K_ARMS:
        check_arm_k(a, r['arms'][a], key)
    for geo, (name_full, name_iso, _pre) in lib.FIXED_ARMS.items():
        for a in (name_full, name_iso):
            if r['arms'][a]['final_delays'] != r['arms'][geo]['final_delays'] or r['arms'][a]['final_dopplers'] != r['arms'][geo]['final_dopplers']:
                fail(f'{a} paths differ from {geo} {key}')
    ck = r['checks']
    if ck.get('full_equals_result_gains') is not True:
        fail(f'K-fullfix gains differ from result.gains {key}')
    if ck.get('diag_iso_equals_result_gains') is not True:
        fail(f'K-diag-isofix gains differ from A2 result.gains {key}')
    for pre, name in (('', 'K-isofix'), ('diag_', 'K-diag-isofix')):
        e, q = ck[f'{pre}iso_rel_err_numpy'], ck[f'{pre}iso_q_cond']
        if not (np.isfinite(e) and np.isfinite(q)) or e > num_bound(q):
            fail(f'{name} gains not equal to the independent numpy ridge solve {key}')


def cluster_of(r):
    return f"{r['rng_entropy']}:{r['rng_domain']}:{r['frame']}"


def check_exogenous(rows):
    """The exogenous inputs (noise, physical gains, coded bits, info bits) are shared by every row of one RNG frame, across scenario, rho, SNR and family."""
    shared = {}
    for r in rows:
        fingerprint = tuple(r['pairing'][k] for k in ('noise_sha256', 'physical_gains_sha256', 'coded_sha256', 'info_sha256'))
        if shared.setdefault(cluster_of(r), fingerprint) != fingerprint:
            fail(f'exogenous cluster hash mismatch {cluster_of(r)}')
    return shared


# ----------------------------------------------------------------------------- summary
def interval_stat(samp, point, draws, name):
    return dict(point=point[name], **samp.interval(draws[name]))


def contrast_name(left, right):
    return f'{left} - {right}'


def summarize_s(rows, n_boot, seed):
    samp = lib.sampling()
    fer = {a: np.array([r['variants'][a]['fer'] for r in rows], float) for a in S_ARMS}
    nmse = {a: np.array([r['variants'][a]['nmse'] for r in rows], float) for a in S_ARMS}
    cap = {a: np.array([r['variants'][a]['sbl']['cap_hit'] for r in rows], float) for a in S_ARMS}
    values = {}
    for a in S_ARMS:
        values['fer/' + a], values['nmse/' + a], values['cap/' + a] = fer[a], nmse[a], cap[a]
    for left, right in S_PRIMARY + S_REPORT:
        values[f'fer/{contrast_name(left, right)}'] = fer[left] - fer[right]
        values[f'nmse/{contrast_name(left, right)}'] = nmse[left] - nmse[right]
    draws, n_clusters = samp.bootstrap_means(values, [cluster_of(r) for r in rows], n_boot=n_boot, seed=seed)
    point = {k: float(np.mean(v)) for k, v in values.items()}
    arms = {}
    for a in S_ARMS:
        xs = [r['variants'][a] for r in rows]
        pairs = [p for x in xs for p in x['pairs']]
        arms[a] = dict(fer=interval_stat(samp, point, draws, 'fer/' + a), n_fail=int(fer[a].sum()), nmse=interval_stat(samp, point, draws, 'nmse/' + a),
                       n_atoms_mean=float(np.mean([x['n_atoms'] for x in xs])), n_pair_total=len(pairs), n_pair_true_delay=sum(bool(p['true_delay']) for p in pairs),
                       n_pair_false_delay=sum(not p['true_delay'] for p in pairs), keys_with_pair=sum(x['n_pair'] > 0 for x in xs),
                       sbl_cap_hit_keys=int(cap[a].sum()), sbl_cap_hit_fraction=interval_stat(samp, point, draws, 'cap/' + a),
                       sbl_iterations_mean=float(np.mean([x['sbl']['iterations'] for x in xs])), sbl_jitter_events=sum(x['sbl']['jitter_events'] for x in xs))
    contrasts = {}
    for left, right in S_PRIMARY + S_REPORT:
        name = contrast_name(left, right)
        contrasts[name] = dict(fer=interval_stat(samp, point, draws, f'fer/{name}'), nmse=interval_stat(samp, point, draws, f'nmse/{name}'),
                               mcnemar=mcnemar(fer[left] > 0, fer[right] > 0), role='primary' if (left, right) in S_PRIMARY else 'context')
    cells = {}
    for sc in lib.SCENARIOS:
        for snr in lib.S_SNRS:
            sel = [i for i, r in enumerate(rows) if r['scenario'] == sc and r['snr_centi_db'] == snr]
            cells[f'{sc}/{snr}'] = dict(n=len(sel), n_fail={a: int(fer[a][sel].sum()) for a in S_ARMS})
    iso = [r['variants']['S-H']['iso_check'] for r in rows]
    return dict(n_keys=len(rows), n_clusters=int(n_clusters), arms=arms, contrasts=contrasts, cells=cells,
                iso=dict(max_rel_err_numpy=max(c['rel_err_numpy'] for c in iso), max_q_cond=max(c['q_cond'] for c in iso), tol=NUM_TOL,
                         rel_diff_vs_sc_mean=float(np.mean([c['rel_diff_vs_sc'] for c in iso]))),
                cost=cost_of(rows))


def rescued(r, arm):
    return int(r['triggered'] and r['arms'][arm]['info_errors'] == 0)


def summarize_k(rows, n_boot, seed):
    samp = lib.sampling()
    trig = np.array([int(r['triggered']) for r in rows], float)
    resc = {a: np.array([rescued(r, a) for r in rows], float) for a in K_ARMS}
    values = {'trig': trig}
    for a in K_ARMS:
        values['resc/' + a] = resc[a]
    for left, right in K_PRIMARY + K_REPORT:
        values[f'resc/{contrast_name(left, right)}'] = resc[left] - resc[right]
    draws, n_clusters = samp.bootstrap_means(values, [cluster_of(r) for r in rows], n_boot=n_boot, seed=seed)
    point = {k: float(np.mean(v)) for k, v in values.items()}
    den = {'trig': 1}
    n_trig = int(trig.sum())
    arms = {}
    for a in K_ARMS:
        sel = [r for r in rows if r['triggered']]
        xs = [r['arms'][a] for r in sel]
        pairs = [p for x in xs for p in x['pairs']]
        arms[a] = dict(rate=samp.ratio_summary(point, draws, {'resc/' + a: 1}, den, limit=EVAL_LIMIT), n_rescued=int(resc[a].sum()), n_triggered=n_trig,
                       n_pair_total=len(pairs), n_pair_true_delay=sum(bool(p['true_delay']) for p in pairs), n_pair_false_delay=sum(not p['true_delay'] for p in pairs),
                       keys_with_pair=sum(x['n_pair'] > 0 for x in xs))
    contrasts = {}
    for left, right in K_PRIMARY + K_REPORT:
        name = contrast_name(left, right)
        contrasts[name] = dict(rate=samp.ratio_summary(point, draws, {f'resc/{name}': 1}, den, limit=EVAL_LIMIT),
                               mcnemar=mcnemar([r['triggered'] and rescued(r, left) == 0 for r in rows], [r['triggered'] and rescued(r, right) == 0 for r in rows]),
                               role='primary' if (left, right) in K_PRIMARY else 'report')
    cells = {}
    for sc in lib.SCENARIOS:
        for rho in lib.K_RHOS:
            for snr in lib.K_SNRS:
                sel = [r for r in rows if r['scenario'] == sc and r['rho_permille'] == rho and r['snr_centi_db'] == snr]
                cells[f'{sc}/{rho}/{snr}'] = dict(n=len(sel), n_triggered=sum(r['triggered'] for r in sel), n_rescued={a: sum(rescued(r, a) for r in sel) for a in K_ARMS})
    trigd = [r for r in rows if r['triggered']]
    chk = [r['checks'] for r in trigd]
    return dict(n_keys=len(rows), n_clusters=int(n_clusters), n_triggered=n_trig, arms=arms, contrasts=contrasts, cells=cells,
                f0=dict(n_syndrome_nonzero=n_trig, f0_info_error_free_among_triggered=sum(r['f0']['info_errors'] == 0 for r in trigd)),
                checks=dict(max_iso_rel_err_numpy=max([c['iso_rel_err_numpy'] for c in chk] + [c['diag_iso_rel_err_numpy'] for c in chk] or [0.0]),
                            max_iso_q_cond=max([c['iso_q_cond'] for c in chk] + [c['diag_iso_q_cond'] for c in chk] or [0.0]),
                            fullfix_equals_a1_result_gains=sum(c['full_equals_result_gains'] is True for c in chk),
                            diag_isofix_equals_a2_result_gains=sum(c['diag_iso_equals_result_gains'] is True for c in chk), n=len(chk), tol=NUM_TOL,
                            iso_rel_diff_vs_full_mean=float(np.mean([c['iso_rel_diff_vs_full'] for c in chk] or [0.0])),
                            diag_iso_rel_diff_vs_full_mean=float(np.mean([c['diag_iso_rel_diff_vs_full'] for c in chk] or [0.0]))),
                cost=cost_of(rows))


def cost_of(rows):
    elapsed = [r['elapsed_seconds'] for r in rows]
    return dict(core_seconds=float(sum(elapsed)), core_hours=float(sum(elapsed)) / 3600, seconds_per_key_mean=float(np.mean(elapsed)), seconds_per_key_max=float(max(elapsed)))


def analyze(rows_dir, s_keys=None, k_keys=None, gates_path=None, n_boot=N_BOOT, seed=SEED, n_clusters_expected=lib.N_FRAMES):
    """Never raises on bad evidence: returns dict(interpretable=False, reason=...) with no numbers at all."""
    s_keys = lib.s_keys() if s_keys is None else s_keys
    k_keys = lib.k_keys() if k_keys is None else k_keys
    try:
        s_rows, s_sources = read_family(rows_dir, 'S', s_keys)
        k_rows, k_sources = read_family(rows_dir, 'K', k_keys)
        if s_sources != k_sources:
            fail('mixed source snapshots between the S and K families')
        if gates_path is not None:
            gates = json.loads(Path(gates_path).read_text())
            if gates.get('all_pass') is not True:
                fail('gates.json is not all_pass')
            if gates.get('sources_sha256') != s_sources:
                fail('gates / main source snapshot mismatch')
        shared = check_exogenous(s_rows + k_rows)
        if len(shared) != n_clusters_expected or len({cluster_of(r) for r in s_rows}) != n_clusters_expected or len({cluster_of(r) for r in k_rows}) != n_clusters_expected:
            fail(f'expected {n_clusters_expected} frame clusters in both families, found {len(shared)}')
        S = summarize_s(s_rows, n_boot, seed)
        K = summarize_k(k_rows, n_boot, seed)
        d1 = S['contrasts'][contrast_name(*S_PRIMARY[0])]['fer']
        d2 = S['contrasts'][contrast_name(*S_PRIMARY[1])]['fer']
        r3a = K['contrasts'][contrast_name(*K_PRIMARY[0])]['rate']
        r3b = K['contrasts'][contrast_name(*K_PRIMARY[1])]['rate']
        r4 = K['contrasts'][contrast_name(*K_PRIMARY[2])]['rate']
        v = verdict(d1, d2, r3a, r3b, r4)
        total = S['cost']['core_hours'] + K['cost']['core_hours']
        return dict(status='draft', interpretable=True, n_boot=int(n_boot), seed=int(seed), sources_sha256=s_sources, S=S, K=K, total_core_hours=total,
                    cluster='RNG entropy/domain/frame; every scenario, rho and SNR row of one frame is one cluster (200 clusters per family)',
                    verdict=dict(v, d1=dict(name=contrast_name(*S_PRIMARY[0]), **d1), d2=dict(name=contrast_name(*S_PRIMARY[1]), **d2),
                                 r3a=dict(name=contrast_name(*K_PRIMARY[0]), **r3a), r3b=dict(name=contrast_name(*K_PRIMARY[1]), **r3b),
                                 r4=dict(name=contrast_name(*K_PRIMARY[2]), **r4), delta=DELTA, equiv=EQUIV,
                                 rule='P1: ci_hi(d1) < 0; P2: ci_hi(d2) <= .01; P3a: ci_lo(r3a) > 0; P3b: ci(r3b) within [-.01, .01]; P4: ci_lo(r4) > 0; REFUTED: ci_lo(d1) > 0 or '
                                      'ci_hi(r3a) < 0; CONFIRMED: P1, P2, P3a, P3b, P4; PARTIAL: P1 and P3a but not all of P2, P3b, P4; else MIXED'),
                    interpretation='draft: prospective test of the decision/estimation split principle; descriptive intervention outcome, no causal certification')
    except NotInterpretable as exc:
        return dict(status='draft', interpretable=False, reason=str(exc), verdict=None)


# ----------------------------------------------------------------------------- reports
def fmt_ci(s, digits=4):
    return f"{s['point']:+.{digits}f} [{s['ci_lo']:+.{digits}f}, {s['ci_hi']:+.{digits}f}]"


def fmt_rate(s, digits=4):
    if s['ci_lo'] is None:
        return f"{(s['point'] if s['point'] is not None else float('nan')):+.{digits}f} [n/a] (unevaluable)"
    flag = '' if s['evaluable'] else ' (UNEVALUABLE)'
    return f"{s['point']:+.{digits}f} [{s['ci_lo']:+.{digits}f}, {s['ci_hi']:+.{digits}f}]{flag}"


def markdown(res):
    if not res.get('interpretable'):
        return f"# SP summary\n\nNOT INTERPRETABLE: {res.get('reason')}\n\nNo FER, rescue rate, contrast or verdict is reported.\n"
    v, S, K = res['verdict'], res['S'], res['K']
    lines = ['# Split-principle prospective test: summary (draft)', '',
             f"S keys {S['n_keys']}, K keys {K['n_keys']} (triggered units {K['n_triggered']}), clusters (frames) {S['n_clusters']}, bootstrap {res['n_boot']} (seed {res['seed']}), 95% percentile CI.", '',
             f"## Verdict: {v['label']}", '', f"- P1 (S, estimation) {'holds' if v['P1'] else 'fails'}: d1 = {v['d1']['name']}: {fmt_ci(v['d1'])}",
             f"- P2 (S, non-inferiority) {'holds' if v['P2'] else 'fails'}: d2 = {v['d2']['name']}: {fmt_ci(v['d2'])}",
             f"- P3a (K, estimation, A2 geometry) {'holds' if v['P3a'] else 'fails'}: r3a = {v['r3a']['name']}: {fmt_rate(v['r3a'])}",
             f"- P3b (K, equivalence, A1 geometry) {'holds' if v['P3b'] else 'fails'}: r3b = {v['r3b']['name']}: {fmt_rate(v['r3b'])}",
             f"- P4 (K, decision = E-1 replication) {'holds' if v['P4'] else 'fails'}: r4 = {v['r4']['name']}: {fmt_rate(v['r4'])}",
             f"- refuted by: {', '.join(v['refuted_by']) or 'nothing'}", f"- rule: {v['rule']}", '',
             '## S family arms', '', '| arm | FER [CI] | failures | NMSE mean [CI] | atoms | same-delay pairs (true/false delay) | SBL cap-hit keys (fraction) |', '|---|---|---|---|---|---|---|']
    for a in S_ARMS:
        x = S['arms'][a]
        lines.append(f"| {a} | {x['fer']['point']:.4f} [{x['fer']['ci_lo']:.4f}, {x['fer']['ci_hi']:.4f}] | {x['n_fail']} | {x['nmse']['point']:.4g} [{x['nmse']['ci_lo']:.4g}, {x['nmse']['ci_hi']:.4g}] | "
                     f"{x['n_atoms_mean']:.2f} | {x['n_pair_total']} ({x['n_pair_true_delay']}/{x['n_pair_false_delay']}) | {x['sbl_cap_hit_keys']} ({x['sbl_cap_hit_fraction']['point']:.3f}) |")
    lines += ['', '## S family contrasts (left - right)', '', '| contrast | role | FER diff [CI] | NMSE diff [CI] | McNemar b/c | log10 p (left better) | log10 p (right better) |', '|---|---|---|---|---|---|---|']
    for name, c in S['contrasts'].items():
        m = c['mcnemar']
        lines.append(f"| {name} | {c['role']} | {fmt_ci(c['fer'])} | {fmt_ci(c['nmse'], 5)} | {m['left_only_bad']}/{m['right_only_bad']} | {m['log10_p_left_better']:.2f} | {m['log10_p_right_better']:.2f} |")
    lines += ['', '## K family rescue rate R among triggered units', '', '| arm | R [CI] | rescued / triggered | same-delay pairs (true/false delay) |', '|---|---|---|---|']
    for a in K_ARMS:
        x = K['arms'][a]
        lines.append(f"| {a} | {fmt_rate(x['rate'])} | {x['n_rescued']} / {x['n_triggered']} | {x['n_pair_total']} ({x['n_pair_true_delay']}/{x['n_pair_false_delay']}) |")
    lines += ['', '## K family contrasts (left - right, rescue-rate difference)', '', '| contrast | role | R diff [CI] | McNemar b/c (not rescued) | log10 p (left better) | log10 p (right better) |', '|---|---|---|---|---|---|']
    for name, c in K['contrasts'].items():
        m = c['mcnemar']
        lines.append(f"| {name} | {c['role']} | {fmt_rate(c['rate'])} | {m['left_only_bad']}/{m['right_only_bad']} | {m['log10_p_left_better']:.2f} | {m['log10_p_right_better']:.2f} |")
    lines += ['', f"cost S {S['cost']['core_hours']:.3f} + K {K['cost']['core_hours']:.3f} = {res['total_core_hours']:.3f} core-h; S-H vs independent numpy ridge solve max rel err {S['iso']['max_rel_err_numpy']:.2e}, "
              f"K iso arms {K['checks']['max_iso_rel_err_numpy']:.2e} (tol {NUM_TOL:.0e}); K-fullfix gains == A1 result.gains in {K['checks']['fullfix_equals_a1_result_gains']}/{K['checks']['n']}, "
              f"K-diag-isofix gains == A2 result.gains in {K['checks']['diag_isofix_equals_a2_result_gains']}/{K['checks']['n']} triggered units.", '',
              '(McNemar treats rows as independent pairs; the frozen criterion is the cluster bootstrap.)', '']
    return '\n'.join(lines)


def smoke_counts(rows_dir):
    """Counts only (engineering smoke on frames >= 8600): rows, errors, trigger counts, cap hits, atoms, pairs, check errors, timing, exogenous-hash invariance.
    No FER, rescue rate or contrast."""
    rows, errors, sources = {'S': [], 'K': []}, 0, set()
    for fam in ('S', 'K'):
        for path in sorted(Path(rows_dir).glob(f'rows_{fam}_shard*.jsonl*')):
            op = gzip.open if path.suffix == '.gz' else open
            with op(path, 'rt') as handle:
                for line in handle:
                    r = json.loads(line)
                    if r.get('status') == 'ok':
                        rows[fam].append(r)
                    else:
                        errors += 1
            sources.add(json.dumps(json.loads(config_path_of(path).read_text())['_config']['sources_sha256'], sort_keys=True))
    allrows = rows['S'] + rows['K']
    try:
        check_exogenous(allrows)
        exogenous_ok = True
    except NotInterpretable:
        exogenous_ok = False
    out = dict(smoke_only=True, rows_ok={f: len(v) for f, v in rows.items()}, rows_error=errors, all_smoke_flagged=all(r.get('smoke') for r in allrows),
               min_frame=min([r['frame'] for r in allrows] or [0]), source_snapshots=len(sources), exogenous_hashes_shared_per_frame=exogenous_ok,
               frames={f: sorted({r['frame'] for r in v}) for f, v in rows.items()})
    s_arms = {}
    for a in S_ARMS:
        xs = [r['variants'][a] for r in rows['S']]
        s_arms[a] = dict(n_atoms_mean=float(np.mean([x['n_atoms'] for x in xs] or [0])), n_pair_total=sum(x['n_pair'] for x in xs), sbl_cap_hit_keys=sum(bool(x['sbl']['cap_hit']) for x in xs),
                         sbl_jitter_events=sum(x['sbl']['jitter_events'] for x in xs), sbl_iterations_mean=float(np.mean([x['sbl']['iterations'] for x in xs] or [0])),
                         gain_seconds_mean=float(np.mean([x['seconds']['gain'] for x in xs] or [0])), sbl_seconds_mean=float(np.mean([x['seconds']['sbl_shared'] for x in xs] or [0])))
    out['S'] = dict(arms=s_arms, seconds_per_key=[r['elapsed_seconds'] for r in rows['S']], n_candidates_stage2_mean=float(np.mean([r['n_candidates_stage2'] for r in rows['S']] or [0])),
                    iso_max_rel_err_numpy=max([r['variants']['S-H']['iso_check']['rel_err_numpy'] for r in rows['S']] or [0.0]),
                    support_s_h_equals_s_c=all([(p[0], p[1]) for p in r['variants']['S-H']['atoms']] == [(p[0], p[1]) for p in r['variants']['S-C']['atoms']] for r in rows['S']))
    trigd = [r for r in rows['K'] if r['triggered']]
    k_arms = {a: dict(n_pair_total=sum(r['arms'][a]['n_pair'] for r in trigd),
                      n_support_changes_mean=float(np.mean([r['arms'][a]['n_support_changes'] for r in trigd if 'n_support_changes' in r['arms'][a]] or [0])))
              for a in K_ARMS}
    out['K'] = dict(n_keys=len(rows['K']), n_triggered=len(trigd), n_untriggered=len(rows['K']) - len(trigd), arms=k_arms,
                    fullfix_equals_a1_result_gains=sum(r['checks']['full_equals_result_gains'] is True for r in trigd),
                    diag_isofix_equals_a2_result_gains=sum(r['checks']['diag_iso_equals_result_gains'] is True for r in trigd),
                    iso_max_rel_err_numpy=max([r['checks']['iso_rel_err_numpy'] for r in trigd] + [r['checks']['diag_iso_rel_err_numpy'] for r in trigd] or [0.0]),
                    seconds_per_key_triggered=[r['elapsed_seconds'] for r in trigd], seconds_per_key_untriggered=[r['elapsed_seconds'] for r in rows['K'] if not r['triggered']],
                    f0_seconds_mean=float(np.mean([r['f0']['seconds'] for r in rows['K']] or [0])))
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
    target = a.out / 'sp_summary.json'
    if target.exists():
        raise FileExistsError(target)
    res = analyze(a.rows, gates_path=a.gates)
    target.write_text(json.dumps(res, indent=1, sort_keys=True, allow_nan=False) + '\n')
    (a.out / 'sp_summary.md').write_text(markdown(res))
    print(json.dumps(dict(interpretable=res['interpretable'], verdict=(res['verdict'] or {}).get('label') if res['interpretable'] else None, reason=res.get('reason'))))
    return 0 if res['interpretable'] else 2


if __name__ == '__main__':
    sys.exit(main())
