Active task: .trellis/tasks/09-22-tf-production-gap-audit

# Codex Astra brief — where should `CODELAY`'s advantage concentrate? A ρ/SNR map from the decision window (fixed question)

Written 2026-11-18 by Claude for Eric. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Read-only: write nothing to the repo. Your final message is the deliverable, which Eric saves as
`.trellis/tasks/09-22-tf-production-gap-audit/research/astra-gain-map-20261118.md`.
Model: `gpt-6.2-astra`. Pass `-m` on any resume and check the log `model:` line.

## Role and limits
Answer only the questions below. No research directions, paper framing or experiment design beyond the explicit prediction asked in Q4.
Zero receiver simulation. Symbolic work and small in-memory numerical computations are allowed, including Monte Carlo over the
**channel law only** (path powers and delays); no receiver or decoder runs. Mark every claim derived, numerically checked or assumed.
Do not read per-unit rows of any run. The admission-law replay is running now, and its outputs must stay unseen.

## Established inputs (cite; do not re-derive)
- Your window on the ideal slice (`astra-prediction-rule.md` in `.trellis/tasks/11-18-admission-law-test/research/`, and
  `astra-producer-consumer-20261118.md` A6.3). Scalar favours the duplicate and full/`CODELAY` favours the missing weak path when
  `1 + 2E/(u+λ) < R < 1 + 2(E+u)/λ`, where:
  - `R = |H_s|²/|H_w|²`;
  - `E = ‖pilot + μ‖²`;
  - `u = Σv`;
  - `λ = σ²`, in receiver-internal units.

  The finite-spacing version is Eq. (13).
- Fable's 11-11 form: `θ_sc = λ'/(2E + λ')` with `λ' = N v̄ + σ²`, giving `θ_sc ≈ v̄/(2 − v̄)` in unit power. See
  `research-assets/prediction-ledger.md`, section 2026-11-11.
- Observed (descriptive, Q2 common triggers, cap 8, frames 10000–10999), from `experiments/slot_mismatch_20261019/out/RESULTS.md`:
  - The `CODELAY`-minus-scalar rescue gap D8 is about 43–50 pp at physical ρ = .3 and about 7 pp at ρ = .5.
  - The scalar arm's phantom-first share is 93.8% overall.
- Receiver conventions and the channel law are in code and audit reports: `experiments/generator_snr_audit_20261019/REPORT.md`, the P1
  generator it audits, and `experiments/tf_e3_sbl_20261017/PROTOCOL.md` §2. The internal convention has data power .5. Physical ρ and SNR
  map to internal σ² by a scaling stated there. Verify the mapping from code; do not assume it.

## Questions
1. **Scaling.** Express E, u and λ in receiver-internal units as functions of physical pilot fraction ρ, SNR and the mean posterior
   symbol variance v̄ (0 ≤ v̄ ≤ data power) of a frame. Show the window bounds as functions of (ρ, SNR, v̄). Which bound moves most
   with ρ?
2. **Window occupancy under the channel law.** For P = 8 paths with the generator's gain and delay law, compute in memory the
   probability that the strongest missing path's ratio R (relative to the strongest retained path) falls inside the window.
   - Assume missing paths are the weakest ones. State the assumption, or take it from the generator's audit if it gives one.
   - Compute over a grid ρ ∈ {.2, .3, .4, .5}, SNR ∈ {4.5, 6, 8} dB and v̄ ∈ {.05, .15, .3}.
   - Say which v̄ is plausible for F0-failed frames, and why.
3. **Retrospective check.** Does Q2's map predict the observed ordering, a large gap at ρ = .3 and a small one at ρ = .5? Does it predict
   roughly the magnitude, given that D8 is a rescue gap and not an occupancy?
   - Be explicit about what the map cannot explain: the rescue conversion and pre-emption.
   - This is retrospective, and the answer must be labelled so.
4. **Prospective prediction.** For ρ ∈ {.2, .4}, which were never run, give a predicted ordering and a range for the window-occupancy
   share at triggered frames. A future run could test this. State the assumptions that fix the numbers.
5. **Limits.** Which approximations (ideal slice, κ = D, single missing path, v̄ uniform) most threaten the map, and in which direction
   would each bias it?

## Output format (final message, English, ≤ 140 lines)
`## Q1` … `## Q5`, then `## Verdict`: one line each on whether the window predicts the ρ ordering (yes / no / undetermined) and the
prospective ranges for ρ = .2 and .4.
