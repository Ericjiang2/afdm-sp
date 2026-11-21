# Edit budget at low pilot fraction

24,000 keys over 400 physical frames. CPU cost 3.9488 core-hours.

Freeze commit `cf582ab743216a79ad16dfc0c56fd66be9dba240`. Launch commit `09d9485043d8558158a4b330e76637753a7b689c`.
Raw rows stay on deinlab. [Raw-row MD5 list](REMOTE_ROWS_MD5.txt) · [Machine-readable results](results.json)

## Observation

The gain is the paired CD4-minus-CD2 rescue-rate difference among triggered keys. The two pilot fractions use the matched signal-to-noise ratio (SNR) windows in §7. The 95% intervals jointly resample physical frames. The interaction describes the triggered populations the two receivers face.

| ρ | Triggered keys | Triggered frames | Discordant frames | New rescues | New harms | Gain (percentage points) | 95% interval | Undefined draws |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.15 | 771 | 210 | 25 | 41 | 1 | 5.188 | [3.216, 7.311] | 0 |
| 0.30 | 718 | 336 | 10 | 8 | 3 | 0.696 | [-0.272, 1.700] | 0 |
| Difference of gains | — | — | — | — | — | 4.492 | [2.473, 6.633] | 0 |

### Conditional rescue

Astra eligibility requires a triggered key with a CD2 information-bit error and three or four distinct true delays missing at entry.

| ρ | Eligible keys | Eligible frames | CD4 rescues | Rescue rate |
| --- | --- | --- | --- | --- |
| 0.15 | 99 | 45 | 32 | 32.32% |
| 0.30 | 47 | 37 | 7 | 14.89% |

Astra ≥10% at ρ=.15 **met**. Above matched ρ=.30 **met**. Joint **met**.
Claude CD4 rescue ≥90% at ρ=.15 **missed**. CD4 rescued 686 of 771 triggered keys (88.98%).

| ρ | SNR (dB) | Triggered keys | CD2 rescue | CD4 rescue | CD6 rescue | A2-2 rescue | A2-6 rescue |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.15 | 6, 6.5, 7, 8 | 771 | 83.79% | 88.98% | 88.85% | 60.05% | 68.35% |
| 0.20 | 6, 6.5, 7, 8 | 293 | 92.49% | 95.22% | 95.22% | 67.58% | 75.77% |
| 0.30 | 4.5, 5 | 718 | 73.40% | 74.09% | 74.09% | 21.45% | 21.17% |

### 1% frame-error-rate crossings

Per-scenario crossings use the frozen rho-sweep rule. Pooled crossings are the equal-weight average of the U and G crossing bounds. Infinite endpoints indicate censoring.

| Scenario | ρ | Arm | Crossing (dB) | 95% interval (dB) | Left-censored draws | Right-censored draws |
| --- | --- | --- | --- | --- | --- | --- |
| U | 0.15 | F0 | [10.000, +∞) | [10.000, +∞) | 0 | 19993 |
| U | 0.15 | CD2 | 8.575 | [7.000, 9.585] | 0 | 80 |
| U | 0.15 | CD4 | 8.000 | [6.500, 8.500] | 0 | 0 |
| U | 0.15 | CD6 | 8.194 | [6.500, 8.612] | 0 | 0 |
| U | 0.15 | A2-2 | 8.884 | [8.326, 9.688] | 0 | 80 |
| U | 0.15 | A2-6 | 8.738 | [8.000, 9.643] | 0 | 80 |
| U | 0.20 | F0 | 10.000 | [8.857, +∞) | 0 | 7494 |
| U | 0.20 | CD2 | 5.830 | [5.185, 7.437] | 0 | 80 |
| U | 0.20 | CD4 | 5.353 | [4.935, 7.437] | 0 | 80 |
| U | 0.20 | CD6 | 5.353 | [4.935, 7.437] | 0 | 80 |
| U | 0.20 | A2-2 | 7.761 | [7.000, 9.321] | 0 | 80 |
| U | 0.20 | A2-6 | 7.226 | [6.685, 7.779] | 0 | 80 |
| U | 0.30 | F0 | 7.369 | [6.223, 8.874] | 0 | 80 |
| U | 0.30 | CD2 | 5.211 | [5.048, 5.417] | 0 | 0 |
| U | 0.30 | CD4 | 5.199 | [5.000, 5.414] | 0 | 0 |
| U | 0.30 | CD6 | 5.199 | [5.000, 5.414] | 0 | 0 |
| U | 0.30 | A2-2 | 6.292 | [5.770, 7.097] | 0 | 0 |
| U | 0.30 | A2-6 | 6.113 | [5.744, 6.389] | 0 | 0 |
| G | 0.15 | F0 | [10.000, +∞) | [10.000, +∞) | 0 | 20000 |
| G | 0.15 | CD2 | 9.476 | [8.000, +∞) | 0 | 3745 |
| G | 0.15 | CD4 | 8.326 | [7.422, 8.655] | 0 | 0 |
| G | 0.15 | CD6 | 8.326 | [7.422, 8.655] | 0 | 0 |
| G | 0.15 | A2-2 | [10.000, +∞) | [8.884, +∞) | 0 | 11326 |
| G | 0.15 | A2-6 | 9.187 | [8.277, +∞) | 0 | 1087 |
| G | 0.20 | F0 | [10.000, +∞) | [9.585, +∞) | 0 | 18014 |
| G | 0.20 | CD2 | 6.613 | [5.500, 6.889] | 0 | 0 |
| G | 0.20 | CD4 | 5.853 | [5.223, 6.830] | 0 | 0 |
| G | 0.20 | CD6 | 5.853 | [5.223, 6.830] | 0 | 0 |
| G | 0.20 | A2-2 | 7.398 | [7.000, 7.828] | 0 | 0 |
| G | 0.20 | A2-6 | 7.163 | [6.685, 7.327] | 0 | 0 |
| G | 0.30 | F0 | 7.244 | [6.389, 8.738] | 0 | 39 |
| G | 0.30 | CD2 | 5.185 | [5.000, 5.407] | 0 | 0 |
| G | 0.30 | CD4 | 5.106 | [4.909, 5.181] | 0 | 0 |
| G | 0.30 | CD6 | 5.106 | [4.909, 5.181] | 0 | 0 |
| G | 0.30 | A2-2 | 5.924 | [5.700, 6.718] | 0 | 0 |
| G | 0.30 | A2-6 | 5.917 | [5.681, 6.718] | 0 | 0 |

| ρ | Arm | Pooled crossing (dB) | 95% interval (dB) |
| --- | --- | --- | --- |
| 0.15 | F0 | [10.000, +∞) | [10.000, +∞) |
| 0.15 | CD2 | 9.026 | [8.050, +∞) |
| 0.15 | CD4 | 8.163 | [7.185, 8.493] |
| 0.15 | CD6 | 8.260 | [7.185, 8.539] |
| 0.15 | A2-2 | [9.442, +∞) | [8.825, +∞) |
| 0.15 | A2-6 | 8.962 | [8.351, +∞) |
| 0.20 | F0 | [10.000, +∞) | [9.400, +∞) |
| 0.20 | CD2 | 6.222 | [5.541, 6.964] |
| 0.20 | CD4 | 5.603 | [5.250, 6.685] |
| 0.20 | CD6 | 5.603 | [5.250, 6.685] |
| 0.20 | A2-2 | 7.579 | [7.173, 8.364] |
| 0.20 | A2-6 | 7.195 | [6.833, 7.494] |
| 0.30 | F0 | 7.306 | [6.440, 8.359] |
| 0.30 | CD2 | 5.198 | [5.054, 5.361] |
| 0.30 | CD4 | 5.152 | [5.019, 5.274] |
| 0.30 | CD6 | 5.152 | [5.019, 5.274] |
| 0.30 | A2-2 | 6.108 | [5.785, 6.657] |
| 0.30 | A2-6 | 6.015 | [5.766, 6.464] |

### Agy crossing predictions

Each secondary threshold uses the observed crossing bounds. The bootstrap intervals show sampling uncertainty. A point bound straddling a threshold leaves the criterion unresolved.

| ρ | CD2→CD6 gain (dB) | 95% interval (dB) | Threshold (dB) | Status |
| --- | --- | --- | --- | --- |
| 0.15 | 0.766 | [0.292, +∞) | 2.5 | missed |
| 0.20 | 0.618 | [0.065, 0.894] | 0.8 | missed |

CD6 optimal tested ρ < .25 **missed**. Possible minimizers 0.30. Simultaneous 95% compatible set 0.20, 0.30.
Best tested CD6 crossing < 5 dB **missed**. Crossing 5.152 dB, 95% interval [5.018, 5.274] dB.
Smaller scalar than CD6 improvement across the tested ρ values **missed**.

| ρ | CD2→CD6 gain (dB) | A2-2→A2-6 gain (dB) | Scalar minus CD gain (dB) | 95% interval of difference (dB) | Scalar gain smaller |
| --- | --- | --- | --- | --- | --- |
| 0.15 | 0.766 | [0.480, +∞) | [-0.286, +∞) | (−∞, +∞) | unresolved |
| 0.20 | 0.618 | 0.385 | -0.234 | [-0.483, 0.619] | met |
| 0.30 | 0.045 | 0.093 | 0.048 | [-0.235, 0.414] | missed |

### Extra edits and decoder outcomes

Counts pool both scenarios and all registered SNRs. Cap exhaustion and net true-delay gain use triggered keys. Edit labels count accepted extra edits.

| ρ | Arm | Triggered keys | Cap exhausted | Steps 3–4 attempted / accepted | Steps 5–6 attempted / accepted | True / phantom / other accepted | Mean net true-delay gain |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.15 | CD2 | 3478 | 3397 (97.67%) | 0 / 0 | 0 / 0 | 0 / 0 / 0 | 1.644 |
| 0.15 | CD4 | 3478 | 2021 (58.11%) | 6380 / 5004 | 0 / 0 | 1567 / 128 / 3309 | 2.089 |
| 0.15 | CD6 | 3478 | 305 (8.77%) | 6380 / 5004 | 2992 / 1276 | 1630 / 161 / 4489 | 2.104 |
| 0.15 | A2-2 | 3478 | 3471 (99.80%) | 0 / 0 | 0 / 0 | 0 / 0 / 0 | 0.222 |
| 0.15 | A2-6 | 3478 | 430 (12.36%) | 6754 / 5826 | 3847 / 1734 | 825 / 4622 / 2113 | 0.291 |
| 0.20 | CD2 | 2575 | 2392 (92.89%) | 0 / 0 | 0 / 0 | 0 / 0 / 0 | 1.477 |
| 0.20 | CD4 | 2575 | 1073 (41.67%) | 4244 / 2925 | 0 / 0 | 699 / 41 / 2185 | 1.743 |
| 0.20 | CD6 | 2575 | 93 (3.61%) | 4244 / 2925 | 1481 / 501 | 717 / 55 / 2654 | 1.749 |
| 0.20 | A2-2 | 2575 | 2536 (98.49%) | 0 / 0 | 0 / 0 | 0 / 0 / 0 | 0.083 |
| 0.20 | A2-6 | 2575 | 172 (6.68%) | 4776 / 3748 | 2143 / 807 | 307 / 2740 / 1508 | 0.010 |
| 0.30 | CD2 | 2411 | 1791 (74.28%) | 0 / 0 | 0 / 0 | 0 / 0 / 0 | 0.984 |
| 0.30 | CD4 | 2411 | 381 (15.80%) | 2780 / 1370 | 0 / 0 | 160 / 14 / 1196 | 1.049 |
| 0.30 | CD6 | 2411 | 18 (0.75%) | 2780 / 1370 | 464 / 101 | 163 / 14 / 1294 | 1.050 |
| 0.30 | A2-2 | 2411 | 2258 (93.65%) | 0 / 0 | 0 / 0 | 0 / 0 / 0 | -0.224 |
| 0.30 | A2-6 | 2411 | 57 (2.36%) | 3981 / 2640 | 1207 / 347 | 44 / 1867 / 1076 | -0.453 |

| ρ | Arm pair | Fail→success | Success→fail | Success→success | Fail→fail |
| --- | --- | --- | --- | --- | --- |
| 0.15 | F0→CD2 | 1979 | 0 | 1 | 1498 |
| 0.15 | F0→CD4 | 2124 | 0 | 1 | 1353 |
| 0.15 | F0→CD6 | 2124 | 0 | 1 | 1353 |
| 0.15 | F0→A2-2 | 898 | 0 | 1 | 2579 |
| 0.15 | F0→A2-6 | 1047 | 0 | 1 | 2430 |
| 0.15 | CD2→CD4 | 154 | 9 | 1971 | 1344 |
| 0.15 | CD2→CD6 | 157 | 12 | 1968 | 1341 |
| 0.15 | CD2→A2-2 | 0 | 1081 | 899 | 1498 |
| 0.15 | CD2→A2-6 | 2 | 934 | 1046 | 1496 |
| 0.15 | CD4→CD6 | 4 | 4 | 2121 | 1349 |
| 0.15 | CD4→A2-2 | 0 | 1226 | 899 | 1353 |
| 0.15 | CD4→A2-6 | 0 | 1077 | 1048 | 1353 |
| 0.15 | CD6→A2-2 | 0 | 1226 | 899 | 1353 |
| 0.15 | CD6→A2-6 | 0 | 1077 | 1048 | 1353 |
| 0.15 | A2-2→A2-6 | 167 | 18 | 881 | 2412 |
| 0.20 | F0→CD2 | 1345 | 0 | 1 | 1229 |
| 0.20 | F0→CD4 | 1404 | 0 | 1 | 1170 |
| 0.20 | F0→CD6 | 1403 | 0 | 1 | 1171 |
| 0.20 | F0→A2-2 | 529 | 0 | 1 | 2045 |
| 0.20 | F0→A2-6 | 602 | 0 | 1 | 1972 |
| 0.20 | CD2→CD4 | 63 | 4 | 1342 | 1166 |
| 0.20 | CD2→CD6 | 62 | 4 | 1342 | 1167 |
| 0.20 | CD2→A2-2 | 0 | 816 | 530 | 1229 |
| 0.20 | CD2→A2-6 | 0 | 743 | 603 | 1229 |
| 0.20 | CD4→CD6 | 0 | 1 | 1404 | 1170 |
| 0.20 | CD4→A2-2 | 0 | 875 | 530 | 1170 |
| 0.20 | CD4→A2-6 | 0 | 802 | 603 | 1170 |
| 0.20 | CD6→A2-2 | 0 | 874 | 530 | 1171 |
| 0.20 | CD6→A2-6 | 0 | 801 | 603 | 1171 |
| 0.20 | A2-2→A2-6 | 76 | 3 | 527 | 1969 |
| 0.30 | F0→CD2 | 765 | 0 | 0 | 1646 |
| 0.30 | F0→CD4 | 776 | 0 | 0 | 1635 |
| 0.30 | F0→CD6 | 776 | 0 | 0 | 1635 |
| 0.30 | F0→A2-2 | 253 | 0 | 0 | 2158 |
| 0.30 | F0→A2-6 | 256 | 0 | 0 | 2155 |
| 0.30 | CD2→CD4 | 14 | 3 | 762 | 1632 |
| 0.30 | CD2→CD6 | 14 | 3 | 762 | 1632 |
| 0.30 | CD2→A2-2 | 0 | 512 | 253 | 1646 |
| 0.30 | CD2→A2-6 | 0 | 509 | 256 | 1646 |
| 0.30 | CD4→CD6 | 0 | 0 | 776 | 1635 |
| 0.30 | CD4→A2-2 | 0 | 523 | 253 | 1635 |
| 0.30 | CD4→A2-6 | 0 | 520 | 256 | 1635 |
| 0.30 | CD6→A2-2 | 0 | 523 | 253 | 1635 |
| 0.30 | CD6→A2-6 | 0 | 520 | 256 | 1635 |
| 0.30 | A2-2→A2-6 | 10 | 7 | 246 | 2148 |

## Frozen verdict

- Direction **supported**
- Practical size **meaningful**
- Matched equivalence at ρ=.30 **unchanged**

## Untested explanation

A plausible contributor is that restoring distinct true delays in extra edits can improve the decoder input (confidence M).
