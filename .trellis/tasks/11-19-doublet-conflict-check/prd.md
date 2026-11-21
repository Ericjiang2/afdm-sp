# 双径冲突检验：Γ+u·Π_lo 会不会压住真实近同延双径（MIXED8 新帧）

## Goal
检验统一协方差 Γ_U 在含真实近同延双径的信道（MIXED8，.35 bin 间隔使 Π_lo 激活）上是否与 `CODELAY` 相容。这是
res-20261119-03 唯一未测的风险。Eric 2026-11-19 批准（"Run both"）。[协议草稿](research/protocol-DRAFT.md)

## Requirements
- 冻结的 MIXED8 生成器与筛查管线只读；U 的实现复用 `experiments/unified_cov_prospective_20261119/` 的构造。
- 新帧在冻结前保持盲；选 SNR 只用旧帧上的 F0、CD 与参照。
- deinlab CPU，≤ 32 进程，tmux `g_doublet`；第一阶段 ≤ 1 核时，主跑 ≤ 4 核时；results.json 带 `_argv` / `_config`。

## Acceptance Criteria
- [ ] 第一阶段：门控（CD 复现旧筛查行；U 在 τ=0 时与 CD 逐位一致；Γ_U 试验分数与暴力求解一致）、SNR 选择、成本，协议仍为 DRAFT。
- [ ] 冻结后主跑；按冻结判定输出，不重标。
- [ ] draft 结果卡、STATE、过程日志。
