# Codex Astra brief: derive the detector-absorption fraction α (read-only derivation)

Written 2026-11-19 by Claude after Eric asked for it ("吸收比例推导先让 Astra 做"). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: write nothing to the repo. Your
final message is the deliverable. Model: `gpt-6.2-astra`.

## Role and limits
- Derive; do not propose research directions or paper framing.
- No receiver simulation. You may read code, read the small audit JSON/MD files listed below, and run small in-memory numerical checks
  (for example a scalar or toy-dimension Monte Carlo of your own model). Keep any check under about 5 CPU-minutes.
- Mark every claim as derived, numerically checked or assumed.

## The measured phenomenon (post hoc, res-20261119-01)
- **Setup.** In the forced-miss sweep, the weak designated path w is masked from F0, so round-1 detection runs with w unmodelled.
- **Closed-form failure.** The closed-form window models the missing-path reward as E²|h_w|²/T (Berkson premise: the soft-symbol error
  e = x − μ is independent of the residual). The measured reward falls short of it.
- **Measured/modelled reward.** .27 / .35 / .45 / .85 at ρ = .3, R = 1.5 / 4 / 12 / 64, and about .39 at ρ = .5.
- **Decomposition.** The residual's projection on the missing-path column is about .50–.64 of E|h_w| at low R. The deficit comes from
  the support's data-error term b2 = Σ_p A_p (x − μ) h̃_p projected on that column: median −.30 to −.37 of E·h_w at R ≤ 12 for both ρ.
  - At ρ = .5 it stays at −.31 even at R = 64.
  - At ρ = .3, R = 64 it falls to −.01, where most masked-F0 frames decode.
- **What is ruled out.** The soft mean is calibrated on average (γ = .93–1.03), so the deficit is not a global miscalibration.
  Gain-error, noise and other-path terms are each < 1%.
- **Definition.** α ≡ −Re(projection of b2 on the missing-path column)/(E·h_w), the fraction of the missing path's projection cancelled
  by detector absorption. The measured α is about .30–.37.

## Material
- `research-assets/res-20261119-01.md`;
- `experiments/ratio_sweep_20261118/audit_v2/AUDIT.md`, `AUDIT2.md`, `audit.json`, `audit2.json`, `decompose.py`;
- protocol `.trellis/tasks/11-18-ratio-sweep/research/protocol-v2-DRAFT.md` §6 (your finite-spacing window);
- the round-1 detector: find it from `experiments/ratio_sweep_20261118/forced_miss.py` and the F0 driver it imports. Report exactly what
  round 1 is (equaliser, soft demapper, whether LDPC decoding precedes the APP used for μ, and the clipping in `moments`).

## Questions
1. **Mechanism model.** Give the simplest model of round-1 detection with an unmodelled path that predicts a nonzero α. State its
   assumptions. Derive why e = x − μ acquires a component aligned with the missing path's contribution seen through the retained strong
   paths. Explain why α is negative-signed relative to h_w, and why it is not removed by the calibration γ ≈ 1.
2. **Closed form.** Derive α as a function of the quantities available per unit or cell (E, u, λ = σ², ρ, R, the decode outcome or
   syndrome state, and the coherence between the missing-path column and the retained columns). Include the limits:
   - decoded frames (u → 0) should give α → 0, consistent with ρ = .3, R = 64;
   - an undecoded heavy-interference regime should approach a plateau, consistent with ρ = .5 staying near .31.
3. **Check.** Compare the predicted α with the measured cell medians in AUDIT2 (both ρ, all R). Report the deviations. Say which part of
   the data the model fails, if any.
4. **Corrected window.** Give the corrected admission condition with α included, that is, the missing-path reward multiplied by the right
   factor. Predict where the scalar 50% flip should move (ξ₅₀ or R₅₀) for the sweep's cells, and compare with the observed ξ₅₀ ≈ .13–.18.
5. **Cheapest prospective test.** Name the cheapest test of the corrected window on fresh frames: which population, which statistic, and a
   decision rule with no free parameters. Do not run it.

## Final message
English, at most 50 lines:
- the round-1 detector as found;
- the model and its assumptions;
- the closed form for α and its limits;
- the comparison table with AUDIT2;
- the corrected window and the predicted flip;
- the proposed prospective test;
- the confirmed `model:`.
