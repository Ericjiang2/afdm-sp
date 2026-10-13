# Loop 8 — Phase A briefing for Oracle GPT-5.4-pro (browser / manual login)

Date: 2026-04-22
Project: AFDM joint OMP+BP channel estimation + detection, learned-receiver line.
Thread goal: pick the **minimum viable learned interface** that actually captures the already-proven BP-joint headroom at high SNR (gate 10/15/20 dB). Prior Oracle session explicitly ruled out C1/C1B1 and B3 in Loop 7.

---

## 1. Where we are (state of the project, condensed)

### What exists

Classical OMP+BP joint channel-estimation + detection pipeline:
1. Least-squares pilot-only LS estimate seed.
2. OMP on the zero-padded pilot block → pick P atoms from the structured Doppler-delay dictionary.
3. Fixed-support BP (or PIC/MMSE) detector on data symbols, conditioned on H_hat.
4. (Optional) 1-2 OMP→BP re-estimation iterations.

A "classical joint unrolled" torch-port of the above exists (`classical_joint_unrolled.py`) that is **bit-exact** to the NumPy reference at N=512/1024 when all learned heads are frozen (`verify_classical_unrolled_matches_numpy.py`). This is the trainable backbone.

### What's been tried (and failed)

Interface families tried on the backbone:
- **S** (soft sparsification weights) — learned sigmoid gates on support picks.
- **B1** (per-iteration scalar schedules — damping, sigma2 gain).
- **B3** (support-only tap corrector: additive correction to on-support amplitudes).
- **C1** (off-support 11-dim-feature residual head, proposed by Oracle in Loop 6).
- **C1B1** (C1 + per-iter refiner combined — Oracle's Loop-7 pick).

At Config A = **N=1024, v=2, P=10 paths, tau=10 ms, rho=0.5** (channel-gen script):
- Classical BP-joint: BER 1.00e-2 @ 20 dB, 5.39e-3 @ 25 dB.
- Perfect-CSI BP (upper bound): **0 / 3 072 000 bits @ both 20 and 25 dB**.
- Perfect-CSI MMSE: 4.29e-4 @ 20 dB, 1.04e-5 @ 25 dB.
- → There is **real, un-capped headroom** between classical and oracle-CSI receivers. The user sees this as an "error floor" in the classical BER curve at 20/25 dB that does not exist with perfect CSI.

All five learned families **failed to capture this headroom** in Loops 4–7:
- S, B1, C1, C1B1 → stat-sig **worse** at SNR=10 and 20 on paired 200f McNemar; null at 15.
- B3 was projected by Oracle to likely fail and Oracle explicitly said "do not run".
- Only narrow positive observed: C1 at P=8 (fallback config, easier channel), SNR=15 only, −0.86 % paired (p=0.0013). Not robust enough to ship as headline.

### Oracle's Loop-7 diagnosis (round-2, gpt-5.4-pro, 2026-04-22)

Ordered most → least likely for the dominant residual error at classical BP-joint P=10:

> A. **Support selection / model-mismatch error** (>> B): OMP picks wrong atoms. Additive off-support corrections cannot repair this — can even inject spurious energy.
>
> B. On-support amplitude/phase error: not the main story.
>
> C. Detector noise-limited: ruled out — PCSI-BP collapses the gap at the same SNRs.

Evidence: large BER headroom vs PCSI, nearly unchanged mean NMSE (−18.7 dB both classical and learned), yet regression from additive head → rare structured *per-frame* channel-est mistakes killing decoding while mean NMSE looks identical.

Oracle's stop rule: "Close Loop-7, ship Loop-6 fallback, write Loop-7 as negative result about headroom-mechanism mismatch."

---

## 2. What we want you to answer in Loop 8

User mandate (verbatim, non-negotiable):

> 要求是提高现在 learned 方法的效果，并且数据得正常。1) BER/MSE 曲线必须符合通信瀑布图，单调非递增、无异常拐点、不高于 PCSI 上界、高 SNR 处 learned 线必须在 classical 线下方。2) 蒙特卡洛帧数合理（考虑置信度）。3) 服务器 GPU 优先。4) gate SNR 10/15/20 优先，学习版本必须在这 3 点（尤其 10–20 dB 高 SNR 段）**稳定下降**，否则评分不通过。5) 打印出每次运行的 N / v / tau / P / batch 等关键参数。6) 先诊断 classical 哪里失配、为什么失配，再用 learned 方法精准消除那个失配，先在诊断子任务上验证确实消除了，再跑完整 SNR 扫描。

### Questions we need answered

**Q1 (main).** Given your own Loop-7 diagnosis (support-selection mistakes dominate), what is the **right family of learned interface**? Please score the candidates below and pick the one you'd bet on:

- **D1. Learned support *proposer*** (learned correlation scorer replacing or augmenting OMP's max-|Φ^H r|). Outputs a top-(M > P) candidate set; classical OMP/BP then picks P from those.
- **D2. Learned support *re-selector*** (per-iteration add-drop proposals, trained to reduce BER via BCE-to-bits / REINFORCE / soft-argmax on residual-gated probs).
- **D3. Learned BP-informed OMP re-scoring** (use BP bit-level posterior entropy to re-weight OMP's column scores, giving OMP a second bite at the apple — "BP→OMP turbo-feedback").
- **D4. Detector-side posterior residual prior** (freeze OMP+BP, wrap a small prior-refinement network around the BP output). We have prior Loop-earlier evidence via oracle-replay that real detector-side headroom exists.
- **D5. Dictionary extension** (add learned fractional-Doppler / basis atoms to the OMP dictionary).
- **D6. End-to-end learned OMP** (learned unrolled OMP with matching-pursuit replaced by a small transformer/GNN over residuals).
- **Other?**

For your pick, specify:
- Identity-at-init design (so training starts at classical BER, no init-time regression).
- Loss target (bit-level BCE on posteriors? NMSE on H? oracle-replay distillation on support indicator? a mix?).
- Training schedule (phases, LR, batch, iters).
- Per-iteration interface point in the unrolled pipeline.
- Validation protocol (how to avoid the 20-frame in-train overfit we hit in Loop 7).

**Q2.** Can we do this on **N=128 or N=256** instead of N=1024, to get ≥10× faster training? Loop-6 tried N=256 v=2 and hit an error floor (k_max_cap=1, κ fractional, dictionary structurally unable to represent true Doppler at both classical and PCSI). If we scale correctly (v, tau, P_paths, k_max_cap, rho, chirp indices), is there **any** small-N config that gives the same qualitative picture (classical BP has real headroom vs PCSI, both receivers waterfall-shaped correctly) — or are we forced to stay at N=1024 for this channel regime? If forced to N=1024, propose the **cheapest** per-epoch setup (batch, eval cadence) that still gives trustworthy gate eval.

**Q3.** Diagnostic sub-tasks to run BEFORE training, to *verify* support-selection is the dominant error per the user's mandate:
- Oracle-support replay: swap OMP support mask with the true channel support, re-run BP → measure BER at gate SNRs. (Expected to give near-PCSI-BP if A is right.)
- Support-Jaccard histogram per frame at gate SNRs: what fraction of frames have ≥1 wrong atom? What is the Jaccard(OMP-support, true-support) distribution?
- Frames-that-kill analysis: which 20 % of frames contribute 80 % of bit errors? Are they low-OMP-confidence / low support-Jaccard / high condition-number frames?
We'll feed these metrics back to you as Round-2 context. Any other diagnostic you want us to compute?

**Q4.** Go/no-go: give your **posterior probability** that the interface you pick in Q1 will give stat-sig BER gain at **all 3 gates** (10/15/20 dB) on paired 500-frame McNemar. If < 30 %, tell us now and we'll re-plan.

**Q5.** Score this plan (pre-execution) on a 1–10 scale. State go/no-go clearly.

---

## 3. Logistics

- Eval protocol: `paired_learned_eval.py --target-errors 150 --min-frames 500 --use-hard --seed 9999` on gate SNRs; McNemar n10/n01 + one-sided binomial p. Torch-ref bit-exact check at each SNR.
- Figures: BER waterfall (log-y) + H-est NMSE (dB), gates overlaid on full SNR sweep 5/10/15/20/25 dB, 4 lines: classical-numpy, torch-ref (sanity), learned, PCSI-BP (upper bound).
- Config print banner at top of every stdout (N, v, tau, P, batch, iter budget, mp type, seed, git SHA).
- Server: RTX 4090, shared with ~5 users. Conda env `AFDM`. GPU currently 3 GB / 24 GB used, 0 % util.
- tmux session prefix `g_loop8_*`.
- Reviewer: you (browser, gpt-5.4-pro). We'll use `oracle --followup <session>` for rounds 2+.

Please be decisive. We are one-shot on this loop — cannot afford another null.
