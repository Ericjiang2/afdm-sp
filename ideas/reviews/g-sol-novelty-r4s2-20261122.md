**第 6 步判定：g21 `(2)`，转现稿审计；g22 `(2)`，核心算子已有直接先例；g23 `(2)`，等带宽前提被探针复核推翻；g24 `(3)`，只保留单帧自校准可辨识性的子问题。**

本次做了只读源码审计和跨领域文献检索。数值上独立复算了 g23 的频谱，其余探针读数来自卡片和归档。四张卡均未执行第 7 步。

## g21 · 嵌入导频与叠加导频的等净载荷比较

**A｜固有重要性：低。** 对现稿图 4 有实质影响，作为独立研究题分量低。固定编码码率回答的是「两套固定配置哪套交付更多比特」，固定每帧净信息比特回答的是「要交付同一载荷，哪套方案更可靠或更省能量」。两种口径都有先例，最接近的论文甚至在同一张图中报告两种结果。现稿场景 S 的约 33% 优势可用于描述冻结配置。将它推广到允许嵌入导频调整码率的系统选择，证据不足。 [归档结果](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation/research-assets/res-20261015-03.md:26) · [Kanazawa 等，图 9](https://arxiv.org/html/2501.15935v2)

**B｜查新：已被做过。** 去掉波形后，比较的是 \(G=k(1-\mathrm{FER})\)，其中 \(k\) 是每帧可承载的净信息比特，\(\mathrm{FER}\) 是误帧率。文献已经明确比较过固定码率与固定 \(k\) 两种问题。

| 最接近工作 | 算子或比较口径 |
|---|---|
| Kanazawa、Iimori、Pradhan、Malomsoky、Ishikawa，2025，*Superimposed Pilot-Based OTFS – Will it Work?*，arXiv:2501.15935 | **直接等价。** 图 9(a) 固定编码码率，允许净速率不同。图 9(b) 调码率配平净速率，图 10 又做了同星座配平。两种口径都成立，该文配平后仍测到其多叠加导频方案占优。 [原文](https://arxiv.org/html/2501.15935v2) |
| Coldrey、Bohlin，2007，*Training-Based MIMO Systems—Part I: Performance Comparison*，IEEE TSP | 比较独占槽位训练和叠加训练，优化时间与功率后比较可达数据率。已处理同一开销与能量权衡，未做本卡有限码长配平。卡片所引的题名、期刊和「必须固定净比特」归因应更正。 [作者机构出版记录](https://research.chalmers.se/en/publication/19026) |
| Asyhari、ten Brink，2017，*Orthogonal or Superimposed Pilots? A Rate-Efficient Channel Estimation Strategy for Stationary MIMO Fading Channels*，IEEE TWC | 在平稳衰落下比较两类训练的可达速率，明确计入独占训练的时间开销。目标是速率，未强制两臂使用同一个纠错码。 [作者稿](https://pure.coventry.ac.uk/ws/portalfiles/portal/23302283/Binder1.pdf) |
| Hassibi、Hochwald，2003，*How Much Training Is Needed in Multiple-Antenna Wireless Links?*，IEEE TIT | 容量下界含数据时长比例 \((T-T_\mathrm{tr})/T\)，并联合分配训练与数据功率。等价的是开销账本，研究对象是独占训练。 [原文](https://my.ece.utah.edu/~ece6962/project/training_MIMO.pdf) |
| Ferrante、Östman、Durisi、Kittichokechai，2018，*Pilot-Assisted Short-Packet Transmission over Multiantenna Fading Channels: A 5G Case Study*，arXiv:1801.10552 | 固定短包净载荷、时延与可靠性约束，再评估导频辅助传输。与本卡的等载荷工程问题同型。 [原文](https://arxiv.org/abs/1801.10552) |
| Mishra、Singh、Prasad、Budhiraja，2020，*OTFS Channel Estimation and Data Detection Designs With Superimposed Pilots*，arXiv:2010.15066 | 将省掉专用导频槽位列为频谱效率收益，并计入叠加数据干扰。支持固定配置下报告槽位收益，未给出本卡的有限码长反转结果。 [原文](https://arxiv.org/abs/2010.15066) |

**C｜`(2)`。** 按 `pit` 规则，熟知的比较口径应回到现稿审计。场景 S 的归档 `H6` 主标签是 \(\rho=0.30\) 下 `SP better`，而 \(\rho=0.50\) 原本就是 `MIXED`。卡片预测的 6 dB 符号反转发生在 \(\rho=0.50\) 的单点。**\(\rho=0.30\) 的高信噪比优势幅度消失，与它的冻结主标签翻转，是两件事。** 两臂都零错时，1024 对 1022 仍差 2 比特。原规则只要至少三个信噪比点的配对区间严格为正，且反向不足三个点，就可能仍给 `SP better`。主场景保护带需要 1029 个槽位、超过 1024 槽的判断由几何条件决定。 [冻结判定规则](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/p2b_agg.py:11)

**D｜最强反对意见。** 指定脚本只覆盖开发域 6 帧，且只跑嵌入导频。即使得到 `0/6`，单侧 95% 误帧率上界仍约 39%。要翻转归档 \(\rho=0.50\) 在 6 dB 的点估计，配平后的嵌入导频误帧率需低于约 **6.8%**，因为 \(1022(1-\mathrm{FER})>952.8\)。约 0.6 核时的原装同键检查有现稿审计价值。审计应先在开发集冻结导频功率，再在原测试键对照原码率、配平码率和两条叠加导频曲线，并分别报告原 `H6` 标签与预先定义的实际等效范围。现稿可立即把「约 +33%」限定为**固定约 \(1/2\) 码率的两套配置**。 [指定探针](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation/ideas/probes/g_probe_g21_ep_equal_rate.py:39)

## g22 · 译出异或码字后折叠信道列

**A｜固有重要性：高。** 强相关或过载的多用户多输入多输出系统中，逐流检测可能连第一条流都起不来。正交调度会消耗并发资源，要恢复同样的总净速率就得提高活动时段的速率。若整帧线性约束能可靠缩小剩余搜索空间，同时保住总速率与译码预算，这个机制本身够一篇论文。

**B｜查新：已被做过，核心二元条件化直接等价。** 设 \(u_t=c_{i,t}\oplus c_{j,t}\)，二进制相移键控的符号映射给出 \(x_{j,t}=(-1)^{u_t}x_{i,t}\)。所以已知 \(u_t\) 后，条件似然自然使用 \(\mathbf h_i+(-1)^{u_t}\mathbf h_j\)。从标量接收推广到多天线，只需将标量系数换成列向量。多对排序与期望传播软检测的具体组合仍有实现差别。

| 最接近工作 | 核心算子比对 |
|---|---|
| Sula、Zhu、Pastore、Lim、Gastpar，2019，*Compute–Forward Multiple Access (CFMA): Practical Implementations*，IEEE TCOM，预印本 arXiv:1712.10293 | **直接等价。** 第 III-B 节式 (6)、(8b) 和算法 1 先译整帧异或，再用 \(p(y_t\mid c_{i,t},u_t)\) 译一流，最后异或恢复另一流。等增益例中，异或为 0 时信号相加，为 1 时第二次译码的该符号似然为零，正是卡片和列与差列的特例。 [原文](https://arxiv.org/pdf/1712.10293) |
| Zhang、Liew，2008，*Channel Coding and Decoding in a Relay System Operated with Physical Layer Network Coding*，arXiv:0807.4770 | 同一线性码下从叠加观测直接译网络编码字。异或闭包与第一段译码等价，任务终点是中继得到组合字。 [原文](https://arxiv.org/abs/0807.4770) |
| Chae、Jang、Ahn、Park、Jeong，2017，*Multilevel Coding Scheme for Integer-Forcing MIMO Receivers With Binary Codes*，IEEE TWC | 二元码与多级映射已经用于整数迫零。核心是译整数线性组合，未用整帧硬异或逐符号替换剩余信道列。 [作者机构出版记录](https://sejong.elsevierpure.com/en/publications/multilevel-coding-scheme-for-integer-forcing-mimo-receivers-with-/) |
| Feng、Silva、Kschischang，2013，*An Algebraic Approach to Physical-Layer Network Coding*，IEEE TIT，arXiv:1108.1695 | 格码余类与多条独立组合作为基本变量，短整数向量选择已有先例。其多组合框架与有限二元字母表的条件化降维有别。 [原文](https://arxiv.org/abs/1108.1695) |
| Cocco、Pfletschinger、Navarro，2014，*Seek and Decode: Random Access with Physical-Layer Network Coding and Multiuser Detection*，arXiv:1406.4736 | 混用单用户字与网络编码方程恢复用户数据，同时利用跨时隙及预编码多样性。与卡片共享「先找容易译的方程」，具体恢复路径不同。 [原文](https://arxiv.org/abs/1406.4736) |
| Zhang、Evans、Zhu，2024，*Compute-Forward Multiple Access for Gaussian MIMO Channels*，arXiv:2409.06110 | 已把先译组合、后恢复个体推广到多天线高斯接入。采用格码和可达速率分析，与本卡有限长度二元硬折叠的实现不同。 [原文](https://arxiv.org/abs/2409.06110) |
| Ping、Liu、Wu、Leung，2006，*Interleave Division Multiple-Access*，IEEE TWC | 用用户专属交织与迭代软检测处理并发干扰。它是系统级替代方案。已查到的论文和本探针均未建立「异交织加期望传播」在同算力下支配本卡。 [原文](https://ieeexplore.ieee.org/document/1618943/) |

**C｜`(2)`。** 最接近的直接对照是二元 CFMA，即先译组合再译个体，而卡片的主要对照是常规逐流解码或静态整数迫零。探针同时改变了候选搜索、额外译码次数和条件化操作，因此每点 16 帧的编码比特误码收益无法归因到折叠本身。剩余差异目前是多流候选排序和近似似然，尚无足够证据支撑独立机制。

**D｜最强反对意见。** 异或字通过校验只说明它属于码本。错误异或也能通过，随后会把剩余信道逐符号改错。即使异或全对，当两列完全相同时，差列仍为零，所以「折叠后变成满秩」需要额外条件。最有区分力的重审证据是同码、同候选和同译码预算下，对照 **二元 CFMA 条件似然、真异或折叠和估计异或折叠**，同时报告错误折叠率与用户块错误率。另一个对照有速率账本错误。四用户逐个分时、用 \(1/2\) 码率 16-QAM 时，合计只有 2 比特/信道使用，并发 \(1/2\) 码率 QPSK 是 4 比特/信道使用。 [指定探针](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation/ideas/probes/g_probe_g22_if_mccf.py:320)

## g23 · 恒包络信号的图解缠接收机

**A｜固有重要性：高。** 多径均衡后的相位跨过分支切口，接收机就可能整段数错 \(2\pi\) 的圈数。降低调制度可减少这种错误，也会减弱相位对数据的响应。若能在同带宽、同载荷和同发射能量下扩大可用的调制度范围，且接收成本可控，就足以改变恒包络波形的设计。

**B｜查新：部分被做过。** 对固定权重，所谓 Hodge 更新就是在跨距 1、2 的图边上拟合包裹相位差，并用逐点相位残差作锚的加权最小二乘。五对角来自这两种边的带状结构。未见完全相同的五层组合，核心子算子各有先例。

| 最接近工作 | 核心算子比对 |
|---|---|
| Ghiglia、Romero，1994，*Robust Two-Dimensional Weighted and Unweighted Phase Unwrapping That Uses Fast Transforms and Iterative Methods*，JOSA A | 包裹相位梯度的加权最小二乘产生离散泊松型方程。与本卡的边项同型，本卡加了第二种跨距和逐点锚。 [原文](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-11-1-107) |
| Ghiglia、Romero，1996，*Minimum \(L^p\)-Norm Two-Dimensional Phase Unwrapping*，JOSA A | 将鲁棒解缠迭代化为一串数据依赖加权最小二乘。包裹梯度和跳变降权已有先例，具体权重及跨层调度不同。 [原文](https://opg.optica.org/josaa/abstract.cfm?uri=josaa-13-10-1999) |
| Cucuringu、Tyagi，2020，*Provably Robust Estimation of Modulo 1 Samples of a Smooth Function with Applications to Phase Unwrapping*，JMLR | 用圆周嵌入和图平滑恢复模一观测。共享圆周与图的结构，观测里没有多径混合，变量也没有离散星座先验。 [原文](https://jmlr.org/papers/v21/18-143.html) |
| Thompson、Ahmed、Proakis、Zeidler、Geile，2008，*Constant Envelope OFDM*，IEEE TCOM | 已建立指数调相、均衡、相位解调以及调制度与带宽的权衡。这是顺序解缠基线。 [原文](https://doi.org/10.1109/TCOMM.2008.070043) |
| López-Morales、Dinis、García-Armada，2022，*Near-Optimal Detection of CE-OFDM Signals with High Power Efficiency via GAMP-based Receivers*，IEEE GLOBECOM Workshops | 广义近似消息传递直接利用指数调相的非线性似然，在频选信道中已对照常规相位检测。它绕开硬解缠，是卡片漏跑的强基线。 [原文](https://novaresearch.unl.pt/en/publications/near-optimal-detection-of-ce-ofdm-signals-with-high-power-efficiencie/) |
| Schniter、Rangan、Fletcher，2016，*Vector Approximate Message Passing for the Generalized Linear Model*，arXiv:1612.01186 | 把线性估计与非线性似然拆成模块，包含相位恢复应用。与卡片的迭代分工有交集，普通幅度型相位恢复的观测模型与 \(H\exp(j\beta Bx)\) 不同。 [原文](https://arxiv.org/abs/1612.01186) |
| Xue、Chen、Li、Cao、Zhang，2026，*Constant-Envelope Waveform Design and Phase Recovery for Integrated Sensing and Communication in High-Mobility Multipath Environments*，Sensors | 在多径恒包络波形上串联正则化反演、参考辅助解缠和整帧相位回归。已经覆盖「去混合后用结构恢复相位」，未用本卡的双跨距图更新或星座软回投。 [原文](https://www.mdpi.com/1424-8220/26/16/5130) |

**C｜`(2)`。** 目前最大的收益来自超出卡片自身带宽约束的点。两个采样网格用相同频谱系数，但逆变换归一化使高采样率网格的相位幅度减半。把两个网格在共同采样点对齐后，按原口径复算，\(\beta=1.2,1.5,1.8\) 的 99% 功率带宽分别是线性参照的 **1.156、1.469、1.664 倍**。这三个点都超出卡片声称的 \(1.00\) 倍上限。\(\beta=1.8\) 时仍有约 99.74% 能量落在接收采样带内，因为那条带比卡片用来声明公平的线性参照更宽。当前证据既未显示低调制度经典接收机已经追平，也不足以证明新接收机在等带宽下领先。 [频谱与接收波形生成代码](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation/ideas/probes/g_probe_g23_ce_afdm_hodge.py:19)

**D｜最强反对意见。** 图求解本身是线性复杂度，探针的整层还使用稠密信道特征分解、矩阵向量乘和稠密子空间投影。50 个参数也按每个调制度和信噪比重新训练。最便宜的重审证据是在**同一实际带宽约束**内，先用独立开发集联合选择各接收机的调制度和参数，再比较广义近似消息传递、无训练图解缠和跨工况共享参数的版本。只有这个对照仍显示差距，才有依据解释为解缠收益。 [均衡与训练代码](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation/ideas/probes/g_probe_g23_ce_afdm_hodge.py:104)

## g24 · 共享色散与离网多径的盲自校准

**A｜固有重要性：高。** 少量已知导频与大量未知数据叠加时，共享前端色散会让所有路径模板一起失配。专用校准前导能提供干净观测，代价是时频资源。若能给出何时可从现有单帧辨认色散、何时必须标定的判据，问题本身足以支撑一篇论文。

**B｜查新：部分被做过。** 正交多项式自聚焦、相位与整体平移的歧义、以及相位误差和离网稀疏参数的联合估计都查到直接先例。未见同一工作在本卡的单帧叠加导频模型下，给出未知数据干扰中的稳定可辨识条件并验证样本外前端。

| 最接近工作 | 核心算子比对 |
|---|---|
| Cho、Hui，2006，*Autofocus Method Based on Successive Parameter Adjustments for Contrast Optimization*，US20060109163A1 | **最直接的 Legendre 先例。** 在合成孔径雷达中用正交 Legendre 多项式拟合公共相位误差，搜索系数使图像更聚焦。与本卡前 \(K\) 峰集中度属于同类相位补偿搜索，目标函数不同。 [公开原文](https://patents.google.com/patent/US20060109163A1/en) |
| Wahl、Eichel、Ghiglia、Jakowatz，1994，*Phase Gradient Autofocus—A Robust Tool for High Resolution SAR Phase Correction*，IEEE TAES | 从强散射点估计共享相位梯度。聚焦与整体位移的区分已有先例，具体估计量不同于两系数峰值搜索。 [原文](https://doi.org/10.1109/7.303752) |
| Wang、Liu，2006，*SAR Minimum-Entropy Autofocus Using an Adaptive-Order Polynomial Model*，IEEE GRSL | 交替调整公共相位多项式系数使图像熵下降。与本卡低维相位搜索同族，使用不同聚焦分数，并允许阶数自适应。 [原文](https://doi.org/10.1109/LGRS.2006.878446) |
| Çamlıca、Gürbüz、Arıkan，2017，*Autofocused Spotlight SAR Image Reconstruction of Off-Grid Sparse Scenes*，IEEE TAES | **直接覆盖相位自聚焦与离网稀疏恢复的结合。** 联合估计公共相位误差和连续位置偏移，未使用叠加导频的数据反馈。 [原文](https://doi.org/10.1109/TAES.2017.2675138) |
| Eldar、Liao、Tang，2017，*Sensor Calibration for Off-the-Grid Spectral Estimation*，arXiv:1707.03378 | 传感器复增益与连续频率的乘积模型等价于去掉多普勒后的核心结构。第 2 节显式处理公共相位、线性斜率与频率平移的歧义，并推导多快拍条件。 [原文](https://arxiv.org/abs/1707.03378) |
| Kazaz、Coutino、Janssen、van der Veen，2020，*Joint Blind Calibration and Time-Delay Estimation for Multiband Ranging*，arXiv:2002.10167 | 直接联合估计射频链失真与连续多径时延，用协方差匹配和先验约束处理病态问题。观测与本卡的单帧未知载荷环境不同。 [原文](https://arxiv.org/abs/2002.10167) |
| Cang、Swärd、Sheng、Jakobsson，2021，*Toeplitz-Based Blind Deconvolution of Underwater Acoustic Channels Using Wideband Integrated Dictionaries*，*Signal Processing* | 宽带水声中已有未知波形与稀疏多径的联合盲反卷积。与本卡共享核失配和稀疏恢复困难，采用宽带积分字典与 Toeplitz 结构。 [原文](https://doi.org/10.1016/j.sigpro.2020.107812) |

**C｜`(3)`。** 子卡应问：**在单帧、固定导频开销、有未知数据干扰的条件下，哪些前端色散方向能与连续时延、多普勒及复增益稳定区分？** 这个缺口决定接收机该当帧启用自校准、跨帧共享校准，还是从专用前导取得观测。先在观测空间消去路径雅可比可解释的方向，再测剩余色散雅可比的最小奇异值，检验它是否能预报估计误差及译码启动。这个问题与改换多项式基或多展开几层有实质区别。

**D｜最强反对意见。** 卡片的「任意点雅可比正交」不成立。即使只有一条路径，基函数 \(P_m\) 与频率 \(\omega\) 在均匀频格上正交，求色散与时延导数的观测内积时仍会多出发射频谱功率 \(|X(\omega)|^2\) 作为权重。多径和多普勒还会引入交叉项。去掉常数和线性项确实为整体相移、整体时移选定了一个规范，但这个操作本身无法保证剩余参数局部可辨识。探针用同一组 Legendre 基生成和拟合，标成「无噪门」的断言测试的是**零色散**路径拟合。所谓正则化有限冲激响应对照把小矩阵加进了设计矩阵，也不等价于岭回归。故卡片的 12 帧每点结果只能说明匹配模型下存在可行性信号。最强对照应共享同一相位模型、初始化和软反馈，以常规集中似然消去路径增益，再用独立测得或独立构造的幅相响应做留出检验。 [生成与校准代码](/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-g/00_Inbox/AFDM-channel-estimation/ideas/probes/g_probe_g24_gauge_disp_afdm.py:193)

最值得抽查的两处原文是 [Kanazawa 等图 9 的双口径](https://arxiv.org/html/2501.15935v2) 和 [Sula 等式 (8b) 与算法 1](https://arxiv.org/pdf/1712.10293)。可用「白话」把这两处证据和 g24 的子卡判据各压成一句。
