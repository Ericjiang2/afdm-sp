# Ideal statistical linearization: the approved affine revision

## Target and outcome

**COHERENT AS STATED.** This revision replaces the derivative tangent with the
minimum-MSE affine projection under the **exact saved joint posterior**, using
real augmentation to retain all pseudo-covariance information. It improves
the tangent, but still passes the registered residual-energy gate in only
**1/48 conditions: 1/24 with pilot, 0/24 without**.

All 48 joint covariance matrices are positive definite with every positive
mode retained. Consequently the ideal affine optimum, not an arbitrary tangent
or a rank-truncated surrogate, still leaves more than `0.1 N sigma2` residual
energy in 47/48 cases. This supports closing the proposed unqualified affine
residual-neglect route on this diagnostic grid. It is not a theorem that affine
inference always has bad LLRs, nor a no-go for mode-conditioned or nonlinear
methods or production receivers.

## Invariant object, assumptions and scope

The invariant object is the exact conditional posterior distribution of the
fixed-geometry physical signal and its latent gain/data vector. Define real
augmented variables

`z=[Re h; Im h; Re d; Im d]`,

`f=[Re s; Im s]`, `s=sum_p h_p U_p(pilot+d)`.

We seek the affine map `Az+b` minimizing `E[||f-Az-b||² | y]`. The expectation
uses the full saved finite-data / proper-conditional-Gaussian-gain mixture from
ORACLE-01. It does not assert posterior independence, proper posterior marginals,
or a single Gaussian posterior. All model priors remain those of the original
oracle; posterior moments are never recycled as independent priors.

Real trace equals complex signal energy. Proper observation noise has real
covariance `(sigma2/2) I_(2N)`, so its real trace is `N sigma2`, not `2N sigma2`.
The generic API permits M observations and uses `M sigma2`.

## Derivation strategy and map

1. Compute exact real joint moments by conditioning on each finite d.
2. Project the centered physical signal onto the real linear span of z.
3. Prove residual orthogonality and the all-affine covariance/MSE optimum.
4. Verify by direct conditional residual covariance, not only matrix subtraction.
5. Assess numerical support and compare the fixed residual gate on every case.

Steps 1–4 are identities/propositions under the stated model. Step 5 is a
registered numerical/engineering decision, not a new theorem or novelty claim.

## Exact augmented moments

For a complex matrix B write

`R(B)=[[Re B,-Im B],[Im B,Re B]]`.

For each candidate d_k, let `B_k=[U_p(pilot+d_k)]` and
`h|d_k,y ~ CN(m_k,C_k)`. In the conditional real gain coordinates,

`r_k=[Re m_k;Im m_k]`, `V_k=R(C_k)/2`, `T_k=R(B_k)`.

The conditional mean of z is `[r_k;Re d_k;Im d_k]`; its conditional covariance
contains V_k in the gain block and zero elsewhere. The conditional mean of f
is `T_k r_k`; its conditional covariance is `T_k V_k T_k^T`; its conditional
f-z covariance has `T_k V_k` in the gain columns and zero in the data columns.

Weighted conditional moments plus between-component outer products give
`mu_z,mu_f,Czz,Cfz,Cf`. This construction retains the mixture's improper and
cross-dependent structure. It does not infer full joint real moments from
only conjugate marginal covariance matrices.

## Optimal affine projection and proof

In exact arithmetic, let `A*=Cfz Czz^dagger` on the covariance support and
`b*=mu_f-A*mu_z`. Covariance-null directions of z are deterministic, so Cfz
annihilates them. Thus

`Cov(f-A*z-b*,z)=Cfz-A*Czz=0`,

`Cres=Cf-Cfz Czz^dagger Czf`.

For any other real A and b, centering first gives

`E||f-Az-b||² = tr(Cres)`
` + tr[(A-A*)Czz(A-A*)^T] + ||mu_f-A mu_z-b||²`.

Both extra terms are nonnegative. Therefore A*,b* achieve minimum MSE among
**all real affine maps** of z, including complex widely-linear maps with
conjugate terms. The solution is unique on the covariance support; arbitrary
null-space coefficients do not change the predictor. This is standard
orthogonal projection/statistical linear regression, not a novel theorem.

The code also computes each residual conditional on d directly. Its random
gain slope is `T_k-A[:,gain]`, and its conditional mean is
`T_k r_k-A mu_z,k-b`. Mixing the resulting PSD covariance and mean outer products
provides stable residual MSE. It is compared with the subtraction formula and
with `Cfz-A Czz`; no epsilon is added to make a matrix invertible.

## Numerical support and a required sensitivity control

The registered retained support is `lambda > 1e-12 lambda_max`. Negative
eigenvalues beyond scale-dependent machine roundoff are rejected. Within-roundoff
negative mass, all discarded positive mass, and the retained/full positive ranks
are reported. No discarded direction is silently called an exact null space.

For every case the code additionally computes the solution using **every
strictly positive eigenvalue**, its direct residual covariance/energy, and the
change relative to the rank-tolerant solution. The formal discarded explanatory
energy `sum_i ||Cfz v_i||²/lambda_i` is reported, but is not a reliable certificate
when those eigenvalues themselves are numerically ambiguous. Any positive-mode
discard labels that result `rank_ambiguous_no_all_affine_certificate`; it must
not be used as a universal affine lower bound merely because discarded mass is
small.

The test suite demonstrates why: a known-data linear model has gain variances
1 and 1e−16, while the second response is amplified by 1e8. Discarded covariance
mass is below 1e−15, yet the truncated residual energy is 1 while the full-positive
linear solution gives zero to numerical accuracy. Small support mass alone
cannot bound predictive error.

**Actual cohort:** no positive mode was discarded in any of the 48 cases.
The minimum joint eigenvalue is 3.51e−6 and the minimum
`lambda_min/lambda_max` is 1.407e−5, well separated from the 1e−12 cutoff.
Full-positive sensitivity is exactly zero because the same support is used.
The all-affine optimum interpretation is therefore not undermined by support
truncation in this cohort, within the stated floating-point validation.

## Frozen revision and diagnostic results

The main task registered this one justified mechanism revision before execution.
`execution/slr/v1/registration.json` then froze implementation/tests, inherited
source and input hashes, support rule, gate and all 48 conditions before any
SLR computation. The grid is the **same already exposed diagnostic grid**;
this is feedback-driven model examination, not an independent confirmation set.
There are six independent (N,seed) exogenous clusters; all geometry/pilot/noise
conditions are retained. No new selection or tuning follows these results.

The frozen gate is `tr(Cres) <= 0.1 N sigma2`.

|Registered group|Pass|Mean optimal residual/noise energy|Range|
|---|---:|---:|---:|
|All|1/48|0.440710|0.000359–0.893670|
|No pilot|0/24|0.541992|0.271048–0.893670|
|Pilot 0.6|1/24|0.339428|0.000359–0.648728|
|Separated geometry|0/24|0.484459|0.281438–0.793535|
|Near-duplicate geometry|1/24|0.396961|0.000359–0.893670|

The sole pass remains case 44; it is not selected as a new operating regime.
These are finite-grid diagnostics, not estimated population pass probabilities
or statistical significance claims.

For pilot-present cases, the derivative tangent's uncentered residual energy
averages 0.696543. Correcting only the residual mean reduces it to 0.520314;
the ideal affine slope/intercept reduce it further to 0.337077. Thus both mean
correction and optimal slope matter, yet 23/24 pilot-present cases still fail
the registered residual-neglect gate. Comparing only with the biased tangent
would overstate the contribution of slope optimization.

Without pilot, global QPSK rotation symmetry forces Cfz=0 and posterior latent
means to zero. The best affine predictor is the constant `E[f|y]`; its remaining
energy is the exact posterior signal variance 0.511960 on average. SLR's gain
over the uncentered tangent (0.838557 average energy) is entirely the removed
mean; improvement over the centered tangent is numerical zero. A global affine
projection cannot encode the rotational product dependence in this setting.

## Tests, raw evidence and cost

Six deterministic tests pass:

- Known data and known gain give exact affine signal maps and zero residual.
- A correlated two-point h=d mixture is exactly affine on its support, so SLR
  removes the large derivative-tangent error. This is a positive counterexample
  to declaring every bilinear posterior unsuitable for affine approximation.
- A symmetric three-point h=d in {-1,0,+1} gives f=d²: optimal slope zero,
  intercept 0.5, residual energy 0.25. No affine map can remove that quadratic
  dependence under this distribution.
- Rank-deficient real covariance and impropriety are preserved.
- The tiny-support/large-response sensitivity example prevents a false bound.

Tests took 0.004 s unittest time, 0.017363 process CPU including discovery. The
complete 48-case evaluation took 0.126233 CPU s / 0.132150 wall s, below the
60 CPU s / 120 wall s cap. No new oracle, scalar_joint, receiver or data-generator
calls occurred. Initial test import failed before the module existed; it ran
no diagnostic. All actual numeric tests and the grid verified Accelerate mode 1
before/after with all five thread variables set to 1.

Full residual-z orthogonality error is at most **7.12e−16**. Direct residual
covariance versus subtraction formula differs by at most **1.14e−15**. Every
actual residual covariance is positive definite (minimum eigenvalue 6.63e−6).
All optimal residuals are no greater than the centered tangent, within roundoff.

`results.json` includes every case and diagnostic; 48 raw NPZ files retain joint
means/covariances, full spectra, affine maps/intercepts, direct residual covariance,
orthogonality and full-positive sensitivity. `recount.json` verifies all source,
input and output hashes, the 48-case/96-event ledger, unchanged gate, positive
support retention, PSD and comparison identities. This is same-author evidence,
not a replacement for independent review.

Results SHA256: `f651d5b8ac0ad0a428d0560afd20688fe702cb3231000783b62bfd178c390402`.

## Cost, deployability and contribution boundary

For K finite data words, these dense moments and projections require the oracle's
component means/covariances and probabilities, plus dense real covariance of
dimension D=2P+2N. The explicit implementation costs roughly
O(K[(M+P+N)² + MP² + M²P]) for moment/residual assembly and O(D³) for the
eigensolve, aside from the exponential enumeration that produced the oracle.
This is not a low-cost receiver API or independent-message construction.

The exact posterior coefficients depend on the current observation through the
entire joint posterior. A deployable SLR method would need a separate coherent
approximation for these moments and messages. Merely substituting this affine
map into AMP would not establish valid Onsager/extrinsic terms.

The ideal result strengthens the bounded rejection: in these 47 cases, simply
choosing a better real affine map cannot push residual energy under the fixed
gate, since even the exact-posterior optimum fails. It does **not** prove that
non-negligible residual necessarily yields poor LLRs, nor rule out explicit
nonlinear residual models, resolved-mode approximations or other distributions.
The main task should close this candidate according to its existing gate, not
start an unregistered chain of new mechanisms to obtain a positive result.
