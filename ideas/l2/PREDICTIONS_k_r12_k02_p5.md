# Pre-registration — `k_r12_k02_p5`（子卡 `I-20261125-k02` 第 8 步 Astra 终审 `P_3 / P_4 / P_5` 机制配对诊断）

> 冻结时间：2026-11-25 21:00 (Asia/Shanghai，已合入 Round-12 Sol #1–#5 全部阻断与非阻断修订，将经 Sol #6 复核 `GO` / `GO_WITH_NONBLOCKING` 后上 `deinlab` 8 核执行) · Runner：`k`（`[高要求]` 组，`gemini-4-neon`）· 对应卡片：[`I-20261125-k02`](../cards/I-20261125-k02.md) · 对应终审：[`r11-astra-k02-killarg-20261125.md`](../reviews/r11-astra-k02-killarg-20261125.md)
> **定位与历史裁决保留声明**：本次检验按 Astra 终审与 `round-12.md` 单列为**机制诊断**，完整保留前两次冻结裁决不受任何修改或覆盖：初跑 [`summary_k_r11_k02.json`](out_k_r11_k02/summary_k_r11_k02.json)（`seed = 2026132501`, `PASS_PRIMARY = false`）与确证复跑 [`summary_k_r11_k02_conf.json`](out_k_r11_k02/summary_k_r11_k02_conf.json)（`seed = 2026142501`, `PASS_PRIMARY = true`）。
> **锁定输出与全新零重叠种子**：正式 `--mode full` 仅允许独占原子写入（先在内存 `json.dumps(..., allow_nan=False)` 严格序列化，写入同目录临时文件并 `fsync` 后经 POSIX 原子 `os.link` 独占发布并清理临时文件，任何序列化或中途写盘错误均不会在正式路径留存截断文件，且已有正式文件时直接抛出 `FileExistsError`）规范路径 `ideas/l2/out_k_r12_k02_p5/summary_k_r12_k02_p5.json` 或 `/data/guoyikun/tmp/funnel_k_r12/summary_k_r12_k02_p5.json`；**全新主种子 `seed = 2026162501`**（显式排除历史与开发种子源 `[2026112501, 2026122501, 2026132501, 2026142501, 2026152501, 999888777, 888777666]` 的前 `15,000` 个场景种子及 `G1` 诊断种子 `2026169900`，零交集；`--mode smoke` 使用隔离种子 `args.seed + 777777` 并额外排除 `2026162501` 前 `15,000` 个种子）。

## 1. 参试臂与单因素配对设计（严格响应 `P_3`、`P_4`、`P_5`、规则 ⑤ 与 Sol #1–#3 全部修订）
全部 **8 条臂**运行在**完全相同的全新 `S1 (-11.0 dB)` 三维空地弯曲杂波（`OSR=8 RRC β=0.25`）配对场景**上，全部采用 `k_l2_r11_k02_conf.py` 同一全图 4,089 格 `1×1 CUT` 盲评分器 `score_cut_full_map` 与严格的先报警后定位判定（`|Δni| <= 2` 且 `|Δti| <= 1`），共享完全相同的独立无目标校准集（`N_cal = 1500`）与独立无目标验证集（`N_val = 2000`）标定并检验 `Pfa_map = 1%`：

1. **`ridge_afdm_st`**（盲实用主方案）：原样复用 `k_l2_r11_k02_conf.py` 逻辑（24/193 导频、仅知粗线性斜率 $\mu$ 的 `Band-3+LOS` 前端 + 整帧 Exact-RC QR + `refine_symbols_joint_em` + 第二次 QR）。
2. **`ofdm_p5_full`**（**核心 `P_5` 机制诊断臂**）：**原样复用父卡 `k_l2_r10_k01.py` 曲脊特权前端**（`base.TAU_Q_OFDM`、`base.HQ_MOV`、`base.NU_Q_OFDM`、利用真实发射载荷 `Xf_bp` 与无目标无噪杂波回波 `paths[:N_CLUT+1]` 拟合 `reg=1e-3`，直接调用未改动的 `base.run_ofdm_joint(..., n_em=3, genie_g=gg, reg=1e-2)`），随后**直接接入子卡 `k_l2_r11_k02_conf.py` 普通块导频 OFDM 的完整后端**（第一次 `qr_project_exact_rc` → `refine_symbols_joint_em(..., Hq_of_em, pil_syms=(0,))` → 第二次 `qr_project_exact_rc` → `compute_rd_map`）。同步记录反馈前误符率 `ser_pre_fb` 与反馈后误符率 `ser_post_fb`。
3. **`ofdm_p5_pre_fb`**（单因素 `P_4` 消融）：与 `ofdm_p5_full` 共享完全相同的父卡曲脊特权前端输出，仅执行第一次 `qr_project_exact_rc`（跳过整帧符号更新与第二次投影），单因素隔离 `P_4` 反馈步的独立效应。
4. **`ofdm_p5_lin_pgrid_full`**（**同网格、同拟合、同解调器、同完整后端的纯曲率单因素 `P_3` 消融**）：与 `ofdm_p5_full` 保持**完全相同的父卡时延节点网格 `base.TAU_Q_OFDM`（`2.022..12.274`）、完全相同的 `fit_genie_g_parent_verbatim` 拟合、完全相同的 `base.run_ofdm_joint` 求解器、完全相同的子卡完整后端**，**仅将脊多普勒曲线由曲脊 `base.NU_Q_OFDM` 换为同网格直脊 `NU_Q_LIN_PGRID = [DNU_LOS_MOV, MU_MOV * base.TAU_Q_OFDM[1:]]`**。同步获得等虚警全图定位率差与逐场景配对误符率差，实现曲率效应 100% 干净归因。
5. **`ofdm_genie_child_full`**（子卡直脊特权前端 + 完整后端）：采用子卡 `k_l2_r11_k02_conf.py` 直脊特权前端（`k02.TAU_Q_LIN` `[1.8..12.6]`, `k02.HQ_OFDM_LIN_MOV`, `k02.run_ofdm_blkpil_blind`），接完全相同的子卡完整后端；与臂 4 配对隔离“时延节点跨度 + 求解器超参”的联合定位率效应。
6. **`ofdm_genie_child_1pass`**（原样 `k02_conf` `ofdm_genie_st`）：子卡直脊特权前端 + 仅第一次 QR，与臂 5 配对隔离直脊前端上的 `P_4` 反馈效应。
7. **`ofdm_blkpil_st`**（原样 `k02_conf` 实用等开销盲 OFDM 对照）：共享同一 `syms_bp` 突发与同一完整后端、仅使用粗线性斜率先验的实用盲块导频 OFDM。
8. **`known_ofdm_bp_st`**（已知载荷上界）：在与 `ofdm_p5_full` 完全相同的 `syms_bp` 突发上使用真实发射符号过 `qr_project_exact_rc`，标定 0% 误符上界。

此外，在全部 `N_pos = 300` 个有目标场景上输出完整 `P_3` 三子因素逐场景配对误符率分解（全部附配对 95% CI）：纯曲率差（`ser_lin_pgrid_psolver - ser_curv_pgrid_psolver`）、纯时延网格跨度差（`ser_lin_cgrid_psolver - ser_lin_pgrid_psolver`）与纯求解器超参差（`ser_lin_cgrid_csolver - ser_lin_cgrid_psolver` 及 `ser_curv_pgrid_csolver - ser_curv_pgrid_psolver`）。

## 2. 独立 `deinlab` 开发集实测离散度与红线 5 完整包络半宽预注册表（响应 Sol #2/#3）
- 独立 `deinlab` 8 核开发集（`N_cal_dev = 200, N_pos_dev = 50`，种子取自隔离源 `rng(888777666)` 第 `500..749` 项，全部位于正式 `2026162501` 排除的前 `15,000` 个种子内，零重叠）逐臂全量实测：
  - `ridge_afdm_st`：`Thr = +11.68 dB`, `Pd_loc = 100.0% (50/50)`, `Mean = +20.68 dB`, **`minPos = +19.71 dB`**, `SER = 3.73% -> 1.15%`；
  - `ofdm_p5_full`：`Thr = +14.24 dB`, `Pd_loc = 100.0% (50/50)`, `Mean = +20.21 dB`, **`minPos = +18.86 dB`**（最差单场景仍高出 `1%` 门限 `+4.62 dB`）, `SER = 0.42% -> 0.40%`；
  - `ofdm_p5_pre_fb`：`100.0% (50/50)`, `Mean = +20.29 dB`, `SER = 0.42%`；
  - `ofdm_p5_lin_pgrid_full`：**`0.0% (0/50)`**, `Mean = +12.40 dB`, `SER = 19.27% -> 11.70%`；
  - `ofdm_genie_child_full`：`6.0% (3/50)`, `SER = 19.27% -> 12.11%`；`ofdm_genie_child_1pass`：`0.0% (0/50)`, `SER = 19.27%`；
  - `ofdm_blkpil_st`：`0.0% (0/50)`, `SER = 74.19% -> 74.72%`；`known_ofdm_bp_st`：`100.0% (50/50)`, `Mean = +20.74 dB`。
- **正式样本量锁定**：**`N_cal = 1500, N_val = 2000, N_pos = 300`**（`cal/val` 与 `k02_conf` 1:1 对齐，`deinlab` 8 核实测速度换算预计墙钟 `~32.6 min / ~4.35 core-h <= 5.0 core-h`）。
- **抗稀有高误符退化的单一精确 `[0, 1]` 有界均值恢复门（响应 Sol #3 #2）**：
  - 主初始化恢复门仅采用**非渐近、无分布假设的精确 Hoeffding–KL 有界 `[0, 1]` 双向 95% 置信区间**（Hoeffding 1963, *JASA* 58:13–30, Theorem 1：$P(\bar X \le x) \le \exp(-n D_{\mathrm{KL}}(x \| \mu))$），要求 **`ci95_hoeffding_kl[1] < 6.0%`**（对比同网格直脊 `19.27%` 留出 `>3×` 物理间隔）且 **`half_width <= 1.50 pp`**（`25% × 6.0%`）。中位数及其精确二项顺序统计量 95% 区间（`n = 300` 对应 1-indexed 第 `133..168` 顺位）**仅作描述性诊断读数输出，不参与布尔门控**，避免未设红线 5 精度门的冗余子条件。
- **直接重抽实测完整包络半宽（响应 Sol #3 #1）**：
  - 追平分支（`15 pp` 裕量，半宽上限 `3.75 pp`）与排他/撤回分支（`50 pp` 裕量，半宽上限 `12.50 pp`）检验的是**同一对估计量 `Delta_P5` 与 `Pd_loc(ofdm_p5_full)`**。
  - 在独立 `deinlab` 开发集（`200 cal + 50 pos`）上做 `120` 轮完整数据集重抽至正式规模 **`(N_cal = 1500, N_pos = 300)`**（每轮均含 `N_cal = 1500` 门限重估 + 400 轮双重自助与 Tango / Clopper-Pearson 保守包络），直接测得以下完整包络半宽（**说明**：上述估算均针对开发集观测分布；若正式运行意外落入门限悬崖聚集区导致完整包络半宽超限，运行时显式红线 5 精度门将直接拦截并输出 `INCONCLUSIVE_PRECISION_INSUFFICIENT`，绝不发布超精度限的机制结论）：

| 诊断判据 | 指标与预注册门槛 | 门槛距离 25% 半宽上限 | 独立开发集 `MC120 @(1500, 300)` 完整包络实测半宽（含 `N_cal=1500` 门限重估） | 满足红线 5 |
|---|---|---|---|---|
| **父卡初始化恢复 (`P_3`)** | `ser_pre_fb` Hoeffding–KL 95% 上界 `< 6.0%`（唯一恢复门） | **`<= 1.50 pp`** | 均值 **`1.17 pp`**（中位 `1.17`、**p90 `1.20`、最大 `1.22 pp <= 1.50 pp`**）；95% 上界最大 `2.45% < 6.0%` | **是** |
| **`Delta_P5` 追平与排他共测指标 (`P_5`)** | 追平上界 `<= +15 pp` / 排他下界 `>= +50 pp` | **`<= 3.75 pp`**（追平） / **`<= 12.50 pp`**（排他） | 开发实测 `Delta_P5` 完整包络半宽：均值/中位/p90/最大均为 **`1.26 pp`**（`<= 3.75 pp` 且 `<= 12.50 pp`）；无门限悬崖的双向 `225/75` 参考 Tango 半宽 `9.76 pp`，若正式运行出现门限悬崖致完整半宽 `> 12.50 pp` 由运行时精度门拦截为 `INCONCLUSIVE` | **是** |
| **单臂 `Pd_loc(ofdm_p5_full)` (`P_5`)** | 追平下界 `>= 85%` / 撤回上界 `< 50%` | **`<= 3.75 pp`**（追平） / **`<= 12.50 pp`**（撤回） | 开发实测 `Pd_loc(ofdm_p5_full)` 完整包络半宽：均值/中位/p90/最大均为 **`0.61 pp`**（`<= 3.75 pp` 且 `<= 12.50 pp`）；若正式运行出现门限悬崖致完整半宽超限由运行时精度门拦截为 `INCONCLUSIVE` | **是** |
| **实用盲对照锚 (`P_1`)** | `Pd_loc(ridge_afdm_st) - Pd_loc(ofdm_blkpil_st)` 95% 下界 `>= +50 pp` | **`<= 12.50 pp`** | 开发实测完整包络半宽：均值/中位/p90/最大均为 **`1.26 pp <= 12.50 pp`** | **是** |

## 3. 门检、等虚警验证与预注册五态机制裁决（纯置信界 + 有效性前置锁 + 非有限免疫原子落盘）
- **`G1_PARITY_AND_EXACT_CUT`**：
  1. 合成 `1e10` 与真实 `S1` 全图精确 CUT 相对误差严格有限且 `< 1e-12`；
  2. 在诊断场景 `2026169900` 上，将实际运行的 `eval_p5_scene_worker` 输出与独立内联复现的父卡 `k_l2_r10_k01_pfa.py:268-288` 参考路径直接对拍（SER 差与分数相对差有限且 `< 1e-12`、峰坐标 `peak_idx` 完全一致）；
  3. 将实际运行的 `eval_p5_scene_worker`（`ridge_afdm_st`, `ofdm_blkpil_st`, `ofdm_genie_child_1pass`）与 `k_l2_r11_k02_conf.eval_scene_worker` 直接对拍（分数、SER 差有限且 `< 1e-12` 且三臂峰坐标 `peak_idx` 全部一致）。
  4. **全链路逐场景非有限拦截与原子独占落盘（响应 Sol #3/#4）**：所有解调误符率经 `_strict_ser` 在符号比较前拦截任意 `NaN/Inf`；每场景 `rdp` 与峰值分数在 `record_arm` 记录非有限标志；阈值比较与统计聚合前经 `_scan_raw_nonfinite` 与 `evaluate_arms` 逐场景、逐臂核查全量 `cal/val/pos` 分数、误符率与 `p3_subfactors`，任意非有限值立即记入 `invalid_reasons`、置 `RAW_INPUTS_FINITE_OK = false`、`c1_pass = false`、`DIAGNOSTIC_VALID = false` 与 `DIAGNOSTIC_OUTCOME = "INVALID_DIAGNOSTIC_DO_NOT_USE"`；输出前再经递归 `_sanitize_nonfinite` 兜底清洗并采用“内存严格序列化 → 同目录临时文件写入+`fsync` → POSIX 原子 `os.link` 独占发布”写盘，绝不留截断文件。
- **`C1_VALIDITY`（8 臂精确 Beta-Binomial FWER + 双主臂防膨胀硬帽）**：精确顺序统计量门限 `a = 15, b = 1486`（`E[P] = 0.9993%`）；8 臂同时检验 `alpha_each = 0.05 / 8` 接受区间 `k_val ∈ [5, 42]`（`[0.25%, 2.10%]`，纯统计并集 FWER 上界 **`3.586% <= 5.0%`**）；对 `P_5` 主对比双方（`ridge_afdm_st` 与 `ofdm_p5_full`）对称附加验证虚警率防膨胀硬帽 `<= 1.75%`（`k_val <= 35/2000`，去重并集误拒上界 **`7.264%`**）。
- **`DIAGNOSTIC_VALID === G1_PARITY_AND_EXACT_CUT AND REAL_MAP_EXACT_CUT_OK AND RAW_INPUTS_FINITE_OK AND C1_VALIDITY`（且零非有限清洗触发）**。
- **预注册五态纯置信界裁决（`DIAGNOSTIC_OUTCOME`，零点估计触发）**：
  1. **`INVALID_DIAGNOSTIC_DO_NOT_USE`**：若 `DIAGNOSTIC_VALID == false` → 立即阻断，不得用于改写卡面主张。
  2. **`OFDM_CATCHES_UP_NARROW_CLAIM`**：`DIAGNOSTIC_VALID == true`、`ser_pre_fb` Hoeffding–KL 95% 上界 `< 6.0%`（半宽 `<= 1.50 pp`）、`Delta_P5` 95% 包络上界 `<= +15 pp`（半宽 `<= 3.75 pp`）、`Pd_loc(ofdm_p5_full)` 95% 包络下界 `>= 85%`（半宽 `<= 3.75 pp`）、实用盲 `ofdm_blkpil_st` 95% 下界落后 `>= +50 pp`（半宽 `<= 12.5 pp`） → 将卡片第 22 行收窄为“共享粗线性斜率先验下，斜脊 AFDM 优于全部四种已测等开销 OFDM 捕获方案；若向 OFDM 提供使用真实发射载荷、无噪杂波回波与三维曲率曲线的特权曲脊初始化（填入本轮实测反馈前/后误符率及其 95% 区间）并接同一完整整帧后端，OFDM 全图盲搜定位可追平 AFDM”。
  3. **`OFDM_LOW_SER_STILL_FAILS_RETRACT_STAGE1_EXPLANATION`**：`DIAGNOSTIC_VALID == true`、初始化恢复门通过，且（`Delta_P5` 95% 包络下界 `>= +50 pp` **或** `Pd_loc(ofdm_p5_full)` 95% 包络**上界** `< 50%`），且两项半宽均 `<= 12.5 pp` → 撤回卡片第 22 行“第一关解不出载荷导致零定位”的单一解释。
  4. **`INCONCLUSIVE_PRECISION_INSUFFICIENT`**：`DIAGNOSTIC_VALID == true`，但对应判决所需的红线 5 半宽门未满足 → 不改写卡面强主张，如实报告精度不足。
  5. **`INTERMEDIATE_PARTIAL_GAP` / `PARENT_INIT_NOT_RECOVERED`**：其余有效高精度情形 → 如实汇报 `2×2` 与三子因素分解并严格按实测边界更新第 22 行。

## 4. 跑前主观概率预测
- `P(G1_PARITY_AND_EXACT_CUT) = 0.99`；`P(C1_VALIDITY) = 0.93`；`P(OFDM_CATCHES_UP_NARROW_CLAIM) = 0.92`；`P(OFDM_LOW_SER_STILL_FAILS) = 0.01`；`P(INTERMEDIATE_OR_INCONCLUSIVE) = 0.07`。
