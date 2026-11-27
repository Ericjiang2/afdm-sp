## 1. `(1a)` 文献查新

**建议 7 张草图进入 15 分钟探针。** 我核查了公开论文、逐条审查了 30 张草图，并计算了一个否决固定秩近似的反例。Stage A 数字作为题给观测使用。草图中的速率、误符率、检出率和提速仍是预测，`SELECT` 表示值得先做可快速证伪的实验。

| 缺口 | 已核查的近邻与占用边界 |
|---|---|
| **G2 · 少射频链混合预编码** | **`PARTIALLY_OCCUPIED`**。Rang Liu、Ming Li、A. Lee Swindlehurst、Norman Franchi、Robert Schober，*Multiuser MIMO-AFDM Beamforming for ISAC in Doubly Dispersive Channels*，arXiv:2607.05119，2026，已做全数字多用户下行通感波束。Jun Zhu 等，*Preconditioned Conjugate Gradient for MIMO-AFDM System*，arXiv:2506.22465，2025，已用信道稀疏化和预条件共轭梯度加速 AFDM 多用户通信预编码。Vincent Savaux、Xuan Chen，*Spatial Precoding in Frequency Domain for Multi-User MIMO Affine Frequency Division Multiplexing*，EUSIPCO 2024，已做频域空域预编码。混合源域近邻是 Ahmet M. Elbir、Abdulkadir Celik、Ahmed M. Eltawil 的 *Hybrid Beamforming for Integrated Sensing and Communications With Low Resolution DACs*，IEEE WCL，arXiv:2411.02827 首发于 2024，以及 Zhe Ting Liao 等的 *Design of Joint Transmit Beamforming for Multi-User MIMO-OFDM Integrated Sensing and Communication Systems*，IEEE TWC 2025。未找到同一少射频链硬件下，按仿射路径偏移联合设计模拟阵和跨格求解器的同机制工作。[Liu](https://arxiv.org/html/2607.05119v1) · [Zhu](https://arxiv.org/html/2506.22465v1) · [Savaux–Chen](https://eurasip.org/Proceedings/Eusipco/Eusipco2024/pdfs/0002112.pdf) · [Elbir](https://arxiv.org/abs/2411.02827) · [Liao](https://scholar.nycu.edu.tw/en/publications/design-of-joint-transmit-beamforming-for-multi-user-mimo-ofdm-int/) |
| **G3 · 1-bit 数模转换器** | **`PARTIALLY_OCCUPIED`**。Zeping Sui 等，*MIMO-AFDM Outperforms MIMO-OFDM in the Face of Hardware Impairments*，IEEE TCOM 2026，已做 AFDM 低分辨率数模转换及 Bussgang 缩放分析。Yiran Wang 等，*Interference Exploitation in ISAC Systems: Finite-Alphabet Precoding with Low Resolution DACs and PSs*，IEEE TWC 2025 在线发表，已做相长干扰与有限字母表联合优化。Yifan Sun、Rang Liu、Ming Li、Qian Liu，*One-Bit DAC/ADC Transceiver Designs for Efficient MIMO-ISAC Systems*，IEEE TCOM 2026，已联合设计 1-bit 通感收发。Murat Babek Salman、Özlem Tuğfe Demir、Emil Björnson，*Performance Analysis for ISAC Systems with 1-bit DACs*，arXiv:2607.23216，2026，已用 SQUID 分裂做非线性通感量化。AFDM 接收端双域期望传播也已有 Qin Yi 等，arXiv:2603.29218，2026。未找到固定 AFDM 波形下，按二次啁啾陪集组织合法比特群翻转并联合优化跨块弱目标旁瓣的工作。[Sui](https://repository.essex.ac.uk/43341/) · [Wang](https://discovery.ucl.ac.uk/id/eprint/10212383/) · [Sun](https://doi.org/10.1109/TCOMM.2026.3663304) · [Salman](https://arxiv.org/abs/2607.23216) · [Yi](https://arxiv.org/abs/2603.29218) |
| **G4 · 饱和功放** | **`PARTIALLY_OCCUPIED`**。Sui 等已分析软包络限幅器。Eya Gourar 等，*Impact of PA Nonlinearities on AFDM Sensing*，arXiv:2609.14030，2026，分析非线性放大后的匹配滤波。其 *Low-Complexity Sensing-Aware PAPR Reduction for AFDM-based ISAC Systems*，arXiv:2607.01064，2026，才是预留啁啾子载波联合降峰与旁瓣的论文。Lingsheng Meng、Yong Liang Guan、Zilong Liu、Yirui Luo、Pingzhi Fan，*Enabling Flexible AFDM-ISAC Design: When Ambiguity Shaping Meets PAPR Control*，arXiv:2604.22198v2，2026，已联合优化模糊旁瓣和峰均功率比。Shiqi Cui 等，*Adaptive \(c_2\)-Perturbed AFDM Waveform Design for Integrated Sensing and Communication*，arXiv:2606.04698v2，2026，已用逐子载波相位扰动做同类整形。剩余边界是固定波形、全载荷、多用户 16-QAM 下，在同一功放可达域里同时保住判决裕度与跨块弱目标检出。[Sui 全文](https://repository.essex.ac.uk/43341/1/MIMO_AFDM_Outperforms_MIMO_OFDM_in_the_Face_of_Hardware_Impairments.pdf) · [Gourar 非线性分析](https://arxiv.org/abs/2609.14030) · [Gourar 预留子载波](https://arxiv.org/abs/2607.01064) · [Meng](https://arxiv.org/abs/2604.22198) · [Cui](https://arxiv.org/abs/2606.04698) |
| **G6 · 下行波束求解加速** | **`PARTIALLY_OCCUPIED`**。Liu 等已给出原始加权最小均方误差与逐轮紧下界法（WMMSE-MM）。Zhu 等已做 AFDM 稀疏预编码加速。Ruiyuan Mao 等，*Joint Chirp Parameter Selection and Low-Complexity MMSE Receiver Design for AFDM Systems*，arXiv:2607.20227，2026，已做逐径稀疏化和循环带状 Cholesky 分解，作用于接收端。未找到保留 Liu 原预编码变量、全块速率和照射约束的两段结构化加速。**Liu 的发射权重逐格分块，信道、协方差和接收处理保留完整跨格耦合。** 这也意味着发射更新只需要大矩阵的逐格主对角块，公平实现应利用这一点。[Liu §II-C、§IV-B](https://arxiv.org/html/2607.05119v1) · [Zhu](https://arxiv.org/abs/2506.22465) · [Mao](https://arxiv.org/abs/2607.20227) |
| **G7 · 单抽头接收与弱目标消遮蔽** | **`PARTIALLY_OCCUPIED`**。Shuntian Tang、Zesong Fei、Xinyi Wang、Dongkai Zhou、Zhiqiang Wei、Christos Masouros，*A Novel Symbol Level Precoding-Based AFDM Transmission Framework: Offloading Equalization Burden to Transmitter Side*，IEEE TWC 2026，已做免均衡接收、功率球和单纯形对偶二次规划。Tang 等 *Probabilistic Symbol-Level Precoding based Affine Frequency Division Multiplexing Transmission*，arXiv:2609.09644，2026，又覆盖了概率判决设计。前一篇的对偶求解器接收完整估计信道矩阵，`kν=1` 是 Stage A 的比较点，不能当作论文方法的限制。Haoran Yin 等，*Ambiguity Function Analysis of AFDM Signals for Integrated Sensing and Communications*，arXiv:2507.08293，2025，已推导旋转的时延–多普勒结构。Peishi Li 等，*MIMO-OFDM ISAC Waveform Design for Range-Doppler Sidelobe Suppression*，IEEE TWC 2025，已做源域联合旁瓣整形。剩余边界是固定 AFDM 参数下，多用户精确相长约束与因果跨块弱目标消遮蔽的联合求解。[Tang TWC](https://discovery.ucl.ac.uk/id/eprint/10231042/) · [Tang 算法 2](https://arxiv.org/html/2508.12215#S4) · [Tang 概率预编码](https://arxiv.org/abs/2609.09644) · [Yin](https://arxiv.org/abs/2507.08293) · [Li](https://arxiv.org/abs/2406.17218) |

`OCCUPIED` 适用于已经公开的**单项机制**，包括 AFDM 稀疏预条件预编码、免均衡对偶预编码，以及 AFDM 旁瓣与峰均功率比联合优化。本轮检索没有确认任何一张完整草图在同问题、同机制上被占用。

## 2. 30 张草图筛选

表中 `P` 表示 `PARTIALLY_OCCUPIED`。`待证` 表示保留了可单独检验的仿射结构，但性能或复杂度上的必要性仍须实测。设 \(s=2Nc_1\)。**偶数 \(N\) 且 \(s\) 为整数时，标准啁啾周期前缀的边界相位为 1。** 单靠该边界相位不能过红线。分数多普勒仍会在 \(c_1=0\) 时造成跨格耦合。筛选中没有把 \(c_1=0\) 的波形性能当作淘汰条件。

| Sketch ID | `(1a)` / `(1b)` | \(c_1=0\) 非退化 | 数学、算力与 `<80%` 消融 | 判决 |
|---|---|---|---|---|
| G2-S1-1 | P / 阵列加权有差异 | 待证 | 削弱长偏移路径可改善预处理，但也会丢信号功率。两三步收敛缺证。 | **DROP**。同照射门槛下优先保留全部多径的设计。 |
| G2-S1-2 | P / 双轴重排有差异 | 是，需 \(s\) 在模 \(N\) 下可逆 | 取 \(s=3\)、\(N=2^j\) 可重排。双轴带状矩阵只作预处理，完整算子决定精度。固定阵列可能已回收八成。 | **SELECT**。可同时检验全多径增益和双轴求解增益。 |
| G2-S1-3 | P / 空间正交与预抵消近直套 | 否 | 空间分解及全块抵消在 \(c_1=0\) 仍可用。平坦啁啾谱不保证全二维无假峰，固定参考跨块重复有 `h01` 同类风险。 | **DROP**。核心分解触及换符号红线。 |
| G2-S2-1 | P / 碰撞权重有差异，稀疏预条件已有近邻 | 待证 | 碰撞核描述同格重叠，不能替代完整跨格干扰。需显式构造循环预处理，固定阵列消融可能过强。 | **SELECT**。检验碰撞图能否改变模拟阵的有效取舍。 |
| G2-S2-2 | P / 联合选径及重排有差异 | 是，需实测偏移带分离 | 主径带外未截断。两阶展开须检查诱导范数和功率代价，谱半径单独不够。 | **SELECT**。可用 27 种组合快速否决。 |
| G2-S2-3 | P / 同余着色有差异 | 是 | \(N=2^j\) 时模 3 分组在环绕处跨类。周期自相关也无法代理分数多普勒全图。 | **DROP**。边界修正和雷达目标均未闭合，优先双轴重排。 |
| G3-S1-1 | P / 滑窗搜索近通用做法 | 否 | 有限时域记忆在普通前缀下仍在。每时刻 32 个比特的分支生成未计入，弹性相长锥的全局影响也未纳入搜索状态。 | **DROP**。线性成本与 AFDM 专属性均缺依据。 |
| G3-S1-2 | P / 顶点同伦与旁瓣主化已有近邻 | 待证 | 密集拖尾下的快速逆、最终合法顶点和同目标胜过位翻转都未建立。 | **DROP**。离散搜索优先验证有精确恒等式的陪集方案。 |
| G3-S1-3 | P / 误差反馈近直套 | 否 | 瞬时 \(N_t-K\) 维不能保证剩余比特有足够的跨时刻可控性。线性整形器也不能直接控制二次模糊残差。 | **DROP**。两层反馈缺少可实现的控制映射。 |
| G3-S2-1 | P / 同伦和局部主化近直套 | 待证 | 奇次啁啾谐波的论证依赖单分量近似。与 G3-S1-2 同类，仍缺精确离散比较。 | **DROP**。重复押注同一优化结构。 |
| G3-S2-2 | P / AFDM 期望传播已覆盖接收端 | 待证 | 路径输出带分开也会共享输入比特。边缘矩匹配和协方差凹槽未给出联合可行性。 | **DROP**。局部稀疏性不足以推出期望传播收敛或弱目标收益。 |
| G3-S2-3 | P / 陪集群翻转有差异 | 是 | 二次相位线性化成立。普通群翻转仍会影响多个余数组，须用真实残差评分并保持 1-bit 字母表。 | **SELECT**。可直接检验能否跳出单比特局部最优。 |
| G4-S1-1 | P / 圆盘分裂常规，参考生成可重参数化 | 否，按原式 | 总参考斜率为 \(s_q/(2N)\)，式中的 \(c_1\) 抵消。移开主峰也不保证分数多普勒旁瓣降低。 | **DROP**。核心参考机制在 \(c_1=0\) 可照用。 |
| G4-S1-2 | P / 因果跨块核与仿射可行集有差异 | 待证 | 通信仿射集与功放圆盘交集可直接验。连续频带核只有近似低秩，须计跨块核与真实功放映射。 | **SELECT**。Stage A 的通信消峰对感知有实测代价，值得验证联合设计。 |
| G4-S1-3 | P / 原始–对偶与雷达谱分裂近串联 | 否 | DAFT 酉性与路径移位不能推出 Kashin 峰值均摊条件。前缀扩展和补零仍可在普通前缀下执行。 | **DROP**。关键条件缺失。 |
| G4-S2-1 | P / 通用圆盘分裂与二次匹配 | 否，按原式 | 自模糊旁瓣通常是四次目标。二次式需要明确冻结的参考。独立数据也不保证无跨块假峰。 | **DROP**。所写二次目标未对应要压的回波。 |
| G4-S2-2 | P / 消峰与投影近串联 | 否 | 时域带状零空间可在 \(c_1=0\) 同阶计算。二次投影可能破坏已满足的峰值与通信约束。 | **DROP**。仿射结构未给出独立作用。 |
| G4-S2-3 | P / 精确限幅伴随可直接移植 | 否 | 硬限幅边界不可微，饱和区的径向导数为零。限幅与伴随优化在 \(c_1=0\) 仍同阶运行。 | **DROP**。穿过功放求梯度本身是通用做法。 |
| G6-S1-1 | P / 多相分组和逐格路径收缩有差异 | 待证 | 多相重排只作预处理。跨块二次型必须保留每块逆算子，不能直接压成路径级小逆。 | **SELECT**。原论文逐格发射更新提供了精确的第二段加速入口。 |
| G6-S1-2 | P / 路径迭代未建立所称区别 | 否，按所称收缩 | 两条无损路径 \(E_p,E_{p'}\) 满足 \(\|E_p^HE_{p'}\|_2=1\)。移离主对角线不推出谱收缩，感知内近似也是仿射约束。 | **DROP**。快收敛与小矩阵闭解均缺依据。 |
| G6-S1-3 | P / 双尺度有差异 | 待证 | 长偏移不等于粗网格上的低频误差。慢时间低秩也不推出逐块逆可压缩。 | **DROP**。先验证更简单、能逐项对照原式的多相方案。 |
| G6-S2-1 | P / 受限路径流形有差异 | 待证 | 流形约束改变原论文逐格共享的发射变量；\(Q=16\) 的预测不能沿用 \(Q=8\) 的计时。 | **DROP**。速率精度和预算都无法从草图推得。 |
| G6-S2-2 | P / 主瓣与低秩尾部分解有差异 | 待证 | \(N=64,\delta=0.5,B=2\) 时，最佳秩 3 尾部逼近的相对 Frobenius 误差仍约 **21.5%**。空间秩 1 张量 \(I_N\) 后是秩 \(N\)。 | **DROP**。两个核心代数前提均不成立。 |
| G6-S2-3 | P / 通用多项式与空间分解 | 否 | 路径对角线分开不推出谱条件数有界。感知方向一般还与通信 Hessian 耦合。 | **DROP**。固定四阶和标量注水缺少成立条件。 |
| G7-S1-1 | P / 免均衡对偶已覆盖，\(c_2\) 整形有近邻 | 待证 | 快速精确算子可用，但循环预处理和互补相位都缺全图收益证据。原截断基线偏弱。 | **DROP**。先检验有明确连续频带残差的固定参数方案。 |
| G7-S1-2 | P / 波形斜率变化有近邻 | 有，依赖改波形 | 跨块变 \(c_1\) 改变题设波形。固定小秩序列也不能精确表示一般全长拖尾。 | **DROP**。核心机制超出固定参数预编码边界。 |
| G7-S1-3 | P / 去斜旁瓣整形和软相长约束有近邻 | 否，按核心算子 | 精确去斜本身只是坐标变换。径向投影可守功率球，但不等于一般各向异性二次子问题的最优解。 | **DROP**。缺少去斜与通信求解之间可检验的结构耦合。 |
| G7-S2-1 | P / 条带预处理有差异 | 有，感知主张依赖改波形 | 跳变 \(c_1\) 越界。去掉后，原草图仍未说明零相关区如何在多用户相长约束下形成。 | **DROP**。固定波形版本缺核心感知机制。 |
| G7-S2-2 | P / 激活约束条带与连续频带投影有差异 | 待证 | 半光滑牛顿可用。连续多普勒基底应作有误差预算的软约束，硬正交可能挤掉相长可行域。 | **SELECT**。可以用精确对偶和全图检测分开验两端。 |
| G7-S2-3 | P / 带状逆与互补序列有近邻 | 否，通信侧 | 通用时域带状逆适用于 \(c_1=0\)。功率球有内部，双块低阶矩相消也不保证全图抑制。 | **DROP**。额外依赖跨块变 \(c_1\)。 |

入选版本固定 \(c_1,c_2\)，逐块使用独立载荷。按题给机制核查，七项均未复用 `h01` 的跨块固定恒模发射、`h02` 的信道老化跟踪、`m04/k01–k03` 的双基地杂波零空间或 `g01/g02` 的上行白化与参数选择。

## 3. Top 7 与 15 分钟探针

**共同判据。** 用同一合法基线和同一预先固定的联合指标 \(J\) 计算单模块回收率 \((J_{\rm single}-J_0)/(J_{A+B}-J_0)\)，两项均须 `<80%`。通信指标在共同照射或检出门槛下比较，同时报另一端的原始数值和朴素串联结果。涉及弱目标时，首块粗检占用各方案相同预算，后续只用先前回波。检测用同一全图及强目标单独存在的校准样本对齐虚警率，目标真值只在峰表输出后用于评分。噪声功率从共同校准数据估计。短探针可否决假峰或可行性，`Pfa=10⁻⁴` 的通过结论需要足量独立校准和测试图。

### #1 · `G2-S1-2`

- **精炼式。** 用固定四链恒模模拟阵保留全部路径的空间能量并满足照射下限，当 \(s\) 在模 \(N\) 下可逆时，以原索引的多普勒带和 \(s^{-1}m\bmod N\) 索引的时延带构造两个正定预处理块，用完整正规方程计算残差。
- **对手。** `(a)` 同四链硬件上的 Liu 完整跨格评价、逐格发射权重，12 轮。`(b)` Elbir HANDBALL 逐格移植，并单列 Liao 的混合方案直套。额外比较单轴预处理、Zhu 稀疏预编码近邻，以及固定阵列的稠密跨格解。在共同照射门槛下重测 `24.56 bps/Hz` 参考点。 [Liu](https://arxiv.org/html/2607.05119v1) · [Elbir](https://arxiv.org/abs/2411.02827) · [Liao](https://scholar.nycu.edu.tw/en/publications/design-of-joint-transmit-beamforming-for-multi-user-mimo-ofdm-int/) · [Zhu](https://arxiv.org/abs/2506.22465)
- **消融与首检。** `A-only` 用优化阵列和原逐格发射权重，预计保留的散射能量仍造成跨格干扰。`B-only` 用最强固定基线阵列和双轴全块求解，预计照射约束会压低速率。先在 \(N=64\) 检查双轴是否比最好的单轴预处理减少实际耗时，以及 `B-only` 是否已经回收八成。 

### #2 · `G4-S1-2`

- **精炼式。** 在固定 AFDM 参数下，利用按 \(s\Delta\ell\) 分组的预处理求通信可行集 \(\mathcal Hx=\gamma d\) 与发射样点圆盘的交集，并在交集内优化已发块与当前块的连续多普勒滞后积，逐时延用离散长椭球序列（DPSS）逼近频带核并检查被丢掉的能量。
- **对手。** `(a)` Liu 块线性通感预编码，接同一实际软包络限幅器（SEL）和 Sui 标量校准。`(b)` 逐格正则迫零直套加同一标量校准。额外独立跑 Gourar 的预留子载波或 Meng 的联合整形，列明有效载荷，另跑纯通信圆盘投影和完整频带核。 [Liu](https://arxiv.org/html/2607.05119v1) · [Sui](https://repository.essex.ac.uk/43341/) · [Gourar](https://arxiv.org/abs/2607.01064) · [Meng](https://arxiv.org/abs/2604.22198)
- **消融与首检。** `A-only` 保留全块通信可行性与圆盘，关闭旁瓣目标，预计重现纯通信消峰的感知损失。`B-only` 保留圆盘、完整信道与因果旁瓣核，用常规软通信损失更新，预计无法在同预算内维持 16-QAM 裕度。**先验功率口径。** 若以每个方案实际输入均方功率强制恰好 `0 dB` 输入回退，同时要求所有输入样点都在限幅圆盘内，则所有样点必须落在圆周上。Stage A 的圆盘自由度只能在统一标称驱动参考下使用。Rapp 功放还须用实际幅度映射和输入功率复算。

### #3 · `G7-S2-2`

- **精炼式。** 固定 \(c_1,c_2\)，在总功率球内，用完整相长约束的半光滑牛顿法求解，以激活约束中保留的 \(s\Delta\ell\) 条带预处理，并对因果粗检强目标邻域的连续频带滞后积施加带误差预算的 DPSS 软惩罚。
- **对手。** `(a)` Tang TWC 的完整信道对偶二次规划，用同一多用户模型和功率预算适配，`kν=1` 另列。`(b)` Li–Masouros 逐格相长预编码直套。额外用精确全算子和无条带预处理对照，跑全图等虚警盲检。 [Tang](https://arxiv.org/html/2508.12215#S4) · [Li–Masouros](https://discovery.ucl.ac.uk/id/eprint/10057140/1/08466792%281%29.pdf)
- **消融与首检。** `A-only` 保留完整相长求解，关闭 DPSS 旁瓣项，预计能降误符但弱目标仍受遮蔽。`B-only` 用完整信道的标准对偶求解器和同一旁瓣项，取消条带加速，按同一预设耗时比较。若它已能在该预算内达到联合质量的八成，则淘汰。先用稠密小问题检查真实判决裕度、功率和精确旁瓣，防止低秩代理报告虚假收益。

### #4 · `G3-S2-3`

- **精炼式。** 利用陪集 \(n=r+bL\) 的内层频率索引 \((m-sr)\bmod (N/L)\) 生成合法 1-bit 群翻转，用完整相长损失与因果跨块模糊旁瓣的同一目标评分，跨块选择只能从合法的近并列候选中产生。
- **对手。** `(a)` Liu 预编码接实际 1-bit 量化和 Sui 标量校准。`(b)` Wang 的交叉熵有限字母表优化直套。额外用 Salman SQUID 作独立对照。**硬门是同目标、同初值组、同计算预算下，优于可翻转任意一个发射比特的爬山法。** [Liu](https://arxiv.org/html/2607.05119v1) · [Sui](https://repository.essex.ac.uk/43341/) · [Wang](https://discovery.ucl.ac.uk/id/eprint/10212383/) · [Salman](https://arxiv.org/abs/2607.23216)
- **消融与首检。** `A-only` 保留陪集群翻转，关闭跨块项，预计主要回收通信增益。`B-only` 保留完整联合目标和跨块残差，只允许任意单比特更新，预计卡在群翻转可越过的局部最优。先从同目标的单比特局部最优出发，检查群翻转能否在多个种子上降低**精确**目标，再测等虚警检出。

### #5 · `G2-S2-1`

- **精炼式。** 以 \(\omega_{pp'}(c_1)-\omega_{pp'}(0)\) 表示仿射位移改变的同格碰撞，把它与全路径容量和照射约束一起用于恒模模拟阵优化，并以去啁啾后正规矩阵的循环平移平均构造快速傅里叶变换预处理，保留精确残差。
- **对手。** `(a)` 同四链、12 轮的 Liu。`(b)` 独立比较 Elbir HANDBALL 和 Liao 混合方案的零改动移植。额外跑同一全块求解器下的无碰撞权重阵列、随机置乱权重、Zhu 稀疏预处理和固定阵列稠密参考。 [Liu](https://arxiv.org/html/2607.05119v1) · [Elbir](https://arxiv.org/abs/2411.02827) · [Liao](https://scholar.nycu.edu.tw/en/publications/design-of-joint-transmit-beamforming-for-multi-user-mimo-ofdm-int/) · [Zhu](https://arxiv.org/html/2506.22465v1)
- **消融与首检。** `A-only` 用碰撞阵列加逐格发射权重，仍有跨格残差。`B-only` 用最强固定基线阵列加同一完整求解器，可能已经吃掉大部分速率增益。先检验真实碰撞权重是否比置乱权重提高**同照射下**的全块速率。若只改善代理指标，淘汰。

### #6 · `G6-S1-1`

- **精炼式。** 保留 Liu 的逐格发射变量和 \(Q=8\) 的全部块，用仿射多相预处理求总接收协方差 \(C\) 与干扰噪声协方差 \(\Sigma\) 的逆作用，再批量计算发射更新实际使用的逐格块 \(H_m^H(\Sigma^{-1}-C^{-1})H_m\)，并保留原照射仿射下界。
- **对手。** `(a)` 缓存完整 \(H_k[q]\)、15 轮、用批量 Cholesky 求解且只装配所需逐格块的 Liu 精确实现。`(b)` Liao 数字加权均方误差方案按 \(F_N\to A\) 零改动移植。Stage A 的逐格解耦实现单列复核。额外跑单级带状预处理与通用矩阵自由求解，所有方法计入预处理构造。 [Liu 式 (39)–(46)](https://arxiv.org/html/2607.05119v1#S4.SS2) · [Liao](https://scholar.nycu.edu.tw/en/publications/design-of-joint-transmit-beamforming-for-multi-user-mimo-ofdm-int/)
- **消融与首检。** `A-only` 保留多相逆作用，使用参考实现的逐格更新装配。`B-only` 保留批量路径收缩，用稠密精确求解逆作用。两者分别受更新装配或协方差求解限制。用**节省时间比例**计算消融，不能用倍数相除。先量 \(N=64\) 完整 15 轮，要求 `≥10×`、速率损失 `≤2%`、功率和照射均可行。通过后才测 \(128,256,512\)，其中 \(512\) 的基线必须实跑。

### #7 · `G2-S2-2`

- **精炼式。** 在 27 个主径组合中选择模 \(N\) 意义下可分离且功率代价最低的组合，以四链恒模阵压低带外耦合，行重排后在三条通信链计算二阶 Neumann 修正，并用完整信道残差和实际发射功率验收。
- **对手。** `(a)` 同硬件的 Liu 12 轮。`(b)` Elbir HANDBALL 逐格直套，并单列 Liao 混合设计直套。额外比较同一主径重排的零阶解、保留全部路径的稠密解，以及采用同一模拟阵的完整跨格解。 [Liu](https://arxiv.org/html/2607.05119v1) · [Elbir](https://arxiv.org/abs/2411.02827) · [Liao](https://scholar.nycu.edu.tw/en/publications/design-of-joint-transmit-beamforming-for-multi-user-mimo-ofdm-int/)
- **消融与首检。** `A-only` 保留选径、模拟聚焦和行重排，用零阶主径带解，预计剩余路径仍推高误符。`B-only` 保留重排和二阶修正，使用固定基线阵列，预计带外残差更强。先量 \(\|D^{-1}E\|_2\)、保留的路径功率和固定照射下的速率。若要达到收缩必须牺牲相当一部分可用多径，或者零阶已回收八成，立即淘汰。

## 4. 入选顺序

`G2-S1-2` → `G4-S1-2` → `G7-S2-2` → `G3-S2-3` → `G2-S2-1` → `G6-S1-1` → `G2-S2-2`
