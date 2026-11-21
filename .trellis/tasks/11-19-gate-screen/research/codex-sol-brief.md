Active task: .trellis/tasks/11-19-gate-screen

# Codex Sol brief: identifiability-gate screen (no FER, no fresh frames), then STOP

Written 2026-11-19 by Claude; Eric approved ("做门控筛查"). Treat this brief as the approval. Confirm `model:` is `gpt-6.2-sol`.
Another Sol session (task `11-19-readout-batch`) may be running: never stage its files; index.lock → retry 30 s × 10.
Code in `experiments/gate_screen_20261119/`; deinlab CPU only, ≤16 processes, tmux `g_gate`, outputs under its `out/`, cap 2 core-hours.
Frozen sources read-only. No decoding outcome is computed or reported. Truth is used only to locate the true doublet for scoring.

## The gate (from `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-gauge-derivation-20261119.md` §2; freeze it as written)
For a co-delay pair (or block) at a frozen soft-symbol mean x̄ with dictionary B (mean-waveform columns), uncertainty Γ (closed-form
co-delay block, u = Σv) and ridge λ*: V0 = (Γ + λ*I)⁻¹, V1 = (Γ + λ*I + BᴴB)⁻¹. For the phase-aligned contrast p of a pair, the gate
**floors** the contrast iff 2·pᴴV1p > pᴴV0p. For blocks > 2 atoms: floored subspace = positive eigenspace of (2V1 − V0) restricted to the
block's normalised Dirichlet modes with eigenvalue < 1. λ* = σ² in support exchange; λ* = λ + u/N at SBL initialisation.

## S1 — MIXED8 true doublets (the one-rule test)
- States: the archived doublet-conflict frames 1000–1599 (already used; old) at 7 dB, ρ .5, triggered frames only; the shared state is
  F0's output entering the CSTATE exchange (x̄, v, σ²). Reconstruct it deterministically with the frozen code (same as the CD/U arms'
  entering state); verify bit-identity of the entering support with the archived rows on ≥ 20 frames.
- For each triggered frame, take the 0.35-bin true doublet (delay and two true Dopplers from truth), build the pair B at those true
  positions with x̄, and apply the gate. Also report the 0.75-bin doublet (control; expected unfloored).
- Report the floored fraction with a frame-cluster 95% interval, stratified by doublet delay (6 / 22).
- **Frozen rule:** the one-rule claim **fails** if the 95% lower bound of the 0.35-bin floored fraction is ≥ .50; **passes the screen**
  if the 95% upper bound is < .50; otherwise uncertain.

## S2 — SBL initial grid (descriptive)
- States: E-3c / unified-SBL keys from old frames 4400–4599 (archived, ρ .3, 6–11 dB; any 200 seeded keys), at EM initialisation on the
  initial candidate grid, λ* = λ + u/N.
- Per co-delay block, compare the gate's floored subspace with S-lo's Π_lo (eigenvalue < .5): dimension of each, and overlap
  = tr(P_gate Π_lo)/rank(Π_lo). Report median and quartiles of rank(P_gate)/rank(Π_lo) and of the overlap, by SNR.
- No rule (descriptive); Astra predicted overlap < 90% and fewer floored modes (≈15 vs 18 on a full 25-atom block).

Deliverables: `SCREEN.md` (method, verification, S1 with rule outcome, S2 tables), `screen.json` with `_argv`/`_config`, code; commit
(HEREDOC, no push, no amend). Final message (English, ≤ 10 lines): commit; S1 fraction + interval + rule outcome (+0.75-bin control);
S2 medians; core-hours; `model:`.
