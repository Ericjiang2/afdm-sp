# Design — doublet conflict check
- Harness: `experiments/cstate_sparse_doublet_screen_20261118/screen.py` (MIXED8 generator, E-2 frozen sources). New code goes in
  `experiments/doublet_conflict_20261119/`.
- U arm: port the exact per-trial Γ_U scoring from `experiments/unified_cov_prospective_20261119/cstate.py` (and `projector.py`),
  using the closed-form CODELAY as base (as in Stage 3), not the screen's constant-variance call path. Record this difference from the
  screen and gate CD against both where applicable.
- Gates:
  - G1: CD (and F0, A2) reproduce archived screen rows on old frames 100–195 at 12 dB where the call path allows. If closed-form CD
    differs from the screen's constant-variance CODELAY, report the difference instead.
  - G2: U with τ = 0 is bit-identical to CD. Γ_U trial scores match a brute-force solve to 1e-10. Doublet census fields are correct on
    synthetic channels.
  - G3: repeatability on smoke frames.
- Outputs per frame: per-arm decoded SHA and errors; atoms and their delays and Dopplers; two-atom flags for the .35 and .75 doublets;
  omitted doublet energy; singleton phantoms; first-edit type.
