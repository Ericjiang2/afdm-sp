#!/usr/bin/env python
"""Gates for the CRB reference (protocol.md section 6, task 10-16-tcom-channel-crb).

--stage local   G2 (small example), G3 (a, c, d, e; b with i.i.d. QPSK), G4 (small), G5, G5b.  Needs only physical.py.
--stage remote  G1, G2 (3 production frames), G3b (production codewords), G4 (production), G7.  Needs the P1 context.
--stage smoke   G6 and G8 from a 20-frame driver run (crb_driver.py --frames 20) against the P1 ledger.
Every gate writes its numbers to <out>/gates_<stage>.json with _argv and _config; the process exits 1 on any failure.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
import time

import numpy as np
import scipy.linalg as sla

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import crb  # noqa: E402

FROZEN_SRC = PROJECT / 'experiments' / 'sp_afdm_frozen_20260920' / 'src'


def rel(a, b):
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)) / max(np.linalg.norm(np.asarray(b)), 1e-300))


def boot_se(samples, target, stat, rng, reps=200):
    """Bootstrap SE (over MC draws, axis 0) of the relative Frobenius error of stat(samples) against target."""
    m = len(samples)
    vals = [rel(stat(samples[rng.integers(0, m, m)]), target) for _ in range(reps)]
    return float(np.std(vals))


class Small:
    """N = 64 test model with an equal-delay pair (protocol G2-G5)."""

    def __init__(self, Channel, daft, seed=1):
        self.Channel, self.daft = Channel, daft
        rng = np.random.default_rng(seed)
        self.n, self.c1, self.c2 = 64, 5 / (2 * 64), np.sqrt(2) / 64
        self.l = np.array([0, 3, 3])
        self.nu = np.array([.3, -.7, .45])
        g = rng.standard_normal(3) + 1j * rng.standard_normal(3)
        self.g = g / np.linalg.norm(g)
        self.P = 3

    def regress(self, nu=None):
        nu = self.nu if nu is None else nu
        ch = self.Channel(self.n, self.c1, self.c2, self.l, nu, np.ones(self.P))
        return lambda u, deriv: ch.regressors(u, derivative=deriv)

    def apply(self, nu, g, x):
        return self.Channel(self.n, self.c1, self.c2, self.l, nu, g).apply(x)

    def dense(self, nu=None, g=None):
        nu = self.nu if nu is None else nu
        g = self.g if g is None else g
        ch = self.Channel(self.n, self.c1, self.c2, self.l, nu, g)
        return np.stack([ch.apply(e) for e in np.eye(self.n)], 1)  # columnwise (apply takes vectors only)

    def unpack(self, th):
        P = self.P
        return th[:P], th[P:2 * P] + 1j * th[2 * P:]

    def theta(self):
        return np.concatenate([self.nu, self.g.real, self.g.imag])

    def mu(self, th, x):
        nu, g = self.unpack(th)
        return self.apply(nu, g, x)

    def cov(self, th, rho, sigma2):
        nu, g = self.unpack(th)
        H = self.dense(nu, g)
        return (1 - rho) * H @ H.conj().T + sigma2 * np.eye(self.n)


# ------------------------------------------------------------------------------------------------ local gates
def stage_local(out):
    sys.path.insert(0, str(FROZEN_SRC))
    from physical import Channel, daft
    s = Small(Channel, daft)
    rng = np.random.default_rng(20261016)
    res, ok = {}, True
    n, P = s.n, s.P
    H = s.dense()

    # G2: K, ||H||_F^2, NMSE, derivative columns against dense / finite differences
    dense_d = []
    for a in range(3 * P):
        if a < P:
            e = np.zeros(P); e[a] = 1e-6
            dense_d.append((s.dense(s.nu + e) - s.dense(s.nu - e)) / 2e-6)
        else:
            e = np.zeros(P, complex); e[(a - P) % P] = 1 if a < 2 * P else 1j
            dense_d.append(s.dense(g=e))
    Kd = np.array([[np.vdot(A, B) for B in dense_d] for A in dense_d])
    K = crb.gram_K(s.l, s.nu, s.g, n)
    est = dict(delays=[0, 3, 5], dopplers=[.31, -.6, 1.2], gains=[.5 + .1j, -.3j, .05])
    tru = dict(delays=s.l, dopplers=s.nu, gains=s.g)
    He = Channel(n, s.c1, s.c2, est['delays'], est['dopplers'], est['gains'])
    He = np.stack([He.apply(e) for e in np.eye(n)], 1)
    u = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    B = crb.regressor_matrix(s.regress(), u, s.g)
    fd = {}
    for h in (1e-5, 1e-6, 1e-7):
        cols = []
        for i in range(P):
            e = np.zeros(P); e[i] = h
            cols.append((s.mu(np.concatenate([s.nu + e, s.g.real, s.g.imag]), u)
                         - s.mu(np.concatenate([s.nu - e, s.g.real, s.g.imag]), u)) / (2 * h))
        fd[h] = np.stack(cols, 1)
    res['G2'] = dict(K_rel=rel(K, Kd), frob_rel=abs(crb.frob2(s.l, s.nu, s.g, n) - np.linalg.norm(H) ** 2) / np.linalg.norm(H) ** 2,
                     nmse_rel=abs(crb.channel_nmse(est, tru, n) - np.linalg.norm(He - H) ** 2 / np.linalg.norm(H) ** 2)
                     / (np.linalg.norm(He - H) ** 2 / np.linalg.norm(H) ** 2),
                     nmse_truth=crb.channel_nmse(tru, tru, n),
                     deriv_rel={str(h): rel(B[:, :P], v) for h, v in fd.items()},
                     deriv_step_spread=max(rel(fd[1e-5], fd[1e-6]), rel(fd[1e-6], fd[1e-7])))
    g2 = res['G2']
    res['G2']['pass'] = bool(g2['K_rel'] <= 1e-9 and g2['frob_rel'] <= 1e-9 and g2['nmse_rel'] <= 1e-9
                             and g2['nmse_truth'] <= 1e-12 and max(g2['deriv_rel'].values()) <= 1e-6
                             and g2['deriv_step_spread'] <= 1e-5)

    # common Monte-Carlo set-up
    M, sigma2, rho = 20000, .1, .4
    th0 = s.theta()
    xp = np.sqrt(rho) * np.exp(2j * np.pi * rng.random(n))
    qpsk = lambda size: ((1 - 2 * rng.integers(0, 2, size)) + 1j * (1 - 2 * rng.integers(0, 2, size))) / np.sqrt(2)
    x = xp + np.sqrt(1 - rho) * qpsk(n)
    hstep = 1e-6

    def perturbed(fn):
        plus, minus = [], []
        for a in range(3 * P):
            e = np.zeros(3 * P); e[a] = hstep
            plus.append(fn(th0 + e)); minus.append(fn(th0 - e))
        return plus, minus

    # G3e noise variances
    w = (rng.standard_normal((M, n)) + 1j * rng.standard_normal((M, n))) * np.sqrt(sigma2 / 2)
    res['G3e'] = dict(re_var=float(np.var(w.real)), im_var=float(np.var(w.imag)), target=sigma2 / 2)
    res['G3e']['pass'] = bool(abs(res['G3e']['re_var'] / (sigma2 / 2) - 1) <= .03 and abs(res['G3e']['im_var'] / (sigma2 / 2) - 1) <= .03)

    # G3a DA: finite-difference score of -||y - mu||^2 / sigma2
    mu0 = s.mu(th0, x)
    y = mu0[None, :] + w
    mp, mm = perturbed(lambda th: s.mu(th, x))
    score = np.stack([(-np.sum(np.abs(y - p_) ** 2, 1) + np.sum(np.abs(y - m_) ** 2, 1)) / sigma2 / (2 * hstep)
                      for p_, m_ in zip(mp, mm)], 1)
    J_da = crb.fim_da(crb.regressor_matrix(s.regress(), x, s.g), sigma2)
    cov = lambda sc: sc.T @ sc / len(sc)
    se_mean = score.std(0) / np.sqrt(M)
    err, se = rel(cov(score), J_da), boot_se(score, J_da, cov, rng)
    res['G3a'] = dict(rel=err, se=se, score_mean_max_z=float(np.max(np.abs(score.mean(0)) / se_mean)))
    res['G3a']['pass'] = bool(err <= max(3 * se, .03) and res['G3a']['score_mean_max_z'] <= 4)

    # G3b MCRB with i.i.d. QPSK (production codewords: remote stage)
    bp = crb.regressor_matrix(s.regress(), xp, s.g)
    J_m = crb.fim_mcrb(bp, crb.gram_K(s.l, s.nu, s.g, n), rho, sigma2)
    reg = s.regress()
    samples = np.stack([crb.fim_da(crb.regressor_matrix(reg, xp + np.sqrt(1 - rho) * qpsk(n), s.g), sigma2)
                        for _ in range(M)])
    err, se = rel(samples.mean(0), J_m), boot_se(samples, J_m, lambda z: z.mean(0), rng)
    res['G3b_small'] = dict(rel=err, se=se, pass_=bool(err <= max(3 * se, .03)))

    # G3c / G3d GD: finite-difference score of the exact Gaussian log-likelihood
    def gd_check(xpp, label):
        def loglik_fn(th):
            C = s.cov(th, rho, sigma2)
            L = np.linalg.cholesky(C)
            return s.mu(th, xpp), L
        base_mu, base_L = loglik_fn(th0)
        dg = (rng.standard_normal((M, n)) + 1j * rng.standard_normal((M, n))) / np.sqrt(2)
        noise = dg @ base_L.T  # rows ~ CN(0, C)
        yy = base_mu[None, :] + noise
        def ll(mu_, L):
            r = sla.solve_triangular(L, (yy - mu_[None, :]).T, lower=True)
            return -2 * np.sum(np.log(np.abs(np.diag(L)))) - np.sum(np.abs(r) ** 2, 0)
        sc = []
        for a in range(3 * P):
            e = np.zeros(3 * P); e[a] = hstep
            sc.append((ll(*loglik_fn(th0 + e)) - ll(*loglik_fn(th0 - e))) / (2 * hstep))
        sc = np.stack(sc, 1)
        t_op = crb.time_operator(s.l, s.nu, s.g, n, s.c1)
        cho = sla.cho_factor(crb.interference_cov(t_op, rho, sigma2), lower=True)
        bpt = daft(crb.regressor_matrix(s.regress(), xpp, s.g), s.c1, s.c2, True)
        J = crb.fim_pi(bpt, cho) + crb.fim_gd_cov(t_op, crb.param_time_operators(s.l, s.nu, s.g, n, s.c1), cho, rho)
        err, se = rel(cov(sc), J), boot_se(sc, J, cov, rng)
        res[label] = dict(rel=err, se=se, pass_=bool(err <= max(3 * se, .03)))
        return J
    gd_check(xp, 'G3c')
    gd_check(np.zeros(n, complex), 'G3d')
    for key in ('G3b_small', 'G3c', 'G3d'):
        res[key]['pass'] = res[key].pop('pass_')

    # G4 closed-form identity with R_x = I
    frob = crb.frob2(s.l, s.nu, s.g, n)
    U = crb.constraint_basis(s.g)
    J_white = (2 / sigma2) * K.real
    bc, _ = crb.h_bound(J_white, K, frob, U)
    bu, _ = crb.h_bound(J_white, K, frob, None)
    res['G4_small'] = dict(c_rel=abs(bc / ((3 * P - 1) * sigma2 / (2 * frob)) - 1), u_rel=abs(bu / (3 * P * sigma2 / (2 * frob)) - 1))
    res['G4_small']['pass'] = bool(res['G4_small']['c_rel'] <= 1e-10 and res['G4_small']['u_rel'] <= 1e-10)

    # G5 attainability: Gauss-Newton ML with known data at 30 dB
    s2 = 1e-3
    J5 = crb.fim_da(crb.regressor_matrix(s.regress(), x, s.g), s2)
    crb5 = np.linalg.inv(J5)
    errs, nm = [], []
    for _ in range(5000):
        yv = mu0 + (rng.standard_normal(n) + 1j * rng.standard_normal(n)) * np.sqrt(s2 / 2)
        th = th0.copy()
        for _it in range(4):
            nu_, g_ = s.unpack(th)
            Bt = crb.regressor_matrix(s.regress(nu_), x, g_)
            r = yv - s.apply(nu_, g_, x)
            th = th + np.linalg.lstsq(np.vstack([Bt.real, Bt.imag]), np.concatenate([r.real, r.imag]), rcond=None)[0]
        errs.append(th - th0)
        nu_, g_ = s.unpack(th)
        nm.append(crb.channel_nmse(dict(delays=s.l, dopplers=nu_, gains=g_), tru, n))
    E = np.array(errs)
    hb, _ = crb.h_bound(J5, K, frob, None)
    res['G5'] = dict(theta_ratio=float(np.trace(E.T @ E / len(E)) / np.trace(crb5)), h_ratio=float(np.mean(nm) / hb))
    res['G5']['pass'] = bool(.9 <= res['G5']['theta_ratio'] <= 1.1 and .9 <= res['G5']['h_ratio'] <= 1.1)

    # G5b independent anchor: one path, known Doppler, one complex gain, LS
    ch1 = Channel(n, s.c1, s.c2, [2], [.37], [1.])
    b = ch1.regressors(x)[:, 0]
    g1 = .6 - .8j
    ww = (rng.standard_normal((M, n)) + 1j * rng.standard_normal((M, n))) * np.sqrt(sigma2 / 2)
    ghat = ((g1 * b)[None, :] + ww) @ b.conj() / np.vdot(b, b).real
    mse = float(np.mean(np.abs(ghat - g1) ** 2))
    target = sigma2 / np.vdot(b, b).real
    Bg = np.stack([b, 1j * b], 1)
    impl = float(np.trace(np.linalg.inv(crb.fim_da(Bg, sigma2))))
    res['G5b'] = dict(mc_rel=abs(mse / target - 1), impl_rel=abs(impl / target - 1))
    res['G5b']['pass'] = bool(res['G5b']['mc_rel'] <= .03 and res['G5b']['impl_rel'] <= 1e-10)
    return res


# ------------------------------------------------------------------------------------------------ remote gates
def stage_remote(out, frames=50):
    import p1ctx
    ctx = p1ctx.load()
    from physical import daft
    res = {}
    n = 1024
    c1, c2 = ctx.system.c1, ctx.system.c2
    g1 = {'max_model_rel': 0., 'max_nmse_truth': 0., 'max_power_dev': 0.}
    prod = []
    for scen in ('U', 'G'):
        for f in range(frames):
            raw, diag, truth = p1ctx.frame(ctx, scen, .3, 6.0, f)
            ch = ctx.Channel(n, c1, c2, truth['l_i'], truth['k_real'], truth['g_i'])
            g1['max_model_rel'] = max(g1['max_model_rel'], rel(ch.apply(raw['pilot'] + raw['data']), raw['noiseless']))
            tr = dict(delays=truth['l_i'], dopplers=truth['k_real'], gains=truth['g_i'])
            g1['max_nmse_truth'] = max(g1['max_nmse_truth'], crb.channel_nmse(tr, tr, n))
            g1['max_power_dev'] = max(g1['max_power_dev'], abs(np.sum(np.abs(truth['g_i']) ** 2) - 1))
            if f < 3 and scen == 'U' or f < 1:
                prod.append((scen, f, raw, truth))
    g1['pass'] = bool(g1['max_model_rel'] <= 1e-10 and g1['max_nmse_truth'] <= 1e-12 and g1['max_power_dev'] <= 1e-12)
    res['G1'] = g1

    # G2 / G4 on production frames (dense H columnwise; nu derivatives by central differences)
    g2 = []
    for scen, f, raw, truth in prod[:3]:
        l, nu, g = np.asarray(truth['l_i']), np.asarray(truth['k_real'], float), np.asarray(truth['g_i'])
        P = len(g)
        dense = lambda nu_, g_: np.stack([ctx.Channel(n, c1, c2, l, nu_, g_).apply(e) for e in np.eye(n)], 1)
        H = dense(nu, g)
        D = []
        for a in range(3 * P):
            if a < P:
                e = np.zeros(P); e[a] = 1e-6
                D.append((dense(nu + e, g) - dense(nu - e, g)) / 2e-6)
            else:
                e = np.zeros(P, complex); e[(a - P) % P] = 1 if a < 2 * P else 1j
                D.append(dense(nu, e))
        Kd = np.array([[np.vdot(A, B) for B in D] for A in D])
        K = crb.gram_K(l, nu, g, n)
        frob = crb.frob2(l, nu, g, n)
        J_white = (2 / .25) * K.real
        U = crb.constraint_basis(g)
        bc, _ = crb.h_bound(J_white, K, frob, U)
        bu, _ = crb.h_bound(J_white, K, frob, None)
        est = dict(delays=l, dopplers=nu + .05, gains=g * 1.1)
        He = dense(nu + .05, g * 1.1)
        nm_d = np.linalg.norm(He - H) ** 2 / np.linalg.norm(H) ** 2
        g2.append(dict(scen=scen, frame=f, K_rel=rel(K, Kd), frob_rel=abs(frob / np.linalg.norm(H) ** 2 - 1),
                       nmse_rel=abs(crb.channel_nmse(est, dict(delays=l, dopplers=nu, gains=g), n) / nm_d - 1),
                       g4_c_rel=abs(bc / ((3 * P - 1) * .25 / (2 * frob)) - 1), g4_u_rel=abs(bu / (3 * P * .25 / (2 * frob)) - 1)))
    res['G2_prod'] = dict(frames=g2, pass_=bool(all(r['K_rel'] <= 1e-9 and r['frob_rel'] <= 1e-9 and r['nmse_rel'] <= 1e-9 for r in g2)))
    res['G4_prod'] = dict(pass_=bool(all(r['g4_c_rel'] <= 1e-10 and r['g4_u_rel'] <= 1e-10 for r in g2)))

    # G3b on a production frame with real LDPC codewords, against the exact-R_d J_M (amendment A1)
    G = np.asarray(ctx.code['G']).astype(np.uint8) % 2
    if G.shape[0] != ctx.code['k']:
        G = G.T
    scen, f, raw, truth = prod[0]
    rho, sigma2 = .3, 10 ** (-.6)
    l, nu, g = np.asarray(truth['l_i']), np.asarray(truth['k_real'], float), np.asarray(truth['g_i'])
    ch1 = ctx.Channel(n, c1, c2, l, nu, np.ones(len(g)))
    regress = lambda u, d: ch1.regressors(u, derivative=d)
    xp = np.sqrt(rho) * ctx.system._zc_seq
    offdiag = crb.coded_offdiag(G, n, rho)
    K = crb.gram_K(l, nu, g, n)
    b_p = crb.regressor_matrix(regress, xp, g)
    J_m = crb.fim_mcrb(b_p, K, rho, sigma2, crb.mcrb_offdiag_term(regress, g, offdiag, n))
    J_iid = crb.fim_mcrb(b_p, K, rho, sigma2)
    rng = np.random.default_rng(7)
    samples = []
    M = 2000
    D_sum = np.zeros((n, n), complex)
    for _ in range(M):
        info = rng.integers(0, 2, size=ctx.code['k']).astype(np.uint8)
        d = np.sqrt(1 - rho) * ctx.qpsk_map(ctx.encode(ctx.code, info), scale=1)
        D_sum += np.outer(d, d.conj())
        samples.append(crb.fim_da(crb.regressor_matrix(regress, xp + d, g), sigma2))
    samples = np.stack(samples)
    err, se = rel(samples.mean(0), J_m), boot_se(samples, J_m, lambda z: z.mean(0), rng)
    res['G3b_prod'] = dict(rel=err, se=se, rel_vs_iid=rel(samples.mean(0), J_iid), exact_vs_iid=rel(J_m, J_iid),
                           pass_=bool(err <= max(3 * se, .03)))

    # G7 (amendment A1): exact off-diagonal R_d from G against the empirical E dd^H over M codewords
    Dm = D_sum / M
    sd = (1 - rho) / np.sqrt(M)
    exact = np.zeros((n, n), complex)
    for (s_, t_), r_st in offdiag.items():
        exact[s_, t_] = r_st
    nz = [(s_, t_) for (s_, t_) in offdiag]
    z_nz = [float(abs(Dm[s_, t_] - exact[s_, t_]) / sd) for s_, t_ in nz]
    mask = ~np.eye(n, dtype=bool)
    for s_, t_ in nz:
        mask[s_, t_] = False
    rms_ratio = float(np.sqrt(np.mean(np.abs(Dm[mask]) ** 2)) / sd)
    diag_dev = float(np.max(np.abs(np.diag(Dm).real - (1 - rho))))
    dup_pairs = len(nz) // 2
    res['G7'] = dict(correlated_symbol_pairs=dup_pairs, pairs=[[int(a), int(b), complex(v).real, complex(v).imag]
                                                               for (a, b), v in offdiag.items() if a < b],
                     max_z_nonzero=max(z_nz) if z_nz else 0., rms_ratio_rest=rms_ratio, diag_dev=diag_dev,
                     pass_=bool((max(z_nz) if z_nz else 0.) <= 4 and .95 <= rms_ratio <= 1.05 and diag_dev <= 1e-12))
    for key in ('G2_prod', 'G4_prod', 'G3b_prod', 'G7'):
        res[key]['pass'] = res[key].pop('pass_')
    return res


# ------------------------------------------------------------------------------------------------ smoke gates
def stage_smoke(out, smoke_dir, p1_rows_dir):
    rows = []
    for p in sorted(Path(smoke_dir).glob('rows_shard*.jsonl')):
        rows += [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    keys = {(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame']) for r in rows}
    ledger = {}
    for p in sorted(Path(p1_rows_dir).glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                k = (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
                if k in keys:
                    ledger[k] = (r['arms']['F0']['decoded_sha256'], r['arms']['B']['decoded_sha256'])
    mism = [k for k in keys if k not in ledger]
    for r in rows:
        k = (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
        if k in ledger and (r['F0']['decoded_sha256'], r['B']['decoded_sha256']) != ledger[k]:
            mism.append(k)
    flagged = {}
    for r in rows:
        cell = (r['scenario'], r['rho_permille'], r['snr_centi_db'])
        flagged.setdefault(cell, []).append(bool(r['bounds']['mcrb']['flagged']))
    worst = max(np.mean(v) for v in flagged.values())
    secs = np.array([r['seconds_receivers'] for r in rows]), np.array([r['seconds_bounds'] for r in rows])
    gd = np.array([r['seconds_gd'] for r in rows if r.get('seconds_gd')])
    return {'G6_smoke': dict(cells=len(rows), matched=len(rows) - len(mism), mismatches=[list(m) for m in mism[:20]],
                             pass_=bool(len(mism) == 0 and len(rows) > 0)),
            'G8': dict(worst_cell_flagged=float(worst), pass_=bool(worst <= .01)),
            'timing': dict(receivers_mean=float(secs[0].mean()), bounds_mean=float(secs[1].mean()),
                           gd_mean=float(gd.mean()) if len(gd) else None)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--stage', choices=('local', 'remote', 'smoke'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--smoke-dir', type=Path)
    p.add_argument('--p1-rows', type=Path, default=PROJECT / 'experiments' / 'tcom_reference_frame_20261015' / 'out' / 'p1')
    args = p.parse_args(argv)
    t0 = time.perf_counter()
    if args.stage == 'local':
        res = stage_local(args.out)
    elif args.stage == 'remote':
        res = stage_remote(args.out)
    else:
        res = stage_smoke(args.out, args.smoke_dir, args.p1_rows)
        for v in res.values():
            if 'pass_' in v:
                v['pass'] = v.pop('pass_')
    status = all(v.get('pass', True) for v in res.values())
    doc = dict(_argv=sys.argv, _config=dict(stage=args.stage, cond_limit=crb.COND_LIMIT), gates=res, all_pass=status,
               seconds=time.perf_counter() - t0)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f'gates_{args.stage}.json').write_text(json.dumps(doc, indent=1, default=float) + '\n')
    for k, v in res.items():
        print(k, 'PASS' if v.get('pass', True) else 'FAIL', {a: b for a, b in v.items() if a not in ('frames', 'mismatches')})
    print('ALL PASS' if status else 'GATE FAILURE')
    sys.exit(0 if status else 1)


if __name__ == '__main__':
    main()
