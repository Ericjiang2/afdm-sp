# C1 trade-off map (Part A)

rows 40000 (error rows 0, duplicates 0); frames per cell 1000; rho 0.3; SNR [5.0, 6.5] dB; L [2, 4, 6, 8, 12, 16, 20, 24, 28, 32] (K = 8L = [16, 32, 48, 64, 96, 128, 160, 192, 224, 256]); arms ['A3', 'SPg_flat']; genie delays; bootstrap B=4000 frames (joint over L/SNR/arm), seed 20261009.

**g used for K*(g): 1.37** (c1_boot, SPg_flat, level 0.5, shrinkage-corrected fit, rms log err 0.115; K* = b/((1-b)s) == c1_analyze.kstar_shr(P=1), max rel diff 4.2e-16).

## 1. FER vs L (Wilson 95% CI)

### SNR 5 dB (sigma2 0.3162); K*(g=1.37) = 73, L* = 9.1

| arm | L=2 | L=4 | L=6 | L=8 | L=12 | L=16 | L=20 | L=24 | L=28 | L=32 |
|---|---|---|---|---|---|---|---|---|---|---|
| A3 | 0.392 [0.362,0.423] | 0.309 [0.281,0.338] | 0.295 [0.268,0.324] | 0.275 [0.248,0.303] | 0.226 [0.201,0.253] | 0.188 [0.165,0.213] | 0.150 [0.129,0.173] | 0.130 [0.111,0.152] | 0.124 [0.105,0.146] | 0.119 [0.100,0.141] |
| SPg_flat | 0.452 [0.421,0.483] | 0.438 [0.408,0.469] | 0.508 [0.477,0.539] | 0.595 [0.564,0.625] | 0.796 [0.770,0.820] | 0.945 [0.929,0.958] | 0.996 [0.990,0.998] | 1.000 [0.996,1.000] | 1.000 [0.996,1.000] | 1.000 [0.996,1.000] |

### SNR 6.5 dB (sigma2 0.2239); K*(g=1.37) = 134, L* = 16.7

| arm | L=2 | L=4 | L=6 | L=8 | L=12 | L=16 | L=20 | L=24 | L=28 | L=32 |
|---|---|---|---|---|---|---|---|---|---|---|
| A3 | 0.175 [0.153,0.200] | 0.073 [0.058,0.091] | 0.039 [0.029,0.053] | 0.036 [0.026,0.049] | 0.009 [0.005,0.017] | 0.004 [0.002,0.010] | 0.001 [0.000,0.006] | 0.002 [0.001,0.007] | 0.000 [0.000,0.004] | 0.000 [0.000,0.004] |
| SPg_flat | 0.213 [0.189,0.239] | 0.130 [0.111,0.152] | 0.127 [0.108,0.149] | 0.144 [0.124,0.167] | 0.227 [0.202,0.254] | 0.440 [0.410,0.471] | 0.742 [0.714,0.768] | 0.944 [0.928,0.957] | 0.998 [0.993,0.999] | 1.000 [0.996,1.000] |

## 2. A3 (true H) FER vs L

- SNR 5 dB: A3 FER 0.392 0.309 0.295 0.275 0.226 0.188 0.150 0.130 0.124 0.119; Spearman(L, FER) -1.00; point-estimate increases none; significant adjacent increases (paired McNemar p<.01) none; FER(L=2) > FER(L=32): 350/77, p=6.0e-43

- SNR 6.5 dB: A3 FER 0.175 0.073 0.039 0.036 0.009 0.004 0.001 0.002 0.000 0.000; Spearman(L, FER) -0.98; point-estimate increases ['20->24 (1->2)']; significant adjacent increases (paired McNemar p<.01) none; FER(L=2) > FER(L=32): 175/0, p=2.1e-53

## 3. SP (SPg_flat) FER vs L: interior minimum?

naive: L_min = last argmin of FER over L; p_left = one-sided exact McNemar FER(L=2) > FER(L_min); p_right = FER(L=32) > FER(L_min).  split-sample: L_min chosen on even-index frames, test on odd-index frames (selection-bias free).  P(L_min interior) = bootstrap probability that the argmin (last) lies strictly inside the grid; P(L_min > 2) = bootstrap probability that it is not the smallest L.

| SNR | L_min | FER_min | FER(L=2) | FER(2) - FER_min [95% CI] | naive left b/c | naive right b/c | split-sample (odd frames) | P(L_min interior) | P(L_min>2) |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 4 | 0.438 | 0.452 | 0.014 [0.000,0.058] | 247/233 p=0.28 | 562/0 p=6.6e-170 | L=4: 122/116 p=0.37 | 0.755 | 0.755 |
| 6.5 | 6 | 0.127 | 0.213 | 0.086 [0.063,0.122] | 187/101 p=2.3e-07 | 873/0 p=1.6e-263 | L=4: 94/52 p=0.00032 | 1.000 | 1.000 |

## 4. SP - A3 gap per L (paired McNemar, b = SP fails only, c = A3 fails only; * p<.01)

| SNR | L=2 | L=4 | L=6 | L=8 | L=12 | L=16 | L=20 | L=24 | L=28 | L=32 |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 60/0* | 129/0* | 213/0* | 320/0* | 570/0* | 757/0* | 846/0* | 870/0* | 876/0* | 881/0* |
| 6.5 | 38/0* | 57/0* | 88/0* | 108/0* | 218/0* | 436/0* | 741/0* | 942/0* | 998/0* | 1000/0* |

## 5. Cliff location vs K*(g)

K*(g=1.37); K_c(level) with 95% bootstrap CI; g_impl = (1-rho)/(s2 + K_c s/(1+K_c s)) = SINR threshold implied by K_c; K*(g) also shown for g = 1.3 / 1.4.  "within CI" = K*(g) inside the K_c bootstrap interval.

| SNR | level | K_c | K_c 95% CI | K*(g) | K*(1.3) / K*(1.4) | g_impl | K* in CI | ln(K*/K_c) |
|---|---|---|---|---|---|---|---|---|
| 5 | 0.1 | <16 | [<16,<16] | 73 (L* 9.1) | 86 / 68 | n/a | no | n/a |
| 5 | 0.5 | 46 | [41,51] | 73 (L* 9.1) | 86 / 68 | 1.56 | no | +0.46 |
| 6.5 | 0.1 | <16 | [<16,<16] | 134 (L* 16.7) | 153 / 127 | n/a | no | n/a |
| 6.5 | 0.5 | 134 | [131,137] | 134 (L* 16.7) | 153 / 127 | 1.37 | yes | -0.00 |

### 5b. Decoder-waterfall-robust cliff definitions

The level-0.5 crossing of the raw SP FER is confounded by the decoder waterfall (SP FER is already ~.44 at L=2..4 at 5 dB).  Two floor-robust variants: (cond) SP-specific failure rate P(SP fails | A3 decodes), level 0.5 (removes frames lost to channel diversity / the code itself); (rel) raw SP FER crossing the midpoint (1 + FER_min)/2 above its own minimum.  K_c by linear interpolation in K, 95% bootstrap CI over frames.

| SNR | definition | K_c | K_c 95% CI | K*(g) | g_impl | K* in CI | ln(K*/K_c) | cond. rate at L=2,4,6,8,12,16,20,24,28,32 |
|---|---|---|---|---|---|---|---|---|
| 5 | cond (level .5) | 70 | [67,73] | 73 (L* 9.1) | 1.39 | yes | +0.04 | 0.099 0.187 0.302 0.441 0.736 0.932 0.995 1.000 1.000 1.000 |
| 5 | rel (level 0.719) | 84 | [80,87] | 73 (L* 9.1) | 1.31 | no | -0.14 |  |
| 6.5 | cond (level .5) | 135 | [132,137] | 134 (L* 16.7) | 1.37 | yes | -0.00 | 0.046 0.061 0.092 0.112 0.220 0.438 0.742 0.944 0.998 1.000 |
| 6.5 | rel (level 0.564) | 141 | [138,143] | 134 (L* 16.7) | 1.34 | no | -0.05 |  |

## 6. First-pass error eps1 (SPg_flat) vs shrinkage-corrected prediction eps = Ks/(1+Ks)

| SNR | row | L=2 | L=4 | L=6 | L=8 | L=12 | L=16 | L=20 | L=24 | L=28 | L=32 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | obs | 0.050 | 0.098 | 0.139 | 0.178 | 0.246 | 0.306 | 0.353 | 0.398 | 0.436 | 0.463 |
| 5 | pred | 0.050 | 0.096 | 0.137 | 0.175 | 0.241 | 0.297 | 0.346 | 0.388 | 0.426 | 0.459 |
| 5 | obs/pred | 1.00 | 1.03 | 1.02 | 1.02 | 1.02 | 1.03 | 1.02 | 1.02 | 1.02 | 1.01 |
| 6.5 | obs | 0.046 | 0.090 | 0.128 | 0.165 | 0.230 | 0.286 | 0.332 | 0.376 | 0.413 | 0.441 |
| 6.5 | pred | 0.046 | 0.088 | 0.126 | 0.161 | 0.224 | 0.278 | 0.325 | 0.366 | 0.403 | 0.435 |
| 6.5 | obs/pred | 1.00 | 1.03 | 1.02 | 1.02 | 1.03 | 1.03 | 1.02 | 1.03 | 1.03 | 1.01 |

