# Exact conditional gain elimination

COLLAPSE-01 is supported **within the stated independent Gaussian gain working
model at fixed geometry and fixed data**. This result establishes an exact
likelihood/score kernel; it establishes neither a full data marginal nor a
production receiver advantage.

## Contract and implementation

The public interface is `CollapsedModel(channel, gain_mean, gain_cov,
noise_variance).evaluate(y, x)`, where `x=pilot+data` and both `x` and `y` are in
the DAFT domain. It returns normalized log likelihood, conditional gain mean
and covariance, and the Wirtinger score `d log p(y|x) / dx*`.

Write the possibly singular covariance as `C0=L L^H` on its actual support,
`h=m0+L z`, and `z~CN(0,I)`. With `B=[U1 x,...,UP x]`, `T=B L`,
`r=y-B m0`, and `Q=I+T^H T/sigma2`,

```text
z_hat = Q^-1 T^H r / sigma2
m = m0 + L z_hat
C = L Q^-1 L^H
log p(y|x) = -N log(pi sigma2) - logdet Q
             - ||y-B m||^2/sigma2 - ||z_hat||^2
g = [H(m)^H (y-H(m)x) - sum_pq C[q,p] U_p^H U_q x] / sigma2.
```

The residual-plus-prior expression avoids subtraction of two large Woodbury
quadratic forms. No covariance jitter or positive-eigenvalue truncation is used.
The existing exact oracle's PSD support factor routine reports floating point
roundoff correction and rejects negative/non-Hermitian priors. A zero covariance
is a deterministic channel, with zero conditional covariance and the ordinary
known-channel likelihood. Gain priors must be independent of the observation.

The score follows Fisher's identity: conditional moments are substituted once;
their derivatives are **not** differentiated again. For
`C[p,q]=E[(h_p-m_p)(h_q-m_q)*]`, the required contraction is `C[q,p]`.
The complex correlated-prior checks explicitly expose an accidental transpose.

The implementation imports the frozen `physical.daft`, `physical.Channel`, and
`TimePathOps`. It performs both observation/data IDAFTs, builds time-domain path
responses, performs the support solve, and applies one DAFT for the score.
`B @ C` followed by each path adjoint implements all cross terms. Time complexity
is `O(N log N + N P^2 + P^3)`; working storage is `O(NP+P^2)`. Geometry/phase and
prior-factor preparation are included in the quoted call. `B`, its Gram, and
its matched observation **depend on x**, so they are not one-time sufficient
statistics for an unknown whole data word.

## Fresh local evidence

Reproduce with the registered Python environment:

```sh
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python experiments/afdm_structured_inference_20261003/collapsed.py
```

The completed `collapse_v1` directory is immutable and this command refuses to
overwrite it. A deliberately authorized new attempt needs a new version.
Registration, per-case NPZ arrays, all-case raw JSON, result JSON, source hashes,
effective thread binding, caps, and actual CPU/wall cost live at
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/collapse_v1/`.

There are 128 paired mathematical cases from **4 independent exogenous draws**,
not 128 independent channels: `N=7`, four geometries, four priors, and two noise
variances. Geometries cover distinct paths, exact repetition, near repetition,
and the maximum legal delay/CPP wrap boundary. Priors cover zero mean, nonzero
mean with complex correlations, rank-one singular support, and known channel.
Noise variances are 0.02 and 2. The nonstandard chirp `c1=.37/N` intentionally
keeps CPP wrap phases nontrivial; this is a physical-operator stress case, not the
production chirp/frame distribution.

The independent reference builds a finite DFT matrix and explicit CPP time
matrices, forms the observation covariance, and solves in observation space.
It does not reuse the time-path response contraction. Relative errors use
`||actual-reference|| / max(1,||reference||)`.

| Quantity | Maximum error |
|---|---:|
| Normalized log likelihood | 3.05e-14 |
| Conditional gain mean | 5.46e-14 |
| Conditional gain covariance | 3.70e-14 |
| Complex score | 1.72e-13 |
| Best of three registered central-difference step errors, worst case | 5.33e-10 |
| P=1 constant-modulus/no-pilot logdet range | 4.45e-16 |

All three finite-difference values (steps 1e-3, 1e-4, 1e-5) are retained for each
case; the table's best-step statistic is not a claim that every step has the
same truncation error. Physical forward and adjoint checks also pass 1e-10.
For one unitary path and no pilot, equal-modulus data have constant total energy,
so the log determinant cannot contribute to data ranking. This special limit
does not remove the determinant in general.

The complete 128-case stage used 0.1420 CPU seconds / 0.1454 wall seconds.
The shared-machine arithmetic quote, 20 complete kernel constructions/calls per
configuration with one effective thread, gave:

| N / P | Mean | p95 |
|---|---:|---:|
| 8 / 2 | 0.1494 ms | 0.1590 ms |
| 1024 / 8 | 0.6266 ms | 0.6605 ms |

These calls include channel/phase setup, prior factorization, all three
transforms, response/Gram construction, solve, covariance, and full score.
They exclude input generation/import, data integration, receiver iterations,
LDPC, and durable storage. They are shared-machine arithmetic quotes, **not
isolated complete-receiver latency or a matched baseline speedup**. Peak RSS was
not isolated; asymptotic workspace does not substitute for that measurement.

## Falsification and next dependency

Prediction: at fixed data the collapsed kernel must match independent dense
integration and directional derivatives, including support singularities.
Observation: it does within numerical tolerance; no mechanism revision was
needed. The mathematical claim is supported in its specified working model.
The normalized physical gain generator need not have this Gaussian prior, and
its mismatch has not been removed by this identity.

`MESSAGE.md` tests the separate proposition that pointwise exactness is enough
for soft data messages. It is not. Production geometry selection, complete
message closure, convergence, FER, and complete performance/cost curves remain
untested here. The existing scalar joint receiver already includes gain
uncertainty and product variance; this work does not characterize it as having
universally omitted those terms.

The shared focused suite `test_collapsed_message.py` has 9 passing tests,
including correlated score indices, two directional axes, deterministic and
singular support, invalid covariance/noise rejection, correlated bit priors,
Gaussian analytic moments, signed sites, and deterministic data limits.
