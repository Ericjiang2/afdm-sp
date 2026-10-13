# MESSAGE-R2: retain outside-block covariance

The final registered message revision supports admission of a bounded,
uniform-prior, one-pass detector candidate. Its likelihood is a declared
Gaussian moment approximation, not the exact QPSK marginal. On the executed
new `N=4` cases it improves soft probabilities over both the zero-external R1
pair and a legal single-symbol control. The mathematical limits and actual
single-pass arithmetic quote pass. Production FER and complete receiver cost
have not been tested by this stage and are not prerequisites retroactively
imposed on a finite prototype.

## Public interface and scope

`gaussian_pair_pass(model, y, pilot, incoming, block_size=2)` returns `app` and
`extrinsic`, both ordered all real/I bits followed by all imaginary/Q bits,
with `LLR=log P(bit=0)-log P(bit=1)`. Observation and pilot are **DAFT-domain**
vectors. The implementation reuses frozen `physical.daft`, `TimePathOps`, and
the R1 `PairLikelihood` observation/reference preparation. It performs internal
time-domain CPP contractions; it does not reinterpret a time-domain input as
DAFT or invent an independent time-domain QPSK prior.

Required working prior: `h~CN(0,I/P)`, independent uniform QPSK data of energy
0.5 and independent complex noise with variance `model.noise`. Incoming LLRs
must be exactly zero. Any nonzero entry, including `1e-15`, is rejected rather
than silently treated as uniform. `block_size=1` and `block_size=2` are the only
supported schedules; blocks are disjoint and there is one pass with no
feedback. Uniform incoming makes APP and extrinsic LLR identical.

Example for a later, separately registered observed-geometry candidate:

```python
model = CollapsedModel(geometry_channel, np.zeros(P), np.eye(P)/P, sigma2)
out = gaussian_pair_pass(model, y_daft, pilot_daft, np.zeros(2*N), block_size=2)
llr_for_existing_decoder = out['extrinsic']
```

`geometry_channel.gains` are not inserted as an observation-dependent gain
prior. Geometry obtained from the same observation would be a plug-in support
estimate whose selection error remains a separate approximation. No decoder,
observed-geometry estimator, native gain/Onsager state, or production receiver
is called here. The helper's `external_variance=0` option exists to verify the
R1 limit; the registered R2 method uses 0.5.

## Moment contract and two positive-definite factorizations

Let `E` select the current block of one or two DAFT coordinates, `a` its fixed
QPSK letters, and `x0=pilot+E a`. With unitary physical path operators `U_p`,
independent zero-mean gains of variance `tau_p=1/P`, and independent uniform
outside QPSK with variance `pd=0.5`,

```text
B = [U_1 x0,...,U_P x0]
C_rest = pd I - pd sum_p tau_p U_p E E^H U_p^H
S = sigma2 I + C_rest + B C_h B^H.
```

This is the **exact conditional second moment** of the physical observation
under those assumptions. The gain-dependent signal and outside-data term share
the same random gains and are not independent. Their cross second moment is
zero because outside data have zero mean. Replacing their sum with `CN(0,S)`
is the explicit Gaussian likelihood approximation; exact second moments do
not make that distribution exact. This method is also distinct from the
continuous Gaussian tilted integral evaluated in `MESSAGE.md`.

Define `alpha=sigma2+pd`, `A=B C_h^(1/2)`, and concatenate
`D=sqrt(pd)[U_p e_j sqrt(tau_p)]` over paths and block coordinates. Then

```text
S = alpha I - D D^H + A A^H
R = I - D^H D / alpha
C_base^-1 = I/alpha + D R^-1 D^H / alpha^2
K = I + A^H C_base^-1 A
logdet S = N log alpha + logdet R + logdet K
S^-1 = C_base^-1 - C_base^-1 A K^-1 A^H C_base^-1.
```

Because `D D^H <= pd I`, `R >= sigma2/alpha I > 0`. Thus the downdate and the
subsequent gain update each use an SPD Cholesky factorization. No indefinite
determinant signs, epsilon jitter, covariance clipping, or hidden fallback are
needed. The test suite covers repeated paths and CPP boundary delays as well.

Per-block preparatory contractions cost `O(N P^2 + P^3)` for at most two
coordinates, with a fixed 16-letter `P`-dimensional solve. Streaming all disjoint
blocks still costs `O(N^2 log N + N^2 P^2 + 16 N P^3)` in the present realization,
not `O(N log N)` for the entire detector. Workspace is `O(NP+P^2+N)`; full
N-by-N covariance matrices are used only for the tiny independent reference.

## Fresh mathematical results

The registration `message-r2_registration.json` preceded code execution. Seed
namespace is `[20261003,104129,80,62]`. At each of `N=2` and `N=4`, three fresh
independent uniform-data samples use `P=2`, delay `[0,1]`, Doppler `[.23,-.38]`,
noise variance 0.2, and pilot/data energies 0.5/0.5. Sizes have distinct draws;
the six rows are not a production cohort or a cross-size paired comparison.
Chirps `.37/N` and `.13/N^2` exercise nontrivial CPP wrap and do not establish
production-chirp performance.

Every pair letter is checked against an independent dense covariance likelihood.
The dense outside covariance is constructed by positively summing all outside
columns, without reusing the signed Woodbury expression. Its second moment is
also checked against uniform enumeration of outside QPSK symbols with analytic
Gaussian gain integration. All methods see the same `y`, pilot, prior and
geometry; truth is used only to generate an observation, never as an argument
to a candidate or reference inference call.

| Mathematical check | Maximum discrepancy |
|---|---:|
| Low-rank versus independent dense normalized log likelihood | 2.85e-14 |
| Dense covariance versus exact outside-QPSK expectation of second moment | 1.07e-15 |
| N=2 pair versus exact discrete marginal, worst per-case LLR RMSE | 9.36e-16 |

When the pair covers all `N=2` coordinates, `C_rest=0`: R2 reduces to the exact
collapsed likelihood, as required. Setting outside variance to zero at `N=4`
also reproduces R1 to test tolerance. The API rejects nonzero-mean, correlated,
or deterministic gain priors rather than falsely applying the iid formula in
a known-channel regime. Those other gain-prior regimes are outside this
restricted candidate; the generic `CollapsedModel` continues to support them.

The following metrics compare approximate bit posteriors with the independent
full discrete marginal. The table averages per-case metrics and retains all
three outcomes; no successful-case filtering or post-result grouping occurs.

| N / method | LLR RMSE | Bit probability MSE | Expected Bernoulli KL |
|---|---:|---:|---:|
| 2 / R1 zero-external pair | 5.62e-16 | 1.55e-32 | numerical zero |
| 2 / R2 covariance pair | 7.46e-16 | 3.22e-32 | numerical zero |
| 2 / R2 covariance singleton | 0.01491 | 0.00001353 | 0.00002933 |
| 4 / R1 zero-external pair | 0.72852 | 0.013153 | 0.042155 |
| 4 / R2 covariance pair | 0.29970 | 0.002301 | 0.005920 |
| 4 / R2 covariance singleton | 0.43290 | 0.005493 | 0.014246 |

Raw numerical-zero KL values can be slightly negative at approximately 1e-17;
they are retained, not clipped. R1 values above are fresh paired re-evaluations
on R2's uniform-prior data, not the nonuniform-prior R1 development table.

At `N=4`, R2 pair LLR RMSEs are `0.24539`, `0.24030`, `0.41341`; R1 values are
`0.63537`, `0.48750`, `1.06270`, and singleton controls are `0.37238`, `0.45490`,
`0.47142`. All three R2 pair results improve both probability MSE and expected
KL relative to both controls. This supports the registered prediction that
outside covariance addresses part of the omitted-uncertainty error. It does
not establish universal dominance, an exact likelihood, or a production effect
size from three examples. Higher-order outside-data/gain dependence remains
unrepresented by the Gaussian replacement.

## Complete arithmetic quote actually executed

The preliminary quote measured setup at 0.447 ms CPU and one pair at 1.943 ms
CPU (2.681 ms wall). Projected three-pass cost was 2.986 CPU / 4.120 wall
seconds. A factor-three margin plus a 20-second reserve fit the registered
180 CPU / 240 wall caps, so the admission decision was persisted before the
complete scans. All three scans completed:

| Repeat | Wall seconds | CPU seconds |
|---|---:|---:|
| 0 | 0.630645 | 0.630607 |
| 1 | 0.641074 | 0.641066 |
| 2 | 0.632189 | 0.632174 |

Every scan includes fresh model/prior/phase/cache setup, all 512 blocks,
8192 local likelihood evaluations, 1026 transforms, APP/extrinsic assembly,
and actual NPZ output writes. Whole-process cumulative macOS peak RSS was
78,249,984 bytes (about 74.63 MiB), including previous small diagnostics; it is
not isolated incremental method memory. The registered stage used 1.973249 CPU
/ 1.974458 wall seconds in total.

These one-thread shared-machine arithmetic inputs are not generated production
frames. Imports/input generation, observed support estimation and receiver
initialization, native iterations, LDPC, and communication scoring are excluded
because they were not run. There is no matched native-receiver speedup or
whole-chain latency claim. The three repeats use identical inputs to measure
repeatable arithmetic; they are not three independent communication samples.
Large-size dense covariance verification was not performed; mathematical
equivalence is checked on the independent small matrices and full-size calls
check finite outputs and executable cost.

## Admission and remaining interface limits

The method now has a lawful, named approximation object; small-model message
error improves under controlled covariance and block-size comparisons; its
full pass runs within the quoted local resource ceiling. It can therefore
serve as the sole detector in a **finite uniform one-pass + existing LDPC
prototype**, with observed geometry, the fixed working gain prior, actual
power conventions and a separately registered complete cost comparison. That
recommendation is an admission to testing, not a prediction of positive FER.

Nonuniform incoming priors cannot be inserted into the current whole-frame
method: outside means alter `B`, and nonuniform variances generally destroy
`pd I` minus a small-rank block. Correlated code beliefs require even more
outside covariance structure. Reusing the same observation through iterative
APPs would additionally require an explicit cavity/feedback contract. The
current API intentionally rejects that mode and does not claim native
Onsager/gain-state compatibility. A local factor's recipient-edge cancellation
is tested separately through `bit_extrinsic`; it does not license unsupported
nonuniform detector feedback.

This completes the second and final registered message mechanism revision.
Remaining prototype questions are observed-geometry error, physical gain-prior
mismatch, noise/power and decoder interface parity, full inference cost, and
FER/undetected-error behavior. They should be measured in the next admitted
task, not declared solved by this mathematical stage or used to erase the
positive local evidence.

## Artifacts and verification

Immutable evidence:
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/message_v3/`.
It contains registration/source binding, six small NPZs including every block's
dense and enumerated covariance, three full-pass NPZs, raw metrics, preliminary
admission quote, actual quote results, and the complete attempt receipt.

Six focused tests pass: independent dense and exact second-moment comparison,
N=2 exact limit, zero outside variance/R1 limit, explicit prior/input rejection,
repeated paths/singleton handling, and local own-edge cancellation. A first
pre-registration test exposed an input-type bug in the new dense reference:
real pilot arrays could not receive complex QPSK additions in place. Both
reference constructions now normalize pilot arrays to complex dtype, matching
the existing kernel boundary. The original failing test passes; no scientific
attempt was failed or overwritten by that development fix.

```sh
.mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python -m experiments.afdm_structured_inference_20261003.test_gaussian_pair
```
