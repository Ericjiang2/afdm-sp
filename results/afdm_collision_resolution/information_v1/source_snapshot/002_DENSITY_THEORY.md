# 实际归一化双径碰撞的密度与单侧局部参数

## 目标、状态与范围

本文件对应 DENSITY-01。目标是从实际归一化潜变量概率律推出密度展开，不能从协方差的非零对数项猜测密度阶数。状态：下列命题已给出证明，待本任务独立审查；本文件自身不构成正式采样 GO，也不提供数值误差证书。

对象固定为 G0、P=2、共同 rounded delay=0、N=4、独立均匀 DAFT 域 QPSK、正圆对称 Gaussian 噪声，保留真实条件 PDP 混合及两种标签分配。基点为 $\mu_*=0.27,0.35$，$\tau=1$，$s=\sigma^2=0.2,1$。证明也适用于满足下列假设的有限维分支；实际基点的假设在第 1 节逐项核实。

来源是冻结 `physical_cluster_weights` / `dirichlet_alpha`、`afdm_higher_order_information/prior.py`、`afdm_efficient_information/prior_likelihood.py` 及该目录 `PRIOR_THEORY.md` 第 7 节。这里推进到密度及局部实验，不修改上一轮结论或数据。

## 假设、记号与依赖关系

- A1：在碰撞附近固定物理 support、rounding、clipping、pruning 和条件 PDP 离散分支，单路径时间响应 $w(\mu)\in\mathbb C^N$ 光滑。
- A2：合法整数 atom 无 alias，故 $R_\delta=B_\delta^HB_\delta/N$，其中 $B_\delta=[w(\mu-\delta),w(\mu+\delta)]$；$w\ne0$ 且下述 $b\ne0$。
- A3：$D=\operatorname{diag}(D_1,D_2)$ 取有限个严格正值，概率 $\pi_D$ 在该分支内固定，且交换 $D_1,D_2$ 保持概率不变。
- A4：输入 $X$ 有有限支撑且与增益、PDP、噪声独立；$x=A^HX$，$A$ 是固定酉 DAFT；$\epsilon\sim\mathcal{CN}(0,sI_N)$，$\tau,s>0$。

定义

$$
a^2=\frac{\|w\|^2}{N},\qquad
b=w_\mu-w\frac{w^Hw_\mu}{\|w\|^2},\qquad
b_2=\frac{\|b\|^2}{N},\qquad
u_0=\frac{w}{\|w\|},\quad u_1=\frac{b}{\|b\|}.
$$

$b_2$ 是实标量，$b$ 是向量。令 $q=\delta^2$，$r=q\log(1/q)$，$r(0)=0$；仅用 $0\le q<e^{-1}$ 的单调分支。$p_\delta$ 是 Lebesgue 密度，$p_0>0$。固定基点的空间与范数是

$$
\mathcal H=L^2(\mathbb C^N,dy/p_0(y)),\qquad
\|f\|_{\mathcal H}^2=\int\frac{|f(y)|^2}{p_0(y)}dy.
$$

依赖图为：实际分支核实 → 原始概率的谱表示 → 小模态能量引理与 Gaussian 核引理 → 密度定理 → 单侧 DQM / Hellinger / KL → 已知 nuisance 的重复分辨尺度。`NUISANCE_THEORY.md` 再从密度定理推出联合局部实验与实际 $J_{\rm eff}>0$；本文件的条件性尺度结论不预先假定该正性。

## 1. 冻结实际分支满足假设

N=4 时 `system_for` 令 $k_{\max}=1$，`k_leak=2`。冻结实现先计算 $m=-2,\ldots,2$ 的 Dirichlet 系数并用其共同正范数归一化，然后施加 atom cap 和相对功率 $0.01$ 剪枝；截断后不重新做列归一化。对 $\nu\in(0.26,0.36)$，center=0，无物理 Doppler clipping，合法 atom 为 $-1,0,1$。未归一系数为

$$
\alpha_m(\nu)=e^{3\pi i(m+\nu)/4}
\frac{\sin[\pi(m+\nu)]}{4\sin[\pi(m+\nu)/4]}.
$$

在此区间，$m=0$ 的功率是整个五点窗口的最大值；这是因为 $|\sin[\pi(m+\nu)/4]|$ 在 $m=0$ 最小，而五个分子的绝对值相同。对 $m=\pm1$，

$$
\frac{|\alpha_m|^2}{|\alpha_0|^2}
=\frac{\sin^2(\pi\nu/4)}{\sin^2[\pi(m+\nu)/4]}
\ge \sin^2(0.26\pi/4)>0.04>0.01.
$$

因此恰保留三个 atom，且远离所有相应阈值；它们在 N=4 中互不 alias。

还可解析证明 $b\ne0$ 及 $w$ 逐项非零。设 $t=\pi\nu/4$、$c_m=\sin t/\sin(t+\pi m/4)$，则

$$
\alpha_m/\alpha_0=e^{-i\pi m/4}c_m,\qquad
c_{-1}<0,\quad c_0=1,\quad c_1>0.
$$

三个整数 atom 线性独立。若 $w_\mu$ 与 $w$ 成比例，所有系数比值的导数都必须为零；但对 $m=\pm1$，

$$
\frac{c'_m}{c_m}=\frac\pi4
\{\cot t-\cot(t+\pi m/4)\}\ne0.
$$

共同窗口归一化不改变比值，所以 $b\ne0$。进一步，去掉一个非零共同复因子后，

$$
w_n\ \propto\ c_{-1}e^{-i\psi_n}+1+c_1e^{i\psi_n},
\qquad \psi_n=\frac{\pi n}{2}-\frac\pi4.
$$

其虚部为 $(c_1-c_{-1})\sin\psi_n\ne0$，$n=0,1,2,3$，故 $w_n\ne0$。同时 $|w_0|^2=|w_1|^2$、$|w_2|^2=|w_3|^2$，这解释低阶功率矩可能缺少 nuisance 区分维度，但不是有效信息为零的证明。

真实条件 PDP 按冻结 `pdp_distribution` 给出。其最大 rounded-zero corrected index 是 67：因为 $T_s=1/8000$、resolution=$1/60$，$\operatorname{round}[(k-1)60/8000]=0$ 恰到 $k=67$，端点没有半整数 tie。两个限制为

$$
L_i=\left\lfloor67(1+\nu_i/6)\right\rfloor.
$$

分别在 $\mu_*=0.27,0.35$ 的 $|\mu-\mu_*|+|\delta|<10^{-3}$ 邻域，$L_1=L_2=70$ 恒定。令 $a_0=e^{-5/32}$、$d_j=10^{-j/40}$；对 $j=1,\ldots,69$，$D=(1,d_j)$ 和 $D=(d_j,1)$ 各自的未归一质量相同，均为

$$
\frac12(1-a_0)a_0^{j-1}(1-a_0^{70-j}).
$$

除以全部质量之和即为 $\pi_D$。这是有限、正、交换对称且局部常量的实际条件混合，不是 equal-PDP 替代。四个实际基点均满足 A1–A4。

## 2. 原始概率的谱表示与稀有小模态

给定 $D$，冻结归一化为

$$
h_D=\frac{D^{1/2}z}{\sqrt{z^HC_{\delta,D}z}},\qquad
C_{\delta,D}=D^{1/2}R_\delta D^{1/2},\qquad
z\sim\mathcal{CN}(0,I_2),
$$

观测为 $Y=\sqrt\tau\,(B_\delta h_D)\odot x+\epsilon$。分母为零的事件概率为零，包括 rank-one 碰撞。令 $\lambda_0>\lambda_1>0$ 为 $\delta>0$ 足够小时 $C_{\delta,D}$ 的两个本征值，$\rho_D=\lambda_1/\lambda_0$。对 $B_\delta D^{1/2}/\sqrt N$ 作奇异值分解；由于 $z$ 酉不变，其右旋转后的模平方 $U,V$ 独立服从 Exp(1)，相位独立均匀。因此有原始概率律的精确恒等式

$$
B_\delta h_D\ \overset d=\ \sqrt N\left[
\sqrt{1-T_D}\,e^{i\theta}u_{0,\delta,D}
+\sqrt{T_D}\,e^{i(\theta+\phi)}u_{1,\delta,D}\right],
\qquad T_D=\frac{\rho_D V}{U+\rho_D V},
$$

其中 $\theta,\phi$ 独立均匀并与 $T_D$ 独立。这一步旋转的是 isotropic $z$，没有把实际 PDP 角分布改成均匀球。

Taylor 展开 $w(\mu\pm\delta)=w\pm\delta w_\mu+O(\delta^2)$ 给出

$$
\det C_{\delta,D}=4D_1D_2a^2b_2\delta^2+O(\delta^3),
\qquad \lambda_0=(D_1+D_2)a^2+O(\delta),
$$

从而

$$
\rho_D=c_Dq+O(\delta^3),\qquad
c_D=\frac{4D_1D_2}{(D_1+D_2)^2}\frac{b_2}{a^2}>0.
\tag{2.1}
$$

该余项足够；不需要用更强的偶次 determinant 余项。大模态谱投影因其在零点有正谱隙而光滑。由 $w(\mu-\delta)$ 和差商 $[w(\mu+\delta)-w(\mu-\delta)]/(2\delta)$ 构成的二维空间也光滑延拓，且在零点为 $\operatorname{span}_{\mathbb C}\{w,b\}$。用二维空间投影减大模态投影，得到小模态投影的光滑延拓。于是可局部定相，使

$$
u_{0,\delta,D}\to u_0,\qquad u_{1,\delta,D}\to u_1,
$$

并具有有界的所需阶导数。相位选择不改变后续相位平均核。

**小模态引理。** 对 $0<\rho<1$，$T=\rho V/(U+\rho V)$ 的密度为

$$
f_\rho(t)=\frac{\rho}{[\rho+(1-\rho)t]^2},\quad 0<t<1.
$$

这是将 $V/U$ 的密度 $(1+z)^{-2}$ 经 $t=\rho z/(1+\rho z)$ 变换所得。因此

$$
ET=\frac{\rho(\rho-1-\log\rho)}{(1-\rho)^2}
=\rho\log(1/\rho)+O(\rho),\qquad
ET^2\le\frac\rho{(1-\rho)^2}=O(\rho).
\tag{2.2}
$$

第二个界来自逐点 $t^2f_\rho(t)\le\rho/(1-\rho)^2$。结合 (2.1)，

$$
ET_D=c_Dr+O(q),\qquad ET_D^2=O(q).
\tag{2.3}
$$

这里 $O(\delta^3\log(1/q))=o(q)$，$c_Dq\log(1/c_D)=O(q)$；有限正 PDP 支撑使所有常数可统一。

## 3. Gaussian 相位核：导数与加权余项

写 $\varphi_s(v)=(\pi s)^{-N}\exp(-\|v\|^2/s)$。在任一相应正交单位向量对 $u_0,u_1$ 下，定义

$$
m_j(x)=\sqrt{\tau N}\,u_j\odot x,\qquad
F(t,y)=E_{X,\theta,\phi}\,
\varphi_s\left(y-e^{i\theta}
[\sqrt{1-t}m_0+\sqrt t\,e^{i\phi}m_1]\right).
$$

在以下导数中，把 $e^{i\theta}$ 吸收到 $m_0,m_1$，令 $v=y-m_0$。则

$$
A(y):=\partial_tF(0,y)=E_{X,\theta}\varphi_s(v)
\left[\frac{|v^Hm_1|^2}{s^2}-\frac{\|m_1\|^2}{s}
-\frac{\operatorname{Re}(v^Hm_0)}s\right].
\tag{3.1}
$$

证明：均值位移为 $\sqrt t\,e^{i\phi}m_1-tm_0/2+O(t^2)$。在 Gaussian 指数展开中，relative-phase 平均消去 $\sqrt t$ 项；径向漂移贡献 $-\operatorname{Re}(v^Hm_0)/s$，平方均值项贡献 $-\|m_1\|^2/s$。一次指数扰动的平方除以二，再平均 $\phi$，贡献 $|v^Hm_1|^2/s^2$。因此没有额外 2 或 $1/2$。

为控制余项，所有 G0 响应均有范数 $\sqrt N$；QPSK 满足 $\|x\|_\infty\le\sqrt N$，故所有相位核均值有共同界 $M=N\sqrt\tau$。在一个紧参数邻域也可选统一 $M$。任意有限阶均值导数由形如

$$
G(y)=C(1+\|y\|)^k
\exp\{-[(\|y\|-M)_+]^2/s\}
\tag{3.2}
$$

的共同包络支配，适当增加有限 $k,C,M$ 即可。另一方面，所有基点均值范数不超过 $M$，所以

$$
p_0(y)\ge (\pi s)^{-N}\exp[-(\|y\|+M)^2/s].
\tag{3.3}
$$

于是 $G^2/p_0$ 在实维 $2N$ 空间可积：其尾指数为 $-\|y\|^2/s+O(\|y\|)$。

**核余项引理。** 对整个 $0\le t\le1$，

$$
|F(t,y)-F(0,y)-tA(y)|\le Ct^2G(y),
\quad
\|F(t)-F(0)-tA\|_{\mathcal H}\le Ct^2.
\tag{3.4}
$$

在 $0\le t\le1/2$，先把均值写成 $a(t)=\sqrt{1-t}m_0$ 加 $\sqrt t e^{i\phi}m_1$。对后者作到三阶的实变量 Taylor 展开；一、三阶相位平均为零，四阶余项由 $Ct^2G$ 支配。二阶相位平均为 $t$ 乘以 $a(t)$ 处的 Hessian；$a(t)=m_0-tm_0/2+O(t^2)$ 的光滑展开再给出 (3.1) 与 $O(t^2G)$。在 $1/2\le t\le1$，三个项 $F(t),F(0),A$ 各自受 $CG$ 控制，而 $t^2\ge1/4$，同一界成立。证明不假设 $\sqrt{1-t}$ 在 $t=1$ 可微。由 (3.2)–(3.3) 得 Hilbert 界。

该引理对 $u_{j,\delta,D}$ 统一成立。相应导数 $A_{\delta,D}$ 满足

$$
|A_{\delta,D}-A|\le C|\delta|G,
\qquad \|A_{\delta,D}-A\|_{\mathcal H}=O(|\delta|).
\tag{3.5}
$$

## 4. 密度定理与标签对称的必要作用

**定理 D1。** 在 A1–A4 下，

$$
p_\delta=p_0+r h+R_\delta,\qquad
h=\kappa A,\qquad
\kappa=E_D[c_D]
=E_D\!\left[\frac{4D_1D_2}{(D_1+D_2)^2}\right]
\frac{\|b\|^2}{\|w\|^2},
\tag{4.1}
$$

且

$$
|R_\delta(y)|\le CqG(y),\qquad
\|R_\delta\|_{\mathcal H}=O(q)=o(r).
\tag{4.2}
$$

证明：给定 $D$，第 2 节的原始概率恒等式和 (3.4) 给出

$$
p_{\delta,D}=F_{\delta,D}(0)+(ET_D)A_{\delta,D}+O_{\mathcal H}(ET_D^2),
$$

也有相同的点态包络余项。由 (2.3)、(3.5)，第二项为 $c_DrA+O_{\mathcal H}(q)$，因为 $|\delta|r=o(q)$。最后一项为 $O_{\mathcal H}(q)$。

剩下的大模态项必须用真实标签混合处理。将几何解析延拓到有符号 $\delta$ 仅用于本证明，则

$$
B_\delta D B_\delta^H=B_{-\delta}D^{\rm swap}B_{-\delta}^H.
$$

由大模态的唯一谱投影与全局相位平均，$F_{\delta,D}(0)=F_{-\delta,D^{\rm swap}}(0)$。因此 $\sum_D\pi_DF_{\delta,D}(0)$ 是光滑偶函数，且在零点等于 $p_0$，其差为 $O(qG)$。有限求和即得 (4.1)–(4.2)。

这一消线性步骤不可省略：在规范 $u_0^H\partial_\delta u_{0,\delta,D}|_0=0$ 下，

$$
\left.\partial_\delta u_{0,\delta,D}\right|_0
=\frac{D_2-D_1}{D_1+D_2}\frac b{\|w\|}.
$$

单个不等 PDP 条件模型通常存在 $O(\delta)$ 密度漂移。只保留一种标签时，本定理的 $r$ 首项一般不成立。

积分 (3.1) 时，在每个 $m_0,m_1$ 下 $v\sim\mathcal{CN}(0,sI)$，故 $E|v^Hm_1|^2=s\|m_1\|^2$ 且 $E\operatorname{Re}(v^Hm_0)=0$。所以 $\int h=0$。条件核的括号受 $C(1+\|y\|^2)$ 控制，对其作基点 posterior 平均可得

$$
s_r(y)=\frac{h(y)}{p_0(y)},\qquad E_0s_r=0,\qquad
|s_r(y)|\le C(1+\|y\|^2),\qquad
J=E_0s_r^2<\infty.
\tag{4.3}
$$

`collision_teacher.py` 使用的有限 QPSK / Bessel 相位消元即为此 $s_r$ 的观测表达；它不需要给定已实现的 latent gain/PDP。

## 5. 单侧 DQM、Hellinger、两向 KL

以下用 $p_r=p_{\delta(r)}$。由定理 D1，$u_r=(p_r-p_0)/p_0$ 满足 $u_r\ge-1$、$E_0u_r=0$、$u_r/r\to s_r$ 于 $L^2(P_0)$。

**定理 D2。** 该单侧参数族在 $r=0$ 具有 DQM：

$$
\left\|\sqrt{p_r}-\sqrt{p_0}-\frac r2s_r\sqrt{p_0}\right\|_2=o(r).
\tag{5.1}
$$

证明：$[\sqrt{1+u}-1-u/2]/u$ 在 $[-1,\infty)$ 有界且在 $u\to0$ 时趋零。$u_r/r$ 的 $L^2$ 收敛给出平方的一致可积性，$u_r\to0$ 于概率，故平方根非线性余项为 $o_{L^2(P_0)}(r)$。再代入 $u_r=rs_r+o_{L^2}(r)$ 即得结论；不需把概率模型延拓到负 $r$。

明确采用 $H^2(P,Q)=\int(\sqrt p-\sqrt q)^2=2(1-\operatorname{Aff}(P,Q))$。于是

$$
H^2(P_r,P_0)=\frac J4r^2+o(r^2),\qquad
\chi^2(P_r,P_0)=Jr^2+o(r^2).
\tag{5.2}
$$

正向 KL 也直接由此加权 $L^2$ 展开推出：$f(u)=(1+u)\log(1+u)-u$ 的 $f(u)/u^2$ 在 $[-1,\infty)$ 有界，在零点趋 $1/2$。利用 $E_0u_r=0$ 与一致可积性，

$$
D(P_r\|P_0)=\frac J2r^2+o(r^2).
\tag{5.3}
$$

反向 KL 需要额外支配，不能只凭加权 $L^2$。本 Gaussian 有界均值混合满足该要求：由 (3.2)–(4.2)，对固定 $k,C$ 有

$$
|u_r(y)|\le Cr(1+\|y\|)^k e^{C\|y\|},
\qquad
\left|\log\frac{p_r(y)}{p_0(y)}\right|\le C(1+\|y\|),
\tag{5.4}
$$

第二个界来自所有均值在同一球内、噪声方差相同的 Gaussian 上下界；两族尾概率均有统一 Gaussian 衰减。取球半径 $L_r=a\log(1/r)$，其中固定 $a>0$ 足够小。球内 (5.4) 使 $\sup|u_r|\to0$，故

$$
-\log(1+u_r)+u_r=\tfrac12u_r^2+o(u_r^2)
$$

一致成立。球外，$E_0|u_r|\mathbf1_{\{\|Y\|>L_r\}}$ 不超过 $P_r$ 与 $P_0$ 两个尾概率之和；结合 log 比界，积分为 $e^{-cL_r^2+O(L_r)}=o(r^m)$，任意固定 $m>0$。同样由 (5.4) 和 Gaussian 尾，球外 $E_0u_r^2=o(r^2)$。因此

$$
D(P_0\|P_r)=\frac J2r^2+o(r^2).
\tag{5.5}
$$

这些是局部精确概率律的渐近恒等式，不是有限 $\delta$ 的已认证数值界。

**坐标边界。** 因 $r=o(\delta)$，$\delta$ 坐标在零点具有零 DQM 导数；这不表示 $r$ 信息为零。若 $J>0$，则 $H(P_q,P_0)/q\sim(\sqrt J/2)\log(1/q)\to\infty$，所以不存在有限的 $q$-DQM 得分。密度值的余项本身不控制其导数，不能据此直接声称分离点的 $I_\delta\sim[r'(\delta)]^2J$。

## 6. 独立重复的分辨尺度

对相同固定 nuisance 的两个简单假设，$R$ 次独立重复的 affinity 精确相乘：

$$
H^2(P_r^{\otimes R},P_0^{\otimes R})
=2\left[1-\left(1-\frac{H^2(P_r,P_0)}2\right)^R\right].
\tag{6.1}
$$

若 $r=r_R\to0$ 且 $J>0$，则 $Rr_R^2\to0$ 时 total variation 趋零；$Rr_R^2\to\infty$ 时 affinity 趋零、total variation 趋一；若 $Rr_R^2\to c\in(0,\infty)$，则

$$
H^2(P_{r_R}^{\otimes R},P_0^{\otimes R})
\longrightarrow2(1-e^{-Jc/8}).
\tag{6.2}
$$

第一与第二个 TV 结论分别来自 $\operatorname{TV}\le H$ 与 $\operatorname{TV}\ge H^2/2$，采用本文件的 Hellinger 约定。

精确反函数是 Lambert $W$ 的负支：

$$
q(r)=-\frac r{W_{-1}(-r)},\qquad
\delta(r)=\sqrt{-\frac r{W_{-1}(-r)}}.
$$

因此对固定 $t>0$，$r_R=t/\sqrt R$ 对应

$$
\delta_R\sim\sqrt{2t}\,
R^{-1/4}(\log R)^{-1/2}.
\tag{6.3}
$$

这里 $\sqrt2$ 来自 $\log(1/q_R)\sim\tfrac12\log R$，不可略去。未知 nuisance 的局部有效常数和条件见 `NUISANCE_THEORY.md`；(6.1) 本身只比较指定的两个简单分布，不是对所有 nuisance 的全局 minimax 结论。

## 边界、未证项与验证说明

- 实际四个基点的 A1–A4 已用冻结构造解析核实。$J>0$ 由配套 nuisance 文件更强的实际 $J_{\rm eff}>0$ 命题推出，需连同其证明独立审查；非零矩 $K$ 不替代该步骤。
- 仅此有限条件 G0 分支；未推出 G1、完整八径、其他 clipping/PDP 分支、非 Gaussian 噪声或无限输入集合的同样结论。单 atom 平台 $b=0$ 仍属于已知完全零信息情形。
- 未证明有限 separation 得分的导数余项、有限样本最优功效、统一复合 minimax 界或具体 Fisher 数值下界；未主张数学机制在文献上首次出现。
- 本文件的验证为解析证明及冻结源码对照，不是运行仿真。教师微型资格由其独立测试记录负责；本文件没有新增科研观测或修改前轮产物。
