# PD1-Q: manuscript qualification and publication-evidence specification

## Objective and immutable boundary

Turn Paper Design v1 into manuscript-quality evidence. This is not a new direction search. Preserve `TF_J20_R2`, receiver `2d130b4d`, baseline `31d5ec0d`, its two rounds / twenty joint iterations / damping .3 / soft physical refit / LDPC cap50. Do not promote POINT or change numerical guards, priors, geometry budgets or schedules.

Keep E1 direction validation and its no-new-call mechanism audit separate from this ticket. Original raw root: `/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_native_direction_20260921/`. Verify current paths/source hashes rather than assuming archive or branch equivalence. No truth reaches an online receiver.

The immediately useful next execution is **Part A** below. Part B is a frozen prospective submission-study specification, not a request to start it automatically after any favorable Part-A number. It requires its own resource authorization. No background job has been created by the blueprint.

## Part A — source, attribution and resource closure; reuse existing observations

1. Recount the current E1 ledgers and diagnostic tables from saved arrays. Preserve exact pre/post iteration conventions, actual denominator definitions of the output-correction and reaction percentages, both coded-round reset points, and source identifiers. Do not infer figure curves from three tabulated medians.
2. Reconcile the master equations with the *executed* implementation. Specifically verify barred-mean order, scalar precision/output damping, pre/post `v_h`, numerical floors, prior `I/P`, actual decoder inputs, APP/check separation, and model-change state reset. Verify the refit lambda and its different role from the inner prior; no common-ELBO claim.
3. Add isolated control wrappers, not modifications to the primary:
   - **POINT:** existing propagated-variance-zero control, all gain-mean/pseudo-variance computations retained.
   - **FIXED-inner:** identical to POINT, except gain means are frozen within each joint batch; the existing outer refit schedule remains unchanged. POINT versus FIXED, not TF versus FIXED, is the clean gain-update intervention.
   - **NO-FEEDBACK (small only):** keep both decoder calls for cost, but do not use decoder output as a prior or CE feedback. Pass the detector's APP moments to the next CE. This isolates code-feedback availability, not coding itself.
   - **NO-GEOMETRY-UPDATE (small only):** retain the observed acquired delays and Doppler centers across the two rounds, permitting the same gain updates and decoding. Charge all actual work; this is a scoped component control, not a new baseline family.
4. Reuse the first16 E1 inputs in each cell for POINT/FIXED. POINT already exists on the first8: run only the missing24 POINT calls and all48 FIXED calls. Add NO-FEEDBACK on first8 at6.5dB and NO-GEOMETRY-UPDATE on those same8. Primary replay on the predeclared frame0 in each cell:3 calls. No new radio observations are required.
5. Same-map qualification/benchmark: compare dense reference at small N, competent four-FFT scalar realization, and tensor-free realization. Require matching scalar states/LLRs before interpreting timing. Core fixtures: N=256,512,1024,2048 atP=8, andP=4,16 atN=1024. Dense tensor cases may be limited to feasible sizes and must be labeled as such. Repeat kernel timing in interleaved order; do not make extra FFTs the expected headline.
6. Fresh-process memory: TF, EP2, EP4, PBi on the same saved6.5dB frame0, one warmup and one measured call each. Report baseline process, peak total process, and explicit allocated online arrays separately. Shared high-water memory is not a per-arm statistic.

The above receiver-call allocation is **at most99 calls**:3 replays +24 POINT +48 FIXED +8 feedback +8 geometry +8 warmup/measured memory calls. Numerical/kernel tests are separate and are not Monte Carlo samples. Reuse any already available identical valid controls instead of repeating them.

### Part-A interpretation

This closes attribution/resource documentation. Do not select a new primary. A POINT/FIXED null requires cautious mechanism wording, not retuning. A newly discovered mathematical or implementation defect stops the next scientific campaign; save its minimal reproduction and explain affected evidence. Lack of demonstrated POINT benefit does not invalidate the frozen TF primary.

Return the exact baseline mapping (published formula -> implemented approximation -> coded/SP change -> cost) and identify any hidden uncharged work. Do not label the proper-complex coded EP/PBi adaptations as the authors' released implementation unless that is true.

## Part B — prospective submission study; separate authorization required

### Primary frozen configurations

TF_J20_R2; EP2_MEAN_R2; EP4_MEAN_R2. All receive observed-only native initialization and the same qualified refit implementation where applicable. No I1 warm-up is imposed on native controls.

### Allocation

- 1024 fresh independent frames at each of6,6.5,7dB, paired across all3 primary configurations:9216 calls on3072 independent observations.
- POINT on the first128 per cell; PBi on the first32 per cell. These subsets are selected by index, not outcomes.
- Part-A controls need not be repeated at full scale.
- New deterministic seed namespace independent of E1 and all development; record it before generation. One namespace proposal is941001, subject to an audit that it has not been used. Do not silently choose a colliding or recycled namespace.

This is a precision allocation, not a guarantee of statistical power. Do not extend after seeing outcomes. Report inconclusive intervals as inconclusive; a separately designed follow-up may be considered later, not automatically launched.

### Primary estimands and inference

Let `H` be TF-wrong/comparator-correct, `R` comparator-wrong/TF-correct, and `n` the paired frames. Estimate

`Delta = FER_TF - FER_comparator = (H-R)/n`.

For six comparisons (2 comparators x3 SNRs), a conservative simultaneous one-sided95% upper bound is

`U_CP(H;n,1-alpha/12) - L_CP(R;n,alpha/12)`, with `alpha=.05`.

Use exact binomial endpoints including zero/all events; no normal approximation or zero-width bound for zero discordance. Primary practical tolerances:0.02 at6/6.5dB and0.01 at7dB. Do not call these IEEE requirements or statistical equivalence. If superiority is additionally tested, specify and multiplicity-adjust it prospectively rather than converting the most favorable cell after the fact.

Latency: report complete median and p90/p95, ratios of medians, distributions of paired ratios, and serial batch/block-resampled intervals. Primary practical speed target is an upper95% median-ratio bound below0.8 and p90 ratio no greater than1 versus EP2 in the stated primary regime. Retain EP4 as the stronger-accuracy frontier, not a control to remove after a favorable EP2 comparison. Record all setup, refit trials, inner iterations, decoder calls, failed work and completed-checkpoint hooks.

Unrestricted final FER and deadline FER are distinct. For display, use deadline fractions{.6,.8,1,1.5,2} of each cell's **pre-existing E1 EP2 median** on the same machine; on different hardware, fix a timing-only calibration from saved frames before fresh generation. Do not choose a deadline from final error outcomes. If no valid decision exists by a deadline, count a deadline failure. Truth scoring/storage are outside receiver time but are logged.

### Small scope extension, only if authorized

64 new paired frames each for a second valid code/interleaver, rho=.25, and a predeclared unresolved/missed-delay adverse case, TF/EP2/EP4 without tuning. Keep exact code rate, total/data-power and SNR units visible. Scope-generalization implementation changes are qualified and hashed separately; a wrapper hardcoded to N1024/rho.5 is not quietly bypassed. These are bounded illustrations, not broad robustness guarantees.

## Evidence to return

Return compact master files: `RESULTS.md`, `claims_and_limits.md`, `cells.csv`, `paired_counts.csv`, `latency_stage_summary.csv`, `kernel_scaling.csv`, `isolated_memory.csv`, `mechanism_definitions.md`, `mechanism_summary.csv`, `baseline_equation_map.md`, source/environment/code/input manifests, allocation lock, full attempt ledger, failure/fallback ledger, and independent recount report.

Per frame/arm retain decoded information/code bits, actual decoder input/APP/check LLRs per checkpoint, completion timestamps, path parameters after acquisition/refit/joint update, iteration/call counts, scalar variance traces, and stage timings. Save each input observation and physical truth once, in separate receiver-access and offline-scoring locations. Heavy vector states only on predeclared audit frames and numerical exceptions. Ordinary decoding errors alone must not trigger outcome-dependent data collection.

For mechanism audit save `x/h` pre-update, barred means, `v_x` pre-update, propagated `v_h` pre-update, posterior `v_h`, `alpha/v_q/v_r`, raw and damped output variances, direct reaction vectors or their explicitly defined norms, and post-update gain movement. Preserve both coded-round resets. Do not reconstruct pre-update fields from a mislabeled post-update column.

All attempts, including numerical failures and missing checkpoints, must appear. Return hashes plus remote inventory for retained heavy arrays; do not claim locally recounted quantities that were only producer-scored remotely. Keep previous evidence stages separate and explicitly mark reuse versus fresh data.

## Falsification / stop conditions

Stop scientific execution on a qualification defect, information leakage, source/seed conflict, or unfair baseline/cost boundary. Save partial results and diagnosis.

For the scientific claim: no robust complete-cost advantage against competent EP, unacceptable primary reliability loss, or dependence on oracle geometry prevents the planned headline. A smaller claim may remain, but no new receiver module or tuning campaign is automatically authorized. POINT matching TF means no propagated-variance reliability claim; FIXED matching POINT means no demonstrated gain-update causal advantage; equal two/four-FFT cost means no FFT-count headline.
