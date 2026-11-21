# Claude check of the gate screen (2026-11-19)

Sol result: `bb5ad661` (code), `a818bf99` (results). [SCREEN](../../../../experiments/gate_screen_20261119/SCREEN.md)

## Verified
- `gate.py` implements the frozen rule in the brief (`df981cd9`): pair contrast phase-aligned, V0/V1 by linear solves, block rule on Dirichlet modes < 1, λ* = σ² (S1) and λ + u/N (S2).
- S1 entering supports bit-identical on 398/398 triggered frames; S2 hashes matched on 200/200 keys.
- Verdict applied as frozen: 0/398, Clopper–Pearson upper bound 0.92% < .50 → **passes the screen**. Not relabelled.
- Sol's STATE / ledger / task edits are accurate and say receiver performance after the floor is untested.
- Six `._*` AppleDouble files on deinlab removed by Claude (own transfer junk; listed in `screen.json` source inventory, not executed).

## Leverage caveat (S1 could hardly fail)
- Astra's closed form for an isolated pair: the gate floors iff (E − u)·x < λ*, x = 1 − |D_N(δ)|.
- At 7 dB, σ² = 0.1995 = 10^(−0.7), so per-sample signal power is 1. The pilot-plus-soft mean then has E ≈ ρN + Σ|x̄|², and
  E − u ≥ ρN − (1 − ρ)N = 0 at ρ = .5, with equality only if every data symbol is completely unknown.
- Firing spacing from the closed form (computed here): E − u = 1.05 → 0.35 bin; 20 → 0.078; 100 → 0.035; 300 → 0.020 bin.
- So on any triggered frame whose soft symbols are not near-total ignorance, the exchange-stage gate floors only pairs closer than
  a few hundredths of a bin. 0/398 (and 0/398 at 0.75 bin) was close to structurally guaranteed. E − u per frame was not stored, so
  this is an inference from the normalisation, confidence H.
- What the screen does establish: in support exchange the one rule reduces, in practice, to **no floor** — the placement that was
  measured best there (res-20261119-03/04). In SBL it floors 15 of S-lo's 18 modes on full 25-atom blocks and nothing on most small
  blocks (median gate rank 0 vs S-lo 2 over all blocks).

## Consequence for the next test
- Astra's second criterion (lost resolved 0.35-bin pairs vs unfloored exchange < 5%) is essentially implied by the above, because the
  gate does not fire in exchange at these SNRs. The decisive open question is only the SBL leg: gate vs S-lo, excess FER upper bound
  < 1 pp, frame-clustered, fresh paired frames. Which S-lo modes the gate drops (small blocks) is where any loss would come from.
- Not run; needs Eric's approval.
