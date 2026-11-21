# SBL spectral split, Phase 2

## Observation

1,200 paired keys in 100 physical-frame clusters. 95% percentile intervals use 20,000 paired cluster draws with seed 20261119. The 100-iteration R0/R1/R2 outcomes are joined from verified E-3c rows. The receiver receipt records 12.07 core-hours.

| Arm | Frame errors | FER [95% CI] |
|---|---:|---:|
| R0 | 39 | 0.03250 [0.02083, 0.04583] |
| R1 | 189 | 0.15750 [0.13250, 0.18333] |
| R2 | 51 | 0.04250 [0.03000, 0.05583] |
| S0 | 74 | 0.06167 [0.04417, 0.08083] |
| T0 | 206 | 0.17167 [0.14917, 0.19583] |
| S-lo | 67 | 0.05583 [0.04000, 0.07417] |
| S-hi | 191 | 0.15917 [0.13500, 0.18417] |
| S-isolo | 82 | 0.06833 [0.05167, 0.08583] |
| S-isohi | 128 | 0.10667 [0.08583, 0.12833] |

| Contrast | Estimate [95% CI] |
|---|---:|
| G | 0.11500 [0.09750, 0.13333] |
| s | 0.83333 [0.76471, 0.89922] |
| t | -0.12319 [-0.23664, -0.02649] |
| I | 0.28986 [0.17361, 0.42424] |
| G_s | 0.09583 [0.08000, 0.11250] |
| f_lo | 1.06087 [1.01613, 1.11429] |
| f_hi | -0.01739 [-0.08036, 0.04032] |
| f_isolo | 0.93043 [0.86325, 1.00000] |
| f_isohi | 0.53043 [0.42148, 0.63964] |
| delta_lo | 0.01250 [0.00583, 0.02000] |
| delta_hi | -0.05250 [-0.06583, -0.04000] |

Eigenvalues in [.25, .75] account for 41,285/762,355 (5.42%) across the initial candidate sets.

### Receiver diagnostics, 100 iterations

| Arm | Mean β | Mean iterations | Converged | Mean EM-end atoms | Mean output atoms | Mean co-delay pairs | Mean EM added trace | Mean refinement added trace | Mean NMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R0 | 5.69901 | 95.5567 | 461 | 635.296 | 23.7333 | 28.8775 | 0 | 0 | 0.0376788 |
| R1 | 4.55918 | 99.2875 | 99 | 635.296 | 22.4933 | 5.2225 | 0 | 0 | 0.0759469 |
| R2 | 4.07297 | 99.9517 | 9 | 635.296 | 23.7317 | 23.1983 | 62359.2 | 2363.21 | 0.0620624 |
| S0 | 4.07297 | 99.9517 | 9 | 635.296 | 23.7317 | 23.1983 | 62359.2 | 0 | 0.0590574 |
| T0 | 4.55918 | 99.2875 | 99 | 635.296 | 22.4933 | 5.2225 | 0 | 2271.95 | 0.0922757 |
| S-lo | 4.3585 | 99.885 | 38 | 635.296 | 23.7317 | 24.3792 | 42159.9 | 0 | 0.0581577 |
| S-hi | 4.24135 | 99.4583 | 72 | 635.296 | 22.2017 | 5.14917 | 20199.3 | 0 | 0.0755524 |
| S-isolo | 4.18272 | 99.9558 | 10 | 635.296 | 23.7283 | 20.0008 | 42159.9 | 0 | 0.0617965 |
| S-isohi | 4.36222 | 99.9475 | 6 | 635.296 | 23.6858 | 13.335 | 20199.3 | 0 | 0.0689865 |

### Per-cell FER, 100 iterations

| Scenario / SNR (dB) | R0 | R1 | R2 | S0 | T0 | S-lo | S-hi | S-isolo | S-isohi |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G/6 | 0.130 | 0.680 | 0.210 | 0.260 | 0.740 | 0.260 | 0.700 | 0.290 | 0.460 |
| G/7 | 0.010 | 0.120 | 0.020 | 0.040 | 0.180 | 0.030 | 0.110 | 0.050 | 0.060 |
| G/8 | 0.020 | 0.050 | 0.000 | 0.030 | 0.040 | 0.030 | 0.070 | 0.030 | 0.050 |
| G/9 | 0.000 | 0.020 | 0.000 | 0.000 | 0.010 | 0.000 | 0.040 | 0.000 | 0.020 |
| G/10 | 0.000 | 0.030 | 0.000 | 0.000 | 0.020 | 0.000 | 0.020 | 0.000 | 0.010 |
| G/11 | 0.000 | 0.010 | 0.000 | 0.000 | 0.010 | 0.000 | 0.000 | 0.000 | 0.000 |
| U/6 | 0.170 | 0.610 | 0.240 | 0.290 | 0.710 | 0.250 | 0.620 | 0.350 | 0.480 |
| U/7 | 0.040 | 0.190 | 0.030 | 0.040 | 0.250 | 0.040 | 0.190 | 0.050 | 0.110 |
| U/8 | 0.020 | 0.080 | 0.010 | 0.060 | 0.050 | 0.050 | 0.070 | 0.040 | 0.050 |
| U/9 | 0.000 | 0.030 | 0.000 | 0.000 | 0.020 | 0.000 | 0.020 | 0.000 | 0.010 |
| U/10 | 0.000 | 0.040 | 0.000 | 0.000 | 0.020 | 0.000 | 0.040 | 0.000 | 0.010 |
| U/11 | 0.000 | 0.030 | 0.000 | 0.020 | 0.010 | 0.010 | 0.030 | 0.010 | 0.020 |

### 400-iteration subset

Frames 4000–4049 contribute 600 keys in 50 clusters. The 100-iteration column uses the same keys. Differences are 400 minus 100.

| Arm | 100-iteration FER [95% CI] | 400-iteration FER [95% CI] | Difference [95% CI] |
|---|---:|---:|---:|
| R1 | 0.14833 [0.11833, 0.18000] | 0.15000 [0.12000, 0.18167] | 0.00167 [-0.00333, 0.00667] |
| S0 | 0.04667 [0.03000, 0.06667] | 0.04833 [0.03167, 0.06833] | 0.00167 [0.00000, 0.00500] |
| S-lo | 0.04000 [0.02333, 0.06000] | 0.04167 [0.02333, 0.06333] | 0.00167 [0.00000, 0.00500] |
| S-hi | 0.14667 [0.11833, 0.17667] | 0.14667 [0.11667, 0.17833] | 0.00000 [-0.00833, 0.00833] |

| Arm | Mean β | Mean iterations | Converged | Mean EM-end atoms | Mean output atoms | Mean co-delay pairs | Mean EM added trace | Mean refinement added trace | Mean NMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R1 | 4.72676 | 168.232 | 593 | 636.445 | 22.4567 | 5.40833 | 0 | 0 | 0.0734195 |
| S0 | 4.24085 | 140.597 | 599 | 636.542 | 23.6117 | 22.8517 | 60723.1 | 0 | 0.0573835 |
| S-lo | 4.52355 | 135.063 | 599 | 636.542 | 23.6133 | 24.0167 | 41057.4 | 0 | 0.0564934 |
| S-hi | 4.41186 | 168.143 | 590 | 636.445 | 22.215 | 5.35167 | 19665.8 | 0 | 0.0730449 |

## Frozen verdicts

§7 governs the 100-iteration classifications. Ratio intervals use positive-denominator draws. A nonpositive point denominator or more than 1% nonpositive draws makes a ratio unevaluable.

| Test | Verdict |
|---|---|
| Stage | SBL |
| Low half | Carries recovery |
| High half | Insufficient alone |
| Δ_lo | Projector shape superior |
| Δ_hi | Isotropic shape superior |
| Candidate | Intervention-level support |

### Claude’s §7.4 prediction score

| Candidate outcome | Forecast | Observed |
|---|---:|---:|
| Intervention-level support | 25% | 1 |
| Low-half-only account does not hold | 35% | 0 |
| Not established | 40% | 0 |

Multiclass Brier score (sum of squared errors) 0.8450. Natural-log loss 1.3863.
