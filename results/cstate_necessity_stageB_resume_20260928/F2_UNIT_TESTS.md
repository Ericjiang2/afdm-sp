# F2 small-reference test coverage

Synthetic-only run: [machine receipt](F2_UNIT_TESTS.json), 20 targeted estimator/receiver pytest cases passed, plus the frozen Q1–Q5 standalone script passed. Five separate saved-state/producer instrumentation cases passed, including an interrupted-call charged failure receipt. All had zero real observations, receiver or decoder calls. The tests use fixed small matrices and project CPP/DAFT operators. They are engineering qualification, not 1024-frame FER evidence.

| Required case | Check |
| --- | --- |
| Single path / integer Doppler | N16 exact `Channel.apply` = `regressors @ gains` = dense physical action. |
| Multiple paths / fractional Doppler / equal-delay doublet | N16 three paths `[ℓ=2,2,4]`, `ν=[.25,1.25,−1.5]`; both same-delay columns preserved and distinct; action equality. Frozen Q1 also checks fourth-order Doppler derivative and complex adjoint. |
| Pilot-only, then one data-aided update | Synthetic `estimate` first feedback exactly zero; second pass receives newly charged hard ±.5±.5j; one dense-H/LMMSE call. |
| Support activation/deactivation | δ ranking enters/exits a fixed atom and resolves exact ties by grid index; no count cap of eight. |
| Grid evolution | Real QP from `_grid_update` agrees to `1e−10` with independently evaluated expected complex residual including covariance; prior frozen Q3 runs complete small EM/grid/final reconciliation twice with full versus GAMP posterior. |
| Hyperparameter updates | First EM δ and β matched to independently computed Gaussian expected-energy and expected-residual formulas at `1e−12`; finite positive on further pass. |
| GAMP means and variances | Gaussian scalar posterior mean/covariance exact reference; implemented GAMP variance equals a separately iterated corrected Alg.3 recursion to `1e−12`. Mean is finite and near exact in the scalar fixture. |
| Stopping/caps | Reduced **synthetic test-only** Q/I/T limits yield explicit GAMP/EM/data cap flags, fixed pass count and no false convergence label. Production limits remain frozen at Q100/I20/T4. |
| Coded interface | Synthetic stub checks two F2E rounds, one F2T continuation, native-check carry and P155 shape; a complete raw plus both checkpoint envelopes round-trip through `evidence.save_artifact`. No real decoder call. |
| P155 LOCAL/CSTATE geometry entry | Actual frozen `reopen_geometry` accepts 155 distinct paths for direct and compact strategies in zero-edit/zero-local synthetic entry. This does **not** qualify the full two-edit/two-local-pass branch or its cost. |
| Shared-prefix accounting / saved-state continuations | Synthetic 1024-frame scheduler checks 2048 paid prefixes and every full-cost logical policy; three-continuation stub verifies deep-copy isolation and complete artifact serialization. These are instrumentation tests, not real calls. |

The older fixed-parameter 32×8 reference gave mean error `8.49e−16` and diagonal-variance error `0.0363`. On the current frozen Q2 orthogonal 12×4 fixture the corresponding values are `0.00248155` and `0.263875`; Q3 terminal channel/residual/median-variance differences are approximately `0.013494/0.003497/0.157501`, within its **previously frozen** engineering gates. These are different fixtures, so their numerical differences are not an algorithm change.

The variance discrepancy is expected for the **declared diagonal GAMP recursion**, not a sign/precision implementation defect: for `Φ=[1]`, `δ=2`, `β=4`, full Gaussian posterior variance is `2/9≈0.222222`, while the Alg.3 variance recursion is `v_next=2(0.25+v)/(2.25+v)` and converges to `≈0.593070`. The test reproduces its 100-step value independently to `1e−12`. On the older seeded 32×8 fixture, the original `f2_core` and current `f2_estimator` GAMP mean/variance agree within `1e−12` and reproduce the reported ~0.0363 diagonal gap. This demonstrates that matching posterior means cannot certify full-covariance equality. It does not prove every finite-iteration or full-pipeline variance difference is exclusively the approximation.

Ruff critical `E4,E7,E9,F,B` and targeted mypy pass for the new test file. The runner/source/real branch qualification is a separate gate.
