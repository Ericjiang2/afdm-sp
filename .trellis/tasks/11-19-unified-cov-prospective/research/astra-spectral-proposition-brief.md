# Codex Astra brief: formalise the spectral principle behind the unified covariance (read-only derivation)

Written 2026-11-19 by Claude after Eric approved it ("Run both"). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: write nothing to the repo. Your
final message is the deliverable. Model: `gpt-6.2-astra`.

## Role and limits
- Derive and state; do not propose research directions or paper framing.
- No receiver simulation. Small in-memory numerical checks of your algebra are allowed.
- Mark every claim as derived, numerically checked or assumed. Separate what is a theorem from what is a heuristic link to receiver
  behaviour.

## Background (all prospective or verified; read the cards)
- **The setting.** The exact co-delay uncertainty block is u·D with D_ij = D_N(ν_j − ν_i). The scalar arm uses u·I. Prop 1 is in the
  skeleton `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md` §3; Prop 2 (split theorem) is
  there too, along with your admission-law formulas.
- **CSTATE (discrete support exchange).**
  - The scalar fails by admitting phantoms.
  - Restoring the exact penalty only on the resolvable half, C-hi = Π_hi(uD)Π_hi + uΠ_lo, matches `CODELAY` on every one of 6,800 fresh
    keys.
  - Restoring only the sub-resolution half, C-lo, behaves like the scalar (res-20261119-03).
- **Overcomplete EM-SBL (E-3c).**
  - The exact Γ fails relative to the scalar.
  - Adding u·Π_lo inside EM recovers 76% of the gap; u·Π_hi recovers 4%.
  - The projector shape beats a same-trace isotropic ridge (res-20261119-02 replay, res-20261119-03 prospective).
- **The unified covariance.** Γ_U = uD + u·Π_lo avoids both failures. In SBL the scalar is still better by 2.6 pp. Π_lo is the
  eigenspace of D below τ = .5, and projectors are built per stage as in the frozen protocol
  `experiments/unified_cov_prospective_20261119/PROTOCOL.md` §1, §10.

## Questions
1. **Part A (support acquisition).**
   - State and prove a proposition: for a co-delay pair (or a block) with penalty matrix G replacing Γ in the profile objective, the
     split reward of a near-duplicate candidate is controlled by the sum-mode eigenvalue of G relative to the exact u(1 + |D|).
   - Show that any G with the exact sum-mode eigenvalue leaves only an O(λ) reward, and that the scalar leaves the Prop 2 reward
     ½u|h_sum|².
   - Say what happens when G changes the difference-mode eigenvalue with the sum-mode eigenvalue fixed, which is why C-hi = CD.
2. **Part B (overcomplete estimation).**
   - State the precise sense in which the exact block's difference-mode eigenvalue u(1 − |D_N(δ)|) → 0 leaves EM-SBL or ridge estimation
     unregularised along difference directions: conditioning, posterior variance, or the β update in which Γ enters.
   - State what lower bound on the difference-mode penalty restores it. Be explicit about which parts are theorems for a fixed-prior
     ridge or MAP problem and which are heuristics for iterative ARD.
   - Your 11-18 toy was a one-step fixed-prior fit and gave the opposite sign, so explain what the iteration adds.
3. **Admissible class.**
   - Characterise the covariances that satisfy both requirements: an exact sum-mode penalty, and a difference-mode floor of order u.
   - Show that the scalar violates the first, the exact block violates the second, and Γ_U and C-hi satisfy both.
   - Is the hard τ = .5 cut necessary, or is a smooth spectral map such as u·max(D, I) in the same class?
4. **Falsifiable corollary.** Give one prediction of the proposition that the existing experiments have not tested. Examples are a
   floor-level dose response, or the effect of capping the resolvable-mode penalty at u on the remaining 2.6 pp SBL gap. State it with
   a decision rule.
5. **Placement.** Should this extend Prop 2 or stand as a new Prop 4? Write it in paper-ready form: statement, assumptions, proof or
   proof sketch.

## Final message
English, at most 70 lines, using LaTeX notation where needed:
- Part A, Part B, the admissible class, the corollary and the placement recommendation;
- every claim labelled D/N/A;
- the confirmed `model:`.
