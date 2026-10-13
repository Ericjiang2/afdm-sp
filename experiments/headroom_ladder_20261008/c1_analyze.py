#!/usr/bin/env python
"""C1 bootstrapping-limit analysis (task 10-08-doppler-cluster; research/distinction-v3.md "Decisive experiment").
Input : run dir(s) with rows_shard*.jsonl written by driver_c1.py.   Output: <out-dir>/ANALYSIS.md, analysis.json, c1_fer.png, c1_eps.png
        (REMOTE_ROWS_MD5.txt is written by the caller).   numpy + scipy (+ matplotlib for the figures) only.
usage: c1_analyze.py --out-dir DIR [--B 2000] [--no-plots] <run dir> [<run dir> ...]

Notation (raw units = transmit power 1: pilot rho, data 1-rho, sigma2 = 10^(-snr/10), channel energy ~ 1, N = 1024)
  K            = 8 L  DPSS coefficients (L distinct delays x 8); every column has m^H m = N.
  eps1         = ||H - H^_1||_F^2 / N of the FIRST-PASS refit (pilot-only: mu = 0, v = .5, no decoding)   [= per-sample channel error
                 energy; invariant to the receiver normalisation because y and pilot are scaled alike]
  eps_LS(K)    = K (sigma2 + (1-rho) E) / (rho N)      per-coefficient error energy s = (sigma2 + (1-rho) E)/(rho N) times K  [spec formula;
                 receiver-units equivalent: s2/(N P_p) with s2 = sigma2/(2(1-rho)) + .5 E, P_p = rho/(2(1-rho))]
  eps_shr(K)   = (1-g)^2 E + g^2 eps_LS,  g = P/(P + eps_LS^assumed)   expected first-pass error of the ridge/LMMSE estimator with a flat
                 prior of total energy P (P = row tau_sum_r1: 1 for SPg_flat, .3 for SPg_flat03, ~.3 E^ for SPg_slep (flat-equivalent only)).
  SINR_spec    = (1-rho) / (sigma2 + eps1)                          [literal spec / K* derivation form, raw units]
  SINR_recv    = .5 / (sigma2_eff + eps1), sigma2_eff = sigma2/(2(1-rho))   [the same literal form in the receiver's normalised units]
  SINR_phys    = (1-rho) E / (sigma2 + (1-rho) eps1)               [physical: estimation error excites the data at power (1-rho)]
  K*(gamma)    = rho N [(1-rho)/gamma - sigma2] / (sigma2 + 1 - rho)        (spec; gamma_th = 1.2 predicted)
  FER          = frame error = info_errors > 0.  Wilson 95% CI.  Bootstrap = frames resampled jointly over every L / rho / SNR / arm (unit = frame
                 index), so arm-vs-arm and rho-vs-rho differences are paired.
  cliff (spec) = smallest L (after the LAST argmin of FER over L) with FER > max(2 FER_min, 0.1).
  K_c(level)   = K at which the FER curve first rises through `level` after its minimum (linear interpolation in K between grid points);
                 +inf = not reached by L = 32 (K = 256), -inf = already above at L = 4.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy import optimize, stats

import analyze

N = 1024
LS = (4, 8, 12, 16, 24, 32)
KS = np.array([8 * L for L in LS], float)
SP_ARMS = ('SPg_flat', 'SPg_flat03', 'SPg_slep')
ARMS = ('A3',) + SP_ARMS
GAMMA_SPEC = 1.2
LEVELS = (0.1, 0.5)
FIELDS = ('info_errors', 'logloss_bits', 'decode_ok', 'eps_ce1', 'eps_det1', 'eps_ce2', 'eps_det2', 'r1_ll_in', 'r1_ll_app', 'r1_mabs_app',
          'r1_syn', 'e_real', 'sigma2', 'tau_sum_r1', 'e_hat1', 'seconds')


def pct(x, q):
    return float(np.percentile(x, q, method='nearest'))


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as s:
        for b in iter(lambda: s.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ data
class Data:
    def __init__(self, dirs):
        self.dirs = [Path(d) for d in dirs]
        self.files = sorted(f for d in self.dirs for f in d.glob('rows_shard*.jsonl'))
        if not self.files:
            raise FileNotFoundError('no rows_shard*.jsonl')
        cols = collections.defaultdict(list)
        n_rows = n_err = 0
        seen = set()
        self.dup = 0
        self.fp = {}
        self.pair_bad = 0
        for f in self.files:
            with open(f) as s:
                for line in s:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    n_rows += 1
                    if r['status'] != 'ok':
                        n_err += 1
                        continue
                    key = (r['arm'], r['snr_centi_db'], r['rho_permille'], r['L'], r['frame'])
                    if key in seen:
                        self.dup += 1
                        continue
                    seen.add(key)
                    # pairing: (L, frame) -> channel fingerprint; frame -> (info, noise) fingerprint
                    fp = (r['channel_seed'], r['physical_gains_sha256'])
                    if self.fp.setdefault(('ch', r['L'], r['frame']), fp) != fp:
                        self.pair_bad += 1
                    mf = (r['info_sha256'], r['noise_sha256'])
                    if self.fp.setdefault(('msg', r['frame']), mf) != mf:
                        self.pair_bad += 1
                    for k in ('arm', 'snr_centi_db', 'rho_permille', 'L', 'frame'):
                        cols[k].append(r[k])
                    for k in FIELDS:
                        cols[k].append(r.get(k, np.nan))
        self.n_rows, self.n_err = n_rows, n_err
        self.c = {k: np.array(v) for k, v in cols.items()}
        c = self.c
        self.snrs = sorted(set(c['snr_centi_db'].tolist()))
        self.rhos = sorted(set(c['rho_permille'].tolist()))
        self.Ls = sorted(set(c['L'].tolist()))
        self.arms = [a for a in ARMS if a in set(c['arm'].tolist())]
        frames = None
        for snr in self.snrs:
            for rho in self.rhos:
                for L in self.Ls:
                    for a in self.arms:
                        m = (c['arm'] == a) & (c['snr_centi_db'] == snr) & (c['rho_permille'] == rho) & (c['L'] == L)
                        fs = set(c['frame'][m].tolist())
                        frames = fs if frames is None else frames & fs
        self.frames = sorted(frames)
        self.nF = len(self.frames)
        self.expected_cells = len(self.snrs) * len(self.rhos) * len(self.Ls) * len(self.arms)
        self.missing = int(self.expected_cells * (max(c['frame']) + 1) - len(c['frame']))
        pos = {f: i for i, f in enumerate(self.frames)}
        self.tab = {}  # (arm, snr, rho) -> {field: (nL, nF) array}
        for snr in self.snrs:
            for rho in self.rhos:
                for a in self.arms:
                    d = {k: np.full((len(self.Ls), self.nF), np.nan) for k in FIELDS}
                    for i, L in enumerate(self.Ls):
                        m = (c['arm'] == a) & (c['snr_centi_db'] == snr) & (c['rho_permille'] == rho) & (c['L'] == L)
                        idx = np.array([pos.get(f, -1) for f in c['frame'][m]])
                        ok = idx >= 0
                        for k in FIELDS:
                            d[k][i, idx[ok]] = c[k][m][ok]
                    d['fail'] = (d['info_errors'] > 0).astype(np.uint8)
                    self.tab[(a, snr, rho)] = d


# ------------------------------------------------------------------------------------------ formulas
def sig2(snr_centi):
    return 10 ** (-snr_centi / 1000.)


def k_star(gamma, rho, s2):
    return rho * N * ((1 - rho) / gamma - s2) / (s2 + 1 - rho)


def gamma_of_k(K, rho, s2):
    return (1 - rho) / (s2 + K * (s2 + 1 - rho) / (rho * N))


def eps_ls(K, rho, s2, E):
    return K * (s2 + (1 - rho) * E) / (rho * N)


def eps_shrunk(K, rho, s2, E_true, E_assumed, P):
    ea = eps_ls(K, rho, s2, E_assumed)
    et = eps_ls(K, rho, s2, E_true)
    g = P / (P + ea)
    return (1 - g) ** 2 * E_true + g ** 2 * et


def eps_shr_closed(K, rho, s2, P, E=1.):
    """expected first-pass error of the ridge estimator with flat prior total energy P (receiver assumes channel energy E = 1; truth E = 1)."""
    ea = eps_ls(K, rho, s2, E)
    g = P / (P + ea)
    return (1 - g) ** 2 * E + g ** 2 * ea


def kstar_shr(gamma, rho, s2, P):
    """K at which (1-rho)/(sigma2 + eps_shr(K)) = gamma (shrinkage-corrected K*)."""
    def f(K):
        return (1 - rho) / (s2 + eps_shr_closed(K, rho, s2, P)) - gamma
    if f(1.) <= 0:
        return 1.
    if f(1e6) >= 0:
        return 1e6
    return float(optimize.brentq(f, 1., 1e6))


def sinr_spec(eps, rho, s2):
    return (1 - rho) / (s2 + eps)


def sinr_recv(eps, rho, s2):
    return .5 / (s2 / (2 * (1 - rho)) + eps)


def sinr_phys(eps, rho, s2, E):
    return (1 - rho) * E / (s2 + (1 - rho) * eps)


def crossing_K(fer, level):
    fer = np.asarray(fer, float)
    i0 = int(np.flatnonzero(fer == fer.min())[-1])
    if fer[i0] >= level:
        return -math.inf
    for j in range(i0 + 1, len(KS)):
        if fer[j] >= level:
            a, b = fer[j - 1], fer[j]
            return float(KS[j - 1] + (level - a) / (b - a) * (KS[j] - KS[j - 1]))
    return math.inf


def cliff_L(fer):
    fer = np.asarray(fer, float)
    i0 = int(np.flatnonzero(fer == fer.min())[-1])
    thr = max(2 * fer.min(), 0.1)
    for j in range(i0 + 1, len(LS)):
        if fer[j] > thr:
            return LS[j]
    return None


def fisher_gt(k1, n1, k0, n0):
    """one-sided exact p for  p1 > p0  (k failures out of n)."""
    return float(stats.fisher_exact([[k1, n1 - k1], [k0, n0 - k0]], alternative='greater')[1])


# ------------------------------------------------------------------------------------------ formatting
def fp(x, nd=3):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 'n/a'
    return f'{x:.{nd}f}'


def fk(x, nd=0):
    if x == math.inf:
        return '>256'
    if x == -math.inf:
        return '<32'
    return f'{x:.{nd}f}'


def fci(lo, hi, nd=0):
    return f'[{fk(lo, nd)},{fk(hi, nd)}]'


def tab(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '|'.join(['---'] * len(head)) + '|'] + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])


# ------------------------------------------------------------------------------------------ main
def clean(o):
    """JSON-safe copy: numpy scalars/arrays -> python, +-inf -> '+inf'/'-inf', nan -> None."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (float, np.floating)):
        o = float(o)
        return None if math.isnan(o) else ('+inf' if o == math.inf else '-inf' if o == -math.inf else o)
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('dirs', nargs='+')
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--B', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=20261008)
    ap.add_argument('--no-plots', action='store_true')
    ap.add_argument('--results-json', type=Path, default=None, help='driver merge results.json: cross-check frame_errors per (L, rho, snr, arm)')
    a = ap.parse_args(argv)
    t0 = time.time()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    D = Data(a.dirs)
    assert a.B % 250 == 0, 'B must be a multiple of 250'
    rng = np.random.default_rng(a.seed)
    nF, nL = D.nF, len(D.Ls)
    assert list(D.Ls) == list(LS), D.Ls
    R = dict(_argv=sys.argv, inputs={str(f): md5(f) for f in D.files}, n_rows=D.n_rows, n_error_rows=D.n_err, duplicates=D.dup,
             missing_rows=D.missing, pairing_violations=D.pair_bad, frames=D.nF, snr_db=[s / 100 for s in D.snrs],
             rho=[r / 1000 for r in D.rhos], arms=D.arms, B=a.B, seed=a.seed)
    md = [f'# C1 bootstrapping-limit analysis\n', f'rows {D.n_rows} (error rows {D.n_err}, duplicates {D.dup}, missing {D.missing}, pairing violations '
          f'{D.pair_bad}); frames per cell {D.nF}; SNR {R["snr_db"]} dB; rho {R["rho"]}; L {list(LS)} (K = 8L = {[int(k) for k in KS]}); arms {D.arms}; '
          f'bootstrap B={a.B} frames (joint over all cells), seed {a.seed}.\n']
    fer = {k: v['fail'].mean(1) for k, v in D.tab.items()}          # (arm,snr,rho) -> (nL,)
    kfail = {k: v['fail'].sum(1).astype(int) for k, v in D.tab.items()}

    # ---------------------------------------------------------------- bootstrap curves (joint frame resampling)
    boot_idx = rng.integers(0, nF, (a.B, nF))
    bfer = {}
    for k, v in D.tab.items():
        F = v['fail']
        bfer[k] = np.stack([F[:, boot_idx[b0:b0 + 250]].mean(-1) for b0 in range(0, a.B, 250)], axis=1).reshape(nL, a.B)  # (nL, B)

    # ---------------------------------------------------------------- 1. FER tables
    R['fer'] = {}
    md.append('## 1. FER vs L (Wilson 95% CI), per SNR x rho\n')
    for snr in D.snrs:
        for rho in D.rhos:
            rows = []
            for ar in D.arms:
                k = (ar, snr, rho)
                cells = []
                for i in range(nL):
                    lo, hi = analyze.wilson(int(kfail[k][i]), nF)
                    cells.append(f'{fer[k][i]:.3f} [{lo:.3f},{hi:.3f}]')
                rows.append([ar] + cells)
                R['fer'][f'{ar}|{snr / 100:g}|{rho / 1000:g}'] = dict(fer=fer[k].tolist(), k=kfail[k].tolist(), n=nF)
            md.append(f'### SNR {snr / 100:g} dB, rho {rho / 1000:g}   (K* spec gamma 1.2: {k_star(GAMMA_SPEC, rho / 1000, sig2(snr)):.0f} = L {k_star(GAMMA_SPEC, rho / 1000, sig2(snr)) / 8:.1f})\n')
            md.append(tab(['arm'] + [f'L={L} (K={8 * L})' for L in LS], rows) + '\n')

    # ---------------------------------------------------------------- 2. prediction (i): true-H monotone
    md.append('## 2. Prediction (i): true-H (A3) FER non-increasing in L\n')
    R['pred_i'] = {}
    rows, n_sig_inc, n_point_inc, all_end_ok = [], 0, 0, True
    for snr in D.snrs:
        for rho in D.rhos:
            k = ('A3', snr, rho)
            sig, pt = [], []
            for i in range(nL - 1):
                p = fisher_gt(int(kfail[k][i + 1]), nF, int(kfail[k][i]), nF)
                if p < 0.01:
                    sig.append(f'{LS[i]}->{LS[i + 1]} (p={p:.1e})')
                if kfail[k][i + 1] > kfail[k][i]:
                    pt.append(f'{LS[i]}->{LS[i + 1]} ({kfail[k][i]}->{kfail[k][i + 1]})')
            rs = stats.spearmanr(np.arange(nL), fer[k]) if fer[k].std() > 0 else None
            end_ok = bool(kfail[k][-1] <= kfail[k][0])
            all_end_ok &= end_ok
            n_sig_inc += len(sig)
            n_point_inc += len(pt)
            R['pred_i'][f'{snr / 100:g}|{rho / 1000:g}'] = dict(significant_increases=sig, point_increases=pt, spearman=None if rs is None else float(rs.statistic),
                                                                 fer=fer[k].tolist())
            rows.append([f'{snr / 100:g}', f'{rho / 1000:g}', ' '.join(f'{x:.3f}' for x in fer[k]), len(pt), '; '.join(pt) or '-', '; '.join(sig) or '-',
                         'n/a' if rs is None else f'{rs.statistic:.2f}'])
    md.append(tab(['SNR', 'rho', 'A3 FER at L=' + ','.join(map(str, LS)), '#point increases', 'point increases (fails)', 'significant increases (Fisher p<.01)', 'Spearman(L,FER)'], rows) + '\n')
    verdict_i = 'CONFIRMED' if n_sig_inc == 0 and all_end_ok else 'REFUTED'
    R['pred_i_summary'] = dict(significant_increases=n_sig_inc, point_increases=n_point_inc, end_ok=all_end_ok, verdict=verdict_i)
    md.append(f'**(i) {verdict_i}**: significant increases {n_sig_inc}, point-estimate increases {n_point_inc} (over 5 steps x {len(D.snrs) * len(D.rhos)} series), FER(L=32) <= FER(L=4) in all series: {all_end_ok}.\n')

    # ---------------------------------------------------------------- 3. SP FER shape, cliff
    md.append('## 3. SP FER vs L: U-shape and cliff\n')
    md.append('spec cliff = smallest L after the last FER argmin with FER > max(2 FER_min, 0.1).  U-shape test: an interior L_min whose FER is significantly below both FER(L=4) and FER(L=32) (Fisher one-sided p<.01).  K_c(level) = interpolated K where FER rises through level (95% bootstrap CI).\n')
    R['cliff'] = {}
    rows = []
    for snr in D.snrs:
        for rho in D.rhos:
            r = rho / 1000
            s2 = sig2(snr)
            ks = k_star(GAMMA_SPEC, r, s2)
            for ar in SP_ARMS:
                if ar not in D.arms:
                    continue
                k = (ar, snr, rho)
                f = fer[k]
                i0 = int(np.flatnonzero(f == f.min())[-1])
                cl = cliff_L(f)
                ushape = 0 < i0 < nL - 1 and fisher_gt(int(kfail[k][0]), nF, int(kfail[k][i0]), nF) < .01 and fisher_gt(int(kfail[k][-1]), nF, int(kfail[k][i0]), nF) < .01
                kc, kci = {}, {}
                for lev in LEVELS:
                    kc[lev] = crossing_K(f, lev)
                    bs = np.array([crossing_K(bfer[k][:, b], lev) for b in range(a.B)])
                    kci[lev] = (float(pct(bs, 2.5)), float(pct(bs, 97.5)), float(np.mean(np.isfinite(bs) & (bs > 0))))
                R['cliff'][f'{ar}|{snr / 100:g}|{r:g}'] = dict(fer_min=float(f.min()), L_min=LS[i0], cliff_L_spec=cl, u_shape=bool(ushape), kstar_spec=ks,
                                                                kc={str(l): kc[l] for l in LEVELS}, kc_ci={str(l): kci[l][:2] for l in LEVELS})
                rows.append([f'{snr / 100:g}', f'{r:g}', ar, f'{f.min():.3f}@L{LS[i0]}', cl if cl else 'none', 'yes' if ushape else 'no', f'{ks:.0f}',
                             f'{fk(kc[0.1])} {fci(*kci[0.1][:2])}', f'{fk(kc[0.5])} {fci(*kci[0.5][:2])}'])
    md.append(tab(['SNR', 'rho', 'arm', 'FER_min@L', 'cliff L (spec)', 'U-shape', 'K* (gamma 1.2)', 'K_c(0.1) [CI]', 'K_c(0.5) [CI]'], rows) + '\n')

    # ---------------------------------------------------------------- 4. eps1 vs K
    md.append('## 4. First-pass channel error eps1 = ||H - H^_1||_F^2/N vs K (mean over frames)\n')
    md.append('pred LS = K (sigma2 + (1-rho) E)/(rho N) (spec; per-coefficient s = (sigma2 + (1-rho)E)/(rho N), units: channel energy per sample per DPSS coefficient, m^H m = N); pred shr = ridge-shrunk version for the arm prior (see header).  ratio = observed / predicted.\n')
    R['eps'] = {}
    for snr in D.snrs:
        for rho in D.rhos:
            r, s2 = rho / 1000, sig2(snr)
            rows = []
            for ar in SP_ARMS:
                if ar not in D.arms:
                    continue
                v = D.tab[(ar, snr, rho)]
                obs = v['eps_ce1'].mean(1)
                E = v['e_real']
                P = v['tau_sum_r1']
                Eass = np.where(np.isfinite(v['e_hat1']) & (ar == 'SPg_slep'), v['e_hat1'], 1.)
                pls = np.array([eps_ls(KS[i], r, s2, E[i]).mean() for i in range(nL)])
                psh = np.array([eps_shrunk(KS[i], r, s2, E[i], Eass[i], P[i]).mean() for i in range(nL)])
                # LS slope through the origin on K <= 96 (little shrinkage)
                m = KS <= 96
                s_hat = float((KS[m] * obs[m]).sum() / (KS[m] ** 2).sum())
                s_pred = float(((s2 + (1 - r) * E.mean(1)) / (r * N))[m].mean())
                c_shr = float(np.exp(np.mean(np.log(obs / psh))))

                def model_c(c):  # receiver's assumed s2 fixed; true per-coefficient variance scaled by c
                    return np.array([np.mean((1 - g) ** 2 * E[i] + g ** 2 * c * eps_ls(KS[i], r, s2, E[i]))
                                     for i in range(nL) for g in [P[i] / (P[i] + eps_ls(KS[i], r, s2, Eass[i]))]])
                fit = optimize.minimize_scalar(lambda lc: float(np.sum((np.log(obs) - np.log(model_c(np.exp(lc)))) ** 2)), bounds=(-2., 2.), method='bounded')
                c_fit = float(np.exp(fit.x))
                R['eps'][f'{ar}|{snr / 100:g}|{r:g}'] = dict(K=KS.tolist(), obs=obs.tolist(), pred_ls=pls.tolist(), pred_shrunk=psh.tolist(),
                                                              slope_obs_K_le_96=s_hat, slope_pred_ls=s_pred, geo_ratio_shrunk=c_shr, c_fit=c_fit, resid_rms_log=float(np.sqrt(fit.fun / nL)),
                                                              sem=(v['eps_ce1'].std(1, ddof=1) / np.sqrt(nF)).tolist())
                rows.append([ar, 'obs'] + [f'{x:.4f}' for x in obs] + [f's_hat {s_hat * 1e4:.3f}e-4'])
                rows.append([ar, 'pred LS'] + [f'{x:.4f}' for x in pls] + [f's_pred {s_pred * 1e4:.3f}e-4 (ratio {s_hat / s_pred:.2f})'])
                rows.append([ar, 'pred shr'] + [f'{x:.4f}' for x in psh] + [f'geo ratio obs/shr {c_shr:.2f}; c_fit {c_fit:.3f} (true s / spec s, rms log resid {np.sqrt(fit.fun / nL):.3f})'])
                rows.append([ar, 'obs/LS'] + [f'{o / p:.2f}' for o, p in zip(obs, pls)] + [''])
                rows.append([ar, 'obs/shr'] + [f'{o / p:.2f}' for o, p in zip(obs, psh)] + [''])
            md.append(f'### SNR {snr / 100:g} dB, rho {r:g}\n')
            md.append(tab(['arm', 'row'] + [f'K={int(k)}' for k in KS] + ['fit'], rows) + '\n')

    # ---------------------------------------------------------------- 5. first-pass SINR vs K
    md.append('## 5. First-pass SINR vs K (mean over frames of the per-frame value)\n')
    md.append('SINR_spec = (1-rho)/(sigma2 + eps1) [raw units, K* derivation form]; SINR_recv = .5/(sigma2_eff + eps1) [receiver-normalised units]; SINR_phys = (1-rho)E/(sigma2 + (1-rho)eps1).  pred = SINR_spec with eps_LS (spec closed form).\n')
    R['sinr'] = {}
    for snr in D.snrs:
        for rho in D.rhos:
            r, s2 = rho / 1000, sig2(snr)
            rows = []
            for ar in ('SPg_flat', 'SPg_slep'):
                if ar not in D.arms:
                    continue
                v = D.tab[(ar, snr, rho)]
                e1, E = v['eps_ce1'], v['e_real']
                ssp, srv, sph = sinr_spec(e1, r, s2).mean(1), sinr_recv(e1, r, s2).mean(1), sinr_phys(e1, r, s2, E).mean(1)
                spred = np.array([sinr_spec(eps_ls(KS[i], r, s2, E[i]), r, s2).mean() for i in range(nL)])
                R['sinr'][f'{ar}|{snr / 100:g}|{r:g}'] = dict(K=KS.tolist(), spec=ssp.tolist(), recv=srv.tolist(), phys=sph.tolist(), pred_spec_ls=spred.tolist())
                rows += [[ar, 'SINR_spec'] + [f'{x:.2f}' for x in ssp], [ar, 'pred (LS)'] + [f'{x:.2f}' for x in spred],
                         [ar, 'SINR_recv'] + [f'{x:.2f}' for x in srv], [ar, 'SINR_phys'] + [f'{x:.2f}' for x in sph]]
            md.append(f'### SNR {snr / 100:g} dB, rho {r:g}\n')
            md.append(tab(['arm', 'row'] + [f'K={int(k)}' for k in KS], rows) + '\n')

    # ---------------------------------------------------------------- 6. K* table, gamma fit
    md.append('## 6. Observed cliffs vs K*(rho, SNR)\n')
    md.append('K*(1.2) = spec closed form with gamma_th = 1.2.  gamma_impl = gamma_of_k(K_c) = implied threshold from the spec formula at the observed K_c; gamma_meas = SINR_spec at K_c with the MEASURED eps1 (log-interpolated in K).  gamma_best = single gamma_th minimising sum (log K*(gamma) - log K_c)^2 over the cells with a finite K_c (a censored cell [K_c > 256] contributes only if K* < 256; [K_c < 32] only if K* > 32); level 0.5 unless stated.\n')
    R['kstar'] = {}
    for lev in LEVELS:
        for ar in SP_ARMS:
            if ar not in D.arms:
                continue
            cells = []
            for snr in D.snrs:
                for rho in D.rhos:
                    r, s2 = rho / 1000, sig2(snr)
                    f = fer[(ar, snr, rho)]
                    kc = crossing_K(f, lev)
                    bs = np.array([crossing_K(bfer[(ar, snr, rho)][:, b], lev) for b in range(a.B)])
                    eps_mean = D.tab[(ar, snr, rho)]['eps_ce1'].mean(1)
                    gm = float('nan')
                    if np.isfinite(kc) and kc > 0:
                        e_at = float(np.exp(np.interp(kc, KS, np.log(eps_mean))))
                        gm = float((1 - r) / (s2 + e_at))
                    cells.append(dict(snr=snr / 100, rho=r, s2=s2, kc=kc, bs=bs, gamma_impl=float(gamma_of_k(kc, r, s2)) if np.isfinite(kc) and kc > 0 else float('nan'),
                                      gamma_meas=gm, kstar=float(k_star(GAMMA_SPEC, r, s2))))

            def loss(g, cs, key='kc'):
                tot = 0.
                for c in cs:
                    ks = max(k_star(g, c['rho'], c['s2']), 1.)
                    kc = c[key] if not isinstance(key, np.ndarray) else key
                    if kc == math.inf:
                        tot += (math.log(ks / KS[-1]) ** 2) if ks < KS[-1] else 0.
                    elif kc == -math.inf:
                        tot += (math.log(ks / KS[0]) ** 2) if ks > KS[0] else 0.
                    else:
                        tot += math.log(ks / kc) ** 2
                return tot
            gs = np.linspace(0.2, 3.0, 561)
            g_best = float(gs[int(np.argmin([loss(g, cells) for g in gs]))])
            # bootstrap CI of gamma_best (cell curves share the same joint frame resample)
            gb = []
            for b in range(min(a.B, 500)):
                cs = [dict(c, kc=c['bs'][b]) for c in cells]
                gb.append(float(gs[int(np.argmin([loss(g, cs) for g in gs]))]))
            R['kstar'][f'{ar}|{lev}'] = dict(gamma_best=g_best, gamma_best_ci=[float(pct(gb, 2.5)), float(pct(gb, 97.5))],
                                              cells=[{k: (float(v) if not isinstance(v, np.ndarray) else None) for k, v in c.items() if k != 'bs'} for c in cells])
            rows = [[f'{c["snr"]:g}', f'{c["rho"]:g}', f'{c["kstar"]:.0f}', f'{c["kstar"] / 8:.1f}', f'{fk(c["kc"])} {fci(pct(c["bs"], 2.5), pct(c["bs"], 97.5))}',
                     'n/a' if not np.isfinite(c['gamma_impl']) else f'{c["gamma_impl"]:.2f}', 'n/a' if not np.isfinite(c['gamma_meas']) else f'{c["gamma_meas"]:.2f}',
                     f'{k_star(g_best, c["rho"], c["s2"]):.0f}'] for c in cells]
            md.append(f'### {ar}, level {lev}: gamma_best = {g_best:.2f} (95% CI {pct(gb, 2.5):.2f}-{pct(gb, 97.5):.2f})\n')
            md.append(tab(['SNR', 'rho', 'K*(1.2)', 'L*(1.2)', 'K_c [CI]', 'gamma_impl', 'gamma_meas', 'K*(gamma_best)'], rows) + '\n')

    # rho ordering of K_c (paired bootstrap)
    md.append('### rho ordering of K_c (paired bootstrap; P = fraction of resamples with strict order K_c(.5) > K_c(.3) > K_c(.2); inf counts as largest, equal infs break the order)\n')
    R['order'] = {}
    rows = []
    for lev in LEVELS:
        for ar in SP_ARMS:
            if ar not in D.arms:
                continue
            for snr in D.snrs:
                if len(D.rhos) < 3:
                    continue
                kcs = {rho: np.array([crossing_K(bfer[(ar, snr, rho)][:, b], lev) for b in range(a.B)]) for rho in D.rhos}
                lo, mid, hi = D.rhos[0], D.rhos[1], D.rhos[-1]
                strict = np.mean((kcs[hi] > kcs[mid]) & (kcs[mid] > kcs[lo]))
                weak = np.mean((kcs[hi] >= kcs[mid]) & (kcs[mid] >= kcs[lo]) & (kcs[hi] > kcs[lo]))
                p_hi_lo = np.mean(kcs[hi] > kcs[lo])
                R['order'][f'{ar}|{snr / 100:g}|{lev}'] = dict(strict=float(strict), weak=float(weak), hi_gt_lo=float(p_hi_lo),
                                                                kc_point={f'{rho / 1000:g}': crossing_K(fer[(ar, snr, rho)], lev) for rho in D.rhos})
                rows.append([lev, ar, f'{snr / 100:g}', ' / '.join(fk(crossing_K(fer[(ar, snr, rho)], lev)) for rho in reversed(D.rhos)),
                             f'{strict:.3f}', f'{weak:.3f}', f'{p_hi_lo:.3f}'])
    md.append(tab(['level', 'arm', 'SNR', f'K_c at rho {"/".join(f"{r / 1000:g}" for r in reversed(D.rhos))}', 'P(strict order)', 'P(weak order)', 'P(K_c(.5) > K_c(.2))'], rows) + '\n')

    # ---------------------------------------------------------------- 6b. K* model fit quality
    md.append('## 6b. Fit quality of K* models against the observed K_c\n')
    md.append('plain = spec K*(gamma) (least-squares first-pass error, no shrinkage); shr = K at which (1-rho)/(sigma2 + eps_shr(K)) = gamma with eps_shr the closed-form ridge error for the arm prior (flat: total prior energy P = 1, flat03: P = .3; E = 1; defined for the flat arms only); const = rho-free baseline K_c = geometric mean of the finite K_c at the same SNR.  err = log(K_pred/K_c) per cell, censored cells contribute only when the prediction contradicts the censoring; rms over the 6 cells.  gamma fitted per arm and level on the grid 0.2-3.0.\n')
    R['fitq'] = {}
    rows, cellrows = [], []
    ggrid = np.linspace(0.2, 3.0, 281)

    def cerr(ks, kc):
        ks = max(ks, 1.)
        if kc == math.inf:
            return math.log(ks / KS[-1]) if ks < KS[-1] else 0.
        if kc == -math.inf:
            return math.log(ks / KS[0]) if ks > KS[0] else 0.
        return math.log(ks / kc)

    def fit_model(cells, kfun):
        best = min(((math.sqrt(np.mean([cerr(kfun(g, c), c['kc']) ** 2 for c in cells])), g) for g in ggrid))
        return best[1], best[0], [cerr(kfun(best[1], c), c['kc']) for c in cells]
    for lev in LEVELS:
        for ar in SP_ARMS:
            if ar not in D.arms:
                continue
            cells = R['kstar'][f'{ar}|{lev}']['cells']
            P_arm = {'SPg_flat': 1., 'SPg_flat03': .3}.get(ar)
            g_pl, rms_pl, e_pl = fit_model(cells, lambda g, c: k_star(g, c['rho'], c['s2']))
            out_ = dict(gamma_plain=g_pl, rms_plain=rms_pl, errs_plain=e_pl)
            g_sh = rms_sh = None
            if P_arm is not None:
                g_sh, rms_sh, e_sh = fit_model(cells, lambda g, c, P_arm=P_arm: kstar_shr(g, c['rho'], c['s2'], P_arm))
                out_.update(gamma_shr=g_sh, rms_shr=rms_sh, errs_shr=e_sh)
                for c, e in zip(cells, e_sh):
                    cellrows.append([lev, ar, f'{c["snr"]:g}', f'{c["rho"]:g}', fk(c['kc']), f'{k_star(g_pl, c["rho"], c["s2"]):.0f}',
                                     f'{kstar_shr(g_sh, c["rho"], c["s2"], P_arm):.0f}', f'{kstar_shr(1.2, c["rho"], c["s2"], P_arm):.0f}'])
            fin = [c for c in cells if np.isfinite(c['kc']) and c['kc'] > 0]
            if fin:
                const = {}
                for snr in set(c['snr'] for c in fin):
                    const[snr] = float(np.exp(np.mean([math.log(c['kc']) for c in fin if c['snr'] == snr])))
                e_c = [cerr(const.get(c['snr'], KS[-1]), c['kc']) for c in cells]
                rms_c = math.sqrt(np.mean(np.square(e_c)))
                out_.update(rms_const=rms_c, errs_const=e_c)
            else:
                rms_c = float('nan')
            R['fitq'][f'{ar}|{lev}'] = out_
            rows.append([lev, ar, f'{g_pl:.2f}', f'{rms_pl:.3f}', 'n/a' if g_sh is None else f'{g_sh:.2f}', 'n/a' if rms_sh is None else f'{rms_sh:.3f}', fp(rms_c)])
    md.append(tab(['level', 'arm', 'gamma plain', 'rms log err plain', 'gamma shr', 'rms log err shr', 'rms log err const-per-SNR'], rows) + '\n')
    md.append(tab(['level', 'arm', 'SNR', 'rho', 'K_c', 'K*_plain(gamma_plain)', 'K*_shr(gamma_shr)', 'K*_shr(1.2)'], cellrows) + '\n')

    # ---------------------------------------------------------------- 7. McNemar slep vs flat (and flat03)
    md.append('## 7. Paired McNemar per L: b = first fails & second ok, c = first ok & second fails  (exact two-sided p)\n')
    R['mcnemar'] = {}
    for first, second, label in (('SPg_slep', 'SPg_flat', 'slep vs flat (spec iv)'), ('SPg_slep', 'SPg_flat03', 'slep vs flat03 (SHAPE effect at equal scale)'),
                                 ('SPg_flat03', 'SPg_flat', 'flat03 vs flat (prior SCALE effect)')):
        if first not in D.arms or second not in D.arms:
            continue
        md.append(f'### {label}: b = {first} fails only, c = {second} fails only\n')
        rows = []
        for snr in D.snrs:
            for rho in D.rhos:
                A, B_ = D.tab[(first, snr, rho)]['fail'].astype(bool), D.tab[(second, snr, rho)]['fail'].astype(bool)
                cell = []
                for i in range(nL):
                    b, c = int((A[i] & ~B_[i]).sum()), int((~A[i] & B_[i]).sum())
                    p = analyze.mcnemar(b, c)
                    R['mcnemar'][f'{first}|{second}|{snr / 100:g}|{rho / 1000:g}|{LS[i]}'] = dict(b=b, c=c, p=p)
                    cell.append(f'{b}/{c}' + ('*' if p < 0.01 else ''))
                rows.append([f'{snr / 100:g}', f'{rho / 1000:g}'] + cell)
        md.append(tab(['SNR', 'rho'] + [f'L={L}' for L in LS], rows) + '\n(* p<0.01)\n')

    # ---------------------------------------------------------------- 8. frame-level threshold mechanism
    md.append('## 8. Frame-level threshold mechanism (SP-specific failures: frames where A3 decodes)\n')
    md.append('Pooled over L (all K), per (SNR, rho, arm): AUC of each first-pass predictor for SP failure among A3-ok frames (AUC 0.5 = none; direction: low SINR / low reliability -> failure), and the logistic 50% point of SINR (P(fail) = sigmoid(a + b log SINR), reported SINR_50 = exp(-a/b)) and the 10-90% width in log-SINR (ln 9 / |b|).\n')
    R['frame'] = {}
    rows = []
    pooled = collections.defaultdict(lambda: [[], []])
    for ar in ('SPg_flat', 'SPg_slep'):
        if ar not in D.arms:
            continue
        for snr in D.snrs:
            for rho in D.rhos:
                r, s2 = rho / 1000, sig2(snr)
                v, a3 = D.tab[(ar, snr, rho)], D.tab[('A3', snr, rho)]
                ok = (a3['fail'] == 0)
                y = v['fail'][ok].astype(float)
                e1, E = v['eps_ce1'][ok], v['e_real'][ok]
                feats = dict(sinr_spec=sinr_spec(e1, r, s2), sinr_phys=sinr_phys(e1, r, s2, E), neg_eps1=-e1, r1_ll_in_neg=-v['r1_ll_in'][ok], r1_ll_app_neg=-v['r1_ll_app'][ok])
                aucs = {}
                for name, x in feats.items():
                    pos, neg = x[y == 1], x[y == 0]
                    aucs[name] = float(stats.mannwhitneyu(neg, pos, alternative='two-sided')[0] / (len(pos) * len(neg))) if len(pos) and len(neg) else float('nan')
                lg = {}
                for name in ('sinr_spec', 'sinr_phys'):
                    x = np.log(np.maximum(feats[name], 1e-6))
                    if 0 < y.sum() < len(y):
                        def nll(p, x=x, y=y):
                            z = p[0] + p[1] * x
                            return float(np.sum(np.logaddexp(0, z) - y * z))
                        res = optimize.minimize(nll, [0., -3.], method='Nelder-Mead', options=dict(xatol=1e-6, fatol=1e-9, maxiter=4000))
                        a0, b1 = res.x
                        lg[name] = dict(sinr50=float(np.exp(-a0 / b1)) if b1 < 0 else float('nan'), width_ln=float(math.log(9) / abs(b1)) if b1 != 0 else float('nan'), slope=float(b1))
                        pooled[(ar, name)][0].append(x)
                        pooled[(ar, name)][1].append(y)
                    else:
                        lg[name] = dict(sinr50=float('nan'), width_ln=float('nan'), slope=float('nan'))
                R['frame'][f'{ar}|{snr / 100:g}|{r:g}'] = dict(n_a3_ok=int(ok.sum()), sp_fail_given_a3_ok=float(y.mean()), auc=aucs, logistic=lg)
                rows.append([ar, f'{snr / 100:g}', f'{r:g}', int(ok.sum()), f'{y.mean():.3f}'] + [f'{aucs[k]:.3f}' for k in feats] +
                            [fp(lg['sinr_spec']['sinr50'], 2), fp(lg['sinr_spec']['width_ln'], 2), fp(lg['sinr_phys']['sinr50'], 2)])
    md.append(tab(['arm', 'SNR', 'rho', 'n(A3 ok)', 'P(SP fail|A3 ok)', 'AUC sinr_spec', 'AUC sinr_phys', 'AUC -eps1', 'AUC -r1_ll_in', 'AUC -r1_ll_app',
                   'SINR_spec 50%', 'ln-width 10-90%', 'SINR_phys 50%'], rows) + '\n')
    for (ar, name), (xs, ys) in pooled.items():
        x, y = np.concatenate(xs), np.concatenate(ys)
        if 0 < y.sum() < len(y):
            def nll(p, x=x, y=y):
                z = p[0] + p[1] * x
                return float(np.sum(np.logaddexp(0, z) - y * z))
            res = optimize.minimize(nll, [0., -3.], method='Nelder-Mead', options=dict(xatol=1e-6, fatol=1e-9, maxiter=4000))
            R['frame'][f'pooled|{ar}|{name}'] = dict(sinr50=float(np.exp(-res.x[0] / res.x[1])), width_ln=float(math.log(9) / abs(res.x[1])), n=int(len(y)))
            md.append(f'pooled over all (SNR, rho, L), {ar}, {name}: SINR_50 = {np.exp(-res.x[0] / res.x[1]):.2f}, ln-width(10-90%) = {math.log(9) / abs(res.x[1]):.2f}, n = {len(y)}\n')

    # ---------------------------------------------------------------- 9. extra diagnostics tables
    md.append('## 9. Means per L: round-1 reliability and eps after the detector\n')
    rows = []
    for snr in D.snrs:
        for rho in D.rhos:
            for ar in D.arms:
                v = D.tab[(ar, snr, rho)]
                rows.append([f'{snr / 100:g}', f'{rho / 1000:g}', ar, 'r1_ll_in'] + [f'{x:.3f}' for x in v['r1_ll_in'].mean(1)])
                rows.append([f'{snr / 100:g}', f'{rho / 1000:g}', ar, 'r1_ll_app'] + [f'{x:.3f}' for x in v['r1_ll_app'].mean(1)])
                rows.append([f'{snr / 100:g}', f'{rho / 1000:g}', ar, 'final logloss'] + [f'{x:.3f}' for x in v['logloss_bits'].mean(1)])
                if ar != 'A3':
                    rows.append([f'{snr / 100:g}', f'{rho / 1000:g}', ar, 'eps_det1'] + [f'{x:.4f}' for x in v['eps_det1'].mean(1)])
                    rows.append([f'{snr / 100:g}', f'{rho / 1000:g}', ar, 'eps_det2 (final)'] + [f'{x:.4f}' for x in v['eps_det2'].mean(1)])
    md.append(tab(['SNR', 'rho', 'arm', 'metric'] + [f'L={L}' for L in LS], rows) + '\n')
    sec = {ar: float(np.mean([D.tab[(ar, s, r)]['seconds'].mean() for s in D.snrs for r in D.rhos])) for ar in D.arms}
    R['mean_seconds_per_cell_per_arm'] = sec
    # ---------------------------------------------------------------- 10. cross-check vs driver merge results.json
    if a.results_json is not None:
        summ = json.loads(a.results_json.read_text())['summary']
        bad, n_cmp = [], 0
        for e in summ:
            if e['arm'] not in D.arms:
                continue
            L = int(e['config'][1:])
            k = (e['arm'], int(round(e['snr_db'] * 100)), int(round(e['rho'] * 1000)))
            mine = int(kfail[k][D.Ls.index(L)])
            n_cmp += 1
            if mine != e['frame_errors'] or D.nF != e['frames']:
                bad.append((e['config'], e['rho'], e['snr_db'], e['arm'], mine, e['frame_errors'], D.nF, e['frames']))
        R['crosscheck_results_json'] = dict(cells_compared=n_cmp, mismatching=len(bad), mismatch_list=bad[:20], results_json_md5=md5(a.results_json))
        md.append(f'## 10. Cross-check vs driver merge results.json\n\ncells compared {n_cmp}, mismatching {len(bad)} (frame_errors = #(info_errors>0) and frame count per (L, rho, snr, arm)).\n')
    write_table(a.out_dir, D, fer, kfail, R, verdict_i)
    R['wall_seconds_analysis'] = time.time() - t0

    (a.out_dir / 'analysis.json').write_text(json.dumps(clean(R), indent=1, allow_nan=False) + '\n')
    (a.out_dir / 'ANALYSIS.md').write_text('\n'.join(md) + '\n')
    if not a.no_plots:
        plots(D, fer, kfail, R, a.out_dir)
    print(f'done in {time.time() - t0:.1f}s -> {a.out_dir}')


def write_table(out, D, fer, kfail, R, verdict_i):
    """C1_TABLE.md: compact FER-vs-L tables + cliff / K* / gamma summary."""
    L_ = ['# C1 table (FER = info_errors>0, 1000 frames/cell, Wilson CI in ANALYSIS.md)\n']
    for snr in D.snrs:
        for rho in D.rhos:
            r, s2 = rho / 1000, sig2(snr)
            L_.append(f'### SNR {snr / 100:g} dB, rho {r:g}: K*(1.2) = {k_star(GAMMA_SPEC, r, s2):.0f} (L* = {k_star(GAMMA_SPEC, r, s2) / 8:.1f})\n')
            rows = []
            for ar in D.arms:
                rows.append([ar] + [f'{x:.3f}' for x in fer[(ar, snr, rho)]] + ([] if ar == 'A3' else [
                    fk(R['cliff'][f'{ar}|{snr / 100:g}|{r:g}']['kc']['0.1']), fk(R['cliff'][f'{ar}|{snr / 100:g}|{r:g}']['kc']['0.5']),
                    R['cliff'][f'{ar}|{snr / 100:g}|{r:g}']['cliff_L_spec'] or 'none', 'U' if R['cliff'][f'{ar}|{snr / 100:g}|{r:g}']['u_shape'] else '-']) + ([''] * 4 if ar == 'A3' else []))
            L_.append(tab(['arm'] + [f'L={L} K={8 * L}' for L in LS] + ['K_c(.1)', 'K_c(.5)', 'cliff L (spec)', 'U'], rows) + '\n')
    L_.append('### gamma_th fitted to the cliffs (K_c at FER level; 95% CI = bootstrap)\n')
    L_.append(tab(['arm', 'level', 'gamma_best', 'CI'], [[k.split('|')[0], k.split('|')[1], f'{v["gamma_best"]:.2f}', f'{v["gamma_best_ci"][0]:.2f}-{v["gamma_best_ci"][1]:.2f}']
                                                     for k, v in R['kstar'].items()]) + '\n')
    L_.append('### gamma measured at the cliff (SINR_spec with the measured eps1 at K_c) and K* model fit quality\n')
    rows = []
    for k, v in R['kstar'].items():
        gm = [c['gamma_meas'] for c in v['cells'] if c['gamma_meas'] == c['gamma_meas']]
        fq = R['fitq'].get(k, {})
        rows.append([k.split('|')[0], k.split('|')[1], f'{min(gm):.2f}-{max(gm):.2f}' if gm else 'n/a', len(gm), fp(fq.get('rms_plain'), 3), fp(fq.get('rms_shr'), 3),
                     fp(fq.get('gamma_shr'), 2), fp(fq.get('rms_const'), 3)])
    L_.append(tab(['arm', 'level', 'gamma_meas range over cells', '#cells', 'rms log err K*(gamma_best)', 'rms log err K*_shr(gamma_shr)', 'gamma_shr', 'rms log err const-per-SNR'], rows) + '\n')
    L_.append(f'(i) A3 monotone: {verdict_i}; significant increases {R["pred_i_summary"]["significant_increases"]}\n')
    (out / 'C1_TABLE.md').write_text('\n'.join(L_) + '\n')


def plots(D, fer, kfail, R, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    col = dict(A3='k', SPg_flat='tab:blue', SPg_flat03='tab:green', SPg_slep='tab:red')
    ns, nr = len(D.snrs), len(D.rhos)
    fig, axs = plt.subplots(ns, nr, figsize=(4.2 * nr, 3.4 * ns), squeeze=False, sharey=True)
    for i, snr in enumerate(D.snrs):
        for j, rho in enumerate(D.rhos):
            ax = axs[i][j]
            r, s2 = rho / 1000, sig2(snr)
            for ar in D.arms:
                lo = [analyze.wilson(int(k), D.nF)[0] for k in kfail[(ar, snr, rho)]]
                hi = [analyze.wilson(int(k), D.nF)[1] for k in kfail[(ar, snr, rho)]]
                ax.errorbar(KS, fer[(ar, snr, rho)], yerr=[np.maximum(np.array(fer[(ar, snr, rho)]) - lo, 0), np.maximum(np.array(hi) - fer[(ar, snr, rho)], 0)], color=col[ar], marker='o', ms=3, lw=1, capsize=2, label=ar)
            ax.axvline(k_star(GAMMA_SPEC, r, s2), color='gray', ls='--', lw=1)
            ax.set_xscale('log')
            ax.set_xticks(KS)
            ax.set_xticklabels([str(int(k)) for k in KS], fontsize=7)
            ax.set_title(f'SNR {snr / 100:g} dB, rho {r:g}', fontsize=9)
            if j == 0:
                ax.set_ylabel('FER')
            if i == ns - 1:
                ax.set_xlabel('K = 8L')
    axs[0][0].legend(fontsize=7)
    fig.suptitle('C1: FER vs K (dashed: K* at gamma_th 1.2)', fontsize=10)
    fig.tight_layout()
    fig.savefig(out / 'c1_fer.png', dpi=130)
    plt.close(fig)
    fig, axs = plt.subplots(ns, nr, figsize=(4.2 * nr, 3.4 * ns), squeeze=False)
    for i, snr in enumerate(D.snrs):
        for j, rho in enumerate(D.rhos):
            ax = axs[i][j]
            for ar in SP_ARMS:
                if ar in D.arms:
                    d = R['eps'][f'{ar}|{snr / 100:g}|{rho / 1000:g}']
                    ax.plot(KS, d['obs'], marker='o', ms=3, color=col[ar], label=f'{ar} obs')
                    if ar == 'SPg_flat':
                        ax.plot(KS, d['pred_ls'], ls='--', color='gray', label='LS pred')
                        ax.plot(KS, d['pred_shrunk'], ls=':', color='tab:blue', label='shrunk pred (flat)')
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_title(f'SNR {snr / 100:g} dB, rho {rho / 1000:g}', fontsize=9)
            if i == ns - 1:
                ax.set_xlabel('K')
            if j == 0:
                ax.set_ylabel('eps1')
    axs[0][0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(out / 'c1_eps.png', dpi=130)
    plt.close(fig)


if __name__ == '__main__':
    main()
