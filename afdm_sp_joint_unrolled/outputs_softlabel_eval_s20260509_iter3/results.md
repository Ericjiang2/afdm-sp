# Paired classical vs learned C2-rel
N=1024 v=2.0 P=8 tau=10.0ms frames=200

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 dB | 2.486e-02 | 2.486e-02 | 3.122e-02 | +25.58% | 1012 | 3617 | 1.000e+00 | -15.74 | -15.46 |
| 20 dB | 2.346e-03 | 2.322e-03 | 6.606e-03 | +181.58% | 103 | 1848 | 1.000e+00 | -17.09 | -16.40 |
| 25 dB | 5.225e-04 | 5.420e-04 | 3.796e-03 | +626.64% | 27 | 1368 | 1.000e+00 | -17.47 | -16.49 |
