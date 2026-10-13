# Open Questions

## 最新（2026-04-20, Round 8+）

1. **Classical joint BP 的新基线数字已显著提升**（N=1024 P=5 tau=10ms SNR=20 = 7.81e-5），这让 **B1-on-BP 的绝对改善空间窄化**。是否需要换论文 framing？
2. **B1-on-PIC-d=0.3 仍是 learned-receiver 最佳配置**（6.51e-5 @ SNR=20），但已经不再显著优于 classical PIC d=0.3（2.28e-4）。是否继续推"learned gain"叙事？
3. 小信道场景（N≤256，tau≤3ms）下 B1 不帮忙 —— 是放弃小信道叙事，还是专门为小信道设计不同 head？
4. **σ² 更新是双刃剑**的现象在 MATLAB 里也有吗？需要让用户跑一下 MATLAB 的 `update_sigma2=true` vs `false` 对比验证。
5. N=64/128 是否真的需要？MATLAB 的自适应 N 机制让 N=64 变相不存在。如果 MATLAB 本来也跑不了 N=64，那是否退出这条实验线？

## Highest Priority (旧, 2026-04-19)

1. Which transfer test most cleanly goes beyond the current AFDM simulator family without putting the current `7.5/10` story at risk?
2. What is the strongest next-step deployment endpoint beyond the current uncoded contiguous-packet ARQ proxy?
3. What nontrivial mechanism, beyond simple confidence or SNR gating, could reduce the low-SNR (`5` dB) harm?

## Method Questions

1. Which observable features matter most inside the frozen corrector?
2. How much of the oracle-beneficial flip set is the frozen corrector actually recovering under each shift axis?
3. Is there a better frozen post-hoc corrector than the current small MLP while keeping the method simple?
4. Why does `P_paths=15` fail so sharply, and is there a simple fix that preserves the rest of the story?
5. Can a cheap oracle-recovery analysis be added without full multi-cache BP replays?

## Paper Questions

1. Which venue is the best fit for a diagnostic-plus-method AFDM story with multi-regime gains, packet-level significance, and a `7.5/10` external review?
2. How aggressively should the paper separate:
   - failed mean-residual line
   - failed linear gating line
   - successful frozen direct-bit line
   - explicit failure-boundary line
3. Should the new bootstrap-CI and feature-ablation package be placed in the main text or partly moved to the appendix?
