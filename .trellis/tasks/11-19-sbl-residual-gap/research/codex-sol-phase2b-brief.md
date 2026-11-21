Active task: .trellis/tasks/11-19-sbl-residual-gap

# Codex Sol brief: residual gap, Phase 2 (re-frozen main run with K′), then STOP

Written 2026-11-19 by Claude. §8 is **re-frozen**; read `.trellis/tasks/11-19-sbl-residual-gap/research/freeze-v2-20261119.md`.
Continue in this session; Phase 1 rules apply, except that frames 4800–4999 may now be simulated. Treat this brief as the approval.
Confirm `model:` is `gpt-6.2-sol`.

- Commit the launch glue first. Record the re-freeze commit as the producing commit (with any glue-only commit and its reason) in
  `_argv` / `_config` and in `PRODUCING_COMMIT.txt`. Use a fresh output directory, `out/main_v2_20261119/`. Do not reuse or touch the
  stopped attempt's directories or rows.
- Main run: E-3c SBL pipeline, U/G × ρ .3 × 6–11 dB × frames 4800–4999 (2,400 keys), arms R0, U2, K′, M and KM′ at 100 iterations.
  - deinlab CPU only, one thread, ≤ 32 processes, tmux `g_gap`.
  - Cost stop at 15 core-hours; the PSD gate stays active; STATUS reads DONE or STOPPED.
- Run the frozen verdict code unchanged, with K replaced by K′.
- `RESULTS.md` contains:
  - the premise, Δ_X − tG with 97.5% intervals, the verdicts and the joint label;
  - per-arm FER with 95% intervals;
  - unclipped κ;
  - KM′ − R0, the interaction, K′ − R0 and M − R0;
  - β, iterations, convergence and co-delay pairs;
  - the K′ census;
  - core-hours.

  Label secondary readouts as such. Do not interpret.
- Return the small files and commit (HEREDOC, no push, no amend; on `index.lock`, retry 30 s × 10). Append a dated paragraph to the task
  `implement.md`.

Final message, English, ≤ 12 lines:
- commit hash, STATUS, keys, core-hours;
- G with its CI;
- per-arm FER;
- κ_K′ and κ_M with contrast intervals and verdicts;
- the joint label;
- KM′ − R0;
- the confirmed `model:`.
