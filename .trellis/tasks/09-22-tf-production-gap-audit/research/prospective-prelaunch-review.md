# Prospective campaign prelaunch review

Reviewed the frozen prospective protocol, generator and receiver runner, analyzer, one-shot launcher, and the independent saved-artifact verifier before source registration. No blocking correctness or evidence-ordering issue remained at review close.

The launcher sequence checked was: commit the remote Git preregistration and verify its blob; check registered runtime versions; generate 3 × 1024 fresh observations; run 6,144 receiver arms; hash and commit the complete observed seal; verify the seal's real Git blob and registration ancestry; only then run truth-based analysis and independent recount. The launcher has no automatic retry. Its 32 GiB checks apply separately to generation evidence (observed plus truth) and receiver evidence, each after its phase; they are not a campaign-wide 32 GiB limit.

The independent verifier checks actual Git preregistration, observed-seal, and truth-seal bytes; sealed artifact inventories and generation ledger hashes; every paired input, receiver raw artifact, decision record, and checkpoint; information and coded bit errors and parity syndromes; trigger, fallback, deadline, timing, and outcome counts; and analyzer CSV/summary agreement. It independently obtains the primary 650-cell conservative upper bound by inverting binomial CDF and survival functions rather than calling the analyzer's statistics function. I aligned its checks and synthetic fixtures with the analyzer's syndrome-zero coded-wrong and information-correct coded-wrong fields.

Local checks actually run:

- `/opt/anaconda3/bin/python -m pytest -q experiments/tf_cstate_prospective_20260923/test*.py` — **24 passed**. These were synthetic tests, including seal-tamper and mismatch cases.
- `ruff check experiments/tf_cstate_prospective_20260923` — **passed**.
- `/opt/anaconda3/bin/python -m mypy --follow-imports=silent --ignore-missing-imports experiments/tf_cstate_prospective_20260923/verify_prospective.py` — **passed** for the independent verifier.
- `/opt/anaconda3/bin/python -m compileall -q experiments/tf_cstate_prospective_20260923` — **passed**.

This review did not generate real observations, invoke a receiver, access remote experiment data, or validate a real campaign outcome. Those claims require the sealed run and its post-run independent receipt.
