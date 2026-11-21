# TASK B — 沿信道更新方向削弱自生软符号回灌

日期：2026-10-13。Active task：`.trellis/tasks/10-08-doppler-cluster`。

## Target

**只提出一个修正：沿最近一次 gain 更新对当前 data pseudo-observation 的完整局部响应，构造 rank-one 的正则化外信息软符号；仅把该软符号送给信道更新。** 下文称 DIR。数据 marginal、decoder LLR、pilot、DPSS、delay support、flat prior、外轮数均保持原定义。

核心不是“再加一个 scalar Onsager”。现核已有 Onsager；DIR 针对有限步、实际结构算子的一条观察得到的反馈方向。新信道分支使用直接 residual 的一次 ridge 优化步，替换原 AMP gain-message 分支，避免两套反应扣除叠加。RAW/GLOB 只作必要消融与近邻控制，不是第二个推荐方法。

## Status

**COHERENT AFTER REFRAMING / EXTRA ASSUMPTION。** 局部反应衰减、posterior shift 的不确定性记账、一次二次目标下降可代数证明；实际 C1 的 own-symbol excess、FER、成本改善尚未证明。没有把 J/R2 已失败的 scalar closure 复活。

标签：**[F]** 文件或原文事实；**[D]** 本文推导/恒等式；**[I]** 证据推论；**[S]** 待测假设、设计选择、试验门。每项非精确推广另外注明近似。本次仅读文件、读网页及写本报告；无代码修改、SSH、运行、git。报告不是实验运行授权。

**新颖性裁决先写明：外信息、正交反馈、SP 联合 OAMP 均已有。本文只剩“有限步完整响应选方向＋只扣一条反应＋矩阵自由实现＋J12 定向因果检验”的候选区别；未建立 Transactions 贡献。** 2026 年已有很近的 SP/ODDM OAMP-JED，见 Prior Art。

## Invariant Object

对象始终是：**同一观测产生的软符号，如何把当前信道估计误差送回信道估计，以及这项反馈在固定实际计算量下的代价。**

离线风险对象为 \(\|P_\perp(h_T-h_o)\|^2\)，其中 \(P_\perp=I-h_oh_o^H/\|h_o\|^2\)。h_o 是真 tap 在同一 DPSS 基的投影，只用于评分；不进入 DIR。Kc 是有限 R/T 的 FER=.5 crossing，不是容量或普适物理 DoF。

### 已有事实与不能推出的结论

| 已有证据 [F] | 对本方法的约束 |
|---|---|
| `c1-joint-fp-theory.md` §9：J12 9/10 格中 \(|D_{reg}|>|D_{alg}|\)；D_reg=.29–.62，D_alg 多数为负 | 不能只优化 joint-vs-plain 差异；也不能称既有 Onsager 完全无效。 |
| 同节：T40/T20 的 orthogonal error=.64–.98；T80/T20=.49–1.00；T20 mid-transient | 固定 T20 改善不够，必须与调优 T30/T40 比。 |
| `c1-round2-own-symbol-theory.md` §7：image 正、absorption/intrinsic 负；Gram 差异正；三个 scalar magnitude 模型失败 | 去掉全部同观测相关性可能删有用信息；不能假定 Q_S≈Q_I。 |
| `c1-inner-budget.md`：预算收益复现，但配置修复不是新方法 | 更新次数不能当成本；必须完整 clock 与相同可靠性/负载比较。 |
| `codex-kernel-review-20261013.md` Q2：data Onsager sum(vh) 有归一化依据；B 列能量不等 | 不往 data update 再塞一个 dense AMP Onsager；信道分支按实际 B 列能量计算。 |
| `research-assets/res-20261013-01.md`：action value 无决策增量 | 本方案不回到 per-frame scheduling，不用学习 failure predictor 包装修正。 |

**[I]** 这些证据支持测试定向反馈控制；不证明最近 gain innovation 就是真信道误差主方向，更不证明一个 rank-one 修正足够。

## Assumptions

1. **[F/D] 固定表示。** C1 genie delays、D=8、flat tau=1/K、drop=0、CPP、N=1024。沿用同一 TimePathOps；不调用有系数接口缺陷的 TapChannel.apply。
2. **[D] 局部微分合同。** 分析一轮 inner update 时，进入该轮的 x/v/vh、旧 residual/damping 状态、外部 prior 固定；只微扰当前 h。这是有限步切片，不是整条轨迹 Jacobian。
3. **[D] QPSK factorized marginal。** 在当前 scalar Gaussian likelihood 与冻结 bit prior 下，实/虚 posterior 独立；Jacobian 可由 posterior 均值算出。此为代码 likelihood 的性质，不要求物理有效噪声真的 Gaussian。
4. **[D] 外信息系数冻结合同。** 证明局部反应时，方向 q、Jacobian 作用向量 u、系数 c 固定。实际算法每步重算它们；其全导数额外项未被证明小，必须测。
5. **[S] 定向覆盖假设。** 最近 gain 更新方向包含造成有害回灌的可观比例。未假定它等于 \(h-h_o\)，也未假定误差各向同性。
6. **[S，近似] 信道统计模型。** 用 corrected feedback 的局部 posterior 二阶矩构造有效白噪声 ridge；非对角 symbol/gain covariance、true residual 与设计的高阶依赖仍未保留。
7. **[S，近似] gain variance。** 新分支返回 diagonal curvature variance，作为下一步 data branch 的 q_h surrogate。它不是完整 posterior covariance，也不是已证明的 hybrid AMP state evolution。

正则量固定 \(\epsilon=10^{-2}\)，damping 沿用 \(\delta=.3\)。epsilon 只限制局部反应扣除系数，非训练所得相关性常数；不在 pilot 失败后扫 epsilon 抢救。

## Notation

沿用 `scalar_joint_cols`：n=N、P=K；x=pilot+mu；Y=IDAFT(y)；B(x) 的第 d 列为 \(U_dx\)；h、vh、hb、xb、s、sv、bar、vp、vr 的含义不变。

\[
H(h)=\sum_dh_dU_d,\quad R_{de}=\operatorname{tr}(U_d^HU_e)/n,
\quad \operatorname{power}(h)=h^HRh.
\]

DPSS 归一化给出 \(R_{dd}=1\)；同 tap 的基正交。h_prev 是**上一轮进入 inner loop 时的 h**，不是 hb，也不是上帧状态；初始化 h_prev=h_init。每轮更新 h 前保存当前 h 为下一轮 h_prev。

实表示：\(\mathcal R(z)=(\Re z_1,\ldots,\Re z_n,\Im z_1,\ldots,\Im z_n)^T\)。符号 pseudo-observation \(r=rx-pilot\)，posterior output 为 \(\mu^+,v^+\)，上标 + 指 `D:171` 之后；D 代表 `experiments/headroom_ladder_20261008/dpss_rx.py`。

## Derivation Strategy

先从精确的 errors-in-variables 信道误差恒等式指出有害项，再直接微分有限步 kernel，得到一条实际反馈方向。对该方向上的 nonlinear response 解一个正则化去反应问题。导出的 soft feedback 均值附带相应不确定性，送入独立的 channel score 分支。用消融把相关性修正与换 solver/列 precision 分开。

## Derivation Map

1. EIV 恒等式定位 \(B(\mu)^HH_oe\)；J12 说明不能以 MSE 一个数替它。
2. 完整 \(D_h rx[g]\) 同时含 residual、adjoint、precision、bar/vp 变化；不只取 \(-H^HB g\)。
3. QPSK Jacobian加上likelihood温度的 \(\partial\mu/\partial vr\) 路径，给出完整denoiser response u、alpha；正则化选择 c。
4. 系数冻结时，soft-symbol回应乘 \(\epsilon\|u\|^2/[(1-\alpha)^2+\epsilon\|u\|^2]\)。
5. shifted posterior mean 的 expected square error 是 v 加位移平方；不能免费宣称 decorrelation 降 MSE。
6. 新 channel residual + 单次预条件最陡下降步；旧 gain Onsager 分支整体移除。
7. 未冻结全导数、J12 excess、误差 transient、固定成本 Kc 决定候选能否存活。

## Main Derivation

### 1. 相关误差从哪里进入信道 [D，精确恒等式]

真实 AF data 为 d，真投影系数为 h_o，软反馈为 m，e=d-m。令 \(B_m=B(pilot+m)\)，\(Q_m=B_m^HB_m+\lambda I\)，\(Y=B(pilot+d)h_o+w+r_{mis}\)。则

\[
h_m-h_o=Q_m^{-1}
\{B_m^HH_oe+B_m^H(w+r_{mis})-\lambda h_o\}.
\tag{1}
\]

因此 own soft-symbol error 与 channel/noise 的方向相关会改变信道风险，即使 \(\|e\|^2\) 不变。\(Q_m\) 同时变化；本方案不删这一项、不套 Q_S≈Q_I。

**[I]** 若能减少沿近期信道更新方向的符号反应，可能减少式(1)里的 channel-error image；但同方向也可能含有用纠错反应。后续风险与 FER 门负责判别。

### 2. 微分真实的有限步 h→rx，而非使用 scalar loop gain [D]

选择观察得到的 gain innovation

\[
g=h-h_{prev}.
\tag{2}
\]

把 g 当一个**实参数扰动方向**：h(a)=h+a g，a 为实数。进入该步的其他状态固定。定义 \(\ell=D_h rx[g]\)。下面给出其完整可实现表达式。

设 s_-、sv_- 为 `D:158–159` 更新前值；bar_old/vp_old 固定；\(\delta=\text{damping}\)。令 \(\omega=1\) 当 bar0=None，否则 \(\omega=\delta\)。已算出的当前 bar/vp/s/sv/hb/xb 使用原 kernel 数值。令 \(D_o=noise+vp\)，\(V=\sum_d vh_d\)，\(t=Y-ph\)。

\[
\dot q=2\Re(g^HRh),\qquad
\dot{bar}=\dot{vp}=\omega\,vx\,\dot q,
\tag{3}
\]

\[
\dot{ph}=B g-s_-\dot{bar},\quad
\dot s=-\delta\frac{\dot{ph}}{D_o}
-\delta\frac{t\,\dot{vp}}{D_o^2},\quad
\dot{sv}=-\delta\frac{\dot{vp}}{D_o^2},\quad
\dot{hb}=\delta g.
\tag{4}
\]

`xb` 对此 h 切片的导数为零。设 \(q_b=hb^HRhb\)、\(J_x=sv q_b\)，则

\[
\dot q_b=2\Re((\delta g)^HRhb),\quad
\dot J_x=\dot{sv}\,q_b+sv\dot q_b,
\quad \dot{vr}=-vr^2\dot J_x
\tag{5}
\]

当 data precision 严格落在 `1e-12` floor 下时，\(\dot{vr}=0\)；在 floor 的不可微边界，测试按单侧导数注明，不虚报中心差分合同通过。

\[
adj=H(hb)^Hs,
\quad \dot{adj}=H(\delta g)^Hs+H(hb)^H\dot s,
\tag{6}
\]

\[
\boxed{\ell=\dot{vr}(adj-xb\,svV)
+vr(\dot{adj}-xb\,\dot{sv}V).}
\tag{7}
\]

式(6)用两次 `o.adjoint_time` 求和后做**一次 DAFT**，不需 n×n H。B g 用现有 B。R 已在 o 中。

这里包含了 R2 候选 image 模型遗漏的 adjoint 与 precision paths；包括 pilot，因为 B 来自 pilot+mu。它仍未包含跨步、外 decoder 或 prior 的全历史导数。

若 \(\|\ell\|=0\)，rx方向无法归一化，定义本修正为零并记录rank-zero；它不处理rx不动但vr变化的pure-temperature方向，不能声称此时全部denoiser response为零。首步g=0时两路均为零。否则

\[
q=\mathcal R(\ell)/\|\ell\|\in\mathbb R^{2n},\qquad q^Tq=1.
\tag{8}
\]

### 3. 实 Jacobian 保留 QPSK 的实/虚差异 [D]

`D:171` 的 scalar likelihood 是 \(\exp[-|r-a|^2/vr]\)。设 \(m=\mathcal R(\mu^+)\)，\(r_R=\mathcal R(r)\)。QPSK 每实分量幅度为 \(\sqrt{pd/2}\)，故

\[
v_{I,j}=pd/2-(\Re\mu_j^+)^2,\quad
v_{Q,j}=pd/2-(\Im\mu_j^+)^2,
\]

\[
J=\operatorname{diag}
\left(2v_I/vr,\ 2v_Q/vr\right).
\tag{9}
\]

冻结bit prior时I/Q条件独立，off-diagonal derivative为零。total v=v_I+v_Q；不以v/vr代替全部real Jacobian。还有一条不能遗漏的直接温度路径：

\[
k_v:=\partial m/\partial vr
=-\frac{2}{vr^2}
\begin{pmatrix}v_I\odot\Re r\\v_Q\odot\Im r\end{pmatrix},
\qquad
\boxed{u=Jq+k_v\,\dot{vr}/\|\ell\|,
\quad \alpha=q^Tu.}
\tag{9b}
\]

等价地，complex \(\partial\mu/\partial vr=\operatorname{Cov}_{q_d}(a,|r-a|^2)/vr^2\)。这是固定prior对softmax的直接微分。因此完整 \(D_hm[g]=\|\ell\|u\)，不是只算 \(J\ell\)。posterior曲率可大于1，温度项也可改变alpha符号；不假装alpha每帧属于[0,1)。

### 4. 唯一推荐的 soft-feedback 修正 [D/S]

寻求 \(m_c=m+c\,u q^T(m-r_R)\)。冻结q/u/c，但保留h扰动引起的rx和vr变化，则

\[
\frac{D_hm_c[g]}{\|\ell\|}=u+c\,u(\alpha-1)
=u\{1-c(1-\alpha)\}.
\tag{10}
\]

无限增益扣除 \(c=(1-\alpha)^{-1}\) 在 alpha≈1 奇异。选择以下**明确的局部 surrogate**：

\[
c=\arg\min_z
\big[1-z(1-\alpha)\big]^2+\epsilon\|u\|^2 z^2
=\frac{1-\alpha}{(1-\alpha)^2+\epsilon\|u\|^2},
\quad\epsilon=10^{-2}.
\tag{11}
\]

因此

\[
\boxed{m_c=m+
\frac{1-\alpha}{(1-\alpha)^2+10^{-2}\|u\|^2}
\,u q^T(m-r_R),\qquad
\widetilde\mu=\mathcal R^{-1}(m_c).}
\tag{12}
\]

\[
\boxed{D_hm_c[g]=
\frac{10^{-2}\|u\|^2}{(1-\alpha)^2+10^{-2}\|u\|^2}\,D_hm[g].}
\tag{13}
\]

式(13)为**系数冻结的局部一阶结果**；u非零时衰减因子在(0,1]。用\(x=|1-\alpha|/\|u\|\)，有\(\|cu\|=x/(x^2+\epsilon)\le5\)，故rank-one扣除算子的norm有界；不能把这写成|c|本身必≤5。u=0时原denoiser方向响应已为零，修正为零。alpha=1时该regularized correction不动，不能声称能修所有near-neutral modes。alpha>1时c可负，仍由同一正则目标决定，不是切换到另一算法。

penalty乘\(\|u\|^2\)是为限制实际反馈位移而非仅限制scalar系数；加入直接temperature响应后，若rx响应很小，u本身可很大，固定\(\epsilon c^2\)无法限制输出map。

只改完整denoiser响应u这一输出方向的rank-one分量；不是逐符号硬裁剪，也不是把整个APP变成全局extrinsic。\(\widetilde\mu\) 可在QPSK convex hull外；它是用于CE的反馈量，不能喂进原QPSK marginal当作合法APP均值。

**[D，重要限制]** 若实际函数重算 q/u/c，则

\[
d\mu_R=J\,dr_R+k_v\,dvr,\qquad
dm_c=d\mu_R+c u q^T(d\mu_R-dr_R)
+d(cu q^T)(m-r_R).
\tag{14}
\]

最后一项未被式(13)消除；整个 kernel 的跨步导数还更复杂。故不能把 coefficient-frozen attenuation 当作 Gaussian decoupling、实际 channel-error 消除或全轨迹稳定定理。

**[S]** 预期近期 g 对主反馈模式有覆盖、系数变化项未抵消局部扣除。必须测试 full recomputation 的响应；只通过 frozen-coefficient 差分是代数自检，不是机制证据。

### 5. 不把相关性扣除当作免费 MSE 收益 [D/近似]

当前 marginal 给出的 distribution q_d 的均值为 mu^+、variance 为 v^+。对任何基于当前输入固定的 \(\widetilde\mu\)，有

\[
\widetilde v_j:=\mathbb E_{q_d}|d_j-\widetilde\mu_j|^2
=v_j^++|\widetilde\mu_j-\mu_j^+|^2,
\quad \bar v_c=n^{-1}\sum_j\widetilde v_j.
\tag{15}
\]

这是 q_d 下的恒等式，**不是物理 true MSE 校准保证**。它明确计入改变 posterior mean 的成本；不得减 variance 来制造“更可靠”。原 mu/v 保留，decoder 与下一轮 data branch 仍使用原 posterior。

以进入本步的 diagonal q_h surrogate 定义

\[
E_h=\operatorname{power}(h)+\sum_d vh_d,
\qquad s_c^2=noise+\bar v_c E_h.
\tag{16}
\]

对固定 R_dd=1，E_h 是该 Gaussian q_h 的平均 operator energy。把实际有色/相关误差压成 s_c²I 是明确近似。更小的 D_reg 也可能伴随更大的 intrinsic symbol uncertainty；最终收益不能由相关项一项的符号决定。

### 6. 同步替换 channel score；不叠加旧 gain Onsager [D/S]

构造 \(B_c=B(pilot+\widetilde\mu)\)，\(\Lambda=\operatorname{diag}(1/\tau)\)。冻结 B_c/s_c² 时，唯一 channel surrogate 目标为

\[
L_c(z)=\|Y-B_cz\|^2+s_c^2z^H\Lambda z.
\tag{17}
\]

不是再造一次独立观测；每步优化同一 Y，prior precision 始终用 tau⁻¹，**不把上一轮 gain precision 累加成新 prior**。

为避免每步 K×K ridge solve，做一次 diagonal-preconditioned steepest-descent：

\[
\beta_d=\|B_{c,d}\|^2,\quad
D_c=\operatorname{diag}(\beta_d+s_c^2/\tau_d),
\]

\[
g_c=B_c^H(Y-B_ch)-s_c^2\Lambda h,
\quad p_c=D_c^{-1}g_c,
\]

\[
\zeta=
\frac{\Re(g_c^Hp_c)}{\|B_cp_c\|^2+s_c^2p_c^H\Lambda p_c},
\qquad
\boxed{h^+=h+\delta\zeta p_c.}
\tag{18}
\]

g_c=0 时明确是 stationary point，令 h^+=h，不计算 0/0。其余情形 s_c²>0、tau>0，分母正。若有非有限数则报失败，不回退旧 kernel、不删帧。

**[D]** 令 a=Re(g_c^Hp_c)、b=p_c^H(B_c^HB_c+s_c²Lambda)p_c。则

\[
L_c(h^+)-L_c(h)
=-(2\delta-\delta^2)a^2/b\le0,
\quad 0<\delta\le1.
\tag{19}
\]

这是固定当前 surrogate 的下降，**不是** true channel error 或下一轮 L_c 的下降定理。

下一步使用的 gain variance 定义为 diagonal curvature proxy

\[
\boxed{vh_d^+=\frac{s_c^2}{\beta_d+s_c^2/\tau_d}.}
\tag{20}
\]

它等于该 quadratic Gaussian surrogate 忽略 off-diagonal precision 后的 variance；不是 `diag(Q_c^-1)`，也未把式(18)当精确 MAP solve。proxy 的失配需列入 calibration 诊断。

**为什么不把 D:170 的 −hb sv n vx 保留？** 原项与 AMP 的 s/Bb message 搭配；式(18)用直接 residual Y−B_c h、一次 prior 目标。把原项照搬进新 score 会对同一 symbol uncertainty 再做一套反应扣除，且不再是式(17)的梯度。data branch 的原 `rx` Onsager 留在原位；它的消息对象仍是原 mu，而不是 mu_tilde。整个混合迭代不冒称标准 BiG-AMP/OAMP。

## Kernel 的精确改动位置

这里列未来实现合同；本轮未改代码。

| scalar_joint_cols 行 | DIR 合同 |
|---|---|
| 132–141 | 增 h_prev=h.copy()。删除只服务旧 gain branch 的 Bb 初始化。每次调用独立状态，不跨帧/arm。 |
| 143–162 | 原 data/output 运算保留；额外保存 h_input、s_-、是否首个 bar update 及 t=Y−ph，供式(3)–(7)。 |
| 163 | 删除 Bb damping；新分支不使用它。xb/hb damping 留给 data branch 与方向计算。 |
| 164、166、168–169 | 原 data_precision、vr、adj、rx 不变；以式(3)–(7)算 ell。不是再次扣 data Onsager。 |
| 165、167、170 | 删除旧 gain_precision/vq/rh 分支；不要以新反馈 B_c^H s 与旧 s 勉强拼接。 |
| 171–172 | 原 ext/app/mu/v、x=pilot+mu 不变；另生成 CE-only mu_tilde、v_tilde、B_c。 |
| 173–174 | 替换为式(18)、(20)；在写 h_new 前把 h_input 保存为 h_prev。 |
| 175–182 | finite 检查覆盖新状态；trace 新增 alpha/c/attenuation/shift-risk/s_c²、真实 per-column precision 摘要、rank-zero、L_c 降幅。保留旧字段时必须标清 in/out 与单位。 |
| 182、184 | 正常步DAFT/IDAFT从2变4；总数上界4T+1（rank-zero可少一个，记录实际计数）；不能沿用2T+1。 |

`gain_pseudo_variance` 在新分支不再是原 shared vq；若需兼容分析，使用具名 vector 或 min/mean/max 新字段，旧共享字段标 unavailable。不能给旧递推脚本一个冒名值。

mode=OFF 必须调用原函数，复现 baseline。**仅把式(12)设 c=0 得到 RAW surrogate solver，不是冻结 kernel。** REF/OFF、RAW、DIR 的身份不能混写。

外部 `DpssRefine`、`GenieRefine`、native coded schedule不改；FROZEN/A3 fixed-gain arms不进入新分支。返回 mu/v/LLR 不替换成 CE-only 信息。所有新行为只在 joint correction arm 启用。

## Complexity

| 项 | 原 kernel | DIR |
|---|---|---|
| 每 inner step transforms | 1 IDAFT + 1 DAFT | 再加 derivative DAFT、B_c IDAFT，共4个 |
| channel contractions | Bb^H s | B_c h、B_c^H residual、B_c p_c；另有 B g 与两个 time adjoint 求和 |
| channel precision | shared sv*||xb||² | 实际每列 beta_d；O(nK) |
| nonlinear correction | marginal O(n) | marginal同；rank-one real Jacobian O(n) |
| dense solve | 无 | 无；无 n×n H、无 K×K新逆矩阵 |
| 时间阶 | O(nK+n log n+K²)，R已存 | 同阶，常数明显增加 |
| 主内存 | phase/M、B、Bb 等 O(nK) | 以B_c替Bb；另 O(n+K) 状态，同阶 |

**[D]** 最多两个额外 transforms、常数个 nK contractions。**[I]** 可能约两倍 detector-step 时间，未测；不能直接说“低成本”。DIR/T20 的 transform数与 BASE/T40 相同，其他 contractions不相同，必须实测。

**[S]** 实用目标是较少有效 inner steps达到调优 baseline 的可靠性，而不是同 T 无视成本报增益。rank-one correction 不引入 K 方向探针；首个实验不升级 rank、加 history bank、学参数或改 prior。

## Remarks and Interpretation：机制预测与 kill rules

### 可证明的预测 [D]

固定 q/u/c，当前 h 沿 g 的 infinitesimal perturbation引起的 CE-only soft response，相对 raw response乘式(13)因子。该因子可以逐状态计算；不拟合真值、不依赖 old scalar kappa。

### 要否证的机制链 [S]

1. 全部系数重算的实际 response也减小；近期 g 与离线测得的有害 image有覆盖。
2. 使用 mu_tilde 的 matched-MSE plain-refit excess低于 RAW，并且 actual orthogonal channel risk下降；不是只去掉有益 absorption。
3. 到达 BASE/T40风险邻域所需的**实测成本**缩短；不声称整条轨迹收敛。
4. 固定 T20 的 Kc可右移；更重要是相同完整 CPU 预算下，胜过T30/T40与GLOB，而非只胜默认T20。

| gate | 预定判据 [S] | 失败后动作 |
|---|---|---|
| B0 数学/实现合同 | analytic tangent vs centered differences相对误差≤1e-5；锁系数式(13)≤1e-5；式(19)数值非增；OFF复现旧 kernel | 属实现/推导错误，先停；不能用FER偶然好过关。 |
| B1 实际反馈反应 | full recomputation 的方向response比 RAW≤.70，在6个机制格中至少4格的cell median成立 | 不成立则kill“该实际反馈被本修正控制”的机制主张；不以锁系数检验代替。 |
| B2 own-error风险 | matched-MSE J12-style D_reg至少降.10，≥4/6格；orthogonal channel risk DIR/RAW≤.90，≥4/6格；无格>1.10 | 相关项改善但总风险不改善＝删有用信息；kill B targeted-method中心。 |
| B3 transient/成本 | 达到BASE40风险邻域的paired实测cost下降；DIR20若只等于BASE40且cost不少，不算新方法 | 仅固定T20好，成本解释掉＝kill计算贡献。 |
| B4 cliff筛选 | 两工况R2的Kc(DIR20)/Kc(BASE20) point≥1.05；与同成本最佳tuned baseline/GLOB比较仍有增量 | 初筛CI跨1为inconclusive；不宣布PASS、不自动扩大试验。 |
| B5 substantive门 | 独立确认：在同CPU budget下Kc≥最佳参照1.05且paired95%下界>1；或相同FER约束下完整time省≥15%、FER非劣margin+.01 | 只剩MSE/配置/普通EP收益，则kill新receiver中心；Trans仍开放。 |

门值是本候选的工程筛选标准，不是TCOM官方要求。不能在结果出来后改 epsilon、方向、阈值把 failure变PASS。

**J12诊断口径必须清楚。** 保留原 raw-mu J12作为连续性诊断；对 CE-only mu_tilde另做同MSE控制，不能直接沿用 raw-mu的h_I或旧分母。令各 arm输出其实际用于CE的m_A，构造matched independent m_I,A，使用同一reported variance与同一 \(\lambda_A=K(noise+\bar v_A)\) 做双方**plain refit**，定义

\[
z_A=P_\perp(h_{I,A}-h_o),\quad
u_A=P_\perp(h_{S,A}-h_{I,A}),\quad
w_A=P_\perp(h_{T,A}-h_{S,A}),
\]

\[
D_{reg,A}=\frac{\sum_f(2\Re z_A^Hu_A+\|u_A\|^2)}{\sum_f\|z_A\|^2},
\quad D_{alg,A}=R_{T,A}-R_{S,A}.
\tag{21}
\]

式(21)代数闭合，仍不依赖Q_S≈Q_I。不同arm分母不同，须同时报 \(\sum\|z_A\|^2\)、绝对 refit/channel risk、true symbol MSE；不能靠放大分母报D_reg变小。CE variance proxy(15)与true MSE的ratio单列。

independent控制复用J12的AWGN posterior-mean匹配工具。DIR的控制对独立pseudo draw应用**同一个冻结输出map**，再匹配true MSE；q/u/c来自被诊断状态，故属于条件 counterfactual，不是完全独立于Y的receiver。若匹配无法在注册的范围内达到误差≤1%，该格相关性比较标不可用；不换一个Gaussian fixture冒称原J12控制、不删该格，B2未满足。

近 neutral 的alpha≈1、创新方向几乎为零、full coefficient derivative很大、spatial error主方向与g无关，都是具体可失败情形。它们不是再加模块的自动理由。

## Closest Prior Art and Remaining Distinction

本轮读primary论文或作者/大学记录。以下只总结所查到的机制；没有穷尽全领域。`aprime-novelty-20261013.md`主要是scheduler图，不能替代反馈算法查新。

| 近邻与核验层级 [F] | 已有机制 | DIR剩余差别 [I/S] |
|---|---|---|
| Parker–Schniter–Cevher，BiG-AMP，2014；abstract/论文入口。[BiG-AMP](https://arxiv.org/abs/1310.2632) | bilinear approximate BP、有限尺寸damping；correlation regulation已在谱系内 | 不以“加Onsager到JED”为新意；用当前kernel有限一步的实方向导数，不假定IID tensor。 |
| Parker–Schniter，P-BiG-AMP，2016；全文模型/更新。[P-BiG-AMP](https://arxiv.org/html/1508.07575) | 已知tensor的bilinear参数估计，Gaussian大系统近似 | 原kernel就是此类标量近似；DIR不是其严格重推，是一条有限步feedback intervention。 |
| Minka，EP，UAI2001；原文。[Expectation Propagation](https://tminka.github.io/papers/ep/minka-ep-uai.pdf) | cavity去除重复site信息、moment matching | 外信息除法与不重复同Y不是新概念；DIR只做选定方向的局部反应正则化，不声称exact cavity。 |
| Ma–Ping，OAMP，2017，§III-B/IV-B全文。[Orthogonal AMP](https://arxiv.org/html/1602.06509) | decorrelated LE＋divergence-free NLE；posterior反应扣除已有 | DIR保留现data kernel，扣完整h→rx响应选出的一条real方向；不照搬其unitarily-invariant SE。 |
| Liu等，On OAMP，2022，abstract。[On Orthogonal AMP](https://arxiv.org/abs/2203.00224) | GS orthogonalization统一EP/turbo/AMP/OAMP | 方向正交化本身也不是新意；候选区别是可观测channel-innovation选择与有限步代价/机制检验。 |
| Wen–Yuan–Yuen–Li，MF-OAMP SP-OTFS，TVT2024；作者大学记录/abstract，非完整更新核验。[MF-OAMP](https://researchportal.hkust.edu.hk/en/publications/mf-oamp-based-joint-channel-estimation-and-data-detection-for-otf/) | SP detector/CE间传递soft information，已有OAMP JED | “SP+orthogonal feedback”无法充当区别；须补其完整公式，当前不能排除实现重合。 |
| Huang–Qiu–Shafie–Yuan，OAMP-JED ODDM，2026-06预印本；§III、Algorithm1与附录全文。[OAMP-JED](https://arxiv.org/html/2606.25420) | 两个OAMP模块交替，DF data message构造CE矩阵；用variational scalar noise传递不确定性 | **最强近邻。** DIR不替换全部LE/NLE、不全局DF；只扣一步完整tangent中的一个rank-one反应，以矩阵自由CE步实现。是否可视该框架的普通低成本近似，尚未排除。 |
| Huang–Guo–Zhang–Zakharov，MP SP-OTFS，作者全文。[SP-OTFS message passing](https://arxiv.org/html/2309.08177) | SP doubly-selective BEM联合CE/detection已存在 | AFDM/DPSS名称不是创新；候选必须增加有限成本、相关结构上的可复用结论。 |

**确切剩余候选句 [S]：**

> 从实际有限步联合kernel的residual、adjoint与precision响应构造channel-innovation方向，仅对该方向的soft-symbol回灌作有界反应扣除，并用posterior shift-risk记账，在相同表示/prior/观测与完整成本下验证其相对全局外信息的增量。

不是“首次extrinsic JED”，不是“首次SP OAMP”，不是“DF推出白噪声”，不是“只加一项即可解cliff”。定向关键词检索未定位同一公式，**未检出不等于新颖性证明**。若GLOB或合理适配的OAMP-JED覆盖全部收益，则剩余只是实现选择，不强行写成Trans方法。

## Minimal Test Plan：复用C1，不执行

### 固定资产与数据边界

**[S]** 复用 `driver_c1.py` 的physical generator/rho shim、GenieRefine、flat配置、scoring；`driver_c1i.py`的按轮输出；`driver_c1j12.py`/`driver_c1v2.py`的真投影、plain-refit、独立MSE控制；IB的Kc crossing/paired bootstrap。

`recursion_j12`硬写旧kernel，**不能原样用于DIR并宣称Q0通过**。未来adapter只复用生成/诊断；DIR state须从新kernel或独立对应递推采集。现vector route不支持record_states=True，不能计划依赖该开关；可用caller-owned test capture，成本另记。

建议公共entropy定义为ASCII `C1-DIR-B-20261013-v1`的SHA256，计算/封存留给后续获准实现；generator的C1 law/domain不变。各arm同外生块，frames0–31为机制开发，32–95为预留性能screen；该entropy是否未用需运行前核查。不是把已有640–719帧重新命名confirmation。

### B0：先验证合同，最多12个receiver smoke calls

- 两个小N纯算子fixture：含CPP wrap、非均匀DPSS幅度；手工式(3)–(7)与finite differences、real J、式(13)、式(19)。不用decoder验证数学合同。
- 同C1 frozen N1024，在下方6格各1帧，OFF与BASE20比较；再每格1个DIR20。无truth进入算法。
- verify每步实际FFT、precision floor分支、g=0初步、finite检查；用actual n_cols=K，不以L代替K。

### B1/B2：机制screen，6格×32帧×6 arms=1152 round-one rows

| 格 | SNR dB | rho | L/K | 用途 |
|---|---:|---:|---|---|
| M1 | 8 | .2 | 8/64 | 小负载、较强有益absorption负例 |
| M2 | 8 | .2 | 24/192 | 旧J12 own-error excess |
| M3 | 8 | .5 | 24/192 | rho变动/删除有益反馈风险 |
| M4 | 6.5 | .3 | 16/128 | 主cliff附近 |
| M5 | 6.5 | .3 | 28/224 | 难格、单方向不足负例 |
| M6 | 11 | .2 | 32/256 | 旧transient强格 |

arms，全部R=1、同refit、同tau、同观测：

1. BASE20：原kernel T20、damping=.3。
2. BASE40：原kernel T40、damping=.3。
3. DAMP20：原kernel T20、damping=.1，普通damping控制。
4. RAW20：式(17)–(20)新channel solver，CE反馈仍mu/v，无定向扣除。隔离列precision、solver、schedule改变。
5. GLOB20：同新solver，用正则化全局scalar外信息控制：alpha_G=mean(v+)/vr、c_G=(1−alpha_G)/[(1−alpha_G)²+.01 alpha_G²]，mu_G=mu+c_G alpha_G(mu−r)；variance同式(15)。它是已知scalar EP/OAMP结构的controlled adaptation，使用相同export-operator正则量，非完整发表OAMP-JED。
6. DIR20：唯一推荐方法，式(2)–(20)。

RAW/GLOB不人为执行无用tangent计算凑相同runtime，按实际算法计clock。DIR相对RAW的效果、相对GLOB的方向价值、相对BASE40的成本必须分开。

保存每步cheap state summaries；在固定t={10,20}及BASE40的40端点存h/mu/CE反馈。first16帧/格做matched-MSE refit诊断：每个BASE/RAW/DIR输出各own+independent两次，共576次plain ridge solves；不把诊断cost当部署receiver cost，也不隐去实验预算。

full derivative probe在first8帧/格的t={5,10,20}：沿g的±扰动，分别锁定/重算系数；固定相对幅度1e-5、以1e-6检查数值敏感性。它们是当前一步marginal/feedback probes，不重复整个coded receiver。zero raw response明确记不可判，不以0/0记通过。

transient length定义：到达对应frame BASE40 endpoint的1.10倍orthogonal-risk邻域，并在剩余保存step未离开；未达到者censored。不是把第一次短暂落入当收敛。true h只用于该离线评分。

**计算量 [D/S]：** 192个外生blocks，每block arms共140次inner update＝26,880次；正常full-rank步的transform预算70,272次（BASE20/DAMP20各41、BASE40 81、RAW/GLOB各61、DIR81）。另576个K维plain ridge solves及有限步probes。CPU小时尚未知；smoke记录每格实际完整时间后再换算，不能把IB不同L/不同shard的时间当本轮测量。

B1/B2失败即停止。保留全部error/censored/matching-failure；不通过换epsilon、增rank或增加T把这个候选变另一方法。

### B3/B4：仅机制screen通过才做负载screen

**[S]** 两个工况，rho=.3：

- 6.5 dB，L={12,16,18,20,24}；8 dB，L={20,24,28,32,36}。
- frames32–95，64帧/格，同新entropy；R=2。
- arms BASE20/BASE30/BASE40/RAW20/GLOB20/DIR20；base damping从机制阶段两个固定候选中选一个**全局值**后冻结，不逐格选；若要声称对充分调优参照，还须公平补damping=.5等开发调优。
- 共10格×64×6＝3840 rows、7680 coded rounds；192,000 inner updates，正常步494,080 transforms。高L、refit、LDPC cost另计；实际CPU预算由B0/B1 timing预测并设cap，不在本报告启动。
- 每轮记录FER/BER、LLR logloss、eps、time、FFT/NK counters；Kc按原IB linear crossing与paired frame bootstrap(B=2000)。所有frames计分。
- censored crossing只给bound；不得用点估计有限地外推。DIR20高于BASE20但低于同clock BASE30/40，B方法中心不成立。

64帧/格是初筛，**不足以认证FER非劣+.01**。若点估计有候选增量且无kill，下一步独立确认才增加新entropy/预注册帧数并完成power；不能把初筛best-cell升级成确认。还需完整合理适配OAMP-JED/EP近邻，才能回答公开方法比较，而非仅靠GLOB消融。

不扩真实support acquisition、第二码、N scaling到第一轮screen。genie成功只支持known-support候选；Trans/部署主张最终仍须对应范围证据。

## Boundaries and Non-Claims

- [D] 证明的是系数冻结的单方向局部反应，以及一个固定quadratic surrogate下降；非全环路去相关、非C1 posterior最优、非收敛/稳定性。
- [S] 减少harmful image、缩短实际transient、移动同成本Kc，是待测预测；没有结果。
- [F/I] 原kernel的scalar能量近似与既有Onsager继续限定data branch。换channel solver带来的收益必须由RAW分离，不能冒称都是correlation correction。
- [D/I] 只去掉一条方向可能保留有益absorption，也可能去掉有益feedback；没有“去相关必降风险”定理。
- [F] EP/OAMP、SP OAMP-JED都已有。此报告给的是可实现且可否证候选，不是创新认证或Trans达标。
- [F] 本轮只写本文件；没有implementation、tests或新仿真证据。

## Open Risks

1. full coefficient derivative破坏式(13)的实际衰减；B1直接否证。
2. recent innovation不覆盖true image，或alpha≈1恰占主导；不自动升级多方向补救。
3. posterior-shift variance与true MSE不校准，有色residual/high-order design相关仍强；B2同时报绝对风险。
4. curvature vh proxy与保留的data AMP branch不相容；可能放大LLR过信或新transient。
5. 额外transforms/contractions吃掉收益；只胜under-budgeted T20则kill方法中心。
6. scalar/global EP或2026 OAMP-JED完整适配已解释全部增量；只剩实现差异。

## Caveman summary

- 一个候选：沿完整h→rx响应，定向扣软符号回灌。
- 不再加scalar Onsager；替换channel score，data/decoder均值保留。
- 局部衰减可证；实际去相关、MSE、FER收益未证。
- rank-one，矩阵自由；每步4FFT，成本约翻倍待测。
- RAW隔离solver；GLOB隔离普通外信息；BASE40隔离预算修复。
- J12 excess不降、同成本不胜：kill B方法中心。
- 2026 SP OAMP-JED近邻很近；新颖性未成立。
- 只写报告；无代码、SSH、运行、git。
