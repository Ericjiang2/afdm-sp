# Γ = 0 support exchange

## Observation

Frames 9400–9799 contributed 13,600 paired keys over 400 physical frames. The shared two-round receiver F0 triggered 1,952 keys with a nonzero syndrome.
Intervals use 20,000 shared physical-frame bootstrap draws (seed 20261126). The trigger denominator was zero in 0 draws.

| Execution | Recorded value |
| --- | --- |
| Frozen protocol revision | 1266052ea0c55e679e7b0a20442c8e1375af0275 |
| Producing Git revision | 41c9e63d6633911fa5178b2e2b5d6839a0e46477 |
| Recorded wall seconds | 299.615 |
| Recorded core-hours | 1.768 |

### First accepted global swap and final support

| Arm | First-edit phantoms | First-edit rate [95% interval] | Final same-delay keys | Final rate [95% interval] |
| --- | --- | --- | --- | --- |
| CD | 36 | 1.84 [0.94, 2.89] % | 28 | 1.43 [0.72, 2.27] % |
| Z | 36 | 1.84 [0.99, 2.80] % | 30 | 1.54 [0.82, 2.39] % |
| H | 50 | 2.56 [1.56, 3.69] % | 39 | 2.00 [1.21, 2.87] % |
| S | 1740 | 89.14 [86.72, 91.40] % | 1759 | 90.11 [87.72, 92.32] % |

| Arm | Phantom | Restored true delay | Other | No accepted swap | Phantoms within 0.25 Doppler bin |
| --- | --- | --- | --- | --- | --- |
| CD | 36 (1.84%) | 1,012 (51.84%) | 563 (28.84%) | 341 (17.47%) | 0 (0.00%) |
| Z | 36 (1.84%) | 947 (48.51%) | 699 (35.81%) | 270 (13.83%) | 0 (0.00%) |
| H | 50 (2.56%) | 963 (49.33%) | 759 (38.88%) | 180 (9.22%) | 1 (2.00%) |
| S | 1,740 (89.14%) | 46 (2.36%) | 87 (4.46%) | 79 (4.05%) | 1,733 (99.60%) |

| Arm | Phantom → same delay | Phantom → distinct delays | Nonphantom → same delay | Nonphantom → distinct delays |
| --- | --- | --- | --- | --- |
| CD | 23 | 13 | 5 | 1911 |
| Z | 25 | 11 | 5 | 1911 |
| H | 32 | 18 | 7 | 1895 |
| S | 1739 | 1 | 20 | 192 |

Z-sel inherits the Z geometry and has the same transitions as Z.

### Rescue and geometry agreement

| Arm | Triggered keys with zero information-bit errors | Rate [95% interval] |
| --- | --- | --- |
| CD | 659 | 33.76 [31.87, 35.62] % |
| Z | 653 | 33.45 [31.54, 35.32] % |
| H | 665 | 34.07 [32.20, 35.91] % |
| S | 290 | 14.86 [13.34, 16.40] % |
| Z-sel | 663 | 33.97 [32.08, 35.83] % |

| Paired rescue contrast | Difference [95% interval] | Point direction | Only first arm rescued | Only second arm rescued |
| --- | --- | --- | --- | --- |
| Z − CD | -0.31 [-0.74, 0.10] pp | CD | 6 | 12 |
| H − CD | +0.31 [-0.26, 0.89] pp | H | 22 | 16 |
| Z-sel − Z | +0.51 [0.21, 0.84] pp | Z-sel | 10 | 0 |
| Z-sel − CD | +0.20 [-0.20, 0.61] pp | Z-sel | 10 | 6 |

| Arm vs CD | Exact first edit | Both without edit | Equal delay multisets | Exact refined Doppler among equal delays | Median absolute gap (bins) |
| --- | --- | --- | --- | --- | --- |
| Z | 1,194 (61.17%) | 229 | 1,689 (86.53%) | 0/1689 (0.00%) | 0.003 |
| H | 950 (48.67%) | 143 | 1,470 (75.31%) | 0/1470 (0.00%) | 0.008 |

### Full-grid frame errors and 1% crossings

| Paired frame error rate (FER) contrast | Difference [95% interval] | Only first arm failed | Only CD failed |
| --- | --- | --- | --- |
| Z − CD | +0.04 [-0.01, 0.11] pp | 12 | 6 |
| H − CD | -0.04 [-0.12, 0.04] pp | 16 | 22 |

Crossings use the frozen Stage 3 interpolation and censoring rules. Left and right counts refer to the bootstrap draws.

| Cell | Arm | 1% crossing (dB) | 95% interval (dB) | Left censored | Right censored |
| --- | --- | --- | --- | --- | --- |
| U_300 | F0 | 7.000 | [6.000, 7.707] | 0 | 0 |
| U_300 | CD | 5.153 | [-∞, 5.205] | 533 | 0 |
| U_300 | Z | 5.153 | [-∞, 5.205] | 545 | 0 |
| U_300 | H | 5.140 | [-∞, 5.194] | 1045 | 0 |
| U_300 | S | 6.000 | [5.667, 6.250] | 0 | 0 |
| U_500 | F0 | 6.625 | [6.458, 6.688] | 0 | 0 |
| U_500 | CD | 6.214 | [6.164, 6.242] | 0 | 0 |
| U_500 | Z | 6.210 | [6.153, 6.239] | 0 | 0 |
| U_500 | H | 6.214 | [6.164, 6.242] | 0 | 0 |
| U_500 | S | 6.328 | [6.269, 6.454] | 0 | 0 |
| G_300 | F0 | 6.422 | [6.097, 6.834] | 0 | 0 |
| G_300 | CD | 5.125 | [-∞, 5.188] | 2007 | 0 |
| G_300 | Z | 5.140 | [-∞, 5.194] | 1065 | 0 |
| G_300 | H | 5.106 | [-∞, 5.181] | 3484 | 0 |
| G_300 | S | 5.822 | [5.640, 6.097] | 0 | 0 |
| G_500 | F0 | 6.869 | [6.500, 7.212] | 0 | 0 |
| G_500 | CD | 6.279 | [6.194, 6.438] | 0 | 0 |
| G_500 | Z | 6.285 | [6.205, 6.439] | 0 | 0 |
| G_500 | H | 6.287 | [6.210, 6.440] | 0 | 0 |
| G_500 | S | 6.500 | [6.331, 6.853] | 0 | 0 |

| Cell | Contrast | Point bounds (dB) | 95% interval (dB) |
| --- | --- | --- | --- |
| U_300 | Z − CD | [0.000, 0.000] | [-∞, +∞] |
| U_300 | H − CD | [-0.013, -0.013] | [-∞, +∞] |
| U_500 | Z − CD | [-0.004, -0.004] | [-0.017, 0.000] |
| U_500 | H − CD | [0.000, 0.000] | [0.000, 0.000] |
| G_300 | Z − CD | [0.015, 0.015] | [-∞, +∞] |
| G_300 | H − CD | [-0.019, -0.019] | [-∞, +∞] |
| G_500 | Z − CD | [0.006, 0.006] | [0.000, 0.017] |
| G_500 | H − CD | [0.008, 0.008] | [-0.003, 0.025] |

Per-signal-to-noise-ratio frame failure counts are in the secondary cell records. [results.json](results.json)

### Support-disagreement readout

Z and CD differed in their delay multisets on 263 triggered keys. The magnitude ratios use the gain supplied to the detector at each exact true-delay match.

| Arm | Nontrue-delay atoms | Nontrue atoms per key → keys | Matched atoms | Gain ratio Q1 | Gain ratio median | Gain ratio Q3 |
| --- | --- | --- | --- | --- | --- | --- |
| CD | 218 | 0 → 79, 1 → 153, 2 → 28, 3 → 3 | 1886 | 0.884 | 0.935 | 0.973 |
| Z | 293 | 0 → 28, 1 → 180, 2 → 52, 3 → 3 | 1811 | 1.082 | 1.141 | 1.191 |

## Frozen verdicts

The first-edit anchors passed. The S threshold requires its lower bound to be at least 80.00% and the CD threshold requires its upper bound to be at most 5.00%.

| Endpoint | Frozen label | Estimate [95% interval] |
| --- | --- | --- |
| P-A Z | SUPPORTED | 1.84 [0.99, 2.80] % |
| P-A H | SUPPORTED | 2.56 [1.56, 3.69] % |
| P-B Z − CD | EQUIVALENT | -0.31 [-0.74, 0.10] pp |

H − CD is a secondary rescue contrast. The ±3 percentage-point P-B margin applies to the pooled triggered keys on this grid.

## Untested explanations

**L confidence.** Removing the covariance term may change which support the search selects, and the joint detector may attenuate or amplify the decoding effect of those changes. Z-sel probes gain initialization on Z’s selected support. Gain ratios and delay counts describe the support-disagreement subset. The relative contribution of support selection and gain initialization across alternative supports remains untested.
