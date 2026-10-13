#!/usr/bin/env python
"""F1 supplementary diagnostics (descriptive only; not part of the pre-registered analysis).

For each config and SNR: realized channel energy per dimension (cl_energy_per_dim; the generator normalises
sum|g|^2 = 1, NOT ||H||_F^2/N = 1), A3 / B failure split by energy outage (energy < 0.5, i.e. effective SNR
-3 dB or worse), and paired conditionals P(B fail | A3 ok), P(A3 fail | B ok).
usage: extra_diag.py <run_dir> <out_prefix>
"""
import glob
import json
import math
import sys

import numpy as np

run, prefix = sys.argv[1], sys.argv[2]
rows = {}
for f in sorted(glob.glob(run + '/rows_shard*.jsonl')):
    for line in open(f):
        r = json.loads(line)
        if r['status'] != 'ok' or r['arm'] not in ('A0', 'A3'):
            continue
        rows.setdefault((r['config'], r['snr_centi_db'], r['frame']), {})[r['arm']] = (r['info_errors'] > 0, r['cl_energy_per_dim'])
configs = ['D1', 'N4a', 'N4b', 'J4', 'N8a', 'N8b', 'J8']
snrs = sorted({k[1] for k in rows})
out = {}
for cfg in configs:
    out[cfg] = {}
    en = np.array([v['A0'][1] for k, v in rows.items() if k[0] == cfg and k[1] == snrs[0]])
    out[cfg]['energy'] = dict(mean=float(en.mean()), p1=float(np.percentile(en, 1)), p5=float(np.percentile(en, 5)),
                              p50=float(np.percentile(en, 50)), frac_lt_0p5=float((en < .5).mean()),
                              frac_lt_0p25=float((en < .25).mean()))
    for snr in snrs:
        ks = [k for k in rows if k[0] == cfg and k[1] == snr]
        b = np.array([rows[k]['A0'][0] for k in ks])
        a = np.array([rows[k]['A3'][0] for k in ks])
        e = np.array([rows[k]['A0'][1] for k in ks])
        lo = e < .5
        out[cfg][snr / 100] = dict(
            n=len(ks), B_fer=float(b.mean()), A3_fer=float(a.mean()),
            A3_fer_energy_lt_0p5=float(a[lo].mean()) if lo.any() else math.nan, n_lt_0p5=int(lo.sum()),
            A3_fer_energy_ge_0p5=float(a[~lo].mean()), B_fer_energy_ge_0p5=float(b[~lo].mean()),
            B_fail_given_A3_ok=float(b[~a].mean()) if (~a).any() else math.nan, n_A3_ok=int((~a).sum()),
            A3_fail_given_B_ok=float(a[~b].mean()) if (~b).any() else math.nan, n_B_ok=int((~b).sum()))
json.dump(out, open(prefix + '.json', 'w'), indent=1, allow_nan=True)  # NaN only where a conditional is undefined
f = lambda x: '-' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{x:.3f}'  # noqa: E731
L = ['# F1 supplementary diagnostics (descriptive)\n', 'Energy = realized ||H||_F^2/N (generator normalises sum|g|^2=1 over rays; D1 is exactly 1).\n',
     '| config | mean | p1 | p5 | p50 | frac<0.5 | frac<0.25 |', '|---|---|---|---|---|---|---|']
for c in configs:
    e = out[c]['energy']
    L.append(f"| {c} | {f(e['mean'])} | {f(e['p1'])} | {f(e['p5'])} | {f(e['p50'])} | {f(e['frac_lt_0p5'])} | {f(e['frac_lt_0p25'])} |")
for snr in (7.0, 8.0, 9.0):
    L += ['', f'## SNR {snr} dB', '', '| config | B FER | A3 FER | A3 FER (E<0.5) [n] | A3 FER (E>=0.5) | B FER (E>=0.5) | P(B fail|A3 ok) | P(A3 fail|B ok) |',
          '|---|---|---|---|---|---|---|---|']
    for c in configs:
        d = out[c][snr]
        L.append(f"| {c} | {f(d['B_fer'])} | {f(d['A3_fer'])} | {f(d['A3_fer_energy_lt_0p5'])} [{d['n_lt_0p5']}] | {f(d['A3_fer_energy_ge_0p5'])} | "
                 f"{f(d['B_fer_energy_ge_0p5'])} | {f(d['B_fail_given_A3_ok'])} | {f(d['A3_fail_given_B_ok'])} |")
open(prefix + '.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
