# DOPPLER_UNCERTAINTY 独立理论审查

日期：2026-10-07。任务：`10-05-method-advantage`。审查对象仅为 `DOPPLER_UNCERTAINTY.md`，不审另一份连续变分坐标更新，不构成 Mission 最终 REVIEW 或目标完成判定。

被审最终版本 SHA256：`2db98ad140ebaad709e3b68e84c9c7265afe239c79a5abba3286fb9c5ba8bd34`。

初审版本 SHA256 为 `dbe886d238b5ab3937923b1ff38007a97e8d2d9e8f33ed5abb82c0ccce035b72`。本报告的四项发现由主线程修改原文，本代理只补审变化；所引用原文行号为初审版本。

方法：沿用已加载的 proof-checker，独立代数推导并定向核对真实 `physical.py` 的 DAFT/CPP 约定。独立性 medium；实际 runtime 模型标识未暴露，不推测名称。没有科学程序、积分程序、RNG、仿真或 SSH；唯一写入是本报告。

## 结论

式 (1)–(8) 的核心恒等式及 tangent–curvature 抵消成立。初审提出的圆对称 gain prior 例外、相关 Gaussian CF 的均值项、offset 向量联合独立性及 CF 求值成本条件，均已由主线程修订并经补审通过。最终结论为 **声明范围内数学 PASS**，没有剩余必须修复的数学错误。

这些是经典随机酉矩传输、Gaussian 去相干半群及 mean-field 期望二次型。项目上的可能增量是对候选 uncertain-Doppler 近似提出守恒约束，并利用现有 CPP 结构实现矩评估。尚无新推断器、文献新颖性或相对完整物理 F1 的完整性能–成本优势证据，当前 ANCHOR 目标未完成。

## Findings (fixed)

本代理仅写本报告。以下问题由独立审查提出、主线程修改原文、随后补审确认；没有改动冻结源码。

1. **时间原点与先验的断言过强**（原文 123–125 行）。令 `h'=h exp(i delta t0)`。若 h 与 delta 独立且 h 的分布圆对称，则 `Law(h'|delta)=Law(h)`，所以同一个独立联合先验得以保留。`CN(0,sigma_h²)`、任意独立幅度加 uniform phase 都是反例。修复：原文已要求正确推送联合先验，并明确圆对称独立 prior 的例外、相位敏感 prior 的限制和 fixed deterministic h 的重参数化。补审通过。

2. **相关 Gaussian CF 少零均值条件**（原文 141–143 行）。写出的实指数只适用于 centered offsets。一般应乘 `exp(i(s mu_i+t mu_j))`；取 trace 后还包含 `exp(i t_n(mu_i-mu_j))`。修复：原文已限定 centered 情形并补充非零均值相位因子，不改变式 (7)。补审通过。

3. **式 (7) 的独立性应是联合独立**（原文 129–137 行）。必须有整个 delta 向量与 x 独立，或至少每个相关 pair 与 x 独立。仅仅每个 delta_i 各自与 x 边缘独立，不足以拆分 `E[phase_i phase_j* xx^H]`。修复：原文已在式 (7) 前声明整个 offset 向量与 x 联合独立，后文的 `q(x)q(h)q(delta)` 满足要求。补审通过。

4. **O(NP²) 只覆盖已知核的矩收缩**（原文 165–170 行）。除 source cross-diagonal 外，还需要 pair CF 值已可用，或每个值可 O(1) 解析求得。修复：原文已计入一次 FFT(v)，将矩评估写为有条件的 O(N log N + NP²)，并要求另计任意连续 q 的构造和 CF 积分成本。Gaussian 等可解析情形支持这一级成本，但不等于完整推断迭代或接收机成本。补审通过。

## Findings (not fixed)

无剩余数学错误。新颖性、完整推断实现及相对 F1 的实际性能–成本收益尚未建立，不能通过修改本文或越权实验补齐。下文给出独立核验依据和无需新实验的最小判别。

## 数学核验

### 式 (1)–(3)：精确矩与分布边界

在输出时间坐标中，`z_n=exp(i delta t_n)(U0 x)_n`。delta 与 x 独立时，均值、Hermitian 二阶矩和非共轭二阶矩分别出现 `chi(t_n)`、`chi(t_n-t_m)`、`chi(t_n+t_m)`，式 (1)、(2) 正确。只需 x 有有限二阶矩，精确式不要求 delta 存在普通矩。

`K_nm=E[v_n conj(v_m)]`，其中 `v_n=exp(i delta t_n)`，故差分核 K 半正定且对角线为 1；Schur 乘法保持半正定和 trace。这里守恒的是未中心化二阶矩的 trace，或单独的 transported data covariance `E[D R D^H]`。完整 centered covariance 还包括随机均值的 covariance，其 trace 可以增加，不能把两者混为一谈。

`R=rho_d I` 时每次 realization 都有 `D R D^H=R`，所以式 (3) 对任意 delta law 成立。对 proper isotropic Gaussian data，条件分布也不变，故旋转后的 data 与 delta 独立；有限 QPSK 只具有相同二阶结论，其完整密度通常不同。式 (2) 也正确保留 improper soft factor 和随机均值产生的 pseudo-covariance。

### 式 (4)–(6)：正 tangent 项不能代替二阶物理模型

展开 `(I+i delta T)R(I-i delta T)`，在 `E delta=0` 下得到式 (4)。其额外 trace 为 `tau2 tr(T²R)`；当 `R=rho_d I` 时，正的高秩项是线性化模型制造的能量，而非真实 Doppler 不确定性带来的数据能量。

在左右两侧加入 `-delta² T²/2`，二阶项变为

`tau2[TRT-(T²R+RT²)/2] = -(tau2/2)[T,[T,R]]`。

迹的循环性使该修正 trace 为零；`[T,R]=0` 时精确传输就不变，不仅是 isotropic R 的二阶修正为零。原文三阶绝对矩 remainder 的阶正确；在固定有限维 compatible norm 下常数可以固定。bounded 的假设足够，且没有错误声称仅凭 variance 控制所有 heavy tails。

对 matrix unit `E_nm`，`ad_T(E_nm)=(t_n-t_m)E_nm`，所以 centered Gaussian 的精确映射为 `exp[-tau2 ad_T²/2]`，式 (6) 正确。以 variance 为时间参数时它确实构成保 trace、保半正定的随机酉半群。二阶截断本身不是一般的全局保半正定近似，不能由精确半群的性质反推截断亦然。

对随机均值单独中心化，`chi(t_n-t_m)-chi(t_n)chi(-t_m)=tau2 t_n t_m+O(tau2²)`；非共轭版本为 `-tau2 t_n t_m+O(tau2²)`。因此原文 rank-one covariance 与负号 pseudo-covariance 正确。它们属于 pilot/soft mean，不是可以再加一份式 (4) 的理由。

### 式 (7)：多径交叉项

在 delta 向量与 x 联合独立时，逐元素展开直接给出式 (7)，允许路径间相关。独立路径且 `i!=j` 时可拆为两份 marginal CF；`i=j` 必须用同一个随机量两次，给出 `chi_i(t_n-t_m)`。误用两个独立副本会把 self term 的对角线从 1 变为 `|chi_i(t_n)|²`，破坏守恒。

对 centered correlated Gaussian，原文二次型的交叉系数 2 和符号正确。trace 上的指数简化为

`exp[-t_n² Var(delta_i-delta_j)/2]`。

非零均值时再乘相位 `exp[i t_n(E delta_i-E delta_j)]`。完全共同的 offset `delta_i=delta_common` 则使所有 trace pair 的 CF 都为 1；此时整个 H 只是共同左乘一个酉 D，expected channel energy 不应依赖该不确定性。独立 offset 不具备这种多径整体守恒简化。

### 式 (8)：factorized 期望二次型

令 `M=E[xx^H]=V+mm^H`。若 x 与 H 独立，先对 x 积分，再用 `z^H z=tr(zz^H)`，即得式 (8)。gain 与 delta 也独立时，path pairs 使用完整 `E[h_i conj(h_j)]`，不要求 gain 的不同分量互相独立。linear term 同样必须使用 gain 均值，不能只在 quadratic term 更换 gain moments。

若 h 与 delta 耦合，仍可保留精确混合核 `E[h_i conj(h_j)exp(i s delta_i+i t delta_j)]`；若 x 也耦合，连 M 都不能移出期望。原文对 factorization 的限制正确。该式作为 q 下的期望可以精确，即便 q 只是 true posterior 的近似；不能因此声称 posterior factorization 精确，也不能把实际依赖 delta 的 G0-normalized gain prior 自动替换为独立 prior。

此处是 proper Gaussian measurement noise 的 expected log-likelihood quadratic，完整负对数 likelihood 还含 `1/sigma2` 和常数。它不是 marginal mixture 的负对数 likelihood，更不是把有限 QPSK Gaussian 化。二次范数本身只需要 Hermitian 二阶矩，不用 pseudo-covariance，不等于之后任意 Gaussian message 近似都可丢弃 pseudo-covariance。

## 实际 CPP 坐标与成本核对

`physical.py` 使用 `A=Lambda_c2 F Lambda_c1` 和正 Doppler。若 x、m、V 在 AF 域而输出在时间域，必须取 `U_i=D(nu_i) C_li P_li A^H`；若输入已在时间域，则去掉最后的 `A^H`。固定整数 delay 和固定 CPP 支持是本推导前提，不包含 fractional delay 或 Doppler-dependent delay 算子。

对 AF-diagonal `V=diag(v)`，实际 CPP wrap phase 恰好消去循环索引的 chirp wrap 差。令 `d_ij=l_i-l_j`，使用 NumPy FFT 的负指数约定，得到

`R_ij[n,n] = FFT(v)[d_ij mod N]/N`
`            * exp(2 pi i c1(l_j²-l_i²))`
`            * exp(2 pi i n(nu_i-nu_j+2 N c1 d_ij)/N)`。

这是直接由实际 unitary path 的行乘积得到的 source-matched identity；其 trace 在交换 i、j 后与已有 `projected_variance` 的约定一致。一次 FFT(v) 和已知 phases 即可按 pair 生成所需 diagonal，不需要 dense N×N covariance。mean responses 由一次 IDAFT(m) 加 O(NP) phase/shift 得到。

因此，当 CF 单次可 O(1) 求值时，固定 q moments 的这一 quadratic evaluation 可达 **O(N log N + NP²)**。可逐 pair 流式累加，无需存下全部 N×P×P 项。一般 full V、任意 CF 积分、q 的构造、gain solve、所有 symbol/bit messages、迭代次数、LDPC 与失败成本均不在这项证明内。已有 point-geometry projected moment 还可能有更便宜的闭式收缩，因此不能从这里直接推出相对 F1 加速。

## 贡献与最小后续判别

随机酉平均、特征函数 Schur 核、double commutator、Gaussian dephasing、Taylor 曲率补偿和 mean-field expected quadratic 均是经典数学。SP 的 mean/data 分解让某个错误容易暴露，但同样原理适用于其他“确定均值加未知信号”的模型，不是 AFDM 独有定理。

可保留的项目贡献是具体的模型一致性约束及 CPP 矩收缩；它尚未成为新的 receiver。F1 没有被证明使用式 (4) 的错误模型，现有 gain/data joint tangent 也不能被这一 Doppler 随机参数反例否定。

最小下一步是让另一份坐标更新推导明确使用哪一个 q、joint prior 和 observation factor，然后在纸面上核对四个极限：Dirac delta 恢复同 prior 的 point-geometry objective；单径 isotropic data self energy 不变；所有路径共同 offset 时整个 quadratic energy 不变；同一路径的 CF 两端不得被独立化。若候选更新没有区别于既有 off-grid VB/EP 的机制，或没有处理 F1 的真实剩余问题，应把本文保留为诊断约束，不以新仿真代替价值判断。本报告没有授权或执行这些实验。

## Verification

- 数学：式 (1)–(8) 在明确条件下成立；上列四项原文修订经补审通过。
- 源码：只读核对真实 DAFT/CPP 与 `projected_variance`；未执行数值验证。
- Lint：不适用，仅理论 Markdown；检查文档空白和引用版本哈希。
- TypeCheck：不适用，没有修改代码。
- Tests：未运行，无科学执行；静态推导不表述为 runtime PASS。
- 所有权：本代理仅写本报告；不改原文、源码、CSV、STATE、旧结果或 spec。原文修订由主线程完成；没有新的可执行代码契约需要同步。
