# 同步 QPSK 数据步独立数学审查

日期：2026-10-07。任务：`.trellis/tasks/10-05-method-advantage`。仅审查 `DATA_UPDATE_BOUND.md`；不是原始结果重算、实验准入或完整目标 REVIEW。

最终被审版本 SHA256：`a8293975fc228b03e4f215089a30e8147858608a02212beba7c26555352f5cdf`。初审版本为 `cfc968065adbf5349d6fba32b68aa23d5da39d48490d8006566caa9f454d1d85`；主线程按审查意见增加了一处支持限定。

沿用 proof-checker，独立性 medium，实际 runtime 模型名称不可见。仅解析推导与既有 API 约定核对；没有数值科学、RNG、求积、仿真、SSH、raw recomputation 或源码执行。本代理只写本报告。

## 结论

**数学 PASS**。式 (8) 的两个 KL 方向、2P_d 常数、保守谱界、β=0 分支、零概率边界及逐点接受条件均成立。修订后的 fixed-point 声明有正确支持前提；未发现剩余必须修复的数学错误。

这补齐了声明的固定工作模型内“一次 Gram matvec 的同步 QPSK 数据步”单调性缺口。它是可保留的有用适配组件候选，不因 KL-MM 已有先例而自动失去价值；数学保证也不等于已经有实用步长、完整变分算法收敛或接收性能优势。

## Findings (fixed)

- File：`DATA_UPDATE_BOUND.md` §4 式 (7) 后。
- Issue：初版“任一正步长的固定点仍满足 q=J”没有当场限定支持。若 β>0 且旧 q 是单点 hard decision，更新会锁在该支持面；即使完整 J 不是该单点分布，也可以成为该受限更新的固定点。
- Fix：主线程已补充“在原允许支持内 q 严格为正时”。与 §6 的支持面说明一致；补审通过。没有改动数学式或科学源码。

## Findings (not fixed)

无剩余数学错误。原文已明确保留有限精度、连续求积误差、生产 prior/LDPC 支撑、其他因子更新以及保守步长实际成本等边界；本次不把这些未验证项目当成已通过。

## 独立推导

### ELBO、KL 常数及曲率方向

QPSK 恒模使 `v_k=P_d-|mu_k|²`。把 `tr(GV)` 加到均值二次型后，数据均值的 diagonal quadratic 正好消去，因此耦合矩阵是 `K=G-diag(G)`，不是 G 本身。熵和原 independent-symbol prior 保留为 `-sum KL(q_k||pi_k)`，得到式 (2)。Hermitian K 的 trace 为零，故 `lambda_max(K)>=0`；若最大特征值为零，所有特征值均为零，K=0。

`|Delta mu_k|<=sqrt(P_d)||q_k^+-q_k||_1` 与使用自然对数的 Pinsker 给出 `|Delta mu_k|²<=2P_d KL(q_k^+||q_k)`。原文指出常数不能普遍减半是正确的：在相反 QPSK 符号上以 `(1/2,1/2)` 为旧分布、扰动为 `(1/2+epsilon,1/2-epsilon)`，均值位移平方与 KL 的比值趋于 2P_d。

精确二次差分为 `2 Re(Delta mu^H z)/sigma²-Delta mu^H K Delta mu/sigma²`。只有 K 的最大特征值决定这个“减去的曲率项”的上界，不需要 K 半正定，也不需要以最大绝对特征值控制负方向。因此 `B>=lambda_max(K)`、`beta>=2P_d B/sigma²` 确实产生紧贴旧 q 的 ELBO 下界。

### 式 (7)–(9)：KL 方向逐项核对

记旧 q 固定时的 separable surrogate 为

`Q(q') = -sum KL(q'_k||pi_k) + sum E_(q'_k)u_k - beta sum KL(q'_k||q_k)`。

在共同有效支持上配成 Gibbs 形式，得到式 (7)，并且对任意候选 q' 有

`Q(q') = constant - (1+beta) sum KL(q'_k||q_k^+)`。

因此 surrogate 的新旧差为 **`(1+beta) KL(旧||新)`**。真实目标相对 surrogate 还需加回近端项并扣除精确曲率，即

`Delta L = (1+beta)D_r + beta D_f - Delta mu^H K Delta mu/sigma²`。

这里 `D_r=KL(旧||新)`、`D_f=KL(新||旧)`，原式 (8) 正确，不能互换。由曲率上界可得式 (9)；在原允许支持内严格正、有限 beta、精确 G/r 下，非固定点有严格上升。

### β=0 与支持

β=0 时直接解没有近端项的 Gibbs 问题，仍有 `Delta L=D_r-curvature`。即使旧 q 有硬零而新 q 恢复先验允许的支持，D_f 可以无穷，但整项 `beta D_f` 已不存在，不能计算 `0*infinity`。K=0 时这是一遍精确同步解；K!=0 时只在候选曲率非正的逐点接受条件下获得同样保证。

β>0 时有限 `KL(q^+||q)` 将新分布限制在旧支持内；该面内的 Gibbs 解为正，所以 `KL(q||q^+)` 有限。若旧支持不完整，单调性仍可在该面成立，但完整空间的 fixed-point 声明不成立。原 prior 为零的位置不可让旧 q 有正质量，否则原工作 ELBO 已不处于有限可比较状态。

以 log probability 避免数值下溢符合证明条件；任意 epsilon floor、算术混合或硬零恢复不是本证明的步骤。finite atomic q(ν) 若搭配纯连续 prior 会有整体 reverse-KL 支撑问题，不能仅凭有限数据项上升声称完整连续 ELBO 上升。原文对此以及 production normalized-gain / hard-LDPC 支撑限制均表述正确。

### 式 (10)：实际路径谱界

`G_t=s0 I+sum_(i!=j) S_ji Wbar_i^H Wbar_j`，其中每个 Wbar_i 的谱范数至多 1。对任意单位向量取 quadratic form 并用三角不等式，得到

`lambda_max(G)<=gamma=tr(S)+sum_(i!=j)|S_ij|`。

再由 `lambda_max(G-D)<=lambda_max(G)-min(g)`，得到 `B_safe=max(0,gamma-min(g))`。它使用实际 G 的 diagonal，而不是把非均匀路径矩简化成 iid variance。若 S 对角，则 G=s0 I、B_safe=0。有限次 power iteration 的 Rayleigh 商不能作为安全上界；原文没有犯此错误。

该界正确但可能很保守；绝对值求和丢掉相位抵消，并不保证得到有用的 eta。浮点 Gram/diagonal 与 S 必须维持已声明的验证，不可用 max/clipping 掩盖无效状态。

### 式 (11)–(13) 与调用成本

逐点测试 `beta D_f>=Re(Delta mu^H K Delta mu)/sigma²` 直接代入式 (8) 即得同一单调下界。β=0 只比较曲率与零，方向正确。以 `beta_j=2^j-1` 回溯，至 `ceil(log2(1+beta_safe))` 已到全局安全值；从 j=0 开始，最多再加一计入试探总数。这个结论依赖精确计算和有效支持，不保证带误差实现无条件成功。

固定 η 的 log-odds 递推是原式 (12)，展开 T 次后权重之和为 `1-(1-eta)^T`；若每次目标 log-odds 与初值之差至多 M，则式 (13) 成立。它约束冻结计算预算下的最大变化，不是 BER/FER 或一般收敛速度定理。

在 q(h)、q(ν) 固定时，G/r/g 与 γ 可缓存。每个保守数据步一个 G matvec 加四点 logits 即足够；完整 q/log q 仍需保存，mu/v 不能恢复一般四点分布的熵。回溯的每个试探都需额外 matvec，但接受候选的 `G Delta mu` 可正确更新下轮缓存。文中初始 g/r、失败试探、外层刷新及所有步数另计的成本边界成立。

## 可保留的贡献与下一步边界

原始 Jacobi 数据步没有普遍单调保证；本文用经典 KL-MM 给出结构化 G 下的一次 matvec 保守替代，确实解决了一个具体数学调度问题。可按用户允许的小创新方向保留，声明为 SP-AFDM 的矩阵无关稳定数据更新组件，而非新的通用 MM 原理。

是否值得使用，应由事先固定的 matvec 总预算下的 beta/eta、ELBO 增量、固定点残差和回溯失败成本判断。它不自动修复 gain/geometry prior 的模型失配、支持获取、连续积分、decoder 接口或端到端性能。当前没有相应运行证据。

## Verification

- 解析式与支持边界：PASS，含 fixed-point 条件修订复核。
- Lint / TypeCheck：本次仅 Markdown，不适用。
- 数值 Tests / raw recomputation：NOT RUN；没有科学执行或 SSH。
- 文档格式与最终被审 SHA256：检查通过。
- 所有权：仅本报告；未改其他文件、源码、CSV、STATE 或旧结果。后续 saved-array audit 须另行绑定源码和 0 new geometry / 0 new observation 的独立预算。
