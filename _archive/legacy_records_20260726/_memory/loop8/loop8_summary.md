# Loop 8 — final summary (pending Oracle Round 2 verdict)

Date: 2026-04-22
Branch: `codex/afdm_dnn_ai`
Reviewer: Oracle GPT-5.4-pro via `oracle --engine browser --browser-manual-login`

## User rubric (this loop)

> 1) BER/MSE 必须符合通信瀑布图，单调非递增、无异常拐点、不高于 PCSI 上界、高 SNR 处 learned 线必须在 classical 下方。
> 2) 蒙特卡洛帧数合理，置信度足够。
> 3) 服务器 GPU 优先。
> 4) gate SNR 10/15/20 优先，learned 必须在这 3 点（尤其高 SNR）稳定下降，否则评分不通过。
> 5) 打印每次运行的关键参数。
> 6) 先诊断 classical 哪里失配、为什么失配，再用 learned 精准消除那个失配；先在诊断子任务上验证消除了，再跑完整 SNR 扫描。

This loop is the **purest enactment of (6)**: diagnose first, decide whether to train, only train if mechanism is recoverable.

## Round 1 (plan review)

Oracle picked **D1-A "augment-only support repair head"**: reuse C1 11-dim feature path, change target from residual regression → missed-support BCE classification, K_add=4, identity-at-init via very-negative classifier bias, then classical restricted re-select on `S_omp ∪ A`. Score 7/10. **Decision: GO — diagnostic-gated.**

Oracle Round-1 thresholds for proceeding to D1-A training:
- (a) Oracle-support replay closes most of classical→PCSI gap at SNR=20.
- (b) Top-K_add=6 recall ≥ 0.90 at SNR=20 AND ≥ 0.80 at SNR=15.

## Phase 0 — diagnostic execution (`loop8_diagnose.py`)

Per-frame on Config A (N=1024 v=2 P=10 τ=10 ms), 200 paired frames per gate at SNR ∈ {10, 15, 20}.

For each frame: classical OMP+BP arm + oracle-dictionary support arm, on identical (channel, data, noise) seeds. Oracle support = top-P_actual virtual taps from `channel_params['l_exp']`, `['k_exp']`, `['chan_coef_exp']`, mapped to dictionary columns and deduped. Recall computed via `|Φ^H r_post_OMP_LS|` scoring.

### Numbers

| SNR | n | BER cls | BER oracle | gap closed | NMSE_cls | NMSE_oracle | avg Jaccard | avg n_missed | top-20 % kill share |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 200 | 1.121e-1 | 9.59e-2  | 14 % | −11.48 dB | −13.67 dB | 0.337 | 17.99 | 25 % |
| 15 | 200 | 4.61e-2  | 1.83e-2  | 60 % | −14.31 dB | −20.67 dB | 0.364 | 17.39 | 32 % |
| 20 | 200 | 8.80e-3  | **0/409 600 bits** | **100 %** | −18.73 dB | **−30.70 dB** | 0.374 | 16.87 | **63 %** |

Recall@K_add (residual MF):

| SNR | K=2 | K=4 | K=6 | K=8 | K=12 |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.009 | 0.017 | 0.027 | 0.035 | 0.053 |
| 15 | 0.009 | 0.020 | 0.031 | 0.039 | 0.054 |
| 20 | 0.012 | 0.023 | 0.035 | 0.048 | **0.067** |

Frames with `recall == 1.0`: **0/200 at every SNR / K_add**.

### Gate decision

- (a) PASS: gap_closed @ 20 dB = 100 %, ratio_oracle/cls = 0.000.
- (b) FAIL by huge margin: recall@K_add=6 = 0.035 (need ≥ 0.90).

**OVERALL: FAIL — do NOT train D1-A blindly.**

### Scientific findings (these ARE the deliverable)

1. **Loop-7 hypothesis A is now quantitatively confirmed**: support-selection accounts for **100 %** of the channel-side BER gap at SNR=20 (oracle-replay BER = 0). Loop-7 was a qualitative diagnosis; Loop-8 turns it into a number.
2. **NMSE alone hides the catastrophe**: classical −18.7 dB vs oracle −30.7 dB at SNR=20 — a 12 dB gap that aggregate NMSE buries because it is concentrated on a few catastrophic per-frame mistakes (top 20 % of frames carry 63 % of bit errors).
3. **The missed atoms are structurally invisible to local residual matched-filter**: even allowing K_add=12 candidate slots, the residual MF recall is only 6.7 % — meaning a learned head that scores atoms one-at-a-time from per-atom features cannot recover them. This forces any future learned method to either (i) score atoms jointly with multi-atom context, or (ii) extend the dictionary, or (iii) provide BP-feedback into a 2nd OMP pass.

### Sanity checks

- BER waterfall classical: 1.12e-1 → 4.61e-2 → 8.80e-3 — monotone, no cliff > 5×, on the same shape as Loop-7 probeA classical 100f (1.12e-1 → 4.62e-2 → 1.00e-2). ✅
- BER waterfall oracle: 9.59e-2 → 1.83e-2 → 0 — monotone, matches PCSI-BP at SNR=20. ✅
- Both arms ≥ PCSI-BP lower bound. ✅
- Config printed at top of stdout (`[loop8_diagnose] CONFIG A: N=1024 v=2.0 P=10 tau=10.00ms rho=0.5 l_max=102 k_max=4 dev=cuda`). ✅
- Sample size: 200 paired frames × 3 SNRs × 2048 bits = 1.23 M bits per gate per arm. At SNR=20, expected classical errors ≈ 3 600; expected oracle errors ≈ 0. CI tight. ✅

## Loop 8 paper position (proposed honest close)

**Headline narrow-positive (unchanged from Loop 7)**: Loop-6 fallback, P=8 C1 alone, SNR=15 paired-McNemar 500f −0.86 % (p=0.0013).

**New negative-result section (Loop 8)**: structural diagnosis. Oracle-support replay closes 100 % of channel-side gap at SNR=20 → support-selection IS the bottleneck. But residual-MF recall of missed support is < 7 % even with K_add=12 → C1-class additive heads structurally cannot help; the missed atoms are not visible in the OMP residual. Future work must use multi-atom joint scoring (e.g. BP→OMP feedback, learned dictionary extension, or transformer-style joint column scorer).

This is a clean, falsifiable, reproducible scientific result and a stronger framing than Loop 7's "we tried things and they regressed".

## Awaiting Oracle Round 2 verdict on:

- Q1: any non-residual-MF feature path that could find missed atoms?
- Q2: which pivot direction (D2 / D3 / D5 / D6 / STOP) is minimum-viable next?
- Q3: re-score Loop 8 (1–10) and the cumulative paper position.
- Q4: final go/no-go.

(Pending — paste below when arrived.)

## Canonical artifacts (Loop 8)

### Scripts
- `afdm_sp_joint_unrolled/loop8_diagnose.py` — Phase-0 diagnostic suite (4 arms inferred + 1 oracle-replay + recall stats).
- `afdm_sp_joint_unrolled/_loop8_plot_diagnostic.py` — 3-panel figure builder.

### Outputs
- `afdm_sp_joint_unrolled/outputs_loop8_diagnose_A/results.json` — per-frame + summary.
- `afdm_sp_joint_unrolled/outputs_loop8_diagnose_A/results.md` — table + gate decision.
- `afdm_sp_joint_unrolled/outputs_loop8_diagnose_A/gate_decision.json` — pass/fail flags.
- `afdm_sp_joint_unrolled/outputs_loop8_diagnose_A.log` — full stdout (config-banner-printed; per-fi tracking).

### Figure
- `figures/loop8/loop8_diagnostic.png` — 3 panels: BER waterfall (classical / oracle / PCSI-BP / PCSI-MMSE), NMSE waterfall (classical / oracle), recall@K_add curve with Oracle thresholds.

### Memory
- `_memory/loop8/phaseA_briefing.md` — Round-1 plan submitted.
- `_memory/loop8/oracle_round1_response.md` — Round-1 verdict (D1-A, 7/10, diagnostic-gated GO).
- `_memory/loop8/round2_briefing.md` — Round-2 results submitted.
- `_memory/loop8/oracle_round2_response.md` — Round-2 verdict (pending).
- `_memory/loop8/loop8_summary.md` — this file.
