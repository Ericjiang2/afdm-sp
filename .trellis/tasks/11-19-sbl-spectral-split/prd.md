# SBL 谱分解检验：cov+ridge 的救回由哪一半承担

## Goal and background

E-3c's `cov+ridge` recovered 92% of the scalar/full-Γ FER gap. The spectral test asks whether that recovery comes from EM-SBL or `_system` refinement, then tests whether SBL recovery depends on the sub-resolution or resolvable directions, or on ridge trace. Eric selected this test on 2026-11-19 as the remaining SBL-reversal candidate in the sum/contrast synthesis. [E-3c result](../../../research-assets/res-20261018-01.md) · [Synthesis §§6.1, 7](../09-22-tf-production-gap-audit/research/ambition-synthesis-20261118.md)

## Phase 1 requirements

- Implement the nine arms and both iteration budgets in the new experiment directory using the read-only E-3/E-3c sources and the [task draft](research/protocol-DRAFT.md). Record the reason for each experiment protocol revision.
- On deinlab, use CPU, one thread per process, at most 16 processes, tmux `g_spectral`, and the experiment's own `out/` directory. The execution brief specifies `gpt-6.2-sol`. [Phase 1 brief](research/codex-sol-phase1-brief.md)
- Keep the 1,200 E-3c keys blind to new arms. Only the three known reference arms may run on the 20 seeded main keys for G1. Use synthetic inputs and the 12 smoke keys on frames 8400–8411 for new-arm checks. Smoke FER and NMSE are engineering logs.

## Acceptance criteria

- [ ] G1 exactly reproduces archived stage 1, round 1, candidate count, atoms, decoded SHA, information errors and NMSE for R0/R1/R2. G2 passes the matrix, trace, refinement, reuse and pruning checks at the specified tolerances. G3 reproduces every new arm on repeated smoke runs after removing timings. Retain receipts.
- [ ] Report the archive join decision, smoke timing for both budgets, eigenvalue census and projected cost. Use the prescribed 400-iteration subset reduction if the projection exceeds the draft 30 core-hour cap.
- [ ] Commit Phase 1 files and the dated execution record with the protocol marked DRAFT. End Phase 1 with the main run and freeze pending.

## Later phases

The 1,200 main keys are U/G × ρ=.3 × SNR 6–11 dB × frames 4000–4099. Their outcomes can support a retrospective replay; a prospective claim requires fresh frames. Later gates cover prediction registration, independent design review under research-checkpoint §1.5, Eric's freeze and budget, then the main run, three-layer result card and STATE update. [Execution plan](implement.md)
