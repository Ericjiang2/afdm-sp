# E-3 aggregate

interpretable: True; gates_all_pass: True; units: 9600

integrity: {"n_rows": 9600, "n_keys": 9600, "n_error_rows": 0, "worst_gamma_diag_rel_err": 4.37701716931253e-16, "cholesky_jitter_events": 0, "non_converged_sbl": 33240, "problems": [], "ok": true}

## Verdict: **MECHANISM-ONLY**

X1-diag=True  X1-hard=True  X2=True  X3=False (McNemar significant: False, FER-diff CI_lo > 0: False)

## Phantom excess E_v = mean(n_pair | v) - mean(n_pair | L-genie) (cluster bootstrap 20000 resamples, seed 20261017); CI contains 0: not significant != equivalent

| variant | E_v | 95% CI | width | contains 0 |
|---|---|---|---|---|
| L-hard | +0.19531 | [+0.12114, +0.26792] | 0.14677 | False |
| L-diag | +18.20656 | [+17.88302, +18.53792] | 0.65491 | False |
| L-cov | -0.39490 | [-0.47146, -0.31979] | 0.15167 | False |

R_ph = E_L-cov / E_L-diag: -0.0217 CI [-0.0260, -0.0175] (limit 0.25); denominator<=0 fraction 0.0000; evaluable True

## FER (unconditional)

| variant | FER | 95% CI |
|---|---|---|
| L-hard | 0.15031 | [0.14427, 0.15667] |
| L-diag | 0.10979 | [0.10458, 0.11510] |
| L-cov | 0.14854 | [0.14271, 0.15448] |
| L-genie | 0.01375 | [0.01156, 0.01604] |

FER(L-diag) - FER(L-cov): -0.03875 [-0.04375, -0.03385]

FER(L-hard) - FER(L-cov): +0.00177 [-0.00156, +0.00521]  (CI contains 0: not significant != equivalent)

## Exact one-sided McNemar (log10 p)

| test | b | c | log10 p |
|---|---|---|---|
| cov_better_than_diag | 78 | 450 | 0.0 |
| cov_better_than_hard | 141 | 124 | -0.8 |
| diag_better_than_cov | 450 | 78 | -64.2 |

## Co-delay census (final output atoms; pair = two atoms with equal delay)

| variant | units with pair | mean n_pair | excess vs genie | pairs | |D_N| hist [0,.2)/[.2,.5)/[.5,.8)/[.8,1] | pairs on true delay | mean atoms | median |dnu| |
|---|---|---|---|---|---|---|---|---|
| L-hard | 0.9994 | 5.6978 | +0.1953 | 54699 | 13227/3787/2995/34690 | 0.8840 | 20.22 | 0.250 |
| L-diag | 1.0000 | 23.7091 | +18.2066 | 227607 | 21489/31517/59270/115331 | 0.9987 | 21.09 | 0.250 |
| L-cov | 0.9973 | 5.1076 | -0.3949 | 49033 | 9802/2702/2049/34480 | 0.9173 | 19.47 | 0.250 |
| L-genie | 0.9995 | 5.5025 | +0.0000 | 52824 | 2509/2212/3507/44596 | 0.9859 | 13.87 | 0.250 |

NMSE (dB, median over units): stage 1 -8.94; L-hard -13.74; L-diag -14.07; L-cov -13.44; L-genie -23.35
round-1 FER (shared): 0.72948

## FER crossing of 0.01 (dB, per cell; interpolation of log10 FER)

| cell | L-hard | L-diag | L-cov | L-genie |
|---|---|---|---|---|
| U_300 | 10.44 | 8.10 | 10.37 | <=6.0 |
| U_500 | 7.78 | 7.65 | 7.79 | 6.57 |
| G_300 | 10.00 | 7.66 | 8.83 | <=6.0 |
| G_500 | 7.56 | 7.56 | 7.56 | 6.58 |

## Per cell and SNR: FER / mean n_pair / median NMSE dB

### U_300

| snr (centi-dB) | n | FER L-hard / L-diag / L-cov / L-genie | n_pair L-hard / L-diag / L-cov / L-genie | NMSE dB L-hard / L-diag / L-cov / L-genie |
|---|---|---|---|---|
| 600 | 400 | 0.5475 / 0.2250 / 0.5250 / 0.0000 | 5.080 / 34.065 / 4.588 / 5.577 | -10.5 / -11.8 / -10.2 / -20.4 |
| 700 | 400 | 0.1250 / 0.0300 / 0.1025 / 0.0000 | 5.505 / 32.502 / 4.870 / 5.265 | -11.3 / -12.3 / -11.0 / -21.9 |
| 800 | 400 | 0.0600 / 0.0125 / 0.0375 / 0.0000 | 5.790 / 29.948 / 4.970 / 5.235 | -11.9 / -12.8 / -11.7 / -23.1 |
| 900 | 400 | 0.0250 / 0.0000 / 0.0200 / 0.0000 | 6.010 / 27.462 / 5.122 / 5.215 | -12.3 / -12.9 / -12.1 / -24.1 |
| 1000 | 400 | 0.0125 / 0.0050 / 0.0150 / 0.0000 | 5.710 / 25.293 / 5.022 / 5.345 | -12.1 / -12.8 / -12.1 / -25.0 |
| 1100 | 400 | 0.0075 / 0.0025 / 0.0050 / 0.0000 | 5.940 / 22.755 / 5.285 / 5.480 | -12.0 / -12.7 / -12.0 / -25.4 |

### U_500

| snr (centi-dB) | n | FER L-hard / L-diag / L-cov / L-genie | n_pair L-hard / L-diag / L-cov / L-genie | NMSE dB L-hard / L-diag / L-cov / L-genie |
|---|---|---|---|---|
| 600 | 400 | 0.9000 / 0.9100 / 0.9275 / 0.1500 | 5.808 / 35.355 / 4.815 / 5.555 | -13.6 / -13.6 / -13.1 / -20.4 |
| 700 | 400 | 0.1175 / 0.1375 / 0.1425 / 0.0000 | 6.025 / 33.070 / 4.713 / 5.268 | -14.9 / -14.5 / -14.5 / -21.9 |
| 800 | 400 | 0.0050 / 0.0025 / 0.0050 / 0.0000 | 5.540 / 21.163 / 4.905 / 5.207 | -18.3 / -17.8 / -18.3 / -23.3 |
| 900 | 400 | 0.0000 / 0.0000 / 0.0000 / 0.0000 | 5.223 / 9.203 / 5.107 / 5.230 | -24.0 / -24.1 / -24.0 / -24.3 |
| 1000 | 400 | 0.0000 / 0.0000 / 0.0000 / 0.0000 | 5.327 / 6.713 / 5.303 / 5.375 | -25.1 / -25.2 / -25.1 / -25.2 |
| 1100 | 400 | 0.0000 / 0.0000 / 0.0000 / 0.0000 | 5.423 / 6.878 / 5.395 / 5.420 | -25.6 / -25.7 / -25.6 / -25.8 |

### G_300

| snr (centi-dB) | n | FER L-hard / L-diag / L-cov / L-genie | n_pair L-hard / L-diag / L-cov / L-genie | NMSE dB L-hard / L-diag / L-cov / L-genie |
|---|---|---|---|---|
| 600 | 400 | 0.5575 / 0.2625 / 0.5750 / 0.0000 | 5.295 / 33.837 / 4.683 / 5.878 | -10.4 / -11.8 / -10.1 / -20.2 |
| 700 | 400 | 0.1550 / 0.0175 / 0.1175 / 0.0000 | 5.645 / 31.675 / 4.933 / 5.617 | -11.2 / -12.3 / -11.0 / -21.6 |
| 800 | 400 | 0.0550 / 0.0075 / 0.0425 / 0.0000 | 5.832 / 29.538 / 5.122 / 5.617 | -11.8 / -12.8 / -11.6 / -23.1 |
| 900 | 400 | 0.0150 / 0.0000 / 0.0075 / 0.0000 | 5.985 / 26.780 / 5.330 / 5.492 | -12.0 / -12.9 / -12.0 / -24.1 |
| 1000 | 400 | 0.0100 / 0.0000 / 0.0075 / 0.0000 | 6.157 / 24.860 / 5.508 / 5.615 | -12.1 / -12.8 / -12.0 / -24.9 |
| 1100 | 400 | 0.0025 / 0.0000 / 0.0000 / 0.0000 | 6.048 / 23.085 / 5.487 / 5.750 | -12.0 / -12.7 / -12.0 / -25.4 |

### G_500

| snr (centi-dB) | n | FER L-hard / L-diag / L-cov / L-genie | n_pair L-hard / L-diag / L-cov / L-genie | NMSE dB L-hard / L-diag / L-cov / L-genie |
|---|---|---|---|---|
| 600 | 400 | 0.8650 / 0.8825 / 0.8875 / 0.1800 | 5.890 / 35.010 / 4.838 / 5.920 | -13.5 / -13.6 / -13.1 / -20.2 |
| 700 | 400 | 0.1475 / 0.1400 / 0.1475 / 0.0000 | 5.907 / 32.615 / 4.850 / 5.692 | -14.8 / -14.5 / -14.5 / -21.7 |
| 800 | 400 | 0.0000 / 0.0000 / 0.0000 / 0.0000 | 5.770 / 22.517 / 5.032 / 5.505 | -17.6 / -16.7 / -17.2 / -23.0 |
| 900 | 400 | 0.0000 / 0.0000 / 0.0000 / 0.0000 | 5.513 / 10.457 / 5.428 / 5.455 | -23.8 / -23.9 / -23.7 / -24.1 |
| 1000 | 400 | 0.0000 / 0.0000 / 0.0000 / 0.0000 | 5.593 / 7.312 / 5.567 / 5.622 | -24.8 / -24.9 / -24.8 / -25.0 |
| 1100 | 400 | 0.0000 / 0.0000 / 0.0000 / 0.0000 | 5.732 / 6.925 / 5.710 / 5.723 | -25.7 / -25.7 / -25.6 / -25.7 |

## SBL runs hitting max_iter (stop rule 1e-4 not met within 100 iterations)

stage 1 (shared): 0.9867; stage 2: L-hard 0.9553; L-diag 0.6128; L-cov 0.9349; L-genie 0.9595

## R-iter robustness check (report-only, pre-registered): 100 vs 400 iterations on the frozen keys

keys: 200 matched (200 riter rows, 0 errors); reused-pipeline mismatches vs main rows: 0
genie mean n_pair (100 iterations, unchanged): 5.7250

| variant | iters | mean n_pair | genie excess | FER | share at iteration cap |
|---|---|---|---|---|---|
| L-diag | 100 | 23.5800 | +17.8550 | 0.1000 | 0.6350 |
| L-diag | 400 | 23.6450 | +17.9200 | 0.1000 | 0.0000 |
| L-cov | 100 | 5.2800 | -0.4450 | 0.1400 | 0.9550 |
| L-cov | 400 | 5.3800 | -0.3450 | 0.1400 | 0.0100 |

FLAG: **not budget-dependent**  (L-diag genie excess at 400 iterations < 50% of its 100-iteration excess on the same keys -> X1-diag labelled "budget-dependent")

## Cost (mean seconds per key)

{
 "keys": 9600,
 "per_key": {
  "stage1_screen": 0.027144148262304952,
  "stage1_sbl": 0.43549816458073715,
  "round1_detect": 0.034297021789971044,
  "round1_decode": 0.026276440360525156,
  "stage2_screen": 0.27486967314088057,
  "total": 14.00025569111977
 },
 "gen_seconds_per_key": 0.03924069325187399,
 "variants": {
  "L-hard": {
   "columns": 0.06062521326375039,
   "sbl": 3.2316259894718438,
   "detect": 0.031575068523864804,
   "decode": 0.021151733843241042,
   "total": 3.345300597194388,
   "sbl_iterations_mean": 99.55145833333333,
   "sbl_start_atoms_mean": 628.7291666666666
  },
  "L-diag": {
   "columns": 0.004888195076152139,
   "sbl": 3.0918241323604403,
   "detect": 0.03218397174733885,
   "decode": 0.02060258443079268,
   "total": 3.1500873526007247,
   "sbl_iterations_mean": 94.93145833333334,
   "sbl_start_atoms_mean": 628.7291666666666
  },
  "L-cov": {
   "columns": 0.06166463952535802,
   "sbl": 3.226749598089324,
   "detect": 0.030938783877451595,
   "decode": 0.02105279575538589,
   "total": 3.3407361058979586,
   "sbl_iterations_mean": 99.325,
   "sbl_start_atoms_mean": 628.7291666666666
  },
  "L-genie": {
   "columns": 0.06215584255405702,
   "sbl": 3.2353398427806193,
   "detect": 0.026914681958248064,
   "decode": 0.019514599901837452,
   "total": 3.34423794110359,
   "sbl_iterations_mean": 99.57552083333333,
   "sbl_start_atoms_mean": 628.7291666666666
  }
 },
 "total_core_hours": 37.43865702499105
}

## Calibrated SNR grid (frozen rule, L-hard only)

{
 "rule": "per (scenario, rho) cell: s0 = smallest candidate SNR in {4..14} dB with L-hard unconditional FER <= .9; grid {s0..s0+5} truncated at 14; L-hard FER(14 dB) > .9 -> UNINFORMATIVE",
 "fer_metric": "fraction of calibration frames with >= 1 information-bit error after round 2 (L-hard)",
 "frames": [
  6000,
  6100
 ],
 "cells": {
  "U_300": {
   "fer_by_snr": {
    "4": 1.0,
    "5": 0.94,
    "6": 0.55,
    "7": 0.15,
    "8": 0.08,
    "9": 0.04,
    "10": 0.02,
    "11": 0.01,
    "12": 0.0,
    "13": 0.0,
    "14": 0.0
   },
   "status": "OK",
   "s0": 6,
   "grid_db": [
    6,
    7,
    8,
    9,
    10,
    11
   ]
  },
  "U_500": {
   "fer_by_snr": {
    "4": 1.0,
    "5": 1.0,
    "6": 0.84,
    "7": 0.11,
    "8": 0.0,
    "9": 0.0,
    "10": 0.0,
    "11": 0.0,
    "12": 0.0,
    "13": 0.01,
    "14": 0.01
   },
   "status": "OK",
   "s0": 6,
   "grid_db": [
    6,
    7,
    8,
    9,
    10,
    11
   ]
  },
  "G_300": {
   "fer_by_snr": {
    "4": 1.0,
    "5": 0.98,
    "6": 0.55,
    "7": 0.18,
    "8": 0.09,
    "9": 0.04,
    "10": 0.01,
    "11": 0.01,
    "12": 0.01,
    "13": 0.0,
    "14": 0.01
   },
   "status": "OK",
   "s0": 6,
   "grid_db": [
    6,
    7,
    8,
    9,
    10,
    11
   ]
  },
  "G_500": {
   "fer_by_snr": {
    "4": 1.0,
    "5": 1.0,
    "6": 0.88,
    "7": 0.11,
    "8": 0.01,
    "9": 0.0,
    "10": 0.0,
    "11": 0.0,
    "12": 0.0,
    "13": 0.0,
    "14": 0.0
   },
   "status": "OK",
   "s0": 6,
   "grid_db": [
    6,
    7,
    8,
    9,
    10,
    11
   ]
  }
 },
 "n_rows": 4400
}
