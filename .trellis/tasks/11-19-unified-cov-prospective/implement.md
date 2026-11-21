# Implement — unified covariance prospective test

1. **Phase 1 (Sol, ≤ 3 core-hours).** Verify that the fresh frame block is unused and record the method. Implement U2 and the CSTATE
   A2 / U arms, then pass G1–G3. Report the leverage readouts (φ_lo half-width from old rows; archived A2 − A1 FER gap) and project the
   main-run cost from smoke timing × 1.3. Write the verdict code with synthetic tests. Commit; the protocol stays DRAFT.
   - Check: all gates pass with receipts, and no fresh-frame simulation has run.
2. **Freeze (Claude).** Merge Astra's blocking items and Sol's revisions into the experiment `PROTOCOL.md` and mark it frozen. Write a
   freeze record and commit before any main run.
   - Check: the freeze commit precedes the first fresh-frame row.
3. **Main run (Sol).** One unattended chain with a cost stop and a DONE/STOPPED status line. Aggregate and run the frozen verdict code
   unchanged, return small files with MD5s, and commit.
   - Check: the key count matches the plan, and the verdicts come from the frozen code.
4. **Report (Claude).** Write the three-layer card (draft), the correction to res-20261119-02, the STATE line and the process log.
   Score the predictions.

**2026-11-19 — Phase 1.** Confirmed `model: gpt-6.2-sol` and cleared P1 frames 4400–4599 before receiver execution. Implemented the six SBL and four CSTATE arms from the approved brief, exact per-trial CSTATE Γ_U scoring, the projector census and §4 verdict tests. deinlab G1–G3 passed after correcting duplicate initialization of the shared frozen P1 context during the read-only preflight. Archived φ_lo half-width was 0.0857 at 1,200 keys and 0.0606 at 2,400 by square-root extrapolation. The split-prospective whole-grid A2 − A1 FER difference was +4.531 pp [3.984, 5.094]. Projected main cost was 19.008 core-hours for the full grids. The protocol remains DRAFT and the fresh block remains blind. [Qualification report](../../../experiments/unified_cov_prospective_20261119/out/phase1_20261119/RESULTS.md) · [DRAFT and revision reasons](../../../experiments/unified_cov_prospective_20261119/PROTOCOL.md)

**2026-11-19 — Phase 1b.** Confirmed `model: gpt-6.2-sol` and extended the blindness check to 4600–4699. Implemented the
C-hi/C-lo mirror arms, fixed-projector objective checks, isolated admission-law gate, saved-first-exchange V5-adm and §10 verdicts.
deinlab G1–G3 passed, with A2 parity on eight same-harness archived K keys and 10/10 closed-form admission cases. Replay of the
200-frame Stage 3 archive slice selected m = 0.500 pp and FER-primary V5 from maximum ψ half-width 0.0231, with 894 V5-adm units per
200 frames. The selected schedule has 200 SBL frames and 19.438 projected total core-hours. Phase 1b used 0.923 core-hours.
The protocol remains DRAFT and fresh frames remain blind. [Phase 1b qualification report](../../../experiments/unified_cov_prospective_20261119/out/phase1b_20261119/RESULTS.md)

**2026-11-19 — Phase 2.** Confirmed `model: gpt-6.2-sol`. The deinlab main chain finished DONE in one attempt, with 2,400 SBL and
6,800 CSTATE keys on frames 4400–4599. It used 18.178 of 25 core-hours and peaked at 31 processes including the supervisor. Producing
commit `3ca53c08` adds launch and aggregation glue for the supervised chain. The protocol, receivers and verdict code match freeze
`7061ad84`. The old pilot and aggregation input checks passed before launch, and all 28 raw-shard MD5s verified on deinlab.
Both crossover premises were established. The frozen spectral mechanism, operational compatibility and joint layers were supported.
[Phase 2 results and receipts](../../../experiments/unified_cov_prospective_20261119/out/main_20261119/RESULTS.md)


## 关闭说明（2026-11-19，Eric 在收官时接受）
结果见 res-20261119-03；证明 v2 在 09-22 research/proofs-20261119/；操作层由 res-20261119-04 收窄。
