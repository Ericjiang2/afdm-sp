#!/usr/bin/env python
"""M1 DPSS oracle ladder driver (task 10-08-doppler-cluster, design.md Stage M1 item 2).  Wraps driver_f2.py (unchanged).

Arms (rows pair bit-for-bit with F2 A3 at the same (config, snr, frame): same generator, entropy, CL_DOMAIN)
  P1 P2 P3 P4 P6 P8   true delays; each tap replaced by its projection onto the first D modulated DPSS around the
                      power-weighted ray centroid, W = max_r|nu_r - c| + 0.5 bins (dpss_taps.py).  Detection = fixed-H
                      TF20R2 (interventions.run_fixed_channel(detector='tf')), the A3/O/OF detector, with the channel
                      supplied as a GENERAL-TAP operator (tapchannel.TapChannel; realization exact, no exponential set).
                      P8 is an extension beyond the specified ladder {1,2,3,4,6}.
  GX                  exact true tap sequences through the same general-tap operator (equivalence check vs A3; run only
                      on frames with frame % 20 == 0).
Nothing frozen is edited; the general-tap hook is a run-time subclass of twofft.TimePathOps (tapchannel.install_general_taps).
Run one process per shard, single thread (launch_m1.sh).
"""
from __future__ import annotations

import hashlib
import sys
import time
import traceback

import numpy as np

import driver as base
import driver_f2 as f2
import dpss_taps
import tapchannel

ORDER_ARMS = {'P1': 1, 'P2': 2, 'P3': 3, 'P4': 4, 'P6': 6, 'P8': 8}
M1_ARMS = tuple(ORDER_ARMS) + ('GX',)
SPOT_EVERY = 20

_orig_cell = f2.run_cell_f2
_orig_load_context = f2.load_context
_cache = {}


def projected(truth, n, orders_list):
    key = (truth['cluster']['config'], truth['channel_seed'], tuple(orders_list))
    if key not in _cache:
        if len(_cache) > 64:
            _cache.clear()
        _cache[key] = dpss_taps.project_taps(truth['l_i'], truth['k_real'], truth['g_i'], orders_list, n)
    return _cache[key]


def run_arm(ctx, obs, truth, arm):
    n = len(obs['y'])
    s = ctx.system
    p = projected(truth, n, dpss_taps.D_LADDER + (8,))
    if arm == 'GX':
        taps, misfit, extra = p['exact_taps'], 0., dict(dpss_order=None)
    else:
        D = ORDER_ARMS[arm]
        taps, misfit = p['by_order'][D]['taps'], p['by_order'][D]['misfit']
        extra = dict(dpss_order=D, dpss_tap_misfit=p['by_order'][D]['tap_misfit'])
    extra.update(dpss_W=[float(x) for x in p['W']], dpss_halfspread=[float(x) for x in p['halfspread']],
                 dpss_centroid=[float(x) for x in p['centroid']], dpss_W_max=float(p['W'].max()))
    channel = tapchannel.make_tap_channel(n, s.c1, s.c2, p['delays'], taps)
    start = time.perf_counter()
    result = ctx.wrappers.run_fixed_channel(obs, s, ctx.code, ctx.native, channel=channel, detector='tf')
    seconds = time.perf_counter() - start
    d = result.decoder
    return dict(arm=arm, decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, misfit=float(misfit), oracle_n_paths=int(channel.p), channel=channel, extra=extra)


def explicit_misfit_taps(ctx, truth, channel):
    s = ctx.system
    n, prefix = int(s.N_total), int(s.l_max_cap)
    ht = ctx.physical_channel_matrix(n, s.c1, s.c2, truth['l_i'], truth['k_real'], truth['g_i'], prefix_length=prefix)
    ha = tapchannel.tap_matrix(channel)
    return float(np.linalg.norm(ht - ha) ** 2 / np.linalg.norm(ht) ** 2)


def run_cell_m1(ctx, arms_wanted, obs, truth, snr_centi, frame, matrix_check):
    rows = []
    other = [a for a in arms_wanted if a not in M1_ARMS]
    if other:
        rows += _orig_cell(ctx, other, obs, truth, snr_centi, frame, matrix_check)
    head = dict(rho=.5, rho_permille=500, snr_centi_db=int(snr_centi), snr_db=snr_centi / 100, frame=int(frame),
                **base.truth_summary(truth))
    head.update(base.cluster_row_fields(truth))
    for key in ('truth_l', 'truth_k', 'truth_g2'):
        head.pop(key, None)
    for arm in M1_ARMS:
        if arm not in arms_wanted or (arm == 'GX' and frame % SPOT_EVERY):
            continue
        try:
            res = run_arm(ctx, obs, truth, arm)
        except Exception as error:
            rows.append(dict(head, arm=arm, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
            continue
        row = dict(head, arm=arm, status='ok', **base.score(ctx, res, truth))
        row.update(misfit=res['misfit'], oracle_n_paths=res['oracle_n_paths'], **res['extra'])
        if matrix_check:
            mm = explicit_misfit_taps(ctx, truth, res['channel'])
            row.update(misfit_matrix=mm, misfit_matrix_abs_diff=abs(mm - res['misfit']))
        rows.append(row)
    return rows


def load_context(args):
    ctx = _orig_load_context(args)
    import twofft  # the native directory's module, already imported by base.load_context
    tapchannel.install_general_taps(twofft)
    for name in ('driver_m1.py', 'dpss_taps.py', 'tapchannel.py'):
        ctx.sources[name] = base.sha256_file(f2.HERE / name)
    return ctx


f2.F2_ARMS = f2.F2_ARMS + M1_ARMS
f2.F2_SPEC['m1_dpss'] = (
    'P_D: true delays; per tap, projection of the true tap sequence onto the first D modulated DPSS '
    '(scipy.signal.windows.dpss(N=1024, NW=W, Kmax, sym=True, norm=2)) centred at the power-weighted ray centroid, '
    'W = max_r|nu_r-c|+0.5 bins; detection = fixed-H TF20R2 with a GENERAL-TAP operator (tapchannel.py); '
    'misfit = sum_l||a_l-a~_l||^2/sum_l||a_l||^2; GX = exact tap sequences on frames%20==0')
f2.run_cell_f2 = run_cell_m1
f2.load_context = load_context

if __name__ == '__main__':
    f2.main(sys.argv[1:])
