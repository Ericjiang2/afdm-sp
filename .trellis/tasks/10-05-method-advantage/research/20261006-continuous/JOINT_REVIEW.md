# Research: 联合可辨识性及最小已知符号边界的独立审查

- Query: 独立挑战完整 law 判据、符号、连续帧反例、Alltop 与常规二次码基线、四阶张量距离，以及新增单/双已知符号命题。
- Scope: internal，手工数学审查；JOINT-01 与 VALUE-01 的指定理论稿。
- Date: 2026-10-06

## Findings

### 结论

PASS（限定于文稿明确的循环单径、整数时延、已知有效块边界、固定非零增益、同方差 proper Gaussian 噪声和总体分布模型）。未发现当前版本的阻断性代数错误。此前发现的行 chirp 周期性假设缺失已由主线程修正并核实：必须同时声明 s∈Z 与 sN∈2Z，不能只要求后者。反例 N=4、s=1/2 虽满足 sN=2，却有 R[n+N]/R[n]=(-1)^n。

这不是重大创新或有限样本效用的通过结论。常规二次码基线已达到最小不可避免歧义群，故三次码“恢复常规 AFDM 基本可辨识性”的必要性主张不成立。双已知符号结果是改变无导频模型后的常规机制解释。

### 文件与相关约束

- `JOINT_IDENTIFIABILITY.md:13`：共同物理假设、变换与循环索引定义。
- `JOINT_IDENTIFIABILITY.md:26`：完整分布的 unitary monomial 判据。
- `JOINT_IDENTIFIABILITY.md:31`：Q 矩阵、非整数排除和 Weyl 系数判据。
- `JOINT_IDENTIFIABILITY.md:44`：二次 CAZAC 歧义与连续帧反例。
- `JOINT_IDENTIFIABILITY.md:55`、`:60`、`:71`、`:76`：普适障碍、Alltop、无理/小有理二次码基线。
- `JOINT_IDENTIFIABILITY.md:81`、`:98`：完整全纯四阶张量距离及物理解释边界。
- `SEMI_BLIND_BOUNDARY.md:8`、`:19`：双/单已知符号与连续帧条件。
- `CONTINUOUS_THEORY.md`：沿用此前零时延审查上下文及其第 6 节联合歧义反例，本轮未重新审查所有 CLT 推导。

以上路径均相对本研究目录。适用规格为分派中明确的研究文件所有权、禁止仿真/SSH/源码修改和主稿的数学假设；未重新加载实现或检查 manifest。

### 1. 完整分布、非整数排除与符号

Gaussian 特征函数处处非零，故相同已知噪声下可反卷积；协方差给出 |h0|=|h1|。unitary 行 r 满足 E|rS|⁴=2−Σ|rj|⁴，输出保持单位模 QPSK 必须令 Σ|rj|⁴=1。结合 Σ|rj|²=1 得每行恰一个非零项。unitary 再给置换，未知公共增益相位调整后系数属于 C4；反向由独立均匀 QPSK 的置换和逐坐标 C4 不变性成立。这是完整 law 的 iff。

Q=E_l0ᴴ Cᴴ F D_k Fᴴ C E_l1。非整数 k 时有限几何和分子 1−exp(2πik) 非零，分母为零反会要求 k 整数，故每个元素非零。N>1 下它不能是 monomial。这里排除的是有效频偏差 k=Δν+sΔl 非整数，而非把任意单个实 CFO 排除。

整数 k 时 row j 取 column j−k，其系数为 (v_(j−k)/v_j) exp(−2πidj/N) exp(2πil1k/N)。四次幂去常数后恰为 w_(j−k) conjugate(w_j) exp(−2πi4dj/N)。单位复数均值模长为 1 iff 全部相同，故 law 相同 iff k∈Z 且 |A_w(k,4d)|=1，符号正确。

二次 w_j=exp(−πiqj²/N) 给 A_w(k,m)=exp(−πiqk²/N) 1_(qk=m mod N)。因此 qk=4d；比较真 (ν,l) 与 (νeff,0) 时 d=−l，得到 νeff=ν+(s−4q⁻¹)l。N64、s5、q1、l1 的 νeff=ν+1 正确；L80 给 4LΔν/N=5，连续各帧相位均可被未知 QPSK 吸收。该反例仍须两个假设同时落在 prior 内且 guard 不观察。

### 2. 普适障碍及公平基线

A_w(0,4d)=N⁻¹Σ exp(−2πi4dj/N)，所以等于 1 恰在 N|4d。令 g=gcd(N,4)，d=N/g、Δν=−sd 即 k=0。g>1 时这是非平凡、与列码无关的障碍；奇 N 时 d=N 是同一模 N 时延，不产生额外障碍。连续帧条件 4LΔν/N=−4Ls/g∈Z 自动满足。标题中的 composite 不应理解为所有合数都有障碍，正文对奇 N 的限定正确。

对无理 c2，f(j)=(j−k mod N)²−j² 在两个索引段分别具有非零整数斜率 −2k 与 2(N−k)。N≥3 保证至少一段含相邻索引，恒定 summands 将要求 −4c2Δf−4d/N∈Z，不可能。因此所有非零 k 均排除。

新增小有理 c2 证明也成立。相邻项相位增量绝对值为 8|c2|t，1≤t≤N−1。若其严格小于 1/N，则无法抵消 4d/N 的非整数剩余（到整数的最小非零距离为 g/N），也无法抵消整数剩余。c2=1/(10N²) 给 0.8(N−1)/N²<1/N，满足条件。结论仅是这一参数值对应的数学基线；本轮未独立追踪其生产配置来源。

因此这两种常规基线均恰留下 N|4d 的不可避免群。三次码的潜在区别最多是可证明的定量 lattice separation，尚未证明相对这些基线的实际统计收益。

### 3. Alltop 与四阶距离

p≥5 prime、k≠0 时，三次差的系数是 −3k j²+(3k²−m)j−k³，二次首项非零。平方 Gauss 和模长、以 j=t+u 展开，非零 u 的 t 和为零，u=0 项为 p，故 |A|=1/√p。k=0 时只有 m=0 非零；4 在模 p 下可逆。因此唯一 |A(k,4d)|=1 的点是 k=d=0。配合非整数排除，所得实 CFO 与整数时延的总体 law 可辨识性成立，增益仍有内禀 C4 相位歧义。

T(U)=Σu_j^⊗4 的项因列正交而正交，范数平方为 N；完整 ordered 四重索引 Frobenius 内积为 Σ_ab (u0_aᴴu1_b)⁴。整数 k 下只有 monomial 项，内积模长为 N|A|。对公共相位最小化给 2N|h|⁸(1−|A|)，系数正确。proper Gaussian 的纯全纯四阶矩为零，QPSK 混合配对因 E S²=0 消失。此处计算的是完整 (4,0) 张量块，不是把所有共轭类型合并的“四阶统计总距离”。Alltop 下 distinct lattice 的下界正确；不覆盖任意接近的实 CFO，不给误差率或样本复杂度。

### 4. 双已知符号新增稿

N≥3 下 trace(K−σ²I)=(N−2)|h|² 非零，可识别增益幅度。等 covariance 推出 QP_JQᴴ=P_J。非整数 k 的 Q 全稠密，而保持坐标子空间要求 J 列在 J 外的项为零，直接矛盾，包括 N=3 的边界。

整数 k 时 preservation 等价于 J+k=J。对 J={0,1}，因 k 是 0 的像，必须 k∈{0,1}；若 k=1 则 1 的像 2 不在 J（N≥3），故只有 k=0。这补全了 adjacent pair stabilizer 的穷尽性。此时 Q=E_d；坐标 0 的非零已知均值确定 h0=h1，坐标 1 确定 exp(−2πid/N)=1，故 d=0、Δν=0。对任意 v 成立，且不再有 C4 gain 歧义。这里 h 是吸收行 chirp 常数后的增益；一旦参数确定，可恢复对应原始物理增益。

单已知符号时同样由 covariance 确定 k=0，均值只固定 h1/h0=exp(2πidj0/N)。剩余 QPSK 要求 exp(−2πid(j−j0)/N)∈C4。总存在循环相邻随机坐标，故必要且充分条件正是 N|4d。奇 N 一导频已足够；偶 N 的单帧 unrestricted 模型保留 g 个分支。这不是所有场景都必须双导频的结论。

连续帧的非零导频均值要求额外相位恰为 1，不能再只要求属于 C4。J={0} 的歧义需 Lsd/N∈Z；N64、L80、s5、d16 给 100，成立。文稿明确区分单帧与连续帧，正确。

### 5. 物理与交付边界

Unew=U_AFDM P、unit-modulus diagonal P 给有效信道 PᴴH_effP，逐元素只乘非零相位，保零模式与奇异值。它不保有限字母表差向量集合，故不能推出 full diversity、BER 或 PAPR 不变。文稿的限制正确。

本轮只完成静态数学核查，没有科学运行、有限样本估计验证、代码实现或新文献检索。双导频的均值/协方差是总体对象，需要数据与相干性支持才可估计；“单帧总体 law 可辨识”不能写成“单次观测精确恢复”。

## External references and related specs

本轮未访问外部资料或判定文献新颖性；Alltop/Gauss 和步骤已在上述限定域内直接代数核验。没有版本化外部 API 或依赖变更。相关约束仅为共同模型及本轮交接的研究范围，未声称读取未加载的项目规格。

## Caveats / Not Found

- 当前两稿未发现未修复的阻断性数学错误；已核实 s 整数假设修订。
- 实际小有理基线的数学结论通过，配置来源不属于本轮核查证据。
- 三次码优于常规基线、双导频有限样本价值、最近邻文献新颖性与重大创新目标均未建立。
- 无须扩大仿真或重新推导旧零时延 CLT 来关闭本轮指定代数审查。

## Follow-up: STATISTICAL_SEPARATION.md 的完整分布统计分离

- Query: 挑战固定正 SNR 下 small-c2 相邻 CFO 的 O(1) KL 上界与 Alltop 的 exp(−cN) affinity 上界。
- Scope: internal，纯数学追加审查，无数值运行。
- Date: 2026-10-06
- 文件：`STATISTICAL_SEPARATION.md`，scalar mixture lemma、lattice affinity proposition、hard adjacent-CFO pair 与 tensor limit 四部分。

**结论：核心单帧命题 PASS。** 这是比“基本可辨识性恢复”更实质的定量差异，但仅针对指定 small-c2 基线、同 prime N、固定每坐标 SNR 与允许单位子载波 CFO 差的参数域；尚不等于相对优化常规基线的优势或实际复合参数接收机结果。

### Scalar lemma 核验

有限同方差正 Gaussian 混合密度处处正、对相位光滑。可以把 QPSK 标签加入 complete-data 模型：位置均值的导数长度为 ρ，complete-data 相位 Fisher information 为 2ρ²/σ²；observed score 是 complete-data score 的条件期望，故 Iθ≤2ρ²/σ²，有界。Gaussian 尾部与有限分量支持所需的平方根密度二次均方可微性，因此 b(θ)=1−Iθθ²/8+o(θ²) 的系数正确。

若 Iθ=0，正密度会使 ∂θfθ 几乎处处为零；光滑性给处处为零。但全纯四阶矩为 κρ⁴exp(4iθ)，导数 4iκρ⁴ 非零，Gaussian 尾部允许交换求导和积分，矛盾。因此 Iθ>0。1−cos(4θ)=8θ²+o(θ²)，比值趋于 Iθ/64>0。其余 C4 点由周期性处理，远离这些点由紧致性与 Gaussian 反卷积给严格正下界。全域存在固定 c>0 的结论成立；不声称 c 对 SNR 一致。

### Affinity 乘积与未知相位

整数 k 的 unitary 相对变换为 monomial，白 Gaussian 仍坐标独立，QPSK 置换不改变产品 law，故 affinity 精确等于各坐标 scalar affinity 乘积。b≤exp[−c(1−cos4θ)]，公共 gain 相位 β 的最坏情况使余弦和取 |Σexp(4iθj)|，因此 supβ Aff≤exp[−cN(1−|A|)]，方向与系数正确。Alltop 的非平凡 lattice 点由 |A|≤1/√N 给一致指数上界。这里 c 与 N、码或相位无关，只依赖固定 ρ、σ。

已知一对简单假设的 Bayes error 满足 Pe≤Aff/2，故每对固定相位选择均有指数上界。它不能推出存在一个同时处理所有未知相位的复合检验器，主稿对此已有正确限定。

### Small-c2 KL 与 tensor 极限

同一 QPSK 标签耦合的 Gaussian KL 为 ρ²|1−exp(iθ)|²/σ²；边缘化由 data processing 给 mixture KL 上界。k=1、d=0 的 N−1 个常规相位为 2πc2(2j−1)，wrap 相位为 −2πc2(N−1)²，符号正确。对 c2=α/N²，常规项平方和≤16π²α²/N，wrap 项≤4，因此完整产品 KL≤(ρ²/σ²)(4+16π²α²/N)。可再以 N≥3 得显式统一常数 (ρ²/σ²)(4+16π²α²/3)。Bretagnolle–Huber 给 Pe≥exp(−KL)/4，因而在 N→∞ 时此 pair 的误差不能消失（SNR 固定，界可能很小）。选取相等的变换后 gain phase 合法，是构造一个难 pair，不是对所有相位的 KL 上界。

四次幂的常规相位为 8πc2(2j−1)；其总实部亏损 O(1/N)、总虚部 O(1)，wrap 项趋于 exp(−8πiα)。故 Re A=1−[1−cos(8πα)+o(1)]/N，Im A=O(1/N)，N(|A|−Re A)=O(1/N)→0，给出所述 N(1−|A|) 极限。该辅助张量结果与 KL 比较一致。

### 唯一需澄清的重复帧措辞

“T 次 affinity 为单帧的 T 次方”严格适用于相同分布的独立重复。若继承 CONTINUOUS_THEORY 的连续 CFO 帧间相位，βt=β0+2πΔνLt/N，一般每帧 affinity 不同，精确式应为 ∏t Aff_t；不过每帧均适用相同 uniform-β 上界，所以 Alltop 的 exp[−cTN(1−1/√N)] 上界仍成立。建议把原句限定为 iid 重复，并附连续帧乘积版本，避免将相位演进默认为相位重置。此措辞问题不阻断任何单帧分离结论。

### 限制

固定每符号 SNR 意味着一帧总发射能量随 N 增长，这正是稿件假设，不能转成固定总帧能量下的指数结论。比较须使用同 prime N 和可容纳间隔 1 CFO 的 prior；若实际搜索区间更窄，该难 pair 不在任务内。优化二次 c2、不同能量预算、连续非格点 CFO、multipath 及可实现估计器均未审查或证明。外部文献新颖性未检索。

## Follow-up: 任意二次码障碍与随机码存在界

- Query: 独立挑战 Dirichlet 归一化、循环 wrap、商空间代表、KL 常数、最坏 pair 指数含义，以及 random-code McDiarmid 界。
- Scope: internal；只追加本报告，无源码、抽样、仿真或 SSH。
- Date: 2026-10-06
- 文件：`QUADRATIC_BARRIER.md`（Target、Dirichlet step、Allowed parameter representatives、KL upper bound、Comparison）；`STATISTICAL_SEPARATION.md:48`（随机相位码存在性）。

**判定：全部代数及集中界通过，但最坏 pair 的定义必须明确限制在整数有效频偏格点。** 所读版本开头只写 CFO full circle、distinct allowed hypotheses，后面的比较才写 integer lattice。如果开头理解为所有不同实 CFO 的 pair，则任何码均因连续性而有 KL 的 infimum 为 0，随机码的一致指数分离也不成立。可定义 a=ν+sℓ∈Z mod N 的共同有限格点，或明确只比较 k=Δa∈Z 且 (k,d) 非平凡的 pair。后文的证明已经支持这个限定；这属于必要的定理域澄清，已发主线程，不是推导中的常数错误。

### Dirichlet 与代表群

K+1 个 fractional parts 放入 K 个区间确实给 1≤k≤K、整数 d，使 |2Nc2k−d|≤1/K。对 no-wrap j≥k，v_(j−k)/v_j 的相位为 4πc2kj−2πc2k²；加入 E_d 后，去公共相位留下 2π(2Nc2k−d)j/N。归一化无缺失的 2 或 4。其绝对相位严格不超过 2π/K，wrap 坐标恰有 k 个。

令 g=gcd(N,4)、M=N/g、d'=d mod M，则 d−d'=rM。更换 d 为 d' 给逐行 exp(2πirj/g)，加上 l1k 项产生的公共常数；前者属于 C4、后者由未知 gain phase 吸收。因此两者的标量 QPSK mixture 完全相同，无须保持 Gaussian 标签不变，必要时作逐坐标 C4 标签重排。

ℓ0=0、ℓ1=d' 都在 J={0,…,M−1}。ν0=0、ν1=k−sd' mod N 均在 full-circle prior，有效差仍为 k mod N；1≤k≤K<N 保证 pair 非平凡。J 中任意两不同 ℓ 的差绝对值小于 M，故不能是非零 universal-group 元素；k=0 时 m=4d≠0 mod N。这一商代表选择成立，但确实使用可随 N 增长的宽 delay prior 与足够 guard。

### KL 常数与最坏 pair 指数

对调整标签后的 no-wrap 项，|1−exp(iθ)|²≤θ²≤4π²/K²；wrap 项≤4。产品 KL 因独立性相加，得到 SNR[4k+4π²(N−k)/K²]≤SNR[4K+4π²N/K²]，正确。取 K=floor(N^(1/3))，对 N≥8 有 K≥N^(1/3)/2，故显式上界 SNR(4+16π²)N^(1/3) 足以给 uniform O(N^(1/3))，允许任意实 c2 随 N 优化。

BH 给该构造 pair 的 Pe≥exp[−C N^(1/3)]/4。若 R_N 定义为允许格点 pair 及其 gain phases 中简单假设最优 Bayes error 的 supremum，则 R_N 也满足此下界，故 −log R_N/N→0；这准确表达“无正的最坏 pair 线性误差指数”。它不表示错误概率有固定正下界，也不提供某个可实现未知参数估计器的收敛率。

随机码使所有允许格点 pair、所有公共相对相位的 Pe≤exp[−cN(1−o(1))]/2，则同一 R_N 具有正的线性指数下界。这里比较的是一族各自知道两个候选分布的简单检验风险，不是已构造一个同时解决所有候选与 nuisance phase 的检验器。主稿的这个限制正确且必须保留。

### McDiarmid 常数与依赖性

k≠0 时两个 w 坐标不同，独立均匀相位保证每个 w_(j−k)conjugate(w_j) 期望为零，即使 k=N/2 也成立。summands 彼此可以依赖；McDiarmid 使用的是 N 个独立输入 w_j，而不是假定 N 个 summands 独立。

改变一个 w_j 至多影响两项，各项变化模长≤2，因此 A 的总变化≤4/N，实部和虚部的 bounded-difference 常数也≤4/N。常数平方和为 16/N；各实部双边尾界为 2exp(−Nu²/8)。|A|≥t 蕴含 |Re A| 或 |Im A|≥t/√2，union bound 正好给 4exp(−Nt²/16)。再对 N(N−1)<N² 个 (k,m) 联合，t=sqrt[16 log(4N²/δ)/N] 确保失败概率≤δ。固定 δ∈(0,1) 时存在确定性码序列使 t=O(sqrt(log N/N))；无实际码搜索或部署证据。

对 k=0、m≠0，A=0 是确切几何和，与随机性无关。故在上述 delay 代表集和整数有效频偏格点上，随机相位码确实具有 exp[−cN(1−t)] 的 uniform-phase affinity 上界，包括充分大的 power-of-two N。取任意逐坐标四次根得到 v 不改变这一结论。

### 科学限制与状态

这追加证明补上了“允许任意优化 c2 的二次列 chirp 类”这一理论基线；不应再把该具体基线比较列为完全未处理。但障碍 pair 的 k 可到 N^(1/3)，d' 可遍布 N/g 个代表，故不能声称现实短 delay、窄 CFO prior 也有同样障碍。也没有覆盖任意非二次传统预编码、非格点局部分辨、有限总能量、样本预算、PAPR/diversity 或多径性能。固定每符号 SNR 和同长度比较仍必要。新颖性和最接近文献尚未核查。

本次审查未发现随机码常数或 Dirichlet 推导错误；唯一需主稿修订的是将格点限定提升到最坏 pair 的定义处。主线程另告知先前连续帧 T 次方措辞及能量限制已修订，本轮未再次逐字核查这些与新证明无关的旧段落。

## Follow-up: 格点定义修复与未知复增益的复合估计器

- Query: 核实格点域修订，并审查 moment–Cauchy affinity 常数、增益 annulus 网格、统一似然控制与二元检验下界归约。
- Scope: internal；手工数学审查，仅追加本报告。
- Date: 2026-10-06
- 文件：`QUADRATIC_BARRIER.md` 的 Target 与 invariant；`COMPOSITE_LATTICE_ESTIMATION.md` 的全部命题。

**PASS。前节格点定义问题已经修复并逐字核实。** QUADRATIC_BARRIER 现在明示 a=ν+sℓ∈Z mod N、全部 N 个格点，并把 invariant 限定为 distinct allowed lattice hypotheses。此前要求不再是未关闭缺陷。

新增复合估计器证明也通过限定模型下审查，未发现常数或 uniformity 漏洞。它补上了本报告早先“尚无复合估计器证明”的具体缺口：在指定宽格点域、已知固定增益幅度上下界及固定正噪声方差下，确实存在仅依赖数据与已知模型的有限网格 ML 估计器，其最坏格点估计错误率有正线性 N 指数。这里证明的是存在性和数学风险界，没有实现或实验验证。

### 1. 不等增益幅度的显式 affinity 界

令 B=∫√pq，平方根密度差的 L2 范数平方为 2(1−B)。由 Cauchy–Schwarz 及 (√p+√q)²≤2(p+q)，得到 |Δm4|²≤4(1−B)(Ep|z|⁸+Eq|z|⁸)≤8M8(1−B)。复值 z⁴ 不影响 Cauchy–Schwarz 的模平方形式。

Gaussian 加固定模信号的八阶绝对矩系数为 binom(4,r)²r!，即 1、16、72、96、24，故稿件 M8 正确。对 A=ρ0⁴、B'=ρ1⁴，|A−B'exp(i4Δφ)|²=(A−B')²+2AB'(1−cos4Δφ)≥2ρmin⁸(1−cos4Δφ)。因此 c0=ρmin⁸/(4M8) 正确，统一覆盖 annulus 内不同增益幅度。gain 下界必须严格正且不随 N 趋零；这是稿件明示条件。

共用 U0ᴴ 后整数格点相对变换为 monomial，噪声和混合密度仍为坐标产品。各坐标应用同一 c0 后，对公共相位最优化即得 exp[−c0N(1−|A_w|)]；不等幅度不会破坏该推导。

### 2. 网格与 log-density 控制

固定紧 annulus 是二维有界集合，可取点均在其中、覆盖半径 N⁻²、大小 O(N⁴) 的 Euclidean net。若上下界相等退化为圆，也仍满足该大小上界。与 |Θ_N|=N²/g 相乘给 O(N⁶) 候选，这是候选数而不是运算总复杂度。

单位模 QPSK 给 ||hUθS||=|h|√N；令 C 大于 ρmax 加适当噪声阈值，Gaussian norm 的指数尾界使 P(||y||>C√N)≤exp(−cE N)，常数统一于 θ 与 annulus 内 h。

对单个 Gaussian component，沿复 gain 增量的对数导数绝对值≤(2/σ²)(|z|+|h|)|dh|；mixture 的 log 导数是 component score 的 posterior 加权平均，所以同样有界。连接两个网格/真实增益的线段可能穿过 annulus 内洞，但仍在半径 ρmax 的圆盘内，密度和导数在该圆盘处处存在，故不产生问题。求和并用 Σ|zj|≤√N||y||，因每个 Uθ unitary，在事件 E_N 上得到统一 C1N Lipschitz 常数。

于是正确 θ 对应最近 gain 网格点的 log likelihood 与真实值差至多 C1/N。若 ML 选择错误 θ，至少一个错误候选满足 likelihood ratio≥exp(−C1/N)。对 sqrt(likelihood ratio) 使用 Markov，因其在真实分布下期望就是 affinity，概率≤exp(C1/(2N)) Aff。这个检验不使用 true gain；true gain 仅用于证明与网格近似比较。

### 3. 风险界与二次类下界

有限候选 union bound 加 E_N 的补事件，恰给稿件 exp(−cE N)+O(N⁶)exp[C1/(2N)−c0N(1−μ_N)]。当 μ_N=o(1)，多项式因子贡献 O(log N)，故存在 N 无关正指数常数；可取任意小于 min(cE,c0) 的常数用于充分大 N 的指数界。所有常数可仅依赖固定 annulus、噪声及固定的渐近码界，从而支持对真实 θ,h 的 supremum。

Alltop 在 prime N 以及已证明存在的随机相位码序列在含 power-of-two 的一般 N 下均满足所需 μ_N=o(1)。随机码在此是选定并为接收机所知的确定性 realization；没有把新码未知性纳入统计 nuisance，也没有实际抽样记录。

任意 θ 估计器可在二次码障碍的两个参数点上诱导二元检验：输出 θ0 时判 0，否则判 1。在 θ0 下二元错误等于 θ 估计错误，在 θ1 下二元错误不超过 θ 估计错误；因此最坏 θ 错误≥二元平均错误≥二元 Bayes error。障碍 pair 可取相同幅度、幅度位于同一 annulus、任意所需公共相位，故 BH 下界 exp[−O(N^(1/3))]/4 合法。这个归约统一约束所有 θ 估计器，并非仅某个候选 ML 算法。

因此在此冻结格点模型内，“一般已知 unit-modulus 列相位码可有正线性 minimax acquisition-error 指数，而所有二次列 chirp 不可有”具有完整上下界支撑。没有证明二次类 N^(1/3) 是紧速率；也没有证明一般码的最优指数常数。

### 4. 尚未覆盖

精确混合似然的大型有限网格是数学构造，不是已部署或高效的 receiver。宽 CFO 和随 N 增长的 delay prior、足够 guard、单路径、固定每符号 SNR、已知噪声及已知严格正 gain 下界仍是必要作用域。实际短 prior、连续 CFO refinement、固定总能量、多径和 BER 尚无此结论。最近文献中的精确增量也未查明。除指定新增稿及格点修订外，本轮未重复读取或重验此前无关内容。
