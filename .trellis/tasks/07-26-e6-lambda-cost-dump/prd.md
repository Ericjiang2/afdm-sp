# E6: Lambda-cost raw dump rerun

## Goal

把 "Λ scorer ≈1.6% receiver runtime" 从 yellow 转 green：重跑 `decision_complexity_bench.py` 并把原始输出 JSON 入库（审计 §12-E6；当前脚本在、原始输出丢失）。

## Requirements

- 重跑 decision_complexity_bench，dump 原始 JSON 到 `outputs_e6_lambda_cost/`
- 端到端同硬件含 scorer 的 receiver 计时（与 runtime_table 同口径，N∈{512,1024,2048}）
- 必须在 deinlab GPU 修复后、与历史 runtime 表同硬件执行
- 预期复现 1.6%（N=1024）/ 1.2% / 3.4%，maxTrel~1e-11 数值等价

## Acceptance Criteria

- [ ] 原始 JSON 入库并 git 追踪（.gitignore 显式 `!` whitelist）
- [ ] 复杂度句（"complexity-preserving"、1.6% 数字）转绿，落 asset card
- [ ] 若数字偏离旧值 >2×，如实记录并把论文数字改为新值

## Notes

- 0.5 天量级；与 E1/E2 无依赖。
