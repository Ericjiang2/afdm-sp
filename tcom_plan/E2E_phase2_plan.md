# E2E Phase 2 — 5-Path Investigation Plan

**Date**: 2026-05-12
**Budget**: ~10-15 GPU·h (user-approved per option 3 of the wrap-up question)
**Goal**: Exhaust the design space sufficiently to make the paper §IV-H E2E claim either (a) defensible "negative-fundamental within the explored regime" or (b) "E2E is feasible with hybrid OMP+NN; here is the BER".
**Pre-state**: 5 phase-1 cells (E0/E2 v5/v6/v7/v9/v10) all stuck at BER=random. Oracle diagnostics proved pipeline correct; CENet training pathology blamed. See `E2E_phase1_snapshot.md`.

## Paths (priority-ranked by expected ROI)

### Path A — Hybrid OMP + NN refinement (HIGHEST PRIORITY)
**Idea**: Compute `Phi^H y` (classical OMP's matched-filter correlation step) as input features to CENet. CENet only learns to *refine* the correlation, not learn the entire sparse-recovery problem from raw y.
**Architecture**: CENet input = (Re/Im of Phi^H y reshaped as (L, K, 2), plus auxiliary features). Output = refined (L, K) gains.
**Loss**: BCE-bits + MSE-symbol (end-to-end, no need for OMP-warmstart since features ARE OMP correlation).
**Hypothesis**: Adding matched-filter inductive bias gives CENet a head-start at the active support, so MSE doesn't have to learn it from scratch.
**Budget**: ~2 GPU·h.
**Outcome interpretation**:
- BER ≤ 5% (matches classical single-pass OMP) → Path A confirms hybrid pattern unlocks E2E. Paper has a positive E2E control + "iterative vs single-pass" Pareto narrative.
- BER ≈ 50% random → CENet training is broken even with strong inductive bias; pure-E2E in our SP regime needs more than matched-filter prior.

### Path B — Two-head decomposition (support + gain)
**Idea**: Decouple sparse recovery into (i) which (l, k) bins are active (binary classification) + (ii) gain values at active bins (regression).
**Architecture**: Same backbone; two heads:
- Support head: outputs (L, K) sigmoid logits; BCE against `(|h_omp| > 1e-3)` mask.
- Gain head: outputs (L, K) complex gains; MSE only on bins where support label is 1.
**Loss**: 1.0 × BCE_support + 1.0 × MSE_gain_on_active
**Hypothesis**: Separating "where" from "how much" matches the structure of classical OMP (correlation → select → solve), letting NN learn each subtask under proper supervision.
**Budget**: ~3 GPU·h.

### Path C — Curriculum dense → sparse
**Idea**: Pretrain CENet to predict `H_true` as a DENSE N×N matrix (no sparsity assumption). After warming up, transition to OMP-sparse target.
**Architecture**: Same as E2; loss schedule.
**Loss**: Phase 1 (500 iter): MSE on flattened H_true (5×N², no sparsity); Phase 2 (1000 iter): blended into sparse MSE.
**Hypothesis**: Dense targets are easier for MSE to learn; sparse comes after the model has a working channel-estimate inductive bias.
**Budget**: ~3 GPU·h.

### Path D — 2D OTFS architecture port
**Idea**: Reshape 1D y (N=1024) into 2D (M=32, N=32) matrix; use OTFS-SP modular paper's 2D U-Net architecture.
**Architecture**: New 2D model; significant refactor.
**Hypothesis**: The 1D-to-DD-grid mapping in our problem may not have the right 2D structure for conv. Reshaping might expose a structure NN can exploit.
**Risk**: Physical meaning of 2D reshape on AFDM is unclear — AFDM is 1D DAFT, not 2D Zak. May be a non-meaningful transformation.
**Budget**: ~5 GPU·h (most expensive due to substantial refactor).
**Note**: Lower priority. Only attempt if A/B/C all fail.

### Path E — Brute-force training scale
**Idea**: Best-of-phase-1 architecture (E2 v10 with weighted MSE) + 10k iter + batch 16 + multi-SNR (SNR ∈ {10, 15, 20, 25}) + cosine LR with warm-restart.
**Architecture**: E2 v10 + larger batch + scheduler tweaks.
**Hypothesis**: 200-500 iter at batch 4 is too little. More compute might escape the plateau even without architectural fix.
**Budget**: ~5 GPU·h.

## Execution order

1. **Path A first** (highest probability, lowest cost). If A succeeds → likely the answer; B/C still informative for ablation.
2. **Path B second** (decoupled losses likely help even if A works).
3. **Path E third** (brute force; quick to launch in parallel with A's running).
4. **Path C fourth** (curriculum; subtle).
5. **Path D last** (only if A/B/E/C all fail and budget remains).

Parallel where GPU permits.

## Phase 2 output structure

All phase 2 results under `afdm_sp_joint_unrolled/outputs_e2e_ladder_phase2/`:
- `pathA_hybrid_omp_nn/`
- `pathB_two_head/`
- `pathC_curriculum/`
- `pathD_2d_arch/`
- `pathE_brute_force/`

Each contains: `train_log.json`, `results.md` (paired vs single-pass OMP and B+ baselines), `best_ckpt.pt`.

Phase 1 artefacts (in `outputs_e2e_ladder/`) remain untouched.

## Phase 2 decision flow

| Best result | Paper §IV-H claim |
|---|---|
| Some path BER ≤ 1.5% (matches classical single-pass) | "E2E feasible with hybrid inductive bias; gives positive E2E result + 'iterative-iter=10 beats single-pass-NN' Pareto" |
| Best path BER 5-20% (partial learning) | "E2E partially feasible but underperforms classical; tabulate all 5 attempts as ablation" |
| All paths BER ≈ 50% | "Robust negative-by-budget: 10 architecturally-distinct E2E variants fail; B+ multi-component head is the practical solution" |

## Time tracking

| Path | Start | End | Wall (min) | GPU·h |
|---|---|---|---|---|
| A | TBD | TBD | TBD | TBD |
| B | TBD | TBD | TBD | TBD |
| C | TBD | TBD | TBD | TBD |
| D | TBD | TBD | TBD | TBD |
| E | TBD | TBD | TBD | TBD |
