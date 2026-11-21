# SBL residual gap — frozen main run stopped

**STATUS:** STOPPED. The frozen K covariance positive-semidefiniteness gate terminated the run before fitting K on the failing key.

| Failing key | Minimum eigenvalue | Allowed minimum | u | Minimum eigenvalue / u |
|---|---:|---:|---:|---:|
| U, ρ = 0.3, 9 dB, frame 4605 | -0.160228678254 | -1.48578093975e-11 | 0.148578093975 | -1.078413876 |

The launch qualification reproduced R0 and U2 on 20 archived keys and all five arms on 12 smoke keys.
The receiver published 0 of 2,400 keys. Its 14 unpublished shard parts contain 38 complete row records and 0 trailing bytes.
The frozen verdict was not evaluated. The premise, arm frame error rates, recovery contrasts and ratios, joint label and secondary results are unavailable.

Phase 2 charged **0.432126 core-hours**, including both launch qualifications and the initial row-free attempt.
The first attempt exceeded the 32-process limit during startup when workers ran short-lived `lscpu` children.
The second launch used 14 workers and peaked at 17 observed processes.

The freeze and producing commits are recorded in `PRODUCING_COMMIT.txt`. Unpublished parts remain on deinlab with checksums in `PARTIAL_ROWS_MD5.txt`.
