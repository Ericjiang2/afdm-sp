# 高阶观测特征、独立校准与有界 GMM 估计

本文件覆盖 FEATURE-01 / EST-01。它实现已批准的开发试验：判断 Gaussian 控制模型中的高阶信息能否被低成本观测统计利用，并保留未知功率/噪声、先验失配及实际 G0 不可辨识平台下的失败。源码、网格和判定口径先于正式研究冻结；结论只根据对应注册 attempt 更新。

## 对象与推导

固定 N=16、无 pilot、独立单位功率 QPSK、共同 delay=0、`c1=.37/N,c2=.13/N²`。这些 chirp 对控制矩合法；实际 G0 的 k=0 单原子平台与 chirp 无关，但其支持仍由真实冻结生成器检查。特征从观测 DAFT 向量 y 经一次逆 DAFT 得到 r，随后计算

`F=[N^-1 sum_n |r_n|², N^-1 sum_n |r_n|⁴, T_48, T_4,12]`。

lag 是预定的 1/4、1/2、3/4 帧位置，不以真值、估计表现或当前观测重新选择。前两个分量用于功率/噪声 nuisance 的联合估计；后两项提供平方半间距 q 的局部灵敏度。

Gaussian 控制模型中，令 `S=tau+sigma2,k=1-1/N`，则精确均值为

`m_1=S`，`m_2=2 S²+2 k tau²`，

`m_T(a,b)=k tau²[cos²(sqrt(q) 2pi a/N)-cos²(sqrt(q) 2pi b/N)]`。

第一、第二分量均与 q 和中心 mu 无关。第四矩通过条件 proper Gaussian 的 `E|r_n|⁴=2 K_nn²` 及独立输入 `E|v_n|⁴=2-1/N` 得出。在 q=0，Jacobian 的 q 列为 `[0,0,kappa_48,kappa_4,12]`；mu 列全零；tau、sigma2 两列的前两行为 `[1,1]` 与 `[4S+4k tau,4S]`，后两行为零。

训练分割估计完整 `Sigma=Cov(F)`，保留所有非对角项。令 Jn 为 `(mu,tau,sigma2)` 导数列，计算

`beta=(Jn^T Sigma^+ Jn)^+ Jn^T Sigma^+ Jq`，

`w=Sigma^+(Jq-Jn beta)`。

保存 `w^T Jn`、协方差全谱和丢弃方向。秩阈值预定 `1e-12`，不加 jitter。对于本模型的碰撞 Jacobian，两个非零 nuisance 列张成前两个特征方向，因此 w 的前两个坐标理论上为零；浮点残差保留。计算的 `(w^T Jq)²/(w^T Sigma w)` 是**固定 Gaussian 工作模型、有限训练协方差的估计量**，不是精确总体 Fisher，也不是使用真实评估 nuisance 的 oracle 投影。零 q 方向或完全零协方差明确拒绝或标为无信息。

## 分割、测度和独立性

注册配置为 `results/afdm_higher_order_information/ESTIMATION_CONFIG.json`。

- 训练：4096 个独立 Gaussian 碰撞帧，固定工作 `tau=1,sigma2=.5`，只估计协方差和投影权重。
- 校准：三组事先指定统计参数 `(tau,sigma2)=(.8,.2),(1.3,.5),(1.3,1.2)`；每组 128 个独立的 16 帧组，共 6144 帧。对 R=1、16 分别计算 `w^T mean(F)`，阈值取各统计参数点经验 95% 上分位数的最大值。R=1 使用每组首帧。
- 评估：Gaussian、二路径固定总增益能量 sphere2、实际 G0 单原子平台三个 prior；每类两个预定统计参数点、三个半间距、64 个 16 帧组，共 18432 个观测向量。Gaussian/sphere 的 delta 为 `[0,.05,.2]`；G0 平台 delta 为 `[0,.025,.07]`。

三种 prior 在相同 nuisance 索引和 gap 索引下复用输入、Gaussian 基变量和标准噪声，用 SHA-256 核对；G0 使用不同的合法 gap 网格，不能称为同物理间距的 prior 配对比较。不同 prior 的 18432 个评估向量来自 **384 个独立的 16 帧外生组**，不能把 prior 臂或 R=1/R=16 复用前缀算作更多独立组。训练、校准、评估 seed 域互不重叠。

阈值仅是三个离散注册点的有限开发校准，既没有宣称覆盖整个连续 nuisance 域，也没有在评估集重调。所有统计参数点、gap、prior 与失败都保留。

## 三种先验

Gaussian 增益为 `h~CN(0,tau I/2)`。sphere2 为 `h=sqrt(tau) z/||z||`，z 是二维 proper Gaussian；它与 Gaussian 有相同二阶增益矩，但不同径向四阶矩。sphere2 是明确的失配对照，不能称为实际生产归一化。

G0 对照使用 PRIOR 已证明的精确 pushforward：N=16、mu=0、同 delay=0、k_leak=2、prune=.01 时，`delta<.09047461579...` 只保留整数 k=0 原子；归一化后的算子为该原子乘均匀随机全局相位。运行前对 0、.025、.07 各自调用 `prior.geometry`，要求两个物理路径的非零 weight 行恰为 k=0，再用这个等分布缩减生成观测。外乘 `sqrt(tau)` 是声明的可见信号尺度，不是潜在 PDP 或实际归一化前的路径总能量。

该 G0 观测分布对 delta **严格不变**。用 Gaussian 特征均值拟合仍会输出数值，但输出不是识别出了真实 G0 间距；它用于展示工作先验失配与不可辨识。这里不模拟潜在发散路径增益或 G1 无限矩支路。

## 估计器、基线与真值边界

候选均值表由同一个控制矩函数生成。未知 nuisance 臂在 `q in [0,.16]` 的 33 点、`tau in [.3,2]` 的 21 点和 `sigma2 in [.1,1.5]` 的 17 点笛卡尔积上全搜索，共 11781 个候选。使用完整训练协方差的 GMM 目标

`(mean(F)-m(theta))^T Sigma^+ (mean(F)-m(theta))`。

已知 nuisance 臂使用实验预先声明的统计 tau、sigma2，只搜索同一 33 点 q 网格。它被明确标为 known statistical nuisance，不代表未知 nuisance 的部署结果，且从不传入逐帧实现的 gains、data 或 latent PDP。

两个高阶方法分别用 q 和原始 delta 坐标调用同一物理候选集合。delta 臂取 `sqrt(q_grid)` 后再计算预测；两者使用相同候选顺序、同一目标和固定第一最小值规则。因此它们应给出相同拟合，脚本逐组检查参数完全一致及目标值误差 `<=1e-10`。此对照不把网格或初始化差异包装成坐标创新，也不宣称平方坐标本身增添了统计信息。

二阶匹配 Gaussian 基线的协方差恒为 `(tau+sigma2)I`，明确返回 q 不可辨识，不用猜 q=0 来制造或掩盖 RMSE。功率特征对 mu 没有信息，所有方法均标中心不可辨识。本研究不声称全局无别名的路径重建。

`CandidateBank.estimate` 的输入只有观测特征均值；真实 delta、tau、sigma2 只在模拟器及单独的 `external_metrics` 中出现。所有拟合均在查看评分前完成，不按成功子集选择方法。误差、q=0/上界率、未知 tau/noise 边界率与工作模型失配逐个 case 保存。

## 费用和验证

观测特征费用包含完整逆 DAFT、幅度平方、四阶统计和 lag 组合；训练协方差、谱分解、nuisance 投影、阈值校准、全部候选均值构造和全部组的目标计算均记录。q/delta 两臂分别执行并计费；构造可跨组复用的候选表单列 setup 费用。生成数据、保存 raw、审计 dense 对照与整条研究运行费用由记录器和 `costs.json` 保留，不把核计时当作生产接收延迟。

独立 dense DFT/CPP 计算每个生成 case 的前 64 帧特征，校验阈值 `2e-11`。小规模测试另核验 N=4 全有限输入 Gaussian Wick 均值、Jacobian 差分、nuisance 正交、秩亏处理、相同物理候选结果、R 前缀与 prior 外生流身份。正式研究需使用已提交源码及新 attempt 名称：

`python -m experiments.afdm_higher_order_information.estimation --stage estimation_v1`

正式结果尚需实际终态读取；不能以测试通过或源代码的预期性质宣布估计效果。无 production receiver、decoder 或确认流调用。
