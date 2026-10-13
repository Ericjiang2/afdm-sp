# AFDM 四条结构化推断路线：研究结果与边界

本轮恢复会话 `01a0f27b-e6d2-74b1-be7c-5f2995ea31dc` 中未执行的结构化推断任务。四条路线完成了公式、反例和数值判别，并实现了一个真实接收机原型。**候选没有通过预登记的生产尺寸开发门：pair 在 6 帧中错了 6 帧，原 joint 的一轮、两轮版本均为 0/6；候选完整单帧均值约 0.709 秒，原两轮 joint 约 0.112 秒。**因此本轮没有得到新的性能—成本优势，也没有启动新鲜确认集。这是三个独立外生簇上的开发结论，不是总体零效应证明。

任务书及唯一逐行状态位于 [Mission 目录](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/PLAN.md)。可复用实现及分项推导位于 [实验目录](../../experiments/afdm_structured_inference_20261003/)。本报告区分公式、工作模型诊断、合法局部干预和完整接收机效用；这些层级不能互相替代。

## 已验证的核心结果

| 路线 | 实际发现 | 不能据此声称 |
|---|---|---|
| 模式结构与表示一致先验 | 同一物理先验下，平衡拆分路径仍改变标量算法输出；单轨道 C2 矩恒等式成立，未知轨道混合可以不再秩一 | 分槽敏感性必然导致生产 FER 损失；补一个交叉矩就能改善 bit LLR |
| 精确信道消元与软消息 | 真实 CPP 下的 Gaussian 增益积分及 score 通过独立检查；两次消息修订改善小模型，并进入实际 N1024 链路，但没有通过迁移门 | 精确 point score 就是精确数据后验；小模型改善保证生产效用 |
| 近碰撞组合坐标 | 固定正确中心时低阶 jet 对足够小间隔有效；中心误差和超出局部范围的间隔会使其失效 | 真几何参考就是可部署估计器；更高阶总能解决问题 |
| 单一概率势与学习积分 | 有限双线性势的导数合同成立；实际训练的共享势比独立头有更小部分误差，却输出非法有限支撑矩；合法单标量修正更准确 | 凸性、PSD 或导数一致性保证星座后验合法；小模型训练成功等于生产优势 |

## 1. 模式、先验与实际表示敏感性

必须先区分“同一物理模型换坐标”和“真正新增散射体”。当 `alpha=T beta` 时，均值和协方差必须同时满足 `m_alpha=T m_beta`、`C_alpha=T C_beta T^H`。

PRIOR 使用 3 个独立外生 draw、6 种条件和真实 `scalar_joint` 小模型调用。正确推送先验后，exact predictive、矩和 LLR 的最大差为 `8.88e-15`。从 UV 的 iid 1/2 改成 UUV 的 iid 1/3 改变了物理先验，其 LLR 差不构成算法缺陷；但 UV 与 UUVV 的 iid 1/4 **保持物理先验相同**，exact LLR 差不超过 `2.52e-15`，标量算法的 LLR L2 差却为 `0.06695–1.19304`。首次聚合增益更新已经不同，初始物理算子的舍入误差不足以解释该现象。

这些比较采用相同 20 轮和 41 次 FFT，不能称同算术成本或同延迟比较。随后复用这些输入调用已有 `block_amp`：六个条件的全部 20 轮轨迹均恢复表示一致性，最大 LLR 差为 `6.78e-15`。13 次真实调用包含单独计费的无观察器控制，确认观察器不改变结果。这说明已有块方法能避免已识别的标量缺陷，不是本轮发明了全协方差算法。块方法对 exact LLR 的误差在四个条件改善、两个变差，不能由不变性推出准确性或 FER 优势。详见 [BLOCK_REPRESENTATION](../../experiments/afdm_structured_inference_20261003/BLOCK_REPRESENTATION.md)。

ORBIT 使用短偶校验码与有限增益状态，覆盖无导频、不同导频强度、合法非均匀模式先验以及未知轨道混合。在固定合法轨道内，tanh/logcosh、非共轭交叉矩和预测矩公式误差不超过 `4.98e-14`。但混合未知轨道后交叉矩可为 rank 2，符号模式集中也不保证轨道集中。

一个直接反例尤其重要：把 exact joint 换成其 exact marginals 的乘积，会破坏增益与数据的交叉信息，却保持 bit LLR（差不超过 `1.78e-15`）。因此“预测交叉矩错了”本身不能推出“bit 决策差了”。尚缺可扩展的未知轨道权重和合法 factor-to-bit cavity；任意软向量加一个 tanh 不是闭合接收机。

详细证据：[PRIOR](../../experiments/afdm_structured_inference_20261003/PRIOR.md)、[ORBIT](../../experiments/afdm_structured_inference_20261003/ORBIT.md)。生产 LDPC 的 C2 代数证据复用旧哈希收据，没有用短码替代生产码检查。

## 2. 信道积分正确，数据积分仍是不同问题

`CollapsedModel.evaluate(y,x)` 接受 DAFT 域的 `y,x`，其中 `x=pilot+data`。它支持非零均值、相关及奇异 Gaussian 增益先验，在声明的支撑内求解，不加任意 epsilon 改造先验。

128 个案例、4 个独立 draw 的真实 CPP 检查中，score 相对误差最大 `1.71e-13`，多步长有限差分的最差最佳步长误差 `5.33e-10`。N=1024/P=8 的一次完整 kernel 报价约 `0.627 ms`，包含其 setup；这不包含接收机初始化、整轮数据消息与 LDPC，不能作为全链延迟。

MESSAGE 的 N=2 实验在相同 16 条件、4 个 draw 下比较了不同数学对象：

| 消息对象 | 对 exact marginal 的 LLR RMSE |
|---|---:|
| profile 后再边缘化 | 0.4692 |
| 固定 mean-H 后边缘化 | 4.3102 |
| exact collapsed 单符号条件 | 0.8912 |
| exact discrete marginal | 约 1.53e-15 |

精确条件 likelihood 并没有自动消除 nuisance data 的积分误差，且在该平均指标上不如 profile-marginal 对照。这不是信道积分公式错误；比较对象分别处理了不同的数据不确定性。

连续 Gaussian tilted 部分是真实 Gauss–Hermite 积分，不是离散 QPSK 枚举。非线性检查只允许一个复坐标不确定、另一坐标确定；17→25 阶的 covariance 变化不超过 `1.32e-8`，score identity 误差不超过 `1.02e-9`。另有四实维 correlated Gaussian 的 affine 解析极限，不能称全帧非线性积分验证。

自身 bit 入边排除、signed Gaussian site 相减及组合 precision 验证均有执行检查。真实双峰 likelihood 能产生负 site precision；site 作为因子可以带符号，但不合法的组合分布会显式拒绝，不靠裁剪变成假成功。

详细证据：[COLLAPSE](../../experiments/afdm_structured_inference_20261003/COLLAPSE.md)、[MESSAGE](../../experiments/afdm_structured_inference_20261003/MESSAGE.md)。

第一项反馈修订把每个局部消息从一个符号扩至两个符号，固定块外为零软均值。新 N=2 案例的 pair LLR RMSE 为 `1.89e-15`；新 N=4 案例从单符号的平均 `1.3819` 降至 `0.8255`，三个 draw 均改善。其单符号对照与上一段 MESSAGE 的条件选择不同，不能跨实验直接拼接数字。

局部共享 Gram 后，N=1024/P=8 的 512 块整遍实际运行三次，每遍包含 8192 个局部字母 likelihood、1026 次变换及 NPZ 落盘，耗时 `0.554–0.558 s`。这是实测有限算术可行性；整遍复杂度仍含 `O(N²P²+N² log N)`，不是全帧线性算法。块外的零不属于 QPSK 支撑，因此这些输出只是在明确连续确定性 cavity 下的近似消息。这个正结果允许继续探索，不能以残差尚存直接判方向失败。详见 [PAIR_MESSAGE](../../experiments/afdm_structured_inference_20261003/PAIR_MESSAGE.md)。

第二次、也是本轮最后一次消息修订保留了块外均匀 QPSK 的协方差。在零均值 iid Gaussian 增益下，观测的真实条件二阶矩可写为 `S=(noise+pd)I−DD^H+AA^H`，通过两次正定低秩更新计算；把原混合分布替换为 `CN(0,S)` 仍是明确近似。外部 QPSK 枚举二阶矩误差为 `1.06e-15`，独立 dense likelihood 误差为 `2.84e-14`，N=2 极限恢复精确边缘。

在三个新的 N=4 draw 中，R1、Gaussian pair 和合法 Gaussian singleton 的平均 LLR RMSE 分别为 `0.72852/0.29970/0.43290`，pair 均改善；对应概率 MSE 为 `0.013153/0.002301/0.005493`。N=1024/P=8 的三遍完整成本为 `0.631–0.641 s`。据此准入一个均匀先验下的一遍检测原型，复用真实观测初始化和几何估计，再译码一次；非零入站先验显式拒绝，不借用旧 Onsager 项。详见 [GAUSSIAN_PAIR](../../experiments/afdm_structured_inference_20261003/GAUSSIAN_PAIR.md) 与 [候选选择](../../experiments/afdm_structured_inference_20261003/SELECTION.md)。其独立登记的完整链结果如下。

### 实际接收链与迁移失败

原型关闭时直接调用原接收机；真实 N1024 报价观测上的 17 个数值数组逐字节相同。开启后使用原 pilot front、一次几何更新、Gaussian pair 或 singleton、原 LDPC 一次译码，不保存虚构的全帧 gain posterior，也不反馈 decoder APP。三项 mock 接口测试与这一实际回放的证据等级分别记录。

开发集为 3 个新外生簇，每簇 10/20 dB 两个配对观测，四个固定接收配置共实际执行 24 次。所有配置的输入相同；跨 SNR 的信道、信息位、码字、导频、无噪信号和标准化噪声哈希一致。全部调用成功并保留，不存在挑选成功子集。

| 配置 | 平均 bit log score | Brier | 错帧数 | 完整单帧平均墙钟 |
|---|---:|---:|---:|---:|
| 原 joint 两轮 | 0.0227808 | 0.00638261 | 0/6 | 0.11194 s |
| 原 joint 一轮 | 0.0612480 | 0.01793913 | 0/6 | 0.06923 s |
| Gaussian pair 一轮 | 0.3341683 | 0.10491722 | 6/6 | 0.70937 s |
| Gaussian singleton 一轮 | 0.3341987 | 0.10492206 | 6/6 | 0.65112 s |

分数越低越好，来自保存的 decoder-input LLR，沿用原接口的 ±20 裁剪。没有未检出的错帧。pair 对原两轮 joint 为救回 0、伤害 6；原一轮也全解对，说明“少跑了第二轮”不足以解释候选失败。pair 相对 singleton 的微小软分数变化没有形成实际原方法效用信号。

每次成本含输入加载、初始化、几何估计、推断、译码、操作计数、有限值检查及原始结果落盘；固定轮数不同、成本不同，不能称同预算比较。开发进程的完整成本为 `21.395 CPU / 21.909 wall s`，包含启动和辅助子进程；只报 worker 的 `11.447 CPU s` 会漏掉成本。样本 p95 已保存，但每配置只有六个时间点，不能当总体尾延迟估计。真实数据/源码哈希和 24 份 raw 复算均通过。

据预登记门，候选既未改善到要求的软分数，也没有净救回，迁移不通过。MECH 的同预算因果比较和 FRESH 的独立确认属于前置未通过，**没有执行，也不是效果为零**。未打开确认流 90，旧揭盲数据未冒充确认集。

详见 [接收器与报价](../../experiments/afdm_structured_inference_20261003/LOCAL_RECEIVER.md)、[完整迁移报告](../../experiments/afdm_structured_inference_20261003/TRANSFER.md)。

为补齐中间尺寸并检查失配边界，又在 N=4/16/64、P=2、每尺寸 3 个新 draw 下运行了原候选、singleton 和 scalar20。该数学诊断使用正确 iid Gaussian 先验、共同声明的已知几何、未编码独立 QPSK；scalar 初始增益来自观测导频 ridge 解，而非真值。它与生产的归一化增益、估计几何和 LDPC 不同，不能混合统计。

N=64 时，pair/singleton 的 log score 为 `0.15809/0.14438`，Brier 为 `0.047897/0.042326`，误码为 `24/384` 对 `18/384`；三个样本均出现 pair 相对 singleton 失优。scalar20 的 log score 为 `0.40606`、Brier 为 `0.046741`、误码为 `19/384`：pair 的 log score 更好，但误码略多，不能称任何一方全面获胜。pair 的平均局部调用成本约 `24.73 ms`，scalar 约 `5.57 ms`。不同尺寸使用不同 draw，不据此声称单调的尺寸因果效应。

这表明小 N 的局部积分优势不足以自动保证扩展，且失优并不要求先存在错误先验或错误几何。不过，生产失败中码、生成先验、估计几何和近似族各自的因果贡献仍未被单独识别；没有通过再调一次候选掩盖这个未决问题。详见 [TRANSFER_SCALE](../../experiments/afdm_structured_inference_20261003/TRANSFER_SCALE.md)。

## 3. 碰撞 jet 的适用域与未解决的观测问题

JET 在 N=16、126 格配置中覆盖重合至间隔 1.2、同相/相消/一般复增益、绝对中心和 CPP 留出。固定正确中心、间隔 0.01 时，native 单中心、jet 一阶、jet 二阶的 scaled operator error 分别约为 `0.01728`、`0.0002035`、`1.741e-6`。间隔 1.2 时则为 `1.3479`、`1.815`、`2.3919`：高阶并非在任意区域都更好。

错中心留出中，即使两条路径完全重合，一阶 jet 仍可有约 `0.098/0.066` 的误差。生产方法必须从观测获得分群和中心，不能把真值中心隐藏进算法输入。组合矩还须使用 `Cov(M)=T Cov(h) T^H`；自由 jet 系数配独立 isotropic prior 会改变问题。

这里的 F1 是真几何双列的表示参考，未运行 F1 optimizer，不能据此评价实际几何搜索效率。可保留的结论是低阶表示的局部近似规律和反例；观测驱动分群、中心、未知 offset 的先验及组合矩支撑仍未闭合。

详细证据：[JET](../../experiments/afdm_structured_inference_20261003/JET.md)。

## 4. 概率势、实际训练与更简单的合法对照

POTENTIAL 在 8 个有限双线性模型及 C2 极限上验证同一势生成均值、covariance 和物理响应：梯度/Hessian/cross/JVP 误差均约 `1e-11`，`dE[z]/dy_R=2Cov(z,f)/sigma2` 误差 `2.20e-11`。路径置换和合法联合相位推送通过；观测相关基测度的额外导数不能省略。

LEARN 实际训练了 6 个网络，各固定 200 步 Adam，没有以测试结果挑 epoch。教师是 N=2/P=2 的合法 256 状态有限模型，**不是 Gaussian 增益教师或生产生成分布**。12/4/8 个独立几何簇分别用于 train/validation/test，每簇 8 个观测；路径置换和相位变换只是同测试观测的配对诊断，不增加独立样本量。

共享势为 1,121 参数，独立头为 1,116 参数，使用相同 33 维物理输入。主留出上共享势的 mean MSE 为 `0.02658`，独立头为 `0.03090`；配对差为 `−0.00432`，8 簇描述性 bootstrap 区间为 `[−0.00511,−0.00345]`。JVP MSE 为 `0.001762` 对 `0.001956`。这只支持所测架构上的局部误差改善，激活函数和导数参数化同时不同，不能把它解释成单一约束的完整因果效应。

所有 6 个网络在主留出中均出现有限支撑越界。每个模型只要有一个非法概率，就拒绝其整个 cohort 的 proper score；没有 clip，也未只报存活样本。共享势虽然 PSD 和响应一致，却违反必要的 finite-support covariance diagonal identity，最大误差 `0.239–0.324`。其有序特征还未保证路径等变；变换测试反映该结构缺失，不否定全部势方法。

同样训练步数下，只学一个正标量的 mean-field 修正得到 `alpha=0.4295`，mean/JVP MSE 为 `0.01393/0.000656`，都优于两个网络族；合法概率的 Brier/log score 为 `0.24941/0.69214`，优于 alpha=1 的 `0.27433/0.74815`，但仍不及 exact 教师的 `0.22787/0.64619`。该 JVP 是近似更新映射的导数，不保证等于其 product 分布下原物理映射的 `Cov(z,f)`，不能直接充当 Onsager 项。

硬动作采用 sign(mean) 对应的合法 product 状态，不是 joint MAP。因此 exact marginal-mean 动作也有非零 joint-mode regret；报告没有给教师虚构零模式误差。

完整训练、数据生成及分析登记用时约 `0.552 CPU / 0.637 wall s`，单线程；checkpoint、梯度训练曲线和全部预测均保留。追加成本核验使用已有权重和数据，不重训。批量 kernel 时间、单观测物理预处理及全接收机时间必须分别解释。

追加核验的 3,456 次单例调用与冻结预测最大差为 `3.68e-16`。含给定几何的 CPP 算子构建、特征和必要导数时，共享势冷启动约 `197–199 μs`、同几何 8 观测摊销约 `95–98 μs`；独立头约 `133–137/32–33 μs`；单标量修正约 `267/41 μs`；exact 有限教师约 `260/130 μs`。因此单标量修正在复用几何时更便宜，冷启动并不比共享势更便宜。这些都未包含几何发现或生产 LDPC，也不是 N=1024 延迟结论。

详细证据：[POTENTIAL](../../experiments/afdm_structured_inference_20261003/POTENTIAL.md)、[LEARN](../../experiments/afdm_structured_inference_20261003/LEARN.md)。

## 文献边界与论文可用性

逐式对比见 [LITERATURE](../../experiments/afdm_structured_inference_20261003/LITERATURE.md)。P-BiG-AMP、Gaussian 消元/logdet、群平均、confluent Prony/jet、ICNN 和学习步长都是已有工具。AFDM GR/GE-SBL 与 D-GESBL 已覆盖部分直接相关的积分或几何演化内容，不能将这些工具本身宣称原创。

RIGM 与 phase-aware code EM 的正文访问分别遇到 406/超时与 404；目前只有真实摘要/元数据证据。其余直接重叠文献保存了正文及访问收据，但本轮检索仍不是首创证明。

可采用的论文措辞是：在声明模型与范围内发现可复现的表示敏感性、条件/边缘混淆反例、jet 失效域，以及凸势一致性不足以保证有限支撑后验的实际训练反例。主算法的新颖性、同预算 FER 改善或生产降本，必须有相应完整证据后才能写入。

## 反馈闭环与尚未证明的内容

| 初始问题 | 实际修订或判别 | 本轮结论 | 精确剩余问题 |
|---|---|---|---|
| 分槽改变软信息是否只是先验变了 | 区分非守恒与守恒拆分，再复用已有 block map | 守恒拆分仍影响 scalar；已有 block 恢复不变性 | 更便宜的不变算术、一般奇异支撑；不把已有工具算新发明 |
| C2 秩一相关是否能直接改善 bit 消息 | 固定轨道、未知轨道混合、exact marginal product 反例 | 单轨道公式成立；交叉矩损失不充分推出 LLR 损失 | 可扩展未知轨道 posterior/cavity |
| 精确增益积分为何仍有消息误差 | 单符号→pair→保留块外协方差→真实 coded receiver | 小模型有正结果，生产开发门失败 | 全帧离散信息与 gain/data 耦合的可扩展处理；生产损失的单独因果归因 |
| jet 是否改善碰撞几何 | 固定阶数、相消/同相、间隔与中心留出 | 正确中心的局部展开有效，越域或错中心可失败 | 观测驱动分群/中心、未知 offset 支撑，不是再扫阶数 |
| 共享势是否值得学习 | 真训练、独立头/解析/标量对照、支撑与变换检查、完整局部成本 | 部分 MSE 改善不等于合法后验；标量对照更准确 | 支撑保持、路径等变和原物理响应同时闭合的模型 |

同预算 MECH 和新鲜 FRESH 的条件关闭依据见 [CONDITIONAL_CLOSE](../../experiments/afdm_structured_inference_20261003/CONDITIONAL_CLOSE.md)。研究任务的执行闭环、某个数学恒等式成立、候选算法成功和领域潜力被穷尽是四件不同的事。本轮完成探索与候选判别，没有得到可晋级的主算法优势，没有更改已接受论文主张，也没有把未运行的预算曲线写成负结果。

## 复核入口

在项目根运行现有环境下的合同测试：

```sh
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python -B -m unittest discover -s experiments/afdm_structured_inference_20261003 -p 'test_*.py'
```

逐阶段注册、配置、源码/输入哈希、原始数组、学习权重、调用账和失败策略保留在 [原始证据目录](../../.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/)。其中 `pipeline_development_v1/readonly_audit_v1.json` 与 `transfer_scale_v1/recount.json` 是保存结果的零新增接收调用复算。每个 stage 的注册记录实际 Python/线程/输入与证据边界；历史 stage 拒绝覆盖。重现实验需要新的隔离输出及登记，不能删除旧结果来重跑。

源码、报告和任务内规范提交 Git；`.mission` 原始研究工件按执行协议保留在本地，不把“只有 Git 源码”称作含全部数据的独立复现包。本报告旁的 `evidence_manifest.json` 绑定本轮注册及 raw 字节，最终独立审查与人类交接存放在同名 Mission CSV 旁。
