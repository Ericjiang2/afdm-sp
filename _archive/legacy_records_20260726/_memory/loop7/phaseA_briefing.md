# Loop 7 — Phase-A plan review briefing for Oracle GPT-5.4-pro (browser)

You are acting as a **senior wireless/ML reviewer at NeurIPS / ICML / IEEE TWC** level, reviewing the **plan** for Loop 7 before we burn GPU on it.

## Rubric (enforce ranking; #1 is a hard gate)

1. **[HARD GATE]** Learned **joint OMP+BP** receiver must beat the **classical BP-torch joint** baseline with **stable BER improvement at high-SNR gates (SNR = 10, 15, 20 dB)**. "Stable" means: no regression, paired-McNemar not-worse at each gate, and at least one gate stat-sig better.
2. **[HARD GATE]** BER + MSE waterfall curves must be "shape-correct":
   - Monotone non-increasing as SNR increases (no cliff up/down > 10× between adjacent SNRs).
   - Every method's BER strictly ≥ Perfect-CSI BP upper bound (or tied within CI).
   - No sudden kink (e.g., a single SNR point dropping to 1e-5 when neighbours are 1e-2).
3. Monte-Carlo frame count per SNR must give reasonable Wilson 95% CI (neither too few → overlapping CIs at every SNR, nor too many → >8 GPU-hours per config). **User-mandated rule: adaptive early-stop — accumulate 150 bit errors and stop, with a frame cap (≤ 1500 per SNR) to bound runtime.**
4. Config (N, v_mean, P_paths, tau_spread) must be **printed at the top of every script invocation** so I can verify from logs.
5. Preferred: smaller N (128 or 256) if it still gives reviewer-safe results — faster iteration.
6. If nothing beats Loop-6 N=1024 v=2 P=8 C1 fallback, we ship that as "honest close" (final report's negative-result section).

## What we already know (from Loop 5 + 6, completed today)

### Loop 6 fallback eval — **v=2 N=1024 P=8 tau=10ms, 500 frames, paired McNemar adaptive**

| SNR | classical BER | learned-C1 BER | rel Δ | McNemar (n10, n01) | p one-sided | verdict |
|---|---|---|---|---|---|---|
| 5 | 1.901e-01 | 1.903e-01 | +0.07% | (114, 122) | 0.721 | null |
| 10 | 1.035e-01 | 1.033e-01 | −0.17% | (132, 121) | 0.265 | null |
| **15** | 2.848e-02 | 2.824e-02 | **−0.86%** | **(19, 4)** | **0.0013** | **learned better (sig)** |
| 20 | 3.255e-03 | 3.353e-03 | +3.00% | (23, 29) | 0.834 | null |
| 25 | 2.672e-03 | 2.903e-03 | +8.63% | (28, 45) | 0.983 | null |

NMSE at SNR=25: −22.30 dB (classical) vs −22.25 dB (learned). **Waterfall PASS** (monotone, above PCSI-BP, no cliffs). Current holder of "least bad" slot.

### Why high-SNR headroom is empty (Loop 5/6 finding)

At v=2 N=1024 P=8, classical BP-joint BER at SNR=20 (3.26e-3) is within ~5% of Perfect-CSI BP. There is no room for a learned head to improve without overfitting. C1 off-support head (Loop 6) correctly preserves identity-at-init (bit-exact) and improves SNR=15 slightly, but **can't escape the perf-CSI floor at gate SNRs 20/25**.

### The canonical comparison we must do

- **Classical**: `classical_joint_bp_torch_probe.py` — OMP support + BP-torch MP detector (GPU, fast); bit-exact to NumPy `joint_omp_mp_iterative` baseline (verified Loop 5).
- **Learned**: `train_classical_joint_unrolled.py` → `paired_learned_eval.py` — same forward pass with a learned head inserted.
- **Upper bound**: Perfect-CSI BP (`outputs_loop6_pcsi_p8/`).
- **Waterfall**: all three on same 500-frame seed set, SNR grid.

## Three candidate configs for Loop 7 (please rank + give expected headroom)

All share: tau_spread=10ms, **adaptive stop at 150 bit errors**, min=50 frames, cap=1500 frames.

### Config A — **N=1024 v=2 P=10** (NEVER TRIED)
- Same geometry as Loop-6 fallback except P_paths: 8 → 10 (25% more paths).
- Hypothesis: more paths → harder OMP estimation → classical BP-joint drifts further from perf-CSI → real headroom opens at SNR = 15/20/25.
- Cost: train C1+B1 head phase2=400, ~3h on RTX 4090; eval ~30 min.

### Config B — **N=256 v=4 P=5 tau=3ms** (kappa-clean, small)
- Kappa-clean setup per CLAUDE.md: (N=256, v=4).
- Cost: ~30 min train, ~10 min eval. Enables 3 seeds + 2 variants in same budget as Config A × 1.
- Risk: small N may have worse waterfall shape (fewer resolution bins, aliasing).

### Config C — **N=128 v=8 P=5 tau=3ms** (kappa-clean, tiny)
- Kappa-clean (N=128, v=8). Smallest.
- Cost: ~10 min train, ~5 min eval. 5+ variants possible.
- Risk: high — pilot rho=0.5 leaves only 64 data subcarriers; BER floor likely too low-resolution for gate SNRs.

## Three candidate methods

### Method 1 — **C1+B1 combined** (C1 off-support + B1 signal prior)
- C1 from Loop 6 (architecturally sound, identity-at-init) + B1 cross-iter signal head (gives per-iter LLR refinement).
- Hypothesis: C1 alone was slightly under-capacity; adding B1 provides cross-iter prior that C1's single-shot correction cannot.

### Method 2 — **B2 best-iter-pretrained detector ensemble** (Oracle R3 secondary)
- Train per-iter candidate pool; learn a per-frame selector over iters (best-iter oracle replay).
- Detector-side, not channel-side. Independent error pool from C1.
- Cost: requires best-iter pretrain (+2h) before main train.

### Method 3 — **Local fractional-Doppler stencil head** (Oracle R3 tertiary)
- Predict continuous Doppler offset + amplitude on same delay row (complementary to C1's off-support).
- Expected biggest headroom under v=2.5 (fractional kappa). For v=2 (integer) should be ≈ null — do not use as primary.

## Concrete plan I want your review on

1. **Classical baselines** (Phase B1): run `classical_joint_bp_torch_probe.py` + `outputs_loop6_pcsi_*` probe on chosen config. Verify waterfall: monotone, below perf-CSI; if fail → stop, fix config before training.
2. **Phase B2**: train one learned variant on chosen config (Method 1 or 2 per your recommendation).
3. **Phase B3**: paired McNemar adaptive eval on 500 frames (target=150 classical errors, min=30, cap=1500).
4. **Phase B4**: plot BER + MSE waterfalls (3 panels: BER, MSE H-est NMSE, Wilson CI bars); audit per rule (1) + (2) above.
5. **Phase B5**: if fail high-SNR gates, either (a) iterate on hyperparameters (lr-heads, lam-sym, phase2-iters) once, or (b) declare Loop-6 fallback.

## Questions for your review

1. **Config pick**: A, B, or C? Or hybrid (run B for fast screen, then A for publication-grade if B looks promising)?
2. **Method pick**: given Loop-6 C1 failure, is Method 1 (C1+B1) still the highest-yield minimum fix, or do you prefer Method 2 (B2 detector ensemble)?
3. **MC budget**: 500 frames paired-adaptive is what Loop 6 used. Should we bump to 1000 for Loop 7 to tighten CIs at SNR=20/25 where BER ~ 3e-3 gives only ~15 classical errors at 500 frames? (Wilson CI at 3e-3, 500f × 4bits/sym × 512syms = 1.024M bits ≈ 3000 errors, so CIs are actually tight — but paired McNemar only uses 10/01 discordant pairs which are sparse. Please sanity-check.)
4. **Go / no-go**: if your predicted posterior probability of Loop-7 beating Loop-6 fallback at all three gates (SNR 10/15/20) is < 30%, tell me to ship Loop-6 fallback + write negative-result paper instead of running Loop 7.

Please respond with:
- Score 1-10 for this plan
- Concrete picks for Config, Method, MC budget
- Predicted posterior P(Loop-7 beats fallback at all 3 gates)
- Anything I'm missing (new head family, new ablation)
- Verdict: "run this plan" / "revise and re-ask" / "skip to negative-result writeup"
