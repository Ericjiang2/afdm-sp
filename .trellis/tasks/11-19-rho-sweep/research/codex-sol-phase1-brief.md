Active task: .trellis/tasks/11-19-rho-sweep

# Codex Sol brief: ρ sweep, Phase 1 (grid, gates, crossings, leverage, cost), then STOP

Written 2026-11-19 by Claude after Eric approved ("直接做"). Eric delegated approvals and the freeze to Claude, so **treat this brief as
the design approval** and do not stop to ask. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root two levels up; branch `main`).
Confirm `model:` is `gpt-6.2-sol`.

## Hard rules
- Phase 1 only: no main run, no freeze.
- **Blindness.** Never run any arm on the fresh block (5000–5399, or the block chosen by DRAFT §1). Phase 1 may use old Stage 3 frames
  (4000–4399; outcomes archived), split-prospective archived keys, and smoke frames.
- Frozen sources are read-only. New code goes in `experiments/rho_sweep_20261119/`. Reuse
  `experiments/unified_cov_prospective_20261119/cstate.py` and the Stage 3 harness. If you must copy a frozen function, put one line at
  the top stating its source, the change, and why it cannot be called directly.
- Do not edit `STATE.md`, any card or the skeleton.
- deinlab: CPU only, one thread per process, ≤ 32 processes, tmux `g_rho`, outputs under
  `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/rho_sweep_20261119/out/`. Phase 1 cap: 1.5 core-hours. Count only your own
  worker processes in any process guard.
- Git: stage only this task's files and the new experiment directory. HEREDOC message, no push, no amend. On `index.lock`, retry
  30 s × 10.

## Read first
- `.trellis/tasks/11-19-rho-sweep/research/protocol-DRAFT.md` and `design.md`;
- `research-assets/res-20261118-03.md` and `experiments/cstate_codelay_sbl_stage3_20261118/` (`run.py`, `analyze.py`);
- `experiments/unified_cov_prospective_20261119/cstate.py`.

## Deliverables
1. `experiments/rho_sweep_20261119/PROTOCOL.md` (DRAFT copy; give a reason for every change). Audit the fresh block and record the
   method.
2. Grid extension (ρ and SNR per DRAFT §1) and arms F0, A2 and CD. Per key, log errors, the trigger, decoded SHA, u, and the first-edit
   type. Configs carry `_argv` / `_config`.
3. Gates G1–G3 per `design.md`, with receipts. Defect rule: fix your own code; a frozen-source or archive mismatch means stop and
   report.
4. Crossing and verdict code for DRAFT §2, with synthetic tests of every branch, including censoring and not-evaluable cases.
5. Leverage from old Stage 3 rows (ρ .3 / .5 only): crossing half-widths at 400 frames, and the old-data Δ between the two ρ values for
   CD/F0 and CD/A2 (A2 may run on old frames 4000–4399 if needed, within the cap).
6. Cost projection × 1.3 for the full grid. If it exceeds 10 core-hours, apply the DRAFT §6 reductions in order and report the result.
7. Commit, append a dated paragraph to the task `implement.md`, and stop.

## Final message
English, ≤ 12 lines: commit hash; fresh-block audit; gate table; leverage readouts; grid and cost; DRAFT changes; confirmed
`model:`.
