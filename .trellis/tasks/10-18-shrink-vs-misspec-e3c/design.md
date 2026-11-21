# E-3c 技术设计

修订 A1（2026-10-18，主跑前，用户授权）：原 f65a8328 方案扩展为上游证据审计、增益/几何对照和机制预测。以本文及 `research/continuation-contract.md` 为准；旧代码/结果不可变。正式主跑须等待审计、工程门和冻结提交。

## 1. 代数事实（动机）

令 s=Σv。对同延 doublet，完整 Γ 的和/差方向特征值为 s(1+|D_N|)、s(1−|D_N|)，标量 Γ 两者均为 s。标量在差方向更强、和方向更弱；不能概括为“更强 ridge”。m 个完全重合原子、总增益 h=Σa_j 时，完整 Γ 罚项为 s|h|²，标量在等分增益处的最小罚项为 s|h|²/m。该恒等式仅讨论不确定性罚项，实际目标还含 σ²I/ARD，不能据此宣称 FER 机理已识别。

## 2. 臂

所有六臂共用 E-3b 的第 1 级、第 1 轮、候选集与流程，只改第 2 级 SBL 和细化中的 Γ_var。数据字典仍用软均值 μ。基线 diag-off/cov-off 另输出固定 SBL 几何、不移动 Doppler、仅 `_system` 重估增益的 refit 结果；明确区分 SBL 增益→固定几何重估→连续细化三个阶段。SBL 从旧行读取其译码结果，所需增益/中间状态重建成本完整记录。

| 臂 | SBL 的 Γ_var | 细化 `_system` 调用 | 检验 |
|---|---|---|---|
| diag-off | Σv·I | gamma_mode='diag', ridge=σ² | 取自 E-3b 行（G1 核对） |
| cov-off | 完整 Γ(v) | gamma_mode='full', ridge=σ² | 取自 E-3b 行（G1 核对） |
| cov+ridge | 完整 Γ(v) + Σv·I | 'full', ridge = σ² + Σv | 收缩 |
| diag2 | 2Σv·I | 'diag', ridge = σ² + Σv | 收缩剂量对照（报告项） |
| cov-oracle | 完整 Γ(v_o) | 'full', v = v_o | 误设 |
| diag-oracle | Σv_o·I | 'diag', v = v_o | 误设对照 |

- v_o = |x − μ|²，逐符号取（AF 域），是单次实现的误差能量剖面，不是正确条件后验方差；仍缺误差均值与符号间相关。用到真值，仅作命名 oracle 诊断，失败不能否定一般后验误设。
- `_system` 的 ridge 参数会把 ridge·I 加到 Q 上，因此 cov+ridge 与 diag2 无需修改冻结核。
- 在 SBL 的 β 更新中，μᴴΓ_var μ 与 tr(·) 一律使用该臂自己的 Γ_var。

## 3. 读数

**校准读数**（每个键，零额外成本）：
- κ = Σ|x − μ|² / Σv，即整帧的实际误差能量与 APP 方差之比；
- 按 v/p_d 分箱 [0, .01)、[.01, .1)、[.1, .3)、[.3, 1)、[1, ∞) 的可靠性表，p_d 为 moments/字典实际坐标中的星座功率；逐键记录标签 ρ、e_rho、system.rho、p_d 与物理缩放，不把标签功率比混作坐标中的功率。
- "自信错误"比例：符号判错且 v < .1 p_d 的符号占全部判错符号的比例。

**其他读数**：每臂的 FER、NMSE、同时延普查（与 E-3b 同口径）、成本。

## 4. 冻结判据

- 两个份额：
  - Sh = (FER(cov-off) − FER(cov+ridge)) / (FER(cov-off) − FER(diag-off))
  - Or = (FER(cov-off) − FER(cov-oracle)) / (FER(cov-off) − FER(diag-off))
- 统计：配对 cluster bootstrap，cluster = (随机流域, 帧)，同源 U/G、ρ、SNR 必须同簇，20000 次，seed 20261018，百分位 95% CI。若重抽样中分母 ≤ 0 的比例超过 1%，份额记为不可评估，保留直接差及失败比例。
- 每个干预份额独立标为 recovered（CI下界≥.8）、small（CI上界≤.2）或 unresolved；仅为当前固定干预追回差距的描述，不命名 SHRINKAGE/MISSPEC 因果结论。
- oracle 配对 cov-oracle−diag-oracle 的 CI 上界≤.01 只称当前误差能量剖面下1个百分点非劣，不称方差正确。
- 重点同时报告 cov+ridge−diag2（同对角强度，非对角不同）、固定几何 refit−SBL 与 continuous−refit，按帧配对。
- McNemar 保留为旧口径/行独立假设下描述，非重复帧上的精确显著性认证。旧 verdict 原样保留，修订统计独立报告。

## 5. 门

- G1：20 个键上 diag-off、cov-off 的 decoded sha 与 E-3b 行一致；主跑中两者也重算，与 E-3b 行逐键核对，不一致即阻断解读。
- G2：
  - cov+ridge 的 Q 等于 cov-off 的 Q 加 Σv·I，误差 ≤ 1e-12；
  - diag2 的对角恰为 2Σv；
  - v_o 只在键内使用，并断言其来自真数据。
- G3：同一输入跑两次结果逐位一致。
- G4：smoke 估计核时 ≤ 15。

## 6. 局限

- 只有 ρ.3、两个场景、100 帧。
- oracle 方差只给出逐符号方差，不含符号间相关。
- 结论只适用于本 SBL 加细化接收机。

## 7. 上游审计与后续预测

先运行独立只读行审计，核对所有旧实验 key/arm/哈希、功率与坐标、Γ 实现和 FER 统计。重聚合输出新目录，不替换旧结果。发现可影响接收机行为的错误时，先最小复现、审查修复与冻结，明确哪些历史主张受影响。

样本外机制预测的具体干预/样本/通过标准须在审计后、读取该数据结果前登记于 `research/prediction-protocol.md`。发展集限定现有 E3/E3b 和 E3c 1200 旧键；未使用帧/新随机域另登记，不能把重用帧伪称 fresh。总新增接收机成本含门检/失败≤15 core-h；若无法容纳，先给成本证据，不隐式扩大。
