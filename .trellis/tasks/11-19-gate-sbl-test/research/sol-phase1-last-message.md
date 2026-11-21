Phase 1 committed as `d3e37f5a`. The protocol remains a draft and all fresh frames remain blind.
Local and deinlab audits found prior SBL calibration on 6000–6099. The selected SBL block 5800–5999 and MIXED8 block 1600–2199 passed on both hosts.

| G1 | G2 | G3 | G4 | G5 |
|---|---|---|---|---|
| R0 and S-lo matched on 20 keys | Byte-identical on 20 SBL keys and 20 MIXED8 frames | 24 grids, 1,452 blocks matched | 12 smoke keys reproduced exactly | 187 of 576,702 legal trials fired across 9 frames. All 20 output rows matched CD byte for byte. |

Leverage: paired 95% half-width of **0.625 percentage points** at 2,400 keys, projected to **0.442** at 4,800.
Cost with the 1.3 multiplier: SBL **22.20 / 11.10 core-hours** at 4,800 / 2,400 keys. MIXED8 **0.253 core-hours**. Selected total **11.35 / 25 core-hours**.
Phase 1 used **0.461 core-hours**, including retries. All **11 synthetic verdict tests** passed.
Appendix A records the frame fallback, projector equality tolerance, exchange identity check, 74-frame pass minimum, and resolved integration defects. [Protocol](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/gate_sbl_test_20261119/PROTOCOL.md)
model: `gpt-6.2-sol`