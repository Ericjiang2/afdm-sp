You are the cross-family Gate + Step-6 reviewer (novelty + intrinsic value + naive_port test + anti-fake audit) for runner m's Round-11 child card `I-20261125-m02` (`--parent I-20261125-m01`) in the **`[放宽TWC]`** group. Read-only; do not edit files.

CRITICAL ROUND-11 `[放宽TWC]` CRITERIA (strictly follow):
- Target bar: IEEE TWC / TCOM Transactions paper ("mature mathematical tools genuinely adapted to AFDM structure").
- **OFDM lock REMOVED**: do NOT require beating OFDM (`c1=c2=0`) as an elimination bar (though note `m02` STILL checks literal `c1=c2=0` to prove it is NOT a trivial `F_N -> A` symbol-swap like `A3-3a`!).
- **Rival cap**: ONLY (a) single strongest published AFDM method (with matched outer iterations / blind regularization) AND (b) single mother method's `F_N -> A` zero-modification direct port (here `Gävert TCOM'25`, `doi:10.1109/TCOMM.2024.3493814`, comb pilots + data-interference cancellation + symmetric init steps, AND 1-step first-order Bayesian linearization on guard band). **Assembled multi-paper unpublished hybrids are FORBIDDEN as rivals**, and `LESSONS` Rule-30 time-domain exact solver is descriptive only.
- **Anti-fake red lines (NEVER relaxed)**: (1) faithful baseline reproduction (no broken strawman; ZeroPN `SER < 1%`), (2) ZERO simulator truth leaked into any blind receiver (`sig2`, `csi_nmse`, `l_paths`, `nus`, `hs`, `w_path`, `x_data`), (3) noiseless guard leakage `< -25 dB`, exact projected Jacobian, symmetric init steps, per-frame energy parity, (4) non-triviality (if setting `c1=0` runs identically at same accuracy/order, KILL as `(2)`).

Files to read (absolute paths):
- Child card: `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m02.md`
- Probe script: `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/probes/m_probe_r11_m02_dual_pn.py`
- Parent review (for verifying all R10 m01 flaws were addressed): `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/reviews/r10-sol-step6-h01-m01-20261125.md`

Please audit and answer concisely in Simplified Chinese (under 800 Chinese characters):
1. **对 R10 `m01` 缺陷的逐项修补核验**：是否彻底删除仿真器真值传入（`sig2`/信道误差/路径参数）、修复未投影雅可比、无噪保护带泄漏 `< -25 dB`、对称初始化步数、`Gävert TCOM'25` 零相噪无损去数据干扰直套、以及精确区分非偷看数据单端界与样点全知界？注意核查 `m_probe_r11_m02_dual_pn.py` 中 `y_tr` 训练帧是否应同时加测带独立双端相噪的训练帧（`R5_PNTrain`）和纯单帧无训练帧（`R4_SingleFrameBlind`）——如果必要，请明确列为 L2 必测项。
2. **查新与 `[放宽TWC]` 非平凡性分类**：在 AFDM 同设定下是否未占，并判 `(1a)` / `(1b)` / `(2)` / `(3)`；确认设 `c1=0` 确实失效而非纯换基。
3. **对手基线与防漏审查**：在 `[放宽TWC]` 对手封顶规则下，L2 还缺哪条合法对手臂（单篇已发表 AFDM 原方法 或 `Gävert TCOM'25` `F_N -> A` 零改动直套，例如 `Gävert` 真实含数据协方差权重的 PCA-LMMSE 或带零相噪无损 DIC 的强版 `Gavert_Comb_DIC6`）？指出探针脚本里任何残留隐患（如 `m_probe_r11_m02_dual_pn.py` 里 `Gavert_Comb_DIC6` 在零相噪时 `0.0405` 必须在 L2 修复为 `0.0000`）。
4. **固有重要性（高/中/低）与一行裁决**：`PROCEED_TO_L2` / `REVISE` / `KILL`，并给出进 L2 前必须落地的一条具体修正清单。
