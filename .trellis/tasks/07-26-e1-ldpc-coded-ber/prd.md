# E1: LDPC coded BER (paired, 3-arm)

## Goal

验证白化优势在信道编码后不消失——**唯一能证伪主 claim 的实验**（审计 §12-E1），必须最先跑；写作 §II–§V 与其并行。

## Requirements

- LDPC rate 1/2，同帧配对，三臂：classical / F2P+geom / F2P+achievable-Λ
- 固定：码、交织、seed（20260601 系）、下游接收机逐字节相同
- SNR15 为主口径（800 配对帧量级）；结果 JSON 必须含 `_argv` + `_config` 指纹
- 输出落 `afdm_sp_joint_unrolled/outputs_e1_ldpc_*/`；跑前跑后各一次 boundary commit
- 前置条件：deinlab GPU 修复（2026-07-26 记录：驱动 mismatch 待管理员重启）

## Acceptance Criteria

- [ ] coded-BER ratio(ach/geom) 给出帧级 bootstrap CI
- [ ] CI<1 → C1/C2 升满，绿灯句 "advantage survives channel coding" 解锁
- [ ] CI 跨 1 → 白化 claim 降级为 uncoded-only 限定（论文仍立，§V 语气收窄）——两种结局都必须如实落 asset card
- [ ] 结果 promote 成 `res-YYYYMMDD-NN` 卡片并更新 STATE.md

## Notes

- 有真实证伪风险；失败不是事故，是结论。禁止因结果不利而改口径重跑。
