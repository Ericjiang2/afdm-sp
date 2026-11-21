#!/usr/bin/env python
"""E-3 unit gates (numpy/scipy only; no receiver context, no data).

  T1  SBL correctness   (a) on-grid noiseless atoms: exact support recovery;  (b) v == 0: L-cov == L-diag == standard SBL, bitwise
  T2  Gamma correctness (a) diag(Gamma) = sum(v) (1e-10), Hermitian, PSD;  (b) Monte Carlo of E[(B(x)-B(mu))^H (B(x)-B(mu))], x from the
                        per-symbol QPSK posterior implied by the LLRs (the one `moments` uses), 4000 samples: relative Frobenius error <= 5%
  T4  determinism       SBL twice -> bitwise equal; hard decision / candidate union / selection helpers
  TC  co-delay detector the frozen detector (scalar_joint / TimePathOps) is correct for paths that share a delay: B h equals Channel.apply,
                        the adjoint identity <A x, z> = <x, A^H z>, R = Gram of the modulations (zero across delays), power = h^H R h
  TG  grid              K = 2575, columns() equals the frozen _responses
  TE  equivalence       the optimised E-step (Cholesky + triangular inverse, trace identity) equals the textbook implementation (full inverse, explicit trace)
The context-level checks (dictionary convention against the noiseless P1 observation, T3, T4 on real frames) run in e3_driver.py --mode gate.
Usage: python test_e3.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e3_lib  # noqa: E402

e3_lib.prepare_paths()
import sbl_rx as sbl  # noqa: E402
from messages import alphabet, logprior, moments  # noqa: E402
from physical import Channel, daft  # noqa: E402
from twofft import TimePathOps  # noqa: E402

EXPERIMENTS = HERE.parent


def system_like(n):
    return 7.0 / (2 * n), 1.0 / (16 * n)


def qpsk_pilot(n, rng):
    return np.exp(2j * np.pi * rng.random(n)) * .5


# ----------------------------------------------------------------------------- T1
def t1_sbl_correctness():
    n = 128
    c1, c2 = system_like(n)
    rng = np.random.default_rng(11)
    delays_g = np.repeat(np.arange(12, dtype=np.int32), 9)
    nus_g = np.tile(np.arange(-2., 2.01, .5), 12)
    xt = daft(qpsk_pilot(n, rng) + (rng.choice([-1., 1.], n) + 1j * rng.choice([-1., 1.], n)) / 2, c1, c2, True)
    B = sbl.columns(xt, delays_g, nus_g, c1, c2)
    truth = [int(np.flatnonzero((delays_g == l) & (nus_g == nu))[0]) for l, nu in ((2, .5), (5, -1.0), (9, 1.5), (5, 0.5))]   # includes a co-delay pair
    g = (rng.normal(size=4) + 1j * rng.normal(size=4)) * .6
    Y = B[:, truth] @ g
    res = sbl.sbl_em(B, Y, beta0=1e6)
    idx, mu, _ = sbl.select_output(res['idx'], res['mu'])
    assert sorted(idx.tolist()) == sorted(truth), f'T1a: support {sorted(idx.tolist())} != {sorted(truth)}'
    err = float(np.max(np.abs(mu[np.argsort(idx)] - g[np.argsort(truth)]) / np.abs(g[np.argsort(truth)])))
    assert err < 1e-3, f'T1a: gain error {err}'
    # (b) v == 0 -> L-cov (full Gamma from the frozen _gamma_cross), L-diag (sum v I) and plain SBL are bitwise the same
    v = np.zeros(n)
    full = sbl.gamma_full(delays_g, nus_g, v, c1)
    runs = [sbl.sbl_em(B, Y + .01 * (rng.normal(size=n) + 1j * rng.normal(size=n)) * 0, beta0=100., Gamma=g_) for g_ in (None, float(v.sum()), full)]
    for r in runs[1:]:
        for key in ('idx', 'mu', 'gamma'):
            assert runs[0][key].tobytes() == r[key].tobytes(), f'T1b: {key} differs'
        assert runs[0]['beta'] == r['beta'] and runs[0]['iterations'] == r['iterations']
    # noisy version of (a)/(b): same equality with non-trivial noise
    Yn = Y + .05 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    runs = [sbl.sbl_em(B, Yn, beta0=100., Gamma=g_) for g_ in (None, 0.0, full)]
    assert all(runs[0]['mu'].tobytes() == r['mu'].tobytes() and runs[0]['idx'].tobytes() == r['idx'].tobytes() for r in runs[1:])
    # data-aided Gamma changes the answer when v > 0 (the variants are really different)
    v2 = .2 + .2 * rng.random(n)
    a = sbl.sbl_em(B, Yn, beta0=50., Gamma=float(v2.sum()))
    b = sbl.sbl_em(B, Yn, beta0=50., Gamma=sbl.gamma_full(delays_g, nus_g, v2, c1))
    assert a['mu'].tobytes() != b['mu'].tobytes() or a['idx'].tobytes() != b['idx'].tobytes()
    return dict(support_recovered=True, gain_rel_error=err, iterations=res['iterations'], converged=res['converged'], n_final=res['n_final'],
                v0_bitwise_equal_runs=3)


# ----------------------------------------------------------------------------- T2
def t2_gamma(samples=4000):
    n = 256
    c1, c2 = system_like(n)
    rng = np.random.default_rng(5)
    # candidate set with co-delay pairs, near-duplicates and different delays
    delays = np.array([3, 3, 3, 7, 7, 11, 20, 20, 33, 40, 40, 40, 41, 59, 60, 60])
    dopplers = np.array([.0, .25, 1.5, -1., -.75, 2., .5, .5 + .25, -2.5, 0., .1, 2.9, 1., -.5, .0, 1.75])
    L = rng.normal(0., 2.5, size=2 * n)
    pd = .5
    mu, v, _ = moments(L, pd)
    gam = sbl.gamma_full(delays, dopplers, v, c1)
    # (a) structure
    diag_err = float(np.max(np.abs(np.diag(gam).real - v.sum()) / v.sum()))
    imag_err = float(np.max(np.abs(np.diag(gam).imag)))
    herm = float(np.linalg.norm(gam - gam.conj().T) / np.linalg.norm(gam))
    eig = np.linalg.eigvalsh((gam + gam.conj().T) / 2)
    assert diag_err < 1e-10 and imag_err < 1e-10 * v.sum() and herm < 1e-10 and eig.min() > -1e-9 * eig.max(), (diag_err, herm, eig.min())
    # (b) Monte Carlo: x from the per-symbol QPSK posterior exp(logprior(L)) (the distribution moments() integrates)
    a, _ = alphabet(pd)
    p = np.exp(logprior(L, pd))
    cum = np.cumsum(p, axis=1)
    acc = np.zeros((len(delays), len(delays)), complex)
    for _ in range(samples):
        u = rng.random(n)[:, None]
        sym = np.minimum((u > cum).sum(axis=1), 3)
        x = a[sym]
        D = sbl.columns(daft(x - mu, c1, c2, True), delays, dopplers, c1, c2)    # B(x) - B(mu) by linearity of B in xt
        acc += D.conj().T @ D
    mc = acc / samples
    rel = float(np.linalg.norm(mc - gam) / np.linalg.norm(gam))
    off = ~np.eye(len(delays), dtype=bool)
    rel_off = float(np.linalg.norm((mc - gam)[off]) / np.linalg.norm(gam[off]))   # the cross terms alone (what separates L-cov from L-diag)
    assert rel <= .05, f'T2b: Monte Carlo relative Frobenius error {rel}'
    assert rel_off <= .15, f'T2b: Monte Carlo relative error of the off-diagonal part {rel_off}'
    # the sample mean / variance of the draws match moments(): sanity of the sampler itself
    u = np.random.default_rng(1).random((20000, n))
    sym = np.minimum((u[:, :, None] > cum[None]).sum(axis=2), 3)
    xs = a[sym]
    mean_err = float(np.max(np.abs(xs.mean(axis=0) - mu)))
    assert mean_err < .02, mean_err
    return dict(n=n, atoms=len(delays), samples=samples, diag_rel_error=diag_err, hermitian_rel=herm, min_eig_over_max=float(eig.min() / eig.max()),
                mc_rel_frobenius_error=rel, mc_rel_error_offdiagonal=rel_off, sampler_mean_abs_error=mean_err)


# ----------------------------------------------------------------------------- T4
def t4_determinism_and_helpers():
    n = 128
    c1, c2 = system_like(n)
    rng = np.random.default_rng(2)
    delays_g, nus_g = sbl.full_grid(20)
    xt = daft(qpsk_pilot(n, rng), c1, c2, True)
    sub = np.sort(rng.choice(len(delays_g), 60, replace=False))
    B = sbl.columns(xt, delays_g[sub], nus_g[sub], c1, c2)
    Y = B[:, :5] @ (rng.normal(size=5) + 1j * rng.normal(size=5)) + .05 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    v = .1 + .1 * rng.random(n)
    gam = sbl.gamma_full(delays_g[sub], nus_g[sub], v, c1)
    for G in (None, float(v.sum()), gam):
        r1, r2 = sbl.sbl_em(B, Y, beta0=30., Gamma=G), sbl.sbl_em(B, Y, beta0=30., Gamma=G)
        assert all(r1[k].tobytes() == r2[k].tobytes() for k in ('idx', 'mu', 'gamma')) and r1['beta'] == r2['beta'] and r1['sizes'] == r2['sizes']
    # max_iter: a problem that converges early is untouched by a larger cap (bitwise); a larger cap only adds iterations
    easy = sbl.sbl_em(B[:, :20], Y, beta0=30., max_iter=100)
    easy4 = sbl.sbl_em(B[:, :20], Y, beta0=30., max_iter=400)
    if easy['converged']:
        assert all(easy[k].tobytes() == easy4[k].tobytes() for k in ('idx', 'mu', 'gamma')) and easy['iterations'] == easy4['iterations']
    hard = sbl.sbl_em(B, Y, beta0=30., max_iter=5)
    hard2 = sbl.sbl_em(B, Y, beta0=30., max_iter=7)
    assert hard['iterations'] == 5 and hard2['iterations'] == 7 and not hard['converged']
    # selection: threshold, cap, at least one atom, energy order
    idx = np.arange(40)
    mu = np.zeros(40, complex)
    mu[:30] = np.linspace(1, .4, 30)
    mu[30:] = 1e-4
    i, m, e = sbl.select_output(idx, mu)
    assert len(i) == 24 and np.all(np.diff(e) <= 0) and i[0] == 0
    mu2 = np.zeros(5, complex)
    mu2[2] = 1.
    mu2[4] = 1e-3 * np.sqrt(.999) * .99      # |mu|^2 below 1e-3 of the total -> dropped
    assert list(sbl.select_output(np.arange(5), mu2)[0]) == [2]
    assert list(sbl.select_output(np.arange(3), np.zeros(3, complex))[0]) == [0]
    # candidate union: screened atoms plus the whole Doppler row of every retained delay
    top = np.array([5, 900, 2000])
    cand = sbl.candidate_union(top, [0, 77], np.repeat(np.arange(103, dtype=np.int32), 25))
    assert set(range(25)).issubset(cand) and set(range(77 * 25, 78 * 25)).issubset(cand) and {900, 2000}.issubset(cand) and len(cand) == 52 and np.all(np.diff(cand) > 0)
    # hard decision: nearest alphabet point, ties -> +
    mu_d = np.array([.1 + .2j, -.3 + .4j, .2 - .1j, -.1 - .1j, 0 + 0j, -0.0 + 1e-9j])
    h = sbl.hard_decision(mu_d, .5)
    a, _ = alphabet(.5)
    assert np.allclose(h, [.5 + .5j, -.5 + .5j, .5 - .5j, -.5 - .5j, .5 + .5j, .5 + .5j]) and all(np.min(np.abs(a - z)) < 1e-15 for z in h)
    pe = np.exp(logprior(np.concatenate([[8., -8.], [-8., 8.]]), .5))      # posterior (+,-) / (-,+): hard decision agrees with the argmax symbol
    mu_p, _, _ = moments(np.concatenate([[8., -8.], [-8., 8.]]), .5)
    assert np.allclose(sbl.hard_decision(mu_p, .5), a[np.argmax(pe, axis=1)])
    # |D_N|
    assert sbl.abs_dn(np.array([0.]), 1024)[0] == 1.0 and sbl.abs_dn(np.array([.55]), 1024)[0] >= .5 > sbl.abs_dn(np.array([.65]), 1024)[0]
    pairs = sbl.codelay_pairs([5, 5, 5, 9], [0., .25, 1.5, 0.], 1024, true_delays=[5, 9])
    assert len(pairs) == 3 and all(p['true_delay'] for p in pairs) and abs(pairs[0]['dnu'] - .25) < 1e-15
    return dict(variants_checked=3, selection_cases=3)


# ----------------------------------------------------------------------------- TC: the frozen detector with paths that share a delay
def tc_codelay_detector():
    n = 256
    c1, c2 = system_like(n)
    rng = np.random.default_rng(9)
    worst = dict(apply=0., adjoint=0., gram=0., power=0., cross_delay_zero=0.)
    for trial in range(6):
        delays = np.array([4, 4, 4, 9, 9, 17, 30])                       # triplet, doublet, singles
        dopplers = rng.uniform(-3, 3, len(delays))
        gains = (rng.normal(size=len(delays)) + 1j * rng.normal(size=len(delays))) / np.sqrt(2)
        ch = Channel(n, c1, c2, delays, dopplers, gains)
        ops = TimePathOps(ch)
        x = rng.normal(size=n) + 1j * rng.normal(size=n)
        xt = daft(x, c1, c2, True)
        # (1) B h == Channel.apply (independent per-path implementation), co-delay terms included
        B = ops.responses_time(xt)
        ref = ch.apply(x)
        worst['apply'] = max(worst['apply'], float(np.linalg.norm(daft(B @ gains, c1, c2) - ref) / np.linalg.norm(ref)))
        # (2) adjoint identity  <A_h xt, z> == <xt, A_h^H z>   with A_h xt = sum_p h_p phase_p xt[idx_p]
        h = (rng.normal(size=len(delays)) + 1j * rng.normal(size=len(delays)))
        z = rng.normal(size=n) + 1j * rng.normal(size=n)
        Ah = ops.responses_time(xt) @ h
        lhs = np.vdot(z, Ah)
        rhs = np.vdot(ops.adjoint_time(h, z), xt)
        worst['adjoint'] = max(worst['adjoint'], float(abs(lhs - rhs) / abs(lhs)))
        # (3) R = Gram of the time-domain modulations, zero across different delays
        k = np.arange(n)
        mod = np.exp(2j * np.pi * k[:, None] * dopplers[None, :] / n)
        gram = (mod.conj().T @ mod) / n * (delays[:, None] == delays[None, :])
        worst['gram'] = max(worst['gram'], float(np.max(np.abs(ops.R - gram))))
        worst['cross_delay_zero'] = max(worst['cross_delay_zero'], float(np.max(np.abs(ops.R[delays[:, None] != delays[None, :]]))))
        # (4) physical power  h^H R h == (1/N) sum_delay || sum_{p at delay} h_p m_p ||^2
        direct = sum(np.sum(np.abs(mod[:, delays == l] @ h[delays == l]) ** 2) for l in np.unique(delays)) / n
        worst['power'] = max(worst['power'], float(abs(ops.power(h) - direct) / direct))
    assert all(v < 1e-12 for v in worst.values()), worst
    # the full detector runs on a co-delay channel (fixed gains) and is deterministic
    from twofft import scalar_joint
    pilot = qpsk_pilot(n, rng)
    ch = Channel(n, c1, c2, [4, 4, 9], [.25, -1., 0.5], [.7, .3j, .5])
    y = ch.apply(pilot + (rng.choice([-1., 1.], n) + 1j * rng.choice([-1., 1.], n)) / 2) + .05 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    o1 = scalar_joint(y, pilot, ch, .005, pd=.5, prior=None, iterations=20, damping=.3, gain_mode='fixed')
    o2 = scalar_joint(y, pilot, ch, .005, pd=.5, prior=None, iterations=20, damping=.3, gain_mode='fixed')
    assert np.isfinite(o1['extrinsic']).all() and o1['extrinsic'].tobytes() == o2['extrinsic'].tobytes() and np.array_equal(o1['gains'], ch.gains)
    return worst


# ----------------------------------------------------------------------------- TG
def tg_grid():
    delays, dopplers = sbl.full_grid(102)
    assert len(delays) == 2575 and delays.dtype == np.int32 and dopplers.min() == -3. and dopplers.max() == 3.
    assert np.array_equal(np.unique(dopplers), np.arange(-3., 3.01, .25)) and np.array_equal(np.unique(delays), np.arange(103))
    n = 128
    c1, c2 = system_like(n)
    rng = np.random.default_rng(4)
    xt = daft(qpsk_pilot(n, rng), c1, c2, True)
    pick = np.array([0, 24, 25, 1300, 2574])
    cols = sbl.columns(xt, delays[pick], dopplers[pick], c1, c2, chunk=2)
    for j, k in enumerate(pick):
        ref = TimePathOps(Channel(n, c1, c2, [int(delays[k]) % n], [float(dopplers[k])], [1.0])).responses_time(xt)[:, 0]
        assert cols[:, j].tobytes() == ref.tobytes() or np.max(np.abs(cols[:, j] - ref)) < 1e-14
    return dict(K=len(delays))



# ----------------------------------------------------------------------------- TE: the optimised E-step equals the textbook implementation
def sbl_em_reference(B, Y, beta0, Gamma=None, gamma0=sbl.GAMMA0, max_iter=sbl.MAX_ITER, tol=sbl.TOL, prune=sbl.PRUNE):
    """Textbook EM-SBL (design section 2 formulas written out literally: full inverse, explicit tr((B^H B + Gamma) Sigma))."""
    import scipy.linalg as sla
    n, m = B.shape
    Gam = np.zeros((m, m), complex) if Gamma is None else (float(Gamma) * np.eye(m, dtype=complex) if np.isscalar(Gamma) else (Gamma + Gamma.conj().T) / 2)
    G = B.conj().T @ B
    G = (G + G.conj().T) / 2
    Gt = G + Gam
    by = B.conj().T @ Y
    idx = np.arange(m)
    Ba, Gta, Gama, bya = B, Gt, Gam, by
    gam, beta = np.full(m, float(gamma0)), float(beta0)
    for it in range(1, max_iter + 1):
        a = Ba.shape[1]
        A = (lambda x: (x + x.conj().T) / 2)(beta * Gta + np.diag(1.0 / gam))
        Sigma = (lambda x: (x + x.conj().T) / 2)(np.linalg.inv(A))
        mu = beta * (Sigma @ bya)
        r = Y - Ba @ mu
        beta_new = n / (float(np.vdot(r, r).real) + float(np.vdot(mu, Gama @ mu).real) + float(np.trace(Gta @ Sigma).real))
        gam_new = np.abs(mu) ** 2 + Sigma.diagonal().real
        rel = float(np.linalg.norm(gam_new - gam) / np.linalg.norm(gam))
        gam, beta = gam_new, beta_new
        keep = gam >= prune * gam.max()
        if not keep.all():
            sel = np.flatnonzero(keep)
            idx, gam, Ba, bya, Gta, Gama = idx[sel], gam[sel], Ba[:, sel], bya[sel], Gta[np.ix_(sel, sel)], Gama[np.ix_(sel, sel)]
        if rel < tol:
            break
    A = (lambda x: (x + x.conj().T) / 2)(beta * Gta + np.diag(1.0 / gam))
    return dict(idx=idx, mu=beta * np.linalg.solve(A, bya), gamma=gam, beta=beta, iterations=it)


def te_equals_reference():
    n = 128
    c1, c2 = system_like(n)
    rng = np.random.default_rng(21)
    delays_g, nus_g = sbl.full_grid(30)
    xt = daft(qpsk_pilot(n, rng) + (rng.choice([-1., 1.], n) + 1j * rng.choice([-1., 1.], n)) / 2, c1, c2, True)
    sub = np.sort(rng.choice(len(delays_g), 150, replace=False))
    B = sbl.columns(xt, delays_g[sub], nus_g[sub], c1, c2)
    Y = B[:, [3, 40, 77, 100]] @ ((rng.normal(size=4) + 1j * rng.normal(size=4)) * .6) + .03 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    v = .05 + .3 * rng.random(n)
    worst = dict(mu=0., beta=0., gamma=0.)
    for G in (None, float(v.sum()), sbl.gamma_full(delays_g[sub], nus_g[sub], v, c1)):
        for max_iter in (8, 100):
            a = sbl.sbl_em(B, Y, beta0=40., Gamma=G, max_iter=max_iter)
            b = sbl_em_reference(B, Y, beta0=40., Gamma=G, max_iter=max_iter)
            assert np.array_equal(a['idx'], b['idx']) and a['iterations'] == b['iterations'], 'TE: active set / iteration count differ'
            worst['mu'] = max(worst['mu'], float(np.max(np.abs(a['mu'] - b['mu'])) / np.max(np.abs(b['mu']))))
            worst['beta'] = max(worst['beta'], abs(a['beta'] - b['beta']) / b['beta'])
            worst['gamma'] = max(worst['gamma'], float(np.max(np.abs(a['gamma'] - b['gamma']) / b['gamma'])))
    assert all(x < 1e-8 for x in worst.values()), worst
    return worst


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--out', type=Path, default=HERE / 'out' / 'unit')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    result = dict(note='numpy-only unit gates; context-level T3 and real-frame checks are in e3_driver.py --mode gate')
    t0 = time.perf_counter()
    for name, fn in (('T1_sbl_correctness', t1_sbl_correctness), ('T2_gamma', t2_gamma), ('T4_determinism_helpers', t4_determinism_and_helpers),
                     ('TC_codelay_detector', tc_codelay_detector), ('TG_grid', tg_grid), ('TE_equals_textbook', te_equals_reference)):
        s = time.perf_counter()
        out = fn()
        out = dict(out) if isinstance(out, dict) else dict(value=out)
        out['seconds'] = time.perf_counter() - s
        result[name] = out
        print(f'{name}: PASS ({out["seconds"]:.1f}s)', flush=True)
    result['all_pass'] = True
    result['total_seconds'] = time.perf_counter() - t0
    (a.out / 'test_e3.json').write_text(json.dumps(result, indent=1, default=str) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k in ('T1_sbl_correctness', 'T2_gamma', 'TC_codelay_detector')}, indent=1, default=str))
    print('ALL PASS')


if __name__ == '__main__':
    main()
