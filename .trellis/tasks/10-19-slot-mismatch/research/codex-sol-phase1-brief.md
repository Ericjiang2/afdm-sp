Active task: .trellis/tasks/10-19-slot-mismatch

# Codex Sol brief — slot-mismatch experiment, Phase 1 (protocol revision, gates, smoke, cost) — then STOP

Written 2026-11-18 by Claude for Eric. You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root is the vault, two levels up;
branch `main`).

## Model discipline (hard rule)
- Every `codex exec` and every `codex exec resume` for this task must pass `-m gpt-6.2-sol` explicitly. On 2026-11-17 an
  omitted `-m` on resume silently fell back to `gpt-6-astra`. If you are resumed, check that this session's log `model:` line
  reads `gpt-6.2-sol`; if it does not, stop and say so in your final message.

## Role boundaries
- You execute Phase 1 only. You do not freeze the protocol, choose minimal vs full scope, set the budget, edit the narrative
  skeleton or accept result cards — Eric decides those at Gate 1/Gate 2. You do not launch the main run.
- Astra (a separate Codex call) will independently derive a Q2 prediction from its 11-11 theory chain; do not try to do that
  derivation for it, and do not read `research/astra-q2-prediction*.md` if it appears before you finish.

## Read first (in this order)
1. `STATE.md` (research items 1–3; decisions 7–9).
2. `.trellis/tasks/10-19-slot-mismatch/prd.md` and `implement.md` (this task's requirements, phases and gates; implement.md is
   the authority for Phase 1 steps).
3. `experiments/slot_mismatch_20261019/PROTOCOL.md` (DRAFT you will revise) and `POSTHOC_CHECKS.md` (10-19 pilots 2–4: same-batch
   ratio D_12/D_8 = .90, edit budget 2→4 ratio 1.00, check 1 direct harm of phantoms replacing spurious slots).
4. `STATE-history.md`, the "2026-10-19 审计与试跑" paragraph.
5. `research-assets/res-20261118-03.md` and `experiments/cstate_codelay_sbl_stage3_20261118/PROTOCOL.md` (closed-form `CODELAY`,
   the mainline arm; its gates and archive are your G2 reference).
6. `FROZEN_DEPENDENCIES.md` (never modify frozen sources; variants are new files with a one-line header: source, change, why it
   cannot be called directly).
7. `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md` points 2 and 4 and the Sec. V-E row
   (the causal sentence "phantoms crowd out weak true paths' slots" that Q2 tests).
8. `research-assets/prediction-ledger.md`, section "2026-11-11 (before the phantom-admission law readout …)" (scalar threshold
   θ_sc ≈ v̄/(2−v̄) is a pairwise ranking law that does not mention slot count) — prior knowledge, not a prediction for you to copy.
9. Existing code you may reuse after re-gating: `experiments/slot_mismatch_20261019/{native_twofft_variant.py,
   geometry_guard_edits_variant.py, sm_driver.py, frame_audit.py, launch_sm.sh}`.

## Deliverables (all in this phase)
1. **Revised `experiments/slot_mismatch_20261019/PROTOCOL.md`, still marked DRAFT**, with:
   - Frames 10000–10999. Verify they are unused: search every experiment driver, launcher and recorded output (local and on
     deinlab under `/data/guoyikun/00inbox/AFDM-channel-estimation/`) for frame ranges that overlap; write the method and the
     result into the protocol. Do not write "unused" without that check.
   - Q2 as a same-batch paired comparison: primary estimand on units triggered at both s=8 and s=12, frame-cluster bootstrap;
     population D_s as secondary. Discuss the selection effect of conditioning on "triggered at both" and the fact that F0_s
     itself changes with s.
   - Arms: `CODELAY` as the mainline CSTATE arm (replaces A1/full Γ); scalar-Γ arm A2 kept; `FULL` as an optional control
     (full scope or a sampled subset only); A3 genie as before.
   - A single σ²-unknown cell: propose a σ̂² estimator using receiver-side quantities only, state every place σ² enters
     (ridge λ = σ², Γ, detector, LLRs), the cell's grid, and its decision rule.
   - Re-check the grid (SNR range, ρ, scenarios) for comparability with P1 and res-20261118-03, and re-check the decision bands
     (Q1 ±.25 dB; Q2 .5/.8) against the expected CI width at 1000 frames; change them only with a written reason.
2. **research-checkpoint moment 1 items inside the protocol** (use the `research-checkpoint` skill if available to you;
   otherwise follow its four parts):
   - Competing hypotheses with per-arm directional predictions for R(CODELAY_s), R(A2_s), D_s and A2's phantom-first-edit share:
     at least H-displace (slot crowding), H-intrinsic (phantoms harmful in themselves / ranking error), and a pre-emption
     alternative (cap-12 F0 already keeps some weak true delays, so fewer rescue opportunities, shrinking D for reasons unrelated
     to crowding). State the 10-19 pilot results as known priors and say which hypothesis each already leans toward.
   - Design-validity questions: slot shortfall at s=12; trigger set changing with s; pairing selection bias; family-T channel-law
     confound; interpretability of the σ̂² cell.
   - Premortem: 3–5 ways the run could fail to answer Q2, each with a mitigation.
   - A new dated section in `research-assets/prediction-ledger.md` with your own probabilities for Q1, Q2 and the σ̂² cell
     (author "Sol", date), written before any new-frame data exists.
3. **Gates** (outputs under `experiments/slot_mismatch_20261019/out/gate_<YYYYMMDD>/`, each with a JSON receipt carrying `_argv`
   and `_config`):
   - G1: the `max_paths=8` variant is bit-identical to the frozen `native_twofft.receive` on ≥32 P1 frames (decoded bits and
     every r0/r1 array); its diff against the frozen file is exactly the max_paths parameter. This gate must pass before anything
     else runs.
   - G2: `CODELAY_8` reproduces archived res-20261118-03 decisions and A2_8 reproduces E-2 family R decoded SHAs on ≥32 historic
     triggered keys each.
   - G3: generator with P_paths=8 reproduces P1 frames bit for bit (≥16); with P_paths=6/10, path count = P, unit per-frame path
     power, delays ≤102; record the redraw rate.
   - G4: recorded slot count = min(s, distinct nominated delays) on every gate unit.
   - G5: σ̂² estimator bias and spread on ≥32 frames (descriptive; no tuning against FER).
   - If a gate fails, stop, record the failure and the evidence, and do not work around it.
4. **Smoke timing and cost** on deinlab: `ssh deinlab`, `cd /data/guoyikun/`, run `nvidia-smi` first; CPU runs with single-thread
   BLAS/OpenMP; tmux sessions named `g_*`; write only under `/data/guoyikun/` (scratch in `/data/guoyikun/tmp/`, never `/tmp`);
   conda via `bash -lc 'conda activate AFDM && …'`. Time ≥12 keys per family. Report core-hours and wall time for a **minimal
   scope** (Q2 primary s∈{8,12}; Q1 s∈{6,8,10,12} on a few key cells; the σ̂² cell) and the **full scope** (all protocol cells),
   each with a suggested cost cap.
5. **Commit and stop.** Follow the commit checklist in this project's `CLAUDE.md` (stage only the files this phase changed; never
   unrelated vault changes; HEREDOC message with body; no push, no amend). Append a dated "Phase 1" paragraph under
   "执行记录" in `.trellis/tasks/10-19-slot-mismatch/implement.md`: what was done, gate results, cost table, open questions for
   Gate 1. Do not edit `STATE.md`.

## Stop point
After the Phase 1 commit, end with a final message (English, ≤25 lines): commit hash, gate pass/fail table, minimal vs full cost
estimates, the three most important open design questions, and the confirmed `model:` value. Do not start the main run, do not
mark the protocol FROZEN, do not call Astra.

## Command Eric uses to start this brief
```bash
cd "/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation" && codex exec -m gpt-6.2-sol -c model_reasoning_effort="high" -s danger-full-access -o .trellis/tasks/10-19-slot-mismatch/research/sol-phase1-last-message.md - < .trellis/tasks/10-19-slot-mismatch/research/codex-sol-phase1-brief.md
```
Resume (always with `-m`; prefer the session id printed at start over `--last`, which picks the most recent Codex session of
any project):
```bash
codex exec resume <session-id> -m gpt-6.2-sol -c model_reasoning_effort="high" "<follow-up>"
```
