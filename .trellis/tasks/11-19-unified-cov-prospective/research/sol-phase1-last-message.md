**Phase 1 complete.** Commit `de7ad0f3` on `main`. Confirmed `model: gpt-6.2-sol`. Stopped before freeze and the main run.

**Fresh block** 4400–4599 cleared the local and deinlab archive audit and remains blind. Overlapping frame labels came from independent RNG streams. [Audit receipt](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/out/phase1_20261119/fresh_check.json)

| Gate | deinlab result |
|---|---|
| G1 | PASS. Five SBL references on 20 keys, F0/CD on 8 Stage 3 keys, and A2 on one archived split-prospective key. |
| G2 | PASS. Bit-exact reductions and 21,850 trial scores checked against brute-force `_system`, with maximum relative error `1.29e−15`. |
| G3 | PASS. Repeated runs matched on 12 SBL and 8 CSTATE smoke keys. All seven synthetic verdict tests passed. |

- **Leverage (a).** The 95% cluster-bootstrap half-width of φ_lo was **0.0857** on 1,200 archived keys and **0.0606** extrapolated to 2,400.
- **Leverage (b).** Whole-grid A2 − A1 FER was **+4.531 pp [3.984, 5.094]** on 6,400 archived split-prospective K keys.
- **CSTATE Γ_U.** The direct route rebuilds the projector on each trial support and solves the full normal equations. Each continuous pass fixes its own projector, and final refit rebuilds it.
- **Projected cost.** **19.008 core-hours** with the 1.3 multiplier for 2,400 SBL and 6,800 CSTATE keys. The gate chain used 0.336 core-hours.
- **DRAFT changes.** Clarified the refinement baseline and projector resets for parity, documented shared-fit and trigger-weighted timing for the budget, and kept the approved Phase 1 scope. The preflight defect from initializing the shared P1 context twice was fixed before any simulation. [DRAFT and revision reasons](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/PROTOCOL.md) · [Qualification report](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/out/phase1_20261119/RESULTS.md)