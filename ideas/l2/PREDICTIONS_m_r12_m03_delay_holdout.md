# Pre-Registered Frozen-Receiver 3-Path Delay Holdout Test (Round-14 Stratified & gesvd-Safe Revision) — `I-20261125-m03` (`[放宽TWC] [轨A-纯通信]`)

> **Scope-Only Adjudication Notice (Eric 2026-11-26 & Astra Step-8 REVISE)**:
> This test adjudicates **ONLY the claim scope** of `I-20261125-m03` across held-out 3-path delay geometries `[0, k, 16]` (holding out `k = 7`). It makes **ZERO modification** to the frozen Round-12 receiver ([`l2_m_r12_m03_modtest.py`](l2_m_r12_m03_modtest.py), MD5 `7d174070e3b640583e8ec0e03d948cd1`) and **NEVER alters** either the frozen Round-11 verdict (`PASS_PRIMARY = false`) or the frozen Round-12 Modified-Method New-Seed Test verdict (`PASS_PRIMARY = true`).

- **Card**: `I-20261125-m03` (`--parent I-20261125-m02`) — *全盲 AFDM 双端相噪含噪训练校准与平层界*
- **Astra Trigger**: [`ideas/reviews/r12-astra-m03-killarg-20261126.md`](../reviews/r12-astra-m03-killarg-20261126.md) (`STEP8: REVISE`, Points `P_1–P_5`)
- **Prior Sol Audit Closed Here**: [`ideas/reviews/r12-sol-prel2-m03-holdout-20261126.md`](../reviews/r12-sol-prel2-m03-holdout-20261126.md) (closes both Blocking items: stratified fixed-delay variance/covariance + exception-only `gesvd` SVD fallback wrapper, plus both Non-blocking items: historical seed endpoints `2027220003`/`2029220003` and per-`k` `path_detection_legacy` summaries)
- **Holdout Script**: [`ideas/l2/l2_m_r12_m03_delay_holdout.py`](l2_m_r12_m03_delay_holdout.py) (imports ALL frozen receiver primitives verbatim from untouched [`l2_m_r12_m03_modtest.py`](l2_m_r12_m03_modtest.py))
- **Reproducible Dev Sizing Script**: [`ideas/probes/m_dev_r12_m03_holdout_sizing.py`](../probes/m_dev_r12_m03_holdout_sizing.py) (directly imports `run_frozen_holdout_frame` and the exact stratified inference functions from `l2_m_r12_m03_delay_holdout.py`)

## Frozen Experimental Protocol (100% Identical `R4/R5` Receiver & Channel Parameters; ONLY `ls_t = [0, k, 16]` Varied)

- **Identical `R4` & `R5` Parameters**: `N = 512, L_cpp = 16, two_Nc1 = 3, g_lo = 180, g_hi = 334, obs_lo = 196, obs_hi = 268, max_hw = 8, snr_db = 30.0, sig_r = sig_t = 1.5e-3`, 64-QAM (`Nd = 358` data bins), fixed relative path powers **`[0.4225, 0.3025, 0.2750]`**, per-frame `nu_p ~ U(-0.4, 0.4)`, uniform phase, independent Wiener PN & AWGN, zero simulator truth passed into any blind receiver.
- **Exception-Only LAPACK `gesvd` Fallback Wrapper (Zero Edit to Frozen `m3`)**:
  - After importing untouched `l2_m_r12_m03_modtest as m3` (MD5 `7d174070e3b640583e8ec0e03d948cd1` verified fail-fast before any simulation), both `l2_m_r12_m03_delay_holdout.py` and `m_dev_r12_m03_holdout_sizing.py` install an idempotent wrapper on `m3.np.linalg.svd` (also initialized in every `Pool` worker).
  - Every normal converging SVD call invokes original `numpy.linalg.svd` verbatim (guaranteeing exact `0.0` bit-for-bit diff and `0` fallbacks at `k = 7`).
  - **ONLY** when `np.linalg.LinAlgError` is raised (as observed on macOS Accelerate LAPACK for dev seed `11020055, k = 15`), the wrapper falls back to `scipy.linalg.svd(..., lapack_driver="gesvd")` and increments an audited counter reported per frame (in-memory), per `k`, per cell, and globally (`svd_gesvd_fallbacks_total`, `svd_gesvd_fallback_frames_total`, plus cell/per-`k` `svd_gesvd_fallback_frames`).
- **Pre-Registered Geometry Split (holding out original `k = 7`)**:
  - **Separated Group (`分离组`)**: **`k ∈ {3, 5, 9, 11, 13}`** (`K = 5`, all coprime to `16`, separated by `>= 3` samples from `0` and `16`; equal deterministic frame counts `n_per_k`).
  - **Adjacent Group (`相邻组`)**: **`k ∈ {1, 15}`** (`K = 2`, each frame contains two adjacent true paths `{0, 1}` or `{15, 16}` separated by 1 sample; equal deterministic frame counts `n_per_k`).
- **Same-Frame Controls**:
  - In `R4` (`single_frame`), retains exact Round-11 legacy `AFDM_EP_Dual_Sym6_NoCMSep` on the IDENTICAL received frame `y_a` and identical `3+3` GN + `6`-outer backend.
  - In `R5` (`prior_pn`), evaluates `AFDM_EP_Dual_Sym6` against `AFDM_Xu_LumpPCA_Sym6` and `AFDM_Gavert_Comb_CovDIC6` on identical data symbols, channel, and PN realizations.
- **Mandatory Path Detection Reporting (`相邻真径检出率` & full support recovery)**:
  - Logs blind-initialized delay support `det_delays` (`l_h`, plus `det_delays_legacy` in `R4`) on every frame in memory without modifying receiver execution, and writes aggregated group-level AND per-`k` summaries (for BOTH `det_delays` and, in `R4`, `det_delays_legacy`) into the output JSON (per-frame raw delay lists are aggregated rather than dumped verbatim): `exact_all3_rate` (exact CP 95% CI), `superset_all3_rate`, per-path recalls (`l=0, l=k, l=16`), `false_extra_path_rate`, and for `k ∈ {1, 15}` both **`adjacent_pair_both_detected_rate`** (`{0,1} ⊆ l_h` or `{15,16} ⊆ l_h`, exact CP 95% CI) and **`adjacent_pair_per_path_recall`**.

## Strictly Disjoint Fresh Seed Namespaces

- Prior `m02` L2: `2026112511 .. 2026172570`
- Prior `m03` Round-11 L2: `2027000001 .. 2027060060`, `2026112599`
- Prior `m03` Round-12 Modified-Method New-Seed Test: `2027100001 .. 2027170060`, `2027200001 .. 2027220003`
- Prior `m03` Round-12 dev & smoke: `10000001 .. 10030060`, `2029000001 .. 2029220003`
- Holdout independent dev sizing (`m_dev_r12_m03_holdout_sizing.py`): **`DEV_HOLDOUT_BASE = 11000001`** (`11000001 .. 11030060`, `240` seeds, plus `9990001 .. 9990002` for `k=7` startup equivalence check)
- Holdout `--smoke`: `SEED_BASE = 2029500001` (`2029500001 .. 2029530010`, `40` frames, `eq_seed = 2029590001 .. 2029590002`)
- **Official `deinlab` Holdout Test**: **`SEED_BASE = 2027500001`** (`cell_idx * 10000 + f`, **`2,120`** distinct formal frames: `Sep_R4: 2027500001..2027501400`, `Sep_R5: 2027510001..2027510400`, `Adj_R4: 2027520001..2027520200`, `Adj_R5: 2027530001..2027530120`; startup `k=7` equivalence seeds `2027590001..2027590002`, total **`2,122`** distinct seeds) — **0% overlap** with every prior run, dev set, and smoke test.

## Stratified Fixed-Delay Inference & Red Line #5 Re-Sizing (`DEV_HOLDOUT_BASE = 11000001`, `n_dev = 60` / cell)

Because each group evaluates $K$ fixed deterministic intermediate delays $k \in \mathcal{K}$ with equal deterministic stratum sizes $n_k = m = N / K$ ($w_k = 1/K$), all group-level inference uses **exact stratified fixed-delay estimation** (never pooled variance):
- Unbiased group means (exact int64 symbol-error counts over $n_{\mathrm{syms}} = 358$): $\bar{A} = \frac{1}{K}\sum_k \bar{A}_k$, $\bar{B} = \frac{1}{K}\sum_k \bar{B}_k$, $\bar{D} = \frac{1}{K}\sum_k \bar{D}_k$.
- Unbiased stratified variance and covariance of group means (`ddof=1` within each fixed delay stratum $k$):
  $$\widehat{\mathrm{Var}}(\bar{D}) = \sum_{k \in \mathcal{K}} \frac{1}{K^2}\frac{s_{D,k}^2}{n_k}, \quad \widehat{\mathrm{Var}}(\bar{A}) = \sum_{k \in \mathcal{K}} \frac{1}{K^2}\frac{s_{A,k}^2}{n_k}, \quad \widehat{\mathrm{Var}}(\bar{B}) = \sum_{k \in \mathcal{K}} \frac{1}{K^2}\frac{s_{B,k}^2}{n_k}, \quad \widehat{\mathrm{Cov}}(\bar{A},\bar{B}) = \sum_{k \in \mathcal{K}} \frac{1}{K^2}\frac{s_{AB,k}}{n_k}.$$
- Residual degrees of freedom $\mathrm{df} = \sum_{k \in \mathcal{K}}(n_k - 1) = N - K$ with Student-$t_{0.975, N-K}$ critical value applied identically to paired differences (`exact_int_stratified_paired_diff`), lock-loss differences (`stratified_paired_ll_diff`), exact Fieller quadratic CIs, and linearized ratio tests $D(M) = A - M B$ (`stratified_paired_ratio_stats`, preserving exact algebraic consistency $\widehat{\mathrm{Var}}(\bar{D}(M)) = \widehat{\mathrm{Var}}(\bar{A}) - 2M\widehat{\mathrm{Cov}}(\bar{A},\bar{B}) + M^2\widehat{\mathrm{Var}}(\bar{B})$).
- Red Line #5 precision target: every ratio primary criterion (`Xu`, `GavComb`) must have projected stratified Fieller & Delta 95% CI log-halfwidth `<= log(1.25) = 0.2231`; every `diff > 0` single-mechanism ablation criterion (`R4` `NoCMSep - EP_Dual`) must have projected stratified Student-$t_{N-K}$ 95% CI halfwidth `<= 25%` of `|dev_mean_diff|`.

Re-verified on all 240 independent dev frames (`deinlab` 8 cores, `svd_fb = 0`; Mac `11020055, k=15` also verified passing via 1 `gesvd` fallback):

| Cell (`k` set, $K$) | Dev `n=60` `EP_Dual` / Rivals & Path Detection | Stratified Dev Dispersion (`df_dev = 60 - K`) | Frozen `n_frames` (`n_per_k`, `df = N - K`) | Stratified Projected 95% CI Halfwidth |
|---|---|---|---:|---|
| **`Sep_R4`** (`{3,5,9,11,13}`, $K=5$) | `exact3=100%`; `EP=1.723e-3 (0% LL)` vs `Xu=7.002e-2 (40.65×, Fieller [26.95, 77.20])`, `NoCMSep=1.811e-2 (diff=+1.639e-2)` | `Xu`: stratified Fieller `log_hw = 0.5263` (`Delta 0.4842`, `req_per_k = 57`); **`NoCMSep`**: `sd_within = 0.07500`, 25% budget `= 0.004097` (`req_per_k = 258`) | **`1,400`** (`280/k`, `df=1395`) | **`NoCMSep` `hw = 0.003932 <= 0.004097` (`24.0% <= 25%`)**; `Xu` Fieller `log_hw = 0.0984 << 0.2231` (`Delta 0.0981`) |
| **`Sep_R5`** (`{3,5,9,11,13}`, $K=5$) | `exact3=100%`; `EP=3.818e-3 (0% LL)` vs `Xu=9.837e-2 (25.77×, Fieller [17.47, 47.74])`, `GavComb=4.229e-1 (110.77×, Fieller [77.17, 199.76])` | `Xu`: Fieller `log_hw = 0.5025` (`Delta 0.4635`, `req_per_k = 52`); `GavComb`: Fieller `log_hw = 0.4756` (`Delta 0.4368`, `req_per_k = 47`) | **`400`** (`80/k`, `df=395`) | **`Xu` Fieller `log_hw = 0.1780 <= 0.2231` (`Delta 0.1761`)**; `GavComb` Fieller `= 0.1678 <= 0.2231` (`Delta 0.1660`) |
| **`Adj_R4`** (`{1,15}`, $K=2$) | `exact3=0.0%, adj_both=0.0%, adj_recall=50.0%`; `EP=0.9411` vs `Xu=0.9390 (0.998×, Fieller [0.9953, 1.0003])`, `NoCMSep=0.9276 (diff=-1.345e-2)` | `Xu`: Fieller `log_hw = 0.0025 << 0.2231` (`req_per_k = 2`); **`NoCMSep`**: `sd_within = 0.02158`, 25% of `|diff|` `= 0.003364` (`req_per_k = 81`) | **`200`** (`100/k`, `df=198`) | **`NoCMSep` `hw = 0.003008 <= 0.003364` (`22.4% <= 25%`)**; `Xu` Fieller `log_hw = 0.0014`; `adj_both` CP `hw ≈ 0.914 pp` |
| **`Adj_R5`** (`{1,15}`, $K=2$) | `exact3=0.0%, adj_both=0.0%, adj_recall=50.0%`; `EP=0.9285` vs `Xu=0.9253 (0.997×)`, `GavComb=0.9210 (0.992×)` | `Xu`: Fieller `log_hw = 0.0036 << 0.2231` (`req_per_k = 2`); `GavComb`: Fieller `log_hw = 0.0058 << 0.2231` (`req_per_k = 2`) | **`120`** (`60/k`, `df=118`) | `Xu` Fieller `log_hw = 0.0025 << 0.2231`; `GavComb` Fieller `= 0.0040 << 0.2231`; `adj_both` CP `hw ≈ 1.514 pp` |

## Pre-Registered Verdicts & Claim-Scope Adjudication Rule

1. **`GATES_OK`** (script exits immediately with code 2 if failed):
   - Exact MD5 of untouched `ideas/l2/l2_m_r12_m03_modtest.py` equals `7d174070e3b640583e8ec0e03d948cd1` (checked fail-fast BEFORE running any FD or simulation check).
   - Startup `k = 7` bit-for-bit identity check (`max_abs_diff == 0.0` AND `k7_svd_gesvd_fallbacks == 0`) against `m3.run_single_frame` for BOTH `R4` (`single_frame`) and `R5` (`prior_pn`).
   - Projected Jacobian finite-difference error `fd_jacobian_rel_err < 1e-6`.
2. **Separated Group Verdict (`PASS_SEPARATED`, `k ∈ {3, 5, 9, 11, 13}`, stratified `df = N - 5`)**:
   - `SEP_R4_XU_4X`: `AFDM_EP_Dual_Sym6` beats `AFDM_Xu_LumpPCA_Sym6` by `>= 4.0×` (exact int64 stratified linearized paired 95% CI lower bound `>= 0.0` AND stratified rival mean 95% CI `> 0.0`).
   - `SEP_R4_CMSEP_MECH`: `AFDM_EP_Dual_Sym6` strictly beats `AFDM_EP_Dual_Sym6_NoCMSep` (exact int64 stratified paired SER diff 95% CI lower bound `> 0.0`).
   - `SEP_R5_XU_5X`: `AFDM_EP_Dual_Sym6` beats `AFDM_Xu_LumpPCA_Sym6` by `>= 5.0×`.
   - `SEP_R5_GAVCOMB_5X`: `AFDM_EP_Dual_Sym6` beats `AFDM_Gavert_Comb_CovDIC6` by `>= 5.0×`.
   - `PASS_SEPARATED = GATES_OK && SEP_R4_XU_4X && SEP_R4_CMSEP_MECH && SEP_R5_XU_5X && SEP_R5_GAVCOMB_5X`.
3. **Adjacent Group Verdict (`PASS_ADJACENT`, `k ∈ {1, 15}`, stratified `df = N - 2`)**:
   - Identical 4 clauses (`ADJ_R4_XU_4X`, `ADJ_R4_CMSEP_MECH`, `ADJ_R5_XU_5X`, `ADJ_R5_GAVCOMB_5X`) evaluated separately on the adjacent group under the same stratified estimator.
   - `PASS_ADJACENT = GATES_OK && ADJ_R4_XU_4X && ADJ_R4_CMSEP_MECH && ADJ_R5_XU_5X && ADJ_R5_GAVCOMB_5X`.
4. **Claim-Scope Decision (writes ONLY into `I-20261125-m03.md`; NEVER alters Round-11/12 frozen verdicts)**:
   - `PASS_SEPARATED && PASS_ADJACENT` -> cross-geometry 3-path advantage supported across both separated and adjacent delays.
   - `PASS_SEPARATED && !PASS_ADJACENT` -> **`RESTRICT_TO_SEPARATED_3PATH`**: restrict `m03` claim strictly to tested separated 3-path geometries (`[0, k, 16], k ∈ {3, 5, 9, 11, 13}` + `k = 7`); explicitly disclose adjacent-path local-peak drop (`adj_both ≈ 0%`) and adjacent-group SER/ratios as the applicability boundary.
   - `!PASS_SEPARATED` -> **`RETRACT_CROSS_GEOMETRY_MULTIPLIER_CLAIM`**: retract cross-geometry multiplier claim.
