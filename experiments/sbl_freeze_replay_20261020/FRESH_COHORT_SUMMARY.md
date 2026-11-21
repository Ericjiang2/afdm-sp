# Prospective fresh-frame soft-Gram validation

Date: 2026-10-21. Producing source73882cff3fb7b10ae3877d7b3f738b6082cee643. Fifty reserved P1 frame IDs2000000..2000049 /200paired keys, same U/G,rho.3,SNR7/8dB. Method, primary criteria and NF1/NF2 committed before any new-frame outcome. Independent saved-raw/count/source/bootstrap audit passed.

Both frozen full-block candidates retain the old-cohort logloss benefit on new frame streams: about12.7% lower loss than the fixed best native control. Each has1/200 failed keys versus4/200 for the control. FER intervals still include zero; no FER superiority or noninferiority is established.

## Observation

The frozen corrected P1 generator uses the same entropy/domain and channel law, with fresh frame coordinates. The pre-run recorded-config inventory checked4394existing files and found no registered overlap. This supports freshness within recorded project experiments, not an exhaustive statement about unregistered historical outputs. No hyperparameters, SNRs, pilot fractions or off-grid settings were selected after outcomes.

Each key refits shared pilot-only stage1 SBL, performs original fixed20/LDPC50, then refits both L-diag/L-cov stage2 SBL from the original APP-derived moments/check prior. Two full-block candidates and the fixed prior-best L-cov/native-joint control receive exactly the corresponding selected support/h0 and original prior. The terminal hook returns L-diag/full and L-cov/joint to the pipeline diagnostic row, explicitly labeled as such; those rows are not original fixed-gain outcomes. All detectors use20steps/damping.3; full uses zero propagated gain variance and the immutable expected-Gram solve, native joint retains its original variance propagation.

| Terminal receiver | Failures/200 | Mean extrinsic bit logloss | Mean channel NMSE | Mean data MSE |
|---|---:|---:|---:|---:|
| L-diag upstream + full block | 1 | .188051 | .023415 | .107635 |
| L-cov upstream + full block | 1 | .188066 | .026229 | .108960 |
| L-cov upstream + native joint (fixed reference) | 4 | .215546 | .027881 | .116769 |

| Candidate minus fixed reference | Primary logloss delta / pointwise95% CI | Relative logloss change | Secondary FER delta / CI |
|---|---:|---:|---:|
| L-diag/full | -.027495 [-.032228,-.022813] | -12.76% | -.015 [-.045,.005] |
| L-cov/full | -.027480 [-.030561,-.024581] | -12.75% | -.015 [-.035,.000] |

All4scenario/SNR cells individually have favorable logloss intervals for both candidates, reported as secondary pointwise contrasts rather than eight independent confirmations. Decoder failures by50-key cell:

| Cell | L-diag/full | L-cov/full | L-cov/joint |
|---|---:|---:|---:|
| U,7dB | 0 | 1 | 1 |
| U,8dB | 0 | 0 | 1 |
| G,7dB | 0 | 0 | 2 |
| G,8dB | 1 | 0 | 0 |

L-diag/full rescues all4control failures but breaks1previously successful key. L-cov/full rescues3control failures, shares1failure, and breaks none in this sample. The equal1/200failure totals for the two candidates neither establish equivalent upstream choices nor imply the same failed key. The three arms share observations/frame randomness; they are not600independent samples.

## Frozen verdict

NF1/NF2 pass: both pooled candidate-minus-reference logloss intervals have upper<0. Forecast probabilities .70/.75 yield Brier .0900/.0625. Bootstrap10000draws seed20261028, resampling the same50P1frame IDs jointly across all4cells/all3arms, using actual sampled row denominators. All intervals are pointwise percentile intervals. Two preselected candidates are reported without best-arm selection.

Neither candidate triggers the registered detected-FER-harm flag (FER CI lower>0), but absence of this flag is not a safety/noninferiority verdict. The primary verdict is favorable prospective logloss validation with FER unresolved, not deployment acceptance. No native-failure, Gamma-reversal, prior-invariance mechanism or method-novelty criterion was tested.

## Interpretation and decision boundary

Tested result: the new gain-update family's score benefit persists under the same physical model on reserved new frame streams, after genuine upstream refitting. It is no longer supported only by replayed old data. The L-cov/full comparison holds upstream support/h0/prior fixed and replaces the downstream update family. L-diag/full versus the fixed reference additionally changes upstream output, so it is an operational pipeline comparison, not a single-component causal estimate.

Untested explanation(L): respecting correlated mean and symbol-uncertainty geometry may improve the finite-step gain/symbol interface. Earlier Gamma-only results isolate a component contribution on old data, but this new test does not identify a unique Onsager/near-duplicate cause. Same-law generalization does not establish new-rho/SNR/off-grid robustness, support completeness, global VEM/CAVI validity or innovation relative to existing methods.

Frozen stage2 SBL reaches its convergence criterion in114/200 L-diag fits and10/200 L-cov fits; both retain the100-iteration cap, with zero reported jitter events. Mean selected atoms24.00/23.23. These are finite-budget upstream results, not converged-posterior comparisons; no iteration increase or support retuning followed the readout.

Recommendation(M): retain the full block as the candidate for further work; another old-cohort diagnostic or model debate is less useful than deciding the evidence/novelty target. Strongest alternative remains the original native reference, whose FER difference is unresolved and detector cost smaller. Evidence that would change the recommendation includes a prospective reliability reversal, a deployment cost that outweighs benefit, or insufficient novelty. No further simulation, literature search, optimization, paper/mainline switch, claim promotion or active-task archive is performed automatically.

## Compute and evidence

Main:100scenario-specific fresh base generations,200keys,600SBLfits,800receiver/800decoder calls. One OLD U/300/700/9100 qualification key adds1base,3SBLfits,4receiver/4decoder; totals101bases/603SBL/804receiver/804decoder. The gate reproduces original round1 decode, both support/h0/prior inputs, both full results and L-cov/native-joint endpoints before any fresh generation. Fixed full-block and actual imported source paths/hashes match the reviewed bytes. Truth remains scoring/diagnostic-only.

Twelve single-thread CPU workers, GPU disabled; DONE/EXIT0, all within frozen845s/3core-hour ceiling. Whole chain148.37s wall,1309.43user+21.17system seconds=.36961core-hours. Full terminal medians44.42/43.83ms detector and61.50/60.80ms detector+decoder, native reference29.32ms and46.63ms, all instrumented and concurrent. Mean stage2SBL times2.44/2.58s are recorded separately; shared stage1/screening work and diagnostic multi-arm calls mean batch totals are not per-arm deployment latency. Diagnostic eigensolves/Cholesky/covariance solves remain included. No optimized end-to-end cost claim.

- [Summary](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/summary.json), SHA256017d80ac773ba3568e7331b9879dccc3434d159153825d49c191d640945e7b35; all3arms,4cells,paired effects,source/config/generation/raw hashes.
- [Source config](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/config_shard000.json), [old-key gate](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/gate.json), [gate attempt](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/gate_attempt.jsonl), [status](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/STATUS.txt), [producing commit](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/PRODUCING_COMMIT.txt), [time](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/time.log).
- Twelve rows_shard000.jsonl..rows_shard011.jsonl (20,276,050bytes total) remain under /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/. Independent byte-size/hash/path and bootstrap receipt: [verification.json](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/fresh_cohort1/verification.json), SHA25659886f5b2735788d48943e5da62f936a9c7dee86ff397d470060012bb5075ae7. Main raw is not downloaded.

Nine focused synthetic tests, targeted source/gate corruption regression, compilation and shell syntax checks passed before real calls. A missing shared-loader source binding was corrected before freeze. These engineering checks are not the scientific outcome. Scientific acceptance and subsequent scope remain with the user.

Independent audit checks all12fresh raw shards,200unique keys/50reserved frame IDs,100+1base generations,allfit/decoder attempts and603SBL/804receiver/804decoder calls. Actual source/family/input/prior/support/h0 and old-gate endpoint bindings pass; gate maximum continuous difference0. Independent NumPy direct-RNG cluster resampling reproduces pooled/cell primary/FER effects to2.08e-17. Audit adds zero generator/SBL/receiver/decoder calls. No remaining bounded execution/readout blocker.
The audit verifies saved input hashes/fingerprints, source paths and the known-key input/output gate; it does not independently reconstruct unsaved bit arrays or observation/header tensors. Final verification includes separate path/size/MD5/SHA receipts for the gate attempt and all13generation files.
Statistical recount uses saved per-key terminal scores. Raw terminal LLR/decoded-bit vectors are not stored, so the underlying loss/error calculations are source/gate qualified rather than independently recomputed from those unsaved vectors.
