# Pre-Registered Predictions (v2 — Post-Advisory-Audit Strengthening): `I-20261125-m01`

- **Date / Runner**: 2026-11-25, runner `m` (`gemini-4-neon`).
- **Audit Trace**: Built directly in response to `gemini-4-hydrogen-high` Rule-5 advisory review (`ADVISORY_REVISE`, logged in `I-20261125-m01.md`), leaving frozen v1 (`PREDICTIONS_m_r10_01.md` + `summary_m_r10_01.json`) completely intact and running an independently pre-registered v2 strengthening run:
  1. **Eliminates `45 dB > 30 dB` inversion in `AFDM_LumpOracCent`**: Upgrades `AFDM_LumpOracCent_OptReg` to an omniscient double-oracle knowing BOTH exact centroid phase $\boldsymbol{\phi}_{\mathrm{lopt}}$ AND exact per-frame lumped-model mismatch variance $\sigma_{\mathrm{mism}}^2 = \frac{1}{N}\|\mathbf{y} \odot e^{-j\boldsymbol{\phi}_{\mathrm{lopt}}} - \mathbf{H}_{\mathrm{circ}}\mathbf{s}\|^2$ (while also keeping `AFDM_LumpPrac` strengthened with blind residual-based final-pass mismatch regularization `max(sig2_use, res_lump)`).
  2. **Symmetric Matched-Projection Stage-1 for OFDM Controls**: Upgrades `OFDM_FixedChirp_Dual` to exact matched-projection Stage-1 Dual-End GN (`Pi_guard(yhat_full)`, symmetric with AFDM's `init_afdm_subband_matched_proj`); retains the strictly stronger TD-regularized `OFDM_Comb_Dual` (and records `OFDM_Comb_FDMP` to document that FD comb projection degrades under comb PN-ICI aliasing).
  3. **Full Multi-Regime Banded OAMP Validation**: Runs `AFDM_SubDual_Banded` (`oamp_cyclic_banded` + `gn_dual_banded`, zero dense $N\times N$ formations) directly across **ALL 1,000 paired frames** of `R1–R6c`, not just 1 frame of `R7`, and saves every reported number directly inside `summary_m_r10_01_v2.json`.
  4. **Adds `R3b (N=512, 45 dB, sig_pn=4e-3, 100 fr)`** (still $< 0.5\times$ `Mirabella Fig. 9`'s $\sigma_\phi^2=10^{-2}$) alongside `R3 (45 dB, 3e-3)` to verify monotonic high-SNR floor scaling of `LumpOracCent_OptReg` under zero diversity confound.

## Pre-Registered Falsifiable Verdicts (`verdicts`, v2)
1. **`P1_V2_BREAKS_OPTREG_LUMP_30DB`**:
   - On `R1 (N=512, 30 dB, 2e-3, 100 fr)`: `AFDM_SubDual_DualGN` beats `AFDM_LumpPrac` by `>= 8x` AND beats double-omniscient `AFDM_LumpOracCent_OptReg` by `>= 2x` (paired 95% CI lower bound `> 0`).
   - On `R2 (N=512, 30 dB, 3e-3, 100 fr)`: `AFDM_SubDual_DualGN` beats `AFDM_LumpPrac` by `>= 10x` AND beats double-omniscient `AFDM_LumpOracCent_OptReg` by `>= 4x` (paired 95% CI lower bound `> 0`).
2. **`P2_V2_HIGH_SNR_MONOTONIC_NO_CONFOUND`**:
   - On BOTH `R3 (45 dB, 3e-3, 100 fr)` and `R3b (45 dB, 4e-3, 100 fr)`: `AFDM_DualOrac < 1e-3` AND `OFDM_DualOrac < 1e-3` (zero diversity confound).
   - Monotonicity check: `R3.AFDM_LumpOracCent_OptReg < R2.AFDM_LumpOracCent_OptReg` (zero unphysical inversion!).
   - On `R3`: `AFDM_SubDual_DualGN` beats `AFDM_LumpOracCent_OptReg` by `>= 2x` (paired 95% CI `> 0`), beats `AFDM_LumpPrac` by `>= 10x`, and beats ALL matched-net-rate OFDM controls (`OFDM_Comb_Dual`, `OFDM_FixedChirp_MP`, `OFDM_TDPre_Dual`) by `>= 15x`.
   - On `R3b`: `AFDM_SubDual_DualGN` beats `AFDM_LumpOracCent_OptReg` by `>= 3x` (paired 95% CI `> 0`), beats `AFDM_LumpPrac` by `>= 8x`, and beats ALL OFDM controls by `>= 15x`.
3. **`P3_V2_CAUSAL_SUBBAND_ABLATION`**:
   - Under the exact same fixed Dual-End GN-OAMP solver on `R1` and `R2`, `AFDM_SubDual_DualGN` beats BOTH `AFDM_CPE_DualGN` and `AFDM_NoDemuxGuard_DualGN` by `>= 10x`.
4. **`P4_V2_IMPCSI_AND_RAND4`**:
   - On `R4 (N=512, 30 dB, CSI NMSE=1e-3, 100 fr)`: `AFDM_SubDual_DualGN` beats `AFDM_LumpOracCent_OptReg` by `>= 3x`, `AFDM_LumpPrac` by `>= 8x`, and all OFDM controls by `>= 15x`.
   - On `R5 (N=256, random closely-spaced 4-path, 30 dB, 3e-3, 200 fr)`: `AFDM_SubDual_DualGN` beats `AFDM_LumpOracCent_OptReg` by `>= 3x`, `AFDM_LumpPrac` by `>= 8x`, and all OFDM controls by `>= 10x`.
5. **`P5_V2_GUARDB_AND_EXTREME`**:
   - `R6a (Zero PN, 100 fr)`: `AFDM_SubDual_DualGN <= AFDM_NoPN_Ref + 1e-3` and `AFDM_SubDual_Banded <= AFDM_NoPN_Ref + 1e-3`.
   - `R6b (Rx-Only PN, 100 fr)`: `AFDM_SubDual_DualGN <= AFDM_LumpPrac + 5e-3`.
   - `R6c (Extreme PN 6e-3, 100 fr)`: `AFDM_SubDual_DualGN` beats `AFDM_LumpOracCent_OptReg` by `>= 2.5x` and strictly beats `AFDM_SubMRC_DualGN` (paired 95% CI `> 0`).
6. **`P6_V2_MULTIFRAMED_BANDED_FIDELITY_AND_SPEEDUP`**:
   - Across `R1, R2, R3, R4, R5`, `|AFDM_SubDual_Banded - AFDM_SubDual_DualGN| <= 3.5e-3` (full 600-frame multi-regime accuracy equivalence of banded Woodbury OAMP!).
   - On `R7 (N=512, single-core full end-to-end timing)`: `speedup >= 5.0x` and `|banded_ser - dense_ser| <= 2e-3`.
7. **`PASS_PRIMARY_V2`**: `P1_V2 && P2_V2 && P3_V2 && P4_V2 && P5_V2 && P6_V2`.
