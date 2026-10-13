# Native tensor-free joint SP-AFDM: bounded development results

**Verdict: the frozen primary passes the development continuation gate through the speed route. The accuracy route fails its four-net-rescue threshold. No confirmation experiment was started.**

The user approved this independent task from the supplied native-joint handoff. The predecessor physical-refinement campaign remains stopped and separate. Screening A and fresh expansion B are not pooled for inference. Source commit `2d130b4d`; qualified baseline `31d5ec0d`; allocation and seed namespaces are in `campaign/plan.json`.

## Answers and decision

1. **Survivors:** retain frozen `TF_J20_R2`, selected `EP2_MEAN_R2`, and `TF_POINT20_R2` as the simplification control. EP2_SOFT and FIXED do not merit broad expansion on these samples. EP4_MEAN remains an accuracy comparator, PBI8_SOFT an expensive limited-subset comparator. I1 remains the predecessor reference; this separately approved native campaign did not rerun it.
2. **Enough signal for further development:** yes, provisionally, from complete runtime with no observed unrestricted error disadvantage against selected EP. In B at6.5dB, TF/EP median cost ratio0.582 and p90 ratio0.445 meet the frozen ≤0.75/≤1.0 speed thresholds; unrestricted FE1/32 versus2/32. The deadline accuracy route has3 net rescues, below its required4. This is a development decision, not established FER superiority or equivalence.
3. **Informative regime:**6.5dB at the frozen D=0.678048s. At8dB both methods have0/16 FE, with0 paired harms; the guard passes, but this cell poorly distinguishes error performance.
4. **Simplification:** POINT ties TF in A FE0/12 and in the predefined B first8 subset FE1/8, with the same failed frame. B information errors are148 versus142 for primary on that subset. Withdraw any claim that propagated gain uncertainty independently explains the gain; POINT is a plausible simpler configuration, not proven equivalent and not relabeled primary. FIXED loses1/4 A frames versus0/4 for joint, a small diagnostic suggesting within-batch gain adaptation matters. This is not a new mean-only/scalar-Gamma/full-Gamma ablation: those conclusions remain in the predecessor report; no full-Gamma claim is justified here.
5. **Competitors to retain for any future authorized confirmation:** EP2_MEAN (selected cost comparator), EP4_MEAN (stronger unrestricted accuracy in A), and PBI8_SOFT (external bilinear family, bounded subset because costly). These are3 configurations from2 external families. POINT is an internal control. No new competitor implementation or retuning is warranted by this run.
6. **Next-stage cost estimate, not authorization:** a hypothetical64-frame6.5dB development extension with TF/POINT/EP2/EP4 plus PBi on8 predefined frames would cost about240s of measured receiver time, roughly5–7min wall on the same single-thread CPU, and approximately50–80MiB evidence with the same audit policy. Estimate uses observed arm means, A EP4 cost and current evidence density; it is not a power calculation or confirmation design. No next-stage job is running.

## Stage A: selection only

70 calls on12 fresh6.5dB observations. D=1.2×median complete EP2_SOFT time. EP2_MEAN selected by deadline FE, then median cost and ID. Both A advancement routes passed:4 rescues/0 harms, median ratio0.5203, p90 ratio0.5281. All70 attempts/140 saved checkpoints passed recount.

| Arm | n | FE at D | Unrestricted FE | Complete median s | p90 s |
|---|---:|---:|---:|---:|---:|
| EP2_MEAN_R2 | 12 | 4 | 4 | 0.5522 | 0.6748 |
| EP2_SOFT_R2 | 12 | 9 | 8 | 0.5650 | 0.6650 |
| EP4_MEAN_R2 | 12 | 6 | 1 | 0.8395 | 1.0737 |
| PBI8_SOFT_R2 | 6 | 6 | 2 | 14.3438 | 14.3514 |
| TF_FIXED20_R2 | 4 | 1 | 1 | 0.3200 | 0.3625 |
| TF_J20_R2 | 12 | 0 | 0 | 0.2873 | 0.3564 |
| TF_POINT20_R2 | 12 | 0 | 0 | 0.2873 | 0.3564 |

PBi uses first6 frames; FIXED first4. Different-n totals are not paired comparisons. Screening selection prevents treating A as independent confirmation.

## Stage B: fresh fixed comparison

112 calls:32 paired6.5dB observations,16 paired8dB observations, POINT/PBi only on first8 at6.5dB. Primary, EP, D and producer remained frozen. All112 attempts/224 checkpoints passed recount; no numerical failures.

| SNR | Arm | n | FE at D / unrestricted | Info errors / bits | Code errors / bits | Median / p90 s | Mean channel NMSE |
|---|---|---:|---:|---:|---:|---:|---:|
| 6.5 | EP2_MEAN_R2 | 32 | 4 / 2 | 225 / 32768 | 448 / 65536 | 0.5049 / 0.6893 | 0.016970 |
| 6.5 | PBI8_SOFT_R2 | 8 | 8 / 2 | 204 / 8192 | 420 / 16384 | 14.3159 / 14.3740 | 0.030779 |
| 6.5 | TF_J20_R2 | 32 | 1 / 1 | 142 / 32768 | 281 / 65536 | 0.2937 / 0.3064 | 0.012544 |
| 6.5 | TF_POINT20_R2 | 8 | 1 / 1 | 148 / 8192 | 285 / 16384 | 0.3049 / 0.3567 | 0.018200 |
| 8 | EP2_MEAN_R2 | 16 | 0 / 0 | 0 / 16384 | 0 / 32768 | 0.4862 / 0.5532 | 0.006605 |
| 8 | TF_J20_R2 | 16 | 0 / 0 | 0 / 16384 | 0 / 32768 | 0.2825 / 0.3289 | 0.006619 |

At6.5dB, paired TF-versus-EP rescues/harms are3/0 atD,1/0 at1.5D,2D and unrestricted. Conservative ≥95% interval for ΔFER=FER_EP−FER_TF is[-0.1128,0.2738] atD and[-0.1276,0.1834] unrestricted: neither excludes zero. Exact95% conditional rescue-probability intervals are[0.2924,1] and[0.0250,1]. These use frames, not independent-bit assumptions. At8dB all paired counts are0/0; no equivalence claim follows.

The frozen primary has1/8 unrestricted FE on the PBi subset versus PBi2/8. PBi returns no decision byD,1.5D or2D on all8. This supports limiting its allocation; eight frames cannot settle broad accuracy superiority. POINT and primary share one failed frame in their paired8; similar FE is not evidence that their internal messages or BER are identical.

## Execution, costs and provenance

Real A launched2026-09-21 11:08:21UTC, within the requested five minutes; B launched11:13:59UTC. Both exited0. CPU `deinlab`, one numerical process, no GPU, thread counts1, all writes/cache/temp under `/data/guoyikun/`. Remote evidence root:
`/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_native_joint_20260921`.

Measured receiver time sums to **275.744s** across182 calls. Actual A/B numerical process wall times are147.90s and200.29s, totaling348.19s (5.80min); CPU user+system338.15s. These exclude preparation, qualification, offline analysis and transfer. Shared-process peak RSS is1,152,088KiB (~1.10GiB), not isolated receiver memory. Final stage artifact inventory contains740 files totaling54,076,394bytes (51.57MiB). Completion snapshots precede final summary files; the final inventory is authoritative.

Complete online costs include initialization, refits, inference, decoding and checkpoint callbacks; static setup/warmups are separate in manifests and warmup ledgers. Saved per-frame seeds, input/source hashes, raw error counts, LLRs, decisions, geometry, times, RSS and diagnostics support recount. NMSE is computed offline from compact paths; six predefined dense canaries agree. Transform diagnostics are explicitly partial logical counts, not full receiver FLOPs or total transforms. Heavy audit data stay remote; no per-call dense path tensor was saved.

Five original Stage-0 qualification scripts passed, including292 historical decision recounts and competent four-FFT checks. A separate old-fixture smoke preserved TF/EP/PBi decisions and reloaded six checkpoints. These qualify engineering only; they are not added fresh samples or evidence of scientific novelty. Two-FFT equivalence is not the claimed receiver advantage.

Evidence: `stage_A_gate.json`, `stage_{A,B}_{manifest,ledger,recount,summary,completion}.json*`, `stage_{A,B}_warmups.jsonl`, `launch_{A,B}/`, and final transfer/closure receipts. Source was frozen before fresh data; offline analysis scripts are separately recorded. No accepted paper claim or project STATE was promoted.

Cost breakdown beyond the182 measured calls: warmups32.294s, unique-frame generation21.699s, scoring/storage3.481s (instrumented categories; not an exhaustive wall-time identity). PBi consumes200.612s of275.744s measured receiver time despite only14 calls. Future allocation should keep that arm on a small predefined subset.
