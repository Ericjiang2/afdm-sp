# CE复合状态的文献四层映射

核验日期2026-09-15；THEORY-01；主会话自审 **weak**。这是定向原文核对，非穷尽综述。
“相关原文”仅指表中指定部分，不能理解为全篇公式已验证或算法已复现。
本地原件/提取文本在 `ce-state-literature-v1/`；获取失败和HTTP错误保留在抓取manifest。

| 文献与稳定身份 | 支撑/表示 | CE | 检测译码 | 复合分析、读取层级及边界 |
|---|---|---|---|---|
| Otnes–Tüchler，*Iterative Channel Estimation for Turbo Equalization of Time-Varying Frequency-Selective Channels*，TWC 2004，DOI [10.1109/TWC.2004.837421](https://doi.org/10.1109/TWC.2004.837421) | 时变频选信道，具体基模型待全文核对 | turbo迭代CE的历史近邻 | turbo equalization | **仅Crossref元数据**；不编造式号、先验形式或等价性。不能把一般迭代CE视为新问题。 |
| Schniter，*A Message-Passing Receiver for BICM-OFDM over Unknown Clustered-Sparse Channels*，JSTSP 2011，DOI [10.1109/JSTSP.2011.2169232](https://doi.org/10.1109/JSTSP.2011.2169232)，[1101.4724v3](https://arxiv.org/html/1101.4724v3) | GM2-HMM簇稀疏tap先验 | GAMP的软信道估计 | §III-C式(31)/(32)对软信道积分形成symbol likelihood；式(33)/(34)排除当前比特输入先验，送SISO译码 | **相关原文**§III-C、式31–34及迭代终止段：区分turbo/equalizer/GAMP/decoder多层迭代。排除当前因子不等于消除loopy历史自响应；BICM-OFDM不是本项目全SP模型。 |
| Parker–Schniter–Cevher，*Bilinear Generalized Approximate Message Passing*，TSP 2014，Part I DOI [10.1109/TSP.2014.2357776](https://doi.org/10.1109/TSP.2014.2357776)，Part II [10.1109/TSP.2014.2357773](https://doi.org/10.1109/TSP.2014.2357773) | 未知矩阵A/X的独立条目先验 | 双线性近似BP，分离先验/似然 | 可扩展turbo机制，但不是本项目LDPC接收器 | **相关原文PDF**实际取得[1310.2632v3](https://arxiv.org/pdf/1310.2632v3)，封面2014-06-06；式(1)–(3)分离分布、§II-A式(4)–(6)后验及摘要。独立条目、大维CLT/Taylor近似不能直接成为有限相关AFDM字典、自适应S与LDPC闭环的严格状态演化定理。v2 HTML的406失败未隐去。 |
| Kanazawa等，*Superimposed Pilot-Based OTFS: Will it Work?*，[2501.15935v3](https://arxiv.org/html/2501.15935v3) | OTFS导频/整数DD表示 | §IV-C算法1、式(28)数据消除 | 式(29)导频消除、式(30)–(32)译码LLR至软符号副本，5G LDPC；uncoded/coded切换 | **相关原文**§IV及§V切换设置。软重建和固定切换已有；噪声、导频模式、功率/吞吐不同。v3式(31)提取文本写为logit后sigmoid，并未显式写跨符号归一化；本表只核对其原文操作位置，不为该表达式的PMF归一性背书，不照搬为本项目合法后验。 |
| “Chi 2026 AFDM MAMP” | 未核实 | 未核实 | 未核实 | **身份缺口**：arXiv请求429，Crossref宽搜及精确标题搜索未找到可验证目标。普通Liu等MAMP结果与其他Chi光通信结果不是这篇文献。不补造作者/DOI/公式，也不据检索失败断言论文不存在。 |
| Ranasinghe等，*Joint Channel, Data and Radar Parameter Estimation for AFDM Systems in Doubly-Dispersive Channels*，TWC 2025，DOI [10.1109/TWC.2024.3510935](https://doi.org/10.1109/TWC.2024.3510935)，[2405.16945v3](https://arxiv.org/html/2405.16945v3) | §III式(27)/(28)使用Γp；延迟/多普勒跨多帧慢变信息，RPE辅助部分另述 | §III-A PBiGaBP，式(29a/b)符号与增益软副本方差、后续soft IC | 给定参数化Γp下的联合信道增益/数据估计 | **相关原文**§III导言、式27–29、§III-A步骤。Γp的长期信息假设必须披露，不是完全未知路径参数的公平免oracle基线；本轮不启动其连续参数估计。 |
| Zemen–Mecklenbräuker，*Time-variant channel estimation using discrete prolate spheroidal sequences*，TSP 2005，DOI [10.1109/TSP.2005.853104](https://doi.org/10.1109/TSP.2005.853104) | DPSS子空间表示的历史近邻 | 时变CE | 本轮未核对译码接口 | **仅元数据**；未读全文模型/定理，不提供未经核对的式号。只能据题目身份定位子空间方向，不能据此认定当前整数邻域最佳。 |
| Tipping–Faul，*Fast Marginal Likelihood Maximisation for Sparse Bayesian Models*，AISTATS **2003**，[作者PDF](https://www.miketipping.com/papers/met-fastsbl.pdf) | 固定字典下顺序增删基；实值Gaussian模型 | 式(2)–(4)线性观测/iid Gaussian噪声/独立权重先验，式(6)后验 | 无本项目检测译码 | **相关原文**§2–3；第5页已渲染目检。式(15)–(19)C去一基的证据分解，$s_i=\phi_i^TC_{-i}^{-1}\phi_i,q_i=\phi_i^TC_{-i}^{-1}t$；式(20)/(21)：$q_i^2>s_i$时\(\alpha_i=s_i^2/(q_i^2-s_i)\)，否则∞。PDF排版日期2006不是出版年；证据增益不等于本项目Schur代理或FER收益。 |
| Zheng等，*Channel Estimation for AFDM With Superimposed Pilots*，[2404.10232v1](https://arxiv.org/html/2404.10232v1) | SP格点列/阈值支撑 | 式(18)对信道与数据平均的有效白协方差；式(19)MMSE；Lemma3式(20)正交导频列 | §III-D迭代CE/MP数据检测，式(23)附近 | **相关原文**§III、Appendix C式(29)–(31)。附录先在高导频功率下忽略先验precision，再以固定trace最小化trace inverse，不能无条件外推到任意有色同y反馈风险；正交CE列不是本轮新贡献。 |
| Zhang等，*AFDM-Enabled Integrated Sensing and Communication: Theoretical Framework and Pilot Design*，JSAC 2026，DOI [10.1109/JSAC.2025.3609766](https://doi.org/10.1109/JSAC.2025.3609766)，[2502.14203v2](https://arxiv.org/html/2502.14203v2) | §IV理想模糊函数与可估域 | Theorem4：整数2c1N下理想模糊函数给正交列；Appendix F式(77)–(79)关联 | 非本项目有限LDPC闭环保证 | **相关原文**Theorems4/5、式(51)–(55)、Appendix F/G。Theorem5限定N为2幂、2c1N为适配的2幂、Q及CAZAC相位；本项目固定2c1N=5，不能直接宣称落在其条件内，也不能忽略其近邻性。原文式(78)后差分Doppler的文字有疑似笔误，采用式本身并保留版本。 |
| Luo等，*Joint Sparse Graph for Enhanced MIMO-AFDM Receiver Design*，[2503.19143v1](https://arxiv.org/html/2503.19143v1)（JSG） | 给定有效H的MIMO图；E-JSG稀疏化另有设计 | 所读推断段未给本项目SP联合CE | §III式(14)符号后验；§III-D3式(38)–(43)VI extrinsic与LDPC prior交换；§IV E-JSG合并位图 | **复用原件并重读相关段落**，`literature/jsg.txt`为保存HTML，新增纯文本提取。AFDM图+LDPC/外信息/去交织已有；给定H的推断公式不足以认定其所有实验都是perfect CSI，更不等价于本项目SP估计回路。 |

## 对本轮主张的约束

1. 支撑坐标：固定整数展开、DPSS或SBL都是已有表示/选择工具；本轮须用实际遗漏风险与同容量干预解释其效果。
2. CE坐标：仿射正规方程、Schur和Q迹恒等式是标准代数。增加真实previous、条件均值与交叉项修正了本项目的分析口径，尚不自动构成创新定理。
3. 检测译码坐标：外信息排除、软符号重建、固定刷新和JSG均有近邻；收益须超过强经典参考并核对完整调用成本。
4. 复合分析：当前能做的是固定实现的完整状态与逐样本风险、预先登记的经验预测。没有已核验文献替本实现证明标量闭合、双稳态或普遍阈值。

未完成的文献项为Otnes/Zemen全文、Chi准确身份及最终候选形成后的窄范围最近邻比较。
这些缺口明确列账；不虚构引用来关闭它们。本行交付允许“全文或明确缺口”，不代表最终论文引用审计通过。
