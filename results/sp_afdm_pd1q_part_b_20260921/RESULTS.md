# Part B — frozen prospective evidence

**Verdict: supported under the predeclared contract.** 9,696 attempts / 3,072 fresh paired observations; 19,392 checkpoints recounted successfully. Exit 0; elapsed 2 h 17 min 5 s. No new simulations were launched during retrieval.

## Primary reliability

| SNR dB | TF errors/1024 | EP2 errors/1024 | EP4 errors/1024 |
|---|---:|---:|---:|
| 6.0 | 206 | 487 | 309 |
| 6.5 | 43 | 140 | 74 |
| 7.0 | 14 | 29 | 20 |

| SNR | Comparator | Rescue / harm | Excess-FER upper, percentage points | Tolerance, pp |
|---|---|---:|---:|---:|
| 6.0 | EP2_MEAN_R2 | 283 / 2 | -23.094 | 2 |
| 6.0 | EP4_MEAN_R2 | 112 / 9 | -6.538 | 2 |
| 6.5 | EP2_MEAN_R2 | 98 / 1 | -6.554 | 2 |
| 6.5 | EP4_MEAN_R2 | 32 / 1 | -1.129 | 2 |
| 7.0 | EP2_MEAN_R2 | 17 / 2 | 0.131 | 1 |
| 7.0 | EP4_MEAN_R2 | 9 / 3 | 0.793 | 1 |

These six upper bounds form a simultaneous one-sided 95% family. All pass. Lower bounds in paired_counts.csv form a separate family, not a joint two-sided 95% interval. At 7 dB, bounds establish the tolerance criterion, not FER superiority.

## Complete online latency

Seconds; brackets are pointwise 95% paired moving-block bootstrap intervals.

| SNR | Method | Median [CI] | p90 [CI] | p95 [CI] |
|---|---|---|---|---|
| 6.0 | TF_J20_R2 | 0.2882 [0.2873, 0.2890] | 0.3071 [0.3058, 0.3093] | 0.3130 [0.3111, 0.3152] |
| 6.0 | EP2_MEAN_R2 | 0.5020 [0.4967, 0.5097] | 0.6929 [0.6845, 0.7004] | 0.7195 [0.7102, 0.7258] |
| 6.0 | EP4_MEAN_R2 | 0.7310 [0.7205, 0.7490] | 1.1237 [1.1049, 1.1333] | 1.1751 [1.1612, 1.1907] |
| 6.5 | TF_J20_R2 | 0.2862 [0.2852, 0.2869] | 0.3046 [0.3026, 0.3080] | 0.3103 [0.3085, 0.3127] |
| 6.5 | EP2_MEAN_R2 | 0.4947 [0.4905, 0.4979] | 0.6802 [0.6695, 0.6900] | 0.7171 [0.7053, 0.7267] |
| 6.5 | EP4_MEAN_R2 | 0.7161 [0.7102, 0.7223] | 1.1081 [1.0802, 1.1223] | 1.1583 [1.1411, 1.1877] |
| 7.0 | TF_J20_R2 | 0.2842 [0.2830, 0.2852] | 0.3043 [0.3025, 0.3057] | 0.3097 [0.3078, 0.3119] |
| 7.0 | EP2_MEAN_R2 | 0.4916 [0.4870, 0.4976] | 0.6760 [0.6629, 0.6871] | 0.7069 [0.6933, 0.7223] |
| 7.0 | EP4_MEAN_R2 | 0.7132 [0.7074, 0.7239] | 1.0836 [1.0595, 1.1120] | 1.1531 [1.1323, 1.1835] |

TF median latency is 42.1–42.6% lower than EP2 and 60.0–60.6% lower than EP4. TF/EP2 median-ratio upper95 is 0.580/0.583/0.583, below 0.8; p90 ratios 0.443/0.448/0.450. Full ratios and uncertainty are in analysis/paired_counts.csv and latency_uncertainty.csv.

## Deadlines

At fixed E1 EP2-median deadlines (~0.50 s), information-frame errors /1024: TF 206/43/14; EP2 649/336/168; EP4 897/596/358 at 6/6.5/7 dB. At 0.6 times those deadlines (~0.30 s): TF 214/44/14; EP2 955/696/496; EP4 1024/1024/1024. All five fixed deadline fractions are retained in cells.csv.

## Controls and claim limits

- POINT, paired first128/SNR: TF errors 21/8/2 vs POINT 20/9/3; TF rescue/harm 2/3, 1/0, 1/0. Similar latency. Does not establish a general reliability advantage from full gain-variance propagation. Primary remains frozen TF_J20_R2.
- PBi, paired first32/SNR: TF errors 6/2/0 vs PBi 21/10/0; PBi median ~14.36 s vs TF ~0.29 s. Exploratory subset only; no universal baseline claim.
- EP4 improves accuracy over EP2, but TF meets the predeclared reliability tolerances against both and has substantially lower complete latency.
- Zero numerical failures, zero missing decisions, zero unknown scored bits across all 9,696 attempts. No pipeline integrity block. No retuning or scope extension.
- Supported claim: under the frozen channel, coding, geometry and CPU configuration at 6–7 dB, TF retains reliability within predeclared tolerances and substantial complete-latency advantage over these EP controls. Do not generalize to arbitrary regimes, hardware or all EP implementations; do not claim equivalence or full-variance superiority.
- Minimum next step: paper evidence/claims preparation using these frozen results; no additional experiment is launched.

## Provenance and retention

Remote inventory: 45,021 files, 1,565,009,669 bytes (~1.46 GiB). Heavy raw evidence stays on deinlab under the original Part B root. Retrieved 8 analysis/recount files verified against inventory SHA256. Numeric source 2d130b4d; statistical contract unchanged. Part A qualification is prior evidence, not new Part B performance measurements.

Machine-readable: [cells](analysis/cells.csv), [paired counts](analysis/paired_counts.csv), [latency uncertainty](analysis/latency_uncertainty.csv), [stage costs](analysis/latency_stage_summary.csv), [manifest](analysis/analysis_manifest.json), [recount](recount_receipt.json). Original automated report remains in analysis/RESULTS.md.
