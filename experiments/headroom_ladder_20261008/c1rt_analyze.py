#!/usr/bin/env python
"""X1 analysis: pilot fraction x inner-update budget coupling (research/c1-prelim-positioning.md, FROZEN before the run).  Rows and JSON only.
    python -B c1rt_analyze.py [--rep-dir out/c1ib2_rep] [--rt-dir out/c1rt] [--out out/c1rt/analysis]
Rows: arms R4T20 / R4T40, frames 0-199; 8 dB rho .2/.3/.5 and 6.5 dB rho .2 from the IB2 REP run, 8 dB rho .1/.15 and 6.5 dB rho .1/.3/.5 from the X1
run (same generator, entropy and frames => paired across rho, T and L).

Kc_R(rho, T) = first FER_R = .5 crossing linear in K = 8 L (c1e_predict.k_cross; censored at the range ends and flagged), FER_R = frac(ierr_R > 0).
Percentile frame bootstrap (B = 2000) with frames resampled jointly across rho, T and L inside one SNR, so every ratio CI is paired.
    g_R(rho) = Kc_R(rho, 40) / Kc_R(rho, 20)
P1 (primary): g_R(.1) / g_R(.3) > 1 with paired CI lower end > 1, at R1 and R2, SNR 6.5 and 8 dB (4 tests; pass if >= 3/4).
P2: argmax_rho Kc_R(rho, 40) <= argmax_rho Kc_R(rho, 20) (point) at R1-R4 for both SNRs; bootstrap frequency of the inequality reported.
P3 (report-only): monotonicity of g_R in rho; Kc_R1(rho) shape.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

import c1e_predict as E

HERE = Path(__file__).resolve().parent
B, SEED, FRAMES, RMAX = 2000, 20261012, 200, 4
TS = (20, 40)
GRID = {650: (0.1, 0.2, 0.3, 0.5), 800: (0.1, 0.15, 0.2, 0.3, 0.5)}
P1_PAIRS = [(650, 1), (650, 2), (800, 1), (800, 2)]

ap = argparse.ArgumentParser()
ap.add_argument('--rep-dir', default='out/c1ib2_rep')
ap.add_argument('--rt-dir', default='out/c1rt')
ap.add_argument('--c1i-dir', default='out/c1i')
ap.add_argument('--out', default='out/c1rt/analysis')
args = ap.parse_args()
P = lambda s: (HERE / s) if not Path(s).is_absolute() else Path(s)
OUT = P(args.out)


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def load(d):
    rows = []
    for f in sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl'))):
        with open(f) as fh:
            rows += [json.loads(x) for x in fh if x.strip()]
    return rows


def pct(x):
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def kc_cens(Ks, ys):
    k = E.k_cross(Ks, list(ys), 0.5)
    if k is not None:
        return k, 0
    if all(y < 0.5 for y in ys):
        return float(Ks[-1]), 1
    if all(y >= 0.5 for y in ys):
        return float(Ks[0]), 2
    raise ValueError('no crossing but mixed FER')


CODE = {0: 'exact', 1: 'above_range', 2: 'below_range'}
rows = load(args.rep_dir) + load(args.rt_dir)
res = dict(_argv=sys.argv, _config=dict(B=B, seed=SEED, frames=FRAMES, grid={k: list(v) for k, v in GRID.items()}, p1_pairs=P1_PAIRS,
                                         dirs=vars(args), md5=dict(script=md5(Path(__file__)), c1e_predict=md5(HERE / 'c1e_predict.py'),
                                                                   rows={d: {Path(f).name: md5(f) for f in sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl')))}
                                                                         for d in (args.rep_dir, args.rt_dir)})),
           n_rows=len(rows), n_error=sum(r['status'] != 'ok' for r in rows))
md = ['# X1: pilot fraction x inner-update budget (R4, T 20 vs 40, frames 0-199)', '',
      f"Rows read {res['n_rows']} (error {res['n_error']}).", '']

# ----------------------------------------------------------------- tables {(snr, rho, T): {L: (frames, RMAX)}}
tab, seeds = {}, {}
for r in rows:
    if r['status'] != 'ok' or r['frame'] >= FRAMES or r['arm'] not in ('R4T20', 'R4T40'):
        continue
    snr, rho, T = r['snr_centi_db'], r['rho_permille'] / 1000, int(r['arm'][3:])
    if snr not in GRID or rho not in GRID[snr]:
        continue
    key = (snr, rho, T)
    cell = tab.setdefault(key, {}).setdefault(r['L'], {})
    if r['frame'] in cell:
        raise ValueError(f'duplicate row {key} L{r["L"]} frame {r["frame"]}')
    cell[r['frame']] = [float(r[f'ierr{q}'] > 0) for q in range(1, RMAX + 1)]
    fp = (r['channel_seed'], r['info_sha256'], r['noise_sha256'])
    if seeds.setdefault((r['L'], r['frame']), fp) != fp:
        raise AssertionError(f'pairing broken at L{r["L"]} frame {r["frame"]}')

sections = {}
for snr, rhos in GRID.items():
    keys = [(snr, rho, T) for rho in rhos for T in TS]
    missing = [k for k in keys if k not in tab]
    if missing:
        md += [f'## {snr / 100:g} dB: missing cells {missing}; skipped', '']
        continue
    frames = sorted(set.intersection(*[set(f) for k in keys for f in tab[k].values()]))
    if len(frames) != FRAMES:
        raise ValueError(f'{snr}: {len(frames)} common frames, expected {FRAMES}')
    Ls = {rho: sorted(set(tab[(snr, rho, 20)]) & set(tab[(snr, rho, 40)])) for rho in rhos}
    arr = {k: {L: np.array([tab[k][L][f] for f in frames]) for L in Ls[k[1]]} for k in keys}
    idx = np.random.default_rng(SEED + snr).integers(0, FRAMES, size=(B, FRAMES))
    est = {}
    for (s, rho, T) in keys:
        Ks = [8 * L for L in Ls[rho]]
        for R in range(1, RMAX + 1):
            fer = [float(arr[(s, rho, T)][L][:, R - 1].mean()) for L in Ls[rho]]
            point, code = kc_cens(Ks, fer)
            M = np.stack([arr[(s, rho, T)][L][idx, R - 1].mean(axis=1) for L in Ls[rho]], axis=1)
            bk, bc = np.empty(B), np.empty(B, int)
            for b in range(B):
                bk[b], bc[b] = kc_cens(Ks, M[b])
            est[(rho, T, R)] = dict(point=point, code=code, boot=bk, bcode=bc, fer=fer)

    def ratio(a, b):
        rb = a['boot'] / b['boot']
        lo, hi = pct(rb)
        return dict(ratio=a['point'] / b['point'], lo=lo, hi=hi, censored=bool(a['code'] or b['code']),
                    n_boot_censored=int(np.sum((a['bcode'] != 0) | (b['bcode'] != 0))))

    sec = dict(n_frames=len(frames), Ls={str(k): v for k, v in Ls.items()}, kc={}, g={}, p1={}, p2={})
    md += [f'## {snr / 100:g} dB', '', '| rho | R | Kc T20 [CI] | Kc T40 [CI] | g = T40/T20 [paired CI] | status |', '|---|---|---|---|---|---|']
    g = {}
    for rho in rhos:
        for R in range(1, RMAX + 1):
            a20, a40 = est[(rho, 20, R)], est[(rho, 40, R)]
            g[(rho, R)] = dict(boot=a40['boot'] / a20['boot'], point=a40['point'] / a20['point'], cens=bool(a20['code'] or a40['code']))
            rt = ratio(a40, a20)
            sec['kc'][f'rho{rho}_R{R}'] = {f'T{T}': dict(point=est[(rho, T, R)]['point'], ci=pct(est[(rho, T, R)]['boot']),
                                                          status=CODE[est[(rho, T, R)]['code']], fer=est[(rho, T, R)]['fer']) for T in TS}
            sec['g'][f'rho{rho}_R{R}'] = rt
            md.append(f"| {rho:g} | {R} | {a20['point']:.1f} [{pct(a20['boot'])[0]:.1f}, {pct(a20['boot'])[1]:.1f}] | "
                      f"{a40['point']:.1f} [{pct(a40['boot'])[0]:.1f}, {pct(a40['boot'])[1]:.1f}] | {rt['ratio']:.3f} [{rt['lo']:.3f}, {rt['hi']:.3f}] | "
                      f"{CODE[a20['code']]}/{CODE[a40['code']]} |")
    md += ['']
    # P1
    md += ['P1  g_R(.1) / g_R(.3) (paired):', '']
    for R in (1, 2):
        rr = g[(0.1, R)]['boot'] / g[(0.3, R)]['boot']
        lo, hi = pct(rr)
        point = g[(0.1, R)]['point'] / g[(0.3, R)]['point']
        ok = bool(lo > 1.)
        sec['p1'][f'R{R}'] = dict(point=point, lo=lo, hi=hi, pass_=ok, censored=bool(g[(0.1, R)]['cens'] or g[(0.3, R)]['cens']))
        md.append(f"- R{R}: {point:.3f} [{lo:.3f}, {hi:.3f}] -> {'PASS' if ok else 'fail'}" + (' (censored)' if sec['p1'][f'R{R}']['censored'] else ''))
    # P2
    md += ['', 'P2  argmax_rho Kc_R (point; bootstrap frequency of argmax(T40) <= argmax(T20)):', '']
    for R in range(1, RMAX + 1):
        am = {T: rhos[int(np.argmax([est[(rho, T, R)]['point'] for rho in rhos]))] for T in TS}
        bam = {T: np.array(rhos)[np.argmax(np.stack([est[(rho, T, R)]['boot'] for rho in rhos], axis=1), axis=1)] for T in TS}
        freq = float(np.mean(bam[40] <= bam[20]))
        sec['p2'][f'R{R}'] = dict(argmax_T20=am[20], argmax_T40=am[40], holds=bool(am[40] <= am[20]), boot_freq=freq)
        md.append(f"- R{R}: rho*(T20) = {am[20]:g}, rho*(T40) = {am[40]:g} -> {'holds' if am[40] <= am[20] else 'violated'}; bootstrap freq {freq:.2f}")
    # P3 monotonicity of g in rho
    md += ['', 'P3  g_R by rho (report): ' + '; '.join(f"R{R}: " + ' '.join(f"{g[(rho, R)]['point']:.3f}" for rho in rhos) for R in range(1, RMAX + 1)), '']
    sec['p3'] = {f'R{R}': [g[(rho, R)]['point'] for rho in rhos] for R in range(1, RMAX + 1)}
    sections[snr] = sec

# closure: new 6.5 dB rho .3 R4T20 rows vs the stored c1i FULL_R4 rows (same observations, same receiver)
c1i_rows = {(r['L'], r['frame']): r for r in load(args.c1i_dir)
            if r['status'] == 'ok' and r['arm'] == 'FULL_R4' and r['snr_centi_db'] == 650 and r['rho_permille'] == 300}
new = {(r['L'], r['frame']): r for r in load(args.rt_dir)
       if r['status'] == 'ok' and r['arm'] == 'R4T20' and r['snr_centi_db'] == 650 and r['rho_permille'] == 300}
both = sorted(set(c1i_rows) & set(new))
fields = [f'{k}{q}' for k in ('cerr', 'ierr', 'dsha') for q in range(1, RMAX + 1)]
mism = sum(any(c1i_rows[k][f] != new[k][f] for f in fields) for k in both)
res['closure_c1i'] = dict(pairs=len(both), mismatches=int(mism))
md += [f'Closure: 6.5 dB rho .3 R4T20 vs stored c1i FULL_R4: {len(both)} (L, frame) pairs, {mism} with any cerr/ierr/dsha difference (rounds 1-4).', '']

p1 = [sections[s]['p1'][f'R{R}']['pass_'] for (s, R) in P1_PAIRS if s in sections]
res['sections'] = {str(k): v for k, v in sections.items()}
res['P1'] = dict(n_pass=int(sum(p1)), n=len(p1), pass_=bool(len(p1) == 4 and sum(p1) >= 3))
res['P2'] = {str(s): {R: sections[s]['p2'][R]['holds'] for R in sections[s]['p2']} for s in sections}
md = md[:2] + [f"**P1 {'PASS' if res['P1']['pass_'] else 'FAIL'}** ({res['P1']['n_pass']}/{res['P1']['n']} tests, rule >= 3/4).  "
               f"P2 holds: {res['P2']}", ''] + md[2:]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'rt.json').write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else float(o)) + '\n')
(OUT / 'rt.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
