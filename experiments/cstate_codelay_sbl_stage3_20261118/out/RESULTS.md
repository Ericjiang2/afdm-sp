# Stage 3 results

Accuracy revision `1508c12e15ccc8615ec26f6cab4dd01310066a00`. Timing revision `81325c28fe97038508c372437ea78d2389d1785f`. Main used 24 CPU shards for 209.4 s and 1.290 core-hours. The quiet timing wall time was 873.4 s on CPU 0.

## Frozen CODELAY gate

13,600 keys, 400 physical frame clusters, and 1976 F0 triggers. F0, FULL and CODELAY failed 1975, 1318 and 1318 keys. The paired FER delta was 0.000 pp. Its percentile interval [0.000, 0.000] pp passes the +0.2 pp gate. There were 0 frame clusters with a FER discordance and 155 differing decoded hashes.

The FER percentile interval is degenerate. The exact one-sided upper 95% limit on the population rate of frame clusters with any FER discordance is 0.746%. Post hoc, all 155 differing hashes occurred on jointly failed keys. CODELAY changed the information error count on 79 of those keys, with fewer errors on 39 and more errors on 40. Two triggered keys had different final delay multisets.

| Cell | FULL crossing (dB) | CODELAY crossing (dB) | 95% difference bounds (dB) | Left-censored draws | Gate |
| --- | ---: | ---: | --- | ---: | --- |
| U_300 | 5.167 | 5.167 | [-inf, +inf] | 1,974 | inconclusive |
| U_500 | 6.255 | 6.255 | [0.000, 0.000] | 0 | pass |
| G_300 | 5.164 | 5.164 | [0.000, 0.000] | 291 | pass |
| G_500 | 6.225 | 6.225 | [0.000, 0.000] | 0 | pass |

The joint gate is inconclusive. In U / rho .3, both curves have 8 / 400 errors at 5 dB and 1 / 400 at 5.5 dB. The paired bootstrap reaches the target at or before the first measured point often enough to leave the upper crossing-difference bound open.

## Same-frame SBL accuracy

| Baseline | Exact common keys | CODELAY errors | SBL errors | CODELAY rescue / harm | Paired delta, 95% CI (pp) |
| --- | ---: | ---: | ---: | ---: | --- |
| L-hard | 9,600 | 40 | 1,443 | 1,403 / 0 | -14.615 [-15.375, -13.854] |
| L-diag | 9,600 | 40 | 1,054 | 1,014 / 0 | -10.562 [-11.104, -10.031] |
| diag-off | 2,400 | 1 | 67 | 66 / 0 | -2.750 [-3.542, -2.000] |

Positive SNR difference below means the archived SBL arm needed more SNR. Crossings use the same frame cohort and each arm’s measured SNR grid.

| Baseline | Cell | SBL − CODELAY crossing (dB) | 95% bounds (dB) | Common-grid point or bound (dB) |
| --- | --- | ---: | --- | --- |
| L-hard | U_300 | 5.270 | [3.860, +inf] | [4.437, +inf] |
| L-hard | U_500 | 1.525 | [1.319, 1.767] | 1.370 |
| L-hard | G_300 | 4.836 | [3.504, 5.460] | [4.000, +inf] |
| L-hard | G_500 | 1.339 | [1.311, 1.377] | 1.114 |
| L-diag | U_300 | 2.930 | [2.230, +inf] | [2.097, +inf] |
| L-diag | U_500 | 1.399 | [1.144, 1.708] | 1.244 |
| L-diag | G_300 | 2.497 | [1.700, 3.087] | [1.660, +inf] |
| L-diag | G_500 | 1.334 | [1.306, 1.371] | 1.109 |
| diag-off | U_300 | 2.976 | [1.536, +inf] | [2.226, +inf] |
| diag-off | G_300 | 1.779 | [1.398, +inf] | [1.000, +inf] |

## Single-core runtime

| Panel | Arm | Mean (ms) | Median (ms) | p95 (ms) |
| --- | --- | ---: | ---: | ---: |
| common | F0 | 247.99 | 247.14 | 256.04 |
| common | FULL | 248.81 | 246.04 | 255.61 |
| common | CODELAY | 248.87 | 246.27 | 255.87 |
| common | L-hard | 2950.03 | 2983.41 | 3415.29 |
| common | diag-off | 3979.17 | 3996.77 | 4552.20 |
| trigger_panel | F0 | 253.50 | 253.57 | 261.70 |
| trigger_panel | FULL | 282.17 | 253.59 | 422.17 |
| trigger_panel | CODELAY | 281.90 | 253.38 | 420.06 |

The 100-key common panel triggered once at 6 dB and zero times at 7 dB. The separate 5 dB panel had 18 triggers. For those, mean geometry latency was 121.15 ms (FULL) and 119.71 ms (CODELAY), a 1.012× ratio.

All 200 timing keys matched their registered outcome and SHA, including the archived timing comparators. 5/6/7 dB timing strata are in [timing_summary.json](timing_summary.json).

## Evidence

Raw main rows remain at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/cstate_codelay_sbl_stage3_20261118/out` (22,820,895 bytes), with [MD5 manifest](MAIN_ROWS_MD5.txt). See [accuracy](accuracy.json), [real-state gate](gate.json), [timing rows](timing.jsonl), [run receipt](main_receipt.json) and [post hoc integrity readout](readout_check.json).
