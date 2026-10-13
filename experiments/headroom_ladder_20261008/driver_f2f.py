#!/usr/bin/env python
"""F2 supplement driver: free-frequency D-exponential per-tap oracle OF_D (orders_free.py) on top of driver_f2
(which stays byte-unchanged).  Same detector (fixed-H TF20R2) and row schema as O_D; arm names 'OF2', 'OF3'.
Why: the specified 1-bin lattice O_D converges only ~1/D (Dirichlet leakage of off-lattice rays), so it overstates the
intrinsic per-tap order; OF_D asks "does ANY D-exponential tap representation reach A3?" (oracle frequencies).
"""
from __future__ import annotations

import sys
import time

import driver as base
import driver_f2 as f2
import orders_free

_orig_run_oracle = f2.run_oracle
_orig_load_context = f2.load_context


def run_oracle(ctx, obs, truth, order):
    if not (isinstance(order, str) and order.startswith('f')):
        return _orig_run_oracle(ctx, obs, truth, order)
    D = int(order[1:])
    n = len(obs['y'])
    ls, nus, gs, misfit = orders_free.free_paths(truth['l_i'], truth['k_real'], truth['g_i'], D, n)
    channel = ctx.Channel(n, ctx.system.c1, ctx.system.c2, ls, nus, gs)
    start = time.perf_counter()
    result = ctx.wrappers.run_fixed_channel(obs, ctx.system, ctx.code, ctx.native, channel=channel, detector='tf')
    seconds = time.perf_counter() - start
    d = result.decoder
    return [dict(arm=f'OF{D}', decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']),
                 seconds=seconds, triggered=None, misfit=float(misfit), oracle_order=order,
                 oracle_n_paths=int(len(ls)), oracle_paths=(ls, nus, gs), max_abs_gain=float(abs(gs).max()))]


def load_context(args):
    ctx = _orig_load_context(args)
    ctx.sources['driver_f2f.py'] = base.sha256_file(f2.HERE / 'driver_f2f.py')
    ctx.sources['orders_free.py'] = base.sha256_file(f2.HERE / 'orders_free.py')
    return ctx


f2.F2_ARMS = f2.F2_ARMS + ('OF2', 'OF3')
f2.ORACLE_ORDER.update({'OF2': 'f2', 'OF3': 'f3'})
f2.F2_SPEC['oracle_free'] = 'OF_D: D free-frequency exponentials per tap (orders_free.py), LS gains; D>=R -> true rays'
f2.run_oracle = run_oracle
f2.load_context = load_context

if __name__ == '__main__':
    f2.main(sys.argv[1:])
