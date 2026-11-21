# Unified covariance prospective test — Phase 1b qualification (2026-11-19)

Phase 1b ends with the protocol in DRAFT. The run used archived and previously used smoke keys. The expanded audit found zero P1 hits in 4600–4699 after verifying the original raw scan digests. The intersecting labels retain their two independent RNG identities. Frames 4400–4699 remain blind. [Extended audit](fresh_check.json)

| Gate | Result | Evidence |
|---|---|---|
| G1 | PASS | 20 SBL reference keys, 8 triggered Stage 3 F0/CD keys, and all 8 selected triggered split-prospective K archive keys for A2. A2 matched decoded hashes, errors, final support, accepted edits and final objective. [Receipt](g1.json) |
| G2 | PASS | U and C-hi reduced bit-exactly to CD and C-lo to A2 at τ=0 on 8 Stage 3 keys. Empty U2 refinement reproduced S-lo on 12 smoke keys. The three spectral CSTATE arms checked 3,750 synthetic and 82,400 smoke trial scores against the brute-force support solver. Maximum relative errors were 1.71e-15 and 1.44e-15. Fixed-projector pass descent and the V5-adm saved-state replay passed. [Receipt](g2.json) |
| G2 isolated admission | PASS | Ten arm/separation cases, at δ=.25 and .5 bin. Each singleton and pair was separately optimized. Maximum relative error against the closed forms was 2.24e-13 at tolerance 1e−8. [Receipt](g2.json) |
| G3 | PASS | 12 SBL and 8 CSTATE smoke keys reproduced after removing timing fields. [Receipt](g3.json) |

## Leverage

The archived split-prospective A2−A1 whole-grid FER gap was 4.531 pp, giving **m = 0.500 pp** by §10.4. The replay paired against CD on the Stage 3 grid gave an A2−CD gap of 2.853 pp, implying 0.500 pp under the same cap.

The Stage 3 leverage slice contains 6,800 keys across 200 archived frames, 4000–4199. 979 triggered keys were replayed and 5,821 nontriggers used the archived F0 outcome across all six arms. Bootstrap intervals used 20,000 paired physical-frame draws. The 95% half-widths for ψ were C-hi 0.0000, C-lo 0.0231. Their maximum was **0.0231**, selecting **FER** under §10.5. C-hi and CD had identical pass/fail outcomes on every old key, giving the empirical zero width for C-hi. The §10.4 companion one-sided bound for C-hi − CD on the old slice is 0.0437 pp. The old slice yielded **894 V5-adm units per 200 frames**. [Leverage receipt](leverage.json)

## Projected main cost

| Work | Core-hours with the 1.3 multiplier |
|---|---:|
| SBL, 200 frames | 18.252 |
| SBL, 300 frames | 27.377 |
| Six CSTATE arms, 200 frames | 1.185 |
| V5-adm, 200 CSTATE frames | 0.001507 |
| Total with 200 SBL frames | 19.438 |
| Total with 300 SBL frames | 28.564 |

§10.9 selects **200 SBL frames** for a total of **19.438 core-hours**. Receiver projections use smoke timings and the archived Stage 3 trigger rate. V5-adm timing uses the incremental cost in the old six-arm replay. The deinlab qualification chain consumed **0.923 core-hours**. [Timing and configuration](results.json)

The verdict suite passed ten synthetic tests, including the three layers, premises, rare-event bounds, H, V5 and V5-adm. The C-hi/CD rare-event bound is a companion readout to the §9 ratio verdict. Admission preferences are conditional on frames containing eligible units. [DRAFT and implementation decisions](../../PROTOCOL.md)

All raw row files remain on deinlab in `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/out/phase1b_attempt01/`. [Remote manifest](MD5SUMS.txt) · [Run log](run.log)
