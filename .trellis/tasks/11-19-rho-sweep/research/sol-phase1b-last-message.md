**Phase 1b committed as `9850943c`.** The protocol remains a draft, and the selected frames stayed blind.

| Check | Result |
|---|---|
| Archived parity | All 1,976 triggered keys matched. |
| Smoke parity and repeatability | All 32 keys passed. |
| Synthetic tests | All 23 passed. |

**Projected half-widths.** P1–P3 were unbounded at both 400 and 600 frames because of the archived SNR floor. P3 uses the two available pilot ratios with the six-ratio confidence threshold. [Precision receipt](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/phase1b/precision.json)  
**Frame choice.** Retained 5400–5799 and both SNR endpoints. The full grid projects to **8.314 core-hours** at 400 frames and **12.472** at 600, above the 10-core-hour cap. Phase 1b used **0.540 core-hours**.  
**Revisions.** Implemented paired P1–P3 verdicts with Bonferroni bounds, exploratory readouts by scenario, and mechanism readouts by SNR and pilot ratio. Confirmed `model: gpt-6.2-sol`. [Draft §7](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/PROTOCOL.md)