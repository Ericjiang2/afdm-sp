# Loop 9 — Round 1 briefing for Oracle (plan review)

Date: 2026-04-22
Reviewer: Oracle GPT-5.4-pro / `--engine browser --browser-manual-login`
Context budget: one pivot round within Loop 9; we expect 2-3 Oracle rounds total.

---

## 1. Project in one paragraph

AFDM-LEO joint channel-estimation + detector. Classical baseline: OMP + DA-LS + BP (torch-exact with NumPy ref, bit-exact at N=512/1024 when learned scalars are frozen). Backbone is `classical_joint_unrolled.py`. Learned heads plug in via `VARIANT_HEADS` (train/eval/paired-McNemar infra ready). Loops 6–8 produced a strong *diagnostic* null on channel-side learned fixes but no learned BER win.

## 2. User rubric for THIS loop (non-negotiable)

1. Compare classical BP (torch) vs learned joint, channel-side only.
2. Identify where classical fails → why → design learned fix → MICRO-VERIFY the mechanism is actually recovered on diagnostic data → only then run full SNR sweep.
3. **NO dictionary extension** (unfair vs classical, complexity concern).
4. Learned version MUST stat-sig reduce BER at SNR=15 AND SNR=20 (paired McNemar). SNR=10 may be null (per Loop 8, only 14% gap closed even with oracle-perfect support).
5. BER + MSE waterfalls must be physically normal: monotone-decreasing, below PCSI-BP, no sudden cliffs or spikes.
6. Adequate but not excessive Monte Carlo frames. Config banner printed at stdout top.
7. Complexity increase over classical must be modest; learned head should not dominate cost.

## 3. What Loop 8 proved (quantitative)

Config A: N=1024, v=2, P=10, τ=10 ms, ρ=0.5, l_max=102, k_max=4.

### Oracle-dictionary support replay (200 paired f/gate)

| SNR | Classical BER | Oracle-support BER | Gap closed | NMSE(cls/orc) dB |
|---:|---:|---:|---:|---|
| 10 | 1.12e-1 | 9.59e-2 | **14 %** | −11.48 / −13.67 |
| 15 | 4.61e-2 | 1.83e-2 | **60 %** | −14.31 / −20.67 |
| 20 | 8.80e-3 | **0/409 600 bits** | **100 %** | −18.73 / **−30.70** |

Top 20 % of frames carry 63 % of bit errors at SNR=20. Support selection = **100 %** of channel-side gap at SNR=20.

### Residual-MF recall of missed support (D1-A gate)

| SNR | K=2 | K=4 | K=6 | K=8 | K=12 |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.009 | 0.017 | 0.027 | 0.035 | 0.053 |
| 15 | 0.009 | 0.020 | 0.031 | 0.039 | 0.054 |
| 20 | 0.012 | 0.023 | 0.035 | 0.048 | 0.067 |

Frames with `recall==1.0`: 0/200 at every SNR/K. → D1-A (per-atom MF over pilot-residual) pre-gate FAIL.

### BP-soft-aided DD residual recall (D3-lite gate, 250 paired f/gate)

| SNR | K=2 | K=4 | K=6 | Verdict |
|---:|---:|---:|---:|---|
| 10 | 0.07× | 0.06× | 0.12× | — |
| 15 | **0.05×** | **0.08×** | **0.24×** | **FAIL** |
| 20 | **0.00×** | **0.27×** | **0.53×** | **FAIL** |

DD score `d_j = log|A(μ)_j^H ((1−ρ)⊙e)|` is 4–20× *worse* than pilot-residual-MF. BP soft means `μ` are themselves biased toward H0's wrong picks, so the data-aided residual carries even less independent info about missed atoms. → D3-lite pre-gate FAIL.

### Your own Round-2 diagnosis (verbatim, Loop 8)

> "The recall failure is **not** a weak-classifier problem; it is a **structural observability problem after greedy support commits**. Once OMP picks a wrong-but-coherent atom, the LS fit explains away the nearby true atom, so the post-OMP residual MF is almost blind to the miss."

## 4. What we claim is the real unused signal

Both D1-A and D3-lite score each inactive atom `j` with a **scalar** built from the post-LS residual projection `Φ^H r`. This signal is provably near-empty (7% recall at K=12).

The information that WAS lost by LS lives elsewhere and has NOT been given to any of the Loop-6/7/8 heads:

- **Coherence with active set**: `coh_{j,s} = |a_j^H a_s| / (||a_j|| ||a_s||)` tells us "atom j overlaps geometrically with picked atom s, so s may be explaining away j".
- **Masked-mass proxy**: `Σ_s |α_s| · |a_j^H a_s| · kern(Δ(l,k)_{j,s})` — how much LS magnitude on the active set is *coherent* with candidate j's column.
- **Pre-LS pilot MF**: matched-filter on `y − 0` restricted to pilot columns, before the first LS fit, is uncorrupted by the "explained-away" bias. Simple, physics-grounded, cheap.
- **Active-atom gain context**: per active atom s we have `|α_s|`, position `(l_s, k_s)`. Candidates geometrically close to high-|α| active atoms are prime candidates.

## 5. Three candidate interfaces we are considering (pick one, or propose a fourth)

All three preserve identity-at-init and keep complexity << model.

### E1 — "C1+coherence" features-only extension (smallest footprint)
Exact same `OffSupportCorrelationHead` skeleton (per-atom MLP, top-M candidates), but expand feature vector from 11 → 16:
- add `coh_max_j`, `coh_mean_j`, `log(masked_mass_j)`, `|α_nearest_active_j|`, `log(|pre_LS_pilot_MF_j|)`.
Identity-at-init: zero-init final MLP layer (already true in C1). Only MLP widths change. Complexity: +~300 params on 11→16 input width. Cached training possible.

### E2 — "Joint over top-M candidates + active |S|" small attention head
Tokens: (M inactive candidates) ∪ (|S| active atoms). Per-token features include the E1 feature set + token type (active/candidate) + `α_s` for actives. One transformer block (1 head, 32-dim, MLP 2-layer). Output: per-candidate logit. Identity-at-init: attention output bias very-negative → K_add=0 → bit-exact classical. Complexity: a few thousand params, O(M²) attention cost per iter — negligible vs OMP.

### E3 — "Residual image CNN" over full (l, k) grid
Compute `r_grid(l, k) = (Φ_full^H r)_{l,k}` as a (L, 2K+1) complex image. Optional per-column features: `active_indicator(l,k)`, `log|α|` on active. 2-3 layer complex-magnitude CNN predicts `missed_prob(l,k)` for every grid cell. Threshold → candidate support addition. Identity-at-init: classifier head bias ≪ 0 → 0 adds. Complexity: small CNN, can be kept below 50 k params. Higher latency but still negligible per frame.

## 6. What we need from you (be terse, ≤ 80 lines)

**Q1 (method pick).** Which of E1 / E2 / E3 — or a cleaner 4th option — has highest posterior on passing the micro-verify gate defined below AND delivering a paired McNemar stat-sig BER win at SNR=15 AND SNR=20 with no regression at SNR=10? Full implementation recipe: interface point, feature vector, architecture, loss, cache schedule, LR/batch/epoch, validation protocol. Same level of detail as your Loop-6 C1 recipe and Loop-8 D1-A/D3-lite recipes.

**Q2 (micro-verify gate).** The mechanism-recovery gate we will run **before** training on GPU. Concretely: on cached post-OMP+LS artifacts (~250 paired f per gate), measure *predicted* missed-support recall at K_add=2,4,6 for your picked method using random-init weights + a CHEAP supervised proxy (e.g. logistic regression on your feature set, oracle-labeled). The pre-train gate: the proxy scoring must beat residual-MF recall by **≥ 2×** at SNR=15 AND SNR=20 for K_add≤6. If the features themselves cannot do it even with oracle labels, the method cannot win. Propose exact gate metric.

**Q3 (posterior).** Posterior of stat-sig paired McNemar BER win at both SNR=15 and SNR=20 for your pick (500 f).

**Q4 (sanity / stop rules).** Within-round kill-switches so we don't repeat the "train best on 20 frames" overfit trap.

**Q5 (score).** Plan score 1–10, GO / NO-GO.

## 7. Constraints reminder (repeat, these are user-hard)

- Channel-side only; detector-side is a separate loop.
- NO dictionary extension (no fractional atoms, no extra columns).
- Complexity increase must stay "modest" — total learnable params < ~50 k, per-frame eval latency < ~2× classical.
- Same Config A as Loop 8 (N=1024, v=2, P=10, τ=10 ms, ρ=0.5) — no config shopping.
- Paired McNemar 500 f at the three gate SNRs; cache-consistent seeds.
- Config banner printed; BER + MSE waterfall plots; physical-sanity checks.

## 8. Attached files (verify they arrived)

- `_memory/loop8/loop8_summary.md` — Loop 8 narrative.
- `_memory/loop8/oracle_round1_response.md` — your D1-A pick (7/10 GO if gate passes).
- `_memory/loop8/oracle_round2_response.md` — your structural verdict (8/10 science, STOP).
- `_memory/loop8/oracle_round3_response.md` — your D3-lite pick (7/10 GO if DD-score gate passes; both gates failed).
- `afdm_sp_joint_unrolled/classical_joint_unrolled.py` — backbone + existing OffSupportCorrelationHead (C1) at L623.
- `afdm_sp_joint_unrolled/train_classical_joint_unrolled.py` — VARIANT_HEADS registration at L310.
- `afdm_sp_joint_unrolled/loop8_diagnose.py` — oracle-dictionary replay + recall gate.
- `afdm_sp_joint_unrolled/loop8_d3lite_pregate.py` — DD-score pre-train gate.

Thanks — please pick ONE interface and give a full recipe we can start implementing within the hour.
