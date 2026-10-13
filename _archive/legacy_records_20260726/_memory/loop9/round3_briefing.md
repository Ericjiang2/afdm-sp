# Loop 9 — Round 3 briefing for Oracle (close loop)

Date: 2026-04-22
Reviewer: Oracle GPT-5.4-pro / `--engine browser --browser-manual-login`
Prior: `_memory/loop9/oracle_round2_response.md` (A' SNR-adaptive tau pick, 6/10 GO).

---

## 1. Round 2 outcome: A' tau calibration was mis-applied — here's what happened

We implemented your A' recipe exactly: 4-knot tau lookup `{tau10,tau15,tau20,tau25}`, 500f/SNR split 250 calib / 250 confirm, acceptance rules as specified. Ran on 30k-frame trained head.

**Result: all taus locked at 0.** None of `{0, 0.5, 1, 1.5, 2}` at SNR=15 or `{0.5..3}` at SNR=20 or `{2..5}` at SNR=25 passed your BER+NMSE+n10>n01 rule. Confirm VERDICT: FAIL overall.

**Why:** the trained head produces **logits that are always negative**. Per-frame logit distribution on 100 frames each:

| SNR | p5 | p50 | p95 | top4_p50 | top4_p95 |
|---:|---:|---:|---:|---:|---:|
| 10 | -3.44 | -3.20 | -2.96 | -3.01 | -2.92 |
| 15 | -3.24 | -2.98 | -2.76 | -2.82 | -2.74 |
| 20 | -3.02 | -2.77 | -2.55 | -2.59 | -2.50 |
| 25 | -2.80 | -2.54 | -2.31 | -2.37 | -2.26 |

Trained bias = -7.89 (barely moved from init -8). Even the top-4 logit per frame stays at ~-2.3. So `logit > 0` → empty adds → head is a **no-op**.

**The "learned" differences in Loop 9 main eval (-4.3% at SNR=10, +44% at SNR=20) were NOT from the head.** They came from `use_soft_decisions=True` in the learned arm vs `False` in the classical reference — a soft-vs-hard decision artifact on the same OMP+LS+BP skeleton. We verified: with `--use-hard`, learned = classical = torch-ref bit-exact (head = no-op).

Both of your Round-2 diagnoses were sound in spirit; the **concrete bugs were two methodological mistakes** in our pipeline:
1. `logit > 0` commit rule incompatible with trained model's logit distribution.
2. paired_learned_eval default soft-decisions for learned arm, hard for reference — cross-decoration confound.

## 2. Fixed method: force top-K add + hard decisions

One-line patch: set scorer final bias += 18 (from -7.89 to +10.11), so all logits become positive → `select_additions` always returns top-K_add_max=4 candidates ranked by logit. Training's recall-optimised ranking is preserved; the broken commit rule is bypassed.

`--use-hard` flag applied to paired_learned_eval so both arms use hard decisions.

## 3. Final 500f paired McNemar (force-topk + hard, adaptive early-stop)

Target: classical arm cum errors ≥ 2000 per SNR (and ≥ min-frames). Seed 123456. Classical BP (torch) reference used (torch-ref column — matches NumPy classical bit-exactly via the fast BP shim).

| SNR | frames | cls BER | torch-ref BER | learned BER | **vs torch-ref** | **McNemar p** (learned win) | NMSE Δ (dB) | n10 | n01 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 |  50 | 1.122e-1 | 1.122e-1 | 1.113e-1 | **−0.78 %** | **6.24e-3** ✓ | −0.09 | 694 | 604 |
| 15 | 200 | 3.985e-2 | 3.985e-2 | 3.890e-2 | **−2.40 %** | **7.51e-15** ✓ | −0.15 | 1489 | 1098 |
| 20 | 115 | 8.500e-3 | 8.505e-3 | 7.214e-3 | **−15.18 %** | **1.36e-36** ✓ | **−0.64** | 453 | 150 |
| 25 | 162 | 6.167e-3 | 5.775e-3 | 5.362e-3 | **−7.15 %** | **2.46e-16** ✓ | −0.18 | 675 | 408 |

Waterfall: classical 0.112 → 0.040 → 0.0085 → 0.0058 (monotone) ; learned 0.111 → 0.039 → 0.0072 → 0.0054 (monotone, strictly below classical). NMSE monotone. No cliff. All sanity checks pass.

**Verdict per user rubric: PASS.** Stat-sig BER win at all four SNRs (p < 0.01 everywhere; p ≤ 1e-14 at SNR=15, 20, 25).

SNR=20 is the biggest absolute win: learned recovers ~15 % of the BER gap and **0.64 dB of channel NMSE**.

## 4. Method recap (what the final model actually does)

1. Classical OMP on pilot sensing matrix `Phi` → raw support `S_omp` (length = _P_actual per frame, typically 32-38 for this channel).
2. Pilot-only LS on `S_omp` → gains `g_ls`.
3. **C2-rel head** (~1 k params):
   - Candidate pool: top-M=48 off-support atoms by `|Phi^H y|`.
   - Per candidate j: features `u_j` (7-d, includes log|Phi_j^H y|, margin to P-th OMP pick, (l,k) normalised, nearest-active distance, log sigma2).
   - Per pair (j, s ∈ S_omp): features `v_{j,s}` (6-d: coh, log(|alpha_s|·coh), dl/dk, indicators).
   - pair MLP 6→16→16 SiLU; max-pool + mean-pool over s → 32-d.
   - scorer MLP (7+32)→16→1 with final bias set to +10 post-training.
   - Output: **top-K_add=4 candidates** by logit, always adds all 4.
4. Union `S_omp ∪ A` (P+4 ≈ 42 cols for this channel) → pilot-only LS → prune back to |S_omp| by |gain| → refit LS.
5. Cluster-expand ±k_leak → DA-LS iterations → BP detection (unchanged classical pipeline).

Training: supervised on cached (u, v) features + oracle-dict miss labels; BCE + 0.5·rank, AdamW lr=1e-3 wd=1e-4 batch=512 4 epochs, 30k cached frames. Val recall@6 = 0.893, val hit@6 = 0.983.

## 5. Questions for you

**Q1 (final assessment).** Score this Loop 9 result 1-10. Does it pass submission bar?

**Q2 (bias-hack concern).** The "force top-K" post-hoc patch (bias += 18) is functionally equivalent to a two-stage learned ranker (train for ranking, ignore commit calibration). Given that this approach achieves stat-sig wins at all four SNRs, is the bias-hack acceptable as a principled choice — or do you recommend a cleaner alternative (e.g., train with rank-only loss and remove BCE; or train the scorer bias to reflect true P(missed) with an auxiliary target)?

**Q3 (generalisation risk).** The head always adds K_add=4 atoms. This blindly adds 4 even on frames where `S_omp ⊇ S_oracle` (classical already correct). For those frames, the prune-back-to-P refit might evict correct classical atoms. Are we masking a failure case? Recommend a principled precision safety valve (e.g. logit-margin-to-active-atom, or confidence-calibration via temperature scaling on a held-out) that wouldn't disable the head at high SNR like the original `logit > 0` rule did.

**Q4 (paper framing).** Given the bias-hack and the force-topk story, what's the cleanest paper narrative for this result? Options:
  (a) "Learned ranking of off-support candidates + always add top-K" — simple, honest, but invites reviewer "why train at all if we ignore the threshold".
  (b) Retrain scorer with centred logit target so bias=+10 at init falls naturally and commit rule re-enables (Option D from Round 2, but now BER is positive).
  (c) Drop commit rule entirely; always add top-K_add; call it a "ranking-informed support augmenter".

**Q5 (close decision).** Close Loop 9 as success? Or require one more validation round?

## 6. Attached files

- This briefing: `_memory/loop9/round3_briefing.md`
- Oracle R2 response: `_memory/loop9/oracle_round2_response.md`
- Final official eval: `_memory/loop9/official_v2_results.json` (+ SNR=15 extended: `snr15_extend_results.json`)
- R2 tau calibration null: `_memory/loop9/calib_results_full.json`, `tau_lookup.json`
- Head code (class at L765 + forward hook L1100 area): `afdm_sp_joint_unrolled/classical_joint_unrolled.py`
- Trainer: `afdm_sp_joint_unrolled/loop9_train_c2rel.py`
- Cache generator: `afdm_sp_joint_unrolled/loop9_cache_features.py`
- BER+NMSE waterfall figure: `figures/loop9/loop9_final_ber_mse.png`

Be terse (≤ 80 lines). We want to close Loop 9 tonight.
