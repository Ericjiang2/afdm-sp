# 新颖性定位稿 v2（Claude，2026-11-18，DRAFT，待 Eric 定稿）

> v1 见 git `12a0a5db`。v2 按 Gemini 的敌意审查修改（Eric 转贴，原文未存）；Gemini 的每条事实断言都已对照记录核实，结论见第 7 节分歧表。
> 依据：10-17 [新颖性判定](../../archive/2026-10/10-17-codelay-novelty/research/novelty-verdict.md)；11-18 [预印本源码核对](recent-preprints-verification-20261118.md)；
> res-20261017-01/03、res-20261118-02/04；SBL 旧键诊断；Astra 对话漏洞 1、3。

## 0. v2 最重要的改动：文献归属

v1 写的是"现有分数 Doppler SP 工作沿用了标量近似 `u‖h‖²`"。经核对，这句话不准确。
- **Y. Luo TCOM'26** 用硬判决重映射填字典，全程不用软方差，观测空间噪声为 `β⁻¹I_N`（核对稿第 14–17 行，V 级）。
- **Kanazawa TVT'26** 在核对稿中归入整数格点一行。
- **Zheng TVT'25** 的字典几何与干扰建模没有逐式核对过（核对稿只覆盖 4 篇预印本）。
- 保留软迹的对角模型 `Σv·I = u‖h‖²`，正是我们自己的受控标量臂 A2 / L-diag。

一个关键的已有观测：在 SBL 一侧，Luo 式硬判决移植（L-hard）每帧的同延迟对数是 **5.70**，与完整 Γ（L-cov 5.11）相当；只有软迹对角模型（L-diag）高达 **23.71**（res-20261017-03）。

由此得出的正确定位：
- 幻影病理是"**把现有接收机升级为利用软信息时，最自然的对角做法**"的结构性失败，不是现有论文本身的失败。
- 现有硬判决接收机的代价在别处：不利用软信息。L-hard 的 `10⁻²` 穿越点比 `CODELAY` 差 1.3–5.3 dB（res-20261118-03）。

**已核（2026-11-18，[逐式核对](literature-uncertainty-model-check-20261118.md)）**：Mishra、Zheng（arXiv v1）、Kanazawa 都是**整数**格点；数据误差都按先验算出的常数白噪声处理（或只用于门限），**都不是 `u‖h‖²` 型**。
- 第 0 节的判断成立。
- 贡献按正面方式写："首次在分数 Doppler 的 SP 支撑获取中正确使用译码软不确定度"。
- 方向 B（把 `CODELAY` 放进文献接收机，证明其近似有缺陷）取消。

## 1. 一句话贡献（v2）

> In data-aided superimposed-pilot channel estimation, the true decoder-induced uncertainty energy `tr(H V Hᴴ)` depends only on the composite channel operator and is invariant to splitting a path into collinear atoms. On orthogonal integer delay–Doppler grids [Wang et al., TCOM'22] its Gram is diagonal, so trace-preserving scalarization is exact. With integer-aligned delays and continuous-Doppler path coordinates, it acquires a deterministic co-delay Dirichlet block `u·D_N(Δν)`. Existing receivers either drop data uncertainty from the dictionary (hard decisions with isotropic noise) or would naturally whiten it as `u‖h‖²`; both miss this block. Under matched grids and refinement, we show that the trace-preserving scalarization converts a split-invariant seminorm into an isotropic coordinate penalty. Support acquisition then favours same-delay phantoms of strong paths over missed weak paths, even with spare path slots. A single-scalar closed-form block (`CODELAY`) restores the co-delay term and matches the full heteroscedastic covariance with zero frame-error discordance.

（第 0 节已核：第 3 句保留"would naturally"的说法，不能把 `u‖h‖²` 归给任何具体文献。可以补一句：在整数格点上，Wang TCOM'22 的期望 Gram 恰好退化为这种对角形式。）

## 2. 已知的部分（必须正面致谢）

| 已知内容 | 来源 | 状态 |
|---|---|---|
| 字典扰动应计入其协方差 | Rosenbaum–Tsybakov AoS'10；Loh–Wainwright AoS'12；Zhu–Leus–Giannakis TSP'11 | V（10-17） |
| 软符号期望 Gram `E[XᴴX] = X̄ᴴX̄ + Σ_x`，以及丢掉 `Σ_x` 带来的偏差 | 迭代接收机经典文献：Kocian–Fleury TCOM'03、Cozzo–Hughes TCOM'03（Gemini 提供，**待 citation audit**）；稀疏 OFDM：Prasad–Murthy–Rao TSP'14；DD 数据辅助：Wang TCOM'22 式 59–60 | Wang V；其余待核 |
| 网格失配或扰动使尖峰分裂为近邻原子 | Zhu–Leus–Giannakis §VII；Duval–Peyré IP'17；band exclusion（Fannjiang–Liao SIIMS'12） | V（10-17） |
| 各向同性 ℓ₂ 惩罚对重复变量均分系数 | Zou–Hastie 2005 Lemma 2 | Astra 指出 |
| 定基数单步最优替换、连续频偏贪心细化（CSTATE 搜索外壳的范式） | SBR：Soussen TSP'11；NOMP：Mamandipoor TSP'16 | 待 citation audit；声明外壳不是新算法 |
| SP 接收机用译码数据重建字典 | Mishra TWC'21；Zheng TVT'25；Kanazawa TVT'26；Y. Luo TCOM'26 | 方法类不是我们的贡献 |

## 3. 确切增量（v2）

| # | 增量 | 与先例的区别 | 证据状态 |
|---|---|---|---|
| D1 | **精确性边界**：在整数对齐时延、充分 CPP、恒定符号方差下，`tr(HVHᴴ) − u‖h‖²` 只剩同延迟项 `u·Σ_{i≠j, ℓ_i=ℓ_j} h_i* h_j D_N(ν_j − ν_i)`。它在整数 DD 格点上为 0，在连续 Doppler 坐标下不为 0。现有硬判决接收机完全不把软不确定度放进字典，同样没有这一项 | Wang TCOM'22 的期望 Gram 在整数格点上退化为对角阵，这个差别在他们的设定里不出现 | **已证**：任意异方差 v 下同延迟元素 `u·D_N(Δν)` 精确；跨时延残差的闭式与上界（Astra B1/B2，derived；Claude 用 `physical.py` 独立数值复核）。**更正**：相邻时延（|d| = 1）时，`Δν = −5` 处共振，残差 = `|v̂[1]|`，没有 Doppler 压制；"双重压制"只在 |d| ≥ 2 时成立。文献归属见第 0 节 |
| D2 | **决策层后果**：trace-preserving 标量化把对拆分不变的算子半范数 `tr(HVHᴴ)` 换成了各向同性的坐标惩罚 `u‖h‖²`，把重复原子的虚假 Schur 增益从 `O(λ)` 放大到 `O(u+λ)`（式 3），并给出它压过缺失弱径的窗口 `θ_full < r_w < θ_sc` | 不在"u 算不算惩罚"上争：`(u+λ)‖h‖²` 的均分本身就是 Zou–Hastie 的直接推论。新的是"哪个对拆分不变的量被错误地换成了坐标惩罚"，以及它在离散支撑决策中的胜负条件。窗口是理想截面（Δν→0、正交、无残差）上的闭式切片，一般情形受式 (12) 的相位与均值相关调制 | 代数 + 378 例核验；res-20261118-01（draft，多数 [64.6%, 97.1%]） |
| D3 | **不是容量伪影**：交换步数固定为 2，上限从 8 放宽到 12 后，损害仍然存在 | 回应"上限设为 P 所致" | res-20261118-04（draft，预注册）：D12/D8 = .763 [.716, .811]，MIXED；首步幻影率 A2 93.8% → 99.8%，`CODELAY` 2.2%。比值**不是**分解：不能读成"76% 来自交换被抢占" |
| D4 | **修法极简且等价**；**所测的三种固定规则**（不禁、近邻禁 `A2n`、全禁 `A2g`）各自至少在一类信道上失败，`CODELAY` 两类都最优 | 只测了三个固定规则，不能写成"任何固定距离规则"。可以附一句论证（不是检验）：阈值大则禁掉真双径，阈值小则放过中距幻影 | res-20261118-03/02（draft）、res-20261017-02（已验收）：`A2g` 在 MIXED8 上 14/96 对 0/96；`A2n` 在 MIXED8 上 0/96，在 R 族少救 3.3 pp |
| D5 | **接口性质（边界）**：在"精确复制、先验按 1/k 缩放"的定义下，固定增益与期望 Gram 更新对复制严格不变（`eG` 的岭项 `α' = kα`），原生坐标更新不是 | 未检到先例（未专门检索） | 400/400 例；因果未定 |

### D6（2026-11-18 补）：普适性，以及"为什么是 AFDM"
来源：[astra-generality-20261118](astra-generality-20261118.md)，Claude 已独立复核。

**普适的部分**：符号方差恒定时，任何完备酉调制在 Doppler 连续时都会出现同延迟块 `u·D_L(Δν)`（OFDM、OTFS、AFDM 等）；式 (3)、(8)、(12)、(14) 的决策链原样迁移。所以拆分奖励这个病理不是 AFDM 特有的。

**AFDM 特有的部分**：三种调制里，只有 AFDM 同时满足下面两点。
1. 时域平坦基 → 同延迟元素用一个标量 u 对任意异方差精确（OFDM 也满足；OTFS 需要 M 个行总方差）。
2. chirp 移位 `2Nc₁d` 把跨时延项推离 Doppler 主瓣，|d| ≥ 2 时被压制（OFDM 没有这一移位；OTFS 在时延范围内跨时延为 0，但第 1 点不满足）。

因此"只修同延迟块、一个标量就够"是 AFDM 结构给出的最小精确形式。这回答了"为什么是 AFDM"。

**诚实边界**：随机 v 下跨时延残差只有几个百分点，AFDM 与 OFDM 的差别是结构性的，数值上可能不大；AFDM 有 `d = 1、Δν = −5` 的共振点。论文中作为结构性质陈述，不作性能主张（没有 OFDM/OTFS 实验）。

## 4. 审稿人攻击与回应（v2，7 条）

1. **"就是二阶矩 EM。"** 算子是标准二阶矩（D4 不主张新算法）。新的是 D1 + D2：在整数格点上标量化是精确的；在连续 Doppler 下，它恰好把一个对拆分不变的量变成了坐标惩罚，从而改变支撑决策。
2. **"就是 basis mismatch / 网格分裂。"** E-1 在同网格、同细化下只换 Γ；首步归因中，移除强径残差后幻影仍以多数保留。
3. **"Zou–Hastie 早有。"** 正面承认均分是 ZH 的推论；区别按 D2 的写法陈述，不在 u 与 λ 的命名上做文章。
4. **"上限设为 P 所致。"** D3，加上 Q1：上限 10/12 时 4/4 格稳健。
5. **"同一修正放进 SBL 反而更差。"** D5：边界加接口性质，不主张统一机制。
6. **（新）"2026 年的 AFDM 都做分数时延，你的块靠整数时延。"** 明确界定模型为采样对齐、可分辨的多径时延（整数抽头 + 连续 Doppler），并作为局限写明。Gemini 给的推论（分数时延下恒定方差时仍只依赖标量 u，核换成二维核 `D_N(Δℓ)·D_N(Δν + 2Nc₁Δℓ)`）**未核实**，交 Astra 第 B3 问或后续推导，核实前不写进论文。
7. **（新）"上限小于 P 或 σ² 未知时你们自己判了 DEGRADED。"**
   - 上限定义为保守上界 `P_cap ≥ P`：过估计零损失（M 族上限 10/12；T 族 P=6 在 ρ .5 稳健，在 ρ .3 比基准还好 0.35 dB，判为 INCONCLUSIVE）；欠估计因截断路径必然退化（上限 6、P=10）。
   - 未知 σ²：用单帧矩估计时，穿越点后移 1.0–1.2 dB（真实信道参照也后移 0.32 dB）；但同帧上 `CODELAY` 对 A2 的救回差距仍保持在 46.7 pp（上限 8，已知噪声时为 51.4 pp）。
   - 更正 Gemini：它引用的"18.6% vs 7.1%"是 M 族上限 12 的数字，不是 N 族。
   - 是否用判决导向的 σ² 估计补救，由 Eric 决定。

## 5. 不可主张 / 需从旧稿删改

- 10-17 判定中的四条"不可主张"照旧。
- "现有工作系统性制造同延迟幻影"（骨架 v1.1 第 2 点）：在第 0 节核实之前，**改为**"the natural soft-aware diagonal extension of existing receivers ..."。
- 预印本核对稿表格最后一格"解释跨估计器反转"：删去。
- "exact across arbitrary heteroscedastic symbol variances"：在 Astra 第 B 部分之前改为条件句，或只写恒定方差。
- "eliminates phantom splitting"：改为 "reduces phantom-first edits from 94% to 2%"。
- "any fixed-distance exclusion rule fails"：改为 "each of the three tested fixed rules fails on at least one channel family"。
- "一条原理统一全文"：改为"统一支撑获取阶段"；给定支撑后的重拟合残差不在范围内。

## 6. 依赖与待办

1. **第 0 节待核**（最高优先，零仿真）：V 级逐式阅读 Mishra 式 (22)/(48)、Kanazawa 式 (24)/(25)、Zheng TVT'25（或 TVT'24 Lemma 1）的数据干扰方差表达式。它决定贡献句第 3 句的写法。
2. ~~Astra 第 A、B 部分~~ 已完成（[astra-producer-consumer-20261118](astra-producer-consumer-20261118.md)）：
   - D1 异方差版本已证。
   - 分数时延下同延迟精确性不再自动成立（B3）。
   - 生产者–消费者命题"在限制下成立"，但近乎定义性，不预测 SBL 反转的符号，**不用它升级第 4 句**。
   - 骨架 v1.1 Prop 1 第 2 条的"整数 Doppler 下跨时延恒零"推论须改：|d| = 1 时可共振。
   - 主线 `CODELAY → scalar_joint` 无无条件免疫定理，第 4 句不可写"下游自然良态"为定理。
3. Eric 验收 res-20261118-01/02/03/04。
4. 投稿前 citation audit，包括 Gemini 新提供的 Kocian–Fleury、Cozzo–Hughes、Mamandipoor。

## 7. Claude（v1）vs Gemini 分歧表

| 条目 | v1 | Gemini | 核实 | 采纳 |
|---|---|---|---|---|
| D1 前提 | 只写了恒定方差 | 漏写整数时延与 CPP | 对 | 是 |
| D1 文献归属 | Zheng/Kanazawa/Y. Luo 用 `u‖h‖²` | Kanazawa 是整数格点；Y. Luo 用硬判决 + `β⁻¹I`；`u‖h‖²` 是我们的 A2 | Y. Luo、Kanazawa 已核实属实；Zheng 未核；L-hard 无多余同延迟对 | 是，并改写定位（第 0 节） |
| D2 与 Zou–Hastie | "u 不是惩罚" | 代数上 `(u+λ)‖h‖²` 就是惩罚；区别应在"不变半范数被换成坐标惩罚" | 对，与拆分不变性的表述一致 | 是 |
| D2 窗口 | 未注明截面条件 | 理想截面切片 | 对（Astra 也指出过） | 是 |
| D3 | holds | holds；另说"约 76% 来自交换被抢占" | 比值不是分解 | 前半采纳，"76%"不采纳 |
| D4 | "任何固定距离规则" | 只测了两个阈值 | 实测三种规则（含不禁）；`A2n` 在 MIXED8 为 0/96 属实 | 是，收窄 |
| D5 | holds | holds | — | — |
| 新攻击：分数时延 | 未列 | 列为最狠 | 属实（核对稿已列为边界） | 是；二维核推论未核，不采纳 |
| 新攻击：上限小于 P、σ² | 未列 | 列；称未知 σ² 下优势 2.6× | 数字张冠李戴（是 M 族上限 12） | 攻击采纳，数字更正 |
| 已知表 | 缺迭代接收机经典、SBR/NOMP | 补 Kocian–Fleury、Cozzo–Hughes、Prasad、SBR、NOMP | 待 citation audit | 是（标待核） |
| 贡献句 | A/B | 都不能直接用，给出改写 | 改写稿仍把 Y. Luo 与"`u‖h‖²`"并列为同一缺陷 | 采纳结构，按第 0 节调整归属 |
