# SP stage-3 close-out — first Phase A screen

D18 subsequently approved a second volume-selected read-only batch. Its separate evidence and results are in `batch-2/phase-a.md`; the first-batch evidence below is preserved unchanged.

2026-11-15; Codex. Authority: Eric's D17 approval relayed in Claude's resume brief. Only the first read-only Phase A batch, at most ten same-kind whole-stage-3 groups. Step-1 Phase A/R3 was delivered before starting. No Phase B/C, disposal, moves, rule registration, project checks or vault commit is authorised or performed.

## Outcome

The first ten-group screen is complete. **No eligible disposal batch emerged.** Eight groups have historical experiment/protocol/Mission bindings and stay `保留`; two remain `继续待审`. The existing current-root static table had missed these historical bindings. A filename prefix or a zero current-root hit count cannot establish that an old result is unbound.

If every recommendation in this exact list is approved, predicted reduction is **0 files / 0 bytes**. Actual reduction in this read-only phase is also **0 files / 0 bytes**. The inspected ten groups contain 1,497 files / 57,592,899 bytes (about 54.9 MiB); those are reviewed holdings, not savings.

| Recommendation | Groups | Files | Logical bytes |
|---|---:|---:|---:|
| 补绑定 | 0 | 0 | 0 |
| 保留 | 8 | 1,485 | 52,941,808 |
| 继续待审 | 2 | 12 | 4,651,091 |
| 打包移出 | 0 | 0 | 0 |
| 彻底删除 | 0 | 0 | 0 |

No further batch was opened. This does not fulfil the hoped-for “one small batch through A/B/C with visible reduction”; it establishes that these ten initial candidates do not meet that starting condition. It does not judge the remaining groups, prove the wider cleanup has no value, or authorise a rule change to make a deletion fit.

## Factual corrections to the brief

1. **136 directories, not 143.** Recount: 79 `afdm_sp_joint_unrolled/outputs_*` directories + 32 `results/` directories + 25 `.mission/` directories. The earlier inventory's 86 output-name groups included seven ordinary log/summary/JSON files. They are explicitly listed in `inventory-detail.json` and excluded; no removal happened. Two container `.DS_Store` files are likewise outside directory groups.
2. Phase separation reuses the approved diagnosis's per-file phase labels for present regular files, without importing its script or changing labels. **72 whole-P3, 59 mixed-or-unresolved, 5 non-P3**. New/unmapped paths and symlinks prevent a whole-P3 verdict. Phase labels include original path/date inference; they are not a proof from byte contents or today's mtime. The 59 bucket includes unresolved groups, not just proven multi-stage mixtures, and they all remain outside this batch.
3. “143 review rows” is superseded by Claude's explicit first-small-batch approval, not taken as authority to review every group. `phase-split.csv` classifies all 136; `small-batch-review.csv` reviews only ten. The other 126 have no new disposition verdict.
4. A literal `.gitignore` entry is not a result binding; a similarly named `_runtime`/`_raw` sibling is not the selected directory. The evidence filter keeps path boundaries and separately identifies configuration-only hits. The expanded check uncovered real historical bindings, so no eligible clean-disposal batch can be claimed.

## Evidence and method

- `phase-split.csv`: unique current directory list, phase composition, current counts/bytes and Git states. `inventory-detail.json` retains phase basis, regular-file exclusions and symlink/unmapped counts, without duplicating a full file-path inventory.
- `selected-groups.json`: the ten same-kind result-directory candidates, chosen from whole-P3 groups with zero named targets in prior current-root coverage, largest logical bytes first. This is an initial candidate screen; final historical conflicts were not ignored.
- `small-batch-review.csv`: one row per candidate with experiment/date, file/byte/tracked/ignored counts, binding evidence, unresolved-reference assessment, recovery scope, writer uncertainty, recommendation/confidence and predicted reduction.
- `bindings.csv`: fresh all-tracked text plus current untracked/ignored source/protocol/asset/task/entry search; historical cards and Mission records are included, not only current STATE. Source excerpts retain the matched path and source line. No complete binary/dynamic/basename-only reference proof is claimed.
- `results-unresolved-prefixes.csv` / `prefix-review.md`: all eight visible-results unresolved records interpreted against the selected groups; 4,714 prefix-free records remain global residual risk. The two CGR pending groups have only external ignore-configuration literal hits, not proof that they are disposable. Their source-contract/review records and ignored transport payloads remain unresolved for retention/recovery.
- `disposition-summary.csv`: five destinations, including zero-count rows. No compressed package, alternate data copy or deletion list was produced.

Recovery: tracked portions are unchanged against reachable HEAD on the existing vault `main` branch. That confirms an existing Git source for those tracked bytes, not recovery of each whole directory. Ignored remainders have no verified recovery source in this bounded audit; older branch/object searching and actual restoration were not performed. No numerical regeneration was attempted or inferred from a parameter list. Remote copies were **没查**, including ones named in old records. No source equivalence/uniqueness count is needed for `.mission` because no mission group entered this batch.

Writers: existing launchers/records identify historical producers and read destinations. No claim that remote jobs are absent is possible without the forbidden remote inspection. Active writes and complete indirect callers remain unverified where they would matter for disposal; no group with that uncertainty was proposed for removal. The Step-1 R3 loaded code/mission ranges remain retained; result/code directories with similar names are distinct.

## Validation and remaining gate

Before handoff, validate that the 136 paths are unique, that all ten rows are whole-P3 results directories, every row has exactly one allowed recommendation, and summary counts reconcile. Compare final Git status to `phase-a-state-before.json`; task-owned files may be added, but no pre-existing status entry may disappear or change. These checks catch inventory/summary drift or a forbidden project mutation; failure means correct only the owned review artifacts or stop and report. They are metadata checks, not execution of any project test or experiment.

Actual validation result, elapsed time and final Git-state evidence are recorded in `validation.json`. No activation/implementation transition was performed for this read-only screen; task metadata remains planning with Phase A evidence available. Phase B/C still need Eric. Nothing is ready for a destructive confirmation from this batch. Claude can review the eight retention bindings and two unresolved cases, then ask Eric whether a differently selected small batch is worth its cost; do not expand automatically.
