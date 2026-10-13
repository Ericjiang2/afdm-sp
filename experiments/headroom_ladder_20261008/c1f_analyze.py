#!/usr/bin/env python
"""Analysis of the A4 fold / bistability batch (research/c1-scalar-closure.md, Amendment A4).  Reads rows and JSON only.
    python -B c1f_analyze.py [--exit-dir out/c1f_exit] [--r10-dir out/c1f_r10] [--c1i-dir out/c1i]
                             [--phi out/c1f/analysis/exit/c1e_phi.json] [--frozen out/c1f/predictions_frozen.json]
                             [--t1 out/c1_t1/t1_transfer.json] [--out out/c1f/analysis]
Outputs <out>/c1f.json (with _argv, _config) and <out>/c1f.md.  No frozen file, c1e_predict.py or receiver code is modified.

A4-0 determinism  FULL_R10 (L24, frames 0-299) rounds 1-4 vs stored c1i FULL_R4 rows: cerr_r, ierr_r, dsha_r, ll_in_r (exact).
A4-1 tunnel       D(Ir) = mean(mi_in1) - Ir per (L, Ir), percentile frame bootstrap (B = 2000, seed 20261009, same RNG order as
                  c1e_analyze.py, so the cell CIs reproduce c1e_phi.json); min over Ir in [.42,.57] (cell CI at the argmin and the
                  frame-paired bootstrap CI of the min statistic); closed = upper CI < 0, open = lower CI > 0.
A4-2 bistability  c1e_predict.load_phi / fixed_points on the new dense map (Phi(0) := Phi(none)); CI-robust closed / escape flags.
A4-3 trajectories FULL_R10: FER by round (frame fails iff ierr_r > 0; Wilson), frame-mean MI_r = mean(1 - ll_in_r) (bootstrap),
                  plateau, comparison with the stable fixed point, MI_10 histogram, still-rising fraction, mean eps_ce / eps_det.
Kc by round       FER(R) = .5 crossing in K = 8 L (linear in K), c1i FULL_R4 (L 8-20, frames 0-299, rounds 1-4) + FULL_R10
                  (L 24/28/32), vs predictions_frozen kc_by_round.
Staircase         c1e_predict.staircase on the dense map (10 rounds) next to the observed frame-mean MI_r.
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

import c1e_predict as E

HERE = Path(__file__).resolve().parent
B, SEED = 2000, 20261009
SNR_CD, RHO_PM = 650, 300
IR_LO, IR_HI = 0.42, 0.57  # min / closed range of the pre-registration
KC_BAR = 0.15

ap = argparse.ArgumentParser()
ap.add_argument('--exit-dir', default='out/c1f_exit')
ap.add_argument('--r10-dir', default='out/c1f_r10')
ap.add_argument('--c1i-dir', default='out/c1i')
ap.add_argument('--phi', default='out/c1f/analysis/exit/c1e_phi.json')
ap.add_argument('--frozen', default='out/c1f/predictions_frozen.json')
ap.add_argument('--t1', default='out/c1_t1/t1_transfer.json')
ap.add_argument('--out', default='out/c1f/analysis')
args = ap.parse_args()
P = lambda s: (HERE / s) if not Path(s).is_absolute() else Path(s)


def load_rows(d):
    rows = []
    for f in sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl'))):
        for x in open(f):
            if x.strip():
                rows.append(json.loads(x))
    return rows


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def pct(x):
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def fmt(m, lo, hi, d=3):
    return f'{m:+.{d}f} [{lo:+.{d}f},{hi:+.{d}f}]'


I_STAR = float(json.loads(P(args.t1).read_text())['exit']['I_in_at_crossings']['FER0.5_linear']['I_in'])
FROZEN = json.loads(P(args.frozen).read_text())
res = dict(_argv=sys.argv, _config=dict(
    B=B, seed=SEED, I_star=I_STAR, snr_centi_db=SNR_CD, rho_permille=RHO_PM, ir_range=[IR_LO, IR_HI], kc_bar_ln=KC_BAR,
    dirs=dict(exit=args.exit_dir, r10=args.r10_dir, c1i=args.c1i_dir, phi=args.phi, frozen=args.frozen, t1=args.t1),
    md5=dict(phi=md5(P(args.phi)), frozen=md5(P(args.frozen)), t1=md5(P(args.t1)), c1e_predict=md5(HERE / 'c1e_predict.py'))))
md = ['# A4 fold / bistability analysis (6.5 dB, rho .3)', '',
      f'I* (T1 EXIT, FER .5 linear) = {I_STAR:.4f}.  Bootstrap: percentile, frame resample, B = {B}, seed {SEED}.', '']

# =========================================================================================== A4-0 determinism
r10_rows = load_rows(args.r10_dir)
r10_ok = [r for r in r10_rows if r['status'] == 'ok']
c1i_rows = load_rows(args.c1i_dir)
res['rows'] = dict(r10=len(r10_rows), r10_error=len(r10_rows) - len(r10_ok), c1i=len(c1i_rows))
stored = {(r['L'], r['frame']): r for r in c1i_rows
          if r['status'] == 'ok' and r['arm'] == 'FULL_R4' and r['snr_centi_db'] == SNR_CD and r['rho_permille'] == RHO_PM}
new24 = {r['frame']: r for r in r10_ok if r['L'] == 24 and r['snr_centi_db'] == SNR_CD and r['rho_permille'] == RHO_PM}
a0 = dict(n_new=len(new24), n_missing_in_c1i=0, fields={})
for fld in ('cerr', 'ierr', 'dsha', 'll_in'):
    for r in range(1, 5):
        a0['fields'][f'{fld}{r}'] = dict(n=0, mismatch=0, max_abs_diff=0.0 if fld == 'll_in' else None)
frame_bad = set()
for fr, n in sorted(new24.items()):
    if fr >= 300:
        continue
    s = stored.get((24, fr))
    if s is None:
        a0['n_missing_in_c1i'] += 1
        continue
    for fld in ('cerr', 'ierr', 'dsha', 'll_in'):
        for r in range(1, 5):
            e = a0['fields'][f'{fld}{r}']
            e['n'] += 1
            a, b = n[f'{fld}{r}'], s[f'{fld}{r}']
            if a != b:
                e['mismatch'] += 1
                frame_bad.add(fr)
            if fld == 'll_in':
                e['max_abs_diff'] = max(e['max_abs_diff'], abs(float(a) - float(b)))
a0['n_frames_compared'] = a0['fields']['cerr1']['n']
a0['n_frames_with_any_mismatch'] = len(frame_bad)
a0['total_mismatch'] = sum(e['mismatch'] for e in a0['fields'].values())
a0['mismatch_frames_first10'] = sorted(frame_bad)[:10]
res['A4_0'] = a0
md += ['## A4-0 determinism (FULL_R10 L24 frames 0-299 rounds 1-4 vs stored c1i FULL_R4)', '',
       f"frames compared {a0['n_frames_compared']}, missing in c1i {a0['n_missing_in_c1i']}, total field mismatches {a0['total_mismatch']}, "
       f"frames with any mismatch {a0['n_frames_with_any_mismatch']}", '',
       '| round | cerr mism | ierr mism | dsha mism | ll_in mism | ll_in max abs diff |', '|---|---|---|---|---|---|']
for r in range(1, 5):
    f = a0['fields']
    md.append(f"| {r} | {f[f'cerr{r}']['mismatch']} | {f[f'ierr{r}']['mismatch']} | {f[f'dsha{r}']['mismatch']} | "
              f"{f[f'll_in{r}']['mismatch']} | {f[f'll_in{r}']['max_abs_diff']:.3e} |")
md.append('')

# =========================================================================================== A4-1 tunnel
exit_rows = load_rows(args.exit_dir)
exit_ok = [r for r in exit_rows if r['status'] == 'ok' and r['snr_centi_db'] == SNR_CD and r['rho_permille'] == RHO_PM]
res['rows']['exit'] = len(exit_rows)
res['rows']['exit_error'] = len(exit_rows) - len([r for r in exit_rows if r['status'] == 'ok'])
cells = {}
for r in exit_ok:
    cells.setdefault((r['L'], None if r['Ir'] is None else round(float(r['Ir']), 2)), {})[r['frame']] = float(r['mi_in1'])
Ls_exit = sorted({k[0] for k in cells})
rng = np.random.default_rng(SEED)  # same consumption order as c1e_analyze.py (L, then none, then Ir ascending)
tun = {}
cell_ci = {}
for L in Ls_exit:
    irs = sorted(k[1] for k in cells if k[0] == L and k[1] is not None)
    for ir in [None] + irs:
        d = cells[(L, ir)]
        fr = sorted(d)
        x = np.array([d[f] for f in fr])
        idx = rng.integers(0, len(x), size=(B, len(x)))
        lo, hi = pct(x[idx].mean(axis=1))
        cell_ci[(L, ir)] = (float(x.mean()), lo, hi, len(x))
phi_json = json.loads(P(args.phi).read_text())['Phi']['6.5']
res['phi_json_check_max_abs'] = float(max(
    max(abs(cell_ci[(L, ir)][j] - phi_json[f'L{L}']['none' if ir is None else f'{ir:.2f}']['mi_in1'][k]) for j, k in enumerate(('mean', 'lo', 'hi')))
    for (L, ir) in cell_ci))
A1 = {}
md += ['## A4-1 tunnel: D(Ir) = mean(mi_in1) - Ir, mean [95% CI]', '',
       f"(cell CIs reproduce c1e_phi.json: max abs difference {res['phi_json_check_max_abs']:.2e})", '']
for L in Ls_exit:
    irs = sorted(k[1] for k in cells if k[0] == L and k[1] is not None)
    frames = sorted(set.intersection(*[set(cells[(L, ir)]) for ir in irs]))
    M = np.array([[cells[(L, ir)][f] for ir in irs] for f in frames])
    prng = np.random.default_rng(SEED)
    idx = prng.integers(0, len(frames), size=(B, len(frames)))
    means = M[idx].mean(axis=1)  # (B, nIr), frame-paired across Ir
    Dm = {ir: cell_ci[(L, ir)][0] - ir for ir in irs}
    D = {f'{ir:.2f}': dict(mean=Dm[ir], lo=cell_ci[(L, ir)][1] - ir, hi=cell_ci[(L, ir)][2] - ir, n=cell_ci[(L, ir)][3]) for ir in irs}
    rng_irs = [ir for ir in irs if IR_LO - 1e-9 <= ir <= IR_HI + 1e-9]
    cols = [irs.index(ir) for ir in rng_irs]
    mins = (means[:, cols] - np.array(rng_irs)).min(axis=1)
    ia = min(rng_irs, key=lambda ir: Dm[ir])
    mlo, mhi = pct(mins)
    scan = [ir for ir in irs if ir <= 0.58 + 1e-9]
    closed = [ir for ir in scan if D[f'{ir:.2f}']['hi'] < 0]
    opened = [ir for ir in scan if D[f'{ir:.2f}']['lo'] > 0]
    none = cell_ci[(L, None)]
    A1[f'L{L}'] = dict(
        n_frames=len(frames), phi_none=dict(mean=none[0], lo=none[1], hi=none[2]), D=D,
        min_D_cell=dict(Ir=ia, **{k: D[f'{ia:.2f}'][k] for k in ('mean', 'lo', 'hi')}),
        min_D_stat=dict(mean_of_min=float(mins.mean()), lo=mlo, hi=mhi, point=float(min(Dm[ir] for ir in rng_irs))),
        closed_Ir=closed, open_Ir=opened,
        paired_cell_ci_check_max_abs=float(max(abs(pct(means[:, irs.index(ir)])[0] - cell_ci[(L, ir)][1]) for ir in irs)))
    md += [f'### L{L} (K = {8 * L}, n = {len(frames)}); Phi(none) = {none[0]:.4f} [{none[1]:.4f},{none[2]:.4f}]', '',
           '| Ir | Phi mean | D mean [CI] | closed (hi<0) | open (lo>0) |', '|---|---|---|---|---|']
    for ir in irs:
        e = D[f'{ir:.2f}']
        md.append(f"| {ir:.2f} | {e['mean'] + ir:.4f} | {fmt(e['mean'], e['lo'], e['hi'])} | "
                  f"{'Y' if e['hi'] < 0 else ''} | {'Y' if e['lo'] > 0 else ''} |")
    m1, m2 = A1[f'L{L}']['min_D_cell'], A1[f'L{L}']['min_D_stat']
    md += ['', f"min D over Ir in [.42,.57]: argmin Ir {m1['Ir']:.2f}, D {fmt(m1['mean'], m1['lo'], m1['hi'])} (cell CI); "
               f"min-statistic paired-bootstrap CI [{m2['lo']:+.3f},{m2['hi']:+.3f}] (point {m2['point']:+.3f}).  "
               f"closed Ir (<= .58): {closed}; open Ir (<= .58): {opened}", '']
chk = {28: lambda a: not (a['min_D_cell']['lo'] > 0),
       32: lambda a: bool(a['closed_Ir']), 36: lambda a: bool(a['closed_Ir'])}
for L, fn in chk.items():
    if f'L{L}' in A1:
        A1[f'L{L}']['prereg_pass'] = bool(fn(A1[f'L{L}']))
res['A4_1'] = A1
md.append('A4-1 pre-registered pass (L28: argmin cell CI not entirely above 0; L32/L36: some Ir with upper CI < 0): '
          + ', '.join(f"L{L} {A1[f'L{L}']['prereg_pass']}" for L in chk if f'L{L}' in A1) + '')
md.append('')

# =========================================================================================== A4-2 bistability + staircase
phi_all = E.load_phi(P(args.phi))[6.5]
A2, stair = {}, {}
md += ['## A4-2 bistability of the dense map (frozen c1e_predict rule; Phi(0) := Phi(none))', '']
for L in sorted(phi_all):
    grid, ph, none = phi_all[L]
    fps, bistable = E.fixed_points(grid, ph, I_STAR)
    traj, best, first = E.staircase(grid, ph, I_STAR, rounds=10)
    unst = [p for p in fps if not p['stable'] and p['below_I_star']]
    fp_u = max((p['I'] for p in unst), default=None)
    irs = [float(g) for g in grid[1:]]
    Dd = A1[f'L{L}']['D']
    closed_rng = [ir for ir in irs if IR_LO - 1e-9 <= ir <= IR_HI + 1e-9 and Dd[f'{ir:.2f}']['hi'] < 0]
    esc = [] if fp_u is None else [ir for ir in irs if ir > fp_u + 1e-12 and ir <= I_STAR and Dd[f'{ir:.2f}']['lo'] > 0]
    far = {f'{ir:.2f}': Dd[f'{ir:.2f}'] for ir in (0.58, 0.60, 0.62, 0.65) if f'{ir:.2f}' in Dd}
    A2[f'L{L}'] = dict(fixed_points=fps, bistable_point=bistable, highest_unstable_FP_below_Istar=fp_u,
                       closed_Ir_in_range=closed_rng, escape_Ir=esc, ci_robust_bistable=bool(closed_rng and esc),
                       single_trapping_state=bool(fp_u is None and not any(p['stable'] and not p['below_I_star'] for p in fps)),
                       D_far=far)
    stair[f'L{L}'] = dict(K=8 * L, traj=traj, first_success_round=first)
    md += [f'### L{L}: fixed points ' + (', '.join(f"I={p['I']:.4f} slope {p['slope']:.3f} {'stable' if p['stable'] else 'unstable'}"
                                                   f"{'' if p['below_I_star'] else ' (above I*)'}" for p in fps) or 'none'),
           f"bistable (point, frozen rule) = {bistable}; closed Ir in [.42,.57] (upper CI<0) = {closed_rng}; "
           f"escape Ir ({'above highest unstable FP ' + format(fp_u, '.4f') if fp_u is not None else 'no unstable FP below I*'}"
           f", <= .577; lower CI>0) = {esc}; CI-robust bistable = {bool(closed_rng and esc)}",
           'D at far Ir: ' + '; '.join(f"{k} {fmt(v['mean'], v['lo'], v['hi'])}" for k, v in far.items()), '']
res['A4_2'] = A2
res['staircase_dense'] = stair

# =========================================================================================== A4-3 trajectories
R = 10
by_L = {}
for r in r10_ok:
    if r['snr_centi_db'] == SNR_CD and r['rho_permille'] == RHO_PM:
        by_L.setdefault(r['L'], []).append(r)
A3 = {}
md += ['## A4-3 FULL_R10 trajectories', '']
mi_rng = np.random.default_rng(SEED)
for L in sorted(by_L):
    rs = sorted(by_L[L], key=lambda x: x['frame'])
    n = len(rs)
    ierr = np.array([[x[f'ierr{r}'] for r in range(1, R + 1)] for x in rs])
    fail = ierr > 0
    mi = np.array([[1. - x[f'll_in{r}'] for r in range(1, R + 1)] for x in rs])
    idx = mi_rng.integers(0, n, size=(B, n))
    mbs = mi[idx].mean(axis=1)
    fer = [dict(r=r, fer=float(fail[:, r - 1].mean()), ci=wilson(int(fail[:, r - 1].sum()), n)) for r in range(1, R + 1)]
    mi_stat = [dict(r=r, mean=float(mi[:, r - 1].mean()), ci=pct(mbs[:, r - 1])) for r in range(1, R + 1)]
    plateau = float(abs(mi[:, 9].mean() - mi[:, 7].mean()))
    still10 = fail[:, 9]
    rise = mi[:, 9] - mi[:, 7]
    edges = np.arange(0.30, 0.90 + 1e-9, 0.02)
    hist = np.histogram(np.clip(mi[:, 9], edges[0], edges[-1] - 1e-9), bins=edges)[0].tolist()
    nonabs = int(sum(1 for i in range(n) for r in range(R - 1) if (not fail[i, r]) and fail[i, r + 1]))
    e = dict(n=n, fer=fer, mi=mi_stat, plateau_abs_MI10_minus_MI8=plateau, n_fail_round10=int(still10.sum()),
             MI10_failing_mean=float(mi[still10, 9].mean()) if still10.any() else None,
             MI10_all_mean=float(mi[:, 9].mean()), frac_rising_gt_0p01_all=float((rise > 0.01).mean()),
             frac_rising_gt_0p01_failing=float((rise[still10] > 0.01).mean()) if still10.any() else None,
             frac_MI10_below_Istar=float((mi[:, 9] < I_STAR).mean()), frac_MI10_ge_Istar=float((mi[:, 9] >= I_STAR).mean()),
             hist_edges=[round(float(x), 2) for x in edges], hist_MI10=hist, nonabsorbing_success_events=nonabs,
             eps_ce_mean=[float(np.mean([x[f'eps_ce{r}'] for x in rs])) for r in range(1, R + 1)],
             eps_det_mean=[float(np.mean([x[f'eps_det{r}'] for x in rs])) for r in range(1, R + 1)],
             nan_count=int(np.isnan(mi).sum()))
    sc = stair.get(f'L{L}')
    fp = A2.get(f'L{L}', {}).get('fixed_points')
    stable = [p for p in (fp or []) if p['stable'] and p['below_I_star']]
    if stable:
        s0 = stable[0]['I']
        e['stable_FP'] = s0
        e['MI10_all_minus_FP'] = e['MI10_all_mean'] - s0
        e['MI10_failing_minus_FP'] = None if e['MI10_failing_mean'] is None else e['MI10_failing_mean'] - s0
    e['staircase_dense_traj'] = None if sc is None else sc['traj']
    e['frozen_traj'] = FROZEN['cells'].get(f'L{L}', {}).get('traj')
    A3[f'L{L}'] = e
    md += [f'### L{L} (n = {n})', '', '| r | FER [Wilson] | MI_r [boot CI] | stair dense | stair frozen | mean eps_ce | mean eps_det |', '|---|---|---|---|---|---|---|']
    for r in range(R):
        md.append(f"| {r + 1} | {fer[r]['fer']:.3f} [{fer[r]['ci'][0]:.3f},{fer[r]['ci'][1]:.3f}] | "
                  f"{mi_stat[r]['mean']:.4f} [{mi_stat[r]['ci'][0]:.4f},{mi_stat[r]['ci'][1]:.4f}] | "
                  f"{'' if sc is None else format(sc['traj'][r], '.4f')} | "
                  f"{'' if not e['frozen_traj'] else format(e['frozen_traj'][r], '.4f')} | {e['eps_ce_mean'][r]:.4f} | {e['eps_det_mean'][r]:.4f} |")
    md += ['', f"plateau |MI_10 - MI_8| = {plateau:.4f}; FER_R10 = {fer[-1]['fer']:.3f}; frames failing at r10 = {e['n_fail_round10']}; "
               f"MI_10 all = {e['MI10_all_mean']:.4f}, failing-only = {e['MI10_failing_mean']}; "
               + (f"stable FP (dense map) = {e['stable_FP']:.4f}, MI_10(all) - FP = {e['MI10_all_minus_FP']:+.4f}, "
                  f"MI_10(failing) - FP = {e['MI10_failing_minus_FP']}; " if stable else 'no stable FP in the dense map for this L; ')
               + f"fraction rising > .01 between r8 and r10: all {e['frac_rising_gt_0p01_all']:.3f}, failing {e['frac_rising_gt_0p01_failing']}; "
               f"MI_10 < I*: {e['frac_MI10_below_Istar']:.3f}; non-absorbing success events {nonabs}; NaN {e['nan_count']}", '',
           'MI_10 histogram (bin .02 from .30): ' + ' '.join(f'{a:.2f}:{c}' for a, c in zip(edges[:-1], hist) if c), '']
res['A4_3'] = A3

# =========================================================================================== Kc by round
fer_tab = {}  # L -> ierr>0 matrix (frames 0-299)
for L in sorted({k[0] for k in stored}):
    if L in (8, 12, 16, 20):
        fr = sorted(f for (l, f) in stored if l == L and f < 300)
        fer_tab[L] = np.array([[stored[(L, f)][f'ierr{r}'] > 0 for r in range(1, 5)] for f in fr])
for L in sorted(by_L):
    fer_tab[L] = np.array([[x[f'ierr{r}'] > 0 for r in range(1, R + 1)] for x in sorted(by_L[L], key=lambda x: x['frame']) if x['frame'] < 300])


def kc_of(ferL, Rr, allow_anchor=True):
    Ls = [L for L in sorted(ferL) if ferL[L].shape[1] >= Rr]
    Ks, ys = [8 * L for L in Ls], [float(ferL[L][:, Rr - 1].mean()) for L in Ls]
    note = ''
    if Rr >= 5 and allow_anchor and 20 in ferL and ys and ys[0] >= 0.5:
        Ks, ys = [160] + Ks, [float(ferL[20][:, 3].mean())] + ys
        note = 'L20 at its R4 value used as lower anchor'
    k = E.k_cross(Ks, ys, 0.5)
    if k is None:
        note = (note + '; ' if note else '') + ('FER < .5 at the largest L (Kc above range)' if ys and ys[-1] < 0.5 else 'FER > .5 at all L (Kc below range)')
    return k, Ks, ys, note


kb = np.random.default_rng(SEED)
boot_idx = {L: kb.integers(0, v.shape[0], size=(B, v.shape[0])) for L, v in sorted(fer_tab.items())}
kc = {}
md += ['## Kc by round (FER(R) = .5 crossing in K = 8 L, linear in K)', '',
       '| R | Kc obs | frozen pred | ln(pred/obs) | within .15 | boot 95% [n valid/B] | L: FER |', '|---|---|---|---|---|---|---|']
for Rr in range(1, 11):
    k, Ks, ys, note = kc_of(fer_tab, Rr)
    pred = FROZEN['kc_by_round'][f'R{Rr}']
    ln = None if k is None else math.log(pred / k)
    ks = []
    for b in range(B):
        fb = {L: v[boot_idx[L][b]] for L, v in fer_tab.items()}
        kb_, *_ = kc_of(fb, Rr)
        if kb_ is not None:
            ks.append(kb_)
    k0 = ln0 = None  # sensitivity when the L20 R4 anchor is used: true FER_20(R>=5) <= FER_20(R4); bound it by FER_20 = 0
    if 'anchor' in note:
        k0 = E.k_cross([160] + Ks[1:], [0.] + ys[1:], 0.5)
        ln0 = None if k0 is None else math.log(pred / k0)
    kc[f'R{Rr}'] = dict(obs=k, pred=pred, ln_pred_over_obs=ln, within_bar=None if ln is None else bool(abs(ln) <= KC_BAR), note=note,
                        K=Ks, fer=ys, boot_n_valid=len(ks), boot_ci=pct(ks) if len(ks) > 20 else None,
                        obs_if_L20_FER_zero=k0, ln_if_L20_FER_zero=ln0)
    bc = kc[f'R{Rr}']['boot_ci']
    md.append(f"| {Rr} | {'-' if k is None else format(k, '.1f')} | {pred:.1f} | {'-' if ln is None else format(ln, '+.3f')} | "
              f"{'-' if ln is None else ('Y' if abs(ln) <= KC_BAR else 'N')} | "
              f"{'-' if bc is None else f'[{bc[0]:.1f},{bc[1]:.1f}]'} [{len(ks)}/{B}] | "
              + ' '.join(f"{K // 8}:{y:.3f}" for K, y in zip(Ks, ys)) + (f" ({note})" if note else '')
              + ('' if k0 is None else f"; sensitivity FER_20 := 0: Kc {k0:.1f}, ln {ln0:+.3f}") + ' |')
res['kc_by_round'] = kc
md.append('')

(P(args.out)).mkdir(parents=True, exist_ok=True)
(P(args.out) / 'c1f.json').write_text(json.dumps(res, indent=1, default=float) + '\n')
(P(args.out) / 'c1f.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
