# 设计

## 臂

六个臂共用同一观测、第 1 级、第 1 轮与候选集，数据字典 B̄ 均为软均值字典。

| 臂 | SBL 中的 Γ_var | 增益 |
|---|---|---|
| D-sbl | Σv·I | SBL 后验均值（= E-3 L-diag） |
| C-sbl | 完整 Γ | SBL 后验均值（= E-3 L-cov） |
| C-ls0 | 完整 Γ（只决定选哪些原子） | 在选出的原子上解 (B̄ᴴB̄ + σ²I)⁻¹B̄ᴴY，不含 Γ |
| D-ls0 | Σv·I（只决定选哪些原子） | 同上 |
| Z-sbl | 0 | SBL 后验均值 |
| Z-ls0 | 0（只决定选哪些原子） | 同上 |

- 被选原子的规则与 E-3 的 `select_output` 相同。
- LS0 直接调用冻结核 `_system(Y, xt_soft, v = 0, paths, c1, c2, ridge = σ²)`，取返回的 h；该 h 即上式的解。
- 第 2 轮：`scalar_joint(gain_mode = 'fixed', prior = check)` 后接 LDPC。

## 读数

各臂的 FER、NMSE、同时延普查、被选原子数；SBL 是否达到迭代上限；成本。

## 冻结判据

统计方法：配对 cluster bootstrap，按帧聚类（同一帧的所有场景与 SNR 合为一个簇，共 100 簇），重抽 20000 次，seed 20261018，取百分位 95% CI。

- **BIAS-SUPPORTED**：FER(C-ls0) − FER(C-sbl) 的 CI 上界 < 0，且 FER(C-ls0) − FER(D-sbl) 的 CI 上界 ≤ .01。
- **VARIANCE-SUPPORTED**：FER(C-ls0) − FER(C-sbl) 的 CI 下界 > 0。
- 其他情况为 **MIXED**。
- 报告项：D-ls0 − D-sbl、Z-sbl − D-sbl、Z-ls0 − Z-sbl，以及精确单侧 McNemar（log10 p）。

## 门

- G1：在 20 个键上，D-sbl 与 C-sbl 的原子、decoded sha 均与 E-3 行一致。
- G2：v ≡ 0 时 Z-sbl = D-sbl = C-sbl；LS0 的解与独立 numpy 求解一致，误差 ≤ 1e-10。
- G3：确定性。
- G4：成本估计 ≤ 6 core-hours。
