# Decision-directed noise variance execution

## 2026-11-18 — Phase 1

Stopped at G1 archive qualification on deinlab. The frozen producer in
`9b633ce9df020158d51621600d7b6eab3b65395d` matches the SHA-256 in the main-run
configuration. Both selected gzip shards match the main-run MD5 manifest.
The audit selected frames 10000, 10001, 10998 and 10999 at all eight SNRs,
with G, rho .3 and cap 8. All 32 B_known (M) and 32 B_SF (N) terminal
records exist. The producer saved information-bit error counts and geometry,
plus the F0 syndrome, but omitted decoded bits and their hashes. The
206 non-row archive files supplied no decoded evidence. G1 failed at
reference availability with zero receiver calls and zero hash comparisons.
See the [G1 receipt](../../../experiments/sigma2_dd_20261118/out/gate_20261118/g1.json).

The stop condition leaves the protocol revision, implementation, G2, G3,
smoke, cost projection and prediction ledger pending. The draft remains
unfrozen. Eric can provide original decoded artifacts, or authorize a revised
G1 that generates new reference hashes through frozen replay after validating
that replay against the archived per-key fields. Replay hashes would have
new provenance.

## 2026-11-18 — Phase 1 resumed under revised G1

The original G1 reference was absent because the brief assumed decoded hashes
that the archived producer never wrote. Revision `881ddfc8` requested exact
comparison on the saved per-key fields. The revised baseline replay passed
32/32 for B_known (M) and 32/32 for B_SF (N) on deinlab, including 6 and 14
A1c branches, with bitwise Dopplers. The frozen producer and module inventory
match the archive. The loaded physical module's regressor, kernel and Γ
functions also match the specified 20260920 implementation.

The [draft protocol](../../../experiments/sigma2_dd_20261118/PROTOCOL.md)
records units, estimator timing, decisions and changes from Claude's draft.
One update follows F0 round 1. Fixed true-H A3 uses each arm's applicable
variance for both rounds, including B_DD's estimate. G2 passed on 32 old
frames × 8 SNRs. Zero-variance mean ratio 1.00213, positive synthetic variance
bias +1.08%, no synthetic floor hits. G3 found no overlap in the local or
deinlab inventories for frames 11000–11999. The revised [gate receipts and
smoke](../../../experiments/sigma2_dd_20261118/out/gate_20261118/) are
recorded alongside the original archive-availability stop.

Two new-runner issues were corrected before qualification. The local
freshness regex initially omitted the capture group expected by the frozen
scanner. The first remote launch imported new study modules inside the
canonical receiver tree, which polluted the source inventory. The execution
copy was moved to scratch and the original manifest comparison was retained.
The corrected code was rerun on deinlab. The first remote attempt log is
`/data/guoyikun/tmp/sigma2-dd-phase1-881ddfc8/attempt1.log`.

Smoke completed 128 keys per arm across the full grid. DD and SF round-1
outputs matched bitwise on all 128 keys. On a triggered old key, a separate
probe verified one update and the variance delivered to the second native CE
and detector, A1c ridge and detector, and both A3_DD rounds. That probe's
estimate reached the floor. Projected 3.12 core-hours, or 4.06 with the 30%
allowance and 15.2 minutes at 16 workers. Suggested cap 5 core-hours, with
~18.75 minutes of CPU-time allowance at 16 workers. The Sol and Claude
predictions were staged independently of Eric's existing ledger edits.
Eric decides whether to freeze the draft and adopt the suggested cap.
No fresh-cohort receiver calls were made.


## 关闭说明（2026-11-19，Eric 在收官时接受）
结果见 res-20261118-05（DEGRADED）；论文是否采用判决导向 σ² 估计器待 Eric 定（开放项）。
