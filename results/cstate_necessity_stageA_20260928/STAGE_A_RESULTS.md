# Stage A saved-output results

This is a **developmental comparison on the existing 6.5 dB, 1,024-frame population**, not fresh confirmation. The [observed seal](observed/observed_seal.json) is Git-committed at `7f670af0359256c5152197a6bd675ff0d8dc16c5`; the [offline analysis](analysis/report.json) and its [receipt](analysis/analysis_receipt.json) are committed at `c829c89e`. The [execution receipt](PRODUCTION_EXECUTION_RECEIPT.json) records 4,096 A–D plus 12 E complete wrappers, zero failed calls. Numbers below come from the frozen [report](analysis/report.json) and [four saved tables](analysis/frame_outcomes.csv); the other tables are [timing](analysis/component_timing.csv), [structure](analysis/structural_diagnostics.csv), and [deadline decisions](analysis/deadline_decisions.csv). The [independent saved-output recount](independent/recount.json) passed; [comparison and coverage](independent/COMPARISON.json) distinguish independently matching endpoints from metrics not independently recomputed. Coded BER and the34-frame direction addendum are primary-analysis results, not additional independently recounted endpoints. Historical A/B array parity was checked during production; the independent reader verifies its sealed links without reloading the historical array payloads.

| Arm | Information errors / FER, n=1,024 | Coded bit errors / BER | Branch triggers | Valid but wrong |
| --- | ---: | ---: | ---: | ---: |
| A: F0+TF | 40 / 3.906% | 9,579 / 0.4568% | 0 | 0 |
| B: F0+TF+CSTATE | 6 / 0.586% | 1,362 / 0.0649% | 40 | 0 |
| C: F1+TF | 12 / 1.172% | 1,695 / 0.0808% | 0 | 0 |
| D: F1+TF+CSTATE | 0 / 0% | 0 / 0% | 12 | 0 |

Nonzero **native** syndrome counts are40 for each A/B prefix and12 for each C/D prefix. A and C have zero branch executions because continuation is disabled, not because their native syndromes all pass. The12 E calls cover every C trigger.

All six paired tables use the same 1,024 frames. Cells are **both correct / left only correct / right only correct / both wrong**. Signed Δ is `FER_left − FER_right` in percentage points, so a positive value favors the right arm; `upper95` is the conservative bound constructed from the two preregistered Clopper–Pearson components, and `p` is two-sided exact McNemar. These are unadjusted developmental contrasts, not a family-wide confirmatory claim.

| Pair | Four cells | Δ (pp) | upper95 (pp) | p |
| --- | ---: | ---: | ---: | ---: |
| A vs B | 984 / 0 / 34 / 6 | +3.320 | +4.609 | 1.16e−10 |
| A vs C | 982 / 2 / 30 / 10 | +2.734 | +4.132 | 2.46e−7 |
| A vs D | 984 / 0 / 40 / 0 | +3.906 | +5.281 | 1.82e−12 |
| B vs C | 1008 / 10 / 4 / 2 | −0.586 | +0.528 | 0.180 |
| B vs D | 1018 / 0 / 6 / 0 | +0.586 | +1.271 | 0.0313 |
| C vs D | 1012 / 0 / 12 / 0 | +1.172 | +2.038 | 0.000488 |

E is a **matched LOCAL control only on the 12 C-triggered frames**, not a fifth population arm: D was correct in 12/12, E in 11/12 (11 both correct, one D-only correct; exact McNemar `p=1`). C absorbs 26 of the historical 34 B-only rescues. These are saved outcomes; the separate decision packet adjudicates K/S/C/E/U.

The [34-frame structural addendum](analysis/structural_addendum.json) binds all64 accepted historical rescue edits (one of34 rescued frames had no accepted edit) to saved F1 initial, entering, native-final and post-CSTATE geometries. The historical target delay is present for51/64 edits before CSTATE and55/64 afterward. Nearest same-delay Doppler distance and slot multiplicity are descriptive, not physical-capture or causal criteria. Saved-slot absolute-gain ordering is not the original candidate-bank score rank; APP path rank was not saved and is explicitly NA. Full-population geometries remain in the per-frame raw bound by the seal. The independent recount finds96/1024 F1 frames with preserved same-delay multiplicity; D accepts19 edits,11 to delays absent on entry and8 already present. Seven edits change Doppler within the same delay; these categories describe geometry and are not causal rescue shares.

Complete-wrapper latency includes durable checkpoints, raw and decision serialization; ledger append is excluded. All times are seconds, measured in the same single-CPU process. E has `n=12`; A–D each have `n=1,024`.

| Arm | Mean | Median | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 0.349 | 0.345 | 0.396 | 0.427 | 0.451 |
| B | 0.363 | 0.350 | 0.436 | 0.600 | 0.697 |
| C | 0.668 | 0.660 | 0.736 | 0.800 | 0.857 |
| D | 0.668 | 0.660 | 0.744 | 0.869 | 1.081 |
| E | 0.849 | 0.839 | 0.918 | 0.928 | 0.930 |

On the same12 C-triggered observations, complete means are C0.6839 s, D0.9191 s and E0.8490 s: D costs0.0701 s more than LOCAL on that matched subset. This conditional comparison does not replace the all1024-frame cost table; the tiny all-frame D−C mean difference must not be read as zero branch cost.

Deadline cells are **correct / ready but wrong / missing** using the latest durable checkpoint at each deadline. A–D denominators remain 1,024; E's denominator is only 12.

| Arm | 0.5 s | 1.0 s |
| --- | ---: | ---: |
| A | 984 / 40 / 0 | 984 / 40 / 0 |
| B | 994 / 30 / 0 | 1018 / 6 / 0 |
| C | 307 / 118 / 599 | 1012 / 12 / 0 |
| D | 382 / 126 / 516 | 1023 / 1 / 0 |
| E, n=12 | 0 / 3 / 9 | 11 / 1 / 0 |

Mean component seconds, retained as separately measured fields; nested work and residual overhead mean these columns should **not** be summed into complete latency:

| Arm | Acquisition | Refit | TF | Decoder | Branch | Raw serialize | Decision record |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | .083 | .098 | .039 | .038 | 0 | .023 | .012 |
| B | .086 | .098 | .039 | .039 | .007 | .024 | .012 |
| C | .377 | .115 | .040 | .039 | 0 | .023 | .011 |
| D | .374 | .115 | .040 | .038 | .002 | .024 | .011 |
| E | .377 | .111 | .039 | .053 | .156 | .035 | .012 |

Durable checkpoint/decoder counts are A 2,048, B 2,088, C 2,048, D 2,060, E 36 (total 8,280). The process-wide maximum `ru_maxrss` after a wrapper was 758,112 KiB (about 740 MiB); this cumulative process peak is **not** an arm-specific allocation. One-time source/context preparation was 3.206 s in the [manifest](observed/manifest.json), outside the per-wrapper clock (0.780 ms per call if evenly amortized across4108 calls). Sum of complete-wrapper clocks was2106.900 s; launcher-to-exit wall time was2226.845 s (37.11 min), including additional setup, bookkeeping and sealing. The immutable manifest's `status=running` is its creation snapshot; the final seal and exit receipt establish completion.

F1 acquisition averaged .377 s in C versus .083 s for F0 in A (about **4.54×**); complete C versus B averaged about **1.84×**. The [frozen complexity ledger](../cstate_necessity_audit_20260925/F1_COMPLEXITY_LEDGER.md) distinguishes F0's actual **24 × 515 = 12,360** maximum greedy correlation products from F1's measured **8 × 2,575 = 20,600** bank scores and 80 coordinate visits per full-slot wrapper. The 5/3 score-count ratio is not a runtime ratio; comparing to an unexecuted 40-nomination F0 budget would be wrong. All observed F1 C/D runs reached eight slots; [structure rows](analysis/structural_diagnostics.csv) retain same-delay multiplicity and accepted edits. Physical-capture sufficiency remains **unknown** because no threshold was frozen. The [raw inventory](raw_hash_inventory.json) binds all 4,108 raw SHA-256 and MD5 values to the observed seal; large raw and checkpoints remain on the remote host.
