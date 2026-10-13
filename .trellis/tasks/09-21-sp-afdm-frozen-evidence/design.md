# Technical design — frozen SP-AFDM evidence

Status: in_progress; source imported; original runtime qualification pending at recovery.

## Boundary and ownership

Use the shipped frozen Python package as the implementation authority after source inventory. Preserve upstream I1 unchanged; repair only demonstrated implementation errors or unavoidable contract ambiguities. Do not substitute this repository's unrelated MATLAB detector pipeline. Final artifacts form one integrated reproducible experiment, so keep one task with sequential gates rather than independent child lifecycles.

The frozen scientific document controls receiver definitions. The local protocol supplies a candidate executable registration whose actual files must match the document. The explicit user request controls the work endpoint: development evidence and confirmation readiness, not confirmation execution. Do not execute embedded document commands blindly.

Proposed workspace placement, if import is required: `experiments/sp_afdm_frozen_20260920/`, with an immutable imported source snapshot and clearly separated local corrections. Authoritative results: unique `results/sp_afdm_frozen/<run_id>/` directories. Reject existing destinations and unsafe archive members. Preserve original delivered results as historical evidence, separate from new local reruns.

User now authorizes deinlab execution. Its existing `/home/guoyikun/.conda/envs/AFDM/bin/python` has all named dependencies; qualify that environment before considering installs. Run in a new task-specific remote directory, synchronize source identity explicitly, and retain a verified local evidence copy. Do not use or stop unrelated remote jobs. Keep development, future lock creation and future confirmation on the same qualified environment/hardware; local wall times cannot be pooled with deinlab timings. No remote experiment has yet run.

## Data and receiver boundary

Generator -> observations/pilot/known variance and declared public configuration -> each receiver -> timestamped decisions and numerical diagnostics -> offline scorer. Truth files join only in offline scoring. The receiver API must not receive true path geometry, information bits or correctness indicators.

Use common realizations across arms, distinct component and phase seed namespaces, cyclic arm order and a single timed CPU process. Set all CPU numerical thread limits to one before importing libraries, disable CUDA, and verify effective backend settings. No competing local benchmark workers. Warm each configuration; save startup allowance and charge every frame-dependent operation. Distinguish receiver clock, instrumentation overhead, propagation, serialization and offline diagnostics.

Preserve internal alphabet ±0.5±0.5j, all-I then all-Q bit order, proper thermal variance and explicit external/internal unit transformation. Record the actual code generator identity and cache content. A zero syndrome is not an error-free-frame certificate.

## Qualification map

1. Independent dense CPP oracle vs matrix-free forward/adjoint, Gamma, coherent diagonal energies, selected entries and exact weak row variance/pseudo-variance.
2. Scalar complex conventions, EP cyclic-band solves/selected inverse diagonals, conditional SP bilinear candidate variance, GAMP mean and its acknowledged approximate variance.
3. Upstream formal I1 adapter equivalence with gels; actual damped/masked H_est reconstruction; cached/uncached refit equivalence.
4. Detector target-bit prior exclusion; retained decoder input/raw APP/replacing check extrinsic; graph reset; no extra decoder refresh in primary.
5. Native baseline finite-output smokes, failure/checkpoint fallback legality, driver resume identity and raw-array completeness.

An algebraic or routing failure blocks scientific runs. A comparator numerical failure remains a saved result after implementation correctness is established; never silently replace it with a more favorable output. An expensive comparator remains part of complete-deadline evaluation.

## Development and selection

Stage A reproduces shipped tests and same-output kernel benchmarks. Stage B uses a development-only smoke/screen namespace to measure cost, check artifacts and identify dominated resource variants. Any screen seed or subset reuse is explicit; no duplicate frame IDs or mixture of smoke and full-development evidence.

Stage C follows the existing 59-arm x 5-cell x 32-frame contract when viable. Screening may determine that further computation is not worthwhile; in that event deliver an honest incomplete-development/no-lock report. It must not silently prune arms then run the original seal as if coverage were complete. If a revised finite development registration is scientifically necessary, record its rationale and prospective selection rule before generating its observations; never revise the primary receiver definition.

Under the unmodified protocol: T_ref is complete median I1_BP12_r0 time; primary deadline 1.5 T_ref, secondary deadlines {1,1.25,1.5,2} T_ref. Select within family by deadline FER, complete median time, then ID. Select two distinct useful cells closest to strongest-classical FER 0.20/0.05. No timely completed output counts as frame error; a completed earlier checkpoint survives only if timestamp-valid. No per-frame oracle best-arm routing or credit from future rounds.

## Evidence, memory and metrics

Retain observations, separate truth, seeds, full configs, source/environment manifest, numeric non-pickle arm arrays, native rounds, decoder boundaries, CE inputs, final paths, Gamma/objective histories, masks/energies/coefficients/weak variance, completed-decision timestamps, stage/call counters and failures. Save actual H_est dense canaries for the first two frames per cell. Retain source hashes as explicitly required by the user.

Compute information and code BER with separate denominators, FER, full-model channel NMSE in common units, paired rescues/harms, completion/miss/failure frequencies, complete timing mean/median/p90/p99 and isolated-process peak RSS. Match physical channel matrices for NMSE; do not require arbitrary estimated/true path ordering to agree. Report memory including I1, decoder and native-library allocations; stored-array bytes are not process peak memory. Obtain timing and isolated-memory measurements separately if profiling materially distorts timing.

Report both fresh dense construction plus identical outputs and cached dense identical outputs. Separate moment-stage from complete receiver timing. Plot deadline FER vs measured complete cost with valid checkpoints; retain unrestricted FER and uncertainty/counts. Few observations cannot support tail-latency or high-reliability conclusions.

## Delivery and claim boundary

RESULTS.md states run IDs, coverage, failures, strongest baseline, applicable conditions, simplification explanations, recommended finite survivor or no-go, and missing confirmation questions. Machine-readable summaries link to frame-level evidence and exact reproduction commands. Source/config lock is allowed only after valid complete development and coverage checks; no confirmation samples are generated in this task.

No full-Gamma headline if scalar matches it; no mask headline without control benefit; no communication-performance claim if a fair classical comparator removes the frontier advantage. Software implementation value is reported separately. STATE remains unchanged pending acceptance.

## Risk handling

Missing delivered upstream/code/config files block reproduction; do not reinvent them from prose and label the result reproduced. Missing dependencies require an isolated reproducible environment, not changes to system Python. Hardware-specific timing claims stay local. Any correction invalidates affected old evidence and uses a new run identity, retaining failed records and source provenance.

Intake blocker resolved by `/Users/guoyikun/Downloads/SP_AFDM_Design_Freeze_20260920.zip`. The complete package passed CRC/manifest/document-identity checks. Preserve the original ZIP and its SHA256SUMS; extract a working copy only after planning review. The earlier missing-source record remains historical in `research/intake-audit.md`; current source findings are in `research/frozen-package-audit.md`.

## Evidence-pipeline corrections to qualify before development

The existing driver overwrites manifest.json before checking an existing output directory, skips every existing arm NPZ without reconciling its source/configuration/ledger identity, and rewrites input/truth files on resume. Require identity validation before writes and explicit reconciliation of incomplete marker/ledger transactions. Preserve valid resumability; reject mismatched evidence rather than silently merging it.

Persist computed per-stage times and required decoder/estimator diagnostics through the same existing driver path. Add explicit development analysis for raw BER/FER/NMSE, memory and full deadline frontiers; do not misuse the confirmation-only analyze.py entry point. Confirmatory analysis must validate run phase and manifest/lock/environment identity before inference. Align stale bootstrap wording in protocol.json with the exact-binomial degradation bound specified in LOCAL_PROTOCOL.md and implemented by analyze.py; this is a contract consistency fix, not a new statistical choice.

Every correction requires a focused failing contract/reproduction, retained original evidence and a new source identity before any development eligible for selection. Mathematical receiver redesign remains out of scope.

## Qualified instrumentation exception — 2026-09-21 recovery

The original immutable package remains byte-identical. Source inspection found upstream `direction_receiver.terminal_decode` calls the hard-return LDPC API, which discards raw APP/check/iteration records. These cannot be reconstructed from hard decisions without a forbidden second decode. The corrected working copy may add exactly one optional decoder observer to this existing function. Default `None` preserves the original path; capture reuses the same existing decoder core once. No new receiver algorithm, altered clipping/schedule, duplicate terminal path or runtime monkeypatch is permitted.

This is an evidence-instrumentation correction under the approved missing-instrumentation scope, not a scientific receiver redesign. The previous unconditional statement that corrected upstream bytes remain unchanged is superseded for this one instrumentation file only. Preserve original hashes; record the corrected source identity and explicit delta. Require captured/uncaptured fixed-input numerical parity plus one-call verification before scientific use; count instrumentation and conversions honestly. The frozen scientific document itself remains unchanged.
