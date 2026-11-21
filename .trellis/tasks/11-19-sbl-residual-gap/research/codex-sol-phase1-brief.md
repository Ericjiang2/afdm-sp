Active task: .trellis/tasks/11-19-sbl-residual-gap

# Codex Sol brief: SBL residual gap, Phase 1 (arms K and M, gates, cost), then STOP

Written 2026-11-19 by Claude after Eric chose this test. Eric delegated approvals and the freeze to Claude, so **treat this brief as the
design approval** and do not stop to ask. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root two levels up; branch `main`).
Confirm `model:` is `gpt-6.2-sol`.

## Hard rules
- Phase 1 only: no main run, no freeze.
- **Blindness.** Never run any arm on frames 4600–4799. Phase 1 uses old keys from 4400–4599 and earlier (G1 compares R0 and U2 with
  archived res-20261119-03 rows) and smoke keys. Do not run K or M on 4400–4599 main keys; use smoke keys and synthetic inputs for them.
- Frozen sources are read-only. Reuse `experiments/unified_cov_prospective_20261119/` (`sbl.py`, `projector.py`). New code goes in
  `experiments/sbl_residual_gap_20261119/`. If you must copy a frozen function, put one line at the top stating its source, the change,
  and why it cannot be called directly.
- Do not edit `STATE.md`, any card or the skeleton.
- deinlab: CPU only, one thread per process, ≤ 32 processes, tmux `g_gap`, outputs under
  `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_residual_gap_20261119/out/`. Phase 1 cap: 1.5 core-hours.
- Git: stage only this task's files and the new experiment directory. HEREDOC message, no push, no amend. On `index.lock`, retry
  30 s × 10. Another Sol session (task `11-19-doublet-conflict-check`) may be committing; never stage its files.

## Read first
- `.trellis/tasks/11-19-sbl-residual-gap/research/protocol-DRAFT.md` and `design.md`;
- `research-assets/res-20261119-03.md`;
- the unified experiment's `PROTOCOL.md` (§1, §10.7) and `sbl.py`.

## Deliverables
1. `experiments/sbl_residual_gap_20261119/PROTOCOL.md` (DRAFT copy; give a reason for every change). Verify that 4700–4799 is unused,
   and record the method.
2. Arms R0, U2, K and M per `design.md`, with the per-key fields; configs carry `_argv` / `_config`.
3. Gates G1–G3, with receipts. Defect rule: fix your own code; a frozen-source or archive mismatch means stop and report.
4. Verdict code for DRAFT §2, with synthetic tests of every branch.
5. K census on smoke keys: the share of co-delay blocks with an eigenvalue above 1, and the capped trace relative to the total.
6. Cost projection × 1.3 for 2,400 keys. Commit, append a dated paragraph to the task `implement.md`, and stop.

## Final message
English, ≤ 12 lines, containing:
- commit hash;
- the fresh-block check;
- the gate table;
- the K census;
- the projected cost;
- the DRAFT changes;
- the confirmed `model:`.
