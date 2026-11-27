# Frozen L2 Pre-Registration: `I-20261126-h01` (`runner h`, Round 13 Stage D — Post-`Sol #6` v6, Cleared by `Sol #7`)

- **Card**: [`ideas/cards/I-20261126-h01.md`](../cards/I-20261126-h01.md) — *饱和功放圆盘下MIMO-AFDM通感预编码*
- **Benchmark & Track**: `[放宽TWC] [分阶段] [轨B-ISAC]` (`§4 B1`)
- **Formal Script**: [`ideas/l2/h_l2_r13_h01.py`](h_l2_r13_h01.py)
- **Output Summary Path**: `ideas/l2/out_h_r13_h01/summary_h_r13_h01.json`
- **Subjective Prior Probability of `PASS_PRIMARY === true`**: **`0.96`** (re-verified on disjoint dev seeds `580000..586098` and v6 smoke after closing the final 2 narrow gating items from `Sol #6` static audit `r13-sol-prel2-h01-v5-20261126.md`; formal seeds `910000..979999` remain 100% untouched).

---

## 1. Competing Hypotheses & Falsification Contract (`research-checkpoint` §1)

- **Primary Hypothesis ($H_{\mathrm{prop}}$)**: In multiuser equalization-free downlink `16-QAM` `MIMO-AFDM ISAC` ($N_t=8, K=3, P_k=3, N=64, N_{\mathrm{CPP}}=8, Q=8, c_1=9/(2N), c_2=1/(2N)$, `63/64` net `16-QAM` payload + `1/64` blind scalar gain pilot at $m=0$) operating through per-antenna nonlinear solid-state `Rapp (p=2.5)` PAs at `0 dB` nominal saturation drive ($A_{\mathrm{sat}} = \sqrt{P_{\mathrm{nom}}/(N N_t)}$, `SNR = 26 dB`) with a `+33 dB` near-range scatterer accompanying a `0 dB` weak target, running **40 fixed iterations** of exact Douglas–Rachford alternating reflections (`M1`) from the minimum-norm representative $\mathbf{Y}_{\min}$ between the closed RZF-targeted affine multiuser+AFDM-chirp manifold $\mathcal{A}_q = \{\mathbf{y} : \mathcal{H}_q\mathbf{y} = \mathbf{b}_{\mathrm{comm},q},\; \mathbf{A}_{\mathrm{rad}}\mathbf{y} = \mathbf{u}_{\mathrm{des}}\}$ (`M2`, exact unregularized thin QR orthogonal projector) and the closed convex disk-ball set $\mathcal{D}(\rho_c A_{\mathrm{sat}}, P_{\mathrm{eff\_cap}})$ ($\rho_c=0.89$, $P_{\mathrm{eff\_cap}} = \min(P_{\mathrm{rad\_cap}}, P_{\mathrm{nom}}(1-\rho_c^5)^{0.4})$, exact 1D KKT Euclidean projector) followed by bounded smooth PA pre-inversion $\mathbf{X}_{\mathrm{in}} = g_{\mathrm{Rapp}}^{-1}(\mathbf{Y}_{\mathrm{fin}})$ (`M3`, guaranteed $\|\mathbf{X}_{\mathrm{in},q}\|_F^2 \le P_{\mathrm{nom}}$ with zero post-pre-inversion rescaling):
  1. Breaks the `16-QAM` saturation SER floor by `>= +0.080` simultaneously (`M=5` Bonferroni, `P1a`) against all 5 published / mother-method `0 dB IBO` rivals: converged zero-post-rescaling per-block-exact-power `Liu & Schober 2026` `WMMSE-MM` (`Rival_a1_Liu26_WMMSE_RawRapp`, evaluated under both blind `m=0` pilot scaling and exact payload-independent `Sui TCOM'26` Eq. 25–27 analytical Bussgang gain $g_{\mathrm{Sui},k} = K_{\mathrm{PA}} g_{\mathrm{lin},k}$ in `Rival_a1_SuiAnalyticalBussgang`), `WMMSE-MM + M3` (`Rival_a2_Liu26_WMMSE_PreInvRapp`), `WMMSE-MM + PostPACoupler` (`Rival_a4_Liu26_WMMSE_PostPACoupler`), and globally converged `Studer JSTSP'13` per-DAFT-bin minimum-$\ell_\infty$ ADMM `F_N -> A` mother-method port (`Rival_b1_PerBinStuderMinLinf`); beats `{Rival_a1, Rival_a2, Rival_b1} @ 28 dB` while independently executed at `24 dB` (using its own `24 dB` $P_{\mathrm{eff\_cap},24}$) by `>= +0.080` (`P1b`); isolates `Rival_b1`'s cross-bin off-diagonal coupling loss against the matched full-channel + chirp-pinned `Studer` minimum-$\ell_\infty$ control `Rival_b2_FullBlockStuderMinLinf` via `SER(Rival_b1) - SER(Rival_b2) >= +0.500` on both `Z0_mp` and `H1 26 dB` (`P1c`); AND beats even that full-channel + chirp-pinned `Studer` control at `26 dB` by `>= +0.0080` in `SER` and `>= +0.060` in $J_8$ (`P1d`);
  2. Pareto-dominates `7.5 dB` scalar input backoff (`Rival_a3_OptBackoff`) on equal-`Pfa` (`0.05`) blind localized target detection `LocBlindPd` (`>= +0.280`) and 8-block CPI joint ISAC reliability $J_8 = (1 - \mathrm{SER})^8 \cdot \mathrm{LocBlindHit}$ (`>= +0.280`) while maintaining non-inferior `SER` within margin `0.0100` (`ci_low(SER_a3 - SER_Prop) >= -0.0100`);
  3. Collapses on sensing (`>= +0.600` drop in `LocBlindPd`) under the strict single-factor diagnostic setting $c_1 = 0$ while holding $c_2 = 1/(2N)$ fixed (`Diag_c1Zero_SameAlg`).
- **Competing Null / Alternative Hypotheses (each would falsify `PASS_PRIMARY`)**:
  1. **$H_{\mathrm{preinv}}$ (Frontend-only / Bussgang / unregularized `Studer` min-$\ell_\infty$ explanation)**: Gifting payload-independent `Sui TCOM'26` Eq. (25)–(27) analytical Bussgang gain (`Rival_a1_SuiAnalyticalBussgang`) or bounded smooth `Rapp` pre-inverse `M3` (`Rival_a2`) eliminates the `>= 8%` `16-QAM` floor (`P1a` fails), OR running globally converged `Studer` minimum-$\ell_\infty$ ADMM on the full coupled AFDM channel + `M2` chirp manifold (`Rival_b2_FullBlockStuderMinLinf`) matches `Prop` on `SER` or $J_8$ without `Prop`'s interior pre-inversion disk-ball + RZF + `M3` (`P1d` fails).
  2. **$H_{\mathrm{backoff}}$ (Scalar IBO tuning explanation)**: Backing off `WMMSE-MM` by `7.5 dB` (`Rival_a3_OptBackoff`) matches `Prop` on `LocBlindPd` or $J_8$, or beats `Prop` on `SER` beyond the `0.0100` non-inferiority bound (`P2` fails).
  3. **$H_{\mathrm{decoupled}}$ (Pure single-factor sufficiency)**:
     - `Abl_Aonly_NoChirpPin` (pure single-factor removal of $\mathbf{A}_{\mathrm{rad}}\mathbf{y}=\mathbf{u}_{\mathrm{des}}$ ONLY: keeps the exact same $\mathbf{b}_{\mathrm{comm},q}$ communication equality RHS, starts 40-step DR from the exact minimum-norm point $\mathbf{Y}_{\min,h}$ of $\{\mathcal{H}_q\mathbf{y}=\mathbf{b}_{\mathrm{comm},q}\}$ with zero random nullspace injection, and keeps identical $P_{\mathrm{eff\_cap}}$, 40-step DR `M1`, and `M3`), OR
     - `Abl_Bonly_NoDiskProj` (pure single-factor removal of 40-step disk DR `M1`: sets `n_dr = 0` on the exact same $\mathbf{Y}_{\min}$, keeping $P_{\mathrm{eff\_cap}}$ ball and `M3`),
     already recovers `>= 80%` of the $J_8$ gain (`P3a` fails), or removing `M1`, `M2`, or `M3` (`Abl_NoPreInv_RawRapp`, exact same $\mathbf{Y}_{\mathrm{fin}}$ without `M3`) fails its paired attribution bound (`P3b` fails).
  4. **$H_{\mathrm{sym}}$ (Single-factor $c_1 = 0$ invariance)**: Setting only $c_1 = 0$ while keeping $c_2 = 1/(2N)$ fixed (`Diag_c1Zero_SameAlg`) preserves `LocBlindPd` (`P2b` fails).

---

## 2. Independent Dev Convergence Verification (`>= 32` Scenes) & Redline 5 Sample Sizing

Disjoint dev calibrations (`dev_verify_v3_exact.py` on `360000..390095`, `check_v5_margins.py` on `580000..586098`, zero overlap with formal `910000+`) verified:
1. **Zero-Post-Rescaling `Liu & Schober 2026` `WMMSE-MM` Per-Block Exact Power & Per-Scene Convergence (`min_iter = 16, max_iter = 60, rel_tol = 1e-3`)**:
   - Fixed-step curve on `32` `Z0_mp` scenes (`370000..370031`, `30 dB`, 3-path linear PA): `4` iters (`SER_blind = 0.00238`, sum-rate `27.26`, max rel step `0.0762`) -> `8` iters (`0.00058`, `27.92`, max `0.0357`) -> `12` iters (`0.00010`, `28.11`, max `0.0357`) -> `16` iters (`0.000000`, `28.19`, max `0.00278`).
   - With `a_perp_comm` double-orthogonalized against the **unweighted** block communication channel $\mathbf{H}_{s,q}$ (**explicitly measured & gated at $\|\mathbf{H}_{s,q}\mathbf{a}_{\perp,\mathrm{comm}}\|_2 < 10^{-12}$ in both Redline 1 and all 9 branches of `G_HYGIENE`**) and **ZERO post-loop rescaling** of `W_sub_list`:
     - The **actual transmitted matrices `W_sub_list`** are **100% bit-for-bit identical** to the matrices evaluated in `obj_hist[-1]` (zero post-loop perturbation of $\mathbf{H}_{s,q}\mathbf{W}_q$);
     - **Per-block deterministic expected power error**: `max_q | ||W_{c,q}||_F^2 + ||w_{s,q}||_2^2 - P_nom | <= 7.11e-13 < 1e-9` directly from the KKT solver;
     - **Per-scene monotonicity & `< 0.1%` final step**: `100%` monotone (`obj_hist[t+1] >= obj_hist[t] - 1e-9`) across all 9 branches, with **per-scene `max(rel_last_step) = 0.000996 < 0.0010 << 0.010`**.
2. **Globally Converged `Studer JSTSP'13` Minimum-$\ell_\infty$ ADMM Pair (`Rival_b1` vs `Rival_b2`, `min_admm = 100, max_admm = 240`)**:
   - **Flat-channel exact parity**: On `Z0_flat` ($\ell=0, \nu=0$), `||X_b1 - X_b2||_F / ||X_b2||_F <= 6.03e-14 < 1e-12`, `SER(b1) = SER(b2) = 0.000000`.
   - **Certified End-to-End Global Optimality**: With relative primal-vs-dual residual balancing (`it < 60`) and exact unrelaxed ADMM (`alpha_or = 1.0` for `it >= 75`), across all `Z0_mp`, `H0`, and `H1` scenes, both `Rival_b1` and `Rival_b2` achieve:
     - Actual final-step iterate consistency `||X_K - Z_K||_2 / ||X_K||_2 <= 0.010`;
     - **Standard unprojected Boyd relative dual residual** `||rho (Z_K - Z_{K-1})||_2 / ||rho U_K||_2 == ||Z_K - Z_{K-1}||_2 / ||U_K||_2 <= 0.010` (Boyd et al. 2011 Sec. 3.1.1 Eq. 3.8 & Sec. 3.3.1);
     - Peak objective step stabilization `| ||X_K||_inf - ||X_{K-1}||_inf | / ||X_K||_inf <= 0.010`;
     - **Exact Hölder $(\ell_1, \ell_\infty)$ global relative duality gap** `(||X_fin[q]||_inf - d_q) / ||X_fin[q]||_inf <= 0.025` (certifying global $\ell_\infty$ optimality on every block $q$).
   - **True Converged Multipath & Nonlinear PA Attribution (`580000..586098`)**:
     - On `Z0_mp` (`30 dB`, linear PA): `Rival_b2` gets `SER = 0.000000 < 0.010`, while `Rival_b1` gets `SER = 0.8577` (`b1 - b2 = +0.8577`).
     - On `H1 26 dB` (`0 dB IBO` `Rapp p=2.5` PA): `Rival_b1` gets `SER = 0.9208` (`b1 - b2 = +0.8953`); restoring full coupled $\mathcal{H}_q$ + `M2` chirp equality in `Rival_b2` reduces `SER` to **`0.0256`** (`2.56%`, $J_8 = 0.828$), while `Prop_Full_AFDM` (adding RZF + interior pre-image disk $\mathcal{D}(\rho_c A_{\mathrm{sat}}, P_{\mathrm{eff\_cap}})$ + smooth `M3` `Rapp` inverse) drives `SER` down **`3.9x` further to `0.0066` (`0.66%`)** and raises $J_8$ to **`0.953`** (`b2 - Prop SER = +0.0189 [SD 0.0187]`, `Prop - b2 J_8 = +0.1250`).

**Frozen Formal Sample Sizes & Disjoint Seed Ranges** (zero overlap with Stage A `1000..7999`, Stage C `8000..8999`, Dev `110000..599999`, or Smoke `210000..475999`):
- `Z0_flat`: **`N_z0_flat = 64`**, seeds `910000 .. 910063`
- `Z0_mp`: **`N_z0_mp = 64`**, seeds `920000 .. 920063`
- `H0_cal`: **`N_cal = 399`**, seeds `930000 .. 930398` (exact order-statistic index $k = \lceil 0.95 \times 400 \rceil = 380 \implies \mathbb{E}[\mathrm{Pfa}] = 20/400 = 0.050000$)
- `H0_val`: **`N_val = 400`**, seeds `940000 .. 940399` (exact 11-arm familywise `99%` Bonferroni `BetaBinomial(400, 20, 380)` two-sided `[0.005/11, 1 - 0.005/11]` interval **`[4, 45]`**, i.e., `[0.0100, 0.1125]`)
- `H1_pos`: **`N_pos = 1040`**, seeds `950000 .. 951039` (primary `26 dB` evaluation; first **`N_xsnr = 256`** scenes `950000 .. 950255` also evaluate SNR-independent paired `Prop @ 24 dB` vs `{Rival_a1, Rival_a2, Rival_b1, Rival_b2} @ 28 dB`)
- Secondary generalizations:
  - `S2_Nt12K4` ($N_t=12, K=4$, `Rapp p=2.5`, `26 dB`): `N_cal_s2 = 199` (`960000..960198`, $k=190$), `N_pos_s2 = 96` (`965000..965095`)
  - `S3_SEL` ($N_t=8, K=3$, `SEL` hard-clipping PA `Sui TCOM'26` Eq. 25–26, `26 dB`): `N_cal_s3 = 199` (`970000..970198`, $k=190$), `N_pos_s3 = 96` (`975000..975095`)

**Projected 95% CI Half-Width Verification at `N_pos = 1040` / `N_z0_mp = 64` (All Strictly `<= 25%` of Threshold)**:
- `P1a` (`M=5` Bonferroni $t_{1039, 1-0.05/10} = 2.5806$, threshold `0.080`, 25% cap `0.0200`): projected max `ci_hw = 2.581 * 0.066 / sqrt(1040) = 0.0053 <= 0.0200`.
- `P1b` (`M=3` Bonferroni $t_{255, 1-0.05/6} = 2.4100$, `N_xsnr=256`, threshold `0.080`, 25% cap `0.0200`): projected max `ci_hw = 2.410 * 0.068 / sqrt(256) = 0.0102 <= 0.0200`.
- `P1c` (`SER(Rival_b1) - SER(Rival_b2)` paired-$t$ on `Z0_mp` `N=64` & `H1` `N=1040`, threshold `0.500`, 25% cap `0.1250`): projected `ci_hw(Z0_mp) ~ 0.037 <= 0.1250`, `ci_hw(H1) ~ 0.004 <= 0.1250`.
- `P1d_ser` (`SER(Rival_b2) - SER(Prop)` paired-$t$ on `H1` `N=1040`, threshold `0.0080`, 25% cap `0.00200`): projected `ci_hw = 1.962 * 0.0187 / sqrt(1040) = 0.00114 <= 0.00200` (`mean ~ 0.0189, ci_low ~ 0.0178 >= 0.0080`).
- `P1d_j8` (`J_8(Prop) - J_8(Rival_b2)` paired-$t$ on `H1` `N=1040`, threshold `0.060`, 25% cap `0.0150`): projected `ci_hw = 1.962 * 0.15 / sqrt(1040) = 0.0091 <= 0.0150` (`mean ~ 0.125, ci_low ~ 0.116 >= 0.060`).
- `P2a_pd_bo` (nominal 95% Newcombe Method 10 score CI, threshold `0.280`, 25% cap `0.0700`): projected `ci_hw = 0.030 <= 0.0700`.
- `P2a_joint_bo` (`J_8(Prop) - J_8(Rival_a3)` paired-$t$ 95% CI, threshold `0.280`, 25% cap `0.0700`): projected `ci_hw = 0.0283 <= 0.0700`.
- `P2a_ser_bo` (`SER(Rival_a3) - SER(Prop)` paired-$t$ 95% CI, non-inferiority bound `-0.0100`, frozen precision scale `0.0100` -> 25% cap `0.00250`): projected `ci_hw = 0.00128 <= 0.00250`.
- `P2a_pd_a1` (nominal 95% Newcombe Method 10 score CI, threshold `0.160`, 25% cap `0.0400`): projected `ci_hw = 0.029 <= 0.0400`.
- `P2b_c1zero` (nominal 95% Newcombe Method 10 score CI, threshold `0.600`, 25% cap `0.1500`): projected `ci_hw = 0.004 <= 0.1500`.
- `P3a_recov` ($\eta_A, \eta_B < 0.80$ paired bootstrap `B=4000`, cap `0.200`): projected `ci_hw ~ 0.017 <= 0.200`.
- `P3b_M2` (nominal 95% Newcombe Method 10 score CI, threshold `0.550`, 25% cap `0.1375`): projected `ci_hw = 0.005 <= 0.1375`.
- `P3b_M1` (`SER(Abl_Bonly) - SER(Prop)` paired-$t$, threshold `0.040`, 25% cap `0.0100`): projected `ci_hw = 0.0031 <= 0.0100`.
- `P3b_M3` (`SER(Abl_NoPreInv) - SER(Prop)` paired-$t$, threshold `0.0036`, 25% cap `0.00090`): projected `ci_hw = 0.00069 <= 0.00090`.

---

## 3. Exact Frozen Verdict Definition (`verdicts.PASS_PRIMARY`) & Redline 4 Post-L2 Contract

`verdicts.PASS_PRIMARY` is `true` **if and only if ALL FOUR top-level gates `G_HYGIENE`, `P1`, `P2`, and `P3` evaluate to `true`** (Redline 4 binding contract: if `PASS_PRIMARY` evaluates to `false` on formal L2, the card MUST NOT be promoted to `active L2`; all raw observations, frozen verdict, and untested `[H/M/L]` explanations are reported honestly and the card is marked `killed` or `parked` per `ideas/prompts/round-agy-extra.md` Redline 4):

1. **`G_HYGIENE`**:
    - `redline1_max_err < 1e-12` AND `uc_subspace_null_err < 1e-15` (unitary DAFT; 2-block continuous multi-tap CPP + global-sample Doppler `< 1e-12`; fast FFT-CPP forward & adjoint parity; `Uc` row-template subspace nulling `< 1e-15` & inner-product parity `< 1e-12`; thin QR affine projection; batched 1D KKT disk-ball projection; `Studer` Moreau $\ell_\infty$ prox variational inequality & flat-channel `b1 == b2` parity `< 1e-12`; production `build_liu26_wmmse_mm_cpi -> sui_analytical_bussgang_gain_from_precoder` unit-gain extraction check `g_sui == 1.0`, payload invariance `< 1e-12`, & zero-post-rescaling per-block exact `WMMSE` power `< 1e-9`; Rapp high-IBO linear limit & bounded pre-inversion identity; plus `Sui` `Rapp(2000) -> SEL` limit `< 1e-3`);
    - `z0_flat_max_ser < 0.010` across all 11 arms + `Rival_a1_SuiAnalyticalBussgang` AND `z0_mp_max_capable < 0.010` across all 10 multipath-capable arms (**including `Rival_b2_FullBlockStuderMinLinf`**) + `Rival_a1_SuiAnalyticalBussgang`;
    - `wmmse_convergence_ok == true`: `100%` monotone objective (`obj_hist[t+1] >= obj_hist[t] - 1e-9` floating-point tolerance) on the **exact unrescaled transmitted matrices `W_sub_list`** across **all 9 branches** (`z0_flat`, `z0_mp`, `h0_cal`, `h0_val`, `h1_26dB`, `p1b_24dB`, `p1b_28dB`, `s2_Nt12K4`, `s3_SEL`), **per-scene `max(wmmse_rel_last_step) < 0.010` across all 9 branches**, **per-block deterministic expected power error `wmmse_max_blk_pow_err < 1e-9` across all blocks & scenes**, AND **explicit unweighted communication-nullspace orthogonality `wmmse_max_aperp_null_err = max ||Hs_q @ a_perp_comm||_2 < 1e-12` across all blocks & scenes** (plus `< 1e-12` in Redline 1);
    - `studer_admm_convergence_ok == true`: across **all scenes of all 9 branches** (explicitly including `Z0_mp` and `H1`) for BOTH `Rival_b1_PerBinStuderMinLinf` and `Rival_b2_FullBlockStuderMinLinf`, actual final-step iterate consistency `iter_primal_rel_max <= 0.010`, **standard unprojected Boyd relative dual residual `dual_rel_max = max ||Z_K - Z_{K-1}||_2 / ||U_K||_2 <= 0.010`**, peak objective step stabilization `peak_step_rel_max <= 0.010`, **exact Hölder $(\ell_1, \ell_\infty)$ global relative duality gap `rel_duality_gap_max <= 0.025`**, AND `peak_vs_l2min_max_ratio <= 1.0 + 1e-9`;
    - All 11 arms have strictly tie-free `H0_cal` scores and independent `H0_val` false-alarm counts $F_{\mathrm{val}} \in [4, 45]$ (exact 11-arm familywise `99%` Bonferroni `BetaBinomial(400, 20, 380)` interval `[0.0100, 0.1125]`);
    - Power & post-PA residual invariants: `Prop_Full_AFDM` satisfies `p_in_max <= P_nom + 1e-9`, `p_out_mean <= p_out_mean(Rival_a1_Liu26_WMMSE_RawRapp) + 1e-9`, `z0_max_post_pa_rel_res < 1e-12`, `h1_mean_post_pa_comm_rel_res <= 0.050`, and `h1_mean_post_pa_chirp_rel_res <= 0.050`.
2. **`P1` (`P1a and P1b and P1c and P1d` — Communication Saturation Floor Wall-Breaking & `Studer` Two-Step Attribution)**:
    - `P1a`: For all 5 published / mother-method `0 dB IBO` rivals $r \in \{\text{Rival\_a1\_Liu26\_WMMSE\_RawRapp}, \text{Rival\_a1\_SuiAnalyticalBussgang}, \text{Rival\_a2\_Liu26\_WMMSE\_PreInvRapp}, \text{Rival\_a4\_Liu26\_WMMSE\_PostPACoupler}, \text{Rival\_b1\_PerBinStuderMinLinf}\}$ on `N_pos = 1040` (`26 dB`, simultaneous Bonferroni $M=5$): `ci_low(SER(r) - SER(Prop)) >= 0.080` AND `ci_hw <= 0.0200`.
    - `P1b`: For all 3 rivals $r \in \{\text{Rival\_a1}, \text{Rival\_a2}, \text{Rival\_b1}\}$ on `N_xsnr = 256` (`r @ 28 dB` vs SNR-independent `Prop @ 24 dB`, simultaneous Bonferroni $M=3$): `ci_low(SER(r@28dB) - SER(Prop@24dB)) >= 0.080` AND `ci_hw <= 0.0200` (with `Rival_b2 @ 28 dB vs Prop @ 24 dB` logged diagnostically in `P1b_b2_28vs24_diag`).
    - `P1c`: Paired pure single-factor attribution `SER(Rival_b1_PerBinStuderMinLinf) - SER(Rival_b2_FullBlockStuderMinLinf)` satisfies `ci_low >= 0.500` AND `ci_hw <= 0.1250` on **both** `Z0_mp` (`N_z0_mp = 64`) and `H1 26 dB` (`N_pos = 1040`).
    - `P1d`: Paired superiority of `Prop_Full_AFDM` over the full-channel + chirp-pinned `Studer` minimum-$\ell_\infty$ control `Rival_b2_FullBlockStuderMinLinf` on `H1 26 dB` (`N_pos = 1040`): `SER(Rival_b2) - SER(Prop)` satisfies `ci_low >= 0.0080` AND `ci_hw <= 0.00200`, AND `J_8(Prop) - J_8(Rival_b2)` satisfies `ci_low >= 0.060` AND `ci_hw <= 0.0150`.
3. **`P2` (ISAC Backoff Pareto Dominance & Single-Factor `c_1 = 0` Non-Degeneracy)**:
    - `P2a_pd_bo`: Nominal 95% Newcombe Method 10 paired score CI on `LocBlindPd(Prop) - LocBlindPd(Rival_a3_OptBackoff)` satisfies `ci_low >= 0.280` AND `ci_hw <= 0.0700`.
    - `P2a_joint_bo`: Paired-$t$ 95% CI on `J_8(Prop) - J_8(Rival_a3_OptBackoff)` satisfies `ci_low >= 0.280` AND `ci_hw <= 0.0700`.
    - `P2a_ser_bo`: Paired-$t$ 95% CI on `SER(Rival_a3_OptBackoff) - SER(Prop)` satisfies `ci_low >= -0.0100` AND `ci_hw <= 0.00250`.
    - `P2a_pd_a1`: Nominal 95% Newcombe Method 10 paired score CI on `LocBlindPd(Prop) - LocBlindPd(Rival_a1_Liu26_WMMSE_RawRapp)` satisfies `ci_low >= 0.160` AND `ci_hw <= 0.0400`.
    - `P2b_c1zero`: Nominal 95% Newcombe Method 10 paired score CI on `LocBlindPd(Prop) - LocBlindPd(Diag_c1Zero_SameAlg)` (with $c_2 = 1/(2N)$ fixed and only $c_1 = 0$) satisfies `ci_low >= 0.600` AND `ci_hw <= 0.1500`.
4. **`P3` (Strict Single-Factor `< 80%` Bidirectional Ablation & Sub-Mechanism Attribution)**:
    - `P3a`: On unified 8-block CPI joint ISAC metric $J_{8,i} = (1 - \mathrm{SER}_i)^8 \cdot \mathrm{LocBlindHit}_i$ relative to `Rival_a1_Liu26_WMMSE_RawRapp`, paired percentile bootstrap (`B = 4000`) 95% CIs for both $\eta_A$ (`Abl_Aonly_NoChirpPin`) and $\eta_B$ (`Abl_Bonly_NoDiskProj`) satisfy `denom_valid == true` (`denom_point >= 0.10` and `min_boot(mp - mb) > 0.05`, strict RFC-8259 JSON), `ci_high < 0.80`, AND `ci_hw <= 0.200`.
    - `P3b_M2`: Nominal 95% Newcombe Method 10 paired score CI on `LocBlindPd(Prop) - LocBlindPd(Abl_Aonly_NoChirpPin)` satisfies `ci_low >= 0.550` AND `ci_hw <= 0.1375`.
    - `P3b_M1`: Paired-$t$ 95% CI on `SER(Abl_Bonly_NoDiskProj) - SER(Prop)` satisfies `ci_low >= 0.040` AND `ci_hw <= 0.0100`.
    - `P3b_M3`: Paired-$t$ 95% CI on `SER(Abl_NoPreInv_RawRapp) - SER(Prop)` satisfies `ci_low >= 0.0036` AND `ci_hw <= 0.00090`.
