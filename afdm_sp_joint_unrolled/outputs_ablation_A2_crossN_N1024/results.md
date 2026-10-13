# Paired classical vs learned C2-rel
N=1024 v=2.0 P=8 tau=10.0ms frames=200

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 dB | 1.785e-02 | 1.785e-02 | 1.712e-02 | -4.10% | 1273 | 973 | 1.224e-10 | -20.40 | -20.26 |
| 20 dB | 5.786e-04 | 5.542e-04 | 6.738e-04 | +16.46% | 64 | 103 | 9.991e-01 | -26.99 | -26.21 |
| 25 dB | 3.906e-05 | 5.127e-05 | 6.592e-05 | +68.75% | 5 | 16 | 9.964e-01 | -29.21 | -28.56 |
