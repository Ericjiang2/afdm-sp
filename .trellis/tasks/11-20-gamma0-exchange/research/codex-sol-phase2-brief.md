Active task: .trellis/tasks/11-20-gamma0-exchange

# Codex Sol brief: Γ = 0 exchange test, Phase 2 (main run and verdict), then STOP

Written 2026-11-20 by Claude for the resumed Phase 1 session. Eric approved the main run on 2026-11-20 ("启动主跑"); treat this brief
as the run approval and do not stop to ask. The protocol is FROZEN
in `1266052e` (`experiments/gamma0_exchange_20261120/PROTOCOL.md`, §7 and Appendix A included). Do not relabel any verdict.

## Hard rules
- Run exactly the frozen design: arms CD, Z, H, S, Z-sel and shared F0 on frames 9400–9799, the Stage 3 grid (13,600 keys).
- deinlab only: CPU, one thread per process, ≤ 24 processes with ≥ 16 cores left free (check load first), tmux `g_gamma0`,
  scratch only under `/data/guoyikun/tmp/`, outputs under
  `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/gamma0_exchange_20261120/out/main_20261120/`.
- One unattended chain with a cost stop at 6 core-hours or 30 minutes wall, and a final `STATUS` line (DONE or STOPPED with reason).
  Do not poll in a loop; wait on the chain's completion.
- Bind the producing Git revision and source checksums before the remote run. Results JSON carries `_argv` and `_config`.
- Raw rows stay on deinlab (record path and md5 in `REMOTE_ROWS_MD5.txt`). Copy back only small files: `results.json`, `RESULTS.md`,
  `run.log`, launcher, receipt, `STATUS`.
- Do not edit `STATE.md`, any card, the skeleton or the frozen protocol sections. Git: stage only this task's files and the
  experiment directory; HEREDOC message, no push, no amend.

## Deliverables
1. Main run; `verdict.py` on the raw rows: P-A (Z and H, first-edit endpoint, anchors) and P-B (Z − CD; H − CD reported), the §3 and
   §7.3 secondary readouts, Z-sel, the mechanism readout, crossings.
2. `RESULTS.md` in three layers: observation (numbers), frozen verdicts (verbatim labels), and untested explanations marked as such.
3. Commit, append a dated paragraph to the task `implement.md`, stop.

## Final message
English, ≤ 14 lines: commit hash; STATUS and core-hours; anchors; P-A for Z and H with intervals; P-B for Z (and H) with intervals;
first-to-final transitions and directional discordance counts; Z-sel versus Z; remote raw-row path and md5 file; confirmed `model:`.
