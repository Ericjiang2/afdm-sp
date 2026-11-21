# 执行计划：SBL 谱分解检验

分三个阶段，中间设两道关卡。分工：Sol 执行；Claude 写协议、预测和报告；另一模型做设计评审；Eric 冻结并验收。

1. **第一阶段（Sol）**
   - Implement the Phase 1 arm dispatch, archive validation and receipts in the new experiment directory. Check the main-key allowlist before any receiver work. [Brief](research/codex-sol-phase1-brief.md) · [Design](design.md)
   - Run `ssh -o ConnectTimeout=15 deinlab true` for reachability. Run G2 synthetic, G1 reference replay and G2/G3 smoke via `g_spectral` on deinlab. Record exact parity, construction errors, pruning/reuse checks and timing-stripped equality. Apply the defect rule in the brief.
   - Use the smoke timings and the join schedule to project cost. Write the draft revision log and the gate and budget receipts. Check the staged diff for task scope and small evidence files before the HEREDOC commit. Append the dated Phase 1 execution record here and stop with the main run and freeze pending.
2. **关卡 A（冻结）**
   - Claude 核对 Sol 的修订和成本；
   - 另一模型（Astra 只读，或 Eric 转 Gemini）简短评审设计与判定规则；
   - Claude 把预测记入预测台账；
   - Eric 冻结并定成本上限。
3. **第二阶段（Sol）**：主跑 → 汇总 → 生成回执，并在 STATUS 写 DONE 或 STOPPED。
4. **关卡 B（报告）**
   - Claude 按三层报告：观察、冻结判定、未检验解释；
   - 写 draft 结果卡，给预测打分，更新 STATE 第 1 项；
   - Eric 验收。

回滚：本实验只读冻结源，只新增文件，不需要回滚步骤。

---

**2026-11-19 — Phase 1 complete.** `gpt-6.2-sol` ran the gates on deinlab in `g_spectral` with 12 CPU workers and one numerical thread per worker. The final attempt passed G1 on 20/20 keys for all three references, G2 on synthetic inputs and all 12 smoke keys at both budgets, and G3 on both runs of every smoke key at both budgets. The forced synthetic fixture exercised active-set pruning. The spectral fits on the 12 smoke keys retained their EM active sets. Verified the 24 immutable E-3c shards and the required fields in all 3,600 reference rows, so join the 100-iteration R0/R1/R2 outcomes and charge T0's live R1 SBL fit once. The first smoke timing replicate gives 17.04 projected core-hours after the 1.3 multiplier, below the suggested 30 core-hour cap with all 600 extended keys on frames 4000–4049. Timing covers shared preparation and the scored receiver. The inclusive [.25, .75] census is 412/7,542 (5.46%).

The SSH upload operation failed before execution. Transferred the four files over SSH exec and verified their remote SHA-256 hashes. The task DRAFT gained the Astra-reviewed §7 in `5c56322e` during attempt 01, which passed. Carried it into the experiment DRAFT, added the zero-variance census and synthetic check, and reran under attempt 02. The smoke outputs agreed across attempts after removing timing fields. The authoritative receipts are in `experiments/sbl_spectral_split_20261119/out/phase1_20261119_attempt02/`. Both attempts and the attempt 01 source snapshot remain under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_spectral_split_20261119/out/`. The committed MD5 receipt identifies the final raw rows. Phase 1 ended with the protocol in DRAFT and the main run pending.

**2026-11-19 — Phase 2（主跑；记录由 Claude 补写）。** 启动器与汇总代码在主跑前已提交（`856e8736`，含判定逻辑的合成单元测试）；冻结的三个源文件相对 `2d4c660b` 没有改动。主跑在 deinlab 上完成，1200/1200 键，12.07 核时（上限 30），`STATUS` 为 DONE。Sol 下载结果后、提交前因 Codex 工作区额度耗尽而中止，于是由 Claude 核对后提交：用帧错数重算 G、s、t、f_lo、Δ_lo，与 RESULTS 一致。冻结判定见 [RESULTS](../../../experiments/sbl_spectral_split_20261119/out/main_20261119/RESULTS.md)，结果卡为 res-20261119-02。


## 关闭说明（2026-11-19，Eric 在收官时接受）
结果见 res-20261119-02（重放），已由 res-20261119-03 前瞻复现；无未了结项。
