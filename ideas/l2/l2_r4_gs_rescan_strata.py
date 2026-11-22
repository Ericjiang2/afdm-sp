#!/usr/bin/env python
"""Idea-funnel local round 4, descriptive add-on to L2 batch 5 (card I-20261122-l37), suggested by the gate review (post hoc, no criterion):
where does the drop sit?  Stratify the per-key NMSE change (archived GS-set -> round-1 rescan) by the number of slots the round-0 refit
had to coarse-scan (n_missing_slots[0] = true delays the pilot front did not acquire), and report the tail where the rescan arm is worse.
  python l2_r4_gs_rescan_strata.py   -> out_r4b5/strata.json
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r4_gs_rescan as b5

N = b5.load(HERE / 'out_r4b5', None, lambda r: r['rescan'])
G = b5.load(b5.GS_DIR / 'out' / 'main', set(N), lambda r: r['arms']['GS-set'])
Cr = b5.load(b5.CRB_DIR / 'out' / 'main', set(N), lambda r: r['bounds']['mcrb']['c'])
res = {}
for rho in (300, 500):
    ks = [k for k in N if k[1] == rho]
    miss = np.array([G[k]['n_missing_slots'][0] for k in ks]); a = np.array([G[k]['nmse'] for k in ks]); b = np.array([N[k]['nmse'] for k in ks]); m = np.array([Cr[k] for k in ks])
    cell = dict(keys=len(ks), strata={})
    for lab, sel in (('0', miss == 0), ('1', miss == 1), ('2', miss == 2), ('3+', miss >= 3)):
        if sel.any():
            cell['strata'][lab] = dict(share_of_keys=float(sel.mean()), r_set_db=float(10 * np.log10(a[sel].mean() / m[sel].mean())),
                                       r_rescan_db=float(10 * np.log10(b[sel].mean() / m[sel].mean())),
                                       share_of_total_excess_removed=float((a[sel] - b[sel]).sum() / (a - b).sum()))
    d = 10 * np.log10(b / a)
    cell['tail'] = dict(rescan_worse_by_1dB=float(np.mean(d > 1)), rescan_worse_by_3dB=float(np.mean(d > 3)), rescan_better_by_3dB=float(np.mean(d < -3)),
                        worst_db=float(d.max()), set_above_minus20dB=float(np.mean(a > .01)), rescan_above_minus20dB=float(np.mean(b > .01)))
    res[str(rho)] = cell
json.dump(res, open(HERE / 'out_r4b5' / 'strata.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
