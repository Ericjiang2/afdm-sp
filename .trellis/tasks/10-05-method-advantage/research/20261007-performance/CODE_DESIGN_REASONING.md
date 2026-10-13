# Research: N64 受限 Weyl 码设计的下界、目标与完整分布连接

- Query: 第三轮显示 FULL 本身错误率仍较高后，观测无关的一般相位码优化是否有数学依据；如何选择 minimax/高阶势，而不为过门任意调参。
- Scope: internal，纯解析推导与后续方案说明；无新仿真、数值码设计、seed search、SSH 或源码修改。
- Date: 2026-10-07
- Active task: `.trellis/tasks/10-05-method-advantage`
- Read: `JOINT_IDENTIFIABILITY.md` 的 A 判据、`COMPOSITE_LATTICE_ESTIMATION.md` 的标量 moment–Hellinger 界，以及旧 `outputs_acquisition_performance_20261007/execution/D/design.json` 已保存 objective。沿用 BAYES_SYMMETRY 的均匀格点与共同 gain 作用域。

## Findings

### 结论

**一般相位码优化是有针对性的下一假设，但不保证严格改善旧随机码，更不保证有限 N 的错误率过门。** 可以把它定义为固定 N64 上、完全不看新观测的 classical waveform optimization；其目标直接对应当前 QPSK 完整 law 的定量分离，且接收机和在线每符号相位乘法不需要改变。

重要的反例是：**只最小化平方歧义的总能量不够。** 在本问题中，二次 CAZAC 码可以把该能量降至全局下界，却留下15个幅度为1的歧义旁瓣，即精确完整 law 歧义。因此应使用 minimax 或 p>1 的高阶旁瓣势，不能把一个容易下降的总能量指标当作可靠码设计。

下文给出 N64 的确定性下界 `μ≥1/√67`。旧保存随机码 `μ=.32532365361130605` 距该下界有空间，但下界未证明可达；它不是已经找到更好码的证据。

## 1. 精确设计对象与旧证据

固定 `N=64, M=16`，`w_j=v_j⁴` 且 `|w_j|=1`，定义

`A(k,4d)=N⁻¹ Σ_j w_(j−k) conjugate(w_j) exp(−2πi·4dj/N)`。

当前去除 universal delay symmetry 后的完整 hypothesis set 是 `Z_64×Z_16`。其相对差为 k mod64、d mod16。k=0,d≠0 的 A 恒为0，所以唯一需要优化的非平凡集合为

`Ω={(k,d):1≤k≤63,0≤d≤15}`，`|Ω|=1008`，`μ(w)=max_Ω|A(k,4d)|`。

该集合覆盖实际的正/负 delay 差。不能只优化 CFO 切片 d=0，也不能把不在当前 m=4d 子格上的 coefficients 混作同等设计目标。均匀先验下每个相对差在每个真 hypothesis 的邻域都出现；一个坏相对差并不是只影响少数罕见真参数。

已保存 D 结果（仅读取，没有重算/搜索）：

| N64 code | 已存 μ |
| --- | ---: |
| current small-c2 | .971907482990321 |
| 129候选中调优 quadratic | .7961593041701783 |
| 原固定随机码 | .32532365361130605 |

原 code 文件 SHA 为 `9d3a2d5532780b3fc884cc7d97fb7001107f9a94b64d0e9513f9eb2f2ffa0e03`。这些数值只表示旧设计 surrogate，不是新的性能结果。

有限维相位 torus 紧、μ 连续，故全局最优值 μ* 存在；旧随机码是一个可行点，严格可说 `μ*≤.32532365361130605`。没有证明不等号严格，也没有声称某个局部优化器能达到 μ*。

## 2. 受限歧义的精确能量恒等式

令 `R_t=A(16t,0)`，t=0,1,2,3，R0=1，并令

`Q=|R1|²+|R2|²+|R3|²≥0`。

有限字符正交性给

`Σ_(d=0)^15 exp[−2πid(j−l)/16] =16·1_(j≡l mod16)`。

在 `Σ_(k=0)^63 Σ_(d=0)^15 |A(k,4d)|²` 中展开双和，再用上述恒等式，只剩 `l=j+16t`。对 k、j 的两次循环和互为共轭，得到精确关系

`Σ_(k=0)^63 Σ_(d=0)^15 |A(k,4d)|² =16 Σ_(t=0)^3 |A(16t,0)|² =16(1+Q)`。

去掉 k=0 的唯一非零 origin 后，

`J1:=Σ_Ω|A|²=15+16Q`。

再把 Ω 中三个特殊点 `(16,0),(32,0),(48,0)` 单独移出，余下1005项满足

`Σ_(Ω\{三特殊点}) |A|² =15(1+Q)`。

因此

`μ²≥(1+Q)/67≥1/67`，亦有 `μ²≥Q/3`。

这是无需任何数值搜索的确定性 coherence 下界。它利用了 k=0 的结构性零，比不区分这些零的普通 frame average 更精确。**未证明存在 unit-modulus w 同时达到该下界。** 达等号至少要求 Q=0，且其余1005项的平方模全部为1/67；这些条件可能受额外代数约束。

同一计算对一般 `N=gM, g=gcd(N,4), M>1` 给 `μ≥1/√(N+g−1)`；本研究实际只使用 N64 的实例，不据此声称所有长度均有可达构造。

## 3. 结构启发：平衡四个频率余数类，但不能只追求 tightness

用 unitary FFT 定义 `ŵ=Fw`，则 `||ŵ||²=N`，循环自相关为

`A(k,0)=N⁻¹ Σ_f |ŵ_f|² exp(−2πifk/N)`。

所以 Q=0 等价于四个 residue classes `f mod4` 的 code-spectrum 能量各为16。这里是 **w 的数学谱**，不是实际 iid payload 发射信号的 RF PSD、PAPR 或物理带外能量。

这解释了为什么 `A(16,0),A(32,0),A(48,0)` 是有用的结构诊断：它们偏大必然抬高受限旁瓣总能量及可达 μ 的下界。可以把这种平衡作为诊断或软约束；不能仅凭该下界就断言真正 minimax 码必须严格 Q=0，或把它强加为未经证明的最优性条件。

**反例：二次 CAZAC 的 J1 全局最优而识别最差。** 取奇 q、

`w_j=exp(−πiqj²/64)`。

它满足 `|A(k,4d)|=1_(qk=4d mod64)`。在 Ω 中恰有15个非零点（k 为4的非零倍数），每个幅度1；其他项为0。因此 Q=0、J1=15 达下界，但 μ=1，存在精确联合 law 歧义。这是本问题中使用纯 integrated sidelobe energy 的直接反证。

另一个必须避开的捷径是直接把 prime-Alltop 公式换成64：

`w_j=exp(2πij³/64)` 时，`(j−32)³−j³≡32j (mod64)`，从而 `A(32,32)=1`。

这里 m32=4d 对应 d8，正在允许集合内；物理参数差可取 Δν=32−5·8≡56 mod64。这一 composite cubic 不是本 N64 的救济构造。一般相位优化应保持完整 Ω，而不是仅换一个低阶多项式。

## 4. 适合的设计目标与可验证梯度

### Minimax 与高阶势

最直接目标是 `min_(|w|=1) μ(w)`。平滑候选可用

`J_p(w)=Σ_Ω |A(k,4d)|^(2p)`，p>1。

其与 μ 的关系为

`μ²≤J_p^(1/p)≤1008^(1/p) μ²`。

由第2节以及 power-mean inequality，有

`J_p ≥ 15(1+Q)^p/67^(p−1) + Q^p/3^(p−1) ≥ 15/67^(p−1)`。

二次 CAZAC 对所有 p 都有 J_p=15，而一个分散旁瓣的码会明显减小高阶势；p>1 正是在处罚少量危险大峰，不是仅降低平均能量。另一方面，降低 J_p **并不逻辑保证** μ 下降。若主目标是 worst-pair 分离，最终 code selection 应事前规定按实际 μ 选择，不能事后拿下降的 surrogate 掩盖变差的最大旁瓣。

也可使用 log-sum-exp of squared sidelobes：

`F_τ=(1/τ)log Σ_Ω exp(τ|A|²)`，`μ²≤F_τ≤μ²+log(1008)/τ`。

这给 τ 一个可解释的近似精度含义。以上均为经典平滑 minimax 方法，不是新算法首创。

### Phase-only 参数化

写 `w_r=exp(iφ_r)` 可始终严格满足单位模；公共相位可固定 φ0=0 消除无关自由度。令

`t_j(k,d)=w_(j−k)conjugate(w_j)exp(−2πi·4dj/N)`。

则

`∂A(k,4d)/∂φ_r=(i/N)[t_(r+k)(k,d)−t_r(k,d)]`，

`∂J_p/∂φ_r=2p Σ_Ω |A|^(2p−2) Re[conjugate(A)·∂A/∂φ_r]`。

所有索引循环，m 为整数保证 wrap 相位一致。这些解析梯度可作未来实现的确定性合同；本轮没有计算梯度或运行一次优化。最终 v 仍使用固定的逐坐标 principal fourth root，避免把不同 QPSK-equivalent root 的 paired-data 行为当成额外调参自由度。

## 5. 与当前接收机及完整概率 law 的连接

### 条件四阶模板：均值间隔变大，单模板噪声方差不变

在正确整数模型、固定 h 下，设一个候选的未取模 fourth matched sum 为 Z_θ。真候选的均值模为 `Nρ⁴`，相对差 (k,d) 的错误候选均值模为 `Nρ⁴|A(k,4d)|`。

每个坐标的四阶均值噪声方差是 V/T，其中

`V=16ρ⁶σ²+72ρ⁴σ⁴+96ρ²σ⁶+24σ⁸`。

由于整数变换下坐标噪声/符号独立、匹配权重为单位模，任一候选线性和的复方差都是 `NV/T`，与具体 code 无关。因此降低 μ 会增加最小的**复统计均值模间隔** `Nρ⁴(1−μ)`，其与单模板标准差的比为

`sqrt(NT)ρ⁴(1−μ)/sqrt(V)`。

这不是 E|Z_true|−E|Z_wrong| 的精确表达，更不是同时比较1024个相关、重尾候选后的错误率。候选间噪声相关性也依赖 code，不能只看正确峰。

### 完整 law：有严格 witness 和 affinity 上界

在等 gain 幅度的整数格点上，完整 holomorphic (4,0) tensor 的未知公共相位最小距离为

`D4²=2Nρ⁸(1−|A(k,4d)|)`。

故 minimax μ 确实最大化这个完整张量块的 worst-pair phase-quotient separation。与仅在 d=0 优化相比，这对应正确的联合 law 不变量。

此前显式 moment–Hellinger 推导还给 annulus 内任意两个 gain 幅度/相位的条件 frame affinity 上界

`Aff(P_(θ,h0),P_(θ',h1)) ≤ exp[−c0 N(1−|A(k,4d)|)]`，

`c0=ρmin⁸/(4M8)`，M8 是固定 gain/noise 上界下的八阶矩。T 个条件独立帧使指数乘 T。这说明目标不是凭经验与错误率相关的任意“好看指标”，而是改善一个严格完整分布分离界；有限 N 下 c0 可能非常保守。

对于均匀格点、多候选 union bound，比只看 μ 更贴近困难邻居数量的几何势是

`Ψ_κ(w)=Σ_Ω exp[−κ(1−|A|)]`，κ=T c0 N；

k=0 的15个错误 delay 只额外贡献 code-independent 的15exp(−κ)。此前有限 gain-net estimator 的 error bound 中，code-dependent 的 union 项可由这类和控制，高阶 J_p 则是更简便的尖峰抑制 surrogate。这个联系需要同时保留 gain-net 近似和其常数，不能直接把 Ψ 当当前48点 FULL 的精确 Bayes error。

**积分 gain 的重要边界：** 不可把上述条件 affinity 上界简单对 h 平均，就断言相同上界自动适用于 gain-integrated law；混合可增加 affinity。Bayes 性能的上界可通过此前 uniform-(θ,h) estimator bound 再取平均来获得。BAYES_SYMMETRY 的先验/群作用也不把 |A| 变成完整 Bayes error 的充分统计量。

两个码即使 μ 相同，其他旁瓣的数量、相位分布、候选相关性和 finite gain-grid mismatch 仍可能造成不同错误率。当前 FULL 高错也不是“任何接收机都无信息”的证据，因 FULL 只是固定48点 profile likelihood；本方向是在保持接收机不变时检验 code intervention，并不排除其他瓶颈。

## 6. 理论空间与有限样本预期应如何表述

旧随机码 μ≈.3253，对应 1−μ≈.6747。由 μ≥1/√67 可知，即便达到这里尚未证可达的下界，worst fourth-template mean gap 或上述 affinity 指数中的 (1−μ) 因子，相对旧随机码最多提高约30%。这不是错误率最多/至少改善30%，更不能推出10个百分点门会通过。

这给出合理而有边界的预期：当前码已显著优于调优二次的 coherence，再优化仍可能改善，但不是无限大的设计空间。若旧随机码已是所选目标的难改局部点，或 FULL 的主要损失来自有限 gain approximation，设计收益可能很小。

第三轮主线程摘要为 random SCREEN128 273/1024、FULL271/1024，quad367/366，坏方向2、CP约.006135及7.72倍速度已过相应门；准确率改善9.1797pp<10pp且random错误26.66%>.25。这使继续扩大 shortlist 缺少针对性，而保持已通过的 screening/cost 部分、改进码分离是一个可检验方向。上述数字来自交接，本轮未重审第三轮 raw；其 FAIL 不因新理论而改变。

## 7. 下一步若获准实施，应冻结的最小方案

1. 只改变已知一般列码，保留 N64/T2/SNR5、SCREEN128/FULL、gain grid、旧调优 quadratic 和旧 random reference；不得同时动 K、gain grid 或噪声/prior 来制造改善。
2. 使用旧 random w 作为事前固定的确定性初值，不抽新 seed，不按新观测选择重启。事先选定一个 primary objective（建议实际 μ），平滑势只作为求解手段；固定停止条件、迭代/线搜索上限并计全部离线设计成本。
3. 将旧码作为可行 incumbent。仅按预注册的无观测 objective 选择 checkpoint；若没有严格可信的 μ 改进，应报告设计未改进，不自动支付新科学 cohort，也不换 seed 继续碰运气。
4. 保存 μ、J_p/尾部谱、Q、code bytes/hash 和实际设计计数；必要合同包括解析梯度有限差分与本文件能量恒等式，但均属未来获准设计阶段，本轮不执行。
5. 若存在合格 code，再用独立新数据比较其 FULL 与固定旧码 FULL，并核同码 SCREEN128 的保真与成本；所有旧结果保留。收益必须来自固定候选的新实验，不能用设计 objective 下降代替真实准确率，也不能把总体目标阈值重新写成刚好通过的值。

这是一条经典 phase-only optimization 的 AFDM 适配路线。可能的科研增量是正确的 QPSK fourth-power joint orbit、restricted-mask objective、可验证下界与实际性能–成本结果之间的完整链条，而不是宣称 minimax、FFT、随机码或梯度法本身首创。

## 8. 新保存数据诊断对优先级的修正

本文件推导过程中，主线程提供了仅从已有第三轮 records 得到的补充诊断（0新调用；本代理没有重算）：

- random FULL 的271次错误中267次 different-a、4次 same-a；最大错误 offset 频数仅3，较分散。
- quadratic FULL 的366次错误中363次 different-a；offset (6,5) 有34次、(57,10) 有29次，存在明显集中。
- 按真实ρ的事后诊断 bins [.75,.875),[.875,1),[1,1.125),[1.125,1.25]，人数251/288/251/234；random错误180/78/12/1，quadratic错误189/118/45/14。

这与“quadratic 有突出的结构性困难邻居、random 已明显摊平它们”相容。random 的前两个低 gain bins 占271次错误中的258次，且 offset 分散；因此不能再把**单一最高歧义旁瓣**预设为 random 剩余错误的主要原因。低 gain 的有限信息与 nuisance handling 都值得检查，但上述分类没有证明其中任何一个是唯一原因或给出不可突破的 Bayes 下界。

据此修正优先级：保留第2–4节能量恒等式/反例作为独立理论结论；一般码 minimax 优化仍是合理、可限定预算的离线候选，但降低其预期收益，不因有下界空间就自动启动新性能 cohort。更优先澄清当前已知 gain prior 与 profile 最大化之间的差距，并评估 prior-matched marginalization 是否存在可实现、可准确审计的低成本近似。两条路线应各自隔离干预，不在同一新候选里同时换码与换 estimator 来掩盖归因。

真实ρ分层只用于事后机制分析，不能给估计器喂真ρ、删掉低gain组或改变原先验来制造通过。

### 共同 gain 的正确 Bayes 积分

对候选θ=(a,l)，记同一数据集 T×N 个 demodulated coordinates 为 z_θ,tj，生产代码已计算的连续参数形式 log likelihood（去公共常数）为

`L_θ(ρ,φ)=Σ_(t,j){logcosh[√2ρ Re(z_θ,tj exp(−iφ))/σ²]+logcosh[√2ρ Im(z_θ,tj exp(−iφ))/σ²]−ρ²/σ²}`。

当前 ρ 在 [.75,1.25] **径向均匀**、φ 圆周均匀且与θ独立；QPSK law 有π/2相位周期，故在共同 gain 先验下，θ 的正确 marginal likelihood 成比例于

`B_θ(Y)=∫_(.75)^1.25 ∫_0^(π/2) exp[L_θ(ρ,φ)] dφ dρ`。

积分外的归一化常数对θ相同，比较时可省。这里**没有额外ρ因子**：该先验不是环域面积均匀；若改用复平面面积元描述，先验密度应含1/ρ而抵消 polar Jacobian。物理 h 到 h_eff 的 delay-dependent 相位旋转保持当前先验，因此不再增加θ相关权重。

必须对 T×N 共同的同一个 gain 积分一次，不能逐帧、逐坐标各自积分后相乘；那会换成不同的 channel prior。均匀θ下，`argmax_θ B_θ` 是此冻结模型的 Bayes MAP。

精确积分的 Bayes MAP 在**总体平均0/1风险**上不劣于任意估计器，因而不劣于当前48点 profile FULL。这是有原理的方向，而非任意换打分。但它不保证每个ρ条件风险、每个已保存样本或同成本近似版本都改善；也不保证改善达到10pp，特别不能把已有271个FULL错误直接改记为可修复错误。

将同48个网格点从max换成weighted-logsumexp，可解释为一个离散 prior 或积分 quadrature 候选，不能自动称为上述连续先验的精确 Bayes MAP。现有ρ网格仅3点，phase16点；若似然尖峰或边界质量未被解析/独立数值误差控制覆盖，该近似仍可能错序。需要先论证积分精度与候选排序稳定性、估计计算成本，再决定是否值得授权新的研究实现；本轮没有做这些数值计算。

与 code optimization 相比，这一方向直接匹配已知生成先验，且有精确 Bayes 最优性的基准。但低gain若主要受信息本身限制，精确积分也可能只改善很少。继续保留当前成功的筛选保真/速度机制，并以独立新证据检验一种明确干预，比再扩K或更换seed更有针对性。

## External references and related specs

本轮没有新文献检索。使用有限字符正交、Parseval、power-mean inequality 和此前内部已核验的完整 law/Hellinger 结果；所有新增恒等式、下界和反例均在本文件给出推导。是否已有同类 restricted Gabor/ambiguity bound 或波形设计文献包含这些细节，尚未审计，不作 first-in-literature 声明。

## Caveats / Not Found

- 本轮没有生成一个新码，也没有计算任何新候选的 objective；唯一数值码信息来自旧 D 保存值。
- `1/√67` 是必要下界，不是已证可达的最优值；没有证明任何局部优化一定严格优于旧随机码。
- 新推导用于下一步方案判断，重要理论主张对外使用前仍应独立复核；不授权自动新增设计/仿真或改写旧 FAIL。
- 本代理只写 CODE_DESIGN_REASONING.md，不改 core、其他研究文件、CSV 或实验记录。

## 独立数学核验回执

2026-10-07，important_final_review已手工独立核对受限字符和、15+16Q与1005项能量、mu下界、奇q CAZAC的15个unit峰以及cubic64反例，未发现错误。该审查者不是本推导作者；随后负责设计审计实现。核验是纯数学审查，不是新性能实验或文献首创认证。
