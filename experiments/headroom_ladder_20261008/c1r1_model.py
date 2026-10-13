#!/usr/bin/env python
"""Round-1 joint estimation-detection loop law I_1(K) (task 10-08-doppler-cluster, research/c1-round1-loop-theory.md).

Model (frozen 2026-10-09; theory note section 4).  Physical units: a = 1 - rho, n = sigma2, channel energy 1, N = 1024.
  q(e)   = eta a (1 - e) / (n + e)            detector SINR; LMMSE split h = h^ + dh, |h^|^2 = 1 - e (link L1)
  v(e)   = M_unc(q(e))                         soft-symbol MSE, AWGN QPSK curve (T1)
  s(v)   = (n + a v) / ((rho + a (1 - v)) N),  beta = 1 / (1 + K s),  e_ind(v) = K s / (1 + K s)
  d(e)   = q v                                 Stein divergence of the posterior-mean symbol denoiser
  w(v)   = a (1 - v) / (rho + a (1 - v))       data share of the refit regressor energy
  c      = kappa(v) beta d,  kappa in {0 (independent errors), w (hypothesis H_w), 1 (full coherent absorption)}
  G(e)   = e_ind(v(e)) / (1 - c)^2;  e* = limit of G iterated from the pilot-only error e_ind(1);  I_1 = J_unc(q(e*))
  Kc_R1  = K where I_1(K) = I* (AWGN code threshold, T1 exit table).
eta = frozen T2 rule (true-H round-1 decoder-input logloss -> equivalent AWGN SINR / q_data); non-SP calibration.
Modes:  retro   -> out/c1r1/retro.json + RETRO.md (stored T0 / c1e rows; post-hoc, hypothesis-generating)
        predict -> out/c1r1/predictions_fresh.json (cells not yet simulated; eta from the rule once A3 rows exist,
                   reference numbers with eta interpolated from existing A3 cells)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

import c1_t2_model as m
import c1_t2_predict as P

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'c1r1'
N = 1024
D_COEF = 8
MODES = ('ind', 'H_w', 'coh')


class LoopLaw:
    def __init__(self, cu, rho, snr_db, K, eta, mode='H_w', link=True):
        self.cu, self.rho, self.a, self.n = cu, float(rho), 1. - float(rho), 10 ** (-float(snr_db) / 10)
        self.K, self.eta, self.mode, self.link = float(K), float(eta), mode, bool(link)

    def q(self, e):
        return self.eta * self.a * ((1. - e) if self.link else 1.) / (self.n + e)

    def parts(self, e):
        q = self.q(e)
        v = float(self.cu('M_unc', q))
        s = (self.n + self.a * v) / ((self.rho + self.a * (1. - v)) * N)
        beta = 1. / (1. + self.K * s)
        d = q * v
        w = self.a * (1. - v) / (self.rho + self.a * (1. - v))
        kappa = {'ind': 0., 'H_w': w, 'coh': 1.}[self.mode]
        c = kappa * beta * d
        return dict(q=q, v=v, s=s, beta=beta, d=d, w=w, c=c, e_ind=self.K * s / (1. + self.K * s))

    def G(self, e):
        p = self.parts(e)
        return p['e_ind'] / (1. - p['c']) ** 2

    def pilot_only(self):
        s = (self.n + self.a) / (self.rho * N)
        return self.K * s / (1. + self.K * s)

    def fixed_point(self, tol=1e-12, itmax=20000):
        e = self.pilot_only()
        for _ in range(itmax):
            e2 = self.G(e)
            if abs(e2 - e) < tol:
                break
            e = e2
        h = 1e-6 * max(e, 1e-6)
        slope = (self.G(e + h) - self.G(e - h)) / (2 * h)
        return dict(e=e, I1=float(self.cu('J_unc', self.q(e))), slope=float(slope), **self.parts(e))

    def all_fixed_points(self, n_grid=3000):
        grid = np.geomspace(1e-5, .98, n_grid)
        h = np.array([self.G(e) - e for e in grid])
        return [float(grid[i]) for i in np.nonzero(np.sign(h[:-1]) != np.sign(h[1:]))[0]]


def crossing(Ks, ys, level):
    for i in range(len(Ks) - 1):
        a, b = ys[i] - level, ys[i + 1] - level
        if a >= 0 > b or a < 0 <= b:
            return float(Ks[i] + a * (Ks[i + 1] - Ks[i]) / (a - b))
    return None


def i_star():
    return float(json.loads((HERE / 'out/c1_t1/t1_transfer.json').read_text())['exit']['I_in_at_crossings']['FER0.5_linear']['I_in'])


def retro(cu):
    t0 = json.loads((HERE / 'out/c1_t0/t0_screen.json').read_text())
    preds = json.loads((HERE / 'out/c1_t2/predictions.json').read_text())
    eta = {(c['dataset'], c['snr_db'], c['rho'], c['L']): c['eta'] for c in preds['cells']}
    phi = json.loads((HERE / 'out/c1e/analysis/c1e_phi.json').read_text())['Phi']
    istar = i_star()
    cells, groups = [], {}
    for name, ds in t0['datasets'].items():
        for c in ds['cells']:
            if c['arm'] != 'SPg_flat':
                continue
            key = (name, c['snr_db'], c['rho'], c['L'])
            rec = dict(dataset=name, snr_db=c['snr_db'], rho=c['rho'], L=c['L'], K=c['K'], eta=eta[key],
                       eps_ce1_obs=c['quantiles']['eps_ce1']['overall']['50'],
                       eps_det1_obs=c['quantiles']['eps_det1']['overall']['50'], fer_r1_obs=c['outcomes']['fer_r1'])
            for mode in MODES:
                for link in (False, True):
                    fp = LoopLaw(cu, c['rho'], c['snr_db'], c['K'], eta[key], mode, link).fixed_point()
                    rec[f'{mode}|L{int(link)}'] = dict(e=fp['e'], I1=fp['I1'], slope=fp['slope'], d=fp['d'], w=fp['w'], c=fp['c'])
            rec['pilot_only_pred'] = LoopLaw(cu, c['rho'], c['snr_db'], c['K'], eta[key]).pilot_only()
            cells.append(rec)
            groups.setdefault((name, c['snr_db'], c['rho']), []).append(rec)
    summary = {}
    for mode in MODES:
        for link in (False, True):
            tag = f'{mode}|L{int(link)}'
            lr = np.array([np.log(r[tag]['e'] / r['eps_det1_obs']) for r in cells])
            summary[tag] = dict(eps_ln_median=float(np.median(lr)), eps_abs_ln_median=float(np.median(abs(lr))),
                                frac_abs_ln_le_015=float(np.mean(abs(lr) <= .15)), frac_abs_ln_le_030=float(np.mean(abs(lr) <= .3)))
    kc = []
    for (name, snr, rho), recs in sorted(groups.items()):
        recs.sort(key=lambda r: r['K'])
        Ks = [r['K'] for r in recs]
        row = dict(dataset=name, snr_db=snr, rho=rho, Kc_r1_obs=crossing(Ks, [r['fer_r1_obs'] for r in recs], .5))
        for tag in ('ind|L1', 'H_w|L1', 'coh|L1', 'H_w|L0'):
            row[tag] = crossing(Ks, [r[tag]['I1'] for r in recs], istar)
        kc.append(row)
    phi_rows = []
    for snr, by_L in phi.items():
        for Lk, row in by_L.items():
            L = int(Lk.lstrip('L'))
            et = [r['eta'] for r in cells if r['dataset'] == 'c1_map' and r['snr_db'] == 6.5 and r['L'] == L] if snr == '6.5' else \
                 [r['eta'] for r in cells if r['dataset'] == 'c1_boot' and r['snr_db'] == 8. and r['rho'] == .3 and r['L'] == L]
            if not et:  # L 20/28 at 8 dB not in c1_boot: interpolate eta in L
                src = [(r['L'], r['eta']) for r in cells if r['dataset'] == 'c1_boot' and r['snr_db'] == 8. and r['rho'] == .3]
                src.sort()
                et = [float(np.interp(L, [s[0] for s in src], [s[1] for s in src]))]
            rec = dict(snr_db=float(snr), L=L, K=D_COEF * L, eta=et[0], I1_obs=row['none']['mi_in1']['mean'])
            for tag, (mode, link) in {'ind|L1': ('ind', 1), 'H_w|L1': ('H_w', 1), 'coh|L1': ('coh', 1), 'H_w|L0': ('H_w', 0)}.items():
                rec[tag] = LoopLaw(cu, .3, float(snr), D_COEF * L, et[0], mode, link).fixed_point()['I1']
            phi_rows.append(rec)
    multi = []
    for (name, snr, rho), recs in sorted(groups.items()):
        et = float(np.median([r['eta'] for r in recs]))
        for K in range(16, 1025, 16):
            fps = LoopLaw(cu, rho, snr, K, et).all_fixed_points()
            if len(fps) > 1:
                multi.append(dict(snr_db=snr, rho=rho, K=K, fixed_points=fps))
                break
    return dict(_argv=sys.argv, I_star=istar, summary=summary, kc_r1=kc, phi_none=phi_rows, first_multi_fp_K=multi, cells=cells)


def write_retro_md(res):
    f = lambda x: '-' if x is None else f'{x:.0f}'
    L = ['# C1 round-1 loop law: retrodiction on stored rows (post hoc, hypothesis-generating)', '',
         f"I* = {res['I_star']:.4f}. Modes: ind = independent soft-symbol errors (T2 structure); H_w = coherent fraction = data share w; "
         'coh = full coherent absorption. L0 = link q = eta a/(n+e) (T2), L1 = LMMSE link q = eta a (1-e)/(n+e).', '',
         '## eps_det1 (median over frames) vs fixed point e*, 56 SPg_flat cells', '',
         '| model | median ln(pred/obs) | median abs | abs<=.15 | abs<=.30 |', '|---|---|---|---|---|']
    for tag, s in res['summary'].items():
        L.append(f"| {tag} | {s['eps_ln_median']:+.3f} | {s['eps_abs_ln_median']:.3f} | {s['frac_abs_ln_le_015']:.2f} | {s['frac_abs_ln_le_030']:.2f} |")
    L += ['', '## Round-1 MI I_1 = Phi_K(none) (c1e, rho .3, frames 500-599)', '',
          '| SNR | K | I_1 obs | ind L1 | H_w L1 | coh L1 | H_w L0 |', '|---|---|---|---|---|---|---|']
    for r in sorted(res['phi_none'], key=lambda r: (r['snr_db'], r['K'])):
        L.append(f"| {r['snr_db']:g} | {r['K']} | {r['I1_obs']:.3f} | {r['ind|L1']:.3f} | {r['H_w|L1']:.3f} | {r['coh|L1']:.3f} | {r['H_w|L0']:.3f} |")
    L += ['', '## Round-1 cliff Kc_R1 (FER_r1 = .5 observed; I_1 = I* predicted)', '',
          '| dataset | SNR | rho | obs | ind L1 | H_w L1 | coh L1 | H_w L0 |', '|---|---|---|---|---|---|---|---|']
    for r in res['kc_r1']:
        L.append(f"| {r['dataset']} | {r['snr_db']:g} | {r['rho']:g} | {f(r['Kc_r1_obs'])} | {f(r['ind|L1'])} | {f(r['H_w|L1'])} | "
                 f"{f(r['coh|L1'])} | {f(r['H_w|L0'])} |")
    L += ['', '## First K (step 16, up to 1024) with more than one fixed point of the H_w L1 round-1 map', '']
    L += [f"- {r['snr_db']:g} dB rho {r['rho']:g}: K {r['K']}, fixed points {[round(x, 4) for x in r['fixed_points']]}" for r in res['first_multi_fp_K']] or ['- none']
    (OUT / 'RETRO.md').write_text('\n'.join(L) + '\n')


FRESH = [dict(snr_db=9.5, rho=.3, Ls=[8, 12, 16, 20, 24, 28, 32]),
         dict(snr_db=8., rho=.4, Ls=[8, 12, 16, 20, 24, 28, 32]),
         dict(snr_db=6.5, rho=.2, Ls=[4, 8, 12, 16, 20, 24])]


def eta_reference(snr, rho, L):
    """Reference eta only (primary predictions use the frozen eta rule on the new A3 rows): bilinear interpolation of
    the existing A3-derived eta over (SNR, rho) at the same L, clamped to the measured range."""
    preds = json.loads((HERE / 'out/c1_t2/predictions.json').read_text())
    tab = {}
    for c in preds['cells']:
        tab.setdefault((c['snr_db'], c['rho']), []).append((c['L'], c['eta']))
    def at(s, r):
        pts = sorted(tab[(s, r)])
        return float(np.interp(L, [p[0] for p in pts], [p[1] for p in pts]))
    if snr == 6.5:
        return at(6.5, .3) + (at(8., rho) - at(8., .3))  # rho offset borrowed from 8 dB
    rhos = [.2, .3, .5]
    by_s = {s: float(np.interp(rho, rhos, [at(s, r) for r in rhos])) for s in (8., 11.)}
    return float(np.interp(snr, [8., 11.], [by_s[8.], by_s[11.]]))


def predict(cu):
    istar = i_star()
    out = dict(_argv=sys.argv, I_star=istar, model='H_w|L1', rule='primary: eta from the frozen T2 eta rule on the new cell A3 rows; '
               'reference: eta_reference()', cells=[], kc_r1_reference={})
    for g in FRESH:
        Ks, I1s = [], []
        for L in g['Ls']:
            et = eta_reference(g['snr_db'], g['rho'], L)
            rec = dict(snr_db=g['snr_db'], rho=g['rho'], L=L, K=D_COEF * L, eta_reference=et)
            for tag, mode in (('H_w', 'H_w'), ('ind', 'ind'), ('coh', 'coh')):
                fp = LoopLaw(cu, g['rho'], g['snr_db'], D_COEF * L, et, mode, True).fixed_point()
                rec[tag] = dict(e=fp['e'], I1=fp['I1'], slope=fp['slope'], c=fp['c'], d=fp['d'], w=fp['w'])
            rec['pilot_only'] = LoopLaw(cu, g['rho'], g['snr_db'], D_COEF * L, et).pilot_only()
            out['cells'].append(rec)
            Ks.append(D_COEF * L)
            I1s.append(rec['H_w']['I1'])
        out['kc_r1_reference'][f"{g['snr_db']:g}|{g['rho']:g}"] = crossing(Ks, I1s, istar)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('mode', choices=('retro', 'predict'))
    args = ap.parse_args()
    cu, _ = P.load_curves(HERE / 'out/c1_t1/t1_transfer.json')
    OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == 'retro':
        res = retro(cu)
        (OUT / 'retro.json').write_text(json.dumps(res, indent=1, default=float))
        write_retro_md(res)
        print((OUT / 'RETRO.md').read_text())
    else:
        res = predict(cu)
        (OUT / 'predictions_fresh.json').write_text(json.dumps(res, indent=1, default=float))
        for c in res['cells']:
            print(c['snr_db'], c['rho'], c['K'], 'eta', round(c['eta_reference'], 3), 'e* H_w', round(c['H_w']['e'], 4),
                  'I1 H_w', round(c['H_w']['I1'], 3), 'ind', round(c['ind']['I1'], 3), 'coh', round(c['coh']['I1'], 3),
                  'slope', round(c['H_w']['slope'], 2))
        print('Kc_R1 reference', res['kc_r1_reference'])


if __name__ == '__main__':
    main()
