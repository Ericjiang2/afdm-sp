# S0 笔记：冻结生成器的运行时抽样路径、常数与修复实现

任务：`.trellis/tasks/10-15-tcom-reference-frame`，阶段 S0（协议 §2）。数字结果见 `out/s0/GATES.md` / `gates.json`。
路径缩写：`UP` = `experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/`；
`HL` = `experiments/headroom_ladder_20261008/`；除非另注，`afdm_*.py` 等文件名均指 `UP/afdm_sp_joint_unrolled/` 下的运行时副本。

## 1. 运行时抽样路径（deinlab 上 `sys.modules` 实测，2026-10-15）

```
HL/driver.py:209-224  generate_base(ctx, rho, snr, frame, seed_fn)         # rho shim = copy.copy(ctx.system)
 -> :215  ctx.make_frame = afdm_sp_joint_unrolled/budgeted_support_eval.py:114-129  make_frame(split=2, rng_factory)
      :117 channel_seed = rng_factory(.., component 1).integers(0, 2**31);  :118 np.random.seed(channel_seed)
      :119 system.generate_channel_matrix()           -> afdm_env.py:505-674
             :527-528 generate_uwa_channel()          -> afdm_env.py:285-359   (路径 delay/gain/velocity 抽样 + 重抽)
             :532-533 delay bin l_i;  :550-554 k_real;  :583-613 Dirichlet 虚拟原子;  :631-641 Frobenius 归一;  :644 H_time
      :120-127 info / coded / data / pilot / noise (components 2, 3), y = H_eff (pilot+data) + noise
 -> :223  ctx.physical_observation(raw, shim, prefix_length = shim.l_max_cap)   = supplement_g1.py:72-125
      物理算子 physical_channel_matrix (supplement_g1.py:18-42)，核对 propagate_cpp (supplement_pilots.py:28-38)
      cpp (supplement_pilots.py:20-25)，transform (supplement_pilots.py:13-17)；GENERATOR = 'physical_cpp_untruncated' (g1:13)
 -> 观测: y = physical_y + sqrt(sigma2) noise (g1:122)；reuse_at_snr (g1:128-138) 只换噪声缩放
```

- 运行时实际导入的 `afdm_env`：`UP/afdm_sp_joint_unrolled/afdm_env.py`（`receiver.py:9-10` 把 `UP` 插入 `sys.path[0]`；`sys.modules['afdm_sp_joint_unrolled.afdm_env'].__file__` 实测）。
  md5 `7e8da04165de5ee0c2e85230d485d32d`，与仓库根 `afdm_sp_joint_unrolled/afdm_env.py` 逐字节相同；
  `loop9_cache_features / run_classical_baselines_python / budgeted_support_eval / supplement_g1 / supplement_pilots / e1_ldpc / budgeted_support_diagnostics` 同样 md5 一致。
  仓库内其他 `afdm_env.py`（`legacy_for_ablation/*`、`paper_figure_code/*`、`afdm_sp_joint_unrolled/outputs_ce_state_20260915/source-v*/`、`.mission/**/dispatch/source-*/`）运行时都不被导入。
- `system` 类：`AFDMSystem(AFDMEnvMixin, AFDMModelsMixin, AFDMTrainerMixin, AFDMBaselinesMixin)`（`system_config.py:20`），其余 mixin 不覆盖 `generate_uwa_channel` / `generate_channel_matrix`。
- 构造链：`receiver.py:26 context()` -> `run_frozen_i1_smoke.py:105 _make_config_a(1024, 2., 8, 10., 4.)`（`loop9_cache_features.py:57-75`）-> `_make_system_variable_N`（`run_classical_baselines_python.py:41-94`）。
  `HL/driver.py:180-183` 断言 `N_total == 1024, l_max_cap == 102, rho == .5`。

## 2. 常数（`ctx.system` 实测值；file:line）

| 量 | 值 | 来源 |
|---|---|---|
| N_total | 1024 | `_make_system_variable_N`（N=32 x M=32，AFDMSystem 构造于 `run_classical_baselines_python.py:61`） |
| P_paths | 8 | `loop9_cache_features.py:59`（`afdm_env.py:45` 默认 10 被覆盖） |
| fs, Ts | 16 kHz, 62.5 us | `loop9_cache_features.py:64-67`（`afdm_env.py:40-42` 默认 8 kHz / 125 us 被覆盖） |
| delta_f | 15 Hz（硬编码，未随 fs 更新）；fs/N = 15.625 Hz | `afdm_env.py:36` |
| delay_resolution | 1/(N delta_f) = 65.104 us（!= Ts） | `afdm_env.py:54` |
| tau_spread / att_dB / tau_mean | 10 ms / 20 dB / 0.8 ms | `loop9_cache_features.py:63`；`afdm_env.py:47-48` |
| v_mean / v_std / c_sound / fc | 2.0 m/s / 0.5 m/s / 1500 m/s / 12 kHz | `loop9_cache_features.py:62`；`afdm_env.py:38-39,50` |
| l_max_cap | 102 = max(N//10, 12) | `run_classical_baselines_python.py:63-64` |
| k_max_cap | 2 = ceil(N v_max fc/(c fs)), v_max = 3.5 | `loop9_cache_features.py:68-70`（`_make_system_variable_N` 内 fs=8 kHz 时先得 4，随后被覆盖） |
| k_clip（生成器 Doppler 截断） | min(k_max_cap, N/2 - k_guard - 1) = 2 | `afdm_env.py:552-554` |
| c1, c2 | 5/(2N) = 0.00244141, (sqrt2 - 1)/(2N^2) | `loop9_cache_features.py:73`；`afdm_env.py:203-205` |
| CPP 前缀长度 | `prefix_length = shim.l_max_cap = 102` | `HL/driver.py:223` |
| 陈旧时延上限（D1） | `max_delay_idx_bar_supported = 54`（在 Ts = 125 us 时算出：floor(102 x 65.104e-6 / 125e-6) + 1），fs 改为 16 kHz 后未重算；正确值 107（旧栅格）/ 103（D2 栅格） | `run_classical_baselines_python.py:76-78`；`loop9_cache_features.py:64-67` |
| 重抽 | 最多 `uwa_resample_max_tries = 32` 次，然后 clip | `afdm_env.py:80,311,346,353-359` |
| Dirichlet | k_leak = 2（每径 5 个虚拟原子），1% 相对功率剪枝，|k_eff| > k_clip 丢弃 | `afdm_env.py:89-90,583-613` |

## 3. 三条抽样律（冻结版）

- **时延律**（`afdm_env.py:313-316`）：8 个增量 ~ Exp(均值 0.8 ms)，`inc_idx = max(1, ceil(inc / Ts))`（平均约 13.3 采样点），`delay_index = cumsum(inc_idx)`，
  `delay_s = (delay_index - 1) Ts`。**时延跨度由 tau_mean x P 决定，不是 tau_spread**；tau_spread = 10 ms 只进入功率时延谱（下）。
  自然（不截断）律的最大时延均值约 105 个采样点，因此 102 的接收机银行边界会拒绝约 48.6% 的自然抽样（D1+D2 实测首次接受率 51.4%）。
  多普勒校正 `delay_idx_bar = max(1, ceil(delay_index/(1 + a_i)))`（`:337-340`）在该参数区**数值上不起作用**（a_i d < 1 时 ceil(d - s) = d；实测 5 万次抽样 `idx_bar == idx`）。
  映射到 bin：`l_i = clip(round(delay_s / delay_resolution), 0, l_max_cap)`（`:532-533`）。
- **增益律**（`:319-330`）：`path_var = exp(-alpha delay_s)`，alpha = ln(10^(20/10))/tau_spread；`amp ~ Rayleigh(sigma = sqrt(path_var 2/(4 - pi)))`，ℓ2 归一；相位 ~ U[0, 2 pi)。
- **Doppler 律**（`:333-334,550-554`）：`v_i = |N(2, 0.5^2)|` m/s（独立同分布，全为正），`k_real = (v_i/c) (fc/fs) N = 0.512 v_i`，均值 1.024，sd 0.256，截断到 [-2, 2]（只有 5.9e-5 的路径被截断）。
- **功率归一**（`:631-641`；`supplement_g1.py:14,74-78`）：G0 `H_eff` 由 Dirichlet 虚拟原子构成，缩放到 `||H_eff||_F = sqrt(N)`；该缩放 `scale` 乘到物理增益 `g_i = g_i_raw scale`，
  物理算子直接复用 `g_i`（`GAIN_RULE = reuse_g0_physical_gains_without_rescaling`），因此 `||h||_F^2 / N` 不严格等于 1。
  scratch 实测（测试熵帧 100-299，rho .5）：flags off 均值 1.025（0.858-1.331）；D1+D2 均值 1.022（1.003-1.401）；**D1+D2+几何 Doppler 均值 1.122（1.007-1.450）**——
  几何律下更多 Dirichlet 旁瓣落在 |k| > 2 被丢弃，`scale` 变大。名义 SNR（sigma2 对数据功率）不变，但信道平均数据 SNR 在 G 场景比 U 场景高约 0.4 dB（均值）。

## 4. 接收机银行

- **F0 导频前端**（`experiments/sp_afdm_frozen_reviewed_20260921/src/receiver.py:124`，`pilot_front`，被 `sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:16` 调用）：`ls = repeat(arange(l_max_cap + 1), 5)`，`ks = tile(arange(-2, 3), l_max_cap + 1)`，
  即时延 0..102 x 整数 Doppler -2..2 = 103 x 5 = **515 列**；再由 `BaselineInitializer('B0-p2-s0.5')` 取最多 40 个。
- **CSTATE 银行**（`tf_cstate_validation_20260922/run_validation.py:57-63,226-227` 调 `geometry_validation.reopen_geometry`，银行构造 `geometry_validation.py:101-106 _bank`）：
  `max_delay = system.l_max_cap = 102`，Doppler -3..3 步长 0.25（25 个值），时延 0..102 = 103 x 25 = **2575 原子**；LOCAL20 与 CSTATE20 同银行（`max_edits` 0 / 2）。
- 两个银行的时延上界都是 102，所以修正律必须显式截断在 102（不是 107）；Doppler 窗口 F0 为 ±2、CSTATE 为 ±3，UWA 律（<= 2）和几何律（nu_max = 1.62）都在窗内。

## 5. gen_fixed.py 的实现与我做的解释

- 复制范围：`generate_uwa_channel`（draw_paths / one_attempt）、`generate_channel_matrix` 到 `H_eff`（paths_to_channel，**不构造 `H_time`**，make_frame 本来就丢弃它）、`make_frame`、`driver.generate_base`。
  使用 `np.random.RandomState(channel_seed)`（与 `np.random.seed` + 模块级调用逐比特等价），不改全局状态。开关全关时 1000/1000 帧逐比特一致（G-S0a）。
- **D1**：判据为显式时延 bin 截断 `max(round(delay_s/res)) <= 102`，无上限重抽、无 clip 回退（安全上限 1e5 次，实测最大 17 次/帧）。
  按最终 fs/Ts 计算的 cap 公式（`afdm_env.py:78-79` 的公式）给出 107（旧栅格）/ 103（D2 栅格），测试证明二者对所有索引等价。
- **D2**：`delta_f := fs/N`（`delay_resolution == Ts` 断言），`l_i = delay_idx_bar - 1` 直接按采样点。
- **D3**：`geometric` 取 `k = 1.62 cos(theta)`，theta ~ U[0, 2 pi) 来自 `SeedSequence([channel_seed, 0x47454F4D])` 独立流（driver 的 rng_factory 只登记 3 个分量，不能请求第 4 个）。
  U/G 两个场景的时延、增益抽样（含重抽次数）**完全相同**，只有 Doppler 不同（实测 60/60 帧 `l_i`、`g_i_raw`、attempts 相同）；`velocities` 仍从流中抽取以保持对齐。
  多普勒-时延校正沿用流中的正 a_i（几何律下用带符号的 a_i 会让负 Doppler 径的 ceil 多加 1 个采样点，重新制造同时延叠路）；参数里的 `doppler_a / velocities_ms` 报告的是实际使用的带符号值。
- **nu_max = 1.62**：冻结律 `generate_uwa_channel` 的 200000 帧 x 8 径 = 1.6e6 次抽样，|k_real| 99% 分位 1.61963，20 块 MC 标准误 0.00087；解析折叠正态值 1.61955；取 3 位小数 1.620 冻结为 `gen_fixed.UWA_NU_MAX_99`。
  注意：几何律的 |k| 分布是反正弦型，50% 分位 1.145（UWA 为 1.024）、90% 分位 1.600（UWA 为 1.353）；99% 分位按协议匹配，但整体比 UWA 律更靠近窗边。
- **CPP 前缀决定**：冻结前缀 `l_max_cap = 102` 已经 >= 102，截断后最大时延 <= 102，所以**前缀保持 102 不变**（flags 关或开都是 102）；`gen_fixed.generate_base` 在 D1 开启时仍取 `max(102, 102, 最大时延)` 并把 `prefix_length / prefix_ge_max_delay` 写进 `diag['gen_fixed']`。
- **自然率比较的解释**：协议 G-S0b(i) 的"自然率"在 D1+D2 下结构性为 0（增量 >= 1 采样点、多普勒校正不起作用 -> 时延严格递增），所以通过条件退化为"两侧都是 0"，已在报告里写明并附上 D1-only（旧 0.96 栅格）的信息性行：
  截断把栅格错配产生的叠路率从自然的 2.08% 推到 2.54%（z = 6.9，只说明在旧栅格上截断本身有偏，不属于门限）。
- **KS 检验**：对象是时延跨度 `max(l) - min(l)`（门限），最大时延作为补充；直接拒绝采样器是独立的向量化实现（`numpy.default_rng`，按声明律 P = 8, Exp(0.8 ms), ceil 到 62.5 us, bin = 采样序号 - 1, 拒绝 max > 102）。
  门限结果 p = 0.051；另外 6 个其他种子的诊断（不属于门限，未调整任何阈值）p = 0.50 / 0.94 / 0.69 / 0.90 / 0.93 / 0.045，符合均匀分布，没有系统偏差。

## 6. 新增文件

`gen_fixed.py`、`s0_gates.py`、`launch_s0.sh`、`S0_NOTES.md`、`out/s0/{gates.json,GATES.md}`（deinlab 上另有 `out/s0/*.json` 各阶段文件与 `logs/`，rows 级细节留远程）。

## 7. 修订 A1：`fix_energy`（protocol.md §10，用户选择方案 b）

- 新开关 `Flags.fix_energy`（默认关）：不再乘以 G0 的 Frobenius 缩放（`afdm_env.py:631-641` 的 `scale`，它在"|k| 截断到 ±2 的 Dirichlet 虚拟原子 DAFT 矩阵"上计算，随 Doppler 抽样变化）；`scale = 1`，`g_i = g_i_raw`（单位范数 Rayleigh 幅度 x 相位），每帧总路径功率为 1。
  时延互不相同（D1+D2 保证）时，物理算子各径在不同对角线上、Frobenius 正交，故 `||H||_F^2 / N = sum|g_i|^2 = 1`。
- G-S0d：U（D1+D2+E, uwa）与 G（D1+D2+E, geometric）各 200 帧，三种方式（`diag`、`raw['H']`、独立重建的 CPP 算子）的 `||H||_F^2 / N` 与 1 的最大偏差分别为 5.8e-15 与 7.3e-15（门限 1e-9），路径总功率偏差 6.7e-16；
  同样的帧在不开 `fix_energy` 时 U 的能量为 1.002-1.293（均值 1.019），G 为 1.007-1.422（均值 1.118）。
- 开关全关：G-S0a 仍是 1000/1000 逐比特一致（rho .3 另 50/50）；G-S0c 对 5 个配置（off, D1+D2, D1+D2+geo, D1+D2+E, D1+D2+E+geo）各 20 帧均通过，最大误差 7.2e-13。
- 新代码 md5：`gen_fixed.py` cb9be5ea91c0a9b1863758ed598de1c6，`s0_gates.py` 0dc749a88ed75c4352175ba4c4bc44f7；`out/s0/gates.json` / `GATES.md` 为全量重跑后的结果（旧结果在新代码下全部复现，数字不变）。
