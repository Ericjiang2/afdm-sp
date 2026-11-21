# Saved-row readouts, 2026-11-19

All eight analyses are **post hoc**. Claude wrote the decision rules before this batch was computed. These rules are applied to previously collected data. The batch performs zero receiver, detector or decoder calls and generates zero frames.

The physical frame is the resampling unit wherever a bootstrap is used. The seed, 10,000 draws per analysis and frozen source manifest fingerprints are recorded in `readouts.json`. Intervals are two-sided 95% unless the table marks a deterministic count bound.

Threshold outcomes describe the specified archived contrasts. Mechanistic explanations remain untested by interventions in this batch.

## R-A

**Source:** `slot_mismatch_20261019/out/main_20261118/rows_shard*.jsonl.gz`.

**Fields:** `family`, `frame`, `scenario`, `rho_permille`, `snr_centi_db`, `truth.delays` for pairing, `s['8'].f0.info_errors`, `s['8'].triggered`, `s['8'].arms.A1c.info_errors`, and `A3.info_errors`.

The 32,000 family-M rows contain 1,000 physical frames (10000–10999),
shared across both scenarios, both pilot fractions and all eight SNR points (4.5–8.0 dB).
The 95% percentile intervals use 10,000 frame-bootstrap replicates with one
shared resample across every curve. The frozen routine interpolates the first 1%
crossing on log FER (frame error rate) and retains unbounded endpoints when the
crossing is outside the grid. Crossing, gap and contrast units are dB.

| Scenario | ρ | Arm | 1% crossing | 95% interval |
|---|---:|---|---:|---|
| G | 0.3 | F0 | 7.000 | [6.500, inf] |
| G | 0.3 | B_8 | 5.151 | [5.037, 5.283] |
| G | 0.3 | A3 | 4.679 | [4.624, 4.774] |
| G | 0.5 | F0 | 6.651 | [6.585, 6.752] |
| G | 0.5 | B_8 | 6.219 | [6.172, 6.310] |
| G | 0.5 | A3 | 6.121 | [6.068, 6.150] |
| U | 0.3 | F0 | 6.446 | [6.183, 6.821] |
| U | 0.3 | B_8 | 5.244 | [5.088, 5.420] |
| U | 0.3 | A3 | 4.658 | [4.628, 4.679] |
| U | 0.5 | F0 | 6.686 | [6.585, 6.810] |
| U | 0.5 | B_8 | 6.225 | [6.180, 6.314] |
| U | 0.5 | A3 | 6.142 | [6.104, 6.165] |

| Scenario | Arm | Gap at ρ=.3 (95% interval) | Gap at ρ=.5 (95% interval) | Δ | 95% interval for Δ | Rule |
|---|---|---|---|---:|---|---|
| G | F0 | 2.321 ([1.846, inf]) | 0.530 ([0.464, 0.640]) | 1.792 | [1.305, inf] | pass |
| G | B_8 | 0.472 ([0.328, 0.611]) | 0.098 ([0.048, 0.192]) | 0.374 | [0.210, 0.519] | pass |
| U | F0 | 1.788 ([1.522, 2.161]) | 0.544 ([0.448, 0.666]) | 1.244 | [0.956, 1.636] | pass |
| U | B_8 | 0.586 ([0.437, 0.764]) | 0.083 ([0.035, 0.174]) | 0.503 | [0.332, 0.689] | pass |

Both scenarios must meet Δ_F0 lower >0.50 dB and Δ_B_8 upper <0.75 dB.

**Rule outcome:** Survives.

## R-B1

**Source:** sbl_residual_gap_20261119/out/main_v2_20261119.

**Fields:** `row.frame`, `snr_centi_db`, `scenario`, `row.variants[arm].sbl.{beta,converged,iterations}`, `n_pair` and `nmse`. Saved `K` and `KM` are K′ and KM′.

Each stratum has 400 paired keys (200 physical frames × 2 scenarios). Brackets are frame-cluster bootstrap 95% intervals. Pair counts are output counts after refinement.

| SNR (dB) | Arm | β mean | EM converged (%) | EM iterations (mean) | Co-delay pairs (mean, total) | NMSE mean |
|---:|---|---:|---:|---:|---:|---:|
| 6 | R0 | 4.829 [4.806, 4.851] | 94.8 [92.5, 96.8] | 85.86 [84.92, 86.82] | 33.99 [33.36, 34.66] (13,595) | 0.0458 [0.0437, 0.0480] |
| 6 | U2 | 3.141 [3.125, 3.157] | 3.8 [2.0, 5.8] | 99.85 [99.71, 99.95] | 26.59 [26.18, 27.02] (10,637) | 0.0725 [0.0697, 0.0753] |
| 6 | K′ | 4.813 [4.791, 4.836] | 95.2 [93.0, 97.2] | 85.76 [84.82, 86.70] | 34.28 [33.63, 34.99] (13,714) | 0.0666 [0.0641, 0.0691] |
| 6 | M | 3.141 [3.125, 3.157] | 3.8 [2.0, 5.8] | 99.85 [99.71, 99.95] | 26.59 [26.18, 27.02] (10,637) | 0.0503 [0.0478, 0.0528] |
| 6 | KM′ | 4.813 [4.791, 4.836] | 95.2 [93.0, 97.2] | 85.76 [84.82, 86.70] | 34.28 [33.63, 34.99] (13,714) | 0.0452 [0.0430, 0.0474] |
| 7 | R0 | 5.292 [5.252, 5.335] | 71.0 [65.8, 75.8] | 92.52 [91.65, 93.39] | 32.20 [31.60, 32.80] (12,881) | 0.0380 [0.0358, 0.0402] |
| 7 | U2 | 3.658 [3.615, 3.710] | 3.5 [1.8, 5.5] | 99.89 [99.81, 99.95] | 25.93 [25.49, 26.37] (10,373) | 0.0616 [0.0588, 0.0643] |
| 7 | K′ | 5.277 [5.237, 5.320] | 71.2 [66.2, 75.8] | 92.48 [91.60, 93.36] | 32.55 [31.93, 33.17] (13,021) | 0.0574 [0.0548, 0.0601] |
| 7 | M | 3.658 [3.615, 3.710] | 3.5 [1.8, 5.5] | 99.89 [99.81, 99.95] | 25.93 [25.49, 26.37] (10,373) | 0.0418 [0.0395, 0.0441] |
| 7 | KM′ | 5.277 [5.237, 5.320] | 71.2 [66.2, 75.8] | 92.48 [91.60, 93.36] | 32.55 [31.93, 33.17] (13,021) | 0.0378 [0.0356, 0.0400] |
| 8 | R0 | 5.826 [5.732, 5.928] | 42.2 [37.0, 47.8] | 97.11 [96.48, 97.70] | 29.62 [28.91, 30.32] (11,850) | 0.0331 [0.0310, 0.0352] |
| 8 | U2 | 4.317 [4.200, 4.446] | 2.8 [1.2, 4.5] | 99.88 [99.78, 99.97] | 24.90 [24.32, 25.47] (9,960) | 0.0523 [0.0497, 0.0550] |
| 8 | K′ | 5.812 [5.717, 5.914] | 40.8 [35.5, 46.0] | 97.14 [96.52, 97.73] | 29.82 [29.09, 30.53] (11,927) | 0.0497 [0.0471, 0.0523] |
| 8 | M | 4.317 [4.200, 4.446] | 2.8 [1.2, 4.5] | 99.88 [99.78, 99.97] | 24.90 [24.32, 25.47] (9,960) | 0.0357 [0.0335, 0.0380] |
| 8 | KM′ | 5.812 [5.717, 5.914] | 40.8 [35.5, 46.0] | 97.14 [96.52, 97.73] | 29.82 [29.09, 30.53] (11,927) | 0.0330 [0.0309, 0.0351] |
| 9 | R0 | 6.181 [6.019, 6.358] | 15.0 [11.2, 19.0] | 99.00 [98.67, 99.31] | 27.22 [26.48, 27.92] (10,887) | 0.0325 [0.0303, 0.0347] |
| 9 | U2 | 4.886 [4.699, 5.095] | 2.0 [0.8, 3.5] | 99.87 [99.74, 99.98] | 23.27 [22.67, 23.86] (9,310) | 0.0488 [0.0462, 0.0515] |
| 9 | K′ | 6.169 [6.007, 6.346] | 14.8 [11.2, 18.5] | 98.95 [98.60, 99.27] | 27.40 [26.66, 28.11] (10,961) | 0.0468 [0.0442, 0.0494] |
| 9 | M | 4.886 [4.699, 5.095] | 2.0 [0.8, 3.5] | 99.87 [99.74, 99.98] | 23.27 [22.67, 23.86] (9,310) | 0.0346 [0.0325, 0.0368] |
| 9 | KM′ | 6.169 [6.007, 6.346] | 14.8 [11.2, 18.5] | 98.95 [98.60, 99.27] | 27.40 [26.66, 28.11] (10,961) | 0.0324 [0.0302, 0.0346] |
| 10 | R0 | 6.234 [6.045, 6.437] | 3.2 [1.8, 5.0] | 99.84 [99.73, 99.94] | 24.97 [24.41, 25.54] (9,988) | 0.0358 [0.0336, 0.0379] |
| 10 | U2 | 5.138 [4.935, 5.358] | 1.5 [0.5, 2.8] | 99.94 [99.86, 99.99] | 22.08 [21.55, 22.60] (8,832) | 0.0501 [0.0476, 0.0527] |
| 10 | K′ | 6.223 [6.034, 6.426] | 3.2 [1.8, 5.0] | 99.85 [99.74, 99.94] | 25.10 [24.54, 25.68] (10,040) | 0.0484 [0.0459, 0.0510] |
| 10 | M | 5.138 [4.935, 5.358] | 1.5 [0.5, 2.8] | 99.94 [99.86, 99.99] | 22.08 [21.55, 22.60] (8,832) | 0.0377 [0.0355, 0.0398] |
| 10 | KM′ | 6.223 [6.034, 6.426] | 3.2 [1.8, 5.0] | 99.85 [99.74, 99.94] | 25.10 [24.54, 25.68] (10,040) | 0.0358 [0.0336, 0.0380] |
| 11 | R0 | 6.327 [6.097, 6.576] | 2.0 [0.8, 3.8] | 99.88 [99.78, 99.96] | 23.05 [22.53, 23.59] (9,222) | 0.0399 [0.0378, 0.0420] |
| 11 | U2 | 5.424 [5.183, 5.684] | 1.0 [0.2, 2.0] | 99.96 [99.91, 100.00] | 20.60 [20.15, 21.05] (8,241) | 0.0525 [0.0500, 0.0549] |
| 11 | K′ | 6.317 [6.087, 6.566] | 1.5 [0.5, 2.8] | 99.90 [99.81, 99.97] | 23.24 [22.73, 23.77] (9,297) | 0.0507 [0.0483, 0.0531] |
| 11 | M | 5.424 [5.183, 5.684] | 1.0 [0.2, 2.0] | 99.96 [99.91, 100.00] | 20.60 [20.15, 21.05] (8,241) | 0.0417 [0.0396, 0.0439] |
| 11 | KM′ | 6.317 [6.087, 6.566] | 1.5 [0.5, 2.8] | 99.90 [99.81, 99.97] | 23.24 [22.73, 23.77] (9,297) | 0.0398 [0.0377, 0.0418] |

Restoration is described by distance to R0 and a paired K′−R0 interval. The brief supplies no equivalence margin.

- At 6 dB, K′−R0 is -0.015 [-0.016, -0.015] for β and 0.5 [-0.8, 2.0] pp for convergence. Closer to R0 than U2 for β? Yes. For convergence? Yes.
- At 7 dB, K′−R0 is -0.015 [-0.016, -0.015] for β and 0.3 [-1.7, 2.3] pp for convergence. Closer to R0 than U2 for β? Yes. For convergence? Yes.
- At 8 dB, K′−R0 is -0.014 [-0.015, -0.014] for β and -1.5 [-3.5, 0.5] pp for convergence. Closer to R0 than U2 for β? Yes. For convergence? Yes.
- At 9 dB, K′−R0 is -0.013 [-0.013, -0.012] for β and -0.3 [-1.7, 1.2] pp for convergence. Closer to R0 than U2 for β? Yes. For convergence? Yes.
- At 10 dB, K′−R0 is -0.011 [-0.011, -0.011] for β and 0.0 [-1.5, 1.3] pp for convergence. Closer to R0 than U2 for β? Yes. For convergence? Yes.
- At 11 dB, K′−R0 is -0.009 [-0.010, -0.009] for β and -0.5 [-1.2, 0.0] pp for convergence. Closer to R0 than U2 for β? Yes. For convergence? Yes.

**Rule outcome:** Descriptive.

## R-B2

**Source:** sbl_residual_gap_20261119/out/main_v2_20261119.

**Fields:** `row.variants[arm].fer` is the archived `info_errors > 0` indicator. K′ and KM′ are saved as `K` and `KM`.

70 keys fail under U2 and succeed under R0. Paired intervals resample physical frames. 0 draws had an empty eligible set. KM′ rescues 69/70.

| K′ fixes | M fixes | Keys | Fraction % [95% CI] |
|---|---|---:|---:|
| False | False | 16 | 22.9 [12.9, 33.0] |
| False | True | 13 | 18.6 [9.5, 28.4] |
| True | False | 17 | 24.3 [14.5, 34.3] |
| True | True | 24 | 34.3 [23.9, 45.8] |

The cutoffs apply to the two off-diagonal point fractions.

**Rule outcome:** Two mechanisms.

## R-C1

**Source:** `ratio_sweep_20261118/out/main_v2_20261119/main_??.jsonl.gz`.

**Fields:** `frame`, `rho`, `R`, `defined`, and `arms[arm].pair.{phantom_gain,weak_gain,Q}`. The archived `weak_gain` is the designated true-delay gain. The main shards are named `main_??`.

24,000 defined rows out of 24,000 rows, pooled across both pilot fractions and all ratio settings. The 95% percentile intervals resample 1,000 physical frames across all settings together.

| Arm | Phantom gain > designated true-delay gain | Fraction [95% interval] |
|---|---:|---:|
| A2 | 21,858/24,000 | 0.911 [0.905, 0.917] |
| CODELAY | 51/24,000 | 0.002 [0.002, 0.003] |

**Survives.** The rule requires A2 ≥ 0.80 and CODELAY ≤ 0.30.

**Rule outcome:** Survives.

## R-C2

**Source:** `unified_cov_prospective_20261119/out/main_20261119/rows_shard*.jsonl`, `leg == 'cstate'`.

**Fields:** `key`, `row.{frame,syndrome}`, `row.arms[arm].{decision,first_edit_type}`, and `row.census.by_arm[arm].{nonempty_scored_trials,scored_trials}`. Two saved decisions identify a key reaching the second exchange round. The count includes all scored trials.

Both arms reached round 2 on 871 paired keys from 198 physical frames. Round 1 starts from the same support and scans the same candidate bank. The projector depends only on trial geometry, so the round-1 counts cancel exactly in the within-key difference. The archived census pools rounds and does not give the separate round-2 counts.

- C-lo minus C-hi had **+12,395,689** nonempty scored trials [95% interval +11,450,457, +13,356,421].
- The 789 keys where only C-lo added an atom at an existing delay in its first accepted edit contributed **+12,029,834** trials [95% interval +11,130,391, +12,959,457], or **97.0%** of the net difference [95.1%, 98.7%].
- Across all round-2 keys for each arm, the archived counts imply at least 69.9% nonempty trials for C-lo and at most 2.9% for C-hi. This uses 14,972,787 and 513,271 cumulative counts and 20,682,400 and 17,942,600 round-2 trials.

**First-step phantom drives the gap.** The rule requires a contribution of at least 80%. The 95% percentile intervals resample physical frames jointly across keys. The share excludes 0 bootstrap draws with a nonpositive net count.

**Rule outcome:** First-step phantom drives the gap.

## R-D

**Source:** `tcom_reference_frame_20261015/out/p1/rows_shard*.jsonl.gz` and `tcom_genie_support_20261016/out/main/rows_shard*.jsonl.gz`.

**Fields:** `scenario`, `rho_permille`, `snr_centi_db`, `frame`, `arms.F0.info_errors`, `arms.A3.info_errors`, and `arms['GS-set'].info_errors`. Pairing uses P1 truth and stream fingerprints and saved GS delay lists.

At 5 dB the October runs contain 2,000 physical frames per scenario and pilot
fraction. The validated join is on (scenario, pilot fraction, physical frame).
P1 hashes match across both fractions for the gains, information bits and noise,
and the two archives agree on the true delay multiset and set at every joined key.
The producer configurations share frame entropy, domain and P1 driver digest.
Their generator digests straddle commit `d727b09e`, which extended scenario S with
optional delay scaling and truncation. The U/G defaults execute the same draws.
Rescue rates use F0 failure at both fractions as the denominator and report 95%
Wilson intervals. The Astra rule compares low-ρ GS-set and high-ρ A3.

| Scenario | Common F0 failures | ρ | Arm | Rescued | Rate | 95% interval |
|---|---:|---:|---|---:|---:|---|
| G | 520 | 0.3 | GS-set | 441 | 84.8% | [81.5%, 87.6%] |
| G | 520 | 0.3 | A3 | 519 | 99.8% | [98.9%, 100.0%] |
| G | 520 | 0.5 | GS-set | 0 | 0.0% | [0.0%, 0.7%] |
| G | 520 | 0.5 | A3 | 7 | 1.3% | [0.7%, 2.8%] |
| U | 467 | 0.3 | GS-set | 401 | 85.9% | [82.4%, 88.7%] |
| U | 467 | 0.3 | A3 | 467 | 100.0% | [99.2%, 100.0%] |
| U | 467 | 0.5 | GS-set | 0 | 0.0% | [0.0%, 0.8%] |
| U | 467 | 0.5 | A3 | 4 | 0.9% | [0.3%, 2.2%] |

Thresholds are low-ρ 95% lower >75% and high-ρ 95% upper <10% in both scenarios.
- GS-set low / A3 high passes.
- GS-set low / GS-set high passes.
- A3 low / A3 high passes.

**Rule outcome:** Survives.

## R-E

**Source:** `doublet_conflict_20261119/out/main_20261119/rows.jsonl`, all 600 MIXED8 frames at 7 dB.

**Fields:** `truth.{delays,dopplers,gains}`, `arms.{CD,U}.{doublet_two_atoms,info_errors,decision}`, `syndrome`, and `arms.F0.doublets[].{separation,delay,atoms,omitted,power}`. The archive encodes each gain as [real, imag] and provides one row file.

The two gains are ordered by increasing Doppler. At the 0.35-bin gap, the Dirichlet-kernel phase is `π(N−1)Δν/N` with `N=1024`, using the producer's positive Doppler convention. The same phase aligns the gains for contrast `c` and gives the frame-center phase cosine.

| Delay | Cohort | n | Median c [95% interval] | Lift vs both [95% interval] | Mann–Whitney p | Rule |
|---:|---|---:|---:|---:|---:|---|
| 6 | both two-atom | 153 | 0.810 [0.745, 0.848] | — | — | — |
| 6 | CD-only two-atom | 9 | 0.273 [0.209, 0.494] | -0.537 [-0.612, -0.336] | 3.608e-05 | Fail |
| 6 | U-only failure | 2 | 0.548 [0.494, 0.601] | -0.262 [-0.341, -0.161] | 0.2282 | Fail |
| 22 | both two-atom | 75 | 0.827 [0.748, 0.855] | — | — | — |
| 22 | CD-only two-atom | 16 | 0.625 [0.542, 0.821] | -0.202 [-0.298, 0.014] | 0.01672 | Fail |
| 22 | U-only failure | 8 | 0.790 [0.273, 0.858] | -0.037 [-0.554, 0.062] | 0.1976 | Fail |

Lift intervals jointly resample physical frames within each delay. The p-values use the specified Mann–Whitney statistic with a two-sided alternative. Groups with overlapping memberships give descriptive p-values because samples share frames.

- Delay 6, CD-only two-atom: 0 shared, 1 undefined lift draws | U-only failure: 1 shared, 1329 undefined lift draws.
- Delay 22, CD-only two-atom: 0 shared, 0 undefined lift draws | U-only failure: 2 shared, 4 undefined lift draws.

The primary contrast uses every both-two-atom frame, as stated in the batch brief. The source idea cited 179 such frames, counting only keys where the U and CD decisions differed. Restricting only the reference cohort to that source definition gives the following sensitivity readout.

| Delay | Restricted reference n | CD-only lift [95% interval], p | U-only-failure lift [95% interval], p |
|---:|---:|---:|---:|
| 6 | 122 | -0.454 [-0.549, -0.269], 7.699e-05 | -0.179 [-0.282, -0.090], 0.3512 |
| 22 | 57 | -0.150 [-0.272, 0.077], 0.1268 | +0.014 [-0.505, 0.122], 0.5829 |

Omitted-energy shares pool saved energy in each phase group among triggered F0 frames with exactly one atom at the 0.35-bin doublet delay. Their 95% intervals resample frames within each phase group and delay. Phase is at the frame center.

| Delay | Anti-phase n | Anti-phase share [95% interval] | In-phase n | In-phase share [95% interval] | Difference [95% interval] | Rule |
|---:|---:|---:|---:|---:|---:|---|
| 6 | 87 | 0.412 [0.391, 0.434] | 19 | 0.020 [0.015, 0.025] | +0.392 [0.371, 0.415] | Pass |
| 22 | 85 | 0.440 [0.417, 0.464] | 67 | 0.014 [0.012, 0.016] | +0.426 [0.403, 0.450] | Pass |

**Selective harm does not survive; phase explanation of tolerance survives.** The selective-harm rule requires a lift ≥ 0.10 and p ≤ 0.05 in each within-delay comparison. The tolerance rule requires both within-delay lower bounds > 0.

**Rule outcome:** Selective harm does not survive; phase explanation of tolerance survives.

## R-F

**Source:** sigma2_dd_20261118/out/main_20261118.

**Fields:** `frame`, `snr_centi_db`, `sigma2`, `arms.DD.B.f0.syndrome` and `arms.DD.B.noise.{residual_power,uncertainty_power}`. Final outcome uses `arms.DD.B.info_errors`.

Pooled 4.5, 5.0, 5.5 and 6.0 dB. The cited agy I4 recipe stratifies by the syndrome after the second DD F0 round. Nonzero syndrome triggers continuation, and zero syndrome defines the decoded comparator. Within-trigger final failure and rescue are also shown to resolve the wording in the brief. r_norm uses all rows. c_ratio requires uncertainty power strictly greater than 0.05σ². Brackets are frame-cluster bootstrap intervals on medians.

| Cohort | r_norm n | r_norm median (IQR) [95% CI] | c_ratio n | c_ratio median (IQR) [95% CI] |
|---|---:|---:|---:|---:|
| F0 undecoded / trigger | 2413 | 0.807 (0.739–0.900) [0.800, 0.811] | 2413 | -0.308 (-0.390–-0.169) [-0.315, -0.299] |
| F0 decoded / no trigger | 1587 | 1.094 (1.045–1.143) [1.087, 1.102] | 290 | 0.240 (0.040–0.487) [0.196, 0.319] |
| Triggered / final failure | 2246 | 0.795 (0.736–0.877) [0.788, 0.800] | 2246 | -0.320 (-0.395–-0.207) [-0.329, -0.313] |
| Triggered / final rescue | 167 | 1.043 (0.972–1.120) [1.016, 1.060] | 167 | 0.086 (-0.056–0.243) [0.033, 0.124] |

Both median cutoffs apply to the F0 undecoded trigger cohort. The archived ratios do not directly isolate a residual cross term.

**Rule outcome:** Overfitting criterion met, cross-term kill criterion missed.

Aggregation CPU time was 0.004181 core-hours on one CPU process.
