Active task: .trellis/tasks/11-18-sigma2-dd

# Codex Sol brief — decision-directed σ² estimator, Phase 1 (protocol revision, implementation, gates, smoke, cost) — then STOP

Written 2026-11-18 by Claude; launched by Claude via `codex exec` on Eric's instruction. You are the executor (GPT-6.2 Sol).
Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. The git root is the vault,
two levels up; branch `main`.

## Model discipline
Confirm this session's `model:` is `gpt-6.2-sol`. If it is not, stop and say so in your final message.

## Role boundaries
- Phase 1 only. Do not freeze the protocol, start the main run or choose the budget; Eric decides those.
- Do not edit `STATE.md`, the narrative skeleton or any result card.

## Read first
1. `.trellis/tasks/11-18-sigma2-dd/prd.md` and `research/protocol-DRAFT.md`. The DRAFT is the starting design; you may revise it, with
   a written reason for every change.
2. `experiments/slot_mismatch_20261019/PROTOCOL.md`, sections "Unknown-noise cell" and decision rules: the frozen single-frame
   estimator and the N-cell definition.
3. `experiments/slot_mismatch_20261019/out/RESULTS.md`, N rows: B_SF crossing shifts +1.189 / +0.992 dB; A3 moves 4.679 → 5.000 dB.
4. `research-assets/res-20261118-04.md`.
5. `experiments/sp_afdm_frozen_20260920/src/physical.py::projected_variance`, the exact Γ(v).
6. The slot-mismatch receiver code you or the previous Sol session wrote for the N family (`experiments/slot_mismatch_20261019/`),
   to find exactly where σ² enters: pilot front, native CE, CSTATE ridge, detector, LLRs.
7. `FROZEN_DEPENDENCIES.md`. Never modify frozen sources; new code goes in `experiments/sigma2_dd_20261118/` and outputs in its `out/`.
   Each copied file starts with one line: its source, what changed, and why it cannot be called directly.

## Deliverables
1. **Revised `PROTOCOL.md`** in `experiments/sigma2_dd_20261118/`, marked DRAFT.
   - It contains the estimator, design, frozen-style decision rule, competing hypotheses, premortem and gates.
   - Check and fix the units of the residual formula against `obs["sigma2"]`.
   - Verify that frames 11000–11999 are unused, with the same method as the slot-mismatch freshness check. Do not write "unused"
     without the check.
2. **Implementation**: the DD update after F0 round 1. It replaces σ² everywhere downstream, with one update and no iteration.
   The three arms B_known, B_SF and B_DD, plus A3 under each σ², on identical frames.
3. **Gates**, with JSON receipts carrying `_argv` and `_config` under `out/gate_<date>/`:
   - G1, revised 2026-11-18 after the first attempt (`72388150`): the slot-mismatch archive stores no decoded hashes. G1 therefore
     compares the saved per-key fields on 32 historical keys per arm (M-family keys for B_known, N-family keys for B_SF).
     - F0 branch: `syndrome`, `info_errors`, `slot_count`, `slot_count_r0`, `r1_delays`, `r1_dopplers`.
     - A1c branch: `edits`, `final_delays`, `final_dopplers`, `info_errors`.
     - Integers and delays must match exactly. Dopplers must match bitwise, or to |Δ| ≤ 1e-12 if the archive stores rounded JSON
       floats; state which.
     - Run on deinlab only. Bit-exact gates are platform-bound, so never run them on the Mac.
   - G2: synthetic estimator check. With true channel and symbols (v = 0) and correct geometry, mean σ̂²_DD/σ² lies within 1 ± 0.02 on
     32 frames × 8 SNRs. Also report the bias with v > 0 and correct geometry.
   - G3: frame freshness.
   - A failure caused by a defect in your own new code is not a gate result: fix it, log the fix and rerun.
     A frozen receiver or archive mismatch is a gate result: stop and report.
4. **Smoke and cost**: on deinlab, time at least 12 keys per arm, then give core-hours and wall time for the full design with a
   suggested cap.
   - deinlab rules: `ssh deinlab` (routes through EasyConnect automatically; test reachability only with
     `ssh -o ConnectTimeout=15 deinlab true`); run `nvidia-smi` first; CPU only; one BLAS/OpenMP/torch thread per process; at most 16
     workers; tmux session `g_s2dd`.
   - Write only under `/data/guoyikun/`, with scratch in `/data/guoyikun/tmp/`, never `/tmp`. Activate conda via
     `bash -lc 'conda activate AFDM && …'`.
5. **Prediction ledger**: in `research-assets/prediction-ledger.md`, add a new dated section for this study with your own
   probabilities (author Sol) and Claude's from the DRAFT §4.
   - This file has unrelated uncommitted edits by Eric. Stage only your new rows, e.g. via a patch applied with `git apply --cached`,
     and confirm with `git diff --cached`.
6. **Commit and stop.** Follow the project `CLAUDE.md` commit checklist: stage only this task's files, HEREDOC message, no push,
   no amend. Append a dated "Phase 1" paragraph to `.trellis/tasks/11-18-sigma2-dd/implement.md` (create it if missing).

## Final message
English, at most 15 lines. Include:
- the commit hash;
- the gate table;
- the cost estimate and suggested cap;
- open design questions for Eric;
- the confirmed `model:` value.
