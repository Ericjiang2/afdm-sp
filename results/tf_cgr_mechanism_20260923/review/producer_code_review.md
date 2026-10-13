# Observed producer code review, 2026-09-23

Disposition: **PASS for frozen producer code and preflight.** This is a code gate before the 100 planned wrappers, not an observed-result or scientific gate. No production receiver call was made by this reviewer.

## Findings (fixed)

- `run_observed.py` originally measured added branch time only to decoder completion. It now also records `branch_complete_seconds` through branch checkpoint, raw artifact and decision record serialization, including failed numerical branch work.
- Initial source binding omitted imported runtime modules, and BLOCK was imported before its source path was available. The current preflight hashes 115 executed native/baseline/geometry/CGR files and code cache; clean-process preflight succeeds.
- The runner initially checked its 2 GiB cap only before calls. It now checks after every call and refuses a PASS seal on overflow.
- The runner initially accepted an unbound control allocation and ignored the producer observation hash. It now requires the canonical witness manifest SHA256 and recomputes the producer's dtype/shape/bytes observation identity.
- Qualification now includes an active reciprocal-floor fixture and BLOCK gain covariance comparison with archived `block_amp`.
- Authored runner/test import style was corrected so critical Ruff passes.

## Findings (not fixed)

None in the reviewed frozen producer. Saved-output parity, observed sealing/Git order, deadline recount and five scientific gates require the planned execution and separate analysis.

## Verification

- Clean `env -u PYTHONPATH` preflight with v4 source binding, registration and qualification: PASS, exactly 100 calls, 115 files, 25 witnesses; output root was not created.
- Registration hash chain: archived protocol SHA256, canonical witness manifest, witness receipt, v4 source binding and v4 qualification agree. Qualifier file SHA matches the v4 receipt. The producer verifies generated scalar variants and BLOCK's archived source hash before calls. `register.py` and `qualify.py` are not imported by the producer and are separately receipt-bound; the offline analyzer is outside the producer import path.
- Local v4 qualification: 95 synthetic checks PASS, maximum recorded error `4.58e-14`; both supplied reference scripts executed. Active floor `vq=1e12`, floored delta error `4.44e-16`.
- Conda `/opt/anaconda3/bin/python experiments/tf_cgr_mechanism_20260923/test_observed.py`: PASS for arm schedule, four detector interfaces, APP/check separation, one LDPC50 call, numerical fallback/retained native checkpoint/cost and post-call cap.
- Critical Ruff `E4,E9,F63,F7,F82`: PASS on authored producer/test/register/freeze files. Targeted mypy with `--follow-imports=skip --ignore-missing-imports --cache-dir=/dev/null`: PASS on the same files. Python compilation: PASS on current producer modules.
