#!/usr/bin/env python3
"""Idea-funnel local round 3, numerical check of the global bound the gate reviewer supplied for card I-20261122-l14
(ideas/reviews/astra-regate-l14-20261122.md), 2026-11-22, runner l, claude-fable-5.2.  New numpy / scipy code, no noise.
For any trajectory with |r| <= 1/2, |r'| <= eta on [0, 1]: with e = r - (best uniform line), E = max |e|,
    R1[r] <= int e^2 <= E^2 - 8 E^3 / (3 eta),   E <= min(1/2, eta / 4),
so R1 <= eta^2 / 48 (eta <= 2) or 1/4 - 1/(3 eta) (eta > 2).  Every link of the chain is checked on random feasible
trajectories (full-speed zigzags with up to 12 turns and random dwell, and slope-clipped random walks).
  python l2_r3_ma_bound.py --out out_r3b22
"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
HERE = Path(__file__).resolve().parent
SEED, K = 20261122, 1000
T = (np.arange(K) + 0.5) / K
ETAS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0]
PER = 300


def closed(eta):
    return eta ** 2 / 48 if eta <= 2 else 0.25 - 1 / (3 * eta)


def r1(r):
    A = np.c_[np.ones(K), T]; res = r - A @ np.linalg.lstsq(A, r, rcond=None)[0]
    return float(np.mean(res ** 2))


def minimax_line(r):
    """min E s.t. |r - a - b t| <= E (linear programme in a, b, E)."""
    A = np.r_[np.c_[-np.ones(K), -T, -np.ones(K)], np.c_[np.ones(K), T, -np.ones(K)]]; b = np.r_[-r, r]
    o = linprog([0, 0, 1], A_ub=A, b_ub=b, bounds=[(None, None), (None, None), (0, None)], method='highs')
    a, s, E = o.x
    return r - a - s * T, float(E), float(s)


def zigzag(rng, eta):
    n = int(rng.integers(0, 13)); sw = np.sort(rng.uniform(0, 1, n)); x = rng.uniform(-0.5, 0.5); d = rng.choice([-1.0, 1.0]); speed = eta * rng.choice([1.0, 1.0, 1.0, rng.uniform(0.2, 1.0)])
    r = np.empty(K); j = 0
    for k in range(K):
        while j < n and T[k] >= sw[j]:
            d = -d; j += 1
        x = min(0.5, max(-0.5, x + d * speed / K)); r[k] = x
    return r


def walk(rng, eta):
    v = np.cumsum(rng.standard_normal(K)); v = v / (np.abs(v).max() + 1e-9) * eta * rng.uniform(0.3, 1.0); x = rng.uniform(-0.5, 0.5); r = np.empty(K)
    for k in range(K):
        x = min(0.5, max(-0.5, x + np.clip(v[k], -eta, eta) / K)); r[k] = x
    return r


def main(out):
    out.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng([SEED, 24]); t0 = time.time(); res = dict(_argv=sys.argv, _config=dict(K=K, per_eta=PER, seed=SEED), etas={})
    worst = dict(a=-1.0, b=-1.0, c=-1.0, d=-1.0)
    for eta in ETAS:
        rows = []
        cands = [np.clip(eta * (np.abs(T - 0.5) - 0.25), -0.5, 0.5)] + [zigzag(rng, eta) if i % 3 else walk(rng, eta) for i in range(PER)]
        for r in cands:
            e, E, s = minimax_line(r); ie2 = float(np.mean(e ** 2)); bound = E ** 2 - 8 * E ** 3 / (3 * eta)
            rows.append(dict(r1=r1(r), ie2=ie2, E=E, slope=s, bound=bound))
        tol = 2.0 / K                                                    # grid error of the integrals and of E
        va = max(x['r1'] - x['ie2'] for x in rows); vb = max(x['ie2'] - x['bound'] for x in rows); vc = max(x['E'] - min(0.5, eta / 4) for x in rows); vd = max(x['bound'] - closed(eta) for x in rows)
        worst = dict(a=max(worst['a'], va), b=max(worst['b'], vb), c=max(worst['c'], vc), d=max(worst['d'], vd))
        res['etas'][str(eta)] = dict(closed_form=closed(eta), v_shape=dict(r1=rows[0]['r1'], ie2=rows[0]['ie2'], E=rows[0]['E'], bound=rows[0]['bound']),
                                     max_r1_random=max(x['r1'] for x in rows[1:]), max_r1_over_closed_random=max(x['r1'] for x in rows[1:]) / closed(eta),
                                     viol_r1_minus_ie2=va, viol_ie2_minus_bound=vb, viol_E_minus_cap=vc, viol_bound_minus_closed=vd, tightest_ie2_over_bound=max(x['ie2'] / max(x['bound'], 1e-12) for x in rows[1:]), tol=tol)
        print(eta, 'closed', round(closed(eta), 6), 'V: r1', round(rows[0]['r1'], 6), 'bound', round(rows[0]['bound'], 6), '| random max r1/closed', round(res['etas'][str(eta)]['max_r1_over_closed_random'], 4),
              '| violations', f'{va:+.1e} {vb:+.1e} {vc:+.1e} {vd:+.1e}', flush=True)
    res['worst_violation'] = worst; res['all_links_hold_within_grid_error'] = bool(max(worst.values()) <= 2.0 / K); res['wall_seconds'] = time.time() - t0
    (out / 'ma_bound_check.json').write_text(json.dumps(res, indent=1)); print('all links hold:', res['all_links_hold_within_grid_error'], worst)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out_r3b22'); a = ap.parse_args(); main(HERE / a.out)
