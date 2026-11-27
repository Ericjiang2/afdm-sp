# L2 Pre-Registered Predictions — `I-20261125-g02`

- **Card**: `I-20261125-g02` (`稀疏AFDM联合啁啾与截断宽度快速在线选参`)
- **Group & Track**: `[放宽TWC]` · `[轨A-纯通信]` (`§4 A3`)
- **Value Ledger**: **Compute Ledger** (online per-frame joint $(c_1, \mathbf{w})$ parameter selection for sparsity-exploiting `LC-BMMSE` AFDM under known instantaneous per-frame `(l_i, alpha_i, beta_i, h_i)` and noise variance `sigma2`, `Mao & Qu Luo IEEE TCOM 2026`, `doi:10.1109/tcomm.2026.3752728`).
- **Seed Isolation (Mechanically Verified via `verify_seed_disjointness` in `PASS_REDLINE1`)**:
  - Formal L2 hard-locks **2,192 pairwise-disjoint integer seeds in `[3100000, 3603353]`** (`tr_id >= 0`, no CLI sample-size override): `SPEED` bases `{64: 3100000, 128: 3200000, 256: 3300000, 512: 3400000}` (`rng`: `base + tr_id * 19`, and common-random-numbers probe seed `base + 50000 + tr_id` shared identically by `B_only` and `Proposed`) and `ACC256` bases `3500000 + tr_id * 23` (`tr_id = 0..335` channel/bits/noise) and `3600000 + tr_id * 10 + ig` (`Proposed` probe).
  - `verify_seed_disjointness()` enumerates all 2,192 formal seeds and gates zero overlap with warmup seeds (`11 + N_w`, `51 + N_w`), Red-Line 1 & diagnostic seeds (`960000..965019`), offline calibration seed (`20261125`), all bootstrap seeds (`20261170..20262049`), `--smoke` negative-`tr_id` seeds (`3097967..3098100`, `3149893..3449900`, `3497677..3599003`), and all historical/dev calibration seeds (`[0, 2999999]`, including v4 dev calibration `810000..890000` and `720000..735000`).

## 1. Paper-Exact Baseline vs Project $2 \times 2$ SPD-Screened Factorial Grid, Scoring Function & Timing Balance

All arms share identical Algorithm 1 sparse-diagonal band assembly (`build_sparse_and_psi_diags`), exact sparsification perturbation power $\sigma_\Delta^2 = \frac{1}{N}\|\mathbf{H}_{\mathrm{eff}} - \tilde{\mathbf{H}}_{\mathrm{eff}}\|_F^2$ (`compute_sigma_delta2_exact`, exact even under overlapping supports) in $\tilde{\boldsymbol{\Psi}} = (\tilde{\mathbf{G}} \odot \mathbf{S}) + (\sigma_n^2 + \sigma_\Delta^2)\mathbf{I}_N$, pre-RHS cyclic-banded factorization (`factor_cyclic_diags` + `apply_cyclic_factor`), single-thread `OMP_NUM_THREADS=1`, and identical channel/bit/noise realizations:
1. **Boundary-Exact Width Constructors (`mao26_all_eq45_inits` & `band_coupled_wf_seed`)**:
   - `mao26_all_eq45_inits`: enumerates **all $L_r = \mathrm{rem\_t} + 1$ admissible initializations** $w_1 \in \{0, 1, \dots, \mathrm{rem\_t}\}$, $w_P = \mathrm{rem\_t} - w_1$ with $\mathbf{w} \in \mathbb{Z}_+^P, \sum_i w_i = w_s$ per `Mao26` Eq. (45).
   - `band_coupled_wf_seed`: enforces $w_0 + w_{P-1} \le \max(0, (d_{\mathrm{band}} - 1) - \mathrm{sep}_{\mathrm{cyc}})$ for all $P \ge 3$ (including `sep_cyc >= d_band - 1` $\to$ `pair_cap = 0`).
2. **Literal Published Reproduction Arms vs Project $2 \times 2$ SPD-Screened Arms**:
   - **Published unscreened reproduction arms (`PaperExact_Mao26`, plus step-2 search baseline `CoarseFine_Mao26`)**: execute `Mao26` Algorithm 1 + Algorithm 2 literally over $k \in \{1, \dots, r_{\max}\}$ with all Eq. (45) initializations `mao26_all_eq45_inits`, **Algorithm 2 lines 7–15 synchronous neighbor scan from fixed $\mathbf{w}^{(t)} \to \mathbf{w}^{(t+1)}$**, **printed Eq. (14) score $2Q - 4Q^2$ (`use_paper_eq14 = True`, $a_M = 2$ at $M=4$)**, **strict improvement `pn < p_t` (`tol = 0.0`)** per Eq. (46), and `spd_two_pass = False`.
   - **Project $2 \times 2$ SPD-screened factorial grid (`FairSparse_Mao26_SPD`, `A_only_WF_Exact`, `B_only_Hutch_HillClimb`, `Proposed_Fast_JCPS`) + `CoarseFine_Mao26_SPD`**: explicitly distinguished as project variants using surrogate score $Q - Q^2$ (`use_paper_eq14 = False`), identical two-pass SPD screening `for req_s in (True, False): ... if best_pa < 1e29: break`, and `tol = 1e-6` (`FairSparse_Mao26_SPD`, `CoarseFine_Mao26_SPD`, and `B_only` share synchronous neighbor scan + `mao26_all_eq45_inits`; `A_only` and `Proposed` share `w_bc` + `w_u` + 2-Swap polish; `B_only` and `Proposed` share bit-identical `qpsk_rad`). Descriptive controls (`FixedOffline_Best`, `c1_zero_same_c2`, `Rule30_TD_Exact`, plus Fig. 2 `[1,2,3]` & `N=64` exhaustive diagnostics) are wrapped in isolated `try...except` blocks that **explicitly persist any failed frame counts and `repr(exc)` exception strings in the output JSON** (never silently swallowed).
3. **Symmetric Per-`N` Warmup & Exact Cyclic Latin-Square Order Balance**:
   - `_ensure_warmup()` warms every `N_w in (64, 128, 256, 512)` across all selector modes and both Cholesky & LU banded solvers.
   - `FORMAL_SPEED_COUNTS = {64: 72, 128: 65, 256: 70, 512: 49}` (`12×6`, `13×5`, `10×7`, `7×7`) execute in cyclic Latin-square order `arms[(abs(tr_id) + pos) % L_N]` (`position_balance_exact_ok` gated in `PASS_CI_PRECISION_25PCT`).

## 2. Red-Line 1 Anchor, Seed & Boundary Gate (`PASS_REDLINE1`, Isolated From All Descriptive Diagnostics)

`PASS_REDLINE1` holds iff all five pure deterministic/anchor checks in `verify_redline1_mao26()` hold simultaneously:
1. `seed_disjointness_exact_ok == True` across all 2,192 formal seeds;
2. Noiseless band-interior `LC-BMMSE` relative error `< 1e-12`;
3. Full-width ($2w_i+1=N$) sparse-to-dense Gram diagonal error `full_gram_diag_rel_err < 1e-12` AND overlapping-support $\sigma_\Delta^2$ error `sigma_delta2_overlap_rel_err < 1e-12`;
4. Boundary & Eq. (45) enumeration invariant `boundary_eq45_and_wbc_exact_ok == True` (`14` inits `0..13` at `k=1`, `2` inits `0..1` and `w_bc[0]+w_bc[-1]==0` at `k=4`);
5. Pure Section V / Table II / Fig. 12 random-delay reproduction (`N=256, d=16, ws=16, Eb/N0=15 dB`, 3 distinct sorted random delays in `[0, 6]`, `{0,-4.675,-6.482} dB`, Jakes `4.17 kHz`, `20` frames): literal `PaperExact_Mao26` achieves `MC_BER` in `[1.5e-4, 2.0e-3]` AND strictly beats fixed-chirp $c_1 = \frac{1}{2N}$ ($k=1, \mathbf{w}_1^\star$). (Mixed Fig. 2 `l=[1,2,3]` + Fig. 10 `k=6` legend check and `N=64` exhaustive check are logged strictly in `isolated_diagnostics`.)

## 3. Red-Line 5 Direct Dev Dispersion Calibration & Sample-Size Derivation

1. **Direct Calibration on Disjoint Dev Seeds (`810000..885000` for v4 exact code across all `N` & all 4 rivals, plus `720000..735000` `24`-frame curve check)**:
   - **Speed scaling across all 4 rivals `{PaperExact_Mao26, FairSparse_Mao26_SPD, CoarseFine_Mao26, CoarseFine_Mao26_SPD}`** (measured $\mathrm{lhw}\cdot\sqrt{M}$ and geometric speedup):
     - `N=64` (`12` dev frames): `PaperExact = 29.54x` ($\mathrm{lhw}\sqrt{M} = 0.4858$), `MaoSPD = 24.27x` (`0.7826`), `CF = 28.33x` (`0.4593`), `CF_SPD = 23.68x` (`0.7387`) $\implies$ at **`M_64 = 72`** ($\sqrt{72} = 8.485$), expected max `lhw = 0.7826 / 8.485 = 0.0922 <= ln(1.25) = 0.22314`;
     - `N=128` (`15` dev frames): `PaperExact = 34.95x` (`0.4870`), `MaoSPD = 30.15x` (`0.7585`), `CF = 33.60x` (`0.4218`), `CF_SPD = 29.02x` (`0.6926`) $\implies$ at **`M_128 = 65`** ($\sqrt{65} = 8.062$), expected max `lhw = 0.7585 / 8.062 = 0.0941 <= 0.22314`;
     - `N=256` (`14` dev frames): `PaperExact = 74.97x` (`0.5662`), `MaoSPD = 65.77x` (`0.7513`), `CF = 73.37x` (`0.5024`), `CF_SPD = 63.15x` (`0.6639`) $\implies$ at **`M_256 = 70`** ($\sqrt{70} = 8.367$), expected max `lhw = 0.7513 / 8.367 = 0.0898 <= 0.22314`;
     - `N=512` (`14` dev frames): `PaperExact = 204.66x` (`0.4319`), `MaoSPD = 183.96x` (`0.6537`), `CF = 201.33x` (`0.4889`), `CF_SPD = 181.28x` (`0.6802`) $\implies$ at **`M_512 = 49`** ($\sqrt{49} = 7.000$), expected max `lhw = 0.6802 / 7.000 = 0.0972 <= 0.22314`.
   - **Bidirectional ablation ratios**: `A_only/Prop`: `3.66x` ($\mathrm{lhw}\sqrt{M} = 0.1511 \implies 0.0181$ at `M_256=70`), `10.54x` (`0.1619 \implies 0.0231` at `M_512=49`); `B_only/Prop`: `20.68x` (`0.8100 \implies 0.0955` at `M_64=72`), `25.14x` (`0.7850 \implies 0.0938` at `M_256=70`), `24.58x` (`0.6618 \implies 0.0945` at `M_512=49`), all `<= 0.22314`.
   - **Additive log-speedup shares $S_{\log}(\mathrm{Arm}, N; \mathrm{Base})$**: vs `MaoSPD`: `A_only` `0.690` ($\mathrm{hw}\sqrt{M}=0.0388$) & `0.548` (`0.0507`), `B_only` `0.050` (`0.0592`), `0.230` (`0.0482`), `0.386` (`0.0450`); vs `PaperExact`: `A_only` `0.699` (`0.0331`) & `0.557` (`0.0390`), `B_only` `0.105` (`0.1942`), `0.253` (`0.1080`), `0.398` (`0.0825`) $\implies$ expected max `hw = 0.1942 / sqrt(72) = 0.0229 <= 0.050`.
   - **`ACC256` accuracy curves across all 4 rivals `{PaperExact, MaoSPD, CF, CF_SPD}`**:
     - On `16` v4 dev frames (`B_blk = 32`): `dSNR_pt = -0.0269 dB` (`PaperExact`, `CF`) and `+0.0196 dB` (`MaoSPD`, `CF_SPD`), `BER_{16,19}` ratio `= 0.9565` ($\mathrm{lhw}\sqrt{M} = 0.5958$ for `PaperExact`/`CF`) and `0.9519` ($\mathrm{lhw}\sqrt{M} = 0.5482$ for `MaoSPD`/`CF_SPD`); on `24` dev frames (`720000`): `dSNR` $\mathrm{hw}\sqrt{M} = 0.6754\text{ dB}$, `BER_{16,19}` $\mathrm{lhw}\sqrt{M} = 0.4314$.
     - Locking **`FORMAL_N_ACC_256 = 336` frames** ($\sqrt{336} = 18.330$) AND increasing per-frame transmission blocks from `32` to **`B_blk = 96`** (`16,515,072` bits/SNR point, suppressing per-frame Binomial bit-count variance by $3\times$ at negligible `+0.3%` CPU cost) gives expected `dSNR hw <= 0.6754 / 18.330 = 0.0368 dB <= 0.050 dB` and expected `BER_{16,19} lhw <= 0.5958 / 18.330 = 0.0325` (further reduced toward `~0.024` by `B_blk = 96`) `<= 0.25 * ln(1.15) = 0.03494`.

2. **Hard-Locked Sample Sizes & `FUNNEL.md:84` Realized CI Half-Width Gate (`PASS_CI_PRECISION_25PCT`)**:
   - `M_64 = 72, M_128 = 65, M_256 = 70, M_512 = 49` frames; `M_acc = 336` frames (`B_blk = 96`).
   - `cap_ratio_lhw(tau) = min(0.25 * ln(tau), ln(1.25))`: `<= 0.22314` on all `10x / 5x / 3x` ratios, `<= 0.050 dB` on `dSNR_3e3` across all 4 rivals, `<= 0.03494` on `BER_{16,19}` across all 4 rivals, and `<= 0.050` on all `< 0.80` `S_log` shares.

## 4. Primary Pre-Registered Verdict (`verdicts.PASS_PRIMARY`)

`PASS_PRIMARY == True` iff `(not args.smoke)`, `PASS_REDLINE1`, `PASS_CI_PRECISION_25PCT`, and **ALL THREE** 95% paired CI-bound gates hold simultaneously:
1. **`PASS_SPEEDUP_10X`**: `CI95_low(geom_speedup(Rival / Prop, N)) >= 10.0` for **all** `N in {64, 128, 256, 512}` and **all four** rivals `Rival in {PaperExact_Mao26, FairSparse_Mao26_SPD, CoarseFine_Mao26, CoarseFine_Mao26_SPD}`.
2. **`PASS_ACCURACY_02DB`**: against **all four** speed rivals `{PaperExact_Mao26, FairSparse_Mao26_SPD, CoarseFine_Mao26, CoarseFine_Mao26_SPD}` on `N=256` (`M_acc = 336, B_blk = 96`), `CI95_high(SNR_at_3e3(Prop) - SNR_at_3e3(Rival)) <= 0.20 dB` AND `CI95_high(MC_BER_{16,19}(Prop) / MC_BER_{16,19}(Rival)) <= 1.15`.
3. **`PASS_ABLATION_AB`**: `CI95_low(A_only / Prop, N=512) >= 5.0`, `CI95_low(A_only / Prop, N=256) >= 3.0`, `CI95_low(B_only / Prop, N) >= 5.0` for `N in {64, 256, 512}`, **AND** `CI95_high(S_log(Arm, N; Base)) < 0.80` across all 5 ablation pairs for **both** `Base = FairSparse_Mao26_SPD` and `Base = PaperExact_Mao26`.
