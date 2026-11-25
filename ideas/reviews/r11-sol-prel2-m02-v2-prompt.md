You are the cross-family Pre-L2 Final Sign-Off Auditor (`gpt-6.2-sol` high, ≤2 min) for `I-20261125-m02` (`[放宽TWC]`). Read-only; do not edit files.

All 6 items from your `FIX_BEFORE_L2` report (`r11-sol-prel2-m02-20261125.md`) have been patched in:
- `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m02_dual_pn.py`
- `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_m_r11_m02.md`
- `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m02.md`

Summary of exact patches applied & smoke-verified (`FD_err=8.31e-10`):
1. Lines 459–486: Exact Hermitian row-sum optimal weights `v_opt = W.sum(axis=1) / sum(W)` used in BOTH analytical bound `ana_cov` AND MC `phi_ind` (errors: `0.088 / 0.032 / 0.005 dB` across 3 settings).
2. Lines 633–657: `AFDM_Xu_LumpPCA_Sym6` now uses joint channel + single-end PN update on ALL regimes AND the exact same best-residual 6-outer loop (`8`-iter OAMP, no extra final pass) as `run_dual_outer`.
3. Lines 686–725: `AFDM_Gavert_Comb_CovDIC6` now uses FULL signal `s_est_ext_c = P_a @ (Ah_a @ xs_0)` (pilot + estimated data) on `(A_a @ y_c)[comb_mask]` with exact residual data covariance `Sigma_inv` (`Gävert` Eqs. 18/28), and in `R4_SingleFrameBlind` estimates its own blind CSI strictly from `y_c` (ZERO cross-frame borrowing of `y_a`!). ZeroPN `R0` verified `0.0000` on ALL 8 arms!
4. Lines 727–745: `OFDM_c1=0` readout now uses identical `phi_cpe` warm-start as `AFDM_EP_CPE_GN6` and reports BOTH OFDM-centered 72-bin `[220:292]` (`5.45e-2`) AND identical index mask `[196:268]` (`5.59e-2`) vs `EP_Dual=0.000` (`SCOPE_READOUTS` only).
5. Lines 861–863 + `PREDICTIONS_m_r11_m02.md` + `I-20261125-m02.md` lines 69–70: Tightened `P1_R3 (45 dB)` to `>= 10x` against ALL 3 rivals (`Xu`, `GavComb`, `Gav1St`) and synchronized card text verbatim with `PREDICTIONS_m_r11_m02.md`.

Please verify these 5 patches cleanly (≤300 Chinese characters) and end with:
`PRE_L2_VERDICT: APPROVED_FOR_DEINLAB` or `PRE_L2_VERDICT: FIX_BEFORE_L2 — <remaining line>`.
