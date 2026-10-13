# Conditional scores versus soft messages

MESSAGE-01 finds a concrete distinction in new local mathematical cases:
exact gain elimination at one data vector is valid, but freezing the other
symbols still changes the soft data posterior. Genuine continuous Gaussian
tilted integration is also validated as a separate probability object. These
results justify studying data integration; they do not demonstrate production
receiver performance or establish that one approximation dominates generally.

## Discrete same-observation comparison

For each of 16 conditions from **4 independent exogenous draws**, all methods
receive the same observation, pilot, channel prior, noise variance, and incoming
bit factors. There are two fixed geometries (separated / near repeated paths),
two noise variances (0.2 / 1), `N=2`, and 16 uncoded QPSK words. The gain prior is
nonzero-mean and complex-correlated. A correlated base data prior is combined
with observation-independent bit incoming factors; it is not replaced by its
marginal LLRs.

The four explicitly different objects are:

1. **Profile marginal surrogate:** optimize latent Gaussian gains separately
   for every full word, then normalize the exponentiated optimized objective
   with the same data prior. This omits the variable log determinant and is not
   the exact marginal likelihood.
2. **Mean-H marginal surrogate:** fit conditional mean gains at `pilot+E_prior[d]`,
   fix that channel, then enumerate all words. This is a plug-in approximation,
   not an independent known-channel prior or a production receiver replay.
3. **Collapsed single-symbol conditional:** use exact gain-integrated likelihood,
   freeze each nuisance symbol to its joint prior-mode value, and enumerate the
   target symbol. The same correlated prior is restricted to that slice. No
   true data value is supplied to inference. Conditioning is exact on that
   slice; it differs from marginalizing nuisance symbols.
4. **Exact discrete marginal:** evaluate the collapsed likelihood at every word
   and sum over nuisance symbols. Compare with the old independent dense exact
   oracle under exactly the same prior and inputs.

Metrics compare each output with the exact posterior, averaged over paired
conditions. They are diagnostic approximation errors, without population
confidence intervals or an independent production test claim.

| Method | LLR RMSE | Bit probability MSE | Bernoulli KL |
|---|---:|---:|---:|
| Profile marginal surrogate | 0.4692 | 0.00756 | 0.02015 |
| Mean-H marginal surrogate | 4.3102 | 0.06814 | 0.64840 |
| Collapsed single-symbol conditional | 0.8912 | 0.03420 | 0.12148 |
| Exact discrete marginal | 1.53e-15 | 7.80e-32 | 1.07e-17 |

The maximum pointwise collapsed-versus-dense likelihood difference is 3.20e-14.
Thus the residual single-symbol error here arises after correct channel
integration. The conditional method also changes the nuisance distribution by
conditioning; these errors are **not an additive decomposition** of a real
receiver's error. Profile versus exact isolates the determinant for the same
discrete summation; mean-H introduces a point estimate and therefore a different
approximation. No geometry estimator or geometry mixture was run: geometry is
fixed in each comparison, and wrong-support/geometry-integral error is not
identified by these data. It must remain a separate JET/geometry investigation.

## Continuous Gaussian tilted object

For a real augmented variable `z=[Re x, Im x]`, the routine
`gaussian_tilted_real(log_likelihood, mean, covariance, order)` integrates

```text
Z(r,V) = integral p(y|z) N(z;r,V) dz
m_tilt = r + V grad_r log Z.
```

It uses Gauss-Hermite quadrature on the covariance support, retaining unequal
real/imaginary variances and correlations. There are no discrete constellation
nodes. The recorded arrays include continuous nodes, quadrature weights,
likelihoods, normalized tilted probabilities and moments. Every positive
eigenvalue remains; deterministic directions get exactly one fixed value.
Quadrature orders exceeding the explicit point cap are rejected before work.

Four nonlinear physical cases use one uncertain complex coordinate and one
deterministic coordinate, with improper Gaussian covariance. Orders 9, 17, 25
are frozen before calculation. Changes from order 17 to 25 are at most:

- log evidence: 8.66e-9;
- mean norm: 9.66e-9;
- covariance norm: 1.32e-8.

The maximum discrepancy between `(m_tilt-r)` transformed by `V^-1` and a
central finite difference of log evidence is 1.02e-9. These are numerical
refinement estimates and cross-checks, **not rigorous error bounds**. A separate
four-dimensional correlated real Gaussian affine case checks the known-channel
limit against analytic moments, to 2.08e-16. That latter case validates the
multi-coordinate integration convention; it is not an uncertain-gain full-frame
nonlinear integration experiment. The test suite also verifies the exactly
deterministic-data limit.

The general covariance API permits full real augmentation, but tensor-product
quadrature costs `order^rank` and is only a tiny reference. It is not an admitted
N=1024 algorithm. A local learned integral would still need a documented cavity,
boundary conditions, approximation error, and complete message/runtime evidence.

## Extrinsic and site legality

`bit_extrinsic` constructs

```text
log joint(d) = log likelihood(d) + log base_prior(d)
               + sum_j (1-2 bit_j(d)) L_in,j / 2
L_out,j = logsumexp_{bit_j=0}(log joint)
          - logsumexp_{bit_j=1}(log joint) - L_in,j.
```

Holding all other factors fixed while varying only `L_in,j` leaves `L_out,j`
unchanged, even with a correlated base prior. Maximum observed difference in
the registered discrete cases is 1.23e-15. This cancellation does not justify
feeding observation-dependent beliefs back as independent new evidence.

For real Gaussian moment matching, `gaussian_site` returns

```text
Lambda_site = V_tilt^-1 - V_cavity^-1
eta_site = V_tilt^-1 m_tilt - V_cavity^-1 r.
```

Recombination recovers the tilted moments to roundoff (maximum mean discrepancy
3.93e-17 in the nonlinear cases). The function retains a signed natural factor.
A negative site precision is not silently clipped: the site need not be a
normalizable density on its own. Every subsequent combined cavity precision
must be positive definite; otherwise the proposed update is rejected. Singular
cavity/tilted densities are not accepted by this full-dimensional site helper;
a future support-coordinate EP implementation must declare that interface.

A focused executable counterexample uses the bounded bimodal likelihood
`exp(-(z-3)^2)+exp(-(z+3)^2)` with a `N(0,1)` cavity. Its tilted distribution is
the equal mixture of `N(-2,1/3)` and `N(2,1/3)`, so variance is `13/3` and site
precision is `3/13-1 < 0`. Order-65 continuous quadrature matches that variance.
Combining with the original cavity is valid; combining with a precision-0.1
cavity is rejected by Cholesky. No positivity repair is used to make this pass.

## Evidence, revision and remaining work

The immutable evidence is
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/message_v1/`:
registration/source and thread binding, 16 discrete NPZ cases, 12 nonlinear
quadrature NPZ files, correlated known-channel reference, complete raw/results,
and attempt cost. The stage used 1.0843 CPU seconds / 1.0977 wall seconds. This
is diagnostic cost, not per-frame receiver latency. There were no failed
registered attempts and no mechanism revision. The implementation/test entry is

```sh
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python -m experiments.afdm_structured_inference_20261003.test_collapsed_message
```

All 9 focused tests pass. They include nonfinite/indefinite input failures,
deterministic limits, correlated priors/cavities, score derivatives and an
actually integrated negative-site counterexample.

The falsifiable claim “exact pointwise channel integration alone supplies
exact single-symbol marginal LLRs” is contradicted by these cases. The lawful
continuous tilted target and bit/site exclusion identities are supported in
their tested domains. The next useful object is a data integral or a legal
approximation to it, not more unqualified coordinate sweeps. Cavity quality,
full-frame correlated nonlinear integration, geometry uncertainty, and production
performance/cost remain untested. The current scalar joint receiver was not
run and is not described here as universally overconfident or missing all gain
uncertainty. These examples do not exhaust the potential of collapsed inference.
