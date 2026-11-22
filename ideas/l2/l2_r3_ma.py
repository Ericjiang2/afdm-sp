#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 check for card I-20261122-l14 (2026-11-22, runner l, claude-fable-5.2).
One movable antenna, K snapshots, unknown angle u, unknown Doppler / CFO, unknown phase: global 2-D maximum likelihood
for four trajectories under the same travel range D and speed limit (eta = v_max T / D).  New numpy code.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch20.md (the card's two-level veto).
  python l2_r3_ma.py smoke|run|read --out out_r3b20
Units: time tau = t / T in [-1/2, 1/2]; position in wavelengths (D = 4); Doppler nu = f_d T in cycles per frame (|nu| <= 2).
"""
import argparse, json, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SEED, WORKERS, K, D, NU_MAX = 20261122, 8, 128, 4.0, 2.0
TAU = (np.arange(K) + 0.5) / K - 0.5
CFG = dict(trials=400, etas=[0.8, 1.5, 2.0, 3.0, 5.0, 10.0], kg_db=[14.0, 16.0, 20.0, 24.0], cap=3.5, q2_trials=200,
           u_grid=np.arange(-1.0, 1.0001, 0.01).tolist(), nu_grid=np.arange(-2.5, 2.5001, 0.05).tolist(), c_grid=np.arange(-4.4, 4.4001, 0.2).tolist())


def traj(name, eta):
    if name == 'static_opt':
        return D * np.clip(eta * TAU, -0.5, 0.5)
    if name == 'u_turn_opt':
        return D * np.clip(eta * (0.25 - np.abs(TAU)), -0.5, 0.5)
    if name == 'u_turn_capped':
        return traj('u_turn_opt', min(eta, CFG['cap']))
    if name == 'cosine_base':
        return 0.5 * D * min(1.0, eta / np.pi) * np.cos(2 * np.pi * TAU)
    if name == 'u_turn_round':                      # corners of the V / U shape rounded over tau_a / T = 0.10 (finite acceleration)
        s = np.linspace(-0.05, 0.05, 41)
        return np.mean(D * np.clip(eta * (0.25 - np.abs(TAU[:, None] + s[None, :])), -0.5, 0.5), axis=1)
    if name == 'cheb3':                             # three crossings at the zeros of U_3, ramps at full speed
        r = np.full(K, -0.5)
        for tj, step in zip((-np.sqrt(0.5) / 2, 0.0, np.sqrt(0.5) / 2), (1.0, -1.0, 1.0)):
            r = r + step * np.clip((TAU - tj) * eta + 0.5, 0.0, 1.0)
        return D * r
    raise ValueError(name)


def r_q(r, q):                                       # residual variance after removing a degree-q polynomial in tau
    V = np.vander(TAU, q + 1, increasing=True); res = r - V @ np.linalg.lstsq(V, r, rcond=None)[0]
    return float(np.mean(res ** 2))


def crb_u(r, kg, q=1):
    return 1.0 / (2 * kg * (2 * np.pi) ** 2 * max(r_q(r, q), 1e-300))


def mle2(y, r):
    """Global search on the (u, nu) grid, three strongest separated peaks, each zoomed three times."""
    ug, ng = np.asarray(CFG['u_grid']), np.asarray(CFG['nu_grid'])
    def surf(us, ns):
        return np.abs((np.exp(-2j * np.pi * np.outer(us, r)) * y[None, :]) @ np.exp(-2j * np.pi * np.outer(ns, TAU)).T) ** 2
    S = surf(ug, ng); best = None; S2 = S.copy()
    for _ in range(3):
        i, j = np.unravel_index(int(np.argmax(S2)), S2.shape); u0, n0, du, dn = ug[i], ng[j], 0.01, 0.05
        for _ in range(3):
            us = u0 + du * np.linspace(-1, 1, 11); ns = n0 + dn * np.linspace(-1, 1, 11); Z = surf(us, ns)
            a, b = np.unravel_index(int(np.argmax(Z)), Z.shape); u0, n0, du, dn = us[a], ns[b], du / 5, dn / 5
        val = float(Z.max())
        if best is None or val > best[0]:
            best = (val, u0, n0)
        S2[max(0, i - 5):i + 6, max(0, j - 5):j + 6] = 0
    return best[1], best[2]


def mle3(y, r):
    """q = 2: unknown quadratic phase exp(j 2 pi c tau^2); grid over c, 2-D search inside, zoom on (u, nu, c)."""
    ug, ng, cg = np.asarray(CFG['u_grid']), np.asarray(CFG['nu_grid']), np.asarray(CFG['c_grid'])
    Eu = np.exp(-2j * np.pi * np.outer(ug, r)); En = np.exp(-2j * np.pi * np.outer(ng, TAU)).T; best = None
    for c in cg:
        S = np.abs((Eu * (y * np.exp(-2j * np.pi * c * TAU ** 2))[None, :]) @ En) ** 2
        i, j = np.unravel_index(int(np.argmax(S)), S.shape)
        if best is None or S[i, j] > best[0]:
            best = (float(S[i, j]), ug[i], ng[j], c)
    _, u0, n0, c0 = best; du, dn, dc = 0.01, 0.05, 0.2
    for _ in range(3):
        us = u0 + du * np.linspace(-1, 1, 9); ns = n0 + dn * np.linspace(-1, 1, 9); cs = c0 + dc * np.linspace(-1, 1, 9); top = None
        for c in cs:
            Z = np.abs((np.exp(-2j * np.pi * np.outer(us, r)) * (y * np.exp(-2j * np.pi * c * TAU ** 2))[None, :]) @ np.exp(-2j * np.pi * np.outer(ns, TAU)).T) ** 2
            a, b = np.unravel_index(int(np.argmax(Z)), Z.shape)
            if top is None or Z[a, b] > top[0]:
                top = (float(Z[a, b]), us[a], ns[b], c)
        _, u0, n0, c0 = top; du, dn, dc = du / 4, dn / 4, dc / 4
    return u0


def cell(args):
    eta, kg_db = args; rng = np.random.default_rng([SEED, 20, int(eta * 10), int(kg_db * 10)]); amp = np.sqrt(10 ** (kg_db / 10) / K)
    arms = ['static_opt', 'u_turn_opt', 'u_turn_capped', 'cosine_base'] + (['u_turn_round'] if eta == 2.0 else [])
    R = {a: traj(a, eta) for a in arms}; err = {a: [] for a in arms}
    for _ in range(CFG['trials']):
        u = rng.uniform(-0.8, 0.8); nu = rng.uniform(-NU_MAX, NU_MAX); ph = rng.uniform(0, 2 * np.pi)
        w = (rng.standard_normal(K) + 1j * rng.standard_normal(K)) / np.sqrt(2)
        for a in arms:
            y = amp * np.exp(1j * (ph + 2 * np.pi * (nu * TAU + R[a] * u))) + w
            err[a].append(mle2(y, R[a])[0] - u)
    out = dict(eta=eta, kg_db=kg_db, arms={})
    for a in arms:
        e = np.array(err[a]); bs = [np.mean(e[rng.integers(0, len(e), len(e))] ** 2) for _ in range(1000)]
        out['arms'][a] = dict(mse=float(np.mean(e ** 2)), mse_ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], outliers=float(np.mean(np.abs(e) > 0.1)),
                              crb=crb_u(R[a], 10 ** (kg_db / 10)), r1_over_d2=r_q(R[a], 1) / D ** 2, err=[float(x) for x in e])
    return out


def cell_q2(_):
    rng = np.random.default_rng([SEED, 20, 2]); eta, kg_db = 5.0, 20.0; amp = np.sqrt(10 ** (kg_db / 10) / K)
    R = {a: traj(a, eta) for a in ('u_turn_opt', 'cheb3')}; err = {a: [] for a in R}
    for _ in range(CFG['q2_trials']):
        u = rng.uniform(-0.8, 0.8); nu = rng.uniform(-NU_MAX, NU_MAX); c = rng.uniform(-4, 4); ph = rng.uniform(0, 2 * np.pi)
        w = (rng.standard_normal(K) + 1j * rng.standard_normal(K)) / np.sqrt(2)
        for a in R:
            y = amp * np.exp(1j * (ph + 2 * np.pi * (nu * TAU + c * TAU ** 2 + R[a] * u))) + w
            err[a].append(mle3(y, R[a]) - u)
    return {a: dict(mse=float(np.mean(np.square(e))), outliers=float(np.mean(np.abs(e) > 0.1)), crb_q2=crb_u(R[a], 10 ** (kg_db / 10), 2), r2_over_d2=r_q(R[a], 2) / D ** 2, err=[float(x) for x in e]) for a, e in err.items()}


def gates():
    g = dict(r1_table={}, noiseless={})
    for eta in CFG['etas']:
        g['r1_table'][str(eta)] = {a: r_q(traj(a, eta), 1) / D ** 2 for a in ('static_opt', 'u_turn_opt', 'cosine_base')}
    rng = np.random.default_rng([SEED, 20, 99])
    for a, eta in (('u_turn_opt', 0.8), ('cosine_base', 0.8), ('u_turn_opt', 5.0), ('static_opt', 2.0)):
        r = traj(a, eta); e = []
        for _ in range(20):
            u = rng.uniform(-0.8, 0.8); nu = rng.uniform(-NU_MAX, NU_MAX); y = np.exp(2j * np.pi * (nu * TAU + r * u) + 1j)
            e.append(abs(mle2(y, r)[0] - u))
        g['noiseless'][f'{a}|{eta}'] = float(max(e))
    return g


def run(out):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    jobs = [(e, k) for e in CFG['etas'] for k in CFG['kg_db']] + [(e, 30.0) for e in (1.5, 5.0)]
    with get_context('spawn').Pool(WORKERS) as pool:
        r2 = pool.apply_async(cell_q2, (0,)); cells = pool.map(cell, jobs, chunksize=1); q2 = r2.get()
    (out / 'ma_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, K=K, D=D, nu_max=NU_MAX, seed=SEED), gates=gates(), cells=cells, q2=q2, wall_seconds=time.time() - t0)))
    print('done', round(time.time() - t0, 1))


def read(out):
    R = json.loads((out / 'ma_rows.json').read_text()); C = {(c['eta'], c['kg_db']): c['arms'] for c in R['cells']}; rng = np.random.default_rng(SEED + 20)
    db = lambda a, b: float(10 * np.log10(a / b)); mse = lambda eta, kg, a: C[(eta, kg)][a]['mse']
    def gain(eta, kg, a, b):                         # MSE of a over MSE of b in dB (positive: b better), paired bootstrap over trials
        ea, eb = np.array(C[(eta, kg)][a]['err']), np.array(C[(eta, kg)][b]['err']); n = len(ea)
        bs = [db(np.mean(ea[ii] ** 2), np.mean(eb[ii] ** 2)) for ii in (rng.integers(0, n, n) for _ in range(2000))]
        return dict(point=db(np.mean(ea ** 2), np.mean(eb ** 2)), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    res = dict(gates=R['gates'], table={f'{e}|{k}': {a: dict(rmse=float(np.sqrt(v['mse'])), outliers=v['outliers'], mse_over_crb_db=(db(v['mse'], v['crb']) if np.isfinite(v['crb']) and v['crb'] < 1e6 else None))
                                                 for a, v in arms.items()} for (e, k), arms in C.items()})
    o1 = {str(e): bool(mse(e, 20.0, 'u_turn_opt') < mse(e, 20.0, 'cosine_base') < mse(e, 20.0, 'static_opt')) for e in (0.8, 1.5, 2.0)}
    wall = gain(10.0, 16.0, 'u_turn_opt', 'u_turn_capped'); q2 = R['q2']; q2gain = db(q2['u_turn_opt']['mse'], q2['cheb3']['mse'])
    res['level1'] = dict(ordering=o1, wall_opt_over_capped_db=wall, q2_uturn_over_cheb3_db=q2gain, q2={a: dict(rmse=float(np.sqrt(v['mse'])), outliers=v['outliers'], r2_over_d2=v['r2_over_d2']) for a, v in q2.items()})
    res['level1']['pass'] = bool(all(o1.values()) and wall['point'] > 0 and q2gain > 0)
    g_static = {str(e): gain(e, 20.0, 'static_opt', 'u_turn_opt') for e in (1.5, 2.0)}; g_cos = {str(e): gain(e, 20.0, 'cosine_base', 'u_turn_opt') for e in (1.5, 2.0)}
    g_round = gain(2.0, 20.0, 'cosine_base', 'u_turn_round')
    res['level2'] = dict(gain_over_static_db=g_static, gain_over_cosine_db=g_cos, wall_db=wall['point'], rounded_gain_over_cosine_db=g_round,
                         c1=bool(all(v['point'] >= 7.5 for v in g_static.values()) and all(v['point'] >= 1.5 for v in g_cos.values())), c2=bool(wall['point'] >= 3.0), c3=bool(g_round['point'] >= 1.0))
    res['level2']['pass'] = bool(res['level2']['c1'] and res['level2']['c2'] and res['level2']['c3'])
    res['gain_over_cosine_all_db'] = {f'{e}|{k}': round(db(mse(e, k, 'cosine_base'), mse(e, k, 'u_turn_opt')), 2) for e in CFG['etas'] for k in CFG['kg_db']}
    res['capped_over_cosine_all_db'] = {f'{e}|{k}': round(db(mse(e, k, 'cosine_base'), mse(e, k, 'u_turn_capped')), 2) for e in CFG['etas'] for k in CFG['kg_db']}
    res['verdict'] = 'PASS' if res['level1']['pass'] and res['level2']['pass'] else 'KILL_DIRECTION' if not res['level1']['pass'] else 'FAIL_QUANTITATIVE'
    (out / 'ma_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read')); ap.add_argument('--out', default='out_r3b20'); a = ap.parse_args()
    if a.mode == 'smoke':
        print(json.dumps(gates(), indent=1)); CFG['trials'] = 30; t0 = time.process_time(); c = cell((2.0, 20.0)); print('cpu/trial', (time.process_time() - t0) / 30)
        print({k: (round(float(np.sqrt(v['mse'])), 4), round(float(np.sqrt(v['crb'])), 4), v['outliers']) for k, v in c['arms'].items()})
        CFG['q2_trials'] = 4; t0 = time.process_time(); q = cell_q2(0); print('cpu/q2 trial', (time.process_time() - t0) / 4, {k: round(v['r2_over_d2'], 4) for k, v in q.items()})
    else:
        dict(run=run, read=read)[a.mode](HERE / a.out)
