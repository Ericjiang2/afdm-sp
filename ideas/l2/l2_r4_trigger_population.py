#!/usr/bin/env python3
"""Idea-funnel local round 4, descriptive add-on to card I-20261122-l32 (2026-11-22, runner l): who triggers the
re-search under total-energy fading?  Arithmetic on the archived rho-sweep per-frame failures (same input, same
fading convolution and project power profile with D1 truncation as l2_r4_fade_convolve.py); no receiver run, no
pre-registered criterion (exploratory readout).  'F0 fails' is used as a proxy for the syndrome trigger.
At the SNR where CODELAY reaches 1% FER: share of frames where F0 fails, and the share of those that CODELAY rescues
(rescued = F0 fails and CD succeeds = P(F0 fail) - P(both fail)).   -> out_r4b1/trigger_population.json
"""
import gzip, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
raw = json.load(gzip.open(HERE / 'out_r4b1/rho_sweep_fail_F0_CD.json.gz', 'rt'))
keys = [k.split('|') for k in raw]
SC = ('U', 'G'); RHO = sorted({int(k[1]) for k in keys}); SNR = sorted({int(k[2]) for k in keys}); FR = sorted({int(k[3]) for k in keys})
fail = np.zeros((len(FR), 2, 2, len(RHO), len(SNR)))
for k, v in raw.items():
    s, r, q, f = k.split('|'); fail[FR.index(int(f)), :, SC.index(s), RHO.index(int(r)), SNR.index(int(q))] = v
snrs = np.array(SNR) / 100.
rng = np.random.default_rng(20261122); m = 400000
idx = np.cumsum(np.maximum(1, np.ceil(rng.exponential(.0008, (m, 8)) * 16000)), axis=1); idx = idx[idx[:, -1] - 1 <= 102]
pv = np.exp(-np.log(100) / 0.01 * (idx - 1) / 16000); w = pv / pv.sum(1, keepdims=True)
edb = 10 * np.log10(np.quantile((w * rng.exponential(1, w.shape)).sum(1), (np.arange(300) + .5) / 300))
grid = np.arange(4, 14.01, .01)


def ev(curve, g, fading):
    lf = np.log10(np.maximum(curve, 1e-5)); x = g + edb if fading else np.array([g])
    return float((10 ** np.interp(x, snrs, lf, left=0., right=lf[-1])).mean())


def readout(F):
    f = F.mean(0); both = (F[:, 0] * F[:, 1]).mean(0); out = {}
    for rho in (250, 300):
        r = RHO.index(rho)
        for fading in (False, True):
            cd = np.array([np.mean([ev(f[1, s, r], g, fading) for s in range(2)]) for g in grid]); g1 = float(grid[np.argmax(cd <= .01)])
            p = {k: float(np.mean([ev(c[s, r], g1, fading) for s in range(2)])) for k, c in dict(F0=f[0], CD=f[1], both=both).items()}
            out[f"rho{rho}_{'faded' if fading else 'unit'}"] = dict(snr_db=g1, f0_fail=p['F0'], cd_fail=p['CD'], both_fail=p['both'],
                                                                    rescued_share=(p['F0'] - p['both']) / p['F0'])
    return out


pt = readout(fail)
B = [readout(fail[rng.integers(0, len(FR), len(FR))]) for _ in range(500)]
for k, v in pt.items():
    for q in ('f0_fail', 'rescued_share'):
        v[q + '_ci95'] = [float(np.percentile([b[k][q] for b in B], 2.5)), float(np.percentile([b[k][q] for b in B], 97.5))]
json.dump(pt, open(HERE / 'out_r4b1/trigger_population.json', 'w'), indent=1)
for k, v in pt.items():
    print(k, {a: (round(b, 4) if not isinstance(b, list) else [round(x, 3) for x in b]) for a, b in v.items()})
