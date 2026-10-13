# v2 serialization fix review, 2026-09-23

Disposition: **PASS for the focused code fix and local qualification.** This review does not authorize a new production campaign. The original first BASE call remains a charged failed call, with its partial evidence preserved and no observed seal.

## Findings (fixed)

- The original successful branch built `gram.group_multiplicities` with integer dictionary keys. Frozen `evidence.save_artifact` rejects non-string metadata keys; the first production call failed during raw serialization after saving three checkpoints. v2 changes exactly that dictionary comprehension to string keys.
- The prior synthetic branch test never serialized a successful branch. Its fallback test saved `branch=None`, so neither exercised the failing nested Gram. v2 adds actual `evidence.save_artifact`/`load_artifact` round trips for BASE, CGR, SHAM and BLOCK, each in full target and scalar control trace forms, plus decision JSON and ledger serialization.

## Findings (not fixed)

- None in the focused v2 producer fix. The synthetic test uses a stub geometry result; prior completed CSTATE evidence already exercised serialization of `asdict(geometry_result)`. No v2 production output exists, and no retry was performed by this reviewer.

## Verification

- Independent `diff -u` of old and v2 `run_observed.py`: one-line int-to-string change.
- Original frozen serializer failure reproduced with an integer-key Gram fixture: `TypeError: evidence metadata keys must be strings` before file creation.
- Conda v2 `test_serialization.py`: PASS, eight successful raw/decision/ledger round trips. v2 `test_observed.py`: PASS for schedule, four-arm branch interface, numerical fallback, checkpoint retention and cap.
- Clean no-`PYTHONPATH` v2 preflight with fresh registration/qualification/source binding: PASS, 100 scheduled calls, 115 bound files, 25 witnesses; no receiver call.
- Critical Ruff `E4,E9,F63,F7,F82` on v2 producer and new serializer test: PASS. Targeted mypy with cache disabled: PASS. The imported `qualify.py` retains intentional late imports after runtime path setup and is outside this focused lint result.
