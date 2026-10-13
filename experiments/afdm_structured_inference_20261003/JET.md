# Collision jet validity and comparison boundary

JET-01 verifies local moment coordinates and their exact CPP-aware derivatives.
The first/second-order jets reduce representation error at small offsets, while
fixed-center error and nonlocal separations can dominate. This is an operator
diagnostic, not a completed F1 optimization or an identified receiver improvement.
This document is the task's `jet_validity` report.

Evidence: [registration](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/jet_v1/registration.json),
[summary](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/jet_v1/results.json),
[126 raw curve records](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/jet_v1/curves.json),
[four contract tests](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/jet_v1/tests.json).
Every case has an NPZ containing the actual physical matrix, source vector,
gain/offset truth for scoring, basis derivatives, moments, pushed-forward prior,
and every estimate/coefficient. There are no omitted unsuccessful cases.

## Coordinates, physical response, and prior

For two paths at the same integer delay, write `nu_j=nu0+delta_j` and
`M_k=sum_j h_j delta_j^k`. The registered approximation is

`sum_j h_j U(nu_j) = sum_{k=0}^r M_k U^(k)(nu0)/k! + remainder`.

`operator_derivatives` uses the frozen CPP channel, transforms to its time
response, multiplies by `(2 pi i t/N)^k`, and transforms back. The first two
derivatives pass independent finite differences at a nontrivial CPP boundary.
The unknown data remain inside `U(pilot+d)`; this geometric Taylor expansion is
not an affine replacement of the gain/data product.

For fixed offsets, `M=T(delta)h`, `T_kj=delta_j^k`. Under the same
`h~CN(0,0.5 I_2)` prior, `Cov(M)=0.5 T T^H`. At most two complex moment directions
are available; at exact collision this drops to one. In particular,

`M2-(delta1+delta2) M1+delta1 delta2 M0=0`.

An independent isotropic prior on the jet coefficients changes the model and is
not the original gain prior expressed in new coordinates. When offsets are
unknown, the pushed-forward prior is a mixture over their stated prior, not the
conditional covariance above. `M1/M0` is generally complex and is undefined at
exact cancellation; it is not a general real Doppler estimate. The complex-gain
test verifies this explicitly.

For each order the recorded scaled Frobenius remainder obeys the deterministic
bound

`sum_j |h_j| [2 pi (N-1)|delta_j|/N]^(r+1)/(r+1)! / sum_j |h_j|`.

The bound uses the real-argument exponential Taylor integral remainder and
unitary chirp/shift factors, including CPP phases. Every registered case passes.

## Fair comparison and information supplied

All 126 cases use `N=16`, seven separations from 0 to 1.2, same-phase,
cancelling and general-complex gains, and both declared center modes. The
development center is fixed at 0.25. Held-out centers are -1.35 and 2.6 with
fixed midpoint errors +0.11 and -0.09, respectively. The latter uses delay 15 and
noninteger stride 5.3 to exercise nontrivial CPP phases. Orders 1 and 2 were fixed
before every run; there is no truth-based per-case order selection.

The `exogenous_grid` center is supplied independently of path truth. It is an
available fixed reference, not evidence of a good observed-data center estimator.
The separate `oracle_midpoint` branch explicitly uses the generating midpoint.
Known path delay and same-delay group membership are supplied in this diagnostic,
and remain additional information a deployable grouping method would need.

The F1 reference contains the exact two columns at the generating Dopplers.
Its least-squares projection onto the true target matrix is an **oracle-column
representation reference**. No F1 optimizer, pilot-only estimator, or production
receiver was run. Native and jet least-squares projections also read the target
matrix and are explicitly named `oracle_projection`. The pushed-forward
reconstructions measure truncation with known diagnostic coefficients, not
coefficient-estimation performance.

| Representation | Real parameters at fixed center/geometry | With unknown Dopplers |
|---|---:|---:|
| Native single response | 2 | 3 |
| F1 two response columns | 4 | 6 |
| Order-1 free jet | 4 | center held fixed |
| Order-2 free jet | 6 | center held fixed |

The last row is overcomplete relative to two gains at fixed offsets; the exact
pushforward prior imposes the recurrence above. Column count, algebraic free
parameters, local Jacobian rank and prior support rank are recorded separately.

## Results and scope

Errors below are the largest across the three gain settings, normalized by
`sqrt(N)*sum_j |h_j|`. This scale stays defined for exact cancellation; a zero
target does not yield a misleading zero-denominator relative error.

| Development separation | Native | Order 1 | Order 2 |
|---|---:|---:|---:|
| 0.0001 | 1.729e-4 | 2.035e-8 | 1.741e-12 |
| 0.01 | 0.01728 | 2.035e-4 | 1.741e-6 |
| 0.05 | 0.08623 | 0.005081 | 2.175e-4 |
| 0.2 | 0.3331 | 0.07967 | 0.01373 |
| 0.6 | 0.8862 | 0.6036 | 0.3308 |
| 1.2 | 1.3479 | 1.8150 | 2.3919 |

At separation zero with held-out fixed-center error, order-1 error is 0.09762
and 0.06554, while order-2 error is 0.01842 and 0.01011. Thus path collision alone
does not guarantee a small jet error: absolute offsets from the chosen expansion
center matter. The exact F1 two-column projection reconstructs all cases within
`1e-12` of the scaled norm, as its information advantage predicts.

In the development general-complex case at separation `1e-4`, the unknown-
geometry F1 real Jacobian has rank 6 and nonzero condition number `6.51e8`.
At separation zero its rank is 4, and the fixed-geometry two-column map has rank
2. The order-1 and order-2 fixed-center maps have ranks 4 and 6 and condition
numbers 7.01 and 29.18. These are raw natural-coordinate singular spectra;
conditioning is coordinate-scale dependent and is not, by itself, an estimation
gain. The moments' singular prior and discarded inverse-map information prevent
interpreting these numbers as equal-information posterior improvement.

At exact collision the general-complex F1 minimum-norm slot estimate has relative
gain-coordinate error 0.527, while the aggregate moment error is `2.22e-16`.
Separated gains are not identifiable there; a zero aggregate error does not
recover the original slots. Both coordinate errors are retained for all cases.

The registered stage used 0.230 CPU seconds / 0.238 wall seconds, including tests
and raw output, under the one-thread 90 CPU/120 wall cap. Per-case measured work
includes diagnostics and serialization; these potentially overlapping shared-
machine microtimes are not isolated receiver latency. A matrix-free order-r jet
requires `r+1` transformed response columns, nominally `O((r+1)N log N)` actions,
versus two exact F1 columns. Order 2 adds a column; preprocessing, grouping,
center estimation, regularization and complete receiver cost are unmeasured.
Dense matrices here are only `16 x 16` diagnostic representations.

## Feedback and remaining decision

Supported: local moment coordinates preserve the physical Taylor structure,
separate identifiable aggregates from colliding slots, and admit explicit
pushforward priors and controlled local remainder bounds.

Contradicted: a fixed low-order jet is uniformly accurate from coincidence to
nonlocal separation, or that collision alone makes it accurate regardless of
center error. Adding order at separation 1.2 makes this registered truncation
worse, so no automatic higher-order sweep was launched.

Unresolved: an observed-data grouping/center rule, offset prior, and constrained
inference over the moment image that beat the actual F1 optimizer at matched
complete cost. Current evidence supports a restricted local representation
claim, not a deployable FER claim and not a rejection of the entire jet family.
The holdout diagnostics expose center selection as the next causal question;
they do not authorize choosing centers from truth or changing frame resources.
