Active task: .trellis/tasks/11-19-grid-eta-dual

# Codex Sol: grid η test, Phase 2 (main run, aggregation, RESULTS), then STOP

The protocol is FROZEN ([freeze record](freeze-20261119.md)). Note §7.12: keep **S-lo** in the S leg (200 frames, three arms ≈ 8.4
core-hours); it overrides Appendix B's two-arm schedule. Treat this brief as the launch approval. Same hard rules as before (frozen
sources read-only, stage only this task's files, HEREDOC, no push, no amend, no `._*`, deinlab CPU only ≤ 16 single-thread processes,
tmux `g_grid`; the edit-budget Sol session may be running — together stay ≤ 32 processes).

1. Launch glue only: pin the freeze commit and source hashes; refuse to run if they differ; commit the launch glue before running.
2. One unattended chain: X leg (56000–56999), then S leg (6800–6999, R0/R1/S-lo, η ∈ {2, 4, 8}). Hard caps X 3, S 15 core-hours: on
   reaching a cap, stop that leg and write STOPPED; never top up. DONE/STOPPED status. Do not poll more often than every 10 minutes.
3. Aggregate with the frozen verdict code: X (each scorer's change, interaction, direction and 10 pp labels, exclusions by reason);
   S (G_B per η, adjacent and endpoint contrasts, monotone / equivalence / endpoint-equivalence / reversal labels); joint label;
   secondaries (S-lo − R0 per η and its slope vs R1's, β, convergence, output same-delay pairs, Π_lo rank and added penalty per η).
4. Write `experiments/grid_eta_dual_20261119/out/main_20261119/RESULTS.md` (observation; frozen verdict; one untested line) plus
   `results.json` with `_argv`/`_config` and an MD5 list of raw rows (raw rows stay on deinlab). Small files only. Do not edit STATE,
   cards or the ledger. Commit and stop.

Final message (English, ≤ 10 lines): commits; X Q changes and interaction with intervals and labels; S G_B per η and labels; joint;
core-hours; `model:`.
