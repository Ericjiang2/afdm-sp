# Research: 三条经典数学联系及不可直接迁移的边界

- Query: 本轮盲不变量、近碰撞估计和奇异检测分别与双谱反演、超分辨率、仅备择下存在 nuisance 的经典理论有什么可核对联系？
- Scope: mixed；三篇指定原始文献的有限阅读与项目数学稿对照，不是全面综述、新颖性认证或完整文献证明审计。
- Date: 2026-10-06
- Active task: `.trellis/tasks/10-05-method-advantage`，本轮范围见 `ROUND.md`。
- Method: 沿用 `research-lit`，来源限定为指定 primary 材料与必要勘误；只写本文，不改已送审的数学稿，不采样、不 SSH、不安装依赖。

## Findings

三条联系支持同一研究顺序：**先确定不变量能识别什么，再研究逆映射的病态程度，最后为奇异零假设建立检验极限。** 它们不提供可直接复制到本轮 AFDM 模型的样本指数或最优率。

| 原始文献 | 已实际读取的范围 | 对应本轮问题 |
|---|---|---|
| Bendory, Boumal, Ma, Zhao, Singer，*Bispectrum Inversion with Application to Multireference Alignment*，IEEE TSP 66(4), 1037–1050 (2018)；[arXiv v2 全文](https://arxiv.org/html/1705.00641v2) | 2017-10-06 v2：§I 观察模型、§II 式 (II.5) 与命题 II.1–II.3、附录 A 的递推相位和局部 Lipschitz 论证。未审全部算法证明。 | 高阶相位闭合、循环群歧义、非零条件与点态稳定性。 |
| Batenkov, Goldman, Yomdin，*Super-resolution of near-colliding point sources*，Information and Inference 10(2), 515–572 (2021)，[DOI:10.1093/imaiai/iaaa005](https://doi.org/10.1093/imaiai/iaaa005)；[arXiv v2 全文](https://arxiv.org/html/1904.09186v2) | 2020-01-24 v2：§1.1–1.3、定理 2.10 的假设/结论、§5.4.1 命题 5.12–5.13、附录 A 的 Prony 表示与递推。勘误仅读到出版社 extract，未读到完整修订项。 | 精确反演和稳定恢复的区别、碰撞 Jacobian 与逆映射放大。 |
| R. B. Davies，*Hypothesis testing when a nuisance parameter is present only under the alternative*，Biometrika 64(2), 247–254 (1977)，[DOI:10.1093/biomet/64.2.247](https://doi.org/10.1093/biomet/64.2.247) | [作者摘要页](https://www.statsresearch.co.nz/rbd_abstracts.htm) 的 1977 条目；搜索工具返回的[原论文扫描件](https://www.stats.org.uk/statistical-inference/Davies1977.pdf) p.252、p.254 提取文本。未完整读取 §2 正则条件。 | 零假设下消失的参数、非标准检验与搜索方向；不能直接引用常规 Wilks 结论。 |

### 1. 高阶相位闭合：与 bispectrum inversion 的联系

**原文事实。** MRA 观察随机循环平移的同一个信号加 Gaussian 噪声。其双谱将三个 Fourier 系数相乘，使平移相位抵消。命题 II.2 对 Fourier 系数全非零的固定信号给出局部稳定逆，常数依赖信号；附录 A 通过 N 次根和递推相位构造平移等价类。[原文 §II 与附录 A](https://arxiv.org/html/1705.00641v2)

**本轮的具体连接（本文解释）。** `BLIND_INVARIANTS.md` 的 balanced 四阶张量在 `i−j+k−l=0 mod N` 上留下四项相位闭合。比较两个候选的相位比，得到循环群同态，再由已知物理 Fourier mask 选定 character。这与双谱的“先平均不变量，再恢复商空间对象”是同一个研究动作。局部连续根支及非零幅度的作用也相同：它们保证局部逆可构造，却不能给趋近零点的统一常数。

**不能迁移之处。** MRA 的隐藏变量是平移；本轮隐藏变量是每坐标独立 QPSK，观察是 `diag(H) Aᴴ S+n`，且采用 2+2 四阶 cumulant，不是三阶 bispectrum。本轮 balanced 矩的全局连续相位自由度还大于实际完整 QPSK 分布的 C4 自由度。不能照搬 MRA 的噪声—样本数关系、算法收敛或其支撑定理来覆盖 N4 AFDM；两者的不变量阶数、噪声矩和比较参数类均不同。

**可用直觉。** 如果不变量的代数逆已给出唯一商类，下一步应量化逆映射随小幅度和缺失约束如何恶化，而不是把“相位难”当成没有信息。

### 2. 碰撞奇异性：与 near-colliding super-resolution 的联系

**原文事实。** 该文观察已知带宽内的连续 Fourier 数据，误差按统一绝对界控制；源节点为实数、幅度允许复数。其证明将观测化为选定间隔的 Prony 型系统，再分析局部单射性、Jacobian 逆和误差集合；附录 A 明确区分相异非零节点的精确 Prony 反演与受扰动稳定性。[原文 §1、§5.4.1、附录 A](https://arxiv.org/html/1904.09186v2)

**本轮的具体连接（本文解释）。** `DETECTION_VS_ESTIMATION.md` 先消两个复增益和一个实中心，再测量间距方向的残余长度。它与近碰撞 Prony 的共同对象是**逆映射在节点合并处的奇异几何**：低阶矩可以被 nuisance 改变所匹配，只有更高阶曲率分辨剩余差别。完整 H 唯一不代表噪声下可稳定估计；正的点态 Fisher 信息也不足以排除邻域内的精确多解或弯曲退化路径。

**不能迁移之处。** 该文的误差输入是直接 Fourier 测量的确定性扰动，本轮先有未知 QPSK 的统计反演，再进入实际截断 Dirichlet 曲线；还存在实际 PDP、Gram 总归一化及已知有限 mask。三 atom 中的同 H 多节点表示，不是增加测量精度能解决的条件数问题。不能设 `ε=T^{-1/2}` 就把外文 minimax 率变成本轮 δ 的最优估计率；须先证明所用观测实验、误差范数、参数邻域和逆映射条件一致。

**勘误与指数裁决。** [勘误 DOI:10.1093/imaiai/iaaa015](https://academic.oup.com/imaiai/article-abstract/10/2/721/5868613) 的出版社 extract 说明排版引入了错误，在线发表日为 2020-07-10，卷期页为 10(2):721 (2021)。完整修订项没有取到。可达 arXiv v2 的摘要与正文对于节点误差的幂次文字并不一致；本记录不选取或转引任一具体超分辨率指数，也不臆测勘误恰好修正了哪一项。

**可用直觉。** 研究“能否分开”前，先说清是检测非单径、恢复无序节点、还是控制相对间距误差；不同损失对应不同奇异方向。

### 3. 零假设下消失的 nuisance：与 Davies (1977) 的联系

**原文事实。** Davies 讨论一个参数为零时，分布不再依赖另一个 nuisance 的检验。作者明确指出通常的渐近检验不能直接使用；在适当条件下可转化为 Gaussian 过程问题。读到的 p.252–254 还分别讨论显著性后的 nuisance 置信区域和离散参数搜索的上穿越控制。[作者摘要](https://www.statsresearch.co.nz/rbd_abstracts.htm)；[原论文扫描件](https://www.stats.org.uk/statistical-inference/Davies1977.pdf)

**本轮的具体连接（本文解释）。** 以 `a=g₋+g₊`、`b=g₊−g₋` 表示实际两径：δ=0 时 `w(μ−δ)g₋+w(μ+δ)g₊=a w(μ)`，b 在信道中消失；δ>0 时它通过分裂方向重新进入。这解释了为何零假设 nuisance 切空间与沿 δ>0 接近它的切空间不必相同。此处消失的是**增益拆分方向**，不能误称 μ 在单径零假设下也不存在。

**不能迁移之处。** 本轮 C2 是固定二维观察对比的 studentized 均值，其 χ² 极限来自相应 CLT；它不是已经证明属于 Davies 的 supremum Gaussian-process 检验，也不能拿该论文替代本轮协方差或功效证明。`COHERENT_LIMIT.md` 的 prior 混合还有重尾随机平移：有界功效的换序与二阶矩的换序不同，不能仅凭“Gaussian 极限”就宣称普通有限信息 LAN。未知 gain 的确定性参数检验与按真实 PDP/gain prior 平均的检验，亦是两个不同的比较对象。

**可用直觉。** 先问零假设到底保留哪些参数，再选择局部坐标和检验统计量；将备择中全部参数直接放进一个常规 Fisher 矩阵，会掩盖这个结构变化。

## Files Found / Code Patterns

相对本目录：

- `BLIND_INVARIANTS.md:141`：完整 balanced K 的 character 纤维；`:176` 的 `Q+r⊆S` 支撑判别；`:199` 的 C4 完整分布推论。
- `DETECTION_VS_ESTIMATION.md:70`：先复增益投影，再实中心投影；`:412` 的匹配低阶矩两点构造；`:477` 的 null/alternative 切空间区别。本次读开头完整定义和上述索引定位，不将这份稿件冒称已由本文独立证明复核。
- `COHERENT_LIMIT.md:25`：真实固定块观察与 prior；`:230` 的有界函数混合换序、`:306` 的截断二阶矩路径。本次读开头定义与索引，不代替其专门数学审查。

实际源码沿用上一研究 topic 已核对的 `experiments/sp_afdm_frozen_20260920/src/physical.py:87`、`experiments/afdm_coherent_structure_20261006/core.py:70` 与 `experiments/afdm_shared_channel_20261004/production_prior.py:46`；本文没有改换 DAFT、采样单位或 Gram。

## Related Specs

沿用本轮已读 `.trellis/spec/research-protocol.md`、`.trellis/spec/backend/bounded-mathematical-studies.md`、`.trellis/spec/backend/structured-inference.md`：外部理论是背景证据，不能替代当前冻结模型的证明、正式运行或科学主张准入。使用 `research-lit` 的来源/访问深度区分，不创建另一个状态源。

## Caveats / Not Found

- MRA 的 PMC 页面返回浏览器检查；改读公开 arXiv v2 HTML，未绕过访问控制。Batenkov 论文的 OUP 正文/勘误直接读取失败，原论文改读公开 arXiv v2；勘误只有搜索返回的出版社 extract。
- Davies 的扫描件网页直取多次超时；作者版本可流式取得，但现有 `pdftotext` 只返回分页符，未将这种提取算作全文阅读。本文只使用确实读到的作者摘要和原扫描件 p.252、254 搜索提取文本；不声称已核查 §2 全部正则条件。没有保存 PDF 或安装 OCR。
- 未核对所有后续修订、相关近年成果、证明的全部边界条件；没有 novelty certification。特别是超分辨率具体指数在完整勘误未读前不进入本轮主张。
- 三条连接主要支持问题分解和证明路线，不能单凭类比给出 AFDM 的 receiver、decoder、FER、CONF 或最优样本复杂度结论。
