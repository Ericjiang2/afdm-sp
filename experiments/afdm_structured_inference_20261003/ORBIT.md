# ORBIT-01: conditional C2 information and unknown-orbit mixing

Result: **supported as a conditional mathematical mechanism; deployment and
production utility are not tested**. C2 cross moments can carry prediction
information that marginal means discard. They do not, by themselves, establish
a bit-LLR defect or a scalable receiver.

## Model and production evidence boundary

Entry point: `python -m experiments.afdm_structured_inference_20261003.orbit`.
Run: `.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/orbit_v1/`.
All 18 cases, registration, source hashes, effective thread binding, inputs,
joint/factorized probabilities, moments, raw NPZ and cost receipts are retained.

The existing production LDPC C2 algebra receipt in
`results/afdm_deep_rethinking_20261003/research/operator_geometry.md` is reused
only after checking the cached matrix-file SHA-256 equals
`cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052`.
No matrices were regenerated and the old algebra was not rerun. Its evidence is
that this production code preserves 0 and pi rotations, not pi/2 or 3pi/2.

The new posterior experiment is explicitly a different, tractable model:
N=3; all 32 even-parity six-bit QPSK words; independent discrete channel prior
on `(+h_A,-h_A,+h_B,-h_B)` with masses `(0.3,0.3,0.2,0.2)`; real CPP path
actions with delay 0/1 and fractional Dopplers 0.31/-0.27. This produces 128
joint states and 64 C2 orbits, not a two-mode full posterior. The entire legal
tiny code prior is retained. The finite channel support is not a Gaussian or
the production generator's gain law.

Three independent exogenous draws are paired across pilot amplitudes
0, 0.1 and 1.5 and uniform/external-bit-tilted priors. The fixed external bit
log odds are `[0.7,-0.3,0.2,0.4,-0.5,0.1]`, restricted and normalized on the
legal code. They never reuse y or a posterior as an independent prior.

## Fixed-orbit identities

With h=s h0, d=s d0 and s in {+1,-1}, define
`u=H(h0)d0`, `v=H(h0)p`, `a=2 Re((y-u)^H v)/sigma2`, and the legal prior ratio
Ls. Then kappa=tanh(a+Ls/2), E[h d^T]=h0 d0^T and
`E[delta_h delta_d^T]=(1-kappa^2) h0 d0^T`.
The signal mean is u+kappa v and its conditional covariance is
`(1-kappa^2) v v^H`. The nonuniform marginal likelihood uses
`logcosh(a+Ls/2)-logcosh(Ls/2)` and stable logaddexp.

Each orbit in every case is compared against direct two-point likelihood
normalization. The largest error across means, nonconjugate product/cross,
signal mean/covariance, log likelihood and orbit weights is **4.9738e-14**,
below the frozen **3e-11** tolerance. A separate test rejects substituting the
conjugate covariance for the physically required transpose product.

## Unknown-orbit result and counterexamples

The global pseudo-cross decomposes exactly into the orbit-weighted conditional
cross and the covariance of conditional means between orbits. Both parts must
be included to recover the global predictive mean.

| Condition | Observed result |
|---|---|
| No pilot, uniform code prior | kappa=0 in every orbit; all exact bit probabilities are 0.5; global marginal-mean product prediction squared errors 0.04316–1.52467 |
| Weak pilot, uniform prior | weighted sign concentration 0.0680–0.2100; within-orbit information remains substantial |
| Strong pilot | weighted sign concentration at least 0.9999999938; within-orbit cross largely vanishes, but top-orbit mass can still be only 0.1980 |
| Uncertain multi-orbit example | seed 1, uniform/no-pilot: top mass 0.1909, full-cross singular values 0.1907 and 0.02176 |
| Nonuniform no-pilot example | seed 2: full-cross singular values 0.46299 and 0.10140; within/between cross norms 0.44029/0.06220 |

Thus a fixed-orbit rank-one identity does not imply rank one for the full
posterior. Even perfect sign concentration does not identify the orbit.
Retaining all exact cross moments restores every saved predictive mean to
roundoff (largest squared error 2.654e-30). This calculation uses oracle joint
weights; it is a diagnostic identity, not an implemented inference shortcut.

The required LLR counterexample is explicit. Replace the exact joint posterior
by the product of its exact gain and legal-word marginals. Cross moments then
disappear while the data marginal is unchanged. Bit LLR differences are at
most **1.7764e-15**, despite substantial prediction errors. In the uniform
no-pilot cases, a hard sign choice has exactly the same noiseless prediction
but bit-probability MSE **0.06566–0.23537** relative to the uncertain posterior.
This also shows that prediction agreement does not imply correct soft bits.

Hard-selecting a single orbit can harm bits even with strongly concentrated
signs: seed 1, uniform/strong-pilot has bit-probability MSE 0.12610 and
prediction squared error 0.05147. The raw results separately retain hard sign,
hard orbit, within-orbit product, global product and restored-moment errors.

## Decision, cost and remaining question

The branch used 0.0978 CPU seconds and 0.1009 wall seconds, one thread and zero
receiver/decoder/remote/GPU calls. It enumerates the full tiny prior solely to
test the mechanism. Exponential codebook enumeration is not an allowed deployed
solution, and shared-process microcost is not a deployment latency estimate.
All 18 conditions come from three paired draws; no confidence interval or
population claim is inferred from them.

Feedback: conditional C2 moments are useful constraints for a legal joint
message representation. A deployable method must still infer unknown orbit
weights and emit consistent bit/cavity messages without a codebook bank or
complete restarts. This work neither solves that closure nor rules it out. It
does rule out inferring an LLR/FER improvement merely from correcting the
predictive cross moment, and rules out describing the entire posterior as a
single rank-one C2 correction. Other research directions remain independent.

Validation: focused fixed-orbit and no-pilot counterexample tests pass, and all
18 saved joint posteriors are recounted without generating new observations.
The production hash is verified separately from these tiny-posterior tests.
