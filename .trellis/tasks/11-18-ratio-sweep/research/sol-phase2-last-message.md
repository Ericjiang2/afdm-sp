Phase 2 completed in **4.403 core-hours** against the 10 core-hour cap. Results commit `844525a6`, producing commit `1a86112b`. Confirmed `model: gpt-6.2-sol`.  
**G4 PASS.** All 64 designated gain entries matched bit-for-bit. Both arms used the same deletion slot from A2’s entering fit.

| Frozen test | Verdict in all cohorts | ρ=.3 | ρ=.5 | Pooled |
|---|---|---|---|---|
| P1 · extreme-bin difference | NOT_SUPPORTED | .419 [.402, .435] | .036 [.030, .043] | .267 [.254, .280] |
| P2 · ξ₅₀ and 95% CI | REFUTED | .144 [.133, .154] | .176 [.170, .181] | .127 [.118, .136] |
| P3 · CODELAY phantom preference inside W | SUPPORTED | 0.36% | 0.21% | 0.27% |
| P4 · maximum absolute prediction error | REFUTED | .999 | 1.000 | 1.000 |

At ρ=.5, R=3, A2 favored the designated phantom in **1,000/1,000** units versus a registered prediction of **0%**. The independent recount confirmed the discrepancy. [RESULTS.md](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/ratio_sweep_20261118/out/main_v2_20261119/RESULTS.md)