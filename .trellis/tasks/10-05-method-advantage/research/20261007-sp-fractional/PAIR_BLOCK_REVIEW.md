# PAIR-BLOCK-THEORY-01 独立数学审查

结论：**PASS（数学恒等式、局部上升方向和成本结构）**。无开放阻断数学项；没有实现、数值试验、运行速度或 BER 证据。有限步长表可以全部拒绝，不能据本报告宣称每步严格改善或全局收敛。

- 审查时间：2026-10-08T03:41:11.103604+00:00
- 审查对象：`PAIR_BLOCK_UPDATE.md`
- 对象 SHA-256：`e1f8ad39793c27ba3b3642f77dafcafc93fa35b66284c371240d5ace90ae1f9f`
- 审查会话：`/root/trajectory_identity_review_live`；实际 model/reasoning metadata 不可核验，不宣称指定模型或跨模型验证。
- 复用已审 `PAIR_COVARIANCE_FFT.md` 的 CPP、Z 和 S_ji 约定。只有本报告落盘，没有数值 import、SSH、receiver 或仿真。

## 逐项核对

**1. 非零 lag 上界及对称性正确。** 在 `u=(v+k) mod N` 中，wrap 带来的因子为 `exp(−2πi l_i)=1`，这里明确使用整数 delay。c2 相位模为 1，故逐项三角不等式直接给出 `b_k=Σ_(i≠j)|S_ji||Z_ij[k]|`。i=j 是完整单位算子，k≠0 时必须排除。再用 `Z_ji[−k]=conj(Z_ij[k])` 和 `|S_ij|=|S_ji|` 交换 i/j 求和，得到 `b_−k=b_k`。它没有保证实际 edge 强度排序，更不保证 posterior/BER 收益排序；笔记没有超出这一边界。

**2. 有限候选和固定 partition 的成本边界正确。** 每个 directed lag 生成 N 条候选，端点规范化并去重后 Q≤LN；互逆 lags 可能生成重复 undirected edges，这只会降低实际 Q，不损坏上界。精确查询、排序和贪心都被计费，内存明确为 O(P²N+LN)。若 L 随 N 取到 N−1，费用仍可变为二次规模；本式不是任意 L 下的次二次复杂度保证。K_max 还自然受不相交约束限制为 floor(N/2)。从 singleton 的 q_u q_v 嵌入 pair 分布，且继续使用同一联合 prior（当前均匀先验使 p_B=p_u p_v）时，联合 q、entropy、prior 与目标都不变。后续拆散相关 pair 一般改变联合分布，固定 partition 正确避免了这一隐性重置。

**3. 数据目标和并行 proposal 正确。** block product 下，跨 block 的二阶矩为均值外积，内部仍保留 T_B，因此 `E[d*Gd]=m*(G−D)m+Σ_B tr(G_BB T_B)`。以 A=G−D 表示时没有假定 A 半正定。固定其他旧 blocks，Gibbs proposal 的外场正是 `r_B−(A m⁰)_B`，内部二次项不能丢。单个坐标的最优不能证明所有 q_B* 同时替换后上升，笔记对此限制准确。

**4. factorwise 算术 mixture 的二次能量式正确。** 概率线性混合使 m_B 和 raw T_B 线性变化，但跨 block 均值乘积是二次项。把 `m⁰+τΔm` 代入 Hermitian A 的二次型，系数恰为 `2 Re[Δm*(A m⁰−r)]+Σ_B tr(G_BBΔT_B)` 与 `Δm*AΔm`；两者均为实数，无 Taylor 余项。QPSK 固定模长只让 T_B 的 diagonal 差为零，不会让 pair raw cross moment 不变。整个 joint 的二元 mixture 一般引入跨 block covariance，不能套用同一 a₁/a₂ 分解。

完整目标差的 block entropy 必须按 q_B^τ 精确计算；非均匀 prior 贡献是线性的，当前 uniform prior 下才消失。协方差的等价表达还可写为 `C_B^τ=(1−τ)C_B⁰+τC_B*+τ(1−τ)Δm_BΔm_B*`，显示它不是两个 covariance 的简单线性平均，并在精确概率/矩一致时保持 PSD。

**5. 一次 GΔm 可服务全部回溯，限于同一 G。** 已有 Gm⁰ 后，D 的 1×1/2×2 block 作用仅需线性工作；a₂ 可由 `Δm*GΔm−Σ_B Δm_B*G_BBΔm_B` 得出。所有 τ 随后只需要有限状态 entropy、prior 和标量多项式，不需新 Gram 或 W/K。接受后的 Gm 线性更新也成立。一个必要的计费解释是：candidate pool 的非零 lag 查询并不自动给出 N 个 G_ii；proposal/D 所需 diagonal、首个 Gm⁰、Gp/匹配项必须在 owner 初始化时取得并记账，可复用既有 gram_diagonal 等接口，其成本仍被笔记总体上界覆盖。不能把“已有缓存”解释成免费构造。gain/ν/geometry 改变后，G/r 与这些缓存的身份失效；新 accepted SourceMoments 仍须使用同一 q_B^τ 的完整 covariance。

**6. Jeffreys 导数和有限 J 的限制正确。** 在严格正的有限 alphabet 上，所有求导都是有限和，可直接交换次序。对每个 block，Gibbs 的 log q_B* 等于当前外场加 log prior 再减归一化常数；用 `Σ_a Δq_B(a)=0` 消去该常数及 entropy 导数中的 1，得到 `Σ_a Δq_B log(q_B*/q_B⁰)`。这正是双向 KL 之和，没有遗漏 σ² 因子，因为能量尺度已包含在 log q_B* 中。至少一个 block 改变则导数严格为正，可推出存在充分小的正 τ，而不能推出预先固定的有限网格必定包含它。全部不变时 Δm、ΔT、entropy/prior 差和目标差均为零。保留显式拒绝结果并记录所有试步符合该命题；浮点下溢不能冒充严格正性。

## 退化/边界检查

- A=0 时 a₂=0，目标按 blocks 分解，所有 block 可同步到各自最优；这是严格符合假设的特例。
- singleton partition 使用同一 mixture、精确目标及步长策略，可作为相配的控制；不能拿不同优化日程的总差异归因于 pair correlation。
- G_uv=0 且 block prior 独立时，Gibbs 的两个符号分解，但旧 q_B 的相关性在中间 τ 未必立刻消失；筆记没有把存储格式等同于相关性收益。
- 仅非负而非严格正的 q_B⁰ 不满足有限 Jeffreys 导数证明的假设；后续软件必须独立定义该边界处理，不能对本证明作无条件外推。

本轮补齐的是有限候选池和固定 G 下精确回溯的代数依据；没有补出有限 J 的统一充分界、重配对不失真映射、实际最佳 pairing 或接收机收益。若继续落地，按本模型的固定 owner/partition 做实现与数值合同即可，无需因本审查另开实验或生命周期。
