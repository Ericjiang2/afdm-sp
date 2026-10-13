#!/usr/bin/env python
"""F2 supplement driver: adds the NESTED order-2 oracle O2n to driver_f2 (which stays byte-unchanged).

Why: the specified grid nu_bar + (k-(D-1)/2)*1.0 puts NO grid point at the centroid for even D (D=2 -> +-0.5 bin),
so O2 can be much WORSE than O1 for narrow clusters (single ray: 19% operator misfit) and the ladder 1,2,3,5 is not nested.
O2n = {nu_bar, nu_bar + s} with s in {+1,-1} chosen per tap by the smaller LS residual (oracle choice):
O1 subset O2n subset O3 subset O5 (all 1-bin-spaced, orthogonal), so misfit is monotone non-increasing in D.
Same detector (fixed-H TF20R2), same rows schema as driver_f2 (arm name 'O2n', oracle_order '2n').
"""
from __future__ import annotations

import sys
import time

import numpy as np

import driver as base
import driver_f2 as f2
import orders

_orig_run_oracle = f2.run_oracle
_orig_load_context = f2.load_context


def nested2_paths(delays, dopplers, gains, n):
    ls, nus, gs = [], [], []
    num = den = 0.
    for d, (nu, g) in sorted(orders.tap_groups(delays, dopplers, gains).items()):
        a = orders.tap_sequence(nu, g, n)
        nb = orders.centroid(nu, g)
        best = None
        for s in (1., -1.):
            c, resid = orders.lstsq_gains(a, [nb, nb + s], n)
            if best is None or resid < best[1]:
                best = (c, resid, [nb, nb + s])
        ls += [d, d]
        nus += best[2]
        gs += list(best[0])
        num += best[1]
        den += float(np.vdot(a, a).real)
    return np.array(ls, int), np.array(nus, float), np.array(gs, complex), num / den


def run_oracle(ctx, obs, truth, order):
    if order != '2n':
        return _orig_run_oracle(ctx, obs, truth, order)
    n = len(obs['y'])
    ls, nus, gs, misfit = nested2_paths(truth['l_i'], truth['k_real'], truth['g_i'], n)
    channel = ctx.Channel(n, ctx.system.c1, ctx.system.c2, ls, nus, gs)
    start = time.perf_counter()
    result = ctx.wrappers.run_fixed_channel(obs, ctx.system, ctx.code, ctx.native, channel=channel, detector='tf')
    seconds = time.perf_counter() - start
    d = result.decoder
    return [dict(arm='O2n', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']),
                 seconds=seconds, triggered=None, misfit=float(misfit), oracle_order='2n',
                 oracle_n_paths=int(len(ls)), oracle_paths=(ls, nus, gs))]


def load_context(args):
    ctx = _orig_load_context(args)
    ctx.sources['driver_f2s.py'] = base.sha256_file(f2.HERE / 'driver_f2s.py')
    return ctx


f2.F2_ARMS = f2.F2_ARMS + ('O2n',)
f2.ORACLE_ORDER['O2n'] = '2n'
f2.F2_SPEC['oracle_nested2'] = 'O2n: grid {nu_bar, nu_bar+s}, s=+-1 chosen per tap by smaller LS residual'
f2.run_oracle = run_oracle
f2.load_context = load_context

if __name__ == '__main__':
    f2.main(sys.argv[1:])
