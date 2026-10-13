# Prior qualification and execution handoff

No registered study has been run by the implementer at this handoff. The main
session must freeze source bytes before admission and serialize each stage.

Qualification command (all five numerical thread variables set to 1 and
CUDA_VISIBLE_DEVICES empty):

`/tmp/afdm-shared-channel-env/bin/python -m unittest experiments.afdm_efficient_information.test_prior_likelihood -v`

All **15 tests passed** across `test_prior_likelihood` and `test_prior_study`. Independent checks cover dense G0 Gram and the full
DAFT/time operator, exact two-increment PDP summation, ACG normalization and
label permutation, explicit global-phase integration, all four likelihood
finite differences, simultaneous D/R/B JVP, exact platform zero, G1 singular
refusal, singular nuisance projection, continuous sampler independence from
quadrature, analytic actual covariance, and the collision logarithmic slope.
Three additional evidence-gate regressions verify discrete-branch reporting,
refusal to replace a changed registered tail point, and failure/missing-step
propagation into information convergence. `py_compile` also passed. These small fixtures are qualification, not research
samples or convergence evidence.

One qualification failure was retained in the development account: the initial
hand-written DAFT used negative chirps. Unitarity and dense Gram tests passed
because neither fixes phase convention. The added independent full-operator
check `A^H H_daft A == diag(B[:,0])` failed at N4 with maximum error .07739522.
Frozen `afdm_env.build_lambda_matrix` and `physical.daft` both use positive
chirps; the local duplicate was removed and `daft(n)` now directly reuses the
frozen function. The operator check and all 12 tests then passed. No registered
observation was generated with the erroneous implementation.

## Frozen planned stages

- `prior_study --mode geometry --stage prior_geometry_v1`: 0 new observations,
  120-second reservation, 108 dense geometry cases (N4/8/16, six centers and six
  separations), analytic threshold sides and six collision/PDP covariance
  sequences. Each sequence point saves its discrete branch and collision-branch
  equality; the fixed last-three fit is explicitly unqualified if any differs.
  Every case is kept; clip/prune, platform and G1 moments are tagged.
- `prior_study --mode information --stage prior_information_v1`: 1536 new
  independent observations, 900-second reservation. Six declared cases with
  256 observations each; first/last 128 independently fit/validate nuisance
  projection. Positive product 12×24 and 24×48 rules plus independent scrambled
  Sobol 64×128 rule; three derivative steps and eight direct finite-difference
  observations per case. Every registered derivative comparison and direct FD
  enters the saved refinement decision. Raw Y, theta, all score arrays and
  estimates are saved.
  Counts, seeds, rules and all tolerances live in `prior_study.py` configurations.

The six cases are G0 equal PDP, G0 conditional unequal PDP, G0 actual marginal,
G1 actual marginal, near-collision G0 actual marginal, and exact-platform G0
actual marginal. Nuisance coordinates are mu,log(tau),log(sigma²); separation is
delta. Information in q is the interior chain rule only. Positive finite-rule
numbers are not an exact Fisher certificate. Unconverged cases remain explicit.

## API and cost meanings

`ActualPrior(n=4,model='g0',pdp='marginal',order=12,phases=24)` exposes
`sample(theta,count,seed)`, `logpdf(Y,theta)`, `evaluate(Y,theta,step)['score']`,
and `branch(theta)`. Theta is `[delta,mu,log_tau,log_sigma2]`.
`pdp='equal'` or a positive two-power vector selects a conditional oracle.
N>6 may sample and diagnose geometry but full QPSK likelihood is refused.

`cost.response_evaluations` counts newly constructed CP1×QPSK-orbit mean
vectors; `logpdf_observations` counts all input rows evaluated including repeats;
`component_observation_pairs` counts mean/observation pairs inside density
integration; `tracked_branch_eigvalsh` counts that one explicitly instrumented
outer branch decomposition. It is **not** all internal eigendecompositions.
The frozen helper's validation eigvalsh/eigh and exact sampler cost are not
pretended to be covered by this partial counter. Full-stage wall/CPU/RSS include
sampling, construction, all stencil calls, fitting and output through protocol.
Mean arrays are cached per candidate/step within an instance. Every independent
rule constructs its own components; its numerical cost is retained.

Required sources include this package's prior modules/tests, `PRIOR_THEORY.md`,
this file, old `prior.py`, `production_prior.py`, frozen `physical.py`, and the
existing `production_diagnostic.source_paths()` list of protected source/data
hash bindings. Imports are preloaded before effective-thread inventory freezes.
