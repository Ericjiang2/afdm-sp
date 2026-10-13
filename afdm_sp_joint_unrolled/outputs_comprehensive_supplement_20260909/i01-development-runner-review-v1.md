# I-01 development runner independent review v1

## Verdict

The frozen six-arm development design, immutable 3456-F reservation ledger,
paired-frame hashing, complete receiver timing, and terminal evidence are
substantively implemented. The first formal 18-F launch should wait for the two
blocking audit defects below to be corrected and covered by focused synthetic
tests. No receiver simulation or remote operation was performed for this
review.

Reviewed artifacts:

- `afdm_sp_joint_unrolled/supplement_feedback_run.py`
- `afdm_sp_joint_unrolled/test_supplement_feedback_run.py`
- `evidence/i01-development-protocol-v1.json`
- `dispatch/launch-i01-development-v1.py`
- The existing feedback/oracle/schedule adapters needed to verify actual
  consumer and terminal boundaries

The protocol artifact is valid JSON and its current SHA-256 is
`20374a21fb6c167fb4b8069097bf6ffc6dbc535f85658f0c36fe47d5f1fcd4ca`.

## Blocking findings before launch

### B1. An interrupted full call loses its active identity

At `supplement_feedback_run.py:465-470`, `TimeoutError` and
`KeyboardInterrupt` are re-raised from the per-call body, but the immediately
following `finally` clears `active`. The outer failure publisher at lines
481-488 consequently writes `active_identity: null`, even though the call was
already charged and its `call-xxxxx-started.json` marker was published.

This violates the intended failure provenance: a deadline or operator
interruption during a receiver call must identify the charged `(block, SNR,
arm)`. Preserve `active` while an exception propagates to the batch failure
handler. Clear it only after the completed frame record or ordinary per-arm
failure record has been durably published. Add a synthetic interruption test
that reaches the outer batch-failure publisher and asserts the exact active
identity.

### B2. Legal arms read truth data before receiver execution

At `supplement_feedback_run.py:429`, every arm evaluates
`frame._truth["data"]` before calling `_controller`, even though `_controller`
uses this value only for I2/I2realloc. I0/Irealloc/Isham/I1 do not pass that
truth into the receiver, so this is not demonstrated numerical leakage.
Nevertheless it makes the recorded legal-arm `truth_access_level: none`
boundary weaker than claimed: the orchestration has already accessed the true
symbols before the legal receiver call.

Construct legal controllers without a truth argument and read
`frame._truth["data"]` only inside the explicit I2/I2realloc diagnostic branch.
Add a focused test with a truth-data accessor that raises for legal arms and is
read exactly once for oracle controller construction.

## Confirmed contracts

- `ARMS`, `SNRS`, and `identities()` fix exactly six arms, 7/8/9 dB, 192
  design blocks, and 3456 unique F identities. Batches contain 1--16 complete
  blocks and reserve exactly 18 F per block.
- The development protocol is exact-field validated against the selected
  checkpoint 1, BP allocations 20/12, ten outer iterations, terminal BP20,
  LDPC50, baseline recipe, quote digest, and both quote outcomes. The quoted
  checkpoint-4 failure remains represented as `null`; no FER participates in
  schedule selection.
- Reservations are atomically serialized under one shared locked ledger,
  reject overlaps or binding changes, cap the campaign at 3456 F, and are not
  reclaimed after failure.
- Every arm in one `(block, SNR)` group uses the same generated frame. Before a
  record is accepted, observed `y/pilot` and truth `H/info/coded/data/noise`
  are rehashed against frame metadata. Source, checkpoint, data protocol,
  development protocol, and quote bindings are rechecked throughout the run.
- Legal feedback and oracle diagnostics use separate adapter entry points.
  I2/I2realloc require one true-symbol CE consumption at outer iteration 2;
  legal arms reject diagnostic consumption. I2 follows the BP20 path;
  I2realloc composes the BP12 zero-feedback path.
- Accepted records require ten outer BP calls, nine post-initial CE audits,
  ten outer graph audits, one final graph audit, and the expected
  detector/CE/decoder feedback record counts. Final BP20 and terminal LDPC50
  execute inside the same timed receiver call.
- The full-call timer is synchronized around receiver entry through terminal
  decode. Generation, controller construction, and snapshot publication are
  separately labelled. Instrumented/concurrent timings are explicitly barred
  from COST-02 claims.
- Output directories are exclusive; deadline, exact F budget, one Torch/BLAS
  thread, explicit device, storage estimate, and frozen CUDA availability are
  enforced. Each call publishes a durable started marker before execution.
- Completed records contain error counts/denominators, terminal replay state,
  input/truth hashes, support and capacity traces, actual CE/graph consumer
  hashes, timing, source bindings, and terminal path/SHA-256/MD5. This is usable
  per-frame scientific and provenance evidence.

## Non-blocking limitations

- CE audit tensors are intentionally compacted to dtype/shape/content hashes.
  They prove array identity and the actual consumer chain but do not permit an
  independent offline rerun of each intermediate CE solve. Terminal NPZs do
  retain observed inputs, terminal channel/state, decoded bits, and truth bits;
  the deterministic frozen generator plus truth hashes supplies regeneration
  provenance for omitted truth arrays.
- The protocol freezes `early_ldpc_maxiter=50`, and the current exact
  `CodeFeedback` construction uses its default 50. Result validation checks the
  decoder event count but does not directly assert a serialized early-decoder
  max-iteration field. Source immutability currently closes this path; recording
  and validating the value would make the evidence more self-contained.
- If frame generation fails, all six reserved identities get failure records,
  while `calls_attempted` counts only receiver calls that started. This is a
  defensible distinction, but downstream aggregation must use reservations and
  `missing_or_failed_identities`, rather than interpreting `calls_attempted` as
  the total charged campaign budget.
- The outer launcher timeout starts 15 seconds after the runner's internal
  deadline, so the runner normally has time to publish its batch failure. A
  native CUDA call that does not return to Python during that grace period may
  still be terminated externally; in that case the durable call-start marker,
  launcher log, and `.exit` file are the surviving provenance.

## Launcher review

`launch-i01-development-v1.py` is bounded and consistent with the server
rules: all task outputs and scratch/cache paths are under the project data
tree, tmux uses the required `g_` prefix and project socket, the GPU UUID is
explicit, admission checks free memory plus the documented strong-collision
threshold, at most two matching task panes are admitted, disk headroom is
checked, the source manifest is verified, and the runner receives an explicit
deadline, storage cap, one thread, exact F count, and `cuda:0` after UUID
visibility binding. The generated shell persists stdout/stderr and the actual
exit status. Exclusive launcher artifacts and the runner ledger prevent an
implicit restart.

The 18-F first batch is a suitable bounded admission step after B1 and B2 are
fixed. Its result must still be treated as development evidence only; it cannot
authorize confirmation or a COST-02 conclusion.

## Re-review after blocker fixes

Both launch blockers are resolved in the reviewed runner revision.

- B1 resolved: the per-call interrupt branch now preserves `active` while
  `TimeoutError` or `KeyboardInterrupt` propagates. `active` is cleared only
  after a completed record is published or an ordinary failure is durably
  recorded. The new synthetic `execute()` regression forces I0 to run first,
  raises `KeyboardInterrupt` from the receiver, and verifies that
  `batch-failure.json.active_identity` exactly equals the durable started-call
  identity `[0, 7, "I0"]`.
- B2 resolved: `_controller(code, arm, truth_data=None)` requires explicit truth
  only for I2/I2realloc. The real `execute()` caller indexes
  `frame._truth["data"]` only in those two diagnostic arms. The same synthetic
  execution regression supplies a truth object whose every index operation
  raises, proving that the first legal I0 call reaches the receiver without
  reading truth. The direct controller test also rejects an oracle arm without
  explicit true-symbol input.

Fresh focused validation on the final reviewed files:

```text
python -m unittest afdm_sp_joint_unrolled.test_supplement_feedback_run
.........
Ran 9 tests in 0.058s
OK
```

This test is entirely synthetic and executes no N=1024 receiver simulation.
`git diff --check` also passed for the runner, test, preparation script,
launcher, and this review document.

The preparation script `prepare-i01-development-v1.py` also passes static
review. It verifies the uploaded archive digest before extraction, rejects
absolute and parent-traversal members, creates the source and input locations
exclusively, hashes every Python source in the extracted package, copies the
three frozen JSON inputs byte-for-byte with hashes, runs only the declared unit
test suites under the snapshot `PYTHONPATH`, and reports `reserved_F=0`. It does
not launch a receiver or reserve development identities. The launcher later
revalidates the generated source manifest, while the runner independently binds
all runtime Python sources and the copied inputs.

Final re-review verdict: no remaining launch blocker was found in the reviewed
runner, focused test, preparation script, or launcher. The first 18-F batch is
admissible as bounded development execution, subject to the existing live GPU,
disk, source-hash, and exclusive-output checks at launch time. The non-blocking
limitations recorded above remain unchanged.
