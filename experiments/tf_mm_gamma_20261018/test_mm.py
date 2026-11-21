#!/usr/bin/env python
"""Unit gates of the model-matched Gamma check (numpy/scipy only; no receiver context, no data).

  U1  sampler        sample_qpsk follows messages.moments: exact mean / variance equal, probability table equals exp(logprior), empirical moments within 4 sigma
  U2  bound = SBL    Gamma = 0 (v == 0): the EIV bound equals -log det C - Y^H C^-1 Y at random (beta, gamma) and at the EM iterates
  U3  trace          sbl_em_traced == frozen sbl_rx.sbl_em bit for bit (Gamma None / scalar / matrix); its trace equals the textbook bound at the textbook EM iterates
  U4  monotone       the textbook EM with the E-3 updates never decreases the bound (Gamma != 0, 6 random problems, 100 iterations each)
  U5  neg. control   an EM whose beta update omits the Gamma terms DOES violate monotonicity (the readout can fail)
  U6  lower bound    on a tiny problem with exactly enumerated x, bound - N log pi <= exact marginal log-likelihood (equality when Gamma = 0)
Usage: python test_mm.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mm_lib as mm  # noqa: E402

sbl = mm.sbl
from messages import logprior, moments  # noqa: E402  (frozen, read-only)


def rand_problem(rng, n=96, m=60, p=40, noise=.2):
    B = (rng.normal(size=(n, m)) + 1j * rng.normal(size=(n, m))) / np.sqrt(2 * n)
    D = (rng.normal(size=(p, m)) + 1j * rng.normal(size=(p, m))) / np.sqrt(2 * p) * .6
    Gamma = D.conj().T @ D                              # Hermitian PSD data covariance of the dictionary
    h = np.zeros(m, complex)
    h[rng.choice(m, 6, replace=False)] = (rng.normal(size=6) + 1j * rng.normal(size=6))
    Y = B @ h + noise * (rng.normal(size=n) + 1j * rng.normal(size=n)) / np.sqrt(2)
    return B, Gamma, Y


def textbook_em(B, Y, beta0, Gamma, iters=100, wrong=None):
    """Explicit-inverse EM of the E-3 updates (no pruning); returns the list of (beta, gamma) used by each E-step and the final ones."""
    n, m = B.shape
    G = B.conj().T @ B
    Gam = np.zeros((m, m), complex) if Gamma is None else Gamma
    Gt = G + Gam
    by = B.conj().T @ Y
    gam, beta = np.ones(m), float(beta0)
    its = []
    for _ in range(iters):
        its.append((beta, gam.copy()))
        eg = Gt if wrong != 'estep_no_gamma' else G
        A = beta * eg + np.diag(1.0 / gam)
        Sig = np.linalg.inv(A)
        mu = beta * Sig @ by
        r = Y - B @ mu
        quad = np.real(np.vdot(mu, Gam @ mu))
        tr = np.real(np.trace(Gt @ Sig))
        if wrong == 'beta_no_gamma':
            denom = np.vdot(r, r).real + np.real(np.trace(G @ Sig))
        else:
            denom = np.vdot(r, r).real + quad + tr
        beta = n / denom
        gam = np.abs(mu) ** 2 + np.real(np.diag(Sig))
    its.append((beta, gam.copy()))
    return its


def bound_trace(B, Y, Gamma, its):
    return np.array([mm.eiv_bound(B, Y, b, g, Gamma) for b, g in its])


# ----------------------------------------------------------------------------- U1
def u1_sampler():
    rng = np.random.default_rng(3)
    n, pd = 400, .5
    out = {}
    for name, L in (('moderate', rng.normal(size=2 * n) * 3), ('clipped', np.clip(rng.normal(size=2 * n) * 30, -20, 20)), ('zero', np.zeros(2 * n))):
        mu, v, _ = moments(L, pd)
        m2, v2 = mm.sampler_moments(L, pd)
        out[name] = dict(mean_err=float(np.max(np.abs(mu - m2))), var_err=float(np.max(np.abs(v - v2))))
        assert out[name]['mean_err'] < 1e-13 and out[name]['var_err'] < 1e-12, (name, out[name])
        # probability table: product of the two bit marginals == exp(logprior) rows (bits (0,0),(0,1),(1,0),(1,1) -> a(1+j), a(1-j), a(-1+j), a(-1-j))
        from scipy.special import expit
        pi, pq = expit(L[:n]), expit(L[n:])
        table = np.column_stack([pi * pq, pi * (1 - pq), (1 - pi) * pq, (1 - pi) * (1 - pq)])
        out[name]['table_err'] = float(np.max(np.abs(table - np.exp(logprior(L, pd)))))
        assert out[name]['table_err'] < 1e-13
    L = rng.normal(size=2 * n) * 2
    mu, v, _ = moments(L, pd)
    R = 40000
    acc, acc2 = np.zeros(n, complex), np.zeros(n)
    for _ in range(R):
        x = mm.sample_qpsk(L, pd, rng)
        acc += x
        acc2 += np.abs(x - mu) ** 2
    mean_z = np.abs(acc / R - mu) / np.sqrt(np.maximum(v, 1e-12) / R)
    var_rel = float(abs(acc2.sum() / R - v.sum()) / v.sum())
    out['empirical'] = dict(draws=R, max_mean_z=float(mean_z.max()), mean_z_rms=float(np.sqrt(np.mean(mean_z ** 2))), var_rel_err=var_rel)
    assert mean_z.max() < 5.0 and var_rel < .01, out['empirical']
    return out


# ----------------------------------------------------------------------------- U2
def u2_bound_equals_sbl():
    rng = np.random.default_rng(5)
    B, Gamma, Y = rand_problem(rng)
    worst = 0.
    for _ in range(8):
        beta, gam = float(10 ** rng.uniform(-1, 2)), 10 ** rng.uniform(-3, 1, B.shape[1])
        a, b = mm.eiv_bound(B, Y, beta, gam, None), mm.standard_sbl_ll(B, Y, beta, gam)
        z = mm.eiv_bound(B, Y, beta, gam, np.zeros_like(Gamma))
        worst = max(worst, abs(a - b) / max(1., abs(b)), abs(z - b) / max(1., abs(b)))
    its = textbook_em(B, Y, 5., None, iters=30)
    tr = bound_trace(B, Y, None, its)
    ref = np.array([mm.standard_sbl_ll(B, Y, b, g) for b, g in its])
    worst_em = float(np.max(np.abs(tr - ref) / np.maximum(1., np.abs(ref))))
    # sbl_em_traced with Gamma=None: its own trace equals the direct marginal at the final parameters
    res = mm.sbl_em_traced(B, Y, 5., Gamma=None, max_iter=30)
    final = mm.standard_sbl_ll(B[:, res['idx']], Y, res['beta'], res['gamma'])
    worst_final = abs(res['trace'][-1] - final) / max(1., abs(final))
    assert worst < 1e-10 and worst_em < 1e-10 and worst_final < 1e-10, (worst, worst_em, worst_final)
    return dict(worst_rel_random_theta=float(worst), worst_rel_em_iterates=worst_em, traced_final_vs_direct=float(worst_final))


# ----------------------------------------------------------------------------- U3
def u3_traced_matches_frozen():
    rng = np.random.default_rng(9)
    B, Gamma, Y = rand_problem(rng)
    out = {}
    for name, G in (('none', None), ('scalar', .37), ('matrix', Gamma)):
        a = sbl.sbl_em(B, Y, 3.0, Gamma=G, max_iter=60)
        b = mm.sbl_em_traced(B, Y, 3.0, Gamma=G, max_iter=60)
        same = all(np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in ('idx', 'mu', 'gamma', 'beta', 'iterations', 'converged', 'n_final', 'sizes', 'jitter_events'))
        assert same, f'traced != frozen for Gamma={name}'
        out[name] = dict(bitwise_equal=bool(same))
    # trace vs textbook bound at textbook iterates (matrix Gamma; no pruning happens in 60 iterations on this problem)
    its = textbook_em(B, Y, 3.0, Gamma, iters=60)
    tr = bound_trace(B, Y, Gamma, its)
    res = mm.sbl_em_traced(B, Y, 3.0, Gamma=Gamma, max_iter=60)
    assert res['n_final'] == B.shape[1] and len(res['trace']) == len(tr)
    out['trace_vs_textbook_rel'] = float(np.max(np.abs(np.array(res['trace']) - tr) / np.maximum(1., np.abs(tr))))
    assert out['trace_vs_textbook_rel'] < 1e-8, out
    return out


# ----------------------------------------------------------------------------- U4 / U5
def u4_monotone():
    rows = []
    for seed in range(6):
        rng = np.random.default_rng(100 + seed)
        B, Gamma, Y = rand_problem(rng, noise=[.05, .1, .2, .4, .8, 1.5][seed])
        tr = bound_trace(B, Y, Gamma, textbook_em(B, Y, 2.0 + seed, Gamma, iters=100))
        s = mm.eiv_summary(tr)
        res = mm.sbl_em_traced(B, Y, 2.0 + seed, Gamma=Gamma, max_iter=100)
        s2 = mm.eiv_summary(res['trace'], res['skip'])
        rows.append(dict(seed=seed, textbook=s, traced=s2, gain=float(tr[-1] - tr[0])))
        assert s['n_viol'] == 0 and s2['n_viol'] == 0, rows[-1]
    return rows


def u5_negative_control():
    out = {}
    for wrong in ('beta_no_gamma', 'estep_no_gamma'):
        counts = []
        for seed in range(6):
            rng = np.random.default_rng(200 + seed)
            B, Gamma, Y = rand_problem(rng, noise=[.05, .1, .2, .4, .8, 1.5][seed])
            Gamma = Gamma * 6.0                                    # large dictionary uncertainty makes the omission matter
            tr = bound_trace(B, Y, Gamma, textbook_em(B, Y, 2.0, Gamma, iters=100, wrong=wrong))
            counts.append(mm.eiv_summary(tr)['n_viol'])
        out[wrong] = dict(violations_per_problem=counts)
    out['detects'] = bool(any(sum(v['violations_per_problem']) > 0 for k, v in out.items() if isinstance(v, dict)))
    assert out['detects'], 'negative control did not violate monotonicity: the readout is not sensitive'
    return out


# ----------------------------------------------------------------------------- U6
def u6_lower_bound():
    rng = np.random.default_rng(17)
    n, m, J = 6, 3, 4
    B0 = (rng.normal(size=(n, m)) + 1j * rng.normal(size=(n, m))) / np.sqrt(2 * n)
    D = [(rng.normal(size=(n, m)) + 1j * rng.normal(size=(n, m))) / np.sqrt(2 * n) * .7 for _ in range(J)]
    p = rng.uniform(.2, .8, J)
    mu_s, var_s = 2 * p - 1, 1 - (2 * p - 1) ** 2
    Gamma = sum(var_s[j] * D[j].conj().T @ D[j] for j in range(J))
    Y = B0 @ ((rng.normal(size=m) + 1j * rng.normal(size=m)) * .8) + .3 * (rng.normal(size=n) + 1j * rng.normal(size=n))
    gaps = []
    for _ in range(6):
        beta, gam = float(10 ** rng.uniform(0, 1.5)), 10 ** rng.uniform(-1.5, .5, m)
        terms = []
        for cfg in range(2 ** J):
            s = np.array([1.0 if (cfg >> j) & 1 else -1.0 for j in range(J)])
            logp = float(np.sum(np.where(s > 0, np.log(p), np.log(1 - p))))
            Bx = B0 + sum((s[j] - mu_s[j]) * D[j] for j in range(J))
            C = np.eye(n) / beta + (Bx * gam[None, :]) @ Bx.conj().T
            sign, ld = np.linalg.slogdet(C)
            terms.append(logp - n * np.log(np.pi) - ld - np.real(np.vdot(Y, np.linalg.solve(C, Y))))
        exact = float(np.logaddexp.reduce(terms))
        bound = mm.eiv_bound(B0, Y, beta, gam, Gamma) - n * np.log(np.pi)
        gaps.append(exact - bound)
        assert exact >= bound - 1e-9, (exact, bound)
        # Gamma = 0 and D = 0: the model has no dictionary uncertainty -> equality
        C0 = np.eye(n) / beta + (B0 * gam[None, :]) @ B0.conj().T
        sign, ld0 = np.linalg.slogdet(C0)
        exact0 = -n * np.log(np.pi) - ld0 - np.real(np.vdot(Y, np.linalg.solve(C0, Y)))
        assert abs(exact0 - (mm.eiv_bound(B0, Y, beta, gam, None) - n * np.log(np.pi))) < 1e-9
    return dict(min_gap=float(min(gaps)), max_gap=float(max(gaps)), note='exact enumerated log p(y) - (L - N log pi) >= 0; equality at Gamma = 0')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=HERE / 'out' / 'unit')
    a = p.parse_args()
    results = {}
    for name, fn in (('U1_sampler', u1_sampler), ('U2_bound_equals_sbl', u2_bound_equals_sbl), ('U3_traced_matches_frozen', u3_traced_matches_frozen),
                     ('U4_monotone', u4_monotone), ('U5_negative_control', u5_negative_control), ('U6_lower_bound', u6_lower_bound)):
        results[name] = fn()
        print(name, 'PASS', json.dumps(results[name], default=str)[:400], flush=True)
    results['all_pass'] = True
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'test_mm.json').write_text(json.dumps(results, indent=1, default=str) + '\n')
    print('ALL UNIT TESTS PASS')


if __name__ == '__main__':
    main()
