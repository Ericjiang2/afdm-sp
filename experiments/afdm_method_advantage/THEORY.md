# 碰撞信息到未知 nuisance 检验：方法、条件与优势边界

## 目标、状态与依据

本文件落实冻结的 [PLAN](../../.mission/20261005_20-24-46-afdm-method-advantage/PLAN.md)：把已有碰撞信息转化为只消费观测的检验和局部估计，并说明与完整观测参考、相同 14 维矩的经典 J 检验、简单二阶对称性检验相比，什么优势可以被本轮实验验证。

状态：方法推导及条件已成文，供本轮独立审查；本文件没有新增随机实验，没有执行旧研究重跑，不宣称有限样本优势已经成立。已有密度和有效信息结果见 [DENSITY_THEORY](../afdm_collision_resolution/DENSITY_THEORY.md)、[NUISANCE_THEORY](../afdm_collision_resolution/NUISANCE_THEORY.md) 及其 [独立准入审查](../../.mission/20261005_15-21-29-afdm-collision-resolution/reviews/admission_review.md)。旧数据仅用于明确标记的规划量级，不用于调整本轮评估阈值。

完整观测主参考是 **未知 nuisance 的 null 拟合与碰撞有效得分**。本轮不实现非零分离全备择 profile likelihood，因此不能称主参考为全备择 MLE、有限样本最优检验或准确性能上界。

## 模型、定义与依赖

固定实际 G0、N=4、P=2、共同 rounded delay=0、独立均匀 DAFT 域 QPSK、正圆 Gaussian 噪声，保留真实条件 PDP 与原始 Gram 增益归一化。记 $s=\sigma^2$，

$$
\eta=(\mu,\log\tau,\log s),\qquad q=\delta^2,\qquad
r=q\log(1/q),\quad 0\le q<e^{-1}.
$$

每个检验组由同一个未知参数下的 $R$ 个独立观测组成。不同基点不合并为一个总体。公开连续拟合域为

$$
\mu\in[.22,.42],\quad \tau\in[.3,2],\quad s\in[.08,2].
$$

这是共同算法设置，不能按生成真值缩窄。推断接口不得接收真实 nuisance、已实现 PDP、增益、符号或噪声；生成器与外部评估记录才可持有这些真值。

令 $w=w(\mu)$，$b=w_\mu-w(w^Hw_\mu)/\|w\|^2$，$u_0=w/\|w\|$、$u_1=b/\|b\|$。已有定理在固定非边界分支给出

$$
p_{r,\eta}=p_{0,\eta}+r h_\eta+o_{L^2(1/p_{0,\eta})}(r),
\qquad s_r=h_\eta/p_{0,\eta},
$$

联合 nuisance 的单侧 LAN，以及实际满足条件时 $0<J_{\rm eff}<\infty$。这些结论不提供任意有限 $\delta$ 的近似误差常数。

依赖图：实际 null 密度与可识别性 → nuisance 拟合的 root-$R$ 条件 → 正交得分/矩统计 → 局部功效与一步估计；完整固定算法另经独立 null 排序校准 → 有限登记网格的交换性性质。C2 的有限分离均值对称性与 J 检验给出基线机制。局部理论和有限网格校准各有独立前提，不能互相代替。

## 1. NullFamily 与 nuisance 的识别

### 1.1 null 拟合不受 PDP 离散分支约束

在 $\delta=0$，每个正 PDP 下的实际 G0 归一化响应都精确等于 $\sqrt N e^{i\theta}u_0$，其中 $\theta$ 均匀。因此

$$
p_{0,\eta}(y)=\frac1{64}\sum_{X\in\mathcal X/\mathrm{global\ phase}}
E_\theta\varphi_s\left(y-e^{i\theta}\sqrt{\tau N}\,u_0\odot A^HX\right).
\tag{1.1}
$$

各分量的全局相位用 Bessel $I_0$ 解析消元，故 null likelihood 无 CP1 积分，也不依赖条件 PDP 权重。PDP 的 floor 边界不能用于截断 null MLE 的公开拟合域。

实际冻结构造在 $\mu\in[.22,.42]$ 全程 rounded center=0、保留整数 atom $-1,0,1$。窗口先归一化，再截断/剪枝的共同因子不改变 $u_0$。相对侧 atom 功率至少为 $\sin^2(.22\pi/4)>.01$，所以公开 null 域没有物理支撑切换。$p_{0,\eta}$ 对 nuisance 光滑；最终构造 $s_r$ 时再单独检查相应物理/PDP 分支。恰在 PDP 边界的 $r$ 方向不在旧局部定理准入范围内，应显式标记，不能假装 null 拟合本身无定义。

### 1.2 14 维矩确实能够识别三个 nuisance

定义 $P_n=N|u_{0n}|^2$。本分支有 $P_0=P_1=P_a$、$P_2=P_3=P_b$，且 $P_a+P_b=2$。令

$$
z=\sin^2(\pi\mu/4),\qquad
P_a(\mu)=1+\frac{2z^2-z}{z^2+1/4},\quad P_b=2-P_a.
\tag{1.2}
$$

证明：去掉共同列相位和正尺度后，三个 Fourier 系数为 $c_{-1}e^{i\pi/4},1,c_1e^{-i\pi/4}$，其中 $c_m=\sin t/\sin(t+\pi m/4)$、$t=\pi\mu/4$。写 $C=c_{-1}+c_1$、$S=c_1-c_{-1}$，则

$$
C=\frac{\sqrt2z}{z-1/2},\qquad
C^2+S^2=\frac{2z}{(z-1/2)^2}.
$$

四个时间点的 $\cos^2\psi_n=\sin^2\psi_n=1/2$，$\cos\psi_{0,1}=1/\sqrt2$、$\cos\psi_{2,3}=-1/\sqrt2$。除以总 Fourier 功率得到 (1.2)。其对 $z$ 的导数为

$$
\frac{dP_a}{dz}=\frac{z^2+z-1/4}{(z^2+1/4)^2}<0
\quad\text{当 }\mu\in[.22,.42],
$$

因为该区间 $0<z<.105<(\sqrt2-1)/2$。$z$ 随 $\mu$ 严格增加，故 $P_a$ 严格单调且导数非零。

独立均匀 QPSK 和等模酉 DAFT 给出 $E|x_n|^2=1$、$E|x_n|^4=2-1/N=7/4$。设

$$
m_a=E|Y_0|^2,\quad m_b=E|Y_2|^2,\quad f_a=E|Y_0|^4.
$$

Gaussian 噪声的精确四阶恒等式给出

$$
m_a=\tau P_a+s,\qquad
f_a=\frac74(\tau P_a)^2+4s\tau P_a+2s^2,
$$

于是存在光滑总体逆映射

$$
z_a=2\sqrt{2m_a^2-f_a}=\tau P_a>0,\quad s=m_a-z_a,
\quad z_b=m_b-s,\quad \tau=(z_a+z_b)/2,
\quad P_a=z_a/\tau.
\tag{1.3}
$$

由 (1.2) 单调反解 $\mu$。所以包含这些三个量的 14 维矩向量，其 nuisance Jacobian $D_\eta$ 在公开域内部有秩 3。这是总体识别证明；有限样本中 $2\hat m_a^2-\hat f_a$ 可以为负，不能把 (1.3) 当作允许静默截断的求解器。

14 个一次/二次功率 monomial 与常数线性独立，而正 Gaussian 噪声使 $p_0(y)>0$ 于整个观测空间。因此非零线性组合不可能几乎处处为常数，矩协方差 $V$ 严格正定。全部所需高阶矩有限。得分—矩恒等式进一步给出

$$
I_{\eta\eta}\succeq D_\eta^TV^{-1}D_\eta\succ0.
\tag{1.4}
$$

因此 null nuisance 的局部信息非奇异。数值 rank 和优化是否达到相应解仍须记录，不能由总体可识别性宣称每一次数值拟合成功。

### 1.3 root-$R$ 条件与算法边界

后面的渐近结论要求：真实 null nuisance 位于公开域内部；最终 $r$ 基点远离其固定分支边界；使用局部一致的拟合解；nuisance 估计误差为 $O_P(R^{-1/2})$；目标、得分及矩在邻域具有所需光滑性和可积包络；数值求解误差小于渐近统计误差。

本有限 Gaussian 混合提供局部光滑与矩条件，(1.3)–(1.4) 提供识别与非奇异性。统计意义上的一致 null MLE、以及第一步一致且第二步采用一致 $V^{-1}$ 权重的 GMM 满足通常的 root-$R$ 展开。预定有限 starts/迭代的数值实现不自动等同于该理论最优解：优化失败、边界命中、rank 截断、目标梯度和完整成本必须保留。边界命中时不得套用下面的内点正态结论。

## 2. 完整观测 null 有效得分参考

用观测独立拟合

$$
\hat\eta_F=\arg\max_{\eta\in\mathcal E}\sum_{i=1}^R\log p_{0,\eta}(Y_i).
$$

令 $S_i=(s_r,s_\eta^T)^T(Y_i;\hat\eta_F)$，经验 OPG 为 $\hat G=R^{-1}\sum_iS_iS_i^T$。取

$$
\hat\beta=\hat G_{\eta\eta}^{\dagger}\hat G_{\eta r},\qquad
e_i=s_r(Y_i;\hat\eta_F)-\hat\beta^Ts_\eta(Y_i;\hat\eta_F),
$$

$$
\hat J_F=R^{-1}\sum_i e_i^2,\qquad
T_F=\frac{\sqrt R\,\bar e}{\sqrt{\hat J_F}}.
\tag{2.1}
$$

伪逆只按登记 rank 规则作用于观察到的 span，不加任意 jitter。$\hat G,\hat J_F$ 都是拟合参数处的经验量，不是 exact Fisher。近零分母或未准入 tangent 必须显式处理并进入失败账本。

**正交性。** 总体 $e_\eta=s_r-\beta(\eta)^Ts_\eta$ 满足 $E_\eta e_\eta=0$、$E_\eta e_\eta s_\eta^T=0$。微分第一式得到

$$
E_{\eta_0}\left[\partial_\eta e_\eta\big|_{\eta_0}\right]=0.
\tag{2.2}
$$

在第 1.3 节条件下，对经验均值 Taylor 展开：一阶项由 root-$R$ 参数误差乘以均值为零的经验导数构成，乘 $\sqrt R$ 后为 $o_P(1)$；二阶余项为 $O_P(\sqrt R\|\hat\eta-\eta_0\|^2)=o_P(1)$。一致估计 $\beta$ 的额外误差同样是 $o_P(1)$。因此

$$
\sqrt R\,\bar e(\hat\eta_F,\hat\beta)
=R^{-1/2}\sum_i e_{\eta_0}(Y_i)+o_P(1).
$$

null 下 $T_F\Rightarrow N(0,1)$。局部 $r=t/\sqrt R$、$\eta=\eta_0+v/\sqrt R$ 下，由已有单侧 LAN 和有效正交性，

$$
T_F\Rightarrow N(t\sqrt{J_{\rm eff}},1),\qquad t\ge0.
\tag{2.3}
$$

未知 nuisance 的局部位移 $v$ 被一阶消去。该参考使用完整观测，但仅对碰撞方向作局部检验，未优化有限 $\delta$ 的完整备择 likelihood。

## 3. 14 维正交矩与同矩 J 基线

定义固定特征

$$
\psi(Y)=\big(|Y_i|^2,\ |Y_i|^2|Y_j|^2:0\le i\le j<4\big)^T\in\mathbb R^{14},
$$

其中先列四个一次功率，再按固定词典序列十个二次乘积。设 $M(\eta)=E_{0,\eta}\psi$、$V(\eta)=\operatorname{Cov}_{0,\eta}(\psi)$，$D=[D_r,D_\eta]$。这些量来自有限 QPSK 与精确 Gaussian 多项式恒等式，浮点评估不等于区间误差证书。

M14 用自身两步 GMM 拟合 $\hat\eta_M$，第二步权重由第一步一致估计冻结。理论最优权重为 $V^{-1}$。在最终点定义

$$
G_M=D^TV^{-1}D,\quad
\beta_M=G_{M,\eta\eta}^{\dagger}G_{M,\eta r},\quad
a=V^{-1}(D_r-D_\eta\beta_M).
$$

总体恒等式为

$$
a^TD_\eta=0,\qquad
J_M=a^TD_r=a^TVa\ge0.
\tag{3.1}
$$

当 $J_M>0$，定义

$$
T_M=\frac{\sqrt R\,a(\hat\eta_M)^T[\bar\psi-M(\hat\eta_M)]}
{\sqrt{a(\hat\eta_M)^TV(\hat\eta_M)a(\hat\eta_M)}}.
\tag{3.2}
$$

对固定观测分布求参数导数，$E\psi-M(\eta_0)=0$ 消去 $a$ 的导数，而剩余项为 $-a^TD_\eta=0$。因此相同 root-$R$ / 光滑条件给出 null 下标准正态，以及局部备择下

$$
T_M\Rightarrow N(t\sqrt{J_M},1),\qquad 0\le J_M\le J_{\rm eff}.
\tag{3.3}
$$

最后一个不等式来自将完整有效得分投影到该线性矩 span。它描述线性矩方法，不是整个 14 维非线性统计的精确信息。旧四点 14 维投影为正是数值证据；本文件没有把这些数值升级成严格舍入下界，也不假定新内点的有限样本性能。

### 3.1 同一 14 维矩的经典过度识别 J 检验

使用相同的两步 GMM 拟合，在最终估计处重新计算矩协方差，并取
$\hat W=V(\hat\eta_M)^{-1}$ 构造 J 统计量；它不是第二步优化期间固定的第一步协方差权重。J 统计量为

$$
Q_J=R[\bar\psi-M(\hat\eta_M)]^T\hat W[\bar\psi-M(\hat\eta_M)].
\tag{3.4}
$$

$\hat W\to V^{-1}$，14 维协方差不截断且 $\operatorname{rank}D_\eta=3$ 时，null 极限为 $\chi^2_{11}$。若实现发生数值 rank 截断，必须报告保留 rank，不能仍机械声称 11 个自由度；正式阈值以登记校准为准。

令 $A=V^{-1/2}D_\eta$、$P=A(A^TA)^{-1}A^T$、$v=(I-P)V^{-1/2}D_r$。局部 Gaussian 矩实验中，拟合后的残差为

$$
Z_\perp=(I-P)\sqrt R\,V^{-1/2}(\bar\psi-M_0)+o_P(1),
$$

而 $T_M=v^TZ_\perp/\|v\|$、$Q_J=\|Z_\perp\|^2+o_P(1)$。因此局部备择下

$$
Q_J\Rightarrow\chi^2_{11}(t^2J_M).
\tag{3.5}
$$

M14 使用已知的一侧碰撞方向；J 检验将额外十个正交残差方向的噪声也纳入。对这个理想局部 Gaussian 单方向族，单侧线性统计具有相应 Neyman–Pearson 优势。但有限 $R$ 的拟合误差、校准误差和有限 $\delta$ 的方向失配可以让 J 更好；这正是必须保留的强基线，不能只展示击败 C2。

### 3.2 未正交消融的真实含义

完整 null 内点 MLE 满足 $\sum_i s_\eta(Y_i;\hat\eta_F)\approx0$，所以完整 raw 与正交 score 的和近似相同。类似地，采用同一冻结权重的 GMM 一阶条件为

$$
D_\eta(\hat\eta_M)^T\hat W[\bar\psi-M(\hat\eta_M)]\approx0.
$$

因此 $D_r^T\hat Wg$ 与 $(D_r-D_\eta\beta)^T\hat Wg$ 的分子也近似相同。未正交消融主要比较 nuisance 方差校正、不同最终权重或有限数值误差，不能被解释为凭空创造了独立的分子信号。

同一点上若两个统计仅差固定正倍数，分别准确校准后拒绝域相同。不同 nuisance 点的尺度变化和有限拟合误差可能使统一校准表现不同，但不能把常量重标定叫作信息增益。本轮按冻结设计保留消融，不为制造差异临时换 fold 或另借真值估计。

## 4. C2 二阶对称性基线的结构限制

C2 仅拟合两个可识别的组合方差：配对功率均值 $(m_a,m_b)$。三个 nuisance 不能只从一次功率均值识别；不得借高阶拟合器后仍称其为纯二阶方法。定义

$$
d(Y)=(|Y_0|^2-|Y_1|^2,\ |Y_2|^2-|Y_3|^2)^T,
\quad Q_{C2}=R\bar d^T\hat\Sigma_d^{\dagger}\bar d.
\tag{4.1}
$$

这里 $\hat\Sigma_d$ 若采用同组 $d$ 的经验协方差，则对应以下结论；若实现使用另一个模型协方差，需分别说明其条件，不能沿用经验 studentization 的结论。

**有限分离均值对称命题。** 本轮中心 $\mu\in\{.27,.31,.35\}$、$0\le\delta\le.12$ 时，即使跨越条件 PDP 分支，仍有

$$
E|Y_0|^2=E|Y_1|^2,\qquad E|Y_2|^2=E|Y_3|^2.
\tag{4.2}
$$

证明：所有物理 Doppler $\nu=\mu\pm\delta$ 均在 $(0,.5)$，共同 rounded center=0。对保留的整数 atom，冻结 Dirichlet 系数可写为

$$
\alpha_m(\nu)=e^{3\pi i\nu/4}e^{-\pi im/4}
\frac{\sin(\pi\nu)}{4\sin[\pi(m+\nu)/4]}.
$$

除共同列相位后，$e^{-\pi im/4}$ 以外的系数为实数；正窗口归一化、截断和实掩码剪枝均保持此结构。去掉各列相位后的时间响应矩阵 $\widetilde B$ 满足

$$
\widetilde B_{1,:}=\overline{\widetilde B_{0,:}},\qquad
\widetilde B_{3,:}=\overline{\widetilde B_{2,:}},
$$

从而 $\widetilde B^H\widetilde B$ 是实对称矩阵。将列相位吸收到独立圆 Gaussian 增益中不改变其分布。对每个正对角 PDP $D$，$u=D^{1/2}z$ 在共轭下不变，其归一化分母 $u^H\widetilde B^H\widetilde Bu/N$ 也在共轭下不变，所以归一化增益与其共轭同分布。这给出两对响应功率相同的期望。该结论逐个 $D$ 成立，因此任意实际条件 PDP 混合都成立，不需要交换标签权重相同。最后，独立 QPSK 的 $E|x_n|^2=1$ 与相同噪声功率得到 (4.2)。

此证明不推广到 rounded center 改变、alias 或其他未核实物理构造。本轮 $.06/.12$ 虽然不属于原碰撞 PDP 分支，却仍在本命题的范围内。

在这些固定分布下，$E d=0$、所需矩有限，正 Gaussian 噪声保证 $\operatorname{Cov}(d)$ 正定。因此经验 studentization 时 $Q_{C2}\Rightarrow\chi^2_2$，既在 null 下成立，也在本命题覆盖的固定有限分离下成立；它不能成为这些备择的一致均值检验。在 $r=t/\sqrt R$ 的局部备择下同样没有均值非中心量。

有限 $R$ 的高阶分布变化可能影响 C2 的尾部和实际拒绝率，应保留实测值。但击败此结构无目标均值方向的二阶基线，单独不足以证明 M14 的研究优势，必须同时面对 J14 和完整观测 null score。

## 5. 分支半径、原点规划与有限 $\delta$

真实条件 PDP 限制为

$$
L(\nu)=\lfloor67(1+\nu/6)\rfloor.
$$

在中心 $\mu$ 的固定 $L$ 分支，其 Doppler 区间为

$$
\nu\in[6(L/67-1),\ 6((L+1)/67-1)).
$$

局部证明所需的对称开邻域半径不超过中心到两端的最小距离，并同时受物理支撑分支限制。恰在离散端点时没有这样的固定对称开邻域。特别地，$L=70$ 对应 $[18/67,24/67)$。

| 中心 | 固定 L70 对称分离半径上确界 | 本轮解释 |
| --- | ---: | --- |
| .27 | .001343283582 | 原弱信号/近边界点；不能期待小预算内显著局部检出 |
| .31 | .041343283582 | 主内点；.005/.015/.025 保持 L70 分支 |
| .35 | .008208955224 | 原弱信号点；大于此值即离开原对称分支 |

所有中心的 $.06/.12$ 都离开原 L70 分支。它们仍由完整实际条件生成器产生，但属于有限分离压力测试，不是已证固定分支 LAN 的验证。

### 5.1 原四点所需重复数仅为规划代理

取旧结果的 heldout 投影残差二阶矩 $\widetilde J$，并把 $\delta$ 推到其分支上沿，仅作局部数量级估算。单侧 size .05、power .8 的理想正态位移为 $z_{.95}+z_{.8}=2.48647486$，代理公式为

$$
\widetilde R_{80}=\frac{(z_{.95}+z_{.8})^2}{\widetilde J\,r^2}.
$$

| mu | s | 上沿 r | R=1024 的代理位移 | 代理 $\widetilde R_{80}$ |
| --- | ---: | ---: | ---: | ---: |
| .27 | .2 | 2.38638e-5 | .02425 | 1.07647e7 |
| .27 | 1 | 2.38638e-5 | .00300 | 7.02674e8 |
| .35 | .2 | 6.47256e-4 | .77003 | 1.06772e4 |
| .35 | 1 | 6.47256e-4 | .08426 | 8.91716e5 |

来源为冻结 [information_cases.json](../../results/afdm_collision_resolution/information_v1/information_cases.json) 的确定性代入，未采样。旧残差含非负训练投影误差，并非认证 $J_{\rm eff}$；上沿没有 nuisance 移动余量，且密度余项常数未知。这些数字不是样本复杂度下界、功效保证或新预算申请，只解释为什么保留旧点之外还需要一个真实分支内部场景。

### 5.2 一步估计的适用范围

本轮实现保存未约束的一步输出及其单侧版本：

$$
\widetilde r_F=\frac{\bar e}{\hat J_F},\qquad
\widetilde r_M=\frac{a^T[\bar\psi-M(\hat\eta_M)]}{a^TD_r},\qquad
\widehat r_j=\max(0,\widetilde r_j),\quad j\in\{F,M\}.
\tag{5.1}
$$

这里没有对 $r$ 作上界投影，也不反算物理分离 $\delta$。实现根据拟合 nuisance 所在 PDP 分支计算半径 $\rho(\hat\mu)$，保存
$r_{\mathrm{branch,max}}=\rho^2\log(1/\rho^2)$、未约束输出为负及单侧输出达到或超过该分支界限的标记。该半径只描述拟合分支，不使用生成真值，也不是有限分离估计误差保证。

在正信息、内点、固定分支且 $r$ 足够小的条件下，坐标关系 $r=\delta^2\log(1/\delta^2)$ 的小分离逆支为

$$
\delta(r)=\sqrt{-r/W_{-1}(-r)},\qquad \delta(0)=0.
$$

这是未执行的理论坐标变换；若以后要报告 $\delta$ 估计，必须另行核实逆支定义域、拟合分支适用性及有限分离误差。近零分母、约束触边以及估计值超过拟合点的固定分支半径均需明确标记，不能静默裁剪后当作内点成功。边界估计不是普通正态分布；如需区间，应反演相应单侧检验，不能对 $\delta$ 使用普通 Wald SE。

即使同分支，有限 $.005/.015/.025$ 也不自动处于足够小的渐近区间：已有密度余项相对首项的阶为 $1/\log(1/\delta^2)$，常数未知。对 $.06/.12$、原 $.27/.35$ 超出各自分支半径的点、或拟合 nuisance 的分支未准入时，不能把 (5.1) 解释为已保证准确的物理分离估计。算法数值输出可原样保存，外部评估应标记“局部解释不适用”，不能据此删掉检测结果或误差较大的样本。

在合法局部序列 $r=t/\sqrt R$ 下，分离尺度为

$$
\delta_R\sim\sqrt{2t}\,R^{-1/4}(\log R)^{-1/2}.
$$

这只是反参数化及局部实验结论，不是仅换坐标得到的方法优势。

## 6. 完整 estimated-null 流程的有限网格校准

每个方法、每个 $R$ 的统计量都是固定映射 $T(Y_{1:R})$，包括连续 nuisance 拟合、OPG/GMM 权重估计、rank 规则、触边和失败规则。校准组必须运行完全相同的映射，不能用已知生成 nuisance 代替估计。

对公共 null 网格 $\mathcal G$，在每个 $\eta_g$ 下生成 $B$ 个独立校准组，保存统计 $T_{g,b}$，并与评估组独立。定义

$$
p_g(T)=\frac{1+\sum_{b=1}^B\mathbf1\{T_{g,b}\ge T\}}{B+1},
\qquad p_{\max}(T)=\max_{g\in\mathcal G}p_g(T).
\tag{6.1}
$$

若真实 null nuisance 等于某个 $\eta_{g_*}$，则该点的校准统计与评估统计可交换，包括各自估计 nuisance 的全过程。保守处理 ties 后，$p_{g_*}$ 是 super-uniform；$p_{\max}\ge p_{g_*}$，所以

$$
P_{0,\eta_{g_*}}\{p_{\max}\le\alpha\}\le\alpha.
\tag{6.2}
$$

不需对 nuisance 网格做 Bonferroni。该概率同时对校准库和新评估组的随机性平均；它不保证条件于某一个已经实现的校准库仍有 size≤$\alpha$，也不提供连续 nuisance 域或 off-grid 的统一保证。

对冻结 $B=128$、$\alpha=.05$，各点应取升序第

$$
k=\lceil(B+1)(1-\alpha)\rceil=123
$$

个校准统计，跨网格取最大阈值，并使用严格 $T>\text{threshold}$。无 ties 单点 size 为 $6/129\approx.04651$；sup 阈值只会更保守。普通 `quantile(.95, method="higher")` 在 B=128 时对应第 122 个次序统计，不能不加核对就宣称同样的 ≤.05 性质。

若程序可能失败，配置必须先定义完整的失败/排序/拒绝约定并单独记录状态。不能删除校准或评估失败后仍把成功子集称为 (6.2) 的样本。所有方法消费同一原始组和同一 $R$；校准与评估严格分离，评估结果不参与选择阈值。

冻结 PLAN 的 null 评估 Wilson 上界≤.10 是有限样本经验可用性门槛，不是把理论 size 目标从 .05 改成 .10。功效比较按预登记家族校正的配对区间及至少 .10 的点差判定；不能仅凭某一格较大、未校正 sample SE 或相关方法共享数据就宣称优势。Off-grid 只能作经验压力测试。

## 7. 成本、可验证优势与未实现项

M14 的观测特征构建为 $O(R\cdot14)$；组均值形成后，每个 nuisance 候选的 GMM 目标只用固定 14 维量。几何/QPSK polynomial 常量可以预缓存，但初始化、矩构造、两步拟合、统计、校准与摊销均须计费。

完整 null MLE 每个 nuisance 候选需约 $64R$ 个相位消元分量；经验完整得分还需同组的四列 score。它是本轮主要的性能/成本参考，同样估计未知参数。完整 null 方法可以比 M14 更有局部信息，M14 可能以信息损失换取成本；只有实际配对功效与完整成本同时满足冻结判据，才可声称这一交换有优势。

同 14 维 J 检验沿用 M14 拟合，额外统计成本很小，是必须保留的经典强基线。C2 只用其自身可识别的二阶组合，不能借用高阶或完整 MLE 的成本而不记账。所有方法均需单列 setup、校准、每组推断及摊销成本，不把 kernel 的快慢冒充部署收益。

**明确未实现：** 非零 $\delta$ 实际边际 profile likelihood 参考仍需 CP1 积分与额外参数优化。旧默认 $12\times24=288$ 个 CP1 节点使每候选约有 $64\times288$ 个分量，近碰撞还有积分资格问题。它可以作为后续昂贵参考，但本轮没有其完整性能比较，也不能由复杂度比直接宣称已经测得相应加速或与它非劣。

本轮只能检验冻结 N4 条件实际模型中是否出现：M14 对 J14/C2 的配对功效优势，或相对完整 null score 至少两倍的完整成本下降且满足预定功效非劣界。经典 score、GMM、J 检验和排序校准不是本工作首创；潜在贡献在于实际归一化碰撞机制提供了可计算的方向，以及该方向是否在诚实的未知 nuisance 比较中产生可复现收益。

## 未证项与验证说明

- 本文件给出模型识别、正交局部理论、C2 对称性和有限网格交换性推导；新推导须经本轮独立审查。没有把优化器的有限迭代输出当成自动满足理论 root-$R$ 条件。
- 没有证明任意有限 $\delta$ 的误差界、连续 nuisance 全域的有限样本 size、完整备择最优性、具体 Fisher 数值下界、生产 N1024 性能或 FER/译码收益。
- 本文件未运行随机实验；旧四点规划表来自只读保存摘要。实际有限样本优势、失败机制、置信区间和成本由本轮独立校准/评估及 raw 审计回答，允许无优势或负结果。
- 全部拟合、分支、rank、近零分母、校准失败与边界命中应在正式记录中保留；后续修订只能按冻结 PLAN 新登记，不覆盖第一次失败。
