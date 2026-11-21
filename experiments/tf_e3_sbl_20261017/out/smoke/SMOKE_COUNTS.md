# E-3 gate-phase smoke: counts only (no interpretation); rows stay on deinlab (md5 in REMOTE_MD5.txt)

Run 2026-10-17 12:47-12:49 UTC by `launch_e3.sh MODE=gate` (26 processes, load ~9); code md5 in CODE_MD5.txt. 0 error rows, 0 Cholesky jitter events,
max |diag Gamma - sum v| / sum v = 3.1e-16. SMOKE ONLY: provisional SNR 8 dB (main-style) and 6/10 dB (calibration-style).

| | main-style smoke: 8 frames x 4 cells, 8 dB, frames 8000..8007 (32 keys) | calibration-style smoke: 4 frames x 4 cells x {6,10} dB, L-hard only, frames 8100..8103 (32 keys) |
|---|---|---|
| FER counts (frames with >= 1 info-bit error), L-hard / L-diag / L-cov / L-genie | 2 / 0 / 2 / 0 of 32 | L-hard 11 of 32 |
| mean n_pair (same-delay pairs among the output atoms), L-hard / L-diag / L-cov / L-genie | 6.84 / 30.47 / 5.53 / 5.34 | L-hard 6.38 |
| per cell (FER counts L-hard/L-diag/L-cov/L-genie) | G.3 1/0/1/0, G.5 0/0/0/0, U.3 1/0/1/0, U.5 0/0/0/0 | L-hard: G.3 2, G.5 4, U.3 1, U.5 4 (8 keys each) |
| round-1 FER (shared) | 0.938 | 0.75 |
| SBL starting atoms (stage 2, mean) / final atoms | 623 / 623 (pruning never fired) | 625 / 625 |
| SBL iterations (mean) / runs that met the 1e-4 stop rule | 100 (L-diag 95.9) / L-diag 14 of 32, others 0 | 99.3 / 1 of 32 |
| output atoms per variant (mean) L-hard / L-diag / L-cov / L-genie | 22.2 / 23.4 / 20.8 / 13.7 | L-hard 20.8 |
| seconds per key (incl. generation .15 / .09) | 11.10 | 3.65 |
| per-variant seconds (columns / SBL / detect / decode / total), L-hard | .052 / 2.53 / .029 / .018 / 2.63 | .058 / 2.72 / .029 / .021 / 2.83 |
| L-diag / L-cov / L-genie total seconds | 2.47 / 2.58 / 2.56 | - |
| other stages per key: stage-1 screen / stage-1 SBL / round-1 detect+decode / stage-2 screen / Gamma | .077 / .33 / .055 / .24 / .043 | .047 / .36 / .055 / .27 / - |

## R-iter code-path smoke (SMOKE ONLY, added with the O1-O3 amendments; frames 8200..8207, 8 dB)
Main-style smoke rows (32 keys, out/smoke_ri_main) and riter rows (8 keys, `--mode riter --smoke`, L-diag and L-cov at max_iter = 400, out/smoke_ri), rows stay on deinlab
(md5 in REMOTE_MD5.txt). Reused-pipeline mismatches vs the main-style rows: 0 of 8 (stage-1 atoms, round-1 decoded sha, candidate-set size). 8/8 SBL runs met the stop rule within 400 iterations
(mean iterations L-diag 116.3, L-cov 157.0; at 100 iterations the cap was hit by 75% / 88% of these runs); n_pair identical at 100 and 400 iterations (L-diag 24.75, L-cov 4.75; genie 4.875), FER 0 in both.
The refactored driver reproduced 4/4 pre-amendment smoke rows (frames 8000, same keys) bitwise (decoded sha, atoms, n_pair, stage-1 atoms, round-1 sha).
