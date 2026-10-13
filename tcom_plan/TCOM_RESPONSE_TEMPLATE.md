# TCOM_RESPONSE_TEMPLATE.md — reviewer-rebuttal scaffold

Use this when TCOM reviews come back. Copy-paste the template and fill in the per-reviewer sections. Keep _all_ rebuttal drafts under `tcom_plan/rebuttals/round_<N>/` so they survive editor reroutes.

---

## How to use

1. Receive review file from editor → save raw to `tcom_plan/rebuttals/round_<N>/raw_<reviewerID>.md`
2. For each numbered comment, classify into one of:
   - **Accept** — straightforward fix, do it
   - **Partially accept** — add caveat / scope statement
   - **Push back** — defend with evidence (cite section, table, file)
   - **Defer** — out of scope for this round, list as future work
3. Track in the table below
4. Synthesize into rebuttal letter using the per-reviewer template

---

## Tracking grid (round N)

| Reviewer | Comment ID | Severity | Disposition | Status | Evidence / fix pointer |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

---

## Per-reviewer rebuttal template

```
We thank Reviewer X for the careful reading and constructive feedback.
Below we address each comment in order.

**R-X.1**: [verbatim comment, abbreviated if long]

  *Response*: [Accept / Partially accept / Push back / Defer]. [One- to
  two-sentence summary of how this is addressed.]

  *Change in revision*: [page/section/figure where the change appears,
  or "no change required because ..."].

  *Supporting evidence*: [pointer to result file / new table row /
  supplementary material section].

[repeat for each comment]
```

---

## Common patterns

- **"Need more seeds / variance"** → cite the 5-seed listwise retrain envelope (E3 in TCOM_PLAN.md).
- **"How does it compare to [SP-AFDM paper X]?"** → cite the Qing 2024 reproduction (E2). If X ≠ Qing 2024, be honest about non-coverage and either reproduce or list as future work.
- **"Complexity claim is unsupported"** → cite §IV-F wall-clock + MAC table (E5).
- **"Mechanism is causally unclear"** → cite per-candidate attribution table (E4) + §IV-E discussion.
- **"Why didn't you train end-to-end?"** → defer to future work; argue stage-wise unrolling is interpretable and matches classical SP literature.
- **"Frame counts inconsistent across tables"** → adaptive-budget early-stop wording per FYP PAPER_CLAIM_AUDIT P2 fix; reference Table caption clarification.

---

## Submission-package checklist (before each round upload)

- [ ] Rebuttal letter PDF — via `paper/rebuttal_round_<N>.tex`
- [ ] Revised manuscript PDF with track-changes — `paper/main_revised_round_<N>.pdf`
- [ ] Diff manuscript (clean) — `paper/main_clean_round_<N>.pdf`
- [ ] Updated REPRODUCTION.md if any new experiments shipped
- [ ] Updated models/MANIFEST.md if any new checkpoints
- [ ] Re-run `/citation-audit` and `/paper-claim-audit`; archive results under `tcom_plan/rebuttals/round_<N>/audit/`
- [ ] Tag commit `tcom-rebuttal-r<N>`
