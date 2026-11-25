# Huang-2010-style Steelman Experiment Results

- Keys: **62400** (18009 archived F0 triggers across 400 physical frames 5400–5799; full 6-rho grid)
- HG OMP recipe: `B0-p2-s0.5`, max passes: `2`, arms: `['F0', 'CD', 'HG', 'HG1', 'Z', 'HGint']`
- Main CPU: **9.8401 core-hours** (wall 3039.0 s)
- Bootstrap: 50,000 paired physical-frame draws (seed 20261124); Bonferroni α = 0.05/3 (98.33% CIs); Q2/Q3 use 36-pair simultaneous projection.

## Primary Verdicts (Pre-registered)

| Contrast | Point (dB) | 98.33% Primary CI (dB) | 98.33% Per-draw CI (dB) | Verdict | Notes |
|---|---|---|---|---|---|
| Q1: HG(.30) − CD(.30) | -0.2962 | [-0.4947, -0.1452] | — | consistency | paired CI at fixed ρ=0.30 |
| Q2: min HG − min CD | -0.6533 | [-0.9668, -0.1936] | [-0.7981, -0.4550] | **HG_AHEAD** | 36-pair proj CI; dir=HG_better, L>0.5=False, U<-0.5=False |
| Q3: min Z − min CD | 0.0501 | [-0.2141, 0.3270] | [-0.0002, 0.1722] | **Z_EQUIVALENT** | 36-pair proj CI; dir=includes_zero, nonzero=False |

## Per-Scenario Primary Contrasts

| Scenario | Q1 (dB) | Q2 (dB) / Verdict | Q3 (dB) / Verdict |
|---|---|---|---|
| U | -0.2103 [-0.5000, -0.0404] | -0.6077 [-1.1867, -0.2877] (HG_AHEAD) | 0.0693 [-0.4515, 0.5616] (Z_INCONCLUSIVE) |
| G | -0.3821 [-0.7212, -0.1529] | -0.6990 [-1.2222, -0.0678] (HG_AHEAD) | 0.0308 [-0.1639, 0.4007] (Z_EQUIVALENT) |

## Scene-Averaged 1% FER Crossings (dB, Point and 95% CI)

| ρ | F0 | CD | HG | HG1 | Z | HGint |
|---|---|---|---|---|---|---|
| 0.15 | [12.0000, +inf] [11.5816, +inf] | 9.0000 [7.8193, +inf] | 4.9539 [4.6845, 5.8066] | 8.4142 [7.0776, 9.6218] | 9.0000 [7.8193, +inf] | 6.1218 [4.9722, 6.8193] |
| 0.20 | 10.3691 [9.6131, +inf] | 6.3066 [5.4267, 6.9447] | 4.4462 [4.3224, 4.5923] | 5.6117 [5.1500, 6.4419] | 6.5293 [5.5000, 7.0242] | 4.5408 [4.4173, 4.6773] |
| 0.25 | 7.7192 [7.3331, 8.0063] | 5.1561 [4.9988, 5.3404] | 4.6297 [4.5032, 4.7500] | 5.1658 [4.9720, 5.3364] | 5.2293 [5.0625, 5.5772] | 4.7919 [4.6277, 4.9482] |
| 0.30 | 6.8066 [6.3109, 7.1845] | 5.0995 [4.9769, 5.3109] | 4.8033 [4.7425, 4.9120] | 5.1055 [4.9858, 5.3126] | 5.1495 [5.0197, 5.3357] | 4.8768 [4.7780, 4.9843] |
| 0.40 | 6.2386 [6.0818, 6.4599] | 5.5765 [5.4764, 5.7531] | 5.3888 [5.2964, 5.4906] | 5.5497 [5.4476, 5.7276] | 5.6211 [5.5039, 5.7767] | 5.4728 [5.3424, 5.5650] |
| 0.50 | 6.7319 [6.5864, 6.9017] | 6.2860 [6.2216, 6.4021] | 6.1272 [6.0242, 6.1751] | 6.2581 [6.2117, 6.3378] | 6.2870 [6.2228, 6.4027] | 6.1734 [6.0895, 6.2077] |

## Secondary Contrasts (95% Projected CI, dB)

| Contrast | Best-vs-Best Point / 95% Projected CI | Fixed ρ=0.30 Point / 95% CI |
|---|---|---|
| HG1_minus_HG | 0.6593 [0.2255, 0.9451] | 0.3022 [0.1780, 0.4598] |
| HG1_minus_CD | 0.0060 [-0.2928, 0.2940] | 0.0060 [-0.0015, 0.0288] |
| HG_minus_F0 | -1.7924 [-2.6100, -1.3240] | -2.0033 [-2.3633, -1.5104] |
| Z_minus_F0 | -1.0890 [-1.8682, -0.8029] | -1.6570 [-2.0099, -1.1814] |
| HGint_minus_HG | 0.0946 [-0.3182, 0.2704] | 0.0735 [-0.0486, 0.1640] |
| HGint_minus_CD | -0.5587 [-0.8494, -0.2677] | -0.2227 [-0.4013, -0.0981] |

## Paired Rescues & HG Pass-2 Diagnostics

- HG vs CD on 18009 triggers: CD_only=18, HG_only=1827, both=6026, neither=10138
- Z vs CD on 18009 triggers: CD_only=249, Z_only=93, both=5795, neither=11872
- HG pass-1 early stop: 6142/18009 (34.11%)
- HG pass-2 ran: 11867, rescued: 1704, FER harmed: 0, bit-improved: 7711, bit-worsened: 3405, still failed: 10156

## Support Recovery on Triggered Keys (1-to-1 Match: exact delay & |Δk| ≤ 0.5)

| Stage / Arm | Keys | Path Recall | Pooled Power Frac | Mean Power Frac | Median Power Frac |
|---|---:|---:|---:|---:|---:|
| HG1_omp | 18009 | 94.44% (136061/144072) | 99.73% | 99.73% | 100.00% |
| HG1_refined | 18009 | 87.38% (125896/144072) | 98.74% | 98.74% | 99.57% |
| HG_final_refined | 18009 | 89.03% (128266/144072) | 99.08% | 99.08% | 99.74% |
| HG_pass2_subset_p1_refined | 11867 | 84.61% (80326/94936) | 98.30% | 98.30% | 99.27% |
| HG_pass2_subset_p2_refined | 11867 | 87.11% (82696/94936) | 98.80% | 98.80% | 99.54% |
| CD_final_refined | 18009 | 87.43% (125966/144072) | 98.88% | 98.88% | 99.50% |
| Z_final_refined | 18009 | 85.62% (123350/144072) | 98.48% | 98.48% | 99.36% |

## Quiet Single-Core Per-Trigger Runtime Panel (ρ=0.30, 5.0 dB, 100 Triggered Keys)

- CPU pinned: `0` (util 0.0%), shared F0 median: `269.69 ms`

| Arm | Mean (ms) | Median (ms) | p95 (ms) | Ratio of Means vs CD | Median Paired Ratio vs CD |
|---|---:|---:|---:|---:|---:|
| CD | 159.01 | 158.76 | 166.28 | 1.000× | 1.000× |
| Z | 159.15 | 158.38 | 165.72 | 1.001× | 1.003× |
| HG | 571.62 | 523.49 | 1055.42 | 3.595× | 3.310× |
| HG1 | 524.24 | 523.48 | 535.48 | 3.297× | 3.295× |
| HGint | 188.61 | 168.34 | 341.46 | 1.186× | 1.066× |
