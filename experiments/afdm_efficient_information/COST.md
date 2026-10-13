# Complete costs and amortization contract

Whole-stage wall/CPU, cumulative process peak RSS, and immutable reservations
come from `protocol`. Failed attempts consume their declared wall and observation
allocation and retain raw files. Cost mode reads every existing registration and
attempt, including failures; a missing attempt is reported as missing, never as
zero runtime. Stage wall is not interpreter startup time. Process peak RSS is a
high-water mark, not an isolated kernel allocation or additive memory cost.

`transfer_study.py --mode cost` is a zero-observation, zero-node saved-data reader.
It binds the selected registration/attempt/result/cost JSON inputs and emits a
stage inventory, source cost documents, and complete measured block records.
It reserves 60 seconds. Transfer reserves 900 seconds and 7680 observations.
The main session schedules all numerical work serially and commits sources
before either registered invocation.

## Charging boundaries

- Source feature training is charged once at its original stage: observation
  generation, exact teacher likelihood/score, model selection, regression fits,
  and any calibration/evaluation. Reusing a saved model in transfer does not
  erase those costs or charge the training computation a second time.
- Transfer records independent observation generation, simulation's output
  transform, model-file loading, independent nominal calibration inference and
  threshold selection, complete evaluation inference, reference construction
  and integration, representation comparisons, and geometry diagnostics.
- Complete inference starts from DAFT y and includes the full inverse DAFT,
  feature construction, frozen prediction, and nuisance-score combination.
  Neither y's true parameters nor latent PDP is passed to that function.
- Internal feature timings are diagnostic subcomponents of complete inference;
  they are not added to the enclosing block. Measured blocks are not added to
  whole-stage time. Repeated reference queries reuse a model cache and count
  only newly constructed response vectors; all query-observation pairs count.
- Callback exceptions retain failed block wall/CPU through `finally`, followed
  by the protocol's failed-attempt record. Unknown operation counts remain
  explicitly uninstrumented; absent fields never mean zero operations.

Source-level counts label what they actually count: response atom entries,
gain-response complex products, FFT rows and chirp products, feature monomial
factors, regression dot products, covariance matrices, Cholesky/solve matrices,
CP1 nodes, constructed conditional mean vectors, and component-observation
pairs. Actual branch eigvalsh calls, support eigendecompositions, and gain
normalization validation eigvalsh calls are distinguished. One batched linalg
API call can operate on many matrices; report matrix counts rather than equating
that API call with one scalar factorization.

## Same-object comparison

Canonical full z and full rr^H encode the same orbit for the circular family.
Their direct construction is a legitimate same-object representation comparison,
provided reconstruction/rotation checks pass. Both complete routes include the
same input-domain conversion. O(N) versus O(N^2) output arithmetic and bytes are
reported separately from measured wall time. This comparison does not establish
equal cost for score evaluation or equal accuracy of a learned predictor.

Full likelihood and a four-anchor approximate score are different operations.
No same-quality inference speedup is claimed unless an independent accuracy
criterion on the same probabilistic object passes. Nominal false-alarm/power
similarity alone does not prove density or efficient-information equivalence.

Given genuinely equivalent output quality, one-time candidate expense T and
per-item costs c_ref,c_new, amortization needs c_ref>c_new and
M >= ceil(T/(c_ref-c_new)). If c_ref<=c_new, there is no measured cost advantage.
If quality equivalence is unestablished, there is no supported amortization
claim regardless of the measured runtime. The transfer score therefore defaults
to an explicit **no equal-quality advantage established** outcome; it does not
manufacture a favorable threshold from teacher or inference kernel timing.

## Reproduction

After the main session commits this source and the feature model exists:

```sh
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_efficient_information.transfer_study --stage transfer_v1 --model-path results/afdm_efficient_information/FEATURE_STAGE/model_1_phase.npz
```

After all contributing stages finish and the main session grants the separate
cost-stage GO:

```sh
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_efficient_information.transfer_study --mode cost --stage cost_v1
```

The placeholder feature stage is replaced by the actual immutable model path;
model bytes, efficient beta, configuration, and imported project kernels are
hash-bound. The command examples are not evidence that these studies ran.
