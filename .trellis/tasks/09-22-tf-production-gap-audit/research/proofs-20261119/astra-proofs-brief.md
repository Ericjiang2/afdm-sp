# Codex Astra brief: write the formal proofs of Props 1–3 (with the spectral extension of Prop 2) as one LaTeX section

Written 2026-11-19 by Claude after Eric approved it ("Start proofs"). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: write nothing to the repo. Your
**final message is the deliverable**: a complete, self-contained LaTeX section, followed by a short gap list. It has no line limit.
Model: `gpt-6.2-astra`.

## Rules
- Prove; do not propose research directions or framing.
- Every step must be justified: by derivation, by a cited standard result (name it), or by a definition traceable to the code or
  protocol. A step you cannot complete is written in place as `\textbf{Gap.}` with what is missing. Never smooth over a gap.
- Use small in-memory numerical checks only to confirm algebra, and report them in a remark. They do not replace a proof.
- Keep the premises explicit in each statement. Do not claim more than you prove. In particular, there is no FER or ARD ordering
  theorem (your own conclusion in the spectral proposition).
- One notation table at the start. Each object has one symbol throughout.

## Sources
- Statements: skeleton §3, `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md` (Props 1–3).
- Prop 1: `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-producer-consumer-20261118.md`, `astra-generality-20261118.md`,
  and the frozen `physical.py` (DAFT, `dkernel`) found from `experiments/cstate_codelay_sbl_stage3_20261118/codelay.py` imports.
- Prop 2: `experiments/cstate_first_step_attribution/PROTOCOL.md` (score-difference identity). Your admission-law and finite-spacing
  window formulas: `research-assets/res-20261118-06.md`, `.trellis/tasks/11-18-ratio-sweep/research/protocol-v2-DRAFT.md` §6.
- Prop 2 spectral extension:
  `.trellis/tasks/11-19-unified-cov-prospective/research/astra-spectral-proposition-20261119.md` (split reward governed by the
  sum-mode penalty; fixed-prior contrast corollary; admissible class).
- Prop 2 window caveat: `research-assets/res-20261119-01.md`. The window rests on the Berkson premise (soft-symbol error independent of
  the residual); detector absorption violates it. State the window corollary under that premise and call it a sufficient (inner)
  failure region, not an exact boundary.
- Prop 3: the compact Schur exchange, `compact_state.py`, and the E-1 geometry
  `experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py`, against the direct Cholesky profile objective. Prove the algebraic
  identity, and state the complexity orders with their assumptions.

## Required structure
1. Notation and standing assumptions (AFDM model, DAFT, CPP, N even, 2Nc₁ ∈ ℤ, APP second-order closure, λ = σ² > 0).
2. **Prop 1**, the co-delay Dirichlet structure and cross-delay perturbation bound, with proof; the fractional-delay remark; the
   cross-modulation remark (constant-variance universality; heteroscedastic exactness iff time-flat basis; chirp shift unique to AFDM).
3. **Prop 2**:
   - (a) the score-difference identity (A, K, m_D);
   - (b) the coincidence split theorem;
   - (c) the spectral extension: the profiled split reward depends only on the sum-mode penalty (Sherman–Morrison form), and the
     finite-spacing contrast-penalty identity L(r);
   - (d) the window corollary under the Berkson premise, as a sufficient region.

   Each part comes with its proof.
4. **Corollary**, the fixed-prior contrast curvature, with its proof, and an explicit statement that it implies no FER ordering.
5. **Prop 3**, compact exchange exactness and complexity, with proof.
6. A remark listing which empirical results each statement explains and which it does not. Cite the result cards by id only.

## Final message
- The LaTeX section (`\section{...}` downwards; amsthm environments; no preamble needed).
- Then a plain-text list: **Gaps** (each with location and what is missing) and **Numerical checks** (what was checked, max error).
- The confirmed `model:`.
