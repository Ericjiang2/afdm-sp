# Sol Pre-Run Static Code Audit — Round 6 Priority Step-7 Revisions (`g04` & `g02`)

- **Date**: `2026-11-23`
- **Reviewer**: `gpt-6.2-sol` (`codex exec --sandbox read-only -m gpt-6.2-sol -`)

## 1. Raw `Sol` Pre-Run Audit Output

**VERDICT: FIX_REQUIRED**

- **g04｜展宽 OTFS 的平均总能量低于 520。** 固定编码位使数据符号均值非零，循环前缀保留了导频与数据的交叉项。按编码表和波形公式计算，导频能量占比为 `0.08` 和 `0.14` 时，平均总能量分别为 **519.9012** 和 **519.8736**。启动检查允许偏差 4，无法检出。`g_r6_rev_g04_impulsive_blind.py:111–124, 287–291, 475–477, 538–552`
- **g04｜真信道对照只在期望上配平数据能量。** 两种波形的平均数据能量均为 447.2，但同一帧的循环前缀能量随波形变化。以全零信息位为例，仿射频分复用（AFDM）和正交时频空调制（OTFS）的含前缀数据能量分别为 **440.394** 和 **438.073**。`g_r6_rev_g04_impulsive_blind.py:111–124, 419–427`
- **g04｜共享盲掩模的辅助读数混入残余脉冲。** 加掩模组译码的是仍含未擦除脉冲的信号，未擦除组只有热噪声，因此差值同时计入擦除和残余脉冲的影响。实际接收链也缺少同一含脉冲帧上关闭置零的基线。`g_r6_rev_g04_impulsive_blind.py:428–456, 587–593, 644–655`
- **g04｜主判据在 5 个百分点边界会误判。** 400 帧中错 55 帧和 35 帧，浮点相减得到 `0.05000000000000002`，导致本应通过的 `<= 0.05` 失败。用错帧数差 `<= 20` 可精确判定。`g_r6_rev_g04_impulsive_blind.py:657–662`
- **g02｜八状态布局的离线搜索预算没有配平。** `SwapHC4000` 最多给 4,000 个候选打分，同状态交换还会跳过。`Balanced_DB` 每轮最多评估 32 个移位，共最多 128,000 个候选。`g_r6_rev_g02_reconfig_ctrl.py:79–85, 100–128`；`PREDICTIONS_g_r6_rev_g02g04.md:53–56`
- **g02｜秩一工况的实际耦合矩阵不互易。** 实现要求反向系数满足 `Cm[v,u] == Cp[u,v]` 才能使相邻阵元的正反耦合相同。独立抽取的 `gam` 经镜像置换后通常破坏该等式，二阶邻接项也未施加互易约束。`g_r6_rev_g02_reconfig_ctrl.py:153–159, 451–455`
- **g02｜结论分流会在主判据失败时仍宣告覆盖必要性。** 序列专属优势未通过时，代码直接输出收窄后的必要性结论，即使四状态受控反转或八状态覆盖比较失败。`g_r6_rev_g02_reconfig_ctrl.py:756–763`；`astra-gate-r5-g02g04-20261123.md:79`

## 2. Pre-Launch Fixes Verified Before Running on `deinlab`

1. **`g04` exact `520.0` analytical energy**: Added fixed deterministic ±1 scrambling `scram_12` to `Spread_OTFS` so all `512` symbols (including the fixed 513th bit) are strictly zero-mean uncorrelated with the pilot (`|E[||s_cp||^2] - 520.0| < 1e-11` asserted in `run_smoke()`), and explicitly documented deterministic expected CP-included energy parity (without data-dependent per-frame AGC) in `PREDICTIONS_g_r6_rev_g02g04.md`.
2. **`g04` clean `SharedBlindMask` attribution & practical `EP_AFDM_Unblanked` baseline**: Applied `km_shared_blind` to `r_af_clean` and `r_ot_clean` so `G04_S2` isolates pure erasure geometry without conflating unblanked residual impulses, and added practical `EP_AFDM_Unblanked` (`keep_mask = 1`) on the exact same frames.
3. **`g04` integer error-count thresholds**: Replaced floating-point `0.05` boundary checks on `n=400` with exact integer error-count comparisons (`>= 20` and `<= 20`).
4. **`g02` distinct-state `SwapHC128k` matched evaluation budget**: Eliminated same-state no-op swaps in `build_swap_hc_layout` using fast incremental updates and added `SwapHC128k` (`128,000` distinct-state swap evaluations, matching `Balanced_DB`'s `4,000 * 32 = 128,000` shift evaluations) alongside `SwapHC150` and `SwapHC4000`.
5. **`g02` exact symmetric multiport reciprocity in `MC_rank1_recip`**: Symmetrized `gam_sym` and `C2_sym` with `Cm = Cp.T` so the multiport coupling matrix satisfies exact reciprocity `M == M.T` to `< 1e-15` (asserted in `run_smoke()`).
6. **`g02` guarded `claim_routing`**: Routed `claim_routing` to `"FAIL_PRIMARY"` whenever `not (g02_p1 and g02_p2)`.
