**Phase 1 committed as `8c92399c`.** The protocol remains a draft.
**Fresh-block audit.** Archived P1 keys overlap 5000–5399. Local and deinlab scans cleared 5400–5799. Both blocks stayed blind.

| Gate | Result |
|---|---|
| G1 | Passed. F0/CD matched 12 Stage 3 keys, and A2 matched eight split-prospective keys. |
| G2 | Passed. All four new ρ values exercised both trigger and bypass paths. |
| G3 | Passed. All 32 smoke keys reproduced. All 21 synthetic tests passed. |

**Old-frame leverage.** From ρ=.50 to .30, CD gained **+1.296 dB** versus F0 and **+0.511 dB** versus A2, with 95% bounds [0.682, +∞) and [0.311, +∞). Finite crossing half-widths were 0.034–1.540 dB. U/.30 CD was unbounded. [Readout](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/phase1/leverage.json)
**Grid and cost.** Six ρ values × 13 SNR points × two scenarios × 400 frames = 62,400 keys. Projected **8.37 core-hours** with margin. Phase 1 used under 0.53 core-hours, including the worker initialization retry.
**Draft changes.** Selected the next block, corrected the U/.30 crossing description, and specified censoring, ties, logging, and timing. Phase 1b remains pending. Confirmed `model: gpt-6.2-sol`. [Protocol](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/PROTOCOL.md)