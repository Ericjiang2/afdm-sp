# 共享信道概率、碰撞坐标与生产失败归因

本轮补齐了上次没有执行的中间概率层、碰撞有效信息、观测估计、合法正权求积及生产配对诊断。结论是：**尚未发现能解释旧失败的算术或接口错误；旧负结果确实不足以否定整个方向。内部联合更新是本批成功的重要条件，但保留共享增益混合也并非处处改善概率。**

来源为会话 `01a1007e-b82a-70c0-bcb2-fec08e9b17cc` 最后未完成的 Mission 请求。原始讨论、执行合同、12 项任务与最终审查均在[本轮目录][mission]；此前已完成的 19 项研究和所有旧结果保持原样。这里是开发性研究结论，不修改论文的已接受主张或关闭研究父任务。

## 1. 旧生产失败现在能解释到哪一步

使用原来的六个 N=1024 观测，来自三个外生簇、每簇 10/20 dB。先把原 joint20 和 pair 的全部保存数值数组回放到**差异为零**，再改变内部更新次数和增益处理。所有前端数组完全一致，使用原 LDPC 译码器，共 36 次实际接收/译码调用；原有 24 份结果重计分也完全一致。

| 接收处理 | 内部更新 | 错帧 / 6 | 译码后错误位总数 | 平均译码输入 bit log-loss |
|---|---:|---:|---:|---:|
| 原生联合更新 | 20 | 0 | 0 | 0.061248 |
| 原生联合更新 | 1 | 6 | 3947 | 0.638940 |
| 旧 Gaussian pair | 一遍 | 6 | 1252 | 0.334168 |
| 固定前端增益的原生更新 | 1 | 6 | 2329 | 0.455659 |
| 固定前端增益的原生更新 | 20 | 6 | 1635 | 1.007613 |
| 固定前端 H 的 Gaussian-outside pair | 一遍 | 3 | 619 | 0.278786 |

实际保存的状态确认：1/20 次更新不是仅修改了选项；每组的首个状态一致，固定增益确实不变，joint20 的增益确实更新。由此可回答原先的疑问：**“原方法一轮成功”不能解释为“一次检测足够”，那一轮内有 20 次信道—数据联合更新。** 固定 H 的 pair 救回了三个 20 dB 观测，说明使用前端拟合增益的方式也会影响结果。

但固定增益的原生模式同时去掉了增益方差；固定 H pair 同时改变了增益模型及使用观测的方法。这些是复合干预，不能把改善独占归因于某一种概率近似。fixed20 的错误位更少而 log-loss 更差，也说明“更多迭代”不是跨模型、跨指标的普遍改进。这里的分母是六个复用观测，不是独立新鲜 FER 确认。

证据：[生产结果][production]、[逐状态核验][states]及[完整接口说明](../../experiments/afdm_shared_channel_20261004/PRODUCTION.md)。独立算术审计覆盖 N=2/4、两种噪声和单/双符号块，旧快速似然与稠密实现最大差 `1.42e-13`，条件二阶矩与完整外部 QPSK 枚举最大差 `2.22e-15`。这验证了它计算的 Gaussian，未证明 Gaussian 等于真实混合分布。

## 2. 三层概率对象：误差确实存在，也确实会抵消

同一观测上比较：

\[
p_{\mathrm{QPSK}}(y\mid d_B)
\quad\leftrightarrow\quad
\mathbb E_h\,\mathcal{CN}(y;\mu_h,S_h)
\quad\leftrightarrow\quad
\mathcal{CN}(y;\mathbb E\mu_h,\mathbb ES_h+\operatorname{Cov}\mu_h).
\]

第一步近似外部数据；第二步进一步压缩共享信道混合。非均匀 I/Q 先验会产生 improper 外部 Gaussian，本实现用实增广协方差保留它，没有强行套 proper 公式。

N=3、P=1/2，包含单/双符号块、两种噪声、均匀/非均匀外部 cavity，Gaussian 和受控单位球面增益各 48 行，共享三个外生抽样簇。Gaussian-QPSK 参考由解析增益消元与有限枚举得到；球面两种积分都只是经过收敛检查的数值参考。

初次低阶规则中，24 个低噪声 Gaussian 案例未收敛。保留它们后，读取原观测，对全部 48 个 Gaussian 案例使用 Sobol 加密、独立 scramble 和 Hermite 交叉核验。最终 96/96 达到预登记数值门；还检查了结论在多个已接受积分规则之间的敏感性。以下区间是**实际规则之间的数值变化范围**，不是置信区间或严格积分误差界。

定义 \(\Delta=\text{单 Gaussian 误差}-\text{共享增益混合误差}\)，正值表示混合更好。

| 先验 | 平均块 KL 的 Δ 范围 | 平均 bit KL 的 Δ 范围 | 块 KL 混合更好 / 更差 | 稳定误差抵消 |
|---|---:|---:|---:|---:|
| Gaussian | [0.002927, 0.002983] | [−0.000130, −0.000107] | 33 / 15 | 26 / 48 |
| 受控单位球面 | [0.019649, 0.019928] | [0.005581, 0.005699] | 41 / 7 | 21 / 48 |

Gaussian 下，平均块 KL 与 Brier 偏向混合，但平均 bit KL 与 LLR RMSE 略偏向单 Gaussian；联合概率更接近不保证每个边缘指标更好。还存在跨所有核验规则都稳定的反例：Gaussian 案例 80 的块 KL Δ 约 −0.0182；球面案例 57 约 −0.0308。因此，“增加混合保真度必然改善最终消息”已被本轮具体例子否定。两个近似误差可以相互抵消。

数据规模很小，非均匀 cavity 是固定的外部消息诊断，不能把这些行当成独立样本或泛化校准实验。完整两步 LLR 误差、交叉项、概率、log-loss、符号变化和失败的低阶结果均保存：[最终概率结果][probability]、[数值敏感性][sensitivity]、[概率对象与公式](../../experiments/afdm_shared_channel_20261004/PROBABILITY.md)。

## 3. 高阶结构与真实生产先验

proper Gaussian 外部 cavity 下，令投影条件均值能量为 \(h^HMh\)，条件方差为 \(v_0+h^HVh\)，其中 M 秩一，V 半正定。当 \(h\sim\mathcal{CN}(0,C)\) 时，混合与单 Gaussian 的四阶矩差为

\[
\Delta_4=4\operatorname{tr}(CMCV)+2\operatorname{tr}(CVCV)\ge0.
\]

总增益能量方差为 \(\tau^2/P\)，因此固定小 P 时增大 N 不能自动消除这项随机性。不过严格固定总能量后，上式不再成立：球面先验的四阶差可以为正、为负或为零。P=1、无固定目标均值、圆 Gaussian 输入时，共享相位就不会制造随机尺度缺口；具有固定目标幅度时则仍可能是非 Gaussian 相位混合。这些边界已用解析矩与正权积分交叉验证。

还有一个必须纠正的生产模型差别：旧生成器先按指数功率延迟谱产生增益，再按**截断 G0 信道矩阵 Frobenius 范数**归一化，G1 重用这些物理增益而不重新缩放。三个旧簇实际 \(\sum|g_p|^2\) 是 1.01601854、1.00986004、1.00894574。因此，上节单位球面实验只是受控比较，不能称为精确生产先验。

条件于真实几何和潜在功率谱 D，正确的归一化推前形式为

\[
h=\frac{D^{1/2}s}{\sqrt{s^HD^{1/2}R_{G0}D^{1/2}s}},
\qquad R_{G0,pq}=\frac1N\operatorname{tr}(U_{G0,p}^HU_{G0,q}),
\]

其中 s 为各向同性复球面方向。这保留了不同路径功率的角向权重和 G0 归一化，不能只把单位球面的半径调大。对应源码、历史潜变量复现及矩核验见[实际先验说明](../../experiments/afdm_shared_channel_20261004/PRODUCTION_PRIOR.md)。它是明确标注真实几何的离线模型核验，不是部署信道估计或 FER 归因。

这次只重放三个旧 channel RNG 流以恢复未保存的潜在 D，没有产生新观测或调用接收机。延迟完全相同，Doppler 差为零，原增益最大差 `6.21e-17`；缩放和独立稠密 G0 范数核验最大差分别为 `1.11e-15`、`2.22e-15`。原采样器在三个流中经历 23/26/1 次内部尝试，这些都是历史流的确定性重放。

八路径情况下，单位球面与 iid Gaussian 的任意单位投影二阶矩均为 0.125，但实际条件先验明显各向异性：

| 保存簇 | 第一路径二阶矩 | 末路径二阶矩 | 平均总能量 | 总能量方差 |
|---|---:|---:|---:|---:|
| 0 | 0.235178 | 0.0673595 | 1.0151813 | 3.76e-5 |
| 1 | 0.182727 | 0.0870595 | 1.0107269 | 8.50e-6 |
| 2 | 0.172331 | 0.0736124 | 1.0087081 | 2.44e-6 |

Sobol 的三个阶数、两个独立 scramble 均保留；二/四阶投影矩的最大加密或独立 scramble 相对差为 0.5385%，最细规则与独立正权 Laplace 积分最大差为 0.1086%，全部通过预登记 1% 门。上表使用 Laplace 参考；它的 128/256 阶差小于 `2.93e-14`，仍称数值参考。总能量方差的理论对照为单位球面 0、iid Gaussian 0.125；实际先验的能量随机性虽小，其路径角向权重仍不能省略。

这解释了为什么“旧 pair 使用精确二阶矩”必须加上“在其声明的 iid Gaussian 工作先验下”：它没有匹配这里的实际条件二阶矩。此发现增加了一个明确的模型失配来源，尚未测量它对 FER 的独立影响。这里始终条件于每个保存几何及恢复的潜在 D，未积分所有可能的潜在 D，不能称为无条件生产先验。原始矩与归一化证据见[实际先验结果][normalization]。


## 4. 碰撞坐标：有效信息有条件，换坐标没有创造信息

等权独立 Gaussian 增益、共同已知 delay 下，写 \(\nu_{1,2}=\mu\mp\delta\)、\(q=\delta^2\)。协方差展开为 \(K(q)=K_0+qK_1+O(q^2)\)。proper complex Gaussian 的信息没有实 Gaussian 的 1/2 因子；对中心、总功率、噪声投影后，

\[
I^{\rm eff}_{qq}=I_{qq}-I_{q\lambda}I_{\lambda\lambda}^{\dagger}I_{\lambda q},
\qquad I^{\rm eff}_{\delta\delta}=4\delta^2I^{\rm eff}_{qq}.
\]

80 个信息检查中，投影与 Schur 形式最大相对差 `1.05e-13`；q 缩小十倍时展开余项约缩小百倍。存在原始信息为正而 nuisance 投影后为零的具体反例。无导频、均匀未知数据时，本二阶矩模型为 \((\sigma^2+\tau p_d)I\)，关于间距的信息严格为零；这不等于完整高阶观测分布没有信息。

随后用真正观测 y 运行固定搜索域的中心/宽度估计，无真实中心初始化，并与原两路径坐标使用相同观测和物理初始网格。144 行仍仅来自三个外生簇。pilot 情形，两种坐标的 q RMSE 均约 0.210，48 行中各有 26 行落 q=0；固定软 cavity 情形，q 坐标与原坐标的 q RMSE 为 0.1815/0.1748。没有普遍改善，无导频情形 48/48 明确不输出不可辨识的估计。

结论是：q 提供了清楚的退化与有效信息表达，但本轮没有得到更好的通用估计器。q=0 的非正则边界、未知数据及 nuisance 不会因为改名而消失。见[信息结果][information]、[估计结果][estimation]及[推导与搜索合同](../../experiments/afdm_shared_channel_20261004/COLLISION.md)。

## 5. 合法概率与条件计算：能保证什么

正权、固定基测度和合法有限星座支撑保证同一 log-partition 产生均值、协方差与混合响应。数值微分最大误差约 `2.1e-11`，二值支撑方差恒等式误差 `1.94e-16`。外信息通过显式排除目标自身因子获得；未经 site 除法的同观测 \(q(h\mid y)\) 不能再当独立先验。

观测相关权重的反例中，固定基测度偏导为 0.05624，总导数为 0.46794，遗漏项约 0.41170；加回链式项后误差 `2.59e-11`。所以“共享凸势”“stop-gradient 后求导”本身都不能保证合法总响应或 Onsager。正权结构保证内部概率一致性，不保证逼近真实后验。见[求积与响应结果][message]。

在固定增益节点、均匀块外 DAFT 方差下，时域 CPP 稀疏矩阵可用于精确求解：先分解 \(B_0=\sigma^2I+vT_hT_h^H\)，再做目标块低秩 downdate。保留 CPP 跨边界项，不做逆矩阵截断；非均匀块外方差明确拒绝，不用平均方差替代。

测试覆盖 8 个完整有限节点消息：三个声明的正权增益节点 × 全部 \(4^b\) 个合法状态，N 从 16 到 1024。稀疏/独立稠密对照的概率最大差 `2.05e-14`，LLR 最大差 `1.82e-12`。本机 N1024 双符号完整有限消息耗时 9.54 ms，包含 3 次分解、3 次 downdate 和 48 次条件似然；同一次稠密参考约 750.63 ms。

这是单次有限三节点测度的计算比较，不是连续增益积分已收敛、整帧接收延迟或生产优势。连续先验可能需要很多节点，因子通常不能跨增益节点共享，非均匀 cavity 也破坏简单时域稀疏性。不能用“小 P”替代完整成本分析。见[求解器结果][solver]与[运算账本](../../experiments/afdm_shared_channel_20261004/SOLVER.md)。

## 6. 哪些自然方向还值得保留

**A：保留共享信道状态，但把有效迭代和合法 cavity 一起设计。** 数值证据支持“存在被压缩掉的消息信息”，同时给出了混合更差的稳定反例。下一项具体数学目标应是能控制消息误差的条件或界，以及在真实增益先验下可计算的近似；生产目标必须与同预算的内部联合更新比较。当前有限节点积分工具尚不是这样的完整算法。

**B：研究 nuisance 投影后的可辨识组合量。** 本轮给出了有效信息和失效边界，但观测估计没有普遍胜出。保留信息结构问题比继续提高自由 jet 阶数更有依据；目前不应把 q 坐标包装为已验证的接收性能贡献。

**C：把合法支撑、正权和完整响应当作 A 的结构约束。** 它们修复概率合法性的漏洞，不能单独承担新颖性。自由学习完整状态权重会改动先验，观测自适应权重/节点必须计算完整响应，不能漏掉变化项。

本轮补读了 AFDM 双域 EP 和联合检测—LDPC 稀疏图的全文。时域稀疏、LU、cavity、星座支撑和联合译码都有明确近邻；P-BiG-AMP、AFDM SBL、confluent Prony 也限制了宽泛创新主张。具体比较见[文献核验](LITERATURE.md)。本轮没有证实一个新的生产性能—成本优势，也没有证明研究空间耗尽。

## 7. 复现、失败记录与验收边界

从项目根运行全部新增合同检查：

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
/tmp/afdm-shared-channel-env/bin/python -m pytest -q experiments/afdm_shared_channel_20261004
```

各源模块及文档提供实际运行命令；最终 57 项新增测试全部通过（2.41 s），Python 编译检查及限定本任务路径的差异检查通过。未配置独立类型检查、构建或 lint 工具；编译检查不替代运行验证。注册文件保存完整 `_argv`、`_config`、种子、环境、源码 SHA、开始/截止时间和实际费用。已有 stage 拒绝覆盖；重新运行时必须使用新 stage 名。概率细化和敏感性工具明确读取并校验本轮保存输入。复现依赖旧项目冻结源码、检查点及本地保存证据，不能只复制新模块。

保留的执行偏差：生产 v1 在接收调用前因新诊断驱动漏记运行环境字段失败，花费 13.17 s，修复后 v2 完成 36 次调用；初始低阶概率积分未收敛，不作为最终参考；保存分数敏感性中的浮点符号保护修改与提交交接发生竞态，实际源码已被注册和快照完整保存，随后提交 `6ed0b30f` 与快照一致，记录的启动 Git HEAD 仍保留前驱值。这项偏差没有引起新的积分或接收调用，未重写原记录。

完整性核验覆盖 11 个 attempt（10 个完成、1 个保留失败），1997 项原始工件哈希和 1639 项源码快照哈希，差异为零；执行输出约 309 MB，低于 2 GB 上限。核验记录见 [VALIDATION.json](VALIDATION.json)，源码提交时序偏差见 [SOURCE_DEVIATION_RECEIPT.json](SOURCE_DEVIATION_RECEIPT.json)。失败 attempt 未生成终态工件哈希账本，其源码快照按原注册核验；此限制已单列。

所有研究保持原始输出与失败，不以成功子集替代全体；模拟/数学检查、旧观测诊断和独立确认分开。独立审查逐项通过九个原始目标；另从保存数组复算概率、碰撞信息、估计、完整有限消息和生产分数，未发现实质缺口。独立测试 57 项通过（2.37 s），交工单机械合同检查通过。见[审查收据](REVIEW_RECEIPT.json)、[施工交工单][handoff]，汇总数据见 [EVIDENCE_SUMMARY.json](EVIDENCE_SUMMARY.json)。

[mission]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/
[production]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/production_v2/results.json
[states]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/production_v2_state_receipt.json
[probability]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/probability_refined_v1/results.json
[sensitivity]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/probability_sensitivity_v1/results.json
[information]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/collision_information_v1/results.json
[estimation]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/collision_estimation_v1/results.json
[message]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/message_v1/results.json
[solver]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/conditional_solver_v1/results.json

[normalization]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/execution/normalization_v1/results.json

[handoff]: ../../.mission/20261004_11-00-00-afdm-shared-channel-followup/20261004_11-00-00-afdm-shared-channel-followup.handoff.md
