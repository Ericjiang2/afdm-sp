# Exact fixed-geometry posterior oracle

## Target

ORACLE-01 supplies an exact small-model reference for the joint data/gain
posterior, including component moments needed by SCHUR-01 and REMAINDER-01.
It does not run or approximate a complete receiver.

## Status

**COHERENT AS STATED.** Analytic integration and finite enumeration are exact
for the declared model, subject to floating-point arithmetic. The implementation
and deterministic mathematical tests pass. The subsequent grouped-bit revision
and registered comparison are documented in `ORACLE_COMPARISON.md`: the combined
suite has 15 tests (12 oracle, 3 comparison). Oracle correctness and the actual
approximation comparison are separate evidence layers.

## Invariant object

The normalized joint posterior `p(h,d | y)` from one fixed likelihood and
independent model priors. A Gaussian working posterior or a local Schur proxy is
not substituted for this object.

## Assumptions and notation

- Fixed complex path operators `U_p` have shape M by N; gains h have length P.
- `x_d = pilot + d`; `B_d = [U_1 x_d, ..., U_P x_d]`.
- `y = B_d h + w`, with proper `w ~ CN(0, sigma2 I)`, `sigma2 > 0`.
- `h ~ CN(m0,C0)` is proper, independent of d and w, with possibly singular
  positive-semidefinite C0. C0=0 means known h=m0.
- Data d belongs to an explicitly supplied finite, unique codebook. Probabilities
  pi_d are a normalized nonnegative prior, independent of the current y.
  Zero probabilities are allowed. Code completeness and independent provenance
  are caller responsibilities; an API cannot infer their scientific legitimacy.
- `Cov(a,b)=E[(a-Ea)(b-Eb)^H]`; pseudo-covariance uses transpose instead of H.

## Derivation strategy and map

1. Integrate the independent Gaussian gain prior for each data word (identity).
2. Obtain its conditional gain posterior on the prior support (identity).
3. Normalize the finite mixture by logsumexp (identity).
4. Apply total expectation/covariance and finite bit marginalization (identity).

No approximation enters this chain. Numerical handling of PSD roundoff is
disclosed separately below.

## Main derivation

Write C0=F F^H with one column for every strictly positive eigenvalue, and
`h=m0+F z`, `z~CN(0,I_r)`. With `T_d=B_d F` and `e_d=y-B_d m0`,

`S_d = sigma2 I + T_d T_d^H`,

`log p(y|d) = -M log(pi) - log det(S_d) - e_d^H S_d^{-1} e_d`.

This includes the data-dependent log determinant; residual-only scoring is
generally not the same posterior. Observation noise makes S_d positive definite
even for singular/zero C0. Cholesky solves evaluate the quadratic and logdet.

For each component, let

`J_d=I_r + T_d^H T_d / sigma2`,

`a_d=J_d^{-1} T_d^H e_d / sigma2`,

`m_d=m0+F a_d`, `C_d^h=F J_d^{-1} F^H`.

The conditional `h|d,y` is proper Gaussian on the same affine support. Code
forms C_d^h as A A^H using the Cholesky factor of J_d, avoiding cancellation
in `C0-C0 B_d^H S_d^{-1} B_d C0`. No inverse of singular C0 is taken. For r=0,
`m_d=m0`, `C_d^h=0`, and the evidence becomes the known-channel likelihood.

`ell_d=log(pi_d)+log p(y|d)`, `log Z=logsumexp(ell)`,
`w_d=exp(ell_d-log Z)`.

The exact gain/data moments are

`mh=sum_d w_d m_d`, `md=sum_d w_d d`,

`Ch=sum_d w_d [C_d^h+(m_d-mh)(m_d-mh)^H]`,

`Cd=sum_d w_d (d-md)(d-md)^H`,

`Chd=sum_d w_d (m_d-mh)(d-md)^H`.

Conditional gain pseudo-covariance is zero, but a mixture need not be proper:
the returned gain, data and cross pseudo-covariances retain the corresponding
between-component outer products without conjugation. Discarding them is an
additional approximation by a consumer, not an oracle identity.

For bit label b_j(d), the LLR convention is

`LLR_j=logsumexp(ell_d: b_j=0)-logsumexp(ell_d: b_j=1)`.

Absent/zero-prior hypotheses yield exact signed infinities. This is deliberate;
no artificial clipping or floor is applied. `log_probabilities` preserves rare
component information even where exponentiation underflows to zero numerically.

## API and handoff

`enumerate_qpsk(n, parity_check=None, amplitude=0.5, max_words=65536)` returns
`(candidates[K,N], bits[K,2N])`. Labels follow project all-I then all-Q order,
bit 0 maps to +a,
and a binary parity-check matrix enforces `H bits = 0 mod 2`. The cap applies
before filtering, so a short-code condition cannot conceal a huge enumeration.
Other finite alphabets/codes may be supplied directly to `exact_posterior`.

`exact_posterior(y, operators, pilot, candidates, gain_mean, gain_cov,
noise_variance, *, bits=None, prior_probabilities=None)` returns:

- `probabilities`, `log_probabilities`, `log_likelihood`, `log_evidence`, `llr`;
- `h_mean`, `h_cov`, `d_mean`, `d_cov`, `h_d_cov`;
- `h_pseudo_cov`, `d_pseudo_cov`, `h_d_pseudo_cov`;
- `component_h_mean[K,P]`, `component_h_cov[K,P,P]`, in candidate input order;
- `prior_support_rank`, `prior_roundoff_correction`, `enumeration_size`.

For REMAINDER, condition on d: any quantity affine in h has its exact mean and
covariance from the component fields, followed by the same weighted mixture.
Do not replace the conditional h distribution by the unconditional h moments.

## Validation and execution evidence

Tests were written before implementation. The initial run failed with
`ModuleNotFoundError` for the not-yet-created oracle module (one import error;
no receiver calls). After implementation 10 tests passed. Following stricter
real-input validation and a tiny-positive-variance contract, 11 tests passed:
0.069 s unittest time, 0.144645 s process CPU including discovery/imports. A final
complex-noise input guard regression passed the same 11 tests in 0.072 s unittest
time and 0.151860 s process CPU. AST parsing also passed for both Python files.
All five thread environment variables were 1. The reused frozen
`controls/thread_binding.py` verified actual Accelerate calling-thread mode 1
before and after the final run; threadpoolctl 3.7.0 reported no other pools.
The two earlier short runs used the five environment settings but did not
explicitly inspect Accelerate mode; they are not the effective-thread evidence.

Historical pre-grouped-bit-revision source SHA256 (not current evidence):

- `exact_oracle.py`: `ad79f6143d82c2e05d2be60566c868df13f955b3843afe1d8aa056bd50651e07`
- `tests/test_exact_oracle.py`: `f2349edd5c19e84fc31b106fe873d20d27a2d32a81dc94cdb4f63dc2f955a9c1`

The initial API used interleaved labels. Before any comparison campaign, it was
corrected to the project's all-I then all-Q order; a new contract test compares
the enumerated prior means with frozen `messages.moments`. The current source
hashes are frozen in the new mission's `execution/oracle/comparison_v1/registration.json`:
`exact_oracle.py` = `d6fae6c9d0e708db9fb2ab6c3809729f12146bb307802f2cb892be6f795b5b77`.
No comparison result was generated using the old bit mapping.

Coverage:

- Known data against a separately computed full-precision Gaussian posterior.
- Known channel against direct finite residual likelihoods.
- Evidence/normalization against an independent determinant-lemma/precision form.
- Scalar gain integration against 24 by 24 Gauss-Hermite quadrature, including
  posterior first and second gain moments; tolerances 1e-13.
- Singular support and path permutation; strictly positive variance 1e-20 is
  retained, not cut off or inflated by epsilon.
- No-pilot global QPSK phase ambiguity: zero marginal LLR/means can coexist with
  nonzero h-d pseudo-cross covariance. This is ambiguity, not failure of Bayes.
- Eight-word length-4 even-parity code with explicit nonuniform independent prior;
  conditional mixture cross-covariance and legal-bit constraints.
- Extreme finite LLR and exact zero-prior mass; invalid shape, covariance,
  nonfinite, duplicate-word, probability and parity inputs reject explicitly.
- Actual frozen `physical.py` N=2 operators with nonperiodic CPP and fractional
  Doppler; complete path action is reused, not rounded to integer Doppler.

Test sizes are N=1 or 2, at most 16 data words. No N1024 inference, Monte Carlo
FER run, server job, hidden data selection, or new physical implementation.

## Remarks and interpretation

Dropping h-d dependence from the **exact marginals** leaves those marginals
(and therefore LLRs) unchanged by definition. Overconfidence is a claim about a
specific approximate inference procedure, not a theorem that any factorization
alone changes LLRs. Comparisons must name that procedure and hold priors fixed.

Likewise, a no-pilot global phase mixture has legitimate uncertainty that a
single local Gaussian may miss. A favorable local covariance comparison cannot
by itself exclude discrete multimodality as the cause of error.

## Boundaries, non-claims and open risks

Enumeration costs exponentially in data bits. Each component currently uses
dense M-dimensional evidence Cholesky plus an r-dimensional posterior solve;
this is an oracle, not a fast receiver proposal. A single admissible data word
is the known-data limit and does not certify the supplied codebook is complete.

Hermitian/PSD validation allows only scale-dependent machine roundoff
`64 eps P ||C0||2`. All positive eigenvalues are retained; negative values inside
that tolerance are removed, and the actual covariance change is returned as
`prior_roundoff_correction`. Invalid negative eigenvalues fail. There is no
jitter or arbitrary epsilon regularization. Severe finite-input overflow or
loss of numerical positive definiteness fails visibly rather than falling back.

Input priors learned from this same y invalidate the independent-prior Bayes
interpretation unless a separate coherent probabilistic model justifies them.
The oracle verifies mathematical reference values, not novelty, calibration of
the production receiver, or causal/FER benefit of preserving coupling.
