# Frozen package intake — source blocker resolved

User supplied `/Users/guoyikun/Downloads/SP_AFDM_Design_Freeze_20260920.zip` after the earlier scoped search. This supersedes the missing-source conclusion in intake-audit.md; no claim is made that the ZIP existed during that search.

## Verified without extraction or execution

- Archive: 56,522,442 bytes; 279 members; 58,118,720 uncompressed bytes.
- ZIP CRC check: no failures. No duplicate member paths, path traversal, absolute paths, backslash paths or symlink members detected.
- SHA256SUMS: all 278 listed members present and matching; no mismatches. This verifies internal consistency, not external provenance/authenticity.
- docs/DESIGN.md and docs/LOCAL_PROTOCOL.md are byte-identical to the two original user-supplied Markdown documents.
- All expected core source, test, driver, lock and registration paths are present, along with the upstream closure and LDPC cache.
- 59 unique JSON configuration IDs: proposed 6; I1 6; native EP 6; native bilinear 6; native GAMP 6; shared EP 6; actual-integer control 6; shared GAMP 6; exact SBL 3; ablations 8.
- 110 Python files parsed with the local Python AST parser without syntax errors. This is not import, dependency or runtime validation on deinlab's Python 3.10.
- Saved mechanism/interface arrays, driver smoke arrays/ledgers/manifests, baseline/core reports and benchmarks are present. No development/confirmation campaign has been newly run or independently recounted.

Commands used Python stdlib zipfile.testzip, hashlib.sha256 against every manifest entry, byte comparisons with Path.read_bytes, JSON catalogue counts and ast.parse. Original ZIP and its contents were not modified or extracted.

## Source-specific findings for execution

Line references below refer to files inside archive root SP_AFDM_Design_Freeze.

1. **Resume can mix evidence identities.** src/run_local.py:42-44 creates/reuses output folders then writes a new manifest unconditionally; lines 63-68 rewrite input/truth and skip existing arm markers. There is no prior-manifest comparison or ledger/marker reconciliation before these operations. Changed sources or configurations can therefore relabel skipped old results under a new manifest. Reproduce with a focused contract test before patching; preserve append-only evidence and reject incompatible resume.
2. **Stage timings are dropped from persisted results.** src/receiver.py:77,93-97 calculates refit_seconds and detector_seconds; src/run_local.py:79 retains only complete/front seconds plus events. The required stage-cost evidence is incomplete. Audit remaining setup/decoder/conversion timing before claiming complete breakdowns.
3. **Analysis lacks run provenance validation.** src/analyze.py:9-16 reads a lock and ledger, checks duplicate keys and expected rows, but does not read run manifest or verify its phase/source/selected configurations against the lock. A complete-looking ledger alone is insufficient for confirmatory inference. Add tests and boundary validation before any future confirmation use.
4. **Statistical metadata is stale.** protocol/protocol.json minimum_evidence calls the degradation bound a one-sided paired bootstrap bound; docs/LOCAL_PROTOCOL.md and src/analyze.py:20-28 use the conservative exact binomial/union-bound construction. Follow the already-frozen latter contract and make protocol/lock wording consistent before selection.
5. **Delivery analysis is not yet complete.** src/analyze.py reports primary deadline FER, paired tests and runtime summaries, but does not produce all requested development FER/BER/NMSE, memory and full-frontier plots/tables. Fill evidence/reporting gaps without changing receiver mathematics.

These are source-inspection findings, not reproduced runtime failures. Other algorithmic correctness and truth-access checks remain open. Existing successful tests cannot substitute for them.

## Environment compatibility

Delivered environment.json records Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0 and PyTorch 2.10.0+cpu. Authorized deinlab AFDM environment has older versions (see intake-audit.md). First run original qualification with the existing environment in a separate working copy. Preserve original results; many tests write directly into package results/. New local/remote outputs must not overwrite delivered evidence.

## Next step

Planning inputs are now complete. Proposed execution: preserve/import source; deinlab original qualification; focused evidence-pipeline corrections and rerun; bounded cost screen; viable registered development; independent recount/plots/manifest/readiness report. No formal confirmation campaign or paper redesign. Final plan review remains required before activation under the current workflow.
