# Γ 只用于选原子、增益用无 Γ 最小二乘（GSO）：偏差 vs 方差判别协议（冻结稿）

任务 `.trellis/tasks/10-18-gamma-support-only/`。本文件 = `design.md`（具有约束力）并入执行期事实与偏差；两者冲突处以 `design.md` 为准，偏差全部列在 §9。
冻结（永不修改）：E-3 / E-3b / E-3c / 协方差审计 / 模型匹配检查的全部目录（只读导入，不复制；md5 见 `SOURCE_MD5.txt`，运行时由 `gso_lib.source_identity` 经 `e3c_provenance.resolve_frozen` 绑定到实际导入的字节，写入每个 `config_shard*.json`）。新代码只在本目录。前置：res-20261018-01（E-3c）、res-20261018-02（Berkson 事后玩具模型）。

## 1. 问题与臂

两种解释对"完整 Γ 的缺陷在哪"给出相反预测。偏差（Berkson）解释：把 Γ 加进 Gram 过度收缩增益，故完整 Γ 只用于选原子、增益改用无 Γ 的最小二乘时 FER 应改善。方差（正则化）解释：缺陷在近共线差方向上的正则不足（E-3c 中各向同性 ridge 追回 92%），故无 Γ、只带 σ² ridge 的 LS 增益应更差。本实验在同一批键上直接比较。

六个臂共用同一观测、第 1 级、第 1 轮、软均值字典 B̄ 与第 2 级候选集（E-3 `process_key` 的逐字算术），只在 (i) 第 2 级 SBL 的 Γ_var 与 (ii) 增益估计器上不同：

| 臂 | SBL 中的 Γ_var | 增益 | 实现 |
|---|---|---|---|
| D-sbl | Σv·I | SBL 后验均值 | `sbl_em(Gamma=float(v.sum()))`（= E-3 L-diag，逐位复现） |
| C-sbl | 完整 Γ(v) | SBL 后验均值 | `sbl_em(Gamma=gamma_full(...))`（= E-3 L-cov，逐位复现） |
| C-ls0 | 完整 Γ（只决定选哪些原子） | LS0 | 与 C-sbl 同一次 SBL，选出的原子相同 |
| D-ls0 | Σv·I（只决定选哪些原子） | LS0 | 与 D-sbl 同一次 SBL |
| Z-sbl | 0 | SBL 后验均值 | `sbl_em(Gamma=None)` |
| Z-ls0 | 0（只决定选哪些原子） | LS0 | 与 Z-sbl 同一次 SBL |

被选原子的规则 = E-3 `select_output`。**LS0** = 冻结核 `geometry_reopen_variant._system(Y, xt_soft, zeros, paths, c1, c2, ridge=σ², gamma_mode='full')` 的返回值下标 3（h）：v = 0 时核返回的 gamma 全为零，故 h = (B̄ᴴB̄ + σ²I)⁻¹B̄ᴴY；驱动在每个 LS0 臂上断言 `gamma` 全零并记录与独立 `numpy.linalg.solve`（LU，列取自 SBL 字典）的相对误差与 cond(Q)。第 2 轮 = E-3 的 `detect_decode`（`scalar_joint(gain_mode='fixed', prior=第 1 轮 check)` 接 LDPC）。三次 SBL 各跑一次，-sbl / -ls0 成对共用；聚合时校验每一对的原子支撑 (时延, Doppler) 完全相同。

## 2. 键与分簇

键 = U/G × ρ .3 × 6..11 dB × 帧 4000..4099，共 1200 个，与 E-3c 相同（`gso_lib.main_keys`，测试 `test_gso.py` 与 `e3c_lib.main_keys` 逐键相等）。帧优先排序，成本止损留下整帧；键 i 归分片 i mod NSHARD。on-grid 第 2 级 SBL，不做连续细化。分簇单位 = 随机数帧 (rng_entropy, rng_domain, frame)：同一帧在不同场景与 SNR 下共享外生随机输入，100 个簇、每簇 12 行（聚合时核对簇内外生哈希一致，簇数必须为 100）。

## 3. 冻结判据与报告项（`gso_agg.py`）

配对 cluster bootstrap：重抽 20000 次，seed 20261018，多项式计数重抽样（冻结的 `sampling.bootstrap_means`），百分位 95% CI；所有臂与所有对比共用同一组重抽样。令 d1 = FER(C-ls0) − FER(C-sbl)，d2 = FER(C-ls0) − FER(D-sbl)：
- **BIAS-SUPPORTED**：CI_hi(d1) < 0 且 CI_hi(d2) ≤ .01。
- **VARIANCE-SUPPORTED**：CI_lo(d1) > 0。
- 其他为 **MIXED**。
边界严格按上式（`test_gso_agg.py` 覆盖 `ci_hi = 0`、`ci_hi(d2) = .01 / .0100001`、`ci_lo = 0`）。对比量按逐行配对差（FER 为整数）做 bootstrap，因此理论上为 0 的端点是精确 0.0，严格不等式不会被浮点抵消翻转；与"臂均值之差"在同一组重抽样下代数相等。
报告项（不进判据）：D-ls0 − D-sbl、Z-sbl − D-sbl、Z-ls0 − Z-sbl、C-sbl − D-sbl（E-3 的反转本身，作背景）；每个对比的 FER 与 NMSE 差及其 CI；精确单侧 McNemar（b = 左臂单独失败，c = 右臂单独失败；报告 log10 p 的两个方向，`left_better` = 左臂失败更少；把行当独立配对，忽略分簇，仅为报告）；各臂的 FER、NMSE、被选原子数、同时延普查（总数及落在真时延 / 非真时延上的对数）、SBL 是否撞迭代上限（`cap_hit` = 未收敛 = 100 次）、Cholesky jitter、按 (场景, SNR) 的失败帧数、LS0 对 numpy 的最大误差、成本。

## 4. 聚合拒绝解读（fail closed）

下列任一情形 `interpretable = false`，此时只输出原因，不输出任何 FER、对比或判定：行集 ≠ 冻结的 1200 键、缺失 / 重复 / 外来键、error 行、smoke 或 v≡0 行混入、缺臂、FER 与 info_errors 不一致、NMSE 非有限或为负、E-3 逐位复现失败（`baseline_check.all` 为假）、E-3 行 md5 清单未核验、某一对 -sbl / -ls0 的原子支撑不同、SBL 迭代上限记录自相矛盾、LS0 与 numpy 解之差超过 max(1e-10, 64·ε·cond(Q))（见 D5）、分片配置的源快照不一致、簇内外生哈希不一致、簇数 ≠ 100、`gates.json` 不是 all_pass 或其源快照与主跑不同。`test_gso_agg.py` 逐项覆盖。

## 5. 门（跑前，结果见 `out/gate/gates.json`、`out/unit/*.json`；全部通过，`all_pass = true`，`item_errors = []`）

门所用键：G1/G3 = 从 1200 个主键中按 seed 20261018 无放回抽取的 20 个（与 E-3c 的 `gate_keys` 相同；它们是主键，因为 G1 要与 E-3 行比对），G2 的 v≡0 重跑取其中每隔 3 个的 7 个；冒烟 = 帧 8500..8507，不与任何主键重叠。
- **G1 复现 E-3**（20 键）：第 1 级原子、第 1 轮 decoded sha、第 2 级候选集大小，以及 D-sbl / C-sbl 对 E-3 L-diag / L-cov 的 decoded sha、被选原子（时延、Doppler、|μ|²）、info_errors、FER、NMSE（浮点逐位相等）、同时延对数、原子数、SBL 迭代数 / 收敛标志 / β / n_final，20/20 全部逐位一致。
- **G2**：(a) v ≡ 0（在第 1 轮 moments 之后令 v := 0，对 7 个键重跑整条流水线）时 Z-sbl = D-sbl = C-sbl（原子、增益哈希、decoded sha、NMSE、info_errors、SBL 记录）逐位一致，Z-ls0 = D-ls0 = C-ls0 一致，Γ 全零，7/7 全部检查通过；(b) LS0 解与独立 numpy 求解的相对误差：27 次门运行 × 3 个 LS0 臂 = 81 个解，最大 6.2e-12（≤ 1e-10），其中最差 cond(Q) = 3.3e4。
- **G3 确定性**：20 个键各整条流水线重算一次，去掉计时字段后逐位一致 20/20。
- **G4 成本**：见 §6，估计 3.62 core-h ≤ 6。
- **单元**：`test_gso.py`（键集 = E-3c、分片划分、LS0 = 独立 numpy 解且 v=0 时核的 gamma 全零、Γ_var 三种取法在零方差时 SBL 逐位相同而非零时互不相同、`gamma_full` 对角 = Σv、E-3 复现比较对每个字段敏感）14 个测试与 `test_gso_agg.py`（判定的三个分支与全部边界、精确 McNemar、簇 = 帧而非行、行序不变、完整性阻断十余项）31 个测试全部通过。门 / 冒烟 / 单元三处源快照一致（`gates.json` 的 `sources_identical = true`，快照写入 `gates.json` 的 `sources_sha256`），主跑聚合再核对一次。

## 6. 冒烟（8 键，帧 8500..8507，U/G 交替、SNR 6..11 dB 循环，8 进程并发；`out/smoke/smoke_counts.json`；**只是冒烟，不并入任何分析**；以下是计数，不作解读）

0 error 行，0 次 Cholesky jitter；第 2 级候选集平均 620.6 个原子；每键秒数 6.3–9.7（均值 8.35）；共用阶段合计约 .85 s（第 1 级筛选 .24 / 第 1 级 SBL .31 / 第 1 轮检测 + 译码 .05 / 第 2 级筛选 .25），每次第 2 级 SBL 约 2.3–2.4 s（3 次），LS0 求解约 2 ms，每臂第 2 轮检测 + 译码约 .05 s。平均输出原子数（D 22.5 / C 21.9 / Z 22.1）；同时延对数合计（D 209 / C 41 / Z 42）；撞迭代上限的键数（D 4 / C 8 / Z 7，共 8 键）；信息比特零错误的帧数（D-sbl 7 / C-sbl 6 / C-ls0 5 / D-ls0 7 / Z-sbl 6 / Z-ls0 4，共 8 帧，未分析）；LS0 对 numpy 最大相对误差 1.8e-12。

## 7. 成本

实测每键 8.35 s（冒烟 8 进程并发，deinlab 近空闲）。1200 键 = **2.78 core-h**；按 E-3c 的竞争因子 1.3 计 **3.62 core-h ≤ 6 core-h**（G4 通过）。门 + 冒烟 + 单元的工程成本另计，合计 0.126 core-h（`gates.json: engineering_core_hours`，不计入 6 core-h 止损，需要时可在启动前用 `COST_CAP_H` 扣除）。链内置成本止损：所有分片已提交的成本之和 ≥ `COST_CAP_H`（默认 6）核时不再开新键（最多再超出已在跑的 ≤ 16 个键，约 0.04 core-h），写 `COST_STOP`，链结束时写 "GSO CHAIN STOPPED"，此时聚合因行集不全而 `interpretable = false`。

## 8. 运行手册

`launch_gso.sh`（tmux 会话名 `g_gso`，仅 CPU，单线程进程，进程数 ≤ 16，启动前检查 load 以保留 ≥ 16 核空闲）：`MODE=gate`（单元 + G1–G3 + 冒烟 + G4 合并 → `out/unit`、`out/gate/gates.json`、`out/smoke/smoke_counts.json`；已执行）、`MODE=chain`（无人值守：校验 `CODE_MD5.txt` 与 `gates.json` → 16 个分片并行跑 1200 键 → `gso_agg.py --gates` → 行文件 gzip + md5 清单 `REMOTE_ROWS_MD5.txt` → 在 `out/main/STATUS.txt` 追加 `GSO CHAIN DONE <utc> (...)` 或 `GSO CHAIN STOPPED <utc> (原因)`）。输出目录绝不覆盖也不续跑：重跑前把 `out/main` 移走；失败分片原样保留，不重试不换配置；一个键失败即写 error 行并终止该分片。只回传小文件，行数据留 deinlab（gzip + md5）。链的"成本止损 / 聚合拒绝"路径已在沙箱副本上端到端演练（COST_CAP_H=0.002，16 行后止损，聚合正确拒绝，gzip / md5 / STATUS 正常），DONE 路径只由聚合单元测试与门数据上的真实模式读取演练覆盖，未在 1200 键上跑过。
启动命令（编排者执行；先确认远端代码与提交一致，`launch_gso.sh` 会自己做 `md5sum -c CODE_MD5.txt`）：
```
ssh deinlab "cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_gso_20261018 && mkdir -p out/main && tmux new-session -d -s g_gso 'MODE=chain bash launch_gso.sh > out/main/launch_chain.log 2>&1'"
```
默认 `NSHARD=16`、`COST_CAP_H=6`（环境变量前缀加在 `MODE=chain` 前）。

## 9. 与 design.md 的执行期偏差与说明

- **D1 Z 臂的写法**：Γ_var = 0 以 `Gamma=None`（标准 SBL）实现；单元与门已验证它与 `Gamma=0.0` 标量、全零矩阵逐位相同。全部臂的 β₀ 都取 E-3 的 `1/(σ² + mean v)`（"六个臂只在 Γ_var 与增益估计器上不同"），因此 Z 臂的 SBL 初值仍用到第 1 轮 APP 的平均方差；EM 之后 β 由数据学出。
- **D2 共用 SBL**：-sbl / -ls0 臂对共用同一次 SBL（同一支撑），每键 3 次而非 6 次 SBL；各臂记录里的 `seconds.sbl_shared` 是共用那次的时间，聚合只用 `elapsed_seconds` 计成本。
- **D3 对比的 bootstrap**：逐行配对差再重抽样（见 §3），与对臂均值作线性组合代数相等；目的只是让严格不等式不受浮点抵消影响。
- **D4 McNemar**：两个方向都报告并忽略分簇（见 §3），仅为报告项。
- **D5 LS0 校验的阈值**：门 G2 按设计用绝对 1e-10（实测最大 6.2e-12，cond(Q) ≤ 3.3e4）。主跑聚合里把它放宽为 max(1e-10, 64·ε·cond(Q))：Cholesky 与 LU 求解之差的量级本来随 cond(Q) 增长，纯 1e-10 在病态键上可能误阻断整个 6 core-h 的结果；错误的解（误差远大于舍入）仍被阻断（单元测试覆盖）。每键的实测误差与 cond(Q) 都记在行里并在摘要中报告最大值。
- **D6 G4 的口径**：估计 = 冒烟 8 键的平均每键耗时 × 1200 × 1.3（E-3c 的竞争因子），≤ 6 core-h 为通过；成本止损只作用于主跑，工程成本（0.126 core-h）另列。
- **D7 门键是主键**：G1 需要与 E-3 行比对，门键必为主键（与 E-3c 相同的 20 个）；这 20 个键的六臂结果因此存在于 deinlab 的 `out/gate/rows_shard*.jsonl`，门流程不读取其 FER。开发期间我另做过一次读取真实门行的聚合 schema 核对（20 键、17 个簇），其 stdout 含这 20 个键的各臂 FER 与一个无统计意义的判定标签；这些数字没有写入任何文件或报告，也没有用于任何设计决定，不构成判据的一部分，但属实应予披露。门行不应入库。
- **D8 冒烟用 8 键**：帧 8500..8507（派发要求"约 8 键、帧 8500+"）；冒烟只用于工程检查与成本，不并入任何分析。
- **D9 分片**：键 i 归分片 i mod 16（交错），16 个进程；无续跑。

## 10. 局限

仅 on-grid 第 2 级 SBL（不做连续细化），仅 U/G × ρ .3 × 6..11 dB × 100 帧，仅 SBL 一个估计器族；"支撑选择"与"增益估计"的分离是对 SBL 输出的事后重估，LS0 的 ridge 取 σ²（噪声方差），不是 SBL 学出的 1/β。结果只出 draft 卡，是干预结果的描述，不证明机制；MIXED 不等于"两者皆非"。
