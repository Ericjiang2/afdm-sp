# Research: CSTATE stage timing readout

- Query: Summarize the sealed 225-row CSTATE validation ledger by cohort and arm, using the `STAGES` definition in `experiments/tf_cstate_validation_20260922/analyze_validation.py`.
- Scope: internal
- Date: 2026-09-22

## Findings

### Source and accounting

- Source: `results/tf_cstate_validation_20260922/observed/ledger.jsonl` (225 rows: 75 observations × 3 arms; each arm has 43 `trigger` and 32 `control`). No truth fields were read.
- `STAGES` is defined at `experiments/tf_cstate_validation_20260922/analyze_validation.py:20-26` as: `message_handling`, `y_transform`, `geometry_setup`, `structural_field_build`, `structural_scoring`, `structural_selection_trace`, `structural_refit_refresh`, `structural_fallback_direct`, `local_refinement`, `geometry_finalization`, `geometry_wrapper_overhead`, `wrapper_validation`, `channel_construction`, `tf`, `ldpc`, `checkpoint_write`, `raw_serialization_hash`.
- Category definitions used below:
  - `structural_exchange` = `geometry_setup` + `structural_field_build` + `structural_scoring` + `structural_selection_trace` + `structural_refit_refresh` + `structural_fallback_direct`.
  - `shared_local` = `local_refinement`.
  - `remaining_branch_overhead` = `message_handling` + `y_transform` + `geometry_finalization` + `geometry_wrapper_overhead` + `wrapper_validation` + `channel_construction` + `checkpoint_write` + `raw_serialization_hash`.
- Each `mean/p95/max` below is seconds, with p95 matching `analyze_reopening.cost_summary` (`np.percentile(...,95)`). `share` is `mean(category) / mean(added_complete_branch_seconds)`.

### Grouped timing

| cohort | arm | n | structural exchange mean/p95/max | shared local mean/p95/max | TF mean/p95/max | LDPC mean/p95/max | remaining branch overhead mean/p95/max | complete added branch mean/p95/max | full wrapper mean/p95/max |
|---|---|---:|---|---|---|---|---|---|---|
| trigger | LOCAL20 | 43 | 0.001134/0.001308/0.001566 (0.58%) | 0.096827/0.104762/0.139295 (49.87%) | 0.019880/0.021210/0.029079 (10.24%) | 0.023802/0.025943/0.026297 (12.26%) | 0.052514/0.072144/0.090648 (27.05%) | 0.194157/0.214074/0.286128 | 0.516566/0.553842/0.750265 |
| trigger | GLOBAL20 | 43 | 0.461498/0.464919/0.489843 (69.38%) | 0.098263/0.112720/0.114845 (14.77%) | 0.019988/0.021586/0.021689 (3.01%) | 0.019831/0.025756/0.026088 (2.98%) | 0.065560/0.071329/0.088197 (9.86%) | 0.665140/0.683887/0.715894 | 0.979598/1.007280/1.053852 |
| trigger | CSTATE20 | 43 | 0.026335/0.027488/0.028124 (10.92%) | 0.098413/0.111892/0.115203 (40.79%) | 0.019904/0.021738/0.022715 (8.25%) | 0.019710/0.024709/0.025975 (8.17%) | 0.076891/0.103595/0.113093 (31.87%) | 0.241252/0.278553/0.292490 | 0.562355/0.591504/0.622366 |
| control | LOCAL20 | 32 | 0.001158/0.001300/0.001572 (0.63%) | 0.092624/0.104435/0.118960 (50.15%) | 0.020537/0.022505/0.029433 (11.12%) | 0.016510/0.017782/0.023035 (8.94%) | 0.053848/0.069952/0.086945 (29.16%) | 0.184677/0.211789/0.225421 | 0.491999/0.508025/0.648865 |
| control | GLOBAL20 | 32 | 0.433435/0.493061/0.495385 (69.06%) | 0.090352/0.100857/0.108768 (14.40%) | 0.019809/0.022188/0.023480 (3.16%) | 0.016425/0.017504/0.017662 (2.62%) | 0.067607/0.082091/0.091373 (10.77%) | 0.627628/0.687827/0.709835 | 0.935983/0.999742/1.013170 |
| control | CSTATE20 | 32 | 0.026595/0.027742/0.079512 (11.33%) | 0.091940/0.104466/0.119350 (39.18%) | 0.020188/0.021584/0.029383 (8.60%) | 0.016503/0.017371/0.023159 (7.03%) | 0.079447/0.099218/0.114135 (33.85%) | 0.234673/0.272805/0.291595 | 0.542477/0.578063/0.686934 |
| all | LOCAL20 | 75 | 0.001144/0.001310/0.001572 (0.60%) | 0.095034/0.104717/0.139295 (49.99%) | 0.020160/0.021703/0.029433 (10.60%) | 0.020691/0.025782/0.026297 (10.88%) | 0.053083/0.071428/0.090648 (27.92%) | 0.190112/0.214306/0.286128 | 0.506084/0.541938/0.750265 |
| all | GLOBAL20 | 75 | 0.449524/0.491019/0.495385 (69.25%) | 0.094888/0.109538/0.114845 (14.62%) | 0.019912/0.021596/0.023480 (3.07%) | 0.018378/0.025439/0.026088 (2.83%) | 0.066433/0.078072/0.091373 (10.23%) | 0.649135/0.687732/0.715894 | 0.960989/1.005131/1.053852 |
| all | CSTATE20 | 75 | 0.026446/0.027620/0.079512 (11.09%) | 0.095651/0.110154/0.119350 (40.11%) | 0.020025/0.021716/0.029383 (8.40%) | 0.018341/0.024546/0.025975 (7.69%) | 0.077981/0.103584/0.114135 (32.70%) | 0.238445/0.278215/0.292490 | 0.553874/0.591405/0.686934 |

### Gate and clock checks

- The CSTATE20 trigger mean complete added branch is `0.241252 s`, below the `<=0.6 s` gate; p95 is `0.278553 s`, max `0.292490 s`. No trigger row used `structural_fallback_direct` (`0` fallback calls in all arms/cohorts).
- All 17 exclusive stage values sum exactly to `added_complete_branch_seconds` on every row (maximum absolute difference `0`).
- The pre-serialization stages (all STAGES except `checkpoint_write` and `raw_serialization_hash`) sum exactly to `branch_decision_seconds` on every row (max difference `0`).
- `replay_ready_seconds + added_complete_branch_seconds` equals `raw_artifact_ready_seconds` on every row; `raw_artifact_ready_seconds + wrapper_bookkeeping_seconds` equals `wrapper_seconds` on every row; baseline setup/two-round/parity/bookkeeping components also sum exactly to `replay_ready_seconds` (all max differences `0`).
- Parent clocks are therefore nested: `branch_decision_seconds` is a pre-serialization parent, `raw_artifact_ready_seconds` includes replay plus the complete added branch, and `wrapper_seconds` adds wrapper bookkeeping. These parent clocks must not be added again to the exclusive stage totals.

## Caveats / Not Found

- The requested derived CSV destinations `results/tf_cstate_validation_20260922/timing_groups.csv` and `timing_all_cohorts.csv` are outside the Trellis researcher write boundary, which permits writes only under the current task's `research/`; they were not written by this agent. The table above is the exact aggregation from the sealed ledger, and the two CSVs can be materialized by the main session/implementation agent without touching `analysis/` or the ledger.
- This is an elapsed-time readout only. No source, raw evidence, analysis CSV, receiver, truth data, or SSH state was modified or rerun.

## Final artifact placement

The main session copied the researcher CSVs byte-for-byte into the two requested results paths. All315 derived summary rows were independently checked against the sealed ledger to the CSV rounding precision (9 decimal places in seconds); original ledger keeps full precision. No receiver/optimizer was called.
