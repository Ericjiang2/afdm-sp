# Sol 查新 + 重要性初筛（第 6 步：l34，前提检查）——本地第 4 轮，2026-11-22

模型：gpt-6.2-sol（`codex --search exec --sandbox read-only`）。l34 由 Gemini 4 Neon 出题，跨家族。提示：`~/.cache/idea-funnel/afdm-20261122-l4/s14-sol.prompt`。以下为原文。

## 线 A｜同帧 Luo 式稀疏贝叶斯学习对照

**有条件值得做。** 如果表 III 要保留对强 SBL 基线的性能或速度主张，投稿前值得补一次同帧对照。如果表 III 只报告两套已冻结接收机的实测差距，明确配置和适用范围即可，省去独立的 L2 仿真。

**固有重要性（抛开先例）｜低。** 目前卡住的是表 III 的归因。同帧比较能回答哪套接收机在这批帧上更好，无法回答差距有多少来自信道估计、检测器或运行预算。逐项替换就能检验这三者，卡片没有提出足以单独支撑一篇顶刊论文的新结构。

**白话。** 这像用同一批录音比较两套听写软件。一套在听写时会重新调整对回声的估计，另一套沿用先前的估计，并且每段都要完整跑第二遍。这样的比赛能告诉你哪套软件在这批录音上更准、更快，但拆不出哪项设计贡献了多少。让第二套也调整回声值得试，因为项目里已经见过同样的调整帮了一种版本、却害了另一种。

### 最接近的工作

1. **Yirui Luo 等，*Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System*，2026（核对全文 §III–VI）。** 用叠加导频起步，在每轮固定当前信道做线性最小均方误差检测，再把硬判决送回离网稀疏估计，并提供低复杂度版本。项目里的两轮固定增益移植只继承了部分设计。[原文](https://arxiv.org/html/2607.18881v1)
2. **Huang 等，*Iterative Sparse Channel Estimation and Decoding for Underwater MIMO-OFDM*，2010（核对全文方法与实验）。** 在水声多载波接收机上分别比较仅检测与译码迭代、加入稀疏信道再估计、硬反馈和软反馈，已经展示了如何拆开这些收益，所用估计器与这里的 SBL 不同。[论文](https://link.springer.com/article/10.1155/2010/460379)
3. **Sun 等，*Joint Channel-Estimation/Decoding with Frequency-Selective Channels and Few-Bit ADCs*（核对全文 §III–V）。** 在编码单载波中，对同一双线性观测做联合信道与符号推断，并和译码器交换软信息，同时评估固定信道的线性均衡方案。它支持测试检测接口，场景是频率选择性信道和低精度量化。[论文](https://arxiv.org/pdf/1807.02494)
4. **Parker 与 Schniter，*Parametric Bilinear Generalized Approximate Message Passing*，2016（核对全文模型与实验）。** 从带噪双线性观测同时估计两组未知量，并用于自校准和盲反卷积。它给出了联合估计增益与符号的通用算子，没有给出这张编码接收机表的排序。[论文](https://phil-schniter.web.app/pdf/jstsp16_pbigamp.pdf)
5. **Tipping 与 Faul，*Fast Marginal Likelihood Maximisation for Sparse Bayesian Models*，2003（核对全文算法与讨论）。** 在固定字典的统计学习中按边际似然逐个增删候选项，说明高效 SBL 可以主动缩小活动集。其删除规则与本卡建议的 `1e-3` 门限不同。[作者全文](https://www.miketipping.com/papers/met-fastsbl.pdf)
6. **Al-Shoukairi、Schniter 与 Rao，*A GAMP Based Low Complexity Sparse Bayesian Learning Algorithm*，2018（核对全文 §III–V）。** 用阻尼近似消息传递替代密集矩阵分解，并明确计入内外层迭代数。它提供了低复杂度对照的依据，实际速度仍取决于字典与收敛行为。[论文](https://arxiv.org/pdf/1703.03044)
7. **Wei 等，*Off-Grid Channel Estimation With Sparse Bayesian Learning for OTFS Systems*，2022（核对全文模型与算法）。** 在导频估计内更新分数时延与多普勒，并用二维分解降低开销。它说明离网更新可以从导频阶段开始，采用的是带保护区的导频设计。[论文](https://arxiv.org/pdf/2101.05629)

**查新判断｜部分被做过。** 按 `scoop-check` 的四轴，问题是同帧条件下的误帧率和时延归因；核心机制是比较 \(y=B(x)h+w\) 中固定路径增益 \(h\) 与联合更新增益和数据符号 \(x\)，再单独检验停止规则和候选剪枝；关键判断是检测接口会改变估计器排序；适用范围是本项目的编码双色散链路。最接近的是项目自己的试点 5，机制、判断和场景都重合，属高重叠。它已经用同一份第二轮 SBL 输出测到排序反转。未见的是把首轮反馈、后续轮数和计算预算放回同一个主表口径后，最强基线还差多少。[试点 5](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_joint_detector_20261019/SUMMARY.md>)

**为什么没有这张补表｜（2）发现了但不构成独立研究问题。** 水声通信早已有控制检测与译码反馈的对照，Luo 原文也专门比较了稠密与低复杂度的估计器。这张表缺的是项目内的一次配对验证。调导频比例会移动工作点，无法消除检测器和计算预算的混杂。[Huang 等](https://link.springer.com/article/10.1155/2010/460379) · [Luo 等，§IV–VI](https://arxiv.org/html/2607.18881v1)

### 主表核查

- **归档有依据，主表的归因需要收紧。** E-3 跑前就冻结了两轮固定增益和无条件执行第二级，目的在于让各 SBL 变体共用下游配置，检验同时延候选和误帧率。设计还用固定增益复核了真信道对照。Stage 3 跑前指定复用封存的准确率记录，计时也要求输出与归档一致。能核实的是这些配置被明确固定，以及不触发剪枝早已记录。卡片所说的“特意不剪枝以保住弱路径”未在协议中找到依据。资产卡的“共享检测器框架”在复用软件组件的意义上成立，但容易让人误读成同配置。现稿骨架已经说明门控摊销，仍需交代检测模式、轮数和稠密求解配置。[E-3 协议](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_e3_sbl_20261017/PROTOCOL.md>) · [Stage 3 协议](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/PROTOCOL.md>) · [资产卡](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261118-03.md:99>)
- **Luo 原文与最强合理基线。** 正确出处是 `arXiv:2607.18881`，题名见上。预印本注明由 *IEEE Transactions on Communications* 接收，Qu Luo 等的参考文献列出卷 74、12485–12500 页及卡片所列 DOI。原文式 (20)–(21) 先消导频，再以当前信道做固定信道的线性检测。算法 1 回送的是解调后重调制的硬符号，没有低密度奇偶校验码（LDPC）译码器的软信息回送，也没有检测器内部的增益重估。**路径增益在下一外轮由估计器重估**，外轮按符号变化量或轮数上限停止。若主张胜过 Luo 的方法，首选把其低复杂度、迭代离网的 `D-GAMP-GESBL` 移植到同一帧和码制，明确标出编码适配。若只补项目内的强对照，至少保留固定增益的 `L-diag`、`diag-off`，并纳入联合增益的 `L-cov`，用独立校准帧选配置。试点只证明 `L-cov+joint` 在该切片最强，最强的完整接收机仍待比较。[Luo 原文 §III–V](https://arxiv.org/html/2607.18881v1) · [交叉题录，参考文献 13](https://arxiv.org/html/2610.41997v1) · [离网对照记录](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-04.md>)
- **耗时倍率有效，但只代表归档配置。** CODELAY 先跑完两轮，在末轮校验子非零时才重搜并做第三轮。SBL 在首轮后总会进入第二级。按原计时工况复核，固定增益 SBL 在导频功率占比 \(\rho=.3\) 时，两个场景的首轮误帧率在 6 dB 都是 **100%**，在 7 dB 为 **98.75% 和 99.0%**。这支持“单加安全早停的收益很小”。本地计时文件只保存了 CODELAY 前两轮末尾的触发标记，SBL 在那 100 帧上的校验子归零数没有从该文件核到。剪枝更值得测，但 `1e-3` 的剪枝门限比较的是先验方差与最大先验方差，现有输出门限比较的是估计增益能量与总能量。数值相同不构成对齐，改动后必须复测误帧率。第 2 级约 629 个候选、最多 100 次密集分解，是该实现的成本。[分格统计](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_e3_sbl_20261017/out/analysis/e3_summary.json:371>) · [剪枝实现](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_e3_sbl_20261017/sbl_rx.py:137>) · [计时记录](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/out/RESULTS.md>)

**真实系统里的影响。** 同总能量、同帧长和同码率下，会改变的决定是：给定 1% 误帧率与时延预算，选哪套接收机、需要留多少信噪比余量。归档的 **1.3–5.3 dB** 是相对指定移植版的交叉点差，部分区间的一端无界。**11.9–16.0 倍**是 \(\rho=.3\)、6–7 dB、CODELAY 仅触发 1/100 帧时的单核整帧均值比。卡片预测的 **0.6–2.3 dB** 和 **2–3.5 倍**目前没有足够证据：每格 4–10 帧估不了 1% 交叉点，剪枝探针量的是子阶段耗时。试点 5 提供了更可靠的量级，但只限第二轮和所测切片：联合增益令 `L-diag` 从 **2.4% 升至 10.1%**，令 `L-cov` 从 **8.8% 降至 1.8%**。给 `L-genie` 真数据后仍差约 0.3 dB，只说明剩余配置还有损失，无法把损失归到网格或固定增益中的某一项。[主表结果](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/out/RESULTS.md>) · [试点 5](</Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_joint_detector_20261019/SUMMARY.md>)

**最强的反对意见。** 同一个联合检测器用在近重复候选很多的标量 SBL 上，已经实测会变差，因此“全部切到联合增益”既不能代表最强 SBL，也无法验证卡片预言的普遍缩水。

**最便宜的决定性检验。**

1. **先决定表要不要改，复用旧帧。** 用原计时的 100 个同帧键，复现归档输出，并读出固定和联合两种首轮的校验子及信息位错误。准确率筛查用 P1 的 U/G 两种信道、\(\rho=.3\) 的 7/8 dB 与 \(\rho=.5\) 的 7/8 dB，各取同一批 100 个物理帧编号。保留 CODELAY 与归档臂，对 `L-hard`、`L-diag`、`L-cov` 和已有的 `diag-off` 分别切换首轮、次轮的增益模式。先固定两轮且不改剪枝。同一份第二级估计结果可以共用给两种次轮检测器，直接数救回和伤害。
2. **再测真正会进主表的候选。** 用独立校准帧选定候选，然后分别打开校验子早停、剪枝，并给强 SBL 一次同样最多三轮的机会。保留相同波形、总能量、帧长、译码预算和噪声输入。跑前锁定判据，例如主表差距变动达到 **0.3 dB**、基线排序翻转，或速度低于拟保留的倍率，就改主张。正式只对入选臂用未见帧补齐交叉点两侧，按物理帧配对给区间，同时报告平均和第 95 百分位整帧时延。100 帧即使零错误，单侧 95% 上界仍约 **2.95%**，所以首轮筛查读固定信噪比下的误帧差，不能当作 1% 交叉点验证。

**表 III 怎么写。** 现在就可写成“在相同 P1 仿真帧上，比较触发式 CODELAY 接收机与归档的两轮、固定增益、第二级总执行的密集 SBL 移植版”。把检测模式、轮数、触发率、候选规模和交叉点区间放在表中。即使卡片的缩幅全部复现，也按各自实测配置报告结果，把匹配对照用于归因，把完整接收机对照用于报告系统代价。若保留对 Luo 低复杂度方法的速度主张，需要实际计时该方法的同帧移植。

本次只读核对了源码、协议、结果和原论文。`paper-search` 按指定解释器启动后，安装版不支持文档中的 JSON 参数，去掉该参数后又因只读环境无法创建临时目录而退出。文献证据来自独立网页检索和原文核对，重叠判断按 `scoop-check` 的四轴完成。未运行新仿真，未修改项目文件。
