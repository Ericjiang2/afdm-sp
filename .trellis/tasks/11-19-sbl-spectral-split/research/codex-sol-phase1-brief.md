Active task: .trellis/tasks/11-19-sbl-spectral-split

# Codex Sol brief: SBL spectral-split test, Phase 1 (arms, gates, smoke, cost), then STOP

Written 2026-11-19 by Claude after Eric chose "SBL spectral test". You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`
(the git root is the vault, two levels up; branch `main`). Confirm `model:` is `gpt-6.2-sol`; if it is not, stop and say so.

## Hard rules
- Phase 1 only. Do not run the main block and do not freeze anything.
- **Blindness.** On the 1200 main keys (E-3c: U/G × ρ .3 × 6–11 dB × frames 4000–4099), run only the reference arms R0, R1 and R2 (their
  outcomes are already known from E-3c). Never compute any new arm (S0, T0, S-lo, S-hi, S-isolo, S-isohi) on a main key in Phase 1. Check
  new arms only on synthetic inputs and on the 12 disjoint smoke keys (frames 8400–8411). Do not interpret smoke FER or NMSE.
- Frozen sources are read-only (`FROZEN_DEPENDENCIES.md`, the E-3/E-3c source manifests). New code goes in
  `experiments/sbl_spectral_split_20261119/`. Import the E-3c modules wherever possible. If a frozen function must be copied to inject a
  matrix ridge, put one line at the top of the copy stating its source, the change, and why it cannot be called directly.
- Do not edit `STATE.md`, any result card or the skeleton.
- deinlab: test reachability only with `ssh -o ConnectTimeout=15 deinlab true` (do not use `ec status`). CPU only, one thread per
  process, at most 16 processes, tmux session `g_spectral`, all outputs under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_spectral_split_20261119/out/`.
  Bit-exact parity gates are platform-bound: run them on deinlab, not on the Mac.

## Read first
1. `.trellis/tasks/11-19-sbl-spectral-split/research/protocol-DRAFT.md`: arms, construction, decision rules, hypotheses.
2. `experiments/tf_e3c_shrink_20261018/`: `PROTOCOL.md`, `e3c_arms.py`, `e3c_driver.py`, `e3c_lib.py`, `e3c_gate.py`, `launch_e3c.sh`.
3. `experiments/tf_e3_sbl_20261017/sbl_rx.py` (`sbl_em`, `gamma_full`, candidate construction).
4. `research-assets/res-20261018-01.md` (E-3c results, raw-row location and MD5 list).

## Deliverables
1. **`experiments/sbl_spectral_split_20261119/PROTOCOL.md`**, marked DRAFT. Every change from the task DRAFT needs a written reason.
   Decide whether the main run **joins** R0, R1 and R2 outcomes from the immutable E-3c rows or **recomputes** them. Join only if the rows
   contain every field the analysis needs (β, iterations, converged flag, atom counts at EM end and at output, co-delay pair census, FER,
   NMSE). Otherwise recompute.
2. **Arms and logging code** exactly as the DRAFT table specifies:
   - The ridge is built once at EM start over the candidate set, block-diagonal by delay, and pruned with the same indices as Γ.
   - `D_ℓ = Γ[S_ℓ, S_ℓ] / sum(v)`, τ = .5.
   - T0 reuses R1's SBL output and changes only the refinement ridge.
   - E-3c's `gamma_consistency` assumes the SBL side and the `_system` side are equal. S0 and T0 differ by design, so check each side
     against its own specification.
   - Support `max_iter` 100 and 400.
   - Per key and arm, log: β, iterations, converged flag, atom counts, co-delay pairs, added trace, the count of D_ℓ eigenvalues in [.25, .75],
     FER and NMSE.
   - Configs carry `_argv` and `_config`.
3. **Gates**, with receipts:
   - **G1 parity**: R0, R1 and R2 on 20 seeded main keys reproduce the archived E-3c fields exactly (stage 1, round 1, candidates, atoms,
     decoded SHA, info errors, NMSE). Run on deinlab.
   - **G2 construction**, on synthetic inputs and the smoke keys:
     - diag(D_ℓ) = 1 within 1e-12;
     - Π_lo is Hermitian and idempotent, and Π_lo + Π_hi = I, within 1e-12;
     - the ridge identities and per-block trace equalities in DRAFT §2 hold within 1e-12 relative to u;
     - S0's SBL Γ equals R2's SBL Γ, and S0's refinement equals R1's;
     - T0's SBL output is bit-identical to R1's;
     - pruning restricts the ridge with the same indices as Γ.
   - **G3 determinism**: each new arm, run twice on the smoke keys, gives identical outputs apart from timing.
   - **Defect rule**: own-code defects → fix, log and rerun. A frozen-source or archive mismatch is a gate failure → stop and report.
4. **Smoke and cost**, on the 12 smoke keys:
   - Measure the mean elapsed time per key and arm at max_iter 100 and 400.
   - Project the main cost × 1.3: 1200 keys × the arms that must run at 100 iterations (depends on the join decision), plus 600 keys
     (frames 4000–4049) × {R1, S0, S-lo, S-hi} at 400 iterations.
   - The draft cap is 30 core-hours. If the projection exceeds it, first shrink the 400-iteration subset to frames 4000–4024. If it still
     exceeds the cap, report and stop.
5. **Commit and stop.** Follow the project `CLAUDE.md` checklist: stage only this task's files and the new experiment directory (small
   files only), HEREDOC message, no push, no amend. Append a dated Phase 1 paragraph to `.trellis/tasks/11-19-sbl-spectral-split/implement.md`.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- gate table;
- the join-vs-recompute decision and its reason;
- the projected main cost, the suggested cap, and the 400-iteration subset;
- the DRAFT changes and their reasons;
- the D_ℓ eigenvalue census on the smoke keys: the share in [.25, .75];
- the confirmed `model:`.
