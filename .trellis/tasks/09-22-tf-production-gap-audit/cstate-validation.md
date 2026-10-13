# Authorized follow-up: fixed CSTATE validation with complete stage timing

The user supplied CODEX_VALIDATION.md and the structural-state reference ZIP,
requesting stage-time decomposition and explicitly prohibiting optimization
of any stage during this run. This is a fixed realization/equivalence test
of the supplied compact formula. No adaptive optimization, tuning, new scorer,
new observations, paper claims or parameter sweep is authorized.

## Frozen inputs and scope

Protocol SHA256: 80afd6d46738ee4e3fa09d53bb523f97968f4a5e1f2574efd4e2327572130c73.
Preserve all earlier A+B+C and GLOBAL artifacts/code. New code and evidence:
experiments/tf_cstate_validation_20260922 and results/tf_cstate_validation_20260922.
Original numerical source2d130b4d/dependency31d5ec0d and prior observed seal
98e741ce5e827bf31e62e76e613a6719444fc81e6d47a9d2029c923b0bb912a8
remain bound. Prior geometry adapter SHA256 is
ad888de73a906d4167938a3391c288db68dd7edb4ec42da0d2e4598079ecf633.

Stage0: zero receiver calls; unmodified verify_and_probe.py and limiting_cases.py,
then full score/valid/accepted-choice/direct-optimum checks on all145 sealed
GLOBAL entering states. Verify production CPP conventions and fixed APP moments.
Retain previous stricter production absolute tolerance2e-10, rtol0 for adapter
parity; original supplied reference tests retain their own published tolerances.
No loosening after failures. The unguarded extreme-condition diagnostic is not
a stability guarantee; declared observed-only direct fallback must reproduce
the control. Assertion/algebra failures are qualification failures, not fallback.
Shared local schedule must also match saved outputs without calling a decoder.
If qualification fails, stop before any receiver calls.

Stage1 only after Stage0 passes: exact same75 observation IDs/43 syndrome triggers
and32 forced controls;225 full wrapper calls, LOCAL20/GLOBAL20/CSTATE20.
Rotate arm order by sorted observation index. Each replays unchanged native
TF20R2 before one extra native TF20/LDPC50. No fourth arm or hidden warmup call.
Use actual P slots, original finite2575-atom bank, at most2 swaps, same2 local
passes, windows/tolerance/max16 trials, APP/check-extrinsic mapping and fresh TF
state. Complete full-grid/top20/local-trial evidence remains equivalent across
GLOBAL and CSTATE. Context initialization is separately timed once per campaign;
per-wrapper setup is included as in the preceding protocol.

## Actual production ordering overrides reference assumptions

The executed production adapter selects the minimum from stable full-grid
lexsort(score,slot,delay,Doppler), then applies its incumbent relative-decrease
guard. The supplied research control uses chunk-major/slot-major traversal.
They are not assumed identical near ties. Preserve the actual executed
production rule for both new GLOBAL and CSTATE; qualify near ties explicitly.
Keep original numerical arithmetic/local-refit behavior; only add instrumentation
and the prescribed compact structural implementation in the new module.

## Required cost decomposition

Measure disjoint intervals with monotonic perf_counter. Keep hierarchical
geometry details, but explicitly label nested totals and avoid double counting.

- Wrapper setup, unchanged baseline replay, baseline parity/evidence overhead.
- APP/check message preparation and observation transform.
- Geometry setup/refit; compact field construction; all-grid scoring;
  validity/selection/trace handling; accepted direct refit and changed K-row refresh.
- Discarded compact work and original direct fallback separately, with counts,
  reasons and durations; total structural time includes both.
- Shared local refinement, including rejected trials and endpoint work.
- Geometry finalization/diagnostics, channel construction, fresh TF, LDPC.
- Checkpoint serialization/hash, raw serialization/hash, and remaining bookkeeping.

Record decision-ready, complete-added-branch and complete-wrapper times separately.
Exclusive components plus explicitly measured residual overhead must reconcile
with their enclosing wall-clock intervals. Preserve raw durations, not only
means; report mean/p95/max and shares for the43 trigger frames and other cohorts.
Any unexplained timing gap is visible, not silently assigned to a numerical stage.
These measurements diagnose the bottleneck; do not optimize any stage in response.

## Execution, seal and acceptance

One CPU process, all BLAS/Torch/OpenMP1, CUDA hidden. All remote files/tmp/cache/
tmux socket under /data/guoyikun; no installs or frozen-source changes.
Each phase hard deadline3600s; evidence cap2GiB; no automatic retries.
Server deinlab and project path are explicitly registered in CLAUDE.md:87-99.

Commit observed output seal before a separate process reads truth. The analyzer
rehashes all outputs, checks source/config/selection and Git-show binding, then
recounts raw bits. It compares GLOBAL/CSTATE discrete edits exactly, shared-local
continuous outputs at established tolerances, and final decisions bit-exactly
on all75; check the original frozen GLOBAL/LOCAL outcomes as well.
Report expected31/43,15/23 and32 controls as equivalence checks, not new discoveries.
Evaluate .5/1s latest-ready checkpoint with baseline fallback, and all fallback
counts/cost. No new true-path-rank investigation is needed.

Acceptance: exact discrete/final-decision equivalence, qualified continuous
outputs, and mean CSTATE complete added branch<=.6s on43 triggers. Report p95/max
and deadline outcomes regardless. Failure stops the fixed configuration;
additional rescues/losses cannot be relabeled as a new mechanism. Preserve all
stage costs and stop after this experiment.
