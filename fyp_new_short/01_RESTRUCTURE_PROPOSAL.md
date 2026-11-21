# 短版 FYP 重构方案

> 目的：参考三篇上一届格拉斯哥学院优秀缩编（董方莹 / 吴宁宁 / 赵畅），结合你给的"脊柱"与具体反馈，重新安排 `FYP_Short_Version` 的章节、篇幅、配图与取材来源。
> 取材原则：**正文文字尽量从 `paper/`（FYP-full，最终态约 4/28，轻量润色到 5/7；已确认是 Final Year Project Report，不是 `paper-tmlcn/` 期刊版）里搬**，缺了或写得不好再自己发挥。
> 目标篇幅 ~8–10 页（三篇范文分别是 10 / 9 / 10 页）。

---

## 一、三篇往届范文的结构拆解（详细对比）

### 1.1 逐篇骨架

**① 董方莹《Semantic Encoding Based on Data Elements》（539，10 页，中英摘要 + 英文正文）**

| 区块 | 内容 | 关键做法 |
|---|---|---|
| 摘要/Abstract | 中英双摘要 + 关键词，约 1 页 | 问题→方法→**带数字的结果**（PSNR 提升 57.1%/32.1%，比 VVC 高 23.5%/11.8%）。1 段话讲完。 |
| 1. Introduction | **极短**（~半页，1 段 + 1 张系统总览图 Fig 1-1） | 只讲"为什么做"+ 给一张 roadmap 图，**不堆文献** |
| 2. Literature Review | **独立成章**，分 2.1 / 2.2 两个主题 | 2.1 现有压缩方法（缺什么）→ 2.2 光照分解（我们灵感/借鉴的那条线） |
| 3. Methodology | 3.1 Proposed Method（架构+公式 3-1…3-11）/ 3.2 Training（损失 3-12…3-15） | 方法与训练分开 |
| 4. Experiments and Results | 4.1 训练结果（表）/ 4.2 测试结果（图）/ 4.3 定量对比（图、BD-rate） | 一节内按"实验"切子节 |
| 5. Conclusion | **编号列贡献 (1)(2)(3)** | 无独立 Future Work |
| References | 13 条 | — |

**② 吴宁宁《基于多模态生理信号的人类情绪识别》（549，9 页，中英摘要 + 英文正文）**

| 区块 | 内容 | 关键做法 |
|---|---|---|
| 摘要/Abstract | 中英双摘要，**摘要里就编号列 (1)(2)(3) 主要工作** | 一上来就把三条贡献摆出来 |
| 1 Introduction | **极短**（~半页，2 段 + 技术框架图 Fig 1-1） | 相关工作只用一句带过（Katsigiannis 多模态融合） |
| 2 信号滤波算法 | 2.1 去噪算法仿真（表 2-1/2-2）/ 2.2 预处理（图） | **方法按"流水线阶段"分章** |
| 3 机器学习模型 | 3.1 特征提取与选择（表）/ 3.2 基于特征的 ML（表、图） | |
| 4 深度学习模型 | 4.1 CNN-LSTM（图）/ 4.2 Capsule（图、表） | **逐级升级**：滤波→ML→DL→胶囊网络 |
| 5 Conclusion and Future Work | 5.1 结论（编号）/ 5.2 展望（编号） | **结论 + 展望合并成一章、各自子节** |
| Reference | 9 条 | — |

**③ 赵畅《光纤分布式声学传感器的三维卷积神经网络硬件实现》（558，10 页，中英摘要 + 中文正文）**

| 区块 | 内容 | 关键做法 |
|---|---|---|
| 摘要/Abstract | 中英双摘要 + 关键词，**带硬指标**（18.3ms@13.8W，98.94%） | — |
| 第一章 引言 | ~1 页，动机 + 相关工作（融在引言里）+ **结尾用 ⚫ 项目符号列 4 条核心设计理念** | 把"脊柱/创新点"在引言结尾一次性亮出来 |
| 第二章 加速器设计 | 2.1 系统组成 / 2.2 滑窗复用 / 2.3 CSA 树 / 2.4 即时池化 | **方法按"模块"分子节**，配系统架构图 |
| 第三章 模型设计与量化 | 网络结构表 + 量化公式 3-1/3-2 | |
| 第四章 结果与讨论 | 4.1 功能仿真 / 4.2 同类加速器对比（表）/ 4.3 跨平台对比（表）/ 4.4 推理精度（图） | 一章内按"对比对象"切子节 |
| 第五章 总结与展望 | 合并成一节 | 结论 + 展望合并 |
| 参考文献 + 本科成果 | 6 条 + 会议论文 | — |

### 1.2 三篇的共性规律（这就是要借鉴的"模板"）

1. **摘要带数字、并常常直接编号列贡献**（吴、赵）。问题→方法→硬结果，一两段讲完，中英双语。
2. **引言极短（半页~1 页），不堆文献**。只讲动机 + 给一张系统/框架总览图。文献都留给后面。
3. **文献综述的处理有两种范式**：
   - **独立成章、按主题分子节**（董方莹 2.1/2.2）——最适合"现有方法→缺什么→我们做什么"的叙事；
   - 或**融进引言一句话带过**（吴、赵）。
   → 你想要"第三部分文献综述"，所以走**董方莹范式**。
4. **方法按"流水线阶段"或"模块"分章/分子节，并且逐级升级**（吴宁宁：滤波→ML→DL；赵畅：模块逐个讲）。公式编号，配架构图。
5. **结果一章内按"实验/对比对象"切子节**，每个子节一张表或一张图。
6. **结论编号列贡献；展望要么合进结论（吴 5.2 / 赵），要么省略（董）**。**三篇都没有独立的 "Discussion" 章**——机理解读都揉进结果或方法里。
7. 篇幅 9–10 页，参考文献 6–18 条。

> **对你最有用的两点**：①董方莹的"独立文献综述（按主题分子节 + 收尾点 gap）"正好是你要的第三部分；②吴宁宁的"逐级升级"叙事 = 你的脊柱（SP→OMP on-grid 基线→迭代接收机→深度学习补残差），结构天然契合。

---

## 二、当前 `00_MATERIAL_DATABASE.md` 的问题诊断

对照范文 + 你的脊柱，现版本主要问题：

1. **引言太长、把太多东西杂糅进去**。现在 1.1–1.4 里塞了 background、related work（1.2 整段）、research question、contributions、还有 error-floor 的具体数字（5×10⁻²、−11.3 dB NMSE）。范文的引言是半页、只讲动机。→ **引言要瘦身**，文献整段挪到独立的"文献综述"章，具体数字挪到方法/结果。
2. **没有独立的"文献综述"章**。你想要的第三部分（文献综述）目前是引言里的 1.2，体量和位置都不对。
3. **摘要开头那句你已经指出的问题**："传统 OFDM 必须付出高昂的 CP 开销才能勉强应对"——只说了时延，**没写分数多普勒的危害、也没写 OFDM 面对分数多普勒的具体局限**；而且**整段摘要没交代为什么用 SP**（EP 太占频谱这个核心动机缺失）。→ 见第四节重写。
4. **方法被压成一个大章（Ch.2，2.1–2.8 八个子节挤在一起）**。范文是把方法拆成 2 章、按脊柱顺序逐级展开。→ 拆成"系统模型 + on-grid OMP 基线"和"提出的接收机（迭代 + 学习头）"两章，让脊柱看得见。
5. **有一个独立的 Ch.4 Discussion**。三篇范文都没有独立 Discussion；而且你新的提纲是"结果→展望"，没有 Discussion。→ **解散 Discussion**：把承重的机理分析（95% 召回 / Dirichlet 旁瓣）并入结果，把 limitations 压进结论/展望。
6. **脊柱没有被显式点出来**。赵畅在引言结尾用项目符号一次性亮出 4 条核心理念——建议你也在引言结尾用 2 条把脊柱点出来（SP 提频谱效率但引有色干扰→迭代解决；AFDM 稀疏全分集天然 OMP，但 OMP on-grid → 分数多普勒泄漏 → 深度学习解决）。

---

## 三、建议的新结构（章节级蓝图）

> 总篇幅 ~8–10 页。每节标了：**篇幅预算 / 借鉴哪篇 / 取材来源（FYP-full 的哪一节）/ 配图表公式 / 展开还是略写**。
> "取材来源"里的 `paper/sections/SectionX.tex` 就是 FYP-full 正文，直接搬文字再压缩。

### 标题 + 作者块
- 标题用 FYP-full 的：*AFDM Transceiver Design for Underwater Acoustic Communication System*，或现材料库那条更具体的副标题（二选一，建议用学校论文册登记的官方题目）。

### 摘要（中）+ Abstract（英）+ Keywords —— ~0.8 页
- **借鉴**：吴/赵（带数字 + 编号贡献）。
- **取材**：`paper/sections/Abstract.tex`（已是好底子），**但开头按第四节重写**，补"分数多普勒危害 + OFDM 局限 + 为什么 SP（EP 太占频谱）"。
- 结尾保留三条硬结果（25 dB 降 2–3 个量级；学习头 +~2 dB / 关 61/81/98% gap；同 O(P·N²) 复杂度、~8% MAC）。

### Ch.1 Introduction —— ~0.8 页（**大幅瘦身**）
- **借鉴**：董/吴/赵的"极短引言 + 总览图"。
- **内容**：① 水声信道双弥散（时延 + 分数多普勒）→ OFDM 两难（CP 太贵 / 分数多普勒毁正交性）；② AFDM 把双弥散折叠成啁啾域稀疏信道 → 天然适配 OMP；③ 带宽受限 → 用 SP 保频谱效率（对比 EP）；④ **结尾用 2 个项目符号点出脊柱**（见下）+ 一句话研究问题。
- **取材**：`paper/sections/Section1.tex` 的 `Background and motivation`（4–71 行）——直接搬前两段，把 error-floor 的具体数字（5×10⁻²、−11.3 dB）删掉留给结果。
- **把这些搬走**：原 1.2 related work → Ch.2；原 1.4 contributions 的长描述 → 压成摘要里的编号 + 结论里的编号。
- **配图**：**Fig.1 = 系统总览图（建议你新画一张，见第六节）**。
- **脊柱项目符号（建议放引言结尾，措辞可直接用；保持一行一条，学赵畅的紧凑度）**：
  - ⚫ **用 SP 换频谱效率**：每个子载波数据+导频叠加，相对 EP 数据容量约翻倍；引入的有色数据干扰由**迭代接收机**消除。
  - ⚫ **OMP 抓不全分数多普勒**：AFDM 稀疏全分集使一次 OMP 即抓 ~95% 支撑，但它是 **on-grid** 的，漏掉的结构性 Dirichlet 旁瓣残差由**学习支撑精化头**补回。
  - （详见第八节"贡献写在哪 / 脊柱要不要用项目符号"——这两条是**动机性的核心洞见**，与"贡献/做了三件事"不是一回事，别混。）

### Ch.2 Literature Review —— ~0.8–1.0 页（**新独立章**）
- **借鉴**：董方莹 2.1/2.2（独立成章、按主题分子节、收尾点 gap）。
- **取材**：`paper/sections/Section1.tex` 的 `Critical literature survey`（74–277 行，现成的 5 段 paragraph，**直接压缩**）。
- **建议子节**（4 条线压成 2–3 个子节，每个 1 段）：
  - 2.1 AFDM 与其稀疏信道估计原语（Bemani / Benzine OMP / Yin 分数多普勒）；
  - 2.2 叠加导频与联合估计-检测（OFDM 起源 → OTFS/OTSM → SP-AFDM 的 Zheng/Cao：已确立"必须迭代"，但每轮重跑 OMP、且无学习）；
  - 2.3 稀疏 MP 检测 + 深度展开（Raviteja；Monga/LISTA；AFDM 里学习件只在检测器、没放在 OMP 支撑选择步）。
- **收尾一段点 gap**：没有任何已发表 AFDM 接收机同时做到 (a) 保 SP 帧、(b) OMP 只跑一次只迭代 LS/MP-BP、(c) 在 OMP 支撑精化步放小学习模块——本文就在这个交点。（取材 Section1 263–277 行 `Synthesis and identified gap`。）

### Ch.3 System Model and the On-Grid OMP Baseline —— ~2.0 页
- **借鉴**：赵畅"按模块分子节"；这一章负责**把两个问题暴露出来**，给后面的解法铺路。
- **取材**：`paper/sections/Section2.tex` 的前四个子节。
  - 3.1 AFDM 信号模型与 DAFT（Section2 `AFDM signal model and the DAFT`）—— **略写**，留 IDAFT(Eq.1)、y=H_eff x+n(Eq.2)、c₁=c₂=0 退化为 OFDM 一句。
  - 3.2 双弥散信道与有效信道稀疏性（Section2 `Doubly-dispersive simulator...`）—— **适度展开**：MSML 一阶建模、整数延迟/分数多普勒映射(Eq.3)、**Dirichlet 旁瓣展开(Eq.4)**（这是脊柱②的物理基础，要讲清楚：最坏 0.5 残差时两个最近 bin 各 ~41%，~28 个有效虚拟抽头）。配 **Fig.2 = Dirichlet 核幅度**（旁瓣几何）。
  - 3.3 叠加导频信号模型（Section2 `Superimposed pilot signal model`）—— **适度展开**：SP 帧(Eq.5)、导频投影(Eq.6)、**干扰方差不随 SNR 衰减(Eq.7)** → 这就是脊柱①的"有色干扰→误码平台"的来源。
  - 3.4 OMP 字典与 on-grid 性质（Section2 `Sparse-baseline OMP dictionary`）—— **略写**：字典只覆盖整数 bin、Dirichlet 展开在 OMP 之后、一次 OMP = O(P·N²)(Eq.8)。**在这里点明"OMP 是 on-grid，所以分数多普勒泄漏它抓不全"**，自然引出 Ch.4 的解法。
- **本章收尾**：明确两条待解问题——(i) SP 有色干扰造成的估计受限误码平台；(ii) on-grid OMP 漏掉的结构性分数多普勒残差。

### Ch.4 Proposed Receiver —— ~1.8 页
- **借鉴**：吴宁宁"逐级升级"（迭代经典 → 加学习头）。
- **取材**：`paper/sections/Section2.tex` 的 `Joint OMP-once + iterative LS/MP-BP receiver` / `Learned support-refinement head` / `Complexity analysis`。
  - 4.1 OMP-once + 迭代 LS/MP-BP（**主线，适度展开**）：一次 OMP 锁支撑 → 只迭代 数据相消 + 阻尼 DA-LS 增益重拟合 + 稀疏 MP-BP。讲清"为什么只跑一次 OMP"（召回 ~95%、连续两次 OMP 支撑 Jaccard>0.94、re-OMP 是 5× 常数冗余）。配 **Fig.3 = 经典框图**（`figure_a_new.png`）。
  - 4.2 学习支撑精化头（**适度展开**）：1041 参数、插在 OMP-once 与迭代环之间、对离支撑候选打分、确定性 top-K_add 追加；强调它**只补 Dirichlet 旁瓣原子、不扩字典、同复杂度类**。配 **Fig.4 = 学习头集成框图**（`figure_b_new.png`）；架构图 `figure_c_new.png` 篇幅紧可省。
  - 4.3 复杂度（**略写**）：同 O(P·N²)；比 dense LMMSE 低两个量级、比 re-OMP-per-iter 低 5× 常数；头 ~8% MAC。
- **训练 / 评测协议**：**压成各一段**（Section2 `Training` / `Evaluation protocol` / `Baseline selection`）——只留"BCE+rank-hinge、27k×4-SNR cache"和"严格配对帧、Clopper–Pearson CI、McNemar、seed 级 train/val/test 隔离"两句。细节进**附录**（见末尾）。

### Ch.5 Results —— ~2.0 页
- **借鉴**：董/赵（一章内按实验/对比切子节，每子节一图或一表）。
- **取材**：`paper/sections/Section3.tex`（四个实验现成）。
  - 5.0 仿真参数（一段或一张小表，Section3 `Simulation parameters`）。
  - 5.1 主 BER 瀑布（Exp1）—— Serial 受估计限（NMSE 冻结 −11.3 dB）；ClassicalJoint 25 dB 降 2–3 量级；学习头各高 SNR 点 −37.7/−40.2/−37.6%（p<10⁻⁶）。配 **Fig.5 = BER+NMSE**（`loop13_combined_4B_ber_mse.png`）+ **Table 2 配对 BER**。
  - 5.2 外迭代收敛（Exp2）—— **略写成几句 + 可选图**（`loop13_iter_convergence_4B.png`），证明 T_out=5 够。
  - 5.3 **支撑召回 + oracle headroom（Exp3 = 机理证据，要保留）** —— OMP-once 召回 ~95%、≥1 漏原子的帧占 67–71%（结构性非噪声）；top-P 物理支撑 oracle 上界，学习头关 61/81/98% gap。配 **Fig.6 召回**、**Fig.7 headroom** + **Table 3**。
  - 5.4 复杂度/MAC（Exp4）—— **略写 + Table 4**（Serial/ClassicalJoint/Learned/re-OMP/Dense-LMMSE 五行）。
- **机理的一句话解读**就地放在 5.3（不再单开 Discussion 章）：学习头加的原子 ≥99.4% 落在活跃路径的 Dirichlet 旁瓣 → 是"旁瓣修复"不是"噪声平均"。（取材 Section4 `Mechanism of the learned head's high-SNR contribution` / `Population-level per-candidate attribution`，**只取结论一句**。）

### Ch.6 Conclusion and Future Work —— ~0.6 页
- **借鉴**：吴宁宁 5.1/5.2、赵畅"总结与展望"合并。
- **取材**：`paper/sections/Section5.tex` + Section4 `Limitations`。
  - 6.1 结论：**编号列三条贡献**（复杂度可控的联合接收机 / 1041 参数学习头 / oracle 机理分析）。
  - 6.2 展望：多 seed 重训方差、复现已发表 SP-AFDM 基线、完整 per-path MSML 仿真器、嵌入式部署成本（延迟/内存/能耗）。limitations 压成展望前一句。

### References —— 精选 ~18 条
- 取材 `paper/references.bib` / `main.bbl`，按短版引用裁剪。

### （可选）Appendix
- **范文都没有正文外附录**（缩编进论文册一般不带附录）。建议：**不单列附录**；评测协议/字典构造/McNemar 这些细节压进正文一句话即可。若学校模板允许附录再考虑，但优先级低。

---

## 四、摘要开头重写（按你的反馈）

你的两点：(a) 原句没写分数多普勒危害 + OFDM 局限；(b) 没交代为什么用 SP（EP 太占频谱）。下面是可直接用的重写（中英各给前两段，取材并强化自 `Section1.tex` 41–54 行与 `Abstract.tex`）。

**中文摘要（开头，替换原第 1–2 句）：**

> 水声（UWA）信道同时具有数毫秒至数十毫秒的长时延扩展，以及量级达 v/c∼10⁻³、远高于陆地射频链路的多普勒，二者叠加产生严重的**分数阶多普勒**频移。这让传统 OFDM 陷入两难：循环前缀要覆盖整个时延扩展才能消除符号间干扰，在仅数千赫兹的水声带宽下要付出难以承受的频谱效率代价；而**哪怕只有零点几个子载波间隔的残余分数多普勒，也会破坏子载波正交性、引入强烈的载波间干扰，单抽头频域均衡器无法修复**。仿射频分复用（AFDM）正是为这类双弥散信道设计：经离散仿射傅里叶变换（DAFT）把每条物理时延-多普勒路径折叠为啁啾域上一个稀疏且全分集的等效信道，使基于压缩感知的 OMP 信道估计天然可行。
>
> 在仅数千赫兹的水声链路上，导频开销本身就是一阶约束。**为保住数据容量，本文采用叠加导频（SP）帧：每个啁啾子载波同时承载数据与导频能量。相比把专门资源留给导频、显著牺牲频谱效率的嵌入式导频（EP），SP 把可用数据容量提升约一倍**；代价是导频观测被未知数据的有色干扰系统性污染、且在中高 SNR 下不随噪声方差衰减，使一次性 OMP+MP 接收机受"估计误差"而非"噪声"限制、出现误码平台——而本文表明，**这一有色干扰可由迭代接收机消除**。

**English Abstract (opening, replaces the first 1–2 sentences):**

> Underwater acoustic (UWA) channels combine delay spreads of several to tens of milliseconds with a relative Doppler of order v/c∼10⁻³ — three to four orders larger than a typical RF link — producing severe **fractional** Doppler shifts. This puts conventional OFDM in a double bind: a cyclic prefix long enough to cover the full delay spread costs a prohibitive fraction of spectral efficiency at few-kilohertz UWA bandwidths, while **a residual fractional Doppler of even a few tenths of a sub-carrier destroys sub-carrier orthogonality and injects strong inter-carrier interference that a single-tap frequency-domain equaliser cannot repair**. Affine Frequency Division Multiplexing (AFDM) is designed for exactly such doubly-dispersive channels: through the discrete affine Fourier transform (DAFT) it folds every physical delay–Doppler path into a single sparse, full-diversity chirp-domain effective channel, making compressive-sensing OMP channel estimation a natural fit.
>
> On few-kilohertz UWA links, pilot overhead is itself a first-order constraint. **To preserve data capacity, this work adopts a superimposed-pilot (SP) frame in which every chirp sub-carrier carries both data and pilot energy. Relative to an embedded-pilot (EP) frame, which dedicates resources to pilots at a large spectral-efficiency cost, SP roughly doubles the usable data capacity**; the price is that the pilot observation is systematically contaminated by unknown-data interference that does not decay with the noise variance, leaving a one-shot OMP+MP receiver estimation-limited rather than noise-limited at mid-to-high SNR — **interference that, as this work shows, an iterative receiver can remove**.

> 之后接现摘要的"本文提出…OMP 仅运行一次…"那段（保持不变），结尾保留三条硬结果。这样摘要就完整覆盖了你的脊柱①②。

---

## 五、机理分析怎么处理（你问的）

**结论：保留，但压缩，且就地嵌入——它是脊柱的一环，不是边角。**

- "为什么一次 OMP 就抓 ~95%" + "剩下 ~5% 是 Dirichlet 旁瓣的结构性残差、与噪声无关" = 你脊柱②的核心，也是**同时论证"OMP-once 够用"和"为什么需要学习头"**的关键。→ **必须留**。
  - 物理基础（Dirichlet 旁瓣展开）放 **3.2**；
  - 证据（召回 ~95% + oracle headroom）放 **5.3**；
  - 一句话机理解读（学习头加的原子 ≥99.4% 落在旁瓣）放 **5.3 结尾**。
- **可以砍掉/只留一句**的边角：loss-form 与 head-capacity 消融、population-level per-candidate 的逐项归因细节、4B vs 2B 操作点论证——这些在短版里属于周边，最多各一句话带过（或完全省略）。

---

## 六、配图建议（回答你"引言附近要不要画一张系统/框图"）

**建议：画 1 张新的"系统总览图"放引言结尾（或 Ch.3 开头），其余框图复用 FYP-full 现成的。** 理由：三篇范文**都**在引言/方法开头放了一张总览图（董 Fig1-1 "system overview"、吴 Fig1-1 "technical framework"、赵 图2-1 "系统架构图"）——这是这本论文册的惯例，且能一眼讲清你的脊柱。

- **要你新画的（md 里我会标 `【待补图：…】` 占位）**：
  - **Fig.1 系统总览**：TX（SP 帧：数据+导频叠加）→ UWA 双弥散信道 → RX 流水线：**OMP-once → [学习支撑精化头] → 迭代(DA-LS + MP-BP) → 检测**。把脊柱画进一张图最值。
- **复用 FYP-full 现成图**（都在 `figures/`，无需重画）：
  - Fig.2 Dirichlet 核幅度 —— 注：`figures/system_block/fig_dirichlet_kernel.pdf` 在当前 `system_block/` 列表里没看到，**可能要你确认/重新生成**（其余都在）。
  - Fig.3 经典框图 `figures/system_block/figure_a_new.png`
  - Fig.4 学习头集成 `figures/system_block/figure_b_new.png`（架构图 `figure_c_new.png` 可选）
  - Fig.5 BER+NMSE `figures/loop13/loop13_combined_4B_ber_mse.png`
  - Fig.6 召回 `figures/loop13/loop13_support_recall.png`
  - Fig.7 oracle headroom `figures/loop13/loop13_oracle_headroom.png`
  - 可选：收敛 `figures/loop13/loop13_iter_convergence_4B.png`

---

## 七、一页速查：新旧结构对照

| 新结构 | 旧（当前材料库） | 主要改动 |
|---|---|---|
| 摘要（中英） | A1/A2 | **开头重写**：补分数多普勒危害 + OFDM 局限 + SP 动机 |
| Ch.1 Introduction（~0.8 页） | Ch.1（1.1–1.4，太长） | **瘦身**：删文献、删具体数字、结尾用 2 条点脊柱 |
| **Ch.2 Literature Review（新独立章）** | 埋在 1.2 | **独立成章**，按主题 3 子节 + 收尾 gap（取 Section1 lit survey） |
| Ch.3 System Model + On-Grid OMP Baseline | Ch.2 的 2.1–2.4 | 单独成章，**收尾暴露两个问题** |
| Ch.4 Proposed Receiver | Ch.2 的 2.5–2.8 | 单独成章，**逐级升级**（迭代→学习头） |
| Ch.5 Results | Ch.3 | 基本保留；**机理解读就地并入 5.3** |
| ~~Ch.4 Discussion~~ | Ch.4 | **解散**：承重机理→5.3，limitations→6.2 |
| Ch.6 Conclusion + Future Work | Ch.5 | **结论编号 + 展望合并** |
| References | R | 裁到 ~18 条 |

---

## 八、贡献写在哪 / 脊柱要不要用项目符号（你追问的）

### 8.1 三篇范文都有"贡献/核心理念"部分，位置如下

| 范文 | 贡献写成什么 | 写在哪 | 形式 |
|---|---|---|---|
| 董方莹 | 三条贡献 | **结论**（5. Conclusion）："the primary contributions of this work are summarized as follows: (1)…(2)…(3)…" | 编号列表 |
| 吴宁宁 | 三条贡献 | **摘要**里就列 "(1)…(2)…(3)…" + **结论 5.1** 再编号复述一遍 | 编号列表（出现两次） |
| 赵畅 | 4 条"核心设计理念"（即创新点） | **引言结尾**："本系统围绕以下核心理念展开：⚫…⚫…⚫…⚫…" + **结论**用散文复述 | **引言项目符号** + 结论散文 |

**三点观察**：
1. **没有一篇**像你现在 FYP-full / 材料库那样，在引言里单开一个"1.4 Contributions"长编号子节。短版里那个长 enumerate 太重，应删。
2. 贡献的标准落点是**结论（编号）**（董、吴都在结论编号），**摘要里再带一份**是吴宁宁的加分项。
3. **赵畅证明了"引言结尾用项目符号"是这本论文册接受的写法**——但他列的是**创新点/设计理念**，而且**每条只有一行**（标签：半句话）。

### 8.2 引言用两个项目符号点脊柱——合适，但要注意三点

**合适**：有赵畅的先例，且能让读者一眼看到主线，对你这种"两步因果链"的叙事很有帮助。但：

1. **别把"脊柱"和"贡献"混为一谈。** 你的两条脊柱是**动机性洞见**（为什么用 SP、为什么 OMP 不够要上 DL）；贡献是**你做的三件事**（复杂度可控联合接收机 / 1041 参数学习头 / oracle 机理分析）。两者分开：脊柱放引言，贡献放结论。
2. **学赵畅的紧凑度——一条一行。** 我上一版的脊柱 bullet 写成了段落，太长。已在 Ch.1 改成一行一条的版本。想更"学术流畅"也可以把这两条写成**引言里的一小段散文**（董/吴风格），不强求 bullet。
3. **避免同一件事在 8 页里重复三遍。** 推荐分工：
   - **引言**：2 条**短**脊柱 bullet（动机洞见）——出现一次；
   - **摘要**：保留三条硬结果的散文（可选编号）；
   - **结论**：三条**贡献**编号列表（董/吴风格）——出现一次。
   - → 这样脊柱（洞见）只在引言出现，贡献（成果）只在结论出现，不打架、不啰嗦。

**一句话结论**：引言用 2 条短 bullet 点脊柱可以（赵畅先例）；贡献别放引言，移到**结论编号列**（必放）+ 摘要带一份（加分）。删掉现有的"1.4 Contributions"长子节。

---

> **下一步可选**：① 我按这个蓝图把 `00_MATERIAL_DATABASE.md` 重排成新版（含重写后的摘要、瘦身引言、独立文献综述、拆开的方法两章、并标好取材行号与配图占位）；② 或直接据此重生成 `FYP_Short_Version.docx`。你定一个，我就动手；其中 Fig.1 总览图等你画好给我就行。
