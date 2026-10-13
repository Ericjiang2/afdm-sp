# Knowledge — AFDM End-to-End Learning

知识点整理。理论、公式、方法论的长期积累。

---

## 格式模板

```markdown
### [ID] YYYY-MM-DD | 主题

**核心概念:**

**数学表达:**

**直观理解:**

**应用关联:**

**参考资料:**

---
```

---

## 记录开始

### 项目背景

本项目基于 OTFS-channel-estimation 仓库 fork 而来，专注于 AFDM（Affine Frequency Division Multiplexing）端到端深度学习研究。

### AFDM 基础

AFDM 是一种新型调制技术，相比 OFDM 在高移动性场景下具有更好的性能。

主要研究方向包括：
1. 信道估计
2. 数据检测
3. 端到端联合优化
4. 展开神经网络（Unrolled Neural Networks）

---

### [pic-bp-damping] 2026-04-20 | PIC/BP damping 稳定性与 Python/MATLAB 对齐

**核心概念:** AFDM 的 joint OMP+MP iterative receiver 里，inner MP detector (PIC 或 BP) 的 damping 系数 `pic_damp` 对 joint 稳定性是关键参数。之前 `damp=0.5`（Python/MATLAB 双方 default）在 AFDM 上**不稳定**，约 10% 信道实现下 cycling 发散。

**数学表达:**
- PIC 更新: `x_hat ← damp · x_hard + (1-damp) · x_hat`，其中 `x_hard = argmin_s |x_new - s|`
- damp=0.5 在强耦合 H（AFDM 近满秩有效信道）上出现 hard-decision 两两振荡 → 硬判决交替 wrong → mean BER 被 catastrophic 帧抬高
- damp=0.3 下 per-frame 全部 converge，perfect-CSI 40 帧 0 错

**直观理解:**
- damp 小 → 更新慢但稳定（averaging out oscillation）
- damp 大 → 更新快但易发散
- BP 对 damp 敏感度远小于 PIC（扫 0.3/0.4/0.5 只差 2x）—— 因为 BP 用 variance 做 soft-min，不依赖硬判决跳跃

**应用关联:**
1. **PIC 建议 default 改 damp=0.3**（取代 0.5），classical 侧立即拿到 ~10x BER 改善。
2. **`update_sigma2` 是双刃剑**：
   - BP @ SNR≈20dB：`update_sigma2=True` 让 σ² 估得过高 → BP 变保守 → 小幅变差
   - BP @ SNR≥25dB：`update_sigma2=False` 让 σ² 冻在真噪声级别（very small），但真实残差被 CE 错误主导 → BP 过度自信 → catastrophic 帧
   - 综合推荐：**`update_sigma2=True` 保留**，适配范围更广
3. Python `mp_detect_bp_torch` 和 MATLAB `MP_detection_optimized` **逐行一致**（同 factor-of-2、同 damp=0.5、同 threshold=1e-4）；docs/Algorithm_Details.md §3.6 的"factor-of-2 差异"是笔误，已推翻。

**P_paths 对齐**：MATLAB `TEST_P_PATHS=5`, Python 默认 `_build_sys(p_paths=10)`。两边用不同 P 会产生 ~44x BER 差异。**必须统一 P=5（MATLAB 习惯）或同时 P=10**。Python 命令行已加 `--p-paths` arg。

**非单调 BER @ 高 SNR**：看起来像 bug 其实是 **catastrophic outlier 帧采样噪声**——60 帧非 paired 采样在 SNR=25 偶尔抽到 1-2 个坏帧，把 mean BER 抬高。40 帧 paired 复现能单调。

**参考资料:**
- 实验证据：docs/Results.md §EXP-20260420-4way, §EXP-20260420-matlab-align, §EXP-20260420-b1-bp-uwa
- MATLAB 源：matlab/AFDM_UWA_acoustic.m:915-1115 (MP_detection_optimized), 1164-1320 (joint_omp_mp_ls_sparse)
- Python 源：afdm_sp_joint_unrolled/mp_detect_bp_torch.py, afdm_sp_joint_unrolled/afdm_baselines.py:275-438 (PIC + BP)

