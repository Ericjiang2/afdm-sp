# 逐命题近邻与新颖性边界

检索及正文阅读：2026-10-04—05。本轮做针对性近邻核查，不是系统综述，也没有证明任何命题为首次提出。外部论文的实验结果没有在本项目复现。检索原件、失败请求、正文提取和哈希位于本轮 Mission 的 `literature/`。

| 本轮命题或方法 | 已实际阅读的一手来源与位置 | 重叠、假设差异与裁决 |
|---|---|---|
| 二阶矩不能保留全部可辨识信息；用四阶统计 | Hyvärinen 与 Oja，*Independent Component Analysis: Algorithms and Applications*，Neural Networks 13，2000；[作者正文](https://www.cs.helsinki.fi/u/ahyvarin/papers/NN00new.pdf)，§§3.2—3.3、4.2.1，式(16)—(19) | 非Gaussian性、四阶累积量、白化后仍需高阶信息是经典原理。ICA的线性独立源混合与本轮随机双径乘上有限字母波形不同；可保留的是指定DAFT/QPSK模型的精确T系数、nuisance正交及边界证明，不能把“使用四阶”称为创新。 |
| nuisance投影与矩信息界 | Mankei Tsang，*Semiparametric estimation for incoherent optical imaging*，Physical Review Research 1, 033006，2019；[正文](https://arxiv.org/html/1906.04578)，§III式(8)—(17)、Appendix A | 文中明确建立Hilbert内积、score切空间、Cauchy–Schwarz和有效影响函数的投影。光子Poisson模型不同，但投影工具是共同的经典统计结构。本轮新增核验落在有限QPSK混合的q单侧L2正则性及具体统计量，不是发明有效信息。 |
| 全协方差加权矩/GMM估计 | Lars Peter Hansen，*Uncertainty Outside and Inside Economic Models*，2013 Nobel Prize Lecture；[官方正文](https://www.nobelprize.org/uploads/2018/06/hansen-lecture.pdf)，式(3)后的GMM与效率界讨论，引用Hansen (1982b) | 由矩条件构造估计器、组合多个矩以及效率界均已有基础。1982原论文正文的候选链接本轮未取到，不冒充已读；作者讲座明确追溯该结果。本轮仅实施冻结lag和工作协方差的开发估计，不保留“GMM本身新颖”的主张。 |
| 相对似然积分与比值误差优化 | Meng 与 Wong，*Simulating Ratios of Normalizing Constants via a Simple Identity: A Theoretical Exploration*，Statistica Sinica 6, 831–860，1996；[期刊全文](https://www3.stat.sinica.edu.tw/statistica/oldpdf/A6n43.pdf)，式(2.3)—(2.5)、§III式(3.1)—(3.5)、§IV | 归一化常数比、相对均方误差、log比值渐近误差和依赖未知比值的最优权函数早已有之。其主公式从两端分布取样；本轮从共同proposal估计两个bit积分，具体方差含协方差项。概率对象不同不自动构成新颖性；LLR误差界是标准均值定理/delta方法应用。 |
| 支持覆盖、重叠与ratio sampling | Radford Neal，*Estimating Ratios of Normalizing Constants Using Linked Importance Sampling*，2005预印本；[正文](https://arxiv.org/html/math/0511216)，§1式(2)—(4)及LIS构造 | 已讨论支持必须覆盖、重要性采样在低重叠时失效、bridge比值和关联采样。本轮的独立pilot加防御混合proposal只作为受控实现候选；不声称共同节点、测度校正、正权或防御混合本身首创，也未实现或比较完整LIS。 |
| AFDM dual-domain / cavity /低复杂度更新 | Qin Yi 等，*A Novel Low-Complexity Dual-Domain Expectation Propagation Detection Aided AFDM for Future Communications*，2026预印本；[正文](https://arxiv.org/html/2603.29218)，§§III-B2—B5、III-C—D | 已有Gaussian site/cavity/星座矩匹配及准带状LU。本轮在指定随机路径增益先验上讨论信息和bit积分；不能把转时域、LU或cavity本身写成贡献。复用此前保存全文及逐公式核查。 |
| AFDM检测译码联合结构 | Qu Luo 等，*Joint Sparse Graph for Enhanced MIMO-AFDM Receiver Design*，2025预印本；[正文](https://arxiv.org/html/2503.19143)，§§III-A—C、IV-A—B | 联合LDPC图、BP/EP和extrinsic LLR已有直接近邻。本轮只做合法小码枚举和只读生产桥接，没有新的联合接收机，也没有FER优势。复用此前保存全文。 |
| 实际归一化先验的零信息平台与G1无限矩 | 本项目冻结 `afdm_env.py`、`production_prior.py`、G1物理观测与本轮 `PRIOR.md` | 这是对特定生成器“物理clip→权重归一化→虚拟clip/prune→G0 Frobenius归一化→G1复用”顺序的可复现数学诊断。球面投影的Beta近零阶和核空间消去是经典数学；尚未完成对所有angular/elliptical分布文献的排查，因此不将该诊断升格为普遍首创。 |

检索使用了arXiv API，并保存了“AFDM AND higher order”结果；该查询命中高阶QAM等歧义对象，不能用少量命中证明不存在相关工作。Tsang关键词查询定位到2019正文和2026新预印本；后者HTML未取到，不能声称已经覆盖最新理论。Hansen旧正文、Owen教材链接等访问失败均记录，未用失败请求充当阅读证据。一个错误ID命中的跨视角定位论文已排除。Google返回JavaScript页面、Bing返回不相关结果，均没有纳入科学证据。

可以保留的研究产出是：指定控制模型的可验证信息缺失定理；实际生成器的精确失效区间与矩存在边界；具有完整失败分母和成本口径的观测估计、LLR积分裁决。它们具备明确内容，但其论文新颖性仍待更全面的最直接领域文献比较。四阶统计、q坐标、nuisance投影、GMM、共同节点和重要性权重本身均从拟创新主张中排除。
