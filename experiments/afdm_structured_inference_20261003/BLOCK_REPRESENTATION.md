# PRIOR-R1: the existing block receiver removes balanced-split sensitivity

**Supported in all six saved cases:** the unchanged existing `block_amp`
preserves UV/UUVV physical means, covariances, soft data and LLRs throughout
20 iterations, within the registered 2e-11 tolerance. The maximum LLR L2
difference is **6.7788e-15**. This is an existing remedy to the scalar
representation defect, not a new block-inference algorithm or a performance
claim.

## Registration, inputs and actual calls

The parent registered PRIOR-R1 before execution in
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/prior-r1_registration.json`.
The complete attempt is in that Mission's `execution/prior_v2/`: source/input
hashes, effective thread binding, 12 raw trajectories, a paid observer-off
control, six case records, final results and cost receipt. Entry point:

```sh
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python -m experiments.afdm_structured_inference_20261003.block_representation
```

The immutable stage refuses overwrite. The driver hashes all 24 prior_v1 raw
NPZ files, prior registration/results/attempt, the R1 registration, the actual
block source and physical/message dependencies. It also verifies the original
prior_v1 source hashes before using that evidence.

No new observation or random stream was generated. The three original
exogenous draws, six N=3 geometry conditions, pilots, y, noise variance and
actual saved initial gains are reused byte-for-byte. UV and UUVV start from
the same physical H to at most 2.31e-16 construction roundoff. Both have iid
slot priors that push forward to the identical physical CN(0,I_2/2) prior.
Both run 20 existing iterations, damping 0.3, zero incoming bit factors and
data power 0.5. Arm order alternates across seeds.

There were **13 actual block_amp calls**: 12 observed calls plus one separately
charged observer-off parity control. No scalar receiver was rerun, and there
were no production, decoder, remote, GPU or generator calls. All block source
bytes remain unchanged.

## Legal interface and observation

Balanced splitting needs no mathematical interface workaround. In each
representation the slot covariance I/P is positive definite, even though the
repeated physical response columns are rank deficient. The block update adds
that proper prior precision before its Cholesky solve, so duplicate columns
do not require jitter, pseudoinverse substitution or a hidden fallback.

The existing `Basis` and `block_amp` are called directly. Transparent wrappers
observe FFT calls, gain solver outputs and the four-symbol marginal function;
they return the original outputs without altered arithmetic, then restore all
patched function names even on exceptions. Recorded state arrays contain each
iteration's gain mean/covariance, data mean/variance and bit APP/extrinsic.
The separately paid plain call has **bit-exact equality** in all six final
array fields, the full trace and iteration count. Instrumentation overhead is
included in observed arm cost, not disguised as deployed runtime.

Comparison uses T mapping `(a1,a2,b1,b2)` to `(a1+a2,b1+b2)`. Gain means compare
as T m, covariances as T C T^H, and H as the same physical operator action.
Nonidentifiable individual duplicate gains are not compared to unique gains.

## Results

| Saved draw / geometry | Scalar final LLR L2 gap (prior_v1) | Block first LLR L2 gap | Block final LLR L2 gap |
|---|---:|---:|---:|
| 0 / separated | 0.28708 | 0 | 2.02e-15 |
| 0 / same delay | 0.26451 | 0 | 1.05e-15 |
| 1 / separated | 0.84237 | 0 | 1.49e-15 |
| 1 / same delay | 1.19304 | 2.22e-16 | 3.77e-15 |
| 2 / separated | 0.06695 | 2.22e-16 | 3.82e-15 |
| 2 / same delay | 0.07175 | 0 | 1.26e-15 |

Maxima across every iteration of every condition:

| Physical/soft quantity | Maximum norm difference |
|---|---:|
| Aggregated gain mean | 1.213e-15 |
| Aggregated gain covariance | 2.990e-16 |
| Physical H matrix | 1.676e-15 |
| LLR | 6.779e-15 |
| Data mean | 1.426e-15 |
| Data variance | 5.468e-16 |

In particular, the first gain update differs by at most 7.89e-17, whereas the
scalar first-step difference was 0.00494–0.02174. The block mean/covariance and
its physical contractions conserve the aggregate information under duplication.
This supports the registered prediction that the scalar defect is avoidable
with the existing block map. Because block_amp also uses its associated block
response corrections, this comparison is not a surgical causal attribution to
one isolated covariance entry while holding all other formulas unchanged.

Representation invariance does **not** imply an exact posterior. The block
UV LLR error against the saved exact reference ranges from 0.28070 to 6.11005.
Relative to the saved scalar UV errors it improves four conditions and worsens
two. These are paired mathematical diagnostics from only three draws, not a
population advantage or FER result. No method or threshold was selected from
these six outcomes.

## Operations and complete observed cost

The observer counts actual function calls and also counts vector transforms
inside vectorized FFT calls; these are different quantities.

| Per 20-iteration call | UV (P=2) | UUVV (P=4) |
|---|---:|---:|
| FFT API calls | 140 | 220 |
| IFFT API calls | 140 | 220 |
| Complex vector transforms | 340 | 620 |
| Gain Cholesky factorizations | 20 of order 2 | 20 of order 4 |
| Cholesky solves | 40 | 40 |
| Basis dense solves / prior inverse | 2 / 1 | 2 / 1 |
| Four-symbol marginal calls | 20 | 20 |
| Observed complete wall range | 8.523–10.139 ms | 10.343–10.434 ms |

Observed per-arm cost includes Channel/Basis construction, phase/path work,
all block iterations, instrumentation copies and raw NPZ saving. It excludes
shared input loading/hash validation, which are included in the whole stage.
The observer-off control consumed 8.003 ms, separately accounted. The complete
stage used **0.19938 CPU seconds / 0.20031 wall seconds**, below 90/120 seconds.
Process peak RSS reached 72,990,720 bytes on macOS; it is a shared cumulative
high-water mark, not isolated per-arm memory.

Equal 20-iteration schedules plainly do not mean equal computation: redundancy
raises transform count and gain solve order despite equal physical outputs.
These tiny shared-machine measurements are not a matched production benchmark.
The historical scalar's 41-transform ledger cannot be converted into a speedup
claim by comparing it with these instrumented timings.

## Admission update and validation

The PRIOR scalar defect no longer supplies a novel algorithm merely by proposing
a full gain block: the project already has a block implementation that removes
the tested defect. A new candidate would need an additional identified gap,
such as general singular-prior support or a cheaper representation-conserving
arithmetic path, and its own evidence. No such additional implementation was
run here. This does not invalidate COLLAPSE, ORBIT, JET or learning targets.

`test_block_representation.py` passes four checks: changed-input rejection,
observer restoration after a deliberate exception, all six saved trajectory
recounts with exact operation counts, and raw observer-off bit parity. Tests
recount saved arrays and do not make another receiver call. The source/input
registration hashes remain valid. General nonuniform/singular coordinate priors
are outside this balanced-iid R1 test; they are not silently claimed supported.
