#!/usr/bin/env python
"""Upper-bound screen: aggregation, endpoints, H_up, labels (spec research/ub-screen-20261015.md sections 4-6, FROZEN).  Reads rows only.

    python -B ub_screen_agg.py --decision DIR [DIR ...] --ro DIR --grid DIR --screen-rows DIR --screen-results JSON --out DIR      full analysis
    python -B ub_screen_agg.py --timing DIR [DIR ...] [--timing-c6 DIR] --out DIR                                                    timing probe -> core-hour projection
    python -B ub_screen_agg.py --selftest
Decision (sections 4-5): endpoint = (reference, condition, nominal ratio in {1.10, 1.25}), L = ceil(ratio Kc_best / 8), 3 x 5 x 2 = 30 one-sided endpoints, delta_i = .05 / 30.
UCB = mean(u) + sqrt(2 S_u^2 ln(2/delta_i) / n) + 7 b_u ln(2/delta_i) / (3 (n - 1)); certified iff UCB / N < 1.  H_up per (reference, condition): 1.10 if both endpoints certified; 1.25 if only
the 1.25 endpoint is certified; NON-MONOTONE (counts as > 1.25) if only the 1.10 endpoint is certified; else > 1.25.  Label per reference over the 5 conditions: NEAR-LIMIT (H_up = 1.10 in >= 4/5),
else BOUNDED-25 (H_up <= 1.25 in >= 4/5), else UNINFORMATIVE.  Everything in section 6 (tau = 1.154, ratios 1.0 / 1.5 / 2.0, UB/N curves, crossings, 9.5 dB) is report-only.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import math
from pathlib import Path
import sys

import numpy as np

import ib_screen_core as C
import ub_screen_core as U

HERE = Path(__file__).resolve().parent
N = C.N
Z95 = 1.959963984540054
REFS = ('MODEL', 'PHYS', 'RAY')
RKEY = {1.10: '1.10', 1.25: '1.25'}


def ckey(cond):
    return f'{cond[0]:g}|{cond[1]:g}'


# ---------------------------------------------------------------------------------------------------------------- loading
def load_rows(d):
    files = sorted(glob.glob(str(Path(d) / 'rows_shard*.jsonl'))) + sorted(glob.glob(str(Path(d) / 'rows_shard*.jsonl.gz')))
    if not files:
        raise FileNotFoundError(d)
    rows = []
    for f in files:
        op = gzip.open if f.endswith('.gz') else open
        with op(f, 'rt') as s:
            rows += [json.loads(x) for x in s if x.strip()]
    cfg = json.loads((Path(d) / 'config_shard000.json').read_text())['_config']
    return rows, cfg, files


def group(rows):
    """{(ref, L): dict(u (n, nc), n, frames, complete, sec)} with frames sorted; duplicates are an error."""
    by = {}
    for r in rows:
        key = (r['ref'], r['L'])
        if r['frame'] in by.setdefault(key, {}):
            raise ValueError(f'duplicate row {key} frame {r["frame"]}')
        by[key][r['frame']] = r
    out = {}
    for key, fr in by.items():
        frames = sorted(fr)
        out[key] = dict(u=np.array([fr[x]['u'] for x in frames]), n=len(frames), frames=frames, complete=bool(frames == list(range(len(frames)))),
                        sec=np.array([fr[x].get('sec', np.nan) for x in frames]))
    return out


def group_screen(rows, models, conds):
    """MODEL / PHYS rows of the screen (A, f, J): u = J + Cst - f per row.  RAY rows of the screen carry no f and are skipped."""
    by, cs = {}, {}
    for r in rows:
        if 'f' not in r:
            continue
        key = (r['ref'], r['L'])
        if key not in cs:
            cs[key] = U.cst(models[r['ref']], r['L'], conds)
        by.setdefault(key, {})[r['frame']] = U.ub_score(r['f'], r['J'], cs[key])
    return {key: dict(u=np.array([fr[x] for x in sorted(fr)]), n=len(fr), frames=sorted(fr), complete=True) for key, fr in by.items()}


# --------------------------------------------------------------------------------------------------------------- decision
def h_up(cert10, cert25):
    """(H_up, non_monotone): 1.10 | 1.25 | None (= '> 1.25')."""
    if cert10 and cert25:
        return 1.10, False
    if cert25:
        return 1.25, False
    return None, bool(cert10)


def label(h_list):
    """NEAR-LIMIT (H_up = 1.10 in >= 4/5), else BOUNDED-25 (H_up <= 1.25 in >= 4/5), else UNINFORMATIVE; None (> 1.25, NON-MONOTONE included) never counts."""
    if sum(1 for h in h_list if h == 1.10) >= 4:
        return 'NEAR-LIMIT'
    if sum(1 for h in h_list if h is not None and h <= 1.25) >= 4:
        return 'BOUNDED-25'
    return 'UNINFORMATIVE'


def endpoint(models, grp, ref, cond, ratio, ci, tau=U.TAU):
    L = U.test_L(cond, ratio)
    g = grp.get((ref, L))
    if g is None or g['n'] < 2:
        return dict(status='missing', L=L, ratio_nominal=ratio)
    st = U.ucb(g['u'][:, ci], U.range_b(models[ref], L, cond))
    out = dict(status='ok', L=L, K=8 * L, ratio_nominal=ratio, ratio_actual=8. * L / C.KC_BEST[cond], n=st['n'], complete_frames=g['complete'], mean_over_N=st['mean'] / N, S_over_N=st['S'] / N,
               var_term_over_N=st['var_term'] / N, range_term_over_N=st['range_term'] / N, ucb_over_N=st['ucb'] / N, b_u_over_N=st['b_u'] / N)
    out['certified'] = bool(out['ucb_over_N'] < tau)
    return out


def analyze_decision(grp, models, conds, tau=U.TAU):
    """grp: {(ref, L): dict(u (n, nc), n)}; conds: the condition list of the rows (index of a condition = column of u)."""
    dec = {}
    for ref in REFS:
        dec[ref] = {}
        for cond in U.CONDS:
            ci = conds.index(cond)
            e = {RKEY[r]: endpoint(models, grp, ref, cond, r, ci, tau) for r in U.RATIOS}
            if all(x['status'] == 'ok' for x in e.values()):
                h, nm = h_up(e['1.10']['certified'], e['1.25']['certified'])
                e.update(H_up=h, non_monotone=nm, status='ok')
            else:
                e.update(H_up=None, non_monotone=False, status='incomplete')
            dec[ref][ckey(cond)] = e
    labels = {}
    for ref in REFS:
        es = list(dec[ref].values())
        done = all(e['status'] == 'ok' for e in es)
        hs = [e['H_up'] for e in es]
        labels[ref] = dict(H_up=hs, non_monotone=[e['non_monotone'] for e in es], label=label(hs) if done else 'incomplete')
    return dict(decision=dec, labels=labels)


# --------------------------------------------------------------------------------------------------------- report-only
def mean_ci(u):
    s = u / N
    m, se = float(s.mean()), float(s.std(ddof=1) / math.sqrt(len(s)))
    return dict(mean=m, se=se, ci95=[m - Z95 * se, m + Z95 * se], n=int(len(s)))


def ro_table(grp, conds, cond_list):
    """ratios 1.0 / 1.5 / 2.0 per (reference, condition): mean u/N with a normal 95% CI over the 512 ro frames.  9.5 dB (Kc_best censored) is listed at every ro L instead."""
    out = {}
    for ref in REFS:
        for cond in cond_list:
            ci = conds.index(cond)
            if cond in C.KC_BEST:
                row = {}
                for r in U.RO_RATIOS:
                    L = U.test_L(cond, r)
                    g = grp.get((ref, L))
                    if g is not None and g['n'] >= 2:
                        row[f'{r:g}'] = dict(L=L, K=8 * L, ratio_actual=8. * L / C.KC_BEST[cond], **mean_ci(g['u'][:, ci]))
                out[f'{ref}|{ckey(cond)}'] = row
            else:
                out[f'{ref}|{ckey(cond)}'] = {f'L{L}': dict(L=L, K=8 * L, ratio_to_320=8. * L / 320., **mean_ci(g['u'][:, ci]))
                                              for (rf, L), g in sorted(grp.items(), key=lambda kv: kv[0][1]) if rf == ref and g['n'] >= 2}
    return out


def point_crossing(Ls, m, tau=1.0):
    """K = 8 L where the mean UB/N first drops below tau (linear in L between grid points).  status: 'exact' | 'below_at_first_point' | 'never_below'."""
    for i, v in enumerate(m):
        if v < tau:
            if i == 0:
                return 8. * Ls[0], 'below_at_first_point'
            x0, x1, y0, y1 = Ls[i - 1], Ls[i], m[i - 1], m[i]
            return 8. * (x0 + (y0 - tau) / (y0 - y1) * (x1 - x0)), 'exact'
    return 8. * Ls[-1], 'never_below'


def curves(grp, ref, conds, Ls=C.LGRID):
    """UB/N point curve on the grid per condition with a normal 95% CI; crossing K for the mean / lower-CI / upper-CI curve."""
    out = {}
    for ci, cond in enumerate(conds):
        per, mean, lo, hi = {}, [], [], []
        for L in Ls:
            g = grp.get((ref, L))
            if g is None or g['n'] < 2:
                continue
            d = mean_ci(g['u'][:, ci])
            per[str(L)] = d
            mean.append(d['mean'])
            lo.append(d['ci95'][0])
            hi.append(d['ci95'][1])
        if not per:
            continue
        Lh = [L for L in Ls if str(L) in per]
        K, st = point_crossing(Lh, mean)
        Kl, sl = point_crossing(Lh, lo)
        Kh, sh = point_crossing(Lh, hi)
        Kc = C.KC_BEST.get(cond)
        out[ckey(cond)] = dict(per_L=per, crossing_K=K, crossing_status=st, crossing_K_lower_ci_curve=Kl, crossing_status_lower=sl, crossing_K_upper_ci_curve=Kh, crossing_status_upper=sh,
                               Kc_best=Kc, ratio_to_Kc_best=None if Kc is None else K / Kc)
    return out


def sandwich(ub_curves, screen_res, cond_list):
    """LB crossing (screen) / Kc_best / UB crossing per reference and condition.  LB: screen report_only_extra LB_{MODEL,PHYS} crossings (mean LB/N = 1); RAY: the screen's report-only RAY score
    (A - U + J_z; NOT a bound)."""
    ex = screen_res.get('report_only_extra', {})
    cur = screen_res.get('report_only_curves', {})
    out, maxdiff = {}, 0.
    for ref in REFS:
        for cond in cond_list:
            k = ckey(cond)
            src = ex.get(f'LB_{ref}' if ref != 'RAY' else 'RAY', {}).get(k)
            lb = None if src is None else dict(crossing_K=src['crossing_K'], status=src['crossing_status'], kind='LB' if ref != 'RAY' else 'RAY report-only score A-U+Jz (not a bound)')
            if ref != 'RAY' and f'locate|{ref}|{k}' in cur and src is not None:  # cross-check against report_only_curves (5 decision conditions)
                per = cur[f'locate|{ref}|{k}']
                Ls = sorted(int(x) for x in per)
                K, _ = point_crossing(Ls, [per[str(L)]['LB_over_N'] for L in Ls])
                maxdiff = max(maxdiff, abs(K - src['crossing_K']))
            ub = ub_curves.get(ref, {}).get(k)
            out[f'{ref}|{k}'] = dict(LB=lb, Kc_best=C.KC_BEST.get(cond), UB_crossing_K=None if ub is None else ub['crossing_K'], UB_status=None if ub is None else ub['crossing_status'],
                                     UB_over_Kc=None if ub is None or cond not in C.KC_BEST else ub['crossing_K'] / C.KC_BEST[cond])
    out['_lb_crossing_crosscheck_max_abs_diff_K'] = maxdiff
    return out


# ----------------------------------------------------------------------------------------------------------------- writing
def fmt(x, p=3):
    return '-' if x is None else format(x, f'.{p}f')


def write_md(res, path):
    d = res['decision_block']
    L = ['# Upper-bound screen: results', '', 'Spec `.trellis/tasks/10-08-doppler-cluster/research/ub-screen-20261015.md` (FROZEN 2026-10-15). tau = 1 bit/QPSK symbol, alpha = '
         f"{U.ALPHA}, {res['n_endpoints']} endpoints, delta per endpoint {res['delta_endpoint']:.3e}. Statistic: combined score u = J + Cst - f, one Bernstein term, certified iff UCB/N < 1.", '',
         '## Labels (section 5)', '']
    for ref in REFS:
        lab = d['labels'][ref]
        L.append(f"- **{ref}: {lab['label']}**; H_up = " + ', '.join(('NON-MONOTONE (>1.25)' if nm else '>1.25') if h is None else f'{h:.2f}' for h, nm in zip(lab['H_up'], lab['non_monotone'])) +
                 f"  (conditions: {', '.join(ckey(c) for c in U.CONDS)})")
    L += ['', 'MODEL / PHYS: Gaussian channel with that covariance (Gaussian = least learnable law for a fixed covariance: no transfer to the ray channel). RAY-genie: the generator\'s ray law, genie angles. '
          'Reading table: spec section 5.', '']
    for ref in REFS:
        L += [f'## {ref}: endpoints (decision)', '', '| condition | ratio (nominal / actual) | L (K = 8L) | n | mean u/N | S_u/N | variance term/N | range term/N | UCB/N | certified |', '|---|---|---|---|---|---|---|---|---|---|']
        for k, e in d['decision'][ref].items():
            for rk in ('1.10', '1.25'):
                x = e[rk]
                if x['status'] != 'ok':
                    L.append(f"| {k} | {rk} | {x['L']} | - | - | - | - | - | - | missing |")
                    continue
                L.append(f"| {k} | {rk} / {x['ratio_actual']:.3f} | {x['L']} ({x['K']}) | {x['n']} | {x['mean_over_N']:.4f} | {x['S_over_N']:.4f} | {x['var_term_over_N']:.4f} | {x['range_term_over_N']:.4f} | "
                         f"{x['ucb_over_N']:.4f} | {'YES' if x['certified'] else 'no'} |")
            L.append(f"| {k} | **H_up** | {'NON-MONOTONE (counts as >1.25)' if e['non_monotone'] else ('>1.25' if e['H_up'] is None else format(e['H_up'], '.2f'))} | | | | | | | |")
        L.append('')
    t = res['report_only']['tau_1p154']
    L += ['## REPORT-ONLY (outside alpha)', '', '### tau = 1.154 side table (empirical code threshold 2 I*), same statistic, certified iff UCB/N < 1.154', '']
    for ref in REFS:
        lab = t['labels'][ref]
        L.append(f"- {ref}: label {lab['label']}; H_up = " + ', '.join('>1.25' if h is None else f'{h:.2f}' for h in lab['H_up']))
    L += ['', '### ratios 1.0 / 1.5 / 2.0 (ro stage, 512 frames): mean u/N and normal 95% CI', '', '| ref | condition | ratio | L (K) | actual ratio | mean u/N | 95% CI |', '|---|---|---|---|---|---|---|']
    for k, row in res['report_only']['ro'].items():
        ref, cond = k.split('|', 1)
        for rk, v in row.items():
            if rk.startswith('L'):
                continue
            L.append(f"| {ref} | {cond} | {rk} | {v['L']} ({v['K']}) | {v['ratio_actual']:.3f} | {v['mean']:.4f} | [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}] |")
    L += ['', '### 9.5 dB rho .3 (Kc_best censored >= 320): mean u/N per ro L, report-only', '', '| ref | L (K) | K/320 | mean u/N | 95% CI |', '|---|---|---|---|---|']
    for k, row in res['report_only']['ro'].items():
        ref, cond = k.split('|', 1)
        if cond == ckey(U.COND_REPORT):
            for rk, v in row.items():
                L.append(f"| {ref} | {v['L']} ({v['K']}) | {v['ratio_to_320']:.3f} | {v['mean']:.4f} | [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}] |")
    L += ['', '### Sandwich: LB crossing (screen) / Kc_best / UB crossing (mean UB/N first below 1, 64 frames per L, linear in L)', '',
          '| ref | condition | LB crossing K (screen) | Kc_best | UB crossing K | UB / Kc_best | status |', '|---|---|---|---|---|---|---|']
    for k, v in res['report_only']['sandwich'].items():
        if k.startswith('_'):
            continue
        ref, cond = k.split('|', 1)
        lb = v['LB']
        L.append(f"| {ref} | {cond} | {'-' if lb is None else format(lb['crossing_K'], '.0f') + ' (' + lb['status'] + ')'} | {v['Kc_best'] if v['Kc_best'] else '>= 320 (censored)'} | "
                 f"{'-' if v['UB_crossing_K'] is None else format(v['UB_crossing_K'], '.0f')} | {fmt(v['UB_over_Kc'], 2)} | {v['UB_status']} |")
    L += ['', 'LB for RAY is the screen\'s report-only RAY score (A - U + J_z), not a bound. MODEL/PHYS UB curves come from the screen\'s stored locate rows (same 64 frames as the LB curves); RAY from the grid run.', '',
          '### UB/N point curves (mean over 64 frames) at L = 4, 8, 16, 24, 32, 48, 96', '', '| ref | condition | ' + ' | '.join(f'L{x}' for x in (4, 8, 16, 24, 32, 48, 96)) + ' |', '|---|---|' + '---|' * 7]
    for ref in REFS:
        for k, v in res['report_only']['ub_curves'].get(ref, {}).items():
            L.append(f"| {ref} | {k} | " + ' | '.join(fmt(v['per_L'][str(x)]['mean']) if str(x) in v['per_L'] else '-' for x in (4, 8, 16, 24, 32, 48, 96)) + ' |')
    Path(path).write_text('\n'.join(L) + '\n')


# ----------------------------------------------------------------------------------------------------------------- timing
def timing_mode(dirs, c6dir, out, contention_json):
    per = {}
    for d in dirs:
        rows, _cfg, _f = load_rows(d)
        for r in rows:
            per.setdefault((r['ref'], r['L']), {})[r['frame']] = r['sec']

    def mean_sec(table, key):
        fr = table[key]
        xs = [v for k, v in sorted(fr.items()) if k > 0] or list(fr.values())  # frame 0 of each (ref, L) is a warm-up when more frames exist
        return float(np.mean(xs)), len(xs)

    meas = {ref: {} for ref in REFS}
    for (ref, L), fr in per.items():
        meas[ref][L] = mean_sec(per, (ref, L))
    c6 = {}
    if c6dir:
        rows, _cfg, _f = load_rows(c6dir)
        t6 = {}
        for r in rows:
            t6.setdefault((r['ref'], r['L']), {})[r['frame']] = r['sec']
        for (ref, L), fr in t6.items():
            if L in meas[ref]:
                c6[ref] = mean_sec(t6, (ref, L))[0] / meas[ref][L][0]
    fac_c6 = {ref: max(c6.get(ref, 1.), 1.) for ref in REFS}
    cont = 1.5
    if contention_json and Path(contention_json).exists():
        cont = float(json.loads(Path(contention_json).read_text())['factor_20'])

    def sec(ref, L):
        Ls = sorted(meas[ref])
        return float(np.interp(L, Ls, [meas[ref][x][0] for x in Ls]))

    dec = {ref: U.FRAMES_DECISION[ref] * sum(sec(ref, L) for L in U.decision_Ls()) / 3600. for ref in REFS}
    ro = {ref: 512 * fac_c6[ref] * sum(sec(ref, L) for L in U.ro_Ls()) / 3600. for ref in REFS}
    grid = {'RAY': 64 * fac_c6['RAY'] * sum(sec('RAY', L) for L in C.LGRID) / 3600.}
    tot = sum(dec.values()) + sum(ro.values()) + sum(grid.values())
    proj = dict(decision_core_hours=dec, ro_core_hours=ro, grid_core_hours_RAY=grid, total_core_hours=tot, contention_factor_20=cont, total_core_hours_contended=tot * cont,
                wall_hours_at_20_shards=tot * cont / 20., cond6_factor=fac_c6, frames=dict(decision=U.FRAMES_DECISION, ro=512, grid=64), decision_Ls=U.decision_Ls(), ro_Ls=U.ro_Ls())
    res = dict(_argv=sys.argv, _config=dict(dirs=[str(x) for x in dirs], c6dir=str(c6dir), contention_json=str(contention_json)),
               measured_sec_per_frame={ref: {str(L): dict(sec=v[0], n=v[1]) for L, v in sorted(meas[ref].items())} for ref in REFS}, projection=proj)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'timing.json').write_text(json.dumps(res, indent=1, default=float, allow_nan=False) + '\n')
    L = ['# Upper-bound screen: timing probe and projection', '', 'Single-thread numpy/scipy, one process, seconds per frame for all conditions of the stage at once (frame 0 of each (ref, L) dropped as warm-up).', '',
         '| ref | L | sec per frame (5 conds) | n |', '|---|---|---|---|']
    for ref in REFS:
        for Lm, v in sorted(meas[ref].items()):
            L.append(f'| {ref} | {Lm} | {v[0]:.3f} | {v[1]} |')
    L += ['', f'6th condition (9.5 dB) factor on sec per frame (ro and grid add it): ' + ', '.join(f'{k} x{v:.3f}' for k, v in fac_c6.items()), '',
          '## Projection (core-hours, single-thread; per-L seconds interpolated linearly in L between measured points)', '',
          f"- decision: MODEL {dec['MODEL']:.2f} + PHYS {dec['PHYS']:.2f} + RAY {dec['RAY']:.2f} = {sum(dec.values()):.2f}",
          f"- ro (512 frames, L set {U.ro_Ls()}): MODEL {ro['MODEL']:.2f} + PHYS {ro['PHYS']:.2f} + RAY {ro['RAY']:.2f} = {sum(ro.values()):.2f}",
          f"- grid (RAY, 64 frames, L 4..96): {grid['RAY']:.2f}",
          f'- **total {tot:.2f} core-hours quiet; x{cont:.2f} contention at 20 concurrent shards (screen measurement) = {tot * cont:.2f} core-hours, ~{tot * cont / 20.:.2f} h wall at 20 shards**']
    (out / 'TIMING.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


# ----------------------------------------------------------------------------------------------------------------- selftest
def selftest():
    ok = True
    # (1) UCB formula on hand numbers
    n, S2, b, delta = 100, 4., 10., 0.05 / 30
    u = np.random.default_rng(0).standard_normal(n) * 2. + 5.
    S2 = float(np.var(u, ddof=1))
    lnv = math.log(2. / delta)
    want = float(u.mean()) + math.sqrt(2. * S2 * lnv / n) + 7. * b * lnv / (3. * (n - 1))
    got = U.ucb(u, b)
    ok1 = abs(got['ucb'] - want) < 1e-12 and abs(lnv - math.log(1200.)) < 1e-12 and abs(got['ucb'] - (got['mean'] + C.eb_offset(S2, n, b, delta))) < 1e-12
    hand = U.ucb(np.array([0., 2.] * 50), 10., delta=0.05 / 30)  # mean 1, S2 = 100/99*1 -> hand formula
    S2h = 100. / 99.
    ok1 &= abs(hand['ucb'] - (1. + math.sqrt(2. * S2h * math.log(1200.) / 100) + 70. * math.log(1200.) / (3. * 99.))) < 1e-12
    print('selftest UCB formula', 'ok' if ok1 else 'MISMATCH', f"(ucb={got['ucb']:.6f}, hand={hand['ucb']:.6f})")
    ok &= ok1
    # (2) H_up rule
    for c10, c25, want in ((True, True, (1.10, False)), (False, True, (1.25, False)), (True, False, (None, True)), (False, False, (None, False))):
        g = h_up(c10, c25)
        okk = g == want
        ok &= okk
        print('selftest h_up', (c10, c25), g, 'ok' if okk else f'MISMATCH want {want}')
    # (3) labels, including NON-MONOTONE (None) entries and the 3/5 case
    cases = (([1.10, 1.10, 1.10, 1.10, None], 'NEAR-LIMIT'), ([1.10, 1.10, 1.10, 1.10, 1.25], 'NEAR-LIMIT'), ([1.10, 1.10, 1.10, 1.25, 1.25], 'BOUNDED-25'),
             ([1.10, 1.10, 1.10, 1.25, None], 'BOUNDED-25'), ([1.10, 1.10, 1.10, None, None], 'UNINFORMATIVE'), ([1.25, 1.25, 1.25, None, None], 'UNINFORMATIVE'),
             ([1.25] * 5, 'BOUNDED-25'), ([None] * 5, 'UNINFORMATIVE'))
    for hs, want in cases:
        g = label(hs)
        ok &= g == want
        print('selftest label', hs, g, 'ok' if g == want else f'MISMATCH want {want}')
    # (4) Gate F: range term per symbol at the frozen n, all 30 endpoints, real constants
    models = {'MODEL': C.ModelRef(), 'PHYS': C.PhysRef(), 'RAY': U.RayRef()}
    lnv = math.log(2. / U.delta_endpoint())
    gf = {}
    for ref in REFS:
        nn = U.FRAMES_DECISION[ref]
        gf[ref] = max(7. * U.range_b(models[ref], U.test_L(c, r), c) * lnv / (3. * (nn - 1)) / N for c in U.CONDS for r in U.RATIOS)
    okf = gf['MODEL'] <= .0196 + 5e-4 and gf['PHYS'] <= .0235 + 5e-4 and gf['RAY'] <= .0235 + 5e-4 and max(gf.values()) <= .025
    ok &= okf
    print('selftest Gate F range term/N (max over endpoints):', {k: round(v, 4) for k, v in gf.items()}, 'ok' if okf else 'MISMATCH')
    ok &= decision_Ls_check()
    # (5) end-to-end plumbing on synthetic u (no heavy compute): MODEL all 1.10; PHYS mix of 1.10 / 1.25; RAY 3 x 1.10 + NON-MONOTONE + (>1.25)
    nc, rng = len(U.CONDS), np.random.default_rng(1)
    scen = {'MODEL': [(.95, .90)] * 5,
            'PHYS': [(1.05, .90), (1.05, .90), (1.05, .90), (.95, .90), (.95, .90)],
            'RAY': [(.95, .90), (.95, .90), (.95, .90), (.95, 1.05), (1.05, 1.05)]}
    want_h = {'MODEL': [1.10] * 5, 'PHYS': [1.25, 1.25, 1.25, 1.10, 1.10], 'RAY': [1.10, 1.10, 1.10, None, None]}
    want_lab = {'MODEL': 'NEAR-LIMIT', 'PHYS': 'BOUNDED-25', 'RAY': 'UNINFORMATIVE'}
    grp = {}
    for ref in REFS:
        nn = U.FRAMES_DECISION[ref]
        for L in U.decision_Ls():
            grp[(ref, L)] = dict(u=N * (1. + .05 * rng.standard_normal((nn, nc))), n=nn, frames=list(range(nn)), complete=True)
        for ci, cond in enumerate(U.CONDS):
            for r, m in zip(U.RATIOS, scen[ref][ci]):
                grp[(ref, U.test_L(cond, r))]['u'][:, ci] = N * (m + .05 * rng.standard_normal(U.FRAMES_DECISION[ref]))
    res = analyze_decision(grp, models, list(U.CONDS))
    for ref in REFS:
        got_h = res['labels'][ref]['H_up']
        okk = got_h == want_h[ref] and res['labels'][ref]['label'] == want_lab[ref]
        ok &= okk
        print('selftest end-to-end', ref, got_h, 'NON-MONOTONE flags', res['labels'][ref]['non_monotone'], res['labels'][ref]['label'], 'ok' if okk else f'MISMATCH want {want_h[ref]} {want_lab[ref]}')
    okn = res['labels']['RAY']['non_monotone'] == [False, False, False, True, False]
    ok &= okn
    print('selftest NON-MONOTONE flag recorded:', 'ok' if okn else 'MISMATCH')
    # small n must not certify (range term dominates): n = 64
    st = U.ucb(N * (.5 + .01 * rng.standard_normal(64)), U.range_b(models['PHYS'], 30, (6.5, .2)))
    okc = st['ucb'] / N > 1.
    ok &= okc
    print('selftest n=64 not certifiable (UCB/N =', round(st['ucb'] / N, 3), ')', 'ok' if okc else 'MISMATCH')
    Kx, sx = point_crossing([4, 8, 12, 16], [1.4, 1.2, 0.9, 0.6])
    okp = abs(Kx - 8 * (8 + (1.2 - 1.) / (1.2 - .9) * 4)) < 1e-12 and sx == 'exact' and point_crossing([4, 8], [.9, .8])[1] == 'below_at_first_point' and point_crossing([4, 8], [1.5, 1.2])[1] == 'never_below'
    ok &= okp
    print('selftest point_crossing', Kx, sx, 'ok' if okp else 'MISMATCH')
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def decision_Ls_check():
    want = [28, 30, 31, 32, 34, 35, 38, 40, 43]
    got = U.decision_Ls()
    ratios = {(c, r): 8. * U.test_L(c, r) / C.KC_BEST[c] for c in U.CONDS for r in U.RATIOS}
    ok = got == want and all(1.100 <= v <= 1.130 for (c, r), v in ratios.items() if r == 1.10) and all(1.255 <= v <= 1.278 for (c, r), v in ratios.items() if r == 1.25)
    print('selftest decision L set', got, 'ok' if ok else f'MISMATCH want {want}')
    return ok


# ---------------------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--decision', type=Path, nargs='+')
    ap.add_argument('--ro', type=Path)
    ap.add_argument('--grid', type=Path)
    ap.add_argument('--screen-rows', type=Path, default=C.OUT / 'locate_ro', help="the screen's stored 64-frame locate rows (MODEL, PHYS; 6 conditions)")
    ap.add_argument('--screen-results', type=Path, default=C.OUT / 'screen' / 'ib_screen_results.json')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--timing', type=Path, nargs='+')
    ap.add_argument('--timing-c6', type=Path, default=None)
    ap.add_argument('--contention-json', type=Path, default=C.OUT / 'timing' / 'contention.json')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if args.timing:
        timing_mode(args.timing, args.timing_c6, args.out, args.contention_json)
        return
    models = {'MODEL': C.ModelRef(), 'PHYS': C.PhysRef(), 'RAY': U.RayRef()}
    drows, dcfgs, dfiles = [], [], []
    for d in args.decision:
        r, c, f = load_rows(d)
        drows += r
        dcfgs.append(c)
        dfiles += f
    conds = [tuple(x) for x in dcfgs[0]['conds']]
    dgrp = group(drows)
    res_dec = analyze_decision(dgrp, models, conds)
    tau_emp = analyze_decision(dgrp, models, conds, tau=U.TAU_EMP)
    rrows, rcfg, rfiles = load_rows(args.ro)
    rconds = [tuple(x) for x in rcfg['conds']]
    ro = ro_table(group(rrows), rconds, list(U.CONDS) + ([U.COND_REPORT] if U.COND_REPORT in rconds else []))
    grows, gcfg, gfiles = load_rows(args.grid)
    gconds = [tuple(x) for x in gcfg['conds']]
    srows, scfg, sfiles = load_rows(args.screen_rows)
    sconds = [tuple(x) for x in scfg['conds']]
    ub_curves = {'RAY': curves(group(grows), 'RAY', gconds)}
    sgrp = group_screen(srows, models, sconds)
    for ref in ('MODEL', 'PHYS'):
        ub_curves[ref] = curves(sgrp, ref, sconds)
    screen_res = json.loads(args.screen_results.read_text())
    sand = sandwich(ub_curves, screen_res, sconds)
    res = dict(decision_block=res_dec, report_only=dict(
        tau_1p154=dict(labels=tau_emp['labels'], decision=tau_emp['decision']), ro=ro, ub_curves=ub_curves, sandwich=sand,
        note_9p5='9.5 dB rho .3 (Kc_best censored >= 320) appears only in the ro and curve/sandwich tables, never in the decision'),
        n_endpoints=U.N_ENDPOINTS, delta_endpoint=U.delta_endpoint(), _argv=sys.argv,
        _config=dict(decision_dirs=[str(x) for x in args.decision], ro_dir=str(args.ro), grid_dir=str(args.grid), screen_rows=str(args.screen_rows), screen_results=str(args.screen_results),
                     decision_cfgs=dcfgs, ro_cfg=rcfg, grid_cfg=gcfg, screen_rows_cfg=scfg, decision_files=[Path(f).name for f in dfiles], seed_domain=U.SEED_DOMAIN, tau=U.TAU, tau_emp=U.TAU_EMP,
                     frames_decision=U.FRAMES_DECISION, code_md5=dcfgs[0]['code_md5']))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'ub_screen_results.json').write_text(json.dumps(res, indent=1, default=float, allow_nan=False) + '\n')
    write_md(res, args.out / 'RESULTS.md')
    print((args.out / 'RESULTS.md').read_text())


if __name__ == '__main__':
    main()
