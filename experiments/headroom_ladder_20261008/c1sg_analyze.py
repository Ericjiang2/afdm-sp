#!/usr/bin/env python
"""X2 analysis: statistic gap of the refit (research/c1-prelim-positioning.md, FROZEN before the run).  Rows and JSON only.
    python -B c1sg_analyze.py [--dir out/c1sg] [--out out/c1sg/analysis]
Per cell (SNR, rho, L), frames 0-199, percentile frame bootstrap (B = 2000):
  r1   = mean eps_W1 / mean eps_G1                         (round-1 refit: white vs genie GLS)
  bound= (S G(a) + K) / (S + K), G(a) = (1 + a) e^a E1(a), a = sigma2/(1 - rho), S = rho N/(sigma2 + 1 - rho)   (separable LS + flat ridge)
  frac = (r1 - 1)/(bound - 1);  rec1 = (mean W1 - mean A1)/(mean W1 - mean G1) (achievable share of the genie gain);  rW = mean W1/mean Wt1
  r2   = mean eps_W2 / mean eps_G2 over all frames and split by final decode (ierr2 = 0 / > 0)  (round-2 data-aided refit; report-only)
P4: r1 CI lower end > 1 in >= 38/40 cells.   P5: r1 <= 1.05 bound in >= 36/40 cells.
Closures: max w_closure1/2 (W recomputation vs receiver gains), max ht_closure (tap operator), error rows.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.special import exp1

HERE = Path(__file__).resolve().parent
B, SEED, N, FRAMES = 2000, 20261013, 1024, 200
ap = argparse.ArgumentParser()
ap.add_argument('--dir', default='out/c1sg')
ap.add_argument('--out', default='out/c1sg/analysis')
args = ap.parse_args()
P = lambda s: (HERE / s) if not Path(s).is_absolute() else Path(s)


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def bound(snr_db, rho, L):
    s2 = 10 ** (-snr_db / 10)
    a = s2 / (1 - rho)
    G = (1 + a) * np.exp(a) * exp1(a)
    S, K = rho * N / (s2 + 1 - rho), 8 * L
    return float((S * G + K) / (S + K)), float(G)


def pct(x):
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


files = sorted(glob.glob(str(P(args.dir) / 'rows_shard*.jsonl')))
rows = [json.loads(x) for f in files for x in open(f) if x.strip()]
ok = [r for r in rows if r['status'] == 'ok' and r['frame'] < FRAMES]
res = dict(_argv=sys.argv, _config=dict(B=B, seed=SEED, frames=FRAMES, dir=args.dir, md5=dict(script=md5(Path(__file__)), rows={Path(f).name: md5(f) for f in files})),
           n_rows=len(rows), n_error=sum(r['status'] != 'ok' for r in rows),
           closure=dict(w1=max(r['w_closure1'] for r in ok), w2=max(r['w_closure2'] for r in ok), ht=max(r['ht_closure'] for r in ok)))
md = ['# X2: statistic gap of the refit (white vs whitened), frames 0-199', '',
      f"Rows {res['n_rows']} (error {res['n_error']}); closures: max|W - receiver| round 1 {res['closure']['w1']:.1e}, round 2 {res['closure']['w2']:.1e}; "
      f"tap-operator misfit {res['closure']['ht']:.1e}.", '']
cells = {}
for r in ok:
    cells.setdefault((r['snr_centi_db'], r['rho_permille'], r['L']), []).append(r)
rng = np.random.default_rng(SEED)
out, p4, p5 = {}, 0, 0
for snr in sorted({k[0] for k in cells}):
    md += [f'## {snr / 100:g} dB', '',
           '| rho | L | eps_W1 | eps_G1 | r1 [CI] | bound | frac | rec1 (A) | W/Wt | r2 all | r2 dec ok (n) | r2 fail (n) | v_cv2 |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for (s, rho, L) in sorted(k for k in cells if k[0] == snr):
        c = sorted(cells[(s, rho, L)], key=lambda r: r['frame'])
        n = len(c)
        col = {k: np.array([r[k] for r in c]) for k in ('eps_W1', 'eps_Wt1', 'eps_G1', 'eps_A1', 'eps_W2', 'eps_G2', 'eps_proj', 'v_cv2')}
        fail = np.array([r['ierr2'] > 0 for r in c])
        idx = rng.integers(0, n, size=(B, n))
        r1 = col['eps_W1'].mean() / col['eps_G1'].mean()
        lo, hi = pct(col['eps_W1'][idx].mean(1) / col['eps_G1'][idx].mean(1))
        bd, G = bound(s / 100, rho / 1000, L)
        frac = (r1 - 1) / (bd - 1)
        rec = (col['eps_W1'].mean() - col['eps_A1'].mean()) / (col['eps_W1'].mean() - col['eps_G1'].mean())
        rW = col['eps_W1'].mean() / col['eps_Wt1'].mean()
        r2 = col['eps_W2'].mean() / col['eps_G2'].mean()
        r2ok = col['eps_W2'][~fail].mean() / col['eps_G2'][~fail].mean() if (~fail).any() else float('nan')
        r2f = col['eps_W2'][fail].mean() / col['eps_G2'][fail].mean() if fail.any() else float('nan')
        p4 += bool(lo > 1.)
        p5 += bool(r1 <= 1.05 * bd)
        out[f'{s}_{rho}_{L}'] = dict(n=n, eps_W1=float(col['eps_W1'].mean()), eps_G1=float(col['eps_G1'].mean()), eps_A1=float(col['eps_A1'].mean()),
                                     eps_proj=float(col['eps_proj'].mean()), r1=float(r1), r1_ci=[lo, hi], bound=bd, G=G, frac=float(frac), rec1=float(rec),
                                     rW=float(rW), r2=float(r2), r2_dec_ok=float(r2ok), r2_fail=float(r2f), n_fail=int(fail.sum()),
                                     v_cv2=float(col['v_cv2'].mean()))
        md.append(f"| {rho / 1000:g} | {L} | {col['eps_W1'].mean():.4f} | {col['eps_G1'].mean():.4f} | {r1:.3f} [{lo:.3f}, {hi:.3f}] | {bd:.2f} | {frac:.2f} | "
                  f"{rec:.2f} | {rW:.3f} | {r2:.3f} | {r2ok:.3f} ({int((~fail).sum())}) | {r2f:.3f} ({int(fail.sum())}) | {col['v_cv2'].mean():.2f} |")
    md.append('')
n_cells = len(out)
res['cells'] = out
res['P4'] = dict(n_pass=p4, n=n_cells, pass_=bool(n_cells == 40 and p4 >= 38))
res['P5'] = dict(n_pass=p5, n=n_cells, pass_=bool(n_cells == 40 and p5 >= 36))
md = md[:3] + [f"**P4 {'PASS' if res['P4']['pass_'] else 'FAIL'}** ({p4}/{n_cells} cells with r1 CI > 1; rule >= 38/40).  "
               f"**P5 {'PASS' if res['P5']['pass_'] else 'FAIL'}** ({p5}/{n_cells} cells with r1 <= 1.05 bound; rule >= 36/40).", ''] + md[3:]
OUT = P(args.out)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'sg.json').write_text(json.dumps(res, indent=1) + '\n')
(OUT / 'sg.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
