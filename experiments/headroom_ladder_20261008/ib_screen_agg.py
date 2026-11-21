#!/usr/bin/env python
"""Information-budget screen: aggregation, K*, labels (spec research/info-budget-screen-20261014.md sections 4-6, FROZEN).  Reads rows only.

    python -B ib_screen_agg.py --locate DIR --confirm DIR --out DIR       full analysis (K*, H_low, labels, report-only tables)
    python -B ib_screen_agg.py --locate DIR --plan                       print the confirm plan (L values to run per reference) from the locate stage
    python -B ib_screen_agg.py --selftest
Mechanics (section 4): per endpoint (stage, reference, condition, grid L): LCB = mean(A) - e_A - mean(f) - e_f + mean(J) - e_J (empirical Bernstein, ranges A [0, 2N],
f [0, B], J [0, N log2(1 + beta rho / s2)]), endpoint risk delta = .05 / (2 stages x 24 grid x 5 conditions x 2 references) split in three over the terms.  LCB/N > tau = 1.
Locate (64 frames) -> m leading passes -> confirm (512 independent frames) indices 0..m (first two if m = 0) -> K* = point before the first failing confirmed point
(none if the smallest fails; right-censored if every confirmed point passes and the grid is not exhausted).  H_low = K*/Kc_best, K = 8 L.  Labels (section 6) per reference.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from pathlib import Path
import sys

import numpy as np

import ib_screen_core as C

HERE = Path(__file__).resolve().parent
TAU_EMP = 1.154


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
    """{(ref, L): dict of arrays over frames (sorted by frame): A, f, J, ...}"""
    by = {}
    for r in rows:
        by.setdefault((r['ref'], r['L']), {})[r['frame']] = r
    out = {}
    for key, fr in by.items():
        frames = sorted(fr)
        keys = [k for k in ('A', 'f', 'J', 'U', 'Jz', 'gmi') if k in fr[frames[0]]]
        out[key] = {k: np.array([fr[f][k] for f in frames]) for k in keys}
        out[key]['n'] = len(frames)
        out[key]['frames'] = frames
    return out


def endpoint(models, ref, L, cond, g, ci):
    rng = C.term_ranges(models[ref], L, cond)
    return C.lcb(g['A'][:, ci], g['f'][:, ci], g['J'][:, ci], rng)


Z95 = 1.959963984540054


def point_crossing(Ls, m):
    """report-only: K = 8 L at which the mean LB/N first drops below 1 (linear in L between grid points).  Returns (K, status): status 'exact' | 'below_at_first_point'
    (mean already < 1 at the smallest L: K <= 8 L_min) | 'never_below' (K >= 8 L_max)."""
    for i, v in enumerate(m):
        if v < C.TAU:
            if i == 0:
                return 8. * Ls[0], 'below_at_first_point'
            x0, x1, y0, y1 = Ls[i - 1], Ls[i], m[i - 1], m[i]
            return 8. * (x0 + (y0 - C.TAU) / (y0 - y1) * (x1 - x0)), 'exact'
    return 8. * Ls[-1], 'never_below'


def frame_scores(g, ci, kind):
    """per-frame score vectors (bits) for one (ref, L) group and condition index: 'lb' = A - f + J, 'gmi' = GMI - f + J (no guarantee), 'ray' = A - U + J_z."""
    if kind == 'lb':
        return g['A'][:, ci] - g['f'][:, ci] + g['J'][:, ci]
    if kind == 'gmi':
        return g['gmi'][:, ci] - g['f'][:, ci] + g['J'][:, ci]
    return g['A'][:, ci] - g['U'][:, ci] + g['Jz'][:, ci]


def report_only_curves(grp, ref, conds, kind, Ls=C.LGRID):
    """REPORT-ONLY, outside the decision: per condition the mean score/N with a plain normal 95% CI over frames at every grid L, and the point-estimate crossing K of 1
    (also for the lower / upper CI curves) against Kc_best."""
    out = {}
    for ci, cond in enumerate(conds):
        rows, mean, lo, hi = {}, [], [], []
        for L in Ls:
            g = grp.get((ref, L))
            if g is None or (kind == 'gmi' and 'gmi' not in g) or (kind == 'ray' and 'U' not in g):
                continue
            s = frame_scores(g, ci, kind) / C.N
            m, se = float(s.mean()), float(s.std(ddof=1) / np.sqrt(len(s)))
            rows[str(L)] = dict(mean=m, ci95=[m - Z95 * se, m + Z95 * se], se=se, n=int(len(s)))
            mean.append(m)
            lo.append(m - Z95 * se)
            hi.append(m + Z95 * se)
        if not rows:
            continue
        Lh = [L for L in Ls if str(L) in rows]
        K, st = point_crossing(Lh, mean)
        Klo, stlo = point_crossing(Lh, lo)
        Khi, sthi = point_crossing(Lh, hi)
        Kc = C.KC_BEST.get(cond)
        out[f'{cond[0]:g}|{cond[1]:g}'] = dict(per_L=rows, crossing_K=K, crossing_status=st, crossing_K_lower_ci_curve=Klo, crossing_K_upper_ci_curve=Khi, Kc_best=Kc,
                                               ratio_to_Kc_best=None if Kc is None else K / Kc)
    return out


def analyze(locate, confirm, conds, models, with_ray=True):
    """locate / confirm: grouped rows.  Returns the full result dict."""
    dec = {}
    G = len(C.LGRID)
    for ref in C.REFS_DECISION:
        dec[ref] = {}
        for ci, cond in enumerate(conds[:len(C.CONDS)]):
            loc = []
            for gi, L in enumerate(C.LGRID):
                if (ref, L) not in locate:
                    loc.append(None)
                    continue
                loc.append(endpoint(models, ref, L, cond, locate[(ref, L)], ci))
            have_all = all(x is not None for x in loc)
            e = dict(locate=[None if x is None else dict(mean_over_N=x['mean_over_N'], lcb_over_N=x['lcb_over_N'], eA=x['eA'], ef=x['ef'], eJ=x['eJ'], n=x['n']) for x in loc])
            if not have_all:
                e.update(status='locate incomplete')
                dec[ref][f'{cond[0]:g}|{cond[1]:g}'] = e
                continue
            m = C.locate_passes([x['lcb_over_N'] for x in loc])
            plan = C.confirm_plan(m)
            e.update(m_locate=m, plan=plan, plan_L=[C.LGRID[j] for j in plan])
            conf, miss = {}, []
            for j in plan:
                key = (ref, C.LGRID[j])
                if key not in confirm:
                    miss.append(C.LGRID[j])
                    continue
                conf[j] = endpoint(models, ref, C.LGRID[j], cond, confirm[key], ci)
            e['confirm'] = {str(C.LGRID[j]): dict(mean_over_N=x['mean_over_N'], lcb_over_N=x['lcb_over_N'], eA=x['eA'], ef=x['ef'], eJ=x['eJ'], n=x['n']) for j, x in conf.items()}
            if miss:
                e.update(status='confirm incomplete', missing_L=miss)
                dec[ref][f'{cond[0]:g}|{cond[1]:g}'] = e
                continue
            kidx, status = C.decide_kstar({j: x['lcb_over_N'] for j, x in conf.items()}, plan)
            Kc = C.KC_BEST[cond]
            K = None if kidx is None else 8 * C.LGRID[kidx]
            e.update(status=status, kstar_index=kidx, kstar_L=None if kidx is None else C.LGRID[kidx], kstar_K=K, Kc_best=Kc, H_low=None if K is None else K / Kc)
            k2, s2 = C.decide_kstar({j: x['lcb_over_N'] for j, x in conf.items()}, plan, tau=TAU_EMP)
            e['side_table_tau_1p154'] = dict(kstar_K=None if k2 is None else 8 * C.LGRID[k2], status=s2)
            dec[ref][f'{cond[0]:g}|{cond[1]:g}'] = e
    labels = {}
    for ref in C.REFS_DECISION:
        h = [dec[ref][f'{c[0]:g}|{c[1]:g}'].get('H_low') for c in conds[:len(C.CONDS)]]
        done = all('H_low' in dec[ref][f'{c[0]:g}|{c[1]:g}'] for c in conds[:len(C.CONDS)])
        labels[ref] = dict(H_low=h, label=C.classify(h) if done else 'incomplete')
    res = dict(decision=dec, labels=labels)
    # report-only: mean curves (all stages), RAY, GMI
    curves = {}
    for stage_name, grp in (('locate', locate), ('confirm', confirm)):
        for (ref, L), g in grp.items():
            if ref in ('RAY',):
                continue
            for ci, cond in enumerate(conds):
                key = f'{stage_name}|{ref}|{cond[0]:g}|{cond[1]:g}'
                curves.setdefault(key, {})[str(L)] = dict(LB_over_N=float((g['A'][:, ci].mean() - g['f'][:, ci].mean() + g['J'][:, ci].mean()) / C.N), n=g['n'],
                                                         A_over_N=float(g['A'][:, ci].mean() / C.N), f_over_N=float(g['f'][:, ci].mean() / C.N), J_over_N=float(g['J'][:, ci].mean() / C.N),
                                                         gmi_LB_over_N=float((g['gmi'][:, ci].mean() - g['f'][:, ci].mean() + g['J'][:, ci].mean()) / C.N) if 'gmi' in g else None)
    res['report_only_curves'] = curves
    if with_ray:
        ray = {}
        for stage_name, grp in (('locate', locate), ('confirm', confirm)):
            for (ref, L), g in grp.items():
                if ref != 'RAY':
                    continue
                for ci, cond in enumerate(conds):
                    ray.setdefault(f'{stage_name}|{cond[0]:g}|{cond[1]:g}', {})[str(L)] = dict(
                        score_over_N=float((g['A'][:, ci] - g['U'][:, ci] + g['Jz'][:, ci]).mean() / C.N), n=g['n'])
        res['report_only_ray'] = ray
    # rho maximising K*_LCB per SNR (decision references, available conditions)
    best = {}
    for ref in C.REFS_DECISION:
        for snr in sorted({c[0] for c in conds[:len(C.CONDS)]}):
            cand = [(dec[ref][f'{c[0]:g}|{c[1]:g}'].get('kstar_K'), c[1]) for c in conds[:len(C.CONDS)] if c[0] == snr]
            cand = [x for x in cand if x[0] is not None]
            best[f'{ref}|{snr:g}'] = None if not cand else max(cand)[1]
    res['report_only_best_rho_per_snr'] = best
    res['n_endpoints'] = C.n_endpoints()
    res['delta_endpoint'] = C.delta_endpoint()
    return res


def write_md(res, path):
    L = ['# Information-budget screen: results', '', 'Spec `.trellis/tasks/10-08-doppler-cluster/research/info-budget-screen-20261014.md` (frozen a34777b6). tau = 1 bit/QPSK symbol, '
         f"alpha = {C.ALPHA}, {res['n_endpoints']} endpoints, delta per endpoint {res['delta_endpoint']:.3e} (split in three over A, f, J).", '', '## Labels (section 6)', '']
    for ref, lab in res['labels'].items():
        L.append(f"- **{ref}: {lab['label']}**; H_low = " + ', '.join('-' if h is None else f'{h:.2f}' for h in lab['H_low']))
    for ref in C.REFS_DECISION:
        L += ['', f'## {ref}: K* per condition', '', '| condition | locate passes m | confirm L | K* (L) | status | Kc_best | H_low | LCB/N at confirm L | tau 1.154 side table K* |', '|---|---|---|---|---|---|---|---|---|']
        for k, e in res['decision'][ref].items():
            conf = ', '.join(f"L{l}:{v['lcb_over_N']:.3f}" for l, v in e.get('confirm', {}).items())
            L.append(f"| {k} | {e.get('m_locate', '-')} | {e.get('plan_L', '-')} | {e.get('kstar_K', '-')} ({e.get('kstar_L', '-')}) | {e['status']} | {e.get('Kc_best', '-')} | "
                     f"{'-' if e.get('H_low') is None else format(e['H_low'], '.2f')} | {conf} | {e.get('side_table_tau_1p154', {}).get('kstar_K', '-')} |")
    ro = res.get('report_only_extra') or {}
    if ro:
        L += ['', '## REPORT-ONLY (outside the decision): point-estimate crossing of mean LB/N = 1', '',
              f"Mean LB/N per frame set with a plain normal 95% CI over the 64 locate frames; K = 8L where the mean first drops below 1 (linear in L); in brackets the same for the lower / upper CI curve. "
              f"Consistency of the report-only run with the decision locate run (A, f, J of the 5 conditions identical): {ro.get('consistency_with_decision_locate_run')}.", '']
        for name in [k for k in ro if k.startswith(('LB_', 'GMI_LB_')) or k == 'RAY']:
            L += [f'### {name}', '', '| condition | crossing K [lower-CI curve, upper-CI curve] | status | Kc_best | K / Kc_best | mean LB/N at L = 4, 8, 16, 24, 32, 48, 96 |', '|---|---|---|---|---|---|']
            for k, v in ro[name].items():
                per = v['per_L']
                pts = ', '.join(f"{per[str(l)]['mean']:.3f}" if str(l) in per else '-' for l in (4, 8, 16, 24, 32, 48, 96))
                L.append(f"| {k} | {v['crossing_K']:.0f} [{v['crossing_K_lower_ci_curve']:.0f}, {v['crossing_K_upper_ci_curve']:.0f}] | {v['crossing_status']} | {v['Kc_best'] if v['Kc_best'] else '-'} | "
                         f"{'-' if v['ratio_to_Kc_best'] is None else format(v['ratio_to_Kc_best'], '.2f')} | {pts} |")
            L.append('')
    Path(path).write_text('\n'.join(L) + '\n')


def selftest():
    ok = True
    G = len(C.LGRID)
    # stage logic
    assert C.locate_passes([1.2, 1.1, .9, 1.3]) == 2 and C.locate_passes([.9, 1.5]) == 0 and C.locate_passes([1.1] * G) == G
    assert C.confirm_plan(0) == [0, 1] and C.confirm_plan(3) == [0, 1, 2, 3] and C.confirm_plan(G) == list(range(G))
    cases = [({0: 1.2, 1: .8}, [0, 1], (0, 'exact')), ({0: .9, 1: 1.5}, [0, 1], (None, 'none')), ({0: 1.2, 1: 1.1}, [0, 1], (1, 'right_censored')),
             ({j: 1.2 for j in range(G)}, list(range(G)), (G - 1, 'grid_end')), ({0: 1.2, 1: 1.2, 2: 1.2, 3: .9}, [0, 1, 2, 3], (2, 'exact'))]
    for lcb, plan, want in cases:
        got = C.decide_kstar(lcb, plan)
        ok &= got == want
        print('selftest decide_kstar', plan[-1], got, 'ok' if got == want else f'MISMATCH want {want}')
    # classification (spec: (1.30, 1.30, 1.30, 1.15, 1.15) must be WEAK)
    for h, want in (([1.3, 1.3, 1.3, 1.15, 1.15], 'WEAK'), ([1.3, 1.3, 1.3, 1.3, .5], 'INFO-HEADROOM'), ([1.3, 1.3, 1.3, None, 1.0], 'WEAK' if False else 'UNINFORMATIVE'),
                    ([1.12, 1.11, 1.3, 1.1, .2], 'WEAK'), ([None] * 5, 'UNINFORMATIVE')):
        got = C.classify(h)
        ok &= got == want
        print('selftest classify', h, got, 'ok' if got == want else f'MISMATCH want {want}')
    # Bernstein offsets: formula and monotonicity
    e64 = C.eb_offset(100., 64, 2048., C.delta_endpoint() / 3)
    e512 = C.eb_offset(100., 512, 2048., C.delta_endpoint() / 3)
    ok &= e64 > e512 > 0
    print('selftest eb_offset (A range, n=64 / 512):', round(e64, 1), round(e512, 1))
    # end-to-end plumbing on synthetic rows (no heavy compute): A=1800+noise, f=40 L, J=300
    models = {'MODEL': C.ModelRef(), 'PHYS': C.PhysRef()}
    rng = np.random.default_rng(0)
    nc = len(C.CONDS)

    def synth(n, Ls):
        rows = []
        for L in Ls:
            for fr in range(n):
                for ref in C.REFS_DECISION:
                    rows.append(dict(stage='x', L=L, frame=fr, ref=ref, A=(1800. + 10. * rng.standard_normal(nc)).tolist(), f=(40. * L + 5. * rng.standard_normal(nc)).tolist(),
                                     J=(300. + 3. * rng.standard_normal(nc)).tolist()))
        return rows

    loc, conf = group(synth(64, C.LGRID)), group(synth(512, C.LGRID))
    res = analyze(loc, conf, C.CONDS, models, with_ray=False)
    for ref in C.REFS_DECISION:
        e = res['decision'][ref]['6.5|0.2']
        print('selftest end-to-end', ref, 'locate passes', e['m_locate'], 'plan', e['plan_L'], 'status', e['status'], 'K*', e.get('kstar_K'), 'H_low', e.get('H_low'),
              'LCB/N at locate L4', round(e['locate'][0]['lcb_over_N'], 3), 'confirm L4', round(e['confirm']['4']['lcb_over_N'], 3))
        ok &= e['m_locate'] == 0 and e['plan'] == [0, 1]
    Kx, sx = point_crossing([4, 8, 12, 16], [1.4, 1.2, 0.9, 0.6])
    ok &= abs(Kx - 8 * (8 + (1.2 - 1.) / (1.2 - .9) * 4)) < 1e-12 and sx == 'exact' and point_crossing([4, 8], [.9, .8])[1] == 'below_at_first_point' and point_crossing([4, 8], [1.5, 1.2])[1] == 'never_below'
    print('selftest point_crossing', Kx, sx)
    print('SELFTEST', 'PASS' if ok else 'FAIL')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--locate', type=Path)
    ap.add_argument('--confirm', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--report-only', type=Path, default=None, help='locate-stage run with --ray --gmi --with-9p5 (report-only columns)')
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    models = {'MODEL': C.ModelRef(), 'PHYS': C.PhysRef()}
    rows, cfg, lf = load_rows(args.locate)
    conds = tuple(tuple(c) for c in cfg['conds'])
    loc = group(rows)
    if args.plan:
        plans = {}
        for ref in C.REFS_DECISION:
            need = set()
            for ci, cond in enumerate(conds[:len(C.CONDS)]):
                m = C.locate_passes([endpoint(models, ref, L, cond, loc[(ref, L)], ci)['lcb_over_N'] for L in C.LGRID])
                need |= {C.LGRID[j] for j in C.confirm_plan(m)}
            print(ref, 'confirm L:', sorted(need))
            plans[ref] = sorted(need)
        plans['union'] = sorted(set().union(*[set(v) for v in plans.values()]))
        (args.locate / 'confirm_plan.json').write_text(json.dumps(plans))
        return
    crow, ccfg, cf = load_rows(args.confirm)
    res = analyze(loc, group(crow), conds, models)
    cgrp = group(crow)
    ro = {}
    if args.report_only:
        rrows, rcfg, rf = load_rows(args.report_only)
        rconds = tuple(tuple(c) for c in rcfg['conds'])
        rgrp = group(rrows)
        # the report-only run recomputes the five decision conditions: verify it is the same data as the decision locate run
        diffs = [float(np.max(np.abs(rgrp[k][t][:, :len(C.CONDS)] - loc[k][t]))) for k in loc for t in ('A', 'f', 'J') if k in rgrp]
        ro['consistency_with_decision_locate_run'] = bool(len(diffs) == 3 * len(loc) and max(diffs) == 0.)
        ro['consistency_max_abs_diff'] = max(diffs) if diffs else None
        for ref in C.REFS_DECISION:
            ro[f'LB_{ref}'] = report_only_curves(rgrp, ref, rconds, 'lb')
            ro[f'GMI_LB_{ref}'] = report_only_curves(rgrp, ref, rconds, 'gmi')
        ro['RAY'] = report_only_curves(rgrp, 'RAY', rconds, 'ray')
        ro['confirm_L4_L8_decision_conditions'] = {ref: report_only_curves(cgrp, ref, conds[:len(C.CONDS)], 'lb', Ls=(4, 8)) for ref in C.REFS_DECISION}
        ro['rows_files'] = [Path(f).name for f in rf]
        ro['conds'] = [list(c) for c in rconds]
    res['report_only_extra'] = ro
    res['_argv'] = sys.argv
    res['_config'] = dict(locate_dir=str(args.locate), confirm_dir=str(args.confirm), locate_cfg=cfg, confirm_cfg=ccfg, rows_files=[Path(f).name for f in lf + cf])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'ib_screen_results.json').write_text(json.dumps(res, indent=1, default=float, allow_nan=False) + '\n')
    write_md(res, args.out / 'RESULTS.md')
    print((args.out / 'RESULTS.md').read_text())


if __name__ == '__main__':
    main()
