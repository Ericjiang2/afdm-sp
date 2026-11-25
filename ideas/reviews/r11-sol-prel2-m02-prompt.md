You are the cross-family Step-6 REVISE re-checker AND Pre-L2 Static Code & Steelman Baseline Auditor (`gpt-6.2-sol` high, ≤3 min) for runner m's Round-11 `[放宽TWC]` card `I-20261125-m02`. Read-only; do not edit files.

Files to inspect (ALL standalone in repo, ZERO missing cache imports):
- Updated card: `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/cards/I-20261125-m02.md`
- Standalone L2 script: `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_m_r11_m02_dual_pn.py`
- Pre-registered predictions: `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_m_r11_m02.md`
- Previous Step-6 REVISE report: `/Users/guoyikun/Downloads/share/claode_birain/afdm-funnel-m/00_Inbox/AFDM-channel-estimation/ideas/reviews/r11-sol-step6-m02-20261125.md`

Executed smoke verification highlights (already run after final edit):
- `FD_jac_rel_err = 8.31e-10`; `Leak_N512(72-bin obs) = -28.61 dB`; `Leak_N256(38-bin obs) = -28.86 dB`.
- Guard-band covariance-corrected analytical lumped floor vs MC (250 fr, 0 fitted params): `L12 = 0.088 dB`, `L16 = 0.032 dB`, `L8_4path = 0.005 dB`.
- `R0_ZeroPN_30dB`: ALL blind AFDM arms (`Uncomp`, `XuLump`, `GavComb_CovDIC6`, `Gav1St`, `EP_CPE`, `EP_Dual`) = `0.0000`.
- `R2 (30 dB, 3e-3)`: `XuLump=8.24e-2`, `GavComb=3.35e-1`, `Gav1St=5.31e-2`, `EP_Dual=1.40e-3`, `LumpOrac=3.21e-2`.
- `R4_SingleFrameBlind (4 fr, zero training frame)`: `XuLump=7.40e-2 (75%)`, `GavComb=2.50e-1`, `Gav1St=4.19e-3`, `EP_Dual=0.000 (0%)`, `LumpOrac=2.03e-2`.
- `R5_PNTrain (2 fr, PN-corrupted training frame)`: `XuLump=4.19e-2`, `GavComb=5.28e-1`, `Gav1St=1.44e-1`, `EP_Dual=0.000`, `LumpOrac=1.12e-2`.
- `R6_Rand4_N256 (4 fr)`: `XuLump=1.56e-2`, `GavComb=7.34e-2`, `Gav1St=2.19e-2`, `EP_Dual=0.000`, `LumpOrac=1.56e-3`.

Please check the 5 pre-L2 audit items under Round-11 `[放宽TWC]` rules (no OFDM requirement in PASS_PRIMARY; no cross-paper assembled hybrid rivals; rivals capped at published AFDM `Xu PIMRC'26` + mother method `Gävert TCOM'25` `F_N->A` direct port):
1. Are ALL 8 items from your Step-6 `REVISE` cleanly resolved (standalone script, FD Jacobian check, 72-bin obs leakage + energy check, `Xu` single-end PCA + `Gävert` Eqs.18/28 CovDIC6 ZeroPN=0.000 + Guard-1Step, `R4_SingleFrameBlind` + `R5_PNTrain`, guard-band covariance analytical bound, single-knob `c1=0` readout in `SCOPE_READOUTS` only)?
2. Static code audit: ANY side-information leak (`sig2_true`, `hs_t`, `ls_t`, `nus_t`, `phi_r`, `phi_t`, `x_data` entering any blind arm)? ANY asymmetry in init/outer steps, broken baseline, RNG misalignment, or sign/normalization bug (verify any sign claim on a 5-line toy test)?
3. Are the pre-registered `PASS_PRIMARY` clauses in `PREDICTIONS_m_r11_m02.md` clean, falsifiable, non-watered-down, and properly aligned with `[放宽TWC]`?
4. Output concise Simplified Chinese (<600 chars) ending with a clear verdict line:
   `PRE_L2_VERDICT: APPROVED_FOR_DEINLAB` or `PRE_L2_VERDICT: FIX_BEFORE_L2 — <exact bug lines>`.
