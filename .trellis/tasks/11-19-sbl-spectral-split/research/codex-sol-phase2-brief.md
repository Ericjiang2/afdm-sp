Active task: .trellis/tasks/11-19-sbl-spectral-split

# Codex Sol brief: SBL spectral split, Phase 2 (aggregation code, FREEZE.json, main run, results), then STOP

Written 2026-11-19 by Claude. The protocol is **frozen**: see `.trellis/tasks/11-19-sbl-spectral-split/research/freeze-20261119.md`.
Eric delegated all approvals to Claude. Treat this brief as the approval: do not stop to ask, and if a Trellis hook asks for
approval, note that this brief is the approval and continue. Confirm `model:` is `gpt-6.2-sol`.

## Hard rules
- Receiver mathematics is frozen at `2d4c660b` (`spectral_receiver.py`, `phase1.py`); do not change it. If you find a receiver defect,
  stop and report; do not fix it.
- **Order of work.** Write the main launcher and the aggregation code, then unit-test the verdict logic on synthetic numbers. Commit
  that before the main run starts. Write `FREEZE.json`, containing the freeze commit and the source hashes, and verify it before launch.
- Analysis follows the frozen `PROTOCOL.md`: §7 governs over §3. Primary verdicts use the 100-iteration pipeline only. Report the
  400-iteration subset descriptively.
- deinlab: CPU only, one thread per process, at most 16 processes, tmux `g_spectral`. Run as one unattended chain with a budget stop at
  **30 core-hours** and a `STATUS` line of `DONE` or `STOPPED`. While it runs, wait with a single blocking loop that checks `STATUS` at
  most every 5 minutes; do not poll more often.
- Other Sol sessions (tasks `11-18-ratio-sweep` and the read-only readouts) run concurrently. Never stage their files. If git fails on
  `index.lock`, wait 30 seconds and retry, up to 10 times.
- Do not edit `STATE.md`, result cards or the skeleton. Do not interpret mechanisms beyond what the frozen rules output.

## Main run
- 1200 keys × {S0, T0, S-lo, S-hi, S-isolo, S-isohi} at max_iter 100. Join R0, R1 and R2 from the verified E-3c rows.
- Frames 4000–4049 (600 keys) × {R1, S0, S-lo, S-hi} at max_iter 400.
- Bootstrap: 20,000 paired physical-frame cluster draws, seed 20261119, clusters as in E-3c.

## Deliverables
1. `experiments/sbl_spectral_split_20261119/out/main_<date>/RESULTS.md`, organised as:
   - **Observation**: per-arm FER with 95% CI; s, t and I; f for each half; Δ_lo and Δ_hi; per-arm diagnostics (β, iterations,
     converged count, atom counts, co-delay pairs, added trace); per-cell FER; the 400-iteration table.
   - **Frozen verdicts**: the stage class, the class of each half, the shape-contrast classes, and the conclusion on the candidate,
     each exactly as §7 defines it.
   - Score Claude's §7.4 predictions.
2. Small evidence files only: `results.json` with `_argv`/`_config`, the receipts, and the MD5 list of the raw shards. Raw rows stay on
   deinlab.
3. Commit with a HEREDOC message, no push, no amend. Append a dated Phase 2 paragraph to the task's `implement.md`.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- core-hours used;
- the verdict line for each of: stage, lo, hi, Δ_lo, Δ_hi, and the conclusion on the candidate;
- the key numbers: s, t, f_lo, f_hi and Δ_lo, each with its CI;
- anything anomalous;
- the confirmed `model:`.
