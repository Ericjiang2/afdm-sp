#!/usr/bin/env python
"""Analysis of the inner-update budget run (IB; research/c1-inner-budget.md, FROZEN).  Reads rows and JSON only; no frozen file is modified.
    python -B c1ib_analyze.py [--dir out/c1ib] [--det-dir out/c1ib_det] [--c1i-dir out/c1i] [--preds out/c1_t2/predictions.json]
                              [--t1 out/c1_t1/t1_transfer.json] [--out out/c1ib/analysis]
Outputs <out>/ib.json (with _argv, _config incl. md5s) and <out>/ib.md.  Cells: 6.5 dB, rho .3, L 8-24 (K = 8 L), frames 0-299.

IB-0 determinism   IB_T20 re-run (--det-dir, frames 0-29, all L) vs the stored c1i FULL_R4 rows: cerr_r, ierr_r, dsha_r, ll_in_r (r = 1..4) exact.
                   (eps_ce_r / eps_det_r equality is reported, not part of the pass rule.)
IB-1 channel error per-frame ratio eps_det1(T) / eps_det1(20) (stored T = 20): median over frames at each L; pass = median(T=40) in [.80, .97]
                   at every L and median(T=80) <= median(T=40) at every L.
IB-2 link          per (T, L) cell: mean_f [I_1(T) - I_1(20)] (I_1 = 1 - ll_in1) vs mean_f [J_unc(q(e_T)) - J_unc(q(e_20))], q = eta a (E_real - e)/(n + e),
                   e = the frame's own eps_det1, E_real = the row's e_real, eta of the c1_map cell (6.5 dB, rho .3, L) from out/c1_t2/predictions.json,
                   a = .7, n = 10^-.65, J_unc from c1_t2_predict.load_curves(t1_transfer.json).  Cell ok if |pred - obs| <= .01;
                   pass for a T if >= 4/5 cells ok; IB-2 passes if both T = 40 and T = 80 pass (pooled count also reported).
IB-3 cliff         Kc_R(T) = FER_R .5 crossing, linear in K = 8 L (c1e_predict.k_cross, first crossing), FER_R = frac(ierr_R > 0), R = 1..4, T in {20 (stored), 40, 80};
                   percentile frame bootstrap (B = 2000, frames resampled jointly across L and T, so the ratio CI is paired).
                   "The inner budget moves the cliff" iff at some R: Kc_R(80) / Kc_R(20) - 1 >= .05 and the bootstrap CI of the ratio excludes 1 (lower end > 1).
                   A crossing outside the L range is censored at the nearest K of the range (flagged; the ratio is then a bound).
Report-only        FER and I_r by round, T, L; seconds per frame by T; eps_det by round and the round-4 eps_det ratio T = 80 vs T = 20.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

import c1_t2_predict as P2
import c1e_predict as E

HERE = Path(__file__).resolve().parent
B, SEED = 2000, 20261010
SNR_CD, RHO_PM = 650, 300
LS = (8, 12, 16, 20, 24)
TS = (20, 40, 80)
NFRAMES = 300
RMAX = 4
A_RHO, N0 = 0.7, 10 ** -0.65
IB1_BAND = (0.80, 0.97)
IB2_TOL, IB2_MIN_CELLS = 0.01, 4
MOVE_BAR = 0.05

ap = argparse.ArgumentParser()
ap.add_argument('--dir', default='out/c1ib')
ap.add_argument('--det-dir', default='out/c1ib_det')
ap.add_argument('--c1i-dir', default='out/c1i')
ap.add_argument('--preds', default='out/c1_t2/predictions.json')
ap.add_argument('--t1', default='out/c1_t1/t1_transfer.json')
ap.add_argument('--out', default=None)
args = ap.parse_args()
P = lambda s: (HERE / s) if not Path(s).is_absolute() else Path(s)
OUT = P(args.out) if args.out else P(args.dir) / 'analysis'


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def load_rows(d):
    rows = []
    for f in sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl'))):
        with open(f) as fh:
            rows += [json.loads(x) for x in fh if x.strip()]
    return rows


def table(rows, arm):
    """{(L, frame): row} of ok rows of this arm in the cell (6.5 dB, rho .3), frames < NFRAMES; duplicates are an error."""
    out = {}
    for r in rows:
        if r['arm'] == arm and r['status'] == 'ok' and r['snr_centi_db'] == SNR_CD and r['rho_permille'] == RHO_PM and r['frame'] < NFRAMES:
            key = (r['L'], r['frame'])
            if key in out:
                raise ValueError(f'duplicate row {arm} {key}')
            out[key] = r
    return out


def n_err(rows, arm):
    return sum(1 for r in rows if r['arm'] == arm and r['status'] != 'ok')


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def pct(x):
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def fnum(x, d=3):
    return '-' if x is None else f'{x:.{d}f}'


rows_ib = load_rows(args.dir)
rows_det = load_rows(args.det_dir)
rows_c1i = load_rows(args.c1i_dir)
stored = table(rows_c1i, 'FULL_R4')
tabs = {20: stored, 40: table(rows_ib, 'IB_T40'), 80: table(rows_ib, 'IB_T80')}
det = table(rows_det, 'IB_T20')
preds = json.loads(P(args.preds).read_text())
ETA = {(c['dataset'], c['snr_db'], c['rho'], c['L']): c['eta'] for c in preds['cells']}
cu, _ = P2.load_curves(P(args.t1))

res = dict(_argv=sys.argv, _config=dict(
    B=B, seed=SEED, snr_centi_db=SNR_CD, rho_permille=RHO_PM, Ls=list(LS), Ts=list(TS), n_frames=NFRAMES, a=A_RHO, n0=N0,
    ib1_band=list(IB1_BAND), ib2_tol=IB2_TOL, ib2_min_cells=IB2_MIN_CELLS, move_bar=MOVE_BAR,
    dirs=dict(ib=args.dir, det=args.det_dir, c1i=args.c1i_dir, preds=args.preds, t1=args.t1),
    md5=dict(preds=md5(P(args.preds)), t1=md5(P(args.t1)), c1ib_analyze=md5(Path(__file__)), c1e_predict=md5(HERE / 'c1e_predict.py'),
             c1_t2_predict=md5(HERE / 'c1_t2_predict.py'), c1_t2_model=md5(HERE / 'c1_t2_model.py'),
             rows={d: {Path(f).name: md5(f) for f in sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl')))}
                   for d in (args.dir, args.det_dir, args.c1i_dir)})))
res['rows'] = dict(ib=len(rows_ib), det=len(rows_det), c1i=len(rows_c1i), ib_error={a: n_err(rows_ib, a) for a in ('IB_T40', 'IB_T80')},
                   det_error=n_err(rows_det, 'IB_T20'),
                   n_ok={f'T{T}': {f'L{L}': sum(1 for k in tabs[T] if k[0] == L) for L in LS} for T in TS})
md = ['# IB: inner-update budget (6.5 dB, rho .3, K = 8 L)', '',
      f"Rows: IB {len(rows_ib)} (error rows {res['rows']['ib_error']}), det {len(rows_det)} (error {res['rows']['det_error']}), c1i {len(rows_c1i)}.  "
      f"ok rows per (T, L): " + '; '.join(f"T{T} " + ' '.join(f"L{L}:{sum(1 for k in tabs[T] if k[0] == L)}" for L in LS) for T in TS), '']

# ================================================================================ IB-0 determinism
fields = ('cerr', 'ierr', 'dsha', 'll_in')
a0 = dict(n_det=len(det), n_missing_in_c1i=0, fields={f'{f}{r}': dict(n=0, mismatch=0) for f in fields for r in range(1, RMAX + 1)},
          info={f'{f}{r}': dict(n=0, mismatch=0, max_abs_diff=0.) for f in ('eps_ce', 'eps_det') for r in range(1, RMAX + 1)})
bad = set()
for key, n_ in sorted(det.items()):
    s = stored.get(key)
    if s is None:
        a0['n_missing_in_c1i'] += 1
        continue
    for f in fields:
        for r in range(1, RMAX + 1):
            e = a0['fields'][f'{f}{r}']
            e['n'] += 1
            if n_[f'{f}{r}'] != s[f'{f}{r}']:
                e['mismatch'] += 1
                bad.add(key)
    for f in ('eps_ce', 'eps_det'):
        for r in range(1, RMAX + 1):
            e = a0['info'][f'{f}{r}']
            e['n'] += 1
            d = abs(float(n_[f'{f}{r}']) - float(s[f'{f}{r}']))
            e['mismatch'] += int(n_[f'{f}{r}'] != s[f'{f}{r}'])
            e['max_abs_diff'] = max(e['max_abs_diff'], d)
a0['total_mismatch'] = sum(e['mismatch'] for e in a0['fields'].values())
a0['n_cells_with_mismatch'] = len(bad)
a0['mismatch_cells_first10'] = sorted(bad)[:10]
a0['expected_cells'] = 30 * len(LS)
a0['pass'] = bool(a0['n_det'] == a0['expected_cells'] and a0['n_missing_in_c1i'] == 0 and a0['total_mismatch'] == 0)
res['IB_0'] = a0
md += ['## IB-0 determinism (IB_T20, frames 0-29, vs stored c1i FULL_R4)', '',
       f"cells {a0['n_det']} (expected {a0['expected_cells']}), missing in c1i {a0['n_missing_in_c1i']}, mismatches over cerr/ierr/dsha/ll_in x rounds 1-4: "
       f"{a0['total_mismatch']} (cells with any: {a0['n_cells_with_mismatch']}).  **IB-0 {'PASS' if a0['pass'] else 'FAIL'}**", '',
       '| round | cerr | ierr | dsha | ll_in | eps_ce mism (max abs) | eps_det mism (max abs) |', '|---|---|---|---|---|---|---|']
for r in range(1, RMAX + 1):
    f = a0['fields']
    i = a0['info']
    md.append(f"| {r} | {f[f'cerr{r}']['mismatch']} | {f[f'ierr{r}']['mismatch']} | {f[f'dsha{r}']['mismatch']} | {f[f'll_in{r}']['mismatch']} | "
              f"{i[f'eps_ce{r}']['mismatch']} ({i[f'eps_ce{r}']['max_abs_diff']:.2e}) | {i[f'eps_det{r}']['mismatch']} ({i[f'eps_det{r}']['max_abs_diff']:.2e}) |")
md.append('')

# common frames across L and T (paired bootstrap, ratios)
common = sorted(set.intersection(*[{k[1] for k in tabs[T] if k[0] == L} for T in TS for L in LS]))
res['common_frames'] = dict(n=len(common), first=common[0] if common else None, last=common[-1] if common else None)
md += [f"Frames common to all (T, L): {len(common)}.", '']
col = lambda T, L, name: np.array([tabs[T][(L, f)][name] for f in common], float)

# ================================================================================ IB-1 channel error
a1 = {}
md += ['## IB-1 round-1 channel error: per-frame eps_det1(T) / eps_det1(20)', '',
       '| L | median T40/T20 | [q10, q90] | median T80/T20 | [q10, q90] | T40 in band | T80 <= T40 |', '|---|---|---|---|---|---|---|']
for L in LS:
    e20 = col(20, L, 'eps_det1')
    ent = {}
    for T in (40, 80):
        ratio = col(T, L, 'eps_det1') / e20
        ent[f'T{T}'] = dict(median=float(np.median(ratio)), q10=float(np.percentile(ratio, 10)), q90=float(np.percentile(ratio, 90)),
                            mean=float(ratio.mean()), n=int(ratio.size))
    ent['T40_in_band'] = bool(IB1_BAND[0] <= ent['T40']['median'] <= IB1_BAND[1])
    ent['T80_le_T40'] = bool(ent['T80']['median'] <= ent['T40']['median'])
    a1[f'L{L}'] = ent
    md.append(f"| {L} | {ent['T40']['median']:.3f} | [{ent['T40']['q10']:.3f}, {ent['T40']['q90']:.3f}] | {ent['T80']['median']:.3f} | "
              f"[{ent['T80']['q10']:.3f}, {ent['T80']['q90']:.3f}] | {'Y' if ent['T40_in_band'] else 'N'} | {'Y' if ent['T80_le_T40'] else 'N'} |")
a1['pass'] = bool(all(a1[f'L{L}']['T40_in_band'] and a1[f'L{L}']['T80_le_T40'] for L in LS))
res['IB_1'] = a1
md += ['', f"**IB-1 {'PASS' if a1['pass'] else 'FAIL'}** (band [{IB1_BAND[0]}, {IB1_BAND[1]}] for T = 40 at every L; median(T=80) <= median(T=40) at every L).", '']

# ================================================================================ IB-2 link consistency
a2 = {}
md += ['## IB-2 link consistency: cell mean of I_1(T) - I_1(20), observed vs LMMSE-link prediction (|diff| <= .01)', '',
       '| T | L | eta | obs dI | pred dI | pred - obs | ok | mean I_1(20) obs | mean J(q20) pred |', '|---|---|---|---|---|---|---|---|---|']
for T in (40, 80):
    cells = {}
    for L in LS:
        eta = ETA[('c1_map', 6.5, 0.3, L)]
        r20 = [tabs[20][(L, f)] for f in common]
        rT = [tabs[T][(L, f)] for f in common]
        assert all(a['e_real'] == b['e_real'] for a, b in zip(r20, rT)), 'e_real differs between paired rows'
        E_real = np.array([r['e_real'] for r in r20], float)
        q = lambda e: eta * A_RHO * (E_real - e) / (N0 + e)
        e20, eT = np.array([r['eps_det1'] for r in r20], float), np.array([r['eps_det1'] for r in rT], float)
        pred_each = cu('J_unc', q(eT)) - cu('J_unc', q(e20))
        i20, iT = 1. - np.array([r['ll_in1'] for r in r20], float), 1. - np.array([r['ll_in1'] for r in rT], float)
        obs, pred = float((iT - i20).mean()), float(pred_each.mean())
        c = dict(eta=eta, obs=obs, pred=pred, diff=pred - obs, ok=bool(abs(pred - obs) <= IB2_TOL), I20_obs=float(i20.mean()),
                 J20_pred=float(cu('J_unc', q(e20)).mean()), n=len(common))
        cells[f'L{L}'] = c
        md.append(f"| {T} | {L} | {eta:.4f} | {obs:+.4f} | {pred:+.4f} | {pred - obs:+.4f} | {'Y' if c['ok'] else 'N'} | {c['I20_obs']:.4f} | {c['J20_pred']:.4f} |")
    a2[f'T{T}'] = dict(cells=cells, n_ok=sum(c['ok'] for c in cells.values()), passes=bool(sum(c['ok'] for c in cells.values()) >= IB2_MIN_CELLS))
a2['pooled_ok'] = sum(a2[f'T{T}']['n_ok'] for T in (40, 80))
a2['pass'] = bool(a2['T40']['passes'] and a2['T80']['passes'])
res['IB_2'] = a2
md += ['', f"cells ok: T40 {a2['T40']['n_ok']}/5, T80 {a2['T80']['n_ok']}/5 (pooled {a2['pooled_ok']}/10).  "
           f"**IB-2 {'PASS' if a2['pass'] else 'FAIL'}** (rule used: each of T = 40, T = 80 has >= 4/5 cells ok).", '']

# ================================================================================ IB-3 cliff
fail = {(T, L): np.array([[tabs[T][(L, f)][f'ierr{r}'] > 0 for r in range(1, RMAX + 1)] for f in common], float) for T in TS for L in LS}
Ks = [8 * L for L in LS]


def kc_cens(ys):
    """(Kc, status): exact crossing, or the nearest K of the range when FER_R never crosses .5 on the L grid (flagged)."""
    k = E.k_cross(Ks, list(ys), 0.5)
    if k is not None:
        return k, 'exact'
    if all(y < 0.5 for y in ys):
        return float(Ks[-1]), 'above_range'  # Kc >= Ks[-1]
    if all(y >= 0.5 for y in ys):
        return float(Ks[0]), 'below_range'  # Kc <= Ks[0]
    raise ValueError('no crossing but mixed FER')


point, status = {}, {}
for T in TS:
    for R in range(1, RMAX + 1):
        point[(T, R)], status[(T, R)] = kc_cens([fail[(T, L)][:, R - 1].mean() for L in LS])
n = len(common)
idx = np.random.default_rng(SEED).integers(0, n, size=(B, n))  # frames resampled jointly across L and T
fer_b = {(T, L): fail[(T, L)][idx].mean(axis=1) for T in TS for L in LS}  # (B, RMAX)
boot = {(T, R): np.empty(B) for T in TS for R in range(1, RMAX + 1)}
bstat = {(T, R): [] for T in TS for R in range(1, RMAX + 1)}
for b in range(B):
    for T in TS:
        for R in range(1, RMAX + 1):
            k, s = kc_cens([fer_b[(T, L)][b, R - 1] for L in LS])
            boot[(T, R)][b] = k
            bstat[(T, R)].append(s)
a3 = dict(fer={}, kc={}, ratio={})
md += ['## IB-3 cliff: Kc_R(T) (FER_R = .5 crossing, linear in K; frame bootstrap B = 2000, paired across L and T)', '',
       '| R | T | Kc [95% CI] | status (point; boot exact/above/below) | FER by L (8,12,16,20,24) |', '|---|---|---|---|---|']
for R in range(1, RMAX + 1):
    for T in TS:
        lo, hi = pct(boot[(T, R)])
        cnt = {s: bstat[(T, R)].count(s) for s in ('exact', 'above_range', 'below_range')}
        fers = [float(fail[(T, L)][:, R - 1].mean()) for L in LS]
        a3['kc'][f'R{R}_T{T}'] = dict(kc=point[(T, R)], status=status[(T, R)], lo=lo, hi=hi, boot_status=cnt, fer=fers)
        md.append(f"| {R} | {T} | {point[(T, R)]:.1f} [{lo:.1f}, {hi:.1f}] | {status[(T, R)]}; {cnt['exact']}/{cnt['above_range']}/{cnt['below_range']} | "
                  + ' '.join(f'{y:.3f}' for y in fers) + ' |')
md += ['', '| R | T | Kc(T)/Kc(20) | 95% CI (paired) | ratio - 1 >= .05 | CI excludes 1 (lo > 1) | moves cliff | censored |', '|---|---|---|---|---|---|---|---|']
moves = []
for R in range(1, RMAX + 1):
    for T in (40, 80):
        rat = point[(T, R)] / point[(20, R)]
        rb = boot[(T, R)] / boot[(20, R)]
        lo, hi = pct(rb)
        cens = status[(T, R)] != 'exact' or status[(20, R)] != 'exact'
        up = bool(rat - 1. >= MOVE_BAR)
        excl = bool(lo > 1.)
        mv = up and excl
        a3['ratio'][f'R{R}_T{T}'] = dict(ratio=rat, lo=lo, hi=hi, up_ge_bar=up, ci_lo_gt_1=excl, ci_hi_lt_1=bool(hi < 1.), moves=mv, censored_point=cens,
                                          n_boot_censored=int(sum(1 for a, b in zip(bstat[(T, R)], bstat[(20, R)]) if a != 'exact' or b != 'exact')))
        md.append(f"| {R} | {T} | {rat:.3f} | [{lo:.3f}, {hi:.3f}] | {'Y' if up else 'N'} | {'Y' if excl else 'N'} | {'**Y**' if (mv and T == 80) else ('Y' if mv else 'N')} | "
                  f"{'point ' + status[(T, R)] + '/' + status[(20, R)] if cens else ''}{' boot ' + str(a3['ratio'][f'R{R}_T{T}']['n_boot_censored']) if a3['ratio'][f'R{R}_T{T}']['n_boot_censored'] else ''} |")
        if T == 80 and mv:
            moves.append(R)
a3['moves_cliff_at_R'] = moves
a3['moves_cliff'] = bool(moves)
a3['r1_shift_80_le_6pct'] = bool(point[(80, 1)] / point[(20, 1)] - 1. <= 0.06)
res['IB_3'] = a3
md += ['', f"**The inner budget {'MOVES' if moves else 'does NOT move'} the cliff** (rule: T = 80 vs 20, ratio - 1 >= .05 and CI lower end > 1; rounds: {moves or 'none'}).  "
           f"Stated expectation (R1 shift <= 6%): Kc_1(80)/Kc_1(20) - 1 = {point[(80, 1)] / point[(20, 1)] - 1.:+.3f} -> {'holds' if a3['r1_shift_80_le_6pct'] else 'violated'}.", '']

# ================================================================================ report-only
rep = dict(fer={}, mean_I={}, seconds={}, eps_det_median={}, eps_det4_ratio={})
md += ['## Report-only', '', '### FER by round (ierr_R > 0) and mean I_R = 1 - ll_in_R, by T and L', '',
       '| T | L | FER r1 | r2 | r3 | r4 | I r1 | r2 | r3 | r4 |', '|---|---|---|---|---|---|---|---|---|---|']
for T in TS:
    for L in LS:
        fer = [float(fail[(T, L)][:, r].mean()) for r in range(RMAX)]
        mi = [float(np.mean(1. - col(T, L, f'll_in{r}'))) for r in range(1, RMAX + 1)]
        rep['fer'][f'T{T}_L{L}'] = [dict(fer=fer[r], wilson=wilson(int(fail[(T, L)][:, r].sum()), len(common))) for r in range(RMAX)]
        rep['mean_I'][f'T{T}_L{L}'] = mi
        md.append(f'| {T} | {L} | ' + ' | '.join(f'{x:.3f}' for x in fer) + ' | ' + ' | '.join(f'{x:.4f}' for x in mi) + ' |')
md += ['', '### Cost per row (4 rounds, one frame at one L): mean seconds.  T = 20 from the stored c1i run (100 shards) and from the IB_T20 re-run (frames 0-29, 30 shards); '
            'T = 40/80 from this run.  Ratios use the re-run T = 20 on its frames 0-29 (same code, closest load); shard counts differ, so the ratios carry a load caveat.', '',
       '| L | T20 (c1i) | T20 (re-run, f0-29) | T40 (f0-29) | T80 (f0-29) | T40/T20 | T80/T20 | T40 (all) | T80 (all) |', '|---|---|---|---|---|---|---|---|---|']
det_frames = sorted({f for (_, f) in det})
for L in LS:
    s = {T: float(np.mean([tabs[T][(L, f)]['seconds'] for f in common])) for T in TS}
    sub = {T: float(np.mean([tabs[T][(L, f)]['seconds'] for f in det_frames if f in common])) for T in (40, 80)} if det_frames else {}
    sd = [r['seconds'] for (l, f), r in det.items() if l == L]
    sd = float(np.mean(sd)) if sd else None
    rep['seconds'][f'L{L}'] = dict(T20_c1i=s[20], T20_rerun=sd, T40_all=s[40], T80_all=s[80], T40_det_frames=sub.get(40), T80_det_frames=sub.get(80))
    r40 = None if not sd or not sub else sub[40] / sd
    r80 = None if not sd or not sub else sub[80] / sd
    md.append(f"| {L} | {s[20]:.2f} | {fnum(sd, 2)} | {fnum(sub.get(40), 2)} | {fnum(sub.get(80), 2)} | {fnum(r40, 2)} | {fnum(r80, 2)} | {s[40]:.2f} | {s[80]:.2f} |")
tot = {T: float(sum(tabs[T][(L, f)]['seconds'] for L in LS for f in common)) for T in TS}
rep['seconds_total_cpu'] = tot
md += ['', 'Total row seconds over L x frames: ' + ', '.join(f'T{T} {tot[T] / 3600:.2f} CPU-h' for T in TS), '',
       '### eps_det by round: median over frames, and median per-frame eps_det_r(T) / eps_det_r(20)', '',
       '| L | T | eps_det1 | eps_det2 | eps_det3 | eps_det4 | ratio r1 | r2 | r3 | r4 |', '|---|---|---|---|---|---|---|---|---|---|']
for L in LS:
    for T in TS:
        med = [float(np.median(col(T, L, f'eps_det{r}'))) for r in range(1, RMAX + 1)]
        rat = [float(np.median(col(T, L, f'eps_det{r}') / col(20, L, f'eps_det{r}'))) for r in range(1, RMAX + 1)]
        rep['eps_det_median'][f'L{L}_T{T}'] = dict(median=med, ratio_vs_T20=rat)
        md.append(f'| {L} | {T} | ' + ' | '.join(f'{x:.4f}' for x in med) + ' | ' + ' | '.join(f'{x:.3f}' for x in rat) + ' |')
res['report_only'] = rep
md.append('')
res['summary'] = dict(IB_0=a0['pass'], IB_1=a1['pass'], IB_2=a2['pass'], IB_3_moves_cliff=a3['moves_cliff'], IB_3_moves_at_R=moves)
md = [md[0], '', 'Summary: ' + ', '.join(f'{k} {v}' for k, v in res['summary'].items())] + md[1:]

OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'ib.json').write_text(json.dumps(res, indent=1, default=float) + '\n')
(OUT / 'ib.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
