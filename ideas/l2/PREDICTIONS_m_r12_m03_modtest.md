# Pre-Registered Modified-Method New-Seed Test — `I-20261125-m03` (`[放宽TWC] [轨A-纯通信]`, v3)

> **Important Label (Eric 2026-11-25 Ruling)**: Because this run introduces a new algorithmic component in `R4` (zero-parameter common-mode linear drift separation `nu_raw = nu_cm + nu_rel` with soft gauge re-centering inside `blind_single_frame_init`), this document, the card, and `runs-m.md` strictly label this run as a **「修改方法后的新种子检验」（Modified-Method New-Seed Test）** — NEVER as a "confirmatory run (确证)". Per Eric's ruling, if `PASS_PRIMARY == false`, card `I-20261125-m03` is immediately closed as `status: killed` and the `m01 -> m02 -> m03` chain terminates permanently.

- **Card**: `I-20261125-m03` (`--parent I-20261125-m02`) — *全盲 AFDM 双端相噪含噪训练校准与平层界*
- **Script**: [`ideas/l2/l2_m_r12_m03_modtest.py`](l2_m_r12_m03_modtest.py) (derived from frozen [`l2_m_r11_m03_dual_pn.py`](l2_m_r11_m03_dual_pn.py), which is kept unmodified as historical evidence).
- **Reproducible Dev Sizing Script**: [`ideas/probes/m_dev_r12_m03_sizing.py`](../probes/m_dev_r12_m03_sizing.py).
- **Approved Method Modification (Strictly Bounded & 100% Symmetric Across ALL Blind Arms)**:
  - **ONLY** `blind_single_frame_init(Y_a, sys_cfg)` (used in `R4_SingleFrameBlind_3e3` and `R0_SingleFrame_ZeroPN`, shared identically by ALL five EP-AFDM blind arms: `AFDM_Uncomp`, `AFDM_Xu_LumpPCA_Sym6`, `AFDM_Gavert_Guard_1Step`, `AFDM_EP_CPE_GN6`, `AFDM_EP_Dual_Sym6`) adds **zero-parameter energy-weighted common-mode linear drift separation (`nu_raw = nu_cm + nu_rel`) + zero-parameter soft gauge re-centering**:
    1. Pass 1 extracts unclipped per-path apparent linear slopes `nu_raw[i] = -sl[i] * N / (2*pi)` and path energies `E_sub[i]`.
    2. Computes zero-parameter energy-weighted common-mode linear drift `nu_cm = sum_i w_i * nu_raw[i]` (`w_i = E_sub[i] / sum_j E_sub[j]`) and clipped relative Dopplers `nu_rel[i] = clip(nu_raw[i] - nu_cm, -0.49, 0.49)`.
    3. Zero-parameter soft gauge re-centering retains the legal in-range common Doppler inside channel Dopplers: `nu_cm_ch = clip(nu_cm, -0.49 - min(nu_rel), 0.49 - max(nu_rel))`, `nu_h = nu_cm_ch + nu_rel`. Thus: (a) under strong Wiener linear drift, inter-path relative Dopplers `nu_rel` avoid asymmetric `±0.49` clipping distortion from the common-mode offset, and excess drift `nu_cm - nu_cm_ch` is absorbed into `phi_mrc`; (b) under zero PN (`R0_SingleFrame_ZeroPN`, where relative slopes `nu_raw - nu_cm` remain clipped to `[-0.49, 0.49]`), baseline hygiene is gated empirically by requiring ALL FIVE EP-AFDM arms (including `AFDM_Uncomp`) plus `AFDM_EP_Dual_Sym6_NoCMSep` to achieve measured `SER < 1e-3`.
    4. Pass 2 derotates each path by the common-mode plus clipped relative slope `(nu_cm + nu_rel[i])` to align inter-path complex gain phases `h_h[i]`, then performs coherent MRC with `nu_h = nu_cm_ch + nu_rel` so `phi_mrc` absorbs excess drift `nu_cm - nu_cm_ch`, followed by unchanged `refine_ch_on_pilot_obs` and blind residual noise estimation.
  - **Same-frame single-mechanism paired control (`AFDM_EP_Dual_Sym6_NoCMSep`)**: in `R4_SingleFrameBlind_3e3` (and `R0_SingleFrame_ZeroPN`), the exact Round-11 legacy `blind_single_frame_init_legacy` is run on the IDENTICAL received frame `y_a` feeding the IDENTICAL `3+3` GN + `6`-outer `EP_Dual` backend, isolating the pure single-mechanism causal gain of common-mode separation.
  - `AFDM_Gavert_Comb_CovDIC6` in `R4` continues to use its own comb-pilot blind estimator from `y_c` (`nu_comb = 0`, zero cross-frame borrowing from `y_a`); because Comb-AFDM has no guard band and no training frame in `single_frame` mode, it cannot blindly estimate fractional Doppler without training (`R0_SingleFrame_ZeroPN` non-zero SER disclosed transparently; it is gated healthy `SER = 0.0000` in `R0_ZeroPN_30dB` and excluded from `P1_R4`).
  - `R0_ZeroPN_30dB, R1, R2, R3, R5, R6` receiver logic is **100% IDENTICAL** to `l2_m_r11_m03_dual_pn.py` (zero simulator truth passed into any blind receiver).

## Fresh Zero-Overlap Seed Namespaces (`+100000` & Independent `P2` Seeds)

- Previous `m02` L2 seeds: `2026112511 .. 2026172570`
- Previous `m03` L2 seeds: `2027000001 + idx_r * 10000 + f` (`2027000001 .. 2027060060`) and `P2` bound seed `2026112599`
- Independent Round-12 dev-set sizing seeds (`m_dev_r12_m03_sizing.py`): `10000001 .. 10030060`
- Local `--smoke` seeds: receiver frames `2029000001 + idx_r * 10000 + f`, `P2` bound `BOUND_SEED_BASE = 2029200001`
- **Official Round-12 Modified-Method New-Seed Test**:
  - Receiver frames (`8` regimes, `idx_r = 0..7`): `2027100001 + idx_r * 10000 + f` (`2027100001 .. 2027170060`, **`1,856`** distinct seeds)
  - `P2` analytical bound MC (`3` cases, `idx_c = 0..2`): **`BOUND_SEED_BASE = 2027200001`**, strictly decoupled per-case channel seed `2027200001 + idx_c * 10000 + 1` and MC seed `2027200001 + idx_c * 10000 + 2` (channel draws invariant to `n_mc` and **0% overlap** with Round-11 `2026112599`, `--smoke`, and receiver frames!).

## Red Line #5 Independent Dev-Set Dispersion & Sample-Size Sizing (`DEV_BASE = 10000001`, `n_dev = 60` / regime + `R3` exact linearized dispersion)

Target per Red Line #5 (`FUNNEL.md`): every ratio/difference primary criterion must have 95% CI halfwidth `<= 25%` of its threshold distance / expected effect scale (log-ratio `hw <= log(1.25) = 0.2231`, lock-loss diff `hw <= 5.0 pp = 25% * 20 pp`, zero-denominator linearized paired diff `D_i(M) = A_i - M*B_i` relative 95% CI `hw <= 0.2231 <= 0.25`, `P1_R4_CMSEP_MECH` linear paired SER diff `hw <= 25% * expected_effect_above_0 = 25% * 0.0185 = 0.004625`, and `P2` bound MC Fieller `hw <= 0.125 dB = 25% * 0.50 dB`), and every primary criterion is judged strictly by its **exact paired 95% CI lower bound** (`t_{n-1, 0.975}` exact integer-count `D_int = k_a - int(M)*k_b` linearized paired difference / exact Fieller), NEVER point estimates.

| Regime | Dev / Prior-Unchanged `EP_Dual` (LL) | Tightest Gated Rival Dispersion & Required `n` | Frozen Full `n_frames` | Projected 95% CI Halfwidth |
|---|---:|---|---:|---|
| `R0_ZeroPN_30dB` | `0.0` | Startup zero-PN hygiene gate (5 blind arms `SER < 1e-3`) | **`24`** | Hygiene gate |
| `R0_SingleFrame_ZeroPN` | `0.0` | Single-frame zero-PN hygiene gate (ALL 5 EP arms incl. `AFDM_Uncomp` + `NoCMSep` `SER < 1e-3`) | **`12`** | Hygiene gate |
| `R1_N512_30dB_2e3` | — | Non-gating readout | **`60`** | Non-gating |
| **`R2_N512_30dB_3e3`** | `1.676e-3 (0%)` | Dev `n=60`: ratio `log_hw_delta`: `Gav1St 0.502 (n=304)`, `GavComb 0.429 (n=222)`, `LumpOrac 0.411 (n=204)`, `Xu 0.384 (n=178)`; LL diff: `Gav1St 56.7±12.6 pp (n=381)`, `Xu 70.0±11.7 pp (n=329)` | **`400`** | `log_hw <= 0.194 <= 0.223`, `LL_hw <= 4.88 pp <= 5.0 pp` |
| **`R3_N512_45dB_3e3_Floor`** | `0.000e+00 (0%)` | Zero-denominator `D_i(M) = A_i - M*B_i = A_i` (unchanged `R3` algorithm, `summary_m_r11_m03.json` `n=80` relative 95% CI `hw/mean`: `Gav1St = 0.0309/0.0968 = 0.319 [n=164 for 0.223]`, `LumpOrac = 0.00460/0.01578 = 0.292 [n=137]`, `Xu = 0.00740/0.03307 = 0.224 [n=81]`, `GavComb = 0.0471/0.3586 = 0.131 [n=28]`; confirmed on dev `n=60` zero errors) | **`200`** | ALL 4 rivals `D_i(M)` relative 95% CI `hw <= 0.201 <= 0.223 <= 0.25` (max `0.2001`) |
| **`R4_SingleFrameBlind_3e3`** | `2.514e-3 (0%)` | Dev `n=60` (soft gauge re-centering): (1) `Xu = 6.32e-2` (`25.13x`, exact Fieller `[17.42, 44.73]`, Delta `log_hw_delta = 0.436`, Fieller log-hw `0.472`); (2) **`P1_R4_CMSEP_MECH` single-mech `NoCMSep = 2.10e-2 (6.7% LL)` vs `2.51e-3 (0% LL)` (`8.35x`, paired diff `+0.0185 ± 0.0179`, Student-t `sd = 0.06929`, threshold `0.0`, Red Line #5 25% budget `= 0.004625` -> required `n >= 865`)** | **`920`** | **`NoCMSep` paired diff Student-t `hw = 0.00448 <= 0.004625` (`24.2% <= 25%`)**; `Xu` exact Fieller `log_hw ≈ 0.111 << 0.223` |
| **`R5_PNTrain_30dB_3e3`** | `3.538e-3 (0%)` | Dev `n=60`: `GavComb 127.5x (log_hw_delta=0.338 -> n=138)`, `Xu 29.7x (log_hw_delta=0.318 -> n=122)` | **`180`** | `log_hw <= 0.195 <= 0.223` |
| `R6_Rand4_N256_30dB_3e3` | — | Non-gating readout | **`60`** | Non-gating |
| `P2` Analytical Bound MC | — | 3 settings, `n_mc = 400` each; exact Fieller dB `hw = 0.073–0.091 dB` (`<= 0.125 dB = 25% * 0.50 dB`) | **`400`** | Exact Fieller `hw <= 0.095 dB <= 0.125 dB` |

## Pre-Registered `PASS_PRIMARY` Clauses (Original Thresholds UNCHANGED; ALL Judged by Exact Paired 95% CI Lower Bounds)

For any paired ratio requirement `E[SER_rival] / E[SER_ours] >= M` (integer `M in {4, 5, 10}`), `paired_ratio_stats` computes exact integer error-count differences `D_int = k_rival - int(M) * k_ours` (eliminating IEEE-754 floating-point rounding at exact threshold equality) and passes iff:
1. `mean(D_int / Nd) - t_{n-1, 0.975} * SE(D_int / Nd) >= 0.0`, AND
2. `mean(SER_rival) - t_{n-1, 0.975} * SE(SER_rival) > 0.0`
(algebraically identical to exact paired Fieller 95% CI lower bound `R_lo >= M`, singularity-free even when `SER_ours == 0`). Diagnostic Fieller endpoints handle `A_q < 0` downward-opening parabolas (`[r_large, +inf)` when `r_small < 0 < r_large`, and explicit `fieller_is_disjoint = True, fieller_disjoint_set = [[0.0, r_small], [r_large, None]]` when `0 <= r_small < r_large`) and `0/0` indeterminate cases (`ratio_indeterminate = True`) exactly.

1. **`GATES_OK`**:
   - `fd_jacobian_rel_err < 1e-6`, `leak_n512_obs72_db < -25.0`, `leak_n256_obs38_db < -25.0`.
   - `R0_ZeroPN_30dB` (`24` fr, `prior_clean`): all five blind AFDM arms (`AFDM_Uncomp`, `AFDM_Xu_LumpPCA_Sym6`, `AFDM_Gavert_Comb_CovDIC6`, `AFDM_Gavert_Guard_1Step`, `AFDM_EP_Dual_Sym6`) achieve `SER < 1e-3`.
   - `R0_SingleFrame_ZeroPN` (`12` fr, `single_frame`): ALL FIVE EP-AFDM blind arms using `blind_single_frame_init` (`AFDM_Uncomp`, `AFDM_Xu_LumpPCA_Sym6`, `AFDM_Gavert_Guard_1Step`, `AFDM_EP_CPE_GN6`, `AFDM_EP_Dual_Sym6`) PLUS the legacy ablation arm `AFDM_EP_Dual_Sym6_NoCMSep` achieve `SER < 1e-3`.
2. **`P1_R2` (`R2_N512_30dB_3e3`, `400` fr)**:
   - `AFDM_EP_Dual_Sym6` paired 95% CI lower bound beats `AFDM_Xu_LumpPCA_Sym6` by `>= 10.0x`, `AFDM_Gavert_Comb_CovDIC6` by `>= 5.0x`, and `AFDM_Gavert_Guard_1Step` by `>= 5.0x`.
   - Lock-loss (`SER > 5%`) paired difference 95% CI lower bound (`mean(LL_rival - LL_ours) - t_{n-1,0.975} * SE >= 0.20`) cuts lock-loss by `>= 20` pp vs ALL three rivals (`Xu`, `GavComb`, `Gav1St`).
3. **`P1_R3` (`R3_N512_45dB_3e3_Floor`, `200` fr)**:
   - `AFDM_EP_Dual_Sym6` paired 95% CI lower bound beats ALL three rivals (`Xu`, `GavComb`, `Gav1St`) by `>= 10.0x`.
4. **`P1_R4` (`R4_SingleFrameBlind_3e3`, `920` fr, zero training frame, symmetric common-mode separation + soft gauge re-centering)**:
   - `P1_R4_XU_4X`: `AFDM_EP_Dual_Sym6` paired 95% CI lower bound beats `AFDM_Xu_LumpPCA_Sym6` by `>= 4.0x`.
   - `P1_R4_CMSEP_MECH` (same-frame single-mechanism paired control): `AFDM_EP_Dual_Sym6` strictly beats `AFDM_EP_Dual_Sym6_NoCMSep` (identical frame & identical `3+3` GN + `6`-outer backend, toggling ONLY common-mode separation OFF) with paired SER difference 95% CI lower bound `> 0.0` (Red Line #5 precision scale: `25%` of expected dev effect `0.0185` above threshold `0.0`, i.e. `hw <= 0.004625`, met by `n = 920` with projected Student-t `hw = 0.00448`).
   - `P1_R4 = P1_R4_XU_4X && P1_R4_CMSEP_MECH`.
5. **`P1_R5` (`R5_PNTrain_30dB_3e3`, `180` fr, PN-corrupted training frame)**:
   - `AFDM_EP_Dual_Sym6` paired 95% CI lower bound beats `AFDM_Xu_LumpPCA_Sym6` by `>= 5.0x` AND `AFDM_Gavert_Comb_CovDIC6` by `>= 5.0x`.
6. **`P2_ANALYTICAL_FLOOR_BOUND`**:
   - All 3 realistic fractional-Doppler multipath analytical lumped bounds (`n_mc = 400` each, fresh independent seeds `2027200001+`) satisfy exact Fieller 95% CI worst-case error `max(|ana_cov_db - mc_indep_db_fieller_ci95[0]|, |ana_cov_db - mc_indep_db_fieller_ci95[1]|) <= 0.50 dB`.
   - On BOTH `R2` (`400` fr) and `R3` (`200` fr), `AFDM_EP_Dual_Sym6` paired 95% CI lower bound beats `AFDM_LumpOrac_Indep` by `>= 4.0x`.
7. **Strict Termination Rule (Red Line #4 + Eric 11-25 Ruling)**:
   - `PASS_PRIMARY = GATES_OK && P1_R2 && P1_R3 && P1_R4 && P1_R5 && P2_ANALYTICAL_FLOOR_BOUND`.
   - If `PASS_PRIMARY === true`: mark `I-20261125-m03` `status: active, next_cost: cross-model review` and explicitly record "修改方法后的新种子检验通过".
   - If `PASS_PRIMARY === false`: immediately close `I-20261125-m03` as `status: killed` (permanent end of `m01 -> m02 -> m03` chain).
- **`SCOPE_READOUTS` (Non-Gating)**: `R1`, `R6`, `R3.OFDM_c1=0_SingleKnob_Sym6`, `R3.OFDM_c1=0_SameMask_Sym6`, `R3.OFDM_c1=0_DualOrac`, `AFDM_EP_CPE_GN6` ablation, energy ratios.
