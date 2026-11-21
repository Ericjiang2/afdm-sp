# 门控 SBL 检验：一条可辨识度规则能否取代分阶段放置（新帧配对）

Eric 2026-11-19："先冻结协议"（选择跑配对新帧检验）。前序：[门控筛查](../11-19-gate-screen/research/claude-check-20261119.md)通过，但交换一侧几乎不可能失败；决定性的问题在 SBL 一侧。

## Goal
在新帧上检验：按可辨识度门控的差模下限（Astra 规则，λ* 随阶段变化），能否在 SBL 中不劣于 S-lo，同时在交换阶段不丢掉可分辨的 0.35 bin 真双径。两者都成立，才能说"一条规则复现了分阶段放置"。

## Acceptance Criteria
- [x] 协议冻结（[PROTOCOL](../../../experiments/gate_sbl_test_20261119/PROTOCOL.md)），Astra 设计评审已并入，预测已登记，冻结提交在任何新帧仿真之前。
- [x] Sol 第一阶段：门控、成本预估、新帧审计、判定代码与测试。
- [x] 主跑与判定（冻结后不重标）；RESULTS + 结果卡草稿（等 Eric 验收）。

## Out of scope
- 不改其他臂；不扩到 P1 的 CSTATE 网格；不改骨架与已接受的卡。
