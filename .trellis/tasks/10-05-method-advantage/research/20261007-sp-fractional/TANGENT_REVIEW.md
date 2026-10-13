# TANGENT_INFORMATION 独立理论审查

日期：2026-10-07。任务：`10-05-method-advantage`；本报告只审查 SP + 连续分数 Doppler 理论 note，不是 Mission 最终 REVIEW，不关闭当前研究目标。

被审版本：`TANGENT_INFORMATION.md`，SHA256：
`b29cae99558be946a41c9b0f4d07e38720b108ce0a6af6c4d82c73dc8f1b4b5e`。

初审版本 SHA256 为 `2a525af473e8c3a473ee8f40730344f3832219e7e5962b48fd17788364d28267`。下列三项由审查提出、主线程修改原文，本代理只补审变化并更新报告。

审查方式：沿用已加载的 proof-checker 方法，独立逐式推导及定向只读源码核对。独立性为 medium；实际运行模型标识未暴露，不推测模型名称。没有执行科学计算、积分程序、RNG、仿真、SSH 或新实验；唯一写入是本报告。

## 结论

式 (1)–(6)、完整边缘 likelihood 的 nuisance 退化反例均成立。初审发现的 §6 最大旁瓣方向、阈值边界 cap 条件及单径生成 law 的固定 delay/base 限定，已由主线程修订并经补审核实。最终结论为 **限定范围内数学 PASS**；没有剩余必须修复的数学错误。

该 note 比已有 JET 多出完整 SP law 不可识别性及实际 G0 剪枝区间的解释，是有范围的建模诊断。它尚未证明重大创新，也未证明相对完整物理 F1 的 FER 或完整性能–成本收益；当前 ANCHOR 目标未完成。

## Findings (fixed)

本代理仅写本报告。以下为独立审查发现、主线程修复、随后补审确认的三项；原文行号指初审版本，没有修改冻结源码。

### 1. 实际 G0 的最大旁瓣方向与 §6 不符

- File：`TANGENT_INFORMATION.md:174–178`。
- Issue：实际冻结 `afdm_env.py:435` 使用 `x = m + kappa`，即系数为 `D_N(delta+m)`；`k_eff = k_base + m`。因此最大非中央系数在 **m = -sign(delta)**。初版写的是 `k=sign(delta)`，对应前文完整物理展开 `D_N(delta-k)` 的方向，不能直接套到 G0。
- Fix：主线程已区分完整物理展开索引与 G0 offset，明确 G0 使用相反符号。式 (6) 不变，因为对称五系数集合的最大幅度比不变；没有改动冻结生成器。补审通过。

### 2. 严格阈值等号不保证旁瓣最终存在

- File：`TANGENT_INFORMATION.md:190–193`。
- Issue：源码先检查 `abs(k_eff)>k_clip`，再做严格 `<` 剪枝。等于阈值只能说明不会被幅度测试删除，不能说明不会被 cap 删除。实际 G0 的符号使该情形可达：取 `k_clip=2`、`k_real=2-delta_star`，则 `k_base=2`、`delta=-delta_star`，最大旁瓣为 `m=+1`，其 `k_eff=3` 已被裁掉。其余旁瓣严格低于阈值，最终仍可只有中央 tap。
- Fix：主线程已将边界保留限定为尚未被 cap 删除的 slot。式 (6) 是 cap 后 central-only 的充分开区间，未必是最大区间；补审通过。这里不声称浮点实现逐比特实现数学等号。

### 3. 单径 gain 边缘 law 需要固定离散 slot

- File：`TANGENT_INFORMATION.md:198–203`。
- Issue：相位均匀性确实给出固定 `(l,k_base)` 下的 gain 边缘 G0 law 不随区间内 delta 变化。若进一步按实际生成器对 delay/base 也边缘化，则 `Pr(l,k_base | delta)` 可能变化：Doppler 参与 delay correction 和接受条件，base 与 residual 也没有被证明独立。初版需要明确这一条件，避免把局部固定 slot 结论读成整个单径 prior 的无条件结论。
- Fix：主线程已明确限定固定 delay 与 central integer Doppler，并排除对 Doppler-dependent delay/接受条件边缘化后的推广。无需也不得据此推论 P=8 生产 prior 的 law 存在同样的正宽零信息区间。补审通过。

## Findings (not fixed)

无剩余数学错误。重大创新及完整物理 F1 上的性能–成本收益仍未建立，属于当前研究目标的证据缺口，不能靠修改本文或越权新增实验解决。

## 数学核验

### 式 (1)：精确有限 QPSK 的 efficient Fisher 下界通过

对实 nuisance 系数任意线性组合，令 `s = s_nu - lambda_1 s_Re(h) - lambda_2 s_Im(h)`。精确 score–moment 恒等式给出

`E[(y-Ey)s] = h b - c a`，其中 c 遍历复数。

QPSK 的 proper 二阶矩与酉路径给出实观测 covariance 为 `(v/2)I`。因此 Cauchy–Schwarz 给出 `E[s²] >= 2||h b-c a||²/v`。对左边取 nuisance 投影最小值，再对右边取 c 的最小值，得到式 (1)。`sigma2>0` 时有限正 Gaussian mixture 满足所需正则性。

这没有把未知 QPSK 当作已知数据，也没有高斯化 QPSK；右端是下界而非精确有限字母表 FI。pseudo-covariance 为零是实 covariance 简化中的必要已声明条件。

Gaussian data 情形的等号也成立：酉性保证 `a^H b` 纯虚，Doppler mean score 只耦合 gain phase；gain amplitude 的 mean score 与之正交，而 covariance 的参数依赖只在 amplitude 方向。因此额外 amplitude 信息不会改变 nuisance 消元后的 Doppler 信息。这个等号不能无条件推广到非酉或多径模型。

### 式 (2)：加权时间方差通过

令 `t=C_l P_l A^H p`，则 `a=A D t`、`b=A D diag(2 pi i n/N)t`。去掉 a 的复标量方向恰得

`||P_a^perp b||² = 4 pi² ||p||² Var_w(n/N)`。

两个不同时间采样点有非零 pilot 能量即可使下界严格正；time impulse 仅使该下界为零，不足以证明精确 QPSK law 不可识别。

### 完整 law 的 central-only 反例通过

截断模型的整个密度只依赖 `beta=h D_N(delta)`，而 `D_N(0)=1`，故邻域中非零。路径 `h(delta)=beta/D_N(delta)` 保持所有 y 上的密度不变，free complex gain 下 efficient FI 为零；任意固定 data/code law 都适用。非零 scalar normalization 可以同样吸收。

这是参数族的局部反例：在 delta=0 的 channel 值误差为零，不能推出邻域 score 保真。固定 informative gain prior 改变了统计实验，不能沿用 free-gain 结论。多个固定槽的 free gains 可逐路径吸收 central-only 系数，但这仍不是生产 generating prior 的定理。

### CPP 展开及式 (3)–(5) 通过

共同的 CPP/delay 右因子酉且与 Doppler 无关；迹的循环性给出 `tr(U_j^H U_k)=N 1[j=k]`，没有遗漏 CPP 相位。有限 Fourier inversion 给出 `U_l(delta)=sum_k D_N(delta-k)U_k`。

由 `sum_n n z^n=-N/(1-z)`，原文非零索引导数的负号正确：`a_k=-2 pi i/[N(1-exp(-2 pi i k/N))]`。去除 `a_0 U_0` 后，cosecant 平方和得到式 (3)。对称索引每对贡献两份能量，给出式 (4) 的系数 6。

`2K<N` 防止偶数 N 的 Nyquist residue 重复；奇数 N、`K=(N-1)/2` 时已经保留全部 residue，有限 N 比率为 1。式 (5) 是固定 K 的大 N 极限及其级数尾界，不能当作 K 随 N 增长时的统一近似。

这些都是 operator Frobenius tangent 比例。具体 pilot 作用后的向量正交性、gain nuisance 投影和精确 SP score 都可能不同，因此 `6/pi²` 不能解释成通用 SP Fisher 保留比例。

### 式 (6)：阈值通过，源码方向已按 Finding 1 修正

对实际 G0 `D_N(delta+m)`、`m=-2,...,2`，N>=5、`0<|delta|<1/2` 时中心为 peak，最大旁瓣在 `m=-sign(delta)`。其幅度比仍为

`sin(pi |delta|/N) / sin(pi(1-|delta|)/N)`。

五系数共同归一化在该比值中消去。令 `s=sqrt(eta)`、`theta=pi/N`、`x=pi|delta|/N`，则 `sin x < s sin(theta-x)` 等价于 `tan x < s sin(theta)/(1+s cos(theta))`。对 `0<eta<1` 得式 (6)，且 `delta_star<1/2`；eta=.01 时极限为 `1/11`。

N>=5 是五个 residue 不重复且上述幅度比较成立的代数范围，不是整套生成器对所有 N>=5 均可运行的保证。默认 `k_guard=4` 时 `k_clip=min(k_max_cap,floor(N/2)-5)`；小 N 可能负 cap 或 cap=0。cap=0 时只有 delta=0 可达，不应把形式开区间视为实际 prior 的正宽支持。生产 N=1024、cap=2 不受该小 N 限制。

## 生成器与 F1 的实际边界

实际 frozen `afdm_env.py:329–346` 独立抽 uniform phases 与 velocities，接受条件仅依赖 delay/Doppler，不依赖 phase；因此接受后的 phase 仍条件均匀。对一个固定 delay/base，记 G0 中央系数为 q(delta)，实际整数 G0 atom 为 V，则

`H_G0 = g_raw q V / |g_raw q|`。

V 是单位模 phase-permutation，Frobenius norm 为 sqrt(N)。最终系数因此为均匀 unit phase，固定 slot 的 gain 边缘 law 与 delta 无关。这里使用 G0 自身的 V，不把 G0 的权重约定冒充完整物理展开。

同一段源码返回的物理 gain 却是

`g_i = g_raw / |g_raw q| = exp(i arg(g_raw))/|q(delta)|`。

其模随 delta 变化。`supplement_g1.py:72–88` 原样取 `params['g_i']` 构造完整物理 H 和 CPP observation，且 `GAIN_RULE='reuse_g0_physical_gains_without_rescaling'`。故不得为推论 G1 而偷偷把这个 gain 改成单位模。

`native_f1.py:33–45` 调用 `time_refine_keep_slots`，后者保留连续 `exp(2 pi i n nu/N)` 以及全部 physical slots，再返回 `Channel`。这次只读核对支持“F1 没有这里的 central-only 参数化缺陷”；它不是新的运行性能证据，也不证明 F1 的所有环节均最优。

## 相对已有资产的增量与价值缺口

已有 `JET.md`/`jet.py` 包含 CPP-aware Taylor jet、moment pushforward prior、碰撞 rank 讨论和 oracle operator 诊断；`physical.py` 已有完整时间域导数。Taylor 展开、Dirichlet 尾能量、nuisance projection 和已计算 response 上的 O(N) 乘法均不能独立作为新算法贡献。

本 note 的具体增量是：将 pointwise-exact 的 channel 截断反例提升为完整 SP marginalized law 的不可识别性，并把同一种退化联系到实际 G0 的正阈值剪枝区间。该增量具有诊断价值，但没有完成邻近 AFDM/OTFS/off-grid 文献的新颖性排查，也没有指向完整物理 F1 的已证实不足。

下一步最小判别应是只读确定当前仍在使用的哪个 receiver 决策或评估依赖 G0 value-energy，并检查其 generating prior 是否落在本结论范围。若 F1 已避开且没有有后果的剩余依赖，应保留此 note，转向其他机制；无需为该反例新增仿真来制造实用性声明。本报告不授权新实验。

## Verification

- 逐式推导：式 (1)–(6) 核验通过；§6 的三项修订经补审通过。
- 源码核对：只读检查实际 frozen generator、G1 gain reuse、F1 keep-slots 入口；没有执行这些代码。
- Lint：不适用，本次只新增理论 Markdown；执行文档空白和引用版本哈希检查。
- TypeCheck：不适用，没有修改可类型检查的代码。
- Tests：未运行；本派工禁止新科学执行，静态数学与源码核对不表述为 runtime PASS。
- 交付范围：本代理仅写本报告；未修改源码、被审原文、CSV、STATE、旧结果或 `.trellis/spec/`。被审原文修订由主线程完成。没有新的可执行代码契约需要同步 spec。
