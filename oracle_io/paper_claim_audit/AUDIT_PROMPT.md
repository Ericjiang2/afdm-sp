# Paper Claim Audit — Zero-Context Evidence Verification

## Your role

You are a **fresh, zero-context paper-to-evidence auditor**. You have **never seen this work before**. Your job is a mechanical cross-check:

> For every number / percentage / comparison / scope statement in the paper, verify that the raw evidence files actually contain that number (or support that statement).

You will receive **only paper source files and raw result JSONs**. You will NOT receive any executor-written summaries, prior audit reports, narrative docs, or conversation history. This is intentional — the point is to verify the paper against data without any bias from how the authors described their work.

**CRITICAL: Use a fresh reasoning session. Do not import any assumptions.**

## What you receive

### Paper source (the claims):
- `paper/main.tex` — LaTeX preamble + structural skeleton
- `paper/sections/Abstract.tex`
- `paper/sections/Section1.tex` — Introduction & claims
- `paper/sections/Section2.tex` — Methods (signal model + Algorithm 1 + learned head)
- `paper/sections/Section3.tex` — Results (all Tables + Figures)
- `paper/sections/Section4.tex` — Discussion
- `paper/sections/Section5.tex` — Conclusions
- `paper/math_commands.tex` — custom macros (`\ClassicalJoint`, `\LearnedHead`, `\Oracle`, `\snr`, `\Kadd`, `\Ppath`, `\Nsub`, `\kleak`, `\rhop`, `\Heff`, `\Serial`, `\fs`, `\fc`, `\xp` etc.). Read this first so you correctly expand macros.

### Raw result files (the evidence):

**Main BER waterfall** (single-checkpoint + pooled runs):
- `afdm_sp_joint_unrolled/outputs_loop13_4B_SMOKE_plain_c2rel_results.json` — plain C2-rel smoke test, seed 20260425, 400 frames. Explicitly labelled SMOKE in the filename.
- `afdm_sp_joint_unrolled/outputs_loop13_4B_retrain_eval_results.json` — plain C2-rel eval, seed 20260425, 400 frames (different checkpoint).
- `afdm_sp_joint_unrolled/outputs_loop13_4B_retrain27k_snr25_eval_results.json` — F2-P run, seed 20260425, 350 frames, ckpt `outputs_loop13_4B_train_27k_with_snr25/...`. **This is the "single-seed 400-frame illustrative row" source for §3 Table 3 (the learned column).**
- `afdm_sp_joint_unrolled/outputs_loop13_4B_retrain27k_snr25_eval_f2p/results.json` — identical numerical content to above (nested-directory copy).
- `afdm_sp_joint_unrolled/outputs_loop13_4B_retrain_eval_plain_c2rel/results.json` — nested copy of the plain-C2-rel 400-frame run.

**3-seed pooled evidence** (for the pooled headline: frame counts 600/773/1300 at SNR 20/25/30 dB):
- `afdm_sp_joint_unrolled/outputs_loop12_r3_official/results.json` — seed 20260423, 500 frames, fs_factor not stored in _config (run with defaults, fs_factor=2.0 per paired_learned_eval CLI).
- `afdm_sp_joint_unrolled/outputs_loop12_matched_f2p_s20_30/results.json` — seed 20260423 extension, +300 frames at SNR 20/25/30.
- `afdm_sp_joint_unrolled/outputs_loop12_seed2_s20_s25_s30/results.json` — seed 20260424, 500 frames at SNR 20/25/30.

**Outer-iteration convergence** (for §3 Table 2 + Fig `fig:iterconv`):
- `afdm_sp_joint_unrolled/outputs_loop13_iter_convergence_4B_merged/results.json` — mixed 80-frame SNR=15 + 300-frame SNR=20 merged file (the one the paper cites).
- `afdm_sp_joint_unrolled/outputs_loop13_iter_convergence_4B/results.json` — original 80-frame both SNRs (superseded by merged for SNR=20).
- `afdm_sp_joint_unrolled/outputs_loop13_iter_convergence_4B_snr20_300f/results.json` — 300-frame SNR=20 rerun (fed into the merge).

**Support recall** (for §3 Table `tab:supportrecall` + Fig `fig:recall`):
- `afdm_sp_joint_unrolled/outputs_loop13_support_recall/recall_by_snr.json`

**Headroom decomposition / oracle headroom** (for §3 Table `tab:oraclehead` + Fig `fig:oraclehead`):
- `afdm_sp_joint_unrolled/outputs_loop13_headroom_4B_big_v2/headroom_results.json` — **the current cited source.** 250 frames per SNR × SNR {15, 20, 25} × configs {baseline, oracle_support, oracle_physical}.

**Other available JSONs** (may or may not be cited; verify whichever the paper references):
- `afdm_sp_joint_unrolled/outputs_loop13_new_baselines_500f_results.json`
- `afdm_sp_joint_unrolled/outputs_loop13_new_baselines_4B_results.json`
- `afdm_sp_joint_unrolled/outputs_loop13_iter_convergence_v2_results.json`
- `afdm_sp_joint_unrolled/outputs_loop13_2B_snr0_5_results.json`

You will NOT receive EXPERIMENT_AUDIT.md, findings.md, REPRODUCTION.md, AUTO_REVIEW.md, CLAIMS_FROM_RESULTS.md, NARRATIVE_REPORT.md, PAPER_PLAN.md, or any executor-written summary. If your audit requires context beyond the files above, say "missing_evidence" rather than guessing.

## Audit protocol

### Step 1 — Extract every quantitative claim from the paper.

For each quantitative claim (number, percentage, ratio, comparison, error-count, frame-count, bit-count, SNR value, confidence interval, McNemar p-value, gap-closed fraction, parameter count, MAC count, complexity class, …) make a row:

```
claim_id: C01, C02, ...
location: Abstract | §1 | §3 | §4 | §5 | Table <label> row K col M | Fig <label> caption | inline text
paper_text: <verbatim quote from paper>
paper_value: <the specific number or phrase>
```

Do not paraphrase. Quote verbatim, including LaTeX-rendered text where possible. Expand macros using `math_commands.tex`.

### Step 2 — Trace each claim to evidence.

For each claim, identify the raw JSON / tex file that supplies the number. Compute the value and compare:

```
evidence_file: <path>
evidence_key_path: <json path, e.g. ["20", "learned_errs"] / ["per_snr", "20", "mean_recall"]>
evidence_value: <the actual number in the file>
match: exact_match | rounding_ok | mismatch | missing_evidence | ambiguous_mapping
```

Tolerance: **only standard rounding to displayed precision.** 3.887e-4 rounded to 3.89e-4 is OK. 3.80e-4 rounded to 3.89e-4 is NOT OK. If the paper says "~2 dB" or "≈ 95%", check that the underlying number rounds to that precision.

### Step 3 — Check these specific failure modes:

1. **Number inflation**: paper displays a value higher than raw.
2. **Best-seed cherry-pick**: paper says "achieves X" but X is the best seed; mean is lower. (In this paper, most tables are paired McNemar from ONE checkpoint + N evaluation seeds — so "best seed" would mean cherry-picked evaluation seed within pooling. Look for mismatches between "pooled headline" and "single-seed illustrative" rows.)
3. **Config mismatch**: two compared methods ran at different fs_factor / N / ρ_p / P_paths. Check the `_config` block in each JSON.
4. **Aggregation mismatch**: paper says "pooled over 600 frames @ SNR=20" but the JSONs sum to a different frame count.
5. **Delta / gap-closed error**: verify arithmetic. E.g., if paper says "Gap closed 81%" and uses `(baseline − learned) / (baseline − oracle_physical)`, check that (baseline, learned, oracle_physical) values substituted give 81 ± 1 %. Flag sub-% rounding drift as rounding_ok.
6. **Caption–content mismatch**: does each Figure / Table caption match the numbers / structure inside it?
7. **Scope overclaim**: does the paper say "consistent / always / generally" while the evidence is from one simulator / one checkpoint / one frame budget?
8. **Pooled-BER reconstruction**: for the 3-seed pooled rows at SNR 20/25/30 dB, SUM `classical_errs` and `learned_errs` over the three per-seed JSONs at each SNR, divide by the summed `cum_bits`, and verify the resulting delta percentage matches the paper's claimed −37.7% / −40.2% / −37.6%. Report exact ratio, and note that absolute pooled BERs from the three JSONs may be at 2B (fs_factor=2.0) whereas the paper's Table 3 headline column might be interpreted as 4B — check whether the paper explicitly states the fs_factor for the pooled row.

### Step 4 — Output format (for each claim)

```
### C<NN> — <one-line summary>
- Location: <section or table/fig + cell>
- Paper text: "<verbatim>"
- Paper value: <number>
- Evidence file: <path>
- Evidence key-path: <json path>
- Evidence value: <number>
- Status: exact_match | rounding_ok | ambiguous_mapping | missing_evidence | number_mismatch | aggregation_mismatch | config_mismatch | delta_error | scope_overclaim | caption_mismatch
- Details: <one-sentence explanation if not exact_match or rounding_ok>
```

After all claims:

```
## Overall verdict: PASS | WARN | FAIL
## Totals: total=<N>, exact_match=<..>, rounding_ok=<..>, ambiguous_mapping=<..>, missing_evidence=<..>, number_mismatch=<..>, aggregation_mismatch=<..>, config_mismatch=<..>, delta_error=<..>, scope_overclaim=<..>, caption_mismatch=<..>
## Priority fixes (if any): <ranked list of FAIL/WARN items with specific edit suggestions>
```

**Be thorough but efficient.** Expect 30–60 distinct quantitative claims across the paper. Don't skip any Table cell or inline number. Don't invent claims that aren't in the paper. Don't include conversation-history-based assumptions.

Honest PASS is more useful than performative WARN. If everything matches to displayed precision, say PASS with confidence.
