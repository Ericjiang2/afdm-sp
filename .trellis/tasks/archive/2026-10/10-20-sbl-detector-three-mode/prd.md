# SBL detector three-mode exploratory pilot

## Authorization and scope
The user approved the proposed fixed/point/joint diagnostic and asked to obtain one useful small result before deciding further work. This is a bounded exploratory follow-up of Pilot 5, not independent confirmation, a new method campaign, or claim promotion.

## Question
On identical scalar/full-Gamma SBL outputs, does the scalar receiver's deterioration appear with gain-mean updates alone, or only/additionally with gain-variance propagation?

## Acceptance
- Reconstruct the frozen Pilot-5 pipeline without changing SBL or production detector mathematics.
- Compare fixed, point, and joint with identical observations, support, initial gains, decoder check prior, 20 iterations, and damping .3 within each SBL output.
- Use the predetermined first 50 old frame clusters (9100..9149), U/G, rho .3, 7/8 dB: 200 paired keys. Never select the main sample by old success/failure.
- Preserve all attempts and compare replayed fixed/joint results against the old row decisions before accepting any row.
- Save per-iteration composite-channel NMSE, data-symbol MSE and symbol uncertainty; final decoder outcomes and detector extrinsic bit log loss. Truth is scoring-only.
- Fail on source/parity/nonfinite/missing-row errors; do not silently exclude failed rows.
- Report paired frame-cluster intervals and outcome transitions, distinguish observation from interpretation, and stop after this pilot regardless of significance.
- Bound execution to CPU only, at most 12 one-thread processes, 20 wall minutes / 4 core-hours including engineering, whichever binds first. No broad grid or automatic expansion.
- Produce a short result with source/config/raw hashes and explicit limitations. No accepted result-card revisions or GitHub push.

## Context
Parent: `.trellis/tasks/09-22-tf-production-gap-audit/`.
Protocol: `protocol.md`. Existing point controls are generic, not an SBL-output comparison. Pilot-5 saved rows lack complex initial gains and trajectories, so deterministic SBL reconstruction is necessary.
