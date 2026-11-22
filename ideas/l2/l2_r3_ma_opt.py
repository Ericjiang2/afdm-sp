#!/usr/bin/env python3
"""Idea-funnel local round 3, follow-up asked by the gate for card I-20261122-l14 (2026-11-22, runner l, claude-fable-5.2).
q = 1 only: is the even V / U trajectory globally optimal among ALL feasible trajectories (|r| <= D/2, |r'| <= v_max),
not only among even ones?  Direct numerical maximisation of R1[r] = variance of r after removing a constant and a
linear term in time, from many random and structured starts, by projected gradient ascent with an exact projection
onto the box-and-slope constraints (Dykstra).  New numpy code; no noise simulation.
Criteria: ideas/l2/PREDICTIONS_r3_batch22.md.
  python l2_r3_ma_opt.py run --out out_r3b22
Units: T = 1, D = 1; K grid points; eta = v_max T / D.
"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SEED, K = 20261122, 400
TAU = (np.arange(K) + 0.5) / K - 0.5
V = np.vander(TAU, 2, increasing=True); PROJ = np.eye(K) - V @ np.linalg.pinv(V)        # removes constant and linear parts
CFG = dict(etas=[0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0], starts=60, iters=1500)


def r1(r):
    x = PROJ @ r
    return float(np.mean(x ** 2))


def closed_form(eta):
    return eta ** 2 / 48 if eta <= 2 else 0.25 - 1 / (3 * eta)


def v_shape(eta):
    return np.clip(eta * (0.25 - np.abs(TAU)), -0.5, 0.5)


def project(r, eta, sweeps=60):
    """Dykstra projection onto {|r| <= 1/2} intersected with {|r[k+1] - r[k]| <= eta / K}."""
    step = eta / K; x = r.copy(); p = np.zeros(K); q = np.zeros(K)
    for _ in range(sweeps):
        y = np.clip(x + p, -0.5, 0.5); p = x + p - y
        z = y + q; w = z.copy()
        for _ in range(8):                                   # alternate forward / backward slope clipping (Gauss-Seidel on pairs)
            d = np.diff(w); ex = np.clip(d, -step, step) - d
            w[:-1] -= ex / 2; w[1:] += ex / 2
        q = z - w; x = w
    x = np.clip(x, -0.5, 0.5)
    for k in range(1, K):                                    # final hard feasibility pass
        x[k] = np.clip(x[k], x[k - 1] - step, x[k - 1] + step)
    return x


def ascend(r0, eta):
    r = project(r0, eta); best = (r1(r), r); lr = 2.0
    for it in range(CFG['iters']):
        g = 2 * (PROJ @ r) / K
        cand = project(r + lr * K * g, eta); val = r1(cand)
        if val > best[0] + 1e-12:
            best = (val, cand); r = cand; lr = min(lr * 1.1, 50.0)
        else:
            lr *= 0.5
            if lr < 1e-4:
                break
    return best


def starts(eta, rng):
    out = [v_shape(eta), -v_shape(eta), np.clip(eta * TAU, -0.5, 0.5)]
    for s in np.linspace(-0.3, 0.3, 13):                     # V / U shapes shifted in time (asymmetric)
        out.append(np.clip(eta * (0.25 - np.abs(TAU - s)), -0.5, 0.5))
    for m in (2, 3, 4):                                      # multi-turn zigzags with random phase
        for _ in range(4):
            ph = rng.uniform(0, 1); z = 2 * np.abs(((TAU + 0.5) * m / 2 + ph) % 1 - 0.5) - 0.5; out.append(z)
    while len(out) < CFG['starts']:
        w = np.cumsum(rng.standard_normal(K)) ; w = (w - w.mean()) / (np.abs(w - w.mean()).max() + 1e-9) * 0.5; out.append(w)
    return out


def run(out):
    out.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng([SEED, 22]); t0 = time.time(); res = dict(_argv=sys.argv, _config=dict(CFG, K=K, seed=SEED), etas={})
    for eta in CFG['etas']:
        vals = []; best = None
        for s in starts(eta, rng):
            v, r = ascend(s, eta); vals.append(v)
            if best is None or v > best[0]:
                best = (v, r)
        ref = r1(project(v_shape(eta), eta)); cf = closed_form(eta); r = best[1]
        even_dist = float(np.min([np.max(np.abs(r - sgn * r[::-1])) for sgn in (1,)]))        # 0 if the best solution is even in time
        res['etas'][str(eta)] = dict(closed_form=cf, v_shape_discrete=ref, best_found=best[0], excess_over_v_shape=best[0] / ref - 1,
                                     best_is_even_max_dev=even_dist, n_starts=len(vals), n_within_1e3=int(np.sum(np.array(vals) > ref * (1 - 1e-3))),
                                     best_traj=[float(x) for x in r[::8]])
        print(eta, 'closed', round(cf, 6), 'V', round(ref, 6), 'best', round(best[0], 6), 'excess', f'{best[0] / ref - 1:+.2e}', 'even dev', round(even_dist, 4), flush=True)
    ex = [v['excess_over_v_shape'] for v in res['etas'].values()]
    res['max_excess'] = float(max(ex)); res['verdict'] = 'COUNTEREXAMPLE' if max(ex) > 2e-3 else 'NO_COUNTEREXAMPLE_FOUND'
    res['wall_seconds'] = time.time() - t0
    (out / 'ma_opt_summary.json').write_text(json.dumps(res, indent=1)); print(res['verdict'], res['max_excess'])


def bang_traj(params, eta, d0, n=2000):
    tau = (np.arange(n) + 0.5) / n - 0.5; r0 = float(np.clip(params[0], -0.5, 0.5)); sw = np.sort(np.clip(params[1:], -0.5, 0.5))
    r = np.empty(n); x = r0; d = d0; j = 0; dt = 1.0 / n
    for k in range(n):
        while j < len(sw) and tau[k] >= sw[j]:
            d = -d; j += 1
        x = min(0.5, max(-0.5, x + d * eta * dt)); r[k] = x
    return tau, r


def r1n(tau, r):
    A = np.c_[np.ones_like(tau), tau]; res = r - A @ np.linalg.lstsq(A, r, rcond=None)[0]
    return float(np.mean(res ** 2))


def run_bang(out):
    from scipy.optimize import minimize
    out.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng([SEED, 23]); t0 = time.time(); res = dict(_argv=sys.argv, etas={})
    for eta in CFG['etas']:
        tau, rv = bang_traj(np.array([-0.5 if eta > 2 else -eta / 4, 0.0]), eta, +1) if False else (None, None)
        n = 2000; tau = (np.arange(n) + 0.5) / n - 0.5; ref = r1n(tau, np.clip(eta * (0.25 - np.abs(tau)), -0.5, 0.5)); best = (0.0, None, None)
        for nsw in range(0, 5):
            for _ in range(300):
                x0 = np.r_[rng.uniform(-0.5, 0.5), np.sort(rng.uniform(-0.5, 0.5, nsw))]; d0 = int(rng.choice([-1, 1]))
                v0 = r1n(*bang_traj(x0, eta, d0, 400))
                if v0 < 0.6 * ref and rng.uniform() < 0.8:
                    continue
                o = minimize(lambda x: -r1n(*bang_traj(x, eta, d0, 400)), x0, method='Nelder-Mead', options=dict(xatol=1e-4, fatol=1e-9, maxiter=400))
                v = r1n(*bang_traj(o.x, eta, d0, n))
                if v > best[0]:
                    best = (v, [float(z) for z in o.x], d0)
        res['etas'][str(eta)] = dict(closed_form=closed_form(eta), v_shape=ref, best_found=best[0], excess=best[0] / ref - 1, best_params=best[1], best_d0=best[2])
        print(eta, 'V', round(ref, 6), 'best', round(best[0], 6), 'excess', f'{best[0] / ref - 1:+.2e}', 'params', [round(z, 3) for z in best[1]], best[2], flush=True)
    ex = max(v['excess'] for v in res['etas'].values()); res['max_excess'] = float(ex); res['verdict'] = 'COUNTEREXAMPLE' if ex > 2e-3 else 'NO_COUNTEREXAMPLE_FOUND'; res['wall_seconds'] = time.time() - t0
    (out / 'ma_bang_summary.json').write_text(json.dumps(res, indent=1)); print(res['verdict'], res['max_excess'])


def rqn(tau, r, q):
    A = np.vander(tau, q + 1, increasing=True); res = r - A @ np.linalg.lstsq(A, r, rcond=None)[0]
    return float(np.mean(res ** 2))


def cheb3(eta, a, n=2000):
    """Three full-speed transitions centred at -a, 0, +a (time in [-1/2, 1/2]), dwelling at the ends in between."""
    tau = (np.arange(n) + 0.5) / n - 0.5; r = np.full(n, -0.5)
    for tj, step in zip((-a, 0.0, a), (1.0, -1.0, 1.0)):
        r = r + step * np.clip((tau - tj) * eta + 0.5, 0.0, 1.0)
    return tau, r


def run_bang_q2(out):
    """Exploratory (no pre-registered criterion): q = 2, best R2 found among full-speed zigzags with up to 6 turns,
    against the two three-crossing candidates on the card / in the gate review.  Recorded as an addendum to I-20261122-l14."""
    from scipy.optimize import minimize
    out.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng([SEED, 25]); t0 = time.time(); res = dict(_argv=sys.argv, etas={}); n = 2000
    for eta in [1.0, 2.0, 3.0, 4.0, 5.0, 8.0, 10.0]:
        cands = {}
        if eta >= 2 * np.sqrt(2):                              # the three transitions do not overlap
            cands['cheb_nodes'] = rqn(*cheb3(eta, 1 / np.sqrt(8), n), 2); cands['shifted_nodes'] = rqn(*cheb3(eta, float(np.sqrt(1 / 8 - 1 / (24 * eta ** 2))), n), 2)
        best = (0.0, None, None, None)
        for nsw in range(0, 7):
            for _ in range(250):
                x0 = np.r_[rng.uniform(-0.5, 0.5), np.sort(rng.uniform(-0.5, 0.5, nsw))]; d0 = int(rng.choice([-1, 1]))
                o = minimize(lambda x: -rqn(*bang_traj(x, eta, d0, 300), 2), x0, method='Nelder-Mead', options=dict(xatol=1e-4, fatol=1e-9, maxiter=300))
                v = rqn(*bang_traj(o.x, eta, d0, n), 2)
                if v > best[0]:
                    best = (v, [float(z) for z in o.x], d0, nsw)
        res['etas'][str(eta)] = dict(best_found=best[0], best_params=best[1], best_d0=best[2], best_turns=best[3], candidates=cands, q1_optimum_for_reference=closed_form(eta))
        print(eta, 'best R2', round(best[0], 6), 'turns', best[3], 'params', [round(z, 3) for z in best[1]], best[2], 'cands', {k: round(v, 6) for k, v in cands.items()}, flush=True)
    res['wall_seconds'] = time.time() - t0
    (out / 'ma_bang_q2_explore.json').write_text(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'bang', 'bangq2')); ap.add_argument('--out', default='out_r3b22'); a = ap.parse_args()
    if a.mode == 'smoke':
        rng = np.random.default_rng(1)
        for eta in (1.5, 5.0):
            t0 = time.process_time(); ref = r1(project(v_shape(eta), eta)); v, r = ascend(np.clip(eta * (0.25 - np.abs(TAU - 0.2)), -0.5, 0.5), eta); v2, _ = ascend(np.cumsum(rng.standard_normal(K)) / 40, eta)
            print(eta, 'closed', closed_form(eta), 'V', ref, 'from shifted V', v, 'from random', v2, 'cpu', round(time.process_time() - t0, 1))
    elif a.mode == 'bang':
        run_bang(HERE / a.out)
    elif a.mode == 'bangq2':
        run_bang_q2(HERE / a.out)
    else:
        run(HERE / a.out)
