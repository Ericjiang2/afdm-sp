# Final review: sealed-data CGR mechanism audit

**Disposition: PASS for the zero-call offline audit; mechanism verdict: unidentifiable from the archive.** This review does not change the original `candidate_pass=false` or the 101-attempt receiver record. No receiver, decoder, frame generator, optimization, or nonlinear trajectory replay was used for this review.

## Findings (fixed)

- `source_contract.md` and `source_contract.json` were restored into this stable `review/` directory after a temporary result-directory move. The JSON SHA-256 is `83752ab3ed20abf5ec2c8fbbf2b1d80949b3aa8033254a1cba6fd7686d602d37`; its eight first-step observation/raw hashes and source bindings are retained.
- `run_offline.py` had one unused BLOCK `pre_state` assignment (Ruff F841); the implementer removed it. The report now includes per-frame own-arm versus swapped-arm orientation and marks sums across 20 distinct BASE states as descriptive, neither telescoping nor a new gate.

## Source and numerical review

- The analytical BASE JVP matches the frozen scalar map's input timing: previous `mu/v/vh` feed the next step; current `hbar/xbar/s/alpha/rx` are intermediate; only the post-gain `h` tangent receives CGR/SHAM's direct impulse. The derivative carries complex-conjugate adjoints, `hᴴRh`, data and gain variances, residual and damping history, reciprocal floors, QPSK softmax moments, and one-sided clipping. A numerical assertion confirms the final gain impulse cannot change the same batch's terminal LLR. Two independent synthetic one-step finite-difference cases (first step and nonzero damping history) pass. No synthetic step is fed into another nonlinear step.
- All 160 saved BASE steps reconstruct to maximum field error `1.60e-14`. The terminal LLR reconstruction uses the actual all-I/all-Q source convention; actual decoder input is asserted equal to clipped saved detector extrinsic before bit scoring. Truth is loaded by witness-manifest path and SHA-256, and `mean(logaddexp(0, -(1-2*c)*L))`, wrong-sign count, and wrong-confidence sum use saved coded bits and saved clipped decoder input. The upstream frozen source uses the same bit-log-loss sign convention. The independent recount matched all 32 frame-arm score/confidence rows without a decoder call.
- The finite panel contains all eight targets × 20 steps, with `Q=N dhᴴRdh` and `A=D+Q` at the original post-gain BASE anchor. Independent recount found maximum `|D-(A-Q)|=7.11e-15`. Across-state sums are explicitly labeled descriptive.
- The eight-target CGR and SHAM terminal shifts are exact saved arm-minus-BASE extrinsic differences; the independent recount found maximum vector difference zero and metric discrepancy at most `1.42e-14`. Pooled normalized first-order prediction error is `0.519` for CGR and `0.443` for SHAM, with both arms beating zero change on 8/8 frames. Swapping the predicted arm raises pooled errors to `1.735` and `1.638`; own-arm distance wins on every frame. Four CGR rescue-frame finite errors remain material (`0.425–0.587`), so this supports a local message-transport component, not a complete nonlinear decision mechanism.
- BLOCK's own archived gain and covariance maps close against saved `h` and `S`, and the mode panel retains actual force excitation, physical `R` visibility, and `W_Σ xbar`. The source-contract check finds a decisive common-force confound: BLOCK uses time-domain `IDAFT(y)` with AF-domain `Basis.responses(x)`. On eight full target first steps each arm's saved residual reproduces its own source equation within `3.96e-16`, yet BLOCK's residual differs from the AF rotation of BASE's by norm `9.45–11.67`. The metric panel therefore cannot isolate why BLOCK harms outcomes relative to CGR. The ten triggered controls lack per-step vectors and covariance; seven easy controls bypass the branch and are not forced-update safety evidence.

## Findings (not fixed)

- The frozen BLOCK coordinate mismatch and missing control vectors are properties of the immutable source/archive. They are not repaired, simulated, or filled in here. The combined metric-causal hypothesis remains **unidentifiable from this archive**; the observed CGR rescues remain empirical and the original five-gate candidate remains failed.
- The BASE tangent is an analytical first-order approximation. Its nontrivial rescue-frame errors preclude an exact transport or population FER claim. No fitted scale, sign, lag, iteration window, or post-hoc gate was introduced.

## Verification

- Synthetic targeted tests: PASS (`/opt/anaconda3/bin/python experiments/tf_cgr_offline_mechanism_20260923/test_tangent.py`).
- Ruff E4/E7/E9/F/B: PASS for all four offline Python files.
- Mypy: PASS for all four offline Python files with `--follow-imports=skip --ignore-missing-imports --cache-dir=/dev/null`.
- Compileall: PASS. Independent sealed-file inventory: 474/474 hashes PASS. Independent finite, transport, and 32 score/confidence recounts: PASS.

Evidence: `analysis/report.json`, `analysis/finite_panel.json`, `analysis/transport.json`, `analysis/block_metric_covariance.json`, `analysis/block_domain_reconciliation.json`, `independent/analysis_table_recount.json`, `independent/observed_raw_inventory.json`, and this directory's `source_contract.json`.
