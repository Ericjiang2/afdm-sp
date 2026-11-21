# TASK KR — 核心接收内核独立只读审查

日期：2026-10-13。任务：`.trellis/tasks/10-08-doppler-cluster`。

**裁决：未发现足以判废现有 C1 flat 结果的内核错误。flat 数值更新与冻结核在同一 general-tap operator 上代数等价；“每处变化均标 # VEC、其余完全相同”不成立。非等模 DPSS 的输出方差、gain precision 仍用了冻结指数路径的能量替代式，不能宣称精确的通用基 P-BiG-AMP 推导。另有 TapChannel 系数接口缺陷，但所读 C1 接收/评分路径绕开了它。**

本次仅源码静态比对、手工代数推导。未 import/执行接收机、未跑测试/仿真、未 SSH、未使用 git。下列测试均为建议，未执行。文档中的既有 PASS 不当作本次运行证据。

证据标签：公式等价为**代数结论**；行号行为为**源码事实**；“当前结果不受影响/没有污染证据”依据所读调用链，均为**静态推论（inference）**，不是运行回放保证。未用代码之外的假设推断性能变化方向。

源文件简称：

- `D` = `experiments/headroom_ladder_20261008/dpss_rx.py`。
- `T` = 同目录 `tapchannel.py`；`C` = `driver_c1.py`；`I` = `driver_c1i.py`。
- `F/twofft.py`、`F/native_twofft.py`、`F/messages.py`、`F/physical.py` = 用户指定冻结副本。根目录：`/private/tmp/claude-501/-Users-guoyikun-Downloads-share-claode-birain-my-vault-00-Inbox-AFDM-channel-estimation/dc21a6d1-d6a2-4ff9-92f7-55c319da1343/scratchpad/frozen_src/`。

已读任务元数据、相关 STATE、`research/c1-scalar-closure.md`、`research-assets/res-20261009-01.md`。辅助追踪限于 wrapper、现有单测源码及 trace 消费点；未审查 `--shuffle-arms`、`c1e_predict.k_cross`。用户给出的真 tap operator 相对误差 `8.7e-16`、refit gains 重算相等，作为**用户提供证据**，未独立复跑。

## 数学先行：Q1 冻结等价性

### P 确实等于 K，非 distinct-delay 数 L

`F/physical.py:101–102`：`Channel.p = len(self.delays)`。`TapChannel` 未覆盖该属性（`T:26–33`）。`D:228` 每个 tap 重复 delay 共 D 次；`D:311–337` 用同一个 `idx` 选 M、delays、tau、gains，构造含 `Cs=len(idx)` 个 delay 槽的信道。因此

\[
P=c.p=C_s=\sum_{l\in\mathrm{kept}}D_l.
\]

C1 flat：`C:191–207` 全部 genie delays，每 tap `D=8`，每轮 `E_l=1/L`；`C:217` 把 eigenvalues 换成 1；冻结配置 `mode=full, drop=0`，`C:319` 为 `SPg_flat` 置 `kappa=1`。各 tap 能量正且相同，`D:308` 全保留。因此

\[
P=K=8L,\qquad
\tau_{l,d}=\frac{\kappa E_l}{D_l}=\frac1{8L}=\frac1P.
\]

合法 `1<=L<=101` 时最小 tau 为 `1/808`，远大于 `tau_floor=1e-9`，floor 不介入。`SPg_flat03` 则为 `0.3/P`，**故意不等于**冻结 `1/P`；Slepian arm 也非等价控制。

### 逐步归纳：数值更新等价，整个返回 dict 不等价

固定同一 `c`、同一已安装的 `twofft.TimePathOps`、相同输入/参数，限制冻结函数 `gain_mode='joint', observation_domain='time', record_states=False`。令冻结标量 gain variance 为 \(u_t\)，vector 核为 \(\boldsymbol u_t\)。初始化：

\[
\tau=1/P,\quad u_0=1/P,\quad
\tau_d=1/P,\quad u_{0,d}=1/P.
\]

假设迭代 t 开始时所有数值状态相同，且 \(u_{t,d}=u_t\)。则

\[
\sum_d u_{t,d}=P u_t,
\]

使 bar、vp、output residual/precision、damped x/h/B、vr/vq、rx/rh 相同。`marginal` 相同，故新 x/v 相同；且

\[
u_{t+1,d}=\frac{(1/P)v_q}{1/P+v_q}=u_{t+1},\qquad
h_{t+1,d}=\frac{(1/P)r_{h,d}}{1/P+v_q}.
\]

归纳成立。`extrinsic/app/mu/variance/gains`、最终 `gain_variance` 数组、迭代数及 time-domain FFT 计数相同。

边界：这是实数/复数精确算术证明。`vh.sum()` 与 `P*vh`、`sv*vsum` 与 `sv*P*vh` 的浮点归约/乘法顺序不同，不能据此声称 bit-exact。现有 `unit_check_m2.py:126–134` 比五个数值数组，用相对容差，未比完整 trace，也未证明 bit-exact。

**此等价对象是冻结 `scalar_joint` 配合同一个 GeneralTimePathOps。** 原始未安装的 `F/TimePathOps` 会把 DPSS 信道的 placeholder dopplers=0 当指数路径，不能表达 M。整个 DPSS refit 接收机也不等于冻结 `time_refine` 接收机；refit 替换本来就是显式设计。

### line-by-line 对照

下表覆盖冻结函数所有语句组；拆行、空格不计语义变化。`F` 行号指 `F/twofft.py`。

| 冻结行 | D 行 | 比对结果；# VEC 情况 |
|---|---|---|
| 30–36 | 106–111 | 新增 tau 参数；移除 gain_mode/record_states/domain 参数；局部 imports。接口变化未标；模式专门化本身不改变被比较路径。 |
| 37 | 112–115 | y/pilot/n/P 同；新增 tau ndarray 转换未标。 |
| 38 | 116–117 | observation/noise 检查相同。 |
| 39 | 118–119 | iterations/damping 相同；模式校验换 tau shape/正值校验；有标。 |
| 40 | 120–121 | finite observations 相同。 |
| 41–44 | 122–129 | prior、alphabet、moments、x 初始化相同。 |
| 45 | 130–131 | 同一模块 TimePathOps；仅保留 time 分支；未标，但本次专门化无数值变化。 |
| 46 | 132–133 | h copy 相同；scalar tau/vh 初始化改外部 vector tau/vh；vh 行有标。 |
| 47 | 134–141 | 所有数值状态初始化相同；删除 states=[]，未标。 |
| 48–50 | 142–147 | loop、IDAFT、B、vx、ex、channel_norm 相同。 |
| 51 | 148–150 | P*vh 换 vh.sum()；新 vsum 行有标，bar/vp 使用该量。 |
| 52–54 | 151–156 | damping、bar0/vp0、z 相同。 |
| 55 | — | 删除 af-domain z 旋转；本次 time 分支原本不执行。 |
| 56–57 | 157–159 | ph、s、sv 相同。 |
| 58 | 160 | st=s；删除未使用的 af 分支。 |
| 59–63 | 161–168 | damped xb/hb/Bb、precision、vr/vq、adjoint 相同。 |
| 64 | 169 | sv*P*vh 换 sv*vsum；有标。 |
| 65–66 | 170–172 | rh、marginal、x 相同。 |
| 67 | 173 | joint denoiser 方差变逐列；有标。 |
| 68 | 174 | joint denoiser 均值变逐列；有标；删除 fixed-mode gate。 |
| 69 | 175–176 | 数值 finite 检查相同。 |
| 70 | 177 | **gain_variance 从本轮更新后的单列 vh，变本轮开始时的总和 vsum；未标。** data_variance 仍为更新后值。 |
| 71–76 | 178–182 | 其余 trace 相同；FFT 常数固定为 time 模式的 2。 |
| 77 | — | **删除 record_states 状态捕获，未标。** |
| 78–80 | 183–184 | 最终 gain_variance 直接返回 vector，flat 时等于 np.full(P,vh)；删除可选 states；直接 return。未标。 |

因此：“所有数值推断变化都被聚焦于 vector prior”基本成立；“所有变化都标了、其他内容原样”严格不成立。trace 与状态捕获是实际接口差异，见下方 minor findings。

## Q2 通用基的正确收缩形式

### 定义与归一化

令 S 为 unitary IDAFT，\(\Pi_l\) 为循环 delay shift，\(C_l\) 为 CPP wrap phase，\(m_d\) 为一个 DPSS 调制列。time-domain 双线性算子：

\[
U_d=\operatorname{diag}(m_d)C_{l_d}\Pi_{l_d}S,
\quad B_d(x)=U_dx,
\quad H(h)=\sum_d h_dU_d.
\]

`D:61,69` 的 norm=2 DPSS、sqrt(N) 放大给出同 tap \(M_l^HM_l=N I\)，故

\[
q_d:=\|U_d\|_F^2/N=\|m_d\|^2/N=1.
\]

**不等的是 B(x) 列能量，不是 M 的列范数。tap power 位于 tau/h 中，未额外乘进 M。** `E_l lambda_d` 不能再当作列范数权重乘一次。

S 每个元素模为 \(1/\sqrt N\)，CPP phase 模为 1，故 \(|U_d[k,j]|^2=|m_d[k]|^2/N\)。同 delay 的 operator Frobenius Gram 为 \(m_i^Hm_j/N\)，不同 delay 的 trace 为零。因此

\[
R_{ij}=\mathbf1_{l_i=l_j}m_i^Hm_j/N,
\quad \|H(h)\|_F^2/N=h^HRh.
\]

`T:112`、继承的 `F/TimePathOps.power:25–28` 已实现这一精确物理范数。**channel_norm 不缺 eigenvalue/tap-power 权重；再加会重复计能量。**

### Gaussian gain denoiser：正确

若伪观测 \(r_{h,d}=h_d+\eta_d\)，\(\eta_d\sim CN(0,v_{q,d})\)，独立 prior \(h_d\sim CN(0,\tau_d)\)，配方得

\[
\widehat h_d=\frac{\tau_dr_{h,d}}{\tau_d+v_{q,d}},\qquad
v_{h,d}=\frac{\tau_dv_{q,d}}{\tau_d+v_{q,d}}.
\]

`D:173–174` 对 shared vq 正确。问题位于伪观测方差的能量近似，而非 denoiser。

### pseudo-variances：输出增益不确定性须用 B 列能量

保持冻结的 scalar symbol variance \(v_x\)，独立 gain variance \(v_{h,d}\)。输出矩的 scalar average 应为

\[
\bar v_{\!*}=v_xh^HRh+\frac1N\sum_dv_{h,d}\|B_d(x)\|^2,
\qquad
v_{p,\!*}=\bar v_{\!*}+v_x\sum_dv_{h,d}q_d.
\]

若保留实际非均匀 symbol variances，第一项应为 \(N^{-1}\sum_jv_j\|H_{:,j}\|^2\)，而非 \(v_x\|H\|_F^2/N\)；这是冻结 scalar symbol closure 的既有近似。

对指数路径 \(|m_d[k]|=1\)，\(U_d\) unitary，\(\|B_d(x)\|^2=\|x\|^2\) 精确。因此冻结 \(P v_h\|x\|^2/N\) 以及 vector 化后的 \((\sum_dv_{h,d})\|x\|^2/N\) 都成立。

DPSS 则

\[
\beta_d(x):=\|B_d(x)\|^2
=\sum_k|m_d[k]|^2|(Sx)[k-l_d]|^2,
\]

一般不等于 \(\|x\|^2\)。`D:149` 是额外的等能量/各向同性替代。`D:150` 的交叉不确定性项正确，因为 q_d=1；不需 B 列能量再加权。

### gain precision：逐列形式，或明确保留平均近似

若输出 precision 仍为 scalar sv，P-BiG-AMP 的列收缩形式为

\[
J_{h,d}=sv\|B_d(x_b)\|^2,\qquad
v_{q,d}=1/\max(J_{h,d},10^{-12}),
\]

\[
r_{h,d}=h_d+v_{q,d}
\big(B_{b,d}^Hs-h_{b,d}\,sv\,N v_xq_d\big).
\]

`Bb=B(xb)` 由 B 对 x 的线性和同一 damping 递推成立。h 的 Onsager 系数 \(N v_xq_d=Nv_x\) 因归一化仍正确，不能拿 \(\beta_d\) 替换这一系数。

若选择**一个 shared vq**，相应能量平均是 \(J_h=sv\,P^{-1}\sum_d\beta_d(x_b)\)。`D:165` 保留 \(sv\|x_b\|^2\)，连该平均都未显式计算。它是指数路径时的精确恒等式、DPSS 时的标量能量近似。shared vq 本身可作为算法近似，但不能宣称与通用基逐列收缩严格相同。

### data precision / Onsager：现有 scalar 形式有依据

scalar data precision 的平均是 \(J_x=sv\|H(h_b)\|_F^2/N=svh_b^HRh_b\)，`D:164` 正确。逐符号版本为 \(J_{x,j}=sv\|H_{:,j}(h_b)\|^2\)；冻结核本来就用平均。

data Onsager 的 diagonal contraction 是

\[
sv\sum_dv_{h,d}\sum_k|U_d[k,j]|^2
=sv\sum_dv_{h,d}q_d
=sv\sum_dv_{h,d}.
\]

故 `D:169` 以 \(\sum_dv_{h,d}\) 替 \(Pv_h\) 正确。这里不该用 \(\beta_d(x)\)，也不该用 tap energy 再加权。此结论针对该 AMP diagonal contraction；未宣称整套标量迭代为精确 posterior 推断。

**回答 Q2：vector prior 与 Gaussian denoiser、归一化后的 data Onsager/交叉 variance 一致；对 DPSS 的输出 gain-variance 项和 gain precision，不是精确的通用基推广。flat arm 不受 vector 化改变影响，因为 Q1 等价成立。DPSS 能量近似由双方共同继承；它限制理论解释，不能据此抹掉已测该接收机的 flat FER/MI/轮数结果。非均匀 tau 与各 \(\beta_d\) 的相关性对 Slepian arm 的影响方向/幅度，本次未测，不作推断。**

## Q3 Refit / Design / detector 一致性

### 基、顺序、CPP 相位：通过静态核对

`D:222–237` 构造

\[
B_{k,(l,d)}=(S(p+\mu))[k-l\bmod N]\,
\begin{cases}e^{2\pi i c_1(N^2+2N(k-l))},&k-l<0,\\1,&\text{otherwise}\end{cases}
\,m_{l,d}[k].
\]

这与 `F/TimePathOps:16–21`、`T:_cp:50–53`、`T:110–112` 的 delay/phase 顺序相同；与 `F/physical.daft:87–90` 的正 Doppler、IDAFT/DAFT 符号一致。DPSS 调制作用于**输出时间 k**，未错移到输入时间 k-l。

refit 用 `Y=S y`，检测器也用 `Y=S y`。同一 `des.M[:,idx]`、`des.delays[idx]`、h2、tau 传入 detector；keep 保留原 tap 次序，各 tap 的 D 列未重排；`D:329–334` 只重建 slice，使下一轮 gs 与 M 对齐。没有按 P/L 混排、CPP 号反、基归一化错位的证据。

**但一致性只对 detector 的 `TimePathOps.responses_time/adjoint_time/power` 成立。TapChannel 的公开 apply/adjoint 不适配系数表示，见 major M2。** 用户给出的真 taps 物理闭合检查使用实际 tap 序列，不能反证此系数接口缺陷。

### Ridge：所声明白噪声模型下正确

`D:240–246,279–281`：\(Q=B^HB+s^2\operatorname{diag}(1/\tau)\)，\(h=Q^{-1}B^HY\)。对应 prior \(CN(0,\operatorname{diag}\tau)\)、有效白噪声 \(s^2I\) 的 MAP/LMMSE。objective `D:338` 为该二次目标最小值 \(Y^HY-b^HQ^{-1}b\)，一致。

`s2=noise+mean(v)*sum(E_l)`（`D:323`）是 scalar data-uncertainty approximation：用 \(Cov(x-\widehat x)\approx\bar vI\)，平均 residual power 为 \(\bar v\|H\|_F^2/N\)。真实时间残差通常有色；自生 soft symbols 也不保证与残差/设计独立。源码/docstring 明确没有冻结 Gamma。因此可以称**有效白噪声 ridge**，不能称真实自反馈观测模型的精确 LMMSE。

flat 两轮 \(\sum E_l=1\)，故 \(s^2=noise+\bar v\)，ridge penalty 为 \(s^2K I\)。flat03 为 \(s^2K/0.3\)。二者差别显式且与各自 prior 一致。

### first_round_energies：去掉 noise variance bias，保留 shrinkage bias

`D:287–296` 两遍：第一遍 total=1，第二遍 total=第一遍非负能量之和（总量下限 `1e-6` 仅用于计算下一遍 s2）。令 \(G=B^HB,Q=G+s^2I,A=Q^{-1}G\)。若条件白噪声模型成立，则

\[
\widehat h=A h+Q^{-1}B^He,\quad
Cov(\widehat h\mid h)=s^2Q^{-1}GQ^{-1},
\]

正是 `D:292`。减掉其 tap-block trace 后，未截断期望是 \(\|(Ah)_l\|^2\)，**不是** \(\|h_l\|^2\)。截零和第二遍随机 plug-in 又改变期望。源码称“estimator-variance bias removed”可接受；不能据此称原 tap energy 的无偏估计。flat 分支 `C:195–200` 不执行这套估计，故这一局限只属 Slepian/M2。

round>=2 用 \(E_l=\|M_lg_l\|^2/N\)（`D:269–270`）是正确的点估计 tap power；不是 posterior expected power，未加 gain variance。flat 分支再固定回 1/L。

### tau / drop：C1 路径一致

未触 floor 时，`D:317` 使每 tap \(\sum_d\tau_{l,d}=\kappa E_l\)；lambda 是集中度先验形状，未作为 modulation 振幅。floor 可使 prior 总量略增，日志记录实际 tau_sum；flat 路径 floor 不触发。

`D:308–311` drop 按 tap E 比例筛选；若全没过门则 argmax 保留。Etot=0 时 0>=0，所以所有零能量 tap 都保留，再由 tau floor 保持正 prior；这不违反“最强者始终保留”，但不意味着只保留一个。C1 frozen drop=0，全 support 保留。

若将来启用 positive drop，`D:323` 的 s2 只计 kept E，未计 dropped tap 残差；它不是完整残差方差模型。**这是该可选配置的局限，现有 C1 drop=0 不受影响。** 无须为本次结果扩展算法。

## Q4 Routing / IntervenedRefine / 状态

- `vector_prior` 只改 `native.scalar_joint`，有 prior_var 才走 vector；缺属性/值为 None 则完整转发原函数（`D:190–199`）。当前 native 调用全用 named pd/prior/iterations/gain_mode/record_states（`F/native:22`），没有 positional 模式错位。非 joint/time 显式报错，不偷偷降级。
- flat channel 总携带 tau（`D:337`），故进入 vector 分支；这是已证明等价的路径。`gain_mode='fixed'` 的 FROZEN 则故意不进入该 context（`I:151–157`），调用冻结 kernel 的 fixed 分支。
- `D:201–205` 在异常退出时恢复 native.scalar_joint；`C:212–222` 在 refit 异常时恢复 Design。wrapper `_hooks` 同样 finally 恢复 front/refine（`experiments/tf_production_gap_audit_20260922/interventions.py:60–73`）。异常后没有所读串行控制流中的 patch 泄漏证据。
- 每帧/arm 新建 refiner（`C:269`、`I:148`）；prev/log/snaps/cache 均实例属性。状态只在本 arm 的 coded rounds 间传递。`native.receive` 每调用重新 pilot_front，每个 detector 调用新建 s/sv/damping 状态。
- `_BASIS` 仅缓存确定性 DPSS；tap_columns 算新 M，Design concatenate 新 lam；FlatDesign 用 ones_like 替换本地 lam，未写缓存。`_CLS` 仅缓存类。固定 C1 参数 `(N=1024,W=2.5,D=8)` 下未见估计状态缓存跨帧。
- `_BASIS` key 对 W 四舍五入 9 位，而生成用原 W（`D:57–63`）；不同 W 可能共用缓存。仅适用于间隔小于该精度的不同 W 请求；C1 full 使用相同 W，不影响。未证明实际 adapt 请求发生该碰撞。
- `install_general_taps` 的 TimePathOps 替换是持久且幂等；plain Channel 通过 super 完全走原分支（`T:90–114`）。不属于异常未恢复的估计状态。缓存/patch 并不支持同进程多套 frozen module 热切换；本次单 module、单线程调用不需要该能力。
- WARM 只在第一次 refit 替换 gains（`I:108–129`），M/delays/tau 原样保留；true coefficients 为同一 tap 基的 LS 投影。后续 gs 来自 detector，后续 refit 重新估计；真值仅进入声明的 warm intervention。`mode='full'` 无注入，WARM_0 在精确算术下相同。
- FROZEN 缓存的是 channel/detail，不会被 detector 原地改 gains：冻结 kernel `h=c.gains.copy()`，fixed 分支不更新 h；同一 snap 重复引用仅用于同 arm 的不变评分。detail objective 保持 pilot-only 数值符合该 intervention，不能误读成每轮新 soft-data objective。
- `record_states=True` 被 vector router 静默移除，vector return 无 states，native 随后读 `o['states']` 会 KeyError；现有默认 C1 调用 record_states=False。见 minor m2。
- 模块 patch 不保证并发安全。wrapper 的锁在 `_instrumented` 内，而 `vector_prior` 在外层先 patch；Design patch、安装 TimePathOps 也非线程局部。并发/不按栈顺序退出可破坏恢复。但源码明确“一进程一 shard、single thread”，未见 C1 实际串行路径发生泄漏。此为接口边界，非已发生污染。

## Findings：按严重度

### critical

无。未建立任何 `invalidating` 结论。

### major M1 — DPSS 能量近似未随通用 modulation 收缩

**位置：** `dpss_rx.py:149`、`:165–170`；参照 `F/twofft.py:51,61–65`、`tapchannel.py:111–112`。

**证据：** 上述 Q2：\(\beta_d=\sum_k|m_d[k]|^2|x_t[k-l_d]|^2\) 一般不等于 \(\|x\|^2\)。输出 gain variance 的正确 scalar contraction 为 \(N^{-1}\sum_dv_{h,d}\beta_d\)，逐列 precision 为 \(sv\beta_d(x_b)\)；源码用了 sum(vh)*ex/N 和 shared sv*exb。channel_norm、data Onsager、h Onsager 的归一化没有漏权。

**后果：scoped。** 限制“通用 DPSS 基下严格推出的 vector-prior AMP”说法；非均匀 Slepian prior 结果应按此具体近似算法解释。flat 在同一 operator 上仍复制冻结更新，**不受 vector 化影响**；现有 flat FER/MI、预算/起点干预数值不因这一比对被判废。若把它们解释为精确通用基 AMP 的性质，该解释不成立。对性能的改变量/方向未测。

**最小确认测试：** N=32、一个 delay、3 个 norm=2 DPSS 列。取 time-domain x_t 为选定 k 的单位脉冲，AF x=DAFT(x_t)。直接算 \(\|B_d\|^2=N|v_d[k]|^2\)，选 k 使各值不同；比较 true weighted bar/Jh 与当前式。不需 decoder 或随机新帧。另用所有模长为 1 的指数列，应严格归约到冻结能量式。

### major M2 — TapChannel.apply/adjoint/tap_matrix 忽略 coefficient gains

**位置：** `tapchannel.py:56–82,85–87`；调用方 `dpss_rx.py:335–337`、`driver_c1i.py:115–117`。

**证据：** apply 的 coef 仅为 cp*tap_mods，未乘 ch.gains[i]；adjoint 未乘 gains[i].conj()。make_tap_channel 把完整 tap 序列放入 mods、gains=1，因此那一种表示正确；DpssRefine 则 mods=M、gains=h2，公开 apply 应计算 \(\sum_dh_dU_dx\)，实际计算 \(\sum_dU_dx\)。即使 h=0 也可能非零。继承的 regressors/其他指数专用方法也未改成通用 M；不能把该类当完整的 physical.Channel 替代品。

**后果：none（所读 C1 接收/评分路径）；scoped（该公开接口）。** scalar_joint 使用独立 TimePathOps，并以 B@h、adjoint_time(h,s)、power(h) 正确乘 gains，未调用 ch.apply。native loop/wrapper 不调用这些公开算子。eps_of 直接 M@gains；现有 `unit_check_c1.py:138–141` 先把 M@h 折成实际 taps，再 make_tap_channel(gains=1)，所以也避开了错误。真 tap 序列的 8.7e-16 物理闭合不会检测这个 coefficient-channel 缺陷。

**最小确认测试：** 一个非零 modulation 列、合法 delay、ch.gains=[0]、非零 x。检查 ch.apply(x)=0、ch.adjoint(y)=0；当前实现一般失败。再以 gains=[2+1j] 比较 `DAFT(TimePathOps.responses_time(IDAFT(x)) @ gains)` 与 ch.apply，并做内积 adjoint 检查。最小接口修正为 coef 乘 gains/共轭 gains；本次未编辑。

### minor m1 — trace.gain_variance 改了量纲与时间索引，且未标 # VEC

**位置：** `dpss_rx.py:148,173,177`；`F/twofft.py:67,70`。

**证据：** vector trace 记 \(\sum_dv_{h,d}^{\mathrm{in}}\)；冻结 trace 记 \(v_h^{\mathrm{out}}\)。即使 flat，既非相同单位也非相同 iteration stage。最终返回 gain_variance 数组仍正确。trace 中 data_variance 是 out，channel_norm/bar 等是 in/damped，整行不是统一时刻 posterior state。

**后果：scoped（诊断与等价性声明）；none（detector 数值输出）。** flat FER/MI 不读此字段计算推断。不能把 vector trace 直接与冻结 trace 对比，不能以末行该字段代称终端 posterior 总方差。旁读 `driver_c1jfp.py:57–58` 将此字段映射为 V；其自编递推同时区分输入/输出状态，此处不据字段名称推断其已有结论失效。

**最小确认测试：** flat tau=1/P，只迭代 1 次；冻结 trace 方差为 \((1/P)v_q/(1/P+v_q)\)，vector trace 为 1，返回数组总和则为 \(P\) 倍冻结 posterior 方差。分别断言 in/out、per-column/total，而不是整 dict 相等。

### minor m2 — record_states 被丢弃，违反冻结 receiver 接口

**位置：** `dpss_rx.py:198–199,183`；`F/native_twofft.py:22,34`。

**证据：** router 无论 True/False 都删除 record_states；native True 分支要求 o['states']。有 prior_var 的调用会在 detector 返回后抛 KeyError。缺 prior_var 时 delegate 原函数，未受影响。

**后果：none（默认 C1）；scoped（状态捕获路径）。** 无 silent numerical divergence；是状态捕获请求先被静默忽略、随后失败。未看到所读默认 C1 性能运行打开此开关。

**最小确认测试：** 在 vector_prior context 中，以 refine_override 返回一个 vector-prior channel，native.receive(..., record_states=True)，预期获得与迭代数同长的 inference_states；当前返回路径 KeyError。直接调用 router也可检查 states 缺失。最小边界修正可为显式拒绝 True；本次未编辑。

### note N1 — EB 与有效噪声均为声明的近似

**位置：** `dpss_rx.py:283–296,317–323`；`driver_c1.py:195–207,217`。

**证据：** noise-debias 后仍有 ridge shrinkage bias；s2 采用白化/独立 residual surrogate；tau floor 改 prior 总量；drop>0 忽略 dropped residual。见 Q3。没有再乘 tap power 的漏项，也没有在 C1 flat 中偷偷估 E。

**后果：scoped（Slepian EB/可选 drop 的统计解释）；none（flat kernel 等价）。** 现有 C1 drop=0；EB debias不作用于 flat。不能用“无偏 tap 能量”“真实模型精确 LMMSE”强化声明。

**最小确认测试：** 一列 B、固定真 h，条件白噪声方差 s2。解析期望 `|hhat|²-var = |G/(G+s2)|² |h|²`，即可证实 shrinkage bias；无需 Monte Carlo。检查 flat 两轮 E 均 1/L、s2=noise+mean(v)、tau=1/(8L)。

### note N2 — 当前串行路径无跨帧/arm 泄漏证据；并发不在合同内

**位置：** `dpss_rx.py:52–69,187–205`；`driver_c1.py:212–222,269–273`；`driver_c1i.py:101–129,148–157`；`tapchannel.py:16–34,90–114`。

**证据：** fresh refiner + per-call numeric state；两处临时 patch 均 finally 恢复；basis/class 缓存不含估计量。TimePathOps 持久安装对 plain channel 明确 delegate。wrapper 锁不覆盖 vector context 的 patch 时段；缓存 W rounded key 是独立的精度边界。

**后果：none（当前 full、单线程 C1）；scoped（并发/近精度 W 输入）。** 未建立实际污染。没有将潜在并发交错说成现有错误。

**最小确认测试：** 保存 native.scalar_joint 和 D.Design identity，在 vector context、flat refit 内各注入一个异常；退出后断言 identity 恢复。顺序重复两个 frame/arm，每次 fresh refiner，交换调用顺序比较数值输出；仅列为后续验证，不重审已审的 driver flag。缓存问题则用两个 key-round 后相同、实际不同 W 的调用，比 uncached basis；C1固定 W 无此需求。

## 审查边界与结果影响

| 对象 | 本次结论 |
|---|---|
| SPg_flat，FULL_Rn，后续 flat refit 的 WARM | 同 operator、同输入下冻结数值更新等价；未发现判废理由。浮点 bit-exact 未证明。 |
| SPg_flat03 | prior scale=0.3/P 的显式控制，故不与冻结 1/P 相等；不是路由泄漏。 |
| SPg_slep / M2 EB | Gaussian denoiser正确；能量/噪声近似需限定；效果大小与方向本次未复测。 |
| FROZEN | 直接冻结 fixed kernel、同一正确 TimePathOps；缓存/gains 不原地漂移。该 arm 显式更改 refit与gain更新两处，不是单变量解释。 |
| flat C1 实测返回图/预算/注入起点结果 | 可继续解释为该具体标量近似接收机的测量；本次未重算 raw rows，不认证那些统计计算。 |
| “原样复制全部返回信息”“精确通用基 AMP”“无偏 EB 能量” | 不支持，须收窄表述。 |

**KR 结案范围：源码/代数审查完成；无需本轮改核、SSH 或新仿真。最小测试用于确认具体问题，不是已经取得的运行证据。**
