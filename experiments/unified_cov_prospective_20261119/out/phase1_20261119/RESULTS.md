# Unified covariance prospective test — Phase 1 qualification (2026-11-19)

The protocol is still DRAFT. The receiver ran on archived or previously used smoke keys. The smoke readouts below concern engineering qualification and timing.

## Frame audit

P1 frames **4400–4599** are unused in the checked archives. The scan read **444,500** files across 27 experiment output roots and 593 historical output roots on deinlab. The local scan read **16,122** files across 33 experiment and 86 historical output roots. It checked explicit frame fields, declared ranges, key lists and CLI offset/count arguments, including gzip rows. The only overlapping labels were from the UB Screen synthetic RNG and the independent S0 Doppler-law calibration. The log-prefixed DPSS gate JSON contributed only counters. Four remaining parse exceptions were AppleDouble sidecars. The receipt records the RNG identities, source paths, raw scan SHA-256 and the prior smoke evidence. [Audit method](../../audit_frames.py) · [Freshness receipt](fresh_check.json)

## deinlab gates

| Gate | Status | Evidence |
|---|---|---|
| G1 reference parity | PASS | All five SBL references matched archived decoded hashes, information errors, atom/pair counts and NMSE on 20 seeded keys. F0 and CODELAY matched on 8 triggered Stage 3 keys. A2 matched on one saved triggered split-prospective K smoke key. [G1 receipt](g1.json) |
| G2 covariance and reductions | PASS | Synthetic symmetry, PSD, projector idempotence and duplicate equal-split checks passed. CSTATE τ = 0 matched CD on the 8 real keys. Empty U2 refinement matched S-lo on 12 smoke keys, including final gain and EM-state hashes. Full trial scores matched brute-force `_system` over 1,250 synthetic and 20,600 smoke trials, with maximum relative errors 2.60e−16 and 1.29e−15. [G2 receipt](g2.json) |
| G3 repeatability | PASS | All arms reproduced after removing timing fields on 12 SBL smoke keys from frames 8400–8411 and 8 CSTATE smoke keys from the archived split-prospective frame 8600. [G3 receipt](g3.json) |

CSTATE U uses the frozen direct exchange schedule. It reuses unchanged data Gram entries, replaces the candidate row and column, and inserts the full CODELAY covariance and rebuilt low-mode projector for each trial support before a batched full solve. A candidate can change the projector on retained atoms at the same delay. Each local pass rebuilds the projector and re-evaluates the incumbent once. Final refit builds a projector on the final support.

SBL U2 shares the S-lo EM fit and builds the refinement projector on each pass's entering atom set. Each pass re-evaluates the incumbent under its fixed projector. The final gain solve uses the last pass's objective.

## Archived leverage

- **SBL.** The 1,200 E-3c and spectral-split paired keys cover 100 physical-frame clusters. The old `φ_lo` is **0.8133 [0.7301, 0.9014]**. The paired cluster-bootstrap 95% half-width is **0.0857**, which scales to **0.0606** for 2,400 keys under the planned square-root extrapolation.
- **CSTATE.** On all 6,400 split-prospective K keys, **A2 − A1 = +4.531 pp [3.984, 5.094]**, with 200 physical-frame clusters. K-diag and K-prod are the A2 and A1 continuations of the same F0 receiver. Each arm uses F0 when the syndrome is zero. The archived grid is U/G × ρ .3/.5 × 4.5–8 dB in 0.5-dB steps, frames 7000–7199. Both readouts use 20,000 paired cluster draws with seed 20261120. [Leverage receipt](leverage.json) · [Split-prospective protocol](../../../tf_split_prosp_20261018/PROTOCOL.md)

## CPU cost

The smoke means are per key in CPU seconds. Shared preparation and F0 run once. U2's cost is incremental after its shared S-lo EM fit. CSTATE continuation costs use the historical Stage 3 whole-grid syndrome rate of 14.53%, with triggered costs measured on the smoke keys.

| Leg | Shared | R0 or A2 | R1 or CD | S-lo or U | S-hi | S-isolo | U2 | Projection × 1.3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SBL, 2,400 keys | 1.098 | 3.656 | 3.503 | 3.933 | 3.402 | 3.879 | 1.356 | 18.050 core-hours |
| CSTATE, 6,800 keys | 0.254 F0 | 0.029 | 0.022 | 0.085 | — | — | — | 0.958 core-hours |

**Total 19.008 core-hours**, below the 25-core-hour limit. The 2,400 SBL and 6,800 CSTATE keys are retained in this DRAFT. The final Phase 1 gate chain used **0.336 core-hours** and 215 seconds wall time. The two one-process filesystem scans and short archive preflights also fit within the Phase 1 cap.

## Defect and verification record

The first read-only preflight initialized the shared frozen P1 context twice. PyTorch rejected the second inter-op thread initialization before the first key was generated. The runner now initializes the provider once per process and checks the same loaded context against both manifests. The read-only preflight passed on retry, followed by the full G1–G3 chain. File transfer used the SSH alias's working exec transport and verified SHA-256 after the skill's SCP route dropped the configured proxy.

Seven synthetic verdict tests passed locally. The copied results carry `_argv` and `_config`. The receiver rows and timings remain under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/out/phase1_attempt01/`. Every remote file in the manifest verified, including the four raw row files. [Results and runtime config](results.json) · [Remote MD5 manifest](MD5SUMS.txt) · [Run log](run.log)
