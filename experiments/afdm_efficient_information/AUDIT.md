# Independent saved-data audit

`audit.py` is a separately registered reader for AUDIT-01. It does not import
the scientific feature, score, likelihood, fitting, calibration or reporting
functions under audit. Its test module imports those functions only to compare
small known fixtures. The runner and frozen physical geometry helpers are
reused; physical-model provenance is therefore not an independent second
implementation of the production generator.

## Frozen admission and evidence

- Run only after the audit sources are committed and the main session gives GO:
  `/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_efficient_information.audit --stage audit_v1`.
- The stage reserves 900 seconds, zero new observations, zero new scientific
  quadrature nodes/rules, zero receiver/decoder calls. Existing rule nodes may
  be deterministically reconstructed as explicitly described below. These are
  audit computations over already approved rules, not new scientific samples.
- Input stages are fixed before registration. The reader streams SHA256 for
  all 4307 protected files, bound source files and snapshots, committed source
  blobs and complete artifact inventories. It repeats the input check at exit.
- Registrations, attempts and the protected manifest are snapshotted. Large
  raw NPZ files are checked in place and are not copied into the audit snapshot.
- A failed registered stage retains all measured and reserved cost and is not
  represented as a completed scientific replay. Unknown successful schemas,
  missing/nonfinite costs, missing artifacts and modified hashes fail explicitly.
- `TRANSFER_ADMISSION_REJECTION.json` is included separately: transfer_v1 was
  rejected before registration, with no stage, new observations or reservation.
  Diagnostic wall time absent from that record is not fabricated.
- The audit's own terminal attempt cost remains outside its input inventory.
  The final task report must add that attempt once, without recursive totals.

## Independent arithmetic and coverage

The common tolerance is `atol=1e-7, rtol=2e-6`; counts, selected candidate IDs,
decisions and inventories require exact equality. This checks reproduction, not
mathematical certification of finite-sample Fisher estimates or quadrature.

| Stage | Full saved-data reconstruction | Density/integration coverage |
|---|---|---|
| feature_control | All 10240 rows; closed polynomial features, frozen predictions, every ridge candidate, train/validation/test splits, nuisance projections, information, MSE/SE and all registered bootstrap resamples | All teacher rows, using Hermitian spectral inverses/log determinants instead of the source Cholesky/solve path |
| feature_actual | All 1280 rows and all feature-layer statistics; every teacher qualification and Gaussian-transfer mismatch | All saved orders 12/24/48 and refined-step components over all 1280 rows |
| inference_control | All training means, covariance banks, candidate objectives, calibration thresholds, selected IDs, rejection counts/Wilson intervals, RMSE/bias, boundaries and grid coverage | All saved inference rows against every candidate, independently using spectral Gaussian mixtures |
| inference_actual | All 12288 feature/prediction rows, candidate mean validation and banks; all 6144 calibration/evaluation frames, all objectives and statistical reports, qualification denominators and reference sensitivity | First 8 frames of each condition and split: 256 frames against all 16 candidates at both primary/refined orders; every saved order48 audit-subset pair. **Not** a full 6144-by-16 independent integration |
| prior_information | All 256 rows per case/rule, nuisance coefficients, residuals, information/SE, convergence gates and classifications | First 8 rows per case and original GL/Sobol rule, both saved derivative steps and all saved FD fixtures. Original v1 did not save component means or FD-side densities: these use independent deterministic reconstruction of the original bound rules and frozen physical geometry |
| prior_refinement | All 256 rows for all 4 rules, residuals, information/SE, convergence decisions, saved chart/Jacobian and angular mass | First 8 rows per saved base rule and derivative component; all saved FD-side component integrals. The 18944 source nodes and 32 unused initialization nodes remain source costs, not new audit nodes |
| transfer | All 7680 raw-generation arithmetic replays, dense IDAFT, four-anchor features/predictions, 48 performance rows, calibration and binomial intervals; 72 dense geometry rows and 24 representation size/product checks | All saved 16-row N4 references per scenario, original saved rules and canonical-phase identity checks |
| cost | Stage roster, all whole-stage wall/CPU/RSS and reservations, copied source cost documents | No likelihood work |

Feature columns are rebuilt using direct power/coherence identities rather
than the original monomial catalog. Ridge fitting uses augmented LAPACK least
squares; moment projection uses a data-matrix SVD rather than the original
covariance pseudoinverse. The Bessel reader uses `scipy.special.ive` on saved
means/derivatives. Prior original rule reconstruction distinguishes itself from
saved-component replay in both output and scope.

Candidate objectives are independently checked before saved objectives are
used for exact tie-breaking and discrete report reconstruction. This avoids
changing a mathematical tie solely through a different floating-point
evaluation order. A source-derived second-Gaussian log density uses its saved
variance array; that variance is not claimed to receive a new analytic
population-covariance proof. Geometry collision fits are recomputed from saved
analytic covariance differences; the audit does not claim fresh covariance
quadrature or an independent collision-coefficient theorem.

## Cost interpretation

Whole-stage wall/CPU already includes setup, fitting and all kernel work.
Nested timers are categories, never added again to whole-stage totals.
The frozen Gaussian teacher calls both a batched Cholesky and a general solve.
Historical `teacher_covariance_factorizations` / `covariance_factorizations`
count Cholesky matrices only. The audit emits source-derived
`cholesky_matrices` and `general_solve_matrices` separately; it never modifies
raw records or doubles measured time. Transfer's newer records already expose
both counts. Learned inference has no established same-object, equal-accuracy
cost advantage merely because the full canonical representation is smaller.

## Validation and outputs

`test_audit.py` contains only tiny fixtures: full closed-feature columns,
ridge/data projections, full feature fitting/bootstrap reports, spectral
Gaussian and Bessel teachers, original rule reconstruction, candidate-bank and
grid statistics, corrupted artifact/missing-cost rejection, unknown schemas,
exact PyTorch virtual namespace filtering, and pre-registration accounting.
These tests are not a formal run of the nine research-stage audit.

Each completed adapter writes a stage report; `checks.json` preserves all
numeric discrepancies even when the registered attempt fails. A successful
`audit_summary.json` requires every check to pass and all input hashes/costs to
remain unchanged. Failed numerical-reference qualifications in the original
research remain failed qualifications after a successful reproduction audit.
