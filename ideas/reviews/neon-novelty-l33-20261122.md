# Neon 查新初筛（第 6 步：l33）——本地第 4 轮，2026-11-22

模型：gemini-4-neon-high（agy 沙箱，paper-search + scoop-check）。l33 由 GPT-6.2 Sol 出题，跨家族。提示：`~/.cache/idea-funnel/afdm-20261122-l4/s13-neon.prompt`。以下为原文。

- **一句话结论**：**不值得做（省去 L2）**

- **固有重要性（抛开先例）**：**低** — 整套“Gram 图连通分量决定校准维数”的数学在真实连续参数信道里以概率 1 退化为 $d_{\mathrm{cal}}=1$（即“当前帧导频顺手估一个公共复标量”的工程常识），且同时要求“每帧本振独立重锁”与“31 帧多径几何严格冻结”自相矛盾；即便白送真实 8 径子空间，它在 1 步预测下仍输给最朴素的最强径相位参考，4 帧外即反亏，改不了任何接收机设计决定。

- **白话 + 一个类比**：
  把一帧里的多径信道想成一面带刻度的表盘，每次拍照前有人把整块表盘随机转一个角度（本振相位重置），所以绝对朝向丢了，但指针之间的夹角（各径相对幅相）还在。卡片声称用 31 张历史照片的“内积连线图”就能算出下一帧只需要用导频定几个朝向，但现实里这张连线图几乎永远是一整块（只要各径功率和多普勒不是刻意凑出零测度抵消），于是结论剥掉术语后只剩一句常识：**历史上能预测出多径的相对形状，新帧来临时用导频补估这一个整体旋转角就行**。更尴尬的是，如果表盘上本来就有一根最粗的指针（最强径）能直接认出来，按最粗指针先对齐再预测，比绕一圈算无标签内积图准得多——而卡片自己已经假设各径时延互异，在时延域本来就分得开。

- **最接近的工作（≥5 篇）**：
  1. **Ubadah & Mohammed (2026)**, *Inter-frame Channel Prediction for Zak-OTFS*, `arXiv:2607.09184v1`（[arXiv](https://arxiv.org/abs/2607.09184)）— **读了全文**：证明 Zak-OTFS 跨帧有效 DD 信道满足确定性旋转不变性 $h_{n,m}=\sum_i \alpha_i^n\beta_i^m A_i$，用 $Q=30$ 个训练帧的 ESPRIT 预测 60–120 帧后的零导频信道；与线 A 差在线 A 放开了跨帧公共相位参照、把零导频预测退回为“当前帧导频校准标量”，却丢掉了长预测视界（4 帧外反亏）。
  2. **Wei, Jiang, Dang, Wu & Zhang (2022)**, *Accurate Channel Estimation for mmWave Massive MIMO With Partially Coherent Phase Offsets*, IEEE Commun. Lett., vol. 26, no. 9, pp. 2170–2174（`doi:10.1109/LCOMM.2022.3184790`）— **读了摘要与检索记录**：明确建模“同一训练帧内共享公共相位、不同帧间存在独立未知相位偏置（partially coherent phase offsets）”，用两阶段 EM-GAMP/EM 跨帧共享稀疏信道结构并单独估计每帧相位偏置；与线 A 差在它做的是 mmWave 角度域稀疏信道估计，而非 Zak-OTFS 跨帧酉演化预测与 Gram 图维数判定。
  3. **Stefanatos & Katsaggelos (2008)**, *Joint Data Detection and Channel Tracking for OFDM Systems With Phase Noise*, IEEE Trans. Signal Process., vol. 56, no. 9, pp. 4230–4243（`doi:10.1109/TSP.2008.925968`；同类基础工作见 **Petrovic, Rave & Fettweis**, IEEE TCOM 2007 `doi:10.1109/TCOMM.2007.902593`；**Mehrpouyan et al.**, IEEE TSP 2012 `doi:10.1109/TSP.2012.2202652`；**OTFS 相噪版** `arXiv:2605.14720`）— **读了摘要与检索记录**：把慢变多径信道响应的跨块跟踪与快变/逐块公共相位误差（CPE，单个复标量）解耦，历史跟踪信道结构、当前块导频/判决单独跟踪公共相位；与线 A 差在经典 CPE 文献多假设 Wiener 相位随机游走或每符号标量偏置，而非每帧独立均匀重置，但“形状跨帧预测 + 当前导频补一个标量”的接收机架构完全一致。
  4. **3GPP TR 38.843（Rel-18/19 AI/ML CSI Prediction）与无线 CSI-Ratio / SRS 相位对齐文献**（如 **Li et al.**, *CSI-Ratio-Based Doppler Frequency Estimation in ISAC*, IEEE Sensors J. 2022；3GPP SGCS 指标 $\frac{|\mathbf{h}^H\hat{\mathbf{h}}|^2}{\|\mathbf{h}\|^2\|\hat{\mathbf{h}}\|^2}$ 与 SRS 跳频/天线切换相位不连续预处理）— **读了摘要、标准综述与检索记录**：3GPP 直接用相位无关的广义余弦相似度（SGCS）衡量“预测信道方向（允许差一个未知复标量）”，把当前时隙的绝对复增益/相位留给 DMRS/PT-RS 估计，面对帧间/包间随机相偏常规采用最强径/最强波束相位锚定或 CSI-Ratio 消去；与线 A 差在标准和工程直接走相位锚定 + 方向预测，不构造无标签 Gram 图。
  5. **Chien & Waldron (2016)**, *A Characterization of Projective Unitary Equivalence of Finite Frames and Applications*, SIAM J. Discrete Math., vol. 30, no. 2, pp. 976–994（`doi:10.1137/15M1042140`；配套图相位同步见 **Singer (2011)**, *Angular synchronization by eigenvectors and semidefinite programming*, ACHA `doi:10.1016/j.acha.2010.02.001`）— **Chien & Waldron 读了全文；Singer 读了摘要与检索记录**：证明有限向量组在逐向量未知相位变换下的射影酉等价完全由 frame graph（Gram 图）的连通分量和基环 $m$-乘积刻画，每个连通分量恰好保留 1 个独立规范相位自由度；与线 A 差在它们是纯框架理论与图同步理论，线 A 的 $d_{\mathrm{cal}}(u)=\#\{c:\Pi_c u\ne 0\}$ 是 Chien–Waldron Theorem 3.1 分块对角 Gram 矩阵的直接推论。
  6. **Eldar, Liao & Tang (2018)**, *Sensor Calibration for Off-the-Grid Spectral Estimation*（沿袭 Paulraj–Kailath 1985 与 Wylie–Roy–Schmitt 1994；[PDF](https://wliao60.math.gatech.edu/Research/papers/Calibration_ELT.pdf)）— **读了全文**：研究 $R_y=\operatorname{diag}(g)T(f)\operatorname{diag}(\bar{g})$ 形式的未知逐阵元/逐快拍对角复增益相位下的无网格频率（等价于多普勒）辨识，在 Lemma 1、Theorem 1 与 §2.3 证明只要 $|f_1|>0$（一般参数下几乎必然成立，且可推广至任意非零滞后 $f_k$），频率与相位校准参数唯一可辨识，仅剩常数相位 + 线性相位斜率（公共频移）平凡歧义；与线 A 差在场景是阵列自校准而非 Zak-OTFS 帧间预测，但底层的 Toeplitz + 对角相位算子同构。
  7. **Carrascosa & Stojanovic (2010)**, *Adaptive Channel Estimation and Data Detection for Underwater Acoustic MIMO–OFDM Systems*, IEEE J. Oceanic Eng., vol. 35, no. 3, pp. 635–646（`doi:10.1109/JOE.2010.2052326`；另见 **Stojanovic**, OCEANS 2006 及 **Nayer & Vaswani**, *Phaseless Subspace Tracking*, ICASSP 2019 `doi:10.1109/ICASSP.2019.8683458`）— **读了摘要与检索记录**：水声 OFDM 早已采用块间稀疏信道跟踪配合判决导向相位/多普勒跟踪，而无相位子空间跟踪也已有系统算法；与线 A 差在未绑定到 Zak-OTFS 帧间本振重置设定。

- **查新判断**：**部分被做过（`scoop-check` 判 Level 2 — High Overlap）**。四个维度里，问题建模（帧间公共相偏/不连续下的信道预测与当前帧标量定相：Wei 2022、3GPP TR 38.843 SGCS、OFDM/MIMO CPE 跟踪）、数学机制（Gram 图连通分量决定规范相位自由度 + 对角相位 Toeplitz 辨识：Chien–Waldron 2016、Singer 2011、Eldar–Liao–Tang 2018）和核心洞见（跨帧公共相偏不破坏帧内相对幅相、新帧只需补 1 个标量）均已被做过；唯一增量只是把这几块拼到 Ubadah–Mohammed (2026) 的 Zak-OTFS 跨帧预测上，且拼出的所谓“多分量校准维数 $d_{\mathrm{cal}}>1$”在真实信道里退化为空壳。

- **为什么没人做**：**(2) 发现了但不重要**（附带 (3) 的隐藏系统开销税：用 31 帧训练只换来 < 4 帧有效预测期）。
  - **证据 1（数学退化）**：在本问题模型下 $G_{jk}=\sum_{i=1}^P |h_i|^2 \alpha_i^{j-k}$ 是 Hermitian Toeplitz 矩阵；如 Eldar–Liao–Tang (2018) §2.1 指出，连续随机功率与多普勒下 $|f_1|>0$ 几乎必然成立，Gram 图必然单连通（$d_{\mathrm{cal}}\equiv 1$）。卡片举的反例（两径严格等功率且每帧相对相位恰转半圈）是连续参数空间中的零测度事件；更致命的是，卡片自己也承认在这个反例里只要从历史帧出发预测下一帧，$d_{\mathrm{cal}}$ 依然是 1。因此“用 Gram 图判定需校准几个分量”不会改变任何真实系统设计。
  - **证据 2（标准与工程早已有更强且更简单的解法）**：3GPP Rel-18/19 AI/ML CSI 预测直接以相位无关的 SGCS 预测信道方向、由当前帧 DMRS/PT-RS 估计公共复标量；面对包间/帧间随机相偏，工程上直接选最强径/最强波束作相位参考或用 CSI-Ratio。卡片自己的探针已证明**最强径参考误差为 0.0074–0.0298，远优于其无标签射影预测的 0.0250–0.0667（差 3–5 dB）**。此外，卡片第 54 行强调的“规则 $(3,6)$ LDPC + QPSK 零导频因 $\pi$ 相位翻转误帧率 $\ge 1/2$”只是全 1 码字属于线性码的教科书相位模糊常识（加已知比特加扰或 1 个导频即消除）。

- **真实系统里的影响**：
  - **不会改变任何设计决定，且前提在所有目标系统里均不自洽**：
    1. **物理前提内部冲突**：“每帧本振独立重锁”对应休眠/间歇突发接收，而“8 径时延、幅度、多普勒在等间隔的 31 帧内严格不变”要求极密集的连续短帧。**水声**（本项目 $N=1024, f_s=16\text{ kHz}$ + 102 点前缀，帧长约 70.4 ms，31 帧达 **2.18 s**）：浅水小尺度相干时间通常仅数十至数百毫秒，2 秒内差分时延漂移可达数个至十余个样点（与已淘汰卡 [I-20261121-c24.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261121-c24.md) 的 7.1 样点估算一致），且水声低载频数字采样不存在每帧 RF PLL 随机重锁；**高速陆地无线**（Ubadah–Mohammed 设定的 1 ms 帧长，§V-D 明确指出平稳窗仅约 50–60 ms）：连续 1 ms 接收时 PLL 锁定不会每帧随机重置相偏，一旦进入 DRX 休眠导致重锁，31 帧跨度早已超出 50 ms 平稳窗；**低轨卫星**以强 LoS 直达径为主，直接用最强径作相位参考即可，完全落在卡片自己反证败北的区间。
    2. **探针口径与量级核对**：卡片把 Ubadah–Mohammed 的 $Q=30$ 直接套到本项目 70 ms 水声生成器上并白送真实 8 径子空间（踩 [LESSONS.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/LESSONS.md) 规则 5 与规则 15）；即便在此极端有利的真子空间探针下，1 步预测把信道 NMSE 从 0.1063/0.0652/0.0298 降到 0.0667/0.0437/0.0250（0.76–2.03 dB），在 4/5/6 dB 工作点（$\sigma^2\approx 0.40/0.32/0.25$）折算成等效 SINR 增益仅约 **0.33 / 0.22 / 0.05 dB**，且到第 4 帧高导频档就已反亏，完全无法摊销 31 帧训练开销。
    3. **退守区间自相矛盾**：卡片因输给最强径参考，把立题缩窄到“无法可靠分离参考径、但仍能估好历史 8 维子空间”的环境；但前文刚以“各径时延互异、占不同对角线”为前提推导酉演化，若连最强时延/DD 峰都分不出来，更不可能在 10 帧奇异值比低至 $10^{-5}$ 的病态条件下恢复整个子空间及其射影演化。

- **最强的反对意见（一句）**：在唯一需要跨帧预测的连续短帧体制里本振不会每帧重置、且只要多径可分就必然被“最强径作相位参考”吊打，而把射影酉等价的 Gram 图连通分量搬过来除了在零测度反例上装饰数学外，在真实信道里永远退化成“当前帧导频顺手估一个公共复标量”。

- **如果要做，最便宜的一步检验是什么**：不必进 L2 编码译码仿真；若仍想彻底死心，只需在卡片现有 NumPy 只读探针上撤去“白送真实子空间”和“白送物理径标签”两个作弊前提，直接比较 **“无标签最强 DD/时延峰作相位参考 + Ubadah–Mohammed ESPRIT + 当前帧 1 标量校准”** 与卡片的射影内积预测器（本机 < 30 秒，0 核时）——只要无需真值标签的最强峰参考仍赢（或把 31 帧训练的真实漂移/摊销开销算进总能量后净收益 < 0.3 dB），立即处决。

---

*附注（按个人规则）：上面对线 A 做出了“固有重要性低、不值得进 L2”的方向性价值判断；如需把它拆成更口语化的排查说明，可输入「白话」。*
