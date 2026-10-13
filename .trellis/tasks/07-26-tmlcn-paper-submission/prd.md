# tmlcn-paper-submission

## Goal

TMLCN 论文投稿收尾（research parent）。科学问题：1041-param learned proposal head 严格超越 classical joint OMP+MP-BP 的主张链是否完整、可审计、可投稿？

## 背景

- 现行稿：`paper-tmlcn/`（分支 `trans/tcom-main`）。
- 已接受证据：见 `research-assets/index.md`（res-20260509-01/02、res-20260516-01、res-20260610-01、res-20260613-01）。
- 当前 blocker：`paper-tmlcn/PAPER_CLAIM_AUDIT.json` 为 2026-05-16 版，verdict=WARN（Fig.3/Fig.5 数据刷新后未重跑）；2026-07-26 已准备零上下文重审 bundle `_claim_audit_bundle_20260726/`。

## Requirements（2026-07-26 审计裁决后更新，用户已确认）

- **叙事手术**（审计 §11 蓝图）：headline 重新归因（部署 ≥87% / 先验 ≤10% / 白化 3.4% / 学习 0）；
  achievable-Λ 为唯一 innovation 核心；学习降为 tested-and-null；kill list（§9 K1–K10）全部执行；
  措辞按 §7 红绿灯；venue TMLCN → **TCOM regular**，标题禁 learned/neural。
- **主线实验闭合**（children）：E1 LDPC（最先，可证伪）→ E2 firm-seed 基线 → E6 Λ-cost dump；E3 可选；E4/E5/E7/E8/E9 推迟。
- 审计报告存档：`~/Downloads/AFDM_claim_reconstruction_audit_20260726_app-ans.html`（评审对象为 `_claim_audit_bundle_20260726/`）。
- 终稿前重跑 paper-claim-audit（对重写后的稿），citation-audit / kill-argument 按需。
- 边界：新增实验一律走 child task；投稿动作永远由用户执行。

## Acceptance Criteria

- [ ] PAPER_CLAIM_AUDIT verdict = PASS（非 stale），audited hashes 对应当前稿
- [ ] headline 数字与 asset cards 一致（−37.74/−40.15/−37.59%、−85.71%、零错 claim、−35.7/−28.9%）
- [ ] 用户确认投稿（外部提交是 human gate，不得自动执行）

## Notes

- Research parent：implementation child 完成不等于 parent 完成；关闭需用户显式验收（见 `.trellis/spec/research-protocol.md`）。
