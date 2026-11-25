# Pre-Registered L2 Protocol, Competing Hypotheses & Kill Gates — Runner `g` Round 5 Batch 1 (2026-11-23)

- **Frozen BEFORE running `deinlab` evaluation**: `2026-11-23 06:42 +08:00`
- **Skill followed**: `~/projects/personal-ai-workflow/skills/research-checkpoint/SKILL.md` (§1 Pre-Registration Checklist & §2 Three-Layer Reporting) + Step 6 Cross-Family Novelty Screen (`ideas/reviews/g-sol-novelty-r5s1-20261123.md`).
- **Cards in Batch 1 (all classified `(1b)` at Step 6)**:
  1. `I-20261123-g01` (`core` Channel C, parent `I-20261122-g15`)
  2. `I-20261123-g02` (`explore`, Anchor D+A)
  3. `I-20261123-g04` (`core` Channel A+B, Anchor A)
- **Global Simulation & Statistical Discipline**:
  1. **Strictly Disjoint Seed / Frame Partitions (Zero Test Leakage, Zero Overlap with Prior Rounds)**:
     - **`g01`** (avoiding `g15`'s `45800..45829` and `46000..46199`!):
       - Smoke / noiseless / interface parity gate: frames `42990..42991`
       - Training set (learned arms ONLY): frames `43000..43399` (`400` frames, mixed $\beta_{\mathrm{train}} \in \{0.0, 0.25\}$ at `SNR = 6.0 dB`, scenario `U`, $\rho = 0.25$)
       - Dev / scalar calibration set (for `free6_iso_cal`, `full_pcsbl_cal`, `zero_train_collinear_cal` scalar multipliers & early-stopping selection ONLY): frames `43500..43579` (`80` frames)
       - **Unseen Evaluation Set**: frames **`47000..47239` (`240` paired frames)** across `sinc` ($\beta=0.0$), unseen `rc015` ($\beta=0.15$), and unseen `rc035` ($\beta=0.35$) at `SNR in {5.5, 6.0, 7.0} dB`.
     - **`g02`**:
       - Smoke / noiseless recovery gate: seeds `84800..84802`
       - Dev / regularization calibration set: seeds `84900..84939` (`40` scenarios)
       - **Unseen Evaluation Set**: seeds **`85000..85299` (`300` paired scenarios)** across $Q \in \{4, 8\}$, $\mathrm{SNR} \in \{12, 16, 20\}\text{ dB}$, and controlled coupling switch (`mc_rms = 0.0` vs `mc_rms = 0.18` (`-14.9 dB`) nearest-neighbor + `0.056` (`-25.0 dB`) unmodeled 2nd-nearest-neighbor + `0.3 dB / 3 deg` element pattern perturbation).
     - **`g04`**:
       - Smoke / noiseless gate: seed `80900` (`2` frames)
       - Dev / `MAD`-threshold & regularization calibration set: seeds `81000..81059` (`60` frames; Note: `81000..81029` were inspected during pre-L2 `PCP-OTFS` baseline sanity check and are strictly confined to dev calibration, NEVER evaluation!)
       - **Unseen Evaluation Set**: seeds **`82000..82399` (`400` paired frames per regime)** across:
         - Regime 0 (`clean`, `p_imp = 0.0`): AWGN + multipath control at `SNR = 11.5 dB`
         - Regime 1 (`bg_64x8`): Bernoulli-Gaussian (`p_imp = 0.045, sig2_imp = 12.0`), $M \times K = 64 \times 8$, `SNR in {10.0, 11.5, 13.0, 14.5} dB`
         - Regime 2 (`mca_64x8`): Middleton Class-A (`A = 0.05, Gamma = 0.08`, canonical non-Gaussian impulsive model), $M \times K = 64 \times 8$, `SNR in {11.5, 13.0} dB`
         - Regime 3 (`bg_32x16`): Bernoulli-Gaussian (`p_imp = 0.045, sig2_imp = 12.0`), **aspect ratio $M \times K = 32 \times 16$** (more favorable to OTFS: lower impulse-pilot peak & 16 time slots per delay row!), `SNR in {11.5, 13.0} dB`.
  2. **Statistical Unit & Intervals**: Paired frame / scenario is the cluster unit; all key contrasts report 4,000-resample paired bootstrap 95% CIs (`_argv` and `_config` recorded in every `summary.json`).
  3. **Explicit Python Boolean Enforcement**: Every gate below is evaluated directly in Python (`read` mode) into `verdicts` in `summary.json` without post-hoc relabelling.

---

## 1. `I-20261123-g01` (`core` — Collinear Phase-Gated Prior & Split-Ratio Noise Calibration vs Deep Unfolding)

### A. Competing Hypotheses (`research-checkpoint` §1.1)
- **$H_{\mathrm{null}}$ (Isotropic scalar calibration already suffices)**: Under continuous fractional delay and unknown RRC roll-off, equal-variance 6-tap clusters with dev-calibrated scalar noise inflation (`free6_iso_cal`) match both zero-training collinear projection and learned unfolding within `< 4 pp` FER and `< 0.02 bit/sym` true-bit signed GMI.
- **$H_{\mathrm{phys}}$ (Closed-form real-collinear projection + calibrated noise captures the gain without neural unfolding)**: Projecting each 6-tap cluster onto its principal 1D real axis $\theta_j = \frac{1}{2}\arg\sum_k h_{j,k}^2$ with in-phase neighbor weighting (`zero_train_collinear_cal`) substantially beats `free6_iso_cal` and `full_pcsbl_cal`, while adding ~68 learned unfolding parameters (`collinear_unfold`) adds `< 4 pp` FER (`< 0.025 bit/sym` GMI) over `zero_train_collinear_cal`.
- **$H_{\mathrm{unfold}}$ (Collinear physics + 2-round BCE-unfolded prior/temperature schedule both contribute)**: `collinear_unfold` beats `free6_iso_cal`, `full_pcsbl_cal`, `split_noise_only`, AND phase-blind `mlp_mag_unfold`, AND improves over `zero_train_collinear_cal` by adapting shrinkage & LLR temperature across Round 0 (high data interference) and Round 1 (post-LDPC feedback).

### B. Design Validity & Anti-Confound Controls (`Sol` Step 6 Lines 30–32 + `Rule 21`)
- **Matched detector interface**: ALL non-oracle 48-tap arms run through the exact same `scalar_joint_hetero` (`iterations=20, damping=0.3`) + `decoder_messages(maxiter=50)` 2-round loop from identical Round-0 `pilot_front` 2D peak clusters (`free6_native_cal` also logged to verify exact parity with `native.scalar_joint(gain_mode='joint')`).
- **True signed-bit metric**: Soft output quality is measured ONLY by **signed true-bit GMI** ($2 \cdot \mathbb{E}[1 - \log_2(1 + \exp(-b_{\pm} L_{\mathrm{ext}}))]$ using `ALL-I THEN ALL-Q` bit convention from `messages.py:1`) and **decoded FER** (`stage3.e1.gd.score`), never unsigned `tanh(|L|/2)^2`.
- **Full `PC-SBL` baseline**: `full_pcsbl_cal` uses exact posterior second moments $e_m = |h_m|^2 + v_{h,m}$ and coupled precision $\alpha_m = (e_m + \beta_{\mathrm{pc}}(e_{m-1}+e_{m+1}) + \epsilon)^{-1}$ with dev-calibrated $(\beta_{\mathrm{pc}}^*, \kappa_{\mathrm{pc}}^*)$.
- **Seven paired arms**: `ora_true48_fix`, `free6_iso_cal`, `full_pcsbl_cal`, `split_noise_only`, `zero_train_collinear_cal`, `mlp_mag_unfold` (same parameter count & BCE training, fed only $|h|^2$ without collinear real/quadrature decomposition), `collinear_unfold`.
- **Premortem**: Most likely failure mode is that after proper dev-set scalar noise-multiplier calibration, `free6_iso_cal` (or `zero_train_collinear_cal`) already reaches within `< 8 pp` of `collinear_unfold` because $P=8$ clusters overlap or Round-0 Doppler error rotates intra-cluster tap phases slightly; our 7-arm ladder isolates this cleanly.
- **Prior probabilities**: $P(H_{\mathrm{unfold}}\text{ passes all gates}) = 0.45$, $P(H_{\mathrm{phys}}\text{ wins but unfolding adds }<4\text{ pp}) = 0.30$, $P(H_{\mathrm{null}}) = 0.25$.

### C. Pre-Registered Boolean Gates (`verdicts['g01']`)
1. `gate_headroom`: At `6.0 dB` `sinc`, `FER(free6_iso_cal) - FER(ora_true48_fix) >= 0.20` (`>= 20 pp` true gap).
2. `dir_beats_baselines_and_mag_mlp`: Pooled across `sinc` and unseen `rc035` at `6.0 dB` (`480` paired evaluations), `collinear_unfold` has strictly lower `FER` than `free6_iso_cal`, `full_pcsbl_cal`, `split_noise_only`, AND `mlp_mag_unfold`, with paired bootstrap 95% CI upper bound of `FER(collinear_unfold) - FER(free6_iso_cal) < 0` AND `FER(collinear_unfold) - FER(mlp_mag_unfold) < 0`.
3. `quant_fer_or_gmi_gain`: At `6.0 dB` pooled across `sinc` + unseen `rc015` + unseen `rc035`, `FER(free6_iso_cal) - FER(collinear_unfold) >= 0.10` (`>= 10 pp` FER reduction; or `>= 0.8 dB` SNR gain at `25%` FER across `{5.5, 6.0, 7.0} dB`).
4. `unfold_beats_zerotrain_by_4pp`: At `6.0 dB` pooled across the 3 pulses, `FER(zero_train_collinear_cal) - FER(collinear_unfold) >= 0.04` (`4 pp`) OR signed Round-0+1 `GMI` gain `>= 0.03 bit/sym` (`paired 95% CI > 0`). *(Decision rule: `PASS_FULL_UNFOLD` iff 1+2+3+4 all True; if 1+2+3 hold for `zero_train_collinear_cal` while 4 is False, `g01` is marked `KILL` as an unfolding card — per `FUNNEL.md` no silent relabelling — and its closed-form result is logged for `c08`!)*

---

## 2. `I-20261123-g02` (`explore` — Reconfigurable MIMO Mode-Sampling Reversal & Single-Snapshot Multiport Extrapolation)

### A. Competing Hypotheses (`research-checkpoint` §1.1)
- **$H_1$ (Full-pair + aperture-balanced `Balanced_DB` + EIV/ML multiport calibration)**: Switching mutual coupling ON flips `Interleaved / EqualMom_TM` vs `Blocks` by `> 6 dB` under the exact same continuous solver; `Balanced_DB_MC` restores full-aperture resolution at $Q=4$ (`> +5 dB` over `Blocks_MC` and `Inter_MC`) AND beats `BalancedRand_MC` by `>= 1.5 dB` at critical $Q=8, N_r=64$ under general mirror-symmetric switch-pair coupling (even with unmodeled `-25 dB` 2nd-neighbor coupling, `0.3 dB / 3 deg` pattern perturbation, and blind mode selection).
- **$H_2$ (Low-dimensional reciprocal impedance sharing suffices)**: Under rank-1 load-impedance reciprocal physics ($\mathbf{C}^+_{a,b}$ governed by $Q$ scalar load impedances rather than $Q^2$ pair entries), `RecipLowDim_Balanced` matches `Balanced_DB_MC` at $Q=8$, bounding the `De Bruijn` advantage over `BalancedRand` to general non-separable pair coupling (e.g. asymmetric parasitic switch geometry).
- **$H_0$ (EIV noise bias or continuous angle optimization erases single-snapshot identifiability)**: Jointly optimizing continuous angles $(\mathbf{u}, \mathbf{v})$ and $\mathbf{C}$ collapses (`projected Jacobian sigma_min ≈ 0`) or fails to improve blind-selected uplink sum-rate by `>= 25%` over `Uncoupled_PDJ`.

### B. Design Validity & Anti-Confound Controls (`Sol` Step 6 Lines 55–61)
- **Spatially balanced + mirror-complete `Balanced_DB`**: Constructed via Eulerian tour search over $K_Q$ maximizing $\min_k \mathrm{Var}(\{n : a_n = k\})$ (achieving `min_var >= 280` vs naive lexicographic `19.36`!) and cutting the open boundary at `(0,1)` whose mirror image `(6,7)` remains interior (`64/64` observed parameters!).
- **Identical continuous solver & controlled $\mathbf{C}=0$ vs $\mathbf{C}\neq 0$ switch**: Every layout runs through the exact same `PDJ + continuous L-BFGS-B/coordinate-Newton angle refinement + EIV-debiased & alternating Gaussian ML multiport refinement` on both $\mathbf{C}=0$ and $\mathbf{C}\neq 0$.
- **Blind data-mode selection**: Every arm chooses $\hat{a}_n^{\mathrm{data}} = \arg\max_k \|\hat{\mathbf{H}}^{(k)}_{n,:}\|_2^2$ from **its own estimated channel** (never true CSI!), and uplink sum-rate is evaluated on the true physical channel induced by $\hat{\mathbf{a}}^{\mathrm{data}}$ (including `-25 dB` 2nd-neighbor coupling and pattern perturbation).
- **Both coupling physics tested at $Q=8$**: (i) General mirror-symmetric pair coupling (`64` real/complex degrees of freedom), and (ii) Rank-1 port-load reciprocal multiport network $(\mathbf{Z}_{\mathrm{ant}} + \mathrm{diag}(\mathbf{z}_{\mathrm{load}}(\mathbf{a})))^{-1}$ (`Sol` line 59 & 61).
- **Prior probabilities**: $P(\text{all gates pass}) = 0.72$.

### C. Pre-Registered Boolean Gates (`verdicts['g02']`)
1. `dir_controlled_ranking_reversal`: On $Q=4, \mathrm{SNR}=20\text{ dB}$ (`300` paired scenarios, identical estimator), at $\mathbf{C}=0$ both `Inter_MC` and `EqualMom_TM_MC` have lower extrapolation NMSE than `Blocks_MC` (`paired 95% CI < 0`, by `>= 2.0 dB`), whereas at $\mathbf{C}\neq 0$ (`-14.9 dB` NN + `-25 dB` 2nd-NN + pattern error) both `Inter_MC` and `EqualMom_TM_MC` have **worse** NMSE than `Blocks_MC` (`paired 95% CI > 0`, losing by `>= 3.0 dB`, total reversal swing `>= 6.0 dB`).
2. `quant_q4_extrapolation_and_blind_rate`: At $Q=4, \mathrm{SNR}=20\text{ dB}$ under $\mathbf{C}\neq 0$ + perturbations, `Balanced_DB_MC` beats `Inter_Unc`, `Inter_MC`, `EqualMom_TM_MC`, and `Blocks_MC` by **`>= 4.0 dB` full-mode NMSE** AND improves **blind-selected** 8-stream uplink sum-rate over `Inter_Unc` and `Inter_MC` by **`>= +6.0 bps/Hz` (`>= 35%` relative gain)**.
3. `quant_q8_critical_beats_random`: At $Q=8, N_r=64, \mathrm{SNR}=20\text{ dB}$ under general mirror-symmetric pair coupling + perturbations, `Balanced_DB_MC` (`min_pos_var >= 250`, `64/64` covered, median $\sigma_{\min}(\mathbf{P}_\perp\boldsymbol{\Phi}) > 0.05$) beats `BalancedRand_MC` by **`>= 1.5 dB` full-mode NMSE** (`paired 95% CI lower bound > +1.0 dB`). *(Also log exact contrast against `RecipLowDim_Balanced` on both general pair coupling and rank-1 impedance coupling to state the exact physical scope boundary!)*

---

## 3. `I-20261123-g04` (`core` — Impulsive-Noise Cross-Waveform Pilot/Data Localization Trilemma & Mask-Projected Receiver)

### A. Competing Hypotheses (`research-checkpoint` §1.1)
- **$H_{\mathrm{dual}}$ (Dual pilot-peak + Zak data-row localization trilemma favors `EP-AFDM + MaskProj`)**: Without impulses (`clean`), `EP-AFDM`, impulse-pilot `EP-OTFS`, and `Sanoopkumar–Farhang` low-peak `PCP-OTFS` achieve virtually identical coded FER (`within +-3 pp`). Under impulsive noise (`BG` and `Middleton Class-A`), impulse-pilot `EP-OTFS` fails due to `+18.1 dB` pilot self-blanking, while `Sanoopkumar–Farhang PCP-OTFS` rescues OTFS channel estimation yet STILL suffers higher coded FER than `EP-AFDM + MaskProj` because Zak-OTFS confines each delay row of data to $K$ periodic time instants (causing localized multi-erasure SINR collapses across delay rows), whereas AFDM spreads every pilot AND data symbol with constant $1/\sqrt{N}$ modulus across all $N$ time samples!
- **$H_{\mathrm{sf\_ties}}$ (`Sanoopkumar–Farhang PCP-OTFS` closes the cross-waveform gap)**: Once OTFS replaces its impulse pilot with `PCP-OTFS` + identical mask-projected CE & retained-sample LMMSE, OTFS matches `EP-AFDM + MaskProj` within `< 0.8 dB` (`< 5 pp` FER), refuting the cross-waveform selection advantage while leaving only a diagnostic against impulse-pilot OTFS.
- **$H_{\mathrm{zhidkov}}$ (Standard blanking without mask-projected operators suffices)**: `EP-AFDM + NaiveZhidkov` (with dev-tuned `MAD` blanking threshold) is within `< 0.8 dB` of `EP-AFDM + MaskProj`.

### B. Design Validity & Anti-Confound Controls (`Sol` Step 6 Lines 89–91)
- **Exact equal net payload & CP energy**: Every waveform (`Comb-OFDM`, `Spread-OTFS`, `EP-OTFS-Impulse`, `EP-OTFS-SF-PCP`, `EP-AFDM`) transmits **exact `k = 512` information bits** per frame (`Spread-OTFS` uses punctured/shortened `k = 512` info bits mapped to `512` QPSK symbols; all `EP/PCP/Comb` waveforms use the identical `(768, 512)` LDPC code over `384` QPSK data symbols + `128` pilot/guard overhead bins) over identical `N + L_cp = 512 + 8 = 520` samples (`2Nc1 = 8` even $\implies$ identical cyclic prefix and bit-exact physical time-domain channel $\mathbf{H}_{\mathrm{td}}$ across all waveforms!).
- **Strict blind `MAD` calibration on dev set ONLY (`seeds 81000..81059`)**: Background scale is estimated blindly per frame via complex median absolute deviation $\hat{\sigma}_{\mathrm{bg}} = \mathrm{median}(|r|) / \sqrt{\ln 2}$. For EVERY arm and EVERY noise model independently, `(pilot_fraction rho_p, threshold_mult c_T, reg_extra)` are grid-searched on the `60` dev frames ONLY and frozen before touching `82000..82399`.
- **Repaired `[all-I, all-Q]` soft bit ordering (`e1_ldpc.py:209`)** applied identically to 0-iter and 1-iter arms across all waveforms.
- **Diagnostic logging**: Log per-arm `pilot_blanked_energy_frac`, `chan_nmse_db`, `post_lmmse_var_std` (symbol-wise SINR dispersion!), `signed_net_gmi`, `fer`, and `wall_ms_per_frame`.
- **Prior probabilities**: $P(H_{\mathrm{dual}}\text{ passes all gates on }64\times 8) = 0.68$, $P(H_{\mathrm{sf\_ties}}\text{ on }32\times 16) = 0.35$.

### C. Pre-Registered Boolean Gates (`verdicts['g04']`)
1. `ctrl_clean_parity_and_reversal`: On `clean` (`p_imp = 0`, `400` unseen frames at `11.5 dB`), `|FER(EP_AFDM_MaskProj) - FER(EP_OTFS_Imp_MaskProj)| <= 0.05` (`within 5 pp`, or OTFS slightly ahead), whereas under `bg_64x8` at `11.5 dB` `EP_AFDM_MaskProj` beats BOTH `EP_OTFS_Imp_MaskProj` AND **`EP_OTFS_SF_PCP_MaskProj` (`Sanoopkumar–Farhang`)** with paired 95% CI upper bound of FER difference `< 0`.
2. `dir_beats_all_across_bg_and_mca`: Under BOTH `bg_64x8` (`Bernoulli-Gaussian`) AND `mca_64x8` (`Middleton Class-A`) at `11.5 dB` and `13.0 dB`, `EP_AFDM_MaskProj` (both `0Iter` and `1Iter`) achieves strictly lower `FER` than `Comb_OFDM_MaskProj`, `Spread_OTFS_MaskProj`, `EP_OTFS_Imp_MaskProj`, `EP_OTFS_SF_PCP_MaskProj`, AND `EP_AFDM_NaiveZhidkov` (`paired 95% CI < 0` against every competitor at `11.5 dB` or `13.0 dB`).
3. `quant_snr_and_fer_margin`: On `bg_64x8`, `EP_AFDM_MaskProj_1Iter` (and `0Iter`) reduces `FER` at `11.5 dB` by **`>= 0.15` (`15 pp`)** relative to BOTH `EP_OTFS_Imp_MaskProj` AND `EP_OTFS_SF_PCP_MaskProj` AND `EP_AFDM_NaiveZhidkov`, AND achieves **`>= 1.2 dB` SNR advantage** at the `10%` FER crossing across `{10.0, 11.5, 13.0, 14.5} dB`. *(On `bg_32x16`, evaluate the exact same paired contrast: if `EP_AFDM_MaskProj` also beats `EP_OTFS_SF_PCP_MaskProj` with `paired 95% CI < 0`, claim holds across both aspect ratios; if gap shrinks `< 5 pp` at $32\times 16$, explicitly state $M/K \ge 4$ as the verified effective regime per card pre-registration!)*

---

## Implementation Notes (Appended for Code-to-Protocol Audit Transparency; Frozen Gates Above Unmodified)

- **`g01` (`g_r5_g01_collinear_unfold.py`)**: Executed on `deinlab` CPU (`workers=32`, `epochs_r0=16, epochs_r1=14, lr=0.04` with parallel Round-1 dataset packing) to fit strictly inside the `FUNNEL.md` `<= 15 min` lightweight unfolding cap while preserving identical parameter count (`76 <= 80`) and disjoint `train/dev/test` frame ranges.
- **`g02` (`g_r5_g02_reconfig_debruijn.py`)**: `nmse_db` evaluates extrapolation across all $Q$ homogeneous mode slices (`H_hom_true`), while `sum_rate_bps_hz` evaluates 8-stream uplink LMMSE sum-rate under blind per-element heterogeneous mode selection (`Hm_sel_true`) chosen from each arm's own estimated channel.
- **`g04` (`g_r5_g04_impulsive_erasure.py`)**: `mca` (`Middleton Class-A`) uses $A=0.05$ with fixed per-arrival variance `10.0` (total impulsive variance $\sigma_I^2 = 0.50$, so thermal-to-impulsive ratio $\Gamma = \sigma^2/\sigma_I^2 \in [0.071, 0.142]$ across `11.5–14.5 dB`, centered at $\sim 0.10$ at `13.0 dB`); on `32x16`, $L_{\max}=3$ (`~11%` of subblock length $M_{\mathrm{ot}}$) preserves spill-free `128`-bin guard parity (`8` guard rows $= 2L_{\max}+2$).
