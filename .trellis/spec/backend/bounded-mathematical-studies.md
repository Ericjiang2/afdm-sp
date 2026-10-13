# Bounded mathematical studies

## 1. Scope / trigger

Applies to local mathematical diagnostics with saved random inputs, numerical
integration or instrumented comparison costs. Scientific grids remain in the
owning task, not in this code specification.

## 2. Signatures

Reference: `experiments.afdm_higher_order_information.protocol.run(stage,
config, sources, calculate, wall_seconds=600)`. The callback receives a fresh
output directory, saves raw data and returns a JSON-compatible summary.

Saved-record reference: `afdm_method_advantage.study.dump_records(path, value)`
and `analysis.records_path(folder)`. Primary input selection is performed by
`analysis.discover_inputs(artifact, config, excluded_stage=None)`.

## 3. Contracts

- Require committed bytes for executing task Python sources before admission.
  Once an implementation is marked ready, edits require a new commit before GO.
- Preload all numerical dependencies before freezing the effective thread-pool
  inventory. A newly imported single-thread OpenMP pool still changes inventory.
- Config declares seed and exact new-observation count. Admission reservations,
  source snapshots, argv, environment, raw hashes and failures are retained.
- Distinguish stage wall time from interpreter startup; complete-message cost
  must include construction and fitting. Count cached responses separately from
  new response evaluations; reused candidates are constructed only once.
- Raw-dependent readers use new stage names, verify input hashes, and declare
  zero new observations/nodes when they only recompute saved results.
- Create checkpoint chunks exclusively; write the final record collection once.
  Compact gzip JSON is lossless (`mtime=0`); bind compressed bytes. A folder must
  contain exactly one of `records.json` and `records.json.gz`, never both.
- Keep selected supplementary cohorts outside the original comparison family.
  Record explicit cohort/mode/name exclusions with metadata hashes and reasons;
  reject unknown scientific cohorts rather than silently skipping them. A frozen
  historical summary retains its original input inventory when new stages appear.

## 4. Validation and error matrix

| Condition | Required behavior |
|---|---|
| Executing source differs from HEAD | Reject before callback/observation generation |
| Existing stage directory | Reject; do not overwrite |
| Late numerical-library import changes pool inventory | Retain failed attempt; preload before a newly registered run |
| Invalid or exceeded observation allocation | Reject before calculation |
| Scientific moments diverge or information is zero | Preserve explicit mathematical classification; finite quadrature values do not override it |
| Missing, duplicate or damaged record representation | Fail explicitly; no plain/compressed fallback |
| Known supplementary cohort in primary scan | Exclude with provenance; do not pool observations or change the original family |
| Unknown or inconsistent scientific cohort | Reject the scan |

## 5. Good / base / bad cases

Good: the same physical candidate grid yields identical q/delta estimates and
is reported as no coordinate gain. Base: preserve every reference-failed group.
Bad: loosen a tolerance or drop failed samples to manufacture an advantage.
Good: replay a failed stage's saved observations with a new stage name and zero
new-observation allocation. Bad: overwrite its checkpoint or reinterpret its
partial run as an independent new cohort.

## 6. Required tests

Test registration and source snapshot before callback, immutable stage names,
failed-attempt reservations, uncommitted-source rejection and complete saved
message-count replay. Model tests separately cover rank, cavity and truth-input
boundaries; recorder fixtures are not research evidence.
For saved records, assert exact gzip roundtrip, exclusive creation, complete
unique group prefixes, byte-hash binding, corruption rejection, and explicit
cohort separation (`afdm_method_advantage/test_study.py`, `test_analysis.py`).

## 7. Wrong versus correct

Wrong: compare thread counts while silently accepting new numerical libraries.
Correct: preload the actual dependency graph and keep the same effective
inventory before and after work, preserving failed preloads as evidence.
