"""Descriptive unit-level statistics for the two archived readouts."""

import numpy as np
from scipy.stats import rankdata

QUANTILES = (0, .05, .25, .5, .75, .95, 1)
LOG_GRID = np.logspace(-4, 4, 81)
CLASSES = ('G_P', 'G_T', 'G_F')


def quantiles(values):
    return {str(p): float(x) for p, x in zip(QUANTILES, np.quantile(values, QUANTILES), strict=True)}


def auc(positive, negative):
    ranks = rankdata(np.concatenate((positive, negative)))
    p, n = len(positive), len(negative)
    return float((ranks[:p].sum() - p * (p + 1) / 2) / (p * n))


def rewards(records):
    ridge = np.asarray([row['ridge'] for row in records])
    missing = {key: sum(row[key] is None for row in records) for key in CLASSES}
    gross = {key: np.asarray([row[key] if row[key] is not None else 0. for row in records])
             for key in CLASSES}
    scaled = {key: values / ridge for key, values in gross.items()}

    def aucs(gains):
        return dict(T_vs_P=auc(gains['G_T'], gains['G_P']),
                    P_vs_F=auc(gains['G_P'], gains['G_F']))

    anchors = np.asarray([row['anchor_power'] for row in records])
    positive = (anchors > 0) & (gross['G_P'] > 0)
    x, y = np.log(anchors[positive]), np.log(gross['G_P'][positive])
    x_centered = x - x.mean()
    slope = float(x_centered @ (y - y.mean()) / (x_centered @ x_centered))
    # With strict exceedance, this order statistic allows at most floor(n/20) exceedances.
    cutoff_index = len(records) - len(records) // 20 - 1
    c = max(float(np.partition(scaled[key], cutoff_index)[cutoff_index])
            for key in ('G_P', 'G_F'))
    return dict(n=len(records), empty_class_counts=missing, slope_n=int(positive.sum()),
                quantiles_over_ridge={key: quantiles(values) for key, values in scaled.items()},
                slope_log_GP_on_log_anchor_power=slope,
                auc_over_ridge=aucs(scaled), auc_gross=aucs(gross),
                exceedance={key: (values[:, None] > LOG_GRID).mean(axis=0).tolist()
                            for key, values in scaled.items()},
                threshold=dict(c=c, **{key: float((values > c).mean())
                                       for key, values in scaled.items()}))


def summarize(rows):
    r1 = [row for row in rows if 'R1' in row]
    r2 = [row['R2'] for row in rows if 'R2' in row]
    status = {str(triggered).lower(): sum(row['triggered'] == triggered for row in r1)
              for triggered in (True, False)}
    arms = {arm: dict(all=rewards([row['R1'][arm] for row in r1]), by_trigger={})
            for arm in ('A2', 'A1c')}
    for arm, value in arms.items():
        for triggered in (True, False):
            key = str(triggered).lower()
            value['by_trigger'][key] = (rewards([row['R1'][arm] for row in r1
                                                 if row['triggered'] == triggered])
                                        if 0 < status[key] < len(r1)
                                        else dict(n=status[key], same_as='all') if status[key]
                                        else dict(n=0))
    return dict(R1=dict(n=len(r1), trigger_counts=status, c_grid=LOG_GRID.tolist(), arms=arms),
                R2=dict(n=len(r2), n_cross_delay_pairs=sum(row['pairs'] for row in r2),
                        c1_values=sorted({row['c1'] for row in r2}),
                        gamma_max_rel_error=max(row['gamma_max_rel_error'] for row in r2),
                        quantiles={key: quantiles([row[key] for row in r2])
                                   for key in ('d1', 'd2', 'd3', 'max_d', 'afdm_max',
                                               'ofdm_max', 'afdm_over_ofdm')}))
