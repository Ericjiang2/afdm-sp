#!/usr/bin/env python
"""Implementation check for zheng_rx.py (done once, before reporting a gate failure): the vectorised Algorithm 1 against a per-edge loop
implementation written directly from eqs. (18), (20)-(33) (dense H_eff for the neighbour sets), N = 64, modes 'perfect' and 'prop'.
Also the formula audit of zheng_rx (closed form vs eq. 9, eq. 5 vs the time-domain model).  Writes out/zheng_gates/impl_check.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from zheng_rx import Zheng  # noqa: E402


def naive(z, y, M, sp2, sd2, mode, grid, h, sigma2=1.):
    N, P, Kp = z.N, z.P, z.Mp
    a = np.sqrt(sd2) * z.qpsk
    xp, Xp, Ginv = z.pilot_matrix(M, sp2)
    dense = {}
    xi = lambda g: dense.setdefault(g, z.xi_dense(g))  # noqa: E731
    pjc, pj = {}, np.full((N, 4), .25)
    ind_prev, zeta_star, prev = None, 0., None
    for i in range(1, z.i_max + 1):
        xbar = pj @ a                                                           # eq. (18)
        if mode == 'prop':
            ic = np.zeros(N, complex) if prev is None else sum(g * (xi(idx) @ xbar) for idx, g in zip(*prev))
            hh = Ginv @ (Xp.conj().T @ (y - ic))                                # eq. (20)
        else:
            hh = np.zeros(Kp, complex)
            hh[grid] = h
        ind = tuple(sorted(np.argsort(-np.abs(hh), kind='stable')[:P])) if mode == 'prop' else tuple(sorted(grid))   # eq. (21)
        if ind != ind_prev:
            pjc = {}
        gains = hh[list(ind)]
        prev = (list(ind), gains)
        Heff = sum(g * xi(idx) for idx, g in zip(ind, gains))                   # eq. (22)
        yd = y - Heff @ xp                                                      # eq. (24)
        I = [np.flatnonzero(np.abs(Heff[c]) > 0) for c in range(N)]
        J = [np.flatnonzero(np.abs(Heff[:, j]) > 0) for j in range(N)]
        msg = lambda j, c: pjc.get((j, c), np.full(4, .25))  # noqa: E731
        mu, var = {}, {}
        for c in range(N):
            for j in I[c]:
                m, v = 0j, 0.
                for e in I[c]:
                    if e == j:
                        continue
                    pe, H = msg(e, c), Heff[c, e]
                    m += np.sum(pe * a) * H                                      # eq. (25)
                    v += np.sum(pe * np.abs(a * H) ** 2) - abs(np.sum(pe * a * H)) ** 2   # eq. (26)
                mu[(c, j)], var[(c, j)] = m, v + sigma2
        newm, ptilde = {}, np.zeros((N, 4))
        for j in range(N):
            logphi = {e: -np.abs(yd[e] - mu[(e, j)] - Heff[e, j] * a) ** 2 / var[(e, j)] for e in J[j]}   # eq. (28)
            tot = sum(logphi.values())
            for c in J[j]:
                q = sum(logphi[e] for e in J[j] if e != c)                       # eq. (27)
                q = np.exp(q - q.max())
                q /= q.sum()
                newm[(j, c)] = (1 - z.delta) * msg(j, c) + z.delta * q           # eq. (29)
            q = np.exp(tot - tot.max())                                          # eq. (30)
            ptilde[j] = q / q.sum()
        pjc = newm
        zeta = float(np.mean(1 - ptilde.max(axis=1) < z.eps))                    # eq. (31)
        before = zeta_star
        if zeta > before:
            pj = ptilde                                                          # eq. (32)
        zeta_star = max(zeta_star, zeta)
        ind_prev = ind
        if before - zeta > z.gamma or zeta == 1.:
            break
    return pj, i, zeta_star


def main():
    z = Zheng(N=64)
    rng = np.random.default_rng(3)
    rows = []
    for mode in ('perfect', 'prop'):
        for trial in range(4):
            al = rng.integers(-1, 2, 3)
            grid = [z.grid_index(i, int(al[i])) for i in range(3)]
            h = (rng.standard_normal(3) + 1j * rng.standard_normal(3)) / np.sqrt(6)
            bits = rng.integers(0, 2, 2 * z.N)
            sd2, sp2 = 10 ** 1.4, 10 ** 5
            x = z.pilot(2, sp2) + z.modulate(bits, sd2)
            y = z.heff_apply(x, grid, h) + (rng.standard_normal(z.N) + 1j * rng.standard_normal(z.N)) / np.sqrt(2)
            fast = z.run(y, 2, sp2, sd2, mode=mode, true_grid=grid, true_gains=h)
            pj, it, zs = naive(z, y, 2, sp2, sd2, mode, grid, h)
            rows.append(dict(mode=mode, trial=trial, iterations_fast=fast['iterations'], iterations_naive=it, zeta_fast=fast['zeta_star'], zeta_naive=zs,
                             max_abs_p_j_difference=float(np.abs(fast['p_j'] - pj).max())))
    payload = dict(_argv=sys.argv[:], code_md5=dict(zheng_rx=hashlib.md5((HERE / 'zheng_rx.py').read_bytes()).hexdigest(),
                                                   zheng_check=hashlib.md5((HERE / 'zheng_check.py').read_bytes()).hexdigest()),
                   audit=Zheng().audit(np.random.default_rng(0)), rows=rows,
                   worst_p_j_difference=max(r['max_abs_p_j_difference'] for r in rows),
                   iterations_identical=all(r['iterations_fast'] == r['iterations_naive'] for r in rows))
    out = HERE / 'out' / 'zheng_gates'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'impl_check.json').write_text(json.dumps(payload, indent=1, default=float) + '\n')
    print('worst |p_j diff|', payload['worst_p_j_difference'], 'iterations identical', payload['iterations_identical'], payload['audit'])


if __name__ == '__main__':
    main()
