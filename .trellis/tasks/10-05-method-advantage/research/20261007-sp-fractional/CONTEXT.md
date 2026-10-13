# Actual model and candidate discrimination

2026-10-07; read-only source study. This file does not register a scientific run.
Canonical task/requirements: `ANCHOR.md`; live rows are in the linked Mission.

## Actual observation and source contract

- `experiments/sp_afdm_frozen_20260920/src/physical.py`: `Channel`, `daft`,
  full CPP propagation, all real Dopplers, and exact time-domain derivatives.
- `experiments/afdm_structured_inference_20261003/MODEL_CONTRACT.md`:
  AF-domain data, N1024, pilot/data power .5/.5, QPSK, all-I then all-Q,
  n2048/dv3/dc6 LDPC seed20260726. The time samples are not iid QPSK.
- Frozen upstream `afdm_sp_joint_unrolled/budgeted_support_eval.py:114`:
  construction is exactly `pilot=sqrt(rho)*_zc_seq`, `x=pilot+data`.
- Frozen upstream `afdm_sp_joint_unrolled/afdm_env.py:129`: ZC root7,
  exp(-i*pi*7*k^2/N); actual c2 is nonzero and irrational-scaled. A heuristic
  identification of its inverse DAFT with an exact constant-modulus chirp is
  invalid. See the independently authored SP_INFORMATION_GEOMETRY note.
- Same upstream `afdm_env.py:586`: local five-coefficient energy normalization,
  clipping and .01 relative-power pruning, then G0 Frobenius normalization.
- `experiments/afdm_shared_channel_20261004/PRODUCTION_PRIOR.md`: actual
  conditional gain law is PDP-anisotropic and normalized by the G0 Gram.
  G1 reuses those same gains without physical renormalization. CN(0,I/P) is a
  working inference prior, not the generating law.

## Already available methods that are not new contributions

1. `experiments/sp_afdm_native_joint_20260921/src/twofft.py` already implements
   full-physical TimePathOps and scalar joint P-BiG-AMP with two transforms per
   iteration. Its gain uncertainty is scalar, its Doppler geometry is fixed
   inside `scalar_joint`, and `time_refine` performs frozen-q physical geometry
   fitting separately. No fractional tail deletion occurs in that detector.
2. `experiments/cstate_necessity_stageA_20260928/keep_slots.py` already retains
   multiple same-delay paths, all physical cross moments and bounded continuous
   Doppler refinement. Its brackets remain anchored to incoming centers.
3. `physical.py:103` and `experiments/afdm_structured_inference_20261003/JET.md`
   already contain exact Doppler derivatives, first/second moment jets, pushed
   forward gain priors and counterexamples to uniform fixed-center accuracy.
4. `experiments/sp_afdm_frozen_20260920/src/structured_ep.py` already has an
   exact cyclic-band Gaussian solver and time-domain sparse matrix. The native
   RESEARCH_VERDICT compares this established EP route. Thus initial candidate
   C (banded elimination) is a reusable comparator, not an unexplored main idea.
5. Native `joint_tangent.py` already has a joint gain/data first-order Gaussian
   Schur method. Its documented dynamic relinearization failures and lack of
   demonstrated rescue must not be erased. Its linearization concerns gain and
   data, not a finished uncertain-real-Doppler message.
6. Existing ORBIT/MESSAGE/POTENTIAL studies already treat symmetry, improper
   moments, cavities, marginalization and cross-moment counterexamples. Merely
   adding a covariance or calling an existing formula Bayesian is insufficient.

## What the new evidence changes

A. Pilot-law ambiguity remains a valid mathematical distinction between
Gaussianized data and QPSK, but the actual ZC is not the simple exact ambiguity
counterexample. It requires a quantitative near-ambiguity/relevance argument
before motivating a transmitter change. Oversampled ambiguity optimization
already has strong OFDM precedents.

B. The active tangent note isolates a different issue: a value-exact truncated
channel can be locally unidentifiable in fractional Doppler after unknown gain
elimination. Actual .01 pruning supplies a positive-width central-only region.
This is relevant to model validity and G0 labels; it does not accuse full F1 of
the same defect. Performance benefit over F1 remains missing.

C. Generic sparse-time/banded inference is deprioritized after finding the
existing implementation and published dual-domain EP. No duplicate prototype.

D. A possible next gap is uncertainty in continuous real Doppler shared across
all samples during SP data detection. A correct tangent has real coefficient
constraints and joint gain/data dependence; it cannot be assigned arbitrary
independent complex jet gains or recycled as a new independent observation.
This is only a candidate requiring new derivation and prior-art discrimination.

## Scientific scope and next action

No new receiver/decoder/observation/SSH job has run. No new performance number
is claimed. Complete the independent theory critique and primary-source overlap
comparison, then choose a genuine remaining mechanism. A model-validity theorem
alone does not satisfy the performance-cost requirement of the active goal.
