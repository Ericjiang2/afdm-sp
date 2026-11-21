#!/usr/bin/env python3
"""Idea-funnel L2 scan for card I-20261121-l05 (2026-11-21, runner l), asked by the gate.  Same model and estimator as l2_l05_hop.py,
with Rel-18-like hop timing and a grid over Doppler difference, hop interval and SNR.
  /opt/anaconda3/bin/python ideas/l2/l2_l05_scan.py ideas/l2/out7/l05_scan.json"""
import json, sys
import numpy as np
SCS, K, OV, NREF, TRIALS, SEED = 30e3, 612, 12, 6, 256, 20261121
f = np.arange(2 * K - OV) * SCS; ref = np.arange(K - OV + 3, K - OV + 3 + NREF)
grid = np.arange(0, 201e-9, 1e-9); S = np.exp(-2j * np.pi * np.outer(f, grid)); Gm = S.conj().T @ S; dg = np.real(np.diag(Gm))
a = np.array([1.0, 10 ** (-1 / 20)])
SCHEMES = dict(ABBA_eq=('ABBA', (1, 5, 7, 11), (.5, .5, .5, .5)), ABAB_eq=('ABAB', (1, 5, 9, 13), (.5, .5, .5, .5)),
               ABAB_w=('ABAB', (1, 5, 9, 13), (.25, .75, .75, .25)))


def estimate(g):
    z = S.conj().T @ g; best = (np.inf, 0)
    for i in range(len(grid) - 5):
        j = np.arange(i + 5, min(i + 81, len(grid)))
        det = dg[i] * dg[j] - np.abs(Gm[i, j]) ** 2
        e = (dg[j] * abs(z[i]) ** 2 + dg[i] * np.abs(z[j]) ** 2 - 2 * np.real(np.conj(z[i]) * Gm[i, j] * z[j])) / det
        if -e.max() < best[0]:
            best = (-e.max(), i)
    return grid[best[1]]


def point(dnu, delta, snr_db, rng):
    sig = 10 ** (-snr_db / 20); T = delta / 4; E = {k: [] for k in SCHEMES}
    for _ in range(TRIALS):
        tau1 = rng.uniform(50e-9, 100e-9); taus = (tau1, tau1 + 30e-9); ph = rng.uniform(0, 2 * np.pi, 2)
        hp = rng.uniform(0, 2 * np.pi, 4); nz = (rng.standard_normal((4, len(f))) + 1j * rng.standard_normal((4, len(f)))) * sig / np.sqrt(2)
        for name, (order, cen, w) in SCHEMES.items():
            acc = np.zeros(len(f), complex); ws = np.zeros(len(f)); t0 = np.mean(cen)
            for m in range(4):
                t = (cen[m] - t0) * T
                H = sum(a[p] * np.exp(1j * (ph[p] + 2 * np.pi * (dnu if p else 0.0) * t)) * np.exp(-2j * np.pi * f * taus[p]) for p in range(2))
                y = np.exp(1j * hp[m]) * H + nz[m]; band = slice(0, K) if order[m] == 'A' else slice(K - OV, 2 * K - OV)
                acc[band] += w[m] * y[band] * np.conj(y[ref].mean()); ws[band] += w[m]
            E[name].append(abs(estimate(acc / ws) - tau1))
    E = {k: np.array(v) for k, v in E.items()}
    def imp(ix):
        q = {k: np.percentile(v[ix], 90) for k, v in E.items()}
        return 1 - q['ABAB_w'] / min(q['ABBA_eq'], q['ABAB_eq'])
    bs = [imp(rng.integers(0, TRIALS, TRIALS)) for _ in range(1000)]
    return dict(p90_ns={k: float(np.percentile(v, 90) * 1e9) for k, v in E.items()}, improvement=float(imp(np.arange(TRIALS))),
                ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], x=float(2 * np.pi * dnu * delta))


rng = np.random.default_rng(SEED); res = dict(_argv=sys.argv, _config=dict(trials=TRIALS, seed=SEED), points={})
for delta in (0.143e-3, 0.5e-3, 1e-3):
    for dnu in (10, 30, 60, 125, 400):
        for snr in (0, 10, 20):
            k = f'd{delta * 1e3:g}ms_dnu{dnu}_snr{snr}'; res['points'][k] = point(dnu, delta, snr, rng)
            r = res['points'][k]; print(k, 'x=%.3f' % r['x'], 'p90', {a_: round(b_, 2) for a_, b_ in r['p90_ns'].items()}, 'imp %.2f [%.2f, %.2f]' % (r['improvement'], *r['ci95']), flush=True)
low = {k: v for k, v in res['points'].items() if int(k.split('_dnu')[1].split('_')[0]) <= 194}
res['kill_by_gate_rule'] = bool(all(v['ci95'][1] < 0.20 for v in low.values()))
res['any_at_rel18_timing'] = bool(any(v['ci95'][1] >= 0.20 for k, v in low.items() if k.startswith('d0.143ms')))
json.dump(res, open(sys.argv[1], 'w'), indent=1); print('kill_by_gate_rule', res['kill_by_gate_rule'], 'any_at_rel18_timing', res['any_at_rel18_timing'])
