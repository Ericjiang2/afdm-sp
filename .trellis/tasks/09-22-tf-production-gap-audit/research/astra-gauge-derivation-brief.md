# Codex Astra brief: does a "representation redundancy (gauge)" principle hold, and what new rule does it predict? (read-only)

Written 2026-11-19 by Claude; Eric approved. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only; final message is the deliverable.
Model `gpt-6.2-astra`. No receiver simulation; small in-memory numerical checks allowed. Label claims D (derived) / N (numerically
checked) / A (assumed). Be adversarial: the candidate was proposed by Claude after seeing the data, so its fit to known phenomena is
not evidence.

## The candidate (Claude's, untested)
Near-coincident atoms create a representation redundancy: the pair has a physical direction (sum, the path itself) and a redundant
direction (difference, unidentifiable from data at coalescence). Thesis: "the uncertainty penalty must be exact (invariant) on
physical directions and gauge-fixed (floored) on redundant directions." Claimed to explain: scalar phantoms (sum mode mis-penalised),
SBL reversal (difference mode unfixed), the doublet cost of Γ_U (a resolvable true doublet's difference is physical, not gauge),
phantom propagation and the pilot-economy result. New prediction: the redundant set should be defined by **identifiability**
(Fisher information of the difference mode, depending on SNR, spacing, E, u), not by the fixed τ = .5; an identifiability-adaptive
floor should rescue SBL like S-lo **and** not suppress resolvable true doublets in MIXED8 — one rule for both stages.

## Material
`proofs-20261119/theory-astra-v2.tex` (Props, spectral extension, fixed-prior corollary), your spectral proposition
`.trellis/tasks/11-19-unified-cov-prospective/research/astra-spectral-proposition-20261119.md`, cards `research-assets/res-20261119-03/04/05/06.md`,
`.trellis/tasks/09-22-tf-production-gap-audit/research/idea-harvest-synthesis-20261119.md`.

## Questions
1. Can "physical vs redundant direction" be defined precisely so that it reduces to the existing statements (split reward depends only
   on the sum-mode penalty; fixed-prior contrast curvature) as special cases? Give the definition. Is "gauge" the right word, or is
   this ordinary identifiability / Fisher-information language? What does it add beyond the spectral statement already in Prop 2?
2. Derive the identifiability-adaptive floor: for a pair at spacing δ, which quantity decides whether the difference direction is
   identifiable (e.g. data-term curvature β‖Bp‖² vs prior/uncertainty terms), and what threshold rule replaces τ = .5? Express it in
   receiver quantities (E, u, λ, N, δ).
3. Predict, before any run: (a) for the E-3c SBL setting at ρ .3, 6–11 dB, does the adaptive rule select (nearly) the same directions
   as τ = .5? (b) for MIXED8 at 7 dB, are the 0.35-bin true doublets "identifiable" under the rule (so no floor applied) or not? If (b)
   says "not identifiable", the one-rule claim fails at this point — say so.
4. Novelty check against what you know of off-grid / basis-mismatch / super-resolution sparse recovery and errors-in-variables
   estimation: is an identifiability-gated covariance floor known? Mark uncertain recall as A.
5. Cheapest decisive test (design only, not run), with a decision rule; or explain why the idea reduces to a relabelling.

## Final message
English, ≤ 60 lines: verdict first (new rule / relabelling / fails), then answers 1–5, then confirmed `model:`.
