# 第 1 轮

我的判断是：**AFDM-SP 的核心困难，是在没有干净训练区的条件下，从同一份接收信号中同时确定“信道怎样作用”和“发了什么”，再让尚不可靠的数据判断参与信道获取。** 其中既有物理上分不清的东西，也有观测中存在信息、当前推断过程却用不好的东西。你的结果反复提醒我：必须把这两者分开。现在看到的若干性能墙，还不能称为物理极限。

我没有打开你排除的两份文件。不过，STATE 已包含它们的方向摘要，因此这次阅读不能称为完全盲读。下面的判断依据是具体结果与反例，不采用那些摘要中的方向推荐；也不把本轮解释作为新增的已验收结论。

先从接收端究竟知道什么说起。按当前主线生成器，一帧观测可以写成

\[
y=H_\theta\bigl(\sqrt{\rho}\,p+\sqrt{1-\rho}\,x\bigr)+w,
\qquad
H_\theta=\sum_{i=1}^{P}h_iU(\ell_i,\nu_i).
\]

这里，\(y\) 是长度为 \(N\) 的接收复向量；\(p\) 是已知导频序列，\(x\) 是未知的编码 QPSK 符号；\(\rho\) 是发射能量中分给导频的比例。\(H_\theta\) 是这一帧的信道算子，未知参数包括路径的整数时延 \(\ell_i\)、连续 Doppler \(\nu_i\) 和复增益 \(h_i\)；\(U\) 表示一条路径施加的时移、频移及 AFDM 相位作用。\(w\) 是接收噪声，当前主要比较中其方差已知。数据不是任意复向量：星座和 LDPC 校验约束限制了它的可能取值，这也是信息来源。[生成器](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tcom_reference_frame_20261015/gen_fixed.py:303)

叠加导频节省了保护资源，却没有省掉辨认信道所需的信息。在项目采用的嵌入导频布局中，主场景所需保护区达到 1029 个位置，超过 \(N=1024\)；短时延场景能容纳它，却要拿出约四分之一的位置。因此，这个问题有明确的通信价值：用数据与导频的重叠，换取更多有效载荷，代价是两者在接收端相互污染。这是该布局和场景的结论，不是所有嵌入导频都不可行。[res-20261015-03](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261015-03.md)

这也解释了为什么提高 SNR 不是万能的。对于把未知数据当干扰的初始估计器，减小热噪声并不会同时减小数据干扰；固定 \(\rho\) 时，导频与数据的发射功率比仍为 \(\rho/(1-\rho)\)。增加导频能量又会挤走数据能量。极端地，\(\rho=1\) 时训练最干净，但这一帧没有数据可传。真正的困难正是在有限训练能量下启动数据辅助，而不是单独把信道估计误差压低。

更关键的是，译码器反馈没有提供第二份独立观测。它把同一个 \(y\) 与码约束结合，产生更强的数据判断；这些判断可以有价值，却仍与先前的信道误差、噪声和消息有关。**联合推断的收益来自更充分地利用已有约束；反馈是否被当成了过于可信的参照，是另一件事。** 后者在你的结果中有明确警讯，但我还不能把“重复计算信息”认定为全部失败的因果机制。

物理上不可约的难处，首先是某些参数本来就无法分别辨认。两条路径若具有相同的时延和 Doppler，则

\[
h_1U+h_2U=(h_1+h_2)U.
\]

观测只依赖增益之和。即使数据完全已知、噪声为零，也不能从这一个信道作用中恢复两个独立增益。两条路径稍微分开后，绝对不可辨识变成不稳定：在项目的整数时延、充分 CPP 模型下，同延迟两原子的归一化 Gram 矩阵最小特征值为 \(1-|D_N(\Delta\nu)|\)。这里 \(D_N\) 是有限帧内两条 Doppler 调制序列的归一化相关，\(\Delta\nu\) 以 Doppler bin 为单位。间隔趋零时，相关趋一，区别两条路径的方向越来越弱。有限观测和噪声限制了这种区分；它不是一个低于某个固定间隔就永远不能分开的硬门槛。[算子几何命题](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/results/cstate_method_closure_20260928/MANUSCRIPT_THEOREM_TEXT.md)

但接收机最终要恢复的是信息比特。**分不清两条射线，不等于不知道它们合起来怎样作用于数据。** 单个增益可以很不确定，而增益之和很确定。反过来，信道矩阵的平均平方误差很小，也不保证传给译码器的软信息可靠。这是我认为项目中最需要始终保留的区分：物理射线参数、等效信道作用、译码可靠性，是三个不同对象。

另一类真正的极限来自保留了什么观测。你已经有一个很有分量的反例：在固定信道、独立 QPSK 源与圆对称高斯噪声的同零时延盲观测模型中，共同 Doppler 平移只改变相位，整块原始坐标功率数组同分布；只看功率，就无法识别那个共同中心。五行截断模型在指定合法分支和非共线增益条件下，反而能给出中心的逆。这说明截断可能打破物理模型原有的对称性，制造出模型内的识别信息。接收端可逆换坐标不会增加原始信息，丢相位或截断则会改变问题。这个边界比“哪个统计量阶数更高”更根本。[res-20261006-03](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261006-03.md)

因此，我不会把那些限定碰撞模型中的正 Fisher 信息、四阶识别或渐近分辨尺度，直接用于解释当前 FER。总体上能识别、有限样本能稳定估计、有限计算下能译出来，中间还有两道距离；有些研究中的重复数是独立整帧数，也不是单帧里的符号数。你的高阶信息和未知参数检验研究已经明确留下了这些限制。[res-20261006-02](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261006-02.md)、[res-20261005-02](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261005-02.md)

回到现有接收机，我看到的第一堵墙是：**正确解释可能已经比错误解释得分高，但接收机仍走不到那里。** 早期选定的 32 个失败帧中，在工作几何下，无论条件评分、增益 profile 评分还是高斯增益边缘评分，真码字都胜过那个由错误信息比特重新编码得到的合法候选，32/32。重新评分并没有创造这种偏好。这不说明真码字是全局 MAP，更不说明接收机能够生成它；它说明这批失败不能解释成“只要换一种评分，真码字就会首次胜出”。同一台账中，延长普通迭代只救回部分帧，给真实几何则救回 27/32。信息、搜索可达性与计算预算不能混成一个“估计不准”。[否定结果台账](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md)

主线的新证据进一步定位了一个具体障碍：初始导频阶段漏掉时延后，固定支撑上的增益和 Doppler 更新无法凭空补出那个时延。这里“支撑”就是模型允许存在路径的位置集合。已验收的 genie 审计中，直接给真实时延，在 6.5–8 dB 消除了接收机相对约束 MCRB 的信道误差差距的 73–81%。但这个 MCRB 已经假定时延已知，且有局部无偏等适用条件；它不是未知支撑接收机的可达性能证明。尤其 \(\rho=.3\) 时，给真时延后仍有 4.5–5.3 dB 的 refit 差距。[res-20261016-03](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261016-03.md)

这里还有个容易被“支撑主导”掩盖的反常：只给真实时延、却不给 CSTATE 后续分支，译码仍比实际主线差；补上同一分支后才大幅接近真信道参照。后半段是事后实验，不能升级为预注册归因。它至少要求我们承认：**正确支撑很重要，但正确支撑不是一个脱离后续推断流程就足够的答案。**

第二堵墙是：**同一项不确定性修正，换一个估计器或检测器接口，就可能反转收益。** CSTATE 是在常规接收失败后，用软数据重新选择路径集合的救援分支。在它的因子消融中，完整数据不确定性矩阵支持的支撑交换贡献了约 89% 的几何增量；取消非对角项，有交换时明显变差，没有交换时几乎不变。新帧守卫实验又发现：在没有真实同延迟多径的信道中，禁止同延迟候选几乎完全追回完整矩阵的收益；在真实同延迟簇信道中，同样的禁令却把条件救回率从约 .126 压到 .016。[res-20261017-01](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-01.md)、[res-20261017-02](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-02.md)

这个矩阵 \(\Gamma\) 究竟是什么，需要讲清楚。它不是信道后验协方差，也不是凭空增加的一份信息。设 \(d\) 是已经包含数据能量缩放的发送数据，接收机以当前软消息形成工作分布，均值为 \(\mu\)、协方差为 \(V\)。用 \(p_\rho\) 表示已缩放导频，构造列向量 \(B_i=U_i(p_\rho+\mu)\)。固定这个工作分布时，对数据不确定性平均有

\[
\mathbb E_q\|y-\textstyle\sum_i h_iU_i(p_\rho+d)\|^2
=\|y-Bh\|^2+h^{H}\Gamma h,
\qquad
\Gamma_{ij}=\operatorname{tr}(U_i^{H}U_jV).
\]

这是二次误差的恒等分解；它并不保证工作分布就是真实后验。项目常用逐符号方差构成对角 \(V\)，但投影到路径坐标后的 \(\Gamma\) 仍可非对角。同延迟、近 Doppler 的路径在处理同一份数据误差，它们的不确定性作用会相干叠加。[协方差适配命题](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/results/cstate_method_closure_20260928/MANUSCRIPT_THEOREM_TEXT.md)

一个极端例子就能看出标量化丢了什么。把一条原子精确复制两份，并把增益平均分开，物理信道和均值拟合都不变。完整不确定性项仍按增益之和计算；只留对角项，则把原来的惩罚减成一半。**表示变多了，物理证据没有增加，但这项近似代价变便宜了。** 这给出了吸引重复原子的结构性理由；它只解释这一代价项的倾向，尚不能推出整个接收机的 FER 方向，因为先验、选择过程和后续更新也在作用。

你的 SBL 结果正好阻止了这种过度推论。已验收的外部检验中，完整 \(\Gamma\) 消除了大量额外同延迟原子，FER 却从标量版本的 .110 变成 .149，冻结裁决只是 MECHANISM-ONLY。随后，把这解释成网格插值，把它解释成“\(\Gamma\) 只该选支撑、不该估增益”，都没有经受住后续检验；后一个前瞻实验的冻结裁决为 REFUTED，该卡仍待验收。[res-20261017-03](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-03.md)、[res-20261018-04](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261018-04.md)、[预测台账](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/prediction-ledger.md)

更有辨别力的是后续小试跑：同一批 SBL 输出接固定增益检测器，标量 \(\Gamma\) 更好，FER 为 .024 对 .088；接联合重估增益的检测器，排序翻转，变成 .101 对 .018。这是有限条件的探索性证据，却已经足以否定把“标量版本好不好”只归于上游信道估计器的讲法。[SBL 接口对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_joint_detector_20261019/SUMMARY.md)

第三堵墙是：**更准的信道与更好的译码，确实会背离。** 在 200 个旧键的三模式对照中，标量上游配均值更新后，平均信道 NMSE 从 .063 降到 .037，FER 却从 .020 升到 .200；36 个由成功变失败的键中，32 个信道误差没有增加。这里 NMSE 衡量整个信道算子的归一化平方误差，FER 衡量信息帧是否译错，两者没有单调关系的保证。继续更新到 40 步也没有显示总体改善。[三模式对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_three_mode_20261020/SUMMARY.md)、[连续更新与重启对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_freeze_replay_20261020/SUMMARY.md)

比这一相关现象更硬的证据，是等价表示探针：均匀复制所有原子、平分初始增益，并保持诱导到物理信道上的工作先验不变，固定增益检测保持一致，原生逐坐标均值更新却从第一步就改变了实际信道作用。这表明当前近似推断会对等价的参数表示作出不同反应。它不能直接证明真实 SBL 的非均匀近重复原子就是排序反转的原因，但已经说明，“它们表示同一个信道”不等于“这个接收机对它们执行同一种推断”。[等价表示结果及适用范围](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)

11 月的探索也要求保留双向限制。一方面，改用期望 Gram 的增益均值更新后，路径 CSTATE 中完整评分相对标量评分的条件优势仍有 37.85 个百分点，原生更新下为 54.98 个百分点；所以不能把评分问题全部归咎于下游。另一方面，在同延迟内采用正交 DPSS 块的旧帧回放中，两种评分在 274 个触发单元里只选出一次不同支撑，译码没有差异；两者最终拟合都仍使用完整 \(\Gamma\)，故不能说端到端标量化已足够。我的解释是：**协方差修正的重要性与表示、决策和下游更新共同有关，不能用“物理模型更完整，所以处处更好”概括。** 这是有证据支持的问题判断，尚不是跨接收机的统一机制。[11 月配对结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)、[块交换回放](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/dpss_block_rescue_20261110/RESULTS.md)

第四堵墙是：**描述能力与到达一个好解的能力，并不相同。** 同延迟 Doppler 簇中，旧参数接收机出现 FER .873、真信道参照 .002 的巨大差距。这不能叫物理不可解；但换成可描述簇的基函数，也不能自动保证顺利启动。最新新帧筛查中，逐抽头扩宽流程在 J4、8.5 dB 错 98/160，独立宽块接收机只错 4/160。前者保留了窄模型阶段的时延与软状态，后者有自己的初始化和更新序列。现有证据没有隔离具体原因，却排除了“最后给足自由度自然就好”的简单想象。[簇信道卡，draft](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261008-02.md)、[新帧扩宽结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)

同样，负载悬崖也不能直接解释为信息论相变。已验收的 C1 研究中，同一个码在几类被测输入下的译码转折都接近 .577 的输入互信息指标，但平均返回映射对长期成功过于乐观；某些真实轨迹到不了人为注入软信息所到达的状态。每轮联合更新从 20 次增至 40 次，又能在六个工况中把临界负载推高。这些是有限预算、特定接收机与输入族的结果，不是一个由互信息标量完全决定的系统，也不是任意算法都越不过的容量界。[res-20261009-01](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261009-01.md)、[res-20261010-01](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261010-01.md)

如果问哪个部件已经在挑大梁，我的答案分两个尺度。**整个系统里，是反复更新符号与信道、再利用 LDPC 约束的联合推断循环。** “检测器”这个名字掩盖了它内部还在重估信道。7 月旧配置中，联合外循环从 1 轮到 10 轮使 BER 约降至五分之一；10 月另一配置中，增加内循环深度又显著移动悬崖。这两组数字不能合并，但都说明，不能把整个迭代接收机的能力归到某个前端评分器或单次信道估计步骤上。[历史七臂对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20260727-02.md)、[内循环预算结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261010-01.md)

**在当前 F0+CSTATE 相对常规接收机的增量里，挑大梁的是带数据不确定性约束的支撑交换。** F0 指导频获取后进行两轮联合估计、检测与译码的常规链。其失败单元中，CSTATE 救回 .302，多跑一轮 F0 为 .160，只重跑检测为 .142。这里约 89% 的比例是“几何更新增量中的交换份额”，绝不是整个系统 89% 的收益。这一层的证据比“完整协方差普遍更优”扎实得多。[res-20261017-01](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-01.md)

我目前最愿意坚持的立场是：**这项研究需要解释的对象，是有限观测、有限计算下，一个未知信道怎样成为足够可信的数据参照，以及数据判断怎样反过来帮助它，而不被所选表示和反馈历史误导。** 支撑漏检、簇表示不足、同延迟相干、软信息失配属于这个问题的不同位置；现有证据还不允许把它们压成一个万能病因。尤其预测台账里数次貌似完整的解释随后失败，使我更看重能同时容纳反例的理解。

我还没有弄懂、最想问你的三个问题是：

1. **你真正面向的物理场景里，一个信道能维持多久？** 当前大多数证据按帧评估；帧间重新抽取信道是现实中的相干时间约束，还是为了统计方便？一个信道只支撑一个码字，还是跨多个码字仍有可用关系，会改变可获得的信息总量，也改变“首帧获取”到底有多不可避免。

2. **当前模型里的哪些先验，是接收机在现实中确实知道的？** 八条互异整数时延、路径数作为上限、已知噪声方差、时延落在接收机字典内，这些条件中，哪些代表目标场景，哪些只是实验基准？我不是问下一步测什么，而是想知道：我们所说的“问题已经解决”，必须对哪个物理世界成立。

3. **你希望“信道估计成功”最终指什么：恢复真实射线，恢复足以预测接收信号的等效信道，还是提供足够可靠的译码软信息？** 三者可以兼得，但你的结果已经证明它们并不自动一致。如果两组路径无法分别辨认、合成信道却一样，或者信道 NMSE 更低而 FER 更差，你认为哪一个对象才是必须守住的？这个答案决定了哪些困难真的需要解决，哪些只是当前坐标给我们增加的负担。

# 第 2 轮

先记录你的三个回答，并纠正我上一轮的提问边界。

1. **任务是单帧突发传输或冷启动首帧获取，不能依赖历史帧先验。** 我接受这个约束，收回把“还能否利用前后帧”当作本轮问题选择空间的做法。帧间独立抽样服务于统计评估；单帧获取本身则是需要解决的通信任务。它的合理性不需要建立在“所有文献都采用同一设定”这个更强的断言上。

2. **工作模型是整数时延、连续分数 Doppler，最大时延处于 CPP 可覆盖范围；P=8 和已知 σ² 是主实验控制条件。** 我不再把这两个控制条件说成方法的必然前提。但要区分“希望稳健”与“已经验证”：槽位 8→12 已有探索性证据，完整/标量 Γ 的差距在共同触发样本上仍保留约九成；这支持优势不只来自八槽位挤占，尚不是任意路径数失配的保证。当前 STATE 仍将 σ² 未知列为待办，我没有找到它已在主线上验收的结果，因此先把“估计 σ² 后仍不敏感”记为验证目标。此外，整数时延是明确的离散模型假设，CPP 足够长是适用条件；宽带采样本身不使任意真实时延严格落在整数格点。[槽位失配结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/slot_mismatch_20261019/POSTHOC_CHECKS.md)、[STATE](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/STATE.md:55)

3. **最终目标是译码入口软信息的 logloss 与端到端编码 FER；射线恢复和信道 NMSE 只作诊断。** 我据此收回“是否必须分清物理射线”这个目标分岔。还有一个必须保留的区别：平均 bit logloss 下降，不保证固定 LDPC 译码器的 FER 下降。如果二者冲突，应把它记成性能权衡；如果 logloss 改善而 FER 区间仍未定，就只确认软信息改善。不能再让 NMSE 替它们裁决，也不能让其中一个未经说明地替代另一个。

在这些约束下，我给两个候选，**押注第一个，第二个是最强替代；置信度中等。** 它们都可以比“增加一个协方差项”更大，但不应大到变成无法否定的“更好地做联合推断”。

下面说“成为自然推论”，是指一个正确解释应当事先导出这些现象的方向和适用边界，不是现在已经从某条定理推导出了所有实验数字。我也不要求一个问题吞下全部结果。

**候选一：在单帧冷启动中，什么证据足以支持接收机改变信道结构，并因此改善可译码性？**

更完整地说：导频提供的初始信道不完整，接收机需要用不可靠的软数据重新判断哪些信道自由度值得保留、加入或替换。**它怎样区分“观测支持了新的信道作用”与“当前数据判断的误差恰好能被另一条路径拟合”？** 这里的结构指允许存在的时延及其内部时变分量，不等于要求恢复真实射线标签；“值得”最终由 logloss 和 FER 判定。

这件事对短包、突发或高速时变链路的接收机设计者重要：没有历史训练可以补救首帧，更多导频又会占用数据能量。它也直接面对审稿人最有力的质疑：**数据辅助重估早已有了，你是在修补一个弱初始化，还是找到了它在什么条件下能正确获取结构、在什么条件下会系统性误判？** 前者容易成为工程补丁，后者才可能形成清楚的问题与贡献。是否新颖仍需独立查新，现有性能提升不能替代这一判断。

这个问题能容纳三组已验收结果，而且每组在其中有不同的位置：

- **为什么后来再获取有价值。** 给真实时延能消除大部分高 SNR 信道误差差距；失败后利用软数据改变支撑，又优于只把导频前端做强。这与“初始导频没有足够证据，而后续数据判断改变了结构获取条件”相容。具体地，F0+CSTATE 在四个条件下比强前端 F1 好 .37–.90 dB，耗时约为其一半。这些结果不自动证明上述解释，但它必须能够解释这个时序优势。[res-20261016-03](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261016-03.md)、[res-20261015-02](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261015-02.md)

- **为什么动作与证据模型必须一起看。** CSTATE 的几何增量约 89% 来自支撑交换；非对角 Γ 的作用在允许交换时很大，不交换时接近零。若问题只是增益估计更准，便不自然地预期这种交互；若问题是结构判断是否误把相关的数据误差当作新方向，这个交互就是必须出现的辨别性现象。[res-20261017-01](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-01.md)

- **为什么不能用“禁止同延迟路径”代替问题本身。** 没有真实同延迟多径时，这条禁令追回了完整 Γ 的效果；有真实簇时，却抹掉了大部分救援收益。真正要判断的是一个额外分量是否提供可用的信道作用，而不是它的标签是否与现有路径重复。[res-20261017-02](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-02.md)

这里最强的反例仍是已验收的 SBL 结果：消除额外同延迟原子，FER 反而变差。因此候选一绝不能偷换成“少产生幻影就会译得更好”。它必须把**结构获取造成的改变如何经过后续推断转化为软信息**纳入问题；目前只能说这个反例划定了边界，不能说已经被统一解释。[res-20261017-03](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-03.md)

它背后任何方案都越不过的限制，是**有限观测对两种解释的可区分性**。把两种完整物理假设下的接收观测分布记作 \(P_0\) 和 \(P_1\)，未知数据及其他未知量按各自声明的模型处理；若两者等先验，最优二元判别错误率为

\[
P_{\mathrm e}^{*}=\frac{1-\operatorname{TV}(P_0,P_1)}{2}.
\]

TV 是两个观测概率分布的总变差距离，不是信道 NMSE。两种假设产生完全相同的观测分布时，任何算法都只能猜；分布很近时，也不可能靠更复杂的评分制造出可靠区分。这个简单假设检验边界不能直接当作当前复合模型的 FER 曲线，但它说明应该寻找什么极限。另一方面，若两种信道结构虽然分不清，却都能支持同样可靠的译码，那么分清它们根本不该是任务要求。有限块长通信把错误概率与假设检验联系起来，提供的正是这种观察问题的方式，而非一条可直接套用的 AWGN 门槛。[Polyanskiy–Poor–Verdú, 2010](https://web.mit.edu/~medard/www/Itpaperaward/Channel%20Coding%20Rate.pdf)

数学上，与它结构相近的是**带不确定设计矩阵的模型选择**。普通稀疏回归把字典当已知；这里用于生成候选响应的软符号本身会错，而且来自同一份接收信号。可以从 errors-in-variables 研究搬过来的是：不能只计候选拟合了多少残差，还要计设计误差怎样沿候选方向相关。不能直接搬来的是它的更新式和误差界，因为当前软符号误差与噪声、信道估计、码约束内生耦合，并不自动满足经典测量误差假设。[Loh–Wainwright](https://arxiv.org/abs/1109.3714)

**什么结果会让我承认这个问题选错了？** 如果在匹配计算量的强接收机上，给正确支撑或允许改变支撑都不再改善目标区间的 logloss/FER，而固定支撑内的推断改变已能回收主要余量，那么结构获取就不是主瓶颈。或者，现有标准接收机已经在无簇与真簇两类中，以相同代价取得全部收益，所谓新证据问题只在当前弱前端或特殊表示中存在，那么它作为论文中心的价值就消失了。单个新评分器失败不足以否定这个问题；但也不能用“这个评分器还不够好”无限保护它。

**候选二：当物理射线不能稳定分辨时，什么样的信道描述仍足以支持可靠译码？**

这个问题的核心不是换哪一种基，而是：**接收机必须知道信道的哪些作用，必须保留哪些不确定性，才能输出可信的比特概率；哪些射线细节只是表示上的自由度？** 同时要求：如果两种表示具有相同的物理信道作用、相同的诱导先验和同一份观测，就不能把仅由坐标拆分产生的信心当成新证据。

它对需要跨不同散射结构工作的接收机更重要。一个整数时延抽头内可以只有一条 Doppler 射线，也可以是多条近邻射线；精确恢复每条射线的难度可能剧增，而它们合成的时变作用仍然可预测。审稿人的攻击则会变成：**这是否只是把已有 BEM 或标准变分增益更新移植过来？你到底识别了哪一种与译码有关、现有描述方式遗漏的边界？** 因此，单纯通过一个表示不变性检查，或把完整 Gram 放回去，都不足以构成贡献。

它能自然容纳的已验收现象，与候选一不同：

- **信道误差离下界仍远，译码却已接近真信道参照。** 主线在 \(\rho=.5\) 的 FER 穿越点距真信道约 .12–.14 dB，但信道 NMSE 距约束 MCRB 仍有数 dB。两者不是同一个损失函数，所以这不构成矛盾；一个面向译码的理论应说明，剩余信道误差中哪些方向实际改变了比特证据，而不是把 NMSE 缺口全部当作可用 FER 余量。[res-20261015-02](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261015-02.md)、[res-20261016-02](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261016-02.md)

- **“更像真实射线集合”不是足够的优劣排序。** 完整 Γ 在 CSTATE 和 SBL 中都抑制额外同延迟原子，译码方向却相反。这要求评价整个信道表示及其不确定性怎样进入检测器，不能仅数恢复了几条真径或多出几条原子。[res-20261017-03](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-03.md)

- **同一个码的成功边界可能更接近软信息质量，而非信道参数误差。** C1 的已验收结果中，被测输入族的译码转折落在接近的互信息指标附近；但单标量状态闭合失败。这提示目标对象确实在软信息层，同时禁止我们把它压成一个普适 MI 阈值。[res-20261009-01](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261009-01.md)

更直接的表示不变性探针、NMSE 改善而 FER 恶化、同延迟簇接收机结果，目前提供了重要支持线索，但其中不少是探索性或待验收结果。我不把它们冒充已验收的统一机制。尤其均匀复制原子的反例只证明当前近似存在表示敏感性，没有证明它解释了实际 SBL 的排序反转。[表示探针](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)

它背后的不可越过边界是：**观测只能辨认会改变观测分布的对象，不能辨认纯粹的参数冗余。** 两条完全重合路径的增益只能以和的形式进入信道；分别恢复两个增益没有唯一答案。但这条不可能性不阻止译码，因为译码可能只需要那个和。因此，一个“射线估计下界”不自动成为“译码下界”，尤其在参数碰撞或冗余表示处。

数学上可搬过来的是**等价类与可观测量**：把产生同一信道算子的参数表示放进同一个等价类，真正的推断对象是这个类对数据的作用。在保持物理先验一致的前提下，精确预测分布不应随参数改写而变；近似推断则未必保持这一性质。相关问题也出现在近似贝叶斯推断的重参数化不变性研究中，但原子复制是冗余映射，不必是可逆坐标变换，不能直接照搬其定理。[Roy et al., NeurIPS 2024](https://papers.neurips.cc/paper_files/paper/2024/hash/0f934dd2030f5740cde0aa2697a105a9-Abstract-Conference.html)

这提供一个严格的“什么不该变”，却还没有提供“怎样使 FER 变好”。logloss 的作用则是评价输出的概率判断：它属于 proper scoring rule，评价的对象与参数平方误差不同；这支持用软信息作为任务目标，但不保证任意有限迭代译码器的 FER 随平均 logloss 单调下降。[Gneiting–Raftery, 2007](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

**什么结果会让我放弃它作为论文中心？** 如果采用标准的、保持物理先验一致的推断后，等价表示敏感性已经消失，但真实近邻原子、不同初态和支撑错误造成的 logloss/FER 差距几乎原样保留，那么“不变性”只是必要的一致性检查，没有解释主要性能墙。或者，如果一个现成块表示已覆盖全部目标场景，剩下的工作只是接上标准估计器，而没有新的可用性边界，那么这个问题虽然正确，却不足以承载这篇论文。

**我押注候选一：软数据究竟在什么条件下足以支持信道结构重获取。**

原因不是它能解释更多现象，而是它已经有一条较窄、较硬的证据链：支撑 genie 定位缺口；匹配额外轮数的消融定位动作；新帧复现定位稳健性；无簇与真簇对照排除简单禁令。最近的探索又表明，改变下游增益均值更新后，完整评分的优势缩小但仍然显著，说明它不是全部附着在某一个检测器缺陷上的现象。后一个结果仍是探索性证据，不能替代主线确认。[11 月评分×更新对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)

我押的是这个问题，不是“完整 Γ 就是答案”。它最终必须给出可提前判断的适用边界：什么情况下额外结构能提供译码收益，什么情况下只是重复拟合软数据误差，以及为什么同一个结构选择在不同下游会产生不同后果。否则它仍然只是对 CSTATE 成功的事后命名。

**最强替代是候选二。** 如果候选一的收益在竞争性标准接收机中消失，而保持同一物理作用时的表示或不确定性处理仍能稳定改变 logloss/FER，我会转押第二个。它可能更深，但目前从“精确的等价表示反例”到“真实接收机的主要性能损失”，还缺一座经检验的桥。首选一为中置信；第二个能成为独立主线的判断为中低置信。这是本轮的问题押注，不改变现有 TCOM 主线或已接受科学主张。

**本轮独立评估状态。** 主会话判断已先在提交 f1434149 固定，之后才请求一次不提供本会话结论的 Claude Sonnet 独立评估。自动审批拒绝该请求，理由是证据摘要包含私人、未发表的科研结果，而本轮没有明确授权向该第三方披露；独立评估未执行，也未形成模型分歧表。没有改走其他服务或间接执行。本轮押注仅代表主会话判断。所采用的 [research-checkpoint](/Users/guoyikun/.codex/skills/research-checkpoint/SKILL.md) 第 4 节要求：“Ask a different model for an independent assessment: give it the question and the evidence, not your conclusion.” 已向 Eric 询问是否允许发送该证据摘要；在取得明确授权前不重试。本轮未运行新仿真，未修改科学结果或主线状态。

# 第 3 轮

这一轮我需要收窄上一轮的押注：**我押的是第一个问题值得解，不是我已经有了能解开它的核心想法。按你现在的要求，第一个暂时没有；第二个有能严格消除一类伪难点的核心原则，但它属于已有方法的基础，尚不足以成为一个新的 TCOM idea。**

下面分别说清楚。不能把一个已实现的计算换个名字，也不能把一个一致性保证当成性能保证。

**第一个问题：怎样判断软数据是否支持新的信道结构。**

目前最接近核心想法的一句话是：

> **不评价“多拟合了一条路径”，只评价“在已有信道及其共同数据不确定性之外，增加了多少新解释能力”。**

它确实能从问题结构推出。当前软数据给出均值和方差；候选路径不只共享均值产生的波形，还共享同一份数据误差。因而比较候选时，应先消去其他路径已经能解释的部分，再计算剩余方向的增量。只在均值波形上做正交化，会漏掉不确定性方向的相关性。

把这个想法写成数学，可以看清它有没有新内容。固定当前软数据工作分布，令 B 的每列为一条路径作用在“导频＋软数据均值”上的响应；Γ 是数据不确定性投影到路径坐标后的矩阵；Λ 是该局部增益先验对应的正则项。记

\[
Q=B^HB+\Gamma+\Lambda,\qquad b=B^Hy.
\]

这里 y 是 N 维接收观测，B 是 N×P 的均值响应矩阵，Γ 和 Λ 都是 P×P 矩阵；Γ 来自当前软数据的二阶矩，Λ 来自工作先验及噪声尺度。Q 是局部二次目标 J(h)=‖y‖²−2Re(hᴴb)+hᴴQh 的曲率矩阵，b 是响应与观测的相关向量。保留路径集合为 S，考虑候选 c；在 Q 正定、软数据分布保持不变的条件下，加入 c 能降低的二次目标恰好是

\[
G(c\mid S)=
\frac{\left|b_c-Q_{cS}Q_{SS}^{-1}b_S\right|^2}
{Q_{cc}-Q_{cS}Q_{SS}^{-1}Q_{Sc}}.
\]

分子是扣除已有解释后的相关，分母是扣除已有方向后的曲率。这是 Schur 补恒等式，不是新的信息论量，也不是译码收益。

**关键核对结果：CSTATE 现在已经在做这件事。** 现有代码先构造完整 Γ 的 Q，再用这两个 Schur 项给替换候选评分，并核对直接求解的目标值。因此，“条件创新评分”“消除共同误差后再选路径”都不能作为本轮新提出的算法。[现有目标与评分](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:70)、[Schur 计算](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:177)

它已经能减掉某些补丁的必要性：不必仅因为两个原子同延迟，就一律禁止其中一个；也不必先规定“间隔小于某个阈值就是假径”，再靠删除规则救场。已验收的无簇/真簇对照表明，完整 Γ 在这两类中都能保留收益，而固定禁令不能。[res-20261017-02](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261017-02.md)

但这还没有让核心难处消失，原因有两处。

第一，**这个二次目标相信的软数据分布，本身可能已经被错误信道带偏。** 完整计入一个错误工作分布的协方差，不等于获得了正确的结构证据。

第二，**目标下降与译码改善之间还没有保证。** 它保证的是在给定工作分布下更好地解释观测，不是给定真实比特后更低的 logloss，更不是有限迭代 LDPC 的 FER。连完全重复的物理方向也要小心：无先验的数据拟合中，它不增加解释空间；但若复制参数时重新分配了独立增益先验，正则化目标仍可能变好，那是统计模型变了，不能算新观测证据。

所以我现在缺的，不是一个更巧的 Schur 公式，而是：**一个可计算的判据或误差界，能把“局部软数据目标更好”连接到“这次结构改变提供了更可靠的比特证据”，并说明何时这条连接会断。** 精确求整个码字与信道的联合后验，在定义上回答了问题；没有可承受的结构化化简，就还不是核心想法。

给一个便宜、可能失败的预测，用来检查这个缺口：

> **在已有完整 Γ 块交换的存档里，会出现至少一帧：交换被当前下降准则接受，最终 logloss 却比相同后端、相同额外轮数的 LOCAL 更差。**

我尚未逐行检查这个事件。它受已知总体结果启发，不是盲前瞻预测。检验只需读取本地块交换行：筛出 FULL 相对 LOCAL 改变了支撑的帧，比较二者 logloss，以 \(10^{-6}\) bits/bit 排除数值舍入；若全体都没有，预测落空。本地行已保存两臂的支撑和 logloss，可以零仿真检查。不过，它们没有保存全部候选目标值，因此只能核对“被既有准则接受的交换”，不能借此声称逐次重算了 Schur 评分。[存档及协议](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/dpss_block_rescue_20261110/PROTOCOL.md)、[逐键行入口](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/dpss_block_rescue_20261110/out/rows-00.jsonl)

若找到反例，只能否定逐帧单调保证；不能否定平均收益，也不能证明唯一失败机制。这是一个辨认缺口的预测，不是我尚未找到的新方法的性能预测。

**最强反驳是：这里不过是已有数据辅助估计的正确实现，研究者正在给一个 surrogate 的失配重新命名。** 目前我无法彻底反驳它。若没有上述从结构证据到译码风险的连接，我不认为“把 Γ 算完整”就达到了你要的核心 idea 标准。

**第二个问题：什么信道描述足以支持可靠译码，而无需分清每条射线。**

这一项有一个更明确的核心想法：

> **把未知量定义为每个时延的合成时变抽头，并把先验定义在这个物理对象上；射线只作坐标，不能因坐标拆分而改变推断问题。**

为什么是它？在整数时延模型中，把已知 CPP 相位归入对应移位算子后，同一时延 ℓ 的未知时变作用可写为

\[
g_\ell[n]=
\sum_{i:\ell_i=\ell}h_i e^{j2\pi\nu_i n/N}.
\]

这里 n=0,…,N−1 是帧内采样索引，νᵢ 是以一帧倒数为单位的归一化 Doppler，hᵢ 是复增益；gℓ 是这一帧内的有效时变抽头向量，右边是一种射线分解。观测和译码依赖左边合成后的作用。两条射线完全重合时，改变它们各自的增益而保持和不变，不会产生新的物理信道。

因此，若任务只要求可靠译码，接收机没有义务先把右边每个 hᵢ、νᵢ 辨认清楚。**那个没有唯一答案的分解可以从必做任务中消失。** 这不意味着可以不估计信道作用，也不意味着真簇只需一条射线近似。

这里比“换成 DPSS”更根本的一点，是先验必须一起变换。举一个能严格算清的极端情形：原来一个增益的工作先验为复高斯、方差 τ；将它精确复制成 k 个相同原子的增益。若这些复制增益独立，每个方差取 τ/k，则合成增益的方差仍为 τ：

\[
\operatorname{Var}\!\left(\sum_{r=1}^{k}h'_r\right)
=\sum_{r=1}^{k}\frac{\tau}{k}
=\tau.
\]

初始均值也相应分配，物理观测模型保持不变。若不同原子复制次数不同，就应分别按各自 kᵢ 分配；把所有新坐标统一设为 \(1/P'\)，通常会让被复制得多的物理路径获得更大先验功率。那已经不只是换表示了。项目已有推导明确指出了这个问题；原来的均匀复制数值验证不能被误写成非均匀复制的一般验证。[完整增益更新与先验边界](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/10-20-sbl-freeze-replay/research/full-gram-gain-block.md)

由此能得到两个层次的保证。

**严格层面：** 固定编码、符号先验和噪声模型，且信道与发送数据的先验独立；若两个参数表示诱导出相同的物理信道先验，且似然只通过同一物理信道作用依赖参数，那么精确推断的合成信道后验、比特后验都相同。它们只是同一个概率模型的两种写法。固定软数据工作分布时，保留完整耦合的局部高斯更新也能得到相应的合成均值、协方差一致性。

**尚无保证的层面：** 近似消息传递、历史状态、阻尼和有限迭代未必保持上述一致性。甚至保持一致性，也不保证更低 FER。现有原生 point 更新在均匀复制、物理先验已匹配时仍改变输出，正说明“只修正先验缩放”还不够；推断映射本身也必须按同一物理对象处理相关性。[等价表示探针](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md)

它能消除的是一类明确的伪难点：为了同一个物理作用反复决定“这算一条还是两条径”，靠合并/删除重复原子修复坐标病态，以及因为原子数改变而重新调整物理先验。这些工作不应成为可靠译码的必要前置步骤。

仍然需要面对的是真实难点：哪些时延存在、抽头实际有多宽的 Doppler 内容、有限样本能估出多少有效方向、后验如何与译码器交互。宽块和窄块若表示的物理信道集合不同，就不是等价坐标变换；不变性定理不能保证扩宽有益，更不能抹掉已有逐步扩宽失败的结果。[新帧扩宽结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md)

它的最强反驳也很直接：**这就是有效抽头/BEM 与贝叶斯推断应有的一致性，不是新原理。** 项目已有文献映射还确认，完整期望 Gram 的数据辅助增益更新已有先例，不能重新包装为本项目的新算法。[已有算子对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)

真正缺的是一座性能上的桥：坐标敏感性究竟是不是当前主要 logloss 损失的来源，而不只是一个容易展示的数学缺陷？

为此，我给一个**低置信、可能被否定**的预测：

> **在同一工况内，对物理等价的原子复制越敏感的旧帧，从原生 point 更新切换到完整更新时，logloss 获益应越大。**

具体只用旧队列：给每个保存状态做同样的均匀双复制，保持物理先验和初始信道不变；根据已推导的一步公式，计算原生第一次增益更新在两种表示下的合成信道差异，用初始信道范数归一化，记为敏感度 s。再从已保存终值取

\[
d=\operatorname{logloss}_{\rm point}
-\operatorname{logloss}_{\rm full},
\]

d 为正表示完整更新更好。我预测 s 与 d 在相同场景/SNR 内呈正的秩相关；统计时按共享物理帧聚类，不能把四个工况当成四倍独立样本。

这个关联尚未检查。原生/完整更新的终值已有存档；s 需要旧观测、支撑、初始增益与消息状态做局部代数重算，不需新随机帧、SBL 重估或完整译码。本地汇总表不够，相关逐键状态登记在远端，所以不能声称现在凭本地 summary 就能完成它。[旧队列与数据位置](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sbl_freeze_replay_20261020/GRAM_COHORT_SUMMARY.md)

若关联稳定反向，预测失败；若区间很宽、正负皆可能，则证据不足，不能当成预测已被否定。无论哪一种，目前都还不能把“修复表示敏感性”确立为主要性能解释。它仍是正确的一致性原则，却不够支撑这条贡献。即使正相关成立，也只是支持线索，不能替代因果检验，因为不同旧帧还可能共享其他困难。

**目前的落点是：第一个问题缺少从结构评分到译码风险的可靠连接；第二个问题缺少从表示一致性到实际性能损失的因果连接。** 对第一个，我还没有新核心想法；对第二个，我有一个能消除分解歧义的已有原则，还没有把它变成新贡献的依据。此时把它们包装成“统一几何”“信息守恒”或“任务导向贝叶斯框架”，只会让名字先于证据。

本轮按 math-reasoning 核对了局部推导、先验条件和极端情形；没有新仿真、接收机或译码器调用，没有执行上述预测，也没有重试外部评估。以上是本轮讨论与候选预测，不是新增已验收机制或实验执行授权。


# 第 4 轮：局部支撑决策边界的独立推导与审计

你指出的层次区别成立。上一轮我把缺少端到端风险保证当成候选一的主要缺口，没有单独判断局部支撑决策理论的价值，这个判断过窄。

本轮结论是：**第 2 层可以形成严格 Proposition，但“只由强弱径功率比与物理 ρ 决定的普适充要阈值”不成立。** 可成立的理论由一般保留集的精确重复奖励恒等式、带明确假设的竞争阈值，以及有限间隔的适用边界组成。完整 Γ 消除的是数据不确定性的拆分奖励；当前代码的独立 ridge 仍然产生拆分奖励。

按 formula-derivation 的对象/假设审计，本推导状态为 **COHERENT AFTER REFRAMING / EXTRA ASSUMPTION**。对象固定为软数据工作分布下的局部二次目标，不把它换成真实条件似然或译码风险。推导链为：物理不确定性代价的不变量（恒等式）→ 坐标拆分降低代理惩罚（恒等式）→ 重优化后的 Schur 奖励（恒等式）→ 特殊两候选竞争边界（条件命题）→ 实际选径及 FER 解释（待检验）。没有新增科学验收或变更论文主张。

**1. 从真实代码的目标开始，而不是先假定一个功率公式。**

设 N 为帧内符号数，m=pilot+μ 为冻结的软均值向量，V 为残余符号工作协方差，U_p 为包含已知变换和 CPP 因子的酉路径算子，满足 U_pᴴU_p=I。B 的第 p 列为 U_pm，h 为待优化的复路径增益，y 为接收观测。令

\[
E=\|m\|^2,\quad u=\operatorname{tr}V=N\bar v,\quad
M=B^HB,\quad b=B^Hy.
\]

E、u、λ 均在同一未除以噪声的目标尺度上。在 V=\bar v I 的假设下，完整 Γ 可写成 \(\bar v\,\operatorname{tr}(U_i^HU_j)\)；仅知道方差均值，不足以把实际完整 Γ 的跨时延项置零。令 H=∑ₚhₚUₚ，一般不确定性代价是 \(\operatorname{tr}(H V H^H)\)。

本代码的 \(\Lambda=\lambda I\)，因此

\[
J(h)=\|y-Bh\|^2+h^H\Gamma h+\lambda\|h\|^2,\quad
Q=M+\Gamma+\lambda I,\quad
\hat h=Q^{-1}b .
\tag{1}
\]

几何评分实际传入的是 **λ=σ²_obs**，不是 σ²_obs P；后者属于另一层的 expected-Gram 增益均值更新。固定容量替换中 λ 不随保留集大小改变。[目标定义](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py:70)、[实际 ridge](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/e1_driver.py:219)、[下游不同 ridge](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/cstate_score_update_20261111/joint.py:12)

对于同一保留集 S，候选 c 的重优化收益为

\[
G_c=\frac{|b_c-q_{cS}Q^{-1}b|^2}
{q_{cc}-q_{cS}Q^{-1}q_{Sc}}.
\tag{2}
\]

这是代码中的 Schur 评分；比较两个候选的 G 必须使用同一个 S。不同替换槽位的基准目标不同，不能跨槽位直接比较 G。

**2. 一般保留集下，精确重复候选有一个非黑盒闭式。**

假设幻影候选是保留集第 j 条原子的精确复制；相位等价复制可先对齐坐标。令

\[
a_j=(Q^{-1})_{jj},\qquad \hat h_j=(Q^{-1}b)_j,\qquad
\delta=
\begin{cases}
u+\lambda,&\Gamma=uI,\\
\lambda,&\Gamma\text{ 完整}.
\end{cases}
\]

这里 \(\hat h_j\) 是删去待替换槽位后、按当前评分模型重拟合的增益，不能换成真值强径增益。两种评分的 Q、a_j、\(\hat h_j\) 一般也不同。

重复候选满足 \(b_c=b_j\)、\(q_{cc}=Q_{jj}\)。均值响应列相同；完整 Γ 的对应列也相同，独立 ridge 没有候选交叉项。因此

\[
q_{Sc}=Qe_j-\delta e_j,\quad
b_c-q_{cS}\hat h=\delta\hat h_j,
\]

\[
q_{cc}-q_{cS}Q^{-1}q_{Sc}
=2\delta-\delta^2a_j.
\]

代入得

\[
\boxed{G_{\rm dup}
=\frac{\delta|\hat h_j|^2}{2-\delta a_j}.}
\tag{3}
\]

这是一般 S 下的精确恒等式，不需要忽略 BᴴB 的交叉项。完整 Γ 的重复列性质也不要求 V 均匀。当前 λ>0 时分母正；由于 \(Q\succeq\delta I\)，有

\[
\tfrac12\delta|\hat h_j|^2\le G_{\rm dup}
\le\delta|\hat h_j|^2 .
\tag{4}
\]

这给出了奖励的闭式尺度，但不能把两种评分不同的 \(\hat h_j\) 当成同一个数来证明任意 S 上的性能排序。

它的物理来源可以直接从能量看见。在均匀 V 下，

\[
h^H\Gamma_{\rm full}h
=\bar v\Big\|\sum_p h_pU_p\Big\|_F^2 .
\]

把同一算子的增益 g 拆成 g/2、g/2，物理 H 与上式均不变；而标量代价由 u|g|² 降到 u|g|²/2。**固定合成增益时，虚假的不确定性奖励恰好是 u|g|²/2。** 独立 ridge 也由 λ|g|² 降到 λ|g|²/2。继续优化合成增益及其他路径，才得到式 (3)，不能把固定增益的 u|g|²/2 与重优化后的 G 混为一谈。

因此完整 Γ 不是“重复候选永不获益”：代码 ridge 下，它仍有 \(\lambda|\hat h_j|^2/(2-\lambda a_j)\)。若复制前后保持合成增益的先验一致，两份增益各取原方差的一半，即各用 2λ 的 ridge，则完整模型的重复收益为零；标量不确定性仍存在拆分奖励。这个匹配要同时修改两份坐标，不能只改新候选，也不能一律用新的总 P 重置所有路径先验。

**3. 强径与真弱径之间，什么时候能写成功率阈值？**

先明确一个可证明的分析截面：S 只有强径，或其他保留方向与此竞争块完全解耦；V 均匀；强、弱候选均是正确的物理原子；两个均值响应满足 B_sᴴB_w=0；观测在这两列上没有残差投影。最后一个条件写 e=0 即可满足，但并非真实突发帧的一般事实。

用 \(H_s,H_w\) 表示真增益，避免与 \(\hat h_j\) 混用，设

\[
y=B_sH_s+B_wH_w,\qquad T=E+u+\lambda.
\]

于是 \(b_s=EH_s,b_w=EH_w\)。直接代入式 (2) 得

\[
\boxed{
G_A^{\rm sc}=
\frac{E^2|H_s|^2(u+\lambda)}
{T(2E+u+\lambda)},\qquad
G_A^{\rm full}=
\frac{E^2|H_s|^2\lambda}
{T(2E+2u+\lambda)}.
}
\tag{5}
\]

弱径得分在这两个模型下相同：

\[
\boxed{G_B=\frac{E^2|H_w|^2}{T}.}
\tag{6}
\]

该截面下，标量相对完整评分多出的重复收益还可精确分离：

\[
G_A^{\rm sc}-G_A^{\rm full}
=\frac{2uE^2|H_s|^2}
{(2E+u+\lambda)(2E+2u+\lambda)}.
\tag{7}
\]

对 E>0、H_w≠0，令 R=|H_s|²/|H_w|²。两个充要条件分别是

\[
\boxed{
G_A^{\rm sc}>G_B
\iff R>1+\frac{2E}{u+\lambda};
\qquad
G_A^{\rm full}>G_B
\iff R>1+\frac{2(E+u)}{\lambda}.
}
\tag{8}
\]

等号为打平。因此

\[
1+\frac{2E}{u+\lambda}<R<
1+\frac{2(E+u)}{\lambda}
\tag{9}
\]

是“标量选幻影、完整选弱径”的严格分歧区间。这是我认为可作为 Proposition 的核心可解释结论，而不是把 Schur 公式再抄一遍。

定义本推导中的有效均值能量比例和无量纲 ridge：

\[
\rho_{\rm eff}:=\frac{E}{E+u},\qquad
\alpha:=\frac{\lambda}{E+u}.
\]

注意这是明确新定义的软状态比例，不是发射导频比例。式 (8) 化为

\[
R_{\rm sc}^*=\frac{1+\rho_{\rm eff}+\alpha}
{1-\rho_{\rm eff}+\alpha},\qquad
R_{\rm full}^*=\frac{2+\alpha}{\alpha}.
\tag{10}
\]

等价的控制量是 \(N\bar v/E\)、λ/E 与强弱径功率比；\(\bar v\) 单独不是无量纲参数。

极端核验：u=0 时两模型相同；固定 u>0、λ→0 时完整重复收益趋零，而标量仍有正奖励。λ=0 的精确重复完整矩阵奇异，原 Schur 比值是 0/0，必须通过最小目标值或极限定义收益为零。E=0 时所有均值相关 b 都为零，候选得分全零，不能继续使用功率比阈值。

“打败 B”还不等于实际接纳：设同一槽位原候选的增益为 G_old，实际替换还要求 \(G_A-G_{\rm old}>10^{-10}(1+|J_{\rm current}|)\)，并在全局合法候选中胜出。代码拒绝 Doppler 间隔小于 10⁻⁶ 的重复原子，式 (3) 是允许近重复候选的极限，不是说代码实际接受精确复制。

**4. 哪些项会破坏简式，以及近重合怎样落到有限间隔？**

跨时延只保证均匀 V 下 Γ_sw=0，不保证 B_sᴴB_w=0。令

\[
\kappa=B_s^HB_w/E,\quad
y=B_sH_s+B_wH_w+e,\quad
\epsilon_s=B_s^He,\quad\epsilon_w=B_w^He.
\]

则

\[
b_s=E(H_s+\kappa H_w)+\epsilon_s,\quad
b_w=E(\kappa^*H_s+H_w)+\epsilon_w,
\]

\[
G_A^{\rm sc}=\frac{(u+\lambda)|b_s|^2}{T(2E+u+\lambda)},\qquad
G_B=\frac{|b_w-E\kappa^*b_s/T|^2}
{T-E^2|\kappa|^2/T}.
\tag{11}
\]

真实的两候选充要条件现在是

\[
\boxed{
(u+\lambda)|b_s|^2(T^2-E^2|\kappa|^2)
>(2E+u+\lambda)|Tb_w-E\kappa^*b_s|^2 .
}
\tag{12}
\]

它显式依赖相位、均值响应相关和残差；只有加回第 3 节假设，才能缩成式 (8)。

确定性反例：E=1、u=.4、λ=.05、κ=.4、H_s=1，分别取 H_w=.4 和 −.4，二者功率比均为 6.25。循环移位算子具有零迹，而所选均值向量使 κ=.4，故不是把算子正交与均值正交混为一谈。

| 弱径增益 | 标量幻影得分 | 弱径得分 | 胜者 |
|---|---:|---:|---|
| +.4 | .170449 | .171985 | 真弱径 |
| −.4 | .089379 | .040082 | 幻影 |

所以，**没有仅由功率比、ρ_eff 与 λ 决定的普适充要阈值**；即使 |κ| 也相同，弱径相位仍能改判。

有限 Doppler 间隔还包含第二个相干量：

\[
D=\operatorname{tr}(U_s^HU_c)/N,\qquad
\kappa_c=(U_sm)^H(U_cm)/E .
\]

D 是算子相干，κ_c 是该帧均值波形相干，两者一般不同。完整交叉项是 Eκ_c+uD，标量交叉项只有 Eκ_c。不能把所有交叉项都写成同一个 D。

作为可核验的特殊有限间隔截面，当 κ_c=D、y=B_sH_s 时，令 (a,c)=(u+λ,E) 对应标量，(λ,E+u) 对应完整，则

\[
G_A(D)=
\frac{E^2|H_s|^2|D|^2a^2}
{T[T^2-c^2|D|^2]} .
\tag{13}
\]

这解释了为何不能随意用一个 |D|² 因子乘在零间隔阈值上：Schur 分母也依赖 D。式 (13) 的核验不含真弱径；要拿它与式 (6) 直接竞争，还需弱径响应对相关列正交，不能偷偷补这个条件。

一般有限间隔可以保留一个有保证的余量界。固定 Q、b 与候选对角 T，记零间隔的残差和 Schur 分母为 z₀、d₀，候选变化为 Δq、Δb_c。令

\[
\varepsilon_z=|\Delta b_c|+\|\Delta q\|\|\hat h\|,\quad
\varepsilon_d=2\|Q^{-1}q_0\|\|\Delta q\|
+\|Q^{-1}\|\|\Delta q\|^2 .
\]

若 ε_d<d₀，则三角不等式给出

\[
\frac{(\max\{|z_0|-\varepsilon_z,0\})^2}{d_0+\varepsilon_d}
\le G_A(\Delta\nu)\le
\frac{(|z_0|+\varepsilon_z)^2}{d_0-\varepsilon_d}.
\tag{14}
\]

用下界仍胜过 B，才能保证有限间隔下不改判；只是“Δν 看起来小”不够。λ 很小时余量界可能很松。码中 .25 的搜索步长与实际保留 Doppler 的距离必须逐候选看，不能假定都在这个极限内。

**5. 本轮到底核验了什么。**

已编写并运行[小型 NumPy 脚本](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.py)，[完整输出](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/phantom_schur_audit_20261111.json)。使用确定性 16 维单位算子与复向量，没有随机物理信道、SBL、接收机或译码调用。

- 单路径及三条耦合保留路径，共 216 个精确重复用例：Schur 与直接增广矩阵最优目标差的最大绝对误差 1.18×10⁻¹⁶；与式 (3) 的误差 4.60×10⁻¹⁷。
- 162 个阈值用例：上下边界排序均符合式 (8)，平局最大绝对误差 5.59×10⁻¹³。
- 有限间隔公式 (13) 的最大绝对误差：标量 1.94×10⁻¹⁶、完整 1.08×10⁻¹⁶。
- 匹配复制先验后，完整重复奖励为 −2.22×10⁻¹⁶（数值零），标量仍为 .164414；λ=0 的完整目标用伪逆核对，增益为数值零。
- 上述相位反例实际得到反向排序。

这些是代数核验，不是物理机制的经验确认。独立 Codex 子代理给出了同样的闭式并审查扰动界；另一子代理只审查存档与代码字段。没有调用外部 Claude 服务，也没有把此评议当成期刊录用判断。

**6. 存档能检验什么，不能检验什么。**

真正应看的观测单位是“同一冻结软状态、同一个被替换槽位的候选比较”，不是最终有没有同延迟双径。

E-1/E-2 的逐帧行保存：
- arms.A1/A2.top5_step1：rank、slot、replacement.delay/doppler、score，score 是最小化目标，越小越好；
- arms.A1/A2.edits：step、slot、old、new、decrease；
- r1.delays/dopplers：交换前几何；arms.A1/A2.final_delays/final_dopplers：各臂最终几何；
- E-2 truth 的路径和复增益；E-1 可通过场景、物理 ρ、SNR、frame 键与 P1 的 truth_l/truth_k/truth_g2 对齐得到真值功率。

本轮核对的是序列化源码及本地汇总，没有读取远端全量行。E-1/E-2 的行没有保存 ce_mu、ce_variance、y、删槽位后的 \(\hat h_j\)、完整候选分数或第二步 shortlist，所以不能凭现有汇总重算式 (3)/(12)，更不能报告新阈值 AUC。[E-1 序列化](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e1_20261017/e1_driver.py:255)、[E-2 序列化](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/tf_cstate_e2_20261017/e2_driver.py:207)

可以零仿真做的有限检查是：预先固定槽位和类别，若 top5 中同时有两类候选，可取各类首个出现者得到实际类别最优分差；缺席类别只有排序界，没有精确分差。跨槽位必须比较目标值而非 G。真弱径还要求匹配尚未占用的真实延迟及 Doppler 网格邻近，不能把任何新延迟都叫恢复真径。E2 真簇中同延迟本来可能有真实信息，不能沿用 R 族的“同延迟就是幻影”标签。A2n 禁止 |D_N|≥.5，不能拿它检验近重合极限。

物理 ρ 的映射尤其重要。P1 把观测与导频除以 \(\sqrt{2(1-\rho)}\)，接收机内部数据功率固定为 .5；几何矩由裁剪后的第二轮 LDPC APP 重新计算。因此在接收机坐标中

\[
u=N/2-\|\mu\|^2,\quad
E=\|pilot+\mu\|^2,\quad
\lambda=\frac{10^{-{\rm SNR}/10}}{2(1-\rho)} .
\]

E 包含 \(2\Re(pilot^H\mu)\)，不能直接替换为 N(ρ+某个均值功率)。在 μ=0 的冷起点可得 ρ_eff=物理ρ；一般软状态下二者不相等，本次结构重开使用的已经是后续软状态。[归一化](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver.py:227)、[软符号矩](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_20260920/src/messages.py:7)

旧 H-RI 曾预测阈值 \(\rho/(1-\rho)^2\)，这与本轮固定目标、重拟合后的 \((1+\rho)/(1-\rho)\)（μ=0、λ忽略）不相同。旧阈值在 ρ=.3→.5 是 .612→2；本轮该特殊截面是 1.857→3，约 +2.08 dB，不能把旧检验直接当新公式的检验。

旧 A2n 条件样本中 phantom 比例 .175→.578，与“固定其余量时增大 ρ 会抑制幻影”的方向相反；旧带 ρ 评分相对基准的 ΔAUC=−.067，去掉 ρ 因子后 AUC=.812。这个已知失败必须保留。它没有单独否定含真实软状态的新公式，因为样本受触发、接受交换、缺失径及 SNR 构成筛选，而且 A2n 本身不在近重合范围；同样也绝不能用这些理由宣布新公式已解释趋势。[旧协议与更正后的结果](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/posthoc_rank_inversion_20261019/SUMMARY.md)

**7. TCOM 审稿人会接受哪一层逻辑。**

我认可你提出的论证分工：**局部决策 Proposition + 独立端到端验证，是成立的研究结构；没有必要证明每帧 logloss 单调下降。** 但现有证据不能把整条因果链称为已经封口。

最有希望的理论主张是：分数 Doppler 的算子相干使“系数惩罚”与“物理不确定性代价”分离；遗漏这项相干会产生可精确量化的冗余奖励，并在明确条件下把固定容量支撑决策从弱径恢复翻向重复强径。一般 S 的式 (3) 保留实际耦合，式 (8) 提供可解释切片，式 (14) 限定有限间隔的适用性。

项目内也已有相关基础：10 月 18 日的记录已写出标量 m 份拆分的 u|h|²/m 惩罚，10 月 19 日已尝试过另一版竞争阈值。因此本轮价值是核实并修正从拆分到决策的推导，不能把“拆分奖励”本身当成新发现；文献新颖性仍需单独界定。[已有拆分讨论](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/research-assets/res-20261018-02.md:55)、[期望 Gram 算子对照](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/10-20-sbl-freeze-replay/research/operator-mapping.md)

有五个必须正面处理的漏洞：

1. **先验混淆。** full 也有 ridge 拆分奖励。若宣称“完整 Γ 恢复整个目标的不变性”，现代码就是反例。应区分数据不确定性项、先验项及二者共同导致的净决策。
2. **真实候选覆盖。** 精确复制被拒绝；真实均值交叉、非均匀 v、Doppler 错配和残差会改判。若实际错误选择大多不在命题的有限间隔/余量覆盖内，命题正确也不能承担主要机制解释。
3. **已知数学与新贡献。** 二次惩罚对重复变量的均分效应并不新；Zou–Hastie 2005 的 Lemma 2 已讨论严格凸惩罚对相同预测变量给相同系数。[原论文](https://web.stanford.edu/~hastie/Papers/B67.2%20%282005%29%20301-320%20Zou%20%26%20Hastie.pdf) 结构相同的是坐标冗余改变系数惩罚，不是说该文已有 AFDM 的式 (8)。完整期望 Gram 也已有 DD 数据辅助估计先例。本轮只能说提出了一个待定位的局部决策命题，不能声称首次发现这个原则；本次检索不是系统查新。
4. **已有实验的证据职责。** P1/E-1/E-2 预注册支持各自冻结的性能/干预结论，不能追认今天推导的阈值曾被预注册。最新 2×2 是 251 个旧触发行、107 个帧簇、物理 ρ=.3 的探索性 replay；完整结构评分的条件 FER 优势在原生更新下为 54.98 pp，换增益均值更新后仍有 37.85 pp，缩小 17.13 pp。这支持结构评分效应不完全依赖原生更新缺陷，但它没有测式 (3) 的拆分奖励，也没有验证阈值；共用 full Γ 局部细化且只替换增益均值，更不是任意检测器下的结论。[2×2 记录](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-22-tf-production-gap-audit/research/deinlab-receiver-screens-20261111.md:19)
5. **“相变”用词。** 目前得到的是有限维、固定状态的确定性决策边界。没有渐近成功概率或集中性分析时，不能把它写成普适统计相变。用“decision boundary”更准确。

最强替代解释仍是强径的 Doppler/增益失配残差：它也会让同延迟候选获益，且随强径功率增长。仅靠 phantom 数量与 FER 的关联不能把它与不确定性拆分奖励区分开。新理论必须在实际冻结状态中解释候选分差，而不只是事后解释终端输赢。

**我的修正判断：这条第 2 层理论线值得保留，且已比“Γ 应该算完整”更具体；它现在具备一个数学上自洽的 Proposition 候选，还不具备“已验证的核心机制”地位。** 把它提升为核心理论点，最缺的是实际选径状态下对收益分解和候选胜负的预测覆盖，而不是端到端单调性定理。结论置信度：代数高；主要机制解释中低；TCOM 核心贡献是否充分仍未定。旧结果卡、否定账本与当前主线均未改写。
