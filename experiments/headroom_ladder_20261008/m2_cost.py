#!/usr/bin/env python
"""M2 per-arm seconds/cell from smoke rows and full-run CPU-hour projection.

  m2_cost.py <out.json> <f2_cost.json> <smoke_dir> [<smoke_dir> ...]

Plan projected: configs D1,N4a,N4b,J4,J8 x SNR 6..11 (6 points) x 1000 frames x arms B(A0),PS,M_full,M_adapt,A3, plus PB16 on N4b,J4 x
SNR {7,9,11} x 1000 frames.  Per-(config, arm) mean seconds come from the smoke rows (config measured there; otherwise the J4 value is used
for J8 and the pooled value for any other missing config).  Scenarios:
  idle    seconds as measured in the smoke (lightly loaded machine)
  loaded  seconds scaled by the F2 loaded/idle ratio of the A3 arm (F2 ran on 100 shards): loaded = idle * (F2 A3 mean / smoke A3 mean)
reuse     the F2 rows already cover B, PS, A3 for D1,N4a,N4b,J4 x SNR 6..11 x frames 0..999; "new" excludes those cells (J8 B/PS/A3 and all
          M / PB16 cells remain).
"""
import glob
import json
import sys

import numpy as np

ARMS = ('A0', 'PS', 'M_full', 'M_adapt', 'A3')
CONFIGS = ('D1', 'N4a', 'N4b', 'J4', 'J8')
F2_COVERED = {'A0', 'PS', 'A3'}
F2_CONFIGS = {'D1', 'N4a', 'N4b', 'J4'}
SNRS, FRAMES = 6, 1000
PB_CONFIGS, PB_SNRS = ('N4b', 'J4'), 3


def main():
    out, f2cost, dirs = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3:]
    sec = {}
    for d in dirs:
        for f in sorted(glob.glob(d + '/rows_shard*.jsonl')):
            for line in open(f):
                r = json.loads(line)
                if r['status'] == 'ok':
                    sec.setdefault((r['config'], r['arm']), []).append(r['seconds'])
    mean = {k: float(np.mean(v)) for k, v in sec.items()}
    count = {k: len(v) for k, v in sec.items()}

    def get(config, arm):
        if (config, arm) in mean:
            return mean[(config, arm)]
        if config == 'J8' and ('J4', arm) in mean:
            return mean[('J4', arm)]
        vals = [v for (c, a), v in mean.items() if a == arm]
        return float(np.mean(vals)) if vals else float('nan')

    ratios = []
    for config in CONFIGS:
        k = f'{config}/A3'
        if k in f2cost and (config, 'A3') in mean:
            ratios.append(f2cost[k]['mean'] / mean[(config, 'A3')])
    load_factor = float(np.mean(ratios)) if ratios else float('nan')
    table = {}
    total = dict(idle_all=0., idle_new=0., idle_pb16=0.)
    for config in CONFIGS:
        for arm in ARMS:
            cells = SNRS * FRAMES
            s = get(config, arm)
            table[f'{config}/{arm}'] = dict(sec_per_cell=s, n_smoke=count.get((config, arm), 0), cells=cells, cpu_h=s * cells / 3600.)
            total['idle_all'] += s * cells / 3600.
            if not (arm in F2_COVERED and config in F2_CONFIGS):
                total['idle_new'] += s * cells / 3600.
    for config in PB_CONFIGS:
        s = get(config, 'PB16')
        cells = PB_SNRS * FRAMES
        table[f'{config}/PB16'] = dict(sec_per_cell=s, n_smoke=count.get((config, 'PB16'), 0), cells=cells, cpu_h=s * cells / 3600.)
        total['idle_pb16'] += s * cells / 3600.
    res = dict(load_factor_f2_over_smoke_A3=load_factor, per_cell=table, totals_cpu_h=dict(
        all_arms_idle=total['idle_all'], new_arms_idle=total['idle_new'], pb16_idle=total['idle_pb16'],
        all_plus_pb16_idle=total['idle_all'] + total['idle_pb16'], new_plus_pb16_idle=total['idle_new'] + total['idle_pb16'],
        all_plus_pb16_loaded=(total['idle_all'] + total['idle_pb16']) * load_factor,
        new_plus_pb16_loaded=(total['idle_new'] + total['idle_pb16']) * load_factor))
    json.dump(res, open(out, 'w'), indent=1)
    print(f'load factor (F2 A3 / smoke A3) = {load_factor:.2f}')
    for k, v in table.items():
        print(f"{k:12s} {v['sec_per_cell']:.3f} s/cell  (smoke n={v['n_smoke']})  {v['cells']} cells  {v['cpu_h']:.2f} CPU-h")
    print(json.dumps(res['totals_cpu_h'], indent=1))


if __name__ == '__main__':
    main()
