Phase 1b committed as `e5698b6e`. The protocol remains DRAFT. Confirmed `model: gpt-6.2-sol`.

| Gate | Result |
|---|---|
| G1 | PASS — all 32 historical keys and unmasked F0 states matched bit-for-bit |
| G2 | PASS — generator, delay masking, and closed-form checks |
| G3 | PASS — both v2 frame blocks verified fresh |

**Selected SNR and ξ ∈ [¼, 4] counts:** ρ=.3 → 4.5 dB, 1,708/2,400. ρ=.5 → 4.5 dB, 1,683/2,400.  
**Undefined windows:** 0/24,000 (0%). Exchange qualification used historical inputs only.  
**Predictions:** [out/phase1b/predictions_v2.json](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/ratio_sweep_20261118/out/phase1b/predictions_v2.json). The curve uses the strongest estimated r1 path. The later oracle draft requires a matching curve.  
**Main cost:** 5.00 core-hours with 30% headroom, or 5.18 if every unit triggers. Draft cap: 10 core-hours.