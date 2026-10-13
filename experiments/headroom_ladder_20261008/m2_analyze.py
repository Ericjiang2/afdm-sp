#!/usr/bin/env python
"""M2 test analysis (task 10-08-doppler-cluster, design.md Stage M2).  Reuses analyze.py (Data, boot_curves, db_analysis, table1, wilson,
mcnemar, boot_ratio, plot) unchanged; adds the M2-specific pairings, cost table and the PRE-REGISTERED S1-S4 verdicts.

usage: m2_analyze.py --out-dir DIR [--B 20000] [--B-aux 2000] <run dir> [<run dir> ...]
  run dirs: out/m2_test (arms A0=B, F0, PS0, PS, M_full, M_adapt, A3) and out/m2_test_pb16 (PB16).  Both dirs are treated as ONE run: a unit
  is a frame = (config, channel_seed, physical_gains_sha256, info_sha256); PB16 (SNR 7, 9, 11, N4b/J4 only) is paired to the same frames.

Conventions (unchanged from analyze.py): FER = info_errors > 0.  Crossing SNR = log-linear interpolation of log10 FER vs SNR (dB) on the
SNR grid, first FER <= target scanning upward, FER==0 cell floor 0.5/n.  Bootstrap = frames resampled jointly over all SNR cells and arms
(stratified by config), so arm-vs-arm crossing differences are paired.  gap/diff = x(first) - x(second) in dB (> 0: first needs more SNR).

PRE-REGISTERED (design.md Stage M2), evaluated at FER target 1e-1, point estimate decides, CI reported:
  S1  x(M_adapt) - x(A3)      <= 0.3 dB on N4b AND J4
  S2  x(M_adapt) - x(B)       <= 0.1 dB on D1                  (B = production A0, incl. CSTATE20)
  S3  x(PS) - x(M_adapt)      >= 0.3 dB on N4b AND J4, and mean seconds/cell(M_adapt) <= mean seconds/cell(PS) on those configs
  S4  x(M_full) - x(M_adapt)  >= 0.1 dB on D1 OR N4a          (else adaptivity claim dropped)
Undefined (an arm does not cross the target in 6..11 dB): verdict UNDEFINED with the bound given; reported as FAIL only if the bound already
decides it.  Also reported: 'strict' = CI bound on the right side of the threshold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

import analyze

ARMS = ('F0', 'A0', 'PS0', 'PS', 'M_full', 'M_adapt', 'A3', 'PB16')
CONFIGS = ('D1', 'N4a', 'N4b', 'J4', 'J8')
TARGETS = (0.1, 0.01)
SHOW = ('A0', 'PS', 'M_full', 'M_adapt', 'A3', 'PB16')   # F0 / PS0 reported in the FER table only
DISP = {'A0': 'B'}


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def nm(a):
    return DISP.get(a, a)


def fci(c, nd=2):
    return analyze.fc(c, nd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('runs', nargs='+')
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--B', type=int, default=20000)
    ap.add_argument('--B-aux', dest='B_aux', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=20261008)
    a = ap.parse_args()
    t0 = time.time()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    rows, md5s = [], {}
    for ri, d in enumerate(a.runs):
        for f in sorted(Path(d).glob('rows_shard*.jsonl')):
            md5s[str(f)] = md5(f)
            for x in f.open():
                if x.strip():
                    r = json.loads(x)
                    r['_ri'], r['_rp0'] = ri, r['rho_permille']
                    rows.append(r)
        if (Path(d) / 'results.json').exists():
            md5s[str(Path(d) / 'results.json')] = md5(Path(d) / 'results.json')
    idx = {c: i + 1 for i, c in enumerate(CONFIGS) if any(r['config'] == c for r in rows)}
    inv = {float(i): c for c, i in idx.items()}
    analyze.GN = 'config'
    analyze.LABELS.update(inv)
    analyze.ARMS = ARMS
    for r in rows:
        r['rho_permille'] = 1000 * idx[r['config']]
        r['_run'] = (0, r['config'])           # both run dirs = one run: PB16 pairs to the same frames
    # ------------------------------------------------------------------ cross-check vs merged results.json
    mism, n_cells_checked = 0, 0
    for ri, d in enumerate(a.runs):
        p = Path(d) / 'results.json'
        mine = {}
        for r in rows:
            if r['_ri'] == ri and r['status'] == 'ok':
                c = mine.setdefault((r['config'], r['snr_centi_db'], r['arm']), [0, 0])
                c[0] += 1
                c[1] += r['info_errors'] > 0
        for e in json.loads(p.read_text())['summary']:
            n_cells_checked += 1
            mism += mine.get((e['config'], round(e['snr_db'] * 100), e['arm'])) != [e['frames'], e['frame_errors']]
    n_err_rows = sum(r['status'] != 'ok' for r in rows)
    D = analyze.Data(rows)
    fer, neff = analyze.boot_curves(D, a.B, rng)
    db = analyze.db_analysis(D, fer, neff, list(TARGETS), 0.5)
    X = db.pop('X')
    ai = {x: i for i, x in enumerate(D.arms)}
    cfg_i = {c: D.rhos.index(1000 * idx[c]) for c in idx}
    snrs = [s / 100 for s in D.snrs]
    smax = snrs[-1]
    cross = {(c['target'], inv[c['rho']], c['arm']): c for c in db['cross']}
    gapd = {(c['target'], inv[c['rho']], c['arm']): c for c in db['to_a3']}

    # ------------------------------------------------------------------ helpers
    def make_diff(Xd, cfgmap, aimap, crossd):
        def diff(t, cfg, a_, b_):
            """x(a_) - x(b_) (dB), summary dict + bound text when undefined."""
            d = Xd[t][:, cfgmap[cfg], aimap[a_]] - Xd[t][:, cfgmap[cfg], aimap[b_]]
            s = analyze.summ(d)
            note = ''
            if not math.isfinite(s['est']):
                ca, cb = crossd[(t, cfg, a_)], crossd[(t, cfg, b_)]
                ea, eb = ca['est'], cb['est']
                fa, fb = ca['reason'].startswith('FER>target'), cb['reason'].startswith('FER>target')
                if fa and not fb and eb is not None and math.isfinite(eb):
                    note = f'diff > {smax - eb:.2f} dB ({nm(a_)} never reaches {t:g} by {smax:g} dB)'
                elif fb and not fa and ea is not None and math.isfinite(ea):
                    note = f'diff < {ea - smax:.2f} dB ({nm(b_)} never reaches {t:g} by {smax:g} dB)'
                elif ca['reason'].startswith('FER<=target') or cb['reason'].startswith('FER<=target'):
                    note = f'FER<=target at lowest SNR for {nm(a_) if ca["reason"].startswith("FER<=target") else nm(b_)}: no bracket'
                else:
                    note = f'undefined: {ca["reason"]} / {cb["reason"]}'
            return dict(s, note=note)
        return diff

    diff = make_diff(X, cfg_i, ai, cross)

    def sec_stats(cfg, arm):
        v = D.F[arm]['seconds'][cfg_i[cfg]].ravel()
        v = v[np.isfinite(v)]
        return dict(n=int(len(v)), mean=float(v.mean()), p95=float(np.percentile(v, 95)), median=float(np.median(v))) if len(v) else None

    # ------------------------------------------------------------------ FER table + Wilson, logloss, seconds
    t1 = [dict(r, config=inv[r['rho']]) for r in analyze.table1(D)]
    # ------------------------------------------------------------------ paired comparisons
    def pairs(p, q, cfg, si=None):
        """p = comparator, q = M-side arm.  rescues = p fails & q ok; harms = p ok & q fails."""
        ri = cfg_i[cfg]
        ix = slice(None) if si is None else slice(si, si + 1)
        fp_, fq = D.F[p]['fail'][ri][ix], D.F[q]['fail'][ri][ix]
        m = np.isfinite(fp_) & np.isfinite(fq)
        if not m.any():
            return None
        resc, harm = int(((fp_ == 1) & (fq == 0) & m).sum()), int(((fp_ == 0) & (fq == 1) & m).sum())
        d = np.where(m, D.F[q]['logloss'][ri][ix] - D.F[p]['logloss'][ri][ix], 0.).sum(0)
        n = m.sum(0).astype(float)
        sel = n > 0
        bs = analyze.boot_ratio(d[sel], n[sel], a.B_aux, rng)
        return dict(config=cfg, snr='ALL' if si is None else D.snrs[si] / 100, p=nm(p), q=nm(q), n=int(m.sum()),
                    fail_p=int(((fp_ == 1) & m).sum()), fail_q=int(((fq == 1) & m).sum()), rescues=resc, harms=harm,
                    p_mcnemar=analyze.mcnemar(resc, harm), dll=float(d.sum() / n.sum()),
                    dll_lo=float(np.percentile(bs, 2.5)), dll_hi=float(np.percentile(bs, 97.5)))

    PAIRS = (('A0', 'M_adapt'), ('PS', 'M_adapt'), ('M_full', 'M_adapt'), ('A0', 'M_full'), ('PS', 'M_full'), ('A3', 'M_adapt'))
    paired = []
    for cfg in idx:
        for p, q in PAIRS:
            for si in [None] + list(range(len(D.snrs))):
                r = pairs(p, q, cfg, si)
                if r:
                    paired.append(r)
        if 'PB16' in D.arms:
            for p, q in (('PB16', 'M_adapt'), ('PB16', 'M_full'), ('PS', 'PB16'), ('A3', 'PB16')):
                for si in [None] + list(range(len(D.snrs))):
                    r = pairs(p, q, cfg, si)
                    if r:
                        paired.append(r)
    # PB16 rows vs the other arms are only defined on the 3 SNR cells where PB16 ran; 'ALL' above is restricted by the finite mask.

    # ------------------------------------------------------------------ pre-registered S1-S4
    T = 0.1
    S = {}
    S1 = []
    for cfg in ('N4b', 'J4'):
        g = diff(T, cfg, 'M_adapt', 'A3')
        S1.append(dict(config=cfg, gap=g, pass_point=bool(g['est'] <= .3) if math.isfinite(g['est']) else None,
                       pass_strict=bool(g['hi'] <= .3) if math.isfinite(g['hi']) else None))
    S['S1'] = dict(rule='x(M_adapt)-x(A3) <= 0.3 dB @1e-1 on N4b and J4', rows=S1,
                   verdict=('PASS' if all(r['pass_point'] for r in S1) else 'FAIL') if all(r['pass_point'] is not None for r in S1) else 'UNDEFINED')
    g = diff(T, 'D1', 'M_adapt', 'A0')
    S['S2'] = dict(rule='x(M_adapt)-x(B) <= 0.1 dB @1e-1 on D1', rows=[dict(config='D1', gap=g, pass_point=bool(g['est'] <= .1) if math.isfinite(g['est']) else None,
                                                                          pass_strict=bool(g['hi'] <= .1) if math.isfinite(g['hi']) else None)])
    S['S2']['verdict'] = ('PASS' if S['S2']['rows'][0]['pass_point'] else 'FAIL') if S['S2']['rows'][0]['pass_point'] is not None else 'UNDEFINED'
    S3 = []
    for cfg in ('N4b', 'J4'):
        g = diff(T, cfg, 'PS', 'M_adapt')
        sm, sp = sec_stats(cfg, 'M_adapt'), sec_stats(cfg, 'PS')
        S3.append(dict(config=cfg, adv=g, sec_M_adapt=sm['mean'], sec_PS=sp['mean'],
                       pass_db=bool(g['est'] >= .3) if math.isfinite(g['est']) else None,
                       pass_db_strict=bool(g['lo'] >= .3) if math.isfinite(g['lo']) else None,
                       pass_cost=bool(sm['mean'] <= sp['mean'])))
    S['S3'] = dict(rule='x(PS)-x(M_adapt) >= 0.3 dB @1e-1 on N4b and J4, and mean s/cell M_adapt <= PS', rows=S3,
                   verdict=('PASS' if all(r['pass_db'] and r['pass_cost'] for r in S3) else 'FAIL') if all(r['pass_db'] is not None for r in S3) else 'UNDEFINED')
    S4 = []
    for cfg in ('D1', 'N4a'):
        g = diff(T, cfg, 'M_full', 'M_adapt')
        S4.append(dict(config=cfg, adv=g, pass_point=bool(g['est'] >= .1) if math.isfinite(g['est']) else None,
                       pass_strict=bool(g['lo'] >= .1) if math.isfinite(g['lo']) else None))
    S['S4'] = dict(rule='x(M_full)-x(M_adapt) >= 0.1 dB @1e-1 on D1 or N4a', rows=S4,
                   verdict=('PASS' if any(r['pass_point'] for r in S4) else 'FAIL') if all(r['pass_point'] is not None for r in S4) else 'UNDEFINED')

    # ------------------------------------------------------------------ headline gaps, all configs, both targets
    gaps = []
    for t in TARGETS:
        for cfg in idx:
            row = dict(target=t, config=cfg)
            for arm in ('A0', 'PS', 'M_full', 'M_adapt', 'PB16'):
                if arm not in D.arms or (t, cfg, arm) not in cross or (arm == 'PB16' and cfg not in ('N4b', 'J4')):
                    continue
                g = diff(t, cfg, arm, 'A3')
                row[arm] = g
            row['A3_cross'] = cross[(t, cfg, 'A3')]
            gaps.append(row)
    extra = []   # M_adapt vs B / PS / M_full for every config and both targets
    for t in TARGETS:
        for cfg in idx:
            extra.append(dict(target=t, config=cfg, B_minus_Madapt=diff(t, cfg, 'A0', 'M_adapt'), PS_minus_Madapt=diff(t, cfg, 'PS', 'M_adapt'),
                              Mfull_minus_Madapt=diff(t, cfg, 'M_full', 'M_adapt'), B_minus_Mfull=diff(t, cfg, 'A0', 'M_full')))
    pbx = []   # like-for-like 3-point grid {7, 9, 11} dB, N4b/J4, all arms re-interpolated on the same 3 points
    if 'PB16' in D.arms:
        sub_rows = [r for r in rows if r['config'] in ('N4b', 'J4') and r['snr_centi_db'] in (700, 900, 1100)]
        Ds = analyze.Data(sub_rows)
        fers, neffs = analyze.boot_curves(Ds, a.B, rng)
        dbs = analyze.db_analysis(Ds, fers, neffs, list(TARGETS), 0.5)
        Xs = dbs.pop('X')
        ais = {x: i for i, x in enumerate(Ds.arms)}
        cfgs = {c: Ds.rhos.index(1000 * idx[c]) for c in ('N4b', 'J4')}
        crosss = {(c['target'], inv[c['rho']], c['arm']): c for c in dbs['cross']}
        diffs = make_diff(Xs, cfgs, ais, crosss)
        for t in TARGETS:
            for cfg in ('N4b', 'J4'):
                row = dict(target=t, config=cfg)
                for arm in ('A0', 'PS', 'M_full', 'M_adapt', 'PB16'):
                    row[arm + '_minus_A3'] = diffs(t, cfg, arm, 'A3')
                row['PB16_minus_PS'] = diffs(t, cfg, 'PB16', 'PS')
                row['PB16_minus_Madapt'] = diffs(t, cfg, 'PB16', 'M_adapt')
                row['A3_cross'] = crosss[(t, cfg, 'A3')]
                pbx.append(row)
    cost = []
    for cfg in idx:
        for arm in ('F0', 'A0', 'PS', 'M_full', 'M_adapt', 'A3', 'PB16'):
            if arm in D.arms:
                s = sec_stats(cfg, arm)
                if s:
                    cost.append(dict(config=cfg, arm=nm(arm), **s))
    # cost on the 7/9/11 dB cells only (PB16 comparison)
    cost_pb = []
    if 'PB16' in D.arms:
        cells = [D.snrs.index(x) for x in (700, 900, 1100)]
        for cfg in ('N4b', 'J4'):
            for arm in ('A0', 'PS', 'M_full', 'M_adapt', 'A3', 'PB16'):
                v = np.concatenate([D.F[arm]['seconds'][cfg_i[cfg]][c] for c in cells])
                v = v[np.isfinite(v)]
                cost_pb.append(dict(config=cfg, arm=nm(arm), n=int(len(v)), mean=float(v.mean()), p95=float(np.percentile(v, 95))))
    # trigger rates
    trig = [dict(config=r['config'], snr=r['snr'], arm=nm(r['arm']), trig=r['trig']) for r in t1 if r['arm'] == 'A0']

    # ------------------------------------------------------------------ markdown
    L = [f"# M2 test analysis (expected-power law)\n\nrun dirs: {', '.join(a.runs)}  |  B={a.B} B_aux={a.B_aux} seed={a.seed}  |  units(frames x config)={D.U}  "
         f"rows={len(rows)}  error_rows={n_err_rows}  dup_skipped={D.dups}\n\nFER = info_errors>0; crossing SNR by log-linear interpolation on the SNR grid "
         f"{snrs}; gap/diff = x(first)-x(second) dB (>0: first needs more SNR); CI = paired bootstrap over frames; `*` = <95% finite draws.\n",
         f"Cross-check vs merged results.json summaries: {mism} mismatching cells of {n_cells_checked} (frames and frame_errors per config/SNR/arm).\n"]
    L.append('## 0. PRE-REGISTERED S1-S4 (design.md Stage M2), FER target 1e-1\n')
    for k in ('S1', 'S2', 'S3', 'S4'):
        s = S[k]
        L.append(f"**{k} {s['verdict']}**: {s['rule']}")
        for r in s['rows']:
            g = r.get('gap') or r.get('adv')
            ex = ''
            if k == 'S3':
                ex = f"; s/cell M_adapt {r['sec_M_adapt']:.3f} vs PS {r['sec_PS']:.3f} (cost {'ok' if r['pass_cost'] else 'FAIL'}); dB {'ok' if r['pass_db'] else 'FAIL'}, strict {r['pass_db_strict']}"
            elif k in ('S1', 'S2', 'S4'):
                ex = f"; point {'ok' if r['pass_point'] else 'FAIL'}, strict(CI) {r['pass_strict']}"
            L.append(f"- {r['config']}: {fci(g)} dB {g['note']}{ex}")
        L.append('')
    L.append('## 1. FER per config, SNR, arm (err/n, Wilson 95%), mean logloss, mean s/cell\n')
    snr_list = sorted({r['snr'] for r in t1})
    for cfg in idx:
        L += [f'### {cfg}\n']
        hdr = ['arm'] + [f'{s:g} dB' for s in snr_list]
        rws = []
        for arm in ARMS:
            cl = {r['snr']: r for r in t1 if r['config'] == cfg and r['arm'] == arm}
            if cl:
                rws.append([nm(arm)] + [f"{cl[s]['fer']:.3f} ({cl[s]['frame_err']}/{cl[s]['frames']}) [{cl[s]['lo']:.3f},{cl[s]['hi']:.3f}]" if s in cl else '-' for s in snr_list])
        L += [analyze.tab(hdr, rws), '']
        rws = []
        for arm in ARMS:
            cl = {r['snr']: r for r in t1 if r['config'] == cfg and r['arm'] == arm}
            if cl:
                rws.append([nm(arm)] + [f"{cl[s]['logloss']:.4f}" if s in cl else '-' for s in snr_list])
        L += ['mean logloss (bits):\n', analyze.tab(hdr, rws), '']
    L.append('## 2. Crossing SNR (dB) at FER targets, paired-bootstrap 95% CI\n')
    for t in TARGETS:
        rws = []
        for cfg in idx:
            r = [cfg]
            for arm in SHOW:
                c = cross.get((t, cfg, arm))
                r.append('-' if c is None else fci(c) if c['est'] is not None and math.isfinite(c['est']) else c['reason'])
            rws.append(r)
        L += [f'### target {t:g}\n', analyze.tab(['config'] + [nm(x) for x in SHOW], rws), '']
    L.append('(PB16 crossing uses only SNR 7, 9, 11 on N4b/J4: coarse 3-point interpolation.)\n')
    L.append('## 3. Gap to A3 (dB) [CI]; bound when an arm does not cross\n')
    for t in TARGETS:
        rws = []
        for row in [g for g in gaps if g['target'] == t]:
            r = [row['config']]
            for arm in ('A0', 'PS', 'M_full', 'M_adapt', 'PB16'):
                g = row.get(arm)
                r.append('-' if g is None else (fci(g) if math.isfinite(g['est']) else g['note'] or 'undefined'))
            r.append(fci(row['A3_cross']) if row['A3_cross']['est'] is not None and math.isfinite(row['A3_cross']['est']) else row['A3_cross']['reason'])
            rws.append(r)
        L += [f'### target {t:g}\n', analyze.tab(['config', 'B', 'PS', 'M_full', 'M_adapt', 'PB16', 'A3 crossing'], rws), '']
    L.append('## 4. Arm-vs-arm crossing differences (dB, first minus second; > 0 = first needs more SNR)\n')
    for t in TARGETS:
        rws = []
        for e in [e for e in extra if e['target'] == t]:
            def cell(g):
                return fci(g) if math.isfinite(g['est']) else (g['note'] or 'undefined')
            rws.append([e['config'], cell(e['B_minus_Madapt']), cell(e['PS_minus_Madapt']), cell(e['Mfull_minus_Madapt']), cell(e['B_minus_Mfull'])])
        L += [f'### target {t:g}\n', analyze.tab(['config', 'B - M_adapt', 'PS - M_adapt', 'M_full - M_adapt', 'B - M_full'], rws), '']
    if pbx:
        L.append('## 5. PB16 bound (cap 16, no stopping rule; SNR 7/9/11 only): like-for-like crossing on the SAME 3-point grid {7, 9, 11} dB for all arms\n')
        rws = []

        def cell(g):
            return fci(g) if math.isfinite(g['est']) else (g['note'] or 'undefined')
        for e in pbx:
            rws.append([e['target'], e['config'], cell(e['A0_minus_A3']), cell(e['PS_minus_A3']), cell(e['M_full_minus_A3']), cell(e['M_adapt_minus_A3']),
                        cell(e['PB16_minus_A3']), cell(e['PB16_minus_PS']), cell(e['PB16_minus_Madapt'])])
        L += [analyze.tab(['target', 'config', 'B-A3', 'PS-A3', 'M_full-A3', 'M_adapt-A3', 'PB16-A3', 'PB16-PS', 'PB16-M_adapt'], rws), '']
        rws = [[r['config'], r['arm'], r['n'], f"{r['mean']:.3f}", f"{r['p95']:.3f}"] for r in cost_pb]
        L += ['seconds/cell on the 7/9/11 dB cells (same frames):\n', analyze.tab(['config', 'arm', 'n', 'mean s', 'p95 s'], rws), '']
    L.append('## 6. Paired frame comparisons (comparator -> M arm): rescues = comparator fails & M ok; harms = comparator ok & M fails; exact McNemar; dLogloss = M - comparator\n')
    L += [analyze.tab(['config', 'snr', 'comparator', 'arm', 'n', 'fail cmp', 'fail arm', 'rescues', 'harms', 'McNemar p', 'dLogloss [CI]'],
                      [[r['config'], r['snr'], r['p'], r['q'], r['n'], r['fail_p'], r['fail_q'], r['rescues'], r['harms'], analyze.fp(r['p_mcnemar']),
                        f"{r['dll']:.4f} [{r['dll_lo']:.4f}, {r['dll_hi']:.4f}]"] for r in paired if r['snr'] == 'ALL']), '',
          '(per-SNR rows are in analysis.json `paired`.)\n']
    L.append('## 7. Cost: complete receiver seconds/cell (all SNR cells pooled; same processes, same load)\n')
    L += [analyze.tab(['config', 'arm', 'n cells', 'mean s', 'median s', 'p95 s'],
                      [[r['config'], r['arm'], r['n'], f"{r['mean']:.3f}", f"{r['median']:.3f}", f"{r['p95']:.3f}"] for r in cost]), '']
    L.append('B / PS trigger (CSTATE20) rates are in table `trigger` of analysis.json.\n')
    Lm = '\n'.join(L) + '\n'
    (a.out_dir / 'ANALYSIS.md').write_text(Lm)
    payload = analyze.clean(dict(_argv=sys.argv[1:], _input_md5=md5s, params=dict(B=a.B, B_aux=a.B_aux, seed=a.seed), wall_seconds=time.time() - t0,
                                 n_units=D.U, n_rows=len(rows), n_error_rows=n_err_rows, results_json_mismatch_cells=mism,
                                 results_json_cells_checked=n_cells_checked, snr_grid=snrs, S=S, table1=t1, cross=db['cross'], gap_to_A3=db['to_a3'],
                                 headline_gaps=gaps, arm_diffs=extra, pb16=pbx, cost=cost, cost_pb16_cells=cost_pb, paired=paired, trigger=trig))
    (a.out_dir / 'analysis.json').write_text(json.dumps(payload, indent=1, allow_nan=False) + '\n')
    msg = analyze.plot(D, fer, a.out_dir / 'fer_curves.png')
    print(msg)
    print(f'mismatch cells {mism}/{n_cells_checked}; error rows {n_err_rows}; wrote {a.out_dir}/ANALYSIS.md in {time.time() - t0:.0f}s')
    for k in ('S1', 'S2', 'S3', 'S4'):
        print(k, S[k]['verdict'], [(r['config'], round((r.get('gap') or r.get('adv'))['est'], 3)) for r in S[k]['rows']])


if __name__ == '__main__':
    main()
