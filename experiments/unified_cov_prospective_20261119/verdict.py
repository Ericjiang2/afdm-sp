"""Joint physical-frame contrasts and DRAFT §§9–10 decision rules."""

from pathlib import Path
import sys

import numpy as np
from scipy.special import betaincinv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tf_covariance_audit_20261018'))
from sampling import bootstrap_means, linear_summary, ratio_summary

N_BOOT = 20_000
SEED = 20261120
SBL_GAP = {'R1': 1, 'R0': -1}
CSTATE_GAP = {'A2': 1, 'CD': -1}
MIRROR_ARMS = ('C-hi', 'C-lo')
ADMISSION_ARMS = ('A2', 'CD', 'U', *MIRROR_ARMS)
MIN_ADMISSION_UNITS = 100
CSTATE_FRAMES = 200
CSTATE_KEYS_PER_FRAME = 34
NOT_EVALUABLE = 'not evaluable'
NOT_ESTABLISHED = 'not established'
UNCERTAIN = 'uncertain'
V1_SUPPORT = 'prospective intervention-level support'
V5_SUPPORT = 'mirror supports'


def estimates(fer_by_arm, frames):
    values = {arm: np.asarray(column) for arm, column in fer_by_arm.items()}
    if any(not np.isin(column, (0, 1)).all() for column in values.values()):
        raise ValueError('Per-key outcomes must be binary')
    draws, n_clusters = bootstrap_means(values, frames, n_boot=N_BOOT, seed=SEED)
    return {arm: float(np.mean(column)) for arm, column in values.items()}, draws, n_clusters


def mirror_ratios(point, draws):
    return {arm: ratio_summary(point, draws, {'A2': 1, arm: -1}, CSTATE_GAP)
            for arm in MIRROR_ARMS}


def select_v5_primary(half_width):
    return 'fer' if half_width is not None and half_width <= .25 else 'adm'


def ni_summary(fer_by_arm, frames, arm, *, point, draws, other='CD'):
    """Use the registered one-sided CP bound below five discordant frame clusters."""
    _, inverse, sizes = np.unique(frames, return_inverse=True, return_counts=True)
    n = len(sizes)
    if n == 0 or not np.all(sizes == sizes[0]):
        raise ValueError('CSTATE non-inferiority requires a complete balanced frame grid')
    candidate = np.asarray(fer_by_arm[arm], dtype=bool)
    reference = np.asarray(fer_by_arm[other], dtype=bool)
    harm = np.bincount(inverse, weights=candidate & ~reference).astype(int)
    benefit = np.bincount(inverse, weights=reference & ~candidate).astype(int)
    discordant = int(np.count_nonzero(harm + benefit))
    evidence = dict(discordant_frame_clusters=discordant,
                    candidate_only_failure_clusters=int(np.count_nonzero(harm)),
                    reference_only_failure_clusters=int(np.count_nonzero(benefit)))
    contrast = {arm: 1, other: -1}
    if discordant >= 5:
        return dict(linear_summary(point, draws, contrast), **evidence,
                    method='paired frame-cluster bootstrap')

    # The draft bounds the number of unobserved harmful keys in any cluster
    # by the largest observed harmful count, with one as the minimum cap.
    c_u = evidence['candidate_only_failure_clusters']
    max_harm = max(1, int(harm.max()))
    cp_upper = 1. if c_u == n else float(betaincinv(c_u + 1, n - c_u, .95))
    upper = cp_upper * max_harm / int(sizes[0])
    return dict(point=float(point[arm] - point[other]), ci_lo=None, ci_hi=upper,
                ci_width=None, contains_0=None, **evidence,
                method='one-sided 95% Clopper–Pearson upper bound',
                cp95_upper=cp_upper, max_harm_keys_per_frame_assumed=max_harm,
                n_frame_clusters=n, keys_per_frame=int(sizes[0]))


def _recovery(metric, positive='carries', negative='insufficient alone'):
    if not metric['evaluable']:
        return NOT_EVALUABLE
    if metric['ci_lo'] >= .5:
        return positive
    if metric['ci_hi'] <= .25:
        return negative
    return UNCERTAIN


def _direction(metric, positive, negative):
    if metric['ci_lo'] > 0:
        return positive
    if metric['ci_hi'] < 0:
        return negative
    return UNCERTAIN


def _noninferiority(metric, margin):
    if metric['ci_hi'] <= margin:
        return 'non-inferior'
    if metric['ci_lo'] is not None and metric['ci_lo'] > margin:
        return 'inferior'
    return UNCERTAIN


def _superiority(metric):
    if metric['ci_hi'] < 0:
        return 'superior'
    if metric['ci_lo'] >= 0:
        return 'not superior'
    return UNCERTAIN


def _mirror(ratios, prerequisite):
    halves = {arm: _recovery(ratios[arm]) if prerequisite else NOT_EVALUABLE
              for arm in MIRROR_ARMS}
    hi, lo = (halves[arm] for arm in MIRROR_ARMS)
    if NOT_EVALUABLE in (hi, lo):
        return dict(verdict=NOT_EVALUABLE, **halves)
    if (hi, lo) == ('carries', 'insufficient alone'):
        return dict(verdict=V5_SUPPORT, **halves)
    if (hi, lo) == ('insufficient alone', 'carries'):
        return dict(verdict='mirror opposite', **halves)
    return dict(verdict=NOT_ESTABLISHED, **halves)


def _layer(premises_ok, components, required):
    if not premises_ok or NOT_EVALUABLE in components:
        return NOT_EVALUABLE
    if components == required:
        return 'supported'
    return NOT_ESTABLISHED


def classify(metrics, *, margin, v5_primary):
    """Evaluate premises before the two support layers and their conjunction."""
    if v5_primary not in ('fer', 'adm'):
        raise ValueError('v5_primary must be fer or adm')
    if not 0 <= margin <= .005:
        raise ValueError('Non-inferiority margin must be in [0, .005]')
    prerequisites = {}
    for name in ('G_B', 'A2_minus_CD'):
        metric = metrics[name]
        if not metric.get('evaluable', True) or metric['ci_lo'] is None:
            prerequisites[name] = NOT_EVALUABLE
        else:
            prerequisites[name] = 'established' if metric['ci_lo'] > 0 else NOT_ESTABLISHED
    premises_ok = all(status == 'established' for status in prerequisites.values())
    cstate_premise = prerequisites['A2_minus_CD'] == 'established'

    lo, hi = (_recovery(metrics[f'phi_{arm}']) for arm in ('lo', 'hi'))
    shape = _direction(metrics['delta_lo'], 'projector superior', 'isotropic superior')
    if NOT_EVALUABLE in (lo, hi):
        v1 = NOT_EVALUABLE
    elif (lo, hi, shape) == ('carries', 'insufficient alone', 'projector superior'):
        v1 = V1_SUPPORT
    elif lo == 'insufficient alone':
        v1 = 'replay did not replicate'
    else:
        v1 = NOT_ESTABLISHED

    v2 = _recovery(metrics['phi_U2'], 'recovers', 'does not recover')
    v3 = _noninferiority(metrics['delta_UC'], margin)
    v4 = _superiority(metrics['delta_UA'])
    v5 = _mirror(metrics['psi'], cstate_premise)
    admission = metrics['admission']
    v5_adm = _mirror(admission['pi'], cstate_premise and admission['n_units'] >= MIN_ADMISSION_UNITS)
    selected = {'fer': v5, 'adm': v5_adm}[v5_primary]['verdict']

    mechanism = _layer(premises_ok, (v1, selected), (V1_SUPPORT, V5_SUPPORT))
    operational = _layer(premises_ok, (v2, v3, v4), ('recovers', 'non-inferior', 'superior'))
    joint = _layer(premises_ok, (mechanism, operational), ('supported', 'supported'))
    return dict(
        prerequisites=prerequisites, lo=lo, hi=hi, shape=shape, V1=v1, V2=v2, V3=v3, V4=v4,
        V5=v5, V5_adm=v5_adm, v5_primary=v5_primary, v5_primary_verdict=selected,
        C_hi_vs_CD=_noninferiority(metrics['delta_C_hi_CD'], margin),
        H=_direction(metrics['H'], 'harmful', 'beneficial'),
        layers=dict(spectral_mechanism=mechanism, operational_compatibility=operational, joint_claim=joint),
    )


def admission_summary(preferences, frames):
    """Estimate preference using the number of observed units as denominator."""
    n_units = len(frames)
    if n_units and (set(preferences) != set(ADMISSION_ARMS)
                    or any(len(preferences[arm]) != n_units for arm in ADMISSION_ARMS)):
        raise ValueError('Admission preferences must contain paired five-arm observations')
    if n_units < MIN_ADMISSION_UNITS:
        return dict(n_units=n_units, n_frame_clusters=len(set(frames)), pi={},
                    evaluable=False, reason='fewer than 100 admission units')
    point, draws, n_clusters = estimates(preferences, frames)
    ratios = mirror_ratios(point, draws)
    return dict(n_units=n_units, n_frame_clusters=n_clusters, preference_rates=point,
                gap=linear_summary(point, draws, CSTATE_GAP), pi=ratios,
                evaluable=all(ratio['evaluable'] for ratio in ratios.values()))


def _sign(point):
    return dict(point=float(point), sign='positive' if point > 0 else 'negative' if point < 0 else 'zero')


def readout(sbl_fer, sbl_frames, cstate_fer, cstate_frames, *, margin, v5_primary,
            cstate_common_mask, adm_preferences, adm_frames):
    _, cstate_sizes = np.unique(cstate_frames, return_counts=True)
    if len(cstate_sizes) != CSTATE_FRAMES or not np.all(cstate_sizes == CSTATE_KEYS_PER_FRAME):
        raise ValueError('CSTATE readout requires 200 complete physical frame clusters of 34 keys')
    mask = np.asarray(cstate_common_mask)
    if mask.dtype != np.bool_ or mask.shape != (len(cstate_frames),) or not mask.any():
        raise ValueError('Common-grid mask must select paired CSTATE rows at rho .3 and 6–11 dB')

    p, b, ns = estimates(sbl_fer, sbl_frames)
    q, c, nc = estimates(cstate_fer, cstate_frames)
    metrics = {
        'G_B': linear_summary(p, b, SBL_GAP),
        'delta_lo': linear_summary(p, b, {'S-isolo': 1, 'S-lo': -1}),
        'A2_minus_CD': linear_summary(q, c, CSTATE_GAP),
        'delta_UC': ni_summary(cstate_fer, cstate_frames, 'U', point=q, draws=c),
        'delta_UA': linear_summary(q, c, {'U': 1, 'A2': -1}),
        'delta_C_hi_CD': ni_summary(cstate_fer, cstate_frames, 'C-hi', point=q, draws=c),
        'psi': mirror_ratios(q, c),
        'admission': admission_summary(adm_preferences, adm_frames),
        'H': linear_summary(p, b, {'U2': 1, 'S-lo': -1}),
    }
    for name, arm in (('lo', 'S-lo'), ('hi', 'S-hi'), ('U2', 'U2')):
        metrics[f'phi_{name}'] = ratio_summary(p, b, {'R1': 1, arm: -1}, SBL_GAP)
    common_cstate = np.mean(np.asarray(cstate_fer['A2'])[mask]) - np.mean(np.asarray(cstate_fer['CD'])[mask])
    common_grid = dict(G_B=_sign(metrics['G_B']['point']), A2_minus_CD=_sign(common_cstate))
    secondary = {f'{a}_minus_R0': linear_summary(p, b, {a: 1, 'R0': -1}) for a in ('S-lo', 'U2')}
    secondary['U2_minus_S-lo'] = metrics['H']
    return dict(sbl_clusters=ns, cstate_clusters=nc, sbl_fer=p, cstate_fer=q, margin=margin,
                common_grid=common_grid, metrics=metrics, secondary=secondary,
                verdicts=classify(metrics, margin=margin, v5_primary=v5_primary))
