# E-2 协议（冻结稿）：同时延守卫臂、新帧复现、真同时延簇信道

任务 `.trellis/tasks/10-17-codelay-guard-e2/`。本文件 = `design.md`（具有约束力的臂、族、判据、门、成本上限）并入执行期事实与偏差；两者冲突处以本文件为准，偏差全列在 §10。
冻结（永不修改）：`experiments/tf_geometry_reopen_20260922/`、`tf_cstate_validation_20260922/`、`sp_afdm_native_joint_20260921/`、`tcom_reference_frame_20261015/`、`tcom_genie_support_20261016/`、`tcom_channel_crb_20261016/`、`headroom_ladder_20261008/`、`tf_production_gap_audit_20260922/`、`tf_cstate_e1_20261017/`（E-1 亦已冻结，只读导入）。新代码只在本目录。
前置：res-20261017-01（E-1，已验收）。E-1 事后观察（doublet 普查）只是假设来源，本任务预注册地检验它。

## 1. 假设与三种解释

E-1 事后观察：对角 Γ 的交换在 94% 单元里，在已有真时延上插入近重复的同时延原子（|Δν| 中位数 .06，|D_N| ≈ 1）；完整 Γ 则补入真时延。A1 − A2 的差距有三种解释：
- **X-phantom**：差距完全来自幻影同时延原子；禁止它们，对角 Γ 就恢复到接近完整 Γ。
- **X-rank**：完整 Γ 的作用超出抑制幻影原子（例如改变真时延候选的排序）；禁止幻影原子只恢复一部分。
- **X-principle vs heuristic**：信道里真有同时延射线时，"一律禁止同时延"的启发式会误删真射线，完整 Γ 则能分辨真射线与幻影；只有含真同时延射线的信道才能分开两者。

## 2. 臂与守卫

所有臂都从同一捕获的 F0 状态出发（`native_twofft.receive(rounds=2, iterations=20, ce_mode='soft', gain_mode='joint')`），只在触发单元（F0 终末校验子 ≠ 0）上运行。固定量沿用 E-1 PROTOCOL §3：`strategy='compact'`、`grid_step=.25`、`chunk_size=64`、`local_halfwidth=.75`、`local_max_evals=16`、`duplicate_tolerance=1e-6`、`top_k=20`、`ridge=sigma2`、`max_delay=system.l_max_cap`、Doppler ∈ [−3, 3]；检测 `scalar_joint(iterations=20, damping=.3, joint, prior=r1_check)`、LDPC `maxiter=50`。r1_* 语义同 E-1 PROTOCOL §3（r1_delays / r1_dopplers = 第二轮 `time_refine` 信道，唯一时延；r1_gains = 检测器 joint 增益；r1_app / r1_check = 第二轮译码器 raw_app / raw_check_extrinsic）。

| 臂 | Γ | max_edits | local_passes | 守卫 | 作用 |
|---|---|---|---|---|---|
| A1 | full | 2 | 2 | off | 生产 CSTATE20 |
| A2 | diag | 2 | 2 | off | E-1 对照 |
| A3 | full | 0 | 2 | off | 复现交换份额 |
| A1g | full | 2 | 2 | all | 完整 Γ + 禁止同时延 |
| A2g | diag | 2 | 2 | all | 对角 Γ + 禁止同时延 |
| A2n | diag | 2 | 2 | neardup | 对角 Γ + 仅禁止近重复（\|D_N(Δν)\| ≥ .5，即 \|Δν\| ≲ .6）；按定理导出，报告臂 |
| A5 | — | — | — | — | 只重跑检测 + LDPC（r1 几何与增益不变） |
| A7 | — | — | — | — | 字面第三轮 F0：`receive(rounds=3)` 从头重跑；G5：其 r0_*/r1_* 全部数组与已捕获 rounds=2 状态逐位相等（E-1 同款） |

**守卫定义**（`codelay_guard` ∈ {off, all, neardup}）。`others` = 除被替换（或被移动）slot 以外的当前路径。
- `all`：候选 `(l, ν)` 若 `l ∈ {p.delay : p ∈ others}`，判为无效。
- `neardup`：若存在 `p ∈ others` 使 `p.delay == l` 且 `|D_N(ν − p.ν)| ≥ .5`，判为无效；`D_N(x) = sin(πx) / (N sin(πx/N))`，`N = len(y) = 1024`，`D_N(0) = 1`（极限）。
- 作用于**所有**共时延原子可进入处，compact / direct / fallback 三条路径一致：
  1. 全局候选掩码：`geometry_validation_guard._valid`（compact）把守卫冲突并入 duplicate 的 `equal` 矩阵，原返回式"没有其他路径冲突"保持不变；`_direct_scores`（direct 与 `_direct_global` fallback）对每个 slot 的 `others` 追加 `hits_group`。
  2. 局部 Doppler 细化：每个试探点 `path_conflicts(test, others, N, guard)` 违反即拒绝（返回 inf，计入 `local_duplicate_rejections`，`valid=False`）。`neardup` 下合法的一对不能漂进 |D_N| ≥ .5。
  3. fallback：`_direct_global` → `_direct_scores` 同样传入 `codelay_guard`。
- `off` 与 E-1 变体逐位一致（G1）。r1 几何时延唯一（`time_refine` 取 unique 时延），故初始状态满足守卫；终末几何的守卫不变量逐行断言（G2，`guard_ok`）。

**实现**（相对 E-1 变体的 diff 仅限守卫，`test_e2.py::T0` 机械检查）：新文件 `codelay_guard.py`（谓词，numpy）；`geometry_validation_guard.py` = E-1 `geometry_validation_variant.py` 的拷贝 + 关键字 `codelay_guard`（默认 `"off"`）+ 4 处插入（头部 5 行注释/import、`_valid`、`_direct_scores`、取值校验）+ 局部试探处 1 行修改 + 签名与调用点透传；它仍从 E-1 `geometry_reopen_variant.py`（无守卫改动，冻结）导入 `Path`、`_system`、`_gamma_cross` 等。

## 3. 族

**R（复现）**：P1 生成器（`gen_fixed`，U/G × ρ{.3,.5}），entropy `2261fde3…`，域 TCRF，帧 3000..3999，SNR 4.5, 5.0, …, 8.0 dB（8 点）。32000 键，**对全部键跑 F0**（无 ledger），按校验子 ≠ 0 触发；预计触发 ≈ 8190（P1 ledger 帧 0..1999 的 16379 触发的一半）。
- **帧查证（执行者）**：P1 流（entropy `2261fde3…` + TCRF）已用帧：0..1999（P1 主跑、GS、E-1）、0..499（CRB）、0..999（zport）、2000..2099（P1 timing）、0..63（P1/zport 门）。对 `experiments/tcom_*`、`tf_cstate_e1_20261017` 全部 launcher 与 driver 的 `--frame-offset` 做 grep，并扫 deinlab 全部含该 entropy 的 `config_shard*.json`（偏移/帧数：crb 0/500、gs 0/2000、p1 0/2000、p1_timing 2000/100、zport 0/1000、e1 0/2000 等）：**3000..3999 在 P1 流上从未使用**。`launch_p2b_gates.sh` 用了 `--frame-offset 3000`，但 P2b 使用独立 entropy/域（`ENTROPY_DEV`/`TCDP`，`ENTROPY_TEST`/`TCP2`），与 P1 流不相交。

**C（真同时延簇）**：Jakes-4（λ=4，每射线 θ 均匀）簇信道接入 P1 管线；ρ ∈ {.3, .5}；新熵 `E2CJ`。
- entropy `850a0ce3fe4865e4799e3876ba125ffd95e879da1b0de7f2d16c05ad38da80a1`（`os.urandom(32).hex()`，2026-10-17，先于任何 E2CJ 数据），域 `0x4532434A`；主跑帧 0..999，校准帧 5000..5099，冒烟帧 ≥ 9000（仅冒烟）。流 = `SeedSequence(8 个 uint32 熵字, 域, 帧, 分量)`，分量 channel=1 / message=2 / noise=3，与 P1 同约定。
- **SNR 网格（冻结规则，只看 F0）**：`calibrate` 在校准帧上用 F0 对候选网格 {6, 8, …, 20} dB 扫描，每个 ρ 单独决定。F0 FER = 校准帧中 F0 后有 ≥ 1 个信息比特错误的帧比例。取 F0 FER ≤ .95 的最小 SNR 为 s0，网格 = {s0, s0+2, s0+4, s0+6} 每点与 20 dB 取较小者（重复合并）。若 20 dB 的 F0 FER 仍 > .95，该 ρ 判 UNINFORMATIVE，不跑主跑。规则实现于 `e2_calib.decide_grid`（`test_e2_agg.py::test_calibration_rule` 覆盖边界），结果写 `out/calibrate/GRID.json`；主跑 `run_C` 只读该文件。

**C 信道构造（精确）**
1. 几何：`e2_channels.draw_cluster_geometry/cluster_paths` 是 `headroom_ladder_20261008/driver.py` 同名函数的逐字拷贝，**唯一改动**是流域为参数（冻结代码硬编码 CLUS）；`test_e2.py::CG0` 证明域 = CLUS 时与冻结函数逐位相等（20 帧）。4 个抽头；抽头 0 时延 0，其后间隔 ~ numpy `geometric(1/8)`（均值 8，支撑 ≥ 1），最大时延 > 100 则整组重抽；抽头功率 ∝ exp(−l/20) 归一；每抽头射线数 1 + Poisson(3)（单个均匀数逆 CDF，上限 64）；射线增益 CN(0, 抽头功率/R_t)；射线 Doppler ν = 2 cos θ，θ ~ U[0, 2π) 每射线独立。冻结代码随后把 Σ|g|² 归一到 1（co-delay 干涉使 ‖H‖_F²/N ≠ 1，50 帧上范围 .546–1.5006）。
2. **数值单位功率归一**：在冻结的 Σ|g|²=1 之上，用独立的稠密时域矩阵 T（CPP 定义，`e2_channels.time_domain_matrix`）算 ‖H‖_F² / N = ‖T‖_F² / N（AF 变换酉，含同时延交叉项），增益再除以 √(该值)。`frame_geometry` 另用 `ctx.physical_channel_matrix`（流水线稠密矩阵）复核 |功率 − 1| < 1e-9，不满足即抛错。
3. 观测：与 P1 完全相同的物理 CPP 算子——`x = pilot + data`，`physical_y = DAFT(propagate_cpp(IDAFT(x), c1, 射线, prefix_length=l_max_cap=102))`，并与稠密矩阵 `h @ x` 核对（< 1e-10）；`y = physical_y + √σ² · noise`，`σ² = 10^(−SNR/10)`（SNR 为标称值，信道平均功率 = 1）；ρ 用 P1 的 shim；系统、码、导频、数据、噪声流的公式与 `gen_fixed.make_frame` 相同（`cluster_message`），`ctx.hd.observe` / `truth_from_raw` 原样使用。
4. 接收端仍是标准路径模型：F0、CSTATE 等一律不变（每时延一个 Doppler；真值射线多于 r1 能表示的）。
5. res-20261008-02 的构造核对：其 F1/F2 数据用同一 `cluster_base`（物理 CPP 算子，`physical_channel_matrix` + `propagate_cpp`）；`tapchannel.py` 的 `TapChannel` 只用于 M1 的 DPSS-BEM **接收端**（`dpss_rx` 等），不参与观测生成，本任务不使用。
6. 真值（用于普查）：射线 (时延, ν, 增益) 全表，每抽头射线数 `rays_per_tap`，抽头时延 `tap_delays`；"真时延集合" = 抽头时延集合；真多射线抽头 = 射线数 ≥ 2 的抽头。

**与 P1 系统的冲突核对（全部兼容，未静默适配）**：时延上限 100 ≤ receiver bank 102 = prefix 102 ✓；|ν| ≤ 2 在核内 ±3 之内、F0 导频字典 ν ∈ {−2..2} 之内 ✓；时延为整数采样（P1 D2 网格）✓；码、导频（Zadoff-Chu）、N = 1024、c1/c2 不变 ✓。簇律平均 16.07 射线/帧，每帧 ~4 个抽头中 94.95% 含 ≥ 2 射线（CG3），而接收端每时延最多一个 Doppler，路径数上限 8（`time_refine`）——这是预期的模型失配，不是冲突。

## 4. 读数与行格式

每单元每臂：成功（0 信息比特错误）、最终几何、同时延普查（定义同 E-1 `posthoc_doublet.py`）、编辑类型、成本。C 族另记真值同时延结构，并判断 A1 的 doublet 是否落在真多射线抽头上。
行：`out/main_R|main_C/rows_shard###.jsonl`（跑完 gzip），**每键一行**（含 F0 成功的键，行内只有 F0 字段）：`family, scenario（R: U/G；C: J4）, rho, rho_permille, snr_centi_db, snr_db, frame, sigma2, gen_seconds, f0{syndrome, info_errors, decoded_sha256, ldpc_iters, seconds}, triggered`；触发行另有 `r1{delays, dopplers}`, `truth{delays, dopplers, gains（[re, im] 对；C 族为全部射线）[, rays_per_tap, tap_delays]}`, `arms{A1..A7}`（同 E-1 行：status, fer, info_errors, syndrome, decoded_sha256, final_delays, final_dopplers, n_support_changes, n_delay_replacements, edits[], top5_step1[], seconds, stages, numerical_fallback…；A7 另有 seconds_minus_f0, g5_ok, g5_keys, r1_decoded_sha256；守卫臂另有 guard_ok）、`g5_ok`、`guard_ok`。`config_shard###.json` = `_argv` + `_config`（参数、臂规格、冻结源 md5 复核表、所有已加载项目模块 md5、环境、C 的 grid 与 md5）。

## 5. 冻结判据

统计沿用 E-1：配对单元；精确单侧 McNemar（报告 log10 p，避免 E-1 的浮点下溢）；cluster bootstrap，cluster = (族, 场景, ρ, 帧)，20000 次，seed 20261017，百分位 95% CI（多项式计数重抽样）；比值统计在其分母 ≤ 0 的重抽样比例 > 1%（或点估计分母 ≤ 0）时判为不可评估——需要不可评估比值的判据**不满足**（D1 逐项报告；D2 判 MIXED 并注明）；凡"CI 含 0"一律附注 **"not significant != equivalent"**。成功率 R_x = 单元集上臂 x 的成功比例。

**D1 复现（R 族主集 = 全部触发单元）。** PASS 需同时满足：
- (a) F5 = (R_A1−R_A5)/R_A1 与 F7 = (R_A1−R_A7)/R_A1 的 CI 下界都 ≥ .10；
- (b) S_Γ = (R_A1−R_A2)/(R_A1−R_A5) 的 CI 下界 > 1；
- (c) S_swap = (R_A1−R_A3)/(R_A1−R_A5) 的 CI 下界 ≥ .5；
- (d) A2 doublet 单元比例 ≥ .80 且 A1 ≤ .05（点估计）。
任一不满足即 FAIL，并逐项报告。

**D2 守卫恢复份额（R 族）。** G = (R_A2g − R_A2)/(R_A1 − R_A2)。按顺序判定，三类互斥：PHANTOM-FULL：G 的 CI 下界 ≥ .90；PHANTOM-PARTIAL：CI 下界 > .10 且不属于 FULL；PHANTOM-NONE：CI 上界 ≤ .10；其余（CI 跨越 .10）MIXED。G 可大于 1（守卫比完整 Γ 更好），照实报告。同时报告 G_n = (R_A2n − R_A2)/(R_A1 − R_A2) 与 R_A1 − R_A1g。

**D3 原则 vs 启发式（C 族，先过信息量门）。**
- 信息量门：C 族 A1 救回单元（A1 成功且 F0 有 ≥ 1 个信息比特错误）≥ 100，否则 D3 = UNINFORMATIVE（C 的 ρ 被校准判 UNINFORMATIVE 则该 ρ 无行；两个 ρ 都无则 D3 = UNINFORMATIVE）。
- D3a：R 族上 CI(R_A1 − R_A1g) ⊂ [−.01, .01]；D3b：C 族上 CI 下界(R_A1 − R_A1g) > 0；D3c：C 族上 CI 下界(R_A1 − R_A2g) > 0。
- PRINCIPLE = D3a ∧ D3b ∧ D3c；HEURISTIC-SUFFICES = C 族上 CI(R_A1 − R_A2g) ⊂ [−.01, .01] 且 D3b 为假；其余 MIXED。C 族集 = 各信息性 ρ 的全部网格点、全部触发单元合并。

**预注册读数（不参与判定）**：两族的同时延普查（臂的 doublet 单元比例、对数、|D_N| 直方图 [0,.2)/[.2,.5)/[.5,.8)/[.8,1]、编辑类型 shares/same_slot/new 及新时延是否在真值集合、末时延集合 = 真值集合的比例、r1 时延重复单元数、真值含重复时延的单元数）；C 族 A1（及其他臂）doublet 落在真多射线抽头上的比例与单元比例，与 R 族对比；A2n 在两族上的表现；按 SNR / 按 ρ 的成功率表；所有对比的 McNemar；成本表。
实现：`e2_agg.py`；`test_e2_agg.py` 的合成数据覆盖 D1 PASS 与每个 FAIL 项（a/b/c/d 及不可评估）、D2 四类 + 不可评估 + G>1、D3 的 PRINCIPLE / HEURISTIC-SUFFICES / MIXED / UNINFORMATIVE（信息量门与无 C 行）、校准规则边界、census、integrity 阻断解读。
聚合拒绝解读（`interpretable=false`）当：行集 ≠ 冻结键集、`g5_ok`/`guard_ok` 任一行为假、任一臂 status ≠ ok、F0 校验子与 `triggered` 不一致、或 gates/cgates 不全过。

## 6. 门（跑前通过，结果见 `out/gate/gates.json`、`cgates.json`、`out/unit/test_e2.json`）

- **G1**：`guard='off'` 时变体与 E-1 变体在 640 个真实 P1 状态（帧 0..19 × 4 格 × 8 SNR，含触发与未触发）上对 A1/A2/A3 逐位一致（全部 `ctx.branch` 输出：result、detector、decoder、先验矩）。由 E-1 G1 传递到生产。结果：640/640 × 3 臂。合成部分（`test_e2.py`）：5 配置 × 64 状态逐位一致，且缺省关键字 = off。
- **G2**：每行断言守卫不变量（`all`：终末时延唯一；`neardup`：无 |D_N| ≥ .5 的同时延对）；合成：compact 与 direct 两路径 × full/diag × 两种守卫 × 64 状态 = 512 次不变量检验 0 违反，compact 与 direct 的有效掩码与分数一致（256/256）；局部细化专项（16 个含真同时延对的合成状态）：`off` 下 15/16 终末对 |D_N| ≥ .5，`neardup` 下 0/16。真实态：159 个触发状态上 A1g/A2g/A2n 的守卫不变量各 159/159；A2g ≠ A2 的决策在 149/159（≥ 8 ✓）；（计数，不解释）A1g ≠ A1 在 0/159，A2n ≠ A2 在 149/159，A2n ≠ A2g 在 58/159。
- **G3**：8 臂确定性（同输入两次逐位一致）：60 个触发状态 × 8 臂全部一致；合成 6 个几何配置 × 64 状态一致。
- **G4**：R 族管线交叉核对：E-2 驱动在 P1 帧 0..19 上重跑，640/640 的触发判定、F0 sha、最终译码 sha 等于 P1 ledger（触发取 A1，未触发取 F0）；159 个触发键的 A1、A2 decoded sha 等于 E-1 主跑行。
- **G5**：A7 rounds=3 的首两轮（r0_*、r1_* 全部键）等于捕获态：60/60（门）；主跑每个触发单元行内断言。
- **CG1**：簇帧 ‖H‖_F²/N − 1：50 帧最大偏差 9.3e-15（流水线稠密矩阵）/ 8.9e-16（独立时域矩阵），门限 1e-9；归一前范围 .546–1.5006（均值 .9953）。
- **CG2**：`physical.Channel.apply`、稠密矩阵 `h @ x`、直接 CPP 传播三者一致：20 帧最大相对误差 6.7e-13（流水线）/ 7.9e-16（独立时域矩阵），门限 1e-9。
- **CG3**（描述性 + 断言）：主跑 1000 帧里含 ≥ 2 射线的抽头 3798/4000 = 94.95%，平均 16.07 射线/帧，抽头最多 11 射线；P1 管线其余部分与信道替换无关——对帧 {0, 1, 2, 500} × ρ{.3, .5} 断言 info、coded、data、pilot、noise 与 channel_seed 与 `p1_driver.generate`（同 E2CJ 种子函数）逐位相同（0 处差异），并对 16 个 (帧, ρ, SNR) 执行 `ctx.hd.observe` 的 P1 观测约定断言。
- **CG0**（附加）：簇几何拷贝与冻结函数逐位相等（20 帧）。

## 7. 成本（上限 24 core-hours，单线程分片，保留 ≥ 16 核空闲）

冒烟实测（同机、各 12 个触发单元，全部 8 臂；门+冒烟与两个冒烟同时在跑，负载约 12）：F0 ≈ .26–.27 s/键；帧生成 R ≈ .13 s/(帧,场景,ρ)（摊到 8 个 SNR），C ≈ .11 s/键（无摊销）；各臂平均秒数 R / C：A1 .166/.174、A2 .181/.183、A3 .143/.150、A1g .172/.180、A2g .166/.172、A2n .175/.179、A5 .045/.045、A7 .356/.363（A7 比 F0 多 .09 s）；8 臂合计 R 1.40 s/单元、C 1.45 s/单元。
估计（核时）：R 32000 键 × .28 s + 约 8190 触发 × 1.40 s ≈ 5.7；C ≤ 8000 键（全部网格点）× .39 s + ≤ 8000 触发 × 1.45 s ≈ 3.9；校准 1600 键 × .29 s ≈ .13。隔离合计 ≈ 9.7；E-1 实测满载并行时每单元慢约 1.5 倍 → 约 14.5；即使慢 2 倍也约 19.4 < 24。分片默认：run_R 64、run_C 32（可同时跑，共 96，保留 ≥ 16 核）、calibrate 50。超限即停并报告。

## 8. 运行手册

`launch_e2.sh` 在 tmux `g_e2` 内运行：`MODE=gate`（cgate + 20 分片 G1–G5 + 两个冒烟）、`MODE=calibrate`（→ `out/calibrate/GRID.json` + md5）、`MODE=run_R`、`MODE=run_C`（读 GRID.json）、`MODE=agg`。每次开跑前核对负载。失败分片原样保留并记录原因，不重试不换配置。回传只含小文件（分析 md/json、manifest、GRID.json、gates、STATUS、config_shard000、日志）；行数据留 deinlab（gzip + md5 清单，全路径写入本地 `REMOTE_ROWS_MD5.txt`）。

## 9. 局限与回滚

局限：单接收机族、单码、QPSK、N = 1024；C 族只有一种簇律（Jakes-4）；`neardup` 阈值 .5 是按定理选定的单点，不扫描；结论条件化在 F0 失败子集；C 族接收端仍是每时延单 Doppler 的路径模型，真值射线多于其可表示数。回滚：删除新目录与任务产物即可，冻结文件未动；失败运行原样保留。

## 10. 与 design.md 的执行期偏差与事实

1. 守卫内核只新增 `geometry_validation_guard.py`（+ 谓词模块 `codelay_guard.py`），仍导入 E-1 的 `geometry_reopen_variant.py`（它本就无需守卫）。compact 路径的守卫并入 duplicate 的 `equal` 矩阵（语义 = 其他路径无冲突）。局部试探的守卫拒绝复用 `local_duplicate_rejections` 计数与 `valid=False` 记录（无单独计数器）。
2. 冒烟帧：R 冒烟用 P1 帧 0..19 的触发单元（5.0/6.0/7.0 dB；本就用于 G4，主跑帧 3000..3999 全程未被看到）；C 冒烟用帧 9000..9011、临时 SNR 10 dB，**仅冒烟**（行内 `smoke=true`，不得并入主分析）。
3. 簇几何拷贝参数化了流域（冻结代码硬编码 CLUS）；功率归一在冻结的 Σ|g|²=1 之上再做数值归一（编排者要求）。
4. 校准 FER 以信息比特错误定义；"与 20 dB 取较小者"解释为对网格每点封顶 20 dB 并合并重复；20 dB FER 恰为 .95 判 OK（".95 以下含"）。
5. D2/D1 的不可评估处理（§5）、D3 对 C 族信息性 ρ 的合并、信息量门计"救回"= A1 成功且 F0 有错，均为 design 未明文的补充；R 与 C 都记录 F0 成功但校验子 ≠ 0 的触发单元数（E-1 为 9/16379），不另作处理。
6. R 与 C 的非触发键也各写一行（仅 F0 字段），行数 = 键数；A7 行内 `g5_ok`，聚合要求全为真。
7. 统计原语（McNemar 精确检验、Holm、bootstrap、百分位 CI）从冻结的 `tf_cstate_e1_20261017/e1_agg.py` 只读导入；McNemar 另报 log10 p。

## 11. 来源与哈希

冻结源 md5：`SOURCE_MD5.txt`（28 个文件：E-1 清单 20 个 + 被只读导入的 E-1 变体/驱动代码），运行时由 `e2_driver.check_frozen_md5` 对已加载模块逐一复核并写入每个 `config_shard*.json`。本目录代码 md5 见 `CODE_MD5.txt`（本文件自身的 md5 由各 config 的 `own_md5` 在开跑时记录）。
