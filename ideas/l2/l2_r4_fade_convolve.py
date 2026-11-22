#!/usr/bin/env python3
"""Idea-funnel local round 4, readout 1 v2 (2026-11-22, runner l, claude-fable-5.2): card I-20261122-l32.
Arithmetic only (no receiver run): FER_faded(g) = E_E[FER_unit(g + 10 log10 E)] on the archived rho-sweep per-frame
failures (out_r4b1/rho_sweep_fail_F0_CD.json.gz, extracted from deinlab rows_shard*, md5 in PREDICTIONS_r4_batch1.md).
v2 adds what the fallback review asked for: D1 truncation in the project profile, a cluster bootstrap over the 400
physical frames, an F0-only residual-floor sensitivity, and the P1 difference-in-differences.
Criteria: ideas/l2/PREDICTIONS_r4_batch1.md.   python l2_r4_fade_convolve.py  -> out_r4b1/summary_v2.json
"""
import gzip, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
raw = json.load(gzip.open(HERE / 'out_r4b1/rho_sweep_fail_F0_CD.json.gz', 'rt'))
keys = [k.split('|') for k in raw]
SC = ('U', 'G'); RHO = sorted({int(k[1]) for k in keys}); SNR = sorted({int(k[2]) for k in keys}); FR = sorted({int(k[3]) for k in keys})
fail = np.zeros((len(FR), 2, 2, len(RHO), len(SNR)))            # frame, arm(F0,CD), scenario, rho, snr
for k, v in raw.items():
    s, r, q, f = k.split('|'); fail[FR.index(int(f)), :, SC.index(s), RHO.index(int(r)), SNR.index(int(q))] = v
snrs = np.array(SNR) / 100.; grid = np.arange(4, 22.01, .25)
rng = np.random.default_rng(20261122)


def energy(kind, m=400000, q=300):
    if kind == 'equal8':
        e = rng.gamma(8, 1 / 8, m)
    else:                                                        # project profile with the D1 redraw (max delay bin <= 102)
        idx = np.cumsum(np.maximum(1, np.ceil(rng.exponential(.0008, (m, 8)) * 16000)), axis=1)
        idx = idx[idx[:, -1] - 1 <= 102]
        pv = np.exp(-np.log(100) / 0.01 * (idx - 1) / 16000); w = pv / pv.sum(1, keepdims=True)
        e = (w * rng.exponential(1, w.shape)).sum(1)
    return float(e.var()), 10 * np.log10(np.quantile(e, (np.arange(q) + .5) / q))


def cross(x, f, t=.01):
    lf = np.log10(np.maximum(f, 1e-5))
    if f[0] <= t:
        return x[0]
    for i in range(1, len(x)):
        if f[i] <= t:
            a = (lf[i - 1] - np.log10(t)) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.
            return x[i - 1] + a * (x[i] - x[i - 1])
    return x[-1]


def stats(fer, edb, plat=0.):
    """fer: arm x scen x rho x snr.  Returns unit and faded crossings averaged over U/G: arm x rho."""
    f = fer.copy()
    if plat:
        f[0][..., snrs >= 9] = np.maximum(f[0][..., snrs >= 9], plat)
    lf = np.log10(np.maximum(f, 1e-5)); x = grid[:, None] + edb[None, :]
    unit = np.array([[np.mean([cross(snrs, f[a, s, r]) for s in range(2)]) for r in range(len(RHO))] for a in range(2)])
    fad = np.array([[np.mean([cross(grid, (10 ** np.interp(x, snrs, lf[a, s, r], left=0., right=lf[a, s, r, -1])).mean(1))
                              for s in range(2)]) for r in range(len(RHO))] for a in range(2)])
    return unit, fad


def contrasts(unit, fad):
    i30, i50 = RHO.index(300), RHO.index(500); g = lambda c, i: c[0, i] - c[1, i]
    return dict(unit_gap30=g(unit, i30), faded_gap30=g(fad, i30), shrink30=g(unit, i30) - g(fad, i30),
                unit_P1=g(unit, i30) - g(unit, i50), faded_P1=g(fad, i30) - g(fad, i50),
                cd_shift30=fad[1, i30] - unit[1, i30], unit_best_cd=unit[1].min(), faded_best_cd=fad[1].min(),
                faded_best_f0_rho=RHO[int(np.argmin(fad[0]))], unit_best_f0_rho=RHO[int(np.argmin(unit[0]))])


out = {}
for kind in ('equal8', 'project_D1'):
    var, edb = energy(kind); res = dict(var_E=var)
    res['point'] = contrasts(*stats(fail.mean(0), edb))
    res['floor'] = {str(p): contrasts(*stats(fail.mean(0), edb, p)) for p in (.001, .0025, .004)}
    if kind == 'project_D1':
        B = [contrasts(*stats(fail[rng.integers(0, len(FR), len(FR))].mean(0), edb)) for _ in range(2000)]
        res['ci95'] = {k: [float(np.percentile([b[k] for b in B], 2.5)), float(np.percentile([b[k] for b in B], 97.5))]
                       for k in ('unit_gap30', 'faded_gap30', 'shrink30', 'unit_P1', 'faded_P1', 'cd_shift30')}
    out[kind] = res
json.dump(out, open(HERE / 'out_r4b1/summary_v2.json', 'w'), indent=1, default=float)
for k, v in out.items():
    print(k, 'varE', round(v['var_E'], 3), {a: round(float(b), 2) for a, b in v['point'].items()})
    print('  floor', {p: (round(float(c['faded_gap30']), 2), round(float(c['faded_P1']), 2)) for p, c in v['floor'].items()})
    if 'ci95' in v:
        print('  ci95', {a: [round(x, 2) for x in b] for a, b in v['ci95'].items()})
