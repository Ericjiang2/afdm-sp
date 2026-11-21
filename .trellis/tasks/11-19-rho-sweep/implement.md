# Implement
1. **Phase 1 (Sol, ≤ 1.5 core-hours).** Fresh-block audit; grid extension; G1–G3; crossing and verdict code with synthetic tests;
   leverage from old Stage 3 rows; cost. Commit; DRAFT. In parallel, Astra runs a read-only design review.
2. **Freeze (Claude).**
3. **Main (Sol).** One chain, cap 10 core-hours; frozen verdict; commit.
4. **Report (Claude).** Independent check, card, STATE, log.

**2026-11-19 — Phase 1 complete (Codex, gpt-6.2-sol).** The [experiment draft](../../../experiments/rho_sweep_20261119/PROTOCOL.md) records the audit, G1–G3 receipts, synthetic crossing/verdict tests (21 passed), and cost projection. Archived overlap rejected frames 5000–5399, and the local and deinlab scans selected 5400–5799. Phase 1 used only archived and smoke keys. Old Stage 3 frames give ρ=.30 minus .50 crossing-gain changes of +1.296 dB for CD/F0 and +0.511 dB for CD/A2, both with an unbounded upper interval endpoint. The full 62,400-key grid projects to 8.37 core-hours with margin. The first worker launch stopped at initialization and the retry passed within the Phase 1 cap. This delivery follows the original Phase 1 draft at `4a6a1836`. The later Phase 1b redesign, protocol freeze, and fresh-frame run remain pending.

**2026-11-19 — Phase 1b complete (Codex, gpt-6.2-sol).** [Draft §7](../../../experiments/rho_sweep_20261119/PROTOCOL.md) adds P1–P3, separate exploratory contrasts and mechanism readouts. All 23 synthetic tests, 32 repeated smoke keys and 1,976 archived trigger replays passed. The 400- and 600-draw interval half-widths are unbounded for the archived contrasts, including the two-ρ P3 proxy. Retained 5400–5799 under the 10 core-hour cap because the full grid projects to 8.314 core-hours at 400 frames and 12.472 at 600. Phase 1b used 0.540 core-hours. The selected frames remain blind, and the draft awaits freeze.

**2026-11-19 — Phase 2 complete (Codex, gpt-6.2-sol).** The frozen main run finished with `DONE`, 62,400 validated keys in 24 shards, and 6.4943 core-hours. Freeze `87e7fd2c`, header correction `84960739`, and producing glue `7c7c3e4d` are recorded in the run configuration and producing commit receipt. [Frozen results](../../../experiments/rho_sweep_20261119/out/main_20261119/RESULTS.md) report P1 supported (+1.261 dB), P2 supported (−1.186 dB), and P3 ahead (+1.139 dB). The raw shards remain on deinlab at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/`. All 24 shard SHA-256 digests were verified before transfer, and the [MD5 manifest](../../../experiments/rho_sweep_20261119/out/main_20261119/REMOTE_ROWS_MD5.txt) records each raw file. Phase 2 ends with the results and provenance receipts.


## 关闭说明（2026-11-19，Eric 在收官时接受）
结果见 res-20261119-06 与 research/mechanism-readout-20261119.md；加 TRUE_GEOMETRY 参照臂属于开放项。
