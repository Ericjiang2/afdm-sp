# PRO_PACK investigation: an untested coherence-induced mean-feedback mechanism

## Outcome

One primary candidate is recommended for a bounded causal production test:
**CGR, coherence-complete gain reaction**. It changes the inference map, not the physical
propagator or its implementation cost. The source-level intervention is alpha*N*vx*R@hbar
in place of alpha*N*vx*hbar in the gain reaction. Everything else stays frozen.

This is not an established new AMP principle. The cross-term algebra is known and broader
versions exist in the supplied source archive. The new scientific lead is the specific
working-geometry regime introduced by CSTATE, which the archived negative screens did
not exercise. Fresh causal relevance and paper-level novelty remain to be demonstrated.
There is no evidence here that proves the whole problem has no further opportunity.

## What was actually inspected/recomputed

- Read all high-level PRO files, its final negative-results ledger and cold index.
- Verified the eight PRO output hashes against its manifest.
- Recomputed all repeated-WORKING-delay cohort counts and mismatch/projection/excess
  medians from its 3072-row table. 36/72 remaining failures have repeated working slots.
- Inspected frozen scalar, coherent-vector and full-block receiver code and the old
  screen callers, not just their summary verdict. Those callers refit to unique delays.
- Inspected P-BiG-AMP's pre-simplification vs large-system cross reaction and the
  non-orthogonal-pilot BiGaBP closest-art records. Read the actual Master gain equation
  from its rendered page. No fresh cold NPZ or production receiver was replayed locally.

## New mathematical/reference calculations

`qualification.json`: 36 checks. Independent scalar reference matches archived TF;
full block matches archived block map; group blocks reduce on distinct delays; same-
delay full block matches the full map; prior-preserving duplicate/merge test for BLOCK.
Maximum discrepancy 8.73e-12. The merge property is NOT claimed for CGR.

`reaction_qualification.json`: 37 checks. Same-delay Gamma=N*vx*R for nonuniform diagonal
V; exact common-state gain change; same-spectrum phase sham; invisible null-direction
counterexample. Maximum numerical-identity discrepancy 4.97e-14. The12 additional separate-module patch qualifications are in `patch_qualification.json`.

## Receiver probes (not production FER)

Small reference: N64, a synthetic systematic sparse-check (128,64) code, known geometry,
random gains normalized in coefficient norm, nontrivial CPP, a shared scalar first round,
and the same second-round CE/LDPC processing. 240 observations in each geometry stratum.
Word errors: distinct scalar/reaction/group/full = 124/124/124/122;
close-pair scalar/reaction/group/full = 140/136/135/134.
Reaction rescued/harmed 8/4 in the close-pair stratum. This is retained adverse evidence
against a universal no-harm claim. See `toy_receiver_rows.json`.

Larger independent reference: N1024, P8, the ACTUAL supplied LDPC(2048,1024) cache and
original decoder, all-I/all-Q, rho=.5, nominal6.5dB. Geometry is fixed and supplied to
all estimators; no acquisition/CSTATE is run. Gains/bits are unknown to the estimator.
A common scalar first round and common posterior-moment gain refit precede the only
changed TF20 batch and LDPC50. This does not recreate the production observations.

128 fixed seeds per stratum, shared message/gain/noise draws across the geometry controls:

| Geometry | Scalar errors | CGR errors (rescue/harm) | Group block | Full block |
|---|---:|---:|---:|---:|
| Eight distinct delays | 0 | 0 (0/0) | 0 | 0 |
| Two same-delay doublets, separation .05 bin | 37 | 34 (3/0) | 34 | 34 |
| Same-delay triple, Dopplers .41,.43,.46 | 42 | 38 (4/0) | 39 | 39 |

The doublet matched-spectrum wrong-phase sham produced47 errors (0 rescues/10 harms vs
scalar), using those SAME128 observations. An operator-Gram preconditioned block also
produced34 errors, with no extra rescues versus CGR. These are exploratory reuse checks,
not independent confirmations. Never pool strata/repeated runs as one FER denominator.

Doublet median operator NMSE: scalar .00479405, CGR .00264032, group .00252756,
full .00251237, wrong-phase sham .00790526. Smaller NMSE did not give blocks additional
correct words over CGR. On the triple, CGR actually retained one more correct word.

Reference detector+decoder median times were about19ms scalar/CGR,36ms group,30ms full
in the first larger run. They are neither calibrated production timings nor full receiver
latencies. Runtime instrumentation and repeated-run timing variability are left in rows.

No coded performance claim follows from the algebra alone; gains here are modest and
cannot establish causal attribution for the saved fresh production failures.

## Run

Python3, NumPy, SciPy. No network access or external private workspace needed.
The frozen files/cache under `frozen_reference/` were copied from the user's archive;
no third-party installation/source reconstruction is needed for these checks.

```sh
OPENBLAS_NUM_THREADS=1 python verify_reference.py
OPENBLAS_NUM_THREADS=1 python verify_reaction.py
OPENBLAS_NUM_THREADS=1 python verify_patch.py
OPENBLAS_NUM_THREADS=1 python run_probe.py
OPENBLAS_NUM_THREADS=1 python run_ldpc2048_probe.py
OPENBLAS_NUM_THREADS=1 python run_triple_probe.py
OPENBLAS_NUM_THREADS=1 python run_sham_probe.py
OPENBLAS_NUM_THREADS=1 python run_gram_probe.py
```

The first timeout-style tool receipt on the larger probe was not a receiver failure:
the completed process wrote all256 rows, summaries and its34.20s execution footer;
these final files were inspected before use. No incomplete results are promoted.

## Files

- `METHOD.md`: equations, reductions, limits and exact novelty boundary.
- `SOURCE_AUDIT.md`: why the previous negative screens do not close this regime.
- `CLOSEST_ART.md`: public and internal ancestry.
- `CODEX_TEST.md`: 25 fixed observations,4 fixed arms,100 complete calls, no sweep.
- `witness_manifest.json`: exact93 indexed existing NPZ paths/hashes.
- `make_production_variant.py`: SHA-bound separate source-module creation; no frozen edits.
- JSON rows and summaries retain positive and negative reference outputs.
- `evidence/`: unchanged high-level supplied PRO records.
