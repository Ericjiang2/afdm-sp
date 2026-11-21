# Zheng port gates (before the port run)

Overall: **PASS**. Code md5: {'zport_gates': 'aec4fa7822ebbbdf8bf2466b15470aaf', 'zport_driver': 'b3afaef479de5d14b5bca5588a981e8a', 'zport_rx': '36f96af43c0961f17db12771fa27f80c', 'p1_driver': 'e8594ebfe04f490a86fc16ebd5069cd2', 'gen_fixed': '9a3a987e0a1aaecde33018da5f38c74c'}.

| gate | criterion | result |
|---|---|---|
| ZP-G1 | sum_j h_j Xi_j x = physical CPP propagation to 1e-10 (integer grid, fractional on/off the .25 grid) | **PASS** max errors vs CPP propagation / physical matrix: fractional_off_grid 8.7e-13 / 1.5e-15; fractional_on_grid 7.9e-13 / 1.9e-15; integer_grid 8.0e-13 / 1.1e-13 |
| ZP-G2 | noiseless frames, true path set and gains fed in: MP + LDPC decodes every frame, both delta readings | **PASS** U/adapted_true_paths/delta0.1: 40/40; U/adapted_true_paths/delta0.9: 40/40; U/faithful_integer_channel/delta0.1: 40/40; U/faithful_integer_channel/delta0.9: 40/40; G/adapted_true_paths/delta0.1: 40/40; G/adapted_true_paths/delta0.9: 40/40; G/faithful_integer_channel/delta0.1: 40/40; G/faithful_integer_channel/delta0.9: 40/40 (receiver sigma2 1e-10) |
| ZP-G5 | A3: Z-OMP selection recovers >= 7 of the 8 true delays on average over the 20 noiseless frames of the scenario (decode outcome is informational) | **PASS** scenario mean hits U 7.45, G 7.54; U/rho0.3/delta0.1: hits 7.25; U/rho0.3/delta0.9: hits 7.35; U/rho0.5/delta0.1: hits 7.60; U/rho0.5/delta0.9: hits 7.60; G/rho0.3/delta0.1: hits 7.40; G/rho0.3/delta0.9: hits 7.45; G/rho0.5/delta0.1: hits 7.70; G/rho0.5/delta0.9: hits 7.60 |
| ZP-G3 | channel parameters, noise hash and codeword equal the P1 rows (64 cells) | **PASS** mismatching 0 |
| ZP-G4 | determinism across two processes, all variants | **PASS** 16 rows, mismatching 0, variants ['Za01', 'Za09', 'Zf01', 'Zf09', 'Zo01', 'Zo09', 'Zt'] |

Informational (G5 decode, noiseless frames, Z-OMP without genie): 159/160 frame decodes succeed; failures: U rho 0.3 delta_new 0.9 frame 2 (122 info errors, MP stopped after 4 iterations by the zeta rule, 7/8 delays hit).

Budget decision (I4 rule): the projection with Z-turbo is 26.5 loaded core-hours, over the 22 core-hour budget; **Z-turbo is dropped from the port run** (frame count unchanged), the run uses Zf01, Zf09, Za01, Za09, Zo01, Zo09 (21.9 loaded core-hours, 0.73 h wall at 30 shards).  Z-turbo was still measured in the timing probe and kept in the G4 determinism check.

## Band truncation (+-4 bins) energy fraction of the true channel, P1 frames

| scenario | frames | mean | median | p90 | p99 | max |
|---|---|---|---|---|---|---|
| G | 200 | 0.0274 | 0.0291 | 0.0387 | 0.0438 | 0.0444 |
| U | 200 | 0.0161 | 0.0148 | 0.0275 | 0.0358 | 0.0384 |

## Timing (8 frames per variant, scenario G, rho .3; loadavg [2.97, 1.67, 0.87] -> [2.15, 1.61, 0.88])

| SNR | cell wall | Zf01 | Zf09 | Za01 | Za09 | Zo01 | Zo09 | Zt | Zt round 2 |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 2.050 | 0.092 | 0.062 | 0.363 | 0.249 | 0.664 | 0.253 | 0.615 | 0.367 |
| 7 | 1.921 | 0.088 | 0.058 | 0.333 | 0.273 | 0.577 | 0.261 | 0.605 | 0.332 |

Mean FER / mean true delays hit (of 8) in the probe: 5 dB: Zf01 1.00/4.9, Zf09 1.00/4.6, Za01 1.00/2.5, Za09 1.00/2.5, Zo01 1.00/6.5, Zo09 1.00/6.5, Zt 1.00/2.6; 7 dB: Zf01 1.00/4.9, Zf09 1.00/4.6, Za01 1.00/2.8, Za09 1.00/2.6, Zo01 0.88/6.8, Zo09 1.00/6.6, Zt 1.00/2.6

Projection all_variants_incl_Zt: 17.68 quiet / 26.53 loaded core-hours (x1.5), 0.88 h wall at 30 shards; within the 22 core-hour budget: False

Projection without_Zt: 14.60 quiet / 21.90 loaded core-hours (x1.5), 0.73 h wall at 30 shards; within the 22 core-hour budget: True
