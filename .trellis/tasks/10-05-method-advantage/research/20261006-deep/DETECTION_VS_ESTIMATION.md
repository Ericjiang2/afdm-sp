# Derivation Package: 检测方向与间距估计方向为何不同

## Target

在固定实际 atom 分支，研究两个未知复增益与一个未知实中心消去后，半间距 δ 的 **real efficient derivative**。对象先限定为完整复信道的 Gaussian oracle；再说明其中哪些不可能性可传递给未知 QPSK 观测。

需要回答：为什么某些固定增益路径可以用盲 C2 在 δ≈T^{-1/2} 检测碰撞，准确估计 δ 却需要额外曲率信息？哪些相位条件使信息再次降阶？三 atom 的精确歧义与四 atom 的唯一性如何进入这件事？

## Status

**COHERENT AFTER REFRAMING / EXTRA ASSUMPTION。** 下文给出解析恒等式、带条件的渐近展开和匹配两点下界；尚待独立证明复核和新一轮 SSH 确定性核验。没有新采样、数值拟合、旧测试重跑或本地科学探针。

三个关键修正：

1. 泛型固定 a,b，b≠0 且 Im(a b̄)≠0 时，单位样本间距信息确为 Θ(δ²)。但不能把 Fisher 倒数直接称为已证明的可实现/统一估计率。
2. 固定 **原始** 同相增益且 b≠0 时，通常信息为 Θ(δ⁴)。四个独立 curve jets 是充分条件，却非必要条件：实际三 atom Dirichlet 曲线的随位置变化列相位也给出非零常数。精确歧义对应 **相位校正后的有效增益** 共线。
3. b=0 要单独处理。更一般地，在三 atom 的某些折点，δ 的一阶 efficient Fisher 信息为正，δ 仍沿完全相同信道的表示曲线发生二阶改变。正 Fisher 信息本身不保证目标在邻域内可辨识。

## Invariant Object

始终使用 Euclidean real Fisher 商空间中的残余长度

\[
J_\delta=\min_{\beta\in\mathbb R}
\|P_\delta f_\delta-\beta P_\delta f_\mu\|^2,
\tag{1}
\]

其中 Pδ 先消去两个复增益的四个实 nuisance 方向。Gaussian oracle 的总 efficient Fisher 信息是 2T Jδ/σ²。不能把某个裸坐标导数、未消 nuisance 的曲率或一个条件均值替换成 (1)。

## Assumptions

- f(μ,δ,g)=g₋w(μ−δ)+g₊w(μ+δ)，w:I→Cⁿ，在当前不跨 clipping、rounding、pruning 分支的开区间内 C⁶；实际固定 Dirichlet 分支是解析的。
- δ>0，两个节点在 I 内。δ 是半间距；全间距为 2δ，改坐标只改常数。
- g₋、g₊ 是未知固定复 nuisance，μ 是未知 **实** nuisance。允许在每个固定 δ>0 对增益作可逆复坐标变换；不把增益当已知。
- 首先观测 Z_t=f+η_t，η_t iid CN(0,σ²I)，σ²>0 已知。或者使用已揭示独立符号的联合 Gaussian 通道，其期望 Fisher 度量相同，见后文。
- rank_C[w,w′]=2，除非某个例子明确另作说明。为取得常用曲率阶，进一步要求 r₂=P₀w″≠0，其中 P₀ 投影到 span_C{w,w′} 的正交补。
- 固定 a=g₋+g₊、b=g₊−g₋ 的 δ→0 路径与允许 a,b 随 δ 变化的路径严格区分。所有 Θ 常数均是点态常数；不对 a→0、b→0、相位共线、支撑边界一致。
- 转到实际归一化 G0 时使用同一个物理 w、同一个原 Gram；不更换成单位增益球或独立等能量模型。a=0 的归一化路径单列。

## Notation

\[
\begin{gathered}
w_\pm=w(\mu\pm\delta),\quad
w'_\pm=w'(\mu\pm\delta),\quad
\mathcal S_\delta=\operatorname{span}_{\mathbb C}\{w_-,w_+\},\\
P_\delta=\Pi_{\mathcal S_\delta^\perp},\quad
r_2=P_0w'',\quad r_3=P_0w''',\quad
\langle x,y\rangle_{\mathbb R}=\operatorname{Re}(x^Hy).
\end{gathered}
\]

所有未带 ± 的 jets 在 μ 求值。Pδ 是 **复** 正交投影，因为每个复 gain 有两个实方向；随后消 μ 必须投影到一个 **实直线**，不能擅自把中心也复化。

## Derivation Strategy

先写严格 Schur-complement/正交投影恒等式，再用对称 secant 基底控制 δ→0 的秩极限；随后分相位和 b=0 情形。三 atom 使用已证的实际有理二次曲线表示得到有限 δ 的精确公式，不用低阶展开猜测是否完全不可辨识。最后构造不同 δ、但低阶信号矩相同的两点，区分局部 Fisher 尺度与统一相对估计的必要条件。

## Derivation Map

1. Gaussian 均值度量 → 消去 complex gains → 实中心投影。
2. 对称 secant 基底 → Aδ、Bδ 的阶 → 泛型 δ² 信息与 raw 同相 δ⁴ 信息。
3. b=0、单路径、主模态取消 → 单独处理投影极限与归一化因子。
4. 实际三 atom → 有效增益相位、精确信息零点与折点反例；四 atom → confluent Cauchy rank。
5. 匹配 Taylor 信号矩 → Gaussian KL 两点下界 → 检测/估计直觉与不能声称的结论。

## Main Derivation

### 1. Identity: 精确消去 nuisance

对实参数 θ_i，Gaussian 均值模型给出

\[
I_{ij}=\frac{2T}{\sigma^2}\operatorname{Re}
\{(\partial_i f)^H\partial_j f\}.
\tag{2}
\]

增益的实切空间恰为 Sδ（视为四维实空间）。在 δ>0 的 rank-two 分支，先用 Pδ 消去增益。记

\[
u=P_\delta f_\delta,\qquad v=P_\delta f_\mu.
\]

则严格地

\[
J_\delta=
\begin{cases}
\|u\|^2-\dfrac{\{\operatorname{Re}(v^Hu)\}^2}{\|v\|^2},&v\ne0,\\[3pt]
\|u\|^2,&v=0.
\end{cases}
\tag{3}
\]

v 很小并不允许把它删掉：最优实投影系数可以发散。只有 v **精确为零** 才适用第二行。

定义

\[
A_\delta=\tfrac12P_\delta(w'_+-w'_-),\qquad
B_\delta=\tfrac12P_\delta(w'_++w'_-).
\]

由 g₋=(a−b)/2、g₊=(a+b)/2，有有限 δ 的精确恒等式

\[
\boxed{u=aA_\delta+bB_\delta,\qquad
v=bA_\delta+aB_\delta.}
\tag{4}
\]

### 2. Lemma: 正确的碰撞 secant 极限

用不退化基底

\[
e_\delta=\frac{w_++w_-}{2}
=w+\frac{\delta^2}{2}w''+O(\delta^4),
\]

\[
h_\delta=\frac{w_+-w_-}{2\delta}
=w'+\frac{\delta^2}{6}w'''+O(\delta^4).
\]

Sδ=span_C{eδ,hδ}；由 rank[w,w′]=2 和投影对满秩基底的光滑依赖，

\[
P_\delta=P_0+O(\delta^2).
\tag{5}
\]

尤其 Pδhδ=0 给出 Pδw′=−δ²Pδw‴/6+O(δ⁴)。代入 Aδ、Bδ，得到

\[
\boxed{A_\delta=\delta r_2+O(\delta^3),\qquad
B_\delta=\frac{\delta^2}{3}r_3+O(\delta^4).}
\tag{6}
\]

Bδ 的系数是 **1/3**，不是直接 Taylor 平均得到的 1/2；相差的一项来自近碰撞 gain 子空间本身的旋转。

### 3. Proposition: 泛型固定增益的间距信息为 Θ(δ²)

若 b≠0，r₂≠0，且 Im(a b̄)≠0，则

\[
u=\delta a r_2+O(\delta^2),\qquad
v=\delta b r_2+O(\delta^2).
\]

将 (3) 展开：

\[
\boxed{
J_\delta=
\delta^2\|r_2\|^2\frac{\{\operatorname{Im}(a\bar b)\}^2}{|b|^2}
+O(\delta^3).}
\tag{7}
\]

证明只需恒等式

\[
|a|^2-\frac{\{\operatorname{Re}(a\bar b)\}^2}{|b|^2}
=\frac{\{\operatorname{Im}(a\bar b)\}^2}{|b|^2}.
\]

虽然 u、v 位于同一条 **复** 曲率直线 C r₂，它们未必位于同一条 **实** 直线。中心只有一个实自由度，这正是剩余信息的来源。

在满足额外 regular-LAN/可实现性条件的点态近似中，δ 的标准误尺度为 1/(√T δ)，相对误差为 1/(√T δ²)。因此 Tδ⁴ 是自然信息量。第 9 节给出相应两点必要条件；这里尚不声称任何具体估计器达到它。

### 4. Proposition: raw 相位共线时再降一阶

设 a=e^{iφ}A、b=e^{iφ}B，A,B∈R，B≠0。即 Im(a b̄)=0，允许反相。定义

\[
q_3=r_3-r_2\frac{\operatorname{Re}(r_2^Hr_3)}{\|r_2\|^2}.
\tag{8}
\]

这是从 r₃ 中消掉 **实** r₂ 方向，不是复 r₂ 方向。式 (4)–(6) 的最优中心系数以 A/B 开始；在 δ² 阶再优化其 O(δ) 修正，得到

\[
u-\beta_*v
=\frac{\delta^2(b^2-a^2)}{3b}q_3+O(\delta^3),
\]

\[
\boxed{
J_\delta=
\frac{\delta^4|b^2-a^2|^2}{9|b|^2}\|q_3\|^2+O(\delta^5).}
\tag{9}
\]

推导：先取 β₀=A/B，δr₂ 项消失，δ²r₃ 系数为 e^{iφ}(B−A²/B)/3；再取 β=β₀+δβ₁，β₁ 的最优化恰好执行 (8)。

若两条 gain 均非零，则 a²−b²=4g₋g₊≠0。因此 q₃≠0 时 Jδ=Θ(δ⁴)。rank_C[w,w′,w″,w‴]=4 是保证 q₃≠0 的充分条件。若 q₃=0，本式只给出首项消失，不能自动指定下一个指数；可能需要更高 jets，也可能精确为零。

对应的形式点态相对误差是 1/(√T δ³)，自然量为 Tδ⁶。它同样不是未经证明的统一可实现率。

### 5. b=0、单路径和主模态取消不是同一个退化

**b=0，a≠0。** 若 r₃≠0，则 u=δa r₂+O(δ³)，v=δ²a r₃/3+O(δ⁴)。虽然 v 比 u 小一阶，仍须投影；β* 可为 O(δ⁻¹)。结果为

\[
\boxed{J_\delta=
\delta^2|a|^2
\left(\|r_2\|^2-
\frac{\{\operatorname{Re}(r_3^Hr_2)\}^2}{\|r_3\|^2}\right)
+O(\delta^4).}
\tag{10}
\]

括号非零时信息为 Θ(δ²)。若 r₃=0，必须考察 v 的更高首项或其是否精确为零，不能代入 (10)。若括号为零，也不能仅凭 (10) 宣称不可辨识。

**单路径。** a=b 或 a=−b 表示 g₋=0 或 g₊=0。此时由 (4) 有 u=v 或 u=−v，Jδ=0 对所有准入 δ 成立；只有 μ±δ 可辨识。

**a=0，b≠0。** 原始未归一化信号的主模态取消，f=δb w′+O(δ³)。若 q₃≠0，(9) 仍给出 raw Jδ=δ⁴|b|²||q₃||²/9+O(δ⁵)。但归一化时 ||f||≈δ|b|||w′||，不能把这一 δ⁴ 直接搬到固定信道能量模型，见下一节。

**固定 b→0 不一致。** 对任意固定非零 raw 同相 b，(9) 可以成立；恰在 b=0 则由 (10) 控制。b=O(δ) 时两项竞争，必须保留完整 (4)。任何只列幂律却省略常数/路径的图都可能误导。

### 6. Identity: 返回实际 G0 归一化

设归一化均值 H=ρ f/||f||，ρ=√(τN)>0；允许 ρ 为未知实 nuisance。其方向微分为

\[
dH=\frac{\rho}{\|f\|}
\left(df-f\frac{\operatorname{Re}(f^Hdf)}{\|f\|^2}\right)
+\frac{f}{\|f\|}d\rho.
\]

由于 f∈Sδ，所有新增径向项都被 gain/幅度 nuisance 消去，故精确地

\[
\boxed{J_\delta^{\rm normalized}
=\frac{\rho^2}{\|f\|^2}J_\delta^{\rm raw}.}
\tag{11}
\]

这使用实际 f 的 Gram 范数，未把增益归一化换成别的 prior。

- a≠0：||f||→|a|||w||>0，(7)、(9)、(10) 的指数不变。
- a=0：上述条件下 raw δ⁴ 乘 δ⁻² 后变为 normalized δ²。此极限 H∝w′ 一般不在原碰撞单径流形上；此前以 a≠0 为条件的碰撞检测展开不适用。
- “两个模型等价”在每个固定 δ>0 指 nuisance 重参数化和投影关系，不意味着在奇异归一化点可忽略一个发散的尺度因子。

### 7. Actual three atoms: 有效相位、精确零点与正 Fisher 折点

引用前轮已推导的实际三 atom 恒等式。对共同支撑 {−1,0,1}，存在固定满列秩复矩阵 L，使

\[
w(\nu)=s(\nu)Lp(y(\nu)),\qquad
p(y)=(1,y,y^2)^T,
\]

\[
y(\nu)=\tan(\pi/N)\cot(\pi\nu/N),\qquad
s(\nu)=\frac{\alpha_0(\nu)}{a_N(\nu)[1-y(\nu)^2]}.
\tag{12}
\]

L 不必酉；下面保留实际 Euclidean 度量。正窗口范数 a_N 是原五点窗口范数，之后实际 cap/prune；(12) 没有重新归一化截断列。

**7.1 为什么三个 complex atoms 仍可能产生 raw 同相 δ⁴ 信息。** 对 (12) 求导，模 span_C{w,w′} 有

\[
r_3=C r_2,\qquad
C=3\left(\frac{s'}s+\frac{y''}{y'}\right).
\tag{13}
\]

这是因为 p‴=0，w″ 的 p″ 系数为 s(y′)²，而 w‴ 的 p″ 系数为 3s′(y′)²+3s y′y″。在当前实际分支，s 的相位导数为

\[
\operatorname{Im}(s'/s)=\omega_N=\pi(N-1)/N,
\]

其余因子实且不为零。因此 Im C=3ω_N≠0，

\[
q_3=i\operatorname{Im}(C)r_2,
\quad
J_\delta^{\rm raw}
=\delta^4\omega_N^2
\frac{|b^2-a^2|^2}{|b|^2}\|r_2\|^2+O(\delta^5)
\tag{14}
\]

对固定 raw 相位共线、b≠0、双非零 gain 成立。可见“没有第四个 complex atom，所以该 δ⁴ 首项必为零”是错误推断：实际 Fisher 空间是实空间。

raw b=0 时，将 (13) 代入 (10)，其括号为 ||r₂||²(Im C)²/|C|²>0，故该固定 raw 路径的点态信息为 Θ(δ²)。

**7.2 有限 δ 的精确信息公式。** 令 ν₁=μ−δ、ν₂=μ+δ，λ_i=g_i s(ν_i)，y_i=y(ν_i)，并定义

\[
c_i=\lambda_i y'(\nu_i),\quad
A_e=c_1+c_2,\quad B_e=c_2-c_1,\quad
r=P_\delta L(0,0,1)^T.
\]

gain 重参数化 λ_i 的导数差都在 Sδ 内，故不影响 quotient。由 p(y₂)−p(y₁)=(y₂−y₁)(0,1,y₁+y₂)^T 得

\[
P_\delta Lp'(y_1)=(y_1-y_2)r,\qquad
P_\delta Lp'(y_2)=(y_2-y_1)r.
\]

于是

\[
u=(y_2-y_1)A_e r,\qquad
v=(y_2-y_1)B_e r,
\]

\[
\boxed{
J_\delta=(y_2-y_1)^2\|r\|^2
\begin{cases}
\dfrac{\{\operatorname{Im}(A_e\overline{B_e})\}^2}{|B_e|^2},&B_e\ne0,\\[4pt]
|A_e|^2,&B_e=0.
\end{cases}}
\tag{15}
\]

并且

\[
\operatorname{Im}(A_e\overline{B_e})
=2y'(\nu_1)y'(\nu_2)\operatorname{Im}(\lambda_1\bar\lambda_2).
\tag{16}
\]

所以一般精确信息零点是 **有效 gain 相位共线** Im(λ₁λ̄₂)=0 且 B_e≠0。实际原始坐标中，该条件是

\[
\operatorname{Im}\{g_-\bar g_+
e^{i\omega_N(\nu_1-\nu_2)}\}=0.
\tag{17}
\]

固定 raw 同相 gain 在小正 δ 时一般不满足 (17)；其有效相位差为 O(δ)，因此 (15) 与 (14) 一致。固定 effective 同相 λ 则对应随 δ 变化的 raw gain，不能与固定 raw 路径混为一谈。

**7.3 折点：正的一阶信息并不消除精确歧义。** 若 c₁=c₂≠0，则 B_e=0 而 A_e≠0，(15) 给出 Jδ>0。但 λ₁、λ₂ 此时相位共线，前轮的精确连续同信道歧义仍成立。

这个现象不是矛盾。取最简单的三 atom 曲线 w(ν)=(1,ν,ν²)，原点 μ=0、b=0、a≠0，则

\[
f=(a,0,a\delta^2).
\]

对任意充分小 h，设置

\[
\mu'=h,\quad \delta'=\sqrt{\delta^2+h^2},\quad
a'=a,\quad b'=-ah/\delta'.
\tag{18}
\]

直接代入得到完全相同 f，且两条 gain 仍非零。δ′(0)=0，但 d²δ′/dh²=1/δ>0。在原点中心的一阶导数可以由 gain 吸收，δ 的一阶导数不能；可是在每个邻域都存在不同 δ、完全相同数据律。因而不能在整个邻域上对 δ 一致估计。

实际 cot 曲线也有同类折点，而不只这个示例。写 M_j=Σλ_i y_i^j，公共相位去掉后取实数，歧义曲线满足

\[
F(\mu,\delta)=M_2-(y_1+y_2)M_1+y_1y_2M_0=0.
\]

在 c₁=c₂=c≠0 点，Fμ=0、Fδ=−2c(y₂−y₁)≠0。令 k=π/N、t₀=tan(π/N)，由 y′=−k(t₀²+y²)/t₀ 得

\[
\frac{d^2\delta}{d\mu^2}
=-\frac{2k(t_0^2+y_1y_2)}{t_0(y_2-y_1)}>0.
\tag{19}
\]

故实际三 atom 的 balanced-effective 点也是间距沿歧义曲线的局部极小折点。Schur-complement 的正值只是一阶切空间事实；它没有证明 δ 是均值像空间上的局部单值函数。

### 8. Four common atoms: 第四 jet 既控制稳定性，也去掉精确二径歧义

对共同保留的四个合法 atom，实际列除以非零列标量后为 Cauchy 形式 1/(1−a_m z(ν))，a_m 互异、z′(ν)≠0。在一个节点取 0–3 阶导数，经可逆三角列变换可化为

\[
\frac{1}{1-a_mz},\quad
\frac{a_m}{(1-a_mz)^2},\quad
\frac{a_m^2}{(1-a_mz)^3},\quad
\frac{a_m^3}{(1-a_mz)^4}.
\]

若其线性组合在四个不同 a_m 为零，乘 (1−az)^4 后是次数至多 3 的多项式并有四个根，所以恒零；按幂次/在 a=1/z 的逐次消元可知四个系数全零。因此

\[
\operatorname{rank}_{\mathbb C}[w,w',w'',w''']=4.
\tag{20}
\]

同理，两个不同节点处的 {w₋,w₊,w′₋,w′₊} 也独立：乘 (1−az₁)²(1−az₂)² 后得到三次多项式，在两个极点的值与一阶导数依次消去四个系数。这给双非零 gain 下有限 δ 的局部满秩；前轮的四列 full-spark 论证进一步给固定分支内全局二径分解唯一性。

因此四 atom 使 (9) 的 q₃ 必非零，也排除三 atom 的精确同信道连续歧义。但它不让小 δ 的信息常数自动有正的统一下界。

一个纯代数例子是 w(ν)=(1,ν,ν²/2,ν³/6)，μ=0；此时 r₂=e₂、r₃=e₃：

| raw gains | a,b | 单位几何信息首项 |
|---|---|---|
| (1,i) | 1+i, −1+i | Jδ=2δ²+O(δ³) |
| (1,2) | 3,1 | Jδ=(64/9)δ⁴+O(δ⁵) |
| (1,1) | 2,0 | Jδ=4δ²+O(δ⁴) |
| (0,1) | 1,1 | Jδ=0，精确单路径混淆 |

这是手算 jet 例子，不是实际 AFDM 数值验收；实际验收应使用同一个冻结物理 w 和 Gram。

### 9. Proposition: 匹配两点给必要尺度；Fisher 不是完整 rate theorem

对两个固定均值 f、f′，Gaussian oracle 的精确 KL 是

\[
D(P_f^{\otimes T}\Vert P_{f'}^{\otimes T})
=T\|f-f'\|^2/\sigma^2.
\tag{21}
\]

以下构造使用两个不同真实参数点。若 δ′/δ=c≠1 固定而 KL 有界，就不可能在同时包含这两个序列的参数集合上让相对估计误差一致趋零；若 KL→0，则它们连检验都无法分开。Gaussian 两点或 Bretagnolle–Huber 下界足够，不依赖 CRLB 的无偏假设。

**9.1 一般 unknown-gain 构造，差为 O(δ²)。** 固定 c>0、c≠1，取

\[
\delta'=c\delta,\quad\mu'=\mu,\quad a'=a,\quad b'=b/c.
\]

两点的 w 和 w′ 系数完全相同，而

\[
f'-f=\frac{a(c^2-1)}2\delta^2w''+O(\delta^3).
\tag{22}
\]

因此 a≠0 的 raw/normalized 正则支路都存在 KL=O(Tδ⁴) 的固定比例间距备择。Tδ⁴→∞ 是这类 nuisance 邻域上统一相对一致性所需的必要条件；本构造不证明充分性。

**9.2 raw 相位共线 b≠0，可再匹配二阶矩。** 去掉公共相位后把 a,b 当作实数。选择 h=h(c) 为以下方程在 c=1、h=0 附近的实根：

\[
a(c^2-h^2)+2bh=a.
\tag{23}
\]

b≠0 保证隐函数定理适用。取

\[
\mu'=\mu+h\delta,\quad\delta'=c\delta,\quad
a'=a,\quad b'=(b-ah)/c.
\tag{24}
\]

围绕原 μ 展开，两点的 0、1、2 阶位置矩依次为 a、δb、δ²a，完全相同；故 f′−f=O(δ³)。c 充分接近 1 时，增益和中心仍在原 nuisance 邻域内，双非零条件保持。a≠0 下归一化是局部光滑映射，结论也传递给实际 G0。于是得到 Tδ⁶→∞ 的对应必要条件。

**9.3 b=0 再次警示局部 Fisher 的限制。** (23) 虽不能在 c=1 按通常隐函数导数解，但取任意接近 1 的 c>1，令

\[
h=\sqrt{c^2-1},\qquad b'=-ah/c,
\tag{25}
\]

仍严格匹配三个低阶矩，差为 O(δ³)。所以即使四 atom 的 b=0 点态 Fisher 为 Θ(δ²)，在包含其完整 unknown-gain 邻域的统一相对问题中，仍存在 Tδ⁶ 的两点必要障碍。这里 nuisance 的变化随 c−1 是平方根级，而不是可被一阶 Schur 展开一致控制的线性级。

结论应写成：点态 Jδ 给局部线性信息；triangular-array LAN、弱 nuisance 的集中速度、非线性余项和精确可辨识性决定能否把它升级为相对估计率。不能仅由 (10) 宣布 b=0 在完整未知增益类上达到 T^{-1/4} 相对分辨边界。

**9.4 哪些可传递给 blind Y。** 若真实通道为 Y_t=H⊙x_t+ε_t，符号被 oracle 揭示，符号律与参数无关且 E|x_{t,n}|²=1，则联合实验严格满足

\[
D(P_{H,X}^{(T)}\Vert P_{H',X}^{(T)})
=T\|H-H'\|^2/\sigma^2.
\tag{26}
\]

删掉 X 后由数据处理不等式 KL 不增。因此 (22)–(25) 给出的 **必要下界** 能传给同一物理 H 的未知 QPSK 观测。另一方面，oracle Fisher 常数、局部可实现性或完整 H 分解算法不能直接当成 blind Y 的可实现算法/率。

### 10. 检测为何能 root-T：极限 nuisance 切空间换了

在 a≠0 的固定 gain 路径，

\[
f=a w+\delta b w'+\tfrac12\delta^2a w''+\cdots.
\]

零间距 null 的局部 nuisance 空间只有 complex w 和一个 real a w′ 方向；Im(b/a) 的 w′ 分量不能被 null 的实中心吸收。因此对 raw 相位泛型路径，距离 null 为 O(δ)，已有实际 N4 blind C2 可以观测对应的一阶功率差，形成点态 T^{-1/2} 检测尺度。

但对每个正 δ 的双径估计问题，两条未知 complex gain 张成的 secant 空间在极限中趋向 **整个 complex span{w,w′}**。它已把刚才的两种 w′ 实方向都消掉。间距估计要到 w″ 曲率才重新出现信息；raw 相位共线时，实中心还能吸收曲率首项，进一步依赖第三 jet 的实横向分量。

这不是统计量“丢失效率”造成的矛盾，而是两种任务的 nuisance 类不同：

- 检测要判断是否偏离低维碰撞流形。
- 估计要在所有正间距的未知增益表示之间区分 δ，并消掉它们互相补偿的位置/增益变化。

## Remarks and Interpretation

1. **秩极限优先于 Taylor 系数。** 两列 w₋、w₊ 合并时，用原基底直接求逆会把 secant 方向藏在病态矩阵里。先改成平均与差商，才能看到 gain nuisance 仍在极限保留 w′。
2. **真实参数用实几何。** 一条 complex 曲率直线等于两个实方向；未知实中心只能拿走其中一个。把所有投影都做成复投影会错误抹掉泛型信息。
3. **坐标 gauge 与物理路径不同。** w→e^{iψ(ν)}w、g_i→e^{-iψ(ν_i)}g_i 不改变同一信道点的 efficient Fisher；但“在新坐标中固定增益再让 δ 变化”一般已换了一条物理路径。raw 与 effective 相位必须连同路径一起交代。
4. **唯一性、稳定性、可检出性是三个问题。** 四 atom 可以保证无噪声唯一性，同时允许 δ⁴ 小信息；三 atom 可以精确检测单径/双径，同时不能在有效相位共线集合上唯一恢复 δ。
5. **正 Fisher 不是万能证书。** 折点表明一阶可估方向未必来自邻域单值目标。面对奇异模型，先找同数据分布的曲线，再讨论 CRLB，比只计算矩阵逆更可靠。
6. **PDP 改变权重，不删除几何反例。** 实际正 PDP 的复 Gaussian 方向对所有双非零复方向都有支撑；raw/effective 共线集合通常概率零，但仍妨碍对任意未知 gain 的统一保证。若改为已知 gain prior 的边际模型或多个独立块，必须重新定义统计实验。

## Boundaries and Non-Claims

- 已证明的是投影恒等式、指定非退化条件下的信息阶、具体精确反例和两点必要条件；没有给出完整 minimax 相图、三角阵 LAN 统一定理或达到边界的 δ 估计器。
- 不声称 blind Y 与 Gaussian 完整 H 实验等价；只使用已揭示符号模型的精确 KL/Fisher 身份来传递必要条件。
- 不把同 raw 相位、同 effective 相位、b=0、a=0、零路径或支撑改变混为一个退化集合。
- 不把 fixed unknown-gain nuisance 结论回写成实际已知 prior 的 iid 重生边际信息定理；旧 q log(1/q) 研究属于另一个实验。
- 未认证首创。这里用到的是 Gaussian 均值 Fisher 几何、Schur 补、confluent Cauchy/Prony、奇异参数和两点下界的标准思想；本稿的任务是把它们按实际冻结 AFDM 分支组合并查清适用边界。

## Open Risks and Minimal SSH Verification

后续只需新登记、零随机观测的确定性核验；不需要重跑前轮 power 实验。

1. 在实际 N4/三 atom 与 N16/至少四共同 atom 的固定 μ 上，用冻结物理 w、Gram 和高精度/解析导数，比较直接 real Jacobian Schur 残余与精确 (4)。必须保存 singular values，不用 jitter。
2. 对预先固定的 generic、raw 同相 b≠0、raw b=0、单路径、a=0 五类 gain，验证 (7)、(9)、(10)、(11) 的**系数残差**。可以报告缩放残余，但不能仅靠 log-log 拟合指数。保留浮点不可靠的小 δ 点。
3. N4 验证 (13) 的 complex 比值及 Im C=3π(N−1)/N；分别构造满足和不满足 (17) 的 gain，核对 (15)。不要用“raw 同相”代替 effective 相位共线。
4. 用前轮精确矩表示构造 balanced-effective 折点，核对同 H 曲线、δ 的一阶零变化及二阶正变化 (19)。同时保存 Jδ>0 与 Prony determinant=0，明确这是预期现象。
5. 四 atom 固定 jets/confluent columns 核验 rank，并检查 (24)、(25) 的 0/1/2 阶矩严格匹配及 cubic remainder；无需任何新随机 gain、符号或噪声。

源码/容差/网格/预算需由主会话收敛、独立复核并提交后才能 SSH GO。本文件只拥有解析结论，不直接启动上述工作。

## Sources Used

- 前轮 `research/20261006-important/algebra/ALGEBRA_CANDIDATES.md`：实际三 atom 变换、有效相位条件、连续歧义与四 atom Cauchy 证明。
- 前轮 `research/20261006-important/coherence/THEORY_CANDIDATES.md`：a≠0 的实际归一化碰撞导数、盲 C2 一阶见证与检测边界。
- 已加载冻结实现 `afdm_efficient_information.prior_likelihood`、`afdm_higher_order_information.prior`、`production_prior.normalize_gain` 及对应实际权重约定；本轮未执行这些数值核。
- 本輪没有外部检索；经典文献定位由主会话合并处理，不在这里凭印象认证引用或新颖性。
