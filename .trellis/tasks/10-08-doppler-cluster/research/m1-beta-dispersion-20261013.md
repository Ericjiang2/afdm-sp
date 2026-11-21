# M1 upper-bound check: DPSS column-energy dispersion r_{l,d} = beta_{l,d} / ||x||^2 (2026-10-13)

Rule (frozen before data, collab-plan-b-20261013.md): p99 of |r-1| <= .05 in every case -> drop M1 (methods caveat); > .20 in any case -> receiver-level M1 arm test; otherwise report, Claude decides.

## Setup
- Generator: driver_c1 draw_c1_paths / c1_message / c1_base + base.cluster_at_snr / observe; old entropy 129abc..., frames 0-49, rho .3, SNR 6.5 dB, L in {16, 32}, genie (distinct true) delays (50 x 16 + 50 x 32 = 2400 taps per case and index d).
- Columns: dpss_rx.tap_columns(n=1024, c=0, W=2.5, D=8) (flat-arm basis), mean |m_d[k]|^2 = 1 for every d.
- x = observation-normalised AF signal: (a) pilot only; (b) pilot + true data; (c) pilot + 0.5 true data (pilot = obs['pilot'], data = raw['data']/sqrt(2(1-rho)), both from base.observe's convention).
- beta_{l,d} is the receiver's own column energy: diag(B^H B) of dpss_rx.Design (B = xt[(k-l) mod N] * CPP phase * m_d[k], xt = physical.daft(x, c1, c2, True)); cross-checked against the direct formula sum_k |m_d[k]|^2 |x_t[(k-l) mod N]|^2 (max difference 4e-15 of ||x||^2). ||x_t||^2 = ||x||^2 to 5e-16.
- Pooled over frames x taps x both L (n = 2400 per row). Script and JSON were scratch on deinlab (/data/guoyikun/tmp/m1_beta, deleted).

## |r - 1| per case and DPSS index d (pooled over L)
| d | (a) mean / std / p1 / p99 / max | (b) mean / std / p1 / p99 / max | (c) mean / std / p1 / p99 / max |
|---|---|---|---|
| 0 | .0004 / .0000 / .0004 / .0004 / .0004 | .0267 / .0208 / .0006 / .0880 / .1046 | .0212 / .0168 / .0003 / .0733 / .0875 |
| 1 | .0005 / .0001 / .0002 / .0007 / .0007 | .0221 / .0153 / .0002 / .0662 / .0721 | .0175 / .0121 / .0003 / .0522 / .0573 |
| 2 | .0009 / .0005 / .0000 / .0019 / .0019 | .0172 / .0137 / .0002 / .0560 / .0585 | .0139 / .0106 / .0004 / .0458 / .0542 |
| 3 | .0028 / .0014 / .0000 / .0044 / .0044 | .0172 / .0132 / .0004 / .0513 / .0536 | .0138 / .0101 / .0003 / .0394 / .0414 |
| 4 | .0020 / .0008 / .0000 / .0034 / .0034 | .0241 / .0196 / .0005 / .0938 / .1000 | .0189 / .0158 / .0002 / .0732 / .0803 |
| 5 | .0090 / .0039 / .0002 / .0132 / .0132 | .0355 / .0279 / .0009 / .1185 / .1249 | .0268 / .0203 / .0004 / .0920 / .1003 |
| 6 | .0137 / .0079 / .0001 / .0248 / .0248 | .0403 / .0306 / .0005 / .1314 / .1469 | .0309 / .0231 / .0005 / .0935 / .1087 |
| 7 | .0116 / .0066 / .0003 / .0223 / .0223 | .0390 / .0295 / .0006 / .1235 / .1577 | .0307 / .0237 / .0006 / .0935 / .1181 |
| all d | .0051 / .0064 / .0001 / .0243 / .0248 | .0278 / .0240 / .0004 / .1114 / .1577 | .0217 / .0185 / .0003 / .0849 / .1181 |

r itself stays centred: case-wise r mean per d lies in [.995, 1.009]; min / max of r over all d: (a) .979 / 1.025, (b) .864 / 1.158, (c) .903 / 1.118.
Split by L (worst d, p99 / max): (a) L16 .0248 / .0248, L32 .0248 / .0248; (b) L16 .130 / .149, L32 .132 / .158; (c) L16 .093 / .109, L32 .095 / .118. No L dependence beyond noise.

## Conclusion (3 lines)
1. Case-level p99 of |r-1| (pooled over d; worst single d in brackets): (a) .024 (.025), (b) .111 (.131), (c) .085 (.094); largest |r-1| anywhere .158 (case b, d = 7, L32).
2. b and c exceed .05, none exceeds .20 -> neither extreme branch of the frozen rule applies: **middle branch, "report; Claude decides"**.
3. The mismatch is zero-mean (r centred at 1, mean |r-1| .02-.03 with data), grows with the data share of x and with DPSS order (d >= 5), and reaches about +-10-16 % at the tails under ideal feedback, +-9-12 % at half feedback.
