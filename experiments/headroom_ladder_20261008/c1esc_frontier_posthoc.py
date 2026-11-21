#!/usr/bin/env python
"""POST HOC frontier diagnostic (2026-10-13, after the frozen A' verdict; NOT a decision input).
Compares fixed vs online policy classes across target FER levels instead of one boundary point.
Shared loading/cost/policy code copied from c1esc_analyze.py (A' escalation test analysis).  Rows and JSON only.
    python -B c1esc_analyze.py [--dir out/c1esc] [--t20-dir out/c1g_r10lo] [--t40-dir out/c1ib2_r10] [--time-dir out/c1ib2_time] [--out out/c1esc/analysis]
Dev = frames 0-299, test = 300-599.  B* = cheapest fixed (E10/E0 x Rc) with dev FER <= delta; P* = cheapest online policy (fixed or
escalation E1-E3, round cap, optional give-up rule syn_{r_g} > theta) with dev FER <= delta.  Test saving S and FER difference d with
paired frame bootstrap.  Primary L16, delta .10: A' viable iff S >= .15, S CI lower > 0, d <= +.01.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
SNR, RHO, R = 650, 300, 10
ARMS = {'E10': 10, 'E0': 0, 'E1': 1, 'E2': 2, 'E3': 3}
FIXED = ('E10', 'E0')
DEV_MAX, N_FRAMES = 300, 600
CONDS = [(16, .10, True), (20, .20, False)]  # (L, delta, primary)
GATE, FER_TOL, B, SEED = .15, .01, 1000, 20261015

ap = argparse.ArgumentParser()
ap.add_argument('--dir', default='out/c1esc')
ap.add_argument('--t20-dir', default='out/c1g_r10lo')
ap.add_argument('--t40-dir', default='out/c1ib2_r10')
ap.add_argument('--time-dir', default='out/c1ib2_time')
ap.add_argument('--out', default='out/c1esc/analysis_frontier')
args = ap.parse_args()
P = lambda s: (HERE / s) if not Path(s).is_absolute() else Path(s)


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def files_of(d):
    return sorted(glob.glob(str(P(d) / 'rows_shard*.jsonl')))


def load(d, arms, Ls):
    out = {}
    for f in files_of(d):
        for x in open(f):
            if not x.strip():
                continue
            r = json.loads(x)
            if r['status'] != 'ok' or r['arm'] not in arms or r['snr_centi_db'] != SNR or r['rho_permille'] != RHO or r['L'] not in Ls:
                continue
            k = (r['arm'], r['L'], r['frame'])
            if k in out:
                raise ValueError(f'duplicate {k}')
            out[k] = r
    return out


Ls = sorted({c[0] for c in CONDS})
rows = load(args.dir, ARMS, Ls)
n_err = sum(1 for f in files_of(args.dir) for x in open(f) if x.strip() and '"status": "error"' in x)
res = dict(_argv=sys.argv, _config=dict(snr=SNR, rho=RHO, arms=ARMS, conds=CONDS, gate=GATE, fer_tol=FER_TOL, B=B, seed=SEED, dev_max=DEV_MAX,
                                         md5=dict(script=md5(Path(__file__)), rows={d: {Path(f).name: md5(f) for f in files_of(d)}
                                                                                     for d in (args.dir, args.time_dir)})),
           n_rows=len(rows), n_error_rows=n_err)
md = ['# A\' escalation test: start T20, escalate to T40 if not decoded by round e (6.5 dB, rho .3, frames 0-599)', '',
      f'Rows {len(rows)} (error rows {n_err}). Dev frames 0-{DEV_MAX - 1}, test {DEV_MAX}-{N_FRAMES - 1}.', '']

# ---------------------------------------------------------------- closure vs stored fixed-T rows (frames 0-299)
F_CL = [f'{k}{q}' for k in ('ierr', 'syn', 'dsha', 'cerr') for q in range(1, R + 1)]
clos = {}
for arm, d, sarm in (('E10', args.t20_dir, 'FULL_R10'), ('E0', args.t40_dir, 'R10T40')):
    st = load(d, {sarm}, Ls)
    pairs = [(rows[(arm, L, f)], st[(sarm, L, f)]) for (_, L, f) in st if (arm, L, f) in rows]
    clos[arm] = dict(pairs=len(pairs), mismatches=sum(any(a[k] != b[k] for k in F_CL) for a, b in pairs))
res['closure'] = clos
md += ['Closure vs stored rows: ' + '; '.join(f"{a} {v['pairs']} pairs, {v['mismatches']} mismatching" for a, v in clos.items()), '']

# ---------------------------------------------------------------- cost
trows = [json.loads(x) for f in files_of(args.time_dir) for x in open(f) if x.strip()]
trows = [r for r in trows if r['status'] == 'ok' and r['snr_centi_db'] == SNR and r['rho_permille'] == RHO]


def increments(L, T):
    tt = np.array([r['t_cum'] for r in trows if r['arm'] == f'R10T{T}' and r['L'] == L], float)
    if tt.size == 0:
        raise ValueError(f'timing reference missing T{T} L{L}')
    c = tt.mean(0)
    return np.diff(np.r_[0., c])


def sched(arm):
    e = ARMS[arm]
    return [20] * e + [40] * (R - e)


def cumcost(L, unit):
    out = {}
    for arm in ARMS:
        s = sched(arm)
        if unit == 'sec':
            inc = {T: increments(L, T) for T in (20, 40)}
            out[arm] = np.cumsum([inc[s[q]][q] for q in range(R)])
        else:
            out[arm] = np.cumsum(np.array(s, float))
    return out


# ---------------------------------------------------------------- policies
def arrays(L):
    frames = sorted(set.intersection(*[{f for (a, l, f) in rows if a == arm and l == L} for arm in ARMS]))
    if len(frames) != N_FRAMES:
        raise ValueError(f'L{L}: {len(frames)} common frames, expected {N_FRAMES}')
    A = {}
    for arm in ARMS:
        rr = [rows[(arm, L, f)] for f in frames]
        ierr = np.array([[r[f'ierr{q}'] for q in range(1, R + 1)] for r in rr])
        syn = np.array([[r[f'syn{q}'] for q in range(1, R + 1)] for r in rr])
        z = syn == 0
        fz = np.where(z.any(1), z.argmax(1) + 1, R + 1)
        tc = np.array([r['t_cum'] for r in rr], float)
        A[arm] = dict(ierr=ierr, syn=syn, fz=fz, tcum=tc)
    return np.array(frames), A


def policies(A, dev):
    out = []
    for arm, e in ARMS.items():
        rcs = range(1, R + 1) if arm in FIXED else range(e + 1, R + 1)
        for Rc in rcs:
            out.append(dict(arm=arm, Rc=Rc, rg=None, th=None, online=arm not in FIXED))
            for rg in range(1, min(4, Rc - 1) + 1):
                live = dev & (A[arm]['fz'] > rg)
                for th in np.unique(A[arm]['syn'][live, rg - 1]):
                    out.append(dict(arm=arm, Rc=Rc, rg=rg, th=int(th), online=True))
    return out


def outcome(A, cc, p):
    a = A[p['arm']]
    stop = np.minimum(a['fz'], p['Rc'])
    fail = a['ierr'][np.arange(len(stop)), stop - 1] > 0
    if p['rg'] is not None:
        give = (a['fz'] > p['rg']) & (a['syn'][:, p['rg'] - 1] > p['th'])
        stop = np.where(give, p['rg'], stop)
        fail = fail | give
    return fail, cc[p['arm']][stop - 1], stop


def select(A, cc, pols, idx, delta, keep):
    best = None
    for p in pols:
        if not keep(p):
            continue
        fail, cost, _ = outcome(A, cc, p)
        fer, c = float(fail[idx].mean()), float(cost[idx].mean())
        cx = (p['rg'] is not None) + (p['arm'] not in FIXED)
        key = (c, fer, cx)
        if fer <= delta + 1e-12 and (best is None or key < best[0]):
            best = (key, p)
    return None if best is None else best[1]


def name(p):
    return f"{p['arm']} Rc{p['Rc']}" + ('' if p['rg'] is None else f" giveup(r{p['rg']}, syn>{p['th']})")


def compare(A, cc, pb, pp, idx, rng):
    fb, cb, _ = outcome(A, cc, pb)
    fp, cp, _ = outcome(A, cc, pp)
    S = 1. - cp[idx].mean() / cb[idx].mean()
    d = float(fp[idx].mean() - fb[idx].mean())
    bi = rng.integers(0, len(idx), size=(B, len(idx)))
    J = idx[bi]
    Sb = 1. - cp[J].mean(1) / cb[J].mean(1)
    db = fp[J].mean(1) - fb[J].mean(1)
    return dict(S=float(S), S_ci=[float(np.percentile(Sb, 2.5)), float(np.percentile(Sb, 97.5))], d=d,
                d_ci=[float(np.percentile(db, 2.5)), float(np.percentile(db, 97.5))],
                fer_base=float(fb[idx].mean()), fer_pol=float(fp[idx].mean()), cost_base=float(cb[idx].mean()), cost_pol=float(cp[idx].mean()))



LEVELS = {16: (.05, .075, .10, .125, .15), 20: (.15, .20, .25)}
MARGIN = .02
md = ['# POST HOC frontier diagnostic (not a decision input): fixed vs online classes across target FER, cost = timing-reference s', '',
      'dev = frames 0-299 (selection), test = 300-599. (a) both classes selected on dev with dev FER <= level; (b) online selected with',
      f'dev FER <= level - {MARGIN} (margin rule), fixed with <= level; (c) in-sample test frontier (optimistic for both, more for online).', '']
out = {}
for L in (16, 20):
    frames, A = arrays(L)
    dev, test = frames < DEV_MAX, frames >= DEV_MAX
    di, ti = np.where(dev)[0], np.where(test)[0]
    pols = policies(A, dev)
    cc = cumcost(L, 'sec')
    ev = [(p,) + outcome(A, cc, p)[:2] for p in pols]
    md += [f'## L{L}', '', '| level | (a) fixed test cost/FER | (a) online test cost/FER | (a) saving | (b) online+margin cost/FER | (b) saving | (c) fixed | (c) online | (c) saving |',
           '|---|---|---|---|---|---|---|---|---|']
    rows_l = []
    for lv in LEVELS[L]:
        def pick(keep, lim):
            best = None
            for p, f, c in ev:
                if not keep(p):
                    continue
                fd, cd = f[di].mean(), c[di].mean()
                if fd <= lim + 1e-12 and (best is None or (cd, fd) < best[0]):
                    best = ((cd, fd), f, c)
            return None if best is None else (best[2][ti].mean(), best[1][ti].mean())
        def front(keep):
            best = None
            for p, f, c in ev:
                if keep(p) and f[ti].mean() <= lv + 1e-12:
                    v = c[ti].mean()
                    best = v if best is None or v < best else best
            return best
        fx, on, onm = pick(lambda p: not p['online'], lv), pick(lambda p: True, lv), pick(lambda p: True, lv - MARGIN)
        cf, co = front(lambda p: not p['online']), front(lambda p: True)
        sv = lambda a, b: None if (a is None or b is None) else 1 - a[0] / b[0]
        r = dict(level=lv, fixed=fx, online=on, online_margin=onm, saving=sv(on, fx), saving_margin=sv(onm, fx),
                 front_fixed=cf, front_online=co, front_saving=None if (cf is None or co is None) else 1 - co / cf)
        rows_l.append(r)
        fmt = lambda t: '-' if t is None else f'{t[0]:.3f} / {t[1]:.3f}'
        f3 = lambda x: '-' if x is None else f'{x:.3f}'
        md.append(f"| {lv} | {fmt(fx)} | {fmt(on)} | {f3(r['saving'])} | {fmt(onm)} | {f3(r['saving_margin'])} | {f3(cf)} | {f3(co)} | {f3(r['front_saving'])} |")
    md.append('')
    out[f'L{L}'] = rows_l
OUT = P(args.out)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'frontier.json').write_text(json.dumps(dict(_argv=sys.argv, _config=res['_config'], rows=out), indent=1, default=float) + '\n')
(OUT / 'frontier.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
