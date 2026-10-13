# Shared-channel probability objects

This module is a bounded mathematical diagnostic using the existing physical CPP/DAFT operators, not a receiver or a claim about the six N1024 failures. Gaussian gain elimination and QPSK enumeration reuse the previous exact oracle. It supplies the missing middle probability object rather than revising the existing Gaussian-pair receiver.

## Factor and cavity contract

Let `F_y(h,d)=p(y|h,d)` be the single full-observation factor. Independent incoming factors are `p0(h)` and `a_j(d_j)`; the latter must be observation-independent external information, or messages from other factors with this factor's site removed. The block message is

\[
F_{y\to B}(d_B)=\int p_0(h)\sum_{d_O}F_y(h,d_B,d_O)\prod_{j\in O}a_j(d_j)\,dh.
\]

No target-block incoming factor occurs here. The factor-to-bit message then sums this block factor times the other block-bit incoming factors, excluding the target's own factor. `outside_cavity` and `block_extrinsic` implement these two exclusions explicitly; no APP-minus-own-LLR subtraction hides the invariant. The saved grid checks own-factor invariance for all local bits, including nonuniform priors. A posterior `q(h|y)` from this same likelihood is not an admissible replacement for `p0(h)` without removing the observation site. This diagnostic does not build such a site or claim an iterative EP algorithm.

The three scores are:

1. Exact Gaussian-gain elimination for every full legal QPSK word, followed by the finite outside sum. This is analytic/enumerated under the stated Gaussian gain prior.
2. Gaussian outside cavity with its mean and full real covariance, integrated over the same gain prior by positive quadrature. Nonuniform independent I/Q priors can be improper; a real augmented covariance retains that information. Uniform priors reduce to the proper complex `CN(y;H(h)x_B,sigma2 I+H(h)C_O H(h)^H)` object.
3. A single Gaussian with the exact second moments of that same cavity. Zero-mean proper Gaussian and uniform-sphere gains make its observation pseudo covariance zero; the known nonzero-gain base also preserves the outside pseudo covariance.

The controlled fixed-total-energy gains are **uniform on the complex sphere**, obtained by normalizing isotropic iid complex Gaussian gains. For P=1, phase is uniform; for P=2, the first power fraction is uniform on [0,1] and phases are independent uniform. This is not the actual production prior: source tracing found that production divides raw gains by the Frobenius norm of a truncated G0 operator and carries those gains to G1 without rescaling. Its geometry-dependent quadratic normalization and raw PDP require a separate pushforward analysis; saved production gain powers sum to about 1.009–1.016 rather than exactly one. Both controlled-sphere QPSK and Gaussian-outside scores require numerical integration: neither is called exact. All densities include normalization constants and prior quadrature weights.

## Fourth-order discrepancy and limits

For a proper Gaussian outside cavity and projection z, define `|m_h|²=hᴴMh`, `v_h=v0+hᴴVh`, with M rank one and V positive semidefinite. Conditional Gaussian fourth moment is `|m_h|⁴+4|m_h|²v_h+2v_h²`. For Gaussian h~CN(0,C), the complex Gaussian quadratic identity gives

\[
E_{mix}|z|^4-E_{MM}|z|^4=4\operatorname{tr}(CMCV)+2\operatorname{tr}(CVCV)\ge0.
\]

For a uniform complex sphere `||h||²=tau`, dimension P and `c=tau/P`, unitary invariance and `sum |h_p|²=tau` give

\[
E[(h^HAh)(h^HBh)]=\frac{\tau^2}{P(P+1)}(\operatorname{tr}A\operatorname{tr}B+\operatorname{tr}AB).
\]

Writing `m=tr M`, `v=tr V`, subtraction yields

\[
\Delta_4=\frac{c^2}{P+1}\{-2m^2+4[P\operatorname{tr}(MV)-mv]+2[P\operatorname{tr}(V^2)-v^2]\}.
\]

The sign is not constrained. For P=1 and M=0, V scalar, `Delta4=0`: a shared uniform phase times an iid circular Gaussian vector remains Gaussian. For P=1 with nonzero fixed target amplitude and V=0, the fixed-modulus random phase mixture has `Delta4=-c²m²`, even without outside interference (general P: `-2c²m²/(P+1)`). The numerical fourth-moment checks include both signs and the zero case. They validate this proper-cavity theorem; they do not extend it silently to the improper nonuniform cavity grid.

For Gaussian iid gains, Var(sum |h_p|²)=tau²/P. Increasing the number of data coordinates at fixed P does not remove that scale randomness. Normalization removes this particular total-energy randomness exactly, but

\[
\operatorname{Var}(h^HVh)=\frac{c^2}{P+1}[P\operatorname{tr}(V^2)-(\operatorname{tr}V)^2]
\]

can remain positive for anisotropic V. In a sequence `y_N=H_N(h)x_N+w_N`, conditionally iid circular Gaussian inputs give conditional expected normalized energy `pd tr(H_N(h)H_N(h)^H)/N+sigma²`. Concentration about that conditional value requires, for example, `tr((H_N H_N^H)^2)/N² -> 0`. The conditional value becomes deterministic for orthogonal-path normalized-trace limits plus fixed total gain energy; that scalar energy limit alone does not imply a joint Gaussian law or accurate block LLRs. No automatic large-N Gaussianization is claimed.

## Saved comparisons and interpretation

The registered grid has N=3, P=1/2, 3 independent exogenous draws, noise .15/1.2, Gaussian and fixed-energy priors, uniform/nonuniform fixed cavity, singleton/pair blocks. Gain/noise draws are paired across conditions; these are not 96 independent samples. Nonuniform cavity is an external fixed message diagnostic; generated data are uniform, so observed Brier/log-loss are descriptive scores rather than a calibration experiment under that nonuniform prior.

Hermite rules or sphere phase/power rules at orders 5/9/13 are compared with independent scrambled Sobol rules of 2^15 nodes. The order-13 result is the numerical candidate; the last refinement and independent-rule errors remain explicit. A failed numerical tolerance does not remove a case. All means and counts include every registered case and are not interpreted as established signs where integration error is unresolved.

Each case stores y, operators, pilot, truth only for scoring, cavity, candidate labels, all raw density scores, normalized probabilities, bit probabilities, LLRs and the two LLR error increments. KL, expected and observed Brier/log-loss, sign changes, and paired MM-minus-mixture differences are saved. The cross term `2 mean[(LLR_mix-LLR_QPSK)(LLR_MM-LLR_mix)]` exposes error cancellation. Known-h and no-outside reductions have separate saved base cases and independent analytic tests.

Run after the source commit:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 /tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.probability --stage probability_v1
```

The runner freezes sources, effective configuration, seed, environment and deadline before calculation; repeated stage names fail. Results belong under the current Mission's `execution/probability_v1`, with every attempt retained. Classical neighbors are conditional Gaussian mixtures, Rao–Blackwellization, EP and bilinear message passing; this experiment establishes no novelty or production utility.

## Completed evidence

The initial 96-row attempt completed in 22.95 seconds, with all 48 controlled-sphere rows passing integration gates and all 24 low-noise Gaussian rows failing. Those results remain unchanged. `probability_refined_v1` reread the identical saved observations, recomputed all 48 Gaussian rows at both noise levels, and retained the 48 admitted sphere rows in one 96-row ledger. It completed in 67.72 seconds; all 96 rows then met the registered numerical gates. The Gaussian primary rule was Sobol 2^18, checked against its nested 2^17 rule, an independent 2^18 scramble, and Hermite order 97 for P=1 or 25 for P=2. Gaussian maximum probability disagreement was 0.000413 for refinement, 0.000383 for the independent scramble, and 0.002728 for Hermite. The latest no-outside low-noise Gaussian base's order-97 probability error against analytic gain elimination was 8.72e-7; old top-level base fields in immutable raw records are historical, not these latest values.

`probability_sensitivity_v1` used only saved scores. Gaussian sensitivity included those four admitted rules. Sphere sensitivity included all nine combinations of QPSK-reference and mixture rules at order 9, order 13, and independent Sobol 2^15. The sign floor was 1e-10. Delta below is loss(MM) minus loss(mixture), so positive favors the mixture; brackets are the observed numerical-rule envelope of the full-cohort mean, not confidence intervals or certified integration bounds.

| Controlled prior | Block KL delta | Bit KL / expected log-loss delta | Expected Brier delta | Stable mixture-better / MM-better block-KL cases |
|---|---|---|---|---|
| Gaussian, 48 rows | [0.0029266, 0.0029832] | [-0.00012979, -0.00010675] | [0.00009523, 0.00010480] | 33 / 15 |
| Isotropic sphere, 48 rows | [0.0196488, 0.0199277] | [0.0055814, 0.0056986] | [0.0015986, 0.0016503] | 41 / 7 |

All these individual block-KL signs persisted across the compared rules. Case 80 (Gaussian) is a stable mixture-worse example, delta block KL [-0.0182741, -0.0181451]; sphere case 57 gives [-0.0307893, -0.0307529]. Negative two-step LLR error cross terms persisted in 26/48 Gaussian and 21/48 sphere rows. Thus preserving the shared-gain mixture can help, but outside-Gaussian error and subsequent Gaussian-projection error can cancel. Three exogenous draws and controlled priors do not establish population performance, calibration under the nonuniform cavity, production causality or novelty.

Reproduce the saved-observation refinement and sensitivity with:

```sh
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.probability_refined --stage probability_refined_v1
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.probability_sensitivity --stage probability_sensitivity_v1
```

Existing stage names are immutable and reject a second invocation; a new attempt requires a new stage name. Nineteen focused tests passed. The machine-readable final receipt is `.mission/20261004_11-00-00-afdm-shared-channel-followup/evidence/probability_final.json`. It explicitly records one provenance deviation: the sensitivity-only 1e-10 guard was hashed/snapshotted before calculation but committed afterward in `6ed0b30f`; the recorded Git HEAD is its predecessor. The producing source matches that later committed blob. The test file was not included in runtime registration; its current bytes were checked against the commit separately. No attempt or raw artifact was rewritten.
