# E-1 协议（冻结稿）：CSTATE 机制因子消融

任务：`.trellis/tasks/10-17-discrete-acquisition-e1/`。本文件在 prd.md / design.md 与之冲突处**优先**（编排者修正 C1–C6 已并入，另有 §9 列出的实现期偏差）。**§10（编排者跑前修订 O1–O5）取代 §4 的 SNR 列表与 §5.2–5.3，并新增 A7 / G5 / K4。**
冻结文件（永不修改）：`experiments/tf_geometry_reopen_20260922/`、`tf_cstate_validation_20260922/`、`sp_afdm_native_joint_20260921/`、`tcom_reference_frame_20261015/`、`tcom_genie_support_20261016/`。新代码只在本目录。

## 1. 问题与读数

CSTATE 对 F0 失败状态的救回来自：(i) 协方差感知的支撑决策（Γ 的非对角耦合）、(ii) 支撑搜索（max_edits>0）、(iii) 额外一轮检测+译码。六臂在**同一捕获的 F0 状态**上做 2×2 因子（Γ × 交换）加两个控制/分解臂。结论仅限 F0 失败子集（条件化），不外推到全帧 FER。

## 2. 变体定义（精确）

**生产 CSTATE20 实际调用链**（读源码确认，与 design.md 第 3 节的描述不同）：`run_validation._branch` → `ctx.kernel.reopen_geometry(..., strategy='compact')`，其中 `ctx.kernel = tf_cstate_validation_20260922/geometry_validation.py`；该文件从 `tf_geometry_reopen_20260922/geometry_reopen.py` 导入 `ExchangeResult, Path, _gamma_cross, _responses, _system`。因此变体必须是**两个**文件的逐字拷贝：

| 变体文件 | 原文件 | 原 md5 | 改动 |
|---|---|---|---|
| `geometry_reopen_variant.py` | `tf_geometry_reopen_20260922/geometry_reopen.py` | a6de0ff1238faeff21d767dd10b084de | `_gamma_cross`、`_system`、`reopen_geometry` 增加关键字 `gamma_mode`（默认 `"full"`）；`"diag"` 分支各一处；3 行注释 |
| `geometry_validation_variant.py` | `tf_cstate_validation_20260922/geometry_validation.py` | b576a04dea5cbfc10cc61d748ebe8fbc | import 改为 `geometry_reopen_variant`；`reopen_geometry/_direct_global/_direct_scores` 增加 `gamma_mode`；每个 `_system(...)` / `_gamma_cross(...)` 调用点透传；3 行注释 |

`test_variant.py::T0` 机械验证：把变体中的白名单插入行删去、`, gamma_mode…` 实参记号去掉、import 改回后，与冻结原文件逐行相等。

**协方差轴触及两处**（C1）：
(a) `_system`：`gamma = projected_variance(...)`（P×P；同时驱动增益重拟合、局部 Doppler 细化目标、接受后的 refit、最终 refit）。`gamma_mode='diag'` 时取 `np.diag(np.diag(gamma))`。
(b) `_gamma_cross(current, candidates, vf, c1)`（P×候选交叉项；compact 路径的 `K += ...` 与换行刷新，及 direct/fallback 路径的 `_direct_scores`）。`gamma_mode='diag'` 时返回全零（所有 path–candidate 对均为不同路径，全属非对角）。
候选自项 `energy = |x|² + Σv` **不变**；`ridge`、检测器、译码器、compact 代数、局部细化的搜索逻辑都不变。
**断言**：`diag(projected_variance(v, delays, dopplers, c1)) == Σv`（相对容差 1e-10，且虚部恒为 0），即 diag 模式 ≡ 精确标量收缩 Γ = (Σv)·I。该断言在 `test_variant.py::T1`（随机路径集含同时延双峰）与 gate 模式（真实 P1 状态的 r1 几何与 A1 末几何）双重检查；失败即**停止并报告**，不改定义。

## 3. 臂（全部从同一 F0 状态；`strategy='compact'`；`grid_step=.25 chunk_size=64 local_halfwidth=.75 local_max_evals=16 duplicate_tolerance=1e-6 top_k=20 ridge=sigma2 max_delay=system.l_max_cap doppler∈[-3,3]`）

| 臂 | Γ | max_edits | local_passes | 说明 |
|---|---|---|---|---|
| A1 | full | 2 | 2 | 生产 CSTATE20；必须与 ledger `arms.B.decoded_sha256` 逐位一致 |
| A2 | diag | 2 | 2 | 只去 Γ 非对角耦合 |
| A3 | full | 0 | 2 | 禁止交换，保留局部 Doppler 细化 |
| A4 | diag | 0 | 2 | 两因子同时关 |
| A5 | — | — | — | 不调用 `reopen_geometry`：`Channel(r1_delays, r1_dopplers, r1_gains)` → 同参数 `scalar_joint(prior=r1_check, iterations=20, damping=.3, gain_mode='joint')` → `decoder_messages(maxiter=50)` |
| A6 | full | 0 | 0 | 仅软协方差 ridge 增益重拟合（几何不变）；**报告臂**，不参与 J1–J3 |

分支实现 = `run_validation._branch` 的参数化拷贝（`e1_driver.run_branch`），保持其 exclusive-stage 计时与各项一致性断言；A5 计同样的阶段但几何各项为 0。

**r1_* 语义**（读 `sp_afdm_native_joint_*/src/native_twofft.py::receive` 确认）：`receive(rounds=2)` 的第 1 轮（索引 r=1，即第二轮）：`c = time_refine(...)`（软方差变量投影的 CE，唯一时延、≤8 径，用上一轮译码矩）→ `r1_delays, r1_dopplers = c.delays, c.dopplers`，`r1_ce_gains = c.gains`；`o = scalar_joint(..., c, prior=上一轮 check)` → `r1_gains = o['gains']`（检测器 joint 增益，非 CE 增益）；`dec = decoder_messages(...)` → `r1_app = dec['raw_app']`，`r1_check = dec['raw_check_extrinsic']`。分支用 `moments(clip(r1_app), 1-rho)` 得 `mu, v`，先验为 `clip(r1_check)`。
含义：A5 是"第三次检测+译码、几何不变、增益用 r1 检测器增益起点、**无 CE 重拟合**"，不等同于字面的第三轮 F0（后者含 `time_refine`）。A1–A4/A6 的增益起点是 `result.gains`（几何目标的软 ridge 解）。因此 A5 与 A6 的差别仅是增益起点（A6−A5 报告在 §5 的 CI 表中）。

## 4. 单元、选择与门

**单元**：触发键 `(scenario, rho, snr, frame)`，SNR 列表见 §10 O1（本节原列表 {6.5,7.0,7.5,8.0} dB 现为预声明次要集），四格 U/G × ρ{.3,.5}，P1 帧 0..1999（entropy 2261fde3…，domain TCRF），F0 终末校验子≠0。成功 = 与真值相比 info 比特错误数 = 0（`gs_driver.score`）。
**选择**：`e1_driver.py --mode select` 扫 P1 ledger（`arms.B.triggered`），写 `triggered_keys.json`（含 ledger 的 B/F0 `decoded_sha256`、`info_errors`，及 ledger 文件 md5）。仅重跑这些键的 F0 以捕获状态。
**门**：
- G1 full 模式与冻结原版逐位一致（`deep_equal` 位级，忽略墙钟字段）：(synthetic) `test_variant.py::T2`，64 个合成状态 × 5 种配置（compact e2/e0/e0-l0、direct、旧 `geometry_reopen` 核）；(real) gate 模式对 frames 0..19 × 4 格 × 8 个 SNR = 640 个真实 P1 状态（触发与未触发）比较 `ctx.branch(...,'CSTATE20')` 与变体 A1 的全部输出（result/detector/decoder/先验矩）。
- G2 diag 模式：非对角恒 0、对角 = Σv（`test_variant.py::T1/T3` 与 gate 真实状态）；且在 ≥8 个触发状态上"决策层"与 full 不同（首选候选 / 接受编辑序列 / 支撑 / 译码输出之一不同）。注意：仅 6.5–8.0 dB 的 frames 0..19 内触发态约 2–3 个，故 G2 的"≥8 触发状态"在 gate 模式取全 8 个 SNR 的触发态（机制检验，不用于主分析）。
- G3 确定性：`test_variant.py::T4`（5 种几何配置各两次）与 gate 真实触发态（每分片前 3 个，六臂各两次）位级相等。
- G4a 每个主分析单元重跑 F0 后校验子≠0（行内 `g4a_ok`）。
- G4b frames 0..19、全部键（触发与未触发）：重跑触发集合 = ledger B 触发集合；最终译码 `decoded_sha256`（触发取 A1，未触发取 F0）= ledger B；F0 `decoded_sha256` = ledger F0。主分析 SNR 子集与全 8 SNR 各报告一次。此外主分析**每个单元**行内记录 `a1_matches_ledger`、`f0_matches_ledger`（聚合时必须全真）。
任一门不过 → 结论"未定"，不得解读 J1–J3（`e1_agg.py` 在 integrity/gates 不通过时输出 `NOT_INTERPRETABLE`）。

## 5. 冻结统计（实现于 `e1_agg.py`，合成数据自测 `test_e1_agg.py`）

5.1 **主分析**：在 4 格 × 4 个 SNR **合并**的全部单元上，精确单侧 McNemar（不一致对；H1 方向如下，每个 α=.05，不做多重校正）：
- K1：A1>A2；K2：A2>A5；K3：A1>A5。
成功率差（rescue-rate difference，臂成功率之差）95% 置信区间：**cluster bootstrap**，cluster = `(scenario, rho, frame)`，20000 次重抽样（多项式计数重抽样 = 有放回抽 cluster），固定 seed 20261017，百分位区间。对：A1−A2、A2−A5、A1−A5、A1−A3、A2−A4、A3−A6、A6−A5。始终报告 CI 宽度；凡"CI 含 0"一律附注 **"not significant != equivalent"**。

5.2 **（被 §10 O3 取代）J 判据与 KILL**：J1（机制）= K1 且 K2 显著；J2（搜索）= CI(A1−A2) 含 0 且 K2、K3 显著；J3（额外轮）= CI(A1−A5) 含 0；KILL = J3；否则 MIXED。
5.3 **（被 §10 O3 取代）判定优先级**（编排者原文未规定冲突处理，实现期补充，需编排者确认）：J3 → KILL；否则仅 J1 → J1；仅 J2 → J2；J1 与 J2 同真或均假 → MIXED。
5.4 **分格**：每格 K1–K3 精确单侧 McNemar，对 4 格做 Holm 校正；同时算反方向（A2>A1、A5>A2、A5>A1）的 Holm 调整 p，< .05 的格标记为"显著反向效应"。
5.5 **描述性**：各臂成功率、相对 F0 的救回/伤害计数、支撑变化（时延集合对称差、替换数、接受编辑数）、A1 与 A2 的首选候选/接受编辑一致率、分阶段（exclusive-stage）与全程成本、总核时。

## 6. 行格式（`out/<dir>/rows_shard###.jsonl`，跑完 gzip）

每键一行：`scenario, rho, rho_permille, snr_centi_db, snr_db, frame, sigma2, gen_seconds, f0{syndrome, info_errors, decoded_sha256, ldpc_iters, seconds}, g4a_ok, ledger{…}, f0_matches_ledger, a1_matches_ledger, r1{delays, dopplers}, truth{delays, dopplers}, arms{A1..A6}`；每臂：`status, fer, info_errors, syndrome, decoded_sha256, ldpc_iters, final_delays, final_dopplers, n_support_changes（对 r1 时延集合的对称差大小）, n_delay_replacements, n_edits, edits[], top5_step1[]（step 1 的 (score, slot, replacement)，仅 max_edits>0）, seconds, stages{exclusive}, objective_before/after, numerical_fallback, condition_number`。`config_shard###.json` 含 `_argv` 与 `_config`（全部参数、臂规格、冻结源码 md5 复核表、所有已加载项目模块 md5、环境）。

## 7. 运行与成本

CPU、单线程分片（`OMP/MKL/OPENBLAS_NUM_THREADS=1`）、tmux `g_e1`、保留 ≥16 核空闲（`launch_e1.sh` 开跑前核对负载）。`MODE=gate`：select + 20 分片真实态门 + 8 单元冒烟；`MODE=run`：全单元分片，结束 gzip + md5 清单 + `e1_agg`。成本上限 16 core-hours；超限即停并报告。失败分片原样保留并记录原因，不重试不换配置。

## 8. 先验规模事实（跑前核对 P1 ledger，非结果解读）

ledger（`tcom_reference_frame_20261015/out/p1`）中 SNR∈{6.5,7.0,7.5,8.0} 的触发键总数 = **272**：U ρ.3：19/14/10/7；U ρ.5：58/4/0/0；G ρ.3：36/20/13/6；G ρ.5：77/8/0/0（按 6.5/7.0/7.5/8.0 dB）。生产 B 对这 272 个触发键的 info 零错数 = 263（96.7%）。design.md 第 8 节"2000–8000 触发帧"的估计偏高一个数量级以上；主分析的统计分辨率由 272 个单元决定，且 A1 靠近上限，不一致对数少。跑前决策点（编排者）已由 §10 O1 解决：主单元集 = 全 P1 网格。

## 9. 与 brief / design.md 的实现期偏差

1. 变体为两个文件而非一个（§2 的调用链事实）。
2. G2 的"≥8 触发状态"取自全 8 个 SNR 的 frames 0..19（§4）。
3. 判定优先级补充（§5.3）。
4. 触发键的预选来自 ledger；未触发键不做 A 臂；G4b 在 frames 0..19 全键上验证 ledger 的触发判定可复现。

## 10. 编排者跑前修订 O1–O5（2026-10-17）

诚实声明：修订前编排者仅见 8 单元冒烟（A1..A6 = 8/6/4/4/4/4）；修订动机为单元数/统计功效与对照强度，不基于该冒烟方向。

§10 取代 §4 的 SNR 列表与 §5.2–5.3；K1–K3 检验保留。其余各节仍有效，除非本节明文覆盖。

**O1 总体。** 主单元集 = 完整 P1 网格上全部触发键：SNR {4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0} dB × 四格（U/G × ρ{.3,.5}）× 帧 0..1999（ledger 计数 ≈ 16379 单元）。预声明次要集 = SNR {6.5,7.0,7.5,8.0} 子集（272 单元），用同一规则从同一批行分析（`e1_agg.py` 输出 `secondary_snr_6p5_to_8p0`）。`launch_e1.sh` 与 `e1_driver.py --mode select` 默认 SNR 列表为全网格。

**O2 新臂 A7 = 字面第三轮 F0。** 在同一观测上从头运行 `ctx.native.receive(obs, ctx.system, ctx.code, rounds=3, iterations=20, ce_mode='soft', gain_mode='joint')`，取其返回的译码器输出（第 2 轮）打分。
- **G5（每个单元）**：`receive` 返回的 `arrays` 暴露每轮状态（键 `r{r}_*`）。断言 rounds=3 运行的 `r0_*` 与 `r1_*` **全部键**（`delays, dopplers, gains, gain_variance, ce_gains, mu, variance, ce_history, ce_gamma, inference_trace, decoded, input_llr, app, check`，含 r1_delays、r1_dopplers、r1_gains、r1_app、r1_check、r1_decoded）与已捕获 rounds=2 状态逐位相等（`e1_lib.deep_equal`，数组按字节、浮点按位），并且 `r2_decoded` 的 sha256 = 返回译码器的 `decoded` sha256。任一缺键或不等 → 该行 `g5_ok=false`，聚合拒绝解读。行内记录 `g5_ok, g5_keys, g5_mismatch` 与 `r1_decoded_sha256`。
- **成本**：A7 `seconds` = 从头 rounds=3 总墙钟（含校验子）；`seconds_minus_f0` = A7 − 同一单元的 F0 秒数（= 第三轮增量，与 A1 的分支秒数可比）；两者都报告。
- **K4**：A1 > A7，精确单侧 McNemar，仅报告（不入判定）。分格 Holm 与反向效应同样覆盖 K4。

**O3 判定规则**（取代 §5.2–5.3；K1–K3 保留，α=.05）。δ = 0.10；R_x = 臂 x 在单元集上的成功率。
- Δ_geo = R_A1 − R_A5；S_Γ = (R_A1 − R_A2)/Δ_geo；F5 = (R_A1 − R_A5)/R_A1；F7 = (R_A1 − R_A7)/R_A1。
- CI：同一 cluster bootstrap（cluster = (scenario, rho, frame)，20000 次，seed 20261017，百分位）；**比值逐次重抽样计算**。可评估性**按分母拆分**（跑前修正，见下）：
  - F5、F7 以 R_A1 为分母：CI 取 R_A1>0 的全部重抽样；`kill_evaluable` = 点估计 R_A1>0 且 R_A1=0 的重抽样占比 ≤ 1%。**Δ_geo ≤ 0 不使 F5/F7 退化**（此时 F5 ≤ 0，J3a 成立即为 KILL）。
  - S_Γ 与阶梯份额以 Δ_geo 为分母：CI 取 Δ_geo>0 的重抽样；`sgamma_evaluable` = 点估计 Δ_geo>0 且 Δ_geo ≤ 0 的重抽样占比 ≤ 1%。
  - 报告两个占比与两个可评估标志。
- KILL（J3）= CI_upper(F5) < δ（J3a：增益只是检测器重跑）**或** CI_upper(F7) < δ（J3b：增益只是多一轮 F0）；报告触发的是哪一条。
- J1 = 非 KILL，且 K1、K2 显著，且 CI_lower(S_Γ) ≥ δ。
- J2 = 非 KILL，且 CI_upper(S_Γ) < δ，且 K2、K3 显著。
- 判定顺序：(1) 若 kill_evaluable 且（J3a 或 J3b），判 KILL；(2) 否则若 kill_evaluable 或 sgamma_evaluable 任一为否，判 MIXED，并注明哪一项不可评估；(3) 否则按 J1 / J2 / MIXED。J1 与 J2 按构造互斥。
- 说明：Δ_geo ≡ 0 → KILL (J3a)，因为 F5 = 0（此时 S_Γ 不可评估但不阻止 KILL）；R_A1 = 0 → MIXED（kill 不可评估）；5% 重抽样 Δ_geo ≤ 0 且 F5 的 CI 上界 ≥ δ → MIXED（sgamma 不可评估）。
- **跑前修正记录（编排者，2026-10-17）**：O3 最初写作"Δ_geo ≤ 0 或 R_A1 = 0 的占比 > 1% → 全部比值判据不可评估 → MIXED"，该措辞有误（把两种分母混在一起，使 Δ_geo ≡ 0 误判 MIXED）；本节上述按分母拆分的规则为跑前修正后的冻结版本。
- 描述性阶梯（各带 CI，份额在点估计上相加为 1）：S_swap = (R_A1−R_A3)/Δ_geo，S_local = (R_A3−R_A6)/Δ_geo，S_refit = (R_A6−R_A5)/Δ_geo，另报 S_Γ,noswap = (R_A3−R_A4)/Δ_geo。
- 仍报告：分格 Holm 与反向效应标记；**按 SNR 的 R_x 表（7 臂）**；**成本表（各臂平均秒数，A7 总秒与 A7−F0）**；§5.1 的差值 CI 表扩展为含 A1−A7。

**O4 数据卫生。** 本地 `out/` 只保留小摘要：`gates.json`、`test_variant.json`、分析 md/json；`triggered_keys.json` 仅在 < 约 2 MB 时留本地，否则只留 md5 与计数。行级 jsonl（冒烟/计时样本）本地删除，md5 写入 `out/LOCAL_REMOVED_MD5.txt`，远端副本保留。deinlab 上只保留主跑所需（代码、`out/select`、`out/gate`），其余列入跑后删除清单。

**O5 实现。** `e1_driver.py`：A7 + G5（run 与 gate 模式；gate 模式 G3 扩为 7 臂，并对触发态检验 G5）；`e1_agg.py`：O3 规则、K4、per-SNR 与成本表、次要集；`test_e1_agg.py`：合成数据覆盖 KILL(J3a)、KILL(J3b)、J1、J2、MIXED、>1% 退化。gate 冒烟 12 单元（含 4.5 与 5.0 dB），7 臂。主跑默认 64 分片。
