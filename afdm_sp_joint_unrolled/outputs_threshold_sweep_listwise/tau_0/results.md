# Paired classical vs learned C2-rel
N=1024 v=2.0 P=8 tau=10.0ms frames=100

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 dB | 1.807e-04 | 1.807e-04 | 3.125e-04 | +72.97% | 8 | 35 | 1.000e+00 | -28.12 | -27.19 |
| 25 dB | 0.000e+00 | 0.000e+00 | 0.000e+00 | +0.00% | 0 | 0 | — | -29.79 | -29.17 |
| 30 dB | 0.000e+00 | 0.000e+00 | 1.465e-05 | +1464843750.00% | 0 | 3 | 1.000e+00 | -29.37 | -28.63 |
