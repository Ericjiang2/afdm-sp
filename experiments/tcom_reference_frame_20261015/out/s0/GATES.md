# S0 gates (generator fix D1-D3)

Overall: **PASS**.  Test entropy `6f264a9a7ac4efe09a742cd9e632450d198774183a087833e07a2b8816db5fe2` (S0 only).  Code md5: gen_fixed `9a3a987e0a1aaecde33018da5f38c74c`, s0_gates `0dc749a88ed75c4352175ba4c4bc44f7`.  `_argv` / `_config` are in gates.json.

| gate | criterion | result |
|---|---|---|
| G-S0a | flags off, frames 0..999: l_i, k_real, g_i (+ every other field) bit-identical to frozen driver.generate_base | **PASS** 1000/1000 (l,k,g), all fields 1000/1000; rho .3 extra 50/50 |
| G-S0b(i) | D1+D2 same-delay stacking rate within 3 SE of the natural (uncapped) rate | **PASS** 0.000% vs 0.000% (z = 0.00, n = 100000/100000) |
| G-S0b(ii) | delay-span two-sample KS p > .01 vs direct rejection sampler | **PASS** p = 0.051 (D = 0.0061); max-delay p = 0.107 |
| G-S0b(iii) | truncation (redraw) rate reported | first-try acceptance 51.422%, 0.945 redraws/frame, max attempts 17 |
| G-S0c | observation = CPP propagation to 1e-10, prefix >= max delay, 20 frames x 5 configs | **PASS** max err 7.23e-13 |
| G-S0d (A1) | fix_energy on, U and G: per-frame ||H||_F^2/N = 1 to 1e-9 (CPP operator), 200 frames each | **PASS** max |dev| U 5.77e-15, G 7.33e-15 |
| smoke | frozen F0+CSTATE (run_a0) runs on 8 frames x 5 configs at 7 dB, rho .5 | **PASS** |

## G-S0a detail

- Frames rho .5: 1000 (shards 11); failed fields: none.
- Frozen draw: 231 frames hit the 32-attempt clip fallback; mean seconds per frame frozen/fixed 0.41/0.18 (fixed copy skips H_time).

## G-S0b detail

Same-delay stacking (frames with >= 2 paths in one delay bin), MC:

| draw | n | rate | SE |
|---|---|---|---|
| off | 40000 | 23.447% | 0.212% |
| d2 | 40000 | 19.675% | 0.199% |
| d1 | 100000 | 2.537% | 0.050% |
| d12 | 100000 | 0.000% | 0.000% |
| natural_d1grid | 100000 | 2.076% | 0.045% |
| natural_d2grid | 100000 | 0.000% | 0.000% |

Off = frozen law (stale cap 54, 32 redraws, clip). d1 = explicit truncation at 102 on the frozen 65.1 us grid; d2 = new grid, stale cap; d12 = both. natural_* = single draw, no cap, no clip. D1-only vs its natural rate: diff 0.461%, z = 6.87 (informational: truncation biases the span and, on the 0.96 grid, the stacking rate). Under D2 the sample delays are strictly increasing in every drawn frame (checked: {'d12': True, 'natural_d2grid': True}), so the natural stacking rate is structurally 0 and equality is the pass condition.

Cap formula (computed from the final fs/Ts) vs explicit bin truncation agree for all indices: {'d1': True, 'd12': True}; cap values {'d1_d2_grid': 103, 'd1_grid_frozen': 107, 'frozen': 54}.

Truncation: D1+D2 first-try acceptance 51.422% vs direct sampler 51.362% (z = 0.38); D1 on the old grid 55.769%; frozen law first-try acceptance 4.715%, clip fallback in 21.245% of frames.

## G-S0c detail

- d12: PASS, max rel. error 7.23e-13, prefix values [102]
- d12e: PASS, max rel. error 7.23e-13, prefix values [102]
- d12egeo: PASS, max rel. error 6.97e-13, prefix values [102]
- d12geo: PASS, max rel. error 6.97e-13, prefix values [102]
- off: PASS, max rel. error 7.15e-13, prefix values [102]

## G-S0d detail (amendment A1: fix_energy)

- d12e: PASS, 200 frames, energy in [1.000000000000, 1.000000000000] (max |dev| 5.77e-15, path power dev 6.66e-16); same frames without fix_energy: mean 1.0191, min 1.0025, max 1.2932
- d12egeo: PASS, 200 frames, energy in [1.000000000000, 1.000000000000] (max |dev| 7.33e-15, path power dev 6.66e-16); same frames without fix_energy: mean 1.1179, min 1.0066, max 1.4215

## Geometric law

- nu_max = 1.62 (pooled estimate 1.61963, MC SE 0.00087 over 20 blocks, 1600000 path draws; analytic folded-normal value 1.61955); frozen in gen_fixed.UWA_NU_MAX_99.
- Fresh UWA quantile in the D1+D2 MC: 1.6217 (SE 0.0010), consistent: True.

| law (D1+D2 draws) | frac k>0 | |k| q50 | q90 | q99 | max | P(|dk|<=1) all pairs |
|---|---|---|---|---|---|---|
| uwa_d12 | 1.000 | 1.024 | 1.353 | 1.622 | 2.000 | 0.9943 |
| geometric_d12 | 0.500 | 1.145 | 1.600 | 1.620 | 1.620 | 0.4473 |

Same-delay pairs exist only without D2 (D1-only draws); fraction within one Doppler bin:

| law | same-delay pairs | P(|dk|<=1) |
|---|---|---|
| uwa_d1only | 2552 | 0.9922 |
| geometric_d1only | 2552 | 0.4549 |

## Smoke (not a performance result)

- d12: 8/8 frames ok, errors 0, A0 0.287 s/frame, F0 0.285 s/frame, generation 0.23 s/frame; info errors A0 [0, 0, 0, 0, 0, 0, 0, 0], F0 [0, 0, 0, 0, 0, 0, 0, 0]
- d12e: 8/8 frames ok, errors 0, A0 0.288 s/frame, F0 0.286 s/frame, generation 0.20 s/frame; info errors A0 [0, 0, 0, 0, 0, 0, 0, 0], F0 [0, 0, 0, 0, 0, 0, 0, 0]
- d12egeo: 8/8 frames ok, errors 0, A0 0.284 s/frame, F0 0.282 s/frame, generation 0.20 s/frame; info errors A0 [0, 0, 0, 0, 0, 0, 0, 0], F0 [0, 0, 0, 0, 0, 0, 0, 0]
- d12geo: 8/8 frames ok, errors 0, A0 0.282 s/frame, F0 0.280 s/frame, generation 0.20 s/frame; info errors A0 [0, 0, 0, 0, 0, 0, 0, 0], F0 [0, 0, 0, 0, 0, 0, 0, 0]
- off: 8/8 frames ok, errors 0, A0 0.287 s/frame, F0 0.284 s/frame, generation 0.24 s/frame; info errors A0 [0, 0, 0, 0, 0, 0, 0, 0], F0 [0, 0, 0, 0, 0, 0, 0, 0]
