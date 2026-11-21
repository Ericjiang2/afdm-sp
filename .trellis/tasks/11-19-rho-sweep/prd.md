# ρ 扫描：CODELAY 是否让系统用更低的导频比（含 U ρ=.3 穿越点补齐）

## Goal
检验 `CODELAY` 的增益是否随导频比 ρ 降低而增大、最优 ρ 是否低于基线（冲刺主线 3，连接第 1 句动机）。顺带补齐 Stage 3
U、ρ=.3 的左截断穿越点。Eric 2026-11-19 批准（"直接做"）。[协议草稿](research/protocol-DRAFT.md)

## Requirements
- 复用经门控的 F0/A2/CD（`experiments/unified_cov_prospective_20261119/cstate.py` 与 Stage 3 管线）；新代码放在 `experiments/rho_sweep_20261119/`。
- 新帧在冻结前保持盲；deinlab CPU，≤ 32 进程，tmux `g_rho`；第一阶段 ≤ 1.5 核时，主跑 ≤ 10 核时；results.json 带 `_argv` / `_config`。

## Acceptance Criteria
- [ ] 第一阶段：门控通过、穿越点与判定代码有合成测试、杠杆与成本读数；协议仍为 DRAFT。
- [ ] 吸收 Astra 评审的 blocking 意见后冻结；主跑；冻结判定不重标。
- [ ] 独立核对、draft 卡、STATE、日志。
