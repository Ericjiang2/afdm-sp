# Injected research evidence context (read-only excerpt)

Authority: `.trellis/spec/backend/research-diagnostics.md`, SHA256 8c1ac82a9bd6299ea4cb96379aa460c2f66eafeadfcb77eecde2d6dd249da5a8. This is a transport excerpt, not a second spec. Scientific handoff overrides old campaign-specific qualification details for this new task.

# Research receiver diagnostics

## Saved BLAS input layout

For bit-exact replay of derived scalar scores, array values/dtype/shape are not
always sufficient: C/F storage order can select different BLAS reductions. If
serialization canonicalizes arrays, define and restore the producer's layout
before recomputing scores. Verify both layouts and producer parity on an
independent case. Preserve completed records and recover their audit; do not
rerun receivers or loosen score/selection equality solely for a storage-order
artifact. This is a numerical replay contract, not a scientific tolerance change.
Keep recovery/orchestration notes separate from the original scientific scope
payload when old terminal records assert scope equality. Bind both the original
failure and subsequent recovery failures; do not rewrite old result metadata to
make a recovery contract match.

## 1. Scope / trigger

Apply when changing the AFDM receiver's offline interventions, calibration caches,
frame provenance, experiment launchers, or result readers. Scientific thresholds
and sample sizes remain in the owning Trellis task, not this code specification.

## 2. Signatures

- `ClassicalJointUnrolled.forward(..., diagnostic_support_override=None,
  diagnostic_channel_override=None, diagnostic_data_override=None,
  diagnostic_support_observer=None)`.
- `load_prior(path, snr, N, *, l_max, k_max)` validates the calibration domain.
- `physical_cluster_weights(system, params, rounded=False)` retains one physical
  slot per path; `fit_physical_cluster(...)` fits observed pilot data only.
- `budgeted_support_eval --local-actions` reuses the existing one-round F2-P
  protected pruning/refit path for every member of one frozen candidate pool.
- `budgeted_support_analyze.read_matrix(base)` accepts completed, paired runs.

## 3. Contracts

- Default `None` hooks preserve the existing numerical path. Truth is confined
  to explicitly named oracle branches or external scoring/diagnostic observers.
- Support override is before cluster expansion; channel override is at the H
  consumed by BP; data override is only at the DA-LS feedback input. These are
  distinct interventions and must not be described as global oracle bounds.
- `P_actual` is the expanded Dirichlet entry count. `n_paths` limits nomination
  before cluster expansion. Report physical paths, unique atoms, nomination and
  actual expanded active support separately.
- Cache identity includes the physical configuration, dictionary `l_max/k_max`,
  sample count, candidate count, seeds, tensor shapes, finite values and hash.
- Array hashes include dtype, shape and contiguous bytes. Frame seeds alone do
  not prove paired observations. Cross-SNR reuse shares one exogenous cluster.
- Keep the original source checkout and every running source snapshot unchanged.
  Record source/checkpoint/LDPC/calibration hashes and actual CPU/CUDA binding.
- Background jobs have separate outputs, explicit deadlines, PIDs and exit codes.
  SSH protocol keepalive does not replace server-side process persistence.
- Concurrent instrumented diagnostic times are not isolated deployment latency.
- `mp_detect_bp_torch` accepts canonical torch sparse COO H as an explicit
  complete matrix representation. Require square scalar-valued COO, finite
  values, unique row-major in-range indices and a finite positive threshold;
  reject uncoalesced or compressed layouts. Implicit entries are zero. Reuse
  the dense path's edge message arithmetic and precision. Only the optional

## Frozen SP-AFDM evidence and complete-cost replay (2026-09-21)

### 1. Scope / trigger

Apply to the isolated `experiments/sp_afdm_frozen_20260920` driver, its resume,
seal, analysis and offline readers. Preserve the imported archive and each remote
source snapshot. Evidence corrections do not change the frozen scientific design.

### 2. Signatures

`evidence.save_artifact(path, payload, identity)` and
`load_artifact(path, expected_identity=None)` preserve numeric arrays plus typed
JSON metadata without pickle. `validate_run(run_dir, expected_identity=None,
require_complete=False, reconcile_orphans=False)` is shared by run/resume/seal/
analysis. `direction_receiver.terminal_decode(..., decoder_observer=None)` is an
optional observer of the existing single decoder call, not a second pass.

### 3. Contracts

Bind source/config/environment/phase/cell/frame, actual LDPC generator, explicit
RNG entropy components, and input/truth/arm hashes. Validate an existing run before
any writes or receiver context construction. A valid complete resume is a no-op.
Keep truth in generation and offline diagnostics; never pass scoring truth into
an operational receiver decision. Save the actual damped/masked I1 H as exact COO
on every frame; check dense canaries on the first two frames. Last LS gains are
not that matrix. Retain every decoder call and native round, input/APP/check,
iteration/syndrome metadata, successful checkpoints and failed-attempt time.

Complete cost includes failed work. Unknown failed-stage splits are explicit
`None`, never fabricated zero. All finite attempt times enter reference latency,
tie breaks and runtime summaries. A timely completed checkpoint remains eligible
after a later failure; future decisions do not qualify. Record whole-process peak
RSS separately from instrumented receiver latency and array storage.

On deinlab, new source/output/tmp/cache paths stay under `/data/guoyikun/`.
CUDA is hidden and BLAS/OpenMP/Torch use one thread. Existing `build()` owns the
one-time Torch inter-op binding; verify afterward rather than setting it twice.
No concurrently timed numerical jobs; preserve PID/deadline/exit/argv/environment.

### 4. Validation and error matrix

- Identity/hash/duplicate-key/ledger-artifact mismatch -> fail before reuse.
- Invalid frame count, NaN/negative/wrong-type time, inconsistent stage/round or
  checkpoint time -> explicit validation failure, no selection.
- Artifact/storage/programming error -> propagate, never label numerical failure.
- Numerical receiver failure -> retain actual elapsed work and allowed earlier
  checkpoint; unavailable raw bits stay missing in BER recount.
- Valid orphan artifact -> preserve for audit before an explicit rerun; never
  silently append it as a completed ledger decision.

### 5. Good / base / bad cases

Good: captured and uncaptured terminal calls have identical numerical outputs
and exactly one decode each. Base: complete original registration is required to
seal; a one-observation engineering screen cannot select families/cells. Bad:
drop failed runtimes, regenerate an old output under new source hashes, or report
posterior-mean signs as the original raw detector hard decisions.

### 6. Tests required

Focused evidence tests cover identity-before-write, complete-resume no-op,
corruption/orphans, exact array/metadata round trips, seed descriptions, stage and
round timing errors, fallback checkpoint eligibility and all-attempt costs.
Observer tests require on/off parity and exact decoder-call counts. Real driver
smoke separately checks saved-bit recount, APP=input+check, H COO/canary equality
and source identity. Synthetic tests are not communication-performance evidence.

### 7. Wrong versus correct

Wrong: average only successful runtimes; rebuild I1 H from the final gains; decode
again merely to recover APP. Correct: include every attempt, preserve actual H,
and observe the existing decoder output. Keep reporting scripts outside the
hashed frozen package so editorial changes do not invalidate receiver snapshots.
