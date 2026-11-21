# 底层逻辑查新与定位复核（Gemini, 2026-11-20）

> **会话污染披露（证据诚实）**：本文件写于与 Eric 的同一连续会话中。在收到本提示词之前，为回答 Eric 的前两轮提问，本会话已读取过 `STATE.md`、`handoff-20261120.md`、`tcom-narrative-skeleton-20261118.md`、`novelty-positioning-20261118.md`、`miao-fable-20261120.md` 与 `lit-diag-soft-variance-20261120.md`。在“第一步”完成并保存之前，本会话**未打开** `literature-uncertainty-model-check-20261118.md`、`recent-preprints-verification-20261118.md`、`.trellis/tasks/archive/2026-10/10-17-codelay-novelty/` 及 `.trellis/tasks/11-20-gamma0-exchange/research/kill-argument/`。下文中所有跨领域先行工作、DOI/arXiv 编号、公式与章节核验均在本轮通过 OpenAlex、Crossref、arXiv API 与 `pdftotext` 全文提取独立完成。
>
> **证据标注口径**：每篇引用均标明核验层级——`[已读原文]`（本轮下载 PDF/TeX 并核对具体节号或公式）、`[仅读摘要]`（经 OpenAlex/Crossref 核验元数据与摘要，未获取正文）、`[凭记忆，未核实]`（仅核验 DOI/书目，具体公式或定理凭知识记忆）。

---

# 第一步

## 立场先说

把名字、波形和参数外衣全部剥掉之后，这篇论文的三层内容在学术版图上呈现出一种**很不讨巧的劈裂**：

- **L1（接收机做法）本质上是“已知部件在编码 SP-AFDM 上的新组合”**。拆开来看，(a) 用码校验控制是否继续做昂贵重估计、(b) 固定基数单步替换 + 局部连续细化、(c) 用译码符号重建字典，每一块在邻近领域都有非常成熟的先例；唯一没有在文献里见到原样做过的，是把它们精确拼在**编码、分数 Doppler、叠加导频 AFDM**里，并靠“(d) 前端 F0 只漏 1–2 条弱径，因此只在约 1% 校验失败帧上做 2 步局部替换就够”这一实证条件把全帧复杂度压低一个数量级。但这不是算法发明，而是**系统架构与瓶颈驱动的工程综合**。
- **L2（打分里的不确定度规则）呈现极端分化**：“对角惩罚 `uI` 奖励把强径拆成重合双峰”在数学机制上属于已知效应的新映射，而它最致命的问题不是“被人做过”，是**文献里在分数 Doppler 支撑搜索中根本没人用 `uI`（打了一个稻草人）**，且你们自己的新帧实验（`res-20261120-01/03`）证明删掉 `Γ`（只用软均值甚至硬判决）在 FER 上与 `CODELAY` 打平。L2 唯一真正有非平凡新意的切片，是**同一不塌缩对角项 `u(I - D)` 在固定基数离散交换与过完备密网格 EM-SBL 之间的相反作用（镜像反转）**——但审稿人会立刻反问：既然你们的离散交换用 `Γ = 0` 就全面碾压了 SBL，那 SBL 那一半的镜像对你们主接收机到底有什么工程必要？
- **L3（AFDM 的同延标量精确性与 chirp 跨时延压制）是全篇最干净、最确实没有被直接写过的数学结构**，但它本身是一条 10 行就能证完的恒等式（Prop 1，`theory-astra-v2.tex` Eqs. (eq:af-full)–(eq:af-cross-bound)），单独撑不起一篇 TCOM regular paper，且在 `Γ = 0` 打平之后，它的定位已经从“接收机必需的最小充分协方差”退化成“解释为什么同延几何与数据无关、以及为什么 `CODELAY` 可以在零方差 FFT 下保持真双径表征优势的结构注记”。

下面按 L1、L2、L3 逐层摆证据，然后回答 SP-OTFS/AFDM 社区为何没用这套组合，最后点出最危险的三篇先行工作及残余可站立的主张。

---

## 一、L1（接收机做法）跨领域底层逻辑查新

### L1(a)：用译码器校验（LDPC 校验子 / CRC）当作免费失败检测器，仅在失败帧触发重估计

先说检索结论：我检索了 OpenAlex 与 arXiv（检索词见文末清单），**没有找到任何一篇论文把“LDPC 零校验子门控”直接接到“分数 Doppler 稀疏多径支撑重获取（swap/局部搜索）”上**。但往相邻领域退半步，“用译码校验/CRC 判断当前估计已够好或已失败，据此控制是否启动更重的信道重估计或候选信道重搜”的底层逻辑并不新鲜，至少存在三条高度重合的先例：

1. **Turbo / 迭代接收机中的校验子或 CRC 提前终止与双阶段切换**
   - **Jie Huang, Jianzhong Huang, C. R. Berger, S. Zhou, and P. Willett**, *"Iterative Sparse Channel Estimation and Decoding for Underwater MIMO-OFDM,"* EURASIP J. Adv. Signal Process., 2010, DOI: `10.1155/2010/460379` `[已读原文]`。
     - **重合与不重合**：Sec. 3.1–3.3（Eqs. (12)–(15), (19)–(22)）构建了一个 LDPC 编码 + 稀疏多径信道重估计（OMP / Basis Pursuit）的块级迭代接收机，用 LDPC 译码输出的软/硬符号重建传感矩阵 `Ψ`（Eq. (13)）重估稀疏信道；而且 Sec. 3.3 明确写明：*"During the decoding process, if all the parity check conditions of one data stream are satisfied, the decoder declares successful recovery of this data stream. In this case we assume that all symbols of this data stream are known without uncertainty."* 不重合在于：它用校验子满足来锁定已解出流并在常规迭代环里继续下一轮全局 BP/OMP，而不是在“便宜两轮前端失败后”单独切入一个**异构的局部支撑替换器**。
     - **重合程度**：**同一机制、邻近场景**（对 L1(c) 与 L1(a) 的早期形态接近抢先；对“失败后切换异构支撑替换模块”属已知部件的差异化用法）。
     - **审稿人攻击与回应**：审稿人会说“LDPC 校验判断成功 + 译码软符号重建稀疏字典重估信道，水声 MIMO-OFDM 2010 年就做过”。回应必须承认数据辅助稀疏重估与校验停止是经典套路，把区别收窄到：**水声 OFDM 是每帧跑固定套路的重估、没有面向低导频 SP 的两层异构架构（便宜固定支撑前端 `F0` + 仅在校验失败时重开连续 Doppler 支撑）**。
   - **Y. Kanazawa, H. Iimori, C. Pradhan, et al.**, *"Superimposed Pilot-Based OTFS: Will It Work?,"* IEEE TVT, 2025/2026, `arXiv:2501.15935v3`, DOI: `10.1109/tvt.2025.3608199` `[已读原文]`。
     - **重合与不重合**：面向 5G LDPC 编码的叠加导频 OTFS，Algorithm 1（Sec. III-C, Eqs. (28)–(32)）显式区分便宜的 `uncoded iteration` 与昂贵的 `coded iteration`（后者用 LDPC LLR 生成软符号副本消除数据对导频的干扰），以切换轮数 `(r_unc, r_cod)` 折中复杂度与性能。不重合在于：它的切换是**预设固定轮数**而非按帧的校验子失败触发，且信道模型是整数 DD 格点门限法，没有离格支撑搜索。
     - **重合程度**：**同一机制（两档复杂度折中）、极近场景（编码 SP-DD 波形）**，但缺少按帧失败条件触发与支撑重获取。
     - **审稿人攻击与回应**：审稿人会问“把 Kanazawa 里的固定轮数切换加上标准 LDPC 校验早停，不就是按失败触发重估吗？”确实如此——**校验早停 / 失败触发本身在工程上就是 turbo 接收机常识**，绝不能把“校验子触发”包装成方法创新，只能作为系统部署里的零开销门控说明。
   - **K. Adachi and M. Nakagawa**, *"Iterative Modified QRD-M Based on CRC Codes for OFDM MIMO Multiplexing,"* IEICE Trans. Commun., 2007, DOI: `10.1093/ietcom/e90-b.6.1433`（及 VTC'06 `10.1109/vtcf.2006.114`）`[仅读摘要]`；**Z. Liu, X. Liang, and C. Zhao**, *"CRC-aided turbo equalization for MIMO frequency selective fading channels,"* J. Electron. (China), 2007, DOI: `10.1007/s11767-005-0178-7` `[仅读摘要]`；**T.-H. Tsai and C.-H. Lin**, *"A low complexity channel estimation algorithm and architecture design in turbo codes with early termination techniques,"* IEEE CASSET, 2004, DOI: `10.1109/casset.2004.1322957` `[仅读摘要]`。
     - **重合程度**：**同一机制、不同场景**。这组早期文献说明：用 CRC 或校验条件判断是否终止/重跑更重的迭代检测或信道估计，在 turbo MIMO-OFDM 里已有二十年历史。

2. **直接把码校验满足度或译码输出当作信道候选选择器的现代工作**
   - **B. Shi, Y. Wu, P. Yuan, D. W. K. Ng, X.-G. Xia, and W. Zhang**, *"Code-Aided Channel Estimation in LDPC-Coded MIMO Systems,"* IEEE WCL, 2023, `arXiv:2311.07091v1`, DOI: `10.1109/lwc.2023.3333416` `[已读原文]`。
     - **重合与不重合**：Sec. III（Eqs. (2)–(8), Algorithms 1–2）直接用 LDPC 校验方程全部满足的后验概率 `P(Π_M = 0 | Y_d, H_hat)` 作为目标函数，对初始 LMMSE 信道估计 `H_hat` 做逐元素坐标上升微调，在 WiMAX LDPC + QPSK 上拿到约 1.3 dB FER 增益。不重合在于：它是平坦衰落 MIMO、优化连续矩阵元素、目标函数是软校验概率而非离散路径支撑最小二乘，且对每帧都跑（未做失败触发门控）。
     - **重合程度**：**只是表面相似 / 同一思想家族（LDPC 校验信息用于信道修复）、不同场景与不同优化对象**。
     - **审稿人攻击与回应**：审稿人可能提“用 LDPC 校验修信道已有人做”。回应很干净：Shi'23 把校验概率当目标函数修平坦 MIMO 连续系数，你们只是把硬零校验子当触发开关、把字典最小二乘用于稀疏多径支撑重获取，两者互补不冲突。
   - **C.-H. Chen, I. Nikoloska, and W. van Houtum**, *"Physics-Aware Initialization Refinement in Code-Aided EM for Blind Channel Estimation,"* `arXiv:2504.11241v2`, Oct. 2025 `[已读原文]`；以及 **C. Wiame, K. R. Duffy, and M. Médard**, *"Joint Error Correction and Fading Channel Estimation Enhancement Leveraging GRAND,"* IEEE ICC, 2025, `arXiv:2506.14756v1`, DOI: `10.1109/icc52391.2025.11161726` `[已读原文]`。
     - **重合与不重合**：这两篇 2025 年的工作都体现“初始信道估计落在坏盆地时，在局部/物理候选集合里重搜信道并用译码器确认”的思想：Chen'25（Sec. II-C）针对盲 EM 陷入相位/移位局部极小，用有限物理候选模型配合译码输出选优；Wiame–Duffy–Médard'25（Sec. III-A）在初始导频信道估计附近撒一组候选信道，并用 ORBGRAND/CRC 后验似然挑出最可信码字。但两者都面向低维/平坦信道、没有稀疏支撑替换，也没有失败触发的二层门控。
     - **重合程度**：**同一机制（以译码验证兜底局部信道重搜）、不同场景**。

**L1(a) 小结**：**已知技巧用在新场景**。用 LDPC 零校验子当免费门控，只在失败帧启动昂贵第二级处理，在通信系统里属于显而易见的工程实践（本质上等价于“两轮固定支撑前端 + 校验早停，不通过才切入重获取”），不能作为独立方法创新宣称。

---

### L1(b)：固定基数的单步替换式局部搜索（+ Schur 补快速打分 + 局部连续 Doppler 细化）

这一块是 **L1 里撞车最严实的地方**。你代码里 `geometry_reopen.py`（固定槽位 `P = 8`，每步遍历 `P × C` 个单槽替换候选，用秩-2 Schur 补算精确最小二乘剖面目标下降，最多替换 `max_edits = 2` 次，随后对当前支撑做局部 1D 连续 Doppler 坐标细化）在稀疏恢复、谱估计和统计变量选择三个领域都有几乎同构的标准算法：

1. **Single Best Replacement (SBR)**：**C. Soussen, J. Idier, D. Brie, and J. Duan**, *"From Bernoulli–Gaussian Deconvolution to Sparse Signal Restoration,"* IEEE TSP, vol. 59, no. 10, pp. 4572–4584, Oct. 2011, DOI: `10.1109/tsp.2011.2160633`, HAL: `hal-00443842` `[已读原文]`；及其同伦扩展 **C. Soussen, J. Idier, J. Duan, and D. Brie**, IEEE TSP 2015, `arXiv:1406.4802`, DOI: `10.1109/tsp.2015.2421476` `[已读原文]`。
   - **重合与不重合**：Soussen'11 Sec. III-B（Table I, Eq. (6)）提出的 SBR 就是对活跃支撑 `Q` 穷举测试全部单元素增/删替换 `Q • i`，按精确最小二乘目标下降择优；更致命的是 Sec. IV-A（Eq. (8)）与 Appendix C **已经给出了基于 Cholesky 分解和块逆 / 秩-1 更新的快速精确单步打分公式**，把单次替换评估降到 `O(k^2)`，并且专门以“高度相关字典（highly correlated dictionaries）”下的稀疏脉冲反卷积作为主战场（Sec. V）。唯一差异在于：SBR 面向惩罚形式 `‖y - Ax‖² + λ‖x‖₀`（单步是加 1 或删 1），而你们是固定基数 `|S| = P`（单步是删 1 加 1 的 1-swap，且最多做 2 步），再加上后续连续 Doppler 局部细化。
   - **重合程度**：**同一机制、不同场景（对离散替换 + 精确块逆快速打分近乎直接覆写）**。
   - **审稿人攻击与回应**：审稿人会直接指出：“你的 Prop 3（紧凑 Schur 补交换与 Cholesky 精确等价）和固定步数单槽替换，本质就是定基数受限预算的 SBR，块逆/Cholesky 增量更新在 Soussen'11 已经标准了。”**回应不能硬顶创新**，必须明确声明替换核与 Schur 补是 SBR/stepwise regression 的标准实现适配，只把 `CPPField` 频域互相关结合 AFDM 字典作为工程实现细节。

2. **统计优化中的固定基数 / $\ell_0+\ell_2$ 局部 1-swap / k-swap 与 splicing 算法**
   - **H. Hazimeh and R. Mazumder**, *"Fast Best Subset Selection: Coordinate Descent and Local Combinatorial Optimization Algorithms,"* Operations Research, 2020, `arXiv:1803.01454`, DOI: `10.1287/opre.2019.1919` `[已读原文]`。
     - **重合与不重合**：Sec. 4（Problem (14), Algorithm 2 `CD-PSI(k)`）直接针对 `L0` 和 `L0+L2`（含岭惩罚！）问题，在坐标下降后做局部组合 **1-swap / k-swap**（从支撑中换出 `≤ k` 个变量、换入 `≤ k` 个候选变量使目标下降），并指出在高度相关特征下，局部 swap 远优于无 swap 的方法（Sec. 6, Fig. 2）。
     - **重合程度**：**同一机制、不同场景**。
   - **J. Zhu, C. Wen, J. Zhu, H. Zhang, and X. Wang**, *"A polynomial algorithm for best-subset selection problem,"* PNAS, 2020, DOI: `10.1073/pnas.2014241117` `[仅读摘要]`（ABESS：固定基数最优子集选择的 `splicing` 局部交换算法）；以及 **W. Xie and X. Deng**, *"Scalable Algorithms for the Sparse Ridge Regression,"* SIAM J. Optim., 2020, `arXiv:1806.03756`, DOI: `10.1137/19m1245414` `[仅读摘要]`。
     - **重合程度**：**同一机制、不同场景**。

3. **连续参数（离格频率 / 多径）的循环局部替换与细化**
   - **B. Mamandipoor, D. Ramasamy, and U. Madhow**, *"Newtonized Orthogonal Matching Pursuit: Frequency Estimation Over the Continuum,"* IEEE TSP, 2016, `arXiv:1509.01942`, DOI: `10.1109/tsp.2016.2580523` `[已读原文]`。
     - **重合与不重合**：Algorithm 1（Sec. III-B）在过采样网格（推荐 4× 即 0.25 bin！）上粗搜新频率，做 `Single Refinement` 后，再对全部已选频率做 `Cyclic Refinement`（循环逐条固定其余路径、在残差上局部连续细化当前路径），最后做联合最小二乘投影。不重合在于 NOMP 是从空集前向增长（无显式“踢掉一条错径、全局换入一条新径”的 swap 步）。
     - **重合程度**：**同一机制、邻近场景**（且 2026 年已经直接搬进 AFDM：**Y. Ma et al., `arXiv:2607.05082`** 与 **S. Li, C. Pan, H. Ren et al., `arXiv:2608.11998`** `[均已读原文]`，两篇都在用 NOMP / CC-NOMP 做分数时延-Doppler AFDM 估计！）。
   - **J. Li and P. Stoica**, *"Efficient mixed-spectrum estimation with applications to target feature extraction,"* IEEE TSP, 1996, DOI: `10.1109/78.485924` `[凭记忆，未核实]`（**RELAX** 算法）与 **B. H. Fleury, M. Tschudin, R. Heddergott, D. Dahlhaus, and K. I. Pedersen**, *"Channel parameter estimation in mobile radio environments using the SAGE algorithm,"* IEEE JSAC, 1999, DOI: `10.1109/49.753729` `[凭记忆，未核实]`（**SAGE**）。
     - **重合与不重合**：RELAX 与 SAGE 都是雷达/无线多径参数估计的鼻祖级范式——固定模型阶数 `K`，循环移除第 `k` 条路径、在残差上全局/局部重搜第 `k` 条路径的连续频率/时延并更新幅度。甚至 2026 年 10 月刚出的 **R. Wang, C. Pan, H. Ren et al.**, *"Model-Order-Adaptive Channel Estimation for AFDM Systems with Fractional Delay and Doppler,"* `arXiv:2610.09970v1` `[已读原文]`，就在 AFDM 里用改进 SAGE 做离格路径增删（残差检验加径 + 条件剔除冗余径）！不重合在于 RELAX/SAGE 逐条对残差做近似解耦更新，而你们的 `CSTATE` 是直接评估全部 `P × C` 组合的精确联合最小二乘（带岭/协方差）剖面目标。
     - **重合程度**：**同一机制、相同/邻近场景**。
   - **带替换/回溯的贪心稀疏恢复家族**：**W. Dai and O. Milenkovic**, *"Subspace Pursuit,"* IEEE TIT, 2009, `arXiv:0803.0811`, DOI: `10.1109/tit.2009.2016006` `[已读原文]`；**D. Needell and J. A. Tropp**, *"CoSaMP,"* ACHA, 2009, DOI: `10.1016/j.acha.2008.07.002` `[凭记忆，未核实]`；**T. Zhang**, *"Adaptive Forward-Backward Greedy Algorithm (FoBa),"* IEEE TIT, 2011, DOI: `10.1109/tit.2011.2146690` `[凭记忆，未核实]`；**Z. Gui, Y. Li, C. Zhou et al.**, *"3D-ESP: An Efficient Subspace Pursuit Algorithm for MIMO-OTFS Channel Estimation,"* IEEE TVT, 2024, DOI: `10.1109/tvt.2024.3421934` `[仅读摘要]`。
     - **重合程度**：**同一机制、邻近场景**（Subspace Pursuit 已经被直接用于 OTFS 稀疏信道估计）。

**L1(b) 小结**：**已被做过（算法范式层面）**。固定基数替换（SBR / 1-swap）+ 0.25 bin 网格 + 局部连续细化（NOMP / RELAX / SAGE）+ 块逆/Cholesky 快速打分，每一个环节在信号处理与统计优化中都已高度成熟。论文绝对不能把 L1(b) 当成算法新颖性卖点。

---

### L1(c) 与 L1(d)：“用判决数据重建字典”以及“前端基本正确，所以局部搜索就够”

- **L1(c)（用译码软/硬判决重建传感字典做稀疏信道重估计）**：**已被做过**。
  - 跨领域先例：**Huang et al., EURASIP JASP 2010**（`10.1155/2010/460379`, Eq. (12)–(15) `[已读原文]`，UWA MIMO-OFDM 用 LDPC 软/硬输出重建字典做 BP/OMP）；**T. Kang and R. A. Iltis**, IEEE JSAC 2008, DOI: `10.1109/jsac.2008.081205` `[仅读摘要]`（UWA LDPC-OFDM 迭代匹配追踪）；**R. Prasad, C. R. Murthy, and B. D. Rao**, IEEE TSP 2014 `[凭记忆，未核实]`（OFDM 联合 SBL 数据辅助）；**W. Yuan et al.**, IEEE WCL 2021, DOI: `10.1109/lwc.2021.3088836` `[仅读摘要]`（SP-OTFS 数据辅助）；**Z. Wei et al.**, IEEE TWC 2022, `arXiv:2101.05629`, Remark 1 & Sec. VI-D `[已读原文]`（离格 SBL-OTFS 数据辅助）；**A. Mehrotra et al.**, `arXiv:2305.15855` `[已读原文]`（SP-OTFS MIMO 数据辅助 SBL）；**Y. Luo et al.**, IEEE TCOM 2026, `arXiv:2607.18881` `[已读原文]`（SP-AFDM 数据辅助离格 SBL）；以及 **9 天前刚挂上 arXiv 的 Z. Yuan, Q. Guo, M. Jin, Z. Liu, and P. Xiao**, *"Message-Passing-Based Bayesian Joint Channel Estimation and Data Detection for Pilot-Guard-Free AFDM,"* `arXiv:2611.14877v1` (11 Nov 2026) `[已读原文]`！
  - **重合程度**：**同一机制、完全相同场景（已被抢先）**。

- **L1(d)（“前端基本正确，通常只错 1–2 条弱径，所以有界局部替换够用”这一瓶颈诊断与架构条件）**：
  - 检索中**没有找到**在低导频 SP-AFDM（`ρ = 0.25–0.30`）下用约束 MCRB + Genie 支撑分解定量证明“73%–81% 的 NMSE 离界差距由漏检弱时延主导、从而证明 2 步局部替换足以替代全帧 SBL”的先行工作。
  - **重合程度**：**新（作为 SP-AFDM 系统诊断与设计依据）**；但注意，这属于**实证诊断发现**，而非普遍数学定理——一旦导频比低到 `ρ < 0.25` 导致 `F0` 大面积崩塌，该条件本身也失效（`res-20261119-06`）。

- **L1 整体（(a)–(d) 组合）结论**：**已知部件、新的组合**（配合一个新的系统瓶颈诊断 L1(d)）。在工程与系统层面上，它对 Luo 式数据辅助 SBL 的 1.3–5.3 dB FER 优势与 11.9×–16.0× 单核加速（`res-20261118-03`，含 1% 触发率摊销）以及把最优导频比压到 `ρ = 0.25–0.30` 的 1.14 dB 系统增益（`res-20261119-06`）是真实的；但必须清醒：审稿人不会为“部件本身”买单，只会为**“为什么现有全帧 SBL 路线走偏了 + 你们用 MCRB 诊断出的漏径结构如何自然导出这个轻架构 + 对 2026 SOTA 的大幅系统优势”**买单。

---

## 二、L2（打分里的不确定度规则）跨领域底层逻辑查新

把 L2 拆成四条底层命题来查，真相会非常刺眼但也非常清楚：

### L2-1：把软符号不确定度作为期望 Gram 二阶矩 `E[ΦᴴΦ] = Φ̄ᴴΦ̄ + Γ` 引入信道估计

- **经典迭代/Turbo 软符号信道估计（无稀疏支撑搜索）**：
  - **K. Fang, L. Rugini, and G. Leus**, *"Block Transmissions over Doubly Selective Channels: Iterative Channel Estimation and Turbo Equalization,"* EURASIP JASP, 2010, DOI: `10.1155/2010/974652` `[已读原文]`（Sec. 4.1, Eqs. (22)–(25)）：在双色散 BEM-OFDM 中，明确把未知数据项写成 `D_o (I_{Q+1} ⊗ diag(s - m) F_L) h` 并将其协方差 `R_{d_f^o}` 计入 LMMSE 估计器（Eq. (25)）。注意这是**观测空间协方差**（边缘化了信道先验 `R_h`），不是坐标空间的 `uI`。
  - **A. Osinsky, A. Ivanov, D. Lakontsev, et al.**, IEEE VTC 2020, `arXiv:2003.09317` `[已读原文]`（Eqs. (2)–(3)）：明确写出 `E[x xᴴ] = μ μᴴ + diag(v)`，在逐子载波标量信道上精确退化为标量权重。
  - **A. Kocian and B. H. Fleury**, IEEE TCOM 2003, DOI: `10.1109/tcomm.2003.818091`；**C. Cozzo and B. L. Hughes**, IEEE TCOM 2003, DOI: `10.1109/tcomm.2003.815062`；**S. Song, A. C. Singer, and K.-M. Sung**, IEEE TSP 2004, DOI: `10.1109/tsp.2004.834270` `[均核验 DOI，正文未读，凭记忆未核实]`。
- **稀疏/多径与双色散现代接收机中的软方差二阶矩**：
  - **Z. Yuan, Q. Guo, M. Jin, Z. Liu, and P. Xiao**, `arXiv:2611.14877v1` (11 Nov 2026) `[已读原文]`（Pilot-Guard-Free AFDM, 分数 Doppler）：Eqs. (88)–(92) 在因子图消息传递中更新路径增益 `h_k` 时，显式把符号后验方差 `ν_{x_n}` 以精确逐符号二阶矩 `|x̂_n|² + ν_{x_n}` 的形式放进分母，但因为是消息传递/AMP 近似，不同路径之间解耦为逐路径边缘高斯消息，没有联合 Gram 矩阵中的跨原子 `Γ` 块，也没有离散支撑替换。
  - **F. Huang, Q. Guo, Y. Zhang, et al.**, IEEE TVT 2024, `arXiv:2309.08177v2`, DOI: `10.1109/tvt.2024.3378833` `[已读原文]`（SP-OTFS BEM 消息传递）：同样在逐符号权重里使用 `|x̂|² + v_x`。
  - **高维统计 EIV（Errors-in-Variables）稀疏回归**：**M. Rosenbaum and A. B. Tsybakov**, Ann. Stat. 2010, DOI: `10.1214/10-aos793` `[凭记忆，未核实]`；**P.-L. Loh and M. J. Wainwright**, Ann. Stat. 2012, `arXiv:1109.3714`, Eqs. (2.4)–(2.5) `[已读原文]`；**H. Zhu, G. Leus, and G. B. Giannakis**, IEEE TSP 2011, DOI: `10.1109/tsp.2011.2109956` `[仅读摘要]`（Sparsity-Cognizant TLS）；**Y. Chen and C. Caramanis**, `arXiv:1206.0823` (2012) `[已读原文]`（Noisy-Dictionary OMP）。
    - **关键机制辨析（极易被审稿人或自己搞混）**：经典 EIV（`Z = X + W`，观测到的字典 `Z` 加了独立噪声 `W`）里，`E[ZᵀZ] = XᵀX + E[WᵀW]`，所以 Loh–Wainwright Eq. (2.4) 是**减去** `-E[WᵀW]`（导致非凸）。而数据辅助信道估计用的是**后验均值** `x̄ = E[x|Y_prev]`，真符号满足 `x = x̄ + ε`（Berkson / 贝叶斯二阶矩结构），因此 `E[B(x)ᴴB(x)] = B(x̄)ᴴB(x̄) + Γ` 是**加上** `+Γ`（保持凸性）。有意思的是，Chen & Caramanis (`1206.0823`, Sec. I, p. 2) 指出，即使在经典 EIV 里，**不带噪声协方差修正的标准 OMP 也能在列独立时实现支撑恢复**，协方差修正主要修系数 `ℓ2` 偏差——这与你们今天测出的“支撑交换中 `Γ = 0` 不出幻影，仅略影响增益初始化尺度（`Z-sel`）”在直觉上高度呼应。
- **重合程度**：期望 Gram 二阶矩本身是**已被做过**的标准数学对象。

### L2-2：对角二次惩罚 `u‖h‖²` 在相干/重合原子上奖励拆径（产生分身/假路径）

- **H. Zou and T. Hastie**, *"Regularization and Variable Selection Via the Elastic Net,"* JRSS-B, 2005, DOI: `10.1111/j.1467-9868.2005.00503.x` `[核验 DOI，Lemma 2 凭记忆未核实]`：证明严格凸的 `ℓ2` 惩罚在完全相同的两个预测变量上唯一极小化于均分系数 `h/2, h/2`（grouping effect），目标惩罚减半。
  - **重合与不重合**：在固定支撑的增益拟合层，`(u + λ)‖h‖²` 对两个重合原子均分增益使惩罚从 `u|h|²` 降为 `(u/2)|h|²`，**在纯代数上就是 Zou–Hastie 效应的直接推论**。不重合在于：Zou–Hastie 把这当作 `ℓ1 + ℓ2` 回归中“成组选入相关特征”的优点；而你们放在**固定基数 `ℓ0` 支撑交换**的剖面目标 `J*(S)` 里，它变成了一个把强径拆成同延克隆、排挤漏检弱真径的灾难性 bug——而且惩罚来源不是人为调出来的岭参数 `λ`，而是把原本**拆分不变**的算子半范数 `tr(HVHᴴ)` 错做成坐标对角近似 `u‖h‖²`。
  - **重合程度**：**同一机制、不同场景（代数内核已知，通信物理来源与离散支撑决策后果为新映射）**。
- **连续谱/离格稀疏恢复与雷达/声呐/GNSS 中的“分身峰 / 虚假路径”**：
  - **A. Fannjiang and W. Liao**, *"Coherence-Pattern Guided Compressive Sensing with Unresolved Grids,"* SIAM J. Imaging Sci., 2012, `arXiv:1106.5177`, DOI: `10.1137/110838509` `[已读原文]`（Sec. 2–3, Algorithm 1 BOMP & Algorithm 2 LO/BLOOMP）：指出欠分辨相干网格下，标准 OMP/SP 会在真实强峰的相干带内反复选出虚假邻近峰，提出**带排除（Band Exclusion, BE）**（你们实验里的 `A2n` 近邻禁令正是它的同类思路！）与**局部替换优化（LO）**，以每步把支集里单个原子替换为相干带内最小残差原子的方式修偏。
  - **V. Duval and G. Peyré**, *"Exact Support Recovery for Sparse Spikes Deconvolution,"* Found. Comput. Math. / `arXiv:1306.6909` (2015) `[已读原文]`（以及 2017 薄网格续作 `[凭记忆，未核实]`）：分析连续/细网格 BLASSO 在网格失配或噪声下把单峰分裂成相邻双峰（2-spike / twin-peak phenomenon）。
  - **雷达 / 声呐多径“鬼目标”文献**：**L. Zheng, J. Long, and M. Lops**, IEEE TSP 2024, DOI: `10.1109/tsp.2024.3384750` `[仅读摘要]`；**H. Luo et al.**, IEEE TGRS 2023, DOI: `10.1109/tgrs.2023.3335454` `[仅读摘要]`；**M. Leigsnering, F. Ahmad, and M. G. Amin**, IEEE TAES 2014, DOI: `10.1109/taes.2013.120528` `[仅读摘要]`。
    - **重合与不重合**：**只是表面相似**。雷达/声呐/穿墙成像里的“multipath ghost target”几乎全部指**物理二次反射产生的镜像虚假目标**，不是算法里因对角方差惩罚 `uI` 导致的“同延迟重合分裂”。而 Fannjiang–Liao (2012) 和 Duval–Peyré (2015) 研究的则是**网格失配/高相干字典本身的分裂**——你们通过控制变量（同网格、同细化下 `S` 89.1% vs `CD`/`Z` 1.84%）已经把它和网格失配拆开了。

### L2-3：拆分不变准则（不加 `Γ`、硬判决或精确算子协方差）——与文献缺口带来的“靶子危机”

这里必须把最痛的事实摆在台面上：
- 在我们查过的全部分数 Doppler / 离格数据辅助稀疏估计文献中——包括 **Y. Luo et al. TCOM'26** (`2607.18881`)、**Z. Wei et al. TWC'22** (`2101.05629`)、**A. Mehrotra et al.** (`2305.15855`)、**Z. Yuan et al. Nov'26** (`2611.14877`)、**J. Huang et al. 2010** (`10.1155/2010/460379`)——**没有找到一篇论文在离格支撑搜索或 SBL 中把软符号方差写成坐标对角岭 `uI`（`u‖h‖²`）**。文献要么直接不加 `Γ`（硬判决或软均值直填，即 `Z` / `H` 路线），要么在观测/消息传递坐标中按逐符号二阶矩 `|x̂_n|² + v_n` 加权（`Yuan'26`, `Huang–Guo'24`），要么像 **S. Wang, Y. Li, and J. Wang** (WCSP 2013, DOI: `10.1109/wcsp.2013.6677226`, MU-SBL `[仅读摘要]`) 那样把字典扰动吸收为观测端非独立同分布噪声方差。
- 而在你们自己今天完成的三组新帧对照实验（`res-20261120-01/02/03`）里：**直接删掉 `Γ`（`Z`）在 P1 1,952 个触发键上与 `CODELAY` 打平（救回 653 vs 659，首步幻影 36 vs 36），在 MIXED8 真双径 2,400 帧上 FER 仍落在你们自定的 `±1.5 pp` 等效裕量内（`+0.54 pp [-0.03, +1.13]`，仅在 0.35-bin 真双径占位表征上有 `-1.54 pp` 的小幅优势）**；甚至硬判决 `H` 在 P1 上救回 665 个（比 `CODELAY` 还多 6 个），在 MIXED8 上只比 `CD` 差 `0.67 pp`。
- **审稿人攻击**：这正是刚才那段致命评审攻击的根源——**文献里没人用 `uI`，而按文献常规不加 `Γ` 就和你们推导出来的 `CODELAY` 在 FER 上打平**。因此，“必须用精确 `CODELAY` 协方差块”这一主张已经彻底站不住；L2 只能改口为**“跨估计器边界诊断与反直觉警示”**。

### L2-4：同一个对角项 `uI` 在过完备密网格 SBL 中反而有益（给亚分辨差模加下限）

- **SBL 在相干/过完备字典上的经典理论与变体**：
  - **D. P. Wipf and B. D. Rao**, IEEE TSP 2004, DOI: `10.1109/tsp.2004.831016` `[核验 DOI，凭记忆未核实]`；**D. P. Wipf and S. Nagarajan**, IEEE JSTSP 2010, DOI: `10.1109/jstsp.2010.2042413` `[核验 DOI，凭记忆未核实]`：证明 SBL 的全局极小比 `ℓ1` 更不易分裂，且具有优于 `ℓ1` 的局部极小结构，但在强相干列下 EM-ARD 仍受局部极小与超参数耦合影响。
  - **Z. Zhang and B. D. Rao**, IEEE JSTSP 2011, `arXiv:1102.3949`, DOI: `10.1109/jstsp.2011.2159773` `[已读原文]`（Block SBL）：通过引入块内相关性矩阵显式建模相邻/相关原子；**Z. Yang, L. Xie, and C. Zhang**, IEEE TSP 2013, DOI: `10.1109/tsp.2012.2222378` `[凭记忆，未核实]`（Off-Grid SBL）；**P. Gerstoft, C. F. Mecklenbräuker, A. Xenaki, and S. Nannuru**, IEEE SPL 2016, `arXiv:1602.09120` `[已读原文]` 与 **S. Nannuru, K. L. Gemba, P. Gerstoft**, Signal Processing 2019 `[仅读摘要]`；**D. Shutin and B. H. Fleury**, IEEE TSP 2011, DOI: `10.1109/tsp.2011.2140106` `[已读原文]`（VB-SAGE 自动修剪多余路径）。
  - **我检索了** `"sparse Bayesian learning"` 配合 `"diagonal loading" / "coherent" / "collinear" / "duplicate" / "measurement matrix uncertainty"`（OpenAlex + arXiv，见检索词清单），**未找到任何文献系统对比过“同一个对角数据不确定度项 `uI` 在固定基数离散支撑交换 vs 过完备密网格 EM-SBL 中的符号反转（镜像失败），并用同延核 `D_N` 的和模/差模谱分解做前瞻干预验证”**。
- **L2 整体结论**：
  - “期望 Gram 二阶矩” = **已被做过**；
  - “`u‖h‖²` 奖励重合原子均分” = **已知技巧/效应（Zou–Hastie）用在新场景**；
  - “离散交换 vs 过完备密网格 SBL 中同一不塌缩项 `u(I - D)` 的镜像反转 + 自洽性设计边界” = **新**（有前瞻干预证据 `res-20261119-03` 和 `res-20261120-01/03`）。但它是一个**诊断性/警示性理论发现**，不是贡献主解码增益的算法模块；且 SBL 那一侧本身仍是实验现象而非 ARD 迭代收敛定理，标量 `R0` 依然比理论构造的 `U2` 略好 2.6 pp。

---

## 三、L3（AFDM 结构：同延精确标量 `u·D_N(Δν)` + chirp 跨时延压制）查新

- **AFDM 基础理论与最新信道估计文献**：
  - **A. Bemani, N. Ksairi, and M. Kountouris**, *"Affine Frequency Division Multiplexing for Next Generation Wireless Communications,"* IEEE TWC 2023, `arXiv:2204.12798v2` `[已读原文]`（Sec. III-D, effective channel matrix 与 `c_1 = (2k_max + 1)/(2N)` 满多样性分离条件）：确立了 DAFT 基的恒模性与不同整数时延路径在 DAFT 域中被 chirp 移位 `2 N c_1 Δℓ` 错开的波形结构。
  - **近期 AFDM 信道估计全文核查**：我直接检查了 **Zheng et al. (`2404.10232`)**、**Y. Luo et al. (`2607.18881`)**、**Yuan et al. (`2611.14877`, Nov 2026)**、**Ma et al. (`2607.05082`)**、**Li et al. (`2608.11998`)**、**Wang et al. (`2610.09970`)** 的全文，以及 **Y. Lan & Y. Liu (SSRN 7661835, 2026, 摘要不可见，未核实)**。
  - **重合与不重合**：Bemani'23 给出的是**确定性信道输入输出关系**中的 chirp 时延-Doppler 分离，没有推导数据辅助估计里**非均匀符号后验方差 `diag(v)` 经 DAFT 投影后的期望 Gram 闭式** `(\Gamma_F)_{ij} = e^{2\pi i c_1(\ell_i^2 - \ell_j^2)} D_N(\Delta\nu + 2Nc_1 d) \hat{v}[d \bmod N]`（`theory-astra-v2.tex` Prop 1, Eq. (eq:af-full)），也没有证明“因 DAFT 基时域恒模，任意异方差 `v` 下同延迟块精确坍缩为单标量 `u·D_N(Δν)`、而跨时延残差在 `|d| ≥ 2` 时被 chirp 移位压进 Dirichlet 旁瓣”。
  - **重合程度**：**新（对 AFDM 既有 DAFT/chirp 结构在软符号二阶矩上的精确推论）**。
  - **审稿人攻击与回应**：审稿人会说两句大实话：① 证明只有十几行，本质是 Bemani'23 的 DAFT 恒模 + 线性 chirp 移位带入 `tr(U_iᴴ U_j diag(v))` 的直接代数展开；② 既然你们自己的 `res-20261120-01/03` 证明交换阶段把 `Γ` 置零（`Z`）也能拿到同等 FER，这条精确闭式在接收机里的不可替代性大打折扣（仅剩 MIXED8 上 `-1.54 pp` 的双径占位小优势和 `Z-sel` 在 P1 上 `+0.51 pp` 的增益初始化微调）。回应只能诚实定位：Prop 1 解释了**为什么 AFDM 的同延几何本质与数据无关（`E·D + u·D = N·D`）**，从而从第一性原理给出“为什么 `Γ = 0`、`H` 与 `CODELAY` 落在同一自洽类”，同时把 `CODELAY` 作为该自洽类中零方差 FFT、严格匹配后验二阶矩的闭式成员。

---

## 四、回答关键问题：为什么 SP-OTFS / SP-AFDM 这一行没用“校验触发 + 局部替换”？

这个问题**不需要猜，文献全文数据直接给出答案**。我下载并逐篇核验了 13 篇 SP-OTFS / SP-AFDM 及 2026 离格 AFDM 论文的全文仿真设定（统计精确词边界正则 + 人工核对仿真节）：

| 论文（均已读原文） | 波形 / 导频 | 分数 Doppler？ | 是否带信道编码？ | 核心评测指标 | 信道更新方式 |
|---|---|---|---|---|---|
| Mishra et al., TWC'21 (`2010.15066`) | SP-OTFS | 仅讨论/整数为主 | **无编码** | NMSE + uncoded BER | 每帧迭代阈值/LMMSE |
| Aghda et al., 2022 (`2212.09280`) | SP-OTFS | 否/离散字典 | **无编码** | NMSE + uncoded BER | 每帧 CS |
| Mehrotra et al., 2023 (`2305.15855`) | SP-OTFS MIMO | 是（网格） | **无编码** | NMSE + uncoded BER | 每帧 DA-BL (EM-SBL) |
| Huang–Guo et al., TVT'24 (`2309.08177`) | SP-OTFS | 是（BEM） | **无编码** | NMSE + uncoded BER | 每帧消息传递 BEM |
| Zheng et al., TVT'25 (`2404.10232v1`) | SP-AFDM | 否（整数） | **无编码** | NMSE + uncoded BER | 每帧干扰消除 + 门限 |
| **Y. Luo et al., TCOM'26 (`2607.18881`)** | **SP-AFDM-ISAC** | **是（离格）** | **无编码** | **NMSE + uncoded BER** | **每帧离格 GE-SBL** |
| **Yuan–Guo et al., Nov'26 (`2611.14877`)** | **无保护带 AFDM** | **是（离格）** | **无编码** | **NMSE + uncoded BER** | **每帧联合贝叶斯 MP** |
| Ma–Ni et al., Jul'26 (`2607.05082`) | 脉冲成形 AFDM | 是（离格） | **无编码** | NMSE + uncoded BER | 每帧导频 NOMP |
| Li–Pan–Ren, Aug'26 (`2608.11998`) | AFDM-ISAC | 是（离格） | **无编码** | RMSE/CRB | 每帧导频 CC-NOMP |
| Wang–Pan–Ren, Oct'26 (`2610.09970`) | AFDM | 是（离格） | **无编码** | NMSE + uncoded BER | 每帧导频改进 SAGE |
| Lei et al., Jan'26 (`2601.22523`) | SP-OTFS | 是 | **无编码**（仅引言提 polar） | NMSE + uncoded BER | 端到端神经网络 U-Net |
| Wei et al., TWC'22 (`2101.05629`) | OTFS（非 SP 主体） | 是（离格） | 仅 Sec. VI-D Fig. 9 用 1/2 卷积码 | **仅报 NMSE** | 每帧数据辅助 SBL |
| **Kanazawa et al., TVT'26 (`2501.15935v3`)** | **SP-OTFS** | **否（整数，结论列为开放问题）** | **5G LDPC** | **NMSE + coded BER + throughput** | **固定轮数 `r_unc + r_cod` 干扰消除 + 整数门限** |

这张表已经把原因说透了：

1. **最直接的实证原因：SP-OTFS/AFDM 领域压倒性多数论文不带信道编码、只跑 uncoded BER 和 NMSE（上表 13 篇里有 11 篇无编码，9 篇 SP/无保护带里有 7 篇无编码）**。没有信道编码，就没有免费的 LDPC 校验子 / CRC 触发器；在 uncoded BER 指标下，哪怕一帧只错 1% 比特也无法按帧门控分流，更不存在“99% 的帧靠便宜前端直接校验归零，把重获取成本摊薄 100 倍”的运行区。
2. **仅有的编码 SP 论文不在“离格稀疏支撑漏检”体制里**：Kanazawa TVT'26（`2501.15935v3`）虽然带了 5G LDPC，但明确停在**整数 DD 格点**（并在结论把分数 Doppler 列为未解问题），采用门限检测加固定轮数切换；另一篇带编码的 SP-OTFS 论文 Yujie Liu et al., IEEE TCOM 2023 (`10.1109/tcomm.2023.3323710`, `[仅读摘要]`) 用的是 BEM 线性基展开而非稀疏离散路径支撑。两者都不存在“漏掉 1–2 条弱时延路径需要重开离散支撑”的问题。
3. **方法路径依赖**：一进入分数 Doppler 稀疏估计，社区沿袭 Wei TWC'22 (`2101.05629`) 的 SBL/VBI 路线（Y. Luo'26、Yuan–Guo'26、Mehrotra'23）或导频专用的 NOMP/SAGE 路线（Ma'26、Li'26、Wang'26），天然每帧做全局重构。至于是不是有人私下试过“校验触发 + 局部替换”但觉得没必要而没发表——**不知道（检索未见任何记录）**。

---

## 五、各层总判定、最危险的三篇先行工作、以及还站得住的主张

### 分项结论

| 层级 | 判定 | 一句话理由 |
|---|---|---|
| **L1 整体** | **已知部件的新组合**（配新瓶颈诊断） | 每个算法积木在邻近领域均已成熟；价值在于针对编码低导频 SP-AFDM 的漏径瓶颈把它们闭环整合，拿到实打实的 FER 与 12–16× 摊销加速优势 |
| L1(a) 校验触发重估 | **已知技巧用在新场景** | Turbo/LDPC 校验早停与失败重估是经典工程做法（Huang'10, Adachi'07, Kanazawa'26），只是未见在 SP-AFDM 接入异构支撑重获取 |
| L1(b) 定基数替换+细化+Schur | **已被做过** | 优化器内核实质是定基数受限预算的 SBR（Soussen'11）+ 局部 swap（Hazimeh–Mazumder'20）+ NOMP/RELAX 连续细化（Mamandipoor'16, Li–Stoica'96） |
| L1(c) 判决重建字典 | **已被做过** | UWA-OFDM（Huang'10）、SP-OTFS（Wei'22, Mehrotra'23）、SP-AFDM（Y. Luo'26, Yuan–Guo'26）均已做过 |
| L1(d) 前端漏 1–2 径→局部替换够用 | **新**（实证系统诊断） | 未见在低导频 SP-AFDM 下用约束 MCRB + Genie 支撑审计定量确立该瓶颈并据此用 2 步局部替换取代全帧 SBL |
| **L2 不确定度规则** | **机制已知、跨估计器镜像为新，但工程靶子薄弱** | 期望 Gram 已知；`uI` 拆径内核是 Zou–Hastie (2005) 的直接推论且文献中无人用 `uI`；`Γ = 0` 在 P1 与 MIXED8 上 FER 均与 `CODELAY` 打平；仅“同一不塌缩项在离散交换 vs 过完备 SBL 中作用反转 + 自洽性边界”为新发现 |
| **L3 AFDM 精确块与 chirp 压制** | **新**（简洁结构命题） | 基于 Bemani'23 的 DAFT/chirp 结构的直接但未见推导的二阶矩恒等式；数学干净，但因 `Γ = 0` 打平而失去工程不可替代性 |

### 最危险的三篇先行工作

1. **C. Soussen, J. Idier, D. Brie, and J. Duan**, *"From Bernoulli–Gaussian Deconvolution to Sparse Signal Restoration,"* **IEEE TSP**, vol. 59, no. 10, pp. 4572–4584, Oct. 2011 (`10.1109/tsp.2011.2160633`, HAL `hal-00443842`, `[已读原文]`)（配 **Mamandipoor et al., IEEE TSP 2016**, `arXiv:1509.01942`）。
   - **杀伤点**：直接打穿 L1(b) 和 Prop 3 的算法新颖性——相关字典上的单元素替换、Cholesky/块逆 `O(k²)` 快速打分和 0.25-bin 网格加连续细化全都是已知标准件。
2. **Z. Yuan, Q. Guo, M. Jin, Z. Liu, and P. Xiao**, *"Message-Passing-Based Bayesian Joint Channel Estimation and Data Detection for Pilot-Guard-Free AFDM,"* **`arXiv:2611.14877v1` (11 Nov 2026)** `[已读原文]`（配 **Y. Luo et al., IEEE TCOM 2026**, `arXiv:2607.18881`）。
   - **杀伤点**：**9 天前刚挂网的最新正面对手**。它做的是无保护带 AFDM + 分数 Doppler + 联合贝叶斯估计与检测，并且显式把符号后验方差 `ν_{x_n}` 以 `|x̂_n|² + ν_{x_n}` 送进路径增益更新（Eqs. (88)–(92)）。它直接挤压了“首次在无保护带/高谱效分数 Doppler AFDM 数据辅助估计中引入软符号不确定度”的话术空间（虽然它是 uncoded + 交织导频 + 逐路径 AMP 消息传递，不同于你们的 LDPC 编码 + 叠加 ZC 导频 + 触发式局部支撑交换）。
3. **H. Zou and T. Hastie**, *"Regularization and Variable Selection Via the Elastic Net,"* **JRSS-B**, 2005 (`10.1111/j.1467-9868.2005.00503.x`)（配 **A. Fannjiang and W. Liao, SIIMS 2012**, `arXiv:1106.5177`, `[已读原文]`）。
   - **杀伤点**：配合 `res-20261120-01/03` 和“无人用 `uI`”的文献事实，审稿人可以一刀切掉 L2 的算法卖点：“对角 `ℓ2` 奖励重合原子均分是 Zou–Hastie 常识；相干网格双峰抑制 Fannjiang–Liao 早做过；文献里没人用 `uI`，而你们不加 `Γ` 就和 `CODELAY` 在 FER 上打平。”

### 在这三篇压顶之下，真正站得住的主张还剩什么？

剥掉一切站不住的包装后，**真正站得住、经得起苛刻 TCOM 审稿人逐条核查的主张只剩三条**，而且它们必须诚实重排主次：

1. **主系统主张（最硬、但本质是诊断驱动的架构贡献，不是新算法）**：在 LDPC 编码低导频 SP-AFDM（`ρ = 0.25–0.30`）下，约束 MCRB 与 Genie 支撑审计表明瓶颈在于导频初估漏检 1–2 条弱时延路径（占 NMSE 差距 73%–81%），而不是已获支撑的参数精调；据此，用 LDPC 零校验子门控仅在失败帧上触发固定预算局部支撑交换（哪怕用最简的 `Γ = 0` 软均值打分），即可把最优工作导频比压到 `ρ = 0.25–0.30`（较强前端 `F0` 最佳对最佳领先 **1.14 dB**），在相同帧上相对 Luo 式数据辅助离格 SBL 提前 **1.3–5.3 dB** 且整帧平均单核快 **11.9×–16.0×**（含约 1% 触发率摊销）。**前提缺口需补齐**：当前 1.14 dB 导频扫描还没挂上 `Γ = 0` 对照臂，投稿前若按此定位必须说清或补测 `Γ = 0` 在 `ρ` 扫描上是否复现全部 1.14 dB。
2. **副机理主张（真正非平凡的理论洞见，但定位为跨估计器建模警示而非解码增益来源）**：在分数 Doppler 数据辅助估计中，揭示从正交整数格点（`Wang TCOM'22`）自然迁移过来的对角软不确定度 `uI` 具有**估计器依赖的双面性**——它多出的不塌缩差模项 `u(I - D)` 在固定基数离散交换中把拆分不变半范数扭曲为坐标惩罚、诱发 89% 幻影并腰斩救回率（规则是必须用拆分不变/自洽模型：`Γ = 0`、硬判决或 `CODELAY`，三者在 FER 上等效），但在过完备密网格 EM-SBL 中恰恰充当亚分辨零空间正则而显著降低 FER（前瞻镜像干预支持，`res-20261119-03`）。
3. **附带结构命题（L3，作理论底座而非卖点）**：推导 AFDM 任意异方差符号不确定度的精确投影 Gram（Prop 1），证明同延块精确坍缩为单标量 `u·D_N(Δν)`、跨时延残差在 `|d| ≥ 2` 时被 chirp 移位压制，从而解释为何同延几何独立于译码器状态（`E·D + u·D = N·D`）以及为何 `CODELAY` 能在零方差 FFT 下提供自洽类里严格匹配后验二阶矩的闭式实现（并在近距真双径上保留小幅表征优势）。

---

### 检索词记录（对“未找到先例”项可复现审计）

- OpenAlex (`title_and_abstract.search` / `search`):
  - `"channel re-estimation" AND (CRC OR syndrome OR LDPC OR failure)`
  - `syndrome AND "channel estimation" AND LDPC`
  - `CRC AND "channel estimation" AND (turbo OR iterative OR re-estimation)`
  - `CRC AND ("channel estimation" OR "equalization") AND (trigger OR fail OR failure OR conditional OR selective OR adaptive)`
  - `("decoding failure" OR "failed frame" OR "unsuccessful decoding") AND "channel estimation"`
  - `LDPC AND ("early termination" OR "early stopping") AND ("channel estimation" OR "turbo equalization")`
  - `"single best replacement" OR ("support" AND "swap" AND "channel estimation")`
  - `("errors-in-variables" OR "dictionary uncertainty" OR "perturbed dictionary" OR "measurement matrix uncertainty") AND ("sparse Bayesian learning" OR "sparse recovery")`
  - `"diagonal loading" AND "sparse Bayesian learning"`
  - `("sparse Bayesian learning" OR "automatic relevance determination") AND ("coherent" OR "collinear" OR "correlated columns" OR "duplicate")`
  - `("L0" OR "cardinality" OR "best subset") AND ("ridge" OR "L2") AND ("collinear" OR "correlated" OR "duplicate" OR "split")`
  - `"superimposed pilot" AND OTFS`; `"superimposed pilot" AND AFDM`; `AFDM AND ("data-aided" OR "decision-directed" OR "superimposed" OR "iterative") AND "channel estimation"`
- arXiv API:
  - `(all:CRC OR all:syndrome OR all:"parity check") AND all:"channel estimation" AND (all:LDPC OR all:turbo OR all:iterative)`
  - `(all:"re-estimation" OR all:"reestimation" OR all:"re-estimate") AND all:"channel" AND (all:LDPC OR all:CRC OR all:turbo OR all:sparse)`
  - `all:AFDM AND all:"channel estimation"`
  - `all:OTFS AND (all:"data-aided" OR all:"superimposed" OR all:"decision-directed") AND all:"channel estimation"`
  - `all:"sparse Bayesian learning" AND (all:"correlated" OR all:"coherent" OR all:"overcomplete" OR all:"uncertain" OR all:"perturbation") AND (all:off-grid OR all:DOA OR all:Doppler OR all:dictionary)`
  - `(all:"spurious" OR all:"ghost" OR all:"split") AND (all:OMP OR all:SBL OR all:CLEAN OR all:NOMP) AND (all:radar OR all:sonar OR all:GNSS OR all:multipath OR all:Doppler)`

---

# 第二步

读取五份既往定位材料（`novelty-positioning-20261118.md`、`literature-uncertainty-model-check-20261118.md`、`recent-preprints-verification-20261118.md`、`10-17-codelay-novelty/research/novelty-verdict.md`、`lit-diag-soft-variance-20261120.md`）后，对照第一步的独立查新结果，逐项指出漏掉的先行工作、结论分歧与可主张清单的收窄裁决。

---

## 一、既有定位材料漏掉的关键先行工作

五份旧材料把绝大部分检索预算都花在了 L2（协方差与 EIV）上，导致**两条致命盲区**：一是漏掉了刚刚挂网的 2026 下半年离格 AFDM 新论文群，二是几乎完全没对 L1（校验触发 + 定基数替换 + 编码稀疏重估）做过跨领域查新。

1. **漏掉最新、最贴身的 2026 AFDM 正面对手（4 篇全文已核 + 1 篇待查）**
   - **Z. Yuan, Q. Guo, M. Jin, Z. Liu, and P. Xiao**, *"Message-Passing-Based Bayesian Joint Channel Estimation and Data Detection for Pilot-Guard-Free AFDM,"* `arXiv:2611.14877v1` (11 Nov 2026) `[已读原文]`。
     - **依据与影响**：挂网仅 9 天，五份旧材料（含 11-18 预印本核对与 11-20 查表）全部漏掉。它做无保护带（交织导频）AFDM + 分数 Doppler + 联合贝叶斯消息传递，且在 Eqs. (88)–(92) 显式用逐符号后验方差 `ν_{x_n}` 按 `|x̂_n|² + ν_{x_n}` 更新路径增益 `h_k`。虽然它是无编码、交织导频、逐路径 AMP 解耦（无联合 Gram 块，无支撑交换），但它直接堵死了“首次在无保护带分数 Doppler AFDM 数据辅助估计中引入软符号不确定度”的笼统宣称。
   - **Y. Ma, Z. Wang, Y. Ni et al.** (`arXiv:2607.05082v1`, Jul 2026，脉冲成形分数时延/Doppler AFDM + NOMP)、**S. Li, C. Pan, H. Ren et al.** (`arXiv:2608.11998v1`, Aug 2026，AFDM-ISAC 分数时延-Doppler 耦合 + CC-NOMP)、**R. Wang, C. Pan, H. Ren et al.** (`arXiv:2610.09970v1`, Oct 2026，分数时延/Doppler AFDM + 模型阶数自适应改进 SAGE，做残差加径与冗余删径) `[三篇均已读原文]`。
     - **依据与影响**：`recent-preprints-verification-20261118.md` 把 2026 离格 AFDM 描绘成清一色嵌入式导频 SBL，漏掉了 2026 年已经成型的 AFDM 离格 NOMP / SAGE 路线。相关工作必须正面回应这组连续参数估计对手。
   - **未核实预警**：**Y. Lan and Y. Liu**, *"Uncertainty-Aware Soft Feedback for Joint Channel Estimation and Detection for AFDM in 6G Communications,"* SSRN 2026, DOI `10.2139/ssrn.7661835`（OpenAlex 已收录，摘要与 PDF 不可获取；题目高度贴近，投稿前必须设法查清）。

2. **漏掉 L1 接收机架构的跨领域先例（旧材料把 L1 当透明外壳，几乎未查）**
   - **L1(a)+(c) 编码稀疏信道重估 + 校验判定先例**：**J. Huang, J. Huang, C. R. Berger, S. Zhou, and P. Willett**, EURASIP JASP 2010 (`10.1155/2010/460379`, Sec. 3.1–3.4, Eqs. (12)–(22) `[已读原文]`，水声 MIMO-OFDM 中用 LDPC 软/硬输出重建字典做 BP/OMP 重估，并在 Sec. 3.3 显式用全校验满足判定数据流成功恢复)；**T. Kang and R. A. Iltis**, IEEE JSAC 2008 (`10.1109/jsac.2008.081205` `[仅读摘要]`)；**B. Shi, Y. Wu, P. Yuan et al.**, IEEE WCL 2023 (`arXiv:2311.07091`, Algorithms 1–2 `[已读原文]`，用 LDPC 校验满足概率做坐标上升修信道)；**C.-H. Chen et al.** (`arXiv:2504.11241v2`, Oct 2025 `[已读原文]`) 与 **C. Wiame, K. R. Duffy, and M. Médard**, IEEE ICC 2025 (`arXiv:2506.14756v1`, Sec. III-A `[已读原文]`，在初始信道邻域重搜并用 ORBGRAND/CRC 选优)；以及早期 CRC 辅助迭代均衡 **K. Adachi & M. Nakagawa** (IEICE 2007 `10.1093/ietcom/e90-b.6.1433`) 与 **Z. Liu et al.** (2007 `10.1007/s11767-005-0178-7`)。
   - **L1(b) 局部交换优化器与块逆更新先例**：`novelty-positioning-20261118.md` 仅在已知表里顺带提了一行 Soussen'11 与 Mamandipoor'16（还标“待 citation audit”），未核实 **Soussen'11 (`10.1109/tsp.2011.2160633`, Sec. IV-A Eq. (8) & App. C `[已读原文]`) 已经给出 Cholesky/块逆 `O(k²)` 精确单步替换打分**（直接覆盖 Prop 3 的代数套路）；并且完全漏掉了 **H. Hazimeh & R. Mazumder**, Operations Research 2020 (`arXiv:1803.01454`, Sec. 4 `CD-PSI(k)` `[已读原文]`，`L0+L2` 局部 1-swap/k-swap)、**J. Zhu et al.**, PNAS 2020 (`10.1073/pnas.2014241117`, ABESS splicing 固定基数交换)、**J. Li & P. Stoica**, IEEE TSP 1996 (RELAX)、**B. H. Fleury et al.**, IEEE JSAC 1999 (SAGE)、**D. Shutin & B. H. Fleury**, IEEE TSP 2011 (`10.1109/tsp.2011.2140106` `[已读原文]`，VB-SAGE)、以及 **Z. Gui et al.**, IEEE TVT 2024 (`10.1109/tvt.2024.3421934`，MIMO-OTFS 3D-ESP Subspace Pursuit)。

3. **补上了 `lit-diag-soft-variance-20261120.md` 未能读到的最关键经典文献，并补充多篇 SP-OTFS / EIV-SBL 文献**
   - **K. Fang, L. Rugini, and G. Leus**, *"Block Transmissions over Doubly Selective Channels: Iterative Channel Estimation and Turbo Equalization,"* EURASIP JASP 2010 (`10.1155/2010/974652` `[已读原文]`)：`lit-diag-soft-variance-20261120.md`（lines 55, 71）因主机拦截未能读取，将其标记为“最可能的 Doppler 原子经典先例”。本轮读取全文（Sec. 4.1, Eqs. (22)–(25)）确认：它将未知数据项 `D_o (I_{Q+1} ⊗ diag(s - m) F_L) h` 的协方差 `R_{d_f^o}` 放在**观测空间 LMMSE（边缘化了 `R_h`）**，属于 `D-obs` 而非坐标空间 `uI`（`D-coord`），且无稀疏支撑选择。这一最大未读隐患现已正式排除。
   - 此外，旧材料漏引了 **Y. Liu, Y. L. Guan, and D. González G.**, IEEE TCOM 2023 (`10.1109/tcomm.2023.3323710`, 编码 Turbo BEM SP-OTFS 导频功率优化)、**M. A. Sheikh et al.**, IEEE TCOM 2024 (`10.1109/tcomm.2024.3446575`, 多帧耦合 SBL SP-OTFS)、**W. Yuan et al.**, IEEE WCL 2021 (`10.1109/lwc.2021.3088836`, 数据辅助 SP-OTFS)、**Y. Lei et al.** (`arXiv:2601.22523`, 2026 分数 Doppler SP-OTFS 端到端学习) 与 **S. Wang, Y. Li, and J. Wang**, WCSP 2013 (`10.1109/wcsp.2013.6677226`, 测量矩阵不确定度 MU-SBL)。

---

## 二、我与既有定位材料结论不同的地方

1. **直接推翻 `10-17 novelty-verdict.md`（C3）关于 Chen–Caramanis (`1206.0823`) 与“支撑交换需要精确协方差”的判断**
   - **旧结论**：`10-17 novelty-verdict.md` 第 31 行认为你们和 Chen–Caramanis (`1206.0823`，误差独立时无协方差 OMP 仍能恢复支撑) 是“反方向互补”——断言“误差在近共线列之间相干时，支撑决策确实需要协方差（E-1 `S_Γ 1.18–1.22`）”。
   - **我的结论与依据**：**方向反了**。`res-20261120-01`（P1，1,952 触发，救回 `Z 653` vs `CD 659`，首步幻影均为 `36`）与 `res-20261120-03`（MIXED8，2,400 帧，`Z − CD = +0.54 pp [-0.03, +1.13]`，冻结判定 EQUIVALENT）证明，支撑交换根本不需要加上 `Γ` 来抑制幻影；真正需要的是**不要加上不塌缩的假对角项 `uI`**。在支撑选择这一步上，你们的结果不是反驳了 Chen–Caramanis，而是跟它**一致**：不加不确定度协方差（`Γ = 0`）照样恢复支撑，精确 `Γ` 只带来很小的增益尺度/近距双径表征微调。

2. **推翻 `literature-uncertainty-model-check-20261118.md`（第 30 行）与 `novelty-positioning-20261118.md`（第 0 节、D4）中“把增益挂钩到 `CODELAY` 胜过硬判决”的归因**
   - **旧结论**：两份 11-18 文档都建议正面写成：“首次在分数 Doppler SP 支撑获取中正确使用译码软不确定度……`CODELAY` 是最小的正确形式。相对文献实际采用的硬判决做法，提前 1.3–5.3 dB。”
   - **我的结论与依据**：**这份归因现在构成了严重的误导风险**。在 `res-20261120-01` 里，硬判决填字典（`H`）在你们自己的交换外壳里救回 **665/1,952**（甚至比 `CODELAY` 的 **659** 多 6 个，首步幻影仅 2.56%），在 `res-20261120-03` 里 `H − CD` 也只有 `+0.67 pp`。可见相对 `L-hard`（Luo 式硬判决 SBL）的 1.3–5.3 dB 优势，以及相对 `F0` 的 1.14 dB 导频扫描优势，**全部来自 L1 的触发式支撑交换架构，而不是来自 `CODELAY` 对软不确定度的建模**。同时，`arXiv:2611.14877`（Nov 2026）也在无保护带分数 Doppler AFDM 中显式使用了软符号方差。

3. **推翻 `recent-preprints-verification-20261118.md`（Sec. II 表与 Sec. III 英文引言草稿）对现有文献的残余归罪**
   - **旧结论**：该文档第 69 行与第 77 行（比 `novelty-positioning-20261118.md` v2 更旧一层）仍把 Zheng TVT'25、Kanazawa TVT'26、Y. Luo TCOM'26 放进“连续 Doppler 下把数据误差吸收成标量白噪声、从而遗漏同延块诱发幻影”的因果句中。
   - **我的结论与依据**：第一，Zheng (`2404.10232v1`) 与 Kanazawa (`2501.15935v3`) 都在整数格点上；第二，Y. Luo (`2607.18881`) 用硬判决 + 观测空间噪声 `β⁻¹ I_N`，你们自己的 `res-20261017-03` 已证实 `L-hard` 的每帧同延对数仅 5.70（与 `L-cov` 5.11、`L-genie` 5.50 齐平），根本没有幻影分裂病。这份英文引言草稿**不能直接入稿**，必须按自洽类逻辑重写。

4. **对 `lit-diag-soft-variance-20261120.md` 第 66 行“Strongest honest answer”的升级修正**
   - **旧结论**：第 66 行给出“文献无人用 `D-coord`，但它是把正交格点教科书做法搬到分数 Doppler 时最自然的升级，我们证明该升级失败并给出最小精确修法（`minimal exact fix`）”。
   - **我的结论与依据**：结合今天刚落地的 `res-20261120-01/03`，把 `CODELAY` 叫作 `minimal exact fix` 依然会被审稿人打回——因为**更简单的修法是根本别加 `Γ`（`Z`）**，它在 P1 与 MIXED8 上 FER 全都落在等效裕量内。诚实的说法必须退一步：**“最自然的对角软升级 `uI` 在离散支撑交换里反而是负优化（破坏拆分不变性），必须改回自洽类（删去 `Γ`、硬判决或精确 `CODELAY`）；而在过完备 EM-SBL 里同一个不塌缩项反而是有益正则。”**

5. **重评 L1 的风险敞口**：五份旧材料都没把 L1 当成需要独立查新的对象，导致一旦 L2 的工程不可替代性坍塌、L1 被迫承担论文主增益时，旧材料对 Soussen'11（SBR 块逆）、Hazimeh–Mazumder'20（`L0+L2` 1-swap）、Huang'10（LDPC 稀疏重估）及 2026 AFDM NOMP/SAGE 的防御完全空白。

---

## 三、旧材料认定的“可主张”清单重审：站得住 vs 必须收窄/撤回

### 仍然站得住的主张

1. **低导频 SP-AFDM 的漏径瓶颈诊断（约束 MCRB + Genie 支撑审计）**：73%–81% 的 NMSE 离界差距来自漏检弱时延路径，而非参数精调。查新未见先行工作，是整篇论文最稳的第一块砖。
2. **瓶颈驱动的轻架构系统增益（L1 整体组合）**：LDPC 零校验子门控 + 固定预算局部支撑交换 + 局部连续 Doppler 细化，把 SP-AFDM 可用导频比压到 `ρ = 0.25–0.30`，相对强前端 `F0` 最佳对最佳领先 1.14 dB（`res-20261119-06`），相对 Luo 式数据辅助 SBL 提前 1.3–5.3 dB 且整帧单核快 11.9×–16.0×（`res-20261118-03`，含约 1% 触发率摊销）。**前提条件**：必须诚实把增益归功于 L1 架构而非 `CODELAY`，并在导频扫描中补测或明示 `Γ = 0` 的表现。
3. **跨估计器的不塌缩对角项镜像反转（L2 真正新颖的理论发现）**：同一对角项 `uI = uD + u(I - D)` 中的不塌缩差模部分 `u(I - D)`，在固定基数离散支撑交换里诱发 89% 幻影并腰斩救回率，在过完备密网格 EM-SBL 里反而通过给亚分辨差模加下限大幅改善 FER（新帧前瞻干预支持，`res-20261119-03`）。查新未见先例，但必须诚实界定为**机理与跨估计器建模警示**，不宣称它驱动主接收机增益，也不把 SBL 侧包装成 ARD 收敛定理。
4. **AFDM 投影不确定度的异方差精确结构与跨调制比较（L3 / D1 / D6）**：Prop 1（任意异方差下同延块精确等于 `u·D_N(Δν)`、`|d| ≥ 2` 跨时延受 chirp 压制、`|d| = 1` 共振点、跨调制恒模基条件与秩注记）数学干净、查新未见推导。但定位必须降格为**解释“同延几何与数据无关（`E·D + u·D = N·D`）及自洽类等价性”的理论底座**，而非“不可替代的算法模块”。

### 必须收窄或撤回的旧“可主张”

1. **撤回 `10-17` C3 与 `11-18` D4 的“支撑交换需要精确协方差 / `CODELAY` 不可替代 / 唯一在 P1 与 MIXED8 两类全优”**：
   - 改为：**支撑交换需要的是“拆分不变（自洽）打分”**；`Γ = 0`（`Z`）、硬判决（`H`）与 `CODELAY` 同属自洽类，在 P1 与 MIXED8 上均无幻影且 FER 等效（`res-20261120-01/03`）。`CODELAY` 仅作为该类中零方差 FFT、严格匹配后验二阶矩的默认成员，在 MIXED8 0.35-bin 真双径上保留小幅表征优势（占位 `+1.54 pp`），不转化为超出裕量的 FER 优势。
   - 同时，**Table II（固定排除规则 `A2n`/`A2g` 对照）必须加入 `Z` 和 `H` 行**；否则只拿 `CODELAY` 对比标量补丁 `A2n`/`A2g` 会被审稿人当场识破漏掉了最简零成本对照 `Z`。
2. **撤回 `11-18` 文献核查与预印本核对中的“首次在分数 Doppler SP/无保护带 AFDM 中正确使用软不确定度”及“Y. Luo 漏掉同延块”**：
   - 改为：明确承认现有分数 Doppler 支撑搜索/SBL 文献无一使用 `uI`（Y. Luo 等用硬判决，本身无幻影；Yuan–Guo `2611.14877` 用逐符号二阶矩消息传递），本文剖析的是把正交整数格点精确对角模型（Wang TCOM'22）与 SBL 有益经验直接迁移到连续 Doppler 离散交换时的结构性失效。
3. **收窄 L1(b) 与 Prop 3 的算法定位**：
   - 明确声明固定基数单步替换与 Schur 补/Cholesky 增量更新属于 **SBR（Soussen TSP'11, Sec. IV-A）+ 局部 swap（Hazimeh–Mazumder OR'20）+ NOMP 局部连续细化（Mamandipoor TSP'16）** 的标准工程适配，不主张提出了新优化器；同时承认 L1(a) LDPC 校验子触发属于 turbo/编码接收机（Huang'10, Kanazawa'26）的零开销工程门控。
4. **明确划清“本文系统增益归谁、理论警示归谁”**：
   - 绝不能让读者（或审稿人）误以为 L2 准则贡献了 1.14 dB 或 1.3–5.3 dB。引言必须开宗明义分成两段清楚的贡献：**系统侧**是 MCRB 漏径诊断导出的校验触发局部支撑交换架构（拿到 1.14 dB 低导频增益与 12–16× 加速）；**理论/机理侧**是分数 Doppler 下软符号不确定度的 AFDM 精确投影结构与离散交换/过完备 SBL 镜像边界（防止做软信息升级时掉进 `uI` 陷阱，并解释为何两类估计器的最优处理恰好相反）。
