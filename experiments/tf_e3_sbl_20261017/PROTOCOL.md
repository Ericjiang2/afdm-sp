# E-3 协议（冻结稿）：外部有效性——Luo 式数据辅助 SBL 接收机中的同时延协方差修正

任务 `.trellis/tasks/10-17-external-sbl-e3/`。本文件 = `design.md`（具有约束力）并入执行期事实与偏差；两者冲突处以本文件为准，偏差全部列在 §10。
冻结（永不修改）：`experiments/tf_geometry_reopen_20260922/`、`tf_cstate_validation_20260922/`、`sp_afdm_native_joint_20260921/`、`tcom_reference_frame_20261015/`、`tcom_genie_support_20261016/`、`tcom_channel_crb_20261016/`、`headroom_ladder_20261008/`、`tf_production_gap_audit_20260922/`、`tf_cstate_e1_20261017/`、`tf_cstate_e2_20261017/`。新代码只在本目录；对冻结代码一律只读导入。
前置：res-20261017-01（E-1）、res-20261017-02（E-2）。外部接收机：Luo et al. arXiv:2607.18881（D-GESBL，SP-AFDM）的两级 EM-SBL 结构。

## 1. 问题

E-1/E-2 只在 CSTATE 的离散交换搜索里验证 H*（同时延原子的译码不确定性相干；标量化产生同时延幻影，完整投影协方差 Γ 消除之）。本任务换一个与 CSTATE 无关、按文献风格搭建的估计器，问两件事：幻影是否同样出现；改用 Γ 后幻影是否消失、FER 是否改善。三种可能：(1) 出现且 Γ 能修；(2) 出现但 Γ 修不好；(3) 不出现（SBL 的连续 ARD 天然抑制）。

## 2. 接收机（所有变体共用）

**约定（读源码并数值核对）**。观测 `Y = daft(obs['y'], c1, c2, inverse=True)`；原子响应 `B = _responses(xt, atoms, c1, c2)`，`xt = daft(pilot + μ_d, c1, c2, inverse=True)`；`Γ = _gamma_cross(C, C, fft(v), c1)`；`μ_d, v = moments(clip(app, ±20), 1 − system.rho)`（`system.rho = .5`，接收端内部约定下数据功率 = pd = .5，QPSK 字母表 = ±.5 ± .5j，`obs['sigma2']` 已折算到该约定）。`_responses`、`_gamma_cross`、`Path` 从冻结的 `geometry_reopen.py` 只读导入，`moments`/`daft`/`Channel`/`scalar_joint`/`decoder_messages` 来自冻结的 `messages.py`/`physical.py`/`twofft.py`/`native_twofft.py`/`receiver.py`。核对（`e3_driver.py --mode gate`，帧 0..2 的 U/G × ρ{.3,.5} × SNR{5, 8} dB 共 24 个状态）：真路径、真数据、真增益求和的字典列 `Σ_p g_p B(xt_true)[:, p]` 与无噪声观测 `daft(noiseless/scale, inverse)` 的相对误差最大 6.9e-16（含噪声的 Y 为 3.7e-16）；真数据 `raw['data']/scale` 与 `alphabet(.5)` 的最大距离 0，对真数据做硬判决得自身（误差 0）。
**原子网格**：时延 0..`l_max_cap`(102)、Doppler ∈ [−3, 3] 步长 .25，K = 2575（与 CSTATE bank 同序，`sbl_rx.full_grid`）。
**EM-SBL 核心**（`sbl_rx.sbl_em`，Luo 式 + 字典不确定数据的 EIV 期望 Gram）：先验 h_k ~ CN(0, γ_k)，噪声精度 β；E 步 Σ = (β(B̄ᴴB̄ + Γ) + diag(1/γ))⁻¹，μ = β Σ B̄ᴴY；M 步 γ_k = |μ_k|² + Σ_kk，β⁻¹ = (‖Y − B̄μ‖² + μᴴΓμ + tr((B̄ᴴB̄ + Γ)Σ))/N；最多 100 次迭代，γ 相对变化 ‖Δγ‖/‖γ‖ < 1e-4 即停；每次 M 步后移除 γ_k < 1e-6·max γ 的原子；γ 初值全为 1（设计未规定，此处冻结）。最后在最终活动集上再做一次 E 步取 μ。
**筛选**：每级先取 |B̄ᴴY| 最大的 M = 256 个原子（并列按索引）作为候选集，再对候选集跑 SBL。
**输出选择**：保留 |μ_k|² ≥ 1e-3·Σ|μ|² 的原子，最多 24 个（按能量取最大者，至少 1 个），允许同时延；这些原子与其 SBL 后验均值增益组成 `Channel`。
**两轮流程**：
1. 第 1 级（只用导频）：B̄ = B(pilot)，Γ = 0，β₀ = 1/(σ² + pd)（内部约定下 pd = 1 − system.rho = .5，即设计的 1/(σ² + (1 − ρ))）。所有变体共用。
2. 第 1 轮：`scalar_joint(..., gain_mode='fixed', prior=None, iterations=20, damping=.3)` → `decoder_messages(maxiter=50)`；`μ_d, v = moments(clip(raw_app), 1 − rho)`，`check = clip(raw_check_extrinsic)`。
3. 第 2 级候选集 = 软均值字典 B(pilot + μ_d) 的前 256 个原子 ∪ 第 1 级所选时延上的整行 Doppler（25 个/时延）；四个变体共用。
4. 第 2 轮：`scalar_joint(..., gain_mode='fixed', prior=check, iterations=20, damping=.3)` → LDPC；读出无条件 FER（不依赖第 1 轮是否已译对）。
**同时延检测器核对**（`test_e3.py::TC`，冻结的 `Channel`/`TimePathOps`/`scalar_joint` 在含共时延路径的信道上）：`scalar_joint`（fixed 增益）只通过四个量接触信道——`B = phase·xt[idx]`、伴随 `A^H`、物理范数 `hᴴRh`、`Bᴴs`（逐路径）。对含 3 重与 2 重同时延的信道，6 次随机试验的最坏值：`daft(B h) − Channel.apply(x)`（独立的逐路径实现）相对误差 3.1e-16；伴随恒等式 ⟨A_h xt, z⟩ = ⟨xt, A_hᴴ z⟩ 相对误差 9.6e-16；`R` 与时域调制 Gram `(1/N)Σ_k conj(m_i)m_j·[l_i = l_j]` 的最大元素差 3.4e-14，跨时延元素恒为 0；`power(h)` 与"按时延分组的功率和"相对误差 5.6e-15；含共时延 `Channel` 的 `scalar_joint` 运行有限且逐位确定。另 T3 用同一调用路径复现 P1 ledger（§6）。

## 3. 变体（只在第 2 级不同）

| 变体 | 字典里的数据 | Γ_var | β₀ | 含义 |
|---|---|---|---|---|
| L-hard | 硬判决重调制 Mod[Demod(μ_d)]（`sqrt(pd/2)(sign Re + j sign Im)`，零判 +；与 `alphabet` 比特约定一致，已测试） | 0 | 1/(σ² + mean(v)) | Luo 原样 |
| L-diag | 软均值 μ_d | Σv·I（= diag Γ，逐键断言 1e-10） | 1/(σ² + mean(v)) | 标量化，对应 E-1 的 A2 |
| L-cov | 软均值 μ_d | 完整 Γ = `_gamma_cross(C, C, vf, c1)` | 1/(σ² + mean(v)) | 对应 A1 |
| L-genie | 真数据 `raw['data']/scale` | 0 | 1/σ² | 网格失配基线 |

超参（M=256、100 次、1e-4、1e-6、1e-3、24、γ₀=1）对四个变体与第 1 级完全相同，不做任何调参。

## 4. 帧与 SNR

**帧**：P1 生成器（entropy `2261fde3…`，域 TCRF），U/G × ρ ∈ {.3, .5}。主跑帧 4000..4399，校准帧 6000..6099，冒烟帧 ≥ 8000（仅冒烟）。
**帧查证（执行者）**：P1 流已用帧：0..1999（P1 主跑、GS、E-1）、0..499（CRB）、0..999（zport）、2000..2099（P1 timing）、3000..3999（E-2 R 族）。对 `experiments/tcom_*`、`tf_cstate_e1/e2` 的 launcher 做 grep，并扫 deinlab 全部含该 entropy 的 `config_shard*.json`：未发现 4000..4399 或 6000..6099 的使用（扫描里 E-2 `calibrate` 5000..5099、`main_C` 0..999、`smoke_C` 9000..9011 的 config 只因打印了 R 族 entropy 而出现；其信道/消息/噪声取自独立的 E2CJ 流，不占用 P1 流）。P2b 的 `--frame-offset 3000` 使用独立 entropy/域。E-3 自己的门与冒烟占用 P1 流帧 0..19、8000..8007、8100..8103，均与主跑和校准不相交。
**主跑**对全部帧运行，读出无条件 FER。
**SNR 网格（冻结规则，只看 L-hard，每个 (场景, ρ) 格单独决定）**：校准帧上扫描 {4, 5, …, 14} dB，L-hard 的无条件 FER（第 2 轮后 ≥ 1 个信息比特错误的帧比例）≤ .9 的最小 SNR 记 s0，网格 = {s0, …, s0+5} 超过 14 dB 的点截断；若 14 dB 时 L-hard FER 仍 > .9，该格 UNINFORMATIVE，不跑主跑。实现 `e3_calib.decide_grid`（`test_e3_agg.py` 覆盖边界：FER 恰为 .9 判 OK），结果写 `out/calibrate/GRID.json`，其 md5 须在主跑开始前写入 STATUS；`run` 只读该文件。

## 5. 读数与冻结判据

**普查口径**（与 E-1/E-2 一致）：显著原子 = 输出选择后保留的原子；同时延对 = 两个显著原子时延相同（同一时延 m 个原子计 m(m−1)/2 对）；每帧对数 n_pair；每对记 |Δν|、|D_N(Δν)|（N=1024）、该时延是否为真时延；幻影超额 E_v = mean(n_pair | v) − mean(n_pair | L-genie)。
**统计**：cluster bootstrap（cluster = (场景, ρ, 帧)，20000 次，seed 20261017，百分位 95% CI；多项式计数重抽样，沿用冻结的 `e1_agg.bootstrap_rates`/`ci`）；精确单侧 McNemar α = .05，只报 log10 p；凡"CI 含 0"一律附注 "not significant != equivalent"。单元 = 主跑的 (格, SNR, 帧) 键，全部合并。
**判据**
- X1 幻影存在：X1-diag：CI_lo(E_L-diag) > 0；X1-hard：CI_lo(E_L-hard) > 0。两者都报告。
- X2 修正去除幻影：R_ph = E_L-cov / E_L-diag（逐重抽样）的 CI 上界 ≤ .25；仅当 X1-diag 成立时评估（此时 E_L-diag > 0）；分母 ≤ 0 的重抽样 > 1% 或点估计分母 ≤ 0 视为不可评估，按"X2 不成立"处理。
- X3 FER 改善：主对比 L-cov 与 L-diag；同时满足 (i) 合并全部单元后，单侧 McNemar（L-cov 优于 L-diag）显著；(ii) FER 差 (L-diag − L-cov) 的 CI 下界 > 0。
- 报告项（不参与判定）：L-cov 对 L-hard 的 McNemar 与 FER 差；FER 达到 1e-2 的穿越点（每格，log10 FER 线性插值，FER=0 取 0.5/n 下限）；L-genie 的 FER；NMSE（`crb.channel_nmse`，逐变体与第 1 级）；成本；按格/SNR 的 FER、n_pair、NMSE 表。
**判定**（按顺序，互斥）：1 ABSENT：X1-diag 与 X1-hard 都不成立；2 NO-FIX：X1-diag 成立且 X2 不成立；3 MECHANISM-ONLY：X1-diag、X2 成立，X3 不成立；4 GENERAL：X1-diag、X2、X3 都成立；5 HARD-ONLY：只有 X1-hard 成立（不评估 X2/X3）。
聚合拒绝解读（`interpretable=false`）当：行集 ≠ 冻结键集、出现 error 行、行缺变体、`diag Γ ≠ Σv`（≥ 1e-10）、或 gates 不全过。实现 `e3_agg.py`；`test_e3_agg.py` 覆盖五类判定各分支、X2 在无 X1-diag 时不评估、X3 的两个条件分别必要、校准规则边界、census、crossing、integrity 阻断。

## 6. 门（跑前，结果见 `out/gate/gates.json`、`out/unit/test_e3.json`）

- **T1 SBL 正确性**：合成（n=128，12 时延 × 9 Doppler 网格）无噪声 4 个格点原子（含一对同时延）精确恢复支撑，增益相对误差 8.2e-9（5 次迭代收敛）；v ≡ 0 时 L-cov（冻结 `_gamma_cross` 的全零矩阵）= L-diag（Σv·I = 0）= 以 μ_d 为字典的标准 SBL（Γ=None），idx/μ/γ/β/迭代数逐位一致（无噪声与含噪声两种输入）；v > 0 时 L-cov ≠ L-diag。附加 TE：优化的 E 步（Cholesky + 三角逆，迹用恒等式 tr(GtΣ) = (a − Σ_k Σ_kk/γ_k)/β）与教科书实现（显式逆与显式迹）在 3 种 Γ × 2 种迭代数上活动集与迭代数一致，μ/β/γ 最大相对差 3.8e-14/2.0e-13/9.7e-12。
- **T2 Γ 正确性**：合成（n=256，16 个原子含同时延与近重复）：diag(Γ) = Σv 相对误差 2e-16，Hermitian 相对 1.6e-15，最小特征值/最大 = .0079（PSD）；蒙特卡罗 E[(B(x)−B(μ))ᴴ(B(x)−B(μ))]（x 按 `moments` 所用的逐符号 QPSK 后验抽样 4000 次）相对 Frobenius 误差 .0038（仅非对角部分 .0060）。真实帧（20 帧，每分片一帧；24 个原子 = 真路径、同时延近重复 Δν=.25、同时延对 Δν=1.5；第 1 轮译码器 APP 的后验）：最坏 MC 相对 Frobenius 误差 .0021（非对角 .0032），diag(Γ) 误差 1.8e-16，Hermitian 3.0e-16，最小特征值/最大 .0486。
- **T3 下游接线**：P1 ledger 的"真信道、固定增益"臂 = **A3**（`run_a3` → `run_fixed_channel(detector='tf')` = `_instrumented(rounds=2, iterations=20, gain_mode='fixed')`：每轮用真 (l_i, k_real, g_i)，第 1 轮 prior=0，第 2 轮 prior=clip(check)）。用 E-3 的检测/译码调用路径（`scalar_joint(..., prior=None/clip(check), iterations=20, damping=.3, gain_mode='fixed')` + `decoder_messages(maxiter=50)`，两轮都用真路径）在 P1 帧 0..19 × 4 格 × 8 SNR = 640 键上：decoded sha 与 ledger A3 一致 640/640，信息比特错误数一致 640/640。
- **T4 确定性**：合成：SBL 三种 Γ 同输入两次逐位一致；真实帧：20 个键（每分片一个，6.0 dB）整条流水线（四个变体、第 1 级、两轮）跑两次，去掉计时字段后逐位一致 20/20；逐键 diag(Γ) 误差最大 1.8e-16。
- **T5 成本**：见 §7。
- **字典约定与数据缩放**（上文 §2）：24 个状态通过；**共时延检测器**：见 §2。

## 7. 成本（上限 ~~40~~ **60** core-hours，见 §11 O1；单线程分片，保留 ≥ 16 核空闲）

冒烟实测（`launch_e3.sh MODE=gate`：门 20 分片 + 冒烟 6 个进程共 26 个进程同时在跑，机器负载 ≈ 9）。主跑式冒烟 = 32 键（8 帧 × 4 格，临时 SNR 8 dB，**仅冒烟**，帧 8000..8007）：每键 **11.1 s**（含帧生成 .15 s）：第 1 级筛选 .08 s（导频字典按 ρ 缓存）+ 第 1 级 SBL .33 s + 第 1 轮检测/译码 .06 s + 第 2 级筛选 .24 s + 四个变体各 2.5–2.6 s（SBL 2.4–2.5 s，字典列 ≤ .05 s，Γ .04 s，检测+译码 .05 s）。校准式冒烟 = 32 键（4 帧 × 4 格 × {6, 10} dB，仅 L-hard，帧 8100..8103）：每键 **3.65 s**。
SBL 维度：候选集 623 个原子（平均；第 2 级）、第 1 级 256 个；**剪枝阈值 1e-6·max γ 在 100 次 EM 迭代内从未触发**（所有 SBL 的 `n_final = n_start`；EM 中不相关原子的 γ 按 ≈ γ/(1+γ·β·G_kk) 的调和速度衰减），故每次 E 步都是 ≈ 650 维的 Cholesky + 三角逆；停止判据 1e-4 在第 2 级只有 14/32（L-diag）、0–1/32（其余）个 SBL 满足，其余打满 100 次。
估计（核时）：主跑 9600 键（400 帧 × 4 格 × 6 SNR）× 11.1 s = **29.6**；校准 4400 键（100 帧 × 4 格 × 11 SNR，仅 L-hard）× 3.65 s = **4.5**；合计 **≈ 34.1**（冒烟负载下）。E-1/E-2 主跑在满载并行下每单元慢 1.5–1.8 倍；按此外推 64 分片并行约 51–61 core-hours，**超过 40 的上限**；低并发（≤ 32 分片，冒烟级别 1.0–1.1 倍）约 34–38，余量不足 15%。
选项（记录；编排者已在 §11 O1 决定：上限提到 60、NSHARD ≤ 48、范围与算法不变）：
(a) 范围不变，限制并发 ≤ 32 个分片（总墙钟 ≈ 1.3 h 级），把竞争因子压到 ≈ 1.1，估计 ≈ 37–38 core-hours（余量 ≈ 6%）；
(b) 改超参（需在冻结前改 design）：剪枝阈值 1e-6 → 1e-3（维度随迭代快速收缩，预计每次 SBL 加速数倍）；或 M = 256 → 128（候选集 ≈ 370，E 步 ≈ 0.2×）；
(c) 缩范围：主跑帧 400 → 300（−25% ≈ −7.4 core-hours），或校准帧 100 → 60；
(d) GPU 上做批量 Cholesky（共享 GPU、不逐位可复现，不推荐）。

## 8. 运行手册

`launch_e3.sh` 在 tmux `g_e3*` 内：`MODE=gate`（门 + 两个冒烟）、`MODE=calibrate`（默认 48 分片，→ `out/calibrate/GRID.json` + md5）、`MODE=run`（读 GRID.json，默认 48 分片）、`MODE=riter`（主跑之后的 R-iter 稳健性检查，默认 48 分片，§11 O2）、`MODE=agg`（有 `out/riter` 时自动并入 riter 小节）。calibrate / run / riter 拒绝 NSHARD > 48。开跑前核对负载。失败分片原样保留，不重试不换配置。只回传小文件；行数据留 deinlab（gzip + md5 清单）。

## 9. 局限

细网格 on-grid 是对 Luo off-grid（Taylor）的简化：分数 Doppler 带来网格失配分裂，故必须扣除 genie 基线；检测器与译码器沿用本项目组件；只有一个外部估计器族（SBL）；ABSENT 只说明 SBL 不出现该现象；结论只限本移植、P1 信道、N=1024、QPSK、本 LDPC 码。

## 10. 与 design.md 的执行期偏差与事实

1. **E 步实现**：为降低成本用 Cholesky + 三角逆代替显式 Σ，迹项用恒等式 tr((B̄ᴴB̄+Γ)Σ) = (a − Σ_k Σ_kk/γ_k)/β（由 AΣ = I 严格推出）；与教科书实现的差异 ≤ 1e-11（TE）。数学上是同一算法，不是近似。
2. 设计未规定而此处冻结：γ 初值 = 1；收敛判据 ‖Δγ‖/‖γ‖；剪枝每次 M 步后执行；最终 μ 取自最终活动集上的一次额外 E 步；Cholesky 数值奇异时一次性加 1e-12·tr/m 的对角抖动并计数（冒烟中 0 次）。
3. β₀ 中的 (1−ρ) 在接收端内部约定下写作 pd = 1 − system.rho = .5（`obs['sigma2']` 已折算）。
4. 硬判决取 μ_d 的实部/虚部符号（与 LLR 符号一致，零判 +）。
5. 剪枝阈值在 100 次迭代内不触发、停止判据多数不满足（§7）：这是设计超参的事实，不是实现缺陷；它决定了成本。
6. 冒烟：主跑式冒烟临时 SNR 8 dB（帧 8000..8007）、校准式冒烟 {6, 10} dB（帧 8100..8103），行内 `smoke=true`，不得并入分析。
7. 非收敛（达 100 次）的 SBL 计数、Cholesky 抖动计数由 `e3_agg` 报告；不参与判定。
8. 每键一行，含第 1 级、第 1 轮、四个变体（原子 [时延, Doppler, |μ|²]、同时延对、NMSE、SBL 迭代/维度、分阶段秒数）与真值路径；校准行同结构但只有 L-hard。

## 11. 编排者跑前修订 O1–O3（2026-10-17）

诚实声明：修订前编排者已见 smoke 计数（8 dB，32 键：FER 2/0/2/0，mean n_pair 6.84/30.47/5.53/5.34）；修订只涉及成本上限与稳健性检查，不改算法、超参、判据或范围。

**O1 成本上限。** 上限由 40 提高到 **60 core-hours**，且校准与主跑（以及 riter）的 `NSHARD` 上限为 **48**（`launch_e3.sh` 强制，超过则 abort；默认值也是 48）。理由：实测 34.1 core-hours（冒烟负载，约 26 个进程同时在跑），E-1/E-2 满载并行下每单元慢 ×1.5–1.8（→ 约 51–61）。该上限是预算护栏，不是科学参数；超限仍即停并报告。

**O2 R-iter 稳健性检查（预注册，report-only，不进入五类判定）。** 主跑结束之后：
- 子样本 200 键，seed 20261017，按 4 格 × SNR 网格点均匀分层。算法（`e3_calib.riter_sample`）：层 = 各格（U_300, U_500, G_300, G_500 的顺序，UNINFORMATIVE 的格没有层）× 升序网格 SNR；每层取 n//S 个键，另有 n%S 个层多取 1 个，这些层由 `np.random.default_rng(20261017).choice(S, n%S, replace=False)` 先抽出，随后按层顺序用同一生成器从主跑帧 4000..4399 无放回抽帧。24 层时 = 每层 8 个、其中 8 层 9 个，共 200。
- 只对 L-diag 与 L-cov 用 `max_iter = 400` 重跑（仅第 2 级 SBL；第 1 级仍 100 次），其余一律不变：第 1 级输出、第 1 轮检测与译码、候选集、β₀、Γ 都由同一确定性流水线重算；`e3_agg` 用主跑行核对第 1 级原子、第 1 轮 decoded sha、候选集大小并报告不一致数（应为 0）。
- 并列报告 100 次与 400 次：mean n_pair 与 genie 超额（genie 保持其 100 次的值）、FER、撞迭代上限的份额。
- **冻结标记规则**：若 L-diag 在 400 次迭代下的 genie 超额 < 其在同 200 键、100 次迭代下的 genie 超额的 50%，卡片必须把 X1-diag 标为 "budget-dependent"（严格小于；100 次超额 ≤ 0 时记 "not applicable"）。
- 实现：`launch_e3.sh MODE=riter`（要求 `out/main/STATUS.txt` 已有 "run done"；输出 `out/riter`，NSHARD ≤ 48）、`e3_driver.py --mode riter`、`e3_agg.py --riter`（独立小节）；合成测试 `test_e3_agg.py::test_riter_sample`、`test_riter_flag_and_analysis`（标记边界 = 50%、不适用、跨键对照、不一致检测）。仅为核对代码路径做过一次 smoke（帧 8200..8207，8 dB，8 键，行内 `smoke=true`，不并入任何分析）：与同键主跑式冒烟行相比，第 1 级/第 1 轮/候选集不一致数 0；400 次下 SBL 撞上限份额 0。
- 预计成本 ≤ 200 键 × 约 25 s ≈ ≤ 1.4 core-hours（冒烟实测约 7.5 s/键）。

**O3 诊断。** 主聚合新增：每个变体的 SBL 撞 `max_iter`（1e-4 停止规则未满足）的份额，第 1 级与第 2 级分开报告（`e3_agg.iter_cap_share`，渲染在 FER 穿越点之后）。

## 12. 来源与哈希

冻结源 md5：`SOURCE_MD5.txt`（22 个文件：E-1 清单 20 个 + 只读导入的 `e1_lib.py`、`e1_agg.py`），运行时由 `e3_driver.check_frozen_md5` 对已加载模块逐一复核并写入每个 `config_shard*.json`。本目录代码 md5 见 `CODE_MD5.txt`（本文件自身的 md5 由各 config 的 `own_md5` 在开跑时记录）。
