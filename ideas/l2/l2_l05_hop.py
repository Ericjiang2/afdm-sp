#!/usr/bin/env python3
"""Idea-funnel L2 check for card I-20261121-l05 (2026-11-21, runner l): the card's cheapest decisive check, self-contained numpy.
  /opt/anaconda3/bin/python ideas/l2/l2_l05_hop.py ideas/l2/out7/l05_hop.json"""
import json, sys
import numpy as np
SCS, K, OV, NREF = 30e3, 612, 12, 6            # subcarrier spacing, subcarriers per band, overlap (one RB), common reference subcarriers
DT, DNU, SNR_DB, TRIALS, SEED = 1e-3, 125.0, 10.0, 512, 20261121
fA = np.arange(K) * SCS; fB = (np.arange(K) + K - OV) * SCS; f = np.arange(2 * K - OV) * SCS
ref = np.arange(K - OV + (OV - NREF) // 2, K - OV + (OV - NREF) // 2 + NREF)          # indices into the union grid, inside the overlap
grid = np.arange(0, 201e-9, 1e-9); S = np.exp(-2j * np.pi * np.outer(f, grid)); Gm = S.conj().T @ S
a = np.array([1.0, 10 ** (-1 / 20)]); sig = 10 ** (-SNR_DB / 20)
SCHEMES = dict(ABBA_eq=('ABBA', {0: .5, 3: .5, 1: .5, 2: .5}), ABAB_eq=('ABAB', {0: .5, 2: .5, 1: .5, 3: .5}),
               ABAB_w=('ABAB', {0: .25, 2: .75, 1: .75, 3: .25}))


def estimate(g):
    z = S.conj().T @ g; n = len(grid); best = (np.inf, 0)
    d = np.real(np.diag(Gm))
    for i in range(n):                      # two-path LS with linear amplitudes, tau2 - tau1 in [5, 80] ns
        j = np.arange(i + 5, min(i + 81, n))
        if not len(j):
            continue
        det = d[i] * d[j] - np.abs(Gm[i, j]) ** 2
        expl = (d[j] * abs(z[i]) ** 2 + d[i] * np.abs(z[j]) ** 2 - 2 * np.real(np.conj(z[i]) * Gm[i, j] * z[j])) / det
        k = int(np.argmax(expl))
        if -expl[k] < best[0]:
            best = (-expl[k], i)
    return grid[best[1]]


rng = np.random.default_rng(SEED); err = {k: [] for k in SCHEMES}
for _ in range(TRIALS):
    tau1 = rng.uniform(50e-9, 100e-9); taus = np.array([tau1, tau1 + 30e-9]); ph = rng.uniform(0, 2 * np.pi, 2)
    hop_phase = rng.uniform(0, 2 * np.pi, 4); noise = (rng.standard_normal((4, len(f))) + 1j * rng.standard_normal((4, len(f)))) * sig / np.sqrt(2)
    for name, (order, w) in SCHEMES.items():
        acc = np.zeros(len(f), complex); wsum = np.zeros(len(f))
        for m in range(4):
            t = (m - 1.5) * DT
            H = sum(a[p] * np.exp(1j * (ph[p] + 2 * np.pi * (DNU if p else 0.0) * t)) * np.exp(-2j * np.pi * f * taus[p]) for p in range(2))
            y = np.exp(1j * hop_phase[m]) * H + noise[m]
            band = slice(0, K) if order[m] == 'A' else slice(K - OV, 2 * K - OV)
            g = y[band] * np.conj(y[ref].mean())
            acc[band] += w[m] * g; wsum[band] += w[m]
        err[name].append(abs(estimate(acc / wsum) - tau1))
E = {k: np.array(v) for k, v in err.items()}; p90 = {k: float(np.percentile(v, 90)) for k, v in E.items()}
def imp(idx):
    q = {k: np.percentile(v[idx], 90) for k, v in E.items()}
    return 1 - q['ABAB_w'] / min(q['ABBA_eq'], q['ABAB_eq'])
bs = [imp(rng.integers(0, TRIALS, TRIALS)) for _ in range(2000)]
out = dict(_argv=sys.argv, _config=dict(SCS=SCS, K=K, overlap=OV, nref=NREF, hop=DT, doppler_diff=DNU, snr_db=SNR_DB, trials=TRIALS, seed=SEED),
           p90_ns={k: v * 1e9 for k, v in p90.items()}, median_ns={k: float(np.median(v)) * 1e9 for k, v in E.items()},
           improvement=float(imp(np.arange(TRIALS))), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
out['verdict'] = 'KILL' if out['ci95'][1] < 0.20 else 'NOT KILLED'
json.dump(out, open(sys.argv[1], 'w'), indent=1); print(json.dumps({k: out[k] for k in ('p90_ns', 'median_ns', 'improvement', 'ci95', 'verdict')}))
