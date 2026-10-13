# 连续不确定性适配：首轮接收机鉴别协议

2026-10-07；PROTOCOL-01。只决定是否继续投入，不是最终 coded/Trans 证据。
固定以下选择后再实现；源码、接口核验、预算与独立准入齐全后才运行。

## 候选与共同模型

真实生成：N1024，SP pilot/data=0.5/0.5，真实 root7 ZC、DAFT/CPP、连续多径
G1；严格复用 G0 归一化增益，不重归一化。SNR 沿用 make_frame 的标称
总符号能量1口径：sigma2=10**(-SNR_dB/10)，proper CN(0,I)噪声乘sqrt(sigma2)；
不按G1实测能量重缩放。data-only SNR比标签低约3.0103 dB。第一轮采用真正 uncoded QPSK，
decoder calls=0；coded 接入和强完整接收机确认仍为后续必需任务。

每个入口只接受 y/pilot/sigma2 和公共物理配置；truth 只在全部输出封口后评分。
每个 arm 从同一观察量重新运行 F1.acquire，最多8个保序槽。获取范围与原先验
分开说明。不得免费使用别的 arm 的最终状态或真值支持。

三个 arm 共用 all-I then all-Q bit 顺序，以 bit-marginal LLR<0 判为1，
LLR=0固定判为0；不用symbol-MAP替代bit-MAP。

三个 arm：

- `f1_scalar`：F1 获取→keep-slots soft CE 两次坐标遍历→原 scalar_joint20，
  prior=0、damping=.3、gain_mode=joint；一次 outer、无 decoder。
- `vb_point`：同 F1 获取→联合 Gaussian gain、QPSK KL-MM 数据步；Doppler
  用连续点坐标优化。其余设置与 `vb_continuous` 相同。
- `vb_continuous`：使用连续 Doppler 密度期望，保留完整 gain covariance、
  非均匀数据交叉矩和真实 CPP 自项。属于已声明工作模型的近似推断。

工作先验固定：gain CN(0,I/P)，各 ν 独立 uniform[-3,3]，独立均匀 QPSK。
不将它们当实际生成先验。gain 初始化 m=F1 gains、C=I/P；data q 均匀。
continuous ν 初始化为以 F1 点为均值、标准差0.125的截断 Gaussian 因子，
后续每次坐标更新都引用同一个 uniform 工作先验，不把该初始化再乘入似然。

固定20个外层 sweep，每 sweep：gain 更新→顺序 ν 坐标 sweep→gain 更新→
3次同步数据步。使用完整 S=C+mmᴴ。ν sweep 允许缓存 R_ij 并按 Δφ 增量更新
其余系数；记录真实执行成本，不将未经实现的复杂度写成已达到。

数据步使用 DATA_UPDATE_BOUND 的几何 KL-MM 更新。逐次从 β=0 试探，随后
β=2^j−1；曲率证书满足才接受，最多到 ceil(log2(1+β_safe))。记录每个拒绝
proposal 与 Gram 调用。最终安全步仍未通过浮点一致性检查则失败；无静默回退。
记录目标增量与式(8)残差，容差为1e-9×max(1,|旧目标|,|新目标|)。正概率用
log q 保存；不把下溢引起的0当作硬支持，不加隐蔽概率 floor。

## 连续积分与点值消融

连续密度保存系数/支持/归一化量，有限节点仅用于积分。[-3,3]分16个等宽
panel，每panel Gauss–Legendre 8/16/32/64点，即128→256→512→1024节点。
比较相邻层 max_n|Δφ_n| 与 |Δlog Z|，两者均≤1e-6后使用较细层；到1024仍
未通过则显式失败。它是分辨率诊断，不能充作严格连续积分误差证书。
计入全部分辨率、相位表构建与缓存成本。log-sum-exp归一化；若为适配严格正权
API删掉总离散质量≤1e-14的尾部，记录该质量及≤2e-14的矩扰动界；禁止隐藏floor。
不同路径保留节点数可用重复同一节点、拆分其质量补齐，不能改变离散积分矩。

点 ν 坐标在固定257个等距节点含端点上评分，选择最多3个最强局部峰，再在相邻
网格区间 bounded minimize_scalar（xatol=1e-6、maxiter=32）细化，保留旧点与
端点作为候选；按冻结其它q因子的expected-log-likelihood坐标势（式10–11的Re Fourier势）最大值选择。失败或非有限结果明确记录。
这是有限全局扫描加局部连续优化，不保证全局最大；Dirac消融不是连续prior下
有限KL的精确VB，不能拿其“ELBO”与连续因子的ELBO直接比较。

## 冻结样本、预算与判据

新development seed namespace `[20261007,703]`，4个独立exogenous blocks，
各在6/8 dB共用同一channel/message/noise realization后缩放噪声。共8个SNR
观测、24次完整接收调用、0 decoder。component RNG 明确区分 channel/message/noise，
禁止接入旧确认seed。使用新不可变输出，不修改旧确认集。

独立阶段：实现核验最多180秒，0新通信观测，复用已保存MATH输入进行算子/
数据步回归并加已声明积分边界fixture；这只是工程证据。真实development最多
1800秒、1 CPU、CUDA隐藏、RSS≤4 GiB、输出≤128 MiB。所有远端写入仍在
/data/guoyikun/；完整源/资产哈希、CPU wall、峰值、失败与保存成本全部保留。
精确stage合同和source inventory在实现后冻结，不直接由本文触发运行。

完整计费包括每个arm自己的F1获取/预计算、全部因子更新、求积/refinement、
成功及失败proposal、变换/求解、概率输出与保存。runtime setup另列并给含setup
总账。禁止用共享缓存免费化候选成本；运行顺序按block轮换，顺序单CPU执行。

开发继续门槛：8个观测各有3个arm全部输出，即24/24完整；失败arm不得删除或
填成零错误。每个arm用其8次完整接收调用分别计算中位耗时；continuous累计raw bit errors至少比point少10%，
且不高于f1_scalar；相对f1_scalar完整接收中位耗时≤1.25倍。若point零错误，
本小样本无法证明不确定性改善，记“无可判别空间”，不能算优势通过。
这些门槛仅筛选后续coded实验，不是统计显著性、量产收益或完整目标通过。
始终报告逐block配对误差、两SNR分层结果及总成本，不用总和掩盖恶化的SNR。

未满足时保留失败；分析是积分/步长开销、工作先验失配、获取错误还是推断机制
无增益，再冻结下一次最小鉴别。不得事后改门槛、样本或只挑成功frame。

## 实现核验的固定清单（运行前补齐）

工程stage读取原MATH N8/N16/N1024的inputs/arrays，逐文件SHA绑定；每组比较
quadratic、Gram对角/作用、mean adjoint、gain Gram/匹配向量和坐标系数，共7项，
再各执行3次DataStepper步，共9步。另执行test_core全部13个组件/边界测试，
逐测试记录started/complete/fail。这些固定fixture没有BER评分。

其中1个测试向receive传入非法truth字段，必须在任何算子执行前拒绝；明确计
receiver_calls=1、receiver_boundary_rejection_calls=1、receiver_payload_executions=0、
backend_fixture_calls=0。其余只调用组件。new_observations=0、decoder_calls=0；
这一次非法API边界调用不算有效接收、生成样本或性能证据，不能因此跳过关键测试。
工程deadline180秒、1CPU、CUDA隐藏、RSS≤4GiB、输出≤128MiB，独立stage/source
绑定，所有求积/目标重算/拒绝proposal均记录。
