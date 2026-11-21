# P1 gates (before any run)

Overall: **PASS**. Code md5: {'p1_gates': '28f81f0dc70ebfbcc826a2424469f25e', 'p1_driver': 'e8594ebfe04f490a86fc16ebd5069cd2', 'gen_fixed': 'cb9be5ea91c0a9b1863758ed598de1c6'}. P1 entropy `2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23`, domain 0x54435246.

| gate | criterion | result |
|---|---|---|
| P1-G1 wiring | flags off + e_rho streams: F0, B, A3 reproduce stored e_rho rows, 64 frames x SNR 5.5, 6.5 (rho .5) | **PASS** 128/128 cells identical (49 F0-triggered cells exercise CSTATE); floats not bit-identical 0, max |diff| 0.0e+00 |
| P1-G2 arm C | C (and D) reproduce Stage-A decisions on 32 prospective frames (6.5 dB) | **PASS** 32/32 frames identical (12 of 12 C-triggered frames included) |
| P1-G3 LOCAL | F0 / B / LOCAL reproduce the five-policy decisions on the 40 original F0-triggered frames | **PASS** 40/40 frames identical (final errors: B 6, LOCAL 29) |
| P1-G4 timing | 16 frames per arm, 5.0 and 7.0 dB, U and G, rho .3, single process; loadavg [2.43, 1.92, 1.47] -> [1.71, 1.79, 1.46] | **PASS** all arms ok; projection 27.6 loaded core-hours (18.4 quiet x 1.5), 0.92 h wall at 30 shards |

## G4 detail (mean seconds per cell; arm columns are per-arm compute incl. shared prefix)

| scenario/SNR | n | cell total | gen | F0 | B | LOCAL | C | D | A3 | F0 trig | C trig |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G_500 | 16 | 1.112 | 0.105 | 0.256 | 0.311 | 0.300 | 0.559 | 0.598 | 0.152 | 0.31 | 0.25 |
| G_700 | 16 | 0.976 | 0.104 | 0.249 | 0.261 | 0.260 | 0.548 | 0.548 | 0.149 | 0.06 | 0.00 |
| U_500 | 16 | 1.062 | 0.102 | 0.257 | 0.289 | 0.284 | 0.557 | 0.586 | 0.152 | 0.19 | 0.19 |
| U_700 | 16 | 0.963 | 0.104 | 0.250 | 0.252 | 0.252 | 0.554 | 0.554 | 0.149 | 0.00 | 0.00 |

Projection: 64000 cells, mean 1.034 quiet seconds per cell (all arms + amortised generation); per-SNR cost interpolated between the two probe SNRs, rho .5 charged at the rho .3 cost. Protocol estimate was ~25 core-hours.

