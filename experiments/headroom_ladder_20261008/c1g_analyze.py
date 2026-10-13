#!/usr/bin/env python
"""Analysis of the A5 batch: per-frame maps, same-frame start dependence, long-run Kc (research/c1-scalar-closure.md, Amendment A5).
Reads rows and JSON only.
    python -B c1g_analyze.py [--exit-dir out/c1f_exit] [--r10-dir out/c1f_r10] [--c1i-dir out/c1i] [--lo-dir out/c1g_r10lo]
                             [--x-dir out/c1g_r10x] [--frozen out/c1f/predictions_frozen.json] [--t1 out/c1_t1/t1_transfer.json]
                             [--out out/c1g/analysis] [--allow-partial]
Outputs <out>/c1g.json (with _argv, _config), <out>/c1g.md, <out>/c1g_frames.csv.  No frozen file, c1e_predict.py or receiver code
is modified.  Without --allow-partial the script refuses to run unless every input dir has results.json, "merge ok" and "done" in
logs/lifecycle.txt and the expected row count (EXIT-D 11700, R10 900, c1i 6000, R10-LO 600, R10-X 600).

A5-0 determinism  clause 1: R10-X (FULL_R10, L28/32, frames 1000-1299) rounds 1-2 vs EXIT_none rounds 1-2 of EXIT-D, frame by frame
                  (cerr, ierr, ll_in exact; dsha reported separately).  clause 2: R10-LO (L16/20, frames 0-299) rounds 1-4 vs stored
                  c1i FULL_R4 (cerr, ierr, dsha, ll_in exact; A4-0 convention).  Failure voids A5-2 / A5-3.
A5-1 Kc by round  FER(R) (frame fails iff ierr_R > 0; Wilson) for L16-32 (R10-LO, R10) R1..R10 and c1i L8/12 R1..R4; Kc_R = FER .5
                  crossing in K = 8 L (linear in K; same code as c1f_analyze), vs frozen kc_by_round, |ln(pred/obs)| <= .15; A5 prediction
                  FER_R10(L20) in [.02,.43] and Kc_R10 in [172,186].
A5-2 per-frame    EXIT-D rows L28/32/36.  D_f(Ir) = mi_in1(Ir) - Ir on G = {.42,...,.56}.  O: D_f > 0 on all G; B: D_f(.56) > 0 and D_f < 0
                  somewhere on G; C: D_f(.56) <= 0 (X: leftover edge case, D_f(.56) > 0 with a zero and no negative).  u_f = highest
                  (- to +) crossing of D_f on G (linear).  Join with R10-X per frame (L28/32): decode-by-R10 (ierr10 == 0) rate per class
                  vs >= .8 (O) / <= .2 (B u C) (point estimate; a class with < 10 frames at an L is pooled over L28+L32).  M2: staircase
                  on the frame's own map (grid [0] + Ir grid, Phi_f(0) = EXIT_none mi_in1, 10 rounds, decoded by R iff first-success
                  round <= R) -> FER_M2(R) vs observed FER(R), |diff at R10| <= .06 at both L.  M0 = the same rule on the mean map.
A5-3 start dep.   R10-X frames failing at R10: share with >= 1 Ir in G having ierr2 == 0 (Wilson lower bound > .10 => start dependence
                  shown at that L).  Direction check, class B pairs (frame, Ir in G) with |Ir - u_f| >= .02: step 2 'up' iff
                  ierr1 == 0 or ierr2 == 0 or mi_in2 > mi_in1; agreement with sign(D_f(Ir)) >= .80 separately for Ir < u_f and Ir > u_f
                  (evaluated per L28 / L32; pooled and L36 shown for information).
Bootstrap: percentile, frame resample, B = 2000, seed 20261009 (Kc part: same RNG order as c1f_analyze.py).
"""
from __future__ import annotations

import argparse
import csv
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
KC_BAR = 0.15
G = [round(0.42 + 0.02 * i, 2) for i in range(8)]  # .42 ... .56 (all below I*)
M2_BAR = 0.06
O_MIN, BC_MAX, POOL_N = 0.8, 0.2, 10
START_LB = 0.10
DIR_GAP, DIR_BAR = 0.02, 0.80
FER20_BAND, KC10_BAND = (0.02, 0.43), (172., 186.)
R = 10

ap = argparse.ArgumentParser()
ap.add_argument('--exit-dir', default='out/c1f_exit')
ap.add_argument('--r10-dir', default='out/c1f_r10')
ap.add_argument('--c1i-dir', default='out/c1i')
ap.add_argument('--lo-dir', default='out/c1g_r10lo')
ap.add_argument('--x-dir', default='out/c1g_r10x')
ap.add_argument('--frozen', default='out/c1f/predictions_frozen.json')
ap.add_argument('--t1', default='out/c1_t1/t1_transfer.json')
ap.add_argument('--out', default='out/c1g/analysis')
ap.add_argument('--allow-partial', action='store_true', help='smoke runs only: do not require finished/merged inputs')
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


def dir_fp(d):
    fs = sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl')))
    return dict(n_files=len(fs), md5_of_shard_md5s=hashlib.md5(''.join(md5(f) for f in fs).encode()).hexdigest())


def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def pct(x):
    return float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))


def fmt(m, lo, hi, d=3):
    return f'{m:+.{d}f} [{lo:+.{d}f},{hi:+.{d}f}]'


def rate(k, n, d=3):
    if n == 0:
        return 'n/a (0)'
    lo, hi = wilson(k, n)
    return f'{k / n:.{d}f} [{lo:.{d}f},{hi:.{d}f}] ({k}/{n})'


def _j(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(type(o))


I_STAR = float(json.loads(P(args.t1).read_text())['exit']['I_in_at_crossings']['FER0.5_linear']['I_in'])
FROZEN = json.loads(P(args.frozen).read_text())
DIRS = dict(exit=args.exit_dir, r10=args.r10_dir, c1i=args.c1i_dir, lo=args.lo_dir, x=args.x_dir)
EXPECT = dict(exit=11700, r10=900, c1i=6000, lo=600, x=600)

# ------------------------------------------------------------------------------------------------ load + completeness gate
ROWS = {k: load_rows(d) for k, d in DIRS.items()}
runstate, problems = {}, []
for k, d in DIRS.items():
    lc = P(d) / 'logs' / 'lifecycle.txt'
    lines = [x.strip() for x in lc.read_text().splitlines()] if lc.exists() else []
    st = dict(results_json=(P(d) / 'results.json').exists(), merge_ok='merge ok' in lines, done='done' in lines,
              n_rows=len(ROWS[k]), n_expected=EXPECT[k], n_error=sum(1 for r in ROWS[k] if r['status'] != 'ok'))
    runstate[k] = st
    if not (st['results_json'] and st['merge_ok'] and st['done']):
        problems.append(f"{k} ({d}): results.json={st['results_json']} merge_ok={st['merge_ok']} done={st['done']}")
    if st['n_rows'] != st['n_expected']:
        problems.append(f"{k} ({d}): {st['n_rows']} rows, expected {st['n_expected']}")
if problems:
    msg = 'INPUT NOT COMPLETE: ' + ' | '.join(problems)
    if not args.allow_partial:
        sys.exit('FAIL: ' + msg + '  (use --allow-partial for a smoke run)')
    print('WARNING (--allow-partial): ' + msg, file=sys.stderr)

res = dict(_argv=sys.argv, _config=dict(
    B=B, seed=SEED, I_star=I_STAR, snr_centi_db=SNR_CD, rho_permille=RHO_PM, G=G, kc_bar_ln=KC_BAR, m2_bar=M2_BAR,
    class_O_min=O_MIN, class_BC_max=BC_MAX, pool_n=POOL_N, start_lb=START_LB, dir_gap=DIR_GAP, dir_bar=DIR_BAR,
    fer20_band=FER20_BAND, kc10_band=KC10_BAND, rounds=R, allow_partial=bool(args.allow_partial),
    dirs=DIRS, row_fingerprint={k: dir_fp(d) for k, d in DIRS.items()},
    md5=dict(frozen=md5(P(args.frozen)), t1=md5(P(args.t1)), c1e_predict=md5(HERE / 'c1e_predict.py'),
             c1g_analyze=md5(HERE / 'c1g_analyze.py'))), runstate=runstate, partial_problems=problems)
md = ['# A5 per-frame maps / start dependence / long-run Kc (6.5 dB, rho .3)', '',
      f'I* (T1 EXIT, FER .5 linear) = {I_STAR:.4f}.  G = {G}.  Bootstrap: percentile, frame resample, B = {B}, seed {SEED}.', '']
if problems:
    md += ['**PARTIAL INPUT (smoke run, not a result): ' + ' | '.join(problems) + '**', '']
md += ['Row counts / errors: ' + '; '.join(f"{k} {v['n_rows']} rows ({v['n_error']} error)" for k, v in runstate.items()), '']
V = []  # verdict lines

okf = lambda r: r['status'] == 'ok' and r['snr_centi_db'] == SNR_CD and r['rho_permille'] == RHO_PM
exit_ok = [r for r in ROWS['exit'] if okf(r)]
r10_ok = [r for r in ROWS['r10'] if okf(r) and r['arm'] == 'FULL_R10']
lo_ok = [r for r in ROWS['lo'] if okf(r) and r['arm'] == 'FULL_R10']
x_ok = [r for r in ROWS['x'] if okf(r) and r['arm'] == 'FULL_R10']
c1i_ok = [r for r in ROWS['c1i'] if okf(r) and r['arm'] == 'FULL_R4' and r['frame'] < 300]
stored = {(r['L'], r['frame']): r for r in c1i_ok}
xo = {(r['L'], r['frame']): r for r in x_ok}
lo_by = {(r['L'], r['frame']): r for r in lo_ok}
none_rows = {(r['L'], r['frame']): r for r in exit_ok if r['arm'] == 'EXIT_none'}
res['rows_ok'] = dict(exit=len(exit_ok), r10=len(r10_ok), lo=len(lo_ok), x=len(x_ok), c1i_full_r4_frames_lt300=len(c1i_ok))


# ================================================================================================ A5-0 determinism
def compare(new, ref, fields, rounds):
    st = {f'{f}{r}': dict(n=0, mismatch=0, max_abs_diff=0.0 if f == 'll_in' else None) for f in fields for r in rounds}
    bad, missing = set(), []
    for k, n in sorted(new.items()):
        s = ref.get(k)
        if s is None:
            missing.append(k)
            continue
        for f in fields:
            for r in rounds:
                e = st[f'{f}{r}']
                e['n'] += 1
                a, b = n[f'{f}{r}'], s[f'{f}{r}']
                if a != b:
                    e['mismatch'] += 1
                    bad.add(k)
                if f == 'll_in':
                    e['max_abs_diff'] = max(e['max_abs_diff'], abs(float(a) - float(b)))
    return st, bad, missing


a0 = {}
md += ['## A5-0 determinism', '']
for name, new, ref, fields, rounds, tag in (
        ('clause1', xo, none_rows, ('cerr', 'ierr', 'll_in'), (1, 2), 'R10-X (L28/32, frames 1000-1299) rounds 1-2 vs EXIT_none rounds 1-2'),
        ('clause2', lo_by, stored, ('cerr', 'ierr', 'dsha', 'll_in'), (1, 2, 3, 4), 'R10-LO (L16/20, frames 0-299) rounds 1-4 vs stored c1i FULL_R4')):
    st, bad, missing = compare(new, ref, fields, rounds)
    tot = sum(e['mismatch'] for e in st.values())
    mx = max(e['max_abs_diff'] for e in st.values() if e['max_abs_diff'] is not None)
    ncmp = st[f'{fields[0]}{rounds[0]}']['n']
    e = dict(desc=tag, fields=st, n_frames_compared=ncmp, n_missing_in_ref=len(missing), total_mismatch=tot,
             n_frames_with_any_mismatch=len(bad), mismatch_frames_first10=sorted(bad)[:10], ll_in_max_abs_diff=mx)
    if name == 'clause1':  # dsha: report-only (different drivers)
        sd, badd, _ = compare(new, ref, ('dsha',), rounds)
        e['dsha_report_only'] = dict(fields=sd, total_mismatch=sum(v['mismatch'] for v in sd.values()), n_frames_with_any_mismatch=len(badd))
    a0[name] = e
    md += [f'### {name}: {tag}', '',
           f"frames compared {ncmp}, missing in reference {len(missing)}, total field mismatches {tot} (fields {', '.join(fields)}), "
           f"frames with any mismatch {len(bad)}, ll_in max abs diff {mx:.3e}"
           + (f"; dsha (report-only): {e['dsha_report_only']['total_mismatch']} mismatches in {e['dsha_report_only']['n_frames_with_any_mismatch']} frames"
              if name == 'clause1' else ''), '',
           '| round | ' + ' | '.join(f'{f} mism' for f in fields) + ' | ll_in max abs diff |', '|---|' + '---|' * (len(fields) + 1)]
    for r in rounds:
        md.append(f'| {r} | ' + ' | '.join(str(st[f'{f}{r}']['mismatch']) for f in fields) + f" | {st[f'll_in{r}']['max_abs_diff']:.3e} |")
    md.append('')
a0['pass'] = bool(a0['clause1']['total_mismatch'] == 0 and a0['clause2']['total_mismatch'] == 0
                  and a0['clause1']['n_frames_compared'] == 600 and a0['clause2']['n_frames_compared'] == 600)
res['A5_0'] = a0
V.append(f"A5-0 determinism: {'PASS' if a0['pass'] else 'FAIL'}  (clause 1: {a0['clause1']['n_frames_compared']} frames, "
         f"{a0['clause1']['total_mismatch']} mismatches, ll_in max |diff| {a0['clause1']['ll_in_max_abs_diff']:.2e}; "
         f"clause 2: {a0['clause2']['n_frames_compared']} frames, {a0['clause2']['total_mismatch']} mismatches, "
         f"ll_in max |diff| {a0['clause2']['ll_in_max_abs_diff']:.2e})")

# ================================================================================================ A5-1 FER by round + Kc by round
fer_tab = {}  # L -> bool matrix (frames 0-299, ierr_r > 0)
for L in (8, 12):
    fr = sorted(f for (l, f) in stored if l == L)
    if fr:
        fer_tab[L] = np.array([[stored[(L, f)][f'ierr{r}'] > 0 for r in range(1, 5)] for f in fr])
by_L = {}
for x in lo_ok + r10_ok:
    if x['frame'] < 300:
        by_L.setdefault(x['L'], []).append(x)
for L in sorted(by_L):
    fer_tab[L] = np.array([[x[f'ierr{r}'] > 0 for r in range(1, R + 1)] for x in sorted(by_L[L], key=lambda x: x['frame'])])
Ls_long = sorted(by_L)
md += ['## A5-1 FER by round (frame fails iff ierr_r > 0; Wilson 95%; frames 0-299)', '',
       '| R | ' + ' | '.join(f'L{L} (K {8 * L}, n {fer_tab[L].shape[0]})' for L in Ls_long) + ' |', '|---|' + '---|' * len(Ls_long)]
fer_json = {}
for L in sorted(fer_tab):
    n = fer_tab[L].shape[0]
    fer_json[f'L{L}'] = [dict(r=r + 1, fer=float(fer_tab[L][:, r].mean()), ci=wilson(int(fer_tab[L][:, r].sum()), n), n=n)
                         for r in range(fer_tab[L].shape[1])]
for r in range(R):
    md.append(f'| {r + 1} | ' + ' | '.join(
        f"{fer_json[f'L{L}'][r]['fer']:.3f} [{fer_json[f'L{L}'][r]['ci'][0]:.3f},{fer_json[f'L{L}'][r]['ci'][1]:.3f}]" for L in Ls_long) + ' |')
md += ['', 'c1i FULL_R4 (R1-R4 only): ' + '; '.join(
    f"L{L} (n {fer_tab[L].shape[0]}) " + ' '.join(
        f"R{e['r']} {e['fer']:.3f} [{e['ci'][0]:.3f},{e['ci'][1]:.3f}]" for e in fer_json[f'L{L}']) for L in (8, 12) if L in fer_tab), '']
res['A5_1_fer'] = fer_json


def kc_of(ferL, Rr):
    Ls = [L for L in sorted(ferL) if ferL[L].shape[1] >= Rr]
    Ks, ys = [8 * L for L in Ls], [float(ferL[L][:, Rr - 1].mean()) for L in Ls]
    note = ''
    # A4 anchor (L20 at its R4 value at K = 160) is only used when L20 has no round >= Rr data; moot here (L16/L20 run to R10)
    if Rr >= 5 and 20 in ferL and 20 not in Ls and ys and ys[0] >= 0.5:
        Ks, ys = [160] + Ks, [float(ferL[20][:, 3].mean())] + ys
        note = 'L20 at its R4 value used as lower anchor'
    k = E.k_cross(Ks, ys, 0.5)
    if k is None:
        note = (note + '; ' if note else '') + ('FER < .5 at the largest L (Kc above range)' if ys and ys[-1] < 0.5 else 'FER > .5 at all L (Kc below range)')
    return k, Ks, ys, note


kb = np.random.default_rng(SEED)
boot_idx = {L: kb.integers(0, v.shape[0], size=(B, v.shape[0])) for L, v in sorted(fer_tab.items())}
kc = {}
md += ['### Kc by round (FER(R) = .5 crossing in K = 8 L, linear in K) vs frozen mean-map staircase', '',
       '| R | Kc obs | frozen pred | ln(pred/obs) | within .15 | boot 95% [n valid/B] | L: FER |', '|---|---|---|---|---|---|---|']
for Rr in range(1, R + 1):
    k, Ks, ys, note = kc_of(fer_tab, Rr)
    pred = FROZEN['kc_by_round'][f'R{Rr}']
    ln = None if k is None else math.log(pred / k)
    ks = []
    for b in range(B):
        fb = {L: v[boot_idx[L][b]] for L, v in fer_tab.items()}
        kb_, *_ = kc_of(fb, Rr)
        if kb_ is not None:
            ks.append(kb_)
    kc[f'R{Rr}'] = dict(obs=k, pred=pred, ln_pred_over_obs=ln, within_bar=None if ln is None else bool(abs(ln) <= KC_BAR), note=note,
                        K=Ks, fer=ys, boot_n_valid=len(ks), boot_ci=pct(ks) if len(ks) > 20 else None)
    bc = kc[f'R{Rr}']['boot_ci']
    md.append(f"| {Rr} | {'-' if k is None else format(k, '.1f')} | {pred:.1f} | {'-' if ln is None else format(ln, '+.3f')} | "
              f"{'-' if ln is None else ('PASS' if abs(ln) <= KC_BAR else 'FAIL')} | "
              f"{'-' if bc is None else f'[{bc[0]:.1f},{bc[1]:.1f}]'} [{len(ks)}/{B}] | "
              + ' '.join(f'{K // 8}:{y:.3f}' for K, y in zip(Ks, ys)) + (f' ({note})' if note else '') + ' |')
res['A5_1_kc'] = kc
md.append('')
kc_pass = [Rr for Rr in range(1, R + 1) if kc[f'R{Rr}']['within_bar']]
kc_fail = [Rr for Rr in range(1, R + 1) if kc[f'R{Rr}']['within_bar'] is False]
kc_na = [Rr for Rr in range(1, R + 1) if kc[f'R{Rr}']['within_bar'] is None]
f20 = fer_json.get('L20', [None] * R)[R - 1]
k10 = kc['R10']['obs']
p_fer = None if f20 is None else bool(FER20_BAND[0] <= f20['fer'] <= FER20_BAND[1])
p_kc = None if k10 is None else bool(KC10_BAND[0] <= k10 <= KC10_BAND[1])
res['A5_1_prediction'] = dict(fer_R10_L20=None if f20 is None else f20['fer'], fer_R10_L20_ci=None if f20 is None else f20['ci'],
                              band_fer=FER20_BAND, pass_fer=p_fer, kc_R10=k10, band_kc=KC10_BAND, pass_kc=p_kc,
                              kc_R10_boot_ci=kc['R10']['boot_ci'])
bci = kc['R10']['boot_ci']
fer_s = 'n/a' if f20 is None else f"{f20['fer']:.3f} [{f20['ci'][0]:.3f},{f20['ci'][1]:.3f}]"
kc_s = 'n/a' if k10 is None else f"{k10:.1f}" + ('' if bci is None else f" [{bci[0]:.1f},{bci[1]:.1f}]")
md += [f"A5 prediction (from the A4 bracket): FER_R10(L20) in [{FER20_BAND[0]},{FER20_BAND[1]}]: observed {fer_s} -> "
       f"{'n/a' if p_fer is None else ('PASS' if p_fer else 'FAIL')}; Kc_R10 in [{KC10_BAND[0]:.0f},{KC10_BAND[1]:.0f}]: observed {kc_s} -> "
       f"{'n/a' if p_kc is None else ('PASS' if p_kc else 'FAIL')}", '']
V.append(f"A5-1 Kc vs frozen staircase (|ln| <= {KC_BAR}): PASS at R{kc_pass}; FAIL at R{kc_fail}; undefined at R{kc_na}.  Kc_R: "
         + ', '.join(f"R{Rr} " + ('-' if kc[f'R{Rr}']['obs'] is None else f"{kc[f'R{Rr}']['obs']:.1f}") +
                     ('' if kc[f'R{Rr}']['ln_pred_over_obs'] is None else f" (ln {kc[f'R{Rr}']['ln_pred_over_obs']:+.3f})") for Rr in range(1, R + 1)))
V.append(f"A5-1 prediction: FER_R10(L20) {fer_s} in [.02,.43] -> {'n/a' if p_fer is None else ('PASS' if p_fer else 'FAIL')}; "
         f"Kc_R10 {kc_s} in [172,186] -> {'n/a' if p_kc is None else ('PASS' if p_kc else 'FAIL')}")

# ================================================================================================ A5-2 per-frame maps
IRS = sorted({round(float(r['Ir']), 2) for r in exit_ok if r['Ir'] is not None})
if [g for g in G if g not in IRS]:
    sys.exit(f'FAIL: EXIT-D Ir grid {IRS} does not contain G {G}')
GRID = np.array([0.] + IRS)
ex = {}  # L -> frame -> {None | Ir: row}
for r in exit_ok:
    slot = ex.setdefault(r['L'], {}).setdefault(r['frame'], {})
    key = None if r['Ir'] is None else round(float(r['Ir']), 2)
    if key in slot:
        sys.exit(f"FAIL: duplicate EXIT-D row L{r['L']} frame {r['frame']} Ir {key}")
    slot[key] = r


def classify(D):
    d = np.asarray(D)
    if d[-1] <= 0:
        return 'C'
    if (d > 0).all():
        return 'O'
    if (d < 0).any():
        return 'B'
    return 'X'


def u_cross(D):  # highest (- to +) crossing of D on G, linear
    u = None
    for i in range(len(G) - 1):
        if D[i] < 0 <= D[i + 1]:
            u = G[i] + (-D[i]) / (D[i + 1] - D[i]) * (G[i + 1] - G[i])
    return u


nsc_of = lambda D: sum(1 for i in range(len(D) - 1) if D[i] * D[i + 1] < 0)
pf, m0, n_incomplete = {}, {}, {}
for L in (28, 32, 36):
    fr_all = sorted(ex.get(L, {}))
    fr = [f for f in fr_all if None in ex[L][f] and all(i in ex[L][f] for i in IRS)]
    n_incomplete[L] = len(fr_all) - len(fr)
    if not fr:
        continue
    mm = np.array([[ex[L][f][None]['mi_in1']] + [ex[L][f][i]['mi_in1'] for i in IRS] for f in fr])
    tr0, _, first0 = E.staircase(GRID, mm.mean(axis=0), I_STAR, rounds=R)
    m0[L] = dict(first=first0, traj=tr0, mean_map=mm.mean(axis=0))
    for f, phi in zip(fr, mm):
        d = ex[L][f]
        D = [d[g]['mi_in1'] - g for g in G]
        traj, _, first = E.staircase(GRID, phi, I_STAR, rounds=R)
        fps, _ = E.fixed_points(GRID, phi, I_STAR)
        stab = [p['I'] for p in fps if p['stable']]
        pf[(L, f)] = dict(L=L, frame=f, cls=classify(D), u=u_cross(D), s=min(stab) if stab else None, nsc=nsc_of(D), D=D,
                          mi_none=float(phi[0]), m2_first=first, any_g2=any(d[g]['ierr2'] == 0 for g in G),
                          g_nonabs=sum(1 for g in G if d[g]['ierr1'] == 0 and d[g]['ierr2'] > 0))
for key, p in pf.items():
    x = xo.get(key)
    if x is not None and key[0] in (28, 32):
        ie = [x[f'ierr{r}'] for r in range(1, R + 1)]
        p.update(obs_ierr=ie, obs_first=next((r + 1 for r, v in enumerate(ie) if v == 0), None), obs_dec10=bool(ie[-1] == 0),
                 mi10=1. - float(x['ll_in10']), obs_nonabs=bool(any(v == 0 for v in ie) and ie[-1] > 0))
joined = {L: [p for (l, f), p in sorted(pf.items()) if l == L and 'obs_ierr' in p] for L in (28, 32)}
res['A5_2_incomplete_exit_frames'] = n_incomplete
CLS = ['O', 'B', 'C', 'X']
md += ['## A5-2 per-frame classes on G (EXIT-D rows)', '',
       'O: D_f > 0 on all G; B: D_f(.56) > 0 and D_f < 0 somewhere; C: D_f(.56) <= 0; X: edge leftover.  u_f = highest - to + crossing on G.', '',
       '| L | frames | O | B | C | X | >1 sign change on G (all / O / B / C) | u_f class B: median [min,max] (n) | u_f defined in class C (n) |',
       '|---|---|---|---|---|---|---|---|---|']
A2c = {}
for L in (28, 32, 36):
    ps = [p for (l, f), p in pf.items() if l == L]
    if not ps:
        continue
    c = {k: sum(1 for p in ps if p['cls'] == k) for k in CLS}
    mc = {k: sum(1 for p in ps if p['nsc'] > 1 and (k == 'all' or p['cls'] == k)) for k in ('all',) + tuple(CLS)}
    ub = [p['u'] for p in ps if p['cls'] == 'B' and p['u'] is not None]
    uc = [p['u'] for p in ps if p['cls'] == 'C' and p['u'] is not None]
    A2c[f'L{L}'] = dict(n=len(ps), counts=c, multi_sign_change=mc, u_B=ub, u_C=uc, n_incomplete_excluded=n_incomplete[L],
                        u_B_stats=None if not ub else dict(median=float(np.median(ub)), min=float(min(ub)), max=float(max(ub)), n=len(ub)))
    md.append(f"| {L}{' (report-only)' if L == 36 else ''} | {len(ps)} | {c['O']} | {c['B']} | {c['C']} | {c['X']} | "
              f"{mc['all']} / {mc['O']} / {mc['B']} / {mc['C']} | "
              + ('-' if not ub else f'{np.median(ub):.3f} [{min(ub):.3f},{max(ub):.3f}] ({len(ub)})') + f' | {len(uc)} |')
res['A5_2_classes'] = A2c
md.append('')

# --- decode-by-R10 per class
cnt = {}
md += ['### Decode by R10 (ierr10 == 0, R10-X) per class', '', '| L | class | n | decoded by R10 [Wilson] |', '|---|---|---|---|']
CLS_SETS = {'O': {'O'}, 'B': {'B'}, 'C': {'C'}, 'X': {'X'}, 'BC': {'B', 'C'}}
for L in (28, 32):
    for cname, ss in CLS_SETS.items():
        sub = [p for p in joined[L] if p['cls'] in ss]
        cnt[(cname, L)] = (len(sub), sum(p['obs_dec10'] for p in sub))
        md.append(f"| {L} | {'B u C' if cname == 'BC' else cname} | {len(sub)} | {rate(cnt[(cname, L)][1], len(sub))} |")
for cname in ('O', 'B', 'C', 'BC'):
    n_ = cnt[(cname, 28)][0] + cnt[(cname, 32)][0]
    k_ = cnt[(cname, 28)][1] + cnt[(cname, 32)][1]
    md.append(f"| 28+32 | {'B u C' if cname == 'BC' else cname} | {n_} | {rate(k_, n_)} |")
md.append('')
crit = []
for g, test, rule in (('O', lambda p: p >= O_MIN, '>= .8'), ('BC', lambda p: p <= BC_MAX, '<= .2')):
    for L in (28, 32):
        n_, k_ = cnt[(g, L)]
        pooled = n_ < POOL_N
        if pooled:
            n_, k_ = cnt[(g, 28)][0] + cnt[(g, 32)][0], cnt[(g, 28)][1] + cnt[(g, 32)][1]
        if n_ < POOL_N:
            crit.append(dict(cls=g, L=L, pooled=pooled, n=n_, k=k_, rate=None, ci=None, passed=None, rule=rule))
        else:
            crit.append(dict(cls=g, L=L, pooled=pooled, n=n_, k=k_, rate=k_ / n_, ci=wilson(k_, n_), passed=bool(test(k_ / n_)), rule=rule))
for c in crit:
    md.append(f"- class {'B u C' if c['cls'] == 'BC' else c['cls']} at L{c['L']} (rule {c['rule']}{', pooled over L28+L32' if c['pooled'] else ''}): "
              + ('NOT EVALUABLE (n < 10 even pooled)' if c['passed'] is None else f"{rate(c['k'], c['n'])} -> {'PASS' if c['passed'] else 'FAIL'}"))
a2a = 'FAIL' if any(c['passed'] is False for c in crit) else ('INCONCLUSIVE' if any(c['passed'] is None for c in crit) else 'PASS')
nonabs_obs = sum(1 for js in joined.values() for p in js if p['obs_nonabs'])
md += ['', f'non-absorbing R10-X frames (some ierr_r == 0 for r <= 10 but ierr10 > 0): {nonabs_obs}', '']
res['A5_2_decode_by_class'] = dict(counts={f'{k[0]}|L{k[1]}': v for k, v in cnt.items()}, criteria=crit, verdict=a2a, nonabsorbing_frames=nonabs_obs)
V.append(f"A5-2a decode-by-R10 vs class: {a2a}.  " + '; '.join(
    f"{'B u C' if c['cls'] == 'BC' else c['cls']} L{c['L']}{'(pooled)' if c['pooled'] else ''} "
    + ('n/a' if c['passed'] is None else f"{c['rate']:.3f} [{c['ci'][0]:.3f},{c['ci'][1]:.3f}] n={c['n']} {c['rule']} {'ok' if c['passed'] else 'NO'}") for c in crit))

# --- M2 / M0 vs observed
md += ['### M2 (frame-own staircase) vs observed FER by round, R10-X frames; M0 = mean-map staircase', '']
M2 = {}
for L in (28, 32):
    js = joined[L]
    if not js:
        continue
    n = len(js)
    obs_fail = np.array([[v > 0 for v in p['obs_ierr']] for p in js])
    m2_fail = np.array([[(p['m2_first'] is None or p['m2_first'] > r) for r in range(1, R + 1)] for p in js])
    f0 = m0[L]['first']
    m0_fail = np.array([float(f0 is None or f0 > r) for r in range(1, R + 1)])
    bi = np.random.default_rng(SEED).integers(0, n, size=(B, n))
    dd = m2_fail[:, R - 1][bi].mean(axis=1) - obs_fail[:, R - 1][bi].mean(axis=1)
    d10 = float(m2_fail[:, R - 1].mean() - obs_fail[:, R - 1].mean())
    dec_m2, dec_ob = ~m2_fail[:, R - 1], ~obs_fail[:, R - 1]
    conf = dict(m2dec_obsdec=int((dec_m2 & dec_ob).sum()), m2dec_obsfail=int((dec_m2 & ~dec_ob).sum()),
                m2fail_obsdec=int((~dec_m2 & dec_ob).sum()), m2fail_obsfail=int((~dec_m2 & ~dec_ob).sum()))
    both = [(p['obs_first'] - p['m2_first']) for p in js if p['obs_first'] is not None and p['m2_first'] is not None]
    M2[f'L{L}'] = dict(n=n, obs_fer=obs_fail.mean(axis=0), m2_fer=m2_fail.mean(axis=0), m0_fer=m0_fail, m0_first=f0,
                       diff_R10=d10, diff_R10_boot_ci=pct(dd), pass_bar=bool(abs(d10) <= M2_BAR), confusion_R10=conf,
                       agreement_R10=float((dec_m2 == dec_ob).mean()), first_round_diff_both_decoded=dict(
                           n=len(both), mean=float(np.mean(both)) if both else None, median=float(np.median(both)) if both else None,
                           exact_agree=float(np.mean([b == 0 for b in both])) if both else None))
    m = M2[f'L{L}']
    md += [f'#### L{L} (n = {n} frames; M0 first-success round {f0})', '', '| R | observed FER [Wilson] | M2 FER | M2 - obs | M0 FER |', '|---|---|---|---|---|']
    for r in range(R):
        lo, hi = wilson(int(obs_fail[:, r].sum()), n)
        md.append(f"| {r + 1} | {m['obs_fer'][r]:.3f} [{lo:.3f},{hi:.3f}] | {m['m2_fer'][r]:.3f} | {m['m2_fer'][r] - m['obs_fer'][r]:+.3f} | {m0_fail[r]:.0f} |")
    c = conf
    md += ['', f"M2 FER_R10 - observed FER_R10 = {fmt(d10, *m['diff_R10_boot_ci'])} (paired frame bootstrap) -> |diff| <= {M2_BAR}: "
               f"{'PASS' if m['pass_bar'] else 'FAIL'}",
           f"per-frame confusion at R10 (rows M2, columns observed): M2 decoded & obs decoded {c['m2dec_obsdec']}, M2 decoded & obs failed "
           f"{c['m2dec_obsfail']}, M2 failed & obs decoded {c['m2fail_obsdec']}, M2 failed & obs failed {c['m2fail_obsfail']}; "
           f"agreement {m['agreement_R10']:.3f}",
           f"first-decode round, observed - M2, among frames decoded by both (n {len(both)}): mean "
           f"{'-' if not both else format(np.mean(both), '+.2f')}, median {'-' if not both else format(np.median(both), '+.1f')}, "
           f"exact agreement {'-' if not both else format(np.mean([b == 0 for b in both]), '.3f')}", '']
if 36 in m0:
    f36 = [p['m2_first'] for (l, f), p in pf.items() if l == 36]
    md.append(f"L36 (report-only, no R10-X): M0 first-success round {m0[36]['first']}; M2 FER by R: " + ' '.join(
        f"R{r}:{np.mean([(x is None or x > r) for x in f36]):.3f}" for r in range(1, R + 1)))
    md.append('')
res['A5_2_M2'] = M2
res['A5_2_M0'] = {f'L{L}': dict(first_success_round=v['first'], traj=v['traj'], mean_map=v['mean_map']) for L, v in m0.items()}
a2b = 'n/a' if len(M2) < 2 else ('PASS' if all(v['pass_bar'] for v in M2.values()) else 'FAIL')
V.append(f"A5-2b M2 FER_R10 vs observed (|diff| <= {M2_BAR} at both L): {a2b}.  " + '; '.join(
    f"L{L[1:]} M2 {v['m2_fer'][R - 1]:.3f} vs obs {v['obs_fer'][R - 1]:.3f}, diff {fmt(v['diff_R10'], *v['diff_R10_boot_ci'])}, M0 first-success round "
    f"{v['m0_first']}, per-frame agreement at R10 {v['agreement_R10']:.3f}" for L, v in M2.items()))

# ================================================================================================ A5-3 start dependence
A3 = {}
md += ['## A5-3 same-frame start dependence (R10-X frames failing at round 10)', '',
       '| L | class | failing at R10 | with >= 1 Ir in G decoding in 2 rounds (ierr2 == 0) [Wilson] |', '|---|---|---|---|']
for L in (28, 32):
    fail = [p for p in joined[L] if not p['obs_dec10']]
    k, n = sum(p['any_g2'] for p in fail), len(fail)
    lo, hi = wilson(k, n)
    byc = {}
    for cname in CLS:
        sub = [p for p in fail if p['cls'] == cname]
        byc[cname] = dict(n=len(sub), k=sum(p['any_g2'] for p in sub), ci=wilson(sum(p['any_g2'] for p in sub), len(sub)))
    A3[f'L{L}'] = dict(n_fail=n, k=k, rate=None if n == 0 else k / n, ci=(lo, hi), shown=bool(n > 0 and lo > START_LB), by_class=byc,
                       n_fail_frames_with_gdecode_via_ierr1_only=sum(p['g_nonabs'] > 0 for p in fail))
    md.append(f"| {L} | all | {n} | {rate(k, n)} -> {'SHOWN' if A3[f'L{L}']['shown'] else 'NOT shown'} (lower bound {'> ' if lo > START_LB else '<= '}{START_LB}) |")
    for cname in CLS:
        md.append(f"| {L} | {cname} | {byc[cname]['n']} | {rate(byc[cname]['k'], byc[cname]['n'])} |")
res['A5_3_start_dependence'] = A3
md.append('')
V.append('A5-3a start dependence (Wilson lower > .10): ' + '; '.join(
    f"L{L[1:]} {v['k']}/{v['n_fail']} = " + ('n/a' if v['rate'] is None else f"{v['rate']:.3f} [{v['ci'][0]:.3f},{v['ci'][1]:.3f}]")
    + (' SHOWN' if v['shown'] else ' NOT shown') for L, v in A3.items()))

# --- direction check
pairs = {}
for (L, f), p in sorted(pf.items()):
    if p['cls'] != 'B':
        continue
    for g, D in zip(G, p['D']):
        if abs(g - p['u']) < DIR_GAP - 1e-9:
            continue
        if D == 0:
            pairs.setdefault(L, []).append(None)
            continue
        row = ex[L][f][g]
        up = bool(row['ierr1'] == 0 or row['ierr2'] == 0 or row['mi_in2'] > row['mi_in1'])
        pairs.setdefault(L, []).append(dict(side='below' if g < p['u'] else 'above', Dpos=bool(D > 0), up=up, agree=bool(up == (D > 0)), frame=f, Ir=g))


def dir_stats(plist):
    out = {}
    for side in ('below', 'above'):
        sub = [q for q in plist if q is not None and q['side'] == side]
        k = sum(q['agree'] for q in sub)
        out[side] = dict(n=len(sub), k=k, rate=None if not sub else k / len(sub), ci=wilson(k, len(sub)),
                         by_sign={s: dict(n=sum(1 for q in sub if q['Dpos'] == (s == 'D>0')), k=sum(1 for q in sub if q['Dpos'] == (s == 'D>0') and q['agree']))
                                  for s in ('D>0', 'D<0')})
    out['n_zero_D_excluded'] = sum(1 for q in plist if q is None)
    return out


md += ['### Direction check, class B pairs (frame, Ir in G) with |Ir - u_f| >= .02',
       'second step up iff ierr1 == 0 or ierr2 == 0 or mi_in2 > mi_in1; agreement = up == (D_f(Ir) > 0)', '',
       '| L | class-B frames | side | pairs | agreement [Wilson] | of which D>0 | of which D<0 |', '|---|---|---|---|---|---|---|']
DIRR = {}
for tag, plist, nfr in ([(f'L{L}', pairs.get(L, []), A2c.get(f'L{L}', {}).get('counts', {}).get('B')) for L in (28, 32)]
                        + [('pooled 28+32', pairs.get(28, []) + pairs.get(32, []),
                            sum(A2c.get(f'L{L}', {}).get('counts', {}).get('B', 0) for L in (28, 32))),
                           ('L36 (report-only)', pairs.get(36, []), A2c.get('L36', {}).get('counts', {}).get('B'))]):
    st = dir_stats(plist)
    DIRR[tag] = dict(n_class_B_frames=nfr, **st)
    for side in ('below', 'above'):
        s = st[side]
        md.append(f"| {tag} | {nfr} | {'Ir < u_f' if side == 'below' else 'Ir > u_f'} | {s['n']} | {rate(s['k'], s['n'])} | "
                  f"{s['by_sign']['D>0']['k']}/{s['by_sign']['D>0']['n']} | {s['by_sign']['D<0']['k']}/{s['by_sign']['D<0']['n']} |")
    if st['n_zero_D_excluded']:
        md.append(f"| {tag} | | D == 0 pairs excluded | {st['n_zero_D_excluded']} | | | |")
res['A5_3_direction'] = DIRR
dir_ok = {}
for L in (28, 32):
    s = DIRR[f'L{L}']
    dir_ok[L] = None if (s['below']['n'] == 0 or s['above']['n'] == 0) else bool(s['below']['rate'] >= DIR_BAR and s['above']['rate'] >= DIR_BAR)
a3b = 'FAIL' if any(v is False for v in dir_ok.values()) else ('INCONCLUSIVE' if any(v is None for v in dir_ok.values()) else 'PASS')
res['A5_3_direction_verdict'] = dict(per_L={f'L{L}': v for L, v in dir_ok.items()}, verdict=a3b, rule='per L28 and L32, both sides >= .80 (point estimate)')
md += ['', f'direction check verdict (per L28 and L32, both sides >= {DIR_BAR}, point estimate): {a3b}', '']


def _dr(tag):
    s = DIRR[tag]
    f = lambda q: 'n/a' if q['n'] == 0 else f"{q['rate']:.3f} [{q['ci'][0]:.3f},{q['ci'][1]:.3f}] n={q['n']}"
    return f"{tag}: below {f(s['below'])}, above {f(s['above'])}"


V.append(f'A5-3b direction (class B, >= .80 on both sides at L28 and L32): {a3b}.  ' + '; '.join(_dr(t) for t in DIRR))

# ================================================================================================ report-only
md += ['## Report-only', '']
ro = {}
md += ['### R10-X (frames 1000-1299) vs A4 FULL_R10 (frames 0-299), FER_R10', '']
for L in (28, 32):
    xs = [r for r in x_ok if r['L'] == L]
    a4 = [r for r in r10_ok if r['L'] == L and r['frame'] < 300]
    if not xs or not a4:
        continue
    k1, n1 = sum(1 for r in xs if r['ierr10'] > 0), len(xs)
    k2, n2 = sum(1 for r in a4 if r['ierr10'] > 0), len(a4)
    d, lo, hi = newcombe(k1, n1, k2, n2)
    ro[f'fer_R10_L{L}'] = dict(x=k1 / n1, x_ci=wilson(k1, n1), a4=k2 / n2, a4_ci=wilson(k2, n2), diff=d, diff_ci_newcombe=(lo, hi))
    md.append(f"- L{L}: R10-X {rate(k1, n1)} vs A4 {rate(k2, n2)}; diff {fmt(d, lo, hi)} (Newcombe)")
md += ['', '### Stalled frames in classes B / C (ierr10 > 0): |MI_10 - s_f|, s_f = lowest stable fixed point of the frame own map, MI_10 = 1 - ll_in10', '']
for L in (28, 32):
    for cname in ('B', 'C', 'BC'):
        sub = [p for p in joined[L] if (not p['obs_dec10']) and p['cls'] in CLS_SETS[cname]]
        v = [abs(p['mi10'] - p['s']) for p in sub if p['s'] is not None]
        ro[f'stalled_L{L}_{cname}'] = dict(n=len(sub), n_with_s=len(v), median_abs=None if not v else float(np.median(v)),
                                           q25_q75=None if not v else (float(np.percentile(v, 25)), float(np.percentile(v, 75))),
                                           mean_mi10=None if not sub else float(np.mean([p['mi10'] for p in sub])),
                                           median_s=None if not v else float(np.median([p['s'] for p in sub if p['s'] is not None])))
        md.append(f"- L{L} class {'B u C' if cname == 'BC' else cname}: stalled n {len(sub)}, with a stable crossing {len(v)}; median |MI_10 - s_f| "
                  + ('-' if not v else f"{np.median(v):.4f} (IQR {np.percentile(v, 25):.4f}-{np.percentile(v, 75):.4f}); median s_f "
                     f"{ro[f'stalled_L{L}_{cname}']['median_s']:.4f}, mean MI_10 {ro[f'stalled_L{L}_{cname}']['mean_mi10']:.4f}"))
res['report_only'] = ro
md.append('')

# ================================================================================================ outputs
md = md[:4] + ['## Verdicts', ''] + ['- ' + v for v in V] + [''] + md[4:]
res['verdicts'] = V
out = P(args.out)
out.mkdir(parents=True, exist_ok=True)
(out / 'c1g.json').write_text(json.dumps(res, indent=1, default=_j) + '\n')
(out / 'c1g.md').write_text('\n'.join(md) + '\n')
with open(out / 'c1g_frames.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['L', 'frame', 'class', 'u_f', 's_f', 'n_sign_changes_G', 'mi_none', 'D_at_0.56', 'M2_first_success_round',
                'obs_first_decode_round', 'obs_decoded_R10', 'mi10', 'any_G_decode_in_2'])
    e = lambda x: '' if x is None else (f'{x:.6f}' if isinstance(x, float) else x)
    for (L, f), p in sorted(pf.items()):
        w.writerow([L, f, p['cls'], e(p['u']), e(p['s']), p['nsc'], e(p['mi_none']), e(p['D'][-1]), e(p['m2_first']) if p['m2_first'] is not None else 'never',
                    ('never' if p['obs_first'] is None else p['obs_first']) if 'obs_ierr' in p else '', int(p['obs_dec10']) if 'obs_ierr' in p else '',
                    e(p.get('mi10')) if 'obs_ierr' in p else '', int(p['any_g2'])])
print('\n'.join(md))
