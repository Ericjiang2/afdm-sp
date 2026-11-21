# Equivalent physical channel and working prior, different native point updates

2026-10-21. A bounded mathematical/representation probe, not a new FER study or a proved mechanism for the Gamma reversal. Producing source commit **c4635b24**; independent algebra review preceded execution.

## Observation

Every atom is duplicated twice, each initialized gain halved. For aggregation D, the new coordinate prior CN(0,I/(2P)) pushes forward to the same original working prior CN(0,I/P). Initial H is also unchanged. Noise, observation, pilot and symbol prior are identical. Only one synthetic n32/P2 fixture and one predetermined saved real key U/rho .3/7dB/frame9100 were used; no SBL rerun or new physical frame.

| Diagnostic | Synthetic n32, P2 to4 | Saved real n1024, P24 to48 |
|---|---:|---:|
| Max relative initial H action discrepancy (3 probes) | 2.10e-16 | 1.31e-15 |
| Fixed20 extrinsic LLR maximum absolute difference | 1.60e-14 | 1.87e-14 |
| First point symbol LLR maximum absolute difference | 8.88e-16 | 3.55e-15 |
| First point-update relative physical H difference | .062906 | 1.380326 |
| First gain-difference formula maximum residual | 9.11e-17 | 1.11e-16 |
| Final point20 extrinsic LLR maximum absolute difference | 3.13542 | 9.53251 |
| Final point20 LLR relative L2 difference | .16104 | .53080 |

Physical first-update differences use the Frobenius norm of the difference divided by the ORIGINAL representation's updated-operator norm. Thus1.380326 is not an NMSE to truth or a FER change. The real first-update action differences on all three independent deterministic vectors are also substantial (relative1.23 to1.34), excluding a coordinate-only nullspace difference.

The synthetic fixed-x exact Gaussian posterior aggregate is invariant: direct mean discrepancy3.34e-16 and covariance discrepancy approximately1.13e-17. Dense DFT/shift atoms independently match the native Gram, physical action and Frobenius norm in this small fixture. No dense1024 channel is built for the real key.

In the saved real key, original fixed20 and point20 replay their stored scores/decoded hashes and point20 returned h20. Original/duplicate fixed20 both decode successfully with0 information-bit errors; original/duplicate point20 both fail, with42/180 errors respectively. These are individual outcomes, not evidence of a population FER trend or of consistent harm from duplication.

## Exact algebra and location of the difference

The [derivation package](../../.trellis/tasks/10-20-sbl-freeze-replay/research/representation-invariance.md) states assumptions, exact prior pushforward, fixed-mode invariance and the first native point update. Write tau=1/P, q=the common gain pseudo-variance, a=B^H s, d=hb*sv*n*mean(v0). At the first update,

- original: h1=tau/(tau+q) * [h+q*a-q*d];
- aggregated k-fold duplicate: Dg1=tau/(tau+k*q) * [h+k*q*a-q*d].

Therefore

`Dg1-h1 = tau*(k-1)*q*(tau*a+q*d-h)/((tau+q)*(tau+k*q))`.

The native scalar coordinate update generally fails to commute with duplicate aggregation, despite equivalent initial H and equivalent induced working prior. The first symbol update still agrees because it precedes the first gain update. Both native examples match the difference formula to floating precision, and their physical channel actions differ after that update.

The aggregate Onsager subtraction is q*d, not k*q*d; the first formula must use prior variance v0 rather than the saved post-symbol v1. Keeping coordinate tau unchanged after duplication would double the aggregate prior variance and invalidate this controlled comparison.

## Frozen qualification and interpretation boundary

- I1, fixed20 and first-point-symbol parity at rtol1e-10/atol1e-12 in both cases: **passes**, engineering forecast Brier .0025.
- I2, first-gain formula parity plus relative physical difference>1e-8 in both cases: **passes**, Brier .0100.

This identifies a concrete structural representation sensitivity in the frozen scalar approximation. It is stronger than an association between symbol error and reported variance, but does not show that the actual SBL near-duplicates cause the observed scalar/full ranking. Uniform exact duplication changes coordinate redundancy while preserving its physical pushforward; actual candidate sets need not satisfy that equivalence. No claim of mathematical novelty, complete instability, a general Gram cure, improved receiver or unified explanation is made. The prior is the detector's assumed Gaussian prior, not the true physical generator law.

## Integrity and reproduction

All original source/input hash gates pass. Initial aggregate gain, working-prior pushforward, duplicate Gram and physical power/action match. Fixed output/all non-gain states/traces and first point symbol/non-gain states pass the declared tolerance. Point/fixed propagated gain variance remains zero. Original saved h0/prior/support and codeword are restored, truth is scoring-only. Exact Gaussian verification is a labeled synthetic fixed-x check, not an oracle real-receiver intervention.

Seventeen combined tests and compilation passed. Reused latest-Sol reviewer independently checked the derivation and implemented/checked two additive files; main inspected code and independently checked recorded gain-difference/posterior residuals and source/output hashes. Current wrapper/native/physical/validator paths and MD5s are recorded. Existing receiver/helper files were unchanged.

One CPUthread, EXIT=0,4.36 user+.39 system CPU seconds, wall4.73 seconds. Remote directory: `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/representation_probe1/`. Local [summary](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/representation_probe1/summary.json), [config](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/representation_probe1/config.json), [verification](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/representation_probe1/verification.json), and original status/runtime log preserve both cases and the complete source/input receipt.

The bounded probe is finished. No larger cohort, near-duplicate perturbation sweep, algorithm modification or scientific claim promotion is automatically authorized by this result.

## Correction (2026-10-21): uniform-duplication scope

The equivalence used here holds only because **every** atom was duplicated the same k times
with gains split equally: initial H, prior pushforward `D(tau/k I)D^H = tau I`, and the
fixed-mode invariance. Under nonuniform exact duplication (atom p copied k_p times,
`K = diag(k_p)`, `tau' = 1/P'`), the pushforward becomes `tau' K`. That is a per-path prior
variance `k_p/P'` in place of `1/P`, so the working prior and the fixed-mode Gaussian aggregate
are no longer invariant. The full soft-Gram update likewise aggregates to
`(M + alpha' K^-1)^-1 b`, not `h_full`; derivation and numerical check are in the
[full-gram-gain-block correction](../../.trellis/tasks/10-20-sbl-freeze-replay/research/full-gram-gain-block.md).
Inexact near-duplicates are not covered.

Consequence: the non-invariance of the native point update located here is shown for uniform
duplication, where the comparison representation is exactly equivalent. It is a candidate
source of the Gamma reversal, not an attribution. Real scalar-Gamma outputs have nonuniform,
inexact near-duplicates, for which even the reference representations differ. The measured
numbers above are unchanged.
