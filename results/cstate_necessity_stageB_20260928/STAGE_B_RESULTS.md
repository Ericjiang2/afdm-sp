# Stage B: bounded execution stopped at equivalence

**Status: `invalid_partial`; no completed Stage-B performance comparison.** The [registered F1 phase](F1_EQUIVALENCE_TIMING_PROTOCOL.md) stopped after 409 attempted complete wrappers: B=198, Cfast=198, Cref=13. The ledger contains 408 `ok` records and one equivalence failure. Wall time through the stop was 181.045651 s; the failed wrapper's charged time was 0.431404 s. No new observation was generated, no F2 receiver ran, and no Stage-B truth analysis was opened.

## What failed, and what did not

At `s650_f0197`, the frozen `coordinate_scores` counter was **995** in the sealed Stage-A C reference and **1002** in Cfast. The contract required exact counters, so the producer stopped correctly. The remaining reported counters match: 8 slots, 20,600 bank scores, 80 coordinate visits, 320 Newton steps, 74 joint solves and 66 accepted coordinates. This is not evidence of a changed path budget or a worse decoded word.

The [read-only saved-output comparison](F1_F197_OFFLINE_COMPARISON.json) found identical ordered delays/bank centers and zero bit differences in both native rounds and the final output. Maximum Doppler/gain/objective-history differences were approximately `6.56e-11 / 9.14e-11 / 1.88e-10`, within the original `2e-10` absolute tolerance. These inspected fields **do not waive the separate exact-counter gate** or establish equivalence on the unrun population. The producer stopped before checking later baseline-array gates; those were not all established by this comparison. The first recorded objective-history difference is at index 31, about `2.27e-13`; saved aggregate state alone does not identify the first differing trial's cause.

The source rule increments this counter only for a new exact floating-point trial key within a coordinate visit. Direct response, initial bank-correlation and final-refit spot checks were bitwise equal in the checked cases; they did not establish the cause of the intermediate search divergence. [The bounded four-acquisition diagnosis](F1_F197_DIAGNOSTIC_PLAN.md) completed in the fixed reference/fast/reference/fast order, with zero TF/LDPC/full-wrapper calls. In that fresh instrumented process all four coordinate traces matched and all four score counters were 995: the two reference calls reproduced the sealed reference, while the two fast calls did not reproduce the stopped run's 1002. [The actual receipt](f197_diagnostic_v1/receipt.json) therefore records no first trace divergence. Instrumentation and execution history were not independently isolated; the original discrepancy remains unexplained, and the diagnostic does not restart or rehabilitate the stopped campaign.

## What can be reported

- **Reference F1 profiling:** eight plain acquisitions averaged 0.3588 s; instrumented acquisitions averaged 0.4196 s. The fixed 17-call profile identifies repeated response construction, conjugation and Python duplicate checking as major measured costs. Its nested timings are nonadditive; see [profile report and raw evidence](F1_PROFILE_REPORT.md).
- **Optimized F1 performance:** not qualified. Partial attempt timings remain in the [ledger](failed_attempt_f1_matched_v1/observed/ledger.jsonl); no successful-subset FER, complete-population latency, deadline table or speedup is published.
- **Published F2:** nine synthetic algebra/fixed-posterior checks passed; no complete EM/grid/support/data-feedback implementation or receiver comparison was admitted. [F2 receipt](F2_IMPLEMENTATION_RECEIPT.md) distinguishes explicit model-derived corrections, diagonal-covariance approximation and still-unfrozen policies.

The existing Stage-A frontier remains historical evidence, unchanged:

| Historical Stage-A system | Information failures / 1,024 | Mean complete latency |
|---|---:|---:|
| F0 + TF | 40 | 0.349 s |
| F0 + TF + CSTATE | 6 | 0.363 s |
| Reference F1 + TF | 12 | 0.668 s |
| Reference F1 + TF + CSTATE | 0 | 0.668 s |

These are [Stage-A measurements](../cstate_necessity_stageA_20260928/README.md), not new F1-fast or F2 results. The complete Stage-B FER/BER, matched LOCAL/F2 increment, triggered-F2 and reliability–latency frontier outputs were **not produced because their admission gates did not close**.

## Evidence and independent limits

[Failure and traceback](failed_attempt_f1_matched_v1/observed/invalid_partial.json) → [launch exit](failed_attempt_f1_matched_v1/launch/launch_exit.json) → [independent failed-attempt recount](independent/FAILED_ATTEMPT_RECOUNT.md). The independent check matched all 409 attempt/ledger identities, all 825 checkpoint SHA references and both 1,234-path SHA/MD5 side inventories. It did not open remote NPZ payloads or truth, and is not a completed-experiment PASS. No successful observed seal exists.

Raw/checkpoint files remain under `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/cstate_necessity_stageB_20260928/observed_f1_matched_v1/`; the [SHA256](failed_attempt_f1_matched_v1/partial_sha256.txt) and [MD5](failed_attempt_f1_matched_v1/partial_md5.txt) inventories identify each retained object. Registration commit: `a8aaa5dedd420660ff34cda94cd7f9bc95a32821`; failure archive and bounded-diagnosis commit: `d203207abde5a236ee2ee41948e1204fdaad550a`.
