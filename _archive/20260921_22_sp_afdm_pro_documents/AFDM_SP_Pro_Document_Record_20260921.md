# GPT Pro 产出文档记录与版本索引
## AFDM-SP 项目本地研究记录

> 用途：记录本项目中 GPT Pro 产出的关键研究文档，说明各文档在研究演化中的角色、是否仍有效、是否被后续文档取代，以及本地归档时应如何使用。  
> 本记录不按“文件越新越好”简单覆盖，而按 **current / supporting / superseded / archive** 四类管理。

---

## 1. 当前 Source-of-Truth 层级

### A. 当前论文与方法主线 — Current

1. **`SP_AFDM_Paper_Design_v1(1).md`**
   - 状态：**CURRENT / MASTER PAPER BLUEPRINT**
   - 角色：当前论文总设计、最终 thesis、贡献、方法、理论命题、实验结构、claim/nonclaim、论文结构。
   - 使用：任何新会话、写稿、回复审稿人、补实验设计都应优先从这里开始。
   - 不应被旧 V4 / list / whitening narrative 覆盖。

2. **`SP_AFDM_Native_Joint_Research_Verdict_20260921(1).md`**
   - 状态：**CURRENT SUPPORTING**
   - 角色：native tensor-free joint receiver 路线形成时的研究裁决。
   - 记录：
     - 为什么终止前一条 full-physical/sparse-innovation 主线；
     - 为什么选择 tensor-free native scalar bilinear joint inference；
     - observation-unitary equivariance；
     - path contractions；
     - 小规模 hostile controls；
     - prior-art 边界。
   - 使用：追溯“为什么现在的论文是这个方法”。

3. **最新 theory chapter（如 `theory_chapter(7).pdf` 或后续更新）**
   - 状态：**CURRENT SUPPORTING THEORY**
   - 角色：AFDM/DAFT/CPP、fractional Doppler、SP nuisance、representation、risk、inference 等更完整数学背景。
   - 使用：Technical Master Document、附录、推导核查。
   - 注意 sign convention 与 native executed code 的正 chirp / 正 Doppler convention 要统一。

---

## 2. 当前最终实验证据 — Current evidence

这些不是 GPT Pro 产出，但必须与 Pro 文档绑定记录。

### `RESULTS(8).md`
- 状态：**FINAL PRIMARY PERFORMANCE EVIDENCE**
- Part B prospective study。
- 3072 fresh independent observations。
- 9696 attempts。
- 6 / 6.5 / 7 dB，每点 1024 frames。
- 主结论：
  - TF 对 EP2 / EP4 的预定义 reliability constraints 六项全部通过；
  - TF median latency 对 EP2 约降低 42%；
  - 对 EP4 约降低 60%；
  - p90 ratio 对 EP2 约 0.44–0.45；
  - 0 numerical failures。
- 这是以后论文性能数字的最高优先级来源。
- 不应再用 development-only 32-frame 数字替代它。

### `RESULTS(7).md`
- 状态：**FINAL QUALIFICATION / ATTRIBUTION EVIDENCE**
- Part A。
- 0 new radio observations，复用 E1 输入。
- 核心：
  - POINT vs FIXED clean intervention；
  - feedback removal；
  - geometry-update removal；
  - exact two-FFT/four-FFT/dense parity；
  - isolated memory；
  - baseline cost/equation mapping。
- 重要机制：
  - POINT → FIXED 大量 rescues；
  - 支持 within-batch gain-mean adaptation 的作用；
  - propagated gain variance 无一般 reliability headline。

### `TABLES.md`
- 状态：**MECHANISM TRACE EVIDENCE**
- 0 new Monte Carlo。
- 记录：
  - `Nv_h_post ≈ 0.57–0.71`
  - late output correction ≈ 1.18–1.20%
  - late reaction ≈ 0.76–0.82%
  - 每轮 startup correction 可达 order-one / 数百 %
  - POINT 仍保持明显 gain-mean movement。
- 使用：机制分析、Proposition 3/4、图 5。

---

## 3. GPT Pro 研究演化文档

### 3.1 `SP_AFDM_Paper_Level_Verdict_20260920(1).md`

- 状态：**SUPERSEDED AS MAIN LINE / IMPORTANT RESEARCH HISTORY**
- 当时主决策：
  - 不继续围着 V4/list 做局部修补；
  - 重组现有资产；
  - 选择“full physical model + sparse innovation inference”。
- 价值：
  - 第一次真正从 paper-level 而非 component-level 重构主线；
  - 对 I1 做重新解释；
  - 提出 model fidelity 与 inference sparsity 分离。
- 后续结果：
  - 该 receiver 在完整 cost 下输给 structured EP；
  - 因此该路线作为“主论文 receiver”被后续 Native Joint Verdict 正式退休。
- 使用：
  - 研究历史；
  - 理解为什么项目从 V4 转到 physical-model correction；
  - 不应作为当前论文主 thesis。

### 3.2 `SP_AFDM_Frozen_Design_20260920(1).md`

- 状态：**SUPERSEDED AS RECEIVER / SUPPORTING TECHNICAL ASSET**
- 主要内容：
  - full physical refinement；
  - Gamma identity；
  - cyclic-diagonal energy；
  - sparse innovation graph；
  - exact rowwise weak variance；
  - 强 baseline adapters。
- 价值：
  - 很多数学和代码资产仍有效；
  - physical refinement / Gamma 继续被当前 native receiver 复用；
  - baseline adaptation 经验保留。
- 后续结果：
  - staged development 证明该 receiver complete-cost frontier 不够强；
  - 不再作为当前论文主方法。
- 使用：
  - Technical Master Document；
  - supporting derivations；
  - archive，不是主稿入口。

### 3.3 `SP_AFDM_Native_Joint_Research_Verdict_20260921(1).md`

- 状态：**CURRENT SUPPORTING / MAJOR TURNING POINT**
- 触发原因：
  - 前一条 full-physical/sparse-innovation receiver 过不了 complete-cost gate；
  - structured EP 便宜；
  - PBiGaBP 显示 richer joint adaptation 但成本过高。
- 新主线：
  - tensor-free scalar parametric bilinear joint inference；
  - gain/data simultaneous adaptation；
  - no I1 warm-up；
  - no dense cavity；
  - no sparse mask/list。
- 关键理论：
  - observation-unitary equivariance；
  - exact path contractions；
  - two-FFT implementation；
  - scalar joint map；
  - repeated-delay `R` correction。
- 重要 self-audit：
  - four-FFT competent comparator 消除了“2 FFT ≈ 2× speed”伪 headline；
  - gain variance 并未显示独立收益；
  - novelty 收紧到 AFDM/SP-specific computational specialization + native coded receiver。
- 使用：
  - 当前方法为什么成立；
  - related work / novelty provenance。

### 3.4 `SP_AFDM_Native_Joint_Codex_Handoff_20260921(1).md`

- 状态：**EXECUTED EXPERIMENT CONTRACT / ARCHIVE**
- 角色：
  - 把 Native Joint Verdict 变成 Stage A / Stage B 的冻结 Codex 实验。
- 已完成：
  - 方向 gate passed；
  - 后续 native direction validation 已形成。
- 当前：
  - 不再需要执行；
  - 留作 provenance / preregistration 证据。

### 3.5 `SP_AFDM_Paper_Design_v1(1).md`

- 状态：**CURRENT MASTER DOCUMENT**
- 当前最高级别 Pro 产出。
- 内容：
  - final thesis；
  - 3 条 contribution；
  - exact receiver equations；
  - Proposition 1–5；
  - mechanism；
  - prior-art equation map；
  - complexity；
  - forbidden claims；
  - paper organization；
  - figures/tables；
  - submission evidence contract；
  - draft abstract contract。
- 以后如果有 Paper Design v2，应在本记录中显式 supersede v1，而不是静默覆盖。

### 3.6 `SP_AFDM_Paper_Design_v1_Codex_Ticket(1).md`

- 状态：**PART A/B EXECUTED CONTRACT / ARCHIVE-SUPPORTING**
- Part A：
  - 已完成，结果 `RESULTS(7).md`
  - qualification / attribution / memory / baseline map。
- Part B：
  - 已完成，结果 `RESULTS(8).md`
  - 3072 fresh observations；
  - 主论文 performance evidence。
- 当前：
  - ticket 本身不再需要执行；
  - 作为 prospective design / reproducibility provenance 保留。

---

## 4. 早期研究文档的定位

### `SP_AFDM_Research_Verdict(1).md`
- 状态：**HISTORICAL / PRE-NATIVE**
- 内容：
  - large-list premise 退场；
  - iterative-first；
  - acquisition / joint-state framing。
- 价值：
  - 记录 V4/list 为什么结束；
  - 不是当前 manuscript 的主要引用源。

### `SP_AFDM_next_chat_handoff_20260920.md`
- 状态：**OLD HANDOFF / SUPERSEDED**
- 已被本次新的交接文档取代。
- 仅保留研究历史。

### V4 / list manuscript, whitening audits, support-exchange audits
- 状态：**ARCHIVE**
- 不作为当前论文主叙事。
- 可在 Technical Master Document 中保留：
  - exact fractional path row construction；
  - conditional marginalization；
  - negative lessons；
  - claim discipline。
- 不应把旧 contribution 重新加回当前论文来“增加贡献数量”。

---

## 5. 推荐的本地目录结构

```text
AFDM-SP/
├── 00_CURRENT/
│   ├── SP_AFDM_Paper_Design_v1.md
│   ├── RESULTS_PartB_Final.md
│   ├── RESULTS_PartA_Qualification.md
│   ├── TABLES_Mechanism.md
│   └── README_CURRENT_STATE.md
│
├── 01_PRO_OUTPUTS/
│   ├── 20260920_Paper_Level_Verdict.md
│   ├── 20260920_Frozen_Design.md
│   ├── 20260921_Native_Joint_Research_Verdict.md
│   ├── 20260921_Native_Joint_Codex_Handoff.md
│   ├── 20260921_Paper_Design_v1.md
│   └── 20260921_Paper_Design_v1_Codex_Ticket.md
│
├── 02_CODEX_RESULTS/
│   ├── staged_old_direction/
│   ├── native_direction_validation/
│   ├── mechanism_audit/
│   ├── partA_qualification/
│   └── partB_submission_evidence/
│
├── 03_THEORY/
│   ├── theory_chapter_latest.pdf
│   └── future_Technical_Master_Document.md
│
├── 04_MANUSCRIPT/
│   ├── future_manuscript_draft_v0.md
│   ├── figures/
│   └── tables/
│
└── 99_ARCHIVE/
    ├── V4_list/
    ├── whitening/
    ├── support_exchange/
    └── failed_directions/
```

---

## 6. 当前证据优先级规则

遇到数字冲突时：

1. **Part B `RESULTS(8)`**  
   > Part A / direction validation / small screens / old waterfalls

2. **Part A `RESULTS(7)`**  
   > earlier mechanism screens

3. **`TABLES.md`**  
   用于机制 trace，不用于 population FER。

4. **Paper Design v1**
   - 负责 interpretation / claims / equations；
   - 不能覆盖 final raw empirical evidence。

5. 旧 Pro verdict / old manuscripts
   - 只能作为历史和 supporting derivation；
   - 不可推翻后续冻结结果。

---

## 7. 当前论文主线中“保留 / 降级 / 删除”

### 保留为 headline

- tensor-free full-fractional scalar bilinear realization；
- native coded joint receiver；
- within-batch gain/data adaptation；
- complete latency–reliability operating benefit。

### 保留但降级

- propagated scalar gain variance：
  - 算法完整性 + startup transient；
  - 不作为性能来源 headline。
- physical refinement：
  - shared infrastructure；
  - 不作为第二个独立 invention。
- LDPC feedback：
  - necessary system component；
  - prior art，不宣称新原则。
- two-FFT：
  - exact implementation detail；
  - 不作为主要速度 headline。

### 从当前主论文移除

- V4 list certification；
- support exchange；
- whitening scorer；
- large-list acquisition；
- learned head；
- sparse innovation graph；
- “gain variance caused the performance”；
- “new AMP / first bilinear AFDM”。

---

## 8. 后续待产出的 GPT Pro 文档

### 计划 1：`manuscript_draft_v0.md`

目标：
- 完整长版 IEEE Transactions 初稿；
- 先写全，后续人工删减；
- 包括 Abstract / Intro / Related Work / Model / Method / Theory / Complexity / Experiments / Discussion / Conclusion / Appendices。

### 计划 2：`SP_AFDM_Technical_Master_Document_v1.md`

目标：
- 项目权威技术底稿；
- 不限篇幅；
- 收录所有关键数学基础、证明、实现映射、证据边界、negative result、prior-art comparison；
- 用于自己学习、核公式、写附录、回复审稿人。

完成后应在本索引中加入，并将它们分别标记为：

- `MANUSCRIPT DRAFT`
- `TECHNICAL MASTER REFERENCE`

---

## 9. 本地研究日志建议格式

以后每次 Pro 产出一个重要文档，追加一条：

```text
### YYYY-MM-DD — 文件名

状态：
CURRENT / SUPPORTING / SUPERSEDED / ARCHIVE

输入：
- 使用了哪些当前证据
- 是否用了新文献/新实验

核心决策：
- 改了什么
- 保留什么
- 杀掉什么

新理论/方法：
- …

新实验要求：
- …

取代：
- 哪个旧文档 / 哪条旧结论

当前用途：
- manuscript / theory / experiment / provenance / archive
```

这样可以避免几周后分不清“哪份报告才是当前有效结论”。

---

## 10. 当前最终记录点

截至 2026-09-21：

> **Native tensor-free joint SP-AFDM receiver 已经从方向发现 → 开发 gate → 跨 SNR 独立验证 → mechanism audit → manuscript qualification → prospective Part B 大样本验证全部走通。**

当前项目不应再继续“找创新方向”。

下一步是：

> **写完整论文初稿 + Technical Master Document + 最终 novelty/related-work audit。**

若后续新实验未出现实质反证，所有旧路线均保持 archive 状态。
