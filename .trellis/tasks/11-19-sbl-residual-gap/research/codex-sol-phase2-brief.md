Active task: .trellis/tasks/11-19-sbl-residual-gap

# Codex Sol brief: SBL residual gap, Phase 2 (frozen main run, verdict), then STOP

Written 2026-11-19 by Claude. The protocol is **frozen**; read `.trellis/tasks/11-19-sbl-residual-gap/research/freeze-20261119.md`.
Continue in this session; Phase 1 rules apply, except that frames 4600–4799 may now be simulated. Treat this brief as the approval.
Confirm `model:` is `gpt-6.2-sol`.

## Run and aggregate
- Commit the launch glue before the first fresh row. Record the freeze commit (and any glue-only commit, with its reason) as the
  producing commit in `_argv` / `_config` and in `PRODUCING_COMMIT.txt`.
- Main run: E-3c SBL pipeline, U/G × ρ .3 × 6–11 dB × frames 4600–4799 (2,400 keys), arms R0, U2, K, M and KM at 100 iterations.
  - deinlab CPU only, one thread, ≤ 32 processes, tmux `g_gap`, output under `out/main_20261119/`.
  - Cost stop at 15 core-hours.
  - The PSD gate stops the run on a violation.
  - STATUS reads DONE or STOPPED.
- Run the frozen verdict code unchanged.
- `RESULTS.md` contains:
  - the premise, Δ_X − tG with 97.5% intervals, the per-arm verdicts and the joint label;
  - per-arm FER with 95% intervals;
  - unclipped κ_K and κ_M;
  - KM − R0, the interaction estimate, K − R0 and M − R0;
  - β, iterations, convergence and output co-delay pairs;
  - the K census;
  - core-hours.

  Label secondary readouts as such. Do not interpret.
- Return the small files to the local `out/main_20261119/` and commit. Use a HEREDOC message; no push, no amend; on `index.lock`, retry
  30 s × 10. Append a dated Phase 2 paragraph to the task `implement.md`.

## Final message
English, ≤ 12 lines, containing:
- commit hash;
- STATUS;
- key count;
- core-hours;
- the premise G with its CI;
- per-arm FER;
- κ_K and κ_M with the contrast intervals and verdicts;
- the joint label;
- KM − R0;
- the confirmed `model:`.
