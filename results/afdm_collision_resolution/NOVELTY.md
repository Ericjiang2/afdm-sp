# 碰撞局部理论的文献边界

2026-10-05。对应本轮 PLAN 第 7 项。结论是**存在值得继续验证的模型特定贡献候选，但本次检索不足以确认首创**。归一化 Gaussian 方向分布、奇异混合的非常规速率、LAN 与有效得分投影均有成熟前史；不能将坐标改写或 Lambert W 反演单独列为创新。

## 检索与实际阅读

原始查询、响应、下载记录及提取文本在 `.mission/20261005_15-21-29-afdm-collision-resolution/literature/`。检索词覆盖 angular central Gaussian、spatial sign covariance eigenvalues、singular mixtures、logarithmic local asymptotics 和 noisy superresolution。使用公开 arXiv API 与 Crossref；网页 connector 的 HTTP transport 不可用，未把它记作成功检索。项目原有 papers/literature 文件名检索没有发现直接匹配。为完成已批准的一手正文核对，保存并阅读了下列五篇公开预印本的相关章节；不是只读摘要，也不是完整逐行复核所有论文证明。

| 文献与版本 | 已读位置和结论 | 与本任务关系及不能移植之处 |
| --- | --- | --- |
| Wróblewska，*A note on some extensions of the matrix angular central Gaussian distribution*，2020 预印本，[arXiv:2010.03243](https://arxiv.org/abs/2010.03243) | §2、Theorem 3、式(6)及其证明：复 Gaussian 矩阵的归一化方向服从 CMACG；形状正比例不改变方向律。Crossref 另返回 2025 出版 DOI [10.24425/cejeme.2025.156674](https://doi.org/10.24425/cejeme.2025.156674)，本次正文读的是 arXiv 版。 | 本项目的归一化方向本身不是新分布。该节使用正定形状；本轮处理秩退化边界、真实标签/PDP 混合和加噪后的观测密度，不能直接把正定方向密度代入碰撞点。 |
| Dürre、Tyler、Vogel，*On the eigenvalues of the spatial sign covariance matrix in more than two dimensions*，[arXiv:1512.02863](https://arxiv.org/abs/1512.02863)，读取 v2 | §2 Propositions 1–3：形状特征值到归一化方向二阶矩特征值的单射、比值收缩、一维积分表达；§3 解释矩反演。 | 说明“归一化后矩仍含形状信息”已有系统理论。正文为实椭圆族，Gamma 形状指数与复二维情形不同；它不是 AFDM 含 nuisance 的完整密度有效信息结论。 |
| Ospald、Herzog，*Short note on a relation between the inverse of the cosine and Carlson’s elliptic integral R_D*，2020 预印本，[arXiv:2001.02203](https://arxiv.org/abs/2001.02203) | §3 式(3)–(5)有对数渐近和 W 的负支反演；§4 式(8)–(16)把结果用于实三维 ACG 的二、四阶矩及轴对称退化极限。式(17)特别警示粗略替换 W 会破坏所需高阶极限。 | 是对“对数退化和 Lambert W 首创”最直接的限制。本轮复二维小模态 Exp 比值、加权观测密度展开和未知 nuisance 的正性并非该文已读章节的结论。两种模型/参数和损失不同，不能仅比较速率符号便宣称优于或重复它。 |
| Heinrich、Kahn，*Optimal rates for finite mixture estimation*，[arXiv:1507.04313](https://arxiv.org/abs/1507.04313)，2015 提交的预印本入口 | 引言、Theorems 3.2–3.3 与 4.3：在正则性和强可识别条件下，以 Wasserstein 损失研究有限混合局部 minimax 速率 n^{-1/(4(m-m0)+2)}；用矩匹配和 LAN 构造困难局部实验，并区分局部 minimax 与逐点速率。 | 不应把“一切碰撞都为 n^{-1/4}”当经典定理。该文自由混合分布估计的参数类/损失与本轮固定归一化双径分离参数不同；本轮尚未得到全参数空间统一 minimax 结论。 |
| Oh 等，*Quantum limits of superresolution in a noisy environment*，PRL 126,120502 (2021)，[DOI](https://doi.org/10.1103/PhysRevLett.126.120502)，读取 [arXiv:2008.11339](https://arxiv.org/abs/2008.11339) | 正文 Proposition 1 及其证明、低分离讨论：激发噪声使两同源分离参数的 QFI 在碰撞处消失。 | 噪声与分离信息退化的邻近机制。量子态/测量族、光子噪声和这里的经典复观测模型不同；不能借其 QFI 上界认证本任务的 Fisher 数值或最优功效。 |

仅核对元数据的背景：Tyler (1987)，*Statistical analysis for the angular central Gaussian distribution on the sphere*，[10.1093/biomet/74.3.579](https://doi.org/10.1093/biomet/74.3.579)；van der Vaart (1998)，*Asymptotic Statistics* 的 LAN 章节，[10.1017/CBO9780511802256.008](https://doi.org/10.1017/CBO9780511802256.008)。本次未获得/阅读两者完整正文，不依赖其未读细节补齐项目证明。2026 年 arXiv:2605.31536 的二维 ACG 普通角矩论文仅检索到元数据/摘要，未据此作覆盖或不覆盖的强判断。

## 可以保留的贡献候选

本轮有依据的候选是这一条完整推理链：**实际条件 PDP 与标签对称的归一化双径概率律 → 稀有小模态的 q log(1/q) 项 → 加噪观测密度的加权 L² 展开 → 合法单侧局部实验 → 对未知中心、功率、噪声仍为正的有效信息**。其中标签对称用于消掉 O(delta) 的大模态漂移，Gaussian 包络承担把矩直觉提升到密度结论的责任。

第二个可清晰陈述的候选是有限 QPSK 信号相位圆上的法向二阶证明：间距方向的法向扩散秩至多二，中心/功率只产生一阶移动，标量噪声产生全法向 Laplacian，因此在实际 N=4 固定分支上无法被这些 nuisance 完全吸收。它证明的是信息存在；没有给出实用下界，也没有证明某个压缩统计量或接收机已保留该信息。该几何证明的通用先例仍需后续专门检索，当前不称新定理首创。

由已证局部实验反演得到 delta_R 的 R^{-1/4}/sqrt(log R) 尺度是模型推论，Lambert W 和局部实验方法本身不是贡献。四基点有限样本研究只负责量级与特征保留诊断，不能用正数估计代替证明，不能从公开基点教师迁移出未知参数部署能力。

## 未覆盖范围与决策

这是定向近邻核查，未系统检索 IEEE/ACM 全库、付费全文、专利、全部非英文文献或所有归一化退化的同义术语；跨领域先例可能遗漏。PDF 提取文本可能丢失排版，已用于比较的关键公式同时以项目独立推导为准。没有形成“查无同类”的全球新颖性证书。

建议继续的依据是已证明的实际模型信息结构，而非未确认的首创标签。下一步应由本轮固定 4/14 维矩的保留结果决定是否值得构造 nuisance 正交统计量；若低阶矩已足够，优先简洁可计算的见证；若不足，再提出新计划。当前不直接扩大八径、训练网格或生产接收机实验。
