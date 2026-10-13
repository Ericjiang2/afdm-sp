# Loop 9 micro-verify — C2-rel proxy gate (N=1024 v=2.0 P=10 tau=10.0ms)

| SNR | n_fr | n_tr | n_val | pos_rate_tr |
|---:|---:|---:|---:|---:|
| 10 | 250 | 150 | 100 | 0.0501 |
| 15 | 250 | 150 | 100 | 0.0521 |
| 20 | 250 | 150 | 100 | 0.0482 |

## recall@K and ratio vs residual-MF

| SNR | K=2: resMF / proxy / ratio / hit_any | K=4: resMF / proxy / ratio / hit_any | K=6: resMF / proxy / ratio / hit_any |
|---:|---:|---:|---:|
| 10 | 0.010 / 0.074 / 7.17x / 0.810 | 0.017 / 0.107 / 6.20x / 0.860 | 0.028 / 0.119 / 4.19x / 0.870 |
| 15 | 0.010 / 0.079 / 8.30x / 0.860 | 0.023 / 0.112 / 4.97x / 0.900 | 0.028 / 0.124 / 4.37x / 0.910 |
| 20 | 0.010 / 0.078 / 8.10x / 0.850 | 0.019 / 0.112 / 6.02x / 0.890 | 0.032 / 0.120 / 3.77x / 0.900 |

## Gate decision (Oracle R1 thresholds)

- SNR=15: **PASS** (rec@6=0.1242198413262453, hit@6=0.91, rel_ok=True)
- SNR=20: **PASS** (rec@6=0.12034503497541925, hit@6=0.9, rel_ok=True)
- **OVERALL: PASS**