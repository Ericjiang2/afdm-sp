"""Frozen paired FER readout (PROTOCOL.md): archived known/SF/DD arms + the new Stein arm on the same 8,000 keys.
Reuses the sigma2_dd readout helpers (crossing module check, bounds tests) by import.
  python readout_stein.py --run out/main --archive <sigma2_dd main dir> --crossings <phase3_crossings.py>
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

import stein  # noqa: F401  (puts ../sigma2_dd_20261118 on sys.path)
from readout import BAND, BOOTSTRAPS, SEED, greater, inside, load_crossings

FIRST, STOP = 11000, 12000
SNRS = tuple(range(450, 801, 50))
B_ARMS = ('known', 'SF', 'DD', 'Stein')
CURVES = tuple(f'B_{m}' for m in B_ARMS) + tuple(f'A3_{m}' for m in B_ARMS)
IDX = {name: i for i, name in enumerate(CURVES)}


def rows(path_dir, arms):
    for p in sorted(Path(path_dir).glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line)
                yield r['frame'], r['snr_centi_db'], {m: r['arms'][m] for m in arms}, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--archive', required=True, type=Path)
    ap.add_argument('--crossings', required=True, type=Path)
    a = ap.parse_args()
    status = (a.run / 'STATUS').read_text().split()
    if status[0] != 'DONE':
        raise ValueError(f'Run not complete: {status}')
    math = load_crossings(a.crossings)
    snr_i = {s: i for i, s in enumerate(SNRS)}
    fail = np.full((STOP - FIRST, len(CURVES), len(SNRS)), -1, dtype=np.float32)
    dd_noise = {}
    for frame, snr, arms, _ in rows(a.archive, ('known', 'SF', 'DD')):
        for m in ('known', 'SF', 'DD'):
            fail[frame - FIRST, IDX[f'B_{m}'], snr_i[snr]] = arms[m]['B']['info_errors'] > 0
            fail[frame - FIRST, IDX[f'A3_{m}'], snr_i[snr]] = arms[m]['A3_errors'] > 0
        dd_noise[frame, snr] = arms['DD']['B']['noise']
    ratios, mismatch = {s: [] for s in SNRS}, 0
    for frame, snr, arms, r in rows(a.run, ('Stein',)):
        b = arms['Stein']['B']
        fail[frame - FIRST, IDX['B_Stein'], snr_i[snr]] = b['info_errors'] > 0
        fail[frame - FIRST, IDX['A3_Stein'], snr_i[snr]] = arms['Stein']['A3_errors'] > 0
        e = dd_noise[frame, snr]
        mismatch += (b['noise']['residual_power'] != e['residual_power']
                     or b['noise']['uncertainty_power'] != e['uncertainty_power'])
        ratios[snr].append(b['noise']['ratio'])
    if (fail == -1).any():
        raise ValueError('Incomplete paired grid')
    n = fail.shape[0]
    counts = fail.sum(axis=0, dtype=np.int64)
    observed = math.crossing_bounds(counts, n)
    rng = np.random.default_rng(SEED)
    matrix = fail.reshape(n, -1)
    samples = np.empty((BOOTSTRAPS, len(CURVES), 2))
    for start in range(0, BOOTSTRAPS, 512):
        batch = min(512, BOOTSTRAPS - start)
        w = np.empty((batch, n), dtype=np.float32)
        for draw in w:
            draw[:] = np.bincount(rng.integers(0, n, n), minlength=n)
        samples[start:start + batch] = math.crossing_bounds((w @ matrix).reshape(batch, len(CURVES), len(SNRS)), n)

    def contrast(i, j):
        return math.bounds_json(math.contrast_bounds(observed, [i], [j])), math.paired_ci(math.contrast_bounds(samples, [i], [j]))

    d_s, d_s_ci = contrast(IDX['B_Stein'], IDX['B_known'])   # P1: Stein - known
    g_sf, g_sf_ci = contrast(IDX['B_SF'], IDX['B_Stein'])     # P2: SF - Stein (>0: Stein better)
    g_dd, g_dd_ci = contrast(IDX['B_DD'], IDX['B_Stein'])     # S1: DD - Stein
    p1 = 'ROBUST' if inside(d_s_ci, -BAND, BAND) is True else 'DEGRADED' if d_s_ci[0] > BAND else 'INCONCLUSIVE'
    p2 = 'BETTER' if g_sf_ci[0] > 0 else 'NOT_BETTER' if g_sf_ci[1] <= 0 else 'INCONCLUSIVE'
    result = dict(_argv=sys.argv, _config=dict(readout_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  frames=[FIRST, STOP - 1], snr_centi_db=SNRS, n_bootstrap=BOOTSTRAPS, seed=SEED),
                  curves={c: dict(info_error_frames=counts[i].tolist(), crossing=math.bounds_json(observed[i]),
                                  crossing_ci=math.bounds_json(math.paired_ci(samples[:, i]))) for c, i in IDX.items()},
                  P1=dict(verdict=p1, delta=d_s, ci=math.bounds_json(d_s_ci)),
                  P2=dict(verdict=p2, gap=g_sf, ci=math.bounds_json(g_sf_ci)),
                  S1=dict(gap=g_dd, ci=math.bounds_json(g_dd_ci), greater_than_half_dd_loss=greater(g_dd_ci, .82)),
                  stein_ratio={str(s): dict(n=len(v), mean=float(np.mean(v)), median=float(np.median(v))) for s, v in ratios.items()},
                  round1_power_mismatches=int(mismatch))
    (a.run / 'results.json').write_text(json.dumps(result, indent=1, allow_nan=False))
    print(p1, d_s_ci, p2, g_sf_ci, 'mismatch', mismatch)


if __name__ == '__main__':
    main()
