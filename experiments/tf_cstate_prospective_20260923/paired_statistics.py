"""Frozen paired primary inference for the prospective 6.5 dB TF comparison.

The primary confidence bound uses two marginal one-sided Clopper--Pearson
limits with Bonferroni tail allocation. McNemar's conditional exact p-value
is diagnostic only and never changes the primary decision.
"""
from __future__ import annotations

from numbers import Integral

from scipy.stats import beta, binomtest


CONFIDENCE = 0.95
MARGINAL_TAIL = (1-CONFIDENCE)/2  # 0.025 for each one-sided discordant bound


def _count(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')
    return int(value)


def cp_lower(k: int, n: int, tail: float) -> float:
    """One-sided exact lower binomial limit, including k=0 and k=n."""
    k, n = _count('k', k), _count('n', n)
    if n == 0 or k > n or not 0 < tail < 1:
        raise ValueError('invalid binomial lower-bound arguments')
    return 0.0 if k == 0 else float(beta.ppf(tail, k, n-k+1))


def cp_upper(k: int, n: int, tail: float) -> float:
    """One-sided exact upper binomial limit, including k=0 and k=n."""
    k, n = _count('k', k), _count('n', n)
    if n == 0 or k > n or not 0 < tail < 1:
        raise ValueError('invalid binomial upper-bound arguments')
    return 1.0 if k == n else float(beta.ppf(1-tail, k+1, n-k))


def fer_interval(k: int, n: int) -> dict:
    """Descriptive two-sided 95% Clopper--Pearson FER interval."""
    k, n = _count('k', k), _count('n', n)
    if n == 0 or k > n:
        raise ValueError('invalid FER count or denominator')
    return dict(errors=k, total=n, estimate=k/n,
                lower_95=cp_lower(k, n, (1-CONFIDENCE)/2),
                upper_95=cp_upper(k, n, (1-CONFIDENCE)/2))


def paired_statistics(*, n: int, both_correct: int, tf_only_correct: int,
                      combined_only_correct: int, neither_correct: int,
                      integrity_valid: bool) -> dict:
    """Analyze the complete paired 2x2 table, with no excluded observations.

    h=tf_only_correct and r=combined_only_correct. Delta is combined FER minus
    frozen TF FER, so a negative upper bound is required for a primary pass.
    """
    n = _count('n', n)
    if n == 0:
        raise ValueError('paired table cannot be empty')
    both = _count('both_correct', both_correct)
    h = _count('tf_only_correct', tf_only_correct)
    r = _count('combined_only_correct', combined_only_correct)
    neither = _count('neither_correct', neither_correct)
    if both+h+r+neither != n:
        raise ValueError('paired 2x2 counts must sum to the complete n')
    if type(integrity_valid) is not bool:
        raise ValueError('integrity_valid must be an explicit bool')

    upper_h = cp_upper(h, n, MARGINAL_TAIL)
    lower_r = cp_lower(r, n, MARGINAL_TAIL)
    upper_delta = upper_h-lower_r
    discordant = h+r
    auxiliary_p = (1.0 if discordant == 0 else
                   float(binomtest(h, discordant, p=.5, alternative='less').pvalue))
    return dict(n=n,
        table=dict(both_correct=both, tf_only_correct=h,
                   combined_only_correct=r, neither_correct=neither),
        discordant_count=discordant,
        delta_hat=(h-r)/n,
        delta_definition='combined_FER_minus_frozen_TF_FER',
        primary_upper_95=upper_delta,
        primary_components=dict(h_upper_one_sided_97p5=upper_h,
                                r_lower_one_sided_97p5=lower_r,
                                marginal_tail_each=MARGINAL_TAIL),
        primary_pass=bool(integrity_valid and upper_delta < 0),
        integrity_valid=integrity_valid,
        primary_status=('invalid_integrity' if not integrity_valid else
                        'pass' if upper_delta < 0 else 'not_pass'),
        auxiliary_exact_conditional_mcnemar_one_sided_p=auxiliary_p,
        auxiliary_role='descriptive_only_not_primary',
        frozen_tf_fer=fer_interval(r+neither, n),
        combined_fer=fer_interval(h+neither, n))
