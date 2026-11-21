# 前瞻检验："Γ 的相干结构管决策，各向同性正则管增益估计"（冻结稿）

任务 `.trellis/tasks/10-18-split-principle-prospective/`。本文件 = `design.md`（具有约束力，含编排者跑前修订 A1）并入执行期事实与偏差；两者冲突处以 `design.md` 为准，偏差全部列在 §10。A1 的内容与原因见 §10。
冻结（永不修改）：E-1 / E-3 / E-3b / E-3c / 协方差审计 / GSO 的全部目录（只读导入，不复制；md5 见 `SOURCE_MD5.txt`，运行时由 `sp_lib.source_identity` 经 `e3c_provenance.resolve_frozen` 绑定到实际导入的字节，写入每个 `config_*_shard*.json`）。新代码只在本目录。

## 1. 新帧与查证

**取用帧**：P1 流（熵 `2261fde3…`，域 TCRF）的帧 7000..7199，共 200 帧，两个族共用，每帧 = 一个簇。smoke 在帧 8600、8601（P1 流此前最大用帧 8507 与 9011 之间）。
**查证脚本** `verify_frames.py`（跑前在 deinlab 执行，回执 `out/frame_check/frames_check.json|txt`，md5 记在回执里，`test_sp.py::FrameAudit` 会核对回执与当前脚本一致）：
- 静态扫描：`experiments/` 下全部 `.py/.sh/.md`（不含本目录与 `_archive`）里落在 7000..7199 的整数共 12 个匹配（10 行），逐条归类见下。
- 配置 / 行扫描：`experiments/*/out/` 下 11201 个文件（全部 `config*.json` 以及 `rows*.jsonl[.gz]` / 结果 `json`），按 run 目录判 P1 流（目录内任一 config 含 P1 熵前缀 `2261fde33dab09d1`，或文件头含之）。**P1 流已用帧**：0..2099、3000..4399、5000..5099、6000..6099、8000..8007、8100..8103、8200..8207、8300..8315、8400..8411、8500..8507、9000..9011（来自 P1 参考帧 / 创世支撑 / CRB / E-1 / E-2 / E-3 / E-3b / E-3c / MM / GSO 的配置与行）。**P1 流在 7000..7199 的命中：无**（配置与行都没有）。deinlab 的 `/data/guoyikun/tmp` 另扫一次（163 个 json / jsonl / gz 文件）：没有任何行含该段的帧；本任务自己的开发配置仅登记了主范围，没有对该段的任何帧运行过。
- 结论：**帧 7000..7199 在 P1 流从未被使用，按设计取用，不后移。**
- 整数巧合（**不属于 P1 流**，已逐条核对其熵 / 域，随机数由 `SeedSequence(熵词, 域, 帧, 分量)` 决定，换熵或换域即为独立实现）：
  1. `headroom_ladder_20261008/ddst_gates.py:40` 帧 7000..7019、`ddst_timing.py` 帧 7100..7101：熵 `129abc3b…`（`driver_c1i.C1_MAP_ENTROPY`，C1 域），`out/ddst_timing/config_shard000.json` 为证。
  2. `headroom_ladder_20261008/out/ub_screen/*`：合成谱筛选（`seed_root` 20261015，分量 delays/data/rays，8192 个合成"帧"序号），与 P1 生成器无关。
  3. `tcom_reference_frame_20261015/p2b_gates.py:40` 的 `g5=7000`（帧 7000..7019）：P2b 的 **DEV 熵** `ca68a12b…`（域 TCDP），脚本头声明 "All gate frames come from the DEV entropy set"，`stage_g5` 用 `dev_seed()`。
  4. `sp_afdm_*/…/paired_learned_eval.py`、`e1_ldpc_coded_eval.py` 中的 `args.seed + 7000`：随机种子偏移，不是帧号。
- 严格口径备选（仅供参考）：若把"任何流里出现过该整数"也算作已用，则无整数巧合的最小起点为 8508（`frames_check.json: strict_alt`）。按 P1 流口径（本任务的口径）无需后移；若改用备选需改 `sp_lib.FRAMES` 并重跑门。
- 不触碰：所有 smoke / 门运行都不含 7000..7199 的任何帧（门键 = 旧键：E-3 帧 4000..4099 与 E-1 帧 0..19；smoke = 8600、8601；驱动里有断言，`out/gate`、`out/smoke` 行的帧集已核对）。配置里本范围的字段名为 `main_frame_range_registered`（不是 `frames`），避免以后的审计把门 / smoke 配置误认为使用了这些帧。

## 2. 键、簇与分片

- **S 族**：U/G × ρ .3 × 6..11 dB × 帧 7000..7199 = 2400 键（`sp_lib.s_keys`，帧优先排序，成本止损留下整帧）。
- **K 族**：U/G × ρ {.3, .5} × 4.5..8.0 dB（步长 .5）× 帧 7000..7199 = 6400 键（`sp_lib.k_keys`）；每个键都跑 F0（`native_twofft.receive rounds=2`，E-1 的 `f0_state`），**F0 终末 syndrome ≠ 0 的键为触发单元**，才跑四个 K 臂。
- **簇** = 随机数帧 (rng_entropy, rng_domain, frame)：同一帧在不同场景、ρ、SNR、两个族的行共享外生随机输入（噪声、物理增益、编码比特、信息比特的哈希；冒烟已验证帧 8600 上 S 行与 K 行、U/G、ρ .3/.5、两档 SNR 的四个哈希完全一致）。两个族各 200 个簇。
- **分片**：同一 (帧, 场景, ρ) 的各 SNR 键构成一组，基础帧只生成一次；组 g 归分片 g mod N。S 共 400 组、K 共 800 组。

## 3. 臂

**S 族**（E-3 管线，on-grid 第 2 级；与 GSO 共用 `process_key` 的算术）：

| 臂 | 选原子 | 增益 |
|---|---|---|
| S-D | SBL，Γ_var = Σv·I | SBL 后验均值（= E-3 L-diag） |
| S-C | SBL，Γ_var = 完整 Γ | SBL 后验均值（= E-3 L-cov） |
| **S-H** | 沿用 S-C 选出的原子 | `_system(Y, xt_soft, v, paths, c1, c2, ridge = σ², gamma_mode = 'diag')` 的 h = (B̄ᴴB̄ + Σv·I + σ²I)⁻¹B̄ᴴY |

第 2 轮：`scalar_joint(gain_mode='fixed', prior=第 1 轮 check)` 再接 LDPC（E-3 的 `detect_decode`）。S-C 与 S-H 共用同一次 SBL（同一支撑），每键两次 SBL。

**K 族**（E-1 管线）：

| 臂 | 交换决策 | 送入检测器的增益 |
|---|---|---|
| K-prod | 完整 Γ（E-1 的 A1，生产 CSTATE20） | `scalar_joint(gain_mode='joint')`，检测器重新估计增益 |
| K-diag | 对角 Γ（E-1 的 A2） | 同 K-prod（复现 E-1） |
| K-fullfix | K-prod 的最终路径 | `gain_mode='fixed'`，h = `_system(…, 'full')`（= `result.gains`） |
| **K-isofix** | K-prod 的最终路径 | `gain_mode='fixed'`，h = `_system(…, 'diag')` |
| K-diag-fullfix（A1 新增） | K-diag（A2）的最终路径 | `gain_mode='fixed'`，h = `_system(…, 'full')` 在 A2 最终路径上 |
| **K-diag-isofix**（A1 新增） | K-diag（A2）的最终路径 | `gain_mode='fixed'`，h = `_system(…, 'diag')` 在 A2 最终路径上 |

K-prod / K-diag **就是**冻结的 E-1 `run_branch` + `arm_record`（只读导入，原样调用），记录里另加同时延普查字段。固定增益臂用 E-3 的 `detect_decode`（`gain_mode='fixed'`，prior = r1 check，`decoder_messages(maxiter=50)`），与 E-1 分支只差 `gain_mode`。K-fullfix / K-isofix 的路径与 K-prod、K-diag-fullfix / K-diag-isofix 的路径与 K-diag 逐元素相同（聚合时核对）。注意 A2 的核用 `gamma_mode='diag'` 解增益，所以逐位等于 A2 `result.gains` 的是 **K-diag-isofix** 的增益（K-fullfix 对 A1 的类比）；K-diag-fullfix 的增益与 A2 `result.gains` 不同（见 §10 D10）。

## 4. 冻结的预测与判定（`sp_agg.py`）

配对 cluster bootstrap：按帧聚类，20000 次多项式重抽样（冻结的 `sampling.bootstrap_means`），seed 20261018，百分位 95% CI。S 与 K 各自重抽样（同一种子；两族簇集合同为这 200 帧）。对比量按逐行配对差再重抽样（整数），因此理论上为 0 的端点是精确 0.0，严格不等式不会被浮点抵消翻转。

- **P1（S，估计）**：d1 = FER(S-H) − FER(S-C)，要求 ci_hi(d1) < 0。
- **P2（S，非劣）**：d2 = FER(S-H) − FER(S-D)，要求 ci_hi(d2) ≤ .01。
- **P3a（K，估计，A2 几何；A1 取代原 P3）**：r3a = R(K-diag-isofix) − R(K-diag-fullfix)，要求 ci_lo(r3a) > 0。
- **P3b（K，等价，A1 几何）**：r3b = R(K-isofix) − R(K-fullfix)，要求 CI ⊂ [−.01, .01]（闭区间，即 ci_lo ≥ −.01 且 ci_hi ≤ .01）。
- **P4（K，决策 = E-1 复现）**：r4 = R(K-prod) − R(K-diag)，要求 ci_lo(r4) > 0。

救回率 R(arm) = Σ[触发 且 信息比特 0 错] / Σ[触发]（E-1 的成功定义）。分子分母取自**同一次**重抽样的总量，且对全部 6400 键（含无触发单元的帧）逐帧重抽样，用冻结的 `ratio_summary` 给 CI：若 > 1% 的重抽样分母 ≤ 0，则该比值**不可评价**（`evaluable = false`）：P3a / P3b / P4 视为未成立，且 K 侧的 REFUTED 不可宣布；直接差仍会报告。

判定按顺序取第一条成立的：
1. **REFUTED**：ci_lo(d1) > 0（P1 显著反向），或 ci_hi(r3a) < 0（P3a 显著反向）。P3b、P4 往任何方向失败都不构成 REFUTED。
2. **CONFIRMED**：P1、P2、P3a、P3b、P4 全部成立。
3. **PARTIAL**：P1 与 P3a 成立，但 P2、P3b、P4 中至少一个不成立。
4. **MIXED**：其他。

报告项（不进判定）：各臂的 FER / 救回率及 CI、NMSE（S 族）、同时延普查（总数及落在真时延 / 非真时延的对数）、SBL 迭代上限命中数与比例、精确单侧 McNemar（把行当独立配对，仅报告）、按 (场景, SNR) 与 (场景, ρ, SNR) 的格点计数、成本。

## 5. 聚合拒绝解读（fail closed）

下列任一情形 `interpretable = false`，此时只输出原因，不输出任何 FER、救回率、对比或判定：行集 ≠ 冻结的 2400 + 6400 键、缺失 / 重复 / 外来键、error 行、smoke / 门 / v≡0 行混入或族标记错、S 缺臂、K 触发单元缺臂（六个臂缺一不可）或无触发行带臂、触发标记与 F0 syndrome 矛盾、FER 与 info_errors 不一致、NMSE 非有限或为负、S-H 与 S-C 原子支撑或 SBL 记录不同、SBL 迭代上限记录自相矛盾、S-H / K-isofix 增益与独立 numpy 岭回归解之差超过 max(1e-10, 64·ε·cond(Q))、K-fullfix 增益不等于 A1 `result.gains`、K-diag-isofix 增益不等于 A2 `result.gains`、两个 isofix 臂的增益与独立岭回归解不符、固定增益臂路径与其几何臂（K-prod / K-diag）不同、分片配置源快照不一致（含 S 与 K 之间）、簇内外生哈希不一致、簇数 ≠ 200、`gates.json` 不是 all_pass 或其源快照与主跑不同。`test_sp_agg.py`（61 个测试）逐项覆盖，并覆盖 CONFIRMED（五个预测全部成立）、PARTIAL（P2 失败、P3b 失败、P3b 反向失败、P4 失败）、REFUTED（S 侧、P3a 反向、双侧）、MIXED（含 P3a 不成立但未反向、一族单独成立）、P3b 闭区间边界、不可评价的 K 分母。

## 6. 门（跑前，结果见 `out/gate/gates.json`、`out/unit/*.json`；全部通过，`all_pass = true`，`item_errors = []`）

门键全部是**旧键**：S = 与 GSO / E-3c 相同的 20 个（帧 4000..4099，seed 20261018 无放回抽取），G2 的 v≡0 重跑取其中每隔 3 个的 7 个；K = 从 E-1 "gate 状态"（帧 0..19 的 159 个触发单元）按同一种子无放回抽取的 20 个。
- **G1**：S：第 1 级原子、第 1 轮 decoded sha、第 2 级候选集大小，以及 S-D / S-C 对 E-3 L-diag / L-cov 的 decoded sha、被选原子、info_errors、FER、NMSE（浮点逐位）、同时延对数、原子数、SBL 迭代数 / 收敛标志 / β / n_final，**20/20 逐位一致**。K：F0 状态（syndrome、info_errors、decoded sha、LDPC 迭代）、第 1 轮几何、K-prod / K-diag 对 E-1 存储的 A1 / A2 记录（除计时外的全部字段，含 edits、objective、condition_number），**20/20 逐位一致**（K 行里新增的 K-diag-* 臂不参与比较）；并且 K-prod 的分支与生产 `ctx.branch(…, 'CSTATE20')` 的 `branch_core` 逐位相同 **20/20**。
- **G2**：(a) v ≡ 0（第 1 轮 moments 之后令 v := 0）7 键：S-D = S-C（原子、增益哈希、decoded sha、NMSE、info_errors、SBL 记录）、S-H 原子 = S-C 原子、S-H 增益 = 在 S-D 原子上做同一岭回归的增益、S-H 增益 = 独立 numpy 岭回归解、Γ 全零，**7/7**；(b) 全部 27 次 S 运行与 20 个 K 单元的 S-H / K-isofix 增益对独立 numpy 求解（`(B̄ᴴB̄ + (Σv+σ²)I)h = B̄ᴴY`，LU）的相对误差最大 1.8e-15（容限 1e-10；最差 cond(Q) = 25.1），核返回的对角 Γ = Σv 的相对误差 ≤ 2.4e-16（47 项）；(c) **K-fullfix 增益 = A1 `result.gains` 比特级相等 20/20；K-diag-isofix 增益 = A2 `result.gains` 比特级相等 20/20**（见 D10：A2 的核用 diag 解增益，所以是 isofix 而非 fullfix）；K-diag-fullfix 增益与 A2 `result.gains` 不同（0/20 相等，诊断量，不是门）；(d) 两个 isofix 臂的增益对独立 numpy 解的相对误差最大 8.6e-16（K 的 cond(Q) 最差 42.3）。
- **G3 确定性**：S 20 键 + K 20 单元各整条流水线重算一次，去掉计时字段后逐位一致 **40/40**。
- **G4 成本**：见 §8，估计 6.15 core-h ≤ 15。
- **单元**：`test_sp.py`（22 个：键集 = GSO / E-3c 的键与门键、分组与分片、帧审计回执、岭回归增益对独立解、diag/full 与零方差、Γ_var 两种取法、E-3 / E-1 复现比较对每个字段敏感、常量在驱动与聚合间一致）与 `test_sp_agg.py`（61 个）全部通过。门 / 冒烟 / 单元三处源快照一致（`gates.json: sources_identical = true`，快照写入 `sources_sha256`），主跑聚合再核对一次。
- 作废的门运行（`out/_superseded/*attempt1`、`*attempt2_pre_A1`，仅在 deinlab）：第一次因把配置字段 `frames` 改名为 `main_frame_range_registered` 而作废；第二次是 A1 之前的版本（K 族四个臂），因 A1 加臂而作废（代码身份变了）。门最终以 A1 之后的这一次为准。
- **A1 新臂的旧单元诊断**（只在 20 个旧 E-1 gate 单元上；不是任何新帧结果）：K-diag-isofix 与 K-diag-fullfix 的增益相对差，最小 6.5e-5、中位数 0.135、最大 0.407（19/20 个单元 > 1e-3，19/20 > 1e-2）；对照 A1 几何的 K-isofix 与 K-fullfix：最小 2.3e-5、中位数 7.1e-5、最大 8.2e-4。A2 路径上近重合同时延对多，P3a 因此有判别力，A1 路径上两种增益几乎一致，P3b 的等价预测是可检验的。

## 7. 冒烟（帧 8600、8601，S 8 键 + K 8 键，8 进程并发；`out/smoke/smoke_counts.json`；**只是冒烟，不并入任何分析**；以下只列计数，不作解读）

0 error 行，0 次 Cholesky jitter；两族的外生哈希按帧一致。S：第 2 级候选集平均 644.6 个原子；每键秒数约 5.3–6.6；平均输出原子数（S-D 24.0 / S-C 23.1 / S-H 23.1）；同时延对数合计（S-D 224 / S-C 30 / S-H 30）；撞迭代上限的键数（S-D 4 / S-C 8 / S-H 8，共 8 键）；S-H 对独立 numpy 解最大相对误差 7.3e-16；S-H 支撑 = S-C 支撑。K：8 键中触发 3、未触发 5；每键秒数 触发 0.88–0.98、未触发 0.25–0.37（F0 平均 0.27 s）；K-fullfix 增益 = A1 `result.gains` 3/3，K-diag-isofix 增益 = A2 `result.gains` 3/3；isofix 臂对独立 numpy 解最大相对误差 7.8e-16；同时延对数合计（K-prod 0 / K-diag 8 / K-fullfix 0 / K-isofix 0 / K-diag-fullfix 8 / K-diag-isofix 8）。

## 8. 成本

冒烟平均每键：S 5.90 s，K 触发 0.94 s、K 未触发 0.28 s（deinlab 近空闲；A1 的两个新臂使触发单元每键增加约 0.1 s）。S 2400 键 = 3.94 core-h；K = (6400 − T)×0.28 + T×0.94，T = E-1 账本触发率 × 6400 = 1637.9，= 0.79 core-h；合计 **4.73 core-h**，按 E-3c 的竞争因子 1.3 计 **6.15 core-h ≤ 15 core-h**（G4 通过）。门 + 冒烟 + 单元的工程成本另计，合计 0.1000 core-h（`gates.json: engineering_core_hours`；作废的两次门运行另各约 0.1），不计入 15 core-h 止损。链内置成本止损：两个族所有分片已提交的成本之和 ≥ `COST_CAP_H`（默认 15）核时不再开新键（最多再超出已在跑的 ≤ 16 个键，约 0.03 core-h），写 `COST_STOP`，链结束时写 "SP CHAIN STOPPED"，此时聚合因行集不全而 `interpretable = false`。预计墙钟：S 13 分片约 18–25 分钟，K 3 分片约 15–20 分钟，二者并行。

## 9. 运行手册

`launch_sp.sh`（tmux 会话名 `g_sp`，仅 CPU，单线程进程，进程数 ≤ 16，启动前检查 load 以保留 ≥ 16 核空闲）：
- `MODE=gate`（单元 + G1–G3 + 冒烟 + G4 合并 → `out/unit`、`out/gate/gates.json`、`out/smoke/smoke_counts.json`；已在 A1 之后重新执行，门运行用 `setsid nohup` 而非 tmux 前台执行）。
- `MODE=chain`（无人值守：校验 `CODE_MD5.txt` 与 `gates.json` → 13 个 S 分片 + 3 个 K 分片并行 → `sp_agg.py --gates` → 行文件 gzip + md5 清单 `REMOTE_ROWS_MD5.txt` → 在 `out/main/STATUS.txt` 追加 `SP CHAIN DONE <utc> (...)` 或 `SP CHAIN STOPPED <utc> (原因)`）。`STATUS.txt` 另有一行 `rows_S=… rows_K=… interpretable=… verdict=<标签>`（沿用 GSO 链的写法；聚合标签只在聚合可解读时才有）。
- 输出目录绝不覆盖也不续跑：重跑前把 `out/main` 移走；失败分片原样保留，不重试不换配置；一个键失败即写 error 行并终止该分片。只回传小文件，行数据留 deinlab（gzip + md5）。链的 DONE / STOPPED / 异常退出 / 重复启动 / 门未通过 / 代码被改 / 进程数 > 16 的各分支已在 deinlab 沙箱副本上用桩驱动端到端演练（沙箱 `SP_DIR`，**未触碰任何主帧**）；驱动的成本止损在 smoke 键上演练（`--cost-cap-seconds 1`：1 键后写 `COST_STOP`）。
- 启动命令（编排者执行；`launch_sp.sh` 自己做 `md5sum -c CODE_MD5.txt`，所以远端代码必须与提交一致）：
```
ssh deinlab "cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_split_prosp_20261018 && mkdir -p out/main && tmux new-session -d -s g_sp 'MODE=chain bash launch_sp.sh > out/main/launch_chain.log 2>&1'"
```
默认 `NS=13`、`NK=3`、`COST_CAP_H=15`（环境变量前缀加在 `MODE=chain` 前；`NS + NK ≤ 16`）。

## 10. 与 design.md 的执行期偏差与说明

- **A1 编排者跑前修订（2026-10-18，冻结前，未见任何新帧结果；design.md 末节 "编排者跑前修订 A1"）**：原因是门检诊断只用旧的 gate 单元，在这些单元上 K-isofix 与 K-fullfix 的增益相对差只有 2e-5 到 8e-4（cond(Q) ≈ 1.2），A1 的最终路径间隔很开，原则本身就预测两种增益在这里没有区别，所以原 P3 没有判别力。改动：(1) 新增 K 臂 K-diag-fullfix / K-diag-isofix（K-diag 的 A2 最终路径，`gain_mode='fixed'`，增益取 `_system(…, 'full'|'diag')`；A2 路径里近重合同时延对很多）；(2) P3 换成 P3a（R(K-diag-isofix) − R(K-diag-fullfix) 的 ci_lo > 0）并新增 P3b（R(K-isofix) − R(K-fullfix) 的 CI ⊂ [−.01, .01]）；(3) 判定改为 REFUTED = P1 或 P3a 显著反向，CONFIRMED = P1、P2、P3a、P3b、P4 全部成立，PARTIAL = P1 与 P3a 成立但 P2、P3b、P4 至少一个不成立，MIXED = 其余。实现于 `sp_driver.process_key_k`（固定增益臂对两种几何各一对）、`sp_agg.verdict(d1, d2, r3a, r3b, r4)`；帧范围不变（7000..7199，其他 RNG 流里的整数巧合不算使用，见 §1），键集不变。
- **D10 A1 的 G2 门按实际恒等式设**：A1 的说明写 "K-diag-fullfix 的增益必须逐位等于 A2 `result.gains`"。但 A2 的核（`reopen_geometry(…, gamma_mode='diag')`）用 diag 模式解增益，所以 `result.gains` = `_system(…, 'diag')` 的 h，即 **K-diag-isofix** 的增益；K-diag-fullfix（full 模式）与它不同，字面照做的门必然失败（旧单元上相对差 11.8% 等）。实现与门验证的是类比 A1 的恒等式：**K-diag-isofix 增益 = A2 `result.gains` 逐位相等（20/20）**，同时保留 **K-fullfix 增益 = A1 `result.gains`（20/20）**；K-diag-fullfix 与 A2 `result.gains` 是否相等作为诊断记录（0/20），不是门。聚合在主跑里同样强制这两条恒等式。

- **D1 G2 的 "v ≡ 0 时 S-H = S-C" 不是恒等式**：S-C 的增益是 SBL 后验均值 (B̄ᴴB̄ + β⁻¹diag(1/γ))⁻¹B̄ᴴY 在被选原子上的分量（先验方差 γ 由 EM 学出，且是活跃集上的解、不是在被选原子上重解），S-H 是 σ²·I 岭回归在被选原子上的重解，二者即使 v ≡ 0 也不相等（7 个 v≡0 门键上相对差 6.8%–8.9%；20 个真实门键上 6.2%–57%）。我实现并验证的是它的精确对应物：v ≡ 0 时 (i) S-D = S-C 逐位相同，(ii) S-H 在 S-C 原子上的增益 = 在 S-D 原子上的增益（逐位），(iii) = 独立 numpy 岭回归解，(iv) 核返回的 Γ 全零；S-H 与 S-C 的相对差作为诊断记入每行 `iso_check.rel_diff_vs_sc`。
- **D2 救回率的统计量**：R 取"同一次重抽样的总量之比"，对全部 6400 键逐帧重抽样（含无触发单元的帧），用冻结的 `ratio_summary`（>1% 分母非正则不可评价）；没有只在有触发单元的帧内重抽样（那样簇集合依赖数据）。差值 r3a、r3b、r4 是逐行配对差之总量除以同一触发总量（两臂分母相同）。
- **D3 K 的 G1 状态与生产核对**：G1 的 20 个 K 单元取自 E-1 gate 帧 0..19 的 159 个触发单元；除对 E-1 存储记录逐位比较外，加做了与生产 `ctx.branch(…, 'CSTATE20')` 的逐位比较（E-1 自己的 G1 也这样做）。未触发键的 F0 判据（syndrome ≠ 0）由 E-1 的 G4b（640/640 与账本一致）覆盖，本任务不重复。
- **D4 数值核对的阈值**：门 G2 按绝对 1e-10（实测最大 1.8e-15，cond(Q) ≤ 25.1）；主跑聚合里放宽为 max(1e-10, 64·ε·cond(Q))（同 GSO D5），错误的解仍被阻断（单元测试覆盖）。
- **D5 主键没有 E-3 / E-1 账本**：主键是全新帧，故主跑行没有 `baseline_check`；复现性只由门（旧键）负责，并由"门 / 冒烟 / 单元 / 主跑源快照一致"保证同一份代码。
- **D6 冒烟组成**：S = 帧 8600、8601 × U/G × 6 / 11 dB（8 键，4 组）；K = 帧 8600 × 四个 (场景, ρ) × 4.5 / 8.0 dB（8 键，4 组，含 ρ .5 @ 4.5 dB 的必触发单元，也含未触发单元）；K 冒烟固定在同一帧，以便验证基础帧复用和外生哈希在场景 / ρ / SNR / 族之间的不变性。
- **D7 分片按组**：主键按 (帧, 场景, ρ) 成组，一组共用一次基础帧生成（GSO 是每键重新生成），组 g 归分片 g mod N；进程分配 13 + 3 按冒烟计时使两族墙钟大致相等，可用 `NS`/`NK` 覆盖。
- **D8 STATUS 里有判定标签**：`STATUS.txt` 的 `rows_S=… verdict=<标签>` 行沿用 GSO 的写法，在聚合可解读时写出判定标签。
- **D9 门的执行方式**：门运行用 `setsid nohup` 在 deinlab 后台执行并一次性阻塞等待，未经 tmux；主跑按要求用 `g_sp` 会话。

## 11. 局限与已知的功效问题

- 仅 on-grid 第 2 级 SBL（S）与 E-1 紧凑 CSTATE（K）；仅 U/G；K 族在 4.5..8.0 dB 的低 SNR 区，触发单元多数落在 ≤ 6 dB。
- **A1 几何上的 P3b 是等价预测**：20 个旧门单元上 K-isofix 与 K-fullfix 的增益相对差只有 2.3e-5–8.2e-4，预计两者救回率几乎相同，P3b 因此可能成立；A2 几何上 K-diag-isofix 与 K-diag-fullfix 的增益相对差中位数 0.135（最大 0.41），P3a 有判别力。S 族上 S-H 与 S-C 的增益相对差 6%–57%。
- 结果只出 draft 卡，是干预结果的描述，不证明机制；MIXED / PARTIAL 不等于"原则错"，REFUTED 只说明估计方向的预测被数据否决。
