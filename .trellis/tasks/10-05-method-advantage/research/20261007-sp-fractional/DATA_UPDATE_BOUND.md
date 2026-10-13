# Research: 同步 QPSK 数据更新的 KL-MM 保证

- Query: 补上 `CONTINUOUS_VARIATIONAL_UPDATE.md` 第 7 节的 Jacobi 单调性缺口：在原 SP expected log-likelihood 与 product-QPSK entropy 下，推导只用一次矩阵无关 Gram 调用的同步数据步，明确步长、谱界、零概率与 ELBO 适用范围。
- Scope: internal mathematical research；经典 KL-MM / relative-smoothness 技术的 AFDM 适配，不主张首创。
- Date: 2026-10-07
- Task: `.trellis/tasks/10-05-method-advantage`，THEORY/SELECT；仅本文件写入。未运行仿真、数值科学、SSH、实现或 Git，未修改其他研究笔记或项目状态。

## Findings

这个缺口可以在声明的工作模型内补上。冻结增益和 Doppler 因子后，令 `K=G-diag(G)`，取 `B≥λmax(K)`，并用自然对数。对单位符号能量为 P_d 的 QPSK，设

\[
\beta\ge\frac{2P_dB}{\sigma^2},\qquad
\eta=\frac1{1+\beta}.
\]

把旧概率与完整单符号 Jacobi 目标按指数 `1−η,η` 作几何混合，可同步更新所有符号，并保证工作模型 ELBO 非下降。一次数据步只需一个 G matvec；一个直接谱界可由 `PathMoments.second` 和 `gram_diagonal()` 得到。该保证不等于全局最优、LDPC 外信息或完整接收机的性能成本优势。

### 1. 文件证据与固定模型

已读：

- `.trellis/tasks/10-05-method-advantage/research/20261007-sp-fractional/CONTINUOUS_VARIATIONAL_UPDATE.md` 第 7 节：原始 SP 二次矩、QPSK 单坐标式、G/r 的矩阵无关作用及未解决的 Jacobi 问题。
- `experiments/afdm_sp_fractional_20261007/moments.py:60`–`:105`：`PathMoments` 的有限正权 Doppler 因子与 `second=C+mmᴴ`。
- 同文件 `:177`–`:202`：`gram_matvec(value)` 与 `gram_diagonal()`，完整同路径自项和跨路径二阶矩。
- 同文件 `:204`–`:210`：`mean_adjoint(y)`；`:116`–`:128` 的 `prepare_source` 接受更新后的 AF 均值、方差。
- 同文件 `:39`–`:47`：现有实数/非负结果检查不通过裁剪掩盖超容差错误；下文的数学保证不替代浮点验证。

沿用原始似然 `y=H(p+d)+w`，`w~CN(0,σ²I)`，σ²>0。在这一次数据更新中，p、σ²、独立符号原先验 π_k，以及 q(h)、q(ν) 全部固定。令

\[
G=E[H^HH]\succeq0,\quad r=E[H^H]y,\quad
g=\operatorname{diag}G,\quad D=\operatorname{diag}(g),\quad
K=G-D,\quad b=r-Gp. \tag{1}
\]

每个数据符号取 `Q=sqrt(P_d/2){±1±i}`，P_d>0；q(d)=∏_k q_k(d_k)。概率 q_k、π_k 在各自允许支持上归一化，所有 KL 均使用自然对数。记 `μ_k=Σ_a q_k(a)a`。不把 q(d) 改成高斯，不在时域另设独立 QPSK，也不把上一轮 q 当作新观测。

### 2. 原数据 ELBO 化为熵加非对角均值耦合

因为 QPSK 恒模，`v_k=P_d−|μ_k|²`，所以

\[
\begin{aligned}
E[(p+d)^HG(p+d)]
&=(p+\mu)^HG(p+\mu)+\sum_k g_k(P_d-|\mu_k|^2)\\
&=\text{const}+2\Re\mu^HGp+\mu^HK\mu.
\end{aligned}
\]

将真正的 product-QPSK 熵与原先验项保留，数据相关 ELBO 为

\[
\boxed{\mathcal L_d(q)=
-\sum_k\operatorname{KL}(q_k\Vert\pi_k)
+\frac{2\Re\mu^Hb-\mu^HK\mu}{\sigma^2}
+\text{const}.} \tag{2}
\]

只需二次矩，是因为这里计算 `E_q log p(y|d,h,ν)`；并不是以二次矩代替完整 QPSK 的边缘似然。K Hermitian、对角为零，故 `tr K=0`，并且 `λmax(K)≥0`。若 `λmax(K)=0`，则 K=0。

在旧 q 处，令

\[
z=b-K\mu=r-G(p+\mu)+g\odot\mu,
\qquad u_k(a)=\frac2{\sigma^2}\Re(\overline a z_k). \tag{3}
\]

单符号坐标最优目标是 `J_k(a)∝π_k(a)exp(u_k(a))`。全部同步直接置为 J，通常没有单调保证；下文保留这个目标但约束同步位移。

### 3. 概率 KL 控制均值位移，常数为 2P_d

对任意两个 QPSK 分布 q_k′、q_k，取 `Δμ_k=E_(q_k′)a−E_(q_k)a`。由恒定幅度与 Pinsker 不等式，

\[
|\Delta\mu_k|\le\sqrt{P_d}\|q_k'-q_k\|_1,
\quad \|q_k'-q_k\|_1^2\le2\operatorname{KL}(q_k'\Vert q_k),
\]

因此

\[
\boxed{\|\Delta\mu\|^2\le
2P_d\sum_k\operatorname{KL}(q_k'\Vert q_k).} \tag{4}
\]

若 KL 为无穷，该不等式作为扩展实数不等式仍成立，但不能用来获得跨出旧概率支持的有限惩罚更新。一般四点 QPSK 分布下，常数 2P_d 不能随意减半：在一对相反符号上各半概率，作微小反向概率移动，(4) 的比值趋于 2P_d。只有另行证明并持续保持实/虚 bit 因子独立等额外结构，才可使用更紧常数；本更新不依赖它。

写 (2) 中的二次部分为 F(μ)。精确差分为

\[
F(\mu+\Delta\mu)-F(\mu)
=\frac2{\sigma^2}\Re\Delta\mu^Hz
-\frac1{\sigma^2}\Delta\mu^HK\Delta\mu. \tag{5}
\]

取 `B≥λmax(K)`、`β≥2P_dB/σ²`，就有

\[
\frac{\Delta\mu^HK\Delta\mu}{\sigma^2}
\le\beta\sum_k\operatorname{KL}(q_k'\Vert q_k). \tag{6}
\]

所以将 F 在旧均值处线性化，并减去右侧 KL，得到处处不大于真实 ELBO、且在旧 q 相等的 MM 下界。这里用的是最大特征值上界，不要求 K 为 PSD，也无需下界控制其负特征值。

### 4. 显式同步步、步长与逐式增量保证

最大化上述下界是 N 个独立四点优化：

\[
\max_{q_k'}\sum_a q_k'(a)[u_k(a)+\log\pi_k(a)]
+H(q_k')-\beta\operatorname{KL}(q_k'\Vert q_k).
\]

当 β>0 时，精确解为

\[
\boxed{q_k^+(a)=
\frac{\exp\{\eta[\log\pi_k(a)+u_k(a)]
+(1-\eta)\log q_k(a)\}}{Z_k},\qquad
\eta=(1+\beta)^{-1}\le
\frac1{1+2P_dB/\sigma^2}.} \tag{7}
\]

它可写成 `q_k^+ ∝ J_k^η q_k^(1−η)`。这是概率的几何插值，不是 `q^+=(1−η)q+ηJ` 的算术阻尼；后者不因外观类似自动继承这个证明。旧 q 出现在计算用的 KL 近端项中，不是再乘一次观测导出的 Bayesian prior。在原允许支持内 q 严格为正时，任一正步长的固定点仍满足 `q_k=J_k`，没有把原似然永久降温。

**β=0 必须单独分支**：直接令 `q_k^+=normalize(π_k exp u_k)`。不计算 `0 log 0` 或 `0^0`，也不人为锁住旧零概率。全局安全 β=0 对应 K=0；第 7 节的逐点验收也允许在某些 K≠0 状态试探 β=0。

令 `D_f=ΣKL(q_k^+||q_k)`、`D_r=ΣKL(q_k||q_k^+)`，`Δμ=μ^+−μ`。对 β>0，在旧支持内由四点 Gibbs 最优性严格得到

\[
\boxed{\mathcal L_d(q^+)-\mathcal L_d(q)
=(1+\beta)D_r+\beta D_f
-\frac{\Delta\mu^HK\Delta\mu}{\sigma^2}.} \tag{8}
\]

证明方向：MM 下界的“新最优解减去旧分布”恰为 `(1+β) KL(旧||新)`；原目标与下界之间的差为 `β KL(新||旧)−ΔμᴴKΔμ/σ²`。这两个 KL 的方向不同，不能交换。

结合 (6)，最终保证为

\[
\boxed{\mathcal L_d(q^+)-\mathcal L_d(q)
\ge(1+\beta)\sum_k\operatorname{KL}(q_k\Vert q_k^+)\ge0.} \tag{9}
\]

当 β=0，(8) 直接解释为 `ΔL=D_r−ΔμᴴKΔμ/σ²`，删除整个 `βD_f` 项，而不是计算 `0×∞`。K=0 时即有同样的增量保证。

固定有效 G/r、有限 β，且 q 在原允许支持内保持正概率时，非固定点有严格上升。这个结论不声称全局最优或速率；旧支持缺失时也只保证该支持面内的更新，见第 6 节。

### 5. 从实际路径二阶矩获得可计算的保守谱界

令 `S=PathMoments.second=C+mmᴴ`，`s0=tr S`。由现有期望 Gram 的真实自项与独立 Doppler 因子，可写

\[
G_t=s_0I+\sum_{i\ne j}S_{ji}\bar W_i^H\bar W_j,
\quad \bar W_i=\operatorname{diag}(\phi_i)C_i\Pi_i,
\quad G=AG_tA^H.
\]

正概率 Doppler 因子满足 `|φ_i[n]|≤1`，CPP/移位酉性因此给出 `||Wbar_i||₂≤1`，故

\[
\lambda_{\max}(G)\le
\gamma:=\operatorname{tr}S+\sum_{i\ne j}|S_{ij}|.
\]

又因 `K=G−diag(g)`，可直接采用

\[
\boxed{B_{\rm safe}=\max\{0,\gamma-\min_k g_k\},\quad
\beta_{\rm safe}=2P_d B_{\rm safe}/\sigma^2.} \tag{10}
\]

计算 γ 为 `O(P²)`，g 已有 `gram_diagonal()`，不需要构造 G 或运行迭代特征值估计。幂迭代的有限步 Rayleigh 商通常是 λmax 的下方估计，不能直接当作本定理的安全上界。

理论上 `γ−min(g)≥λmax(K)≥0`；式中 max 是明确的非负上界定义，不是允许吞掉无效 S、非 Hermitian G 或严重数值误差。原 API 的验证和后续浮点容差仍须执行。若 S 正好对角，则 G=s0I，B_safe=0，恢复一次精确同步解；不应只因有 gain variance 就强制小步长。

该界用绝对值累加，忽略跨路径相位抵消与实际 Gram 的细结构，可能明显过松。它是廉价保守界，不是声称已找到了实用最优步长。

### 6. 零概率、原先验和完整 ELBO 的边界

- 若 π_k(a)=0，则有效工作模型要求 q_k(a)=0；在该允许支持上执行更新。旧 q 在 π=0 的位置有正质量时，原 KL 已无穷，不是可正常开始的状态。
- 若 π_k(a)>0 而旧 q_k(a)=0，β>0 的更新将该位置锁为零。保证仅限旧支持面，不能声称达到完整四点空间的驻点；一个人为 hard decision 可能因此完全冻结。
- 最直接的可执行前提是从原允许支持内严格正的 q 开始，以 log-probability 存储更新。不要把数值下溢误认作模型的硬零。随意加 epsilon/floor 或概率混合可能改变目标或使 ELBO 降低，不属于本证明。要恢复人为删掉的支持，需重新声明初始化，或单独用原 ELBO 接受检验；不能静默修复后沿用单调性声明。
- β=0 分支只依赖 π 和 u，允许恢复所有原允许符号，不使用旧零概率作为掩码。
- 对 q(h)、q(ν) 固定且所有其他因子的原先验 KL 有限的同一个工作模型，完整 ELBO 与 (2) 只差常数，因此 (9) 就是完整 ELBO 的真实数据步保证。改变 π、σ²、G/r 或其他因子后必须重算，不得沿用旧谱界和旧差分。
- `PathMoments` 当前将有限正权节点视为精确离散 Doppler law。如果该 q(ν) 的参考工作先验也是匹配支持的离散 law，则本数据步可直接作用于其有限 ELBO；若节点只是连续因子的求积近似，则要另外控制矩误差。把字面上的有限原子 q(ν) 配一个纯连续先验，其整体反向 KL 无穷，不能借有限数据项上升宣称完整连续 ELBO 上升。
- 实际 G0 归一化增益先验、硬 LDPC 码字先验的支撑问题仍按前一笔记处理。本步是声明的独立 QPSK 工作模型更新，不是 LDPC 外信息，也没有证明 decoder 接口正确。

### 7. 可选逐点验收：减少保守阻尼而保留同一目标保证

不必把 B_safe 永久当作实际步长。对固定旧 q，可试探较小 β≥0，用 (7) 生成候选，然后计算

\[
\Delta\mu=\mu^+-\mu,\qquad
K\Delta\mu=\texttt{gram\_matvec}(\Delta\mu)-g\odot\Delta\mu.
\]

若 β>0，接受条件为

\[
\boxed{\beta D_f\ge
\operatorname{Re}(\Delta\mu^HK\Delta\mu)/\sigma^2.} \tag{11}
\]

若 β=0，只测试右侧是否 ≤0，不计算 D_f。这是沿本次候选位移的曲率证书；由精确恒等式 (8)，它同样保证 (9)，无需宣称较小 β 是全局谱界。对 π 内部正旧 q，可用 `η_j=2^{-j}`、`β_j=2^j−1` 回溯；至迟到

\[
j=\lceil\log_2(1+\beta_{\rm safe})\rceil
\]

就有理论保证，最多该值加 1 个试探。每个试探额外需要一次 Gram matvec，须完整计费；失败候选不写回 q。实际浮点比较需使用已声明误差检查，不能把“理论最终会接受”当成无条件吞掉数值失败的理由。

接受后可缓存 `G(p+μ^+)=G(p+μ)+GΔμ`，下一步无需重复算同一个向量。因此试探 matvec 可同时提供下一步所需缓存；总成本按初始化、所有试探及外层刷新实际计数，而不是按成功步数隐藏拒绝成本。该回溯仍是经典 MM 的适配，不构成新算法首创。

### 8. 与当前 moments API 对齐的可实现公式

冻结一个 `PathMoments` 实例 `op` 时，先计算并缓存

```text
g = op.gram_diagonal()
r = op.mean_adjoint(y)
S = op.second
gamma = real(trace(S)) + sum(abs(S[i,j]) for i != j)
B_safe = max(0, gamma - min(g))
beta = 2 * P_d * B_safe / sigma2
eta = 1 / (1 + beta)
```

每个保守同步步只需

```text
mu[k] = sum_a q[k,a] * alphabet[a]
Gx = op.gram_matvec(pilot + mu)
z = r - Gx + g * mu
u[k,a] = (2 / sigma2) * real(conj(alphabet[a]) * z[k])

if beta == 0:
    logits = log_pi + u
else:
    logits = eta * (log_pi + u) + (1 - eta) * log_q
log_q_new = logits - row_logsumexp(logits)
q_new = exp(log_q_new)
```

掩码按第 6 节原允许支持处理。新 `μ` 与 `v=P_d−|μ|²` 供 `prepare_source(pilot, μ, v)` 使用；实现时也可直接计算 `v_k=Σ_a q_k(a)|a−μ_k|²`，避免相近数相减造成的负舍入，而非用裁剪隐瞒错误。这个数据步自身不要求每次调用 `prepare_source`；后续 Doppler/gain 更新需要新源矩时再按其成本调用。

必须保留完整四点 q/log q 与原 π/log π，因为一般四点分布的 μ、v 不足以恢复熵和 KL。只有显式保持 bit-product 因子时，才可由两个 bit 概率重建四点概率；不能将仅有的 μ/v 当作完整变分状态。

当前 `gram_matvec` 每次为一次 IDAFT、一次 DAFT 和 `O(NP²)` 路径收缩。固定工作模型的保守步总计 `O(N log N+NP²+4N)`；初始 g 为一次普通 FFT 加路径对收缩，r 为两次 DAFT 加 `O(NP)` 收缩，γ 为 `O(P²)`。没有逐符号 Gram 调用，也不需形成 N×N H/G；保存 q/log q 仅 `O(4N)`。回溯、外层因子更新和所有内层迭代另计。

### 9. 保守界是否使该适配无用：限定于当前缺口的可证伪判据

保证上升不等于值得运行。至少记录 `B_safe`、`β_safe`、η、Gram 调用数、实际数据 ELBO 增量和固定点残差，例如 `ΣKL(q_k||J_k)`；不能只报告步数或收敛曲线平滑。

具体的阻尼限制可直接从 (7) 看出。对任意两个允许符号 a,b，定义旧 log-odds `ℓ_k(a,b)` 与本次坐标目标的 log-odds `t_k(a,b)=log[π_k(a)/π_k(b)]+u_k(a)−u_k(b)`，则

\[
\ell_k^+=(1-\eta)\ell_k+\eta t_k. \tag{12}
\]

在固定 η 的 T 步中，若所有目标 log-odds 与初值的距离至多 M，则

\[
|\ell_k^{(T)}-\ell_k^{(0)}|
\le[1-(1-\eta)^T]M\le T\eta M. \tag{13}
\]

所以当实际预算只允许 T 次 matvec 且 `Tη≪1`，算法最多走完这个有界目标变化的一小部分；这可以被记录的 log-odds 和目标范围直接核对，不是 BER 结论。若固定预算结束后固定点残差仍高于预先声明的容差、每次 matvec 的 ELBO 增益又很小，便否定“这组保守步长在该数据子问题上有可用收益”的主张。

对可选验收步，还可比较 `β_safe` 与实际所需比值 `max(0, ΔμᴴKΔμ/(σ²D_f))`（只在 D_f>0 时定义）。若安全界远大于逐点证书，需要付出多少额外 matvec 才能换来更多 ELBO 增益，应按同一冻结问题和相同总调用预算比较。若回溯开销抵消了收益，或内层数据更新成本吃掉相对于现有方法的余量，就保留本单调性结果，但不能据此宣称方法有实用优势。

该适配并不因“KL-MM 已有 antecedent”而自动失去价值：若它以一次矩阵无关 Gram 解决 AFDM 当前数据更新的真实稳定性/成本问题，仍可成为有用组件。它的价值需要证据，不能由经典性直接否定，也不能由数学保证直接宣布成立。

## Caveats / Not Found

- 本文件是解析证明和 API 静态核对；未实现或运行增量验证。
- 保证针对同一有效工作模型、固定其他因子、精确 G/r 及 KL 的数据步。浮点误差、连续求积误差、模型切换与 decoder 接口尚无保证。
- 已解决廉价同步步的单调性缺口；未证明全局最优、完整收敛速率、BER/FER 或端到端性能成本优势。
- 方法属于经典 KL-MM / 镜像近端技术的具体 AFDM 适配，不主张新算法首创。
