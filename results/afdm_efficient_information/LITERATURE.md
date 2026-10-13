# 得分压缩与实际先验：逐命题近邻核对

阅读日期：2026-10-05。以下是对具体构造的一手近邻核对，不是系统性首创证明。全部预定数值研究及近碰撞加密已运行；本文件按这些结果限定可保留的贡献。全文原件、提取文本及失败请求保存在本轮Mission的literature目录；外部论文的实验数字未在本项目复现。

| 本轮对象 | 实读一手来源与公式/段落 | 重叠与本轮必须补的证据 |
|---|---|---|
| 使用完整似然得分压缩有限字母观测 | Alsing & Wandelt, *Generalized massive optimal data compression*, 2018，[全文](https://arxiv.org/html/1712.00012)，§2.2式(4)—(7)、§2.3式(9)—(11)、§5 | 得分压缩及Fisher scoring早已有明确理论。文中最优性是在预定fiducial点的局部Fisher意义，§5说明压缩多峰和非渐近失败。本轮必须处理q单侧边界、实际先验非正则支路和未知nuisance；不能将“用score”作为创新，也不能从局部信息直接宣称全局估计有效。 |
| 消除nuisance的一阶敏感度 | Alsing & Wandelt, *Nuisance hardened data compression for fast likelihood-free inference*, 2019，[全文](https://arxiv.org/html/1903.01473)，§3.1、§4、§5式(8)—(12) | 式(12)明确给出 t_theta-F_theta,eta F_eta,eta^(-1)t_eta。该文的nuisance边缘化、局部Laplace推导与本轮频率学有效得分要区分；不把对nuisance指定先验后边缘化视为剔除任意未知nuisance的同一对象。奇异块、本轮条件期望压缩与投影顺序、有限样本校准需单独核验。 |
| 从隐变量或完整教师回归可观测得分 | Brehmer, Louppe, Pavez & Cranmer, *Mining gold from implicit models to improve likelihood-free inference*, 2018，[全文](https://ar5iv.labs.arxiv.org/html/1805.12244)，§4.1式(5)—(8)、§4.3式(13)及SALLY/SALLINO | 平方损失的最优预测为条件期望，joint score回归得到observable score，以及局部一维方向压缩均为既有方法。本轮有限特征/岭回归只给近似；得分MSE不是完整特征Fisher，也不能把隐藏PDP标签输入部署推断。 |
| 协方差加权的低维线性摘要 | Heavens, Jimenez & Lahav, *Massive Lossless Data Compression and Multiple Parameter Estimation from Galaxy Spectra*, MNRAS 317, 965–972, 2000，[全文](https://ar5iv.labs.arxiv.org/html/astro-ph/9911102)，§2式(2)—(8)及后续参数无关噪声假设 | MOPED多参数Fisher保持早已存在，标准结论依赖Gaussian观测与参数无关协方差的特定结构。本轮非Gaussian双径混合和参数相关实际推前不满足直接套用条件；协方差白化、矩加权与投影本身不构成新颖性。 |
| 高阶统计、Hilbert有效信息与GMM | 前轮已实读的Hyvarinen/Oja 2000、Tsang 2019、Hansen 2013讲座；原文和逐式映射见前轮LITERATURE.md | 原理沿用，不重复包装。新的嵌套多项式有时只是同一统计量sigma代数内的线性空间扩展，不能把回归改善等同新增信息。 |
| 圆对称观测的相位规范、rrH与充分统计量 | 本轮按参数无关全局相位群作用作直接因子分解；专门AFDM群不变近邻尚未完整排查 | 这是经典群不变/充分统计思想的应用。O(N)代表元可避免显式NxN存储，但充分性不保证有限回归性能，也不自动构成新算法首创。相干均值或非圆噪声须作为失效边界。 |
| 实际归一化与PDP边缘化 | 固定生成器源码及本轮PRIOR推导；Tyler 1987 ACG文献仅核到DOI元数据，未读正文 | Gaussian方向归一化、angular central Gaussian密度不是新概念；不能把实值ACG公式无证明套到复数情形。需独立推导复球面权重、离散PDP条件权重及标签混合，并分别验证积分与得分。特定生成器的条件切片不是完整八路径总体。 |
| AFDM迭代检测、非Gaussian符号约束与复杂度 | 前轮已实读Yi等2026 dual-domain EP，arXiv:2603.29218；Luo等2025 Joint Sparse Graph，arXiv:2503.19143 | 本轮未新增生产接收机，不能把更保真的小模型似然或更好的局部score近似当作已超过现有AFDM检测方法。新颖性与部署性能须由具体结果支持。 |

## 当前裁决

从拟创新主张中排除：score compression、nuisance hardening、score回归、GMM、相位规范本身、q换元和标准重要性权重。当前四维得分模型没有显示接近完整似然的检测能力；迁移也没有建立同精度推断优势，因而不能保留这些性能创新主张。

可继续核查的模型特定结果是：冻结G0归一化和离散PDP条件法则如何产生平台、非平台碰撞的可观测q log(1/q)项及有限q-DQM障碍；正规分支上实际PDP边缘有效信息的数值正证据；固定谱坐标正权加密如何解决同一近碰撞观测的积分不收敛。最后一项只解决求积误差，仍未通过有限样本正信息判据。具体推导、原始失败与新验证见PRIOR_THEORY.md、PRIOR_RESULTS.md及prior_refinement_v1。

这几项是已获得特定证据的候选研究内容，不是已证明文献首创。尤其归一化秩退化导致的对数渐近与端点求积本身可能有更广的既有理论；本轮没有完成这条专门近邻的系统检索，因此不作“首次”“普遍新定理”判断。O(N)完整相位代表元与外积的等价及表示成本结果属于经典不变性应用，不能借此宣称低成本学习推断成立。

原始Fisher、有效Fisher、线性矩下界、精确压缩信息、回归风险与有限样本检测/估计效用分开。文献中的渐近“无信息损失”不替代本轮独立训练/校准/测试、复合零假设逐点虚警率及实际先验验证。

## 失败与未覆盖部分

首批Alsing两篇ar5iv请求超时，第二次arxiv HTML和ar5iv全文成功。Pollard arXiv:1107.3797的ar5iv返回“no content available”，作者站点TLS证书校验失败，因此未把它列为已读一手正文。AFDM/Fisher/score的arXiv API定向查询超时，不能由此推断不存在相关论文。Tyler DOI 10.1093/biomet/74.3.579仅有元数据，未冒充阅读全文。完整检索请求与响应身份见LITERATURE_SOURCES.json及Mission/literature/retrieval_v*.json。
