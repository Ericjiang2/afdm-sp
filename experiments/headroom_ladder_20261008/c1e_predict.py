#!/usr/bin/env python
"""Staircase prediction from the measured SP return map Phi_K (research/c1-scalar-closure.md, Amendment A3 refinement).

Rule (frozen, committed before the EXIT grid output was read):
  Phi_K(I_r) = mean measured round-1 decoder-input MI after injecting the decoder state of previous decoder-input MI I_r
  (out/c1e/analysis); Phi_K(0) := Phi_K(none) (no decoder information = pilot-only state); linear interpolation in I_r
  on [0, max grid], clamped above.  Staircase I_1 = Phi_K(none), I_{r+1} = Phi_K(I_r).  Decode at round r iff I_r >= I*
  (I* = input MI at AWGN FER .5, out/c1_t1/t1_transfer.json "exit").  Kc_EXIT(R) = K where I_R(K) crosses I*, linear in K
  between grid L (I_R evaluated as the best of rounds 1..R, since a success is absorbing).
  Fixed points of Phi_K on [0, max grid]: sign changes of Phi - I; stable iff local slope < 1.  Bistable iff a stable fixed
  point lies below I* and Phi(I) > I somewhere between a higher unstable fixed point and I*.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
D_COEF = 8
R_MAX = 4


def load_phi(path):
    """Adapter: returns {snr: {L: (grid_ir ndarray, phi ndarray, phi_none float)}}; bound to c1e_analyze output schema."""
    blob = json.loads(Path(path).read_text())
    table = blob['Phi']
    out = {}
    for snr_key, by_L in table.items():
        for L_key, by_ir in by_L.items():
            none = float(by_ir['none']['mi_in1']['mean'])
            pts = sorted((float(k), float(v['mi_in1']['mean'])) for k, v in by_ir.items() if k != 'none')
            out.setdefault(float(snr_key), {})[int(L_key.lstrip('L'))] = (np.array([0.] + [p[0] for p in pts]),
                                                              np.array([none] + [p[1] for p in pts]), none)
    return out


def staircase(grid, phi, i_star, rounds=R_MAX):
    f = lambda x: float(np.interp(x, grid, phi))
    traj = [f(0.)]
    for _ in range(rounds - 1):
        traj.append(f(traj[-1]))
    best = list(np.maximum.accumulate(traj))
    first = next((r + 1 for r, v in enumerate(traj) if v >= i_star), None)
    return traj, best, first


def fixed_points(grid, phi, i_star):
    xs = np.linspace(0., grid[-1], 4001)
    h = np.interp(xs, grid, phi) - xs
    fps = []
    for i in np.nonzero((np.sign(h[:-1]) * np.sign(h[1:]) < 0) | ((h[:-1] != 0) & (h[1:] == 0)))[0]:
        x = xs[i] - h[i] * (xs[i + 1] - xs[i]) / (h[i + 1] - h[i])
        d = 1e-3
        slope = (np.interp(x + d, grid, phi) - np.interp(x - d, grid, phi)) / (2 * d)
        fps.append(dict(I=float(x), slope=float(slope), stable=bool(slope < 1), below_I_star=bool(x < i_star)))
    stable_low = [p for p in fps if p['stable'] and p['below_I_star']]
    unstable_above = [p for p in fps if not p['stable'] and stable_low and p['I'] > stable_low[0]['I']]
    bistable = bool(stable_low and unstable_above and any(np.interp(x, grid, phi) > x for x in
                                                          np.linspace(unstable_above[0]['I'], i_star, 50)))
    return fps, bistable


def k_cross(Ks, ys, level):
    for i in range(len(Ks) - 1):
        a, b = ys[i] - level, ys[i + 1] - level
        if a >= 0 > b or a < 0 <= b:
            return float(Ks[i] + a * (Ks[i + 1] - Ks[i]) / (a - b))
    return None


def main():
    i_star = float(json.loads((HERE / 'out/c1_t1/t1_transfer.json').read_text())['exit']['I_in_at_crossings']['FER0.5_linear']['I_in'])
    phi = load_phi(HERE / 'out/c1e/analysis/c1e_phi.json')
    res = dict(_argv=sys.argv, I_star=i_star, cells={}, kc={})
    for snr, by_L in sorted(phi.items()):
        Ls = sorted(by_L)
        best_by_R = {R: [] for R in range(1, R_MAX + 1)}
        for L in Ls:
            grid, ph, none = by_L[L]
            traj, best, first = staircase(grid, ph, i_star)
            fps, bistable = fixed_points(grid, ph, i_star)
            res['cells'][f'{snr:g}|{L}'] = dict(K=D_COEF * L, traj=traj, first_success_round=first, fixed_points=fps,
                                                bistable=bistable)
            for R in best_by_R:
                best_by_R[R].append(best[R - 1])
        Ks = [D_COEF * L for L in Ls]
        res['kc'][f'{snr:g}'] = {f'R{R}': k_cross(Ks, ys, i_star) for R, ys in best_by_R.items()}
    out = HERE / 'out/c1e/analysis/c1e_predictions.json'
    out.write_text(json.dumps(res, indent=1))
    for snr, kc in res['kc'].items():
        print(snr, 'dB Kc_EXIT', kc)
    for key, c in res['cells'].items():
        print(key, 'K', c['K'], 'traj', [round(x, 3) for x in c['traj']], 'first', c['first_success_round'],
              'FPs', [(round(p['I'], 3), p['stable']) for p in c['fixed_points']], 'bistable', c['bistable'])


if __name__ == '__main__':
    main()
