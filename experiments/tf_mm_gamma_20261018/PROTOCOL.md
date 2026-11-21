# 模型匹配合成检查协议（冻结稿）：完整 Γ 在模型正确时是否不劣于标量

任务 `.trellis/tasks/10-18-model-matched-gamma/`。本文件 = `design.md`（具有约束力）并入执行期事实与偏差；两者冲突处以本文件为准，偏差全部列在 §10。
冻结（永不修改）：E-3 全部代码 `experiments/tf_e3_sbl_20261017/`（本任务只读导入，不复制；md5 见 `SOURCE_MD5.txt`，运行时由 `mm_driver.check_e3_code_md5` 复核）及其下游冻结核（`tf_e3_sbl_20261017/SOURCE_MD5.txt` 的 22 个文件，运行时由 `e3_driver.check_frozen_md5` 复核，两张表都写入每个 `config_shard*.json`）。新代码只在本目录。与 Codex 的 E-3c 并行，不触碰其任何文件。
前置：res-20261017-03（E-3：数据辅助 SBL 中完整 Γ 的 FER 与 NMSE 都不如标量 Γ）。

## 1. 问题

E-3 的反转有两种解释：(i) 代码或用法问题（Γ 在 SBL 中的用法、β 更新、ARD 与 EIV 罚项的交互；此前只在 v ≡ 0 时验证过）；(ii) 模型误设（真实 APP 后验不是 EIV 模型假设的样子）。本检查造一个**数据不确定性模型匹配**的世界：数据按第 1 轮译码 APP 的逐符号后验抽样，于是 EIV 模型对数据这一维是精确的。在这个世界里完整 Γ 不应劣于标量 Γ；若仍劣于，则指向 (i)。结论限于"在模型匹配世界中"，只出 draft 卡。

## 2. 管线、合成观测与约定核对

**键**：U/G × ρ = .3 × {6, 7, 8} dB × 帧 4000..4049，共 300 个（`mm_driver.main_keys`，帧优先排序，因此成本止损后留下的是整帧）。与 E-3 主跑的键重叠；本检查的结局是合成 NMSE，不是 E-3 的结局。

**共享管线**（`mm_driver.prepare_key`，E-3 `process_key` 到第 2 级候选集为止的逐字算术，帧生成/观测构造/检测/译码/SBL/筛选/输出选择全部调用冻结的 E-3 函数）：P1 帧 → 第 1 级导频 SBL（`sbl.sbl_em`，Γ = 0）→ 第 1 轮检测（`scalar_joint`，固定增益，prior 0）+ LDPC → `μ_d, v = moments(clip(raw_app, ±20), pd)`，`pd = 1 − system.rho = .5` → 第 2 级候选集 = 软均值字典 B(pilot + μ_d) 的前 256 个原子 ∪ 第 1 级所选时延的整行 Doppler。候选集在**真实**观测 Y 上算出，并由真实观测变体与全部合成变体共用（§10 D1）。本检查不跑第 2 轮检测/译码（读数是信道 NMSE、同时延普查、EIV 下界，没有 FER）。

**后验抽样约定（已逐项核对，gate G1 + 单元 U1）**
- `messages.alphabet(pd)` = a·[1+j, 1−j, −1+j, −1−j]，比特对 (0,0),(0,1),(1,0),(1,1)，`a = sqrt(pd/2)`；内部约定下 pd = .5，a = .5（QPSK 点 ±.5 ± .5j，`obs['sigma2']` 已折算到该约定）。
- LLR 向量按"先全部 I 比特、再全部 Q 比特"分组；**L > 0 表示该比特为 0**；比特 0 对应实部（虚部）取 +。`logprior` 里四点后验是两个独立比特的乘积，P(bit = 0) = σ(L) = 1/(1 + e^(−L))。
- `moments`：μ = p·a；v = max(pd − |μ|², 0)，即 Var(Re) + Var(Im) 的总复方差。E-3 先把 `raw_app` 截到 ±20 再调用 `moments`，抽样用同一个截后的 L。
- 抽样器 `mm_lib.sample_qpsk`：Re x̃ = +a 的概率为 σ(L_I)，否则 −a；Im x̃ = +a 的概率为 σ(L_Q)，否则 −a。精确均值 a(tanh(L_I/2) + j tanh(L_Q/2))，精确总方差 a²[(1 − tanh²(L_I/2)) + (1 − tanh²(L_Q/2))] = pd − |μ|²，与 `moments` 的 μ、v 一致到 1e-15（U1：三类 L 向量，含截断的 ±20 与全零）；两比特乘积概率表与 `exp(logprior)` 一致到 1.9e-15。
- 经验核对（G1，真实第 1 轮 APP，6 个键 × 2000 次抽样，全帧合并）：见 §6。符号约定的独立检查：hard(μ) 与真数据在 ≥ 62.4% 的符号上一致（随机猜测为 25%）。
- 真径响应：`Y_syn = sbl.columns(daft(pilot + x̃, inverse), l_i, k_real) @ g_i + n`，与 E-3 约定检查（`dictionary_convention_check`）同一构造；把 x̃ 换成真数据且不加噪声时与 `daft(noiseless/scale, inverse)` 的相对误差 7.2e-16（G1 内逐键核对）。
- 噪声：n ~ CN(0, `obs['sigma2']`) 直接在变换域生成（`daft` 是酉变换，白噪声方差不变；E-3 约定检查已证实 Y − Y0 为变换后的噪声）。
- 种子：`np.random.SeedSequence([20261018, scen(U=0,G=1), rho_permille, snr_centi_db, frame, r])`，r = 0..R−1。每次抽样先取 2n 个均匀数（x̃ 实、虚部），再取 2n 个标准正态（噪声）。抽样流与要跑哪些变体无关。R = 3。

## 3. EIV EM 下界（单调性读数）

模型 y = B(x)h + n，h ~ CN(0, Λ)，Λ = diag(γ)，n ~ CN(0, β⁻¹I)，x 独立取自译码 APP（逐符号）。B(x) 对 x 线性；B̄ = E B(x)，Γ = E[(B(x) − B̄)ᴴ(B(x) − B̄)]，G̃ = B̄ᴴB̄ + Γ = E[B(x)ᴴB(x)]。

E 步只对 h 求后验，对 x 取期望（x 的分布固定为 APP，不更新）。对任意 q(h)，取 q(h,x) = q(h)·q₀(x)：

  log p(y; β,γ) ≥ F(q; β,γ) := E_{q(h)q₀(x)}[log p(y|h,x) + log p(h; γ)] + H(q)  （x 的两项 E log q₀ − E log q₀ 相消）。

因 E_x‖y − B(x)h‖² = ‖y − B̄h‖² + hᴴΓh，对 q = CN(m, S)：E‖y − B(x)h‖² = ‖y − B̄m‖² + mᴴΓm + tr(G̃S)。F 对 q 的最大点是 q* = CN(μ, Σ)，Σ = (βG̃ + Λ⁻¹)⁻¹，μ = βΣB̄ᴴy；F 对 (β, γ) 的最大点是 γ_k = |μ_k|² + Σ_kk，β⁻¹ = [‖y − B̄μ‖² + μᴴΓμ + tr(G̃Σ)]/N。这正是 `sbl_rx.sbl_em` 的 E 步与 M 步，所以它是 F 的坐标上升。

记 A = βG̃ + Λ⁻¹，b = B̄ᴴy。把 q 取在 E 步最优点得到 profile 下界（高斯积分闭式）：

  **L(β, γ) = N log β − log det Λ − log det A − β‖y‖² + β² bᴴ A⁻¹ b**  （= max_q F + N log π）。

- Γ = 0（v ≡ 0）时 L = −log det C − yᴴC⁻¹y，C = β⁻¹I + B̄ΛB̄ᴴ（矩阵行列式引理 + Woodbury），即设计中的 L(β, γ)，等于标准 SBL 的边缘对数似然（差常数 N log π）。
- Γ ≠ 0 时 L − N log π 是 EIV 模型的边缘 log E_x p(y|x) 的下界（Jensen；U6 用精确枚举核对），并且 EM 迭代下 L(θ_{t+1}) ≥ F(q_t; θ_{t+1}) ≥ F(q_t; θ_t) = L(θ_t)：**每次 EM 迭代后 L 不降**。剪枝原子（γ_k < 1e-6·max γ）会改变模型，跨剪枝的那一步不在定理之内。
- 求值（`mm_lib.sbl_em_traced`）：E 步已有的 Cholesky 因子给 log det A = 2Σ log diag(Lchol)；β² bᴴA⁻¹b = β·Re(bᴴμ)（μ = βA⁻¹b）。每次 E 步（使用当步的 β, γ）求一次，最终参数再求一次，共 iterations + 1 个点。
- 读数：一次 SBL 运行的违规数 = 满足 L_{t+1} < L_t − 1e-9·max(1, |L_t|) 的相邻点对个数（冻结容差；跨剪枝的点对排除并另计 `n_prune_events`）；另记最大相对降幅 `max_rel_drop`。**真实键上出现违规是发现，不修。** 该读数不参与判据。

数值核对（`test_mm.py`，结果 `out/unit/test_mm.json`；全部通过）：
- U2 v ≡ 0 等于标准 SBL：随机 (β, γ) 上与 −log det C − yᴴC⁻¹y（N×N 直接求）相对差 ≤ 4.2e-15；沿 EM 迭代 ≤ 1.8e-15；`sbl_em_traced` 终点 ≤ 2.8e-16。真实键上（G2，v ≡ 0，真实/合成各一次）终点与标准边缘似然 ≤ 4.9e-15。
- U3 `sbl_em_traced` 与冻结 `sbl_rx.sbl_em` 逐位一致（idx、μ、γ、β、迭代数、收敛标志、n_final、jitter；Γ = None / 标量 / 矩阵三种）；其 trace 与教科书（显式逆）EM 迭代点上的 L 相对差 5.9e-15。
- U4 单调：6 个合成问题（n = 96，m = 60，Γ ≠ 0 的随机半正定，噪声 .05 到 1.5）× 100 次迭代，教科书 EM 与 `sbl_em_traced` 违规数均为 0。
- U5 负对照：E 步忽略 Γ 但 M 步使用 Γ 的"错误 EM"在 6 个问题中的 2 个出现单调性违规；β 更新漏掉 Γ 项的错误 EM 在这 6 个问题上未出现违规。结论：读数对至少一类错误 EM 是敏感的，并非对一切错误敏感。
- U6 下界性：n = 6, m = 3，4 个二值符号精确枚举 16 个组态的精确边缘 log p(y) 减去 (L − N log π) 在 6 组随机 (β, γ) 上取值 2.77 到 67.1（≥ 0）；Γ = 0 时与精确值相等（1e-9）。

## 4. 变体（只在第 2 级 SBL 的数据模型不同，其余与 E-3 逐位相同）

| 变体 | 观测 | 字典里的数据 | Γ_var | β₀ |
|---|---|---|---|---|
| S-diag（合成） | Y_syn | 软均值 μ_d | Σv·I | 1/(σ² + mean v) |
| S-cov（合成） | Y_syn | 软均值 μ_d | 完整 Γ(v) = `_gamma_cross(C, C, fft(v), c1)` | 1/(σ² + mean v) |
| S-hard（合成） | Y_syn | 硬判决 hard(μ_d) | 0 | 1/(σ² + mean v) |
| S-genie（合成） | Y_syn | 该次抽到的 x̃ | 0 | 1/σ² |
| S-diag / S-cov（真实对照） | 真实 Y | 同上 | 同上 | 同上 |

超参（M = 256、≤ 100 次、1e-4、1e-6、1e-3、24 个输出原子、γ₀ = 1）与 E-3 完全相同；β₀ 的取法沿用 E-3 的 L-hard / L-diag / L-cov / L-genie（设计表对 S-hard、S-genie 的 β₀ 未明写，§10 D2）。真实观测对照即 E-3 的 L-diag / L-cov，必须逐位复现 E-3 行（G3；聚合时对全部 300 个键再核一遍）。

## 5. 读数与冻结判据

**读数**：信道 NMSE（`crb.channel_nmse`，与 E-3 同口径）取 10 log10 得 dB；同时延普查（口径同 E-3，`sbl.codelay_pairs`）；EIV 下界单调性（§3）。
**主量**：D = NMSE_dB(S-cov) − NMSE_dB(S-diag)，在合成观测上，每个键先对 R = 3 次求平均（dB 域，因此等价于逐次差再平均），再对键做配对 cluster bootstrap：cluster = (场景, 帧)，跨 SNR 合并（100 个 cluster），20000 次，seed 20261018，百分位 95% CI；多项式计数重抽样，沿用冻结的 `e1_agg.bootstrap_rates` / `ci`。
**判定**（`mm_agg.verdict`，边界由 `test_mm_agg.py` 覆盖）：
- **CODE-CONSISTENT**：CI_hi(D) ≤ 0。模型正确时完整 Γ 不劣于标量，真实数据中的反转应归因于模型误设，而不是代码。
- **SUSPECT**：CI_lo(D) > .2 dB（严格大于）。模型正确时完整 Γ 仍然更差，说明 SBL 中 Γ 的用法或交互有问题，必须排查。
- **INCONCLUSIVE**：其余情形。凡"CI 含 0"一律附注 "not significant != equivalent"。
**报告项（不进判据）**：真实观测对照 D_real（应 > 0 以复现 E-3 方向；用同一 bootstrap）；S-hard、S-genie 的 NMSE（及相对 S-diag 的差）；同时延普查（含相对 S-genie 的幻影超额）；EIV 下界单调性违规数（真实/合成 × 变体）；按 (场景, SNR) 的 D；真实观测 S-diag/S-cov 与 E-3 行逐位一致的键数；成本。
**聚合拒绝解读**（`interpretable = false`，此时只输出完整性、EIV 表与成本，不输出 D）当：行集 ≠ 冻结的 300 键、有重复/error 行、有 smoke 行、行缺真实变体或缺合成抽样/变体、`diag Γ ≠ Σv`（≥ 1e-10）、或 gates 不全过。

## 6. 门（跑前，结果见 `out/gate/gates.json`、`out/unit/*.json`；全部通过，`all_pass = true`，`item_errors = []`）

门所用的键与主跑键不相交，唯一例外是 G3（只跑真实观测对照，不产生任何合成结局）：G1/G2 用帧 8310..8312 × U/G、6 dB；G4 用帧 8320..8321 × U/G；冒烟用帧 8300..8302。
- **G1 抽样器**（6 个键，每键 2000 次抽样，全帧合并）：x̃ 的经验均值相对误差 ‖x̄ − μ‖/‖μ‖ 最大 1.70%（≤ 2%），经验方差相对误差 |Σvar_emp − Σv|/Σv 最大 .063%（≤ 2%）；μ、v 与抽样器精确矩的最大差 6.7e-16、9.2e-16；样本点到 `alphabet(pd)` 的距离 0；真径响应相对误差 7.2e-16；hard(μ) 与真数据一致率最小 62.4%；mean v ≈ .167–.179，第 1 轮信息比特错误 180–209。注：均值误差的统计期望 sqrt(v̄ /(R(pd − v̄))) = 1.6%（v̄ = .17），实测的 ‖x̄ − μ‖² 与该期望之比为 .94–1.07，即 1.7% 完全是 2000 次抽样的蒙特卡罗噪声；对 v̄ ≳ .22 的帧，任何正确的抽样器在 2000 次下都会超过 2%，本检查最差的 6 dB 键 v̄ ≈ .17，因此该门对主跑键是可通过的但裕度很小。
- **G2 退化**（3 个键）：v ≡ 0（μ_d 保留、v 置 0、x̃ = μ_d）时 Γ 为全零；S-cov 与 S-diag 逐位一致（idx、μ、γ、β、迭代数、选出原子），真实与合成观测均 3/3；S-diag 与冻结 `sbl_rx.sbl_em(Γ=None)`（标准 SBL，即 E-3 的 v ≡ 0 退化）逐位一致，真实/合成均 3/3；`sbl_em_traced` 与冻结 `sbl_em` 在 v > 0 的真实问题上（S-diag、S-cov）逐位一致 3/3。附：v ≡ 0 时 S-genie 的 μ 与 S-diag 相对差 ≤ 5.4e-14（字典列在两条路径上按不同分块生成，故不要求逐位）。
- **G3 复现 E-3**（10 个键 = 冻结键序中每隔 30 个取一个）：第 1 级原子、第 1 轮 decoded sha、第 2 级候选集大小、S-diag 与 S-cov 的输出原子（时延、Doppler、|μ|²）、NMSE、同时延对数、SBL 迭代数/β/收敛标志，与 deinlab 上 E-3 行（`tf_e3_sbl_20261017/out/main/rows_shard*.jsonl.gz`）全部逐位一致，11 项检查每项 10/10。同批真实运行的 EIV 下界：20 次 SBL 运行 0 次违规、0 次剪枝事件。
- **G4 确定性与成本**：4 个键整条流水线（真实 + R = 3 合成 × 4 变体）跑两次，去掉计时字段后逐位一致 4/4。成本估计见 §7（不是通过判据，单独报告）。
- **单元**：`test_mm.py`（U1–U6，§3）与 `test_mm_agg.py`（每个判定分支、完整性阻断、R 平均、cluster 结构、D_real 不进判据、E-3 逐位比较、确定性等 9 个测试）全部通过。

## 7. 成本（上限 3 core-h）与冒烟

每键 14 次 SBL 运行（真实 2 + 合成 3 × 4），每次约 650 维的 100 次 EM 迭代（剪枝阈值从未触发，停止判据多数不满足），其余阶段合计约 1.5 s。实测（单线程进程，deinlab 上同时有他人负载）：

| 条件 | 每次 SBL | 每键 | 300 键 |
|---|---|---|---|
| 冒烟重跑（输出已删除，仅计时），6 进程并发，机器近乎空闲（load ≈ 1） | 2.47 s | 35.8 s | **2.98 core-h** |
| 冒烟 6 个键，6 进程并发，机器 load 15–23 | 2.52 s | 36.6 s | 3.05 core-h |
| 冒烟（同上，首次，load ≈ 28） | 3.12 s | 45.3 s | 3.77 core-h |
| G4，8 进程并发，load ≈ 21 | 3.09 s | 43.0 s | 3.58 core-h |
| G4（首次，load ≈ 27） | 3.29 s | 46.0 s | 3.84 core-h |

**结论：按设计的 R = 3、4 个变体全跑，估计 2.98（机器空闲）到 3.85（他人负载 load ≈ 27）core-h，在典型负载下超过 3 core-h 的上限**（空闲时恰好贴着上限）。链内置成本止损：所有分片已提交的成本之和 ≥ 上限时不再开新键（最多再超出已在跑的 ≤ 8 个键，约 0.08 core-h），写 `COST_STOP`，链结束时写 "MM CHAIN STOPPED"，此时聚合因行集不全而 `interpretable = false`。要在上限内拿到可解读结果，需要编排者在启动前二选一（均不改代码，只改启动环境变量；默认值 = 设计）：
- `COST_CAP_H=4.2`：设计不变，上限放宽到 4.2 core-h（估计的最坏值 3.85 加余量）。
- `AUX_REPS=1`：S-diag、S-cov 仍做全部 R = 3 次抽样（主判据不变，抽样流相同），S-hard、S-genie（只进报告项）只在第 1 次抽样上运行；每键 10 次 SBL，估计 2.2（空闲）–2.9（load ≈ 27）core-h，在 3 core-h 内。这是对设计的偏离，需编排者决定。
此外：并发越少每次 SBL 越快（竞争因子）；`NSHARD` 默认 8（上限 8）。

冒烟（6 个键，帧 8300..8302 × U/G、7 dB，`out/smoke/smoke_counts.json`；**只是冒烟，不并入任何分析**；以下是计数，不作解读）：0 error 行，0 次 Cholesky jitter，max |diag Γ − Σv|/Σv = 1.9e-16；每键秒数 36.6（第 1 级筛选 .27 / 第 1 级 SBL .35 / 第 1 轮检测+译码 .06 / 第 2 级筛选 .29 / Γ .05 / 帧生成 .13 / 每次 SBL 2.52）；第 2 级候选集 633 个原子（平均）；mean v = .130；第 1 轮信息比特错误 126–154；x̃ 相对 μ 的偏离比 Σ|x̃ − μ|²/Σv 平均 1.007；x̃ 与 hard(μ) 不同的符号比例平均 .174；mean n_pair（真实 S-diag/S-cov 31.8/4.8，合成 S-diag/S-cov/S-hard/S-genie 32.4/5.4/8.7/5.2）；平均输出原子数（真实 24.0/23.3，合成 24.0/15.0/21.4/13.8）；撞迭代上限的份额（真实 .5/1.0，合成 .72/1.0/1.0/1.0）；NMSE dB 中位数（真实 S-diag/S-cov −12.7/−11.1；合成 S-diag/S-cov/S-hard/S-genie −14.9/−13.6/−14.1/−21.4）；EIV 违规 0（真实 12 次运行、合成 72 次运行）。

## 8. 运行手册

`launch_mm.sh`（tmux 会话名 `g_mm*`，仅 CPU，单线程进程，进程数 ≤ 8，保留 ≥ 16 核空闲，启动前检查 load）：`MODE=gate`（单元 + G1–G4 → `out/unit`、`out/gate/gates.json`）、`MODE=smoke`（6 个键）、`MODE=chain`（无人值守：run → agg → gzip/md5 → STATUS）。
chain 的前置：`out/gate/gates.json` 存在且 `all_pass = true`（否则 abort）、`out/main/STATUS.txt` 里没有已完成的链（否则 abort）。流程：NSHARD（默认 8）个分片并行跑 300 个键（键 i 归分片 i mod NSHARD）→ `mm_agg.py`（含对 E-3 行的全 300 键逐位复现计数）→ 行文件 gzip + md5 清单（`REMOTE_ROWS_MD5.txt`）→ 在 `out/main/STATUS.txt` 追加 `MM CHAIN DONE <utc>`（300 行、聚合退出码 0、`interpretable = True`）或 `MM CHAIN STOPPED <utc> (原因)`（成本止损、有非零退出、行数 ≠ 300、不可解读）。失败分片原样保留，不重试不换配置；驱动可续跑（`load_done`），但重跑需先把 `out/main` 移走。只回传小文件，行数据留 deinlab（gzip + md5）。
启动命令（编排者执行；默认 = 设计，R = 3、4 个变体、成本上限 3 core-h；`COST_CAP_H` / `AUX_REPS` 见 §7，作为环境变量前缀加在 `MODE=chain` 前）：
```
ssh deinlab "cd /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_mm_gamma_20261018 && mkdir -p out/main && tmux new-session -d -s g_mm 'MODE=chain bash launch_mm.sh > out/main/launch_chain.log 2>&1'"
```
启动前核对远端代码 md5 与提交一致（`CODE_MD5.txt`，`md5sum -c` 即可）。

## 9. 局限

"模型匹配"只覆盖**数据不确定性**这一维：x̃ 取自 APP 的逐符号后验，与 EIV 的期望 Gram 精确匹配；信道仍是真实的 10 径稀疏、分数 Doppler、不在 .25 网格上的信道，不是 CN(0, Λ) 先验，这部分误设靠 S-genie 基线（网格失配）量化，不属于本检查要消除的内容。APP 取自本项目的检测器/译码器第 1 轮（P1 信道、N = 1024、QPSK、本 LDPC 码），6 dB 的第 1 轮译码多数失败（信息比特错误约 180–209）。逐符号独立抽样忽略 APP 在符号间的相关（EIV Γ 也如此假设）。只有一个外部估计器族（SBL）。CODE-CONSISTENT 只说明在这个世界里 Γ 的用法与 EIV 模型相容，不证明真实数据的反转由某个具体的误设机制引起。

## 10. 与 design.md 的执行期偏差与事实

- **D1 候选集**：设计 §1 说候选集由 E-3 管线得到，§3 说筛选"与 E-3 逐位相同"。本实现取前者，并与派发要求"候选集同 E-3"一致：候选集（含其中的"软均值字典前 256 个原子"筛选）在**真实**观测 Y 上算出，合成变体共用；没有在 Y_syn 上重新筛选。这使得真实对照能与 E-3 行逐位对照。
- **D2 β₀**：S-hard 的 β₀ 沿用 E-3 L-hard 的 1/(σ² + mean v)；S-genie 沿用 L-genie 的 1/σ²。设计表未写。
- **D3 不跑第 2 轮检测/译码**：本检查的读数不含 FER。
- **D4 单调性读数的定义**（§3）：下界公式、容差 1e-9、剪枝点对排除，均由执行者在跑前冻结。
- **D5 G1 指标的具体定义**（§2、§6）：均值误差用 ‖x̄ − μ‖/‖μ‖、方差误差用 |Σvar_emp − Σv|/Σv（ddof = 1），都按全帧合并；门键选在 6 dB（v 最大）。
- **D6 G3 键与比较项**：每隔 30 个冻结键取一个；比较项见 §6。聚合时对全部 300 个键再做同样的逐位比较（报告项）。
- **D7 成本**：估计超过 3 core-h 上限（§7），已提供两个启动环境变量（默认 = 设计）供编排者决定；链的成本止损按已提交成本，最多超出在飞的 ≤ 8 个键。
- **D8 gate 的执行兜底**：每个 gate 项出错时记录并让 gate 失败（`item_errors`），不丢分片。首轮 gate 曾因 G2 实现中的一个 `None` 字典 bug（真实观测上误请求 S-genie）使 3 个分片中断，修复后全部重跑；之后又加入真径响应核对与 `AUX_REPS` 选项并整体重跑，下列结果来自最终代码（`own_md5` 见各 config）。
- **D9 smoke**：6 个冒烟键行内 `smoke = true`，聚合会因 smoke 行存在而拒绝解读，不得并入分析；门/冒烟的行数据留 deinlab，只回传 `gates.json`、单元 JSON、`smoke_counts.json`、STATUS 与 md5 清单。
- **D10 launcher 的 chain 模式未真正执行**（按派发要求不跑链）：只做了 `bash -n` 语法检查与以下独立演练。(a) 成本止损：两个分片（smoke 键、上限 5 s）在已提交成本 79 s ≥ 上限后各自停止并写 `COST_STOP`。(b) 链脚本的收尾部分在 deinlab 临时目录（`/data/guoyikun/tmp`，已删除）中演练：把分片启动行换成 `true`，输入为 `test_mm_agg.make_rows` 生成的假行：300 行 → 前置 gate 检查片段通过、agg 运行、gzip/md5、`interpretable=True` → 写 `MM CHAIN DONE`；只有 150 行 → 写 `MM CHAIN STOPPED (... rows=150 ...)`；已有完成标记时再次启动 → abort（退出码 5）。(c) 对 smoke 行的聚合给出"拒绝解读"并产出 EIV/成本表。分片启动行与成本止损的衔接（`--cost-cap-seconds`）只在驱动层面演练过（a）。

## 11. 来源与哈希

只读导入的 E-3 文件 md5：`SOURCE_MD5.txt`。本目录代码 md5：`CODE_MD5.txt`（本文件自身的 md5 由主跑各 config 的 `own_md5` 在开跑时记录）。gate / 冒烟 / 单元的小结果：`out/gate/gates.json`、`out/gate/STATUS.txt`、`out/unit/test_mm.json`、`out/unit/test_mm_agg.json`、`out/smoke/smoke_counts.json`、`out/smoke/STATUS.txt`、`out/smoke/REMOTE_MD5.txt`。

## §11 编排者跑前决定（2026-10-18）
- 成本上限从 3 提高到 4.2 core-h（`COST_CAP_H=4.2`），设计不变（全部 4 个变体 × R=3）。这个上限只是预算护栏，不属于科学参数。
- 诚实声明：冻结前，编排者已看过 6 键 smoke 的计数（`out/smoke/smoke_counts.json`）。这里的决定只涉及成本，不改判据、键集和设计。
- 接受 §10 中的偏差 D1–D10。
