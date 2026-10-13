# Loop 11 — Round 1 briefing for Oracle GPT-5.4-pro (browser)

Date: 2026-04-23 ~01:00 CST
Reviewer: Oracle GPT-5.4-pro via `oracle --engine browser`
Repo: `afdm-channel-estimation` branch `codex/afdm_dnn_ai`
Pipeline: AFDM channel estimation + joint detection (classical OMP→cluster expand→DA-LS→BP, with C2-rel learned support-repair head).

---

## 1. Loop-by-loop history (compact)

- **Loop 6**: C1 off-support head; only narrow-positive at SNR=15 (−0.86 %, p=0.0013) for P=8 v=2 N=1024. P=10/v=2.5 regimes regress.
- **Loop 7**: P=10 has huge oracle-replay headroom but C1/C1B1 stat-sig regress at SNR=10/20. Oracle: residual error is **support-selection / model-mismatch**; additive off-support corrector cannot repair wrong OMP picks.
- **Loop 8**: Quantitative diagnostic confirmed:
  - At SNR=20 (P=10): oracle-dictionary-support replay → **0/409 600 bit errors** (matches PCSI-BP exactly). 100 % of channel-side BER gap is support-selection; mean NMSE gap 12 dB.
  - 63 % of bit errors at SNR=20 come from worst 20 % of frames.
  - Top-K_add=6 recall = **3.5 %** (need ≥ 90 %) via residual-MF scoring proxy.
  - D3-lite (BP-informed 2nd-pass) DD-score recall is 4–20× WORSE than residual-MF — BP soft means biased toward wrong OMP picks.
  - Conclusion: missed atoms are **structurally invisible** to single-atom MF on either pilot or data residual.
- **Loop 9** (P=10 v=2): C2-rel "candidate-active relation head" trained at K_add=6, val recall@6=0.909. Final 500f paired McNemar:
  - SNR=15: −2.40 %, p=7.5e−15 ✓
  - SNR=20: −15.18 %, p=1.4e−36 ✓ NMSE −0.64 dB
  - SNR=25: −7.15 %, p=2.5e−16 ✓
  - All stat-sig BER win, waterfall monotone. Oracle 8/10 close. **Paper framing: "ranking-informed support augmentation" (deterministic top-K + classical refit/prune).**
- **Loop 10** (P=8 pivot, user wanted visible figure):
  - **v2 = P=10 ckpt cross-applied at P=8 + per-SNR `tau-lookup {30:999}` + force-topk + short-circuit** ⇒ headline:

| SNR | classical | torch-ref | learned | Δ vs tref | McNemar p | NMSE cls/lrn (dB) |
|---:|---:|---:|---:|---:|---:|---:|
| 10 |1.04e-1 |1.04e-1 |1.03e-1 | −0.34 % |0.13 null | −12.14 / −12.17 |
| 15 |2.97e-2 |2.97e-2 |2.95e-2 | −0.53 % |0.20 null | −16.64 / −16.77 |
| 20 |3.13e-3 |3.12e-3 |2.67e-3 | **−14.4 %** | **1.5e−19** | −22.08 / −22.38 |
| 25 |8.37e-4 |7.25e-4 |6.42e-4 | **−11.4 %** | **2.7e−8** | −23.70 / −24.04 |
| 30 |7.76e-4 |6.96e-4 |5.93e-4 | **−14.7 %** | **8.4e−11** | −24.17 / −24.37 |

- Variant A (P=8 retrain) **lost** at SNR=25/30 (NULL and +9 % regress). v2 stays headline.
- F1 alone (no-prune) **worse** than v2 (support pollution).

## 2. Figure-rejection that triggered Loop 11

User examined `figures/loop10/tau30cutoff_official_v2.png`: **stat-sig but NOT visibly separated**. The −14 % rel BER reduction at SNR=20 is roughly a **0.3–0.5 dB SNR-shift** in the log-waterfall. User's communications-paper standard is **≥ 1–2 dB visible separation at high SNR**, ideally with the learned line clearly below classical at SNR=20/25/30 in print.

Loop 8 diagnostic shows the **oracle ceiling is 100 % of the channel-side gap → near-PCSI**. So the headroom is there; the question is why the learned method captures only ~14 % of it.

## 3. User Loop-11 rubric (verbatim, hard)

> 1. **主线**: learned 方法 BER 视觉上 1–2 dB 增益（高 SNR 学下来到 classical 之下，看得见）。
> 2. **发散性分析**: 为什么 oracle replay 的 BER 能贴近 perfect CSI，但 learned 方法学不到这中间这么大的信道估计失配 gap？最好让 oracle gpt-5.4-pro 发散性想想还有没有可能的解释 / 路径。
> 3. **加速**: N=1024 在 4090 上训练/eval 都偏慢，是否有安全的并行 / 优化 (CUDA streams, batched eval, AMP, bucketized BP, etc.)。
> 4. **数据正确性 hard guard**:
>    - BER & MSE 曲线必须给。
>    - BER 高 SNR 不能高过低 SNR、不能高过 PCSI 上界、不能突然几十/几百倍跌或翘 → 得到结果先自评数据是否正常。
>    - 看线形（不光看点）：learned 的 BER 线高 SNR 在 classical 之下、低 SNR 差不多就行；瀑布形态正常。
>    - MC 帧数适度（不太小不太大），考虑置信度。
>    - **自适应早停**: 训练 patience 早停；eval 累计 200–500 错 bits 提前终止 / SNR；最大化时间利用率。
>    - 优先 GPU 跑。
> 5. **Reviewer 严格用 `oracle --engine browser`**。

## 4. Existing Loop-11 plan from Oracle R2-followup (Loop 10 close)

> **Target**: ≥ 1 dB visible shift at SNR=20/25 (BER ratio ≤ 0.75 at SNR=20, ≤ 0.70 at SNR=25). 2 dB at P=8 acknowledged as unlikely.
>
> R1 fast screen (1 day budget) at SNR={20, 25}, ~100f, 800-err adaptive stop:
> 1. F1 — no-prune (smoke: null → needs F2)
> 2. F2 — multi-round refinement `--refine-rounds 2`: rerun C2-rel on DA-LS residual at iter 1, update support, redo DA-LS. NEW CODE.
> 3. F1 + F2 together
> 4. P=10 backup of F1+F2 as parallel sanity
>
> Hard stop rule: if best P=8 < 40 % BER reduction at SNR=20 AND 25 after R2 → pivot to harder regime (tau=15 ms / v=3) or F3 learned swap (12–20 h).
>
> Not this loop: F4 (BP-differentiable BER fine-tune, 20 h+, unstable). F5 (LISTA / learned OMP, major redesign).

## 5. Open architectural ideas for divergent thinking (non-exhaustive, not yet tried)

The user explicitly asks Oracle to brainstorm DIVERGENTLY. Below are options I've sketched — please confirm/rank/add new ones:

A. **Multi-atom joint scorer** (transformer/GNN over ALL candidate atoms in the dictionary, not single-atom MF). Cost: medium (1–2 day implementation, multi-iter training).
B. **Learn the OMP step directly** (LISTA-style: replace argmax + LS by a learned soft selection unrolled over K_paths iterations). Cost: high.
C. **Multi-round refinement + active-set update** (= F2 from existing plan): re-trigger C2-rel on DA-LS residual at iter 1+, update support iteratively. Low-medium cost.
D. **Joint support repair + tap correction** (combine C2-rel for support + B3-tap-corrector for active gains). Loop 9 already showed B3 alone fails; combo TBD.
E. **Detector-side residual prior** (`vx_recal_v1` line — independent of channel-side; project notes already say "real headroom in oracle-replay" on detector side). Decouple from channel-side support fix.
F. **Train the head with a BP-aware loss, not BCE** (target = BP-output BER reduction conditioned on adding atom j; uses BP forward in training). Cost: high (BP differentiability).
G. **Replace classical OMP with a few-iter learned channel estimator** that outputs a posterior over {δ, k, gain} per path; downstream BP unchanged. Major.
H. **Oracle replay BER → 0 mystery diverged**: maybe the oracle "replay" we measure is not the right asymptote because oracle uses *exact* on-grid atoms while real channel is fractional / off-grid in some realizations. If that's the case, even a perfect support-selector cannot match the oracle ceiling because the oracle cheats by knowing the true (`l_exp, k_exp, chan_coef_exp`). Could the "100 % gap closed" finding be partially an artifact of how oracle support is defined?
I. **Heavy-tail frame mass concentrate**: Loop 8 found 63 % of errors come from 20 % of frames at SNR=20. A frame-level "this realization is hard" detector → conservative fallback (e.g., extra OMP restarts) might close most of the gap without changing the per-atom scorer.
J. **Use posterior soft means more aggressively**: re-feed BP posteriors back into a 2nd OMP pass with **uncertainty-weighted** dictionary masking (downweight atoms aliasing high-confidence symbols). Loop-8 D3-lite already failed this lighter version; could a heavier multi-iter version work?
K. **Curriculum + better data augmentation**: Loop-9 trained on K_add=6 with 30k frames at fixed SNRs. Maybe more SNR coverage / harder corner cases (low-K_add ground truth missed) would help.

## 6. 4090 speedup needs (concrete numbers if possible)

Current eval: ~30 frames / minute / SNR at N=1024 P=8 (BP joint torch). Training: 4 epochs × 30k feature samples = ~25 min (already cached). Bottlenecks suspected:
- BP iterations (40 inner iters × 5 outer iters × per-frame loop, no batching).
- DA-LS `linalg.solve` on small matrices (dispatch overhead).
- `construct_sensing_matrix_torch` on every iter, never cached.
- OMP loop K_paths iterations of `argmax + lstsq`.

Asks:
- Safe ways to **batch frames inside one SNR** (paired-eval currently 1 frame at a time to keep seed-matched). Could we run B frames in parallel under the same RNG sequence?
- **Mixed precision (fp16 / bf16)** safe regions vs unsafe (BP needs fp32).
- **CUDA streams** to overlap channel-est compute with detector compute across frames.
- **Caching** Phi columns per-channel realization (channel changes per frame, so probably no help — confirm).
- Anything else 4090-specific.

## 7. Adaptive early-stop already in place

- Eval: `--target-errors N` adaptive stop per SNR (current: 800 cls err bits / SNR, capped at 200 frames). Confirm if 200–500 cap is reasonable for Loop 11.
- Training: best-checkpoint by val BCE; no patience-based early stop yet. **Need to add patience early-stop (e.g., 5 epochs no val improve).**

## 8. Concrete asks from this Round 1

1. **Score the existing R1 plan (F1 / F2 / F1+F2 / P=10 backup) 1–10 for likelihood of producing visible 1–2 dB separation at SNR=20/25.** If posterior < 30 %, propose better.
2. **Divergent hypothesis brainstorm**: rank options A–K (and add new ones) by (mechanistic plausibility × implementation cost × visible 1–2 dB gain probability). Pick the **top 1–2 to implement this loop**.
3. **The "oracle replay → near-PCSI but learned can't capture" question**: brainstorm 3–5 distinct mechanistic hypotheses (not just support-selection), and for each, propose a CHEAP probe (≤ 1 hour compute) that could falsify or confirm.
4. **4090 speedups**: 3–5 safe interventions ranked by speedup × code-effort × correctness risk. Highlight which need careful seed-management to preserve paired-McNemar reproducibility.
5. **Adaptive early-stop**: confirm 200–500 err bits cap is OK; suggest training patience number (5? 10?); suggest min-frames floor.
6. **Hard stop rule**: when should we accept "1–2 dB at P=8 is structurally impossible" and pivot to harder-regime story (tau=15 ms, v=3) for figure?
7. **Anything I'm missing**: brutal honesty on whether this loop is going to produce a visible-separation paper figure or whether we should pivot earlier.

Reply format: numeric scores, ranked lists, executable CLI / pseudocode where possible. xhigh reasoning effort.
