**Phase 1b complete.** Commit `246dcbd7` on `main`. Confirmed `model: gpt-6.2-sol`. The protocol remains DRAFT and P1 frames 4400–4699 remain blind.

| Gate | deinlab result |
|---|---|
| G1 | PASS. 20 SBL references, 8 Stage 3 F0/CD keys, and 8 archived A2 keys across all four cells. |
| G2 | PASS. Bit-exact τ=0 mirror reductions and empty-U2 parity. Both fixed-projector descent and saved-state V5-adm checks passed. All 10 isolated admission cases matched the closed forms within `2.24e−13` relative error. |
| G3 | PASS. 12 SBL and 8 CSTATE smoke keys reproduced. Ten synthetic verdict tests also passed. |

- **Leverage.** `m = 0.500 pp`. The maximum old-data 95% ψ half-width was **0.0231**, selecting **FER as V5 primary**. The replay yielded **894 V5-adm units per 200 frames**.
- **Cost.** Selected **200 SBL frames** at **18.252 core-hours**. The 300-frame option costs 27.377 SBL core-hours and 28.564 total. The selected total is **19.438 core-hours**, including 1.185 for six CSTATE arms and 0.0015 for V5-adm.
- **DRAFT revisions.** Mirror covariances use two-sided projections because the covariance can change within a fixed-projector pass. The C-hi/CD rare-event bound accompanies the ψ verdict because §10.4 bounds a FER difference. [Phase 1b report and receipts](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/out/phase1b_20261119/RESULTS.md)