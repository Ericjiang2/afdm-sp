# 漏斗门槛校准：2025–2026 AFDM 顶刊论文过关测试（2026-11-24）

> **目的**：将真实发表在 IEEE 核心期刊上的最新 `AFDM` 论文当作“假想候选卡”，逐篇过一遍当前漏斗规则（`ideas/FUNNEL.md` 第八轮口径 + `~/projects/personal-ai-workflow/skills/idea-funnel/SKILL.md` 的 `Value ledgers` 与 `Public-pain check`），检验漏斗究竟是 **(a) 门槛比 Transactions 还严**、**(b) 品味方向与领域热点错开**，还是 **(c) 战场找错了**。

## 一、选样规则与跑前冻结名单（防挑樱桃，分析前先锁定）

1. **检索工具与查询**：使用 `python3 ~/projects/personal-ai-workflow/skills/idea-funnel/scripts/search_papers.py`（数据源 `open_alex` + `crossref`，年份 `2025–2026`），检索标题含 `"affine frequency division multiplexing"`（含连字符写法）或独立缩写词 `"AFDM"`（含 `MIMO-AFDM`、`NOMA-AFDM`、`DAFT-s-AFDM`、`AFDM-ISAC` 等）的论文；并对六个目标期刊逐刊补查防单页截断漏检。
2. **期刊白名单与剔除条件**：严格只收 `IEEE TWC`、`IEEE TCOM`、`IEEE TSP`、`IEEE TVT`、`IEEE JSAC`、`IEEE TIT` 六本 Transactions / Journal 正式接收上线的研究论文；剔除一切快报（`WCL`、`CL`、`SPL`）、综述杂志（`Wireless Commun.`、`Network`、`Commun. Standards Mag.`、`VT Mag.`）、开放综合刊（`IEEE Access`、`OJ-COMS`、`Sensors`、`Physical Communication`）、会议与预印本。共命中符合条件的池子 **42 篇**。
3. **时间排序与截断**：因 Crossref 对部分 2026 Early Access 仅返回年份 `[2026]`（直接排会退化为按刊名 DOI 字母序误排），统一读取 Crossref DOI 精确上线注册日 `created.date-parts`（`YYYY-MM-DD`，同日再按 IEEE 稿件流水号降序），从新到旧严格取前 **20 篇**（时间跨度 `2026-06-05` 至 `2026-11-19`；含 `IEEE TVT` 8 篇、`IEEE TWC` 6 篇、`IEEE JSAC` 4 篇、`IEEE TCOM` 2 篇；其中 9 篇获取到开放全文或对应 arXiv 全文核对方法与仿真设定，11 篇无公开全文，严格标注`仅摘要`）。

### 跑前冻结样本表（共 20 篇）

| # | 上线日期 | 期刊 | 阅读深度 | DOI | Title |
|---:|---|---|---|---|---|
| 1 | 2026-11-19 | IEEE TCOM | 仅摘要 | `10.1109/tcomm.2026.3755494` | Dual-Chirp AFDM for ISAC: Ambiguity Suppression and Low-Complexity Receiver Design |
| 2 | 2026-11-17 | IEEE TVT | 全文 | `10.1109/tvt.2026.3754453` | Multi-Functional Non-Orthogonal AFDM Waveform for Integrated Sensing and Communications |
| 3 | 2026-11-12 | IEEE TVT | 仅摘要 | `10.1109/tvt.2026.3752613` | Pilot-Aided Multi-Mode AFDM-DNN Signal Detection |
| 4 | 2026-11-09 | IEEE JSAC | 全文 | `10.1109/jsac.2026.3752077` | DAFT-s-AFDM Enabled ISAC Systems: Ambiguity Function Analysis and Waveform Design |
| 5 | 2026-11-06 | IEEE JSAC | 全文 | `10.1109/jsac.2026.3751260` | Continuous-Time Analysis of AFDM: Pulse-Shaping, Fundamental Bounds, and Impact of Hardware Impairments |
| 6 | 2026-11-05 | IEEE TVT | 全文 | `10.1109/tvt.2026.3751020` | Grid-Refinement SBL for AFDM Channel Estimation Under Fractional Delay and Fractional Doppler Channels |
| 7 | 2026-11-05 | IEEE JSAC | 全文 | `10.1109/jsac.2026.3750788` | Affine Frequency Division Multiplexing With Pre-Chirp Spreading Index Modulation: A CSI-Driven Secure Transmission Framework |
| 8 | 2026-11-02 | IEEE JSAC | 全文 | `10.1109/jsac.2026.3749531` | AFDM-ISAC Design Amalgamating FMCW Radar and Carrier Aggregation |
| 9 | 2026-10-09 | IEEE TVT | 仅摘要 | `10.1109/tvt.2026.3742403` | Expectation-Maximization Vector Approximate Message Passing Detectors for MIMO-AFDM Systems |
| 10 | 2026-10-08 | IEEE TWC | 全文 | `10.1109/twc.2026.3741723` | AFDM–FTN: A Spectrally Efficient Waveform for High-Mobility Communications |
| 11 | 2026-10-07 | IEEE TWC | 仅摘要 | `10.1109/twc.2026.3741199` | ISAC Performance Analysis for AFDM |
| 12 | 2026-09-10 | IEEE TVT | 全文 | `10.1109/tvt.2026.3732687` | A Low-Complexity Joint Fractional Delay and Doppler Frequency Estimator for AFDM-Enabled Vehicular LEO-ICAN Systems |
| 13 | 2026-09-09 | IEEE TVT | 仅摘要 | `10.1109/tvt.2026.3732258` | Adaptive Guard Design with Low-Power Control-Layer Feedback for AFDM over Doubly-Selective Channels |
| 14 | 2026-09-01 | IEEE TVT | 仅摘要 | `10.1109/tvt.2026.3729877` | Learning Sparsity Pattern: An Adaptive Joint Detection for AFDM Grant-Free System in LEO Satellites Communication |
| 15 | 2026-07-28 | IEEE TWC | 仅摘要 | `10.1109/twc.2026.3715351` | Performance Analysis and Parameter Optimization of AFDM in Doubly-Dispersive Channels |
| 16 | 2026-07-09 | IEEE TWC | 仅摘要 | `10.1109/twc.2026.3709479` | Affine-BCJR Detection for Affine Frequency Division Multiplexing |
| 17 | 2026-07-01 | IEEE TWC | 全文 | `10.1109/twc.2026.3706989` | ISAC With Affine Frequency Division Multiplexing: An FMCW-Based Signal Processing Perspective |
| 18 | 2026-06-11 | IEEE TVT | 仅摘要 | `10.1109/tvt.2026.3702880` | A Maximum Distance Separable Code Assisted AFDM With Joint Spatial-Signal Domain Index Modulation |
| 19 | 2026-06-10 | IEEE TWC | 仅摘要 | `10.1109/twc.2026.3699661` | GNN-Enhanced Binary Loop Detection for NOMA–AFDM |
| 20 | 2026-06-05 | IEEE TCOM | 仅摘要 | `10.1109/tcomm.2026.3700535` | AFDM Transceiver Optimization for PAPR Reduction |

---

## 二、逐篇过关校准表（按漏斗关卡先后顺序取最早死因）

> **关卡判定顺序说明**（严格对照 `ideas/FUNNEL.md` 与 `SKILL.md`）：先查建卡前的**品味禁区**（不做雷达/目标感知 `ISAC`、拒绝无可解释物理结构的纯黑盒神经网络、本轮关闭纯理论分界/算账主题）；通过者查题面结构门（**拼凑组合**、**加开销凑增益**、**公共痛点门**、**单纯省 dB**）；再查第 6 步（**先例占用或原版直套即灵**）与第 7 步（**最强已有组合补上差距**、**账本门槛不达标**）；全部通过计为**能活过全部关卡**。

| # | 期刊 | 阅读深度 | 一句话贡献 | 战场标签 | 五类归属 | 最早死在哪一关 | 判断依据一句（引节号或图号） |
|---:|---|---|---|---|---|---|---|
| 1 | TCOM | 仅摘要 | 提出双啁啾 `DC-AFDM` 将一维脊状模糊函数重塑为十字结构抑制感知耦合伪峰，并配无矩阵 `TAP-PCG` 降低线性检测复杂度。 | 感知通信一体化 | 破壁 | 品味禁区（范围硬边界 1：不做雷达与目标感知） | 仅摘要：核心动机是消除 `ISAC` 时延–多普勒模糊脊定位伪峰（且剥出通信侧 `TAP-PCG` 也仅对比稠密直接 `LMMSE` 求逆稻草人）。 |
| 2 | TVT | 全文 | 将带宽压缩非正交 `nAFDM` 用于 `ISAC`，配噪声协方差白化 `K-Best` 球形译码与二维 `FFT` 测距测速，在 $\alpha=0.85$ 获 `17.65%` 有效谱效增益。 | 感知通信一体化 | 拼凑组合 | 品味禁区（范围硬边界 1：不做雷达与目标感知） | `Sec. I`、`Sec. III` 与 `Figs. 1, 4–6` 主体为单/双基地雷达测距测速分辨力与 `RMSE` 设计（通信侧亦只是 `SEFDM` 白化球形译码直套）。 |
| 3 | TVT | 仅摘要 | 针对导频辅助多模索引调制 `MM-AFDM`，提出先全 `SNR` 预训练、再用高 `SNR` 样本精调的两阶段 `DNN` 检测器以压低高信噪比误码平层。 | 接收端估计/检测 | 单纯性能 | 品味禁区（正向赛道红线：拒绝无可解释物理结构的纯黑盒神经网络） | 仅摘要：直接用通用黑盒 `DNN` 配按 `SNR` 分段采样训练做符号检测，且仅拿单次线性 `MMSE` 当对比基线。 |
| 4 | JSAC | 全文 | 推导局部/交织 `DAFT-s-AFDM` 的闭式期望模糊函数（揭示交织映射周期伪峰与四阶矩耦合），并用概率星座整形 `PCS` 联合优化通信速率与感知旁瓣。 | 感知通信一体化 | 单纯性能 | 品味禁区（范围硬边界 1：不做雷达与目标感知） | `Sec. III`、`Sec. V` 与 `Figs. 2–6, 8, 10` 全围绕单基地雷达模糊函数旁瓣、`CA-CFAR` 与 `MUSIC` 测速优化展开。 |
| 5 | JSAC | 全文 | 基于仿射傅里叶级数（`AFS`）建立连续时间 `AFDM` 解析模型，证明严格带限 `RRC` 成形与边缘子载波抑制（`SC`）维持多载波结构的必要性，并推导 `PSD`、相噪/频偏/采样抖动退化与单径 `CRB`。 | 理论极限 | 分界相图 | 品味禁区（本轮关闭纯理论算账/分界与前提分析，不单独立卡） | `Sec. II–IV` 与 `Sec. V` 明确仅做连续时间谱、硬件退化评估与单径 `CRB` 推导而未提任何新估计算法或补偿器（`Sec. V` 将估计检测留作 Future Work）。 |
| 6 | TVT | 全文 | 在嵌入式双导频（占 `3Q` 窗）下推导双分数时延–多普勒 `FDFD` 输入输出关系，提出一阶近似与二维网格细化稀疏贝叶斯学习（`FLA-GR-SBL` / `2D-GA-SBL`）。 | 接收端估计/检测 | 单纯性能 | 先例占用或原版直套即灵 | `Sec. III` 与 `Figs. 2, 4` 直接将 `OTFS` 离网/网格演化 `SBL`（文中 `[16]`）搬到 `AFDM` 双分数导频字典，保留每轮 $O((N_l N_\nu)^3)$ 求逆且额外增加双导频开销。 |
| 7 | JSAC | 全文 | 利用合法 `CSI` 死区量化加密正交前啁啾（$c_2$）扩频码本作为索引调制（`AFDM-PCS-IM`）传隐蔽比特，并设计双层 `Walsh` 约束消息传递检测器 `TLMP-WC`。 | 编码调制 | 拼凑组合 | 拼凑组合 | `Sec. II–IV` 与 `Figs. 1–2` 将前啁啾 `IM`、`Walsh` 扩频、`CSI` 量化密钥扰动与双层 `MP` 四块拼接，且前啁啾 $\mathbf{\Lambda}_{c_2}$ 在解调后退化为普通符号域酉加扰。 |
| 8 | JSAC | 全文 | 将载波聚合（`CA`）与类 `FMCW` 去啁啾接收融合于 `AFDM-ISAC` 提升测距精度与带宽分辨率，并用感知时延–多普勒辅助通信双分数信道估计 `CDS-CE`。 | 感知通信一体化 | 拼凑组合 | 品味禁区（范围硬边界 1：不做雷达与目标感知） | `Sec. II–III` 与 `Figs. 1, 4–7, 11–13` 主体为跨频段 `FMCW` 雷达脉冲压缩测距测速设计，踩中雷达感知硬禁区。 |
| 9 | TVT | 仅摘要 | 将期望最大化向量近似消息传递（`EM-VAMP` / `JEM-VAMP`）引入 `MIMO-AFDM`，在分数多普勒下联合迭代估计数据符号、未知噪声方差与 `BEM` 路径增益。 | 接收端估计/检测 | 开销·去先验·模型化硬件 | 先例占用或原版直套即灵 | 仅摘要：`EM-VAMP` 联合估计符号、噪声方差与信道基系数是 `MIMO/OTFS` 成熟标准算子，换入 `MIMO-AFDM` 等效矩阵属第 6 步 `(2)` 硬套。 |
| 10 | TWC | 全文 | 提出超奈奎斯特 `AFDM-FTN` 波形提谱效，设计 `BEM` 信道估计与跨时域–`FTN`–变换域多层消息传递联合估计检测（`BEM-MLMP-JCED`）。 | 发射端/波形/参数设计 | 开销·去先验·模型化硬件 | 先例占用或原版直套即灵 | `Sec. III` 与 `Fig. 9` 将既有 `OTFS-FTN [29]` + `BEM [32]` + 多层 `MP` 迁至 `AFDM`（且编码实验 `Fig. 13` 锁死同 `1/2` 码率，漏跑等净频效升码率正交 `AFDM` 强基线）。 |
| 11 | TWC | 仅摘要 | 建立含定时偏移 `STO` 与频偏 `CFO` 的连续/离散时间 `AFDM` 干扰模型（揭示对 `STO` 敏感性），并推导单基地与多基地 `ISAC` 模糊函数及 `CRLB`。 | 感知通信一体化 | 分界相图 | 品味禁区（范围硬边界 1：不做雷达与目标感知；且关闭纯分界分析） | 仅摘要：后半主轴为单/多基地 `ISAC` 模糊函数与 `CRLB`，前半为同步误差敏感度纯理论算账而无补偿算法。 |
| 12 | TVT | 全文 | 针对低轨卫星通信导航一体化（`LEO-ICAN`）视距单径信道，利用分数多普勒频谱折返包络结构提出最小熵多普勒搜索 + 闭式比值分数时延联合估计器。 | 接收端估计/检测 | 算力 | 最强已有组合补上差距 | `Sec. II Eq. (5)`、`Table I` 与 `Figs. 5–6` 将信道简化为单条纯视距径 $h\delta(\tau-\tau_0)\delta(\nu-\nu_0)$ 且设导频幅度 `x_pilot=100`，耗时只比二维 `MF-GFS` 与 `OG-SBL` 稻草人，未比单径同阶 $O(N\log N)$ 的一维去啁啾 `FFT+牛顿插值`（多径下包络比值式亦失效）。 |
| 13 | TVT | 仅摘要 | 接收端逐帧估计多径时延与分数多普勒扩展，将量化保护带宽度指令嵌入外侧保护子载波经低功率控制层闭环反馈给发射端自适应缩减保护带。 | 发射端/波形/参数设计 | 开销·去先验·模型化硬件 | 先例占用或原版直套即灵 | 仅摘要：测信道扩展并经反向控制链路闭环自适应调整保护间隔/循环前缀长度属 `OFDM/OTFS` 教科书链路自适应直套（且额外引入反向反馈信道前提）。 |
| 14 | TVT | 仅摘要 | 针对低轨免授权随机接入 `AFDM` 未知稀疏度下的联合活跃检测与信道估计，用带自注意力聚合的 `GNN` 学习时延–多普勒网格相关性精修稀疏先验。 | 多址/多用户 | 开销·去先验·模型化硬件 | 拼凑组合 | 仅摘要：把预设稀疏先验、`GNN` 消息传递与 `Self-Attention` 聚合三模块叠加，且仅对比在格近邻 `NNSPL` 而未扣闭式离网块稀疏基线与真值 `MSE` 消融。 |
| 15 | TWC | 仅摘要 | 在连续时间 `Weyl–Heisenberg` 框架下证明带保护间隔 `AFDM` 的渐近有用信号与 `ISI/ICI` 能量收敛性，经泰勒展开给出渐近 `SINR` 近最优啁啾率与保护间隔长度闭式解。 | 发射端/波形/参数设计 | 分界相图 | 品味禁区（本轮关闭分界/设计准则账；且撞一维/二维离线旋钮扫描底线） | 仅摘要：属本轮关闭的纯参数设计准则推导，且摘要自述闭式解相对直接搜最优参数仅是“损失可忽略”（离线扫两个标量参数已达精确最优，触发 `FUNNEL.md` 杀卡准则 2）。 |
| 16 | TWC | 仅摘要 | 利用仿射域等效信道稀疏带状结构建立有限状态 `Affine-BCJR` 逐符号 `MAP` 检测，并用 `Reverse Cuthill–McKee (RCM)` 置换与分块迭代压缩记忆长度和状态数。 | 接收端估计/检测 | 算力 | 最强已有组合补上差距 | 仅摘要：`RCM` 压缩树宽依赖整数多普勒少径稀疏图（摘要自述多径增多即需分块解耦迭代），一旦放入本漏斗强制的连续分数多普勒编码设定，带状 `CD-OAMP / EP` 已以 $O(N)$ 复杂度逼近 `MAP` 而无需指数级 `BCJR` 状态。 |
| 17 | TWC | 全文 | 给出使 `AFDM` 子载波严格等价于奈奎斯特采样周期 `FMCW` 的参数准则，建立 `DD-DAFT` 域输入输出模型与两种零导频匹配滤波感知算法。 | 感知通信一体化 | 开销·去先验·模型化硬件 | 品味禁区（范围硬边界 1：不做雷达与目标感知） | `Sec. II–IV` 与 `Figs. 4–7` 全文围绕 `FMCW` 等价雷达匹配滤波无导频测距测速（`PSLR`、`Image SNR`、检测概率 $P_d$）展开。 |
| 18 | TVT | 仅摘要 | 提出最大距离可分（`MDS`）码辅助的 `DAFT` 域 + 星座域 + 空域三维联合索引调制（`JSSDIM-AFDM`），并推导平均误比特率上界。 | 编码调制 | 拼凑组合 | 拼凑组合 | 仅摘要：将 `AFDM-IM`、广义空间调制 `GSM`、多模星座与 `MDS` 码分配做四合一组合搬移，属标准 `IM` 排列组合套路。 |
| 19 | TWC | 仅摘要 | 提出功率域 `PD-NOMA-AFDM`，设计内环 `MRC-MP` 消符号间干扰、外环更新外信息的双环 `SIC` 检测器 `BLMM`，并叠加 `GNN` 修正多用户干扰后验。 | 多址/多用户 | 拼凑组合 | 拼凑组合 | 仅摘要：将 `PD-NOMA`、基于 `Bemani/Thaj–Viterbo` 的 `MRC-MP` 双环 `SIC` 与 `GNN` 后验微调三者串联（第 8 轮 `g` 草稿 `h` 已实测纯闭式异方差 `EP/Turbo-PIC` 在过载上行直接追平单用户界）。 |
| 20 | TCOM | 仅摘要 | 在扩频 `AFDM` 上联合训练星座几何、最小化瞬时功率方差的预编码神经网络与接收端 `LSTM` 检测器，以压低 `PAPR` 并微幅改善 `BER`。 | 发射端/波形/参数设计 | 开销·去先验·模型化硬件 | 品味禁区（正向赛道红线：拒绝无可解释物理结构的纯黑盒 NN/LSTM 堆叠） | 仅摘要：端到端堆叠预编码 `NN`、可学星座与黑盒 `LSTM` 检测器压 `PAPR`（且为 `OFDM` 自编码器降 `PAPR` 直套，未比零参数闭式 `DAFT-s-AFDM` 或 `ICF+Zhidkov`）。 |

---

## 三、统计汇总与三个竞争假设的证据裁决

### 1. 各战场篇数分布（总计 20 篇，另列 `JSAC/TCOM/TWC` 12 篇高档子集）

| 战场标签 | 全部 20 篇占比 | 其中 `JSAC / TCOM / TWC`（12 篇） | 其中 `TVT`（8 篇） | 存活篇数 |
|---|---:|---:|---:|---:|
| `感知通信一体化`（ISAC） | **6**（30%） | **5**（42%：`#1, #4, #8, #11, #17`） | 1（`#2`） | 0 |
| `接收端估计/检测` | **5**（25%） | **1**（8%：仅 `#16 Affine-BCJR`） | 4（`#3, #6, #9, #12`） | 0 |
| `发射端/波形/参数设计` | **4**（20%） | **3**（25%：`#10, #15, #20`） | 1（`#13`） | 0 |
| `编码调制` | **2**（10%） | **1**（8%：`#7`） | 1（`#18`） | 0 |
| `多址/多用户` | **2**（10%） | **1**（8%：`#19`） | 1（`#14`） | 0 |
| `理论极限` | **1**（5%） | **1**（8%：`#5`） | 0 | 0 |
| `硬件损伤` / `其他` | **0**（0%） | 0 | 0 | 0 |

### 2. 五类价值归属与最早死因分布

- **五类归属**：`拼凑组合` **6 篇**（30%：`#2, #7, #8, #14, #18, #19`）、`开销·去先验·模型化硬件` **6 篇**（30%：`#5` 归分界则此项 5 篇；含 `#9, #10, #13, #17, #20`）、`分界相图` **3 篇**（15%：`#5, #11, #15`）、`单纯性能` **2 篇**（10%：`#3, #6`）、`算力` **2 篇**（10%：`#12, #16`）、`破壁` **1 篇**（5%：`#1`）、`跨层倒挂` **0 篇**（0%）。
- **最早死因分布（总存活 `0 / 20`）**：
  1. **`品味禁区`：10 篇（50%）**——其中 `不做雷达与目标感知 ISAC` **6 篇**（`#1, #2, #4, #8, #11, #17`），`拒绝纯黑盒 NN/LSTM` **2 篇**（`#3, #20`），`关闭纯理论算账/分界准则主题` **2 篇**（`#5, #15`）；
  2. **`拼凑组合`：4 篇（20%）**——`#7, #14, #18, #19`；
  3. **`先例占用或原版直套即灵`：4 篇（20%）**——`#6, #9, #10, #13`；
  4. **`最强已有组合补上差距`：2 篇（10%）**——`#12, #16`；
  5. **`能活过全部关卡`：0 篇（0%）**。
- **最接近活下来的候选在什么战场**：整批里最有独立理论或结构含量、非简单模块堆砌的只有 **3 篇**——`#5`（`JSAC` **理论极限**：连续时间 `AFS` 严格解析模型、谱与带限子载波抑制必要性）、`#15`（`TWC` **发射端/波形/参数设计**：`Weyl–Heisenberg` 渐近 `SINR` 收敛定理与闭式参数解）和 `#16`（`TWC` **接收端检测**：`RCM` 图带宽压缩 `Affine-BCJR`）。前两篇死在“本轮关闭纯理论分析/分界准则”，第三篇死在“本漏斗锁死连续分数多普勒编码设定，不允许退回整数多普勒少径稀疏图”。

---

### 3. 对三个假设的支持与反对证据

1. **假设 (a)：「门槛比 Trans 还严」—— 强支持（解释了跨过品味禁区的全部 10/10 篇死亡）**
   - **支持证据**：跨过品味禁区的 10 篇真实顶刊（`#6, #7, #9, #10, #12, #13, #14, #16, #18, #19`）在我们的漏斗里 **`0/10` 存活**（4 篇死于 `拼凑组合`、4 篇死于 `先例占用或原版直套即灵`、2 篇死于 `最强已有组合补上差距`）。真实 `TWC / JSAC / TVT` 明确接受“把 `OTFS / OFDM / MIMO` 已成熟的算子（`FTN #10`、`EM-VAMP #9`、`2D Off-Grid SBL #6`、`IM/NOMA + GNN #7/#18/#19`）适配到 `AFDM` 输入输出矩阵上，补齐专属 `PEP` / 状态演化推导并对比线性 `LMMSE` 或固定码率基线”；而我们的第 6 步要求**剥掉 `AFDM` 外壳按纯数学算子跨波形查新**，第 7 步又强制配齐**文献作者自己都从不同台运行的跨论文最强组合（如等净码率 `LDPC`、时域循环带状 `CD-OAMP`、离网 `NOMP/SAGE`）**——我们的准入标尺实质上是 `TIT` / 十年一遇开山作标尺，显著高于常规 `TWC / TCOM / TVT` 录用线。
   - **反对证据**：被拦下的这 10 篇里，`拼凑组合` 拦下的 4 篇（`IM + MDS`、`NOMA + GNN`、`Pre-chirp IM` 等）恰是按既定品味正常拦截套路排列组合文；真正比常规顶刊录用线严出一截的，主要是第 6 步**剥壳按跨波形算子判 `naive_port` 原版直套**（拦下 4 篇“把 OTFS/OFDM 算子搬到 AFDM 并补专属推导”的论文）与第 7 步**跨论文最强组合基线**（拦下 2 篇）。

2. **假设 (b)：「方向与领域热点错开」—— 强支持（直接切掉了整整 `10/20 = 50%` 的顶刊版面）**
   - **支持证据**：`AFDM` 在 2026 年 `JSAC / TCOM / TWC` 爆发的最大物理支点是“啁啾基天然等价于 `FMCW` 雷达波形”，因此 **`ISAC` 独占了 `30%`（且占了 `JSAC + TCOM` 6 篇里的 3 篇）**，却被范围硬边界第 1 条直接封禁；同时新波形早期最受 `JSAC / TWC` 欢迎的另一支是**连续时间基础模型、谱分析与基本界/渐近公式**（`#5 JSAC`, `#15 TWC`，占 `10%`），又被“关闭分界/算账主题、只准跑算法硬指标”挡在门外；外加黑盒 `NN` 禁令切掉 `10%`（`#3, #20`）。我们在起跑线上就把当前 `AFDM` 顶刊一半的主流产区关掉了。
   - **反对证据**：即便把这 10 篇禁区论文放进来，除 `#5` 与 `#15` 两篇连续时间理论分析外，其余 `ISAC` 与 `NN` 论文（如 `#2 nAFDM-ISAC`、`#8 CA+FMCW`、`#3/#20` 黑盒 `NN`）放到第 6–7 步依然会死于模块拼凑或 `OFDM-ISAC` 直套，说明“品味错开”不能单独解释 `0` 存活。

3. **假设 (c)：「战场找错了（活下来或接近活下来的集中在发射端、编码调制、理论）」—— 对高档刊分布成立，但对“换战场即可在现门槛下出卡”构成反证**
   - **支持证据**：在剔除 `TVT` 后的 `JSAC / TCOM / TWC` 12 篇高档刊里，**纯接收端估计/检测仅占 `1/12`（8%，`#16`）**，其余 `11/12` 全在感知、发射端波形/参数、连续时间基础理论、编码调制与多址；且全样本最接近过关的 3 篇硬核工作里，有 2 篇（`#5 JSAC` 连续时间 `AFS` 理论与带限子载波抑制、`#15 TWC` 连续时间渐近 `SINR` 与参数闭式解）都在**连续时间波形理论与发射端参数层**，确实不在叠加导频接收机内部。
   - **反对证据**：样本中的发射端与编码调制论文（`#7 Pre-chirp IM`、`#10 AFDM-FTN`、`#13 自适应保护带`、`#18 MDS-IM`、`#20 PAPR`）在现行「剥壳跨波形 `naive_port` + 防拼凑 + 等净码率最强基线」门槛下同样 **`0/5` 存活**（且第 7–8 轮实测也已跑过 `PAPR`、`DAFT-s-AFDM`、多址斜率、码与 `EXIT` 匹配等十余个非接收端草稿均撞上酉等价或 `OTFS/OFDM` 先例），证明只要保持“跨出 `AFDM` 名字算先例占用”不变，单纯在 `ABSTRACTION.md §4` 补开发射端与编码调制问题并不会自动涌现幸存卡。

**最终结论**：我倾向于 **「(a) 跨波形纯算子 `naive_port` 门与跨论文最强组合基线比常规 Trans 严一档（而防拼凑门系按品味正常工作）」与「(b) 品味主动切掉了 AFDM 一半热点（ISAC 与连续时间纯理论/界分析）」双主因叠加，同时 (c) 在 `TWC/TCOM/JSAC` 高档刊上部分成立（纯接收机估计检测在顶刊仅占 1/12，高含金量非感知工作集中在连续时间物理成形/基本界 `#5` 与波形结构层 `#15/#16`）**；置信度：**中**（20 篇中 11 篇仅核摘要，且“最早死在哪一关”由单模型独立判定）；推翻条件：若在**不改现行第 6–7 步 `naive_port` 与 Steelman 门槛、仍封禁 `ISAC` 与纯理论/界分析**的前提下，仅靠在 `ABSTRACTION.md §4` 增开发射端与编码调制开放问题跑一轮（8 小时）就能产出 ≥ 2 张过第 8 步终审的独立 L3 卡，则推翻“(a)+(b) 是主因、单改战场不够”的判断。
