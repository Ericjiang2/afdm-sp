# Paired classical vs learned C2-rel
N=1024 v=2.0 P=8 tau=10.0ms frames=100

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 dB | 1.807e-04 | 1.807e-04 | 1.465e-04 | -18.92% | 10 | 3 | 4.614e-02 | -28.12 | -28.15 |
| 25 dB | 0.000e+00 | 0.000e+00 | 0.000e+00 | +0.00% | 0 | 0 | — | -29.79 | -29.78 |
| 30 dB | 0.000e+00 | 0.000e+00 | 0.000e+00 | +0.00% | 0 | 0 | — | -29.36 | -29.43 |
