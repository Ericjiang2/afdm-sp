# E-2 aggregate

interpretable: True; gates_all_pass: True; cgates_all_pass: True

**D1 (replication, family R): PASS**  failed items: none

```
{
 "a_F5_F7_ci_lo_ge_.10": {
  "satisfied": true,
  "F5_ci_lo": 0.471506801317804,
  "F7_ci_lo": 0.41321944996863386,
  "evaluable": true
 },
 "b_S_Gamma_ci_lo_gt_1": {
  "satisfied": true,
  "ci_lo": 1.17809364548495,
  "evaluable": true
 },
 "c_S_swap_ci_lo_ge_.5": {
  "satisfied": true,
  "ci_lo": 0.8611819944107233,
  "evaluable": true
 },
 "d_doublet_share_A2_ge_.80_A1_le_.05": {
  "satisfied": true,
  "A2": 0.9339294585196225,
  "A1": 0.016145057128663685
 }
}
```

**D2 (guard recovery share, family R): PHANTOM-FULL**

**D3 (principle vs heuristic, family C): PRINCIPLE**

```
{
 "D3a": true,
 "D3b": true,
 "D3c": true,
 "C_A1_minus_A2g_inside_pm_0p01": false,
 "R_A1_minus_A1g": {
  "point": -0.00024838549428712886,
  "ci_lo": -0.0009886338011398529,
  "ci_hi": 0.00037764469313649314,
  "ci_width": 0.001366278494276346,
  "contains_0": true
 },
 "C_A1_minus_A1g": {
  "point": 0.11006372809346786,
  "ci_lo": 0.09960212201591512,
  "ci_hi": 0.12071044858835772,
  "ci_width": 0.021108326572442604,
  "contains_0": false
 },
 "C_A1_minus_A2g": {
  "point": 0.10966542750929367,
  "ci_lo": 0.09925272985130959,
  "ci_hi": 0.12025989962396558,
  "ci_width": 0.021007169772655987,
  "contains_0": false
 },
 "info_gate": {
  "a1_rescued_units": 945,
  "minimum": 100,
  "passed": true
 }
}
```

## Family R: 8052 triggered units of 32000 keys

integrity: {"n_rows": 32000, "n_keys": 32000, "n_triggered": 8052, "checks": {"f0_syndrome_consistent": 0, "g5_ok": 0, "guard_ok": 0, "arms_not_ok": 0, "triggered_with_f0_success": 3}, "numerical_fallbacks": {"A1": 0, "A2": 0, "A3": 0, "A1g": 0, "A2g": 0, "A2n": 0, "A5": 0, "A7": 0}, "problems": [], "ok": true}

| arm | success | rate |
|---|---|---|
| A1 | 2390/8052 | 0.2968 |
| A2 | 955/8052 | 0.1186 |
| A3 | 1353/8052 | 0.1680 |
| A1g | 2392/8052 | 0.2971 |
| A2g | 2393/8052 | 0.2972 |
| A2n | 2125/8052 | 0.2639 |
| A5 | 1214/8052 | 0.1508 |
| A7 | 1353/8052 | 0.1680 |

### Differences of success rate (cluster bootstrap 20000 resamples, seed 20261017); CI contains 0: not significant != equivalent

| pair | diff | 95% CI | width |
|---|---|---|---|
| A1-A2 | +0.1782 | [+0.1697, +0.1870] | 0.0173 |
| A1-A7 | +0.1288 | [+0.1204, +0.1375] | 0.0171 |
| A2g-A2 | +0.1786 | [+0.1700, +0.1874] | 0.0173 |
| A1-A2g | -0.0004 | [-0.0011, +0.0004] | 0.0015 |  (CI contains 0: not significant != equivalent)
| A2n-A2 | +0.1453 | [+0.1374, +0.1533] | 0.0159 |
| A1-A1g | -0.0002 | [-0.0010, +0.0004] | 0.0014 |  (CI contains 0: not significant != equivalent)
| A2n-A2g | -0.0333 | [-0.0373, -0.0293] | 0.0081 |
| A1g-A2g | -0.0001 | [-0.0004, +0.0000] | 0.0004 |  (CI contains 0: not significant != equivalent)
| A1-A5 | +0.1461 | [+0.1373, +0.1552] | 0.0178 |
| A1-A3 | +0.1288 | [+0.1204, +0.1375] | 0.0171 |
| A2-A5 | -0.0322 | [-0.0374, -0.0268] | 0.0106 |

### Ratios

| quantity | point | 95% CI | den<=0 fraction | evaluable |
|---|---|---|---|---|
| F5 | +0.4921 | [+0.4715, +0.5127] | 0.0000 | True |
| F7 | +0.4339 | [+0.4132, +0.4543] | 0.0000 | True |
| S_Gamma | +1.2202 | [+1.1781, +1.2644] | 0.0000 | True |
| S_swap | +0.8818 | [+0.8612, +0.9015] | 0.0000 | True |
| G | +1.0021 | [+0.9979, +1.0064] | 0.0000 | True |
| G_n | +0.8153 | [+0.7949, +0.8360] | 0.0000 | True |

### Exact one-sided McNemar (reported; b = first arm only, c = second only)

| test | b | c | log10 p |
|---|---|---|---|
| A1>A2 | 1437 | 2 | -427.2 |
| A2g>A2 | 1440 | 2 | -428.1 |
| A1>A2g | 3 | 6 | -0.0 |
| A1>A1g | 3 | 5 | -0.1 |
| A2n>A2 | 1176 | 6 | -340.2 |
| A2n>A2g | 6 | 274 | 0.0 |
| A1>A3 | 1048 | 11 | -293.1 |
| A1>A5 | 1183 | 7 | -340.4 |
| A1>A7 | 1048 | 11 | -293.1 |
| A1g>A2g | 0 | 1 | 0.0 |

### Per SNR (success rate)

| snr (centi-dB) | n | A1 | A2 | A3 | A1g | A2g | A2n | A5 | A7 |
|---|---|---|---|---|---|---|---|---|---|
| 450 | 3201 | 0.246 | 0.072 | 0.116 | 0.247 | 0.247 | 0.201 | 0.099 | 0.116 |
| 500 | 2446 | 0.184 | 0.070 | 0.094 | 0.183 | 0.184 | 0.169 | 0.087 | 0.094 |
| 550 | 1764 | 0.354 | 0.150 | 0.237 | 0.354 | 0.354 | 0.323 | 0.209 | 0.237 |
| 600 | 550 | 0.796 | 0.405 | 0.509 | 0.796 | 0.796 | 0.749 | 0.478 | 0.509 |
| 650 | 66 | 0.985 | 0.667 | 0.652 | 0.985 | 0.985 | 0.970 | 0.606 | 0.652 |
| 700 | 17 | 0.941 | 0.824 | 0.412 | 0.941 | 0.941 | 0.941 | 0.471 | 0.412 |
| 750 | 5 | 1.000 | 1.000 | 0.600 | 1.000 | 1.000 | 1.000 | 0.600 | 0.600 |
| 800 | 3 | 1.000 | 1.000 | 0.667 | 1.000 | 1.000 | 1.000 | 0.333 | 0.667 |

### Per rho (success rate)

| rho (permille) | n | A1 | A2 | A3 | A1g | A2g | A2n | A5 | A7 |
|---|---|---|---|---|---|---|---|---|---|
| 300 | 1891 | 0.761 | 0.283 | 0.368 | 0.762 | 0.762 | 0.665 | 0.328 | 0.368 |
| 500 | 6161 | 0.154 | 0.068 | 0.107 | 0.154 | 0.155 | 0.141 | 0.096 | 0.107 |

### Co-delay census (pre-registered readout; final geometry; doublet = two paths with equal delay)

| arm | units with doublet | frac | pairs | |D_N| hist [0,.2) / [.2,.5) / [.5,.8) / [.8,1] | final delay set == truth set |
|---|---|---|---|---|---|
| A1 | 130 | 0.0161 | 130 | 88 / 35 / 5 / 2 | 0.4878 |
| A2 | 7520 | 0.9339 | 14001 | 4 / 3 / 0 / 13994 | 0.0637 |
| A3 | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.2086 |
| A1g | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.4892 |
| A2g | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.4894 |
| A2n | 3474 | 0.4314 | 5075 | 645 / 4430 / 0 / 0 | 0.3963 |
| A5 | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.2086 |
| A7 | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.2086 |

r1 duplicate-delay units: 0; units whose truth has duplicate delays (rays): 0

| arm | edits | shares | same_slot | new | new in truth | new not in truth |
|---|---|---|---|---|---|---|
| A1 | 10892 | 178 | 4465 | 6249 | 5538 | 711 |
| A2 | 14559 | 13093 | 1180 | 286 | 283 | 3 |
| A1g | 10897 | 0 | 4578 | 6319 | 5554 | 765 |
| A2g | 10896 | 0 | 4574 | 6322 | 5556 | 766 |
| A2n | 12404 | 5640 | 2921 | 3843 | 3738 | 105 |

### Cost (mean seconds; A7 total is a from-scratch rounds=3 run)

{
 "keys": 32000,
 "triggered": 8052,
 "mean_f0_seconds": 0.4763200535829965,
 "mean_gen_seconds_per_key": 0.03236478552222252,
 "arms": {
  "A1": {
   "mean_seconds": 0.28661500483512337
  },
  "A2": {
   "mean_seconds": 0.3013011095124115
  },
  "A3": {
   "mean_seconds": 0.23913236115228662
  },
  "A1g": {
   "mean_seconds": 0.28325424172743874
  },
  "A2g": {
   "mean_seconds": 0.276806422419209
  },
  "A2n": {
   "mean_seconds": 0.28650597271793304
  },
  "A5": {
   "mean_seconds": 0.07295268835097142
  },
  "A7": {
   "mean_seconds": 0.6131626153261259,
   "mean_seconds_minus_f0": 0.12783703366006502
  }
 },
 "total_core_hours": 9.7995733781481
}

## Family C: 7532 triggered units of 8000 keys

integrity: {"n_rows": 8000, "n_keys": 8000, "n_triggered": 7532, "checks": {"f0_syndrome_consistent": 0, "g5_ok": 0, "guard_ok": 0, "arms_not_ok": 0, "triggered_with_f0_success": 0}, "numerical_fallbacks": {"A1": 0, "A2": 0, "A3": 0, "A1g": 0, "A2g": 0, "A2n": 0, "A5": 0, "A7": 0}, "problems": [], "ok": true}

| arm | success | rate |
|---|---|---|
| A1 | 945/7532 | 0.1255 |
| A2 | 672/7532 | 0.0892 |
| A3 | 116/7532 | 0.0154 |
| A1g | 116/7532 | 0.0154 |
| A2g | 119/7532 | 0.0158 |
| A2n | 942/7532 | 0.1251 |
| A5 | 115/7532 | 0.0153 |
| A7 | 118/7532 | 0.0157 |

### Differences of success rate (cluster bootstrap 20000 resamples, seed 20261017); CI contains 0: not significant != equivalent

| pair | diff | 95% CI | width |
|---|---|---|---|
| A1-A2 | +0.0362 | [+0.0310, +0.0417] | 0.0107 |
| A1-A7 | +0.1098 | [+0.0994, +0.1204] | 0.0211 |
| A2g-A2 | -0.0734 | [-0.0808, -0.0662] | 0.0146 |
| A1-A2g | +0.1097 | [+0.0993, +0.1203] | 0.0210 |
| A2n-A2 | +0.0358 | [+0.0309, +0.0409] | 0.0100 |
| A1-A1g | +0.1101 | [+0.0996, +0.1207] | 0.0211 |
| A2n-A2g | +0.1093 | [+0.0990, +0.1197] | 0.0207 |
| A1g-A2g | -0.0004 | [-0.0009, +0.0000] | 0.0009 |  (CI contains 0: not significant != equivalent)
| A1-A5 | +0.1102 | [+0.0997, +0.1209] | 0.0212 |
| A1-A3 | +0.1101 | [+0.0996, +0.1207] | 0.0211 |
| A2-A5 | +0.0740 | [+0.0667, +0.0814] | 0.0147 |

### Ratios

| quantity | point | 95% CI | den<=0 fraction | evaluable |
|---|---|---|---|---|
| F5 | +0.8783 | [+0.8571, +0.8991] | 0.0000 | True |
| F7 | +0.8751 | [+0.8540, +0.8958] | 0.0000 | True |
| S_Gamma | +0.3289 | [+0.2963, +0.3599] | 0.0000 | True |
| S_swap | +0.9988 | [+0.9884, +1.0093] | 0.0000 | True |
| G | -2.0256 | [-2.3587, -1.7632] | 0.0000 | True |
| G_n | +0.9890 | [+0.9248, +1.0599] | 0.0000 | True |

### Exact one-sided McNemar (reported; b = first arm only, c = second only)

| test | b | c | log10 p |
|---|---|---|---|
| A1>A2 | 292 | 19 | -63.6 |
| A2g>A2 | 1 | 554 | 0.0 |
| A1>A2g | 826 | 0 | -248.7 |
| A1>A1g | 829 | 0 | -249.6 |
| A2n>A2 | 276 | 6 | -73.1 |
| A2n>A2g | 823 | 0 | -247.7 |
| A1>A3 | 829 | 0 | -249.6 |
| A1>A5 | 830 | 0 | -249.9 |
| A1>A7 | 827 | 0 | -249.0 |
| A1g>A2g | 0 | 3 | 0.0 |

### Per SNR (success rate)

| snr (centi-dB) | n | A1 | A2 | A3 | A1g | A2g | A2n | A5 | A7 |
|---|---|---|---|---|---|---|---|---|---|
| 600 | 965 | 0.089 | 0.018 | 0.006 | 0.007 | 0.007 | 0.077 | 0.007 | 0.006 |
| 800 | 1914 | 0.091 | 0.041 | 0.011 | 0.011 | 0.011 | 0.091 | 0.012 | 0.010 |
| 1000 | 1880 | 0.118 | 0.080 | 0.016 | 0.016 | 0.016 | 0.119 | 0.016 | 0.017 |
| 1200 | 1843 | 0.163 | 0.148 | 0.022 | 0.021 | 0.022 | 0.167 | 0.022 | 0.023 |
| 1400 | 930 | 0.174 | 0.166 | 0.018 | 0.020 | 0.020 | 0.176 | 0.014 | 0.018 |

### Per rho (success rate)

| rho (permille) | n | A1 | A2 | A3 | A1g | A2g | A2n | A5 | A7 |
|---|---|---|---|---|---|---|---|---|---|
| 300 | 3733 | 0.133 | 0.092 | 0.021 | 0.020 | 0.021 | 0.132 | 0.022 | 0.021 |
| 500 | 3799 | 0.118 | 0.087 | 0.010 | 0.011 | 0.011 | 0.118 | 0.009 | 0.010 |

### Co-delay census (pre-registered readout; final geometry; doublet = two paths with equal delay)

| arm | units with doublet | frac | pairs | |D_N| hist [0,.2) / [.2,.5) / [.5,.8) / [.8,1] | final delay set == truth set |
|---|---|---|---|---|---|
| A1 | 7526 | 0.9992 | 16250 | 13318 / 2134 / 483 / 315 | 0.0000 |
| A2 | 7530 | 0.9997 | 17541 | 9638 / 1500 / 587 / 5816 | 0.0000 |
| A3 | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.0000 |
| A1g | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.0000 |
| A2g | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.0000 |
| A2n | 7527 | 0.9993 | 16476 | 13171 / 3305 / 0 / 0 | 0.0000 |
| A5 | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.0000 |
| A7 | 0 | 0.0000 | 0 | 0 / 0 / 0 / 0 | 0.0000 |

r1 duplicate-delay units: 0; units whose truth has duplicate delays (rays): 7532

| arm | edits | shares | same_slot | new | new in truth | new not in truth |
|---|---|---|---|---|---|---|
| A1 | 15052 | 14837 | 190 | 25 | 7 | 18 |
| A2 | 15059 | 15017 | 40 | 2 | 0 | 2 |
| A1g | 14698 | 0 | 4399 | 10299 | 137 | 10162 |
| A2g | 14698 | 0 | 4403 | 10295 | 137 | 10158 |
| A2n | 15054 | 14870 | 161 | 23 | 6 | 17 |

units with a true multi-ray tap: 7532

| arm | doublet pairs on true multi-ray tap | frac of pairs | doublet units on true multi-ray tap | frac of doublet units |
|---|---|---|---|---|
| A1 | 16244 | 0.9996 | 7526 | 1.0000 |
| A2 | 17242 | 0.9830 | 7509 | 0.9972 |
| A1g | 0 | n/a | 0 | n/a |
| A2g | 0 | n/a | 0 | n/a |
| A2n | 16469 | 0.9996 | 7527 | 1.0000 |

### Cost (mean seconds; A7 total is a from-scratch rounds=3 run)

{
 "keys": 8000,
 "triggered": 7532,
 "mean_f0_seconds": 0.398569623569143,
 "mean_gen_seconds_per_key": 0.046126493806543295,
 "arms": {
  "A1": {
   "mean_seconds": 0.2524241316359143
  },
  "A2": {
   "mean_seconds": 0.25468873758530775
  },
  "A3": {
   "mean_seconds": 0.21023771338611424
  },
  "A1g": {
   "mean_seconds": 0.2501031098077054
  },
  "A2g": {
   "mean_seconds": 0.24923101420541735
  },
  "A2n": {
   "mean_seconds": 0.2553850895314306
  },
  "A5": {
   "mean_seconds": 0.06232310845327439
  },
  "A7": {
   "mean_seconds": 0.5197529221475753,
   "mean_seconds_minus_f0": 0.1235123458751183
  }
 },
 "total_core_hours": 5.285943140585312
}

## Calibrated C-family SNR grid (frozen rule, F0 only)

{
 "rule": "smallest candidate SNR with F0 FER <= .95 -> s0; grid {s0, s0+2, s0+4, s0+6} capped at 20 dB; F0 FER(20 dB) > .95 -> UNINFORMATIVE",
 "fer_metric": "fraction of calibration frames with >= 1 information-bit error after F0 (rounds=2)",
 "frames": [
  5000,
  5100
 ],
 "rho": {
  "0.3": {
   "fer_by_snr": {
    "6": 0.95,
    "8": 0.94,
    "10": 0.92,
    "12": 0.91,
    "14": 0.9,
    "16": 0.89,
    "18": 0.89,
    "20": 0.9
   },
   "status": "OK",
   "s0": 6,
   "grid_db": [
    6,
    8,
    10,
    12
   ]
  },
  "0.5": {
   "fer_by_snr": {
    "6": 0.99,
    "8": 0.95,
    "10": 0.94,
    "12": 0.93,
    "14": 0.93,
    "16": 0.92,
    "18": 0.92,
    "20": 0.93
   },
   "status": "OK",
   "s0": 8,
   "grid_db": [
    8,
    10,
    12,
    14
   ]
  }
 },
 "n_rows": 1600
}

