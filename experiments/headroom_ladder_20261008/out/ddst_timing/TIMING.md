# DDST Stage-1 cost estimate (timing run: frames 7100-7101, one single-thread process, quiet server)

| L | DDST-A | DDST-A-blind | DDST-N | SPg_flat | Tx (M + eig) |
|---|---|---|---|---|---|
| 8 | 0.89 s | 0.89 s | 0.85 s | 0.82 s | 1.10 s |
| 16 | 1.31 s | 1.31 s | 1.25 s | 1.20 s | 1.17 s |
| 32 | 2.43 s | 2.42 s | 2.24 s | 2.24 s | 1.36 s |
| 40 | 2.88 s | 2.89 s | 2.68 s | 2.77 s | 1.49 s |

Generator/scoring overhead per (frame, cell, L) block: 0.70 s (remainder of the shard wall time 74.0 s over 8 blocks).

- 3 arms (SPg_flat, DDST-A, DDST-N): 96.3 s per frame over the 14 cells, x 200 frames = **5.35 core-hours** (budget 20).
- 4 arms (+ DDST-A-blind): 122.5 s per frame over the 14 cells, x 200 frames = **6.81 core-hours** (budget 20).
