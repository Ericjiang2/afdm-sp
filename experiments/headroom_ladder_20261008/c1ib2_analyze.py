#!/usr/bin/env python
"""Analysis of the second inner-update-budget batch (IB2; research/c1-inner-budget.md section "IB2", FROZEN).  Reads rows and JSON only.
    python -B c1ib2_analyze.py [--rep-dir out/c1ib2_rep] [--sweep-dir out/c1ib2_sweep] [--r10-dir out/c1ib2_r10] [--det-dir out/c1ib2_det]
        [--time-dir out/c1ib2_time] [--ib-dir out/c1ib] [--c1i-dir out/c1i] [--f10-dir out/c1f_r10] [--g10-dir out/c1g_r10lo]
        [--boot-dir out/c1_boot] [--map-dir out/c1_map] [--out out/c1ib2/analysis]
Outputs <out>/ib2.json (with _argv, _config incl. md5s) and <out>/ib2.md.  A section whose input rows are absent is skipped and said so.

Kc method (as IB-3 / c1f_analyze): Kc_R(T) = first FER_R = .5 crossing, linear in K = 8 L (c1e_predict.k_cross), FER_R = frac(ierr_R > 0), percentile frame bootstrap
(B = 2000), frames resampled jointly across L and T inside one condition, so every ratio CI is paired.  A crossing outside the L range is censored at the nearest
K of the range and flagged (bound).  "Moves" = ratio - 1 >= .05 and CI lower end > 1.

IB2-0   (a) REP R4T20 rows vs the stored c1_boot SPg_flat rows (8 dB, rho .2 / .3 / .5, the L both runs have, frames 0-199): cerr1, cerr2, ierr2, syn1, syn2, ll_in1 exact,
            eps_ce1/2, eps_det1/2 within 1e-10 (c1i closure convention; stored rows carry round-1 cerr/syn/ll and round-2 final counts only); ll_in2 vs logloss_bits report-only.
        (b) internal T = 20 determinism on the cells without stored rows: det rows (frames 0-9) vs REP R4T20 rows, cerr/ierr/dsha/ll_in rounds 1-4 exact.
        (c) supporting: rounds 1-4 of the R10 rows (T = 40 vs IB_T40; T = 20 f10/g10 vs c1i FULL_R4) equal the 4-round rows (the R10 rows are used for R <= 4 at L28/32).
IB2-1   per REP condition: Kc_R(40)/Kc_R(20) - 1 >= .05 with CI lower end > 1 at R1 and at R2; pass if >= 4/5 conditions.
IB2-2   6.5 dB rho .3, L 8-24, frames 0-299: Kc_R(30) between Kc_R(20) and Kc_R(40) (point, inclusive) at every R = 1..4, and the paired CI of Kc_R(50)/Kc_R(40) contains 1 at every R.
IB2-3   Kc_R10(40)/Kc_R10(20) paired CI lower end > 1 (L16-32); stated expectation +5% to +15%.
IB2-4   report-only compute frontier at 6.5 dB rho .3: Kc(R, T) vs measured cost (receiver-clock seconds through round R, mean over the timing-reference rows) and R x T;
        equal-inner-update-budget pairs (R, 40) vs (2R, 20).
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
B, SEED = 2000, 20261011
MOVE_BAR = 0.05
RMAX = 10
GRID_A = (8, 12, 16, 20, 24)  # the IB grid
MAIN = (650, 300)  # 6.5 dB, rho .3 (permille)
REP_CONDS = [(650, 200), (800, 200), (800, 300), (800, 500), (950, 300)]
EPS_TOL = 1e-10

ap = argparse.ArgumentParser()
for name, default in (('rep-dir', 'out/c1ib2_rep'), ('sweep-dir', 'out/c1ib2_sweep'), ('r10-dir', 'out/c1ib2_r10'), ('det-dir', 'out/c1ib2_det'),
                      ('time-dir', 'out/c1ib2_time'), ('ib-dir', 'out/c1ib'), ('c1i-dir', 'out/c1i'), ('f10-dir', 'out/c1f_r10'),
                      ('g10-dir', 'out/c1g_r10lo'), ('boot-dir', 'out/c1_boot'), ('map-dir', 'out/c1_map')):
    ap.add_argument('--' + name, default=default)
ap.add_argument('--out', default='out/c1ib2/analysis')
args = ap.parse_args()
P = lambda s: (HERE / s) if not Path(s).is_absolute() else Path(s)
OUT = P(args.out)


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def load_rows(d, must=()):
    """Rows of d/rows_shard*.jsonl; lines are pre-filtered by substrings (must) before parsing."""
    rows = []
    for f in sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl'))):
        with open(f) as fh:
            for x in fh:
                if x.strip() and all(m in x for m in must):
                    rows.append(json.loads(x))
    return rows


def keyed(rows, arm, snr, rho, frame_max):
    """{(L, frame): row}: ok rows of this arm in the cell, frames < frame_max; a duplicate is an error."""
    out = {}
    for r in rows:
        if r['arm'] == arm and r['status'] == 'ok' and r['snr_centi_db'] == snr and r['rho_permille'] == rho and r['frame'] < frame_max:
            k = (r['L'], r['frame'])
            if k in out:
                raise ValueError(f'duplicate row {arm} {snr} {rho} {k}')
            out[k] = r
    return out


def n_err(rows):
    return sum(1 for r in rows if r['status'] != 'ok')


def pct(x):
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def f3(x, d=3):
    return '-' if x is None else f'{x:.{d}f}'


def n_rounds(row):
    r = 0
    while f'ierr{r + 1}' in row:
        r += 1
    return r


res = dict(_argv=sys.argv, _config=dict(B=B, seed=SEED, move_bar=MOVE_BAR, grid_a=list(GRID_A), main=list(MAIN), rep_conds=[list(c) for c in REP_CONDS],
                                         eps_tol=EPS_TOL, dirs={k: v for k, v in vars(args).items()}))
md = ['# IB2: replication, T sweep, 10 rounds, compute frontier', '']

# ================================================================================ load
DIRS = dict(rep=args.rep_dir, sweep=args.sweep_dir, r10=args.r10_dir, det=args.det_dir, time=args.time_dir, ib=args.ib_dir, c1i=args.c1i_dir,
            f10=args.f10_dir, g10=args.g10_dir, boot=args.boot_dir, map=args.map_dir)
MUST = dict(boot=('"arm": "SPg_flat"', '"snr_centi_db": 800'), map=('"arm": "SPg_flat"', '"snr_centi_db": 650'))
D = {k: (load_rows(d, MUST.get(k, ())) if glob.glob(str(P(d) / 'rows_shard*.jsonl')) else []) for k, d in DIRS.items()}
res['rows'] = {k: dict(n=len(v), error=n_err(v)) for k, v in D.items()}
res['_config']['md5'] = dict(
    script=md5(Path(__file__)), c1e_predict=md5(HERE / 'c1e_predict.py'),
    rows={k: {Path(f).name: md5(f) for f in sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl')))} for k, d in DIRS.items()})
md += ['Rows read: ' + ', '.join(f"{k} {v['n']} (error {v['error']})" for k, v in res['rows'].items()), '']

# ================================================================================ IB2-0
a0 = dict(a=None, b=None, c=None)
md += ['## IB2-0 determinism / closure', '']
# (a) closure vs the stored 2-round SPg_flat rows (c1_boot 8 dB; c1_map 6.5 dB rho .3)
rep20 = {c: keyed(D['rep'], 'R4T20', c[0], c[1], 200) for c in REP_CONDS}
boot = {(r['rho_permille'], r['L'], r['frame']): r for r in D['boot'] if r['arm'] == 'SPg_flat' and r['status'] == 'ok' and r['snr_centi_db'] == 800}
cmap = {(r['L'], r['frame']): r for r in D['map'] if r['arm'] == 'SPg_flat' and r['status'] == 'ok' and r['snr_centi_db'] == 650 and r['rho_permille'] == 300}
c1i_t20 = keyed(D['c1i'], 'FULL_R4', *MAIN, 300)
f10 = keyed(D['f10'], 'FULL_R10', *MAIN, 300)
g10 = keyed(D['g10'], 'FULL_R10', *MAIN, 300)
ib_t40 = keyed(D['ib'], 'IB_T40', *MAIN, 300)
r10_t40 = keyed(D['r10'], 'R10T40', *MAIN, 300)
sw30, sw50 = keyed(D['sweep'], 'R4T30', *MAIN, 300), keyed(D['sweep'], 'R4T50', *MAIN, 300)


def closure(pairs):
    cnt = {k: dict(n=0, mismatch=0) for k in ('cerr1', 'cerr2', 'ierr2', 'syn1', 'syn2', 'll_in1')}
    eps_max = ll2_max = 0.
    ll2_mis = n = 0
    for r, s in pairs:
        n += 1
        vals = dict(cerr1=(r['cerr1'], s['r1_cerr']), cerr2=(r['cerr2'], s['coded_errors']), ierr2=(r['ierr2'], s['info_errors']),
                    syn1=(r['syn1'], s['r1_syn']), syn2=(r['syn2'], s['syndrome']), ll_in1=(r['ll_in1'], s['r1_ll_in']))
        for k, (x, y) in vals.items():
            cnt[k]['n'] += 1
            cnt[k]['mismatch'] += int(x != y)
        eps_max = max(eps_max, max(abs(r[k] - s[k]) for k in ('eps_ce1', 'eps_det1', 'eps_ce2', 'eps_det2')))
        ll2_max = max(ll2_max, abs(r['ll_in2'] - s['logloss_bits']))
        ll2_mis += int(r['ll_in2'] != s['logloss_bits'])
    tot = sum(v['mismatch'] for v in cnt.values())
    return dict(n_compared=n, fields=cnt, total_mismatch=tot, eps_max_abs=eps_max, ll_in2_vs_logloss_bits=dict(mismatch=ll2_mis, max_abs=ll2_max),
                **{'pass': bool(n > 0 and tot == 0 and eps_max <= EPS_TOL)})


srcs_a = {}
pairs = [(r, boot[(c[1], L, f)]) for c in REP_CONDS if c[0] == 800 for (L, f), r in sorted(rep20[c].items()) if (c[1], L, f) in boot]
if pairs:
    srcs_a['REP R4T20 vs c1_boot (8 dB, rho .2/.3/.5, frames 0-199)'] = closure(pairs)
for name, tab in (('c1i FULL_R4', c1i_t20), ('c1f_r10 FULL_R10', f10), ('c1g_r10lo FULL_R10', g10)):
    pairs = [(r, cmap[k]) for k, r in sorted(tab.items()) if k in cmap]
    if pairs:
        srcs_a[f'{name} vs c1_map (6.5 dB, rho .3, frames 0-299)'] = closure(pairs)
a0['a'] = dict(sources=srcs_a, **{'pass': bool(srcs_a and all(v['pass'] for v in srcs_a.values()))}) if srcs_a else None
if srcs_a:
    for name, v in srcs_a.items():
        fl = ', '.join(k + ' ' + str(e['mismatch']) + '/' + str(e['n']) for k, e in v['fields'].items())
        md += [f"(a) {name}: {v['n_compared']} (cell, frame) pairs; mismatches {v['total_mismatch']} ({fl}); eps max abs diff {v['eps_max_abs']:.2e}; "
               f"ll_in2 vs logloss_bits {v['ll_in2_vs_logloss_bits']['mismatch']} unequal (max abs {v['ll_in2_vs_logloss_bits']['max_abs']:.2e}).  **{'PASS' if v['pass'] else 'FAIL'}**", '']
else:
    md += ['(a) skipped (no stored c1_boot / c1_map counterparts among the loaded rows)', '']
# (b) internal determinism, det vs rep
if D['det'] and D['rep']:
    n_cells = n_bad = n_missing = 0
    fields = {f'{f}{r}': 0 for f in ('cerr', 'ierr', 'dsha', 'll_in') for r in range(1, 5)}
    for r in D['det']:
        if r['status'] != 'ok' or r['arm'] != 'R4T20':
            continue
        s = rep20.get((r['snr_centi_db'], r['rho_permille']), {}).get((r['L'], r['frame']))
        if s is None:
            n_missing += 1
            continue
        n_cells += 1
        bad = [k for k in fields if r[k] != s[k]]
        for k in bad:
            fields[k] += 1
        n_bad += bool(bad)
    a0['b'] = dict(n_cells=n_cells, n_missing_in_rep=n_missing, n_cells_with_mismatch=n_bad, fields_mismatch=fields, **{'pass': bool(n_cells > 0 and n_missing == 0 and n_bad == 0)})
    md += [f"(b) internal T = 20 determinism (cells without stored rows, frames 0-9): {n_cells} cells compared, missing in REP {n_missing}, cells with any mismatch "
           f"(cerr/ierr/dsha/ll_in, rounds 1-4) {n_bad}.  **{'PASS' if a0['b']['pass'] else 'FAIL'}**", '']
else:
    md += ['(b) skipped (det or rep rows absent)', '']

# main-condition tables are loaded above
def compare_rows(A, Bt, fields=('cerr', 'ierr', 'dsha', 'll_in'), rounds=range(1, 5)):
    n = bad = 0
    for k, r in A.items():
        s = Bt.get(k)
        if s is None:
            continue
        n += 1
        bad += any(r[f'{f}{q}'] != s[f'{f}{q}'] for f in fields for q in rounds)
    return n, bad


c_r10_40 = compare_rows(r10_t40, ib_t40)
c_t20 = {name: compare_rows(t, c1i_t20) for name, t in (('f10', f10), ('g10', g10))}
a0['c'] = dict(R10T40_vs_IB_T40=dict(n=c_r10_40[0], mismatch=c_r10_40[1]), T20_f10_vs_c1i=dict(n=c_t20['f10'][0], mismatch=c_t20['f10'][1]),
               T20_g10_vs_c1i=dict(n=c_t20['g10'][0], mismatch=c_t20['g10'][1]),
               **{'pass': bool(c_r10_40[1] == 0 and all(v[1] == 0 for v in c_t20.values()) and (c_r10_40[0] > 0 or any(v[0] > 0 for v in c_t20.values())))})
md += [f"(c) rounds 1-4 of the 10-round rows vs the 4-round rows (cerr/ierr/dsha/ll_in): R10T40 vs IB_T40 {c_r10_40[1]}/{c_r10_40[0]} mismatches; "
       f"T = 20 f10 vs c1i {c_t20['f10'][1]}/{c_t20['f10'][0]}, g10 vs c1i {c_t20['g10'][1]}/{c_t20['g10'][0]}.  **{'PASS' if a0['c']['pass'] else 'FAIL / not available'}**", '']
res['IB2_0'] = a0

# ================================================================================ Kc machinery


def kc_cens(Ks, ys):
    """(Kc, code): 0 exact crossing; 1 'above range' (all FER < .5, Kc >= max K); 2 'below range' (all FER >= .5, Kc <= min K)."""
    k = E.k_cross(Ks, list(ys), 0.5)
    if k is not None:
        return k, 0
    if all(y < 0.5 for y in ys):
        return float(Ks[-1]), 1
    if all(y >= 0.5 for y in ys):
        return float(Ks[0]), 2
    raise ValueError('no crossing but mixed FER')


CODE = {0: 'exact', 1: 'above_range', 2: 'below_range'}


class Cond:
    """fail[T][L] -> (n, RMAX) float array (1 = frame error in round r, NaN = round not run); frames common to all arrays."""

    def __init__(self, name, fail, seed):
        self.name, self.fail = name, fail
        self.n = next(iter(next(iter(fail.values())).values())).shape[0]
        self.idx = np.random.default_rng(seed).integers(0, self.n, size=(B, self.n))
        self._bm, self._est = {}, {}

    def avail(self, T, L):
        a = self.fail.get(T, {}).get(L)
        return 0 if a is None else int(np.sum(~np.isnan(a[0])))

    def Ls(self, T, R, restrict=None):
        return sorted(L for L in self.fail.get(T, {}) if self.avail(T, L) >= R and (restrict is None or L in restrict))

    def bmean(self, T, L):
        if (T, L) not in self._bm:
            self._bm[(T, L)] = self.fail[T][L][self.idx].mean(axis=1)  # (B, RMAX)
        return self._bm[(T, L)]

    def est(self, T, R, Ls):
        key = (T, R, tuple(Ls))
        if key not in self._est:
            Ks = [8 * L for L in Ls]
            point, code = kc_cens(Ks, [float(self.fail[T][L][:, R - 1].mean()) for L in Ls])
            M = np.stack([self.bmean(T, L)[:, R - 1] for L in Ls], axis=1)
            bk, bc = np.empty(B), np.empty(B, int)
            for b in range(B):
                bk[b], bc[b] = kc_cens(Ks, M[b])
            lo, hi = pct(bk)
            self._est[key] = dict(T=T, R=R, Ls=list(Ls), point=point, code=int(code), status=CODE[code], lo=lo, hi=hi, boot=bk, bcode=bc,
                                  fer=[float(self.fail[T][L][:, R - 1].mean()) for L in Ls],
                                  boot_status={CODE[c]: int(np.sum(bc == c)) for c in CODE})
        return self._est[key]

    def ratio(self, a, b):
        rb = a['boot'] / b['boot']
        lo, hi = pct(rb)
        rat = a['point'] / b['point']
        up, excl = bool(rat - 1. >= MOVE_BAR), bool(lo > 1.)
        return dict(ratio=rat, lo=lo, hi=hi, up_ge_bar=up, ci_lo_gt_1=excl, ci_contains_1=bool(lo <= 1. <= hi), moves=bool(up and excl),
                    censored=bool(a['code'] or b['code']), n_boot_censored=int(np.sum((a['bcode'] != 0) | (b['bcode'] != 0))),
                    status=f"{a['status']}/{b['status']}")


def strip(e):
    return {k: v for k, v in e.items() if k not in ('boot', 'bcode')}


def build_fail(tables, frames=None):
    """tables: {T: [{(L, frame): row}, ...]} -> per (T, L) the source with the most rounds; frames = common frames over everything."""
    best = {}
    for T, lst in tables.items():
        for tab in lst:
            for (L, f), r in tab.items():
                nr = n_rounds(r)
                cur = best.setdefault((T, L), {}).setdefault(f, (nr, r))
                if nr > cur[0]:
                    best[(T, L)][f] = (nr, r)
    if not best:
        return None, []
    common = sorted(set.intersection(*[set(v) for v in best.values()])) if frames is None else frames
    if not common:
        return None, []
    fail = {}
    for (T, L), v in best.items():
        a = np.full((len(common), RMAX), np.nan)
        for i, f in enumerate(common):
            nr, r = v[f]
            for q in range(1, nr + 1):
                a[i, q - 1] = float(r[f'ierr{q}'] > 0)
        fail.setdefault(T, {})[L] = a
    return fail, common


# ================================================================================ IB2-1 replication
rep_tabs = {c: {T: [keyed(D['rep'], f'R4T{T}', c[0], c[1], 200)] for T in (20, 40)} for c in REP_CONDS}
a1 = dict(conds={})
md += ['## IB2-1 replication (rounds 4, T 20 vs 40, frames 0-199)', '']
rep_cond_obj = {}
for i, c in enumerate(REP_CONDS):
    tabs = {T: [t for t in lst if t] for T, lst in rep_tabs[c].items()}
    if not all(tabs.values()):
        continue
    fail, frames = build_fail(tabs)
    if fail is None:
        continue
    co = Cond(f'{c[0] / 100:g} dB rho {c[1] / 1000:g}', fail, SEED + 100 + i)
    rep_cond_obj[c] = co
    Ls = sorted(set(co.Ls(20, 4)) & set(co.Ls(40, 4)))
    ent = dict(name=co.name, n_frames=co.n, Ls=Ls, rounds={})
    md += [f'### {co.name} (L {Ls}, {co.n} frames)', '', '| R | Kc T20 [CI] | Kc T40 [CI] | ratio [paired CI] | moves | status | FER T20 (by L) | FER T40 (by L) |', '|---|---|---|---|---|---|---|---|']
    for R in range(1, 5):
        e20, e40 = co.est(20, R, Ls), co.est(40, R, Ls)
        rt = co.ratio(e40, e20)
        ent['rounds'][f'R{R}'] = dict(T20=strip(e20), T40=strip(e40), ratio=rt)
        md.append(f"| {R} | {e20['point']:.1f} [{e20['lo']:.1f}, {e20['hi']:.1f}] | {e40['point']:.1f} [{e40['lo']:.1f}, {e40['hi']:.1f}] | {rt['ratio']:.3f} [{rt['lo']:.3f}, {rt['hi']:.3f}] | "
                  f"{'Y' if rt['moves'] else 'N'} | {rt['status']} | " + ' '.join(f'{y:.2f}' for y in e20['fer']) + ' | ' + ' '.join(f'{y:.2f}' for y in e40['fer']) + ' |')
    ent['passes'] = bool(ent['rounds']['R1']['ratio']['moves'] and ent['rounds']['R2']['ratio']['moves'])
    a1['conds'][co.name] = ent
    md.append('')
a1['n_conditions'] = len(a1['conds'])
a1['n_pass'] = sum(e['passes'] for e in a1['conds'].values())
a1['pass'] = bool(a1['n_conditions'] == len(REP_CONDS) and a1['n_pass'] >= 4)
res['IB2_1'] = a1
if a1['n_conditions']:
    md += [f"**IB2-1 {'PASS' if a1['pass'] else 'FAIL'}**: conditions with a move at both R1 and R2: {a1['n_pass']}/{a1['n_conditions']} "
           f"({', '.join(n + ' ' + ('Y' if e['passes'] else 'N') for n, e in a1['conds'].items())}); rule >= 4/5.", '']
else:
    md += ['IB2-1 skipped (rep rows absent)', '']

# ================================================================================ main condition (6.5 dB, rho .3)
main_tabs = {20: [t for t in (c1i_t20, g10, f10) if t], 30: [t for t in (sw30,) if t], 40: [t for t in (ib_t40, r10_t40) if t], 50: [t for t in (sw50,) if t]}
main_tabs = {T: v for T, v in main_tabs.items() if v}
fail_main, frames_main = build_fail(main_tabs) if main_tabs else (None, [])
main = Cond('6.5 dB rho .3', fail_main, SEED) if fail_main else None
if main:
    md += [f'## 6.5 dB, rho .3: frames common to all (T, L) arrays: {main.n}; L available: ' +
           '; '.join(f"T{T} " + ' '.join(f"L{L}:{main.avail(T, L)}r" for L in sorted(main.fail[T])) for T in sorted(main.fail)), '']

# ================================================================================ IB2-2 saturation
a2 = dict(rounds={})
if main and all(T in main.fail for T in (20, 30, 40, 50)):
    md += ['## IB2-2 saturation (L 8-24, rounds 1-4, frames common)', '',
           '| R | Kc T20 | Kc T30 | Kc T40 | Kc T50 | T30 between 20 and 40 | T50/T40 [paired CI] | CI contains 1 | T30/T20 [CI] | T40/T20 [CI] | T50/T20 [CI] | status |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for R in range(1, 5):
        Ls = sorted(set.intersection(*[set(main.Ls(T, R, GRID_A)) for T in (20, 30, 40, 50)]))
        e = {T: main.est(T, R, Ls) for T in (20, 30, 40, 50)}
        lo_, hi_ = sorted((e[20]['point'], e[40]['point']))
        between = bool(lo_ <= e[30]['point'] <= hi_)
        r5040 = main.ratio(e[50], e[40])
        r_ = {f'T{T}/T20': main.ratio(e[T], e[20]) for T in (30, 40, 50)}
        a2['rounds'][f'R{R}'] = dict(Ls=Ls, kc={f'T{T}': strip(e[T]) for T in e}, between=between, r50_40=r5040, ratios=r_)
        md.append(f"| {R} | " + ' | '.join(f"{e[T]['point']:.1f}{'*' if e[T]['code'] else ''}" for T in (20, 30, 40, 50)) +
                  f" | {'Y' if between else 'N'} | {r5040['ratio']:.3f} [{r5040['lo']:.3f}, {r5040['hi']:.3f}] | {'Y' if r5040['ci_contains_1'] else 'N'} | " +
                  ' | '.join(f"{r_[k]['ratio']:.3f} [{r_[k]['lo']:.3f}, {r_[k]['hi']:.3f}]" for k in ('T30/T20', 'T40/T20', 'T50/T20')) +
                  f" | {'; '.join(sorted({r_[k]['status'] for k in r_} | {r5040['status']}))} |")
    a2['pass'] = bool(all(v['between'] and v['r50_40']['ci_contains_1'] for v in a2['rounds'].values()))
    md += ['', f"**IB2-2 {'PASS' if a2['pass'] else 'FAIL'}** (T30 between T20 and T40 at every R: {[v['between'] for v in a2['rounds'].values()]}; "
               f"CI(T50/T40) contains 1 at every R: {[v['r50_40']['ci_contains_1'] for v in a2['rounds'].values()]}).  (* = censored at the range edge.)", '']
else:
    a2['pass'] = None
    md += ['## IB2-2 skipped (sweep rows absent)', '']
res['IB2_2'] = a2

# ================================================================================ IB2-3 ten rounds
a3 = dict(rounds={})
if main and 20 in main.fail and 40 in main.fail and any(main.avail(40, L) >= RMAX for L in main.fail[40]) and any(main.avail(20, L) >= RMAX for L in main.fail[20]):
    md += ['## IB2-3 ten rounds (T 40 vs T 20; L = those with 10-round rows for both)', '', '| R | L | Kc T20 [CI] | Kc T40 [CI] | ratio [paired CI] | moves | status |', '|---|---|---|---|---|---|---|']
    for R in range(1, RMAX + 1):
        Ls = sorted(set(main.Ls(20, R)) & set(main.Ls(40, R)))
        if len(Ls) < 2:
            continue
        e20, e40 = main.est(20, R, Ls), main.est(40, R, Ls)
        rt = main.ratio(e40, e20)
        a3['rounds'][f'R{R}'] = dict(Ls=Ls, T20=strip(e20), T40=strip(e40), ratio=rt)
        md.append(f"| {R} | {Ls[0]}-{Ls[-1]} | {e20['point']:.1f}{'*' if e20['code'] else ''} [{e20['lo']:.1f}, {e20['hi']:.1f}] | {e40['point']:.1f}{'*' if e40['code'] else ''} [{e40['lo']:.1f}, {e40['hi']:.1f}] | "
                  f"{rt['ratio']:.3f} [{rt['lo']:.3f}, {rt['hi']:.3f}] | {'Y' if rt['moves'] else 'N'} | {rt['status']} |")
    r10 = a3['rounds'].get(f'R{RMAX}')
    if r10:
        a3['pass'] = bool(r10['ratio']['lo'] > 1.)
        a3['expectation_5_to_15pct'] = bool(0.05 <= r10['ratio']['ratio'] - 1. <= 0.15)
        md += ['', f"**IB2-3 {'PASS' if a3['pass'] else 'FAIL'}**: Kc_R10(40)/Kc_R10(20) = {r10['ratio']['ratio']:.3f} [{r10['ratio']['lo']:.3f}, {r10['ratio']['hi']:.3f}] "
                   f"(shift {r10['ratio']['ratio'] - 1.:+.3f}); stated expectation +5% to +15%: {'inside' if a3['expectation_5_to_15pct'] else 'outside'}.  (* = censored.)", '']
else:
    a3['pass'] = None
    md += ['## IB2-3 skipped (10-round rows absent)', '']
res['IB2_3'] = a3

# ================================================================================ IB2-4 compute frontier
a4 = dict(points=[], pairs=[], cost=None)
cost, cost24, time_note = {}, {}, None
trows = [r for r in D['time'] if r['status'] == 'ok' and r['snr_centi_db'] == MAIN[0] and r['rho_permille'] == MAIN[1]]
if trows:
    for T in (20, 30, 40, 50):
        rr = [r for r in trows if r['arm'] == f'R10T{T}']
        if not rr:
            continue
        for R in range(1, RMAX + 1):
            cost[(R, T)] = float(np.mean([r['t_cum'][R - 1] for r in rr]))
            r24 = [r['t_cum'][R - 1] for r in rr if r['L'] == 24]
            cost24[(R, T)] = float(np.mean(r24)) if r24 else None
    n_sh = len(glob.glob(str(P(args.time_dir) / 'results_shard*.json')))
    time_note = (f"cost = mean over {len(trows)} timing-reference rows (L {sorted({r['L'] for r in trows})}, frames {sorted({r['frame'] for r in trows})[0]}-{sorted({r['frame'] for r in trows})[-1]}) "
                 f"of the receiver-clock seconds at the end of round R (incl. pilot front); run with {n_sh} shards; machine load during the run is NOT controlled by this script "
                 f"(the reference run is meant to be alone on a quiet server).")
a4['cost_note'] = time_note
if main:
    md += ['## IB2-4 compute frontier (report-only), 6.5 dB rho .3', '']
    if time_note:
        md += [time_note, '']
    else:
        md += ['No timing-reference rows (out/c1ib2_time): cost column unavailable; R x T only.', '']
    pts = []
    for T in (20, 40, 30, 50):
        if T not in main.fail:
            continue
        for R in range(1, RMAX + 1):
            restrict = None if T in (20, 40) else GRID_A
            Ls = main.Ls(T, R, restrict)
            if len(Ls) < 2:
                continue
            e = main.est(T, R, Ls)
            pts.append(dict(R=R, T=T, U=R * T, Ls=Ls, kc=e['point'], lo=e['lo'], hi=e['hi'], status=e['status'], cost=cost.get((R, T)), cost_L24=cost24.get((R, T))))
    for p in pts:
        p['pareto_cost'] = bool(p['cost'] is not None and not any(
            (q['cost'] is not None and q['cost'] <= p['cost'] and q['kc'] >= p['kc'] and (q['cost'] < p['cost'] or q['kc'] > p['kc'])) for q in pts))
        p['pareto_U'] = bool(not any((q['U'] <= p['U'] and q['kc'] >= p['kc'] and (q['U'] < p['U'] or q['kc'] > p['kc'])) for q in pts))
    a4['points'] = pts
    md += ['| R | T | R x T | cost s (all L) | cost s (L24) | Kc [95% CI] | L grid | status | Pareto (cost) | Pareto (R x T) |', '|---|---|---|---|---|---|---|---|---|---|']
    for p in sorted(pts, key=lambda p: (p['cost'] if p['cost'] is not None else 1e9, p['U'])):
        md.append(f"| {p['R']} | {p['T']} | {p['U']} | {f3(p['cost'], 2)} | {f3(p['cost_L24'], 2)} | {p['kc']:.1f} [{p['lo']:.1f}, {p['hi']:.1f}] | {p['Ls'][0]}-{p['Ls'][-1]} | {p['status']} | "
                  f"{'Y' if p['pareto_cost'] else ''} | {'Y' if p['pareto_U'] else ''} |")
    md += ['', '(T 30 / 50 points use the L 8-24 grid; T 20 / 40 use every L with rows for that round.  A point with status above_range is a lower bound.)', '']
    # best Kc at equal compute: running maximum over cost, and over R x T
    for key, label in (('cost', 'measured cost'), ('U', 'inner-update count R x T')):
        seq = sorted([p for p in pts if p[key] is not None], key=lambda p: p[key])
        best, run = [], None
        for p in seq:
            if run is None or p['kc'] > run['kc']:
                run = p
                best.append(p)
        a4[f'best_by_{key}'] = [dict(R=p['R'], T=p['T'], kc=p['kc'], **{key: p[key]}) for p in best]
        if best:
            md += [f'Highest Kc reached so far, by {label}: ' + '; '.join(f"({p['R']},{p['T']}) {p['kc']:.0f} @ {p[key]:.1f}" for p in best), '']
    md += ['Equal inner-update budget: (R, 40) vs (2R, 20).', '', '| R | (R, 40) Kc | (2R, 20) Kc | ratio (R,40)/(2R,20) [paired CI] | status | cost (R,40) s | cost (2R,20) s |', '|---|---|---|---|---|---|---|']
    for R in range(1, 6):
        if 40 not in main.fail or 20 not in main.fail:
            break
        Ls = sorted(set(main.Ls(40, R)) & set(main.Ls(20, 2 * R)))
        if len(Ls) < 2:
            continue
        a, b = main.est(40, R, Ls), main.est(20, 2 * R, Ls)
        rt = main.ratio(a, b)
        a4['pairs'].append(dict(R=R, Ls=Ls, a=strip(a), b=strip(b), ratio=rt, cost_a=cost.get((R, 40)), cost_b=cost.get((2 * R, 20))))
        md.append(f"| {R} | {a['point']:.1f} | {b['point']:.1f} | {rt['ratio']:.3f} [{rt['lo']:.3f}, {rt['hi']:.3f}] | {rt['status']} | {f3(cost.get((R, 40)), 2)} | {f3(cost.get((2 * R, 20)), 2)} |")
    md.append('')
else:
    md += ['## IB2-4 skipped (no 6.5 dB rho .3 arrays)', '']
res['IB2_4'] = a4

# ================================================================================ report-only
rep = dict(fer_I={}, eps_ratio={}, calib={})
md += ['## Report-only', '']


def rows_of(c, T):
    return {k: v for k, v in rep_tabs[c][T][0].items()} if c in rep_tabs else {}


md += ['### FER by round (ierr_R > 0) and mean I_R = 1 - ll_in_R, REP conditions, by L and T', '', '| condition | L | T | FER r1 | r2 | r3 | r4 | I r1 | r2 | r3 | r4 |', '|---|---|---|---|---|---|---|---|---|---|---|']
for c, co in rep_cond_obj.items():
    Ls = sorted(set(co.Ls(20, 4)) & set(co.Ls(40, 4)))
    frames_c = sorted({f for (_, f) in rep_tabs[c][20][0]} & {f for (_, f) in rep_tabs[c][40][0]})
    for L in Ls:
        for T in (20, 40):
            tab = rep_tabs[c][T][0]
            fer = [float(np.mean([tab[(L, f)][f'ierr{q}'] > 0 for f in frames_c])) for q in range(1, 5)]
            mi = [float(np.mean([1. - tab[(L, f)][f'll_in{q}'] for f in frames_c])) for q in range(1, 5)]
            rep['fer_I'][f'{co.name}|L{L}|T{T}'] = dict(fer=fer, I=mi)
            md.append(f"| {co.name} | {L} | {T} | " + ' | '.join(f'{x:.3f}' for x in fer) + ' | ' + ' | '.join(f'{x:.4f}' for x in mi) + ' |')
md += ['', '### Median per-frame eps_det_r(T = 40) / eps_det_r(T = 20), REP conditions', '', '| condition | L | r1 | r2 | r3 | r4 |', '|---|---|---|---|---|---|']
for c, co in rep_cond_obj.items():
    Ls = sorted(set(co.Ls(20, 4)) & set(co.Ls(40, 4)))
    frames_c = sorted({f for (_, f) in rep_tabs[c][20][0]} & {f for (_, f) in rep_tabs[c][40][0]})
    for L in Ls:
        rat = [float(np.median([rep_tabs[c][40][0][(L, f)][f'eps_det{q}'] / rep_tabs[c][20][0][(L, f)][f'eps_det{q}'] for f in frames_c])) for q in range(1, 5)]
        rep['eps_ratio'][f'{co.name}|L{L}'] = rat
        md.append(f'| {co.name} | {L} | ' + ' | '.join(f'{x:.3f}' for x in rat) + ' |')
# calibration drop: mean I_1(T) < mean I_1(20) while FER_1(T) <= FER_1(20)
md += ['', '### I_1 calibration drop at larger T (mean I_1(T) - I_1(20) < -.005 while FER_1(T) <= FER_1(20))', '', '| condition | L | T | dI_1 | dFER_1 | flagged |', '|---|---|---|---|---|---|']
calib_rows = []
for c, co in rep_cond_obj.items():
    Ls = sorted(set(co.Ls(20, 4)) & set(co.Ls(40, 4)))
    frames_c = sorted({f for (_, f) in rep_tabs[c][20][0]} & {f for (_, f) in rep_tabs[c][40][0]})
    for L in Ls:
        t20, t40 = rep_tabs[c][20][0], rep_tabs[c][40][0]
        dI = float(np.mean([t40[(L, f)]['ll_in1'] - t20[(L, f)]['ll_in1'] for f in frames_c]) * -1.)
        dF = float(np.mean([t40[(L, f)]['ierr1'] > 0 for f in frames_c]) - np.mean([t20[(L, f)]['ierr1'] > 0 for f in frames_c]))
        calib_rows.append((co.name, L, 40, dI, dF))
if main:
    tab_by_T = {T: {} for T in main.fail}
    for T, lst in main_tabs.items():
        for tab in lst:
            for k, r in tab.items():
                tab_by_T[T].setdefault(k, r)
    fr = frames_main
    for T in (30, 40, 50):
        if T not in tab_by_T or 20 not in tab_by_T:
            continue
        for L in sorted(main.fail[T]):
            if L not in {l for (l, _) in tab_by_T[20]}:
                continue
            dI = float(np.mean([tab_by_T[20][(L, f)]['ll_in1'] - tab_by_T[T][(L, f)]['ll_in1'] for f in fr]))
            dF = float(np.mean([tab_by_T[T][(L, f)]['ierr1'] > 0 for f in fr]) - np.mean([tab_by_T[20][(L, f)]['ierr1'] > 0 for f in fr]))
            calib_rows.append(('6.5 dB rho .3', L, T, dI, dF))
for name, L, T, dI, dF in calib_rows:
    flag = bool(dI < -0.005 and dF <= 0)
    rep['calib'][f'{name}|L{L}|T{T}'] = dict(dI1=dI, dFER1=dF, flagged=flag)
    md.append(f"| {name} | {L} | {T} | {dI:+.4f} | {dF:+.3f} | {'Y' if flag else ''} |")
rep['calib_flagged'] = [k for k, v in rep['calib'].items() if v['flagged']]
res['report_only'] = rep
md.append('')

res['summary'] = dict(IB2_0_a=(a0['a'] or {}).get('pass'), IB2_0_b=(a0['b'] or {}).get('pass'), IB2_0_c=a0['c']['pass'], IB2_1=a1['pass'] if a1['n_conditions'] else None,
                      IB2_1_n_pass=a1['n_pass'], IB2_2=a2['pass'], IB2_3=a3['pass'])
md = [md[0], '', 'Summary: ' + ', '.join(f'{k} {v}' for k, v in res['summary'].items())] + md[1:]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'ib2.json').write_text(json.dumps(res, indent=1, default=float) + '\n')
(OUT / 'ib2.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
