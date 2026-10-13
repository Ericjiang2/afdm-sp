"""Fixed-family paired FER intervals; outcomes are independent exogenous blocks."""
import numpy as np

from afdm_sp_joint_unrolled.supplement_statistics import paired_delta


def paired_fer(arm, reference, *, alpha, comparisons):
    left, right = np.asarray(arm), np.asarray(reference)
    if (left.ndim != 1 or not len(left) or right.shape != left.shape
            or not np.isin(left,(0,1)).all() or not np.isin(right,(0,1)).all()):
        raise ValueError('paired binary error vectors on identical blocks required')
    n = len(left)
    n10 = int(np.count_nonzero((left == 1) & (right == 0)))
    n01 = int(np.count_nonzero((left == 0) & (right == 1)))
    benefit = paired_delta(n01,n10,n,alpha_family=alpha,m=comparisons)
    return dict(n=n,n10=n10,n01=n01,arm_errors=int(left.sum()),reference_errors=int(right.sum()),
        difference=(n10-n01)/n,lower=-float(benefit['upper']),upper=-float(benefit['lower']),
        one_sided_marginal_alpha=float(benefit['tail']),family_alpha=alpha,comparisons=comparisons,
        definition='FER_arm minus FER_reference; negative is improvement',
        method='paired multinomial discordances with exact CP marginal bounds and union bound')


def confirmation_decisions(rows):
    expected = {(snr,reference) for snr in (7,8,9) for reference in ('A2','B_star_1')}
    if len(rows)!=6 or {(r['snr_db'],r['reference']) for r in rows}!=expected:
        raise ValueError('all six confirmation contrasts required')
    for row in rows:
        if row['n']!=2048 or row['family_alpha']!=.025 or row['comparisons']!=6:
            raise ValueError('confirmation denominator or alpha allocation changed')
        row['improvement_supported'] = row['upper'] < 0
        row['meaningful_improvement_supported'] = row['upper'] <= -.005
        row['noninferiority_005_supported'] = row['upper'] <= .005
    primary = {r['snr_db']:r for r in rows if r['reference']=='B_star_1'}
    return dict(improvement_7_8=all(primary[s]['upper']<0 for s in (7,8)),
        meaningful_improvement_7_8=all(primary[s]['upper']<=-.005 for s in (7,8)),
        noninferiority_9=primary[9]['upper']<=.005,
        strong_reference_rule_met=all(primary[s]['upper']<0 for s in (7,8)) and primary[9]['upper']<=.005,
        scope='fixed G0/N1024 three-arm series; no broader classical-optimality or mechanism claim')
