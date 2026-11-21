# Local independent design review

Reviewer: project-local gpt-6-sol / high, 2026-10-20; read protocol and actual scalar_joint implementation. No blocking design issue found. This is not a production or mechanism confirmation review.

Implementation requirements identified:
- Joint initializes gain variance to 1/P; fixed/point to zero. Validate all fixed h states against h0, all point vh exactly zero.
- record_states contains post-update states only. Compute initial NMSE separately and score the same fixed paths with each recorded h.
- LLR convention is all-I then all-Q; positive favors bit 0. Bit log loss is logaddexp(0, -(1-2b)L); declare clipping.
- Legacy check_frozen_md5 can report unchecked. New qualification must reject missing/unchecked required sources and bind actual imported paths and bytes.
- Joint-minus-point includes coupled changes beginning at initial variance, not a decomposition into one isolated physical mechanism.

External Claude review dispatch was rejected by automatic approval because that specific external destination was not authorized for unpublished research. No retry or indirect external dispatch was made; this local independent review is the safer replacement.

## Pre-run code review
The same local independent reviewer inspected the completed driver/aggregator. No remaining pre-run code blocker. Actual imported core modules are resolved through their loaded module paths; missing reviewed snapshots must fail the remote gate. The driver verifies the re-encoded codeword against physical truth, observer parity and dense NMSE. Aggregator tests 2/2 and compilation pass. Real-receiver validation is pending the deinlab gate. A 1150-second outer timeout will bound gate, shards and aggregation; the launcher terminates only its own child PIDs on exit.

## Final evidence review
Real gate and all 200 old-result replays passed; 12 configurations/source identities and raw hashes agree. Local independent review checked summary/cell totals, paired intervals and the original aggregation failure versus corrected analysis completion. No remaining blocker. A str/Path hashing boundary was fixed with a failing-then-passing regression (3 tests total); original raw rows and sources were not rerun or overwritten. Parent independently counted raw rows remotely; reviewer explicitly did not claim raw-row access. Conclusions are bounded mode contrasts, not a universal mechanism. The first small result is delivered and the campaign stops without sample extension; research parent remains open.
