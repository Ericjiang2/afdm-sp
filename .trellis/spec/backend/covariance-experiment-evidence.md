# Covariance experiment evidence

## 1. Scope / trigger
Use for covariance interventions that replay saved receiver runs, import reviewed
source snapshots, or pool observations sharing exogenous frame randomness.

## 2. Signatures
- `resolve_frozen(root, manifest, loaded_md5, loaded_paths)` binds canonical source
  identities to actual imported bytes.
- `gamma_consistency(..., spec, sbl_G, ..., sigma2)` returns covariance-component
  and normal-equation checks with explicitly declared numerical scales.
- `bootstrap_means(values, cluster_ids, n_boot, seed)` jointly resamples arms.
- `fresh_cohort.py --producing-commit <40hex>` requires the actual pre-run
  commit; its launch chain passes `FRESH_COHORT_COMMIT` and records the value in
  `_argv`/`_config` and `PRODUCING_COMMIT.txt`, including non-Git remote checkouts.
- `DiagonalGamma(physical).projected_variance(*args, **kwargs)` returns only the
  diagonal of the original covariance; `.daft(...)` delegates without alteration.

## 3. Contracts
- Load the real receiver context before identifying its sources. If an imported
  path is supplied, require that exact file and its frozen digest; another
  matching copy cannot substitute. Record actual paths separately from stable
  canonical hash keys. Unit/gate/smoke/main sources must match without waivers.
- Check the directly returned Gamma plus declared extra ridge against SBL Gamma.
  Verify both direct diagonals relative to the expected uncertainty scale.
  Independently verify Q closure relative to the data Gram scale. Do not recover
  a tiny variance by subtracting two large matrices and then divide by that
  tiny variance. Preserve the registered tolerance; fix arithmetic first.
- A Gamma-only diagonal ablation is `Q=BHB+diag(diag(Gamma))+alpha*I`;
  diagonalizing `BHB+Gamma` deletes two components and answers a different question.
  When replaying a frozen loop, a narrow covariance facade may change only
  `projected_variance`; delegate transforms unchanged and avoid global monkeypatches.
- A fresh-frame replay must retain the frozen upstream workflow and original
  round1 APP/check prior. A scoped terminal-detector hook must label its actual
  pipeline return mode; its E3 diagnostic row is no longer an original fixed
  detector result. Count actual SBL fits, detectors, decoders and base generations
  separately; a shared upstream fit is not a new fit for each terminal arm.
- Sampling clusters follow RNG entropy/domain/frame. Keep all shared scenario,
  pilot fraction and SNR rows together. Resample paired arms jointly and divide
  by resampled row count when cluster sizes differ.
- A realized squared error is an error-energy profile, not a correct conditional
  posterior covariance. Oracle response and ridge response are diagnostics.

## 4. Validation / errors
Wrong/missing actual source, duplicate/missing key, mixed snapshot, failed row,
changed within-cluster exogenous hashes or invalid stage FER/NMSE -> fail closed.
Missing/malformed required producing-commit provenance must fail before fresh
generation/fitting; never guess a remote Git revision or hide it with a default.
A covariance facade must reject nonfinite/non-Hermitian/materially non-PSD
original Gamma before projection, using the same declared RTOL/ATOL as its
solver, so a positive diagonal cannot hide an indefinite original.
Nonpositive bootstrap ratio denominators -> record failure fraction and mark
unevaluable at the registered limit; retain direct differences.

## 5. Good / base / bad
Good: actual reviewed source digest matches and canonical duplicate is ignored.
Base: zero symbol uncertainty makes all declared uncertainty interventions equal.
Bad: choose any matching file, loosen tolerance after cancellation, or treat
scenario/SNR copies of one frame as independent samples.

## 6. Required tests
Coexisting source copies; wrong/missing actual path; six-arm zero and tiny
variance; corrupted Gamma/Q/ridge; Gamma-only off-diagonal deletion with full BHB retained and
zero/diagonal-Gamma equality; indefinite original Gamma with positive diagonal;
actual gate full-score trace validation; terminal-hook prior/return-mode and
actual stage-counter checks; joint-frame bootstrap; variable cluster-size
means; denominator failure; stage FER/error consistency; failed-attempt retention.

## 7. Wrong versus correct
Wrong: `(diag(Q - BHB - sigma2*I) - s) / s` for very small s.
Wrong: label a terminal-hook return as the frozen original fixed outcome.
Correct: save its actual mode and qualify the upstream/prior plus unchanged
reference outputs on an old key before touching fresh samples.

Wrong: label `diag(diag(BHB+Gamma))` as a Gamma-only ablation.
Correct: keep BHB intact and project only Gamma; bind both the local matrix
contract and unchanged whole-loop inputs/observer outputs.

Correct: compare direct Gamma diagonals to s, and separately check
`Q == hermitian(BHB + Gamma + ridge*I)` on the Gram scale.

Reference implementation/tests: `experiments/tf_e3c_shrink_20261018/` and
`experiments/tf_covariance_audit_20261018/{sampling,test_sampling}.py`.
