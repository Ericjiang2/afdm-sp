# Pre-Registration for `I-20261125-h02` (`[高要求] [轨B-ISAC]` · Round 11)

- **Card ID**: `I-20261125-h02` (`跨块信道老化下路径解耦MIMO-AFDM通感预编码`)
- **Ledgers**: **Floor-Breaking (`破壁账`, protocol bar: `≥ 1.0 dB` SNR win or `≥ 1` decade floor reduction at matched zero added overhead)** + **Cross-Layer / ISAC Inversion (`跨层/通感倒挂账`, protocol bar: `≥ 0.8 dB` win over standalone-optimal / uncoupled cascade while preserving radar detection)**
- **Script**: `ideas/l2/h_l2_r11_h02.py`
- **Execution Environment**: `deinlab`, `conda activate AFDM` (`/home/guoyikun/.conda/envs/AFDM/bin/python`), `OMP_NUM_THREADS=1`, `multiprocessing.Pool(8)` (`8` CPU workers strictly `≤ 8` core cap).
- **Seed Isolation**: Dev calibration (`dev_smoke_h02_revise.py`, `smoke` seeds `900..999`, `1000..9999`) is strictly disjoint from unseen formal L2 test seeds **`SEED_BASE_Z0 = 200000`**, **`SEED_BASE_Z1 = 300000`**, and **`SEED_BASE_S2 = 400000`**.
- **Explicit Signaling & Zero-Side-Info Contract (per `Sol` Pre-L2 Audit Item 1–3)**:
  - All blind arms (`Prop_BeamMatchedDualISAC_AFDM`, `OFDM_Comb_JointWLS_DualISAC`, `OFDM_HillClimb_JointWLS_ISAC`, `ExtrapBlockRZF_*`, `OFDM_ExtrapBlockRZF`, `DDAM_CleanFullEq_AFDM`, `Abl_Aonly_PathNull_NoTrack_AFDM`, `Abl_Bonly_MRT_WithTrack_AFDM`) execute **100% pure UE-local reception** from `yk` and public frame constants alone (`ZERO` BS-side `est_s1`, `W_beams`, or `sig2_ul_hat` passed to UE).
  - *Single explicit generosity exception in favor of baseline*: `Liu26_PerBinWMMSE_Aged_AFDM` (`Rang Liu & Schober 2026` Sec. IV-B Eq. 33) optimizes 40 distinct per-bin beamformers `W_bin[k,m]` that cannot be learned from 1 pilot symbol, so this adversary baseline is generously granted unpriced BS-to-UE signaling of its Stage-1 MMSE combiner `U_rx_liu[q][k]` (`2,560` complex scalars per user per block, `7,680` across `K=3` users per block in favor of the baseline; pilot subtraction still uses pure UE-blind `obs_af` estimation).
  - Exact per-block expected transmit energy $\mathbb{E}_{d_{\text{pay}}}[\|\mathbf{S}_{\text{tot}}[q]\|_F^2] \equiv P_{\text{tot}} = 64.0$ (accounting for pilot, deterministic reference `Dt[0]`, and `DDAM` per-block path phases) is enforced identically across every arm and block.

---

## 1. Dev-Set Dispersion Calibration & Sample Size Justification (Red Line 5)

From the independent dev-set calibration (`dev_smoke_h02_revise.py`, `n_pos=20` dynamic scenes at `SNR=28 dB`, `nu_max=0.85, sig_nu=0.025, sig_th=0.8 deg`, plus `n_pos=15` static scenes):
1. **Cross-Waveform Paired `2×2 DiD` (`SER_best_OFDM - SER_Prop_AFDM`)**:
   - Dev point estimate: `Δ_Z1 = +0.15668` (`sd_Z1 = 0.04047`), `Δ_Z0 = -0.00011` (`sd_Z0 = 0.00023`), `sd_DiD ≈ 0.0405`.
   - Chosen L2 sample size: **`N_pos_Z0 = 64`**, **`N_pos_Z1 = 144`** independent multi-user channel scenes (`exact multiples of 8 workers`; `N_cal_Z0 = N_val_Z0 = 120`, `N_cal_Z1 = N_val_Z1 = 320`, `N_pos_S2 = 48`).
   - Expected 95% CI half-width at `N_pos_Z1 = 144`: `1.96 * 0.0405 / sqrt(144) = 0.0066 ≤ 0.25 * 0.080 = 0.0200`.
2. **Floor-Breaking `+2.0 dB` Cross-SNR Headroom (`SER_best_OFDM@28dB - SER_Prop_AFDM@26dB >= 0.050`) + Paired Geometric Ratio at `28 dB` (`>= 3.20×`)**:
   - Dev paired log-ratio `ln(SER_OFDM_Comb@28dB / SER_Prop_AFDM@28dB)` had `mean = 1.6871` (`5.40×`), `sd = 0.4849`. At `N_pos_Z1 = 144`, expected log half-width is `1.96 * 0.4849 / sqrt(144) = 0.0792 ≤ min(0.25 * ln(3.20), ln(1.25)) = 0.2231`.
   - Evaluating `Prop_BeamMatchedDualISAC_AFDM` at **`SNR = 26.0 dB` (`2.0 dB` LOWER SNR, `2×` stricter than the `1.0 dB` Floor-Breaking ledger bar!)** against `best_OFDM` at **`28.0 dB`**: expected 95% CI half-width at `N_pos_Z1 = 144` is `1.96 * 0.042 / sqrt(144) = 0.0069 ≤ 0.25 * 0.050 = 0.0125`.
3. **Radar Unified QR-Projected Equal-`Pfa` (`Pfa_target = 0.05`) `LocBlindPd` Gain (`>= +0.55`, Newcombe-Wilson Paired Binary CI) & Two-Way Ablations (`< 80%`)**:
   - Calibration/validation sample sizes: **`N_cal = 320`**, **`N_val = 320`** independent target-free CPIs (`SE = 1.22%` at `Pfa = 0.05`).
   - Paired binary `LocBlindPd` difference `Prop(Q=16) - Short8xQ2` on `N_pos_Z1 = 144` is evaluated using **Newcombe's Method 10 paired Wilson score 95% CI** (non-degenerate even at `100% vs 0%`, where conservative Wilson half-width is `0.0369 ≤ 0.25 * 0.55 = 0.1375`).
   - Zero-leak `Abl_Aonly` and `Abl_Bonly_MRT` bootstrap 95% CI half-widths at `N_pos_Z1 = 144` are `≤ 0.050 = 0.25 * (1.0 - 0.80)`, and `SER_Bonly_MRT - SER_Prop` / `SER_Aonly - SER_Prop` half-widths are `≤ 0.008 ≤ 0.25 * 0.080 = 0.020`.
   - **All realized half-width bounds (`<= 25%` of threshold distance) are explicitly gated into `P1` and `P2` in `h_l2_r11_h02.py`!**

---

## 2. Primary Verdicts (`PASS_PRIMARY` — ALL sub-clauses + half-width gates + hygiene gates must hold!)

`verdicts.PASS_PRIMARY` is `true` **if and only if BOTH `P1` and `P2` hold** (including: all 8 full-CPI communication arms `{Prop, OFDM_Comb, OFDM_HillClimb, OFDM_Extrap, Liu26, ExtrapAged, DDAM, Abl_Aonly}` satisfy `Z=0` static mean `SER < 0.010`; `Prop` empirical `val_Pfa_blind` in `[0.015, 0.095]` at `Pfa_target = 0.05`; and **every** primary criterion's realized 95% CI half-width is `<= 25%` of its threshold distance):

1. **`P1` (`[高要求]` Cross-Waveform `2×2 DiD` & `≥ 2.0 dB` Floor-Breaking Advantage over Strongest Equal-Overhead `OFDM`)**:
   - `CI95_lower(DiD_SER_vs_best_OFDM) >= 0.080` **AND** `did_ci_hw <= 0.020`, **AND**
   - `CI95_lower(geom_ratio_SER_best_OFDM_28dB_over_Prop_28dB) >= 3.20` **AND** `log_half_width <= ln(1.25)`, **AND**
   - `CI95_lower(SER_best_OFDM_28dB - SER_Prop_AFDM_26dB) >= 0.050` **AND** `ci95_half_width <= 0.0125`.

2. **`P2` (ISAC Coherent-CPI Deadlock Resolution & Two-Way `A ⇄ B` Coupling Necessity)**:
   - `CI95_lower(SER_rival_28dB - SER_Prop_AFDM_28dB) >= 0.150` **AND** `ci95_half_width <= 0.0375` for EVERY `rival in {Liu26_PerBinWMMSE_Aged_AFDM, ExtrapBlockRZF_Aged_AFDM, DDAM_CleanFullEq_AFDM}`, **AND**
   - `Newcombe_CI95_lower(LocBlindPd_Prop_Q16 - LocBlindPd_Short8xQ2) >= 0.55` **AND** `ci95_half_width <= 0.1375` under unified QR clutter-projected RD scoring (`identical fn_clut, identical 1e-6 QR rank threshold, zero peak mask, total energy ratio proj_keep_db`), **AND**
   - `CI95_upper(recovery_Aonly) < 0.80` (`hw <= 0.050`), `CI95_upper(recovery_Bonly_MRT) < 0.80` (`hw <= 0.050`), `CI95_lower(SER_Aonly - SER_Prop_AFDM) >= 0.080` (`hw <= 0.020`), and `CI95_lower(SER_Bonly_MRT - SER_Prop_AFDM) >= 0.080` (`hw <= 0.020`).

---

## 3. Diagnostic & Boundary Readouts (`SCOPE_READOUTS` — descriptive, not AND-chained into `PASS_PRIMARY`)

1. **`True-H` Attribution Readout**: `Oracle_TrueEffH_AFDM` vs `Oracle_TrueEffH_OFDM_Comb` `SER` at `Z=0` and `Z=1`.
2. **Pure CSI-Aging Isolation Readout**: Paired `ExtrapBlockRZF_UnagedQ0_AFDM` vs `ExtrapBlockRZF_Aged_AFDM` vs `Prop_BeamMatchedDualISAC_AFDM`.
3. **Radar Total Target Energy Retention (`proj_keep_db`)**: `10 * log10(sum(tot_proj_e) / sum(tot_raw_e))` for `Q=16` vs `8×(Q=2)`.
4. **Second Antenna/User Scaling Regime (`Nt = 16, K = 4, Pk = 3`, `SNR = 26 dB`, `N_pos = 48`)**.
