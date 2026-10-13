# Research: 连续多普勒的精确 mean-field 坐标更新

- Query: 从原始 SP 似然推导连续实数 Doppler 因子、联合复高斯增益因子及 AF 域 QPSK 因子的变分更新；核对 CPP、自路径能量、无稠密 H 的计算成本和先验适用边界。
- Scope: mixed；解析推导、项目源码与已保存论文文本的定点核对。
- Date: 2026-10-07
- Task: `.trellis/tasks/10-05-method-advantage`，Mission THEORY-01；仅本文件由本研究者写入。未运行实现、仿真、RNG、SSH 或 Git。

## Findings

在明确的独立工作先验与 mean-field 因子族下，Doppler 坐标更新成立：自路径二次项严格与该路径的 ν 无关，剩余似然指数是实值有限 Fourier 多项式。精确 CPP 使非均匀 AF 符号方差的路径间对角交叉矩只需一次 FFT 后逐路径对计算；更新系数的预处理为 `O(N log N+NP²)`。但连续积分、联合增益求解、数据更新顺序和实际生产先验仍需单独计费/建模；这不是完整接收机的成本或性能证明。

### 1. 已读文件与代码契约

下列引用中的 `FROZEN` 为 `experiments/sp_afdm_frozen_20260920/`，`UP=FROZEN/upstream/spafdm_receiver_handoff/`：

- `research/20261007-sp-fractional/DOPPLER_UNCERTAINTY.md:127`–`:170`：路径交叉矩、mean-field 期望二次项与尚待证明的计算成本。该文件未修改。
- `FROZEN/src/physical.py:20`、`:87`、`:103`：真实 CPP、DAFT 约定及连续 Doppler 导数；已在前一子任务读过。
- `experiments/sp_afdm_native_joint_20260921/src/twofft.py:11`–`:24`：`TimePathOps.idx`、CPP/Doppler 相位、时域响应与伴随移位。
- 同文件 `:30`–`:35`：现有 scalar P-BiG-AMP 的增益工作先验与初始化边界；下文不是把它已有的 scalar 更新冒称为新公式。
- 同文件 `:89`–`:98`：已有 `time_refine` 用 `FFT(v)` 与时延差计算增益 Gram 的数据方差项，与下文 CPP 交叉矩符号相符。
- `experiments/afdm_shared_channel_20261004/PRODUCTION_PRIOR.md:25`–`:74`、`UP/afdm_sp_joint_unrolled/supplement_g1.py:14`、`:76`–`:85`：真实 G0 归一化增益及 G1 原样复用规则。生产增益先验不是独立联合高斯。
- `.mission/20261007-sp-fractional-trans/raw/2607.17001v1.txt`：OTFS off-grid VB、有限 steering 指数与 VM 近似。
- `.mission/20261007-sp-fractional-trans/raw/2607.18881v1.txt`：AFDM SP 数据辅助 GESBL、Gaussian 等效残差和网格演化。

以下推导只使用 `TimePathOps` 的精确物理移位/相位/伴随结构；现有 `R`、`power()` 及 scalar AMP 方差不能替代本笔记的非均匀源矩或完整期望 Gram。

### 2. 模型、因子与“精确”的含义

取 N 个 AF 符号、P 个固定路径槽，整数时延 `0≤l_i<N`，前缀覆盖所有时延。已知 `p≠0`，数据仍未知：

\[
y=\sum_{i=1}^P h_iU_i(\nu_i)(p+d)+w,
\quad w\sim\mathcal{CN}(0,\sigma^2I),\quad \sigma^2>0.
\]

DAFT 与 CPP 取原始约定

\[
A=\Lambda_2F\Lambda_1,\quad U_i(\nu)=A D_\nu C_i\Pi_i A^H,
\quad t_n=2\pi n/N,\quad D_\nu[n,n]=e^{it_n\nu}.
\]

`(Π_i z)_n=z_(n-l_i mod N)`；`C_i` 是实际 CPP 对角相位。旋转观测为 `Y=Aᴴy`，定义 `L_i=C_i Π_i Aᴴ`，则原始似然为

\[
p(Y\mid d,h,\nu)\propto
\exp\left[-\sigma^{-2}\left\|Y-\sum_i h_iD_{\nu_i}L_i(p+d)\right\|^2\right]. \tag{1}
\]

选择变分族，而非断言真实后验有此分解：

\[
q(d,h,\nu)=\Big[\prod_{k=0}^{N-1}q_k(d_k)\Big]
\mathcal{CN}(h;m,C)\Big[\prod_{i=1}^P q_i(\nu_i)\Big]. \tag{2}
\]

每个 `q_k` 支持于原 AF 域 QPSK，不在时域另设独立 QPSK。记

\[
\mu=E_qd,\quad V=\operatorname{diag}(v_k),\quad
\bar x=p+\mu,\quad M=V+\bar x\bar x^H,\quad
S=E_qhh^H=C+mm^H,\quad
\phi_i[n]=E_{q_i}e^{it_n\nu_i}. \tag{3}
\]

允许 q_k 的符号概率不均匀；它可以有非零伪协方差，但原 proper-noise 复线性似然的平方范数只需要 M，不需要 `E[xxᵀ]`。不能因此声称完整数据后验是高斯或 proper。

精确坐标公式意为 `q_i* ∝ exp(E_(q_-i) log p(Y,d,h,ν))` 在指定变分族内的坐标最优解。这里计算的是 `E_q log p`，不是 `log E_q p`；二次矩足够计算前者，不表示已用二次矩精确得到完整 QPSK 边缘似然。它需要明确的原始先验。先推导工作模型

\[
p(d,h,\nu)=\prod_k\pi_k(d_k)\;
\mathcal{CN}(h;m_0,C_0)\;\prod_i\pi_i(\nu_i),\quad C_0\succ0. \tag{4}
\]

π_i 可为已声明有界实区间上的均匀先验或其他已声明密度。它不是默认生产 UWA 先验。非高斯、几何耦合及奇异生产先验的限制见第 8 节。

### 3. CPP 对角交叉矩：一次 FFT(v) 后不再需要稠密源协方差

令 `s_i=L_i xbar`，以及

\[
R_{ij}[n]=E[(L_ix)_n\overline{(L_jx)_n}]
=s_i[n]\overline{s_j[n]}+K_{ij}[n],\quad
K_{ij}[n]=(L_iVL_j^H)_{nn}. \tag{5}
\]

真实 CPP 恰好消去负索引 wrap 的额外 chirp 相位，因此对所有输出 n 和 AF 索引 k，均有不取模的解析式

\[
(L_i)_{nk}=N^{-1/2}
e^{-2\pi ic_1(n-l_i)^2}
e^{2\pi i(n-l_i)k/N}e^{-2\pi ic_2k^2}. \tag{6}
\]

证明：对 `n-l_i<0`，`C_i[n] exp[-2πic1(n-l_i+N)²]` 正好等于 `exp[-2πic1(n-l_i)²]`；傅里叶项的额外 `exp(2πik)` 为 1。这里没有假设 CPP 为普通 CP，也没有要求 `2Nc1` 为整数。

定义带标准前向 FFT 符号的

\[
\widehat v[d]=N^{-1}\sum_k v_ke^{-2\pi idk/N},\qquad d=l_i-l_j.
\]

把 (6) 代入 (5)，c2 相位相消，得到

\[
\boxed{K_{ij}[n]=\widehat v[(l_i-l_j)\bmod N]
e^{2\pi ic_1[2n(l_i-l_j)-l_i^2+l_j^2]}.} \tag{7}
\]

于是一次 IDAFT 得到 xbar 的时域向量，再用 `TimePathOps` 的 CPP 移位得所有 s_i；一次 FFT(v) 得到所有方差交叉矩所需的标量。逐 (n,i,j) 构造或流式消费 R_ij 为 `O(NP²)`，不存储 `Aᴴ V A` 或 H。

两个直接可反驳的检查：`K_ii[n]=mean(v)`；若 `V=vI` 且 `l_i≠l_j`，则 `K_ij[n]=0`。同延迟不同 Doppler 的路径不能按“不同路径”而删除该项。

### 4. q(ν_i) 的连续坐标更新

令其余因子固定。完整期望平方误差为

\[
\begin{aligned}
\mathcal E={}&\|Y\|^2
-2\Re\sum_{n,i}\overline{Y_n}\,m_i\phi_i[n]s_i[n]
+\sum_i S_{ii}\operatorname{tr}M\\
&+2\Re\sum_{i<j}S_{ij}\sum_n
\phi_i[n]\overline{\phi_j[n]}R_{ij}[n].
\end{aligned} \tag{8}
\]

对同一路径 i，必须使用同一个 ν_i 两次：`E exp[it_n(ν_i-ν_i)]=1`，而不是 `|φ_i[n]|²`。该路径的条件自项甚至在不积分 ν_i 时就满足

\[
S_{ii}\operatorname{tr}(D_{\nu_i}L_iML_i^HD_{\nu_i}^H)
=S_{ii}\operatorname{tr}M. \tag{9}
\]

它与 ν_i 无关。利用 (8) 中有关 i 的两个共轭交叉项，定义

\[
a_i[n]=m_i s_i[n]\overline{Y_n}
-\sum_{j\ne i}S_{ij}R_{ij}[n]\overline{\phi_j[n]}. \tag{10}
\]

精确连续坐标更新为

\[
\boxed{q_i^*(u)=Z_i^{-1}\pi_i(u)
\exp\left\{\frac{2}{\sigma^2}\Re\sum_{n=0}^{N-1}a_i[n]e^{it_nu}\right\}.} \tag{11}
\]

Z_i 在原声明支持上积分。`n=0` 是常数，可在数值求归一化时消去。似然指数是实值有限 Fourier 多项式，具有周期 N 个 Doppler bin，最小周期可因活跃谐波而更小；这不意味着把实际有界实区间的两端认作同一点。一般包含多个谐波，不等于一个标准 von Mises 分布。

若 π_i 的 log-density 不是 Fourier 多项式，则整个 log q_i 还包含非多项式的 log π_i；“有限 Fourier”描述的是精确似然项。若原先验是路径相关或 h–ν 相关，还须加入相应 `E log p` 项，不能仍称 (11) 是整个原模型的精确更新。

一次冻结 q(d)、q(h) 的全路径系数预处理需 `O(N log N+NP²)`。顺序更新 q_i 后，`Δφ_i` 对其余 a_j 的影响可按 (10) 逐路径对增量更新，整个 ν sweep 仍是 `O(NP²)` 的交叉收缩，加上所有积分/矩计算成本。可存所有 R_ij 用 `O(NP²)` 内存，也可用 (7) 流式重建，只存 s_i、φ_i、a_i 和 P×P 增益矩，基本工作内存为 `O(NP+P²+N)`。

### 5. 连续积分与正权求积：保持概率合法，不免费保证精度

对 π_i 连续部分，可在其支持取正权节点 `(u_q,w_q)`，形成

\[
\omega_q\propto w_q\pi_i(u_q)
\exp\{(2/\sigma^2)\Re\sum_n a_i[n]e^{it_nu_q}\},\quad
\widehat\phi_i[n]=\sum_q\omega_qe^{it_nu_q},\quad \sum_q\omega_q=1. \tag{12}
\]

若原先验在 clipping 边界有原子质量，必须把原子按其质量单独加入，不能用连续密度积分默默删除。正归一化权使 `φ_i[0]=1`、`|φ_i[n]|≤1`，也使完整 difference-characteristic 核为 PSD；同一路径的自项仍必须按 (9) 精确保留，不能改成两个独立求积副本。

直接算 Q_i 个节点的指数及 N 个矩均为 `O(NQ_i)`，全路径为 `O(N Σ_i Q_i)`，不是已证明的 `O(NP)`。有限 Fourier 指数的指数函数通常有无限 Fourier 展开，不能由“指数里只有 N 项”推出有限节点精确积分。高集中度、多峰、端点及先验不连续会影响误差。FFT/NUFFT、递推或自适应求积可作为实现选择，但各自的网格、容差、节点数和额外成本在此未获得保证。

式 (11) 的精确连续更新有通常的坐标 ELBO 非下降性质。固定离散节点上的 (12) 可成为另一个离散变分模型的精确坐标更新；把它用作连续积分近似、特别是动态改变节点时，不自动继承原连续 ELBO 的单调性。

### 6. q(h) 的联合复高斯更新及其先验条件

令 B 的第 i 列为 `Dν_i L_i x`。定义

\[
\Gamma_{ij}=E[B_i^HB_j]=
\begin{cases}
\operatorname{tr}M,&i=j,\\
\sum_n\overline{\phi_i[n]}\phi_j[n]R_{ji}[n],&i\ne j,
\end{cases}\qquad
b_i=\sum_n\overline{\phi_i[n]s_i[n]}Y_n. \tag{13}
\]

Γ 是真正的期望 Gram，因此 Hermitian PSD，不是只用软均值构造的 `BbarᴴBbar`。由 (4) 的固定联合 Gaussian 先验，得到

\[
\boxed{C_{\rm new}=(C_0^{-1}+\Gamma/\sigma^2)^{-1},\qquad
m_{\rm new}=C_{\rm new}(C_0^{-1}m_0+b/\sigma^2).} \tag{14}
\]

更新后使用完整 `S=C_new+m_new m_newᴴ`，不能把跨路径 C_ij 删除后仍称它是联合 q(h) 更新。Γ 与 b 利用 (5)–(7) 计算，成本 `O(N log N+NP²)`；一般联合求解另需 `O(P³)`，存 C、Γ 需 `O(P²)`。这里的矩阵只有路径数 P 维，未构造 N×N H。

精确 Gaussian 坐标形式依赖 Gaussian gain prior 的共轭性。任意其他 p(h) 下，精确坐标密度是 `p(h) exp[-(hᴴΓh-2Re hᴴb)/σ²]`，一般不再 CN；强行投影到 CN 是新增近似。每次 (14) 都引用同一个原先验 `(m0,C0)`，不得把上一轮 `(m,C)` 作为新的独立先验重复乘同一个 y 的似然。

### 7. q(d_k) 与矩阵无关的期望 Gram

令 AF 信道 `H=Σ_i h_iU_i(ν_i)`，定义

\[
G=E[H^HH],\quad r=E[H^H]y,\quad
g_k=G_{kk},\quad e=r-G\bar x+\operatorname{diag}(G)\odot\mu.
\]

冻结其余数据因子时，QPSK 单坐标更新为

\[
\boxed{q_k^*(a)\propto\pi_k(a)
\exp\{[2\Re(\overline a e_k)-g_k|a|^2]/\sigma^2\},\quad a\in\mathcal Q.} \tag{15}
\]

这来自展开 `E||y-H(p+d)||²`，其中 `e_k=(r-Gp)_k-Σ_(j≠k)G_kj μ_j`。QPSK 的 `|a|²` 为常数，可从该坐标的归一化中删除，但 g_k 仍参与 e_k 的自贡献扣除。它是符号变分坐标势，不自动等于 BP/AMP 的校准消息或 LDPC 外信息。

令 `c_i[n]=(C_i)_nn`。利用独立 q(ν_i)，期望时间域 Gram 可精确作用于任意时间向量 z：

\[
G_tz=\sum_i S_{ii}z+
\sum_{i\ne j}S_{ji}\Pi_i^H
\left[\overline{c_i}\,c_j\,
\overline{\phi_i}\,\phi_j\odot(\Pi_jz)\right],
\quad G=A G_t A^H, \tag{16}
\]

\[
r=A\sum_i\overline{m_i}\Pi_i^H
\left[\overline{c_i}\,\overline{\phi_i}\odot Y\right]. \tag{17}
\]

乘法方括号内的各 n 向量逐点相乘。G matvec 用精确 CPP 移位/伴随原语，成本 `O(N log N+NP²)`；r 为 `O(N log N+NP)`。相同时延差的 shift-diagonal 项可以合并，但不预先假定 P² 项必能降为 P 项。

PSD 与同路径保能还有一个显式检查。记 `Wbar_i=diag(φ_i) C_i Π_i`，则

\[
G_t=\sum_{i,j}S_{ji}\bar W_i^H\bar W_j
+\sum_i S_{ii}(I-\bar W_i^H\bar W_i). \tag{18}
\]

第一项为带随机 h 的期望平方范数算子，第二项因 `|φ_i[n]|≤1` 为 PSD。直接用第一项而删去第二项，正是错误地把同一路径的两侧 ν 独立化，会低估对角能量。

diag(G) 同样不必逐列应用 G。令 `Δ_ij=l_j-l_i`，对 i≠j 定义

\[
\xi_{ij}=\frac{e^{2\pi ic_1(l_i^2-l_j^2)}}{N}
\sum_n\overline{\phi_i[n]}\phi_j[n]
e^{2\pi i(2c_1\Delta_{ij})n}.
\]

由 (6) 得

\[
\boxed{G_{kk}=\sum_iS_{ii}+
\sum_{i\ne j}S_{ji}\xi_{ij}e^{-2\pi i\Delta_{ij}k/N}.} \tag{19}
\]

先以 `Δ_ij mod N` 合并 P² 个系数，再一次 N 点 FFT 就给出全部对角元；构造 ξ 的成本 `O(NP²)`，FFT 为 `O(N log N)`。精确结果是实且非负，c2 在这个对角量中相消。它不表示完整 G 与 c2 无关。

**数据 sweep 的未解决成本/收敛边界**：一次 G xbar 和 diag(G) 可同时生成所有冻结其余因子的 (15) 候选值。但一次性同步写回是 Jacobi 更新，不自动是顺序 CAVI，也不自动保证 ELBO 非下降。真正逐符号更新时，前面符号改变后必须维护 `G xbar`；若每次重算 matvec，N 个坐标将花费 `O(N² log N+N²P²)`。本推导没有证明廉价的精确顺序 sweep，也没有把阻尼或并行固定点迭代的收敛当成已解决。选择单符号、分块或并行更新后，完整成本必须按实际执行重算。

### 8. 先验、获取中心、生产支撑及可证伪边界

- **生产增益先验不是 (4)**：已审计规则为 `h=g/sqrt(gᴴR_G0(ν,l)g)`，G1 原样复用该 h。联合先验支撑在 `hᴴR_G0(ν,l)h=1`。通常对每个 ν，这是一张低维曲面；非退化 CN q(h) 对其赋概率零，故独立 CN×q(ν) 相对于该原生产联合先验通常不是绝对连续，反向 KL 为无穷。不能声称 (11)/(14) 是该生产先验的精确 VB 更新。需要另行声明独立 Gaussian 工作先验，或改变潜变量/变分支撑；本文件不替用户决定。
- **真实 Doppler 先验**：UWA 速度、接受/裁剪机制及几何耦合不等于独立均匀分布；裁剪还可产生端点原子。对一般原联合先验，坐标指数需加 `E_(q_-i) log p(h,ν,l)`，其 dependence 不一定有限 Fourier，也不保证 q(h) 共轭。
- **获取中心不是新观测**：可把 `ν_i=νbar_i+δ_i` 作为纯坐标变换，把 `exp(it_nνbar_i)` 吸收进 s_i/相位，并同步平移同一个原支持与先验。νbar 来自同一个 y 时，可以是初始化；若据此只留下窄窗口，就限制了数据依赖的搜索/变分族，不能伪称该窗口本来就是独立先验。固定 l 和路径槽也须标明来自已授权的观测获取、原先验或真值诊断；本公式不自动赋予正确支持。
- **单径检查**：P=1 时，(11) 不直接含 C_ii 或 V，因为其自项全为常数。进一步限定 l₁=0，若 q(d) 均匀且 `p=cAe0`，则 s 只在 n=0 非零，(11) 返回原 ν 先验。此前完整有限 QPSK 边缘似然对该例有正信息，并不意味着当前 mean-field 坐标已经提取了该信息；后续数据学习是否能打破退化未获保证。
- **零增益均值初始化检查**：若 m=0 且 C 对角，则所有 a_i=0，ν 更新保持先验。跨路径 C_ij 与增益均值是实际更新内容，不应以“有方差所以有几何信息”替代 (10)。
- **点几何检查**：φ_i[n]=exp(it_nν_i) 时，同路径修正 (18) 的第二项为零，所有期望算子退化为点几何下含联合增益二阶矩的精确算子；再令 C=0 即恢复确定信道的 HᴴH。
- **编码约束**：若原数据先验是硬 LDPC 码字集合，普通独立 q_k 通常给非法码字正概率，反向 KL 同样可能无穷。本笔记的 (4)/(15) 是声明的未编码或独立符号工作先验切片。正式 LDPC 因子图/外信息接口需另行推导，不能把同一 y 产生的 decoder posterior 当作额外独立观测或重复先验。

### 9. 文献重叠与本推导尚未证明的差异价值

[arXiv:2607.17001v1，Off-grid Variational Bayesian Parameter Estimation for Fractional Delay-Doppler OTFS-ISAC](https://arxiv.org/abs/2607.17001)：已读保存文本的 mean-field 坐标规则 (9)、steering 指数 (14) 和 VM 近似 (15)。文本约 `:1806` 明说 “To obtain a tractable circular approximation”，随后 `q≈VM`；因此“连续参数后验 + steering 期望 + VB”已有直接 antecedent，不能声称首创。式 (11) 保留完整多谐波实区间因子，不能反向把该文单 VM 近似说成这里的普遍精确闭式。

[arXiv:2607.18881v1，AFDM SP 数据辅助 D-GESBL / D-GAMP-GESBL](https://arxiv.org/abs/2607.18881)：已读保存文本 `:118`–`:120`、`:254`–`:260`、`:3185` 后的层次 Gaussian prior、`:3404` 后的 residual equivalent-Gaussian approximation，以及 `:3611` 后的一阶 Taylor/EM/grid evolution。AFDM + SP + 数据反馈 + off-grid Bayesian + 低成本消息传递的宽泛组合已被覆盖。此处保留原始 SP 平方误差、QPSK 的 q 均值/方差和精确 CPP 相位；是否形成实用且有新意的差异，不能从这些恒等式推出。

本推导确定的是一个可核查的条件公式链：原始似然 → 精确 CPP 交叉矩 → qν 的多谐波指数 → Gaussian 工作先验下 qh → qd 所需期望 Gram。它没有验证积分精度、并行数据更新、支持获取、先验适配、局部极值、收敛、BER/FER、校准或完整时间成本。现有 TimePathOps、variable projection、scalar P-BiG-AMP 和完整物理 F1 均须作为既有资产保留，不能以重写这些原语作为创新结论。

## Caveats / Not Found

- 本文件只做解析与静态核对；无数值恒等式测试、接收机实现、科学运行或外部独立 proof check。
- `O(N log N+NP²)` 是指定冻结因子下的系数/矩收缩与单次 Gram matvec 成本，不能省略 `O(P³)` 联合增益求解、`O(NΣQ_i)` 求积、数据调度和全部迭代次数。
- 对原始生产归一化先验和硬 LDPC 先验，直接 CN×独立符号 mean-field 存在支撑/KL 障碍；条件公式不构成其精确后验算法。
- 未证明历史新颖性、完整性能成本优势或能完成主任务的生产收益目标。
