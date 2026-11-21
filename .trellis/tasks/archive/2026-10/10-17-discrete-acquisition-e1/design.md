# E-1 技术设计：协方差 × 支撑交换 因子消融

## 1. 问题与假设

问题：CSTATE 的救回收益来自哪里？三个候选机制：
- H-cov：协方差感知的候选打分（Γ 的非对角项，即同时延 Doppler 相干）。
- H-swap：允许支撑交换（max_edits>0）的搜索空间。
- H-round：额外的一轮编码（检测器 + LDPC）本身。

理论桥梁：受限定理（`results/cstate_method_closure_20260928/MANUSCRIPT_THEOREM_TEXT.md`）给出标量闭合精确的充要条件，且等时延 doublet 的最小标量谱误差为 |D_N(Δν)|。若 H-cov 成立，则"定理的非闭合项在真实决策上确实起作用"，这把定理从限制分析升级为接收机行为的预测；若 H-cov 不成立，定理只能停在限制分析。

## 2. 因子与臂

| 臂 | Γ | max_edits | strategy | 说明 |
|---|---|---|---|---|
| A1 | 全量 | 2 | compact | 生产 CSTATE20（复现基线） |
| A2 | 对角 | 2 | compact | 只去掉非对角协方差耦合 |
| A3 | 全量 | 0 | compact | 禁止支撑交换，保留局部 Doppler 细化 |
| A4 | 对角 | 0 | compact | 两个因子同时关 |
| A5 | 不适用 | 不适用 | 无几何更新 | 控制臂：同状态再跑一轮检测 + 译码 |

共享固定量：F0 状态（r1_app/r1_check/r1_delays/r1_dopplers/r1_gains 与 observation）、`scalar_joint(iterations=20, damping=.3, gain_mode='joint')`、LDPC `maxiter=50`、`grid_step=.25`、`local_passes=2`、`local_halfwidth=.75`、`local_max_evals=16`、`duplicate_tolerance=1e-6`、`top_k=20`、`ridge=sigma2`、`max_delay=system.l_max_cap`、doppler 范围 ±3。

## 3. 协方差轴的实现定义

`geometry_reopen.py` 中协方差经 `_gamma_cross(a, b, vf, c1)`（第 51 行）进入 `_system`（第 63 行）的 `Q = B^H B + gamma + ridge*I`（第 68 行），进而决定候选打分与接受（第 185–236 行）。
- 全量模式：`gamma` 保持原实现（含 `dkernel` 非对角项）。
- 对角模式：置零非对角，仅保留 `gamma` 的对角（等价于标量收缩 Γ = tr(V)·I 的决策侧近似）。

实现约束：**不得修改冻结文件**。新建 `experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py`，从冻结文件逐字复制并只加一个 `gamma_mode` 参数与一处分支；协议记录冻结文件 md5。

## 4. 帧集与配对

- 帧：P1 帧（entropy 2261fde3…，domain TCRF），四格（U/G × ρ .3/.5），SNR ∈ {6.5, 7.0, 7.5, 8.0} dB，取 F0 失败帧。
- 配对：与 P1 ledger 的 B/A3 行按 (scenario, rho, snr, frame) 配对；A1 必须逐帧复现 ledger 的 B 决策。
- 条件化声明：本实验只在 F0 失败帧上有统计含义；结论不得直接外推到全帧 FER。

## 5. 读数与统计

主读数：配对净救回 = (A_x 救回数 − A_x 伤害数)，伤害 = F0 成功而臂失败（在本子集中应为 0，需断言）。
次读数：候选排序轨迹（top-20 分数与入选支撑）、支撑变化计数（延迟集合改动次数）、完整单帧成本（沿用 `run_validation` 的 exclusive-stage 记账）。
统计：帧 bootstrap 20000 次给净救回与成本差的 95% CI；A1 vs A2、A1 vs A3、A1 vs A5 的配对 McNemar（精确，单侧按预注册方向）；格内 Holm 校正。

## 6. 判据（跑前冻结）

- J1（机制）：若 A1 显著优于 A2 且 A2 显著优于 A5，则"协方差感知的支撑决策"成立，且不是额外轮效应。
- J2（搜索）：若 A2 ≈ A1（CI 含 0）且两者都优于 A5，则机制是支撑搜索，协方差无独立作用。
- J3（额外轮）：若 A5 ≈ A1（CI 含 0），则收益主要是额外编码轮，CSTATE 叙事降为救援调度。
- KILL：若 A1 相对 A5 的净救回 CI 含 0，则本实验不支持任何机制主张，CSTATE 在论文中只作为工程救援出现。

## 7. 门

- G1 复现：变体在 `gamma_mode='full'` 下与冻结原版在 ≥64 帧（含触发与未触发）逐位一致（结果字典深度相等）。
- G2 变异：`gamma_mode='diag'` 时断言非对角项为 0 且对角保留；在 ≥8 帧上确认结果与 full 不同（否则该臂无意义，停止）。
- G3 确定性：同输入两次运行逐位一致。
- G4 状态一致：F0 状态与 P1 ledger 的 B 臂触发集合逐帧一致（复用 gs_cstate 的 A1-G2 模式）。

## 8. 成本

F0 状态捕获 + 5 臂 × 触发帧。触发帧估计 2000–8000（四格 × 四 SNR 点）。单臂单帧 ≈ 0.1–0.3 s。预计 4–10 core-hours，上限 16。

## 9. 局限与回滚

局限：单接收机族、单码、N=1024、genie 时延、F0 失败子集；A3/A4 的"禁交换"仍保留局部 Doppler 细化，故 J2/J3 的解释限于此定义。
回滚：删除新目录与任务产物即可，冻结文件未动；任何失败运行保留原样并记录原因。
