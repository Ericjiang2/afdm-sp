# Python vs MATLAB DAFT-convention comparison

Config py:  frames-cap=100  T=5  pic-iter=20
Config mat: frames-cap=100  T=5  pic-iter=20

## BER vs SNR (mean ± std)

| SNR | method | Python conv | MATLAB conv |
|---:|:---|:---|:---|
| 20 dB | perfect_csi_mmse | 1.465e-04±5.1e-04 | 1.465e-04±4.1e-04 |
| 20 dB | ls_mmse | 1.662e-01±3.0e-02 | 1.550e-01±3.6e-02 |
| 20 dB | omp_mmse | 1.440e-01±3.1e-02 | 1.553e-01±4.4e-02 |
| 20 dB | omp_mp | 1.097e-01±4.8e-02 | 1.141e-01±3.8e-02 |
| 20 dB | joint_omp_mp | 2.263e-02±2.1e-02 | 3.337e-02±3.7e-02 |
| | | | |
| 25 dB | perfect_csi_mmse | 0.000e+00±0.0e+00 | 0.000e+00±0.0e+00 |
| 25 dB | ls_mmse | 1.867e-01±3.3e-02 | 1.861e-01±4.2e-02 |
| 25 dB | omp_mmse | 1.673e-01±2.8e-02 | 2.003e-01±5.8e-02 |
| 25 dB | omp_mp | 1.135e-01±7.9e-02 | 1.324e-01±8.0e-02 |
| 25 dB | joint_omp_mp | 2.476e-02±3.0e-02 | 3.552e-02±4.0e-02 |
| | | | |

## Channel-estimation NMSE (dB, mean)

| SNR | method | Python conv | MATLAB conv |
|---:|:---|:---|:---|
| 20 dB | ls | -7.23 dB | -7.51 dB |
| 20 dB | omp | -8.00 dB | -7.05 dB |
| 20 dB | joint | -15.13 dB | -13.53 dB |
| | | | |
| 25 dB | ls | -7.42 dB | -7.50 dB |
| 25 dB | omp | -8.17 dB | -6.41 dB |
| 25 dB | joint | -14.71 dB | -12.96 dB |
| | | | |

## Joint OMP-MP iteration convergence (BER at iter T)

| SNR | conv | iter 1 | iter 2 | iter 3 | iter 4 | iter 5 |
|---:|:---|:---|:---|:---|:---|:---|
| 20 dB | py | 1.39e-01 | 9.46e-02 | 5.19e-02 | 3.42e-02 | 2.26e-02 |
| 20 dB | mat | 1.46e-01 | 1.05e-01 | 6.22e-02 | 4.35e-02 | 3.34e-02 |
| | | | | | | |
| 25 dB | py | 1.48e-01 | 1.01e-01 | 5.31e-02 | 3.60e-02 | 2.48e-02 |
| 25 dB | mat | 1.75e-01 | 1.27e-01 | 7.31e-02 | 5.16e-02 | 3.55e-02 |
| | | | | | | |

## Headline: Joint OMP-MP BER at each SNR

| SNR | py-conv joint BER | mat-conv joint BER | ratio (mat / py) |
|---:|:---|:---|:---:|
| 20 dB | 2.2632e-02 | 3.3374e-02 | 1.475 |
| 25 dB | 2.4756e-02 | 3.5522e-02 | 1.435 |

Interpretation: if ratio is within ±0.1 of 1.0 the two conventions are empirically equivalent; if one is consistently lower (ratio far from 1.0) that convention has better OMP dictionary conditioning.