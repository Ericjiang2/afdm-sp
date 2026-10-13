# 本轮直接近邻补查

检索日期：2026-10-04。复用上一轮已读的一手论文与[逐公式比较](../../experiments/afdm_structured_inference_20261003/LITERATURE.md)，本轮补读此前仅有摘要的两篇全文。原始 HTML、arXiv 元数据、文本提取及 SHA-256 均在当前 Mission 的 `literature/retrieval.json`。这是有针对性的重叠检查，不是系统性新颖性证明。

| 论文与阅读位置 | 实际方法 | 对本轮的约束与差别 |
|---|---|---|
| Qin Yi 等，*A Novel Low-Complexity Dual-Domain Expectation Propagation Detection Aided AFDM for Future Communications*，[arXiv:2603.29218](https://arxiv.org/html/2603.29218)，2026 预印本，§§III-B2—B5、III-C、III-D | 在给定有效信道矩阵的检测模型内，使用 Gaussian site、cavity 和星座矩匹配。利用时域或 AF 域准带状结构进行 LU；§III-B5 进一步以带宽参数近似三角逆，§III-D 给出含 FFT 与迭代数的复杂度。 | “转时域”“利用 CPP 有限 delay 稀疏性”“LU 降本”均已有直接 AFDM 近邻。本轮的对象是每个随机增益节点下的归一化条件似然及目标块方差 downdate，采用稀疏因子直接求解，未截断逆矩阵。但每个节点都要付出代价；这个不同对象尚不等于新颖性或完整接收器优势。 |
| Qu Luo 等，*Joint Sparse Graph for Enhanced MIMO-AFDM Receiver Design*，[arXiv:2503.19143](https://arxiv.org/html/2503.19143)，2025 预印本，§§III-A—C、IV-A—B | 从给定信道的检测后验与 LDPC 图构造联合稀疏图；包含离散 BP、Gaussian EP、extrinsic LLR、按位线性星座编码与弱信道边近似。 | 联合检测译码、星座支撑、Gaussian 消息和外信息排除都不是本轮可以笼统声称的新机制。本轮聚焦不确定共享增益积分的近似次序及其误差；并未交付比该联合图更好的完整算法。 |

两篇的公式分别把有效信道矩阵作为检测似然里的给定量；所读更新没有执行本轮的共享随机路径增益积分。这个差别只限于所核公式，不能由此断言整篇论文未讨论其他信道情形。论文自己报告的 BER 与复杂度未在本项目复现，不作为本轮结果。

其余直接近邻继续限制贡献的表述：P-BiG-AMP 已处理双线性未知增益/数据及近似消息；AFDM PBiGaBP 已有导频辅助联合推断和 cavity；AFDM SBL 已有 Gaussian 增益消元、log determinant 与几何导数；confluent Prony 已有碰撞和导数坐标；有限指数族与正权求积是经典概率结构。

因此，本轮能争取的具体研究贡献是：对指定先验和合法 cavity 给出可验证的近似误差/失效条件；对含 nuisance 的碰撞组合量给出有效信息结果；或者找到在相同概率对象、误差与完整成本下更好的积分方法。当前执行首先补证据，不能把这些目标写成已证明的新颖性。
