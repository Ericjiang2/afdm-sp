# Research: truth-grid rank readout

- Query: Summarize `truth_grid_ranks.csv` by trigger/control, global step 0/1, and entering same-delay status; associate paired outcomes to identify GLOBAL-only rescues and representative still-failing missing-delay witnesses.
- Scope: internal
- Date: 2026-09-22

## Findings

### Scope and denominator

- Sources: `results/tf_geometry_reopen_20260922/analysis/truth_grid_ranks.csv`, `paired_outcomes.csv`, and `summary.json`.
- `paired_outcomes.csv` has 75 observations: 43 `trigger` and 32 `control`. The paired outcome denominator is observation-level.
- `truth_grid_ranks.csv` has 1,160 path-step rows: 145 global steps × 8 true paths. It contains 600 step-0 rows and 560 step-1 rows; five control observations have step 0 only, so 70 observations contribute both steps. Rank table denominators below are path-step rows, not independent frames.
- `truth_grid_ranks.csv` has no `kind` field; `kind` was joined from `paired_outcomes.csv` by `observation_id`.
- Entering classes: `none` = `entering_same_delay_path_count == 0`; `far` = same-delay path exists and minimum Doppler distance `> 0.125`; `near` = `entering_same_delay_within_half_grid_step == True` (equivalent to distance `<= 0.125` in these rows). Totals are 82 none, 207 far, 871 near. No row has `entering_same_delay_exact_atom == True`; `missing_or_all_slots_masked` is False for all 1,160 rows.

### Nearest true-atom rank by class

Counts are `hits / path-step rows` with percentages; median is `best_global_rank`.

| kind | step | entering class | n | top-1 | top-10 | top-20 | median rank |
|---|---:|---|---:|---:|---:|---:|---:|
| control | 0 | none | 24 | 15/24 (62.5%) | 22/24 (91.7%) | 23/24 (95.8%) | 1 |
| control | 0 | far | 12 | 4/12 (33.3%) | 7/12 (58.3%) | 8/12 (66.7%) | 3.5 |
| control | 0 | near | 220 | 7/220 (3.2%) | 54/220 (24.5%) | 60/220 (27.3%) | 678.5 |
| control | 1 | none | 5 | 2/5 (40.0%) | 3/5 (60.0%) | 4/5 (80.0%) | 9 |
| control | 1 | far | 12 | 1/12 (8.3%) | 6/12 (50.0%) | 7/12 (58.3%) | 13 |
| control | 1 | near | 199 | 13/199 (6.5%) | 107/199 (53.8%) | 121/199 (60.8%) | 9 |
| trigger | 0 | none | 35 | 15/35 (42.9%) | 23/35 (65.7%) | 28/35 (80.0%) | 3 |
| trigger | 0 | far | 102 | 23/102 (22.5%) | 62/102 (60.8%) | 77/102 (75.5%) | 6 |
| trigger | 0 | near | 207 | 2/207 (1.0%) | 21/207 (10.1%) | 37/207 (17.9%) | 622 |
| trigger | 1 | none | 18 | 3/18 (16.7%) | 12/18 (66.7%) | 13/18 (72.2%) | 3.5 |
| trigger | 1 | far | 81 | 6/81 (7.4%) | 41/81 (50.6%) | 49/81 (60.5%) | 10 |
| trigger | 1 | near | 245 | 13/245 (5.3%) | 100/245 (40.8%) | 125/245 (51.0%) | 18 |

### Paired outcome witnesses

`summary.json` reports 21 GLOBAL-only rescues (`LOCAL20_correct=False`, `GLOBAL20_correct=True`), all among the 43 trigger observations; there are 0 LOCAL-only rescues, 10 both-correct, and 12 neither-correct. The examples below are representative path-step witnesses, not additional frame-level samples.

#### GLOBAL-only rescue (2 examples)

| observation | step/path | true atom (delay, Doppler) | best rank | accepted atom | accepted same-delay Doppler distance |
|---|---|---|---:|---|---:|
| `s650_f0035` | 0 / 3 | (51, 1.008110) | 1 | (51, 1.0) | 0.008110 |
| `s650_f0221` | 1 / 6 | (37, 0.732984) | 1 | (37, 0.75) | 0.017016 |

Both rows are top-1 true-atom replacements and have accepted delay equal to the true delay; their paired outcomes are original false, LOCAL20 false, GLOBAL20 true (`paired_outcomes.csv`).

#### Still-failing missing-delay witnesses (2 examples)

Here “missing-delay witness” means the paired outcome remains false under original, LOCAL20, and GLOBAL20, while the selected replacement has no entering same-delay path (`entering_same_delay_path_count=0`) and its accepted delay differs from the true delay. The same-delay accepted-distance field is therefore undefined.

| observation | step/path | true atom (delay, Doppler) | best rank | accepted atom | accepted same-delay Doppler distance |
|---|---|---|---:|---|---:|
| `s650_f0863` | 1 / 2 | (32, 0.816656) | 2 | (36, 1.25) | — (delay mismatch) |
| `s650_f0605` | 0 / 1 | (14, 1.406832) | 5 | (83, 0.0) | — (delay mismatch) |

These are not `missing_or_all_slots_masked` rows—the exported mask is false everywhere. They are selected as delay-mismatch witnesses from the still-failing paired set; the distinction is recorded to avoid conflating the two fields.

## Caveats / Not Found

- Rank percentages describe path-step rows and must not be reported as independent-frame success rates.
- `accepted_new_same_delay_doppler_distance` is blank whenever the accepted delay differs from the true delay; the two missing-delay examples correctly report this as undefined rather than zero.
- No receiver was run, no truth grid or result was retuned, and no code/result file was modified.
