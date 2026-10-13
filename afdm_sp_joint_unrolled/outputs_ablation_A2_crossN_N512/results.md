# Paired classical vs learned C2-rel
N=512 v=2.0 P=8 tau=10.0ms frames=200

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 dB | 3.552e-02 | 3.552e-02 | 3.567e-02 | +0.44% | 1208 | 1240 | 7.411e-01 | -15.99 | -16.08 |
| 20 dB | 7.314e-03 | 7.334e-03 | 1.053e-02 | +43.93% | 273 | 931 | 1.000e+00 | -20.36 | -18.87 |
| 25 dB | 2.842e-03 | 3.247e-03 | 6.064e-03 | +113.40% | 134 | 794 | 1.000e+00 | -22.26 | -19.94 |
