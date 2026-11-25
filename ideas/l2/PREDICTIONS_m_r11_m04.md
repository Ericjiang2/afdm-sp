# Pre-Registered L2 Predictions Ledger — `I-20261125-m04` (`[放宽TWC] [轨B-ISAC]`)

- **Card**: `I-20261125-m04` — *压缩保护带 AFDM 格拉斯曼零空间无解码通感与界*
- **Script**: `ideas/l2/l2_m_r11_m04_guard_null_isac.py`
- **Frozen Date**: `2026-11-25` (v7 — **post-Sol Call 15/15 calibration/gate harmonization** per Eric 11-25 instruction: replaced all `np.quantile` thresholds, Wilson `P_fa` checks, and the looser `[0.02%, 0.25%]` startup window with the exact order-statistic threshold $X_{(b)}$ [$b = n_{\mathrm{cal}} + 1 - a$, $a = \operatorname{round}(p (n_{\mathrm{cal}} + 1))$] and exact finite-sample Beta-Binomial predictive interval validation uniformly for every arm and both NOMP startup pilots, making the in-script startup gate identical to the frozen criterion; strictly prior to Sol Call 16/16 approval and `deinlab` full L2 execution; ZERO post-hoc relaxation of any detection, estimation, BLER, or bound performance threshold).
- **Disjoint Fresh Seeds**:
  - Local `--smoke` namespace: `SEED_BASE = 2028000000` (`2028000001+`).
  - Official `deinlab` Full L2 namespace: `SEED_BASE = 2030000000` (`2030000001+`) — **0% overlap** with `--smoke`, dev (`100001`), or any prior run (`2029...`).
- **Frozen Blind Receiver Signature**: Every arm accepts ONLY `(y, rx_cfg)` — zero true `sigma2`, zero unknown payload `x_d`, zero true clutter order `P_c`, zero target ground truth.
- **Frozen Blind Clutter-Order Rule (`max_clut = 3`, frozen on dev set `100001`)**:
  - Path 1 accepted iff initial pilot-MF peak-to-median ratio `r0 > 15.0` (else `Pc_hat = 0`, `H_c = 0`, `N_G = E_G`).
  - Subsequent clutter path `p in {2, 3}` accepted iff Grassmannian residual drop `J_try < 0.25 * J_cur` AND relative amplitude `min(|h_try|) > 0.25 * max(|h_try|)`.
- **Frozen Unified Full-Map Scoring**:
  - Grid: `l_grid = np.linspace(0.2, 10.5, 43)`, `nu_grid = np.linspace(-2.5, 2.5, 41)`.
  - Clutter exclusion mask: `|l - l_hat| < 1.2` AND `|nu - nu_hat| < 0.8` around each arm's own estimated clutter paths.
  - Statistic: `T = max(sc_masked / (median(sc) + 1e-12))`; threshold `tau = X_(b)` computed as the exact 1-indexed order statistic of the independent `H0-cal` set with `a = max(1, round(pfa_nom * (n_cal + 1)))`, `b = n_cal + 1 - a` (nominal `pfa_nom = 0.02`), validated on the independent `H0-verify` set via the exact finite-sample `BetaBinomial(n_ver, a, b)` two-sided predictive interval `[k_lo, k_hi]` (same exact rule for EVERY arm; Bonferroni family-wise 95% FWER `alpha_each = 0.05 / 19` across all 19 gated arm-regime checks in `R1 [8 arms] + R2 [8 arms] + R3a [3 arms]`, and `0.05 / 4` across the 4 non-gating `R3b` checks; stratified `R_null` `Pc = 0, 1, 2` also reported with `R2`'s `(a, b)`). *(Updated after Sol Call 15/15.)*
  - Hit tolerance: `|l_est - l_true| < 0.5` AND `|nu_est - nu_true| < 0.5`.

## Pre-Registered Pass/Fail Criteria (`PASS_PRIMARY`)

1. **`GATES_OK`** (ALL must hold; script exits immediately with code 2 if startup gates fail):
   - Exact Golub-Pereyra pseudoinverse Grassmannian gradient FD check (`sigma = 0.14`): `fd_grad_rel_err < 1e-7`.
   - Exact nullspace clutter-data leakage: `||N_G^H H_d x_d||_2 < 1e-12`.
   - Genuine rank-deficiency stress test: BOTH exact rank-0 canceling paths (`rank(Hd)=0`, including full `refine_orth_null_gn`) AND non-zero period-2 comb null (explicitly asserting `rank(Hd) == 52 < Nd = 104, ||Hd|| > 1`) produce finite `N_G`, gradient, and GN output (`rank_deficiency_finite == True`).
   - Runtime ablation isolation check: `B_only_NoNullspace` makes ZERO calls to `orth_nullspace_NG` and `refine_orth_null_gn` (`ablation_b_only_isolated == True`).
   - `R3c` zero-coupling & CPP-energy gates: `||H_r3c[p_win_76, D_76]||_F < 1e-12` AND with standard public PHY bit-scrambling XORed after `conv_encode`, EVERY coded QAM symbol (including tail bits) is strictly uniform over the constellation so `|E[||P_cpp A^H (xp + xd)||_2^2] - 138.0| < 1e-11` across all 3 arms (`Ours_G24`, `Std_G76_Ep24`, `Std_G76_Ep76`), with realized `mean_etx` logged and ZERO `xd`-dependent pilot scaling.
   - Red-Line-#1 Baseline Reproductions + Blind/CFAR Noiseless Reconstructions (`< 1e-12`):
     - `Y. Luo TCOM'26` Fig. 8 origin (`N=256, Nr=8, 4-QAM, 10 dB, c1=9/512`): `NMSE < -14.0 dB`, `SER < 0.01`, AND genuine blind noiseless `run_luo_gesbl` (zero true `xd`/paths passed in) `err < 1e-12, SER == 0.0`. *(Implementation note: uses per-atom coupled `2×2` `(l_m, nu_m)` Gauss-Newton grid evolution with exact net-gradient posterior cross-covariance `rhs_net = res @ conj(Mu[idx,:]) - Nr * (Phi @ Sigma[:, idx])`, updating each top active atom's `(l, nu)` sequentially rather than solving the full coupled multi-atom block system of Y. Luo Eqs. (40)–(45); verified to reproduce Fig. 8 to `-15.66 to -17.79 dB, SER = 0.0000` and blind noiseless recovery `< 1e-15`.)*
     - `Ma 2606.25572 / Bemani WCL'24` full-guard **with non-zero unknown 64-QAM data** evaluated with ACTUAL windowed `rx_ma_seq_mf`: 1-path noiseless `err < 1e-12` (`P_det == 1`), 2-path `20 dB` `NMSE < -20.0 dB` (`P_det == 2`), AND compressed-guard `Ma` Case-1 `MCRB1 / CRB > 10×`.
     - `NOMP` (`Mamandipoor TSP'16 / Shah TVT'25`) $\mathbf{F}_N \to \mathbf{A}$ direct port verified **directly through the ACTUAL main arm `rx_nomp_dirport`** (`max_clut=5`, exact order-statistic OS-CFAR multiplier `X_(b)` calibrated under $\mathcal{CN}(\mathbf{0}, \mathbf{I}_N)$ with `n_cal = 80000`, `pfa_cfar = 1e-3`, `a = 80`, `b = 79921` for the actual public pilot `xp`, dense search grid `(l_grid, nu_grid)`, and integer-grid median noise estimator, with adaptive early-exit Newton): `P_det == 3` at `20 dB` & noiseless, `NMSE < -20.0 dB`, noiseless `err < 1e-12` (verified identically for both `max_clut=3` and `max_clut=5`), exact element-wise `_nomp_atom_bank` agreement `< 1e-12`, AND on an independent `n_val = 16000`-frame white-noise validation set, the exceedance count `k_fa` falls inside the exact 2-pilot FWER (`alpha_each = 0.05 / 2`) `BetaBinomial(16000, 80, 79921)` predictive interval `[7, 27]` (`[0.0438%, 0.1688%]`) for BOTH full-pilot and compressed-guard main pilots (in-script startup gate identical to this criterion; no looser `[0.02%, 0.25%]` window). *(Updated after Sol Call 15/15.)*
   - Independent `H0-verify` empirical `P_fa` gate for **EVERY arm uniformly** across `R1 (8 arms), R2 (8 arms), R3a (3 arms)` (`19` total checks): every arm's exceedance count `k_fa_verify = sum(ver_stats > X_(b))` falls inside the exact `BetaBinomial(n_ver, a, b)` two-sided predictive interval at family-wise 95% FWER (`alpha_each = 0.05 / 19`; same exact order-statistic & Beta-Binomial rule for all arms; e.g., full L2 `R1/R2`: `n_cal=n_ver=150, a=3, b=148, k in [0, 14]`; `R3a`: `n_cal=n_ver=120, a=2, b=119, k in [0, 12]`), AND `R0` blind clutter-order exact accuracy across `Pc in {0, 1, 2}` `>= 85%`. *(Updated after Sol Call 15/15.)*

2. **`P1_R1` (`R1_1PathClut_Neg20dB`: `N=128, G=24, Nr=1`, unknown Gaussian payload, `25 dB`, `Pc=1` + `-20 dB` weak target; `150/150/120` frames)**:
   - `Ours_GrassNull` `Hit-Pd >= 85%`.
   - Beats `Ma_SeqMF`, `Luo_GESBL` (pilot-only), `NOMP_DirPort`, `A_only_NullPilot` (with symmetric post-detection joint GN), and `B_only_NoNullspace` by `>= 50` pp with paired 95% CI strictly `> 0`.
   - Both independent ablations (`A_only_NullPilot`, `B_only_NoNullspace`) strictly `< 80%`. (Supplementary non-gating diagnostics `B_only_NOMP_LS_Diag` [from-scratch NOMP clutter + LS subtraction + isotropic MF] and `B_only_TikhonovDet_Diag` [`N_G` clutter + Tikhonov `rho=0.25` isotropic MF] also logged.)

3. **`P1_R2` (`R2_2PathFading_Neg18dB`: `N=128, G=24, Nr=1`, unknown Gaussian payload, `25 dB`, `Pc=2` deep fading `0/-2.5 dB` + `-18 dB` weak target; `150/150/120` frames + 60-trial fixed-geometry CRB check)**:
   - `Ours_GrassNull` `Hit-Pd >= 75%`.
   - Beats `Ma_SeqMF`, `Luo_GESBL`, `NOMP_DirPort`, `A_only_NullPilot`, and `B_only_NoNullspace` by `>= 45` pp with paired 95% CI strictly `> 0`.
   - Both independent ablations (`A_only_NullPilot`, `B_only_NoNullspace`) strictly `< 80%`.
   - On detected frames, `Ours` weak-target `rmse_l <= 2.5 * Ma_CRB_l`, `rmse_nu <= 2.5 * Ma_CRB_nu`, and `|h_mag_bias| < 0.02` (with miss rate, variance, MSE, and Case-1 MCRB reported alongside).

4. **`P1_R3` (`R3a_Coop64QAM_Nr1_24dB` + `R3c_EqualNetThroughput_BLER`)**:
   - `R3a` (`N=128, G=24, Nr=1`, cooperative 64-QAM, `24 dB`, `120/120/100` frames): `Ours_GrassNull` (zero decoding) `Hit-Pd >= 60%` and beats full `Y. Luo D-GESBL` (exact Sec. IV cross-cov grid evolution + 64-QAM decision feedback) AND `NOMP_DirPort` by `>= 35` pp with paired 95% CI strictly `> 0`.
   - `R3c` (Equal Net Info Bits = **exact `206` net info bits / `138` total samples**, `L_cpp=10`, **standard public PHY bit-scrambling ensuring exact `E[||P_cpp A^H (xp + xd)||_2^2] == 138.0` identically across all 3 arms verified `< 1e-11` in startup gates, with realized `mean_etx` logged and zero `xd`-dependent pilot scaling**, terminated `(7,5)_8` conv code + soft-LLR Viterbi + symmetric 1-pass DF CE polish, zero-coupling Bemani full-guard geometry `l_c=[1,3], l_t=5` with `||H[p_win, D_76]||_F = 4.45e-13 < 1e-12`, `120` paired frames/SNR over `10..22 dB`, **strict BLER crossing `ys[i] >= target > ys[i+1]` with monotonic tail `all(y < target for y in ys[i+1:])` only — ZERO endpoint extrapolation**):
     - **Blind-CE at `BLER = 10%`** (updated honestly pre-L2 after fixing `Std_G76` coupling from `0.81` to `4.45e-13` so `Std_G76` is completely uncrippled): `Ours_G24` strictly crosses and beats `Std_G76_Ep24` by **`>= 1.5 dB`** AND `Std_G76_Ep76` by **`>= 2.5 dB`** (`BLER = 5%` crossing also reported).
     - **Oracle-CE at `BLER = 5%`**: `Ours_G24` strictly crosses and beats `Std_G76_Ep24` by **`>= 3.0 dB`** AND `Std_G76_Ep76` by **`>= 5.0 dB`**.

5. **`P2_R4` (`R4_Analytical_SCNR_Bound`)**:
   - Zero-parameter closed-form `SCNR_null` matches 400-trial MC within `<= 0.50 dB` across ALL 3 distinct settings (`N=128 G=24 2-path 25 dB`, `N=128 G=16 1-path 25 dB`, `N=256 G=32 2-path 20 dB`).

6. **Non-Gating Diagnostics (`R3b` & `SCOPE_READOUTS`, logged honestly without affecting `PASS_PRIMARY`)**:
   - `R3b_MultiAnt_Nr8` (`N=128, G=24, Nr=8` ULA): `Ours_GrassNull_Nr8` vs `Luo_GESBL_Nr8` on non-cooperative Gaussian `16 dB` and low-SNR cooperative 64-QAM `12 dB`.
   - `OFDM c1=0` contiguous `G=24` full E2E `Hit-Pd` on `R2` (non-triviality `A3-3a` readout).
   - `2 × 2` (`contig/comb` × `nu_t = 0.05 / 1.40`) `AFDM` vs `OFDM` `data_gain / G` mechanism table.
   - Exact **Woodbury marginal NLL (`Ma` Eq. 9 with `ln det`, oracle `sigma2`)** vs `sigma2`-free `J_null` (`30` frames of `R2`).

7. **Strict Termination Rule (Red Line #4)**:
   - `PASS_PRIMARY = GATES_OK && P1_R1 && P1_R2 && P1_R3 && P2_R4`.
   - If `PASS_PRIMARY == false`, card `I-20261125-m04` is immediately marked `status: parked` or `killed`.
