# E2E Phase 1 — Snapshot before Phase 2

**Date snapshotted**: 2026-05-12 (after commits `5455599`)
**Reason**: User electing Phase 2 (5-path investigation, ~10-15 GPU·h) — locking phase-1 state for clean comparison.
**Phase-1 verdict**: 5 cold-start CENet variants stuck at BER 0.5 (random); oracle diagnostics confirmed pipeline is correct; failure is CENet training pathology on sparse DD-grid targets, NOT SP fundamental.

## Phase 1 commits

| Commit | Content | Notes |
|---|---|---|
| `51a34fd` | Initial E2E ladder (E0/E2 v5/v6/v7) | **Mechanism claim "SP fundamental" is wrong** — superseded by `5455599` |
| `5455599` | Forensic correction: CENet pathology, oracle diagnostics, v9/v10 attempts | Authoritative phase-1 state |

## Phase 1 cells (5 architectural variants × 1-2 seeds each)

| Cell | Architecture | Loss | BER | Why it failed |
|---|---|---|---|---|
| **E0** | Pure Transformer 925K params; bug-fixed pilot Re/Im channels; Xavier out_proj; cosine LR | BCE-bits + MSE-symbol | 0.95→0.95 / **0.495** | Pure NN cold-start; can't escape random in 200 iter |
| **E2 v5** | DD-grid CENet (global-pool→MLP head 437K params) + ThresholdNet + analytical chirp + LMMSE | BCE-bits + MSE-symbol | 3.82→**0.95 plateau** / **0.494** | LMMSE+bit loss admits trivial H=0 minimum |
| **E2 v6** | E2 v5 + NMSE-on-H_true supervised pretrain (300 iter) → joint (700 iter) | Phase 1: NMSE; Phase 2: BCE+MSE+0.5·NMSE | NMSE stuck at **1.0** / 0.494 | Pretrain didn't break "predict-zero"; joint phase couldn't recover |
| **E2 v7** | E2 v5 + supervised MSE(g_dd, classical-OMP-output) — "perfect oracle warmstart" | MSE-mean on (L*K)=515 bins | **0.002 = predict-zero baseline** / **0.490** | Loss looked like convergence but is `sum(\|h_omp\|²)/515 ≈ 1.07/515 ≈ 0.002`; CENet output still ~zero (max=0.005 vs target max=0.91) |
| **E2 v9** | Per-position 1D conv head (kept spatial info, AdaptivePool to L delay bins, 80K params smaller) + same MSE | Same MSE-mean on sparse target | 0.002 plateau / 0.494 | Architecture change didn't help; same predict-zero trap |
| **E2 v10** | E2 v9 + magnitude-weighted MSE (\|target\|>1e-3 bins get 100× weight) | Weighted MSE | **0.04 (escaped zero!)** / **0.49** | Model now outputs nonzero, but loss plateaus; couldn't find OMP support |

(v8 was a Xavier-init-only mid-run attempt; killed when it showed the same predict-zero pattern as v7 — no train log saved.)

## Phase 1 oracle diagnostics

The user pushed back on the "BER=0.5 stuck" pattern as "doesn't match prior W8 Path C C1/C3 at 8-9% — likely code bug". This triggered the oracle tests that proved the failure was NOT in pipeline correctness:

**Oracle 1**: `H_eff = H_true (ground-truth)` → my LMMSE detector
- BER = **0.0000** (perfect)
- → LMMSE detector implementation is correct

**Oracle 2**: Classical single-pass OMP gains → my `_HReconstructor` → my LMMSE detector
- BER ≈ **1.4%**
- → AFDM channel reconstruction is correct
- → SP single-pass with classical OMP gives BER 1.4% — **clearly feasible**, NOT random

**Diagnostic 3**: Load `best_e2.pt` from v9, run inference, inspect g_dd:
- CENet output: max=0.0055, mean=0.0015, sum|.|²=0.0022
- Classical OMP target: max=0.91, mean=0.0037, sum|.|²=1.07
- → CENet output is essentially zero; the apparent "loss=0.002 convergence" is the trivial predict-zero baseline

## Phase 1 — what we proved + what we didn't

**Proved**:
1. Our LMMSE detector is correct (oracle BER=0 with H_true).
2. Our AFDM channel reconstruction is correct (OMP gains → 1.4% BER).
3. Classical single-pass OMP at SNR=20 dB in SP regime achieves BER ≈ 1.4% — NOT random.
4. CENet (in 5 architectural variants) cannot train from cold-start to predict sparse DD-grid gains within 500-1000 iters at batch 4.

**Did NOT prove** (these would require Phase 2 work):
1. Whether E2E is feasible with **hybrid** inductive bias (e.g., feeding `Phi^H y` matched-filter correlation as features).
2. Whether **two-head decomposition** (support classification + gain regression) unlocks training.
3. Whether **curriculum** (dense→sparse target sequence) breaks the predict-zero trap.
4. Whether **2D port** of OTFS-SP architecture transfers to AFDM.
5. Whether **10k+ iter + larger batch + multi-SNR** brute-force training would have eventually worked.

**Honest paper §IV-H claim from phase 1 alone** (in `tcom_plan/E2E_ladder_results.md`):
> "We tried 5 cold-start E2E variants and none beat B+; failure mechanism is CENet training pathology on sparse targets, not SP fundamental infeasibility; we do not exhaust the design space; report as negative-by-budget; B+ remains the main contribution."

## Phase 1 files (preserved in repo, untouched by phase 2)

### Code (state at phase-1 end)
- `afdm_sp_joint_unrolled/path_e_models.py` — E0 FixedTransformerReceiver, E2 OtfsModularReceiver, CENet_DDGrid (per-position conv + xavier init, post-v9), ThresholdNet, AutoencoderJointTxRx (E3 unused), _HReconstructor (vectorised analytical chirp)
- `afdm_sp_joint_unrolled/train_path_e.py` — multi-phase trainer (NMSE pretrain, OMP-warmstart MSE, weighted MSE, skip-classical-baseline)

### Train logs (1 per cell)
- `afdm_sp_joint_unrolled/outputs_e2e_ladder/e0/train_log.json` — E0 200 iter
- `afdm_sp_joint_unrolled/outputs_e2e_ladder/e2_v5/train_log.json` — E2 v5 500 iter
- `afdm_sp_joint_unrolled/outputs_e2e_ladder/e2_v6_pretrain_joint/train_log.json` — E2 v6 1000 iter
- `afdm_sp_joint_unrolled/outputs_e2e_ladder/e2_v7_omp_warmstart/train_log.json` — E2 v7 500 iter (predict-zero diagnosis target)
- `afdm_sp_joint_unrolled/outputs_e2e_ladder/e2_v10_weighted_mse/train_log.json` — E2 v10 500 iter (weighted MSE escape attempt)

### Docs
- `tcom_plan/E2E_ladder_results.md` — phase 1 corrected results doc (authoritative version, supersedes any prior)
- `tcom_plan/E2E_phase1_snapshot.md` — this file (index)

## Phase 2 plan (separate doc `tcom_plan/E2E_phase2_plan.md`)

5 candidate paths, ~10-15 GPU·h total budget, separate outputs under `outputs_e2e_ladder_phase2/` so phase-1 artefacts stay intact.
