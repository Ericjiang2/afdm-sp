# Astra brief: check agy's interface-rank corollary for Prop 1 (read-only)

Read-only: do not edit files or run code. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.

## Read
- `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex` — Prop 1 and its remarks, especially
  "Which part is modulation independent" (around line 247).
- `.trellis/tasks/09-22-tf-production-gap-audit/research/ambition-direction-agy-20261119.md` §C1 (the claim, as agy stated it).
- `.trellis/tasks/09-22-tf-production-gap-audit/research/ambition-direction-astra-20261119.md` (your earlier note that for QPSK
  v_n = E_s − |μ_n|², so "how many linear summaries reconstruct the matrix" differs from "how many numbers the decoder must pass").

## Claim to check (agy)
For a unitary modulation matrix W (rows = time samples n, columns = transmit coordinates t), let (S_W)_{tn} = |W_{tn}|². The minimal
number of linear summaries of the variance vector v needed to reproduce the co-delay uncertainty block exactly, for all v, equals
rank(S_W). It is 1 for AFDM and OFDM, m₀ for OTFS, N for single-carrier.

## Questions
1. State the corollary precisely (what object is reproduced: the co-delay block only, or the whole Γ; over which v; which W), and
   prove it or give a counterexample. Check each waveform value (AFDM, OFDM, OTFS m₀, single carrier) against the definitions used
   in Prop 1.
2. Is it a correct generalisation of the existing remark, or does it change Prop 1's scope (e.g. cross-delay terms, fractional delay)?
3. Give the exact remark text (LaTeX-ready, ≤ 12 lines) you would add under Prop 1, worded so it claims only the number of linear
   summaries needed to reconstruct the block, not the number of numbers a decoder must pass. Say whether it should be a remark or a
   corollary.
4. Any reason not to include it in this paper (triviality, OTFS claims we did not simulate)?

## Output
Final message only, English, ≤ 45 lines, numbered by question.
