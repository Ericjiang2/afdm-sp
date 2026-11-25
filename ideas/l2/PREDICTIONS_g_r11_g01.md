# L2 Pre-Registered Predictions — `I-20261125-g01`

- **Card**: `I-20261125-g01` (`脉冲成形多用户MIMO-AFDM导频窗白化信道估计`)
- **Group & Track**: `[放宽TWC]` · `[轨A-纯通信]` (`§4 A1`)
- **Value Ledger**: **Performance / Floor-Breaking Ledger** (single-symbol embedded-pilot, single-pass pilot-window estimation, zero data-detection outer loop, uncoded high-SNR diversity/floor regime).
- **Seed Isolation**: Development probes and dispersion calibration used seed `20261125` and negative trial offsets (`tr = -3000..-3011` for `S1`, `-4000..-4007` for `S2`, `-5000..-5011` for `CLEAN`); formal L2 evaluation locks strictly disjoint unseen Monte Carlo test seeds `_SCEN_SEED_BASE[scen] + tr_id * 17 + int(round(snr_db * 10))` (`tr_id >= 0`, disjoint bases `910000 / 930000 / 950000` across scenarios) on `deinlab` (`<= 8` CPU workers with `OMP_NUM_THREADS=1`).

## 1. Red-Line 1 Anchor & Physical Operator Gate (`PASS_REDLINE1`, Hard Abort on Failure)
1. **Noiseless Integer Multipath Exactness (`Yin TWC'24` Eq. (25) & (36)–(44))**: Under integer delays $l_p \in [0, l_{\max}]$, integer Dopplers, and full random data on `[M_O .. N-1]`, `Yin24 EPA-DR` relative reconstruction error `< 1e-12`.
2. **Acyclic Continuous-Time 3-Block Kernel Exactness**: Relative error between the upsampled `4x RRC` 3-block acyclic linear convolution (`simulate_3block_rx`) and analytical lag kernel (`full_pulse_H`) `< 1e-12` (measured `6.59e-16`).
3. **Published Normal Operating Point (`Yin TWC'24` Table II / Fig. 12)**: On `2 × 2` `MIMO-AFDM` (`N=256, P=4, l_max=2, alpha_max=2, k_nu=1, O_MIMO=62, 4-QAM`, blind noise estimated strictly on zero-signal guard bins `[2, 3, 23, 24, 44, 45]`, threshold $\zeta = \sqrt{3 \hat{N}_0}$, `SNRp = 35 dB, SNRd = 14 dB`, `80` frames), `BER_Perfect > 0`, `BER_EPA_DR <= 1.60 * BER_Perfect`, and `BER_EPA_DR < 0.025`. Formal simulation aborts immediately if `PASS_REDLINE1` is false.

## 2. Red-Line 5 Complete Dispersion Calibration & Sample-Size Selection
Measured on disjoint development frames (`12` frames `S1 @ 30 dB`, `8` frames `S2 @ 30 dB`, `12` frames `CLEAN @ 28 dB`) with exact acyclic 3-block `4x RRC`, complete `12`-column inter-block leakage basis, and common 2-step purely blind noise variance `s2_common`:
- **`Scenario S1` (`N=128, K=3` [1 weak `0 dB` + 2 strong `+16 dB`], `N_bs=5, P=3`, `SNR_weak = 30 dB`)**:
  - Paired bootstrap log-BER-ratio dispersion $\hat{\sigma}_{\ln R} \cdot \sqrt{M}$ vs `Full_BW_ACNE`: `yin24_a = 2.745` (`pt > 40x`), `fleury_sage_b = 2.489` (`pt = 37.37x`), `matched_dir_b = 2.489` (`pt = 35.56x`), `a_only = 2.315` (`pt = 23.30x`), `b_only = 2.367` (`pt = 22.04x`), `diag_weight = 2.135` (`pt = 22.22x`), `spatial_only = 1.611` (`pt = 9.74x`), `shift_guard = 2.540` (`pt = 31.48x`).
  - Joint paired bootstrap ablation-share dispersion $\hat{\sigma}_{\mathrm{share}} \cdot \sqrt{M}$: `share_A = 0.094` (`pt = 0.084`), `share_B = 0.141` (`pt = 0.432`).
  - Paired per-frame `NMSE_dB(spatial_only) - NMSE_dB(full)`: `mean = +15.65 dB`, `SD = 6.35 dB`.
- **`Scenario S2` (`N=128, K=4` [2 weak `0 dB` + 2 strong `+15 dB`], `N_bs=6, P=3`, `SNR_weak = 30 dB`)**:
  - Paired bootstrap log-BER-ratio dispersion $\hat{\sigma}_{\ln R} \cdot \sqrt{M}$ vs `Full_BW_ACNE`: `yin24_a = 2.904` (`pt = 48.07x`), `fleury_sage_b = 3.020` (`pt = 32.54x`), `matched_dir_b = 3.039` (`pt = 30.46x`).
- **`Scenario CLEAN` (`N=128, K=3` equal power `0 dB` near-far, `N_bs=5, P=3`, `SNR = 30 dB`)**:
  - Per-frame `NMSE_dB`: `mean = -30.58 dB`, `SD = 1.81 dB`; per-frame `SER`: `mean = 0.00000` (`0 / 2484` symbol errors across `12` dev frames).
- **Pre-Registered Sample Sizes**:
  - **`M_S1 = 680` independent frames** (`187,680` weak-user bits) at `S1 (30 dB)`;
  - **`M_S2 = 720` independent frames** (`311,040` weak-user bits) at `S2 (30 dB)`;
  - **`M_clean = 2000` independent frames** (`414,000` symbols) at `CLEAN (30 dB)`;
  - `M_curve = 60` frames at `S1 (20, 25 dB)` (diagnostic curve).
  - At `(680, 720, 2000)`, **every single primary criterion has expected 95% CI half-width $\le 25\%$ of BOTH the threshold distance from neutral AND the expected-to-threshold margin** (and $\le \ln(1.25) = 0.2231$ on every log-ratio):
    1. `S1` rivals `>= 10x`: half-width `0.187–0.206 <= ln(1.25) = 0.2231 <= 0.25*(ln 35.6 - ln 10) = 0.317 <= 0.25*ln(10) = 0.576`;
    2. `S2` rivals `>= 10x`: half-width `0.212–0.222 <= ln(1.25) = 0.2231 <= 0.25*(ln 30.5 - ln 10) = 0.279 <= 0.576`;
    3. Ablation shares `< 0.80`: half-width `0.0071` (`A-only`) and `0.0106` (`B-only`) `<= 0.050 <= 0.25*(0.80 - 0.432) = 0.092`; ablation BER `>= 5x`: `0.178 <= 0.2231 <= 0.370`;
    4. Cross-window: `Diag/Full >= 4x` (`0.160 <= 0.2231`), `SpatialOnly/Full >= 3x` (`0.121 <= 0.2231 <= 0.294`), `SpatialOnly - Full NMSE_dB >= 8.0 dB` (paired-$t$ half-width `0.478 dB <= 0.25*(15.65 - 8.0) = 1.91 dB <= 2.00 dB`);
    5. Shifted-guard `>= 5x`: `0.191 <= 0.2231 <= 0.402`;
    6. `CLEAN` sanity (`30 dB, M_clean = 2000`): paired-$t$ `NMSE_dB` half-width `0.079 dB <= 0.25*(-20 - (-30.58)) = 2.64 dB`; frame-level `SER` (`X_m in [0, 1]`) uses **exact two-sided 95% Hoeffding (1963, Theorem 1) KL-Chernoff confidence interval** `[kl_low_025, kl_high_025]` (`M_clean * D_KL(X_bar || mu) <= ln(40)`), whose expected interval at dev `X_bar = 0` is `[0.0, 0.00184]` with **half-width `0.00092 <= 0.25 * 0.01 = 0.0025`** (and upper margin `0.00184 <= 0.0025`), guaranteeing exact finite-sample `<= 2.5%` false-pass rate for ANY `[0, 1]`-bounded frame SER distribution with zero intra-frame independence assumption.

## 3. Primary Pre-Registered Verdict (`verdicts.PASS_PRIMARY`, Zero-Post-Selection 95% CI Bounds)
All 8 co-frame `[data_bins]` arms share the exact same `[0 .. M_O-1]` observation and common 2-step purely blind `s2_common(Y_rx[obs_idx])`, while the separate-frame `ShiftGuard` arm runs the identical blind `estimate_common_blind_s2(Y_sh[obs_idx])` on its own received waveform `Y_sh` (avoiding cross-waveform leakage). All Newton-VarPro parametric arms (`matched_dir_b`, `a_only`, `b_only`, `diag_weight`, `spatial_only`, `full`, and `shift_guard`) execute the exact same 3-stage search/refinement budget (greedy init + pre-polish + dual-start re-search + 5-step joint VarPro polish), while `yin24_a` executes its published closed-form $\sqrt{3\hat{N}_0}$-thresholded diagonal reconstruction (`Yin TWC'24`) and `fleury_sage_b` executes its 3-stage coordinate-wise `SAGE` search + joint LS amplitude refit (`Fleury JSAC'99`); all arms feed the exact same algebraic unbiased `16-QAM LMMSE` detector. In `paired_ber_ratio_ci95`, positive denominators use exact unmodified `sum(en)/sum(ed)`, whereas any zero denominator (`sum(ed) == 0`) uses the conservative cluster-level worst-case bound `3.6889 * bits_per_frame` so zero errors can never falsely inflate a ratio below threshold. **Every rival and ablation arm has its paired 95% CI computed individually (zero post-selection by point estimate), and `PASS_PRIMARY` requires `not args.smoke`, `PASS_REDLINE1`, and ALL FIVE CI-bound conditions simultaneously:**
1. **Legal Rivals (`>= 10x` across ALL legal rivals individually)**:
   `min_{r in {yin24_a, fleury_sage_b, matched_dir_b}} CI95_low_S1(BER(r)/BER(full)) >= 10.0` AND `min_{r in {yin24_a, fleury_sage_b, matched_dir_b}} CI95_low_S2(BER(r)/BER(full)) >= 10.0`.
2. **Bidirectional `A + B` Ablation (`< 80%` share & `>= 5x` BER across BOTH arms individually)**:
   `CI95_high(share_A) < 0.80` (with non-positive denominator mapped to `+inf`), `CI95_high(share_B) < 0.80`, AND `min(CI95_low(BER(a_only)/BER(full)), CI95_low(BER(b_only)/BER(full))) >= 5.0`.
3. **Cross-Window Causal Proof**:
   `CI95_low(BER(diag_weight)/BER(full)) >= 4.0`, `CI95_low(BER(spatial_only)/BER(full)) >= 3.0`, AND paired-$t$ `CI95_low(NMSE_dB(spatial_only) - NMSE_dB(full)) >= 8.0 dB`.
4. **Equal-Net-Throughput 3-Block Shifted-Guard**:
   `CI95_low(BER(shift_guard)/BER(full)) >= 5.0`.
5. **Clean Unimpaired Sanity (`Red-Line 2`, Exact Two-Sided Hoeffding-KL Frame-Cluster CI)**:
   Paired-$t$ `CI95_high(NMSE_dB) < -20.0 dB` AND `max(SER_frame_t_ci95_high, hoeffding_kl_ci95_high) < 0.01`.
