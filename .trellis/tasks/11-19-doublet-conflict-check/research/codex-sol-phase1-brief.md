Active task: .trellis/tasks/11-19-doublet-conflict-check

# Codex Sol brief: doublet conflict check, Phase 1 (U in the MIXED8 harness, gates, SNR, cost), then STOP

Written 2026-11-19 by Claude after Eric approved it ("Run both"). Eric delegated approvals and the freeze to Claude, so **treat this
brief as the design approval** and do not stop to ask. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root two levels up; branch `main`).
Confirm `model:` is `gpt-6.2-sol`.

## Hard rules
- Phase 1 only: no main run, no freeze.
- **Blindness.**
  - Never run any arm on the fresh block (1000–1599, or the block chosen by DRAFT §1).
  - Use U only on synthetic inputs and smoke frames. **Do not run U on the old evaluation frames 100–195 either**: SNR selection uses
    F0/CD there, and U must stay out of it.
- Frozen sources are read-only. New code goes in `experiments/doublet_conflict_20261119/`. Reuse
  `experiments/unified_cov_prospective_20261119/` (`cstate.py`, `projector.py`) for Γ_U, and
  `experiments/cstate_sparse_doublet_screen_20261118/screen.py` for the MIXED8 family. If you must copy a frozen function, put one line at
  the top stating its source, the change, and why it cannot be called directly.
- Do not edit `STATE.md`, any card or the skeleton.
- deinlab: CPU only, one thread per process, ≤ 32 processes, tmux `g_doublet`, outputs under
  `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/doublet_conflict_20261119/out/`. Phase 1 cap: 1 core-hour.
- Git: stage only this task's files and the new experiment directory. HEREDOC message, no push, no amend. On `index.lock`, retry
  30 s × 10.

## Read first
- `.trellis/tasks/11-19-doublet-conflict-check/research/protocol-DRAFT.md`, `design.md`;
- `research-assets/res-20261118-02.md` and `experiments/cstate_sparse_doublet_screen_20261118/`;
- `research-assets/res-20261119-03.md` and the unified experiment's `PROTOCOL.md` §1 and §10.7 (construction rules).

## Deliverables
1. `experiments/doublet_conflict_20261119/PROTOCOL.md` (DRAFT copy, with a reason for every change).
2. Arms F0, A2, CD and U, plus TRUE_GEOMETRY, with the per-frame fields in `design.md`; configs carry `_argv` / `_config`.
3. Gates G1–G3 per `design.md`, with receipts. Defect rule: fix your own code. A frozen-source or archive mismatch means stop and report.
4. SNR selection by DRAFT §1 (F0/CD on old frames 100–195 only). Report the per-SNR CD failure rate and the choice.
5. Verdict code for DRAFT §2, with synthetic tests of every branch, including the rare-event rule.
6. Cost projection × 1.3 for 600 fresh frames. Commit, append a dated paragraph to the task `implement.md`, and stop.

## Final message
English, ≤ 12 lines, containing:
- commit hash;
- the fresh-block check;
- the gate table;
- the SNR choice and per-SNR CD failure rates;
- the CD call-path note (closed form versus the screen's constant variance);
- the projected cost;
- the DRAFT changes;
- the confirmed `model:`.
