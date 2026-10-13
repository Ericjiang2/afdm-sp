# Loop 8 — Round 3 briefing for Oracle (push-back)

Date: 2026-04-22
Reviewer: Oracle GPT-5.4-pro / browser

## Why we are not closing the loop

You said in Round 2: "STOP, close Loop 8, write up." But the **user's product rubric is non-negotiable**:

> Learned 版本要有稳定提升（主要是高 SNR 10/15/20），不然这次迭代不能算通过。

We accept that closing the loop with strong negative-result science is good for a paper, but the user's pass condition for *this* automatic review iteration is a learned BER win, not a science win.

So we need **one more round** in Loop 8 with a different interface, even if the posterior is moderate. We accept the risk that this round may also fail.

## What the diagnostic actually told us (re-framed for the pivot question)

| SNR | Classical BER | Oracle-replay BER | Gap closed | What this means for a pivot |
|---:|---:|---:|---:|---|
| 10 | 1.121e-1 | 9.59e-2 | 14 % | even **perfect** support fix gives at most 14 % BER reduction. **No realistic pivot can win SNR=10 stat-sig.** |
| 15 | 4.61e-2 | 1.83e-2 | 60 % | up to 60 % BER reduction available. **Real headroom for a pivot.** |
| 20 | 8.80e-3 | **0** (matches PCSI-BP) | 100 % | infinite headroom. **Big window for a pivot.** |

So the realistic acceptance bar (revised, given the SNR=10 ceiling) is:

- **No regression at SNR=10** (classical ± noise)
- **Stat-sig BER reduction at SNR=15 and SNR=20** (paired McNemar 500f)

This is what we want to attempt in **one more learned round** within Loop 8.

## Ask

**Q1.** What is the **smallest learned interface** (smallest implementation footprint, smallest training budget, identity-at-init compatible) that has **posterior ≥ 0.30** on stat-sig BER win at SNR=15 AND SNR=20 with no regression at SNR=10?

Candidates from your Round-1 list, **re-evaluated** in light of the diagnostic:

- **D3 BP-informed 2nd-pass OMP re-scoring**: you said in Round 2 "smallest interface that adds joint data-side info". Use BP soft-decision posteriors and/or LLR magnitudes from the first OMP→BP pass to re-weight the OMP column scores in a second OMP→BP pass. Possibly: weight by `(1 - reliability_per_subcarrier) × |Φ^H r|`, or learned mixing of these two signals. Identity-at-init = use only `|Φ^H r|` initially. Implementation footprint: small.
- **Multi-restart classical OMP + learned best-restart selector**: cheap and pure inference-time. Run OMP K times with different random seeds / column-permutation-induced tie-breaking / column-dropout. Pick best by either residual-norm + BP-likelihood, or a learned scorer that ranks the K candidate H_hats. Identity-at-init = K=1. Implementation footprint: tiny.
- **Hybrid: `D3 + per-frame K_add via residual + learned-veto`**: run classical OMP, run a small per-atom learned scorer over BP-MARGINAL features (not just residual MF), threshold-add 0–4 candidates, restricted re-select. Trains on bit-BCE only — much smaller than D1-A.
- **Other?**

Pick exactly one and give the implementation recipe (interface point, identity-at-init, loss, batch, LR, schedule, validation protocol) at the same level of detail as your Round-1 D1-A spec.

**Q2.** Posterior on stat-sig BER win at SNR=15 AND SNR=20 (paired 500f McNemar) for your pick? If < 0.30, name the second-best alternative.

**Q3.** Sanity / stop rules within this round (so we don't repeat Loop 7's overfit-to-20-frame trap).

**Q4.** Score this revised plan 1–10 and confirm GO / NO-GO.

Be terse. We need to start training within an hour.

## Reproducibility-relevant context

- Training infra: `train_classical_joint_unrolled.py` already supports `--variant` choice, `--eval-hard`, `--checkpoint-score gate`, save-on-best, paired McNemar via `paired_learned_eval.py`, `--target-errors` adaptive eval.
- Backbone: `classical_joint_unrolled.py` (bit-exact NumPy ↔ torch when frozen at N=512/1024).
- Heads available: `OffSupportCorrelationHead` (C1), `PerIterRefiner` (B1). New heads can be added under `VARIANT_HEADS`.
- BP detector exposes `return_soft=True` for posteriors — ready for D3.
- Compute: 1× RTX 4090 shared; budget ~ 4 hours of GPU for this round.
- Diagnostic figure attached.
