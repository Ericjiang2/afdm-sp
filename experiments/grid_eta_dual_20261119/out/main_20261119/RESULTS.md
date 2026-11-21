# Grid fineness η · frozen Phase 2 results

## Observation

X evaluated all 1,000 registered forced-miss units at ρ = .30, 4.5 dB and R = 128. All 1,000 frames entered the paired analysis. The exclusion counts were zero for out-of-bank offsets and duplicate candidates.

| Scorer | Q(.25) | Q(.125) | Q(.0625) | Close minus wide (pp, 95% CI) |
|---|---:|---:|---:|---:|
| A2 | 45.00% (450/1000) | 45.70% (457/1000) | 46.70% (467/1000) | +1.70 [+0.90, +2.60] |
| CODELAY | 1.80% (18/1000) | 2.20% (22/1000) | 1.90% (19/1000) | +0.10 [-0.40, +0.60] |
| A2 minus CODELAY change | — | — | — | +1.60 [+0.70, +2.50] |

S evaluated 200 physical frames, each with U and G at ρ = .30 and 6 dB. Across the three grids there were 1,200 paired keys and 3,600 arm outcomes. The first-stage grid was fixed at η = 4. The first-round state matched across grids on all keys.

| η | R0 frame errors | R1 frame errors | S-lo frame errors | G_B, R1 − R0 (pp) | S-lo − R0 (pp) |
|---:|---:|---:|---:|---:|---:|
| 2 | 126/400 (31.50%) | 261/400 (65.25%) | 193/400 (48.25%) | +33.75 | +16.75 |
| 4 | 52/400 (13.00%) | 278/400 (69.50%) | 120/400 (30.00%) | +56.50 | +17.00 |
| 8 | 265/400 (66.25%) | 256/400 (64.00%) | 186/400 (46.50%) | -2.25 | -19.75 |

| Contrast | Paired difference (pp, 95% CI) |
|---|---:|
| G_B(4) − G_B(2) | +22.75 [+18.00, +27.75] |
| G_B(8) − G_B(4) | -58.75 [-65.50, -52.00] |
| G_B(8) − G_B(2) | -36.00 [-42.75, -29.50] |
| G_B(2) − G_B(8) | +36.00 [+29.50, +42.75] |
| S-lo minus R0, η = 8 vs η = 2 | -36.50 [-42.75, -30.25] |

The endpoint slope relative to R0 was -6.00 pp per unit of η for R1 and -6.08 for S-lo. The absolute slopes were 6.00 and 6.08 pp per unit of η, respectively.

| η | Arm | Mean β | Converged | Mean output same-delay pairs | Mean pruned atoms | Median refinement condition number |
|---:|---|---:|---:|---:|---:|---:|
| 2 | R0 | 4.075 | 100.00% | 18.448 | 0.00 | 12.14 |
| 2 | R1 | 3.348 | 44.50% | 7.360 | 0.00 | 29.89 |
| 2 | S-lo | 3.194 | 98.00% | 16.938 | 0.00 | 102.82 |
| 4 | R0 | 4.826 | 95.25% | 33.153 | 0.00 | 18.43 |
| 4 | R1 | 3.337 | 7.00% | 4.870 | 0.00 | 22.87 |
| 4 | S-lo | 3.148 | 3.00% | 26.363 | 0.00 | 4387.91 |
| 8 | R0 | 5.327 | 0.00% | 55.605 | 0.00 | 26.25 |
| 8 | R1 | 3.275 | 0.00% | 4.290 | 0.00 | 22.81 |
| 8 | S-lo | 3.105 | 0.00% | 44.862 | 0.00 | 16874.57 |

| η | Full-grid low modes per delay | Mean screened candidates | Mean screened rank | Largest screened block | Mean Π_lo rank | Total S-lo penalty trace |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 6 | 422.18 | 422.18 | 13 | 165.52 | 11,073,707.07 |
| 4 | 18 | 627.31 | 464.62 | 25 | 425.68 | 28,477,635.87 |
| 8 | 41 | 1062.20 | 410.31 | 49 | 878.87 | 58,804,874.09 |

## Frozen verdict

- X direction is **supported**. The 10 pp prediction is **refuted**.
- S primary label is **uncertain**. Strict monotonicity does not pass, all-pairs equivalence does not pass, endpoint equivalence does not pass, and reversal passes.
- Joint label is **opposite prediction**.

Intervals use the frozen 20,000 paired physical-frame bootstrap draws with seed 20261124.

## Untested explanation

Incomplete convergence at η = 8 may contribute to the increase in R0 frame errors that drives the reversal (untested, medium confidence). A matched longer-budget R0 replay on archived keys could test this explanation.

## Provenance

Freeze b6046c54 and launcher dc8784dc. X charged 0.153 / 3 core-hours and S charged 6.200 / 15. Both legs finished **DONE**.

Raw rows are retained on deinlab at /data/guoyikun/00inbox/AFDM-channel-estimation/experiments/grid_eta_dual_20261119/out/main_20261119. [Raw shard MD5 list](REMOTE_ROWS_MD5.txt) · [Machine-readable results](results.json) · [CPU accounting](budget.json)
