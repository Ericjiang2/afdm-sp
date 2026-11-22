#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 check for card I-20261122-l07 (2026-11-22, runner l, claude-fable-5.2).
Single-RF-chain power-only array: estimate the separation of two equal-power incoherent sources (or an angular
spread) from per-beam power readings.  New code (numpy/scipy only; the project receiver is not involved).
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch3.md.
  python l2_r3_spade.py smoke|run|read --out out_r3b3

Model.  M-element half-wavelength ULA, element index m = -(M-1)/2 .. (M-1)/2, steering a(u)_m = exp(j m u).
Two incoherent sources at ubar +- s, total per-element power P, noise variance sigma2 = 1 (array SNR gamma = M P).
One beam w (unit norm) per snapshot; |w^H x|^2 is exponential with mean mu(w) = (P/2)(|w^H a(ubar+s)|^2 +
|w^H a(ubar-s)|^2) + sigma2, so the mean power over L snapshots is mu * Gamma(L, 1) / L exactly.
"""
import argparse, json, os, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
SEED = 20261122
M = 32
MIDX = np.arange(M) - (M - 1) / 2
RAY = 2 * np.pi / M                       # Rayleigh width in u
LTOT, LCOARSE = 400, 40                   # total snapshots; snapshots spent on the coarse stage by the adaptive arms
DELTA0_BLIND = 0.05 * RAY                 # null offset used by every triad arm (does not use the true separation)
GAMMAS_DB = [15, 20, 25, 30]
XIS = [0.10, 0.15, 0.20, 0.35, 0.50]      # separation / Rayleigh width;  s = xi * RAY / 2
TRIALS = 500
WORKERS = 12
MAIN_ARMS = ['dft8', 'pencil_null', 'spade_unc', 'cm', 'cm_oracle_delta', 'cm_single_null']
EXTRA = {'q3': [(25, 0.20), (30, 0.20)],                                   # 3-bit phase shifters: nearest vs sigma-delta
         'unknown_noise': [(15, 0.15), (15, 0.20), (20, 0.15), (20, 0.20), (25, 0.20)],
         'gauss_truth': [(25, 0.20)]}


def steer(u):
    return np.exp(1j * np.outer(np.atleast_1d(u), MIDX))          # (len(u), M)


def pencil(uc):
    return np.exp(1j * MIDX * uc) / np.sqrt(M)


def cm_null(uc):                                                   # constant-modulus pi-step beam, null at uc
    return np.sign(MIDX) * np.exp(1j * MIDX * uc) / np.sqrt(M)


def spade_null(uc):                                                # amplitude-tapered first-derivative mode, null at uc
    return MIDX * np.exp(1j * MIDX * uc) / np.linalg.norm(MIDX)


def quantize(w, bits, mode):
    """Phase-only weights with b-bit phases.  'near': nearest level.  'sd': first-order error diffusion that keeps the
    running sum of sign(m) exp(-j eps_m) near zero (eps = phase error), i.e. protects the null of a pi-step beam."""
    q = 2 * np.pi / 2 ** bits; psi = np.angle(w)
    if mode == 'near':
        phi = np.round(psi / q) * q
    else:
        phi = np.zeros(M); run = 0j
        order = np.argsort(np.abs(MIDX), kind='stable')
        for i in order:
            lo = np.floor(psi[i] / q) * q; cands = (lo, lo + q)
            vals = [run + np.exp(-1j * (c - psi[i])) * np.sign(MIDX[i]) for c in cands]
            j = int(np.argmin(np.abs(vals))); phi[i] = cands[j]; run = vals[j]
    return np.exp(1j * phi) / np.sqrt(M)


def mean_power(W, P, ubar, s, sigma2=1.0):
    A = steer([ubar + s, ubar - s])                                # (2, M)
    R = np.abs(W.conj() @ A.T) ** 2                                # (K, 2)
    return 0.5 * P * R.sum(axis=1) + sigma2


def mean_power_gauss(W, P, ubar, srms, sigma2=1.0, nodes=41):      # Gaussian angular spread with rms srms (truth only)
    x, wq = np.polynomial.hermite_e.hermegauss(nodes); wq = wq / wq.sum()
    R = np.abs(W.conj() @ steer(ubar + srms * x).T) ** 2
    return P * R @ wq + sigma2


def fit(W, L, Phat, ubar0, P0, known_noise=True):
    """ML over (ln P, ubar, ln s[, ln sigma2]) from gamma-distributed beam powers; three starts in s."""
    def nll(x):
        s2 = 1.0 if known_noise else np.exp(x[3])
        mu = mean_power(W, np.exp(x[0]), x[1] * RAY, np.exp(x[2]) * RAY, s2)
        return float(np.sum(L * (np.log(mu) + Phat / mu)))
    best = None
    for s0 in (0.03, 0.10, 0.25):
        x0 = [np.log(max(P0, 1e-6)), ubar0 / RAY, np.log(s0)] + ([] if known_noise else [0.0])
        r = minimize(nll, x0, method='Nelder-Mead', options=dict(xatol=1e-4, fatol=1e-7, maxiter=600, maxfev=900))
        if best is None or r.fun < best.fun:
            best = r
    return float(np.exp(best.x[2]) * RAY), float(best.x[1] * RAY)


def coarse(Wd, Ld, Phat):
    """Point-source ML for the centroid from the coarse DFT sweep (three starts around the strongest beam)."""
    k = int(np.argmax(Phat)); uk = (k - 3) * RAY
    def nll(x):
        mu = np.exp(x[0]) * np.abs(Wd.conj() @ steer(x[1] * RAY)[0]) ** 2 + 1.0
        return float(np.sum(Ld * (np.log(mu) + Phat / mu)))
    best = None
    for du in (-0.4, 0.0, 0.4):
        r = minimize(nll, [np.log(max(Phat[k] - 1, 1e-3) / M), uk / RAY + du], method='Nelder-Mead',
                     options=dict(xatol=1e-4, fatol=1e-7, maxiter=300))
        if best is None or r.fun < best.fun:
            best = r
    return float(best.x[1] * RAY), float(np.exp(best.x[0]))


def digital_crb(P, ubar, s, L):
    """Slepian-Bangs bound for s with an M-chain coherent array and L snapshots; unknown (P, ubar, s), known noise."""
    def R(th):
        A = steer([th[1] + th[2], th[1] - th[2]])
        return 0.5 * th[0] * (A.T @ A.conj()) + np.eye(M)
    th = np.array([P, ubar, s]); R0i = np.linalg.inv(R(th)); D = []
    for i, h in enumerate((1e-6 * P, 1e-7, 1e-7)):
        e = np.zeros(3); e[i] = h; D.append((R(th + e) - R(th - e)) / (2 * h))
    J = np.array([[L * np.trace(R0i @ D[i] @ R0i @ D[j]).real for j in range(3)] for i in range(3)])
    return float(np.sqrt(np.linalg.inv(J)[2, 2]))


def triad(kind, uhat, delta0, bits=None, qmode=None):
    null = dict(pencil_null=lambda uc, sign: pencil(uc + sign * RAY), spade_unc=lambda uc, sign: spade_null(uc),
                cm=lambda uc, sign: cm_null(uc))[kind]
    beams = [pencil(uhat), null(uhat + delta0, +1), null(uhat - delta0, -1)]
    if bits:
        beams = [quantize(b, bits, 'near') if i == 0 else quantize(b, bits, qmode) for i, b in enumerate(beams)]
    return np.array(beams)


def cell(job):
    gdb, xi, trials = job
    rng = np.random.default_rng([SEED, gdb, int(round(xi * 100))])
    P = 10 ** (gdb / 10) / M; s = xi * RAY / 2
    Wd = np.array([pencil(k * RAY) for k in range(-3, 5)])        # 8 DFT beams around [0, RAY]
    arms = list(MAIN_ARMS)
    if (gdb, xi) in EXTRA['q3']:
        arms += ['cm_q3_near', 'cm_q3_sd']
    if (gdb, xi) in EXTRA['unknown_noise']:
        arms += ['cm_unknown_noise', 'pencil_null_unknown_noise']
    if (gdb, xi) in EXTRA['gauss_truth']:
        arms += ['cm_gauss_truth', 'dft8_gauss_truth']
    est = {a: [] for a in arms}; cent_err = []
    Ls2 = LTOT - LCOARSE
    for _ in range(trials):
        ubar = rng.uniform(0, RAY)
        draw = lambda mu, L: mu * rng.gamma(L, 1.0) / L
        # fixed DFT sweep with the whole budget
        Ld = np.full(8, LTOT / 8); Pd = draw(mean_power(Wd, P, ubar, s), Ld)
        k = int(np.argmax(Pd)); est['dft8'].append(fit(Wd, Ld, Pd, (k - 3) * RAY, max(Pd[k] - 1, 1e-3) / M)[0])
        # coarse stage shared by every adaptive arm
        Lc = np.full(8, LCOARSE / 8); Pc = draw(mean_power(Wd, P, ubar, s), Lc)
        uhat, Phat0 = coarse(Wd, Lc, Pc); cent_err.append(uhat - ubar)
        L3 = np.array([Ls2 / 2, Ls2 / 4, Ls2 / 4])
        def adaptive(W2, L2, truth_fn=mean_power, known_noise=True):
            P2 = draw(truth_fn(W2, P, ubar, s), L2)
            return fit(np.vstack([Wd, W2]), np.r_[Lc, L2], np.r_[Pc, P2], uhat, Phat0, known_noise)[0]
        for kind in ('pencil_null', 'spade_unc', 'cm'):
            est[kind].append(adaptive(triad(kind, uhat, DELTA0_BLIND), L3))
        est['cm_oracle_delta'].append(adaptive(triad('cm', uhat, 0.5 * s), L3))
        est['cm_single_null'].append(adaptive(np.array([pencil(uhat), cm_null(uhat)]), np.array([Ls2 / 2, Ls2 / 2])))
        if 'cm_q3_near' in est:
            for qm in ('near', 'sd'):
                est[f'cm_q3_{qm}'].append(adaptive(triad('cm', uhat, DELTA0_BLIND, 3, qm), L3))
        if 'cm_unknown_noise' in est:
            Ln = np.r_[0.9 * L3, 0.1 * Ls2]; far = pencil(uhat + np.pi)
            for kind in ('cm', 'pencil_null'):
                est[f'{kind}_unknown_noise'].append(adaptive(np.vstack([triad(kind, uhat, DELTA0_BLIND), far]), Ln, known_noise=False))
        if 'cm_gauss_truth' in est:
            est['cm_gauss_truth'].append(adaptive(triad('cm', uhat, DELTA0_BLIND), L3, truth_fn=mean_power_gauss))
            Pg = draw(mean_power_gauss(Wd, P, ubar, s), Ld); k = int(np.argmax(Pg))
            est['dft8_gauss_truth'].append(fit(Wd, Ld, Pg, (k - 3) * RAY, max(Pg[k] - 1, 1e-3) / M)[0])
    out = dict(gamma_db=gdb, xi=xi, trials=trials, s=s, coarse_centroid_rmse_over_ray=float(np.sqrt(np.mean(np.square(cent_err))) / RAY),
               digital_crb_rel=digital_crb(P, 0.37 * RAY, s, LTOT) / s, arms={})
    for a, v in est.items():
        e = (np.array(v) - s) / s
        boot = [np.sqrt(np.mean(e[rng.integers(0, len(e), len(e))] ** 2)) for _ in range(1000)]
        out['arms'][a] = dict(rel_rmse=float(np.sqrt(np.mean(e ** 2))), rel_rmse_ci95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                              rel_bias=float(np.mean(e)), rel_mad=float(np.median(np.abs(e))))
    return out


def leakage(bits=3, n=4000):
    rng = np.random.default_rng([SEED, 7]); res = {}
    for mode in ('near', 'sd'):
        v = []
        for _ in range(n):
            uc = rng.uniform(-np.pi, np.pi); w = quantize(cm_null(uc), bits, mode)
            v.append(abs(np.vdot(w, steer(uc)[0])) ** 2 / M)            # response at the intended null, relative to a matched pencil
        res[mode] = dict(mean_db=float(10 * np.log10(np.mean(v))), median_db=float(10 * np.log10(np.median(v))))
    res['reduction_mean_db'] = res['near']['mean_db'] - res['sd']['mean_db']
    return res


def gates():
    """Closed forms quoted by the card, checked numerically: derivative-mode efficiency of the pi-step beam and of the
    first-null pencil, and exact nulls."""
    d = spade_null(0.0)
    eta_cm = abs(np.vdot(cm_null(0.0), d)) ** 2; eta_pn = abs(np.vdot(pencil(RAY), d)) ** 2
    return dict(eta_cm=float(eta_cm), eta_cm_closed=0.75 * M * M / (M * M - 1), eta_pencil_null=float(eta_pn),
                eta_pencil_null_closed=3 / ((M * M - 1) * np.sin(np.pi / M) ** 2),
                null_cm=float(abs(np.vdot(cm_null(0.3), steer(0.3)[0]))), null_pencil=float(abs(np.vdot(pencil(0.3 + RAY), steer(0.3)[0]))))


def run(out, trials=TRIALS):
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(g, x, trials) for g in GAMMAS_DB for x in XIS]
    t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        cells = pool.map(cell, jobs)
    res = dict(_argv=sys.argv, _config=dict(M=M, LTOT=LTOT, LCOARSE=LCOARSE, delta0_blind_over_ray=DELTA0_BLIND / RAY, gammas_db=GAMMAS_DB,
                                           xis=XIS, trials=trials, seed=SEED, extra={k: [list(c) for c in v] for k, v in EXTRA.items()}),
               gates=gates(), leakage_3bit=leakage(), cells=cells, wall_seconds=time.time() - t0)
    (out / 'spade_rows.json').write_text(json.dumps(res, indent=1)); print('done', round(res['wall_seconds'], 1), 's')


def read(out):
    res = json.loads((out / 'spade_rows.json').read_text()); C = {(c['gamma_db'], c['xi']): c for c in res['cells']}
    r = lambda g, x, a: C[(g, x)]['arms'][a]['rel_rmse']
    a_cell = C[(25, 0.20)]
    crit_a = dict(cm=r(25, 0.20, 'cm'), dft8=r(25, 0.20, 'dft8'), digital_crb=a_cell['digital_crb_rel'],
                  ratio_dft_over_cm=r(25, 0.20, 'dft8') / r(25, 0.20, 'cm'), ratio_cm_over_digital=r(25, 0.20, 'cm') / a_cell['digital_crb_rel'])
    crit_a['pass'] = bool(crit_a['ratio_dft_over_cm'] >= 5 and crit_a['ratio_cm_over_digital'] <= 2.5)
    gains = {f'{g}|{x}': 20 * np.log10(r(g, x, 'pencil_null') / r(g, x, 'cm')) for g in (15, 20) for x in (0.15, 0.20)}
    crit_b = dict(mse_gain_db=gains, mean_db=float(np.mean(list(gains.values())))); crit_b['pass'] = bool(crit_b['mean_db'] >= 2.5)
    lk = res['leakage_3bit']
    crit_c = dict(leakage=lk, mse_plateau_gain_db=20 * np.log10(r(30, 0.20, 'cm_q3_near') / r(30, 0.20, 'cm_q3_sd')))
    crit_c['pass'] = bool(lk['reduction_mean_db'] >= 6 or crit_c['mse_plateau_gain_db'] >= 6)
    un = {f'{g}|{x}': 20 * np.log10(r(g, x, 'pencil_null_unknown_noise') / r(g, x, 'cm_unknown_noise')) for g in (15, 20) for x in (0.15, 0.20)}
    single = {f'{g}|{x}': 20 * np.log10(r(g, x, 'cm_single_null') / r(g, x, 'cm')) for g in (15, 20, 25) for x in (0.15, 0.20)}
    table = {f'{g}|{x}': dict(digital_crb=round(C[(g, x)]['digital_crb_rel'], 4), coarse_cent=round(C[(g, x)]['coarse_centroid_rmse_over_ray'], 3),
                              **{a: round(v['rel_rmse'], 4) for a, v in C[(g, x)]['arms'].items()}) for g in GAMMAS_DB for x in XIS}
    summ = dict(gates=res['gates'], criterion_a=crit_a, criterion_b=crit_b, criterion_c=crit_c,
                secondary=dict(unknown_noise_mse_gain_db=un, unknown_noise_mean_db=float(np.mean(list(un.values()))),
                               triad_over_single_null_mse_gain_db=single,
                               gauss_truth=dict(cm=r(25, 0.20, 'cm_gauss_truth'), dft8=r(25, 0.20, 'dft8_gauss_truth'))),
                verdict='PASS' if crit_a['pass'] and crit_b['pass'] and crit_c['pass'] else 'KILL', rel_rmse_table=table,
                wall_seconds=res['wall_seconds'])
    (out / 'spade_summary.json').write_text(json.dumps(summ, indent=1)); print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['smoke', 'run', 'read']); ap.add_argument('--out', default='out_r3b3')
    a = ap.parse_args(); o = HERE / a.out
    if a.mode == 'smoke':
        t0 = time.process_time(); c = cell((25, 0.20, 20)); t = time.process_time() - t0
        print(json.dumps(dict(gates=gates(), leakage=leakage(n=300), cpu_per_trial=t / 20, est_core_hours=t / 20 * TRIALS * len(GAMMAS_DB) * len(XIS) / 3600,
                              sample={k: round(v['rel_rmse'], 3) for k, v in c['arms'].items()}, digital=c['digital_crb_rel']), indent=1))
    elif a.mode == 'run':
        run(o)
    else:
        read(o)
