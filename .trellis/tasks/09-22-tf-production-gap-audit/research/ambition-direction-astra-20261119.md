**【判断】首选现在写正文。第一步是用一张图讲清楚：同一条强径被表示成两条近邻路径时，接收机在哪一步会因此选错，又该在哪一步保留正则化。** 这是现有证据中，其他接收机设计者最有可能带走并使用的结论。对“现在动笔”的置信度 **H（高）**。最值得为之改变顺序的是一次独立实测信道回放，排第二。

下文【据】指文件或原始文献中的事实，【推】指由其推出的结论，【假】指我的成本估计、外部先验或建议采用的判据。“外部先验”估计同类增项能否让审稿人把论文从一个接收机结果读成可复用的贡献。没有成对稿件及其评审结果可供估计频率，故只给高、中、低。

### 1．现在写，把两个相反结果放进同一张主图

【据】当两条候选路径趋于重合，把增益平分给它们，物理信号保持相同，逐路径计算的不确定度惩罚却会减半。新帧上，搜索路径时只修正两条路径**共同贡献**的方向，6,800 个工况的帧对错就与闭式同延迟修正 `CODELAY` 完全一致。在过完备稀疏贝叶斯学习（SBL）中，给两条路径**彼此抵消**的方向加惩罚下限，找回了完整协方差相对标量方案错帧差距的 76.3%；加在另一方向只找回 4.2%。前者有目标函数层面的证明，后者有前瞻干预证据。 [证明 §2](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex:286>) · [前瞻结果卡](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-03.md>)

【推】主图应让读者先看懂“为什么拆成两条会占便宜”，再看到“为什么同一修正放错阶段会付出代价”。系统意义已有独立落点：总功率固定、双方各取六点网格中最好的导频比时，`CODELAY` 达到 1% 错帧率所需信噪比比原前端低 **1.14 dB**，98.33% 区间为 **[0.56, 2.07] dB**。两者最优导频比的区间仍有重叠。 [导频扫描结果卡](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-06.md>)

【假】**可行性高 × 兴趣高。** 外部先验中：清楚的设计规则有机会改变读者怎样使用论文，仅靠写作成为标志性工作的机会仍低。首检用半天、一张图、一位未参与者。让 Eric 脱稿推导平分惩罚，再让读者独立回答“下限应加在哪一步、依据是哪一层证据”。两问都答对就展开全文；答错先改图。风险是把 SBL 的实验排序写成定理。可比的写法是从物理结构直接给出设计者要设的参数。[Bemani 等的 AFDM 原文](https://arxiv.org/abs/2204.12798)

### 2．在一个事先选定的实测信道上，只换路径评分

【据】现有强基线比较采用同一套检测、译码框架中的移植版本，主要性能来自同一合成信道族。Watermark 提供由海上实测时变冲激响应驱动的公开回放，可给水声场景一个来源独立的检验。 [配对基线结果卡](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261118-03.md>) · [Watermark 官方说明](https://www.ffi.no/en/research/watermark)

【推】对考虑采用该方法的人，最有价值的问题是：冻结前端、候选库和译码器后，在独立记录上，把标量评分换成同延迟评分还会少错帧吗？回放可以回答性能迁移。单条记录缺少逐径真值时，不能据此归因每次幻影或漏检。

【假】**可行性中 × 兴趣高。** 外部先验中：独立回放比同一生成器再加一格更可能改变可信度，单一海域能支持的推广仍有限。首检限半天，按带宽、时延扩展和可用独立记录块数预选记录，查看原始数据能否直接通过现有接收机。若须重写同步器或改变时延模型，就留到下一篇。若可直接接入，预算上限五个人日、无需显卡；先在独立校准段确认已知信道可译且原前端有可救错误，再冻结比较。在留出记录块上，配对错帧率改善的 95% 区间下界高于零，才支持迁移。

### 3．把“一个方差总量够用”推进为跨波形的接口规则

【据】现有证明已给出分界：在采用逐符号方差的模型下，仿射频分复用（AFDM）与普通正交频分复用的同延迟块由总方差决定；矩形脉冲的正交时频空调制（OTFS）还可能依赖各时延行的方差和。再证明一次矩阵不同，给设计者增加的信息有限。 [证明中的跨波形推论](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex:247>)

【推】真正能提高上限的是说明**少传哪一项会选错路径**。这里有个容易忽略的前提：本文四相相移键控的数据符号能量恒为 \(E_s\)，给定软均值 \(\mu_n\)，其边缘方差已由 \(v_n=E_s-|\mu_n|^2\) 决定。“重构这个矩阵需要几个线性摘要”与“译码器必须额外传几个数”是两个问题。

【假】**可行性中 × 兴趣高，长期上限最高。** 外部先验低；若能预言另一种波形的实际决策，升为中。首检限两个人日，用非恒模星座手构两组可实现的后验，保持软均值、总方差、观测及候选相同，只改变方差在时延行间的分配。若两组的完整评分选出不同路径、行方差和能分别恢复选择，且小扰动不消除翻转，就值得单开研究；若只得到矩阵差异或数值平局，本文保留现有推论。 [此前的线性摘要设想](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/astra-ambition-A-20261118.md:33>)

### 4．预言实际接收帧中，弱径何时输给幻影

【据】这是理论上最诱人的缺口，也是已有反证最直接的一项。强制漏检扫描中，标量评分的翻转发生在理想预测位置的 **0.127 倍**，95% 区间为 **[0.118, 0.136]**。事后分解表明检测器吸收是最大贡献项，但仅修正吸收时，低功率比一格的预测奖励比约为 **0.42**，实测为 **0.27**；直接投影本身也有损失。 [强制漏检卡及显式更正](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-01.md>) · [证明复核](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/claude-proof-recheck-v2-20261119.md>)

【假】**可行性低 × 兴趣高。** 对预测弱径可检测性的读者重要，外部先验低：为一个译码器补偿失配，很容易只拟合原工作点。首检限两天纸笔推导，要求从评分前可得的量同时给出吸收与直接投影的预测。需要代入真实弱径增益来估计吸收、实测候选得分或事后译码标签，就停止。只有公式冻结后，在留出工作点、两档导频比下均把翻转位置预测到两倍以内，我才会提高其顺位。

### 改判条件与陷阱

- **【判断】最强替代是第 2 项。** 若已能提供符合接收机带宽和时延范围的独立记录，校准段也表明有可救错误，我会把这次有上限的回放排到完整写稿前，置信度 **M（中）**。它直接检验目前证据最薄的一环，即同一评分规则离开本项目的信道生成器后是否仍有用。
- **【据＋推】把同一个协方差放进所有阶段，或继续追平标量 SBL。** 差模下限使间隔 0.35 个多普勒频格的真双径少获双原子表示 **4.17 个百分点**，错帧代价仍不确定。两项修改合用后追平标量也只是次要读数。这些结果足以界定使用范围，继续加样本主要提高数值精度。 [双径冲突卡](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-04.md>) · [剩余差距卡](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-05.md>)
- **【据＋推】从少收幻影跳到盲估路径数。** 已有失败帧的事后读数中，同时把两类误报压到 5% 时，`CODELAY` 的漏检真径通过率仅 **2.0%**。仅靠消除强径副本，仍过不了数据干扰形成的门限。 [盲定阶读数 §3](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md>)
- **【据＋推】把工程补项当成投稿前提。** 判决导向噪声估计在所测工况使 1% 错帧率门槛恶化 **1.64 dB**。给导频扫描补真实几何参照，可以辨别高导频比失败的原因，却不会改变已经前瞻成立的 1.14 dB 系统比较。两项各有明确用途，都不应挡住正文。 [噪声估计卡](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261118-05.md>) · [导频扫描卡](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-06.md>)