# Gamma-only off-diagonal ablation

Date: 2026-10-21. Source1198b266. Same old200keys /50 shared P1 frame clusters; informed exploratory screening. Independent saved-raw/count/bootstrap audit passed. No SBL fit or new physical frame.

Retaining full BHB while diagonalizing only downstream Gamma worsens logloss under both saved upstream choices. Scalar-upstream decoding also loses6 previously successful keys. This isolates a useful uncertainty-coupling contribution within the new point-gain receiver family.

## Observation

Same saved support/h0/check prior and20-step schedule; zero propagated gain variance. Reference Q=BHB+Gamma(v_pre)+noise*P I. New gamma_diag Q=BHB+diag(diag(Gamma(v_pre)))+noise*P I. The narrow facade delegates all transforms and uses the immutable full-loop source. L-diag/L-cov below name the UPSTREAM estimator output; full/gamma_diag name the separate DOWNSTREAM gain-block covariance choice.

| Saved upstream | Full Gamma logloss | Diagonal Gamma logloss | Relative increase on deletion | Full / diagonal Gamma failures |
|---|---:|---:|---:|---:|
| L-diag | .189826 | .235469 | 24.04% | 0 / 6 of200 |
| L-cov | .189927 | .202184 | 6.45% | 0 / 0 of200 |

| Upstream | Primary logloss delta: diagonal minus full | Pointwise95% frame-cluster CI | Secondary FER delta / CI |
|---|---:|---:|---:|
| L-diag | +.045642 | [.042346,.048891] | +.030 [.005,.060] |
| L-cov | +.012258 | [.010382,.014279] | .000 [.000,.000] |

Both primary intervals have lower>0. All4cells individually have positive logloss delta intervals for both upstream variants; they are secondary pointwise reports, not eight independent confirmations. Scalar-upstream failures are3/50 U7dB,0/50 U8dB,2/50 G7dB,1/50 G8dB; the other three upstream/downstream combinations have0 in every cell. The two200-key totals share the same observations/frame randomness and must not be treated as400 independent samples. Zero-failure contrasts do not establish equivalence or zero population FER.

| Saved upstream | Full / diagonal Gamma final channel NMSE | Full / diagonal Gamma data MSE | Full / diagonal Gamma reported symbol variance |
|---|---:|---:|---:|
| L-diag | .024835 / .029225 | .110024 / .130160 | .057432 / .048415 |
| L-cov | .026482 / .025893 | .110842 / .116603 | .058497 / .055359 |

L-cov channel-NMSE difference is inconclusive: diagonal-minus-full -.000588[-.001184,.000043], despite worse logloss and data MSE. Lower point-estimate channel NMSE does not substitute for detection quality. Lower reported symbol variance coexists with larger data error in both variants; this is an error/variance observation, not posterior-calibration or variance-causality proof.

## Frozen verdict

Protocol and GA1/GA2 were committed before any new receiver outcome. Both informed forecasts pass: logloss(new gamma_diag)-logloss(saved full) CI lower>0. Forecast probabilities .65/.55, Brier .1225/.2025. Bootstrap10000draws, seed20261027, resampling all4cells and both variants jointly over50 P1 frames; pointwise percentile95% intervals and actual resampled row denominator. Not an independent confirmation or a multiplicity-adjusted superiority test.

## Interpretation and decision boundary

Tested component effect: full downstream Gamma contributes to logloss on this fixed old cohort even when BHB remains full. The benefit previously observed cannot all be attributed to keeping BHB off-diagonals. Compared descriptively with the earlier whole-Gram-diagonal arm (200/198 failures), keeping full BHB already changes outcomes greatly (6/0 failures); retaining Gamma off-diagonals improves further (0/0). These sequential controls do not yield an additive percentage decomposition or a unique explanation of the original native update failure.

Untested candidate explanation (L): uncertain symbols induce correlated gain directions that an isotropic diagonal-Gamma penalty represents poorly. The current test establishes the component effect under the declared hybrid schedule, not that this explanation accounts for the native Onsager/near-duplicate or upstream-ranking reversal. New-sample generalization, complete support, a global VEM/CAVI guarantee and method novelty remain unestablished.

Engineering recommendation (M): keep full Gamma in the candidate receiver for any later prospective validation. Strongest alternative is retain the accepted native full-upstream/joint receiver until new frames and end-to-end cost justify a change. Evidence that would change the recommendation is a prospective loss reversal or a measured deployment cost that outweighs quality; neither is tested here. No new run, optimization, external debate, mainline switch or claim promotion follows automatically.

## Execution and provenance

Gate on frame9100/all4cells/both upstreams:8 full replays reproduce decoded outputs/errors/FER, primitive counts and terminal scores/gains;8 new calls plus8 observer-off calls qualify the facade/observer. Observer parity is established by the source-bound runtime assertion, not independent replay of stored per-symbol arrays. Main400receiver/400decoder, gate24/16; total424/416, no SBL. All20-step new calls use61FFT,20gain solves and20diagnostic covariance solves. Original Gamma PSD checks add qualification eigenvalue work before projection. Instrumented timing includes these checks; full Gamma is still computed before projection, so this is not a cheaper receiver implementation.

DONE/EXIT0 in32.20s wall,158.26user+17.04system seconds=.04869core-hours, under15min/3core-hour ceiling. Twelve single-thread CPU workers, GPU disabled. New instrumented detector medians44.41/44.29ms and detect+decode61.67/61.24ms; saved full values42.73/42.62 and59.11/59.23ms come from a different run. No matched or optimized latency inference.

- [Summary](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gamma_ablation1/summary.json), SHA256384c53bbb2f02feba40e8e147102a90fd377bc3e16fdd9e253a37d39cf710fdc: all cells, paired effects, source identity and raw/config/gate hashes.
- [Source config](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gamma_ablation1/config_shard000.json), [gate](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gamma_ablation1/gate.jsonl), [status](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gamma_ablation1/STATUS.txt), [producing commit](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gamma_ablation1/PRODUCING_COMMIT.txt), [time](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gamma_ablation1/time.log).
- Original full summary SHA256 eabf7b1f5e134e5d0e02456aaa851a74965590de3471aef2b62e92047da2b443 and verification SHA256 f62b62826af2650eca05e3d26aca06f6082db1be9f3ec9d9ef583cba315d38db remain immutable.
- Twelve raw rows_shard000.jsonl..rows_shard011.jsonl (7,745,248bytes total) remain under /data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gamma_ablation1/. Raw byte-size/hash/path and independent bootstrap receipt: [verification.json](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/gamma_ablation1/verification.json), SHA25640896c235fe8976a4ce8ef411b9b8bebece1ed6ae8d250014bb4f6e7c1a5e19f.

Eight focused synthetic tests, source compilation and shell syntax checks passed before execution. The local independent review first reproduced and fixed original non-PSD Gamma hidden by projection and a gate-full trace validation gap; both fixes precede the first real call. Original frozen sources/results remain unchanged. Task remains active pending user scientific acceptance.

Independent audit reads all12 raw shards and original frozen references:200 unique keys/50frames/4cells, attempts/source/input/primitive/full bindings and424/416 calls pass. Direct NumPy RNG frame-resampling independently reproduces primary pooled/cell logloss and FER effects, with maximum deviation2.08e-17. Audit makes zero new receiver, decoder, generator or SBL calls. No remaining bounded execution/readout blocker.
