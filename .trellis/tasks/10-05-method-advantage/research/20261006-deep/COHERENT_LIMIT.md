# Research: 单相干块的真实 prior 混合局部极限

- Query: 在实际 G0/P2/N4、未知 QPSK、同一信道内 T 个符号下，δ=h/√T 是否具有 prior 平均的非退化局部极限？gain 比值的重尾如何影响换序、功效与旧 q log 理论？
- Scope: internal；解析研究，只使用现有冻结物理构造和实际 PDP prior。
- Date: 2026-10-06
- Status: 数学命题及证明稿；待独立审阅，未运行数值、随机采样或 SSH。
- Active task: `.trellis/tasks/10-05-method-advantage`；本轮 authority 见 `ROUND.md` 与 `.mission/20261006_12-39-13-afdm-deep-principles/PLAN.md`。
- Ownership: 只写本文件；旧研究、旧 CSV、生产代码与他人文件均未改动。

## Findings

候选混合极限成立，而且可以得到 prior 平均意义下完整的尺度区分：δ√T→0 时连揭示真实符号及原始 gain 的 oracle 都无法区分；δ=h/√T、固定 h>0 时 blind C2 有严格介于 size 和 1 的极限功效；δ√T→∞ 且 δ→0 时该功效趋 1。这是当前实际 prior、固定 nuisance 的检测边界，不是任意 gain 的 uniform 保证、完整 likelihood LAN 或分离度估计率。

先 T→∞ 后，C2 的局部极限是一个正态随机平移：Z+hζv，其中 Z 与 ζ 独立，ζ 的实密度是有限个缩放 t₂ 密度的真实 PDP 混合。ζ 有有限一阶绝对矩，却无二阶矩。对有界检验功效使用支配收敛合法；对二阶矩交换极限不合法。

取 χ²₂ 的右尾 α 阈值 cα=−2 log α，则该极限功效 A(h) 满足

\[
A(h)-\alpha={\alpha c_\alpha\Gamma\gamma\over4}
h^2\log(1/h)+O(h^2),\qquad h\downarrow0,
\]

其中 Γ 保留实际 PDP，γ=vᵀΣ0⁻¹v>0。这证明小 h 的对数增益，同时解释为何固定 T 的 q log 密度展开不可直接代入 T→∞。

## Target / Invariant Object / Assumptions

目标是 **接收数据统计量的 prior 混合分布与功效**，不是以 Eζ² 替代条件信息。证明链为：实际 prior 的 Gaussian 回归 → 精确比值重尾 → 条件三角阵 CLT → 有界函数混合换序 → prior 检测尺度 → 小 h 尾积分。

固定 N=4、G0、两径共同 rounded delay=0，物理 Doppler 为 μ−δ、μ+δ。μ 位于当前三 atom 支撑及一个实际 PDP 离散分支的内部；τ>0、噪声方差 s>0 固定。可在所选平滑分支内部的紧集、正的 τ/s 紧集上取物理及矩包络，但本文件只声称固定 nuisance 处的极限。

沿用上轮真实 Gram 归一化，不替换为 unit-sphere gain 或未归一化 Gaussian 工作 prior：

\[
B_\delta=[w(\mu-\delta),w(\mu+\delta)],\quad
R_\delta=B_\delta^HB_\delta/N,\quad
H_\delta(g)=\sqrt{\tau N}{B_\delta g\over\|B_\delta g\|}.
\tag{1}
\]

每块先抽一次实际 PDP D 和 raw g，然后 T 个符号共享 Hδ(g)：

\[
g_-\mid D\sim\mathcal{CN}(0,d_1),\quad
g_+\mid D\sim\mathcal{CN}(0,d_2),\quad g_-\perp g_+,
\]

\[
Y_t=H_\delta(g)\odot x_t+\epsilon_t,\quad
x_t=A^HX_t,\quad \epsilon_t\sim\mathcal{CN}(0,sI_N).
\tag{2}
\]

Xt 的坐标独立均匀 QPSK，t 间独立；A 是冻结等模酉 DAFT。原生成器如果先按 raw gain 能量除一个公共正数，该数在 (1) 及下述 gain 比值中都消去，因此这里的 Gaussian 表示与实际径向归一化相容。

定义

\[
a=g_-+g_+,\quad z={g_+-g_-\over g_++g_-},\quad \zeta=\operatorname{Im}z,
\qquad d(Y)=\begin{pmatrix}|Y_0|^2-|Y_1|^2\\|Y_2|^2-|Y_3|^2\end{pmatrix}.
\tag{3}
\]

a=0 的事件在每个正 D 下概率为零。对于每个固定 a≠0，上轮实际三 atom 推导已给出

\[
\Delta_\delta(g):=E[d(Y)\mid g,D]
=\delta\zeta v+O_g(\delta^2),
\tag{4}
\]

\[
v={2\pi\tau(1+\xi^2)\over1+2\xi^2+5\xi^4}
\begin{pmatrix}1+3\xi^2\\-(1-\xi^2)\end{pmatrix},\qquad
\xi=\tan(\pi\mu/4).
\tag{5}
\]

这里 v 与上轮 k 相同，不是新的拟合系数。O_g 不对 a→0 统一。本文件用 (4) 的点态结论，随后只对有界测试函数换序，绝不先对该展开平方积分。

## 命题 1：真实 gain 比值的虚部是有限缩放 t₂ 混合

### 1.1 固定 PDP 的精确分布

给定 D，令 S=d1+d2，ρD=(d2−d1)/S，ℓD=2√(d1d2)/S∈(0,1]。令 braw=g+−g−（不与物理导数 b 混淆），则

\[
E|a|^2=E|b_{\rm raw}|^2=S,\qquad
E[b_{\rm raw}\bar a]=d_2-d_1.
\]

联合 proper complex Gaussian 回归给出

\[
b_{\rm raw}=\rho_D a+e,\qquad
e\perp a,\qquad e\sim\mathcal{CN}(0,4d_1d_2/S).
\]

故可以取独立 Z0,Z1∼CN(0,1)，使

\[
\boxed{z\overset d=\rho_D+\ell_D W,\qquad W=Z_1/Z_0.}
\tag{6}
\]

ρD 是实数，只影响 Re z，不影响 ζ。复变量变换 (Z0,Z1)↦(Z0,W) 的实 Jacobian 是 |Z0|²，因而

\[
f_W(w)={1\over\pi^2}\int_{\mathbb C}|u|^2
e^{-(1+|w|^2)|u|^2}\,d^2u
={1\over\pi(1+|w|^2)^2}.
\]

对 Re W 积分，用 ∫R(a+x²)⁻²dx=π/(2a^{3/2}) 得

\[
\boxed{f_{\zeta\mid D}(u)
={\ell_D^2\over2(\ell_D^2+u^2)^{3/2}}.}
\tag{7}
\]

因此 ζ/ℓD 与标准 t₂/√2 同分布。它不是实 Gaussian 比值产生的 t₁；“复 Cauchy”一词不能用来误判其一阶矩。

可直接积分得到

\[
P(|\zeta|>L\mid D)=1-{L\over\sqrt{L^2+\ell_D^2}}
\sim{\ell_D^2\over2L^2},\quad
E[\zeta\mid D]=0,\quad E[|\zeta|\mid D]=\ell_D,
\tag{8}
\]

\[
E[\zeta^2\mathbf1_{|\zeta|\le L}\mid D]
=\ell_D^2\left[\operatorname{asinh}(L/\ell_D)
-{L\over\sqrt{L^2+\ell_D^2}}\right]
=\ell_D^2\log L+O_D(1).
\tag{9}
\]

特别地 E[ζ²|D]=∞。

### 1.2 实际 PDP 混合，不丢标签、不改权重

对 μ=.27,.31,.35 的当前 L=70 分支，取 a0=e^{−5/32}、dj=10^{−j/40}，j=1,…,69。实际 prior 同时保留 D=(1,dj) 和 D=(dj,1)，各自未归一质量

\[
m_j={1\over2}(1-a_0)a_0^{j-1}(1-a_0^{70-j}),\qquad
Z=2\sum_{j=1}^{69}m_j.
\tag{10}
\]

这是 `pdp_distribution` 的原始条件质量，并非 equal PDP。其他固定 L 内点可将 70 改成相应 L。局部 δ 足够小时 L1=L2=L，所有上述质量与 δ 无关，所以可在所有足够大的 T 上耦合同一个 D,g。

由于交换 D 不改变 ℓD，ζ 的边缘密度可将两标签合并为权重 ωj=2mj/Z：

\[
f_\zeta(u)=\sum_j\omega_j
{\ell_j^2\over2(\ell_j^2+u^2)^{3/2}},\qquad
\ell_j={2\sqrt{d_j}\over1+d_j},\qquad
\Gamma:=\sum_j\omega_j\ell_j^2
=E_D{4d_1d_2\over(d_1+d_2)^2}>0.
\tag{11}
\]

于是 P(|ζ|>L)∼Γ/(2L²)，截断二阶矩为 Γ log L+O(1)。有限正 PDP 支撑使这里的余项常数可统一。交换标签前 z 的实移位 ρD 不同；合并标签只用于 ζ 的边缘律，没有删除物理标签或把完整 z 的分布改成圆对称。

## 命题 2：δ=h/√T 的混合局部极限与 prior 检测边界

### 2.1 Null 协方差精确式及相位无关性

在碰撞，H0(g)=√(τN)e^{iθ}u0(μ)，θ=arg a，u0=w/‖w‖。当前分支 |H0,0|²=|H0,1|²=τPa，|H0,2|²=|H0,3|²=τPb，Pa+Pb=2。

对任意 θ，圆 Gaussian 旋转 ε′t=e^{−iθ}εt 保持全部噪声的联合律和独立性，且

\[
|Y_{t,n}|^2=|\sqrt{\tau N}u_{0,n}x_{t,n}+\epsilon'_{t,n}|^2.
\]

因此整个 d 序列的 null 条件分布不依赖 θ、D 或 raw gain 模长，Δ0=0。该证明也覆盖每符号不同 θt，故与上轮共享 null 库的结论一致。

可进一步不经数值枚举得到 Σ0。独立 proper QPSK 满足 E|X|²=1、E|X|⁴=1；等模酉 DAFT 给出

\[
E[|x_i|^2|x_j|^2]=1+\mathbf1_{i=j}-1/N,
\quad \operatorname{Cov}(|x_i|^2,|x_j|^2)=\mathbf1_{i=j}-1/N.
\tag{12}
\]

证明：独立 proper 输入四阶矩的两项配对分别给 1 与 |(AᴴA)ij|²；QPSK 四阶累积量 1−2=−1 再给 −Σk|Aki|²|Akj|²=−1/N。

令 Pn=|Hn|²。条件 Gaussian 功率矩给出

\[
\operatorname{Cov}(|Y_i|^2,|Y_j|^2\mid H)
=P_iP_j(\mathbf1_{i=j}-1/N)
+\mathbf1_{i=j}(s^2+2sP_i).
\tag{13}
\]

将 null 的 P0=P1=τPa、P2=P3=τPb 代入配对差，交叉协方差严格抵消：

\[
\boxed{\Sigma_0=\operatorname{Cov}(d(Y)\mid H_0)
=2\operatorname{diag}((\tau P_a+s)^2,(\tau P_b+s)^2)\succ0.}
\tag{14}
\]

即使不使用闭式 (14)，正噪声也给所有 H 的 ΣH≽2s²I：给定 x,H，两个功率差涉及互不重叠的噪声坐标，每个功率的条件方差至少 s²。归一化的 ‖H‖²=τN、有限 QPSK 和 Gaussian 噪声使 d 的任意固定阶矩在所有 raw g、δ 上有统一上界。

### 2.2 条件三角阵 CLT 与经验协方差

固定 h≥0，取 δT=h/√T，并在不同 T 上耦合同一个 D,g。对每个 a≠0，物理曲线光滑且归一化分母在 δ=0 非零，因此

\[
H_{\delta_T}(g)\to H_0(g),\qquad
\sqrt T\Delta_{\delta_T}(g)=h\zeta v+O_g(h^2/\sqrt T)\to h\zeta v.
\tag{15}
\]

每个 T 内的 d(Yt) 条件于该 g,D 独立同分布。其协方差 ΣHδT 由 (13) 连续趋于 Σ0；前述统一三阶矩保证任意固定实向量 ℓ 的 Lyapunov 比为 O(T^{-1/2})，且投影方差下界由 2s²‖ℓ‖² 保证。Cramér–Wold 因此给出

\[
\sqrt T(\bar d_T-\Delta_{\delta_T}(g))\mid g,D
\Rightarrow \mathcal N(0,\Sigma_0).
\tag{16}
\]

用分母 T−1 的经验协方差 Σ̂T，统一四阶矩给各二阶样本均值的方差 O(1/T)，从而条件于同一 g,D，Σ̂T−ΣHδT→0 于概率，因此 Σ̂T→Σ0。s>0 使 d 的分布在 R² 有密度，T≥3 时样本协方差几乎必然非奇异；理论中无需 ridge 或静默伪逆。

### 2.3 有界测试函数允许混合换序

对任意有界连续 f，(15)–(16) 与 Slutsky 给出每个 a≠0 下的条件极限。条件期望始终由 ‖f‖∞ 支配；由于 P(a=0)=0、PDP 权重在固定分支最终恒定，可以对真实 D,g 用支配收敛。由此得到

\[
\boxed{\sqrt T\bar d_T\Rightarrow Z+h\zeta v,
\qquad \widehat\Sigma_T\to\Sigma_0\ \text{于概率},}
\tag{17}
\]

其中 Z∼N(0,Σ0) 可取与 (D,g)、因而与 ζ 独立。更精确地，对任意有界潜变量函数 ψ(D,g)，同样的条件期望论证给 ψ 加权收敛；即 (17) 是相对于这些潜变量的稳定混合收敛。随机性体现在均值，而不是把无限 Eζ² 当作 Gaussian 协方差。

定义完全由观测构造的上轮 C2 统计

\[
Q_T=T\bar d_T^T\widehat\Sigma_T^{-1}\bar d_T,
\qquad \gamma=v^T\Sigma_0^{-1}v>0.
\]

正定矩阵处的连续映射给出

\[
\boxed{Q_T\Rightarrow Q_h,\qquad
Q_h\mid\zeta\sim\chi^2_2(h^2\gamma\zeta^2).}
\tag{18}
\]

各条件非中心 χ² 都无原子，其混合在任意有限阈值也无原子，故 (18) 同时推出固定阈值的拒绝概率收敛；不是只证明了均值或特征函数而跳过检验事件。

### 2.4 Prior 平均的尺度区分

令 0<α<1、cα=−2 log α，Ψ(λ)=P{χ²₂(λ)>cα}。则

\[
P_{\delta_T}\{Q_T>c_\alpha\}\longrightarrow
A(h):=E_\zeta\Psi(h^2\gamma\zeta^2).
\tag{19}
\]

Ψ(0)=α，Ψ 对 λ 严格增加，任意有限 λ 下 Ψ(λ)<1，而 |ζ|>0 且有限几乎必然。因此 **每个固定 h>0 都有 α<A(h)<1**。此外 A(h)→α（h↓0）、A(h)→1（h→∞），均可由有界收敛证明。

更一般，若 δT→0 且 δT√T→∞，对每个固定 ζ≠0 的 gain，(4) 的相对余项趋零、Σ̂T→Σ0，故 QT→∞ 于条件概率。条件拒绝概率有界，实际 prior 下 ζ=0 概率零，DCT 给出 prior 平均功效趋 1。

若 δT√T→0，可证明所有检验的 prior 平均无区分，而非只证明 C2 无功效。向 oracle 同时揭示 (D,g) 和全部 Xt；它比真实 blind 实验更强。实际 latent law 在固定分支上相同，给定 g,X 的 Gaussian KL 经过 X 平均为

\[
D(P_{\delta_T,T}^{X\mid g,D}\|P_{0,T}^{X\mid g,D})
={T\over s}\|H_{\delta_T}(g)-H_0(g)\|^2\to0
\tag{20}
\]

对每个 a≠0 成立。Pinsker 给条件 TV→0；TV≤1 允许对 g,D 再用 DCT。共同 latent law 下，揭示 latent 的联合 TV 等于条件 TV 的平均，因此 oracle 联合 TV→0，丢弃 latent/X 后的 blind TV 也趋零。

这里比较同一固定 nuisance 下的实际 null/alternative prior 实验；未知 nuisance 不可能让更强 oracle 下已不可能的区分变得可能。结合 (19)，T^{-1/2} 是此 prior 家族的非退化检测尺度。未声称 full likelihood 的局部实验与 (17) 等价，未证明 C2 的最优功效，也未提供 uniform over gains 或全 nuisance 的 minimax 定理。

## 命题 3：极限功效的小 h 展开具有临界对数项

### 3.1 非中心 χ² 的零点导数

Poisson 混合恒等式为

\[
\Psi(\lambda)=e^{-\lambda/2}\sum_{j=0}^\infty
{(\lambda/2)^j\over j!}P\{\chi^2_{2+2j}>c_\alpha\}.
\]

因为 P{χ²₂>c}=e^{−c/2}=α，而 P{χ²₄>c}=α(1+c/2)，

\[
\Psi(\lambda)-\alpha=K_\alpha\lambda+O(\lambda^2),
\qquad K_\alpha=\Psi'(0)={\alpha c_\alpha\over4}>0.
\tag{21}
\]

该余项在 0≤λ≤1 上由有界二阶导数统一控制；全局则 0≤Ψ−α≤1−α。

### 3.2 截断积分证明，不能代入 Eζ²

置 b=h√γ（此 b 只用于本小节），L=1/b。对 |ζ|≤L 应用 (21)，尾部用有界性：

\[
A(h)-\alpha
=K_\alpha b^2 E[\zeta^2\mathbf1_{|\zeta|\le1/b}]
+O\!\left(b^4E[\zeta^4\mathbf1_{|\zeta|\le1/b}]
+P\{|\zeta|>1/b\}\right).
\tag{22}
\]

对每个 D，(7) 直接给

\[
E[\zeta^4\mathbf1_{|\zeta|\le L}\mid D]
=\ell_D^2\int_0^L{u^4\over(\ell_D^2+u^2)^{3/2}}du
\le{\ell_D^2L^2\over2},
\]

且 (8) 给 P{|ζ|>L|D}≤ℓD²/(2L²)。因此 (22) 的余项 O(b²)，而 (9)、(11) 的截断二阶矩为 Γ log(1/b)+O(1)。有限 D 混合可直接求和，最终

\[
\boxed{A(h)-\alpha
={\alpha c_\alpha\Gamma\gamma\over4}
h^2\log(1/h)+O(h^2).}
\tag{23}
\]

等价地，h²log(1/h²) 的系数为 αcαΓγ/8；两个写法差一个 2，不能混用。本结论先取 T→∞、固定 h 得到 A(h)，然后 h↓0。没有交换这两重极限。

若 ζ 有有限二阶矩，同样的有界性可给通常的 h² 系数 KαγEζ²；本实际 prior 恰处于二阶矩临界发散，才出现 h²log(1/h)。该机制是正则变化与截断矩的标准联系，不是一般 Gaussian 小信号公式。

## a→0 稀有事件、旧 q log 与不可用的二阶矩

### 4.1 为什么它们不破坏有界功效极限

给定 D，a∼CN(0,S)，P{|a|≤ε}=1−e^{−ε²/S}=O(ε²)。更适合尺度比较的是 (6) 的 W：

\[
P(|W|>L)={1\over1+L^2}.
\tag{24}
\]

δ|z| 不是小量的区域在当前有限正 PDP 支撑下具有 O(δ²) 概率；δ=h/√T 时为 O(1/T)。证明是 |ρD|≤1、ℓD≤1，通过 |W| 的精确尾界控制。它可使 Taylor 的 g 相关常数很大，但对任何有界拒绝概率，零测集外的点态收敛加 DCT 已足够；无需把非一致余项强行放进 L²。

一个明确的非一致序列是 g−=1、g+=−1+i/√T，此时 a=i/√T、z=1+2i√T，δ=h/√T 不再使 δz 趋零。归一化信道可能偏离 null O(1)，不能套用固定 g 的局部展开。该序列不是一组固定 gain；它说明必须保留“非 uniform over gains”的边界，而不反驳实际 prior 下的有界混合极限。

### 4.2 二阶矩与旧 q log 精确相容

上轮已从真实谱小模态律证明，令 q=δ²、r=q log(1/q)，

\[
E_g\|\Delta_\delta(g)\|^2
=C r+O(q),\qquad C={\Gamma\over2}\|v\|^2.
\tag{25}
\]

此式只涉及一个 H，不含 T，故可在本节直接代入 δ=h/√T。条件方差分解给

\[
E\|\sqrt T\bar d_T\|^2
=T E\|\Delta_{\delta_T}\|^2+E\operatorname{tr}\Sigma_{H_{\delta_T}}
=C h^2\log(T/h^2)+O_h(1).
\tag{26}
\]

最后一项有界且趋 trΣ0，因为 ΣH 在归一化 H 集上连续有界。固定 h>0 时 (26) 随 log T 发散；(17) 的极限 Z+hζv 同样具有无穷二阶矩。因此弱收敛与旧 q log 结果相容，二阶矩一致可积性却不成立。

固定 T 的块密度 r 展开具有随 T 增长的信息常数。若机械代入 δ=h/√T，就会把 T r=h²log(T/h²) 当作越来越强的局部信号，甚至误推固定 h 的功效趋 1。但 (19) 严格给 A(h)<1。这是固定 T 余项不能对 T 增长统一的明确反证，不是两项理论冲突。

### 4.3 局部混合极限甚至不是有限 KL 的 Gaussian shift

对任意 h>0，E Qh=2+h²γEζ²=∞；null Q0∼χ²₂ 具有 E exp(tQ0)<∞（0<t<1/2）。KL 变分不等式用于有界函数 fn(q)=t min(q,n)，给

\[
D(\mathcal L(Q_h)\|\mathcal L(Q_0))
\ge t E[\min(Q_h,n)]-\log E[e^{tQ_0}].
\]

令 n→∞ 得该方向 KL=∞。这并不表示某个固定阈值完美区分：A(h) 仍严格小于 1。罕见极大 gain 比值支配 KL/二阶矩，典型拒绝概率却是有界量。此结果足以禁止把 (17)–(18) 包装成普通有限信息 Gaussian/LAN 实验；本文件不据此推断 Hellinger 的最优尺度或完整 likelihood 的局部几何。

## B 个块：哪些结论能延伸，哪些不能

固定有限 B，每块各抽独立的实际 D,g，块内 T 符号共享信道。用相同有界函数论证对有限乘积换序，有

\[
(\sqrt T\bar d_{T,b})_{b=1}^B
\Rightarrow (Z_b+h\zeta_bv)_{b=1}^B,
\]

其中各块独立。ΣbQT,b 条件于 ζ1,…,ζB 的极限为

\[
\chi^2_{2B}\!\left(h^2\gamma\sum_{b=1}^B\zeta_b^2\right).
\tag{27}
\]

固定 B 的 null 阈值应使用 χ²₂B；它仍给实际 prior 平均的非退化 root-T 功效。不能把 ∑ζb² 替换为 B Eζ²。

若 B=BT→∞，单块的点态条件 CLT+DCT 不自动给完整 BT 块系统的近似。一个直观且精确的界是：每块事件 {|W|>√T} 的概率 1/(1+T)，至少一个块落入该区域的概率

\[
1-\left({T\over T+1}\right)^{B_T}
\longrightarrow1-e^{-\beta}\quad\text{若 }B_T/T\to\beta.
\tag{28}
\]

因此单块可以忽略的非一致区域，在块数与 T 同阶时不再可整体忽略；(28) 是换序风险提示，不是证明所有该区域都导致实际检验失败。要把一块的极限用到增长 B，需要足够强的定量近似误差及其累积控制，本文件未给出。

若明确按“先 T→∞ 得每块极限，再 B→∞”的顺序，固定 h>0 下每块有 A(h)>α，独立有界拒绝指示的平均可一致区分；这是普通大数律。它不能替代有限 T、BT 联合增长下的最优相图或 h 随 B 缩小的速率。

## 研究直觉、经典联系与可证伪预测

1. **先选不会被边缘化消掉的对象。** 单个符号的 C2 期望为零，但一个固定信道块的条件均值是 δζv。块内先平均保留这一次 ζ，块间或逐符号先平均则消掉其符号；这是随机效应和相干观测的区别。
2. **用有界量而非发散矩判断检测。** ζ 的二阶矩、局部极限的 forward KL 都发散，仍有 α<A(h)<1。功效是适合做 prior 换序的对象；把 Eζ² 代进非中心量会制造虚假的无限信息结论。
3. **复 Gaussian 比值的实投影恰落在临界 t₂。** 尾概率 ∝L⁻² 使截断二阶矩只有对数发散；这同一个机制在旧固定 T 模型产生 q log(1/q)，在新极限功效产生 h²log(1/h)。公共的数学结构不是两个模型拥有相同样本单位。
4. **两次取极限必须写明顺序。** 固定 T 后 δ→0 与固定 h、δ=h/√T 后 T→∞ 的剩余项不同；(19)、(26) 同时提供可核对的功效和二阶矩预测。仅看到矩随 log T 增大，不能声称功效趋 1。
5. **检测与参数估计继续分开。** v 与 ζ 只以 hζ 出现在该统计量的局部均值；本文件不提供从一个混合随机位移中唯一恢复 δ 的结论。

上述联系使用 Gaussian 回归、复变量 Jacobian、Lyapunov CLT、稳定混合收敛、支配收敛、Poisson 非中心 χ² 混合与正则变化截断矩等经典技术。本次没有外部文献检索，未主张该机制或公式在文献上首次出现。

## 最小 SSH 确定性验证建议（未执行）

1. 使用实际 `pdp_distribution` 读取所有正 D 及权重，只计算 ℓD、Γ，核对交换标签具有相同 ζ 律。不得替换 equal PDP，不重抽 gain。
2. 用 (12)–(14) 的 Gaussian/QPSK 精确矩，或 256 个合法 QPSK 的确定性枚举，核对 Σ0 的两个对角元和零交叉元。复用冻结 N4 DAFT，无新随机观测。
3. 对 (19) 用有界的一维积分：由 (7) 的 CDF，ζ=ℓD u/√(1−u²)，u∼Unif(−1,1)。故

   A(h)=ΣDπD∫₀¹ Ψ(γh²ℓD²u²/(1−u²)) du。

   u→1 的被积函数极限为 1；可用固定节点求积加严格的尾区间长度界，不用对极大 gain 做随机抽样。记录节点数、加密差与尾界，遵守本轮总核评估上限。
4. 对若干预定小 h 核对 [A(h)−α]/[h²log(1/h)] 朝 αcαΓγ/4 的趋势；O(1/log(1/h)) 收敛本来很慢，有限网格不能反过来拟合系数或宣称严格证明。宜直接积分非负功效差并用 Poisson 表达处理小非中心量，避免两个接近概率相减。
5. 验证 null h=0 积分必须严格返回 α；正 h 给 α<A(h)<1 且单调。若出现大于 1、负功效差或把无穷 Eζ² 代入，这属于实现错误而非新科学结果。

## Files Found / Code Patterns / Related Specs

- `research/20261006-important/coherence/THEORY_CANDIDATES.md`：上轮实际三 atom 的闭式 C2 导数 (8)–(10)、Studentized 检测、严格 null phase 不变性、真实 q log 跨时矩 (19)；本文件复用这些已写证明，不重跑旧实验。
- `experiments/afdm_efficient_information/prior_likelihood.py:46`：实际 PDP 两标签、common-rounded-zero 条件质量；`:296` 附近 sample 每个 observation 重抽 gain，原代码本身不是相干块。
- `experiments/afdm_higher_order_information/prior.py:25`：G0 geometry、真实 clipping、正交整数 atom 与 Gram；`:106` 的 JVP 仅对正定分支，不能代替本文件碰撞点的解析点态推导。
- `experiments/afdm_shared_channel_20261004/production_prior.py:76`：按完整 Gram 二次型归一化；径向公共因子相消。
- `experiments/afdm_collision_resolution/DENSITY_THEORY.md:92`：原真实小模态谱律及 q log 来源；`:218` 的原边缘密度展开。
- `experiments/afdm_method_advantage/THEORY.md:248`：独立重生 C2 无均值信号的有限 δ 共轭对称证明。
- 已读并沿用 `.trellis/spec/backend/structured-inference.md` 的真实 prior、truth/observable、tiny 验证与全链收益边界；本轮没有加载无关生命周期文件或改动规范。
- 继续使用已读 `formula-derivation/SKILL.md` 的对象—假设—命题—边界结构。外部 references 本次未查证；上述经典技术名称不构成新颖性声明。

## Caveats / Not Found

- 固定实际正 PDP、固定平滑分支内点是必要范围。μT 以 T^{-1/2} 接近 PDP/floor 边界时，latent mixture 可能随 h 改变，本证明没有覆盖。
- a=0 或 Bδg=0 的零概率事件不能当正常归一化输入；a 接近零不影响有界 DCT，却阻止 raw-gain uniform 结论。
- 若人为把 gain 相位 prior 改为共线实增益，ζ=0 几乎必然，C2 的 root-T 混合功效退回 α。若某条路径方差为零，Γ=0，实际二径正性假设失败。都不能继续套用 (23)。
- s=0 的无噪声实验不属于 Gaussian KL 下界和本证明的边界；它可能对任意非零 δ 已呈支持分离。
- 未证明最优 test、完整 blind likelihood 的局部极限、full LAN、uniform/minimax 分辨率、δ 估计率、任意增长 B/T 相图、有限样本误差或生产接收机增益。
- 所有新公式尚待独立解析复核；本文件未运行任何数值或随机实验。确定性验证应由主会话按本轮 SSH 预算与冻结协议执行。
