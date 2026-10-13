# Research: 冻结 G0 五 atom 的二阶恢复与截断诱导中心信息

- Query: 实际 N≥9、五个公共 G0 atom 下，二阶协方差能否在未知 gain、未知信号尺度与未知 Gaussian 噪声方差时识别正 Doppler 双径？
- Scope: internal；完整解析证明与冻结源码约定对照，零数值运行、零新观察、无 SSH。
- Date: 2026-10-06
- Active task: `.trellis/tasks/10-05-method-advantage`；范围见 `.mission/20261006_15-24-04-afdm-usable-inference/PLAN.md`。
- Status: **节点反演、给定节点后全分支 rank=5、full 模型调制对称性、整块功率分布不变性与 ε 条件推论均已获独立解析复核。** 有限样本可用性、稳定最优率及论文新颖性仍未建立；数值证据由主线程另行管理。

## Findings

**科学范围的首要限制：本文的中心 Doppler 二阶识别是冻结 G0 截断模型中的信息。** 第 9 节证明，补全全部 N 个 Dirichlet atom、使用匹配的 full Gram 后，共同 Doppler 平移只乘逐时单位相位，功率与归一化均不变。对 fixed H 和独立 proper circular 对角 Gaussian 噪声，第 9.6 节进一步用耦合证明整块逐坐标功率观测的联合分布不变，故任意 power-only 非线性或高阶统计均不能识别 μ。固定五行截断破坏了该调制等变性。以下代数定理成立，但不能据此宣称未截断物理信道具有同样信息。

**实际完整五 atom 分支中，泛型节点并不需要四阶统计才能辨识。** 对 N≥9、两条正 Doppler、同零 delay、实际 G0 五行 m=−2,…,2 都保留，只要校正 Dirichlet 列相位后的两个有效 gain 不共线，观察功率的三个非零 Fourier 系数之虚部即可恢复无序 Doppler 对。方法消去了所有 gain 和共同尺度，不使用噪声 DC，不需要 σ² 或 τ 真值，也不枚举 16 个谱因子。

因此 N5 三 atom 的开放二阶歧义不能外推到实际大 N 五 atom。原反例与谱因子资格测试保留在 [SECOND_ORDER_N.md](SECOND_ORDER_N.md)。第 8 节进一步证明给定不同正节点后功率设计恒满列秩，故结合节点定理可恢复 H 到公共相位、归一化后的 gain 外积、τ 与 σ²。原始 gain 的径向尺度已被生成器归一化消除，不是恢复对象。全部结论限定于实际 G0 五 atom 模型。

### 1. 精确模型、mask 与有效 gain

N≥9，h=π/N，定义下列实常数（它们不是 DAFT chirp 参数）：

\[
c=\cos h>0,\qquad e=\cos(2h)>0,\qquad
d=\frac{\tan(2h)}{\tan h}=\frac{2c^2}{e}>2,
\qquad k=\frac{e^2}{dc^2}>0.
\tag{1}
\]

两条实际 Doppler ν₁≠ν₂ 位于同一合法开区间 I⊂(.22,.42)，共同 rounded delay=0，没有 physical clipping；**所有比较候选都由原生成器保留完整五行 m=−2,−1,0,1,2**。原五点窗口归一化、cap/prune、actual PDP 与实际 Gram 总归一化不改动。此区间并不自动保证任意 N、靠近 .22 的所有点都保留 +2 行，必须读取真实 mask；本文不涵盖侧带被剪掉的分支。N≥9 是分离全部 −4,…,4 功率谐波的充分条件，本文不主张它是受物理约束节点识别的最小必要阈值。

令 q_m 为包括 √τ 的归一化 G0 合成系数，H_i=Σ_m q_m exp(2πimi/N)。冻结 Dirichlet 比值给出

\[
\beta_m=e^{\mathrm imh}q_m
=\gamma_1 f_m(y_1)+\gamma_2 f_m(y_2),\quad
y_j=\tan h\cot(h\nu_j)>1,
\tag{2}
\]

\[
f_m(y)=\frac1{c_m(1+t_m y)},\quad
(t_{-2},t_{-1},t_0,t_1,t_2)=(-d,-1,0,1,d),
\quad(c_{-2},c_{-1},c_0,c_1,c_2)=(e,c,1,c,e).
\tag{3}
\]

若原始 gain 方向为 g_j、窗口正范数为 a_N(ν_j)、原 G0 Gram 为 R，则

\[
\gamma_j=\frac{\sqrt\tau}{\sqrt{g^HRg}}
\frac{\alpha_0(\nu_j)}{a_N(\nu_j)}g_j.
\tag{4}
\]

原生成器在 PDP 加权后做的公共径向缩放在该式抵消。ν∈(0,.5) 时 α₀ 的相位是 `π(N−1)ν/N`，其幅度为正，所以本文的关键条件

\[
\operatorname{Im}(\gamma_1\bar\gamma_2)\ne0
\tag{5}
\]

等价于

\[
\operatorname{Im}\!
\left[g_1\bar g_2 e^{\mathrm i\pi(N-1)(\nu_1-\nu_2)/N}\right]\ne0.
\tag{6}
\]

这不是 raw gain 非同相条件；在固定相异节点下，raw 两正实 gain 通常也满足 (6)。它与三 atom Prony 的有效相位条件一致，因为额外单列比例是非零实数。对每个真实严格正 PDP，原始复 Gaussian 方向连续，(5) 的失败集合概率为零；这不提供远离该集合的统一常数。

### 2. I₂、I₃、I₄ 怎样仅从观察得到

保持真实未知 iid QPSK 的固定相干块：`Y^(t)=diag(H) Aᴴ S^(t)+n^(t)`，n 为未知 σ² 的圆 Gaussian，A 为冻结酉 DAFT。总体逐坐标功率

\[
p_i=E|Y_i|^2=|H_i|^2+\sigma^2.
\tag{7}
\]

对 ℓ=1,…,4 定义

\[
C_\ell=\frac1N\sum_{i=0}^{N-1}p_i e^{-2\pi\mathrm i\ell i/N}
=\sum_{m=-2}^{2-\ell}q_{m+\ell}\bar q_m,
\tag{8}
\]

\[
I_\ell=\operatorname{Im}\left(e^{\mathrm i\ell h}C_\ell\right)
=\operatorname{Im}\sum_{m=-2}^{2-\ell}\beta_{m+\ell}\bar\beta_m.
\tag{9}
\]

N≥9 保证功率的九个谐波 −4,…,4 无 alias，故 (8) 精确。常数噪声只占 DC，完全不进入这些 Iℓ；τ 和 gain 大小会共同缩放 Iℓ，下一步取比消去。N8 的 ±4 已混叠，不能直接套 (8) 的 I₄ 公式。

数据接口只需要把 p_i 换成 `T^{-1}Σ_t|Y_ti|²` 后做一个 N 点 DFT；没有真实符号、H、gain、PDP 标签、σ²、τ 或真实节点输入。样本版的合法性/误差另见第 6 节，不把总体恒等式当成每份样本都成立。

### 3. Identity：所有虚部只含同一个 gain 因子

置

\[
S=y_1+y_2>0,\quad P=y_1y_2>1,\quad
D_t=(1+ty_1)(1+ty_2)=1+tS+t^2P,
\tag{10}
\]

\[
\Gamma=(y_2-y_1)\operatorname{Im}(\gamma_1\bar\gamma_2)\ne0.
\tag{11}
\]

由于所有 f_m 实数，自项 `|γ_j|² f_a(y_j)f_b(y_j)` 没有虚部。交叉项的精确差为

\[
f_a(y_1)f_b(y_2)-f_a(y_2)f_b(y_1)
=\frac{(t_a-t_b)(y_2-y_1)}{c_ac_bD_{t_a}D_{t_b}}.
\tag{12}
\]

所以

\[
I_\ell=\Gamma\sum_{m=-2}^{2-\ell}
\frac{t_{m+\ell}-t_m}{c_{m+\ell}c_mD_{t_{m+\ell}}D_{t_m}}.
\tag{13}
\]

**所有分母为什么为正。** y₁,y₂>1 且 d>2：D₁,D_d 的两因子均正；D_{−1} 的两因子均负，乘积为正；D_{−d} 也同理为正。c_m>0，D₀=1。于是各 Iℓ 同号，符号由 Γ 决定，且 I₄≠0。不能把单个 f_{−m}<0 误当成 D_{−m}<0。

令

\[
U=1+P,\qquad V=1+d^2P,\qquad
A=U^2-S^2=D_1D_{-1}>0,\quad
B=V^2-d^2S^2=D_dD_{-d}>0.
\tag{14}
\]

枚举 (13) 的有限项得

\[
\begin{aligned}
I_4/\Gamma&=\frac{2d}{e^2B},\\
I_3/\Gamma&=\frac{2(d+1)(UV-dS^2)}{ceAB},\\
I_2/\Gamma&=\frac{2dV}{eB}+\frac{2}{c^2A}.
\end{aligned}
\tag{15}
\]

例如 I₃ 来自 `1/(D₁D_{−d})+1/(D_dD_{−1})`，通分后的分子正好为 `2(UV−dS²)`。该有限项展开是本轮最优先的独立索引/符号核查对象。

### 4. Proposition：两个比值给严格单调的节点逆映射

定义仅由观察得出的两个量

\[
x=\frac{cd}{(d+1)e}\frac{I_3}{I_4},\qquad
v=\frac{I_2}{I_4}.
\tag{16}
\]

由 (15)，

\[
x=\frac{UV-dS^2}{A}
=d+\frac{(d-1)(P+1)(dP-1)}A>d.
\tag{17}
\]

又有

\[
B-d^2A=(d^2-1)(d^2P^2-1),
\tag{18}
\]

故

\[
\frac BA=d^2+(d+1)\frac{dP+1}{P+1}(x-d).
\tag{19}
\]

于是 P 是单变量方程

\[
v=F(P;x):=
e(1+d^2P)+kd^2
+k(d+1)\frac{dP+1}{P+1}(x-d),\quad P>1
\tag{20}
\]

的唯一解，因为

\[
\frac{\partial F}{\partial P}
=ed^2+k(d+1)\frac{d-1}{(P+1)^2}(x-d)
>ed^2>0.
\tag{21}
\]

真实模型保证该解存在。若要从任意输入检查存在性，x>d 时 F 连续严格增且趋向 +∞，所以恰在 `v>F(1;x)` 时存在唯一 P>1；这仍不是完整物理资格的全部条件。

得到 P 后，顺次恢复

\[
A=\frac{(d-1)(P+1)(dP-1)}{x-d},\quad
S=+\sqrt{(P+1)^2-A},\quad
y_{1,2}=\frac{S\pm\sqrt{S^2-4P}}2,
\tag{22}
\]

\[
\nu_j=\frac1h\arctan\frac{\tan h}{y_j}.
\tag{23}
\]

正支 S>0 来自正 Doppler 所给 y_j>1；没有这项物理知识，S² 本身不能选择正负支。真实模型保证实异根、y_j>1、ν_j∈I。任一同样满足完整五 atom / 正分支、且与本模型协方差相等的另一双径，其 I₄ 相同非零，也满足 (17)–(23)，故无序节点对必相同。证毕。

该证明没有靠维数计数、有限探针或一般谱因子定理，亦没有用完整 H。它说明五 atom 物理约束比 ambient 16 个谱因子计数强得多。full conjugate-reflection 因子把正节点映到负节点，与此正支限制相容地被排除。

**固定正则内点的一致性推论。** 另固定一个满足上述条件的真实参数点，要求两节点到 I 的边界有正距离，且实际 cap/prune 的所有相关比较均有严格裕量，使完整五行 mask 在该点的某个邻域内恒定。仅在阈值等号处恰好保留五行不满足此附加条件。条件于固定 H，随独立相干块内快照数 T→∞，经验功率依强大数定律收敛；(8)–(9) 是连续线性变换，I₄≠0、(21) 及相异根保证局部逆连续。所有节点合法域不等式严格，且真实 mask 局部恒定，故按这些显式检查定义的经验矩节点反演最终几乎必然通过检查，并几乎必然收敛到真实无序节点对。有限 T 时检查失败仍须报告未判定。这个点态推论不改变总体节点唯一性的条件，也不提供有限样本误差、趋零 δ 的统一率或相对其他算法的优势。

### 5. 从节点到完整 H 与强二阶参考

第 4 节先证明节点恢复。给定恢复节点后，令 b₁,b₂ 是真实 G0 两条时间响应列，则

\[
p_i=u|b_{1i}|^2+w|b_{2i}|^2
+2r\operatorname{Re}(b_{1i}\bar b_{2i})
-2s\operatorname{Im}(b_{1i}\bar b_{2i})+\sigma^2.
\tag{24}
\]

这里 `u=|ξ₁|²,w=|ξ₂|²,r+is=ξ₁conj(ξ₂)`，ξ 包括当前信号尺度与 Gram 归一化，见 (35)。由这些已恢复节点构造的 N×5 实设计矩阵为

\[
[|b_1|^2,\ |b_2|^2,\ 2\operatorname{Re}(b_1\bar b_2),
\ -2\operatorname{Im}(b_1\bar b_2),\ \mathbf1]
\tag{25}
\]

**第 8 节证明 (25) 对上述整个不同正节点、完整五 atom 分支恒满列秩。** 因此连同 σ² 的 Hermitian gain 外积 X 也唯一，真实模型保证其 PSD/rank-one，可恢复 ξ 和 H 到公共相位。该秩结论不需要有效 gain 非共线；从未知节点开始的泛型恢复仍需要 (5)。

用于该 G0 模型的有限样本比较时，应至少包括“代数节点初始化＋冻结 G0 全功率拟合”的强二阶参考；同样使用 unknown σ²/τ 和相同数据。不能把一个依赖真值 DC 的弱谱因子参考当成全部二阶信息的能力。四阶若在此模型有收益，应体现更好的稳健性、方差或额外退化层处理，不能再声称泛型五 atom 节点没有二阶信息；未截断物理模型的中心对称性另见第 9 节。

### 6. 取比前的扰动边界与明确失败条件

先讨论确定性误差，不把它冒充已证明的统计置信区间。若 `|Ĩℓ−Iℓ|≤ε` 对 ℓ=2,3,4 成立，且 `|I₄|>2ε`，则

\[
\left|\frac{\widehat I_\ell}{\widehat I_4}
-\frac{I_\ell}{I_4}\right|
\leq\frac{2\epsilon}{|I_4|}
\left(1+\left|\frac{I_\ell}{I_4}\right|\right).
\tag{26}
\]

因为 `|Ĩ₄|≥|I₄|−ε>|I₄|/2`，分子展开即得。它给出不可忽略的 `1/|I₄|` 放大。在实际数据中 I₄ 不可见，必须由另行校准的误差控制来判定可信度；仅看非零浮点数不能认证可用。

如果 x̂>d、v̂>F(1;x̂) 并求得 P̂>1，(21) 和 `0<F_x<kd(d+1)` 给

\[
|\widehat P-P|
\leq\frac{|\widehat v-v|+kd(d+1)|\widehat x-x|}{ed^2}.
\tag{27}
\]

继续经过 (22) 时，误差还受 `1/(x−d)`、`1/S` 和 `1/sqrt(S²−4P)` 等导数影响。后者是节点间隔的倒数。准确可计算的局部 Jacobian 来自 (20) 的隐函数导数

\[
P_v=1/F_P,\quad P_x=-F_x/F_P,
\quad A=\frac{(d-1)(P+1)(dP-1)}{x-d},
\tag{28}
\]

再对 (22)–(23) 求导；不需要用数值 log-log 图猜指数。

**共同尺度怎样消失。** 式 (15) 中所有 Iℓ 都等于 Γ 乘正的实有理函数，Γ 是 (11)。固定非碰撞几何下，有效 gain 接近共线会使全部 Iℓ 同时趋零；其比值在总体仍有限，经验比值却变得不稳定。固定 raw gain 且 g₁+g₂≠0、δ→0 时，y₂−y₁ 为 O(δ)：泛型 raw 相位下 Γ 为 O(δ)，raw 共线但不同 Dirichlet 列相位时通常再有一个 O(δ) 因子，Γ 为 O(δ²)。主模态精确取消 g₁+g₂=0 时归一化尺度也奇异，不能套用这两个阶数。

在固定正则分支上，把 (26) 与节点根的导数组合，最直接的误差放大含 `ε/(|Γ| |y₂−y₁|)`；泛型近碰撞时提示可能出现 δ⁻² 量级的绝对节点误差放大。这是该 ratio 逆映射的敏感性提示，不是 sharp minimax 率，也不说明完整二阶功率拟合无法做得更好。必须先做确定性 moment 扰动，再决定是否值得新增观测比较。

**不得隐藏的失败。** I₄=0 / 误差尺度内近零、x̂≤d、v̂≤F(1;x̂)、负的 S² 或判别式、根不大于 1、Doppler 越界、真实 mask 不符，都需显式拒绝或报告未判定；不得 clip、取绝对值修根、固定真值中心、换 mask 或 silently fallback 后算成成功。有效共线层可能仍有其他二阶信息，但本命题和算法对此不作保证。

### 7. 优先给主线程的最小确定性核对

全部未执行；须使用冻结已提交源码、独立准入及 SSH 单线程规则。

1. N∈{9,16}、ν∈{(.27,.35),(.29,.33)}、raw gain∈{(1,.7i),(1,.7)}。沿真实 geometry / Gram 得 H，核对完整五行 mask；从总体 `|H|²+σ²` 的 DFT 取得 Iℓ，而非直接把真值 γ 传给反演。
2. 独立核对 (12)–(15) 的符号、e^{+iℓh} dephase、N≥9 的无 alias、未知 σ² 增加只改 DC；随后按 (16)–(23) 盲反解，真值仅用于输出误差。
3. 加一个预设有效共线 gain fixture，I₂/I₃/I₄ 应同时为零且反演显式拒绝。另将该相位偏离预设小量，保存 I₄、Jacobian 和 (26) 的误差放大；不用按结果挑 gain。
4. 先在同一总体 I 上施加已冻结的有限确定性扰动方向/幅度，观察合法域、节点误差和拒绝率；无新随机 Y。只做精确反解小误差不够证明有限样本可用。
5. 节点恢复后，使用恢复值构造 (25)，保存奇异值及 rank-one/PSD gain 重建残差。第 8 节已证明代数满秩；本项检验实际实现、浮点分辨率及条件数，不能把经验 SVD 阈值当成该定理的前提。

### 8. 给定节点后的完整功率设计：全分支满秩证明

本节严格推导已由独立 reviewer 核对通过，包括 (33) 的三个形式变量有理恒等式精确检查；这不是数值样本实验。结论适用于 N≥9、完整五 atom、不同正节点的整个所述分支；**给定节点后的秩结论不需要有效 gain 非共线**。此前的非共线条件仍用于从未知节点开始的三虚部节点反演。

实际两条响应列可写为 `b_j(i)=κ_j B_{y_j}(θ_i)`，其中 `κ_j=α₀(ν_j)/a_N(ν_j)≠0`、`θ_i=2πi/N−h`，且

\[
B_y(\theta)=\sum_{m=-2}^2 f_m(y)e^{\mathrm im\theta}.
\tag{29}
\]

用非零对角矩阵变换两个复 gain，对 Hermitian 2×2 矩阵的四个实自由度是可逆变换，故不会改变 (25) 的列秩。只需对 B_y、B_z 证明，y,z>1 且 y≠z。所有 f_m 为实数，前三个功率列为 θ 的偶函数，第四列为奇函数；所有功率谐波均在 −4,…,4，N≥9 时离散采样后仍可唯一分离。**本节 Fourier 系数的“实/虚”均指 θ=t−h 坐标：实际 t 网格的 DFT 系数 C_ℓ 须先乘 e^{iℓh} 去相位。** 未去相位的原始 C_ℓ 不具有下文所用的实/虚分离。

定义

\[
\begin{aligned}
D_1(y)&=1-y^2,&D_d(y)&=1-d^2y^2,\\
L_\ell(y,z)&=\sum_{m-\ell\in\{-2,\ldots,2\}}f_m(y)f_{m-\ell}(z),&
K_\ell(y,z)&=\tfrac12\{L_\ell(y,z)+L_\ell(z,y)\}.
\end{aligned}
\tag{30}
\]

这里求和也限定 m∈{−2,…,2}。`|B_y|²` 的第 ℓ 个 Fourier 系数为 K_ℓ(y,y)，`2Re(B_y conj(B_z))` 的该系数为 2K_ℓ(y,z)。直接有限和给出

\[
\begin{aligned}
K_4(y,z)&=\frac{1-d^2yz}{e^2D_d(y)D_d(z)},\\
K_3(y,z)&=\frac{1-dyz}{ce}
\left\{\frac1{D_d(y)D_1(z)}+\frac1{D_d(z)D_1(y)}\right\},\\
K_2(y,z)&=\frac1e\left\{\frac1{D_d(y)}+\frac1{D_d(z)}\right\}
+\frac{1-yz}{c^2D_1(y)D_1(z)}.
\end{aligned}
\tag{31}
\]

令 `a=(d+1)e/(2c)`，利用 d=2c²/e 得到恒等式

\[
\begin{aligned}
K_2(y,y)&=aK_3(y,y),\\
\frac{K_3(y,y)}{K_4(y,y)}
&=\frac{2e}{c}\left\{d+\frac{d-1}{y^2-1}\right\},\qquad
K_4(y,y)=\frac1{e^2D_d(y)}\ne0.
\end{aligned}
\tag{32}
\]

该比值在 y>1 上严格递减。另一方面，异节点的同一线性组合满足

\[
\begin{aligned}
K_2(y,z)-aK_3(y,z)
&=-\frac{(y-z)^2\,\mathcal Q(y,z)}
{2c^2D_d(y)D_d(z)D_1(y)D_1(z)}<0,\\
\mathcal Q(y,z)
&=(d-1)^3(d+1)+d^3(y^2-1)(z^2-1)\\
&\quad+d(d-1)^2(d+1)(yz-1)>0.
\end{aligned}
\tag{33}
\]

式 (33) 可由 (31) 通分核对：分子先除以 (y−z)²，再用 `y²+z²−y²z²=1−(y²−1)(z²−1)` 因式化。分母含四个负因子，严格为正。

**三个偶功率列的非零谐波线性无关。** 若这三列的某个实线性组合在 ℓ=4,3,2 上均为零，先用 ℓ=2 的系数方程减去 a 倍 ℓ=3 的方程。式 (32) 消去两自功率系数，式 (33) 强制交叉实部系数为零。余下 ℓ=4,3 两行的行列式非零，因为 (32) 的比值在不同 y,z 处不同，故两自功率系数也为零。

**奇功率列与 DC 再各增一秩。** 第四列 `−2Im(B_y conj(B_z))` 的第 4 个 Fourier 系数为 `i{L₄(y,z)−L₄(z,y)}`，其中

\[
L_4(y,z)-L_4(z,y)
=\frac{2d(z-y)}{e^2D_d(y)D_d(z)}\ne0.
\tag{34}
\]

它纯虚，与前三列及 DC 的实 Fourier 系数独立。先由第 4 个 Fourier 系数的虚部消去第四列，再用上一段消去前三列，最后常数列系数只能为零。因此 (25) 的秩严格等于 5。此证明不依赖有限探针、复合 q_m 是否恰有抵消或经验 SVD 阈值。

**物理恢复的准确对象。** 令 `𝔅=[b₁,b₂]` 为实际 G0 时间响应矩阵；由于共同零 delay、五个整数 Fourier atom 无 alias，`R=𝔅ᴴ𝔅/N=WᴴW`，与原生成器 Gram 完全相同。这里 𝔅 包含实际列尺度 κ_j，不是仅含 f_m 的去尺度响应。用 `g_raw` 区分归一化前原始 gain，并令

\[
\xi=\frac{\sqrt\tau\,g_{\rm raw}}
{\sqrt{g_{\rm raw}^HRg_{\rm raw}}},\qquad X=\xi\xi^H,
\qquad \tau=\operatorname{tr}(RX).
\tag{35}
\]

给定节点后，完整总体功率唯一确定 X 与 σ²，甚至无需预先施加 PSD/rank-one 约束；真实模型保证解具有这些性质。再由 rank-one 分解恢复 ξ 及 H 到公共相位。结合第 4 节的非共线节点识别定理，完整五 atom 正分支的泛型二径因此可由二阶功率恢复节点、H 的公共相位等价类、τ 与 σ²。原始 gain 的公共径向尺度已由生成器归一化消除，不能恢复，也不是新增 scale/noise 混淆。节点置换同样属于标签对称。

本节满秩不提供统一最小奇异值或有限样本稳定性；y→z 时 (33) 的 (y−z)² 和 (34) 的 (z−y) 同时趋零。节点未知且有效 gain 共线的分支尚未分类，不能用“给定节点时满秩”跳过该问题。

### 9. 首要模型边界：五 atom 的中心信息来自截断

本节核对冻结源码的符号后给出解析对照，不改代码、数据、prior 或运行预算。它区分三个对象：本文实际 G0 五行模型；按相同 Fourier 符号补全的全 N 分量模型；现有代码中名为 `g1` 的控制。三者不能互换。

**9.1 冻结 full Dirichlet 补全的确切符号。** 冻结 `afdm_env.py:418–445` 的 `dirichlet_alpha` 使用 x=m+κ；本稿节点均在 (.22,.42)，其 rounded center 为零。对这些非整数内点，代码的闭式正是有限和

\[
\alpha_N(m+\nu)=\frac1N\sum_{r=0}^{N-1}
e^{2\pi\mathrm i(m+\nu)r/N}.
\tag{36}
\]

冻结整数 G0 时间基是 `exp(+2πimn/N)`，见 `prior.py:33–36`。若数学上把 m 补成任意完整 N 个整数残基、无 cap/prune、无五点窗口缩放，则

\[
\begin{aligned}
F_\nu(n)&=\sum_{m\in\mathbb Z_N}
\alpha_N(m+\nu)e^{2\pi\mathrm imn/N}\\
&=\frac1N\sum_{r=0}^{N-1}e^{2\pi\mathrm i\nu r/N}
\sum_{m\in\mathbb Z_N}e^{2\pi\mathrm im(r+n)/N}\\
&=e^{2\pi\mathrm i\nu r_n/N},\qquad r_n=(-n)\bmod N\in\{0,\ldots,N-1\}.
\end{aligned}
\tag{37}
\]

因此此符号约定的 full completion 是通常正时序单径 `exp(+2πiνn/N)` 的固定时间指标置换，不能不加说明直接等同它。该置换不影响以下共同平移论证，也不改变 full Gram。由 Parseval，完整 α 向量范数为 1；若完整列只作自身全 N 范数归一化，也不会加入 ν 相关缩放。

**9.2 共同中心平移的精确二阶不可辨识性。** 取任何足够小实 a，使两节点 ν₁+a、ν₂+a 仍位于同一合法内点区间。定义单位对角矩阵

\[
M_a=\operatorname{diag}\{e^{2\pi\mathrm ia r_n/N}\}_{n=0}^{N-1}.
\tag{38}
\]

令 F=[F_{ν₁},F_{ν₂}]，则 `F(ν₁+a,ν₂+a)=M_a F(ν₁,ν₂)`，所以匹配的完整 Gram 满足

\[
R_{\rm full}(\nu_1+a,\nu_2+a)
=\frac1N F^H M_a^HM_aF
=R_{\rm full}(\nu_1,\nu_2).
\tag{39}
\]

固定同一个非零 raw gain 方向、同一个 actual PDP 实现方向与同一 τ，采用此 R_full 的归一化得到

\[
H_{\rm full}(\mu+a,\delta)=M_aH_{\rm full}(\mu,\delta),\qquad
|H_{\rm full}(\mu+a,\delta)|^2=|H_{\rm full}(\mu,\delta)|^2.
\tag{40}
\]

更直接地，令 t_r=2πr/N，归一化前的功率为

\[
|g_1|^2+|g_2|^2+
2\operatorname{Re}\{g_1\bar g_2e^{-2\mathrm i\delta t_{r_n}}\},
\tag{41}
\]

不含 μ；(39) 保证归一化不重新引入它。真实同零 delay 正时序物理响应也满足同一结论，只须把 r_n 换成 n。因此对固定相干 H、未知 QPSK 酉混合的观察，全部二阶协方差 `diag(|H|²)+σ²I` 都对共同中心平移不变，即使已知 τ、σ² 也无法恢复 μ。这是参数类中的精确非单射，不依赖渐近 N 或数值小误差；并不主张按可能随几何变化的 prior 边缘化后分布一定相同。

**9.3 G0 在哪一步破坏了该对称性。** 冻结 `physical_cluster_weights:92–102` 先取 m=−2,…,2 的五点 Dirichlet 窗口，按其能量归一化，再做 cap/prune；`generate_channel_matrix:591–611` 对应同样顺序。固定五点 Fourier 投影一般不与非整数 M_a 交换，投影后的逐时幅度会随绝对节点位置改变。五点列范数也随节点位置变化，最终 `R_G0=W_G0ᴴW_G0` 与 full Gram 不同。实际二径未知 gain 的非零列尺度可被参数重标定吸收，但投影改变列的形状，不能由一个 gain 尺度撤销。本文三虚部逆及满秩定理刻画的正是这个冻结近似模型中的信息。

所以准确的研究表述是“冻结五 atom G0 模型的二阶可辨识性及截断诱导的中心信息”。不能称“物理分数 Doppler 固有二阶中心信息”，也不能以本稿撤销未截断物理模型对相位统计的需求。全 N 补全只是这一解析审计中的对照模型；并未替换本轮实际生成器或授权新运行。

**9.4 现有 `g1` 标签还复用了 G0 Gram。** `prior.py:37` 定义 `g1=exp(+i outer(time,ν))`，是正时序响应。可是 `ActualPrior._components:205–206` 与 `sample:308–309` 均先用 `geo['gram']` 归一化，再选 `geo[self.model]`；该 Gram 由 G0 weights 得来。因此现有 `model='g1'` 控制不是 (39) 中匹配 R_full 的完整归一化模型。在固定同一 τ、raw gain 时，它的 G0 分母可留下 μ 相关的公共尺度，不能直接套用 (40) 的固定尺度不变式。

**但本轮 τ 未知时，这个尺度效应仍不能提供中心识别。** 固定同一非零 raw gain g，记 `r₀=gᴴR_G0(μ,δ)g`、`r_a=gᴴR_G0(μ+a,δ)g`，两者须严格正以定义归一化。取节点与 τ 的合法内点，并要求 G0 mask 在该点邻域恒定，则 r_a 连续；足够小的合法 a 保证 r_a>0 且 `τ′=τ r_a/r₀` 仍在允许尺度域中。于是 `√τ′/√r_a=√τ/√r₀`，现有 g1 控制在 (μ+a,τ′) 的 H 只差正时序单位调制，功率完全相同。这是 fixed-gain、unknown-scale 参数类中的 μ–τ 混淆；不主张将 gain 边缘化后仍可用一个统一 τ′ 匹配所有混合分量。本文不改变旧接口、既有结果或标签，只明确不可把该控制当作 (39)–(41) 的匹配 full-normalization 验证替身，也不能把其固定 τ 尺度变化当成本轮可用中心信息。

**9.5 四阶仍可区分 full 模型的共同平移对。** 若 H_full 所有时间坐标非零，前轮 balanced 四阶纤维定理仍适用。对小的非零非整数 a，M_a 不是循环 character：其第 1 与第 N−1 个对角项之积为 e^{2πia}≠1，而 character 必满足该乘积为 1；第 0 项等于 1 也固定了可能的公共相位。因此 (40) 中两组不同中心具有相同二阶矩但不同 balanced 四阶张量，固定参数对的四阶 Frobenius gap 严格正。这不证明所有 full 模型的全局参数唯一性，不提供有限样本优势，也不批准新增观测；它说明本文 G0 的泛型二阶定理与真实物理模型需要相位信息并不矛盾。

**9.6 短推论：整块逐坐标功率联合分布不含共同中心信息。** 固定两个确定性信道 H 与 H′=DH，其中 D 是确定的单位对角矩阵，|D_ii|=1。取任意有限 T，观察 `Y^(t)=diag(H)U S^(t)+n^(t)`；两模型使用同一固定 U、同一源分布，噪声独立于全部源，且各快照独立、`n^(t)~CN(0,Σ)` 为零均值 proper circular Gaussian、Σ 为相同的对角协方差。原观察的 Σ=σ²I 满足该条件。

在同一概率空间取完全相同的 S^(t)，并定义 `n′^(t)=D n^(t)`。因为 `DΣDᴴ=Σ` 且噪声伪协方差为零，整个 `(S,n′)` 与第二模型规定的输入联合分布相同；独立性也保留。同时逐样本有

\[
Y'^{(t)}=\operatorname{diag}(DH)US^{(t)}+Dn^{(t)}
=DY^{(t)},\qquad |Y'^{(t)}_i|^2=|Y^{(t)}_i|^2.
\tag{41a}
\]

故整份功率数组 `{|Y_i^(t)|²: i=0,…,N−1, t=1,…,T}` 的联合分布在两模型中完全相同，任意可测 power-only 统计也同分布。证明不需要 S 或 US 为 circular Gaussian，也不需要 US 的坐标独立；真实 QPSK 源可以原样耦合。若某些 H_i=0，推论依然成立，不需要第 9.5 节的时间非零条件。

将 D 取为 (38)，得到匹配 full Gram 的固定信道共同中心平移对：即使 τ 已知，任意有限快照数、任意阶的功率矩、功率相关、非线性功率特征与整块 power-only 似然都不能区分这对 μ。对现有 g1 控制，先按第 9.4 节作合法 τ′ 补偿，再应用同一推论，也得到相同结论。因此该结论强于“Cov(Y) 相同”；power-only 检验对这一参数对的拒绝概率恒相同，无法靠增加功率统计的阶数获得中心识别。

这不与第 9.5 节矛盾：可区分中心的 balanced 四阶张量含有 `Y_i conj(Y_j) Y_k conj(Y_l)` 的复相位信息，并非只依赖逐坐标功率的子集。结论限定于 fixed H、相同源分布、上述对角相位不变噪声及当前对角信道观察。**power-only 特指原始 Y 坐标的逐坐标功率数组；不包括先对 Y 做非对角变换再取模。** 例如 `Uᴴdiag(exp(−iθ))Y` 后的模长是相位敏感特征，即使最终统计使用模长或四次方，也不属于本推论排除的 power-only 类。结论也不覆盖任意相关噪声，不声称一个统一 τ′ 可在 gain 边缘化后匹配所有 prior 混合分量。此处无新增模拟或有限样本收益声明。

### 10. 条件模型推论：已知正侧带幅度可趋小，但不能称为原生成器

本节仅分析主线程提出的条件模型：固定相同 N≥9 与三/五行的 f_m，把 ±2 两行都乘一个已知 ε>0，其余三行不变，**不再对这些人为缩小的行运行 pruning**。这不是实际 G0 的另一工作模式，也不是 full 物理模型。若在该条件模型中重算列范数或共同 Gram 归一化，它们只重定义两个非零列尺度及共同幅度，可吸收进 γ_j(ε) 与 Γ_ε；但必须仍满足有效非共线。

三个可观察虚部变为

\[
\begin{aligned}
I_4^{(\varepsilon)}&=\varepsilon^2\Gamma_\varepsilon\frac{2d}{e^2B},\\
I_3^{(\varepsilon)}&=\varepsilon\Gamma_\varepsilon
\frac{2(d+1)(UV-dS^2)}{ceAB},\\
I_2^{(\varepsilon)}&=\Gamma_\varepsilon
\left\{\varepsilon\frac{2dV}{eB}+\frac{2}{c^2A}\right\}.
\end{aligned}
\tag{42}
\]

令 `G₄=I₄^(ε)/ε²`、`G₃=I₃^(ε)/ε`，再定义

\[
x=\frac{cd}{(d+1)e}\frac{G_3}{G_4}>d,
\qquad v_\varepsilon=\frac{I_2^{(\varepsilon)}}{G_4}.
\tag{43}
\]

消元与第 4 节相同，只把原 F 的第一项乘 ε：

\[
\begin{aligned}
v_\varepsilon=F_\varepsilon(P;x)
&=\varepsilon e(1+d^2P)+kd^2
+k(d+1)\frac{dP+1}{P+1}(x-d),\\
\partial_PF_\varepsilon
&=\varepsilon ed^2+
k(d+1)\frac{d-1}{(P+1)^2}(x-d)>0.
\end{aligned}
\tag{44}
\]

所以任意固定、已知 ε>0 都保留泛型节点唯一性；P 后的 S 与节点公式不变。任意输入的 P>1 存在条件为 `x>d` 且 `v_ε>F_ε(1;x)`，仍须检查所有根与条件模型分支。

ε=0 时 G₃、G₄ 不再有观察定义，不能把 (44) 的形式极限当成仍可用的逆映射。此时条件模型只剩三 atom，而 SECOND_ORDER_N 第 4 节的同 N 三 atom 构造（其代数对 N≥5 成立）给开放二阶歧义。故“已知任意小非零侧带”与“侧带严格为零”可以有不同的总体可辨识性；这不保证前者可从有限样本稳定估计。式 (42) 中三、四次谐波分别带 ε、ε²，经验误差取比可能放大，本文不声明最优 ε 速率。

这一推论只解释固定截断模型的结构边界。实际 pruning 是离散 mask 切换，不是本节连续 ε 路径；补回全部其余 Dirichlet 行还会按第 9 节恢复中心调制不变性，故不能据此声称“增加更多真实侧带总会增加中心功率信息”。本节无新数值或采样授权。

### 11. 截断机制的短恒等式：中心幅度变化由交换子残差产生

本节只隔离**不作逐列归一化**的固定 Fourier 正交投影 P_S；H 是投影前的同一完整响应，D_a 是第 9 节的共同 Doppler 单位对角调制。它不是实际 G0 逐列窗口归一化与最终 Gram 归一化的替代公式。定义

\[
\mathcal E_a=[P_S,D_a]H=P_SD_aH-D_aP_SH.
\tag{45}
\]

由于 `P_SD_aH=D_aP_SH+ℰ_a` 且 D_a 保持每个坐标的模，逐坐标精确有

\[
|P_SD_aH|^2-|P_SH|^2
=2\operatorname{Re}\{\overline{D_aP_SH}\odot\mathcal E_a\}
+|\mathcal E_a|^2.
\tag{46}
\]

这里 ⊙ 是逐坐标乘积。因此

\[
\bigl\||P_SD_aH|^2-|P_SH|^2\bigr\|_\infty
\le\bigl(2\|P_SH\|_\infty+\|\mathcal E_a\|_\infty\bigr)
\|\mathcal E_a\|_\infty.
\tag{47}
\]

再由 `ℰ_a=D_a(I−P_S)H−(I−P_S)D_aH` 及 D_a 的酉性得到

\[
\|\mathcal E_a\|_2
\le\|(I-P_S)H\|_2+\|(I-P_S)D_aH\|_2.
\tag{48}
\]

所以该原始投影模型中的中心幅度变化来自投影与调制不交换的残差，并受平移前后被丢弃的 Fourier 尾部控制。全 N 支撑时 P_S=I，残差和幅度差严格为零。非零残差不保证幅度差非零，边界也不说明支撑扩大时中心信息单调变化；它们只是确定性恒等式与误差界，不是 Fisher 信息、噪声下可检测性或有限样本收益。实际 G0 的额外归一化仍须按前文单独处理。本节不增加任何数值配置。

## Files Found / Code Patterns / Related Specs

- `experiments/afdm_higher_order_information/prior.py:25`：实际 cap / clipping / G0 Fourier 响应；`:36` 的正号 Fourier 约定决定 (8) 的 DFT 符号。
- `experiments/afdm_shared_channel_20261004/production_prior.py:46`、`:74`：真实 W 与 Gram；式 (4) 沿用该公共归一化。
- `experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py:418`：Dirichlet 的 m+κ 正号；`:448` 为整数 Python DAFT；`:591` 起五点窗口归一化、cap/prune，`:631` 起最终 Frobenius 归一化。
- 同 upstream 的 `budgeted_support_diagnostics.py:82`：明确匹配 truncated generator 的实际 W；`:92`–`:102` 给保留顺序。
- `experiments/afdm_efficient_information/prior_likelihood.py:205`、`:308`：现有 g1 控制也使用 G0 Gram，不能作独立 full-normalization 证据。
- `experiments/afdm_coherent_structure_20261006/core.py:70`：固定一份 H、独立未知 QPSK 和噪声；(7) 不要求知道符号。
- `SECOND_ORDER_N.md:206` 附近：五 atom rational 资格判据；本文提供更直接的泛型节点证书，不删除旧判据对退化候选的价值。
- 沿用已读 `research-protocol.md`、`bounded-mathematical-studies.md`、`structured-inference.md` 与 `formula-derivation`；不改变原始 prior、实验、论文或生产主张。
- 本 topic 未新增外部搜索；高阶谱/Prony 的经典背景见上一轮 `CLASSICAL_CONNECTIONS.md`。本文“同 gain 因子取比＋正支单调反演”的新颖性仍需专门差异审查，不能自称首创。

## Caveats / Not Found

- **最重要的模型限制：μ 二阶识别为冻结 G0 截断模型的效应。** 匹配 full Gram 的未截断同 delay 物理模型对共同 Doppler 平移有精确功率不变性；第 9.6 节还证明，在 fixed H 与 proper circular 对角噪声条件下，整块功率数组联合分布不变，任意 power-only 统计均无中心判别力。现有 g1 控制需合法 τ′ 补偿且不能直接等同匹配 full Gram 的物理模型。
- 需要 N≥9、完整五 atom、共同零 delay、正 Doppler 分支、有效 gain 非共线；没有声称含剪枝缺项、负 Doppler 或跨分支的全局恢复。
- 三个 I 比值识别节点；第 8 节已证明 (25) 全分支满秩。节点未知且有效 gain 共线的分支仍未分类，raw gain 径向尺度被归一化消除。
- 噪声方差无需真值，但经验非零 Fourier 系数仍有噪声方差；“剔除 DC”不等于统计上无噪声。
- 近碰撞和近有效共线会使 I₄ 极小。本文不是已验证的稳定 estimator、最优率或实际收益；应先执行 moment 扰动和强二阶参考检验。
- 本稿完成不意味着长期目标完成。解析主命题复核已完成；仍需冻结模型数值核对、针对性文献差异及可用性证据。
