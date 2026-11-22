#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 check for card I-20261122-l21 (2026-11-22, runner l, claude-fable-5.2): one movable
antenna, unknown phase, frequency offset AND linear frequency drift (q = 2).  Three parts:
  theory : fine-grid values of the card's trajectories; every link of the card's global bound on random feasible
           trajectories; counterexample search (full-speed zigzags, free start, up to 8 turns) around eta_0 and at 5, 10.
  noise  : global 3-D grid search plus refinement (no true initial values), all arms on the same frames and noise.
  read   : the card's direction / quantitative vetoes.
Source: l2_r3_ma.py (model, mle3, crb; imported), l2_r3_ma_opt.py (bang_traj; imported).  The parent's script has no q = 2
trajectories apart from the old three-crossing one.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch23.md.   python l2_r3_ma_q2.py smoke|theory|noise|read --out out_r3b23
"""
import argparse, json, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r3_ma as ma  # noqa: E402
from l2_r3_ma_opt import bang_traj  # noqa: E402

SEED_SMOKE, SEED_RUN, WORKERS = 2026112214, 2026112215, 7
TAU, K, D = ma.TAU, ma.K, ma.D
B2 = np.sqrt(2) - 1
CELLS = [(0.8, 24.0), (2.0, 24.0), (5.0, 20.0), (10.0, 14.0), (10.0, 16.0), (10.0, 20.0), (10.0, 24.0)]
TRIALS = 120


def shapes(tau, eta):
    """Normalised trajectories (range 1) on the time grid tau in [-1/2, 1/2]."""
    s = 2 * tau; out = dict(v_shape=np.clip(eta * (0.25 - np.abs(tau)), -0.5, 0.5), cosine=0.5 * min(1.0, eta / np.pi) * np.cos(2 * np.pi * tau),
                            sine3=min(0.5, eta / (3 * np.pi)) * np.sin(3 * np.pi * tau))
    if eta <= 1 / B2:
        out['zigzag2'] = (eta / 2) * np.sign(s) * (np.abs(s) - 2 * np.maximum(np.abs(s) - B2, 0))
    for name, a in (('three_shift', np.sqrt(max(1 / 8 - 1 / (24 * eta ** 2), 0))), ('three_cheb', 1 / np.sqrt(8))):
        if a >= 1 / eta and a + 1 / (2 * eta) <= 0.5 + 1e-12:
            r = np.full(len(tau), -0.5)
            for tj, st in zip((-a, 0.0, a), (1.0, -1.0, 1.0)):
                r = r + st * np.clip((tau - tj) * eta + 0.5, 0.0, 1.0)
            out[name] = r
    return out


def rq(tau, r, q=2):
    A = np.vander(tau, q + 1, increasing=True); Q, _ = np.linalg.qr(A); res = r - Q @ (Q.T @ r)
    return float(np.mean(res ** 2))


def b_closed(eta):
    return 0.25 - 1 / (2 * eta)


def bound(eta):
    S = 2 / eta + 1 / (eta + 8); E = min(0.5, 1 / (2 * S))
    return E ** 2 - 4 * S * E ** 3 / 3


# ------------------------------------------------------------------ theory
def theory(out, seed=SEED_RUN):
    from scipy.optimize import linprog, minimize
    out.mkdir(parents=True, exist_ok=True); rng = np.random.default_rng([seed, 1]); t0 = time.time(); res = dict(_argv=sys.argv, _config=dict(seed=seed))
    fine = (np.arange(200000) + 0.5) / 200000 - 0.5
    res['values'] = {str(eta): dict({k: rq(fine, v) for k, v in shapes(fine, eta).items()}, low_speed_closed=(eta ** 2 * (17 - 12 * np.sqrt(2)) / 3 if eta <= 1 / B2 else None),
                                    three_closed=b_closed(eta), bound=bound(eta)) for eta in (0.8, 1.5, 2.0, 3.0, 5.0, 10.0)}
    # (ii) every link of the bound on random feasible trajectories
    n = 800; tg = (np.arange(n) + 0.5) / n - 0.5; A2 = np.vander(tg, 3, increasing=True); worst = dict(r_le_ie2=-1.0, ie2_le_chain=-1.0, E_le_cap=-1.0, chain_le_bound=-1.0); tight = 0.0; chk = {}
    for eta in (0.8, 2.0, 3.0, 5.0, 10.0):
        S = 2 / eta + 1 / (eta + 8); cands = list(shapes(tg, eta).values())
        for i in range(200):
            nsw = int(rng.integers(0, 11)); x0 = np.r_[rng.uniform(-0.5, 0.5), np.sort(rng.uniform(-0.5, 0.5, nsw))]; r = bang_traj(x0, eta * (1.0 if i % 4 else rng.uniform(0.3, 1.0)), int(rng.choice([-1, 1])), n)[1]; cands.append(r)
        v = dict(a=-1.0, b=-1.0, c=-1.0, d=-1.0); best = 0.0
        for r in cands:
            Aub = np.r_[np.c_[-A2, -np.ones(n)], np.c_[A2, -np.ones(n)]]; o = linprog([0, 0, 0, 1], A_ub=Aub, b_ub=np.r_[-r, r], bounds=[(None, None)] * 3 + [(0, None)], method='highs')
            E = float(o.x[3]); e = r - A2 @ o.x[:3]; ie2 = float(np.mean(e ** 2)); R = rq(tg, r); chain = E ** 2 - 4 * S * E ** 3 / 3
            v = dict(a=max(v['a'], R - ie2), b=max(v['b'], ie2 - chain), c=max(v['c'], E - min(0.5, 1 / (2 * S))), d=max(v['d'], chain - bound(eta))); best = max(best, R / bound(eta))
        chk[str(eta)] = dict(viol_R2_minus_ie2=v['a'], viol_ie2_minus_chain=v['b'], viol_E_minus_cap=v['c'], viol_chain_minus_bound=v['d'], max_R2_over_bound=best, n_traj=len(cands))
        worst = dict(r_le_ie2=max(worst['r_le_ie2'], v['a']), ie2_le_chain=max(worst['ie2_le_chain'], v['b']), E_le_cap=max(worst['E_le_cap'], v['c']), chain_le_bound=max(worst['chain_le_bound'], v['d'])); tight = max(tight, best)
        print('bound', eta, chk[str(eta)], flush=True)
    res['bound_check'] = dict(per_eta=chk, worst_violation=worst, grid_tolerance=2.5 / n, holds=bool(max(worst.values()) <= 2.5 / n), max_R2_over_bound=tight)
    # (iii) counterexample search: full-speed zigzags, free start and initial direction, 0..8 turns
    srch = {}
    for eta in (3.0, 3.2, 3.291, 3.4, 3.6, 4.0, 5.0, 10.0):
        best = (0.0, None, None, None)
        for nsw in range(0, 9):
            for _ in range(160):
                x0 = np.r_[rng.uniform(-0.5, 0.5), np.sort(rng.uniform(-0.5, 0.5, nsw))]; d0 = int(rng.choice([-1, 1]))
                o = minimize(lambda x: -rq(*bang_traj(x, eta, d0, 300)), x0, method='Nelder-Mead', options=dict(xatol=1e-5, fatol=1e-10, maxiter=400))
                val = rq(*bang_traj(o.x, eta, d0, 2000))
                if val > best[0]:
                    best = (val, [float(z) for z in o.x], d0, nsw)
        fine_val = rq(*bang_traj(np.array(best[1]), eta, best[2], 200000)); sh = shapes(fine, eta)
        srch[str(eta)] = dict(best_found_fine_grid=fine_val, best_params=best[1], best_d0=best[2], best_turns=best[3], three_shift=(rq(fine, sh['three_shift']) if 'three_shift' in sh else None),
                              three_closed=b_closed(eta), bound=bound(eta), excess_over_three_closed=fine_val / b_closed(eta) - 1, best_over_bound=fine_val / bound(eta))
        print('search', eta, {k: (round(v, 7) if isinstance(v, float) else v) for k, v in srch[str(eta)].items() if k != 'best_params'}, flush=True)
    res['search'] = srch; res['wall_seconds'] = time.time() - t0
    (out / 'q2_theory.json').write_text(json.dumps(res, indent=1)); print('theory done', round(time.time() - t0))


# ------------------------------------------------------------------ noise
def cell(args):
    eta, kg_db, seed, trials = args; rng = np.random.default_rng([seed, int(eta * 10), int(kg_db * 10)]); amp = np.sqrt(10 ** (kg_db / 10) / K)
    R = {a: D * r for a, r in shapes(TAU, eta).items()}; err = {a: [] for a in R}
    for _ in range(trials):
        u = rng.uniform(-0.8, 0.8); nu = rng.uniform(-ma.NU_MAX, ma.NU_MAX); c = rng.uniform(-4, 4); ph = rng.uniform(0, 2 * np.pi)
        w = (rng.standard_normal(K) + 1j * rng.standard_normal(K)) / np.sqrt(2)
        for a in R:
            y = amp * np.exp(1j * (ph + 2 * np.pi * (nu * TAU + c * TAU ** 2 + R[a] * u))) + w; err[a].append(ma.mle3(y, R[a]) - u)
    return dict(eta=eta, kg_db=kg_db, arms={a: dict(err=[float(x) for x in e], r2_over_d2=ma.r_q(R[a], 2) / D ** 2, crb=ma.crb_u(R[a], 10 ** (kg_db / 10), 2)) for a, e in err.items()})


def noise(out, seed=SEED_RUN, trials=TRIALS):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time(); p0 = time.process_time()
    with get_context('spawn').Pool(WORKERS) as pool:
        cells = pool.map(cell, [(e, k, seed, trials) for e, k in CELLS], chunksize=1)
    import resource
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'q2_noise_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(seed=seed, trials=trials, cells=CELLS, K=K, D=D, u_grid_step=0.01, nu_grid_step=0.05, c_grid_step=0.2), cells=cells,
                                                           core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0)))
    print('noise done', round(time.time() - t0), 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read(out):
    T = json.loads((out / 'q2_theory.json').read_text()); N = json.loads((out / 'q2_noise_rows.json').read_text()); rng = np.random.default_rng(SEED_RUN + 1)
    C = {(c['eta'], c['kg_db']): c['arms'] for c in N['cells']}; db = lambda a, b: float(10 * np.log10(a / b))
    def gain(key, base, new):                 # MSE(base) / MSE(new) in dB, paired bootstrap over frames
        ea, eb = np.array(C[key][base]['err']), np.array(C[key][new]['err']); n = len(ea)
        bs = [db(np.mean(ea[ii] ** 2), np.mean(eb[ii] ** 2)) for ii in (rng.integers(0, n, n) for _ in range(2000))]
        return dict(point=db(np.mean(ea ** 2), np.mean(eb ** 2)), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    tab = {f'{e}|{k}': {a: dict(rmse=float(np.sqrt(np.mean(np.square(v['err'])))), outliers=int(np.sum(np.abs(v['err']) > 0.1)), crb_rmse=float(np.sqrt(v['crb'])), r2_over_d2=v['r2_over_d2']) for a, v in arms.items()} for (e, k), arms in C.items()}
    res = dict(table=tab, core_hours_noise=N['core_hours'], bound_holds=T['bound_check']['holds'], bound_worst_violation=T['bound_check']['worst_violation'], search={k: dict(excess=v['excess_over_three_closed'], turns=v['best_turns'], best=v['best_found_fine_grid'], over_bound=v['best_over_bound']) for k, v in T['search'].items()})
    low = {}
    for key in ((0.8, 24.0), (2.0, 24.0)):
        mse = {a: float(np.mean(np.square(v['err']))) for a, v in C[key].items()}; base = min((a for a in mse if a != 'zigzag2'), key=lambda a: mse[a])
        low[f'{key[0]}'] = dict(best_baseline=base, gain_db=gain(key, base, 'zigzag2'), mse=mse)
    res['low_speed'] = low
    g5 = gain((5.0, 20.0), 'three_cheb', 'three_shift'); res['eta5_shift_over_cheb_db'] = g5; res['eta5_three_over_vshape_db'] = gain((5.0, 20.0), 'v_shape', 'three_shift')
    res['eta10_three_over_sine3_db'] = {str(k): gain((10.0, k), 'sine3', 'three_shift') for k in (14.0, 16.0, 20.0, 24.0)}
    ex10 = T['search']['10.0']['excess_over_three_closed']
    d1 = bool(ex10 <= 2e-3); d2 = bool(any(v['gain_db']['point'] > 0 for v in low.values()))
    q1 = bool(all(v['gain_db']['point'] >= 1.0 for v in low.values())); q2 = bool(g5['point'] >= -0.5)
    res['direction'] = dict(no_counterexample_at_eta10=d1, zigzag_beats_best_baseline_in_a_low_speed_cell=d2, passed=bool(d1 and d2 and res['bound_holds']))
    res['quantitative'] = dict(low_speed_gain_ge_1db_both=q1, eta5_shift_not_worse_than_cheb_by_half_db=q2, passed=bool(q1 and q2))
    res['local_design_only_at_eta10_low_snr'] = bool(any(res['eta10_three_over_sine3_db'][k]['point'] < 0 for k in ('14.0', '16.0')))
    res['verdict'] = 'PASS' if res['direction']['passed'] and res['quantitative']['passed'] else 'KILL_DIRECTION' if not res['direction']['passed'] else 'DOWNGRADE_QUANTITATIVE'
    (out / 'q2_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'theory', 'noise', 'read')); ap.add_argument('--out', default='out_r3b23'); a = ap.parse_args(); o = HERE / a.out
    if a.mode == 'smoke':
        fine = (np.arange(200000) + 0.5) / 200000 - 0.5
        for eta in (0.8, 2.0, 3.0, 5.0, 10.0):
            print(eta, {k: round(rq(fine, v), 6) for k, v in shapes(fine, eta).items()}, 'low closed', round(eta ** 2 * (17 - 12 * np.sqrt(2)) / 3, 6), 'three closed', round(b_closed(eta), 6), 'bound', round(bound(eta), 5),
                  'max |r|', {k: round(float(np.abs(v).max()), 3) for k, v in shapes(fine, eta).items()}, 'max slope/eta', {k: round(float(np.abs(np.diff(v)).max() * 200000 / eta), 3) for k, v in shapes(fine, eta).items()})
        t0 = time.process_time(); c = cell((5.0, 20.0, SEED_SMOKE, 6)); print('cpu per frame (all arms)', round((time.process_time() - t0) / 6, 2), {a: (round(float(np.sqrt(np.mean(np.square(v['err'])))), 4), round(float(np.sqrt(v['crb'])), 4)) for a, v in c['arms'].items()})
    else:
        dict(theory=theory, noise=noise, read=read)[a.mode](o)
