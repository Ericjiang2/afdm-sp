Active task: .trellis/tasks/11-20-gamma0-exchange

# Codex Sol brief: MIXED8 FER replication (leg 3), Phase 1, then STOP

Written 2026-11-20 by Claude for the resumed gamma0 Sol session. Eric approved this leg ("加大帧数"); do not stop to ask.
- Draft: `experiments/gamma0_mixed8_rep_20261120/PROTOCOL.md`. Reuse the leg-2 code in `experiments/gamma0_mixed8_20261120/` by import;
  new files only in `experiments/gamma0_mixed8_rep_20261120/`. Arms F0, CD, Z, H, S, Z-sel (no A2g, no TRUE_GEOMETRY).
- G3: choose and audit the next free contiguous 2,400-frame MIXED8 block (disjoint from 100–195, 1000–1599, 2200–2799 and every
  manifest). G1/G2/G4: confirm by source hash that the receiver and wrappers are byte-identical to leg 2's bound revision, instead of
  rerunning them. G5: timing on ≤ 3 smoke frames outside all blocks and cost projection × 1.3.
- Verdict code for §2: Q1 (Newcombe 10 lower > 0 → CD_BETTER, upper < 0 → Z_BETTER, else NO_DIFFERENCE_SHOWN) and Q2 (inside ±1.5 pp →
  EQUIVALENT, else NOT_EQUIVALENT), anchors first; §3 readouts including the descriptive 3,000-frame pooled Δ_F. Synthetic tests of every
  branch.
- Blindness: no arm on the fresh block. Same deinlab rules as before (tmux `g_gamma0r`, ≤ 24 single-thread processes, ≥ 16 cores free,
  outputs under `.../experiments/gamma0_mixed8_rep_20261120/out/`, scratch under `/data/guoyikun/tmp/`). Phase 1 cap 0.5 core-hour.
- Commit only this task's files and the new experiment directory; append a dated paragraph to `implement.md`; stop.
- Final message (English, ≤ 10 lines): commit hash; fresh block and audit; hash-identity check; projected cost; DRAFT changes with
  reasons; confirmed `model:`.
