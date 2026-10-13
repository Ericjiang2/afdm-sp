# E2: firm-seed baseline reruns

## Goal

把旧 seed 时代（复现危机代码态）的外部/消融基线全部在 firm seed 上重跑，使瀑布图 F2 与文献 delta（vs Cao/Zheng）可进主图（审计 §12-E2）。

## Requirements

- 臂：serial（n_outer=1）、LMMSE-SP(n=1)、Cao re-OMP、OMP-(P+K)；可选 DRCE 失配演示
- 全部 seed 20260601 配对；帧/下游/预算固定
- 预期复现旧量级：serial 地板 ~4e-2、LMMSE 灾难、Cao 介于其间——若不复现，如实记录并调查
- 结果 JSON 含 `_argv` + `_config`；输出落 `outputs_e2_baselines_*/`；boundary commits

## Acceptance Criteria

- [ ] 各臂进 F2 waterfall（classical / F2P+geom / F2P+ach / PCSI + 本任务各臂）
- [ ] Cao vs F2P+ach 配对比率给出 CI（占住 §6 行 1 的文献 delta）
- [ ] 贡献 #3（OMP-once 接收机）、#12（组合 delta）、EP-不适配声明由 B 升 A 的证据落 asset card

## Notes

- 与 E1 无依赖，可在 GPU 修复后并行。
