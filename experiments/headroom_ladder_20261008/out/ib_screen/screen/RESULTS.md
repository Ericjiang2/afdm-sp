# Information-budget screen: results

Spec `.trellis/tasks/10-08-doppler-cluster/research/info-budget-screen-20261014.md` (frozen a34777b6). tau = 1 bit/QPSK symbol, alpha = 0.05, 480 endpoints, delta per endpoint 1.042e-04 (split in three over A, f, J).

## Labels (section 6)

- **MODEL: UNINFORMATIVE**; H_low = -, -, -, -, -
- **PHYS: UNINFORMATIVE**; H_low = -, -, 0.13, -, -

## MODEL: K* per condition

| condition | locate passes m | confirm L | K* (L) | status | Kc_best | H_low | LCB/N at confirm L | tau 1.154 side table K* |
|---|---|---|---|---|---|---|---|---|
| 6.5|0.2 | 0 | [4, 8] | None (None) | none | 201.0 | - | L4:0.618, L8:0.490 | None |
| 6.5|0.3 | 0 | [4, 8] | None (None) | none | 213.6 | - | L4:0.535, L8:0.422 | None |
| 8|0.2 | 0 | [4, 8] | None (None) | none | 254.2 | - | L4:0.743, L8:0.602 | None |
| 8|0.3 | 0 | [4, 8] | None (None) | none | 269.3 | - | L4:0.666, L8:0.541 | None |
| 8|0.5 | 0 | [4, 8] | None (None) | none | 222.9 | - | L4:0.477, L8:0.380 | None |

## PHYS: K* per condition

| condition | locate passes m | confirm L | K* (L) | status | Kc_best | H_low | LCB/N at confirm L | tau 1.154 side table K* |
|---|---|---|---|---|---|---|---|---|
| 6.5|0.2 | 0 | [4, 8] | None (None) | none | 201.0 | - | L4:0.893, L8:0.791 | None |
| 6.5|0.3 | 0 | [4, 8] | None (None) | none | 213.6 | - | L4:0.813, L8:0.723 | None |
| 8|0.2 | 0 | [4, 8] | 32 (4) | exact | 254.2 | 0.13 | L4:1.025, L8:0.915 | None |
| 8|0.3 | 0 | [4, 8] | None (None) | none | 269.3 | - | L4:0.952, L8:0.853 | None |
| 8|0.5 | 0 | [4, 8] | None (None) | none | 222.9 | - | L4:0.765, L8:0.686 | None |

## REPORT-ONLY (outside the decision): point-estimate crossing of mean LB/N = 1

Mean LB/N per frame set with a plain normal 95% CI over the 64 locate frames; K = 8L where the mean first drops below 1 (linear in L); in brackets the same for the lower / upper CI curve. Consistency of the report-only run with the decision locate run (A, f, J of the 5 conditions identical): True.

### LB_MODEL

| condition | crossing K [lower-CI curve, upper-CI curve] | status | Kc_best | K / Kc_best | mean LB/N at L = 4, 8, 16, 24, 32, 48, 96 |
|---|---|---|---|---|---|
| 6.5|0.2 | 61 [55, 66] | exact | 201.0 | 0.30 | 1.118, 0.986, 0.759, 0.585, 0.427, 0.179, -0.277 |
| 6.5|0.3 | 49 [43, 56] | exact | 213.6 | 0.23 | 1.063, 0.947, 0.742, 0.584, 0.437, 0.206, -0.231 |
| 8|0.2 | 99 [95, 102] | exact | 254.2 | 0.39 | 1.285, 1.141, 0.888, 0.686, 0.501, 0.205, -0.360 |
| 8|0.3 | 94 [90, 98] | exact | 269.3 | 0.35 | 1.239, 1.111, 0.881, 0.696, 0.524, 0.245, -0.298 |
| 8|0.5 | 60 [53, 67] | exact | 222.9 | 0.27 | 1.088, 0.988, 0.803, 0.657, 0.514, 0.279, -0.197 |
| 9.5|0.3 | 126 [123, 129] | exact | - | - | 1.390, 1.248, 0.993, 0.780, 0.582, 0.252, -0.410 |

### GMI_LB_MODEL

| condition | crossing K [lower-CI curve, upper-CI curve] | status | Kc_best | K / Kc_best | mean LB/N at L = 4, 8, 16, 24, 32, 48, 96 |
|---|---|---|---|---|---|
| 6.5|0.2 | 65 [59, 71] | exact | 201.0 | 0.33 | 1.127, 1.005, 0.787, 0.602, 0.445, 0.199, -0.253 |
| 6.5|0.3 | 58 [50, 64] | exact | 213.6 | 0.27 | 1.084, 0.979, 0.783, 0.615, 0.469, 0.238, -0.193 |
| 8|0.2 | 98 [94, 102] | exact | 254.2 | 0.38 | 1.270, 1.135, 0.890, 0.677, 0.491, 0.198, -0.363 |
| 8|0.3 | 95 [91, 100] | exact | 269.3 | 0.35 | 1.232, 1.112, 0.892, 0.696, 0.523, 0.247, -0.292 |
| 8|0.5 | 71 [63, 78] | exact | 222.9 | 0.32 | 1.108, 1.018, 0.844, 0.686, 0.545, 0.311, -0.160 |
| 9.5|0.3 | 124 [120, 128] | exact | - | - | 1.367, 1.234, 0.986, 0.763, 0.561, 0.236, -0.423 |

### LB_PHYS

| condition | crossing K [lower-CI curve, upper-CI curve] | status | Kc_best | K / Kc_best | mean LB/N at L = 4, 8, 16, 24, 32, 48, 96 |
|---|---|---|---|---|---|
| 6.5|0.2 | 107 [96, 117] | exact | 201.0 | 0.53 | 1.213, 1.097, 0.962, 0.817, 0.693, 0.484, 0.042 |
| 6.5|0.3 | 87 [76, 96] | exact | 213.6 | 0.41 | 1.154, 1.047, 0.931, 0.801, 0.687, 0.495, 0.078 |
| 8|0.2 | 165 [160, 170] | exact | 254.2 | 0.65 | 1.379, 1.256, 1.098, 0.934, 0.792, 0.548, 0.015 |
| 8|0.3 | 160 [155, 166] | exact | 269.3 | 0.60 | 1.329, 1.217, 1.079, 0.930, 0.799, 0.573, 0.067 |
| 8|0.5 | 110 [96, 124] | exact | 222.9 | 0.49 | 1.173, 1.077, 0.977, 0.857, 0.751, 0.564, 0.133 |
| 9.5|0.3 | 202 [198, 205] | exact | - | - | 1.475, 1.357, 1.194, 1.026, 0.877, 0.613, 0.011 |

### GMI_LB_PHYS

| condition | crossing K [lower-CI curve, upper-CI curve] | status | Kc_best | K / Kc_best | mean LB/N at L = 4, 8, 16, 24, 32, 48, 96 |
|---|---|---|---|---|---|
| 6.5|0.2 | 117 [106, 128] | exact | 201.0 | 0.58 | 1.225, 1.115, 0.982, 0.836, 0.712, 0.507, 0.061 |
| 6.5|0.3 | 102 [91, 115] | exact | 213.6 | 0.48 | 1.175, 1.077, 0.964, 0.832, 0.718, 0.529, 0.109 |
| 8|0.2 | 166 [160, 171] | exact | 254.2 | 0.65 | 1.372, 1.251, 1.097, 0.932, 0.790, 0.548, 0.011 |
| 8|0.3 | 164 [158, 170] | exact | 269.3 | 0.61 | 1.328, 1.219, 1.085, 0.934, 0.804, 0.580, 0.071 |
| 8|0.5 | 133 [120, 142] | exact | 222.9 | 0.60 | 1.193, 1.106, 1.009, 0.887, 0.781, 0.598, 0.163 |
| 9.5|0.3 | 198 [194, 203] | exact | - | - | 1.464, 1.345, 1.187, 1.019, 0.870, 0.608, 0.002 |

### RAY

| condition | crossing K [lower-CI curve, upper-CI curve] | status | Kc_best | K / Kc_best | mean LB/N at L = 4, 8, 16, 24, 32, 48, 96 |
|---|---|---|---|---|---|
| 6.5|0.2 | 69 [59, 78] | exact | 201.0 | 0.34 | 1.150, 1.017, 0.818, 0.647, 0.518, 0.264, -0.315 |
| 6.5|0.3 | 51 [40, 60] | exact | 213.6 | 0.24 | 1.078, 0.945, 0.748, 0.579, 0.452, 0.200, -0.374 |
| 8|0.2 | 111 [103, 119] | exact | 254.2 | 0.44 | 1.316, 1.171, 0.949, 0.758, 0.607, 0.313, -0.374 |
| 8|0.3 | 92 [85, 100] | exact | 269.3 | 0.34 | 1.252, 1.109, 0.890, 0.700, 0.551, 0.260, -0.421 |
| 8|0.5 | 49 [39, 57] | exact | 222.9 | 0.22 | 1.073, 0.932, 0.717, 0.531, 0.387, 0.102, -0.563 |
| 9.5|0.3 | 128 [123, 134] | exact | - | - | 1.399, 1.244, 1.001, 0.790, 0.617, 0.285, -0.509 |

