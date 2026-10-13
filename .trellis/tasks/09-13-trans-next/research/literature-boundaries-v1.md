# 最近邻文献与本轮研究边界（核验：2026-09-13）

普通软译码反馈、SP 数据辅助 CE、稀疏图以及固定迭代切换均不能单独承载新颖性。本轮局部 CE 响应诊断提供了可证伪的机制测量，但还没有完整风险收益；CPU 剖析也尚未证明一种新接收算法。

下表是服务于当前候选取舍的定向核验，不声称穷尽文献或完成最终新颖性审查。全文阅读指所列模型/算法/实验相关段落，未声称逐式复核全部证明。

| 原始来源与已核验内容 | 与当前项目的关系 | 不可混同的边界 / 下一步 |
|---|---|---|
| Zheng et al., *Channel Estimation for AFDM With Superimposed Pilots*，2024；[作者全文](https://arxiv.org/html/2404.10232v1)。SP 导频布置、CE/检测迭代已经存在。 | 直接 AFDM-SP 背景参考；“引入 SP”“迭代消除数据导频干扰”不是当前新增贡献。 | 原论文导频/估计器设置须保持身份；当前通用 ridge 不等于该公开基线复现。 |
| Kanazawa et al., *Superimposed Pilot-Based OTFS: Will it Work?*，arXiv v3，2026-02-24；[全文 §IV–V](https://arxiv.org/html/2501.15935v3)。译码软符号重建，uncoded/coded 迭代切换，5G LDPC，统一功率口径与吞吐量。 | 编码 SP 迭代和固定切换的强最近邻。REFRESH4/47 应作为经典控制，不包装为新方法。 | OTFS 导频图案与 AFDM 全叠加设置不同；该文复杂度公式不是本项目 CPU 实测，不能跨图直接比较曲线。 |
| Luo et al., *Joint Sparse Graph for Enhanced MIMO-AFDM Receiver Design*，2025；[全文 §II–III](https://arxiv.org/html/2503.19143v1)。MIMO-AFDM 有效 H、BP/EP 与码图联合推断。 | “稀疏 AFDM 图+译码”已是直接近邻，结构化图实现必须与这类已有设计区分。 | 所读推断式针对给定有效 H 的符号后验；这不足以凭空认定所有实验为 perfect CSI，也不能据此声称本文完成 SP 联合 CE。 |
| Hawkins et al., *Iterative Soft-MMSE Detection Aided AFDM and OTFS*，IEEE OJVT 6:2944–2959，2025，DOI 10.1109/OJVT.2025.3623883；[作者机构记录及摘要](https://eprints.soton.ac.uk/506882/)。先验加权 soft-MMSE、RSC/RSC-URC、EXIT 分析与等效波形比较。 | AFDM 软输入检测与码反馈不是空白；应有强软输入检测器比较。 | 当前核验为机构元数据/摘要；未声称全文算法已逐项复现。不能把其 RSC 收益移植为本项目 LDPC 收益。 |
| Li & Yu, *Doubly-Iterative Sparsified MMSE Turbo Equalization for OTFS Modulation*，IEEE TCOM，2023，DOI 10.1109/TCOMM.2023.3237243；[作者预印本](https://arxiv.org/abs/2207.00866)、[作者代码](https://github.com/Alga53/DISMMSE-Turbo-Equalizer-for-OTFS)。 | 有公开实现的软输入稀疏 MMSE turbo 近邻，适合核验外信息和资源口径。 | 当前只验证论文身份/代码入口，尚未完成代码移植或算法等价。AFDM 的 H、导频抵消、噪声及 LDPC 接口适配须单列，不冒称原文复现。 |
| Luo et al., *Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System*，2026-07；[全文 §III 算法1及式(15)–(21)](https://arxiv.org/html/2607.18881v1)，[作者摘要页](https://arxiv.org/abs/2607.18881)注明 Accepted by IEEE TCOM。D-GESBL/D-GAMP-GESBL 用检测数据更新字典并处理分数时延/多普勒。 | 直接否定“数据加入伪导频字典”本身新颖。这里还提供了清晰的 SIC 与数据辅助 CE 区别。 | 算法1是 LMMSE 后 Mod[Demod] 判决反馈；不能把摘要的 decoded 自动解释为 FEC 译码。全文相关段落已读，未做其网格演化仿真。连续参数估计仍在当前任务范围外。 |
| Schniter, *Belief-propagation-based joint channel estimation and decoding for spectrally efficient communication over unknown sparse channels*，2010/2011 v2；[作者摘要与版本记录](https://arxiv.org/abs/1012.4519)。未知稀疏信道上的 BICM-OFDM 联合估计/译码，使用 relaxed BP。 | “未知信道+码反馈+低复杂度联合推断”并非新问题。 | 本条为摘要层核验；容量 pre-log 与本项目有限 N、叠加导频、物理分数信道的 FER 不是同一主张。 |
| Schniter, *A Message-Passing Receiver for BICM-OFDM over Unknown Clustered-Sparse Channels*，2011，DOI 10.1109/JSTSP.2011.2169232；[全文 §III-C、式(31)–(34)、§IV](https://arxiv.org/html/1101.4724v3)，[正式元数据](https://arxiv.org/abs/1101.4724)。GAMP、结构稀疏先验与 SISO 译码；式(34)显式排除当前比特输入先验。 | 自身先验排除和联合估计/译码已有标准消息定义，应作为机制推导的基础。 | 排除当前输入因子并不证明有限 loopy 图的所有历史自响应为零。本文 §III-C 还区分 turbo/equalizer/GAMP/decoder 多层迭代，支持完整调用记账的必要性。HTML 内动态排版日期不作为出版日期。 |

## 取舍

1. **保留的研究问题**：合法外信息经过 CE 和有限 BP 后的竞争返回路径，何时影响完整报文风险；同一可靠性下能否给出完整成本收益及适用边界。
2. **不作为创新点**：普通软先验、固定刷新、行删除恒等式、整数移位表示、QPSK tanh 形式、已有矩阵缓存技巧。它们可用于构造强基线或消除实现浪费，不能自动支持 Transactions 贡献。
3. **新增缺口**：现有 REF-01 的五臂是同一接收家族的经典增强，不替代公开近邻算法对照。新增 REF-02 先核验作者 DI-S-MMSE 代码的 SISO 外信息/数值合同，再在共同观测下给出明确标注的适配参考；不能只挑弱 BP 对照。
4. **保持范围**：最新 SBL 文献使分数连续参数的邻近工作更加明确，但不据此重开用户当前排除的连续多普勒估计。本文若仍采用整数展开工作模型，必须公开物理分数信道和模型失配边界。

`LIT-01` 是当前方向的文献边界核验。最终方法形成后仍需检查该方法的直接最近邻，不能用本表给尚不存在的方法签发“新颖”结论。
