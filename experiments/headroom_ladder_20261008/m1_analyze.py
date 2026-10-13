#!/usr/bin/env python
"""M1 DPSS-ladder analysis.  Reuses analyze.py (Data, boot_curves, db_analysis, table1) unchanged; A3 reference rows are the F2 A3 rows
restricted to the SAME (config, snr, frame) cells as the M1 rows (frames 0..599), so arm-vs-A3 gaps are fully paired.

usage: m1_analyze.py --out-dir DIR [--B 20000] --a3 <f2 dir>[,<f2 dir>] --m1 <m1 dir> [<m1 dir> ...]
Outputs: DIR/M1_TABLE.md, DIR/m1_summary.json (+ analysis input md5s).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import analyze

CONFIGS = ('D1', 'N4a', 'N4b', 'J4')
ARMS = ('P1', 'P2', 'P3', 'P4', 'P6', 'P8', 'GX', 'A3')
ORDER = {'P1': 1, 'P2': 2, 'P3': 3, 'P4': 4, 'P6': 6, 'P8': 8}
TARGETS = (0.1, 0.01)
THRESH = 0.2  # dB: "saturated" = gap to A3 <= THRESH


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(dirs):
    for d in dirs:
        for f in sorted(glob.glob(d + '/rows_shard*.jsonl')):
            for line in open(f):
                if line.strip():
                    yield f, json.loads(line)


def fnum(x, nd=2):
    return '-' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:.{nd}f}'


def fci(c, nd=2):
    if c is None or c.get('est') is None or not math.isfinite(c['est']):
        return '-'
    return f"{c['est']:.{nd}f} [{fnum(c['lo'], nd)}, {fnum(c['hi'], nd)}]" + ('*' if c.get('valid', 1) < .95 else '')


def tab(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--B', type=int, default=20000)
    ap.add_argument('--seed', type=int, default=20261008)
    ap.add_argument('--a3', required=True)
    ap.add_argument('--m1', nargs='+', required=True)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    md5s = {}
    m1_rows, cells = [], set()
    for f, r in load(a.m1):
        md5s[f] = md5(f) if f not in md5s else md5s[f]
        m1_rows.append(r)
        cells.add((r['config'], r['snr_centi_db'], r['frame']))
    ref = []
    for f, r in load(a.a3.split(',')):
        if r['arm'] == 'A3' and r['status'] == 'ok' and (r['config'], r['snr_centi_db'], r['frame']) in cells:
            ref.append(r)
            md5s.setdefault(f, md5(f))
    rows = [dict(r, _run=0) for r in m1_rows + ref]
    n_err = sum(r['status'] != 'ok' for r in rows)
    idx = {c: i + 1 for i, c in enumerate(CONFIGS) if any(r['config'] == c for r in rows)}
    inv = {float(i): c for c, i in idx.items()}
    for r in rows:
        r['rho_permille'] = 1000 * idx[r['config']]
        r['_run'] = (r['_run'], r['config'])
    analyze.ARMS = ARMS
    D = analyze.Data(rows)
    rng = np.random.default_rng(a.seed)
    fer, neff = analyze.boot_curves(D, a.B, rng)
    db = analyze.db_analysis(D, fer, neff, list(TARGETS), 0.5)
    db.pop('X', None)
    t1 = [dict(r, config=inv[r['rho']]) for r in analyze.table1(D)]
    cross = {(c['target'], inv[c['rho']], c['arm']): c for c in db['cross']}
    gap = {(c['target'], inv[c['rho']], c['arm']): c for c in db['to_a3']}
    snrs = sorted({r['snr'] for r in t1})
    smax = snrs[-1]
    present = [x for x in ARMS if any(r['arm'] == x for r in t1)]
    pres_x = [x for x in present if x != 'GX']  # GX (30 frames/cell) only in the FER table
    misfit = {}
    for r in rows:
        if r['status'] == 'ok' and r['arm'] in ORDER:
            misfit.setdefault((r['config'], r['arm']), {})[r['frame']] = r['misfit']
    wmax = {}
    for r in rows:
        if r['status'] == 'ok' and r['arm'] in ORDER:
            wmax.setdefault(r['config'], {})[r['frame']] = r['dpss_W_max']

    def bound(t, cfg, x):
        g, c3 = gap.get((t, cfg, x)), cross.get((t, cfg, 'A3'))
        if g is None or g['est'] is not None and math.isfinite(g['est']):
            return None
        c = cross.get((t, cfg, x))
        if c and c['reason'].startswith('FER>target') and c3 and c3['est'] is not None and math.isfinite(c3['est']):
            return f'> {smax - c3["est"]:.2f} dB (arm > {smax:g} dB)'
        return c['reason'] if c else None

    L = [f'# M1 DPSS oracle ladder: {a.B} bootstrap draws, units={D.U}, error rows={n_err}',
         f'SNR grid {snrs}; FER = info_errors>0; A3 = F2 A3 rows on the same (config, snr, frame) cells; gap = x(arm)-x(A3) dB '
         f'(>0 = arm needs more SNR); * = CI from <95% finite draws\n']
    S = dict(params=dict(B=a.B, seed=a.seed, snrs=snrs), n_units=D.U, n_err_rows=n_err, input_md5=md5s)
    L.append('## 1. FER (err/n) per config, SNR, arm\n')
    for cfg in idx:
        arms = [x for x in present if any(r['config'] == cfg and r['arm'] == x for r in t1)]
        rws = []
        for arm in arms:
            cl = {r['snr']: r for r in t1 if r['config'] == cfg and r['arm'] == arm}
            rws.append([arm] + [f"{cl[s]['fer']:.3f} ({cl[s]['frame_err']}/{cl[s]['frames']})" if s in cl else '-' for s in snrs])
        L += [f'### {cfg}\n', tab(['arm'] + [f'{s:g} dB' for s in snrs], rws), '']
    L.append('## 2. Crossing SNR (dB) at FER target, bootstrap 95% CI\n')
    for t in TARGETS:
        rws = []
        for cfg in idx:
            r = [cfg]
            for x in pres_x:
                c = cross.get((t, cfg, x))
                r.append('-' if c is None else fci(c) if c['est'] is not None and math.isfinite(c['est']) else c['reason'])
            rws.append(r)
        L += [f'### target {t:g}\n', tab(['config'] + pres_x, rws), '']
    L.append('## 3. Gap to A3 (dB) with CI; bound when the arm never reaches the target\n')
    for t in TARGETS:
        rws = []
        for cfg in idx:
            r = [cfg]
            for x in pres_x[:-1]:
                g = gap.get((t, cfg, x))
                r.append('-' if g is None else fci(g) if g['est'] is not None and math.isfinite(g['est']) else (bound(t, cfg, x) or '-'))
            rws.append(r)
        L += [f'### target {t:g}\n', tab(['config'] + pres_x[:-1], rws), '']
    L.append('## 4. DPSS projection misfit ||H-H_D||_F^2/||H||_F^2 per frame (median [p25, p75]; mean) and median W_max (bins)\n')
    rws = []
    for cfg in idx:
        r = [cfg, f"{np.median(list(wmax[cfg].values())):.2f}" if cfg in wmax else '-']
        for x in ORDER:
            v = np.array(list(misfit.get((cfg, x), {}).values()))
            if len(v):
                r.append(f'{np.median(v):.3g} [{np.percentile(v, 25):.2g}, {np.percentile(v, 75):.2g}]; {v.mean():.3g}')
                S.setdefault('misfit', {}).setdefault(cfg, {})[x] = dict(median=float(np.median(v)), p25=float(np.percentile(v, 25)),
                    p75=float(np.percentile(v, 75)), p90=float(np.percentile(v, 90)), mean=float(v.mean()), n=len(v))
            else:
                r.append('-')
        rws.append(r)
    L += [tab(['config', 'W_max med'] + [x for x in ORDER], rws), '']
    L.append(f'## 5. Saturation: smallest D with gap to A3 <= {THRESH} dB (point; CI-hi); prediction D1 1, N4a 2, N4b 3-4, J4 5-6\n')
    sat = {}
    for t in TARGETS:
        for cfg in idx:
            pts = cis = None
            per = {}
            for x in ORDER:
                g = gap.get((t, cfg, x))
                if g is None or g['est'] is None or not math.isfinite(g['est']):
                    per[x] = None
                    continue
                per[x] = (g['est'], g['hi'])
                if pts is None and g['est'] <= THRESH:
                    pts = ORDER[x]
                if cis is None and g['hi'] is not None and math.isfinite(g['hi']) and g['hi'] <= THRESH:
                    cis = ORDER[x]
            sat[f'{t:g}/{cfg}'] = dict(smallest_D_point=pts, smallest_D_ci=cis, per_arm=per)
            L.append(f"- @{t:g} {cfg}: smallest D point={pts}, CI-hi={cis}; gaps " + ', '.join(
                f"{x}:" + ('undef' if v is None else f'{v[0]:.2f}[hi {fnum(v[1])}]') for x, v in per.items()))
    S['saturation'] = sat
    S['table1'], S['cross'], S['gap'] = t1, db['cross'], db['to_a3']
    S['idx'] = idx
    (a.out_dir / 'M1_TABLE.md').write_text('\n'.join(L) + '\n')
    (a.out_dir / 'm1_summary.json').write_text(json.dumps(S, indent=1, default=float) + '\n')
    print('\n'.join(L[-10:]))


if __name__ == '__main__':
    main()
