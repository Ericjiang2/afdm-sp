# POS-01 / WIRE-03 / RUN-05 下一位置诊断契约（2026-09-06）

只读核对父v2 B1-c、CSV三行与现`budgeted_support_diagnostics.py`/runner/生成器；未运行receiver、未改实现或CSV。结论：现代码只有true/rounded两种固定位置参考，**没有观测驱动位置优化**，不可关闭RUN-05。

## 现实现确切范围

`physical_cluster_weights(system,params,rounded=False)`为每条物理路径构造一个W列：读取l_i、k_real；rounded=True先取np.round，False直接用真实小数位置。按±k_leak产生Dirichlet alpha，先能量归一化，然后按物理clip及相对功率阈值裁剪。

`fit_physical_cluster(system,params,Phi,y,rounded=False)`固定W后只进行一次`np.linalg.lstsq(Phi@W,y,rcond=eps*max(A.shape))`求8个复增益，再经`gen_h_daft`重建H。它没有位置变量迭代、步长、候选比较或33拟合预算。它不读真gain/data但true臂读取真实位置，rounded臂也依赖已知物理槽。

runner的`POSITION_ARMS=('position_true','position_rounded')`只注册两臂；位置H在接收前一次拟合，`diagnostic_channel_override`在各outer用固定H覆盖当前H，再经共同最终BP/LLR/LDPC。这个现有注入边界可扩第三臂，不必另建接收链。

当前测试验证true截断基底可以重建生成器H，及固定true位置pilot无噪声拟合；没有证明任何函数在优化Doppler。

## 最小代码入口

1. 将现W构造核心改为接受显式`delays, locations`（长度固定8），原physical_cluster_weights只作true/rounded输入适配。三臂共用同一核心，不复制Dirichlet公式。
2. 提取现固定位置的单次拟合核心：输入system/Phi/y/delays/locations，输出W、g、H、pilot residual、rank/singular/rcond和clip/prune元数据；原fit_physical_cluster可保持wrapper。所有候选统一complex128/SVD路径及rcond。
3. 新局部函数只接受`known_delays, initial_rounded_locations, Phi, y, system`，**签名不接params、true_locations、true gains、H_true或真data**。验证初始位置为整数、长度8、合法域；runner先在隔离truth适配层取rounded中心再传入。不要把完整params拷贝后声称“没有使用”。
4. CLI/runner新增`position_local`，三臂在同一位置注入分支共用fixed_H override和下游；位置模式仅改变输入来源。元数据明确`partial_oracle_known_delay_P8_rounded_slots`。保留direct40接收器自身容量账本与位置参考实际H基底列数，不能把内部nomination集合冒称位置H的真实支撑。

## 固定两sweep算法与精确计数

初始化：k_center=共同rounded初始槽，合法区间是每槽 `[k_center-.5,k_center+.5] ∩ [-k_clip,k_clip]`，其中k_clip用生成器同一公式 `min(k_max_cap,N//2-k_guard-1)`。当前值为center；先拟合一次并缓存完整结果。

按固定路径索引0..7执行sweep(step=.25)，然后再次0..7执行sweep(step=.125)。对每个坐标，**从进入该坐标时的同一个当前向量**产生负/正两个候选；其他坐标不变，比较两个候选与缓存当前值的共同pilot残差，固定同分时keep，合法严格改善才提交。不可先接受负步后再从更新值试正步，否则不再是约定的±step候选。

候选每次重新拟合全部8个复gain。当前值复用缓存，不重新拟合；总上限 `1 + 2 sweeps × 8 coordinates × 2 directions = 33`，否则把“当前点也重拟合”会变49。越出约束的候选可以明确记`outside_registered_bound`并不拟合，或按预冻结规则clip且去重；建议直接拒绝越界避免隐含改变步长。一次候选拟合发生数值失败也计入尝试次数/费用。

两步从整数中心出发通常最多到±.375，约束±.5只是允许域，不代表已经搜索整个区间；不得额外增加到±.5的候选或第三轮“完成收敛”。固定两轮结束记录`registered_sweeps_exhausted`，不默认写converged=true。残差数值余量若需采用，应数据前冻结并记录，不用真小数offset调整方向/停止/步长。

## 物理生成规则保持

现`afdm_env.generate_channel_matrix`先对每路径±k_leak alpha归一化，再丢弃越界/弱功率条目，不对保留下来的残余再归一化。三臂及每个候选都必须保持相同顺序、k_leak=2、P_phys=8、功率阈值、numpy rounding规则（含半整数banker's round）和整数DAFT生成器。候选越过round切换点时中心/原子列会切换，必须真实记录，不能用平滑插值掩盖。

生成器最后对真H作全局Frobenius归一化，归一化比例已经被真增益吸收；候选pilot-LS的g本身负责观测尺度。不要读真fro_scale或再次强制候选H的范数=sqrt(N)，否则候选实际目标与共同pilot-LS不一致。

8物理列固定保留，碰撞/零列不删掉槽位，SVD给最小范数解并保存rank。有效整数basis列可随位置和clip改变；这正是需要保存的裁剪切换，不是偷偷改变物理路径数量。完整连续Doppler与分数时延未建模，描述只能是截断生成器内的连续位置参数局部离散搜索。

## 产物与验收

每帧保留完整trace：身份/input/config/source hash、known delays/rounded centers、各候选locations、step/sweep/path/sign、fit序号、接受前后pilot residual、rank/singular/rcond、clip/prune/零列/有效整数列集合、accepted/keep/failure原因。true位置仅真参考臂和离线误差解释可见，优化trace不含用于决定行动的true偏移。三臂还保存final locations、H hash、g、总fits、CPU准备费用及完整接收费用，失败/秩亏仍进固定24帧分母。

先做良态无碰撞小系统：用合法8个物理槽及网格可达的小数偏移合成pilot观测，验证local位置至少一项改变、共同pilot残差下降，真实H拟合误差方向符合参考。不能只检查数值有限或true优于rounded。两步搜索量化且与增益耦合，不要求任意真实位置精确恢复；清洁toy应提前选可辨识和可达案例，不能从正式帧挑容易成功的案例。

补边界：clip端点、半整数round切换、碰撞/秩亏、全零basis、LS非有限、预算耗尽、同分keep，验证失败没有换帧及fits≤33。隔离测试改变与函数签名无关的true fractional数据而保持rounded/y/Phi相同，local结果应不变；真正不同y导致搜索变化用于证明观测消费者存在。

真实WIRE-03 GPU小批必须三臂贯穿同一最终BP/LDPC，输入、已知槽/初始化、系统及SVD配置相同；local fits实际>1且位置/残差trace可核验。RUN-05只在此门、BASE-01工作点和S2预算成立后：Ddev每流前8帧共24，三臂72次接收；local最多24×33=792拟合，rounded/true另各24次拟合（若每帧都重新拟合，总上限840）。局部初始拟合与rounded同配置结果可以按hash复用，但必须注明复用而不重复计费，不虚构新独立数据。

解读保留四类：local和跨流线索改善；只有true有效；残差下降但FER无益；混合/少错导致INCONCLUSIVE。部分oracle初始槽、截断模型范围及失败分母不能省略。不得以true/rounded两臂旧结果或toy通过冒充三臂真实验收。
