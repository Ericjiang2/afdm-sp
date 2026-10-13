# _archive/fyp/ — Final Year Project archive (read-only)

Snapshot of FYP-specific artifacts that are no longer part of the active TCOM-submission workflow but are preserved for academic record / future reference. Do not modify; do not delete.

## Tracked (in git)

- `Logbook Cover Sheet2.docx` — final FYP logbook cover sheet
- `NARRATIVE_REPORT_FYP.md` — FYP-versioned narrative report (TCOM-version lives at project root)
- `PAPER_PLAN_FYP.md` — FYP-versioned paper plan (TCOM-version lives at project root)
- `midterm-results/2840210g_Guo_UESTC4006P_Interim_2026.pdf` — interim report PDF

## Untracked (on disk, not in git history)

These files are large and not regenerable from code, so they live here on disk but are not pushed to remote to keep repo size manageable. Use `git add -f <path>` to promote any item if needed for academic record.

- `2840210g_Guo_UESTC4006P_Log Book 3.pdf` — final logbook PDF (~4.5 MB)
- `AFDM_Defense_Speech.md` — defense talk script
- `AFDM_Defense_Yikun_Guo.pptx` — defense slides (~8.7 MB)
- `_logbook_archive/*.docx` — pre-merge logbook drafts (3 files)
- `midterm-results/*.png` — interim BER/MSE/IterConv plots (5 files)

## Why these are archived rather than deleted

The FYP closed at A5 / 86.7 (REVIEW_STATE.json). Reviewers, examiners, or follow-up academic processes (departmental audit, awards, future grad-school applications) may need to refer back to the submission package. Keeping a single "_archive/fyp/" directory makes that lookup trivial without polluting the TCOM-submission working tree.

## Reproducing the FYP final PDF

The FYP report itself is still at `paper/main.pdf` (last built 2026-04-25 10:42, 54 pages, 8.14 MB). To reproduce the bit-exact submission state, check out the `fyp-final` tag:

```
git checkout fyp-final
cd 00_Inbox/AFDM-channel-estimation/paper && latexmk -pdf main.tex
```
