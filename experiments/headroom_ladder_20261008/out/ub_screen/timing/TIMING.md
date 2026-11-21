# Upper-bound screen: timing probe and projection

Single-thread numpy/scipy, one process, seconds per frame for all conditions of the stage at once (frame 0 of each (ref, L) dropped as warm-up).

| ref | L | sec per frame (5 conds) | n |
|---|---|---|---|
| MODEL | 4 | 0.003 | 2 |
| MODEL | 16 | 0.026 | 2 |
| MODEL | 28 | 0.071 | 7 |
| MODEL | 43 | 0.153 | 7 |
| MODEL | 52 | 0.225 | 2 |
| MODEL | 56 | 0.267 | 2 |
| MODEL | 68 | 0.389 | 2 |
| MODEL | 96 | 0.577 | 2 |
| PHYS | 4 | 0.003 | 2 |
| PHYS | 16 | 0.027 | 2 |
| PHYS | 28 | 0.082 | 7 |
| PHYS | 43 | 0.218 | 7 |
| PHYS | 52 | 0.320 | 2 |
| PHYS | 56 | 0.566 | 2 |
| PHYS | 68 | 0.557 | 2 |
| PHYS | 96 | 0.582 | 2 |
| RAY | 4 | 0.002 | 2 |
| RAY | 16 | 0.008 | 2 |
| RAY | 28 | 0.016 | 7 |
| RAY | 43 | 0.031 | 7 |
| RAY | 52 | 0.042 | 2 |
| RAY | 56 | 0.057 | 2 |
| RAY | 68 | 0.069 | 2 |
| RAY | 96 | 0.144 | 2 |

6th condition (9.5 dB) factor on sec per frame (ro and grid add it): MODEL x1.172, PHYS x1.090, RAY x1.054

## Projection (core-hours, single-thread; per-L seconds interpolated linearly in L between measured points)

- decision: MODEL 2.18 + PHYS 1.45 + RAY 0.23 = 3.86
- ro (512 frames, L set [26, 27, 28, 32, 34, 38, 41, 42, 48, 51, 54, 56, 64, 68]): MODEL 0.41 + PHYS 0.59 + RAY 0.07 = 1.07
- grid (RAY, 64 frames, L 4..96): 0.02
- **total 4.95 core-hours quiet; x1.50 contention at 20 concurrent shards (screen measurement) = 7.41 core-hours, ~0.37 h wall at 20 shards**
