# Correct-prior, known-geometry scale boundary

The bounded transfer diagnosis is complete. The pair mechanism can lose its
advantage even when the Gaussian working gain prior and declared fixed geometry
are correct: at `N=64`, the singleton control has better realized log score
and Brier score on all three executed draws, and fewer aggregate bit errors.
Relative to scalar joint inference, results are metric-dependent: the pair has
better aggregate log score but slightly worse Brier/bit error at `N=64`, at much
higher local cost. These findings constrain the small-block claim; they do not
identify a single cause of the previously observed production failure.

## Frozen model and executed allocation

The separate `transfer_scale_contract.json` authorizes this mathematical check.
The earlier algorithms, production candidate and hyperparameters are unchanged.
The stage did not modify or replace `run_contract.json`, did not open a fresh
confirmation set, and did not invoke a production receiver or LDPC decoder.

- Sizes `N=4,16,64`, each with three independent draws; `P=2`.
- Independent uniform uncoded QPSK with per-symbol data energy 0.5.
- Independent `h~CN(0,I/2)`, exactly matching all arms' working gain prior.
- Pilot energy 0.5, complex noise variance 0.02.
- Declared known delay `[0,1]`, Doppler `[.23,-.38]`, chirps `.37/N`, `.13/N^2`.
- Per-case RNG seed `[20261003,104129,80,83,N,draw]`.

The known geometry is shared mathematical side information. This is neither
estimated production geometry nor a production oracle experiment. Input
observations are generated with the frozen real CPP physical operator. True
gain/data arrays are saved for generation provenance and external scoring but
never supplied as inference priors or used to construct the exact reference.

Three arms share each observation and declared geometry:

1. Frozen Gaussian pair pass, block size 2, uniform incoming LLRs.
2. Frozen Gaussian singleton pass, block size 1, uniform incoming LLRs.
3. Frozen `scalar_joint`, 20 iterations, damping 0.3, joint gain-uncertainty mode,
   data energy 0.5, uniform incoming LLRs, original time-domain computation.

Every arm pays the same observed pilot-only ridge initialization
`h_init=(B_pilot^H B_pilot+sigma2 P I)^-1 B_pilot^H y` and gets a channel container
with those gains. Scalar joint uses the initialization; pair/single retain their
fixed independent zero-mean Gaussian gain prior and correctly ignore these
container gains. Saved initial gain arrays are exactly equal across arms.
Observations/pilots are supplied in the DAFT domain; the existing scalar
`observation_domain='time'` option selects its internal unitary computation,
not a reinterpretation of the input convention.

Exactly **9 small-model scalar calls** and **27 total local detector calls** ran.
There were zero production/LDPC calls. Sizes use different independent samples;
equal draw numbers are not cross-size paired observations. Within each size,
the three draws—not the individual correlated bits—are statistical units.

## Realized probability and uncoded-error results

Log score is mean `log(1+exp((2b-1)LLR))` for realized generated truth, and Brier
is mean `(P(bit=0)-(1-b))^2`; lower is better. Errors use `LLR<0` as bit 1.
The table contains all samples, with no filtering or post-result retuning.

| N | Arm | Log score | Brier | Bit errors / bits | Uncoded frames with errors / 3 |
|---:|---|---:|---:|---:|---:|
| 4 | Pair | 0.480405 | 0.161564 | 5 / 24 | 3 |
| 4 | Singleton | 0.493503 | 0.163374 | 4 / 24 | 3 |
| 4 | Scalar joint 20 | 0.508932 | 0.168575 | 6 / 24 | 3 |
| 16 | Pair | 0.285572 | 0.095742 | 13 / 96 | 2 |
| 16 | Singleton | 0.337868 | 0.108627 | 17 / 96 | 3 |
| 16 | Scalar joint 20 | 0.416137 | 0.125762 | 16 / 96 | 2 |
| 64 | Pair | 0.158089 | 0.047897 | 24 / 384 | 3 |
| 64 | Singleton | 0.144379 | 0.042326 | 18 / 384 | 3 |
| 64 | Scalar joint 20 | 0.406064 | 0.046741 | 19 / 384 | 3 |

At `N=64`, per-draw pair/singleton log scores are
`0.229151/0.200817`, `0.096000/0.093891`, and `0.149117/0.138429`.
Singleton Brier is also lower on every draw. Pair bit errors are `11,6,7`;
singleton errors are `6,6,6`. Thus the loss of the pair advantage over its legal
control is observed under the correct prior and exact declared geometry.

Do not turn that observation into “scalar joint wins on every metric.” Scalar
has 19 errors versus pair's 24 and slightly lower Brier at `N=64`, but its log
score is worse in two draws and in the aggregate. Those are different quality
properties of the returned probabilities. Similarly, the pair's best aggregate
log score at `N=4` does not make it best in bit errors. The tiny sample does not
support a universal ranking or a significance claim.

## N=4 independent exact marginal check

For each `N=4` observation, the frozen dense exact oracle enumerates all 256
uncoded QPSK words and integrates gains under `CN(0,I/2)`. It receives no true
gains or true data. The expected marginal-approximation metrics are distinct
from the realized truth scores above:

| Arm | Mean per-draw LLR RMSE | Bit probability MSE | Expected Bernoulli KL |
|---|---:|---:|---:|
| Pair | 2.319536 | 0.046213 | 0.165735 |
| Singleton | 2.833425 | 0.052459 | 0.157446 |
| Scalar joint 20 | 3.157378 | 0.055965 | 0.155208 |

The pair has smaller LLR/probability squared error but higher expected KL in
these high-SNR examples. There is no general posterior improvement under every
proper score. This is compatible with the declared Gaussian moment likelihood
being approximate even though its second moments are exact in this working
model. No exact enumeration was attempted at `N=16` or `N=64`.

## Measured local cost and accounting

Each timed local call includes fresh geometry-container construction, the
identical observed pilot-only ridge setup, detector execution, and actual raw
NPZ output write. Scalar's 20-step trace JSON write is included as well. Input
generation, truth scoring, registration/hash checks, and the independent N=4
oracle are excluded from arm latency but included in whole-stage cost. These
are instrumented shared-machine local call times, not complete deployment
latency or an observed-geometry/LDPC pipeline.

| N | Pair mean wall ms | Singleton mean wall ms | Scalar joint 20 mean wall ms |
|---:|---:|---:|---:|
| 4 | 2.106 | 1.738 | 5.200 |
| 16 | 6.323 | 5.754 | 5.091 |
| 64 | 24.734 | 22.673 | 5.566 |

At `N=64`, pair local cost is about 4.44 times scalar's under this exact
accounting. The timing order was fixed and the machine was shared, so the
smallest timing differences should not be treated as isolated benchmarking.
The large cost separation is recorded rather than presented as a universal
hardware-independent ratio. The 20-iteration baseline was frozen; it was not
given extra iterations to manufacture a matched-budget comparison.

The whole stage completed in 0.268576 CPU / 0.270829 wall seconds under separate
30 CPU / 60 wall second timers. Effective thread-pool binding is one thread,
persisted in registration and checked again before completion. All 27 arm
start/complete events, 9 scalar traces, 39 NPZ files (9 inputs, 27 outputs,
3 exact references), source hashes and complete attempt receipt are retained.

## What this resolves and what remains unidentified

This check rules out the strong explanation that a pair-versus-singleton loss
requires a wrong Gaussian gain prior or wrong geometry: a loss occurs in the
executed `N=64` cases with both correct. It also shows that pair's probability
and cost tradeoff is not captured by its earlier tiny-model improvement.
Because each size has different random draws, it does **not** isolate increasing
N as the sole causal variable or establish monotonic accuracy degradation.

It does not reproduce or explain the entire production failure. The production
setting differs in coding/decoder interaction, physical normalized gain law,
path count and geometry distribution, actual support estimation and
initialization, chirps/frame conventions, and complete runtime components.
This uncoded, fixed-geometry check removes several mismatches together rather
than estimating each one's causal contribution. Distinguishing those
contributions would require registered comparisons holding the other production
inputs fixed; none is claimed or launched here. The exact-versus-Gaussian
likelihood gap, failure to exploit observations jointly across all data blocks,
and code interaction remain plausible mechanisms rather than identified root
causes of production FER.

The production rejection/confirmation decision is unchanged. This completes the
requested middle-size and correct-model boundary evidence without changing the
candidate, opening confirmation, or initiating a third message revision.

## Reproduction and verification

Source: `transfer_scale.py`. Immutable output:
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/transfer_scale_v1/`.
The script uses its own frozen contract and output directory; it does not
override the shared `common.run` contract or constants. An existing output
directory is rejected.

The executable checks require exactly 9 scalar / 27 local calls, finite LLRs,
identical observed initialization across arms, unchanged source hashes and
unchanged effective thread binding. Compilation and difference checks pass.
Saved-array recount verifies every reported truth score/error and the N=4
LLR RMSE without additional detector calls.
