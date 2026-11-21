"""Claude's independent recomputation of the residual-gap readouts from raw rows (not the frozen verdict code).

Point estimates must match RESULTS.md exactly; intervals use an independent frame-cluster bootstrap (2,000 draws, seed 7) and
need only agree approximately. Usage on deinlab: python claude_check_gap.py <dir with rows_shard*.jsonl[.gz] or rows.jsonl>
"""
import glob
import gzip
import json
import sys

import numpy as np


def rows(directory):
    paths = sorted(glob.glob(f'{directory}/rows_shard*.jsonl*')) or sorted(glob.glob(f'{directory}/rows*.jsonl*'))
    for path in paths:
        opener = gzip.open if path.endswith('.gz') else open
        with opener(path, 'rt') as handle:
            for line in handle:
                entry = json.loads(line)
                yield entry.get('row', entry)


def main(directory):
    data, arms = [], None
    for row in rows(directory):
        variants = row['variants']
        arms = arms or sorted(variants)
        data.append((row['frame'], [int(variants[a]['fer']) for a in arms]))
    frames = np.array([f for f, _ in data])
    values = np.array([v for _, v in data], float)
    idx = {a: i for i, a in enumerate(arms)}
    print('keys', len(values), 'frames', len(np.unique(frames)), 'arms', arms)
    print('FER', {a: round(float(values[:, i].mean()), 5) for a, i in idx.items()})
    uniq, inv = np.unique(frames, return_inverse=True)
    sums = np.zeros((len(uniq), len(arms)))
    np.add.at(sums, inv, values)
    counts = np.bincount(inv).astype(float)
    rng = np.random.default_rng(7)
    draws = []
    for _ in range(2000):
        pick = rng.integers(0, len(uniq), len(uniq))
        draws.append(sums[pick].sum(0) / counts[pick].sum())
    draws = np.array(draws)
    point = sums.sum(0) / counts.sum()
    u2, r0 = idx['U2'], idx['R0']
    gap = lambda m: m[..., u2] - m[..., r0]
    g, gd = gap(point), gap(draws)
    print(f'G = U2 - R0: {g:.4f} [{np.percentile(gd, 2.5):.4f}, {np.percentile(gd, 97.5):.4f}]')
    for arm in arms:
        if arm in ('R0', 'U2'):
            continue
        delta, dd = point[u2] - point[idx[arm]], draws[:, u2] - draws[:, idx[arm]]
        line = f'{arm}: kappa {delta / g:.3f}'
        for t in (.5, .25):
            c = dd - t * gd
            line += f' | Delta-{t}G {delta - t * g:+.4f} [97.5%: {np.percentile(c, 1.25):+.4f}, {np.percentile(c, 98.75):+.4f}]'
        disc = int(np.sum(values[:, u2] != values[:, idx[arm]]))
        print(line, f'| discordant keys vs U2 {disc}')


if __name__ == '__main__':
    main(sys.argv[1])
