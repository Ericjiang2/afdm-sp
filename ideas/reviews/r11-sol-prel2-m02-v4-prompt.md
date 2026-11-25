You are the cross-family Pre-L2 Final Sign-Off Auditor (`gpt-6.2-sol` high, ≤60s) for `I-20261125-m02` (`[放宽TWC]`). Read-only; do not edit files.

The exact 3 line ranges from `r11-sol-prel2-m02-v3-20261125.md` have been patched in `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m02_dual_pn.py`:
1. `refine_channel_sbl_em` (lines 229–260): Exact Xu arXiv:2604.17858 Eq. (13) SBL-EM update (`gamma_m = (sqrt(1 + 4*rho*(|mu_m|^2 + Sigma_mm)) - 1)/(2*rho)` and `beta = (N+c-1)/(d + C_beta)` with `C_beta = ||y_d - X mu_h||^2 + (1/beta) sum(1 - Sigma_mm/gamma_m)`).
2. `oamp_exact` + `AFDM_Gavert_Guard_1Step` + `AFDM_Gavert_Comb_CovDIC6` (lines 98–107, 695–703, 745–755): `oamp_exact` returns exact per-symbol posterior variance vector `vx_vec` (shape `Nd`), used directly as `M @ diag(vx_vec) @ M^H` in both `Sigma_g1` and `Sigma_res` (no scalar mean approximation).
3. `AFDM_LumpOrac_Indep` (lines 795–815): Computes exact per-sample local Hermitian covariance `Wn_o[n]`, per-sample optimal weights `v_n_o[n] = sum_q Wn_o[n, :, q]`, and unnormalized receiver-side irreducible interference variance `sig2_irred_rx = Re(sum(W_avg * C_o))` (exact receiver-side scale without dividing by `w_tot_o`).

Please verify ONLY these 3 patches (≤150 Chinese characters) and end with:
`PRE_L2_VERDICT: APPROVED_FOR_DEINLAB` or `PRE_L2_VERDICT: FIX_BEFORE_L2 — <line>`.
