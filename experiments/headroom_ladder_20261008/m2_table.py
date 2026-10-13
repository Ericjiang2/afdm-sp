#!/usr/bin/env python
"""Short M2_TABLE.md from m2_analyze.py's analysis.json (no new statistics).  usage: m2_table.py <analysis.json> <out.md>"""
import json
import math
import sys

a = json.load(open(sys.argv[1]))
S = a['S']
DISP = {'A0': 'B'}


def fc(d, nd=2):
    if d is None or d.get('est') is None or not math.isfinite(d['est']):
        return (d or {}).get('note') or 'undefined'
    return f"{d['est']:.{nd}f} [{d['lo']:.{nd}f}, {d['hi']:.{nd}f}]" + ('*' if d.get('valid', 1) < .95 else '')


L = [f"# M2 test table (expected-power law; B={a['params']['B']} paired bootstrap over frames; frames 0..999 x SNR 6..11 dB x 5 configs)\n",
     f"rows {a['n_rows']}, error rows {a['n_error_rows']}, results.json cross-check mismatching cells {a['results_json_mismatch_cells']}/{a['results_json_cells_checked']}.\n",
     '## Pre-registered S1-S4 (FER target 1e-1; point estimate decides, CI in brackets)\n',
     '| id | rule | config | value (dB) [95% CI] | point | strict (CI) | verdict |', '|---|---|---|---|---|---|---|']
for k in ('S1', 'S2', 'S3', 'S4'):
    s = S[k]
    for r in s['rows']:
        g = r.get('gap') or r.get('adv')
        pt = r.get('pass_point', r.get('pass_db'))
        st = r.get('pass_strict', r.get('pass_db_strict'))
        extra = f"; s/cell M_adapt {r['sec_M_adapt']:.3f} vs PS {r['sec_PS']:.3f}" if k == 'S3' else ''
        L.append(f"| {k} | {s['rule']} | {r['config']} | {fc(g)}{extra} | {'PASS' if pt else 'FAIL'} | {'yes' if st else 'no'} | {s['verdict'] if r is s['rows'][-1] else ''} |")
L.append('')
L.append('## Gap to A3 at FER 1e-1 (dB, x(arm)-x(A3), CI); bound when the arm never reaches 1e-1 by 11 dB\n')
L += ['| config | B | PS | M_full | M_adapt | PB16 (7/9/11 grid, own crossing) |', '|---|---|---|---|---|---|']
for g in [x for x in a['headline_gaps'] if x['target'] == 0.1]:
    L.append(f"| {g['config']} | " + ' | '.join(fc(g.get(k)) if g.get(k) else '-' for k in ('A0', 'PS', 'M_full', 'M_adapt', 'PB16')) + ' |')
L.append('')
L.append('## Gap to A3 at FER 1e-2 (only where defined; most arms do not reach 1e-2 by 11 dB, bounds given)\n')
L += ['| config | B | PS | M_full | M_adapt |', '|---|---|---|---|---|']
for g in [x for x in a['headline_gaps'] if x['target'] == 0.01]:
    L.append(f"| {g['config']} | " + ' | '.join(fc(g.get(k)) if g.get(k) else '-' for k in ('A0', 'PS', 'M_full', 'M_adapt')) + ' |')
L.append('')
L.append('## FER at 7 / 9 / 11 dB (errors per 1000 frames)\n')
t = a['table1']
L += ['| config | SNR | B | PS | M_full | M_adapt | A3 | PB16 |', '|---|---|---|---|---|---|---|---|']
for cfg in ('D1', 'N4a', 'N4b', 'J4', 'J8'):
    for snr in (7.0, 9.0, 11.0):
        cells = []
        for arm in ('A0', 'PS', 'M_full', 'M_adapt', 'A3', 'PB16'):
            r = [x for x in t if x['config'] == cfg and x['snr'] == snr and x['arm'] == arm]
            cells.append(f"{r[0]['frame_err']} ({r[0]['fer']:.3f})" if r else '-')
        L.append(f'| {cfg} | {snr:g} | ' + ' | '.join(cells) + ' |')
L.append('')
L.append('## Paired M_adapt vs comparator, all SNR cells pooled (rescues = comparator fails & M_adapt ok; harms = reverse; exact McNemar)\n')
L += ['| config | comparator | rescues | harms | McNemar p | dLogloss (M_adapt - cmp) [CI] |', '|---|---|---|---|---|---|']
for r in a['paired']:
    if r['snr'] == 'ALL' and r['q'] == 'M_adapt' and r['p'] in ('B', 'PS', 'M_full', 'PB16'):
        L.append(f"| {r['config']} | {r['p']} | {r['rescues']} | {r['harms']} | {r['p_mcnemar']:.2e} | {r['dll']:.4f} [{r['dll_lo']:.4f}, {r['dll_hi']:.4f}] |")
L.append('')
L.append('## Cost: complete receiver seconds/cell (mean / p95), all SNR cells pooled, shared load (80+20 single-thread shards)\n')
L += ['| config | B | PS | M_full | M_adapt | A3 | PB16 |', '|---|---|---|---|---|---|---|']
for cfg in ('D1', 'N4a', 'N4b', 'J4', 'J8'):
    cells = []
    for arm in ('B', 'PS', 'M_full', 'M_adapt', 'A3', 'PB16'):
        r = [x for x in a['cost'] if x['config'] == cfg and x['arm'] == arm]
        cells.append(f"{r[0]['mean']:.3f} / {r[0]['p95']:.3f}" if r else '-')
    L.append(f'| {cfg} | ' + ' | '.join(cells) + ' |')
L.append('')
L.append('## PB16 (cap 16, no stopping rule) like-for-like on the 3-point grid {7, 9, 11} dB, gap to A3 at 1e-1\n')
L += ['| config | B | PS | M_full | M_adapt | PB16 | PB16 - PS | PB16 - M_adapt |', '|---|---|---|---|---|---|---|---|']
for e in [x for x in a['pb16'] if x['target'] == 0.1]:
    L.append(f"| {e['config']} | " + ' | '.join(fc(e[k]) for k in ('A0_minus_A3', 'PS_minus_A3', 'M_full_minus_A3', 'M_adapt_minus_A3', 'PB16_minus_A3', 'PB16_minus_PS', 'PB16_minus_Madapt')) + ' |')
open(sys.argv[2], 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
