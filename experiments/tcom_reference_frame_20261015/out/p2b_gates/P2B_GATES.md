# P2b gates (before any test-frame run)

Overall: **PASS**. Code md5: {'p2b_gates': 'e7e887a896c0535753e53108eceeb8ae', 'p2b_driver': '62eda9e2759eff3162c3136b0e958249', 'ep_rx': '914b059cc16d6cb812df6e64d7fb88a5', 'gen_fixed': '9a3a987e0a1aaecde33018da5f38c74c', 'p1_driver': 'e8594ebfe04f490a86fc16ebd5069cd2'}. Dev entropy `ca68a12bfdb5c0a5e797efb26e6c71c4c4f30cc46113c33e8b8c962da6a789b8` (domain 0x54434450); test entropy `e0f4a8f31b265a62e0a9f1ab4076a4a189f046acecec5d4c920b0a5cf64bee80` (domain 0x54435032) is untouched.

| gate | criterion | result |
|---|---|---|
| P2b-G0 | P1 scenarios U, G bit-identical to the P1-era gen_fixed (200 frames); scenario S law: max delay <= 25, distinct delays, acceptance vs direct sampler | **PASS** identical: True; S redraw rate 58.2% (1.395 redraws/frame, first-try acceptance 41.75% vs direct 41.55%, z = 1.61, KS p = 0.846), max delay 25 |
| P2b-G1 | EP-genie, noiseless (sigma2 1e-10): all decoded, detector output = transmitted symbols | **PASS** 20/20 decoded, max |x_hat - x| 5.6e-07 |
| P2b-G2 | estimator, noiseless pilot-only, 50 frames: delays exact, Doppler within 0.05 | **PASS** delays exact 50/50, max Doppler error 0.0007, closed-form response vs operator 2.3e-14 |
| P2b-G3 | SP + EP arms reproduce themselves (two processes, 16 frames) and equal the rows stored before the shared LMMSE core | **PASS** 16 rows, mismatching 0, regression mismatches 0/16, arms ['A3_r300', 'A3_r500', 'B_r300', 'B_r500', 'EP', 'EPG', 'F0_r300', 'F0_r500'] |
| P2b-G4 | LDPC n = 1530 round trip, 100 messages | **PASS** decode 100/100, mapping 100/100, k = 767 (rate 0.5013) |
| P2b-G5 | SP-genie-LMMSE (report-only arm) on noiseless SP frames, 20 frames x rho {.3, .5} | **PASS** 40/40 decoded (informational: first-round max |x_hat - x| 0.29, first-round hard bit errors 0, 38/40 cells have operator singular values below the noise prior, min 2.1e-17) |
| P2b-G6 | determinism including the SPG arm (two processes, 16 frames, all arms) | **PASS** 16 rows, mismatching 0, arms ['A3_r300', 'A3_r500', 'B_r300', 'B_r500', 'EP', 'EPG', 'F0_r300', 'F0_r500', 'SPG_r300', 'SPG_r500'] |
| timing | 16 frames per arm, 5.0 and 7.0 dB, loadavg [2.42, 1.65, 1.34] -> [1.8, 1.6, 1.34] (SPG probe [1.74, 1.59, 1.34] -> [1.53, 1.55, 1.33]) | **PASS** 8.3 quiet / 12.4 loaded core-hours (x1.5; SPG adds 2.00 quiet), 0.41 h wall at 30 shards |

## Estimator with data present (informational, rho_EP = 0.1)

| SNR | path recall | energy recall | false paths / frame | median / p90 Doppler error |
|---|---|---|---|---|
| 4.5 dB | 0.762 | 0.959 | 0.000 | 0.0418 / 0.1230 |
| 8 dB | 0.890 | 0.990 | 0.000 | 0.0307 / 0.0899 |

## Timing (mean seconds per arm and per (frame, SNR) wall)

| SNR | n | wall | A3_r300 | A3_r500 | B_r300 | B_r500 | EP | EPG | F0_r300 | F0_r500 |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 16 | 1.520 | 0.150 | 0.164 | 0.339 | 0.418 | 0.341 | 0.096 | 0.259 | 0.257 |
| 7 | 16 | 1.255 | 0.147 | 0.148 | 0.250 | 0.245 | 0.358 | 0.096 | 0.249 | 0.243 |

Projection before the SPG arm: 16000 cells; shared per-frame cost 0.325 s (SP bases, true operator, genie Gram); per-SNR cost interpolated between the probe SNRs: 6.27 quiet core-hours.

SPG arm only (mean seconds per cell and rho; the per-frame Gram H^H H is counted in the shared cost): 5 dB: SPG_r300 0.221, SPG_r500 0.229; 7 dB: SPG_r300 0.212, SPG_r500 0.214; Gram 0.111 s per frame. Updated projection: 8.27 quiet = 6.27 + 2.00 (SPG).

