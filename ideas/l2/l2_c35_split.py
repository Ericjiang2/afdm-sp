#!/usr/bin/env python3
"""Idea-funnel L2 readout for card I-20261121-c35 (2026-11-21, runner l): zero new simulation.
Splits the stage-A4 gap (pilot estimator vs its pilot_white bound) in the true-delay arm, with A4's metric,
from the per-path rows of l2_batch2.py c01o.   python l2_c35_split.py out2/c01o_rows.jsonl.gz out2/c35_split.json"""
import gzip, json, sys
import numpy as np
BOUND = {100: 0.085, 150: 0.068}
rows = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
out = dict(_argv=sys.argv, bound_pilot_white=BOUND)
for rho in (100, 150):
    for snr in (400, 500, 600):
        full, cut, share = [], [], []
        for r in rows:
            if r['rho'] != rho or r['snr'] != snr:
                continue
            a = r['arm']; e = np.array([np.nan if x is None else abs(x) for x in a['err']], float); g = np.array(a['power'], float)
            ok = ~np.isnan(e)
            if not ok.any():
                continue
            w = g[ok] / g[ok].sum(); ee = e[ok]
            full.append(float(np.sum(w * ee))); cut.append(float(np.sum(w * np.where(ee > 0.25, 0.0, ee)))); share.append(float(np.sum(w * (ee > 0.25))))
        f, c = float(np.mean(full)), float(np.mean(cut))
        out[f'rho{rho}_snr{snr}'] = dict(frames=len(full), metric_all=f, metric_outliers_zeroed=c, outlier_power_share=float(np.mean(share)),
                                         ratio_all_to_bound=f / BOUND[rho], ratio_cut_to_bound=c / BOUND[rho])
json.dump(out, open(sys.argv[2], 'w'), indent=1); print(json.dumps(out, indent=1))
