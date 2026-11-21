# TCOM channel-estimation CRB reference (ECRB family) for F0+CSTATE

## Goal

补齐 TCOM 三层参照中最后缺的一层：信道估计误差的 Cramér–Rao 类下界，并与 F0（导频估计、最终估计）和 B = F0+CSTATE
最终 refit 的实际信道 NMSE 对比。冻结规则见 `protocol.md`。

## Requirements

- 界的族（用户决定 2026-10-16）：Van Trees BCRB 在本生成器下不适用，改用 ECRB 族——按帧条件 CRB（genie 时延、P = 8 已知）
  再对信道律求平均：MCRB（主下界）、DA-CRB（真数据已知、逐帧）、PI-CRB（导频信息，数据当高斯干扰）；
  完整 Slepian–Bangs GD-CRB 只在子集上报告。
- 场景与系统沿用 P1：gen_fixed 场景 U、G，ρ ∈ {.3, .5}，SNR 4.5–8.0 dB，N = 1024，QPSK，LDPC (3,6) n = 2048，σ² 已知。
- 推导先过一次 Codex（数学设计，按用户分工）；代码用数值恒等 gate 验证，不另做 Codex review。
- 每次正式运行前后各 commit；结果 JSON 带 `_argv`、`_config`；rows 留在 deinlab，本地只存小文件与 md5。
- 远程只用 CPU，`/data/guoyikun/` 下落盘，tmux `g_*`，整机至少留 16 核。

## Acceptance Criteria

- [x] 协议（含推导）经 Codex 一次审阅并经用户批准后冻结 commit。
- [x] Gate G1–G8（G7 首次失败 → 修订 A1 后通过） 全部通过并 commit（任何一条不过即停、报告）。
- [x] 正式运行结果写成 draft 卡 `res-YYYYMMDD-NN`，按协议 §5 给出标签。
- [x] STATE.md 与 research-assets 索引同步更新。

## Notes

- 父任务 09-22-tf-production-gap-audit；前一子任务 10-15-tcom-reference-frame（已归档，P1/P2 卡已验收）。
- 之前的信息论界过松（res-20261014-03、res-20261015-01），本任务只做估计误差界，不再做容量类界。
