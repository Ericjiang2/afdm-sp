Active task: .trellis/tasks/11-19-grid-eta-dual

# Codex Sol: grid η test, Phase 1b (apply PROTOCOL §7), then STOP

Continuation from Claude (2026-11-19). Your Phase 1 (`4c03fca6`) passed review. PROTOCOL §7 (Astra review + Claude's post-Phase-1
adjustments in §7.11) now governs over §1–§6; read it first. Same hard rules as Phase 1 (no main run, no freeze, fresh blocks blind,
frozen sources read-only, deinlab CPU only ≤ 16 processes, tmux `g_grid`, no `._*`, stage only this task's files, HEREDOC, no push, no
amend; another Sol session for `11-19-edit-budget-lowrho` may be committing). Phase 1b cap 1.5 core-hours.

1. §7.3/§7.11: implement the **second-stage-only** grid: freeze the first-round state (pilot screening, first APP, soft symbols, u) at the
   nominal grid and change only the EM candidate grid by η. Gate: at η = 4 it must equal your Phase 1 parity rows. If this cannot be done
   without changing frozen sources, keep the whole-pipeline sweep and label it per §7.3. Report screened ranks and Π_lo rank / total
   added penalty per η.
2. §7.2/§7.4/§7.5: update the verdict code: X direction requires the interaction lower bound > 0 **and** Q_A2(0.0625) − Q_A2(0.25) lower
   bound > 0; report each scorer's change; S strict monotonicity, all-pairs equivalence (±1.5 pp), endpoint-equivalence label, and the
   significant-decrease rule G_B(2) − G_B(8) lower bound > 0; one frame-ID resample per draw across all arms/offsets/grids/scenarios.
   Extend the synthetic tests.
3. §7.6/§7.11: S schedule = 6 dB only, U/G, ρ .3, frames 6800–7199 (audit 7000–7199 on both hosts). Recost × 1.3 for R0/R1/S-lo;
   apply the fallbacks in §7.11 (drop S-lo, then 200 frames) to fit 15 core-hours. Using old frames, estimate the paired frame-level SD
   of G_B differences between grids to replace Astra's illustrative SD, and report the projected half-width.
4. §7.8: on 10 fixed old keys, run η = 8 with 200 EM iterations vs 100 and report whether R1's outcome changes (convergence artefact check).
5. Append "Appendix B. Phase 1b notes" (do not edit §0–§7). Commit and stop.

Final message (English, ≤ 10 lines): commit; stage-specific or whole-pipeline; gates; audit 7000–7199; projected half-width; chosen
schedule and cost; 200-iteration check; `model:`.
