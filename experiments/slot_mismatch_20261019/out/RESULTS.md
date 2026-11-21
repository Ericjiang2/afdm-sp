# Slot-count mismatch confirmation, Phase 3

[Protocol](../PROTOCOL.md) frozen in `9b633ce9df020158d51621600d7b6eab3b65395d`. The complete run ended with `DONE 200 30.723700`. All 200 shard receipts reported completion. The 104,000 receiver-input keys comprise 32,000 each in M, T6 and T10 and 8,000 in N, with physical frame IDs 10000–10999 and SNR 4.5–8.0 dB at 0.5 dB increments. The run used 30.724 of 40 permitted core-hours.

[Results JSON](main_20261118/results.json) records the arguments, script checksums, grid, all FER counts and bootstrap outputs. [Run configuration](main_20261118/RUN_CONFIG.json) and [completion receipt](main_20261118/main_receipt.json) identify the frozen sources. All 200 gzip MD5s, exact shard key coverage and required F0/continuation branches passed the archive checks. The raw `rows_shard000.jsonl.gz` through `rows_shard199.jsonl.gz` remain at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/slot_mismatch_20261019/out/main_20261118/` on deinlab. [Per-shard MD5 manifest](main_20261118/REMOTE_ROWS_MD5.txt), manifest MD5 `c7c895f191ed105f12de52c9a8824e69`. Phase 3 read the archive without invoking a receiver.

## 1. Observations

### FER = .01 crossings

B selects A1c on final nonzero F0 syndrome and F0 otherwise. A3 uses the true channel at the supplied variance. Entries give the first crossing in dB. An open upper endpoint indicates that the last measured FER is above .01. The JSON includes the 1,000-key FER numerator at every grid point for each curve.

| Family | Cell | B₆ | B₈ | B₁₀ | B₁₂ | A3 |
| --- | --- | --- | --- | --- | --- | --- |
| M | U, 0.3 | [8.000, +∞] | 5.244 | 5.158 | 5.158 | 4.658 |
| M | U, 0.5 | [8.000, +∞] | 6.225 | 6.347 | 6.331 | 6.142 |
| M | G, 0.3 | [8.000, +∞] | 5.151 | 5.174 | 5.158 | 4.679 |
| M | G, 0.5 | [8.000, +∞] | 6.219 | 6.202 | 6.250 | 6.121 |
| T6 | U, 0.3 | — | 4.878 | — | — | 4.647 |
| T6 | U, 0.5 | — | 6.168 | — | — | 6.128 |
| T6 | G, 0.3 | — | 4.790 | — | — | 4.668 |
| T6 | G, 0.5 | — | 6.210 | — | — | 6.186 |
| T10 | U, 0.3 | — | 7.132 | — | — | 4.694 |
| T10 | U, 0.5 | — | [8.000, +∞] | — | — | 6.174 |
| T10 | G, 0.3 | — | 7.500 | — | — | 4.680 |
| T10 | G, 0.5 | — | [8.000, +∞] | — | — | 6.165 |
| N | G, 0.3 | — | 6.339 | — | 6.150 | 5.000 |

In N, the mean estimated-to-true variance ratio ranges from 0.987 to 0.995 across SNRs, and its within-SNR SD ranges from 0.118 to 0.225. No estimate hit the variance floor among the 8,000 keys. The A3 crossing moves from 4.679 dB under known variance to 5.000 dB under the estimate on the same G/0.3 keys.

### Q2 primary common-trigger set

The comparison is on the same 7,462 of 24,000 M keys from 1,000 physical frames at 4.5–7 dB. Final F0 syndrome was nonzero on 8,106 cap-8 keys and 8,151 cap-12 keys. There were 644 cap-8-only triggers, 689 cap-12-only triggers and 15,205 neither. On the common-trigger set the actual F0 slot counts were 8/12 on 7,421 keys, 8/11 on 31 and 8/10 on 10. On all 24,000 keys the counts were 23,883, 82, 32 and 3 for 8/12, 8/11, 8/10 and 8/9 respectively, in both recorded F0 rounds.

| Cap | A1c rescues | A2 rescues | A1c-only : A2-only | Gap, pp [95% CI] |
| --- | --- | --- | --- | --- |
| 8 | 1,796/7,462 (24.07%) | 675/7,462 (9.05%) | 1,125 : 4 | 15.02 [14.19, 15.84] |
| 12 | 1,388/7,462 (18.60%) | 533/7,462 (7.14%) | 879 : 24 | 11.46 [10.68, 12.24] |

`D8 − D12 = 3.56 pp [2.77, 4.35]` (descriptive), and `D12/D8 = 0.763 [0.716, 0.811]`. Across caps, A1c had 540 cap-8-only and 132 cap-12-only rescues, and A2 had 354 and 212 respectively. Directional transitions across both arms and both caps are in the JSON.

| Cell | 8 only | 12 only | Both | Neither | D8 (pp) | D12 (pp) |
| --- | --- | --- | --- | --- | --- | --- |
| G, 0.3 | 258 | 160 | 801 | 4,781 | 49.69 | 43.45 |
| G, 0.5 | 83 | 202 | 3,023 | 2,692 | 7.54 | 4.13 |
| U, 0.3 | 235 | 132 | 670 | 4,963 | 42.84 | 40.90 |
| U, 0.5 | 68 | 195 | 2,968 | 2,769 | 7.01 | 3.64 |

| Cap | Arm | No edit | Phantom first | Final co-delay | Phantom edits dropping a true delay / all phantom edits | Rescues gaining a missing true delay |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | A1c | 1362 | 166 (2.22%) | 144 (1.93%) | 23/212 | 1366 |
| 8 | A2 | 203 | 6,997 (93.77%) | 7,015 (94.01%) | 3,969/12,129 | 71 |
| 12 | A1c | 117 | 589 (7.89%) | 879 (11.78%) | 31/966 | 1009 |
| 12 | A2 | 0 | 7,444 (99.76%) | 7,457 (99.93%) | 115/14,873 | 41 |

Phantom-first and final co-delay shares both use all common-trigger keys. Phantom-first checks the incoming delay against the surviving support after the dropped slot is removed. The edit counts include each accepted edit separately.

### Q2 secondary reads

| Population | Common triggers | Left gap (pp) | Right gap (pp) | Right/left [95% CI] |
| --- | --- | --- | --- | --- |
| M, both caps realized | 7,421 | 15.07 | 11.52 | 0.765 [0.719, 0.813] |
| M, all eight SNRs | 7,472 | 15.02 | 11.44 | 0.762 [0.716, 0.810] |
| M, cap 8 vs 10, all SNRs | 7,535 | 15.43 | 13.14 | 0.851 [0.809, 0.894] |
| M, cap 10 vs 12, all SNRs | 7,731 | 12.20 | 12.17 | 0.998 [0.948, 1.051] |
| N, 4.5–7 dB | 1,010 | 39.70 | 35.25 | 0.888 [0.814, 0.965] |
| N, all eight SNRs | 1,031 | 39.19 | 34.53 | 0.881 [0.809, 0.957] |

Cap-specific trigger effects use zero difference off the corresponding cap’s trigger set.

| Population | Cap | Triggered / all | Gap on triggers (pp) | Gap on all keys (pp) |
| --- | --- | --- | --- | --- |
| M, 4.5–7 dB | 6 | 12,940/24,000 | 7.17 | 3.87 |
| M, 4.5–7 dB | 8 | 8,106/24,000 | 17.95 | 6.06 |
| M, 4.5–7 dB | 10 | 7,977/24,000 | 13.14 | 4.37 |
| M, 4.5–7 dB | 12 | 8,151/24,000 | 12.13 | 4.12 |
| M, all SNRs | 6 | 13,827/32,000 | 6.74 | 2.91 |
| M, all SNRs | 8 | 8,127/32,000 | 17.95 | 4.56 |
| M, all SNRs | 10 | 7,991/32,000 | 13.15 | 3.28 |
| M, all SNRs | 12 | 8,163/32,000 | 12.12 | 3.09 |
| N, 4.5–7 dB | 8 | 1,354/6,000 | 40.25 | 9.08 |
| N, 4.5–7 dB | 12 | 1,180/6,000 | 33.73 | 6.63 |
| N, all SNRs | 8 | 1,391/8,000 | 39.47 | 6.86 |
| N, all SNRs | 12 | 1,203/8,000 | 33.08 | 4.98 |

On the 2,160 common triggers where cap 12 already retained a true delay absent at cap 8, the gap moved from 17.36 to 12.08 pp (ratio 0.696), and A2 phantom-first share moved from 99.63% to 99.31%. A1c rescues gaining an entering-missing true delay were 459 and 297, and A2 counts were 12 and 21. On the other 5,302 common triggers the gap moved from 14.07 to 11.20 pp (ratio 0.796), and A2 phantom-first share moved from 91.38% to 99.94%. The corresponding rescue counts were 907 and 712 for A1c and 59 and 20 for A2. The grouping is descriptive and uses the F0 entering supports.

On matched M/N observed keys, counts below are directed from known to estimated variance. Whole-grid B discordance counts compare successful decodes on the 8,000 matched keys. Gap estimates in the last column use the intersection of triggers for the given cap under both noise inputs.

| Cap | Known-only : estimated-only triggers | Both trigger | Known-only : estimated-only B success | Known → estimated gap (pp) |
| --- | --- | --- | --- | --- |
| 8 | 40 : 358 | 1033 | 179 : 11 | 51.40 → 46.66 |
| 12 | 31 : 266 | 937 | 151 : 9 | 41.09 → 37.46 |

## 2. Frozen verdicts

### Q1 and N

All contrasts use 20,000 matched physical-frame draws (seed `20261019`) jointly across the grid, variants and caps. Crossing estimates use first log-FER interpolation, with zero replaced by `0.5/n` inside an interpolation bracket. Censor bounds remain unbounded through paired contrasts and the percentile limits. M compares `B_s − B_8` in each cell. T compares the `B − A3` gap with the matched M gap. N compares B under estimated and known noise at the same cap. ROBUST requires both interval endpoints within ±0.25 dB. DEGRADED requires the lower endpoint above +0.25 dB. All other intervals are INCONCLUSIVE.

| Family | Cell | Cap | Delta (dB) | 95% paired interval (dB) | Frozen verdict |
| --- | --- | --- | --- | --- | --- |
| M | U, 0.3 | 6 | [2.756, +∞] | [2.579, +∞] | DEGRADED |
| M | U, 0.3 | 10 | -0.087 | [-0.240, 0.047] | ROBUST |
| M | U, 0.3 | 12 | -0.087 | [-0.227, 0.025] | ROBUST |
| M | U, 0.5 | 6 | [1.775, +∞] | [1.685, +∞] | DEGRADED |
| M | U, 0.5 | 10 | 0.122 | [0.013, 0.220] | ROBUST |
| M | U, 0.5 | 12 | 0.106 | [0.023, 0.189] | ROBUST |
| M | G, 0.3 | 6 | [2.849, +∞] | [2.712, +∞] | DEGRADED |
| M | G, 0.3 | 10 | 0.023 | [-0.082, 0.129] | ROBUST |
| M | G, 0.3 | 12 | 0.007 | [-0.124, 0.128] | ROBUST |
| M | G, 0.5 | 6 | [1.781, +∞] | [1.690, +∞] | DEGRADED |
| M | G, 0.5 | 10 | -0.017 | [-0.105, 0.025] | ROBUST |
| M | G, 0.5 | 12 | 0.031 | [-0.082, 0.139] | ROBUST |
| T6 | U, 0.3 | 8 | -0.355 | [-0.565, -0.177] | INCONCLUSIVE |
| T6 | U, 0.5 | 8 | -0.042 | [-0.144, 0.031] | ROBUST |
| T6 | G, 0.3 | 8 | -0.349 | [-0.516, -0.193] | INCONCLUSIVE |
| T6 | G, 0.5 | 8 | -0.074 | [-0.216, 0.045] | ROBUST |
| T10 | U, 0.3 | 8 | 1.851 | [1.282, 2.341] | DEGRADED |
| T10 | U, 0.5 | 8 | [1.744, +∞] | [1.562, +∞] | DEGRADED |
| T10 | G, 0.3 | 8 | 2.348 | [1.541, +∞] | DEGRADED |
| T10 | G, 0.5 | 8 | [1.737, +∞] | [1.637, +∞] | DEGRADED |
| N | G, 0.3 | 8 | 1.189 | [0.809, 1.579] | DEGRADED |
| N | G, 0.3 | 12 | 0.992 | [0.608, 1.488] | DEGRADED |

M cap 6 is DEGRADED in 4/4 cells, and caps 10 and 12 are each ROBUST in 4/4. T6 is ROBUST in both rho=.5 cells and INCONCLUSIVE in both rho=.3 cells under the frozen gate, with negative intervals that extend below −0.25 dB. T10 is DEGRADED in 4/4 cells. N is DEGRADED at both caps in G/0.3. The N verdict applies to the receiver together with this single-frame, AGC-calibrated moment estimator.

### Q2

1. Archive coverage and both continuation branches passed, including all common-trigger keys.
2. The D8 lower bound is 0.14195, above 0.05. The NO-BASELINE rule does not fire.
3. Nonpositive denominators occurred in 0 of 20,000 draws. The UNINFORMATIVE rule does not fire.
4. A2 cap-12 final co-delay share is 7,457/7,462 (99.93%), above 50%. The ratio upper bound is 0.81120, above 0.50, so DISPLACEMENT-COMPATIBLE does not fire.
5. The ratio lower bound is 0.71650, below 0.80, so PERSISTENT does not fire.
6. The remaining frozen category is **MIXED**.

## 3. Untested explanation

**M confidence.** Additional distinct true delays in cap-12 F0 may leave less missing support for either continuation to recover. This is consistent with a larger gap reduction in the observed pre-emption stratum while A2 continues to produce co-delay pairs. The stratum is defined by the entering state itself, and changing cap also changes the entering APP. A paired continuation with matched entering support and APP and a controlled ability to retain an additional weak true delay could test the explanation. The current run leaves the local decision identity and the SBL reversal mechanism untested.
