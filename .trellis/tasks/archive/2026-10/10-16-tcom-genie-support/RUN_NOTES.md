# Run notes — genie-support audit

- Main run deinlab 2026-10-16 09:02–09:18 UTC, 96 single-thread shards, 64000 rows, 0 failures, 24.1 core-hours wall-summed
  (S6 projected 10.9 from a 20-frame smoke; the slowdown came from shared cores, not more work). Rows are gzipped remotely (19 MB),
  md5 list in `experiments/tcom_genie_support_20261016/out/main/REMOTE_ROWS_MD5.txt` (md5 of the list 7b271c74…).
- Analysis: `experiments/tcom_genie_support_20261016/out/analysis/{GS_RESULTS.md, gs_results.json}`.
- **Stop rule (protocol §3 H-S3) triggered in 4/4 cells.** x(GS-multi) − x(B) at FER 1e-2 is +.12 to +.36 dB with CI entirely
  above 0. Per protocol, no card is written until the user decides.
- Pre-registered NMSE verdicts (from the same analysis, not yet carded):
  - H-S1 SUPPORTED 4/4: f_set = .73–.81 at 6.5–8 dB (CI lo ≥ .68).
  - H-S2 per cell: U ρ.5 SUPPORTED (r_multi 1.9–2.3 dB, NEAR); G ρ.5 INCONCLUSIVE (8 dB CI hi 3.05); G ρ.3 and U ρ.3 REFUTED
    (4.5–5.3 dB, GAP).
- Not anticipated by the protocol: all 4000 (scenario, frame) channels have 8 distinct delays (the D2 delay grid), so GS-set and
  GS-multi differ only in slot order (mult step ≈ 0 dB). The multiplicity step of the decomposition is empty for this generator.
- Post hoc check (after the stop rule, not pre-registered; P1 ledger F0, 5000 weights): x(F0) − x(GS-set) = G ρ.3 1.52 [1.17, 1.97],
  G ρ.5 .43 [.32, .55], U ρ.3 1.09 [.89, 1.74], U ρ.5 .28 [.19, .38]. Under the same schedule (no CSTATE), true delays beat F0.
  B beats GS, so the CSTATE branch gains more FER than delay recovery alone gives.
- A1 (post hoc GS+C) run deinlab 2026-10-16 09:45–09:54 UTC, 96 shards, 64000 rows, 0 failures, 14.1 core-hours wall-summed.
  Rows gzipped remotely (3.4 MB) under `out/a1/`, md5 list in `out/a1/REMOTE_ROWS_MD5.txt` (md5 of the list c8f620ad…).
  Analysis `out/analysis/{A1_RESULTS.md, a1_results.json}`. The 640 A1 smoke rows were deleted after the gate (summary in
  `out/a1_gates/gates_a1.json`); the main-gate smoke rows are kept gzipped remotely under `out/smoke/`.
