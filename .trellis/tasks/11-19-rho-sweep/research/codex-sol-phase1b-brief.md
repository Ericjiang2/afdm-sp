Active task: .trellis/tasks/11-19-rho-sweep

# Codex Sol brief: ρ sweep, Phase 1b (DRAFT §7 revisions), then STOP

Written 2026-11-19 by Claude. Continue in this session; the Phase 1 rules still apply (blindness, read-only frozen sources, deinlab limits,
git rules). Treat this brief as the approval. Phase 1b cap: 1 core-hour. Confirm `model:` is `gpt-6.2-sol`.

Read the task `protocol-DRAFT.md` **§7** and `astra-design-review.md`. §7 governs.

## Deliverables
1. **Verdict code for P1–P3**, with:
   - one physical-frame resample shared across arms, scenarios, SNRs and ρ;
   - censoring encoded as (−∞, L] or [H, ∞), with signed bounds propagated through each contrast;
   - Bonferroni 98.33% intervals;
   - P3 grid-minimum bounds built from opposite endpoints;
   - decisive one-sided bounds retained.

   Add synthetic tests for every branch, including censored and decisive one-sided cases.
2. **Exploratory readouts**, which are not verdicts:
   - V1 and V4 low-versus-high averages, with censor-aware bounds;
   - the direction below .30;
   - optimum sets under simultaneous bounds;
   - each scenario reported separately.
3. **Mechanism readouts**: per SNR and ρ, the trigger rate; paired rescue and harm per trigger for A2 and CD; and the share of first
   edits won by a phantom versus a true path.
4. **Precision** from archived paired Stage 3 curves (ρ .3 / .5): the projected half-widths of P1–P3 at 400 and at 600 frames. Report
   the §7 frame decision and its cost. If 600 frames are chosen, audit 5400–5599 as well.
5. Update the experiment `PROTOCOL.md` (DRAFT) with §7 and your notes. Commit and stop.

## Final message
English, ≤ 12 lines: commit hash; gate and test table; projected half-widths; frame choice and cost; revisions; confirmed `model:`.
