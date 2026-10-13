# Headroom analysis

runs: smoke/pop144  |  B=2000 B_aux=2000 seed=20261008 T=11.513 N=1024 ref_rho=0.5  |  units=144 rows_ok_dups_skipped=0 error_rows=0

FER = info_errors>0. dec_fail = syndrome!=0; undet = syndrome==0 & info_errors>0. `*` = CI from <95% finite bootstrap draws. dB columns: shift=x(rho)-x(ref); to_A3=x(arm)-x(A3); step=x(prev)-x(next) (>0 recovered).

## 1. Per (rho, snr, arm)

| rho | snr | arm | n | err | FER | Wilson95 | dec_fail | undet | BER | logloss | sec | trig |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5 | 6.0 | F0 | 48 | 10 | 0.208 | [0.117, 0.343] | 10 | 0 | 1.74e-02 | 0.3838 | 0.27 |  |
| 0.5 | 6.0 | A0 | 48 | 4 | 0.083 | [0.033, 0.196] | 4 | 0 | 6.12e-03 | 0.3721 | 0.31 | 0.208 |
| 0.5 | 6.0 | A1 | 48 | 6 | 0.125 | [0.059, 0.247] | 6 | 0 | 8.95e-03 | 0.3604 | 0.27 |  |
| 0.5 | 6.0 | A2 | 48 | 4 | 0.083 | [0.033, 0.196] | 4 | 0 | 4.17e-03 | 0.3462 | 0.17 |  |
| 0.5 | 6.0 | A3 | 48 | 1 | 0.021 | [0.004, 0.109] | 1 | 0 | 1.67e-03 | 0.3178 | 0.17 |  |
| 0.5 | 6.5 | F0 | 48 | 1 | 0.021 | [0.004, 0.109] | 1 | 0 | 1.16e-03 | 0.2888 | 0.26 |  |
| 0.5 | 6.5 | A0 | 48 | 0 | 0.000 | [0.000, 0.074] | 0 | 0 | 0.00e+00 | 0.2864 | 0.27 | 0.021 |
| 0.5 | 6.5 | A1 | 48 | 0 | 0.000 | [0.000, 0.074] | 0 | 0 | 0.00e+00 | 0.2685 | 0.27 |  |
| 0.5 | 6.5 | A2 | 48 | 0 | 0.000 | [0.000, 0.074] | 0 | 0 | 0.00e+00 | 0.2713 | 0.17 |  |
| 0.5 | 6.5 | A3 | 48 | 0 | 0.000 | [0.000, 0.074] | 0 | 0 | 0.00e+00 | 0.2425 | 0.16 |  |
| 0.5 | 7.0 | F0 | 48 | 1 | 0.021 | [0.004, 0.109] | 1 | 0 | 2.79e-03 | 0.2474 | 0.26 |  |
| 0.5 | 7.0 | A0 | 48 | 0 | 0.000 | [0.000, 0.074] | 0 | 0 | 0.00e+00 | 0.2437 | 0.27 | 0.021 |
| 0.5 | 7.0 | A1 | 48 | 0 | 0.000 | [0.000, 0.074] | 0 | 0 | 0.00e+00 | 0.2205 | 0.27 |  |
| 0.5 | 7.0 | A2 | 48 | 0 | 0.000 | [0.000, 0.074] | 0 | 0 | 0.00e+00 | 0.2189 | 0.17 |  |
| 0.5 | 7.0 | A3 | 48 | 0 | 0.000 | [0.000, 0.074] | 0 | 0 | 0.00e+00 | 0.2017 | 0.16 |  |

## 2. Ladder (paired by frame)

| rho | snr | step | n | fail_prev | fail_next | rescues | harms | McNemar p | dLogloss [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| 0.5 | 6.0 | F0->A0 | 48 | 10 | 4 | 6 | 0 | 0.0312 | -0.0117 [-0.0202, -0.0047] |
| 0.5 | 6.0 | A0->A1 | 48 | 4 | 6 | 0 | 2 | 0.5000 | -0.0117 [-0.0227, -0.0009] |
| 0.5 | 6.0 | A1->A2 | 48 | 6 | 4 | 2 | 0 | 0.5000 | -0.0142 [-0.0258, -0.0026] |
| 0.5 | 6.0 | A2->A3 | 48 | 4 | 1 | 3 | 0 | 0.2500 | -0.0284 [-0.0395, -0.0188] |
| 0.5 | 6.5 | F0->A0 | 48 | 1 | 0 | 1 | 0 | 1.0000 | -0.0024 [-0.0073, 0.0000] |
| 0.5 | 6.5 | A0->A1 | 48 | 0 | 0 | 0 | 0 | 1.0000 | -0.0178 [-0.0284, -0.0093] |
| 0.5 | 6.5 | A1->A2 | 48 | 0 | 0 | 0 | 0 | 1.0000 | 0.0028 [-0.0059, 0.0127] |
| 0.5 | 6.5 | A2->A3 | 48 | 0 | 0 | 0 | 0 | 1.0000 | -0.0288 [-0.0416, -0.0169] |
| 0.5 | 7.0 | F0->A0 | 48 | 1 | 0 | 1 | 0 | 1.0000 | -0.0036 [-0.0108, 0.0000] |
| 0.5 | 7.0 | A0->A1 | 48 | 0 | 0 | 0 | 0 | 1.0000 | -0.0233 [-0.0391, -0.0111] |
| 0.5 | 7.0 | A1->A2 | 48 | 0 | 0 | 0 | 0 | 1.0000 | -0.0016 [-0.0060, 0.0015] |
| 0.5 | 7.0 | A2->A3 | 48 | 0 | 0 | 0 | 0 | 1.0000 | -0.0172 [-0.0210, -0.0149] |
| 0.5 | ALL | F0->A0 | 144 | 12 | 4 | 8 | 0 | 0.0078 | -0.0059 [-0.0102, -0.0024] |
| 0.5 | ALL | A0->A1 | 144 | 4 | 6 | 0 | 2 | 0.5000 | -0.0176 [-0.0243, -0.0108] |
| 0.5 | ALL | A1->A2 | 144 | 6 | 4 | 2 | 0 | 0.5000 | -0.0043 [-0.0097, 0.0011] |
| 0.5 | ALL | A2->A3 | 144 | 4 | 1 | 3 | 0 | 0.2500 | -0.0248 [-0.0303, -0.0198] |

Fraction of A0 failures rescued by arm (vs A0, independent):

| rho | snr | arm | A0 fails | rescued | frac |
|---|---|---|---|---|---|
| 0.5 | 6.0 | A1 | 4 | 0 | 0.000 |
| 0.5 | 6.0 | A2 | 4 | 1 | 0.250 |
| 0.5 | 6.0 | A3 | 4 | 3 | 0.750 |
| 0.5 | 6.5 | A1 | 0 | 0 | - |
| 0.5 | 6.5 | A2 | 0 | 0 | - |
| 0.5 | 6.5 | A3 | 0 | 0 | - |
| 0.5 | 7.0 | A1 | 0 | 0 | - |
| 0.5 | 7.0 | A2 | 0 | 0 | - |
| 0.5 | 7.0 | A3 | 0 | 0 | - |
| 0.5 | ALL | A1 | 4 | 0 | 0.000 |
| 0.5 | ALL | A2 | 4 | 1 | 0.250 |
| 0.5 | ALL | A3 | 4 | 3 | 0.750 |

## 3. dB at FER targets

| target | rho | arm | crossing SNR dB [CI] | note |
|---|---|---|---|---|
| 0.1 | 0.5 | F0 | 6.16 [6.02, 6.35] |  |
| 0.1 | 0.5 | A0 | - | FER<=target at lowest SNR (no bracket) |
| 0.1 | 0.5 | A1 | 6.04 [6.01, 6.13]* |  |
| 0.1 | 0.5 | A2 | - | FER<=target at lowest SNR (no bracket) |
| 0.1 | 0.5 | A3 | - | FER<=target at lowest SNR (no bracket) |
| 0.01 | 0.5 | F0 | - | FER>target at all SNR |
| 0.01 | 0.5 | A0 | 6.50 [6.50, 6.50] | ok; zero-FER floor 0.5/n above target (resolution-limited) |
| 0.01 | 0.5 | A1 | 6.50 [6.50, 6.50] | ok; zero-FER floor 0.5/n above target (resolution-limited) |
| 0.01 | 0.5 | A2 | 6.50 [6.50, 6.50] | ok; zero-FER floor 0.5/n above target (resolution-limited) |
| 0.01 | 0.5 | A3 | 6.50 [6.50, 6.50]* | ok; zero-FER floor 0.5/n above target (resolution-limited) |

### dB gap to A3 (same rho)

| target | rho | arm | dB [CI] |
|---|---|---|---|
| 0.1 | 0.5 | F0 | - |
| 0.1 | 0.5 | A0 | - |
| 0.1 | 0.5 | A1 | - |
| 0.1 | 0.5 | A2 | - |
| 0.01 | 0.5 | F0 | - |
| 0.01 | 0.5 | A0 | 0.00 [0.00, 0.00]* |
| 0.01 | 0.5 | A1 | 0.00 [0.00, 0.00]* |
| 0.01 | 0.5 | A2 | 0.00 [0.00, 0.00]* |

### ladder step dB recovered (kill / route rules)

| target | rho | step | dB [CI] |
|---|---|---|---|
| 0.1 | 0.5 | A0->A1 | - |
| 0.1 | 0.5 | A1->A2 | - |
| 0.1 | 0.5 | A2->A3 | - |
| 0.01 | 0.5 | A0->A1 | 0.00 [0.00, 0.00] |
| 0.01 | 0.5 | A1->A2 | 0.00 [0.00, 0.00] |
| 0.01 | 0.5 | A2->A3 | 0.00 [0.00, 0.00]* |

- target 0.1 rho 0.5: A0->A3 - dB; A0->A1 share -; A1->A3 - dB; local<0.1dB rule None; acquisition share>=0.5 rule None
- target 0.01 rho 0.5: A0->A3 0.00 [0.00, 0.00]* dB; A0->A1 share -; A1->A3 0.00 [0.00, 0.00]* dB; local<0.1dB rule True; acquisition share>=0.5 rule None

## 4. Prediction checks

### P1: A0 FER vs rho (argmin; interior; non-monotone; bootstrap argmin frequency)

n/a (need >=2 rho and A0)

### P2: A3 shift vs 10log10((1-ref)/(1-rho)); tol 0.15 dB

n/a

### P3: AUC for A0 failure (T=11.513 gamma threshold; AUC>0.5 = predictor larger on failures)

| rho | predictor | n | fails | AUC pooled [CI] | AUC within-SNR mean (cells) |
|---|---|---|---|---|---|
| 0.5 | E_miss(T) | 144 | 4 | 0.443 [0.134, 0.811] | 0.466 (1) |
| 0.5 | A0_missed_energy_fraction | 144 | 4 | 0.564 [0.217, 0.939] | 0.534 (1) |
| 0.5 | same_delay_underfit | 144 | 4 | 0.536 [0.387, 0.886] | 0.545 (1) |
| 0.5 | n_distinct_delays<n_paths | 144 | 4 | 0.521 [0.370, 0.871] | 0.534 (1) |

E_miss T-sensitivity (point AUC pooled): T=9.21 rho=0.5: 0.537; T=11.51 rho=0.5: 0.443; T=13.82 rho=0.5: 0.653

mean E_miss by cell: 0.5/6.0: 0.0080; 0.5/6.5: 0.0106; 0.5/7.0: 0.0072

## Notes

- cross-check vs driver results.json summary (frames, frame_errors per cell): 0 mismatching cells
- sigma2 not stored in rows: derived as 10^(-snr_db/10) (driver asserts this for obs); N and K_INFO=1024 are constants; truth_g2/pdp_total/n_paths/n_distinct_delays come from rows (truth_g2 sorted desc).
- smoke/pop144/fer_curves.png
