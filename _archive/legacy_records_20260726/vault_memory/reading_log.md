# 论文/资料阅读记录

**最后更新**: 2026-06-06

---

## TCOM 规划参考文档 (tcom_plan/, 3 份, 2026-06-04 新增)

路径: `00_Inbox/AFDM-channel-estimation/tcom_plan/`. SP-AFDM 检测理论论文规划三件套.

### Paper_Architecture.html (Doc I — 框架/叙事)
- 主线: SP-AFDM 最优 = 联合贝叶斯/ML(不可解) → on-grid 代理把分数多普勒变 Dirichlet support
  泄漏 → 类内最优检测器 Λ → OMP=白噪声 MF 失配(SP 干扰有色非高斯) → learned head 摊销 Λ → turbo 桥.
- 章节 §I-VIII; 贡献 C1(理论 Λ)/C2(head 摊销)/C3(turbo)/C4(ISAC 可选).
- §VII-c "为什么要学"裁决 = GATE, 决定 head 英雄版(TWC/JSAC) vs 理论版(TSP).

### Theory_Detection_and_Turbo.html (Doc II — 推导)
- §IV: Λ 因式分解 `logΛ=log(π/(1-π)) + (b/(1+b))T - log(1+b)`, `T=|φᴴC⁻¹r|²/(φᴴC⁻¹φ)`.
  Prop.1 OMP=白噪声 GLRT; Prop.2 自特征↔证据 T, 对特征↔几何先验 π. 边界 PCSI≥oracle≥Λ≥head≥OMP.
- §VI: turbo 估 C_d + 残差高斯化. (Doc III §3 修正: 此部分 over-reach, 一次性 Λ⁰ 才是核.)

### Conclusions and Open Questions.html (Doc III — 决策日志, 用户标"修正视图")
- 核心修正 §3: head **不需迭代**; 真贡献 = t=0 进环前、满功率有色干扰下**一次性** support 检测.
- §11 承重开放实验(最高优先) = "head vs 手调几何 vs 白MF, 逼近 genie-Λ"裁决. → 见 task_plan.md.

→ 落地裁决实验代码锚点/红线见 `00_Inbox/AFDM-channel-estimation/findings.md` (2026-06-06 段).

---

## 已读文献

### AFDM 相关

*暂无记录*

### 深度学习接收机

*暂无记录*

### SP (Superimposed Pilot) 技术

*暂无记录*

---

## 待读文献

1. SP-OTFS 相关论文
2. EP-based detection for fractional Doppler
3. Deep Unfolding Survey

---

## 阅读模板

```markdown
## [论文标题]

**来源**:
**日期**:
**状态**: [待读/在读/已读]

### 核心贡献
-

### 方法论
-

### 与我的工作关联
-

### 关键引用
-
```