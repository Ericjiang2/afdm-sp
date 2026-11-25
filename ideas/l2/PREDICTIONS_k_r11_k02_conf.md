# Pre-registration — `k_r11_k02_conf`（子卡 `I-20261125-k02` 新鲜种子确证复跑：修正 `C1` 有限样本 Beta-Binomial FWER 与 `G0` 非饱和工作点）

> 冻结时间：2026-11-25 15:20 (Asia/Shanghai，已合入 Sol Call #7 全部五处静态审计修订，将经 Sol Call #8 复核 `GO` 后执行) · Runner：`k`（`[高要求]` 组，`gemini-4-neon`）· 对应卡片：[`I-20261125-k02`](../cards/I-20261125-k02.md)
> 原始首跑记录完整保留且受独占创建保护禁止覆盖：[`summary_k_r11_k02.json`](out_k_r11_k02/summary_k_r11_k02.json)（`seed = 2026132501`，物理/消融/压力全通，`PASS_PRIMARY = false` 仅因两项统计标定设置）。
> 本次确证复跑锁定独立输出路径 `ideas/l2/out_k_r11_k02/summary_k_r11_k02_conf.json`（`open(..., "x")` 独占创建，拒绝覆盖已有文件或首跑文件）与**全新新鲜种子 `seed = 2026142501`**（正式 `--mode full` 下硬锁，显式排除 `2026112501, 2026122501, 2026132501, 999888777` 的前 `12,000` 个场景种子，零交集；`--mode smoke` 改用隔离种子 `args.seed + 777777` 并额外排除 `2026142501` 前 `12,000` 个种子；前期开发对拍仅使用单场景 `1234567`，未触碰任何 `2026142501` 正式场景）。随本次换种同步更新的 7 个 `G1` 诊断场景种子为 `2026149900..2026149905`（`+38 dB` 无损伤静态健康检）与 `2026149999`（真实 `S1` 精确 CUT 误差校验）。

## 1. 相对首跑 `k_l2_r11_k02.py` 的透明变更（零物理模型、零接收机算法、零参试臂改动）
1. **代数等价的性能向量化**：将 `HQ_AFDM_MOV / HQ_STAT_0 / HQ_OFDM_MOV_LIN / HQ_OFDM_LIN_MOV / HQ_OFDM_LIN_STAT` 预堆叠为连续 `(Q, N, N)` 数组，在 `run_ofdm_blkpil_blind` / `run_ofdm_distpil_blind` / `ofdm_genie_st` 中改用单次 BLAS 矩阵乘 `(Hq @ v).T * ph[None, :]` 与 `np.tensordot`，并在 `ep_16_fast` 中将正定矩阵的 `la.inv` 替换为代数等价的 Cholesky 求解（保持默认 `check_finite=True`，分解失败直接抛错；单场景 7 主/消融臂对拍实测最大相对偏差 `3.65e-12`，无静默回退；预计 8 核墙钟从 `42.9 min` 降至 `~31 min / ~4.1 core-h`）。
2. **`G0` 静态非饱和工作点标定修正**：首跑 `G0 @ -18.5 dB` 上 `ridge_afdm_st = 96.7%` 与 `ofdm_comb_st = 99.2%` 双双超过 `92%` 非饱和上限。在 `k02` 外部 12 场景开发标定（种子 `999888777` 衍生开发探针，候选 `-21.5 dB` 与 `-22.0 dB`，三代表臂读数：`-21.5 dB` 为 `ridge_afdm_st 67% (+11.38 dB) / ofdm_comb_st 58% (+12.01 dB) / ofdm_blkpil_st 58% (+12.00 dB)`；`-22.0 dB` 为 `42% / 58% / 58%`；其余两臂 `dbu_ofdm_st / ofdm_distpil_st` 未在 12 场景探针中查询，正式 L2 中全部 5 主臂在配对场景上严格对称共享 `-21.5 dB`）按居中落于 `[15%, 92%]` 非饱和区间的规则选定并硬锁 **`snr_g0_slope = -21.5 dB`**。需说明：`C3_DiD_conservative` 对照的是两个冻结工况（`S1 -11.0 dB` 与 `G0 -21.5 dB`）下的相对优势差。
3. **精确有限样本顺序统计量门限、12 臂 FWER Beta-Binomial `C1` 与主臂防膨胀工程硬帽**：
   - 首跑中 `C1` 对 12 条臂同时采用固定 `p = 0.01` 的 Clopper-Pearson 区间并忽略 `N_cal` 门限估计方差（在跨臂独立近似与连续零假设下 12 臂同时误拒率粗估约 `~89%`；实际各臂共享场景且首跑用 Weibull 插值门限），导致仅 `Pd = 0%` 的 `ofdm_distpil_st` 落在保守侧 `0.35% (7/2000)`，主臂 `ridge_afdm_st` 精确命中 `1.00% (20/2000)`。
   - 本次确证复跑改用精确顺序统计量门限 $\hat{T} = X_{(b)}$（`b = n_cal + 1 - a`, `a = round(p * (n_cal + 1))`；零基索引 `b - 1`，严格 `>` 判报警；`S1`: `a=15, b=1486, E[P]=0.9993%`；`G0`: `a=4, b=397, E[P]=0.9975%`），在 `cal/val` 独立同分布连续零假设下精确满足 $K_{\mathrm{val}} \sim \mathrm{BetaBinom}(n_v, a, b)$。`dual_bootstrap_delta_pd` 同步采用相同顺序统计量索引 `b - 1`。
   - **冻结 `C1` 判据**：
     - **统计校准层（12 臂并集 FWER 上界 `≤ 5.0%`）**：全部 12 条参试臂（`S1` 7 臂 + `G0` 5 臂）的 `k_val` 均落入 `alpha_each = 0.05 / 12`（双侧各 `0.05 / 24`）的精确 Beta-Binomial 预测区间（`S1`: `k_val ∈ [5, 44]` 即 `[0.25%, 2.20%]`；`G0`: `k_val ∈ [0, 15]` 即 `[0.00%, 3.75%]`）；
     - **附加主臂防虚警膨胀工程硬帽（仅约束主臂 `ridge_afdm_st` 观察到的验证虚警率，方向上对主臂更严）**：同时要求主臂 `ridge_afdm_st` 观察到的验证虚警率满足 `S1 <= 1.75%`（`k_val <= 35/2000`，精确零假设下独立超出概率 `2.14%`）且 `G0 <= 2.50%`（`k_val <= 10/400`，独立超出概率 `2.76%`）；将两道附加硬帽计入后，全 `C1` 逐项误拒概率相加的并集上界为 `7.72%`。
   - 同步清理 `slope_mismatch_2pct` 压力读数（无独立 `val` 集时仅按 `cal_se` 标定门限评估 `pos_se`，不再输出同集伪 `val/c1_pass` 字段）。

## 2. 其余门检与冻结主判据（与首跑 `PREDICTIONS_k_r11_k02.md` 100% 一致）
- **`G1_HEALTH_BW_PILOT_G0SER`**：全 5 主臂实测 `BW99(ridge_afdm_st) <= BW99(each OFDM) + 0.005`、导频占比 `ridge_afdm_st <= each OFDM`、`rc_approx < 1.5%`、合成 `1e10` 与真实 `S1` 图精确 CUT 相对误差 `< 1e-12`、`+38 dB` 无损伤静态全 5 主臂 `SER < 1.0%`，且 `G0 (-11 dB)` 全 5 主臂 `SER < 2.0%`。
- **`C2_BLIND_BREAKTHROUGH`（`S1 -11 dB`, `N_cal=1500, N_val=2000, N_pos=200`）**：`ridge_afdm_st` 相对全部 4 条等开销 OFDM 的 Bonferroni 同时 95% 双自助下界 `>= +0.50`，且相对父卡 `k01_orig` 的 95% 下界 `>= +0.50`。
- **`C3_ABLATION_PASS`（`S1 -16.0 dB`, `N_pos=200`）**：`ridge_afdm_st` 相对 `k01_orig` 95% 下界 `>= +0.50`，相对单遍 `burst_em0` 95% 下界 `> 0`，且单遍占比 `em0_share < 0.80`。
- **`C3_G0_DID_PASS`（`G0 -21.5 dB`, `N_cal=400, N_val=400, N_pos=120`）**：显式满足非饱和条件（`ridge_afdm_st` 与最强 OFDM 的 `Pd_loc` 均在 `[15%, 92%]`）、`Delta_G0` 95% 上界 `<= +0.15`，且保守双重差分 `Delta_S1 - max(0, Delta_G0)` 95% 下界 `>= +0.50`。
- **`PASS_PRIMARY === G1_HEALTH_BW_PILOT_G0SER AND C1_VALIDITY AND C2_BLIND_BREAKTHROUGH AND C3_ABLATION_PASS AND C3_G0_DID_PASS`**。

## 3. 跑前主观概率预测
- `P(G1_HEALTH) = 0.99`；`P(C1 统计校准 + 主臂硬帽) = 0.92`；`P(C2) = 0.99`；`P(C3_ablation @ -16 dB) = 0.97`；`P(C3_G0_nonsat @ -21.5 dB & DiD) = 0.94` → **综合 `P(PASS_PRIMARY) = 0.83`**。
