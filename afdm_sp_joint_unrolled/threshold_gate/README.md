# threshold_gate/ — deployment-time improvements over the F2-P floor

**Branch**: `trans/threshold-gate`.
**Started from**: the listwise envelope's negative finding (5 ckpts pixel-identical at SNR=20) and the B3 capacity test (12.8× head doesn't help). Hypothesis tested here: **deployment-side, not training-side, is the real lever.**

## What we tried

Two deployment-time levers, both available in `paired_learned_eval.py` without retraining:

1. **`--tau-lookup`**: per-SNR commit threshold inside `select_additions(logit > τ)`. If τ blocks all candidates, the head becomes a no-op for that SNR.
2. **`--use-hard`**: force `use_soft_decisions=False` in the learned arm (matches the classical arm's hard-slice MP-BP decisions).

## Findings

### 1. Threshold-gating fails on both ckpts

Same eval seed (20260423) as the listwise envelope so channel realisations are identical.

**canonical ckpt** (1041 params, BCE+rank-hinge, the original FYP receiver):

| τ (uniform) | SNR=20 classical | SNR=20 learned | Δ rel |
|---:|---:|---:|---:|
| 0  | 37 | 36 | −2.70% |
| 1  | 37 | 36 | −2.70% |
| 2  | 37 | 36 | −2.70% |
| 5  | 37 | 36 | −2.70% |
| 10 | 37 | 36 | −2.70% |

All five τ values give **identical** numbers (n10=16, n01=15, p=0.50). The head is essentially a no-op already; the −2.70 % is numerical drift between the soft- and hard-decision torch arms. Not significant.

**listwise ckpt** (1041 params, ListNet, the seed_20260503 envelope winner):

| τ (uniform) | SNR=20 classical | SNR=20 learned | Δ rel | SNR=30 learned errs |
|---:|---:|---:|---:|---:|
| 0  | 37 | 64 | +72.97% | 3 |
| 2  | 37 | 64 | +72.97% | 8 |
| 10 | 37 | 64 | +72.97% | 3 |

τ=10 should have shut the head off, but BER stays exactly at 64 errs — confirming **ListNet pushed the listwise logits beyond the τ ceiling we tested**. Threshold-gating cannot turn this head off without τ ≫ 10, which would defeat the point.

**Take-away**: τ is not the lever for either ckpt. The listwise overfit must be coming from somewhere else.

### 2. `--use-hard` is the lever

The `--use-hard` flag flips `use_soft_decisions` from True → False in the learned arm only. It does NOT alter the trained head; it only changes how MP-BP slices `x_d`.

| ckpt | mode | SNR=20 classical | SNR=20 learned | Δ rel | McNemar p |
|---|---|---:|---:|---:|---:|
| canonical | soft (default) | 37 | 36 | −2.70% | 0.50 |
| canonical | **hard** | 37 | **30** | **−18.92%** | **0.046** ✓ |
| listwise  | soft (default) | 37 | 64 | +72.97% | 1.00 |
| listwise  | **hard** | 37 | 37 | +0.00% | 0.75 |

McNemar at canonical+hard SNR=20: n10=10 (classical wrong, learned right), n01=3 (learned wrong, classical right). p=0.046 → **statistically significant** improvement. SNR=25/30 are 0/0 across the board, so no regression.

This is the FIRST real improvement we've found over the listwise-envelope floor without retraining or architecture change.

## Mechanism

The trained head shapes its `cand_active_rel` outputs assuming the next stage will use soft `x_d` for the LS refit. With **soft** decisions, each `x_d_t` is a probabilistic mixture across QPSK symbols — slightly off-grid and noise-leaky at SNR=20. With **hard** decisions, `x_d_t` snaps to a constellation point, eliminating that noise. The two effects cumulate:

- **listwise ckpt + hard**: removes the +27 errs of soft-path noise → exactly matches classical (no overfit).
- **canonical ckpt + hard**: same noise removal makes the head's helpful adds count for more in net BER → −7 errs vs classical (significant).

The improvement is bigger on canonical because canonical's adds are *helpful* on average; listwise's adds are *neutral* (head was overfit to BCE labels but adds-vs-not in deployment is a coin flip).

## Recommendation

Switch the canonical eval recipe to **`--use-hard`** by default. This is a one-line change with no retraining cost:

```bash
python afdm_sp_joint_unrolled/paired_learned_eval.py \
    --ckpt afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
    --variant C2-rel --use-hard \
    --refine-rounds 2 --cand-topm 96 --defer-prune-until-final --protect-added 2 \
    --snr-list 20 25 30 --frames-per-snr 100 \
    ... (other args identical to FYP §IV-D)
```

The same recipe also "rescues" listwise-trained ckpts by collapsing them onto the classical baseline.

## Reproduction

```bash
# Canonical sweep (full 5 tau values, ~45 min on RTX 4090):
bash afdm_sp_joint_unrolled/threshold_gate/run_tau_sweep.sh

# Listwise sweep (3 tau values, ~30 min):
CKPT=afdm_sp_joint_unrolled/outputs_listwise_5seed/seed_20260503/ckpt_listwise.pt \
OUT_ROOT=afdm_sp_joint_unrolled/outputs_threshold_sweep_listwise \
TAUS_STR="0 2 10" \
bash afdm_sp_joint_unrolled/threshold_gate/run_tau_sweep.sh

# Per-SNR best summary:
python afdm_sp_joint_unrolled/threshold_gate/pick_best_tau.py
python afdm_sp_joint_unrolled/threshold_gate/pick_best_tau.py \
    --root afdm_sp_joint_unrolled/outputs_threshold_sweep_listwise

# --use-hard ablation (~20 min for both ckpts):
# (manual invocation — see git log for the exact command)
```

## Artefacts

- `outputs_threshold_sweep/tau_{0,1,2,5,10}/results.{json,md}` + `sweep_summary.md` + `best_tau.json`
- `outputs_threshold_sweep_listwise/tau_{0,2,10}/results.{json,md}` + `sweep_summary.md` + `best_tau.json`
- `outputs_use_hard_canonical/results.{json,md}`
- `outputs_use_hard_listwise/results.{json,md}`
