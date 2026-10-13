# CGR mechanism diagnostic: fixed 25-observation, four-arm continuation

The frozen CGR arm recovered four of eight designated BASE failures with no loss of a BASE-correct observation. Its aligned gain reaction beat SHAM and BLOCK on these targets. The five fixed engineering gates nevertheless finish **4/5, candidate does not pass**: the complete physical-direction trace is inconclusive. This outcome supports a bounded paired decision effect, not confirmation of the proposed coherence mechanism or a representative frame-error rate.

## Provenance and call accounting

The 25 observations and four arms were fixed by the supplied [protocol](../../_archive/20260923_tf_cgr_investigation/CODEX_TEST.md) and canonical witness manifest before the run. Every arm used its own two-round native prefix and the same post-refit entering state; BASE kept the frozen final TF20, CGR changed only the gain reaction to physical R·hbar, SHAM changed only that reaction's phase alignment, and BLOCK used the qualified full Gaussian gain block. Inputs and receiver configuration were unchanged. The observed run used single-thread CPU execution on deinlab and passed 95 remote synthetic numerical checks, eight synthetic payload round trips through the real evidence serializer, focused wrapper tests, and a clean 115-source-file / 25-witness preflight.

The original frozen producer had one failed BASE attempt: three checkpoints were saved before a raw-artifact metadata-key serialization error, after 0.514756875 s; no raw artifact, decision, or complete wrapper exists for that attempt. It remains immutable. The separately approved v2 repair converted those metadata keys to strings. V2 executed once, 2026-09-23 11:58:53–11:59:53 UTC, and exited 0 with **100/100 complete wrappers** (25 per arm), no numerical failures, 100 raw artifacts, 100 decisions and 272 checkpoints. The total is **101 attempted calls across both runs**, while every paired table below has the 25-observation, 100-complete-wrapper v2 denominator.

The v2 [observed seal](observed/observed_seal.json) (`42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43`) was committed as `dc228d7254274f3be3403514fc75f0758aacc15c` before truth-dependent analysis. Its 474-file, 152,200,556-byte inventory passed remote and local full rehash. The source binding, registration, ledger and transfer details are in [the observed-only receipt](observed_transfer_receipt.json). The analyzer used the committed Git seal object, source-bound H/G/free_cols, and the separately tagged truth payloads only after that commit. No production receiver was called during analysis. The initial offline reader used synthetic `c1/c2` values in its physical diagnostics. The corrected [r2 reader](../../experiments/tf_cgr_mechanism_20260923/analyze_r2.py) derives both from five hash-bound frozen context sources. The original six analysis files remain unchanged; the [impact receipt](analysis_r2/parameter_impact.json) compares them with r2. Decisions, deadlines, physical traces, working moments and gates are unchanged; projection differences are at most 1.60e-12 in a subtraction diagnostic and 5.33e-15 in the fitted physical residual.

## Exact paired outcomes

| Arm | Correct, all 25 | Correct, eight target BASE failures | Rescues vs BASE | Harms vs BASE | Valid-but-wrong |
| --- | ---: | ---: | ---: | ---: | ---: |
| BASE | 14 | 0 | 0 | 0 | 0 |
| CGR | 18 | 4 | 4 | 0 | 0 |
| SHAM | 11 | 0 | 0 | 3 | 0 |
| BLOCK | 7 | 0 | 0 | 7 | 0 |

CGR rescued `s650_f0390`, `s650_f0720`, `s600_f0600`, and `s700_f0732`. The seven already-rescued controls and seven easy controls had no CGR loss. SHAM lost three BASE-correct controls; BLOCK lost seven. These are exact information-bit decisions using the actual free-column mapping, with coded errors and syndrome counts retained per call in [decisions.json](analysis_r2/decisions.json).

All pairwise 2×2 overlaps are shown below. “Left only” and “right only” mean correct for that arm alone; each row sums to 25.

| Left / right | Both correct | Left only | Right only | Neither correct |
| --- | ---: | ---: | ---: | ---: |
| BASE / CGR | 14 | 0 | 4 | 7 |
| BASE / SHAM | 11 | 3 | 0 | 11 |
| BASE / BLOCK | 7 | 7 | 0 | 11 |
| CGR / SHAM | 11 | 7 | 0 | 7 |
| CGR / BLOCK | 7 | 11 | 0 | 7 |
| SHAM / BLOCK | 7 | 4 | 0 | 14 |

All four new native-prefix arrays and the post-refit entering-state hash matched within each observation. The analyzer also checked r0/r1 decoded bits against the cold historical TF traces and final BASE decoded bits against the historical TF/CSTATE result for all **25/25** observations. Historical LLR parity was not separately checked, so this is a bits-level parity statement. On all three designated triggered distinct-delay controls, CGR and SHAM final-batch detector fields had maximum absolute difference zero from BASE and final bits matched.

## Measured cost and deadlines

All times below come from this v2 run with identical instrumentation. Branch times include the completed added branch and serialization cost, including any charged failure work. Historical campaign timing is excluded.

| Arm | Complete mean / p95 / max (s), n=25 | Triggered branch mean / p95 / max (s), n=18 |
| --- | ---: | ---: |
| BASE | .523 / .654 / .717 | .299 / .352 / .371 |
| CGR | .520 / .672 / .677 | .298 / .366 / .384 |
| SHAM | .514 / .662 / .673 | .293 / .352 / .357 |
| BLOCK | .609 / .799 / .830 | .419 / .490 / .510 |

Earlier ready checkpoints remain eligible even when the complete wrapper finishes later. Each deadline cell is **correct / wrong but ready / missing**, always with denominator 25. The full 200 arm×frame×deadline records and ready clocks are in [deadline.json](analysis_r2/deadline.json).

| Deadline | BASE | CGR | SHAM | BLOCK |
| --- | ---: | ---: | ---: | ---: |
| 0.5 s | 13 / 12 / 0 | 17 / 8 / 0 | 11 / 14 / 0 | 7 / 18 / 0 |
| 1.0 s | 14 / 11 / 0 | 18 / 7 / 0 | 11 / 14 / 0 | 7 / 18 / 0 |

## Physical diagnosis and the fixed gates

For the four CGR rescues, terminal CGR physical mismatch was lower than terminal BASE mismatch on each frame. Yet the predicted BASE common-state correction did not point uniformly toward truth throughout the saved 20-step trajectories. Its signed physical effect, defined as mismatch before minus mismatch after that one-step correction, had both signs on every rescued frame:

| Rescued frame | Negative / positive BASE iterations | Sum of signed effects | Terminal BASE minus CGR mismatch |
| --- | ---: | ---: | ---: |
| s650_f0390 | 7 / 13 | −816.02 | +52.35 |
| s650_f0720 | 6 / 14 | −286.44 | +64.25 |
| s600_f0600 | 5 / 15 | −114.14 | +42.91 |
| s700_f0732 | 8 / 12 | −602.90 | +96.77 |

These one-step signed-effect sums are evaluated at different BASE states; they are descriptive, not the cumulative causal change along the actual CGR trajectory. The full 1,440 arm×iteration mismatch records, signed effects and dhᴴRdh values are in [physical_trace.json](analysis_r2/physical_trace.json). The 72 selected-geometry projections in [projection.json](analysis_r2/projection.json) use actual same-delay N×P physical modulation columns and retain singular values, ranks, Gram diagnostics and coefficient sensitivity. No selected fit was rank deficient in this run. The 640 target arm×iteration [working-moment diagnostics](analysis_r2/working_moments.json) compare same-delay Γ entries against N·vx·R; maximum absolute error was 3.14e-11, with norm ratios effectively one. Physical operator Gram R, waveform-response Gram BᴴB and working Γ are separately saved in the raw evidence.

| Fixed continuation gate | Result |
| --- | --- |
| At least two target rescues; zero rescued-control harm and no new valid-but-wrong | Pass: 4 rescues, 0 harm, 0 new valid-but-wrong |
| Distinct-delay CGR/SHAM numerical and final-bit identity | Pass: all three controls, maximum detector difference 0 |
| CGR exceeds SHAM by at least one target **and** physical-direction support | **Not established**: 4 versus 0 target wins, but mixed signed trajectories make directional support inconclusive |
| CGR added-branch mean ≤1.10× BASE | Pass: .298 versus .299 s |
| BLOCK has fewer than two additional net target wins over CGR | Pass: BLOCK 0 versus CGR 4 |

The corrected [machine report](analysis_r2/report.json) records `candidate_pass=false` (4/5 gates). Its all-iterations-nonnegative directional pattern was a conservative sufficient interpretation written before truth was read; **CODEX_TEST.md did not pre-register that numeric sign threshold**. Independent review of the complete signed traces also judged support **inconclusive**, not a disproof of physical coherence. The target cohort was selected by prior outcomes, so these counts are a bounded mechanism diagnostic, not a population FER estimate. The failed gate stops this candidate configuration under the supplied protocol; it does not authorize retuning, extra calls, a new frame selection, or a broader research claim.

Luna's independent [truth recount](../tf_cgr_mechanism_20260923/independent/v2_truth_recount_receipt.json) checked 25 bound truth payloads, all 100 decisions, all 200 deadline rows and all six pairwise overlaps with zero mismatch. It did not validate the separate physical diagnostic. The parent Trellis task remains in progress.
