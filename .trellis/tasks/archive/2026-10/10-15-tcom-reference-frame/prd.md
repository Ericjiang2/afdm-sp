# TCOM reference frame for F0+CSTATE (P1 confirmation, P2 baselines)

## Goal

给 F0+CSTATE 主线补齐 TCOM 论文需要的参照：在修正后的生成器上做预注册的多 SNR 新确认（含 true-H 和强前端对照），
再加一个已发表的 SP-AFDM 基线（Zheng 2025）和嵌入导频对比。冻结规则见 `protocol.md`。

## Requirements

- S0：生成器缺陷 D1–D3 以 opt-in 开关修复；开关全关时与冻结生成器逐比特一致；不修改任何冻结文件。
- P1：协议 §3 的设计（2 场景 × ρ{.3,.5} × 8 SNR × 2000 帧；F0、B、LOCAL、C=F1、D、A3），判定按 H1–H4。
- P2a：Zheng 2025 先在自身设定过 G-Z1–Z3，再移植（Z-faithful、Z-adapted、Z-turbo），判定 H5。
- P2b：主场景 EP 不可行的解析说明；缩小时延场景 S 的 goodput 对比，判定 H6。
- 每个阶段跑前、跑后各 commit；结果 JSON 带 `_argv` 和 `_config`；rows 留在 deinlab，本地只存小文件和 md5。
- 算力合计不超过 50 core-hours（CPU）。

## Acceptance Criteria

- [x] S0 gate G-S0a/b/c 全部通过并 commit。
- [x] P1 按冻结规则给出 H1–H4 判定，并写出 draft 结果卡。
- [x] P2a 复现 gate 的结论和 H5 判定写进结果卡。
- [x] P2b 解析结论和 H6 判定写进结果卡。
- [x] P1 的 H1 若 FAIL：停止，不进入 P2，报告给用户。（未 FAIL：INCONCLUSIVE，用户决定继续）
- [x] STATE.md 和 research-assets 索引同步更新。

## Notes

- 用户决定（2026-10-15）：F0+CSTATE 为 TCOM 主线；§9 的 D1–D7 全部按建议采纳。
- Zheng 2025 GLOBECOM 全文由用户下载到 papers/；到位前，P2a 只能按预印本加标准 MP 实现。
