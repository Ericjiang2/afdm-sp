#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l02 (2026-11-21, runner l), asked by the gate.
Source: experiments/headroom_ladder_20261008/driver_c1e.py, imported unchanged; only its `targets` function is replaced here so that an arm label
maps to a fixed (I_A, I_R) pair instead of the pair read off the (3,6) code's T1 curve.  Reason it cannot be called as is: the driver has no option
for a free pair.   Run (deinlab, one process per shard):  python -B l2_l02_inject.py --mode generate --out <dir> --Ls 28 --snr-list 6.5
   --Ir 0.11,0.12,0.21,0.22 --frames 100 --shard i --nshard n      then  --mode merge --out <dir>
"""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments' / 'headroom_ladder_20261008'))
import driver_c1e as d  # noqa: E402
PAIRS = {0.11: (0.1276, 0.4483), 0.12: (0.1276, 0.5198), 0.21: (0.3173, 0.6134), 0.22: (0.3173, 0.6669)}


def targets(curve, ir):
    if ir is None:
        return None
    ia, ir_ = PAIRS[round(float(ir), 2)]; sa, sr = d.J_inv(ia), d.J_inv(ir_)
    return dict(IA=ia, IR=ir_, sigma_A=sa, sigma_R=sr, sigma_C=float(np.sqrt(sr ** 2 - sa ** 2)))


d.targets = targets
if __name__ == '__main__':
    print('pairs', PAIRS, flush=True)
    d.main()
