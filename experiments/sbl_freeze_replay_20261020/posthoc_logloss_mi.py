"""Post-hoc read-only check: per-frame extrinsic bit logloss versus decode failure, against the C1 MI threshold.

Reads saved rows only (no generator/SBL/receiver/decoder calls) and prints results; writes nothing.
L_th = (1 - I*) ln 2 converts the C1 decoder-input threshold I* = .577 bit into the nats logloss of bit_loss.
Usage: python -I posthoc_logloss_mi.py <outputs_sbl_freeze_replay_20261020 dir>
"""
import glob
import json
import math
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.stats import rankdata

I_STAR = .577
L_TH = (1 - I_STAR) * math.log(2)
SEED, DRAWS = 20261021, 2000


def records(directory):
    out = []
    for path in sorted(glob.glob(directory + '/rows_shard*.jsonl')):
        for line in open(path):
            row = json.loads(line)
            for name, arm in row['arms'].items():
                # gram_cohort1 nests arms by upstream; fresh_cohort1 uses flat 'upstream/arm' keys.
                items = arm.items() if 'fer' not in arm else [('', arm)]
                for sub, score in items:
                    label = name + ('/' + sub if sub else '')
                    if not label.endswith('/diag'):
                        out.append((row['frame'], label, score['extrinsic_bit_logloss'], score['fer']))
    if not out:
        raise ValueError('no rows read from ' + directory)
    return out


def auc(loss, fail):
    pos, neg = loss[fail == 1], loss[fail == 0]
    if not len(pos) or not len(neg):
        return float('nan')
    rank = rankdata(np.r_[pos, neg])
    return (rank[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def report(directory):
    rec = records(directory)
    frame = np.array([r[0] for r in rec])
    loss = np.array([r[2] for r in rec])
    fail = np.array([r[3] for r in rec])
    units = np.unique(frame)
    index = {u: np.where(frame == u)[0] for u in units}
    rng = np.random.default_rng(SEED)
    draws = np.array([auc(loss[s], fail[s]) for s in
                      (np.concatenate([index[u] for u in rng.choice(units, len(units))]) for _ in range(DRAWS))])
    draws = draws[np.isfinite(draws)]
    high = loss > L_TH
    print(f'== {directory.rstrip("/").split("/")[-1]}: n={len(loss)} fails={fail.sum()} frames={len(units)} '
          f'AUC={auc(loss, fail):.3f} [{np.percentile(draws, 2.5):.3f},{np.percentile(draws, 97.5):.3f}] '
          f'fail|L>Lth={fail[high].sum()}/{high.sum()} fail|L<=Lth={fail[~high].sum()}/{(~high).sum()} '
          f'min failing L={loss[fail == 1].min():.3f}')

    def nll(t):
        p = np.clip(1 / (1 + np.exp(-(t[0] + t[1] * (loss - .3)))), 1e-12, 1 - 1e-12)
        return -(fail * np.log(p) + (1 - fail) * np.log(1 - p)).sum()
    t = minimize(nll, [0., 50.]).x
    l50 = .3 - t[0] / t[1]
    print(f'   logistic L50={l50:.4f} nats -> I50={1 - l50 / math.log(2):.4f} bit (L_th={L_TH:.4f})')


if __name__ == '__main__':
    root = sys.argv[1]
    for name in ('gram_cohort1', 'fresh_cohort1'):
        report(root + '/' + name)
