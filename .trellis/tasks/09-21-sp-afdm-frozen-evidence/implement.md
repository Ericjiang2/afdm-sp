# Execution plan — frozen SP-AFDM evidence

Status: bounded staged delivery complete; research task awaits user acceptance. Latest authority is `staged-plan.md`. Both stages completed, continuation heuristic failed, and execution stopped. No further full grid, retuning or confirmation is authorized. Earlier sections below are historical requirements superseded where the staged plan narrows them.

## 1. Source and environment gate

- [x] Locate shipped package and its upstream, tests, protocol/configurations.json, code generator and historical results. Inventory verified; review applicable licenses before redistribution.
- [x] Verify package has all 59 registered arms, source lock/seal tools and analysis entry points. Presence and JSON catalogue checked directly inside ZIP; execution still pending.
- [x] Preserve original package; choose isolated workspace import and fresh results destination. Inspect user diffs before touching existing tracked files. Original-source boundary: 70dd0077; current-user unrelated changes preserved.
- [x] Load trellis-before-dev and Python/evidence specs; document exact changed files and intent before source edits. Existing authorization covers necessary in-scope fixes, not scientific redesign.
- [x] Pin one environment with Python, NumPy, SciPy, CPU PyTorch and Matplotlib. Record OS/CPU/BLAS/thread settings, dependency versions and source hashes. No system package modification.
- [x] Prefer authorized deinlab AFDM environment; qualify its PyTorch CPU path with CUDA disabled. Inspect remote task destination before creating it, transfer only task-owned sources, verify source identity, and retrieve/reconcile frame evidence. Do not mix local and remote latency samples.
- [x] Inspect process/resource availability; establish single CPU benchmark ownership. Available storage must be measured again before broad runs.

Entry observation: default Python 3.14.6 has none of NumPy/SciPy/PyTorch/Matplotlib; bundled Python 3.12.14 has NumPy 2.3.5 but lacks the other three. Filesystem showed about 206 GiB free. These are read-only environment observations, not runtime qualification.

Remote steering: deinlab SSH read-only probe succeeded. Existing AFDM environment: Python 3.10.20, NumPy 1.26.4, SciPy 1.10.1, PyTorch 2.5.1+cu121, Matplotlib 3.7.1; 128 logical CPUs were reported in the earlier wrong-project probe; fresh recovery measured 251 GiB total RAM, 242 GiB available and low sampled load. No installation is currently justified. That was the initial discovery observation; subsequent original qualification and corrected smoke passed. See `research/original-qualification.md` and `research/evidence-pipeline-correction.md`. Initial discovery evidence remains in `research/intake-audit.md`.

Update: source supplied and verified; see `research/frozen-package-audit.md`. Original package used Python 3.13.5 / NumPy 2.3.5 / SciPy 1.17.0 / PyTorch 2.10.0+cpu. Deinlab versions differ; do not label old/new numerical outputs bitwise reproducible until checked. Qualify the existing environment first and freeze actual versions used for new evidence.

## Concrete file scope for approved execution

- Preserve original ZIP unchanged. Prospective local working root: `experiments/sp_afdm_frozen_20260920/`; prospective remote root: `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_20260920/`. Check nonexistence before import; never overwrite existing user work.
- `src/run_local.py`: reproduce/fix resume identity and marker/ledger reconciliation; persist complete timing/diagnostic evidence and effective environment metadata.
- `src/receiver.py`: audit existing refit/detector/front timings and decoder records; add only missing instrumentation required by the contract. Correct algorithms only when qualification demonstrates a defect.
- `src/seal.py`, `src/analyze.py`, `protocol/protocol.json`: test source/run identity and coverage; reject invalid inference inputs; align the stale statistical description with the already-frozen exact bound. Preserve family selection rules.
- `tests/test_protocol.py` plus focused driver/evidence tests: failing reproductions for actual evidence gaps; keep synthetic tests explicitly separate from communication evidence.
- Add package-local development reporting and isolated-memory measurement entry points only if no reusable equivalent exists; retain one receiver implementation and the existing catalogue as authority.
- New per-run output under `results/sp_afdm_frozen/<run_id>/`; task research/handoff and task-local `research/code-changes.md` record findings/provenance. No unrelated files.

## 2. Audit and original qualification

- [ ] Map frozen receiver steps, legal-information boundary and every comparator to actual source/test lines.
- [x] Run original checks sequentially from an isolated delivered-package copy with CUDA disabled and OPENBLAS/OMP/MKL/NUMEXPR threads set to one. Eight original commands passed; logs, exit status and process metrics retained under results/sp_afdm_frozen/qualification_original_20260921/.

```text
python tests/test_core.py
python tests/test_baselines.py
python tests/test_bilinear.py
python tests/test_cache.py
python tests/test_fallback.py
python tests/test_integration.py
python tests/test_native.py
python tests/benchmark_kernels.py
```

- [x] Recount existing mechanism observations independently where delivered arrays permit it. All 104 saved decisions passed tests/verify_saved_decisions.py. Missing original fields are recorded in research/raw-diagnostics-source-map.md.
- [x] If a test fails: retain failure, minimize reproduction, fix only the violated contract, run targeted regression then relevant full qualification. No sweep with a known broken comparator.
- [x] Audit registration/seal coverage, timestamp legality, resume markers vs ledger, failure decisions, complete costs and array schema before using them for selection.

## 3. Minimal driver and cost screen

```text
python src/run_local.py --phase development --frames 1 --arms P_M24_I20 I1_BP12_r0 --cell 2 --out <fresh-smoke-dir>
```

- [x] Inspect whether --out affects seed identity; prevent accidental mixing of smoke rows and registered development rows.
- [x] Verify saved arrays and offline recount, full timing boundaries, actual I1 canary and no operational truth routing.
- [x] Run minimal paired representatives of every native baseline, exact SBL and critical controls before broad selection. Never treat this as the full registered development.
- [x] Measure complete time and fresh-process peak RSS for representative arms; estimate 9440-call development and prospective confirmation storage including native rounds and canaries. Report empirical cost bounds before scaling.
- [x] Preserve screen failures/dominated variants and all negative findings. Do not change temperature, normalization, LLR routing or iteration budget opportunistically.

## 4. Registered development or explicit no-go

- [ ] Use unchanged 59 x 5 x 32 registration if viable; document resource decision. All strong baseline families receive their registered opportunities.
- [ ] If aborting for cost or invalid design/implementation, preserve partial ledger and deliver no-lock recommendation. An alternative smaller registration must be prospective and visibly distinct.
- [ ] Run one timed process with per-frame resume validation; no repeated timing shards on the same host in parallel.
- [ ] Derive selected family configs and useful operating cells solely from development. Check finite-option membership and all expected unique frame/arm keys.
- [ ] Generate confirmation_lock.json only after original complete-coverage and FER-transition rules pass. Do not invoke the confirmation phase.

## 5. Analysis and complete delivery

- [ ] Independently recompute BER/FER and paired harms/rescues from saved bits; reconcile time/checkpoint eligibility and ledger failures.
- [ ] Derive NMSE, support omission/collision/model diagnostics, latency summaries, peak memory and call/stage counts with explicit denominators.
- [ ] Produce machine-readable summaries and tables; FER/BER and NMSE by operating point; complete deadline FER/cost and memory frontiers; stage timing; scalar/full Gamma and controlled-interface comparisons; fresh/cached dense benchmark.
- [ ] Write RESULTS.md and exact reproduction manifest, include all five requested delivery categories and readiness/frozen-setting/no-go recommendation. Mark development uncertainty and absent confirmation explicitly.
- [ ] Run artifact/schema/recount tests, applicable lint/type checks if configured, relevant package checks, then a minimal reproduction smoke. Do not mistake static checks for execution evidence.
- [x] Use one independent trellis-check agent after implementation; inspect for duplicated logic, silent fallbacks, truth leakage, hidden initialization/decoder costs and discarded negative outcomes.
- [x] Record .py/.m/.sh changes in task-local `research/code-changes.md` with agent provenance. The old `docs/Code_Changes.md` mechanism is archived read-only and superseded by CLAUDE.md's Trellis record authority. Stage only owned task files if committing; never commit unrelated pre-existing changes.
- [ ] Write handoff into this task. Update accepted STATE/Atlas only after user acceptance. No push.

## Rollback and stop gates

- Qualification failure -> stop scientific execution, keep diagnostic evidence.
- Source/config change after selection -> invalidate candidate lock and affected data identity, retain original artifacts.
- No useful FER transition, unfair baseline, missing full costs or incomplete development -> no confirmation-ready claim.
- Negative complete frontier -> document and stop; no receiver-module expansion.
- Final confirmation remains a separate future decision.

## Agent allocation

One Sol high execution agent is active in the resumed session. Main coordinates and reviews evidence; reuse agents and keep count small. One independent Sol high checker may review the final implementation. Luna xhigh is reserved for a useful bounded read-only lookup.

## Qualified instrumentation exception — 2026-09-21 recovery

The original immutable package remains byte-identical. Source inspection found upstream `direction_receiver.terminal_decode` calls the hard-return LDPC API, which discards raw APP/check/iteration records. These cannot be reconstructed from hard decisions without a forbidden second decode. The corrected working copy may add exactly one optional decoder observer to this existing function. Default `None` preserves the original path; capture reuses the same existing decoder core once. No new receiver algorithm, altered clipping/schedule, duplicate terminal path or runtime monkeypatch is permitted.

This is an evidence-instrumentation correction under the approved missing-instrumentation scope, not a scientific receiver redesign. The previous unconditional statement that corrected upstream bytes remain unchanged is superseded for this one instrumentation file only. Preserve original hashes; record the corrected source identity and explicit delta. Require captured/uncaptured fixed-input numerical parity plus one-call verification before scientific use; count instrumentation and conversions honestly. The frozen scientific document itself remains unchanged.

## Current-session delivery limit — user decision 2026-09-21

After the 59-arm screen completed in 228 s, the user chose “本次先交付小规模结果” over the estimated 5–6 h full development. Deliver the existing screen and representative memory evidence. Full 59 × 5 × 32 development, selection and confirmation lock remain unperformed; their unchecked criteria are future work, not blockers to this bounded delivery. Preserve task state for a later explicit continuation.

Bounded delivery completed: 59/59 one-observation configurations and offline raw recount passed; 10/10 isolated memory probes passed. Report: `results/sp_afdm_frozen/RESULTS.md`. Full registration and inference acceptance criteria remain explicitly open. Corrected source boundary: `31d5ec0d`.

## Active continuation: minimal staged campaign

The user has now explicitly authorized `staged-plan.md`; previous “await continuation” limitation is superseded for this bounded campaign. Implementer owns package-external compact runner/validator/launchers; checker reviews only that changed boundary. Stage 1: 260 calls. Conditional Stage 2: at most 320. Keep archived receiver source/results immutable. Report six requested answers; no full grid/confirmation.

## Minimal staged delivery completed

Stage 1: 260/260; Stage 2: 256/256; independent fresh observations 20 + 64. Both compact recounts and all 34 heavy audit arm-cells passed; 0 numerical failures. Nine synthetic contract tests passed before execution. Receiver time 1752.166 s; four numerical-process wall times total 1995 s; evidence files 39,540,686 bytes. Proposed nets only 2/1 deadline rescues over EP at 6/8 dB while costing 2.27/2.47×: frozen continuation heuristic false. Stop/defer, no new experiment or confirmation. Six answers, estimates and all retained/eliminated configurations are in `results/sp_afdm_frozen/RESULTS.md`. Remote clearance at 2026-09-21 08:47:46 UTC found no related process/session. Scientific acceptance/STATE remain unchanged.
