# MIXED8 Γ = 0 frame error rate replication

## Observation

The six receivers processed 2,400 paired frames (2800–5199) at ρ = 0.5 and 7 dB. The shared F0 decoder triggered continuation on 1,558 frames.

| Execution | Recorded value |
| --- | --- |
| Frozen protocol revision | e44f050aa7d894c17c88d37ced40f05ed9a97f0b |
| Producing revision | 7f46fba29bcd87d2047e0116ad8d64edd4bf7def |
| Single-thread workers | 21 |
| Idle physical cores left at kickoff | 41 |
| Wall seconds | 141.67 |
| CPU core-hours | 0.742502 |

### Frame errors and paired differences

Secondary rate and energy intervals use 20,000 paired physical-frame bootstrap draws (seed 20261127). The primary and 0.35-bin occupancy contrasts use 95% Newcombe method 10 intervals.

On the new frames, the Z − CD frame error rate (FER) difference was +0.54 [-0.03, 1.13] pp. The paired failures were 30 under Z only, 17 under CD only, 137 under both, and 2216 under neither.

| Arm | Failed frames | FER [95% interval] |
| --- | --- | --- |
| F0 | 1558 | 64.92 [63.04, 66.79] % |
| CD | 154 | 6.42 [5.46, 7.42] % |
| Z | 167 | 6.96 [5.96, 8.00] % |
| H | 170 | 7.08 [6.08, 8.12] % |
| S | 704 | 29.33 [27.50, 31.13] % |
| Z-sel | 167 | 6.96 [5.96, 8.00] % |

| Contrast | FER difference [95% interval] | Only first failed | Only second failed |
| --- | --- | --- | --- |
| H − CD | +0.67 [0.08, 1.25] pp | 35 | 19 |
| Z-sel − Z | +0.00 [-0.25, 0.25] pp | 4 | 4 |

Across the 3,000-frame descriptive pool, including the earlier 600 separately bound frames, Z − CD was +0.63 pp (40 Z-only and 21 CD-only failures).

### Doublet occupancy, omitted energy, and singleton phantoms

A true doublet delay is occupied when at least two fitted atoms share its delay. Each energy fraction is pooled omitted energy divided by pooled true energy.

| Arm | 0.35-bin occupied frames | 0.75-bin occupied frames | 0.35-bin omitted [95% interval] | 0.75-bin omitted [95% interval] |
| --- | --- | --- | --- | --- |
| F0 | 0 (0.00 [0.00, 0.00] %) | 0 (0.00 [0.00, 0.00] %) | 9.75 [9.29, 10.24] % | 28.74 [28.01, 29.47] % |
| CD | 959 (39.96 [38.00, 41.92] %) | 1540 (64.17 [62.29, 66.04] %) | 3.46 [3.25, 3.68] % | 5.63 [5.33, 5.94] % |
| Z | 922 (38.42 [36.50, 40.33] %) | 1539 (64.12 [62.25, 66.00] %) | 3.67 [3.45, 3.90] % | 5.75 [5.45, 6.06] % |
| H | 961 (40.04 [38.08, 42.00] %) | 1540 (64.17 [62.29, 66.08] %) | 3.54 [3.33, 3.77] % | 5.70 [5.40, 6.01] % |
| S | 271 (11.29 [10.00, 12.58] %) | 1060 (44.17 [42.21, 46.13] %) | 8.27 [7.83, 8.74] % | 11.16 [10.63, 11.71] % |
| Z-sel | 922 (38.42 [36.50, 40.33] %) | 1539 (64.12 [62.25, 66.00] %) | 3.67 [3.45, 3.90] % | 5.75 [5.45, 6.06] % |

At 0.35 bin, Z − CD occupancy was -1.54 [-2.27, -0.81] pp, with 21 Z-only and 58 CD-only occupied frames.

Singleton phantoms occur when extra atoms occupy a true singleton delay. Entries show affected frames [95% bootstrap interval for the rate] and total affected delay groups.

| Arm | Any spacing | Dirichlet magnitude ≥ 0.5 | Doppler gap ≤ 0.25 bin |
| --- | --- | --- | --- |
| F0 | 0 (0.00 [0.00, 0.00] %) / 0 | 0 (0.00 [0.00, 0.00] %) / 0 | 0 (0.00 [0.00, 0.00] %) / 0 |
| CD | 3 (0.12 [0.00, 0.29] %) / 3 | 0 (0.00 [0.00, 0.00] %) / 0 | 0 (0.00 [0.00, 0.00] %) / 0 |
| Z | 5 (0.21 [0.04, 0.42] %) / 5 | 1 (0.04 [0.00, 0.12] %) / 1 | 1 (0.04 [0.00, 0.12] %) / 1 |
| H | 3 (0.12 [0.00, 0.29] %) / 3 | 0 (0.00 [0.00, 0.00] %) / 0 | 0 (0.00 [0.00, 0.00] %) / 0 |
| S | 1427 (59.46 [57.50, 61.42] %) / 1716 | 1427 (59.46 [57.50, 61.42] %) / 1716 | 1427 (59.46 [57.50, 61.42] %) / 1716 |
| Z-sel | 5 (0.21 [0.04, 0.42] %) / 5 | 1 (0.04 [0.00, 0.12] %) / 1 | 1 (0.04 [0.00, 0.12] %) / 1 |

### Frames with discordant occupancy at the true 0.35-bin doublet delay

Each direction conditions on which arm occupied the delay with at least two fitted atoms. Omitted energy is the residual after projection onto the fitted Doppler components at that delay.

| Subgroup | Frames | Z omitted | CD omitted | Z − CD (pp) | Mean paired Z − CD omitted energy |
| --- | --- | --- | --- | --- | --- |
| Z only | 21 | 0.47% | 10.94% | -10.47 | -0.0129667 |
| CD only | 58 | 19.30% | 0.63% | +18.67 | +0.0185967 |

| Subgroup | Arm | Fitted → nearest true median (bins) | True → nearest fitted median (bins) | Frames with no fitted atom |
| --- | --- | --- | --- | --- |
| Z only | Z | 0.0918 | 0.0918 | 0 |
| Z only | CD | 0.1526 | 0.1955 | 0 |
| CD only | Z | 0.1435 | 0.1969 | 0 |
| CD only | CD | 0.0931 | 0.0931 | 0 |

Doppler distances are pooled over atoms on frames with a nonempty fit. Each true or fitted Doppler is compared with its nearest counterpart independently. Per-frame true Dopplers, fitted Dopplers and gains, and paired omission values are in [results.json](results.json).

## Frozen verdicts

Anchors **PASS**. CD FER was 6.42% against [3%, 9%]. S − CD was +22.92 pp against a minimum of +10 pp. Both use the full fresh panel.

- Q1 (CD superiority) **NO_DIFFERENCE_SHOWN**.
- Q2 (equivalence within ±1.5 pp) **EQUIVALENT**.

Both verdicts use the fresh-frame interval reported above.

## Untested explanation

**Low confidence.** The covariance term Γ may suppress unstable exchanges between close Doppler components. Such exchanges can affect final support and detection even when the number of fitted atoms is unchanged. The occupancy-conditioned energy comparisons describe selected frame subsets. Z-sel probes the gain refit on fixed Z support. These observations leave the proposed causal mechanism open.
