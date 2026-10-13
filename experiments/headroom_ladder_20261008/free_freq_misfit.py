#!/usr/bin/env python
"""F2 supplementary, OFFLINE (no receiver): operator misfit ||H-H_alt||_F^2/||H||_F^2 of per-tap representations on the F2 frames,
to separate representation loss from lattice leakage.  Uses the identity of orders.py (misfit = sum_l||a_l-fit_l||^2/sum_l||a_l||^2).
  lattice  : orders.oracle_paths D=1,2,3,5 (as O1..O5), nested D=2 (O2n)
  free     : D exponentials with FREE frequencies (variable projection, LS gains), D=1,2,3,5; multi-start
             (power-weighted split of the true rays, lattice start, random starts); D>=R -> exact (misfit 0)
usage: free_freq_misfit.py <out.json> [frames] [nproc]
"""
import json
from multiprocessing import Pool
import sys

import numpy as np

import driver
import orders
import orders_free

ENTROPY = '129abc3bec7243c1dd584ffab5b2a3989f2e81da01ee8397de783e8f52357812'
N = 1024
CONFIGS = ('N4a', 'N4b', 'J4')
DS = (1, 2, 3, 5)


def one(args):
    config, frame = args
    pa = driver.cluster_paths(driver.draw_cluster_geometry(ENTROPY, frame), config)
    l, nu, g = pa['l_i'], pa['k_real'], pa['g_i']
    out = dict(config=config, frame=frame, max_rays=max(pa['rays_per_tap']), max_spread=max(pa['tap_spread']))
    for D in DS:
        out[f'lat{D}'] = orders.oracle_paths(l, nu, g, D, N)[3]
    import driver_f2s
    out['lat2n'] = driver_f2s.nested2_paths(l, nu, g, N)[3]
    for D in DS:
        out[f'free{D}'] = orders_free.free_paths(l, nu, g, D, N)[3]
    return out


def main():
    out = sys.argv[1]
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    tasks = [(c, f) for c in CONFIGS for f in range(frames)]
    with Pool(nproc) as p:
        rows = p.map(one, tasks, chunksize=4)
    summ = {}
    keys = [k for k in rows[0] if k.startswith(('lat', 'free'))]
    for c in CONFIGS:
        rr = [r for r in rows if r['config'] == c]
        summ[c] = {k: dict(median=float(np.median([r[k] for r in rr])), p75=float(np.percentile([r[k] for r in rr], 75)),
                           p90=float(np.percentile([r[k] for r in rr], 90)), mean=float(np.mean([r[k] for r in rr])),
                           frac_lt_1e3=float(np.mean([r[k] < 1e-3 for r in rr])), frac_lt_1e2=float(np.mean([r[k] < 1e-2 for r in rr])))
                   for k in keys}
    json.dump(dict(frames=frames, entropy=ENTROPY, summary=summ, rows=rows), open(out, 'w'), indent=1)
    for c in CONFIGS:
        print(c, ' '.join(f"{k}:{summ[c][k]['median']:.3g}" for k in keys), flush=True)


if __name__ == '__main__':
    main()
