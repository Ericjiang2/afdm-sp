# TCOM genie-support audit: is the MCRB gap support acquisition?

## Goal

把已验收卡 `research-assets/res-20261016-02.md` 的事后分解（B 到约束 MCRB 的信道 NMSE 差距主要来自漏检的弱路径时延，
不是 refit）变成预注册结果。冻结规则见 `protocol.md`。

## Requirements

- 在 P1 帧上加 genie 支撑臂：GS-set（真时延集合）与 GS-multi（真时延多重集 = headroom A1）；Doppler 与增益用生产 refit 目标、
  检测器与译码不变，不接 CSTATE。
- NMSE 对 MCRB 用帧 0..499（与 CRB 行配对）；FER 1e-2 交叉点用帧 0..1999（与 P1 账本 B、A3 配对）。
- 复用 `experiments/tcom_channel_crb_20261016/{crb.py, p1ctx.py}` 与 headroom ladder 的 `arms.refine_fixed_delays`；冻结代码不改。
- 无新数学 → 不做 Codex 推导审阅；代码只用数值 gate（protocol §4）。
- 运行前后各 commit；结果 JSON 带 `_argv`、`_config`；rows 留 deinlab，本地只存小文件与 md5。
- 远程只用 CPU，`/data/guoyikun/` 下落盘，tmux `g_*`，整机至少留 16 核。

## Acceptance Criteria

- [x] 协议经用户批准后冻结 commit。
- [x] Gate S1–S6 全部通过并 commit `before genie-support run`。
- [x] 正式运行完成（另加事后修订 A1：GS+C 臂，A1-G1–G3 通过），commit `after genie-support run`。
- [x] Draft 卡 `res-YYYYMMDD-NN` 按 protocol §3 给出 H-S1/H-S2 判定与 H-S3 描述，与 res-20261016-02 互链。
- [x] STATE.md 与 research-assets/index.md 同步更新。

## Notes

- 父任务 09-22-tf-production-gap-audit；前一子任务 10-16-tcom-channel-crb（已归档，卡已验收）。
- headroom ladder（res-20261008-01）在旧生成器、ρ .5 上跑过 A1；本任务在修正后的 P1 生成器上重做，并加 NMSE 对 MCRB。
