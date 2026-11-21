# 统一协方差 Γ+u·Π_lo 前瞻检验：SBL 与 CSTATE 两条管线

## Goal
在新帧上前瞻检验候选统一模型 Γ_U = Γ + u·Π_lo：同一份协方差在 EM-SBL 中救回精确 Γ 的反转，在 CSTATE 中保持 `CODELAY`
对幻影的压制。冲刺主线 1（解决"拼凑"，第 4 句）。Eric 2026-11-19 批准（"Yes, run it"），冻结与预算由 Claude 代办。
[协议草稿](research/protocol-DRAFT.md) · [重放卡](../../../research-assets/res-20261119-02.md)

## Requirements
- 两条管线的新臂按协议草稿 §1、§3 实现；冻结源码只读，新代码放在 `experiments/unified_cov_prospective_20261119/`。
- 冻结前新帧（4400–4599，或协议 §2 规则选出的整块）保持盲：第一阶段只用旧键与 smoke 键。
- deinlab 只用 CPU，单线程，≤ 32 进程，tmux `g_unified`；第一阶段 ≤ 3 核时，主跑 ≤ 25 核时。
- results.json 带 `_argv` / `_config`；原始行留在 deinlab，本地只存小结果与 MD5。

## Acceptance Criteria
- [ ] 第一阶段：G1–G3 全部通过并留存凭据；杠杆读数与成本预估写入执行记录；协议仍标 DRAFT。
- [ ] 冻结：Astra 评审的 blocking 意见已处理，判定代码在合成输入上测过并提交。
- [ ] 主跑：按冻结判定输出 V1–V4 与统一结论，不重标。
- [ ] 三层结果卡（draft）、STATE 登记、过程日志更新；res-20261119-02 的更正已显式写入。
