# 碰撞单侧局部实验、有效信息与实际正性

## 目标、状态与定义

本文件对应 NUISANCE-01，承接 `DENSITY_THEORY.md` 的实际原始概率密度展开。目标是区分原始信息与未知 nuisance 后保留的信息，并说明哪些证据足以证明后者为正。状态：证明已成文，待本任务独立审查；特别是第 3 节的分布法向二阶证明须与实际条件核实一并审查。本文件不授予正式采样 GO，不以数值投影残差代替总体结论。

沿用密度文件的 $N,w,b,u_0,u_1,q,r,s,\kappa,A,h=\kappa A$。nuisance 为

$$
\eta=(\mu,\log\tau,\log s),\qquad s=\sigma^2>0.
$$

碰撞基点 $\eta_0$ 的密度记 $p_0=p_{0,\eta_0}$；所有得分与内积均在该点定义。$h_{\eta_j}=\partial_{\eta_j}p_{0,\eta}|_{\eta_0}$、$s_{\eta_j}=h_{\eta_j}/p_0$，并令

$$
S=(s_r,s_\eta^T)^T,\qquad s_r=h/p_0,\qquad
I=E_0SS^T=
\begin{pmatrix}J&I_{r\eta}\\ I_{\eta r}&I_{\eta\eta}\end{pmatrix}.
$$

得分均为实函数，线性 span 和投影均在实 Hilbert 空间 $L^2(P_0)$ 中进行。假设为密度文件 A1–A4，联合邻域仍固定离散分支且 $\tau,s>0$。具体四个基点的解析核实在那里完成。下面另行列出有效正性所需的几何条件，不能以抽象假设冒充实际验证。

依赖图：D1 密度展开 + nuisance 光滑性 → 联合单侧 DQM → 单侧 LAN → 有效投影；D1 的导数算子 + 有限信号圆几何 → $J_{\rm eff}>0$。矩见证是独立充分路径，不作为几何证明的隐藏前提。

## 1. 联合 DQM 与合法单侧 LAN

### 1.1 联合密度展开

在碰撞，真实 PDP 归一化后的 G0 响应精确等于 $\sqrt N e^{i\theta}u_0$，$\theta$ 均匀，且不依赖 $D$。故

$$
p_{0,\eta}(y)=E_{X,\theta}\,
\varphi_s(y-e^{i\theta}m_0(X;\eta)),\qquad
m_0=\sqrt{\tau N}\,u_0(\mu)\odot x.
$$

这是有限输入、紧相位上的光滑 Gaussian 混合。$\mu$ 与 $\log\tau$ 通过均值光滑变化，$\log s$ 通过正噪声方差光滑变化。密度文件的谱间隙、有限正 PDP 支撑、相位 Taylor 余项及支配常数都可在足够小的 $\eta$ 邻域统一选择。

为把变化噪声的密度放入同一个 $\mathcal H=L^2(dy/p_0)$，选择 $s_{\max}<2s_0$。均值/噪声的有限阶导数具有多项式乘 $\exp[-(\|y\|-M)_+^2/s_{\max}]$ 包络，而 $p_0$ 的下界使用 $s_0$，故平方后除以 $p_0$ 的尾二次系数为 $-2/s_{\max}+1/s_0<0$。这给出所需的统一支配，不把变化噪声误当相同方差。

于是 $\eta\mapsto p_{0,\eta}$ 在 $\mathcal H$ 可微，$\eta\mapsto h_\eta^{(r)}$ 连续；结合统一 $O_{\mathcal H}(q)$ 余项，得到

$$
p_{r,\eta_0+v}=p_0+r h+v^Th_\eta
+o_{\mathcal H}(r+\|v\|),\qquad r\downarrow0,\ v\to0.
\tag{1.1}
$$

其中左侧 $r$ 通过同一个 $q\log(1/q)$ 反函数定义，$h_\eta^{(r)}$ 表示随基点变化的 $r$ 密度导数，不与向量 $h_\eta$ 混淆。密度导数积分为零，且各得分至多二次多项式增长，故 $E_0S=0$、$I$ 有限。(1.1) 以密度文件的平方根引理给出联合单侧 DQM。

### 1.2 单侧局部似然实验

取固定 $t\ge0$、$v\in\mathbb R^3$，$a=(t,v^T)^T$，令

$$
r_R=t/\sqrt R,\qquad \eta_R=\eta_0+v/\sqrt R,
\qquad \Delta_R=\frac1{\sqrt R}\sum_{i=1}^RS(Y_i),
\quad Y_i\overset{\mathrm{iid}}\sim P_0.
$$

**定理 N1。** 对每个这样的固定 $a$，

$$
\log\frac{dP_{r_R,\eta_R}^{\otimes R}}{dP_0^{\otimes R}}
=a^T\Delta_R-\frac12a^TIa+o_{P_0}(1),
\qquad \Delta_R\Rightarrow\mathcal N(0,I).
\tag{1.2}
$$

证明：写一条观测的密度比减一为

$$
u_R=\frac{a^TS}{\sqrt R}+\varepsilon_R,
\qquad E_0\varepsilon_R=0,\quad R E_0\varepsilon_R^2\to0.
$$

这由 (1.1) 得到。故 $\sum_i\varepsilon_R(Y_i)=o_P(1)$，$\sum_i u_R(Y_i)^2\to a^TIa$。后者可用 $\sum_i\varepsilon_R^2=o_P(1)$ 与 $R^{-1}\sum_i(a^TS_i)^2$ 的大数律及 Cauchy–Schwarz 得到。$\sqrt R u_R\to a^TS$ 的 $L^2$ 收敛还给出平方的一致可积性，从而

$$
P_0\{\max_i|u_R(Y_i)|>c\}
\le R P_0(|u_R|>c)
\le c^{-2} E_0[(\sqrt R u_R)^2\mathbf1_{\{|\sqrt R u_R|>c\sqrt R\}}]\to0.
$$

在该最大值小于 $1/2$ 的高概率事件上，逐项展开 $\log(1+u_R)$，总余项受 $C\max_i|u_R|\sum_i u_R^2=o_P(1)$ 控制。中心极限定理完成证明，允许 $I$ 奇异。

参数域是锥 $\{t\ge0\}\times\mathbb R^3$。没有构造负 $r$ 的伪概率，也不能把此边界实验直接套成无约束双侧 Wilks 检验。$t=0$ 时就是 nuisance 的通常局部实验。

## 2. 有效投影与局部分辨尺度

令 $\mathcal T_\eta=\operatorname{span}_{\mathbb R}\{s_\mu,s_{\log\tau},s_{\log s}\}$。它是有限维闭子空间。用 Moore–Penrose 逆定义

$$
\beta=I_{\eta\eta}^{\dagger}I_{\eta r},\qquad
e_r=s_r-\beta^Ts_\eta,\qquad
J_{\rm eff}=E_0e_r^2
=J-I_{r\eta}I_{\eta\eta}^{\dagger}I_{\eta r}\ge0.
\tag{2.1}
$$

这是正交投影：若 $c\in\ker I_{\eta\eta}$，则 $c^Ts_\eta=0$ 几乎处处，因此 $c^TI_{\eta r}=0$，所以 $I_{\eta r}$ 属于 $I_{\eta\eta}$ 的值域，正规方程可解。奇异性不需要 ridge/jitter，也不许可擅自删除物理 nuisance。

对每个 $t$，$v=-\beta t$ 最小化局部二次距离 $a^TIa$，最小值为 $t^2J_{\rm eff}$。沿此局部最不利路径，(1.2) 化为

$$
t\Delta_{{\rm eff},R}-\tfrac12t^2J_{\rm eff}+o_P(1),
\qquad \Delta_{{\rm eff},R}=R^{-1/2}\sum_i e_r(Y_i)
\Rightarrow\mathcal N(0,J_{\rm eff}).
\tag{2.2}
$$

因此当 $J_{\rm eff}>0$，未知 nuisance 后的**局部**非退化尺度仍为 $r\asymp R^{-1/2}$。若固定非中心量 $z=\sqrt{RJ_{\rm eff}}\,r>0$，则

$$
\delta_R\sim\sqrt{2z}\,J_{\rm eff}^{-1/4}
R^{-1/4}(\log R)^{-1/2}.
\tag{2.3}
$$

这是已给参数模型中的局部实验尺度与常数，不是全 nuisance 空间的统一有限样本保证。若 $J_{\rm eff}=0$，该路径在此阶退化，必须分析下一阶；不能把 $J>0$ 的简单假设尺度照搬为复合分辨率。

## 3. 二阶法向分布证明有效信息严格为正

### 3.1 条件定理：陈述所有额外条件

将 $\mathbb C^N$ 看作 $\mathbb R^{2N}$。假定 $N\ge2$，在全局相位商后，碰撞的无噪声分布为有限正权重圆混合

$$
\nu_0=\sum_{j=1}^L\omega_j\int_0^{2\pi}
\delta_{m_j(\theta)}\frac{d\theta}{2\pi},\qquad
m_j(\theta)=e^{i\theta}m_{0j},\quad \omega_j>0,
$$

其中每个 $m_{0j}\ne0$，且这些圆两两不相交。设 $b_j(\theta)=e^{i\theta}m_{1j}$，至少一个 $m_{1j}\ne0$，并且 $\kappa>0$。$r$ 导数具有 D1 给出的均值收缩加相位平均二阶形式；$\mu,\log\tau$ 仅对圆均值作一阶光滑变形，$\log s$ 是正各向同性 Gaussian 噪声的方差变化。

**定理 N2。** 在以上条件下，

$$
h\notin\operatorname{span}_{\mathbb R}
\{h_\mu,h_{\log\tau},h_{\log s}\},\qquad
J_{\rm eff}>0.
\tag{3.1}
$$

该定理不要求 nuisance Gram 满秩，不要求每个输入的所有时间坐标非零，也不要求低阶矩能分离导数方向。

### 3.2 把密度导数还原为紧支撑分布

对实值 $f\in C_c^\infty(\mathbb R^{2N})$，令 $D_v f$ 是沿固定实向量 $v$ 的方向导数。D1 的相位 Taylor 展开在信号分布层面定义 order 至多二的紧支撑分布

$$
T_r(f)=\kappa\sum_j\omega_j\int
\left[\frac14(D_{b_j}^2+D_{ib_j}^2)f(m_j)
-\frac12D_{m_j}f(m_j)\right]\frac{d\theta}{2\pi}.
\tag{3.2}
$$

系数 $1/4$ 来自 Taylor 的 $1/2$ 乘以 relative phase 的 $E\cos^2\phi=E\sin^2\phi=1/2$；$D_{b_j}^2$ 在每个点将 $b_j$ 视作固定向量，不对其作向量场导数。于是 $h=T_r*\varphi_s$。

均值 nuisance 产生的分布为

$$
T_\mu(f)=\sum_j\omega_j\int D_{\partial_\mu m_j}f(m_j)\frac{d\theta}{2\pi},
\quad
T_{\log\tau}(f)=\frac12\sum_j\omega_j\int D_{m_j}f(m_j)\frac{d\theta}{2\pi}.
$$

它们均为至多一阶。全局相位规范造成的切向速度也仅是一阶，且沿均匀闭圆积分为零。由于

$$
\partial_s\varphi_s=\tfrac14\Delta_{\mathbb R^{2N}}\varphi_s,
$$

噪声 nuisance 的分布为 $T_{\log s}=(s/4)\Delta\nu_0$，即

$$
T_{\log s}(f)=\frac s4\sum_j\omega_j\int\Delta f(m_j)\frac{d\theta}{2\pi}.
\tag{3.3}
$$

这里噪声每个实坐标的方差为 $s/2$，因此 heat 系数是 $1/4$，不是 $1/2$。

假设 $h=a_\mu h_\mu+a_\tau h_{\log\tau}+a_s h_{\log s}$ 于 $L^2(dy/p_0)$。$p_0>0$，故相应 Gaussian 卷积密度之差几乎处处为零。令 $T=T_r-a_\mu T_\mu-a_\tau T_{\log\tau}-a_sT_{\log s}$，则 $T*\varphi_s=0$。$T$ 有紧支撑，对 Fourier 变换有

$$
\widehat T(\xi)e^{-s\|\xi\|^2/4}=0.
$$

乘子在每点非零，可在任意紧 Fourier 邻域以光滑倒数局部相除，得到 $\widehat T=0$，故 $T=0$。这里只用紧支撑分布的 Fourier 变换及局部可逆性，不声称反 Gaussian 卷积在整个 Schwartz 空间连续。

### 3.3 隔离一条圆的法向 Hessian

选择 $m_{1j}\ne0$ 的一条圆。有限个紧圆互不相交，可在该圆任意小弧附近选不接触其他圆的管状邻域。该圆在 $m=m_j(\theta)$ 的切线为实一维

$$
\mathcal T_m=\operatorname{span}_{\mathbb R}\{im\},
\quad \mathcal N_m=\mathcal T_m^\perp,
\quad \dim_\mathbb R\mathcal N_m=2N-1\ge3.
$$

在小弧上选择光滑正交法向框架，管坐标写为 $(\theta,z)$。对任意紧支撑于该弧的光滑对称矩阵函数 $H(\theta)$，用管状截断函数构造

$$
f(\theta,z)=\tfrac12\chi(\theta,z)z^TH(\theta)z,
$$

其中 $\chi=1$ 于 $H$ 支撑对应的零截面附近。可令 $f$ 在邻域外为零，得到全空间紧支撑光滑函数。它和其梯度在全部信号圆上恒为零；在选中弧上，Hessian 的切向及交叉分量为零，法向块恰为任意 $H(\theta)$。

将这样的 $f$ 代入分布恒等式 $T=0$，所有一阶 nuisance 项及 $T_r$ 的收缩漂移均消失。记 $P_\perp$ 为法向正交投影，$b_R,(ib)_R$ 为实向量表示。任意 $H$ 给出

$$
\int\operatorname{tr}\left\{
\left[\kappa P_\perp(b_Rb_R^T+(ib)_R(ib)_R^T)P_\perp
-a_s s I_{\mathcal N_m}\right]H(\theta)\right\}d\theta=0.
$$

选中圆的正权重和共同 $1/4$ 已消去。由测试函数的任意性和系数连续性，每个该弧点都必须满足

$$
\kappa P_\perp(b_Rb_R^T+(ib)_R(ib)_R^T)P_\perp
=a_s s I_{\mathcal N_m}.
\tag{3.4}
$$

左边的秩至多为二。法空间维数至少三，存在非零法向量同时正交于 $P_\perp b_R$ 与 $P_\perp(ib)_R$；对其取二次型得 $a_s=0$，因为 $s>0$。但 $b\ne0$ 时 $b_R,(ib)_R$ 实线性独立，不可能同时落入一维切线。因此左边是非零半正定矩阵，与右边为零矛盾。假设的 nuisance 线性表示不成立。

乘以 $1/p_0$ 识别密度导数和得分后，$s_r$ 不属于有限维闭空间 $\mathcal T_\eta$，其正交残差范数严格为正。结合 D1 的有限信息界，得到 $0<J_{\rm eff}\le J<\infty$。这完成条件定理证明；尚需核实实际圆几何。

### 3.4 实际 N=4、QPSK、冻结分支核实

在密度文件第 1 节已经从真实三 atom Dirichlet 系数证明 $w_n\ne0$ 对所有 $n$ 成立，且 $b\ne0$。因此 $\operatorname{diag}(u_0)A^H$ 可逆，每个 QPSK 字的 $m_0$ 非零。

若两个字的相位圆相交，就有 $m_0(X')=e^{i\gamma}m_0(X)$。可逆性推出 $X'=e^{i\gamma}X$。QPSK 每个坐标非零且属于同一四点字母表，故共同相位只能取四个 QPSK 旋转。除去这个 global-four 等价类，恰有 $4^{4-1}=64$ 个正等权 orbit；它们的圆两两不相交。此证明不要求 $x=A^HX$ 的每一坐标非零。

对于小模态均值 $m_1=\sqrt{\tau N}\,u_1\odot x$，独立均匀 QPSK 与酉 DAFT 给出 $E|x_n|^2=1$，故

$$
E_X\|m_1(X)\|^2=\tau N\sum_n|u_{1n}|^2=\tau N>0.
$$

该期望在 global-phase 商后不变，因此至少一个 orbit 的 $m_1\ne0$。实际有限 PDP 的每个 $D_i>0$ 且 $b\ne0$，所以 $\kappa>0$。最后，$\mu$ 和 $\log\tau$ 在此固定分支只光滑移动碰撞圆，$\log s$ 恰为 (3.3) 的各向同性 heat 方向。

N2 的所有条件均已解析核实，因而在本任务四个实际基点

$$
\boxed{0<J_{\rm eff}(\mu_*,1,s)<\infty,
\qquad \mu_*\in\{0.27,0.35\},\quad s\in\{0.2,1\}.}
\tag{3.5}
$$

该结论来自分布的导数阶数与法向秩障碍，不来自有限样本残差或浮点 rank。它没有给出实用的正数下界，故不保证 2048 个样本能精确估计其大小，也不保证预定低阶特征保留了该信息。

## 4. 矩见证：条件性数值路线及其限制

### 4.1 可认证的充分条件

令 $\psi(Y)\in\mathbb R^K$ 为在公开基点固定的有限方差特征，$\bar\psi=\psi-E_0\psi$，定义

$$
\Sigma=E_0\bar\psi\bar\psi^T,\quad
d_r=E_0[\bar\psi s_r],\quad
D_\eta=E_0[\bar\psi s_\eta^T].
$$

若某个实向量 $a$ 满足 $a^TD_\eta=0$、$a^Td_r\ne0$，则

$$
J_{\rm eff}\ge\frac{(a^Td_r)^2}{a^T\Sigma a}>0.
\tag{4.1}
$$

证明：$f=a^T\bar\psi$ 对 nuisance 得分正交，故 $E_0fe_r=E_0fs_r=a^Td_r$。对 $f,e_r$ 用 Cauchy–Schwarz 即得；非零分子同时保证 $a^T\Sigma a>0$。有限维分离定理表明存在这样的 $a$ 当且仅当 $d_r\notin\operatorname{col}(D_\eta)$。

精确符号等式或带严格区间余量的线性代数可以认证此条件。浮点 rank、接近零的 nuisance 残差或训练得到的正 held-out 残差均不自动是认证见证。训练/评估拆分能避免同样本拟合偏差，不能消除投影系数估计误差。第 3 节已独立证明实际总体正性；本节仍然必须按特征空间的条件检查其保留程度。

### 4.2 精确多项式导数算子

对可积测试函数 $f$，令 $g(m)=E_\epsilon f(m+\epsilon)$。用 Wirtinger 导数，D1 的对偶算子为

$$
\mathcal Lg(m)=\sum_{i,j}(m_1)_i\overline{(m_1)_j}
\partial_{m_i}\partial_{\bar m_j}g(m)
-\frac12\left[\sum_i m_i\partial_{m_i}g(m)
+\bar m_i\partial_{\bar m_i}g(m)\right],
$$

在 $m=e^{i\theta}m_0$、$m_1$ 同乘该相位处求值。于是

$$
\left.\partial_rE_rf(Y)\right|_{0+}
=\kappa E_{X,\theta}\mathcal Lg(e^{i\theta}m_0).
\tag{4.2}
$$

这与 (3.2) 等价，因为 $D_b^2+D_{ib}^2=4\sum_{i,j}b_i\bar b_j\partial_{m_i}\partial_{\bar m_j}$。对 balanced monomial $F(m)=\prod_i m_i^{a_i}\bar m_i^{a_i}$，径向项为 $-|a|F$，即

$$
\mathcal LF=\sum_{i,j}(m_1)_i\overline{(m_1)_j}
\partial_{m_i}\partial_{\bar m_j}F-|a|F.
\tag{4.3}
$$

Gaussian 一维功率恒等式为

$$
E|m+\epsilon|^{2k}=
\sum_{\ell=0}^k\binom{k}{\ell}^2\ell!\,s^\ell|m|^{2(k-\ell)}.
\tag{4.4}
$$

不同坐标噪声条件独立，先对乘积应用 (4.4)，再对有限 QPSK orbit 平均，即得到所有有限阶功率矩及 (4.2) 的导数。算子采用多项式而非除以 $m_i$ 的表达，因此允许某些时间符号坐标为零。

例如

$$
\partial_rE|Y_n|^2\big|_0
=\kappa\tau N(|u_{1n}|^2-|u_{0n}|^2).
\tag{4.5}
$$

上一轮信道功率系数是 $K_n=\kappa N(|u_{1n}|^2-|u_{0n}|^2)$，所以观测导数恰为 $\tau K_n$，无额外噪声项。常数函数的算子为零，与零期望得分一致。`collision_teacher.py` 的 14 个一次/二次功率特征与至多四次功率协方差均使用这些有限代数恒等式；其浮点评估仍不等于符号或区间证书。

### 4.3 为什么 $K\ne0$ 单独不够

以下仅是逻辑反例，不是把实际 G0 改成 Gaussian 模型。取任意非零 Hermitian $H$ 和正定 $C_0$，在充分小邻域定义

$$
Y\sim\mathcal{CN}(0,C_0+(\mu+r)H).
$$

其协方差对 $r$ 的导数是非零 $H$，存在非零二阶矩导数；但 $s_r=s_\mu$，故 $J_{\rm eff}=0$。因此“可观测矩随分离变化”只能支持原始方向非零，不能证明它独立于 nuisance。

实际 N=4 切片的一阶功率向量具有 $(a,a,b,b)$ 对称结构，有限个功率特征完全可能让 $d_r$ 落入 $\operatorname{col}(D_\eta)$。这种特征失败与第 3 节的全密度有效正性并不矛盾；若发生，应如实报告该特征空间未见证，不选择新特征后冒称独立确认。

## 边界、未证项与验证说明

- (3.5) 的证明依赖有限 QPSK 圆、逐项非零碰撞响应、$N\ge2$、$b\ne0$、正各向同性噪声和已证 $r$ 密度导数；没有覆盖全八径、G1、平台、连续输入或任意 anisotropic-noise nuisance。
- 本文件不给 $J_{\rm eff}$ 的数值下界或高精度值；预定样本用于估计量级、投影稳定性及特征保留，而非重新用数值残差证明总体正性。
- 没有证明全参数空间可识别、复合检验的全局 minimax 风险、有限 separation 的有效得分渐近、receiver/decoder 增益或文献新颖性。
- 验证类型为解析证明和冻结源码对照；未新增科研采样。独立审查应重点检查联合加权支配、单侧 LAN 余项、Gaussian 卷积单射、管状测试函数的法向 Hessian 和实际 64 圆条件。
