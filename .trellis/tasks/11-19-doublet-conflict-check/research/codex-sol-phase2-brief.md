Active task: .trellis/tasks/11-19-doublet-conflict-check

# Codex Sol brief: doublet conflict check, Phase 2 (frozen main run, verdict), then STOP

Written 2026-11-19 by Claude. The protocol is **frozen**; read `.trellis/tasks/11-19-doublet-conflict-check/research/freeze-20261119.md`.
Continue in this session; Phase 1 rules apply, except that the fresh block may now be simulated. Treat this brief as the approval.
Confirm `model:` is `gpt-6.2-sol`.

## Run and aggregate
- Record the freeze commit (and any later commit that changes only launch glue, with its reason) as the producing commit in `_argv` /
  `_config` and in `PRODUCING_COMMIT.txt`. Commit the launch glue before the first fresh row.
- Main run: MIXED8, ρ .5, 7 dB, frames 1000–1599, arms F0, A2, CD, U and TRUE_GEOMETRY. deinlab CPU only, one thread, ≤ 32 processes,
  tmux `g_doublet`, output under `out/main_20261119/`, cost stop 4 core-hours, STATUS DONE or STOPPED.
- Run the frozen verdict code unchanged.
- `RESULTS.md` contains, with 95% intervals:
  - the primary Δ with its verdict and method (bootstrap or rare-event);
  - per-arm FER;
  - the U/CD discordant frames;
  - the two-atom rates for .35-bin and .75-bin doublets (U vs CD, paired);
  - omitted doublet energy;
  - singleton phantoms;
  - core-hours.

  Label secondary readouts as such. Do not interpret.
- Return the small files (`results.json` with `_argv` / `_config`, `RESULTS.md`, `config.json`, `STATUS`, the remote rows MD5 list) to
  the local `out/main_20261119/`. Raw rows stay on deinlab.
- Commit (HEREDOC, no push, no amend; on `index.lock`, retry 30 s × 10) and append a dated Phase 2 paragraph to the task
  `implement.md`.

## Final message
English, ≤ 10 lines, containing:
- commit hash;
- STATUS;
- frame count;
- core-hours;
- Δ with its interval, method and verdict;
- per-arm FER;
- the .35-bin two-atom rates (U vs CD);
- the confirmed `model:`.
