# MESSAGE-R1: bounded two-symbol factor messages

The registered pair revision reduces the local data-integration error in the
executed small cases. At `N=2` it recovers the exact discrete marginal; at `N=4`
it improves on a single-symbol version in all three draws but leaves material
error from the omitted outside-block uncertainty. A complete `N=1024/P=8`
single-pass arithmetic quote was admitted after a preliminary estimate and
actually completed three times. This is positive evidence for the bounded
block mechanism, not evidence of complete receiver utility.

## Registered scope and probability object

This revision was authorized by the task-local
`message-r1_registration.json` before implementation/execution. The stage is
`execution/message_v2`; stream is `[20261003,104129,80,61]`, with three fresh
draws per small size. No old source, previous raw output, Mission CSV, physical
generator, production receiver, or decoder was modified or rerun.

The method uses independent `h~CN(0,I/P)`, noise variance 0.2, per-symbol pilot
energy 0.5, and QPSK data energy 0.5. Chirps `c1=.37/N`, `c2=.13/N^2` deliberately
exercise nontrivial CPP phases and are **not production-setting evidence**.
Within each disjoint adjacent block of at most two symbols, all 16 QPSK symbol
pairs (or four singleton letters) are integrated exactly. Incoming bit factors
are applied only within the block. Every outside data coordinate is held at
zero, and later blocks do not consume earlier block outputs.

The outside reference is an explicitly declared **deterministic continuous
cavity**. Zero is not in the QPSK alphabet, so it is not a legitimate
finite-QPSK prior or a positive-probability conditioning event in the full
discrete model. The reported local probabilities are normalized factor
messages under that continuous-cavity approximation. Calling them exact global
QPSK marginals would be wrong. Observation-dependent gain estimates and scoring
truth are never supplied as an independent prior.

`PairLikelihood(model,y,pilot)` prepares a likelihood-only kernel using the
same frozen physical transforms, CPP time-path operators, and Gaussian support
factor as `CollapsedModel`. It explicitly rejects nonzero gain means rather
than silently ignoring them. Complex correlated and singular zero-mean gain
covariances use the support factor without jitter. `pair_pass(...)` returns APP
and extrinsic LLRs in the project's all-I, then all-Q bit order.

For one local block, form `T(a)=T0+a1 T1+a2 T2`, with `Tj=B(e_j)L` and
`T0=B(pilot)L`. Precompute `G_rs=T_r^H T_s` and `b_r=T_r^H y`. Each of the 16
letters then needs

```text
G(a) = sum_rs conj(a_r) a_s G_rs,  a_0=1
b(a) = sum_r conj(a_r) b_r
Q = I + G(a)/sigma2
log p(y|a, external=0) = -N log(pi sigma2) - ||y||^2/sigma2
                       + ||chol(Q)^-1 b(a)/sigma2||^2 - logdet Q.
```

Only the local arithmetic is shared; no full data-word bank is built in the
1024-dimensional pass. The 256-word `N=4` enumeration is explicitly the tiny
oracle reference. Recipient-edge exclusion is exact for the declared local
factor: subtract its own incoming LLR after finite summation.

## Local mathematical evidence

There are three fresh samples at each of `N=2` and `N=4`, with `P=2`, delays
`[0,1]`, Dopplers `[.23,-.38]`, independent incoming bit priors, and matching
Gaussian gains/noise. The two sizes use distinct draws; do not pool the six
conditions as a production sample or claim a cross-size paired effect.

For every block and every local letter, the shared-Gram likelihood is compared
with frozen `CollapsedModel.evaluate` using the complete score/moment kernel.
The maximum difference is `2.49e-14`. Independent full-word marginals use the
frozen observation-space dense `exact_posterior`; no generated truth enters
that reference. The maximum outgoing own-bit dependence after varying only
its incoming LLR is `2.45e-15`.

The single-symbol comparator uses the same zero-external reference, prior,
observation, physical operators and likelihood kernel. It is not the earlier
prior-mode-conditioned comparator in `MESSAGE.md`, so these tables must not be
combined as one matched experiment.

| Size / method | Mean per-draw LLR RMSE | Bit probability MSE | Bernoulli KL |
|---|---:|---:|---:|
| N=2, single | 0.38614 | 0.007024 | 0.024253 |
| N=2, pair | 1.89e-15 | 2.09e-31 | numerical zero |
| N=4, single | 1.38189 | 0.029379 | 0.076908 |
| N=4, pair | 0.82547 | 0.010353 | 0.027822 |

The raw `N=2` KL mean is `-6.94e-18`, a retained floating point roundoff value;
it was not silently clipped to zero. For `N=4`, the individual pair LLR RMSEs
are `1.19985`, `0.86940`, `0.40716`; corresponding single-symbol errors are
`1.85555`, `1.72646`, `0.56366`. All three paired comparisons improve, while none
becomes exact. Three examples establish reproducible instances, not an accuracy
guarantee across channels or a confidence interval for production gains.

The registered prediction was therefore supported in its stated scope:
integrating the entire `N=2` data block removes the conditional/marginal gap;
restricting a larger word to pairs leaves a nuisance-distribution approximation.
No post-result tuning, different grouping, extra sweep, or support-bank expansion
was used.

## Actual complete single-pass quote

Before the full scan, measured setup was `0.414 ms` and one pair was `1.280 ms`.
The projected CPU time for three full scans was `1.966 s`; a factor-three safety
margin plus 20 seconds reserve fit the registered 180 CPU / 240 wall cap. This
decision and its inputs were saved in `preliminary_quote.json` **before** the
full scan. The three full scans then completed:

| Repeat | Wall seconds | CPU seconds |
|---|---:|---:|
| 0 | 0.556188 | 0.555575 |
| 1 | 0.553610 | 0.553594 |
| 2 | 0.557563 | 0.557555 |

Each pass independently includes model/prior/phase/cache setup, reference
transforms, all 512 disjoint blocks, all 8192 local likelihood evaluations,
1026 FFT/IDAFT calls, APP/extrinsic output construction, and the NPZ write of
inputs and outputs. The maximum shared-Gram versus full-evaluate difference
for all 16 letters of the first `N=1024` pair is `5.46e-12`. This is a size
canary, not a full dense likelihood recount for all 8192 letters.

Input vectors for the 1024-dimensional quote are exogenous arithmetic inputs,
not production-frame generation. Imports/input generation, observed-support
estimation, the native receiver's initialization and iterative state, LDPC,
and end-to-end communication scoring were not run and are excluded. These
are one-thread shared-machine timings, without a matched original-receiver
baseline. They establish actual single-pass arithmetic cost, not a performance
budget win. Whole-process cumulative macOS peak RSS was 77,185,024 bytes
(about 73.61 MiB); it includes earlier diagnostics and is not an isolated
incremental memory peak for this method. The entire registered stage cost
1.7381 CPU / 1.7395 wall seconds.

Sharing the local Gram does **not** make the whole scan one `O(N log N)` call.
Current streamed block construction costs `O(N log N + N P^2)` per block;
each block's fixed 16 solves cost `O(16 P^3)`. The complete disjoint pass is
`O(N^2 log N + N^2 P^2 + 16 N P^3)`, with streamed workspace `O(NP+P^2+N)`.
Eliminating more cross-block arithmetic would be a separate implementation
change requiring its own matched correctness/cost check.

## Admission recommendation and remaining scientific work

This revision is **not a no-go for local blocks**: it supplies exact local
factor arithmetic, a genuine small-model approximation-error improvement, a
finite executable pass, and measured full-pass arithmetic cost. It is a
reasonable component for a bounded downstream prototype experiment if that
prototype explicitly declares its zero-external approximation and its actual
comparison budget.

It cannot currently be represented as an exact or drop-in replacement for the
native receiver's whole joint update. The executed method does not produce or
update the native gain/Onsager state, does not supply an uncertain outside-block
cavity, and has not passed an actual decoder interface or comparison against
the native complete receiver. A deliberately separate one-pass detector could
send these approximate LLRs to a decoder, but its all-frame cost and utility
still require an explicit prototype contract and new evidence. The positive
tiny result alone neither proves that proposal beneficial nor prohibits it.

The identifiable remaining gap is outside-block integration, not a failure of
the local Gaussian gain elimination or the pair's extrinsic cancellation.
Any feedback revision should target that gap and preserve a legal common
message schedule; merely adding coordinate sweeps would mix additional cost
with a different conditioning approximation. Production selected-geometry
error, gain-prior mismatch, FER/undetected errors and complete budget curves
remain untested. This result does not exhaust possible block or collapsed
inference designs.

## Reproduction and verification

Immutable evidence lives in
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/message_v2/`:
registration, six small-case NPZs, first-large-pair reference NPZ, three complete
pass NPZs, preliminary quote, raw/results, attempt cost and bound source hashes.
The runner refuses an existing output directory, so completed evidence cannot
be overwritten by rerunning it.

Five focused tests pass: complex correlated-prior Gram versus full kernel,
N=2 versus independent exact marginal, recipient-edge exclusion and explicit
outside-bit independence, odd-size singleton handling/repeatability, and
rejection of unsupported/nonfinite inputs. Test command:

```sh
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python -m experiments.afdm_structured_inference_20261003.test_pair_message
```
