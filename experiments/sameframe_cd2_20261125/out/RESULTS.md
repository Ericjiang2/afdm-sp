# Same-Frame CD2 Headroom & Quiet Timing Results (`sameframe_cd2_20261125`)

- Freeze commit: `e3bf93f6436f9cc0dcad5d22d2dc7c62f1a570d6`
- Part A CPU: **3.1375 core-hours** (cap 6.0 h; wall 566.5 s)

## Primary Verdict P1' (Pre-Registered, Frames 41000–41399)

| Contrast | Point (dB) | 95% Paired CI (dB) | Verdict |
|---|---:|---|---|
| `min CD2 (100..250) − min s100 (100..200)` | **0.5765** | **[0.3168, 0.8372]** | **INCONCLUSIVE** |

## Part A: Same-Frame 1% FER Crossings (Frames 41000–41399, U/G Mean, dB)

| Arm | ρ=0.05 | ρ=0.10 | ρ=0.15 | ρ=0.20 | ρ=0.25 | ρ=0.30 | Best ρ |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | [12.0000, +inf] | [12.0000, +inf] | 8.5693 | 6.0808 | 4.9547 | 5.1322 | 0.25 |
| delay | [12.0000, +inf] | 6.3631 | 4.4469 | 4.4000 | 4.5236 | 4.7266 | 0.20 |
| HG | — | 8.0231 | 4.8329 | 4.5724 | 4.6221 | — | 0.20 |
| HGint | — | 7.9684 | 5.1845 | 4.7237 | 4.6277 | — | 0.25 |
| CD2 | — | 7.9712 | 4.7053 | 4.4156 | 4.5273 | — | 0.20 |
| CD2e8 | — | 7.7847 | 4.4828 | 4.4527 | 4.5277 | — | 0.20 |
| s100 | — | 3.8391 | 4.0617 | 4.2489 | — | — | 0.10 |
| s050 | — | 3.4559 | 3.4861 | 4.0884 | — | — | 0.10 |
| ldop | [12.0000, +inf] | 3.4518 | 3.4848 | 4.0721 | — | — | 0.10 |
| full | [12.0000, +inf] | 3.4477 | 3.6205 | 4.0374 | — | — | 0.10 |
| s025 | — | 3.4526 | 3.6211 | 4.0566 | — | — | 0.10 |
| s200 | — | [10.0693, +inf] | [10.5000, +inf] | 10.5651 | — | — | 0.20 |

### Part A Secondary Contrasts (95% Paired Frame Bootstrap, seed 20261125, dB)

| Contrast | Point (dB) | 95% CI (dB) |
|---|---:|---|
| CD2_minus_s050 | 0.9597 | [0.8168, 1.0344] |
| CD2_minus_ldop | 0.9638 | [0.8198, 1.0388] |
| CD2_minus_full | 0.9679 | [0.8250, 1.0438] |
| CD2_minus_delay | 0.0156 | [-0.1352, 0.1686] |
| CD2_minus_base | -0.5391 | [-0.7406, -0.3732] |
| CD2_minus_HG | -0.1569 | [-0.2976, -0.0137] |
| CD2_minus_HGint | -0.2121 | [-0.3588, -0.0622] |
| CD2e8_minus_s100 | 0.6136 | [0.3057, 0.8572] |
| CD2e8_minus_s050 | 0.9968 | [0.7798, 1.0530] |
| CD2e8_minus_ldop | 1.0009 | [0.7850, 1.0570] |
| CD2e8_minus_full | 1.0050 | [0.7892, 1.0610] |
| CD2e8_minus_HG | -0.1197 | [-0.2973, 0.0001] |
| CD2e8_minus_HGint | -0.1750 | [-0.3606, -0.0637] |
| CD2e8_minus_CD2 | 0.0371 | [-0.1350, 0.1097] |
| HG_minus_s100 | 0.7333 | [0.4484, 1.0249] |

### Part A Pass-2 Diagnostics

- `CD2`: pass-1 stop 7125/13735, pass-2 ran 6610 (rescued 2722), mean edits p1=1.95 p2=1.59
- `CD2e8`: pass-1 stop 7747/13735, pass-2 ran 5988 (rescued 2244), mean edits p1=3.86 p2=2.13

## Part B: Quiet Single-Core Timing Panels (Huang Frames 5400–5799)

- Pinned CPU: `0` (pre-start util `0.0%`, wall `386.4 s`, timing CPU `0.1077 core-hours`)

### Panel `rho200_snr450` (ρ=0.20, SNR=4.5 dB; 100 triggered + 50 untriggered F0; shared F0 median 272.19 ms)

| Arm | Mean (ms) | Median (ms) | p95 (ms) | Pass-2 Rate | Ratio of Means vs CD | Median Paired Ratio vs CD | Amortized Full-Frame (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| CD | 162.76 | 162.29 | 169.89 | 0.0% | 1.000× | 1.000× | 355.98 |
| CD2 | 189.02 | 162.02 | 328.01 | 17.0% | 1.161× | 1.001× | 369.66 |
| CD2e8 | 199.86 | 177.68 | 345.98 | 11.0% | 1.228× | 1.094× | 375.59 |
| HG | 639.99 | 525.20 | 1061.95 | 20.0% | 3.932× | 3.273× | 609.85 |
| HG1 | 531.27 | 525.20 | 534.78 | 0.0% | 3.264× | 3.240× | 552.07 |
| HGint | 199.05 | 169.98 | 346.82 | 17.0% | 1.223× | 1.056× | 375.37 |

### Panel `rho300_snr500` (ρ=0.30, SNR=5.0 dB; 100 triggered + 50 untriggered F0; shared F0 median 270.67 ms)

| Arm | Mean (ms) | Median (ms) | p95 (ms) | Pass-2 Rate | Ratio of Means vs CD | Median Paired Ratio vs CD | Amortized Full-Frame (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| CD | 160.91 | 160.49 | 168.83 | 0.0% | 1.000× | 1.000× | 305.43 |
| CD2 | 172.80 | 159.99 | 321.64 | 8.0% | 1.074× | 0.997× | 308.55 |
| CD2e8 | 183.74 | 169.50 | 340.11 | 8.0% | 1.142× | 1.055× | 311.27 |
| HG | 572.38 | 524.39 | 1055.18 | 9.0% | 3.557× | 3.284× | 408.02 |
| HG1 | 525.00 | 524.28 | 532.23 | 0.0% | 3.263× | 3.269× | 395.56 |
| HGint | 189.49 | 169.05 | 346.20 | 12.0% | 1.178× | 1.059× | 312.88 |
