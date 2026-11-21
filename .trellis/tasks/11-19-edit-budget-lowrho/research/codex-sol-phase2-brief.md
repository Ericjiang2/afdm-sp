Active task: .trellis/tasks/11-19-edit-budget-lowrho

# Codex Sol: edit-budget test, Phase 2 (main run, aggregation, RESULTS), then STOP

The protocol is FROZEN ([freeze record](freeze-20261119.md)). Treat this brief as the launch approval. Same hard rules as before (frozen
sources read-only, stage only this task's files, HEREDOC, no push, no amend, no `._*`, deinlab CPU only ≤ 16 single-thread processes,
tmux `g_edit`; the grid-η Sol session may be running or committing).

1. Launch glue only: pin the freeze commit and source hashes; refuse to run if they differ; commit the launch glue before running.
2. One unattended chain on deinlab over the frozen grid and frames 6400–6799. Hard cap 6 core-hours: on reaching it, stop and write
   STOPPED; never top up. Write DONE/STOPPED status. Do not poll more often than every 10 minutes.
3. Aggregate with the frozen `primary.py`: direction, practical size, matched equivalence (with new rescues / harms, discordant-frame
   counts, unresolved flags); secondaries of §3 and §7 (Astra subgroup, agy crossing thresholds and optimal ρ, Claude CD4 ≥ .90, per-arm
   1% crossings with the rho-sweep rule, extra-edit labels true/phantom/other, cap exhaustion, decoder transitions). Verdicts as frozen.
4. Write `experiments/edit_budget_lowrho_20261119/out/main_20261119/RESULTS.md` (observation; frozen verdict; one untested line) plus
   `results.json` with `_argv`/`_config` and an MD5 list of raw rows (raw rows stay on deinlab). Bring back small files only. Do not
   edit STATE, cards or the ledger. Commit and stop.

Final message (English, ≤ 10 lines): commits; g(.15) and g(.30) with intervals; the three labels; key secondaries; core-hours; `model:`.
