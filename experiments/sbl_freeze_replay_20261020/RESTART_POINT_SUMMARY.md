# Restart helps point mode; fixing gains helps further under the same restart

User-approved single-arm addition, 2026-10-20. The [original RF/P40 readout](SUMMARY.md) is preserved. This is an exploratory old-frame comparison, not independent new-frame confirmation or a promoted paper claim.

## Observation

RP starts fresh point20 from exactly the same saved h20 and original round-1 check prior as RF. Same 200 scalar-Gamma keys / 50 RNG-frame clusters, U/G, rho .3, 7/8 dB. No SBL was rerun and no outcome stratum was selected.

| Logical detector history | Failures / 200 | FER | Mean final channel NMSE | Mean raw bit log loss |
|---|---:|---:|---:|---:|
| P40: point20 + continuous point20 | 41 | .205 | .034894 | .29844 |
| RP: point20 + restart point20 | 31 | .155 | .040286 | .27024 |
| RF: point20 + restart fixed20 | 20 | .100 | .037117 | .26186 |

Saved fixed20 from h0 remains 4/200 (.020), and saved point20 is 40/200 (.200); both are contextual 20-step baselines rather than equal-total-step controls.

Primary contrast, RP minus RF: **+.055 [.015, .095]**. Relative to RF, RP breaks 14 successes and rescues 3 failures. Under the same reset, h20, prior and 20-step budget, continuing gain adaptation worsens pooled FER in this cohort.

Secondary contrast, RP minus P40: **-.050 [-.085, -.015]**. Relative to P40, RP rescues 16 failures and breaks 6 successes. Within point mode, restarting non-gain internal state at h20 improves pooled FER.

Intervals are pointwise paired frame-cluster percentile bootstrap intervals, 10000 draws, seed 20261022, with all four cells of a frame resampled jointly.

| Cell (50 keys) | P40 failures | RP failures | RF failures |
|---|---:|---:|---:|
| U, 7 dB | 19 | 13 | 9 |
| U, 8 dB | 3 | 6 | 2 |
| G, 7 dB | 18 | 11 | 8 |
| G, 8 dB | 1 | 1 | 1 |

The pooled improvement is not uniform across cells: RP is worse than P40 at U/8 dB. P40 has the lowest mean channel NMSE but the highest pooled FER among these three arms.

## Frozen verdict and explanation boundary

- P20, RP-RF CI lower > 0: **true**, Brier .2500.
- P21, RP-P40 CI upper < 0: **true**, Brier .2025.

The new arm separates two conditional operational effects: a reset benefit under point adaptation, and a fixed-gain benefit under reset. This supersedes the earlier lack of a matched reset-point control; it does not retroactively alter the original combined-intervention result. It does not provide an additive decomposition into independent mechanisms, isolate which reset state matters, or prove a Gram, Onsager or LLR-calibration explanation. The reset includes symbol, residual and damping memories; later gain and symbol trajectories then coevolve. Returned gains are post-update, whereas the last symbol/LLR update uses the pre-final-update gain.

One candidate interpretation (untested, confidence L): harmful history in the coupled soft-symbol/gain loop and continued point adaptation can each contribute in their respective tested conditions. This is still a lead about internal dynamics, not a general physical-channel error rule or a complete explanation of all Gamma results. No additional experiment is launched after this readout.

## Qualification and provenance

- All 200 planned unique keys / 50 frame clusters, no failed/excluded rows. Saved h20/h0/prior bytes and hashes are checked; every RP row binds the exact old row and input/support. The immutable old summary pins raw hashes, configs and source identity.
- Real qualification reproduces old RF decoded hash, error count, LDPC iterations, raw log loss, NMSE, data MSE and symbol variance exactly. RP observer-on/off parity and zero gain variance pass. Before the first gain update, fixed/point symbol outputs and recorded non-gain states agree exactly.
- Current loaded receiver inventory and frozen actual paths/hashes match run2; omitted private helper imports are separately checked against producing helper hashes. Old receiver scripts/results were not overwritten. Truth enters scoring only.
- Seven combined aggregation tests, compilation and shell syntax pass. Reused latest-Sol agent implemented and checked four new files; main independently inspected and qualified them, recounted raw failures and checked raw/source hashes. No new agent or Gemini call.
- Producing commit **99f918be**; restart_point1 EXIT=0. CPU only, <=12 one-thread workers. Measured process-tree cost 91.08 user + 11.17 system CPU seconds (about .0284 core-hours); wall 14.50 seconds including gates/aggregation. Cached actual runtime is not deployment latency or the logical 40-step cost.
- Raw retained on deinlab: `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/restart_point1/rows_shard000.jsonl` through `rows_shard011.jsonl`, 2,360,083 bytes total.
- Local [summary](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/restart_point1/summary.json), [real gate](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/restart_point1/gate.json), [raw SHA receipts](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/restart_point1/RAW_SHA256.txt), [independent verification](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/restart_point1/verification.json), configs and original status/runtime log in the same output directory.

Bounded execution is complete. Scientific acceptance, further scope and archive remain with the user.
