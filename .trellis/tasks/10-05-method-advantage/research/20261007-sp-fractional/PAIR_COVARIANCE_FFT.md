# Derivation Package: 稀疏符号相关性的 CPP 精确 FFT 矩

## Target and Status

DATA-CORRELATION-THEORY-01。解决 `DATA_CORRELATION_GAP.md` 的计算缺口：
保留少量 QPSK symbol pairs 的协方差时，如何计算原 gain/Doppler 二阶矩而不构造
N×N 数据协方差或 N×N 物理算子。COHERENT AS STATED，独立数学审查通过，待数值验证。
这是经典 FFT/稀疏 covariance 的精确 AFDM/CPP 适配，不声明首创或实测加速。

## Invariant Object and Assumptions

目标量为 K_ij(t)=E[(T_li U(d−m))_t (T_lj U(d−m))_t*]，
U=A* 是项目实际 inverse DAFT，T_l 包含真实 CPP。
N≥2，整数 delay l_i∈{0,…,N−1}，c1/c2 实数，u/v/t 均用 0…N−1 原始索引。
C_uv=E[(d_u−m_u)(d_v−m_v)*] 是 Hermitian PSD；除 N 个对角项外，
有 K 个 unordered pairs，即至多 2K 个非零 off-diagonal entries。
当前 block q_d 与 h/ν 独立；随机 ν 推广另要求 q_h 与 q_ν 独立，各路径 ν_i 独立。
固定 point ν 自动满足后两项。不允许将本公式混用到依赖 h 的 q(d|h)。

## Source Convention

`experiments/sp_afdm_frozen_20260920/src/physical.py:87` 的真实实现为
U=diag(exp(−2πic1 t²)) F* diag(exp(−2πic2 u²))，F 为单位化负号 DFT。
`experiments/afdm_sp_fractional_20261007/moments.py` 的 CPP 对 t−l<0 乘
exp(2πic1[N²+2N(t−l)])。以下符号均按这两个函数，不换成其他论文约定。

## Derivation Map

CPP wrap 严格消去 → 两个延迟 basis 的乘积 → 按 (u−v) mod N 分组 →
一次 IFFT 恢复每个 path pair 的 time covariance → 原 gain/ν 公式直接使用该矩。

## Main Derivation

**1. 延迟后的 inverse-DAFT basis。** 对任意 u，精确有

v_l,u(t)=(T_l U)_tu
=N^(−1/2) exp[−2πic1(t−l)²+2πi(t−l)u/N−2πic2u²]。

若 t−l≥0 直接成立；否则原 inverse DAFT 用 t−l+N，CPP 的
+c1[N²+2N(t−l)] 恰消去 chirp 的额外负相位，傅里叶项多出的 exp(2πiu)=1。
**不需要 2Nc1 为整数**，也不把 fractional Doppler 截断或四舍五入。

**2. 稀疏协方差的离散频差分组。** 定义

α_ij(t)=exp[2πic1(2t(l_i−l_j)−l_i²+l_j²)]，

W_ij[k]=Σ_{(u−v) mod N=k} C_uv
  exp[−2πic2(u²−v²)−2πi(l_i u−l_j v)/N]。

则由 K_ij(t)=Σ_uv C_uv v_li,u(t) v_lj,v(t)*，逐项相乘得到

K_ij(t)=α_ij(t) · IFFT(W_ij)[t]。

这里 IFFT 自带 1/N；不可再乘或除 N。frequency bin 可取模，但
u²−v² 和 delay phase 必须用原始 u/v；不能只以模差替代 c2 相位。
C 的共轭反向项都须加入 W；不能直接以 2 Re 替代一般 i≠j 的复 K_ij。
可用 K_ji=K_ij* 仅存/算 unordered path pairs。

**3. 退化为现有 diagonal variance 公式。** 若 C=diag(v)，仅 k=0 非零：

W_ij[0]=FFT(v)[(l_i−l_j) mod N]，
K_ij(t)=α_ij(t) FFT(v)[l_i−l_j]/N。

这正是当前 `_cross_source` 的 variance_fft[delay difference]×phase 项。
有 pair covariance 时，同路径 K_ii(t) 一般不恒定，但
Σ_t K_ii(t)=tr C；因此当前 gain Gram 的 diagonal 仍为 source energy，
expected quadratic 的同路径项仍能用 trace 汇总。不能把“积分后相同”写成逐 t 相同。

**4. 接回真实增益/多普勒统计。** `_cross_source(i,j)` 的 source 二阶矩应为
mean_response_i(t) mean_response_j(t)*+K_ij(t)。
对于 i≠j，再乘原 φ_i φ_j* 与完整 gain 二阶矩，原 expected quadratic/
gain Gram/Doppler Fourier 势的结构不变。均值响应与 matched 向量不受 C 的
off-diagonal 项直接影响；data objective 的 tr(G C) 项则必须更新。

### Pair 交互 G_uv 的查询也无需 dense G

若需查询 candidate symbol pair (u,v)，令 ψ_ij(t)=E[e_i(t)* e_j(t)]，
e_i(t)=exp(2πitν_i/N)。独立 ν 时 i≠j 为 φ_i*φ_j，同一路径 ψ_ii=1。
令 Z_ij=FFT(ψ_ij α_ij*)/N，则路径交互矩阵满足

(E[H_i*H_j])_uv = exp[2πic2(u²−v²)+2πi(l_i u−l_j v)/N]
  Z_ij[(u−v) mod N]。

G_uv=Σ_ij S_ji(E[H_i*H_j])_uv，其中 S_ji=E[h_i* h_j]；注意转置索引。
同一路径为 δ_uv；与数据 covariance 的 W_ij 是不同的变换，不能重复使用错缓存。

## Cost and Implementation Boundary

仅为代数操作量，未测运行速度：

- 一次 diagonal variance FFT：O(N log N)。
- 每 unordered path pair，将 2K 个 covariance entries 累加到 W：O(K)。
- 每 path pair 一次长度 N IFFT，加 α 相位/均值项：O(N log N)。
- 合计 O(P²(K+N log N))，若流式输出所需矩可用 O(N+K) 额外 scratch；
  若保存全部 cross-source kernels，需 O(P²N+K) 存储。
- G_uv 查询需另外构建 Z 的 path-pair FFT；Q 个 candidate symbol pairs 的
  查询成本为 O(P²N log N+P²Q)。没有包含在 W 的 FFT 费用里。
- C_d 改变需要更新 W/K（以及方差 FFT）；Z 不依赖 C_d。ν 改变影响 Z，
  gain 改变影响 S 的加权，delay/chirp 改变影响对应相位与变换。
  所有依赖更新、rejected proposals、缓存建造和最终保存必须计费。
  代数上不变的量不构成绕过当前 owner 合同的理由；无跨 owner 的 stale SourceMoments 复用。

pair 选择可能仍需扫描 N² 个候选；上述查询公式没有自动解决这个问题。
后续必须给出 observation-only 的有限候选/配对预算，并与 singleton 控制匹配。
不把 selected pairs 内的精确矩说成真实完整 posterior 精确。

## Boundaries and Open Risks

FFT 恒等式本身是精确的；低秩/稀疏性来自所选 block variational family。
若使用任意 dense C，形成 W 已需 O(N²P²)，不能继续引用稀疏复杂度。
pair q_B、非零 c_uv、所有 block 熵必须一致，不允许仅改 QPSK logits 而丢掉矩。
目前无代码、无 N8/N1024 数值核验、无新的接收机收益或完整成本证据。
