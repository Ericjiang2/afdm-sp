# Exact posterior remainder and local-model scope

## Target and status

**COHERENT AS STATED:** quantify the bilinear remainder at the exact posterior
means, including its nonzero mean and cross term with the linear part. The
registered small-model screen passes only **1 of 48 conditions** (1/24 with
pilot, 0/24 without). An ungated tangent approximation at global posterior means
is therefore not justified across this oracle grid. This does not rule out a
local approximation inside a resolved mode or another independently justified
regime, and does not prove production FER failure.

## Invariant object and assumptions

The object is the exact posterior second moment of signal fluctuation about
`s0 = H(mh)(pilot+md)`, where `mh=E[h|y]` and `md=E[d|y]`.
These are diagnostic posterior moments, **not independent incoming priors**.

The finite distribution over d and proper Gaussian conditional `h|d,y` are
taken from the sealed ORACLE-01 outputs. Conditional gain means/covariances are
`m_k,C_k`, probabilities `w_k`; operators U_p and pilot are fixed. The mixture
may be improper and strongly dependent even though each conditional Gaussian
is proper. Current operators are square N by N; the generic implementation
uses M observation dimensions and noise energy `M sigma2`.

No new oracle, receiver, simulation, or generator is executed in this study.
One saved posterior per condition is sufficient: changing the earlier scalar
initialization does not change the exact posterior and must not double its
sample count.

## Derivation map

1. Expand the exact bilinear physical signal around posterior marginal means.
2. Condition on each finite d and integrate affine functions of Gaussian h.
3. Average component means, second moments and linear/remainder cross terms.
4. Check against direct unexpanded signal fluctuation; separately center at the
   true posterior signal mean to retain the effect of nonzero remainder mean.
5. Compare an independent-product diagnostic and apply a frozen engineering
   screen. This final screen is a decision convention, not an algebra theorem.

## Exact expansion and component formulas

Define `eta=h-mh`, `a=d-md`, `B0=[U_p(pilot+md)]`, `H0=sum_p mh_p U_p`.
Then, identically,

`H(h)(pilot+d)-s0 = L+t`,

`L=B0 eta+H0 a`, `t=sum_p eta_p U_p a`.

For component k set `g_k=m_k-mh`, `Q_k=[U_p(d_k-md)]`,
`l_k=B0 g_k+H0(d_k-md)`, `t_k=Q_k g_k`.

The conditional identities are

`E[t|k]=t_k`,

`E[||t||²|k]=tr(Q_k C_k Q_k^H)+||t_k||²`,

`E[||L||²|k]=tr(B0 C_k B0^H)+||l_k||²`,

`E[L^H t|k]=tr(B0^H Q_k C_k)+l_k^H t_k`.

Average all quantities using w_k. Although `E[L]=0`, **E[t] need not vanish**.
The exact second-moment decomposition is

`E||L+t||² = E||L||² + E||t||² + 2 Re E[L^H t]`.

For an independent check the code constructs the full unexpanded
`B_k=[U_p(pilot+d_k)]` and evaluates the mean and covariance of
`B_k h - s0` directly. This checks the centering and both cross contributions,
not just a restatement of the expanded sum. The posterior signal variance about
its **true** mean is `E||L+t||²-||E[t]||²`.

Remainder covariance and pseudo-covariance are also retained:

`Ct=sum_k w_k[Q_k C_k Q_k^H+t_k t_k^H]-mt mt^H`,

`Pt=sum_k w_k t_k t_k^T-mt mt^T`, where `mt=sum_k w_k t_k`.

The conditional pseudo term is zero because h|d,y is proper, but the mixture
pseudo term generally is not. Stored h/d pseudo-covariances are computed from
the same mixture. Dropping these is an additional approximation.

## Independent-product formula and counterexample

If eta and a are independent, zero-mean, and have finite second moments Ch,Cd,

`E||t||² = sum_pq Ch[p,q] tr(U_q^H U_p Cd)`,

`E[t]=0` and `E[L^H t]=0`.

Independence factors the expectation of `eta_p conj(eta_q) a a^H`; properness
is not required for this energy identity. Here it is evaluated using the
**posterior marginal** Ch,Cd only as a product-distribution diagnostic. It is
not a valid independence assertion about the true posterior and is not fed to
an inference update as an independent prior.

A finite correlated counterexample is included in the tests: scalar U=1,
pilot=0.2, h=d in {-1,+1} with probabilities {0.25,0.75}. About mh=md=0.5:

- exact remainder energy 1.3125, independent-product prediction 0.5625;
- remainder mean 0.75;
- linear energy 1.08, cross term −1.8;
- direct fluctuation second moment 0.5925, true centered variance 0.03.

The cross term cancels a substantial part of the separate positive energies.
Reporting only the independent-product energy would miss both mean bias and
cancellation. The example has degenerate conditional gain covariances and a
correlated finite mixture; it is not mislabeled an independent Gaussian model.

## Frozen diagnostic protocol

`execution/remainder/v1/registration.json` was written before computation and
binds remainder source/tests, thread helper, and the prior comparison's sealed
registration/results/recount. All 48 conditions are reused without selection:
N=2/3, two geometries, pilot amplitude 0/0.6, two noise variances, three seeds.
They contain six independent (N,seed) exogenous clusters, not 48 independent
channel draws. No significance or population pass-rate estimate is claimed.

The necessary-for-this-engineering-screen conditions are both

`E||t||² <= 0.1 N sigma2`,

`|2 Re E[L^H t]| <= 0.1 N sigma2`.

Passing is only sufficient to **continue screening** a local model; it does
not prove accurate marginals, a valid message schedule or posterior Gaussianity.
Failure blocks unqualified use under this gate, not every possible local model.
The thresholds were not adjusted after seeing results. CPU cap was 60 seconds.

## All-condition results

|Registered group|Both gates pass|Mean remainder/noise energy|Mean absolute cross/noise energy|Remainder/noise range|
|---|---:|---:|---:|---:|
|All|1/48|1.576414|0.498817|0.002372–6.606413|
|No pilot|0/24|2.140963|~0|0.308422–6.606413|
|Pilot 0.6|1/24|1.011864|0.997634|0.002372–2.826339|
|Separated geometry|0/24|1.696502|0.605012|0.347414–5.648627|
|Near-duplicate geometry|1/24|1.456325|0.392622|0.002372–6.606413|

Every case is included in `results.json`. The sole passing record is case 44;
it is reported as part of the cohort, not selected as a new deployment regime.
Only 1/48 meets the remainder-energy gate; 27/48 meet the cross gate, including
all 24 degenerate no-pilot tangents.

For pilot-present cases, mean remainder energy is 0.696543 and linear energy
0.690104. The **mean of their casewise ratios** is 1.123469 (range
0.007203–2.104201). Mean cross term is −0.574059 and remainder-mean squared
norm is 0.176229. Its independent-product energy estimate is 0.590969: mean
underestimation 0.105574, but the error changes sign across cases, ranging
−0.352669 to +0.116046 in independent-minus-exact units. No universal bound is
inferred from the average.

The pilot-present remainder improper ratio `||Pt||F/||Ct||F` averages 0.328459;
h/d pseudo-covariance norms average 0.129028/0.127016. These are full conditional
posterior diagnostics, not proper-Gaussian working-model covariances.

## Why the no-pilot tangent degenerates

Global QPSK rotation symmetry forces mh=md=0 in the no-pilot model, while the
signal product remains informative. Therefore B0=H0=0 mathematically: L=0 and
the entire signal fluctuation resides in t. In stored floating arithmetic,
linear energy averages 1.47e−33. The reported t/linear ratios around 1e32–1e34
reflect that vanishing denominator and should not be interpreted as physically
precise amplification factors. The exact limiting ratio is undefined/infinite.

No-pilot remainder-mean energy averages 0.838557, and direct centered signal
variance averages 0.511960. Marginal h/d pseudo-covariances are near zero by
symmetry, while remainder impropriety remains nonzero (mean ratio 0.209541).
Neither proper marginals nor vanishing conjugate h-d cross-covariance imply
the bilinear joint posterior is independent.

## Validation, evidence and cost

Five deterministic tests pass: known h/data zero-remainder limits; independent
proper-Gaussian second-moment quadrature; the correlated finite-mixture
counterexample; path permutation and direct decomposition; invalid input
rejection. The independent Gaussian test uses exact second-moment quadrature,
not Monte Carlo data mislabeled as analytic proof. Initial tests failed only
because the implementation module did not yet exist; no diagnostic ran then.

Tests took 0.002 s unittest time, 0.015850 process CPU including discovery.
The 48 saved-posterior evaluations used 0.081302 CPU s / 0.087239 wall s.
There were **zero new oracle, scalar_joint, complete receiver or generator
calls**, and no discarded/failed case. Actual Accelerate mode 1 was verified
before/after with all five thread environment variables set to 1.

Expanded versus direct fluctuation energy agrees within **1.33e−15** across
all 48 cases. `recount.json` verifies source/input bindings, all input/output
raw hashes, the 48-case/96-event ledger, unchanged thresholds and decomposition.
This is same-author verification; an independent review remains a distinct step.

Results SHA256: `9b7837f7f576f5a6180a71693747d5f61ac78a2172df143ff7081835592ef5c6`.

## Feedback, boundary and non-claims

The proposed global-posterior-mean tangent is **not supported as a general
replacement on this exact grid**. Most pilot-present cases also fail; the
limitation is not solely an artificial no-pilot control. A replacement would
need an independently justified local regime, mode conditioning, or an explicit
method retaining the neglected terms; the present result does not establish
any of those solutions. Do not silently inflate residual noise or relabel the
independent-product formula as an exact posterior correction.

This is not a blanket no-go theorem for local Schur/Woodbury inference, which
remains algebraically valid for its stated linear-Gaussian model. It separates
that model's exact algebra from the unverified approximation to a bilinear,
potentially multimodal posterior. No new performance experiment, new mechanism
revision, or threshold tuning is prescribed by this report.
