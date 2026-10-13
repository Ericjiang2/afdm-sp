# TF+CSTATE sealed-data recovery readout

**Original one-shot campaign remains `invalid`.** It stopped on a metadata schema mismatch before truth access. The user then authorized a retry of the failed test. This separate recovery changed only the analyzer's check for the already committed fifth `verification` field and its exact value. The 3,072 observations, 6,144 receiver calls, old source, registration, observed/truth seals and Git commits were unchanged. No generator or receiver was called during recovery.

Recovery status: `completed`. Independent saved-artifact verifier: `pass`; it recounted 3072 observations, 6144 receiver calls, 12554 checkpoints, and 3072 paired native prefixes.

| SNR (dB) | TF information FER | TF+CSTATE information FER | Rescues / harms | 0.5 s system failures TF → combined |
|---:|---:|---:|---:|---:|
| 6 | 206/1024 (20.12%) | 61/1024 (5.96%) | 145 / 0 | 206 → 79 |
| **6.5 primary** | **40/1024 (3.91%)** | **6/1024 (0.59%)** | **34 / 0** | **40 → 10** |
| 7 | 20/1024 (1.95%) | 5/1024 (0.49%) | 15 / 0 | 20 → 6 |

At 6.5 dB, full paired table: 984 both correct, 0 TF only correct, 34 combined only correct, 6 both wrong. ΔFER (combined−TF) = **−0.033203125**, or **−3.32 percentage points**. The prespecified conservative exact one-sided 95% upper bound is **−0.01950560** (−1.95 points), below zero. Thus the *numerical rule on the original sealed population* passes; this is a **postfailure recovery result**, not an unqualified clean completion of the original one-shot pipeline. No separate SNR was promoted to primary.

At 6.5 dB, complete receiver mean latency TF→combined: 0.3285→0.3375 s (+9.05 ms), p95: 0.3686→0.3804 s. Triggered cohort: 40/1024; mean paired extra time 0.2266 s, p95 paired extra 0.2732 s. No missing decisions at 0.5 s in either arm; remaining deadline failures are ready decoded errors. No harms, numerical fallbacks or undetected information-word errors occurred in any SNR cell.

In the 6.5 dB triggered branch, mean stage time includes local refinement ~100.5 ms (40.5% of branch), raw serialization/hash ~58.9 ms (23.7%), structural setup/field/scoring/selection/refit ~28.7 ms (11.5%), TF ~19.7 ms and LDPC ~18.9 ms. The full 17-stage and all-cohort timing decomposition is in [RESULTS.md](recovery_20260923/analysis/RESULTS.md), [stage_summary.json](recovery_20260923/analysis/stage_summary.json), and [stage_times.csv](recovery_20260923/analysis/stage_times.csv). No stage was optimized in this run.

Integrity evidence: [recovery status](recovery_20260923/status.json), [analysis receipt](recovery_20260923/analysis/receipt.json), [independent verifier receipt](recovery_20260923/verification/receipt.json). Full per-frame/arm CSVs are retained under `recovery_20260923/analysis/`. Original [invalid campaign record](failure/READOUT.md) is preserved.
