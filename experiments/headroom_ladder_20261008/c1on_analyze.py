#!/usr/bin/env python
"""T1-T3: online-scheduling headroom (A') and scalar-state sufficiency (A) from stored 10-round rows
(research/c1-online-headroom-T123.md, FROZEN before this analysis).  Rows and JSON only; no simulation.
    python -B c1on_analyze.py [--t20-dirs out/c1g_r10lo,out/c1f_r10] [--t40-dir out/c1ib2_r10] [--time-dir out/c1ib2_time] [--out out/c1on/analysis]
Data: 6.5 dB, rho .3, frames 0-299, L 16-32; T20 = FULL_R10 rows, T40 = R10T40 rows; per-round ierr<r>, syn<r>, ll_in<r>.
Cost C_T(L, r) = mean t_cum[r-1] of the quiet timing reference (R10T20 / R10T40, frames 0-9) at that (T, L).
T1  fixed family {(T, Rc)} with syndrome early stop; best fixed = cheapest with FER <= .10; matched-FER oracle saving S1, bootstrap CI.
T2  deployable give-up rule (syn_{r_g} > theta) on the best fixed member; select on frames 0-149, evaluate on 150-299.
T3  logistic next-round success: M0 [1, I, I^2, k, I k] vs M1 = M0 + [dI, r, log(1+syn)]; 2-fold by frame; held-out log-loss.
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
SNR, RHO, RMAX = 650, 300, 10
LS, TS = (16, 20, 24, 28, 32), (20, 40)
ARM = {20: 'FULL_R10', 40: 'R10T40'}
DELTA, GATE, FER_TOL, B, SEED, SPLIT = .10, .15, .01, 1000, 20261014, 150

ap = argparse.ArgumentParser()
ap.add_argument('--t20-dirs', default='out/c1g_r10lo,out/c1f_r10')
ap.add_argument('--t40-dir', default='out/c1ib2_r10')
ap.add_argument('--time-dir', default='out/c1ib2_time')
ap.add_argument('--out', default='out/c1on/analysis')
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


def load(dirs, arm):
    out = {}
    for d in dirs:
        for f in files_of(d):
            for x in open(f):
                if not x.strip():
                    continue
                r = json.loads(x)
                if r['status'] != 'ok' or r['arm'] != arm or r['snr_centi_db'] != SNR or r['rho_permille'] != RHO or r['L'] not in LS:
                    continue
                k = (r['L'], r['frame'])
                if k in out:
                    raise ValueError(f'duplicate {arm} {k}')
                out[k] = r
    return out


dirs = {20: [s for s in args.t20_dirs.split(',') if s], 40: [args.t40_dir]}
rows = {T: load(dirs[T], ARM[T]) for T in TS}
frames = sorted(set.intersection(*[{f for (L, f) in rows[T] if L == L0} for T in TS for L0 in LS]))
n = len(frames)
res = dict(_argv=sys.argv, _config=dict(snr=SNR, rho=RHO, Ls=list(LS), Ts=list(TS), arms=ARM, delta=DELTA, gate=GATE, fer_tol=FER_TOL, B=B, seed=SEED,
                                         split=SPLIT, dirs=dict(t20=dirs[20], t40=dirs[40], time=args.time_dir),
                                         md5=dict(script=md5(Path(__file__)),
                                                  rows={d: {Path(f).name: md5(f) for f in files_of(d)} for d in dirs[20] + dirs[40] + [args.time_dir]})),
           n_frames=n, frames=[frames[0], frames[-1]] if frames else None)
if n != 300:
    raise ValueError(f'{n} common frames, expected 300')
fidx = np.array(frames)
IERR, SYN, LL = {}, {}, {}
for T in TS:
    for L in LS:
        rr = [rows[T][(L, f)] for f in frames]
        IERR[(T, L)] = np.array([[r[f'ierr{q}'] for q in range(1, RMAX + 1)] for r in rr])
        SYN[(T, L)] = np.array([[r[f'syn{q}'] for q in range(1, RMAX + 1)] for r in rr])
        LL[(T, L)] = np.array([[r[f'll_in{q}'] for q in range(1, RMAX + 1)] for r in rr], float)

# cost reference
trows = [json.loads(x) for f in files_of(args.time_dir) for x in open(f) if x.strip()]
trows = [r for r in trows if r['status'] == 'ok' and r['snr_centi_db'] == SNR and r['rho_permille'] == RHO]
COST = {}
for T in TS:
    for L in LS:
        tt = [r['t_cum'] for r in trows if r['arm'] == f'R10T{T}' and r['L'] == L]
        if not tt or any(len(t) != RMAX for t in tt):
            raise ValueError(f'timing reference missing for T{T} L{L}')
        COST[(T, L)] = np.mean(np.array(tt, float), axis=0)
UNIT = {(T, L): T * np.arange(1, RMAX + 1, dtype=float) for T in TS for L in LS}
res['cost_s'] = {f'T{T}_L{L}': COST[(T, L)].tolist() for T in TS for L in LS}
md = ['# T1-T3: online-scheduling headroom and scalar-state sufficiency (6.5 dB, rho .3, frames 0-299)', '',
      f'Frames {n}; cost = quiet timing reference t_cum by (T, L, round); secondary unit = inner updates r*T.', '']


def first_zero(syn):
    z = syn == 0
    return np.where(z.any(axis=1), z.argmax(axis=1) + 1, RMAX + 1)


FZ = {k: first_zero(v) for k, v in SYN.items()}


def members(L, cost):
    out = []
    for T in TS:
        for Rc in range(1, RMAX + 1):
            stop = np.minimum(FZ[(T, L)], Rc)
            fail = IERR[(T, L)][np.arange(n), stop - 1] > 0
            out.append(dict(T=T, Rc=Rc, stop=stop, fail=fail, cost=cost[(T, L)][stop - 1]))
    return out


def best_fixed(M, idx):
    best = None
    for i, m in enumerate(M):
        fer = float(m['fail'][idx].mean())
        c = float(m['cost'][idx].mean())
        if fer <= DELTA + 1e-12 and (best is None or c < best[2]):
            best = (i, fer, c)
    return best


def oracle(M, idx, n_fail_allowed, give_cost):
    F = np.stack([m['fail'][idx] for m in M])
    C = np.stack([m['cost'][idx] for m in M])
    succ_cost = np.where(~F, C, np.inf).min(axis=0)
    fail_all = ~np.isfinite(succ_cost)
    cost = np.where(fail_all, give_cost, succ_cost)
    own = float(cost.mean()), float(fail_all.mean())
    extra = int(n_fail_allowed - fail_all.sum())
    if extra > 0:
        order = np.argsort(-np.where(fail_all, -np.inf, succ_cost))[:extra]
        cost = cost.copy()
        cost[order] = give_cost
    return float(cost.mean()), own


# ================================================================ T1
t1 = {}
rng = np.random.default_rng(SEED)
boot_idx = rng.integers(0, n, size=(B, n))
md += ['## T1 oracle headroom (matched-FER oracle vs best fixed schedule with syndrome early stop)', '',
       '| L | K | best fixed (T, Rc) | FER | cost s | oracle cost s | S1 [95% CI] | S1 (own FER) | S1 (unit r*T) |', '|---|---|---|---|---|---|---|---|---|']
for L in LS:
    M = members(L, COST)
    give = min(COST[(T, L)][0] for T in TS)
    allidx = np.arange(n)
    bf = best_fixed(M, allidx)
    if bf is None:
        t1[L] = dict(operable=False)
        md.append(f'| {L} | {8 * L} | not operable (no member with FER <= {DELTA}) | | | | | | |')
        continue
    m = M[bf[0]]
    oc, own = oracle(M, allidx, int(m['fail'].sum()), give)
    s1 = 1. - oc / bf[2]
    s1_own = 1. - own[0] / bf[2]
    bs = []
    for idx in boot_idx:
        b = best_fixed(M, idx)
        if b is None:
            continue
        oc_b, _ = oracle(M, idx, int(M[b[0]]['fail'][idx].sum()), give)
        bs.append(1. - oc_b / b[2])
    lo, hi = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))) if bs else (None, None)
    Mu = members(L, UNIT)
    bfu = best_fixed(Mu, allidx)
    ocu, _ = oracle(Mu, allidx, int(Mu[bfu[0]]['fail'].sum()), min(UNIT[(T, L)][0] for T in TS))
    s1u = 1. - ocu / bfu[2]
    t1[L] = dict(operable=True, best=dict(T=m['T'], Rc=m['Rc'], fer=bf[1], cost=bf[2]), oracle_cost=oc, S1=s1, ci=[lo, hi], n_boot=len(bs),
                 S1_own_fer=s1_own, oracle_own_fer=own[1], S1_unit=s1u, best_unit=dict(T=Mu[bfu[0]]['T'], Rc=Mu[bfu[0]]['Rc']))
    md.append(f"| {L} | {8 * L} | T{m['T']}, R{m['Rc']} | {bf[1]:.3f} | {bf[2]:.3f} | {oc:.3f} | {s1:.3f} [{lo:.3f}, {hi:.3f}] | {s1_own:.3f} | {s1u:.3f} |")
oper = [L for L in LS if t1[L]['operable']]
t1_pass = [L for L in oper if t1[L]['S1'] >= GATE]
res['T1'] = dict(per_L={str(L): v for L, v in t1.items()}, operable=oper, pass_L=t1_pass, decision='T2' if t1_pass else 'A-first')
md += ['', f"**T1 decision: {'go to T2 (headroom >= .15 at L ' + str(t1_pass) + ')' if t1_pass else 'A-first (oracle headroom < .15 at every operable L)'}**", '']


# ================================================================ T2
def auc(score, label):
    pos, neg = score[label], score[~label]
    if len(pos) == 0 or len(neg) == 0:
        return None
    allv = np.concatenate([pos, neg])
    ranks = np.argsort(np.argsort(allv, kind='mergesort'), kind='mergesort') + 1.
    _, inv, counts = np.unique(allv, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    ranks = (sums / counts)[inv]
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


t2 = {}
dev, test = fidx < SPLIT, fidx >= SPLIT
md += ['## T2 deployable give-up rule (select on frames 0-149, evaluate on 150-299)', '',
       '| L | base | rule (r_g, theta) | dev saving / dFER | test saving / dFER | AUC syn_r (r=1..4) |', '|---|---|---|---|---|---|']
for L in oper:
    b = t1[L]['best']
    T, Rc = b['T'], b['Rc']
    stop = np.minimum(FZ[(T, L)], Rc)
    fail0 = IERR[(T, L)][np.arange(n), stop - 1] > 0
    cost0 = COST[(T, L)][stop - 1]
    aucs = []
    for r in range(1, 5):
        live = FZ[(T, L)] > r
        aucs.append(auc(SYN[(T, L)][live, r - 1].astype(float), fail0[live]) if live.sum() > 1 and r < Rc else None)
    best = None
    for rg in range(1, min(4, Rc - 1) + 1):
        live = FZ[(T, L)] > rg
        for th in np.unique(SYN[(T, L)][dev & live, rg - 1]):
            give = live & (SYN[(T, L)][:, rg - 1] > th)
            f1 = fail0 | give
            c1 = np.where(give, COST[(T, L)][rg - 1], cost0)
            dfer = float(f1[dev].mean() - fail0[dev].mean())
            sav = 1. - c1[dev].mean() / cost0[dev].mean()
            if dfer <= FER_TOL + 1e-12 and (best is None or sav > best[0] + 1e-12 or (abs(sav - best[0]) <= 1e-12 and dfer < best[1])):
                best = (sav, dfer, rg, int(th))
    if best is None:
        t2[L] = dict(base=dict(T=T, Rc=Rc), rule=None, auc=aucs)
        md.append(f"| {L} | T{T}, R{Rc} | none (Rc = 1 or no admissible rule) | | | {aucs} |")
        continue
    sav, dfer, rg, th = best
    give = (FZ[(T, L)] > rg) & (SYN[(T, L)][:, rg - 1] > th)
    f1 = fail0 | give
    c1 = np.where(give, COST[(T, L)][rg - 1], cost0)
    tsav = 1. - c1[test].mean() / cost0[test].mean()
    tdfer = float(f1[test].mean() - fail0[test].mean())
    t2[L] = dict(base=dict(T=T, Rc=Rc), rule=dict(r_g=rg, theta=th), dev=dict(saving=sav, dfer=dfer), test=dict(saving=float(tsav), dfer=tdfer,
                 base_fer=float(fail0[test].mean())), auc=aucs, viable=bool(tsav >= GATE and tdfer <= FER_TOL + 1e-12))
    md.append(f"| {L} | T{T}, R{Rc} | ({rg}, {th}) | {sav:.3f} / {dfer:+.3f} | {tsav:.3f} / {tdfer:+.3f} | "
              + ' '.join('-' if a is None else f'{a:.2f}' for a in aucs) + ' |')
t2_viable = [L for L in t1_pass if t2.get(L, {}).get('viable')]
res['T2'] = dict(per_L={str(L): v for L, v in t2.items()}, viable_L=t2_viable,
                 decision=('A-prime-first candidate' if t2_viable else 'A-first') if t1_pass else 'not decisive (T1 failed; report-only)')
md += ['', f"**T2 decision: {res['T2']['decision']}**" + (f' (viable at L {t2_viable})' if t2_viable else ''), '']


# ================================================================ T3
def samples(T):
    X, Y, F = [], [], []
    for L in LS:
        I = 1. - LL[(T, L)]
        for i in range(n):
            for r in range(1, RMAX):
                if FZ[(T, L)][i] <= r:
                    break
                Ir = I[i, r - 1]
                dI = Ir - I[i, r - 2] if r >= 2 else 0.
                k = 8 * L / 256.
                X.append([Ir, Ir * Ir, k, Ir * k, dI, float(r), np.log1p(SYN[(T, L)][i, r - 1])])
                Y.append(float(IERR[(T, L)][i, r] == 0))
                F.append(fidx[i])
    return np.array(X), np.array(Y), np.array(F)


def fit_logistic(X, y, lam=1e-4, iters=60):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.
    Z = np.hstack([np.ones((len(X), 1)), (X - mu) / sd])
    w = np.zeros(Z.shape[1])
    R = lam * np.eye(Z.shape[1])
    R[0, 0] = 0.
    for _ in range(iters):
        p = 1. / (1. + np.exp(-np.clip(Z @ w, -30, 30)))
        g = Z.T @ (p - y) + R @ w
        Hm = (Z * (p * (1 - p))[:, None]).T @ Z + R
        step = np.linalg.solve(Hm, g)
        w -= step
        if np.max(np.abs(step)) < 1e-9:
            break
    return lambda Xn: 1. / (1. + np.exp(-np.clip(np.hstack([np.ones((len(Xn), 1)), (Xn - mu) / sd]) @ w, -30, 30)))


def logloss(p, y):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


M0, M1 = [0, 1, 2, 3], [0, 1, 2, 3, 4, 5, 6]
HIST = {4: 'dI', 5: 'round', 6: 'log1p(syn)'}
t3 = {}
md += ['## T3 scalar-state sufficiency (held-out log-loss, nats; Delta = LL(M0) - LL(M1))', '',
       '| T | fold (train -> test) | n test | LL M0 | LL M1 | Delta | drop-one increase (dI / round / syn) |', '|---|---|---|---|---|---|---|']
for T in TS:
    X, Y, F = samples(T)
    folds = []
    for name, tr, te in (('A', F < SPLIT, F >= SPLIT), ('B', F >= SPLIT, F < SPLIT)):
        ll0 = logloss(fit_logistic(X[tr][:, M0], Y[tr])(X[te][:, M0]), Y[te])
        ll1 = logloss(fit_logistic(X[tr][:, M1], Y[tr])(X[te][:, M1]), Y[te])
        drop = {}
        for j, nm in HIST.items():
            cols = [c for c in M1 if c != j]
            drop[nm] = logloss(fit_logistic(X[tr][:, cols], Y[tr])(X[te][:, cols]), Y[te]) - ll1
        folds.append(dict(fold=name, n_test=int(te.sum()), ll0=ll0, ll1=ll1, delta=ll0 - ll1, drop=drop, base_rate=float(Y[te].mean())))
        md.append(f"| {T} | {name} | {int(te.sum())} | {ll0:.4f} | {ll1:.4f} | {ll0 - ll1:+.4f} | "
                  + ' / '.join(f'{drop[k]:+.4f}' for k in ('dI', 'round', 'log1p(syn)')) + ' |')
    t3[T] = dict(n_samples=int(len(Y)), folds=folds)
deltas = [f['delta'] for T in TS for f in t3[T]['folds']]
dec3 = ('scalar state insufficient (A needs >= 2 states)' if all(d >= .02 for d in deltas)
        else 'scalar state suffices at this condition' if all(d < .005 for d in deltas) else 'inconclusive')
res['T3'] = dict(per_T={str(T): v for T, v in t3.items()}, decision=dec3)
md += ['', f'**T3 decision: {dec3}**', '']

OUT = P(args.out)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'on.json').write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else float(o)) + '\n')
(OUT / 'on.md').write_text('\n'.join(md) + '\n')
print('\n'.join(md))
