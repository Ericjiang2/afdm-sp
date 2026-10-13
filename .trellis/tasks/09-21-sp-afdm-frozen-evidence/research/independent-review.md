# Independent evidence-pipeline review — 2026-09-21

## Findings (fixed)

- File: `experiments/sp_afdm_frozen_20260920/src/evidence.py`, `src/run_local.py`, `tests/test_evidence_contract.py`
- Issue: The shared run validator accepted malformed stage/round timing metadata, and failed stages could be represented by omitted fields or implicit zeroes.
- Fix: Require finite nonnegative complete/stage/event times, explicit `None` for unavailable failed-stage splits, ordered round records, bounded known stage totals, and a declared failure timing scope. The driver now emits that schema for whole-attempt failures.

- File: `experiments/sp_afdm_frozen_20260920/src/seal.py`, `src/analyze.py`, `tests/test_protocol.py`
- Issue: Selection and confirmation runtime summaries excluded numerical-failure attempts even though their measured cost was saved and must be charged.
- Fix: Compute reference, selection tie-break, and runtime summaries from every validated complete attempt; report numerical-failure incidence separately.

- File: `experiments/sp_afdm_frozen_20260920/src/evidence.py`, `src/run_local.py`, `tests/test_evidence_contract.py`
- Issue: Frame seed namespaces were executable but not explicitly retained in frame artifacts or bound to run identity.
- Fix: Bind the actual SeedSequence prefix, phase code, component IDs, replicate/split arguments, and generated channel seed into the manifest identity and both input/truth artifacts. Validation recomputes and checks the descriptor without changing generated observations.

- File: `experiments/sp_afdm_frozen_20260920/src/receiver.py`, `tests/test_fresh_decoder_accounting.py`
- Issue: `ABL_fresh_APP` retained and charged only its terminal LDPC call; the fresh APP decoder call was included in complete wall time but omitted from decoder records and decoder-stage time.
- Fix: Preserve both decoder records in order, attach metadata to the fresh event, and charge the sum of fresh and terminal decoder times. The receiver still makes exactly the same two mathematically required calls.

## Findings (not fixed)

None within the reviewed evidence-correction scope. The four-arm run is an engineering smoke with one observation, not development coverage or radio-performance evidence.

## Verification

- Lint: not configured / not run
- TypeCheck: not configured / not run
- Python syntax compilation: pass
- Whitespace check (`git diff --check`): pass
- Tests: pass (12 sequential regressions on `deinlab`, including focused evidence, decoder-observer, fresh-decoder, fallback, integration, native, and protocol tests)
- Runtime smoke: pass (four arms, one frame; offline recount and fresh-decoder accounting pass)
- Final remote source: `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921`
- Evidence: `/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/reviewed_pipeline_20260921`
- Run identity: `b665510819ae7464320450681458c29de98fd0158239c9f5d13610bf27cf52df`
