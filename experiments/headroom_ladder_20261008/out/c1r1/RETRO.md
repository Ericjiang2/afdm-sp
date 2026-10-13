# C1 round-1 loop law: retrodiction on stored rows (post hoc, hypothesis-generating)

I* = 0.5770. Modes: ind = independent soft-symbol errors (T2 structure); H_w = coherent fraction = data share w; coh = full coherent absorption. L0 = link q = eta a/(n+e) (T2), L1 = LMMSE link q = eta a (1-e)/(n+e).

## eps_det1 (median over frames) vs fixed point e*, 56 SPg_flat cells

| model | median ln(pred/obs) | median abs | abs<=.15 | abs<=.30 |
|---|---|---|---|---|
| ind|L0 | -0.602 | 0.602 | 0.00 | 0.00 |
| ind|L1 | -0.536 | 0.536 | 0.00 | 0.02 |
| H_w|L0 | +0.026 | 0.119 | 0.64 | 0.95 |
| H_w|L1 | +0.124 | 0.138 | 0.54 | 0.79 |
| coh|L0 | +0.768 | 0.768 | 0.04 | 0.05 |
| coh|L1 | +0.770 | 0.770 | 0.02 | 0.07 |

## Round-1 MI I_1 = Phi_K(none) (c1e, rho .3, frames 500-599)

| SNR | K | I_1 obs | ind L1 | H_w L1 | coh L1 | H_w L0 |
|---|---|---|---|---|---|---|
| 6.5 | 64 | 0.598 | 0.636 | 0.572 | 0.475 | 0.602 |
| 6.5 | 96 | 0.549 | 0.605 | 0.516 | 0.403 | 0.562 |
| 6.5 | 128 | 0.503 | 0.574 | 0.467 | 0.352 | 0.529 |
| 6.5 | 160 | 0.449 | 0.540 | 0.423 | 0.312 | 0.499 |
| 6.5 | 192 | 0.411 | 0.504 | 0.385 | 0.281 | 0.473 |
| 6.5 | 224 | 0.375 | 0.469 | 0.352 | 0.256 | 0.451 |
| 8 | 64 | 0.708 | 0.754 | 0.696 | 0.580 | 0.718 |
| 8 | 96 | 0.656 | 0.736 | 0.642 | 0.486 | 0.681 |
| 8 | 128 | 0.599 | 0.715 | 0.585 | 0.420 | 0.643 |
| 8 | 160 | 0.534 | 0.688 | 0.529 | 0.371 | 0.605 |
| 8 | 192 | 0.486 | 0.659 | 0.482 | 0.334 | 0.572 |
| 8 | 224 | 0.440 | 0.624 | 0.439 | 0.302 | 0.540 |

## Round-1 cliff Kc_R1 (FER_r1 = .5 observed; I_1 = I* predicted)

| dataset | SNR | rho | obs | ind L1 | H_w L1 | coh L1 | H_w L0 |
|---|---|---|---|---|---|---|---|
| c1_boot | 8 | 0.2 | 132 | - | 118 | 70 | 176 |
| c1_boot | 8 | 0.3 | 141 | - | 133 | 65 | 187 |
| c1_boot | 8 | 0.5 | 100 | 149 | 97 | 41 | 123 |
| c1_boot | 11 | 0.2 | 190 | - | 157 | 93 | 198 |
| c1_boot | 11 | 0.3 | 220 | - | 178 | 94 | 230 |
| c1_boot | 11 | 0.5 | 225 | - | 249 | 99 | - |
| c1_map | 5 | 0.3 | - | - | - | - | - |
| c1_map | 6.5 | 0.3 | 76 | 125 | 62 | 34 | 84 |

## First K (step 16, up to 1024) with more than one fixed point of the H_w L1 round-1 map

- none
