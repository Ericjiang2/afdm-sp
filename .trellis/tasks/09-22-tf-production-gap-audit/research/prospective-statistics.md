# Frozen prospective paired statistics

This records the analysis rule before generating the independent prospective
observations. The 6.5 dB cell has exactly 1,024 paired frames and is the sole
primary confirmation cell. The 6 and 7 dB cells are descriptive. A frame is
never removed because its syndrome, decision, runtime, or error is unfavorable.
An incomplete pair or failed evidence/source integrity makes the primary result
invalid, rather than changing its denominator.

## Paired table and primary estimand

Let `h` count frozen TF correct / TF+CSTATE wrong; let `r` count frozen TF
wrong / TF+CSTATE correct. Also record both correct and neither correct, with
all four cells summing to `n=1024`. The combined-minus-frozen FER difference is

`Delta = p_h - p_r`, estimated by `(h-r)/1024`.

Across independently generated paired frames, `(h,r,n-h-r)` is multinomial;
each marginal count separately has a binomial distribution with denominator
`n`. The counts are dependent, but the following simultaneous argument does
not assume independence.

For a count `k` in `n`, define one-sided Clopper–Pearson limits at tail
`a=0.025` using the beta quantile `B^{-1}`:

- `L(k,n,a)=0` when `k=0`, else `B^{-1}(a;k,n-k+1)`.
- `U(k,n,a)=1` when `k=n`, else `B^{-1}(1-a;k+1,n-k)`.

The frozen 95% conservative upper confidence bound is

`U_Delta = U(h,1024,0.025) - L(r,1024,0.025)`.

Each component fails in its adverse direction with probability at most 0.025.
By the union bound, both cover simultaneously with probability at least 0.95,
irrespective of the dependence of `h` and `r`. On that simultaneous event,
`Delta <= U_Delta`. Discrete binomial tails and Bonferroni allocation can make
actual coverage greater than 95%; this interval is intentionally conservative.
The primary pass condition is **strictly `U_Delta < 0` and all preregistered
integrity checks valid**. Equality to zero does not pass. The code fixes these
tails and does not allow a post-outcome alpha override.

This construction is mathematically valid for the requested finite-sample
paired primary claim. It may require more rescue discordances than an exact
conditional McNemar test, because it also bounds the unconditional magnitude
of the FER difference. That is a power tradeoff, not a reason to replace the
registered primary test after outcomes are seen.

## Auxiliary and descriptive results

For `d=h+r>0`, the one-sided exact conditional McNemar p-value for an
improvement is `Pr[Binomial(d,1/2) <= h]`; for `d=0`, it is 1. It is reported
only as an auxiliary diagnostic and never changes `U_Delta` or the pass rule.
For example, with `h=0,r=6,n=1024`, the auxiliary p-value is `1/64`, while the
conservative primary bound remains positive. This explicit disagreement is
covered by the unit tests.

Each arm's FER is reported with a separate descriptive two-sided 95%
Clopper–Pearson interval using 0.025 in each tail. These intervals do not form
the primary paired comparison. The 0.5 s deadline paired outcome table is
separate from eventual results: use the latest decision actually ready by the
deadline; a later unfinished branch cannot erase an earlier checkpoint. A
missing deadline decision is recorded as missing/unready and counts as a
**system deadline failure** in the full-`n=1024` deadline table. This does not
invent decoded bits or label them bit errors. Separately report the number of
ready decisions and their decoded errors; ready-only error counts never replace
the full-denominator system deadline comparison. No deadline result substitutes
for eventual complete-pair primary counts.

`paired_statistics.py` accepts four complete-table counts and an explicit
integrity boolean, returns only JSON-safe scalars/dicts, and raises on invalid
counts. `test_paired_statistics.py` enumerates every count triple for small `n`
against a grid of multinomial parameters, including boundaries, and checks
coverage at least 95%; the union-bound proof above covers parameters outside
that finite test grid. The tests also cover `h/r=0/n`, synthetic `n=1024`
primary pass/fail, invalid integrity, and a significant auxiliary p-value that
cannot override a nonpassing primary bound.

## Statistical sources

- Clopper & Pearson, *The Use of Confidence or Fiducial Limits Illustrated in
  the Case of the Binomial*, Biometrika 26 (1934), 404–413:
  https://doi.org/10.1093/biomet/26.4.404
- SciPy documents its `binomtest(...).proportion_ci(method='exact')` as the
  Clopper–Pearson method and its one-sided binomial `alternative` semantics:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html
- SciPy's beta distribution documentation defines the inverse CDF used for the
  explicit limits: https://docs.scipy.org/doc/scipy/tutorial/stats/continuous_beta.html

The Bonferroni simultaneous-coverage step follows directly from the union
bound: `Pr(failure of either one-sided bound) <= 0.025+0.025=0.05`.
