# SP-AFDM 首轮联合估计–检测的信息模型：Codex 独立推导

作者：**Codex**。日期：2026-10-09。

排版勘误（2026-10-10）：式 (18) 的 I/Q 均值之间补回漏印的加号；原数值核验与实际 kernel 均使用正确加法，数值结论不变。

推导归属：本文的推导、化简及组织由 Codex 主会话完成，辅助代理仅核查指定数学步骤。已知问题背景来自用户转述；构造本模型时未阅读 Claude 新的 c1r1_model.py、c1-scalar-closure.md 或其拟合/预测结果文件。数学工具属于线性估计、复高斯积分与消息传递的既有理论，不申明文献优先权。

这是用户要求的**第一阶段独立推导**。本轮不比较 Claude 的推导，不审计其折叠/双稳态结论，不启动新性能仿真，不改 STATE.md。

## Target

对象是第一外轮：零译码先验进入接收机，经过导频 refit 和 **20 次 inner joint 更新**，产生交给 LDPC 的 LLR。推导该输出的信息指标如何依赖接收机系数数 K、实际 AFDM 算子、导频、功率和调度。

“第一次 inner 更新”和“第一外轮结束”严格区分。前者获得二次型的显式分布；后者获得保留同一观测及全部算法记忆的完整有限维递推与概率积分。

## Status

**COHERENT AS STATED：有限维精确模型及下面标明条件的恒等式。**

尚未得到只需几个标量、即可廉价预测真实 20 步输出的闭式状态演化。本文不给这种尚未证明的压缩贴上“完整解析预测器”的标签。完整有限维模型是基准；低维压缩必须逼近它，而不能把未知相关项设为零。

## Invariant Object

对第 j 个编码 bit，令 \(b_j\in\{0,1\}\)、\(s_j=1-2b_j\)，第 T 次 inner 更新给出的 raw LLR 为 \(\Lambda_{T,j}\)。实际交给译码器的量为
\[
L_{T,j}=\operatorname{clip}(\Lambda_{T,j},-20,20).
\]
本研究代码采用的“信息量”是
\[
\widehat{\mathcal I}_T
=1-\frac1{2N}\sum_{j=1}^{2N}\log_2(1+e^{-s_jL_{T,j}}),
\qquad
\mathcal I_T=E[\widehat{\mathcal I}_T].
\tag{1}
\]
它是固定 LLR 尺度的对数损失指标，不能未经校准就称 Shannon 互信息。对于均匀 bit，
\[
\mathcal I_T
=I(b;L_T\mid j)
-E\,D_{\rm KL,2}\!\left(P(b\mid L_T,j)\,\|\,Q_{L_T}(b)\right),
\quad Q_l(0)=\frac1{1+e^{-l}}.
\tag{2}
\]
证明：交叉熵等于真实条件熵加 KL，且 \(H(b\mid j)=1\)。因此信息损失有**可区分性损失与 LLR 校准损失**两部分。式 (1) 可以为负；不把它截成零。

## Assumptions

- 接收机为当前 SPg_flat、给定延迟支持、每 tap 的 DPSS 阶数固定；系数先验为 \(CN(0,I_K/K)\)。不把 Slepian、自适应选阶或未知支持获取混入本模型。
- 第一外轮的译码先验为零；数据星座为 \(d_i=c(\pm1\pm i)\)，\(c=\sqrt{P_d/2}\)。所有 I 位在前，所有 Q 位在后；正 LLR 表示 bit 0。
- \(P_p=\|p\|^2/N>0\)、\(P_d>0\)、噪声方差 \(n_0>0\)。物理单位可取 \(P_p=\rho,P_d=1-\rho,n_0=10^{-S/10}\)。源码内部则为 \(P_d=1/2,P_p=\rho/[2(1-\rho)],n_0=10^{-S/10}/[2(1-\rho)]\)。
- 全文统一使用 time-domain 观测 \(Y=\operatorname{IDAFT}(y_{\rm AF})\)。输入符号 x、p、d 仍在 DAFT 域，算子已包含 IDAFT、CPP 与时变信道。
- 对二阶数据恒等式，使用 \(E[d]=0,E[dd^H]=P_dI\)；不因此假定整段 LDPC 码字独立。最终概率积分保留实际码字分布。
- 条件于真实射线几何，原 C1 生成器的射线增益独立、零均值、proper complex Gaussian。最终分布计算使用真实射线算子；不会把 DPSS 截断误差伪装成独立噪声。
- 一般恒等式不假定导频列正交，也不假定每次 inner 更新的误差独立。

## Notation

\[
\mathcal H(h)=\sum_{\alpha=1}^{K}h_\alpha A_\alpha,\qquad
B(x)=[A_1x,\ldots,A_Kx],\qquad
\mathcal H(h)x=B(x)h.
\tag{3}
\]
其中 \(A_\alpha:\mathbb C^N\to\mathbb C^N\) 是接收机 DPSS/延迟算子。定义
\[
(G_H)_{\alpha\beta}=\frac1N\operatorname{tr}(A_\alpha^HA_\beta),
\qquad q(h)=h^HG_Hh=\|\mathcal H(h)\|_F^2/N.
\tag{4}
\]
当前相同延迟内使用正交 DPSS、不同整数延迟对应不同矩阵对角带，故该物理范数坐标可取 \(G_H=I\)；保留 \(G_H\) 的写法便于核对源码 TimePathOps.power。

\(t=0,\ldots,T-1\) 表示 inner 次数；\(\beta=.3\) 是 damping；\(v_t\) 是数据**报告方差**的均值；\(V_t\) 是增益**报告方差**的总和。它们不预设等于真实 MSE。\(k=K/N\)。n₀ 表示噪声，绝不是码长。

## Derivation Strategy

先求导频线性回归产生的真实相关项，再把 inner kernel 写成自然参数递推。利用首次更新的代数消去得到显式 LLR；随后从真实生成分布构造整轮信息积分。最后用边缘似然梯度说明自相关修正的统计来源。

## Derivation Map

1. 导频回归 \(W_p\) → 平滑矩阵 \(Q_p\) → 数据信号被回归吸收的部分及 K 的谱依赖。
2. 同一观测 Y + 原始状态 → 精确 T 步自然参数递推 → raw LLR。
3. 首个 inner 的特殊初值 → 二次型加常数之比 → 条件分布、矩与 K 维低秩运算。
4. 真实射线/码字先验 → Y 的条件高斯分布 → 第一外轮的信息均值及分布。
5. 高斯信道边缘化 → 矩阵方差修正；用于判断低维闭合能否成立，不替换现有接收机。

## Main Derivation

### 1. 导频回归中的自相关项是可精确计算的

当前 flat refit 给出
\[
B_p=B(p),\quad \lambda_K=K(n_0+P_d),\quad
W_p=(B_p^HB_p+\lambda_KI)^{-1}B_p^H,\quad h_0=W_pY,
\tag{5}
\]
\[
Q_p=B_pW_p,\qquad T_p=I-Q_p.
\tag{6}
\]
\(Q_p\) 是 Hermitian 正半定 ridge 平滑矩阵，一般**不幂等**。不可无条件把它当正交投影。

条件于真实固定信道 \(H_\star\)，有 \(Y=H_\star(p+d)+w\)。对任意固定目标系数 \(h_\star\)，由式 (5) 得
\[
\boxed{
E[(h_0-h_\star)d^H\mid H_\star]=P_dW_pH_\star,\qquad
E[(h_0-h_\star)w^H\mid H_\star]=n_0W_p.
}
\tag{7}
\]
证明：展开 \(W_pH_\star p+W_pH_\star d+W_pw-h_\star\)，利用 d、w 的零均值、独立性及二阶矩。即使均值模型的 MSE 正确，这两个交叉项仍存在。

消除估计导频后的观测精确为
\[
Y-B_ph_0=T_pH_\star d+T_pH_\star p+T_pw.
\tag{8}
\]
所以期望的数据信号也被 \(T_p\) 作用；不能只增加一个“信道误差噪声”而保持信号增益不变。

若 \(g_\ell\) 为 \(B_p^HB_p\) 的非零特征值，则
\[
d_p(K):=\operatorname{tr}Q_p
=\sum_\ell\frac{g_\ell}{g_\ell+K(n_0+P_d)},\qquad
\operatorname{tr}Q_p^2=\sum_\ell
\left[\frac{g_\ell}{g_\ell+K(n_0+P_d)}\right]^2.
\tag{9}
\]
这是 K 进入自相关效应的首个明确位置：**导频回归吸收了多少观测方向，以及吸收得多强**。

原 C1 的单位模射线算子和归一化射线功率给出 \(E[H_\star H_\star^H\mid\vartheta]=I\)。因此，在固定几何 \(\vartheta\) 下，
\[
E\|T_pH_\star d\|^2
=P_d\left[N-2d_p(K)+\operatorname{tr}Q_p^2\right].
\tag{10}
\]
这是关于所指定平均的恒等式，不是每帧标量衰减。仅在额外的等信息导频条件 \(B_p^HB_p=NP_pI\) 下，
\[
\frac{d_p(K)}N
=\frac{kP_p}{P_p+k(n_0+P_d)}.
\tag{11}
\]
当前实际 Gram 应使用式 (9)，不能直接宣称式 (11) 严格成立。

### 2. 整个第一外轮：保留同一 Y 的精确递推

以下是原 kernel 的代数重写，不是重新提出的接收机。定义 \(m_0=0,x_0=p,h_0=W_pY,v_0=P_d,V_0=1\)，并初始化
\[
s_{-1}=0,\quad u_{-1}=0,\quad \bar x_{-1}=p,\quad\bar h_{-1}=h_0.
\]
每个 \(t=0,\ldots,T-1\)，先计算
\[
X_t=\|x_t\|^2/N,\quad q_t=q(h_t),\quad
\widetilde b_t=v_tq_t+V_tX_t,\quad
\widetilde a_t=\widetilde b_t+V_tv_t.
\tag{12}
\]
首步 \(b_0=\widetilde b_0,a_0=\widetilde a_0\)；后续
\[
b_t=\beta\widetilde b_t+(1-\beta)b_{t-1},\qquad
a_t=\beta\widetilde a_t+(1-\beta)a_{t-1}.
\tag{13}
\]
输出残差及其报告精度为
\[
s_t=\frac{\beta[Y-B(x_t)h_t+b_ts_{t-1}]}{n_0+a_t}
 +(1-\beta)s_{t-1},\qquad
u_t=\frac{\beta}{n_0+a_t}+(1-\beta)u_{t-1}.
\tag{14}
\]
再更新
\[
\bar x_t=\beta x_t+(1-\beta)\bar x_{t-1},\qquad
\bar h_t=\beta h_t+(1-\beta)\bar h_{t-1}.
\tag{15}
\]
因为 \(B(x)\) 对 x 线性，源码保存的 Bb 精确等于 \(B(\bar x_t)\)，无须增加一个独立矩阵状态。

保留源码 precision floor \(\varepsilon=10^{-12}\)：
\[
J_{x,t}=\max\{u_tq(\bar h_t),\varepsilon\},\qquad
J_{h,t}=\max\{u_t\|\bar x_t\|^2,\varepsilon\}.
\tag{16}
\]
定义数据自然参数
\[
\boxed{
z_t=J_{x,t}(x_t-p)+\mathcal H(\bar h_t)^Hs_t-u_tV_t\bar x_t.
}
\tag{17}
\]
于是 raw LLR、软均值与报告方差为
\[
\Lambda_{t+1}
=4c\begin{bmatrix}\Re z_t\\ \Im z_t\end{bmatrix},\qquad
m_{t+1,i}
=c\left[\tanh\frac{\Lambda_{t+1,i}}2
+i\tanh\frac{\Lambda_{t+1,N+i}}2\right],
\tag{18}
\]
\[
x_{t+1}=p+m_{t+1},\qquad
v_{t+1}=\frac1N\sum_i\max(P_d-|m_{t+1,i}|^2,0).
\tag{19}
\]
对 flat prior，增益和报告总方差直接化为
\[
\boxed{
h_{t+1}=
\frac{J_{h,t}h_t+B(\bar x_t)^Hs_t-u_tNv_t\bar h_t}
{K+J_{h,t}},\qquad
V_{t+1}=\frac{K}{K+J_{h,t}}.
}
\tag{20}
\]
推导式 (17)：将源码 \(r_x=x_t+J_{x,t}^{-1}(\mathcal H(\bar h_t)^Hs_t-u_tV_t\bar x_t)\) 减 p，再除以 pseudo-variance。推导式 (20)：把 \(r_h=h_t+J_{h,t}^{-1}(\cdots)\) 代入 \(\tau r_h/(\tau+1/J_{h,t})\)，并使用 \(\tau=1/K\)。没有引入独立误差假设。

式 (12)–(20) 与给定 Y 合起来，就是第一外轮完整的有限维动力学。K 不仅出现在一个误差比例中，还控制增益 shrinkage、报告方差和实际算子集合。s、damping 均值和报告精度保留了内轮历史；不能在每一步重抽一个独立等效噪声。

### 3. 第一次 inner 更新可以进一步精确消去

令
\[
q_0=h_0^HG_Hh_0,\qquad D_0=n_0+P_p+P_d+P_dq_0.
\tag{21}
\]
首步 \(s_0=\beta T_pY/D_0,u_0=\beta/D_0,\bar x_0=p,\bar h_0=h_0\)。故
\[
\boxed{z_0=\frac{\beta}{D_0}
\left[\mathcal H(h_0)^HT_pY-p\right].}
\tag{22}
\]
这里的 \(-p\) 来自**仍然存在的数据端 Onsager 项**，不能因初始化 \(s_{-1}=0\) 就把所有 Onsager 项删掉。

若 data precision floor 未触发且 \(q_0>0\)，还可写
\[
r_x-p=\frac{\mathcal H(h_0)^HT_pY-p}{q_0}.
\tag{23}
\]
式 (22) 的 LLR 表达式更稳健：由于 \(x_0-p=0\)，即使 data floor 触发，它仍成立。

令 \(e_i\) 为第 i 个标准基向量，并定义
\[
M_i=[A_1e_i,\ldots,A_Ke_i],\qquad
C_i=W_p^HM_i^HT_p,\qquad
G=W_p^HG_HW_p.
\tag{24}
\]
由于 \(\mathcal H(h_0)e_i=M_iW_pY\)，得到
\[
\boxed{
\Lambda_{1,i}
=\frac{4c\beta\,\Re(Y^HC_iY-p_i)}
{n_0+P_p+P_d+P_dY^HGY},\qquad
\Lambda_{1,N+i}
=\frac{4c\beta\,\Im(Y^HC_iY-p_i)}
{n_0+P_p+P_d+P_dY^HGY}.
}
\tag{25}
\]
**这是观测二次型加常数之比。** \(\hat H\) 与被检测信号共享 Y 的依赖已经显式保留。式 (25) 不需要正交导频，不需要高斯等效误差，不需要 SP/FER 拟合。

### 4. 一个直接后果：冷启动的首次增益更新可发生共同相位翻转

利用 ridge normal equation，
\[
B_p^HT_pY
=B_p^HY-B_p^HB_ph_0
=K(n_0+P_d)h_0.
\tag{26}
\]
若 gain precision floor 未触发，则
\[
v_{q,0}=\frac{D_0}{\beta NP_p},\qquad
\boxed{
h_1=\frac{1-P_d/P_p+k(n_0+P_d)/P_p}
{1+Kv_{q,0}}\,h_0.
}
\tag{27}
\]
当
\[
P_d>P_p,\qquad
k<\frac{P_d-P_p}{n_0+P_d},
\tag{28}
\]
式 (27) 的实系数为负，出现共同的 \(\pi\) 相位翻转。物理单位 \(\rho=.3\) 下，右侧界在 6.5 dB 为 .432960，在 8 dB 为 .465935。

这是**当前算法首个 cold inner 更新的精确暂态性质**，不是物理信道改变。首步 LLR 仍使用 h₀；不能把 h₁ 的性质误说成第一外轮输出，也不能仅据此判定算法存在 bug 或会失败。它说明：从第一步就套用“每步都是校准后验、MSE 平滑下降”的状态假设不成立。

源码的另一个必要状态事实是：h₀ 来自 ridge，但增益报告方差被初始化为先验总量 \(V_0=1\)。它不是导频等效高斯模型下 posterior covariance 的迹。建模时不能自行把 V₀ 改成真实/预测首遍 MSE。

### 5. 首次 LLR 的条件分布可以由高斯二次型理论求得

令 \(\vartheta\) 包含真实延迟、多普勒和每 tap 的射线数，\(T_r(\vartheta)\) 为真实射线算子，\(g\sim CN(0,C_{\rm ray})\)。条件于完整码字 d 与 \(\vartheta\)，
\[
Y=\mathcal T_\vartheta(p+d)g+w,\quad
\mathcal T_\vartheta(x)=[T_1x,\ldots,T_Rx],
\]
\[
\boxed{
Y\mid(d,\vartheta)\sim CN(0,\Sigma_{d,\vartheta}),\qquad
\Sigma_{d,\vartheta}
=n_0I+\mathcal T_\vartheta(p+d)C_{\rm ray}
\mathcal T_\vartheta(p+d)^H.
}
\tag{29}
\]
这一步使用真实射线高斯增益，而不是把接收机 DPSS 先验当真实生成器。真实模型与接收机表示失配被保留。给定几何和码字后，\(W_p,M_i,G\) 固定；这里不能加入基于 Y 的支持筛选、能量重估或逐帧信道归一化。解除条件时须平均条件分布，不能用平均协方差代替混合分布并仍称精确。

以 I 位为例，令 \(D_i=(C_i+C_i^H)/2\)、\(\kappa=4c\beta\)、\(A_0=n_0+P_p+P_d>0\)。给定实数 \(\ell\)，式 (25) 等价于
\[
P(\Lambda_{1,i}\le\ell\mid d,\vartheta)
=P\!\left[
Y^H(\kappa D_i-\ell P_dG)Y
\le\kappa\Re p_i+\ell A_0
\right].
\tag{30}
\]
若 \(\lambda_j(\ell)\) 是
\[
\Sigma^{1/2}(\kappa D_i-\ell P_dG)\Sigma^{1/2}
\]
的非零特征值，则右侧就是
\[
P\!\left[\sum_j\lambda_j(\ell)E_j
\le\kappa\Re p_i+\ell A_0\right],
\qquad E_j\overset{\rm iid}{\sim}\operatorname{Exp}(1).
\tag{31}
\]
证明：白化 proper complex Gaussian Y，再酉对角化 Hermitian 二次型。特征值可正可负，不能当作全正权重分布。Q 位改用 \((C_i-C_i^H)/(2i)\) 与 \(\Im p_i\)。

矩阵的秩至多 \(\min(N,2K)\)：其像空间包含于
\[
\operatorname{ran}W_p^H+
\operatorname{ran}(T_p^HM_i).
\]
因此首次更新的分布可归约为至多 2K 个加权指数变量；这是实际结构下的显式分布计算，不是宣称 LLR 为高斯。

还可直接求比值矩。令 A、B 为 Hermitian，c₀、d₀ 为实数，记
\[
\Sigma_t=(\Sigma^{-1}+P_dtG)^{-1},\quad
Z(t)=\det(I+P_dt\Sigma^{1/2}G\Sigma^{1/2})^{-1},
\]
\[
R_A=\frac{Y^HAY-c_0}{A_0+P_dY^HGY}.
\]
其中 \(R_B\) 按同式使用 B、d₀ 定义。
则
\[
E[R_A]
=\int_0^\infty e^{-A_0t}Z(t)
\left[\operatorname{tr}(A\Sigma_t)-c_0\right]dt,
\tag{32}
\]
\[
E[R_AR_B]
=\int_0^\infty t e^{-A_0t}Z(t)
\left[
(\operatorname{tr}(A\Sigma_t)-c_0)
(\operatorname{tr}(B\Sigma_t)-d_0)
+\operatorname{tr}(A\Sigma_tB\Sigma_t)
\right]dt.
\tag{33}
\]
证明使用 \(r^{-1}=\int_0^\infty e^{-tr}dt\)、\(r^{-2}=\int_0^\infty te^{-tr}dt\) 及指数倾斜后的高斯协方差 \(\Sigma_t\)。\(A_0>0\) 与有限高斯四阶矩保证绝对可积，允许交换积分。乘相应 \(\kappa\) 即得到 raw LLR 矩；裁剪后的指标必须再按其定义积分。

### 6. 第一外轮结束的信息模型：一个固定高斯输入贯穿 T 步

令 \(\Psi_{T,K}(Y;p)\) 表示式 (5)、(12)–(20) 产生的 raw LLR 向量。给定几何 \(\vartheta\) 时，接收机支持及算子由该工况确定。对实际码字分布 \(P_{\rm code}(b)\)，有
\[
\boxed{
\mathcal I_T(K)
=1-\frac1{2N}
E_{\vartheta,b,Z}\!
\sum_{j=1}^{2N}
\log_2\!\left[
1+\exp\left\{
-s_j\,\operatorname{clip}
\left([\Psi_{T,K}(\Sigma_{b,\vartheta}^{1/2}Z;p)]_j,-20,20\right)
\right\}\right],
\quad Z\sim CN(0,I_N).
}
\tag{34}
\]
每次取样只有一个 Z；它生成同一个 Y，贯穿所有 inner 更新。T=20 对应目标第一外轮。将式 (34) 中损失函数换成 \(\mathbf1\{\widehat{\mathcal I}_T\le u\}\)，即可定义帧信息指标的完整分布；不需要用均值替代尾部。

式 (34) 的输入都是生成模型、码、算子、功率和接收机规则。它没有 FER 拟合参数，也没有从 SP 结果测来的未知回归函数。但是，高维码字/高斯积分可能昂贵；**“无拟合的完整数学模型”不等于“廉价闭式宏观定律”**。

如需压缩，可对这个固定输入函数作有控制的逼近，而不是把每步噪声独立化。对任意 raw-LLR 近似 \(\widetilde\Psi\)，由 clip 的 1-Lipschitz 性及 logistic loss 的导数界，
\[
\boxed{
|\mathcal I_T-\widetilde{\mathcal I}_T|
\le\frac1{\ln2}
\sqrt{\frac1{2N}E\|\Psi_{T,K}-\widetilde\Psi_{T,K}\|^2}.
}
\tag{35}
\]
也可直接对裁剪后的 LLR 使用该界。其有界性保证 Gaussian Hermite 展开在 \(L^2\) 中存在并收敛；这是一个数学上可控的逼近途径，不保证所需阶数或成本适合工程使用。

### 7. 自相关修正的统计来源：边缘似然的精确梯度

这一节是参考统计模型，不声称其梯度下降等于当前 damped AMP。假设接收机模型 \(Y=B(x)h+w\)、\(h\sim CN(0,C)\)，C、\(A_\alpha\)、n₀ 不随候选 x 自适应改变；对固定候选 x 积掉 h：
\[
S(x)=n_0I+B(x)CB(x)^H,\qquad
\ell(x)=\log\det S(x)+Y^HS(x)^{-1}Y.
\tag{36}
\]
其条件增益均值、协方差为
\[
\bar h=CB^HS^{-1}Y,\qquad
C_{\rm post}=C-CB^HS^{-1}BC.
\tag{37}
\]
定义
\[
\mathcal V(C_{\rm post})
=\sum_{\alpha,\beta}
(C_{\rm post})_{\alpha\beta}A_\beta^HA_\alpha
=E[(\mathcal H(h)-\mathcal H(\bar h))^H
(\mathcal H(h)-\mathcal H(\bar h))\mid Y,x].
\tag{38}
\]
有精确 Wirtinger 梯度
\[
\boxed{
\nabla_{x^*}\ell(x)=\frac1{n_0}
\left[
\mathcal V(C_{\rm post})x
-\mathcal H(\bar h)^H(Y-\mathcal H(\bar h)x)
\right].
}
\tag{39}
\]
证明：\(\partial S/\partial x_i^*=BCM_i^H\)。对式 (36) 求导得到
\[
\frac{\partial\ell}{\partial x_i^*}
=\operatorname{tr}(M_i^HS^{-1}BC)
-(M_i\bar h)^HS^{-1}Y.
\]
再用 \(S^{-1}BC=BC_{\rm post}/n_0\) 与 \(S^{-1}Y=(Y-B\bar h)/n_0\)，即得式 (39)。

这说明“用软符号帮助估计信道，再用该信道检测同一符号”必须同时处理拟合项与信道不确定性项。后一项是矩阵 \(\mathcal V(C_{\rm post})\)，不是由一个 CE MSE 自动决定。

源码式 (17) 已存在形似 \(-u_tV_t\bar x_t\) 的修正，式 (14) 也有历史残差修正。因而不能未经检查就说“当前算法完全没有自相关修正”。需要回答的是：其标量报告方差、算子各向同性近似及历史修正，在当前结构中是否足以近似正确响应。本文没有把这一待检验问题提前宣布为已知失败根因。

## Remarks and Interpretation

1. **K 首先控制回归吸收与增益更新，而非直接决定信息量。** 式 (9)、(20)、(25) 给出三个明确入口；实际 Gram 与物理信道统计仍然必需。
2. **真实 MSE、报告方差与信息量是不同对象。** 式 (7) 的交叉项、式 (27) 的冷启动暂态和式 (2) 的校准损失，分别说明为什么一个 MSE 标量不能自动闭合本循环。
3. **第一 inner 可以解析，20 次 inner 必须保留历史。** 本文给出首次更新分布及整轮的精确动力学/概率模型；不把首次更新公式冒充 T=20 的结果。
4. **归一化可严格核对。** 同时令 \(Y,p,d\) 除以 \(g=\sqrt{2(1-\rho)}\)、\(P_p,P_d,n_0\) 除以 \(g^2\)，有 \(W_p'=gW_p,Q_p'=Q_p,h_t'=h_t,z_t'=gz_t,c'=c/g\)，故 LLR 不变（比较两种单位时要求相关 precision floor 都未触发）。源码内部的 pd=.5 与物理总功率 1 因此相容。

## Boundaries and Non-Claims

- 没有宣称已得到真实 AFDM 结构下的单变量、两变量或无历史的严格 state evolution。
- 没有声称 \(\mathcal I_{20}(K)\) 在任意信道族中严格单调，也没有推出折叠位置、两个稳定态或 FER 断崖。
- 条件分布式 (29) 依赖所述 proper Gaussian 射线增益；其他生成器应换掉该分布，算法恒等式本身不变。
- 不能拿式 (39) 的条件后验、式 (5) 的 pilot-only LMMSE 和源码 Vₜ 当同一个对象。
- 20 步高维积分虽定义完整，却未被本轮算成实际 C1 信息曲线；小矩阵恒等式核验不是性能验证。
- 暂态相位翻转不等于错误实现，也不意味着已经找到改善接收机的方法。

## Open Risks

唯一关键的压缩问题是：能否从式 (34) 得到成本足够低、误差可检查的宏观近似。若采用 Gaussian/cavity/低阶矩压缩，应说明被丢掉的交叉项与历史响应，并检查式 (35) 对目标信息指标是否有足够控制。本轮先保留精确基准，不用“自相关系数”代替尚未推导的项。

## Verification and Provenance

已完成以下小规模确定性检查；没有运行 Monte Carlo、LDPC FER 或服务器新实验：

| 检查 | 范围 | 结果 |
| --- | --- | --- |
| 式 (25) 与实际 scalar_joint_cols 首步 | N=32，K=8/16/24，实际 DPSS/CPP/DAFT kernel | LLR 最大绝对差 ≤1.12×10⁻¹⁵ |
| 式 (27) 与实际首步 gain | 同上 | 最大绝对差 ≤5.1×10⁻¹⁷ |
| 式 (12)–(20) 自然参数递推与原 kernel | 每个 K 检查 T=1/2/4/20，共 12 组 | LLR 最大绝对差 <3.0×10⁻¹⁵，gain <1.5×10⁻¹⁶ |
| 物理单位与 pd=.5 单位等价 | 同上，T=20 | LLR 最大绝对差 <3.6×10⁻¹⁵ |
| 式 (39) 的复梯度 | N=8，K=3，非对角 Hermitian C，16 个实方向，Cholesky logdet 中心差分 | 最大绝对差 1.16×10⁻⁹ |

前四项用现有 Python 3.12、NumPy/SciPy、单线程运行，输入为确定性合成数组。没有给这些数组赋予“真实 C1 验证帧”的含义。早先另一次 gradient 检查的 slogdet 实现发出数值警告；最终采用正定 Cholesky logdet、显式有限性检查重新核验，上表仅报告后者。

辅助数学核查确认首步时序、LLR 系数、ridge normal equation、相位翻转条件、式 (30)–(33) 的复高斯因子/秩界及式 (39) 的协方差索引。保留 source 中的 floor 与裁剪位置，没有悄悄替换接收机。

源码 SHA256：

- dpss_rx.py：800aa51a8f81dfd1aca6eb5ab5fa81ac1bff79716875187b8f89d8a5994595af。
- tapchannel.py：bcf3597782da42d94ff37f09010b45e5effe79a231493489ccbc829c6a3414bc。
- frozen messages.py：9b19937c90a6e2b15f30d4e326320a38cd2635f9c0c5b14814406991da25ec95。
- native twofft.py：c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0。

主要源码位置：experiments/headroom_ladder_20261008/dpss_rx.py:106–181、209–236、298–349；driver_c1.py:175–217；arms.py:124–131；experiments/sp_afdm_frozen_20260920/src/messages.py:7–23；experiments/sp_afdm_native_joint_20260921/src/native_twofft.py:21–27。

方法背景参考：[Parker–Schniter–Cevher, Bilinear Generalized Approximate Message Passing](https://arxiv.org/html/1310.2632)。它解释了 scalar-variance AMP 与 damping 的谱系；本文不把经典 Onsager 思想据为新发现，也未用其随机矩阵假设替代实际 AFDM 算子。
