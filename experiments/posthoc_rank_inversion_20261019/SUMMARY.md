# Rank-inversion check on E-2 rows — summary (exploratory, post hoc)

- Protocol: `PROTOCOL.md`, frozen in 494583ff; I6 (manifest filter, before data) in ed2f48e8. Script md5 3fb99348…
- Run: deinlab 2026-10-19, read-only over the 56 E-2 family R row files (md5-checked against the manifest); 32000 rows,
  8052 triggered units. Output `out/ri_summary.json` (with `_argv`, `_config`), log `out/out_run.log`. Raw rows stay on deinlab.

## 1. Observation
| readout | A2n (primary) | A2 (report-only) |
|---|---|---|
| first-edit classes (phantom / same-slot / new-delay) | 2845 / 1313 / 2930 | 7460 / 235 / 148 |
| R1: phantoms with Z0 > 1 | **.959 [.946, .971]** (n 2807) | .999 [.998, 1.000] (n 6220) |
| R1 by ρ (.3 / .5) | .857 / .973 | .997 / .9996 |
| R1 with weak-path grid loss | .960 [.948, .972] | .999 |
| power check: non-phantom first edits with Z0 > 1 (best case \|D\| = .5) | **.999** (n 3329) | 1.000 (n 152) |
| R2: AUC S_RI / AUC S_A (phantom vs not) | .721 [.703, .738] / .787 [.771, .803] | — |
| R2: ΔAUC = AUC(S_RI) − AUC(S_A) | **−.067 [−.078, −.055]** (n 6136) | — |
| R4: p10 ratio of \|h1\|²/\|hw\|², \|D\| bin [.2,.35) over [.35,.5) | .75 [.29, 1.39] (n 519 / 2232); H-RI value 2.39 | — |
| R3: logistic onset shift ρ .3 → .5 | — | −76 dB, CI [−959, 743]: degenerate (95% of A2 first edits are phantoms) |
| units with no missed true delay: phantom first edits | 38 / 1680 | 1240 / 1680 |

Guard invariant: 0 A2n phantoms with |D_N| ≥ .5. No phantom sits on a spurious occupant; every unit has a true delay in r1.

## 2. Frozen verdict
**PARTIAL.** R1's CI lower bound is ≥ .85, but ΔAUC's CI lower bound is not > 0. The result is not INCONSISTENT, since R1's
upper bound is above .75. Labelled exploratory, as frozen.

The pre-declared power check applies. Non-phantom first edits satisfy the same necessary condition 99.9% of the time, so
R1 does not discriminate, and the verdict rests on R2. R2 is reversed: adding the strongest occupied path power to
1/|hw|² makes prediction of phantom acceptance *worse*. Both H-RI and H-B predicted the opposite direction.

## 3. Candidate explanation (untested, confidence M)
H-A: under the near-duplicate guard, a scalar-Γ phantom is accepted mainly when no missed true path is scorable (small
|hw|²); the strong path's power and |D_N| add no predictive value. R4's |D|² scaling is also absent (CI excludes 2.39).
Cheapest falsifying test, on existing rows: use `top5_step1` to compare the best phantom score with the best new-delay
score per unit. H-A predicts that the margin depends on |hw|² and not on |h1|²·|D|². Not run.

## Correction note (2026-10-19, same day; sections 1–3 above are kept unchanged)
- **Independent recount** (`independent_recount.py`, separate code with scipy `mannwhitneyu` that does not import
  `ri_analysis.py`; output `out/independent_recount.json`) reproduces every frozen point estimate exactly: the classes,
  R1 = .95939 (n 2807), AUC_RI = .72078, AUC_A = .78749, and A2 R1 = .99887.
- **Section 3 is wrong.** Post hoc robustness readouts, not in the protocol:
  - The predictor without the ρ term, log(|h1,max|²/|hw|²), gives AUC .812, above S_A's .787.
  - Within each ρ the ratio also beats S_A: .821 vs .783 at ρ .3, .740 vs .708 at ρ .5.
  - |h1,max|² alone gives AUC .636.
  The strong path's power therefore *does* predict phantom acceptance. R2 reversed because of the ρ factor in S_RI:
  H-RI's threshold ρ/(1−ρ)² makes phantoms easier at ρ .3, but the observed first-edit phantom rate is .175 at ρ .3 and
  .578 at ρ .5.
- **Design error (Claude).** S_RI bundled the power ratio with the ρ scaling, so R2 tested both jointly and could not
  separate them. The frozen verdict PARTIAL stands.
- **Corrected reading** (untested, confidence L–M):
  - The power-ratio dependence predicted by both H-RI and H-B is present.
  - The parts specific to H-RI are not: the ρ scaling has the opposite sign, and R4 shows no |D|² scaling.
  - The single remaining candidate is H-B (strong-path misfit residual). Cheapest test: in the `top5_step1` scores, the
    phantom candidate's score should grow with |h1|² and not with |D|²; ρ should act through F0's residual quality, not
    through (1−ρ)²/ρ.
  - The per-ρ phantom rates are not adjusted for SNR or trigger mix, which differ by ρ.

## Prediction ledger (Claude, frozen) — scored
- R1 CI lower ≥ .85, P = .50 → occurred, but trivially (power check .999).
- ΔAUC CI lower > 0, P = .55 → did not occur (reversed).
- Verdict CONSISTENT .35 / PARTIAL .40 / INCONSISTENT .25 → PARTIAL.
- R3 shift within ±2 dB of +5.1 dB, P = .25 → not estimable (degenerate).
