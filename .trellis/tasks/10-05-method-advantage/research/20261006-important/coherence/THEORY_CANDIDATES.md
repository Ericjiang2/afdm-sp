# Research: 相干块中的碰撞可辨识性与跨符号见证

- Query: 同一固定信道的多符号，以及 B 个独立信道块各 T 个符号，是否改变原 G0/P2/N4 碰撞边界；固定未知复增益与中心后哪些变化可观测？
- Scope: internal；实际冻结 G0、共同 rounded delay=0、当前三 atom 分支的纯数学推导。
- Date: 2026-10-06
- Status: COHERENT AS STATED；下述两项命题已给完整解析推导，尚未经独立正式审查或数值检验。
- Ownership: 只写本 coherence 研究目录；未修改代码、规范、任务状态、原结果或 Git；未 SSH、采样、仿真或拟合。

## Findings

最重要的改变是：**同一个实际信道被重复观测时，旧 C2 功率差不再是无均值信号的基线。它对几乎所有固定复增益具有 O(δ) 的条件均值，仅用未知 QPSK 接收数据就能以点态 T^{-1/2} 尺度检测碰撞。** 原独立重生模型把该有符号随机效应逐符号平均掉，故仍只有 q log(1/q) 的边缘方向。两者是不同实验，不是原模型获得了更好分辨率。

第二个可证明结果是：保留块结构后，两个不同符号的 C2 乘积具有严格正的 q log(1/q) 均值，且 null 方差随 T(T−1) 的倒数下降。它为固定 T 的块边缘实验给出显式、只用接收数据、对全部 null nuisance 正交的见证。T 增长时还存在 Θ(q) 的块间随机效应方差，不能把 BT 当成独立样本数或无限外推固定 T 的 LAN。

### Target / Invariant Object

研究对象是可观测概率实验，而非某个 gain 坐标的形式 Fisher 信息。依赖链为：真实 Gram 归一化 → 固定信道的 null 流形距离 → 可观测功率差 → 相干块内 U 统计 → 与旧边缘 q log 方向的关系。

### Assumptions / Notation

1. N=4，G0，P=2，两个物理 Doppler 为 μ−δ、μ+δ，共同 rounded delay=0；局部固定三 atom 支撑 −1,0,1，远离 clipping/pruning/rounding 断点。μ∈[.22,.42] 的 null 支撑已由旧理论核实；局部 nuisance 流形投影取 μ 为该区间内点。涉及实际 PDP 的局部边缘展开仍要求固定其离散分支。
2. 单径时间响应为 w(ν)∈C⁴，来自冻结 Dirichlet 窗口先归一化再裁剪/剪枝。Bδ=[w(μ−δ),w(μ+δ)]，Rδ=BδᴴBδ/N。
3. 固定信道分析使用 raw 复增益 g=(g−,g+)；实际归一化信道和观测为

   Hδ(g)=√(τN) Bδg/‖Bδg‖，  Yt=Hδ(g)⊙xt+εt，  xt=AᴴXt。

   Xt 的四个 DAFT 坐标独立均匀 QPSK，t 间独立；εt∼CN(0,sI)，s>0，与所有其余变量独立。τ>0。这正是 g/√(gᴴRδg) 的原始 Gram 归一化，不是 ‖g‖=1 的替代 prior。
4. 一个相干块内 g、μ、δ、τ、s 固定。多个块分析中 μ、δ、τ、s 共同，gb 可以固定任意，也可以按实际 PDP/Gaussian 原始律独立重生。两种情形分别标出。
5. 固定 gain 的碰撞展开要求 a=g−+g+≠0。记 z=(g+−g−)/a，ζ=Im z。a=0 是取消主模态的奇异路径，不能代入本展开。
6. b=w′−w(wᴴw′)/‖w‖²，u0=w/‖w‖，u1=b/‖b‖，均在 μ 求值；旧实际分支已有 b≠0。q=δ²，r=q log(1/q)。

### 统一余项与渐近范围约定

- 除非单独声明，δ↓0，N=4 固定；μ 位于一个固定平滑物理/PDP 分支内部的紧集，且该紧集到其边界有正距离。τ、s 分别位于严格正的紧区间。所有局部 nuisance 投影均取公开 null 域内点。由连续性，‖w‖、‖b‖ 以及 (16) 的 ‖c‖ 在所取实际紧集上有正下界。
- 命题 1 的 O_g、o_g 以 raw g 固定且 a≠0 为前提；常数与允许的 δ 邻域可依赖 g。没有给出 a→0 的统一余项，也没有给出 ζ→0 时的统一检测常数或 T^{-1/2} 保证。固定 B 的结论固定整组 g1,…,gB，常数可依赖该组与 B。
- 实际边缘命题在上述固定 PDP 分支上只有有限个正 D，权重局部固定；谱与矩展开的常数可以对该有限支撑统一。式 (19) 的均值恒等式没有 T，O(q) 对全部 T≥2 相同；式 (23) 的 Θ 上下界由 (22) 与一致有界且正定的 ΣH 给出，常数可取独立于 B≥1、T≥2。它们不自动构成联合 B,T 极限下的正态近似。
- (11)–(12) 固定一个 gain 实现而 T→∞；(13) 固定 B；(24)–(25) 则固定 T≥2 而 B→∞。块密度的 L² 包络、余项、DQM/LAN 以及 (24) 的近似误差允许依赖 T，没有宣称在 T 增长时统一有效。
- 式 (24) 明确采用 rB=t/√B、固定 t≥0；t=0 为 null。一般双重增长仅保留精确方差 (22)、统一矩阶 (23) 与明确标注的充分条件 (26)。

## 命题 1：固定信道的泛型碰撞具有可实现的 T^{-1/2} 检测尺度

### 1.1 最强实验先行：已知符号只降低 H 的测量噪声

给定所有 xt，令 Qt=diag(|xt,0|²,…,|xt,3|²)，QT=ΣtQt。若每个对角元均正，Gaussian 线性实验的充分统计量为

\[
\widehat H_n={\sum_t\overline{x_{t,n}}Y_{t,n}\over\sum_t|x_{t,n}|^2},
\qquad \widehat H\mid H,x\sim\mathcal{CN}(H,sQ_T^{-1}).
\tag{1}
\]

证明是逐坐标完成平方；拟合残差与 H 无关。这里固定 s；若 s 也未知，应保留残差平方和，不能声称 Ĥ 单独对 s 充分。若某坐标总激励为零，该坐标不可恢复，不能以逆或 jitter 掩盖。

在平衡设计 QT=TI 时，(1) 精确化为 H+CN(0,sI/T)。对实际随机且被 oracle 揭示的 QPSK，E|xt,n|²=1，故 QT/T→I 几乎必然。**同一块有 T 次测量，只有一个 H；它不等价于 T 个独立 gain 实现。**

更强的“直接给出精确 H”oracle 只剩物理分解问题：增加 T 无法消除两个参数给出同一 H 的歧义。尤其 g+=0 时，Hδ(g) 正好是中心 μ−δ 的单径 null，任何数据量都不能一致地区分。实际连续 prior 赋该事件零概率，不等于未知任意增益下的 uniform 保证。

### 1.2 消去未知 gain 幅相与实中心

原始曲线的 Taylor 展开是

\[
B_\delta g=a\{w+\delta z w'+\tfrac12\delta^2w''+O(\delta^3)\}.
\tag{2}
\]

记 θ=arg a、c=wᴴw′/‖w‖²。归一化映射的导数给出

\[
H'_0={\sqrt{\tau N}e^{i\theta}\over\|w\|}
\{z b+i\operatorname{Im}(zc)w\}.
\tag{3}
\]

null 是局部流形 M0={√(τ′N)e^{iθ′}u0(μ′)}。其真实切空间对应复尺度以及一个**实** μ′ 方向；除去全局相位与尺度后，中心只能吸收 (Re z)b，无法吸收 i(Im z)b。实内积 Re(vᴴu) 下 b 与 ib 正交，且二者都与复直线 Cw 正交。因此

\[
\operatorname{dist}(H_\delta(g),\mathcal M_0)
={\sqrt{\tau N}\,\|b\|\over\|w\|}|\zeta|\,\delta+O(\delta^2)
\quad (\zeta\ne0).
\tag{4}
\]

这里是当前分支的局部距离。null 在公开 μ 区间没有远处重复点：旧功率参数 Pa(μ) 严格单调，故局部结果不会被该区间内另一个 null 分支抵消。

如果 ζ=0，取 μ′=μ+zδ 就能吸收一阶，距离为 O(δ²)。更具体地，在 z∈R、z²≠1 且 w,w′,w″ 复线性无关时，二阶法向分量为

\[
{\sqrt{\tau N}e^{i\theta}\over2\|w\|}
(1-z^2)\,P^{\mathbb R}_{\{w,iw,w'\}^{\perp}}w''\,\delta^2,
\tag{5}
\]

故距离 Θ(δ²)。实际三 atom 的复线性无关由并行 [algebra 研究第 6 节、式 (19)–(20)](../algebra/ALGEBRA_CANDIDATES.md) 的可逆二次曲线表示推出；本命题泛型结论 (4) 不依赖该额外结果。z=±1 等价于某一路 gain 为零，恰是前述精确 null。固定 raw 同相与有限 δ 下“吸收 Dirichlet 列相位后的有效 gain 同相”不是同一个例外集；后者导致的全局分解歧义交由该独立 algebra 记录第 3 节讨论。分离度不可唯一估计不等于无法检测是否为双径，该文件也区分了这两项任务。

### 1.3 Oracle 不可能性及其边界

令 Pδ,T^X 是把真实符号也给接收机的联合实验。相同符号律下 Gaussian 条件 KL 及 E|xt,n|²=1 给出精确恒等式

\[
D(P_{\delta,T}^X\|P_{0,T}^{X,H_*})
={T\over s}\|H_\delta-H_*\|^2.
\tag{6}
\]

因而固定 a≠0 时 Tδ²→0，连已知符号 oracle 都不能把 Hδ 与碰撞 H0 区分，TV→0；未知数据更不可能。ζ=0 时取上述移动中心 null，Tδ⁴→0 同样给出不可能性。这说明不能给任意未知复增益统一宣称 T^{-1/2}，也不能把 gain 任意接近零的情况排除后不说明。

直接精确观测 H 与有限噪声实验不同：对 (4) 的非零分量，任何充分小 δ>0 的 H 都在 null 流形之外；零噪声下可精确判断。这是零噪声与 δ→0 极限不交换的一个具体表现。

### 1.4 真实 N4 分支的 blind 一阶见证

定义接收数据功率差

\[
d(Y)=(|Y_0|^2-|Y_1|^2,\ |Y_2|^2-|Y_3|^2)^T,
\qquad \Delta(H)=E[d(Y)\mid H].
\]

独立 QPSK 通过酉 DAFT 满足 E|xn|²=1；噪声功率相同，故精确地

\[
\Delta(H)=(|H_0|^2-|H_1|^2,\ |H_2|^2-|H_3|^2)^T.
\tag{7}
\]

每个 null 的 Δ 恒零，无需知道或估计 μ、τ、s、g、符号或全局相位。

现在给出可核对的实际闭式系数。置 t=πμ/4、ξ=tan t、K=1+2ξ²+5ξ⁴。按冻结 Dirichlet 系数比值，w(μ)=γ(μ)R(μ)，γ≠0 是含原窗口正归一化及列相位的公共因子，且

\[
R={1\over1-\xi^2}
\begin{pmatrix}
1-3\xi^2-2i\xi\\
1-3\xi^2+2i\xi\\
1+\xi^2+2i\xi\\
1+\xi^2-2i\xi
\end{pmatrix},\quad
\|R\|^2={4K\over(1-\xi^2)^2},\quad
\xi'={\pi\over4}(1+\xi^2).
\tag{8}
\]

证明 (8)：c±=sin t/sin(t±π/4)=√2ξ/(ξ±1)，去掉公共因子后 Rn=c−exp(−iψn)+1+c+exp(iψn)，ψn=πn/2−π/4。代入四个 ψn 即得，不涉及更换窗口或重新列归一化。

对于 (7) 中一对坐标 i,j，null 已有 |wi|²=|wj|²，故 (3) 的归一化漂移和公共因子 γ′ 的贡献在功率差中消去：

\[
\Delta'_{ij}(0)
={2\tau N\over\|w\|^2}
\operatorname{Re}\{z(\bar w_iw'_i-\bar w_jw'_j)\}.
\tag{9}
\]

由共轭对结构，括号为纯虚数。直接对 (8) 求导得到

\[
\operatorname{Im}(\bar R_0R'_0)
=-{2(1+3\xi^2)\xi'\over(1-\xi^2)^2},\qquad
\operatorname{Im}(\bar R_2R'_2)
={2\xi'\over1-\xi^2},
\]

各自的共轭配对坐标虚部取相反数。将这些式子与 N=4 代入 (9)，有

\[
\boxed{\Delta(H_\delta(g))=\delta\zeta\,k(\mu,\tau)+O_g(\delta^2),\quad
k={2\pi\tau(1+\xi^2)\over K}
\begin{pmatrix}1+3\xi^2\\-(1-\xi^2)\end{pmatrix}.}
\tag{10}
\]

当前分支 0<ξ<1，两分量都非零。O_g 的常数不对 a→0 统一；禁止把这个点态展开在实际 prior 下平方后直接积分。

### 1.5 只消费观测的检验与点态最优尺度

在同一块求 d 的样本均值 d̄ 和经验协方差 Σ̂，令

\[
Q_T=T\bar d^T\widehat\Sigma^{-1}\bar d.
\tag{11}
\]

这与旧 C2 的代数形式相同，但样本现在来自**固定同一信道**。null 下条件 d 独立同分布，均值零。Σ0 正定：给定 x,H 后，每个复 Gaussian 噪声坐标的功率方差为 s²+2s|Hnxn|²，两对坐标互不相交，故 Cov(d|H)≽2s²I。有限 QPSK 与 ‖H‖²=τN 给出全部所需有限且局部统一的矩。

于是 null 下 QT⇒χ²₂。固定 a≠0、ζ≠0，沿 δT=c/√T，有三角阵 CLT、Σ̂→Σ0，且

\[
Q_T\Rightarrow\chi^2_2(\lambda),\qquad
\lambda=c^2\zeta^2k^T\Sigma_0^{-1}k>0.
\tag{12}
\]

δT→0 且 √TδT→∞ 时检验一致。结合 (6)，T^{-1/2} 是这些固定 gain 路径的点态可实现检测边界。符号、中心、gain、τ 和 s 的真值均不进入 (11)；它们只进入功效描述。有限 T 的 χ² 误差与所需样本常数尚未测量；不能把渐近边界称为已经证实的有限样本优势。

这只是 H0:δ=0 的检测，不是分离度 δ 的正则估计率：局部条件信号只含 δζ，不能把 gain 比率当已知除掉。ζ 很小、a 很小、支持改变、跨块漂移都会破坏统一常数。

### 1.6 B 个固定 gain 块和共同中心

对固定 B 个块，各有 ab≠0，zb=(gb,+−gb,−)/ab。已知符号且平衡设计时，投影 B 个独立相位与一个共同实 μ 后，堆叠信道距离平方的一阶系数为

\[
\delta^2{\tau N\|b\|^2\over\|w\|^2}
\left[\sum_b(\operatorname{Im}z_b)^2+
\sum_b(\operatorname{Re}z_b-\overline{\operatorname{Re}z})^2\right]+o(\delta^2).
\tag{13}
\]

理由是归一化后每块相同范数，第一阶需最小化 Σb|zb−v|²，v∈R，最优 v 为 Re zb 的均值。即使每个 zb 都实，只要块间中心漂移系数不同，一个共同中心也不能同时吸收它们。这一额外方向目前仅在 oracle 几何中证明；(11) 的一阶 blind 见证只利用 Im zb，不能声称它也捕获该实方向。

对一般情形，固定 B 时 ΣbQT,b 的 null 极限为 χ²₂B，沿 δ=c/√T 的非中心量为 c²kᵀΣ0⁻¹k Σb(Im zb)²。所有块的同向均值直接相加会发生 gain 相位抵消，按块先平方保留的是相干效应。

### 1.7 两种 mode 的 null 校准库可严格共用

在 δ=0，实际归一化把任意 PDP/gain 都化为 Ht=√(τN)e^{iθt}u0(μ)。对任意固定相位序列 θ1,…,θT，有

\[
|Y_{t,n}|^2
=\left|\sqrt{\tau N}u_{0,n}x_{t,n}
+e^{-i\theta_t}\epsilon_{t,n}\right|^2.
\tag{13a}
\]

独立圆 Gaussian 噪声在逐符号相位旋转后联合律完全不变，并保持与全部 QPSK 独立；条件于相位序列的整个功率数组分布都不依赖该序列。因此共享一个 θ 的 coherent mode 与逐符号独立 θt 的 regenerate mode，具有**完全相同的 null 联合功率数组分布**，而不只是单观测边缘相同。

任何仅由该数组构造的统计——包括 (11) 的两维功率差、样本协方差、数值失败判据、nested T 的全部统计——在两种 mode 的 null 联合分布严格相同。故可以共用同一 (μ,τ,s,T) 的独立校准库；无须重复生成另一个 mode 的 null 库。该结论不把不同 μ 或 s 的 null 混成一个分布，也不允许把校准组当评估组。nested T 复用同一组前缀有合法配对意义，但如果从多个 T 中选择最有利结果，需按预登记规则处理多重比较；不能当作互相独立的新校准样本。

δ>0 时，两种 mode 的单观测边缘仍相同（每个符号看到同一个原实际 prior），但 joint 不同：coherent 的 Δ(H) 在整组固定，regenerate 的各 Δ(Ht) 独立重生。该区别正是主实验要测量的效应，不是符号能量或噪声边缘改变。

## 命题 2：跨符号 C2 乘积是 q log(1/q) 的可观测块见证

本节 gb 在块间按原实际 prior 独立重生：给定实际有限正 PDP D，gb=D^{1/2}zb，zb∼CN(0,I₂)，然后沿用原 Gram 归一化。为避免符号冲突，本节的 zb 是 Gaussian 基变量；命题 1 的 gain 比率只在显式引用 (10) 时使用。

### 2.1 跨符号 U 统计及无 nuisance 的 null 均值

T≥2 时，在每块定义

\[
U_T={1\over T(T-1)}\sum_{t\ne u}d(Y_t)^Td(Y_u)
=\|\bar d\|^2-{\operatorname{tr}\widehat\Sigma\over T},
\tag{14}
\]

第二式使用分母 T−1 的无偏样本协方差。条件独立性给出**精确**恒等式

\[
E[U_T\mid H]=\|\Delta(H)\|^2.
\tag{15}
\]

每个 null H 都有 Δ=0，故 E0UT=0 对全部 μ,τ,s 成立；噪声方差被跨符号独立性消去，并非估计后扣除真噪声。独立逐符号重生时，右侧变成 EΔ(Ht)ᵀEΔ(Hu)=0；同一公式便不再含此信号。这正是新增观测结构。

### 2.2 从原真实小模态概率律推导正系数

记

\[
\Gamma=E_D\left[{4D_1D_2\over(D_1+D_2)^2}\right]>0,
\quad \kappa=\Gamma{\|b\|^2\over\|w\|^2},
\quad c=\begin{pmatrix}
u_{1,0}\bar u_{0,0}-u_{1,1}\bar u_{0,1}\\
u_{1,2}\bar u_{0,2}-u_{1,3}\bar u_{0,3}
\end{pmatrix}.
\tag{16}
\]

可选 w 的公共相位使去相位时间向量按 (0,1)、(2,3) 成共轭对。此时 wᴴw′ 为实数，b 同样成共轭对，因此 c 是纯虚非零向量。(8) 的两个虚 Wronskian 非零给出实际 c≠0，而非浮点 rank 判断。

固定 D 和 δ>0 时，去掉两条路径各自的 Dirichlet 列相位后，B̃δ 的两对行互为共轭，B̃δᴴB̃δ 实对称。D 为实对角，故可取左右奇异向量，使两个左奇异向量 uj,δ,D 各自都满足上述共轭对结构。列相位吸收到独立圆 Gaussian gain 不改变其真实分布。

旧密度理论的精确谱表示因此适用：

\[
H=\sqrt{\tau N}e^{i\theta}
\{\sqrt{1-V}\,u_{0,\delta,D}+\sqrt V e^{i\phi}u_{1,\delta,D}\},
\quad V={\rho_D E_1\over E_0+\rho_D E_1},
\]

其中 E0,E1 独立 Exp(1)，φ、θ 独立均匀，ρD=cDq+O(δ³)，cD=[4D1D2/(D1+D2)²]‖b‖²/‖w‖²。其精确密度为

\[
f_\rho(v)={\rho\over[\rho+(1-\rho)v]^2},\quad0<v<1,
\qquad EV=\rho\log(1/\rho)+O(\rho),\quad EV^2=O(\rho).
\tag{17}
\]

由于两条单模态均各自具有配对等功率，功率差只含交叉项：

\[
\Delta(H)=2\tau N\sqrt{V(1-V)}
\operatorname{Re}(e^{i\phi}c_{\delta,D}).
\tag{18}
\]

cδ,D 是由相应两个谱向量按 (16) 构成的向量，可选符号使 cδ,D→c；其符号不影响后续平方。φ 平均给出

\[
E_\phi\|\Delta\|^2
=2\tau^2N^2 V(1-V)\|c_{\delta,D}\|^2.
\]

谱向量光滑延拓、有限 PDP 支撑，以及 (17) 共同给出

\[
\boxed{E_\delta U_T=C(\mu,\tau)r+O(q),\qquad
C=2\tau^2N^2\kappa\|c\|^2
={\Gamma\over2}\|k(\mu,\tau)\|^2>0.}
\tag{19}
\]

最后的等式可由 k_i=−4τN Im(w̄a ba)/‖w‖² 与 ci=2i Im(w̄a ba)/(‖w‖‖b‖) 逐项验证。系数保留实际 Γ，不替换为 equal PDP。均值不依赖 T 或 s，所有 T≥2 共用同一个精确条件均值；噪声与 T 只影响测量方差。

由 (18)，EΔ=0 甚至对每个 D 与有限 δ 都精确成立。这与旧 C2 边缘无均值方向一致；(19) 研究的是新的跨符号乘积，而非推翻该结论。

### 2.3 精确方差与两种渐近顺序

令 ΣH=Cov(d(Y)|H)。对二阶 U 统计直接展开相同/相交/不相交索引，有

\[
\operatorname{Var}(U_T\mid H)
={4\over T}\Delta^T\Sigma_H\Delta
+{2\over T(T-1)}\operatorname{tr}(\Sigma_H^2).
\tag{20}
\]

证明：写 dt=Δ+et，et 条件均值零，则 UT−‖Δ‖²=(2/T)ΣtΔᵀet+[T(T−1)]⁻¹Σt≠u etᵀeu。两项不相关；第二项只在同一个无序指标对时协方差非零，方差为 2 trΣH²/[T(T−1)]。

null 下 Δ=0，功率差的条件分布不依赖共同信道全局相位，ΣH=Σ0。因此

\[
\operatorname{Var}_0(U_T)={2\operatorname{tr}(\Sigma_0^2)\over T(T-1)}.
\tag{21}
\]

B 独立块均值 Ū 的方差精确为

\[
\operatorname{Var}_\delta(\bar U)
={1\over B}\left[
\operatorname{Var}_H(\|\Delta\|^2)
+{4\over T}E_H(\Delta^T\Sigma_H\Delta)
+{2\over T(T-1)}E_H\operatorname{tr}(\Sigma_H^2)\right].
\tag{22}
\]

在当前固定参数紧邻域，ΣH 一致正定有界。又 (17) 满足

\[
E[V^2(1-V)^2]/\rho\longrightarrow\int_0^1(1-v)^2dv=1/3.
\]

用支配收敛证明：积分核 v²(1−v)²/[ρ+(1−ρ)v]² 一致有界，且逐点趋 (1−v)²。结合 c≠0 与均匀 φ 的四阶矩，E‖Δ‖⁴=Θ(q)，而 (E‖Δ‖²)²=O(r²)=o(q)。故

\[
\operatorname{Var}_\delta(\bar U)
=\Theta\left({q+r/T+T^{-2}\over B}\right),\qquad T\ge2.
\tag{23}
\]

这是相干块的真实双层波动：测量噪声可以由 T 降低，块间稀有 gain 取消事件不能。

**固定 T，B→∞：块密度展开的必要步骤。** 一个块只有一组 gain/PDP、一个全局相位 θ 与一个相对相位 φ，二者同时作用于全部 T 个符号；不能逐符号独立积分这些信道相位。记 Fδ,D,T(v) 为给定小模态能量 v、对该共同相位与完整 QPSK 序列平均后的 C^{NT} Gaussian 核。

在固定实际碰撞分支，L(ν)=⌊67(1+ν/6)⌋。μ 位于该分支内点时，可取足够小邻域使 L(μ−δ)=L(μ+δ)=L 恒定。因此实际两标签条件质量满足 πD=πDswap，且权重局部固定。由于

\[
B_\delta D B_\delta^H=B_{-\delta}D^{\rm swap}B_{-\delta}^H,
\]

其大模态谱投影相同，共同全局相位平均给出 Fδ,D,T(0)=F−δ,Dswap,T(0)。故 ΣDπD Fδ,D,T(0) 是 δ 的光滑偶函数，在零点等于 p0,T，偏移仅为 O(q)。这一标签混合步骤消去的是可能出现的 O(δ) 大模态漂移，不能省略。

固定 T 时，完整 QPSK 序列集合有限；每符号 ‖xt‖∞≤√N，且 ‖H‖=√(τN)，所以堆叠 Gaussian 均值范数至多 MT=√(τN²T)。相位 Taylor 展开使相对相位的奇数阶项消失，给出

\[
F_{\delta,D,T}(v)=F_{\delta,D,T}(0)+v A_{\delta,D,T}
+O(v^2G_T),\qquad A_{\delta,D,T}=A_T+O(\delta G_T).
\]

对 v≤1/2 使用均值的四阶 Taylor 余项，对 v≥1/2 用 v²≥1/4 及三个核项的有界包络，因而不要求 √(1−v) 在 v=1 可微。包络可取 GT(y)=CT(1+‖y‖)^k exp{−[(‖y‖−MT)+]²/s}，适当增大有限 CT,k,MT 即可包含所需的几何导数。另一方面 p0,T(y)≥(πs)^{−NT}exp[−(‖y‖+MT)²/s]，故 GT²/p0,T 的尾指数为 −‖y‖²/s+O(‖y‖)，在实维 2NT 可积。若联合扰动 s，以基点 s0 作分母，并缩小邻域到 smax<2s0，则尾部二次系数 −2/smax+1/s0<0，给出同一个 L² 空间内的 nuisance 支配。

由 (17)，EDV=cD r+O(q)、EDV²=O(q)；再由 δr=o(q)、有限 D 的统一余项与上述标签偶性，得到

\[
p_{\delta,T}=p_{0,T}+r h_T+O_{L^2(1/p_{0,T})}(q),
\qquad h_T=\kappa A_T.
\]

这些固定 T 常数没有对 T→∞ 的统一保证。单个不等 PDP 条件模型是不能省略标签混合的反例：在 u0ᴴu0′=0 的规范下，大模态导数为

\[
\left.\partial_\delta u_{0,\delta,D}\right|_0
={D_2-D_1\over D_1+D_2}{b\over\|w\|}.
\]

它一般给块密度一个 O(δ) 漂移，等同于一阶中心移动；固定 μ 的该条件模型不属于本节 r 首项定理。式 (19) 的特殊 U 均值仍可因其 null 均值恒零而单独成立，但不能由此声称整个条件密度没有 O(δ) 项。

现在取 B 个独立块、rB=t/√B，固定 t≥0。由 (19) 的均值、(21) 的方差及固定 T 的局部三角阵 CLT，块均值检验的非中心量为

\[
{t\,C\sqrt{T(T-1)}\over\sqrt{2\operatorname{tr}(\Sigma_0^2)}}.
\tag{24}
\]

实际未知 nuisance 下，E0,ηUT 恒为零，故其与全部 null nuisance 得分正交。得分—矩恒等式和 Cauchy–Schwarz 给出**块有效信息的显式下界**

\[
\boxed{J_{\mathrm{eff},T}\ge
{C^2T(T-1)\over2\operatorname{tr}(\Sigma_0^2)}>0.}
\tag{25}
\]

所需可积性来自有限 QPSK、紧的归一化 H 与 Gaussian 噪声。它是固定 T 的 r 信息；不是 δ 在碰撞的普通正则 Fisher 信息，也不是完整信息的等式。

**固定 B，T→∞。** 先按实际 prior 抽出 B 个 gain 后，几乎必然 ab≠0 且至少一个 Im[(gb,+−gb,−)/(gb,+gb,−)]≠0。命题 1 的条件 T^{-1/2} 检测边界适用；当 δ√T→∞，每个非退化实现的条件功效趋一，进而以有界收敛得到 prior 平均功效趋一。其 null calibration 用 (11) 或固定 B 的 χ²₂B，不能使用声称 B→∞ 的正态近似。

**任意联合 B,T 极限尚未求得最优边界。** 不能将 (24) 的固定 T 展开机械代入 T→∞。例如由 (22) 得到 Ū 的一个充分一致性条件是

\[
{B r^2\over q+r/T+T^{-2}}\to\infty,
\tag{26}
\]

而非单独 T√B r→∞。这只是该均值统计的 Chebyshev 充分条件，不是 minimax 下界；固定 B 时即使 (26) 不成立，按块 studentized 检验仍可能一致。稀有大 |gain 比率| 使以总体二阶矩描述其典型功效很不精确。

## 与原 q log 结论的关系

| 实验 | 独立单位 | 已证明的局部内容 | 不可移用之处 |
|---|---|---|---|
| 旧每符号 gain 重生 | R 个独立 (H,X,ε) | r 信息正；δ∼R^{-1/4}/√log R | 同信道重复不属于此实验 |
| 固定未知 H，相干 T 符号 | 条件于一次 gain 的 T 个 X,ε | 泛型相位下 blind C2 均值 O(δ)，点态 δ∼T^{-1/2} | 不等于 δ 的一致参数估计率，不对退化 gain 统一 |
| B 独立块，每块固定 T≥2 | B 个完整 NT 维观测块 | 同一 r 坐标；跨时 U 见证，J_eff,T 下界随 T(T−1) 增长 | 常数不对任意 T→∞ 一致 |
| 固定 B、T 增长 | B 次 gain 实现，各反复测量 | 几乎处处条件泛型结论可用 | 不能把 B 增长近似当作已发生 |
| 精确 H oracle | 一次精确物理响应 | 泛型离开 null；某一路 gain=0 时完全不可区分 | 数据不提供精确 H，分解歧义也不会因 T 消失 |

δ 项被边缘化消掉并不意味着每个真实相干块没有该项。另一方面，z 的二阶矩在实际连续 gain 比值下不有限；先对固定 gain Taylor 再平方积分是不合法捷径。原小模态 V 的精确概率律在 (17) 中给出截断后的 r，从而使两种结论完全一致。

## 经典技术与模型特定结论

- 经典：Gaussian 线性充分统计、null 流形切空间投影、KL/data processing 下界、studentized 均值检验、Hoeffding U 统计分解、得分—矩下界、随机效应的条件/边缘区别。
- 模型特定：保留真实三 atom 与 Gram 归一化后的 (8)–(10) 闭式非零 blind 见证；C2 在独立重生与相干块中的角色翻转；真实 PDP 的系数 C=Γ‖k‖²/2；块信息下界 (25) 与稀有块方差 Θ(q)。
- 未核查外部文献，不能称这些机制、方法或此模型结论首创。尚未给完整 receiver/decoder 方法、FER、N1024、成本或有限 T 优势。

## 最小数值验证建议（全部未执行；交主会话 SSH）

1. 只调用已冻结的小 N geometry/Gram：在 μ=.27,.31,.35 和固定 g=(1,i)、(1,.5i)、(1,1)、(1,.5)、(1,0) 上检查 ‖H‖²=4τ。用递减 δ 的双边/单边差商核对 (10)，不随机采样、不按结果调 g；g=(1,0) 必须恰落入移动中心 null。
2. 用 (8) 的闭式 R 与冻结实际 w 的一个公共复比例核对逐坐标残差；比较 b 的真实导数与理论配对差。验证不要用替代的完整四 atom Fourier 曲线。
3. 主会话如获实验执行准入，独立登记少量相干块数据；保持每块同一 g，仅重生 QPSK/噪声。并列 T 增长下的原 C2 (11) 和错误的每符号 gain 重生对照；保存每块 Δ 真值仅作外部诊断，绝不传给检验。
4. 固定 T=2,4，验证 UT 样本均值相对 (19)、null 方差相对 (21)；先做确定性 QPSK/噪声矩消元或已准入积分，再考虑随机检验。任何积分误差与有限 δ 余项需分别标注。
5. 不需实现新 GMM、不需 full likelihood 调优，不更改生产 receiver/decoder/CONF。若 (10) 的冻结物理导数不符，先停在符号/索引/相位核对，不能通过拟合系数“修复”定理。

## Files Found / Code Patterns

- `experiments/afdm_collision_resolution/DENSITY_THEORY.md:36`：实际 N4 三 atom、窗口顺序、非零 b 与固定 PDP 分支；`:92` 的谱表示与小模态重尾；`:218` 的真实边缘 r 展开；`:329` 的独立重复分辨尺度。
- `experiments/afdm_collision_resolution/NUISANCE_THEORY.md:101`：未知 μ/logτ/logs 的有效投影；`:227` 附近的实际 N4 几何核实。仅复用已陈述结论，不把它误解为 fixed-gain 结论。
- `experiments/afdm_method_advantage/THEORY.md:55`：公开 null μ 的 Pa 单调识别；`:248`：原独立重生 C2 配对均值对称证明，解释本研究为何必须保留块结构。
- `experiments/afdm_higher_order_information/prior.py:25`：geometry 的真实 clipping、G0 整数 atom Fourier 响应、Gram 来源；`:106`：正定分支完整归一化导数，不能直接用于 rank-one 碰撞。
- `experiments/afdm_efficient_information/prior_likelihood.py:23`：N4 system cap；`:46`：实际 PDP 混合；`:296` 附近：sample 每次重新抽 PDP/gain/QPSK，说明原代码不模拟相干块。
- `experiments/afdm_shared_channel_20261004/production_prior.py:27`：frozen_components 只沿冻结目录加载；`:46`：真实 Gram；`:76`：normalize_gain 的二次型归一化。
- `experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/budgeted_support_diagnostics.py:82`：先五点窗口归一化，再 cap/prune；每条物理路径一列。
- `experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/afdm_env.py:418`：Dirichlet 定义；`:587`：实际展开顺序；`:631`：Frobenius 归一化为 √N。

## Related Specs / External References

- 已读 `.trellis/spec/backend/structured-inference.md`：真实归一化 prior 与工作 prior 必须区分；truth-provided 模型点不可包装为 deployable 估计；tiny 数学检查不支持 FER/全链成本主张。
- 使用 `/Users/guoyikun/.codex/skills/formula-derivation/SKILL.md` 组织对象、假设、恒等式、命题及边界；用户指定输出路径优先于其默认根目录路径。
- 外部文献：本次没有外部搜索；Gaussian location、U 统计、LAN 等只作标准数学技术使用。版本来源为当前项目冻结 `sp_afdm_frozen_20260920`，未检索上游新版本。

## Caveats / Not Found

- 两项命题改变的是观测实验的相干结构，不能回写为旧独立重生研究的性能成果。
- 固定 gain 点态结论不是对任意未知增益的统一 minimax 率；零路径、主模态取消、近同相、几何退化都是实质边界。
- 未证明未知 QPSK 下完整路径参数可全局唯一恢复；本研究只给碰撞检测，oracle 代数辨识由平行 algebra 研究负责。
- 未完成任意 B,T 联合增长的最优检测相图，也未认证有限 δ、有限样本功效或常数。式 (26) 仅为特定统计的充分条件。
- 本文件所有验证均为解析推导与源码对照，没有运行数值实验。主会话应先独立核对 (8)–(10) 的索引、符号和归一化，再决定最小服务器验证。
