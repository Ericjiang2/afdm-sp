Active task: .trellis/tasks/11-18-ratio-sweep

# Codex Sol brief: ratio sweep Phase 1b (forced-miss v2: generator, F0 masking, recalibration, closed-form predictions), then STOP

Written 2026-11-19 by Claude. Eric delegated all approvals to Claude for fully automatic work on 2026-11-19. Treat this brief as the
approval: do not stop to ask for design approval, and if a Trellis hook asks for it, note that this brief is the approval and continue.
You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root two levels up; branch `main`).
Confirm `model:` is `gpt-6.2-sol`; if it is not, stop and say so.

## Hard rules
- Phase 1b only. Do not run the main block and do not freeze anything.
- **No exchange outcomes on any v2 frame.** Do not run or log first-exchange classes on calibration v2 or main v2 frames. Calibration v2
  runs the masked F0 only and computes the closed-form quantities.
- Frozen sources are read-only. New or changed code stays in `experiments/ratio_sweep_20261118/`. If a frozen F0 function must be copied
  to add delay masking, put one line at the top of the copy stating its source, the change, and why it cannot be called directly.
- Do not edit `STATE.md`, result cards or the skeleton.
- deinlab: test reachability only with `ssh -o ConnectTimeout=15 deinlab true`. CPU only, one thread per process, at most 16 processes,
  tmux `g_sweep`, outputs under the experiment's remote `out/`. Run bit-exact checks on deinlab.

## Read first
1. `.trellis/tasks/11-18-ratio-sweep/research/protocol-v2-DRAFT.md`: the v2 design, closed-form R_A2* and R_C*, the SNR rule and the
   decision rules.
2. `.trellis/tasks/11-18-ratio-sweep/research/external-critique-gemini-20261119.md`: why v2 replaces v1.
3. Your Phase 1 work: `experiments/ratio_sweep_20261118/PROTOCOL.md`, `sweep.py`, `phase1.py`, `out/phase1_verified/`.

## Deliverables
1. **Revise `experiments/ratio_sweep_20261118/PROTOCOL.md` to v2**, still DRAFT. Keep the v1 text in a "Superseded v1 design" section; do
   not delete it. Give a reason for every deviation from the task v2 DRAFT.
2. **Generator v2**:
   - Clip the background paths to [.1, .4] relative to the original strong power.
   - Weak path = 1/R. Drop the weakest-path requirement; the strong path must stay the unique maximum.
   - R grid {1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64, 128}.
   - Frame IDs: calibration v2 54000–54199, main v2 55000–55999, same namespace.
3. **Forced-miss F0**:
   - Exclude every candidate on the designated weak delay from every F0 delay-selection step, so that round-1 decoding uses the masked
     support. Do not delete the delay after the fact.
   - Save the r1 state. In the main run, A2 and CODELAY start their first exchange from that same state with the bank unmasked; implement
     this now, but qualify it only on historical or synthetic inputs.
4. **Closed-form per-unit quantities** from r1, with no truth and no exchange:
   - E, u, λ and z = |D|, defined as in Phase 1 (strong anchor and nearest legal same-delay candidate);
   - T = E+u+λ;
   - `R_A2* = (T² − z²E²)/(z²(u+λ)²)`;
   - `R_C* = (T² − z²(E+u)²)/(z²λ²)`, set to +∞ when the numerator is ≤ 0;
   - ξ = R/R_A2*.

   A unit without an anchor or a legal candidate is "window undefined".
5. **Gates**, with receipts carrying `_argv`/`_config`:
   - **G1**: Phase 1 G1 still passes. With masking disabled, the v2 code reproduces the archived historical keys exactly.
   - **G2**: realized R, total power 1, background clip and strong-path uniqueness hold across the v2 grid. Masked F0 never selects the weak
     delay, and the masked bank differs from the full bank only by that delay. Closed-form check: at z = 1, R_A2* equals 1 + 2E/(u+λ) and
     R_C* equals 1 + 2(E+u)/λ to 1e-12, on synthetic values.
   - **G3**: freshness of both v2 blocks against all earlier blocks.
   - **Defect rule**: own-code defects → fix, log and rerun. A frozen-source or archive mismatch → stop.
6. **Calibration v2**:
   - Masked F0 only, ρ ∈ {.3, .5}, SNR ∈ {4.5, 5.5, 6.5, 7.5, 8.5} dB, all 12 R values, 200 frames per cell.
   - Per cell: F0 FER, the window-defined count, the count with ξ in [1/4, 4], quantiles of E, u, λ, z, R_A2*, R_C* and ξ, and the
     predicted shares P̂_A2 = share(ξ > 1) and P̂_C = share(R > R_C*) among window-defined units.
   - Apply the SNR rule exactly as written: per ρ, choose the SNR that maximizes the total count of window-defined units with ξ ∈ [1/4, 4]
     over all R; on a tie, take the lower SNR.
   - Write `out/phase1b/calibration_v2_summary.json` and `out/phase1b/predictions_v2.json` (selected SNR, P̂_A2 and P̂_C per (ρ, R)). The
     predictions file is the pre-registered theory curve.
7. **Cost estimate** for the main v2 block: 1000 frames × 12 R × 2 ρ, every unit eligible, first exchange for both arms plus the full
   continuation on nonzero-syndrome units. Add 30% headroom. Draft cap: 10 core-hours.
8. **Commit and stop.** Follow the project `CLAUDE.md` checklist: stage only this task's files and the experiment directory (small files
   only), HEREDOC message, no push, no amend. Append a dated Phase 1b paragraph to `.trellis/tasks/11-18-ratio-sweep/implement.md`.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- gate table;
- selected SNR per ρ and the ξ∈[1/4,4] counts;
- the share of units with an undefined window;
- the path to `predictions_v2.json`;
- main cost and cap;
- the confirmed `model:`.
