# Headroom ladder: where does deployed-to-PCSI gap live

## Goal

Replace open-ended method search (Codex session 01a1050f, 2026-10-04..08, looped on
local Doppler-uncertainty / pair-covariance VB) with one decisive measurement:
decompose the deployed-to-PCSI coded gap into acquisition, local-estimation,
model-truncation and detector terms. Direction for any further method work is
chosen from this decomposition, not from post-hoc failure chaining.

## Background (first-principles prediction, to be falsified)

- E1 (`research-assets/res-20260727-01.md`): deployed vs PCSI gap 0.754 dB @FER 1e-1,
  1.012 dB @1e-2 (N1024, P8, rho .5, n_outer 10, 800 frames/pt).
- CRB-regime local error costs sigma^2/(2N) residual per real parameter
  (gain-refit Doppler: J = (2|h|^2|x|^2/sigma^2) N pi^2/3; residual = |h|^2|x|^2 (pi^2/3) E[delta^2]).
  Loss_local ~= 10 log10(1 + K_r/(2N)) ~= 0.05 dB for K_r = 24, N = 1024 (data-aided).
  Uncertainty-aware detection gain <= Loss_local.
- Prediction H0: >= 80% of the gap is in acquisition (support / path count / gross Doppler)
  and/or model truncation, not in local CRB-regime error.

## Requirements

1. Same frames, same detector, same LDPC, same SNR grid across all arms (paired by seed;
   pairing proven by per-frame equality of a shared field, as E1 did).
2. Physical G1 world, count-blind production receiver B = F0+TF+CSTATE20 (E1 world rejected:
   G0 generator lies inside receiver class + genie n_paths=P_actual). Arms (design.md):
   - A0 B (F0 readout free).
   - A1 genie delays + same-delay multiplicity, estimated Doppler + gains.
   - A2 genie geometry (delay + continuous Doppler), estimated gains.
   - A3 true H fixed.
   Plus E-rho: pilot fraction rho in {.2,.3,.4,.5} x total SNR grid, arms A0/A2/A3 (theory T3).
3. Metrics per arm/SNR: coded FER, BER, per-frame bitwise GMI of LLRs
   (1 - E log2(1+exp(-s L))), dB shift at FER 1e-1 / 1e-2 with frame-block bootstrap CI.
4. results.json carries `_argv` + `_config` fingerprint (project CLAUDE.md rule).
5. Remote: deinlab, /data/guoyikun only, tmux g_ prefix, nvidia-smi before GPU use.
6. Proportional ceremony: commit before/after run, md5 of big files in notes; no per-file
   SHA admission rituals.

## Kill / route rules (pre-registered)

- If gap(A2->A3) + gap(A1->A2) < 0.1 dB @FER 1e-1: close all local-uncertainty method lines
  (continuous-Doppler VB, collapsed gain, pair covariance) permanently for this regime.
- If gap(A0->A1) dominant (>= 50% of A0->A3): next direction = acquisition
  (data-aided global re-acquisition; pilot-fraction threshold analysis).
- If gap(A3p->A3) dominant: next direction = model class (tail / full-physical operator).
- If A3 itself far from a detector bound: detector term flagged (not measured in this task).

## Acceptance Criteria

- [ ] design.md fixes arm list, injection points, frames, SNR grid, compute budget.
- [ ] Smoke run (small frames) passes pairing + fingerprint checks.
- [ ] Full run: dB-gap table with CIs for each ladder step; route decision written.
- [ ] Result card `res-YYYYMMDD-NN` drafted; STATE.md untouched unless user approves.

## Out of scope

- Changing production rho (needs user decision; separate task if routed).
- Codex mission CSV `.mission/20261007-sp-fractional-trans/` rows: left as-is, not executed.
