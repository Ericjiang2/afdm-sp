Active task: .trellis/tasks/11-20-gamma0-exchange

# Codex Sol brief: Γ = 0 exchange test, Phase 1 (arms, gates, fresh-block audit, verdict code, cost), then STOP

Written 2026-11-20 by Claude. Eric approved Phase 1 on 2026-11-20 ("启动两个"), so treat this brief as the design approval and do
not stop to ask. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root two levels up; branch `main`).
Confirm `model:` is `gpt-6.2-sol`.

## Hard rules
- Phase 1 only: no main run, no freeze.
- **Blindness.** Never run any arm on the fresh block (9400–9799, or the block G3 chooses). Run Z, H and S only on synthetic inputs
  and at most 3 smoke keys outside every evaluation block; report only assertions and timings from them, never phantom or rescue
  counts.
- Frozen sources are read-only (`experiments/tf_cstate_e1_20261017/`, `experiments/cstate_codelay_sbl_stage3_20261118/`, and every
  entry in `FROZEN_DEPENDENCIES.md`). New code goes in `experiments/gamma0_exchange_20261120/`. Reach Z and H by parameter or a thin
  wrapper around the geometry call (variance vector set to zeros; mean replaced by hard decisions). If you must copy a frozen function,
  put one line at the top stating its source, the change and why it cannot be called directly.
- Do not edit `STATE.md`, any card or the skeleton.
- deinlab: CPU only, one thread per process, ≤ 24 processes with ≥ 16 cores left free, tmux `g_gamma0`, outputs under
  `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/gamma0_exchange_20261120/out/`, scratch only under
  `/data/guoyikun/tmp/`. Phase 1 cap: 1 core-hour.
- Git: stage only this task's files and the new experiment directory. HEREDOC message, no push, no amend. On `index.lock`, retry
  30 s × 10.

## Read first
- `experiments/gamma0_exchange_20261120/PROTOCOL.md` (DRAFT) and the task `prd.md` / `implement.md`;
- `experiments/cstate_codelay_sbl_stage3_20261118/` (`PROTOCOL.md`, `run.py`, `codelay.py`) and `research-assets/res-20261118-03.md`;
- `experiments/tf_cstate_e1_20261017/e1_driver.py` (`run_branch`, `ARM_SPECS`) and `geometry_reopen_variant.py`.

## Deliverables
1. Arms CD, Z, H, S and the shared F0 capture, per DRAFT §1; per-key rows carry each arm's edits (slot, old, new), final paths,
   gains, info errors, decoded hash, syndrome, and input identity; configs carry `_argv` / `_config`.
2. Gates G1–G5 per DRAFT §6, with receipts:
   - G1: CD bitwise against stage 3's saved results on the triggered keys among frames 4000–4024;
   - G2: Γ = 0 and Q = BᴴB + λI asserted inside the Z geometry call, with detector inputs other than paths and gains identical to CD;
   - G3: fresh-block audit against every experiment manifest, and distinct true delays on every fresh frame;
   - G4: H decisions equal the frozen QPSK slicer, pilot restored;
   - G5: kickoff timing.
   Defect rule: fix your own code; a frozen-source or archive mismatch means stop and report.
3. Verdict code for DRAFT §2 (P-A with anchors, P-B with disjoint categories, frame-cluster bootstrap 20,000, seed 20261126) and
   the §3 secondary readouts, with synthetic tests of every branch.
4. Cost projection × 1.3 for the full fresh block. Commit, append a dated paragraph to the task `implement.md`, and stop.

## Final message
English, ≤ 12 lines: commit hash; the fresh-block check; the gate table; how Z and H were reached (parameter, wrapper or copy, with
reason); the projected cost; any DRAFT changes with reasons; the confirmed `model:`.
