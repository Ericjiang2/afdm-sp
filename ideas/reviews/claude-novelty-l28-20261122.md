# Claude opus 查新初筛（第 6 步：l28）——本地第 4 轮，2026-11-22

模型：claude opus（`claude -p --no-session-persistence --model opus`；Gemini 出的卡本应交 gpt-6.2-sol，Codex 无额度后改派，属跨家族）。提示：`~/.cache/idea-funnel/afdm-20261122-l4/s9c-claude.prompt`。以下为原文。

# 线 A（I-20261122-l28）：用跨抽头共享的多普勒核做克罗内克子空间边缘证据

**结论：不值得做（省去 L2）。**

先说清这次查新的覆盖面：
- `paper-search` 的 Python 脚本被权限拦下，没有跑成。
- `scoop-check` 只按它的结构做了判断（拆成四个维度、逐篇比重叠、给等级）。它要求的逐步落盘、TaskCreate 和 `fetch_paper.sh` 下全文都没有执行。
- 检索靠网页搜索和网页读取完成，下面每篇都注明了读到什么程度。
- 没有改任何项目文件。

---

## 一句话结论
**不值得做（省去 L2）**。

它的数学核心是 Zhang–Rao 2013 的块稀疏贝叶斯学习（BSBL）先验：每块一个功率，所有块共用一个块内相关矩阵。再加上 BSBL 的快速边缘似然版本（BSBL-FM）。"各抽头共用同一张 Jakes 时间相关"这个物理结构，Liu–Guan–González 的叠加导频 OTFS 接收机（KL-BEM）已经在 3GPP TDL-E 上用过，而且同样用判决符号当伪导频迭代。剩下的新东西只有一处：在约 100 个采样的长时延窗里，用证据准则去找稀疏时延。而这个场景是本项目自己的参数造出来的。

## 固有重要性（抛开先例）：**中**
- **问题本身是真的。** 叠加导频接收机遇到"时延扩展长、每个抽头内有多普勒展宽"的信道会捕获崩塌，项目实测：TDL 上无真值的 `SPcb` 误帧率 .55–.90，真信道约 0。
- **解法结构是教科书式的贝叶斯建模**（可分离先验加边缘证据）。这不是"一个准则同时消掉两难"的原理，组会三句话讲完，但讲不出反直觉的地方。
- **可回收的诊断账本：** `TDL_REPORT.md` 的三级阶梯（真信道 .003/.000/.000 → 给真时延的平坦 DPSS `SPg_flat` .308/.159/.162 → `SPcb` .781/.897/.551，条件是 8 dB、ρ = .2、d60）。它把"找径缺口"和"先验缺口"分开了，可以作为现稿讨论簇信道局限的一段素材。

## 白话 + 类比
一条很长的走廊里有十几间房，有人在说话，你要找出是哪几间。这栋楼的人口音都一样（同一个终端的速度决定所有反射共用一张多普勒形状表）。卡片的做法是：先从最响的几间房学会这种口音，再用它判断轻声的房间里是不是真有人；第一遍译码后背景噪声变小，再听一遍、补漏删假。

剥掉术语，其实是两条工程常识：
- "先估出速度或多普勒展宽，再定基的维数和相关形状"。KL-BEM 接收机直接读取车速来构造 Jakes 相关；Huang 等用已知 f_max 定基的阶数 2⌈N·f_max·Δf⌉+1。
- "译码后用软符号当伪导频重估"。所有迭代 SP-OTFS 接收机都这么做。

把这两条接上"块稀疏贝叶斯证据"，是一次组合，不是新原理。

## 最接近的工作（7 篇）
1. **Z. Zhang & B. D. Rao，"Extension of SBL Algorithms for the Recovery of Block Sparse Signals with Intra-Block Correlation"，IEEE TSP 61(8), 2013**（[arXiv 1201.0862](https://arxiv.org/abs/1201.0862)，经代理读了 §I–III.C 原文）。先验 x_i ~ N(0, γ_i B_i)；§III.A 写"constraining B_i = B (∀i)"防过拟合，式 (7) 把 B 在所有块上汇总估计；BSBL-ℓ1 变体只在非零块上平均。**差在哪：** 这正是卡片的 diag(e)⊗C_Dop 加汇总估计核。卡片多出的只是"特征分解后逐维求和"的近似，以及用在通信接收机里。
2. **B. Liu, Z. Zhang, H. Fan, Q. Fu，"Fast Marginalized Block Sparse Bayesian Learning Algorithm"**（[arXiv 1211.4909](https://arxiv.org/abs/1211.4909)，技术报告，经代理读了 ar5iv 全文）。块边缘似然式 (19) ℒ(i) = log|I + A_i s_i| − q_iᵀ(A_i⁻¹ + s_i)⁻¹ q_i，按下降最大的块贪婪更新；BSBL-FM(2) 让各块共用一个 AR 系数。**差在哪：** 没有显式的 q² > s 增删门限，也没有做特征分解；共享的是 AR(1) 系数，不是完整核矩阵。卡片的 T_KMS > 1 是它在"块内列正交"近似下的特例。
3. **Y. Liu, Y. L. Guan, D. González G.，"BEM OTFS Receiver with Superimposed Pilots over Channels with Doppler and Delay Spread"，ICC 2022**（DOI 10.1109/ICC45855.2022.9838956），及专利 **US12627548B2**（[Google Patents](https://patents.google.com/patent/US20250055738A1/en)，前约 4 万字读到原文，其余只有摘要）。
   - 叠加导频、KL-BEM，基取 Jakes 相关 J₀(2πn·f_max·T_s) 的前 Q 个特征向量。
   - f_max 从车速输入得到，相关矩阵也可"用之前的信道估计更新"。
   - 判决符号作伪导频迭代，后续轮次提高阶数。
   - 仿真用 TDL-E、L = 21、125 km/h、QPSK（后三项出自摘要）。
   - 原文写到旧的 SP-OTFS 接收机"intended for channels with Doppler shift rather than Doppler spread, it has the worst performance"。
   - **差在哪：** 21 个抽头是稠密窗，全部估计，没有稀疏找径；没有用边缘证据定阶。这是"共享多普勒核 + 叠加导频 + TDL 多普勒展宽"的直接先例。
4. **F. Huang, Q. Guo, Y. Zhang, Y. V. Zakharov，"Message Passing-Based Joint Channel Estimation and Signal Detection for OTFS with Superimposed Pilots"，IEEE TVT**（[arXiv 2309.08177](https://arxiv.org/abs/2309.08177)，§I–III.B1 读到原文，仿真部分只有摘要）。GCE-BEM，系数用无信息先验（λ_c = ∞）；阶数由已知 f_max 定，第 1 轮后从 5 升到 9；仿真用 TDL-C、L = 5（出自摘要）。**差在哪：** 抽头窗短而稠密，不找径，不用跨抽头先验。它回答了 (c)：文献靠"短稠密时延窗 + 已知 f_max"绕开了找径。
5. **T. Zemen & A. F. Molisch，"Adaptive Reduced-Rank Estimation of Nonstationary Time-Variant Channels Using Subspace Selection"，IEEE TVT 61(9), 2012**（只看了摘要）。802.11p 车联网短帧，每帧从多普勒带宽和时延支撑两组假设里选一个，使估计误差的概率界最小，配迭代接收机，报告了误帧率。**差在哪：** 用的是专用梳状导频，不是叠加导频。但"每帧数据驱动地自动缩基的维数"已经有了，这就是卡片说的"慢速时自动缩到 1–2 维"。
6. **R. Prasad, C. R. Murthy, B. D. Rao，"Joint Approximately Sparse Channel Estimation and Data Detection in OFDM Systems Using Sparse Bayesian Learning"，IEEE TSP 2014**（只看了摘要）。块间共用支撑、AR(1) 时间相关的 K-SBL，以及联合数据检测的 J-SBL。**差在哪：** 时间相关跨 OFDM 符号，每个抽头是 AR 过程，不是帧内基展开；有"SBL + 软数据回送"这条结构。
7. **Benzine 等，"Models, Methods and Waveforms for Estimation and Prediction of (Doubly) Sparse Time-Varying Channels"**（[arXiv 2504.13762](https://arxiv.org/abs/2504.13762)，只看了摘要；作者归属卡片已写，我没有独立核实）。AFDM 下每个格点配一个 DPSS 小基处理分数多普勒，给出恢复条件。**差在哪：** 是离散径的离格近似，没有跨抽头共享核，没有叠加导频迭代。

数学来源（不算先例，只说明算子形式早就有）：多任务高斯过程的 ICM 模型，协方差是"任务矩阵 ⊗ 共享核"；水声领域有 fast TMSBL（[Frontiers 2024](https://www.frontiersin.org/articles/10.3389/frcmn.2024.1465902/full)），也用 γ_i B_i 先验加快速边缘似然。

**scoop-check 判定：Level 2 — High Overlap。**
- 对 Liu–Guan–González：核心洞见（共享 Jakes 时间相关、可由估计更新）和应用场景（叠加导频迭代接收机，TDL 多普勒展宽）重合；机制部分重合（已知核的 KL 基对边缘证据增删）；问题框架不同（稠密短窗对稀疏长窗）。
- 对 Zhang–Rao BSBL：机制和洞见重合（Level 3）。

差异只能写成这一句：
> Unlike Liu–Guan–González's KL-BEM SP-OTFS receiver, which uses a speed-derived Jakes correlation over a dense L-tap window, the proposal acquires a sparse delay support inside a ~100-sample window via BSBL-style block evidence with a frame-pooled kernel, re-run after decoding.

这条差异是否带来收益，还没有任何误帧率证据。

## 查新判断：**部分被做过**
- **已有：**
  - 克罗内克或共享块内相关的贝叶斯先验及其快速边缘似然（BSBL、BSBL-FM）。
  - 各抽头共用 Jakes 核的叠加导频 BEM 接收机，含伪导频迭代、TDL 多普勒展宽场景（Liu–Guan–González）。
  - 每帧自动选多普勒子空间的维数（Zemen–Molisch）。
- **未见：** 在叠加导频下、长时延窗内，把这三者合成"带证据门限的稀疏找径 + 译码后重捕获"。
- **(c) 的答案：** 文献没有直面"叠加导频在 TDL 上盲捕获崩塌"这件事。做法要么是短稠密窗加已知 f_max 或车速（Huang：L = 5；Liu：L = 21），要么换嵌入导频。

## 为什么没人做：**(2) 发现了但不重要**
证据：
1. **标准系统用专用导频处理 TDL 类信道。** 叠加导频文献在 TDL 上都取短而稠密的抽头窗，并假设已知 f_max 或车速，所以"在 100 个采样里找 18 个抽头"这个难处没有出现。
2. **"慢速自动缩维"在工程上是一维旋钮**：从车速或多普勒展宽估计定 D（KL-BEM 读车速，Huang 用 2⌈N·f_max·Δf⌉+1，Zemen–Molisch 每帧选一个假设）。卡片里慢速 `TDL_A`（ν_max = 0.25）上"比 `BOMP` 高 1.18 dB"的对照，是不知道速度、维数固定为 8 的 `BOMP`，属于对自己有利的口径（规则 16、6）。
3. **TDL 上的崩塌建立在项目自定的几组参数上**：ρ = .2、前缀 102、每个原始抽头 1+Poisson(3) 条随机射线（`driver_c1t.py:9`；l24 已指出这个生成器不是标准的连续 Jakes TDL）。另外，C1 和簇信道线 10-15 已降为讨论素材（STATE.md:101），主线是离散径的 `F0+CSTATE`。

## 真实系统里的影响
- **可能改变的决定：** 时延扩展长、多普勒展宽明显的信道里，叠加导频 AFDM 能否不用嵌入导频。
- **量级：** 在项目设定里，全部做成的天花板大约是把 `SPcb` 的 .78–.90 压到 `SPg_flat` 的 .16–.31 附近，或因克罗内克先验再低一点。这一点没有误帧率证据。卡片只有 30 帧的第 0 轮等效信干噪比，而且克罗内克上限臂同时白送了真时延、真抽头功率和真 Jakes 核，按规则 15 实际兑现常常减半。
- **前提有三处不成立或未核：**
  - **公平基线缺失：** 同开销下"OFDM 加专用导频加二维 Wiener"或"嵌入导频"都没比。
  - **卡片自己的数字指向反面：** 第 0 轮证据门限捕获的功率只有 0.71–0.75，漏掉 25–29%，而 `TDL_REPORT.md` 里 `SPcb` 在同一工况只漏掉 0.111，崩塌时伴随的是 5.7 个假时延（总共保留 16.3 个）。这只能说明证据门限比 `SPcb` 保守，用"假径换漏径"；崩塌主要来自假径，是我对读数的推测（可信度：中），没有检验过。如果属实，调 `SPcb` 的停止门限这个一维旋钮可能就够了。
  - **生成器依赖：** 每抽头 1–4 条随机射线时，同一帧里各抽头并不共享多普勒形状，只在统计平均意义上共享。卡片的"物理不变量"在本项目生成器下只是一个近似先验。

## 最强的反对意见
在 `TDL_B` 上，卡片的第 0 轮只比朴素 `BOMP` 高 0.10 dB，整个声称的收益都押在"译码后重新找径"上。而重新找径是所有迭代叠加导频接收机的标准动作，`SPcb` 现在恰好没做。

## 如果要做，最便宜的一步检验
放在 deinlab，约 0.15 CPU 核时：在 `TDL_B_d60`（8 dB、ρ = .2，200 帧新帧）上配对跑四臂。
- 臂 1：现有 `SPcb`
- 臂 2：`SPcb` 加"第 1 轮用软残差重新找径"，平坦先验，门限照旧
- 臂 3：`SPg_flat`（给真时延）
- 臂 4：`SPg_kron_oracle`（给真时延 + 真克罗内克核）

判据跑前写死：
- 臂 2 收掉了臂 1 到臂 3 误帧率差距的 ≥ 70%：找径缺口由标准做法解决，本卡的找径部分没有空间。
- 臂 4 相对臂 3 收掉的部分不到臂 3 到真信道差距的 50%：先验部分也没有杠杆，卡片淘汰。

两条都不触发，才值得把卡片收窄成"叠加导频长时延窗下的 BSBL 式找径"再做一次查新。

Sources:
- [Zhang & Rao, arXiv 1201.0862](https://arxiv.org/abs/1201.0862)
- [Liu, Zhang, Fan, Fu, arXiv 1211.4909](https://arxiv.org/abs/1211.4909)
- [Liu–Guan–González patent US20250055738A1 / US12627548B2](https://patents.google.com/patent/US20250055738A1/en)
- [Liu–Guan–González ICC 2022 (NTU record)](https://nanyangtechnologicaluniv.demo.elsevierpure.com/en/publications/bem-otfs-receiver-with-superimposed-pilots-over-channels-with-dop)
- [Liu–Guan–González TCOM 2022 (dblp)](https://dblp.dagstuhl.de/rec/journals/tcom/LiuGG22.html)
- [Huang et al., arXiv 2309.08177](https://arxiv.org/html/2309.08177v2)
- [Zemen & Molisch TVT 2012 (researchr)](https://researchr.org/publication/ZemenM12)
- [Zemen et al. TSP 2007 (dblp)](https://dblp.org/rec/journals/tsp/ZemenMKF07)
- [Prasad–Murthy–Rao (IISc)](https://eprints.iisc.ac.in/49656/)
- [arXiv 2504.13762](https://arxiv.org/abs/2504.13762)
- [Kanazawa et al., arXiv 2501.15935](https://arxiv.org/abs/2501.15935v3)
- [Fast TMSBL UWA, Frontiers 2024](https://www.frontiersin.org/articles/10.3389/frcmn.2024.1465902/full)
- [Wei et al. off-grid SBL OTFS, arXiv 2101.05629](https://arxiv.org/abs/2101.05629)
