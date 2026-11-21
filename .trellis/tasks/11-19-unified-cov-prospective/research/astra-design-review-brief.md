# Codex Astra brief: pre-freeze design review of the unified-covariance prospective protocol (fixed questions, read-only)

Written 2026-11-19 by Claude under Eric's delegation (Claude freezes). This is the external design review required by
research-checkpoint §1.5, because the conclusion would be stated as a mechanism ("one spectral fact explains two failures"). Working
directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: write nothing to the
repo. Your final message is the deliverable. Model: `gpt-6.2-astra`.

## Role and limits
- Answer only the questions below. Do not propose research directions or paper framing.
- No receiver simulation and no reading of per-unit result rows. Small in-memory numerical checks of algebra are allowed.
- Mark every claim as derived, numerically checked or assumed. Label each issue **blocking** or **non-blocking**.

## Material
- Protocol: `.trellis/tasks/11-19-unified-cov-prospective/research/protocol-DRAFT.md` and `design.md`.
- Evidence: `research-assets/res-20261119-02.md` (SBL spectral split, replay), `research-assets/res-20261118-06.md` (CSTATE admission
  law) and `research-assets/res-20261119-01.md` (forced-miss sweep, detector absorption).
- Your earlier review of the spectral split: `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-design-review-20261119.md`.

## Questions
1. **Construction.**
   - Is Γ_U = Γ + u·Π_lo, with the per-step projector rule of DRAFT §1, one coherent object across the two pipelines?
   - Does the different rule per step (EM: built on the initial grid, then pruned; continuous passes: frozen per pass; discrete
     trials: built per trial) create an artefact or a confound between the legs?
   - Derive the admission-law phantom reward under Γ_U for a co-delay candidate at δ = .25 and .5 bin. Does Γ_U keep CODELAY's phantom
     suppression? Is the card's claim correct that the equal split of an exact duplicate is untouched?
2. **Is the CSTATE leg informative?**
   - Π_lo is nonempty only for co-delay trial pairs within about .6 bin. Is "U equivalent to CD" then close to guaranteed by
     construction?
   - If it is, say what CSTATE readout would make the unification test non-trivial, or whether it should be stated as a compatibility
     check only.
3. **Discrimination and competing models.**
   - Do the arms and verdicts separate H-U from H-replay, H-amount, H-conflict-C and H-conflict-R?
   - Is there a competing "unified" covariance that a reviewer would demand as a control, and that this design cannot exclude? An
     example is a spectral floor u·max(D, I).
4. **Decision rules.**
   - Look for loopholes: a verdict reachable for the wrong reason, or a likely outcome with no verdict.
   - Check the V3 margin m = .5 pp, the φ thresholds, the crossover premise, and the conjunction of four verdicts (multiplicity).
5. **Leverage.** From the replay numbers in res-20261119-02, is 2,400 SBL keys enough for the V1 shape test (Δ_lo)? If not, give the
   cheapest fix.

## Final message
English, at most 40 lines:
- the blocking items first, each with a minimal fix;
- then the non-blocking items;
- the confirmed `model:`.
