# Saved N1024 production diagnosis

This is a bounded diagnostic of the same six development observations from
`pipeline_development_v1` (three shared channel/message/noise clusters at
10/20 dB), not a new confirmation or independent six-channel FER campaign.
All original registration/source/checkpoint/population/raw hashes are retained
and verified. No original source/results are edited.

The predeclared allocation is 36 actual receiver and LDPC calls:

| Arm | Inner updates | Gain treatment | Outside treatment |
| --- | ---: | --- | --- |
| joint20 | 20 | observed initialization; native joint updates | native scalar approximation |
| pair | one block pass | zero-mean Gaussian prior; observed geometry | old Gaussian pair moment matching |
| joint1 | 1 | same observed initialization; native joint update | native scalar approximation |
| fixed1 | 1 | observed point estimate held fixed, gain variance zero | native scalar approximation |
| fixed20 | 20 | observed point estimate held fixed, gain variance zero | native scalar approximation |
| observed_H_pair | one block pass | same observed point estimate | conditional Gaussian outside |

`joint20` and `pair` are replayed against saved full numerical arrays for every
observation before any intervention. Integer/decoded results must agree
exactly; continuous values use predeclared atol=1e-9, rtol=1e-10 and all actual
nonzero errors are reported. The frontend observation-only arrays must be
bit-exact across arms. New native states are captured using the existing
`record_states=True` interface, and wrappers only observe API results.

The fixed-H block control builds the full observed channel matrix and factors
sigma2 I + .5 HH^H once. For each block it removes .5 H_B H_B^H by a positive
rank-1/2 downdate and evaluates all legal QPSK states with the complete
normalizing constants. This is exact arithmetic under a different conditional
Gaussian-outside point-estimate model. It is not exact QPSK inference, a legal
new independent prior derived from y, or an isolated Gaussianization test.
Its full matrix/factorization cost is recorded; no cheap production claim is
made. Independent small dense tests cover its normalized likelihood and LLR.

Within joint or fixed mode, 1 versus 20 iterations isolates internal update
count on identical frontend inputs. Fixed versus joint also changes gain
variance, so it is a compound intervention. Pair versus observed-H pair changes
the gain model and its use of the observation. Geometry error, normalized-gain
prior mismatch, outside-QPSK approximation, loss from moment matching and
iteration/feedback remain separate possible mechanisms. No one contrast can
assign the entire historical loss to a single Gaussianization.

Each actual call saves decoder input/APP/check/decoded arrays, frontend/gain
arrays, iteration state, operation calls, CPU/wall time and observation/hash
identity. Truth is opened only after every new call is durably saved, then used
for offline scores and a fresh recount of all 24 original raw outputs. Failed
calls and costs remain in the append-only calls ledger; partial output cannot
be promoted to a complete successful-subset result.

Run after the main session's source commit:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' \
/tmp/afdm-shared-channel-env/bin/python -m experiments.afdm_shared_channel_20261004.production_diagnostic production --stage production_v2
```

Wall cap: 1200 seconds. Local CPU only, no observation generation, SSH, GPU or
production edits. Setup and instrumented shared-machine timing are recorded;
they do not establish isolated deployment latency.

The first registered attempt `production_v1` stopped during bootstrap with
zero receiver/decoder calls (no calls ledger). The new harness omitted the
`effective_blas_post_bootstrap` record required by the old thread verifier.
The field is now populated by the actual `blas_binding()` immediately after
the actual frozen build, matching the old pipeline's caller contract; no
receiver or thread checker changed. A fresh-process test executes the real
checkpoint/LDPC/bootstrap/thread verification. The failed attempt (13.1723 s
wall, 2.5750 s CPU) and its original source snapshot remain preserved;
`production_v1_failure_receipt.json` records the cause and scope.

## Registered production_v2 results

All 36 receiver/decoder calls completed. All saved baseline numerical-array
differences were exactly zero, and the paired frontend arrays were bit-exact.
A fresh read of all 24 old outputs reproduced every saved score exactly.
The original native one/two outer rounds both have 0/6 frame errors; old pair
and singleton both have 6/6 and 1,252 total coded-bit errors.

| Arm | Frame errors / 6 | Total coded-bit errors | Mean input bit log-loss | Mean Brier |
| --- | ---: | ---: | ---: | ---: |
| joint20 | 0 | 0 | 0.061248 | 0.017939 |
| joint1 | 6 | 3947 | 0.638940 | 0.223260 |
| pair | 6 | 1252 | 0.334168 | 0.104917 |
| fixed1 | 6 | 2329 | 0.455659 | 0.145700 |
| fixed20 | 6 | 1635 | 1.007613 | 0.120496 |
| observed_H_pair | 3 | 619 | 0.278786 | 0.072837 |

The observed-H control decodes all three 20 dB rows and fails all three 10 dB
rows. Native 20-step joint inference succeeds on both SNRs. The fixed-gain
20-step control reduces bit errors relative to one step but worsens log-loss,
particularly at 20 dB; iteration is not uniformly beneficial across gain
models or metrics.

Saved state inspection confirms 1 versus 20 actual states, exact equality of
the first state within each joint/fixed comparison, fixed gain equality to
the observed frontend throughout, and nonzero joint gain changes. Thus the
internal iteration distinction is operational, not only a requested option.
This directly refutes treating an original one-outer-round success as evidence
that one detector pass should suffice. The observed-H improvement indicates
that fitted gains can matter to a different point-estimate detector; it does
not isolate the loss caused by replacing a shared-channel mixture by one
Gaussian. Three clusters remain a small developmental sample.

The recorded complete attempt cost is 14.0696 s wall / 14.0281 s CPU; the
36 actual calls including input loading and raw writes total 12.2927 s wall.
The separate failed v1 overhead is 13.1723 s wall / 2.5750 s CPU. No failed
work is silently excluded. Detailed records live under the task's
`execution/production_v2/{results,scores,baseline_parity,frontend_pairing,
paired_differences,saved_recount,attempt}.json`, with complete raw NPZs.
`production_v2_state_receipt.json`, `production_launch_receipt.json` and
`production_harness_fix_checks.txt` retain the additional saved-state check,
executed argv/environment/attempt handles and 15 passing tests.
