#!/usr/bin/env python
"""Compare FROZEN T2 predictions (out/c1_t2/predictions.json, commit 1dfb182c) with observed SP outcomes (out/c1_t0)."""
import json
from pathlib import Path
import sys
import numpy as np
from c1_t2_predict import crossing

HERE = Path(__file__).resolve().parent
pred = json.loads((HERE / 'out/c1_t2/predictions.json').read_text())
t0 = json.loads((HERE / 'out/c1_t0/t0_screen.json').read_text())
obs = {}
for name, ds in t0['datasets'].items():
    for c in ds['cells']:
        if c['arm'] == 'SPg_flat':
            q = c['quantiles']
            obs[(name, float(c['snr_db']), float(c['rho']), int(c['L']))] = dict(
                fer_r1=c['outcomes']['fer_r1'], fer=c['outcomes']['fer_final'],
                det1=q['eps_det1']['overall']['50'], ce2_fail=q['eps_ce2']['r1_fail'].get('50'),
                ce2_ok=q['eps_ce2']['r1_correct'].get('50'))
lines = ['# C1 T2 frozen predictions vs observed (SPg_flat)', '',
         '| ds | SNR | rho | L | K | e_det1 obs / A | FER_r1 obs / A / B | FER R2 obs / A / B | e_ce2|r1fail obs / A / B |', '|---|' * 9]
groups = {}
f = lambda x, d=3: '-' if x is None else f'{x:.{d}f}'
for r in sorted(pred['cells'], key=lambda r: (r['dataset'], r['snr_db'], r['rho'], r['L'])):
    o = obs[(r['dataset'], r['snr_db'], r['rho'], r['L'])]
    a, b = r['A'], r['B']
    lines.append(f"| {r['dataset'][3:]} | {r['snr_db']:g} | {r['rho']:g} | {r['L']} | {r['K']} | {f(o['det1'],4)} / {f(a['e_det1'],4)} | "
                 f"{f(o['fer_r1'])} / {f(a['fer_r1'])} / {f(b['fer_r1'])} | {f(o['fer'])} / {f(a['p_fail_R2'])} / {f(b['p_fail_R2'])} | "
                 f"{f(o['ce2_fail'],4)} / {f(a['eps_ce2_given_r1_fail'],4)} / {f(b['eps_ce2_given_r1_fail'],4)} |")
    groups.setdefault((r['dataset'], r['snr_db'], r['rho']), []).append((r['K'], o, a, b, r))
lines += ['', '## Cliff (FER .5 crossing over K) and inner-stage ratio', '',
          '| ds | SNR | rho | Kc obs R2 | Kc A | Kc B | Kc_r1 obs | Kc_r1 A | median e_det1 obs/A |', '|---|' * 9]
for (ds, snr, rho), v in sorted(groups.items()):
    v.sort(key=lambda t: t[0]); Ks = [t[0] for t in v]
    c = lambda ys: crossing(Ks, ys)
    ratio = np.median([t[1]['det1'] / t[2]['e_det1'] for t in v])
    lines.append(f"| {ds[3:]} | {snr:g} | {rho:g} | {f(c([t[1]['fer'] for t in v]),0)} | {f(c([t[2]['p_fail_R2'] for t in v]),0)} | "
                 f"{f(c([t[3]['p_fail_R2'] for t in v]),0)} | {f(c([t[1]['fer_r1'] for t in v]),0)} | {f(c([t[2]['fer_r1'] for t in v]),0)} | {ratio:.2f} |")
out = HERE / 'out/c1_t2/COMPARE.md'
out.write_text('\n'.join(lines) + '\n')
print('\n'.join(lines[-12:]))
