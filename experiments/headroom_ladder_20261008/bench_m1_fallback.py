#!/usr/bin/env python
"""M1 item 1 bench (deinlab, single thread): cost/accuracy of the FALLBACK realization (dense in-band exponential set,
0.25-bin lattice, ridge LS gains) versus the direct general-tap operator, on F1/F2 frames.

(a) covering sets: per tap all lattice points in [c-W, c+W] (K = 2*floor(4W)+1 exponentials) fitted to the D=3 DPSS target;
    reports P_total, operator misfit of the fallback vs the target for several ridge levels, max |gain|, cond(E^H E).
(b) runtime: fixed-H scalar_joint (20 iterations, damping .3, gain_mode='fixed') alone, median of 3 repeats, for the general-tap
    operator (P = #taps) and dense sets with K in {5, 10, 20} per tap (P_total = 4K = 20, 40, 80), each fitted to the exact taps.
usage: bench_m1_fallback.py <out.json>
"""
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import driver  # noqa: E402
import driver_f2 as f2  # noqa: E402
import driver_m1 as m1  # noqa: E402
import dpss_taps  # noqa: E402
import orders  # noqa: E402
import tapchannel  # noqa: E402

ENTROPY = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'
N = 1024
RIDGES = (1e-12, 1e-10, 1e-8, 1e-6)


def dense_paths(delays, taps, centres, K, ridge, grid=.25):
    ls, nus, gs, num, den, gmax = [], [], [], 0., 0., 0.
    for i, d in enumerate(delays):
        nu, g, mis, gm, _ = dpss_taps.dense_exp_fit(taps[:, i], centres[i], None, N, grid=grid, count=K, ridge_rel=ridge)
        k = np.arange(N)
        resid = taps[:, i] - np.exp(2j * np.pi * np.outer(k, nu) / N) @ g
        num += float(np.vdot(resid, resid).real)
        den += float(np.vdot(taps[:, i], taps[:, i]).real)
        ls += [int(d)] * K
        nus += list(nu)
        gs += list(g)
        gmax = max(gmax, gm)
    return np.array(ls, int), np.array(nus), np.array(gs), num / den, gmax


def main():
    out = Path(sys.argv[1])
    args = f2.parse_args(['--mode', 'generate', '--out', str(out.parent), '--frames', '1', '--entropy-hex', ENTROPY,
                          '--snr-list', '9'])
    ctx = m1.load_context(args)
    import twofft
    s = ctx.system
    rep = dict(covering=[], runtime=[])

    # (a) covering sets vs D=3 DPSS target
    for config in ('N4b', 'J4'):
        for f in range(6):
            pa = driver.cluster_paths(driver.draw_cluster_geometry(ENTROPY, f), config)
            p = dpss_taps.project_taps(pa['l_i'], pa['k_real'], pa['g_i'], (3,), N)
            taps = p['by_order'][3]['taps']
            for ridge in RIDGES:
                num = den = 0.
                P, gmax, cmax = 0, 0., 0.
                for i in range(len(p['delays'])):
                    nu, g, mis, gm, cond = dpss_taps.dense_exp_fit(taps[:, i], p['centroid'][i], p['W'][i], N,
                                                                   grid=.25, ridge_rel=ridge)
                    num += mis * float(np.vdot(taps[:, i], taps[:, i]).real)
                    den += float(np.vdot(taps[:, i], taps[:, i]).real)
                    P += len(nu)
                    gmax, cmax = max(gmax, gm), max(cmax, cond)
                rep['covering'].append(dict(config=config, frame=f, ridge_rel=ridge, P_total=P, misfit_vs_target=num / den,
                                            dpss_misfit_vs_truth=p['by_order'][3]['misfit'], max_abs_gain=gmax,
                                            max_cond_gram=cmax, W=[float(x) for x in p['W']]))

    # (b) runtime of the detector alone
    msg_cache = {}
    for config, f in (('N4b', 0), ('J4', 0)):
        msg = msg_cache.setdefault(f, driver.cluster_message(ctx, ENTROPY, f))
        raw_base, diag = driver.cluster_base(ctx, msg, driver.draw_cluster_geometry(ENTROPY, f), config)
        raw = driver.cluster_at_snr(raw_base, 9.0)
        obs, truth = driver.observe(raw, .5, 9.0), driver.truth_from_raw(raw, diag)
        p = dpss_taps.project_taps(truth['l_i'], truth['k_real'], truth['g_i'], (3,), N)
        exact = p['exact_taps']
        chans = {'general_taps': tapchannel.make_tap_channel(N, s.c1, s.c2, p['delays'], exact)}
        for K in (5, 10, 20):
            ls, nus, gs, mis, gmax = dense_paths(p['delays'], exact, p['centroid'], K, 1e-10)
            chans[f'dense_K{K}'] = ctx.Channel(N, s.c1, s.c2, ls, nus, gs)
            rep['runtime'].append(dict(config=config, kind=f'dense_K{K}', P=int(len(ls)), misfit_vs_exact=mis, max_abs_gain=gmax,
                                       span_bins=.25 * (K - 1)))
        chans['true_rays'] = ctx.Channel(N, s.c1, s.c2, truth['l_i'], truth['k_real'], truth['g_i'])
        for name, ch in chans.items():
            ts = []
            for _ in range(3):
                t0 = time.perf_counter()
                twofft.scalar_joint(obs['y'], obs['pilot'], ch, obs['sigma2'], pd=.5, prior=np.zeros(2 * N), iterations=20,
                                    damping=.3, gain_mode='fixed')
                ts.append(time.perf_counter() - t0)
            rec = next((r for r in rep['runtime'] if r['config'] == config and r['kind'] == name), None)
            if rec is None:
                rec = dict(config=config, kind=name, P=int(ch.p))
                rep['runtime'].append(rec)
            rec['detector_seconds_median'] = float(np.median(ts))
            rec['detector_seconds_all'] = ts
            print(config, name, rec['P'], f"{np.median(ts):.4f}s", flush=True)
    out.write_text(json.dumps(rep, indent=1, default=driver.to_jsonable, allow_nan=False) + '\n')
    print('done', flush=True)


if __name__ == '__main__':
    main()
