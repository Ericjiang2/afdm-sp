# Observed-only method interfaces and implementation contract

`evaluate_methods(y, config)` accepts only an R-by-4 finite complex observation
array (R>=8) and public settings. It returns a JSON-compatible dictionary with
`statistics`, `r_hat`, `fits`, `diagnostics`, `failures`, `observations` and
`costs`. There is no input for true separation, nuisance, PDP, gains or labels.
The frozen main runner supplies `METHOD_CONFIG.json["method_config"]`.

A minimal call is `evaluate_methods(y, {})`; the complete default configuration
is `methods.DEFAULT_CONFIG`. The main study uses three mu starts (.24,.31,.40)
and one signal-fraction start (.5). Default fractions (.35,.65) are only API
defaults and do not override an explicitly supplied main-study configuration.
The public bounds are mu=[.22,.42], log_tau=[log(.3),log(2)], and
log_sigma2=[log(.08),log(2)]. Solver options are L-BFGS-B with analytic Jacobian,
maxiter=80, maxls=30, ftol=1e-10 and gtol=1e-6. A selected optimizer result is
successful only if SciPy reports success and the bound-projected objective
gradient is <=1e-3. Bound proximity tolerance is 1e-7; matrix relative cutoff is
1e-10; final PDP branch distance tolerance is 1e-9. All are public config fields.
No tuning depends on evaluation outcomes.

## Null family and exact finite arithmetic

`NullFamily` builds the actual frozen G0 zero-separation response with the finite
Dirichlet Fourier sum and its analytic derivative, including the full original
pre-pruning normalization. Throughout the declared public mu interval the
retained physical atoms are -1,0,1. Five deterministic physical parity checks
run on construction; tests additionally compare scores and moments with the
frozen collision teacher. The normalized common path vector u0 determines
m0=sqrt(4 tau) u0 .* QPSK_time. All 64 QPSK phase-orbit representatives are
summed; I0/I1 analytically eliminate the uniform continuous gain phase.

The null density does not depend on the latent PDP. Continuous null optimization
therefore passes through discrete PDP thresholds without clipping or rejection.
The final r=q log(1/q) tangent is a separate request: its actual conditioned PDP
factor and distance to the nearest PDP threshold are computed only at the fitted
point. Exact or tolerance-near threshold points yield `TangentUnavailable`.
No fixed 1e-4 numerical stencil is imposed on otherwise legal optimization
candidates; all derivatives are analytic. Physical support violations outside
the qualified public chart fail explicitly.

Cached values are only fixed QPSK orbit/polynomial constants, a single exact
floating-mu geometry, and exact discrete-PDP-branch factors. There is no parameter
rounding, interpolated coefficient grid or truth-conditioned cache. The first
construction cost is recorded. All polynomial expressions permit zero time
symbol coordinates without dividing by them.

## Continuous nuisance fitting

`fit_null_mle(y, config, family)` minimizes negative mean exact null log density.
The fixed Cartesian product of mu starts and signal-fraction starts is used.
Observed mean energy initializes signal/noise scales; feasible initialization
projection onto the public box is explicitly recorded for each start. This is
not post-fit clipping. Every start retains final objective, theta, gradient,
projected gradient, status/message, iterations, nfev, bounds and convergence.
The minimum objective across all starts is selected, including failed starts;
a lower failed result is never hidden by substituting a successful worse one.
Finite multi-start search is not a global-MLE certificate.

`fit_null_m14` uses its own observations, without any MLE estimate. It first fits
14 moment means with the empirical diagonal feature variance as fixed weights.
Zero/nonfinite variance fails; no variance floor is inserted. At the successful
first fit, it constructs the exact finite-QPSK/Gaussian covariance V, freezes
its declared PSD inverse, and fits again from that first estimate. Failure of
the first step stops the second step and is preserved. The optimizer's hot path
uses closed degree-one/two moment means and analytic derivatives, independent
of R after the observed moments are built. Degree-four covariance arithmetic
runs only at the first fit and final evaluation. Covariance eigenvalues/rank
are recorded; no jitter is added.

The conditional moment formulas use E|x_i|^4=7/4 and
E|x_i|^2|x_j|^2=3/4 (i!=j), with the full finite QPSK sums retained as cached
constants. Derivatives/covariances are checked against the older general
polynomial teacher, including all r and nuisance derivatives.

## Statistics and local estimates

- `full_score`: at the independently fitted null MLE, construct all four exact
  score columns. Fit the target score to nuisance columns using their same-group
  OPG Gram. If e denotes the resulting residual, T=sum(e)/sqrt(sum(e^2)). The
  denominator is an empirical OPG residual, not exact efficient Fisher.
- `full_raw`: same MLE and target score, divided by the raw OPG normalizer.
  For an exact interior MLE, sum(s_eta)=0, so the raw/adjusted numerators agree.
  This is chiefly a nuisance variance-adjustment diagnostic; boundary and
  nonstationary fits need not have equal numerators. The main configuration
  may keep this as a diagnostic rather than a primary comparison arm.
- `moment_score`: at its own GMM fit, recompute V and the 14-by-4 derivative
  matrix D. Let beta=G_eta_eta^+ G_eta_r with G=D^T V^+ D, and
  a=V^+(D_r-D_eta beta). T=sqrt(R) a^T(observed_mean-model_mean)/sqrt(a^T V a).
- `moment_raw`: use a_raw=V^+D_r and its raw variance at the same GMM fit.
  GMM first-order conditions can make the two numerators nearly equal. The
  second-step frozen fitting weight and final V may differ at finite R; this
  distinction is retained. Separate calibration can also absorb a constant
  normalization change. This arm does not prove an independent information gain.
- `moment_j`: classical overidentification statistic
  R (observed_mean-model_mean)^T V^+ (observed_mean-model_mean), using the same
  GMM nuisance fit. It remains defined at a valid null point whose collision
  tangent is unavailable; it does not use r derivatives.
- `second_moment`: fit the two variance combinations for coordinate pairs (0,1)
  and (2,3). Studentize their within-pair power differences with the observed
  two-dimensional centered covariance and use R mean(d)^T Cov(d)^+ mean(d).
  It does not pretend to identify three nuisance parameters. In this frozen
  finite-separation domain, the actual conjugate row symmetry makes both mean
  contrasts zero even under alternatives, including changed PDP branches;
  finite-sample performance is still measured. The stronger classical J arm
  therefore matters when judging the candidate's advantage.

`r_hat` is returned only for full_score and moment_score, with signed and
one-sided-max-zero values explicitly separated. It is the local one-step
mean-score divided by its information/derivative quantity. No automatic delta
conversion, global feasibility claim or consistency claim at arbitrary
separation is made; every result has `local_only: true`. Each estimate also
records the fitted PDP-cell distance d as `fitted_delta_branch_radius`, its
monotone local-coordinate image `r_branch_max=d^2 log(1/d^2)`, and
`outside_fitted_local_branch`. Because the cell is open, equality at this bound
is flagged as well. Signed negative estimates are retained and marked by
`unconstrained_below_zero`; their one-sided values remain zero. These fields do
not truncate an estimate or change any statistic. The bound is only a diagnostic
at the fitted null point: being inside it neither estimates the true delta nor
certifies a finite-separation approximation error or asymptotic accuracy.

## Failure, boundaries and replay evidence

Optimizer failure preserves all starts, returns null affected statistics and
adds an explicit failure entry. A final tangent rejection leaves a successful
null fit intact, returns null tangent statistics and preserves J where valid.
The runner must predeclare how failures enter calibration/evaluation denominators
and ranks; it cannot drop them. Boundary fits are retained with flags and do not
automatically inherit interior asymptotic guarantees. Invalid observations,
configuration, nonfinite optimization values, indefinite covariance or
nonpositive normalizers raise explicit exceptions; no silent alternate model
or successful zero-statistic fallback is used.

Sufficient saved replay quantities include full-score vector sums/Gram,
projection coefficient, raw/adjusted numerator and denominator; moment residual,
model mean, V, D, witness, raw witness, nuisance coefficient, numerator and
normalizer; C2 pair variances, contrasts' means/covariance; and both fitted
parameter vectors with every optimizer start outcome. These allow independent
statistic reconstruction without refitting or generating new observations.

## Cost accounting

`costs.per_method_seconds` contains full_score, full_raw, moment_score,
moment_raw, moment_j and second_moment. Each includes its own continuous fit
and statistic construction; full/raw share one actual MLE, and moment/raw/J
share one actual GMM. J's independent cost stops before the collision tangent
work, so the simple baseline is not charged for unused score construction.
Shared setup is separate (`setup_seconds`, `setup_cache_hit`, and the original
construction cost). The `*_complete_seconds` convenience fields add the actual
setup incurred on that call. Final JSON-list conversion is separately timed;
`joint_complete_seconds` includes the whole call through that conversion.
Methods' standalone-path times must not be summed as actual joint runtime.
The caller separately records durable serialization and complete registered
stage cost. A cost advantage must include setup/calibration amortization and
all relevant fitting work; cached pure-kernel time is not deployment latency.

## Deterministic verification

The test suite uses fixed trigonometric observations, not random scientific
samples. It checks old likelihood/score and all moment/derivative parity,
analytic Jacobians across a null PDP threshold, explicit final tangent rejection,
actual continuous optimizer behavior, independent MLE/GMM estimates, forced
maxiter failure preservation, saved-statistic replay, no-truth signature,
no-jitter/invalid-input rejection, and C2 finite-separation covariance symmetry
using exact P2 covariance identities without observations or quadrature.
