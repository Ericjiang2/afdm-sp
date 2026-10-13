# Runner review before production, 2026-09-23

Scope: `run_observed.py`, `test_observed.py`, and qualification receipt v3. No production wrapper call was made during this review.

## Findings (fixed by implementer during review)

- The first runner counted branch time only to decoder completion. It now records `branch_complete_seconds` through branch checkpoint, raw artifact, and decision record serialization, while retaining decoder-ready timing separately.
- Source binding initially omitted imported code and clean preflight imported BLOCK before its source path was available. The current binding covers 118 source/cache files and a clean-process preflight passes.
- The first runner could write a PASS seal after its final call exceeded the 2 GiB limit. It now checks the cap after each completed call and stops without a seal when exceeded.
- The first runner did not verify the producer observation hash or pin the approved control allocation. It now recomputes the producer's per-array identity and binds the canonical witness manifest SHA256.
- Qualification v3 adds an actually active reciprocal-floor case and compares BLOCK's returned gain covariance with the archived map; 95 synthetic checks pass.

## Findings (not fixed at this checkpoint)

- Critical Ruff `E4` still reports two multiple-import lines in authored runner/test code. Implementer has been notified.
- Final analyzer, Git-seal ordering, saved-output prefix equality, historical BASE parity, and production timing have not yet been reviewed or executed.

## Verification

- Clean `env -u PYTHONPATH` preflight: PASS, 100 scheduled calls, 118 bound files, 25 witnesses. This does not invoke a receiver.
- Conda `/opt/anaconda3/bin/python experiments/tf_cgr_mechanism_20260923/test_observed.py`: PASS for schedule, four-arm synthetic branch, numerical fallback, retained checkpoint/cost and post-call cap.
- Targeted mypy on runner/test with `--follow-imports=skip --ignore-missing-imports --cache-dir=/dev/null`: PASS. A normal cache directory triggered a mypy internal serializer error; disabling its cache completed the check.
- Critical Ruff `E4,E9,F63,F7,F82`: FAIL only on two `E401` multiple-import lines.
