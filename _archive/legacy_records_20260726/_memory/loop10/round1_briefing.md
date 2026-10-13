# Loop 10 — Round 1 briefing for Oracle (plan + sanity)

Date: 2026-04-22 (night)
Reviewer: Oracle GPT-5.4-pro / `--engine browser --browser-manual-login`
Prior: Loop 9 closed SUCCESS 2026-04-22 (3 rounds, 8/10). See `_memory/loop9/round3_briefing.md` for the closed result.

---

## 1. Why Loop 10 exists

User reviewed Loop 9's waterfall figure (`figures/loop9/loop9_final_ber_mse.png`) and said (verbatim, translated):

> "N=1024, P=10 classical BP-joint BER is far from PCSI; headroom looks large. But the learned curve is visually pasted onto the classical curve. At SNR=20 the learned gain is only ~15 %, the BER lines don't separate, you can't see it in a paper figure. Previous Loop 8 oracle-replay showed **100 % gap closure at SNR=20** is possible — why is the current learned method only capturing 15 %? Is classical BP-joint already near-optimal and learned only buying noise? **That's not a real improvement worth writing.**"

User's explicit Loop-10 rubric (hard):
1. Pivot to **N=1024 P=8 v=2 τ=10 ms** (fewer paths → cleaner-looking classical waterfall, user asked for p8 specifically).
2. BER waterfall **visibly separated** between classical and learned in the high-SNR region (SNR ≥ 20). Low-SNR can be null. No regression.
3. BER shape must be physically normal: monotone-decreasing, strictly below PCSI-BP upper bound, no cliffs, no bumps, no 10×/100× jumps.
4. Adaptive frame count per SNR — early-stop when accumulated classical error bits ≥ 800, floor min-frames so CIs are sane.
5. Banner at stdout-top must print N, v, τ, P to confirm the right config is running.
6. MSE (NMSE_H in dB) waterfall also required and must also be below PCSI-LS and monotone.
7. GPU on remote server for speed.
8. Loop does NOT stop until BER figure visibly separates at high SNR; Oracle can STOP only if structurally impossible, not because of marginal stat significance.

## 2. Loop 9 closed-state you can build on

- **Model**: C2-rel (`CandidateActiveRelationHead` @ `classical_joint_unrolled.py:765`). ~1k params. Features: 7-dim per-candidate + 6-dim per-(candidate, active) pair → pair-MLP 6→16→16 SiLU + max/mean pool over S_omp → 32 dim → scorer 39→16→1.
- **Training**: 30k-frame cache at P=10 (SNRs 10/15/20), BCE + 0.5·rank, 4 epochs, val recall@6 = 0.893 / hit@6 = 0.983.
- **Inference**: scorer bias += 18 post-training → force-topk selects top K_add=4 off-support atoms deterministically; union with S_omp (size P); pilot-only LS → prune back to |S_omp| by |gain| → refit → cluster expand ±k_leak → DA-LS → BP.
- **Loop-9 final (P=10) vs torch-ref** (500f cap, adaptive 2000 err, seed 123456): −0.78 % / −2.40 % / **−15.18 %** / **−7.15 %** at SNR = 10 / 15 / 20 / 25, p ≤ 1e-14 at three of four points, NMSE Δ = −0.64 dB @ SNR=20.
- **Closed status**: Oracle 8/10, accepted as "ranking-informed support augmentation" paper framing.

## 3. Loop 8 evidence the user is citing (headroom at P=10 ≈ 100 % at SNR=20)

Oracle-dictionary support replay (200 f/gate, P=10): oracle-support achieves 0/409 600 bits @ SNR=20, 14 % / 60 % / 100 % gap closed at 10/15/20 dB, NMSE_H −30.7 dB vs classical −18.7 dB. Top 20 % of frames carry 63 % of bit errors. ⇒ support selection IS 100 % of channel-side gap at SNR=20 — the current head only extracts 15 % of this because trained recall@6 on cache is 0.893 but the force-topk adds only K_add=4 under a structural "observability after greedy commit" ceiling (Oracle's own Loop-8 R2 finding).

**Open question**: does the unused ~85 % of gap need (a) a different mechanism (beyond post-LS residual features), or (b) just more aggressive support replacement (higher K_add, swap-not-union, multi-round)?

## 4. What we plan for Loop 10 (pick / veto / modify)

### Plan A — Ship P=8 retrain of exactly the closed C2-rel recipe, no method change
- Re-cache 30k frames at P=8 SNRs {10, 15, 20} via `loop9_cache_features.py --p-paths 8 --n-10 12000 --n-15 12000 --n-20 12000`.
- Retrain with same `loop9_train_c2rel.py` config.
- Paired eval P=8 SNRs {10, 15, 20, 25, 30} with `--use-hard`, `--target-errors 800` (per user rubric — tighter than Loop 9's 2000), `--min-frames 50`.
- Cost: cache ~2-3 h, train ~10 min, eval ~1 h GPU.
- Risk: P=8 shrinks classical-to-PCSI headroom (fewer paths, less support-uncertainty), likely halves the relative gain. **We may produce a Loop-9 style 5-8 % win at SNR=20, which still won't visibly separate the curves.**

### Plan B — Plan A **+ K_add scaling (force-topk with per-SNR K_add)**
- Keep trained model; at inference raise K_add from 4 → {6, 8}. Classical prune-back-to-P refit will evict most additions on easy frames; only the ones that beat the weakest OMP atom survive.
- No retraining, 5 extra minutes. Gives us P=8 × {K=4, 6, 8} × 4 SNRs in one eval run.
- Risk: too-high K_add pushes too many low-quality candidates through; prune step might evict correct OMP atoms.

### Plan C — Plan A + sequential add-and-test (your Round-3 safety valve from Loop 9)
- Per scored candidate in descending score order: add; re-run pilot-LS on union; keep only if (i) residual reduces by ≥ ε_r *and* its refit-gain |α_j| exceeds the weakest OMP atom's |α| by margin η, or (ii) it survives top-P prune-by-|gain|. Stop when K_accepted = K_cap or all candidates rejected.
- One-line change in `classical_joint_unrolled.py` after `select_additions`. No retrain.
- Risk: sequential loop inside classical path adds per-frame LS cost (small, `|S| ≈ 40`).

### Plan D — Plan A + richer head (bigger MLP + extra features)
- Add features: `(|pre-LS pilot MF|_j − max over active)`, per-candidate `Σ_s kern(Δl, Δk)·|α_s|·coh_{js}`, and the `log(σ²)` is already in. Grow scorer hidden 16 → 32.
- Re-train from scratch on P=8 cache. +5k params (still tiny).
- Risk: longer train, may overfit with only 30k frames at P=8.

### Plan E — Recast as support-replacement (not augmentation) — multi-round
- Run classical OMP → LS. Then learned head proposes top-K swap candidates, swap each with weakest active atom tentatively; accept swap iff residual strictly decreases. Iterate 1-2 rounds.
- Structurally new; requires re-training with different supervision target (label = oracle support minus OMP support).
- Risk: 2-3× more code, may not finish in 4 rounds of the loop.

## 5. Questions for you

**Q1.** Is P=8 scientifically defensible as the headline config? Concern: reviewer may ask "why not stick with the harder P=10 where the method's ceiling is 100 % gap closure". Defend or demand P=10 stay in the paper as main.

**Q2.** Rank A / B / C / D / E for expected visible-separation-at-high-SNR at P=8 on a single round (budget = one ≤6 h GPU cycle end-to-end). What is the posterior that a pick lands us with ≥ 30 % relative BER reduction at SNR=20 AND visibly below-classical curve at SNR ≥ 20 on 500-frame paired eval?

**Q3.** If you believe (a) no simple plan beats ~10-15 % at P=8, call it out; we should then not drop P=10 from the paper.

**Q4.** Propose a *combined* plan of at most TWO of {A-E} for Loop-10 Round 2. Explicit commands (CLI flags) so we can execute without back-and-forth.

**Q5.** Sanity-check the adaptive-frame protocol: `--target-errors 800 --min-frames 50`, max 500. With P=8 classical BER roughly halving from Loop-9's numbers, SNR=25/30 may need the full 500 frames; is that enough for McNemar p < 0.01 at the expected effect size? If not, recommend the right `(target-errors, min-frames, max-frames)` triple.

Be terse. ≤ 60 lines response.

## 6. Attached files

- This briefing: `_memory/loop10/round1_briefing.md`
- Loop 9 closed briefing: `_memory/loop9/round3_briefing.md` (has final C2-rel result table + method recap).
- Head: `afdm_sp_joint_unrolled/classical_joint_unrolled.py` (class `CandidateActiveRelationHead` at line 765, call site ≈ line 1100).
- Paired eval: `afdm_sp_joint_unrolled/paired_learned_eval.py` (adaptive early-stop, hard-decision flag, McNemar).
- Cache generator: `afdm_sp_joint_unrolled/loop9_cache_features.py` (supports `--p-paths 8`).
- Trainer: `afdm_sp_joint_unrolled/loop9_train_c2rel.py`.
- Loop 9 waterfall: `figures/loop9/loop9_final_ber_mse.png` (the figure the user says "lines don't separate").
