# Derivation Package：有限配对与精确概率混合回溯

## Target and Status

PAIR-BLOCK-THEORY-01。补齐有限预算 pair-block 候选的两项数学缺口：候选选择
不能免费扫描 N²；同时更新多个 block 不能借单坐标凹性声称整体单调。
COHERENT AS STATED，待独立数学审查。以下是经典 block variational inference、
Fourier 分组和线搜索在当前 AFDM/SP 模型中的组合适配，不宣称首创或已测收益。

## Invariant Object and Assumptions

固定本次更新的 q_h、各 ν 因子、delay/chirp、pilot、noise σ²>0。沿用
`G=E[H*H]`、`r=E[H*]y−G p`。数据为不相交 blocks 的乘积 q_d=∏_B q_B；
每 block 一个或两个 QPSK 符号，先验也按 block 分解，p_B(a)>0。
所有候选只使用 observation/model state；truth 不进入配对或步长选择。
block partition 在一次 proposal/line search 内固定。不同 ν 的 q 与 q_h 独立。

记 m_B=E_qB[d_B]，T_B=E_qB[d_B d_B*]，C_B=T_B−m_Bm_B*。
D 为由各 G_BB 拼成的 block-diagonal 矩阵，A=G−D。D/A 仅为代数对象，
实现不得构造其 N×N 数组。去掉固定 y/pilot/gain 项的数据目标是

F_d(q)=Σ_B [H(q_B)+E_qB log p_B]
  −[m* A m +Σ_B tr(G_BB T_B)−2 Re(m* r)]/σ²。

这是完整固定信道因子下界的数据相关部分，不是跨 q_h/ν 的完整 evidence，
也不是真实 posterior 的 log loss。只有当与 gain KL 等其他项一起组合时才成为
此前定义的完整条件变分下界。

## Derivation Map

频差 Gram → 有限 lag 候选池与上界 → 不相交配对 → 单块 Gibbs proposal →
factorwise 概率混合 → 能量二次式与精确 entropy → 单调回溯及完整成本。

## Main Derivation

### 1. 按 lag 筛选，不扫描所有 N² 对

对 k=(u−v) mod N，`PAIR_COVARIANCE_FFT.md` 已给出

G_uv=exp[2πic2(u²−v²)] Σ_ij S_ji Z_ij[k]
  exp[2πi(l_i u−l_j v)/N]。

因为 l_i 为整数，即使 u=v+k−N，也有
exp[2πi(l_i u−l_j v)/N]
=exp[2πi l_i k/N] exp[2πi(l_i−l_j)v/N]。

因此对每个非零 k，所有 v 的元素满足同一个可计算上界

|G_(v+k mod N),v| ≤ b_k := Σ_(i≠j) |S_ji| |Z_ij[k]|。

i=j 的算子严格为 I，所以在 k≠0 时不出现该项。
由于 `Z_ji[−k]=conj(Z_ij[k])` 与 S Hermitian，b_(−k mod N)=b_k。
这是 triangle inequality 的上界，未证明紧或它能正确排序实际 BER 收益。

固定 L≤N−1 后，对非零 k 按 `(-b_k,k)` 排序，选前 L 个 directed lags。
每个 lag 为所有 v 生成一条 undirected edge，规范化端点并去重。
候选数 Q≤LN；对这些候选查询精确 G_uv，不以 b_k 替代实际交互。
示例的 observation-only 排序分数可取
`w_uv=|G_uv| sqrt(v_u v_v)/σ²`，其中 v 来自上一状态的合法边缘分布；
这只是候选启发式，不是后验相关系数或理论最优匹配权重。
按 `(-w_uv,u,v)` 排序，贪心选择未占用端点，至多 K_max 个 pairs，其余 singleton。

构建全部 Z/b 为 O(P²N log N)，lag 全排序 O(N log N)，生成/去重候选
O(LN log(LN)) 的保守上界，精确查询 O(P²LN)，edge 排序/贪心
O(LN log(LN))。保留 Z 与候选需 O(P²N+LN)，不是 O(N) 总内存。
L 和 K_max 必须在性能实验前固定；选点开销与未入选候选均计费。
非零 lag 候选查询没有提供 N 个 G_ii：block 能量还需原 `gram_diagonal`，
owner 初始化还需 Gp、matched 以及初始 Gm^0。这些实际调用另行计费，虽仍在
上述 P²N log N 量级内，也不能把它们写成候选查询附带的免费结果。

本算法只限制 partition 候选池；后面的 Gm 仍使用完整物理 Gram，不截掉其他
lag 或 covariance。对未选择 lag 仍有上述元素上界，但没有自动得到 posterior
或 BER 误差界。可在第一轮从 singleton 状态选定 partition 并把 q_u q_v 嵌入
16-state q_B；这保持原联合分布和目标值。之后若更换 partition、拆开旧 pair，
一般会丢掉相关性并改变目标，不能免费视为恒等初始化；本候选不在迭代中重配对。

### 2. 精确并行 block proposal

固定其他 blocks 的旧均值 m^0，r_B^c=r_B−(A m^0)_B。每个 block 的坐标最优解为

q_B^*(a) ∝ p_B(a) exp([2 Re(a* r_B^c)−a*G_BB a]/σ²)。

这里的 * 是本坐标最优，不是全局/真实 posterior。所有 q_B^* 均在相同旧状态
计算，所以同时完整替换 q^0→∏q_B^* 未获整体单调保证。

定义 factorwise arithmetic mixture

q_B^τ=(1−τ)q_B^0+τ q_B^*,  0≤τ≤1；q_d^τ=∏_B q_B^τ。

这不是整份 joint q_d^0 与 ∏q_B^* 的二元 mixture。后者引入跨 block 相关，
不属于当前变分族，也不满足下面的二次能量表示。

### 3. 精确能量二次式：回溯不需要重复 Gram 作用

记 Δm=m^*−m^0，ΔT_B=T_B^*−T_B^0。因为每个 block 的概率算术混合，
m^τ=m^0+τΔm、T_B^τ=T_B^0+τΔT_B，精确有

E_d(τ)−E_d(0)=τ a_1+τ² a_2，

a_1=2 Re[Δm*(A m^0−r)]+Σ_B tr(G_BB ΔT_B)，
a_2=Δm* A Δm ∈R。

这由代入 m 的二次项与 T 的线性项逐项展开，没有 Taylor 截断。
QPSK 各符号模长固定，所以 diagonal T 项的差为零；pair 的 raw cross moment
一般变化，不能把整个 ΔT_B 设为零。

进而完整的本次固定因子目标差是

ΔF_d(τ)=Σ_B[H(q_B^τ)−H(q_B^0)]
  +τ Σ_B E_(q_B^*−q_B^0) log p_B −(τ a_1+τ² a_2)/σ²。

非均匀 prior 的线性项不能漏；当前 uniform uncoded QPSK 情况该项为零。
只需已有 Gm^0、一次 GΔm 和已查询的 block entries：
A m^0=Gm^0−D m^0，a_2=Δm*GΔm−Σ_B Δm_B*G_BBΔm_B。
每个 τ 的新开销只剩 finite probabilities/entropy 与标量式，无新的 Gram/FFT。
接受后 `Gm^τ=Gm^0+τGΔm` 也精确成立；只在同一固定 G owner 内可复用，
后续 gain/ν/geometry 改变时该身份不允许沿用旧缓存。

实际 C_B^τ=T_B^τ−m_B^τ(m_B^τ)*，不是 C_B^0 与 C_B^* 的简单线性平均。
接受的 q_B、mean、variance、cross covariance、entropy 必须从同一 q_B^τ 产生。
数据线搜索无需为每个 rejected τ 构造 W/K；接受后给 gain/ν 使用的 SourceMoments
仍须包含完整 C_B，并按 owner 合同刷新。代数复用不省略实际计算的记账。

### 4. 为什么回溯存在上升方向

假设 q_B^0 与 q_B^* 在有限 alphabet 全部严格正。由 Gibbs 定义与概率和为 1，

dF_d(q^τ)/dτ |_(τ=0)
=Σ_B Σ_a (q_B^*(a)−q_B^0(a)) log[q_B^*(a)/q_B^0(a)]
=Σ_B [KL(q_B^*||q_B^0)+KL(q_B^0||q_B^*)]≥0。

只要至少一个 block proposal 真正改变，这个导数严格正，连续性保证存在充分小
τ>0 使 ΔF_d(τ)>0。这是局部存在性，未给统一的步长下界或迭代收敛速度。
若两者全部相同，Δm=ΔT=0，所有目标差为零。

实现可预设有限步长表 `1,1/2,…,2^(−J)` 并按精确目标选择首个合格项。
有限 J 未必包含足够小的 τ；因此必须保留“本步拒绝、状态不变”的真实结果，
记录全部试步及开销，不能声称每步都严格改善。浮点实现需另冻结有限容差，
完整概率在极端 logits 下的下溢也需显式处理，不能把数学正性当作运行时保证。

## Degeneracies and Limits

- Singleton partition：同一推导成立，作为 matched 控制，不以 pair 与旧不同步长
  算法的总差异冒充纯相关性收益。
- G block diagonal：A=0，二次项 a_2=0，各 q_B^* 可同步到位；目标变成各块可加。
- 所选 block 内 G_uv=0：对应 Gibbs proposal 在 independent prior 下分解；pair
  存储不自动创造有用相关性。
- 只有一条完整 CPP 物理路径时，每个 H_1(ν) 均为 unitary，所以固定 q_h/ν
  的 G=E|h_1|² I，即使 ν 的因子有非零宽度也成立。此时最优 q_d 已完全分解，
  pair family 不提高该固定因子目标；因此本候选的目标机制是多径交互，而非
  单径中仅因 fractional ν 就存在的 data-block 收益。真实积分后仍可能存在
  gain-data/ν-data 依赖，本结论没有消除那些关联。
- q_h/ν 更新后 G/r 改变：旧二次式和缓存均不再适用，不能跨 sweep 比较旧多项式。
- 本推导不恢复 q(h|d) 的 gain-data 依赖；它只扩大 q_d 的 block family。

## Cost and Scientific Interpretation

完整候选仍需测量 acquisition、G/Z 构造与有限 edge 搜索、所有 gain/ν 更新、
接受/拒绝步、最终保存和 LDPC。一次 line search 可省重复 Gram 作用是代数事实；
目前没有相关实现或计时，不能把理论操作量直接写成 speedup。
只有与相同步长/轮数/初始化的 singleton 控制比较，才能检查 pair 相关性的增量。
pairing、块同步和 FFT 都有既有方法先例，实际 AFDM+SP 连续多径收益尚未建立。
