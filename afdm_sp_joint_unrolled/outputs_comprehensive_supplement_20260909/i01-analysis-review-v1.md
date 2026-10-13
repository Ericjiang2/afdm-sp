# I-01 development analysis review v1

## Verdict

The estimator signs and calls into the frozen statistics engine are correct, but
the analyzer needs one manifest-contract fix before it is used as the formal
I-01 development summary. It accepts a 48-entry `F_I` list with duplicate or
missing contrasts, and it accepts changed family alpha/recycling metadata.

## Verified behavior

- The analyzer refuses an audit unless `status == "passed"`, `F_audited ==
  3456`, and the proofs contain exactly the 192 blocks x 3 SNRs x 6 arms. It
  rejects duplicate proof identities and non-binary FER values.
- It produces 18 arm/SNR summaries from the current frozen manifest, then 45
  paired intervals and 3 interaction intervals.
- The paired sign is correct. For manifest arms `[first, second]` with
  coefficients `[1, -1]`, `W` counts `first=error, second=success`, `L` counts
  the reverse, and `paired_delta` therefore reports
  `FER(first) - FER(second)`. An in-memory complete fixture with `W=10, L=0`
  returned `delta=10/192=0.052083333333333336`, `n=192`.
- The interaction uses counts in manifest arm order and coefficients
  `[1, -1, -1, 1]`, so its point estimate and conservative linear CP interval
  have the registered sign. Every call uses `m=66`; unused slots are not
  numerically removed from the multiplicity penalty.
- The CLI hashes the imported `supplement_statistics.py` and rejects a mismatch
  with `deterministic_engine_sha256`. Output creation is exclusive. Its scope
  correctly labels all intervals as development descriptions and makes no
  confirmation, COST-02, selection, or deployability claim.

## Required fix

`analyze()` checks only `len(contrasts) == 48` after filtering entries whose arms
are inside the six-arm set. This does not establish the required inventory. A
synthetic mutation replacing the final interaction with a duplicate of the
first pairwise contrast was accepted and emitted 48 rows. The analyzer should
validate unique contrast IDs and the exact registered set: all 15 unordered
six-arm pairs at each of SNR 7/8/9 with `paired_CP` and `[1,-1]`, plus exactly
one `information_x_reallocation` interaction at each SNR with arms
`[I0,I2,Irealloc,I2realloc]`, coefficients `[1,-1,-1,1]`, and `linear_CP`.

The family guard also checks only `m_used_after_selection == 66`. In-memory
mutations setting `F_I.alpha=0.5` or `unused_slots_recycle_alpha=true` were both
accepted; the first directly changes every CI and the second contradicts the
frozen no-recycling contract. Require the frozen `alpha=0.05/7`, `m_max=66`,
`m_used_after_selection=66`, and `unused_slots_recycle_alpha is false` before
computing intervals. These checks should live in `analyze()` as well as any CLI
hash gate so direct callers receive the same contract.

## Limits of this review

This was a read-only code/contract review plus in-memory synthetic evaluation.
It did not read the remote 3456F result, rerun a receiver, or recompute the
completed raw audit. The review establishes formula direction and present
manifest output shape; it does not turn development intervals into confirmation
evidence.

## Fix verification

The revised analyzer closes both required findings above.

- `validate_family()` now freezes `alpha=0.05/7`, `m_max=66`,
  `m_used_after_selection=66`, and `unused_slots_recycle_alpha=false` before any
  interval is computed.
- It requires 66 unique family IDs and derives the exact I-01 inventory from the
  six frozen arms: all 15 unordered pairs at each of three SNRs plus the one
  registered interaction at each SNR. Every selected entry is checked for exact
  ID, ordered arms, coefficients, SNR, method, and nominal scene. A duplicate
  can therefore no longer replace a missing contrast while preserving length.
- The new synthetic suite covers the original family, duplicate replacement,
  each allocation mutation, each definition mutation, missing contrasts, the
  known `W=10,L=0` direction, and partial/missing/duplicate development data.
  Fresh review execution passed all 7 tests. Python compilation and diff checks
  also passed.

No remaining defect was found within the requested two-finding scope. The test
and analyzer import the project package, so direct execution from their nested
directory needs the repository on `PYTHONPATH` (the review used `PYTHONPATH=.`);
this is an invocation requirement and does not weaken the corrected family
validation. The scientific limitation remains unchanged: these are development
descriptions, not confirmation conclusions.
