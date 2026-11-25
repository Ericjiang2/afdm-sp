# Stage A7 Results: Decisive Diagnosis on High-SNR (4.5–5.0 dB) Stage A6 `SBdop` Failures

- Freeze commit: `161de2e529f00135cc6cc305e7c47f5b88614d96`
- Confirmation cohort: `38` keys across `25` unique physical frames (`snr in [450, 500]`)
- Runtime: **0.2865 core-hours** (cap `1.00 h`, wall `54.0 s`)
- **Frozen Verdict**: **`SEARCH`**

## Primary Proportions (Physical-Frame Cluster Bootstrap, 2000 draws, seed 20261125)

| Observable | Count / Share [95% Cluster CI] |
|---|---|
| `f_SB` (`L_SB(SB) > L_SB(truth_box)`) | `38/38` (`100.00%`, 95% CI `[100.00%, 100.00%]`) |
| `f_SBG_rescue` (truth-free `SBGdop` errors == 0) | `38/38` (`100.00%`, 95% CI `[100.00%, 100.00%]`) |
| `f_SBG_reaches_tbox` (`L_SB(SBG) <= L_SB(truth_box) + 0.1`) | `34/38` (`89.47%`, 95% CI `[75.00%, 100.00%]`) |
| `f_KD` (`L_KD(sb_box) > L_KD(truth_box)`) | `38/38` (`100.00%`, 95% CI `[100.00%, 100.00%]`) |
| `f_code` (coded valid-LDPC ML prefers truth over `SBdop`) | `38/38` (`100.00%`, 95% CI `[100.00%, 100.00%]`) |
| `f_tbox_rescue` (oracle truth-box `SB` errors == 0) | `38/38` (`100.00%`, 95% CI `[100.00%, 100.00%]`) |
| `f_ldop_rescue` (archived true-Doppler `ldop` errors == 0) | `38/38` (`100.00%`, 95% CI `[100.00%, 100.00%]`) |

## Breakdown by `(ρ, SNR)` Cell

| ρ | SNR (dB) | n | `SB` prefers truth | `SBGdop` rescues | `tbox` rescues | `ldop` rescues | `KD` prefers truth | Median `ΔL_SB` (nats) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.10 | 4.5 | 21 | 21/21 | 21/21 | 21/21 | 21/21 | 21/21 | +73.59 |
| 0.10 | 5.0 | 10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | +98.09 |
| 0.15 | 4.5 | 6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | +50.75 |
| 0.15 | 5.0 | 1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | +58.35 |

## Log-Likelihood Gap Quantiles & Doppler Diagnostics

- `ΔL_SB = L_SB(SB) - L_SB(truth_box)` (nats): min `25.44`, p25 `50.36`, median **`74.32`**, p75 `98.58`, max `139.98`.
- `ΔL_KD = L_KD(sb_box) - L_KD(truth_box)` (nats): min `139.32`, median **`411.77`**, max `880.52`.
- Capped MAE: `SB` `0.0955` -> `SBG` **`0.0417`**; path outlier frac (`>0.25` bin): `39.14%` -> **`4.61%`**.
- Per-key `SBG` CPU time: mean `2.60 s`, median `2.65 s`, p95 `3.43 s`.
