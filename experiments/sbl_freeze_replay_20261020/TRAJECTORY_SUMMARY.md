# Point updates increase the error/variance mismatch in both Gamma variants

Readout 2026-10-21; exploratory analysis plan frozen on 2026-10-20, commit **ef324633**. This processes old trajectories only: **zero receiver, SBL or decoder calls**, no new frames or selected outcome strata. Known endpoint means informed the analysis; this is not an independent confirmatory experiment.

## Observation

All 200 keys / 50 RNG-frame clusters, U/G, physical rho .3, 7/8 dB, scalar/full Gamma x fixed/point/joint. E is true symbol mean-squared error; V is mean reported symbol variance, both in the frozen internal data-power .5 convention. G=E-V is a moment-mismatch diagnostic, not a posterior-calibration theorem.

Time averages use every one of the 20 symbol-update steps per key, equally weighted:

| Gamma / mode | Mean E | Mean V | Mean G |
|---|---:|---:|---:|
| scalar / fixed | .144512 | .102532 | .041981 |
| scalar / point | .159596 | .084355 | .075241 |
| scalar / joint | .179823 | .134785 | .045038 |
| full / fixed | .156670 | .108002 | .048668 |
| full / point | .161404 | .083004 | .078400 |
| full / joint | .183519 | .136259 | .047261 |

Paired point-minus-fixed time-average effects, with pointwise 95% paired frame-cluster bootstrap intervals (10000 draws, seed 20261023):

| Gamma | Delta E | Delta V | Delta G |
|---|---:|---:|---:|
| scalar | +.015084 [.012952, .017219] | -.018177 [-.019337, -.017032] | +.033261 [.030719, .035901] |
| full | +.004734 [.003121, .006395] | -.024998 [-.026517, -.023477] | +.029732 [.027586, .031941] |

The scalar-minus-full interaction in Delta G is **+.003528 [.001783, .005318]**. This interaction is positive, but the much larger point-mode gap increases occur in both variants. Full Gamma has a larger variance reduction and a slightly larger absolute time-average point gap than scalar Gamma. Do not present generic variance compression as scalar-specific or infer an additive causal share from these quantities.

All four cells show scalar point-minus-fixed E up and V down with directional intervals. The gap interaction is positive by its interval in U/7, U/8 and G/7 dB; G/8 dB spans zero (.000819 [-.001531, .003182]). Full cell outputs are retained in JSON.

## Time pattern and metric limits

The [four-panel figure](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/trajectory_analysis1/trajectories.png) shows E, V, G and the channel NMSE of the gain actually used for each symbol update. Solid lines are scalar Gamma, dashed lines full; mode colors are shared.

For scalar point, mean E is .13802 at step10 and .14551 at step20 while V falls .06588 to .04538. Its pre-update channel NMSE falls .06391 to .03719 over the same displayed steps. This is a descriptive segment of the full trajectory, not a selected inferential window or a claimed significant onset. Gain-update transients also produce early channel-NMSE spikes in both variants; these curves do not establish divergence or the cause of later decoding loss.

Joint mode has higher time-average E than point, yet lower final FER and terminal E. Thus time-average E itself is not a terminal decoding-performance ranking. Fixed mode also develops a late E/V gap. The plot supports a shared trajectory symptom; it does not identify variance as the causal harmful term, which reset memory matters, or a Gram/Onsager mechanism. No per-step LLR/log-loss data exist in these rows, so none are fabricated.

## Frozen checks and interpretation

- T1: scalar point-fixed time-average E CI lower>0 and V CI upper<0: **passes**, informed-analysis forecast Brier .1600.
- T2: scalar-minus-full Delta G interaction CI lower>0: **passes**, Brier .2025.

Both pre-analysis directional criteria pass. The interpretation remains narrower than a unified explanation: the error/variance mismatch is shared by both Gamma variants, with a positive additional scalar mode effect. Candidate explanation (untested, confidence L): coupled gain/soft-symbol updates can accompany underestimated uncertainty relative to realized error. This analysis does not show that increasing variance would repair FER or explain the scalar/full ranking. The original matched restart/gain-adaptation effects remain as reported; no accepted claim is changed.

A future causal test would need a matched intervention rather than choosing a temperature or stopping step from this plot. No such intervention, new-frame run or scope expansion is performed here.

## Integrity, reproducibility and outputs

- All 12 raw/config shards bind to the immutable accepted summary SHA256 `b3b6f0ac9f4a0720df2ca9465eec40ec536033006e23e7c72740f17e91b0e2d0`, producing source identity and actual frozen validator hash. All six arms, 21 gain states and 20 symbol states qualify, with positive finite V. All original terminal means/counts and NMSE trajectories reproduce; mean summation parity uses the predeclared rtol1e-12/atol1e-14, counts exact.
- Symbol step t uses h_(t-1), not the returned h_t. Both aligned and returned NMSE are preserved. Paired bootstrap resamples all four scenario/SNR rows jointly by frame and uses actual resampled row count. The same weights preserve contrasts across metrics and Gamma. Time curves are descriptive point estimates, with no per-step significance or onset claim.
- Independent standard-library recomputation from the raw rows matches the time-average E/V effects. Raw hashes and local producing script hashes match, and PNG/SVG/summary SHA receipts are verified. Parent visually inspected the complete PNG: all panels, axes, six-arm legend and line styles are readable. SVG text remains editable.
- Reused one existing latest-Sol agent for two additive files; main checked code, actual input qualification, direct recomputation and visual output. Thirteen combined tests and compilation passed; unavailable lint/type tools were not claimed. One CPU thread, EXIT=0, 3.31 user + .17 system CPU seconds, wall 4.16 seconds, no GPU or new simulation. Matplotlib/temp/cache writes stayed under /data/guoyikun.
- Original raw rows remain at `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1/rows_shard000.jsonl` through `rows_shard011.jsonl` (44,181,396 bytes). Original receiver/analyzer/results were not overwritten.
- Derived remote directory: `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/trajectory_analysis1/`. Local small copies: [JSON](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/trajectory_analysis1/summary.json), [PNG](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/trajectory_analysis1/trajectories.png), [editable SVG](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/trajectory_analysis1/trajectories.svg), [verification](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/trajectory_analysis1/verification.json), [raw hashes](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/trajectory_analysis1/RAW_SHA256.txt), original status and runtime log.

Bounded analysis is complete; scientific acceptance, further experiments and archive remain with the user.
