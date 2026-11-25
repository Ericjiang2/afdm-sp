# Stage A5 Results: Semi-Blind Round-0 Doppler Proxy Check

- Freeze commit: `75530d4d2a953a9efc54c5d0771d840c2134a0af`
- Draws: **200** (frames `41000–41099` × U/G), SNRs: `[400]`
- Runtime: **1.9665 core-hours** (cap 6.0 h, wall 327.0 s)

## Primary Verdict (Pre-Registered, SNR = 4 dB)

- `E = min_{ρ ∈ {0.10, 0.15}} mean(SB)` = **0.0430 bin** (at ρ=0.15), 95% CI **[0.0408, 0.0455] bin** → **PASS** (threshold `0.08` bin)

## 4 dB Summary Table (Power-Weighted Capped MAE, bin; 200 Draws)

| ρ | PW mean [med] | SB mean [med] (95% CI) | KD mean [med] | SB-CRB | PW-CRB | SB Eff | PW Eff | SB Outlier >0.25 | Stage A Actual (4–5 dB) |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| 0.10 | 0.0930 [0.0874] | **0.0527** [0.0472] ([0.0495, 0.0559]) | 0.0154 [0.0149] | 0.0398 | 0.0852 | 1.32× | 1.09× | 23.25% | 0.1568 |
| 0.15 | 0.0726 [0.0702] | **0.0430** [0.0408] ([0.0408, 0.0455]) | 0.0155 [0.0151] | 0.0369 | 0.0684 | 1.17× | 1.06× | 18.62% | 0.1079 |
| 0.20 | 0.0607 [0.0585] | **0.0376** [0.0361] ([0.0355, 0.0398]) | 0.0156 [0.0152] | 0.0346 | 0.0581 | 1.09× | 1.04× | 15.06% | 0.0824 |
