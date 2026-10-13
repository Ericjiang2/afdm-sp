# Loop 9 — Round 2 briefing for Oracle (results review)

Date: 2026-04-22
Reviewer: Oracle GPT-5.4-pro / `--engine browser --browser-manual-login`
Prior: `_memory/loop9/oracle_round1_response.md` (C2-rel recipe, 8/10 GO, micro-gate pass).

---

## 1. What we did

Implemented C2-rel **exactly as your Round 1 recipe** in `classical_joint_unrolled.py::CandidateActiveRelationHead`:
- Hook at `t==0` after `omp_sparse_torch` and before `expand_cluster_support`.
- Candidate set: top-M=48 off-support atoms by pre-LS pilot MF `|Phi^H y|`.
- Features: u_j (7) candidate-local, v_{j,s} (6) pair-to-active with **raw** OMP support (not cluster-expanded).
- Arch: pair MLP `6->16->16 SiLU`, max+mean pool, scorer `(7+32)->16->1`.
- Identity-at-init: zero weights, bias=-8. Hook activation verified bit-exact in `_smoke_c2rel_identity.py`.
- Action: add up to K_add_max=4 candidates with logit>0, union with S_omp, pilot-only LS, prune back to P by |gain|, refit LS, continue classical.

Config A (locked, same as Loop 8): **N=1024, v=2 m/s, P=10, tau=10 ms, rho=0.5**.
All runs reuse the torch BP path (`mp_detect_bp_torch`).

## 2. Micro-verify gate (PASSED per your R1 thresholds)

250 paired frames per SNR, 150/100 train/val split, L2 logistic regression proxy on the 19-d pooled feature vector.

| SNR | K=2: resMF/proxy/ratio | K=4: resMF/proxy/ratio | K=6: resMF/proxy/ratio | hit_any@6 (proxy) |
|---:|---:|---:|---:|---:|
| 10 | 0.010 / 0.074 / **7.17x** | 0.017 / 0.107 / **6.20x** | 0.028 / 0.119 / **4.19x** | 0.870 |
| 15 | 0.010 / 0.079 / **8.30x** | 0.023 / 0.112 / **4.97x** | 0.028 / 0.124 / **4.37x** | 0.910 |
| 20 | 0.010 / 0.078 / **8.10x** | 0.019 / 0.112 / **6.02x** | 0.032 / 0.120 / **3.77x** | 0.900 |

All three gates passed: ratio >= 2x everywhere, rec@6 >= 0.12 at SNR=20, hit_any@6 >= 0.45 at SNR=15/20. Posterior bumped 0.30 -> 0.48.

## 3. Cache + training

- Cache: 30k frames (6k/12k/12k for SNR 10/15/20), M=48, P_pad=64 with mask.
  Skip-frame-BER (deliberate speed trade; uniform frame weight, not 2x for bad frames).
- Trainer: AdamW lr=1e-3 wd=1e-4 batch=512 4 epochs, SNR weights 0.2/0.4/0.4, BCE + 0.5 rank.
- Train log:

  | epoch | train_loss | val_bce | r@2 | r@4 | r@6 | hit@6 |
  |---:|---:|---:|---:|---:|---:|---:|
  | 0 (pre-train)  | —      | 0.4012 | 0.005 | 0.013 | 0.028 | 0.066 |
  | 1              | 0.380  | 0.3733 | 0.113 | 0.207 | 0.295 | 0.575 |
  | 2              | 0.345  | 0.1973 | 0.149 | 0.273 | 0.379 | 0.676 |
  | 3              | 0.309  | 0.1924 | 0.562 | 0.805 | 0.883 | 0.981 |
  | 4              | 0.306  | 0.1867 | 0.572 | 0.820 | **0.893** | **0.983** |

  The trained head's recall@6 = **0.893** (well above micro-gate proxy's 0.12) and hit@6 = **0.983**. Training converged cleanly, best at ep 4.
- Ckpt: 1041 params total; `outputs_loop9_c2rel_train/ckpt_c2rel.pt` (7.7 KB).

## 4. Full-SNR eval (1000 frames/SNR)

| SNR | Classical BP | Learned C2-rel | Δ% | NMSE_cls (dB) | NMSE_learned (dB) | McNemar n10 / n01 | p_one-sided (learned better) | Frame-paired t |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | **0.1137** | **0.1089** | **-4.30%** | -11.40 | **-12.02** | 45543 / 35535 | **6.3e-271** (stat-sig BETTER) | +24.4 |
| 15 | 0.0419 | 0.0430 | **+2.53%** | -14.74 | -14.72 | 15073 / 17243 | 1.0 (stat-sig WORSE, -ve direction) | -7.1 |
| 20 | 0.0090 | **0.0130** | **+44.6%** | -18.60 | **-17.39** | 3676 / 11901 | 1.0 | -24.7 |
| 25 | 0.0060 | **0.0111** | **+85.3%** | -18.98 | **-17.30** | 2734 / 13210 | 1.0 | -21.6 |

torch-ref arm matches NumPy classical to ~0.001% (complex64 rounding). Waterfall shape:
- Classical monotone: 0.1137 -> 0.0419 -> 0.0090 -> 0.0060 (good, passes sanity).
- Learned monotone: 0.1089 -> 0.0430 -> 0.0130 -> 0.0111. Monotone but **far above classical** at >=15 dB.
- Learned NMSE dominates at SNR=20 and SNR=25: classical -18.6 / -19.0 dB vs learned -17.4 / -17.3 dB (learning *hurts* channel estimate).

**User rubric verdict: FAIL.** SNR=10 is a huge win, but SNR=15, 20, 25 are stat-sig losses.

## 5. Our mechanism diagnosis (please verify or refute)

The head was trained on BCE+rank for missed-atom recall, and it succeeded at exactly that: recall@6 = 0.89 on val. But recall is not precision. At high SNR the classical OMP already recovers most of the mass, so adding 4 candidates with logit>0 is often **net negative**:

1. Candidate proposer is tuned at low/mid SNR (training mix 1:2:2 over 10/15/20) and **does not condition the logit cut at logit>0 on sigma2**. The scorer puts many candidates >0 at SNR=20 because the proxy-like coherence features look similar per frame regardless of SNR.

2. "Union then prune back to P by |gain|" means that when 4 learned candidates get picked and each grabs some pilot residual energy via LS, **true OMP atoms with smaller |gain| can be kicked out**. The LS of the union is very flexible (P+K_add=~40 columns on N=1024) and will happily split true-tap energy across the learned additions.

3. At SNR=25, classical's NMSE is already near the noise floor; adding even one wrong atom inflates LS variance. Result: classical NMSE -19.0 dB vs learned -17.3 dB (**1.7 dB worse channel estimate**) and BER 2x worse.

4. SNR=15 is the borderline regime: classical NMSE -14.7 dB, learned -14.7 dB (tied), but BER +2.5% — so the learned channel estimate is tied in energy but the support mistakes matter more for detection.

5. At SNR=10 the BER and NMSE both improve: the added atoms are useful because classical OMP misses a lot and noise dominates LS variance; adding "likely-missed" atoms even if imperfect helps on average.

**Summary of the failure mode: SNR-agnostic logit>0 threshold + P-prune is net-positive only in the noise-dominated regime (SNR=10) and net-negative above 15 dB.** This looks like a classic "high-recall, low-precision" calibration problem, not a broken feature design — micro-gate was PASSED on the same features.

## 6. Remediation ideas (rank and correct)

We want to pick exactly ONE minimum fix and redo the eval. All are post-hoc on the trained ckpt; no retraining required.

### Option A — SNR-adaptive logit threshold
Make the add-threshold tau(sigma2) monotone increasing in 1/sigma2. Simple one-knob policy:
  tau = theta * (1 + kappa * max(0, -log10(sigma2) - t0))
with (theta=0, kappa=1, t0=1.0) so tau=0 at SNR=10 and tau increases at SNR>=15. Calibrate kappa on a held-out 500f grid at SNR in {10, 15, 20, 25}. Zero-additional-params.

### Option B — "Precision-margin" threshold
Only add candidate j if logit(j) - min_{s in S_omp} logit(s_imputed) > margin, where the imputed logit for an active atom s is computed by temporarily treating s as a candidate. margin=1.0 blind, calibrate on held-out.

### Option C — K_add=K_add(sigma2) schedule
k_add_max is a function of sigma2 (e.g. 4 at SNR=10, 2 at SNR=15, 1 at SNR=20, 0 at SNR=25). Keeps logit>0 rule but caps aggressiveness.

### Option D — Retrain with BER-aware loss
Use a distillation-style loss: cached (u,v) + the classical BER per frame, train the head to **increase logits only on candidates whose addition reduces BP-LS residual**. Requires regenerating the cache with per-candidate ablation (~hours).

### Option E — "Commit" probability threshold on logit
Add the candidate only if sigmoid(logit) > p0, with p0 calibrated (e.g. p0 = 0.7 or 0.9). Much more conservative than logit>0 (= p>0.5).

## 7. Questions for you

**Q1 (fix pick).** Which of A-E (or a cleaner 6th) is the minimum-viable fix that has highest posterior on delivering:
  (a) **no regression** at SNR=10 vs our current -4.30% win (keep it),
  (b) **stat-sig win** at SNR=15 AND SNR=20 (paired McNemar 500f, same seeds),
  (c) no regression at SNR=25?
Give exact hyperparameter calibration procedure (grid, validation split, sample size).

**Q2 (posterior).** Posterior of win at SNR=15 AND SNR=20 (paired McNemar 500f) under your picked fix, *without* retraining (post-hoc only).

**Q3 (retrain trigger).** Under what result would you advise retraining (Option D) instead of post-hoc calibration?

**Q4 (score / decision).** Score this Loop 9 round 1-10 cumulative with Loop 6/7/8 context. GO for Round 3 (post-hoc calibration) or STOP?

**Q5 (sanity).** Anything in our mechanism diagnosis (section 5) you disagree with? The "recall high, precision bad at high SNR" framing or the "P-prune kicks out true OMP" framing?

## 8. Attached files

- This briefing: `_memory/loop9/round2_briefing.md`
- Oracle R1 response (your prior recipe): `_memory/loop9/oracle_round1_response.md`
- Micro-verify PASS: `_memory/loop9/microverify_results.md`, `_memory/loop9/microverify_gate.json`
- Full eval JSON: `_memory/loop9/eval_results_full.json`
- Head code (section with CandidateActiveRelationHead): `afdm_sp_joint_unrolled/classical_joint_unrolled.py` (class at line ~765)
- Trainer: `afdm_sp_joint_unrolled/loop9_train_c2rel.py`
- BER+NMSE waterfall figure: `figures/loop9/loop9_ber_mse.png`

Be terse (<= 70 lines). We want to pick ONE fix and redo the eval within the hour.
