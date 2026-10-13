# Deterministic deep-principles checks

This package verifies three new mathematical predictions against the unchanged
actual G0/Dirichlet model. It generates **zero random observations** and makes no
receiver, decoder, fitting, or optimization calls. Scientific stages run only on
the main session's authorized SSH snapshot. Local tests use tiny fixed arrays.

## Frozen configuration and invocation

`config.py:CONFIG` is the scientific source of truth. Export it into the output
control directory, commit the source, and bind the exported bytes before running:

```sh
python -m experiments.afdm_deep_principles_20261006.study --print-config
python -m experiments.afdm_deep_principles_20261006.study --print-imports

python -m experiments.afdm_deep_principles_20261006.study \
  --phase moments --stage moments_v1 --artifact-root ABSOLUTE_OUTPUT \
  --config ABSOLUTE_CONFIG --wall-seconds 600
```

The other phases are `stability` / `stability_v1` and `mixture` / `mixture_v1`.
`--print-imports` preloads the real numerical imports, including frozen upstream,
then lists real bound source paths and excluded virtual module labels. It does
not construct an ActualPrior or evaluate a physical response. Normal stage CLI
requires the supplied config to equal the committed CONFIG exactly.

The output root must contain `control/run_contract.json`. Each phase reserves
its full allocation, including failed attempts: 4,000 moments, 4,000 stability,
42,000 mixture = 50,000 kernel evaluations and at most 1,800 reserved wall seconds.
The remaining task allowance belongs to the main session. Existing stages are
never overwritten. No installation or remote execution is initiated by this code.

## What is checked

- **Moments:** N4, all 256 legal QPSK vectors, actual null and separated fixed H.
  The complete dechirped K22 and K40 tensors are compared with their analytic
  formulas. Gaussian noise at variances 0, .2, 1 is integrated using Wick terms,
  not sampled. Null C2 covariance is independently obtained from the exhaustive
  power covariance plus exact Gaussian conditional variance.
- **Stability:** actual N4 and N16 columns at a fixed legal branch. Derivatives
  through order three use the finite Fourier sum and analytic derivatives of the
  original five-point window norm, then the unchanged actual cap/prune mask.
  Their value is checked against the frozen physical response. Complex gain plus
  real center projection is compared with a separate real Jacobian SVD. Analytic
  delta² / delta⁴ coefficients and matched-pair cubic remainders are checked at
  preselected deltas .01, .003, .001. No exponent is fitted. Numerical rank failure
  is explicit; no jitter or silent pseudoinverse is used.
- **Mixture:** all 138 actual PDP components and both labels are retained before
  combining identical scales. Gamma is independently checked against the finite
  geometric PDP formula. The local-limit power is integrated at h=.05,.2,1 after
  the exact transform z=ell*u/sqrt(1-u²), using 64 and 128 Legendre nodes on
  [0,1−1e-6]. The omitted power-excess tail is in [0,.95e-6]. Interior refinement
  is a numerical diagnostic, **not a rigorous bound on total quadrature error**.
  The small-h logarithmic coefficient is stored as an analytic formula only;
  these moderate-h calculations do not certify its asymptotic limit.

For noncentrality at most 1e-6, the bounded power kernel uses the explicit
quadratic Poisson expansion. Its absolute Taylor error is bounded by lambda³/6;
larger values use SciPy's noncentral chi-square survival function. Invalid
probabilities fail rather than being clipped.

## Accounting, artifacts, and failure handling

The counter charges logical scalar kernel values: each enumerated QPSK state and
its fixed-channel response, each K22/K40 or covariance coordinate, each actual
geometry call, each Dirichlet derivative coefficient, each independent Fisher
projection, each position-moment coefficient, each PDP component, each Legendre
node, and each evaluated bounded power value. Arithmetic, tensor contractions,
and the internal operations within one such kernel are not separately counted as
new evaluations or observations. Charges occur before calls. The unmodified
recorder separately records real wall/CPU time, peak process memory, source/Git
identities, thread pools, and artifact hashes.

Every completed case saves an exclusive NPZ with raw tensors/vectors/integrands
and a JSON check record. `scientific_checks.json` retains all completed cases;
`kernel_counts.json` records successful counts. An exception writes
`kernel_counts_partial.json` and propagates to the old recorder's failed-attempt
record; earlier raw cases remain in place. Failed cases cannot be dropped to
create a passing summary.

The adapter privately reuses the previously qualified coherent admission chain
and its older higher-order recorder. It retargets only the private instance and
requires committed bytes for this new package before any callback. It preloads
numerical dependencies and keeps the effective thread inventory fixed.

## Local contract checks

```sh
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
  /tmp/afdm-shared-channel-env/bin/python -m unittest \
  experiments.afdm_deep_principles_20261006.test_contracts -v
ruff check experiments/afdm_deep_principles_20261006
python -m compileall -q experiments/afdm_deep_principles_20261006
```

These fixtures are not scientific acceptance. They verify real-versus-complex
center projection, elementary derivatives, both Gaussian Wick pairings, bounded
power behavior, budget rejection, source admission, and private-instance isolation.
