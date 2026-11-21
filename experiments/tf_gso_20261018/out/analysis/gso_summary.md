# GSO summary (draft)

keys 1200, clusters (frames) 100, bootstrap 20000 (seed 20261018), 95% percentile CI.

## Verdict: VARIANCE-SUPPORTED

- d1 = C-ls0 - C-sbl: +0.2208 [+0.1975, +0.2433]
- d2 = C-ls0 - D-sbl: +0.2942 [+0.2650, +0.3233]
- rule: BIAS-SUPPORTED: ci_hi(d1) < 0 and ci_hi(d2) <= .01; VARIANCE-SUPPORTED: ci_lo(d1) > 0; else MIXED

## Arms

| arm | FER [CI] | failures | NMSE mean | atoms | same-delay pairs (true/false delay) | SBL cap-hit keys |
|---|---|---|---|---|---|---|
| D-sbl | 0.0425 [0.0292, 0.0567] | 51 | 0.05648 | 23.73 | 34653 (34607/46) | 739 |
| C-sbl | 0.1158 [0.0958, 0.1375] | 139 | 0.07285 | 22.49 | 6267 (5471/796) | 1101 |
| C-ls0 | 0.3367 [0.3033, 0.3700] | 404 | 0.07534 | 22.49 | 6267 (5471/796) | 1101 |
| D-ls0 | 0.0708 [0.0517, 0.0917] | 85 | 0.04238 | 23.73 | 34653 (34607/46) | 739 |
| Z-sbl | 0.2542 [0.2225, 0.2858] | 305 | 0.06814 | 23.21 | 6909 (5813/1096) | 1118 |
| Z-ls0 | 0.3433 [0.3092, 0.3775] | 412 | 0.07724 | 23.21 | 6909 (5813/1096) | 1118 |

## Contrasts (left - right)

| contrast | role | FER diff [CI] | NMSE diff [CI] | McNemar b/c | log10 p (left better) | log10 p (right better) |
|---|---|---|---|---|---|---|
| C-ls0 - C-sbl | primary | +0.2208 [+0.1975, +0.2433] | +0.00249 [+0.00150, +0.00351] | 265/0 | 0.00 | -79.77 |
| C-ls0 - D-sbl | primary | +0.2942 [+0.2650, +0.3233] | +0.01886 [+0.01658, +0.02118] | 353/0 | 0.00 | -106.26 |
| D-ls0 - D-sbl | report | +0.0283 [+0.0150, +0.0433] | -0.01410 [-0.01578, -0.01244] | 42/8 | -0.00 | -6.24 |
| Z-sbl - D-sbl | report | +0.2117 [+0.1850, +0.2400] | +0.01167 [+0.00980, +0.01358] | 254/0 | 0.00 | -76.46 |
| Z-ls0 - Z-sbl | report | +0.0892 [+0.0733, +0.1050] | +0.00909 [+0.00852, +0.00967] | 110/3 | 0.00 | -28.64 |
| C-sbl - D-sbl | context | +0.0733 [+0.0583, +0.0892] | +0.01637 [+0.01466, +0.01807] | 90/2 | -0.00 | -24.06 |

cost 3.066 core-h (9.20 s/key); LS0 vs numpy max rel err 7.44e-12 (tol 1e-10).

(McNemar treats rows as independent pairs; the frozen criterion is the cluster bootstrap.)
