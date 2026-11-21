# Model-matched Gamma check: aggregate

interpretable: True; gates_all_pass: True; units: 300

integrity: {"n_rows": 300, "n_keys": 300, "n_error_rows": 0, "worst_gamma_diag_rel_err": 3.675862261337047e-16, "cholesky_jitter_events": 0, "problems": [], "ok": true}

## EIV EM lower bound: monotonicity violations (tolerance 1e-9 relative; transitions across atom pruning excluded)

| world:variant | runs | runs with violation | violating transitions | worst relative drop | prune events |
|---|---|---|---|---|---|
| real:S-diag | 300 | 0 | 0 | 0 | 0 |
| real:S-cov | 300 | 0 | 0 | 0 | 0 |
| syn:S-diag | 900 | 0 | 0 | 0 | 0 |
| syn:S-cov | 900 | 0 | 0 | 0 | 0 |
| syn:S-hard | 900 | 0 | 0 | 0 | 0 |
| syn:S-genie | 900 | 0 | 0 | 0 | 3 |

## Verdict: **SUSPECT**

D = NMSE_dB(S-cov) - NMSE_dB(S-diag), synthetic, R-averaged per key: +1.3673 [+1.2076, +1.5203]   (cluster bootstrap over (scenario, frame): 100 clusters, 20000 resamples, seed 20261018; CODE-CONSISTENT iff CI_hi <= 0; SUSPECT iff CI_lo > 0.2 dB)

fraction of keys with D < 0: 0.100

## Report-only

D_real = NMSE_dB(S-cov) - NMSE_dB(S-diag), REAL observation: +1.3004 [+1.1488, +1.4502]; reproduces the E-3 direction (point > 0): True

| quantity (dB) | mean [95% CI] |
|---|---|
| synthetic NMSE_dB S-diag | -15.3058 [-15.5861, -15.0442] |
| synthetic NMSE_dB S-cov | -13.9385 [-14.2355, -13.6738] |
| synthetic NMSE_dB S-hard | -14.8096 [-15.0785, -14.5706] |
| synthetic NMSE_dB S-genie | -21.9555 [-22.1867, -21.7127] |
| real NMSE_dB S-diag | -12.7717 [-13.1175, -12.4541] |
| real NMSE_dB S-cov | -11.4713 [-11.8594, -11.1196] |
| synthetic NMSE_dB S-hard - S-diag | +0.4962 [+0.3459, +0.6389] |
| synthetic NMSE_dB S-genie - S-diag | -6.6497 [-6.9770, -6.3154] |

| cell | keys | D (synthetic) | D_real |
|---|---|---|---|
| U_600 | 50 | +2.1353 | +1.6845 |
| U_700 | 50 | +1.3909 | +1.3073 |
| U_800 | 50 | +0.5958 | +0.8751 |
| G_600 | 50 | +2.1634 | +1.7242 |
| G_700 | 50 | +1.3552 | +1.2185 |
| G_800 | 50 | +0.5630 | +0.9929 |

## Same-delay census (output atoms; pair = two atoms with equal delay)

| world:variant | runs | mean n_pair | runs with pair | pairs | pairs on true delay | mean atoms | median |dnu| | SBL at iteration cap |
|---|---|---|---|---|---|---|---|---|
| real:S-diag | 300 | 31.9467 | 1.0000 | 9584 | 0.9990 | 23.75 | 0.500 | 0.337 |
| real:S-cov | 300 | 5.1433 | 0.9967 | 1543 | 0.8665 | 22.75 | 0.250 | 0.887 |
| syn:S-diag | 900 | 31.6444 | 1.0000 | 28480 | 0.9998 | 23.72 | 0.500 | 0.697 |
| syn:S-cov | 900 | 5.1833 | 0.9967 | 4665 | 0.9792 | 15.61 | 0.250 | 0.962 |
| syn:S-hard | 900 | 7.9278 | 1.0000 | 7135 | 0.8963 | 21.39 | 0.500 | 0.974 |
| syn:S-genie | 900 | 5.6644 | 0.9978 | 5098 | 0.9782 | 13.89 | 0.250 | 0.960 |

Phantom excess vs S-genie (synthetic, mean n_pair difference): S-diag +25.9800 [+24.9789, +26.9722]; S-cov -0.4811 [-0.6567, -0.3122]; S-hard +2.2633 [+2.0522, +2.4711]

## Real-observation runs vs the E-3 rows of the same keys (bit-identical counts)

{
 "keys_compared": 300,
 "identical": {
  "stage1_atoms": 300,
  "round1_sha": 300,
  "n_candidates": 300,
  "S-diag_atoms": 300,
  "S-diag_nmse": 300,
  "S-diag_sbl": 300,
  "S-diag_pairs": 300,
  "S-cov_atoms": 300,
  "S-cov_nmse": 300,
  "S-cov_sbl": 300,
  "S-cov_pairs": 300
 }
}

## Cost

{
 "keys": 300,
 "per_key": {
  "stage1_screen": 0.017937987785165508,
  "stage1_sbl": 0.3172499285452068,
  "round1_detect": 0.028956053539489705,
  "round1_decode": 0.025492882436762253,
  "stage2_screen": 0.2441604873475929,
  "total": 35.853126975451595
 },
 "gen_seconds_per_key": 0.11719755489689608,
 "mean_sbl_seconds": 2.4974383531516375,
 "sbl_runs_per_key": 14.0,
 "total_core_hours": 2.997527044195708,
 "cap_core_hours": 3.0
}
