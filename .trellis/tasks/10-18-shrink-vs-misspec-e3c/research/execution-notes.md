# E3c execution notes — 2026-10-18

Current priority: user requested E3c results first; broad old-campaign audit and sample-out mechanism work deferred.

## Engineering attempt 1

- Remote root: `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/tf_e3c_shrink_20261018/`.
- `test_e3c.py`: 3 synthetic tests passed in AFDM before the first real-key admission attempt; not a full gate or performance result.
- Attempt `out/gate/shard000.log` failed before receiver computation: canonical manifest path `sp_afdm_native_joint_20260921/src/twofft.py` does not exist remotely, where the frozen source uses `sp_afdm_native_joint_reviewed_20260921`.
- Root cause: new source-identity reader failed to apply the same documented relocation used by the upstream loader. Strict aliases and unchanged MD5 validation were added; no old receiver source or old output was changed.
- Shared budget ledger `out/budget/budget.json`: failed attempt charged 4.768141126260161 elapsed single-thread seconds. Preserve this ledger across every subsequent engineering/main attempt.
- No communication performance observation was produced by that failed attempt. Final gate uses a new root and the final frozen code; no source waiver.

## Local verification

- Shared `sampling.py`: 7 contract tests passed under bundled Python/NumPy.
- Aggregation and provenance tests passed locally. Final remote synthetic/unit receipts and final gate/main evidence are required separately.
- Main/campaign scientific results remain unproven until all 1200 keys pass integrity/parity and aggregation finishes.

## Engineering attempts 2–3

- `out/qualified_v1`: synthetic tests passed; unit provenance then refused the canonical receiver.py copy whose digest differs from the actually imported reviewed snapshot. No receiver computation. Fixed source identity to load actual P1 context and require its actual import path; no matching-copy fallback. Both coexistence and missing/wrong-loaded-path negative tests pass.
- `out/qualified_v2`: provenance and units passed. Eighteen of twenty real gate keys completed. Two stopped at the diagonal consistency check (shards 016/017): normalized-by-Gram errors 4.252996649034341e-17 / 2.7214914579444652e-17, but diagonal errors relative to tiny variance were 9.041766595688664e-12 / 1.0069743913351797e-12. The checker subtracted large Q and Gram matrices to recover a small variance term, amplifying floating-point cancellation.
- Fix strategy: compare the directly returned covariance component plus the declared extra ridge against SBL covariance; independently check Q closure on the Gram scale. Keep the 1e-12 invariant tolerance and the receiver computation unchanged. Preserve failed rows/logs/cost. A final same-source full gate is still required.

## Final qualification and main launch

- Source freeze: local commit `e1bfd013873a81cf1a6f3c2754a6e871726fa0c1`. Final numerical test has four tests including tiny-variance corruption negatives; aggregation four tests; provenance two tests. Shared sampling seven tests independently passed locally.
- Final root: `out/qualified_v3/`. G1 20/20 old-key replay, G2 covariance/ridge/oracle checks, G3 20/20 six-arm exact repeat, G4 twelve smoke keys all passed under one source snapshot. Forty-four local/remote source hashes match. `gates.json`, `unit.json`, `FREEZE.json` are copied locally.
- Smoke mean elapsed/key 23.70328806821878 seconds; main 1.3-contention projection 10.27142482956147 core-hours. Prior engineering and failures cost 0.6590389864864604 core-hours. Total limit remains 15 core-hours, single-thread processes, GPU hidden.
- Main started 2026-10-18 04:39:27 UTC (12:39:27 Asia/Shanghai), tmux `g_e3c`, 24 shards, fifty keys/shard. All use the existing shared `out/budget/` ledger and a 2149-second lease per process. `out/chain.log` confirms freeze/gates verification; 24 raw row files and actual driver processes were observed.
- Completion requires `out/qualified_v3/STATUS=complete`, complete 1200-key summary, no error rows, full baseline replay, unchanged source hashes, cost ledger, raw/compressed SHA manifests, and the independent saved-result check. No partial performance result has been interpreted.
- Resume: read the actual tmux/process/STATUS and logs at the remote root before any launch. Never restart a missing/slow observation handle without verifying the original job state. Final read-only checker belongs outside the frozen E3c source directory.

## Final completion and saved-result verification

- Main completed 2026-10-18 05:03:19 UTC (13:03:19 Asia/Shanghai). STATUS=complete; 1200/1200 paired keys, 100 independent RNG frame clusters; zero main error rows. tmux g_e3c exited normally. No restart or additional receiver experiment.
- Source freeze stayed unchanged. Independent checker e3c_result_check.py (outside frozen source) passed seven contract tests and verified all raw/config/source manifests plus 318227 numeric and 507 Boolean/null summary leaves. CI checking reuses the audited sampler; this is independent saved-result reduction, not an independent receiver rerun.
- Summary SHA256 e0f233c7e79f87bdb2b8820552e61aeea790fdcb5d041bbc455e641d8eaa1be1 matches local copy. Raw rows remain remote; RAW_SHA256, COMPRESSED_SHA256 and REMOTE_ROWS_MD5 manifests copied locally. All 24 main shard logs and qualification/failure receipts retained.
- Shared budget: 9.507352057091063 core-hours including engineering failures, 76 complete leases, four failed leases, none running; within 15 core-hours.
- Main result: FER diag-off .0325, cov-off .1575, cov+ridge .0425, diag2 .0233333, cov-oracle .1866667, diag-oracle .0216667. Ridge recovery .92, frame-cluster 95% CI [.849315,1]; realized-error-profile oracle recovery negative. Ridge does not establish scalar equivalence or uniquely identify a mechanism.
- Fixed-geometry gains locate the full-arm degradation at estimator switching: original SBL .115833 -> fixed gain refit .1675 -> continuous .1575. Continuous movement helps relative to fixed refit; previous causal wording must be restricted.
- Critical limit: ridge arm 1191/1200 SBL runs did not converge within 100 iterations. This is a fixed-budget pipeline finding. No extended-iteration or new predictive experiment was performed in this E3c-first milestone.
- Draft result res-20261018-01 links both predecessor cards; STATE and asset index point to pending acceptance. Independent review records a pass within these explicit limits. Broad E1/E2/E3 audit and fresh mechanism/predictive work remain deferred; parent task not completed or archived.
