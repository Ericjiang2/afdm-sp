# Research: 相干盲观测的四阶不变量、剩余对称群与实际三 atom 可辨识性

- Query: 固定且未知的实际 G0 信道 H 在 iid 未知 QPSK 与圆 Gaussian 噪声下，能否由无限相干重复盲恢复到不影响路径参数的 gauge，并接上前轮完整 H 的 Prony 结论？
- Scope: mixed；冻结源码对照、解析证明、三项经典文献定位。未数值采样、未运行数值程序、未 SSH、未改源码。
- Date: 2026-10-06
- Active task: `.trellis/tasks/10-05-method-advantage`
- Active scope: 本目录 `ROUND.md` 与 `.mission/20261006_12-39-13-afdm-deep-principles/PLAN.md`；历史 `prd.md/design.md` 仅作索引。
- Status: **COHERENT AFTER REFRAMING / EXTRA ASSUMPTION**。完整平衡四阶张量的纤维可以精确证明；接到实际路径参数须加时间坐标非零、合成 Fourier 支撑完整与 Prony 非退化条件。以下是完整解析论证，尚待本轮独立证明复核及主线程冻结后 SSH 对照。

## Findings

对所有时间坐标非零的 H，完整的 2+2 四阶累积量恰好识别 H 到

\[
H'_i=e^{\mathrm i\phi}e^{2\pi\mathrm i ri/N}H_i,
\qquad \phi\in\mathbb R/(2\pi\mathbb Z),\quad r\in\mathbb Z_N.
\]

这是**该矩张量**的完整歧义群。不能未经证明把它等同于完整 QPSK 分布的歧义群。未知 Gaussian 噪声方差不影响四阶累积量，并能由其对角线和二阶矩分离出来。

在实际 N4 三 atom 分支，若合成后的三个 Fourier 系数均非零，已知支撑 `{-1,0,1} mod 4` 排除所有非零 r，剩下全局相位。一个非平衡四阶矩还能将其缩为 QPSK 的四重相位；因此此物理类的完整盲观测分布恰好识别 H 到 C4。全局相位不影响前轮 Prony 的实节点方程：有效增益不共线时，Doppler 对、中心、半间距由无限相干盲观测可辨识；共线时，同 H 的精确多解仍在，完整分布也无能为力。

这是固定信道、固定分支、泛型参数的识别定理。它没有把无限样本识别转换成有限 T 的稳定估计保证，也没有改变生产 receiver、decoder、FER 或 CONF 主张。

### 1. Target、invariant object 与源码边界

**Target.** 分开证明三个映射：

\[
\mathcal L(Y\mid H,\sigma^2)
\ \longrightarrow\ K^{2,2}(H)
\ \longrightarrow\ H/\text{gauge}
\ \longrightarrow\ \{\nu_1,\nu_2\}.
\tag{1}
\]

第一步只取可观测矩，第二步研究其精确纤维，第三步使用固定物理支撑及前轮代数结果。四阶张量是本推导的不变量对象；不用协方差 Gaussian 替代真实 QPSK 分布。

**Files found / code patterns（路径相对项目根）。**

| 文件 | 本文采用的事实 |
|---|---|
| `experiments/sp_afdm_frozen_20260920/src/physical.py:87` | `daft` 是正 chirp、FFT、正 chirp；inverse 按共轭相位反向实现。 |
| `experiments/afdm_efficient_information/prior_likelihood.py:31` | 当前小系统 c1=2.5/N、c2=.1/N²。 |
| 同文件 `:36` | `qpsk_time` 只枚举全局 QPSK 轨道代表，原用途还积分了增益全局相位；不能直接将其当作固定 H 的完整符号概率空间。 |
| 同文件 `:46` | 实际共同 rounded delay=0、正 Doppler 的条件 PDP 混合。 |
| `experiments/afdm_coherent_structure_20261006/core.py:58` | 先抽一次实际 PDP / Gaussian 方向，再由实际 Gram 归一化得到 H。 |
| 同文件 `:70`、`:90` | coherent 模式共享一个 H，逐符号独立抽 QPSK 与 Gaussian 噪声，`x=symbols@daft(N).conj()`、`y=H*x+noise`。 |
| `experiments/afdm_higher_order_information/prior.py:25` | 先 physical clipping，再真实 G0 权重；时间响应为 `exp(+i outer(time,k)) @ weights`。 |
| `experiments/afdm_shared_channel_20261004/production_prior.py:46`、`:74` | R=WᴴW 来自冻结 clipping/pruning，gain 除以真实 Gram 范数；没有替代为单位阵。 |
| `research/20261006-important/algebra/ALGEBRA_CANDIDATES.md` | 本任务前轮的三矩变换、泛型 Prony 反演与同 H 连续歧义。 |
| `research/20261006-important/coherence/THEORY_CANDIDATES.md` 式 (8) | 实际 N4 单径四个时间坐标的显式非零表达式。 |
| `afdm_sp_joint_unrolled/outputs_coherent_structure_20261006/RESEARCH_REPORT.md` | 前轮已审查的完整 H 代数结论及相干检测结果；本文没有重算其数值。 |

表中两条 `research/...` 路径相对当前 Trellis task，其余路径相对项目根。本轮不读取或修改 implementation/check manifest，不重启历史已完成研究。

### 2. Assumptions、notation 与 derivation map

**基础观察模型。** 所有下标在循环群 Z_N 中解释，N≥2。每次观察是列向量

\[
Y^{(t)}=\operatorname{diag}(H)US^{(t)}+n^{(t)},\qquad U=A^H,
\quad n^{(t)}\sim\mathcal {CN}(0,\sigma^2 I).
\tag{2}
\]

H∈C^N 固定，σ²≥0 有限且未知；不同 t 的符号和噪声独立，且独立于这个固定 H。每个 S_s 独立均匀取 `exp(iπ/4){1,i,-1,-i}`，单位功率。这里的固定 H 包括实际 √τ 增益尺度。对实际随机信道的应用是**条件于本块已实现 H**；不能先对 gain 边缘化再套用下列公式。

定义

\[
r_i=e^{-2\pi\mathrm i c_1i^2},\qquad
v_s=e^{-2\pi\mathrm i c_2s^2},\qquad
U_{is}=N^{-1/2}r_i e^{2\pi\mathrm i is/N}v_s.
\tag{3}
\]

这与源码 `A=diag(exp(+2πic2s²)) F diag(exp(+2πic1i²))` 完全一致，F 使用负号酉 Fourier 约定。令 Z_i=conj(r_i)Y_i；这是已知可逆的行相位校正，Gaussian 噪声律不变。

定义平衡四阶累积量

\[
K_{ijkl}=\operatorname{cum}(Z_i,\bar Z_j,Z_k,\bar Z_l).
\tag{4}
\]

零均值 proper 的模型给出

\[
K_{ijkl}=E[Z_i\bar Z_jZ_k\bar Z_l]
-E[Z_i\bar Z_j]E[Z_k\bar Z_l]
-E[Z_i\bar Z_l]E[Z_k\bar Z_j].
\tag{5}
\]

一般四阶累积量还有 `−E[Z_i Z_k]E[bar Z_j bar Z_l]`；本模型 E[ZZᵀ]=0，故该项精确为零，不是近似。所有期望均条件于固定 H。

**物理推论的额外假设。** N=4、G0、P=2、共同且已知 rounded delay=0；两条实际 Doppler 都落在同一合法开分支 I⊂(.22,.42)，无 clipping、共同保留 S={−1,0,1}，PDP 条件分支固定且各对角元严格正，沿原五点窗口归一化→cap/prune→实际 Gram 总归一化。两 Doppler 相异、两 gain 非零。仅有 μ∈[.22,.42] 不足以保证两条路径都在这个分支。

证明中的非零条件分别指：时间坐标 H_i≠0、合成 Fourier 系数 q_m≠0、Prony 行列式 D≠0。三者不是同一条件。

**Derivation map.** (i) QPSK 单源累积量与 Fourier 正交性给精确四阶闭合关系；(ii) 比较两个 H 的坐标比，把所有歧义化为循环群 character；(iii) 固定 Fourier mask 排除非零 character；(iv) 全局相位不改 Prony 方程，获得泛型路径识别；(v) 一个 N4 非平衡矩可选地识别剩余相位到 C4。全链没有小 δ 近似。

### 3. Identity：四阶闭合与 Gaussian 噪声剔除

QPSK 满足 E[S]=E[S²]=0、E|S|²=E|S|⁴=1，故

\[
\operatorname{cum}(S,\bar S,S,\bar S)=1-1-1=-1.
\tag{6}
\]

不同源独立，混合源累积量为零；独立 Gaussian 的四阶累积量为零。由累积量多线性性和 (3)，列 chirp 在 2+2 乘积中抵消，所以

\[
\begin{aligned}
K_{ijkl}
&=-\frac{H_i\bar H_jH_k\bar H_l}{N^2}
\sum_{s=0}^{N-1}e^{2\pi\mathrm i(i-j+k-l)s/N}\\
&=-\frac1N H_i\bar H_jH_k\bar H_l\,
\mathbf1\{i-j+k-l=0\pmod N\}.
\end{aligned}
\tag{7}
\]

若直接用 Y，右边还要乘 `r_i conj(r_j) r_k conj(r_l)`。不能在未 dechirp 的张量上漏掉这项。

特别地

\[
K_{iiii}=-|H_i|^4/N,\qquad
|H_i|^2=\sqrt{-NK_{iiii}},
\qquad \sigma^2=E|Y_i|^2-\sqrt{-NK_{iiii}}.
\tag{8}
\]

最后一步用了 U 酉与 iid 单位功率 QPSK，使 `E[YYᴴ]=diag(|H|²)+σ²I`。每个 i 都给相同 σ²，可用作模型自洽检查。实际归一化信道还满足 τ=‖H‖²/N。这些是总体恒等式；带噪经验四阶数可能符号错误，不允许静默截断后声称满足恒等式。

**直觉。** 二阶统计把独立源的贡献相加后只剩功率；四阶 cumulant 去掉了两个 Gaussian 配对项，留下同一非 Gaussian 源的四次乘积。Fourier 求和再充当一个离散守恒约束：只有总索引 i−j+k−l=0 的四项相位闭合存活。

### 4. Proposition A：完整 K 的歧义恰为 U(1)×Z_N

**命题。** 设 H_i≠0 对每个 i 成立。H′ 与 H 产生相同的完整张量 (7)，当且仅当存在 |a|=1 和 r∈Z_N，使

\[
H'_i=a\chi_r(i)H_i,\qquad \chi_r(i)=e^{2\pi\mathrm i ri/N}.
\tag{9}
\]

这里没有要求比较候选 H′ 预先非零：对角张量相等自动给出 `|H′_i|=|H_i|>0`。

**证明。** 由 (8)，R_i=H′_i/H_i 均为单位模。对合法四元组 `(i,0,k,i+k)`，张量相等除以非零 H 乘积得到

\[
R_i\bar R_0R_k\bar R_{i+k}=1.
\tag{10}
\]

置 a=R_0、χ(i)=R_i/a，则 χ(0)=1，(10) 等价于 χ(i+k)=χ(i)χ(k)。循环群由 1 生成，故 χ(i)=χ(1)^i；循环闭合给 χ(1)^N=1，存在唯一 r∈Z_N 使 χ=χ_r。反向地，(9) 的全局相位在 2+2 乘积中抵消，character 的乘积在合法四元组上等于 `exp(2πir(i−j+k−l)/N)=1`；非法四元组原本为零。因此张量相同。证毕。

**噪声未知的补充。** 如果再要求二阶矩相同，(8) 给 σ′²=σ²；Gaussian 方差不能补偿一个不同的信道幅度。

**只需一条循环链即可理解恢复。** 已知幅度后，取

\[
c_i=\frac{-NK_{i,0,1,i+1}}
{|H_i||H_0||H_1||H_{i+1}|}
=p_i\bar p_0p_1\bar p_{i+1},\quad p_i=H_i/|H_i|.
\tag{11}
\]

选全局相位 p_0=1。于是 `p_{i+1}=p_i p_1/c_i`，而 `p_1^N=∏_i c_i`。N 个根就是 N 个 character，既无更多连续歧义，也没有遗漏离散歧义。这个构造只解释总体逆映射，不是已实现或已验证的带噪接收算法。

**对象边界。** (9) 是 K 的完整纤维；并未证明 arbitrary chirp-QPSK 的全部观测分布对每个 r 都不变。列 chirp v_s 在 balanced cumulant 中消失，通常仍会影响更高或非平衡矩。因此不能用 K 的相等去断言完整分布相等。

### 5. Proposition B：固定 Fourier support 消除 character

按冻结 G0 正号约定，定义唯一 Fourier 系数

\[
H_i=\sum_{m\in\mathbb Z_N}q_m e^{2\pi\mathrm i mi/N},
\qquad q_m=\frac1N\sum_iH_i e^{-2\pi\mathrm i mi/N}.
\tag{12}
\]

`q_m=0` 对 m∉S 已知。由 (9)，`q′_m=a q_{m-r}`。令 Q=supp(q)，候选 character 恰好受以下支撑条件限制：

\[
\mathcal R(Q,S)=\{r\in\mathbb Z_N:Q+r\subseteq S\}.
\tag{13}
\]

当 **Q=S**，有限集合等势意味着 `S+r⊆S` 等价于 `S+r=S`，故剩余群是 S 的平移稳定子。

N4 的 S={3,0,1} 的补集只有 {2}。若 S+r=S，则补集也固定，`{2+r}={2}`，从而 r=0。因此：若所有 H_i 非零，三个合成 q_{−1},q_0,q_1 均非零，则任一同一 mask 内、K 相同的 H′ 必为 aH。这一结论甚至在所有 mask 内信道的较大类成立，因此可限制到实际双径族。

**支撑非零条件为何必要地单列。** 原路径的每个 Dirichlet 列在 S 上非零，并不保证两条路径叠加后的 q 每行都非零。若 Q⊊S，不能直接只检查 `Stab(Q)`：一个不保持 Q 的平移也可能仍落在 S 内，正确集合是 (13)。例如在这个较大 mask 类，单 Fourier atom Q={0} 平移到 {1} 或 {3} 仍合法；Q={1,3} 则有周期 r=2。它们证明“知道 mask 就总能消除 character”错误，不证明这些例子必属本轮正 Doppler 双径子族；该子族的支撑退化层还需另行分析。

### 6. Corollary：actual N4 完整分布将全局相位缩到 C4

本节只加强 Proposition B，不尝试分类任意 N、任意零点/稀疏支撑的完整分布。

因为该 QPSK 的 E[S⁴]=−1 且 E[S²]=0，proper Gaussian 的全纯四阶矩也为零，(2)–(3) 给出

\[
E[Z_i^4]=-\frac{H_i^4}{N^2}
\sum_{s=0}^{N-1}e^{8\pi\mathrm i is/N}v_s^4.
\tag{14}
\]

N=4 时第一项指数恒为 1，实际 c2=.1/16=1/160，故

\[
E[Z_i^4]=-B_4H_i^4,\qquad
B_4=\frac1{16}\sum_{s=0}^3e^{-\pi\mathrm i s^2/20}\ne0.
\tag{15}
\]

非零证明不需要数值：四个角的绝对值分别为 0、π/20、π/5、9π/20，均小于 π/2，因此四项实部严格正。

若满足 Proposition B 的 H,H′ 给相同完整分布，先由 K 得 H′=aH；再由一个非零坐标的 (15) 得 a⁴=1。反向地，a∈{1,i,−1,−i} 时 `aS` 与 S 同分布，`a diag(H)US=diag(H)U(aS)`，噪声独立且相同，故 H′=aH 确实给相同完整分布。结合 (8)，该类 `(H,σ²)` 的完整分布纤维**恰为 C4**。

这是固定 H 的结论。若将本块全局 gain 相位按圆 prior 边缘化，(15) 的信息也随之被平均掉，不能拿此 corollary 去解释原每观察重生 gain 的边缘模型。

### 7. Proposition C：将 blind H 接到前轮实际 Prony 节点

额外采用第 2 节的实际双径合法分支。由 (12) 得到 q 后，令 h=π/N、c=cos h，按 m=−1,0,1 定义 β_m=exp(imh)q_m（此处 i 为虚数单位）和

\[
M_0=\frac c2(\beta_{-1}+\beta_1),\quad
M_1=\frac c2(\beta_{-1}-\beta_1),\quad
M_2=M_0-\beta_0.
\tag{16}
\]

前轮真实 Dirichlet 推导给出精确表示

\[
M_j=\lambda_1 y_1^j+\lambda_2 y_2^j,\quad j=0,1,2,
\qquad y_i=\tan(\pi/N)\cot(\pi\nu_i/N).
\tag{17}
\]

λ_i 包含真实窗口因子、Dirichlet 列相位、raw gain 与共同 Gram 归一化；不是另设 iid Gaussian 有效 gain。设

\[
D=\operatorname{Im}(M_1\bar M_0)
=(y_1-y_2)\operatorname{Im}(\lambda_1\bar\lambda_2)\ne0.
\tag{18}
\]

则真实节点是实二次式 `z²−Sz+P=0` 的两个根，其中

\[
S=\frac{\operatorname{Im}(M_2\bar M_0)}D,
\qquad P=\frac{\operatorname{Im}(M_2\bar M_1)}D.
\tag{19}
\]

**全局相位为何可忽略。** 从 balanced K 恢复的 H 可能乘 a，q 和 M 同乘 a；(18)–(19) 的所有分子分母同乘 |a|²，S,P 不变。因此不需要用第 6 节消除连续全局相位，也无需知道任何真实符号、PDP 或 gain 来定义这些总体逆映射。ν=(N/π) arctan(tan(π/N)/y) 在该合法区间单调，得到无序 Doppler 对，继而 μ=(ν₁+ν₂)/2、δ=|ν₂−ν₁|/2。

**命题的逻辑结论。** 在时间 H_i、合成 q_m 及 D 都非零的实际 N4 固定双径分支，同一完整盲分布的任意另一合法双径参数必须有相同无序节点对。事实上二阶矩与完整 balanced 四阶累积量已经足够识别节点。此结论对无穷相干重复成立，不依赖“已知符号 oracle”。

**为什么它在实际 PDP 下是泛型而非人为排除大块先验。** 固定任意两个相异内点 Doppler：各 W_m(ν) 非零；前轮 coherence 式 (8) 的 N4 单径时间坐标也全非零。因此 `q_m=0`、`H_i=0` 各自是 raw 二维复 gain 的非平凡复线性约束。D=0 则是两个非零列因子乘 gain 后的相对相位共线条件，同样为连续复方向分布的零测集。每个实际 D_PDP≻0 保持 Gaussian 原始方向具有连续全支撑密度；正的 Gram 总归一化只作公共实数缩放，不改变这些零事件。对实际有限正 PDP 混合仍几乎处处满足这些条件。此概率论说明不提供任何远离退化面的统一常数。

### 8. Counterexamples、边界与有限样本

**8.1 时间零点。** Proposition A 用了除以每个 H_i。没有非零条件，剩余相位可比 character 更大。例如 ambient N4 模型

\[
H=(1,e^{\mathrm i\theta},0,0)
\tag{20}
\]

对所有 θ 都有相同 K：有效索引只有 {0,1}，两个正索引之和为 0、1、2，模 4 互异，闭合只能匹配同一多重集合，于是相位都抵消。θ 是任意连续参数，超出全局×character。此例是一般观察模型的反例，并未宣称所有 θ 都满足本轮物理 mask。若有零点，须研究非零支撑上四项闭合关系的连通/生成性质，不能把非零域证明机械延伸。

**8.2 Fourier 支撑缺项或周期。** 见 (13)。时间零点与 Fourier 零系数完全不同；单 Fourier atom 的 H 各时间坐标全非零，仍可能有 mask 允许的 character 歧义。反过来，完整 q 支撑也可能出现特定时间点抵消。

**8.3 三 atom 的精确同 H 歧义。** 当 λ₁、λ₂ 共实相位，取公共相位后 M_j=r_j∈R。任选 a 在原节点 y₁ 附近，定义

\[
b(a)=\frac{r_2-ar_1}{r_1-ar_0},\qquad
\ell_1(a)=\frac{b(a)r_0-r_1}{b(a)-a},\qquad
\ell_2(a)=\frac{r_1-ar_0}{b(a)-a}.
\tag{21}
\]

则 `r_j=ℓ₁(a)a^j+ℓ₂(a)b(a)^j`，j=0,1,2；原点处分母非零，故存在连续不同合法节点对给相同 M、q、H。前轮已在实际正 PDP 支撑与 Gram 归一化内构造并核验。固定同一 σ²，完全相同 H 给完全相同所有 T 的盲分布；任何更高阶矩、更多重复、甚至直接知道 H 都不能消除该路径歧义。这是**参数化非单射**，不是观测矩不足。

同时 `M₀M₂−M₁²=λ₁λ₂(y₁−y₂)²≠0` 仍可排除单径，所以同 H 多节点表示不等于无法判断路径数。raw gain 同相与 λ 共线不等价，不能混用。

**8.4 碰撞、零路径与其他物理分支。** δ=0 或某 gain 为零时，节点本就不唯一地表示两条非零分离路径；不在 Proposition C 内。跨 mask、rounding、alias、clipping 或非零 delay 的类未证明。本轮没有以 G1、未截断 Fourier 波或等 PDP 替代 G0。

**8.5 为什么无限重复足够，但有限样本仍难。** 固定 H、N、σ² 下，QPSK 有界、Gaussian 有所有有限矩，故经验二/四阶矩依强大数定律一致，估计这些矩所需的八阶矩也有限。式 (11) 在非零点有局部连续逆（选择一个连续根支），固定完整支撑点的错误 character 各有严格非零 mask 外残差，式 (19) 在 D≠0 且节点分离时亦局部连续。因此可构造固定正则点的一致盲恢复，不需先知道 H。该推论是总体映射加大数定律，不是本轮已实现的 estimator。

经验矩本身在固定点有 T^{-1/2} 随机误差，但反演常数含小 |H_i| 的倒数、小 |q_m| 的支撑判别余量、小 |D| 的倒数及节点根间隔的倒数。δ→0、相位退化、零点附近都可能使常数发散。本文不声称关于趋零 δ 的统一 T^{-1/2} 间距估计率、最优率、有限 T 阈值或生产效用；也不从本定理推出前轮检测曲线的具体指数。

另一个尺度警示：diag cumulant 大小为 |H_i|⁴/N；虽然 Gaussian 噪声在期望中消失，四阶经验量的方差仍受噪声八阶矩支配。高阶统计的“消噪”是无偏结构，不是有限样本零噪声。

### 9. Remarks / 科研直觉与跨领域连接

1. **先求歧义群，再讨论估计器。** 与其直接设计复杂 blind fit，先问哪类 H 的全部观测特征必然相等。这里将 N 个未知相位的相等关系压成一个循环群同态，得到精确 obstruction；物理 support 随后固定离散自由度。
2. **ICA 的非 Gaussian 机制。** iid QPSK 的非零第四 cumulant 是相位信息来源。若改成 proper Gaussian S，四阶 cumulant 全为零，Y 只剩由 |H|² 决定的 Gaussian law；在一般 H 类中相位完全不可见。已知 Fourier/DAFT 结构让本问题可以直接求出歧义，不需要通用 ICA 张量分解定理。
3. **相位恢复与高阶谱。** 普通功率给 |H|，四项闭合给相位组合。其逻辑与 bispectrum/trispectrum 的相位闭合和移位不变性相近；这里得到 character 调制，是因为观察坐标在循环群上。不能将本文的 2+2 四阶对象称为通常的三阶 bispectrum。
4. **Gauge 与 synchronization。** (11) 是带闭环一致性的相位传递关系；N 个根来自绕环的离散选择。零坐标会删除约束，正如同步图断开会产生额外自由度，但这里约束是四项超边，不能只凭普通图连通就声称充分。全局相位对 Doppler 没有影响，是参数目标天然商掉的 gauge。
5. **观测非单射与参数化非单射须分开。** Proposition A/B 修复的是未知符号造成的观察歧义；(21) 属于 H→路径分解的歧义，两者位于 (1) 的不同箭头。前者被更多矩克服，不会自动克服后者。

### 10. External references / classical positioning

以下于 2026-10-06 检索核对题名、作者及页面摘要/书目信息；只作经典方法定位，未逐篇完整推演其定理，也没有完成当前 AFDM 特殊模型的新颖性检索。

- Pierre Comon, *Independent component analysis, A new concept?*, Signal Processing 36 (1994), 287–314。[出版社页面](https://www.sciencedirect.com/science/article/abs/pii/0165168494900299) 与[作者版本](https://www.gipsa-lab.grenoble-inp.fr/~pierre.comon/FichiersPdf/como94-SP.pdf)。对应“二阶独立不足、高阶 cumulant 提供非 Gaussian 源分解信息”；本文不借此宣称任意 complex ICA 条件自动满足。
- Amit Singer, *Angular synchronization by eigenvectors and semidefinite programming*, Applied and Computational Harmonic Analysis 30 (2011), 20–36。[原文归档](https://pmc.ncbi.nlm.nih.gov/articles/PMC3003935/)；[arXiv:0905.3174](https://arxiv.org/abs/0905.3174)。对应从相位差恢复角度及全局相位自由度；四项闭合与 pairwise synchronization 的联系是本文解释，不冒称其原定理直接覆盖本模型。
- Tamir Bendory, Nicolas Boumal, Chao Ma, Zhizhen Zhao, Amit Singer, *Bispectrum Inversion with Application to Multireference Alignment*, IEEE TSP 66(4) (2018), 1037–1050。[原文归档](https://pmc.ncbi.nlm.nih.gov/articles/PMC5966049/)；[arXiv:1705.00641](https://arxiv.org/abs/1705.00641)。对应 invariant 高阶谱恢复及平移对称性；本轮第四 cumulant 与其三阶 bispectrum 是不同对象。

无需将经典 cumulant、character、phase closure、Prony 或 synchronization 工具包装为首创。模型特定贡献候选是它们与当前实际 DAFT、G0 mask、PDP/Gram 支撑的精确兼容链条；其新颖性未审查。

### 11. 最小 SSH 确定性验证建议（本代理未执行）

主线程按本轮 PLAN 登记、冻结已提交源码、核对独立快照后统一执行。无需 Gaussian quadrature，也无需新随机观测；有限 QPSK 状态求和应登记为确定性评估，不记成新增随机 Y。

1. **DAFT 与张量符号。** N4、c1=2.5/4、c2=.1/16，直接冻结 `physical.daft` 构造 U，对全部 4⁴=256 索引检查 `Σ_s U_is conj(U_js) U_ks conj(U_ls)` 与带 r 的 (7) 系数一致。保存合法和非法 closure 的最大绝对残差。
2. **一组真实物理信道。** 复用前轮确定性输入 ν=(.29,.33)、pre-normalization gain 方向 `(1+.2i,−.4+.7i)`，共同 delay=0、τ=1；从冻结 geometry 与真实 Gram 得 H，不用替代曲线。保存 H、q、min|H|、min|q_S|、D、‖H‖²/N 和 branch signature。
3. **完整 256 QPSK 状态。** 枚举 `exp(iπ/4)i^s` 的全部 4⁴ 状态，不直接使用原 `qpsk_time` 轨道代表作为 fixed-H 概率空间。精确加权求一、二、四阶矩，核对 (5)–(8)、(15)。Gaussian 部分以 Wick 恒等式解析加入两个预设 σ²（例如 .2、.7），验证 cumulant 不变及方差反解；不用生成噪声。
4. **群与 mask。** 构造四个 character 和一个固定非 QPSK 全局相位（例如 φ=.37）。检查全部 K 相等；对 r=1,2,3 检查唯一禁用 m=2 系数非零，对 r=0 为零。加入 (15) 后非 QPSK 全局相位须可区分，而 φ=π/2 完整四阶矩应相同。无需宣称非零 character 的完整分布相同。
5. **blind→Prony。** 只用上述精确总体矩经 (8)、(11) 得到候选 H，按 mask 选分支，再经 (16)–(19) 恢复节点；真值只用于外部误差检查。验证路径全程不调用真实 H 去定相位或选择正确 r。N 个根的任意排序均须得到同样无序节点对。
6. **反例不合并。** 用合成 ambient H=(1,exp(iθ),0,0) 的两个预设 θ 检查 K 相等，并明确该 check 不是物理先验实验。前轮 (21) 的同 H 反例只引用其已保存原始证据；如主线程需要新矩核对，可以用原保存 H 做零新观测复算，不能重生或覆写旧实验。

先保留失败及原始残差，若冻结源码符号不符，停止在索引/共轭/归一化核查，不拟合一个补偿常数来“修复”恒等式。核对误差容差由主线程冻结；本文未提供有限样本阈值。

## Related Specs

- 已读 `.trellis/spec/research-protocol.md`：保持一条证据链，解析、数值、主张分层；本文件不提升论文或生产主张。
- 已读 `.trellis/spec/backend/bounded-mathematical-studies.md`：正式执行前提交与冻结；保存准入、预算、失败及不可变原始证据。本文只给待主线程执行的建议。
- 已读 `.trellis/spec/backend/structured-inference.md`：保留实际 PDP / Gram 和合法 constellation，不把数学正确性等同于 receiver 价值。
- 使用 `/Users/guoyikun/.codex/skills/formula-derivation/SKILL.md`：目标、对象、假设、恒等式、命题、解释与非主张分开；输出路径采用父线程指定的独占文件。

## Caveats / Not Found

- 未证明含时间零点、合成 Fourier 缺项的实际双径子族的完整分类；给出的相关反例区分了 ambient 观察类与实际物理子族。
- 未证明任意 N/任意 chirp 的完整 QPSK 分布歧义群；已证的是一般 N 的 balanced 四阶纤维，以及实际 N4、完整支撑类的 C4 完整分布纤维。
- 未给有限 T 的统一稳定常数、近碰撞估计率、样本复杂度、最优检验或实现效用；Gaussian cumulant 为零不等于经验矩无噪声。
- 实际正 PDP 下的“几乎处处”不排除任意接近退化集的信道，也不改变前轮三 atom 的精确同 H 多解。
- 本文件是解析证明与源码对照，不是运行验证。所有正式确定性数值由主线程依本轮预算、准入和 SSH 规则执行，零新随机观察。
- 经典背景已有限检索定位，AFDM 专门新颖性、近期优先权未检索，不声称首创。
