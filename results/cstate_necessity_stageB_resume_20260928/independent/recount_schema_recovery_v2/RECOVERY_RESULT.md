# Five-policy independent recount: schema recovery v2

The authorized offline saved-output recount passed (exit 0). All 173 compared primary fields are exactly equal; **0 nonidentical fields and 0 nonzero numeric deltas**. No receiver or decoder was called and no new observation was generated. This is a scoped developmental comparison of the five admitted policies; it is not a production or broader-domain claim.

## Whole-population outcomes

Each policy uses the same 1,024 fixed 6.5-dB observations. FER denominator is 1,024; coded BER denominator is 2,097,152 bits (2,048 × 1,024). Decimal values below retain the JSON float representation.

| Policy | FER (errors / frames; value) | BER (errors / bits; value) | Triggered prefix | Executed branch |
| --- | --- | --- | --- | --- |
| F0 | 40/1024; 0.0390625 | 9579/2097152; 0.004567623138427734 | 40 | 0 |
| B | 6/1024; 0.005859375 | 1362/2097152; 0.0006494522094726562 | 40 | 40 |
| F0_LOCAL | 29/1024; 0.0283203125 | 7680/2097152; 0.003662109375 | 40 | 40 |
| F2T | 39/1024; 0.0380859375 | 11293/2097152; 0.005384922027587891 | 40 | 40 |
| F2E | 1021/1024; 0.9970703125 | 422368/2097152; 0.2014007568359375 | 1021 | 0 |


The original F0 trigger occurs on 40 frames. B, F0_LOCAL, and F2T each execute 40 branches; F0 and F2E have no admitted branch. F2E_LOCAL and F2E_CSTATE are **not admitted**, so their branch outcomes are unavailable, not zero-valued effects.

## Deadline decisions

At each deadline the columns are ready / correct / wrong-ready / missing, with denominator 1,024.

| Policy | 0.5 s | 1.0 s |
| --- | --- | --- |
| F0 | 1024/984/40/0 | 1024/984/40/0 |
| B | 1024/986/38/0 | 1024/1018/6/0 |
| F0_LOCAL | 1024/987/37/0 | 1024/995/29/0 |
| F2T | 1024/984/40/0 | 1024/984/40/0 |
| F2E | 0/0/0/1024 | 0/0/0/1024 |


The 0.5 s correct counts are F0_LOCAL 987 and B 986; at 1.0 s they are B 1018 and F0_LOCAL 995. These are results for this campaign and deadline clock.

## Complete latency and branch cost (seconds)

Complete latency covers the full paid chain. Population branch cost includes zero cost for frames without an executed branch; conditional branch cost uses only executed branches. A dash means that no branch was executed, so the conditional distribution is undefined.

| Policy | Quantity | n | Mean | Median | p95 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F0 | Complete | 1024 | 0.35432787159129475 | 0.35230544046498835 | 0.4072624042164534 | 0.43707329963101055 | 0.49423488485626876 |
| F0 | Branch/population | 1024 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F0 | Branch/conditional | — | — | — | — | — | — |
| B | Complete | 1024 | 0.3649903174027713 | 0.3544636364094913 | 0.4263380951480939 | 0.6761871245130896 | 0.7332913668360561 |
| B | Branch/population | 1024 | 0.010662445811476573 | 0.0 | 0.0 | 0.2860342325363307 | 0.3555617139209062 |
| B | Branch/conditional | 40 | 0.2729586127738003 | 0.27438432804774493 | 0.3077608067425899 | 0.3442797319870442 | 0.3555617139209062 |
| F0_LOCAL | Complete | 1024 | 0.362872761925928 | 0.3544636364094913 | 0.4263380951480939 | 0.6109774871170519 | 0.7373383853118867 |
| F0_LOCAL | Branch/population | 1024 | 0.008544890334633237 | 0.0 | 0.0 | 0.23651846924098208 | 0.3948049182072282 |
| F0_LOCAL | Branch/conditional | 40 | 0.21874919256661088 | 0.21670651843305677 | 0.2521658083191141 | 0.3450500628887675 | 0.3948049182072282 |
| F2T | Complete | 1024 | 0.9868371556874536 | 0.3544636364094913 | 0.4263380951480939 | 18.189146282130384 | 21.509435566840693 |
| F2T | Branch/population | 1024 | 0.6325092840961588 | 0.0 | 0.0 | 17.831641307934184 | 21.06518493499607 |
| F2T | Branch/conditional | 40 | 16.192237672861665 | 16.492259039892815 | 19.342460315208882 | 20.476251209406183 | 21.06518493499607 |
| F2E | Complete | 1024 | 15.630671752944409 | 15.66008400451392 | 18.092834301840046 | 19.34379535128828 | 22.05832066293806 |
| F2E | Branch/population | 1024 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F2E | Branch/conditional | — | — | — | — | — | — |


## Paired outcomes against B

| Pair | B only correct | Other only correct | Both correct | Both wrong |
| --- | --- | --- | --- | --- |
| B_vs_F0 | 34 | 0 | 984 | 6 |
| B_vs_F0_LOCAL | 23 | 0 | 995 | 6 |
| B_vs_F2E | 1015 | 0 | 3 | 6 |
| B_vs_F2T | 33 | 0 | 985 | 6 |


## Original F0-trigger cohort and memory

The prespecified original F0-trigger cohort has 40 frames. The three-arm annex below reports saved outcomes on those same frames; it does not select a new cohort.

| Policy | Information failures / 40 | Coded bit errors | Complete mean (s) | Branch conditional mean (s) |
| --- | --- | --- | --- | --- |
| F0 | 40 | 9579 | 0.3668548882706091 | — |
| B | 6 | 1362 | 0.6398135010444094 | 0.2729586127738003 |
| F0_LOCAL | 29 | 7680 | 0.5856040808372199 | 0.21874919256661088 |


The shared process campaign RSS high-water is **744,528 KiB** across 2,168 paid calls. It is cumulative `RUSAGE_SELF`, not an independent per-policy peak. The excluded F2E_LOCAL/F2E_CSTATE branch subgroup has no results to compare.

## Frozen provenance

| Artifact | SHA-256 |
| --- | --- |
| results/cstate_necessity_stageB_resume_20260928/independent/recount_schema_recovery_v2/F2_FIVE_OUTCOME_RECOUNT.json | 2fde7e112c1d163fc5009fefea546bad2a74a475a940f9ccbfb3aba035a1bea7 |
| results/cstate_necessity_stageB_resume_20260928/independent/recount_schema_recovery_v2/F2_FIVE_PRIMARY_EXACT_COMPARISON.json | 5985039e85b7d62d633a8a1fa655973e472d90fc32bc5d320c078f6f60c38f42 |
| results/cstate_necessity_stageB_resume_20260928/independent/recount_schema_recovery_v2/receipt.json | 36330ce408f12210917d58ee6d989805bd07b044da6a8d7ffb1ba8235f758a49 |
| results/cstate_necessity_stageB_resume_20260928/population_five_analysis_v2/report.json | dbc93d3df5b40e8ee16b7323da413df5c7e659801defda3b6fdf1ac76f729c16 |
| results/cstate_necessity_stageB_resume_20260928/F2_FIVE_PRIMARY_GIT_ATTESTATION.json | 1479074e1d7f6e9031d3774847af86436509250723969cb8b5281885b341fb9f |


Reader: `experiments/cstate_necessity_stageB_resume_20260928/independent_recount_five_v2.py` — SHA-256 `d06c42f135c9d927b8c5a678ea230636fc3f3703bff5b7cfc4f61e6a9309e8fa`. The primary attestation records the full seven-file primary inventory and Git commitments. The preserved earlier failed attempt remains separately archived; its output is not merged into these results.
