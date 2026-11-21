# E-1 aggregate: PRIMARY (all triggered keys, full P1 grid)

units: 12  interpretable: True  FINAL: **MIXED**

integrity: {"n_rows": 12, "n_keys": null, "checks": {"g4a_ok": 0, "f0_matches_ledger": 0, "a1_matches_ledger": 0, "g5_ok": 0, "arms_not_ok": 0, "units_with_nonzero_syndrome_not_failing_f0": 0}, "numerical_fallbacks": {"A1": 0, "A2": 0, "A3": 0, "A4": 0, "A5": 0, "A6": 0, "A7": 0}, "problems": [], "ok": true}
gates_all_pass: None

## Per-arm success (0 info-bit errors)

| arm | success | rate | rescued vs F0 | harmed vs F0 |
|---|---|---|---|---|
| A1 | 12/12 | 1.0000 | 12 | 0 |
| A2 | 7/12 | 0.5833 | 7 | 0 |
| A3 | 9/12 | 0.7500 | 9 | 0 |
| A4 | 9/12 | 0.7500 | 9 | 0 |
| A5 | 9/12 | 0.7500 | 9 | 0 |
| A6 | 9/12 | 0.7500 | 9 | 0 |
| A7 | 9/12 | 0.7500 | 9 | 0 |

## Exact one-sided McNemar (alpha .05 each, pooled; K4 reported only)

| test | b | c | p | significant |
|---|---|---|---|---|
| K1 A1>A2 | 5 | 0 | 0.0312 | True |
| K2 A2>A5 | 0 | 2 | 1 | False |
| K3 A1>A5 | 3 | 0 | 0.125 | False |
| K4 A1>A7 | 3 | 0 | 0.125 | False |

## Cluster-bootstrap 95% CI of rate difference (2000 resamples, seed 20261017); CI contains 0: not significant != equivalent

| pair | diff | CI | width | contains 0 |
|---|---|---|---|---|
| A1-A2 | +0.4167 | [+0.1663, +0.7007] | 0.5343 | False |
| A2-A5 | -0.1667 | [-0.4167, +0.0000] | 0.4167 | True (CI contains 0: not significant != equivalent) |
| A1-A5 | +0.2500 | [+0.0000, +0.5000] | 0.5000 | True (CI contains 0: not significant != equivalent) |
| A1-A3 | +0.2500 | [+0.0000, +0.5000] | 0.5000 | True (CI contains 0: not significant != equivalent) |
| A2-A4 | -0.1667 | [-0.4167, +0.0000] | 0.4167 | True (CI contains 0: not significant != equivalent) |
| A3-A6 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A6-A5 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A1-A7 | +0.2500 | [+0.0000, +0.5000] | 0.5000 | True (CI contains 0: not significant != equivalent) |

## Ratio criteria (delta = 0.1); Delta_geo = R_A1 - R_A5 = +0.2500 CI [+0.0000, +0.5000]
fraction of resamples with R_A1 = 0: 0.0000 -> kill_evaluable: True; with Delta_geo <= 0: 0.0300 -> sgamma_evaluable: False (limit 0.01 each)

| quantity (denominator) | point | CI | width |
|---|---|---|---|
| S_Gamma (Delta_geo) | +1.6667 | [+1.0000, +5.0000] | 4.0000 |
| F5 (R_A1) | +0.2500 | [+0.0000, +0.5000] | 0.5000 |
| F7 (R_A1) | +0.2500 | [+0.0000, +0.5000] | 0.5000 |
| S_swap (Delta_geo) | +1.0000 | [+1.0000, +1.0000] | 0.0000 |
| S_local (Delta_geo) | +0.0000 | [+0.0000, +0.0000] | 0.0000 |
| S_refit (Delta_geo) | +0.0000 | [+0.0000, +0.0000] | 0.0000 |
| S_Gamma_noswap (Delta_geo) | +0.0000 | [+0.0000, +0.0000] | 0.0000 |

J3a=False J3b=False (fired: None) J1=None J2=None -> **MIXED** (not evaluable: S_Gamma/ladder (divide by Delta_geo: point Delta_geo <= 0 or >1% of resamples with Delta_geo <= 0))

## Per SNR (success rate R_x)

| snr (centi-dB) | n | A1 | A2 | A3 | A4 | A5 | A6 | A7 |
|---|---|---|---|---|---|---|---|---|
| 450 | 2 | 1.000 | 0.000 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 |
| 500 | 2 | 1.000 | 0.000 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 |
| 550 | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 600 | 2 | 1.000 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 |
| 650 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 700 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 750 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 800 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Per cell (Holm over 4 cells)

| cell | n | succ A1..A7 | K1 p_holm | K2 p_holm | K3 p_holm | K4 p_holm | reverse effects |
|---|---|---|---|---|---|---|---|
| U_rho300 | 0 | 0,0,0,0,0,0,0 | 1 | 1 | 1 | 1 | none |
| U_rho500 | 0 | 0,0,0,0,0,0,0 | 1 | 1 | 1 | 1 | none |
| G_rho300 | 12 | 12,7,9,9,9,9,9 | 0.125 | 1 | 0.5 | 0.5 | none |
| G_rho500 | 0 | 0,0,0,0,0,0,0 | 1 | 1 | 1 | 1 | none |

## Cost (mean seconds per unit; A7 total is a from-scratch rounds=3 run, A7 - F0 is the third-round increment)

| arm | mean s | A7-F0 |
|---|---|---|
| A1 | 0.1636 |  |
| A2 | 0.1772 |  |
| A3 | 0.1442 |  |
| A4 | 0.1457 |  |
| A5 | 0.0402 |  |
| A6 | 0.0435 |  |
| A7 | 0.3554 | 0.0902 |
| F0 | 0.2652 | |

## Support changes and totals

{
 "support": {
  "A1": {
   "mean_n_support_changes": 3.3333333333333335,
   "mean_n_delay_replacements": 1.6666666666666667,
   "mean_n_edits": 2.0,
   "frac_units_support_changed": 0.9166666666666666
  },
  "A2": {
   "mean_n_support_changes": 2.5833333333333335,
   "mean_n_delay_replacements": 0.75,
   "mean_n_edits": 2.0,
   "frac_units_support_changed": 1.0
  },
  "A3": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  },
  "A4": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  },
  "A5": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  },
  "A6": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  },
  "A7": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  }
 },
 "a1_vs_a2": {
  "frac_same_accepted_edits": 0.3333333333333333,
  "frac_same_top1_candidate": 0.0
 },
 "unit_core_seconds": {
  "mean_gen": 0.11928633778976898,
  "mean_f0": 0.2652432124208038,
  "mean_all_seven_arms": 1.06979410808223,
  "total_core_hours": 0.004847745527642676
 }
}


# E-1 aggregate: PRE-DECLARED SECONDARY (SNR 6.5..8.0 dB subset)

units: 4  interpretable: True  FINAL: **KILL**

integrity: {"n_rows": 4, "n_keys": null, "checks": {"g4a_ok": 0, "f0_matches_ledger": 0, "a1_matches_ledger": 0, "g5_ok": 0, "arms_not_ok": 0, "units_with_nonzero_syndrome_not_failing_f0": 0}, "numerical_fallbacks": {"A1": 0, "A2": 0, "A3": 0, "A4": 0, "A5": 0, "A6": 0, "A7": 0}, "problems": [], "ok": true}
gates_all_pass: None

## Per-arm success (0 info-bit errors)

| arm | success | rate | rescued vs F0 | harmed vs F0 |
|---|---|---|---|---|
| A1 | 4/4 | 1.0000 | 4 | 0 |
| A2 | 4/4 | 1.0000 | 4 | 0 |
| A3 | 4/4 | 1.0000 | 4 | 0 |
| A4 | 4/4 | 1.0000 | 4 | 0 |
| A5 | 4/4 | 1.0000 | 4 | 0 |
| A6 | 4/4 | 1.0000 | 4 | 0 |
| A7 | 4/4 | 1.0000 | 4 | 0 |

## Exact one-sided McNemar (alpha .05 each, pooled; K4 reported only)

| test | b | c | p | significant |
|---|---|---|---|---|
| K1 A1>A2 | 0 | 0 | 1 | False |
| K2 A2>A5 | 0 | 0 | 1 | False |
| K3 A1>A5 | 0 | 0 | 1 | False |
| K4 A1>A7 | 0 | 0 | 1 | False |

## Cluster-bootstrap 95% CI of rate difference (2000 resamples, seed 20261017); CI contains 0: not significant != equivalent

| pair | diff | CI | width | contains 0 |
|---|---|---|---|---|
| A1-A2 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A2-A5 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A1-A5 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A1-A3 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A2-A4 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A3-A6 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A6-A5 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |
| A1-A7 | +0.0000 | [+0.0000, +0.0000] | 0.0000 | True (CI contains 0: not significant != equivalent) |

## Ratio criteria (delta = 0.1); Delta_geo = R_A1 - R_A5 = +0.0000 CI [+0.0000, +0.0000]
fraction of resamples with R_A1 = 0: 0.0000 -> kill_evaluable: True; with Delta_geo <= 0: 1.0000 -> sgamma_evaluable: False (limit 0.01 each)

| quantity (denominator) | point | CI | width |
|---|---|---|---|
| S_Gamma (Delta_geo) | n/a | [n/a, n/a] | n/a |
| F5 (R_A1) | +0.0000 | [+0.0000, +0.0000] | 0.0000 |
| F7 (R_A1) | +0.0000 | [+0.0000, +0.0000] | 0.0000 |
| S_swap (Delta_geo) | n/a | [n/a, n/a] | n/a |
| S_local (Delta_geo) | n/a | [n/a, n/a] | n/a |
| S_refit (Delta_geo) | n/a | [n/a, n/a] | n/a |
| S_Gamma_noswap (Delta_geo) | n/a | [n/a, n/a] | n/a |

J3a=True J3b=True (fired: ['J3a', 'J3b']) J1=None J2=None -> **KILL**

## Per SNR (success rate R_x)

| snr (centi-dB) | n | A1 | A2 | A3 | A4 | A5 | A6 | A7 |
|---|---|---|---|---|---|---|---|---|
| 650 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 700 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 750 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 800 | 1 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Per cell (Holm over 4 cells)

| cell | n | succ A1..A7 | K1 p_holm | K2 p_holm | K3 p_holm | K4 p_holm | reverse effects |
|---|---|---|---|---|---|---|---|
| U_rho300 | 0 | 0,0,0,0,0,0,0 | 1 | 1 | 1 | 1 | none |
| U_rho500 | 0 | 0,0,0,0,0,0,0 | 1 | 1 | 1 | 1 | none |
| G_rho300 | 4 | 4,4,4,4,4,4,4 | 1 | 1 | 1 | 1 | none |
| G_rho500 | 0 | 0,0,0,0,0,0,0 | 1 | 1 | 1 | 1 | none |

## Cost (mean seconds per unit; A7 total is a from-scratch rounds=3 run, A7 - F0 is the third-round increment)

| arm | mean s | A7-F0 |
|---|---|---|
| A1 | 0.1648 |  |
| A2 | 0.1732 |  |
| A3 | 0.1442 |  |
| A4 | 0.1450 |  |
| A5 | 0.0379 |  |
| A6 | 0.0411 |  |
| A7 | 0.3509 | 0.0834 |
| F0 | 0.2675 | |

## Support changes and totals

{
 "support": {
  "A1": {
   "mean_n_support_changes": 3.5,
   "mean_n_delay_replacements": 1.75,
   "mean_n_edits": 2.0,
   "frac_units_support_changed": 1.0
  },
  "A2": {
   "mean_n_support_changes": 2.75,
   "mean_n_delay_replacements": 1.0,
   "mean_n_edits": 2.0,
   "frac_units_support_changed": 1.0
  },
  "A3": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  },
  "A4": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  },
  "A5": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  },
  "A6": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  },
  "A7": {
   "mean_n_support_changes": 0.0,
   "mean_n_delay_replacements": 0.0,
   "mean_n_edits": 0.0,
   "frac_units_support_changed": 0.0
  }
 },
 "a1_vs_a2": {
  "frac_same_accepted_edits": 0.25,
  "frac_same_top1_candidate": 0.0
 },
 "unit_core_seconds": {
  "mean_gen": 0.11696033866610378,
  "mean_f0": 0.2674785917624831,
  "mean_all_seven_arms": 1.0570958534954116,
  "total_core_hours": 0.0016017053154711094
 }
}
