# Independent assessment brief: the next ambitious step for the SP-AFDM paper (read-only)

Written 2026-11-19 by Claude for an independent model (Astra via Codex, or agy/Gemini). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: write nothing to the repo except, for
agy, the single output file named at the end. **Do not read `ambition-direction-claude-20261119.md`** or any file whose name contains
`divergence-ambition`. Your view must be independent of Claude's.

## The decision
Eric (the author) must choose the next step after a sprint that has closed. The question: **what single next step most raises the
paper's ambition (from a solid regular IEEE TCOM paper toward a landmark contribution) at a feasible cost?** Writing the paper now and
leaving ambition to follow-up papers is a legitimate answer.

## Evidence (accepted cards; read them, not summaries)
- Narrative skeleton v1.3.1: `.trellis/tasks/09-22-tf-production-gap-audit/research/tcom-narrative-skeleton-20261118.md`.
- Sprint results:
  - `research-assets/res-20261119-01.md` through `-06.md`, which cover the forced-miss sweep, the SBL spectral replay, the unified
    covariance prospective test, the doublet conflict, the SBL residual gap and the ρ sweep;
  - `research-assets/res-20261118-01.md` through `-06.md`.
- Proofs: `.trellis/tasks/09-22-tf-production-gap-audit/research/proofs-20261119/theory-astra-v2.tex` and the reviews in that folder.
- Earlier ambition discussion, including external critiques: `.trellis/tasks/09-22-tf-production-gap-audit/research/ambition-synthesis-20261118.md`
  (§1, §2, §4, §4b, §4c, §6.3).
- Open items: `.trellis/tasks/09-22-tf-production-gap-audit/research/wrapup-acceptance-20261119.md` §C.
- Constraints: one RTX 4090 shared by about 5 users, a 128-core CPU server, and Codex sessions that cost money. Eric is a student whose
  first-author paper this is, and he must be able to explain and defend every claim.

## What to deliver
1. **Candidates.** Propose your own candidates. You may also evaluate the ones that appear in the evidence (for example in the ambition
   synthesis and the open items). For each candidate give:
   - importance (would a top reviewer or reader care, and why);
   - feasibility × interest;
   - Heilmeier answers (what, how it is done today, what is new, who cares, risks, cost, the mid-term check);
   - the outside view (base rates for this kind of addition changing a paper's reception);
   - the cheapest first falsifiable check, with a decision rule.
2. **Ranking.** Rank the candidates, including "write now", and name your top recommendation.
3. **Change conditions.** State what evidence would change your recommendation, and give your confidence (H/M/L).
4. **Traps.** List the traps: directions that look ambitious but are low value or likely to fail, each with the reason.

## Rules
Mark each claim as grounded in a named file, derived, or assumed. No simulation. At most 60 lines in the final message (Astra). agy:
write the same content to `.trellis/tasks/09-22-tf-production-gap-audit/research/ambition-direction-agy-20261119.md`, and keep the chat
reply under 15 lines.
