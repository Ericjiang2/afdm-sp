I cannot certify the experiment integrity from the current attachment payload. The requested audit files are not accessible: `/mnt/data` is empty, and targeted searches for `eval_classical_joint_unrolled.py`, `Section3.tex`, `CLAIMS_FROM_RESULTS.md`, and the listed `outputs_loop13*.json` files returned only unrelated TikZ/figure build files, not the evaluation scripts or result JSONs. The findings below are therefore an **auditability failure**, not a finding that the thesis results are fraudulent.

### A. Ground-Truth Provenance: FAIL

Evidence: N/A — The required scripts `eval_classical_joint_unrolled.py`, `run_classical_baselines_python.py`, `loop13_iter_convergence_probe.py`, `loop13_new_baselines_eval.py`, `loop13_support_recall_probe.py`, `headroom_decomposition_probe.py`, and `compute_heldout_metrics.py` were not available in the accessible files, so I could not trace `y_sim, bits_sim → model → bits_hat → ber(bits_sim, bits_hat)` end-to-end.
Details: Upload the full source tree or an archive containing those scripts. Without them, I cannot determine whether BER, support recall, NMSE, or headroom metrics use simulator-drawn ground truth or model-derived proxies.

### B. Score Normalisation: FAIL

Evidence: N/A — The support-recall and evaluation scripts, especially `loop13_support_recall_probe.py`, and the output `outputs_loop13_support_recall/recall_by_snr.json` were not accessible, so I could not inspect denominators, top-K definitions, raw hit/total counts, or self-normalisation risks.
Details: Upload the support-recall script and JSON. This check cannot pass until the denominator and raw-count provenance are inspected directly.

### C. Result-File Existence and Number Matching: FAIL

Evidence: N/A — None of the listed result files were accessible: `outputs_loop13_4B_full_results.json`, `outputs_loop13_4B_retrain_eval_results.json`, `outputs_loop13_4B_retrain27k_snr25_eval_results.json`, the iter-convergence JSONs, new-baseline JSONs, headroom JSONs, support-recall JSON, or `outputs_loop13_2B_snr0_5_results.json`.
Details: This is the critical blocking issue. I cannot verify file existence, JSON validity, key paths, numeric agreement with `paper/sections/Section3.tex`, `Section4.tex`, `Abstract.tex`, or whether `_merge_snr20_300f.py` produces the claimed mixed 80/300-frame convergence table.

### D. Dead-Code Detection: FAIL

Evidence: N/A — `classical_joint_unrolled.py` and the listed evaluation scripts were not accessible, so I could not identify unused metric functions, unused feature extractors, deployment/training mismatch, fallback bypasses, or whether the learned arm could silently reduce to the classical arm.
Details: Upload `classical_joint_unrolled.py`, the trained-head loading/eval scripts, and any config/checkpoint-loading code. This check specifically requires source inspection, not summaries.

### E. Scope vs Language: FAIL

Evidence: N/A — The requested thesis files `paper/sections/Abstract.tex`, `Section1.tex`, `Section4.tex`, and `Section5.tex` were not accessible, so I could not compare scope language against the actual tested scenarios, seeds, frame counts, or confidence intervals.
Details: Upload the paper source files and result files together. Scope inflation cannot be judged from the project briefing alone.

### F. Evaluation-Type Classification: WARN

Evidence: N/A — From the project briefing only, the work appears to be simulated AFDM/UWA evaluation rather than hardware/ocean measurements, but I could not verify the source files.
Details: Provisional classification is `simulation_only`; whether the headline metrics are also `real_gt` depends on inspecting the missing evaluation scripts.

## Overall Verdict: FAIL

## Integrity Status: fail

## Evaluation Type: simulation_only

## Claim Impact

* Abstract's BER/NMSE headline: unsupported
* §3 iter-convergence claim (mixed 80/300 frame): unsupported
* §3 support-recall claim: unsupported
* §3 headroom-decomposition claim: unsupported
* §4 "classical joint is the data-detection bottleneck" claim: unsupported

## Action Items (ranked by severity)

1. Upload the complete audit package as a single archive containing the source tree, `paper/sections/*.tex`, `CLAIMS_FROM_RESULTS.md`, all listed JSON result files, and helper scripts such as `_merge_snr20_300f.py`.
2. Include a manifest with file sizes and hashes for every result JSON and evaluation script, so file existence and number matching can be checked unambiguously.
3. Re-run the audit only after the primary evidence is available; otherwise any PASS/FAIL on ground-truth provenance, score normalisation, or dead-code bypasses would be speculative.
