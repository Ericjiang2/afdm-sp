Active task: .trellis/tasks/11-18-ratio-sweep

# Codex Sol brief: controlled power-ratio sweep, Phase 1 (generator, logging, calibration block, gates, cost), then STOP

Written 2026-11-18 by Claude and launched via `codex exec` after Eric's decision ("Do the sweep first").
You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`
(the git root is the vault, two levels up; branch `main`). Confirm `model:` is `gpt-6.2-sol`; if it is not, stop and say so.

## Hard rules
- Phase 1 only. Do not run the main block. Do not freeze anything.
- **Calibration block:** log only the inputs the prediction needs (E, u, λ, spacing to the nearest grid candidate, κ, D, F0 weak-path
  miss flag). **Do not compute, log or inspect first-edit classes** of A2 or CODELAY on calibration or main frames. Astra will predict
  from the calibration distributions before any edit class is seen.
- Do not edit `STATE.md`, the skeleton or any result card. Never modify frozen sources (`FROZEN_DEPENDENCIES.md`). New code goes in
  `experiments/ratio_sweep_20261118/`.

## Read first
1. `.trellis/tasks/11-18-ratio-sweep/research/protocol-DRAFT.md` (design, two stages, decision rules).
2. `experiments/admission_law_20261118/` (`PROTOCOL.md`, `replay.py`, `gates.py`): the first-exchange replay and logging you will reuse.
3. `experiments/cstate_sparse_doublet_screen_20261118/PROTOCOL.md`: an existing controlled-channel construction on the P1 generator.
4. `experiments/slot_mismatch_20261019/out/RESULTS.md` and the corrected P1 generator it uses.

## Deliverables
1. **Revised `experiments/ratio_sweep_20261118/PROTOCOL.md`.** Keep it marked DRAFT. Give a written reason for every change. Fix the
   following concretely:
   - the controlled-channel construction: R grid, how the other six path powers are drawn and clamped, and frame alignment across R
     (same delays and Dopplers per physical frame, only powers change);
   - the two frame blocks, with freshness verified;
   - the SNR per ρ cell, chosen from the calibration block by a rule written before you look at it, e.g. the lowest SNR where the F0
     weak-path miss rate is ≥ 30% and F0 FER ≤ .5.
2. **Generator plus first-exchange logging code.** The main-run logging must record each eligible unit's first-edit class for A2 and
   CODELAY. In Phase 1 that part is implemented and gated on historical or synthetic units only, never on calibration frames.
3. **Gates**, with receipts carrying `_argv`/`_config`:
   - G1: on historical slot-mismatch units, the replay path reproduces the archived F0 and first-edit fields exactly (same as the
     admission-law G1). Run on deinlab.
   - G2: the controlled generator realises the requested R exactly (relative error ≤ 1e-12), keeps total power 1, and keeps the weak path
     the weakest. Power changes across R leave delays, Dopplers, pilot, message and noise unchanged.
   - G3: frame freshness for both blocks.
   - Own-code defects: fix them, log them and rerun. A frozen-source or archive mismatch is a gate failure: stop.
4. **Calibration block.** On deinlab, CPU only, one thread per process, at most 16 workers, tmux `g_sweep`, outputs under `/data/guoyikun/…`.
   Per (ρ, SNR candidate, R) cell, write a summary JSON locally containing: F0 weak-path miss rate, F0 FER, eligible-unit count, and the
   distributions (quantiles) of E, u, λ, x = 2(1−ρ)v̄, spacing, κ and D. **No edit classes.** Apply the pre-written SNR rule and record the
   chosen SNR per ρ.
5. **Cost estimate** for the main block (1000 frames per cell), with a suggested cap.
6. **Commit and stop.** Follow the project `CLAUDE.md` checklist: stage only this task's files, HEREDOC message, no push, no amend. Append a
   dated Phase 1 paragraph to `.trellis/tasks/11-18-ratio-sweep/implement.md`, creating the file if needed.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- gate table;
- chosen SNR per ρ;
- eligible-unit counts;
- the path to the calibration summary JSON (Astra will read it);
- main-block cost and cap;
- the confirmed `model:`.
