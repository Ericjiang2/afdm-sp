# Paired classical vs learned C2-rel
N=1024 v=2.0 P=8 tau=10.0ms frames=100

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 dB | 3.809e-04 | 4.199e-04 | 3.613e-04 | -5.13% | 27 | 23 | 3.359e-01 | -27.91 | -27.77 |
| 25 dB | 9.766e-06 | 2.441e-05 | 5.371e-05 | +450.00% | 0 | 9 | 1.000e+00 | -29.49 | -29.18 |
| 30 dB | 0.000e+00 | 0.000e+00 | 0.000e+00 | +0.00% | 0 | 0 | — | -29.64 | -28.89 |
