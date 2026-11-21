# Zheng et al. 2025 reproduction in its own regime (P2a part 1)

Overall: **FAIL**.  N = 512, QPSK, P = 3 (delays 0..2, alpha in {-1,0,1}), delta .1, gamma .1, epsilon .2, i_m 20, uncoded, 2000 frames per point.  Code md5: {'zheng_rx': '9c6ae7f56571c58c4d1e4f4e8b4e26a0', 'zheng_repro': 'dd63bde6f753ad3ac3d83c09e607196b'}.  Entropy `83103fa458e2c4c413173efb758fd85d8a03e204b3d2b625e13b0b5e72893825`, domain 0x5A48454E.

| gate | criterion | result |
|---|---|---|
| G-Z1 | perfect-CSI BER at 8/14/20 dB <= paper Prop. SP (SNR_p 50, M 8) read values 4.3e-2 / 3.4e-3 / 3.8e-4 and decreasing in SNR_d | **FAIL** 8 dB: ours 5.07e-02 vs paper 4.3e-02; 14 dB: ours 7.10e-03 vs paper 3.4e-03; 20 dB: ours 1.04e-03 vs paper 3.8e-04; strictly decreasing: True |
| G-Z2 | Prop. SP MSE < SP-without-IC MSE at every SNR_d; Prop. SP MSE at 17, 20, 23 dB increasing | **PASS** Prop < no-IC at every SNR_d: [True, True, True, True, True, True]; 17/20/23 dB increasing: True |
| G-Z3 | Prop. SP (SNR_p 50, M 8) within a factor 2 of the read values at >= 4 of 6 points; SNR_p 40: BER(23) > BER(20); M = 1 BER > M = 8 BER at 17, 20, 23 dB | **FAIL** (a) 2/6 within factor 2; (b) p40 BER(23) 8.69e-03 vs BER(20) 4.87e-03; (c) M=1 > M=8 at 17/20/23: [True, True, True] |

## Prop. SP, SNR_p 50 dB, M = 8: BER and MSE next to the paper

| SNR_d | ours BER | paper BER | ratio | perfect CSI BER | no-IC BER | MSE prop | MSE no-IC | paper MSE (Fig. 2) |
|---|---|---|---|---|---|---|---|---|
| 8 | 5.224e-02 | 4.30e-02 | 1.21 | 5.073e-02 | 5.271e-02 | 1.662e-04 | 6.590e-04 | 8.40e-03 |
| 11 | 2.202e-02 | 1.40e-02 | 1.57 | 2.062e-02 | 2.247e-02 | 2.511e-04 | 1.223e-03 | 7.80e-03 |
| 14 | 8.368e-03 | 3.40e-03 | 2.46 | 7.103e-03 | 8.661e-03 | 4.283e-04 | 2.349e-03 | 8.00e-03 |
| 17 | 3.570e-03 | 9.30e-04 | 3.84 | 2.434e-03 | 3.759e-03 | 8.625e-04 | 4.595e-03 | 9.00e-03 |
| 20 | 2.104e-03 | 3.80e-04 | 5.54 | 1.039e-03 | 2.178e-03 | 1.681e-03 | 9.077e-03 | 1.07e-02 |
| 23 | 1.757e-03 | 3.50e-04 | 5.02 | 6.079e-04 | 1.780e-03 | 3.481e-03 | 1.802e-02 | 1.40e-02 |

## Prop. SP, SNR_p 40 dB, M = 8

| SNR_d | ours BER | paper BER | ratio |
|---|---|---|---|
| 8 | 5.266e-02 | 4.30e-02 | 1.22 |
| 11 | 2.264e-02 | 1.40e-02 | 1.62 |
| 14 | 9.172e-03 | 3.90e-03 | 2.35 |
| 17 | 4.802e-03 | 1.25e-03 | 3.84 |
| 20 | 4.869e-03 | 1.00e-03 | 4.87 |
| 23 | 8.688e-03 | 3.90e-03 | 2.23 |

## Prop. SP, SNR_p 50 dB, M = 1

| SNR_d | ours BER | paper BER | ratio |
|---|---|---|---|
| 11 | 2.318e-02 | 1.50e-02 | 1.55 |
| 14 | 9.681e-03 | 5.50e-03 | 1.76 |
| 17 | 5.026e-03 | 3.00e-03 | 1.68 |
| 20 | 3.654e-03 | 2.45e-03 | 1.49 |
| 23 | 3.325e-03 | 2.50e-03 | 1.33 |

## Prop. SP, SNR_p 50 dB, M = 4 (informational)

| SNR_d | ours BER | paper BER | ratio |
|---|---|---|---|
| 11 | 2.282e-02 | 1.45e-02 | 1.57 |
| 14 | 9.329e-03 | 4.30e-03 | 2.17 |
| 17 | 4.475e-03 | 1.70e-03 | 2.63 |
| 20 | 3.149e-03 | 1.18e-03 | 2.67 |
| 23 | 2.843e-03 | 1.20e-03 | 2.37 |

## Iterations and final zeta (Prop. SP, SNR_p 50, M 8; informational)

| SNR_d | mean iterations | paper (Fig. 3a, approx.) | final zeta* | path set correct |
|---|---|---|---|---|
| 8 | 19.98 | 19.0 | 0.7498 | 1.000 |
| 11 | 19.51 |  | 0.8833 | 0.999 |
| 14 | 18.42 |  | 0.9519 | 1.000 |
| 17 | 17.10 |  | 0.9799 | 0.997 |
| 20 | 16.14 |  | 0.9897 | 0.997 |
| 23 | 15.55 | 8.0 | 0.9926 | 0.989 |

## c2 sensitivity (Prop. SP, SNR_p 50, M 8, SNR_d 17 dB)

c2 = 1/(2 pi N^2): BER 3.570e-03 (7311 errors, MSE 8.625e-04); c2 = 0: BER 3.583e-03 (7339 errors, MSE 8.247e-04); difference 0.23 standard errors.


## DIAGNOSTIC ONLY (not a gate, not a substitute for the gates): the alternative reading of eq. (29), delta = 0.9 (delta weighting the old message, i.e. p = 0.1 p_old + 0.9 p_tilde)

| SNR_d | Prop BER | paper | ratio | perfect-CSI BER | no-IC BER | Prop mean iterations |
|---|---|---|---|---|---|---|
| 8 | 4.432e-02 | 4.30e-02 | 1.03 | 4.331e-02 | 4.586e-02 | 19.07 |
| 11 | 1.482e-02 | 1.40e-02 | 1.06 | 1.436e-02 | 1.654e-02 | 14.31 |
| 14 | 3.976e-03 | 3.40e-03 | 1.17 | 3.747e-03 | 5.436e-03 | 8.28 |
| 17 | 1.222e-03 | 9.30e-04 | 1.31 | 9.956e-04 | 2.321e-03 | 4.96 |
| 20 | 6.533e-04 | 3.80e-04 | 1.72 | 4.189e-04 | 1.635e-03 | 4.06 |
| 23 | 5.522e-04 | 3.50e-04 | 1.58 | 2.686e-04 | 1.555e-03 | 3.79 |

Seconds per MP run (N = 512): prop 0.0441, perfect 0.0261, no-IC 0.0201 (SNR_d 8 dB); 0.936 s per frame over all 34 runs.

