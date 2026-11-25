# L2 Pre-Registered Predictions — `I-20261125-g02`

- **Card**: `I-20261125-g02` (`稀疏AFDM联合啁啾与截断宽度快速在线选参`)
- **Group & Track**: `[放宽TWC]` · `[轨A-纯通信]` (`§4 A3`)
- **Value Ledger**: **Compute Ledger** (online per-frame joint $(c_1, \mathbf{w})$ parameter selection for sparsity-exploiting `LC-BMMSE` AFDM under instantaneous per-frame `(l_i, alpha_i, beta_i, h_i)`, `Mao & Qu Luo IEEE TCOM 2026`, `doi:10.1109/tcomm.2026.3752728`).
- **Seed Isolation & Baseline Parity**: Development calibration (`calibrate_offline_best_fixed` and 20-frame dispersion probes) used seed `20261125` and negative trial offsets `tr = -2000..-2019`; formal L2 locks strictly disjoint test seed bases `971000 / 973000 / 975000 / 977000 / 981000` (`tr_id >= 0`). **All selector arms (`FairSparse_Mao26`, `CoarseFine_Mao26`, `A_only_WF_Exact`, `B_only_Hutch_HillClimb`, `Proposed_Fast_JCPS`) share the exact same sparse-diagonal band assembly (`build_sparse_and_psi_diags`), vectorized cyclic-banded Cholesky/LU solver (`solve_cyclic_diags`), enforced single-thread `OMP_NUM_THREADS=1` execution, and identical channel/bit/noise realizations** (exact-evaluation arms cache per-$k_c$ `H_full`; probe arms cache per-$k_c$ `DAFT-FFT` probe projections `HZ_cache`, and `A_only`, `B_only`, and `Proposed` share identical SPD-first Cholesky early-rejection with all-rejected LU fallback). Per `[放宽TWC]` Group 2 rules, `Rule30_TD_Exact`, `FixedOffline_Best`, and `c1_zero_same_c2` (`k_c = 0` with `c_2 = 1/(2N)` preserved — no cross-waveform `OFDM` lock) are reported strictly as descriptive diagnostics outside `PASS_PRIMARY`.

## 1. Red-Line 1 Anchor & Geometry Gate (`PASS_REDLINE1`, Hard Abort on Failure)
1. **Noiseless Band-Interior `LC-BMMSE` Reconstruction**: At `N=256, P=3, l=[0, 2, 5], alpha=[-1, 0, 1], beta=0, k=2, d=17`, relative 4-QAM symbol reconstruction error `< 1e-12` (measured `2.44e-13`).
2. **Exact Full-Period Sparse-Gram Identity (`Mao26` Eq. (28))**: On odd `N=127` (`w=[63, 63, 63]` covering exact full period without Nyquist wrap), relative error between `build_sparse_and_psi_diags` main diagonal and exact `diag(H_full^H H_full)` `< 1e-12`.
3. **Published `Mao26` Fig. 8 Non-Monotonic Valley Reproduction**: On `N=256, \tilde{d}=37 (d=19), w_s=16, E_b/N_0=15 dB, l=[0, 2, 6]` (`30` Jakes frames, keeping `c_2 = 1/(2N)` fixed across all `k`), actual Monte Carlo 4-QAM `MC_BER` exhibits the non-monotonic valley (`opt_{k in {1,2,3}} MC_BER(k) < MC_BER(k=0)` AND `< MC_BER(k=4)`). Formal L2 aborts immediately if `PASS_REDLINE1` is false; small-`N=64` optimality is also logged diagnostically against full non-negative composition enumeration (`w_i >= 0, sum w_i = 16`) with matching SPD-first/fallback selection.

## 2. Red-Line 5 Dispersion Calibration & Pre-Registered Sample Sizes
Measured on disjoint dev frames (`tr = -2000..-2019`, `20` frames × `32` 4-QAM blocks/frame across `Eb/N0 in {10, 13, 16, 19} dB` at `N=256` and `8` speed frames across `N=64..512`, Table II `NTN-TDL-A {0, -4.675, -6.482} dB`, random distinct delays in `[0, 6]`, Jakes `f_max / Delta_f = 4.17 / 15.0 = 0.278`, `\tilde{d}=33 (d=17), w_s=16`):
- **Paired Log-Speedup Dispersions (`SD` of $\ln(t_{\mathrm{rival}} / t_{\mathrm{prop}})$)**:
  - `N=64`: `FairSparse_Mao26 = 0.297` (`geom = 16.1x`), `CoarseFine = 0.30` (`geom = 14.5x`), `B_only ~ 0.30` (`geom ~ 14x`);
  - `N=128`: `FairSparse_Mao26 = 0.320` (`geom = 25.8x`), `CoarseFine = 0.31` (`geom = 25.2x`);
  - `N=256`: `FairSparse_Mao26 = 0.285` (`geom ~ 45x`), `CoarseFine = 0.28` (`geom ~ 42x`), `A_only ~ 0.20` (`geom ~ 4.4x`);
  - `N=512`: `FairSparse_Mao26 = 0.268` (`geom ~ 95x`), `CoarseFine = 0.26` (`geom ~ 85x`), `A_only ~ 0.20` (`geom ~ 9.0x`).
- **Paired `N=256` Monte Carlo 4-QAM Accuracy Dispersions (`20` dev frames)**:
  - Horizontal SNR difference at `MC_BER = 3.0e-3` (`Prop - FairSparse_Mao26`): dev `MC_BER = [0.01605, 0.00631, 0.00226, 0.00056]` vs `[0.01613, 0.00625, 0.00215, 0.00058]`, paired bootstrap `halfwidth * sqrt(20) = 0.4039 dB`;
  - High-SNR (`Eb/N0 in {16, 19} dB`) pooled `MC_BER(Prop) / MC_BER(FairSparse_Mao26)`: `point = 1.039`, `log_halfwidth * sqrt(20) = 0.1536`.
- **Pre-Registered Sample Sizes & Explicit Realized CI Half-Width Gate (`PASS_CI_PRECISION_25PCT`)**:
  - **Speed Scaling**: **`M_64 = 100, M_128 = 80, M_256 = 80, M_512 = 60` independent frames**;
  - **`N=256` Fig. 10 Accuracy Curve**: **`M_acc = 200` independent channel frames** (`32` 4-QAM blocks = `16,384` bits/frame -> `3,276,800` bits per SNR point across `Eb/N0 in {10, 13, 16, 19} dB`).
  - At these sample sizes, **every primary criterion's realized 95% CI half-width is explicitly enforced in code (`PASS_CI_PRECISION_25PCT`) to be $\le 25\%$ of its threshold distance**:
    1. Speedup `>= 10.0x` across `N = 64..512`: expected log-CI half-widths `0.059..0.071 <= 0.25 * ln(10.0) = 0.5756` (also `<= ln(1.25) = 0.2231`);
    2. Horizontal SNR gap `<= 0.20 dB` at `MC_BER = 3.0e-3`: expected bootstrap half-width `0.4039 / sqrt(200) = 0.0286 dB <= 0.25 * 0.20 = 0.050 dB`;
    3. High-SNR (`{16, 19} dB`) `Prop / Mao26 <= 1.15`: expected log-CI half-width `0.1536 / sqrt(200) = 0.0109 <= 0.25 * ln(1.15) = 0.0349`;
    4. Bidirectional `A+B` ablations: `A_only / Prop >= 5.0x` at `N=512` (`0.052 <= 0.25 * ln(5.0) = 0.402`), `>= 3.0x` at `N=256` (`0.045 <= 0.25 * ln(3.0) = 0.275`), `B_only / Prop >= 5.0x` at `N=64` (`0.059 <= 0.402`).

## 3. Primary Pre-Registered Verdict (`verdicts.PASS_PRIMARY`, Zero-Post-Selection 95% Paired CI Bounds)
`PASS_PRIMARY == True` if and only if `not args.smoke`, `PASS_REDLINE1`, `PASS_CI_PRECISION_25PCT`, and **ALL THREE** 95% paired CI-bound gates hold simultaneously:
1. **`PASS_SPEEDUP_10X` (All 4 Subcarrier Sizes Individually)**:
   `min_{N in {64,128,256,512}} CI95_low(geom_speedup(FairSparse_Mao26 / Prop, N)) >= 10.0` AND `min_{N in {64,128,256,512}} CI95_low(geom_speedup(CoarseFine_Mao26 / Prop, N)) >= 10.0`.
2. **`PASS_ACCURACY_02DB` (Cliff/Waterfall & High-SNR Parity on Actual `MC_BER`)**:
   On `N=256` across `Eb/N0 in {10, 13, 16, 19} dB` (`M_acc = 200`, `B = 4000` paired cluster bootstrap resamples, mapping any non-crossing replicate to `+inf` via exact order statistics):
   `CI95_high(SNR_at_3e3(Prop) - SNR_at_3e3(FairSparse_Mao26)) <= 0.20 dB` AND `CI95_high(MC_BER_{16,19}(Prop) / MC_BER_{16,19}(FairSparse_Mao26)) <= 1.15`.
3. **`PASS_ABLATION_AB` (Bidirectional `A+B` Coupling Necessity)**:
   `CI95_low(geom_speedup(A_only / Prop, N=512)) >= 5.0`, `CI95_low(geom_speedup(A_only / Prop, N=256)) >= 3.0`, AND `CI95_low(geom_speedup(B_only / Prop, N=64)) >= 5.0`.
