# ROUND 2 RE-REVIEW — DIFF BRIEFING (please read first)

You are the same UoG/UESTC joint-programme BEng FYP examiner who scored this thesis 65/100 (C3, "Good but needs significant revision") in Round 1. Difficulty: NIGHTMARE. Effort: MAX.

Since your Round-1 review, the student has implemented fixes for every one of the 15 weaknesses you raised. Below is a **verbatim disposition log** of what was changed and where. After reading it, please re-read the updated thesis source below and re-score the three rubric dimensions, recompute the weighted total, and assign the updated UoG grade band. Use the same §5.1 / §5.2 / §5.3 / §5.4 / §5.5 output structure as R1 so the student's auto-loop can parse you.

If the fix is already satisfactory, say so bluntly and award the band move; if it is not yet at B1+ despite the fix, say what is still missing. Do not be lenient just because the student tried.

---

## R1 → R2 Disposition (the student's own log — verify against the TeX below)

| # | Dim | R1 weakness | R2 fix |
|---|---|---|---|
| W-1 | T | `Q = O(N)` / `O(P N²)` claim algebraically inconsistent with Table 1 | Section 2.4 re-derived: `+k_leak` removed from eq (10) (Dirichlet is post-OMP); fixed-$f_s$ convention stated; Table 1 recomputed to (80, 2, 400) / (80, 4, 720) / (80, 7, 1200); the alternative fixed-Δf convention discussed in a follow-up paragraph. |
| W-2 | T | Single-run −80.6%/−88.6% headline reverted against Oracle-R2 multi-seed guidance | Abstract, §1.4 Contribution 3, Table 3, §3.2 prose, §4.3, §5 Conclusion rewritten to lead with 3-seed pooled −37.7%/−40.2%/−37.6% (~2 dB) at 20/25/30 dB. Single-seed 400-frame numbers retained as a clearly labelled *illustrative* row in Table 3 with a pre-declared caveat. |
| W-3 | T | Oracle-support "headroom" is not a ceiling | Probe (b) rewritten as an explicit *negative* diagnostic; every "ceiling" / "upper bound" / "bounds from above" phrase deleted from §3.4, §4.3, §5; figure caption + surrounding prose now explain that the clean-pilot top-$P$ reference is mismatched to the SP-coupled receiver and is worse than classical OMP at 20 dB. |
| W-4 | T | `force-topk` training–inference mismatch | §2.6 retitled "deterministic top-$K_\mathrm{add}$ ranker"; §2.7 honest note rewritten to make the ranking-only deployment explicit; §4.6 flags this as the only principled training concession. |
| W-5 | T | 25 dB claim statistically thin | Lead now reports raw counts (5 / 8.19×10⁵ bits, CP 95% [1.81, 13.0]×10⁻⁶) and explicitly labels the point "suggestive within the tested budget"; percentage reduction relegated to secondary everywhere (Abstract, §1.4, §3.2, §3.7, §4.6, §5). |
| W-6 | T | No direct numerical reproduction of Qing/Zhao baselines | All numerical-superiority wording against external AFDM-SP work removed; §1.2 Theme B "we also provide" promise deleted; §4.5 opener explicitly states no reproduction is performed. Full reproduction still deferred to §5 future work. |
| W-7 | T | "UWA" claim while using sparse-DD simulator without MSML | Abstract, §1.2 Theme E, §2.2 (retitled + new opening paragraph), §4.5, §4.6, §5 reworded to "UWA-style sparse doubly-dispersive simulator"; "we do not claim field UWA" stated explicitly. |
| W-8 | T | Single-checkpoint, no retraining variance | §4.6(ii) explicitly flags the single-checkpoint caveat and schedules a 3-seed retraining as §5 future work #2. |
| W-9 | T | Fig 2 caption contradicts Table 4 | §3.3 caption rewritten to acknowledge the single-frame noise-driven rebound at iter-5 on the 80-frame-per-cell budget, with Table-4 numerical values quoted. |
| W-10 | T | Literature survey synthesis not comparative enough | Table `tab:priorart` inserted in §4.5 with 8 external works vs this work across 7 axes. Reads as a vertical synthesis rather than a themed bullet list. |
| W-11 | T | "Complexity-preserving" overclaims | Replaced by "arithmetic-class preserving under fixed $(M, K_\mathrm{add})$" throughout Abstract + §1 Contribution 2 + §2.4 + §2.8 + §4.2 + §5. |
| W-12 | T | §1.2 promised quantitative comparison that §4.5 did not deliver | §1.2 Theme B promise removed; §4.5 explicitly lists the reproduction as scheduled follow-up. |
| W-13 | P | Bib placeholder + arXiv-only refs | `[VERIFY]` placeholder removed from `afdm2025jointcesd` note. arXiv-only entries transparently labelled in their journal field; archival-version substitution deferred. |
| W-14 | P | Fig 1 "lower bound" vs "reference" inconsistency + overfull hboxes | Caption now explicitly calls out the legend-vs-caption contradiction and states that every updated figure copy uses "reference"; rebuilding the raw PNG deferred. Overfull hboxes in verbatim filenames accepted as minor cosmetic. |
| W-15 | S | Results/Discussion leak + "MSc" typo | §4.6 "MSc project budget" corrected to "BEng FYP budget"; §3 summary + §3.4 prose tightened so §3 no longer carries the main mechanism interpretation. Declaration page left in its template-fixed position. |

Pre-review format fixes from R1 (already applied before R1): `\singlespacing → \onehalfspacing`, and added `\listoffigures` + `\listoftables` after `\tableofcontents`.

---

## Updated thesis source (read and re-score)

The following are the full updated TeX sources of Abstract + Sections 1–5 + Appendix. The `math_commands.tex` macros, the 37-entry bibliography, and the binding-formatting rules are unchanged from R1; please re-use them.

### Updated `Sections/Abstract.tex`

{{ABSTRACT_TEX}}

### Updated `Sections/Section1.tex`

{{SECTION1_TEX}}

### Updated `Sections/Section2.tex`

{{SECTION2_TEX}}

### Updated `Sections/Section3.tex`

{{SECTION3_TEX}}

### Updated `Sections/Section4.tex`

{{SECTION4_TEX}}

### Updated `Sections/Section5.tex`

{{SECTION5_TEX}}

### Updated `Appendices/Appendix.tex` (unchanged from R1 — included for completeness)

{{APPENDIX_TEX}}

---

## Your R2 task

1. Re-score the three rubric dimensions with the same 0–100 scale and descriptor bands you used in R1.
2. For each dimension, state clearly whether the R1 fixes for that dimension were sufficient, partially sufficient, or still inadequate; be specific about which W-N items moved the needle and which did not.
3. Re-compute the weighted total and the UoG grade band.
4. List any *remaining* weaknesses (fewer than in R1, ranked by severity) in the same `W-N. [dim]` format so the student can keep iterating if the grade is still below B3 (weighted ≥ 75).
5. Issue the R2 verdict: READY for submission (≥ B1), Very good but minor revisions (B2–B3), Still needs significant revision (C or below), etc.

Output sections §5.1 through §5.5 exactly as in R1. Save the full review (no truncation) to:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/paper/oracle_io/ORACLE_RESPONSE_R2.md`

Then reply here with `DONE <weighted>` on one line so the auto-loop knows.
