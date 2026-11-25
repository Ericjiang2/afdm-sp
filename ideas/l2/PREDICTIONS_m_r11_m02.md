# Pre-Registered Predictions: `I-20261125-m02` (`--parent I-20261125-m01`)

- **Group / Track / Ledgers**: `[放宽TWC]` · `[轨A-纯通信]` · **Hardware Impairment / Floor-Breaking (Primary)** + **Tight Analytical Bound (Secondary)**.
- **Script**: [`ideas/l2/l2_m_r11_m02_dual_pn.py`](l2_m_r11_m02_dual_pn.py) (100% standalone, zero simulator truth passed into any blind receiver).
- **Seeds**: Fresh unseen seeds `2026112511 + idx_r * 10000 + f` (zero overlap with dev probes `1000..50000`).
- **Sol Step-6 `REVISE` Audit Compliance**:
  1. Standalone script with finite-difference check of exact projected Jacobian $\mathbf{A}_{\mathcal{O}}\mathbf{J}$ (`< 1e-6`).
  2. Exact noiseless leakage verified on the actual observation windows (`N=512` 72-bin obs `-28.6 dB < -25 dB`, `N=256` 38-bin obs `-28.2 dB < -25 dB`), plus per-frame energy ratio (including CPP/CP) logged.
  3. Published AFDM single-end rival: `AFDM_Xu_LumpPCA_Sym6` (`Xu PIMRC'26 / arXiv:2604.17858` reduced-rank PCA single-end Wiener PN, upgraded to symmetric 6-step init + 6 outer + blind mismatch variance regularization).
  4. Mother method `Gävert TCOM'25 (10.1109/TCOMM.2024.3493814)` `F_N -> A` direct port: BOTH `AFDM_Gavert_Comb_CovDIC6` (comb pilots + ZeroPN-safe preliminary data-interference cancellation + Gävert Eqs. (18)/(28) exact residual data-covariance weighting $\mathbf{\Sigma}_{\mathrm{res}}^{-1}$ + symmetric 6 init steps) AND `AFDM_Gavert_Guard_1Step` (1-step first-order Bayesian PCA on EP-AFDM guard).
  5. Mandatory regimes `R4_SingleFrameBlind_3e3` (zero training frame, 100% single-frame blind) and `R5_PNTrain_30dB_3e3` (training frame itself corrupted by independent dual-end Wiener PN).
  6. Exact guard-band covariance-corrected analytical lumped floor bound $\sigma_{\mathrm{irred,lump,cov}}^2$ verified against Monte Carlo across 3 realistic multipath fractional-Doppler settings (zero fitted parameters).
  7. `[放宽TWC]` compliance: OFDM is REMOVED from `PASS_PRIMARY`; single-knob `OFDM_c1=0_SingleKnob_Sym6` (exact same 72-bin window budget `[220:292]`, same warm-start, same 6 init + 6 outer; only toggling `c1` to 0) is recorded in `SCOPE_READOUTS` purely to verify non-triviality against `A3-3a`.

## Pre-Registered `PASS_PRIMARY` (2 Clauses — Both Must Be True)

1. **`P1_FLOOR_AND_LOCKLOSS_BREAK`** (*Hypothesis*: AFDM single-pilot DAFT delay separation + exact projected 6-step PCA dual-end GN removes the high-SNR error floor and sharply lowers lock-loss rate under 100% blind reception; *Falsification*: if any sanity gate fails or any published/direct-port rival matches within margin, the floor-breaking claim is refuted):
   - Startup & ZeroPN sanity gates: `fd_jacobian_rel_err < 1e-6`, `leak_n512_obs72_db < -25.0`, `leak_n256_obs38_db < -25.0`, and on `R0_ZeroPN_30dB` (24 fr) ALL blind AFDM arms (`AFDM_Uncomp`, `AFDM_Xu_LumpPCA_Sym6`, `AFDM_Gavert_Comb_CovDIC6`, `AFDM_Gavert_Guard_1Step`, `AFDM_EP_Dual_Sym6`) achieve `SER < 1e-3`.
   - `R2_N512_30dB_3e3` (80 fr): `AFDM_EP_Dual_Sym6` beats `AFDM_Xu_LumpPCA_Sym6` by `>= 10x`, beats `AFDM_Gavert_Comb_CovDIC6` and `AFDM_Gavert_Guard_1Step` by `>= 5x` (all paired 95% CI lower bounds `> 0`), and cuts lock-loss rate (`SER > 5%`) by `>= 20` percentage points relative to ALL three rivals.
   - `R3_N512_45dB_3e3_Floor` (80 fr): `AFDM_EP_Dual_Sym6` beats ALL three rivals (`AFDM_Xu_LumpPCA_Sym6`, `AFDM_Gavert_Comb_CovDIC6`, and `AFDM_Gavert_Guard_1Step`) by `>= 10x` (full 1-decade high-SNR floor break; all paired 95% CI `> 0`).
   - `R4_SingleFrameBlind_3e3` (60 fr, zero training frame, zero cross-frame borrowing): `AFDM_EP_Dual_Sym6` beats `AFDM_Xu_LumpPCA_Sym6` by `>= 4x` (paired 95% CI `> 0`).
   - `R5_PNTrain_30dB_3e3` (60 fr, PN-corrupted training frame): `AFDM_EP_Dual_Sym6` beats `AFDM_Xu_LumpPCA_Sym6` and `AFDM_Gavert_Comb_CovDIC6` by `>= 5x` (paired 95% CI `> 0`).

2. **`P2_ANALYTICAL_FLOOR_BOUND`** (*Hypothesis*: The zero-parameter Hermitian-optimal guard-band covariance analytical lumped floor accurately predicts Monte Carlo irreducible interference across distinct multipath channels, and dual-end AFDM beats even the data-independent lumped genie; *Falsification*: if any analytical bound differs by `> 0.5 dB` or dual-end fails to clear the lumped genie by `>= 4x`, the bound/floor-breaking mechanism is refuted):
   - Across all 3 realistic fractional-Doppler multipath settings (`L=12 N=512`, `L=16 N=512`, `L=8 4-path N=256`), `|ana_cov_db - mc_indep_db| <= 0.5 dB` (using exact row-sum optimal weights $\mathbf{v} = \mathbf{W}\mathbf{1}/(\mathbf{1}^H\mathbf{W}\mathbf{1})$).
   - On BOTH `R2` and `R3`, `AFDM_EP_Dual_Sym6` beats the data-independent lumped genie `AFDM_LumpOrac_Indep` by `>= 4x` (paired 95% CI `> 0`).

## `SCOPE_READOUTS` (Diagnostic & Boundary Reporting, Non-Gating)
- `R1_N512_30dB_2e3` (60 fr): lower-linewidth operating point (`2e-3`).
- `R6_Rand4_N256_30dB_3e3` (60 fr): random closely-spaced 4-path channel generality.
- `R3.OFDM_c1=0_SingleKnob_Sym6`, `R3.OFDM_c1=0_SameMask_Sym6` & `R3.OFDM_c1=0_DualOrac`: single-knob `c1 -> 0` non-triviality readouts (identical `phi_cpe` warm-start as `AFDM_EP_CPE_GN6`, same 6 init + 6 outer, reporting BOTH OFDM-centered 72-bin `[220:292]` AND exact identical index mask `[196:268]`).
- `AFDM_EP_CPE_GN6` vs `AFDM_EP_Dual_Sym6`: honest attribution ablation separating AFDM DAFT guard delay separation vs per-path constant-envelope MRC warm-start.
- Per-frame energy ratio (including CPP/CP) mean & std across all regimes.
