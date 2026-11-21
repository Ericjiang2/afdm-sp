# 设计

## 帧
P1 生成器，帧 7000..7199，共 200 帧。执行者需查证这段帧从未被使用过；若已被用过，就向后找最小的、从未被用过的连续 200 帧，并记录查证结果。

## 族 S：数据辅助 SBL（E-3 管线，on-grid 第 2 级）
键：U/G × ρ .3 × 6..11 dB × 200 帧 = 2400。

| 臂 | 选原子 | 增益 |
|---|---|---|
| S-D | SBL，Γ_var = Σv·I | SBL 后验均值（= E-3 L-diag） |
| S-C | SBL，Γ_var = 完整 Γ | SBL 后验均值（= E-3 L-cov） |
| **S-H**（按原则构造） | 沿用 S-C 选出的原子 | 在这些原子上用各向同性正则重解：`_system(Y, xt_soft, v, paths, c1, c2, ridge = σ², gamma_mode = 'diag')` 的 h，即 (B̄ᴴB̄ + Σv·I + σ²I)⁻¹B̄ᴴY |

第 2 轮：`scalar_joint(gain_mode = 'fixed', prior = check)`，再接 LDPC。

## 族 K：CSTATE（E-1 管线）
键：U/G × ρ{.3, .5} × 4.5..8.0 dB × 200 帧，对全部键先跑 F0；只有触发单元（F0 终末 syndrome ≠ 0）进入以下各臂。

| 臂 | 交换决策 | 送入检测器的增益 |
|---|---|---|
| K-prod | 完整 Γ（A1） | 生产配置：`scalar_joint(gain_mode = 'joint')`，检测器重新估计增益 |
| K-diag | 对角 Γ（A2） | 同 K-prod（复现 E-1） |
| K-fullfix | 完整 Γ（A1，同一组最终路径） | `gain_mode = 'fixed'`，增益取 `_system(..., gamma_mode = 'full')` 的 h（即 result.gains） |
| **K-isofix**（按原则构造） | 完整 Γ（A1，同一组最终路径） | `gain_mode = 'fixed'`，增益取 `_system(..., gamma_mode = 'diag')` 的 h |

## 冻结的预测（由原则推出，跑前写定）

所有差值均用配对 cluster bootstrap 估计 CI（按帧聚类，20000 次，seed 20261018，95% 百分位区间）。

- **P1（S 族，估计）**：FER(S-H) − FER(S-C) 的 CI 上界 < 0。
- **P2（S 族，非劣）**：FER(S-H) − FER(S-D) 的 CI 上界 ≤ .01。
- **P3（K 族，估计）**：K 族只看触发单元的救回率 R。要求 R(K-isofix) − R(K-fullfix) 的 CI 下界 > 0。
- **P4（K 族，决策，即 E-1 的复现）**：R(K-prod) − R(K-diag) 的 CI 下界 > 0。

## 判定（按顺序取第一条成立的）

1. **REFUTED**：P1 或 P3 的方向反了，且显著，即 FER(S-H) − FER(S-C) 的 CI 下界 > 0，或 R(K-isofix) − R(K-fullfix) 的 CI 上界 < 0。
2. **CONFIRMED**：P1、P2、P3、P4 全部成立。
3. **PARTIAL**：P1 与 P3 成立，但 P2 或 P4 不成立。
4. **MIXED**：其他情况。

报告项：各臂的 FER / 救回率、NMSE、同时延普查、SBL 达到迭代上限的比例、成本。

## 门
- G1：S-D、S-C 在 20 个 E-3 键上与 E-3 的行逐位一致；K-prod、K-diag 在 E-1 的 gate 状态上与 E-1 的 A1、A2 逐位一致。
- G2：v ≡ 0 时 S-H = S-C；K-fullfix 的增益等于 result.gains。
- G3：确定性。
- G4：成本 ≤ 15 core-h。

## 编排者跑前修订 A1（2026-10-18，冻结前，未见任何新帧结果）

**原因**：门检诊断只用了旧的 gate 单元。在这些单元上，K-isofix 与 K-fullfix 的增益相对差只有 2e-5 到 8e-4，cond(Q) ≈ 1.2。A1 的最终路径之间间隔很开，原则本身就预测这两种增益在这里没有区别，所以原来的 P3 没有判别力。这是设计错误。

**新增 K 臂**（交换决策与 K-diag 相同，均为对角 Γ 的 A2，因此最终路径相同；这些路径里近重合的同时延对很多）：
- K-diag-fullfix：`gain_mode='fixed'`，增益取 `_system(..., gamma_mode='full')` 在 A2 最终路径上的 h。
- K-diag-isofix：`gain_mode='fixed'`，增益取 `_system(..., gamma_mode='diag')` 在 A2 最终路径上的 h。

**预测的修改**：
- **P3a**（取代 P3，有判别力）：R(K-diag-isofix) − R(K-diag-fullfix) 的 CI 下界 > 0。
- **P3b**（原则预测在无判别力处两者等价）：R(K-isofix) − R(K-fullfix) 的 CI ⊂ [−.01, .01]。

**判定**：
- REFUTED：P1 显著反向，或 P3a 显著反向。
- CONFIRMED：P1、P2、P3a、P3b、P4 全部成立。
- PARTIAL：P1 与 P3a 成立，但 P2、P3b、P4 中至少一个不成立。
- MIXED：其余情形。
