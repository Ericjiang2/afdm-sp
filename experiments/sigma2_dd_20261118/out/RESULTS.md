# Decision-directed noise variance results

## Observation

The frozen P1 G cell used 1,000 paired physical frames, eight SNRs, physical pilot
fraction .3, and true path count and receiver cap 8. The run completed 8,000 observations
and 48,000 arm evaluations in 12 min 02 s using 3.089159 core-hours and 16 workers.
The readout verified all 200 gzip MD5s and the full paired key grid before calculating
the 20,000 physical-frame bootstrap draws. [Protocol](../PROTOCOL.md) · [Run receipt](main_20261118/main_receipt.json) · [Results JSON](main_20261118/results.json)

| SNR (dB) | B_known | B_SF | B_DD | A3_known | A3_SF | A3_DD |
|---:|---:|---:|---:|---:|---:|---:|
| 4.5 | 223 | 262 | 966 | 40 | 50 | 944 |
| 5.0 | 26 | 71 | 751 | 1 | 6 | 615 |
| 5.5 | 1 | 31 | 390 | 0 | 0 | 167 |
| 6.0 | 0 | 21 | 139 | 0 | 0 | 14 |
| 6.5 | 0 | 8 | 26 | 0 | 0 | 1 |
| 7.0 | 0 | 5 | 5 | 0 | 0 | 0 |
| 7.5 | 0 | 1 | 1 | 0 | 0 | 0 |
| 8.0 | 0 | 0 | 0 | 0 | 0 | 0 |

Each cell shows the count of information-bit error frames among 1,000 observations.

| Arm | FER=.01 crossing (dB) | 95% bootstrap interval (dB) |
|---|---:|---:|
| B_known | 5.147 | [5.082, 5.242] |
| B_SF | 6.384 | [6.109, 6.908] |
| B_DD | 6.790 | [6.617, 7.000] |
| A3_known | 4.688 | [4.634, 4.784] |
| A3_SF | 4.880 | [4.734, 5.015] |
| A3_DD | 6.064 | [5.944, 6.174] |

R = crossing(B_SF) − crossing(B_DD) was -0.405 dB ([-0.724, 0.103]).
Its paired interval includes zero. The true-H A3_DD crossing was 1.376 dB above A3_known.

### DD estimate diagnostics

Values show mean ± sample SD of the internal variance ratio σ̂²_DD/σ², followed by
the floor rate. Trigger refers to nonzero syndrome after the second DD F0 round.

| SNR (dB) | All keys (n=1,000) | Trigger n | Trigger | No-trigger n | No trigger |
|---:|---:|---:|---:|---:|---:|
| 4.5 | 0.127 ± 0.195 / 29.0% | 966 | 0.097 ± 0.112 / 30.0% | 34 | 0.976 ± 0.117 / 0.0% |
| 5.0 | 0.388 ± 0.358 / 5.7% | 777 | 0.214 ± 0.155 / 7.3% | 223 | 0.994 ± 0.134 / 0.0% |
| 5.5 | 0.714 ± 0.378 / 0.6% | 449 | 0.336 ± 0.163 / 1.3% | 551 | 1.023 ± 0.160 / 0.0% |
| 6.0 | 0.928 ± 0.296 / 0.0% | 221 | 0.458 ± 0.187 / 0.0% | 779 | 1.062 ± 0.149 / 0.0% |
| 6.5 | 1.056 ± 0.200 / 0.0% | 89 | 0.638 ± 0.253 / 0.0% | 911 | 1.097 ± 0.138 / 0.0% |
| 7.0 | 1.134 ± 0.140 / 0.0% | 39 | 0.913 ± 0.375 / 0.0% | 961 | 1.143 ± 0.113 / 0.0% |
| 7.5 | 1.189 ± 0.130 / 0.0% | 24 | 1.361 ± 0.380 / 0.0% | 976 | 1.185 ± 0.115 / 0.0% |
| 8.0 | 1.231 ± 0.161 / 0.0% | 17 | 1.750 ± 0.354 / 0.0% | 983 | 1.222 ± 0.140 / 0.0% |
| Pooled | 0.846 ± 0.453 / 4.4% | 2582 | 0.258 ± 0.279 / 13.7% | 5418 | 1.126 ± 0.152 / 0.0% |

The floor was reached on 353/8,000 keys (4.4125%), all among DD triggers at 4.5–5.5 dB.
The trigger floor rate was 353/2,582 (13.67%). At 6.5 dB, where B_DD had 26 errors and
B_SF had eight, DD-triggered keys averaged 0.638 times the true variance with zero floor hits.

The round-1 delay sets of B_DD and B_known agreed on all 8,000 paired keys.
The table gives mean missed true delays for both arms, within the same DD trigger strata.

| SNR (dB) | All keys | Trigger | No trigger |
|---:|---:|---:|---:|
| 4.5 | 1.787 | 1.796 | 1.529 |
| 5.0 | 1.729 | 1.846 | 1.323 |
| 5.5 | 1.698 | 2.022 | 1.434 |
| 6.0 | 1.677 | 2.231 | 1.520 |
| 6.5 | 1.639 | 2.483 | 1.557 |
| 7.0 | 1.599 | 2.513 | 1.562 |
| 7.5 | 1.582 | 2.250 | 1.566 |
| 8.0 | 1.555 | 2.294 | 1.542 |

## Frozen verdict

**DEGRADED.** Δ_DD = crossing(B_DD) − crossing(B_known) = +1.643 dB
with paired 95% CI [1.462, 1.838] dB.

| Rule | Evaluation |
|---|---|
| ROBUST if the interval lies inside [−.25, +.25] dB | Fails. Upper endpoint 1.838 > .25 dB. |
| DEGRADED if the lower endpoint exceeds +.25 dB | Passes. Lower endpoint 1.462 > .25 dB. |
| INCONCLUSIVE otherwise | The DEGRADED condition applies. |

The point estimates score SD1–SD4 false for both authors. H-good missed the ±.25 dB
band. H-bias predicted a positive R and the point estimate was negative. H-none
missed the ±.25 dB band for R, and R fell below the +.5 dB recovery threshold.
[Prediction ledger](../../../research-assets/prediction-ledger.md)

## Untested explanation

**M confidence.** APP moments use the same received samples as the residual, so the
noise–symbol-error cross term can be negative. Subtracting Γ in that regime may
underestimate usable detector noise. Low ratios on DD triggers near the crossing
and the A3_DD loss with a fixed true channel fit that hypothesis. A3_DD shares the
estimate from B_DD, which also carries its fitted gains, geometry and APP calibration.
The trigger split is descriptive and depends on the updated variance.

Raw rows remain on deinlab in the main-run directory. The per-shard list has MD5
`9fde2d4884c1c6b379101bc20c647228`. [Per-shard MD5 list](main_20261118/REMOTE_ROWS_MD5.txt)
