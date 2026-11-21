"""Visible-feature probe on saved edit-budget rows.

Rules: .trellis/tasks/11-20-low-pilot-missed-path/research/visible-probe-rules-20261120.md (committed 96083710 before this ran).
Zero simulation: reads rows_shard*.jsonl only. Run in the AFDM conda env (numpy, scikit-learn).
"""
import glob
import json
import math
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

POPULATIONS = {'rho150': (150, {600, 650, 700, 800}), 'rho300': (300, {450, 500})}
DRAWS, SEED = 2000, 20261120


def entry_features(paths):
    delays = sorted({d for d, _ in paths})
    gaps = np.diff(delays)
    return [len(delays), delays[-1] - delays[0], float(np.std([nu for _, nu in paths])),
            int(gaps.min()) if len(gaps) else 0]


def cd2_features(arm):
    objective = arm['state']['objective']
    if objective <= 0:
        raise ValueError('non-positive CD2 objective')
    edits = arm['accepted_edits']
    return [float(arm['first_edit_type'] == 'new_delay'), arm['co_delay_pairs'], len(edits),
            sum(e['label'] == 'phantom' for e in edits), math.log(objective)]


def load(root):
    rows = {name: [] for name in POPULATIONS}
    for path in sorted(glob.glob(f'{root}/rows_shard*.jsonl')):
        with open(path) as fh:
            for line in fh:
                row = json.loads(line)
                for name, (rho, snrs) in POPULATIONS.items():
                    if row['rho_permille'] == rho and row['snr_centi_db'] in snrs and row['triggered']:
                        arms = row['arms']
                        rows[name].append(dict(
                            cell=(row['scenario'], row['snr_centi_db']), frame=row['frame'],
                            syn=[math.log1p(row['syndrome'])], entry=entry_features(row['entering_paths']),
                            cd2=cd2_features(arms['CD2']), fail4=arms['CD4']['errors'] > 0,
                            fail2=arms['CD2']['errors'] > 0))
    return rows


def design(units, parts):
    cells = sorted({u['cell'] for u in units})
    onehot = np.array([[u['cell'] == c for c in cells[1:]] for u in units], float).reshape(len(units), -1)
    blocks = [onehot] + [np.array([u[p] for u in units], float) for p in parts]
    return np.hstack(blocks)


def folds(X, y, groups):
    fold = np.zeros(len(y), int)
    for k, (_, test) in enumerate(GroupKFold(5).split(X, y, groups)):
        fold[test] = k
    return fold


def oof(X, y, groups, model):
    pred = np.zeros(len(y))
    for train, test in GroupKFold(5).split(X, y, groups):
        m = model()
        m.fit(X[train], y[train])
        pred[test] = m.predict_proba(X[test])[:, 1]
    return pred


def comparison_blocks(cells, y, score):
    """Per (cell, fold): fail x ok concordance matrix (1, .5, 0).

    Pairs are formed only inside one fold: out-of-fold models carry fold-specific intercepts that are
    anti-correlated with the held-out labels, which biased cross-fold pairs (cell-only baseline gave .33, not .5).
    """
    blocks = []
    for c in sorted(set(cells)):
        idx = np.array([i for i, k in enumerate(cells) if k == c])
        f, o = idx[y[idx] == 1], idx[y[idx] == 0]
        if len(f) and len(o):
            d = score[f][:, None] - score[o][None, :]
            blocks.append((f, o, (d > 0) + .5 * (d == 0)))
    return blocks


def auc(blocks, w):
    num = sum(w[f] @ m @ w[o] for f, o, m in blocks)
    den = sum(w[f].sum() * w[o].sum() for f, o, _ in blocks)
    return num / den


def run(units, target, parts_by_model):
    y = np.array([u[target] for u in units], int)
    cells = [u['cell'] for u in units]
    frames = np.array([u['frame'] for u in units])
    lin = lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1., max_iter=5000))  # noqa: E731
    hgb = lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=.05, max_iter=150,  # noqa: E731
                                                 l2_regularization=1., min_samples_leaf=20, random_state=0)
    cells = [(c, k) for c, k in zip(cells, folds(design(units, []), y, frames))]
    scores = {}
    for name, parts in parts_by_model.items():
        X = design(units, parts)
        scores[f'{name}/lin'] = oof(X, y, frames, lin)
        if parts:
            scores[f'{name}/hgb'] = oof(X, y, frames, hgb)
    blocks = {k: comparison_blocks(cells, y, s) for k, s in scores.items()}
    uniq = np.unique(frames)
    member = [np.flatnonzero(frames == f) for f in uniq]
    rng = np.random.default_rng(SEED)
    boots = {k: [] for k in scores}
    for _ in range(DRAWS):
        w = np.zeros(len(y))
        for j in rng.integers(0, len(uniq), len(uniq)):
            w[member[j]] += 1
        for k in scores:
            boots[k].append(auc(blocks[k], w))
    point = {k: auc(blocks[k], np.ones(len(y))) for k in scores}
    out = dict(n=len(y), events=int(y.sum()), frames=len(uniq),
               auc={k: [round(point[k], 4)] + [round(float(q), 4) for q in np.percentile(boots[k], [2.5, 97.5])]
                    for k in scores})
    deltas = {}
    for flav in ('lin', 'hgb'):
        full, syn = f'full/{flav}', 'syn/lin' if flav == 'lin' else 'syn/hgb'
        if full in scores and syn in scores:
            diff = np.array(boots[full]) - np.array(boots[syn])
            deltas[f'full-syn/{flav}'] = [round(point[full] - point[syn], 4)] + \
                [round(float(q), 4) for q in np.percentile(diff, [2.5, 97.5])]
    out['delta'] = deltas
    # Standardised coefficients of the full linear model on all data (descriptive: which quantity carries weight).
    X = design(units, parts_by_model['full'])
    m = lin().fit(X, y)
    n_fe = len({u['cell'] for u in units}) - 1
    names = sum(([f'{p}{i}' for i in range(len(units[0][p]))] for p in parts_by_model['full']), [])
    out['full_lin_std_coef'] = dict(zip(names, np.round(m[-1].coef_[0][n_fe:], 3).tolist()))
    return out


def main(root):
    rows = load(root)
    res = {}
    t1 = {'base': [], 'syn': ['syn'], 'full': ['syn', 'entry']}
    res['T1_rho150_cd4_fail'] = run(rows['rho150'], 'fail4', t1)
    res['T1_rho300_cd4_fail'] = run(rows['rho300'], 'fail4', t1)
    t2_units = [dict(u, rescue4=not u['fail4']) for u in rows['rho150'] if u['fail2']]
    res['T2_rho150_cd2fail_cd4_rescue'] = run(t2_units, 'rescue4',
                                              {'base': [], 'syn': ['syn'], 'full': ['syn', 'entry', 'cd2']})
    res['feature_names'] = dict(syn=['log1p(syndrome)'],
                                entry=['distinct_delays', 'delay_span', 'doppler_std', 'min_delay_gap'],
                                cd2=['first_edit_new_delay', 'co_delay_pairs', 'n_edits', 'n_phantom_edits',
                                     'log_objective'])
    json.dump(dict(source=root, draws=DRAWS, seed=SEED, results=res), sys.stdout, indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
