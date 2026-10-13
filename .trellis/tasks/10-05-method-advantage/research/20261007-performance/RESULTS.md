# Frozen pilot results: useful computation benefit, joint gate not met

Status: registered development evidence, not production/CONF or first-in-literature certification.
Source commit 6bd5e122; protocol commit 1fe69f3c; isolated remote commit 8c30d2bd3b3b0e247066b5f260a5a3fe9c0bf020. SSH deinlab, one CPU thread, CUDA hidden. D/P/A all completed, launcher exit 0. No retries, source revisions or dropped groups.

## Concrete outcome

Random-code SCREEN32 versus same-code FULL: complete-call speed ratio 21.183206x; all 256 groups have matching error indicators (bad/reverse discordance 0/0). This is retained as a useful classical AFDM adaptation; not a newly invented FFT/phase-power method. Actual random-code error is 17/256 (6.640625%), versus ambiguity-tuned quadratic 25/256 (9.765625%). Equal-cell paired improvement 3.125 percentage points, exploratory 95% interval [−0.2716335,6.5216335] pp. The frozen >=10pp / positive-lower-interval code-improvement gate **fails**. Other four gates pass; overall positive_pilot_signal is false. Prior theory plus this speedup must not be relabeled as completion of the stronger whole objective.

| N | SNR dB | Current SCREEN/FULL errors | Tuned quadratic SCREEN/FULL | Random SCREEN/FULL | Random FULL/SCREEN time |
|---:|---:|---:|---:|---:|---:|
| 32 | 5 | 33/34 | 19/19 | 13/13 | 7.4775x |
| 32 | 15 | 0/0 | 0/0 | 0/0 | 7.4326x |
| 64 | 5 | 21/21 | 6/6 | 4/4 | 28.1521x |
| 64 | 15 | 0/0 | 0/0 | 0/0 | 28.2373x |

Each cell contains 64 independent paired groups. High-SNR cells have zero errors for every waveform/algorithm. This reveals a ceiling in half the study; it does not license deleting those cells or recomputing a favorable primary endpoint. At low SNR, the tuned quadratic baseline is much stronger than old small-c2; the remaining code gain is modest and statistically inconclusive in this pilot. The screening itself has no random-arm excess errors, so a diagnosis blaming its fourth-power noise is not supported by these results.

## Audit and resource evidence

Independent audit reconstructs all 768 waveform datasets using explicit dense DFTs, all fourth-score grids by direct sums, all 2304 saved selections and count/statistic fields; exact mixture recalculation is limited to 24 predeclared candidates. Maximum discrepancies: Y 4.0441e-13; fourth scores 6.9989e-12; mixture spots 2.0009e-11. This is integrity evidence, distinct from passing scientific gates. D candidate ambiguity values were not independently recomputed; candidate bytes, fixed family, selected argmin and chosen codes were checked. No new audit observations/estimator calls.

Counts: 163280 selected design ambiguity values,96 design phases,3072 new N-vectors,147456 complex observations,256 paired groups,2304 acquisition calls,0 production receiver/decoder calls. All group source arrays and score grids retained. Costs exclude common generation/disk logging from estimator calls for every arm; design, I/O and process costs reported separately. /usr/bin/time includes interpreter imports; no kernel-only speed claim.

Resources: 255.175 stage seconds out of1020 reserved; whole-process maximum RSS 87.387 MiB; 42.104 MiB cumulative stage artifacts. Reservations include D120/P600/A300; no retry budget used. Final remote inventory verifies source snapshot unchanged and binds every raw path with MD5/SHA256. All1674 returned stage files matched their SHA256 inventory. Raw arrays are retained outside Git; metadata and complete remote provenance are durable.

Remote root: `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_acquisition_performance_20261007/`. Exact per-file hashes: local `afdm_sp_joint_unrolled/outputs_acquisition_performance_20261007/REMOTE_INVENTORY.json`. Primary report: `execution/P/results.json`; independent report: `execution/A/audit.json`; runtime: `RESOURCE_RESULTS.json` and `run.log`.

## Remaining and next inference

The stronger goal remains open. Retain the validated computation improvement and the earlier scoped theory. Register a distinct followup before code/data changes: test the design-class effect where short observations make acquisition difficult, with a properly tuned quadratic comparator; keep old results untouched and prohibit seed selection. Also examine whether the old worst-case theoretical barrier implies an average-risk barrier under the uniform acquisition prior; without that bridge, worst-case theory is not an automatic explanation of mean errors.
