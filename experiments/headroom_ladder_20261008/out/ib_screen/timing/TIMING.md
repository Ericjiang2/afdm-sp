# Information-budget screen: timing and projection

Single-thread numpy/scipy, one process, seconds per frame for all 5 conditions at once (frames are shared across conditions).

| ref | L | side | draw | A (pivoted QR) | f + J | total |
|---|---|---|---|---|---|---|
| MODEL | 4 | K | 0.000 | 0.297 | 0.003 | 0.301 |
| MODEL | 16 | K | 0.000 | 0.299 | 0.027 | 0.326 |
| MODEL | 32 | K | 0.000 | 0.298 | 0.089 | 0.387 |
| MODEL | 48 | K | 0.000 | 0.298 | 0.180 | 0.478 |
| MODEL | 64 | K | 0.000 | 0.301 | 0.343 | 0.644 |
| MODEL | 96 | N | 0.000 | 0.310 | 0.529 | 0.839 |
| PHYS | 4 | K | 0.000 | 0.298 | 0.003 | 0.301 |
| PHYS | 16 | K | 0.000 | 0.299 | 0.026 | 0.326 |
| PHYS | 32 | K | 0.000 | 0.299 | 0.105 | 0.404 |
| PHYS | 48 | K | 0.000 | 0.301 | 0.253 | 0.554 |
| PHYS | 64 | N | 0.000 | 0.303 | 0.521 | 0.824 |
| PHYS | 96 | N | 0.000 | 0.307 | 0.526 | 0.834 |

| extra (PHYS) | L16 | L48 | L96 |
|---|---|---|---|
| RAY (A under rays + U + J_z), s | 0.72 | 0.74 | 0.79 |
| LMMSE-GMI column, s | 1.16 | 1.15 | 1.16 |
| 6 conditions (with 9.5 dB), total s | 0.327 | 0.579 | 0.926 |

## Projection (core-hours, single quiet process)

- locate (64 frames x 24 L x MODEL+PHYS): 0.48
- confirm, literal rule (L = 4, 8 only): 0.174
- confirm, worst case (all 24 L x 512 frames x MODEL+PHYS): 3.86
- **total literal: 0.66; worst case: 4.34**
- measured slowdown of the mean row time (L = 48): x1.50 at 20 concurrent single-thread shards, x2.85 at 40 -> at 20 concurrent: literal 0.98, worst case 6.49 core-hours; at 40 concurrent: literal 1.87, worst case 12.36

## Bernstein range-term offsets per symbol (S^2 = 0, i.e. a lower bound of the true offset), delta per endpoint = 1.042e-04 (/3 per term)

| ref | cond | L | n=64 offset (A + f + J) | n=512 offset | max possible LB/N = (2N + J range)/N |
|---|---|---|---|---|---|
| MODEL | 6.5 dB rho 0.2 | 4 | 3.84 | 0.47 | 4.29 |
| MODEL | 6.5 dB rho 0.2 | 48 | 3.84 | 0.47 | 4.29 |
| MODEL | 6.5 dB rho 0.3 | 4 | 4.07 | 0.50 | 4.77 |
| MODEL | 6.5 dB rho 0.3 | 48 | 4.07 | 0.50 | 4.77 |
| MODEL | 8 dB rho 0.2 | 4 | 4.20 | 0.52 | 4.70 |
| MODEL | 8 dB rho 0.2 | 48 | 4.20 | 0.52 | 4.70 |
| MODEL | 8 dB rho 0.3 | 4 | 4.44 | 0.55 | 5.21 |
| MODEL | 8 dB rho 0.3 | 48 | 4.44 | 0.55 | 5.21 |
| MODEL | 8 dB rho 0.5 | 4 | 4.74 | 0.58 | 5.88 |
| MODEL | 8 dB rho 0.5 | 48 | 4.74 | 0.58 | 5.88 |
| PHYS | 6.5 dB rho 0.2 | 4 | 2.48 | 0.31 | 2.92 |
| PHYS | 6.5 dB rho 0.2 | 48 | 2.48 | 0.31 | 2.92 |
| PHYS | 6.5 dB rho 0.3 | 4 | 2.63 | 0.32 | 3.23 |
| PHYS | 6.5 dB rho 0.3 | 48 | 2.63 | 0.32 | 3.23 |
| PHYS | 8 dB rho 0.2 | 4 | 2.76 | 0.34 | 3.18 |
| PHYS | 8 dB rho 0.2 | 48 | 2.76 | 0.34 | 3.18 |
| PHYS | 8 dB rho 0.3 | 4 | 2.94 | 0.36 | 3.53 |
| PHYS | 8 dB rho 0.3 | 48 | 2.94 | 0.36 | 3.53 |
| PHYS | 8 dB rho 0.5 | 4 | 3.18 | 0.39 | 4.05 |
| PHYS | 8 dB rho 0.5 | 48 | 3.18 | 0.39 | 4.05 |
