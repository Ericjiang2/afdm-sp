#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l02 (2026-11-21, runner l): zero-simulation EXIT tunnel test.
Inner loop = measured detector + channel re-estimation transfer T(I_A) from
experiments/headroom_ladder_20261008/out/c1e/analysis/c1e_phi.json (res-20261009-01; rho .3).
Outer code = LDPC ensembles under the Gaussian-approximation EXIT model (J function of ten Brink et al. 2004),
merged schedule: the detector is refreshed inside the BP iteration.  Question: at a load where the (3,6) code
stalls, does any rate-1/2 ensemble open the tunnel, and how many dB lower can it go at K = 224?
Approximations (stated in the card): T is used as a function of I_A only (the table pairs I_A with the APP
information of the (3,6) code), consistent-Gaussian beliefs, infinite length, linear interpolation of T in SNR.

  /opt/anaconda3/bin/python ideas/l2/l2_exit_tunnel.py --out ideas/l2/out3/exit_tunnel.json
"""
import argparse, itertools, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PHI = ROOT / 'experiments/headroom_ladder_20261008/out/c1e/analysis/c1e_phi.json'
H1, H2, H3 = 0.3073, 0.8935, 1.1064


def J(s):
    return (1 - 2 ** (-H1 * np.asarray(s, float) ** (2 * H2))) ** H3


def Jinv(i):
    i = np.clip(np.asarray(i, float), 1e-12, 1 - 1e-12)
    return (-np.log2(1 - i ** (1 / H3)) / H1) ** (1 / (2 * H2))


def transfer(P, snr, L):
    pts = []
    for ir, c in P[snr][L].items():
        pts.append((0.0 if ir == 'none' else c['ia_real']['mean'], c['mi_in1']['mean']))
    pts.sort(); x = np.array([p[0] for p in pts] + [1.0]); y = np.array([p[1] for p in pts] + [pts[-1][1]])
    return x, np.maximum.accumulate(y)


def ensemble(lam, dc):
    """lam: {degree: edge fraction}; checks concentrated on floor(dc), floor(dc)+1 (edge perspective)."""
    d = np.array(sorted(lam)); l = np.array([lam[k] for k in d], float); l = l / l.sum()
    lo = int(np.floor(dc)); frac_hi = dc - lo            # node-perspective mix giving average check degree dc
    nodes = {lo: 1 - frac_hi, lo + 1: frac_hi}
    rho = {k: v * k / dc for k, v in nodes.items() if v > 0}
    rate = 1 - (sum(v / k for k, v in rho.items())) / (l / d).sum()
    Ld = (l / d) / (l / d).sum()
    return dict(d=d, lam=l, rho=rho, rate=float(rate), Ld=Ld)


def converge(E, x, y, iters=4000, tol=1e-9):
    """Merged schedule. Returns (final check-to-variable information, detector a-priori information at the end)."""
    ic = 0.0
    for _ in range(iters):
        s_c = Jinv(ic) if ic > 0 else 0.0
        ia_det = float(np.sum(E['Ld'] * J(np.sqrt(E['d']) * s_c)))
        s_ch = Jinv(np.interp(ia_det, x, y))
        iev = float(np.sum(E['lam'] * J(np.sqrt((E['d'] - 1) * s_c ** 2 + s_ch ** 2))))
        new = 1 - sum(r * J(np.sqrt(k - 1) * Jinv(1 - iev)) for k, r in E['rho'].items())
        if new - ic < tol:
            ic = new; break
        ic = new
    s_c = Jinv(ic)
    return ic, float(np.sum(E['Ld'] * J(np.sqrt(E['d']) * s_c)))


def opens(E, x, y):
    return converge(E, x, y)[0] > 1 - 1e-4


def candidates():
    out = [('(3,6) regular', ensemble({3: 1.0}, 6.0))]
    for dmax in (6, 8, 12, 20, 30):
        for l2 in np.arange(0.0, 0.61, 0.05):
            for l3 in np.arange(0.0, 1.01 - l2, 0.05):
                lam = {2: l2, 3: l3, dmax: 1 - l2 - l3}
                lam = {k: v for k, v in lam.items() if v > 1e-9}
                avg = 1 / sum(v / k for k, v in lam.items())           # average variable degree
                dc = 2 * avg                                           # rate 1/2
                if dc < 3:
                    continue
                E = ensemble(lam, dc)
                if abs(E['rate'] - 0.5) < 1e-9:
                    out.append((f'lam2={l2:.2f} lam3={l3:.2f} lam{dmax}={1 - l2 - l3:.2f} dc={dc:.2f}', E))
    return out


def min_snr(E, P, L, lo=3.0, hi=9.5, step=0.05):
    """Lowest SNR (dB) at which the tunnel opens at load L; T linear in SNR between/beyond the 6.5 and 8 dB tables."""
    x1, y1 = transfer(P, '6.5', L); x2, y2 = transfer(P, '8', L)
    grid = np.linspace(0, 1, 201); a = np.interp(grid, x1, y1); b = np.interp(grid, x2, y2)
    for s in np.arange(lo, hi + 1e-9, step):
        y = np.clip(a + (b - a) * (s - 6.5) / 1.5, 1e-6, 1 - 1e-6)
        if opens(E, grid, np.maximum.accumulate(y)):
            return float(s)
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); a = ap.parse_args()
    P = json.loads(PHI.read_text())['Phi']; C = candidates(); res = dict(_argv=sys.argv, n_candidates=len(C))
    reg = C[0][1]
    # validation of the model: (3,6) decoder extrinsic vs the table's design pairs (I_r -> IA_t)
    flat = lambda i: (np.array([0.0, 1.0]), np.array([i, i]))
    res['validate_36'] = {str(i): round(converge(reg, *flat(i))[1], 3) for i in (0.42, 0.45, 0.50, 0.53, 0.55, 0.57, 0.60, 0.65)}
    res['table_IA_t'] = {'0.42': 0.079, '0.45': 0.114, '0.50': 0.208, '0.53': 0.310, '0.55': 0.442, '0.57': 0.659, '0.60': 0.930, '0.65': 0.997}
    tab = {}
    for snr in ('6.5', '8'):
        for L in P[snr]:
            x, y = transfer(P, snr, L)
            ok = [name for name, E in C[1:] if opens(E, x, y)]
            tab[f'{snr}dB_{L}'] = dict(start=float(y[0]), area=float(np.trapezoid(y, x)), reg36_opens=bool(opens(reg, x, y)),
                                       n_irregular_open=len(ok), example=ok[:3])
    res['tunnel'] = tab
    best = {}
    for L in ('L8', 'L16', 'L28'):
        s36 = min_snr(reg, P, L); cand = []
        for name, E in C[1:]:
            s = min_snr(E, P, L, hi=(s36 or 9.5))
            if s is not None:
                cand.append((s, name))
        cand.sort()
        best[L] = dict(reg36_min_snr=s36, best_irregular_min_snr=cand[0][0] if cand else None, best_irregular=cand[0][1] if cand else None,
                       gain_db=None if (s36 is None or not cand) else round(s36 - cand[0][0], 2), top5=cand[:5])
    res['min_snr'] = best
    Path(a.out).write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
