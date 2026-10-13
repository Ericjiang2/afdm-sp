#!/usr/bin/env python
"""Analysis of the C1 paired-intervention run (driver_c1i.py; arms FULL_R4, FROZEN, WARM_1.0).  Reads rows only.
    python -B c1i_analyze.py <c1i_dir> <c1_map_dir> <out_dir>
Per (L, arm): FER after each round r (info-error frames; also coded-error frames and syndrome-weight>0 frames of the round-r decision),
median eps_ce_r / eps_det_r.  Exact two-sided McNemar tests on the paired info-error indicators (same frame, same observation):
FULL_R4 R2 vs R4, WARM_1.0 vs FULL_R4 (R1, R2, R4), FROZEN vs FULL_R4 (R2).  Closure check: FULL_R4 rounds 1-2 vs the stored c1_map
SPg_flat rows (same L, frame, rho .3, 6.5 dB).  Truth-informed WARM_1.0 is a mechanism probe, never a receiver result.
"""
import glob
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import binomtest

c1i, cmap, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
rows = [json.loads(x) for f in sorted(glob.glob(str(c1i / 'rows_shard*.jsonl'))) for x in open(f) if x.strip()]
ok = [r for r in rows if r['status'] == 'ok']
Ls = sorted({r['L'] for r in rows})
arms = [a for a in ('FULL_R4', 'WARM_1.0', 'FROZEN') if any(r['arm'] == a for r in rows)]
cell = {(r['L'], r['frame'], r['arm']): r for r in ok}
frames_of = {L: sorted({f for (l, f, a) in cell if l == L}) for L in Ls}
R_OF = {'FULL_R4': 4, 'WARM_1.0': 4, 'FROZEN': 2}
res = dict(n_rows=len(rows), n_error_rows=len(rows) - len(ok), Ls=Ls, arms=arms)


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(c - h), float(c + h))


# ------------------------------------------------------------------ per (L, arm, round) table
table = {}
for L in Ls:
    for arm in arms:
        rs = [cell[(L, f, arm)] for f in frames_of[L] if (L, f, arm) in cell]
        if not rs:
            continue
        for r in range(1, R_OF[arm] + 1):
            ie = np.array([x[f'ierr{r}'] > 0 for x in rs])
            ce = np.array([x[f'cerr{r}'] > 0 for x in rs])
            sy = np.array([x[f'syn{r}'] > 0 for x in rs])
            table[f'L{L}|{arm}|r{r}'] = dict(
                L=L, arm=arm, r=r, n=len(rs), fer_info=float(ie.mean()), fer_info_ci=wilson(int(ie.sum()), len(rs)),
                fer_coded=float(ce.mean()), fer_syn=float(sy.mean()),
                eps_ce_med=float(np.median([x[f'eps_ce{r}'] for x in rs])), eps_det_med=float(np.median([x[f'eps_det{r}'] for x in rs])),
                mean_cerr=float(np.mean([x[f'cerr{r}'] for x in rs])))
res['table'] = table

# ------------------------------------------------------------------------------------------- McNemar
def mcnemar(A, rA, B, rB, L):
    fr = [f for f in frames_of[L] if (L, f, A) in cell and (L, f, B) in cell]
    a = np.array([cell[(L, f, A)][f'ierr{rA}'] > 0 for f in fr])
    b = np.array([cell[(L, f, B)][f'ierr{rB}'] > 0 for f in fr])
    n01 = int(np.sum(a & ~b))   # A fails, B succeeds
    n10 = int(np.sum(~a & b))   # A succeeds, B fails
    p = 1.0 if n01 + n10 == 0 else float(binomtest(min(n01, n10), n01 + n10, .5).pvalue)
    return dict(n=len(fr), fer_A=float(a.mean()), fer_B=float(b.mean()), A_fail_B_ok=n01, A_ok_B_fail=n10, p_exact=p,
                diff_B_minus_A=float(b.mean() - a.mean()))


tests = [('FULL_R4 R2 vs FULL_R4 R4', 'FULL_R4', 2, 'FULL_R4', 4)]
tests += [(f'FULL_R4 R{r} vs WARM_1.0 R{r}', 'FULL_R4', r, 'WARM_1.0', r) for r in (1, 2, 4)]
tests += [('FULL_R4 R2 vs FROZEN R2', 'FULL_R4', 2, 'FROZEN', 2)]
res['mcnemar'] = {}
for name, A, rA, B, rB in tests:
    if A in arms and B in arms:
        res['mcnemar'][name] = {f'L{L}': mcnemar(A, rA, B, rB, L) for L in Ls}

# --------------------------------------------------------------------- closure vs stored c1_map rows (FULL_R4 rounds 1-2)
stored = {}
for f in sorted(glob.glob(str(cmap / 'rows_shard*.jsonl'))):
    for x in open(f):
        r = json.loads(x)
        if r['arm'] == 'SPg_flat' and r['snr_centi_db'] == 650 and r['L'] in Ls and r['status'] == 'ok':
            stored[(r['L'], r['frame'])] = r
eps_d, cnt_d, miss, n_cmp = [], [], 0, 0
for (L, f, arm), r in cell.items():
    if arm != 'FULL_R4':
        continue
    st = stored.get((L, f))
    if st is None:
        miss += 1
        continue
    n_cmp += 1
    eps_d.append(max(abs(r[k] - st[k]) for k in ('eps_ce1', 'eps_det1', 'eps_ce2', 'eps_det2')))
    cnt_d.append(max(abs(r['cerr1'] - st['r1_cerr']), abs(r['syn1'] - st['r1_syn']), abs(r['ierr2'] - st['info_errors']),
                     abs(r['cerr2'] - st['coded_errors']), abs(r['syn2'] - st['syndrome'])))
res['closure_vs_c1_map'] = dict(n_compared=n_cmp, n_missing_in_c1_map=miss, max_abs_eps_diff=max(eps_d) if eps_d else None,
                                max_abs_count_diff=max(cnt_d) if cnt_d else None,
                                n_pairs_with_any_diff=int(sum(1 for a, b in zip(eps_d, cnt_d) if a > 1e-10 or b > 0)))
# FROZEN invariants and WARM_1.0 injection
fz = [r for r in ok if r['arm'] == 'FROZEN']
w1 = [r for r in ok if r['arm'] == 'WARM_1.0']
res['invariants'] = dict(
    frozen_max_gain_drift=max((r['frozen_gain_drift'] for r in fz), default=None),
    frozen_eps_ce2_eq_ce1=all(r['eps_ce2'] == r['eps_ce1'] for r in fz),
    warm_eps_init_eq_proj=all(r['eps_init'] == r['eps_proj'] for r in w1),
    max_warm_eps_init=max((r['eps_init'] for r in w1), default=None))

(out / 'c1i_analysis.json').write_text(json.dumps(res, indent=1) + '\n')

# ------------------------------------------------------------------------------------------------ markdown
md = ['# C1 paired intervention (6.5 dB, rho .3): FER by round (info-error frames), paired on the same observation', '']
md.append(f"rows {res['n_rows']} (error rows {res['n_error_rows']}); frames per L: {', '.join(f'L{L}: {len(frames_of[L])}' for L in Ls)}")
md += ['', '| L | arm | R1 | R2 | R3 | R4 | eps_ce1 | eps_det1 | eps_ce2 | eps_det2 | eps_ce4 | eps_det4 |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
for L in Ls:
    for arm in arms:
        g = lambda r, k: table.get(f'L{L}|{arm}|r{r}', {}).get(k)  # noqa: E731
        fm = lambda v: '' if v is None else f'{v:.3f}'  # noqa: E731
        md.append(f'| {L} | {arm} | ' + ' | '.join(fm(g(r, 'fer_info')) for r in (1, 2, 3, 4)) + ' | ' +
                  ' | '.join(fm(g(r, k)) for r, k in ((1, 'eps_ce_med'), (1, 'eps_det_med'), (2, 'eps_ce_med'), (2, 'eps_det_med'),
                                                       (4, 'eps_ce_med'), (4, 'eps_det_med'))) + ' |')
md += ['', 'Coded-error frame fraction (cerr>0) / syndrome>0 fraction of the round-r decision:', '',
       '| L | arm | r | fer_info | fer_coded | fer_syn | mean cerr |', '|---|---|---|---|---|---|---|']
for L in Ls:
    for arm in arms:
        for r in range(1, R_OF[arm] + 1):
            t = table.get(f'L{L}|{arm}|r{r}')
            if t:
                md.append(f"| {L} | {arm} | {r} | {t['fer_info']:.3f} | {t['fer_coded']:.3f} | {t['fer_syn']:.3f} | {t['mean_cerr']:.1f} |")
md += ['', '## Paired exact McNemar (A_fail_B_ok = frames A fails and B succeeds)', '',
       '| test | L | n | FER A | FER B | A fail/B ok | A ok/B fail | p |', '|---|---|---|---|---|---|---|---|']
for name, d in res['mcnemar'].items():
    for lk, v in d.items():
        md.append(f"| {name} | {lk[1:]} | {v['n']} | {v['fer_A']:.3f} | {v['fer_B']:.3f} | {v['A_fail_B_ok']} | {v['A_ok_B_fail']} | {v['p_exact']:.3g} |")
c = res['closure_vs_c1_map']
md += ['', f"## FULL_R4 rounds 1-2 vs stored c1_map SPg_flat rows", '', f"compared {c['n_compared']} (missing {c['n_missing_in_c1_map']}); "
       f"max |eps diff| = {c['max_abs_eps_diff']}; max |count diff| = {c['max_abs_count_diff']}; pairs with any diff = {c['n_pairs_with_any_diff']}",
       '', f"invariants: {json.dumps(res['invariants'])}"]
(out / 'c1i_analysis.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
