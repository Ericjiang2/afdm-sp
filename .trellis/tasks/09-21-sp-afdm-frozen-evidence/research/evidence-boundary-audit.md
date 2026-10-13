# Evidence boundary audit — recovery follow-up

Scope: direct source inspection; no scientific performance conclusions. Original byte-identical qualification proceeds independently. Source files refer to experiments/sp_afdm_frozen_20260920.

## Confirmed source gaps

1. src/run_local.py creates folders and overwrites manifest before considering existing arrays. Resume skips NPZ markers without checking ledger, input, source or config identities. This can relabel old evidence. Validate complete identity before any writes; preserve valid resume and explicitly reconcile crash states under the frozen protocol.
2. flatten() keeps numeric ndarrays but discards scalar/string leaves. Decoder records therefore retain arrays while losing stage, iteration, timing, syndrome/validity and provenance metadata. Required diagnostics need one lossless numeric-array plus JSON metadata representation, shared by writer and readers.
3. finish() calculates refit_seconds and detector_seconds, but run_local persists neither. Native loops retain only the final result scalar values; store every round and total charge. I1 final decoder raw APP/check/iterations are not saved; instrument the existing call without a second decode.
4. run_local catches every Exception, including storage/programming errors, as numerical_failure. Separate expected receiver numerical failure from artifact corruption or programming defects; retain actual failed runtime, failure record and completed eligible checkpoints, then stop on integrity errors.
5. seal verifies manifest phase/source and ledger key coverage, but not configuration/cell/frame identity nor arrays or actual environment adequacy. analyze does not read manifest at all. One shared evidence validator should serve resume/seal/analysis rather than divergent checks. Reject NaN/nonfinite times, invalid timeline order, duplicate keys and inconsistent ledger/array identities.
6. deadline_error returns failure before checking any completed checkpoint when status is numerical_failure. Pure-function execution reproduced it with a synthetic valid checkpoint; see deadline-contract-reproduction.json. Current receiver returns known fallback cases as status ok, so this is a boundary inconsistency, NOT evidence that actual saved performance has already been miscounted.
7. protocol minimum_evidence mentions bootstrap despite exact-binomial degradation bound in LOCAL_PROTOCOL and analyze. Correct description only; no statistical redesign.
8. --frames uses `a.frames or default`: explicit zero silently becomes full 32. Reject zero before launching work. Reject duplicate/empty --arms, nonfinite values and invalid cells at the driver boundary.

## Scientific boundaries to retain

run()/run_native() only receive y, pilot, sigma2 and public model/code settings. They do not receive raw truth. Native startup uses pilot-only OMP; same-I1 arms must pay full front-end even if engineering tests share it. Complete run timer encloses front initialization and terminal operations; generation/compression remain outside. Raw APP minus actual incoming LLR replaces check prior. A syndrome-zero result is not receiver-known correctness.

Inspect newly persisted records and independently recompute info/code BER, FER, timeline decisions and full-H NMSE offline. Keep historical tests/arrays unchanged. Any failing actual algebra/routing qualification blocks development until resolved; no method expansion.

## Implementation validation targets

- Failing resume mismatch and orphan-marker/ledger tests before fix; unchanged valid resume must do no receiver work or overwrite inputs.
- Real I1/proposed/native smoke record round-trip and raw recount, not only mocks.
- All-zero/full-failure resource edge cases reject invalid reference time; truthful failure denominators.
- Original numerical qualification plus focused regression; code AST is static verification only.
