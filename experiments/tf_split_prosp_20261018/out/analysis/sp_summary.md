# Split-principle prospective test: summary (draft)

S keys 2400, K keys 6400 (triggered units 1608), clusters (frames) 200, bootstrap 20000 (seed 20261018), 95% percentile CI.

## Verdict: REFUTED

- P1 (S, estimation) fails: d1 = S-H - S-C: +0.0404 [+0.0312, +0.0504]
- P2 (S, non-inferiority) fails: d2 = S-H - S-D: +0.1075 [+0.0917, +0.1242]
- P3a (K, estimation, A2 geometry) fails: r3a = K-diag-isofix - K-diag-fullfix: -0.0292 [-0.0390, -0.0204]
- P3b (K, equivalence, A1 geometry) holds: r3b = K-isofix - K-fullfix: +0.0000 [+0.0000, +0.0000]
- P4 (K, decision = E-1 replication) holds: r4 = K-prod - K-diag: +0.1803 [+0.1611, +0.1995]
- refuted by: S: ci_lo(d1) > 0, K: ci_hi(r3a) < 0
- rule: P1: ci_hi(d1) < 0; P2: ci_hi(d2) <= .01; P3a: ci_lo(r3a) > 0; P3b: ci(r3b) within [-.01, .01]; P4: ci_lo(r4) > 0; REFUTED: ci_lo(d1) > 0 or ci_hi(r3a) < 0; CONFIRMED: P1, P2, P3a, P3b, P4; PARTIAL: P1 and P3a but not all of P2, P3b, P4; else MIXED

## S family arms

| arm | FER [CI] | failures | NMSE mean [CI] | atoms | same-delay pairs (true/false delay) | SBL cap-hit keys (fraction) |
|---|---|---|---|---|---|---|
| S-D | 0.0550 [0.0433, 0.0675] | 132 | 0.05787 [0.0557, 0.06009] | 23.59 | 67377 (67274/103) | 1485 (0.619) |
| S-C | 0.1221 [0.1062, 0.1383] | 293 | 0.07304 [0.07041, 0.07571] | 22.53 | 12050 (10543/1507) | 2248 (0.937) |
| S-H | 0.1625 [0.1417, 0.1842] | 390 | 0.07107 [0.06844, 0.07377] | 22.53 | 12050 (10543/1507) | 2248 (0.937) |

## S family contrasts (left - right)

| contrast | role | FER diff [CI] | NMSE diff [CI] | McNemar b/c | log10 p (left better) | log10 p (right better) |
|---|---|---|---|---|---|---|
| S-H - S-C | primary | +0.0404 [+0.0312, +0.0504] | -0.00196 [-0.00243, -0.00150] | 106/9 | 0.00 | -21.73 |
| S-H - S-D | primary | +0.1075 [+0.0917, +0.1242] | +0.01320 [+0.01207, +0.01436] | 261/3 | 0.00 | -72.99 |
| S-C - S-D | context | +0.0671 [+0.0558, +0.0788] | +0.01517 [+0.01417, +0.01618] | 168/7 | 0.00 | -40.72 |

## K family rescue rate R among triggered units

| arm | R [CI] | rescued / triggered | same-delay pairs (true/false delay) |
|---|---|---|---|
| K-prod | +0.2917 [+0.2732, +0.3100] | 469 / 1608 | 20 (20/0) |
| K-diag | +0.1113 [+0.0957, +0.1271] | 179 / 1608 | 2810 (2810/0) |
| K-fullfix | +0.2774 [+0.2603, +0.2943] | 446 / 1608 | 20 (20/0) |
| K-isofix | +0.2774 [+0.2603, +0.2943] | 446 / 1608 | 20 (20/0) |
| K-diag-fullfix | +0.1748 [+0.1592, +0.1901] | 281 / 1608 | 2810 (2810/0) |
| K-diag-isofix | +0.1455 [+0.1301, +0.1612] | 234 / 1608 | 2810 (2810/0) |

## K family contrasts (left - right, rescue-rate difference)

| contrast | role | R diff [CI] | McNemar b/c (not rescued) | log10 p (left better) | log10 p (right better) |
|---|---|---|---|---|---|
| K-diag-isofix - K-diag-fullfix | primary | -0.0292 [-0.0390, -0.0204] | 47/0 | -0.00 | -14.15 |
| K-isofix - K-fullfix | primary | +0.0000 [+0.0000, +0.0000] | 0/0 | 0.00 | 0.00 |
| K-prod - K-diag | primary | +0.1803 [+0.1611, +0.1995] | 2/292 | -83.87 | 0.00 |
| K-fullfix - K-prod | report | -0.0143 [-0.0251, -0.0031] | 49/26 | -0.00 | -2.28 |
| K-isofix - K-prod | report | -0.0143 [-0.0251, -0.0031] | 49/26 | -0.00 | -2.28 |
| K-diag-fullfix - K-diag | report | +0.0634 [+0.0507, +0.0770] | 2/104 | -28.16 | 0.00 |
| K-diag-isofix - K-diag | report | +0.0342 [+0.0245, +0.0443] | 3/58 | -13.78 | 0.00 |

cost S 4.094 + K 0.748 = 4.841 core-h; S-H vs independent numpy ridge solve max rel err 3.31e-14, K iso arms 5.20e-15 (tol 1e-10); K-fullfix gains == A1 result.gains in 1608/1608, K-diag-isofix gains == A2 result.gains in 1608/1608 triggered units.

(McNemar treats rows as independent pairs; the frozen criterion is the cluster bootstrap.)
