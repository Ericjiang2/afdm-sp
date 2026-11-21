# E-3b smoke counts (counts only; frames >= 8300, never analysed)

rows 16, good 16, error rows 0

| variant | FER events on-grid (re-run) | FER events off-grid | n_pair total | coordinates | accepted | evals | max evals/coordinate | atoms moved / atoms | non-converged SBL |
|---|---|---|---|---|---|---|---|---|---|
| hard-off | 3 | 4 | 104 | 1128 | 1027 | 9183 | 16 | 357 / 376 | 16 |
| diag-off | 1 | 1 | 470 | 1152 | 1126 | 9997 | 16 | 379 / 384 | 11 |
| cov-off | 3 | 4 | 94 | 1083 | 996 | 8844 | 16 | 347 / 361 | 15 |
| genie-off | 0 | 0 | 86 | 651 | 601 | 5814 | 16 | 214 / 217 | 15 |

seconds per key (pipeline + frame generation, on-grid check excluded): mean 15.55, min 12.83, max 19.21; mean refine seconds per variant: hard-off 1.26, diag-off 1.38, cov-off 1.18, genie-off 0.50; mean SBL seconds per variant: hard-off 2.55, diag-off 2.44, cov-off 2.44, genie-off 2.35
core-hours for 2400 keys: raw 10.37, x1.3 13.48
max cond(Q) over all refinements: 422
keys: [('G', 300, 600, 8306), ('G', 300, 700, 8301), ('G', 300, 700, 8313), ('G', 300, 800, 8308), ('G', 300, 900, 8303), ('G', 300, 900, 8315), ('G', 300, 1000, 8310), ('G', 300, 1100, 8305), ('U', 300, 600, 8300), ('U', 300, 600, 8312), ('U', 300, 700, 8307), ('U', 300, 800, 8302), ('U', 300, 800, 8314), ('U', 300, 900, 8309), ('U', 300, 1000, 8304), ('U', 300, 1100, 8311)]
