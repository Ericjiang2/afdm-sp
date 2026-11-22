#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 check for card I-20261122-l08 (2026-11-22, runner l, claude-fable-5.2).
Two known markers at the packet ends (preamble + postamble): per-path Doppler from the marker samples alone, true delays
given, real 8-path channels of the project generator (scenarios U and G), unknown data leaking into the marker windows.
New code (numpy); only the channel truth (delays, Dopplers, gains) is read through the project harness.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch6.md.
  python l2_r3_marker.py smoke|run|read --out out_r3b6

Packet (samples): [marker A, L][guard G][prefix 102 + data 1024][guard G][marker B, L]; silence before and after.
Path i: gain g_i, integer delay l_i, Doppler nu_i bins (phase exp(j 2 pi nu_i t / 1024), t = absolute sample index).
"""
import argparse, json, os, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SEED, WORKERS, N, CP, LMAX = 20261122, 12, 1024, 102, 102
CFG = dict(frames=[50000, 50200], scenarios=['U', 'G'], snrs_db=[4.0, 6.0],
           arms=[dict(name='L256_guard', L=256, G=102, post=True), dict(name='L256_noguard', L=256, G=0, post=True),
                 dict(name='L128_guard', L=128, G=102, post=True), dict(name='L128_noguard', L=128, G=0, post=True),
                 dict(name='front512_only', L=512, G=102, post=False)],          # same marker energy as L256 x 2, one end only
           grid=np.arange(-2.2, 2.2001, 0.02).tolist(), sage_iters=4, cycle_err=0.30)


def estimate(y, U, tw, grid, iters):
    """y: window samples; U: (P, T) marker replicas per path on the window; tw: absolute sample index of each window
    sample.  SAGE over paths with a full Doppler grid each pass, then a fine local grid.  Returns nu_hat, g_hat."""
    P = U.shape[0]; grid = np.asarray(grid)
    E = np.exp(-2j * np.pi * np.outer(grid, tw) / N)                       # (G, T)
    en = np.sum(np.abs(U) ** 2, axis=1)
    nu = np.zeros(P); g = np.zeros(P, complex)
    comp = lambda i, v, gi: gi * U[i] * np.exp(2j * np.pi * v * tw / N)
    res = y.copy()
    for it in range(iters):
        for i in range(P):
            res = res + comp(i, nu[i], g[i])
            c = E @ (np.conj(U[i]) * res); k = int(np.argmax(np.abs(c)))
            nu[i] = grid[k]; g[i] = c[k] / en[i]
            res = res - comp(i, nu[i], g[i])
    for i in range(P):                                                       # fine pass, +-0.02 in 0.001 steps
        res = res + comp(i, nu[i], g[i])
        fine = nu[i] + np.arange(-0.02, 0.0201, 0.001)
        c = np.exp(-2j * np.pi * np.outer(fine, tw) / N) @ (np.conj(U[i]) * res); k = int(np.argmax(np.abs(c)))
        nu[i] = fine[k]; g[i] = c[k] / en[i]
        res = res - comp(i, nu[i], g[i])
    return nu, g


def one(l, nu, g, snr_db, arm, rng):
    L, G = arm['L'], arm['G']
    m = lambda: np.exp(2j * np.pi * rng.uniform(size=L))
    d = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
    body = np.r_[d[-CP:], d]
    if arm['post']:
        s_mark = np.r_[m(), np.zeros(G + CP + N + G), m()]; s_data = np.r_[np.zeros(L + G), body, np.zeros(G + L)]
        D = L + G + CP + N + G; wins = [np.arange(0, L + LMAX), np.arange(D, D + L + LMAX)]
    else:
        s_mark = np.r_[m(), np.zeros(G + CP + N)]; s_data = np.r_[np.zeros(L + G), body]
        wins = [np.arange(0, L + LMAX)]
    T = len(s_mark) + LMAX; t = np.arange(T); tw = np.concatenate(wins)
    def through(s, li, vi, gi):
        out = np.zeros(T, complex); out[li:li + len(s)] = s
        return gi * out * np.exp(2j * np.pi * vi * t / N)
    sig = sum(through(s_mark + s_data, li, vi, gi) for li, vi, gi in zip(l, nu, g))
    s2 = float(np.sum(np.abs(g) ** 2)) / 10 ** (snr_db / 10)
    y = sig + np.sqrt(s2 / 2) * (rng.standard_normal(T) + 1j * rng.standard_normal(T))
    U = np.zeros((len(l), len(tw)), complex)
    for i, li in enumerate(l):
        rep = np.zeros(T, complex); rep[li:li + len(s_mark)] = s_mark; U[i] = rep[tw]
    nh, _ = estimate(y[tw], U, tw, CFG['grid'], CFG['sage_iters'])
    p = np.abs(g) ** 2; err = np.abs(nh - nu)
    return dict(mae_w=float(np.sum(p * err) / p.sum()), cyc_w=float(np.sum(p * (err > CFG['cycle_err'])) / p.sum()),
                mae_w_nocyc=float(np.sum(p * err * (err <= CFG['cycle_err'])) / max(np.sum(p * (err <= CFG['cycle_err'])), 1e-12)),
                n_cyc=int(np.sum(err > CFG['cycle_err'])))


def one_hybrid(l, nu, g, snr_db, arm, rng, return_estimate=False):
    """Markers of length L at both ends plus a superimposed pilot of power share rho over the prefix + data segment.
    The receiver uses every sample of the packet: known signal = markers + superimposed pilot, unknown data = interference.
    Samples are whitened with the nominal per-region noise level (markers: sigma2; data segment: sigma2 + (1 - rho) * total path power)."""
    L, G, rho = arm['L'], arm['G'], arm['rho']
    m = lambda: np.exp(2j * np.pi * rng.uniform(size=L)) if L else np.zeros(0, complex)
    d = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2); sp = np.exp(2j * np.pi * rng.uniform(size=N))
    body_d = np.sqrt(1 - rho) * np.r_[d[-CP:], d]; body_p = np.sqrt(rho) * np.r_[sp[-CP:], sp]
    s_known = np.r_[m(), np.zeros(G), body_p, np.zeros(G), m()]; s_data = np.r_[np.zeros(L + G), body_d, np.zeros(G + L)]
    T = len(s_known) + LMAX; t = np.arange(T)
    def through(s, li, vi, gi):
        out = np.zeros(T, complex); out[li:li + len(s)] = s
        return gi * out * np.exp(2j * np.pi * vi * t / N)
    sig = sum(through(s_known + s_data, li, vi, gi) for li, vi, gi in zip(l, nu, g))
    ptot = float(np.sum(np.abs(g) ** 2)); s2 = ptot / 10 ** (snr_db / 10)
    y = sig + np.sqrt(s2 / 2) * (rng.standard_normal(T) + 1j * rng.standard_normal(T))
    nv = np.full(T, s2); nv[L + G:L + G + CP + N + LMAX] = s2 + (1 - rho) * ptot
    wgt = 1 / np.sqrt(nv)
    U = np.zeros((len(l), T), complex)
    for i, li in enumerate(l):
        U[i, li:li + len(s_known)] = s_known
    nh, _ = estimate(y * wgt, U * wgt[None, :], t, CFG['grid'], CFG['sage_iters'])
    if return_estimate:
        return nh
    p = np.abs(g) ** 2; err = np.abs(nh - nu)
    return dict(mae_w=float(np.sum(p * err) / p.sum()), cyc_w=float(np.sum(p * (err > CFG['cycle_err'])) / p.sum()),
                mae_w_nocyc=float(np.sum(p * err * (err <= CFG['cycle_err'])) / max(np.sum(p * (err <= CFG['cycle_err'])), 1e-12)),
                n_cyc=int(np.sum(err > CFG['cycle_err'])))


HYB = dict(frames=[52000, 52200], scenarios=['U', 'G'], snrs_db=[4.0, 6.0],
           arms=[dict(name='sp10_only', L=0, G=0, rho=0.10), dict(name='sp30_only', L=0, G=0, rho=0.30),
                 dict(name='L64_sp10', L=64, G=0, rho=0.10), dict(name='L128_sp10', L=128, G=0, rho=0.10),
                 dict(name='L256_sp10', L=256, G=0, rho=0.10), dict(name='L128_sp05', L=128, G=0, rho=0.05),
                 dict(name='L128_nosp', L=128, G=0, rho=0.0)])


def job_hybrid(frame):
    import l2_r2_batch1 as r2
    C = r2.setup(); stage3, ctx = C['stage3'], C['ctx']; out = dict(frame=frame, cells={})
    for si, scen in enumerate(HYB['scenarios']):
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, scen, 300), 300, 500)
        l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
        for snr in HYB['snrs_db']:
            for ai, arm in enumerate(HYB['arms']):
                rng = np.random.default_rng([SEED, frame, si, int(snr * 10), 100 + ai])
                out['cells'][f"{scen}|{snr}|{arm['name']}"] = one_hybrid(l, nu, g, snr, arm, rng)
    return out


def run_hybrid(out):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        rows = pool.map(job_hybrid, list(range(*HYB['frames'])))
    (out / 'hybrid_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=HYB, rows=rows, wall_seconds=time.time() - t0)))
    print('done', round(time.time() - t0, 1))


def read_hybrid(out):
    R = json.loads((out / 'hybrid_rows.json').read_text()); rows = R['rows']; n = len(rows); rng = np.random.default_rng(SEED + 9); res = dict(frames=n, cells={})
    for key in rows[0]['cells']:
        v = np.array([r['cells'][key]['mae_w'] for r in rows]); c = np.array([r['cells'][key]['cyc_w'] for r in rows]); nc = np.array([r['cells'][key]['mae_w_nocyc'] for r in rows])
        bs = [v[rng.integers(0, n, n)].mean() for _ in range(4000)]
        res['cells'][key] = dict(mae_w_mean=float(v.mean()), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], mae_w_median=float(np.median(v)),
                                 cycle_power_frac=float(c.mean()), mae_w_no_cycle=float(nc.mean()))
    crit = {}
    for arm in ('L64_sp10', 'L128_sp10', 'L256_sp10', 'L128_sp05', 'L128_nosp', 'sp10_only', 'sp30_only'):
        ks = [f'{s}|{snr}|{arm}' for s in HYB['scenarios'] for snr in HYB['snrs_db']]
        crit[arm] = dict(all_upper_below_004=bool(all(res['cells'][k]['ci95'][1] < 0.04 for k in ks)), worst_mean=float(max(res['cells'][k]['mae_w_mean'] for k in ks)),
                         worst_cycle_power=float(max(res['cells'][k]['cycle_power_frac'] for k in ks)))
    res['criterion'] = crit
    res['verdict'] = 'PASS' if crit['L128_sp10']['all_upper_below_004'] and not crit['L128_nosp']['all_upper_below_004'] else 'KILL' if not crit['L128_sp10']['all_upper_below_004'] else 'NO_CONTRAST'
    (out / 'hybrid_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def job(frame):
    import l2_r2_batch1 as r2
    C = r2.setup(); stage3, ctx = C['stage3'], C['ctx']; out = dict(frame=frame, cells={})
    for si, scen in enumerate(CFG['scenarios']):
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, scen, 300), 300, 500)
        l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
        out.setdefault('gain_power', {})[scen] = float(np.sum(np.abs(g) ** 2))
        for snr in CFG['snrs_db']:
            for ai, arm in enumerate(CFG['arms']):
                rng = np.random.default_rng([SEED, frame, si, int(snr * 10), ai])
                out['cells'][f"{scen}|{snr}|{arm['name']}"] = one(l, nu, g, snr, arm, rng)
    return out


def selftest():
    """Single path, power 1/8, no data leakage possible (guard), 6 dB: local accuracy against the closed form in the card."""
    rng = np.random.default_rng([SEED, 1]); arm = CFG['arms'][0]; errs = []
    for _ in range(300):
        nu = rng.uniform(-1.6, 1.6); g = np.sqrt(1 / 8) * np.exp(2j * np.pi * rng.uniform())
        L, G = arm['L'], arm['G']; D = L + G + CP + N + G
        s_mark = np.r_[np.exp(2j * np.pi * rng.uniform(size=L)), np.zeros(D - L), np.exp(2j * np.pi * rng.uniform(size=L))]
        T = len(s_mark); t = np.arange(T); tw = np.r_[np.arange(0, L), np.arange(D, D + L)]
        y = g * s_mark * np.exp(2j * np.pi * nu * t / N) + np.sqrt(10 ** -0.6 / 2) * (rng.standard_normal(T) + 1j * rng.standard_normal(T))
        nh, _ = estimate(y[tw], s_mark[tw][None, :], tw, CFG['grid'], 1); errs.append(nh[0] - nu)
    errs = np.array(errs); ok = np.abs(errs) < CFG['cycle_err']
    L, D = arm['L'], arm['L'] + 2 * arm['G'] + CP + N
    crb = N / (2 * np.pi) / np.sqrt(L * (1 / 8) * 10 ** 0.6 * (D ** 2 + (L ** 2 - 1) / 3))
    return dict(rmse_no_cycle=float(np.sqrt(np.mean(errs[ok] ** 2))), crb_sigma=float(crb), cycle_errors=int((~ok).sum()), n=len(errs))


def run(out):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        rows = pool.map(job, list(range(*CFG['frames'])))
    (out / 'marker_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=CFG, selftest=selftest(), rows=rows, wall_seconds=time.time() - t0)))
    print('done', round(time.time() - t0, 1))


def read(out):
    R = json.loads((out / 'marker_rows.json').read_text()); rows = R['rows']; n = len(rows); rng = np.random.default_rng(SEED + 6); res = dict(frames=n, selftest=R['selftest'], cells={})
    for key in rows[0]['cells']:
        v = np.array([r['cells'][key]['mae_w'] for r in rows]); c = np.array([r['cells'][key]['cyc_w'] for r in rows]); nc = np.array([r['cells'][key]['mae_w_nocyc'] for r in rows])
        bs = [v[rng.integers(0, n, n)].mean() for _ in range(4000)]
        res['cells'][key] = dict(mae_w_mean=float(v.mean()), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], mae_w_median=float(np.median(v)),
                                 cycle_power_frac=float(c.mean()), frames_with_cycle_error=float(np.mean([r['cells'][key]['n_cyc'] > 0 for r in rows])), mae_w_no_cycle=float(nc.mean()))
    best = {}
    for arm in ('L256_guard', 'L256_noguard'):
        ks = [f'{s}|{snr}|{arm}' for s in CFG['scenarios'] for snr in CFG['snrs_db']]
        best[arm] = dict(all_upper_below_004=bool(all(res['cells'][k]['ci95'][1] < 0.04 for k in ks)), all_lower_above_004=bool(all(res['cells'][k]['ci95'][0] > 0.04 for k in ks)),
                         worst_mean=float(max(res['cells'][k]['mae_w_mean'] for k in ks)))
    res['criterion'] = best
    res['verdict'] = 'PASS' if any(b['all_upper_below_004'] for b in best.values()) else 'KILL' if all(b['all_lower_above_004'] for b in best.values()) else 'UNDETERMINED'
    (out / 'marker_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read', 'hybrid', 'readhybrid')); ap.add_argument('--out', default='out_r3b6'); a = ap.parse_args()
    if a.mode == 'smoke':
        print(json.dumps(selftest())); t0 = time.process_time(); r = job(50000); print('cpu per frame', time.process_time() - t0, {k: round(v['mae_w'], 4) for k, v in r['cells'].items()})
    else:
        dict(run=run, read=read, hybrid=run_hybrid, readhybrid=read_hybrid)[a.mode](HERE / a.out)
