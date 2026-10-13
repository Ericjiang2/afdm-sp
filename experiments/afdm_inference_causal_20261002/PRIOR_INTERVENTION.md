# PRIOR-02: fixed last-state interface intervention

**Result: changing only CE's prior precision produces a perturbation that the original joint update largely attenuates. This does not identify the prior switch as the main inference defect.** The source describes CE gains as initialization, so the two regularizers remain a legitimate target-switch strategy rather than a demonstrated implementation bug.

## Frozen scope

The registration selects all 256 archived baseline frames, freezes each actual terminal geometry, and forms common feedback from the final decoder APP/check messages clipped at ±20. This constructs a new fixed last-state feedback interface; it is not replay of the original cascade's entering messages. Even for archived coherent-stage outputs, both diagnostic arms use original `twofft.scalar_joint`, not the historical private coherent variant.

Two exact frozen-q fits differ only in the gain prior precision:

Q_a=BᴴB+Gamma+sigma2*a*I, h_a=Q_a⁻¹Bᴴy, a=1 or P.

B and Gamma use existing physical regressors/projected_variance with the same frozen APP moments, complete CPP and continuous Doppler. Each fit initializes the actual unmodified `scalar_joint`, both with its original prior CN(0,I/P), identical check prior, noise, geometry and damping=.3. Each arm runs 20 steps, and separately 40 steps as a propagation diagnostic. There are no geometry searches, posterior-covariance-as-prior substitutions, additional candidate banks, LDPC calls or FER measurements.

All 1,024 planned calls completed on the local CPU within the 120-second CPU cap: observed CPU time **23.03 seconds**, actual Accelerate current-thread mode 1. Both arms at each iteration budget perform the same operations; the 40-step diagnostic is not an efficiency or innovation claim. Registration/source/input/raw hashes and complete per-frame metrics are preserved under `execution/prior_intervention/`.

## Results

Attenuation means ||h_joint,1-h_joint,P|| / ||h_CE,1-h_CE,P||.

| Whole-cohort metric | 20 steps | 40 steps |
|---|---:|---:|
| Median gain-perturbation attenuation | .01064 | .0004704 |
| Mean attenuation | .01299 | .004553 |
| Maximum attenuation | .5690 | .3762 |
| Median extrinsic-LLR RMS difference | .0001613 | .000004897 |
| Mean extrinsic-LLR RMS difference | .0002833 | .0002006 |
| Median symbol-mean RMS difference | .000004101 | .0000001803 |
| Maximum gain-variance difference | 2.07e-8 | 8.07e-9 |

Every frame's gain perturbation is smaller after joint processing than before it. Typical differences shrink strongly, but a few outliers remain; mean symbol-mean difference is not monotonically reduced across the two budgets. Neither universal convergence nor zero impact follows.

A further diagnostic evaluates the common-P frozen-q normal-equation residual at each resulting detector mean/variance. Mean relative residuals for precision1 versus precisionP initialization are .0019590/.0019511 at 20 steps and .00150710/.00150708 at 40 steps. These are **surrogate residuals** for fixed-q CE, not a proof that uncertain-data AMP should solve that objective. Their similar values provide no evidence that changing the initializer alone closes the actual inference approximation.

Branch-specific records and distributions cover all terminal stages, not just failures. The cohort's old correctness labels were not loaded by this intervention, and no output was selected by those labels.

## Causal interpretation

The two-arm difference isolates the initial CE regularizer at the specified fixed interface. It supports the claim that original joint inference often suppresses this initialization perturbation. It does not show whole-cascade FER harm or benefit, does not test geometry changes induced by another ridge during acquisition/refinement, and does not establish a common globally convergent objective.

Feedback for H1: keep the algebraic distinction documented, but downgrade it as a candidate principal defect. A prior-unification-only change is not supported as a main innovation. The remaining covariance/soft-information approximation requires independent oracle and message-closure evidence.

## Verification and reproduction

Two targeted tests passed: the precision1 fixed-geometry implementation matches actual `time_refine(rounds=0)` on a valid fractional-Doppler case, and P=1 produces exact agreement between both prior conventions. Every real fit saves its normal-equation residual, and every output preserves frozen P and geometry through the existing API. Python compilation passed.

```sh
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python -m unittest discover -s experiments/afdm_inference_causal_20261002/tests -p test_prior_intervention.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python experiments/afdm_inference_causal_20261002/prior_intervention.py
```

The second command intentionally refuses to overwrite the completed records. Preserve this run and register a new destination before a future independent repeat. The result receipt binds registration and the complete records file. No frozen receiver source changed; no remote experiments or fresh performance claims were made.
