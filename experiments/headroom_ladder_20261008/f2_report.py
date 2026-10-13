#!/usr/bin/env python
"""F2 short report: FER/crossing/gap tables from analyze.py output + per-config misfit and PS slot statistics
from the rows, and the two pre-registered readings.  numpy only.
usage: f2_report.py --analysis analysis.json --out F2_TABLE.md [--json f2_summary.json] <rows dir>...
"""
import argparse
import glob
import json
import math

import numpy as np

CONFIGS = ('D1', 'N4a', 'N4b', 'J4')
ARMS = ('A0', 'PS0', 'PS', 'O1', 'O2', 'O2n', 'O3', 'O5', 'OF2', 'OF3', 'A3')
ORDER = {'O1': 1, 'O2': 2, 'O2n': 2, 'O3': 3, 'O5': 5, 'OF2': 2, 'OF3': 3}  # O2n nested D=2; OF_D free-frequency (supplements)
TARGETS = (0.1, 0.01)


def fnum(x, nd=2):
    return '-' if x is None else f'{x:.{nd}f}'


def fci(c, nd=2):
    if c is None or c.get('est') is None:
        return '-'
    return f"{c['est']:.{nd}f} [{fnum(c['lo'], nd)}, {fnum(c['hi'], nd)}]" + ('*' if c.get('valid', 1) < .95 else '')


def tab(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows])


def cross_text(c, smax, smin):
    if c['est'] is not None:
        return fci(c)
    if c['reason'].startswith('FER>target'):
        return f'>{smax:g} (no crossing)'
    if c['reason'].startswith('FER<=target'):
        return f'<{smin:g} (below at lowest SNR)'
    return c['reason']


def rows_stats(dirs):
    mis, ps, err = {}, {}, {}
    for d in dirs:
        for f in sorted(glob.glob(d + '/rows_shard*.jsonl')):
            for line in open(f):
                r = json.loads(line)
                arm, cfg = r['arm'], r['config']
                if r['status'] != 'ok':
                    err[(cfg, arm)] = err.get((cfg, arm), 0) + 1
                    continue
                if arm in ORDER:
                    mis.setdefault((cfg, arm), {})[r['frame']] = r['misfit']
                if arm == 'PS':
                    ps.setdefault(cfg, []).append(r)
                if arm == 'A0':
                    ps.setdefault(cfg + '_A0', []).append(r)
    return mis, ps, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--analysis', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--json', default='')
    ap.add_argument('dirs', nargs='+')
    a = ap.parse_args()
    an = json.load(open(a.analysis))
    t1 = an['table1']
    snrs = sorted({r['snr'] for r in t1})
    smin, smax = snrs[0], snrs[-1]
    present = [x for x in ARMS if any(r['arm'] == x for r in t1)]
    cross = {(c['target'], c['config'], c['arm']): c for c in an['db']['cross']}
    gap = {(c['target'], c['config'], c['arm']): c for c in an['db']['to_a3']}
    bound = {(g['target'], g['config'], g['arm']): g.get('bound') for g in an['f1']['gaps']}
    mis, ps, err = rows_stats(a.dirs)
    L = [f'# F2 order test: {an["params"]["B"]} bootstrap draws, units={an["n_units"]}, error rows={an["n_err_rows"]}',
         f'analysis: {a.analysis}; SNR grid {snrs}; FER = info_errors>0; gap = x(arm)-x(A3) dB (>0 = arm needs more SNR); '
         f'* = CI from <95% finite draws\n']
    S = {}
    # 1. FER tables
    L.append('## 1. FER (err/n) per config, SNR, arm\n')
    for cfg in CONFIGS:
        arms = [x for x in present if any(r['config'] == cfg and r['arm'] == x for r in t1)]
        rows = []
        for arm in arms:
            cells = {r['snr']: r for r in t1 if r['config'] == cfg and r['arm'] == arm}
            rows.append([arm] + [f"{cells[s]['fer']:.3f} ({cells[s]['frame_err']})" if s in cells else '-' for s in snrs])
        L += [f'### {cfg}\n', tab(['arm'] + [f'{s:g} dB' for s in snrs], rows), '']
    # 2. crossing
    L.append('## 2. Crossing SNR (dB) at FER target, bootstrap 95% CI\n')
    for t in TARGETS:
        rows = [[cfg] + [cross_text(cross[(t, cfg, x)], smax, smin) if (t, cfg, x) in cross else '-' for x in present] for cfg in CONFIGS]
        L += [f'### target {t:g}\n', tab(['config'] + present, rows), '']
    # 3. gaps
    L.append('## 3. Gap to A3 (dB) with CI; bounds when a curve does not cross\n')
    for t in TARGETS:
        rows = []
        for cfg in CONFIGS:
            r = [cfg]
            for x in present[:-1]:
                g = gap.get((t, cfg, x))
                if g is None:
                    r.append('-')
                elif g['est'] is not None:
                    r.append(fci(g))
                else:
                    b = bound.get((t, cfg, x)) or ''
                    r.append(b.replace(' (arm never reaches target by', ' (arm >').replace('dB)', 'dB)') if b else '-')
            rows.append(r)
        L += [f'### target {t:g}\n', tab(['config'] + present[:-1], rows), '']
    # 4. misfit
    L.append('## 4. Oracle operator misfit ||H-H_D||_F^2/||H||_F^2 per frame (median [p25, p75]; mean)\n')
    rows = []
    for cfg in CONFIGS:
        r = [cfg]
        for x in ORDER:
            v = np.array(list(mis.get((cfg, x), {}).values()))
            if len(v):
                r.append(f'{np.median(v):.3g} [{np.percentile(v, 25):.2g}, {np.percentile(v, 75):.2g}]; {v.mean():.3g}')
                S.setdefault('misfit', {}).setdefault(cfg, {})[x] = dict(median=float(np.median(v)), p25=float(np.percentile(v, 25)),
                                                                          p75=float(np.percentile(v, 75)), mean=float(v.mean()), n=len(v))
            else:
                r.append('-')
        rows.append(r)
    L += [tab(['config'] + list(ORDER), rows), '']
    # 5. PS slots
    L.append('## 5. PS (Stage-A arm D) slot use vs truth; B (A0) for reference (all SNR cells pooled)\n')
    rows = []
    for cfg in CONFIGS:
        p, b = ps.get(cfg, []), ps.get(cfg + '_A0', [])
        if not p:
            continue
        m = lambda k, rr=p: float(np.mean([r[k] for r in rr]))  # noqa: E731
        stop = {}
        for r in p:
            stop[r['ps_stopping_reason']] = stop.get(r['ps_stopping_reason'], 0) + 1
        S.setdefault('ps_slots', {})[cfg] = dict(n_slots=m('ps_n_slots'), distinct_delays=m('ps_n_fit_delays'),
            max_slots_per_delay=m('ps_max_slots_per_delay'), frac_multi=float(np.mean([r['ps_n_multi_slot_delays'] > 0 for r in p])),
            taps_covered=m('ps_taps_covered'), rays=float(np.mean([r['n_paths'] for r in p])),
            true_taps=float(np.mean([r['n_distinct_delays'] for r in p])), underfit=m('ps_same_delay_underfit'),
            stopping=stop, b_underfit=float(np.mean([r['same_delay_underfit'] for r in b])), b_slots=float(np.mean([r['n_fit_slots'] for r in b])))
        s = S['ps_slots'][cfg]
        rows.append([cfg, f"{s['rays']:.1f}/{s['true_taps']:.1f}", f"{s['n_slots']:.2f}", f"{s['distinct_delays']:.2f}",
                     f"{s['max_slots_per_delay']:.2f}", f"{s['frac_multi']:.3f}", f"{s['taps_covered']:.2f}", f"{s['underfit']:.3f}",
                     f"{s['b_slots']:.2f}/{s['b_underfit']:.3f}", json.dumps(stop)])
    L += [tab(['config', 'rays/taps (truth)', 'PS slots', 'PS distinct delays', 'PS max slots at one delay', 'frac frames >1 slot at a delay',
               'PS true taps covered', 'PS same-delay underfit', 'B slots/underfit', 'PS stop reasons'], rows), '']
    if err:
        L += ['Error rows (arm failed to run): ' + ', '.join(f'{k[0]}/{k[1]}: {v}' for k, v in sorted(err.items())) + '\n']
    else:
        L += ['Error rows: none.\n']
    # 6. readings
    L.append('## 6. Pre-registered readings\n')
    ra = []
    for t in TARGETS:
        for cfg in ('N4b', 'J4'):
            g = gap.get((t, cfg, 'PS'))
            ok = None if g is None or g['est'] is None else bool(g['est'] <= .3)
            okci = None if g is None or g['est'] is None or g['hi'] is None else bool(g['hi'] <= .3)
            ra.append(dict(target=t, config=cfg, gap=g, point_le_0p3=ok, ci_hi_le_0p3=okci, bound=bound.get((t, cfg, 'PS'))))
    S['reading_a'] = ra
    L.append('(a) PS within 0.3 dB of A3: ' + '; '.join(
        f"@{r['target']:g} {r['config']}: {('gap ' + fci(r['gap'])) if r['gap'] and r['gap']['est'] is not None else (r['bound'] or '-')} "
        f"(point<=0.3: {r['point_le_0p3']}, CI-hi<=0.3: {r['ci_hi_le_0p3']})" for r in ra))
    rb = {}
    L.append('\n(b) smallest D with O_D within 0.2 dB of A3 (point; CI-hi) per config; prediction D1 1, N4a 1-2, N4b 2-3, J4 ~5.')
    L.append('    ladder "spec" = O1,O2,O3,O5 (even-D grid has no point at the centroid); ladder "nested" = O1,O2n,O3,O5 (supplement, monotone); ladder "free" = OF2,OF3 (supplement, free-frequency exponentials, N4b/J4 only, frames 0-599, SNR 6-11):')
    for lname, arms_l in (('spec', ['O1', 'O2', 'O3', 'O5']), ('nested', ['O1', 'O2n', 'O3', 'O5']), ('free', ['OF2', 'OF3'])):
        if lname != 'spec' and not any(r['arm'] == arms_l[1 if lname == 'nested' else 0] for r in t1):
            continue
        for t in TARGETS:
            for cfg in CONFIGS:
                pts, cis, per = None, None, {}
                for x in arms_l:
                    g = gap.get((t, cfg, x))
                    if g is None or g['est'] is None:
                        per[x] = None
                        continue
                    per[x] = (g['est'], g['hi'])
                    if pts is None and g['est'] <= .2:
                        pts = ORDER[x]
                    if cis is None and g['hi'] is not None and g['hi'] <= .2:
                        cis = ORDER[x]
                rb[f'{lname}/{t:g}/{cfg}'] = dict(smallest_D_point=pts, smallest_D_ci=cis, per_arm=per)
                L.append(f"- [{lname}] @{t:g} {cfg}: smallest D point={pts}, CI-hi={cis}; gaps " + ', '.join(
                    f"{x}:" + ('undef' if v is None else f'{v[0]:.2f}[hi {v[1]:.2f}]') for x, v in per.items()))
    S['reading_b'] = rb
    open(a.out, 'w').write('\n'.join(L) + '\n')
    if a.json:
        json.dump(S, open(a.json, 'w'), indent=1, default=float)
    print('\n'.join(L[-12:]))


if __name__ == '__main__':
    main()
