Phase 1 complete at `f0d606e2`. Confirmed `model: gpt-6.2-sol`.
Fresh-block audit found zero P1 hits in 4600–4799, including 4700–4799, across local and deinlab archives. The block stayed blind.

| Gate | Result |
|---|---|
| G1 | PASS · R0 and U2 matched all 20 seeded archive keys exactly |
| G2 | PASS · K cap and uncapped parity, plus M EM and refinement parity, verified on 12 smoke keys and with synthetic cap controls |
| G3 | PASS · All non-timing fields repeated exactly on 12 smoke keys |

K capped at least one mode in 636/636 multi-atom co-delay blocks, removing 39.10% of U2’s trace and 65.56% of the exact covariance trace.  
Projected cost for 2,400 keys is **11.552 core-hours** with 1.3× headroom. [Receipts](experiments/sbl_residual_gap_20261119/out/phase1_20261119_attempt02/results.json)  
The [DRAFT](experiments/sbl_residual_gap_20261119/PROTOCOL.md) records the audit, interval conventions, census denominators and gate details. All six verdict tests passed. The first launch’s import collision was fixed before any frames ran.