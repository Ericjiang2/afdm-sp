# Paired classical vs learned C2-rel
N=2048 v=2.0 P=8 tau=10.0ms frames=200

| SNR | classical BER | torch-ref BER | learned BER | rel Δ vs cls | McNemar n10 | McNemar n01 | McNemar p (learned better) | NMSE cls (dB) | NMSE learn (dB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 dB | 1.694e-02 | 1.694e-02 | 1.495e-02 | -11.73% | 2538 | 910 | 1.747e-169 | -21.00 | -21.20 |
| 20 dB | 0.000e+00 | 0.000e+00 | 0.000e+00 | +0.00% | 0 | 0 | — | -30.51 | -30.28 |
| 25 dB | 0.000e+00 | 0.000e+00 | 0.000e+00 | +0.00% | 0 | 0 | — | -32.04 | -31.72 |
