# attribution/ — per-candidate mechanism attribution

**TCOM novelty axis B2** (sharpens FYP partial-verdict claim C4 from "consistent with" to "explanatory evidence for").
**Owning branch**: `trans/listwise-mechanism`.
**Status**: skeleton — not yet implemented.

## Purpose

For every atom the learned head adds to the support during a paired evaluation run, classify it geometrically against the simulator's true (l, k) physical paths. The four classes:

| Class | Definition |
|---|---|
| `dirichlet_sidelobe` | Within ±1 Doppler bin of a true physical (l, k) tap, but not exactly on it |
| `virtual_tap` | Within ±k_leak of a true tap (k_leak = 2 in the canonical setup) |
| `main_lobe_collision` | Exactly on a true tap (already chosen by OMP-once — duplicate hit) |
| `false_positive` | More than k_leak bins from any true tap |

If ≥ 60% of added atoms fall in `dirichlet_sidelobe`, the §IV-E mechanism story moves from "consistent with side-lobe repair" to "explanatory evidence supports side-lobe repair as the dominant mechanism."

## Planned files

| File | Purpose |
|---|---|
| `attribute_added_atoms.py` | Per-frame atom logger that compares head-added atoms against simulator-known physical paths; emits `attribution.json` with class counts per (frame, SNR). |
| `summarize_attribution.py` | Aggregates `attribution.json` into the §IV-E table (4 classes × 3 SNRs). |

## Reuse

- True path indices: simulator's `H_true` / `(l_p, round(k_p^real))` from `../afdm_env.py` — same source `classical_joint_headroom_probe.py::_oracle_physical_indices` already uses.
- Receiver invocation: `../paired_learned_eval.py` with a logging hook (no new training).
- Support extraction: `../loop13_support_recall_probe.py` — copy the support-comparison logic, extend to per-atom attribution.

## Operating point

Single 250-frame paired run × {15, 20, 25} dB on the listwise-best checkpoint (selected from §IV-B 5-seed sweep). Single seed (20260419) — this is a mechanism diagnostic, not a BER measurement, so no retraining variance is needed here.

## Output

`outputs_attribution/attribution.json` + `outputs_attribution/attribution_summary.md` (the §IV-E table).
