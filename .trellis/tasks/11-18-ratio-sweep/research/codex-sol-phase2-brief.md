Active task: .trellis/tasks/11-18-ratio-sweep

# Codex Sol brief: ratio sweep v2, Phase 2 (paired-score instrumentation, G4, FREEZE.json, main run, results), then STOP

Written 2026-11-19 by Claude. The protocol is **frozen**: `.trellis/tasks/11-18-ratio-sweep/research/freeze-v2-20261119.md`. Read it
first. It fixes the truth-free anchor that your Phase 1b curve uses and defines the designated pair. Eric delegated all approvals to
Claude. Treat this brief as the approval: do not stop to ask. Confirm `model:` is `gpt-6.2-sol`.

## Hard rules
- **Order of work.**
  1. Implement the designated-pair logging: per unit and arm, at the first exchange, the gross pre-acceptance Schur gains of the
     designated phantom candidate and the designated weak candidate under the one prespecified deletion slot, plus Q_a.
  2. Implement the main launcher and the aggregation of P1–P4 and the secondary reads exactly as the frozen record and v2 DRAFT §6
     define them.
  3. Unit-test the verdict logic on synthetic numbers.
  4. Run **G4**: on historical keys and synthetic inputs, the logged designated gains equal the receiver's internal gain-matrix entries
     bit-for-bit.
  5. Commit.
  6. Write and verify `FREEZE.json`, containing the commit and the source hashes.
  7. Only then launch the main block.
- Do not change the generator, the masking, the F0 or exchange mathematics, or the closed-form definitions qualified in Phase 1b. A
  frozen-source or archive mismatch, or a G4 failure that is not an own-logging defect: stop and report.
- Main block: frames 55000–55999, ρ ∈ {.3, .5}, both at 4.5 dB, all 12 R values. Primary units are forced-miss units with a defined
  window. Run the full continuation on nonzero-syndrome units for the secondary FER read.
- deinlab: CPU only, one thread per process, at most 16 processes, tmux `g_sweep`. Run as one unattended chain with a budget stop at
  **10 core-hours** and a `STATUS` line of `DONE` or `STOPPED`. While it runs, wait with a single blocking loop that checks `STATUS` at
  most every 5 minutes.
- Other Sol sessions (tasks `11-19-sbl-spectral-split` and the read-only readouts) run concurrently. Never stage their files. If git
  fails on `index.lock`, wait 30 seconds and retry, up to 10 times.
- Do not edit `STATE.md`, result cards or the skeleton.

## Analysis
Use 20,000 physical-frame cluster bootstrap draws, seed 20261119, resampling each frame jointly across all R and ρ. For P4, resample
the calibration and main blocks independently.

Report by ρ and pooled:
- P1–P4 with their frozen verdict classes;
- the five global first-edit classes by R (secondary);
- the triggered-unit FER difference between the arms by R;
- the share of units whose anchor is not on the true strong delay;
- the share of units where another anchor's phantom or a third candidate wins globally.

Score Claude's §6.4 predictions.

## Deliverables
- `experiments/ratio_sweep_20261118/out/main_v2_<date>/RESULTS.md` with three layers: observation, frozen verdicts, and an
  explanation section limited to a list of the candidate explanations that the protocol names, without new ones.
- `results.json` with `_argv`/`_config`, the receipts, and the raw-shard MD5 list. Raw rows stay on deinlab.
- Commit with a HEREDOC message, no push, no amend. Append a dated Phase 2 paragraph to the task `implement.md`.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- core-hours used;
- G4 status;
- the P1–P4 verdict lines with their key numbers (ξ₅₀ and its CI, by ρ and pooled);
- anything anomalous;
- the confirmed `model:`.
