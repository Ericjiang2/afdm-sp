# DDST zero-simulation screen: results

Protocol: `.trellis/tasks/10-08-doppler-cluster/research/ddst-zero-sim-screen-20261014.md` (frozen before this run).

## Interference geometry (median over 4 delay draws)

| L | K | r_90 | r_99 | f(K) | f(N/4) | f(N/2) |
|---|---|---|---|---|---|---|
| 4 | 32 | 121 | 178 | 0.458 | 0.000 | 0.000 |
| 8 | 64 | 356 | 560 | 0.529 | 0.193 | 0.020 |
| 12 | 96 | 493 | 774 | 0.503 | 0.274 | 0.090 |
| 16 | 128 | 588 | 899 | 0.478 | 0.325 | 0.137 |
| 20 | 160 | 629 | 931 | 0.448 | 0.343 | 0.157 |
| 24 | 192 | 656 | 948 | 0.421 | 0.354 | 0.170 |
| 28 | 224 | 670 | 960 | 0.391 | 0.360 | 0.177 |
| 32 | 256 | 672 | 958 | 0.364 | 0.364 | 0.179 |
| 40 | 320 | 691 | 965 | 0.318 | 0.373 | 0.190 |
| 48 | 384 | 689 | 965 | 0.269 | 0.372 | 0.189 |

## Round-1 cliff Kc_R1 (law H_w, LMMSE link)

| group | Kc base | Kc U (no dim. cost) | Kc R (dim. cost) | g_U | g_R | r_opt at Kc base |
|---|---|---|---|---|---|---|
| c1_boot 8 dB rho 0.2 | 117 | 210 | 168 | 1.788 | 1.431 | 184 |
| c1_boot 8 dB rho 0.3 | 132 | 223 | 183 | 1.691 | 1.383 | 168 |
| c1_boot 8 dB rho 0.5 | 97 | 157 | 131 | 1.622 | 1.351 | 144 |
| c1_boot 11 dB rho 0.2 | 149 | 296 | 238 | 1.986 | 1.598 | 288 |
| c1_boot 11 dB rho 0.3 | 175 | 336 | 269 | 1.913 | 1.531 | 232 |
| c1_boot 11 dB rho 0.5 | 248 | 439 | 351 | 1.766 | 1.415 | 184 |
| c1_map 6.5 dB rho 0.3 | 62 | 108 | 86 | 1.751 | 1.390 | 152 |

Gate: g_R >= 1.15 in >= 5/7 groups. Passing groups: 7/7. **Decision: PASS-to-design.**

## Geometry flag at the baseline cliff

- 8|0.2: Kc 117, r_90 556 (0.54 N)
- 8|0.3: Kc 132, r_90 593 (0.58 N)
- 8|0.5: Kc 97, r_90 495 (0.48 N)
- 11|0.2: Kc 149, r_90 615 (0.60 N)
- 11|0.3: Kc 175, r_90 642 (0.63 N)
- 11|0.5: Kc 248, r_90 672 (0.66 N)
- 6.5|0.3: Kc 62, r_90 340 (0.33 N)
