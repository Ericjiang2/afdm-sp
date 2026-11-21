# Frozen MIXED8 doublet conflict check

MIXED8, ρ = 0.5, 7 dB, 600 frames (1000–1599).

## Primary verdict

Δ = FER(U) − FER(CD) is 1.0000 [-0.1667, 2.1667] pp using paired frame percentile bootstrap, 95%. The 1 pp margin gives **uncertain**.

U/CD had 14/600 discordant frames (2.3333 [1.2814, 3.8840]%, exact 95% interval).
- U-only failures (10) — 1065, 1073, 1077, 1253, 1363, 1374, 1448, 1517, 1577, 1583
- CD-only failures (4) — 1051, 1131, 1210, 1516

## Per-arm FER

Two-sided exact Clopper–Pearson 95% intervals.

| Arm | Failures | FER, % [95% interval] |
|---|---:|---:|
| F0 | 398/600 | 66.3333 [62.3954, 70.1095] |
| A2 | 183/600 | 30.5000 [26.8364, 34.3568] |
| CD | 33/600 | 5.5000 [3.8158, 7.6376] |
| U | 39/600 | 6.5000 [4.6626, 8.7789] |
| TRUE_GEOMETRY | 0/600 | 0.0000 [0.0000, 0.6129] |

## Secondary readouts

Support estimates use paired frame bootstrap percentile intervals (95%, 20,000 draws).
Energy fractions divide pooled omitted energy by pooled true energy. Rate differences are in pp.

| Outcome | U [95% interval] | CD [95% interval] | U − CD [95% interval] |
|---|---:|---:|---:|
| 0.35-bin two-atom rate, % | 38.0000 [34.1667, 42.0000] | 42.1667 [38.1667, 46.0000] | -4.1667 [-5.8333, -2.6667] |
| 0.75-bin two-atom rate, % | 66.0000 [62.1667, 69.8333] | 66.0000 [62.1667, 69.8333] | 0.0000 [0.0000, 0.0000] |
| Mean omitted doublet energy per frame | 0.0169 [0.0155, 0.0183] | 0.0161 [0.0147, 0.0175] | 0.0007 [0.0005, 0.0010] |
| Omitted doublet energy fraction, % | 4.7353 [4.3637, 5.1119] | 4.5248 [4.1468, 4.9096] | 0.2105 [0.1360, 0.2931] |
| Omitted 0.35-bin doublet energy fraction, % | 4.2141 [3.7376, 4.7231] | 3.7577 [3.3069, 4.2459] | 0.4564 [0.3028, 0.6296] |
| Omitted 0.75-bin doublet energy fraction, % | 5.2151 [4.6407, 5.8133] | 5.2309 [4.6596, 5.8266] | -0.0158 [-0.0531, 0.0226] |
| Frames with singleton phantoms, % | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

Singleton phantoms occurred on 0/600 U frames and 0/600 CD frames.

Exchange decisions differed on 280/600 frames (46.6667 [42.6164, 50.7499]%, exact 95% interval).
Among these frames, the 0.35-bin two-atom representation was as follows.

| Arms with two atoms | Frames | % [exact 95% interval] |
|---|---:|---:|
| both | 179/280 | 63.9286 [58.0012, 69.5577] |
| U only | 0/280 | 0.0000 [0.0000, 1.3088] |
| CD only | 25/280 | 8.9286 [5.8616, 12.8980] |
| neither | 76/280 | 27.1429 [22.0222, 32.7546] |

## Compute

0.2073 CPU core-hours through aggregation, including workers.
