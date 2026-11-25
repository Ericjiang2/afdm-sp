查看缓存论文目录并读取点名的三篇论文全文。
读取三篇核心缓存论文的算法与仿真部分，并查看完整缓存目录。
读取缓存中的第3、4、6条核心对应论文。
检索本地缓存关键文献，并精读Kanazawa与Li宽带AFDM核心段落。
核查缓存中的OTFS/AFDM文献标题，并联网检索核心基线算法。
精读第1、3、4、6条对应的缓存论文关键章节。
联网核查CoFEM、NOMP、Liu2024及Wang2022，并续读宽带AFDM与ODDM缓存。
联网查证VALSE/NOMP/CoFEM/Liu2024细节，并扫读其余缓存论文瓶颈。
精读相位噪声/离网SBL/无保护带AFDM缓存论文，并联网补查关键细节。
查验缓存中其余SBL/VB/ODDM/AFDM论文的复杂度与对比结果，并联网检索NOMP/GAMP/CoFEM精确边界。
精读缓存中的ODDM离网SBL与AFDM-SAGE论文，并核查无求逆SBL与VALSE对比。
核查AFDM-SAGE与DI-S-MMSE仿真结果，并检索Fast-SBL与OAMP精度边界。
核对最终引用细节、公式编号与Mamandipoor/Hansen精确实验设定。
总览复核结论：**第 3、4 条丢弃成立；第 2、5、6 条部分成立（原理由存在证据漏洞或范围错位，但按 10× 门槛翻盘空间有限）；第 1 条可能错杀（原理由点名的 5 篇快算法里有 4 篇存在明显工况错配或被公开全文结果反驳，需补低成本验证）。** 下面逐条给证据，最后回答总问题。

---

### 1. 分数时延 + 分数多普勒的离网 SBL 的精确快解
**判定：可能错杀**

**证据（逐项核查原丢弃理由点名的 5 项工作）：**
1. **Chen et al., arXiv:2602.04316v2 (2026)**（[chen26_leo_fdfd_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/chen26_leo_fdfd_afdm.txt)，**已读全文**）：**不成立，属于单径错配**。Section II (p. 2) 明确将信道简化为单径 LOS：$h(\tau,\nu)=h\delta(\nu-\nu_0)\delta(\tau-\tau_0)$，Table I 设导频幅值 $x_{\text{pilot}}=100$，Section V Conclusion 明写 *"Future work will focus on severe multipath or NLOS environments"*。在 $P=3\text{--}8$ 多径下根本不适用。
2. **Ma–Wang–Ni–Luo–Yuan, arXiv:2607.05082v1 (2026, AFNC)**（[wang26_ps_afdm_fdfd.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/wang26_ps_afdm_fdfd.txt)，**已读全文**）：**不成立，对比基线并非离网 SBL 且工况偏温和**。Section V (p. 6) 仅测试 3 径 TDL-C，归一化时延为 $(0.6366, 2.7105, 4.6003)$（相邻径间距 $\approx 2$ 采样格，远大于 1 个分辨单元），功率 $(0, -13.2, -13.9)\,\text{dB}$，$\text{SNR}_p=15\text{--}40\,\text{dB}$；且其对比的 SBL 是 $\delta_\tau^{\text{SBL}}=1, \delta_f^{\text{SBL}}=0.1$ 的 **on-grid SBL**（原文直述 *"whereas SBL relies on an on-grid model"*），并未对比离网 SBL。
3. **NOMP (Mamandipoor et al., IEEE TSP 2016)**（**读了联网检索摘要，未读原 PDF**）与 **公开多径实测对比**：
   - 在通信多径随机连续参数（含近距径）下，**已有两篇公开全文显示 NOMP 显著劣于离网 SBL**：
     - **Wei et al., IEEE TWC 2022**（[wei2022_offgrid_sbl_otfs.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/wei2022_offgrid_sbl_otfs.txt)，**已读全文**）Section VI-A、Fig. 5–7：$P=5$ 条连续随机分布时延–多普勒径下，Off-grid NOMP 的 NMSE 显著高于 1D Off-grid SBL（远大于 0.2 dB；Fig. 6 粗网格 $r_\nu=r_\tau=0.8$ 时 NOMP 甚至输给传统脉冲法）。
     - **Xu et al., arXiv:2604.17858v1 (2026)**（[xu26_sbl_pn_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/xu26_sbl_pn_afdm.txt)，**已读全文**）Section IV、Fig. 2：在无相位噪声的理想晶振 AFDM 信道（$N=64, P=3$）下，Newton-OMP 出现明显高 SNR error floor，远输于动态网格演化 SBL。
   - **需同时记录的反向证据**：**Wang–Pan–Ren–Wang (2026)**（[wang26_moa_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/wang26_moa_afdm.txt)，**已读全文**）Section VII、Fig. 2–4 在 14 符号跨时间双导频、$M=1024, P\in[5,10]$ 下，精心初始化的 MOA-SAGE 与 NOMP-CFAR 反而明显优于其实现的粗网格 SBL（后者出现高 SNR error floor）。但该文未测单帧低导频 SNR 及亚瑞利（$<1$ 分辨单元）散射簇，且其 SBL 基线仅做有限局部细化，不能直接外推到单帧亚瑞利/低 SNR 场景。
4. **Y. Luo et al., arXiv:2607.18881v1 / IEEE TCOM 2026 (D-GAMP-GESBL)**（[sp-afdm-sbl-luo2026.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/sp-afdm-sbl-luo2026.txt)，**已读全文**）：**体制错配**。该文采用全频带 i.i.d. 随机**叠加导频 + 数据辅助**（$x=x_p+x_d$）且 $N_r=8$ 多天线 MMV、粗初始网格 $r_\tau=r_k=1$，字典低相干，GAMP 才得以收敛；不能直接套用到单啁啾导频形成的高相干离网字典。
5. **Hansen–Fleury–Rao, IEEE TSP 2018 (Superfast LSE)**（**读了联网检索摘要，未读原 PDF**）：它用广义 Schur 加速 1D 离网 SBL，但强依赖协方差的**纯 Toeplitz 结构**（位移秩 2）；AFDM 分数时延的频谱卷绕确实打破了纯 Toeplitz，使其无法直接适用。

**哪一步不成立 & 翻盘风险点：**
- **不成立的步骤**：原理由把上述 5 项工作视为「AFDM 多径 FDFD 场景已有同精度近线性替代」，这在多径近距（$<1$ 分辨单元）、低导频 SNR、同延迟散射簇下缺乏证据支撑，且被 Wei 2022 / Xu 2026 反驳。
- **但草稿自身过 10× 门槛面临两个硬风险**：(a) 位移秩 $\alpha=2K+2$（如 $K=7\text{--}21 \Rightarrow \alpha=16\text{--}44$）时，广义 Schur 的复杂度为 $O(\alpha^2 N\log^2 N)$ 或 $O(\alpha N^2)$，常数项极大，在 $N=256\text{--}1024$ 下未必跑得过 BLAS3 Cholesky（Woodbury 到观测窗 $N_p$ 为 $O(N_p^3)$）；(b) 必须同步对标**活跃集顺序 SBL（Tipping–Faul Fast Marginal Likelihood，只维护 $P\times P$ 逆）**及 **MOA-SAGE**，而不是只对标朴素 $O(G^3)$ 批量 EM。

**需补的便宜检验：**
在单/双啁啾导频 AFDM（$N=256, 512$，$P=5\text{--}8$，专门包含径距 $0.3\text{--}0.8$ 格与 $\text{SNR}_p=0\text{--}10\,\text{dB}$）上，跑两组低成本数值验证：(1) 对比批量 EM 离网 SBL vs NOMP vs MOA-SAGE vs 活跃集 Fast-SBL 的 NMSE，确认精确离网 SBL 是否真有 $>0.5\,\text{dB}$ 不可替代优势；(2) 同机同线程实测位移秩 $\alpha=2K+2$ 求解器与 Woodbury-Cholesky 的耗时比，检查常数是否吃掉加速比。

---

### 2. 数据辅助重估的 Gram 是两级扭曲 Toeplitz（由已知序列的自模糊函数生成）
**判定：部分成立**（若目标是线性重估，丢弃成立；若目标是高相干字典 SBL，原理由中「CoFEM / GAMP 保精度」一步证据不足，但结构化直接法本身仍难过 10× 门槛）

**证据：**
1. **线性均值求解（FFT + CG）**：数据辅助重估的线性方程若只求均值（如 LMMSE / 岭回归），FFT 快算子 + PCG 在良态下确实达到逐位精确且 10×–46× 加速，该部分丢弃完全成立。
2. **CoFEM（Lin–Song–Bilgic–Ba, IEEE TSP 2022, arXiv:2105.10439）在高相干字典上的缺口**（**读了联网检索摘要，未读原 PDF**）：
   - CoFEM 用 Jacobi 预条件 CG + $K$ 个 Rademacher 探针（Hutchinson 对角估计）近似 $\text{diag}(\Sigma)$，其理论分析主要保证对角预处理能消除超参数 $\alpha_j \to \infty$ 造成的病态。
   - **高相干字典的两处隐忧**：(i) 对角探针估计方差为 $\text{Var}(\hat{\Sigma}_{ii}) \propto \frac{1}{K}\sum_{j\neq i}|\Sigma_{ij}|^2$；高相干时延–多普勒字典下 $\Sigma$ 非对角元大，要保 SBL 剪枝与 NMSE 差 $\le 0.2\,\text{dB}$ 需大探针数 $K$，使每次 EM 需解 $(K+1)$ 条线性方程；(ii) Jacobi 预处理无法消除高相干字典 $\Phi^H\Phi$ 自身的小特征值，PCG 步数在强相干下可能远超 13–35 步。
   - **OTFS / AFDM 的应用现状**：联网检索显示已有预印本将 CoFEM 用于 **grant-free massive MIMO-OTFS 的 2D pattern-coupled SBL**（**仅检索摘要**），但**未查到**公开文献验证 CoFEM 在单天线高相干离网/宽基 OTFS/AFDM SBL 上保持 $\le 0.2\,\text{dB}$ 同精度且实测快 $\ge 10\times$。
3. **GAMP 与无求逆 SBL 在高相干字典上不保精度**：
   - 标准 GAMP 依赖近似 i.i.d. 低相干字典，在高相干/相关字典上已知易发散（Rangan–Schniter–Fletcher, IEEE TIT 2019 VAMP；需 SVD/GMD 预处理，而数据辅助重估中字典随外迭代数据更新而变，每轮重做 SVD 仍是立方级）。[sp-afdm-sbl-luo2026.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/sp-afdm-sbl-luo2026.txt)（**已读全文**）能用 GAMP-GESBL 依赖的是全频带随机叠加导频与 $r_\tau=r_k=1$ 粗网格。
   - 另一路线无求逆 MM-SBL 在高相干离网字典上精度失守：**Shan–Shafie–Yuan–Wang (2024)**（[oddm-offgrid.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/oddm-offgrid.txt)，**已读全文**）Section IV & Fig. 4 实测显示，用对角 MM 替代精确求逆的 T-GRAESBI 在 $\text{SNR}=10\,\text{dB}$ 下比精确 GRASBI **损失约 3 dB NMSE**（相对 OGSBI 增益由 11 dB 降至 8 dB）。
4. **但结构化直接法自身的硬伤**：两级块 Toeplitz（尺寸 $L\times Q$，总维数 $D=LQ$）的位移结构直接求解，复杂度为 $O(D^2 \min(L, Q))$，相比稠密 Cholesky $O(D^3)$ **只省一个 $\max(L, Q)$ 因子**（若把较小维放外层则只省 $\min(L, Q)$），且多为 BLAS2 访存，对标高度优化的 BLAS3 Cholesky 在 $D \le 500$ 时实测很难稳定到 10×。

**需补的便宜检验：**
仅当你确认数据辅助重估**必须用高相干字典 SBL（不能用普通 LMMSE）**时，用 30 行脚本在 $D=500\text{--}1000$ 的高相干数据辅助字典上跑 SBL 后期迭代，实测 CoFEM（$K=10, 30, 100$）相对精确 Cholesky-SBL 的 NMSE 差与单线程耗时，确认 CoFEM 是否真的掉精度或慢于位移直接法。

---

### 3. 导频功率比按闭环设计
**判定：丢弃成立**

**证据：**
1. **Kanazawa–Iimori–Pradhan–Malomsoky–Ishikawa, arXiv:2501.15935v3 / IEEE TVT 2025**（[sp-otfs-will-it-work.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/sp-otfs-will-it-work.txt)，**已读全文**）：
   - Section V-A (p. 8) 确实按未编码 BER 离线一维扫描 $\alpha \in [0.1, 0.9]$（步长 0.1），并直接指出 *"These simulations only need to be computed once offline, and both the time and space complexities are negligible"*。
   - 同时需厘清：Fig. 7（coded BER 中 EP 优于 SP）与 Fig. 9(b)/10（等传速率吞吐量中多 SP 优于 EP）的反转，主因是 EP 存在 56% 保护带速率损失、等传速率时被迫采用高阶调制/高码率，而非单由 $\alpha$ 未按闭环优化导致。
2. **Mishra–Singh–Prasad–Budhiraja, IEEE TWC 2022**（[sp-otfs-mishra.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/sp-otfs-mishra.txt)，**已读全文**）：Section IV (eq. 59–68) 确为基于未编码 SP-NI SINR 下界的功率分配，但 Fig. 4(a) 显示 BER 曲线在最优 $\sigma_p^2$ 附近较平坦（在 [sp-afdm-sbl-luo2026.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/sp-afdm-sbl-luo2026.txt) Fig. 7 中亦然）。
3. **已有闭环先例**：**Liu–Guan–González, IEEE TCOM, vol. 72, no. 1, pp. 601–617, Jan. 2024**（*"Turbo BEM OTFS Receiver with Optimized Superimposed Pilot Power"*，即 Kanazawa 文中 Ref [28]，**读了联网检索摘要**）已针对编码 Turbo BEM OTFS 接收机优化叠加导频功率并结合 EXIT chart 分析闭环收敛。
4. **门槛判断**：单标量 $\alpha \in (0,1)$ 在每个 (SNR, MCS) 工作点离线扫 10–20 个点即得闭环最优查找表，不存在对「离线闭环最优标量组合」赢 $\ge 0.8\,\text{dB}$ 的理论空间。原丢弃理由站得住。

---

### 4. 非理想信道下 MRC 反超近似 MMSE
**判定：丢弃成立**（且原草稿对文献现象的归因本身有偏差）

**证据：**
1. **Li–Yuan–Qiu–Li–Xie, IEEE TCOM, May 2024**（[turbo-sic-mmse-zp-otfs.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/turbo-sic-mmse-zp-otfs.txt)，**已读全文**）Section VI-B、Fig. 13 (p. 13)：
   - **关键纠偏**：原文明确写着 *"our proposed **exact MMSE consistently demonstrates superior performance compared to MRC** under the same imperfect channel condition, whereas the **approximate MMSE** can outperform MRC under some imperfect channel conditions"*——精确 SIC-MMSE 在非理想信道下**始终赢 MRC**，反输给 MRC 的只是**跨 $\Delta m=100$ 个子信道复用滤波权重**的近似 SIC-MMSE。
   - 失败机制也仅是工程近似失配：其非理想 CSI 模型用带噪多普勒 $\tilde{\kappa}=\kappa+\Delta\kappa$ 递推时间列，权重复用步长 $\Delta m$ 没随 $\sigma_k^2$ 收缩，放大了相位失配。
2. **Huang–Qiu–Tong–Yuan–Lin, arXiv:2410.17556v1 (2024)**（[oddm-imperfect-ce.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/oddm-imperfect-ce.txt)，**已读全文**）Section V–VII、Fig. 5–6, 9：在 ODDM 实际嵌入导频非理想估计下，hard/soft SIC-MMSE 始终优于 MRC，MRC 反而在高 SNR 出现误差平层。
3. **已知修法**：将信道估计误差协方差 / 期望 Gram（如 **Wang–Shen–Xing–An–Hanzo, IEEE TCOM, Jul. 2022**，**读了联网检索摘要**；以及 [sp-otfs-mishra.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/sp-otfs-mishra.txt) eq. (52)(54)、[oddm-oamp-jed.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/oddm-oamp-jed.txt) eq. (35)-(36) 的变分噪声膨胀）注入检测器，确属无线通信领域成熟且常规的修法。原丢弃理由成立。

---

### 5. 宽基（每抽头 5 个 DPSS 基）数据辅助重估的结构化直接解
**判定：部分成立**（直接写「同 2」略粗糙，但结论大概率仍过不了 10× 门槛）

**证据与补充分析：**
1. **与第 2 条的差异（原理由省略了两点）**：
   - DPSS（Slepian）基函数不是复指数，沿多普勒基数 $Q=5$ 维**不满足**扭曲 Toeplitz 结构，只有沿时延抽头维 $L$ 近似**块 Toeplitz（块大小 $5\times 5$）**，叠加有限帧首尾截断后位移秩至少 $\ge 2Q=10$（含边界项更高）。
   - 若不做先验方差正则化或进入 SBL 后期剪枝，高阶 DPSS 基在帧边缘衰减且列相干度高于单复指数，CG 迭代步数未必和第 2 条完全一致（原理由未专门实测 5-DPSS-SBL）。
2. **为什么仍大概率丢弃成立**：
   - **线性岭回归 / LMMSE 数据辅助重估**：每抽头 5 个 DPSS 的先验方差（按特征值衰减）提供天然正则化，FFT 算子 + 预条件 CG 复杂度为 $O(I_{\text{CG}} Q N\log N)$，实测已远快于稠密 Cholesky；
   - **即便是 SBL 必须精确求逆**：块大小为 $Q=5$ 的块 Levinson / 广义 Schur 复杂度 $\sim O(Q^3 L^2)$ 对比稠密 Cholesky $\frac{1}{3} Q^3 L^3$，理论 FLOPs 比值约 $L/6$，再扣去 BLAS2 vs BLAS3 访存常数差距（3–5×），通常需要极长时延扩展 $L \ge 200\text{--}300$（总未知数 $D \ge 1000\text{--}1500$）才可能实测到 10×；在典型 $L=20\text{--}100$ 下结构化直接法很难达标。

**需补的便宜检验（与第 2 条合并执行）：**
用真实 5-DPSS 基在 $L \in \{40, 100, 200\}$ 上跑 SBL 数据辅助重估，单次实测 PCG 步数、CoFEM 探针精度与块 Levinson 耗时；若 PCG 仍 $<40$ 步且 CoFEM 保 $\le 0.2\,\text{dB}$，则可彻底坐实丢弃。

---

### 6. 宽带时间伸缩下啁啾载波的逐径重聚焦
**判定：部分成立**（检测侧丢弃成立；估计侧原理由论据错位，但估计侧同样面临既有先例与 10× 门槛压力）

**证据：**
1. **核查 Li et al., arXiv:2507.03537v1 (Jul 2025)**（[li25_wideband_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/li25_wideband_afdm.txt)，**已读全文**）：
   - **原文确证部分**：式 (34) 确已给出 DAFT 域展宽 $L_i = \left|\frac{2c_1(\alpha_i^2+2\alpha_i)N(N-1)+2c_1\alpha_i N^2}{1+\alpha_i}\right|+2N_v+1$，式 (45)(46) 确已给出最优 $c_1$ 与 $N < \frac{1}{4\alpha_{\max}}+1$；Fig. 5(b) 与 Section V-A 表明时域信道矩阵 $\bar{H}_T$ 远比 DAFT 域 $\bar{H}$ 稀疏，其 CD-D-OAMP 即在时域求解。
   - **原丢弃理由的两处不严谨**：
     1) **检测与估计错位**：[li25_wideband_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/li25_wideband_afdm.txt) Section IV–VI **全程假设完美 CSI**（p. 8 *"The perfect channel state information (CSI) is assumed at the receiver"*），完全未做信道估计；而「逐径重聚焦」针对的是 DAFT 域宽带模糊下的参数估计/分辨。
     2) **时域矩阵性质与强多尺度约束**：按 [li25_wideband_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/li25_wideband_afdm.txt) eq. (15)-(16) 与 **Cao et al., GLOBECOM 2024 / arXiv:2405.02660v2**（[cao24_wideband_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/cao24_wideband_afdm.txt)，**已读全文**）eq. (8)，时域矩阵含 $\text{Sa}(\pi((1+a_i)m-f_s\tau_i-n))$，是**拟带状（$1/|\Delta|$ 衰减）而非严格带状**，严格意义上带状分解是截断近似（但配合 CG/拟带状预条件确可精确解）。另外在强多尺度水声（如 [cao24_wideband_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/cao24_wideband_afdm.txt) Fig. 6 测到 $a_{\max}=10^{-3}, 10^{-2}$）下，Li 的 $N < 1/(4\alpha_{\max})+1$ 会把 $N$ 压到 $<251$ 甚至 $<26$ 而失效。
2. **但为什么即便转看估计侧也很难翻盘**：
   - **检测侧**：不同径有不同的 $a_i$，单次 DAFT/FrFT 无法同时聚焦全部 $P$ 条径；反倒是时域里即使 $a_{\max}=10^{-3}\text{--}10^{-2}, N=1024$，斜移 $a_{\max}N$ 仅 $1\text{--}10$ 采样点，时域拟带状 CG / CD-D-OAMP 已经足够快。
   - **估计侧**：利用「伸缩后的啁啾仍是啁啾（调频率变为 $c_1(1+a_i)^2$）」做逐径 FrFT 重聚焦，在宽带水声 MSML 信道估计里已有经典先例（**Zhao–Yu–Wei–Ji–Chen, IEEE TSP, vol. 64, no. 20, pp. 5396–5408, Oct. 2016**，即 [cao24_wideband_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/cao24_wideband_afdm.txt) 的 Ref [13]，**仅读引文标题与摘要**；通过 FrFT 逐径聚焦估计多尺度多时延）。对宽带 AFDM 而言，逐径去啁啾 + FFT 实质就是 2D 匹配滤波的常规加速，除非能针对宽带强多尺度高分辨离网估计证明新机制，否则难过独立创新与 10× 门槛。

**需补的便宜检验（仅当想核查估计侧是否错杀）：**
在残余多尺度差 $\Delta a \in [5\times 10^{-4}, 5\times 10^{-3}]$、$N=1024$（超出 Li25 式 (46) 区间）下，对照 Zhao TSP 2016 的 FrFT 逐径剥离与 Cao24 AFDM-OMP，核查 AFDM 多啁啾结构是否提供任何超越单啁啾 FrFT 重聚焦的额外精度或降阶收益。

---

### 总问题：对「单天线单用户双色散接收机里算力账没有 10× 位置」的最强反例

先给严格审稿判断：
- **在「检测侧（编码工作点、条件数 4–40 的线性子问题）」上，你的总判断基本成立——我查不到能稳过全部门槛的强反例。**
  - *附记一个边缘弱反例（不硬凑，明说其弱点）*：在带非均匀译码外信息方差 $V=\text{diag}(v_1,\dots,v_{MN})$ 的精确 SISO-LMMSE Turbo 均衡中，需要每轮重算 $(H_{DD}VH_{DD}^H + N_0 I)^{-1}$ 及其全部 $MN$ 个对角线外信息方差（**H. Li & Q. Yu, IEEE TCOM, vol. 71, no. 3, Mar. 2023**，[di-smmse-otfs.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/di-smmse-otfs.txt)，**已读全文**，Sec. III & V，Fig. 8(a) 显示其稀疏近似逆 FSPAI 在分数多普勒下比精确逆在未编码时掉 0.8 dB、编码时掉 0.3 dB）。它之所以**不能算强反例**，是因为单天线 OTFS/AFDM 信道硬化效应强，用标量平均方差 $\bar{v}I$ 的跨域 OAMP（配合时域带状求逆，如 [oddm-oamp-jed.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/oddm-oamp-jed.txt) / [li25_wideband_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/li25_wideband_afdm.txt)）是否会相对精确非均匀 $V$ 的 SISO-LMMSE 掉 $>0.2\,\text{dB}$，我未查到公开实证支持。

- **在「估计侧」上，存在 1 个明确的强反例**（恰好突破了你总判断的两个隐含前提：「条件数只有 4–40」以及「只需要求线性均值」）：

#### 最强反例：单天线双色散（OTFS / ODDM / AFDM）中「高相干动态字典的 2D 离网 / 网格演化 SBL（含联合相位噪声）」每步 EM 迭代的精确后验协方差求逆与非对角协方差计算

- **≥ 3 个独立课题组（2022–2026，均已读全文）卡在同一运算上：**
  1. **UNSW + 北交大组**：
     - **Z. Wei, W. Yuan, S. Li, J. Yuan, D. W. K. Ng**, *"Off-grid Channel Estimation with Sparse Bayesian Learning for OTFS Systems"*, IEEE TWC 2022（[wei2022_offgrid_sbl_otfs.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/wei2022_offgrid_sbl_otfs.txt)，Sec. III-B & V-B，eq. (31)(33)(68)(71)-(72)）：1D 离网 SBL 被卡在 $O(N_\nu^2 M_\tau^2 N_T M_T)$ 级矩阵求逆（降维到 2D 解耦版则因步间误差传播在 Fig. 5–6 掉显著精度）。
     - **Y. Shan, A. Shafie, J. Yuan, F. Wang**, *"Off-grid Channel Estimation for Orthogonal Delay-Doppler Division Multiplexing Using Grid Refinement and Adjustment"*, arXiv:2407.06580 / IEEE TWC 2024（[oddm-offgrid.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/oddm-offgrid.txt)，Sec. III-B eq. (22)、Table II、Fig. 4 & 6）：
       - **被卡运算**：每步内部 SBL 迭代的观测域稠密协方差求逆 $\Sigma_{\bar{h}} = \Gamma - \Gamma \bar{\Phi}^H (\lambda I_{M_T N_T} + \bar{\Phi}\Gamma\bar{\Phi}^H)^{-1}\bar{\Phi}\Gamma$（eq. (22)），复杂度 $O(N_{\text{inter}} (M_T N_T)^3)$；即使在 $M_\tau=N_\nu=8$ 的小网格下，Table II & Sec. V 报出总复数乘法量高达 **$1.299 \times 10^9$**，远远超过单帧译码开销。
  2. **Surrey + 重庆大学组**：
     - **Q. Luo, L. Liu, Z. Li, Q. Peng, H. Wu, P. Xiao**, *"Grid-Refinement SBL for AFDM Channel Estimation Under Fractional Delay and Fractional Doppler Channels"*, arXiv:2610.41997v1, Oct. 2026（[afdm-2d-sbl-luo2026.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/afdm-2d-sbl-luo2026.txt)，Sec. III-C/D，eq. (15)(21)(25)）：
       - **被卡运算**：单天线 AFDM FDFD 下每步 EM 迭代对精度矩阵稠密求逆 $\Sigma_{\bar{h}}^{(t)} = (\rho^{(t)}\bar{\Phi}_p^{1D,H}\bar{\Phi}_p^{1D} + \text{diag}(\theta^{(t)}))^{-1}$（eq. (15)），复杂度 $O(N_p(N_l N_\nu)^2 + (N_l N_\nu)^3)$ per iteration，且 eq. (21)(25) 的离网时延/多普勒更新显式用到 $\Sigma_{\bar{h}}$ 的非对角元素与导数矩阵耦合。原文 Conclusion 明确将低复杂度实现列为未解未来工作。
  3. **华中科大 + Univ. of Essex 组**：
     - **Y. Xu, H. Zhang, L. Xiao, G. Liu, Z. Liu**, *"Joint Phase Noise and Off-Grid Channel Estimation for AFDM Systems via Sparse Bayesian Learning"*, arXiv:2604.17858v1, Apr. 2026（[xu26_sbl_pn_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/xu26_sbl_pn_afdm.txt)，Sec. III-A/B，eq. (11)(18)(22)）：
       - **被卡运算**：单天线 AFDM 联合相位噪声与离网网格演化每步 E-step 观测域求逆 $(\beta^{-1}I_N + \Psi\Gamma\Psi^H)^{-1}$（eq. (11)，其中 $\Psi = P(\eta)\Phi(G)$ 每步动态变化），复杂度 $O(N^3 + N^2 M_S)$ per iteration，且 eq. (18) 的 PN 更新依赖 $\Sigma^{-1}$、eq. (22) 的网格演化依赖非对角 $\Sigma$；论文仿真被迫局限在 $N=64$（Sec. IV）。

- **为什么目前查不到 $\le 0.2\,\text{dB}$ 同精度快算法：**
  - **无求逆 MM-SBL 不保精度**：[oddm-offgrid.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/oddm-offgrid.txt) Section IV (eq. (43)-(48)) 专门构造了对角化无求逆版本 T-GRAESBI 来消除 eq. (22) 的矩阵求逆，但 Fig. 4 实测在 $\text{SNR}=10\,\text{dB}$ 下比精确 GRASBI **掉约 3 dB NMSE**（另一无求逆基线 T-GEESBI 掉得更惨），远破 0.2 dB 门槛。
  - **标准 GAMP 不保收敛**：嵌入式导频的细网格（$r_l, r_\nu = 0.2\text{--}0.5$）字典高度相干，标准 GAMP 易发散；[sp-afdm-sbl-luo2026.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/sp-afdm-sbl-luo2026.txt) 的 GAMP-GESBL 依赖的是全频带随机叠加导频与粗网格。
  - **VAMP / UTAMP 降不了阶**：由于网格演化 $G^{(t)}$ 与相位噪声 $P(\eta^{(t)})$ 每步都在改变感知矩阵 $\Psi^{(t)}$，无法离线一次性 SVD，每步重做 SVD 仍是 $O(N^2 M_S)$。
  - **CoFEM（Lin et al. TSP 2022）尚未过关**：细网格离网字典 + SBL 剪枝使条件数远高于 4–40，且离网 M-step 需非对角耦合项与高精度方差估计，目前未查到 CoFEM 在该类动态高相干离网 SBL 上达到 $\le 0.2\,\text{dB}$ 且实测 10× 加速的证据。

- **严格边界声明**：该反例成立的前提是系统工作在**需要离网贝叶斯联合推断的工况**（如单帧嵌入式导频近距多径、或带强相位噪声的联合估计）；若系统允许退回多符号长导频且无相位噪声，参数化方法（如 [wang26_moa_afdm.txt](file:///Users/guoyikun/.cache/idea-funnel/pdf_cache/papers/wang26_moa_afdm.txt) 的 MOA-SAGE）可绕开批量 SBL。除此反例外，在 2022–2026 年单天线单用户双色散接收机文献中，**我查不到第二个能同时满足「≥ 2 个独立课题组卡住 + 无 $\le 0.2\,\text{dB}$ 同精度快算法 + 算力占比压过译码」的强反例**。
