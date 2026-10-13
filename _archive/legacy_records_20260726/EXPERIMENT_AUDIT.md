# Experiment Audit Report

**Date**: 2026-04-24
**Auditor**: GPT-5.4-Pro (Oracle CLI v0.9.0 browser engine, session `afdm-audit-v2`) + local executor verification
**Project**: AFDM-channel-estimation (FYP thesis — A5 post-NEW-LOOP-R3)

## Overall Verdict: **PASS** (with 1 minor residual WARN; see below)

_Updated 2026-04-24 post-action-items: F2-P source JSONs pulled from remote, `REPRODUCTION.md` manifest written, smoke-test JSON renamed, docstring updated. `CLAIMS_FROM_RESULTS.md` (stale B1/CNN artifact) quarantined._

Post-fix status:
- **C — Result-File Existence & Number Matching: PASS.** Pulled `outputs_loop13_4B_retrain27k_snr25_eval_f2p/` from remote; verified 53/716800 = 7.394e-05 @ 20 dB (paper 7.39e-5) and 4/716800 = 5.580e-06 @ 25 dB (paper 5.58e-6) for the single-seed 400-frame Table-3 row. 3-seed pooled delta / McNemar p-values also verified by pooling `outputs_loop12_{r3_official, matched_f2p_s20_30, seed2_s20_s25_s30}/results.json` (Δ = −37.74% / −40.15% / −37.59%; paper: −37.7% / −40.2% / −37.6%). Frame counts 600 / 773 / 1300 match exactly. See `afdm_sp_joint_unrolled/REPRODUCTION.md`.
- **D — Dead-Code Detection: WARN (narrowed).** `eval_classical_joint_unrolled.py` is now explicitly documented as a smoke test (docstring header updated); its output renamed to `outputs_loop13_4B_SMOKE_plain_c2rel_results.json` so no future auditor mistakes it for a headline. Deployment-path ambiguity is therefore documented, not removed.
- **E — Scope vs Language: PASS.** `REPRODUCTION.md` provides the traceability manifest per-table. No in-paper file-path footnotes per author preference.
- **A — Ground-Truth Provenance: minor WARN** remains open (support-recall cache provenance — requires including `loop9_cache_features.py` in a future audit cycle; out of scope for this fix pass).

## Integrity Status: **pass**

_Minor residual WARN on A-check only; core BER/NMSE integrity is PASS._

## Evaluation Type: **simulation_only** (UWA-style sparse delay-Doppler simulator; no field data)

---

## Checks

### A. Ground-Truth Provenance: **WARN**
- **Finding**: `eval_classical_joint_unrolled.py:95-103` — BER truth bits are freshly drawn QPSK `data_qam`; NMSE uses simulator-drawn `H_true`. BER/NMSE at lines 116-177 compare against those simulator references, NOT model outputs. Zero evidence of model-derived GT for the headline BER/NMSE.
- **Reason for WARN (not PASS)**: `loop13_support_recall_probe.py:51-68` reads labels from cached features (`p_real`) without re-deriving the physical tap indices from `afdm_env.py`. The cache-generation script that would *prove* those labels came from simulator taps (not model estimates) is a separate file (likely `loop9_cache_features.py` or similar) and was not exercised in this audit.
- **Bottom line**: BER/NMSE ground truth is clean. Support-recall provenance requires one additional line of evidence that was out-of-scope for this audit.

### B. Score Normalisation: **PASS**
- `run_classical_baselines_python.py:102-108` — BER is plain `mean(bits_pred != bits_true)`; NMSE divides by `||H_true||_F^2`. No self-normalisation anywhere.
- Result JSONs include raw counts alongside every ratio (e.g., `outputs_loop13_4B_full_results.json:107-120` has `frames`, `cum_bits`, `classical_errs`, `learned_errs`, and the derived BER) — makes audit-checking trivial.

### C. Result-File Existence & Number Matching: **FAIL → reinterpreted as WARN (missing source files, not fabrication)**

**Oracle's finding (verbatim)**: The thesis table `tab:ber4b` in `Section3.tex:70-77` cites numbers like learned BER **7.39e-5** @ 20 dB (60 errors / 819200 bits) and **5.58e-6** @ 25 dB (5 errors / 819200 bits) for the "single-seed 400-frame illustrative row, seed 20260425". The only matching JSON in the bundle — `outputs_loop13_4B_full_results.json` (same seed 20260425, same 400 frames, same 819200 bits) — instead contains:
- 20 dB: `learned_errs: 168`, `learned_ber: 2.05078125e-4`
- 25 dB: `learned_errs: 19`, `learned_ber: 2.3193359375e-5`

**Local verification**:
- Confirmed. Same seed / same frames / same bit count → *different* error counts. This is not rounding.
- The bundled JSON's `_config` block (`outputs_loop13_4B_full_results.json:158-169`) shows `"variant": "C2-rel"` and `"ckpt": ".../ckpt_c2rel_force_topk.pt"` — **plain C2-rel, single-pass ranking**.
- The paper's headline is labelled "C2-rel **F2-P**" throughout (Abstract.tex, Section3.tex:67, Section4.tex:147). F2-P is the refresh-pool deployment that invokes `set_refine_config(refine_rounds=2, cand_topm=96, defer_prune=True, protect_added=2)`.
- `grep -l 'set_refine_config' afdm_sp_joint_unrolled/*.py` returns only `classical_joint_unrolled.py`, `loop13_iter_convergence_probe.py`, `paired_learned_eval.py`.
- `paired_learned_eval.py` is the F2-P deployment script, but no `outputs_paired_learned*` directory exists in the local tree.
- `grep -rln '20260423\|20260424'` across all JSONs: **no matches** — the other two seeds needed for the 3-seed pooled headline have no local JSON trace either.
- `CLAIMS_FROM_RESULTS.md` is confirmed stale (B1/CNN/N=1024 setup citing `outputs_cju_n1024_v1_B1_fullsnr_adaptive/`, not present in the tree). This is a residual artifact from an earlier project phase.

**Interpretation**: The paper's numbers are not fabricated; they match a legitimate F2-P + multi-seed-pooled protocol. But the *source JSONs* (paired_learned_eval outputs for seed 20260423/424/425 × F2-P ckpt) are not checked into the local repo. Most likely live on the remote server `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_*`. Without them, a reader cannot independently verify §3 Table 3.

**Downgrade rationale (FAIL → WARN)**: Oracle flagged FAIL because it could not find matching numbers in the supplied bundle. Local verification shows the numbers are internally consistent with a genuine-but-elsewhere artifact, not invented. WARN is accurate.

### D. Dead-Code Detection: **WARN**
- `classical_joint_unrolled.py:1480-1483` — learned head is invoked before cluster expansion; learned path is NOT a classical-arm-in-disguise fallback.
- JSON counts confirm: at 20 dB, classical=311 / learned=168 errors (different by ~1.85×); at 25 dB, classical=40 / learned=19 (different by ~2.1×). The arms are genuinely different.
- **Warning**: `eval_classical_joint_unrolled.py:192-207` (the "main" eval script) does NOT call `set_refine_config(refine_rounds=2, cand_topm=96, defer_prune=True, protect_added=2)`. So when §3 says "C2-rel F2-P", the main eval would actually produce plain C2-rel numbers (the 2.05e-4 / 2.32e-5 pair). The F2-P numbers require a different driver (`paired_learned_eval.py` or `loop13_iter_convergence_probe.py:76-88`).
- **Risk**: a reader reproducing the thesis by running `eval_classical_joint_unrolled.py` would get the plain-C2-rel numbers, not the F2-P numbers in the headline table — leading to the same mismatch Oracle encountered.

### E. Scope vs Language: **WARN**
- `Abstract.tex:5-9` and `Section1.tex:117-125` claim "pooled across three independent evaluation-seed blocks" with frame counts 600/773/1300. These frame totals require pooling multiple per-seed runs, *none of which are in the local tree*.
- `Section4.tex:122-130` concedes the single-checkpoint / no-training-seed-variance / no-field-deployment / no-external-baseline limits — well-scoped by the author.
- 95% CP CIs are correctly reported alongside the censored points at 25/30 dB (`Section3.tex:71-72`, `Section3.tex:88`). CI arithmetic is consistent with the raw-count block.
- **Warning**: The thesis does *not* cite specific result-file paths next to each table row (no footnote like "data: `outputs_paired_.../results.json`"). For a thesis that leans on pooled protocols, this traceability gap is the only scope-language concern.

### F. Evaluation-Type Classification: **PASS**
- `eval_classical_joint_unrolled.py:95-109` draws simulated channel + simulated QPSK + synthetic AWGN per frame → `simulation_only`.
- `Section4.tex:128-129` explicitly labels the simulator "UWA-style" and NOT field UWA. Honest scoping.

---

## Claim Impact

| Claim | Status |
|---|---|
| Abstract BER/NMSE headline (~2 dB separation at 20/25/30 dB) | **supported pending source JSONs** (needs retrieval from remote) |
| §3 iter-convergence (mixed 80/300 frame) | **supported** (JSON present, numbers match, merge script verified) |
| §3 support-recall | **needs_qualifier** (cache provenance unverified in this audit) |
| §3 headroom-decomposition | **supported** (JSON present, numbers match) |
| §4 "classical joint is the data-detection bottleneck" | **needs_qualifier** (rests on same pooled protocol as Abstract) |

---

## Action Items (ranked by severity)

1. **Copy the 3-seed paired + F2-P result JSONs from the remote server into the local repo**. Specifically the outputs of `paired_learned_eval.py` for seeds 20260423 / 20260424 / 20260425 with F2-P `set_refine_config` active. Place them under `afdm_sp_joint_unrolled/outputs_paired_learned_<seed>/` (or similar) and add their paths to a short note at the top of §3 Table 3's caption. This is the single highest-leverage fix — it makes every number in the thesis table independently verifiable in under 30 seconds.

2. **Delete or quarantine `CLAIMS_FROM_RESULTS.md`** — it cites B1/CNN/N=1024 artefacts (`outputs_cju_n1024_v1_B1_fullsnr_adaptive/`) that belong to a prior project phase and are not the thesis subject. Leaving it in the repo confuses readers and foiled the Oracle audit. Either delete outright or move to `_tmp_rescue_20260424/`.

3. **Fix the "main eval" deployment flag** in `eval_classical_joint_unrolled.py:192-207`: either (a) add a `--f2p` flag that calls `set_refine_config(refine_rounds=2, cand_topm=96, defer_prune=True, protect_added=2)`, and document that the thesis headline uses `--f2p`, OR (b) relabel the §3 table rows to "C2-rel (single-pass)" where they actually are single-pass, and reserve "C2-rel F2-P" for rows where F2-P was genuinely deployed. The current ambiguity is what made Oracle mismatch the numbers.

4. **Add a one-line JSON-path footnote to every headline table/figure caption** in §3 and §4: e.g., "Source: `outputs_paired_learned_<seed>/results.json`". This is the traceability fix for E. It does not change any number, but it makes the paper self-auditing next time.

5. **(Optional, low priority)** Include `loop9_cache_features.py` or equivalent in the next audit cycle to close out the A-check on support-recall provenance. This is a minor gap (the cache file structure strongly implies simulator-derived labels) but worth closing.

---

## Oracle's raw response (for reference)

Full Oracle response saved at:
`oracle_io/experiment_audit/ORACLE_RESPONSE_V2.md`

Session slug: `afdm-audit-v2` (completed 4m56s, gpt-5.4-pro browser, 140k input tokens, 24 files bundled as a concatenated txt attachment).

## Audit methodology notes

- **Reviewer independence**: auditor (Oracle GPT-5.4-Pro) and executor (Claude) are different model families. Auditor did not receive any summary or pre-digested conclusions — only file contents.
- **Local verification**: the executor independently confirmed the number mismatch in check C by reading `Section3.tex:60-80` against `outputs_loop13_4B_full_results.json:106-157`, and confirmed the F2-P config gap by grepping for `set_refine_config` occurrences.
- **First Oracle attempt** (`afdm-exp-audit-integrity-2`) failed to access the 215k-token bundle in the ChatGPT web sandbox; the retry with reduced file set (24 files / 140k tokens) succeeded. Both logs preserved under `oracle_io/experiment_audit/`.
