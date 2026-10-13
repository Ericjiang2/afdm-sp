# Five-policy source review — before population execution

Scope: the new five-policy producer, launcher, offline reader, subgroup helper and focused synthetic tests. This review uses the locked registration SHA-256 `88efa4b503cb4cddeae78039f5d7d8805988425110e4c14511a57e66b699fe96`. The runner SHA-256 is `98d2c461a65890282977bb035a890f795d5f3b3eac4defea0d6f6797b9213d02`; the reader SHA-256 is `d8ab381babe37aae4bf1d2c9f6cdb8dd3105db67e0ff36ac2ee68bbf2929acef`. All nine registered producer, launcher, analysis and subgroup file hashes match the local final files. No receiver, truth, SSH operation or population call was run for this review.

## Findings (fixed)

- File: `experiments/cstate_necessity_stageB_resume_20260928/analyze_method_closure_five.py` and `f2_run_population_five.py`. Issue: the draft saved per-call cumulative process RSS but omitted it from analysis, leaving the full F2E 155-slot memory footprint unreported. Fix: the producer seals the campaign process high-water; the reader validates monotonic paid-call RSS and exports `paid_call_memory.csv` plus the campaign peak. The report explicitly says these are shared-process cumulative peaks, not isolated policy peaks.
- File: `experiments/cstate_necessity_stageB_resume_20260928/analyze_method_closure_five.py`. Issue: logical prefix/branch cost and branch raw SHA were emitted but not independently reconciled with paid calls. Fix: the reader checks each segment cost, total cost and branch SHA against its actual paid prefix/continuation row.
- File: `experiments/cstate_necessity_stageB_resume_20260928/f2_run_population_five.py`. Issue: a 900-second B/LOCAL call starting near the 72-hour campaign limit could overrun that limit. Fix: each paid call's timer is bounded by both its per-call cap and the remaining campaign wall time.

The complete F2E timing path starts before input loading and ends after durable raw and decision serialization. `receive_f2e` hands its 155-path `Channel` to two unchanged `scalar_joint` TF20/LDPC50 rounds, with checkpoint writes inside the measured receiver interval. The producer checks `p == 155`; it neither calls the excluded F2E continuation adapters nor replaces them with zero-effect rows. The fixed schedule accounts for 2,048 fresh prefixes and 120 F0-triggered continuations; the reader requires all 2,168 paid calls, 5,120 logical rows, exact 40 F0 triggers and exact saved observation identities. It checks the observed Git attestation before opening even the truth seal. Any incomplete run has no admissible population result.

## Findings (not fixed)

None within this focused source review. Independent per-policy peak RSS is unavailable from the registered single shared process and is explicitly not inferred.

## Verification

- Targeted synthetic tests: 10 passed (`test_f2_population_five.py`, `test_trigger_subgroups_five.py`, `test_f2_run_population.py`). These are contract tests, not communication-performance evidence.
- Lint: Ruff passed on the five new Python producer/reader/helper/test files; `bash -n` passed on the launcher.
- TypeCheck: unavailable locally (`mypy`/`pyright` absent); no type-check pass is claimed.
- Source registration: nine final local source/launcher hashes match the manifest. No actual remote execution or saved-output recount is claimed.
