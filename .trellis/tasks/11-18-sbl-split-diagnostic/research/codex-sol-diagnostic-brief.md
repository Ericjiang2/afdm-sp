Active task: .trellis/tasks/11-18-sbl-split-diagnostic

# Codex Sol brief — SBL interface representation-invariance and support-compression diagnostics (old keys only; then STOP)

Written 2026-11-18 by Claude for Eric. You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation` (git root is the vault, two levels up;
branch `main`). Every `codex exec` / `codex exec resume` passes `-m gpt-6.2-sol`; check the log `model:` line.

## What this is
A bounded diagnostic on saved data. It decides whether a later fresh-frame confirmation of "the SBL scalar/full ranking flips with the
downstream gain interface because some interfaces depend on coordinate representation" is worth designing. It is not that confirmation,
and nothing here licenses "unified" or "confirmed".

## Read first
1. `.trellis/tasks/11-18-sbl-split-diagnostic/prd.md` and `implement.md`.
2. The design: `.trellis/tasks/09-22-tf-production-gap-audit/research/split-invariance-sbl-prospective-DRAFT-20261118.md`, sections 1–3, 5 and
   the "v1 → v2 corrections" (question A, question B, the pre-declared continue / stop / unclear categories, and the claim ceiling).
3. `experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md` and `representation_probe.py` (exact k=2 duplication construction,
   coordinate prior 1/(kP), first-update difference formula; fixed and point only, one synthetic fixture and one saved real key).
4. `experiments/sbl_three_mode_20261020/SUMMARY.md` and `driver.py` (the 200 saved keys, frames 9100–9149, U/G, ρ .3, 7/8 dB; fixed/point/joint
   failures 4/40/23 for scalar Γ and 15/11/2 for full Γ; remote rows under
   `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1/`).
5. `experiments/sbl_freeze_replay_20261020/gram_block.py`, `gram_cohort.py`, `GRAM_COHORT_SUMMARY.md` (the frozen expected-Gram point-gain
   update `eG` on the same 200 keys).
6. `experiments/slot_mismatch_20261019/sm_driver.py::merge_atoms`.
7. `FROZEN_DEPENDENCIES.md` (never modify frozen sources; new code goes in `experiments/sbl_split_diagnostic_20261118/`, outputs in its `out/`).

## Steps
1. **Synthetic checks (before any real key).**
   - `eG`: under exact k=2 duplication with Γ' = DᴴΓD, the implemented ridge α = σ²·P becomes kα, and the aggregated normal-equation
     solution and posterior covariance should equal the original exactly (the draft's derivation in question A). Verify numerically on a
     small fixture; if it fails, stop and report — do not adjust the ridge.
   - `point`: reproduce the existing probe's first-update difference formula.
2. **Gates (record JSON receipts with `_argv` and `_config`).**
   - G1: original-representation fixed/point/joint reproduce the three-mode saved decisions on all 200 keys for both upstreams
     (failure counts and per-key decoded hashes).
   - G2: original-representation `eG` reproduces the saved `gram_cohort` full-block results it corresponds to.
   - G3: after duplication, initial physical H matches the original (relative difference ≤ 1e-12) and the aggregated prior matches.
   - G4: `merge_atoms` applied to an exactly duplicated input recovers the original atom set and H.
   - A gate that fails because the frozen receiver, archive or generator disagrees with saved results: stop, record evidence, do not
     work around it. A failure caused by a defect in your own new driver code (wrong import, wrong binding, typo) is not a gate result:
     fix it, record the fix in the execution log, and rerun. Before the full run, execute the exact entry point **on deinlab** on one key
     (`--smoke-one-key`). Bit-exact gates are platform-bound: the archives were produced on Linux x86-64 with NumPy 1.26.4, so a local
     macOS arm64 / NumPy 2.x run can only check imports and bindings, never G1–G3 hashes (2026-11-18 local smoke: G1 hash mismatch, expected).
3. **Question A (exact duplication), all 200 keys × {L-diag, L-cov} × {fixed, point, joint, eG}:** per key report the relative physical H
   difference after the first gain update, action differences on three deterministic vectors, terminal extrinsic-LLR max and relative L2
   difference, and whether the discrete decoded result agrees. Classify each interface with the draft's pre-declared tolerance
   (H relative difference ≤ 1e-10 and LLR max difference ≤ 1e-9 = representation-invariant).
4. **Question B (support compression), same keys × {L-diag, L-cov} × {fixed, joint}, original vs merged:** per key relative operator error
   ‖H_merged − H‖_F/‖H‖_F; FER and extrinsic log-loss for each arm; M_U,I = FER(U, I) − FER(U-merged, I); the interface contrast
   M_U,joint − M_U,fixed; and the upstream difference of that contrast. Frame-cluster bootstrap (50 clusters, 10,000 draws, fixed seed),
   point estimates and intervals, described as diagnostics.
5. **Run**: one unattended chain on deinlab. Use the SSH alias `deinlab` (it routes through the EasyConnect proxy automatically when
   it is up). Test reachability only with `ssh -o ConnectTimeout=15 deinlab true`; do not use `ec status` (from a Codex process
   `container ls` cannot reach the container service and `ec` then misreports "stopped"). If the ssh test fails, stop and report;
   do not try other routes. (`nvidia-smi` first; CPU only, one BLAS/OpenMP/torch thread per process, **at most 8 workers** —
   the slot-mismatch main run is using 24; tmux `g_sbldiag`; outputs under
   `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sbl_split_diagnostic_20261118/out/`, scratch only in `/data/guoyikun/tmp/`).
   Cost cap 2 core-hours; end with one line `DONE …` or `STOPPED …` in `out/STATUS`. Wait for it to finish (it should take minutes), then
   copy small files back.
6. **Report**: `experiments/sbl_split_diagnostic_20261118/out/RESULTS.md` with the question A table, the question B table, the
   pre-declared category from the draft (continue / stop and write the boundary / unclear) checked rule by rule, scoring of the draft's
   section-5 Claude predictions, and limits. Do not write to `research-assets/prediction-ledger.md` (this is not a pre-registered fresh-frame
   run) and do not edit `STATE.md`, the narrative skeleton or any result card.
7. **Commit and stop**: project `CLAUDE.md` checklist (stage only this task's files; HEREDOC; no push, no amend). Append a dated paragraph to
   the execution record in `implement.md`. Final message (English, ≤15 lines): commit hash, gate table, the category, the two or three
   numbers that decided it, and the confirmed `model:` value.

## Command Eric uses to start this brief
```bash
cd "/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation" && codex exec -m gpt-6.2-sol -c model_reasoning_effort="high" -s danger-full-access -o .trellis/tasks/11-18-sbl-split-diagnostic/research/sol-diagnostic-last-message.md - < .trellis/tasks/11-18-sbl-split-diagnostic/research/codex-sol-diagnostic-brief.md
```
