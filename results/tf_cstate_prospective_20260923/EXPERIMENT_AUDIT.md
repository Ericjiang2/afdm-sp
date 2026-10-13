# Independent integrity audit: final TF+CSTATE campaign

**Date:** 2026-09-23

**Reviewer:** independent `gpt-5.6-sol / high`, read-only source and artifact review
**Overall:** **WARN** for procedure/scope; **evidence integrity PASS** for the user-authorized recovery result.

The original one-shot campaign is `invalid`: its analyzer stopped on a local Git-binding receipt schema mismatch before truth access ([failure record](failure/READOUT.md); `analyze_prospective.py:409-424`). The recovery is a separate, explicitly user-authorized offline retry. Its wrapper checks the exact prior failure, frozen files and Git objects, then calls only the recovery analyzer and original verifier (`retry_failed_analysis.py:64-114,147-161`). The analyzer diff accepts only the fifth `verification` key and its exact committed value (`analyze_recovery.py:409-426`). This supports a **qualified recovered-data result**, not an unqualified claim that the original one-shot pipeline completed cleanly.

| Check | Finding | Evidence |
|---|---|---|
| A. Ground truth | **PASS; simulation truth.** `make_frame` generates message/channel/noise before receiver calls; observed inputs contain only `{y,pilot,sigma2}`, while `info/coded` are stored separately. Truth is not derived from decoder outputs. | `generate_population.py:133-138,182-240`; `run_prospective.py:253-281`; `analyze_recovery.py:358-444,506-627` |
| B. Metric denominators | **PASS.** Information FER uses all 1,024 paired frames per SNR. Information and coded BER use fixed bit denominators. The primary CP bound uses full `n`, with no trigger-subset or self-score normalization. | `analyze_recovery.py:275-335`; `paired_statistics.py:24-93` |
| C. Result existence and values | **PASS.** Six analysis outputs match receipt SHA-256. Summary and verifier receipt match recovery status hashes. Independently recounted paired tables are `(818,0,145,61)` at 6 dB, `(984,0,34,6)` at 6.5 dB and `(1004,0,15,5)` at 7 dB. Independent binomial inversion reproduces primary upper bound `−0.0195055986783896`. | `recovery_20260923/analysis/receipt.json`; `summary.json`; `verification/receipt.json`; `status.json` |
| D. Executed evaluation path | **PASS for reported metrics.** Recovery runs the modified schema gate and saved-data analyzer; the original verifier independently recomputes bit/syndrome, deadline and CP statistics. Neither invokes receiver/optimizer. This is not an exhaustive unused-function audit of the repository. | `retry_failed_analysis.py:147-161`; `verify_prospective.py:1-25,184-211,442-538,551-803,920-946` |
| E. Scope | **WARN.** One simulated physical-channel population at each of three prespecified SNRs, 1,024 frames each; only 6.5 dB is confirmatory. No hardware or alternate-channel conclusion. | `protocol/PROTOCOL.md:18-30`; `FINAL_CSTATE_REPORT.md` |
| F. Evaluation type | **`simulation_only`.** Legitimate generated truth for a physical-channel simulation; not real hardware data. | `generate_population.py:182-240` |

**Claim impact:** The statement “the registered numerical 6.5 dB gate passes on the original sealed population” is supported **with the postfailure-recovery qualifier**. Descriptive 6 and 7 dB comparisons are supported within this simulation. “The original one-shot campaign completed cleanly” is unsupported. Zero observed harms in these 3,072 pairs must not be generalized to zero harm in all channels.

The reviewer checked [FINAL_CSTATE_REPORT.md](FINAL_CSTATE_REPORT.md) against the machine outputs and found no material numerical discrepancy. Its sole wording suggestion—replace “zero new frame errors” with “zero harms”—was applied before delivery. This audit is a targeted scientific-integrity review, not a replacement for the independent saved-artifact verifier.
