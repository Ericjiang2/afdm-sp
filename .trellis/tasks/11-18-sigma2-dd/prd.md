# 未知噪声：判决导向 σ² 估计

## 背景
槽位失配 N 格（res-20261118-04，draft）中，单帧矩估计 σ̂² 使 B 的穿越点后移约 1 dB（DEGRADED）。这是唯一判为退化的稳健性格子，审稿人一定会问到"σ² 未知怎么办"。Eric 2026-11-18 批准做一个小实验补救。

## 目标
检验判决导向估计 `σ̂²_DD = (‖y − B(x̄)h‖² − hᴴΓ(v)h)/N`（第一轮之后更新一次）能否让 B 的穿越点回到已知 σ² 的 ±0.25 dB 以内。

## 约束
- 分工：Claude 起草协议（`research/protocol-DRAFT.md`）；Sol（Codex `gpt-6.2-sol`，每次 exec/resume 都显式写 `-m`）修订协议、实现、过门控并执行；Astra（可选）核估计器偏差；Eric 冻结、定预算、验收。
- 新帧块、预注册判定；遵守 `FROZEN_DEPENDENCIES.md`；新代码放 `experiments/sigma2_dd_20261118/`。
- deinlab 使用 CPU，单线程，tmux 会话名以 `g_` 开头，SSH 别名 `deinlab`。

## 验收
冻结协议、门控全过、三层报告、预测台账打分、草稿结果卡；由 Eric 验收。
