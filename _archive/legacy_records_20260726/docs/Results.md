# Results — AFDM End-to-End Learning

实验结果分析。性能对比、消融实验、图表解读。

---

## 格式模板

```markdown
### [EXP-ID] YYYY-MM-DD | 实验名称

**实验目的:**

**实验设置:**
- 参数1:
- 参数2:

**结果数据:**
| 指标 | 方法A | 方法B | 方法C |
|------|-------|-------|-------|
| 指标1 | | | |
| 指标2 | | | |

**关键发现:**

**可视化:** [图表路径]

**结论:**

---
```

---

## 记录开始

### 已有模型文件

**模型文件**（位于根目录）:
- `afdm_blind_dnn_G1.0.keras` - 盲信道估计模型
- `afdm_e2e_lmmse_G1.0.keras` - LMMSE 端到端模型
- `afdm_sp_blind_dnn_rho0.30.keras` - SP 盲估计模型 (rho=0.30)

**结果数据**:
- `afdm_blind_results_G1.0.pkl`
- `afdm_e2e_results_G1.0.pkl`
- `afdm_sp_blind_results_rho0.30.pkl`

**可视化图表**:
- `afdm_blind_results_guard1.0.png`
- `afdm_channel_estimation_blind_0.png`
- `afdm_channel_estimation_blind_1.png`
- `afdm_e2e_G1.0.png`
- `afdm_pilot_placement_density0.25.png`
- `afdm_sp_blind_results_rho0.30.png`
- `afdm_sp_pilot_placement_rho0.30.png`
- `validate_sp_nmse.png`

---

### [EXP-20260420-4way] 2026-04-20 | PIC d=0.3 / d=0.5 / BP 三 backbone × classical/B1 4-way paired 对比

**实验目的:** 检验 (a) 换掉 PIC 默认 `damp=0.5`（不稳定）改成 `damp=0.3` 后 classical vs learned 还剩多少 headroom；(b) 用 classical BP（torch mp_detect_bp_torch）当 backbone，B1 是否能带来增益，是否能在"真正的 classical BP vs learned BP"意义上打赢 PIC。

**实验设置:**
- N=1024，v=1.0，10-path UWA，60 frames/SNR，paired seed=7777 across configs
- MP iter=20，outer iter=5，γ_H=0.7，γ_x=0.6，`threshold_mp=1e-4`，`update_sigma2=True`，early_stop=True
- 检测器：(a) PIC damp=0.3  (b) PIC damp=0.5  (c) BP damp=0.5（torch）
- B1 = `PerIterSymbolRefiner` CNN，200 heads iters，lr=2e-4，用对应 backbone 重训

**结果数据:** BER @ N=1024, v=1.0

| SNR | cls-PIC-d0.3 | lrn-PIC-d0.3 | cls-PIC-d0.5 | lrn-PIC-d0.5 | cls-BP-d0.5 | lrn-BP-d0.5 | perfect-CSI MMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 9.55e-2 | 8.60e-2 | 9.28e-2 | 8.46e-2 | 1.09e-1 | 1.03e-1 | 5.92e-2 |
| 15 | 1.04e-2 | 7.55e-3 | 1.05e-2 | 6.03e-3 | 4.02e-2 | 4.08e-2 | 1.02e-2 |
| 20 | **2.28e-4** | **6.51e-5** ✅ | 3.82e-4 | 2.04e-4 | 8.81e-3 | 1.30e-2 ⚠️ | 4.80e-4 |
| 25 | 9.28e-4 ⚠️ | 9.12e-4 | 8.87e-4 | 1.57e-3 ⚠️ | 9.16e-3 | 1.54e-2 ⚠️ | 2.44e-5 |

辅助实验：perfect-CSI 下 40 帧 {MMSE, PIC d∈{0.3,0.5,0.7,1.0}, BP d=0.5} 纯检测器对比，40 帧 × 2048 bit：
- MMSE = 6.1e-4（每帧 max=6 错，distribution smooth）
- **PIC d=0.3 = 0** 错  (40 帧全零)
- PIC d=0.5 = 2.1e-2 ←默认damp，40 帧里 4 帧 catastrophic（每帧 600+ 错）
- PIC d=0.7 / 1.0 发散到 2.1e-1 / 4.2e-1
- BP torch d=0.5 = 0 错 (120 帧全零 at perfect CSI)

BP damp sweep @ joint mode（N=1024, v=1.0, adaptive target 200 errors）：
- damp=0.3: SNR20=3.41e-2 SNR25=4.38e-2
- damp=0.4: SNR20=1.96e-2 SNR25=1.39e-2（BP 最佳）
- damp=0.5: SNR20=3.65e-2 SNR25=2.54e-2

**关键发现:**

1. **B1 最佳栖息地是 PIC damp=0.3**：6.51e-5 at SNR=20，比 `lrn-PIC-d0.5` 的 2.04e-4 再降 3x，比 `cls-PIC-d0.3` 的 2.28e-4 降 71%。这是全部组合里 SNR=20 BER 最低的 learned 配置。
2. **"B1 大胜 PIC" 的光环大部分是假的** — 主要是在帮 PIC 从 `damp=0.5` 不稳定爬出来。`cls-PIC-d0.3 = 2.28e-4` 已经胜过 `lrn-PIC-d0.5 = 2.04e-4`（只差 12%），**换 damp 不用训也能几乎完全追平老 learned** PIC。
3. **BP 在 joint 模式烂**：classical 8.8e-3，learned 1.3e-2（B1 反而让 BP 更差）。比 cls-PIC-d0.3 差 **38–57 倍**。damp 扫 0.3/0.4/0.5 只差 2x，不是 damp 问题。
4. **perfect-CSI 下 BP 本身完美**（120 帧零错 at SNR=20），但 joint-CE 下被炸。codex 判断：BP 对 CE 错图过度自信 + σ²/DA-LS 反馈放大错误（hypothesis #1+#2，damp #3 已被上述扫描证伪）。
5. **高 SNR 非单调**：所有 classical 在 SNR=25 BER 反而高于 SNR=20（PIC d=0.3: 2.28e-4 → 9.28e-4，+4x）。待查。

**结论:**
- 推荐 default：PIC damp **0.3** 取代 0.5，在 classical 这侧立刻拿到 2e-4 级别 BER；
- 如果追求最佳 BER，继续用 B1（但要在 d=0.3 backbone 重训，**放弃原 B1 on d=0.5 checkpoint**）；
- BP 路线在 joint 模式上**暂不可用**；需要下阶段专门针对 "CE-BP 过度自信" 的接口改造（放宽 threshold_mp / 延后 update_sigma2 / 降 γ_h）；
- 高 SNR 非单调问题需要独立查，codex 建议测 per-iter BER（验证 iter4<iter5）和 freeze σ²_eff ablation。

---

### [EXP-20260420-matlab-align] 2026-04-20 | Python BP vs MATLAB BP 对齐复现

**实验目的:** 验证前一个 EXP 的"BP joint 烂"结论是真 bug 还是 config 不对齐。

**实验设置:**
- Python 和 MATLAB 都用 `N=1024, v=2.0, P_paths=5, rho=0.5, K_LEAK=2, mp_mode=bp, damp=0.5, tau_spread=10ms`（现实 UWA）
- 200 frames paired, seed=7777
- MATLAB 版跑自 `matlab/AFDM_UWA_acoustic.m` 的 TEST_MODE 加 diag 打印块
- Python 版跑自 `afdm_sp_joint_unrolled/snr_nonmonotonic_probe.py`
- κ @ v_mean=2, N=1024 = 0.048（NEAR-INTEGER）；per-path κ 因 v_std 分散到 0.18–0.45

**结果数据（Joint BP BER, 200 frames）**:

| SNR | MATLAB Joint (it5) | Python BP sigma2_on iter4 | Python BP sigma2_off iter4 |
|----:|----:|----:|----:|
| 15 | 1.89e-2 | **1.30e-2** | 2.72e-3 |
| 20 | 1.99e-4 | **7.81e-5** | **0** |
| 25 | 5.03e-5 | **0** | 4.88e-6 |
| 30 | 1.51e-5 | **0** | 1.95e-5 |

Per-iter @ SNR=20 (两边都 5 outer iter)：

| iter | MATLAB (damped) | Python (raw mu_x) |
|---:|---:|---:|
| 1 | 1.33e-2 | 7.63e-2 (un-damped) |
| 2 | 8.65e-4 | 1.50e-2 |
| 3 | 2.72e-4 | 5.15e-4 |
| 4 | 2.09e-4 | 1.34e-4 |
| **5** | **1.99e-4** | **7.81e-5** |

Python iter0 是 BP 裸输出（未 damp），所以前几列比 MATLAB 高；最后一轮两边都进入收敛态。

**关键发现:**

1. **Python BP joint 在 P=5 下和 MATLAB 完全对齐，甚至略胜 2.5x**（SNR=20: 7.81e-5 vs 1.99e-4）。
2. 之前 4-way eval 的"BP joint 8.8e-3 烂"是 **`P_paths=10` 的 artifact**。Python `_build_sys` 默认 P=10，MATLAB TEST_MODE P=5 — 不公平。
3. **MATLAB 公式 `MP_detection_optimized` 和 Python `mp_detect_bp_torch` 逐行一致**（包括 `log_prob = -dist_sq/(2*var_ext)` 同样有 factor-of-2）。之前 Algorithm_Details.md §3.6 写的 "MATLAB 无 factor-of-2" 是笔误。
4. **MATLAB 在 SNR=25→30 也出现非单调**（5.03e-5 → 1.51e-5 正常，但 4.3e-4 超过 25 的那组是之前 P=10 MATLAB 的）。Python paired 40 帧下 classical PIC d=0.3 单调，60 帧非 paired 才出现非单调 → **非单调是 catastrophic 帧采样噪声**。

**结论:**
- **P_paths=5 必须作为 Python 对齐 MATLAB 的 default**（`_build_sys(p_paths=5)` 已加 CLI arg）。
- Python BP joint detector **等效或优于 MATLAB MP**。之前报的"BP 不行"已经被推翻。

**相关文件:**
- Python 运行：`afdm_sp_joint_unrolled/outputs_matlab_matched_bp_*/results.md`
- MATLAB 修改：line 107 `NUM_OUTER_ITS`, 150 `TEST_P_PATHS`, 154 `TEST_N_OVERRIDE`, 追加 CONFIG dump at line 185+
- Probe脚本：`afdm_sp_joint_unrolled/snr_nonmonotonic_probe.py`（加了 --p-paths, --tau-spread, --rho, --k-leak）
- Repro 复现：`afdm_sp_joint_unrolled/outputs_repro_n256_bp_tau05_*/results.md` 显示 SNR≤25 bit-exact

---

### [EXP-20260420-b1-bp-uwa] 2026-04-20 | B1 on BP @ N=1024 P=5 tau=10ms (真实UWA)

**实验目的:** 在对齐 MATLAB 的真实 UWA config (P=5, tau=10ms) 下，测试 learned B1 (PerIterSymbolRefiner) 能否比 classical BP joint 再降 BER。

**实验设置:**
- Backbone: `classical_joint_unrolled`，`cfg.mp_mode='bp'`，`cfg.pic_damp=0.5`
- Training: `train_classical_joint_unrolled.py --variant B1 --freeze-scalars --mp-mode bp --pic-damp 0.5 --p-paths 5 --n-total 1024 --v-mean 2.0`
- SNRs: [10, 15, 20, 25]，batch=2，lr_heads=2e-4，complex64
- **早停：`--patience 3`, `--eval-every 30`**（v0.3 新增）
- 300 iters budget 但通常 early-stop 在 ~180 iters

**结果数据（训练 held-out eval, 20 frames/SNR, best at i=89）**:

| SNR | classical BP | learned B1 on BP | Δ |
|----:|----:|----:|----:|
| 10 | 8.58e-2 | 7.73e-2 | **−8.54e-3 (helps)** |
| 15 | 1.12e-2 | 1.11e-2 | −7e-5 (≈ tied) |
| 20 | 3.42e-4 | 4.39e-4 | +1e-4 (tiny regression) |
| 25 | 0 | 0 | 0 (tied) |

**Best checkpoint**: `outputs_cju_n1024_B1_bp_p5_realuwa/classical_joint_unrolled_best.pt`
- mean_Δ = **−2.13e-3**（整体 B1 帮助）
- 主要来自 SNR=10 的大幅提升
- 早停在 i=179 触发（省 40% 训练时间）

**关键发现:**

1. **B1 有 headroom，但只在低 SNR**（SNR=10 有 10% 相对 BER 改善）。
2. **高 SNR (≥20) B1 无 headroom** —— classical BP joint 已经逼近 perfect-CSI MMSE，B1 会增加噪声。
3. **早停工作良好**：patience=3 × eval_every=30 ≈ 90 iters 无改善就退出，给整体训练节省 ~40% 时间，best ckpt 不变。

**规律（综合历次训练）:**

| Config | classical BP @ SNR=20 | B1 best mean_Δ | B1 帮助 |
|---|---|---|---|
| **N=1024 P=5 tau=10ms (本实验)** | ~4e-4 | **−2.13e-3** | ✅ 在 SNR=10 |
| N=256 P=5 tau=3ms | ~1e-2 | ~−5e-5 | ≈ 平 |
| N=256 P=5 tau=0.5ms | 4e-4 | **+3.44e-3** | ❌ 有害 |
| N=1024 P=10 tau=10ms (旧, 含 P 错配) | 8.8e-3 | +5.49e-5 | ≈ 平 |

**根本规律**：**信道越简单（tau 短 / N 小）→ classical 越贴近下界 → B1 越没用**。B1 的价值 regime 是"信道复杂 + 真实 UWA 物理"。

**结论:**
- 主线 learned-receiver 训练应专注 **N=1024 + P=5 + tau=10ms（真实 UWA）** 条件。
- B1 only 的总体改善 modest（~10% BER 在 SNR=10），**不够发一篇论文**。需要考虑：
  a) 不同的 learned head（侧重 CE 而非 detector）
  b) 更大的 B1 capacity / 多 refiner
  c) 换 learning target（distillation）
  d) 接受 classical 已经够好，论文重点转向 config 对齐 + damping 稳定性

**相关文件:**
- 训练：`outputs_cju_n1024_B1_bp_p5_realuwa/{train.log, classical_joint_unrolled_best.pt, classical_joint_unrolled_final.pt}`
- 脚本修改：`train_classical_joint_unrolled.py` 加 `--p-paths`, `--tau-spread`, `--patience` CLI
