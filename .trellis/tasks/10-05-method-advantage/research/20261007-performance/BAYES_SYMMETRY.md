# Research: 二次列码障碍能否提升为均匀先验 Bayes 平均风险下界

- Query: 在当前均匀 delay/整数 CFO、圆对称且径向独立的共同 gain 先验下，是否能把二次列 chirp 的 exp[−O(N^(1/3))] 最坏风险障碍提升为平均风险障碍；核验 Weyl quotient、增益积分、估计器和有限 gain grid 的作用。
- Scope: internal，纯解析推导；未运行仿真、科学代码、SSH 或生命周期操作。
- Date: 2026-10-07
- Active task: `.trellis/tasks/10-05-method-advantage`
- Prior material read: `research/20261006-continuous/QUADRATIC_BARRIER.md`、`COMPOSITE_LATTICE_ESTIMATION.md`、`APPLICABILITY.md` 的参数域、困难 pair、KL/estimator 论证；沿用本目录已核实的 PROTOCOL 和实现接口。

## Findings

### 结论

**成立，且无需额外付出 1/|Θ_N| 的因子。** 在下述明确先验及观测模型下，每个二次列码（包括随 N 优化的任何实 c2）都有

`R_Bayes^*(N,T) ≥ (1/4) exp{−[T Eρ²/σ²] [4K+4π²N/K²]}`，`1≤K<N`。

选择 `K=floor(N^(1/3))`、固定 T、固定每符号噪声尺度且 gain 径向二阶矩有界，得到 `R_Bayes^*≥exp[−O(N^(1/3))]/4`。这把旧的理论障碍提升为当前均匀格点先验下的平均风险障碍，而不仅是 minimax 的坏点。

关键不是直接对旧的固定 h 下界取平均。必须先对**每个数据集共同、未知的 h** 正确边缘化，用保持先验的相位耦合证明边缘 KL 上界，再把困难 pair 的全部群平移逐对求和。下文给出完整步骤。

这仍不推出 N=32/64、T=4 的具体改进幅度，亦不证明当前固定随机码 realization 或 SCREEN32 取得理论最优率。主线程给出的 pilot 结果为 quad SCREEN 25/256、random SCREEN 17/256，差 3.125 个百分点且 CI 含零，10pp gate 未过；本解析结论不改变该实验判定。

## 1. 固定统计实验与风险对象

令 `g=gcd(N,4)`、`M=N/g`，参数集合 `Θ=Z_N×Z_M`，参数 `θ=(a,l)`、`a=ν+sl mod N`。当前 N=32/64 时 g=4、M=N/4。给定任意固定已知 unit-modulus 列码 C=diag(v)，去 row chirp 后的单帧矩阵为

`U_(a,l)=D_a Fᴴ C E_l`，`E_l[j,j]=exp(−2πilj/N)`。

物理模型给有效 gain `h_eff=h exp(−πis l²/N)`。若物理 h 的相位在 [0,2π) 均匀，且径向分布与 θ、相位独立，则 h_eff 具有同一先验，与 θ 仍独立；下文用 h 表示这个有效 gain。

设 `h=ρ exp(iφ)`，先验 `μ(dh)=μρ(dρ)dφ/(2π)`，径向支持固定紧环域且 `0<ρmin≤ρ≤ρmax`。定义**共同 h 的** T 帧边缘 law

`Pbar_θ^(T) = ∫ P_(θ,h)^(⊗T) μ(dh)`。

这通常不等于 `[∫P_(θ,h)μ(dh)]^(⊗T)`：帧间共享 h，边缘化后帧/坐标一般不独立。所有 KL 和风险证明使用前一式。

当前 `L=5N/4`、ν 为整数，帧 t 的因子 `exp(2πiνLt/N)` 属于 C4，故独立均匀 QPSK 在条件 law 中已经吸收它；因此实际连续帧实验确实具有上述条件 iid 形式。一般 L 不自动满足此结论，见第 7 节。

当前先验 l 在 0,…,M−1 均匀，ν 在 0,…,N−1 均匀且独立。固定 l 时 ν↦a=ν+sl 是 Z_N 的双射，因此 θ 正好在 Θ 均匀。估计 (ν,l) 出错当且仅当估计 (a,l) 出错。

对任意允许随机化的估计器 δ，定义

`r_θ(δ)=Pbar_θ^(T){δ(Y)≠θ}`，`R_av(δ)=|Θ|⁻¹Σ_θ r_θ(δ)`，`R_Bayes^*=inf_δ R_av(δ)`。

这些风险已对共同 h 积分；不是固定 h 的条件风险，也不是对 h 再取 supremum 的原始 minimax 风险。

## 2. Delay quotient 对任意列码都成立

`E_M[j,j]=exp(−2πij/g)`，因为 g 整除 4，其每项属于 C4。于是 `E_M S` 与 S 同分布，且 C 与 E_l、E_M 均为对角矩阵。对任意 h 和任意 v：

`P_((a,l+M),h)=P_((a,l),h)`。

因此 l modulo M 是真实 law quotient，而不是只针对二次码的代数简写。保持 a 而取 l 的不同代表会相应改变物理 ν=a−sl，这不影响当前 full-circle prior 的成员资格。此步骤依赖独立均匀 QPSK，没有使用 gain 积分。

## 3. 正确处理 projective cocycle：完整 Heisenberg 群作用

令 `ζ=exp(2πi/N)`，`W_(b,c)=D_b Π_c`。由 `Π_cD_a=ζ^(−ac)D_aΠ_c` 及 `Π_cFᴴ=FᴴE_c` 得

`W_(b,c) U_(a,l)=ζ^(−ac) U_(a+b,l+c)`。

所以在条件 law 上，unitary 变换同时把参数平移并把 gain 旋转：

`W_(b,c)# P_((a,l),h) = P_((a+b,l+c),ζ^(−ac)h)`。

加法在 a mod N、l mod M 上解释。圆对称 gain 先验使该相位旋转保持 μ，故在 T 帧上对每帧施加同一 W 有

`W_(b,c)# Pbar_(a,l)^(T) = Pbar_(a+b,l+c)^(T)`。

**不可直接声称 Θ 在观测向量上有 faithful 的 W_(b,c) 表示。** `W_(0,M)=Π_M` 通常不是 identity；两个商代表的矩阵未必相同，而且 W 的乘法有中心相位。

严格做法是使用有限 Heisenberg 群 `H_N={(r,b,c):r,b,c∈Z_N}`，表示为 `ζ^rD_bΠ_c`，乘法为

`(r,b,c)(r',b',c')=(r+r'−b'c, b+b', c+c') mod N`。

H_N 在观测空间有真实 unitary 群作用，在参数上的作用为 `(a,l)↦(a+b,l+c mod M)`。中心 r 及 c 的 M 倍代表属于 label-action kernel；它们不必固定每个观测向量，但固定对应边缘 law。该参数作用是传递的，足以完成对称化和下面的 pair 平移证明。

## 4. 边缘 KL 上界：不偷换条件与积分后 law

旧 QUADRATIC_BARRIER 对 `v_j=exp(−2πic2 j²)`，给定 1≤K<N，取 `1≤k≤K`、整数 d，使

`ε=2Nc2 k−d` 满足 `|ε|≤1/K`。

取 `d'=d mod M`，困难相对参数 `δ0=(k,d')≠(0,0)`。旧 no-wrap/wrap 推导意味着存在一个与 ρ、φ 无关的常数相位 β（吸收公共二次 chirp 常数及代表变化的公共相位），使所有 h=ρ exp(iφ) 均满足

`KL(P_((0,0),h) || P_(δ0,exp(iβ)h)) ≤ (ρ²/σ²) B_N(K)`，

其中 `B_N(K)=4K+4π²N/K²`。d 的代表变化只引入逐坐标 C4，可通过 symbol 标签重排消去，不改变此条件 KL 界。

T 帧在固定 h 后独立，**同一** β 可用于全部帧，所以条件产品 KL 的上界乘 T。现在构造两个含 latent h 的联合分布：

`J0(dh,dY)=μ(dh) P_((0,0),h)^(⊗T)(dY)`，

`J1(dh,dY)=μ(dh) P_(δ0,exp(iβ)h)^(⊗T)(dY)`。

μ 对 h↦exp(iβ)h 不变，因此 J1 的 Y 边缘正是 `Pbar_δ0^(T)`，而不是某个改变先验后的替代模型。由 KL data processing / joint convexity：

`KL(Pbar_0^(T)||Pbar_δ0^(T))`

`≤ KL(J0||J1) = ∫ KL(P_(0,h)^(⊗T)||P_(δ0,exp(iβ)h)^(⊗T)) μ(dh)`

`≤ [T Eρ²/σ²] B_N(K) =: C_N`。

当前 ρ~Uniform[.75,1.25] 给 `Eρ²=(.75²+.75·1.25+1.25²)/3=49/48`，不是把隐藏 gain 固定成 1，也没有通过已知 σ²泄露真实 ρ。

第 3 节的 law equivariance、unitary KL 不变性进一步给所有 θ：

`KL(Pbar_θ^(T)||Pbar_(θ+δ0)^(T)) = KL(Pbar_0^(T)||Pbar_δ0^(T)) ≤ C_N`。

## 5. 全部困难 pair 求和：平均风险没有稀释因子

对每个 θ，用 δ 的输出诱导二元检验：若输出 θ 则选 θ，否则选 θ+δ0。其在两个假设下的错误率分别不超过 `r_θ(δ)` 和 `r_(θ+δ0)(δ)`。故 equal-prior binary Bayes error e_B 与 Bretagnolle–Huber 不等式给

`[r_θ(δ)+r_(θ+δ0)(δ)]/2 ≥ e_B(Pbar_θ,Pbar_(θ+δ0)) ≥ exp(−C_N)/4`。

对全部 θ 求和，因为 θ↦θ+δ0 是 Θ 的置换，左边平均正是 R_av(δ)，所以

`R_av(δ) ≥ exp(−C_N)/4`。

此论证对任意估计器成立，取 inf 即得到开头的 Bayes 下界。无需选 disjoint pairs，也不要求 δ0 的群阶为偶数；沿可能奇数长度的循环双计数后仍恰好覆盖每个风险两次。尤其没有只对单个 pair 赋 prior 2/|Θ| 而产生的稀释。

补充的对称化事实：对任何 δ，均匀抽 g∈H_N，将 Y 变换为 gY，再将 δ(gY) 的 label 逆变换，可构造随机估计器 δsym，使所有 θ 的风险均为原 R_av(δ)。因此

`inf_δ average_θ r_θ(δ) = inf_δ sup_θ r_θ(δ)`。

这里等号右边仍是**h 已按 μ 平均后的** minimax，不能直接与旧 `inf sup_(θ,h)` 混同。上面的 latent coupling 正是从旧条件困难 pair 到新边缘 law 的必需环节。

## 6. 对实际 FOURTH / SCREEN32 / FULL 的含义

Bayes 下界不要求实际估计器等变，因此无论下列实现细节如何，三者平均风险都受该下界约束；等变性只帮助解释哪些层面保持统计实验的均匀性。

### 四阶筛选的等变性

在 FFT 坐标 X 中，施加 W_(b,c) 给 `X'_j=exp(−2πic(j−b)/N) X_(j−b)`。于是协议中的 score 满足

`Score_(a',l')(W_(b,c)Y)=Score_(a'−b,l'−c)(Y)`，

其中 l modulo M。任意 unit-modulus v 都有这一 score 置换恒等式。FOURTH argmax 与 top32 集合在无 ties 时相应置换；固定最低 label 的 tie-breaking 一般不等变。若模板不成公共相位比例、噪声密度连续，则这种 exact score tie 通常是零概率集合；但若存在实际结构性 ties 或浮点 ties，不能无条件删掉这一实现例外。

### 当前有限 gain 网格并未自动破坏对称性

生产网格相位为 `rπ/32, r=0,…,15`，标量 QPSK law 又有 π/2 周期；有效相位集等价于 full-circle 的 64 点网格。Weyl cocycle 只引入 `2πq/N` 的旋转。

**N=32 和 N=64 都整除 64，故所有这些旋转都保持当前 phase-grid law 集合。** 固定三个 magnitude 也受 unitary action 保持。因此当前 FULL 的 gain-profile score 对 Weyl label 变换闭合，SCREEN32 继承同一性质（除 shortlist/最终 ties）。不能用“有限 phase grid”笼统解释这两个 N 的平均性能差异或对称性失效。

若推广到不整除 64 的 N，同一个 phase grid 一般不再闭合；若直接对 physical h 使用 θ 无关网格、忽略其与有效 h 的 delay 相位换算，也会改变这一结论。当前实现明确网格化 h_eff、再转换返回 physical gain，避免了后一个问题。

尽管当前 objective 有上述对称性，FULL 仍是 48-point profile likelihood，不是对 μ 积分的 Bayes MAP，也不是连续 h 的 ML；SCREEN32 还丢弃候选。对称性本身既不证明最优性，也不证明 finite-grid approximation 的损失很小。gain 的 prior 径向 uniform 与这三个离散幅度最大化不是同一操作。

### 平均风险指数可以比较，但不能偷换实际接收机

此前 COMPOSITE_LATTICE_ESTIMATION 中一般列码的 uniform-(θ,h) 指数风险上界，直接对当前先验平均仍成立。结合本报告，固定 T 时可得到**存在性层面**的一般列码与整个二次列码类的 Bayes 平均风险指数差。

它所构造的 gain net 随 N 细化、候选计算昂贵；不能据此断言当前固定 48-point FULL 或 SCREEN32 达到该上界。随机码的渐近存在性也不能自动认证本次固定 seed 在 N32/64 的条件数。

## 7. 会失效或需要新证明的边界

- **非圆对称 gain prior / gain 相位与 θ 相关：** h↦exp(iβ)h 可能改变先验，J1 的边缘不再是欲比较的 law；“存在某对 gain 相位的条件 KL 小”不足以得 Bayes 小 KL。
- **不均匀或缩窄 θ prior：** 平移不再保持 prior 或离开允许集合，全 pair 求和不再等于原平均风险。可另研究平移重叠质量，但本报告不给全域保证。
- **不同 frame clock：** 若整数 ν 的 exp(2πiνLt/N) 不在 C4，连续帧携带额外的时间相位信息。困难 pair 往往需要随 t 改变 gain 相位才能配对，不能用一个共同 h 的先验旋转吸收。当前 L=5N/4 满足所需条件；不能把结论不加条件地推到一般 L。
- **已知 pilots、非 iid payload 或 guard-inclusive observation：** E_M S 可能不再与 S 同分布；Weyl quotient 或有效窗闭合均可能失效。
- **非格点 CFO / fractional delay / multipath：** 当前 finite group 和困难 pair 构造没有覆盖这些模型。
- **随 N 增长的 T 或缩放 SNR：** 当前下界指数为 O(TN^(1/3)Eρ²/σ²)。只有在相应尺度固定时，才排除正的线性 N 指数；例如 T 达 N^(2/3) 时不能再用它作同样排除。
- **gain 相位积分后的矩：** Eμ h⁴=0，故不能把非零条件全纯四阶均值当作边缘均值继续使用。实际 score 使用同一观测上的四阶聚合及模长，保留未知公共相位下的信息；本报告下界全程针对完整边缘 law，未使用错误的边缘四阶均值。

## 8. 对本轮结果的精确解释

本报告填补了“旧 theorem 只有最坏点、现 pilot 却看均匀均值”的一个真实理论缺口。在当前先验与 clock 下，可以严格证明平均风险也有全二次类障碍。因此不应再笼统说最坏点结论必然与此均匀平均实验无关。

但保守常数包含 `T(Eρ²/σ²)[4K+4π²N/K²]`；在本轮有限 N/SNR 下，下界可极小。它并不预测 quad 的错误率应高于 random 多少，不保证 random 的优越性，更不能把未通过的 10pp gate 改称成功。此前实验的 21.183× 同波形速度比、bad=0 和均值准确率差未显著，是不同的已观测事实；新定理不能替换这些数据。

上述群作用在每个固定 N、σ² cell 内使用，不把不同观测维度或不同 SNR 当作同一群轨道。四 cell 等权平均风险的下界是相应四个 cell 下界的等权平均；这不会改变有限 N 常数可能过弱的限制。

## External references and related specs

没有新增文献检索或声称该群论/信息论技术首创。使用的 KL data processing、prior-preserving coupling、finite-group symmetrization 和 Bretagnolle–Huber 是经典工具；新的工作是把它们严格对应到已冻结 AFDM/QPSK quotient、共同 gain 先验和 current clock。以上文件为内部依据，数学细节在本文件自足展开。

## Caveats / Not Found

- 这是新的解析推导，建议主线程按其重要性安排独立数学复核后再用于对外理论主张；本文件不是数值验证或论文创新性认证。
- 仅写入本 BAYES_SYMMETRY.md，未修改代码、CSV、旧理论或已完成实验记录。
- pilot 数字来自主线程分派结果摘要，本轮没有重新读取或审计科学 raw。
