# Pre-Registration — Local Round 6 Priority Step-7 Revisions (`I-20261123-g04` & `I-20261123-g02`)

- **Date**: `2026-11-23`
- **Runner**: `g` (`gemini-4-carbon`)
- **Authority**: Step-8 cross-model review `ideas/reviews/astra-gate-r5-g02g04-20261123.md` + `round-local.md` §7 two-tier pre-registration (`PASS_PRIMARY` ≤ 2 clauses + `SCOPE_READOUTS`).
- **Scripts**:
  - `ideas/l2/g_r6_rev_g04_impulsive_blind.py` → `ideas/l2/out_g_r6_rev/summary_g04_rev.json` & `frames_g04_rev.jsonl`
  - `ideas/l2/g_r6_rev_g02_reconfig_ctrl.py` → `ideas/l2/out_g_r6_rev/summary_g02_rev.json` & `frames_g02_rev.jsonl`

---

## 1. `I-20261123-g04` — Impulsive-Noise Cross-Waveform Erasure Projection & Data-Domain Attribution

### Experimental Design & Fairness Invariants
1. **Seeds (strictly disjoint from Round 5 and from each other)**:
   - Smoke check: seed `82800`.
   - Unified mixed blind development pool (`120` frames at `64x8, SNR = 11.5 dB`): `82900..82939` (`40` clean AWGN), `82940..82979` (`40` Bernoulli-Gaussian, `p_imp = 0.045, sigma_I^2_cond = 12.0`), `82980..83019` (`40` Middleton Class-A, `A = 0.05`, total `sigma_I^2 = 10.0 * sigma2 / 1.0`? Fixed physical impulsive environment `A = 0.05`, per-arrival variance `10.0`, mean `sigma_I^2 = 0.50`, so at `11.5 dB` `sigma2 = 0.07079`, true `Gamma = sigma2 / sigma_I^2 = 0.1416`).
   - Unseen paired test slice (`400` frames at `64x8, SNR = 11.5 dB`): seeds `83100..83499`, sharing bit-identical channel `H_td`, thermal noise `w_th`, impulsive arrivals `v_imp`, and `512` information bits across all arms.
2. **Zero Side-Information Blind Practical Chain**:
   - Every practical arm calibrates **one single unified hyperparameter tuple** `(rp, c_T, reg_mult)` over the pooled 120-frame mixed development set (`clean + bg + mca` combined), without receiving any `noise_type` label at dev selection or test time.
   - The practical receiver function receives **only** the 520-sample received baseband vector `r_cp` (`sigma2` and `noise_type` are absent from the receiver call signature). Background scale is estimated via `sig_env = median(|r|) / sqrt(ln 2)` and guard residual `sig2_guard`, with purely blind LMMSE regularization `min(max(sig2_guard, 1e-4 * sig_env^2), 0.50) + reg_mult * sig_env^2` (and `max(sig2_guard - Ed, 1e-4 * sig_env^2) + reg_mult * sig_env^2` for guard-free `Spread_OTFS_MaskProj`).
3. **Exact 520-Sample CP-Included Expected Energy Normalization**:
   - With `N = 512, L_cp = 8` (`N_tot = 520`), both the unit pilot waveform and the zero-mean data modulation columns (with fixed deterministic ±1 scrambling on `Spread_OTFS` so all `512` symbols are strictly zero-mean uncorrelated with the pilot) are normalized by their deterministic 520-sample CP-included norms (`P_cp = [I_N[-8:]; I_N]`), so `E[||s_cp||_2^2] == 520.0` identically to `< 1e-12` across `EP_AFDM`, `EP_OTFS_SF_PCP`, `EP_OTFS_Imp`, `Comb_OFDM`, and `Spread_OTFS`, propagated through true linear multipath convolution before CP removal (no data-dependent per-frame AGC).
4. **True-Channel Same-Mask Data Attribution Arms (paired on the same `400` frames `83100..83499`)**:
   - Gift exact `H_td`, exact `sigma2`, and exact pilot removal (`r_data = (H_lin * s_data_cp)[L_cp:] + w_th`, identical `384` QPSK data symbols carrying `512` LDPC bits and identical deterministic expected `(1 - 0.14) * 520 = 447.2` CP-included data energy) to `AFDM` and `OTFS`.
   - Evaluate both waveforms on the clean data-plus-thermal-noise signal under (a) **unblanked** (`keep_mask = 1`) and (b) **the identical pre-determined impulse-arrival erasure mask** (`keep_mask = 1_{v_imp == 0}`), plus a secondary readout applying a waveform-symmetric blind envelope mask to the same clean data signal (isolating pure erasure geometry without residual unblanked impulses). Define per-frame excess erasure FER `dFER_erase(W) = FER(W, true H, mask) - FER(W, true H, unblanked)`.

### Two-Tier Verdicts for `I-20261123-g04`
- **`PASS_PRIMARY` (2 clauses; both required for `PASS`; exact integer frame-error threshold `20 / 400 == 5.0 pp`)**:
  1. **`G04_P1` (Practical blind CP-normalized unknown-channel advantage)**: On the `400` unseen frames (`83100..83499`, `64x8, 11.5 dB`), under a single mixed-dev blind receiver rule with exact 520-sample CP expected energy parity, `EP_AFDM_MaskProj_1Iter` beats `EP_OTFS_SF_PCP_MaskProj`, `EP_OTFS_Imp_MaskProj`, `Comb_OFDM_MaskProj`, `Spread_OTFS_MaskProj`, `EP_AFDM_NaiveZhidkov`, and `EP_AFDM_Unblanked` on **both** `bg` and `mca`, with `err(EP_OTFS_SF_PCP_MaskProj) - err(EP_AFDM_MaskProj_1Iter) >= 20` (`5.0 pp` on `n=400`) and paired 95% bootstrap CI strictly `> 0` on both `bg` and `mca`, while on `clean` AWGN `|err(AFDM_1Iter) - err(OTFS_Imp)| <= 20` (`5.0 pp`).
  2. **`G04_P2` (True-channel identical-mask data-erasure attribution)**: On the exact same `400` frames (`bg` and `mca`), under true `H_td` and identical impulse-position erasure mask, the paired excess erasure error difference `sum[dFER_erase(OTFS) - dFER_erase(AFDM)] >= 20` (`>= 5.0 pp` on `n=400`) and paired 95% bootstrap CI strictly `> 0` on **both** `bg` and `mca`.
- **`SCOPE_READOUTS` (claim-scoping diagnostics, non-gating)**:
  - `G04_S1`: Zero-iteration `EP_AFDM_MaskProj_0Iter` vs `EP_OTFS_SF_PCP_MaskProj` paired FER difference on `bg` and `mca` (isolates non-iterative gain without 1-iter data feedback).
  - `G04_S2`: True-channel attribution under a shared blind amplitude-threshold mask (confirming attribution does not depend on oracle vs blind mask generation).
  - *Scope commitment*: Claims against `PCP-OTFS` are explicitly scoped to the tested `PCP` pilot + mask-projected OMP/LMMSE chain (not Sanoopkumar & Farhang's untested two-stage unmasked estimator).

### Concrete Predictions (`g04`)
- Practical blind `FER(PCP_OTFS) - FER(AFDM_1Iter)` at `11.5 dB`: `+11% to +19%` on `bg` and `+14% to +22%` on `mca` (confidence `0.85`).
- True-channel identical-mask excess FER `[dFER_erase(OTFS) - dFER_erase(AFDM)]`: `+7% to +15%` on both `bg` and `mca` (confidence `0.80`).

---

## 2. `I-20261123-g02` — Single-Factor Mutual-Coupling Reversal & Pairwise-Swap Coverage Comparison

### Experimental Design & Fairness Invariants
1. **Debiasing Sign Invariant**: Keep `g_r5_g02_reconfig_debruijn.py` lines 311–317 (`P_diag_nb = -np.einsum(...)`, `EIV_rhs += -sigma2 * np.einsum(...)`, `rhs_deb = -(P_Phi.conj().T @ P_y) - EIV_rhs`) **100% unchanged**, and assert in `smoke` that the 24-direction exact EIV bias norm drops from `~0.047` to `< 1e-15`.
2. **Seeds (strictly disjoint from Round 5)**:
   - Smoke check: `85800`.
   - Dev calibration (`40` scenarios): `85900..85939` (`reg_c in [0.10, 0.20, 0.35, 0.60, 1.00]` calibrated **independently for every layout arm** on both `Q=4` and `Q=8` so `SwapHC` and baselines get the exact same dev budget as `Balanced_DB`).
   - Unseen paired test slices (`300` scenarios each at `SNR = 20.0 dB`): `86000..86299`.
3. **Slice 1 (`Q=4, Nr=64, Nt=8, SNR=20 dB`): Strict Single-Factor Nearest-Neighbor Coupling Switch**:
   - Pre-generate `(a_rand, u_true, v_true, c_true, noise, elem_pert)` from `rng_sc = default_rng(sc_seed)` in fixed order, and draw `Cp_true` from an independent `rng_mc = default_rng(sc_seed + 10_000_000)` (`C2p = None` in the primary single-factor switch; `C2p != 0` reported in `SCOPE_READOUTS`). Assert bit-identical `(u_true, v_true, c_true, noise, elem_pert, a_rand)` between `Q4_C0` and `Q4_MC1NN`.
4. **Slice 2 (`Q=8, Nr=64, Nt=8, SNR=20 dB`): Pre-Locked Pairwise-Swap Hill-Climbing Baselines (`SwapHC150_MC`, `SwapHC4000_MC`, `SwapHC128k_MC`)**:
   - Before touching any channel data, construct from equal-count random layout (seed `612`, matching Astra's audit seed, plus verify across 5 independent layout seeds in `SCOPE_READOUTS`) three zero-channel-access distinct-state pairwise-swap layouts lexicographically maximizing `(mirror_param_coverage, min_k Var(pos_k))`:
     - `SwapHC150`: `150` distinct-state swap evaluations (`64/64` mirror coverage, `min_var >= 250`).
     - `SwapHC4000`: `4,000` distinct-state swap evaluations.
     - `SwapHC128k`: `128,000` distinct-state swap evaluations (matching `Balanced_DB`'s exact `4,000 * 32 = 128,000` candidate shift evaluations).

### Two-Tier Verdicts for `I-20261123-g02`
- **`PASS_PRIMARY` (2 clauses; both required for `PASS`)**:
  1. **`G02_P1` (`Q=4` single-factor nearest-neighbor MC ranking reversal)**: Toggling **only** nearest-neighbor coupling (`Cp_true = 0` vs `Cp_true != 0` on bit-identical `u, v, c, noise, elem_pert`) flips **both** `Inter_MC` and `EqualMom_TM_MC` relative to `Blocks_MC` from `>= +2.0 dB` NMSE lead (`95% CI > 0`) at `C=0` to `<= -3.0 dB` NMSE deficit (`95% CI < 0`) at `C != 0` (total swing `>= 6.0 dB`), while full-coverage calibration (`Balanced_DB_MC`) beats `Inter_Unc` and `Inter_MC` by `>= +4.0 dB` NMSE and `>= +6.0 bps/Hz` blind sum-rate.
  2. **`G02_P2` (`Q=8` critical neighbor-coverage necessity over random layout)**: At `Q=8, Nr=64, SNR=20 dB` (mirror-shared nearest-neighbor coupling + unmodeled 2nd-neighbor + `0.3 dB / 3 deg` element perturbations), full mirror-coverage layouts (`Balanced_DB_MC`, `SwapHC4000_MC`, and `SwapHC128k_MC`) beat equal-count `BalancedRand_MC` by `>= +1.5 dB` point NMSE and `> +1.0 dB` paired 95% CI lower bound, with positive blind sum-rate gain (`95% CI > 0`).
- **`SCOPE_READOUTS` (automatic claim-boundary routing, non-gating)**:
  - **`G02_S1` (`Balanced_DB_MC` vs `SwapHC128k_MC`, `SwapHC4000_MC`, and `SwapHC150_MC` at `Q=8, 20 dB`)**:
    - *Pre-registered automatic claim rule*: Conditional on `PASS_PRIMARY == True` (otherwise `FAIL_PRIMARY`), `Balanced_DB_MC` retains a sequence-specific advantage claim **if and only if** it beats `SwapHC128k_MC` (and `SwapHC4000_MC`) by `>= +1.5 dB` point NMSE and `> +1.0 dB` paired 95% CI lower bound under mirror-shared coupling; **if `< +1.5 dB` (tie/near-tie), we immediately revise `g02`'s title and thesis to "neighbor-pair mirror coverage necessity + EIV-debiased implicit resolvent calibration (achievable by zero-cost pairwise-swap hill-climbing or De Bruijn cycles)" and drop sequence exclusivity**.
  - **`G02_S2` (Non-mirror-symmetric directional coupling `Cm != pi(Cp)` at `Q=8, Nr=128` or `Q=4, Nr=64`, plus `Q=4` `BalancedRand_MC` vs `SwapHC` vs `Balanced_DB_MC`, plus true rank-1 `z_mut * outer(gam, gam)` reciprocal physics)**: Tests whether breaking mirror symmetry (where `SwapHC` optimizing mirror-coverage only covers `~45/64` directed edges while `De Bruijn` covers `63/64`–`64/64` directed edges!) separates directed Eulerian coverage from undirected/mirror swap coverage, and records `Q=4` `MC1NN + C2p` secondary readout.

### Concrete Predictions (`g02`)
- `G02_P1` (`Q=4` single-factor swing): `Inter_MC` vs `Blocks_MC` swings by `8.5 to 10.5 dB` (`+2.2 dB` at `C=0` to `-7.2 dB` at `C!=0`) (confidence `0.90`).
- `G02_P2` & `G02_S1` (`Q=8` mirror-shared): Both `Balanced_DB_MC` and `SwapHC4000_MC` beat `BalancedRand_MC` by `+1.7 to +2.3 dB`, while `Balanced_DB_MC` vs `SwapHC4000_MC` will be within `+-0.5 dB` under mirror-shared coupling — triggering the clean pre-registered narrowing to neighbor-pair coverage necessity (confidence `0.80`).
