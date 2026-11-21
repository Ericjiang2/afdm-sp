Active task: .trellis/tasks/11-20-gamma0-exchange

# Codex Sol brief: MIXED8 Γ = 0 test (leg 2), Phase 1, then STOP

Written 2026-11-20 by Claude for the resumed gamma0 Sol session. Eric approved leg 2 ("这两个都做"); treat this brief as the design
approval and do not stop to ask. Same hard rules as the P1 Phase 1 brief, with these specifics:
- Draft: `experiments/gamma0_mixed8_20261120/PROTOCOL.md`. New code in `experiments/gamma0_mixed8_20261120/`; reuse
  `experiments/doublet_conflict_20261119/mixed8_receiver.py` and your `experiments/gamma0_exchange_20261120/paired.py` wrappers
  (Z, H, Z-sel) by import or thin wrapper; A2g from the MIXED8 screen code (`experiments/cstate_sparse_doublet_screen_20261118/`).
  No copies of frozen code without the one-line source/change/reason header.
- Blindness: no arm on the fresh block; Z, H, A2g, Z-sel only on synthetic inputs and ≤ 3 smoke frames; report assertions and timings
  only.
- deinlab: tmux `g_gamma0m`, ≤ 24 single-thread processes with ≥ 16 cores free, outputs under
  `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/gamma0_mixed8_20261120/out/`, scratch under `/data/guoyikun/tmp/`.
  Phase 1 cap 1 core-hour.
- Deliverables: arms per DRAFT §1 with per-frame rows (edits, paths, gains, errors, doublet two-atom flags and omitted energy for
  0.35 and 0.75 bin, singleton phantoms); gates G1–G5 per DRAFT §6 (G1 against res-19-04's archived frames for CD and S); fresh-block
  choice and audit; verdict code for §2–§3 with synthetic tests of every branch; cost projection × 1.3. Commit (this task's files and
  the new experiment directory only), append a dated paragraph to the task `implement.md`, stop.
- Final message (English, ≤ 12 lines): commit hash; fresh block and audit; gate table; how each arm was reached; projected cost; DRAFT
  changes with reasons; confirmed `model:`.
