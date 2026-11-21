# Phantom-admission law — semi-blind replay

This semi-blind replay used frames whose aggregate rescue and phantom shares were known in advance. Per-unit outcomes, gains and window membership were first inspected after the protocol freeze.

## Observation

The replay completed 8,106 cap-8 triggered M-family keys across frames 10000–10999, 4.5–7 dB and all four G/U × ρ .3/.5 cells. It matched the archived F0 fields and both first edits on every target key. It used 1.043 core-hours of the 2-core-hour cap. The readout verified all 200 gzip MD5s and unique target keys before scoring. [Protocol](../PROTOCOL.md) · [Completion receipt](main_20261118/main_receipt.json) · [Results JSON](main_20261118/results.json)

The common subset admitted 7,667/8,106 keys (94.58%). Among admitted keys, A2 made 7,232 phantom edits, added 127 missing true delays, made 169 other edits and made no edit on 139 keys. Of the admitted keys, 5,654 lay inside W, 596 lay outside and 1,417 had undefined W. Undefined W omitted a key from the window contrasts alone. The shares retain other and no-edit observations in their denominators.

| Subset check | Removed at this step | Failed independently | Remaining |
|---|---:|---:|---:|
| E > 0 | 0 | 0 | 8,106 |
| u > 0 | 0 | 0 | 8,106 |
| λ > 0 | 0 | 0 | 8,106 |
| A2 K > 0 | 0 | 0 | 8,106 |
| A1c K > 0 | 0 | 0 | 8,106 |
| Legal P competitor | 0 | 0 | 8,106 |
| Legal N competitor | 0 | 0 | 8,106 |
| One surviving anchor | 0 | 0 | 8,106 |
| \|D\| ≥ .90 | 0 | 0 | 8,106 |
| \|κ − D\| ≤ .05 | 0 | 0 | 8,106 |
| P coherence with other survivors ≤ .15 | 43 | 43 | 8,063 |
| N coherence with entering atoms ≤ .15 | 396 | 399 | 7,667 |

| Descriptive estimate | Point | 95% physical-frame bootstrap interval |
|---|---:|---:|
| A2 three-class accuracy | 99.63% | [99.49%, 99.77%] |
| Always-phantom accuracy on the same subset | 94.33% | [93.43%, 95.17%] |
| Paired accuracy gain | +5.31 pp | [+4.47, +6.19] pp |
| A2 phantom-first inside W (5,654/5,654) | 100.00% | [100.00%, 100.00%] |
| A2 phantom-first outside W (465/596) | 78.02% | [74.51%, 81.40%] |
| A1c phantom-first inside W (157/5,654) | 2.78% | [2.06%, 3.57%] |
| A2 minus A1c phantom share inside W | +97.22 pp | [+96.43, +97.94] pp |

Accuracy maps no edit to the rule's other class. A predicted new delay outside the true missing set is an error. The AUC used the two observed P/N classes with ties worth one half.

Calibration compared the phantom candidate–slot pair attaining P_A2 on each admitted key with the same pair in A1c. Claude's scalar calibration forecasts were scored on the pooled pairs. All measured gains were positive.

| Arm | Pairs | Spearman ρ | Median relative error |
|---|---:|---:|---:|
| A2 | 7,667 | .9991 | 0.80% |
| A1c | 7,667 | −.0452 | 90.03% |
| Pooled | 15,334 | .8688 | 6.99% |

At the readout's fixed splits, every pair lay in |D| ≥ .95 and |κ − D| < .025. Those strata have the table's values. The strata .90 ≤ |D| < .95 and .025 ≤ |κ − D| ≤ .05 were empty.

## Frozen verdicts

| Rule | Evaluation |
|---|---|
| UNSCORABLE if coverage < 5%, either AUC class is empty, or either W stratum is empty | All prerequisites passed. Coverage was 94.58%, the AUC class counts were 7,232 and 127, and the W counts were 5,654 and 596. |
| M1 SUPPORTED above .50, REFUTED at or below .50, INCONCLUSIVE otherwise | **SUPPORTED.** AUC .999385 [.998747, .999842]. The lower endpoint exceeds .50. |
| M2 SUPPORTED above zero, REFUTED at or below zero, INCONCLUSIVE otherwise | **SUPPORTED.** A2 inside-minus-outside difference +21.98 pp [+18.60, +25.49] pp. The lower endpoint exceeds zero. |
| Astra's inside-window arm-separation falsifier | The upper endpoint of the A2-minus-A1c interval exceeds zero. |

Intervals use 20,000 paired physical-frame draws over the 1,000 physical frames. Each draw carries all of a sampled frame's keys together. Neither primary estimate had an undefined draw.

Astra's outside-W A2 share and inside-W A1c share fell inside their forecast ranges. The coverage, accuracy, AUC and inside-W A2 share exceeded their upper forecast bounds. Claude scored seven of seven binary forecasts with mean Brier .1586 under the pooled calibration convention. [Prediction ledger](../../../research-assets/prediction-ledger.md)

## Untested explanation

**M confidence.** In A1c the uncertainty cross-term can cancel much of the modeled phantom reward at close spacing, leaving a smaller modeled innovation. Projected residuals omitted by the isolated-anchor approximation may then account for a larger share of the measured reward. The arm-specific calibration is consistent with this explanation. The replay did not isolate the projected residual.

Raw shards remain on deinlab. The MD5 of the per-shard manifest is `a2e6c503f47b4a962c077850e8bb15bc`. [Per-shard manifest](main_20261118/REMOTE_ROWS_MD5.txt)
