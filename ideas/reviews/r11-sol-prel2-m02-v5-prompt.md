You are the cross-family Pre-L2 Final Sign-Off Auditor (`gpt-6.2-sol` high, ≤45s) for `I-20261125-m02` (`[放宽TWC]`). Read-only; do not edit files.

All 3 remaining items from `r11-sol-prel2-m02-v4-20261125.md` are now fixed in `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m02_dual_pn.py`:
1. `oamp_exact` (line 99) & `Sigma_g1`/`Sigma_res` (lines 697, 748): returns unclamped raw posterior variance `vx_vec_raw` (`0.0` on deterministic symbols, zero floor clamping) and uses it directly without artificial floor clamping.
2. `refine_channel_sbl_em` (lines 229–257): removed artificial clamps on `beta` and `gam` (only `1e-12` zero-div guard), and explicitly noted the PDF Eq. (13) parenthesis typo (`sqrt(4*rho*(|mu|^2+Sigma+1)) - 1 < 0` for small `rho`, whereas exact M-step root of `rho*g^2 + g - (|mu|^2+Sigma) = 0` is `(sqrt(1 + 4*rho*(|mu|^2+Sigma)) - 1)/(2*rho)`).
3. `AFDM_LumpOrac_Indep` (lines 795–811): uses exact per-sample local normalized weights `local_w = v_n_o.real / v_n_o.real.sum(axis=1, keepdims=True)` and exact local receiver-side variance `sig2_irred_rx = float(np.sum(Wn_o.real * C_loc, axis=(1, 2)).mean())` matching your verification script verbatim.

Verify ONLY these 3 items (≤100 Chinese characters) and output:
`PRE_L2_VERDICT: APPROVED_FOR_DEINLAB` or `PRE_L2_VERDICT: FIX_BEFORE_L2 — <line>`.
