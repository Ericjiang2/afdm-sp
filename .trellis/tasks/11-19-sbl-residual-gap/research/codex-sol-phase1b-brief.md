Active task: .trellis/tasks/11-19-sbl-residual-gap

# Codex Sol brief: SBL residual gap, Phase 1b (pre-freeze revisions §7), then STOP

Written 2026-11-19 by Claude. Continue in this session; the Phase 1 rules still apply (blindness on 4600–4999, read-only frozen sources,
deinlab limits, git rules). Treat this brief as the approval. Phase 1b cap: 1.5 core-hours. Confirm `model:` is `gpt-6.2-sol`.

Read `protocol-DRAFT.md` §7 and `astra-design-review.md`. §7 governs where it conflicts with §1–§5.

## Deliverables
1. **Arm KM**: cached K EM output plus R0's scalar refinement, final gain fit and decode.
2. **G2 additions**:
   - K's initial EM covariance spectrum: u·min(λ, 1) on the high subspace and u(1+λ) on the low subspace;
   - the full initial K covariance, cross-delay terms included, must have λ_min ≥ −1e−10·u, checked on smoke and synthetic inputs. The
     main runner must stop and report on any violation;
   - KM's EM output equals K's bit for bit.
3. **Verdict code** updated to §7.3–§7.4:
   - paired contrasts Δ_X − tG with 97.5% intervals;
   - the premise rules;
   - fewer than 5 discordant clusters → uncertain;
   - the narrowed joint labels;
   - unclipped κ;
   - synthetic tests for every branch.
4. **Leverage** from old keys only: the uncertainty of Δ_X − tG implied by the archived U2/R0 paired discordances on 4400–4599, labelled
   conditional.
5. **Fresh-block check** for 4800–4999. Project the cost for 4,800 keys (arms R0, U2, K, M, KM) and for 2,400 keys. Apply §7.7 and report
   the choice.
6. Update the experiment `PROTOCOL.md` (DRAFT) with §7 and your implementation notes. Commit and stop.

## Final message
English, ≤ 12 lines, containing:
- commit hash;
- the gate table, including the PSD gate;
- the leverage;
- the frame choice and its cost;
- the revisions;
- the confirmed `model:`.
