# P-02 qualification observability: bounded read-only audit

No source/snapshot modification, receiver replay, budget change, flag rewrite, or process action was performed. This note maps the missing refit diagnostics to the original P-02 requirements; it does not add a stationarity or independent-recomputation acceptance gate.

## Contract impact

`Supplement_pilot_run.make_record` preserves `baseline_eligible`, `initial_estimator`, the recipe, hashes, full-call wall/CPU/peak-GPU measurements, support/capacity/graph records, error counts and power metadata. It omits `channel_refit.diagnostics` **and** `baseline_stationary`. The saved terminal contains final H/gains/support and pre-refit outer `x_soft`, observations, terminal statistics and decoded bits, but no optimizer history or pre-refit gains/H.

The frozen Pmatched protocol requires qualification and complete cost in selection. It does not require that every original qualification decision be independently recomputed from retained optimizer traces. Therefore this omission does not, by itself, invalidate the original recorded `baseline_eligible` selection criterion or full-call cost measurements. It limits their audit strength: eligibility is a source-bound execution assertion, not independently reconstructed optimizer convergence. A selector/report must preserve that distinction. This note does not certify any not-yet-audited Pmatched frame or close P-02.

Pfixed uses B0-p2-s0.5 and never takes the terminal-refit path, so this omission has no refit-qualification consequence for Pfixed.

## Group versus bounded parameterization

| Family | Actual frozen qualification logic | What the retained fields support | What is missing |
|---|---|---|---|
| group-p3-s1 | Initial SBL convergence AND group refit `converged` | When initial convergence and eligibility are both true, source control flow implies the refit reported convergence. When the initial flag is true and eligibility false, it implies the refit reported nonconvergence. | Actual residual/relative-change history, iterations, stopping details and refit-specific diagnostics cannot be independently checked from the eligibility bit. If initial convergence is false, eligibility false alone cannot isolate the refit outcome. |
| bounded-param-p3-s1 and bounded-param-p2-s1 | Initial SBL convergence; completed fixed one-sweep refit is eligible even if not stationary | A successfully completed, source/hash-bound record establishes the declared bounded recipe was used and the returned result passed its normal runtime checks. | `baseline_stationary` is lost; eligibility true does **not** imply grid-coordinate stationarity. Query count/locations, center selection, selected basis/rank, and before/after refit hashes are not retained. |

The bounded-param path intentionally treats stationarity as optimization evidence rather than an additional runtime eligibility gate (`BaselineReceiver.run`). It would change the frozen criterion to reject these candidates solely because stationary diagnostics were not retained. Likewise, the group predicate may be reported as runtime-reported convergence, but must not be relabeled as independently recalculated convergence.

## What original artifacts can and cannot establish

With verified contract, source bindings, summary/frame hashes and raw terminal hashes, the existing artifacts support: exact arm/block/SNR/pilot identity and budget accounting; final support/capacity; observation and common-exogenous hashes; saved final H/gains; terminal decoding outputs and independent bit-error recount; declared simulation power result; and full receiver elapsed/CPU/GPU measurements. The timer surrounds `BaselineReceiver` construction and `run`, which performs initial estimation, refit when applicable, final BP, demapping and LDPC. Missing optimizer diagnostics do not remove those operations from measured complete-F cost. These measurements remain instrumented development costs, not isolated deployment latency or operation-count certificates.

The frozen algorithm/source can establish the prescribed query/iteration **caps and rules**, not the per-frame realized query sequence or optimizer history. Verify against the source snapshot named by the run's binding hashes; the live working checkout now contains later feedback-adapter changes and must not silently replace that frozen provenance.

Final y, pilot, x_soft, support and gains contain enough mathematical ingredients to assemble the final refit sensing matrix and evaluate some final-state residual/objective checks if separately authorized. Such a calculation would be a new final-state diagnostic, not recovery of the lost trajectory, not proof of the original stopping decision, and not recovery of bounded-search centers selected from unavailable pre-refit gains. No such calculation was executed here.

## Reporting boundary

Retain the original eligibility flags and original budget. Describe group convergence as runtime-reported/source-bound when inferred through the flag; describe bounded-param eligibility as fixed-budget algorithm completion plus initial qualification, with stationarity unavailable. Report full measured costs without inventing missing operator counts. Do not claim independent refit-convergence recomputation, bounded-search stationary solutions, or a newly verified optimizer trace. No rerun or new gate is recommended by this audit.
