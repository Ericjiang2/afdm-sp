# Production channel generator: defects, measured impact, proposed fixes (2026-10-08)

Scope: frozen production generator `afdm_sp_joint_unrolled/afdm_env.py` (+ `run_classical_baselines_python.py`,
`loop9_cache_features.py`), used by G0 and G1 (supplement_g1 reuses its l_i, k_real, g_i). Documentation only — no code
changed; existing paper results remain tied to the current law. Fixes must be opt-in flags with bit-identical default.

## D1 Stale delay-support cap (severity: high)
- `run_classical_baselines_python.py:76-78` sets `max_delay_idx_bar_supported = floor(l_max_cap·delay_res / Ts) + 1` while
  Ts = 125 us (fs = 8 kHz). `loop9_cache_features.py:64-67` later sets fs = 16 kHz, Ts = 62.5 us and never recomputes it.
  Cap = 54 samples (3.375 ms) instead of 107.
- `afdm_env.py:346-354`: up to 32 redraws, then fallback `np.minimum(delay_idx_bar, 54)`.
- Measured (E-rho population, 2000 frames): 20.8% frames have >= 2 paths stacked at the capped delay (l ~ 51);
  accepted frames are biased toward delay span <= 3.4 ms (MC: first-try acceptance 4.4% vs 55.5% with the correct cap).
- Impact: artificial same-delay doublets; distorted delay-spread law vs the stated tau_spread = 10 ms.
- Fix: compute the cap after the final fs/Ts are set (single helper called at the end of config construction), and
  replace clip-fallback by unbounded redraw or an explicit truncated law; log redraw counts.

## D2 Delay-grid inconsistency (severity: medium)
- delta_f = 15 Hz hard-coded (`afdm_env.py:36`) -> delay_res = 1/(N·delta_f) = 65.1 us, while samples use Ts = 62.5 us
  (fs/N = 15.625 Hz). l_i = round(delay/65.1 us) on sample-quantized delays -> occasional distinct sample delays collapse
  to one bin (ratio .96): a second source of artificial same-delay stacking.
- Fix: delta_f := fs/N everywhere (or quantize delays directly in samples); assert consistency at construction.

## D3 Doppler law is near-degenerate across paths (severity: medium for generality)
- v_i = |N(2, .5^2)| m/s for every path -> all Dopplers positive, ~1.0 +- .26 bins, k_real clipped to +-2. Any two paths at
  the same delay are almost surely within one bin (unresolvable doublet). Not representative of geometric scattering
  (nu = nu_max cos theta, signs mixed).
- Fix: optional geometric law nu_i = nu_max cos(theta_i) (as in the clustered generator, driver.py `--channel-model
  clustered`), keeping the UWA law as a named scenario.

## D4 Narrowband approximation of Doppler scaling (severity: known limitation)
- Only constant per-path shift a_i fc/fs + integer delay rescaling; no in-frame time compression (a·N ~ 1.36 samples per
  frame). Already disclosed in paper (Section 3/6, first-order MSML). Wideband AFDM I/O is prior art (arXiv 2507.03537).

## D5 Power normalization (severity: low, document)
- G0 Frobenius normalization per frame (||H||_F = sqrt(N)) removes total-energy fading; G1 reuses the gains. Diversity /
  outage statements require expected-power normalization (option exists in driver_f3.py `--power-norm expected`).

## Validation plan for the fix (when implemented)
1. Flags off: bit-identical frames vs current generator (hash check on l, k_real, g over >= 1000 frames).
2. Flags on: report delay-span histogram, same-delay collision rate, Doppler histogram; expect collisions from D1/D2 -> ~0.
3. Rerun production B on fixed vs current law (paired seeds) at the paper's SNR grid; report FER shift; if material,
   disclose in the paper and re-run headline claims.
