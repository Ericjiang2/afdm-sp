# F2 five-policy developmental comparison

**Primary offline result: PASS, with an analysis-only recovery qualification.** The
registered five-policy receiver campaign completed all 1,024 existing 6.5-dB
observations: 2,048 shared-prefix calls, 120 original-F0-triggered continuations,
2,168 paid calls total, and 5,120 logical policy rows. There were no receiver
failures. The first frozen reader exited 1 because it expected `stream_ids` in a
prefix ledger row where the saved schema has no such field. Its log and exit
receipt remain unchanged. The separately hashed [v2 reader](../../experiments/cstate_necessity_stageB_resume_20260928/analyze_method_closure_five_v2.py)
validated the [erratum](F2_FIVE_ANALYSIS_ERRATUM.json), registered source maps,
observed Git attestation, all sealed observed files and the truth seal before
scoring. It passed without another receiver call. The subsequent authorized independent timing-schema recovery completed raw/checkpoint-to-truth recount: **173 comparison fields exactly equal, zero nonzero differences**. See the [successful receipt](independent/recount_schema_recovery_v2/receipt.json) and [exact comparison](independent/recount_schema_recovery_v2/F2_FIVE_PRIMARY_EXACT_COMPARISON.json). The [previous failed independent attempt](independent/failed_recount_v1/attempt2/attempt_receipt.json) remains unchanged.

| Policy | Information errors / 1024 | FER | Coded errors / 2,097,152 | BER | Syndrome nonzero | Full median / mean / p95 / p99 / max (s) | Correct by 0.5 s / 1 s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| F0 | 40 | 0.039063 | 9,579 | 0.004568 | 40 | 0.352 / 0.354 / 0.407 / 0.437 / 0.494 | 984 / 984 |
| B (F0+CSTATE) | 6 | 0.005859 | 1,362 | 0.000649 | 6 | 0.354 / 0.365 / 0.426 / 0.676 / 0.733 | 986 / 1,018 |
| F0_LOCAL | 29 | 0.028320 | 7,680 | 0.003662 | 29 | 0.354 / 0.363 / 0.426 / 0.611 / 0.737 | 987 / 995 |
| F2T | 39 | 0.038086 | 11,293 | 0.005385 | 39 | 0.354 / 0.987 / 0.426 / 18.189 / 21.509 | 984 / 984 |
| F2E | 1,021 | 0.997070 | 422,368 | 0.201401 | 1,021 | 15.660 / 15.631 / 18.093 / 19.344 / 22.058 | 0 / 0 |

FER is the information-error count divided by 1,024; BER is the coded-error
count divided by 2,097,152. All five policies had zero valid-but-wrong final
words. At 0.5 and 1 s, F2E had no ready durable checkpoint on any frame;
the other policies had a ready checkpoint on all frames. The final-FER versus
mean-complete-latency frontier within this cohort is **F0 → F0_LOCAL → B**:
the mean rises from 0.354 to 0.363 to 0.365 s as information errors fall
from 40 to 29 to 6. F2T and F2E are dominated on these two metrics. The
deadline comparison differs: at **0.5 s LOCAL has 987 correct versus B's
986**, while at **1 s B has 1,018 versus LOCAL's 995**. The earlier F1
campaign has a different clock and must not be pooled with these seconds.

The table below gives all ten full-population paired final-decision comparisons.
“Left only” and “right only” count frames correct only for that policy. The
exact two-sided McNemar values describe this exposed developmental cohort.

| Left | Right | Left only | Right only | Both wrong | Exact p |
| --- | --- | ---: | ---: | ---: | ---: |
| B | F0 | 34 | 0 | 6 | 1.16e-10 |
| B | F0_LOCAL | 23 | 0 | 6 | 2.38e-7 |
| B | F2T | 33 | 0 | 6 | 2.33e-10 |
| B | F2E | 1,015 | 0 | 6 | 5.70e-306 |
| F0 | F0_LOCAL | 0 | 11 | 29 | 9.77e-4 |
| F0 | F2T | 0 | 1 | 39 | 1.0 |
| F0 | F2E | 981 | 0 | 40 | 9.79e-296 |
| F0_LOCAL | F2T | 11 | 1 | 28 | 6.35e-3 |
| F0_LOCAL | F2E | 992 | 0 | 29 | 4.78e-299 |
| F2E | F2T | 0 | 982 | 39 | 4.89e-296 |

On the **original F0-triggered 40** only, B leaves 6 errors, LOCAL 29 and
F2T 39. Relative to F0, these are 34, 11 and 1 rescues with zero harms.
Conditional branch complete means on those 40 are 0.273 s (B), 0.219 s
(LOCAL), and 16.192 s (F2T); their 40-frame full-clock means are 0.640,
0.586 and 16.559 s. The [subgroup table](population_five_subgroup_v2.json)
contains their paired outcomes and deadline counts. F2E is nonzero-syndrome on
1,021 frames, but F2E+LOCAL and F2E+CSTATE were excluded for the entire cohort
as `not_admitted_frozen_interface`; their trigger-subgroup comparisons are
**unavailable**, not zero harm or substituted prefix outcomes.

The [component timing CSV](population_five_analysis_v2/component_timing.csv)
retains every call's non-overlapping input, receiver and post-receiver clocks,
including durable checkpoint, raw and decision serialization. Mean F0 prefix
components are 0.013842 s input, 0.307094 s receiver and 0.033392 s
post-receiver. Mean F2E prefix components are 0.014033, 15.585180 and
0.031458 s. The F2E receiver clock includes all 155-slot estimation, TF/refit,
decoder and checkpoints; its saved front-stage fields are nested and must not
be added to the receiver time again. The saved F2E prefix front fields include
grid, matrix, dense-H, LMMSE, posterior and other stages; F2T has corresponding
front fields on its triggered branch. B and LOCAL retain nested branch TF and
LDPC stage fields. **Independent prefix TF and decoder durations were not
separately recorded** in the primary component table for F0 or F2E, nor are
independent F2T branch TF/decoder durations available there. Their work is
inside the respective complete receiver clock; that total cannot be reported
as either missing substage. Population-averaged added branch complete
costs are 0.010662 s (B), 0.008545 s (LOCAL) and 0.632509 s (F2T), with
non-triggered frames charged zero branch cost. The F2T full-clock p95 stays
near F0 because exactly 40/1,024 frames execute its expensive branch; its
p99 and maximum expose that cost.

The [paid-call memory ledger](population_five_analysis_v2/paid_call_memory.csv)
has 2,168 monotone `RUSAGE_SELF` entries. Campaign high-water RSS was
**744,528 KiB**. This is a shared-process cumulative peak including F2E's
downstream work and retained shared state, not an independent peak for any
policy; no memory ranking between policies is supported.

Primary evidence is [report.json](population_five_analysis_v2/report.json),
[frame outcomes](population_five_analysis_v2/frame_outcomes.csv),
[deadline decisions](population_five_analysis_v2/deadline_decisions.csv), and
the [full observed-file inventory](population_five_analysis_v2/observed_file_inventory.json).
The original seven-policy attempt remains `invalid_partial` after 19 attempts;
none of its outputs entered these denominators. No new observation, receiver
call, method change, or F1 rerun occurred in this analysis recovery.
