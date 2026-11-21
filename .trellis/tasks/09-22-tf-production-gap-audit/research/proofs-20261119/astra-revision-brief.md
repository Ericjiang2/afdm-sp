# Codex Astra brief: revise the proofs to v2 from two independent reviews (read-only)

Written 2026-11-19 by Claude. Working directory: `/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Read-only: write nothing to the repo. Your **final message is the deliverable**: the full revised LaTeX section (no line limit),
followed by a change log. Model: `gpt-6.2-astra`.

## Inputs
- Your v1: `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v1.tex`
- Reviews: `claude-proof-check-20261119.md`, `agy-proof-check-20261119.md` (same folder)
- Rulings on every issue, which you must follow: `review-divergence-20261119.md` (same folder)

## What to change (all items in the divergence table; the main ones)
1. **Prop 3.** Restate the general class. On every labelled augmented support S ∪ {a}, the uncertainty matrix must be Hermitian PSD,
   coordinate-indexed, and have Γ_aa = u (or use Γ_aa in d_a). Each trial uses its principal submatrix. Note that Γ_F, Γ_C and Γ_D
   satisfy this, and that per-trial spectral projectors do not.
2. **Prop 2(d).**
   - Retitle it as an exact characterisation of the idealised pairwise comparison, under ideal projection: zero remaining
     projections, or zero conditional-mean projections given the frozen design, plus κ = D.
   - State that the Berkson model only motivates these premises. It does not imply them, because x̄ is computed from the same Y.
   - Remove "sufficient inner region". State plainly that without residual control the window is neither sufficient nor necessary on
     real frames.
   - Define Y_sig and η, fix the h_R handling, and replace the undefined isolation phrase with the Schur-complemented 2×2 premise.
   - Add κ ≠ D to the Gap paragraph, with the innovation λκ + u(κ − D).
3. **Prop 2(c).**
   - Add Q₀ ≻ 0 as a premise; it holds automatically for g₊ ≤ 2u + λ.
   - Recast the m > 2 construction as a design prescription, or prove it. The preserved subspace must contain the range of the exact
     block at the targeted coincidence.
4. **Prop 1.** State the delay domain ℓ ∈ {0..L}, L < N. Relax the premises where your proof allows: the closed form holds for any c₁
   and N when the chirp-periodic prefix multiplier is kept. Say exactly which conclusions need N even and 2Nc₁ ∈ ℤ.
5. **Corollary.** State when Γ agrees with the exact co-delay block, and the coordinate frame for a non-diagonal 𝒫.
6. **Presentation.**
   - Put parts (a)–(d) inside theorem environments.
   - Unify the notation so that each object has one symbol; add κ, T, θ_g, 𝒦, Σ, β and α to the table.
   - Define 𝒢_g.
   - Report the numerical errors exactly as computed.

## Rules
Keep every correct proof; change only what the rulings require. Mark any step you still cannot complete as `\textbf{Gap.}`. Do not
add claims.

## Final message
- The full v2 LaTeX section.
- **Change log**: for each numbered issue (C#n = Claude, A#n = agy), what changed and where.
- **Remaining gaps.**
- The confirmed `model:`.
