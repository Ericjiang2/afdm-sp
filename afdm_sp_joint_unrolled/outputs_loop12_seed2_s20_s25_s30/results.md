# Paired classical vs learned C2-rel
N=1024 v=2.0 P=8 tau=10.0ms frames=500

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 dB | 3.279e-03 | 3.275e-03 | 2.018e-03 | -38.48% | 791 | 145 | 1.375e-108 | -21.75 | -22.75 |
| 25 dB | 1.216e-03 | 1.145e-03 | 7.324e-04 | -39.78% | 393 | 74 | 7.308e-54 | -23.61 | -24.48 |
| 30 dB | 5.410e-04 | 5.244e-04 | 3.838e-04 | -29.06% | 223 | 62 | 8.586e-23 | -23.84 | -24.35 |
