# PD1-Q Part A — qualification and attribution

**Part A complete:99/99 calls,0 new observations; qualification/recounts pass. Part B not started.** Only saved E1 observations are reused. Frozen primary remains `TF_J20_R2`, source `2d130b4d`, baseline `31d5ec0d`: 2 rounds × 20 joint iterations, damping .3, soft refit, LDPC cap50. No receiver tuning or new radio observation. Scope remains N1024, nominal P8, QPSK, LDPC2048/1024, pilot-power fraction rho=.5; SNR definitions and code identity are inherited unchanged from the frozen E1 inputs.

## Numerical qualification

Six prescribed size/path fixtures pass per-iteration state and LLR parity before interleaved timing (7 repeats, 20 iterations). Maximum absolute state/LLR difference is 5.20e−14 for four-FFT and 4.85e−12 for the independent dense CPP reference. Tolerances remain atol2e−9, rtol1e−8. Residual states are compared after the required AF/time unitary coordinate alignment.

| N | P | TF two-FFT (ms) | Four-FFT (ms) | Ratio |
|---:|---:|---:|---:|---:|
| 256 | 8 | 10.719 | 11.820 | 0.907 |
| 512 | 8 | 13.567 | 15.379 | 0.882 |
| 1024 | 8 | 19.052 | 23.670 | 0.805 |
| 2048 | 8 | 31.594 | 36.393 | 0.868 |
| 1024 | 4 | 16.948 | 20.173 | 0.840 |
| 1024 | 16 | 24.218 | 27.521 | 0.880 |

Dense is qualified/timed only at N256/P8: 41.877 ms versus TF 10.719 ms, with 44.240 ms dense-basis setup reported separately; retained dense basis 8,388,608 bytes. Other dense fixtures were not run. Kernel timings exclude radio acquisition/refit/decoding and are not complete receiver costs. The moderate two/four-FFT difference is an implementation detail, not the paper headline. First uncaptured calls follow parity qualification and are not cold-process latency.

The initial harness compared residuals in different domains and stopped. A later new-wrapper scoring defect treated packed truth as unpacked arrays. Both are documented in [qualification_incidents.md](qualification_incidents.md); numerical receiver source is unchanged. Original failed receipts are preserved.

## Evidence closure

E1 saved-output recount on deinlab passes 252 attempts / 504 checkpoints, zero new receiver calls (`e1_recount.json`). New attribution independently passes 91 attempts / 182 checkpoints, with info/coded errors and syndromes recounted from saved arrays (`independent_recount_report.json`). Isolated-memory recount also passes8 attempts /16 checkpoints, including bits, syndromes and decoder LLR accounting (`memory_recount.json`). Saved mechanism recount passes240 vector-derived rows and1920 scalar rows, with zero maximum mismatch for checked saved states. All recounts ran on deinlab saved arrays; returned compact files are not a claim of local raw-array recount. No publication-level statistical inference follows from reused observations.

## Attribution on reused observations

Final information-frame errors; each primary/POINT/FIXED cell uses the same first16 E1 observations. POINT first8 are reused E1 outputs; only missing first16 controls were executed.

| SNR (dB) | n | TF_J20_R2 | POINT | FIXED-inner |
|---:|---:|---:|---:|---:|
| 6.0 | 16 | 2 (155 bits) | 3 (214 bits) | 16 (1734 bits) |
| 6.5 | 16 | 1 (97 bits) | 1 (122 bits) | 13 (1294 bits) |
| 7.0 | 16 | 0 (0 bits) | 0 (0 bits) | 6 (435 bits) |

Each cell has 16,384 information bits. Switching FIXED→POINT rescues13/12/6 frames and harms0/0/0 at6/6.5/7dB. Switching POINT→TF rescues1/0/0 and harms0/0/0. Full coded/info counts are in [cells.csv](analysis/cells.csv) and [paired_counts.csv](analysis/paired_counts.csv); the latter defines rescues/harms relative to its comparison arm.

POINT–FIXED is the gain-mean intervention: FIXED also has zero propagated gain variance, still computes gain pseudo-variance, and retains outer refits. Large error differences here support the role of inner gain-mean adaptation on these saved frames; they are not a fresh-sample population claim. TF–POINT differs by only one frame at6dB and none at6.5/7dB: no demonstrated general propagated-variance reliability benefit, no promotion of POINT.

At6.5dB on the same first8 observations: TF1/8, NO-FEEDBACK5/8, NO-GEOMETRY8/8. Both scoped interventions worsen this subset. NO-FEEDBACK retains both decoder calls; this concerns availability of decoder feedback, not coding versus no coding. NO-GEOMETRY retains observed acquired path centers and gain adaptation, not oracle geometry.

Control latency is approximately0.29–0.30s median. POINT combines old and new execution batches; treat small timing differences cautiously. These controls establish attribution and are not a new TF–EP performance campaign.

## Isolated resources

Each arm runs in a fresh CPU process, same saved6.5dB/frame0, one warmup plus one measured call. Baseline is after imports/static context/input loading. Total high-water includes warmup, measurement and evidence instrumentation.

| Arm | Baseline RSS (KiB) | Total process peak (KiB) | Visible online NumPy subtotal, approximate (MB) |
|---|---:|---:|---:|
| TF | 594880 | 623296 | 8.45 |
| EP2 | 594868 | 623524 | 8.45 |
| EP4 | 594976 | 623588 | 8.45 |
| PBi | 595484 | 1148064 | 403.63 |

The visible NumPy subtotal is a deduplicated lower bound sampled at selected function returns. It excludes hidden native/BLAS/Torch workspace and unsampled temporaries. It is not total live allocation. Instrumented probe latency is excluded from ordinary latency statistics. TF and EP have similar observed process peaks here; the dense PBi adaptation uses substantially more memory on this audit frame.

## Cost and provenance

Actual99 calls =3 primary replays +24 missing POINT +48 FIXED +8 NO-FEEDBACK +8 NO-GEOMETRY +8 isolated-memory warmup/measured. New radio observations:0. Offline repair reuses the original3 replay calls; duplicate identity records are not additional calls. Complete attribution receiver time sums26.893s; instrumented memory calls sum34.633s. These are receiver-call costs, not whole-session elapsed time; kernel, setup, offline recount, storage and failed harness work have separate launch receipts.

Primary source2d130b4d, baseline31d5ec0d; runner scoring repaird1fd9d4f; mechanism recount2311922f. Three replay outputs match prior E1 decoded bits/LLRs/path values. See [master equations](master_equation_reconciliation.md), [baseline equation/cost map](baseline_equation_map.md), [claims and limits](claims_and_limits.md), [allocation lock](analysis/allocation_lock.json), [latency stages](analysis/latency_stage_summary.csv), [isolated memory](analysis/isolated_memory.csv), and [kernel fixtures](kernel_v2/kernel_scaling.csv). Hardware/runtime and exact hashes are recorded in the execution manifests; comparator names denote local proper-complex coded/SP adaptations, not original authors' software.

## Saved-trace mechanism closure

Predeclared frame0 at each SNR, TF and POINT, both coded rounds:240 vector-derived iteration rows. Existing first8 paired scalar traces:1920 rows. These are re-derived from saved arrays, with no receiver calls. The extended table records pre/post variances, precisions, raw/damped output variances, direct-term norms and gain movement; remote audit vectors retain x/h_pre and barred means. Both round resets and pre/post alignment pass. No precision floor fires in this audit subset.

Late-iteration summary (t5–19, both rounds pooled; percentages are medians of per-iteration ratios):

| SNR | TF median N·vh_post | Output correction | Actual reaction / backprojection | TF gain movement | POINT gain movement |
|---:|---:|---:|---:|---:|---:|
| 6.0 | 0.710 | 1.204% | 0.824% | 0.735% | 0.233% |
| 6.5 | 0.640 | 1.178% | 0.767% | 0.830% | 0.357% |
| 7.0 | 0.567 | 1.185% | 0.756% | 0.576% | 0.419% |

These late coefficients are consistent with the stated fixed-P scaling at this single N1024/P8 operating point, but do not estimate an empirical asymptotic exponent. At each round reset vh_pre=1/P=.125: initial output correction spans196%–467%, so gain-variance effects are not uniformly small. POINT's explicit variance terms are zero while gain means still move. The POINT–FIXED control supplies the causal evidence for gain adaptation; the saved trajectories alone do not.

[Mechanism definitions](mechanism_definitions.md), [compact summary](analysis/mechanism_summary.csv), [all240 extended rows](mechanism_extension/extended_audit_metrics.csv), [36 per-round/period summaries](mechanism_extension/mechanism_extension_summary.csv), and [recount/provenance receipt](mechanism_extension/receipt.json) retain the detailed conventions. Compact summary is a direct grouped median/min/max of extended rows, selected prospectively by iteration index rather than outcome.

## Retention and closure

Remote evidence root: `/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_a_20260921/`. Inventory snapshot:591 files,52,037,892 bytes (49.63MiB), excluding cache/temp and inventory self-files. The13,379,079-byte mechanism vector NPZ stays remotely retained; its exact path/hash and all saved input/checkpoint/attempt hashes are in [remote_inventory.json](remote_inventory.json). [Transfer verification](transfer_check.json) passes for145 returned compact files. [Input manifest](analysis/input_manifest.json) binds48 reused observations; [source/environment/code/input manifest](analysis/source_environment_code_input_manifest.json) fixes identities and execution scope.

[Full attempt ledger](analysis/full_attempt_ledger.jsonl) contains99 successful numerical calls. [Failure ledger](analysis/failure_fallback_ledger.jsonl) separately preserves the initial coordinate-comparison and packed-truth scoring failures; those do not become extra receiver calls or disappear from provenance. No numerical receiver failures occurred. All owned Part-A processes exited; no background continuation or Part B job remains. Raw-array recount was remote; local work checked compact-file hashes and derived the displayed summary table.

## Part-A verdict

**Qualification and attribution support retaining the frozen TF primary for review.** The permitted mechanism wording is inner gain-mean adaptation plus coded feedback and geometry updates under this scoped experiment. A general reliability benefit from propagated gain variance is not established. Kernel FFT count is not the headline. The prior E1 complete-cost comparison remains a direction-validation result, not submission-level confirmation.

No receiver module, damping, iteration count, prior or primary selection changed. **Stop here: Part B, fresh confirmation and scope extensions were not started.**
