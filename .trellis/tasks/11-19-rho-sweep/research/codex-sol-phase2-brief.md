Active task: .trellis/tasks/11-19-rho-sweep

# Codex Sol brief: ρ sweep, Phase 2 (frozen main run, verdicts), then STOP

Written 2026-11-19 by Claude. The protocol is **frozen**; read `.trellis/tasks/11-19-rho-sweep/research/freeze-20261119.md`. Continue
in this session; Phase 1 rules apply, except that frames 5400–5799 may now be simulated. Treat this brief as the approval. Confirm
`model:` is `gpt-6.2-sol`.

- Commit the launch glue before the first fresh row. Record the freeze commit (and any glue-only commit, with its reason) as the
  producing commit in `_argv` / `_config` and in `PRODUCING_COMMIT.txt`.
- Main run: the full frozen grid on frames 5400–5799 (62,400 keys), arms F0, A2 and CD.
  - deinlab CPU only, one thread, ≤ 32 processes counting only your own workers, tmux `g_rho`, output under `out/main_20261119/`.
  - Cost stop at 10 core-hours. STATUS reads DONE or STOPPED.
  - Wait for completion, checking at intervals of 10 minutes or more.
- Run the frozen verdict code unchanged.
- `RESULTS.md` contains:
  - P1–P3 with point estimates, Bonferroni intervals and verdicts;
  - the per-scenario contrasts;
  - all crossings per (ρ, scenario, arm), with censoring;
  - the exploratory readouts, including the direction below .30 and the optimum sets;
  - the mechanism readouts (trigger rate, rescue and harm per trigger, phantom-versus-true first edits);
  - the U/.30 CD crossing;
  - core-hours.

  Label exploratory readouts as such. Do not interpret.
- Return the small files to the local `out/main_20261119/`, then commit (HEREDOC, no push, no amend; on `index.lock`, retry 30 s × 10).
  Append a dated paragraph to the task `implement.md`.

Final message, English, ≤ 12 lines:
- commit hash, STATUS, keys, core-hours;
- P1, P2 and P3, each with point, interval and verdict;
- the CD and F0 crossings at .30 and .50 for each scenario;
- the U/.30 CD crossing;
- the confirmed `model:`.
