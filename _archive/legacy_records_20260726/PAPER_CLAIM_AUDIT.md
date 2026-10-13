# Paper Claim Audit Report

**Date**: 2026-04-25
**Auditor**: Codex GPT-5.4 xhigh (fresh zero-context thread, threadId `019dc079-ccb4-7c60-8a91-b9b6de470b44`)
**Paper**: AFDM-SP learned C2-rel F2-P receiver (BEng FYP thesis)
**Note**: switched from Oracle web (which refused to access the attachment bundle for the second time) to Codex with direct read-only filesystem access.

## Overall Verdict: **FAIL**

The paper is **not making fake claims** — headline deltas and frame counts reconstruct exactly from the pooled raw JSONs — but several **table rows cite absolute values and counts that do NOT come from the named raw source files**. Most are rewriting-fixable; three are real substantive issues (items 1, 3, and 5 below).

## Totals (38 claims audited)

| Status | Count |
|---|---|
| `exact_match` | 4 |
| `rounding_ok` | 18 |
| `ambiguous_mapping` | 1 |
| `missing_evidence` | 2 |
| `number_mismatch` | 4 |
| `aggregation_mismatch` | 5 |
| `config_mismatch` | 3 |
| `caption_mismatch` | 1 |
| `delta_error` | 0 |
| `scope_overclaim` | 0 |
| **TOTAL** | **38** |

## Priority issues (ranked)

### P1 (FAIL) — Table 3 pooled row absolute BERs don't match the pooled source JSONs
- **Affected rows**: Table `tab:ber4b`, "3-seed pooled (headline)" at SNR 10/15/20/25/30 dB.
- **Paper says** (e.g., SNR 20 dB row): Classical $5.0 \times 10^{-4}$, Learned $\mathbf{3.1 \times 10^{-4}}$, counts $\approx 381 / 1.23 \times 10^6$.
- **Pooled evidence** (sum of `outputs_loop12_{r3_official, matched_f2p_s20_30, seed2_s20_s25_s30}`): Classical $3.00 \times 10^{-3}$, Learned $1.87 \times 10^{-3}$, 2295 learned errors / $1.23 \times 10^6$ bits.
- **Delta OK** (−37.74% ≈ paper −37.7%, frames 600/773/1300 exact). **Absolute BERs are 2B-scale**, but the paper's table prints 4B-scale absolute numbers.
- **Claims affected**: C05, C06, C07, C08, C09, C10 (per-row absolute values in headline rows 10–30 dB).
- **Fix**: either (a) replace the absolute BER columns with the 2B pooled values from the 3 JSONs (honest but breaks the 4B consistency of Table 3); (b) produce a 4B-rerun of those 3 pooled seeds and point to it explicitly; (c) change Table 3 caption to state clearly "pooled delta and frame counts from 2B seed blocks; absolute BER column is from the 4B single-seed illustrative run, shown as representative of the same 2 dB log-BER separation". Option (c) is cheapest and is a caption edit only.

### P2 (FAIL) — "Single-seed 400-frame" label on Table 3 is wrong; the actual source is 350 frames at 20/25 dB
- **Affected rows**: Table `tab:ber4b`, "Single-seed 400-frame (illustrative)" rows at SNR 15/20/25 dB; Table `tab:oraclehead` caption ("learned column from the separate single-seed 400-frame F2-P run").
- **Paper says**: "400 frames", $5 / 8.19 \times 10^5$ at 25 dB, budget $8.19 \times 10^5$ bits.
- **Evidence**: `outputs_loop13_4B_retrain27k_snr25_eval_results.json` (`_config.frames = 350`, with adaptive early-stop leaving 80 frames at SNR=15 dB and 350 at SNR=20/25 dB). Actual SNR=25 is **4 errors / 716800 bits → 5.58e-6**.
- **Math check**: $5 / 8.19 \times 10^5 = 6.10 \times 10^{-6}$, NOT $5.58 \times 10^{-6}$. The paper's displayed "5 / 8.19e5 = 5.58e-6" is arithmetically inconsistent.
- **Claims affected**: C13, C14, C15, C16, C32.
- **Fix**: change "400-frame" → "350-frame (adaptive)" in Table 3 caption + lower-block header + Table 8 caption; change "5 / 8.19 × 10^5" → "4 / 7.17 × 10^5" at 25 dB; same-bit-budget PCSI sentence needs rewording (the paper says "in the same bit budget the PCSI+MMSE reference yields 0 bit errors" — check which budget, since F2-P is 7.17e5 bits / 350 frames and different plain-C2-rel oracle observations use other budgets).

### P3 (FAIL) — Pooled McNemar p-value at 30 dB is **under-reported** (paper says 4e-3, actual ~1e-59)
- **Affected claim**: Table `tab:ber4b` SNR=30 dB cell cites "$p = 4 \times 10^{-3}$".
- **Evidence**: summing `mcnemar_n10 + n01` over the 3 pooled JSONs at 30 dB yields a χ² that makes the two-sided continuity-corrected p `≈ 2.9 × 10^{-59}`.
- **Direction**: this is a **conservative** error — the true p is even more significant than the paper claims. It does NOT overstate the result. But the number is still wrong.
- **Claims affected**: C11 (abstract's "worst-case p ≤ 4e-3").
- **Fix**: either recompute p at 30 dB using the pooled counts and cite the correct value, or change "$p = 4 \times 10^{-3}$" → "$p \ll 10^{-3}$" to avoid the over-specific wrong number.

### P4 (WARN) — Serial-floor claim BER ≈ 4.1e-2 is not supported
- **Affected claim**: multiple (Abstract, §1, §3, §4) all cite "serial arm floors at BER ≈ 4.1e-2 from SNR ≥ 15 dB".
- **Evidence** (`outputs_loop13_new_baselines_4B_results.json`): serial BER at 15/20/25 dB is 5.78e-2 / 4.93e-2 / 4.94e-2.
- **Claims affected**: C37 (Abstract + §1 motivation + §3 + §4).
- **Fix**: soften to "≈5e-2" or "4–6 × 10^{-2}". The NMSE ≈ −11.3 dB part IS supported; only the BER number needs adjustment.

### P5 (WARN) — "≈ 2.5 orders of magnitude at SNR = 25 dB" is not supported by the raw evidence
- **Affected claim**: Abstract + §1 + §3 + §3 summary.
- **Evidence**: no single coherent (serial, classical) pair in the raw files gives 2.5 decades. Available pairs: 4B baseline → retrain = 3.0 decades; 2B pooled = 1.83 decades.
- **Fix**: change to "approximately two to three orders of magnitude" (covers both observed pairs) or pick one specific evaluation and say "≈3 orders of magnitude under the [4B / new-baseline] eval".

### P6 (WARN) — Table 8 (`tab:oraclehead`) row-source caption is imprecise
- **Affected claim**: caption says "learned column from the separate single-seed 400-frame F2-P run of Table 3".
- **Evidence**: the F2-P source is 350-frame adaptive. See P2.
- **Fix**: same as P2 — change "400-frame" → "350-frame adaptive".

### Minor: missing raw evidence for two claims (not blocking submission, but should be noted)
- **C28 — support-Jaccard > 0.94 from iter 2**: no Jaccard trace in the raw JSONs audited. Supported by a probe run that was not included in the audit package. If raw JSON exists elsewhere, cite it; otherwise soften to "support overlap between successive OMP passes is high".
- **C36 — MAC-count table (`tab:complexity`)**: analytical counts, not produced by a profiler run. If this is the intent (all cells are closed-form complex-op counts derived from the receiver diagram), the paper should say so explicitly in the caption rather than presenting as "measured". No fix needed if §2 already derives these analytically.

## What is CORRECT (the audit confirms)

- **All pooled delta percentages** (−37.7 / −40.2 / −37.6%) reconstruct exactly from the 3 seed JSONs (C10, `rounding_ok`).
- **All pooled frame counts** (600 / 773 / 1300) match exactly (C04).
- **All iter-convergence Table 5 cells** at t=1..5 match the merged JSON to displayed precision (C17-C21).
- **All four support-recall table rows** match the raw file exactly (C23-C26).
- **All three oracle-headroom Table 8 rows** (with gap-closed 61/81/98%) match the v2 JSON to displayed precision (C29-C31, C35).
- **Physical-oracle censored-zero claim** (CP 95% UB ≈ 5.86 × 10^{-6}) is correctly computed (C34).
- **Clean-pilot sign-flip between 30-frame and 250-frame reruns** (1.6σ) is supported by the two headroom JSONs (C33).
- **All parameter counts** (1,041 = 384 + 657) are internally consistent (C01).
- **All configuration parameters** (N=1024, P=8, fs=16 kHz at 4B, (l_max, k_max, Q) = (160, 2, 800)) match the JSON `_config` blocks (C02, C03).

## Implication

The thesis's **headline story is data-supported**. The pooled delta, frame counts, p-value *ordering* (p ≤ 4e-3), learned vs oracle ranking, gap-closed fractions, support-recall statistics, and iter-convergence waterfall are all exact-match or rounding_ok.

The FAIL verdict comes from **three specific table-presentation issues** (P1, P2, P3) where the paper prints numbers or labels that don't trace back to a single raw source:

- P1: 4B absolute pooled BER columns in Table 3 — probably from a 4B pool run that isn't in the audit evidence set
- P2: "400-frame" label that's actually 350-frame adaptive
- P3: "p = 4e-3" at 30 dB that's actually p ≈ 1e-59 (direction of error: under-reports significance)

Plus two cosmetic soft-claim issues (P4, P5) and two "cite-the-source" gaps (C28 Jaccard, C36 MAC counts).

## Action items for the author

Minimum-effort path to `PASS` (estimated ~1 hour of LaTeX edits, zero re-runs):

1. **P1 fix**: Edit Table 3 caption to clarify "pooled delta and frame counts from 2B seed blocks; 4B absolute BERs are from the single-seed illustrative row". OR: change the absolute-BER columns in the pooled rows from 4B numbers to the 2B pooled reconstruction (~10 numbers, each a simple lookup from the 3 JSONs).
2. **P2 fix**: "400-frame" → "350-frame (adaptive)" in two places (Table 3 caption lower block, Table 8 caption). Fix the "5 / 8.19e5" → "4 / 7.17e5" in the §3 / §4 / §5 same-budget sentences.
3. **P3 fix**: "$p = 4 \times 10^{-3}$" → "$p \ll 10^{-3}$" at the 30 dB cell + "worst-case p ≤ 4e-3" in Abstract → "worst-case p < 10^{-3}" (note: ≤ 4e-3 is technically TRUE if p is 1e-59, but it's a much weaker claim than what the data actually support).
4. **P4 fix**: "4.1e-2" → "4–6 × 10^{-2}" (or cite specific: "5e-2 at SNR=20 dB").
5. **P5 fix**: "2.5 orders of magnitude" → "2–3 orders of magnitude" (or "≈3 orders" with specific receiver pair named).
6. **C28 / C36**: add a one-line note in §3 or §2 that support-Jaccard and MAC counts are from (a) an ancillary probe that produced per-iteration Jaccard traces, and (b) closed-form per-operation counting of the receiver architecture — respectively. If no Jaccard source JSON can be produced, soften to "support overlap is high".

**No experiments need to be rerun for P1-P5 + C28/C36.** All fixes are either source-traceability captions (P2, P6) or arithmetic corrections (P1, P3, P4, P5, C28, C36).

## Artifacts

- Full Codex raw response: inline in this report (the 38 claim-level analyses are reproduced in `PAPER_CLAIM_AUDIT.json`)
- Audit prompt: `oracle_io/paper_claim_audit/AUDIT_PROMPT.md`
- Oracle (failed, bundle-not-accessible) response: `oracle_io/paper_claim_audit/ORACLE_RESPONSE.md`
- Oracle log: `oracle_io/paper_claim_audit/oracle_run.log`
- Codex thread ID: `019dc079-ccb4-7c60-8a91-b9b6de470b44` (for replay if needed)
