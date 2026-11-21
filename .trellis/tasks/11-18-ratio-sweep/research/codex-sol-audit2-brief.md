Active task: .trellis/tasks/11-18-ratio-sweep

# Codex Sol brief: post hoc audit 2 — decompose the weak-column projection (one explanation, one falsifier), then STOP

Written 2026-11-19 by Claude. Continue from your audit (`b4e294cf`). Post hoc; frozen verdicts unchanged. Eric delegated approvals; do not
stop to ask. Confirm `model:` is `gpt-6.2-sol`.

## The single candidate explanation (Claude, untested, confidence M)
The round-1 soft symbols μ were detected with the weak path unmodeled. The support fit B_S(μ)h̃_S therefore absorbs part of the weak
path's contribution, so the residual's projection onto the weak column is only about half of E·h_w at low R. The stronger the masked
path (lower R), the more is absorbed.

## Falsifier: decomposition on the same 2,016 audit units
At the deletion-slot support S_s used for scoring, decompose the residual

r = y − B_S(μ)h̃_S

into:
- (a) the true weak-path signal A_w(x)h_w;
- (b) the support-fit error Σ_{p∈S} A_p(x)h_p − B_S(μ)h̃_S, split further into
  - (b1) a gain-error part Σ A_p(x)(h_p − h̃_p) and
  - (b2) a data-error part Σ A_p(x − μ)h̃_p;
- (c) the true paths not in S and not the weak path;
- (d) the noise.

For each term T, report the normalized projection Re[(B_wᴴT)/(E·h_w)] on the designated weak column B_w(μ), as the median and IQR per
(ρ, R). Check that the terms add up to the logged b_w within 1e-10 relative.

**Reading rule (fixed now, before you compute).** The explanation is supported if the sum (b1) + (b2) accounts for at least 60% of the
shortfall 1 − |b_w|/(E|h_w|) at R ≤ 4 for both ρ. It is falsified if (c) + (d) accounts for at least 60%. Otherwise it is mixed. Report
which of (b1) and (b2) dominates.

## Rules
Write new code in `experiments/ratio_sweep_20261118/audit_v2/`, read-only on main outputs. deinlab ≤ 16 processes, cap 0.5 core-hours. On
`index.lock`, wait 30 seconds and retry, up to 10 times. Commit with HEREDOC, no push.

## Final message
English, ≤ 10 lines, containing:
- commit hash;
- the closure check;
- per (ρ, R ∈ {1.5, 4, 12, 64}), the medians of (a), (b1), (b2), (c) and (d);
- the reading-rule outcome;
- core-hours used;
- `model:`.
