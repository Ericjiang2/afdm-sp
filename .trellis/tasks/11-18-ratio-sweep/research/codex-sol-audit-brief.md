Active task: .trellis/tasks/11-18-ratio-sweep

# Codex Sol brief: post hoc audit of the P2/P4 refutation (read-only on main v2 rows), then STOP

Written 2026-11-19 by Claude (research-checkpoint §3: audit before explaining). The frozen verdicts stand and must not be relabelled.
This is a **post hoc audit**. Report numbers only, and label everything post hoc. Eric delegated approvals; do not stop to ask.
Confirm `model:` is `gpt-6.2-sol`.

## Why
In the A2 arm, the designated phantom beats the designated weak candidate even at R = 1.5–4, where the closed-form window predicts the
weak path. The CODELAY arm behaves exactly as predicted. The weak candidate sits on a delay with no co-delay atom, so its Schur gain is
identical in both arms; only the phantom side differs. The admission-law replay validated the A2 phantom-reward model (0.8% median
error). The audit must separate two possibilities:
- (i) the prediction inputs (E, u, λ, κ, h̃) do not match the quantities the receiver's scoring uses (a unit or definition mismatch);
- (ii) the measured weak-candidate reward is much smaller than the model's E²|h_w|²/T (H2).

## Audit items
Use the main v2 rows plus deterministic replay of the same units through the frozen code if a needed field was not logged. Truth may
be used. Take a seeded subset of at least 2,000 units balanced over (ρ, R) if a full pass exceeds 1 core-hour.

1. **Phantom side.**
   - Model: Astra's finite-spacing formula `|Tκ − q_a|²|h̃_j|² / (T − |q_a|²/T)` with the unit's E, u, λ, κ, D and fitted anchor gain,
     for A2 (q = Eκ) and CODELAY (q = Eκ + uD).
   - Compare with the logged designated phantom gains: median relative error and Spearman, per (ρ, R).
2. **Weak side.**
   - Model: E²·|h_w|²·|D(δ_w)|²/T, with |h_w|² the true weak gain in the receiver's internal scaling and δ_w the weak path's offset from
     the designated weak candidate's Doppler.
   - Compare with the logged designated weak gain: the distribution of the ratio measured/model, per (ρ, R).
   - Also report |b_w|/(E|h_w|), where b_w = B_wᴴ r at the deletion slot's support.
3. **Berkson calibration.** Using the true data d, report γ = (‖pilot‖² + Re μᴴd)/E and κ_cal = ‖d − μ‖²/u, per (ρ, R).
4. **Aliasing check.** The share of units whose masked-F0 support holds an atom at delay ℓ_w ± 1 with Doppler within 1 bin of
   ν_w ∓ 2Nc₁ (the d = ±1 resonance).
5. **Unit-consistency check.** Recompute E, u and λ from the scoring's own internal arrays for 20 units, and compare them with the logged
   values to 1e-12.

## Rules
- Read-only with respect to the frozen experiment: write new code in `experiments/ratio_sweep_20261118/audit_v2/`. Do not touch
  `out/main_v2_20261119/` except to read it.
- deinlab: CPU only, ≤ 16 processes, tmux `g_sweep`. Cap 1.5 core-hours.
- Another Sol session (task `11-19-sbl-spectral-split`) is running. Never stage its files. On `index.lock`, wait 30 seconds and retry, up
  to 10 times.

## Deliverables
- `experiments/ratio_sweep_20261118/audit_v2/AUDIT.md`, containing the tables above, labelled post hoc, plus `audit.json` with
  `_argv`/`_config`.
- Commit with a HEREDOC message, no push, no amend.

## Final message
English, ≤ 12 lines, containing:
- commit hash;
- item 5 pass or fail;
- per item, the headline numbers at ρ = .3 for R ∈ {1.5, 4, 12, 64}, and ρ = .5 pooled;
- core-hours used;
- the confirmed `model:`.
