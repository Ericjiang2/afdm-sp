#!/usr/bin/env python
"""Transfer table Phi[SNR][L][I_r] of the C1 EXIT-state run (driver_c1e.py).  Reads rows only; no predictions.
    python -B c1e_analyze.py <c1e_dir> <out_dir>
Per (SNR, L, I_r): n frames, mean and percentile bootstrap 95% CI (B = 2000 frame resamples, fixed seed) of
  mi_in1 (= measured I_{r+1}, MI of the round-1 decoder-input LLR), mi_app1, mi_chk1, ia_real, ir_real (realised MI of the injected
  clipped L_A / L_R), dec1 (round-1 decode rate, cerr1 == 0), and the round-2 values mi_in2, mi_app2, mi_chk2, dec2 (cerr2 == 0).
EXIT_none rows (I_r = none, normal pilot-only round 1): same columns plus FER by round (info errors).  Targets IA/IR from T1 are listed.
"""
import glob
import json
from pathlib import Path
import sys

import numpy as np

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
rows = [json.loads(x) for f in sorted(glob.glob(str(src / 'rows_shard*.jsonl'))) for x in open(f) if x.strip()]
ok = [r for r in rows if r['status'] == 'ok']
B = 2000
rng = np.random.default_rng(20261009)
METRICS = ('mi_in1', 'mi_app1', 'mi_chk1', 'ia_real', 'ir_real', 'dec1', 'mi_in2', 'mi_app2', 'mi_chk2', 'dec2', 'fer1', 'fer2')


def val(r, m):
    if m.startswith('dec'):
        return float(r[f'cerr{m[3:]}'] == 0)
    if m.startswith('fer'):
        return float(r[f'ierr{m[3:]}'] > 0)
    v = r.get(m)
    return None if v is None else float(v)


def ci(x, idx):
    m = x[idx].mean(axis=1)
    return dict(mean=float(x.mean()), lo=float(np.percentile(m, 2.5)), hi=float(np.percentile(m, 97.5)))


cells = {}
for r in ok:
    cells.setdefault((r['snr_centi_db'], r['L'], r['Ir']), []).append(r)
phi = {}
for (snr, L, ir), rs in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1], -1. if kv[0][2] is None else kv[0][2])):
    rs = sorted(rs, key=lambda r: r['frame'])
    n = len(rs)
    idx = rng.integers(0, n, size=(B, n))
    e = dict(n=n, frames=[rs[0]['frame'], rs[-1]['frame']])
    for m in METRICS:
        vals = [val(r, m) for r in rs]
        if any(v is None for v in vals):
            continue
        e[m] = ci(np.array(vals), idx)
    if ir is not None:
        e['IA_target'], e['IR_target'] = rs[0]['IA_target'], rs[0]['IR_target']
        e['sigma_A'], e['sigma_C'] = rs[0]['sigma_A'], rs[0]['sigma_C']
    phi.setdefault(f'{snr / 100:g}', {}).setdefault(f'L{L}', {})['none' if ir is None else f'{ir:.2f}'] = e

res = dict(n_rows=len(rows), n_error_rows=len(rows) - len(ok), bootstrap=dict(B=B, seed=20261009, kind='percentile, frame resample'),
           note='mi_in1 = measured I_{r+1}; dec = decode rate of the round-r decision (coded errors == 0); fer = info-error frame rate; '
                'EXIT_none = normal pilot-only round 1', Phi=phi)
(out / 'c1e_phi.json').write_text(json.dumps(res, indent=1) + '\n')


def f(e, m, d=3):
    if m not in e:
        return ''
    a = e[m]
    return f"{a['mean']:.{d}f} [{a['lo']:.{d}f},{a['hi']:.{d}f}]"


md = ['# C1 EXIT transfer table Phi[SNR][L][I_r]  (rho .3, frames 500-599; mean [bootstrap 95% CI])', '',
      f"rows {res['n_rows']} (error rows {res['n_error_rows']}); mi_in1 = measured I_(r+1) = MI of round-1 decoder-input LLR; "
      "dec = fraction of frames whose round-r decision has 0 coded errors; ia/ir = realised MI of injected (clipped) L_A / L_R.", '']
for snr, byL in phi.items():
    md += [f'## SNR {snr} dB', '',
           '| L | I_r | n | IA_t | IR_t | ia_real | ir_real | mi_in1 | mi_app1 | mi_chk1 | dec1 | mi_in2 | mi_app2 | mi_chk2 | dec2 |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for L, byI in byL.items():
        for ir, e in byI.items():
            md.append(f"| {L[1:]} | {ir} | {e['n']} | {e.get('IA_target', float('nan')):.3f} | {e.get('IR_target', float('nan')):.3f} | "
                      f"{f(e, 'ia_real')} | {f(e, 'ir_real')} | {f(e, 'mi_in1')} | {f(e, 'mi_app1')} | {f(e, 'mi_chk1')} | {f(e, 'dec1', 2)} | "
                      f"{f(e, 'mi_in2')} | {f(e, 'mi_app2')} | {f(e, 'mi_chk2')} | {f(e, 'dec2', 2)} |".replace('nan', ''))
    md.append('')
md += ['## EXIT_none (normal pilot-only round 1): mean MI and FER by round', '',
       '| SNR | L | n | mi_in1 | mi_in2 | mi_app1 | mi_app2 | mi_chk1 | mi_chk2 | FER r1 | FER r2 |', '|---|---|---|---|---|---|---|---|---|---|---|']
for snr, byL in phi.items():
    for L, byI in byL.items():
        e = byI.get('none')
        if e:
            md.append(f"| {snr} | {L[1:]} | {e['n']} | {f(e, 'mi_in1')} | {f(e, 'mi_in2')} | {f(e, 'mi_app1')} | {f(e, 'mi_app2')} | "
                      f"{f(e, 'mi_chk1')} | {f(e, 'mi_chk2')} | {f(e, 'fer1', 2)} | {f(e, 'fer2', 2)} |")
(out / 'c1e_phi.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
