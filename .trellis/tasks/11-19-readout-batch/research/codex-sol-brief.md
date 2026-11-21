Active task: .trellis/tasks/11-19-readout-batch

# Codex Sol brief: zero-cost readout batch (aggregation of saved rows only), then STOP

Written 2026-11-19 by Claude; Eric approved ("Launch both"). Treat this brief as the approval. Confirm `model:` is `gpt-6.2-sol`.
Read-only aggregation of **saved rows** (no receiver, detector or decoder call, no new frames). Code and outputs in
`experiments/readout_batch_20261119/` (local) and `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/readout_batch_20261119/out/`
(deinlab, CPU, ≤16 processes, tmux `g_readout`, cap 1 core-hour). Do not edit frozen experiments, cards, STATE or the skeleton.
Decision rules below were written by Claude before any computation; apply them literally, and report numbers even when a rule
fails. Label everything post hoc. Field names in the rules come from other models' reading of the code: if a field differs, use the
equivalent field and say so.

Sources: `.trellis/tasks/09-22-tf-production-gap-audit/research/idea-harvest-{astra,agy,devin}-20261119.md` (full definitions).

| ID | Readout | Rows | Rule |
|---|---|---|---|
| R-A | Pilot economy on the same frames: 1% FER crossings of F0, B_8 (A1c on triggered else F0) and true-H A3, family M, ρ .3/.5, both scenarios; Δ_X = [c(X) − c(A3)]_{.3} − [c(X) − c(A3)]_{.5}; frame bootstrap | slot_mismatch main_20261118 (Devin #1 recipe; crossing routine `phase3_crossings.py`) | Survives if Δ_F0 95% lower > .5 dB and Δ_B8 95% upper < .75 dB |
| R-B1 | β, EM convergence, output co-delay pairs, NMSE by arm (R0, U2, K′, M, KM′), stratified by SNR | sbl_residual_gap main_v2_20261119 (agy I1) | Descriptive; report whether K′ restores β/convergence to R0 per SNR stratum |
| R-B2 | Among keys where U2 fails and R0 succeeds: 2×2 table of (K′ fixes, M fixes) | same | "Two mechanisms" if both off-diagonal cells ≥ 15% of the set; "one mechanism" if one off-diagonal cell < 5%; else unresolved |
| R-C1 | Fraction of defined rows with designated phantom gain > true-delay gain, per arm (A2, CODELAY), pooled over ρ, R | ratio_sweep main_v2_20261119 (Devin #4) | Survives if A2 ≥ .8 and CODELAY ≤ .3 |
| R-C2 | Same-frame propagation: frames where both C-hi and C-lo reach exchange round 2; per frame the count of round-2 trials with nonempty Π_lo, C-lo minus C-hi; share of the net difference contributed by frames where only C-lo's first accepted edit added an atom at an existing delay | unified_cov_prospective main_20261119 (Astra #1) | "First-step phantom drives the gap" if that share ≥ 80%; else report only the count bound |
| R-D | October common-failure check: on frames where F0 fails at both ρ .3 and .5 (5 dB, per scenario), conditional rescue by true delays (GS-set) and by true channel (A3) at each ρ | tcom_reference_frame_20261015 + tcom_genie_support_20261016 (Astra #2) | Survives if low-ρ rescue 95% lower > 75% and high-ρ rescue 95% upper < 10% in both scenarios |
| R-E | Doublet phase: for the 0.35-bin doublet, phase-aligned contrast fraction c = \|g1 − e^{i arg D_N(Δν)} g2\|² / [2(\|g1\|²+\|g2\|²)] from truth; compare CD-only two-atom frames and U-only-failure frames vs both-two-atom frames, stratified by doublet delay (6 vs 22); also anti-phase (cos Δφ < −.5) minus in-phase (> .5) omitted-energy share among single-atom frames | doublet_conflict main_20261119 (agy I2, Astra #3) | Anti-phase selective harm survives if within-delay median-c lift ≥ +.10 and Mann–Whitney p ≤ .05; phase explanation of tolerance survives if the anti-minus-in-phase omitted-energy 95% lower > 0 |
| R-F | Non-Berkson overfitting: undecoded vs decoded triggers at 4.5–6 dB: median/IQR of r_norm = residual_power/σ² and c_ratio = (residual_power − σ²)/uncertainty_power (uncertainty_power > .05σ²) | sigma2_dd main_20261118 (agy I4) | Overfitting shown if median r_norm < 1.0 on undecoded triggers; unified negative-cross-term claim dies if median c_ratio ≥ .80 |

Deliverables: `experiments/readout_batch_20261119/READOUTS.md` (one section per ID: rows/fields used, numbers with 95% intervals,
rule outcome), `readouts.json` with `_argv`/`_config`, code; commit (HEREDOC, no push, no amend; index.lock retry 30 s × 10).
Final message (English, ≤ 12 lines): commit hash; one line per ID with the rule outcome and headline number; core-hours; `model:`.
