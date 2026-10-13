# I-01 development runner implementation v1

## Outcome

Implemented the bounded I-01 development runner in
`afdm_sp_joint_unrolled/supplement_feedback_run.py` and retained/extended the
existing half-written contract test in
`afdm_sp_joint_unrolled/test_supplement_feedback_run.py`. No receiver, feedback,
oracle, schedule, generator, or terminal-decoder implementation was copied.
The runner reuses `SupplementData`, `BaselineReceiver`, `CodeFeedback`,
`DiagnosticCodeSymbols`, `UniformBPSchedule`, `terminal_snapshot`, the frozen
checkpoint builder, atomic JSON publication, source hashing, and error scoring.

The fixed identity is `(design block, SNR, arm)`. A batch explicitly covers
1--16 blocks and all three SNRs and six arms. The complete campaign domain is
`192 * 3 * 6 = 3456 F`. Reservations are immutable and atomically stored in
`i01-development-ledger` beside the supplied development protocol. Existing
identities cannot be retried or reclaimed automatically. The engineering quote
ledger is not read or modified.

## Exact development protocol contract

The CLI requires `--development-protocol` and `--quote`. The frozen development
protocol must contain exactly these fields and values (the quote digest shown is
the actual local artifact digest):

```json
{
  "schema": "supplement-I01-development-protocol-v1",
  "domain": "fixed6arms3snrs192blocks",
  "checkpoint": 1,
  "baseline_recipe": "B0-p2-s0.5",
  "arms": ["I0", "Irealloc", "Isham", "I1", "I2", "I2realloc"],
  "snrs": [7, 8, 9],
  "blocks": 192,
  "bp_counts": {"I0": 20, "Irealloc": 12, "Isham": 12, "I1": 12, "I2": 20, "I2realloc": 12},
  "outer_iterations": 10,
  "early_ldpc_maxiter": 50,
  "terminal_bp_iterations": 20,
  "final_ldpc_maxiter": 50,
  "total_F": 3456,
  "quote_sha256": "4b71d207bc4c303e599f7ee55da219040080efe63dfd4ac0d71f88d7c285b4ed",
  "quote_raw_audit_sha256": "3275492ff760b4b7f0f901dd1ea17109379d818a9c61f887a485c23ee8e61688",
  "scope": "single cost-selected checkpoint from at most two prelisted candidates; checkpoint4 failed, preserved; equal development budget; no confirmation authorization",
  "timing": "complete instrumented development F, including final LDPC; concurrent timing not COST-02",
  "cost_selection": "timing only on prelisted engineering blocks; no development FER used",
  "source_binding": "each batch source manifest is immutable and all batch reservations require identical bindings"
}
```

The runner independently verifies the quote content: `status=complete`,
`attempted_F=72`, checkpoint outcomes `{"1": 12, "4": null}`, and the quote's
explicit no-FER/no-COST-02 scope. The actual protocol at
`evidence/i01-development-protocol-v1.json` passed this validation and has SHA-256
`20374a21fb6c167fb4b8069097bf6ffc6dbc535f85658f0c36fe47d5f1fcd4ca`.

## Runtime and evidence contracts

The runner requires a finite future deadline, exact batch F count, explicit
output-byte cap, explicit CPU/CUDA device, Torch/BLAS thread count exactly one,
the frozen checkpoint hash, and immutable hashes for the data protocol,
development protocol, quote, checkpoint, and all Python sources. Requested CUDA
fails if unavailable; no CPU substitution occurs. Output directories are
created exclusively.

Each started call is published before receiver execution. A completed record
contains the paired frame input hashes, truth-label hashes/shapes, offline scoring,
baseline eligibility and initial-estimator evidence, actual schedule, ten outer
BP graph audits plus the final BP graph, nine actual CE audits, detector/CE/decoder
feedback consumer records, capacity/support traces, full receiver wall/CPU/peak
cost, separately labelled generation/construction/snapshot costs, and a terminal
NPZ. Dense CE arrays are represented by hashes of their actual dtype, shape, and
contiguous bytes rather than JSON lists. I2/I2realloc are accurately labelled as
one true-symbol CE intervention at `checkpoint+1`; their records require exactly
one consumption at outer iteration 2. Failures keep their original identity and
charged call/reservation and produce no automatic retry.

## Validation

Focused and adjacent feedback tests:

```text
MPLCONFIGDIR=/private/tmp/afdm-mpl \
  /private/tmp/afdm-supplement-validation-20260909/bin/python -m unittest \
  afdm_sp_joint_unrolled.test_supplement_feedback_run \
  afdm_sp_joint_unrolled.test_supplement_feedback \
  afdm_sp_joint_unrolled.test_supplement_feedback_adapter \
  afdm_sp_joint_unrolled.test_supplement_feedback_diagnostic \
  afdm_sp_joint_unrolled.test_supplement_feedback_schedule
```

Result before the final I0-schema correction: 20 tests passed in 0.259 seconds.
After correcting the real I0 schema (which legitimately omits
`code_feedback_records`), the runner/adapter/diagnostic/schedule subset passed 16
tests in 0.205 seconds. Python compilation and `git diff --check` passed.

One real N=1024 CPU smoke used `split=design`, block 0, SNR 8, threads 1, and
executed the six arms directly through the shared receiver, followed by
`validate_result_audit`. This was **six additional unreserved F calls** and must
be recorded after the fact in the owning accounting; it is not claimed as a
pre-reserved development batch. No terminal NPZ or standalone log was written;
the raw output remains in the task tool transcript. The command environment was:

```text
MPLCONFIGDIR=/private/tmp/afdm-mpl OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
/private/tmp/afdm-supplement-validation-20260909/bin/python - <<'PY'
# build_code, SupplementData(...).make_frame(system,'design',0,8),
# build_receiver(...,'cpu'), then all six BaselineReceiver calls
PY
```

Observed full-call wall times were I0 3.7063 s, Irealloc 2.7180 s, Isham 2.5841 s,
I1 2.5909 s, I2 3.4430 s, and I2realloc 2.6176 s. Every arm produced 11 BP graph
records, nine CE records, and one final-BP record. The four feedback paths each
produced 20 feedback records; I2/I2realloc each produced one oracle-consumption
record. `decode_ok` was true for all except Isham; this outcome was not used to
select or alter the schedule. These concurrent/instrumented smoke timings are not
COST-02 evidence.

A prior formal-style CPU runner attempt used the temporary copied protocol
`/private/tmp/i01-feedback-smoke-protocol-sol.json`, output
`/private/tmp/i01-feedback-smoke-20260909-sol`, and a ledger under `/private/tmp`.
It reserved 18 temporary-ledger identities. Read-only reconciliation shows three
started calls: `(0,7,I2realloc)`, `(0,7,Isham)`, and `(0,7,I0)`. The first two
completed and each has a frame JSON plus terminal NPZ; the third was interrupted
after its started record. `batch-failure.json` records `calls_attempted=3` and
`calls_completed=2` (its `active_identity` is null, so the third started record is
the identity evidence). The complete temporary directory and its reservation are
retained. It did not touch the authoritative development ledger. Accounting keeps
the full 18F reservation without reclaim and lists the separate six-arm direct
smoke as another 6F, for 24F conservative after-the-fact occupancy; the owning
engineering ledger is 122/128 after this reconciliation.

No confirmation data was accessed, no FER selected a checkpoint or schedule, no
remote execution was performed, and no Git commit was made.
