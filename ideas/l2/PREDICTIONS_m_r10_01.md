# Pre-Registered Predictions: `m-r10-01` (AFDM 双端收发相噪的导频子带解耦与带状联合检测)

- **Date / Runner**: 2026-11-25, runner `m` (`gemini-4-neon`), A2 target (`Sui TCOM'26 Eqs.(21)-(22) & Fig. 4`, `Mirabella JSAC'26 Eq.(40) & Fig. 9`, `McWade 2605.14720 Eq.(5)`, `Tasin 2610.33672`, `Chaiyasoonthorn SPL'26 Eq.(2)`).
- **Governance Note (Rule 5)**: `Sol` 6/6 returned `REVISE` (confirming reproducibility of N=512 numbers & requesting fixed-solver ablation, matched-net-rate OFDM wideband-preamble + fixed-slope chirp controls, high-SNR floor check, zero-PN & phase-oracle references on both waveforms, zero-`np.unwrap`, matched subband projection, and true end-to-end runtime). Because `Sol` pre-card gate cap (6/6) is exhausted, this card stays strictly at `layer: L1` in `待审` pending `Sol` final sign-off; this 100–200-frame `deinlab` run pre-collects the complete falsifiable evidence requested by `Sol` 6/6.

## Frozen Protocol & Parameters
- **Physical Model**: Exact non-wrapping CPP linear-convolution dual-end Wiener phase noise $\mathbf{y} = \operatorname{diag}(e^{j\boldsymbol{\phi}_R}) \mathbf{H}_{\text{lin}} \operatorname{diag}(e^{j\boldsymbol{\phi}_T}) \mathbf{P}_{\text{CPP}} \mathbf{A}^H \mathbf{x} + \mathbf{w}$, $\boldsymbol{\phi}_T \in \mathbb{R}^{N+L_{\text{cpp}}}$ continuous across $[-L_{\text{cpp}}, \dots, N-1]$, $\sigma_T^2 = \sigma_R^2 = \frac{1}{2}\sigma_{\text{PN}}^2$, $\nu_p \sim \mathcal{U}[-0.5, 0.5]$.
- **Matched Net Rate & Total Symbol Power $N$**:
  - `N = 512`: `122` pilot/guard bins (`23.8%` overhead, `390` 64-QAM data symbols), $2Nc_1 = 3$, coprime delays $l = [0, 7, 16]$ ($\gcd(7,16)=1$, zero periodic residue ambiguity), $L_{\text{cpp}} = 16$.
  - `N = 256`: `82` pilot/guard bins (`32.0%` overhead, `174` 64-QAM data symbols), $2Nc_1 = 2$, random non-uniform closely-spaced 4-path multi-cluster $l = [0, \text{rand}\{1,2\}, \text{rand}\{7..10\}, \text{rand}\{14..16\}]$ (PDP `[0.22, 0.18, 0.30, 0.30]`) and coprime $l = [0, 7, 16]$.
- **Fixed Solver & Matched Baselines**:
  - Identical 10-outer-iter annealed Dual-End Banded GN (`n_gn=3`) $\rightleftarrows$ OAMP (`n_iter=8`, `n_iter=12` final) across all dual-end arms.
  - Baselines: `AFDM_NoPN_Ref`, `AFDM_CPE_DualGN` (no subband init), `AFDM_NoDemuxGuard_DualGN` (no per-path separation), `AFDM_LumpPrac` (`Bittner'07` iterative soft-OAMP + lumped GN), `AFDM_LumpOracCent` (centroid-optimal lumped phase oracle), `AFDM_DualOrac`, plus matched-net-rate `OFDM_NoPN_Ref`, `OFDM_Comb_Dual` (scattered Comb-PTRS), `OFDM_TDPre_Dual` (wideband ZC TD preamble dual-end fit), `OFDM_FixedChirp_Dual` (`Li-Wang'24` fixed-slope chirp in guard subcarriers), and `OFDM_DualOrac`.
- **Proposed Methods**:
  - `AFDM_SubMRC_DualGN`: Zero-`np.unwrap` complex-phasor per-path DAFT subband MRC init with exact Gibbs-free interior anchoring & Wiener MMSE constant boundary extrapolation over the circular-filter edge zone $M_e = L_{\text{cpp}}$ (preventing circular wrap-around Gibbs bias of non-periodic Wiener phase + non-wrapping CPP; same clean `phi_mrc` is also fed to `AFDM_LumpPrac` for strict fairness) + non-wrapping banded Dual-End GN-OAMP (with adaptive high-SNR OAMP variance floor `v_fl = min(5e-4, max(0.5*sigma2, 1e-6))` applied identically across all arms and oracles).
  - `AFDM_SubDual_DualGN`: Same + Gibbs-interior-masked matched-projection Stage-1 subband dual-split `(pr0, pt0)` init (for extreme $\sigma_{\text{PN}}^2 = 6\times 10^{-3}$).
  - `AFDM_SubAuto_DualGN`: Blind MAP-objective selector picking between `SubMRC_DualGN` and `SubDual_DualGN` using strictly blind residual (zero side info).

## Pre-Registered Falsifiable Predictions (`verdicts`)
1. **`P1_BREAKS_LUMPED_ORACLE_30DB`** (Primary): On `R1 (N=512, 30 dB, sig_pn=2e-3, 100 frames)` and `R2 (N=512, 30 dB, sig_pn=3e-3, 100 frames)`, `AFDM_SubMRC_DualGN` achieves **$\ge 4\times$ lower SER than `AFDM_LumpOracCent`** AND paired 95% CI lower bound $> 0$ (strictly breaks the theoretical hard floor of all lumped-PN receivers).
2. **`P2_HIGH_SNR_FLOOR_AND_NO_DIVERSITY_CONFOUND`** (Primary): On `R3 (N=512, 45 dB, sig_pn=3e-3, 100 frames)`, `OFDM_DualOrac < 2e-3` (confirming diversity confound is removed at high SNR), `AFDM_LumpOracCent > 1.5e-2` (proving irreducible high-SNR lumped floor), AND `AFDM_SubMRC_DualGN` beats `AFDM_LumpOracCent` by **$\ge 4\times$** AND beats **ALL THREE** matched-net-rate OFDM controls (`OFDM_Comb_Dual`, `OFDM_TDPre_Dual`, `OFDM_FixedChirp_Dual`) by **$\ge 10\times$** (with paired 95% CIs strictly $> 0$).
3. **`P3_CAUSAL_SUBBAND_ABLATION`** (Primary): Under the exact same fixed Dual-End GN-OAMP solver on `R1` and `R2`, `AFDM_SubMRC_DualGN` beats BOTH `AFDM_CPE_DualGN` and `AFDM_NoDemuxGuard_DualGN` by **$\ge 5\times$** (proving AFDM per-path subband demuxing is causally necessary to enter the global basin).
4. **`P4_RANDOM_MULTICLUSTER_AND_IMPCSI`** (Primary):
   - On `R4 (N=512, 30 dB, sig_pn=2e-3, CSI NMSE=1e-3, 100 frames)`, `AFDM_SubMRC_DualGN` beats `AFDM_LumpPrac` by **$\ge 2\times$** and beats `OFDM_Comb_Dual` by **$\ge 3\times$**.
   - On `R5 (N=256, random closely-spaced 4-path multi-cluster, 30 dB, sig_pn=3e-3, 200 frames)`, `AFDM_SubMRC_DualGN` beats `AFDM_LumpOracCent` by **$\ge 3\times$** and beats all three OFDM controls by **$\ge 5\times$**.
5. **`P5_GUARDB_AND_EXTREME_DUAL`** (Guard-b):
   - On `R6a (Zero-PN, 100 frames)`, `AFDM_SubMRC_DualGN <= AFDM_NoPN_Ref + 1e-3` (zero degradation).
   - On `R6b (Rx-Only PN sig_r=3e-3, sig_t=0, 100 frames)`, `AFDM_SubMRC_DualGN <= AFDM_LumpPrac + 5e-3` (no harmful overfitting when Tx PN is absent).
   - On `R6c (Extreme PN sig_pn=6e-3, N=256, 100 frames)`, `AFDM_SubDual_DualGN` beats `AFDM_LumpOracCent` by **$\ge 3\times$** and improves over `AFDM_SubMRC_DualGN` (demonstrating Stage-1 matched-proj dual-split value in extreme PN).
6. **`P6_END_TO_END_BANDED_SPEEDUP`** (Complexity): On `R7 (N=512, single-core full end-to-end 10-outer-iter timing including Stage-1 init + Banded OAMP + Banded GN vs Dense SVD OAMP + Dense GN)`, end-to-end speedup is **$\ge 4\times$** while banded SER stays within `2e-3` of dense SVD SER.
7. **`PASS_PRIMARY`**: `P1 && P2 && P3 && P4 && P5 && P6`.
