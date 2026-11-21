# Design — rho sweep
- Arms F0, A2 and CD reuse the gated CSTATE route from the unified experiment (Stage 3 closed-form CD; A2 = `gamma_mode='diag'` with
  the same schedule).
- Extend the Stage 3 cell grid to ρ ∈ {.15, .2, .25, .3, .4, .5} and the SNR grid in DRAFT §1, without changing any receiver code.
- Crossings and censoring: reuse the Stage 3 `analyze.py` logic (port it; do not edit the frozen file). Write the verdict code for
  DRAFT §2 with synthetic tests, including the censoring and not-evaluable branches.
- Gates:
  - G1: F0 and CD at ρ .3 and .5 reproduce archived Stage 3 rows; A2 reproduces archived split-prospective rows.
  - G2: new ρ values run end to end on smoke frames.
  - G3: repeatability.
