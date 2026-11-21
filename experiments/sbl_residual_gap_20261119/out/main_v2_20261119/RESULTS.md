# SBL residual gap — frozen main run

2,400 keys in 200 physical frames. Paired frame-cluster bootstrap with 20,000 draws and seed 20261121.

## Primary verdict

The gap G = FER(U2) − FER(R0) was 2.3333 [1.5417, 3.1667] pp (95% CI). The premise passed.
Observed G was positive. Its 95% lower bound was positive. The share of draws with nonpositive denominators was 0.000% (within the 1% limit).

| Arm | Δ − .5G (pp, 97.5% CI) | Δ − .25G (pp, 97.5% CI) | κ (unclipped, 95% CI) | Discordant frames | Verdict |
|---|---:|---:|---:|---:|---|
| K′ | 0.3750 [-0.1042, 0.8958] | 0.9583 [0.4167, 1.5312] | 0.6607 [0.4746, 0.9000] | 47 | uncertain |
| M | 0.0417 [-0.5000, 0.5833] | 0.6250 [0.0625, 1.2188] | 0.5179 [0.3148, 0.7500] | 42 | uncertain |

The joint verdict is **uncertain**.
The κ intervals use positive-denominator draws.

## Secondary readouts

| Arm | FER (%, 95% CI) | Failed keys | Information errors | Mean NMSE | Mean β | Mean EM iterations | Converged (%) | Co-delay pairs | Keys with pairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R0 | 2.6250 [1.7917, 3.5833] | 63 | 5016 | 0.0375035 | 5.78141 | 95.704 | 38.042 | 68423 | 2400 |
| U2 | 4.9583 [3.8750, 6.1250] | 119 | 10455 | 0.0563019 | 4.42735 | 99.899 | 2.417 | 57353 | 2400 |
| K′ | 3.4167 [2.5417, 4.3333] | 82 | 6605 | 0.0532629 | 5.76849 | 95.680 | 37.792 | 68960 | 2400 |
| M | 3.7500 [2.7083, 4.8750] | 90 | 7499 | 0.0402982 | 4.42735 | 99.899 | 2.417 | 57353 | 2400 |
| KM′ | 2.5833 [1.7500, 3.5000] | 62 | 4829 | 0.0373166 | 5.76849 | 95.680 | 37.792 | 68960 | 2400 |

| Paired contrast | FER difference (pp, 95% CI) |
|---|---:|
| K′ − R0 | 0.7917 [0.1667, 1.4167] |
| M − R0 | 1.1250 [0.4583, 1.7917] |
| KM′ − R0 | -0.0417 [-0.2500, 0.1250] |
| Cap × refinement interaction, (KM′ − M) − (K′ − U2) | 0.3750 [-0.2500, 1.0000] |

### K′ covariance census

K′ capped 460,289 of 1,531,407 initial-grid eigenvalues.
Trace removed 9.98686e+07, exact trace 1.5218e+08, and uncapped U2 trace 2.55224e+08.
- Trace removed relative to uncapped U2 covariance — 39.1297%.
- Co-delay squared Frobenius share, pooled — 99.9635%.
- Co-delay squared Frobenius share, median across keys — 99.9667%.

Full K′ covariance PSD checks passed on 2,400 keys. Minimum λ_min / u was 0.000116961.

## Provenance

Freeze commit `5030ff0f66a569f81c43e112e1a075c0fd30314e` and producing commit `5030ff0f66a569f81c43e112e1a075c0fd30314e`. Launch glue `25b6f526516bcced7fb076995d91ad5a731d67c2`.
Raw row manifest `REMOTE_ROWS_MD5.txt` (MD5 `cc89c229e1077ca6393fe0ef18f8bebd`).

## CPU accounting

Main chain used **10.809 core-hours**.
