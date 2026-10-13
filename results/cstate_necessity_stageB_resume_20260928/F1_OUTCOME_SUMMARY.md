# F1 admitted comparison: current developmental evidence

The admitted compatible optimization does **not replace B on this fixed developmental population**: it has more observed information failures and greater complete mean latency. This is a descriptive comparison, not a statistically established population dominance or a fresh confirmation.

| Full1024 policy | Information failures / FER | Coded BER | Complete mean / p95 (s) | Correct durable decision by0.5s /1.0s |
| --- | --- | --- | --- | --- |
| B = F0+TF+CSTATE | 6 /0.58594% | 0.0006494522 | 0.346394 /0.387398 | 1004 /1018 |
| Ccompat = admitted F1+TF | 12 /1.17188% | 0.0008082390 | 0.558312 /0.594751 | 755 /1012 |

Relative to B, Ccompat rescues4 frames and harms10; both fail2. Exact two-sided McNemar p=0.1795654 does not establish equivalence. Neither full arm has a valid-but-wrong output or a numerical failure. At both deadlines each arm has a durable decision for all1024 frames; the latest eligible checkpoint may precede its final output. The Cref timing subset has64 frames, with2 information failures; it is not a second full-population estimate.

Primary analysis was frozen in Git `d87ae32c6b8febe826e8e4f2ecbdff40b347959c`, after observed Git `64893916d5de5e81fd720946d666d9dbe313fb0d`. Its read-only remote analysis took40s and made zero receiver calls. [Report](analysis_f1_compat_v1/report.json), [frame outcomes](analysis_f1_compat_v1/frame_outcomes.csv), [deadline decisions](analysis_f1_compat_v1/deadline_decisions.csv), [component costs](analysis_f1_compat_v1/component_timing.csv) and [8491-file raw inventory](analysis_f1_compat_v1/observed_file_inventory.json) retain the full derivation chain. Generated CSV CRLF bytes are preserved exactly for remote/local/Git digest matching.

`triggered_prefix_nonzero` in the frozen report aggregates the producer's policy-trigger flag. Its zero for Ccompat/Cref does not mean zero native syndrome failures; use `syndrome_nonzero` for that question (Ccompat12, Cref2). No branch is defined for those policies.

The [matched profile](F1_FAST_PROFILE.md) removes32.1% of reference acquisition excess and reduces matched complete latency12.2%; it does not isolate all remaining cost as intrinsic. The historical f197 search-count discrepancy remains unexplained as recorded in the [adjudication](F1_EQUIVALENCE_ADJUDICATION.md); the current full1024 equivalence pass does not rewrite that failure. Full F2 comparison and final manuscript adjudication remain open.

[Independent mechanical recount](independent/F1_COMPAT_OUTCOME_RECOUNT.json) matches243/243 comparisons across the frozen outcome, deadline and timing tables and their Git blobs, plus8/8 conditional branch-cost checks. Its scope is table arithmetic and Git binding; it does not claim a second independent raw-to-truth scoring pass.
