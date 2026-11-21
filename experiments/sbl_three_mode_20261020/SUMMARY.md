# Three-mode SBL pilot: mean-only updates hurt; joint variance propagation mitigates

Exploratory old-data diagnostic, 2026-10-20. User requested one small useful result, then stop. No accepted claim is changed.

## Observation

Frozen Pilot-5 first 50 RNG-frame clusters (9100..9149), U/G, rho .3, 7/8 dB: **200 paired keys**, six arms. Each scalar/full SBL output is reconstructed once and shared by fixed/point/joint, with identical support, initial gains and decoder prior. Detector budget is 20 iterations, damping .3.

| SBL Gamma | fixed failures / FER | point failures / FER | joint failures / FER |
|---|---:|---:|---:|
| scalar | 4/200 = **.020** | 40/200 = **.200** | 23/200 = **.115** |
| full | 15/200 = **.075** | 11/200 = **.055** | 2/200 = **.010** |

Point updates gain means with zero propagated gain variance. Joint additionally initializes and propagates gain uncertainty, changing subsequent coupled messages.

Primary scalar contrasts, 10000 paired frame-cluster bootstrap draws, seed 20261020; pointwise percentile 95% intervals:
- point minus fixed: **+.180 [.130, .235]**.
- joint minus point: **-.085 [-.130, -.045]**.

Scalar fixed-to-point transitions: 36 successes become failures, zero failures rescued. Point-to-joint: 17 rescued, zero newly broken. Full point-to-joint: 9 rescued, zero newly broken. Full point-minus-fixed is -.020 [-.060, .015125], not evidence of equivalence.

Average composite-channel NMSE (linear) for scalar Gamma is .063008 initially, .037117 after point, .046185 after joint. Thus the mode with the lowest average channel NMSE has the highest FER. Of the 36 scalar fixed-success/point-failure keys, **32 have non-increasing channel NMSE** (outcome-selected descriptive diagnostic, not a primary test). Raw extrinsic bit log loss is .23086/.28108/.25406 for fixed/point/joint (positive LLR favors bit 0; loss in nats/bit).

## Registered predictions and interpretation

- P14 (point FER between fixed and joint): **false**.
- P15 (point-fixed CI lower > 0): **true**.
- P16 (joint-point CI lower > 0): **false; direction reversed**.

The mean-updating mode alone can harm scalar-Gamma decoding even with zero propagated gain variance. Joint mode mitigates this harm relative to point in this cohort. This rules against attributing the observed deterioration solely to enabling the variance-propagating mode. It does **not** isolate a single variance-term causal effect or prove an Onsager, Gram, duplicate-atom, shrinkage or LLR-temperature mechanism. Candidate interpretation (untested, confidence L-M): task-sensitive soft-symbol/gain feedback matters beyond global channel Frobenius NMSE. No new explanation is promoted to a claim.

## Integrity, provenance and limits

- Real gate: observer on/off parity on all six arms; exact old fixed/joint decoder and SBL-output replay; fixed h unchanged; point variance zero; independent small dense NMSE check .5311495881 vs identical reference, truth/self zero.
- All 200 rows passed old replay; no receiver error or excluded key. Twelve configs share source identities; 22 frozen source checks are ok. Independent direct raw recount matches all six failure counts.
- Producing source commit **d3e4a468**. Original receiver execution completed all rows, then aggregation failed at a str/Path hashing boundary. Regression reproduced it; analysis-only fix **f7d5d4a8**, 3 tests pass. Frozen remote scripts/configs/raw rows were preserved, no receiver rerun. Corrected analyzer is in a separate directory.
- Receiver/gate process tree: 1334.90 user + 20.67 system CPU seconds, wall 2:26.72. Corrected aggregation: 2.62 wall seconds. No GPU; maximum 12 one-thread workers. No automatic expansion.
- Remote raw: `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1/rows_shard000.jsonl` through `rows_shard011.jsonl`, 44,181,396 bytes total. Retained remotely.
- Local small evidence: [summary](../../afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/analysis_fix/summary.json), [raw SHA-256 manifest](../../afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/analysis_fix/RAW_SHA256.txt), [independent count receipt](../../afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/analysis_fix/verification.json), [real gate](../../afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1/gate.json). Original failed aggregate log remains remote at `run1/aggregate.log`; original run EXIT=1 and corrected analysis COMPLETED records are preserved separately.
- Reviewed locally by an independent gpt-6-sol agent; no remaining evidence/interpretation blocker. The reviewer did not claim raw-row access; the parent performed the remote independent recount.
- Reused old frames, one generator/code/modulation, one pilot fraction, two SNRs, fixed SBL compute. Not prospective confirmation or a general detector-design theorem. Stop here for user assessment.
