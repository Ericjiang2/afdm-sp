# Fixed-channel OAMP/LDPC screen

## Correction after the user questioned fairness

On 2026-11-09 the user challenged the two-round cutoff and dense solver. The original budget-specific counts below remain reproducible. Treating that screen as sufficient to discontinue OAMP development was premature. Same-adapter follow-up verifies the first two rounds exactly and recovers 6/9/12/14/15 frames at rounds 1/2/5/10/20. At round 20, 24 of 40 frames still change hard decisions. Full convergence has not been established.

On the first triggered frame (N1024, eight paths, cyclic half-bandwidth90), reusing the exact cyclic-band solver gives the same linear-extrinsic center and variance as the dense implementation, maximum center difference 2.43e-13 and relative linear residual 5.85e-16. Three-trial median update times are 0.572533 s dense setup+update versus 0.106803 s structured factorization+update. This is a one-step solver microbenchmark. Repeated structured factorizations across changing decoder variances need a separate complete timing comparison.

The matched two-decoder-call cap was a valid declared budget but did not equalize the numerical inference schedule or establish converged algorithm performance. TF runs20 scalar symbol updates per call, while the tested adapter uses one linear update and lets LDPC supply the nonlinear stage. The Gaussian-extrinsic update on the decoder side also requires a separate fidelity audit. The protocol's initial pass/fail result must retain its limited meaning. Follow-up code and plan are in `experiments/oamp_ldpc_20261109/diagnose.py` and `DIAGNOSTIC_PLAN.md`, committed before execution as `97a7bb66`. Small outputs are under `outputs_oamp_ldpc_20261109/diagnostic_v1/`.

User-authorized Opus5.5 review is complete. It confirms the LE algebra, recognizes the existing bit-extrinsic turbo convention, and distinguishes that convention from the Gaussian APP-orthogonalization variant. Its recommendations and main-session checks are in [the review synthesis](oamp-review-20261109/README.md). The tested adapter should be labeled an undamped isotropic turbo-LMMSE loop with an OAMP-form LE. At round20 the rescued count has plateaued since round11, but24 frames still change hard decisions and the median relative check-prior change is0.485. Thus neither universal convergence nor a converged algorithm ranking follows.

## Complete OAMP20 versus TF2 timing, requested separately

After the user asked for the actual20-round cost, `time_twenty.py` was committed as `f6bc287a` and executed on deinlab. The previous20-round diagnostic had not logged a complete latency clock. This new run alternates arm order serially on the same40frames, one CPU thread, fixed20 OAMP exchanges versus2 TF detector/decoder batches, without early stopping. It includes matrix construction and dense eigenbasis setup for OAMP. Both start after the common native prefix and saved-channel restoration. All880 decoded, incoming-LLR and check-extrinsic checkpoints exactly reproduce their existing artifacts.

| Quantity | OAMP-form turbo-LMMSE20 | Fixed TF2 |
|---|---:|---:|
| Median complete continuation seconds | 1.114289 | .086183 |
| Mean complete continuation seconds | 1.078197 | .082380 |
| p90 complete continuation seconds | 1.170283 | .086892 |
| Median setup seconds | .578938 | .000000212 |
| Median detector seconds | .062124 | .038426 |
| Median decoder seconds | .480448 | .047819 |
| Median continuation excluding setup seconds | .542769 | .086183 |
| Total actual LDPC sweeps over40frames | 28850 | 3054 |

The ratio of complete medians is12.9293. The median paired ratio is13.0835. Component medians do not sum to the median complete time. After separately accounting for dense setup, the measured remaining computation has a median-time ratio of6.30, with decoder time480ms versus48ms. These are current dense-implementation measurements. Raw timing records and original-artifact bindings are in `outputs_oamp_ldpc_20261109/timing20_v1/timing_results.json`; local independent aggregation checks passed. This timing replay incurs880 detector invocations and880 LDPC invocations, no new observations.

## Original two-call observation

The authorized deinlab replay completed with exit code 0. All 40 archived nonzero-syndrome triggers at 6.5 dB were processed. Both continuations held the saved TF round-1 physical channel fixed, started with the same clipped code-check prior, and executed two additional LDPC calls with at most 50 sweeps each.

| Continuation | Rescues after call 1 | Rescues after call 2 | Overlap with 34 archived CSTATE rescues | Median continuation time |
|---|---:|---:|---:|---:|
| Fixed-gain scalar TF | 12 | 14 | 14 | 0.086077 s |
| Scalar LMMSE OAMP/LDPC adaptation | 6 | 9 | 9 | 0.629109 s |

OAMP versus fixed TF has one rescue and six harms, both measured within the native-failed cohort. OAMP setup, including a dense time-domain Gram eigendecomposition, has median 0.574440 s. Setup is included in the measured 7.308642 median-time ratio. The remaining 984 original native decisions are retained by the proposed syndrome-triggered policy.

## Frozen verdict

The protocol committed at `cd24f670` required recovery of at least 17 of the 34 CSTATE rescues and a median time ratio at most 2. Both criteria fail. Prediction OA1 was 0.25 and receives Brier loss 0.0625. This bounded development comparison is complete.

## Interpretation and scope

The tested fixed-H OAMP/LDPC adapter provides fewer rescues and takes longer than the matched fixed-TF continuation on this cohort. It therefore supplies no evidence for replacing the matched continuation or expanding this adapter under the frozen criterion.

The decoder acts as the nonlinear module. There is one trace-normalized scalar LMMSE update per LDPC invocation. The adapter uses the average decoder-implied symbol variance, the existing QPSK mapping, and direct replacement of the decoder check prior. It was implemented for this screen, without trained OAMP-Net weights, separate QPSK inner denoising iterations, damping tuning, or joint channel re-estimation. It is an adaptation motivated by Luo et al., arXiv:2312.11302 §IV-C, with the repository's decoder interface.

These are the saved September 23 observations, predating the October corrected-generator confirmation. Selection used the archived native syndrome and all 40 triggers were included. The small reused cohort and two-call schedule delimit the result. CSTATE's 34 rescues are an archived one-additional-call reference. The two newly executed arms have matched decoder caps, and the reported timing comparison is between those two arms.

Candidate explanations for the difference in rescues remain untested (L confidence). The large setup cost is directly instrumented evidence about this dense implementation.

## Verification and provenance

The direct LMMSE and scaled-identity algebra checks passed. Every triggered physical channel passed the independent time-matrix versus AF-domain apply check. The run bound the native and baseline source inventories and actual LDPC matrix/cache to the original registration.

A separate saved-output verifier read 40 raw artifacts and independently recounted 160 new decoded checkpoints. It checked incoming prior pairing, replacement after call 1, code identity, truth/observation binding, per-checkpoint bit errors, sweep budgets, timing sums and output hashes. It made zero receiver/decoder calls. The compact results were also recounted locally. The verifier shares the existing artifact reader and is a separate code path within the same agent session.

- Executed code and protocol in `experiments/oamp_ldpc_20261109/`.
- Small results in `afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/`, including `verification.json`.
- Remote raw directory is `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109/`. Each raw SHA-256 is in `observed_seal.json`.
- Initial result commit is `a4af3f2e`.
- New observation generation 0. Two continuations per trigger, two detector/decoder calls each, totaling 160 new detector invocations and 160 LDPC invocations. Frozen-source and scoring context construction does not invoke the baseline receiver.
