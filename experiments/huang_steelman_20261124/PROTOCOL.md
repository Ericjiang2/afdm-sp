# FROZEN — 预注册协议：已发表的"校验触发 + 数据辅助全局重捕获"对照臂（Huang-2010-style Steelman）

> 状态：**FROZEN**（2026-11-24；由 agy 核对 Huang 2010 原文与冻结代码起草，经 Sol 设计审查 #1 `reviews/sol-review-1-design.md` 后逐条修订定稿；冻结提交后再执行任何评估帧运行）。
> 上游：现稿路线（Eric 11-20）、[res-20261119-06](../../research-assets/res-20261119-06.md)（ρ 扫描，各取最优时 CD 领先 F0 1.14 dB）、[res-20261118-03](../../research-assets/res-20261118-03.md)（Stage 3 CODELAY 与安静单核计时）、[res-20261120-01](../../research-assets/res-20261120-01.md)（$\Gamma=0$ 交换验证）、漏斗前提检查卡 `ideas/cards/I-20261122-l34.md`。
> 授权：Eric 已授权在草案预算（主跑 ≤ 12 核时，计时 ≤ 0.5 核时）内完成冻结与运行；超出预算则停止并汇报。

---

## 冻结前修订（对照 Huang et al., EURASIP JASP 2010 原文、冻结代码与 Sol 审查 #1）

### A. 对照 Huang 2010 原文与冻结代码的修订（R1–R8）

核对原论文全文（J. Huang, J. Huang, C. R. Berger, S. Zhou, and P. Willett, *"Iterative Sparse Channel Estimation and Decoding for Underwater MIMO-OFDM,"* EURASIP J. Adv. Signal Process., vol. 2010, Art. ID 460379, 11 pages, doi:10.1155/2010/460379，实读 Springer 出版 PDF 全文 §§1–7）及本仓库冻结源码与 `rho_sweep_20261119` 归档数据后，对 Claude 草案（`.trellis/tasks/09-22-tf-production-gap-audit/research/huang-steelman-prereg-DRAFT-20261124.md`）作出如下修订：

| 编号 | 修订项 | 草案原写法 | 定稿写法 | 依据与理由 |
|---|---|---|---|---|
| R1 | 原文求解器核实与臂范围 | 称 Huang 2010 用"OMP 或 BP"，论文含义泛指"已发表的全局重捕获" | 明确标注：Huang 2010 §3.1.2 式 (15)–(16) **仅使用复数 Basis Pursuit（BP，$\ell_1$ 正则最小二乘，内点法 [26]）**，原文未出现 OMP（OMP 见其引用的 Berger et al. IEEE TSP 2010 [16] 同字典对比）。本实验将 `HG` 准确命名为**"两遍 Huang-2010-style 全局数据辅助 OMP 重捕获"**，沿用 `pilot_front` 的同一 OMP 求解器（`BaselineInitializer` / `omp_sparse_torch`），所有论文结论严格限定于该两遍全局 OMP 对照，不外推至未测的 BP 或 6/10 遍外环 | 保持单因子控制与门 G2 求解器等价；Huang 2010 未给正则参数 $\lambda$ 的公式或数值，另造 BP 会引入自由调参并破坏与 F0 前端对齐 |
| R2 | 软符号反馈与内部归一化功率 `pd` | 写 `moments(·, 1-ρ)` | 核实 Huang 2010 §3.3–3.4 式 (19)–(22) 与 Figs. 2–10：原文 §3.3 用 **extrinsic** 送检测器（对应 `r1_check`）、用 **APP** 送信道估计器（对应 `r1_app`）；§3.4 对比全硬、门限硬、全软（式 21，$\Gamma_s=0$）与门限软（式 22），Fig. 2–6 与 §6（SPACE08 QPSK）显示软反馈优于硬反馈，且 QPSK 下全软 $\Gamma_s=0$ 与 $\Gamma_s\in\{0.2,0.4\}$ 几乎重合。故保留全软反馈 `pilot + mu`。**代码口径修正**：冻结 `observe()` 已把所有 $\rho$ 的观测与导频除以 $\sqrt{2(1-\rho)}$，使内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`（见 `headroom_ladder_20261008/driver.py:227`、`e1_driver.py:211`、`rho_sweep_20261119/phase1.py:55`）。全部新臂与 G3 统一使用 `pd = 1 - ctx.system.rho`（= 0.5），G3 真数据符号为 `raw['data'] / sqrt(2*(1-rho))` | 避免 $\rho \neq 0.5$ 时产生幅度失配 bug；严格对齐 Huang 2010 §3.3–3.4 与 CD 参考信号 |
| R3 | 噪声项与符号不确定度 $\Gamma(v)$ | 未明确对照原文噪声项 | 核实 Huang 2010 §3.1 式 (12)–(15)：原文把反馈符号视为确定性导频写入传感矩阵 $\mathbf{\Psi}$，稀疏估计目标中**不含符号不确定度协方差 $\Gamma(v)$**（误差并入加性噪声 $\mathbf{n}_\nu$）。`HG` 的全局 OMP 阶段不含 $\Gamma(v)$，忠实于原文；随后的连续精修保留 F0 自己的 `time_refine(..., mode='soft', max_paths=8, rounds=2)`（在 8 条互异时延上解 $(B^HB+\Gamma(v)+\sigma^2 I)h=B^HY$） | OMP 阶段忠实于原文；精修阶段保留 F0 同款 `mode='soft'` 是给 HG 的有意 steelman 适配，防止把对手锁死在离散网格上 |
| R4 | 两遍外环契约、裁剪与早停 | 写"最多 2 遍，校验通过即停"，未细化两遍接线与数值异常 | 核实 Huang 2010 §3.3 在所有 LDPC 校验方程满足（`syndrome == 0`）时早停，原文外环上限为仿真 10 遍 / 海试 6 遍。本实验锁定可执行的两遍契约（见 §1）：第 1 遍接 F0 的 `r1_check` 与 `r1_app`；每遍均把 `scalar_joint` 的 `extrinsic` 经 `np.clip(..., -20, 20)` 送入 `decoder_messages(..., maxiter=50)`；若第 1 遍 `syndrome == 0` 立即早停；否则用第 1 遍译码器的 `raw_check_extrinsic`（±20 裁剪）和 `raw_app`（±20 裁剪算新 `mu, v`）进入第 2 遍。任何数值异常（`LinAlgError`/`FloatingPointError`）显式记录并中止，不静默回退。同时报告第 2 遍的净救回、退化（位错增加）和剩余失败 | 相比 CD 的 1 次分支已是预算内的 steelman 让步；`HG1` 给出严格等总轮次（3 轮）对照；并记录第 2 遍净效应以约束更多遍数空间 |
| R5 | 细字典 OMP 原子预算与 G3 实测诊断 | 草案 §8 建议仅看真值 G3 二选一 {24, 40} | 写死确定性选参规则（只看冒烟帧 G3 与 G4 预算，绝不触碰评估帧或评估 FER）：在真数据 G3（20 帧）与预算门 G4 上同时评估 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。两档均合格时，**仅当 40 比 24 多找回至少 4 条真径**（即 `matched_40 >= matched_24 + 4`，共 160 条）才选 40，否则保留 24；仅一档合格则选该档；均不合格则停。并按 Sol 建议补齐隔离冒烟帧上的**真实触发软反馈诊断**（含 OMP 提名前后/精修前后漏径、`complex64 gels` vs `complex128 gelsd` 数值精度核查与 `Phi_S` 条件数） | 杜绝细字典相干列（相邻 0.25 格相关度约 0.90）导致单精度 `gels` 病态或强径挤占候选列把 HG 做残 |
| R6 | Q2/Q3 的同时配对投影区间构造 | 笼统写"沿用 ρ 扫描 §7 的已测试实现" | 核查 `rho_sweep` P3 发现：其非配对 12 点矩形相减在 `CD` 自身上的最小宽度为 `5.451 − 4.897 = 0.554 dB`，即使 `Z == CD` 也会给出 `[-0.554, +0.554] dB`，使 `[-0.5, +0.5]` 等效判定在数学上不可行；而单纯的逐次抽样 $\min_\rho$ 自助法在最优 $\rho$ 近并列（如归档 CD 在 `.25` 与 `.30` 仅差 0.0566 dB）时存在 Fang & Santos 折角欠覆盖风险。定稿采用**36 对配对差同时置信投影**（见 §3）：基于精确恒等式 $\min_a c_A(a)-\min_b c_B(b)=\min_a\max_b D(a,b)=\max_b\min_a D(a,b)$，在同一套 50,000 次物理帧自助重采样上对全部 36 对配对差 $D(a,b)=c_A(a)-c_B(b)$ 构造同时 $1-\alpha$ 区间 $[L(a,b),U(a,b)]$（Bonferroni $\alpha/36$），再投影得 $[L_{\text{proj}}, U_{\text{proj}}] = [\min_a\max_b L(a,b),\; \max_b\min_a U(a,b)]$。实测在归档 CD 曲线上：`Z==CD` 时精确为 `[0, 0]`，单帧微扰时为 `[0, 0.233]` dB，`F0-CD` 为 `[1.000, 1.865]` dB。逐次抽样配对自助区间作为次要精度读数一并报告 | 既保持跨臂物理帧配对抵消（等效检验可行），又对最优 $\rho$ 并列与截断具备严格同时覆盖保障 |
| R7 | 归档完整核验与未触发键策略 | 草案标注"约 1.8 万，冻结前核实" | 已核验 deinlab 24 个归档分片 MD5 与本地 `REMOTE_ROWS_MD5.txt` 逐字节一致，总计 62,400 键，触发数精确为 **18,009**（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`）；全部 18 个本地与远端冻结源码文件 MD5 一致。主跑前全量校验 62,400 归档键的唯一性、`triggered == bool(syndrome)` 及未触发键上 `CD == F0`；主跑仅在 18,009 个触发键上实时重放 `f0_state` 并逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`/`decoded_sha`/`errors` 与归档逐比特一致；44,391 个未触发键复用归档 `F0`（G1 覆盖全部 6 个 $\rho$ 的未触发复现） | 避免对 44,391 个所有臂均恒等于 F0 的未触发键做无效重算，同时全量锁死归档不变量与触发键逐比特复现 |
| R8 | G1–G4 精确化与分层成本外推 | G4 只抽 4.5–5.0 dB，预算缩减直接删 $\rho$ | G1 扩至 20 键（确定键序，覆盖全部 6 个 $\rho$ 的未触发键 + 4 格触发键的 F0/CD 译码与几何字段）；G2 增加 2,575 列已知分数多普勒信号测试；G3 锁定精确一对一匹配与真实触发软反馈诊断；G4 按归档实际触发结构**分低信噪比（3–4 dB，占 9,175/18,009 = 50.9%）与中高信噪比（≥4.5 dB）两层 × 6 个 $\rho$ 抽样 48 键加权外推**（含所有阶段总 CPU 时间并乘 1.2× 余量），超预算时**优先砍次要粗字典臂 `HGint` 以保全主问题 6 点 $\rho$ 网格** | 堵住低信噪比两遍满跑导致的成本低估缺口；保全主检验 Q2/Q3 的 6 点完整网格 |

### B. Sol 设计审查 #1（`reviews/sol-review-1-design.md`，VERDICT: REVISE）逐条回应

| Sol 意见 | 处置 | 具体修改或反驳理由 |
|---|---|---|
| 1（必改）：论文裁决限于两遍 Huang 式全局 OMP；锁定两遍契约、裁剪、早停与数值失败；明确 `HGint` 为粗字典方案对照 | **采纳** | 见 R1、R4 与 §1、§3；同步修正 §6 H-global 中 $(1-\rho)/\rho$ 为软均值能量与导频能量比的上界 |
| 2（必改）：G3 增加真实触发软反馈切片、精确一对一匹配、提名前后与精修前后诊断、双精度 `gelsd` 对照；锁定 24 vs 40 的 "+4 条真径" 与双门规则 | **采纳** | 见 R5 与 §5（G3a 真数据门 + G3b 真实触发软反馈与单双精度诊断） |
| 3（必改）：(a) Q2/Q3 区间解决最优 $\rho$ 并列折角问题并用合成用例验过；(b) 消除 Q2/Q3 判定表重叠，建议 `CD_AHEAD` 改用 $L>0.5$、`CD_NEEDED` 改用 $L_Z>0.5$ | **部分采纳，局部反驳** | (a) **完全采纳**：升级为 36 对配对差同时置信投影（R6），免疫 Fang & Santos 并列折角并保留配对抵消，并在实施时对全部边界用例做单元测试；(b) **消除重叠完全采纳，但保留 Q2/Q3 原草案的 $L>0$ 方向阈值并并行报告 $L>0.5$**：在 400 帧、98.33% 同时投影区间下，区间半宽约 0.35–0.55 dB（例如 `rho_sweep` P3 真实领先 1.14 dB 时下界仅 0.556 dB），若要求 $L>0.5$ 才判 `CD_AHEAD` 且 $U\le 0.5$ 才判 `CD_SLIGHT`，则像 `[+0.20, +0.90]`（点估计 +0.55 dB，明显优于 0）这样的显著领先会被错误归为 `INCONCLUSIVE`；同理 Q3 中 `[+0.05, +0.80]` 既无法宣称 $\pm 0.5$ 等效又已证实 $L_Z>0$，判 `CD_NEEDED` 忠实于草案。我们用唯一互斥的判定表（§3）彻底消除表格与正文冲突，并在输出中对 Q2/Q3 同时显式报告"是否严格超过 0.5 dB 门槛（$L>0.5$ / $U<-0.5$）"及"是否严格不含 0" |
| 4（必改）：按真实归档字段修订 G1/G2，确定排序，覆盖 6 个 $\rho$ 未触发复现，全量核查归档不变量与逐触发键 F0/输入指纹 | **采纳** | 见 R7、R8 与 §5（G1 20 键 + G2a/G2b + 全量归档与逐键断言） |
| 5（必改）：G4 按场景/$\rho$/SNR 分层加权覆盖 3–4 dB 低信噪比与两遍成本；预算吃紧先砍 `HGint` 保全 6 点网格 | **采纳** | 见 R8 与 §5（G4 分层 48 键，优先砍 `HGint`，若仍超 12 核时再按缩减网格或 `STOPPED_BUDGET` 处理） |
| 6（推荐）：隔离切片加无交换续跑或 BP / 更深外环压力测试 | **暂缓（保留说明）** | 维持 Eric 已批准的草案臂集合与 12 核时预算上限，不扩 scope；无交换续跑已有 E-1 的 `A5` 历史证据，BP 缺少 Huang 2010 原文给定的 $\lambda$ 规则；在局限与读数中明确限定归因与求解器边界 |

---

## 0. 要回答的问题

现稿的主张是：译码失败后，在 F0 的支撑上做**局部、固定预算的交换**（`CODELAY` 分支，最多 2 次编辑），比已发表的数据辅助全局重捕获更有优势。
最可能的审稿攻击是："这就是 Huang 等 2010（EURASIP JASP，doi 10.1155/2010/460379）搬到 AFDM 上。"
F0 本身不做数据辅助重新找径：第 0 轮只用导频找径（`pilot_front`），之后每轮只在固定时延上把多普勒在 $\pm 0.75$ bin 内微调（`twofft.time_refine`）。

本检验在完全相同的评估帧（5400–5799）、相同的触发条件（归档 F0 第 2 轮校验子 `syndrome != 0`）、相同的下游检测器（`scalar_joint`）和译码器（LDPC maxiter 50）、相同的多普勒分辨率（$\Delta k = 0.25$）下回答两个主问题：
1. **局部交换（`CD`）对两遍 Huang-2010-style 全局数据辅助 OMP 重捕获（`HG`）**在 1% FER 穿越点（固定 $\rho=.30$ 与 6 点网格各取最优）及单触发耗时上各差多少；
2. **局部交换中 $\Gamma=0$（`Z`）与 `CODELAY`（`CD`）**在完整 6 点 $\rho$ 网格各取最优穿越点上是否落在 $\pm 0.5\text{ dB}$ 等效带内（回答 kill-argument P1）。

---

## 1. 对照臂（全部共用同一归档 F0 触发门控：`syndrome != 0`）

所有臂均工作在冻结 `observe()` 归一化坐标下，内部数据功率恒为 `pd = 1 - ctx.system.rho = 0.5`，评估臂除已知 `sigma2` 外不使用任何真值。

| 臂 | 支撑更新规则 | 下游链路与停止规则 | 角色 |
|---|---|---|---|
| `F0` | 不更新 | — | 归档行（全部 18,009 触发键实时重放并逐比特断言一致） |
| `CD` | `e1_driver.run_branch(..., cd, ..., 'A1')`（`max_edits=2`、`local_passes=2`、compact、多普勒 $\pm 3$、步长 0.25，闭式 `CODELAY` 核） | `scalar_joint(prior=clip(r1_check,-20,20), pd=0.5, iterations=20, damping=0.3, gain_mode='joint')` → `decoder_messages(code, clip(extrinsic,-20,20), maxiter=50)` | 归档行，不重跑（G1 抽查逐比特复现） |
| **`HG`（主对照，steelman）** | **第 1 遍**：`prior = clip(r1_check, -20, 20)`，`mu, v, _ = moments(clip(r1_app, -20, 20), 0.5)`，参考 `x = obs['pilot'] + mu`；在全局细字典（$l\in\{0,\dots,102\}$，$\nu\in[-3,3]$ 步长 0.25，共 2,575 列）上用 `Channel.regressors(x)` 建 $\mathbf{\Phi}$，调 `BaselineInitializer(recipe, lstsq_driver='gels', dictionary_limit=2575)`（`recipe` 按 G3 规则从 `B0-p2-s0.5` [24] / `B0-p3-s0.5` [40] 锁定，`capacity=40`）全局 OMP 找径（不含 $\Gamma(v)$） | 送入 `time_refine(obs['y'], obs['pilot'], mu, v, delays, dopplers, gains, c1, c2, obs['sigma2'], mode='soft', max_paths=8, rounds=2)` → `scalar_joint(obs['y'], obs['pilot'], c, obs['sigma2'], pd=0.5, prior=prior, iterations=20, damping=0.3, gain_mode='joint')` → `decoder_messages(ctx.code, clip(o['extrinsic'], -20, 20), maxiter=50)`。计算 `syndrome_weight`：若为 0 则早停并输出第 1 遍结果；否则用第 1 遍译码输出更新 `prior = clip(raw_check_extrinsic, -20, 20)`、`mu, v, _ = moments(clip(raw_app, -20, 20), 0.5)` 进入**第 2 遍**，输出第 2 遍结果（**最多 2 遍**） | 两遍 Huang-2010-style 全局 OMP 重捕获 |
| **`Z`（主对照，归因）** | 与 `CD` 相同的交换分支，核替换为 `gamma0_exchange_20261120/paired.py::zero_variance(cd)`（$\Gamma = 0$，同时改变选径与增益拟合） | 与 `CD` 相同 | 检验 $\Gamma=0$ 与 `CODELAY` 端到端穿越点是否等效 |
| `HG1`（次要，零额外算力） | 同 `HG`，仅取第 1 遍输出 | 同 `HG` 第 1 遍 | 拆分"多给第 2 遍"与"全局 vs 局部"（与 CD 严格同为 3 轮） |
| `HGint`（次要，粗字典方案对照） | 同 `HG`（最多 2 遍，校验早停），但全局字典改用 `pilot_front` 原样整数多普勒（$l\in\{0,\dots,102\}, \nu\in\{-2,-1,0,1,2\}$，515 列，`B0-p2-s0.5` 固定 24 原子） | 同 `HG` | 原 `pilot_front` 粗字典方案对照（同时差多普勒范围 $\pm 2$ vs $\pm 3$ 与步长，不作纯步长单因子解释） |

- **数值异常处理**：任何新运行臂（`HG`、`HG1`、`HGint`、`Z` 及 G1/计时面板实时 `CD`）出现 `LinAlgError`、`FloatingPointError`、非有限消息或冻结几何内核 `numerical_fallback=True` 均显式报错中止，绝不静默回退。注：归档 `rho_sweep_20261119` 行未单列保存 `CD` 的 `numerical_fallback` 布尔字段（属上游归档固有格式），G1 与 100 键计时面板的实时 `CD` 均强制断言 `numerical_fallback=False`。
- **未触发键**：当归档 `F0` 的 `syndrome == 0` 时，所有臂等于归档 `F0`。
- **路径预算**：`HG`/`HG1`/`HGint` 经 `time_refine(..., max_paths=8)` 保留 8 条互异时延路径，`CD`/`Z` 保留 8 个槽位，均等于真实 $P=8$。

---

## 2. 帧、工况与归档配对

- **评估帧**：`rho_sweep_20261119` 已归档的帧 **5400–5799**（400 个物理帧）；场景 `U`、`G`；$\rho \in \{0.15, 0.20, 0.25, 0.30, 0.40, 0.50\}$；SNR 13 点：`{3.0, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0}` dB（共 62,400 键）。
- **归档来源与全量不变量**：deinlab `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/main_20261119/rows_shard000..023.jsonl`（24 文件 MD5 已核对与本地 `REMOTE_ROWS_MD5.txt` 一致）。启动主跑前程序全量核验：62,400 唯一键齐全；每行 `triggered == bool(syndrome)`；全部 44,391 个未触发键上 `arms['CD']['errors'] == arms['F0']['errors']` 且 `decoded_sha` 一致；全部 18,009 个触发键（$\rho=.15/.20/.25/.30/.40/.50$ 依次 `3648 / 2617 / 2308 / 2360 / 3019 / 4057`，其中 3–4 dB 共 9,175 键）实时重放 `f0_state` 时逐键断言输入指纹（`y, pilot, info, coded, noise, data`）及 F0 `syndrome`、`decoded_sha`、`errors` 与归档逐比特一致。
- **盲态与隔离**：G2/G3/G4 仅使用隔离冒烟帧 **5800–5839**，不触碰任何评估帧。

---

## 3. 主判据与统计规则

- **统计单元与自助法**：物理帧簇（400 簇）；单套共享多项式权重贯穿所有场景、$\rho$、SNR 与臂；`BOOT_DRAWS = 50,000`，`BOOT_SEED = 20261124`。
- **穿越点与截断传播**：沿用 `p1_agg.crossing`（1% FER 首个 $\le 10^{-2}$ 相邻段对数线性插值，零 FER 下限 `0.5/400`）与 `rho_sweep_20261119/analysis.py` 的 `Bounds(lower, upper)` 截断传播：左截断 $(-\infty, L_0]$、右截断 $[H_0, +\infty)$；场景均值 `_mean` 对上下端分别平均；差 `_difference(A, B)` 取 `(A.lower - B.upper, A.upper - B.lower)`（保证永不出现 `inf - inf` 或 `NaN`）。
- **多重比较校正**：三项主检验（Q1、Q2、Q3），Bonferroni 族错误率 $\alpha_{\text{fam}} = 0.05$，每项水平 $\alpha = 0.05/3$（**98.33% 置信区间**）。两场景（U、G）取算术平均。
- **Q1 区间构造（固定 $\rho=.30$）**：对单对配对差 $D_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$ 取最近秩百分位 $\alpha/2$（下界）与 $1-\alpha/2$（上界）。
- **Q2 与 Q3 区间构造（36 对配对差同时置信投影，免疫最优 $\rho$ 并列折角）**：
  对任意两臂 $(A, B)$ 在 6 点 $\rho$ 网格 $\mathcal{R}$ 上的最优穿越点差 $\Delta_{\mathrm{best}}(A,B) = \min_{a\in\mathcal{R}} c_A(a) - \min_{b\in\mathcal{R}} c_B(b)$，利用精确恒等式：
  $$\min_{a\in\mathcal{R}} c_A(a) - \min_{b\in\mathcal{R}} c_B(b) = \min_{a\in\mathcal{R}} \max_{b\in\mathcal{R}} \big(c_A(a) - c_B(b)\big) = \max_{b\in\mathcal{R}} \min_{a\in\mathcal{R}} \big(c_A(a) - c_B(b)\big)$$
  在同一套 50,000 次自助重采样上，对全部 $|\mathcal{R}|^2 = 36$ 对配对差 $D(a,b) = c_A(a) - c_B(b)$ 各自取 Bonferroni 水平 $\alpha_{\text{pair}} = \alpha / |\mathcal{R}|^2$ 的最近秩双侧区间 $[L(a,b), U(a,b)]$（当 $|\mathcal{R}|=6$ 时单侧尾秩 $\lceil 50000 \times 0.05 / (3 \times 72)\rceil = 12$），投影得到：
  $$L_{\mathrm{proj}} = \min_{a\in\mathcal{R}} \max_{b\in\mathcal{R}} L(a,b), \qquad U_{\mathrm{proj}} = \max_{b\in\mathcal{R}} \min_{a\in\mathcal{R}} U(a,b)$$
  当全部 $|\mathcal{R}|^2$ 对配对区间同时覆盖真实配对差（概率 $\ge 1-\alpha$）时，$L_{\mathrm{proj}} \le \Delta_{\mathrm{best}} \le U_{\mathrm{proj}}$ 必然成立；且当两臂逐帧相等、所有在尾部抽样中未被其他 $\rho$ 严格支配的 $\rho$ 均无截断时（例如所有 $\rho$ 尾部均无截断，或出现截断的劣质 $\rho$ 在全部尾部抽样上均严格劣于某一无截断 $\rho$），对角项 $L(r,r)=U(r,r)=0$ 保证投影区间精确坍缩为 `[0, 0]`；若存在未受严格支配的尾部截断，保守区间运算如实给出更宽或 `[-\infty, +\infty]` 区间。点估计区间 $[l_0, h_0]$ 由全样本上的 $\min_a c_A(a) - \min_b c_B(b)$ 经 `_difference(_minimum, _minimum)` 给出。同时把逐次抽样配对自助区间 `[q_{α/2}, q_{1-α/2}]` 记作次要精度读数，并在实现前用单元测试覆盖有限、单/双侧截断、最优 $\rho$ 并列、首穿反弹、两臂完全相同及恰好落于 $0 / \pm 0.5$ dB 的边界用例。

### 三项主检验（正值表示 CD 所需 SNR 更低，即 CD 更好）

1. **Q1（固定 $\rho=.30$，一致性读数）**：$\Delta_{30} = c_{\mathrm{HG}}(.30) - c_{\mathrm{CD}}(.30)$，报点估计区间与 98.33% 配对区间，不替代 Q2 裁决。

2. **Q2（主裁决：两遍 Huang 式全局 OMP vs 局部交换 CD）**：$\Delta_{\mathrm{best}} = \min_\rho c_{\mathrm{HG}} - \min_\rho c_{\mathrm{CD}}$，98.33% 同时投影区间 $[L, U]$，点估计 $[l_0, h_0]$。唯一互斥完备判定表（跑后不改名）：

| 判定 | 唯一互斥条件 | 对论文的含义（严格限定于两遍 Huang 式全局 OMP） |
|---|---|---|
| `CD_AHEAD` | $L > 0$ 且 $l_0 \ge 0.5\text{ dB}$ | 局部交换在 1% FER 上明确胜过两遍 Huang 式全局 OMP，且点估计达 $\ge 0.5$ dB 工程档；`HG` 写进主表作基线（同时显式报告 $L > 0.5$ 是否成立） |
| `CD_SLIGHT` | $L > 0$ 且 $l_0 < 0.5\text{ dB}$ | 局部交换在精度上统计领先但点估计 $< 0.5$ dB；论文主打转向耗时与复杂度（见 §4） |
| `HG_AHEAD` | $U < 0$ | 两遍 Huang 式全局 OMP 精度优于 CD（同时报告 $U < -0.5$ 是否成立）；需重估主线定位并结合耗时给出决策边界 |
| `EQUIVALENT` | $L \le 0 \le U$ 且 $L \ge -0.5\text{ dB}$ 且 $U \le +0.5\text{ dB}$ | 精度在 $\pm 0.5$ dB 容差内无显著差异；取舍取决于每次触发耗时 |
| `INCONCLUSIVE` | 其余（即 $L \le 0 \le U$ 且 $L < -0.5$ 或 $U > +0.5$，含截断导致的无界情形） | 如实报告，不追加运行，由 Eric 决策 |

3. **Q3（独立主裁决：$\Gamma=0$ 局部交换 `Z` vs `CD`）**：$\Delta_{\mathrm{best}, Z} = \min_\rho c_Z - \min_\rho c_{\mathrm{CD}}$，98.33% 同时投影区间 $[L_Z, U_Z]$。唯一互斥完备判定表（与 Q1/Q2 独立报告）：

| 判定 | 唯一互斥条件 | 含义 |
|---|---|---|
| `Z_EQUIVALENT` | $L_Z \ge -0.5\text{ dB}$ 且 $U_Z \le +0.5\text{ dB}$ | 在 6 点 $\rho$ 网格各取最优下，`Z` 与 `CD` 的 1% FER 落在 $\pm 0.5$ dB 等效带内，可用更简单的 $\Gamma=0$ 交换分支（同时报告区间是否严格不含 0） |
| `CD_NEEDED` | $L_Z > 0$ 且 $U_Z > 0.5\text{ dB}$ | `CODELAY` 协方差显著优于 `Z` 且越出 0.5 dB 等效带（同时报告 $L_Z > 0.5$ 是否成立） |
| `Z_BETTER` | $U_Z < 0$ 且 $L_Z < -0.5\text{ dB}$ | `Z` 显著优于 `CD` 且越出 $-0.5$ dB 等效带（同时报告 $U_Z < -0.5$ 是否成立） |
| `Z_INCONCLUSIVE` | 其余（含截断导致的无界情形） | 不确定，如实报告 |

*附注*：0.5 dB 约对应 12% 线性信噪比差，是预先接受的工程等效容差。`Z` 将整个重开几何分支的 $v$ 置零（同时改变选径与增益拟合），故 `Z_EQUIVALENT` 仅支持在注册网格上采用 $\Gamma=0$ 交换分支，不单独把全部增益归因于交换结构本身（无交换续跑对照已有 E-1 `A5` 历史证据）。

---

## 4. 次要读数（只报告，不改判定）

1. **配对救回表**：每个 `(scenario, rho, SNR)` 上相对 `F0` 的 `CD_only / HG_only / both / neither`（以及 `Z` vs `CD` 分歧）。
2. **次要臂与遍数拆分**：`HG1` 与 `HGint` 相对 `HG` 和 `CD` 的穿越点与 95% 配对投影区间；`HG` 第 1 遍早停率、第 2 遍净救回/退化（位错增减）/剩余失败数。
3. **分场景与精度对照**：U、G 分别报告 Q1/Q2/Q3 的点估计与 98.33% 区间；同时报告逐次抽样配对自助区间与非配对同时矩形最优 $\rho$ 集合。
4. **安静单核耗时面板（$\le 0.5$ 核时）**：沿用 `stage3/timing.py`（自动选最空闲单核 `os.sched_setaffinity`、轮换臂序、预热帧无关结构、核对每个计时输出与归档/主跑逐比特一致）。样本：归档 $\rho=.30, 5.0$ dB 按帧号升序各取 U 前 50、G 前 50 共 100 个触发键（归档 U=88、G=110）。报告 `CD`、`Z`、`HG`（完整 1–2 遍）、`HG1`（同一次 HG 调用内记录第 1 遍耗时）、`HGint` 的触发分支均值/中位数/p95 及 `HG/CD` 中位配对倍率；同时报告共享 `F0` 耗时及结合触发率的整帧摊销耗时。
5. **支撑恢复诊断**：在全部 18,009 触发键上按统一一对一匹配规则（见 G3）记录 `HG` 第 1 遍 OMP 提名后、第 1 遍 `time_refine` 后、第 2 遍 `time_refine` 后及 `CD`/`Z` 最终 8 径的真径匹配条数与功率占比。

---

## 5. 门禁（任一不过立即停止，报告，不给判定）

- **G1 归档复现（20 键）**：按确定排序 `(scenario, rho_permille, frame, snr_centi_db)` 选键：
  - 触发复现（8 键）：`U/G × ρ ∈ {.30, .50}` 各取前 2 个触发键，逐比特核对输入指纹、`F0` 的 `syndrome`/`decoded_sha`/`errors`、`CD` 的 `decoded_sha`/`errors`/`state.paths`/`decision`。
  - 未触发复现（12 键）：`U/G × 全部 6 个 ρ` 各取前 1 个未触发键，逐比特核对输入指纹及 `F0` 的 `syndrome == 0`/`decoded_sha`/`errors`。
- **G2 实现等价与细字典验证**：
  - **G2a（`pilot_front` 逐列等价）**：在 4 个冒烟键（帧 `5800, 5801`, U/G, $\rho=.30$, 5.0 dB）上，HG 找径器取参考 `obs['pilot']`、整数网格（515 列）、`B0-p2-s0.5`（24 原子），重建 `pilot_front` 的列号 `ids = delays * 5 + (dopplers + 2)`，断言选出列索引序列完全一致、增益最大绝对差 $< 10^{-6}$。
  - **G2b（2,575 列细字典已知信号测试）**：在 $\rho=.30$ 归一化坐标下构造无噪 3 径分数多普勒信号（含 $\nu = \pm 2.75$，超出 $\pm 2$ 范围），验证 `Channel.regressors` 列索引、观测域与归一化，断言 OMP 前 3 步精确找回全部 3 个列号与增益（相对误差 $< 10^{-4}$）。
- **G3 不被做残与数值诊断（仅用冒烟帧 5800–5839，绝不触碰评估帧）**：
  - **精确一对一匹配规则**：对每帧，只在 `l_fit == l_true` 且 $|\hat{\nu}-\nu| \le 0.5$ 的配对中先最大化匹配条数；同一时延有并列时按真径功率 $|g_p|^2$ 降序、$|\hat{\nu}-\nu|$ 升序确定性消歧。功率占比为 $\sum_{p\in\text{matched}}|g_p|^2 / \sum_p |g_p|^2$（帧级均值与总体汇总双报）。
  - **G3a（真数据健全性门与 K 选参）**：帧 `5800–5819`（20 帧，U，$\rho=.30$，10.0 dB），`mu = raw['data']/sqrt(2*(1-rho))`、`v = np.zeros(N)`，跑 HG 第 1 遍（OMP + `time_refine(mode='soft', max_paths=8, rounds=2)`），同时测 `K=24`（`B0-p2-s0.5`）与 `K=40`（`B0-p3-s0.5`）。质量门槛：总匹配条数 $\ge 144/160$（90%）且总体匹配功率占比 $\ge 95\%$；同时报告 OMP 提名后与 `time_refine` 后各自找回率及最差单帧找回条数。选参规则（结合 G4 预算门）：
    1. 若 24 与 40 均通过 G3a 质量门与 G4 预算门（$\le 12$ 核时）：**仅当 `matched_40 >= matched_24 + 4`** 时选 40，否则锁 24；
    2. 若仅一档同时通过 G3a 与 G4：锁该档；
    3. 若两档均不通过：立即停止。
  - **G3b（真实触发软反馈与单双精度数值诊断）**：在隔离冒烟帧 `5800–5839` 上取 U/G × $\rho\in\{0.20, 0.25, 0.30\}$ × 5.0 dB 的实际 F0 触发键（最多取 24 个触发键），跑锁定后的 `HG` 第 1 遍，记录：(i) OMP 提名后与 `time_refine` 后的真径找回率与功率占比；(ii) `Phi_S` 条件数分布；(iii) 同输入下 `complex64 gels` 与 `complex128 gelsd` 的支持集一致率与相对增益差，若 `complex64 gels` 出现非有限数或严重秩亏发散（中位相对增益差 $> 0.1$）则停止并汇报。
- **G4 分层成本门（≤ 12 核时）**：
  - 在冒烟帧 `5800–5839` 上按 **6 个 $\rho$ × 2 个 SNR 层（`low`: 3.0/4.0 dB；`mid`: 4.5/5.0/5.5 dB）** 抽取 **48 个真实 F0 触发键**（每格 4 键，U/G 交替），实测完整单触发键 CPU 时间（含 `inputs/observe`、`f0_state`、`HG` 1–2 遍、`HGint` 1–2 遍、`Z` 及诊断记录），按归档各 $(\rho, \text{SNR 层})$ 的精确触发键数（18,009 总计，其中 3–4 dB 为 9,175 键）加权求和，加上 0.15 核时归档读写与汇总余量后乘 `1.2×` 安全系数。
  - 预算处理顺序：
    1. 若外推 $\le 12$ 核时：保留全部臂与全部 6 个 $\rho$；
    2. 若 $> 12$ 核时：首先去掉次要粗字典臂 `HGint` 重算外推（保全主问题 Q1/Q2/Q3 的 6 点完整网格）；
    3. 若去掉 `HGint` 后仍 $> 12$ 核时：依次去掉 $\rho=.40$、再去掉 $\rho=.15$（此时任何主裁决须显式标为缩减网格口径）；仍超则立即停止并输出 `STOPPED_BUDGET`。

---

## 6. 竞争假设与跑前预测

| 假设 | 内容 | 预言 |
|---|---|---|
| H-local | 失败帧常只漏 1–2 条弱径，其余径已对。HG 用失败帧的低质量软符号从头重估全部径，会连带破坏原本估对的径 | `CD_AHEAD`；HG 在低 SNR 尤其差；`HG1` 与 `HG` 差别小 |
| H-global | 软均值能量相对导频能量之比上界为 $(1-\rho)/\rho$（译码器无信息时为 0），当译码已恢复大部分符号时全局重搜可直接看见弱径且无幻影问题 | `EQUIVALENT` 或 `HG_AHEAD`；HG 的最优 $\rho$ 低于 CD |
| H-grid | 差距主要来自字典粗细/范围，而非局部与全局之别 | `HGint` 明显劣于 `HG`，而 `HG` 与 `CD` 接近 |

### 跑前预测（冻结提交时写定，跑后追加打分进 `research-assets/prediction-ledger.md`）

**Claude（原草案记录，未改）**：
- `HS-C1`（Q2 判定）：`CD_AHEAD` .30 / `CD_SLIGHT` .15 / `EQUIVALENT` .30 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
- `HS-C2`（Q3 判定）：`Z_EQUIVALENT` .65 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .15
- `HS-C3`（计时）：CD 每次触发的中位耗时低于 HG：.75
- `HS-C4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.35

**agy（Gemini 4 Neon，冻结前独立记录）**：
- `HS-G1`（Q2 判定）：`CD_AHEAD` .25 / `CD_SLIGHT` .15 / `EQUIVALENT` .35 / `HG_AHEAD` .15 / `INCONCLUSIVE` .10
- `HS-G2`（Q3 判定）：`Z_EQUIVALENT` .70 / `CD_NEEDED` .15 / `Z_BETTER` .05 / `Z_INCONCLUSIVE` .10
- `HS-G3`（计时）：CD 每次触发的中位耗时低于 HG：.80
- `HS-G4`（最优 $\rho$）：HG 的最优 $\rho$（点估计 argmin）严格低于 CD 的最优 $\rho$：.25

---

## 7. 设计有效性（Research Checkpoint §1）与局限

- **单因子**：`HG`、`HG1`、`Z`、`CD` 共用同一归档 F0 触发、同一全软参考 `pilot + mu`（`pd=0.5`）、同一 0.25 多普勒分辨率、同一 `scalar_joint` 与 LDPC 译码器。`HG1` 隔离遍数；`HGint` 作为原 `pilot_front` 粗字典方案对照；`Z` 隔离重开几何分支置零 $\Gamma=0$。
- **杠杆**：高 $\rho$ 下 CD 已救回 91–93% 触发，区分力集中在低 $\rho$（.15–.25），Q2 覆盖全部 6 点。
- **统计单元与真值隔离**：物理帧（400 簇）；真数据符号仅用于 G3a，真路径仅用于 G3 及事后支撑匹配诊断。
- **已知局限**：(1) `HG` 使用两遍 OMP 而非 Huang 2010 原文的 Basis Pursuit 与 6/10 遍外环；(2) `Z` 同时改变选径与增益拟合，不单独证明"交换架构"相对无交换续跑的归因；(3) 单一码制/调制/帧长（QPSK, LDPC (3,6) $n=2048$, $N=1024$），已知 $\sigma^2$，路径上限 $8=P$，且本评估与门禁帧的 8 条真径时延互异（不覆盖聚簇真双径）。

---

## 8. 预算与 deinlab 执行规范

- **预算硬停**：主跑总 CPU $\le 12$ 核时（按 `workers × wall_limit` 与主进程 `rusage` 双重封顶），安静单核计时 $\le 0.5$ 核时；超限输出 `STOPPED_BUDGET`。
- **deinlab 环境**：仅用个人 conda 环境 `AFDM`（`/home/guoyikun/.conda/envs/AFDM/bin/python`），日志第一行打印 `sys.executable`；`cd /data/guoyikun/tmp`；`TMPDIR=/data/guoyikun/tmp`、`XDG_CACHE_HOME=/data/guoyikun/tmp/.cache`；6 个线程环境变量全设 1、`CUDA_VISIBLE_DEVICES=""`；`tmux` 会话名 `g_huang_steelman`；使用 24 个工作进程（整机 128 核，留足 >100 核余量）；不向 `/tmp` 或 `/home/guoyikun` 写任何文件；运行前脚本内再次校验全部冻结源码 MD5。
- **输出**：`experiments/huang_steelman_20261124/out/` 存放 `gate.json`、`summary.json`（含 `_argv`、`_config`）、`RESULTS.md`、`READOUT.md`、`timing_summary.json`、`REMOTE_ROWS_MD5.txt`；原始 JSONL 留远端。
