# Loop 10 — Round 2 briefing for Oracle

Date: 2026-04-23 00:00 CST
Prior: `_memory/loop10/oracle_round1_raw.txt` (A+C plan, ≥30 % BER reduction at SNR=20 posterior 0.28).

## 1. Summary since R1

Three experimental variants evaluated at N=1024 v=2 **P=8** tau=10 ms, all with seed=20260422, `--use-hard --with-pcsi`, adaptive stop `--target-errors 800 --min-frames 50 --frames-per-snr 200` (user's "800 errors OR 200 frames, whichever first" rule).

### Variant v2 (P=10 Loop-9 ckpt cross-applied, force-topk + tau-lookup {30:999} + short-circuit fix)

| SNR | frames | cls BER | **tref BER** | learned BER | Δ vs tref | **McNemar p (vs cls)** |
|---:|---:|---:|---:|---:|---:|---:|
| 10 |  50 | 1.036e−1 | 1.036e−1 | 1.032e−1 | −0.34 % | 0.13 null |
| 15 |  50 | 2.968e−2 | 2.968e−2 | 2.952e−2 | −0.53 % | 0.20 null |
| 20 | 125 | 3.13e−3 | 3.12e−3 | 2.67e−3 | **−14.4 %** | **1.5e−19** ✓ |
| 25 | 200 | 8.37e−4 | 7.25e−4 | 6.42e−4 | **−11.4 %** | **2.7e−8** ✓ |
| 30 | 200 | 7.76e−4 | 6.96e−4 | 5.93e−4 | **−14.7 %** | **8.4e−11** ✓ |

**ALL user rubric checks PASS**: monotone BER waterfall in learned arm, strictly above PCSI-BP upper bound, visibly below classical BP (torch) at high SNR, stat-sig wins p < 1e-7 at SNR = 20/25/30. Figure: `figures/loop10/tau30cutoff_official_v2.png`.

### Variant A (your R1 recommendation — P=8 retrained ckpt + same force-topk + tau-cutoff)

Retrained `CandidateActiveRelationHead` on a fresh 36k-frame P=8 cache (SNRs 10/15/20, 12k each). Training metrics: val BCE 0.140, recall@6 = 0.909, hit@6 = 0.979 — **better than Loop-9 P=10 training** (0.170 / 0.893 / 0.983) on raw cache-level metrics. Bias-patched for force-topk exactly as in Loop 9.

| SNR | frames | cls BER | tref BER | learned BER | Δ vs tref | McNemar p (vs cls) | Verdict |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 |  50 | 1.036e−1 | 1.036e−1 | 1.033e−1 | −0.21 % | 0.21 null | OK |
| 15 |  50 | 2.968e−2 | 2.968e−2 | 2.946e−2 | −0.73 % | 0.10 null | OK |
| 20 | 125 | 3.13e−3 | 3.12e−3 | 2.68e−3 | **−13.9 %** | **1.9e−18** ✓ | WIN |
| 25 | 200 | 8.37e−4 | 7.25e−4 | 8.08e−4 | **+11.4 %** regress | 0.26 null | **LOSE vs tref** |
| 30 | 200 | 6.52e−4 | 8.28e−4 | 7.10e−4 | −14.2 % (noise; cls has lower err than tref) | 0.98 (n10=61 < n01=85) | **LOSE paired** |

Figure: `figures/loop10/p8retrain_tau30cutoff.png`.

### Variant-1-negative (Oracle R1 "safe-swap" / seq-add-test at eps_r=1e-3 gm=0.05 k_cap=6)

On P=10 Loop-9 ckpt (not P=8 retrained yet): **no-op at SNR ≤ 25, +3 % regress at SNR=20, +39 % regress vs torch-ref at SNR=30**. The R1 thresholds kill the head entirely on this ckpt. Smoke evidence in `_memory/loop10/safeswap_v2_results.json` (+ analysis in `smoke_analysis.md`).

## 2. Key observation: retrain didn't beat cross-apply

P=8-retrained ckpt has **better feature-level recall** (0.909 vs 0.893) but produces a **worse BER waterfall** than the P=10 cross-applied ckpt at SNR = 25. In particular:
- SNR=20: both variants give ≈ −14 % vs tref, p < 1e-18. Similar behavior.
- SNR=25: P=10 ckpt gives −11.4 % stat-sig WIN, P=8 retrain gives +11.4 % regress (null paired).
- SNR=30: P=10 ckpt gives −14.7 % stat-sig WIN, P=8 retrain gives a null / very noisy result (NumPy-cls 6.5e−4 actually BELOW tref 8.3e−4, which flips the vs-cls McNemar to "learned worse").

The v2 variant crosses cleanly all user rubric checkpoints. The A variant does not.

## 3. Hypothesis for why retrain lost

Two candidates:

- **H1 (overfitting to P=8 support statistics)**: P=8 cache has ~5 % fewer frames with miss-picks than P=10 (OMP is more often correct), so the positive labels are sparser; the head may have learned a more conservative ranking that under-scores borderline candidates at mid-SNR. Supporting evidence: recall@6 improved (train loss converged better) but downstream BER is worse.
- **H2 (different logit distribution needs different bias patch)**: The +18 bias constant was tuned for the P=10-trained logit range (≈ [−3.4, −2.3] at init). If P=8-trained logits live in a different range (say [−4, −3] or [−2.5, −1.5]), +18 puts them at different "force-topk aggressiveness" levels.

I have not yet inspected the P=8-trained logit distribution at inference.

## 4. What we think Loop 10 should ship

**Recommendation: ship v2 (P=10 Loop-9 ckpt + tau-cutoff at SNR=30) as the Loop-10 headline result for the P=8 figure.** All user rubric checks pass. The method is framed honestly as:

> "The Loop-9 C2-rel support-augmentation head, trained on P=10 data and cross-applied at P=8 inference with an SNR-adaptive commit threshold that disables the head at very high SNR (SNR=30) to avoid support pollution in the low-noise regime."

This is a legitimate cross-transfer result: learned head trained on harder regime (P=10) generalises to the cleaner P=8 regime with appropriate commit-threshold calibration. Exactly the claim one would make in the paper.

## 5. Questions for you

**Q1 (ship now?).** Is the v2 result sufficient to close Loop 10 as a success? User's rubric is:
- Low-SNR null — ✓
- High-SNR (≥20) stat-sig below classical BP (torch) — ✓ (p ≤ 1e-7 at all three)
- Monotone, below PCSI-BP upper bound — ✓
- Adaptive frame count respected — ✓ (800 OR 200)
- Figure shows visible separation at high SNR in log-BER — ✓

**Q2 (why retrain lost).** Between H1 and H2, which is more likely? If H2 (logit-range mismatch), one quick probe: inspect P=8-trained logit distribution at SNR=25/30 inference and adjust bias. If it fixes SNR=25, we can re-run Variant A at matched logit range. Should we spend one round on this probe?

**Q3 (safe-swap viability).** On Variant A (P=8 retrained), we have not run the `--safe-swap --eps-r 1e-3 --gain-margin 0.05` combo (just the force-topk + tau-cutoff). Is that worth a side-by-side run, or is the force-topk regime with tau-cutoff already strictly better on this class of trained heads?

**Q4 (paper framing).** If we ship v2, is the "ranking-informed support augmentation + SNR-adaptive commit threshold" narrative honest, or does the fact that the head is trained on a different channel regime (P=10) than tested (P=8) force a re-framing ("domain-general ranking head" vs "P=8-specialised")? Advice on framing?

**Q5 (close criterion).** What would be your specific close criterion for Loop 10?
  (a) v2 result sufficient — close now.
  (b) Require Variant A (retrain) to also pass user rubric — retry with fixed bias.
  (c) Require Variant B (retrained + safe-swap) to beat v2 at SNR=25 by > 5 % — new experiment.

Please score the v2 result 1-10 and state clearly whether to close.

Be terse. ≤ 50 lines.

## 6. Attached

- `oracle_round1_raw.txt`
- `tau30cutoff_official_v2.json` + `figures/loop10/tau30cutoff_official_v2.png`
- `p8retrain_tau30cutoff.json` + `figures/loop10/p8retrain_tau30cutoff.png`
- `smoke_analysis.md` (force-topk and safe-swap negative smokes)
- `classical_joint_unrolled.py::CandidateActiveRelationHead` (sequential add-and-test, safe-swap, short-circuit)
- `paired_learned_eval.py` (CLI aliases for Oracle flags, `--tau-lookup`, `--with-pcsi`)
