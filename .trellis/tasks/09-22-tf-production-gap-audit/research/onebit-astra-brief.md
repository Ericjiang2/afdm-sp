# Astra brief: is the identifiability gate a one-bit information rule, and does that say anything new? (read-only)

Read-only: do not edit files or run code. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Do NOT read `.trellis/tasks/09-22-tf-production-gap-audit/research/miao-assessment-claude-20261119.md`.

## Read
- `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-gauge-derivation-20261119.md` §2 (your gate);
- `experiments/gate_screen_20261119/gate.py`; `research-assets/res-20261119-07.md` (paired test of the gate);
- `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex` Prop 2 and Corollary (fixed prior);
- `research-assets/res-20261119-02.md`, `-03.md` (SBL spectral split; the reversal).

## Conjecture to examine (Claude)
For a complex Gaussian linear functional pᴴh, the gate condition 2·pᴴV₁p > pᴴV₀p is equivalent to "the frame's mean-waveform data
carry less than 1 bit of information about pᴴh", since I = log₂(pᴴV₀p / pᴴV₁p).

## Questions
1. State the probabilistic model in which V₀ and V₁ are prior and posterior covariances of h (support exchange with λ* = σ²; SBL
   initialisation with λ* = λ + u/N), and prove or refute the one-bit equivalence. Give the exact conditions.
2. In SBL (type-II evidence), is the per-direction Occam term of the evidence the same quantity? Does the SBL reversal under the exact
   covariance follow from the exact block removing the difference-mode Occam cost? Derive or refute; say what is only analogy.
3. Does the one-bit reading yield any **new quantitative or sign prediction** not already contained in the existing results — e.g. where
   the +0.46 pp gate-vs-S-lo excess should concentrate (block size, SNR), or how a different bit threshold would change both stages? If it
   is only a relabelling, say so plainly.
4. Can the scalar phantom (split reward, Prop 2 item 4) be stated in the same information / description-length language? Give the
   statement or say no.

## Output
Final message only, English, ≤ 50 lines, numbered by question; mark each claim [derived], [conjecture] or [analogy].
