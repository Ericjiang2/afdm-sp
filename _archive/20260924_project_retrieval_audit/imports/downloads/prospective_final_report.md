# Final TF+CSTATE prospective experiment — complete report

**Run:** 2026-09-23, deinlab, single CPU process. **Scope:** the final fresh TF versus frozen TF+CSTATE comparison only. This report does not combine earlier A+B+C, geometry reopening, or development samples.

**Completion status.** Data generation, all receiver calls, sealed-data analysis, and independent saved-artifact verification are finished. The original unattended pipeline remains **`invalid`**: its analyzer rejected an extra descriptive field in a preregistered Git-binding receipt before reading truth. Following the user's explicit retry instruction, a separate offline recovery analyzer accepted only that exact fifth field and value. Recovery analysis completed; the original independent verifier passed. No new observations or receiver calls were made during recovery. The numerical primary criterion passes on the original sealed population, with this procedural qualification.

## Experiment and primary rule

There were 1,024 new independent observations at each of 6, 6.5 and 7 dB (3,072 total), with separate channel, message and noise streams across frames and SNRs. Each observation was shared only by its paired arms. Both arms independently ran the frozen native `TF_J20_R2` prefix. TF+CSTATE retained the native decision when the final syndrome was zero; otherwise it ran the frozen CSTATE20 continuation. The run made **6,144 native-prefix calls**. Only **6.5 dB** was the prespecified confirmatory cell; 6 and 7 dB are descriptive.

The endpoint is **information-word frame error rate** (FER), evaluated against generated information bits, not syndrome or coded-bit error alone. Let `h` count TF-correct/CSTATE-wrong pairs and `r` count TF-wrong/CSTATE-correct pairs. The paired effect is `ΔFER = FER(CSTATE) − FER(TF) = (h−r)/1024`. The registered one-sided conservative 95% upper bound is the Clopper–Pearson upper bound for `h/1024` at tail 0.025 minus the lower bound for `r/1024` at tail 0.025. The numerical gate requires this upper bound to be strictly below zero with intact evidence.

## Reliability results

| SNR | TF information FER, 95% CP interval | TF+CSTATE information FER, 95% CP interval | Paired rescues / harms | ΔFER |
|---:|---:|---:|---:|---:|
| 6 dB | 206/1024 = 20.12% [17.70%, 22.71%] | 61/1024 = 5.96% [4.59%, 7.59%] | 145 / 0 | −14.16 points |
| **6.5 dB, primary** | **40/1024 = 3.91% [2.81%, 5.28%]** | **6/1024 = 0.59% [0.22%, 1.27%]** | **34 / 0** | **−3.32 points** |
| 7 dB | 20/1024 = 1.95% [1.20%, 3.00%] | 5/1024 = 0.49% [0.16%, 1.14%] | 15 / 0 | −1.46 points |

At 6.5 dB the complete paired table is **984 both correct, 0 TF-only correct, 34 CSTATE-only correct, 6 both wrong**. Thus `Δ̂ = −0.033203125`. The preregistered one-sided 95% upper bound is **−0.01950560** (−1.95 percentage points): `U(h=0)=0.00359594` and `L(r=34)=0.02310154`. The original independent verifier recomputed the bound by a separate binomial inversion and agreed. The auxiliary exact one-sided McNemar p-value is `5.82×10⁻¹¹`; it does not replace the registered gate.

The observable nonzero-syndrome trigger fired on **206/1024, 40/1024 and 20/1024** frames at 6, 6.5 and 7 dB. CSTATE rescued **145, 34 and 15**, leaving **61, 6 and 5** wrong, respectively. Across all three cells there were **zero harms (TF-correct/CSTATE-wrong pairs), zero numerical fallbacks, and zero undetected information-word errors**. Zero-syndrome coded-word errors and information-correct/coded-wrong cases were also zero. These are sample observations for this frozen receiver and physical simulation, not a guarantee of zero harm elsewhere.

Information BER fell from **1.6948% to 0.4638%** at 6 dB, **0.4612% to 0.0611%** at 6.5 dB, and **0.2677% to 0.0431%** at 7 dB. Coded BER and raw bit-error counts are retained in the full analysis report.

## The 0.5-second decision deadline

The deadline is measured from the same frame entry in each arm. It chooses the latest ready checkpoint; an unfinished CSTATE branch leaves the earlier native decision available. A system failure is a missing decision or a ready-but-wrong decision, over all 1,024 frames per SNR.

| SNR | TF system failures | TF+CSTATE system failures | CSTATE rescues ready by 0.5 s | Eventual CSTATE rescues |
|---:|---:|---:|---:|---:|
| 6 dB | 206 | 79 | 127 | 145 |
| **6.5 dB** | **40** | **10** | **30** | **34** |
| 7 dB | 20 | 6 | 14 | 15 |

No decision was missing at 0.5 s in either arm; every remaining system failure was a ready decoded error. At 6.5 dB, four eventual rescues arrived too late to improve the 0.5-second result. Deadline outcomes are secondary; they do not replace the no-deadline primary FER.

## Complete receiver latency

Per-frame complete latency starts before observation load/hash and includes native work, trigger, optional CSTATE, checkpoint artifacts, serialization/hash, and durable decision-record write. The final timing-ledger append and paired audit are outside this clock and recorded separately. Both arms used the same scope. No new optimization was made during this run.

For campaign accounting, fresh generation took **1,237.2 s** and the 6,144-call receiver phase took **3,033.1 s**. The later user-authorized offline recovery analysis took **78.5 s** and independent verification **84.1 s**. These phase wall times are separate from per-frame receiver latency.

| SNR | TF mean / p95 | TF+CSTATE mean / p95 | Mean paired extra time | Triggered frames: mean paired extra time | Nontriggered: mean paired extra time |
|---:|---:|---:|---:|---:|---:|
| 6 dB | 333.4 / 378.7 ms | 377.5 / 568.6 ms | 44.1 ms | 215.7 ms (n=206) | 0.93 ms (n=818) |
| **6.5 dB** | **328.5 / 368.6 ms** | **337.5 / 380.4 ms** | **9.05 ms** | **226.6 ms (n=40)** | **0.21 ms (n=984)** |
| 7 dB | 325.1 / 364.8 ms | 329.8 / 365.9 ms | 4.74 ms | 223.3 ms (n=20) | 0.39 ms (n=1004) |

At 6.5 dB, the triggered cohort's **paired extra-time p95 is 273.2 ms**. The all-frame mean ratio of mean latencies is **1.0276**; the mean of per-frame paired ratios is **1.0324**. These are distinct quantities. The all-frame CSTATE p95 is 380.4 ms, while its triggered-cohort p95 is 601.3 ms. Full mean/median/p90/p95/max distributions for every arm and trigger cohort are in the underlying report.

The 17 exclusive CSTATE stage means for the **6.5 dB triggered cohort** are below. Shares use the complete branch-stage sum, **248.45 ms**. This branch sum and the 226.6 ms paired extra-time mean use different clocks and should not be equated.

| Stage | Mean (ms) | Branch share |
|---|---:|---:|
| Message handling | 0.26 | 0.11% |
| Observation transform | 0.10 | 0.04% |
| Geometry setup | 1.14 | 0.46% |
| Structural field build | 17.06 | 6.87% |
| Structural scoring | 2.02 | 0.81% |
| Structural selection/trace | 4.84 | 1.95% |
| Structural refit/refresh | 3.64 | 1.47% |
| Structural direct fallback | 0 | 0% |
| **Shared local refinement** | **100.53** | **40.46%** |
| Geometry finalization | 1.56 | 0.63% |
| Geometry wrapper overhead | 0.15 | 0.06% |
| Wrapper validation | 0.07 | 0.03% |
| Channel construction | 0.03 | 0.01% |
| TF continuation | 19.72 | 7.94% |
| LDPC | 18.94 | 7.63% |
| Checkpoint write | 19.51 | 7.85% |
| **Raw serialization/hash** | **58.87** | **23.69%** |

Local refinement is the largest measured branch stage, followed by serialization/hash. Structural setup, field build, scoring, selection and refit together take about **28.70 ms (11.55%)**. The full stage decomposition by SNR and triggered/nontriggered/all cohorts remains in [stage_summary.json](recovery_20260923/analysis/stage_summary.json) and [stage_times.csv](recovery_20260923/analysis/stage_times.csv).

## Evidence, recovery, and limits

The protocol, random namespace, source/configuration hashes and primary rule were registered before fresh generation. Generation and receiving exited 0. The remote evidence repository committed preregistration as `1d7254f5e6627b8726f9c4806147c994077cf01f`, then committed the complete observed seal as `929c679b4797de18271065b8e8bf35b67b6de13f` before any truth-dependent analysis. The committed observed and truth-hash-seal bytes matched disk. The verifier checked source identities, all paired input identities and native-prefix equality, **3,072 observations, 6,144 arm records, 12,554 checkpoints, and 9,216 unique component stream IDs**. Its independent [receipt](recovery_20260923/verification/receipt.json) says `pass` and agrees with all primary counts, timing/deadline tables and confidence values.

The original analyzer exited 1 on `ValueError: local preregistration Git-show receipt differs`: the committed local binding had an extra `verification` field, while the analyzer required exactly four keys. This happened **before truth payload access**. The user's subsequent retry authorization allowed a separate analyzer that accepts only the exact fifth field and its committed value. Its diff from the original analyzer changes that schema check only; the frozen statistical formula and receiver are unchanged. The original campaign's `invalid` status and files were preserved. This recovered result meets the **predeclared numerical rule on the original sealed data**; it is **not an unqualified clean one-shot prospective completion**.

This is one simulated physical-channel population at three prespecified SNRs, with one 1,024-frame sample per SNR. It evaluates the frozen TF and TF+CSTATE implementations under the recorded single-thread CPU environment. The 6 and 7 dB effects are descriptive. The report makes no hardware, alternate-channel, or universal zero-harm claim. The research task remains open for user acceptance; all requested experimental execution and independent recount for this final campaign are complete.

Primary artifacts: [full analysis and all-cohort/stage tables](recovery_20260923/analysis/RESULTS.md), [machine summary](recovery_20260923/analysis/summary.json), [analysis receipt](recovery_20260923/analysis/receipt.json), [independent verification](recovery_20260923/verification/receipt.json), [independent integrity audit](EXPERIMENT_AUDIT.md), [original invalid-run record](failure/READOUT.md), and [recovery scope](RECOVERY_PROTOCOL.md). Per-frame and per-arm CSVs are under `recovery_20260923/analysis/`.
