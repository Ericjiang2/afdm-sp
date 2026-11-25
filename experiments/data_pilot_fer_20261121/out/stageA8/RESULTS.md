# Stage A8 Results: Full-Frame 1% FER Recovery of Truth-Free Global Semi-Blind Doppler (`SBGdop`)

- Freeze commit: `856e6401f88afe752fd249d627c7f3a8286d51a4`
- Grid: frames `41000–41399` × U/G (`800` draws/cell), ρ ∈ `[100, 150]`, SNRs = `[300, 400, 450, 500]`
- Runtime: **5.8995 core-hours** (cap `8.20 h`, wall `785.3 s`)

## Primary Verdict (Pre-Registered, 1% info-FER U/G Mean, LB >= 0.50 dB Gate)

| Contrast | Point (dB) | 95% Paired CI (dB) | Verdict |
|---|---:|---|---|
| `min CD2 (100..250) − min SBGdop (100..150)` | **0.9492** | **[0.8063, 1.0254]** | **GO** |

## 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)

| Arm | ρ=0.10 | ρ=0.15 | ρ=0.20 | ρ=0.25 | Best (dB) [95% CI] | Best ρ |
|---|---:|---:|---:|---:|---|---:|
| CD2 | 7.9712 | 4.7053 | 4.4156 | 4.5273 | **4.4156** [4.2706, 4.4899] | 0.20 |
| PWdop | [5.0000, +inf] | 4.3501 | — | — | **4.3501** [4.1819, 4.5453] | 0.15 |
| SBdop | [5.0000, +inf] | 4.3769 | — | — | **4.3769** [4.1737, 4.5615] | 0.15 |
| SBGdop | 3.4664 | 3.9437 | — | — | **3.4664** [3.4619, 3.4703] | 0.10 |
| s100 | 3.8391 | 4.0617 | 4.2489 | — | **3.8391** [3.6030, 4.0387] | 0.10 |
| s050 | 3.4559 | 3.4861 | 4.0884 | — | **3.4559** [3.4502, 3.4606] | 0.10 |
| ldop | 3.4518 | 3.4848 | 4.0721 | — | **3.4518** [3.4458, 3.4569] | 0.10 |

## Secondary Contrasts (95% Paired Frame Bootstrap, seed 20261125, dB)

| Contrast | Point (dB) | 95% CI (dB) |
|---|---:|---|
| SBdop_minus_SBGdop | 0.9106 | [0.7086, 1.0957] |
| PWdop_minus_SBGdop | 0.8837 | [0.7176, 1.0790] |
| SBGdop_minus_s050 | 0.0105 | [0.0075, 0.0138] |
| SBGdop_minus_ldop | 0.0145 | [0.0114, 0.0179] |
| SBGdop_minus_s100 | -0.3727 | [-0.5721, -0.1370] |
| CD2_minus_SBdop | 0.0386 | [-0.1890, 0.2327] |
| CD2_minus_ldop | 0.9638 | [0.8198, 1.0388] |

## Per-(ρ, SNR) Doppler Metric, FER & Paired Rescue/Regression vs `SBdop` (800 Draws/Cell)

| ρ | SNR (dB) | `SBG` MAE [med] | `SBG` >0.25 | `SBG` F0 FER | `SBG` Final FER | `SB` Final FER | Rescued (`SB->SBG`) | Regressed (`SB->SBG`) |
|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 0.10 | 3.0 | 0.0470 [0.0446] | 10.91% | 82.25% | **56.12%** | 75.75% | `+158` | `-1` |
| 0.10 | 4.0 | 0.0427 [0.0404] | 9.47% | 3.25% | **0.00%** | 5.25% | `+42` | `-0` |
| 0.10 | 4.5 | 0.0410 [0.0386] | 9.08% | 0.12% | **0.00%** | 2.62% | `+21` | `-0` |
| 0.10 | 5.0 | 0.0392 [0.0369] | 8.36% | 0.00% | **0.00%** | 1.25% | `+10` | `-0` |
| 0.15 | 3.0 | 0.0428 [0.0408] | 10.30% | 93.12% | **83.38%** | 88.50% | `+47` | `-6` |
| 0.15 | 4.0 | 0.0391 [0.0375] | 9.03% | 6.38% | **0.88%** | 3.38% | `+21` | `-1` |
| 0.15 | 4.5 | 0.0375 [0.0358] | 8.44% | 0.38% | **0.00%** | 0.75% | `+6` | `-0` |
| 0.15 | 5.0 | 0.0360 [0.0343] | 7.80% | 0.00% | **0.00%** | 0.12% | `+1` | `-0` |

## Paired Accounting & Timing Summary

- Across all `6400` paired keys vs Stage A6 `SBdop`: rescued `306`, regressed `8`, both failed `1115`, both succeeded `4971`.
- Per-key `SBG` CPU time: mean **`2.943 s`**, median `2.820 s`, p95 `4.298 s`.
