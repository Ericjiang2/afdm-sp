# Final-gain restart recovers part of the scalar-SBL decoding loss

Exploratory follow-up, 2026-10-20. Same 200 scalar-Gamma keys / 50 old frame clusters as the three-mode pilot; U/G, rho .3, 7/8 dB. No sample extension, tuning, second-stage SBL rerun or accepted-claim change.

## Observation

| Detector arm | Failures / 200 | FER | Mean final channel NMSE | Mean raw bit log loss |
|---|---:|---:|---:|---:|
| Saved fixed20 from h0 | 4 | .020 | .063008 | .23086 |
| Saved point20 from h0 | 40 | .200 | .037117 | .28108 |
| P40: continuous point40 from h0 | 41 | .205 | .034894 | .29844 |
| RF: saved h20, restart fixed20 | 20 | .100 | .037117 | .26186 |

RF starts a fresh symbol/message state with the original round-1 check prior, fixes the returned point20 gains h20, and uses no point20 decoder feedback. Its logical detector history is 20+20 steps; the first 20 steps are reused from saved evidence. P40 has 40 continuous steps. These are distinct trajectories with the same logical step count, not an equal-runtime benchmark.

Primary paired frame-cluster bootstrap contrasts (10000 draws, seed 20261021; pointwise 95% intervals):
- RF minus point20: **-.100 [-.155, -.055]**; 21 failures rescued, 1 success broken.
- P40 minus point20: **+.005 [-.025, .035]**; 6 rescued, 7 broken.
- RF minus P40: **-.105 [-.150, -.065]**; 22 rescued, 1 broken.

| Cell (50 keys each) | fixed20 | point20 | P40 | RF |
|---|---:|---:|---:|---:|
| U, 7 dB | 1 | 18 | 19 | 9 |
| U, 8 dB | 0 | 4 | 3 | 2 |
| G, 7 dB | 2 | 16 | 18 | 8 |
| G, 8 dB | 1 | 2 | 1 | 1 |

## Registered verdict and bounded interpretation

- P17: RF improves point20 with CI upper < 0: **true**, Brier .1600.
- P18: P40 improves point20 with CI upper < 0: **false**, Brier .2025.
- P19: RF improves P40 with CI upper < 0: **true**, Brier .2025.

The registered restart/freeze intervention recovers part of the old point20 loss; simply continuing to 40 steps does not show a pooled improvement in this cohort. The latter interval is not an equivalence test and does not rule out improvement at other budgets. RF remains worse than the saved fixed20 initialization (20 versus 4 failures).

Lower mean channel NMSE again does not ensure better decoding: P40 has lower NMSE than point20 but slightly more failures and higher raw bit loss. RF retains the same returned h20 and therefore its final channel NMSE, while improving decoding. Ordering caveat: point20's last symbol/LLR update uses the pre-final-update gain, whereas the returned gain is post-update h20. Do not claim identical gain values generated the two arms' LLRs.

One candidate explanation (untested, confidence L): the coupled soft-symbol/gain update trajectory contributes to some failures beyond the final global channel-error magnitude. Reset and freeze are combined here; this does not isolate state reset, freezing, gain-update ordering, Gram conditioning or an Onsager mechanism. A minimal future discriminator would add a fresh point20 from h20 alongside RF, preserving the reset while toggling gain adaptation. No further arm is authorized or launched by this readout.

## Integrity and provenance

- All 200 exact planned keys, 50 shared-frame clusters; zero failed or excluded rows. Each reconstructed round-1 prior hash and P40 first-20 h/scalar-trace prefix matches the saved evidence exactly. Representative old point20 decoded bits/errors replay exactly; observer-on/off parity passes both new arms; RF gains remain fixed.
- Independent standard-library raw recount matches 4/40/41/20 failures. Raw hashes match the summary, and current new source hashes match producing configs. Two aggregation tests, Python compilation and shell syntax checks pass. Pre-run independent local latest-Sol code review preceded the real receiver gate; the main agent reviewed the small import fix and final evidence. No new external-model call was made for these outcomes.
- Initial attempt run1 (source feffc7ed) failed its source gate before numerical outcomes: a generic imported `driver` name collided with the frozen headroom driver in the module inventory. The independently hashed reference helper now uses its own alias. No frozen receiver source or expected hash changed. Fix/source commit **50d79546**; successful run **run2**, EXIT=0. Failed logs remain in run1; failed helper-source snapshot remains remotely at `/data/guoyikun/tmp/sbl-freeze-replay-failed-source-20261020/`.
- Successful process tree: 200.77 user + 15.99 system CPU seconds, wall 26.78 seconds. Failed source-gate attempt: 5.00 + .49 CPU seconds, wall 5.48 seconds. Combined launcher cost about .0617 core-hours and 32.26 execution wall seconds; diagnostic SSH time is additional and small. CPU only, at most 12 one-thread workers. Actual cached replay runtime is not deployment runtime.
- Immutable raw rows remain on deinlab at `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2/rows_shard000.jsonl` through `rows_shard011.jsonl`, 9,129,222 bytes total. Prior source experiment remains unchanged.
- Local evidence: [summary](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2/summary.json), [real gate](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2/gate.json), [raw hashes](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2/RAW_SHA256.txt), [independent receipt](../../afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2/verification.json), configs and original status/logs in the same output tree.

Old-data diagnostic, not fresh-frame confirmation or a unified theory. The bounded run is finished; scientific acceptance and any next experiment remain with the user.
