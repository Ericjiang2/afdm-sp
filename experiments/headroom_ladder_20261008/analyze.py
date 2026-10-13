#!/usr/bin/env python
"""Headroom ladder / E-rho analysis. Input: run dir(s) with rows_shard*.jsonl (driver.py rows).
Output: <out-dir>/ANALYSIS.md + analysis.json (with _argv and input md5s). numpy + scipy only.

Conventions
  frame error = info_errors > 0 (driver.py merge definition); decode failure = syndrome != 0 (reported).
  unit (= frame, resampled jointly over every rho/snr/arm cell it appears in) =
      (run dir, channel_seed, physical_gains_sha256, info_sha256).  Population mode has different
      frames per SNR -> units appear in one cell only; bootstrap is stratified by cell-presence signature.
  crossing SNR: log-linear interpolation of log10 FER vs SNR (dB), first FER<=target scanning upward;
      FER==0 cell uses floor 0.5/n.  shift = x(rho)-x(ref rho) (negative = lower rho saves SNR);
      to_A3 = x(arm)-x(A3) (>0 = dB gap to PCSI); step = x(prev)-x(next) (>0 = dB recovered).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

ARMS = ('F0', 'A0', 'PS0', 'PS', 'O1', 'O2', 'O2n', 'O3', 'O5', 'OF2', 'OF3', 'A1', 'A2', 'A3')  # PS*/O* = F2 arms (absent in older runs)
K_INFO = 1024  # LDPC info bits (e1_ldpc free_cols), rate 1/2, n=2048
Z = 1.959964
GN = 'rho'  # group column name ('config' with --group config)
LABELS = {}  # group value (rho_permille/1000) -> label, config mode only
REASON = {0: 'ok', 1: 'FER<=target at lowest SNR (no bracket)', 2: 'FER>target at all SNR',
          3: '<2 SNR points / empty cell', 4: 'ok; zero-FER floor 0.5/n above target (resolution-limited)'}


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def wilson(k, n):
    if n == 0:
        return math.nan, math.nan
    p, d = k / n, 1 + Z * Z / n
    c, h = (p + Z * Z / (2 * n)) / d, Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return c - h, c + h


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * float(stats.binom.cdf(min(b, c), n, .5)))


# ------------------------------------------------------------------------------ data
class Data:
    def __init__(self, rows):
        ok = [r for r in rows if r['status'] == 'ok']
        self.n_err_rows = len(rows) - len(ok)
        self.rhos = sorted({r['rho_permille'] for r in ok})
        self.snrs = sorted({r['snr_centi_db'] for r in ok})
        self.arms = [a for a in ARMS if any(r['arm'] == a for r in ok)]
        uid = {}
        for r in ok:
            uid.setdefault((r['_run'], r['channel_seed'], r['physical_gains_sha256'], r['info_sha256']), len(uid))
        self.U, R, S = len(uid), len(self.rhos), len(self.snrs)
        ri, si = {v: i for i, v in enumerate(self.rhos)}, {v: i for i, v in enumerate(self.snrs)}
        keys = ('fail', 'dec_fail', 'undet', 'info_err', 'logloss', 'seconds', 'trig')
        self.F = {a: {k: np.full((R, S, self.U), np.nan) for k in keys} for a in self.arms}
        self.dups, self.a0 = 0, []
        for r in ok:
            a, i = r['arm'], (ri[r['rho_permille']], si[r['snr_centi_db']],
                              uid[(r['_run'], r['channel_seed'], r['physical_gains_sha256'], r['info_sha256'])])
            F = self.F[a]
            if np.isfinite(F['fail'][i]):
                self.dups += 1
                continue
            e = r['info_errors']
            for k, v in (('fail', e > 0), ('dec_fail', not r['decode_ok']), ('undet', r['decode_ok'] and e > 0),
                         ('info_err', e), ('logloss', r['logloss_bits']), ('seconds', r['seconds']),
                         ('trig', float(bool(r['triggered'])) if a == 'A0' else math.nan)):
                F[k][i] = v
            if a == 'A0':
                self.a0.append(dict(ri=i[0], si=i[1], u=i[2], fail=float(e > 0), rho=r['rho'], snr=r['snr_db'],
                                    g2=np.asarray(r['truth_g2']), pdp=r['pdp_total'],
                                    mef=r.get('missed_energy_fraction', math.nan),
                                    underfit=float(r.get('same_delay_underfit', False)),
                                    distinct_lt=float(r['n_distinct_delays'] < r['n_paths']),
                                    nfit=float(r.get('n_fit_slots', math.nan)), npaths=float(r['n_paths']),
                                    ndist=float(r['n_distinct_delays']),
                                    maxspread=float(r.get('max_tap_spread', math.nan)),
                                    maxrays=float(r.get('max_rays_per_tap', math.nan))))
        P = np.stack([np.isfinite(self.F[a]['fail']) for a in self.arms], -1)  # (R,S,U,A)
        sig = np.moveaxis(P, 2, 0).reshape(self.U, -1)
        groups = {}
        for u in range(self.U):
            groups.setdefault(sig[u].tobytes(), []).append(u)
        self.strata = [np.array(g) for g in groups.values()]


def weights(strata, U, c, rng):
    W = np.zeros((c, U))
    for idx in strata:
        W[:, idx] = rng.multinomial(len(idx), np.full(len(idx), 1. / len(idx)), size=c)
    return W


def boot_ratio(Su, n, B, rng, chunk=500):
    out, U = np.empty(B), len(Su)
    for i in range(0, B, chunk):
        c = min(chunk, B - i)
        idx = rng.integers(0, U, size=(c, U))
        out[i:i + c] = Su[idx].sum(1) / n[idx].sum(1)
    return out


def summ(v):
    """v[0] point estimate, v[1:] bootstrap draws."""
    b = np.asarray(v[1:], float)
    fin = np.isfinite(b)
    lo, hi = np.percentile(b[fin], [2.5, 97.5]) if fin.sum() >= 50 else (math.nan, math.nan)
    return dict(est=float(v[0]), lo=float(lo), hi=float(hi), valid=float(fin.mean()) if len(b) else math.nan)


# ------------------------------------------------------------------- 1. per-cell table
def table1(D):
    out = []
    for ri, rho in enumerate(D.rhos):
        for si, snr in enumerate(D.snrs):
            for a in D.arms:
                F = D.F[a]
                m = np.isfinite(F['fail'][ri, si])
                n = int(m.sum())
                if n == 0:
                    continue
                k = int(F['fail'][ri, si][m].sum())
                lo, hi = wilson(k, n)
                out.append(dict(rho=rho / 1000, snr=snr / 100, arm=a, frames=n, frame_err=k, fer=k / n, lo=lo, hi=hi,
                                decode_fail=int(F['dec_fail'][ri, si][m].sum()),
                                undetected=int(F['undet'][ri, si][m].sum()),
                                ber=float(F['info_err'][ri, si][m].sum() / (n * K_INFO)),
                                logloss=float(F['logloss'][ri, si][m].mean()),
                                seconds=float(F['seconds'][ri, si][m].mean()),
                                trig=float(F['trig'][ri, si][m].mean()) if a == 'A0' else None))
    return out


# ------------------------------------------------------------------ 2. ladder pairing
def ladder(D, B, rng):
    steps, rescue = [], []
    for ri, rho in enumerate(D.rhos):
        for si in list(range(len(D.snrs))) + [None]:
            ix = slice(None) if si is None else slice(si, si + 1)
            get = lambda a, k: D.F[a][k][ri][ix]  # noqa: E731
            chain = [a for a in D.arms if np.isfinite(get(a, 'fail')).any()]
            tag = dict(rho=rho / 1000, snr='ALL' if si is None else D.snrs[si] / 100)
            for p, q in zip(chain[:-1], chain[1:]):
                a, b = get(p, 'fail'), get(q, 'fail')
                m = np.isfinite(a) & np.isfinite(b)
                if not m.any():
                    continue
                resc, harm = int(((a == 1) & (b == 0) & m).sum()), int(((a == 0) & (b == 1) & m).sum())
                d = np.where(m, get(q, 'logloss') - get(p, 'logloss'), 0.).sum(0)
                n = m.sum(0).astype(float)
                sel = n > 0
                bs = boot_ratio(d[sel], n[sel], B, rng)
                steps.append(dict(tag, step=f'{p}->{q}', n=int(m.sum()), fail_prev=int(((a == 1) & m).sum()),
                                  fail_next=int(((b == 1) & m).sum()), rescues=resc, harms=harm,
                                  p_mcnemar=mcnemar(resc, harm), dlogloss=float(d.sum() / n.sum()),
                                  dll_lo=float(np.percentile(bs, 2.5)), dll_hi=float(np.percentile(bs, 97.5))))
            if 'A0' in chain:
                f0 = get('A0', 'fail') == 1
                for q in chain:
                    if q in ('A1', 'A2', 'A3', 'PS', 'O1', 'O2', 'O2n', 'O3', 'O5', 'OF2', 'OF3'):
                        b = get(q, 'fail')
                        rescue.append(dict(tag, arm=q, a0_fail=int(f0.sum()),
                                           rescued=int((f0 & (b == 0)).sum()),
                                           frac=float((f0 & (b == 0)).sum() / f0.sum()) if f0.any() else math.nan))
    return steps, rescue


# ------------------------------------------------------- 3. bootstrap FER curves + dB
def boot_curves(D, B, rng, chunk=250):
    R, S, A = len(D.rhos), len(D.snrs), len(D.arms)
    Fz = np.moveaxis(np.stack([np.nan_to_num(D.F[a]['fail']) for a in D.arms], -1), 2, 0).reshape(D.U, -1)
    Pz = np.moveaxis(np.stack([np.isfinite(D.F[a]['fail']) for a in D.arms], -1), 2, 0).reshape(D.U, -1).astype(float)
    fer, neff = np.empty((B + 1, R * S * A)), np.empty((B + 1, R * S * A))
    start = 0
    while start <= B:
        c = 1 if start == 0 else min(chunk, B + 1 - start)
        W = np.ones((1, D.U)) if start == 0 else weights(D.strata, D.U, c, rng)
        num, den = W @ Fz, W @ Pz
        fer[start:start + c], neff[start:start + c] = np.where(den > 0, num / np.maximum(den, 1e-300), np.nan), den
        start += c
    return fer.reshape(B + 1, R, S, A), neff.reshape(B + 1, R, S, A)


def crossing(fer, neff, snr, target):
    """fer, neff: (B,S); snr ascending (dB). Returns x (B,), code (B,)."""
    Bn, S = fer.shape
    x, code = np.full(Bn, np.nan), np.zeros(Bn, int)
    if S < 2:
        return x, code + 3
    bad = np.isnan(fer).any(1)
    below = fer <= target
    j, has = below.argmax(1), below.any(1)
    code[~has], code[has & (j == 0)], code[bad] = 2, 1, 3
    idx = np.flatnonzero(has & (j > 0) & ~bad)
    jj = j[idx]
    f = np.where(fer == 0, .5 / np.maximum(neff, 1e-12), fer)
    y0, y1, yt = np.log10(f[idx, jj - 1]), np.log10(f[idx, jj]), math.log10(target)
    res = (fer[idx, jj] == 0) & (y1 >= yt)
    t = np.where(res, 1., (yt - y0) / np.where(res, 1., y1 - y0))
    x[idx] = snr[jj - 1] + t * (snr[jj] - snr[jj - 1])
    code[idx[res]] = 4
    return x, code


def db_analysis(D, fer, neff, targets, ref_rho):
    R, A = len(D.rhos), len(D.arms)
    snr = np.array(D.snrs) / 100
    ai = {a: i for i, a in enumerate(D.arms)}
    out = dict(cross=[], shift=[], to_a3=[], steps=[], kill=[], X={})
    for t in targets:
        X, C = np.full((fer.shape[0], R, A), np.nan), np.zeros((R, A), int)
        for r in range(R):
            for a in range(A):
                cols = np.flatnonzero(neff[0, r, :, a] > 0)
                if len(cols) < 2:
                    C[r, a] = 3
                    continue
                x, c = crossing(fer[:, r, cols, a], neff[:, r, cols, a], snr[cols], t)
                X[:, r, a], C[r, a] = x, c[0]
        out['X'][t] = X
        for r, rho in enumerate(D.rhos):
            for a in D.arms:
                out['cross'].append(dict(target=t, rho=rho / 1000, arm=a, reason=REASON[C[r, ai[a]]],
                                         **summ(X[:, r, ai[a]])))
                if rho / 1000 != ref_rho and round(ref_rho * 1000) in D.rhos:
                    out['shift'].append(dict(target=t, rho=rho / 1000, arm=a, **summ(X[:, r, ai[a]] -
                                             X[:, D.rhos.index(round(ref_rho * 1000)), ai[a]])))
                if a != 'A3' and 'A3' in ai:
                    out['to_a3'].append(dict(target=t, rho=rho / 1000, arm=a, **summ(X[:, r, ai[a]] - X[:, r, ai['A3']])))
            ch = [a for a in D.arms if a in ('A0', 'A1', 'A2', 'A3')]
            for p, q in zip(ch[:-1], ch[1:]):
                out['steps'].append(dict(target=t, rho=rho / 1000, step=f'{p}->{q}',
                                         **summ(X[:, r, ai[p]] - X[:, r, ai[q]])))
            if len(ch) >= 2 and ch[0] == 'A0' and ch[-1] == 'A3':
                tot = X[:, r, ai['A0']] - X[:, r, ai['A3']]
                row = dict(target=t, rho=rho / 1000, a0_to_a3=summ(tot))
                if 'A1' in ai and 'A2' in ai:
                    a01 = X[:, r, ai['A0']] - X[:, r, ai['A1']]
                    loc = X[:, r, ai['A1']] - X[:, r, ai['A3']]
                    row.update(a0_a1_share=summ(np.where(tot >= .05, a01 / np.where(tot >= .05, tot, 1), np.nan)),
                               a1_to_a3=summ(loc), rule_local_lt_0p1=bool(loc[0] < .1) if np.isfinite(loc[0]) else None,
                               rule_acq_share_ge_0p5=bool(a01[0] / tot[0] >= .5) if tot[0] >= .05 else None)
                out['kill'].append(row)
    return out


# ---------------------------------------------------------------------- 4. predictions
def p1_check(D, fer, neff):
    if len(D.rhos) < 2 or 'A0' not in D.arms:
        return None
    a, rows = D.arms.index('A0'), []
    for si, snr in enumerate(D.snrs + ['pool']):
        if snr == 'pool':
            c = (fer[:, :, :, a] * neff[:, :, :, a]).sum(2) / neff[:, :, :, a].sum(2)
        else:
            c = fer[:, :, si, a]
        if not np.isfinite(c[0]).all():
            continue
        best = int(np.argmin(c[0]))
        freq = np.bincount(np.nanargmin(np.where(np.isfinite(c[1:]), c[1:], 9), axis=1), minlength=len(D.rhos)) / (len(c) - 1)
        d = np.diff(c[0])
        row = dict(snr=snr if snr == 'pool' else snr / 100, fer={D.rhos[i] / 1000: float(c[0, i]) for i in range(len(D.rhos))},
                   argmin_rho=D.rhos[best] / 1000, n_tied_min=int((c[0] == c[0].min()).sum()),
                   interior=bool(0 < best < len(D.rhos) - 1), non_monotone=bool(not ((d >= 0).all() or (d <= 0).all())),
                   argmin_boot_freq={D.rhos[i] / 1000: float(freq[i]) for i in range(len(D.rhos))})
        if snr != 'pool' and 500 in D.rhos and D.rhos[best] != 500:
            x, y = D.F['A0']['fail'][best, si], D.F['A0']['fail'][D.rhos.index(500), si]
            m = np.isfinite(x) & np.isfinite(y)
            row['p_mcnemar_best_vs_0.5'] = mcnemar(int(((x == 0) & (y == 1) & m).sum()), int(((x == 1) & (y == 0) & m).sum()))
        rows.append(row)
    return rows


def p2_check(D, db, ref_rho, tol=.15):
    if 'A3' not in D.arms:
        return []
    ai, out = D.arms.index('A3'), []
    for t, X in db['X'].items():
        for r, rho in enumerate(D.rhos):
            if rho / 1000 == ref_rho or round(ref_rho * 1000) not in D.rhos:
                continue
            pred = 10 * math.log10((1 - ref_rho) / (1 - rho / 1000))
            obs = X[:, r, ai] - X[:, D.rhos.index(round(ref_rho * 1000)), ai]
            s, res = summ(obs), summ(obs - pred)
            out.append(dict(target=t, rho=rho / 1000, ref=ref_rho, obs=s, pred=pred, resid=res,
                            point_within_tol=bool(abs(res['est']) <= tol) if np.isfinite(res['est']) else None,
                            ci_within_tol=bool(res['lo'] >= -tol and res['hi'] <= tol) if np.isfinite(res['est']) and np.isfinite(res['lo']) else None))
    return out


def e_miss(rows, N, T):
    out = np.empty(len(rows))
    for i, r in enumerate(rows):
        sigma2 = 10 ** (-r['snr'] / 10)
        gamma = r['rho'] * N * r['g2'] / (sigma2 + (1 - r['rho']))
        out[i] = r['g2'][gamma < T].sum() / r['pdp']
    return out


def auc_prep(score, y, unit):
    """Weighted Mann-Whitney AUC (midrank ties) as f(W:(c,U)) -> (c,); unit-multiplicity weights."""
    o = np.argsort(score, kind='stable')
    s, yy, uu = score[o], y[o], unit[o]
    new = np.r_[True, s[1:] != s[:-1]]
    gid, st = np.cumsum(new) - 1, np.flatnonzero(new)
    en = np.r_[st[1:], len(s)]

    def f(W):
        w = W[:, uu]
        wn, wp = w * (yy == 0), w * (yy == 1)
        C = np.concatenate([np.zeros((len(W), 1)), np.cumsum(wn, 1)], 1)
        v = C[:, st][:, gid] + .5 * (C[:, en] - C[:, st])[:, gid]
        with np.errstate(invalid='ignore', divide='ignore'):
            return (wp * v).sum(1) / (wp.sum(1) * wn.sum(1))
    return f


def p3_check(D, args, rng):
    rows = D.a0
    if not rows:
        return None
    y = np.array([r['fail'] for r in rows])
    unit, rix, six = (np.array([r[k] for r in rows]) for k in ('u', 'ri', 'si'))
    preds = {'E_miss(T)': e_miss(rows, args.N, args.T), 'A0_missed_energy_fraction': np.array([r['mef'] for r in rows]),
             'same_delay_underfit': np.array([r['underfit'] for r in rows]),
             'n_distinct_delays<n_paths': np.array([r['distinct_lt'] for r in rows])}
    ones = np.ones((1, D.U))
    groups = [(f'{D.rhos[i] / 1000}', rix == i) for i in range(len(D.rhos))] + ([('all', np.ones(len(rows), bool))] if len(D.rhos) > 1 else [])
    res, fns = [], {}
    for g, mask in groups:
        for pn, sc in preds.items():
            if np.isnan(sc[mask]).any() or y[mask].min() == y[mask].max():
                res.append(dict(rho=g, pred=pn, auc=math.nan, auc_within_snr=math.nan, n=int(mask.sum()), n_fail=int(y[mask].sum())))
                continue
            fns[(g, pn)] = auc_prep(sc[mask], y[mask], unit[mask])
            w = []
            for s in range(len(D.snrs)):
                m = mask & (six == s)
                if m.any() and y[m].min() != y[m].max():
                    w.append(float(auc_prep(sc[m], y[m], unit[m])(ones)[0]))
            res.append(dict(rho=g, pred=pn, auc=float(fns[(g, pn)](ones)[0]), n=int(mask.sum()), n_fail=int(y[mask].sum()),
                            auc_within_snr=float(np.mean(w)) if w else math.nan, n_within_cells=len(w)))
    vals = {k: [] for k in fns}
    for i in range(0, args.B_aux, 100):
        W = weights(D.strata, D.U, min(100, args.B_aux - i), rng)
        for k, fn in fns.items():
            vals[k].append(fn(W))
    for r in res:
        k = (r['rho'], r['pred'])
        if k in vals:
            b = np.concatenate(vals[k])
            b = b[np.isfinite(b)]
            r['auc_lo'], r['auc_hi'] = (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))) if len(b) >= 50 else (math.nan,) * 2
    sens = []  # T sensitivity (point AUC, pooled per rho)
    for T in (math.log(1e4), math.log(1e5), math.log(1e6)):
        sc = e_miss(rows, args.N, T)
        for g, mask in groups:
            ok = y[mask].min() != y[mask].max()
            sens.append(dict(T=T, rho=g, auc=float(auc_prep(sc[mask], y[mask], unit[mask])(ones)[0]) if ok else math.nan))
    em = preds['E_miss(T)']
    desc = [dict(rho=D.rhos[i] / 1000, snr=D.snrs[s] / 100, mean_E_miss=float(em[(rix == i) & (six == s)].mean()),
                 frac_E_miss_pos=float((em[(rix == i) & (six == s)] > 0).mean()))
            for i in range(len(D.rhos)) for s in range(len(D.snrs)) if ((rix == i) & (six == s)).any()]
    return dict(T=args.T, N=args.N, auc=res, T_sensitivity=sens, E_miss_desc=desc)


# ----------------------------------------------------------------- F1 (clustered) section
LAMBDA = {'D1': 1, 'N4a': 4, 'N4b': 4, 'J4': 4, 'N8a': 8, 'N8b': 8, 'J8': 8}


def lab(v):
    return LABELS.get(v, v)


def f1_check(D, args, rng, db):
    """Clustered-channel tables: fitted slots vs truth, floors, gap + kill rule, failure-predictor AUC."""
    rows = D.a0
    out = dict(slots=[], floors=[], gaps=[], kill=[], auc=[])
    if not rows:
        return out
    rix, six, unit = (np.array([r[k] for r in rows]) for k in ('ri', 'si', 'u'))
    y = np.array([r['fail'] for r in rows])
    top = len(D.snrs) - 1
    fields = ('nfit', 'npaths', 'ndist', 'underfit', 'mef')
    for gi, rho in enumerate(D.rhos):
        for tag, mask in (('all SNR', rix == gi), (f'{D.snrs[top] / 100:.1f} dB', (rix == gi) & (six == top))):
            if not mask.any():
                continue
            v = {k: np.array([r[k] for r in rows])[mask] for k in fields}
            out['slots'].append(dict(rho=rho / 1000, cell=tag, n=int(mask.sum()), fit_slots=float(v['nfit'].mean()),
                                     frac_fit_slots_8=float((v['nfit'] >= 8).mean()), true_rays=float(v['npaths'].mean()),
                                     true_taps=float(v['ndist'].mean()),
                                     rays_per_tap=float((v['npaths'] / v['ndist']).mean()),
                                     frac_same_delay_underfit=float(v['underfit'].mean()),
                                     mean_missed_energy=float(v['mef'].mean())))
    ai = {a: i for i, a in enumerate(D.arms)}
    for gi, rho in enumerate(D.rhos):
        for si in (top,):
            row = dict(rho=rho / 1000, snr=D.snrs[si] / 100)
            for a in D.arms:
                m = np.isfinite(D.F[a]['fail'][gi, si])
                k, n = int(D.F[a]['fail'][gi, si][m].sum()), int(m.sum())
                lo, hi = wilson(k, n)
                row[a] = dict(frame_err=k, n=n, fer=k / n if n else math.nan, lo=lo, hi=hi)
            out['floors'].append(row)
    cross = {(c['target'], c['rho'], c['arm']): c for c in db['cross']}
    gapd = {(c['target'], c['rho'], c['arm']): c for c in db['to_a3']}
    max_snr = D.snrs[-1] / 100
    for t in sorted({c['target'] for c in db['cross']}):
        for rho in D.rhos:
            r = rho / 1000
            for arm in [a for a in D.arms if a != 'A3']:
                cb, c3, g = cross.get((t, r, arm)), cross.get((t, r, 'A3')), gapd.get((t, r, arm))
                if cb is None or c3 is None or g is None:
                    continue
                row = dict(target=t, rho=r, arm=arm, B=cb, A3=c3, gap=g)
                if not math.isfinite(g['est']):
                    if cb['reason'].startswith('FER>target') and math.isfinite(c3['est']):
                        row['bound'] = f'gap > {max_snr - c3["est"]:.2f} dB (arm never reaches target by {max_snr:.1f} dB)'
                    elif c3['reason'].startswith('FER>target'):
                        row['bound'] = 'A3 never reaches target in range; gap undetermined'
                    elif cb['reason'].startswith('FER<=target'):
                        row['bound'] = 'arm already below target at lowest SNR; gap undetermined'
                out['gaps'].append(row)
    for row in out['gaps']:
        if row['arm'] == 'A0' and row['target'] == 0.01 and LAMBDA.get(lab(row['rho'])) == 4:
            g = row['gap']
            known = math.isfinite(g['est'])
            out['kill'].append(dict(rho=row['rho'], gap=g, lower_bound=row.get('bound'),
                                    point_below_0p2=bool(g['est'] < .2) if known else None,
                                    ci_hi_below_0p2=bool(g['hi'] < .2) if known and math.isfinite(g['hi']) else None))
    preds = {'max_tap_spread': np.array([r['maxspread'] for r in rows]),
             'max_rays_per_tap': np.array([r['maxrays'] for r in rows]),
             'n_rays_total': np.array([r['npaths'] for r in rows]),
             'same_delay_underfit': np.array([r['underfit'] for r in rows]),
             'missed_energy_fraction': np.array([r['mef'] for r in rows])}
    ones = np.ones((1, D.U))
    fns, res = {}, []
    for gi, rho in enumerate(D.rhos):
        mask = rix == gi
        for pn, sc in preds.items():
            rec = dict(rho=rho / 1000, pred=pn, n=int(mask.sum()), n_fail=int(y[mask].sum()))
            if np.isnan(sc[mask]).any() or y[mask].min() == y[mask].max():
                rec.update(auc=math.nan, auc_within_snr=math.nan)
            else:
                fns[(rho / 1000, pn)] = auc_prep(sc[mask], y[mask], unit[mask])
                w = []
                for sj in range(len(D.snrs)):
                    m = mask & (six == sj)
                    if m.any() and y[m].min() != y[m].max():
                        w.append(float(auc_prep(sc[m], y[m], unit[m])(ones)[0]))
                rec.update(auc=float(fns[(rho / 1000, pn)](ones)[0]),
                           auc_within_snr=float(np.mean(w)) if w else math.nan, n_within_cells=len(w),
                           constant_predictor=bool(np.ptp(sc[mask]) == 0))
            res.append(rec)
    vals = {k: [] for k in fns}
    for i in range(0, args.B_aux, 100):
        W = weights(D.strata, D.U, min(100, args.B_aux - i), rng)
        for k, fn in fns.items():
            vals[k].append(fn(W))
    for rec in res:
        k = (rec['rho'], rec['pred'])
        if k in vals:
            b = np.concatenate(vals[k])
            b = b[np.isfinite(b)]
            rec['auc_lo'], rec['auc_hi'] = (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))) if len(b) >= 50 else (math.nan,) * 2
    out['auc'] = res
    return out


def relabel(o):
    if isinstance(o, dict):
        return {k: (lab(v) if k == 'rho' and isinstance(v, float) else relabel(v)) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [relabel(v) for v in o]
    return o


def rename_group_key(o):
    if isinstance(o, dict):
        return {('config' if k == 'rho' else k): rename_group_key(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [rename_group_key(v) for v in o]
    return o


# -------------------------------------------------------------------------- output
def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(o) else None
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def fm(x, nd=3):
    return '-' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:.{nd}f}'


def fc(d, nd=2):
    if d['est'] is None or not math.isfinite(d['est']):
        return '-'
    return f"{fm(d['est'], nd)} [{fm(d['lo'], nd)}, {fm(d['hi'], nd)}]" + ('*' if d['valid'] < .95 else '')


def fp(p):
    return '-' if p is None else (f'{p:.2e}' if p < 1e-3 else f'{p:.4f}')


def tab(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows])


def to_md(R, args):
    L = [f"# Headroom analysis\n\nruns: {', '.join(args.runs)}  |  B={args.B} B_aux={args.B_aux} seed={args.seed} "
         f"T={args.T:.3f} N={args.N} ref_rho={args.ref_rho}  |  units={R['n_units']} rows_ok_dups_skipped={R['dups']} "
         f"error_rows={R['n_err_rows']}\n\nFER = info_errors>0. dec_fail = syndrome!=0; undet = syndrome==0 & info_errors>0. "
         f"`*` = CI from <95% finite bootstrap draws. dB columns: shift=x(rho)-x(ref); to_A3=x(arm)-x(A3); step=x(prev)-x(next) (>0 recovered).\n"]
    L += ['## 1. Per (rho, snr, arm)\n', tab([GN, 'snr', 'arm', 'n', 'err', 'FER', 'Wilson95', 'dec_fail', 'undet', 'BER', 'logloss', 'sec', 'trig'],
          [[r['rho'], r['snr'], r['arm'], r['frames'], r['frame_err'], fm(r['fer']), f"[{fm(r['lo'])}, {fm(r['hi'])}]", r['decode_fail'],
            r['undetected'], f"{r['ber']:.2e}", fm(r['logloss'], 4), fm(r['seconds'], 2), fm(r['trig'], 3) if r['trig'] is not None else ''] for r in R['table1']]), '']
    L += ['## 2. Ladder (paired by frame)\n', tab([GN, 'snr', 'step', 'n', 'fail_prev', 'fail_next', 'rescues', 'harms', 'McNemar p', 'dLogloss [95% CI]'],
          [[r['rho'], r['snr'], r['step'], r['n'], r['fail_prev'], r['fail_next'], r['rescues'], r['harms'], fp(r['p_mcnemar']),
            f"{fm(r['dlogloss'], 4)} [{fm(r['dll_lo'], 4)}, {fm(r['dll_hi'], 4)}]"] for r in R['steps_pair']]),
          '\nFraction of A0 failures rescued by arm (vs A0, independent):\n', tab([GN, 'snr', 'arm', 'A0 fails', 'rescued', 'frac'],
          [[r['rho'], r['snr'], r['arm'], r['a0_fail'], r['rescued'], fm(r['frac'])] for r in R['rescue']]), '']
    db = R['db']
    L += ['## 3. dB at FER targets\n', tab(['target', GN, 'arm', 'crossing SNR dB [CI]', 'note'],
          [[r['target'], r['rho'], r['arm'], fc(r), '' if r['reason'] == 'ok' else r['reason']] for r in db['cross']]), '']
    for key, title in (('shift', 'shift vs ref rho (same arm)'), ('to_a3', 'dB gap to A3 (same rho)')):
        if db[key]:
            L += [f'### {title}\n', tab(['target', GN, 'arm', 'dB [CI]'], [[r['target'], r['rho'], r['arm'], fc(r)] for r in db[key]]), '']
    if db['steps']:
        L += ['### ladder step dB recovered (kill / route rules)\n', tab(['target', GN, 'step', 'dB [CI]'],
              [[r['target'], r['rho'], r['step'], fc(r)] for r in db['steps']]), '']
    for k in db['kill']:
        if 'a1_to_a3' in k:
            L.append(f"- target {k['target']} rho {k['rho']}: A0->A3 {fc(k['a0_to_a3'])} dB; A0->A1 share {fc(k['a0_a1_share'])}; "
                     f"A1->A3 {fc(k['a1_to_a3'])} dB; local<0.1dB rule {k['rule_local_lt_0p1']}; acquisition share>=0.5 rule {k['rule_acq_share_ge_0p5']}")
    L.append('')
    L += ['## 4. Prediction checks\n', '### P1: A0 FER vs rho (argmin; interior; non-monotone; bootstrap argmin frequency)\n']
    if R['p1']:
        rh = list(R['p1'][0]['fer'])
        L.append(tab(['snr'] + [f'FER@{x}' for x in rh] + ['argmin', 'tied', 'interior', 'non-mono', 'p(best vs .5)', 'boot argmin freq'],
                     [[r['snr']] + [fm(r['fer'][x]) for x in rh] + [r['argmin_rho'], r['n_tied_min'], r['interior'], r['non_monotone'],
                       fp(r.get('p_mcnemar_best_vs_0.5')), ' '.join(f'{k}:{v:.2f}' for k, v in r['argmin_boot_freq'].items())] for r in R['p1']]))
    else:
        L.append('n/a (need >=2 rho and A0)')
    L += ['', f"### P2: A3 shift vs 10log10((1-ref)/(1-rho)); tol 0.15 dB\n", tab(['target', 'rho', 'obs [CI]', 'pred', 'resid [CI]', 'point<=tol', 'CI<=tol'],
          [[r['target'], r['rho'], fc(r['obs']), fm(r['pred']), fc(r['resid']), r['point_within_tol'], r['ci_within_tol']] for r in R['p2']]) if R['p2'] else 'n/a', '']
    p3 = R['p3']
    L.append(f"### P3: AUC for A0 failure (T={p3['T']:.3f} gamma threshold; AUC>0.5 = predictor larger on failures)\n" if p3 else '### P3: n/a')
    if p3:
        L += [tab(['rho', 'predictor', 'n', 'fails', 'AUC pooled [CI]', 'AUC within-SNR mean (cells)'],
                  [[r['rho'], r['pred'], r['n'], r['n_fail'], f"{fm(r['auc'])} [{fm(r.get('auc_lo'))}, {fm(r.get('auc_hi'))}]",
                    f"{fm(r['auc_within_snr'])} ({r.get('n_within_cells', 0)})"] for r in p3['auc']]),
              '\nE_miss T-sensitivity (point AUC pooled): ' + '; '.join(
                  f"T={s['T']:.2f} rho={s['rho']}: {fm(s['auc'])}" for s in p3['T_sensitivity']),
              '\nmean E_miss by cell: ' + '; '.join(f"{d['rho']}/{d['snr']}: {d['mean_E_miss']:.4f}" for d in p3['E_miss_desc']), '']
    f1 = R.get('f1')
    if f1:
        L += ['## 5. F1 clustered-channel checks\n', '### 5a. B (A0) fitted slots vs truth (A0 = F0 round-1 fit, as driver rows)\n',
              tab([GN, 'cell', 'n', 'B fit slots', 'frac slots=8', 'true rays P', 'true taps', 'rays/tap', 'frac same-delay underfit', 'mean missed-energy frac'],
                  [[r['rho'], r['cell'], r['n'], fm(r['fit_slots'], 2), fm(r['frac_fit_slots_8'], 3), fm(r['true_rays'], 2), fm(r['true_taps'], 2),
                    fm(r['rays_per_tap'], 2), fm(r['frac_same_delay_underfit'], 3), fm(r['mean_missed_energy'], 4)] for r in f1['slots']]), '',
              '### 5b. FER at highest SNR (Wilson 95%)\n']
        arms_f = [a for a in f1['floors'][0] if a not in ('rho', 'snr')]
        L += [tab([GN, 'snr'] + [f'{a} err/n FER [Wilson]' for a in arms_f],
                  [[r['rho'], r['snr']] + [f"{r[a]['frame_err']}/{r[a]['n']} {fm(r[a]['fer'], 4)} [{fm(r[a]['lo'], 4)}, {fm(r[a]['hi'], 4)}]" for a in arms_f]
                   for r in f1['floors']]), '',
              '### 5c. Gap to A3 (dB; x(arm)-x(A3), >0 = arm needs more SNR) with bounds when a curve does not cross\n',
              tab(['target', GN, 'arm', 'arm crossing', 'A3 crossing', 'gap [CI]', 'bound / note'],
                  [[r['target'], r['rho'], r['arm'], fc(r['B']), fc(r['A3']), fc(r['gap']), r.get('bound', '')] for r in f1['gaps']]), '',
              '### 5d. Pre-registered kill rule: B->A3 gap at FER 1e-2 < 0.2 dB for the lambda=4 configs\n']
        L += [f"- {k['rho']}: gap {fc(k['gap'])}; lower bound: {k['lower_bound']}; point<0.2: {k['point_below_0p2']}; CI-hi<0.2: {k['ci_hi_below_0p2']}"
              for k in f1['kill']] or ['- no lambda=4 config with FER 1e-2 gap rows']
        L += ['', '### 5e. Per-frame AUC for B (A0) frame failure (AUC>0.5 = predictor larger on failures)\n',
              tab([GN, 'predictor', 'n', 'fails', 'AUC pooled [CI]', 'AUC within-SNR mean (cells)'],
                  [[r['rho'], r['pred'], r['n'], r['n_fail'], f"{fm(r['auc'])} [{fm(r.get('auc_lo'))}, {fm(r.get('auc_hi'))}]" + (' const' if r.get('constant_predictor') else ''),
                    f"{fm(r['auc_within_snr'])} ({r.get('n_within_cells', 0)})"] for r in f1['auc']]), '']
    L += ['## Notes\n'] + [f'- {n}' for n in R['notes']]
    return '\n'.join(L) + '\n'


def plot(D, fer, path):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception as e:  # noqa: BLE001
        return f'plot skipped: {e!r}'
    ncol = min(len(D.rhos), 4)
    nrow = -(-len(D.rhos) // ncol)
    fig, ax = plt.subplots(nrow, ncol, figsize=(4 * ncol, 3.4 * nrow), squeeze=False)
    for r, rho in enumerate(D.rhos):
        a_ = ax[r // ncol, r % ncol]
        for a, arm in enumerate(D.arms):
            a_.semilogy(np.array(D.snrs) / 100, np.maximum(fer[0, r, :, a], 1e-4), 'o-', label=arm, ms=3)
        a_.set_title(f'{GN}={lab(rho / 1000)}' if LABELS else f'rho={rho / 1000}')
        a_.set_xlabel('SNR dB')
        a_.grid(alpha=.3)
    ax[0, 0].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    return str(path)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('runs', nargs='+', help='run dirs containing rows_shard*.jsonl')
    ap.add_argument('--out-dir', type=Path, help='default: first run dir')
    ap.add_argument('--B', type=int, default=2000, help='bootstrap draws for FER/dB (20000 for final)')
    ap.add_argument('--B-aux', dest='B_aux', type=int, default=2000, help='draws for logloss CI and AUC CI')
    ap.add_argument('--seed', type=int, default=20261008)
    ap.add_argument('--targets', default='0.1,0.01')
    ap.add_argument('--ref-rho', type=float, default=0.5)
    ap.add_argument('--T', type=float, default=math.log(1e5), help='detectability threshold on gamma_i (P3)')
    ap.add_argument('--N', type=int, default=1024)
    ap.add_argument('--plot', action='store_true')
    ap.add_argument('--group', choices=('rho', 'config'), default='rho', help='config: F1 clustered rows (group = row[config])')
    ap.add_argument('--config-order', default='D1,N4a,N4b,J4,N8a,N8b,J8')
    args = ap.parse_args(argv)
    t0, rng = time.time(), np.random.default_rng(args.seed)
    rows, md5s, notes = [], {}, []
    for ri, d in enumerate(args.runs):
        files = sorted(Path(d).glob('rows_shard*.jsonl'))
        if not files:
            raise FileNotFoundError(f'no rows_shard*.jsonl in {d}')
        for f in files:
            md5s[str(f)] = md5(f)
            for x in f.open():
                if x.strip():
                    r = dict(json.loads(x), _run=ri)
                    r['_rp0'], r['_ri'] = r['rho_permille'], ri
                    if r['arm'] != 'A0':  # truth/fit detail only needed for A0 rows
                        for k in ('truth_g2', 'truth_l', 'truth_k', 'fit_delays', 'fit_dopplers'):
                            r.pop(k, None)
                    rows.append(r)
        if (Path(d) / 'results.json').exists():
            md5s[str(Path(d) / 'results.json')] = md5(Path(d) / 'results.json')
    global GN
    if args.group == 'config':
        order = [c for c in args.config_order.split(',') if any(r.get('config') == c for r in rows)]
        idx = {c: i + 1 for i, c in enumerate(order)}
        GN = 'config'
        LABELS.update({float(i): c for c, i in idx.items()})
        for r in rows:
            r['rho_permille'] = 1000 * idx[r['config']]  # group index stored in the rho column
            r['_run'] = (r['_run'], r['config'])  # units never shared across configs
    D = Data(rows)
    # consistency with driver merge summary
    mism = 0
    for ri, d in enumerate(args.runs):
        p = Path(d) / 'results.json'
        if p.exists():
            mine = {}
            for r in rows:
                if r['_ri'] == ri and r['status'] == 'ok':
                    c = mine.setdefault((r.get('config'), r['_rp0'], r['snr_centi_db'], r['arm']), [0, 0])
                    c[0] += 1
                    c[1] += r['info_errors'] > 0
            for e in json.loads(p.read_text())['summary']:
                mism += mine.get((e.get('config'), round(e['rho'] * 1000), round(e['snr_db'] * 100), e['arm'])) != [e['frames'], e['frame_errors']]
    notes.append(f'cross-check vs driver results.json summary (frames, frame_errors per cell): {mism} mismatching cells')
    notes.append('sigma2 not stored in rows: derived as 10^(-snr_db/10) (driver asserts this for obs); N and K_INFO=1024 are constants; '
                 'truth_g2/pdp_total/n_paths/n_distinct_delays come from rows (truth_g2 sorted desc).')
    targets = [float(x) for x in args.targets.split(',')]
    fer, neff = boot_curves(D, args.B, rng)
    steps_pair, rescue = ladder(D, args.B_aux, rng)
    db = db_analysis(D, fer, neff, targets, args.ref_rho)
    cfg_mode = args.group == 'config'
    R = dict(n_units=D.U, dups=D.dups, n_err_rows=D.n_err_rows, table1=table1(D), steps_pair=steps_pair, rescue=rescue, db=db,
             p1=None if cfg_mode else p1_check(D, fer, neff), p2=[] if cfg_mode else p2_check(D, db, args.ref_rho),
             p3=None if cfg_mode else p3_check(D, args, rng), f1=f1_check(D, args, rng, db) if cfg_mode else None, notes=notes)
    if cfg_mode:
        notes.append('config mode: group column = F1 config (stored in the rho_permille column as 1000*index); P1/P2/P3 not applicable. '
                     'Units are per (run, config, channel_seed, gains, info), so bootstrap is stratified by config.')
        db.pop('X', None)
        R = relabel(R)
    out_dir = args.out_dir or Path(args.runs[0])
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.plot:
        notes.append(plot(D, fer, out_dir / 'fer_curves.png'))
    db.pop('X', None)
    (out_dir / 'ANALYSIS.md').write_text(to_md(R, args))
    payload = clean(dict(_argv=argv, _input_md5=md5s, params={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
                         wall_seconds=time.time() - t0, **R))
    (out_dir / 'analysis.json').write_text(json.dumps(rename_group_key(payload) if cfg_mode else payload, indent=1, allow_nan=False) + '\n')
    print(f'wrote {out_dir / "ANALYSIS.md"} and analysis.json in {time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
