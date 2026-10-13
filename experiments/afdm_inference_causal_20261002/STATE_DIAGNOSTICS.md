# STATE-01: whole-cohort archived terminal-state diagnosis

**H2's general mathematical limitation is supported; its role as the practical failure mechanism is inconclusive and should be downgraded as a leading hypothesis.** This is an analysis of already revealed development outputs, not new receiver performance evidence.

## Cohort and frozen analysis

All 256 original-cascade baseline outputs from `development-run` were included, with six final errors and zero missing states. N=1024, represented P=8 in every terminal state, nominal SNR=6 dB throughout. The separate new `execution/state_diagnostics/registration.json` froze cohort, metrics, contrasts and bootstrap seed before feature/outcome analysis. Labels were already historically revealed; this is not prospective preregistration or fresh confirmation.

Source/run/label receipts were checked against archived manifest and ledger hashes; each raw state and observed input was individually hash-bound. The observation contract contains only y, pilot and sigma2. No true channel, true symbols, codeword files, or receiver runners were loaded. Last-stage precedence follows `receiver_v2/adapter.actual_terminal_channel`; extraction uses the corresponding detector gains and **its own mu/variance**, not geometry's earlier gains or decoder APP moments. The selected stage's decoded bits must exactly match the final decoder bits. MODEL-01's contract confirms this stage logic. The implementation independently reproduces that small extraction contract without importing its receiver wrappers.

The raw data table is `execution/state_diagnostics/states.jsonl`: all 256 IDs, stage, P, geometry indicators, Gram eigenvalues, scalar/conditional covariance metrics, outcome, input/raw hashes and missingness. `summary.json` binds this file and analysis/source hashes. Outputs were created exclusively, preserving old evidence.

## Reference and metrics

For each actual saved terminal mean, define B=[U_p(pilot+mu)]. The working reference is

C=(P I+BᴴB/sigma2)^(-1), c=tr(C)/P.

This is the exact covariance **conditional on treating that total input as known in a Gaussian gain model**. It is not the exact joint posterior for the actual uncertain data, and is not a calibrated truth-based covariance target.

The Frobenius error decomposes exactly:

||C-vh I||² = ||C-cI||² + P(vh-c)².

Report directional=||C-cI||/||C||, scale=sqrt(P)|vh-c|/||C||, total=||C-vhI||/||C||. The identity was checked numerically on every frame, together with scalarity of stored variance. The separation prevents variance scale changes from being incorrectly credited to directional information loss.

## Observations

| Metric | Success mean (250) | Failure mean (6) | Failure minus success, bootstrap 95% interval |
|---|---:|---:|---:|
| Directional relative error | .08840 | .09781 | .00941 [-.03175, .07351] |
| Scalar scale relative error | .39876 | .67833 | .27956 [.23362, .32739] |
| Total relative error | .42948 | .68934 | .25985 [.21745, .30074] |
| Gram minimum/maximum eigenvalue | .77610 | .74635 | -.02975 [-.17002, .05139] |
| Mean saved data variance | .08136 | .14712 | .06575 [.05397, .07645] |

Intervals use 4,000 resamples separately within error/success labels, fixed seed 2026100201. They are descriptive, unadjusted exploratory intervals across several metrics, not significance gates. Six errors give fragile uncertainty estimates. Whole-cohort directional median=.07254, 95th percentile=.09143, maximum=.91919: large directional outliers exist, but the difference by final correctness is not established.

The larger total covariance discrepancy chiefly reflects scalar scale, and failed frames also retain more symbol uncertainty. It is invalid to attribute the observed scale discrepancy exclusively to finite-N AMP bias: the reference deliberately removes that symbol uncertainty. In the separate exactly-known-data orthogonal model, the positive scalar fixed-point variance's relative excess is bounded by P/(N-P) for N>P (finite positive prior reduces it); at N=1024/P=8 this is about .7874%. Thus a roughly .40–.68 scale discrepancy cannot be explained by that finite-N orthogonal limit alone. This does not isolate its cause under actual uncertain data.

## Stage confounding is decisive

| Stage / same-delay status | Frames | Errors |
|---|---:|---:|
| prefix_round1 / no | 214 | 0 |
| cstate / no | 27 | 0 |
| cstate / yes | 3 | 0 |
| coherent / yes | 4 | 0 |
| f1_round1 / no | 2 | 0 |
| f1_cstate / no | 5 | 5 |
| f1_cstate / yes | 1 | 1 |

Every failed frame terminates at f1_cstate, and this cohort contains no successful f1_cstate output. Consequently every stage/P/same-delay stratum lacks outcome overlap. Conditional contrasts are explicitly null, not zero. There is no honest adjusted estimate separating covariance discrepancy from terminal stage/selection, geometry difficulty and residual data uncertainty. P and SNR are constant, so this dataset cannot estimate variation across path counts or SNR. Terminal stopping-stage comparison also involves selection by previous observed syndrome.

## Interpretation and next action

1. **Established:** actual archived Gram matrices are not universally isotropic; scalar directional expressiveness is limited, consistent with IDENT-01. The reference mismatch is measurable without inventing failure-only examples.
2. **Not established:** loss of directional gain uncertainty explains actual FER or is the best repair target. Global directional error and Gram conditioning show no clear error association, and stage overlap is absent.
3. **Recommended feedback:** downgrade the direction-only practical hypothesis. Continue exact small posterior and properly coupled-message diagnostics as specified, including residual data uncertainty and reference-model error. Do not choose a main detector solely because the duplicate-atom counterexample is elegant. A later intervention must compare matched stages/budgets and use genuine mechanism measurements.

## Checks and reproduction

Run from project root with the existing environment:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python experiments/afdm_inference_causal_20261002/state_diagnostics.py
```

Existing results intentionally refuse overwrite. The run verified effective Apple Accelerate **current-thread mode 1**, not merely environment variables or an empty threadpool inventory. All 256 field/identity/dimension/decomposition checks passed; no receiver or remote jobs were run. Runtime output, full environment bindings and source hashes reside in summary.json.
