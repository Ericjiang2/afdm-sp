# E-3b 协议（冻结稿）：给 SBL 加连续 Doppler 细化，检验标量 Γ 的优势是否消失

任务 `.trellis/tasks/10-17-offgrid-sbl-e3b/`。本文件 = `design.md`（具有约束力）并入执行期事实与偏差；两者冲突处以本文件为准，偏差与澄清全部列在 §10。
冻结（永不修改）：`experiments/tf_e3_sbl_20261017/`（E-3 全部代码，commit 54eb0437）、`tf_cstate_e1_20261017/`（含 `geometry_reopen_variant.py`）、`tf_geometry_reopen_20260922/`、`tf_cstate_validation_20260922/`、`sp_afdm_native_joint_20260921/`、`sp_afdm_frozen_20260920/`、`tcom_reference_frame_20261015/`、`tcom_genie_support_20261016/`、`tcom_channel_crb_20261016/`、`headroom_ladder_20261008/`、`tf_production_gap_audit_20260922/`。新代码只在本目录；对冻结代码一律只读导入。
前置：[res-20261017-03](../../research-assets/res-20261017-03.md)（E-3，已接受）。该卡的事后解释：固定网格上分数 Doppler 需要几个相邻的同时延原子来插值，标量 Γ 奖励把增益摊开，起了有益的插值与收缩作用（L-diag FER .110 对 L-cov .149）。E-3b 只检验这个解释。

## 1. 问题

给同一个 E-3 的 SBL 加上连续 Doppler 细化（CSTATE 式的逐原子标量搜索，目标函数取 E-1 变体核 `_system`）。若插值解释成立，细化后标量 Γ 的优势应消失或反转；若不成立，优势应不受细化影响。判定按 §5 的冻结规则，结论只适用于本接收机、ρ.3、P1 信道。

## 2. 流程与约定（每个键）

1. **第 1 级、第 1 轮、第 2 级候选集、四个变体的第 2 级 SBL**：逐位沿用 E-3（`sbl_rx.py` 与 `e3_driver.py` 的辅助函数由 `import` 只读使用；`e3b_driver.process_key` 是 E-3 `process_key` 的同序拷贝，只在 `select_output` 之后插入细化）。SBL 的 100 次迭代、M=256、阈值与 E-3 完全相同，不调。
2. **连续 Doppler 细化**（每个变体各自，`offgrid_refine.refine`）：输入为 SBL 输出原子（≤ 24 个，已按能量降序）。目标函数
   `value(paths) = geometry_reopen_variant._system(Y, xt, v_m, paths, c1, c2, ridge = σ², gamma_mode = g_m)[4]`。做 P = 3 遍；每遍按能量降序遍历原子 k，固定其余原子，在 `[center_k − .5, center_k + .5] ∩ [−3, 3]` 内用 `scipy.optimize.minimize_scalar(method='bounded', xatol=1e-3, maxiter=16)`（≤ 16 次评估）最小化 value；只有"所评估过的最佳点严格小于当前 value（`<`）"才接受。时延不变、原子数不变；同时延原子可以靠近乃至重合，**不加任何守卫**。最终增益 = 最终几何上 `_system` 的 `h`。`_system` 的任何异常原样上抛，该键写成 error 行（不发明修复）。
3. **第 2 轮**：`scalar_joint(gain_mode='fixed', prior=clip(check), iterations=20, damping=.3)` → LDPC（`maxiter=50`）→ 无条件 FER，与 E-3 同一调用。

**约定如何与 E-3 / E-1 对齐**（逐项读源码核对）：
- `Y = daft(obs['y'], c1, c2, True)`：与 E-3 `process_key` 及 E-1 分支（`e1_driver.run_branch`：`Y = daft(obs['y'], system.c1, system.c2, True)`）相同。
- `xt = daft(pilot + x_data, c1, c2, inverse=True)`：E-3 的字典用的是同一表达式（`sbl.columns(self_xt(pilot + μ_d, …))`）；E-1 把 `obs['pilot'] + mu` 作为 `x_mean_af` 传入核，核内部 `xt = daft(x, c1, c2, inverse=True)`。软均值变体的 `xt` 与 E-3 的字典 `Bs` 位对位同源；`_system` 的 `B` 与 `sbl.columns` 都来自同一冻结 `_responses`。
- `ridge = float(obs['sigma2'])`（E-1 同；E-3 的 β₀ 用的也是这个 σ²）。`v` 来自 `moments(clip(raw_app, ±20), pd)`，`pd = 1 − system.rho`。
- `Path` 取自 `geometry_reopen_variant`（`_system` 同模块）；E-3 的 SBL 仍用冻结 `geometry_reopen` 的 `Path/_responses`，两者的 `_responses` 是同一份代码。
- hard / genie：`v_m = 0`（全零向量），`gamma_mode='full'`（v = 0 时不起作用，门 G2 断言 `_system` 返回的 gamma 恒为 0，逐键写入 `refine.gamma_abs_max` 并由聚合阻断）。diag：`gamma_mode='diag'`（gamma = Σv·I）；cov：`'full'`。

## 3. 变体与配对

| 变体 | 字典里的数据（xt） | v_m | g_m | 对照（E-3 行） |
|---|---|---|---|---|
| hard-off | 硬判决重调制 Mod[Demod(μ_d)] | 0 | full（无作用） | L-hard |
| diag-off | 软均值 μ_d | v | diag | L-diag |
| cov-off | 软均值 μ_d | v | full | L-cov |
| genie-off | 真数据 `raw['data']/scale` | 0 | full（无作用） | L-genie |

键：U/G × ρ.3 × SNR {6,…,11} dB × 帧 4000..4199，共 2400 个（`e3b_lib.main_keys`，有序 (帧, 场景, SNR)），全部包含在 E-3 主跑键中（E-3 `GRID.json` 对 U_300 与 G_300 均为 {6..11}）。on-grid 结果直接取 E-3 行，不重跑。每行记录细化前的 SBL 输出原子（`atoms_ongrid`），聚合在全部 2400 键上与 E-3 行的 `atoms` 做精确比较，并核对第 1 级原子、第 1 轮 decoded sha、第 2 级候选数；任何不一致都阻断解读。E-3 行从 deinlab 的 `tf_e3_sbl_20261017/out/main/rows_shard*.jsonl.gz` 读取，先按其 `REMOTE_ROWS_MD5.txt`（md5 `ecdf211c0768d7248073c5d0393576a5`，96 个文件）逐一核对。

## 4. 读数

预注册（不参与判定）：每个变体 on-grid 与 off-grid 的 FER 及 1e-2 穿越点；同时延普查（口径同 E-3：`n_pair`、幻影超额；注意时延不变，所以 `n_pair` 与 on-grid 相同，细化只改变 |Δν| 分布）；细化后同时延对的 |Δν| 分布与 |Δν| < .1、< 1e-6 的比例；NMSE；细化接受率（总体与分遍）；每坐标评估数、位移、cond(Q)；成本。

## 5. 冻结判据（design §3，逐字）

记号：A_on = FER(L-cov) − FER(L-diag)（E-3 行，同一批键）；A_off = FER(cov-off) − FER(diag-off)；Δ = A_on − A_off。所有量都用配对 cluster bootstrap（cluster = (场景, 帧)，20000 次，seed 20261017，百分位 95% CI；`e1_agg.bootstrap_rates`，同一次重抽样内计算所有量）。另报告 diag-off 对 cov-off 的精确单侧 McNemar（H1：diag-off 成功更多），取 log10 p（并报反向与 on-grid 对照）。判定按顺序取第一条成立者（互斥）：

1. **REVERSED**：CI_hi(A_off) < 0 且 CI_lo(Δ) > 0。细化后完整 Γ 反而更好，插值解释被支持。
2. **VANISHED**：CI(A_off) ⊂ [−.01, .01]（闭区间）且 CI_lo(Δ) > 0。优势消失，插值解释被支持。
3. **REDUCED**：CI_lo(A_off) > 0 且 CI_lo(Δ) > 0。优势缩小但仍在，插值解释只解释了一部分。
4. **PERSISTS**：CI_lo(A_off) > 0 且 CI_lo(Δ) ≤ 0。优势不受细化影响，插值解释被否定。
5. **MIXED**：以上都不成立。

凡"CI 含 0"一律附注 "not significant != equivalent"。聚合拒绝解读（`interpretable=false`）当：行集 ≠ 冻结的 2400 键、出现 error 行、行缺变体、含 smoke 行、缺 E-3 配对行、on-grid 阶段与 E-3 行不一致、细化不变量失败（value 单调、每坐标 ≤ 16 次评估、Doppler 在 [−3,3] 与窗口内、`value_recheck_equal`）、gamma 结构失败（hard/genie 的 gamma ≠ 0；diag 的非对角 ≠ 0；diag/cov 的 diag(Γ) ≠ Σv，1e-10）、任一 md5 清单不符、或 gates 不全过。实现 `e3b_agg.py`；`test_e3b_agg.py` 覆盖五个判定分支、`verdict()` 的边界与优先级、全部阻断条件。

## 6. 门（跑前；结果 `out/gate/gates.json`、`out/unit/test_e3b.json`，全部通过）

- **G1 on-grid 一致**：20 个键（`gate_keys`：对 2400 个主跑键做 seed 20261017 的不放回抽样）重跑 E-3 的 on-grid 第 2 级。第 1 级原子、第 1 轮 decoded sha、候选数，以及四个变体的 SBL 输出原子（时延/Doppler/能量，位对位）、on-grid 第 2 轮 decoded sha、信息比特错误数，**20/20 键全部等于 E-3 行**。
- **G2 细化正确性**：(a) 合成单径分数 Doppler（6 个 ν₀，v = 0，Y 由 `Channel.apply` 独立生成）细化后 Doppler 误差最大 1.03e-4（< 1e-3）；(b) 合成多径含同时延原子与近重合起点：value 单调不增、≤ 16 次评估/坐标、位于 [−3,3] 与窗口内；(c) v = 0 时 `_system` 的 gamma 对 diag/full 都恒为 0（含两条距离 1e-6 的同时延路径），v > 0 时 diag 只留对角（= Σv）而 full 有非对角；(d) 平坦目标（Y = 0）不接受任何更新，边界原子窗口不越界。真实键：20 键 × 4 变体（5145 个坐标搜索，4788 个接受）的 value 单调、每坐标评估数 ≤ 16、边界/窗口、gamma 结构全部通过，`_system` 失败 0 次，最大 cond(Q) = 7.1e3。
- **G3 确定性**：合成 `refine()` 两次逐位一致（diag/full）；真实键 20 个整条流水线（四个变体、两轮）跑两次，去掉计时字段后逐位一致 20/20。
- **G4 成本**：由 smoke 估计（§7）。规则：估计核时 = smoke 每键平均秒数 × 2400 / 3600，门用 ×1.3 争用系数（design §4）后的值，须 ≤ 30。结果 10.37 → 13.48 core-h，通过。

## 7. 成本

smoke = 16 键，U/G × ρ.3，每个 SNR 各 ≥ 2 键（SNR 6/7/8/9 dB 各 3 个，10/11 dB 各 2 个；U/G 在每个 SNR 都出现），帧 8300..8315（与主跑帧 4000..4199 不相交，行内 `smoke=true`，不得并入分析），16 个进程同时运行（负载约 9），含 on-grid 对照轮（其耗时不计入）：每键 **15.55 s**（最小 12.83，最大 19.21），其中每变体 SBL 2.4–2.55 s、细化 hard 1.26 / diag 1.38 / cov 1.18 / genie 0.50 s。2400 键估计 **10.4 core-h**（×1.3 争用 13.5）；design 的粗估为 16–21。上限 30 core-h，同时最多 24 个进程，保留 ≥ 16 核空闲。
smoke 计数（仅计数）：16 键 0 个 error 行；FER 事件数 on-grid 重跑 / off-grid：hard 3/4，diag 1/1，cov 3/4，genie 0/0；细化坐标 4014 个、接受 3750 个、评估 33838 次，单坐标评估数最大 16；`_system` 失败 0 次，cond(Q) 最大 422；off-grid 同时延对数 hard 104、diag 470、cov 94、genie 86，其中 |Δν| < .1 的对数 0 / 288 / 2 / 5，|Δν| < 1e-6 的对数全为 0。（完整表见 `out/smoke/SMOKE_COUNTS.md`。）

## 8. 运行手册

`launch_e3b.sh`（deinlab，tmux `g_e3b*`，conda AFDM，单线程分片，ssh 命令一律 `</dev/null`）：
- `MODE=gate`：单测（`test_e3b.py`、`test_e3b_agg.py`）+ G1/G2/G3（20 分片）+ 合并 → `out/unit`、`out/gate`。
- `MODE=smoke`：16 键冒烟（16 分片）+ 计数 + 与 G4 合并 → `out/smoke`、`out/gate/gates.json`。
- `MODE=chain`（无人值守，**23 个分片** + 一个短暂的成本检查进程 = 最多 24 个进程）：核对 `CODE_MD5.txt`；要求 `out/gate/gates.json` 的 `all_pass` 为真；跑主跑（2400 键按有序键表切成 23 个连续块）；约 10%（240 行）与 50% 行数时各做一次成本推算（均值 (`seconds.total` + `gen_seconds`) × 2400 / 3600），超过 30 core-h 则杀掉分片并写 `E3B CHAIN STOPPED …`；然后聚合（`e3b_agg.py`，读未压缩行）→ gzip + md5 清单（`out/main/REMOTE_ROWS_MD5.txt`、`out/analysis/ANALYSIS_MD5.txt`）。`out/main/STATUS.txt` 以 `E3B CHAIN DONE <utc>` 或 `E3B CHAIN STOPPED <reason>` 结束。停止后保留行，原样重跑同一命令即续跑（已完成的键跳过）；已定稿（存在 `REMOTE_ROWS_MD5.txt`）时拒绝重跑。
- 启动：`mkdir -p out/main; tmux new-session -d -s g_e3b 'MODE=chain bash launch_e3b.sh >> out/main/launch_chain.log 2>&1'`。
- `MODE=agg`：只重跑聚合。
两条链路径（成本停止、正常完成）已在 scratch 副本（smoke 键、4 分片）上演练通过，演练目录已删除。失败分片原样保留，不重试不换配置。只回传小文件，行数据留 deinlab。

## 9. 局限

连续一维坐标搜索不是 Luo 的 Taylor 更新，属于同类机制的简化；细化只作用在 SBL 的输出原子上，不进入 EM 迭代内部；只覆盖 ρ.3、两个场景、200 帧；n_pair 不随细化改变（时延固定），细化只改变同时延对的 Doppler 间距与增益；结论只限本移植、P1 信道、N=1024、QPSK、本 LDPC 码。

## 10. 与 design.md 的偏差、澄清与执行期事实

1. **窗口中心（对 design §1.3 的读法）**：design 写作 `[ν_k − .5, ν_k + .5] ∩ [−3, 3]`，并称"与 CSTATE 局部细化同型"。CSTATE 的窗口固定在进入局部阶段时的几何上，这里照此处理：窗口中心 = SBL 输出的网格 Doppler，三遍之间不重新居中（原子最多偏离其网格点 .5）。若编排者要求"每遍以当前 ν_k 重新居中"，需在冻结前改 `offgrid_refine.refine` 并重跑门。
2. **接受准则**：严格 `<`，没有 CSTATE 的 1e-10 相对判据（design 写"严格下降"）。后果：浮点噪声量级的下降也算接受，接受率因此偏高（真实键 93%）。
3. **不实现 Luo 的 Taylor off-grid 步**：用连续一维搜索代替（prd 已声明）。
4. **分片数 23**（不是 24）：保证"分片 + 成本检查"≤ 24 个并发进程；块大小 104–105 键。
5. **链的顺序**：run → 成本检查 → agg（读未压缩行）→ gzip + md5（按编排者的列举顺序）。成本检查在 10% 与 50% 行数各一次（后者是额外护栏）。
6. **G4 规则**（design 未写系数）：×1.3 争用后的估计须 ≤ 30（§6）。
7. **on-grid 的 SBL 阶段重跑**：细化需要 SBL 输出原子与（对软均值变体的）`xt`，E-3 行没有保存增益，所以四个变体的第 2 级 SBL 重跑；on-grid 的 FER 等结果仍取自 E-3 行。重跑与 E-3 的一致性：主跑 2400 键逐键比对原子（聚合阻断），门 G1 另比 decoded sha。on-grid 第 2 轮仅在门与 smoke 中额外运行，耗时不计入成本。
8. 细化前的初始 `_system` 求值用来取 `value_before`（不用其 h）；每个变体多一次最终 `_system` 求值取 h 与 gamma。
9. 每行 `_argv` 为完整 `sys.argv`；`_config` 为该分片的实际运行配置摘要（超参、`own_md5`、`config_md5`）；完整配置（含冻结源 md5 核对表、运行时环境）在 `config_shard*.json`。
10. smoke 行内 `smoke=true`，帧 ≥ 8300，不得并入分析；它在门 G4 之外不产生任何判定。
11. 诚实声明：跑前编排者已见的数据仅有 smoke 计数（§7，非主跑帧）与 20 个 G1 键的"on-grid 一致"比较（G1 只比较等式，未产生 off-grid FER 的任何汇总）。

## 11. 来源与哈希

冻结源 md5：`SOURCE_MD5.txt`（28 项：E-3 清单 22 项 + E-3 代码 5 个文件 + `geometry_reopen_variant.py`），运行时由 `e3b_driver.check_frozen_md5` 对已加载模块逐一复核并写入每个 `config_shard*.json`。本目录代码 md5：`CODE_MD5.txt`（链启动时 `md5sum -c`）；本文件自身的 md5 由各 config 的 `own_md5` 在开跑时记录。E-3 行清单 md5：`ecdf211c0768d7248073c5d0393576a5`；E-3 `GRID.json` md5：`9f3242788a93258ae9a129a6532e5157`。门/单测产物 md5：`out/gate/gates.json` `1dd591015e7697a136f6b6a4405cc73c`，`out/unit/test_e3b.json` `506fe5c1f5a241daaee75493e67eb2e9`；smoke 行 md5 见 `out/smoke/REMOTE_MD5.txt`。
G1 的 20 个键：(U,900,4006) (U,800,4012) (G,600,4013) (G,900,4021) (U,800,4054) (G,600,4072) (U,600,4077) (U,700,4090) (G,900,4100) (U,600,4109) (U,1000,4109) (U,1100,4132) (G,1100,4134) (U,700,4153) (U,900,4164) (G,700,4164) (U,800,4170) (U,900,4174) (U,1000,4190) (G,1100,4199)（ρ 均为 .3，SNR 为 centi-dB）。
