# FROZEN 2026-11-21 — Stein 闭合估噪的端到端检验（Eric "冻结端到端检验"，Claude 代办冻结）

任务：`.trellis/tasks/11-21-stein-sigma2-e2e`。起因：外部候选三的公式在存档触发帧上合并判据成立，但偏差随 SNR 从 0.78 升到 2.66（[零成本读数](../stein_sigma2_readout_20261120/READOUT.md)）。偏差能否转成误帧率，只有端到端能回答。

## 设计（只改一处）
- 完全沿用 [sigma2_dd 协议](../sigma2_dd_20261118/PROTOCOL.md)：G 场景、ρ = .3、P = cap = 8、帧 11000–11999、4.5–8.0 dB 每 0.5 dB，同一观测、噪声与 LDPC 消息；第 1 轮用 SF 初值 s0，第 1 次 LDPC 后做**一次**噪声更新，用于第 2 轮 CE、检测、A1c（含 ridge）和 A3 的两轮。
- 唯一改动：更新值由 `raw = r − ν` 换成外部公式 σ̂² = [r + sqrt(max(0, r² + 4ν(r − ν)))]/2，r、ν 与 DD 同一计算（`dd_estimator.estimate_dd` 的 residual_power、uncertainty_power），下限 .001 不变。实现：`stein.py` 只替换 `native_dd.estimate_dd` 这一个名字。
- 只新跑 Stein 一臂（B_Stein + A3_Stein，8,000 键）；known / SF / DD 三臂用存档 `sigma2_dd_20261118/out/main_20261118` 的同键结果配对。

## 门槛（已在冻结前通过，`out/gate.json`）
- G-A：未替换的 DD 在帧 11000–11001 全部 8 个 SNR 上逐键复现存档 DD 行（B 字典 JSON 完全相同）：16/16。
- G-B：替换后的 Stein 臂保留存档 DD 行的第 1 轮几何、r、ν 与 s0，且估计值等于公式作用于存档 r、ν：16/16。
- 成本：每键 CPU 时间外推 8,000 键加 30% 余量为 1.29 核时；上限 2 核时，预算停止。

## 判读（冻结，不改标签；交叉点、自助法沿用 sigma2_dd：slot-mismatch 对数插值，20,000 次配对帧自助，种子 20261019，删失端保留）
- **P1** Δ_S = crossing(B_Stein) − crossing(B_known) 的 95% 区间：在 [−.25, +.25] 内 → ROBUST；下界 > +.25 → DEGRADED；否则 INCONCLUSIVE。
- **P2**（对最简单可用替代）G_SF = crossing(B_SF) − crossing(B_Stein)：下界 > 0 → BETTER；上界 ≤ 0 → NOT_BETTER；否则 INCONCLUSIVE。
- 次要（只报告）：G_DD = crossing(B_DD) − crossing(B_Stein)，以及是否收回 DD 损失（1.64 dB）的一半以上（下界 > .82）；四条 A3 交叉；逐 SNR 的 σ̂²/σ²；第 1 轮 r、ν 与存档 DD 不一致的键数（应为 0）。

## 竞争假设
| 假设 | 预言 |
|---|---|
| H-good：Stein 修正了软符号吃噪声，校准足够 | P1 ROBUST，P2 BETTER |
| H-partial：低 SNR 校准、高 SNR 高估，高估只让 LLR 偏保守 | P1 DEGRADED 或 INCONCLUSIVE，P2 BETTER，G_DD > 0 |
| H-none：交叉点附近（5–7 dB）高估 1.3–1.9 倍抵消了收益 | P2 NOT_BETTER 或 INCONCLUSIVE |

## Premortem
最可能与预期相反的原因：交叉点落在 6–7 dB，正是 Stein 高估 1.3–1.9 倍的区间；而 SF 本身不差（交叉 6.38 dB）。设计无法排除这一点，读数会直接显示。

## 事先预测（Claude）
P1：ROBUST .10，DEGRADED .60，INCONCLUSIVE .30。P2：BETTER .45，NOT_BETTER .15，INCONCLUSIVE .40。

## 运行
deinlab 项目树内运行 `run_stein.py`（单线程 BLAS、隐藏 CUDA、最多 16 进程、预留 16 核），一次无人值守，结尾写 DONE/STOPPED。行文件留在服务器，结果 JSON 与 MD5 清单回传 `out/main/`。
