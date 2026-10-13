# Task Plan — "为什么要学" 裁决实验 (2×2 ablation, t=0 one-shot)

> **承重 / 最高优先级实验** (Conclusions §11, Architecture §VII-c). 一票决定论文是
> 英雄版 (head 主角 → TWC/JSAC) 还是理论版 (Λ 主角, head 降旁证 → TSP).
> 全程冻结 **t=0, 不开 turbo** (Conclusions §3 修正: head 的真贡献是进迭代环前、
> 满功率有色干扰下的一次性 support 检测).

## STATUS (2026-06-09) — Phase 1-5 跑通, C1 诊断完成, firm-up 进行中
box 已恢复, 全程**远程 deinlab** (conda AFDM). Phase 0-4 ✓; Phase 5 ranking/recall 在 smoke 上跑通 + C1 诊断完成.
**关键结论 (smoke→C1 sweep)**: C1 **活, regime-dependent** — 白化在 mid-SNR(10-15) colored-干扰主导区真有价值
(Δ_evid +.08~.19, Δ_whiten +.16~.28); 低 SNR 噪声主导→白化无关; SNR=20 病态角(C≈(1-ρ)HH^H)证据不稳.
C2 hero 干净: 良态区 head ≤ genie-Λ_FINE, 阶梯 white_Λ<geom<head<genie_Λ. 早前 SNR20 单 cell "证据冗余"
是踩病态角误判. **现 firm-up**: 2000帧×SNR{10,15,20}×ρ0.5×3-seed (canonical_grid s07/08/09), tmux g_firmup.
代码: decision_{harvest,metrics,review,bound,c1_sweep,firmup}.py (远程). 详 findings.md/progress.md 6-09 段.
RESUME: `! ssh deinlab hostname`; firm-up 结果 `outputs_decision_firmup/firmup_summary.json`.
⚠️ 本地 `mp_detect_bp_torch.py` 是 shim, 勿 scp 到 remote.

## 唯一问题
head (1041-param scorer) 凭什么比 "几何先验 + 白证据" 的确定性组合更好?
判决主对手 = **(E0,P1) white-Λ 强手调基线**, 不是纯几何.

---

## 探测器阶梯 = 2×2 消融 + 3 额外点 (载重件)

| 先验 \ 证据 | E0: 白 MF `|φ_i^H r|²` | E1: 白化 MF (genie C) `T(φ_i)` |
|---|---|---|
| **P0: 平** | (E0,P0) = 白 MF = OMP 选择量 = **地板** | — |
| **P1: 几何 π_i** | (E0,P1) = **white-Λ (判决主对手)** | (E1,P1) = **genie-Λ = 可达边界** |

额外 3 点:
- **pure-geometry** (P1, 无证据): 对每个已检高增益主瓣确定性补 (0,±1) 邻居 (最朴素手调规则).
- **(E1′,P1) realizable-Λ**: genie C → OMP-once 估的 `Ĉ⁰=(1-ρ)σ²Ĥ⁰Ĥ⁰ᴴ`. 一格干掉两个 gate.
- **head**: 1041-param `CandidateActiveRelationHead` logits.

**决定性量 = [head − (E0,P1)]** = head 唯一可能凭"学"挣到的 (白化+工作点相关摊销).
- head ≈ (E0,P1) → 学习无贡献 (理论版).
- head ≈ (E1,P1) ≫ (E0,P1) → head 成功摊销了闭式算不出的白化 (英雄版).

---

## Phases (动手顺序: 最便宜的决定性结果先出)

- [x] **Phase 0 — Lock scope & config** ✓ (2026-06-06). 决策见 Decisions Log.
- [x] **Phase 1 — Logging/harvest.** ✓ `decision_harvest.py` 远程跑通 (smoke 150/600/2000帧).
      每帧 dump: u,v,cand_cols,y(genie missed), T_genie/q_genie, T_white/q_white, white_mf,
      bin_id, dl_nn/dk_nn/g_nn(可观测条件), genie_gain_sq, seed.
- [x] **Phase 2 — genie-Λ + 退化 sanity.** ✓ self-test PASS: Prop.1 (C→σ²I ⇒ 白化统计≡白MF) +
      Cholesky vs 显式逆 max|dT|=3e-14.
- [x] **Phase 3 — 校准.** ✓ coarse 4-bin + **fine 层次 prior** (dl,dk,gain-tercile, held-out, shrinkage).
- [x] **Phase 4 — 5 scorers 插件.** ✓ white_mf/white_Λ/pure_geom/genie_Λ(coarse+fine)/head, 共用池.
- [~] **Phase 5 — Ranking + recall (DECISIVE).** smoke + C1 sweep 完成 → C1 活 regime-dependent, C2 hero.
      **firm-up 进行中**: 2000帧×SNR{10,15,20}×ρ0.5×3-seed. 主指标 rec@1 (rec@4 饱和已弃).
      新发现: 主指标须 rec@1 (rec@4 被几何饱和); 强基线是 pure_geom/genie_Λ_FINE 非坍塌的 white_Λ.
- [ ] **Phase 6 — BER gap 分解 (量化/说服 reviewer, 非决策).** 同下游, 只换 scorer.
      阶梯 OMP ≤ white-Λ ≤ head ≤ genie-Λ ≤ oracle ≤ PCSI. Clopper-Pearson.
      拆 [head−Λ] / [Λ−oracle] / [head−(E0,P1)].
- [ ] **Phase 7 — 两个控制 (便宜且杀伤力大).**
      ρ-sweep (≥3 pilot 功率比): head 优势随 ρ↓ 增大, ρ→1 趋 0 (SP 制造 gap 的证据).
      近整数多普勒 (小 a_i): 泄漏→0 ⇒ head 优势应消失 (证明抓的是泄漏几何).
- [ ] **Phase 8 — Verdict & paper fork.** 应用判决规则 → Architecture §6 分叉.

---

## 判决规则 (直接接 Architecture §6)
- **PASS (英雄版)**: ground-truth recall & τ-vs-Λ 上 head 显著 > (E0,P1) (配对检验, CI 不重叠),
  且 BER 上 [head−Λ] 小、[head−(E0,P1)] 实质为正 → 完整 C1–C3, head 主角.
- **FAIL (理论版)**: head ≈ (E0,P1) (CI 重叠) → Λ-理论为主, head 降"简单达成器".
- **关键判别**: head 必须打过 **(E0,P1)** 强基线, 不只是纯几何. 只打过纯几何却平 (E0,P1)
  → 诚实部分结果: "只需几何+白幅度两样, 不需要学".

---

## 固定配置 (待 Phase 0 确认)
N=1024 · M(pool)=48/96 · P_path=8 · K_add=4 · k_leak=2 · **t=0** · SNR∈{15,20,25} dB ·
3-seed pool · ranking 指标 ≥2000 帧/cell · BER 跑到足够错误事件 (高 SNR 1e4–1e5 或自适应停).

## Open Decisions (Phase 0) — RESOLVED 2026-06-06
1. ✓ **Ranking-first 决定性切**: 先跑 Phase 1-5, 拿 head vs (E0,P1) 判决后再决定是否上 BER.
2. ✓ **全程远程 deinlab**: 所有 phase 在 deinlab 跑 (code dir `/data/guoyikun/00inbox/AFDM-channel-estimation/`).
3. ✓ **3-seed pool**: headline τ/recall 统计基于 3 个 retrain seed 的 head.
4. ✓ 语言 = Python; 候选池 = 现有 pilot-MF top-M (固定, 5 scorer 共用).

## 写作纪律 (贯穿命名)
"in-class / on-grid surrogate optimal" · 阶梯叫 "achievable bound" 不叫 oracle ·
head 是 "amortized achiever / DNN-aided hybrid" · 不让 "low-complexity"/"deep unfolding" 漏进.

## Decisions Log
- **2026-06-06 Phase 0 锁定**: ranking-first 决定性切 (Phase 1-5 先, BER 后) · ~~全程远程 deinlab~~ ·
  3-seed pool · Python · 固定 pilot-MF top-M 候选池 (head 原生, 5 scorer 共用, 不偏置对比).
- **2026-06-06 Phase 1 pivot — 改本地**: deinlab SSH 超时不可达 → 用户改"本地做"(CE conda env, torch 2.9.1).
  本地缺 3 件 (remote-only/gitignored): `mp_detect_bp_torch.py`(BP 检测器)、trained C2-rel head ckpts、
  cached features. ⇒ 本地走**自包含 CPU pipeline**: 重新 harvest cache → 本地重训 3-seed head →
  genie-Λ ladder → τ/recall. 决定**方向**有效; canonical-ckpt 权威数字待 deinlab 恢复后复现.
  `mp_detect_bp_torch.py` 用 loud-fail shim 占位 (决定性切不跑 BP); Phase 6 BER 须换回 remote 真版.
- **本地 runner**: `CE` env = `/opt/anaconda3/envs/CE/bin/python` (torch 2.9.1, numpy 2.2.6).

## Risk Register
- **R1 (oracle 泄漏)**: π/σ²_h 必须 held-out + 按 bin, 禁用本帧真实 |h_i|². 红线见 Phase 3.
- **R2 (候选池一致性)**: head 用 pre-LS pilot MF `|Φ^H y|` 建池; Λ 用 residual `r⁰`.
  须统一为单一候选池 (建议 residual-MF `|Φ^H r⁰|`, 与 Λ/OMP-greedy 一致), 否则对比被污染.
- **R3 (H_eff 体积)**: N×N×2000 帧 = 32GB 太大 → 缓存 channel_params 离线重建, 不缓存 H_eff.
- **R4 (高斯近似)**: i_d 是高斯混合非高斯; genie-Λ 用高斯 C 是近似 → head 若略超 genie-Λ
  是结果不是 bug (解析先验偏松).
