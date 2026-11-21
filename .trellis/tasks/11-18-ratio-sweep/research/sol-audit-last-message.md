Post hoc audit committed as `b4e294cf`. Replayed 2,016 units in **0.2074 core-hours**. Confirmed `model: gpt-6.2-sol`.  
**Item 5 PASS:** maximum absolute error in E, u, and λ was **0** across 20 units in both arms.

| ρ, R | Phantom median error % A2/CODELAY | Spearman A2/CODELAY | Median weak gain measured/model | Median normalized weak projection | Median γ / κ_cal | Aliasing |
|---|---:|---:|---:|---:|---:|---:|
| .3, 1.5 | 0.63 / 86.90 | .995 / .007 | .266 | .502 | .933 / 1.700 | 0/84 |
| .3, 4 | 0.91 / 88.24 | .997 / −.206 | .345 | .579 | .992 / 1.191 | 0/84 |
| .3, 12 | 0.96 / 89.73 | .997 / −.128 | .450 | .644 | 1.011 / .941 | 0/84 |
| .3, 64 | 5.11 / 94.98 | .941 / −.201 | .845 | .849 | 1.002 / .287 | 0/84 |
| .5, pooled | 0.44 / 83.16 | .998 / −.011 | .388 | .601 | 1.028 / 1.013 | 0/1,008 |

Weak-side medians agree across arms at the displayed precision. Maximum absolute weak-gain difference was 2.84×10⁻¹⁴. [AUDIT.md](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/ratio_sweep_20261118/audit_v2/AUDIT.md)