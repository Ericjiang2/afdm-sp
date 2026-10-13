# CGR: one zero-receiver-call mechanism falsification

## Status and purpose

This is a NEW exploratory mechanism analysis of the existing sealed 25-observation, four-arm run. It does not amend the original protocol, change `candidate_pass=false`, authorize tuning, or authorize new receiver/decoder calls.

Hypothesis under test:

> Phase-aligned CGR removes a physical data-uncertainty force mismatch while preserving TF's scalar gain response metric. Its effect on decisions is mediated by the delayed gain-to-data natural-field response, not by stepwise descent of true-channel error. The specific proposed explanation of BLOCK's harm is amplification, by its gain response metric, of physically visible weak waveform-response modes. Covariance contractions are recorded separately, not used as an unspecified explanation when the metric hypothesis fails.

Algebraic identities alone do not establish this hypothesis. The transport predictions and the proposed BLOCK mechanism must survive independently.

## Authorization boundary

Use only the original v2 observed seal and already saved source, raw arrays, checkpoints, analysis_r2 records, and tagged truth payloads. The observed seal quoted in the report is:

`42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43`

The report quotes commit `dc228d7254274f3be3403514fc75f0758aacc15c`. Verify these against the actual archived inventory rather than resolving frame names in another campaign.

Receiver calls: 0. LDPC calls: 0. New observations: 0. New trajectories: 0. Retuning: 0.

Do not execute a replay to obtain missing vectors. Read source to derive algebraic contractions and their analytical directional derivatives; evaluate those expressions at recorded states only. Tangent recurrences are diagnostic calculations, not alternative nonlinear receiver trajectories. Do not call the full receiver, acquisition, structural search, or decoder. Do not alter the original artifacts or analysis_r2 files.

The presently accessible handoff contains the report, not the full raw numerical trace. Nothing in this protocol claims these tests have already been performed.

## Fixed cohort

Analyze all eight targets, not only the rescued four:

- s650_f0390, s650_f0415, s650_f0718, s650_f0720
- s650_f0770, s650_f0996, s600_f0600, s700_f0732

The four observed CGR rescues are s650_f0390, s650_f0720, s600_f0600, s700_f0732.

Retain the seven triggered previously rescued controls:

s600_f0958, s650_f0127, s650_f0413, s650_f0519, s650_f0761, s650_f0797, s700_f0184.

Retain the three triggered distinct-delay controls:

s600_f0087, s600_f0552, s700_f0509.

The seven easy controls are nontriggered bypasses. Their unchanged outputs must not be counted as evidence of safe forced CGR or BLOCK updates.

## Existing evidence to read

Use the report's actual paths and inventory identifiers for:

- `analysis_r2/physical_trace.json`
- `analysis_r2/working_moments.json`
- `analysis_r2/projection.json`
- `analysis_r2/decisions.json`
- `analysis_r2/report.json`
- source-bound v2 raw artifacts, entering states, final detector LLRs, and relevant source modules

Inspect and report actual NPZ keys and iteration timing. Do not infer an array's stage from a similar field name. In particular distinguish physical R, waveform-response G=B(xbar)^H B(xbar), and working Gamma; distinguish pre-update h, barred h, post-update h, and the data weights used for terminal LLRs.

The protocol required full x/mu/v/s snapshots for the eight targets, but only scalar/path traces on controls. If a requested control decomposition cannot be reconstructed from existing artifacts, mark it unavailable. Do not invent historical state or fill it with a new call.

## 1. Reconcile the exact source map and timing

Verify the actual final batch has 20 synchronous TF iterations followed by one LDPC50 invocation, with fixed incoming code prior during TF20. Verify the final LLRs come from the final data-denoiser weights, not from a hidden recomputation using the last gain output.

For BASE/CGR/SHAM define

    lambda_t = P + 1/vq_t
    k_t = alpha_t*N*vx_t/lambda_t
    M_BASE = I
    M_CGR = R
    M_SHAM = D^H R D

D has fixed alternating signs within each same-delay group in stored slot order.

At a common entering state, reconcile the saved post-update means with

    hplus_CGR - hplus_BASE = -k_t*(R-I)@hbar_t.

There is no extra beta factor on this direct gain-denoiser difference. Damping acts through barred states and residual/variance histories.

The finite physical intervention must compare `hplus_BASE` with `hplus_BASE+dh`, when dh is the difference of post-update means. Check whether the original analyzer used this matching anchor. Report any discrepancy separately; do not rewrite its original gate outcome.

## 2. Disentangle finite physical changes from derivatives

For each recorded BASE step, keep the old signed effect D_t. Using precisely the same anchor and physical normalization, compute

    Q_t = ||H(dh_t)||_F^2 = N*dh_t^H R dh_t
    A_t = D_t + Q_t.

A_t is the first-order improvement along dh; D_t=A_t-Q_t is the full finite-step improvement. If the archived mismatch is divided by N, apply that normalization to both terms. Report all 20 rows, not a selected late window. Sums across distinct BASE states are descriptive, not a telescoping causal effect.

This panel diagnoses the original local story only. It cannot pass the revised mechanism by itself, and it does not change `candidate_pass=false`.

## 3. Primary new test: BASE-only prediction of terminal natural-field shifts

For QPSK +/-a +/-ja, reconstruct at each recorded iteration

    gamma_t = 1/vr_t                       # includes the actual reciprocal floor
    omega_t = alpha_t*P*u_t
    f_t = gamma_t*mu_t + H(hbar_t)^H@s_t - omega_t*xbar_t

Before clipping and numerical implementation details,

    Lext_I = 4*a*real(f_t)
    Lext_Q = 4*a*imag(f_t).

Reconcile to saved detector LLRs with the actual all-I/all-Q order, input-prior subtraction, clipping and precision. Use actual final decoder inputs for final comparisons. Do not call LDPC.

The reconstructed natural field is an exact diagnostic identity of the declared scalar map, not a new likelihood theorem.

Let S_t contain every recorded mean and damping-history state needed by BASE. Derive matrix-free analytical JVPs J_t of its map from the hash-bound source, evaluated solely at BASE states. Include dependence through channel power h^H R h, scalar variances, alpha, barred means, Gaussian gain denoising, and QPSK soft means/variances. Do not freeze variance or residual derivatives merely because they are inconvenient.

For CGR and SHAM separately, propagate the parameter-free first-order prediction

    dz_0 = 0
    dz_(t+1) = J_t dz_t + b_t

where the only nonzero component of b_t is the post-update gain impulse

    b_CGR,h = -k_t*(R-I)@hbar_t
    b_SHAM,h = -k_t*(D^H R D-I)@hbar_t.

Read out the predicted final detector natural-field/LLR shift with the analytical output derivative at the last BASE data step. Apply the declared one-sided derivative at clipping boundaries and report boundary cases; compare unclipped fields as well.

Timing invariant: the final gain-only impulse has zero influence on that batch's terminal data LLRs. Verify this without running a new receiver.

Compare predictions to actual saved arm-minus-BASE field shifts for all eight targets. Report unscaled normalized error, cosine, and prediction error relative to the zero-change predictor. Do not fit a scale, damping, lag, subset of iterations, or sign after seeing results. Keep per-frame results and pooled values distinct. A scalar correlation obtained only after fitting a scale is not a successful prediction.

Also report the framewise proper bit log-score using the actual clipped decoder input:

    loss(L,c) = mean(logaddexp(0, -(1-2*c)*L)).

This is descriptive calibration evidence, not an acceptance substitute for decoding correctness. Successful decoding does not mathematically require lower average bit log-loss. Inspect the saved wrong-bit confidence burden as well, without treating bits as independent experimental units.

A useful transport explanation must outperform zero-change prediction, distinguish actual CGR and SHAM shifts in their physical orientation, and explain the observed decision-relevant message differences. A correct one-step injection formula alone is tautological and insufficient. If finite nonlinear differences make the BASE tangent inaccurate, the proposed perturbative transport explanation has not been established; do not rename the failure an unmeasured basin effect.

## 4. BLOCK cross-check within the same offline audit

First read and transcribe BLOCK's exact gain precision, regularization/floors, covariance update, and contractions. The following standard Gaussian-block equation is a hypothesis to reconcile, not permission to replace the actual source:

    g_R = B(xbar)^H@s - alpha*N*vx*R@hbar - P*h
    hplus_scalar = h + inv(P + 1/vq)*g_R
    hplus_block  = h + inv(P*I + alpha*G)@g_R
    G = B(xbar)^H B(xbar).

At the genuinely common initial state, verify whether the other relevant input/output contractions are identical. Only then attribute the mean-step difference to this metric. Preserve the exact source formula if it differs; explicitly reject an incompatible hypothesized formula rather than silently adapting it.

For the source-verified metric, resolve its response by G modes. The proposed amplification ratio for an eigenvalue g_j is

    (P + alpha*||xbar||^2)/(P + alpha*g_j)

when floors are inactive. Record actual force excitation in each mode: a large inverse eigenvalue with zero force is not an explanation.

Weight motion by physical R, not just coefficient norm:

    physical_motion = N*dh^H R dh.

An amplified operator-null direction cannot explain changed detector fields.

Record the distinct full-covariance channel contraction

    W_Sigma = sum_ij Sigma[j,i] * U_i^H U_j
    tr(W_Sigma)/N = tr(R @ Sigma)

and use W_Sigma (not tr(Sigma) alone) when attributing changes in data reaction and uncertainty power. Under Sigma=u*I, W_Sigma=P*u*I.

Check whether physically visible metric amplification actually precedes/contributes to the harmful saved LLR changes, including the seven triggered BASE-correct controls as far as their saved fields permit. A condition number, large covariance, or worse final decision alone is insufficient. If only coefficient-null motion is amplified, or if metric amplification is absent, reject the specific BLOCK explanation. A dominant covariance effect requires an explicit measured decomposition; it cannot be used as a generic fallback story.

## Fixed reporting and stop rule

Write a new, separately named offline report and retain:

1. source/field/timing reconciliation and missing-field inventory;
2. complete finite-versus-infinitesimal physical panel;
3. framewise BASE-only transport prediction errors for CGR and SHAM;
4. source-verified BLOCK metric/physical-covariance panel;
5. one verdict: supported provisionally, falsified, or unidentifiable from the archive.

The original receiver gate remains failed in all cases. No result here is a fresh population FER result.

If transport predictions fail, BLOCK's proposed physical amplification is absent, or the available archive cannot establish the required chain, leave CGR as an empirical patch and stop this branch. Do not tune, expand the cohort, request missing-state replays, add receiver calls, or revive a generic 'basin escape' explanation. A further production test requires a separate decision and authorization.
