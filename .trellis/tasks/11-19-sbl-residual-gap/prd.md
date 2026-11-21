# SBL 剩余差距检验：U2 与标量之间 2.6 pp 来自 EM 封顶还是细化

## Goal
拆开 res-20261119-03 中 U2 与标量 R0 之间剩下的 2.6 pp：来自 EM 对可分辨模罚得过重（K 臂封顶），还是来自细化阶段（M 臂
换成标量细化）。服务冲刺主线 1（方法层收口）。Eric 2026-11-19 选择（"SBL gap test"）。[协议草稿](research/protocol-DRAFT.md)

## Requirements
- 复用 `experiments/unified_cov_prospective_20261119/` 的 SBL 实现；新代码放在 `experiments/sbl_residual_gap_20261119/`。
- 新帧 4600–4799 在冻结前保持盲；第一阶段只用旧键（4400–4599 及更早）和 smoke 键。
- deinlab CPU，≤ 32 进程，tmux `g_gap`；第一阶段 ≤ 1.5 核时，主跑 ≤ 15 核时；results.json 带 `_argv` / `_config`。

## Acceptance Criteria
- [ ] 第一阶段：G1–G3 通过，有凭据；判定代码有合成测试；成本预估；协议仍为 DRAFT。
- [ ] 吸收 Astra 评审中的 blocking 意见后冻结；主跑；冻结判定不重标。
- [ ] 独立核对、draft 卡、STATE、日志。
