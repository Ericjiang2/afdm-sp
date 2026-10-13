# Research: SP、连续分数多普勒与有限星座的信息几何

- Query: 在真实 CPP 单径模型中，导频响应退化是否等价于完整观测律退化？有限 QPSK 能否严格打破高斯化数据的退化？时域 chirp 的时延–多普勒混淆是否落在实际支持内，是否适用于实际 AF 域 ZC 导频？
- Scope: internal mathematical research；外部文献只记录主会话给出的待核对线索。
- Date: 2026-10-07
- Authority: `.trellis/tasks/10-05-method-advantage` 紧凑交接；本文件为唯一写入目标。未运行仿真、RNG、服务器任务、实现或 Git 操作。

## Findings

结论有两个必须同时保留的部分。单径、未编码 iid QPSK 下，完整观测律确实比“同协方差的高斯化数据”具有更小的等价类，且存在真实 CPP 模型内、连续多普勒的严格零信息/正信息分离反例。但是，实际 root-7 ZC 加实际非零 c2 并不具有该反例的导频退化：其时域幅度无非零循环时移周期，因此不同整数时延的导频响应不可能共线。该反例不能充当当前 ZC 的现实性能痛点证据。

### 1. 文件、约定与适用边界

下文路径缩写只用于引用，完整前缀如下：

- `P = experiments/sp_afdm_frozen_20260920/src/physical.py`：精确 CPP 单径算子、连续多普勒导数和 Dirichlet 系数。
- `U = experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/`。
- `E = U/afdm_sp_joint_unrolled/afdm_env.py`：实际 ZC 及 chirp 参数、连续物理多普勒截断。
- `B = U/afdm_sp_joint_unrolled/budgeted_support_eval.py`：数据与 SP 导频构造。
- `C = U/afdm_sp_joint_unrolled/loop9_cache_features.py`：当前系统配置。
- `F = U/run_frozen_i1_smoke.py`：冻结 N、时延和多普勒支持。

代码证据：

- `P:20`、`P:109` 实现延迟、CPP 边界相位、连续时间调制后 DAFT；`P:87` 给出正 chirp DAFT 约定。
- `P:103` 的 Doppler 导数在时域逐点乘 `2π i n/N`，没有分数时延模型。
- `P:77` 给出每条精确 AF 对角线的 Dirichlet 系数；只有整数有效位移时才是单条对角线。
- `E:129`–`E:131`：root `r=7`，`zc[k]=exp(-iπ r k²/N)`。
- `E:203`–`E:205`：`c1=(2k′+1)/(2Nd_min)`，`c2=(sqrt(2)-1)/(2N²)`。
- `B:114`–`B:128`：`pilot=sqrt(rho)*zc`；默认数据经 LDPC，只有显式 `uncoded=True` 切片才是本笔记的 iid QPSK。
- `C:57`–`C:74` 与 `F:105`–`F:121`：实际 `N=1024`、`l_max=102`、`k_max=2`、`c1=5/(2N)`、`rho=.5`。
- `E:549`–`E:554`：连续物理多普勒裁到 `[-2,2]`。`P:55` 的拟合搜索范围 `[-3,3]` 不能替代真实支持。
- 增益来源按 `experiments/afdm_shared_channel_20261004/PRODUCTION_PRIOR.md:25`–`:34`：G0 先对局部 Dirichlet 权重归一化、裁剪及剪枝，再以 G0 矩阵 Frobenius 范数缩放物理增益；G1 必须复用这些物理增益，规则为 `reuse_g0_physical_gains_without_rescaling`。`U/afdm_sp_joint_unrolled/supplement_g1.py:14`、`:76`–`:85` 直接确认该规则。本笔记引用 `P` 核对路径算子，不以 `src/run_local.py` 这一单独本地研究入口作为生产观测或增益归一化的权威。

取单位酉 DFT `F_N`，定义

\[
A=\Lambda_2F_N\Lambda_1,\quad
\Lambda_j[n,n]=e^{2\pi i c_j n^2},\quad
D_\nu[n,n]=e^{2\pi i\nu n/N},\quad
(\Pi_l s)_n=s_{(n-l)\bmod N}.
\]

真实 CPP 为

\[
C_l[n,n]=\begin{cases}
e^{2\pi i c_1[N^2+2N(n-l)]},&n<l,\\
1,&n\ge l,
\end{cases}\qquad U_{l,\nu}=A D_\nu C_l\Pi_l A^H.
\]

每个单径 `U` 都是酉算子，包括任意实数 ν。多径和 `Σ h_j U_j` 一般不是酉算子。

研究切片为

\[
Y=hU_\theta(p+d)+w,\qquad
p\ne0,\ h\ne0,\quad w\sim\mathcal{CN}(0,\sigma_w^2 I),\ \sigma_w^2>0.
\]

所有噪声、数据、必要时的随机增益互相独立。`l` 是整数、ν 是连续实数；不对 l 求导。除第 5 节外，h 是未知确定参数，不偷偷边缘化；自由确定增益不是上述依赖 G0 几何和归一化的生产增益先验。QPSK 使用 `sqrt(P_d/2){±1±i}`，`P_d>0`，坐标 iid 均匀；换成另一固定整体旋转不改变以下群结论。

### 2. 高斯化数据：只有导频响应与增益幅度

若 `d~CN(0,P_d I)`，单径酉性直接给出

\[
Y\mid\theta,h\sim\mathcal{CN}\left(hq_\theta,
 s_h I\right),\quad q_\theta=U_\theta p,\quad
s_h=|h|^2P_d+\sigma_w^2. \tag{G1}
\]

两组参数的观测律相同，当且仅当均值和协方差相同。因为 `||qθ||=||p||>0`，均值相同已迫使 `|h0|=|h1|`，所以这里可简化为

\[
\mathcal L_G(Y;\theta_0,h_0)=\mathcal L_G(Y;\theta_1,h_1)
\iff h_0q_0=h_1q_1. \tag{G2}
\]

- **相同固定 h**：要求 `q0=q1`，只共线不够。
- **允许未知 h 随假设重拟合**：要求 `q1=e^{iα}q0`，并取 `h1=e^{-iα}h0`。该比例的模必须为 1。
- 该结论不能直接用于多径：高斯数据的协方差变成 `P_d H H^H+σw²I`，仍可能携带导频均值以外的信息。

### 3. 有限 QPSK：精确等价群及真实配置的无混淆结论

记 `S=Q^N`。高斯卷积的特征函数处处非零，因此可消去 w。各星座点等权且单径映射可逆，故

\[
\mathcal L_Q(Y;\theta_0,h_0)=\mathcal L_Q(Y;\theta_1,h_1)
\iff h_0U_0(p+S)=h_1U_1(p+S). \tag{Q1}
\]

取均值、中心化协方差，再令

\[
V=(h_1/h_0)U_0^HU_1,
\]

得到精确充要条件

\[
|h_1|=|h_0|,\qquad Vp=p,\qquad VS=S. \tag{Q2}
\]

其中

\[
VS=S\iff V=P\operatorname{diag}(\zeta_1,\ldots,\zeta_N),
\quad \zeta_j\in\{1,i,-1,-i\}, \tag{Q3}
\]

P 是置换矩阵。证明不需要假设整数多普勒：对 V 的任一单位范数行 v，iid proper QPSK 满足

\[
\mathbb E|v d|^4=P_d^2\left(2-\sum_j|v_j|^4\right).
\]

输出仍为 QPSK 则该值为 `P_d²`，故 `Σ|vj|⁴=1`。结合 `Σ|vj|²=1`，该行只有一个非零项，且模为 1。酉性给出置换结构，单坐标星座不变又把相位限定为 C4。反向显然成立。非单项式混合可由四阶幅度矩区分；单项式但非 C4 的相位则可由非零复四阶矩区分。

一般 p 的这个有限群稳定子是平凡的：每个非恒等群元素的固定点是一个真复线性子空间，有限并集为零测集。**实际 ZC 是结构化 p，不能引用该一般位置结论。**例如 N 为偶数时 `p[N-k]=p[k]`，ZC 本身就有非平凡置换稳定子；真正要检查的是物理相对算子是否落进稳定子。

#### 命题 Q4：实际参数支持内，单径完整 QPSK 律没有不同物理参数的精确混淆

在 `N=1024,c1=5/(2N),c2=(sqrt2-1)/(2N²)`、`0≤l≤102`、`|ν|≤2` 下，对任意非零已知 p，(Q1) 只在 `θ0=θ1,h0=h1` 时成立。

证明：这里 CPP 相位确实简化为

\[
c_1[N^2+2N(n-l)]=5N/2+5(n-l)\in\mathbb Z.
\]

这是从真实 CPP 参数推出的特例，不是把 CPP 任意换成 CP。又因 Λ1 的整数样本延拓具有 N 周期，定义

\[
T_t=F_ND_tF_N^H,\qquad R_l[k,k]=e^{-2\pi ikl/N},
\]

即可逐项验证

\[
U_{l,\nu}=e^{-2\pi ic_1l^2}\Lambda_2T_{\nu+5l}R_l\Lambda_2^H.
\]

所以相对算子除全局相位外为

\[
U_0^HU_1\doteq
\Lambda_2R_{l_0}^H T_{\Delta\nu+5\Delta l}R_{l_1}\Lambda_2^H. \tag{Q4a}
\]

若 `Δν` 非整数，`T` 每个元素都是非零 Dirichlet 值，故整个相对算子稠密，不能属于 (Q3)。若 `Δν` 为整数，令 `m=Δν+5Δl`。不同 θ 下必有 `m≠0`，因为 `|Δν|≤4<5`；且 `|m|≤514<N`。相对算子虽然是单项式，但在没有 wrap 的两个相邻列上，系数之比为

\[
\exp\{2\pi i b\},\qquad b=2c_2m-\Delta l/N. \tag{Q4b}
\]

至少有两个这样的列，因为 `N-|m|≥510`。若 `Δl=0`，则 `m≠0` 给出 `b≠0`。若 `Δl≠0`，

\[
|2c_2m|\le\frac{(\sqrt2-1)(5|\Delta l|+4)}{N^2}
<\frac{|\Delta l|}{N},
\]

所以仍有 `b≠0`；同时 `|b|<1/4`。因此该比值不在 C4，全局增益相位也不能修正它。(Q2) 被排除。若 θ 相同，`Vp=p≠0` 又迫使 `h1=h0`。证毕。

这只是**有限噪声下观测分布的精确可辨识性**，不保证参数距离、有限样本误差率、数值稳定性、优化可达性或收益大小；低 SNR 下相异分布仍可极接近。实际默认 LDPC 数据和多径不在证明范围内。

### 4. 局部信息：固定整数 l 的连续 ν

令 `q=Uνp`、`q′=∂νUνp`、`E_p=||p||²`。酉性给出 `Re(qᴴq′)=0`。对高斯模型同时消去未知复增益的两个实方向，可得精确有效 Fisher 信息

\[
J_{G,\nu\mid h}=\frac{2|h|^2}{s_h}
\left\|P_q^\perp q'\right\|^2,
\qquad P_q^\perp=I-qq^H/E_p. \tag{L1}
\]

原因是 q′ 的 q 方向为纯相位方向，由增益相位消去；剩余分量与增益幅度方向正交。高斯协方差只随增益幅度变，不给 ν 增加一个协方差项。若 h 已知，则不投影，信息为 `2|h|²||q′||²/s_h`。

置 `z=Dν C_l Π_l Aᴴp`，有 `q′=A diag(2π i n/N)z`。于是

\[
\|P_q^\perp q'\|^2
=E_p(2\pi/N)^2\operatorname{Var}_{\omega}(n),
\qquad \omega_n=|z_n|^2/E_p. \tag{L2}
\]

因此高斯有效信息为零，当且仅当延迟后的时域导频只占一个采样点。恒模时域 chirp 的该方差反而为 `(N²−1)/12>0`。**不同离散 l 的全局混淆，不等于固定 l 的局部 ν 信息为零。**

有限 QPSK 还有一个严格的局部结论：对 N≥2、h≠0、有限正噪声，精确完整 QPSK 似然在消去复 h 后对 ν 的有效 Fisher 信息严格为正，即使 (L1) 为零。

证明要点：精确密度是同方差高斯的有限混合，中心为 `m_a=hU(p+a)`，各中心互异。若某个联合方向 `(ν′=1,h′=g)` 的密度导数为零，去卷积后得到有限个不同点处的 δ 分布一阶导数之和为零。使用分别支撑于各点附近的测试函数，迫使每个中心速度都为零：

\[
(hU'+gU)(p+a)=0\quad\forall a\in S.
\]

星座差向量张成全部实 `2N` 维空间，故 `hU′+gU=0`。这要求 `UᴴU′` 是标量阵。然而真实连续多普勒的 `UᴴU′` 酉相似于 `diag(2π i n/N)`，N≥2 时不是标量阵，矛盾。有限混合正密度保证“Fisher 范数为零”与该导数为零等价；增益 nuisance 空间有限维且闭，故有效 Fisher 信息严格正。

这也补全了 `TANGENT_INFORMATION.md` 第 3 节的零下界边界：其精确 QPSK 矩下界恰为 (L1) 右侧；时域单点导频使这个下界为零，但上述有限混合切线论证仍给出完整有限 QPSK 有效 Fisher 信息严格正。它无需给接收机已知数据，也不把下界当成信息真值。该证明没有给出实用的正下界，也没有证明任意非高斯化近似、更低阶统计量、有限搜索或实际接收机能保留这些信息。

#### 可证伪的连续多普勒分离反例

取任意合法 A、`l=0`、`p=c A e_0`，其中 c≠0。它是非零 AF 域 SP 导频，且每个 AF 分量都非零，但时域导频为单点：

\[
U_{0,\nu}p=cA D_\nu e_0=p\quad\forall\nu.
\]

所以即使固定同一个 h，高斯化数据的观测律对 ν 完全相同。取 `ν0=0,ν1=1/2`，均在实际支持内，则

\[
U_0^HU_1=A D_{1/2}A^H
=\Lambda_2F_ND_{1/2}F_N^H\Lambda_2^H
\]

稠密，违反 (Q3)，有限 QPSK 律不同；由上述切线证明，其局部有效信息也严格正。这是 SP + 真正分数多普勒的严格存在性反例，**不是实际 ZC，也不是推荐导频**；导频时域集中还带来另外的峰均功率问题，本笔记不做设计选择。

### 5. 固定 h 与边缘化增益不可混淆

若 H 是共同指定的圆对称先验，且 `0<E|H|²<∞`，Gaussian 数据模型下边缘观测律相同的充要条件为 `q1=e^{iα}q0`：

- 充分性：耦合 `H1=e^{-iα}H0`，先验不变，(G1) 的条件律逐项相同。
- 必要性：边缘均值为零，二阶矩是 `E|H|²(qqᴴ+P_d I)+σw²I`；相同二阶矩要求 `q0q0ᴴ=q1q1ᴴ`。

非圆对称先验不一定允许该相位耦合。没有指定先验时，不作“边缘化 h 后仍然…”的断言。

对于 QPSK，先验保持的同一个条件耦合仍然是充分条件，但 (Q2) 的必要性不能直接穿过积分。举例：若 `H=r e^{iΦ}`，r>0 固定且 Φ 均匀，则去掉噪声后精确等价条件是有限多重集

\[
\left\{\operatorname{Orb}_{U(1)}\big(rU(p+a)\big):a\in S\right\}
\]

相同，须保留轨道长度/半径与重复权重，零向量单独视为零轨道。它允许不同星座点使用不同的相位匹配，比一个全局 V 的条件更宽。该条件来自互不相交圆轨道上的 Haar 测度，不是把圆对称 H 当作已知 h。

对任何具有有限非零二阶矩的圆对称 H，QPSK 边缘律相同仍必需 `q0q0ᴴ=q1q1ᴴ`，因为 QPSK 与高斯数据共享该二阶矩。因此下一节实际 ZC 的“不同 l 不共线”也排除这种先验下的跨时延边缘等价；但命题 Q4 的完整确定增益无混淆结论不自动整体移植到任意增益先验。

### 6. 时域 chirp 混淆：先检查 CPP，再检查支持，再检查实际 ZC

#### 6.1 CPP 相容性及支持条件

假设时域导频确实是 `s_n=c exp[2π i(a n²+b n)]`，c≠0。对 `x=n-l<0`，CPP 接上的样本与未取模 chirp `s_x` 的比为

\[
\exp\{2\pi i[(a+c_1)(2Nx+N^2)+bN]\}.
\]

因此下列是对所有整数边界样本有效的充分相容条件：

\[
2N(a+c_1)\in\mathbb Z,\qquad
(a+c_1)N^2+bN\in\mathbb Z. \tag{C1}
\]

若不满足，不能把有限窗 CPP 移位直接改写为无限 chirp 移位。满足时，精确导频响应在 DAFT 前为

\[
D_\nu C_l\Pi_ls
=e^{2\pi i(a l^2-b l)}s_n
 e^{2\pi i(\nu-2Na l)n/N}. \tag{C2}
\]

因为 s 所有样本非零，两个响应共线的充要条件是

\[
\Delta\nu-2Na\Delta l\in N\mathbb Z. \tag{C3}
\]

全局相位由 h 吸收；若 h 要保持同一个固定值，还必须检查 (C2) 的全局相位相同。若 `|ν|≤K,0≤l≤L`，存在跨时延混淆恰要求某个 `1≤|Δl|≤L` 满足

\[
\operatorname{dist}(2Na\Delta l,N\mathbb Z)\le2K. \tag{C4}
\]

**真实支持内既有无混淆例，也有混淆例**：

- 实际 `N=1024,c1=5/(2N)`，取 `a=-c1,b=0`。相容性成立，斜率 `2Na=-5`。对 `1≤|Δl|≤102`，`dist(5Δl,NZ)≥5>4`，故 `|ν|≤2` 内没有跨时延混淆。拟合搜索 `[-3,3]` 则会包含间隔 5 的例子，不能把它伪称为真实支持内混淆。
- 同一物理配置取 `a=1/(2N),b=0`，也满足 (C1)。路径 `(l0,ν0)=(0,-1/2)` 与 `(l1,ν1)=(1,+1/2)` 有相同有效频率，响应只差 `exp(iπ/N)`，未知 h 可补偿；两条物理多普勒均为分数且位于真实支持。命题 Q4 又保证，完整 iid QPSK 律不会随这个导频混淆一起退化。

#### 6.2 实际 AF 域 root-7 ZC 不属于该时域 chirp 退化

实际导频为 `p_k=c exp(-iπ7 k²/N)`，而非指定的时域 chirp。令

\[
\eta=\sqrt2-1,\qquad a_*=7+\eta/N,\qquad
z_k=(\Lambda_2^Hp)_k/c=e^{-i\pi a_*k^2/N}.
\]

时域导频 `s=Aᴴp=c Λ1ᴴF_Nᴴz`。因此 `|s_n/c|²=|(F_Nᴴz)_n|²`。考察 z 的一阶循环相关

\[
C_1^{(z)}=\sum_{k=0}^{N-1}z_{(k+1)\bmod N}\overline{z_k}.
\]

设 `v_k=exp[-iπ a_*(2k+1)/N]`，`G=Σ_{k=0}^{N-1}v_k`。准确处理末端 wrap 项后

\[
C_1^{(z)}=G+v_{N-1}(e^{i\pi a_*N}-1),\qquad
|G|=\frac{\sin(\pi\eta/N)}{\sin(\pi a_*/N)}.
\]

对 `N=1024`，`7N` 为偶数，故 `e^{iπa_*N}=e^{iπη}`。用 `2/5<η<1/2`、`sin x≤x` 及 `sin x≥2x/π (0≤x≤π/2)` 可得

\[
|G|\le\frac{\pi\eta}{2a_*}<\frac\pi{28}<1,
\qquad |e^{i\pi\eta}-1|=2\sin(\pi\eta/2)>1.
\]

反三角不等式因此严格给出 `C1^(z)≠0`。循环相关等于时域幅度平方的傅里叶系数（符号依 DFT 方向，非零性不变），所以 `|s|²` 的第一非零频率系数非零。若 `|s|²` 具有整数周期 `Δl`，该系数要求 `exp(2π i Δl/N)=1`。于是没有 `0<|Δl|<N` 的幅度周期。

任意两条单径导频响应共线，都必需

\[
|s_{(n-l_0)\bmod N}|=|s_{(n-l_1)\bmod N}|\quad\forall n,
\]

因为多普勒与 CPP 都只改变相位。因此实际 ZC 下 **不同整数 l 的导频响应不可能共线，任意 ν 都不能补偿这个幅度差异**。上述结论同时说明实际逆 DAFT 导频不是恒模时域 chirp。

另外，该时域导频不可能只占一个样本：否则 z 必是纯线性相位序列，而其相邻比 `exp[-iπa_*(2k+1)/N]` 随 k 改变。这结合 (L2) 给出实际 ZC 在固定 l 下的 Gaussian 有效 Doppler Fisher 信息严格正。

这里未给出实际 ZC 的定量最小模糊度、最小信息、所有同 l 远距离 Doppler 假设的分离界或误差性能。完整支持内有限 QPSK 确定增益无混淆已有 Q4，但实际 ZC 的 Gaussian 情况在本节只证明“无跨时延精确混淆”和“固定 l 局部信息为正”。

### 7. 已知工具重叠、与相邻机制的关系及可用结论

上述 Gaussian 化、有限混合可辨识性、QPSK 四阶矩对称、消 nuisance 的 Fisher 投影均是标准工具。不能把这些本身包装成 AFDM 新算法。单径酉模型下，精确未编码 QPSK 似然还可写为

\[
\log f(y;\theta,h)=\text{const}+\sum_{j=1}^N\log\left[
\frac14\sum_{a\in Q}\exp\left(-\frac{|(U_\theta^Hy)_j-h(p_j+a)|^2}{\sigma_w^2}\right)
\right].
\]

候选 U 的应用可用现有 DAFT/移位/调制实现；这属于传统有限星座边缘似然。它没有解决多径的非酉性、编码依赖、未知路径数、优化及端到端总成本问题。

主会话并行分析的另一个机制是“保留某一点算子值，不等于保留该点的连续参数导数”：单条整数对角线截断可在 ν=0 精确，却把附近变化压进未知复增益。它与本笔记的导频均值等价类不同；现有 `P:103` 已有完整真实导数，不能把恢复该导数单独宣称为新方法。本文件不重复相邻机制的截断信息计算。

对 `TANGENT_INFORMATION.md` 的独立解析复核（2026-10-07；未修改该文件）：第 3 节把 proper 复观测转为实协方差 `vI/2`，再对任意 gain-score 线性组合应用协方差 Cauchy–Schwarz；逐点不等式之后分别取 nuisance 下确界，确实得到其式 (1)，因子 2 与最小化顺序均正确。第 6 节的对称五槽 central-only 阈值式 (6) 也成立。但审读版本第 177–180 行的最大旁瓣方向需修正：`E:435` 实际使用 `x=m+kappa`，所以 G0 的最大旁瓣在 `m=-sign(delta)`；`+sign(delta)` 属于精确 Fourier 展开 `D_N(delta-m)` 的约定。对称保留集合使最大幅度比及阈值不受该符号修正影响。阈值边界的严格 `<` 确实保留等于阈值的槽，但前提是该槽未先被 `k_cap` 裁剪；源代码的裁剪在 `E:605`，阈值判断在 `E:607`。一径 G0 的末次 Frobenius 归一化使唯一有效系数模为 1，均匀初始相位使其 gain-marginal 律与 delta 无关，这在固定整数 l 与 base 槽、只边缘化增益的条件下成立；不能把它改写成 G1 的物理增益恒模，因为 G1 复用的是 `E:641` 中 G0 缩放后的物理增益。

外部文献线索（由主会话提供，本研究者未独立打开或完成新颖性审计）：

- [Oversampled Low Ambiguity Zone Sequences for Channel Estimation over Doubly Selective Channels](https://arxiv.org/abs/2409.17707)：低模糊区序列直接相关，通用低模糊导频设计不能视为空白。
- [AFDM-Enabled ISAC: Theoretical Framework and Pilot Design，JSAC 2026](https://www.southampton.ac.uk/~sqc/listP/JSAC2026AFDM.pdf)：标题及链接按主会话交接记录，版本/细节待主会话审查。
- [arXiv:2609.16691](https://arxiv.org/abs/2609.16691)：主会话标注为 pilot + data ambiguity 相关；本文件不据此作优先权判断。

相关内部材料：`.trellis/tasks/10-05-method-advantage/research/20261007-performance/STRUCTURE_NOTE.md` 已读，约束同一物理前缀与有限 QPSK 不变性边界。旧整数盲问题的逐坐标四次幂充分性不适用于此处一般稠密 fractional mixing 和非零 p。没有重载实现/检查 manifests，也没有声称读过未提供的项目规范。

## Caveats / Not Found

- 本文件是解析推导及静态源码核对；没有数值仿真、运行验证、外部独立证明检查或生产效益证据。
- 证明适用于单径、完整真实 CPP 算子、未编码 iid QPSK。默认生产是多径加 LDPC，不可偷换。
- 对实际 ZC，已解析排除 cross-delay 导频共线；因此“利用有限星座修复当前 ZC 的这种精确退化”缺少问题前提。
- 定理中的理想 chirp 参数取源码指定数学常数；源码浮点三角函数会有舍入，未把理想等式当作 bitwise 数值测试结果。Q4 的相位比排除有宽裕的显式不等式，仍不代替实际数值精度审计。
- `h=0`、`P_d=0`、N=1、非独立数据、未知噪声/数据尺度、路径叠加、截断算子、以及不同增益先验都需要另行建模；本文件不作无条件外推。
- 只建立“哪些观测律能严格相同、何时局部信息为零”的机制界线；尚无新颖性、实际难度、算法优势、FER/BER 或完整成本收益主张。
