# Pre-registration — `k_r10_k01_pfa`（`I-20261125-k01` Step-8 REVISE 等虚警窗口决定性复验）

> 冻结时间：2026-11-25 11:22 (Asia/Shanghai) · Runner：`k`（`gemini-4-neon`）· 对应卡片：`I-20261125-k01`
> 对应审稿：`ideas/reviews/r10-astra-k01-killarg-20261125.md`（Astra `REVISE`：确认 `34.22 dB` 泄漏降幅成立，但指出原 `Pd 98.3% vs 10.0%` 用全图均值归一的单格门限评判剔除 153 格保护区的 15 格窗口择峰，并非等虚警比较）。
> **铁律**：按 `FUNNEL.md` 第 4 条，本复验采用新鲜随机种子 `seed = 2026112501 + 10000 = 2026122501`（全项目仅允许这一次重做）；底层信道、波形与接收机直接 `import k_l2_r10_k01` 原样复用，不改动任何物理或接收机实现。

## 1. 统一评分函数与「搜索窗口预先给定」口径

1. **唯一评分函数 `score(rd_map, center)`**：
   - 输入：任意波形输出的距离–多普勒功率图 `rd_map`（形状 `141 × 29`，复用 `k_l2_r10_k01.compute_rd_map`）与中心格 `center = (ni, ti)`。
   - 分子：以 `center` 为中心的 `5 × 3` 窗口（`[max(0, ni-2):min(141, ni+3), max(0, ti-1):min(29, ti+2)]`，内点 15 格）最大值。
   - 分母：全图剔除以 `center` 为中心的 `17 × 9` 保护块（`g_nu=8, g_tau=4`，内点 153 格）后余下格子的算术均值（下限 `1e-15`）。
   - 返回：`ratio = peak / bg_mean`（线性比值）与 `10 log10(ratio)`（dB）。
   - **代码硬断言**：校准集（`cal`）、独立验证集（`val`）与有目标集（`pos`）全部通过 `score(rd_map, center, role=...)` 计算分数，脚本末尾断言三路径调用计数精确等于各自 `帧数 × 臂数`。
2. **窗口位置与范围（"window given a priori"）**：
   - 主检验明确限定为**搜索窗口预先给定**（`window given a priori`）：有目标帧取该场景目标的真实 `(ni, ti)` 格（`S1` 为 `(NI_MOV, TI_EVAL)`，`G0` 为 `(NI_STAT, TI_EVAL)`）；无目标校准帧与验证帧使用**完全相同的 `center` 列表**（从配对正例目标格列表逐帧对应），使无目标与有目标帧的窗口统计量除目标是否存在外同分布。
   - 门检 `G2`：除上述声明的 `center` 首次参与计算严格在 `compute_rd_map()` 返回之后（仅传入 `score()`）外，任何目标真值（`snr_t=None`、`len(paths)==N_CLUT+1`）均不进入校准/验证帧的信道、波形或接收机计算。
3. **独立校准、独立验证与目标虚警水平**：
   - 目标窗口虚警概率：**`Pfa_win = 1e-2`**（每帧单一窗口至多 1 次报警；`Pfa_win = 1e-3` 需每集 `≥ 20,000` 帧，对应 `≥ 18.9` 核时，超出 `G3` 2 核时硬上限，故不加跑 `1e-3`）。
   - 每条臂独立在无目标校准集上取分布无关有限样本无偏顺序统计量分位数 `thr = np.quantile(cal_scores, 1.0 - 0.01, method="weibull")`（对应 `q*(n+1)` 绘点位置，对连续 i.i.d. 分数精确满足 $\mathbb{E}[P(X>\text{thr})]=0.0100$，消除 `linear` 插值在 `n=180/1050` 处的有限样本上偏），报警规则固定为 `score > thr`（永不事后修改门限规则），随后在完全独立的无目标验证集上计算经验 `Pfa_win` 与精确 95% Clopper-Pearson 置信区间（`scipy.stats.beta.ppf`）。

## 2. 参试臂、场景与算力预算（`G3` 硬门检）

- **主比较臂（4 条，均等 `12.5%` 导频预算、等 99% 占用带宽）**：
  1. `ridge_afdm`（中心化 `Ridge-AFDM`, `c1 = mu/(2N)`, `193` 激活子载波）
  2. `ofdm_comb`（`223` 激活子载波 + 同 `Band-3 + 1-col LOS` Soft-EM）
  3. `dbu_ofdm`（`DBU/Group-Precoded OFDM, arXiv:2604.10296` + 同 Soft-EM）
  4. `ofdm_blkpil`（`OFDM-BlkPil(1/8) + MultiSym-JointEM`）
- **描述性对照臂（3 条，仅记录不入主判据）**：`ofdm_2pil`（`25%` 双倍导频）、`known_afdm`（已知载荷上限）、`ofdm_genie`（真信道初值诊断）。
- **场景与样本量（新鲜主种子 `2026122501 = 2026112501 + 10000`，启动前断言与原 `k01` 种子零交集）**：
  - `S1`（移动：`LOS=+18 dB, Clut=+28 dB, v_T=220 m/s, SNR_t=-11 dB`）：
    - 主 4 臂：`N_cal_s1 = 1050`, `N_val_s1 = 1050`, `N_pos_s1 = 200`（配对，满足 `≥ 200`）。
    - 描述 3 臂：`N_cal_desc = 150`, `N_val_desc = 150`, `N_pos_s1 = 200`。
  - `G0`（静态对照：`v_T=0, mu=0, LOS=+18 dB, Clut=+28 dB, SNR_t=-11 dB`）：
    - 主 4 臂：`N_cal_g0 = 180`, `N_val_g0 = 180`, `N_pos_g0 = 100`（配对，满足 `≥ 100`）。
- **次级读数（Secondary Readout，不入主判据）**：
  - **全图盲搜（Blind Full-Map Detection）**：在每张 `rd_map` 上对全部 `141 × 29 = 4,089` 个中心格求同一 `score(rd_map, center)` 的最大值（采用保护块外四互不重叠矩形和 + `5×3` 最大滤波，彻底消除大峰值浮点相消；启动前在真实图与 `1e10` 高动态构造图上对**全部 4,089 格**断言与 `score()` 误差 `< 1e-12`），按各波形独立在无目标校准集取每图 `Pfa_map = 1e-2` 门限、在独立验证集核验 `Pfa_map`，并汇报各臂盲搜 `Pd`。
- **`G3` 算力实测预算（`deinlab`, `16` 核, tmux `g_funnel_k_pfa`, 输出 `/data/guoyikun/tmp/funnel_k_pfa/`）**：
  - 实测单线程耗时：`S1` 主 4 臂 `1.703 core-s/scene`，`G0` 主 4 臂 `1.728 core-s/scene`，`S1` 描述 3 臂 `1.381 core-s/scene`。
  - 预期原始核时：`2300 × 1.703 + 460 × 1.728 + 500 × 1.381 + 9(G1) = 5,412 core-s = 1.503 core-h`。
  - 乘以 `× 1.3` 安全系数：**`1.954 core-h ≤ 2.00 core-h`**（16 核墙钟约 `5.6–7.3 min`；脚本同步记录墙钟折算核时与进程 CPU 时间）。

## 3. 冻结主判定规则（`PASS_PRIMARY`，全部必须同时满足）

- **`C1`（等虚警有效性）**：在主场景 `S1` 上，对全部 4 条主臂（`ridge_afdm`, `ofdm_comb`, `dbu_ofdm`, `ofdm_blkpil`），独立验证集经验窗口虚警率 `Pfa_win` 点估计落在 **`[0.5, 1.5] × 1e-2`** 内，且其精确 95% Clopper-Pearson 置信区间与 **`[0.5, 2.0] × 1e-2`** 有交集。（若某臂未过 `C1`，只允许增大校准样本量重跑校验，绝不修改门限规则。）
- **`C2`（`S1` 移动场景等虚警检测增益）**：在 `S1`（`N_pos_s1 = 200` 配对场景）上，定义 `Delta Pd = Pd(ridge_afdm) - max(Pd(ofdm_comb), Pd(dbu_ofdm), Pd(ofdm_blkpil))`；采用 **2,000 次固定种子配对自助法**（每次重抽对同一组配对场景索引同时计算 4 臂 `Pd` 并取三对手最大值，保守且严谨），要求 `Delta Pd` 的 **95% 置信下限 `> 0`**。
- **`C3`（`G0` 静态对照无显著差异）**：在 `G0`（`v_T = 0, N_pos_g0 = 100` 配对场景）上，同法计算的带符号 `Delta Pd = Pd(ridge_afdm) - max(Pd(ofdm_comb), Pd(dbu_ofdm), Pd(ofdm_blkpil))` 之 95% 配对自助法置信区间**包含 `0`**（`ci_lo ≤ 0 ≤ ci_hi`，未在静态条件下检出虚增益）。

`verdicts.PASS_PRIMARY === (C1 AND C2 AND C3)`。
- 若 `PASS_PRIMARY == true`：卡片维持 `layer: L2, status: active, next_cost: cross-model review`。
- 若 `PASS_PRIMARY == false`：按 `FUNNEL.md` 铁律 4 置 `status: killed`（若在次级全图盲搜读数上 `ridge_afdm` 仍显著胜过三等开销对手，则置 `status: parked` 并写明原因），严禁留 `next_cost: cross-model review`。

## 4. 跑前门检（`G1 / G2 / G3`）

- **`G1`**：在原 `k01` 主场景的 5 个 `S1` 场景上，验证新函数 `10 log10(score(rd_map, center))` 与原 `k_l2_r10_k01.eval_rd_peak` 对全部 4 条主臂（含 `ridge_afdm` 与 `ofdm_comb`）的绝对差均 `< 0.01 dB`（预期 `< 1e-12 dB`，同时验证四臂 RNG 顺序逐位一致）；并验证全图盲搜评分在真实图与 `1e10` 高动态构造图上全部 4,089 格误差 `< 1e-12`。
- **`G2`**：断言全部校准/验证帧满足 `snr_t is None`、`len(paths) == N_CLUT + 1`，且 `center` 首次参与计算严格在 `compute_rd_map()` 返回之后。
- **`G3`**：`× 1.3` 预估核时 `1.954 ≤ 2.00 core-h`，`workers = 16 ≤ 16`，输出写入 `/data/guoyikun/tmp/funnel_k_pfa/`（禁写 `/tmp`）。

## 5. 跑前主观概率预测（Pre-run Predictions）

- **Claude**：`P(PASS_PRIMARY) = 0.70`；`P(C2 95% 下限 > 0.50) = 0.55`。
- **Runner k (`gemini-4-neon`)**：
  - `P(C2 95% 下限 > 0) = 0.96`（原 `+10.82 dB` 窗口 SCNR 优势体量远超 15 格窗口门限迁移）。
  - `P(C2 95% 下限 > 0.50) = 0.72`（预期 `Pd(ridge_afdm) ≈ 0.80–0.92` 对最强等开销对手 `≈ 0.05–0.15`，主要下行风险在于匹配滤波无目标杂波尾可能略抬高 `ridge_afdm` 的 15 格窗口门限）。
  - `P(C3 静态对照含 0) = 0.92`（静态下三臂 SCNR 均 `+20–22 dB`，显著高于窗口门限，预期 `Pd ≈ 0.99–1.00`）。
  - `P(C1 四臂同时落入 [0.5,1.5]e-2) = 0.50`（`N_cal=N_val=1050` 下单臂理论通过率约 `80%`，采用无偏 Weibull 分位数消除 `linear` 偏移后，四臂联合抽样波动仍是 `PASS_PRIMARY` 的首要有限样本风险）。
  - **综合 `P(PASS_PRIMARY) = 0.48`**（若物理效应 `C2 & C3` 强过但单臂因有限样本抽样略偏 `C1`，可按要求仅增校准量复验）。
