# ORACLE-01: actual scalar inference versus the exact posterior

## Judgment

The registered small-model evidence **does not support a blanket claim that the
current joint detector is overconfident**. With pilot amplitude 0.6, actual
`scalar_joint(gain_mode='joint')` has mean probability MSE 0.006657 against the
exact posterior and slightly *lower* mean sharpness. The same algorithm's point
mode and a discrete point-gain plug-in are substantially sharper and less
accurate in this grid. Existing gain uncertainty is doing useful work here.

A full covariance/coupling representation gap remains: the joint algorithm's
gain-covariance trace is almost correct on average, yet its directional matrix
error and missing h-d moments are nonzero. This justifies a precise representation
study, not a causal declaration that restoring cross-covariance must fix LLRs.
The exact-marginal-product control proves why that stronger inference is invalid.

## Frozen protocol and common model

Before any comparison run, `comparison_v1/registration.json` froze the grid,
source hashes, methods, initializations and budget. Files live under
`.mission/20261002_22-12-10-afdm-inference-causal-defects/execution/oracle/`.
No method, iteration count, grid, threshold or reporting subgroup was selected
from outcomes; both pilot and geometry strata were declared before execution.

- N=2 or 3, P=2; actual frozen CPP/fractional-Doppler operators.
- Production-form chirp scaling `c1=2.5/N`, `c2=(sqrt(2)-1)/(2N²)`.
- Separated paths: delays [0,1], Dopplers [0.31,-0.27]. Near-duplicate paths:
  delays [0,0], Dopplers [0.31,0.32]. Geometry is supplied and identical to all.
- Independent gain prior `CN(0,I/2)`; independent uniform QPSK data power 0.5;
  noise variances 0.15 or 0.8. Pilot amplitudes 0 or 0.6, phase `exp(0.4 i k)`.
- Seeds 0,1,2 use independent gain/data/noise streams. Exogenous draws are paired
  across geometry, pilot and noise settings: **6 independent (N,seed) clusters**,
  48 fixed observation conditions, 96 initialization records, not 96 independent
  channels. At most 64 QPSK candidates per exact posterior.
- Initializations: observable pilot ridge with the same gain-prior scale, and
  fixed independent `[1,i]/sqrt(2)`. Neither is substituted for the gain prior.
- Actual frozen `twofft.scalar_joint`: 20 iterations, damping 0.3, zero grouped
  data-prior LLR, unchanged default time observation domain. No production
  receiver cascade, geometry search, LDPC, or FER experiment.

The oracle bit mapping was corrected to all-I then all-Q before registration;
the mapping is directly tested against frozen `messages.moments`.

## Four compared objects

1. **scalar_joint**: actual source, joint gain mode; returned means, scalar gain
   variances and diagonal data variances. Missing cross-covariance is represented
   as zero because this factorized output has no such field. Internal Onsager
   terms still exist; zero exported cross-covariance does not mean the algorithm
   ignores every bilinear interaction.
2. **scalar_point**: actual source, `gain_mode='point'`. Same gain-prior shrinkage
   parameter and input, but gain variance is zero. Its altered trajectory is
   recorded, so this is a concrete uncertainty-handling control, not a claim
   that only one final output number changed.
3. **plugin_joint_gain**: exact finite-data likelihood conditional on the final
   gain estimate from scalar_joint. It retains the full discrete data model but
   removes gain uncertainty. This is a plug-in approximation to the common
   generative problem, **not** a new independent known-channel Bayes prior and
   not oracle access to generated h.
4. **oracle_product**: product of the exact h and exact d marginals. LLR, means,
   and marginal covariances are unchanged by construction; h-d conjugate and
   pseudo-cross covariances are set to zero. This isolates what a factorization
   alone can and cannot imply, without constructing an inconsistent receiver.

The grid uses uncoded uniform QPSK because scalar_joint consumes factorized bit
priors. Passing a short-code oracle while silently ignoring its constraints in
the scalar arm would violate common priors. Short-code and nonuniform independent
codebook support remain separately validated in the exact-oracle unit tests.

## Metrics and scoring interpretation

Let p=P(bit=0|y) be exact and q the approximation. Report probability MSE,
LLR RMSE, Bernoulli KL, and the exact conditional expected Brier score:

`Brier(q|y)=p(1-q)²+(1-p)q²`; its excess over oracle is exactly `(q-p)²`.

This measures conditional probabilistic error using the analytic posterior.
It is not an empirical reliability diagram, population calibration proof, or
Monte Carlo bit-error estimate. Sharpness gap is `mean(|q-1/2|-|p-1/2|)`;
positive means more extreme probabilities, not automatically correctly signed
confidence. Signed covariance trace gaps and absolute Frobenius/mean errors
compare the returned posterior representation to the exact one.

## Results

Each row below averages the 24 registered pilot-amplitude-0.6 conditions with
pilot-ridge initialization. No significance claim is made from these six paired
exogenous clusters.

|Method|Probability MSE / excess Brier|LLR RMSE|Sharpness gap|h mean L2 error|h covariance Fro error|
|---|---:|---:|---:|---:|---:|
|scalar_joint|0.006657|0.573462|−0.010200|0.089998|0.166105|
|scalar_point|0.042395|1.763936|+0.125659|0.170103|0.516257|
|plugin_joint_gain|0.037346|2.250217|+0.107729|0.089998|0.516257|
|oracle_product|0|0|0|0|0|

Fixed independent initialization gives nearly the same pilot-present joint
result: probability MSE 0.006686, sharpness gap −0.008784. Thus the pilot-present
aggregate observation is not limited to the ridge initialization.

Joint gain-covariance trace gap is only −0.001506, whereas its Frobenius error is
0.166105. Matching total uncertainty does not match its direction. Exact h-d
conjugate covariance norm averages 0.147075 and pseudo-cross norm 0.283785; all
factorized outputs miss these. The exact-product arm misses the same cross
moments **without any LLR error**, disproving “missing cross moments alone imply
miscalibrated LLRs” as an unconditional argument.

Geometry changes the sign of confidence error. For pilot ridge with pilot 0.6:

|Geometry|Joint probability MSE|Joint sharpness gap|Point-mode probability MSE|
|---|---:|---:|---:|
|Separated|0.002881|+0.012602|0.055036|
|Near-duplicate|0.010433|−0.033001|0.029754|

The near-duplicate grid is harder in exact-marginal approximation error, but its
joint soft output is on average less extreme than exact. Directionality,
multimodality, iteration dynamics and scalar approximation remain distinct
explanations; this grid does not identify one as the unique causal mechanism.

## Multimodality and the no-pilot control

With zero pilot and isotropic zero-mean gain prior, the common QPSK rotation
`(h,d) -> (-i h, i d)` preserves likelihood and prior. Exact marginal bit LLRs
are zero (maximum observed absolute value 1.78e−15), as are h/d means. The joint
posterior is nevertheless informative about products and relations.

At zero pilot the conjugate h-d covariance vanishes by rotational symmetry,
while pseudo-cross norm averages 0.608604. A test restricted to conjugate
cross-covariance would miss this dependence. With zero ridge initialization,
actual scalar output has exact zero bit marginals yet gain-covariance Fro error
0.269829 and data-covariance Fro error 0.416724. Correct bit marginals do not
mean the joint posterior is represented correctly.

With the fixed asymmetric initialization, every zero-pilot scalar_joint record
has nonzero finite-iteration LLR, with mean probability MSE 0.004575; point mode
has MSE 0.128158. This is symmetry breaking/local iteration behavior in a
multimodal posterior, not evidence that a single local Gaussian covariance
correction will restore the entire posterior.

## Evidence, integrity and cost

`results.json` contains all 96 records, every iteration trace, exact/approximate
metrics, subgroup means and source/config hashes. Ninety-six raw NPZ files retain
the shared observations, operators, candidates, exact mixture/component moments,
actual scalar trajectories and outputs. Generated h/d are not passed to inference.

The grid completed **192 actual scalar_joint calls / 3840 iterations** in
1.113583 CPU s and 1.113999 wall s, below the registered 60 CPU s / 120 wall s
caps. No failures or excluded cases. The contract suite separately makes two
small actual scalar calls; do not hide them in a “zero calls” statement.

Actual Accelerate calling-thread mode 1 was checked before/after, with all five
thread variables set to 1. The combined 15-test suite passed in 0.124 s unittest
time (0.167978 process CPU including imports). An initial comparison-test import
failed before its module existed; no simulation ran in that failed test.

Same-author saved-output recount verified all 96 raw SHA256 values, all registered
source hashes, exactly 48 started/finished case pairs, the complete case/init
set, zero exact-product LLR discrepancy and the Brier identity. See
`comparison_v1/recount.json`. This is not an independent scientific audit.

Results SHA256: `fa13584723430c670610e251dc730aaa6f8933c795fb7eff2a0d7bef49397314`.
All current implementation/test hashes are in `registration.json`; old frozen
physical, messages and twofft files were imported without modification.

## Feedback and permitted claim

**Update H3's interpretation:** there is a measurable joint representation gap,
but “the current scalar joint detector is generally overconfident because it
omits coupling” is not established and is contradicted by the pilot-present
aggregate direction in this grid. Keeping existing gain uncertainty improves
conditional scoring relative to these point approximations. A proposed
directional/coupled replacement must outperform that existing uncertainty-aware
baseline under common priors, handle improper/multimodal posteriors or state a
valid local regime, and meet separate real-state and matched-budget gates.

Permitted wording: “In a registered small CPP-AFDM model, exact enumeration
reveals directional covariance and cross-moment discrepancies in scalar joint
inference. Confidence errors depend on geometry and initialization; covariance
factorization alone does not identify the cause of marginal LLR error.”

This is a bounded diagnostic result. It does not prove a production failure
cause, justify a new algorithm by itself, demonstrate FER improvement, or
settle innovation novelty. No additional tuning or experiments are requested
by this result; downstream decisions follow the main CSV's existing gates.
