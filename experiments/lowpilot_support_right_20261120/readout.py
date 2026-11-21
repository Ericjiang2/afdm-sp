"""Zero-simulation readout of support-right (SR) failures. Rules: RULES.md (committed 17ff4f94 before this ran).

Usage: python readout.py <rows_dir> <arm>   (edit budget: CD4; rho sweep: CD). Needs numpy and scikit-learn.
"""
import glob
import json
import math
import sys
from collections import defaultdict

import numpy as np
from sklearn.linear_model import LogisticRegression

CLEAN_DATA_SNR = 3.449  # A3 at rho .30, 5 dB: 5 + 10 log10(.7) = 3.451 dB
DRAWS, SEED = 2000, 20261120


def wilson(k, n):
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [k, n, round(p, 4), round(c - h, 4), round(c + h, 4)]


def load(root, arm):
    units = []
    for path in sorted(glob.glob(f'{root}/rows_shard*.jsonl')):
        with open(path) as fh:
            for line in fh:
                row = json.loads(line)
                if not row['triggered']:
                    continue
                truth, a = row['truth'], row['arms'][arm]
                est = {d: nu for d, nu in a['state']['paths']}
                if len(est) != 8 or set(est) != set(truth['delays']):
                    continue
                power = np.array([g[0] ** 2 + g[1] ** 2 for g in truth['gains']])
                dnu = np.array([abs(est[d] - nu) for d, nu in zip(truth['delays'], truth['dopplers'])])
                rho = row['rho_permille'] / 1000
                snr = row['snr_centi_db'] / 100
                units.append(dict(scenario=row['scenario'], rho=row['rho_permille'], snr=row['snr_centi_db'],
                                  frame=row['frame'], cluster=(row['scenario'], row['frame']),
                                  data_snr=snr + 10 * math.log10(1 - rho), log2rho=math.log2(rho),
                                  fail=a['errors'] > 0, e_w=float(power @ dnu / power.sum()),
                                  e_max=float(dnu[power.argmax()])))
    return units


def cluster_weights(units, rng):
    keys = sorted({u['cluster'] for u in units})
    index = {k: i for i, k in enumerate(keys)}
    member = np.array([index[u['cluster']] for u in units])
    for _ in range(DRAWS):
        counts = np.bincount(rng.integers(0, len(keys), len(keys)), minlength=len(keys))
        yield counts[member].astype(float)


def auc_blocks(units, score):
    cells = defaultdict(list)
    for i, u in enumerate(units):
        cells[(u['scenario'], u['rho'], u['snr'])].append(i)
    s = np.array([score(u) for u in units])
    blocks = []
    for idx in cells.values():
        f = np.array([i for i in idx if units[i]['fail']])
        o = np.array([i for i in idx if not units[i]['fail']])
        if len(f) and len(o):
            d = s[f][:, None] - s[o][None, :]
            blocks.append((f, o, (d > 0) + .5 * (d == 0)))
    return blocks


def auc(blocks, w):
    num = sum(w[f] @ m @ w[o] for f, o, m in blocks)
    den = sum(w[f].sum() * w[o].sum() for f, o, _ in blocks)
    return num / den


def auc_with_ci(units, score):
    blocks = auc_blocks(units, score)
    point = auc(blocks, np.ones(len(units)))
    boots = [auc(blocks, w) for w in cluster_weights(units, np.random.default_rng(SEED))]
    return [round(point, 4)] + [round(float(q), 4) for q in np.percentile(boots, [2.5, 97.5])]


def r2(units):
    X = np.array([[u['scenario'] == 'G', u['data_snr'], u['log2rho']] for u in units], float)
    y = np.array([u['fail'] for u in units], int)

    def or_per_halving(w):
        m = LogisticRegression(penalty=None, max_iter=10000).fit(X, y, sample_weight=w)
        return math.exp(-m.coef_[0][2])

    point = or_per_halving(np.ones(len(y)))
    boots = [or_per_halving(w) for w in cluster_weights(units, np.random.default_rng(SEED))]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return dict(n=len(y), events=int(y.sum()), or_per_halving_rho=[round(point, 3), round(lo, 3), round(hi, 3)])


def main(root, arm):
    units = load(root, arm)
    clean = [u for u in units if u['data_snr'] >= CLEAN_DATA_SNR]
    low = [u for u in clean if u['rho'] <= 200]
    out = dict(source=root, arm=arm, sr_keys=len(units), sr_clean=len(clean))
    out['R1_low_rho_clean'] = wilson(sum(u['fail'] for u in low), len(low))
    table = defaultdict(lambda: [0, 0])
    for u in units:
        table[(u['rho'], u['snr'])][0] += u['fail']
        table[(u['rho'], u['snr'])][1] += 1
    out['R1_table_fail_n'] = {f'{r}/{s}': [*v, round(v[0] / v[1], 4)] for (r, s), v in sorted(table.items())}
    out['R2'] = r2(clean)
    out['R3_auc_e_w'] = auc_with_ci(low, lambda u: u['e_w'])
    out['R3_auc_e_max'] = auc_with_ci(low, lambda u: u['e_max'])
    out['R3_median_e_w_fail_ok'] = [round(float(np.median([u['e_w'] for u in low if u['fail']] or [np.nan])), 4),
                                    round(float(np.median([u['e_w'] for u in low if not u['fail']])), 4)]
    for snr in (800, 1000):
        g = [u for u in units if u['rho'] == 150 and u['snr'] == snr]
        out[f'R4_rho150_snr{snr}'] = wilson(sum(u['fail'] for u in g), len(g)) if g else None
    g = [u for u in units if u['rho'] == 300 and u['snr'] == 500]
    out['R5_rho300_snr500'] = wilson(sum(u['fail'] for u in g), len(g)) if g else None
    json.dump(out, sys.stdout, indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
