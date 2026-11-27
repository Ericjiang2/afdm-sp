跑前假说**部分成立**。按论文发表前的时间截点回放，现行 AFDM `[高要求]` 和 `[放宽TWC]` 都是 **0 / 6**，通用协议也是 **0 / 6**。项目两档先挡在靶区和前置文献锚点，上一轮通过品味门的 10 篇则主要死于拼凑、直套和强基线。两轮仍有重合，尤其是 Mirabella 本身就在上一轮样本里。

本次以**可核实的原文证据能否过门**作二元裁决。`KILL` 包括未能证明达到硬门槛，逐篇区分证据缺失、实测量级不足和先例占用。时间截点取期刊首次发表前，Step 6 排除同一稿件的预印本，保留更早独立发表的会议稿和其他工作。项目口径按第 11 轮两档的靶区执行，固定保留 `2024–2026` 锚点窗口。此次是只读回放，未跑复现或跨模型终审。Mirabella 的数值和式号取自可获取的作者稿 `arXiv:2602.20909v2`。

## 逐篇过门

### #1 Thaj & Viterbo，零填充 OTFS 的 Rake 均衡

- **算力账，降阶有实据，完整门槛未证。** 原文 Figs. 9–10 在误比特率 \(10^{-3}\) 处相对消息传递分别领先约 **1 dB、2.5 dB**。Sec. VII 和 Fig. 14 报复乘数，Rake 为 \(O(SLNM)\)，其中 \(S\) 是迭代数，\(L\) 是不同延迟数，\(NM\) 是帧尺寸。它降低了相对消息传递和低复杂度线性均衡的路径数或带宽依赖，三者对帧尺寸都可呈线性。论文未给出对最快同精度方案的同机 `≥10×`，也未证实相对更早同阶 Rake 的同精度降阶。指定标题的正式出处是 **IEEE TVT 2020**，DOI `10.1109/TVT.2020.3044276`。 [作者稿](https://arxiv.org/pdf/2005.02192) · [Monash 出版记录](https://research.monash.edu/en/publications/low-complexity-iterative-rake-decision-feedback-equalizer-for-zer/)
- **口径 I。`[高要求] KILL`，最先触发 `round-agy-extra.md:18`。`[放宽TWC] KILL`，最先触发 `round-agy-extra.md:24–27`。** 原卡解决零填充 OTFS 的检测问题，缺少 AFDM 结构改造。即使按 `FUNNEL.md:73` 给它一个探索名额，`FUNNEL.md:32,55` 的发表年份窗口也早于不了该卡。
- **口径 II。`KILL`，`SKILL.md:119–123,192–193`。** 更早的 WCNC 2020 已给出零填充、循环块和 \(O(NML)\) 每轮 Rake 主核。期刊稿新增时域实现、超松弛和迭代译码，但现有对照未隔离出相对该先例达到算力门槛的增量。Step 6 应按增量查新。 [WCNC 2020 原文](https://engit.monash.edu/profiles/wp-content/uploads/2017/09/wcnc20Tharaj.pdf)

### #2 ten Brink、Kramer & Ashikhmin，按检测闭环设计 LDPC

- **跨层倒挂账，闭环收益跨过数字，倒挂对照未证。** Sec. III-D、Table I 和 Fig. 9 显示，按外信息传递图（EXIT）匹配检测器后，低密度奇偶校验码（LDPC）在 **4 发 1 收**时比标准 UMTS Turbo 码领先 **超过 5 dB**，所测方案距各自容量界 **不超过 1.25 dB**。原文的关键对手是 Turbo 码，未给出同一对候选码在独立测试和闭环中的排序反转，也就无法核实 `≥0.5 dB` 的倒挂和对最强独立最优组合的 `≥0.8 dB` 净赢。 [原文 Sec. III-D](https://www.researchgate.net/publication/3161232_Design_of_Low-Density_Parity-Check_Codes_for_Modulation_and_Detection)
- **口径 I。`[高要求] KILL`，`round-agy-extra.md:18`。`[放宽TWC] KILL`，`round-agy-extra.md:24–27`。** 原卡在多天线检测与译码之间做联合设计，未使用 AFDM 特有耦合。若走探索名额，仍触发 `FUNNEL.md:32,55`。
- **口径 II。`KILL`，`SKILL.md:127–129,192–193`。** 协议要求测出双向排序，论文给出的是失配机理与强闭环对照。另外，三位作者在 2002 年已发表检测器并入变量节点、再用 EXIT 选节点度数的核心做法。即使补齐倒挂读数，Step 6 也只应审期刊增量。 [2002 年会议稿](https://mediatum.ub.tum.de/doc/1755650/1755650.pdf)

### #3 Bemani、Ksairi & Kountouris，AFDM 波形与全分集

- **性能账为主，开销账为辅。** Sec. IV、Fig. 9 的三径例里，AFDM 的高信噪比误码斜率对应**三阶分集**，OFDM 和所测 OCDM 为**一阶**，加相位旋转的 OTFS 与 AFDM 基本重合。分集收益相对 OFDM 成立，相对最强图内对手未证 `≥0.8 dB`。Sec. VII 给出的导频与保护格公式，在 \(l_{\max}=2,\alpha_{\max}=2,\xi_\nu=0\) 时为 **29 对 45 格，少 35.6%**。格数跨过 `15%`，原文缺少两套完整导频估计链在同误帧率下的对照。 [原文 Secs. IV、VI–VII](https://www.eurecom.edu/publication/6896/download/comsys-publi-6896.pdf)
- **口径 I。`[高要求] KILL`、`[放宽TWC] KILL`，均最先触发 `FUNNEL.md:32,55`。** 2023 年发表前无法引用 `2024–2026` 顶刊。静态扫参禁令 `FUNNEL.md:50` 针对扫一遍就能消除的伪痛点。此卡用 \(c_1\) 改变路径排布、用 \(c_2\) 保证分集，单凭旋钮少不能套用该禁令。OTFS 的同分集阶也不足以证明算子同构，见 `SKILL.md:245–256`。
- **口径 II。`KILL`。** 性能账与开销账分别缺 `SKILL.md:142–143` 和 `SKILL.md:130–131` 要求的对照。另有独立的 Step 6 障碍：**2021 年 ICC Workshops 已发表波形和全分集定理，2021 年 ISWCS 已发表嵌入导频，2022 年 ICASSP 已发表低复杂度均衡**。按期刊发表前回放，`SKILL.md:235–238,255–258` 要求审剩余增量，不能把整套方案再当作首创。 [全分集](https://arxiv.org/abs/2104.11331) · [嵌入导频](https://www.eurecom.fr/publication/6671/download/comsys-publi-6671.pdf) · [低复杂度均衡](https://www.eurecom.eu/en/publication/6821)

### #4 Hassibi & Hochwald，多天线链路的最优训练

- **分界律／紧界账，设计定理成立，账本数字未证。** Theorems 2–3 给出训练和数据功率可分配时的闭式解，训练长度取发射天线数 \(T_\tau=M\)。Figs. 1–2 中，优化功率相对等功率使**容量下界提高约 5–10%**。Fig. 4 超过 **6 dB** 的差是训练与数据阶段之间的最优功率差，不能计作界收紧 `≥1 dB`。原文未给出相对最佳旧界收紧 `≥30%` 或协议要求的翻转验证。 [原文 Theorems 2–3、Figs. 1–4](https://telin.ugent.be/~mm/Lennert/BER_degradation/01193803.pdf)
- **口径 I。`[高要求] KILL`，`round-agy-extra.md:18`。`[放宽TWC] KILL`，`round-agy-extra.md:24–27`。** 原卡是块衰落多天线训练设计，未提出 AFDM 专属问题。若忽略靶区，`FUNNEL.md:32,55` 仍先拦下；再往后，`FUNNEL.md:50` 会拦以静态训练长度和功率分配为主体的选参卡。
- **口径 II。`KILL`，`SKILL.md:134–141`。** 定理给出最优训练长度，原文证据未落在协议规定的信噪比翻转或旧界收紧指标上。通用协议关于短扫参的 `SKILL.md:243–244` 也不足以否掉一个跨参数成立的定理。独立于量纲问题，同一作者在 **Asilomar 2000** 已发表 \(T_\tau=M\) 的核心结论，期刊卡须另审增量。 [Asilomar 2000 原文与摘要](https://authors.library.caltech.edu/records/0k04j-m1s71)

### #5 Nazer & Gastpar，计算转发

- **破壁账，省功率跨过数字，地板前提未证。** Sec. X、Fig. 12 在每条回传链路 **2 bit/信道使用**、中断概率 **25%** 下，达到回传瓶颈所需的发射功率比解码转发低 **约 5 dB**。Example 4 的 Hadamard 信道还给出计算速率随功率增长的结论。Fig. 12 的 **5 dB** 是在固定中断概率下的速率比较，未证明最强基线先有 `FER ≥ 10^-2` 且持续 `≥5 dB` 的平层或失锁。原文也要求目的端收到满秩方程组。 [原文 Example 4、Secs. IX–X](https://arxiv.org/pdf/0908.2119)
- **口径 I。`[高要求] KILL`，`round-agy-extra.md:18`。`[放宽TWC] KILL`，`round-agy-extra.md:24–27`。** 原卡研究高斯中继网络中的代数译码，未引入 AFDM 结构。这里的范围理由也无需把该网络说成 `FUNNEL.md:28` 所列的双向中继。
- **口径 II。`KILL`，`SKILL.md:124–126,192–193`。** 破壁账把有限帧错误地板设成先决条件，因而收不下已证可达速率的增益。更早的 Allerton 2007 已提出用格码可靠解线性函数并转发，Step 6 应核对期刊稿对一般信道系数、满秩恢复和可达速率的增量。 [Allerton 2007 原文](https://www.ideals.illinois.edu/items/139323/bitstreams/450228/data.pdf)

### #6 Mirabella et al.，连续时间 AFDM，`10.1109/JSAC.2026.3751260`

- **分界律／紧界账，工程量级清楚，账本数字未证。** Sec. II-A、Eqs. (14)–(15) 在其仿射傅里叶级数成形模型内给出频谱副本不重叠的条件。按原式和 Table II 的 \(N=64,\alpha=0.25\)，**49 个子载波可用，15 个须停用，占 23.4%**。Sec. III-A 的例子中，截断到 17 个采样周期后，AFDM 带外能量由 **−39.24 dB 升至 −30 dB**。前者是保护开销，后者是截断代价。所推时延和多普勒估计的 Cramér–Rao 下界限于单径，两项数字均未证明旧界收紧或多径翻转达到硬门槛。 [作者稿 Secs. II–IV](https://arxiv.org/html/2602.20909v2)
- **口径 I。`[高要求] KILL`、`[放宽TWC] KILL`，已核证据下均最先触发 `FUNNEL.md:32,55`。** Sui 的相噪和频偏对照、Song 等人的同步失配模型可以锚定相邻问题，但未核到该卡在前人原参数内先复现了**边缘频谱副本重叠**这个主张对应的痛点。若接受成形与同步失配作为较宽的锚点，两档仍会在 `FUNNEL.md:52` 卡住，`[高要求]` 还缺 `round-agy-extra.md:19` 要求的等带宽、等开销 OFDM 净赢双重差分。现行 `FUNNEL.md:54` 已开放理论紧界账。 [Sui et al. 原文](https://repository.essex.ac.uk/43341/1/MIMO_AFDM_Outperforms_MIMO_OFDM_in_the_Face_of_Hardware_Impairments.pdf) · [Song et al. 原文摘要](https://ieeexplore.ieee.org/abstract/document/11723252/authors)
- **口径 II。`KILL`，`SKILL.md:134–141`。** 该规则接收数值翻转与紧界改进，未接收由证明确定的设计可行域。`SKILL.md:265,278` 允许解析证据和充分性检验，因此**缺新迭代接收机本身没有触发淘汰**。原文 Eq. (14) 也明确指出常规 OFDM 有相应的带限要求。AFDM 特有项在 Eq. (17)，接收滤波响应随采样时刻变化。 [作者稿 Eqs. (14)–(17)](https://arxiv.org/html/2602.20909v2)

## 汇总矩阵与结构诊断

| 论文 | AFDM `[高要求]` | AFDM `[放宽TWC]` | 通用 `SKILL.md` |
|---|---|---|---|
| #1 Thaj–Viterbo | KILL | KILL | KILL |
| #2 ten Brink et al. | KILL | KILL | KILL |
| #3 Bemani et al. | KILL | KILL | KILL |
| #4 Hassibi–Hochwald | KILL | KILL | KILL |
| #5 Nazer–Gastpar | KILL | KILL | KILL |
| #6 Mirabella et al. | KILL | KILL | KILL |
| **存活** | **0 / 6** | **0 / 6** | **0 / 6** |

上一轮 `0 / 20` 混含四种期刊，且与本轮重叠 #6。防拼凑、零改动直套和配平强基线能挡住换皮，也能识别已发表的核心。固定年份锚点和统一接收机指标会漏掉新波形、可达速率与设计边界。最小改两处：锚点按提案日期滚动，接收可独立核验的公开模型缺口；为定理开放以可达率、分集阶或可行域变化计分的入口，保留同设定查新。 [上一轮校准 `trans-calibration-20261124.md:84`](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/reviews/trans-calibration-20261124.md:84>)