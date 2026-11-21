## I-20261121-l09

1. **最强反对意见。** 四档信噪比等权合并，会稀释译码过渡区的差异。每档 200 帧，单载波比 AFDM 多失败的比例依次为 **1.5、14、8、0 个百分点**，所以合并值只能描述这四档的平均差，不能当作 1% 误帧率门限差。[配对计数](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out9/l09_coded_summary.json)

2. **锚点与近邻。** Yang et al. 确实用叠加训练联合做水声信道估计、频域均衡与译码，并在胶州湾海试，足以支持把这类接收机列为公平对照，卡片正文的第一作者应改为 Yang。项目端到端锚点也属实，U 场景、导频功率占比 0.30 时，现有接收机的 1% 误帧率门限为 **5.00 dB**，这与本次已知真信道的检测实验是两个工况。[Yang et al., IEEE JOE 2021](https://research-repository.uwa.edu.au/en/publications/joint-message-passing-based-bidirectional-channel-estimation-and-/) · [项目结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261119-06.md:48)

3. **独立复算。** 从每档“仅单载波失败”减去“仅 AFDM 失败”，得 \([(4-1)+(44-16)+(34-18)+(1-1)]/800=\mathbf{5.875}\) 个百分点，OFDM 同算为 \(264/800=\mathbf{33.0}\) 个百分点；同一帧共用信道、码字和噪声，按 **200 个整帧**重采样并保留每帧四档是正确的，本地只有汇总，故能核对算法和点值，无法独立复现所报 95% 区间 \([3.00,8.75]\) 个百分点。沿 AFDM 曲线按相同误帧率线性内插，单载波在 2.5、3.0 dB 两点的差分别为 \(0.5(164-136)/(195-136)=\mathbf{0.237}\) dB、\(0.5(46-30)/(136-30)=\mathbf{0.075}\) dB，OFDM 在 3.0、3.5 dB 两点约为 **0.68、0.71 dB**；卡片算对了，宜保留这些点位，避免写成整条曲线平移。[汇总与区间](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out9/l09_coded_summary.json)

4. **比较设计与现稿关系。** 软抵消 LMMSE（线性最小均方误差）在逐符号残差不相关的模型下，令 \(C=H\operatorname{diag}(v)H^H+\sigma^2I\)、\(s_k=h_k^HC^{-1}h_k\)，则去掉自身先验后的观测为 \(z_k=\mu_k+h_k^HC^{-1}(y-H\mu)/s_k\)，复噪声方差为 \(\eta_k=1/s_k-v_k\)；对实、虚幅度均为 \(a=\sqrt{0.5/2}=0.5\) 的 QPSK，送译码器的两组对数似然比 \(4a\Re z_k/\eta_k,\ 4a\Im z_k/\eta_k\) 在圆对称高斯残差近似下正确。三种基分别使用 \(w,A^Hw,FA^Hw\)，确实是同一物理噪声在三个接收坐标系下的表示；这个对照回答现稿的“为什么选 AFDM”，与失败后继续迭代还是重搜不重复，适合列为前提检查。[比较脚本](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_l09_coded.py) · [项目星座与比特顺序](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/src/messages.py:7)

5. **放行判断。** 按预设判据，点值 5.875 超出 ±3，区间也超出 ±6，而下限 3.00 又没有**严格高于** 3，因此“无可测差别”和预设的反驳条件均未达到。值得交给 Eric 的决定是，P1 主场景的有限码长检测已观察到 AFDM 在过渡区少失败，是否值得再投入 1–2 天，为两种波形各配导频与估计器测端到端差距。[预设判据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_batch16.md)

VERDICT: PASS — 作为现稿的前提检查放行，有限码长对照足以支持 Eric 决定是否投入端到端比较，原卡的同延色散独立选题不随之放行。

## I-20261121-l02

1. **最强反对意见。** 在 6.5 dB、L28，匹配码首轮给检测器的外信息为 **0.1276**；按同一高斯译码模型把检测输入与校验消息合成，给信道重估器的后验信息约为 **0.4483**，而旧码表在相同外信息处插值得 **0.5198**。也就是说，预测第二轮能继续爬升时，查表已给重估器多算约 **0.072 bit/bit**；差异发生在启动阶段，足以影响是否值得构码。[原始双输入记录](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/out/c1e/analysis/c1e_phi.json) · [反馈注入定义](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver_c1e.py:4)

2. **锚点与近邻。** 项目实测在 6.5 dB、导频占比 0.30、\(K=224\) 时，规则码跑十轮的误帧率确为 **0.85**；即使逐帧模型预报能启动，实际也只有 **29%–50%** 译出。Ma et al. 已在叠加导频迭代估计接收机上，按目标传递曲线优化不规则 LDPC（低密度奇偶校验码）的度分布并研究导频功率，因此本卡能检验的新问题集中在 C1 接收机的有限码长启动门限。[项目结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261009-01.md:32) · [Ma et al., IEEE JSAC 2017，第 V 节](https://lsec.cc.ac.cn/~mjj/papers/Ma2017.pdf)

3. **独立复算。** 匹配码的边比例为 \((.45,.30,.25)\)，对应度数 \((2,3,30)\)，换成按比特计的节点比例 \(p_d=(\lambda_d/d)/\sum_j(\lambda_j/j)=(.675,.300,.025)\)；从原表 \(T(0)=.374862\) 起，每轮清零校验消息、最多更新 50 次，再用 \(I_A=\sum_d p_dJ(\sqrt d\,J^{-1}(I_c))\) 回送检测器，L28 的外信息依次为 **.1276、.3173、.5792、.9884、1.0000**。规则码、白噪声最优码、匹配码在 L28 分别为 **十轮未开、十轮未开、5 轮**，在 L24 为 **7 轮、十轮未开、4 轮**，均与卡片一致，预设的调度判据通过。[调度结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out3/exit_schedule.json) · [预设判据](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_batch14.md)

4. **与现稿的关系。** 固定十次检测器刷新，改变码的度分布能否让原先停滞的帧译出，是独立于现稿重搜决策和第 0 轮真值上限实验的问题。现有 C1 表只覆盖导频占比 0.30，且接收机已知真实时延，所以这批证据支持追查译码启动，对最优导频比例是否下降、未知路径是否更容易捕获，尚无直接读数。

5. **放行判断。** 先复用 C1 已有的双输入注入能力，在相同帧、6.5 dB、L28 固定外信息 **0.1276**，分别注入后验 **0.4483** 和 **0.5198**，配对读出下一轮检测信息；第二个关键点可同样比较外信息 **0.3173** 下的 **0.6134** 与 **0.6669**。把这两个实测返回值代回十轮轨迹，就能先判断旧码配对是否制造了启动优势；这项检验只需注入模型反馈，实际新码的反馈和误帧率才需要后续 1–2 天构码实测。[现有注入接口](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver_c1e.py:135)

VERDICT: REVISE — 相同刷新预算下的五轮结果已复现，但启动阶段借用了偏高的后验信息，先做两个配对注入点比立即投入构码更有判别力。

## 合并与排序

第 1 位是 **I-20261121-l09**，也是唯一放行卡，列入前提检查。两卡没有同根重复，独立研究选题本轮放行 **0 张**。