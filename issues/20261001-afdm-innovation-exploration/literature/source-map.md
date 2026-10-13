# 最近邻证据图

核验日期 2026-10-01；MAP-01。状态 **partially searched**。复用当前公开检索缓存与已存历史原文核对，本次补取 NOMP、near-collision 与计算价值原文。仅发送公开题名/方法词/公开 arXiv ID；未上传项目内容。来源 ID 固定，便于后续 concern 引用。

## 改变本轮设计的证据卡

| ID / 来源 | 已核实机制或结果 | 读取层级 / 锚点 | 本轮转移条件及剩余差异 |
|---|---|---|---|
| L-01 [NOMP](https://arxiv.org/abs/1509.01942v2)，[TSP 2016 DOI](https://doi.org/10.1109/TSP.2016.2580523) | 检测新正弦后，对已有原子循环 Newton 精炼并重拟合 LS；讨论最小间距与病态 | 本轮 primary HTML 转文本；`1509.01942v2.txt` 130–136、477–490、1439–1833、1992–2205 | 连续局部精炼/强相关原子本身不能作创新；AFDM 的工作协方差、编码消费者与预算是额外条件，不由 NOMP 结论担保 |
| L-02 [Super-resolution of near-colliding point sources](https://arxiv.org/abs/1904.09186v2) | 部分紧簇的节点/幅度重建难度依 SRF 放大；非簇参数更稳定；特定假设下给 minimax rate | 本轮 primary HTML；`1904.09186v2.txt` 158–298、1377–1423；读取摘要与引言结果陈述，未逐条验证证明 | 连续带宽、有界误差、簇分离假设不能原样替代有限 N、码相关输入的 TF FER；支持 C-PAIR 的问题真实性，不能据其声称本项目已达分辨极限 |
| L-03 [JCCD-VALSE](https://arxiv.org/abs/2107.07101v1)，[JOE 2022 DOI](https://doi.org/10.1109/JOE.2022.3162025) | 连续延迟的 gridless VALSE、MMSE、LDPC 交换外信息；更新 CFO/噪声，自动估计 nuisance 参数 | 已有 primary HTML 重读 §IV，式(15)/(16)及循环描述；保留 `2107.07101v1-excerpts.md`；Crossref 核对期刊/年份 | 水声 OFDM/公共 Doppler scale 与当前 SP-AFDM 模型不同；可据此否定“首次连续几何+软译码闭环”，不能把它当已复现公平基线 |
| L-04 [D-GESBL](https://arxiv.org/abs/2607.18881v1)，2026 预印本 | SP-AFDM 分数延迟/多普勒、MMV off-grid SBL、动态网格、数据辅助反馈、GAMP 降成本 | 已有 primary HTML 重读算法 `Mod[Demod(...)]`、等效 Gaussian 残差假设、数值讨论；保留 `2607.18881v1-excerpts.md` | 不能把数据辅助/动态网格作新颖点；所见原文未建立当前 LDPC APP 模式保留或 TF full Γ 理论。未将“decoded”字样推断为 LDPC APP |
| L-05 [Selecting Computations](https://arxiv.org/abs/1207.5879v1)，2012 版本 | 以最终决策效用减计算成本为目标的 metalevel 决策；最优停止与近似策略 | 本轮 primary HTML；`1207.5879v1.txt` 105–129、329–344、1398 后 Theorem 4；2014 的 1408.2048 为重复题名记录，未当两个独立来源 | 计算结果分布须建模；当前接收机的 action 前状态是否足够未知。通用 $Q_a(z)$ 和阈值没有独立新颖性 |
| L-06 [VALSE](https://arxiv.org/abs/1604.03744v2)，[TSP 2017 DOI](https://doi.org/10.1109/TSP.2017.2655489) | 文献身份及 Bayesian line-spectra 主题已核实 | 已有 arXiv API 摘要/元数据；本次 HTML 返回 406，保留在 `fetch-records.json`；未假称全文成功 | 不对其完整 posterior factorization 或某条定理作未读等价性断言；主要闭环近邻使用已读 L-03 |
| L-07 [AFNC for pulse-shaped AFDM](https://arxiv.org/abs/2607.05082v1)，2026 预印本 | 摘要明确 Newtonized 分数延迟/多普勒估计，以预计算 shaping-pulse ambiguity function 加速 Jacobian/Hessian | 已有 arXiv API 摘要/元数据；未读完整算法/证明 | 已足以约束“AFDM Newton refinement 首创”的宽表述；是否与具体成对簇更新重叠，候选定型后须补读原文 |
| L-08 项目历史综合：`../../../.trellis/tasks/09-13-trans-next/research/ce-state-literature-map-v1.md`；`spafdm-gpt-20260920/architecture-verdict.md` | 迭代 CE、外信息、SBL 增删、OSD、候选边缘化、joint prediction、coreset、branch 已有明确近邻或内部探索 | 本轮重读历史来源图、architecture verdict 的完整相关段和 master record 第 9 节；历史公开来源读取层级逐项保留 | 公共历史论文机制与本项目内部探索不同；内部探索是去重约束，不冒称外部先发表。N=24/48 reference 或单次 N=1024 attachment 不冒充当前全规模总体结果 |

L-08 路径按项目根解析：`.trellis/tasks/09-13-trans-next/research/`；本文件表内相对路径仅描述关联，不要求迁移原件。

## 只作定位的经典身份

- Golub–Pereyra，*Separable nonlinear least squares: the variable projection method and its applications*，Inverse Problems 2003，[DOI 10.1088/0266-5611/19/2/201](https://doi.org/10.1088/0266-5611/19/2/201)。Crossref 身份已核；本轮未读全文，不能据此宣称某个带先验 AFDM 公式逐式等价。
- Smith，*Statistical resolution limits and the complexified Cramér-Rao bound*，TSP 2005，[DOI 10.1109/TSP.2005.845426](https://doi.org/10.1109/TSP.2005.845426)。Crossref 身份已核；仅用于定位 resolution 近邻，未借用其界作本项目数值结论。
- *Efficient Least Residual Greedy Algorithms for Sparse Recovery*，[2004.06661](https://arxiv.org/abs/2004.06661v1)，[DOI 10.1109/TSP.2020.2988427](https://doi.org/10.1109/TSP.2020.2988427)。现有 API 摘要/元数据确认 OLSR/IOLSR 近邻；带增广特征的 Schur 增删仍应作为标准 LS 代数，不在此制造新定理。

## 缺口与追补条件

1. AFNC 原文与针对“成对簇/变量投影/正交矩坐标”的窄检索：仅当 C-PAIR 被真实机制与成本证据晋级，再进行最近邻精查。当前不给“首次”结论。
2. 当前代码预算下的低成本模式获取：已有公共闭环工作与内部 branch/OSD 足以判定宽表述重叠；具体新提议器定型后需要补查对应 postprocessing/restart 文献。当前 M-CACHE 是候选实验，非已确证新方法。
3. 完整 TF 非标量/非圆协方差更新：当前 D-FULL 是局部反作用干预，非完整消息方程推导。若其效应存活，须对 vector/bilinear AMP 相关方法进一步比较。

以上缺口是新颖性主张边界，不是停止已授权实验的理由。公开全文与选段保存了读取依据；`fetch-records.json` 记录本轮访问成功/失败，`reused-source-records.json` 绑定已存原文摘录哈希。

## 反馈后窄补检索（2026-10-01）

- L-09：Picinbono & Chevalier，*Widely linear estimation with complex data*，IEEE TSP，1995，[DOI 10.1109/78.403373](https://doi.org/10.1109/78.403373)。Crossref 题名、作者、年份、期刊核实于 `widely_linear_classic_metadata.json`，**只核元数据，未读取该论文证明**。本轮增广 Gaussian SISO 公式独立推导/数值核对，不把经典增广实数表示主张为新理论。
- L-10：*A Perturbation Method for Decoding LDPC Concatenated with CRC*，[DOI 10.1109/WCNC.2007.128](https://doi.org/10.1109/WCNC.2007.128)，公开题名元数据保存在 `remaining_neighbor_metadata.json`。只表明译码扰动/postprocessing 并非新概念，**不能**据题名认定其与本轮 F1 acquisition restart 同算法。未读取完整方法，不作为数值基线或逐式等价证据。
- `remaining_neighbor_metadata.json` 与 `widely_linear_metadata.json` 保留相关性不高的查询结果，未把搜索命中包装为已读文献。当前重启方案仅是原有前端的条件获取，不主张首次 cascade/restart。若论文拟独立宣称新获取算法，还需算法层面最近邻全文比较；当前结果不承担该新颖性主张。
