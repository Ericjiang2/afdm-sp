# M2 test table (expected-power law; B=20000 paired bootstrap over frames; frames 0..999 x SNR 6..11 dB x 5 configs)

rows 216000, error rows 0, results.json cross-check mismatching cells 0/216.

## Pre-registered S1-S4 (FER target 1e-1; point estimate decides, CI in brackets)

| id | rule | config | value (dB) [95% CI] | point | strict (CI) | verdict |
|---|---|---|---|---|---|---|
| S1 | x(M_adapt)-x(A3) <= 0.3 dB @1e-1 on N4b and J4 | N4b | 0.29 [0.21, 0.39] | PASS | no |  |
| S1 | x(M_adapt)-x(A3) <= 0.3 dB @1e-1 on N4b and J4 | J4 | 0.53 [0.43, 0.62] | FAIL | no | FAIL |
| S2 | x(M_adapt)-x(B) <= 0.1 dB @1e-1 on D1 | D1 | 0.17 [0.09, 0.25] | FAIL | no | FAIL |
| S3 | x(PS)-x(M_adapt) >= 0.3 dB @1e-1 on N4b and J4, and mean s/cell M_adapt <= PS | N4b | 0.29 [0.16, 0.42]; s/cell M_adapt 0.741 vs PS 1.632 | FAIL | no |  |
| S3 | x(PS)-x(M_adapt) >= 0.3 dB @1e-1 on N4b and J4, and mean s/cell M_adapt <= PS | J4 | 2.36 [1.82, 2.64]*; s/cell M_adapt 0.745 vs PS 1.672 | PASS | yes | FAIL |
| S4 | x(M_full)-x(M_adapt) >= 0.1 dB @1e-1 on D1 or N4a | D1 | 0.01 [0.00, 0.02] | FAIL | no |  |
| S4 | x(M_full)-x(M_adapt) >= 0.1 dB @1e-1 on D1 or N4a | N4a | 0.05 [0.01, 0.12] | FAIL | no | FAIL |

## Gap to A3 at FER 1e-1 (dB, x(arm)-x(A3), CI); bound when the arm never reaches 1e-1 by 11 dB

| config | B | PS | M_full | M_adapt | PB16 (7/9/11 grid, own crossing) |
|---|---|---|---|---|---|
| D1 | 0.24 [0.16, 0.34] | 0.27 [0.18, 0.37] | 0.41 [0.31, 0.53] | 0.41 [0.30, 0.53] | - |
| N4a | 0.71 [0.54, 0.89] | 0.58 [0.44, 0.75] | 0.46 [0.32, 0.64] | 0.41 [0.28, 0.57] | - |
| N4b | diff > 2.50 dB (B never reaches 0.1 by 11 dB) | 0.58 [0.45, 0.71] | 0.36 [0.27, 0.47] | 0.29 [0.21, 0.39] | 0.80 [0.65, 0.93] |
| J4 | diff > 3.15 dB (B never reaches 0.1 by 11 dB) | 2.89 [2.34, 3.18]* | 0.46 [0.36, 0.55] | 0.53 [0.43, 0.62] | 0.58 [0.44, 0.73] |
| J8 | diff > 3.48 dB (B never reaches 0.1 by 11 dB) | diff > 3.48 dB (PS never reaches 0.1 by 11 dB) | 0.46 [0.36, 0.54] | 0.54 [0.45, 0.62] | - |

## Gap to A3 at FER 1e-2 (only where defined; most arms do not reach 1e-2 by 11 dB, bounds given)

| config | B | PS | M_full | M_adapt |
|---|---|---|---|---|
| D1 | undefined: FER>target at all SNR / FER>target at all SNR | undefined: FER>target at all SNR / FER>target at all SNR | undefined: FER>target at all SNR / FER>target at all SNR | undefined: FER>target at all SNR / FER>target at all SNR |
| N4a | undefined: FER>target at all SNR / FER>target at all SNR | undefined: FER>target at all SNR / FER>target at all SNR | undefined: FER>target at all SNR / FER>target at all SNR | undefined: FER>target at all SNR / FER>target at all SNR |
| N4b | diff > 0.34 dB (B never reaches 0.01 by 11 dB) | diff > 0.34 dB (PS never reaches 0.01 by 11 dB) | diff > 0.34 dB (M_full never reaches 0.01 by 11 dB) | diff > 0.34 dB (M_adapt never reaches 0.01 by 11 dB) |
| J4 | diff > 1.39 dB (B never reaches 0.01 by 11 dB) | diff > 1.39 dB (PS never reaches 0.01 by 11 dB) | 0.33 [0.10, 0.57] | 0.39 [0.17, 0.66] |
| J8 | diff > 2.00 dB (B never reaches 0.01 by 11 dB) | diff > 2.00 dB (PS never reaches 0.01 by 11 dB) | 0.68 [0.39, 0.96] | 0.90 [0.64, 1.00] |

## FER at 7 / 9 / 11 dB (errors per 1000 frames)

| config | SNR | B | PS | M_full | M_adapt | A3 | PB16 |
|---|---|---|---|---|---|---|---|
| D1 | 7 | 359 (0.359) | 357 (0.357) | 390 (0.390) | 381 (0.381) | 329 (0.329) | - |
| D1 | 9 | 141 (0.141) | 144 (0.144) | 158 (0.158) | 156 (0.156) | 123 (0.123) | - |
| D1 | 11 | 42 (0.042) | 42 (0.042) | 45 (0.045) | 44 (0.044) | 37 (0.037) | - |
| N4a | 7 | 382 (0.382) | 365 (0.365) | 371 (0.371) | 362 (0.362) | 314 (0.314) | - |
| N4a | 9 | 149 (0.149) | 142 (0.142) | 132 (0.132) | 131 (0.131) | 110 (0.110) | - |
| N4a | 11 | 54 (0.054) | 52 (0.052) | 45 (0.045) | 45 (0.045) | 35 (0.035) | - |
| N4b | 7 | 594 (0.594) | 364 (0.364) | 352 (0.352) | 341 (0.341) | 291 (0.291) | 393 (0.393) |
| N4b | 9 | 395 (0.395) | 106 (0.106) | 90 (0.090) | 85 (0.085) | 66 (0.066) | 122 (0.122) |
| N4b | 11 | 272 (0.272) | 22 (0.022) | 15 (0.015) | 14 (0.014) | 6 (0.006) | 32 (0.032) |
| J4 | 7 | 911 (0.911) | 483 (0.483) | 297 (0.297) | 317 (0.317) | 236 (0.236) | 337 (0.337) |
| J4 | 9 | 864 (0.864) | 189 (0.189) | 47 (0.047) | 51 (0.051) | 22 (0.022) | 62 (0.062) |
| J4 | 11 | 822 (0.822) | 92 (0.092) | 2 (0.002) | 3 (0.003) | 1 (0.001) | 6 (0.006) |
| J8 | 7 | 995 (0.995) | 767 (0.767) | 274 (0.274) | 301 (0.301) | 184 (0.184) | - |
| J8 | 9 | 988 (0.988) | 573 (0.573) | 21 (0.021) | 25 (0.025) | 10 (0.010) | - |
| J8 | 11 | 977 (0.977) | 431 (0.431) | 1 (0.001) | 1 (0.001) | 0 (0.000) | - |

## Paired M_adapt vs comparator, all SNR cells pooled (rescues = comparator fails & M_adapt ok; harms = reverse; exact McNemar)

| config | comparator | rescues | harms | McNemar p | dLogloss (M_adapt - cmp) [CI] |
|---|---|---|---|---|---|
| D1 | B | 1 | 87 | 5.75e-25 | 0.0011 [0.0007, 0.0016] |
| D1 | PS | 0 | 81 | 8.27e-25 | 0.0009 [0.0004, 0.0014] |
| D1 | M_full | 28 | 0 | 7.45e-09 | -0.0040 [-0.0042, -0.0039] |
| N4a | B | 120 | 30 | 5.97e-14 | -0.0323 [-0.0355, -0.0294] |
| N4a | PS | 72 | 34 | 2.85e-04 | -0.0164 [-0.0180, -0.0149] |
| N4a | M_full | 32 | 1 | 7.92e-09 | -0.0039 [-0.0041, -0.0037] |
| N4b | B | 1604 | 2 | 0.00e+00 | -0.2281 [-0.2387, -0.2167] |
| N4b | PS | 142 | 26 | 1.51e-20 | -0.0313 [-0.0339, -0.0288] |
| N4b | M_full | 48 | 2 | 2.27e-12 | -0.0036 [-0.0037, -0.0034] |
| N4b | PB16 | 111 | 4 | 3.45e-28 | -0.0382 [-0.0413, -0.0354] |
| J4 | B | 4189 | 0 | 0.00e+00 | -0.5986 [-0.6190, -0.5783] |
| J4 | PS | 798 | 32 | 1.55e-192 | -0.1092 [-0.1183, -0.1006] |
| J4 | M_full | 8 | 62 | 1.83e-11 | 0.0095 [0.0084, 0.0106] |
| J4 | PB16 | 51 | 17 | 4.45e-05 | -0.0255 [-0.0282, -0.0229] |
| J8 | B | 4908 | 0 | 0.00e+00 | -0.8972 [-0.9187, -0.8764] |
| J8 | PS | 2763 | 2 | 0.00e+00 | -0.3518 [-0.3661, -0.3362] |
| J8 | M_full | 7 | 95 | 7.85e-21 | 0.0124 [0.0113, 0.0134] |

## Cost: complete receiver seconds/cell (mean / p95), all SNR cells pooled, shared load (80+20 single-thread shards)

| config | B | PS | M_full | M_adapt | A3 | PB16 |
|---|---|---|---|---|---|---|
| D1 | 0.806 / 1.493 | 1.593 / 2.511 | 0.767 / 1.050 | 0.753 / 1.026 | 0.460 / 0.624 | - |
| N4a | 0.824 / 1.517 | 1.612 / 2.563 | 0.763 / 1.047 | 0.751 / 1.027 | 0.515 / 0.714 | - |
| N4b | 1.000 / 1.582 | 1.632 / 2.624 | 0.753 / 1.040 | 0.741 / 1.021 | 0.507 / 0.710 | 5.634 / 8.389 |
| J4 | 1.120 / 1.591 | 1.672 / 2.644 | 0.749 / 1.046 | 0.745 / 1.034 | 0.503 / 0.706 | 5.565 / 8.347 |
| J8 | 1.126 / 1.600 | 1.813 / 2.699 | 0.736 / 1.035 | 0.737 / 1.035 | 0.567 / 0.807 | - |

## PB16 (cap 16, no stopping rule) like-for-like on the 3-point grid {7, 9, 11} dB, gap to A3 at 1e-1

| config | B | PS | M_full | M_adapt | PB16 | PB16 - PS | PB16 - M_adapt |
|---|---|---|---|---|---|---|---|
| N4b | diff > 2.56 dB (B never reaches 0.1 by 11 dB) | 0.63 [0.47, 0.78] | 0.41 [0.28, 0.54] | 0.33 [0.21, 0.46] | 0.86 [0.69, 1.01] | 0.22 [0.11, 0.35] | 0.53 [0.37, 0.69] |
| J4 | diff > 3.28 dB (B never reaches 0.1 by 11 dB) | 3.04 [2.58, 3.29]* | 0.46 [0.33, 0.59] | 0.54 [0.41, 0.68] | 0.71 [0.56, 0.88] | -2.33 [-2.61, -1.87]* | 0.17 [0.05, 0.30] |
