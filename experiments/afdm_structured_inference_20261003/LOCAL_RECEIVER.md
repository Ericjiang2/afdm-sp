# Observed-input one-pass receiver and production-size quote

`local_receiver.receive` is default-off. Its disabled branch delegates directly
to unchanged `native_twofft.receive` and returns the original result. The enabled
branch runs the frozen pilot initializer, one soft geometry refinement (two
coordinate passes, at most eight observed delay groups), a uniform Gaussian pair
or singleton pass, and the original LDPC decoder once (input clip 20, maxiter 50).
Only y, pilot and noise are accepted; both vectors are in DAFT coordinates.

The gain prior is independently declared CN(0,I/P). Estimated gains initialize
the geometry front and are saved as CE evidence; they are not a new prior or a
whole-frame candidate gain posterior. The candidate consumes exactly zero bit
priors and has no decoder feedback or inherited AMP residual/Onsager state.
The four schedules are fixed costed controls, not equal-budget comparisons.

## Validation and quote

Three mock-based interface tests passed: direct delegation without candidate
import, invalid observation/schedule rejection, and a single uniform-prior pass
using the original clipped decoder interface. Those are interface tests, not
production simulations. The independent real quote in
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/pipeline_quote_v1/`
then executed exactly five N1024 calls on one 20 dB observation. Direct native-one
and disabled replay agree byte-for-byte on all 17 numerical arrays, including
decoder messages, geometry and iteration evidence; only explicit timing fields
are excluded.

| Call | Complete CPU (s) | Complete wall (s) | LDPC calls |
|---|---:|---:|---:|
| native-one direct | 0.07309 | 0.09196 | 1 |
| disabled native-one replay | 0.06892 | 0.06911 | 1 |
| native-two | 0.11176 | 0.11191 | 2 |
| pair | 0.69888 | 0.69934 | 1 |
| singleton | 0.63506 | 0.63530 | 1 |

Complete call cost includes observation load, initialization, refinement,
inference, decoding, instrumentation and durable raw NPZ save. Source and
runtime registration, imports/context, physical generation, scoring and final
source checks are included in the worker total: 3.11191 CPU / 3.66806 wall seconds.
Setup was 1.34264 CPU / 1.87606 wall; physical generation 0.13783 / 0.13997.
The supervisor additionally records process startup/shutdown: 3.29042 child CPU
/ 3.91170 wall seconds. The stage used one effective CPU thread (Torch and
Apple Accelerate verified), one context build and the pre-existing hash-checked
LDPC cache/checkpoint. No cache rebuild, failed call or retry occurred.

All 264 registered source files remained unchanged. Actual operation counts,
decoder outcomes, proper scores, FER, BER, observed/truth artifacts and raw
messages are retained with hashes. Pair used 512 blocks/8192 local likelihoods;
singleton used 1024/4096. The whole-process peak RSS was 499,613,696 bytes;
it includes setup/generation and is not an isolated arm memory peak.

The measured development projection, including six observations, 24 calls,
setup/generation/output overhead, a factor of three and a ten-second reserve,
is 44.63407 CPU / 46.64036 wall seconds, below the frozen 300/420 caps. This
passes the cost gate only. One quote cluster is not an effect estimate, a
production efficacy claim, or confirmation evidence. Development and any later
continuation follow the independently frozen pipeline contract.
