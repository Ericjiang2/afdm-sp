# DDST Stage 1 results

Protocol: `.trellis/tasks/10-08-doppler-cluster/research/ddst-small-run-protocol-20261014.md` (frozen). Analysis: `experiments/headroom_ladder_20261008/ddst_s1_analyze.py`.
Kc = FER_k = .5 crossing, linear in K = 8L; CI = percentile, paired frame bootstrap (B = 2000, seed 20261014, frames resampled jointly across L, arms and SNR groups); a crossing outside the L range is censored at the range edge and the ratio is "not assessable".

## Decision (mechanical)

**KILL**

- P1 (6.5 dB rho .3, R10, DDST-A/SPg_flat): 0.842 [0.807, 0.880], bar >= 1.1, CI lower bound > 1 needed, assessable True (exact/exact) -> fail
- P2 (8 dB rho .3, R10): 0.814 [0.789, 0.844], bar >= 1.05, assessable True (exact/exact) -> fail
- R1 primary (6.5 dB, DDST-A): 0.800 [0.733, 0.882], assessable False (below_range/exact), CI lower bound > 1: False

## 6.5 dB, rho .3 (primary)

| round | arm | Kc [95% CI] | status | ratio vs SPg_flat [95% CI] | ratio status |
|---|---|---|---|---|---|
| R1 | SPg_flat | 80.0 [72.5, 87.3] | exact | - | - |
| R1 | DDST-A | 64.0 [64.0, 64.0] | below_range | 0.800 [0.733, 0.882] | NOT ASSESSABLE (below_range/exact) |
| R1 | DDST-N | 64.0 [64.0, 64.0] | below_range | 0.800 [0.733, 0.882] | NOT ASSESSABLE (below_range/exact) |
| R1 | DDST-A-blind | 64.0 [64.0, 64.0] | below_range | 0.800 [0.733, 0.882] | NOT ASSESSABLE (below_range/exact) |
| R4 | SPg_flat | 170.3 [164.1, 175.2] | exact | - | - |
| R4 | DDST-A | 142.3 [136.8, 147.6] | exact | 0.836 [0.802, 0.867] | assessable (exact/exact) |
| R4 | DDST-N | 64.0 [64.0, 64.0] | below_range | 0.376 [0.365, 0.390] | NOT ASSESSABLE (below_range/exact) |
| R4 | DDST-A-blind | 138.7 [130.9, 144.9] | exact | 0.814 [0.766, 0.852] | assessable (exact/exact) |
| R10 | SPg_flat | 183.4 [178.7, 189.8] | exact | - | - |
| R10 | DDST-A | 154.5 [149.0, 161.4] | exact | 0.842 [0.807, 0.880] | assessable (exact/exact) |
| R10 | DDST-N | 64.0 [64.0, 64.0] | below_range | 0.349 [0.337, 0.359] | NOT ASSESSABLE (below_range/exact) |
| R10 | DDST-A-blind | 151.1 [145.4, 158.5] | exact | 0.824 [0.789, 0.863] | assessable (exact/exact) |

FER by L (frac ierr_k > 0):

| round | arm | L8 | L12 | L16 | L20 | L24 | L28 | L32 |
|---|---|---|---|---|---|---|---|---|
| R1 | SPg_flat | 0.385 | 0.615 | 0.910 | 0.995 | 1.000 | 1.000 | 1.000 |
| R1 | DDST-A | 0.580 | 0.805 | 0.980 | 1.000 | 1.000 | 1.000 | 1.000 |
| R1 | DDST-N | 0.965 | 0.965 | 0.995 | 1.000 | 1.000 | 1.000 | 1.000 |
| R1 | DDST-A-blind | 0.625 | 0.835 | 0.990 | 1.000 | 1.000 | 1.000 | 1.000 |
| R4 | SPg_flat | 0.150 | 0.105 | 0.170 | 0.400 | 0.710 | 0.890 | 0.995 |
| R4 | DDST-A | 0.165 | 0.215 | 0.370 | 0.660 | 0.945 | 0.990 | 1.000 |
| R4 | DDST-N | 0.815 | 0.620 | 0.720 | 0.915 | 0.995 | 1.000 | 1.000 |
| R4 | DDST-A-blind | 0.185 | 0.235 | 0.415 | 0.670 | 0.940 | 0.995 | 1.000 |
| R10 | SPg_flat | 0.110 | 0.070 | 0.110 | 0.255 | 0.590 | 0.780 | 0.970 |
| R10 | DDST-A | 0.140 | 0.160 | 0.260 | 0.550 | 0.865 | 0.965 | 1.000 |
| R10 | DDST-N | 0.780 | 0.580 | 0.625 | 0.840 | 0.975 | 1.000 | 1.000 |
| R10 | DDST-A-blind | 0.160 | 0.155 | 0.305 | 0.575 | 0.865 | 0.960 | 1.000 |

## 8 dB, rho .3 (replication)

| round | arm | Kc [95% CI] | status | ratio vs SPg_flat [95% CI] | ratio status |
|---|---|---|---|---|---|
| R1 | SPg_flat | 138.5 [132.5, 143.3] | exact | - | - |
| R1 | DDST-A | 128.0 [128.0, 128.0] | below_range | 0.924 [0.893, 0.966] | NOT ASSESSABLE (below_range/exact) |
| R1 | DDST-N | 128.0 [128.0, 128.0] | below_range | 0.924 [0.893, 0.966] | NOT ASSESSABLE (below_range/exact) |
| R1 | DDST-A-blind | 128.0 [128.0, 128.0] | below_range | 0.924 [0.893, 0.966] | NOT ASSESSABLE (below_range/exact) |
| R4 | SPg_flat | 235.9 [230.6, 240.3] | exact | - | - |
| R4 | DDST-A | 194.7 [188.9, 200.4] | exact | 0.825 [0.794, 0.858] | assessable (exact/exact) |
| R4 | DDST-N | 128.0 [128.0, 159.3] | below_range | 0.543 [0.533, 0.678] | NOT ASSESSABLE (below_range/exact) |
| R4 | DDST-A-blind | 192.6 [187.3, 198.9] | exact | 0.816 [0.788, 0.851] | assessable (exact/exact) |
| R10 | SPg_flat | 256.8 [250.2, 261.7] | exact | - | - |
| R10 | DDST-A | 209.1 [204.2, 214.5] | exact | 0.814 [0.789, 0.844] | assessable (exact/exact) |
| R10 | DDST-N | 147.6 [142.1, 153.8] | exact | 0.575 [0.551, 0.604] | assessable (exact/exact) |
| R10 | DDST-A-blind | 207.7 [203.2, 212.6] | exact | 0.809 [0.784, 0.837] | assessable (exact/exact) |

FER by L (frac ierr_k > 0):

| round | arm | L16 | L20 | L24 | L28 | L32 | L36 | L40 |
|---|---|---|---|---|---|---|---|---|
| R1 | SPg_flat | 0.400 | 0.705 | 0.970 | 1.000 | 1.000 | 1.000 | 1.000 |
| R1 | DDST-A | 0.805 | 0.950 | 0.995 | 1.000 | 1.000 | 1.000 | 1.000 |
| R1 | DDST-N | 0.990 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| R1 | DDST-A-blind | 0.835 | 0.960 | 0.995 | 1.000 | 1.000 | 1.000 | 1.000 |
| R4 | SPg_flat | 0.015 | 0.005 | 0.125 | 0.375 | 0.710 | 0.965 | 0.990 |
| R4 | DDST-A | 0.055 | 0.120 | 0.475 | 0.775 | 0.965 | 1.000 | 1.000 |
| R4 | DDST-N | 0.730 | 0.530 | 0.735 | 0.955 | 0.995 | 1.000 | 1.000 |
| R4 | DDST-A-blind | 0.070 | 0.140 | 0.495 | 0.780 | 0.970 | 1.000 | 1.000 |
| R10 | SPg_flat | 0.010 | 0.000 | 0.080 | 0.220 | 0.490 | 0.870 | 0.965 |
| R10 | DDST-A | 0.035 | 0.050 | 0.345 | 0.635 | 0.905 | 0.990 | 1.000 |
| R10 | DDST-N | 0.675 | 0.390 | 0.605 | 0.850 | 0.980 | 1.000 | 1.000 |
| R10 | DDST-A-blind | 0.035 | 0.070 | 0.345 | 0.660 | 0.930 | 0.995 | 1.000 |

## Report-only

### Measured R1 gain vs the zero-simulation bound

| cell | arm | measured R1 ratio [95% CI] | bound g_R | measured / bound | (ratio-1)/(g_R-1) |
|---|---|---|---|---|---|
| 6.5 dB | DDST-A | 0.800 [0.733, 0.882] | 1.390 | 0.575 | -0.512 |
| 6.5 dB | DDST-A-blind | 0.800 [0.733, 0.882] | 1.323 | 0.605 | -0.620 |
| 8 dB | DDST-A | 0.924 [0.893, 0.966] | 1.383 | 0.668 | -0.198 |
| 8 dB | DDST-A-blind | 0.924 [0.893, 0.966] | 1.377 | 0.671 | -0.201 |

### Realised data power (ratio to nominal) and PAPR

| cell | arm | data power mean [min, max] | PAPR mean / p95 / max dB | peak power max | gate pass |
|---|---|---|---|---|---|
| 6.5 dB | SPg_flat | 1.0000 [1.0000, 1.0000] | 8.45 / 9.66 / 10.69 | 11.98 | 1.000 |
| 6.5 dB | DDST-A | 0.9997 [0.9563, 1.0471] | 8.74 / 10.02 / 11.52 | 13.99 | 1.000 |
| 6.5 dB | DDST-N | 0.9997 [0.9563, 1.0471] | 8.74 / 10.02 / 11.52 | 13.99 | 1.000 |
| 6.5 dB | DDST-A-blind | 0.9995 [0.9540, 1.0460] | 8.80 / 10.05 / 11.17 | 12.95 | 1.000 |
| 8 dB | SPg_flat | 1.0000 [1.0000, 1.0000] | 8.45 / 9.66 / 10.69 | 11.98 | 1.000 |
| 8 dB | DDST-A | 0.9997 [0.9534, 1.0481] | 8.82 / 10.07 / 11.32 | 13.39 | 1.000 |
| 8 dB | DDST-N | 0.9997 [0.9534, 1.0481] | 8.82 / 10.07 / 11.32 | 13.39 | 1.000 |
| 8 dB | DDST-A-blind | 0.9997 [0.9525, 1.0484] | 8.84 / 10.13 / 11.24 | 13.13 | 1.000 |

Receiver wall-seconds in the run (sum of row seconds, pause outliers excluded; the shards ran 20-40 concurrently, so these are contended times): 37148 (10.32 core-hours); Tx side (M + eigh, once per frame and L): 5119 s.

### Receiver seconds, 6.5 dB (mean per frame; in brackets: mean per round over rounds 2-10 / round 1)

| arm | L8 | L12 | L16 | L20 | L24 | L28 | L32 |
|---|---|---|---|---|---|---|---|
| SPg_flat | 1.27 (0.11/0.28) | 1.72 (0.16/0.33) | 2.29 (0.21/0.39) | 2.81 (0.26/0.44) | 3.04 (0.29/0.44) | 3.56 (0.34/0.49) | 4.27 (0.41/0.56) |
| DDST-A | 1.59 (0.14/0.30) | 1.99 (0.18/0.34) | 2.53 (0.24/0.40) | 3.09 (0.29/0.45) | 3.33 (0.32/0.46) | 3.87 (0.37/0.51) | 4.63 (0.45/0.59) |
| DDST-N | 1.29 (0.11/0.26) | 1.71 (0.16/0.31) | 2.25 (0.21/0.36) | 2.66 (0.25/0.40) | 2.98 (0.28/0.42) | 3.50 (0.34/0.47) | 4.18 (0.40/0.54) |
| DDST-A-blind | 1.62 (0.15/0.30) | 2.03 (0.19/0.34) | 2.55 (0.24/0.39) | 2.94 (0.28/0.43) | 3.31 (0.32/0.45) | 3.86 (0.37/0.51) | 4.58 (0.44/0.58) |

### Receiver seconds, 8 dB (mean per frame; in brackets: mean per round over rounds 2-10 / round 1)

| arm | L16 | L20 | L24 | L28 | L32 | L36 | L40 |
|---|---|---|---|---|---|---|---|
| SPg_flat | 2.18 (0.20/0.36) | 2.48 (0.23/0.39) | 2.92 (0.28/0.42) | 3.45 (0.33/0.47) | 4.15 (0.40/0.55) | 4.76 (0.46/0.62) | 5.34 (0.52/0.67) |
| DDST-A | 2.59 (0.24/0.40) | 2.77 (0.26/0.41) | 3.28 (0.31/0.45) | 3.86 (0.37/0.51) | 4.59 (0.44/0.59) | 5.11 (0.50/0.64) | 5.67 (0.55/0.70) |
| DDST-N | 2.26 (0.21/0.36) | 2.44 (0.23/0.37) | 2.97 (0.28/0.42) | 3.51 (0.34/0.47) | 4.20 (0.41/0.55) | 4.68 (0.45/0.60) | 5.15 (0.50/0.64) |
| DDST-A-blind | 2.69 (0.25/0.41) | 2.80 (0.27/0.40) | 3.34 (0.32/0.46) | 3.92 (0.38/0.51) | 4.70 (0.46/0.59) | 5.18 (0.50/0.64) | 5.53 (0.54/0.68) |

### Rank and receiver s2 factor

| cell | L | r genie | r blind | mean phi genie | mean phi blind |
|---|---|---|---|---|---|
| 6.5 dB | 8 | 144 | 136 | 0.395 | 0.527 |
| 6.5 dB | 12 | 120 | 120 | 0.528 | 0.572 |
| 6.5 dB | 16 | 112 | 128 | 0.573 | 0.570 |
| 6.5 dB | 20 | 136 | 136 | 0.555 | 0.567 |
| 6.5 dB | 24 | 152 | 144 | 0.547 | 0.563 |
| 6.5 dB | 28 | 168 | 160 | 0.540 | 0.553 |
| 6.5 dB | 32 | 192 | 176 | 0.526 | 0.544 |
| 8 dB | 16 | 168 | 168 | 0.504 | 0.533 |
| 8 dB | 20 | 144 | 144 | 0.546 | 0.559 |
| 8 dB | 24 | 144 | 136 | 0.555 | 0.571 |
| 8 dB | 28 | 160 | 152 | 0.546 | 0.560 |
| 8 dB | 32 | 176 | 168 | 0.538 | 0.549 |
| 8 dB | 36 | 192 | 184 | 0.529 | 0.540 |
| 8 dB | 40 | 208 | 200 | 0.522 | 0.531 |

### Round-1 diagnostics, 6.5 dB (mean over frames: eps_ce1 / ll_in1)

| arm | L8 | L12 | L16 | L20 | L24 | L28 | L32 |
|---|---|---|---|---|---|---|---|
| SPg_flat | 0.160 / 0.400 | 0.231 / 0.444 | 0.282 / 0.496 | 0.338 / 0.537 | 0.369 / 0.589 | 0.411 / 0.625 | 0.441 / 0.664 |
| DDST-A | 0.115 / 0.440 | 0.201 / 0.477 | 0.260 / 0.528 | 0.313 / 0.574 | 0.347 / 0.628 | 0.387 / 0.664 | 0.417 / 0.702 |
| DDST-N | 0.117 / 0.525 | 0.200 / 0.524 | 0.257 / 0.555 | 0.310 / 0.598 | 0.342 / 0.645 | 0.382 / 0.680 | 0.410 / 0.717 |
| DDST-A-blind | 0.138 / 0.455 | 0.209 / 0.485 | 0.260 / 0.537 | 0.316 / 0.577 | 0.350 / 0.629 | 0.391 / 0.666 | 0.421 / 0.706 |

### Round-1 diagnostics, 8 dB (mean over frames: eps_ce1 / ll_in1)

| arm | L16 | L20 | L24 | L28 | L32 | L36 | L40 |
|---|---|---|---|---|---|---|---|
| SPg_flat | 0.268 / 0.401 | 0.323 / 0.452 | 0.353 / 0.514 | 0.394 / 0.560 | 0.424 / 0.606 | 0.455 / 0.645 | 0.478 / 0.674 |
| DDST-A | 0.232 / 0.465 | 0.295 / 0.505 | 0.331 / 0.565 | 0.371 / 0.609 | 0.402 / 0.722 | 0.433 / 0.693 | 0.456 / 0.722 |
| DDST-N | 0.230 / 0.527 | 0.291 / 0.539 | 0.326 / 0.583 | 0.364 / 0.627 | 0.394 / 0.667 | 0.425 / 0.703 | 0.447 / 0.730 |
| DDST-A-blind | 0.240 / 0.477 | 0.299 / 0.510 | 0.334 / 0.564 | 0.374 / 0.611 | 0.404 / 0.657 | 0.438 / 0.697 | 0.458 / 0.725 |

