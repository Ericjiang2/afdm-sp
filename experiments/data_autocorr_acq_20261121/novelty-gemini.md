# 第一步

## 立场先说

先把话挑明：**从底层数学和信号处理机理来看，你们设想的“(a) 用未知数据二阶统计辨识双选信道”和“(b) 径对出现在差分时延 $\times$ 差分多普勒处并据此恢复稀疏多径”已经被至少五个学科反复做透了，甚至 2024 年已经有人在完全相同的 AFDM 波形上写过直接利用接收信号协方差矩阵交并项 $h_p h_q^*$ 做盲参数估计的论文（Ranasinghe et al., `arXiv:2407.05328v2`）。** 这两条在 TCOM 审稿人眼里绝对不能当成“新发现”或核心贡献去卖。

剥掉所有表面包装后，这套想法里**唯一还没在文献里找到原样撞车、但目前也只是“候选新意”的，是把 (a)–(d) 压在一起的系统综合**：用**单帧**（$T=1$）时域接收信号的延迟乘积 FFT $A_r(d, f) = \sum_n r_n r^*_{n-d} e^{-j2\pi f n/N}$ 作为低成本粗捕获器找回漏检弱径；把极低功率（如 $\rho \le 0.15$）的叠加导频降格为**全息/Turnpike 消歧参考**（专门解绝对时延/多普勒锚点、整体相位和前后镜像 $\ell_s \pm d$）；并据此在**编码 SP-AFDM** 里利用“数据二阶统计随 $\rho$ 下降几乎不掉、导频匹配滤波随 $\rho$ 下降陡崩”的**交叉点**，尝试击穿现有接收机 $\rho < 0.25$ 的自举悬崖。

但这里必须泼一盆冷水：你们现有的证据 `experiments/data_autocorr_acq_20261121/READOUT.md` 只走到了“如果上帝把真最强径当锚交给你，94.8% 的有效弱径能落进公共虚警预算前 8 个竞争峰内”的**可见性测试**。锚点自己靠极低导频找不找得准、$\ell_s \pm d$ 镜像候选翻倍后怎么消歧、与最强径同延（$\ell_w = \ell_s$）的弱径全漏怎么办、以及第 0 轮塞进这些候选后编码 FER 穿越点到底左移多少——这些端到端硬仗目前一行都没测。没看到 FER 真正跨过 $\rho=0.25$ 之前，连 (d) 都只能算待证猜想，不算立住的贡献。

> **独立性与证据口径披露**：按要求，在撰写并保存本“第一步”前，本会话**未打开** `experiments/data_autocorr_acq_20261121/astra-review.md`。关于本项目的实现仅核对了 `novelty-gemini-prompt.md`、`READOUT.md` 与 `calc.py`（第 43–81 行确定所测统计量为 $A_r(d,f) = \sum_{n=0}^{N-1} r_n r^*_{n-d} e^{-j 2\pi f n/N}$，取 $|A_r(d,f)|^2$ 在 $1/\text{PAD}$ 网格找局部峰）。下文每条文献均注明核验层级：`[已读原文]` / `[仅读摘要]` / `[核验 DOI，正文凭记忆未核实]` / `[凭记忆，未核实]`。

---

## 一、跨领域底层逻辑核查（(a)–(d) 逐项对表）

### 1. AFDM 与 MIMO-OFDM 双选信道的二阶统计盲/半盲估计（最直接的近身威胁）

1. **K. R. R. Ranasinghe, K. Ando, H. S. Rou, G. T. F. de Abreu, and A. Bathelt**, *"Blind Bistatic Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels,"* `arXiv:2407.05328v2` (2024) `[已读原文]`（Sec. II-B Eqs. (6)–(12), Sec. III-B Eqs. (19)–(25), Sec. III-C Eqs. (28)–(33), Sec. IV Fig. 2；其后续期刊延伸 *IEEE TWC*, Feb. 2025, `DOI:10.1109/TWC.2024.3510935` `[仅读摘要]` 为联合信道数据及雷达估计）。
   - **底层逻辑重合与不重合**：**重合得极其刺眼**。该文直接在 **AFDM 双色散稀疏信道**（整数时延 + 分数多普勒，Sec. II-A Eqs. (1)–(2)）上，利用未知数据协方差接近白化（$\mathbb{E}[X X^H] \approx T \sigma_X^2 \mathbf{I}_N$）这一同一性质，构造去噪后的样本协方差 $\tilde{\mathbf{R}}_Y = \frac{1}{T}\mathbf{Y}\mathbf{Y}^H - \sigma_W^2\mathbf{I}_N = \sum_{p,q} h_p h_q^* \boldsymbol{\Gamma}_p \boldsymbol{\Gamma}_q^H$（Eqs. (21)–(23)）。文中明确指出当 $p=q$ 时 $\boldsymbol{\Gamma}_p \boldsymbol{\Gamma}_p^H = \mathbf{I}_N$ 不带径信息，所有有效参数信息全部落在交叉项 $p \neq q$ 上，权重恰好是 $h_p h_q^*$（$H_G(p,q)$），并将行和向量 $\bar{\mathbf{r}}_Y = \tilde{\mathbf{R}}_Y \mathbf{1}_N$ 写成离散时延–多普勒对字典上的稀疏重构（Eqs. (24)–(33)），且仿真中恰恰包含一个 LoS 强参考径与一个运动目标径（Sec. IV）。**不重合**在于：① 它是**跨 $T$ 帧**的多帧样本协方差（Fig. 2 中主要跑在 $T=100, 1000, 10000$，$T=1$ 时 RMSE 极差），假设延迟–多普勒在 $T$ 帧内平稳，且用 $N \times (K_\tau^2 D_\nu^2)$ 的 LASSO + 分数规划求解，规模仅测到 $N=64, \ell_{\max}=4, P=1$；你们是**单帧（$T=1$）时域延迟乘积的 1D FFT**，复杂度只有 $O(N L_{\max}\log N)$（在 $N=1024, L_{\max}=102$ 下把“解 $K^2$ 维对字典优化”降成直接二维峰值检测作粗候选）；② 该文做的是无编码盲感知，没有叠加导频锚定消歧，也没有考察低 $\rho$ 下的自举交叉点。
   - **重合程度**：**同一机制、相同场景（对 AFDM 下基于数据二阶协方差恢复径对 $h_p h_q^*$ 构成最直接的同波形邻近先例；对单帧粗捕获与低导频编码通信属于不同机制实现与不同任务）**。
   - **审稿人攻击与回应**：审稿人一定会把 `2407.05328` 甩在桌上：“AFDM 用未知数据样本协方差的跨径交叉项 $h_p h_q^*$ 提取双色散多径参数，2024 年已经发表过。”回应绝不能硬说“它做雷达我做通信”，必须正面承认多帧样本协方差做 AFDM 盲估计已被做过，把区别精准切在三刀上：① `2407.05328` 依赖 $T \gg 1$ 帧静态平均、直接解 $K_\tau^2 D_\nu^2$ 维秩-1 正定稀疏逆问题，单帧 $T=1$ 退化且算不动大时延扩展；② 我们利用时域延迟乘积的单帧遍历性 + 1D FFT 只做**第 0 轮粗候选提名**，把“求精和解歧”留给叠加导频与 LDPC 迭代环；③ 我们给的是低 $\rho$ 叠加导频交叉点而非纯盲感知。

2. **M. R. Mehrabani, B. Abolhassani, and F. Haddadi**, *"Semi-Blind Channel Estimation and Pilot Allocation for Doubly-Selective Massive MIMO-OFDM Systems,"* *IEEE Access*, 2024, `DOI:10.1109/access.2024.3441375` `[仅读摘要；IEEE Xplore PDF 返回 HTTP 418 未能直接下载原文，投稿前必须人工下载阅读公式]`。
   - **核验确认**：经 Crossref 与 OpenAlex 核验，该论文真实存在（Gold OA）。摘要明确写明：在 CE-BEM 稀疏双选信道模型下，先用遗传算法按互相关最小优化导频位置，*"Secondly, taking the advantage of the complex exponential (CE)-BEM, the correlation of the received signal is used to estimate the channel's most significant lags (MSLs). Using optimized pilot locations and MSLs, we propose a novel algorithm, called semi-blind block orthogonal matching pursuit (SB-BOMP)"*。
   - **底层逻辑重合与不重合**：**重合点**非常关键——它在**稀疏双选信道**上显式践行了“**用未知接收信号的相关统计找稀疏主支撑（MSLs），从而减少导频需求**”的半盲分工逻辑。**不重合点**（基于摘要，待读原文核实）：它针对 Massive MIMO-OFDM 与 CE-BEM 块稀疏系数，用的是分立正交导频 + 空时块相关筛选**时延支撑位置（MSLs）**；而你们是单天线（SISO）AFDM 叠加导频，利用单帧时间延迟乘积的**频谱（差分多普勒轴 $\nu_i - \nu_j$）**同时给出差分时延与差分多普勒，再用导频解锚点与镜像歧义。
   - **重合程度**：**同一机制、邻近场景（对“用接收信号二阶相关提取稀疏主抽头以减导频”这一半盲思路 (a)/(c) 构成直接邻近风险，具体与单帧差分多普勒 FFT 的差异须读全文后才敢写死）**。
   - **审稿人攻击与回应**：审稿人会问：“半盲双选信道里用接收信号相关先找稀疏时延支撑、再配少数导频做 OMP 重构，Mehrabani 2024 已经用过。”回应须在核读全文后明确指出它如何利用 Massive MIMO 空域/块相关找绝对时延延迟（MSLs），以及与单天线单帧延迟–多普勒差分谱、叠加导频消歧的区别。

3. **顺带排雷**：**K. Zhang, W. Yuan, and M. S. Greco**, *"Zak-OTFS ISAC with Bistatic Sensing via Semi-Blind Atomic Norm Denoising Scheme,"* `arXiv:2601.03639v2` (2026) `[已读原文（摘要与 Sec. I）]`。虽叫 "semi-blind"，实际是将未知离散星座约束以负二次惩罚写进原子范数联合去噪（同时求信道和符号），**不用接收信号二阶自相关**，属**只是表面相似**。

---

### 2. 经典盲/半盲时变信道辨识与叠加训练（(a)/(b)/(c) 的通信学母体）

1. **周期自相关与循环平稳时变信道辨识**：**L. Tong, G. Xu, and T. Kailath**, *IEEE Trans. Inf. Theory*, 1994, `DOI:10.1109/18.312157` `[核验 DOI，正文凭记忆未核实]`；**M. K. Tsatsanis and G. B. Giannakis**, *Proc. CISS*, 1995（coding-induced cyclostationarity）、*Int. J. Adapt. Control Signal Process.*, 1996 及 *IEEE Trans. Signal Process.*, vol. 45, no. 12, Dec. 1997, `DOI:10.1109/78.650270` (*"Subspace methods for blind estimation of time-varying FIR channels"*) `[核验 DOI，正文凭记忆未核实]`；以及综述与统一框架 **G. B. Giannakis and C. Tepedelenlioğlu**, *"Basis expansion models and diversity techniques for blind identification and equalization of time-varying channels,"* *Proc. IEEE*, vol. 86, no. 10, Oct. 1998, `DOI:10.1109/5.720248` `[核验 DOI，正文凭记忆未核实]`。
   - **底层逻辑重合与不重合**：Tong–Xu–Kailath (1994) 开创用输出二阶统计量替代高阶累计量盲辨识 FIR 信道；而 **Tsatsanis–Giannakis (1995–1997) 与 Giannakis–Tepedelenlioğlu (1998) 直接就是你们 `calc.py` 公式的通信学鼻祖**。一旦把离散时变信道写成多普勒复指数展开 $h(n; \ell) = \sum_q h_q(\ell) e^{j\omega_q n}$，白数据输入下输出的时变自相关 $c_{rr}(n; d) = \mathbb{E}[r_n r^*_{n-d}]$ 对 $n$ 展开后，其循环频率（cyclic frequencies）精确落在所有成对频偏之差 $\omega_q - \omega_{q'}$ 上，循环相关系数正好是跨时延抽头乘积 $h_q(\ell) h_{q'}^*(\ell-d)$！**不重合**在于：该脉络预设已知固定基展开频率网格 $\omega_q$、靠过采样/多天线或发射端预编码引入的多帧循环平稳子空间分解（SVD）去解稠密 FIR 系数，不利用单帧（$T=1$）稀疏多径下少数孤立径的直接 FFT 峰值捕获，也不存在叠加导频做单锚点消歧和编码低 $\rho$ 切换。
   - **重合程度**：**同一机制、相同或邻近场景（对 (a) 和 (b) 的物理–数学机理构成根本性抢先，必须正面引述致敬）**。
   - **审稿人攻击与回应**：任何资深的信号处理审稿人看到 $\sum_n r_n r^*_{n-d} e^{-j2\pi f n/N}$，第一反应就是“这不就是 Giannakis 1998 年的时变信道循环自相关吗，其循环频率本来就是成对多普勒差 $\nu_i - \nu_j$”。回应绝不能宣称“发现延迟乘积带有 $(\Delta\ell, \Delta\nu)$ 径对谱”，必须坦白说清：该循环谱结构源自 Tsatsanis–Giannakis (1997/1998)；本文的工作是在**单帧、非平稳、SISO 稀疏连续多普勒**体制下，把它当作有限样本的候选路径检出器（而非全盲渐近子空间求解器），并用极低功率叠加导频消解其固有平移与镜像歧义。

2. **Tugnait 叠加训练主线 vs. 半盲二阶统计消歧**：
   - **J. K. Tugnait and W. Luo**, *IEEE Commun. Lett.*, 2003 `[凭记忆，未核实]`；**X. Meng and J. K. Tugnait**, *"Semi-blind channel estimation and detection using superimposed training,"* *Proc. IEEE ICASSP*, 2004, `DOI:10.1109/icassp.2004.1326852` `[核验 DOI，正文凭记忆未核实]`；**J. K. Tugnait, X. Meng, and S. He**, *"Doubly Selective Channel Estimation Using Superimposed Training and Exponential Bases Models,"* *EURASIP J. Adv. Signal Process.*, 2006, `DOI:10.1155/asp/2006/85303` `[已读原文]`（摘要与正文检索确认：Step 1 用周期叠加训练序列的**一阶统计均值**估计 CE-BEM 信道，Step 2 用 Viterbi 检测与确定性最大似然 DML 交替迭代；全文未用未知数据的二阶自相关找径）；以及数据依赖型 **M. Ghogho, D. McLernon, E. Alameda-Hernandez, and A. Swami**, *IEEE SPL*, 2005, `DOI:10.1109/lsp.2004.842283` `[核验 DOI，正文凭记忆未核实]`。
     - **重合程度**：对 (c) 是**表面相似/不同机制**（Tugnait 系列在第 0 轮把未知数据看作零均值噪声、靠一阶周期均值提导频，而不是用数据二阶统计找径），但它确立了“叠加导频先粗估 + 判决辅助（semi-blind）迭代精修”的整体范式先例。
   - **半盲二阶统计 + 导频专职消歧**：**A. K. Jagannatham and B. D. Rao** 的白化–旋转（whitening-rotation）半盲 MIMO 估计系列 `[仅通过检索摘要核实，未读原文]`（其核心逻辑是：仅凭未知数据的二阶协方差就能把信道矩阵辨识到仅剩一个未知酉旋转矩阵 $\mathbf{Q}$，因此导频不再负责估计全部信道参数，只专门用来解那几个旋转歧义参数）。
     - **重合程度**：**同一机制（数据 SOS 承担参数主力，少量导频专职消除对称性歧义）、不同场景（空间平坦 MIMO 酉矩阵歧义 vs. 单帧双选稀疏路径的平移/全局相位/共轭镜像歧义）**。

---

### 3. 射电天文闪烁弧与二次谱（最惊人的完全同构先例）

- **J. M. Cordes, B. J. Rickett, D. R. Stinebring, and W. A. Coles**, *"Theory of Parabolic Arcs in Interstellar Scintillation Spectra,"* *Astrophys. J.*, vol. 637, pp. 346–365, 2006, `arXiv:astro-ph/0407072`, `DOI:10.1086/498332` `[已读原文]`（重点核验 Sec. 3.1、Eq. (8)、Sec. 3.4.3 Eqs. (14)–(15)、Sec. 5）；配套 **M. A. Walker, D. B. Melrose, D. R. Stinebring, and C. M. Zhang**, *MNRAS*, 2004, `arXiv:astro-ph/0403587` `[已读摘要与引言]`，及早期观测 **D. R. Stinebring et al.**, *ApJ*, 2001 `[凭记忆，未核实]`。
  - **底层逻辑重合与不重合**：虽然跨了学科，但数学物理结构是**100% 镜像重合**。脉冲星穿过星际介质形成多径散射屏，天文台只看得到未知随机发射信号经过信道后的动态谱强度 $|E(\nu, t)|^2$，对其做二维傅里叶变换得到**二次谱（secondary spectrum）** $S_2(f_\nu, f_t)$。Cordes et al. Sec. 3.1 白纸黑字写明：**二次谱中的 $(f_\nu, f_t)$ 正是成对散射径之间的差分时延（differential delay $\propto \theta_2^2 - \theta_1^2$）与差分多普勒（beat frequency due to different Doppler shifts $\propto V_\perp \cdot (\theta_2 - \theta_1)$），即“differential delay-Doppler spectrum, similar to that measured in radar applications”**；Eq. (8) 写出每对路径 $(1,2)$ 的干涉核且具有中心反演对称性 $(p, q) \to (-p, -q)$。更令人震惊的是 **Sec. 3.4.3 Eqs. (14)–(15) 与 Sec. 5**（以及文档第 630 行讨论）：当星际图像里存在一个占主导的未散射点源核心 $B(\theta) = a_1 \delta(\theta - \theta_p) + a_2 g(\theta)$ 时，弱散射径之间的互干涉项可以忽略，二次谱就等价于一张**全息图（hologram），那个最强直达核心天然充当全息参考光束（reference beam），把所有微弱散射径的相对时延与相对多普勒从二次自相关里直接映照出来**！
  - **不重合**：天文上是无合作导频、长积分时间下的宽带被动观测，最后还是停在二次谱本身关于原点中心对称的共轭镜像歧义上（文中也提到单看二次谱有对称反演与相位问题），没有叠加人工参考导频来破镜像，也不做信道编码译码。
  - **重合程度**：**同一机制、不同场景（对 (b) 以及“靠最强径做锚暴露弱径的全息机制”构成概念与数学上的完全先例）**。
  - **审稿人攻击与回应**：一旦把 Cordes 摆出来，审稿人会立刻说“‘靠最强径当锚从差分时延–差分多普勒二次谱里拎出全部弱径’本质就是射电天文早已分析透的二次谱全息干涉机制，甚至对称镜像歧义 $(p,q)\leftrightarrow(-p,-q)$ 都写在了原文里”。回应方式应该很坦诚：主动引用 Cordes (2006) 借其物理直觉与数学同构性，同时点出无线接收机必须把“无参考的全息对称歧义”解成确定时延符号与绝对相位才能相干均衡译码——这正是极低功率叠加导频接手的地方。

---

### 4. 稀疏相位恢复、Turnpike 问题与全息参考消歧（(b)/(c) 唯一性与歧义的精确数学定性）

- **J. Ranieri, A. Chebira, Y. M. Lu, and M. Vetterli**, *"Phase Retrieval for Sparse Signals: Uniqueness Conditions,"* `arXiv:1308.3058v2` (2013) `[已读原文]`（Abstract, Sec. II–IV, Theorems 1–4）；连续超分辨延伸 **G. Baechler, M. Kreković, J. Ranieri, A. Chebira, and M. Vetterli**, *IEEE TSP*, 2019, `DOI:10.1109/tsp.2019.2931169` `[核验 DOI，正文未读]`；综述 **K. Jaganathan, Y. C. Eldar, and B. Hassibi**, `arXiv:1510.07713` `[已读引言]` 及 *IEEE TSP*, 2017, `DOI:10.1109/tsp.2017.2656844` `[核验 DOI，正文未读]`。
  - **底层逻辑重合**：`1308.3058v2` 的摘要直接把 **blind channel estimation** 列为应用场景之一！它在数学上证明：从一组稀疏脉冲 $\sum_{m=1}^N c_m \delta(x - x_m)$ 的自相关函数（即全部成对差值 $x_i - x_j$ 与乘积 $c_i c_j^*$）恢复原信号，等价于组合数学里的 **turnpike problem**。只要自相关没有碰撞（collision-free），一维及多维稀疏信号（Theorem 4，包含二维连续延迟–多普勒平面！）**几乎处处唯一可恢复——直到那四个著名的平凡歧义**：域平移（绝对时延、绝对多普勒）、全局常数相位旋转、以及共轭时间反演（twin-image / 前后镜像）！你们提示词第 9 行写出的“导频只需要定绝对时延、绝对多普勒、整体相位、前后镜像”，**分毫不差地就是稀疏自相关/相位恢复的四个经典平凡歧义（trivial ambiguities）**。
- **D. A. Barmherzig, J. Sun, P.-N. Li, T. J. Lane, and E. J. Candès**, *"Holographic Phase Retrieval and Reference Design,"* *Inverse Problems*, 2019, `arXiv:1901.06453v2`, `DOI:10.1088/1361-6420/ab23d1` `[已读原文（摘要与 Sec. 1）]`。
  - **底层逻辑重合**：在自相关/相位恢复中故意并入一个已知的“参考部分”（reference），专门用来破除移位、相位和孪生镜像（twin-image）歧义，并直接从信噪比与重建误差出发优化参考信号设计。这和“让叠加导频专门定参考消歧、把主体支撑交给自相关”在信息论与几何结构上是同一个原理。
- **重合程度**：**同一机制、不同场景**。这组文献的杀伤力在于：**你不能把“自相关能恢复全部稀疏路径位置只差平移、全局相位与镜像，加上一个已知参考就能破掉这四个歧义”写成自己的原创数学发现**——这在稀疏相位恢复里已经是定理级常识。它们同时也给你们提供了一个现成的理论武器：只要你的稀疏通道在 $(\ell, \nu)$ 二维平面上无差值碰撞（$P=8$ 在 $103 \times \text{连续多普勒}$ 上几乎必然无碰撞），从理论上就保证了弱径间交叉峰与镜像歧义可解。

---

### 5. 声学/水声/声呐倒谱与被动雷达单通道自模糊函数

1. **倒谱（Cepstrum）与自相关多径回声检测**：**D. G. Childers, D. P. Skinner, and R. C. Kemerait**, *Proc. IEEE*, 1977, `DOI:10.1109/proc.1977.10747` `[核验 DOI，正文凭记忆未核实]`（源起 Bogert–Healy–Tukey 1963 `[凭记忆，未核实]`）；水声实际应用 **E. L. Ferguson, S. B. Williams, and C. T. Jin**, *"Improved Multipath Time Delay Estimation Using Cepstrum Subtraction,"* *IEEE ICASSP*, 2019, `arXiv:1810.11990` `[已读原文（摘要与 Sec. 1）]`。
   - **重合与不重合**：单水听器面对未知宽带辐射源，利用直达声与反射声在自相关或对数功率谱倒谱上的周期条纹（Lloyd's mirror 干涉 Eq. (1)）来盲检相对时延差。但它是**一维纯时延（静态或慢变）**，没有多普勒轴（多普勒扩展会冲毁频谱条纹），也没有叠加导频与编码译码。
   - **重合程度**：**同一机制（一维退化特例）、不同场景**。
2. **被动雷达（PCL）与单通道自模糊函数（AAF）**：
   - 传统双通道被动雷达（如 Colone et al., *IEEE TAES* 2009 `[凭记忆，未核实]`）有专门指向发射机的干净参考天线，算的是互模糊函数（CAF）而非自相关，与你们**只是表面相似**。
   - 真正重合的是**无参考通道/单通道被动雷达**：接收信号是强直达径 + 多径目标回波之和，直接计算单路信号的自模糊函数 $\chi_r(d, f) = \sum_n r_n r^*_{n-d} e^{-j2\pi f n/N}$，物理上正是把强直达径当自带参考，在 $(d, f)$ 平面上显示目标相对直达径的时延差与多普勒差（注：本次通过 arXiv 与 OpenAlex 以 `"passive radar"` + `"single-channel" / "without reference" / "self-ambiguity" / "auto-ambiguity"` 检索，仅找到讨论 SiriusXM 帧结构导致的多普勒自模糊论文 `arXiv:2609.09393` `[未读正文]`，未直接抓取到代表性单通道 AAF 多目标捕获全文，故该细节标记为 `[凭记忆，未核实]`）。核心差异在于：被动雷达直达径比目标高 40–80 dB，工程痛点是如何挖空/重调并消除直达径与强静止杂波的巨大旁瓣基底，且无合作叠加导频；你们则在通信符号离散星座和编码约束下利用中低功率比与单帧 ZC 锚定。
   - **重合程度**：**同一机制、不同场景**。

---

## 二、为什么叠加导频 OTFS / AFDM 这一行没用数据二阶统计来捕获？

先摆直接检索的客观事实：**在我对 6 篇主流叠加导频/无保护带 OTFS 与 AFDM 原文的全文逐篇核查中，没有任何一篇用未知数据的二阶自相关来做初始路径捕获。** 具体包括：
- **H. B. Mishra et al., *IEEE TWC* 2021 (`arXiv:2010.15066`)** `[已读原文]`：虽有 "second-order statistical characteristics" 字样（Sec. III-B, Eq. (28) 后），那是指“把未知数据当干扰做导频信道估计后，估计误差向量 $\mathbf{e}_p$ 的均值和方差”，用来喂给 MP 数据检测器，完全不是对接收信号求二阶自相关找路径；
- **K. Zheng et al., *IEEE TVT* 2025 (`arXiv:2404.10232v1`)** `[已读原文]`：全文无任何 data autocorrelation / cyclostationarity；
- **Y. Kanazawa et al., *IEEE TVT* 2026 (`arXiv:2501.15935v3`)** `[已读原文]`：LDPC 编码 SP-OTFS，仅用导频门限 + 译码回代干扰消除，无数据二阶统计；
- **Y. Luo et al., *IEEE TCOM* 2026 (`arXiv:2607.18881`)** `[已读原文]`：SP-AFDM 离格 SBL，硬判决数据辅助，无数据二阶统计；
- **A. Mehrotra et al. (`arXiv:2305.15855`)** `[已读原文]`：SP-OTFS MIMO，无数据二阶统计；
- **Z. Yuan et al. (Nov 2026, `arXiv:2611.14877v1`)** `[已读原文]`：无保护带交织导频分数多普勒 AFDM，联合贝叶斯消息传递，无数据二阶统计。

至于“有没有人私下试过但因为单帧样本方差太大而放弃、所以没发出来”——**不知道**（未见任何公开负面记录或讨论）。

但从已读文献与 `READOUT.md` 的数据里，能清楚看到社区错过它的三个结构性原因：
1. **主流工作区屏蔽了交叉点**：现有 SP-OTFS/AFDM 论文大多默认工作在较高的导频比（典型 $\rho \approx 0.3\text{–}0.5$）或按无编码 NMSE/BER 调参。`READOUT.md` 直接显示：在 $\rho = 0.30\text{–}0.50$，导频匹配滤波本身就能抓回 **99.4%–100%** 的有效弱径；更微妙的是，由于叠加了确定性的 ZC 导频，导频自己的延迟乘积会在自相关平面制造确定性竞争峰——你们严格判据下自相关捕获率在 $\rho = 0.30$ 掉到 `0.722`、在 $\rho = 0.50$ 直接暴跌到 `0.196`！所以在大家习惯的 $\rho \ge 0.3$ 区间去试，不仅没必要，甚至显得不如纯导频好；只有下探到编码系统才敢用的 $\rho \le 0.15$，数据二阶统计才会反超导频。
2. **传统盲估计对“多帧精确求解”的思维定式**：信号处理教科书（Tsatsanis–Giannakis 1997、Giannakis–Tepedelenlioğlu 1998）以及唯一的 AFDM 协方差先例（Ranasinghe `2407.05328`）都试图只靠二阶统计完成**全盲高精度估计**，因此在单个短帧（$N=1024$ 甚至 $N=64$）上必然撞上有限样本方差墙，逼着大家堆到 $T=100\text{–}10000$ 帧。没有人退一步想：在**编码接收机**里，第 0 轮根本不需要靠自相关把增益和频偏算准，只要靠它把漏掉的弱径拖进候选池，后续编码迭代的相干积分就能把精度捞回来。
3. **方法血统的路径依赖**：叠加导频通信一脉（从 Tugnait 2003/2006 到 Mishra 2021、Zheng 2024、Luo 2026）始终沿着“一阶导频均值初估 + 数据辅助迭代消除（DML/MP/SBL）”往下走，研究注意力全部花在怎么消掉未知数据干扰，下意识把第 0 轮数据看作纯毒药而非免费的高信噪比探针。

---

## 三、分项判定、最危险三篇先行工作与残余可站立主张

### 1. 分项结论

| 分拆模块 | 判定 | 一句话依据 |
|---|---|---|
| **(a) 用未知数据二阶统计辨识双选信道** | **已被做过** | 经典时变循环自相关（Tsatsanis–Giannakis 1997/1998）与 AFDM 盲样本协方差（Ranasinghe `2407.05328`）均已做过。 |
| **(b) 径对在 $(\Delta\ell, \Delta\nu)$ 处恢复稀疏多径** | **已被做过** | 射电天文二次谱及“核心作锚暴露弱径”全息机制（Cordes 2006）、稀疏相位恢复 Turnpike 唯一性（Ranieri `1308.3058`）与 AFDM 盲协方差交叉项（`2407.05328`）均已做过。 |
| **(c) 导频只负责消歧/定参考、找径交给数据统计** | **机制已有、用在新场景** | 抽象逻辑已有全息参考相位恢复（Barmherzig `1901.06453`）、半盲旋转消歧（Jagannatham–Rao）与多天线双选相关找 MSLs（Mehrabani `2024`）；但在 **SISO 单帧叠加导频分数多普勒**里把“极低功率导频”专职降格为“解平移 + 全局相位 + 镜像歧义的锚”尚属新场景迁移（明显不同于 Tugnait 一阶均值路线）。 |
| **(d) 降低编码系统导频开销 + 数据/导频交叉点** | **候选新意（端到端未证）** | 在 SP-OTFS/AFDM 6 篇主流原文中未见利用“$\rho \le 0.15$ 数据自相关反超导频匹配滤波”的交叉点突破编码自举极限；但目前仅测到“上帝锚定下的候选可见性”，编码 FER 与端到端降导频尚未检验。 |
| **(a)–(d) 整体组合** | **已知原理的跨界新组合 + 潜在新系统机制** | 数学构件均非首创，真正可能长成 TCOM 核心贡献的，是“单帧自相关粗捕获 + 超低功率导频全息消歧 + 编码接收机突破 $\rho < 0.25$ 悬崖”这一闭环。 |

### 2. 最危险的三篇先行工作

1. **K. R. R. Ranasinghe et al., `arXiv:2407.05328v2` (2024)** `[已读原文]`（及关联 *IEEE TWC* 2025）——就在 AFDM 同波形、同双色散信道上写了 $\tilde{\mathbf{R}}_Y = \sum_{p,q} h_p h_q^* \boldsymbol{\Gamma}_p \boldsymbol{\Gamma}_q^H$ 并利用非对角交叉项做稀疏参数恢复，最容易让审稿人一棍子打死为“AFDM 二阶协方差寻径已有”。
2. **M. K. Tsatsanis & G. B. Giannakis (*IEEE TSP* 1997, `10.1109/78.650270`) + G. B. Giannakis & C. Tepedelenlioğlu (*Proc. IEEE* 1998, `10.1109/5.720248`)** `[核验 DOI，正文凭记忆未核实]`——确立了时变信道输出的时变自相关频谱精确出现在成对多普勒之差 $\omega_q - \omega_{q'}$ 上，堵死了把差分频移当作新数学推导的口子。
3. **J. M. Cordes et al. (*ApJ* 2006, `astro-ph/0407072`) `[已读原文]` + J. Ranieri et al. (`arXiv:1308.3058v2`) `[已读原文]` + D. A. Barmherzig et al. (`arXiv:1901.06453v2`) `[已读原文部分]`**——分别从物理成像和组合数学上做透了“强径作全息锚在差分时延–多普勒二次谱里拎出弱径”与“已知参考破除自相关平移/全局相位/孪生镜像四大歧义”。
   - **另附一张必须人工核读的潜在暗雷**：**M. R. Mehrabani et al., *IEEE Access* 2024 (`10.1109/access.2024.3441375`)** `[仅读摘要]`，因同样做“稀疏双选信道半盲估计：接收信号相关找主支撑 + 少导频”，若正文细节靠近你们的延迟相关打分，会成为第四枚直接对手。

### 3. 在这三座大山之下，还站得住的主张与硬伤边界

如果不吹牛、只留硬核，真正能站上 TCOM 审稿台的只剩下下面这组**条件性主张**：
1. **物理交叉点事实**：在编码叠加导频双色散通信中，常规一阶导频匹配滤波的弱径检出受制于自身功率比 $\rho$ 与数据自干扰（$\text{SINR}_0 \le \rho/(1-\rho)$），而利用未译码高功率数据（$1-\rho$）的**单帧**时域延迟乘积谱在低 $\rho$ 下反而越强，两者在 $\rho \approx 0.15$ 附近发生功能分工的必然反转——导频越少、数据这把探针越亮（且需在推导中诚实说明：该机制依赖**非零时延差**与**低导频下 ZC 导频自身互相关不压过数据峰**，高 $\rho$ 下自相关严格检测反而劣于导频）。
2. **极低导频叠加的“全息参考”分工角色**：抛弃“导频必须独立抓齐所有径”的自举假定，只需极低功率导频定出有限几个离散对称性参考（最强锚点位置、镜像方向 $\pm d$ 的手性选择、绝对多普勒零点与复增益初始相位），把找漏检弱径交给单帧 $O(N L_{\max} \log N)$ 数据自相关候选提名，从而打破 SP-AFDM 的 $\rho < 0.25$ 崩塌墙。

**但你必须立刻正视四个还没跨过去的死穴**——只要其中一个在真实接收机里爆掉，整套故事立刻作废：
1. **锚点自举鸡生蛋**：`READOUT.md` 用的锚是上帝给的真最强径 `strongest = argmax(g)`。如果 $\rho = 0.05\text{–}0.15$ 时导频连最强径自己都抓歪了、或者最强径和次强径幅度接近时导频挑错了锚，自相关怎么消歧？
2. **候选翻倍与交叉峰混杂**：每个 $(d, f)$ 峰对应 $\ell_s + d$ 和 $\ell_s - d$ 两个镜像位置，而且**次强径与第三强径之间的交叉峰**（non-anchor pairs）同样出现在图上；真实系统里没有上帝标签告诉你哪个峰连着锚，在公共虚警预算之外还得解决“强径–弱径配对 vs 弱径–弱径混杂 + 前后镜像二选一”。
3. **同延盲区（$d = 0$）**：延迟乘积在 $d=0$ 上所有时延能量混成一团、完全看不见与最强径共享同一整数时延的弱径（即 `MIXED8` 类的近距双径，在 `calc.py` 第 71 行直接被跳过）。
4. **单径假设与低 SNR 平方损失**：自相关在能量上是 $h_i h_j^*$ 乘积，面对弱径功率随幅度乘以 $h_s$ 有利，但在低导频极低 SNR 或密集多径散射簇（大量相近径交叉项把平面铺成杂波基底）时，单帧样本噪声方差和互调基底会不会把第 0 轮拖死，以及最后到底能不能把编码 FER 穿越点真实推到 $\rho < 0.25$ 且省下总 SNR，完全未测。

---

## 检索词记录

- OpenAlex API:
  - `https://api.openalex.org/works/https://doi.org/10.1109/access.2024.3441375`
  - `Tsatsanis Giannakis time-varying` (`filter=publication_year:1994-1999`)
  - `Giannakis Tepedelenlioglu basis expansion`
  - `Tong Xu Kailath blind identification second-order`
  - `Meng Tugnait superimposed training` (`filter=publication_year:2003-2009`)
  - `title_and_abstract.search:"cyclic autocorrelation" AND (multipath OR Doppler OR "time-varying")`
  - `title_and_abstract.search:("auto-ambiguity" OR "self-ambiguity") AND (multipath OR delay OR passive)`
  - `title_and_abstract.search:blind AND multipath AND delay AND Doppler AND autocorrelation`
  - `title_and_abstract.search:("superimposed training" OR "superimposed pilot") AND ("second-order" OR autocorrelation)`
  - `OTFS (blind OR "semi-blind") (autocorrelation OR "second-order" OR cyclostationary OR covariance) "channel estimation"`
  - `AFDM (blind OR "semi-blind" OR "superimposed" OR autocorrelation OR cyclostationary) "channel estimation"`
  - `"holographic" "phase retrieval" autocorrelation reference`
  - `Ranieri phase retrieval sparse signals uniqueness`
  - `Cordes parabolic arcs scintillation secondary spectrum`
- arXiv API:
  - `(all:OTFS) AND (all:blind OR all:"semi-blind") AND all:"channel estimation"`
  - `(all:AFDM) AND (all:blind OR all:"semi-blind" OR all:superimposed OR all:autocorrelation)`
  - `(all:"passive radar" OR all:"passive bistatic") AND (all:"single-channel" OR all:"without reference" OR all:"reference-free" OR all:"self-ambiguity" OR all:"auto-ambiguity")`
  - `all:"delay-Doppler" AND (all:autocorrelation OR all:"second-order" OR all:cyclostationary) AND (all:blind OR all:"semi-blind")`
  - `all:OTFS AND (all:"superimposed pilot" OR all:"superimposed training")`
- Crossref API (`query.title` + `query.author`) 与 Google Web Search（核对 Tsatsanis–Giannakis 1995/1997、Meng–Tugnait 2004、Jagannatham–Rao、Mehrabani 2024 MSLs、单通道被动雷达自模糊函数）。


---

# 第二步

读取 `astra-review.md`（尤其是第 4 节）之后，把两份独立检索摆到同一张桌子上看，结论比各自单独看更加锋利。下面直接回答提示词第 5、6 项。

## 四、对照 `astra-review.md` 第 4 节：它漏了什么，哪里结论不同

`astra-review.md` 第 4 节极其精炼（只有一段加三篇引文），方向判断大体准确，但在文献覆盖和结论粒度上**漏掉了几块直接决定审稿生死的拼图**：

1. **漏掉了同波形、同数学对象的直接先例（最危险的遗漏）**
   - `astra-review.md` 只在时间线上退回到 1995 年的 Tsatsanis–Giannakis 会议论文（`DOI:10.1109/ACSSC.1995.540533`，经 Crossref 核实确为 *"Blind identification of time-varying channels using second-order statistics"*, Asilomar 1995），完全漏掉了 **2024 年就在 AFDM 波形上做的盲协方差估计 Ranasinghe et al. (`arXiv:2407.05328v2`, [已读原文])**。后者与我们共用完全相同的 AFDM 矩阵表达式、同一稀疏双色散模型，并且显式推出了样本协方差去噪后有效信息全部落在 $p \neq q$ 交叉项 $h_p h_q^*$ 上。审稿人几乎必然拿 `2407.05328` 而不是 1995 年的 Asilomar 论文来质疑“AFDM 下利用信号自相关交叉项提取径对的新颖性”。
   - 同时漏掉了 **Mehrabani et al., *IEEE Access* 2024 (`DOI:10.1109/access.2024.3441375`, [仅读摘要])**——它直接在稀疏双选信道里用接收信号相关先找主支撑（most significant lags）、再配少数导频做半盲重构。这一点比 Meng–Tugnait (2004) 更贴近你们“(c) 相关找径 + 导频省开销”的架构。

2. **漏掉了与“消歧参考”最核心的那半边数学母体**
   - Astra 只列了 Cordes et al. (`astro-ph/0407072`)，准确点出了“径对出现在差分时延与差分多普勒处”，但**没有指出 Cordes 原文（Sec. 3.4.3 Eq. (15) & Sec. 5）已经把“强主导径当全息参考束（hologram reference beam）拎出所有微弱散射径”当核心机理解释过了**，而且也漏掉了组合数学/相位恢复里专门证明自相关恢复唯一性与四大平凡歧义的 **Ranieri et al. (`arXiv:1308.3058v2`, [已读原文])**，以及专门研究“加一个已知参考破除自相关平移、全局相位、孪生镜像三大歧义”的 **全息相位恢复 Barmherzig et al. (`arXiv:1901.06453v2`, [已读原文部分])** 和经典半盲旋转消歧 **Jagannatham–Rao**。
   - 漏掉这几篇的后果很严重：如果你只看 `astra-review.md`，很容易误以为“自相关有歧义、加个已知参考消解歧义”这套分工在抽象层面是新的——其实在相位恢复和半盲 MIMO 领域，“用参考破自相关平移/共轭镜像歧义”也是标准范式。

3. **漏掉了“为什么 OTFS / AFDM 这一行没人用它”的全文证据**
   - `astra-review.md` 对 Meng & Tugnait (2004, `DOI:10.1109/icassp.2004.1326852`, 经 OpenAlex 核实摘要 `[仅读摘要]`，以及其 2006 年双选 CE-BEM 期刊扩展 `DOI:10.1155/asp/2006/85303` `[已读原文]`) 的定性是准确的：该系列第 1 步确实仅用周期叠加训练的一阶统计初估，第 2 步转入 Viterbi / DML 半盲迭代，不用未知数据二阶自相关找径。但它没有检查当代 SP-OTFS / SP-AFDM / 无保护带 AFDM 全文，也因此没给出“主流 6 篇论文几乎全在无编码或 $\rho \ge 0.3$ 工作区，看不到低 $\rho$ 交叉点”这一可核查解释。

4. **对两份评估在已有三篇上的差异与一致处**
   - **Tsatsanis–Giannakis 1995**：一致认为其确立了用二阶统计量（循环自相关）辨识时变基展开信道；本查新补充了其完整期刊谱系（1997 `IEEE TSP`、`Giannakis–Tepedelenlioğlu 1998 Proc. IEEE`），指出循环频率本来就精确落在成对频偏差 $\omega_q - \omega_{q'}$ 上，因此它不仅对 (a) 抢先，也对 (b) 的通信数学机理抢先。
   - **Cordes et al. (`astro-ph/0407072`)**：Astra 仅提了“差分时延与差分多普勒几何先例”；本查新深入原文 Eq. (8)、Eq. (15) 发现，它连“强主径作全息锚把弱径从交叉项干扰里凸显出来”这一整步都先做过。
   - **Meng–Tugnait 2004**：完全一致。它在一阶统计上抢先了叠加训练粗估 + 判决反馈的流程，但没有用数据二阶自相关找径，与本思路在 (a)/(b) 上属于不同机制；真正的近邻威胁是把数据相关找稀疏抽头与导频结合的 Mehrabani (2024) 与半盲 MIMO 消歧一脉。

---

## 五、那句结论还站不站得住？该怎么收窄

`astra-review.md` 第 30 行留下的原句是：

> *“可能新的只剩：用导频估出的参考消解径对歧义，从而找回漏径、降低编码 AFDM 所需导频比例”*

**直接结论：原话在抽象层面上还太宽，必须再砍掉一半包装、收窄为带硬条件的系统级主张才站得住。** 理由有三层：
1. **不能在抽象层面宣称“用已知参考消解自相关歧义”本身是新的**：全息相位恢复（Barmherzig 2019）早就把“放一个已知参考破自相关的平移、相位与孪生镜像歧义”写成了框架，Jagannatham–Rao 也在半盲 MIMO 里做过“数据协方差定空间结构 + 少量导频消旋转歧义”，甚至 Mehrabani (2024) 已经在双选信道里用信号相关先抓主时延延迟以减少导频。如果只拿这句抽象话投 TCOM，会被这几组文献从“一般原理”层直接打穿。
2. **必须把“可能新”精确钉在三个不可拆分的约束交集上**：
   - **体制**：**单帧（$T=1$）**时域延迟乘积 FFT 粗提名（区别于需要 $T \gg 1$ 帧协方差求逆的 Ranasinghe `2407.05328` 和多帧子空间 SVD 的 Tsatsanis–Giannakis），把自相关从“全盲精估器”降格为“第 0 轮候选提名器”；
   - **交叉点与角色转换**：在**编码叠加导频**通信里，揭示数据二阶自相关与导频匹配滤波随导频功率比 $\rho$ 的**反向斜率交叉点**（$\rho \le 0.15$ 数据统计反超导频），使极低功率叠加导频不再承担独立找齐所有弱径的任务，只做 Turnpik/全息参考消歧（定锚点时延–多普勒、破前后镜像 $\ell_s \pm d$、给绝对复相位）；
   - **工程目的**：在编码接收机迭代环兜底精估的前提下，把可工作的导频比真正推过现有 $\rho < 0.25$ 的自举崩塌悬崖，换来**端到端编码 FER 穿越点或最优工作总 SNR 的真实改善**。
3. **三条刚性生效条件（缺一则该主张直接失效）**：
   - **前提条件 1（未验证）**：去掉 `READOUT.md` 里的上帝真最强径锚，在真实极低 $\rho$（如 $0.05\text{–}0.15$）下用导频真实估计出来的锚点 + 真实前后镜像消歧策略，依然能把漏径有效送进第 0 轮并**在编码 FER 上把最优工作点明显推过 $\rho = 0.25$（且总 SNR 确实优于当前 $\rho = 0.30$ 基线）**——否则只是一张漂亮的“可见性玩具图”。
   - **前提条件 2（必须补读核实）**：投稿前必须人工下载阅读 **Mehrabani et al., *IEEE Access* 2024 (`10.1109/access.2024.3441375`)** 的公式，确认其“用接收信号相关找 MSLs”到底是在空间天线维度做还是在时域做，排除它已经用单帧延迟相关做过稀疏支撑提名的撞车风险。
   - **前提条件 3（诚实边界）**：必须显式承认该机制存在 $d=0$ 同延盲区（无法捕获与锚点共享整数时延的近距径）、多非锚点交叉峰混杂以及高 $\rho$ 下的 ZC 导频延迟自相关污染，不将其吹成全能万能检测器。
