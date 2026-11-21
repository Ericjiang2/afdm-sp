#!/usr/bin/env python
"""POST HOC variant of c1esc_analyze.py (written after the frozen result; NOT a decision input).
Change: online policies are selected under dev FER <= min(delta, dev FER(B*) + .01) (matched reliability) instead of <= delta.
A' escalation test analysis (research/c1-escalation-A-prime.md).  Rows and JSON only.
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
ap.add_argument('--out', default='out/c1esc/analysis_posthoc')
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
md = ['# POST HOC (matched-reliability selection; not a decision input) -- A\' escalation test: start T20, escalate to T40 if not decoded by round e (6.5 dB, rho .3, frames 0-599)', '',
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


rng = np.random.default_rng(SEED)
out = {}
for (L, delta, primary) in CONDS:
    frames, A = arrays(L)
    dev, test = frames < DEV_MAX, frames >= DEV_MAX
    di, ti = np.where(dev)[0], np.where(test)[0]
    pols = policies(A, dev)
    ent = dict(delta=delta, primary=primary, n_policies=len(pols))
    md += [f'## L{L} (K {8 * L}), delta {delta}' + (' -- PRIMARY' if primary else ' -- report-only'), '']
    for unit in ('sec', 'updates'):
        cc = cumcost(L, unit)
        pb = select(A, cc, pols, di, delta, lambda p: not p['online'])
        delta_p = delta if pb is None else min(delta, float(outcome(A, cc, pb)[0][di].mean()) + FER_TOL)
        sel = dict(all=select(A, cc, pols, di, delta_p, lambda p: True),
                   escalation_only=select(A, cc, pols, di, delta_p, lambda p: p['arm'] not in FIXED and p['rg'] is None),
                   giveup_only=select(A, cc, pols, di, delta_p, lambda p: p['arm'] in FIXED and p['rg'] is not None))
        u = dict(base=None if pb is None else name(pb), policies={})
        if pb is None:
            md += [f'[{unit}] no fixed schedule reaches dev FER <= {delta}; not operable.', '']
            ent[unit] = u
            continue
        md += [f'[{unit}] B* = {name(pb)}', '', '| online policy (selected on dev) | P* | test cost base -> P* | test FER base -> P* | S [95% CI] | d [95% CI] |',
               '|---|---|---|---|---|---|']
        for k, pp in sel.items():
            if pp is None:
                md.append(f'| {k} | none admissible | | | | |')
                continue
            c = compare(A, cc, pb, pp, ti, rng)
            u['policies'][k] = dict(policy=name(pp), **c)
            md.append(f"| {k} | {name(pp)} | {c['cost_base']:.3f} -> {c['cost_pol']:.3f} | {c['fer_base']:.3f} -> {c['fer_pol']:.3f} | "
                      f"{c['S']:.3f} [{c['S_ci'][0]:.3f}, {c['S_ci'][1]:.3f}] | {c['d']:+.3f} [{c['d_ci'][0]:+.3f}, {c['d_ci'][1]:+.3f}] |")
        if unit == 'sec':
            # measured t_cum of this run (load-noisy), same selected policies
            meas = {a: None for a in ARMS}
            pa = u['policies'].get('all')
            if pa is not None:
                fb, _, sb = outcome(A, cc, pb)
                fp, _, sp = outcome(A, cc, sel['all'])
                mb = np.array([A[pb['arm']]['tcum'][i, sb[i] - 1] for i in ti])
                mp = np.array([A[sel['all']['arm']]['tcum'][i, sp[i] - 1] for i in ti])
                u['measured_S_all'] = float(1. - mp.mean() / mb.mean())
                md += ['', f"Measured-time saving of P*(all) on test (run t_cum, load-noisy, report-only): {u['measured_S_all']:.3f}"]
            # oracle headroom on all frames (reference)
            allidx = np.arange(len(frames))
            F = np.stack([outcome(A, cc, dict(arm=a, Rc=Rc, rg=None, th=None))[0] for a in ARMS for Rc in range(1, R + 1)])
            C = np.stack([outcome(A, cc, dict(arm=a, Rc=Rc, rg=None, th=None))[1] for a in ARMS for Rc in range(1, R + 1)])
            sc = np.where(~F, C, np.inf).min(0)
            fa = ~np.isfinite(sc)
            give_c = min(cc[a][0] for a in ARMS)
            fb_all, cb_all, _ = outcome(A, cc, pb)
            cost = np.where(fa, give_c, sc)
            extra = int(fb_all.sum() - fa.sum())
            if extra > 0:
                o = np.argsort(-np.where(fa, -np.inf, sc))[:extra]
                cost[o] = give_c
            u['oracle_S_allframes'] = float(1. - cost.mean() / cb_all.mean())
            md += [f"Oracle headroom vs B* on all 600 frames (matched FER, reference): {u['oracle_S_allframes']:.3f}", '']
        else:
            md.append('')
        ent[unit] = u
    if primary:
        pa = ent['sec']['policies'].get('all')
        viable = bool(pa is not None and pa['S'] >= GATE and pa['S_ci'][0] > 0 and pa['d'] <= FER_TOL + 1e-12)
        ent['A_prime_viable'] = viable
        md += [f"**PRIMARY decision (L{L}, delta {delta}): A' {'VIABLE' if viable else 'NOT viable -> demote to remark; direction A only'}**"
               + ('' if pa is None else f" (S = {pa['S']:.3f} [{pa['S_ci'][0]:.3f}, {pa['S_ci'][1]:.3f}], d = {pa['d']:+.3f})"), '']
    out[f'L{L}'] = ent
res['conds'] = out
OUT = P(args.out)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'esc_posthoc.json').write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else float(o)) + '\n')
(OUT / 'esc_posthoc.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
