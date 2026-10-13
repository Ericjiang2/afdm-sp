# Derivation Package：得分压缩、nuisance 与可用线性信息

## Target

从精确观测族的得分推导观测特征 Phi 的有效信息，并界定可实际训练的低成本得分逼近。这里的理论对象不是旧 T 族的一个数值比值，而是压缩实验本身。有限样本 MSE、线性矩下界和完整压缩 Fisher 分别处理。

## Status

**COHERENT AS STATED**。压缩得分恒等式、精确损失分解、有限四状态反例和圆对称模型中的充分外积均为解析结论。实际分支能否使用它们，仍取决于合法坐标、DQM 和有限得分矩。

## Invariant Object

令兴趣参数为 theta，nuisance 向量为 eta。在基点 P0，实得分 `s=(s_theta,s_eta)` 均值为零、平方可积。固定观测映射 Phi 不依赖未知真实参数；训练得到的映射须在独立训练完成后条件冻结。定义 Hilbert 空间 `L2_0(P0)`、条件期望投影 `C=E[.|Phi]`、nuisance 空间 `H=span(s_eta)` 及其投影 P_H。

## Assumptions

- 原观测族在基点二次均方可微，或有足以交换边缘积分和单侧参数导数的明确支配条件。
- 若 theta=q=delta² 位于 0 边界，只沿合法单侧 tangent 讨论；不因正噪声就自动宣称实际归一化模型 q 正则。
- 当前参数族、PDP 条件/边缘测度、输入分布与教师得分一致。改变其中之一须另标实验。
- nuisance 可以降秩；均使用 L2 张成空间或相应 Moore–Penrose 投影。
- 所有特征 Fisher 结论指总体分布。用有限样本替换协方差/Jacobian 得到的是估计，不是已认证下界。

## Notation

完整有效得分 `e=s_theta-P_H s_theta`，完整有效信息 `I_eff=||e||²`。压缩 nuisance 空间为 `H_Phi=span(C s_eta)`，压缩后的有效得分记 e_Phi。F 是 Phi 的有限个中心化实函数组成的向量。

## Derivation Strategy / Map

合法密度导数 -> 条件期望得分 -> 压缩实验内 nuisance 投影 -> 两项信息损失 -> 有限特征线性空间 -> 训练/评估边界。再用四状态指数族说明错误顺序的后果，并检查 AFDM 特征映射实际保留的 sigma 代数。

## Main Derivation

### 1. 压缩得分〔恒等式〕

对任意有界可测 a(Phi)，由导数交换和得分定义，

`partial_j E_theta[a(Phi)]|0=E0[a(Phi) s_j]=E0[a(Phi) E0(s_j|Phi)]`。

因此压缩实验的得分是 `s_j^Phi=C s_j`。这是在观测压缩后定义的得分，不是把一个优化后的参数向量压缩。DQM 情形也可从 likelihood-ratio 的 L2 推导获得同一结果。

### 2. 必须在压缩实验内重做 nuisance 投影〔恒等式〕

`e_Phi=(I-P_HPhi) C s_theta`，

`I_eff^Phi=inf_beta ||C(s_theta-beta^T s_eta)||²`。

因为 `C P_H s_theta` 属于 H_Phi，

`e_Phi=(I-P_HPhi) C e`。

由正交分解得到精确损失恒等式

**`I_eff-I_eff^Phi = ||e-Ce||² + ||P_HPhi Ce||²`。**

第一项是压缩丢失的有效得分变异；第二项是压缩后重新暴露的 nuisance 混淆。因此 `I_eff^Phi<=||Ce||²<=I_eff`，而 `||Ce||²` 一般不是压缩有效信息。只有 `Ce` 与压缩 nuisance 空间正交时，才可省去第二次投影。

重要特殊正结论：若精确 e 是 Phi-可测，则 `Ce=e`；对任何 nuisance 分量，`E[e C s_eta]=E[e s_eta]=0`，故 `e_Phi=e`、`I_eff^Phi=I_eff`。因此把**精确有效得分本身**作为压缩统计可保留局部有效信息；一般不交换的反例不否定这一经典结论。

### 3. 四状态最小反例〔精确有限模型〕

X、Z 独立均匀 ±1，定义正规指数族

`p_(theta,eta)(x,z)=exp[theta x+eta(x+z)] / sum_(x',z') exp[theta x'+eta(x'+z')]`。

在 0 点，`s_theta=X,s_eta=X+Z`，Fisher 为 `[[1,1],[1,2]]`，完整有效得分 `.5(X-Z)`、信息 `.5`。压缩 Phi=X 后，两列得分均为 X，故正确压缩有效信息为 0。然而 `E[e|X]=.5X` 的平方范数是 `.25`。压缩前后 nuisance 投影不交换。上述损失两项各为 `.25`。有限状态/正概率保证全部正则条件，无需数值近似；也可将 theta 限于非负半轴而保留单侧反例。

### 4. 线性矩信息与完整特征 Fisher〔命题〕

给定特征 F，`Sigma=E FF^T`、`J=E F s^T`。对得分逐列投影到线性空间 span(F)，得到矩信息矩阵

`I_lin=J^T Sigma^+ J`。

其 nuisance 有效项是该矩阵的广义 Schur 补，等于

`inf_beta (J_theta-J_eta beta)^T Sigma^+ (J_theta-J_eta beta)`。

因为 span(F) 包含于所有 Phi-可测平方可积函数，`I_eff,lin<=I_eff^Phi`。嵌套线性空间在总体上使该最小化信息不减。但同一 Phi 的不同多项式基可能拥有不同线性下界，而完整 Phi Fisher 完全相同。例：对称 X 四点分布中平方得分 `X²-E X²` 与 X 线性正交，Phi=X 已保留整个观测，使用 F=X 的线性矩信息却为零；加入 X² 可恢复它。

### 5. 回归 MSE 的精确意义〔恒等式及限制〕

对任何冻结的 Phi-可测回归函数 g，

`E||s-g(Phi)||²=E||s-C s||²+E||C s-g(Phi)||²`。

因此独立评估的全得分 MSE 测量条件期望逼近误差与不可压缩误差之和；它不直接等于有效信息损失。尤其只回归 e 而不处理压缩 nuisance，可能重演四状态反例。

实现同时回归全部四列得分，使用独立 validation 选择预登记 ridge，test 只评分。test 的协方差和 score-矩交叉项可用于**诊断性**重投影，不能把这一诊断当部署训练，也不能把训练样本中的正交关系当作总体正交。有限样本矩信息是 plug-in 估计；报告秩、批次/重采样不确定性及残差，不宣称认证 Fisher 保留率。

近似有效得分的一个条件界也可从精确损失式获得。若 Phi-可测 g 满足 `E(e-g)²<=epsilon`，则 `E(e-Ce)²<=epsilon`。写压缩 nuisance Gram 为 G，`B=E[(s_eta-C s_eta)(s_eta-C s_eta)^T]`。由 `E[e s_eta]=0` 得 `b=E[Ce C s_eta]=-E[(e-Ce)(s_eta-C s_eta)]`，故 `||b||²<=epsilon tr(B)`。若 G 的最小正特征值为 lambda，则

`I_eff-I_eff^Phi <= epsilon[1+tr(B)/lambda]`。

G 的零空间与 b 正交；若 G=0，第二损失项为零而仅有 epsilon。这个界说明需同时关注回归误差和压缩 nuisance 的退化，不能用 MSE 的一个经验比例直接声称 Fisher 保留率。实现没有已知总体 epsilon 或 lambda 的认证值，故不会把该条件界当作数值保证。

### 6. AFDM 功率与相位特征实际保留什么〔命题〕

注册嵌套基为：总能量 -> 旧 T/平均四阶功率 -> 全部逐点功率和功率交叉 -> 相位相干及强度加权四阶相干。所有特征由观测构造。

完整功率交叉是功率向量 p 的确定性函数。它可扩大线性回归空间，却不增加相对于完整 p 的 sigma 代数或精确 Fisher。更强地，最后一层含全部 `Q=yy^H` 的实/虚坐标。若所有参数下 `p_theta(e^(i phi)y)=p_theta(y)`，则 Q 是充分统计：对非零 y，选 Q_jj>0，向量 `Q_:j/sqrt(Q_jj)` 恢复 y 至一个全局相位；具有相同 Q 的观测恰在同一相位轨道。likelihood ratio 在该轨道上恒定，故由 Q 可测。于是全得分都是 Q-可测，`I_eff^Q=I_eff`。

零均值圆对称 Gaussian 增益、球面对称增益及保持全局相位对称的实际归一化推前均满足该全局相位不变性，只要其得分存在；已知 pilot 不破坏增益的全局圆对称，但改变输入先验或使用非圆对称已知增益需要重查。**充分不等于廉价**：Q 有二次规模，有限多项式/岭回归可能仍无法逼近 log-sum-exp 混合得分，不能把理论充分性报告成已实现的保留率或性能收益。

Q 不是最紧凑的表示。令 j 为 `argmax |y_j|`，并固定取最早索引处理 tie；若 y 非零，定义 `z=y conj(y_j)/|y_j|`，零向量单独映射为零。z 与 Q 彼此可确定同一相位轨道，故在上述圆对称族下同样充分，构造仅 O(N)。保存全部实/虚坐标有 2N 个数，但每个 anchor 分层只有 2N-1 个自由度。注册加入该 gauge 作为**非嵌套输入对照**，独立训练回归，不因充分就预设有限拟合更好。

非圆对称反例：`Y~CN(m,sigma2 I)` 且已知相干非零均值 m 携带参数时，`||e^(i phi)y-m||²` 一般随 phi 改变，Q/gauge 不再充分。ties、零向量与映射的分层不妨碍可测充分性；参数无关映射的可微性不是这一统计论证的前提。

## Boundaries and Non-Claims

不假定任何实际碰撞点都有 q 得分；不把教师条件 PDP 当可观测边缘；不假定未知 mu/tau/noise 已消除；不以回归相关系数推导检测功效或估计精度；不使用 Wilks 处理边界。检测、估计与计算费用由独立后续研究逐项验证。

## Open Risks

有限特征高相关导致秩亏，训练矩可过拟合。相位层虽在合适模型下充分，线性回归空间仍有限。实际先验积分误差会污染教师标签与信息估计，须保留原始收敛标记和条件/边缘模型身份。
