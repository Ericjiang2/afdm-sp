# Stein 闭合估噪的端到端检验

Eric 2026-11-21 决定"冻结端到端检验"。外部候选三的估噪公式在存档触发帧上合并判据成立，但偏差随 SNR 单调变化（[零成本读数](../../../experiments/stein_sigma2_readout_20261120/READOUT.md)）。

## Goal
在 res-20261118-05 的同一批 1,000 帧上，比较 Stein 估噪与已知噪声、SF、DD 在 FER = 1% 处的穿越点。

## Acceptance
- [ ] 冻结协议与门槛：[PROTOCOL.md](../../../experiments/sigma2_stein_20261121/PROTOCOL.md)、`out/gate.json`。
- [ ] 无人值守运行完成（DONE），结果按冻结判读报告，预测打分。
- [ ] 价值判断（是否进论文、是否值得写结果卡）由 Eric 定。

## 关闭（Eric 2026-11-21："前面的都可以停了"）
- 结果：Stein 穿越点 5.46 dB，对已知 σ² +0.31 [0.17, 0.48]（P1 不确定），好于 SF 0.93 [0.65, 1.39]（P2 BETTER）。
- 留下的东西：`experiments/sigma2_stein_20261121/`（协议、门槛、代码、READOUT、结果 JSON）；行文件在 deinlab 同名目录，MD5 见 `out/main/REMOTE_ROWS_MD5.txt`。
- 未了结：暂不成卡；若论文写未知噪声一节再决定是否成卡。

## Out of scope
不改原 sigma2_dd 实验与冻结证据；不做盲选径（公式 2）。
