读取运行记录并列出探针脚本与本地论文缓存。
读取本地第8轮记录与全部五个探针脚本。
读取第8轮剩余记录并复核本地探针输出。
读取第8轮末尾记录并检查沙箱内 Python 环境。
检索 Zemen-Molisch 与 Krylov 硬件实现并阅读缓存硬件损伤论文。
深查 Zemen-Molisch 准则与硬件实现细节并续读缓存论文仿真节。
并行查阅缓存全文与精准联网核查先验、损伤及硬件实现。
查核 Zemen-Molisch 详细公式、缓存硬件损伤与实现论文。
检索 Zemen-Molisch 细节、Krylov 实现与缓存先验/硬件文献。
深挖 Zemen-Molisch 准则、硬件损伤量化曲线与 Krylov 实现原因。
精搜 Zemen-Molisch 准则与 Krylov 硬件实现并查缓存先验数据。
精准查证 Zemen-Molisch 准则、低比特量化 dB 差、去先验与 Krylov 实现。
补查 Zemen-Molisch 细节、缓存仿真图号与 Krylov 硬件实现。
下面按严格审稿口径逐条复核草稿 9–16 的丢弃理由，并回答 (A)(B)(C) 三个总问题。全文未改动任何项目文件，也不提出新题；引用文献均标明「读了全文」或「仅读摘要/二手综述」。

---

### 草稿 9：数据辅助重估的条件数随波形变，满分集啁啾率在闭环里反输
- **判定**：**丢弃成立**
- **证据与核查**：
  - 核对 [runs.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/runs.md#L640) 与 [l_probe_r8_data_probe_waveform.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/probes/l_probe_r8_data_probe_waveform.py#L1-L38)。探针公式 `10*log10(1 + beta * tr(G^-1)/n)` 对应理想判决下 LS 估计误差折算到 out-of-sample 信道重建误差的等效噪声增量，推导无误。
  - **机理核实**：恒模 QPSK 确实给 OFDM（零多普勒线）、SC（零时延线）、AFDM（啁啾脊）各自一条精确零模糊线，但在二维双色散信道支撑（$L > 1, D > 1$）上，零模糊线只占 $L D$ 个差集对的一维零测度切片，其余非对角元全为 $O(1/\sqrt{N})$ 伪随机旁瓣，Gram 谱由 Marchenko–Pastur 主导，故三种波形在 $\beta=0.10\text{–}0.49$ 内仅差 **0.01–0.15 dB**（远低于倒挂账 0.5 dB 门槛）。
  - **放宽假设也不翻转**：(i) 改高阶 QAM 会同时破坏 OFDM/SC 的恒模正交线，差距更小；(ii) 回到稀疏水声径数（$P=8, D=5, N=1024 \Rightarrow \beta \approx 0.04$），差距缩至 $< 0.02$ dB；(iii) 旁证上，Mirabella et al.（*IEEE JSAC* 2026, arXiv:2602.20909v2，读缓存全文 §III-E 式 (56)–(57) 与 Fig. 6）虽证明非零 $c_1$ 略微抬高单径 CRB，但量级为 $O(c_1^2 N) \sim O(1/N)$，曲线基本重合，不构成 $\ge 0.5$ dB 倒挂。

---

### 草稿 10：每条径一束（逐径波束 → 撤时延/多普勒 → 合并）替代空–时联合 LMMSE
- **判定**：**丢弃成立**（探针漏测空间 MMSE 波束，但不改变丢弃结论）
- **证据与核查**：
  - 核对 [runs.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/runs.md#L643) 与 [l_probe_r8_simo_pathbeam.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/probes/l_probe_r8_simo_pathbeam.py#L1-L41)。
  - **探针瑕疵**：脚本第 22、25 行只测了无正则化的空间迫零波束 `pinv(A)` 和共轭波束 `A.conj().T`，**漏测了空间 LMMSE（Wiener）逐径波束** $\mathbf{w}_p \propto (\mathbf{A}\operatorname{diag}(|\mathbf{h}|^2)\mathbf{A}^H + \sigma^2 \mathbf{I})^{-1}\mathbf{a}_p$。在每阵元 5 dB 下，纯 ZF 在 $N_r = 8\text{–}16$ 和 $\pm 20^\circ$ 线阵上会严重放大噪声，高估了逐径波束的损失。
  - **为何丢弃仍成立**：
    1. **自由度下限**：当 $N_r \le P$ 或小角展强相关线阵时，即便换空间 MMSE 波束，空间自由度仍不足以分离 $P$ 条径，残留跨径 ISI 使其无法满足算力账「精度差 $\le 0.2$ dB」的硬门槛；只有 $N_r \gg P$（通道硬化区）才可能贴近联合解。
    2. **无降阶 + 已有先例**：空–时联合 LMMSE 用稀疏乘法 + CG 每步复杂度本身就是 $O(N_r N P)$（线性阶），与逐径波束 + 撤移位 + 合并**同阶**，且通道硬化区条件数变小、CG 步数很少，同机难达 $\ge 10\times$ 实测加速。大阵列下角域逐波束多普勒补偿与合并也已有先例（如 Guo–Zhang–Wang–Gao, *IEEE TWC* 2019，仅核题名与常识，未读全文）。

---

### 草稿 11：超前缀（回波时延大于前缀）双块均衡的结构化快解
- **判定**：**部分成立**（算力账丢弃结论成立，但探针漏算了「逐符号后验方差」与「窗外能量回收」）
- **证据与核查**：
  - 核对 [runs.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/runs.md#L645) 与 [l_probe_r8_overprefix_cg.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/probes/l_probe_r8_overprefix_cg.py#L1-L45)。
  - **成立部分**：在时域非循环线性卷积下，系统矩阵 $H$ 与上一块拖尾阵 $T$ 每行至多 $P$ 个非零元；即便把脚本第 40 行丢弃的 $-0.39$ dB 窗外拖尾（落在下一块 $y_{k+1}$ 内）并入做双块联合稀疏模型，矩阵仍保持每行 $P$ 非零元，稀疏乘法 + CG 仍是 $O(N P \cdot I_{\text{CG}})$ 线性阶，相对稠密求逆同解快 156×，算力账没有降阶空间。上一块译出后扣 IBI 属于 RISIC（Kim–Stüber 1998）及多篇短前缀迭代对消的既有机制。
  - **探针边界瑕疵（不至于翻案，但须标清）**：
    1. 探针第 35–38 行只解了**单右端项均值方程**（且隐含均匀先验方差）。超前缀非循环矩阵不再移不变（块边界符号能量缺失），若 turbo 均衡需要精确的**逐符号后验方差**（$N$ 个对角元），朴素 CG 需要跑 $N$ 次而反慢于稠密；需依赖 Krylov 标量方差近似（Dietl–Utschick 2007；Dumard–Zemen 2008）或仅对边界 $l_{\max} - L_{\text{cp}}$ 个符号做修正。
    2. 探针第 34 行假设上一块完美译出对消，未测错误传播（不过那属于检测/译码耦合问题，不是矩阵求逆算力问题）。

---

### 草稿 12：闭环按轮由窄到宽定阶 / 留一式信道重估
- **判定**：**丢弃成立**
- **证据与核查**：
  - 核对 [runs.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/runs.md#L646)。
  - **文献核实（读摘要与公开简介，未读全文）**：Y. Liu, Y. L. Guan, and D. González G., *"Near-Optimal BEM OTFS Receiver With Low Pilot Overhead for High-Mobility Communications,"* *IEEE TCOM*, vol. 70, no. 5, pp. 3392–3406, May 2022，及同组 *"Turbo BEM OTFS Receiver With Optimized Superimposed Pilot Power,"* *IEEE TCOM*, vol. 72, no. 1, pp. 601–617, Jan. 2023，已明确在双色散迭代接收机里使用「初始低阶 GCE-BEM 粗估 → 迭代阶段切换高阶 GCE-BEM 精修」策略。因此按轮由窄到宽定阶在文献上已属既有做法。
  - **机理核实**：叠加导频闭环的收敛门限由 EXIT 图起始端（$I_A \approx 0$ 纯导频第 0 轮）决定；一旦采用带特征值先验的 LMMSE，固定基的倒挂已缩至 $0.0\text{–}0.4$ dB（$< 0.5$ dB 门槛），后期再放宽阶数无法拉低门限（实测 0.00–0.05 dB）。留一式重估为负（$-0.05$ 至 $-0.25$ dB）同样符合统计直觉：单符号对全帧 $P D \ll N$ 个信道系数的杠杆仅 $O(PD/N)$，排除单符号几乎不减自反馈，只略增估计方差。

---

### 草稿 13：发射端不知道多普勒扩展时啁啾率 $c_1$ 怎么取
- **判定**：**部分成立**（在项目自身的「窄带离散 + 叠加导频 + 时域处理」设定下丢弃成立；但原文「把 $2 N c_1$ 取到上限不花任何开销」作为一般结论不成立）
- **证据与核查**：
  - 核对 [runs.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/runs.md#L654) 与三处缓存全文证据：
    1. **宽带时间伸缩反例**：[runs.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/runs.md#L634) 已核实 Li 等（arXiv:2507.03537，式 (34), (45), (46)）——在宽带多普勒伸缩因子 $a$ 下，DAFT 域展宽正比于 $c_1 N a = \frac{1}{2} K a$；把 $K = 2 N c_1$ 拉满到上限会按 $K$ 倍放大伸缩模糊，直接撞上 $a N < 1/4$ 的 DAFT 域混叠墙（仅当接收机连导频捕获也完全在时域做、彻底弃用 DAFT 域时才无关）。
    2. **连续时间带限脉冲成形约束**：Mirabella et al.（*IEEE JSAC* 2026, arXiv:2602.20909v2，读缓存全文 §III-E 式 (56)–(57) & Remark 2）证明，严格带限 RRC 脉冲下要求 $c_1 \le \sqrt{N_u}/(\sqrt{6}(N-2))$，远小于离散上限 $1/(2(l_{\max}+1))$，过大 $c_1$ 破坏多载波结构并恶化 CRB。
    3. **主流嵌入导频（EP-AFDM）开销非零**：Bemani et al.（*IEEE TWC* 2023）与 Wang et al.（arXiv:2610.09970v1，读缓存全文 §II-C 式 (10)）中保护带宽度正比于 $2 N c_1 l_{\max}$，不知多普勒扩展时保守取大 $c_1$ 会直接付大块保护带频效税；而 Cao & Shao（Agile-AFDM, arXiv:2512.14424v1，读缓存全文 §I-B）的动态 $c_1$ 又假设发射端已知实时 CSI。
  - **为何维持丢弃而非判错杀**：在无反向反馈的开环发射端，发射机没有观测数据，不可能凭空推断信道多普勒扩展；有反向反馈时只需回传一个标量 $\hat{k}_{\max}$（几比特信令），不构成深算法题。因此结论仍可丢弃，但须把理由收紧到「窄带离散 + 叠加导频 + 时域处理」，删去「取到上限不花任何开销」的泛化断言。

---

### 草稿 14 + 16：接收机不知道多普勒扩展时每抽头基数与先验怎么定
- **判定**：**可能错杀**
- **证据与逐项核查 (a)(b)(c)**：
  - **(a) Zemen–Molisch（*IEEE TVT* 2012, vol. 61, no. 9, pp. 4042–4056, doi:10.1109/TVT.2012.2211053）核查**（注明：**未读到全文 PDF**，仅查核作者主页 thomaszemen.org、ResearchGate 摘要与同组后续论文摘要）：
    - **已确认**：该文面向非平稳车联网（802.11p）双色散信道，预定义一组局部 delay–Doppler 支撑假设（对应不同广义 DPSS / Slepian 降秩子空间），每帧**按观测数据做假设检验（hypothesis test）**动态挑选子空间；其选择准则为**最小化信道估计均方误差（MSE）的概率界**，并且**显式需要噪声方差 $\sigma_z^2$**（既用于 Wiener 滤波正则化，也用于假设检验中权衡截断偏差与噪声方差）。
    - **未确认**：因未读全文，无法核实其具体检验统计量是否等于高斯边际对数似然（`logev`），也无法确认其是否在未知/稀疏延迟抽头上按所有抽头合并求边际似然。因此，仅凭题名把 `ZM` 归为 Zemen–Molisch 2012 的「原样直套」**论据不充分**（尽管「从预定义 DPSS 带宽库按数据逐帧选子空间」的高层思想确有该文及 Hofer–Xu–Zemen VTC 2015 为先例）。
  - **(b) 叠加导频 / 数据辅助 / 双色散 turbo 接收机文献核查**：
    - 专用导频 + 迭代接收机已有同组 Zemen–Bernadó–Czink–Molisch（*IEEE TVT* 2012, *"Iterative Time-Variant Channel Estimation for 802.11p Using Generalized Discrete Prolate Spheroidal Sequences"*，仅读摘要/概述）将 2D GDPS 嵌入数据辅助迭代；叠加导频 turbo 接收机有 Liu–Guan–González（*IEEE TCOM* 2022/2023，仅读摘要），但用 GCE-BEM 且仍依赖已知最大多普勒；共享多普勒支撑的模型选择有 Yang–Shao–Hou–Ma（arXiv:2605.00049v2，**读了缓存全文** §III-B–C），利用「活跃延迟共享同一多普勒集合」的笛卡尔积结构加 BIC 选支撑维数，但仅做**在网格整多普勒 + 纯导频 + 无迭代译码**。
    - 在缓存 95 篇与 2010–2026 检索中，**未查到**在「叠加导频 + 编码双色散 turbo 接收机第 0 轮（强数据自干扰，导频 SINR $\approx -6$ dB）+ 连续带限 DPSS 子空间」下做跨抽头合并边际似然选带宽的已发表工作（不排除存在未检索到的会议短文）。
  - **(c) 探针 [l_probe_r8_unknown_spread.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/probes/l_probe_r8_unknown_spread.py#L1-L79) 偷用四项强先验，`ZMs` 臂并不成立**：
    1. **偷用精确支撑与精确径数 $P$**（第 53、60、62 行）：`Phc = phi(reg, taps, Bc)` 直接传入真实活跃延迟 `taps`，且先验方差硬除以真实 `P`。真实接收机需在全时延窗 $L=25$（或项目 $L=100$）上同时处理大量空抽头，自由度膨胀 4–15 倍后，第 0 轮 $-6$ dB 下的 `logev` 能否选准完全未测。
    2. **`ZMs` 臂并未去掉「每抽头功率先验」，实现不成立**（第 28、61–62 行）：信道生成器（第 28 行）把全部 $P$ 条径做成**完全等功率**且总能量精确归一为 1；而 `ZMs`（第 61–62 行）写的 `pv = np.tile(lc / lc.sum() / P, P) * sc`（`sc ∈ {0.25, 0.5, 1.0, 2.0, 4.0}`）依然硬编码了**全径等功率（$1/P$）+ 全径同带宽 + 精确 DPSS 特征值谱比 `lc/lc.sum()`**，仅搜索一个全帧全局标量 `sc`（且真值 `1.0` 正好在网格正中）。一旦换成真实指数衰减 PDP（强弱径差 10–20 dB）或各径多普勒扩展不均匀（如静态直达径 + 宽多普勒海面散射径），`ZMs` 的协方差模型直接失配。
    3. **偷用精确噪声与数据干扰方差 `nv`**（第 51 行）：第 0 轮直接给真值 `nv = S2 + (1 - RHO)`，理想判决给真值 `S2`。高斯边际似然 `logev`（第 42–43 行）对 `nv` 高度敏感，`nv` 偏估会直接把带宽选偏。
    4. **真值 `NU` 精确命中字典格点 + 未测闭环门限**（第 17、72 行）：真值 `NU = 1, 2` 恰好是 `LIB` 的精确格点，且未测真实 EXIT/LDPC 闭环。
- **哪一步不成立 & 要补的便宜检验**：
  - 不成立处：用「已知支撑 + 等功率 PDP + 已知 `nv` + 命中格点」的理想化 `ZM/ZMs` 读数（$\le 0.11$ dB）去宣称「现有无先验方法已经贴着 `ORA`」。
  - **便宜检验（本机单线程 $< 30$ 秒）**：在 `l_probe_r8_unknown_spread.py` 上同时松开三项先验——(1) **全延迟窗 $L=25$ 未知支撑**（联合估活跃抽头与带宽，或先粗糙支撑检测再选带宽）；(2) **指数 PDP（15 dB 动态范围）**外加一组**异质多普勒（1 条静态直达径 + 5 条 Jakes 径）**；(3) **`nv` 未知**（从数据剖面似然或 EM 联合估 `nv`）且真值 `NU` 取离网值（如 `1.3`, `2.4`）。重测 `ZM`/`ZMs`（及逐抽头功率+共享带宽 SBL）在第 0 轮 NMSE 与 EXIT 闭环门限上离 `ORA` 的差距，以及相对 ARD/BIC 的优势；只有在这组无偷先验设定下现成方法仍 $\le 0.5$ dB，才算坐实丢弃。

---

### 草稿 15：编码工作点的低比特量化 / 维纳相位噪声闭环
- **判定**：**部分成立**（**低比特量化半条丢弃成立**；**维纳相位噪声半条可能错杀**，原丢弃理由不成立）
- **证据与核查**：
  1. **低比特量化（2–3 比特，3.45–5 dB 编码工作点）——丢弃成立**：
     - 核对 [runs.md](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/runs.md#L654-L655) 与 [l_probe_r8_lowbit_adc.py](file:///Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/probes/l_probe_r8_lowbit_adc.py#L1-L44)。
     - **核心核查（「序列级处理能否明显超过逐实维独立、高斯输入互信息极限」）**：**在奈奎斯特采样 + 逐样点无记忆标量量化下，信息论上绝对不能。**
       - 证明：逐样点量化信道无记忆，$P(Y^N | X^N) = \prod_{n=1}^N P(Y_n | X_n)$，由数据处理不等式与链式法则，
         $$I(S^N; Y^N) \le I(X^N; Y^N) = \sum_{n=1}^N \big[h(Y_n | Y^{n-1}) - h(Y_n | X_n)\big] \le \sum_{n=1}^N I(X_n; Y_n).$$
       - 扩展波形（AFDM/OFDM）经 IDAFT/IDFT 与多径叠加后，时域样点 $X_n$ 高度服从复高斯分布（Tasin & Rahman 2026 缓存全文 Appendix A 实测 AFDM 四阶矩 1.999 vs 理论高斯 2.000）。因此，任何序列级非线性接收机（MLSD、GAMP、GTurbo、神经网络）都**无法突破**探针算出的单维高斯互信息极限（2-bit 在 3.45/5 dB 至少亏 **+1.90 / +2.55 dB**，物理上不可能回到无损伤 $\le 0.5$ dB；3-bit 下线性 Bussgang 已仅亏 **+0.53 / +0.70 dB**，离极限只差 0.02–0.04 dB，既没有 $\ge 1$ dB 的现有亏损，也没有 $\ge 1$ dB 非线性增益）。
       - 仅有的两个理论例外都会改变物理前提：(i) **高于奈奎斯特的过采样**（Krone–Fettweis 2012 等，以时间维换幅度维，需改硬件采样率）；(ii) **非高斯离散输入分布**（Singh–Dabeer–Madhow, *IEEE TCOM* 2009，经典结论：量化 AWGN 容量达到输入至多 $2^b+1$ 离散点），但扩展波形本身把时域高斯化了，无法享用。
       - 旁证：Yang–Sui–Liu–Musavian（arXiv:2602.07001v1，读缓存全文 §V Fig. 6）的 5-bit 亏 5 dB / 4-bit 亏 17 dB / 3-bit 平台确实发生在 **20–50 dB 高 SNR 未编码**区；Wang–Shih–Wen–Jin（*IEEE TCOM* 2019，仅读摘要）的 GTurbo 收益亦主要在高阶调制（如 2-bit 16-QAM）与联合稀疏估计，而非 3.5–5 dB QPSK。
  2. **维纳相位噪声闭环——可能错杀（原「时域对角可原样直套 OFDM」的理由不成立）**：
     - **哪一步不成立**：
       1. **与未知双色散多普勒的强耦合破坏 OFDM 直套**：经典 OFDM 时域联合相噪–检测迭代（Petrovic 2007；Lin–Lim *TSP* 2007）假设块内信道时不变，把全部块内时变归因于相噪。一旦信道本身是未知双色散多径，**宽带非平滑的维纳相噪**与**低通平滑的多普勒扩展**乘性耦合，既产生公共多普勒与相噪低频漂移的可辨识性混淆，又破坏离网分数多普勒的 Dirichlet 核结构。缓存两篇 2026 全文直接给出反例：
          - **McWade & Farhang**（arXiv:2605.14720v1，读缓存全文 §I p. 1–2 & §V Fig. 12–13, 16–17）：500 km/h TDL-C 下，现有 BEM + CPE 处理在编码 4-QAM 亏 **4 dB**、编码 16-QAM 亏 **6 dB 且出 $10^{-3}$ 误码平台**。
          - **Xu et al.**（arXiv:2604.17858v1，读缓存全文 §I–II 式 (5)(7) & §IV Fig. 5–6）：AFDM 离网估计器直套独立相噪估计（`OffGrid-SBL/GridFission-SBL (With PN Est.)`）在 **5–10 dB 即出现严重 NMSE 平台**。
       2. **发射端相噪（Tx PN）不是时域对角公因子**：若发射端存在维纳相噪 $\phi_T[n]$，多径接收为 $y_n = e^{j\phi_R[n]}\sum_p h_p e^{j2\pi\nu_p n/N} e^{j\phi_T[n-l_p]} s[n-l_p] + w_n$，不同时延路径携带不同时延的 $\phi_T[n-l_p]$，与多径卷积耦合，OFDM 接收端单对角相噪跟踪直接失效。
     - **要补的便宜检验**：先定物理场景——**若是水声低载频（数 kHz–几十 kHz）**，晶振相对相噪线宽极小，应核对典型水声晶振 $\sigma_{\text{PN}}^2 = 2\pi\Delta f T_s$ 是否造成 $<0.1$ dB 退化（若是，则按「水声无此痛点」丢弃，而非按「OFDM 可直套」丢弃）；**若是 mmWave / sub-THz / LEO 高载频双色散场景**（$\beta_{\text{PN}} \sim 1\text{–}10$ kHz），用 $N=256$ 编码双色散玩具（6–8 径分数多普勒，QPSK/16-QAM）对比「OFDM 式解耦时域相噪跟踪 + 双色散重估」vs「联合相噪–双色散迭代」vs「无相噪基线」（含 Rx-only 与 Tx+Rx 两臂），核查解耦直套是否真崩（亏 $\ge 1$ dB 或出平台）。

---

### (A) 去先验账的最强反例
- **严格核查结论**：在 2018–2026 双色散编码/迭代接收机公开文献中，**查不到一个完全满足全部条件的现成强反例**（即同时满足：$\ge 2$ 个独立课题组假设已知 + **现有最强无先验方法在已发表图表里实测仍亏 $\ge 1$ dB**）。
- **逐项排除与最接近的候选**：
  1. **未知路径数 / 稀疏度（不构成反例）**：Wang–Pan–Ren–Li–Wang（SEU, arXiv:2610.09970v1，读缓存全文 §VII Fig. 2–3）与 Yang–Shao–Hou–Ma（UMacau/HKU, arXiv:2605.00049v2，读缓存全文 §IV Fig. 1）均已给出纯导频下的无先验方案，且二者各自已做到贴近或反超「给了真阶数/真支撑的对手」（前者 NOMP-CFAR/SAGE-BIC 在高 SNR 也逼近；后者仅未编码且在网格）。
  2. **未知噪声方差 $\sigma_w^2$（查不到 $\ge 1$ dB 反例）**：虽有 $\ge 2$ 组在迭代检测里假设已知（如 Li–Yuan–Qiu *TCOM* 2024；Huang–Qiu OAMP-JED；Mishra SP-OTFS），但已有编码迭代接收机将其作为超参联合估计且无明显亏损（如 Wan–Zhu–Cheng–Xu, JCCD-VALSE, arXiv:2107.07101v1 读缓存全文 §I & §III；Li–Han–Ge, *Remote Sensing* 2024 读缓存全文）；未查到「联合估计标量噪声方差仍亏 $\ge 1$ dB」的公开图表。
  3. **最接近的候选（属「缺对比图表」而非「已证亏 $\ge 1$ dB」）：未知最大多普勒扩展 $f_{\max}$ 与信道时间相关谱核（如 Jakes 核）**。
     - **$\ge 2$ 独立组假设已知（铁证）**：(i) Liu–Guan–González（*IEEE TCOM* 2022/2023，读摘要）的 BEM-OTFS turbo 接收机按已知 $f_{\max}$/速度定基与阶数；(ii) McWade–Farhang（arXiv:2605.14720v1，读缓存全文 §IV 式 (55)–(56)）显式代入精确 $f_D$ 算 Jakes 自相关 $J_0(2\pi f_D T_s |m-n|)$；(iii) FTN 叠加导频双色散 turbo 接收机（本地缓存 `ftn-sp-turbo.txt` 读全文 §III p. 314–316）显式写明 `f_d, N, \tau, T` 接收端已知。
     - **为何仍不能算已证反例**：公开文献几乎没有在编码迭代闭环里画「无 $f_{\max}$ 先验的最强方法 vs 已知 $f_{\max}$」的对比图；且草稿 16 提示，若采用跨抽头共享带宽的子空间选择，无先验代价能否超过 1 dB 必须先跑完上面草稿 14+16 要求的「去偷先验」检验才能定论，目前不能硬推。

---

### (B) 模型化硬件损伤账的最强反例
三类（功放 / 量化 / 相位噪声）里，**最强反例是「维纳/PLL 相位噪声与双色散信道的耦合估计及编码检测」**（适用于高载频 mmWave / sub-THz / LEO 双色散场景，不适用于低载频水声）：

1. **相位噪声 + 双色散耦合（最强反例，满足 $\ge 2$ 个独立组 + 强耦合 + 现有方法亏 $\ge 1$ dB 或出平台 + 信息论上可回收至 $\le 0.5$ dB）**：
   - **组 1（Trinity College Dublin）**：**S. McWade & A. Farhang**, *"Joint Phase Noise and Channel Estimation for OTFS,"* arXiv:2605.14720v1 (2026)（**读缓存全文**）。
     - **位置与数字**：§V **Fig. 12–13**（未编码 4-QAM，500 km/h TDL-C）、**Fig. 16**（1/2 码率编码 4-QAM，$\beta_{\text{PN}}=10$ kHz）、**Fig. 17**（1/2 码率编码 16-QAM，$\beta_{\text{PN}}=5$ kHz）。
     - **现有最强处理与亏损**：此前 OTFS 结合双色散信道估计的最强基线为 BEM/样条插值 + CPE 补偿；在 Fig. 12–13 中 BEM 亏 **2–8 dB**（并在 $4\times 10^{-5}$ 出平台），在编码 Fig. 16 亏 **4 dB**，在编码 16-QAM Fig. 17 亏 **6 dB 且在 BER $10^{-3}$ 出平台**。且该文自身的 Proposed 方案只是**单次纯导频线性 Wiener 滤波**（无译码反馈迭代、假设已知 $f_D$ 与 $\beta_{\text{PN}}$），Fig. 14 表明在强相噪下其自身也陡升退化（全文未画无相噪参考线）。
   - **组 2（HUST + Univ. of Essex）**：**Y. Xu, H. Zhang, L. Xiao, G. Liu, & Z. Liu**, *"Joint Phase Noise and Off-Grid Channel Estimation for AFDM Systems via Sparse Bayesian Learning,"* arXiv:2604.17858v1 (2026)（**读缓存全文**）。
     - **位置与数字**：§IV **Fig. 5**（NMSE）与 **Fig. 6**（BER），以及 **Fig. 3**（降秩子空间截断平台）。
     - **现有最强处理与亏损**：现有离网双色散估计器加独立相噪估计（`OffGrid-SBL (With PN Est.)`、`GridFission-SBL (With PN Est.)`）因未解耦相噪与分数多普勒的双线性相互作用，在 **5–10 dB 即出现严重 NMSE 平台**（与联合 EM 差 $> 10$ dB）；该文 Proposed 仅在 $N=64, P=3$、5 个 +30 dB 强导频、未编码、纯接收端相噪下验证，无编码数据辅助闭环与 Tx PN。
   - **组 3（BUET，PA + 相噪双损伤耦合）**：**M. Tasin & S. S. Rahman**, *"Gain Before Tracking: Compensating Power-Amplifier Nonlinearity and Phase Noise in AFDM Uplinks,"* arXiv:2610.33672v1 (2026)（**读缓存全文**）。
     - **位置与数字**：§V **Fig. 3** 与 **Table VII**（p. 8，编码 16-QAM，6 径分数多普勒 AFDM，Rapp PA + 维纳相噪）。
     - **现有最强处理与亏损**：其最强接收机（标量 Bussgang 增益 + 判决导向 CPE 跟踪，无迭代非线性/ICI 对消）在 IBO = 3 dB、码率 3/4 下 10% BLER 需 **21.3 dB**（Preamble 校准 20.1 dB），相对近线性 IBO = 8 dB（17.1 / 16.4 dB）**仍亏 3.7–4.2 dB**；在符合 5G NR EVM 规范的 IBO = 5 dB 下仍亏 **1.2–1.3 dB**（18.3 vs 17.1 dB）。
   - **与量化的本质区别**：相位噪声是单位模相移（不损香农容量上界），只要联合估计/迭代跟踪够准，理论上可回到无相噪 $\le 0.5$ dB 内。

2. **功放非线性与低比特量化为何不是同样干净的反例**：
   - **功放非线性**：Tasin & Rahman（2026 Table VII）与 Sui et al.（*IEEE TCOM* 2026, arXiv:2601.00502v2 读缓存全文 §VI **Fig. 7**，$\nu_{\text{clip}}=1,2$ dB 出现 BER 平台）虽有大亏损/平台，但两篇都**没有接上经典的迭代削峰/功放失真重建对消**（Tellado / Dinis 族）；装上之后在 PA 与双色散耦合下是否还剩 $\ge 1$ dB，目前查不到现成已发表图表。
   - **低比特量化**：Yang–Sui–Liu–Musavian（arXiv:2602.07001v1 读缓存全文 §V **Fig. 6**：OTFS-IPAC 5-bit 亏 5 dB、4-bit 亏 17 dB、3-bit 出平台）与 Sui et al.（*TCOM* 2026 读缓存全文 §VI **Fig. 5**：3–4 bit DAC 出平台）均是**未编码高 SNR + 线性 AQNM**；Mehrotra et al.（*IEEE TCOM* vol. 73, no. 6, pp. 3971–3987, June 2025，仅读摘要）已做了有限比特 MIMO-OTFS/OTSM 的 VBL 信道估计 + 量化感知 MMSE（未读全文，无法核对其残余 dB 差）。更重要的是，如草稿 15 所示，在低 SNR 编码 QPSK 下 2-bit 的 1.9–2.6 dB 损失是香农极限，无法回到无损伤 $\le 0.5$ dB 内。

---

### (C) 事实核查：已实现的 Krylov / 共轭梯度型 turbo 均衡或数据辅助信道估计
- **有没有已实现（FPGA / DSP / 实时样机）？**
  - **未查到**在 FPGA / DSP / ASIC 或实时水声样机上把 Krylov / 共轭梯度（Dietl–Utschick *TSP* 2007；Dumard–Zemen *TSP* 2008）用于 **turbo 均衡** 或 **数据辅助信道估计** 的已发表实现（仅基于本次公开检索与缓存核查，不排除存在未检索到的学位论文或非公开工程样机）。
  - **必须区分的近邻实现**：**Massive MIMO 单次（非迭代）线性检测**已有成熟的 FPGA / ASIC CG 实现——最著名的是 **B. Yin, M. Wu, J. R. Cavallaro, & C. Studer**, *"Conjugate Gradient-based Soft-Output Detection and Precoding in Massive MIMO Systems,"* *IEEE GLOBECOM* 2014 及后续 FPGA/VLSI 架构（仅读摘要/综述）。但那针对的是 $128 \times 8$ 通道硬化（低条件数、3–5 步即收敛）的空间单次检测，而非长时延双色散 ISI 的 turbo 均衡或数据辅助估计。
  - **已查到的水声 / 迭代接收机硬件实现全部采用非 Krylov 方案**：
    - **Li & Zheng**（*Global Oceans* 2020，读缓存全文 `li-zheng-fpga-tdte.txt` §II–IV, Table I–II）：Zynq UltraScale+ FPGA，151 抽头时域 turbo 均衡，用块平均方差 + 行并行 **$LDL^H$（$U^H D U$）直接求逆**，矩阵求逆占 184,914 / 199,948 = **92.5%** 时钟周期（2 轮 turbo）。
    - **Peng, Salvo Rossi, Dong, & Kansanen**（*EUSIPCO* 2016，读缓存全文 `peng-eusipco16-dsp-ofdm.txt` §IV–V, Table II）：TMS320C6678 双核 DSP，水声迭代 OFDM，均衡器直接用 **Schniter 带状 MMSE（半宽 2，仅占 5.25 ms = 5.2%）**，真正占 **87%（87.7 ms）** 的是 **180 步 OMP + 增量块 Cholesky** 稀疏信道估计（已用 FFT 算相关与列范数）。
    - **Kongsberg / FOI 样机**（EU UAN D3.3, 2011，读缓存全文 `uan-deliv33-uwa-turbo.txt` §2.5 & §2.5.2）：低功耗 DSP，单载波 turbo 均衡，采用逐符号 $O(N^2)$ 矩阵求逆更新，被迫把均衡器截短到 **15 抽头、3 轮迭代**。
    - **Studer, Fateh, & Seethaler**（*IEEE JSSC* 2011，读缓存全文 `studer-mmse-pic-jssc11.txt` §II–III）：4×4 MIMO-OFDM MMSE-PIC ASIC，用 **LU 分解 + 自定义 Newton–Raphson 倒数器**。
    - **Huang, Yeh, & Pan**（arXiv:2606.30565v1, 2026，读缓存全文 `otfs-ncc-gpu-sdr.txt` §IV）：实时 GPU + USRP SDR 的 OTFS 样机，直接改用**免求逆的 GA-MPA（高斯近似消息传递）**。
- **文献给出（及体系结构决定的）不用 Krylov / CG 的四条主要原因**：
  1. **需要逐符号后验方差 / SINR 刻度（turbo LLR 的结构硬伤）**：如 Studer et al.（*JSSC* 2011 缓存全文 §II-C3 & §III-B 式 (6)(9)(13)）所指，精确 SISO MMSE-PIC 需要每个符号的后验增益 $\mu_i = \mathbf{w}_i^H \mathbf{h}_i$ 来算外信息 LLR 缩放 $\rho_i = \mu_i/(1 - E_i \mu_i)$。CG 跑一次只能解出一个右端项的均值，**拿不到矩阵逆的 $N$ 个对角元**；若不想跑 $N$ 次 CG，就必须做全块平均方差或近似 SINR（如 Yin 等在 Massive MIMO 里的近似或 Dietl–Utschick / Dumard–Zemen 的降秩近似）。
  2. **时变信道下逐符号更新 vs 固定延迟流水线**：UAN D3.3（缓存全文 §2.5, p. 11–12）明确指出，长帧（1.1 s）水声信道在块内时变，需逐符号更新自适应均衡器系数，直接卡死在 $O(N^2)$ 更新上；Studer et al.（*JSSC* 2011 缓存全文 §II-B, p. 3）亦强调硬件接收机要求**恒定吞吐量与确定性延迟**，而 CG 迭代步数随信道条件数波动，且每步的全局内积归约与标量除法存在强循环依赖（loop-carried dependency），硬件流水化不如定长 $LDL^H$ / 带状分解直接。
  3. **定点数值退化**：FPGA-CG 硬件实现文献普遍指出（仅读综述/摘要），长时延高条件数 ISI 信道下，定点 CG 很快丢失搜索方向的 $A$-共轭正交性、收敛变慢甚至发散，通常需要较宽字长/浮点或额外预条件器，抵消硬件面积优势。
  4. **确实存在「算法层与水声硬件层脱节」+「瓶颈不在求逆本身」**：在 **Peng et al. (2016)** 里，87% 耗时来自 **OMP 贪婪支撑搜索**而非线性均衡求逆，换 CG 救不了；而在 **Li & Zheng (2020)** 里，他们已经做了全块平均方差（全块只需解一次 $151 \times 151$ 线性系统 $\mathbf{A}\mathbf{g} = \mathbf{s}$ 得到公共滤波器 $\mathbf{g}$），却仍照搬 Xilinx HLS 的全矩阵求逆流算出了完整的 $\mathbf{A}^{-1}$——原文根本未讨论 Krylov/CG 或单右端项求解，说明**工程上沿用现成 HLS 矩阵求逆核的惯性**确实是重要原因之一。
