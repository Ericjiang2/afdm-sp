# Near-collision refinement: fixed spectral coordinates

## Target and status

Refine only the unresolved `near_collision_g0_actual_marginal` likelihood at
`theta=(delta=.035,mu=.35,log_tau=0,log_sigma²=log(.8))`. Reuse the exact 256
observations from `prior_information_v1`; no new observation, receiver call,
decoder call or independent statistical replication is generated. The original
failed convergence remains in v1. Status: implementation qualified; numerical
research awaits committed-source admission and main-session scheduling.

The invariant object remains the observed actual-PDP-marginal G0 law from
`PRIOR_THEORY.md`. Equal PDP, Gaussian gains, a different target point or a
changed conditioning event are not substituted. Existing v1 modules and raw
files are read-only. Implementation is `prior_refinement.py`; all new inputs,
nodes, tolerances and seeds are frozen in its CONFIG before research execution.

## Why the coordinate change addresses the diagnosed error

In the original CP1 chart, the nearly null gain combination lies at an interior
relative phase and power split. For small Gram eigenvalue this creates a narrow
region where `v/sqrt(v^H R v)` changes quickly. The v1 direct derivative checks
passed but two independent node comparisons failed: this is an integration
resolution problem, not evidence that a smaller finite-difference step alone
fixes the likelihood.

Let U be the unitary eigenvector matrix of the G0 normalization Gram at the
**fixed public design point** theta_star, ordered from small to large
eigenvalue. A canonical column-phase convention makes saved coordinates
reproducible. Haar measure on the complex sphere, and its CP1 quotient by
uniform global phase, is invariant under U. Thus

`v=U z`, `z=(sqrt(t),sqrt(1-t) exp(i phi))`,

is an exact new chart with uniform t∈[0,1] and phi∈[0,2pi). At theta_star,
`v^H R v=lambda_small t+lambda_large(1-t)`; the difficult region is now close
to t=1, independently of phi. Map

`t=1-(1-s)^4`, `dt/ds=4(1-s)^3 > 0` for s∈(0,1).

A positive Gauss–Legendre×phase or scrambled Sobol rule in (s,phi), multiplied
by this positive Jacobian, still integrates the same Haar base. No eigenvalue
is changed, floored or jittered. The marginal angular density is retained as

`f(v)=sum_j p_j D1_j D2_j/[D2_j |v1|²+D1_j |v2|²]²`.

It must be evaluated **after rotation in the original physical path axes**.
Using only `|z1|²` in that density would change the actual PDP model; the
independent exact-covariance qualification checks this distinction.

## Full theta derivative in a fixed chart

U is selected once from theta_star and remains fixed during every likelihood
and finite-difference evaluation, including shifted theta values. The nodes,
quadrature Jacobian and U therefore have zero theta derivatives by construction.
This does not drop a coordinate derivative: for every nearby theta,

`p_theta(y) = integral p(y | B_theta v/sqrt(v^H R_theta v), tau,sigma²)`
`                    * f_theta(v) * 4(1-s)^3 ds dphi/(2pi)`,

with the same **constant** mapping v=U_star z(s,phi). The identity holds for
any fixed unitary U_star; it does not require U_star to diagonalize R_theta
away from the design point. On the frozen local branch, PDP increment limits
and their exact finite probabilities are unchanged, so f_theta(v)'=0 for
mu/delta; log_tau/log_sigma² also do not change this density. An attempted
stencil across pruning, clipping, rounding or PDP-limit branches is rejected
by the existing source-bound branch check. These are exact reasons for zero
chart/density terms, not a frozen-prior approximation.

The complete derivative remains

`h'=-(1/2)h (v^H R_theta' v)/(v^H R_theta v)`,
`(B_theta h)'=B_theta' h+B_theta h'`,

plus log_tau scaling and the analytic log_sigma² score. This is the existing
full fixed-base JVP; only its observation-independent quadrature nodes change.
All four score columns are independently checked against direct logpdf finite
differences while asserting that nodes and weights are bytewise unchanged.
A moving U(theta) chart would require additional terms and is not implemented.

## Frozen study contract

Input: `results/afdm_efficient_information/prior_information_v1/near_collision_g0_actual_marginal.npz`,
SHA-256 `81557344a52b5933b452c368c9b48736bfa4dcaba18a970d65ae709a57abe4fc`.
All 256 saved Y rows and the physical point must match the registration.
Train/evaluation splitting remains first/last 128 rows; changed nodes do not
make the evaluation rows statistically new.

Positive rules in the fixed chart:

| Rule | s order × phases | Nodes | Direction rule |
|---|---:|---:|---|
| coarse | 16×32 | 512 | Legendre × midpoint periodic phase |
| medium | 32×64 | 2048 | Legendre × midpoint periodic phase |
| fine | 64×128 | 8192 | Legendre × midpoint periodic phase |
| independent | 64×128 | 8192 | scrambled Sobol seed 751; phase shift .137 turns |

Total new integration nodes: 18,944. The four reused base-class initializations
also construct eight unused placeholder nodes each; these 32 are explicitly
recorded as initialization overhead, never counted as used quadrature support.
The independent rule changes both radial samples and relative-phase directions.
All choices are observation-independent and fixed before the run.

All three neighboring/independent comparisons enter the refinement decision.
Tolerances are inherited unchanged from v1: maximum logpdf difference .03,
per-column score relative RMS .05, quadrature mass error .001, every derivative
step and direct-FD relative RMS .001, independent-rule effective-information
relative difference .12. Score relative denominators retain the v1 .01 floor.
Steps remain 1e-4,5e-5,2e-5; direct FD uses eight saved rows. Nuisance projection
uses rcond=1e-10. A numerical positive decision still requires refined
integration and held-out residual information greater than four batch SE.
Failure remains unresolved; thresholds, observations and models are not changed
to obtain a passing classification.

Run command, after source commit and with the five thread variables set to 1:

`/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_efficient_information.prior_refinement --stage prior_refinement_v1`

Reservation: **900 seconds, zero new observations**. No remote/GPU calls.
Integration batch size 4 limits temporary component-observation arrays. Complete
wall/CPU includes node construction, all components/stencils, fitting and
compressed evidence output. Raw components are below roughly 1 GB before
compression for this fixed configuration; the task-wide 2 GB output admission
still applies. Chart eigendecompositions are reported separately from the
frozen kernel's explicitly partial branch counter.

## Saved evidence and independent replay schema

- `observations.npz`: exact reused Y and theta. `scores.npz` also retains the v1
  fine logpdf/score for direct comparison, all four new-rule logpdf/score arrays,
  train/evaluation efficient residuals, all derivative-step scores, and direct
  finite-difference plus/minus logpdf arrays, derivative step and derived score.
- `<rule>_nodes.npz`: exactly used physical-axis `nodes`, base CP1 `weights`
  including Jacobian, `chart_s`, `chart_phi`, `jacobian`, `base_weights`,
  `unitary`, design theta and design Gram eigenvalues.
- `<rule>__base_components.npz`: exactly cached `means`, `logweights`,
  `derivatives` in delta/mu/log_tau order, theta and derivative step. The noise
  derivative is the analytic phase-integrated Gaussian expression. Each JSON
  sidecar records node filename, whether derivative arrays exist, angular mass
  error before normalization, complete discrete branch and cost snapshot.
- `fine__step_1/2_components.npz`: complete arrays for the two refined JVP
  steps. `fine__fd_<axis>_plus/minus_components.npz`: all eight component sets
  actually used for direct FD. A stored derivative_step of zero means that no
  component derivative was requested; the JSON presence flag is authoritative.
- `refinement.json`: all comparisons, individual refinement gates, unchanged
  train/evaluation information estimates, costs, input hash and classification.
  The protocol stores source/config snapshots, final hashes and any failure.

Saving components reads an existing cache entry and performs no extra
likelihood or geometry evaluation. Audit can recompute each logpdf and all
four scores directly from the stored means/logweights/derivatives and Bessel
formula, then recompute FD and nuisance projection, without constructing any
new node or calling `ActualPrior.evaluate`.

## Qualification evidence and remaining limits

Five targeted tests pass: Jacobian/Haar second-moment identity; frozen-node
four-parameter FD; actual covariance against independent analytic integration;
exact cached component persistence plus separate Bessel reintegration; and
independent positive Sobol directions. Fixtures are small qualification checks,
not the registered 256-observation research result.

A successful refinement answers numerical integration at one separated point.
It does not resolve finite evaluation-sample uncertainty, make the two 128-row
splits new independent data, certify positive population efficient Fisher, or
restore regular q behavior at collision. The q log(1/q) obstruction and the G0
platform theorem remain unchanged.
