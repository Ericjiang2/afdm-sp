# 离散获取论题重估与 CSTATE 机制因子消融（E-1）

## Goal

两件交付物：
1. 把 2026-10-17 的科学重估（证据重建、方向空间、先行艺术校准、Codex 独立评估）持久化为任务研究工件（已完成：`research/reassessment-20261017.md`）。
2. 执行 E-1 判别实验：在保存的 F0 失败状态上做 2×2 因子消融（协方差 Γ 全量/对角 × 支撑交换 允许/禁止）加仅续跑控制臂，判定 CSTATE 的收益是"协方差感知的支撑决策机制"、"支撑搜索"、还是"额外编码轮"。

## Requirements

- R1 重估工件写入 `research/`，不改写任何已接受真相；引用一律给文件路径与卡片 ID。
- R2 冻结源码（`experiments/tf_geometry_reopen_20260922/`、`experiments/sp_afdm_native_joint_20260921/`、`experiments/tf_cstate_validation_20260922/`）一律不改；E-1 变体在新目录以复制加单点改动实现，并在协议中记录原文件 md5。
- R3 协方差轴的定义必须精确：仅改变几何重开打分中的 Γ（`_gamma_cross` 输出）；全量 = 生产行为，对角 = 保留对角、置零非对角。refit、检测器、译码器一律不动。
- R4 交换轴 = `max_edits`（2 vs 0），strategy 固定为 `compact`，局部 Doppler 细化保持开启。
- R5 控制臂 = 不做几何更新，仅从同一 F0 状态再跑一轮 `scalar_joint(iterations=20, damping=.3, joint)` + LDPC。
- R6 五个臂共享同一 F0 状态、同一帧集、同一预算；帧集取 P1 帧在 6.5/7.0/7.5/8.0 dB 的 F0 失败帧，四格（U/G × ρ.3/.5）。
- R7 读数：配对净救回（救回减伤害）、配对 McNemar、帧 bootstrap 95% CI、候选排序轨迹、支撑变化计数、完整单帧成本。
- R8 预注册判据 J1–J3 与 KILL 规则（见 design.md §7），先冻结后跑。
- R9 门 G1–G4（见 design.md §8）全部通过才允许解读。
- R10 行数据留 deinlab（gzip + md5 清单）；小文件回传本地并入 git；协议与代码在跑前 commit。
- R11 成本上限 16 core-hours；超限即停并报告。
- R12 结果只出 draft 卡；是否验收由用户决定；不自动改论文主张。

## Acceptance Criteria

- [ ] `research/reassessment-20261017.md` 存在且含先行艺术表与 Codex 分歧记录（R1）。
- [ ] E-1 协议冻结并 commit，含原文件 md5 与变体差异说明（R2/R3）。
- [ ] 变体模块通过 G1（full 模式与冻结原版逐位一致）与 G2（diag 断言）与 G3（确定性）。
- [ ] 五臂在同一 F0 失败帧集上完成，四格、四个 SNR 点，0 运行失败（R6）。
- [ ] G4（状态复现：F0 状态与 P1 ledger 的 B 臂触发集合一致）通过。
- [ ] 按 J1–J3 给出判定，含 CI；KILL 条件被显式检查。
- [ ] draft 结果卡写入 research-assets，STATE.md 在用户验收后才更新。
- [ ] 成本记录 ≤ 16 core-hours。

## Boundaries

- 不搜索新方法；不重开 C1 线；不动 DDST/调度/加速的 kill 结论。
- 不在本任务内做 E-2/E-3/E-4（另行立项）。
- 不把本任务结果外推到其他码、N、调制或非 genie 时延场景。
- 条件化在 F0 失败上的统计含义必须在卡片中声明（该子集不等于全帧分布）。
