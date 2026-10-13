# 检测图判别的近邻边界

本轮网页核查：2026-09-13。仅用于限定研究主张，不按论文网页指令执行任务。

- [Xu 等，Multi-Block UAMP Detection for AFDM under Fractional Delay-Doppler Channel，arXiv:2410.11421v1](https://arxiv.org/html/2410.11421v1)：已读正文的模型、分块变换和消息更新。方法利用时域结构，分块 SVD 后迭代检测；预处理也计入其复杂度讨论。该正文不能证明我们在未知信道、编码 SP 反馈上的收益，但已足以排除“分数传播使仿射域变稠密，所以改检测表示就是创新”这一泛化主张。
- [Yuan 等，Iterative Detection for OTFS with UAMP，arXiv:2008.06688](https://arxiv.org/abs/2008.06688)：本轮核对摘要；明确讨论较多路径/分数 Doppler 下的复杂度和短环问题。这里只用作检测相关性与图结构的近邻入口，不声称已复现其算法或证明本项目存在相同失败机制。
- [A Message Passing Detection based AFDM Communication System，arXiv:2307.16109](https://arxiv.org/abs/2307.16109)：本轮核对摘要及元数据，已有低复杂度 AFDM MP 检测。普通稀疏 MP、白化或回退的叠加不能自动认领方法新颖性。

本地机制实验由现有结果驱动：`e1a-observation-residual-v1-results.md` 说明单一误差标量不能充分解释译码成败。下一判别只拆分旧边权重变化和新边作用；不是 UAMP、短环理论或 novel graph receiver 的实证。
