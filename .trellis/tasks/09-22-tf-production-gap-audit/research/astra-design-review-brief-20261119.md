# Codex Astra brief: pre-freeze design review of two protocols (fixed questions, read-only)

Written 2026-11-19 by Claude under Eric's delegation (fully automatic; Claude freezes). This is the external design review required
by research-checkpoint §1.5 before freezing a protocol whose conclusion would be stated as a mechanism. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Read-only: write nothing to the repo. Your final message is the deliverable. Model: `gpt-6.2-astra`.

## Role and limits
- Answer only the questions below. Do not propose research directions or paper framing.
- No receiver simulation and no reading of per-unit result rows. Small in-memory numerical checks of algebra are allowed.
- Mark every claim as derived, numerically checked or assumed.

## Protocol A: SBL spectral split
`.trellis/tasks/11-19-sbl-spectral-split/research/protocol-DRAFT.md`; background `research-assets/res-20261018-01.md` (E-3c) and
`experiments/tf_e3_sbl_20261017/sbl_rx.py` (`sbl_em`: Γ enters the β update).

1. **Construction.**
   - Is `Π_lo` (eigenvalues of `D_ℓ = Γ[S_ℓ,S_ℓ]/sum(v)` below τ = .5) a sound definition of the sub-resolution (difference-mode) subspace
     for 25 atoms spanning [−3, 3] at a .25 step, and for small screened groups?
   - The ridge is built once at EM start and then restricted by pruning to principal submatrices, which are no longer projectors. Does
     that undermine the interpretation? If it does, give the minimal fix.
2. **Discrimination.**
   - Do the arms separate H1–H5 as the table claims?
   - In particular, is the trace-matched isotropic control (`u·(r_ℓ/k_ℓ)·I_ℓ`) the right control for the β/amount channel, given how
     Γ enters both the E-step precision and the β update?
   - If it is not, what is?
3. **Decision rules.**
   - Any loophole: a verdict reachable for the wrong reason, or a likely outcome with no verdict?
   - Are the fraction thresholds (.5 / .25) and the "first matching" order sensible?

## Protocol B: ratio sweep v2
`.trellis/tasks/11-18-ratio-sweep/research/protocol-v2-DRAFT.md`; the window comes from
`.trellis/tasks/11-18-admission-law-test/research/astra-prediction-rule.md` (your own rule, Eq. (13) window W).

4. **Algebra.**
   - Verify `R_A2* = (T² − z²E²)/(z²(u+λ)²)` and `R_C* = (T² − z²(E+u)²)/(z²λ²)`, T = E+u+λ, as the inverses of the two boundaries of W
     in r = 1/R, including the reduction at z = 1.
   - State any condition under which a boundary is undefined or reverses.
5. **Design.**
   - Forced miss masks the weak delay in F0 and unmasks it at the first exchange. Does that create an artefact that would make the window
     look right or wrong for reasons unrelated to the mechanism?
   - Is ξ = R/R_A2* the right normalized axis?
   - Are S1–S4 well-posed? In particular, S2's factor-2 tolerance and S3's band definition.
6. **Most likely misleading verdict.** For each protocol, name the single most likely way it produces a verdict that would mislead, and
   the cheapest design change that prevents it.

## Output format (final message, English, ≤ 120 lines)
`## A1` … `## A3`, `## B4` … `## B5`, `## 6`.

Then `## Required changes before freeze`, with at most 5 bullets. Each bullet is labelled `blocking` (the protocol would mislead without
it) or `optional`.
