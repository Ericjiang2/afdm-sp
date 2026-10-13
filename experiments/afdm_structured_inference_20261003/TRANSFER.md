# Fixed production-size transfer screen: candidate not admitted

The uniform Gaussian pair receiver did not pass the frozen continuation gate.
In all six development observations it had a coded frame error; both native
one-round and two-round controls decoded all six correctly. Its mean negative
log probability was 0.334168 versus native-two's 0.022781. The paired comparison
has zero rescues and six harms. Do not start MECH or FRESH/stream90 from this
screen. This rejects the current candidate for continuation under this contract;
it does not establish a zero effect or an impossibility for other pair methods.

## Prospective contract and evidence

Source/configuration/seed registration preceded generation in
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/execution/pipeline_development_v1/`.
The completed quote and its source hashes are bound into this registration.
There are three independently seeded exogenous clusters, each observed at 10
and 20 dB, and four fixed arms per observation: 24 actual complete calls. The
arm order rotates prospectively with observation index. This is a fixed
feasibility screen with three independent clusters, not a powered efficacy test.
The two SNR points within a cluster are paired, not independent replications.

The original generator, real continuous-Doppler CPP propagation and cached
LDPC n2048/dv3/dc6/seed20260726 are unchanged. N=1024, rho=0.5,
c1=0.00244140625, c2=1.9751241797117955e-7. All receivers received exactly
y/pilot/sigma2; truth was opened only after all 24 calls for external scoring.
Every arm received the same verified observed arrays. Across SNR within each
cluster, byte hashes of channel parameters, information/coded bits, pilot,
noiseless signal and registered normalized-noise draw agree. Reconstructing the
CPP observation with that noise gives maximum absolute error zero in all six
observations. Candidate gains remain geometry-front evidence, not an invented
Gaussian gain posterior or a reused independent prior.

## Saved-input probabilities and decoded decisions

Scores below are recomputed from saved clipped decoder-input LLRs, with
logP(bit0)/P(bit1) convention. Negative log probability and bit Brier are means
over bits and observations; lower is better. FER is coded frame error.

| Arm | Negative log probability | Brier | Frame errors | Information BER | Rescues / harms vs native-two |
|---|---:|---:|---:|---:|---:|
| native-two | 0.0227808 | 0.00638261 | 0/6 | 0 | 0 / 0 |
| native-one | 0.0612480 | 0.01793913 | 0/6 | 0 | 0 / 0 |
| pair | 0.3341683 | 0.10491722 | 6/6 | 0.10270182 | 0 / 6 |
| singleton | 0.3341987 | 0.10492206 | 6/6 | 0.10351563 | 0 / 6 |

No undetected frame errors occurred. Pair and singleton each had 1,252 coded
bit errors; information errors were 631 and 636 respectively. Pair's tiny
aggregate soft-score advantage over singleton supplies no native-utility
signal. Single-round native also succeeding means merely removing the second
native round does not explain the observed candidate failures.

| SNR | native-two log score / errors | native-one log score / errors | pair log score / errors | singleton log score / errors |
|---|---:|---:|---:|---:|
| 10 dB | 0.04556157 / 0 of 3 | 0.12249595 / 0 of 3 | 0.35912213 / 3 of 3 | 0.35918667 / 3 of 3 |
| 20 dB | 2.0612e-9 / 0 of 3 | 8.1777e-8 / 0 of 3 | 0.30921450 / 3 of 3 | 0.30921080 / 3 of 3 |

Per-cluster pair/native-two mean log scores are 0.3368276/0.0261571,
0.3362234/0.0199646 and 0.3294539/0.0222207. Pair has two errors in every
cluster and native-two has none. The full per-cluster and per-SNR Brier, BER,
rescue/harm and cost tables are in `summary.json`; all individual rows are in
`scores_from_raw.json`.

The registered gate is either (i) pair log score at most 0.98 times native-two
with no extra frame errors, or (ii) net rescued frames with no greater log
score. Both branches are false. No tuning, replacement observations, survivor
filtering, receiver retry or confirmation draw was used.

## Complete cost and runtime checks

| Arm | CPU mean / max / p95 (s) | Wall mean / max / p95 (s) |
|---|---:|---:|
| native-two | 0.11168 / 0.11487 / 0.11417 | 0.11194 / 0.11506 / 0.11448 |
| native-one | 0.06910 / 0.07030 / 0.07025 | 0.06923 / 0.07030 / 0.07029 |
| pair | 0.70903 / 0.71422 / 0.71368 | 0.70937 / 0.71458 / 0.71399 |
| singleton | 0.65085 / 0.65502 / 0.65481 | 0.65112 / 0.65593 / 0.65555 |

Each complete call includes load/hash checks, pilot/refinement, inference,
original decoder, operation instrumentation, finite checks and durable raw save.
There are only six timings per arm; these empirical p95 values are not reliable
population tail estimates. Different schedules and measured costs are not
matched-budget evidence.

The supervisor records **21.394898 cumulative child CPU / 21.908510 wall
seconds**, below the 300/420 resource limits. The worker alone records
11.447223 CPU / 21.705431 wall seconds; use the supervisor numbers for complete
process cost. Shared setup was 1.573021 worker CPU / 11.816225 wall, including
one context build; generation was 0.527274 / 0.533972. During setup Matplotlib
created a temporary font cache because the default directory was unwritable;
startup/helper cost is retained in the supervisor total, not removed as an
outlier. A subsequent saved-evidence audit cost 0.053434 CPU / 0.058726 wall
seconds and made no additional receiver or generator call.

Torch intra/inter-op and Apple Accelerate effective threading were verified at
one, with CUDA hidden. Process peak RSS was 537,427,968 bytes including setup,
generation and scoring; no isolated per-arm peak is claimed. Actual receiver
operation totals are 24 pilot fronts/515-column dictionaries, 30 geometry
refinements, 18 scalar passes, 12 Gaussian passes, 30 LDPC calls, 9,216 Gaussian
blocks and 73,728 local-word likelihoods. Instrumented NumPy operations include
12,774 IFFT calls, 414 FFT calls (25,524 vector transforms), 114,589 solves and
82,944 Cholesky factorizations. These count the named observed API sites; they
do not claim to expose every internal Torch or native-library operation.

All 268 bound source/evidence files remained unchanged. Started/completed
receiver ledgers both contain exactly 24 calls, with no failed attempts.
`readonly_audit_v1.json` independently reloads the NPZ artifacts and cached
code matrix, verifies observed/truth seals and source/raw hashes, and recomputes
aggregate scores, FER, BER and undetected errors to 1e-14 tolerance. The adapter
interface's three mock tests, pure allocation/seed checks, five gate-boundary
cases and syntax checks passed before execution. No production effect is
inferred from those mock or static checks.
