# Oracle and identifiability supplement: independent reader

`supplement_audit.py` audits the saved `oracle-identifiability/1` stage. It
imports only the frozen audit's file/hash/check infrastructure and the shared
recorder. It never imports or calls `oracle_identifiability.py`, its statistical
functions, original inference calibration functions, or an integration kernel.
The test module alone calls the upstream writer to create a tiny artificial
saved-stage fixture, then checks the independent reader and deliberate corruption.

Run after source commit and main-session GO:

```sh
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_efficient_information.supplement_audit --stage supplement_audit_v1 --input-stage oracle_identifiability_v1
```

The registered cap is 60 seconds; zero new observations, scientific nodes,
rules, receiver calls or decoder calls. All numerical imports happen before
admission; physical geometry/PyTorch initialization is unnecessary for this
array-only reader. The process must use the same project single-thread
environment as the preceding registered readers. The old 761-second audit is
not rerun. Its hash infrastructure is reused without executing old adapters.

The reader verifies the supplemental stage and both original inference stages
with `audit_hashes` before and after calculation: all 4307 protected files,
source bytes/snapshots, committed source blobs, full artifact inventories and
wall/CPU/RSS/observation reservations. Registration/attempt hashes also must
match the supplement's bound original records and recorded consumed-artifact
hashes. The new audit snapshots small registrations/attempts, its sources and
the protected manifest; large original or supplementary NPZ files are not
copied. Its own attempt cost remains outside the input-stage cost total.

Every supplemental row is read and independently reconstructed:

| Output | Coverage and independent calculation |
|---|---|
| NP oracle | All 112 pair/R rows and raw LLR/decision arrays; same-nuisance pair IDs rebuilt from candidates; original calibration/evaluation R-prefix density sums; strict calibrated threshold/rank, finite-calibration marginal bound, false-alarm/power counts and Wilson95, LLR mean/SE |
| Paired decisions | All 1408 rows; same saved groups, four-cell tables, both methods' Bernoulli summaries and signed difference SE |
| Known-eta MLE | All 152 condition/R rows and selected-ID arrays; original candidate IDs restricted by exact nuisance equality; native-target/delta RMSE/bias, delta MSE/SE and boundary counts |
| Paired estimation | All 976 rows; saved original selected IDs, paired delta squared errors and SE; originally unidentified targets retain null error claims |
| Argmin ambiguity | All 976 evaluation rows and every raw group; exact/tolerance sets, unchanged original selected IDs, joint/interest/nuisance and coordinate cardinalities, full count distributions and Wilson95 multiplicity rates |
| Moment criterion | All 9 banks; independent coefficient contractions, exact stored-coefficient classes and matrices, coordinatewise nearby relations and every neighbor list |
| Original calibration | Every original method/R/condition threshold, rank and complete reference objective matrix; original nonrandom decisions checked against unchanged calibration; information-free random decisions read from original saved raw |

Statistical scalar comparisons use `atol=1e-12, rtol=1e-11`; source likelihood
versus objective consistency uses the bound supplement's `1e-10` absolute
tolerance. IDs, counts, masks, rank and machine-tolerance arrays require exact
equality. Original objective values are never shifted or renormalized. The
argmin neighborhood is exactly `64*eps*max(1,max(abs(row)))`; coefficient
neighbors use the registered coordinatewise scale. Ragged exact classes and
neighbor lists are compared as ordered saved-ID lists, not coerced to a NumPy
rectangular array. Near-neighbor relations are never transitively closed.

Coefficient contractions are independently checked by einsum. Exact
equivalence then refers to the verified **stored floating coefficients**, as
the source contract specifies; it is not redefined using slightly different
floating arithmetic. Neither sample ties nor criterion equivalence establishes
full-distribution structural nonidentifiability. The reader checks only the
declared inherited structural labels (control power maps' mu invariance and
the working second Gaussian's q/mu invariance); it supplies no new theorem.

Finite-calibration empirical oracle power remains a reference, not a certified
upper bound. Reused null samples across alternatives are not combined into
an enlarged independent sample count. Reference numerical qualification is
inherited and its exact record checked; no new quadrature is performed.

Outputs are `supplement_audit.json`, `checks.json`, and the standard registered
attempt/source/environment artifacts. Any numeric discrepancy is retained and
causes the attempt to fail. Missing, extra or duplicate supplemental rows are
rejected. Tiny fixture success is not a formal result on research data.
