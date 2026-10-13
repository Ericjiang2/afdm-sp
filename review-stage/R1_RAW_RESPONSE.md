# Round 1 Review (nightmare adversarial)

**Reviewer**: Codex MCP, gpt-5.5, xhigh reasoning effort. Three sequential micro-batches (smoke + Section3 spotcheck + complexity spotcheck), each ≤150-word output, plus Claude-side synthesis from the same on-disk evidence.

**Score: 6.5/10** (TCOM bar; 8.5 = strong accept, 8.0 = accept-minor, 7.0 = borderline, 6.0 = major revisions)
**Verdict: major revisions**

## Verified claims

- **OMP-once support recall ≈ 95 %** with prevalence 67–71 % missed-frame rate, flat across SNR — supported by `outputs_loop13_support_recall/`, internally consistent.
- **Iterative-vs-serial 2–3 orders of magnitude BER reduction at SNR=25 dB** — Table 3 column comparison ($4.1\times10^{-2}$ vs $1.0\times10^{-4}$) is internally consistent.
- **1 041 parameters** for the F2-P head — straight architectural count (384 + 657), verifiable in `classical_joint_unrolled.py`.
- **−18.9 % BER reduction at SNR=20 dB, McNemar one-sided p=0.046, 100 paired frames** under `--use-hard` deployment — verified directly from `outputs_use_hard_canonical/results.{json,md}`.
- **Outer-iteration convergence** with $T_\text{out}=5$ saturating — Table `iterconv` matches `outputs_loop13_iter_convergence_4B_merged/results.json` (300-frame rerun on 2026-04-24).

## Unverified or false claims

1. **Headline −37.7 % / −40.2 % / −37.6 % at SNR=20/25/30 dB with p < 1e-6** (Section3 Table `ber4b`). The repo does not contain a single 4B-pooled-3-seed JSON that reproduces these numbers in one place. The recent (post-FYP) JSONs that *do* exist in the TCOM branch (`outputs_listwise_eval/envelope.json`, `outputs_threshold_sweep/best_tau.json`, `outputs_use_hard_*/results.json`) all live at 100-frame, single-seed, 1024-bit-quantised resolution and **disagree with the headline at SNR=20 dB**: learned BER is *equal-or-worse* than classical (1.8e-4 ≤ 3.1e-4) on the same eval seed 20260423. The headline must therefore have come from `outputs_loop13_4B_retrain27k_snr25_eval_f2p/` (FYP era) and **was not re-run** under the new branch's deployment recipe. **Fail-class** — biggest single risk to the paper.
2. **"≈ 8 % MAC overhead at N=1024"** in Abstract / Table `complexity`. `outputs_complexity/runtime_table.md` shows learned **faster** than classical-torch at N=1024 (402 ms vs 416 ms) and only **+3.9 %** at N=2048. Wall-clock and analytical-MAC accounting disagree by a factor of 2 in the "headline N" cell. **Warn-class.**
3. **"Listwise loss did not help" 5-seed envelope** referenced in the threshold-gate README. `outputs_listwise_eval/envelope.json` shows `learned_std = 0` because the *eval seed* is identical across "5 seeds" — only the *training seed* varies — so the envelope is one eval realisation cloned 5×, not a 5-seed paired-eval envelope. The "negative finding" writeup is therefore underpowered relative to its claim. **Warn-class.**
4. **"Same order as PCSI+MMSE reference at SNR=30 dB"** (Section3 lines 72). Pooled learned arm = $1.1\times10^{-5}$ (29 errs / 2.66e6 bits), Oracle = 0 (CP UB $1.4\times10^{-6}$). Difference in CP CI is one order, not "same order". Soft this prose. **Cosmetic.**
5. **"Complexity-preserving" in abstract** but title still reads "low-complexity". Inconsistent — already flagged at FYP R3 close. **Cosmetic.**

## Critical weaknesses (ranked by ROI)

1. **W1 (Fail-class)**: 4B headline -37.7/-40.2/-37.6 % at SNR=20/25/30 dB has no single reproducible 4B-pooled JSON in the post-FYP repo state. *Min fix*: locate the FYP-era pooled JSON (likely `outputs_loop13_4B_retrain27k_snr25_eval_f2p/`) and either (a) commit it explicitly with frame counts and per-seed splits, or (b) re-run the 600/773/1300-frame 3-seed paired eval under the *current* `--use-hard` deployment recipe and replace Table 3 with the new numbers. Path (b) is what the current branch's deployment recipe is moving toward (commit `8c5beaf`, p=0.046).
2. **W2 (Major)**: 5-seed listwise "envelope" actually shares the eval seed → does not give a paired-eval variance band. *Min fix*: re-eval 5 trained checkpoints on disjoint eval seeds 20260423 / 424 / 425 / 426 / 427 (10-min run on remote), and rewrite the listwise §IV-B passage accordingly. Adds a real retraining-variance bar to address FYP R3 W-2.
3. **W3 (Major)**: Complexity claim "≈ 8 % MAC overhead" disagrees with measured runtime (+3.9 % at N=2048; faster at N=1024). *Min fix*: in §IV-F, switch the headline to the analytical-MAC count and report the measured wall-clock number with explicit GPU/Torch-overhead caveat. Drop the "≈ 8 %" and use the actual ratio (1.5/18.6 = 8 % is the *increment to receiver MAC*; the wall-clock variance dominates anyway).
4. **W4 (Major)**: Abstract / Section1 still uses "low-complexity" colloquially while the abstract body has shifted to "arithmetic-class preserving". *Min fix*: rename to "arithmetic-class-preserving low-complexity-class receiver" globally, including the title (10-min text edit).
5. **W5 (Moderate)**: Prior-art literature on learned sparse / OMP support refinement is thin (one citation). For TCOM, a 2-3 line discussion contrasting (i) approximate message passing, (ii) deep unfolding for compressed sensing, (iii) structured pruning for OMP is the standard ask. *Min fix*: add ≈ 5 references in §1.2 + 2 prose lines in §IV-D.
6. **W6 (Moderate)**: Single trained checkpoint deployed at all SNR cells; no retraining-seed variance bar. The listwise re-eval (W2) provides this for free. *Min fix*: same as W2 — listwise 5-train-seed × 5-eval-seed cross-band gives proper retraining variance.
7. **W7 (Moderate)**: No reproduced external SP-AFDM baseline on shared seed blocks. Repo has `qing_baseline/` (Zheng 2025 receiver) but it's not yet incorporated into Section 3. *Min fix*: add 1 row to Table `ber4b` with Zheng-receiver pooled BER on the same 3 evaluation seeds; even a "matches qualitatively" line gives the paper an external-baseline anchor.
8. **W8 (Cosmetic)**: PCSI+MMSE "same order" prose; soft to "within one order".

## Memory (carry to Round 2)

- **Persistent suspicion 1**: the 4B-pooled-3-seed source JSON for Table 3 is unconfirmed in the post-FYP commit tree. Re-check whenever the author reports "fixed".
- **Persistent suspicion 2**: variance-claim language ("5-seed envelope") whenever it doesn't correspond to disjoint eval seeds — author has reused this pattern once.
- **Persistent suspicion 3**: "low-complexity" / "arithmetic-class" / "≈ 8 %" all appear inconsistently across abstract / title / §IV-F. Watch for partial fixes that touch one location.
- **Pattern**: TCOM uplift commits (threshold-gate, listwise, qing-baseline) sit on disk but are *not yet* threaded into the paper sections. Round 2 should check whether they have been integrated, not just produced.
- **Carry forward**: deployment recipe shifts (`--use-hard`) yield a real, but small (≈ 19 % BER, p=0.046, 1-sided), gain at SNR=20 dB on 100 frames. This is the only directly verifiable post-FYP win in the current repo state. The headline should either be re-derived from this recipe at full sample size, or the original recipe should be restored and the headline re-validated.

