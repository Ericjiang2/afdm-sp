# Deterministic verification contract, MATH-01

2026-10-07. Verify mathematical kernels before selecting a receiver prototype.
No new random observation, decoder, receiver, training, or confirmation sample.
This is not a performance experiment and cannot close the active goal.

## Objects and cases fixed before execution

Implement expected quadratic error, per-path continuous-Doppler coordinate
log-density up to its normalizer, and expected-Gram matvec/diagonal from
CONTINUOUS_VARIATIONAL_UPDATE.md. Reuse actual `physical.Channel` and `daft`;
do not redefine the observation model or time-domain QPSK.

Three deterministic geometries: (N,delays)=(8,[0,3]), (16,[1,15]),
(1024,[0,9]). For all, c1=5.3/(2N), c2=(sqrt(2)-1)/(2N^2), providing actual
nontrivial CPP wrap phases. Each independent path-Doppler factor has three
points: path0 [-.25,.05,.30], path1 [.41,.62,.88], weights [.2,.5,.3]. These
finite distributions are exact diagnostic inputs, not a discretized claim
about the production prior. Use positive nonuniform AF variances and complex
off-diagonal gain covariance. Specify the deterministic analytic arrays in
source before admission; no RNG or result-dependent case selection.

For N8 and N16, independently construct dense U from the actual Channel action
on basis vectors. Enumerate all nine Doppler combinations and compare the
quadratic expectation, expected Gram/diagonal, and conditional Doppler scores
at u=[-.70,-.37,0,.19,.52,.75,1.10] to the structured implementation. The
conditional score is checked up to one common additive constant. For N1024,
the independent reference uses Channel.apply/adjoint on each of the nine
combinations and no dense N-by-N matrix. Dense construction is forbidden there.

Also verify single-path isotropic data covariance/trace conservation against
the known wrong independent-copy factor and first-order random tangent. Wrong
models must exhibit their predicted nonzero defect; they are negative controls,
not competing receivers. Validate shapes, positive weights, Hermitian PSD gain
covariance and nonnegative data variances; invalid input raises explicitly.

## Acceptance and resource limits

Normalized error threshold: 1e-10 at N8/N16 and 1e-9 at N1024. Hermitian/PSD
roundoff threshold 1e-10 times max(1,norm). Retain every check, including any
failure. No precision or threshold changes after results. Three geometry
probes, zero new observations, zero receiver/decoder calls, seed='none'.

One admitted SSH stage, wall cap 180s, one CPU thread, CUDA hidden, peak RSS
cap 1GiB, output cap 16MiB. All remote writes, temporary files and caches under
/data/guoyikun. Source bytes committed and independently reviewed before GO;
isolated snapshot, read-only resource preflight, immutable recorder, source and
result hashes. Reuse the prior phase/coherent immutable protocol through a
private adapter instead of creating a new recording system. Do not upload
.trellis, STATE, research-assets or unrelated sources. Main supplies exact
source manifest and remote paths after implementation.

Save all small arrays and errors needed for independent recomputation. NPZ
stays out of Git; JSON/report and remote absolute paths/hashes become evidence.
Report complete stage wall/CPU/RSS, not a receiver acceleration. Source/static
review may precede this numerical stage; it is not a runtime PASS.

## Decision

If an identity fails, retain failure and fix/renew source admission before any
new stage. If identities pass, assess novelty and design a real matched-cost
receiver test under the original anchor. Mathematical correctness alone does
not select a Transactions-level contribution.
