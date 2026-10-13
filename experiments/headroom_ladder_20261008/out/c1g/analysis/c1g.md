# A5 per-frame maps / start dependence / long-run Kc (6.5 dB, rho .3)

I* (T1 EXIT, FER .5 linear) = 0.5770.  G = [0.42, 0.44, 0.46, 0.48, 0.5, 0.52, 0.54, 0.56].  Bootstrap: percentile, frame resample, B = 2000, seed 20261009.

## Verdicts

- A5-0 determinism: PASS  (clause 1: 600 frames, 0 mismatches, ll_in max |diff| 0.00e+00; clause 2: 600 frames, 0 mismatches, ll_in max |diff| 0.00e+00)
- A5-1 Kc vs frozen staircase (|ln| <= 0.15): PASS at R[1, 2, 3, 4, 5, 6]; FAIL at R[7, 8, 9, 10]; undefined at R[].  Kc_R: R1 76.8 (ln +0.012), R2 131.7 (ln +0.035), R3 159.0 (ln -0.003), R4 167.2 (ln +0.075), R5 172.3 (ln +0.084), R6 176.0 (ln +0.109), R7 177.4 (ln +0.163), R8 178.2 (ln +0.162), R9 179.6 (ln +0.154), R10 180.1 (ln +0.152)
- A5-1 prediction: FER_R10(L20) 0.313 [0.263,0.368] in [.02,.43] -> PASS; Kc_R10 180.1 [176.2,184.8] in [172,186] -> PASS
- A5-2a decode-by-R10 vs class: FAIL.  O L28 0.495 [0.399,0.592] n=99 >= .8 NO; O L32 0.286 [0.172,0.436] n=42 >= .8 NO; B u C L28 0.000 [0.000,0.019] n=201 <= .2 ok; B u C L32 0.000 [0.000,0.015] n=258 <= .2 ok
- A5-2b M2 FER_R10 vs observed (|diff| <= 0.06 at both L): FAIL.  L28 M2 0.743 vs obs 0.837, diff -0.093 [-0.127,-0.060], M0 first-success round None, per-frame agreement at R10 0.893; L32 M2 0.913 vs obs 0.960, diff -0.047 [-0.073,-0.023], M0 first-success round None, per-frame agreement at R10 0.947
- A5-3a start dependence (Wilson lower > .10): L28 176/251 = 0.701 [0.642,0.754] SHOWN; L32 180/288 = 0.625 [0.568,0.679] SHOWN
- A5-3b direction (class B, >= .80 on both sides at L28 and L32): PASS.  L28: below 0.829 [0.800,0.854] n=765, above 0.975 [0.914,0.993] n=81; L32: below 0.911 [0.890,0.928] n=908, above 0.980 [0.930,0.994] n=100; pooled 28+32: below 0.873 [0.856,0.888] n=1673, above 0.978 [0.945,0.991] n=181; L36 (report-only): below 0.965 [0.951,0.976] n=840, above 0.955 [0.875,0.984] n=66

Row counts / errors: exit 11700 rows (0 error); r10 900 rows (0 error); c1i 6000 rows (0 error); lo 600 rows (0 error); x 600 rows (0 error)

## A5-0 determinism

### clause1: R10-X (L28/32, frames 1000-1299) rounds 1-2 vs EXIT_none rounds 1-2

frames compared 600, missing in reference 0, total field mismatches 0 (fields cerr, ierr, ll_in), frames with any mismatch 0, ll_in max abs diff 0.000e+00; dsha (report-only): 0 mismatches in 0 frames

| round | cerr mism | ierr mism | ll_in mism | ll_in max abs diff |
|---|---|---|---|---|
| 1 | 0 | 0 | 0 | 0.000e+00 |
| 2 | 0 | 0 | 0 | 0.000e+00 |

### clause2: R10-LO (L16/20, frames 0-299) rounds 1-4 vs stored c1i FULL_R4

frames compared 600, missing in reference 0, total field mismatches 0 (fields cerr, ierr, dsha, ll_in), frames with any mismatch 0, ll_in max abs diff 0.000e+00

| round | cerr mism | ierr mism | dsha mism | ll_in mism | ll_in max abs diff |
|---|---|---|---|---|---|
| 1 | 0 | 0 | 0 | 0 | 0.000e+00 |
| 2 | 0 | 0 | 0 | 0 | 0.000e+00 |
| 3 | 0 | 0 | 0 | 0 | 0.000e+00 |
| 4 | 0 | 0 | 0 | 0 | 0.000e+00 |

## A5-1 FER by round (frame fails iff ierr_r > 0; Wilson 95%; frames 0-299)

| R | L16 (K 128, n 300) | L20 (K 160, n 300) | L24 (K 192, n 300) | L28 (K 224, n 300) | L32 (K 256, n 300) |
|---|---|---|---|---|---|
| 1 | 0.890 [0.850,0.921] | 0.990 [0.971,0.997] | 1.000 [0.987,1.000] | 1.000 [0.987,1.000] | 1.000 [0.987,1.000] |
| 2 | 0.467 [0.411,0.523] | 0.753 [0.702,0.799] | 0.940 [0.907,0.962] | 1.000 [0.987,1.000] | 1.000 [0.987,1.000] |
| 3 | 0.287 [0.238,0.340] | 0.507 [0.450,0.563] | 0.817 [0.769,0.856] | 0.967 [0.940,0.982] | 0.997 [0.981,0.999] |
| 4 | 0.237 [0.192,0.288] | 0.430 [0.375,0.487] | 0.740 [0.688,0.786] | 0.937 [0.903,0.959] | 0.983 [0.962,0.993] |
| 5 | 0.203 [0.162,0.252] | 0.380 [0.327,0.436] | 0.693 [0.639,0.743] | 0.903 [0.865,0.932] | 0.977 [0.953,0.989] |
| 6 | 0.187 [0.147,0.235] | 0.350 [0.298,0.406] | 0.650 [0.594,0.702] | 0.893 [0.853,0.923] | 0.970 [0.944,0.984] |
| 7 | 0.173 [0.135,0.220] | 0.337 [0.286,0.392] | 0.637 [0.581,0.689] | 0.877 [0.835,0.909] | 0.967 [0.940,0.982] |
| 8 | 0.167 [0.129,0.213] | 0.333 [0.282,0.388] | 0.627 [0.571,0.679] | 0.873 [0.831,0.906] | 0.960 [0.931,0.977] |
| 9 | 0.167 [0.129,0.213] | 0.320 [0.270,0.375] | 0.613 [0.557,0.667] | 0.863 [0.820,0.898] | 0.953 [0.923,0.972] |
| 10 | 0.167 [0.129,0.213] | 0.313 [0.263,0.368] | 0.610 [0.554,0.663] | 0.853 [0.809,0.889] | 0.953 [0.923,0.972] |

c1i FULL_R4 (R1-R4 only): L8 (n 300) R1 0.407 [0.353,0.463] R2 0.150 [0.114,0.195] R3 0.093 [0.065,0.132] R4 0.087 [0.060,0.124]; L12 (n 300) R1 0.640 [0.584,0.692] R2 0.227 [0.183,0.277] R3 0.140 [0.105,0.184] R4 0.120 [0.088,0.162]

### Kc by round (FER(R) = .5 crossing in K = 8 L, linear in K) vs frozen mean-map staircase

| R | Kc obs | frozen pred | ln(pred/obs) | within .15 | boot 95% [n valid/B] | L: FER |
|---|---|---|---|---|---|---|
| 1 | 76.8 | 77.7 | +0.012 | PASS | [70.6,82.0] [1999/2000] | 8:0.407 12:0.640 16:0.890 20:0.990 24:1.000 28:1.000 32:1.000 |
| 2 | 131.7 | 136.4 | +0.035 | PASS | [125.5,136.5] [2000/2000] | 8:0.150 12:0.227 16:0.467 20:0.753 24:0.940 28:1.000 32:1.000 |
| 3 | 159.0 | 158.5 | -0.003 | PASS | [152.7,164.3] [2000/2000] | 8:0.093 12:0.140 16:0.287 20:0.507 24:0.817 28:0.967 32:0.997 |
| 4 | 167.2 | 180.3 | +0.075 | PASS | [161.6,171.3] [2000/2000] | 8:0.087 12:0.120 16:0.237 20:0.430 24:0.740 28:0.937 32:0.983 |
| 5 | 172.3 | 187.3 | +0.084 | PASS | [167.8,176.0] [2000/2000] | 16:0.203 20:0.380 24:0.693 28:0.903 32:0.977 |
| 6 | 176.0 | 196.3 | +0.109 | PASS | [171.9,180.1] [2000/2000] | 16:0.187 20:0.350 24:0.650 28:0.893 32:0.970 |
| 7 | 177.4 | 208.9 | +0.163 | FAIL | [173.5,181.6] [2000/2000] | 16:0.173 20:0.337 24:0.637 28:0.877 32:0.967 |
| 8 | 178.2 | 209.6 | +0.162 | FAIL | [174.2,182.6] [2000/2000] | 16:0.167 20:0.333 24:0.627 28:0.873 32:0.960 |
| 9 | 179.6 | 209.6 | +0.154 | FAIL | [175.6,184.3] [2000/2000] | 16:0.167 20:0.320 24:0.613 28:0.863 32:0.953 |
| 10 | 180.1 | 209.6 | +0.152 | FAIL | [176.2,184.8] [2000/2000] | 16:0.167 20:0.313 24:0.610 28:0.853 32:0.953 |

A5 prediction (from the A4 bracket): FER_R10(L20) in [0.02,0.43]: observed 0.313 [0.263,0.368] -> PASS; Kc_R10 in [172,186]: observed 180.1 [176.2,184.8] -> PASS

## A5-2 per-frame classes on G (EXIT-D rows)

O: D_f > 0 on all G; B: D_f(.56) > 0 and D_f < 0 somewhere; C: D_f(.56) <= 0; X: edge leftover.  u_f = highest - to + crossing on G.

| L | frames | O | B | C | X | >1 sign change on G (all / O / B / C) | u_f class B: median [min,max] (n) | u_f defined in class C (n) |
|---|---|---|---|---|---|---|---|---|
| 28 | 300 | 99 | 141 | 60 | 0 | 54 / 0 / 54 / 0 | 0.542 [0.478,0.560] (141) | 0 |
| 32 | 300 | 42 | 168 | 90 | 0 | 26 / 0 / 26 / 0 | 0.542 [0.482,0.560] (168) | 0 |
| 36 (report-only) | 300 | 4 | 151 | 145 | 0 | 11 / 0 / 11 / 0 | 0.548 [0.475,0.560] (151) | 0 |

### Decode by R10 (ierr10 == 0, R10-X) per class

| L | class | n | decoded by R10 [Wilson] |
|---|---|---|---|
| 28 | O | 99 | 0.495 [0.399,0.592] (49/99) |
| 28 | B | 141 | 0.000 [0.000,0.027] (0/141) |
| 28 | C | 60 | 0.000 [0.000,0.060] (0/60) |
| 28 | X | 0 | n/a (0) |
| 28 | B u C | 201 | 0.000 [0.000,0.019] (0/201) |
| 32 | O | 42 | 0.286 [0.172,0.436] (12/42) |
| 32 | B | 168 | 0.000 [0.000,0.022] (0/168) |
| 32 | C | 90 | 0.000 [0.000,0.041] (0/90) |
| 32 | X | 0 | n/a (0) |
| 32 | B u C | 258 | 0.000 [0.000,0.015] (0/258) |
| 28+32 | O | 141 | 0.433 [0.354,0.515] (61/141) |
| 28+32 | B | 309 | 0.000 [0.000,0.012] (0/309) |
| 28+32 | C | 150 | 0.000 [0.000,0.025] (0/150) |
| 28+32 | B u C | 459 | 0.000 [0.000,0.008] (0/459) |

- class O at L28 (rule >= .8): 0.495 [0.399,0.592] (49/99) -> FAIL
- class O at L32 (rule >= .8): 0.286 [0.172,0.436] (12/42) -> FAIL
- class B u C at L28 (rule <= .2): 0.000 [0.000,0.019] (0/201) -> PASS
- class B u C at L32 (rule <= .2): 0.000 [0.000,0.015] (0/258) -> PASS

non-absorbing R10-X frames (some ierr_r == 0 for r <= 10 but ierr10 > 0): 0

### M2 (frame-own staircase) vs observed FER by round, R10-X frames; M0 = mean-map staircase

#### L28 (n = 300 frames; M0 first-success round None)

| R | observed FER [Wilson] | M2 FER | M2 - obs | M0 FER |
|---|---|---|---|---|
| 1 | 1.000 [0.987,1.000] | 1.000 | +0.000 | 1 |
| 2 | 1.000 [0.987,1.000] | 0.997 | -0.003 | 1 |
| 3 | 0.987 [0.966,0.995] | 0.970 | -0.017 | 1 |
| 4 | 0.943 [0.911,0.964] | 0.913 | -0.030 | 1 |
| 5 | 0.913 [0.876,0.940] | 0.843 | -0.070 | 1 |
| 6 | 0.880 [0.838,0.912] | 0.817 | -0.063 | 1 |
| 7 | 0.873 [0.831,0.906] | 0.797 | -0.077 | 1 |
| 8 | 0.850 [0.805,0.886] | 0.773 | -0.077 | 1 |
| 9 | 0.837 [0.791,0.874] | 0.750 | -0.087 | 1 |
| 10 | 0.837 [0.791,0.874] | 0.743 | -0.093 | 1 |

M2 FER_R10 - observed FER_R10 = -0.093 [-0.127,-0.060] (paired frame bootstrap) -> |diff| <= 0.06: FAIL
per-frame confusion at R10 (rows M2, columns observed): M2 decoded & obs decoded 47, M2 decoded & obs failed 30, M2 failed & obs decoded 2, M2 failed & obs failed 221; agreement 0.893
first-decode round, observed - M2, among frames decoded by both (n 47): mean +1.00, median +1.0, exact agreement 0.234

#### L32 (n = 300 frames; M0 first-success round None)

| R | observed FER [Wilson] | M2 FER | M2 - obs | M0 FER |
|---|---|---|---|---|
| 1 | 1.000 [0.987,1.000] | 1.000 | +0.000 | 1 |
| 2 | 1.000 [0.987,1.000] | 1.000 | +0.000 | 1 |
| 3 | 0.997 [0.981,0.999] | 0.993 | -0.003 | 1 |
| 4 | 0.993 [0.976,0.998] | 0.980 | -0.013 | 1 |
| 5 | 0.983 [0.962,0.993] | 0.973 | -0.010 | 1 |
| 6 | 0.983 [0.962,0.993] | 0.960 | -0.023 | 1 |
| 7 | 0.970 [0.944,0.984] | 0.943 | -0.027 | 1 |
| 8 | 0.967 [0.940,0.982] | 0.937 | -0.030 | 1 |
| 9 | 0.960 [0.931,0.977] | 0.927 | -0.033 | 1 |
| 10 | 0.960 [0.931,0.977] | 0.913 | -0.047 | 1 |

M2 FER_R10 - observed FER_R10 = -0.047 [-0.073,-0.023] (paired frame bootstrap) -> |diff| <= 0.06: PASS
per-frame confusion at R10 (rows M2, columns observed): M2 decoded & obs decoded 11, M2 decoded & obs failed 15, M2 failed & obs decoded 1, M2 failed & obs failed 273; agreement 0.947
first-decode round, observed - M2, among frames decoded by both (n 11): mean +0.55, median +1.0, exact agreement 0.182

L36 (report-only, no R10-X): M0 first-success round None; M2 FER by R: R1:1.000 R2:1.000 R3:1.000 R4:1.000 R5:1.000 R6:0.993 R7:0.993 R8:0.993 R9:0.993 R10:0.990

## A5-3 same-frame start dependence (R10-X frames failing at round 10)

| L | class | failing at R10 | with >= 1 Ir in G decoding in 2 rounds (ierr2 == 0) [Wilson] |
|---|---|---|---|
| 28 | all | 251 | 0.701 [0.642,0.754] (176/251) -> SHOWN (lower bound > 0.1) |
| 28 | O | 50 | 1.000 [0.929,1.000] (50/50) |
| 28 | B | 141 | 0.894 [0.832,0.934] (126/141) |
| 28 | C | 60 | 0.000 [0.000,0.060] (0/60) |
| 28 | X | 0 | n/a (0) |
| 32 | all | 288 | 0.625 [0.568,0.679] (180/288) -> SHOWN (lower bound > 0.1) |
| 32 | O | 30 | 1.000 [0.886,1.000] (30/30) |
| 32 | B | 168 | 0.887 [0.830,0.926] (149/168) |
| 32 | C | 90 | 0.011 [0.002,0.060] (1/90) |
| 32 | X | 0 | n/a (0) |

### Direction check, class B pairs (frame, Ir in G) with |Ir - u_f| >= .02
second step up iff ierr1 == 0 or ierr2 == 0 or mi_in2 > mi_in1; agreement = up == (D_f(Ir) > 0)

| L | class-B frames | side | pairs | agreement [Wilson] | of which D>0 | of which D<0 |
|---|---|---|---|---|---|---|
| L28 | 141 | Ir < u_f | 765 | 0.829 [0.800,0.854] (634/765) | 29/94 | 605/671 |
| L28 | 141 | Ir > u_f | 81 | 0.975 [0.914,0.993] (79/81) | 79/81 | 0/0 |
| L32 | 168 | Ir < u_f | 908 | 0.911 [0.890,0.928] (827/908) | 12/50 | 815/858 |
| L32 | 168 | Ir > u_f | 100 | 0.980 [0.930,0.994] (98/100) | 98/100 | 0/0 |
| pooled 28+32 | 309 | Ir < u_f | 1673 | 0.873 [0.856,0.888] (1461/1673) | 41/144 | 1420/1529 |
| pooled 28+32 | 309 | Ir > u_f | 181 | 0.978 [0.945,0.991] (177/181) | 177/181 | 0/0 |
| L36 (report-only) | 151 | Ir < u_f | 840 | 0.965 [0.951,0.976] (811/840) | 4/15 | 807/825 |
| L36 (report-only) | 151 | Ir > u_f | 66 | 0.955 [0.875,0.984] (63/66) | 63/66 | 0/0 |

direction check verdict (per L28 and L32, both sides >= 0.8, point estimate): PASS

## Report-only

### R10-X (frames 1000-1299) vs A4 FULL_R10 (frames 0-299), FER_R10

- L28: R10-X 0.837 [0.791,0.874] (251/300) vs A4 0.853 [0.809,0.889] (256/300); diff -0.017 [-0.075,+0.042] (Newcombe)
- L32: R10-X 0.960 [0.931,0.977] (288/300) vs A4 0.953 [0.923,0.972] (286/300); diff +0.007 [-0.027,+0.041] (Newcombe)

### Stalled frames in classes B / C (ierr10 > 0): |MI_10 - s_f|, s_f = lowest stable fixed point of the frame own map, MI_10 = 1 - ll_in10

- L28 class B: stalled n 141, with a stable crossing 141; median |MI_10 - s_f| 0.0255 (IQR 0.0171-0.0394); median s_f 0.4106, mean MI_10 0.3895
- L28 class C: stalled n 60, with a stable crossing 60; median |MI_10 - s_f| 0.0262 (IQR 0.0151-0.0364); median s_f 0.3590, mean MI_10 0.3380
- L28 class B u C: stalled n 201, with a stable crossing 201; median |MI_10 - s_f| 0.0258 (IQR 0.0166-0.0380); median s_f 0.3975, mean MI_10 0.3741
- L32 class B: stalled n 168, with a stable crossing 168; median |MI_10 - s_f| 0.0324 (IQR 0.0197-0.0426); median s_f 0.3953, mean MI_10 0.3676
- L32 class C: stalled n 90, with a stable crossing 90; median |MI_10 - s_f| 0.0254 (IQR 0.0181-0.0356); median s_f 0.3500, mean MI_10 0.3189
- L32 class B u C: stalled n 258, with a stable crossing 258; median |MI_10 - s_f| 0.0293 (IQR 0.0185-0.0404); median s_f 0.3798, mean MI_10 0.3506

