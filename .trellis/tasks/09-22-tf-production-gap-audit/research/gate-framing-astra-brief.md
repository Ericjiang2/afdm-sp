# Astra brief: how should the paper frame the identifiability gate? (read-only, short)

Read-only: do not edit files or run code. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.

## Evidence (read these; do NOT read `.trellis/tasks/09-22-tf-production-gap-audit/research/skeleton-revision-drafts-20261119.md`)
- `research-assets/res-20261119-07.md` — paired fresh-frame test of the gate (joint supported; SBL G vs S-lo +0.46 pp [0.10, 0.83];
  exchange identical to CODELAY, 0/116 doublets lost).
- `research-assets/res-20261119-03.md`, `-04.md`, `-05.md` — the spectral mirror, the doublet conflict, the SBL residual gap.
- `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md` — current skeleton: sentence 4,
  Proposition 3 (exactness scope), Q9.
- Your own derivation `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-gauge-derivation-20261119.md` §2.

## Question
The paper currently says the covariance correction is placed per stage (exact sum mode, no floor in discrete exchange; difference-mode
floor S-lo in EM-SBL). Two framings are possible for the TCOM paper:
- (a) the gate is the **principle** that derives the stage-specific placement; the implementation stays CODELAY in exchange and S-lo
  in EM-SBL;
- (b) the gate is the **implementation**, used in both stages.

1. Which framing do you recommend, with confidence (H/M/L)? Give the strongest alternative and the evidence that would change your view.
2. Does the evidence license "one identifiability rule derives the stage-specific placement" as a paper claim? State the exact wording
   you would allow and what must not be claimed.
3. Is a remark under Prop 2 giving the isolated-pair form (E − u)·x < λ* safe to add as a design-rule remark (not a theorem)? Any
   condition or error in it?

## Output
Final message only, English, ≤ 35 lines, numbered by question.
