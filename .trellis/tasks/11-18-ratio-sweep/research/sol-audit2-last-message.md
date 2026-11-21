Post hoc audit 2 committed as `df8c3d15`. Replayed 2,016 units in **0.2090 core-hours**. Confirmed `model: gpt-6.2-sol`.  
**Closure:** Five terms failed on all units, with maximum relative error 0.296. Adding the true-versus-fitted Doppler term passed on all units, with maximum error 2.47×10⁻¹⁵.  
**Reading rule: SUPPORTED.** At R≤4, b1+b2 accounted for **80.3% / 89.9%** of the shortfall at ρ=.3/.5. b2 dominated. c+d accounted for 0.86% / 0.42%.  
Medians in order (a, b1, b2, c, d), identical across arms at the shown precision. [Full tables and IQRs](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/ratio_sweep_20261118/audit_v2/AUDIT2.md)

| ρ | R=1.5 | R=4 | R=12 | R=64 |
|---|---|---|---|---|
| .3 | (.8616, −.0111, −.3532, 0, −.0017) | (.9373, −.0048, −.3620, 0, −.0012) | (.9725, −.0046, −.3033, 0, .0043) | (.9300, −.0054, −.0120, 0, .0371) |
| .5 | (.9352, −.0032, −.3443, 0, −.0005) | (.9717, −.0037, −.3647, 0, −.0033) | (.9829, −.0030, −.3690, 0, .0029) | (.9214, .0019, −.3098, 0, .0731) |