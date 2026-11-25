# Step-8 Diagnostic Pre-Registered Predictions — `I-20261125-g01` (Revised SPD Cross-Window vs Intra-Window Disconnection)

- **Card**: `I-20261125-g01` (`脉冲成形多用户MIMO-AFDM导频窗白化信道估计`)
- **Group & Track**: `[放宽TWC]` · `[轨A-纯通信]` (`§4 A1`)
- **Review Mandate**: Step-8 `gpt-6.2-astra` `REVISE` (`ideas/reviews/r11-astra-g01-killarg-20261125.md`, Points `P_3–P_4`), `ideas/prompts/round-12.md` §2 (`runner g` Task ①), and `Sol` Call `6/6` + Extra Call `1/1` resolutions (`sol_prel2_call6_batch_g01_g02_out.md:5–12`, `sol_r12_extra_g01_c1_out.md:1–13`).
- **Seed Isolation (Mechanically Verified via `verify_g01_seed_disjointness` in `PASS_REDLINE1`)**:
  - Formal evaluation hard-locks **1,740 pairwise-disjoint integer seeds**: `S1` uses base `4100000` (`FORMAL_N_S1 = 1500`, `tr_id = 0..1499` $\to$ `4100300..4125783`) and `S2` uses base `4200000` (`FORMAL_N_S2 = 240`, `tr_id = 0..239` $\to$ `4200300..4204363`) on `deinlab` (`<= 8` CPU workers, `OMP_NUM_THREADS=1`).
  - All historical/dev seeds (`91000`, `858637..989000`, `1105000`, `1210000..1435000`, `3097000..3610000`), bootstrap seeds (`20261200..20261299`), and `--smoke` negative-`tr_id` seeds (`4098583, 4098600` for `S1` and `4198583, 4198600` for `S2`, explicitly enumerated and excluded in `verify_g01_seed_disjointness()`) have **zero intersection** with the 1,740 formal seeds.

## 1. Research Checkpoint: Pre-Locked Windows, Revised SPD Intervention Questions & 1-to-1 Operator Mapping

1. **Pre-Locked Frame Window Indices (Zero Free Parameters, Direct from `Yin TWC'24` Eq. (25)–(26) & `g_l2_r11_g01.py:58–62`)**:
   Under `l_max = 2, alpha_max = 1, k_nu = 1, two_Nc1 = 5, Q_yin = 14`, user $u$ has pilot at $p_u = (u+1)Q_{\mathrm{yin}} + u$ and causal integer-delay/Doppler support $[p_u - 5 l_{\max} - 2,\, p_u + 2]$:
   - **`S1` (`N=128, K=3`, weak `u=0` at `0 dB`, strong `u=1,2` at `+16 dB`, `N_bs=5, P=3`, `obs_idx = [0..58]`, `data_bins = [59..127]`)**: `W_head = [0 .. 16]`, `W_mid = [17 .. 46]`, `W_rguard = [47 .. 58]`.
   - **`S2` (`N=128, K=4`, weak `u=0,1` at `0 dB`, strong `u=2,3` at `+15 dB`, `N_bs=6, P=3`, `obs_idx = [0..73]`, `data_bins = [74..127]`)**: `W_head = [0 .. 31]`, `W_mid = [32 .. 61]`, `W_rguard = [62 .. 73]`.

2. **Confirmed Revised Test Specification & Per-Frame `full`-Arm Pre-Projection Feasibility Check**:
   On the 3-window Hermitian baseline $\mathbf{\Sigma} = \frac{1}{2}(\mathbf{G}\mathbf{G}^H + (\mathbf{G}\mathbf{G}^H)^H) + \hat{\sigma}_{\mathrm{blind}}^2 \mathbf{I}$ over $(W_{\mathrm{head}}, W_{\mathrm{mid}}, W_{\mathrm{rguard}})$, setting $\tilde{\mathbf{\Sigma}}_{13} = \tilde{\mathbf{\Sigma}}_{31} = \mathbf{0}$ alone while keeping $(\mathbf{\Sigma}_{11}, \mathbf{\Sigma}_{22}, \mathbf{\Sigma}_{33}, \mathbf{\Sigma}_{12}, \mathbf{\Sigma}_{23})$ fixed violates 3-block Schur positive-definiteness across `40 / 40` calibration frames at `S1 @ 30 dB` ($\lambda_{\min}(\tilde{\mathbf{\Sigma}}) \in [-2.58, -0.27] < 0$). On every formal frame, `check_raw_zero13_min_eig(paths_full, s2_common)` is evaluated **once per frame directly on the converged `full` arm's pre-projection covariance** (`full_final_raw_zero13_min_eig`), aggregating per-frame `raw_zero13_nonspd_frame_rate` (`fraction of frames with full_final_raw_zero13_min_eig <= 0.0`) completely independent of any composite diagnostic arm.
   Every primary arm is an exact block-preserving SPD operator sharing `Y_rx`, blind `s2_common`, exact pulse kernel `use_pulse=True`, 3-stage Newton-VarPro search budget, and `detect_unb_lmmse`, mapped **1-to-1** to its own operator claim:
   - **Operator Q1 — `cut_chordal_prec0` (`VERDICT_CHORDAL_DIRECT_PREC_3X`)**: Unique chordal SPD completion $\mathbf{\Sigma}_{13}^{\mathrm{ch}} = \mathbf{\Sigma}_{12}\mathbf{\Sigma}_{22}^{-1}\mathbf{\Sigma}_{23}$, preserving $\mathbf{\Sigma}_{11}, \mathbf{\Sigma}_{22}, \mathbf{\Sigma}_{33}, \mathbf{\Sigma}_{12}, \mathbf{\Sigma}_{23}$ bit-exact and setting direct GLS precision $(\mathbf{C}_{\mathrm{inv}})_{13} = (\mathbf{C}_{\mathrm{inv}})_{31} = \mathbf{0}$.
   - **Operator Q2 — `cut_2blk_rguard` (`VERDICT_RGUARD_2BLK_COV_3X`)**: Exact 2-window SPD covariance disconnection $\mathrm{blkdiag}(W_{\mathrm{head}} \cup W_{\mathrm{mid}},\, W_{\mathrm{rguard}})$, preserving $\mathbf{\Sigma}_{11}, \mathbf{\Sigma}_{22}, \mathbf{\Sigma}_{12}, \mathbf{\Sigma}_{33}$ bit-exact and setting $\mathbf{\Sigma}_{13} = \mathbf{0}, \mathbf{\Sigma}_{23} = \mathbf{0}$.
   - **Operator Q3a — `cut_2blk_head` (`VERDICT_HEAD_2BLK_COV_3X`)**: Exact 2-window SPD covariance disconnection $\mathrm{blkdiag}(W_{\mathrm{head}},\, W_{\mathrm{mid}} \cup W_{\mathrm{rguard}})$, setting $\mathbf{\Sigma}_{13} = \mathbf{0}, \mathbf{\Sigma}_{12} = \mathbf{0}$.
   - **Operator Q3b — `cut_3blk_windows` (`VERDICT_ALL_INTERWINDOW_3BLK_3X`)**: Exact 3-window SPD covariance pinch $\mathrm{blkdiag}(W_{\mathrm{head}}, W_{\mathrm{mid}}, W_{\mathrm{rguard}})$, zeroing all inter-window covariances $(\mathbf{\Sigma}_{13}=\mathbf{0}, \mathbf{\Sigma}_{12}=\mathbf{0}, \mathbf{\Sigma}_{23}=\mathbf{0})$.
   - **Operator Q4 — Single-Factor Intra-Window Cross-Bin Control (`spatial_only` vs `cut_3blk_windows`, `VERDICT_INTRA_WINDOW_OVER_SPATIAL_3X`)**: Both have identically zero inter-window covariances, differing solely by retaining vs zeroing intra-window cross-bin covariances within $W_{\mathrm{head}}, W_{\mathrm{mid}}, W_{\mathrm{rguard}}$.
   - *Isolated Descriptive Composite Diagnostic (`cut_literal_psd`)*: Executed in an isolated `try...except` block per frame and completely excluded from `verify_cut_operator_invariants()`, `PASS_REDLINE1`, `PASS_CI_PRECISION_25PCT`, `PASS_PRIMARY`, and `card_claim_routing`.

3. **Three-State CI Semantics (`CONFIRMED_GE_BAR` / `REFUTED_LT_BAR` / `UNPROVEN_STRADDLES_BAR`) & Pre-Run Forecast**:
   - **`CONFIRMED_GE_BAR`**: $\mathrm{lo} \ge \tau$ (supported under pre-registered 95% confidence bound);
   - **`REFUTED_LT_BAR`**: $\mathrm{hi} < \tau$ (ruled out at $\ge \tau$ under pre-registered 95% confidence bound);
   - **`UNPROVEN_STRADDLES_BAR`**: $\mathrm{lo} < \tau \le \mathrm{hi}$ (fails positive $\mathrm{lo} \ge \tau$ bar without ruling out $\ge \tau$).
   - **Forecast**: `P(H_intra) = 0.92`, `P(H_inter) = 0.05`, `P(straddle) = 0.03`.

## 2. Red-Line 5 Direct Dispersion Calibration, `FUNNEL.md:84` Half-Width Cap & Sample Sizes

On `40` disjoint dev frames (`tr_id = -3000..-3039` on `S1 @ 30 dB`): `cut_chordal_prec0 / full = 1.00x` ($\mathrm{lhw}\sqrt{M}=0.342$), `cut_2blk_rguard / full = 0.83x` (`2.564`), `cut_2blk_head / full = 1.04x` (`0.319`), `cut_3blk_windows / full = 0.88x` (`2.256`), `spatial_only / full = 5.73x` (`4.930`), `spatial_only / cut_3blk_windows = 6.48x` (`6.422`), `a_only / full = 14.40x` (`5.646`).
- **Primary `S1`**: **`FORMAL_N_S1 = 1500` frames** ($\sqrt{1500} = 38.730$), expected worst `lhw = 0.1658 <= cap_ratio_lhw(tau) = min(0.25 * ln(tau), ln(1.25)) = 0.22314355`.
- **Secondary Scope Readout `S2`**: **`FORMAL_N_S2 = 240` frames**.

## 3. Pre-Registered Verdicts & Strict 1-to-1 Operator Card Routing (`diag_g_r12_g01_cut.json`)

1. **`PASS_REDLINE1`**: Gates `verify_redline1_yin24()` + `verify_cut_operator_invariants()` across **only** the four exact-SPD primary cut operators (`cut_chordal_prec0`, `cut_2blk_rguard`, `cut_2blk_head`, `cut_3blk_windows`) plus `seed_disjointness_exact_ok`, `windows_exact_ok`, `raw_zero13_synth_nonspd` ($\lambda_{\min}(\tilde{\mathbf{\Sigma}}_{\mathrm{raw}}) < 0$ on pre-projection zero-$(1,3)$ synthetic matrix), combined Frobenius norm `||(Cinv)[target_zero_blocks]||_F / ||Cinv||_F < 1e-12`, and `full` arm parity `< 1e-12` (`cut_literal_psd` never enters `PASS_REDLINE1`).
2. **`PASS_CI_PRECISION_25PCT` & `PASS_VALID_FORMAL`**: All 7 primary ratios on `S1` (`1500` frames, `S2` `240` frames) have `observed_zero_undecidable == False` and `log_halfwidth <= ln(1.25) = 0.22314355`.
3. **`PASS_PRIMARY` & 1-to-1 `card_claim_routing`**:
   - `PASS_SAME_PULSE_CROSS_BIN_GAIN = VERDICT_FULL_OVER_A_ONLY_5X and VERDICT_FULL_OVER_SPATIAL_3X and VERDICT_INTRA_WINDOW_OVER_SPATIAL_3X`; `PASS_PRIMARY = PASS_VALID_FORMAL and PASS_SAME_PULSE_CROSS_BIN_GAIN`.
   - `literal_3win_single_cov13_note` uses `s1_sum["raw_zero13_nonspd_frame_rate"] > 0.0` computed once per frame on the converged `full` arm's pre-projection covariance (`"INFEASIBLE_NON_SPD_ON_3WIN_GLS"` vs `"FEASIBLE_ON_FORMAL"`), while `direct_gls_precision_13_claim`, `right_guard_2win_cov_conditioning_claim`, `all_interwindow_3win_cov_claim`, and `intra_window_single_factor_3x` map strictly 1-to-1 to `Q1`, `Q2`, `Q3b`, and `Q4`.
