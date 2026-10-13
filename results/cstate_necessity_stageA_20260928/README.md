# CSTATE necessity — developmental Stage A, 2026-09-28

**Finished receiver campaign:** 1024 archived observations, A/B/C/D each1024 plus12 matched LOCAL calls;4108/4108 successful,0 numerical failures,0 new observations. Registered `c89b7a58`; observed outputs sealed before truth at `7f670af0`; primary analysis frozen before independent recount at `c829c89e`.

**Result:** A F0+TF40 errors; B F0+TF+CSTATE6; C F1+TF12; D F1+TF+CSTATE0. C absorbed26/34 original B-only rescues but costs1.84× B in complete mean. LOCAL rescued11/12 C failures, versus12/12 for CSTATE. Stronger acquisition did not replace B; the whole continuation still helps after F1, while a general global-reopening advantage over LOCAL remains unresolved. This is developmental evidence, not fresh confirmation.

## Question → answer → evidence

- **Can a stronger initializer replace CSTATE?** [Decision and fixed gates](STAGE_A_DECISION.md) → [full results](STAGE_A_RESULTS.md) → [frame outcomes](analysis/frame_outcomes.csv) and [complete/component timings](analysis/component_timing.csv).
- **Does global reopening add more than another continuation?** Decision's C-vs-D and D-vs-LOCAL rows → [paired tables](analysis/report.json), `local_on_C_triggered` → [structural diagnostics](analysis/structural_diagnostics.csv). Never infer a global mechanism from the12-vs0 contrast alone.
- **Were observations, code and comparisons matched?** [Registration](EXPERIMENT_MANIFEST.json) → [source review](INDEPENDENT_IMPLEMENTATION_REVIEW.md) → [execution receipt](PRODUCTION_EXECUTION_RECEIPT.json) → [Git-before-truth proof](OBSERVED_GIT_ATTESTATION.json) → [provenance](PROVENANCE.json).
- **Where are exact saved decisions and remote raw?** [Observed seal](observed/observed_seal.json) binds every saved file; [raw SHA256/MD5 inventory](raw_hash_inventory.json) gives full remote paths. Raw remains on `deinlab`, under `/data/guoyikun/00inbox/AFDM-channel-estimation/results/cstate_necessity_stageA_20260928/observed/`.
- **Can the numerical result be independently reproduced from saved outputs?** [Independent recount](independent/recount.json) → [field-by-field comparison and coverage](independent/COMPARISON.json). This independent pass adds zero receiver/decoder calls; metrics not independently recounted are explicitly distinguished from matching metrics.
- **What changed from the earlier A4 audit?** [Original lineage audit](../cstate_necessity_audit_20260925/CSTATE_ACQUISITION_LINEAGE_AUDIT.md) → [72-frame supplement](../cstate_necessity_audit_20260925/supplement/README.md) → frozen F1 below → this full-population developmental comparison. Outcome absorption does not establish causal shares of earlier grouping loss.

## Frozen request and method

- [User request](USER_REQUEST.txt) and [request provenance](REQUEST_PROVENANCE.json).
- [Task execution contract](../../.trellis/tasks/09-22-tf-production-gap-audit/cstate-necessity-stageA.md).
- [Arms, balanced order and complete clocks](ARM_DEFINITIONS.md).
- [Frozen F1](../cstate_necessity_audit_20260925/F1_NOMP_AFDM_SPEC.md), [equation/source map](../cstate_necessity_audit_20260925/F1_EQUATION_TO_SOURCE_MAP.md), [complexity ledger](../cstate_necessity_audit_20260925/F1_COMPLEXITY_LEDGER.md), [Stage-A rules](../cstate_necessity_audit_20260925/STAGE_A_PREREGISTRATION.md).
- Predecessor: [72-frame acquisition lineage supplement](../cstate_necessity_audit_20260925/supplement/README.md), still A4. Partial grouping losses do not establish causal rescue shares or CSTATE necessity.

Search terms: CSTATE necessity; F1; NOMP; stronger initializer; front-end strength; Stage A; CSTATE complementarity; acquisition replacement; risk-cost frontier.

[Registered execution manifest](EXPERIMENT_MANIFEST.json), [real Git blob attestation](REGISTRATION_ATTESTATION.json), [remote qualification](F1_UNIT_TESTS_remote.json), [implementation review](INDEPENDENT_IMPLEMENTATION_REVIEW.md).
