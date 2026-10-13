# I-01 actual bindings verifier review v1

## Verdict

The verifier correctly closes most of the previously declared limitation around
actual source, input, ledger, contract, and exit files. Two completeness holes
should be fixed before its `status=passed` result is used as formal evidence.

## Verified behavior

- It hashes every `*.py` below the frozen source package and requires the exact
  228-path/digest mapping recorded by the raw audit. A missing, extra, renamed,
  or changed Python source therefore fails.
- It requires 13 audited batch roots with the exact frozen ranges. Each current
  `contract.json` and `summary.json` must retain the SHA-256 stored in the raw
  audit.
- It reconstructs every batch identity from its contract, rejects duplicate or
  overlapping contract identities, checks the per-batch F/T/E reservation, and
  requires the final union to equal all 3456 `(block,SNR,arm)` identities.
- Each contract must retain the common file/source bindings and code hashes.
  The verifier resolves the four paths actually recorded after the command-line
  flags and hashes their current bytes against the contract binding.
- Each reservation filename is derived from the contract config digest, its
  JSON must equal the contract before the runtime-only `ledger` field was added,
  and the ledger directory must contain exactly those 13 reservation JSONs.
  Each sibling exit file must contain `0`.
- The implementation is read-only except for the explicitly requested exclusive
  output file and performs no receiver calls.

## Required fixes

### 1. Revalidate the raw-audit proof identity set

The initial guard checks only `audit.status`, `audit.F_audited`, and the number of
batches. The loop never reads `batch['proofs']`. Consequently a modified audit
with empty proofs, duplicated proofs, or proofs assigned to the wrong batch can
still pass as long as those three top-level values and the recorded
contract/summary hashes remain present. The 3456 identities currently checked
come from the contracts, not from the raw audit that the result claims was
complete.

For each audited batch, require the proof identities to be unique and exactly
equal the batch contract identity set. Also require the global proof union to be
the full 3456-identity domain. This binds `raw_audit_sha256` to an audit whose
actual proofs support its top-level completion claim; it does not require
re-reading terminal arrays.

### 2. Reject a post-audit `batch-failure.json`

`not list(path.glob('failure*'))` catches `failure-*.json` but not
`batch-failure.json`. Such a file may be added after the raw audit while the
already-hashed contract and summary remain unchanged, and the actual-bindings
verifier would still pass. Check `not (path / 'batch-failure.json').exists()` in
addition to the per-call failure glob, matching the raw auditor's failure
semantics.

## Limits

This review inspected the verifier and its already established raw-audit
contract only. It did not access the remote result tree, execute a receiver, or
independently hash the 228 remote files. The findings concern evidence binding
and completeness, not any development FER or confirmation conclusion.

## Fix verification

Both required findings are closed in the revised verifier.

- Each batch now requires `F_audited` and the proof-list length to equal the
  contract-derived domain size, and requires the proof identity set to equal
  that domain. Equal list/set/domain sizes reject duplicate proofs as well as
  missing, extra, and wrong-batch identities. Since the 13 contract domains are
  already checked for disjointness and exact whole-design coverage, these
  per-batch checks also bind the raw-audit proof union to all 3456 identities.
- The failure search is now `*failure*.json`, which covers both
  `failure-*.json` and `batch-failure.json`, including a failure marker added
  after the original raw audit.

The added synthetic cases exercise empty, duplicate, and wrong-batch proofs and
a late `batch-failure.json`, alongside the existing source, input, reservation,
and complete-domain cases. A fresh run passed all 7 tests in 0.311 seconds;
`git diff --check` also passed. No remaining defect was found within the two
reported findings. This remained a local synthetic/read-only review with no
receiver or remote execution.
