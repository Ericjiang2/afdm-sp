Active task: .trellis/tasks/09-22-tf-production-gap-audit

# Codex Sol brief: two read-only readouts on archived units (no new frames), then STOP

Written 2026-11-19 by Claude. Eric delegated all approvals to Claude for fully automatic work. Treat this brief as the approval: do
not stop to ask for design approval, and if a Trellis hook asks for it, note that this brief is the approval and continue.
You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Confirm `model:` is `gpt-6.2-sol`.

These are **post hoc descriptive readouts**, not pre-registered tests. Report numbers only. Do not label anything SUPPORTED or REFUTED.

## Hard rules
- No new frames. Use only archived units and deterministic replay of archived keys through frozen code. Frozen sources are read-only.
  New code goes in `experiments/zero_sim_readouts_20261119/`.
- deinlab: test reachability only with `ssh -o ConnectTimeout=15 deinlab true`. CPU only, one thread per process, at most 16 processes,
  tmux `g_readouts`, outputs under that experiment's remote `out/`. Hard cap: **3 core-hours**.
- Other Sol sessions (tasks `11-19-sbl-spectral-split` and `11-18-ratio-sweep`) run at the same time and commit their own paths. Never
  stage their files. If a git command fails on `index.lock`, wait 30 seconds and retry, up to 10 times.
- Do not edit `STATE.md`, result cards or the skeleton.

## Read first
- `experiments/admission_law_20261118/` (`PROTOCOL.md`, `replay.py`, `gates.py`, `out/RESULTS.md`): archived units, row schema, and the
  replay path that reproduces them.
- `.trellis/tasks/09-22-tf-production-gap-audit/research/zero-cost-readouts-20261119.md` §1: what R2 is for.

## R1. Premise of blind model-order selection (scalar vs CODELAY phantom rewards on a noise scale)
**Units**: the 7,667 admission-law units, arms A2 (scalar) and A1c (CODELAY), first exchange only.

**Per unit and arm**, compute three gross Schur gains (the reward for adding the atom, before any deletion proxy):
- G_P: the best measured phantom gain;
- G_T: the best gain over candidates on true missing delays;
- G_F: the best gain over candidates on false new delays (unoccupied, not true).

The archive logs only per-slot class winners. If G_T and G_F cannot be separated from the rows, replay the units through the frozen
admission-law path with extended logging. Prove parity on the archived fields first. If the cap requires it, use a seeded random
subset of at least 1,500 units.

**Report, per arm**:
- quantiles of G_P/λ, G_T/λ and G_F/λ, where λ is the logged ridge (σ²);
- the OLS slope of log G_P on log |h̃_anchor|²;
- AUC(G_T vs G_P) and AUC(G_P vs G_F);
- for c on a log grid, the curves P(G_P > cλ), P(G_F > cλ) and P(G_T > cλ);
- the smallest c with P(G_P > cλ) ≤ .05 and P(G_F > cλ) ≤ .05, and P(G_T > cλ) at that c.

Also report the same quantities split by unit trigger status if available.

## R2. Real decoded-variance spectrum and cross-delay coupling (AFDM vs OFDM factor)
**Units**: a seeded random subset of 1,000 admission-law units (all are failed frames).

**Procedure**:
- Replay F0 round 1 through frozen code, with parity on the archived E and u.
- Obtain the per-symbol APP variance vector v in the same domain and convention that Γ uses (`gamma_full` / `_gamma_cross` with
  `fft(v)`).

**Report**:
- quantiles over units of |v̂[d]|/u for d = 1, 2, 3, and of max over 1 ≤ d ≤ 102 of |v̂[d]|/u;
- over the F0 retained atoms of each unit with ℓᵢ ≠ ℓⱼ:
  - the realized max |Γᵢⱼ|/u from the frozen `gamma_full`;
  - the OFDM counterfactual max of |D_N(Δν)|·|v̂[d]|/u for the same pairs (no chirp shift);
- quantiles of both, and of their ratio;
- one sanity check: the realized values agree with the closed form |D_N(Δν + 2Nc₁d)|·|v̂[d]|/u to within 1e-10 relative.

## Deliverables
- `experiments/zero_sim_readouts_20261119/` with code, `README.md` (what was run, receipts with `_argv`/`_config`, parity results) and
  `out/summary.json`.
- Commit: stage only that directory (small files) and this brief's sibling result note if you write one. HEREDOC message, no push, no
  amend.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- parity;
- the R1 headline numbers per arm (median G_P/λ, AUCs, the separating c and P(G_T > cλ));
- the R2 headline quantiles (median and 95th percentile of max_d |v̂[d]|/u; the realized-vs-OFDM ratio);
- core-hours used;
- the confirmed `model:`.
