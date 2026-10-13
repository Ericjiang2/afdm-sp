# Structured inference mathematical modules

## 1. Scope / trigger

Use these contracts when changing path representation, collapsing Gaussian
gains, or deriving receiver messages from a scalar potential. They complement
`research-diagnostics.md`; mathematical correctness is not production utility.
Reference implementation: `experiments/afdm_structured_inference_20261003/`.

## 2. Signatures

- `CollapsedModel(channel, gain_mean, gain_cov, noise_variance).evaluate(y,x)`:
  y and x in DAFT coordinates; returns log likelihood, conditional gain moments
  and the Wirtinger derivative with respect to x conjugate.
- `gaussian_tilted_real(log_likelihood,mean,covariance,order,max_points=65536)`:
  real-augmented continuous Gaussian integration, with deterministic directions
  retained on the covariance support.
- `gaussian_site(...)`: signed natural-parameter subtraction; a site alone need
  not be a normalizable Gaussian. Combined precision must remain positive.
- `finite_potential(z,f,log_prior,eta,xi,sigma2)` and `source_jvp(...)`:
  finite legal-state reference with an explicitly observation-independent base.
- `gaussian_pair_pass(model,y,pilot,incoming,block_size=1|2)`: uniform-prior
  local alphabet integral using a Gaussian with the true conditional second
  moment. Reject nonzero incoming and non-iid/nonzero-mean gain priors.

## 3. Contracts

For alpha=T beta representing the same physical operator, require
`T m_beta=m_alpha` and `T C_beta T^H=C_alpha`. Duplicate slots under a new iid
1/P rule do not generally preserve the original prior. Even balanced splitting
can change scalar approximate messages: test the actual algorithm, not only the
exact model. Existing block covariance algorithms must be included in the
novelty/reuse assessment before claiming a new full-covariance mechanism.

Collapsed score uses `sum_pq C[q,p] U_p^H U_q`, including off-diagonal complex
covariance. Its exactness is conditional on x and the Gaussian working prior;
it is not a bit LLR. Profile optimization, fixed-neighbor conditionals, discrete
marginals and continuous Gaussian tilted integrals are distinct objects.

For real coordinates, `d E[z]/d y_R = 2 Cov(z,f)/sigma2`; do not replace the
cross covariance by Cov(z,z), omit base-measure derivatives, or confuse positive
curvature with legal constellation support. Fixed C2 rank-one cross moments do
not imply a rank-one full posterior after mixing unknown orbits.

For independent uniform outside QPSK and zero-mean iid Gaussian gains,
`S=(noise+pd)I-DD^H+AA^H` retains the exact conditional observation covariance.
Its Gaussian likelihood is still an approximation to the true mixture. Use
an SPD downdate followed by an SPD update; validate against dense covariance
and outside-symbol enumeration. Nonuniform outside priors require different
covariance arithmetic. Never silently reuse the uniform formula in decoder
feedback. A one-pass detector can use the original observed geometry front
and decoder without carrying over another algorithm's AMP state.

## 4. Validation and error matrix

| Condition | Required behavior |
|---|---|
| PSD prior with null directions | Integrate on declared support; no arbitrary jitter |
| Indefinite/nonfinite prior or nonpositive noise | Explicit failure |
| Quadrature points exceed registered cap | Reject before evaluation |
| Negative site precision | Preserve signed factor; validate combined precision |
| Own incoming bit factor varies, others fixed | Extrinsic output must stay unchanged |
| Learned mean implies probability outside [0,1] | Report invalidity; never silently clip or score only survivors |
| Tiny checks or kernel quote only | No N1024 FER/full-latency claim |
| Same iterations but changed representation | Count transforms/solve order and actual complete cost |
| Frozen registration references source bytes | Preserve those sources; revisions use new named files |

## 5. Good/base/bad cases

Good: independent dense CPP covariance and multistep directional derivatives
verify an efficient collapsed contraction. Base: correct local quadrature with
refinement error is labeled numerical reference. Bad: use a one-symbol slice
as a marginal LLR or a truth-provided collision center as a deployable estimator.

## 6. Required checks

Use the focused `test_prior_orbit`, `test_collapsed_message`, and
`test_jet_potential` modules. Assertions include transported predictive/LLR
equivalence; unchanged bits after replacing an exact joint by its exact marginal
product; CPP adjoints and derivative indices; a genuinely integrated negative
site; fixed-center jet remainder and degrees of freedom; mixed source JVP and
observation-dependent-base counterexample. Numerical experiments freeze source,
configuration, exogenous streams and effective thread binding before work.

## 7. Wrong versus correct

Wrong: “The cross-moment fix improved prediction, therefore FER must improve.”
Correct: exact marginal products can preserve all bit probabilities while
destroying predictive cross information; test legal messages and full-chain
utility separately. Equal iteration/FFT counts also do not establish equal
arithmetic or wall budgets.

## Actual normalized gain priors

The frozen production generator first applies a latent exponential PDP and
then normalizes the truncated G0 matrix in Frobenius norm; G1 reuses those
physical gains. Conditional on the realized PDP D and geometry, its gain law
is `D^(1/2)s / sqrt(s^H D^(1/2) R_G0 D^(1/2)s)`, with isotropic complex-sphere
s and `R_G0=W^H W` in the legal orthogonal integer-atom convention. A unit
sphere or iid Gaussian prior is a separate working model. Preserve the
weight-normalize/clip/prune order and check the Gram against actual dense G0.
Recovering omitted PDP from an original saved RNG stream is an offline oracle
diagnostic, not a new observation or a deployable prior estimate. Distinguish
conditional-on-PDP moments from the unconditional production law and from
decoding causality. Reference: `experiments/afdm_shared_channel_20261004/PRODUCTION_PRIOR.md`.
