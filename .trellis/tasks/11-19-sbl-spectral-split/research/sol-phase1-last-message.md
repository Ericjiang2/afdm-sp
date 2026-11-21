Phase 1 complete in commit `2d4c660b`. The protocol is DRAFT and the main run is pending. [Receipts](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_spectral_split_20261119/out/phase1_20261119_attempt02/phase1.json)

| Gate | Result on deinlab |
|---|---|
| G1 parity | PASS · exact R0/R1/R2 replay on 20 seeded keys |
| G2 construction | PASS · synthetic and 12 smoke keys at both budgets. Pruning was exercised synthetically. |
| G3 determinism | PASS · all six new arms reproduced on 12 smoke keys at both budgets |

**Join R0/R1/R2 at 100 iterations.** All 24 archive shards verified and all 3,600 reference rows had the required fields. The projection includes T0’s live R1 SBL fit.
**Projected cost** · 17.04 core-hours with the 1.3× multiplier, below the suggested 30 core-hour cap. The 400-iteration subset stays at frames 4000–4049 (600 keys).
**DRAFT revisions** · Incorporated the reviewed zero-variance census rule, logged traces separately for the two atom sets, and checked the SBL and refinement components against their arm-specific targets.
**Smoke census** · 412 of 7,542 eigenvalues (5.46%) fell in [.25, .75].
Confirmed `model: gpt-6.2-sol`.