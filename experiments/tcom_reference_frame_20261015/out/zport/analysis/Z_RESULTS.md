# P2a part 2: H5 (B against the ported Zheng baselines)

H5 overall: **PASS**; B better than the best variant of each family in all four cells: {'faithful': True, 'adapted': True, 'omp': True}.  Cell labels: {'G_rho300': 'B better than the best Zheng variant', 'G_rho500': 'B better than the best Zheng variant', 'U_rho300': 'B better than the best Zheng variant', 'U_rho500': 'B better than the best Zheng variant'}

## G_rho300 (n = 1000)  label: **B better than the best Zheng variant**

| SNR | Zf01 | Zf09 | Za01 | Za09 | Zo01 | Zo09 | B |
|---|---|---|---|---|---|---|---|
| 4.5 | 0.999 | 0.999 | 1.000 | 1.000 | 0.999 | 0.998 | 0.213 |
| 5 | 0.997 | 0.998 | 1.000 | 1.000 | 0.994 | 0.986 | 0.021 |
| 5.5 | 0.996 | 0.997 | 1.000 | 1.000 | 0.972 | 0.963 | 0.001 |
| 6 | 0.989 | 0.992 | 0.999 | 0.999 | 0.862 | 0.900 | 0.002 |
| 6.5 | 0.981 | 0.987 | 0.998 | 0.999 | 0.679 | 0.812 | 0.001 |
| 7 | 0.955 | 0.982 | 0.996 | 0.997 | 0.502 | 0.692 | 0.001 |
| 7.5 | 0.930 | 0.965 | 0.996 | 0.996 | 0.367 | 0.591 | 0.001 |
| 8 | 0.887 | 0.956 | 0.988 | 0.990 | 0.291 | 0.478 | 0.000 |

(FER)

| arm | crossing @1e-2 (dB) | status |
|---|---|---|
| Zf01 | 8.0 | censored-high (FER > target at every SNR) |
| Zf09 | 8.0 | censored-high (FER > target at every SNR) |
| Za01 | 8.0 | censored-high (FER > target at every SNR) |
| Za09 | 8.0 | censored-high (FER > target at every SNR) |
| Zo01 | 8.0 | censored-high (FER > target at every SNR) |
| Zo09 | 8.0 | censored-high (FER > target at every SNR) |
| B | 5.121847902241799 | ok |

- **H5 baseline Zo01** (crossing 8.0, censored-high (FER > target at every SNR)); B crossing 5.121847902241799 (ok); gain x(Z*) - x(B) = 2.8781520977582007 dB [2.773975818572346, 2.9597365729643457]; B better: True; best Zheng variant better: False
- family faithful: Zf01 (other reading Zf09); gain 2.8781520977582007 dB [2.773975818572346, 2.9597365729643457]; B better: True
- family adapted: Za01 (other reading Za09); gain 2.8781520977582007 dB [2.773975818572346, 2.9597365729643457]; B better: True
- family omp: Zo01 (other reading Zo09); gain 2.8781520977582007 dB [2.773975818572346, 2.9597365729643457]; B better: True
- family FER at 6 / 7 / 8 dB: faithful 0.989/0.955/0.887; adapted 0.999/0.996/0.988; omp 0.862/0.502/0.291; B 0.002/0.001/0.000
- band-truncation energy of the true channel (mean) 0.02809546472155187; mean true delays hit (of 8) at the lowest / highest SNR: Zf01 5.4/5.5, Zf09 5.2/5.2, Za01 2.5/2.5, Za09 2.5/2.5, Zo01 6.6/6.9, Zo09 6.5/6.8

## G_rho500 (n = 1000)  label: **B better than the best Zheng variant**

| SNR | Zf01 | Zf09 | Za01 | Za09 | Zo01 | Zo09 | B |
|---|---|---|---|---|---|---|---|
| 4.5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.984 |
| 5.5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.999 | 0.581 |
| 6 | 1.000 | 1.000 | 1.000 | 1.000 | 0.994 | 0.993 | 0.053 |
| 6.5 | 0.996 | 0.999 | 1.000 | 1.000 | 0.974 | 0.947 | 0.002 |
| 7 | 0.995 | 0.995 | 1.000 | 1.000 | 0.861 | 0.862 | 0.000 |
| 7.5 | 0.991 | 0.994 | 1.000 | 1.000 | 0.632 | 0.762 | 0.000 |
| 8 | 0.977 | 0.990 | 0.998 | 1.000 | 0.395 | 0.660 | 0.000 |

(FER)

| arm | crossing @1e-2 (dB) | status |
|---|---|---|
| Zf01 | 8.0 | censored-high (FER > target at every SNR) |
| Zf09 | 8.0 | censored-high (FER > target at every SNR) |
| Za01 | 8.0 | censored-high (FER > target at every SNR) |
| Za09 | 8.0 | censored-high (FER > target at every SNR) |
| Zo01 | 8.0 | censored-high (FER > target at every SNR) |
| Zo09 | 8.0 | censored-high (FER > target at every SNR) |
| B | 6.254445097247107 | ok |

- **H5 baseline Zo01** (crossing 8.0, censored-high (FER > target at every SNR)); B crossing 6.254445097247107 (ok); gain x(Z*) - x(B) = 1.7455549027528932 dB [1.6394714728255648, 1.8328732205393612]; B better: True; best Zheng variant better: False
- family faithful: Zf01 (other reading Zf09); gain 1.7455549027528932 dB [1.6394714728255648, 1.8328732205393612]; B better: True
- family adapted: Za01 (other reading Za09); gain 1.7455549027528932 dB [1.6394714728255648, 1.8328732205393612]; B better: True
- family omp: Zo01 (other reading Zo09); gain 1.7455549027528932 dB [1.6394714728255648, 1.8328732205393612]; B better: True
- family FER at 6 / 7 / 8 dB: faithful 1.000/0.995/0.977; adapted 1.000/1.000/0.998; omp 0.994/0.861/0.395; B 0.053/0.000/0.000
- band-truncation energy of the true channel (mean) 0.02809546472155187; mean true delays hit (of 8) at the lowest / highest SNR: Zf01 5.6/5.6, Zf09 5.5/5.5, Za01 2.6/2.6, Za09 2.6/2.5, Zo01 7.1/7.3, Zo09 7.1/7.2

## U_rho300 (n = 1000)  label: **B better than the best Zheng variant**

| SNR | Zf01 | Zf09 | Za01 | Za09 | Zo01 | Zo09 | B |
|---|---|---|---|---|---|---|---|
| 4.5 | 0.997 | 0.998 | 0.999 | 1.000 | 0.999 | 0.999 | 0.199 |
| 5 | 0.991 | 0.994 | 0.999 | 0.999 | 0.989 | 0.984 | 0.018 |
| 5.5 | 0.974 | 0.981 | 0.999 | 0.998 | 0.938 | 0.948 | 0.003 |
| 6 | 0.925 | 0.956 | 0.998 | 0.998 | 0.802 | 0.842 | 0.002 |
| 6.5 | 0.844 | 0.915 | 0.995 | 0.996 | 0.566 | 0.740 | 0.000 |
| 7 | 0.735 | 0.874 | 0.991 | 0.993 | 0.424 | 0.641 | 0.000 |
| 7.5 | 0.598 | 0.842 | 0.985 | 0.985 | 0.301 | 0.512 | 0.000 |
| 8 | 0.492 | 0.807 | 0.979 | 0.977 | 0.260 | 0.409 | 0.000 |

(FER)

| arm | crossing @1e-2 (dB) | status |
|---|---|---|
| Zf01 | 8.0 | censored-high (FER > target at every SNR) |
| Zf09 | 8.0 | censored-high (FER > target at every SNR) |
| Za01 | 8.0 | censored-high (FER > target at every SNR) |
| Za09 | 8.0 | censored-high (FER > target at every SNR) |
| Zo01 | 8.0 | censored-high (FER > target at every SNR) |
| Zo09 | 8.0 | censored-high (FER > target at every SNR) |
| B | 5.164024991913495 | ok |

- **H5 baseline Zo01** (crossing 8.0, censored-high (FER > target at every SNR)); B crossing 5.164024991913495 (ok); gain x(Z*) - x(B) = 2.835975008086505 dB [2.6623297625639815, 3.0]; B better: True; best Zheng variant better: False
- family faithful: Zf01 (other reading Zf09); gain 2.835975008086505 dB [2.6623297625639815, 3.0]; B better: True
- family adapted: Za01 (other reading Za09); gain 2.835975008086505 dB [2.6623297625639815, 3.0]; B better: True
- family omp: Zo01 (other reading Zo09); gain 2.835975008086505 dB [2.6623297625639815, 3.0]; B better: True
- family FER at 6 / 7 / 8 dB: faithful 0.925/0.735/0.492; adapted 0.998/0.991/0.979; omp 0.802/0.424/0.260; B 0.002/0.000/0.000
- band-truncation energy of the true channel (mean) 0.0161327378946023; mean true delays hit (of 8) at the lowest / highest SNR: Zf01 6.0/6.2, Zf09 5.9/5.9, Za01 2.6/2.6, Za09 2.6/2.6, Zo01 6.6/6.9, Zo09 6.5/6.8

## U_rho500 (n = 1000)  label: **B better than the best Zheng variant**

| SNR | Zf01 | Zf09 | Za01 | Za09 | Zo01 | Zo09 | B |
|---|---|---|---|---|---|---|---|
| 4.5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.978 |
| 5.5 | 0.999 | 0.999 | 1.000 | 1.000 | 0.999 | 0.998 | 0.555 |
| 6 | 0.995 | 0.995 | 0.999 | 1.000 | 0.990 | 0.983 | 0.060 |
| 6.5 | 0.980 | 0.985 | 0.999 | 0.998 | 0.942 | 0.918 | 0.001 |
| 7 | 0.958 | 0.963 | 0.998 | 0.998 | 0.775 | 0.796 | 0.000 |
| 7.5 | 0.898 | 0.929 | 0.998 | 0.998 | 0.475 | 0.687 | 0.000 |
| 8 | 0.816 | 0.892 | 0.997 | 0.994 | 0.259 | 0.589 | 0.000 |

(FER)

| arm | crossing @1e-2 (dB) | status |
|---|---|---|
| Zf01 | 8.0 | censored-high (FER > target at every SNR) |
| Zf09 | 8.0 | censored-high (FER > target at every SNR) |
| Za01 | 8.0 | censored-high (FER > target at every SNR) |
| Za09 | 8.0 | censored-high (FER > target at every SNR) |
| Zo01 | 8.0 | censored-high (FER > target at every SNR) |
| Zo09 | 8.0 | censored-high (FER > target at every SNR) |
| B | 6.218809072123576 | ok |

- **H5 baseline Zo01** (crossing 8.0, censored-high (FER > target at every SNR)); B crossing 6.218809072123576 (ok); gain x(Z*) - x(B) = 1.7811909278764242 dB [1.6894198255594244, 1.8281664925513272]; B better: True; best Zheng variant better: False
- family faithful: Zf01 (other reading Zf09); gain 1.7811909278764242 dB [1.6894198255594244, 1.8281664925513272]; B better: True
- family adapted: Za09 (other reading Za01); gain 1.7811909278764242 dB [1.6894198255594244, 1.8281664925513272]; B better: True
- family omp: Zo01 (other reading Zo09); gain 1.7811909278764242 dB [1.6894198255594244, 1.8281664925513272]; B better: True
- family FER at 6 / 7 / 8 dB: faithful 0.995/0.958/0.816; adapted 1.000/0.998/0.994; omp 0.990/0.775/0.259; B 0.060/0.000/0.000
- band-truncation energy of the true channel (mean) 0.0161327378946023; mean true delays hit (of 8) at the lowest / highest SNR: Zf01 6.3/6.3, Zf09 6.3/6.3, Za01 2.6/2.6, Za09 2.6/2.6, Zo01 7.1/7.3, Zo09 7.1/7.3

