"""Paired physical-frame estimates and the DRAFT §7 decision rule."""

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tf_covariance_audit_20261018'))
from sampling import bootstrap_means, linear_summary, ratio_summary

ARMS = ('R0', 'U2', 'K', 'M', 'KM')
INTERVENTIONS = ('K', 'M')
CUTOFFS = {'half': .5, 'quarter': .25}
N_BOOT = 20_000
SEED = 20261121
DENOMINATOR_FAILURE_LIMIT = .01
MIN_DISCORDANT_CLUSTERS = 5

RECOVERS_HALF = 'recovers at least half'
RECOVERS_LESS_THAN_QUARTER = 'recovers less than one quarter'
UNCERTAIN = 'uncertain'
NOT_EVALUABLE = 'not evaluable'

JOINT_VERDICTS = {
    (RECOVERS_HALF, RECOVERS_LESS_THAN_QUARTER): 'H-cap supported',
    (RECOVERS_LESS_THAN_QUARTER, RECOVERS_HALF): 'H-ref supported',
    (RECOVERS_HALF, RECOVERS_HALF): 'both interventions recover at least half',
    (RECOVERS_LESS_THAN_QUARTER, RECOVERS_LESS_THAN_QUARTER): 'both interventions recover less than one quarter',
}


def cutoff_summary(point, draws):
    """Two-sided 97.5% percentile interval for a paired cutoff contrast."""
    lo, hi = map(float, np.percentile(draws, [1.25, 98.75]))
    return dict(point=float(point), ci_lo=lo, ci_hi=hi, ci_width=hi - lo,
                contains_0=lo <= 0 <= hi, confidence_level=.975)


def classify(gap, cutoff_contrasts, discordant_clusters):
    """Require recurrence of the gap sign before testing each intervention."""
    premise = dict(point_positive=gap['point'] > 0, lower_bound_positive=gap['ci_lo'] > 0,
                   denominator_failure_within_limit=(
                       gap['denominator_nonpositive_fraction'] <= DENOMINATOR_FAILURE_LIMIT))
    if not all(premise.values()):
        return dict(gap_established=False, premise_checks=premise, verdict=NOT_EVALUABLE,
                    by_arm=dict.fromkeys(INTERVENTIONS, NOT_EVALUABLE))

    by_arm = {}
    for arm in INTERVENTIONS:
        contrasts = cutoff_contrasts[arm]
        if discordant_clusters[arm] < MIN_DISCORDANT_CLUSTERS:
            by_arm[arm] = UNCERTAIN
        elif contrasts['half']['ci_lo'] > 0:
            by_arm[arm] = RECOVERS_HALF
        elif contrasts['quarter']['ci_hi'] < 0:
            by_arm[arm] = RECOVERS_LESS_THAN_QUARTER
        else:
            by_arm[arm] = UNCERTAIN
    verdict = JOINT_VERDICTS.get((by_arm['K'], by_arm['M']), UNCERTAIN)
    return dict(gap_established=True, premise_checks=premise, verdict=verdict, by_arm=by_arm)


def readout(fer_by_arm, frames):
    """Estimate from matched binary outcomes; caller validates full key coverage."""
    if set(fer_by_arm) != set(ARMS):
        raise ValueError('Expected paired outcomes for R0, U2, K, M and KM')
    values = {arm: np.asarray(fer_by_arm[arm]) for arm in ARMS}
    if any(not np.isin(outcomes, (0, 1)).all() for outcomes in values.values()):
        raise ValueError('Per-key FER outcomes must be binary')
    values = {arm: outcomes.astype(int) for arm, outcomes in values.items()}
    gap_by_key = values['U2'] - values['R0']

    # Form the signed contrasts at the key level so equality at a cutoff is
    # preserved exactly even when separate resampled FERs would round differently.
    columns = dict(values, gap=gap_by_key)
    for arm in INTERVENTIONS:
        delta = values['U2'] - values[arm]
        columns[f'delta_{arm}'] = delta
        for label, threshold in CUTOFFS.items():
            columns[f'{arm}_{label}'] = delta - threshold * gap_by_key
    columns.update({f'{arm}_vs_R0': values[arm] - values['R0'] for arm in ('K', 'M', 'KM')})
    # Difference in the cap effect (capped minus uncapped), scalar minus unified refinement.
    columns['cap_by_refinement_interaction'] = (values['KM'] - values['M']) - (values['K'] - values['U2'])
    draws, n_clusters = bootstrap_means(columns, frames, n_boot=N_BOOT, seed=SEED)
    point = {name: float(np.mean(column)) for name, column in columns.items()}

    gap = linear_summary(point, draws, {'gap': 1})
    gap['denominator_nonpositive_fraction'] = float(np.mean(draws['gap'] <= 0))
    ratios = {arm: ratio_summary(point, draws, {f'delta_{arm}': 1}, {'gap': 1},
                                 limit=DENOMINATOR_FAILURE_LIMIT)
              for arm in INTERVENTIONS}
    cutoff_contrasts = {
        arm: {label: dict(cutoff_summary(point[f'{arm}_{label}'], draws[f'{arm}_{label}']), threshold=threshold)
              for label, threshold in CUTOFFS.items()}
        for arm in INTERVENTIONS
    }
    frame_ids = np.asarray(frames, dtype=str)
    discordant = {arm: int(len(np.unique(frame_ids[values['U2'] != values[arm]]))) for arm in INTERVENTIONS}
    return dict(n_frame_clusters=n_clusters, bootstrap=dict(draws=N_BOOT, seed=SEED),
                fer={arm: linear_summary(point, draws, {arm: 1}) for arm in ARMS},
                gap=gap, recovery=ratios, discordant_frame_clusters=discordant,
                cutoff_contrasts=cutoff_contrasts,
                difference_vs_R0={arm: linear_summary(point, draws, {f'{arm}_vs_R0': 1})
                                  for arm in ('K', 'M', 'KM')},
                cap_by_refinement_interaction=linear_summary(point, draws, {'cap_by_refinement_interaction': 1}),
                verdict=classify(gap, cutoff_contrasts, discordant))
