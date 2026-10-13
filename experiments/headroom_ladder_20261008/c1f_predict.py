#!/usr/bin/env python
"""Frozen predictions for the A4 fold / bistability run (research/c1-scalar-closure.md, Amendment A4).
Source: the existing return map out/c1e/analysis/c1e_phi.json (6.5 dB, rho .3, frames 500-599, L 8..28) and the frozen
staircase / fixed-point rules of c1e_predict.py, extended to 10 rounds.  Written before any A4 row exists.
Output: out/c1f/predictions_frozen.json
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import c1e_predict as E

HERE = Path(__file__).resolve().parent
R_MAX = 10


def main():
    istar = float(json.loads((HERE / 'out/c1_t1/t1_transfer.json').read_text())['exit']['I_in_at_crossings']['FER0.5_linear']['I_in'])
    phi = E.load_phi(HERE / 'out/c1e/analysis/c1e_phi.json')[6.5]
    Ls = sorted(phi)
    cells, best = {}, {R: [] for R in range(1, R_MAX + 1)}
    for L in Ls:
        grid, ph, _ = phi[L]
        traj, b, first = E.staircase(grid, ph, istar, rounds=R_MAX)
        fps, bistable = E.fixed_points(grid, ph, istar)
        cells[f'L{L}'] = dict(K=8 * L, traj=traj, first_success_round=first, fixed_points=fps, bistable=bistable)
        for R in best:
            best[R].append(b[R - 1])
    Ks = [8 * L for L in Ls]
    out = dict(_argv=sys.argv, I_star=istar, source='out/c1e/analysis/c1e_phi.json (6.5 dB, rho .3, frames 500-599)',
               kc_by_round={f'R{R}': E.k_cross(Ks, ys, istar) for R, ys in best.items()}, cells=cells)
    (HERE / 'out/c1f').mkdir(parents=True, exist_ok=True)
    (HERE / 'out/c1f/predictions_frozen.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out['kc_by_round']))
    for k, c in cells.items():
        print(k, [round(x, 3) for x in c['traj']], c['first_success_round'], [(round(f['I'], 3), f['stable']) for f in c['fixed_points']])


if __name__ == '__main__':
    main()
