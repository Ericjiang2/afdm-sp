# Step-8 Diagnostic Pre-Registration — `h_r12_h02_p4` (`I-20261125-h02` Astra `REVISE` Point `P_4` 配对检验)

- **Card ID**: [`I-20261125-h02`](../cards/I-20261125-h02.md) (`跨块信道老化下路径解耦MIMO-AFDM通感预编码` · `[高要求] [轨B-ISAC]`)
- **Review Mandate**: Step-8 `gpt-6.2-astra` two-beat `kill-argument` review [`r12-astra-h02-killarg-20261126.md`](../reviews/r12-astra-h02-killarg-20261126.md) (`STEP8: REVISE`, Points `P_1–P_4`) and Eric 2026-11-26 Round-12 closure mandate.
- **Role & Preservation of Prior Frozen Verdicts**: Single-purpose **Step-8 mechanism diagnostic** (`step8_p4_paired_mechanism_diagnostic`). Both prior frozen L2 verdicts remain **100% untouched and unedited**:
  1. Round 11 initial L2: [`summary_h_r11_h02.json`](out_h_r11_h02/summary_h_r11_h02.json) (`verdicts.PASS_PRIMARY = false`);
  2. Round 12 modified-evaluation unseen-seed L2: [`summary_h_r12_h02_conf.json`](out_h_r12_h02/summary_h_r12_h02_conf.json) (`verdicts.PASS_PRIMARY = true`).
- **Script & Output**: [`ideas/l2/h_l2_r12_h02_p4.py`](h_l2_r12_h02_p4.py) (directly importing `h_l2_r12_h02_conf` per `CLAUDE.md` D18 with zero duplicated channel/precoder/receiver functions) $\to$ `ideas/l2/out_h_r12_h02_p4/diag_h_r12_h02_p4.json` (remote `/data/guoyikun/tmp/funnel_h_r12/diag_h_r12_h02_p4.json`, serialized with `allow_nan=False`, `fsync`ed to same-directory temp file, and atomically published via `os.replace`; `_validate_out_path()` explicitly rejects both `summary_h_r11_h02.json` and `summary_h_r12_h02_conf.json` in all modes and rejects `diag_h_r12_h02_p4.json` under `--smoke`).
- **Execution Environment**: `deinlab`, `/home/guoyikun/.conda/envs/AFDM/bin/python`, `OMP_NUM_THREADS=1`, `multiprocessing.Pool(8)` (`8` CPU workers `<= 8` core cap), gated on `gpt-6.2-sol` (`high`) pre-run check (`GO` or `GO_WITH_NONBLOCKING`).
- **Strict Seed Isolation (Mechanically Enforced by `verify_seed_disjointness()` in `G1_PARITY_AND_INVARIANTS`)**:
  - All historical Round-11/12 probe, dev, smoke, bootstrap, and formal seeds (`[0, 100000)`, `260705`, `[110000, 163000)`, `[200000, 991000)`, `[1000900, 1991000)`, `[2150000, 2161000)`), plus all `P_4` dev calibration seeds (`[3100000, 4900000)`), lie strictly below `5,000,000` (plus import constant `20261125` for `P_of_hc`).
  - Formal `P_4` locks **`7,599` pairwise-disjoint integer seeds** strictly inside `[5100000, 6400000)`:
    - `cal`: `5100000 .. 5101598` (`N_cal = 1599`, `rng_s1`: `6100000 .. 6101598`);
    - `val`: `5200000 .. 5201599` (`N_val = 1600`, `rng_s1`: `6200000 .. 6201599`);
    - `pos`: `5300000 .. 5300599` (`N_pos = 600`, `rng_s1`: `6300000 .. 6300599`);
    - Synchronized dual-bootstrap RNG seed: `5900001`.
  - Parity scene `7900000` (`8900000`) and `--smoke` seeds (`7100000..8300019`, `7950001`) lie in `[7100000, 8900001)`, strictly disjoint from `[5100000, 6400000)` and `[0, 5000000) ∪ {20261125}`.

---

## 1. Research Checkpoint (§1): Paired Factorial Arms, Competing Hypotheses & Single-Factor Validity

### 1.1 Five Paired Radar Arms on Identical `Z=1` (`28 dB, Nt=12, K=3, nu_max=0.85, sig_nu_sub=0.025, sig_th_sub=0.8`) Scenes
- **Pre-Specified Sector Surveillance Pointing vs Independent Echo Target Truth**: Following `Liu & Schober 2026` (`arXiv:2607.05119` Sec. IV-A & Sec. V, $\theta_t = 40^\circ$), the monostatic ISAC BS operates in **pre-cued azimuth sector surveillance mode** (`PRE_SPECIFIED_SEARCH_THETA_DEG = 40.0` deg, known a priori to Stage-1 transmit radar beam synthesis and supplied identically as an explicit `theta_search_deg` input to 2D range–Doppler scoring across target-free `cal`, target-free `val`, and target-present `pos`; azimuth DoA is not blindly estimated). Conversely, echo target angle `theta_tar_true_deg` (`None` on target-free `cal` and `val`; `POS_TRUE_TARGET_THETA_DEG = 40.0` deg for an in-sector target on `pos`) is an **independent input** passed **solely** into `_build_echo` when `has_tar == True` and never read by `score_pure_blue_rd_maxsp`.
- All 5 radar arms share the **exact same** independent target-free `cal` (`N_cal = 1599`), target-free `val` (`N_val = 1600`), and target-present `pos` (`N_pos = 600`, weak target `-3 dB` at `ell_tar = 2, nu_tar = 0.145, theta_tar_true_deg = 40.0` against 4 clutter scatterers at `+32 dB`, `|nu_c| <= 0.03`) scenes. Both `S_tot_cpi` and `Y_rad_cpi` are locked read-only (`arr.flags.writeable = False`) before scoring so `Q=2` and `Q=16` scorers receive **provably bit-identical** transmitted samples and echoes:

1. **`Prop_Q16`**: `Prop_BeamMatchedDualISAC_AFDM` (`S_tot_prop`, `Y_rad_prop`), scored via `score_pure_blue_rd_maxsp(..., sub_cpi_len = 16, max_sp = 6, theta_search_deg = PRE_SPECIFIED_SEARCH_THETA_DEG)` (verified bit-exact `0.0` tuple diff against `h_l2_r12_h02_conf.unified_pure_blue_rd_score` in `G1`). Because `Prop` transmits on `K = 3` user beams + `1` radar beam, `rank(S_tot_prop) <= 4 <= 6` on every scene (`prop_sp12_identical == True` verified across all `cal/val/pos` scenes, and bit-exact `0.0` diff vs `max_sp = 12` verified in `G1`).
2. **`Prop_SameWave_Short8xQ2`**: Bit-identical `(Y_rad_prop, S_tot_prop)` of `Prop_Q16`, scored with `sub_cpi_len = 2, max_sp = 6, theta_search_deg = PRE_SPECIFIED_SEARCH_THETA_DEG` (bit-exact `0.0` diff vs `unified_pure_blue_rd_score` verified in `G1`).
3. **`ExtrapShort8xQ2_ScoredQ2`**: `ExtrapBlockRZF_Short8xQ2_AFDM` (Stage-1 uplink re-sounding every 2 blocks at `sound_block_idx = 2*isub - 1`, per-block RZF precoding `S_tot_short`, and radar echoes `Y_rad_short`), scored with `sub_cpi_len = 2, max_sp = 6, theta_search_deg = PRE_SPECIFIED_SEARCH_THETA_DEG` (bit-exact `0.0` diff vs `h_l2_r12_h02_conf.run_single_trial` verified in `G1`).
4. **`ExtrapShort8xQ2_ScoredQ16` (Primary Literal `P_4` Arm)**: **Bit-for-bit identical** `(Y_rad_short, S_tot_short)` of `ExtrapShort8xQ2_ScoredQ2`, changing **only** `sub_cpi_len = 2 -> 16` (`max_sp = 6`, `theta_search_deg = PRE_SPECIFIED_SEARCH_THETA_DEG`; bit-exact `0.0` diff vs `h_l2_r12_h02_conf.unified_pure_blue_rd_score(..., 16)` verified in `G1`).
5. **`ExtrapShort8xQ2_ScoredQ16_Sp12` (Single-Constant Uncapped-Spatial-Rank Companion Arm)**: **Bit-for-bit identical** `(Y_rad_short, S_tot_short)`, `sub_cpi_len = 16`, and `theta_search_deg = PRE_SPECIFIED_SEARCH_THETA_DEG`, changing **only** the spatial singular-mode cap `6 -> Nt_v = 12` (`n_sp = min(Nt_v, int(np.sum(sv_s > 0.01 * sv_s[0])))`, keeping `0.01 * sv_s[0]` and `1e-6` `B_clut` SVD untouched). Comparing Arm 5 vs Arm 4 (`sp_trunc_effect_on_rival_Sp12_minus_MaxSp6`) directly tests whether receiver `min(6, ...)` spatial truncation causes any localization loss on the 12-antenna RZF waveform, and comparing `Prop_Q16` (`=== Prop_Q16_Sp12`) vs Arm 5 gives a symmetric uncapped-rank `Q=16` comparison.

On `pos` scenes, pure UE-local blind communication `SER` for `Prop_BeamMatchedDualISAC_AFDM` and `ExtrapBlockRZF_Short8xQ2_AFDM` is also recorded via `h_l2_r12_h02_conf` functions.

### 1.2 Competing Hypotheses, Design Validity & Premortem
- **Competing Hypotheses**:
  - `H_conflict` (Original card framing): Re-sounding and updating RZF precoding every 2 blocks degrades 16-block coherent radar target localization by `>= 0.55` even when the monostatic receiver jointly processes all 16 blocks using its known `S_tot_short` (`Delta_P4_literal >= 0.55` and `Delta_P4_sp12 >= 0.55`).
  - `H_catchup_sp12` (Phase-continuous model + receiver `max_sp=6` truncation): Because target and clutter slow-time phases advance continuously across refresh boundaries (`np.arange(Q) * Tsym`) and the monostatic radar knows `S_tot_short`, switching `sub_cpi_len: 2 -> 16` immediately refutes the `0.55` gap (`Delta_P4_literal < 0.55`, `proj_keep_db ~ -0.8 to -1.0 dB`); any `~8–12 pp` residual gap under `max_sp = 6` comes solely from truncating modes `7..10` of the 12-antenna RZF waveform, vanishing to `<= +10 pp` (`~0.00 pp`, `LocBlindPd >= 90%`) under `max_sp = 12`.
  - `H_partial_waveform_gap`: Even after lifting `max_sp` to `12`, 2-block RZF beam switching across sub-CPIs still leaves an intermediate localization gap (`> +10 pp` though `< 0.55`).
- **Four Validity Checks**:
  - *(a) Single-factor contrasts*: `Arm 3 -> Arm 4` changes only `sub_cpi_len: 2 -> 16`; `Arm 4 -> Arm 5` changes only `max_sp: 6 -> 12` (verified no-op on `Prop_Q16`); `Arm 1 -> Arm 2` changes only `sub_cpi_len: 16 -> 2` on `Prop`.
  - *(b) Leverage & equivalence margins*: Superiority bar `tau_sup = 0.55` (`25%` half-width cap `0.1375`, applied to `Delta_P4_literal`, `Delta_P4_sp12`, and both `Q=2` anchors); symmetric uncapped catch-up equivalence bar `tau_eq = 0.10` (`Delta_P4_sp12 <= +0.10` and `LocBlindPd(Arm 5) >= 0.90`, `25%` half-width cap `0.0250`, applied strictly to `Arm 5` / `Delta_P4_sp12`).
  - *(c) Statistical unit*: Scene `seed_i` (`cal`, `val`, `pos` mutually disjoint; all 5 arms share identical scenes and synchronized `(cal, pos)` bootstrap index draws).
  - *(d) Exact metric definitions*: `LocBlindPd` = strict alarm `blind_score > tb` first, then `|j_pk - jw_true| <= 2` and `l_pk == ell_tar`; `proj_keep_db` = `10 * log10(sum(tot_proj_e) / sum(tot_raw_e))` (matching `h_l2_r12_h02_conf.py:1108`) plus per-scene paired 95% CI.
- **Premortem**: Without Arm 5 (`max_sp = 12`), a `~10 pp` gap on Arm 4 (`max_sp = 6`) could be misread as partial slow-time waveform loss when it is actually `min(6, ...)` receiver truncation on a rank-12 RZF waveform; Arm 5 rules this out cleanly.
  - **Pre-Run Subjective Probability Ledger** (exhaustive over the mutually exclusive 9-outcome `DIAGNOSTIC_OUTCOME` partition, sum `= 1.000`):
  - `P(INVALID_DIAGNOSTIC_DO_NOT_USE) = 0.040`
  - `P(INCONCLUSIVE_PRECISION_INSUFFICIENT) = 0.015`
  - `P(SHORT_WINDOW_ANCHOR_BELOW_055_RETRACT_CONFLICT) = 0.002`
  - `P(LITERAL_REFUTES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT) = 0.900`
  - `P(LITERAL_STRADDLES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT) = 0.010`
  - `P(LITERAL_GE_055_UNDER_MAXSP6_ONLY_SP12_CATCHES_UP_RETRACT_CONFLICT) = 0.003`
  - `P(PROP_STILL_BEATS_BY_055_KEEP_RADAR_ADVANTAGE) = 0.005`
  - `P(LITERAL_REFUTES_055_SP12_NOT_CAUGHT_UP_REPORT_EXACT_DIFF) = 0.020`
  - `P(UNPROVEN_055_SP12_NOT_CAUGHT_UP_REPORT_EXACT_DIFF) = 0.005`

---

## 2. Independent Dev-Set Calibration & Red Line 5 Full-Envelope Precision Table

Independent dev calibration was executed on `deinlab` (`dev_h02_p4_cal.py` on `3100000..3300079`, `dev_h02_p4_size_check.py` at **full formal scale `N_cal = 1599, N_pos = 600`** on `3400000..3600599`, and `dev_h02_p4_sp_check.py` on `3700000..3800119`; all strictly `< 5,000,000` and disjoint from formal `[5100000, 6400000)`):
- Dev `(1599 cal, 600 pos)` direct measurements:
  - `Prop_Q16` (`=== Prop_Q16_Sp12`, exact rank `4`): `LocBlindPd = 100.0% (600/600)`, `proj_keep_db = -0.74 dB`;
  - `ExtrapShort8xQ2_ScoredQ2`: `LocBlindPd = 0.0% (0/600)`, `proj_keep_db = -53.60 dB` (`Prop_SameWave_Short8xQ2`: `0.0%`, `-55.16 dB`);
  - `ExtrapShort8xQ2_ScoredQ16` (`max_sp = 6`): `LocBlindPd = 88.0% (528/600)` (`97.5%` on `3300000..79`, `92.5%` on `3800000..119`), `proj_keep_db = -0.82 dB`; paired `Delta_P4_literal = +0.1200`, 95% outer envelope `[+0.0883, +0.1583]`, **`env_half_width = 0.03833`**;
  - `ExtrapShort8xQ2_ScoredQ16_Sp12` (`max_sp = 12`, `0.01 * sv_s[0]` unchanged): `LocBlindPd = 100.0% (600/600)` (`120/120` on `3800000..119`, `min_pos = 25.11` vs `thr = 7.22`), `proj_keep_db = -0.95 dB`; paired `Delta_P4_sp12 = 0.0000`, 95% outer envelope `[-0.00636, +0.00636]`, **`env_half_width = 0.00636`**.

Locked formal sample sizes: **`N_cal = 1599, N_val = 1600, N_pos = 600`** (`~9–11 min` wall / `~1.3 core-h` on `deinlab` 8 workers). Every paired difference CI is the **conservative outer envelope** of exact `Newcombe (1998) Method 10` Wilson score CI and synchronized `cal + pos` dual bootstrap (`B = 2000`, recomputing every arm's threshold `tb*` in every replicate), with boundary-conservative half-width `max(mean - env_low, env_high - mean)`. Every single-arm `LocBlindPd` CI is the outer envelope of exact Clopper–Pearson 95% CI and `cal + pos` dual bootstrap (`B = 2000`).

| Gated Quantity | Pre-Registered Threshold / Margin | Red Line 5 `25%` Half-Width Cap | Independent Full-Scale Dev `(1599, 600)` Measured Full-Envelope Half-Width | Meets Red Line 5 |
|---|---|---|---|---|
| `Delta_P4_literal` (`Prop_Q16 - ExtrapShort8xQ2_ScoredQ16`, `max_sp=6`) | Original `P2` bar `tau_sup = 0.55` | **`<= 0.1375`** (`13.75 pp`) | **`0.03833`** (`3.83 pp`, `3.59×` margin) | **Yes** |
| `Delta_P4_sp12` (`Prop_Q16 - ExtrapShort8xQ2_ScoredQ16_Sp12`, `max_sp=12`) | `tau_sup = 0.55` & catch-up `tau_eq = 0.10` | **`<= 0.1375`** & **`<= 0.0250`** (`2.50 pp`) | **`0.00636`** (`0.64 pp`, `3.93×` margin vs `0.0250`) | **Yes** |
| Single-arm `LocBlindPd(ExtrapShort8xQ2_ScoredQ16_Sp12)` | Catch-up lower bar `0.90` (`margin = 0.10`) | **`<= 0.0250`** (`2.50 pp`) | **`0.00613`** (`0.61 pp`, `4.08×` margin) | **Yes** |
| Short-window anchors (`Prop_Q16 - ExtrapShort8xQ2_ScoredQ2` & `Prop_SameWave_Short8xQ2`) | `tau_sup = 0.55` | **`<= 0.1375`** (`13.75 pp`) | **`0.00900`** (`0.90 pp`, `15.3×` margin) | **Yes** |

*(Runtime safeguard: pure half-width gates `REDLINE5_PRECISION_GATES` check ONLY `env_half_width <= 0.1375` / `<= 0.0250` and route breaches to `INCONCLUSIVE_PRECISION_INSUFFICIENT`; short-window `Q=2` anchor effect bounds `ci95_envelope[0] >= 0.55` are checked separately in `SHORT_WINDOW_ANCHOR_EFFECT_GATES` and route to `SHORT_WINDOW_ANCHOR_BELOW_055_RETRACT_CONFLICT` if breached under valid precision.)*

---

## 3. Gates, Exact Equal-`Pfa` Validation & Pre-Registered Card-Update Routing

1. **`G1_PARITY_AND_INVARIANTS` & `G2_NO_TRUTH_IN_CAL_VAL`**:
   - Red Line 1a (`< 1e-13` CPP operator) + Red Line 1b (`Liu & Schober 2026` Fig. 1a monotone WMMSE trajectory);
   - Mechanical `verify_seed_disjointness()` across all `7,599` formal seeds;
   - Bit-exact `0.0` difference on held-out parity scene `7900000` for `SER` and full 5-element radar score tuples `(win_score, blind_score, peak_idx, tot_proj_e, tot_raw_e)` against `h_l2_r12_h02_conf.run_single_trial` and `unified_pure_blue_rd_score`, plus read-only CPI array enforcement (`writeable == False`) and explicit decoupling check between `theta_search_deg` and `theta_tar_true_deg`;
   - Zero target truth (`has_tar_used == False` and `theta_tar_true_used is None`) in all `cal` and `val` scenes, `prop_sp12_identical == True` across every `cal/val/pos` scene, and `RAW_INPUTS_FINITE_OK == True`.
2. **`C1_VALIDITY` (Exact Order-Statistic Threshold + 5-Arm Simultaneous Beta-Binomial FWER + Anti-Inflation Hard Cap)**:
   - At `N_cal = 1599`, `0.95 * (N_cal + 1) = 1520` is an exact integer: `np.quantile(cb, 0.95, method="weibull")` equals the exact 1-indexed order statistic $X_{(1520)}$ (`a = 80, b = 1520`, exact null $\mathbb{E}[P_{\mathrm{fa}}] = 80 / 1600 = 0.050000$).
   - Across all `M = 5` distinct radar arms on `N_val = 1600`, exact two-sided `BetaBinom(1600, 80, 1520)` at `alpha_each = 0.05 / 5` requires **`k_val in [51, 114]`** (`val_pfa_blind in [3.1875%, 7.1250%]`, union FWER upper bound **`4.64% <= 5.0%`**), which simultaneously enforces symmetric anti-inflation `val_pfa_blind <= 0.075` across all 5 radar arms.
3. **`DIAGNOSTIC_VALID = G1_PARITY_AND_INVARIANTS and G2_NO_TRUTH_IN_CAL_VAL and PROP_SP12_IDENTICAL_ALL_SCENES and RAW_INPUTS_FINITE_OK and C1_VALIDITY`**.
4. **Conditioned Spatial-Truncation Attribution (`SP_TRUNCATION_ATTRIBUTION`)**:
   - Let `[trunc_lo, trunc_hi]` be the paired 95% outer-envelope CI of `sp_trunc_effect_on_rival_Sp12_minus_MaxSp6` (`Arm 5 - Arm 4`). Card `## 筛选记录` always reports `sp_trunc_effect_on_rival_Sp12_minus_MaxSp6` directly and attributes a positive `Arm 4` gap to `min(6, ...)` spatial truncation **if and only if** `trunc_lo > 0.0` (`"CONFIRMED_POSITIVE_MAXSP6_TRUNCATION_LOSS"`); if `trunc_lo <= 0.0 <= trunc_hi` (`"NO_CONFIRMED_SP_TRUNCATION_DIFF_STRADDLES_ZERO"`, including identical hit sequences) or `trunc_hi < 0.0` (`"CONFIRMED_NEGATIVE_MAXSP12_EXTRA_CLUTTER_LOSS"`), the card states no positive truncation loss was confirmed.
5. **Mutually Exclusive Pure-Confidence-Bound `DIAGNOSTIC_OUTCOME` & 1-to-1 Card Update Rule** (evaluated strictly in this exact `if / elif` precedence order):
   - **Step 1 — Validity**: **`INVALID_DIAGNOSTIC_DO_NOT_USE`** (`not DIAGNOSTIC_VALID`; `DECISION_READY = false`): do not alter card claims; report blocking failure.
   - **Step 2 — Precision (checked BEFORE all effect branches)**: **`INCONCLUSIVE_PRECISION_INSUFFICIENT`** (`(not hw_055_ok) or (sp12_raw_catches_up and (not hw_sp12_eq10_ok))`; `DECISION_READY = false`): do not alter card claims; report precision failure.
   - **Step 3 — Short-Window Anchor Effect**: **`SHORT_WINDOW_ANCHOR_BELOW_055_RETRACT_CONFLICT`** (`not anchors_q2_ge_055_ok`, reached only when Step 1 & Step 2 passed; `RETRACT_ISAC_CONFLICT_CLAIM = true`): precision passed yet one or both short-window `Q=2` anchor contrasts fell below `0.55` at 95% lower bound — retract the ISAC long-CPI conflict claim and report exact `Q=2` and `Q=16` paired CIs.
   - **Step 4 — Joint `>= 0.55` Superiority**: **`PROP_STILL_BEATS_BY_055_KEEP_RADAR_ADVANTAGE`** (`lit_lo >= 0.55` and `sp12_lo >= 0.55`, `RETRACT_ISAC_CONFLICT_CLAIM = false`): retain within-model `>= 0.55` pre-cued sector radar advantage per Astra `P_4`, explain strictly via waveform + receiver (never claiming phase reset at refresh boundaries), clarify `P_2/P_3`, report exact paired differences and `proj_keep_db`.
   - **Step 5 — Confirmed `SP12` Catch-Up (`sp12_catches_up_confirmed == True`)**: **`LITERAL_REFUTES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT`** (`lit_hi < 0.55`), **`LITERAL_STRADDLES_055_AND_SP12_CATCHES_UP_RETRACT_CONFLICT`** (`lit_lo < 0.55 <= lit_hi`), or **`LITERAL_GE_055_UNDER_MAXSP6_ONLY_SP12_CATCHES_UP_RETRACT_CONFLICT`** (`lit_lo >= 0.55`, indicating the `0.55` bar was reached only under `max_sp = 6` while `max_sp = 12` caught up within `<= +10 pp`; any residual positive gap inside `[0, 0.10]` is reported as-is rather than attributed entirely to truncation) — all with **`RETRACT_ISAC_CONFLICT_CLAIM = true`**:
     Once the receiver's `6`-mode spatial cap is lifted symmetrically (`max_sp = 12`), the 16-block-scored refreshed rival catches up within `<= +10 pp` (`sp12_hi <= 0.10`, `LocBlindPd >= 90%`, `hw_sp12_eq10_ok`). **Retract the "ISAC coherent-CPI vs communication refresh conflict (`通感冲突 / 每两块重测迫使雷达失去跨段相干性`)" claim** across title/summary/`问题（一句话）`/`白话与类比`/`去壳三句`/`价值与代价` in `I-20261125-h02.md`, retaining **only** the communication advantages under 16-block TDD channel aging (`Prop 3.01%` vs equal-overhead blind `OFDM_Comb 17.47%` [`7.11×`], vs 16-block aged `AFDM` precoders `52.7%–71.5%`, and vs 8×-overhead 2-block refreshed `RZF 41.21%`) plus Astra `P_2/P_3` clarifications, while reporting `Delta_P4_literal` (`max_sp = 6`, with its exact three-state `0.55` classification), `Delta_P4_sp12` (`max_sp = 12`), `sp_trunc_effect_on_rival_Sp12_minus_MaxSp6` (conditioned on `SP_TRUNCATION_ATTRIBUTION`), and `proj_keep_db` truthfully in `## 筛选记录` (preserving both prior frozen L2 verdicts intact).
   - **Step 6 — Neither Joint `0.55` Superiority Nor `SP12` Catch-Up**: **`LITERAL_REFUTES_055_SP12_NOT_CAUGHT_UP_REPORT_EXACT_DIFF`** (`lit_hi < 0.55` and `not sp12_raw_catches_up`, `RETRACT_ISAC_CONFLICT_CLAIM = false`) or **`UNPROVEN_055_SP12_NOT_CAUGHT_UP_REPORT_EXACT_DIFF`** (`lit_hi >= 0.55`, `not (lit_lo >= 0.55 and sp12_lo >= 0.55)`, and `not sp12_raw_catches_up`, `RETRACT_ISAC_CONFLICT_CLAIM = false`): here `SP12` did **not** meet `sp12_hi <= 0.10 and rv_sp12_lo >= 0.90` yet joint `>= 0.55` superiority also failed — remove any "0% collapse / phase reset across refresh boundaries" wording and report all exact realized paired differences (`Delta_P4_literal`, `Delta_P4_sp12`, `Arm 5 - Arm 4`), 95% CIs, and `proj_keep_db` truthfully without claiming `>= 0.55` superiority or full `<= 10 pp` catch-up.
