# Fixed prospective CGR mechanism test

The registered 6.5 dB population contained 256 fresh observations. All 768 planned wrappers completed: 256 each of BASE, CGR, and SHAM; no unexpected numerical fallback. The original 101 attempts remain a separate historical campaign. No BLOCK arm was run.

| Frozen gate | Result | Evidence |
| --- | --- | --- |
| I — integrity | Pass | 256 sealed observations; 768 complete wrappers; ordered prediction and observed Git seals |
| M — transport | Insufficient support | Only 3 frames met the prediction-sealed E criterion, below the fixed minimum of 8; each of four sign tests had 3 wins, 0 losses, one-sided p=0.125, Holm-adjusted p=0.5 |
| U — decisions/safety | Insufficient recovery evidence | BASE had 0 information-word failures among 256, so CGR had 0 rescues; all three arms decoded all 256 correctly, with 0 harms and 0 new valid-but-wrong words |
| L — calibration | Pass | Fixed mean CGR-minus-BASE bit log loss was −0.00435 on E and −0.000051 over all 256; CGR-minus-SHAM was −0.01065 on E |

On E, the pooled unclipped prediction error divided by actual shift norm was 0.330 for CGR and 0.443 for SHAM; cosines were 0.946 and 0.902. These directional summaries are descriptive for three selected frames and do not satisfy M's prospective inference gate. Neither `prospective_mechanism_supported` nor `bounded_continue` passed. There is no basis here for a population FER improvement claim or another outcome-driven run.

All 256 frames had a ready checkpoint by 0.5 s: correct BASE/CGR/SHAM counts were 255/254/256; by 1.0 s all were 256/256/256. Mean complete times were 0.351/0.356/0.354 s, respectively. These timings describe phased runs and are not randomized standalone latency comparisons.

The source/namespace registration is Git commit `ef44db445929f4059ebd2dd781199e3e9b6ce95f`. The BASE-only prediction seal was committed before interventions at `706cf305b979ba287cb47ed3f4082b5044b7aeca`. The full observed seal and truth-seal identity were committed before truth access at `ac662205c7f8bcfbfa262aad9f751bcc9de76d69`. The complete fixed tables, frame outcomes, contrasts, timing, and analysis receipt are in [analysis/report.json](analysis/report.json) and [analysis/analysis_receipt.json](analysis/analysis_receipt.json). [Independent recount](independent/recount_receipt.json) completed; two corrections to its reader path and G-matrix orientation were retained, with no receiver rerun.
