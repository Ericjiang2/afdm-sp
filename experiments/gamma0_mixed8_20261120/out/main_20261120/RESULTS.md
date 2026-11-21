# MIXED8 Γ = 0 support exchange

## Observation

MIXED8 at pilot fraction 0.5 and 7 dB. Frames 2200–2799 contributed 600 paired observations, including 366 F0 triggers. Primary endpoints cover all frames.

Secondary intervals are 95% paired physical-frame bootstrap intervals using 20,000 shared draws (seed 20261127).

| Execution | Recorded value |
| --- | --- |
| Frozen protocol revision | 52b27bd8d54b5e60179dbdf940500c0171ebbbb2 |
| Producing revision | 5051bcbaac5143589f32d90d017e3f7942ab55c0 |
| Wall seconds | 51.58 |
| CPU core-hours | 0.276221 |

### Frame errors and paired differences

| Arm | Failed frames / 600 | Frame error rate [95% interval] |
| --- | --- | --- |
| F0 | 366 | 61.00 [57.00, 65.00] % |
| CD | 33 | 5.50 [3.83, 7.33] % |
| Z | 39 | 6.50 [4.67, 8.50] % |
| H | 39 | 6.50 [4.67, 8.50] % |
| S | 158 | 26.33 [22.83, 30.00] % |
| A2g | 331 | 55.17 [51.17, 59.17] % |
| Z-sel | 37 | 6.17 [4.33, 8.17] % |
| TRUE_GEOMETRY | 0 | 0.00 [0.00, 0.00] % |

| Contrast | Frame error rate difference [95% interval] | Only first failed | Only second failed |
| --- | --- | --- | --- |
| Z − CD | +1.00 [-0.17, 2.17] pp | 10 | 4 |
| H − CD | +1.00 [-0.33, 2.33] pp | 12 | 6 |
| A2g − Z | +48.67 [44.67, 52.67] pp | 292 | 0 |
| Z-sel − Z | -0.33 [-0.83, 0.00] pp | 0 | 2 |
| F0 − TRUE_GEOMETRY | +61.00 [57.00, 65.00] pp | 366 | 0 |
| CD − TRUE_GEOMETRY | +5.50 [3.83, 7.33] pp | 33 | 0 |
| Z − TRUE_GEOMETRY | +6.50 [4.67, 8.50] pp | 39 | 0 |
| H − TRUE_GEOMETRY | +6.50 [4.67, 8.50] pp | 39 | 0 |
| S − TRUE_GEOMETRY | +26.33 [22.83, 30.00] pp | 158 | 0 |
| A2g − TRUE_GEOMETRY | +55.17 [51.17, 59.17] pp | 331 | 0 |
| Z-sel − TRUE_GEOMETRY | +6.17 [4.33, 8.17] pp | 37 | 0 |

### Occupancy, omitted energy and singleton phantoms

A true doublet delay is occupied when it has at least two fitted atoms. The energy fraction divides pooled omitted energy by pooled true energy at each separation.

| Arm | 0.35-bin occupied frames | 0.75-bin occupied frames | 0.35-bin omitted [95% interval] | 0.75-bin omitted [95% interval] |
| --- | --- | --- | --- | --- |
| F0 | 0 (0.00 [0.00, 0.00] %) | 0 (0.00 [0.00, 0.00] %) | 9.33 [8.46, 10.29] % | 27.32 [25.93, 28.76] % |
| CD | 223 (37.17 [33.33, 41.17] %) | 361 (60.17 [56.17, 64.17] %) | 3.63 [3.19, 4.11] % | 5.99 [5.35, 6.65] % |
| Z | 215 (35.83 [32.00, 39.83] %) | 361 (60.17 [56.17, 64.17] %) | 3.82 [3.35, 4.32] % | 6.09 [5.45, 6.74] % |
| H | 217 (36.17 [32.33, 40.17] %) | 363 (60.50 [56.50, 64.50] %) | 3.75 [3.30, 4.24] % | 6.04 [5.41, 6.69] % |
| S | 60 (10.00 [7.67, 12.50] %) | 251 (41.83 [37.83, 45.67] %) | 8.05 [7.22, 8.94] % | 11.03 [9.99, 12.14] % |
| A2g | 0 (0.00 [0.00, 0.00] %) | 0 (0.00 [0.00, 0.00] %) | 9.28 [8.41, 10.24] % | 27.27 [25.88, 28.71] % |
| Z-sel | 215 (35.83 [32.00, 39.83] %) | 361 (60.17 [56.17, 64.17] %) | 3.82 [3.35, 4.32] % | 6.09 [5.45, 6.74] % |
| TRUE_GEOMETRY | 600 (100.00 [100.00, 100.00] %) | 600 (100.00 [100.00, 100.00] %) | 0.00 [0.00, 0.00] % | 0.00 [0.00, 0.00] % |

Singleton phantom counts include only the four true singleton delays. Each cell below gives the number of affected frames followed by the total count of affected delay groups.

| Arm | Any spacing | Dirichlet magnitude ≥ 0.5 | Doppler gap ≤ 0.25 bin |
| --- | --- | --- | --- |
| F0 | 0 / 0 | 0 / 0 | 0 / 0 |
| CD | 0 / 0 | 0 / 0 | 0 / 0 |
| Z | 0 / 0 | 0 / 0 | 0 / 0 |
| H | 2 / 2 | 0 / 0 | 0 / 0 |
| S | 333 / 397 | 333 / 397 | 333 / 397 |
| A2g | 0 / 0 | 0 / 0 | 0 / 0 |
| Z-sel | 0 / 0 | 0 / 0 | 0 / 0 |
| TRUE_GEOMETRY | 0 / 0 | 0 / 0 | 0 / 0 |

### First accepted exchange

| Arm | Existing delay | New delay | No accepted exchange |
| --- | --- | --- | --- |
| CD | 366 (61.00%) | 0 (0.00%) | 234 (39.00%) |
| Z | 366 (61.00%) | 0 (0.00%) | 234 (39.00%) |
| H | 366 (61.00%) | 0 (0.00%) | 234 (39.00%) |
| S | 366 (61.00%) | 0 (0.00%) | 234 (39.00%) |
| A2g | 0 (0.00%) | 359 (59.83%) | 241 (40.17%) |
| Z-sel | 366 (61.00%) | 0 (0.00%) | 234 (39.00%) |

Z and CD accepted the same first slot and atom on 313/600 frames (52.17%). Both had no accepted exchange on 234/600. Agreement including those frames was 91.17%.

### Frames with discordant occupancy at the true 0.35-bin doublet delay

Each direction conditions on which arm occupied the delay with at least two fitted atoms. Omitted energy is the residual after projection onto the fitted Doppler components at that delay.

| Subgroup | Frames | Z omitted | CD omitted | Z − CD (pp) | Mean paired Z − CD omitted energy |
| --- | --- | --- | --- | --- | --- |
| Z only | 6 | 0.30% | 9.86% | -9.56 | -0.0108623 |
| CD only | 14 | 13.67% | 0.82% | +12.85 | +0.0167389 |

| Subgroup | Arm | Fitted → nearest true median (bins) | True → nearest fitted median (bins) | Frames with no fitted atom |
| --- | --- | --- | --- | --- |
| Z only | Z | 0.1088 | 0.1088 | 0 |
| Z only | CD | 0.1573 | 0.1799 | 0 |
| CD only | Z | 0.1551 | 0.1870 | 0 |
| CD only | CD | 0.1267 | 0.1372 | 0 |

Doppler distances are pooled over atoms on frames with a nonempty fit. Each true or fitted Doppler is compared with its nearest counterpart independently. Per-frame true Dopplers, fitted Dopplers and gains, and paired omission values are in [results.json](results.json).

## Frozen verdicts

**Anchors PASS.** CD frame error rate was 5.50% against [3%, 9%]. S − CD was +20.83 pp against the minimum +10 pp. Both checks use unconditional point estimates.

Primary intervals use Newcombe (1998), method 10, at 95%. [Method 10 and Table III](https://www.site.uottawa.ca/~nat/Courses/csi5388/Newcombe.1998.pdf)

| Endpoint | Z − CD [95% interval] | Only Z | Only CD | Margin | Frozen label |
| --- | --- | --- | --- | --- | --- |
| P-F (Frame error rate) | +1.00 [-0.33, 2.43] pp | 10 | 4 | ±1.5 pp | INCONCLUSIVE |
| P-D (0.35-bin occupancy) | -1.33 [-2.83, 0.16] pp | 6 | 14 | ±3 pp | EQUIVALENT |

The pair of endpoint labels failed the frozen joint equivalence criterion.

## Untested explanation

**Low confidence.** Dropping Γ reduces the penalty for fitting a difference between nearby Doppler components. An extra fitted atom may represent the true channel waveform better or fit residual interference. The paired omission and Doppler distances describe waveform and geometry accuracy on the occupancy-disagreement subsets. Z-sel probes gain initialization on Z’s fixed geometry.
