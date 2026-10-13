# Loop 6 — Oracle Phase A briefing (AFDM learned joint receiver)

## Role

You are a senior ML reviewer (NeurIPS/ICML level). Score this research project 1–10 for a top wireless-communication-ML venue and give concrete actionable fixes. We need a head/training redesign that WILL achieve a stable gain over classical at high SNR.

## Project

**Goal.** Unroll the classical AFDM joint-OMP-MP iterative receiver into a differentiable torch module (`ClassicalJointUnrolled`) and train learnable heads/scalars so the learned receiver beats the classical one on BER at high SNR while keeping the BER/channel-MSE waterfall physically sane.

**System.** AFDM (Affine Frequency Division Multiplexing) over a doubly-selective channel. Config locked for this loop (per user): **N=1024, velocity=2, τ_rms=10 ms, QPSK, rho=0.5 pilot fraction (superimposed)**. We will sweep **P ∈ {6, 8, 10} paths** (nominal sparsity) and pick the one with cleanest comparison.

**Classical baseline (bit-exact torch replica confirmed).** `joint_omp_mp_iterative` with T=5 outer iters:
- iter 0: OMP(y, Phi, sparsity=P) → support → cluster-expand ±k_leak → DA-LS gains on expanded support
- iter ≥1: hard-decision DA-LS refit of tap gains → reconstruct H → sparsify → BP(y−Hx_pilot) detect → damp symbols → σ² update → early stop

**The torch replica is bit-exact to the NumPy classical across 400 frames × 5 SNR.** (Fixed in Loop 5 via `module.cfg.n_paths = sparsity` per-frame sync.)

## User rubric (first priority)

1. **Learned hard-decision BER < classical hard-decision BER at SNR ∈ {10, 15, 20} dB** with 95% Wilson CI separation. Low SNR (0, 5 dB) can tie. **Iteration fails unless this holds.**
2. BER waterfall is physically plausible: monotone decreasing in SNR, strictly **above** perfect-CSI BP lower bound, no cliffs/dropouts or sudden kinks. Same for channel NMSE.
3. Adequate MC frames (Wilson 95 % CI), reasonable runtime.
4. GPU priority.
5. **Judge LINES, not just points.** The learned-BER line shape should be correct, below classical line at high SNR.

## Loop 5 state (what we confirmed)

Pipeline is now trustworthy (bit-exact torch-ref ≡ NumPy classical). TWO learned variants failed the rubric under hard-decision eval:

### Variant S-lam (5 params, λ_ls_factor-only)
5 per-iter `λ_ls_factor` scalars trainable, clipped `(5e-4, 2e-3)`. Other scalars frozen.
Soft-eval gain: +5.43e-4 mean_Δ but **hard-eval does NOT generalize**.

### Variant B3 (3.6k params, channel_tap_corrector DeepSets)
```
ChannelTapCorrector:
  feats per active tap i: [Re(g_i), Im(g_i), |g_i|,
                           Re(c_i), Im(c_i), |c_i|,    <-- c_i = A_active^H (y − A g_LS)
                           l_i/l_max, k_i/k_max,
                           t/(T-1), log σ², log ||r||²]
  encoder 11→32→32 SiLU, mean-pool, decoder 64→32→2
  Δg_i = 0.1 · tanh(dec)
  zero-init last linear → identity at start.
```
Trained heads-phase 240 iter, lr 3e-4, batch 2, BP-mode, complex128, SNR∈{10,15,20,25}, loss = λ_bce·BCE + λ_sym·‖x̂−x‖² + λ_chan·‖Ĥ−H‖².

### Canonical 400-frame hard-eval table (N=1024 v=2 τ=10ms P=8, seed 5151)

| SNR | classical NumPy-hard | torch-ref hard zero-init | learned B3 hard | Δ vs cls |
|---:|---:|---:|---:|---:|
|  5 dB | 1.905e-1 | 1.905e-1 | 1.905e-1 |  0.0 % |
| 10 dB | 1.047e-1 | 1.047e-1 | 1.048e-1 | +0.1 % |
| 15 dB | 3.184e-2 | 3.184e-2 | 3.208e-2 | +0.7 % |
| 20 dB | 2.164e-3 | 2.164e-3 | 2.290e-3 | +5.8 % |
| 25 dB | 1.383e-3 | 1.383e-3 | 1.455e-3 | +5.2 % |

Waterfall passes sanity (monotone, below perf-CSI-BP, no cliffs) — but the learned arm is a consistent **mild regression**, not a win.

## Diagnosis (Codex Round-3 hypothesis)

At the **LS optimum on the active support**, the gradient w.r.t. tap gains is zero, so
`c_i = A_active^H (y − A g_LS) ≈ 0` for i ∈ active. **Therefore the B3 head receives a near-dead feature** under hard decisions (soft decisions perturb LS optimality, explaining why soft-eval showed gain that did not generalize to hard eval). S-lam has no head features at all and is trying to compensate via bulk regularization in a regime where the classical λ is already near-optimal.

## Key constraints / guardrails

- **MUST stay identity at init** — when heads=() or zero-weights, the module must bit-exactly match NumPy classical (already satisfied).
- Training eval mode must be hard-decision; use_soft_decisions=True only during training for gradients; eval `--use-hard`.
- complex128 throughout (soft-decision precision noise hurt Loop 5).
- **No oracle-support cheating** in training or eval.
- Budget: ≤4 hours per variant training on one RTX 4090.

## Question for the reviewer

**Phase A task.** Given the Loop-5 dead-feature problem at LS optimum on active support:

1. **Propose 2–3 head redesigns** that inject useful gradient signal under hard-decision operation. Consider:
   - off-support residual correlations (columns of Phi **not** in active support) → carry support-misspecification signal.
   - pre-LS vs post-LS gain delta, or the LS step itself as a feature.
   - the detector-side bit-LLR magnitudes and their cross-iter trajectory.
   - σ²_eff history / resnorm trajectory as conditioning.
   - a final-iter-only post-filter (learned soft-decision ensemble over x_soft_history).
2. **Rank them by probability of achieving the rubric #1 gate on P=8 at N=1024 v=2.**
3. **Specify the training target** (BCE on bit posteriors? MSE on symbols? hybrid? curriculum on SNR?).
4. **Name the one single concrete experiment** you would run next. A minimum head architecture (input features → layers → output), a 1-page training recipe (loss, SNR curriculum, batch, epochs, lr, scheduler), and the pass/fail metric + number of eval frames needed for 95 % CI separation at 1e-3 BER.
5. Score the overall Loop-5 trajectory out of 10 and say verdict: `ready / almost / not ready`.

Be brutally honest. If the rubric gate cannot be met with current data/architecture constraints, say so and name what would have to change.

## Proposed Loop-6 execution plan (for your review)

- Run a **dead-feature diagnostic** on the hard pipeline (`|A_active^H r|` after DA-LS at each iter, at 5 SNRs) and confirm c_i ≈ 0 at SNR ≥ 15.
- Implement the **reviewer-recommended new head** (subject to your Phase A verdict).
- Sweep **P ∈ {6, 8, 10}** at N=1024 v=2 τ=10ms; pick best P (by waterfall separation from perf-CSI-BP bound: we want "headroom" to exist).
- 300–400 paired frames × 5 SNR for final eval (95 % Wilson CI adequate for 1e-3 BER on 150k bits).

## Attached files

- `afdm_sp_joint_unrolled/classical_joint_unrolled.py` — main unrolled receiver (1058 lines, incl. all 6 head classes)
- `afdm_sp_joint_unrolled/train_classical_joint_unrolled.py` — training script (671 lines)
- `afdm_sp_joint_unrolled/paired_learned_eval.py` — 400-frame paired eval with hard/soft flag (232 lines)
- `afdm_sp_joint_unrolled/afdm_baselines.py` — NumPy classical `joint_omp_mp_iterative`
