# Research: 连续帧四阶相位码的旋转序列、有限时间 alias 与一致解码

- Query: 连续 CFO 帧的四阶相关向量能否化为旋转 iid 序列？能否不假设精确分数前端或估频后的噪声独立性，同时消除跨帧相消并改善整数点的四次根慢率？
- Scope: internal / mathematical；仅解析探索，无科学代码、仿真、采样或 SSH。
- Date: 2026-10-06
- Active task: `.trellis/tasks/10-05-method-advantage`；本文件是唯一写入对象，不维护另一个任务状态。
- Status: 以下为完整自查推导，尚待主线程独立审查；不是文献首创或“大创新已达成”的结论。

## Findings

连续帧模型确实允许 `q_t=e^{iωt}(μ+e_t)` 的精确表示，e_t 为 iid、零均值且具有全部有限矩的复向量；但一般不应假设 e_t proper。频率 `ω=8πνL/N mod 2π` 只给 ν modulo `N/(4L)`。

不必先证明单音最小二乘的 T^(−3/2) 频率率。一个更容易完整证明的入口是相邻帧矩阵：`M_T=avg(q_{t+1}q_tᴴ)`。其期望恰为 `e^{iω}μμᴴ`。迹给时间频率，而 `M_T/tr(M_T)` 给未知 gain 无关的空间投影；N≥3 时，该投影可在 4L 个时间 alias 中唯一选支。

这个有限候选估计器在固定 N、L、ν、h≠0 下模 N 强一致；当 σ²>0 时有可证明的局部 root-T 正态极限。整数 CFO 处同样是 root-T，因估计值由时间频率决定、空间响应只作有限选支，不再对估计噪声取第四次根。本文件没有声称它最优，也没有证明 T^(−3/2) 率。

相邻帧相关、单音相位估计及秩一归一化本身属于经典结构。当前可争取的增量是其与随机 QPSK 的精确四阶空间码响应结合，得到不需块起始相位对齐的连续帧结论；是否超出已知 cyclic-cumulant 同步组合仍须一手文献审查，不能单凭这一推导认定“大创新”。

### 1. 模型、范围与先排除的反例

固定 N≥3、整数采样间隔 L≥1、非零未知复 h、CFO ν∈R/NZ。已去除已知行 chirp 后，连续帧观察为

\[
Z_t=h e^{2\pi i\nu Lt/N}D_\nu F^HCS_t+\eta_t,
\qquad D_\nu=\operatorname{diag}(e^{2\pi i\nu n/N}).
\tag{1}
\]

F 为负指数酉 DFT，`C=diag(v)`，|v_s|=1，`w_s=v_s⁴` 的循环平移正交。各帧及各坐标的 S 独立均匀取 `exp(iπ/4)C₄`；噪声 iid `CN(0,σ²I)`，零均值 proper，独立于全部源。h 是不含已显式写出的 CFO 块起始相位的固定通道系数。σ²≥0；非退化速率结论另外要求 σ²>0。

这不是一般时变相位信道：若再允许每帧任意未知通道相位，时间频率可被该相位吸收，以下结论不成立。非 circular 噪声也不保证反旋转后 iid。L 必须已知；L 为正整数时 ν+N 与 ν 的原始采样模型完全相同，故目标只能 modulo N。

定义每帧的已知变换与四阶相关：

\[
X_t=FZ_t,\quad u_k=P_kw,\quad
(P_kz)_s=z_{s-k\bmod N},\quad
(q_t)_k=\frac1N u_k^H X_t^{\odot4}.
\tag{2}
\]

本文件没有分数 CFO 补偿前端，也不把任何估计频率当作真值去假定条件噪声仍白。

### 2. 精确旋转 iid 表示

令 β=2πνL/N，将噪声定义为 `η'_t=e^{−iβt}η_t`。由于各帧 white proper Gaussian 的圆对称性，全部 η′_t 的联合律仍 iid，且与 S 独立。因此

\[
Z_t=e^{i\beta t}\widetilde Z_t,
\qquad \widetilde Z_t=hD_\nu F^HCS_t+\eta'_t
\quad\text{为 iid 向量。}
\tag{3}
\]

式 (2) 的变换对 Z 为四次齐次函数，故精确有

\[
q_t=e^{i\omega t}(\mu+e_t),\qquad
\omega=4\beta=8\pi\nu L/N\pmod{2\pi}.
\tag{4}
\]

其中 e_t 是对 iid `\widetilde Z_t` 应用同一四次多项式再中心化所得，iid、E[e_t]=0，具有全部有限矩。这是利用真实固定参数构造的分布表示，不是估频后条件噪声独立性的声明。

沿用已核对的残差卷积及 CAZAC 反卷积恒等式，令

\[
g_\nu(k)=\frac1N\sum_{n=0}^{N-1}e^{2\pi i(\nu-k)n/N},
\qquad b(\nu)_k=g_\nu(k)^4,
\qquad \mu=-h^4b(\nu).
\tag{5}
\]

这里是 g 的复四次幂，不是 |g|⁴。由于 `Σ_k|g_ν(k)|²=1`，b(ν) 从不为零；h≠0 保证 μ≠0。一般残差 ν 下 e_t 的伪协方差可能非零，下面保留它。

### 3. 相邻帧矩阵避免估频后再假定独立

设 `z_t=μ+e_t`，对 T≥2 定义

\[
M_T=\frac1{T-1}\sum_{t=0}^{T-2}q_{t+1}q_t^H
=e^{i\omega}\frac1{T-1}\sum_{t=0}^{T-2}z_{t+1}z_t^H.
\tag{6}
\]

z_t 独立，故

\[
E[M_T]=e^{i\omega}\mu\mu^H,
\qquad E[\operatorname{tr}M_T]=e^{i\omega}\|\mu\|_2^2.
\tag{7}
\]

乘积序列只是一阶相依；按偶数 t、奇数 t 拆分，各自是 iid 的不重叠相邻帧乘积。有限矩强大数定律给

\[
M_T\longrightarrow e^{i\omega}\mu\mu^H
\quad\text{a.s.}
\tag{8}
\]

所以在 `tr(M_T)≠0` 时可同时定义

\[
\widehat\omega_T=\arg\operatorname{tr}M_T\pmod{2\pi},
\qquad \widehat B_T=\frac{M_T}{\operatorname{tr}M_T}.
\tag{9}
\]

其极限分别为 ω 与

\[
B(\nu)=\frac{b(\nu)b(\nu)^H}{\|b(\nu)\|_2^2}.
\tag{10}
\]

后者消除了 h 的全部复尺度和时间旋转相位。有限 T 的 B̂_T 不必 Hermitian/PSD；它直接作为矩阵模板的估计即可，不作静默投影或裁剪。若迹恰为零则报告未判定；因 (7) 的极限非零，该失败状态几乎必然最终不再出现。

### 4. 空间投影与有限时间 alias 的唯一性

N≥3 时，ν↦B(ν) 在 R/NZ 上单射。证明：若 B(ν)=B(ν′)，则 b(ν′) 与 b(ν) 成比例，因而其模的峰位置和相邻比值相同。前轮已逐边界核对的 Dirichlet 比值逆由这些量唯一给 ν modulo N；在整数处只有一个非零峰，在半整数处两个相邻峰给同一中点。这证明投影相等强制 ν′=ν mod N，而不需要未知 h。

单靠时间频率，给定 `ω∈[0,2π)` 时有 4L 个候选：

\[
\nu_j(\omega)=\frac{N}{8\pi L}(\omega+2\pi j),
\qquad j=0,\ldots,4L-1.
\tag{11}
\]

它们均在 [0,N) 且两两不同。采用完全数据定义的有限选支规则

\[
\widehat j_T\in\arg\min_j
\|\widehat B_T-B(\nu_j(\widehat\omega_T))\|_F,
\qquad \widehat\nu_T=\nu_{\widehat j_T}(\widehat\omega_T)\pmod N,
\tag{12}
\]

以固定规则处理有限样本相同分数。这里 N 维 b 模板是已知解析函数，不输入真实 h、ν 或真实 alias 标签。

**强一致性。** 对每个固定合法 N,L,ν,h,σ²，真实时间 alias 对应的投影与全部错误候选有严格正的最小距离，因为候选有限且 (10) 单射。b 及 B 在 ν 的圆上连续。由 (8)–(10)，足够大 T 时错误候选都比真候选的局部延拓更远，因此 (12) 最终选中真候选的局部延拓，且 ν̂_T→ν modulo N a.s.。ω=0 的主值跳变只重排候选索引，不改变圆上的候选集合或结论。

这里空间曲线可能非常平坦，但它只负责固定有限候选的最终排除。定理没有给 N、L 增长、深衰落或 alias 间距趋零时的统一样本界。

**N=2 的具体接口反例。** 令 0<x<1/2。此时

\[
b(x)=e^{2\pi ix}(\cos^4(\pi x/2),\sin^4(\pi x/2)),
\tag{13}
\]

所以 B(x)=B(−x)。再取 x=1/(4L)，两者时间频率都等于 π modulo 2π。因此这个相邻帧均值接口对这两个不同 CFO 无法消歧。它不证明所有原始观测估计器都失败，但足以阻止把 (12) 的全局结论无条件扩到 N=2。

### 5. 可证明的局部 root-T 率，不预设 T^(−3/2)

定义 iid e_t 的协方差与伪协方差

\[
\Sigma=E[e_te_t^H],\qquad \Pi=E[e_te_t^T],\qquad
a=\|\mu\|_2^2>0.
\tag{14}
\]

去真实旋转后的迹为相邻复内积平均。其虚部的线性噪声项精确望远镜相消：

\[
\begin{aligned}
\operatorname{Im}(z_t^Hz_{t+1})
&=\operatorname{Im}(\mu^He_{t+1})-
\operatorname{Im}(\mu^He_t)+b_t,\\
b_t&=\operatorname{Im}(e_t^He_{t+1}).
\end{aligned}
\tag{15}
\]

b_t 是零均值一阶相依序列。由独立的两端 e_t、e_{t+2} 均零均值，`Cov(b_t,b_{t+1})=0`。又

\[
\begin{aligned}
E|e_t^He_{t+1}|^2&=\operatorname{tr}(\Sigma^2),\\
E[(e_t^He_{t+1})^2]&=\|\Pi\|_F^2,\\
v_b=\operatorname{Var}(b_t)
&=\tfrac12\{\operatorname{tr}(\Sigma^2)-\|\Pi\|_F^2\}\ge0.
\end{aligned}
\tag{16}
\]

全部有限矩满足标准一阶相依 CLT 的条件。式 (15) 两个端点项除以 √T 后依概率消失，所以对 ω 的局部有符号圆周误差 ℓ_{2π}，arg 的 delta method 给

\[
\sqrt T\,\ell_{2\pi}(\widehat\omega_T-\omega)
\ \Longrightarrow\ \mathcal N(0,v_b/a^2).
\tag{17}
\]

这里并未把 e_t 在使用 ω̂_T 后当成新的独立噪声；CLT 全部直接对真实参数下的原始统计 (6) 推导。若 v_b=0，(17) 只是退化极限，不声称非退化 root-T 尺度。

σ²>0 是 v_b>0 的充分条件：给定符号后 X 含全支持复 Gaussian 噪声；逐坐标第四次幂是满射，且 CAZAC 相关变换可逆，所以 e_t 在 C^N 有全支持。独立 e_t、e_{t+1} 的内积虚部不可能几乎处处为零，故 v_b>0。

由第 4 节的最终正确有限选支，ν̂_T 的局部有符号圆周误差满足

\[
\sqrt T\,\ell_N(\widehat\nu_T-\nu)
\ \Longrightarrow\
\mathcal N\!\left(0,
\left(\frac{N}{8\pi L}\right)^2\frac{v_b}{a^2}\right).
\tag{18}
\]

这一结论对每个固定 ν，包括整数和半整数 CFO，都成立。空间投影仅用于最终选支，连续数值由时间频率给出，所以不需在整数处对空间弱侧瓣噪声取第四次根。这里不是关于 ν 邻域、h→0 或 N,L 变化的统一速率。

**整数 CFO 的可核算常数。** 在 ν 为整数时，前轮已核对的每帧相关误差满足

\[
\Sigma=(V/N)I,\qquad \Pi=0,\qquad a=|h|^8,
\tag{19}
\]

其中

\[
V=16|h|^6\sigma^2+72|h|^4(\sigma^2)^2
+96|h|^2(\sigma^2)^3+24(\sigma^2)^4.
\tag{20}
\]

因此 (18) 的渐近方差为

\[
\frac{N V^2}{128\pi^2 L^2|h|^{16}}.
\tag{21}
\]

这是针对 (12) 的固定参数分布极限，不是有限样本 MSE 界、最优性结论或仿真收益。σ=0 时需另看是否 v_b 退化；整数且无噪时 e_t=0，不适用非退化 root-T 描述。

### 6. 未知循环 delay 的具体冲突：连续帧并不自动消歧

本节仅核对主线程提出的循环 delay 对照，不改变前文 zero-delay 假设，也不接管其联合识别文档。取偶 N、`c₁=5/(2N)`、`c₂=q_c/(8N)`，其中 gcd(q_c,N)=1。行 chirp `R_nn=exp(−2πic₁n²)` 在偶 N 下具有 N 周期，所以循环 delay l 经 R 去除后可写为

\[
h_l D_{\nu+5l}F^H C\,
\operatorname{diag}(e^{-2\pi ilj/N})S,
\tag{22}
\]

常相位已吸收入未知 h_l。四次幂码为 `w_j=exp(−πiq_cj²/N)`，其线性调制满足

\[
w_j e^{-8\pi ilj/N}
=e^{\pi iq_cr_l^2/N}w_{j-r_l},
\qquad r_l=-4q_c^{-1}l\pmod N.
\tag{23}
\]

式 (23) 不只说明四阶均值相等：两组单位模列系数除去一个公共相位后，逐坐标第四次幂完全相同，故相差逐坐标 C₄ 因子。配合 iid QPSK 的置换与 C₄ 不变性，(22) 的**完整单帧律**等同于某个零 delay 信道，等效 CFO 为

\[
\nu_{\rm eff}=\nu+5l+r_l\pmod N.
\tag{24}
\]

在连续帧中，真实块起始相位仍由 ν 决定；若

\[
4L(\nu_{\rm eff}-\nu)/N\in\mathbb Z,
\tag{25}
\]

则两模型逐帧相差的全局调制也是 C₄，固定一个起始公共 gain 相位后，全部独立帧的完整联合律仍相同。N=64、L=80 时 `4L/N=5`，所以任意整数 CFO 差都满足条件。例：q_c=1、l=1 给 ν_eff=ν+1；只要两参数都在允许范围，就不能靠本文件的连续帧方法区分它们。

该反例说明：消除旧跨帧相消与保证 zero-delay CFO 识别，不等于解决未知 delay。主线程的多码联合设计需要另外证明；本文件不作联合 delay–CFO 的可辨识性或收益承诺。

### 7. 与时间谱方法及创新目标的关系

对旋转序列 (4) 作单音谱估计是合理候选，但频率一致并不自动足以把旋转后直接均值当成 μ：若只知 ω̂−ω=o(1)，T(ω̂−ω) 仍可发散。证明这条谱路线需要相应的频率误差控制或联合估计论证，不能直接套一个未验证的 T^(−3/2) 率。

本文件用 lag-one 矩阵绕开这个依赖：相位在相邻帧间只留下常数 e^{iω}，且空间信息由迹比直接保留。它没有“估频后噪声仍独立”的缺口，也无需无偿的逐帧相位对齐；代价是 q 本身为四阶统计，M 为跨帧八阶乘积，噪声和有限样本成本可能较高。

与旧小理论包相比，严格增加的是：连续 CFO 帧适用的观测统计；未知 gain 下有限时间 alias 的一致消除；不依赖朴素第四次根的、整数点也成立的 root-T 例子。尚未证明它优于经典连续 CFO 估计、单音频率拟合、其他 cyclic-cumulant 方案或现有前端。若文献已有相同阶次、相同相位码与 alias 消除接口，则它仍可能只是可用的经典组合；当前不能把数学闭合等同于较大创新。

## Files Found / Code Patterns / Related Specs

- 同任务 `research/20261006-residual/DERIVATION_PACKAGE.md` Proposition 1–2：随机 QPSK 的 `g_δ⁴*w` 传递与 CAZAC 相关取出 `g_δ⁴`；本文保留其正负号和 1/N 相关归一化。
- 同文件 Proposition 4–5：N≥3 的空间 Dirichlet 比值识别，以及旧直接第四次根在整数处的 T^(−1/8) 限制；这里仅用其总体空间单射性和整数误差协方差。
- 同任务 `research/20261006-phase/PHASE_CODE_THEORY.md` 第 8 节：V 的 16/72/96/24 系数及 proper 误差核算。
- `experiments/sp_afdm_frozen_20260920/src/physical.py:87`：已读取的负指数酉 Fourier 与两 chirp 约定；本轮未运行该代码。
- 复用已读研究与服务器规范；无新生命周期、源码、CSV 或其他代理文档写入。

## External References / Novelty Boundary

本轮未新增文献检索。相邻相关的相位估计、有限相依 CLT、秩一模板匹配和二次相位码不主张首创。具体 cyclic-cumulant / coded CFO 最近工作及该组合的技术差异由主线程核对；无未经引用的 full-diversity 保证。

## Caveats / Not Found

- 固定单径、无 timing 偏差、固定复 h、已知整数 L、iid QPSK 与 proper white Gaussian；任意块间通道相位、非 circular 噪声或多径不在保证内。
- 第 6 节给出未知循环 delay 时可延续到连续帧完整联合律的具体歧义，不能将 zero-delay 定理外推为联合 delay–CFO 识别。
- 结论仅 modulo N；时间频率单独仍有 4L 个 alias，N=2 给出了该接口不能消除的反例。
- root-T 是固定参数局部极限，不是最优率、邻域统一率、增长维度结果或有限样本性能证据。
- 第 4 节可能需要辨别很近的空间模板；没有给跨 L、N、深衰落的统一选支预算。
- 未执行任何新科学数值、随机样本、SSH 或生产波形更改。本文仍是待独立审查的研究候选，不满足“大创新”目标的自动停止条件。
