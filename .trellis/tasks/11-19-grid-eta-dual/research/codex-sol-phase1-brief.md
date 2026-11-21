Active task: .trellis/tasks/11-19-grid-eta-dual

# Codex Sol brief: grid_eta_dual_20261119, Phase 1 (implementation, gates, fresh-frame audit, verdict code, cost), then STOP

Written 2026-11-19 by Claude. Eric chose this test ("两项都冻结") and delegated the freeze to Claude: **treat this brief as the design
approval**; do not stop to ask. Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`
(git root two levels up; branch `main`). Confirm `model:` is `gpt-6.2-sol`.

## Hard rules
- Phase 1 only: no main run, no freeze. Never run any arm on the fresh blocks named in PROTOCOL; old archived keys/units only for gates,
  calibration and leverage; never decode a new arm on archived main keys beyond what the gates require.
- Frozen sources read-only; reuse by import. If you must copy a frozen function, put one line at the top stating source, change, and why
  it cannot be called directly.
- New code in `experiments/grid_eta_dual_20261119/`. Do not edit STATE.md, cards, the ledger or the skeleton.
- deinlab: CPU only, one thread per process, ≤ 32 processes (another Sol session may be running: keep yours ≤ 16), tmux `g_grid`, outputs
  under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/grid_eta_dual_20261119/out/`, no `._*` files (`COPYFILE_DISABLE=1`). Phase 1 cap 2 core-hours.
- Git: stage only this task's files and `experiments/grid_eta_dual_20261119/`; another Sol session (the other 11-19 test) may be committing — never stage its
  files; on `index.lock` retry 30 s × 10. HEREDOC, no push, no amend.

## Read first
- `experiments/grid_eta_dual_20261119/PROTOCOL.md` (DRAFT) and the experiments/cards it cites.

## Deliverables
1. The arms and manipulations of PROTOCOL §1–§2 with per-key fields needed for every primary and secondary readout; configs carry
   `_argv` / `_config`.
2. The gates of PROTOCOL §6 with receipts (defect rule: fix your own code; a frozen-source or archive mismatch means stop and report).
3. Any calibration PROTOCOL asks for, from archived rows only.
4. Fresh-block audit on local and deinlab (same method as earlier 11-19 receipts).
5. Verdict code for the primary rules with synthetic tests of every branch.
6. Cost projection × 1.3; apply PROTOCOL's cap rule (main cap: X ≤ 3、S ≤ 10 core-hours).
7. Append "Appendix A. Phase 1 revisions and reasons" to PROTOCOL.md (do not edit the numbered sections). Commit and stop.

## Final message
English, ≤ 12 lines: commit; audit result and chosen blocks; gate table; calibration result; projected cost; Appendix A changes; `model:`.
