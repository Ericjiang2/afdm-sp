# Research: QPSK 完整盲分布的列 chirp 歧义与四次幂相位码设计

- Query: 一般 N 下，DAFT 列 chirp 如何控制完整 QPSK 盲分布的 character 歧义？第四次幂 CAZAC 能否给可量化的抗 alias 设计？
- Scope: internal / mathematical；仅解析与冻结源码读取，无科学运行、SSH、采样或生产波形修改。
- Date: 2026-10-06
- Active task: `.trellis/tasks/10-05-method-advantage`。
- Current plan: `.mission/20261006_20-14-46-afdm-phase-information/PLAN.md`；该目录 CSV 为本轮唯一执行状态，本文件不是新状态系统。
- Status: 既有主代数已由 Claude 全文审查通过；第 8 节新增相关器桥梁已完成解析自查，由主线程纳入最终审查。经典工具及 CAZAC 本身不主张新颖；AFDM 适配的实际收益与技术差异由主线程另行验证。

## Findings

固定各时间坐标均非零的 H 后，完整 QPSK 盲分布的剩余歧义可精确刻画。对于已由 balanced 四阶限定的 `H′=a χ_r H`，完整分布相同当且仅当 `a v_{s−r mod N}/v_s∈C₄` 对所有 s 成立。对二次 chirp，该判据化为 `4c₂ g_r∈Z`：奇 N 时 `g_r=gcd(N,r)`，偶 N 时 `g_r=2gcd(N,r)`。

完整全纯四阶张量（4,0）的最佳公共相位分离度由四次幂码的循环自相关决定。平幅 |H_i|=1 时，**Frobenius 距离平方**恰为 `2N(1−|A_r|)`。偶 N 取 `c₂=1/(8N)`、奇 N 取 `c₂=1/(4N)`，均使全部 r≠0 的 A_r=0，从而达到这一平幅总体张量指标的 maximin 上界。现用 `c₂=.1/N²` 虽精确消除所有非零 character，但 r=1 的距离平方仅趋向常数 `(5+√5)/2`，不随 N 增长。

这些是固定 H 的总体可辨识性与分离度结论。未知幅度、深衰落、有限样本估计、物理候选资格和波形约束仍须显式处理；不能把最佳真值相位比较或 CAZAC 恒等式本身当成可部署收益。

### 1. Assumptions、冻结约定与待恢复对象

N≥2，所有循环下标取 Z_N 中的标准代表 0,…,N−1。观察为

\[
Y^{(t)}=\operatorname{diag}(H)US^{(t)}+n^{(t)},\qquad
n^{(t)}\sim\mathcal{CN}(0,\sigma^2I),
\tag{1}
\]

其中 H 固定，σ²≥0 有限且可未知，快照独立。S 的各坐标 iid 均匀取 `exp(iπ/4) C₄`，`C₄={1,i,−1,−i}`；源与噪声独立。本文件关于完整纤维的命题要求 H_i≠0 对全部 i 成立。

冻结 Python DAFT 的逆矩阵分解为

\[
U=R F^H C,\quad R_{ii}=e^{-2\pi i c_1i^2},\quad
C_{ss}=v_s=e^{-2\pi i c_2s^2},\quad
F_{is}=N^{-1/2}e^{-2\pi i is/N}.
\tag{2}
\]

使用 `Z=RᴴY` 去除已知行 chirp；它不改变噪声律或 Frobenius 距离。c₁ 在下述源端 phase-code 判据中消失，但这不等于 c₁ 对多径物理信道或 full-diversity 条件无关。

前轮 `BLIND_INVARIANTS.md` 已证：完整 balanced 四阶 cumulant 相同，当且仅当

\[
H'_i=a\chi_r(i)H_i,\qquad |a|=1,\quad
\chi_r(i)=e^{2\pi i ri/N},\quad r\in\mathbb Z_N.
\tag{3}
\]

其对角项给 `K_{iiii}=−|H_i|⁴/N`；与协方差合用还给 σ′²=σ²。因此本轮比较完整分布时，无需假定候选噪声方差已知或候选幅度预先相同，它们由相同分布强制相同。

### 2. Proposition A：完整 QPSK 盲分布的精确 character 条件

**命题。** 在第 1 节假设下，`(H,σ²)` 与 `(H′,σ′²)` 的完整观察律相同，当且仅当 σ′²=σ²，且存在满足 (3) 的 a,r，使

\[
a\frac{v_{s-r\bmod N}}{v_s}\in C_4
\quad\text{对全部 }s\in\mathbb Z_N.
\tag{4}
\]

**推导。** 定义循环置换 `(P_r z)_s=z_{s-r mod N}`。由 Fourier 约定，`diag(χ_r)Fᴴ=FᴴP_r`，故

\[
\operatorname{diag}(a\chi_rH)U
=\operatorname{diag}(H)U\,(aC^{-1}P_rC),
\qquad (aC^{-1}P_rCS)_s
=a\frac{v_{s-r}}{v_s}S_{s-r}.
\tag{5}
\]

若 (4) 成立，右边仅对 iid QPSK 坐标作置换及 C₄ 旋转，源的完整联合分布不变，因此信号加相同噪声的律相同。

反之，相同完整律先由前轮 balanced 四阶定理给 (3)，并由二阶给相同 σ²。Gaussian 卷积的实特征函数处处非零，可以消去相同噪声，得到两信号向量同分布。H_i≠0 与 U 酉使 `diag(H)U` 可逆，再用 (5) 得 `(aC⁻¹P_rCS)≡_d S`。逐坐标看，单位模因子 b 使 `b exp(iπ/4)C₄` 与原四点分布相同，当且仅当 b∈C₄。因此必须满足 (4)。证毕。

这一步不需要调用一般 ICA 唯一性，也没有把任意非 Gaussian 性当作充分条件。QPSK 四点支持与 balanced 四阶已确定的 monomial 结构共同给出必要性。r=0 时始终只剩 a∈C₄；任何 c₂ 都不能消除源本身的公共四象限对称。

### 3. Proposition B：二次 chirp 的整数 gcd 判据

对 1≤r≤N−1 定义整数

\[
d_s(r)=(s-r\bmod N)^2-s^2,\quad d_0=(N-r)^2,\quad
g_r=\gcd\{d_s-d_0:s=0,\ldots,N-1\}>0.
\tag{6}
\]

存在某个公共相位 a 使 (4) 成立，当且仅当

\[
4c_2(d_s-d_0)\in\mathbb Z\quad\forall s
\quad\Longleftrightarrow\quad 4c_2g_r\in\mathbb Z.
\tag{7}
\]

最后一个等价关系由整数 gcd 的 Bézout 表示给出，对实数 c₂ 也成立。通过判据时，全部允许公共相位恰为

\[
a=e^{2\pi i c_2d_0}\zeta,\qquad \zeta\in C_4.
\tag{8}
\]

为计算 g_r，把标准代表拆成两段：

\[
d_s-d_0=
\begin{cases}
2(N-r)s,&0\le s<r,\\
-\{r^2+(N-r)^2\}-2r(s-r),&r\le s<N.
\end{cases}
\tag{9}
\]

所以两段相邻差为 2(N−r)、−2r，段间基值为 `−[r²+(N−r)²]`。内部两段都非单点时直接得到

\[
g_r=\gcd(2r,2N,r^2+(N-r)^2)
=\gcd(2\gcd(N,r),N^2).
\tag{10}
\]

r=1 或 N−1 缺少的一段相邻差是另一差的整数倍，不改变 gcd；N=2,r=1 单独给差 −2，也满足 (10)。令 d=gcd(N,r)，由于 d|N，可得简式

\[
\boxed{g_r=
\begin{cases}
\gcd(N,r),&N\text{ 为奇数},\\
2\gcd(N,r),&N\text{ 为偶数}.
\end{cases}}
\tag{11}
\]

**有理与无理 c₂ 的完整分类。** 令 `ρ_N=4c₂`（奇 N）或 `ρ_N=8c₂`（偶 N）。若 ρ_N 无理，则所有非零 r 都被排除。若 `ρ_N=p/q` 已约分、q>0，则允许的非零 r 满足 `q|gcd(N,r)`：q|N 时正好是 q 的非零倍数；q∤N 时没有非零 r。这里描述的是 character 投影；相位 a 仍按 (8) 联动，不能未经证明称整个歧义群总为两个群的直积。

### 4. Proposition C：完整全纯四阶张量（4,0）与四次幂码自相关

定义完整全纯四阶张量（4,0）

\[
T(H)_{ijkl}=E[Z_iZ_jZ_kZ_l]
=-\frac{H_iH_jH_kH_l}{N^2}
\sum_{s=0}^{N-1}w_s e^{2\pi i(i+j+k+l)s/N},
\quad w_s=v_s^4.
\tag{12}
\]

因为 E[S²]=0、E[S⁴]=−1，且 proper Gaussian 的全纯四阶 cumulant 与伪协方差为零，这里全纯四阶矩等于 cumulant，未知 σ² 不改变总体 T。经验 T 仍有噪声方差，不能称为无噪观察。**本文距离只计这个（4,0）块，Frobenius 范数对全部有序 i,j,k,l 求和。** 若把共轭（0,4）块同时堆叠，距离平方会再乘 2；不能仍沿用本文单块常数。

定义四次幂码的归一化循环自相关

\[
A_r=\frac1N\sum_{s=0}^{N-1}w_{s-r}\bar w_s
=\frac1N\sum_s\left(\frac{v_{s-r}}{v_s}\right)^4.
\tag{13}
\]

**平幅精确式。** 若 |H_i|=1 对全部 i 成立，则

\[
\boxed{\min_{|a|=1}\|T(a\chi_rH)-T(H)\|_F^2
=2N(1-|A_r|).}
\tag{14}
\]

右侧是距离的**平方**，距离本身须取平方根。证明使用酉张量积：令 `D_H=diag(H)`、`W=Σ_s w_s e_s^{⊗4}`，则 `T(H)=−D_H^{⊗4}(Fᴴ)^{⊗4}W`。平幅时外侧为酉映射，所以 `‖T(H)‖²=N`，且

\[
\langle T(H),T(a\chi_rH)\rangle=a^4N A_r.
\tag{15}
\]

展开平方范数并对 a⁴ 的全部单位圆值优化即得 (14)。行 chirp 若未预先消去，只乘额外单位模张量因子，也不改变该距离。

**任意非零幅度的夹界。** 令 `h_min=min_i|H_i|>0`、`h_max=max_i|H_i|`。逐张量元素乘积的模平方落在 `[h_min⁸,h_max⁸]`，因此

\[
2N h_{\min}^8(1-|A_r|)
\le \min_{|a|=1}\|T(a\chi_rH)-T(H)\|_F^2
\le 2N h_{\max}^8(1-|A_r|).
\tag{16}
\]

下界先对每个 a 成立再取最小，上界取平幅问题的最优 a 即可。非平幅时最优 a 未必仍由 A_r 的相位给出；不能把 (14) 原样当成加权张量的精确式。

由单位圆三角等号，`|A_r|=1` 当且仅当全部 `(v_{s-r}/v_s)^4` 相同，恰对应 (7)。因此在 H_i≠0 时，balanced 四阶加全纯四阶已能分开全部完整分布不等价的 character 候选；这里不需要更高阶矩来补这一离散判别。

### 5. Proposition D：第四次幂 CAZAC 的奇偶 N 构造

考虑仅作为研究候选的两组 chirp：

\[
c_2^\star=
\begin{cases}
1/(8N),&N\text{ 为偶数},\\
1/(4N),&N\text{ 为奇数}.
\end{cases}
\tag{17}
\]

偶 N 时 `w_s=exp(−πi s²/N)`，该二次序列具有 N 周期，因为 `w_{s+N}/w_s=exp(−πi(2s+N))=1`。故可去掉 circular 下标的模运算而计算

\[
A_r=e^{-\pi i r^2/N}\frac1N\sum_s e^{2\pi i rs/N}=0,
\quad r\ne0.
\tag{18}
\]

奇 N 时 `w_s=exp(−2πi s²/N)` 也有 N 周期，且

\[
A_r=e^{-2\pi i r^2/N}\frac1N\sum_s e^{4\pi i rs/N}=0,
\quad r\ne0,
\tag{19}
\]

因为奇 N 下 2r≠0 mod N 对所有非零 r 成立。这两条是直接几何级数证明，无素数 N 假设；N=2 亦在偶分支内。

于是所有非零 character 的 (14) 都等于 2N。对任意单位模列码，(14) 至多 2N；构造同时达到全部非零 r 的这个上界，因此是**平幅、完整全纯四阶张量（4,0）、最佳公共相位商空间距离指标**的 maximin 最优设计。不能由此宣称它对非平幅加权距离、有限样本方差或端到端误码率也最优。

CAZAC 与二次相位码本身属于经典工具；本稿只给它们与特定 QPSK 盲分布 character 判据和张量距离的精确连接。是否构成足够的 AFDM 技术增量需另行查新与比较，不以已有 OFDM 先例自动淘汰适配价值。

### 6. 小扰动的确定性分离度保障

令 `c₂=c₂⋆+η`，η 为任意实数，包括任意小无理数。对每个 r，基准 A_r=0，而扰动使第 s 项乘 `exp(−8πiηd_s)`。由于 d_s 的和为零，且第一段 d_s>0、第二段 d_s<0，直接求和得到

\[
\frac1N\sum_s|d_s|=\frac{2r(N-r)(N-1)}N.
\tag{20}
\]

利用 `|exp(ix)−1|≤|x|`，

\[
|A_r(c_2^\star+\eta)|
\le\frac{16\pi|\eta|r(N-r)(N-1)}N
\le4\pi|\eta|N(N-1).
\tag{21}
\]

所以对 0<ε<1，只要 `|η|≤ε/[4πN(N−1)]`，全部非零 r 的平幅距离平方至少为 `2N(1−ε)`；任意非零 H 再乘 h_min⁸ 得下界。**已有全部 |A_r|<1 就足以排除非零 character，无需无理扰动；有理的未扰动 CAZAC 构造已满足这一点。** η 取无理数只是另一个可由 (7) 确认的充分选择，可能用于满足另外核对过的波形条件，不能写成消歧的必要条件。

这不是要求实际计算机“存储一个无理数”。有限精度实现必须对实际编码的 c₂ 及 A_r 检查分离余量，不能把声明无理当成精确安全证书。若某个经独立核对的 AFDM full-diversity 定理要求 c₂ 无理，本构造可兼容这一单一条件；本稿尚未核对其 c₁、delay/Doppler 支撑、码字差矩阵等其余前提，不能保证该候选满足 full diversity。

### 7. 现用 c₂=.1/N²：精确消歧但邻近 character 分离仅为常数量级

**精确无歧义。** 现用 c₂=1/(10N²)。奇 N 的 `ρ_N=2/(5N²)` 约分分母为 5N²；偶 N 的 `ρ_N=4/(5N²)` 分母为 5N²/4。对全部 N≥2 这些分母都大于 N，故按第 3 节没有非零 r 满足完整-law 相等条件。结论是精确代数可辨识，不是有限样本稳健性。

**r=1 的闭式。** 令 `β=4π/5`、`x=β/N²`、`L=N−1`。这时 `d₀=L²`、`d_s=1−2s`（1≤s≤L），几何级数给

\[
\begin{aligned}
A_1&=\frac1N\left\{e^{-ixL^2}
 +\sum_{s=1}^L e^{ix(2s-1)}\right\},\\
|A_1|&=\frac1N\left|R_N+e^{-i\beta(1-1/N)}\right|,
\qquad R_N=\frac{\sin(Lx)}{\sin x}>0.
\end{aligned}
\tag{22}
\]

这里相位 β 固定，小的 bulk 相位与单个 wrap 项不能一起当作一致的小角；漏掉 wrap 项会得到错误的 N 阶数。

把 `R_N=Σ_{s=1}^L cos(x(2s−1−L))`，使用 `0≤1−cos t≤t²/2`，有显式界

\[
0\le L-R_N\le\frac{x^2L(L^2-1)}6\le\frac{\beta^2}{6N}.
\tag{23}
\]

又 `|exp(−iβ(1−1/N))−exp(−iβ)|≤β/N`。N≥3 时，令 c=cosβ，则

\[
0\le|L+e^{-i\beta}|-(L+c)
=\frac{\sin^2\beta}{|L+e^{-i\beta}|+L+c}
\le\frac1{2(N-2)}.
\tag{24}
\]

合并得严格误差界

\[
\left|N(1-|A_1|)-(1-\cos\beta)\right|
\le\frac{\beta+\beta^2/6}{N}+\frac1{2(N-2)}.
\tag{25}
\]

因此 `1−|A₁|=Θ(N⁻¹)`，平幅问题的距离平方满足

\[
\min_{|a|=1}\|T(a\chi_1H)-T(H)\|_F^2
=2(1-\cos(4\pi/5))+O(N^{-1})
\longrightarrow\frac{5+\sqrt5}{2}.
\tag{26}
\]

这给出了严格量级而非数值曲线。当前码的最坏非零 r 分离度不超过 r=1 的常数量级；本稿未声称 r=1 对每个有限 N 都是最坏 r。CAZAC 构造的对应平幅距离平方为 2N，但从几何间距提升到有限样本算法收益仍需估计误差、计算预算与公平观察知识比较。

### 8. 最小相关器桥梁：真分数补偿条件下的单径研究模型

本节只处理明确的单径研究 use-case，采用正时序信道 `H_i=h exp(2πi(κ+r)i/N)`，h≠0 为未知复 gain、r∈Z_N 为整数偏移。**κ 必须是真实分数偏移，补偿须精确。** 它不是假设实际接收机已经无误估得 κ，也不把单径桥梁外推到旧 G0 双径或多 delay 模型。

令 `D_κ=diag(exp(2πiκi/N))`。对原始观察做已知行 chirp 去除、真实分数补偿及 Fourier 变换，得到

\[
X^{(t)}=FR^HD_{-\kappa}Y^{(t)}
=hP_rCS^{(t)}+\xi^{(t)},\qquad
X_s^{(t)}=h v_{s-r}S_{s-r}^{(t)}+\xi_s^{(t)}.
\tag{27}
\]

补偿与变换均为确定性酉算子，所以原独立 white proper Gaussian 噪声变为 iid `ξ_s^(t)~CN(0,σ²)`，仍独立于源。定义 `u_k=P_k w`、`‖u_k‖²=N`，以及 N 维经验全纯四阶矩

\[
m_s=\frac1T\sum_{t=1}^T(X_s^{(t)})^4,
\qquad m=-h^4u_r+e,\qquad E[e]=0.
\tag{28}
\]

**未知复 gain 的 profile least squares。** 对每个候选 k，把未知 `−h⁴` 视为自由复尺度 α。其无约束最小二乘满足

\[
\widehat\alpha_k=\frac{u_k^Hm}{N},\qquad
\min_{\alpha\in\mathbb C}\|m-\alpha u_k\|_2^2
=\|m\|_2^2-\frac{|u_k^Hm|^2}{N}.
\tag{29}
\]

因此该 profile LS 规则等价于选最大 `|u_kᴴm|`，不需要真实 h 作输入。它不是已证的有限样本最大似然规则：e 一般非 Gaussian，且其方差依赖 h。这里仅用 N 个坐标四阶矩构成相关器，不要求实际存储 N⁴ 个完整张量项。

**三个指标必须区分。** 令真均值 μ_m=−h⁴u_r，q=k−r mod N；由 `u_kᴴu_r=N A_{r−k}` 和 `|A_{−q}|=|A_q|`，

\[
\begin{aligned}
\min_{\alpha\in\mathbb C}\|\mu_m-\alpha u_k\|_2^2
&=N|h|^8(1-|A_q|^2),\\
|u_r^H\mu_m|-|u_k^H\mu_m|
&=N|h|^4(1-|A_q|).
\end{aligned}
\tag{30}
\]

第一行是真均值到错误候选**复直线**的距离平方，已允许错误分支调整 gain 幅度和相位；第二行是未归一化相关器的原始分数差。它们均不同于 (14) 在平幅 |H_i|=|h| 下只优化公共相位的完整（4,0）张量距离平方 `2N|h|⁸(1−|A_q|)`。

**噪声方差的精确核算。** QPSK 满足 `S⁴=−1` 逐样本恒定。对任意固定 |a|=|h| 与 `ξ~CN(0,σ²)`，二项式及 `E[ξ^j conj(ξ)^k]=0`（j≠k）给

\[
E|a+\xi|^8
=\sum_{j=0}^4\binom4j^2 j!\,|h|^{8-2j}(\sigma^2)^j.
\tag{31}
\]

对源相位平均不会改变此式。减去四阶均值的模平方 |h|⁸，得到单坐标四阶误差的复方差

\[
\begin{aligned}
V&=16|h|^6\sigma^2+72|h|^4(\sigma^2)^2
+96|h|^2(\sigma^2)^3+24(\sigma^2)^4,\\
\operatorname{Cov}(e)&=\frac VT I,
\qquad E|u_k^He|^2=\frac{NV}{T}.
\end{aligned}
\tag{32}
\]

这里复方差指中心化后的 `E|·|²`。坐标误差的独立性来自 (27) 中真实补偿后的 iid 源和噪声；不同候选的相关器误差共享 e，不能直接宣称彼此独立。

**确定性的正确选支条件。** 令 `ρ=max_{q≠0}|A_q|<1`，则

\[
\max_{k\in\mathbb Z_N}|u_k^He|
<\frac{N|h|^4(1-\rho)}2
\quad\Longrightarrow\quad
\underset{k}{\arg\max}\ |u_k^Hm|=r.
\tag{33}
\]

证明只需三角不等式：真分支的分数至少为 `N|h|⁴−B`，任一假分支的分数至多为 `N|h|⁴ρ+B`，其中 B 是左侧最大扰动。此为关于真实参数的分析保证，不要求选择器获得真实 h。式 (32) 刻画真补偿下的相关误差方差，尚未据此宣称实际观察预算下的选支概率或算法收益。

**实际分数估计的边界。** 若 κ 换成同一批 Y 估计的 κ̂，残余分数偏移一般混合源坐标，数据依赖的补偿又与噪声相关；此时 (28) 的精确均值、无偏性、坐标独立性及 (32) 不能直接沿用。即使 κ̂ 来自独立数据，只要残余偏移非零，仍须另行分析均值变化。此桥梁只提供可检验的理想条件和 profile 相关器形式，未把真分数补偿当成已经部署的前端。

### 9. 未知幅度、物理资格与实现边界

1. **幅度未知。** 总体上 balanced 四阶对角给 |H_i|，所以第 2 节的完整-law 结论不依赖 oracle 幅度。有限样本中对角四阶估计及开方可能不稳定；不得静默 clip 后宣称取得总体保证。
2. **深衰落。** (16) 的 h_min⁸ 可任意接近零；实际严格正 PDP 只给一般方向的连续支持，不给统一时间坐标下界。H 有零坐标时不能直接沿用完整 balanced 纤维定理，本稿不宣称完整歧义分类仍成立。
3. **实际物理参数类。** (3) 首先是 ambient 固定 H 类中的歧义；时间域对角模型直接适用于共同零 delay 分支，不自动覆盖一般不同 delay 的 AFDM 多径信道。某些 χ_rH 可能不属于允许的 Doppler、mask 或多径族；若物理先验已排除它们，抗 character 设计可能没有额外的可实现收益。平幅 H 只是设计指标的解析参考，不替代真实双径/PDP 分布。G0 截断与未截断模型的区别沿用上一轮 POWER_IDENTIFIABILITY 第 9 节，不用改变模型制造收益。
4. **相位优化仅为总体诊断。** (14) 对真实张量与 a 作优化不是可部署候选选择器。一般 H 下，从 balanced 四阶构造候选再由完整全纯四阶张量（4,0）选支，仍有幅度估计、候选生成和共享样本误差问题。第 8 节在真分数补偿的单径条件下给出 N 维相关器桥梁，但未解决实际同样本分数估计后的误差。
5. **并非任意 power-only 高阶。** 完整全纯四阶张量（4,0）保留相位信息。仅原始坐标 |Y|² 的统计仍受上一轮整块功率分布不变性约束；先非对角变换后取模则是另一类相位敏感测量。
6. **波形兼容。** 改 c₂ 会改实际调制/解调，不是免费后处理。当前生产 c₁/c₂、full-diversity、支持 guard、pilot/receiver 和多径模型契约必须由主线程先核对。这里无生产采纳、CONF 或运行授权。

## Files Found / Code Patterns

- `experiments/sp_afdm_frozen_20260920/src/physical.py:87`：冻结 `daft`；`:89–90` 给两 chirp 与 Fourier 正负号，支持 (2)。
- `experiments/afdm_higher_order_information/prior.py:17`：研究系统的 `c₁=2.5/N,c₂=.1/N²` 及原 cap/prune 设置；第 7 节保持这个实际 c₂ 对照。
- `experiments/afdm_coherent_structure_20261006/core.py:70`：固定一份 H 后重复未知 QPSK 与 Gaussian 噪声的相干观察；本稿不运行该函数。
- 同任务 `research/20261006-deep/BLIND_INVARIANTS.md:104`：balanced 四阶闭合与完整 U(1)×Z_N 纤维；`:199` 的 N4 公共相位推论由本文一般 N 条件扩展。
- 同任务 `research/20261006-usable/POWER_IDENTIFIABILITY.md` 第 9 节：full/G0 模型区别、power-only 联合分布不变性，保持只读。

## Related Specs / External References

- 复用已读 `research-protocol.md`、`bounded-mathematical-studies.md`、`structured-inference.md`：模型真实性、解析与数值证据分离、冻结准入与服务器约束不变。
- 按已读 `formula-derivation` 的假设—恒等式—命题—范围格式组织；未重启生命周期或载入其他角色 manifest。
- 本轮文献查新由主线程负责，本稿没有新增外部检索。CAZAC、二次相位码和 QPSK 的 C₄ 对称是经典对象；不能仅凭上述精确推导宣称首创。
- 未读取并验证一手 AFDM full-diversity 定理，故不给候选 c₂ 的无条件兼容承诺；小无理扰动只提供 (21) 的确定性码分离保障。

## Caveats / Not Found

- 完整-law iff 依赖固定且全部非零的 H、iid QPSK、已知同一 U 与相同 white proper Gaussian 模型；不对 gain 边缘化模型作统一结论。
- (14)、(16)、(26) 是单个完整全纯四阶张量（4,0）块的距离平方；(30) 的复直线距离平方与原始相关分数差是另外两个指标。均不直接等于统计距离、样本复杂度或实际收益。
- 第 8 节 profile 相关器均值与方差只在真实分数补偿、单径及 iid proper Gaussian 噪声下成立；未外推实际同样本分数估计后的无偏性或独立性。
- CAZAC 最优性只针对平幅完整四阶张量指标；深衰落、未知幅度估计与有限样本代价尚未解决。
- 物理类可能已排除某些或全部 character 候选；这种情况下本设计的实际用途尚待证明。
- 未运行任何科学数值、随机观察或 SSH，未改旧稿、生产波形、接收机或其他代理文件。此文件完成不等于本轮长期目标完成。
