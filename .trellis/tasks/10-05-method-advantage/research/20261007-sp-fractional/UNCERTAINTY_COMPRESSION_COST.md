# Research: 连续不确定性压缩的真实成本与两项精确复用机制

- Query: 少量正权矩节点在当前 AFDM + SP + 连续 fractional receiver 中究竟减少什么；哪些精确复用或块结构能降低完整成本，同时保持模型与数据步单调性；给出最值得测试的机制及可证伪实验。
- Scope: internal；指定源码静态审读与解析等价性推导。
- Date: 2026-10-07
- Active task: `.trellis/tasks/10-05-method-advantage`
- CSV / row: `.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv` / `QUAD-DIAG-01`
- Ownership: 仅本文件；未修改源码或其他研究文档，未数值计算、仿真、SSH 或 Git。
- Handoff: 当前 CSV 12 行，SSH-DEV 已经原始独立审计关闭，QUAD-DIAG 进行中；本轮不重新加载生命周期。

## Findings

### 结论与优先级

**小节点压缩不是当前数据算子的普遍加速器。** 源码已在 `PathMoments` 构造时将每条路径的分布折叠成长度 N 的 φ；后续 Gram、增益统计、Doppler 系数和目标函数不再遍历积分节点。压缩能降低分布构造/导出、重复 φ 重建和缓存容量，但不能把这些已经折叠的 `O(P²N)` 路径对运算再按节点数缩短。

最值得先测试两项无需近似、无需修改 KL-MM 验收的机制：

1. **按真实依赖复用已验证 φ、固定几何及未变数据源统计。** 直接消除 20 sweeps 中 80 次 `PathMoments` 构造所引起的重复相位折叠，并复用增益更新与 Doppler sweep 之间相同的数据源统计。已有缓存不会被重复包装成贡献。
2. **固定数据块内预聚合 Gram 的加权循环移位系数。** 将每个候选步重算的路径对乘积移到 `DataStepper` 构造时，按相同 delay difference 合并；每次 matvec 保留原来的两个 DAFT，独立目标函数和 equation (8) 检查也保留。

主会话交接的 point 20-sweep 中位耗时为 1.6287 s，f1scalar 为 0.5864 s，约 2.78 倍；本轮未独立重算这些时间。point 已经每条路径一个节点，因而其额外成本不能靠“再压缩节点”解决。continuous 在第一个坐标积分失败，没有完成同等工作，失败时间不参与速度优势比较。两项机制是否足以弥补 2.78 倍差距，当前没有证据。

### 文件、代码模式与任务约束

路径相对项目根。本轮完整读取以下三份源码；`moments.py` 的实际位置由 `receiver.py` 的 import 确认，不在 receiver 子目录内。

| 文件 | 相关事实与行号 |
|---|---|
| `experiments/afdm_sp_fractional_receiver_20261007/receiver.py:61` | `MomentFactory.build` 每次矩形化 nodes/weights、重新构造 `PathMoments`，记录相位条目。 |
| `experiments/afdm_sp_fractional_receiver_20261007/receiver.py:118` | 已有整组坐标系数初始化和随后仅更新未来坐标的 delta-φ 机制。 |
| `experiments/afdm_sp_fractional_receiver_20261007/receiver.py:168` | 每 sweep 四次 `factory.build`，按 gain → sequential Doppler → gain → 三个 data steps 排列；固定执行 20 sweeps。 |
| `experiments/afdm_sp_fractional_receiver_20261007/data_step.py:52` | 已在每个固定 data block 缓存 Gram diagonal、matched、safe bound 和 `G(pilot+mean)`。 |
| `experiments/afdm_sp_fractional_receiver_20261007/data_step.py:116` | 每个回溯 proposal 计算一次 Gram matvec，另算一次独立 expected quadratic；所有 proposal 都核查 equation (8)。 |
| `experiments/afdm_sp_fractional_receiver_20261007/data_step.py:158` | 接受后已用 `gx += G delta` 更新缓存，未再次完整计算 Gx。 |
| `experiments/afdm_sp_fractional_20261007/moments.py:67` | 构造函数复制/验证增益 covariance，建立静态 CPP/indices，并由完整节点重新计算 φ。 |
| `experiments/afdm_sp_fractional_20261007/moments.py:116` | source 只依赖几何、pilot、data mean/variance；其 owner 当前绑定具体 `PathMoments` 实例。 |
| `experiments/afdm_sp_fractional_20261007/moments.py:133` | `_cross_source` 每次重算几何相位和源交叉二阶矩；没有相应缓存。 |
| `experiments/afdm_sp_fractional_20261007/moments.py:177` | Gram 每次 matvec 重算 CPP/φ/second 的路径对系数与移位。 |
| `.trellis/tasks/10-05-method-advantage/research/20261007-sp-fractional/QUADRATURE_CONCENTRATION.md` | 已验证的正权压缩界、连续积分/离散 tail 区别、算子误差和完整成本边界；本轮复读第 5–6 节及限制。 |

Related specs / task-local contracts：当前因子化、同路径二次项、完整 gain covariance、原先固定三个数据步/20 sweeps、显式失败、无 probability floor、不删困难观测、每 proposal 的 equation (8) 与单调性检查均按现源码保留。这里的精确化简不授权修改这些科学或运行契约；未读其他 spec 文件，不声称已加载。

### 1. 真实依赖图：节点已经被折叠一次

令 `A` 为单位ary DAFT，`T_i=C_i P_{l_i}` 为带精确 CPP 的循环延迟，`D(ν)=diag(exp(it_nν))`。路径算子为 `H_i(ν)=A D(ν)T_i A*`，平均路径算子为

\[
\bar H_i=A\,\operatorname{diag}(\phi_i)T_i A^*,\quad
\phi_{i,n}=E[e^{it_n\nu_i}],\quad \|\bar H_i\|_2\le1.
\]

记 gain mean 为 μ，`S=Cov(h)+μμ*`，则独立路径 Doppler 的二次平均为

\[
\bar H=\sum_i\mu_i\bar H_i,\qquad
G=E[H^*H]=\underbrace{\sum_iS_{ii}I}_{\text{同路径项精确抵消 Doppler}}
+\sum_{i\ne j}S_{ji}\bar H_i^*\bar H_j.
\]

`moments.py:140–210` 的所有调用均只使用 φ、S/μ、固定几何和源统计，不访问 nodes/weights。后者除了构造/留存外没有参与这些算子。因此当前实现已经采用了上述分布到观测矩的降维；不能再次把“避免为每个积分节点执行 DAFT”当作本轮新优化。

#### 成本拆分

记 P 为路径数，K 为积分端累计节点/探测数，L 为矩形化后的单路径节点数（最大 retained count），B 为完整运行中实际 proposal 总数。

| 工作 | 当前主要尺度 | 小 k 正权压缩能否减少 |
|---|---|---|
| 每次 Fourier 密度评估/积分前端 | 直接实现 `O(KN)`，另有 tail/logZ/误差诊断 | 不能消除定位质量与 logZ 成本；少量输出矩不使 f 评估脱离 N。 |
| `PathMoments` 内重算 φ | 每次 `O(PLN)`；广播临时数组也达此尺度 | 可以降成 `O(PkN)`，但复用已有可信 φ 可直接避免本次重建。 |
| 矩形化与导出 nodes/weights | `O(PL)` 加完整记录 | 可减少；实际 trace 若仍保留完整前端证据，则该证据成本仍应计入。 |
| gain statistics / coordinate coefficients | `O(P²N)`，另有变换 | 已经不依赖 L；节点压缩不会再降低其路径对数量。 |
| gain solve / covariance 验证 | `O(P³)`，P≤8 | 不因节点数下降；不允许把 full covariance 换成 diagonal。 |
| data proposal 的 Gδ | 两个 N 点 DAFT + `O(P²N)` | 无 L 因子；可由下述精确预聚合减少重复系数工作。 |
| 独立 expected quadratic | 源准备、y 变换、`O(P²N)` | 无 L 因子；不因正权压缩而自动减掉。 |
| QPSK softmax/KL/entropy、LLR、观测/F1、序列化 | 各自原成本 | 不因节点压缩消失。 |

低 k 也不意味着 G 低秩：单路径时任意 Doppler 分布都给 `G=S_11 I`，只要 `S_11>0` 就是 N 阶满秩。多个路径且 gain covariance 非对角时，也不能把 full S 擅自降秩或对角化来制造成本收益。

### 2. 机制一：复用真正未变的矩与数据源

#### 2.1 可由源码证明的等价性

将现对象所携数据按依赖拆开，而不是按每次调用重新计算：

- 固定几何 `N,c1,c2,delays,indices,CPP,time`：在整次 receiver call 不变。
- Doppler factors 与 φ：只有 sequential Doppler 坐标更新时变化；gain/data 更新不改变 φ。factor 已含计算完成的 φ，`doppler_sweep` 直接读取它进行 delta 更新（`receiver.py:133`）。
- gain 状态 μ、Cov、S：只在 gain update 后变化；它不影响 φ 和 source。
- source：仅依赖固定几何、pilot、当前 log_q 所导出的 mean/variance，不依赖 φ、μ、Cov。变换后的固定观测 `A*y` 在整次调用不变。

据 `receiver.py:172,175,178,181`，每 sweep 四次构造分别仅对应旧/新两组 Doppler 因子和旧/新 gain 状态。相同因子被多次从 nodes 重折叠；相邻 sweeps 的最后/最初因子也相同。完整 20 sweeps 为 80 次构造，但每个新 factor 的 φ 在 optimizer 返回时已经存在。直接复用这个唯一可信计算结果比先引入额外近似压缩再重算 φ 更简单。

另外，同一 sweep 的 gain-before、Doppler、gain-after 和 data-block 初始 objective 使用同一个 log_q，故 `prepare_source` 的数组在这四处相同。`_cross_source` 所得

\[
R_{ij}[n]=r_i[n]r_j[n]^*+\widehat v[(l_i-l_j)\bmod N]\,
e^{2\pi i c_1(2n(l_i-l_j)-l_i^2+l_j^2)}
\]

也相同，不应因 gain 或 φ 改变而失效。缓存固定几何相位在整次 receiver call 有效；缓存 R 仅在同一 source/version 内有效。还可利用 `R_ji=conj(R_ij)` 和 gain Gram Hermitian 性只构建一半路径对，保留原 Hermitian/PSD 审核。这些是精确实数/复数代数等价性，浮点求和顺序可能有细小差异。

#### 2.2 必须保留的失效条件与对象边界

当前 `SourceMoments.owner is self` 是有效防错约束（`moments.py:130`）。不能直接删 guard 后跨对象混用 source。可行设计需使固定几何拥有单一、明确的 identity，并使 source 绑定该几何 identity 和数据版本；或者由受控构造过程复用不可变数组并建立正确的新 owner 包装。二者选一个一致设计，不能新增绕过验证的旁路。

φ 应与生成它的已验证因子绑定，不接受任意外部数组仅凭 `φ_0=1,|φ|≤1` 冒充合法分布矩；这两个逐元条件并不足以保证正定特征函数。矩形化重复同一点并分摊权重在精确算术中不改 φ，故重算不是必要的科学步骤，但移除重算前应对原路径做等价核验。

缓存键不能只用 shape、sweep 编号或浮点“变化很小”：log_q、pilot、几何或 factor 发生有效变化必须失效。R 不随 gain/φ 改变，但 Gram 系数随 S/φ 改变；混淆这两种缓存会造成 stale-operator 错误。不可把前后两次 gain update 合并：它们之间 Doppler 已更新，增益统计通常不同。

#### 2.3 已有工作不重复宣称

- 积分端 phase table 缓存已在已有浓度笔记/交接中确认；这里针对的是 `PathMoments` 在另一处重建，并非再发明同一缓存。
- sequential delta-φ 系数更新已存在；只讨论其中重复的 R/固定相位，不能宣称本轮首次避免每坐标重算全组系数。
- data diagonal、matched、Gx 和接受后的 Gδ 增量也已缓存；本机制不把这些作为新增收益。

### 3. 机制二：固定数据块的加权循环移位 Gram

#### 3.1 精确重写

在一个 `DataStepper` 的三次 step 及其回溯中，φ 和 S 不变。令 `u=A*x`，`τ=tr(S)`。对一对 `i≠j`，设 `Δ=l_j−l_i (mod N)`、`m=(n+l_i) mod N`。由 `moments.py:184–186` 逐项换下标得到

\[
w_{ij}[n]=S_{ji}\,CPP_i[m]^*CPP_j[m]\,\phi_i[m]^*\phi_j[m],
\qquad
(G_tu)[n]=\tau u[n]+\sum_{i\ne j}w_{ij}[n]u[(n-\Delta)\bmod N],
\]

其中 `G=A G_t A*`。按相同 Δ 合并

\[
W_\Delta[n]=\sum_{i\ne j:\ l_j-l_i\equiv\Delta}w_{ij}[n],\qquad
G_t=\tau I+\sum_{\Delta\in\mathcal D}\operatorname{diag}(W_\Delta)P_\Delta.
\]

`P_Δu[n]=u[(n−Δ) mod N]`。不同路径可有相同 delay，故 Δ=0 的交叉项也必须保留，不能并入“同一路径”后删除。Hermitian 结构要求

\[
W_{-\Delta}[n]=W_\Delta[(n+\Delta)\bmod N]^*.
\]

这既可作为构建时的核验，也明确了 CPP wrap 后正确的共轭/移位位置。不能仅取未移位系数的共轭。

#### 3.2 成本与收益条件

在每个固定 data block 首次需要 Gram 时构建 W，花费 `O(P²N)`，内存 `O(DN)`，`D=|𝒟|≤min(N,P(P−1))`。之后每个 Gδ 用两个 DAFT 和 `O(DN)` 的一次系数乘法/移位；不再在每个 proposal 里重做 CPP、φ、S 的逐对乘积。data block 至少有初始 Gx 和三个 proposal，即至少四次 matvec，回溯越多越能摊薄一次性构建成本。

即使所有非零 delay differences 不同，D 仍约 P²，渐近阶数不变，但固定系数乘积从每次 matvec 移到了 block 构建。若许多路径共享差值，D 会更小，才有路径对聚合带来的额外阶数/常数收益。W 的分配、聚合、内存流量和计数都必须计费；P 很小或 matvec 很少时，预构建可能无收益。

**W 通常不是常数。** CPP 和 fractional φ 使 `W_Δ[n]` 随 n 变化，因此 G_t 是加权移位和，不普遍是 circulant，不能拿一次 FFT 对角化后逐频标量除法替代当前算子。也不能因 ν 分布只需两个节点，就假设这些 n 依赖消失。

一个严格特例是 P=1：交叉项为空，`G=τI`，可直接缩放，两个 DAFT 都不需要。一般 P>1 不满足此条件。该特例是等价边界测试，不是本次 P≤8 观测中已发现的性能机制。

#### 3.3 保持现有数据步验收

此重写只改变 `gram_matvec` 的相同算子实现。保留 `expected_quadratic` 的独立路径和所有 proposal 的 curvature、equation (8)、monotonicity、increment-bound 检查；因此模型、提议公式、安全上界和接受规则均不变。

从数学上，固定数据块的 objective 也可写成

\[
Q(q)=\|y\|^2-2\Re[b^*x]+x^*Gx+d^Tv,
\quad x=pilot+m,\ b=\bar H^*y,\ d=\operatorname{diag}(G).
\]

利用已经算出的 Gδ 可更便宜地得到候选 objective，但**本轮不将其选为推荐机制**：若 equation (8) 和 objective 都共享同一 Gδ/缓存，当前用独立 expected quadratic 抓 stale Gram 的检查可能退化为同源自洽。单纯以 equation (8) RHS 更新 objective 会直接消灭独立核验。要减少此成本，需先单独设计保留独立证据的检查契约，不能把更改审计强度混入精确运算优化。

### 4. 压缩误差、近似算子和早停：哪些保证仍然成立

设每条路径的压缩满足 `||φ_i−φhat_i||_∞≤ε_i`，两侧均来自合法正概率分布，因此平均路径算子范数不超过 1。固定 μ、S 时，直接由上面的精确展开有

\[
\|\bar H-\widehat{\bar H}\|_2\le h_\epsilon:=\sum_i|\mu_i|\epsilon_i,
\quad
\|G-\widehat G\|_2\le g_\epsilon:=\sum_{i\ne j}|S_{ji}|(\epsilon_i+\epsilon_j).
\]

同路径项保持精确，不应多算或近似掉。统一 ε 时 `g_ε≤2εΣ_{i≠j}|S_ji|`，表明影响还取决于 gain 二阶交叉权重，并不只由 k 或 ε 决定。进一步有

\[
\|d-\widehat d\|_\infty\le g_\epsilon,\qquad
\|(G-\operatorname{diag}d)-(\widehat G-\operatorname{diag}\widehat d)\|_2\le2g_\epsilon.
\]

对固定候选 mean 增量 δm，curvature 的误差不超过 `2g_ε||δm||²/σ²`。对任意 q，熵精确而二次项近似时，objective 误差不超过

\[
E_F(q)=\frac{2\|y\|\|x\|h_\epsilon+g_\epsilon(\|x\|^2+\sum_n v_n)}{\sigma^2}.
\]

因此即使压缩保持正权/PSD，对近似 objective 的单调性也不自动等于原连续 objective 的单调性。若要保留原目标的单调性，至少需要 `Fhat(q')−Fhat(q)≥E_F(q')+E_F(q)` 等有余量的认证，或对候选继续运行原目标的可靠积分/算子核验。若提议 logits 也来自近似算子，原 equation (8) 对精确目标不再原样成立，不能只给 curvature 加一个误差项就声称完整原证书恢复。本轮不改变接受规则。

#### 早停的边界

- **精确固定点可停**：固定 data operator 下，若 `log_q == log_jacobi` 在数学上完全相同，则所有后续几何 proposal 不变；剩余 data steps 可用恒等性证明冗余。浮点算出的 KL=0 可能来自 underflow/舍入，不能仅凭它当作分布完全相等。
- **小 fixed-point KL 不是 20 sweeps 的误差证书**：当前日志有该指标，但单调性只保证接受序列的 objective 不下降，不提供全局收缩性、全局最优性或 outer gain/Doppler 的误差界。固定三步/20 sweeps 是现有合同，阈值早停会改变算法路径，需独立科学批准和等效性证据。
- **均值近似不控制 LLR**：Pinsker 可给 `||m(q')−m(q)||²≤2 DATA_POWER·KL(q'||q)`（反向 KL 也分别成立），但很小的稀有符号质量仍可对应很大的对数比变化。不能用小均值差直接保证 working bit LLR 或错误率不变。
- **回溯提前拒绝不等于可删检查**：curvature 不通过时可数学上知道该候选不接受，但当前代码刻意要求每个 proposal 的 equation (8) 都成立，防止缩步掩盖 stale cache。跳过 rejected proposal 的独立 objective 会改变这条检查契约，本轮不推荐。

所以本轮的两个首选机制都是精确复用；误差控制压缩应先解决可靠积分与误差账本，不把早停作为未经证明的速度来源。

### 5. 最小可证伪实验设计（仅提案，未执行）

#### 机制一：可信 φ/源统计复用

1. 使用小尺寸确定性 fixtures，对包含 CPP wrap、相同 delay/不同 Doppler、非均匀 AF variance 和非对角 gain covariance 的配置，比较旧/新 φ、R、gain Gram/matched、全部坐标系数和 expected quadratic。fixtures 只检验等价性，不作为真实 receiver 性能证据。
2. 专门构造失效边界：只改 gains 时 source/R 必须保持但 S 必须更新；只改 φ 时 source/R 保持而算子改变；只改 log_q 时 source/R 必须失效；改几何或 pilot 必须失效。错 owner、错版本应显式报错。若旧/新不一致或 stale 状态未被拒绝，机制被证伪。
3. 对一份已有 observed-only 开发观测回放完整 point 20 sweeps，先比较每次 gain、Doppler、data proposal 的值、接受层、方程残差与最终输出，再测完整时间。不得只计省下的 constructor 时间。phase 重算、source FFT/DAFT、R 构建、缓存字节与序列化分别计数。

#### 机制二：固定块 Gram 预聚合

1. 同一小尺寸 fixture 下，对复基向量逐列比较旧 Gram 与加权移位实现；覆盖 Δ=0、Δ 与 −Δ、边界 wrap、重复差值，以及 full gain covariance。检查 Hermitian 条件、Gram diagonal 和非负二次型。P=1 应退化为精确 τI；这能抓移位符号/CPP 错位。
2. 固定一个已有 point data block，回放至少实际三个数据步的全部 proposal；独立 expected quadratic 保持旧实现，核对 equation (8)、curvature 和接受层。新增 W 建立成本与内存全部计入；若验收路径显著变化、identity 失败或总 block 时间未降，则相应正确性/速度主张被证伪。
3. 将上述两项各自启用及共同启用，与同一 baseline 完整 receiver 对照，区分独立收益和重叠收益。只有 continuous 能完成相同 sweeps 后才作完整性能–成本比较；现有积分失败的 case 仅用于失败诊断成本记录。

最小因果指标：constructor 的相位折叠次数是否消失、相同 source 的变换次数是否下降、Gram 固定系数是否每 block 仅构建一次、每个 proposal 是否仍得到同一实际验收、完整 runtime/峰值内存是否改善。若算子原本不是主耗时，即使这些计数下降，也不能宣称端到端优势。

完整成本至少包括已有 harness 所计 F1、输入/初始化、预计算与缓存、gain/Doppler/data 全部迭代与回溯、积分及失败、检查、trace/序列化和输出。不得将优化后的子模块秒数与 f1scalar 端到端秒数直接相比；具体共同项归属沿用原审计口径，不在本轮另造口径。

补充已保存 trace 证据：主会话从 8 份 point raw 的 JSON metadata 读取并导出至 `control-quadrature/saved-point-cost-metadata.json`；每例 backend 为 0.945–0.994 s，F1 为 0.3757–0.3970 s，有 80 次 PathMoments 构建、154–167 次 source prepare、60 个接受的数据步和 74–87 个 proposals，即 14–27 次拒绝，最高接受 level 为 1。大幅回溯并非这 8 例的主要现象，不能把成本优化收益押在大 β 的深度 backtracking 上。这些均是原运行 trace，没有新增计时或剖析，不能据此分解各模块耗时；本作者未重新计算 raw。

## External references

- 本轮未新增外部检索。正权 Gauss 压缩与 Taylor/尾误差前提沿用 `QUADRATURE_CONCENTRATION.md` 及其已核查的 NIST DLMF 引用；本文新增依赖图、加权移位等价式和 fixed-S 算子扰动界均由所列源码与代数直接推导。
- 经典 Gaussian quadrature 或 OFDM 类移位算子的适配可作为工程方法保留，不声称首次。是否有研究价值仍取决于完整 AFDM/CPP 条件下的可验证精度与端到端成本结果。

## Caveats / Not Found

- 未读取其他 raw、服务器或 timing 明细，没有新 profiling 或数值结果；1.6287 s / 0.5864 s 及运行状态来自主会话交接。
- 尚未证明 constructor、source 或 Gram 路径对占据主要 wall time，故两项机制只是具有明确等价依据的优先测试对象。
- 本轮未修改现有 20 sweeps、三数据步、full covariance、积分上限、独立 objective 或失败处理；没有将近似压缩/早停伪装成精确重用。
- 误差界在固定 μ、S 及可靠 φ 误差前提下成立；外层反复更新、病态求逆、提议改变和有限精度认证需要额外稳定性分析，不能从本笔记推出 BER/BLER 或整个 receiver 优势。
