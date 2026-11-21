Active task: .trellis/tasks/11-19-gate-sbl-test

# Codex Sol brief: gate SBL test, Phase 1 (arms G and G-ex, gates, audit, verdict code, cost), then STOP

Written 2026-11-19 by Claude. Eric chose this test ("先冻结协议") and delegated the freeze to Claude: **treat this brief as the design
approval** and do not stop to ask. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root two levels up; branch `main`).
Confirm `model:` is `gpt-6.2-sol`.

## Hard rules
- Phase 1 only: no main run, no freeze.
- **Blindness.** Never run any arm on SBL frames 5800–6199 or MIXED8 frames 1600–2199. Never decode with G on archived SBL main keys
  (4400–4599, 4800–4999); use the 12 E-3c smoke keys (8400–8411) and synthetic inputs for G decoding. Constructing P_gate on archived
  keys (no decoding) is allowed for G3. G-ex may decode on archived MIXED8 frames 1000–1019 only for G2/G5.
- Frozen sources are read-only, including `experiments/gate_screen_20261119/gate.py` (`bb5ad661`), `experiments/unified_cov_prospective_20261119/`
  (`sbl.py`, `projector.py`, `cstate.py`) and `experiments/doublet_conflict_20261119/`. Reuse by import. If you must copy a frozen
  function, put one line at the top stating source, change and why it cannot be called directly.
- New code in `experiments/gate_sbl_test_20261119/`. Do not edit `STATE.md`, any card or the skeleton.
- deinlab: CPU only, one thread per process, ≤ 32 processes, tmux `g_gsbl`, outputs under
  `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/gate_sbl_test_20261119/out/`. Phase 1 cap 2 core-hours. Do not copy
  macOS `._*` files (use `COPYFILE_DISABLE=1` or rsync excludes).
- Git: stage only this task's files and the new experiment directory. HEREDOC message, no push, no amend. On `index.lock`, retry 30 s × 10.

## Read first
- `experiments/gate_sbl_test_20261119/PROTOCOL.md` (DRAFT; §1 is the arm definition);
- `experiments/gate_screen_20261119/SCREEN.md`, `gate.py`, `s2.py` (the P_gate construction on the SBL initial grid you must reuse);
- `research-assets/res-20261119-03.md` and `res-20261119-04.md`;
- the unified experiment `PROTOCOL.md` §10 and `sbl.py`; the doublet experiment `PROTOCOL.md` and `mixed8_receiver.py`.

## Deliverables
1. Arm **G** in the SBL pipeline (R0, S-lo, G) and arm **G-ex** in the MIXED8 pipeline (F0, CD, G-ex), per PROTOCOL §1. Per-key
   fields: decoded flag, FER inputs, output co-delay pair count, β, iterations, converged flag, and the gate census of §4 (per block:
   size, rank P_gate, rank Π_lo, tr(P_gate Π_lo)); G-ex also logs, per frame, the number of trial supports where the gate fired and a
   fingerprint for byte-identity with CD; the 0.35-bin resolution fields of §3 (two distinct atoms at the true delay, optimal
   assignment, each ≤ 0.10 bin). Configs carry `_argv` / `_config`.
2. Gates with receipts (defect rule: fix your own code; a frozen-source or archive mismatch means stop and report):
   - G1: R0 and S-lo reproduce archived res-20261119-03 rows (non-timing fields) on 20 seeded archive keys.
   - G2: the G path with P_gate replaced by Π_lo is byte-identical to archived S-lo on the same 20 archive keys (with the
     substitution it is S-lo, so this does not unblind G); the G-ex path with Π_lo substitution is byte-identical to archived U on
     MIXED8 frames 1000–1019.
   - G3: P_gate on the SBL initial grid matches the gate-screen S2 per-block ranks on ≥ 20 archived S2 keys (construction only).
   - G4: repeatability of complete non-timing rows on smoke keys.
   - G5: on MIXED8 frames 1000–1019, report how many trial supports the gate fires on and whether G-ex rows equal CD rows.
3. Fresh-block audit for SBL 5800–6199 and MIXED8 1600–2199 (local and deinlab, same method as the residual-gap Phase 1 receipts).
4. Verdict code for PROTOCOL §3 (S leg, X leg, joint, validity condition) with synthetic tests of every branch.
5. Leverage check: from archived res-03 rows, the paired S-isolo − S-lo 95% half-width at 2,400 keys and its √2 projection to 4,800.
6. Cost projection × 1.3 for the main run (S leg at 4,800 and at 2,400 keys; X leg 600 frames); apply PROTOCOL §2's 25 core-hour rule.
7. Append Phase 1 revisions to PROTOCOL.md as "Appendix A. Phase 1 revisions and reasons" (do not edit §0–§7). Commit and stop.

## Final message
English, ≤ 12 lines: commit hash; fresh-block audit; gate table; G5 firing count; leverage half-widths; projected cost and chosen
frame block; Appendix A changes; `model:`.
