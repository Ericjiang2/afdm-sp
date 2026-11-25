You are the cross-family Pre-L2 Final Sign-Off Auditor (`gpt-6.2-sol` high, ≤90s) for `I-20261125-m02` (`[放宽TWC]`). Read-only; do not edit files.

All 4 remaining line items from `r11-sol-prel2-m02-v2-20261125.md` have been patched in:
- `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m02_dual_pn.py`
- `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_m_r11_m02.md`

Exact 4 patches:
1. Lines 469–477 (`verify_analytical_lumped_bound_suite`): Fixed first-order Taylor expansion of `angle(sum_p v_opt[p] e^{j th_p})` to use `v_phase = np.real(v_opt)` (matches your complex 2x2 counterexample `0.25 == 0.25` exactly!).
2. Lines 228–252 & 671–685 (`AFDM_Xu_LumpPCA_Sym6`): Added `refine_channel_sbl_em()` implementing Xu PIMRC'26 (arXiv:2604.17858) SBL-EM Bayesian MAP posterior + hyperparameter `gamma_p = |mu_p|^2 + Sigma_h[p,p]` joint update inside the symmetric 6-outer best-residual loop.
3. Lines 687–694 (`AFDM_Gavert_Guard_1Step`): Now runs preliminary OAMP at CPE and passes FULL signal `s_est_g1 = P_a @ (Ah_a @ xs_0)` + exact residual data covariance `Sigma_g1` (Gävert Eqs. 18/28) into the 1-step Bayesian PCA update.
4. Lines 788–806 (`AFDM_LumpOrac_Indep`) + `PREDICTIONS_m_r11_m02.md` line 31: `AFDM_LumpOrac_Indep` now uses exact Hermitian row-sum optimal weights `v_opt_o` & covariance-corrected `sig2_irred`; `PREDICTIONS` line 31 explicitly lists `OFDM_c1=0_SameMask_Sym6`.

Please verify ONLY those 4 patches cleanly (≤200 Chinese characters) and output:
`PRE_L2_VERDICT: APPROVED_FOR_DEINLAB` or `PRE_L2_VERDICT: FIX_BEFORE_L2 — <line>`.
