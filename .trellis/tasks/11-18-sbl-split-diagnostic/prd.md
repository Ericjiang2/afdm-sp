# SBL 接口表示不变性与支撑压缩：旧键诊断

## 背景
- STATE 研究第 1 项：SBL 排序反转的领先候选是检测器增益接口，仅有探索性证据。
- 11-18 草案 v2（`.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md`，以下称"草案"）
  决定先用旧键做第 1 阶段诊断，再决定是否设计新帧前瞻确认。草案是本任务的设计文件（问 A、问 B、结论类别、预测、主张上限都以它为准）。
- 父任务：`09-22-tf-production-gap-audit`。

## 目标
1. 问 A：在物理 H 与诱导先验严格匹配的精确均匀复制（k = 2）下，`fixed`、`point`、`joint`、`eG` 四种下游接口各自是否表示不变。
2. 问 B：在自然 SBL 输出上，支撑压缩（`merge_atoms`）改变了多少物理算子，合并效应在 `joint` 下是否超出 `fixed`，且标量上游大于完整上游。
3. 按草案第 3 节预先写死的类别给出"继续 / 停止并写退路 / 不明"。

## 约束
- 分工（Eric 2026-11-18）：Sol（Codex `gpt-6.2-sol`）执行；Eric 原话"跑第 1 阶段旧键诊断，如果简单你就直接跑了"。Claude 评估后认为不简单
  （需合并三套现有代码路径、过门控、远端运行），改为交 Sol 执行。每次 `codex exec` / `resume` 显式写 `-m gpt-6.2-sol`。
- 零新帧：只用三模式试跑的 200 个保存键（帧 9100–9149）与已保存的上游输出，不重拟合 SBL，不扩大样本。
- 复用现有代码（`experiments/sbl_freeze_replay_20261020/representation_probe.py`、`gram_block.py`、`gram_cohort.py`，
  `experiments/sbl_three_mode_20261020/driver.py`，`experiments/slot_mismatch_20261019/sm_driver.py::merge_atoms`），不改冻结源；
  遵守 `FROZEN_DEPENDENCIES.md`。新代码放 `experiments/sbl_split_diagnostic_20261118/`，输出放其 `out/`。
- deinlab 上槽位失配主跑正在用 24 个工作进程：本任务最多 8 个单线程进程，CPU only。
- 结果全部是旧数据诊断，不能写"统一""确认"；不改骨架、不改已接受卡。

## 验收
- 门控全过；问 A、问 B 的读数表；按草案类别给出结论；Claude 的草案预测打分（写在本任务结果文件里，不写入预测台账，因为未预注册新帧）。
- 提交后停下，由 Eric 决定是否进入第 2 阶段。
