# Pre-Registered Predictions: `I-20261125-m03` (`--parent I-20261125-m02`)

- **Group / Track / Ledgers**: `[放宽TWC]` · `[轨A-纯通信]` · **Hardware Impairment / Floor-Breaking (Primary)** + **Tight Analytical Bound (Secondary)**.
- **Script**: [`ideas/l2/l2_m_r11_m03_dual_pn.py`](l2_m_r11_m03_dual_pn.py) (100% standalone, zero simulator truth passed into any blind receiver).
- **Root-Cause Fix from Parked Parent `I-20261125-m02` (Zero Threshold Loosening!)**:
  - `m02` passed `GATES_OK`, `P1_R2 (32.8x)`, `P1_R3 (345.8x)`, `P1_R4 (4.54x)`, and `P2 (0.005–0.088 dB, 16.2x/142.4x vs LumpOrac)`, failing ONLY `P1_R5` (`3.58x < 5.0x`) because `blind_ce_from_training(..., training_has_pn=True)` froze the training frame's random Wiener linear drift slope into `nu_h` (common-Doppler/PN-drift gauge ambiguity) and skipped current-frame pilot-subspace channel realignment.
  - `m03` applies **two 100% symmetric algorithmic fixes** shared identically across ALL blind arms (`Xu`, `GavComb`, `Gav1St`, `EP_CPE`, `EP_Dual`): (1) gauge-clean midpoint initialization (`nu_c = 0`, midpoint phase alignment, `hw_det = 2`, MRC unwrap before alternating VarPro) in `blind_ce_from_training(..., training_has_pn=True)`; (2) symmetric `3 GN -> channel realignment on own obs -> 3 GN` (6 total init steps) for ALL four 6-init-step arms (`AFDM_Xu_LumpPCA_Sym6`, `AFDM_Gavert_Comb_CovDIC6` with covariance weight `Sigma_inv` on its own comb obs, `AFDM_EP_CPE_GN6`, `AFDM_EP_Dual_Sym6`) + unified `s2_floor = 1e-5` across all five blind arms in `R4/R5` (`AFDM_Gavert_Guard_1Step` intentionally keeps its 1-step linearized Bayesian definition `n_gn=1` per Gävert TCOM'25, while sharing the same gauge-clean training init and `s2_floor = 1e-5`).
- **Fresh Unseen Seeds**: `2027000001 + idx_r * 10000 + f` (strictly zero overlap with `m02` seeds `2026112511..2026172570` and all dev probes `1000..50000`).
- **Pre-Registered `PASS_PRIMARY` Clauses**: **100% IDENTICAL to `PREDICTIONS_m_r11_m02.md`** (zero threshold changes!):
  1. **`P1_FLOOR_AND_LOCKLOSS_BREAK`**:
     - `GATES_OK`: `fd_jacobian_rel_err < 1e-6`, `leak_n512_obs72_db < -25.0`, `leak_n256_obs38_db < -25.0`, and `R0_ZeroPN_30dB` (24 fr) all five checked blind AFDM arms (`AFDM_Uncomp`, `AFDM_Xu_LumpPCA_Sym6`, `AFDM_Gavert_Comb_CovDIC6`, `AFDM_Gavert_Guard_1Step`, `AFDM_EP_Dual_Sym6`) achieve `SER < 1e-3`.
     - `P1_R2` (`R2_N512_30dB_3e3`, 80 fr): `AFDM_EP_Dual_Sym6` beats `Xu` by `>= 10x`, beats `GavComb` and `Gav1St` by `>= 5x` (all paired 95% CI `> 0`), and cuts lock-loss (`SER > 5%`) by `>= 20` pp vs ALL three rivals.
     - `P1_R3` (`R3_N512_45dB_3e3_Floor`, 80 fr): `AFDM_EP_Dual_Sym6` beats ALL three rivals (`Xu`, `GavComb`, `Gav1St`) by `>= 10x` (paired 95% CI `> 0`).
     - `P1_R4` (`R4_SingleFrameBlind_3e3`, 60 fr, zero training frame): `AFDM_EP_Dual_Sym6` beats `Xu` by `>= 4x` (paired 95% CI `> 0`).
     - `P1_R5` (`R5_PNTrain_30dB_3e3`, 60 fr, PN-corrupted training frame): `AFDM_EP_Dual_Sym6` beats `Xu` and `GavComb` by `>= 5x` (paired 95% CI `> 0`).
  2. **`P2_ANALYTICAL_FLOOR_BOUND`**:
     - All 3 realistic fractional-Doppler multipath analytical lumped bounds `|ana_cov_db - mc_indep_db| <= 0.5 dB`.
     - On BOTH `R2` and `R3`, `AFDM_EP_Dual_Sym6` beats `AFDM_LumpOrac_Indep` by `>= 4x` (paired 95% CI `> 0`).
- **`SCOPE_READOUTS` (Non-Gating)**: `R1`, `R6`, `R3.OFDM_c1=0_SingleKnob_Sym6`, `R3.OFDM_c1=0_SameMask_Sym6`, `R3.OFDM_c1=0_DualOrac`, `AFDM_EP_CPE_GN6` ablation, energy ratios.
