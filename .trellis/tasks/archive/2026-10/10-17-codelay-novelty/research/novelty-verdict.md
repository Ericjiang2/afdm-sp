# 新颖性判定：同时延协方差主张 H*（2026-10-17）

- 输入：`search-shortlist.md`，由 Sonnet 检索，覆盖五个领域，短名单 15 篇。
- 编排者亲读的决定性来源（证据等级 V）：
  - Kanazawa arXiv:2501.15935v3 §III-C，式 (22)–(25)；
  - Luo arXiv:2607.18881v1 Algorithm 1 与式 (15)–(24)；
  - Zhu–Leus–Giannakis arXiv:1008.2996（IEEE TSP 59(5) 2011），§V 与 §VII Test Case 2–4。
- 其余条目的证据等级见短名单。
- 结论只适用于本次检索范围：检索内未发现 ≠ 无人做过。
- 覆盖缺口：
  - IEEE 付费全文未读，包括 Prasad TSP'14、Song'04、Yuan WCL'21、Chi TSP'11 期刊版；
  - 软判决信道估计（B 区）与 Dirichlet 核同时延（E 区）方向的自由文本检索偏少（captcha 或配额所限）。

## 0. 结论先行

- **H* 不是新的一般推断原则。**"字典误差要计入它的协方差"在误差变量（EIV）稀疏回归中早已确立，见 corrected Lasso、MU selector、WSS-TLS。另一个一般现象也有先例：未建模的字典扰动会在真原子旁边产生重复的近邻原子（S-TLS 的 DoA 实验、Duval–Peyré doubling，但两者都源于网格失配或离散化）。
- **在检索范围内未发现先例的部分**：
  - (i) 误差来自**译码数据不确定性**，而且标量模型已经计入了不确定性的总方差，只丢掉了原子之间的相干。
  - (ii) 这种相干是 delay-Doppler 字典特有的结构：即使符号方差恒定，同一时延上两个原子之间的不确定性 Gram 也等于 Σv·D_N(Δν)，不是对角阵。
  - (iii) 由此产生的失败模式，是在已占用的真时延上出现近重复的幻影原子。
  - (iv) 预注册的两类信道对照：精确协方差在两类信道上都最优；任何固定排除规则都只能在其中一类上取胜。
- **SP-OTFS/AFDM 数据辅助文献的现状**：全部使用标量或白化数据干扰模型，包括 Mishra 式 (22)/(48)、Zheng TVT'24 Lemma 1、Kanazawa 式 (24)、Luo 式 (24)。Kanazawa 和 Zheng 都写到会检出"不存在的路径"，但把原因归于干扰超过门限，没有人把它归因到协方差的结构。
- **定位**：属于"领域内此前未被识别的机制 + 预注册的经验原则"。新颖性强度中等。最大的审稿风险是被说成"这就是精确二阶矩的 EM"或"这就是 basis mismatch"。对后者，E-1/E-2 已经有直接的对照可以回应：A1 与 A2 使用同一网格和同一细化流程，只有 Γ 不同。

## 1. 逐条判定

| 主张 | 判定 | 最近先行 | 精确区别 |
|---|---|---|---|
| **C1 现象**：标量化数据不确定性 → 已占真时延上的近重复同时延幻影原子 | **部分已知**（一般形状已知，具体形式未发现） | Zhu–Leus–Giannakis TSP'11 Test Case 4（V）：Lasso 在每个源两侧各给一个原子，建模结构化扰动的 WSS-TLS 给出正确支撑。Duval–Peyré arXiv:1503.08577（V 摘要）：细网格 Lasso 把尖峰"duplicated as the two nearest neighbors"。Rosenbaum–Tsybakov AoS'10（V）：忽略矩阵不确定性时，支撑集"much too large"。 | 先例中的扰动来自网格失配、离散化或独立误差，对照方式是"完全忽略扰动 vs 建模扰动"。我们的扰动来自译码软信息；标量臂已经计入总方差，只丢掉同时延原子间的相干，就足以产生幻影；同网格对照（A1 vs A2）排除了网格机制。 |
| **C2 机制**：同时延原子的不确定性相干 ∝ Σv·D_N(Δν) | **对象已知，结构与后果未发现** | 软符号 EM 中的 E[ΦᴴΦ] = Φ̄ᴴΦ̄ + Σ 属教科书内容；WSS-TLS 与 Loh–Wainwright 使用已知的一般误差协方差。Prasad TSP'14 J-SBL（A）在 OFDM 中联合处理未知数据。 | 编排者推导（非文献）：在 OFDM 抽头字典中，若符号方差恒定为 v，不确定性 Gram 为 F_Lᴴ(vI)F_L = N v I，即标量模型精确。在 delay-Doppler 字典中，同一时延、不同 Doppler 的两个原子之间 Gram 为 Σv·D_N(Δν)，方差恒定也不是对角阵。因此"标量化"在 OFDM 文献中基本无害，在 OTFS/AFDM 中却会结构性失效。这正是受限兼容定理的内容。 |
| **C3 原则**：支撑交换评分需要精确投影协方差；固定排除规则在两类信道中至少一类失败 | **原则一般已知；条件化的比较结论未发现** | Loh–Wainwright arXiv:1412.5632（V）在已知 Σ_w 下证明修正 Gram 的支撑一致性。反方向结论见 Chen–Caramanis arXiv:1206.0823（V）：误差独立时，支撑恢复"requires no knowledge of even the statistics of the noise"。排除式启发式见 Fannjiang–Liao arXiv:1106.5177 的 band exclusion（V）。DA-OMP arXiv:2412.01498 把同时延相邻 Doppler 原子视为分数 Doppler 的正常表示。 | 我们的结论与 Chen–Caramanis 的独立误差结论正好互补：误差在近共线列之间相干时，支撑决策确实需要协方差（E-1 S_Γ 1.18–1.22）。排除规则（band exclusion 型 A2g，以及按定理阈值的 A2n）在 R 或 C 上各失败一次，精确协方差两类都赢（E-2 D3 PRINCIPLE）。这是预注册的经验结论，不是定理。 |
| **C4 理论**：受限兼容定理，doublet 特征值 1 ± \|D_N\| | **数学初等；作为解释环节有价值** | 2×2 Gram 的特征值 1 ± \|μ\| 是初等事实；未检到把它与数据不确定性的标量闭合联系起来的工作（未专门检索）。 | 不宜作为独立的新颖性主张，只作 C2 的形式化。E-2 显示定理阈值（A2n）无法单独预测 R 族中 \|D_N\| < .5 的幻影（G_n = .815），需要扩展到决策层的条件。 |

## 2. 对论文定位的含义

- **可主张**：
  - 指出 SP 数据辅助 delay-Doppler 接收机中一个此前未报告的失败模式，以及它的结构根源：同时延不确定性相干，这一点在 OFDM 中不存在；
  - 一个方法级修正，即在离散支撑决策中使用投影协方差；它本身就是精确 EM 二阶矩，不是新算法；
  - 预注册的因果证据：E-1 的因子消融；E-2 的守卫臂，以及在真簇信道上的原则与启发式对照。
- **不可主张**：
  - "首次在稀疏恢复中考虑字典误差协方差"（WSS-TLS、corrected Lasso）；
  - "首次发现重复近邻原子"（S-TLS、Duval–Peyré）；
  - "数据辅助重获取"这一方法类（Kanazawa、Luo、Zheng）。
- **要达到"强 Trans"还缺两样**：
  - (a) **外部有效性**：把同一修正放进文献中的标量化接收机，例如 Kanazawa 式门限检测或 Luo 式 D-GESBL 的移植版，看幻影同时延检测是否消失、FER 是否改善。这能把"我们接收机的机制"升级为"该领域通行近似的缺陷"。在提升新颖性与意义两方面，这是最有判别力的下一步。
  - (b) **决策层理论**：给出标量评分接受同时延候选的条件（关于 Σv、\|D_N\|、SNR、已有路径增益），并解释 R 族中 \|D_N\| < .5 的幻影。

## 3. Related-work 段落草稿（英文，供论文用）

> Errors-in-variables sparse regression accounts for a perturbed regression matrix through its error covariance: the corrected
> Lasso [Loh–Wainwright 2012] and the MU selector [Rosenbaum–Tsybakov 2010] correct the Gram matrix or the constraint set, and
> weighted/structured S-TLS [Zhu–Leus–Giannakis 2011] weights a structured perturbation by its known covariance. In grid-based
> estimation, unmodelled perturbations are known to split a source into neighbouring atoms [Zhu–Leus–Giannakis 2011, Sec. VII;
> Duval–Peyré 2017], and band exclusion [Fannjiang–Liao 2012] suppresses such near-duplicates with a separation prior. Data-aided
> superimposed-pilot OTFS/AFDM receivers rebuild the sensing dictionary from decoded data but model the residual data
> uncertainty as white interference [Mishra et al. 2021; Zheng et al. 2024; Kanazawa et al. 2025; Luo et al. 2026]. We show that
> in delay-Doppler dictionaries this whitening is structurally wrong: the decoder-induced uncertainty is coherent across atoms
> sharing a delay, with cross term Σv·D_N(Δν) even for constant symbol variance, whereas for OFDM tap dictionaries with
> constant symbol variance it is exactly white. Dropping this coherence makes the support search insert phantom same-delay atoms; the exact projected covariance
> removes them on channels without co-delay paths and still admits true co-delay rays on clustered channels, where any
> exclusion rule fails.

（引文 ID：Loh–Wainwright AoS 2012, arXiv:1109.3714；Rosenbaum–Tsybakov AoS 2010, DOI 10.1214/10-AOS793；Zhu–Leus–Giannakis IEEE TSP
59(5) 2011, DOI 10.1109/TSP.2011.2109956；Duval–Peyré Inverse Problems 2017, DOI 10.1088/1361-6420/aa5e12；Fannjiang–Liao SIAM
J. Imaging Sci. 5(1) 2012, DOI 10.1137/110838509；Mishra et al. IEEE TWC 2021, arXiv:2010.15066；Zheng et al. IEEE TVT 2024,
arXiv:2404.10232；Kanazawa et al. arXiv:2501.15935；Luo et al. arXiv:2607.18881（TCOM 接收为作者自述）。投稿前需对期刊卷期做一次
citation audit。）
