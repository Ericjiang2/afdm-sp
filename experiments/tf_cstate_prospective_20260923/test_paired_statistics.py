"""Finite-sample coverage and boundary tests for frozen paired inference."""
from __future__ import annotations

import json
from math import comb
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paired_statistics import MARGINAL_TAIL, cp_lower, cp_upper, paired_statistics


def _multinomial_probability(n, h, r, p_h, p_r):
    other = n-h-r
    return comb(n, h)*comb(n-h, r)*p_h**h*p_r**r*(1-p_h-p_r)**other


def test_exhaustive_small_n_multinomial_upper_coverage():
    # Enumerate every possible count triple, including p_h/p_r on boundaries.
    # The parameter mesh checks the exact joint law, not independent-binomial
    # sampling; the Bonferroni proof in the pre-registration covers all p.
    for n in range(1, 7):
        upper = {(h, r): cp_upper(h, n, MARGINAL_TAIL)-cp_lower(r, n, MARGINAL_TAIL)
                 for h in range(n+1) for r in range(n-h+1)}
        for a in range(11):
            for b in range(11-a):
                p_h, p_r = a/10, b/10
                delta = p_h-p_r
                coverage = sum(_multinomial_probability(n, h, r, p_h, p_r)
                               for (h, r), bound in upper.items()
                               if bound + 1e-14 >= delta)
                assert coverage >= .95-1e-12, (n, p_h, p_r, coverage)


def test_cp_zero_and_all_boundaries():
    n = 1024
    assert cp_lower(0, n, .025) == 0
    assert cp_upper(n, n, .025) == 1
    assert cp_upper(0, n, .025) == pytest.approx(1-.025**(1/n))
    assert cp_lower(n, n, .025) == pytest.approx(.025**(1/n))
    all_h = paired_statistics(n=n, both_correct=0, tf_only_correct=n,
                              combined_only_correct=0, neither_correct=0,
                              integrity_valid=True)
    all_r = paired_statistics(n=n, both_correct=0, tf_only_correct=0,
                              combined_only_correct=n, neither_correct=0,
                              integrity_valid=True)
    assert all_h['delta_hat'] == all_h['primary_upper_95'] == 1
    assert not all_h['primary_pass']
    assert all_r['delta_hat'] == -1
    assert all_r['primary_upper_95'] < 0
    assert all_r['primary_pass']
    with pytest.raises(ValueError):
        cp_upper(n+1, n, .025)


def test_n1024_primary_pass_and_integrity_gate():
    counts = dict(n=1024, both_correct=994, tf_only_correct=0,
                  combined_only_correct=30, neither_correct=0)
    result = paired_statistics(**counts, integrity_valid=True)
    assert result['primary_pass']
    assert result['primary_upper_95'] < 0
    assert result['delta_hat'] == -30/1024
    assert result['frozen_tf_fer']['errors'] == 30
    assert result['combined_fer']['errors'] == 0
    assert json.loads(json.dumps(result)) == result
    invalid = paired_statistics(**counts, integrity_valid=False)
    assert not invalid['primary_pass']
    assert invalid['primary_status'] == 'invalid_integrity'


def test_auxiliary_mcnemar_cannot_replace_primary():
    # Conditional discordance is significant but the pre-registered
    # unconditional conservative bound is not below zero.
    result = paired_statistics(n=1024, both_correct=1018, tf_only_correct=0,
                               combined_only_correct=6, neither_correct=0,
                               integrity_valid=True)
    assert result['auxiliary_exact_conditional_mcnemar_one_sided_p'] == pytest.approx(1/64)
    assert result['primary_upper_95'] > 0
    assert not result['primary_pass']
    no_discordance = paired_statistics(n=1024, both_correct=1024, tf_only_correct=0,
                                      combined_only_correct=0, neither_correct=0,
                                      integrity_valid=True)
    assert no_discordance['auxiliary_exact_conditional_mcnemar_one_sided_p'] == 1
    assert not no_discordance['primary_pass']


def test_complete_table_required_without_filtering():
    with pytest.raises(ValueError, match='complete n'):
        paired_statistics(n=1024, both_correct=1000, tf_only_correct=1,
                          combined_only_correct=1, neither_correct=1,
                          integrity_valid=True)
    with pytest.raises(ValueError, match='explicit bool'):
        paired_statistics(n=1, both_correct=1, tf_only_correct=0,
                          combined_only_correct=0, neither_correct=0,
                          integrity_valid=1)
    with pytest.raises(ValueError, match='nonnegative integer'):
        paired_statistics(n=1, both_correct=True, tf_only_correct=0,
                          combined_only_correct=0, neither_correct=0,
                          integrity_valid=True)
