# Post hoc check: Gemini report-2 "swap-score rank inversion" condition on E-2 rows

- **Frozen 2026-10-19** by user decision ("按草案冻结 … 跳过外部评审（结果标为探索性）"), before any row was read for this check.
  Trellis task `.trellis/tasks/10-19-rank-inversion-posthoc/`. External review (item 5 of the checklist) skipped by the user;
  the outcome is labelled exploratory.
- Implementation notes fixed at freeze (they make the draft's wording precise; no rule changed):
  - I1. "First accepted edit" = the edit with the smallest `step` in the arm's `edits` list; global swaps happen before local
    refinement, so the geometry before it is exactly r1 (delays and Dopplers).
  - I2. Edit classes: *phantom* (new delay equals the delay of another slot after replacement), *same-slot* (new delay
    equals the replaced slot's old delay), *new-delay* (all others). R1 uses phantoms only. In R2 the outcome is
    phantom vs not phantom (same-slot and new-delay together), as in the draft ("otherwise").
  - I3. R2 additionally requires at least one true delay present in r1 (so h1,max exists); units without one are counted.
  - I4. Cluster = frame index (shared across scenario, ρ and SNR), which is conservative.
  - I5. Code: `ri_analysis.py` (this folder), D_N as in `codelay_guard.abs_dn` with N = 1024.
  - I6 (2026-10-19, after the first launch stopped at the input-integrity check, before any row was read). The md5
    manifest also lists the 56 config files; the check now compares only `rows_shard*.jsonl.gz` entries. No analysis
    code changed.

## Status and scope
- Exploratory, post hoc. The hypothesis came from an external model that had seen summaries of these data (G_n = .815,
  the A2n readouts). Any outcome is "consistent / inconsistent with H-RI on the data that motivated it", never a
  confirmation. A confirmation would need fresh frames.
- No new receiver runs. Inputs: E-2 family R rows (deinlab, `tf_cstate_e2_20261017/out/main_R/rows_shard*.jsonl.gz`,
  md5 list local), read-only. The analysis script runs on deinlab and only a summary comes back.
- Not available from rows: p̄μ = ‖μ‖²/N (needs an F0 replay, excluded by the user). Handled by the bound below.

## Hypotheses (what each predicts)
- **H-RI (Gemini report 2, §3.3).** A scalar-Γ swap prefers co-delay phantom c (on the delay of occupant path 1) over the
  missed weak path w iff Z(p̄) = |h1|²(1−ρ−p̄)²|D|² / ((ρ+p̄)|hw|²) > 1, |D| = |D_N(ν_c − ν_1)|.
  Z(p̄) decreases in p̄, so Z0 := Z(0) ≥ Z(p̄): **Z0 > 1 is necessary** for a phantom accept.
  Predicts: R1 high; R2 S_RI beats S_A; R3 onset shift ≈ +5.1 dB from ρ .3 to ρ .5; R4 required ratio ∝ 1/|D|².
- **H-A (no better option).** Phantoms are accepted when no missed true path is scorable (small |hw|), regardless of
  |h1| or |D|. Predicts: R2 S_RI ≈ S_A; R1 unconstrained.
- **H-B (strong-path misfit).** Phantoms sit on the strongest path because its Doppler/gain misfit leaves the largest
  residual; depends on |h1|² but not on |D|² scaling or the ρ/(1−ρ)² factor. Predicts: R2 S_RI > S_A (like H-RI), but R3/R4
  do not follow the H-RI scaling.
  H-RI and H-B are separated only by R3/R4, which are report-only here.

## Population and definitions
- Units: family R, triggered, arm A2n (diag Γ + ban on co-delay atoms with |D_N| ≥ .5). Secondary: arm A2 (no guard).
- Edit used: the first accepted edit (step 0), so the current geometry is exactly r1 with one slot replaced.
- Phantom: the new atom's delay equals the delay of another slot after replacement. New-delay: otherwise.
- Occupant 1: the other slot at that delay; |D| from its r1 Doppler and the new Doppler; |h1|² = true gain power at that
  delay (truth delays are distinct in R). If the occupant delay is not a true delay, the unit is "occupant spurious",
  counted separately.
- |hw|² = largest true gain power among true delays absent from the geometry before the edit. Units with no missed true
  delay (|hw| = 0) form their own stratum and are excluded from R1/R2 (Z0 = ∞ there by construction); their phantom rate is
  reported.
- Cluster: frame (frames shared across ρ and SNR). 20000 cluster-bootstrap resamples, percentile 95% CI.

## Readouts and decision rule
- **R1 (necessary condition, primary).** Among A2n phantom first-edits with |hw| > 0: share with Z0 > 1.
- **R2 (discrimination, primary).** Unit-level, A2n units with |hw| > 0 and ≥ 1 accepted edit; outcome = first edit is
  phantom. Predictors fixed before data: S_RI = log(|h1,max|²(1−ρ)²·.25 / (ρ|hw|²)) (best case allowed by the guard,
  |D| → .5, strongest occupied true path), S_A = log(1/|hw|²). Statistic ΔAUC = AUC(S_RI) − AUC(S_A).
- **Verdict (frozen before reading any row):**
  - CONSISTENT: R1 CI lower ≥ .85 and ΔAUC CI lower > 0.
  - INCONSISTENT: R1 CI upper < .75 (at least a quarter of phantoms violate a necessary condition even at the most
    permissive p̄ = 0).
  - otherwise PARTIAL.
- **Report-only.** R1 on arm A2 (there |D| ≈ 1, so the condition is |h1|²/|hw|² > ρ/(1−ρ)²: 0.61 at ρ .3, 2.0 at ρ .5).
  R3: per-ρ logistic fit of phantom on log(|h1|²/|hw|²) in A2; onset shift ρ .3 → .5 vs the H-RI value +5.1 dB.
  R4: A2n phantoms in |D| bins [.2,.35) / [.35,.5): 10th percentile of |h1|²/|hw|², ratio vs the H-RI value ≈ 2.4.
  Weak-path grid loss: repeat R1 with |hw|² × max over the .25 grid of |D_N(ν_w − grid)|² (the weak path's on-grid
  candidate is weaker than its true power).

## Premortem
- If R1 fails, the most likely reason is that the formula drops the occupant's own Doppler/gain misfit, which creates
  a co-delay residual without data error. That would favour H-B. p̄ cannot rescue a failure (p̄ = 0 is the most
  permissive value).
- If R1 passes trivially (power ratios in R are almost always large), R1 has no power. Guard: also report the share of
  *new-delay* first-edits with Z0 > 1 (computed with the best guard-allowed co-delay |D| = .5). If that share is also
  ≥ .85, R1 does not discriminate and the verdict leans on R2 only.

## Prediction ledger (Claude, before data)
- R1 CI lower ≥ .85: P = .50 (strong vs missed-path power ratios in an 8-path unit-power law are usually ≥ 10).
- ΔAUC CI lower > 0: P = .55.
- Verdict CONSISTENT: .35; PARTIAL: .40; INCONSISTENT: .25.
- R3 onset shift within ±2 dB of +5.1 dB: P = .25.

## Cost and records
- One read-only pass over the R rows on deinlab, single process, minutes. The script and spec are committed before the
  run. The summary comes back to `experiments/posthoc_rank_inversion_20261019/` (whitelisted small JSON/MD).
- No result card unless the user asks; at most a draft card labelled exploratory.
- External review (checklist item 5): Codex MCP is down. Options: skip it, because the outcome is labelled exploratory
  and not a mechanism claim; or ask Gemini to review this spec in its own thread.
