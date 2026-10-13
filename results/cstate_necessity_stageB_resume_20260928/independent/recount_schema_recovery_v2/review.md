# Independent recount v2 schema repair review

**Static GO; no saved-output recount result yet.** Reviewed `experiments/cstate_necessity_stageB_resume_20260928/independent_recount_five_v2.py` SHA-256 `d06c42f135c9d927b8c5a678ea230636fc3f3703bff5b7cfc4f61e6a9309e8fa` against the preserved reader SHA-256 `36d8bd7918a45a8664daf89115d5212a2d7742f837a8f52829f23e41e368b889`.

The sole behavior diff reads each primary arm's complete-latency distribution from `timing.complete_latency_seconds` during the existing comparison. The frozen primary `report.json` SHA-256 `dbc93d3df5b40e8ee16b7323da413df5c7e659801defda3b6fdf1ac76f729c16` has that nested distribution with `n`, `mean`, `median`, `p95`, `p99`, and `max`; it has no `timing.mean`. FER, BER, trigger, deadline, paired, branch-cost, memory, and raw/checkpoint-to-truth logic are unchanged by the diff. The reader adds no receiver or decoder execution path.

The three targeted frozen-schema tests in `test_independent_recount_five_v2_schema.py` SHA-256 `5f7596c48571686eae35d79794c04fb6085c203e9e99bb9042efb5c3193a5ab6` passed locally. This supports source freeze and one authorized offline run; it does not claim that run succeeded or that independent aggregates agree with primary results.
