# F1 compatibility profile and matched timing

Observed Git seal `64893916d5de5e81fd720946d666d9dbe313fb0d` (SHA-256 `067fa733bbc1ecf26fe25b843f95d556f191bebb9d7b2ce4fcd3dae67f0cebdb`); 2,112/2,112 complete wrappers, launcher exit 0. Inputs and equivalence checks: [receipt](F1_FAST_EQUIVALENCE_RECEIPT.json). Full quantiles/components: [CSV](F1_FAST_TIMING.csv). This analysis read only sealed metadata and ledgers, not truth or remote raw NPZs.

The producer compared all 1,024 Ccompat calls and 64 current Cref calls with same-frame sealed Stage-A C: ordered geometry, counters/stopping, eligible continuous arrays at `atol=2e-10, rtol=0`, intermediate vectors, and final bits. Every `reference_max_difference` is 0. Cref/Ccompat final decoded hashes agree on all 64 matched frames. All 1,024 B calls reproduced sealed B trigger and decoded-bit gates. This developmental-population pass does not explain or erase the earlier Cfast f197 counter failure (1002 versus 995).

| Population | Acquisition mean / p95 (s) | Complete mean / p95 (s) | Executed CSTATE branches |
|---|---:|---:|---:|
| full 1,024 · B | 0.0820 / 0.0987 | 0.3464 / 0.3874 | 40 |
| full 1,024 · Ccompat | 0.2743 / 0.2908 | 0.5583 / 0.5948 | 0 |
| matched 64 · B | 0.0818 / 0.0986 | 0.3624 / 0.5603 | 6 |
| matched 64 · Cref | 0.3643 / 0.3779 | 0.6337 / 0.6633 | 0 |
| matched 64 · Ccompat | 0.2736 / 0.2917 | 0.5565 / 0.5985 | 0 |

The last column counts executed conditional CSTATE branches, not native nonzero syndromes or information failures. Cref and Ccompat do not execute that branch by policy.

Prespecified matched-64 removable acquisition excess: **32.1%** = `(mean Cref − mean Ccompat)/(mean Cref − mean B)`. Matched-64 complete-latency reduction: **12.2%** = `(mean Cref − mean Ccompat)/mean Cref`, against the frozen 10% material threshold. These are ratios of matched-subset means. Full-1,024 Ccompat/B mean acquisition and complete ratios are **3.344×** and **1.612×**; the Cref n=64 tails cannot be read as n=1,024 tails.

Acquisition includes F1 construction/bank. Native includes acquisition, refit/TF/decoder and durable checkpoints; conditional B branch includes its checkpoint. Complete includes raw/decision writing but excludes ledger append and historical-reference comparison. Components are **overlapping, not additive**. The CSV gives mean/median/p95/p99/max plus minimum by component and paired difference. Maximum process-cumulative RSS was 714344 KiB, not isolated per-arm memory.

At 0.5 s (unscored): B 1008/1024 final checkpoint ready, 984/1024 complete; Cref 0/64 final checkpoint ready, 0/64 complete; Ccompat 147/1024 final checkpoint ready, 0/1024 complete.
At 1.0 s (unscored): B 1024/1024 final checkpoint ready, 1024/1024 complete; Cref 64/64 final checkpoint ready, 64/64 complete; Ccompat 1024/1024 final checkpoint ready, 1024/1024 complete.

Under the preregistered joint label, this is **F1-UNRESOLVED**: the 12.2% matched complete-latency improvement exceeds 10%, but only 32.1% of matched acquisition excess was removed, short of the >50% condition for `F1-PYTHON-BOUND`; the remaining cost is not isolated enough to claim `F1-INTRINSICALLY-HEAVIER`.

The earlier [17-call F1-only profile](../cstate_necessity_stageB_20260928/F1_PROFILE_REPORT.md) suggested repeated response work, Python duplicate checks and refit conjugation as implementation costs. The matched run establishes the current cost clock but cannot isolate the causal contribution of each micro-optimization. Correct/wrong ready, FER, BER and valid-but-wrong require the separately sealed truth analysis. No F2 conclusion is inferred.
