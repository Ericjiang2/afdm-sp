# Paired classical vs learned C2-rel
N=1024 v=2.0 P=8 tau=10.0ms frames=300

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 dB | 2.529e-03 | 2.536e-03 | 1.683e-03 | -33.46% | 338 | 78 | 5.882e-40 | -22.20 | -22.99 |
| 25 dB | 1.296e-03 | 1.143e-03 | 6.374e-04 | -50.83% | 356 | 51 | 1.061e-57 | -22.86 | -24.02 |
| 30 dB | 4.085e-04 | 4.069e-04 | 3.158e-04 | -22.71% | 102 | 45 | 1.469e-06 | -24.61 | -24.97 |
