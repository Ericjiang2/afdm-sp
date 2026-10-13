# Offline analyzer code review — 2026-09-23

**Post-seal erratum:** this original code verdict is superseded for physical analysis. After the first analysis, review found `analyze.py` used synthetic-fixture `c1/c2` at its offline diagnostic call site rather than the production source-bound system parameters. The original bytes and analysis outputs are preserved; a separately versioned offline reader and output directory are required before any final physical-evidence verdict. No additional receiver call is needed. The checks below describe the earlier code review, not approval of the parameter provenance.

**Code verdict: PASS for offline execution after a committed observed seal.** This is a source and synthetic-test verdict, not an empirical five-gate verdict. No cold truth was opened for this review.

Reviewed immutable file bytes:

- `experiments/tf_cgr_mechanism_20260923/analyze.py`: SHA-256 `105660af22f39b99c58b3d5b7ef4d208b200762119760a503e67944d38609456`
- `experiments/tf_cgr_mechanism_20260923/test_analyze.py`: SHA-256 `e0adc921b42c4cb659cb7f482fbaa9f1e3acb2eff163af6ed5bbd850fcd905df`

Review findings resolved in this analyzer version:

- The analyzer verifies the complete 100-call observed inventory and a full Git commit containing the matching seal before loading any truth. It rejects analysis output inside the observed or witness roots. It checks 25×4 allocation, sealed hashes, four-arm native/post-refit equality, historical BASE bits, and three completed distinct-delay identity controls.
- Exact bit recount uses the sealed code-cache bytes and actual `H`, `G`, and `free_cols`. It reports all arm-pair overlaps, rescues, harms, valid-but-wrong outcomes, full 25-observation deadline denominators, and complete/triggered-branch time distributions.
- The selected-geometry physical projection now solves actual per-delay modulation columns by SVD least squares. Its primary Frobenius residual is the fitted physical signal norm, avoiding near-duplicate Gram-square conditioning and subtraction cancellation. The Gram/eigenvalue, singular-value/rank, coefficient-sensitivity, and cancellation values remain diagnostics. Independent dense full-operator least squares agrees for exact duplicate, near duplicate, and separated synthetic paths. The analyzer also reports all 20 target iterations' signed common-state physical effects, `dhᴴRdh`, CGR terminal mismatch, and working same-delay Γ versus `N vₓ R`.
- The five registered engineering gates are evaluated without retuning. Mixed directional evidence remains `inconclusive`; it is not converted to a post hoc pass. The failed first attempt is shown separately as one charged attempt with zero complete wrappers, and the paired v2 denominator remains 100.

Verification on the frozen bytes: `/opt/anaconda3/bin/python experiments/tf_cgr_mechanism_20260923/test_analyze.py` PASS; `ruff check` on the analyzer and test PASS; targeted `mypy --follow-imports=skip --ignore-missing-imports --cache-dir=/dev/null` PASS; `py_compile` PASS.

**Pending empirical gates:** the proposed 100 v2 calls require the user's additional budget approval and have not been represented here as complete. The observed seal has not been reviewed as a committed object, no truth recount or physical trajectory result has been seen, and Luna's independent recount is outstanding. The prior serialization failure remains a distinct charged attempt; an approved 100-call v2 run would bring the total to 101 attempted calls. A passing synthetic fixture cannot establish FER or a physical mechanism claim.
