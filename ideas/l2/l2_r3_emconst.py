#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 check for card I-20261122-l11 (2026-11-22, runner l, claude-fable-5.2).
Block-static OFDM, one known pilot symbol and M unknown data symbols; pilot-initialised EM for the channel impulse
response; how much the unknown data help depends on the rotational symmetry of the constellation.  New numpy code.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch11.md.
  python l2_r3_emconst.py smoke|run|read --out out_r3b11
"""
import argparse, json, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SEED, WORKERS = 20261122, 12
N, L, M, ITERS = 1024, 103, 100, 20
CFG = dict(frames=40, snrs_db=[3.0], geoms=['A1', 'A8', 'B', 'C'], extra=[('A8', 0.0), ('A8', 6.0)],
           consts=['qam16', 'psk16', 'apsk_dvb', 'apsk_tight', 'apsk_4fold'])
F = np.exp(-2j * np.pi * np.outer(np.arange(N), np.arange(L)) / N)          # H = F h


def constellation(name):
    if name == 'qam16':
        a = np.array([-3, -1, 1, 3]); c = (a[:, None] + 1j * a[None, :]).ravel()
    elif name == 'psk16':
        c = np.exp(2j * np.pi * np.arange(16) / 16)
    else:
        ratio = 2.6 if name == 'apsk_dvb' else 1.8
        inner = np.exp(1j * (np.pi / 4 + np.pi / 2 * np.arange(4)))
        if name == 'apsk_4fold':                                           # 3 outer points per quadrant at 45 deg and 45 +- 18 deg
            ang = np.concatenate([np.pi / 4 + np.pi / 2 * q + np.deg2rad([-18.0, 0.0, 18.0]) for q in range(4)])
        else:                                                              # uniform 30-degree spacing
            ang = np.pi / 12 + 2 * np.pi * np.arange(12) / 12
        c = np.r_[inner, ratio * np.exp(1j * ang)]
    return c / np.sqrt(np.mean(np.abs(c) ** 2))


def channel(geom, rng):
    h = np.zeros(L, complex)
    if geom == 'A1':
        h[int(rng.integers(0, L))] = np.exp(2j * np.pi * rng.uniform())
    elif geom == 'A8':
        idx = rng.choice(L, 8, replace=False); g = rng.standard_normal(8) + 1j * rng.standard_normal(8); h[idx] = g / np.linalg.norm(g)
    else:
        l0, l1 = (0, 35) if geom == 'B' else (40, 65)
        h[l0] = np.sqrt(0.9) * np.exp(2j * np.pi * rng.uniform()); h[l1] = np.sqrt(0.1) * np.exp(2j * np.pi * rng.uniform())
    return h


def em(Y, yp, xp, c, s2):
    b0 = yp * np.conj(xp); h = F.conj().T @ b0 / N; h_pilot = h.copy(); c2 = np.abs(c) ** 2
    for _ in range(ITERS):
        H = F @ h
        D = -np.abs(Y[:, :, None] - H[:, None, None] * c[None, None, :]) ** 2 / s2
        D -= D.max(axis=2, keepdims=True); W = np.exp(D); W /= W.sum(axis=2, keepdims=True)
        mu1 = W @ c; mu2 = W @ c2
        a = mu2.sum(axis=1) + 1.0; b = (Y * np.conj(mu1)).sum(axis=1) + b0
        h = np.linalg.solve(F.conj().T @ (a[:, None] * F), F.conj().T @ b)
    return h_pilot, h


def job(args):
    geom, snr, fr = args
    rng = np.random.default_rng([SEED, CFG['geoms'].index(geom), int(snr * 10), fr]); s2 = 10 ** (-snr / 10)
    h = channel(geom, rng); H = F @ h; out = dict(geom=geom, snr=snr, frame=fr, mse={})
    xp = np.exp(2j * np.pi * rng.uniform(size=N))
    wp = np.sqrt(s2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    Wn = np.sqrt(s2 / 2) * (rng.standard_normal((N, M)) + 1j * rng.standard_normal((N, M)))
    sel = rng.integers(0, 16, (N, M))                                      # same symbol indices and noise for every constellation
    for name in CFG['consts']:
        c = constellation(name); X = c[sel]
        hp, he = em(H[:, None] * X + Wn, H * xp + wp, xp, c, s2)
        hg = np.linalg.solve(F.conj().T @ ((np.sum(np.abs(X) ** 2, axis=1) + 1.0)[:, None] * F),
                             F.conj().T @ (((H[:, None] * X + Wn) * np.conj(X)).sum(axis=1) + (H * xp + wp) * np.conj(xp)))
        rec = dict(pilot=float(np.sum(np.abs(hp - h) ** 2)), em=float(np.sum(np.abs(he - h) ** 2)), genie=float(np.sum(np.abs(hg - h) ** 2)))
        if geom == 'C':
            rec['mirror_tap_pow'] = float(np.abs(he[15]) ** 2); rec['target_err'] = float(np.abs(he[65] - h[65]) ** 2)
        out['mse'][name] = rec
    return out


def kappa4(c):
    return float(abs(np.mean(c ** 4)) ** 2)


def run(out):
    out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    jobs = [(g, s, f) for g in CFG['geoms'] for s in CFG['snrs_db'] for f in range(CFG['frames'])] + [(g, s, f) for g, s in CFG['extra'] for f in range(CFG['frames'])]
    with get_context('spawn').Pool(WORKERS) as pool:
        rows = pool.map(job, jobs)
    consts = {n: dict(mu4=float(np.mean(np.abs(constellation(n)) ** 4)), kappa4_sq=kappa4(constellation(n))) for n in CFG['consts']}
    (out / 'emconst_rows.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, N=N, L=L, M=M, iters=ITERS, seed=SEED), constellations=consts, rows=rows, wall_seconds=time.time() - t0)))
    print('done', round(time.time() - t0, 1))


def read(out):
    R = json.loads((out / 'emconst_rows.json').read_text()); rows = R['rows']; rng = np.random.default_rng(SEED + 11); res = dict(constellations=R['constellations'], gain_db={}, criteria={})
    def gains(geom, snr, name):                                            # per-frame EM gain over pilot-only, dB of the ratio of means via bootstrap
        rr = [r for r in rows if r['geom'] == geom and r['snr'] == snr]
        p = np.array([r['mse'][name]['pilot'] for r in rr]); e = np.array([r['mse'][name]['em'] for r in rr]); g = np.array([r['mse'][name]['genie'] for r in rr])
        return p, e, g
    def boot(fn, n):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(2000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    for geom, snr in [(g, 3.0) for g in CFG['geoms']] + [tuple(x) for x in CFG['extra']]:
        if True:
            for name in CFG['consts']:
                p, e, g = gains(geom, snr, name); n = len(p)
                res['gain_db'][f'{geom}|{snr}|{name}'] = dict(em=boot(lambda ii: 10 * np.log10(p[ii].mean() / e[ii].mean()), n), genie=float(10 * np.log10(p.mean() / g.mean())))
    for geom in ('A1', 'A8', 'C'):
        pq, eq, _ = gains(geom, 3.0, 'qam16'); n = len(pq); gd = {}
        for name in CFG['consts']:
            p, e, _ = gains(geom, 3.0, name); gd[name] = (p, e)
        G = lambda name, ii: 10 * np.log10(gd[name][0][ii].mean() / gd[name][1][ii].mean())
        k1 = {name: boot(lambda ii, name=name: G(name, ii), n) for name in ('psk16', 'apsk_dvb')}
        k2 = boot(lambda ii: G('qam16', ii) - G('apsk_dvb', ii), n)
        k3 = boot(lambda ii: (G('apsk_4fold', ii) - G('apsk_tight', ii)) / max(G('qam16', ii) - G('apsk_tight', ii), 1e-9), n)
        res['criteria'][geom] = dict(K1_gain_psk16=k1['psk16'], K1_gain_apsk_dvb=k1['apsk_dvb'], K1_floor_respected=bool(k1['psk16']['point'] <= 4.0 and k1['apsk_dvb']['point'] <= 4.0),
                                     K2_qam_minus_apsk_dvb=k2, K2_pass=bool(k2['ci95'][0] >= 3.0), K3_recovered_fraction=k3, K3_pass=bool(k3['point'] >= 0.7))
    c = res['criteria']
    res['verdict_main'] = 'PASS' if all(c[g]['K1_floor_respected'] and c[g]['K2_pass'] for g in c) else 'KILL'
    res['verdict_constructive'] = 'PASS' if all(c[g]['K3_pass'] for g in c) else 'FAIL'
    (out / 'emconst_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read')); ap.add_argument('--out', default='out_r3b11'); a = ap.parse_args()
    if a.mode == 'smoke':
        print({n: (round(float(np.mean(np.abs(constellation(n)) ** 4)), 3), round(kappa4(constellation(n)), 4)) for n in CFG['consts']})
        t0 = time.process_time(); r = job(('A8', 3.0, 0)); print('cpu', time.process_time() - t0)
        print({k: {a: round(10 * np.log10(v['pilot'] / v[a]), 2) for a in ('em', 'genie')} for k, v in r['mse'].items()})
    else:
        dict(run=run, read=read)[a.mode](HERE / a.out)
