# PD1-Q Part A：已执行接收机的主方程对照

范围：只对 `2d130b4d` 的 `experiments/sp_afdm_native_joint_20260921/src/{twofft,native_twofft,native_controls}.py`、冻结基线 `31d5ec0d` 的 `messages.py` / `decoder_messages` 以及既有 D252 保存状态作实现对照。这里的等式是**实际执行映射**，不是新算法推导、共同 ELBO 或原作者代码的逐行复现。固定主臂为 `TF_J20_R2`：两轮、每轮二十次、阻尼 `β=0.3`、soft 物理重拟合、LDPC 上限 50；Part A 不改变它。

记 `N` 为符号数、`P` 为本轮重拟合后的物理路径数，`x=pilot+μ`，`v_x=mean(v)`，`h` 为路径增益均值，`v_h` 为传播的**标量**增益方差，`B(x)` 为时域路径响应矩阵，`R` 为路径内积矩阵，`σ²=observation['sigma2']`。上标 `pre/post` 指同一次 inner 迭代更新前/后，不指 coded round。

| 环节 | 执行的顺序与等式 | 口径 / 不可替换的含义 |
|---|---|---|
| 输入、先验 | `receive` 仅接受 `y,pilot,sigma2`；pilot-only `pilot_front` 给初始路径、`μ=0,v=0.5,prior=0`。每次 `scalar_joint` 从重拟合的 `c.gains` 起步，`τ=1/P`，joint 的 `v_h^pre=τ`；POINT/FIXED 为 0。 | `τ=1/P` 是 inner 零均值复增益先验方差。真路径、真码字和 `H_true` 不进入在线函数。`c.gains` 是初始化，不是额外的真值或独立增益观测。 |
| 前向与输出方差 | 先用 **pre-update** `x,h,v_x,v_h` 算 `B(x), z=B(x)h`；`bar_raw=v_x·hᴴRh + P v_h ||x||²/N`，`vp_raw=bar_raw+P v_h v_x`。除首迭代外，`bar,vp` 各自以 `β raw+(1−β) previous` 阻尼。 | `bar/vp` 的原始增益不确定性项与重拟合 Gamma 不是同一量。保存的 `channel_norm_factor` 对应本次 pre-update `hᴴRh`。 |
| 输出校正与精度 | `ph=z−s_old·bar`；`s=β(Y−ph)/(σ²+vp)+(1−β)s_old`；`sv=β/(σ²+vp)+(1−β)sv_old`。时间实现中 `Y=IDAFT(y)`，`st=s`；AF 对照把 `s` 逆变换后用于同一伴随。 | 输出方差先阻尼，随后更新 `s/sv`。这是实际固定阻尼次序，不应写成一次未经阻尼的似然精度。 |
| barred means 与伪观测 | **输出更新之后、当前 `x/h` 后验更新之前**，`xb=βx+(1−β)xb_old`，`hb=βh+(1−β)hb_old`，`Bb=βB(x)+(1−β)Bb_old`。`α_x=sv·hbᴴRhb`，`α_h=sv||xb||²`；`vr=1/max(α_x,1e−12)`，`vq=1/max(α_h,1e−12)`。`rx=x+vr[DAFT(A(hb)ᴴst)−xb·sv·P·v_h^pre]`；`rh=h+vq[Bbᴴst−hb·sv·N·v_x^pre]`。 | 两项 reaction 分别使用 **barred** `xb/hb`，不能把未阻尼 `x/h` 代回代码；`vr/vq` 都有精度下限，不能宣称无条件精确倒数。记录的 `vq/vr` 属于本次更新，`v_x`/`v_h` 原始 scalar trace 属于 post-update。 |
| 后验与显式控制 | QPSK `marginal` 在 `rx−pilot` 上融合当前 code prior，返回 `extrinsic=APP−prior` 与新的 `μ,v`；`x_post=pilot+μ`。joint：`v_h^post=τ vq/(τ+vq)`；POINT/FIXED：传播 `v_h^post=0`。joint 和 POINT 都执行 `h_post=τ rh/(τ+vq)`；FIXED 在 inner batch 内保持 `h_post=h_pre`，但仍计算 `rh/vq`，外层 refit 不冻结。 | POINT 仅抑制**传播方差**，没有关闭增益均值更新、gain pseudo-variance 或 posterior shrinkage。POINT–FIXED 才隔离 inner 增益均值更新；TF–FIXED 同时改变两件事。 |
| 每轮 LDPC / 下一轮 CE | 每轮恰一次 `decoder_messages(code, clip(detector_extrinsic,−20,20), maxiter=50)`。实际 `incoming_llr` 是这个已裁剪 extrinsic；LDPC `raw_app=incoming_llr+raw_check_extrinsic`。下一轮 detector prior 为 `clip(raw_check_extrinsic,−20,20)`，下一轮 CE 的 `μ,v` 取 `moments(clip(raw_app,−20,20),1−ρ)`；`s['gains']` 取本轮 joint 推断均值。 | APP 不再叠加到 detector prior；check message 是替换先验，不是额外重复的一次 decoder。APP moments 是同一观测的 coded feedback，并非独立外信息。两轮的 decoder input、APP、check 与 decoded checkpoint 均由 producer 保存。 |
| coded round 模型重置 | 下一轮先用观测、当前 APP moments 与推断增益执行 `time_refine`，再**重新调用** `scalar_joint`。因此新模型下 `s=0,sv=0,Bb=None,bar0/vp0=None`，`xb/hb` 从新 `x/c.gains` 起步，joint `v_h=1/P_new`；code prior 与 CE moments 由前轮传入。 | 两轮不是一个不断延续的 AMP inner 轨迹；`v_h^pre=1/P` 的启动瞬态在每轮都出现。D252 `mechanism/DEFINITIONS.md` 已按此区分 pre/post；不能把保存的 post `gain_variance` 当本次 bar 的 pre 值。 |
| 物理重拟合 | `time_refine` 的每次目标求解 `Qh=b`，`Q=BᴴB+G(v)+σ²I`、`b=BᴴY`；`G(v)` 来自 CE 的符号方差与物理路径交叉项。soft 用向量 `v`，mean 令 `v=0`；两次 bounded coordinate passes，至多八观测延迟组。 | 此处的 ridge 系数 `λ=σ²` 属于**外层观测物理重拟合目标**，并非 inner `τ=1/P`、也不是共享优化目标/ELBO 的一项。TF、POINT、PBi 用 soft；登记的 EP2/EP4 为 mean，但调用同一个 time-domain refit 实现。 |

机制百分数遵循保存状态的定义：原始输出方差校正比为 `P v_h^pre (||x_pre||²/N+v_x^pre)/(σ²+v_x^pre·h_preᴴRh_pre)`，**不把输出阻尼混入分子分母**；实际 data reaction 比为 `||sv·P·v_h^pre·xb|| / ||DAFT(A(hb)ᴴ st)||`，与用未阻尼 `x_pre` 的“literal”诊断分列。`N v_h^post=1/(sv||xb||²/N+P/N)` 只在 joint 且 gain-precision floor 未触发时是代数恒等式；POINT 的 hypothetical posterior variance 不传播。原 scalar trace 的 `data_variance/gain_variance` 是 post-update，而 `channel_norm_factor` 是 pre-update；不要拿三格汇总中位数反推逐迭代曲线。

| 文献公式族 → 本地比较对象 | 实际实现 / coded 与 SP 改动 | 计费与声明边界 |
|---|---|---|
| [Parker–Schniter scalar P-BiG-AMP，III-H/Table V、IV-A](https://arxiv.org/html/1508.07575) → `TF_J20_R2` | 全分数 Doppler 的相位路径算子及 proper-complex QPSK 边缘、观测酉旋转后的标量更新；另加 observed-only pilot 初始化、物理重拟合与两轮 LDPC check/APP 交换。 | 每次完整计 pilot、两次 refit、inner、两次 LDPC、checkpoint 回调及失败在线工作。两/四 FFT 是同一标量映射的实现对照，不是本文主性能/新颖性声明。 |
| [Yi 等 dual-domain EP](https://arxiv.org/html/2603.29218v1) → `EP2/EP4_MEAN_R2` | 本地 `structured_ep.py` 是 proper-complex cyclic-band Gaussian 求解、协方差边缘投影、AF QPSK/LDPC 的**适配比较臂**；两轮各先运行相同代码的 time-domain `time_refine(mode='mean')`。 | 收费 observed pilot front、refit、band solve、decoder 和失败工作。不是原作者发布代码或严格逐式复现；不能把它描述为 EP 的普适复杂度下界。 |
| [Ranasinghe 等 AFDM PBiGaBP](https://arxiv.org/html/2405.16945v4) → `PBI8_SOFT_R2` | 本地 `bilinear.py` 保留 proper-complex gain/data cavity 类计算，但采用观测初始化、全分数物理路径、soft time refit 与 LDPC 双轮；属于 PBiGaBP **family adaptation**，并非作者代码。 | 昂贵 dense comparator 的实际完整耗时需如实报告；它不等于 TF 标量映射，也不能凭少量子集推断总体胜负。 |

结论边界：在上述已执行路径与保存状态的静态对照中，未见需立即停止 Part A 的明确主方程/消息流缺陷。此文件不是新的数值资格测试，也不把 Part A 机制控制的结果预判为正向。相关实现位置：`twofft.py` 的 `scalar_joint/time_refine`，`native_twofft.py` 的 `receive`，冻结基线 `messages.py` 的 `marginal/moments`，上游 `supplement_messages.py` / `e1_ldpc.py` 的 decoder 路径，以及 `results/sp_afdm_native_direction_20260921/mechanism/DEFINITIONS.md`。
