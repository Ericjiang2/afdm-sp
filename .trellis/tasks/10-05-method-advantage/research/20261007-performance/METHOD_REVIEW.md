# Research: 实际联合捕获试验的数学、基线与统计门槛审查

- Query: 实现前核查模型到 FFT 四阶评分、连续整数 CFO、有限增益网格精确似然、优化二次码基线及计数/门槛。
- Scope: internal；独立静态数学与实验设计审查，无代码执行、模拟、SSH 或生命周期重载。
- Date: 2026-10-07
- Active task: `.trellis/tasks/10-05-method-advantage`
- CSV: `.mission/20261007-acquisition-performance/20261007-acquisition-performance.csv`
- Reviewed file: 本目录 `PROTOCOL.md`，2026-10-07 初始冻结协议。
- Method: 已读取并采用 `/Users/guoyikun/.codex/skills/experimental-design/SKILL.md` 的独立单位、配对、分层及分析匹配原则；没有生成新设计或安装依赖。

## Findings

### 当前判定：FIXES REQUIRED，核心评分与似然代数通过

需要在实现前补清三项定义及一项统计解释：SNR 到噪声方差、QPSK state mapping、返回 gain 的物理/有效相位约定、分层样本的非劣门槛。均为局部协议修订，不要求扩大实验、追加试验或改变研究目标。修订后本设计可以作为限定整数捕获模型的开发 pilot；本审查不授予远端执行权限，也不构成绩效或创新认证。

### 1. 模型 → FFT 四阶评分：PASS

N 为 32/64、s=5 满足 s∈Z 与 sN 偶数。循环恒等式给

`RᴴΠ_lR = exp(−πis l²/N) D_(sl) Π_l`。

令 a=ν+sl mod N、h_eff=h exp(−πis l²/N)。在整数 a 下，去 chirp 并 FFT 得

`X_tj = h_eff exp(2πiνLt/N) v_(j−a) exp(−2πil(j−a)/N) S_(t,j−a) + η'_tj`。

所有索引按模 N，unitary 变换保白噪声分布。L=5N/4 与整数 ν 给 frame factor=exp(2πi·5νt/4)∈C4。因此无需估计 ν 后 coherent alignment，独立 QPSK 产品 law 已吸收该因子；四次幂也直接将其消除。

对 κ=E S⁴，有

`E m_j = κ h_eff⁴ w_(j−a) exp(−8πil(j−a)/N)`。

乘 conjugate(w_(j−a)) 并匹配正号 exp(8πilj/N) 即是 `N ifft(q_a)[4l]`。被省略的公共相位不影响模长；FFT 规范须是 unitary F，而 ifft 使用标准带 1/N 的定义，协议中的 N 系数正确。直接求和合同比较应覆盖非零 a、非零 l 和循环 wrap。

### 2. 精确有限网格 likelihood：PASS，需补映射及 gain 定义

对于明确的 constellation `S=(±1±i)/sqrt(2)`，标量 Gaussian mixture 密度是

`(πσ²)^−1 exp[−(|z|²+ρ²)/σ²] cosh(√2ρ Re(z exp(−iφ))/σ²) cosh(√2ρ Im(z exp(−iφ))/σ²)`。

候选 z 只乘单位相位，所有候选的 Σ|z|² 相同，所以省略这一项和公共归一化常数正确。`logaddexp(u,−u)−log2` 是稳定且精确的 logcosh 表达式。

**F1 — 星座定义：** “rotated QPSK”不足以单独指定上述 cosh 公式。应固定四个整数 state 到 `(±1±i)/sqrt(2)` 的映射和数据顺序；若采用另一个旋转角，应在 demodulation 或似然中显式吸收。不要让生成器与 likelihood 各自猜测。

**F2 — 返回 gain：** 候选真值处的 z 含 h_eff，而非原模型的 h。SCREEN/FULL gain 网格估计的是 h_eff 的 C4 等价代表。若返回字段叫 physical h，应转换 `h_hat = h_eff_hat exp(+πis l_hat²/N)`，并说明其只在 C4 商意义下可辨识；不能宣称恢复真实唯一相位。FOURTH 返回 unavailable 已合理规定。主评分和 ν,l 错误率不受这一 gain 输出定义问题影响。

连续 h 用相同固定网格近似、phase 仅覆盖一个 C4 基本域是合法的。FULL 是同一 gain 网格、全部 θ 的最大值，故 FULL score≥SCREEN score 是确定性集合包含合同，并非统计优越性的假设。

### 3. SNR 与数据定义：需修订

**F3 — σ² 尚未由 SNRdB 定义。** 建议明确 nominal `σ²=10^(−SNRdB/10)`，并用 `sqrt(σ²/2)(ξ_R+iξ_I)` 生成复噪声。实际每符号条件接收 SNR 为 ρ²/σ²。这样 σ² 与隐藏随机 gain 独立，且三个 waveform arm 共用同一个物理噪声和 gain。

若反而按每组真实 ρ 令 σ²=ρ²/γ，又把 σ² 提供给 estimator，则已知 γ 和 σ² 会暴露 |h|；这改变了声明的未知增益实验。必须在实施前固定一个定义，不能将两种 SNR 混用。

CP=N/4 而最大 l=N/4−1，声明的循环单径有效块模型有足够 guard。此 pilot 不观察 guard，不检验 timing acquisition、fractional CFO、multipath 或 guard-based 基线，限定作用域正确。

### 4. 优化二次码与配对公平性：PASS，解释须精确

129 候选包括当前 c2 加 128 个预先给定值，没有 observation leakage。w 的 c2 周期为 1/4，给定候选在该周期内覆盖；有限 grid 优化不是全局优化，协议已经正确标注。

非零 k 的 d=0,…,N/4−1 对应所有 m=4d mod N；允许 delay 差的负值也通过此集合覆盖。k=0 的非平凡 delay pair 自动 A=0，不需要放入 max。该设计指标确实是当前整数商格点域的最坏 ambiguity，而非错误的 CFO-only slice。

随机码仅一次固定种子、不筛 seed；二次码允许预注册的 observation-independent 调参，偏向更强基线而非弱化它。所有三臂共享每组 l、ν、ρ、φ、symbol 与标准噪声，是合法 common-random-number 配对；独立统计单位是 256 组，不是 3072 帧或 147456 个复数观测。

最坏 ambiguity 是总体分布/四阶分离 surrogate，不能保证在本 N/T/SNR 下优化实际错误率。应称“按预注册 ambiguity 指标调优的 129 候选二次基线”，不得简化成性能最优二次码。若 package 的收益仅在 SCREEN 出现、FULL 无相应收益，应报告 screening 与 waveform 的相互作用，不把它单独归因为更高的完整 law 可分性。

### 5. 门槛与分层不确定性：需解释修订，接受集合可不变

**F4 — pooled Clopper–Pearson 不是本设计的一般精确置信区间。** 四个 cell 固定各 64 组，discordance 指示独立但成功概率可随 cell 变化；总数是 Poisson-binomial，一般不是 Binomial(256,p)。目标应明示为四 cell 等权平均的 `P(SCREEN wrong, FULL correct)`。

可以保留现有非劣 gate 的接受集合，但给出正确有限样本论证：在 n=256、阈值平均 p0=.02、单侧 .05 下，原 CP gate 恰为总坏方向 discordance `x≤1`。Binomial(256,.02) 的 Pr(X≤1) 约 .0353<.05，Pr(X≤2)>.05。对独立不等概率 Bernoulli，在该低尾范围也有保守性：Hoeffding 的等均值 binomial 尾比较适用于 x≤np0−1，这里 1<4.12。

这个特例还可直接证明而无需假定 iid：固定总均值 μ≥5.12，任取两个 Bernoulli 参数 p,q，令 R 为其余之和，则

`Pr(S≤1)=Pr(R=0)(1−pq)+Pr(R=1)(1−p−q+pq)`。

保持 p+q、把 p,q 平均化会增大 pq。剩余均值≥μ−2≥3.12，故 `Pr(R=1)≥Pr(R=0)`（非退化时其比值是 Σ r_i/(1−r_i)，边界取极限）。所以平均化不减该低尾概率，最大值在同均值 binomial 取得；其尾概率又随 μ 增大而减小。因此 x≤1 对“等权平均坏方向概率≥.02”的拒绝概率至多约 .0353。这支持原来的通过/失败门槛，但不支持把所有可能 x 的 pooled CP 数值统称为本分层模型的精确 95% upper bound。

建议保留 CP 数值作为 binomial reference，同时将正式 gate 写成上述平均风险的保守低尾检验；或事先指定对异质 Bernoulli 平均有效的置信上界。不要在看到数据后选择其中有利方案。

准确率改善的 D_cg=I(quad SCREEN wrong)−I(random SCREEN wrong) 是每组配对差。等权估计量为 `Δhat=(1/4)Σ_c mean_g D_cg`；与分层设计直接匹配的 normal SE 为 `sqrt[(1/16)Σ_c s_c²/64]`。建议把此公式写入协议，明确所报 normal CI 为 exploratory，而非无条件有限样本保证。不应把不同 cell 的均值差当作额外随机抽样噪声。

“每 cell 错误率≤.25”是观察到的 pilot gate，并非该 cell 真实错误概率≤.25 的置信认证。所有门槛须联合通过才有正开发信号，且不升级为生产/CONF，合理。任一失败后保留结果、做已注册的针对性后续而不是重选 seed，同样合理。

### 6. 计数与成本：PASS

- Design：130×[(31×8)+(63×16)]=163280 个选取的非平凡 ambiguity 值；96 次设计相位抽样正确。FFT 内部还计算其他频点，不能把这一输出 pair 数误报为浮点运算数。
- Observation：4 cell×64=256 独立 paired groups；×3 waveform=768 datasets；×4 frame=3072 N-vectors；加权长度为 147456 complex observations。
- Estimation：256×3 waveform×3 algorithm=2304 完整 paid calls。FULL 和 SCREEN 各自含 uncached dechirp/FFT/template，公平。
- 设计离线成本单列，接收机计时不含共同生成/磁盘但包含自身所有运算，process/startup/I/O另列，边界清楚。不得用缓存预处理的 SCREEN 对比重复预处理的 FULL。
- 执行顺序循环旋转可减弱同组顺序偏差；首次调用成本仍应如实保留，无需额外 warmup 数据。固定单线程、无同时计时任务满足这一开发比较所需的基本控制。

600s 和 2GiB 是硬 cap，不是已被本静态审查验证可满足的运行量。特别是 FULL 的 exact mixture 总计算较大；实际触及 cap 应按记录器失败处理，不隐含自动重试、缩小 grid、漏跑组或过滤慢样本的权限。

## External references and related specs

- 直接沿用此前 `research/20261006-continuous/JOINT_IDENTIFIABILITY.md`、`STATISTICAL_SEPARATION.md` 和对应审查的矩阵/完整 law 判据，本轮未重复重载。
- 使用已读取的 experimental-design 技能；关于具体 FFT、Gaussian mixture 和上述低尾保守性的核查为本报告直接推导，未新查外部文献。
- 主线程负责服务器规则、source admission 与不可变 recorder；本代理未读取或宣称验证未加载的服务器条款。只核查 PROTOCOL 中显示的科学与成本接口。

## Caveats / Not Found

- F1–F4 为实现前明确修订项，已向主线程发送；尚未核实其是否修改。
- 不存在当前协议下的性能数据、运行证据或创新认证。本轮只审查计划；旧理论完成不等于新目标完成。
- 仅在此宽整数 CFO、商代表 delay、循环单径 pilot 内评估表现/成本；不能外推 production、fractional CFO、multipath 或 BER。
- 本代理唯一写入文件为本 METHOD_REVIEW.md，保留其他代理和用户文件。

## Follow-up: 协议修复已核实

2026-10-07 源码准入时重新读取当前 PROTOCOL，确认 F1–F4 均已明确修订，前述未关闭状态不再适用：固定 QPSK mapping、nominal σ² 与隐藏 gain 独立、返回 physical gain modulo C4、非劣门槛改为异质 Bernoulli 平均风险的 x≤1 保守检验；paired interval SE 也明确为 cell 内方差公式。

因此本报告的**方法与实验计划判定更新为 PASS（限定开发 pilot）**。源码执行准入独立记录在同目录 SOURCE_ADMISSION.md，其中异常中途计数/保存及未完 audit 尚有待关闭项；方法通过不等于已允许运行或取得性能证据。
