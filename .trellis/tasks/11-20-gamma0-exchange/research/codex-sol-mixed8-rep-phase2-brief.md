Active task: .trellis/tasks/11-20-gamma0-exchange

# Codex Sol brief: MIXED8 replication (leg 3), Phase 2 (main run and verdict), then STOP

Written 2026-11-20 by Claude for the resumed gamma0 Sol session; Eric approved this leg including the run on 2026-11-20 ("加大帧数"); do not stop to ask. The protocol is FROZEN in
`e44f050a` (`experiments/gamma0_mixed8_rep_20261120/PROTOCOL.md`, §7 and Appendix A included). Do not relabel any verdict.
- Run exactly the frozen design on frames 2800–5199: F0, CD, Z, H, S, Z-sel at ρ .5, 7 dB.
- deinlab only: CPU, one thread per process, ≤ 24 processes with ≥ 16 cores free (check load first), tmux `g_gamma0r`, scratch under
  `/data/guoyikun/tmp/`, outputs under `.../experiments/gamma0_mixed8_rep_20261120/out/main_20261120/`. One unattended chain, cost stop at
  3 core-hours or 30 minutes wall, final `STATUS` line. Bind the producing revision and source checksums first; results JSON carries
  `_argv` / `_config`. Raw rows stay remote with `REMOTE_ROWS_MD5.txt`; copy back only small files.
- `verdict.py` on the raw rows: anchors, Q1 and Q2 (Newcombe) on the fresh frames only, all §3 readouts including the descriptive 3,000-frame pool. `RESULTS.md` in three layers (observation,
  frozen verdicts verbatim, untested explanations marked).
- Do not edit `STATE.md`, cards, the skeleton or frozen protocol sections. Commit only this task's files and the experiment directory;
  append a dated paragraph to the task `implement.md`; stop.
- Final message (English, ≤ 12 lines): commit hash; STATUS and core-hours; anchors; Q1 and Q2 with the interval and discordance counts;
  occupancy Z − CD; singleton phantoms by arm; H − CD, Z-sel − Z; Z-only / CD-only two-atom omitted-energy readout; confirmed `model:`.
