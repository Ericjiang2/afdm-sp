# Actual-support soft-Gram screening

Date: 2026-10-21. Same old200 keys /50 shared frame clusters; informed exploratory screening. Producing source `ee5882ce`. Independent saved-raw recount and primary bootstrap verification passed; scientific/user acceptance remains pending.

Both saved upstream outputs achieve zero decoded information-bit errors on every key when followed by the new full soft-Gram gain update. LLR log loss also improves relative to the best native control, with additional compute. This is a useful candidate result, not independent confirmation or a general superiority claim.

## Observation

Preserve the exact saved support, h0 and original check prior for both upstream L-diag (scalar Gamma) and L-cov (full Gamma). No SBL fitting, new frames or tuning. New full/diag20 updates use the same pre-symbol snapshot, RHS and zero-mean prior `alpha=noise*P`; their only difference is the off-diagonal entries of `M=B^H B+Gamma(v_pre)`. The native symbol/residual schedule and zero propagated gain variance are unchanged. The new full block versus native point changes the gain-update family, including its pseudo-observation/Onsager formula.

Replay every native baseline on the same inputs in the same worker, with outcome-independent balanced arm order. All1200 native baseline outcomes match old decoded hashes/errors/FER exactly; terminal continuous scores also reproduce exactly. Source-qualified final-gain checks pass the frozen tolerance. Source/raw/prior qualification precedes all new calls.

| Downstream gain update | Scalar-Gamma upstream failures/200 | Full-Gamma upstream failures/200 |
|---|---:|---:|
| Native fixed | 4 | 15 |
| Native point | 40 | 11 |
| Native joint | 23 | 2 |
| New full soft Gram | **0** | **0** |
| New diagonal soft Gram | 200 | 198 |

Each new full arm also has zero failures in every50-key scenario/SNR cell. The two200-key totals share observations and frame randomness; do not describe them as400 independent samples. Equal zero failure counts do not establish equivalence of the upstream choices or elimination of Gamma reversal.

| Pooled matched contrast | FER difference | Pointwise95% frame-cluster CI |
|---|---:|---:|
| Scalar-upstream new full minus new diagonal | -1.000 | [-1.000,-1.000] |
| Full-upstream new full minus new diagonal | -.990 | [-1.000,-.970] |
| Either new full minus best native full-Gamma/joint | -.010 | [-.025,.000] |
| Scalar-upstream new full minus native point | -.200 | [-.255,-.150] |
| Scalar-upstream new full minus native fixed | -.020 | [-.045,.000] |
| Full-upstream new full minus native point | -.055 | [-.090,-.025] |

Bootstrap:10000 draws, seed20261026, joint resampling of50 P1 frame IDs across all4 cells and10 arms, actual resampled row denominator. All intervals are exploratory and pointwise; no multiplicity-adjusted or confirmatory claim. Full results include all9 frozen contrasts, transitions and all cells.

The best native control fails only twice. The pre-freeze protocol correction records why the percentile-bootstrap upper bound cannot realistically be negative even for a perfect candidate: probability of omitting the at-most-two negative frame clusters is at least(48/50)^50=.1299. The null-spanning interval is inconclusive, not equivalence or noninferiority.

| Quality metric | Scalar-upstream new full | Full-upstream new full | Best native full-Gamma/joint |
|---|---:|---:|---:|
| Mean extrinsic bit log loss | .189826 | .189927 | .219107 |
| Mean final channel NMSE | .024835 | .026482 | .028158 |
| Mean data-symbol MSE | .110024 | .110842 | .119659 |

Primary-comparison secondary log-loss contrasts versus best native: scalar-upstream -.029281[-.034220,-.024547], full-upstream -.029180[-.032705,-.025687], about13.4% lower pooled mean loss. This metric supports the candidate without resolving low-event FER superiority. Channel NMSE is descriptive and does not substitute for decoding quality.

## Frozen verdict

C1 passes: both within-family full-minus-diagonal FER intervals have upper<0. C2 passes: scalar-upstream full-minus-native-point interval upper<0. C3 passes: full-upstream new full has<=2 failures (observed0). C3 is the raw-count forecast corrected before execution, NOT the abandoned impossible significance criterion, and not a noninferiority conclusion. Brier scores: .0625/.1225/.4225. These forecasts are informed by old endpoints and the prior single new real-key outcome.

## Interpretation and next decision

Tested operational result: dropping soft-Gram off-diagonals severely degrades this local-surrogate update family on these inputs. The new diagonal arm is extremely weak, so defeating it alone would not justify further work. The more useful observations are full0/200 for both upstream outputs and improved log loss against the best native control.

Untested candidate explanation, confidence L: respecting correlated gain geometry may reduce the original scalar-update sensitivity. This study does not identify a unique defect in the native AMP iteration or prove actual near-duplicate atoms explain upstream Gamma reversal. Full M contains both mean-regressor and symbol-uncertainty coupling; this is not a Gamma-only ablation. A local expected-log Gaussian gain fit is not a global AMP/VI derivation or a novel-method claim.

This is the planned point for an independent Gemini assessment before new-frame validation: give it the actual equations, all controls, adverse diagonal results, low-event limitation and compute cost. Ask it to assess global consistency, relation to existing soft Gaussian/EM updates and the cheapest decisive test. Strongest alternative: retain the existing native full-Gamma/joint receiver, whose observed error rate is already low and cost smaller. No Gemini message, new run, paper change, claim promotion or task archive has been performed.

## Compute and provenance

Matched instrumented median detector times: new full42.73/42.62ms versus best native28.82ms (about48% more); detector+decoder59.11/59.23ms versus45.65ms (about29% more). New full/diagonal retain qualification eigensolves, Cholesky and diagnostic covariance solves; these concurrent CPU measurements are not optimized or isolated deployment latency. Upstream SBL time is excluded, so no end-to-end pipeline cost comparison is established. Native20 has41 FFTs; either new20 has61 FFTs,20 gain solves and20 diagnostic covariance solves.

Gate16 detector/10 decoder calls; main2000 detector/2000 decoder calls. Total2016/2010; zero SBL fits. Twelve one-thread CPU workers, GPU disabled, entire chain EXIT0/DONE in32.77s wall; aggregate user+system228.83CPU seconds, within the frozen15min/3core-hour budget.

- [Summary](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_cohort1/summary.json), SHA256 `eabf7b1f5e134e5d0e02456aaa851a74965590de3471aef2b62e92047da2b443`.
- [Gate](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_cohort1/gate.json), [source config](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_cohort1/config_shard000.json), [status](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_cohort1/STATUS.txt), [producing commit](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_cohort1/PRODUCING_COMMIT.txt).
- Raw12 `rows_shard000.jsonl` through `rows_shard011.jsonl` remain at `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_cohort1/`; all per-file sizes/MD5/SHA256 hashes and the independent recount are in [verification.json](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gram_cohort1/verification.json), SHA256 `f62b62826af2650eca05e3d26aca06f6082db1be9f3ec9d9ef583cba315d38db`. Total raw27,034,607bytes remain remote.

Original sources/results remain immutable. Thirty-two synthetic contract tests, four-module compilation and shell syntax checks passed before execution. Synthetic tests are engineering evidence only; they are not these scientific observations.

Independent verification read every raw key and original reference, checked balanced arm order/attempts/primitive/source/byte hashes, and directly recomputed all4 primary FER contrasts in pooled and4-cell groups plus C2 using a separate RNG-index bootstrap implementation. Points/intervals match exactly; maximum mean-metric difference4.44e-16 from summation order. All33 original small evidence files match local/remote SHA256s. Maximum gain/covariance normal residuals1.013e-16/1.175e-16. The audit made zero receiver, decoder, SBL or generator calls. No unresolved implementation/readout blocker remains.
