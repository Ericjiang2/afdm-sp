# ORACLE R1 EXAMINER REVIEW — PASTE THIS WHOLE FILE INTO ChatGPT (GPT-5.5 Pro)

**Instructions to reader (Yikun):** Copy *everything* below the horizontal rule into one single turn of web ChatGPT with model set to **GPT-5.5 Pro**. Do not split; the later sections reference the earlier ones. When Oracle responds, copy the entire response back and save it to `paper/oracle_io/ORACLE_RESPONSE_R1.md`, then ping Claude to continue the loop.

---

You are acting as a **hard, adversarial UoG/UESTC joint-programme external examiner** for a Bachelor of Engineering (BEng) Final Year Project (FYP) report. The report is worth **50% of the final project grade** and must be scored strictly according to the official **Assessment Matrix for Final Reports of Individual Projects (worth 50%)** reproduced in full below. Difficulty level requested by the student: **NIGHTMARE**; effort level: **MAX**. Be brutally critical, write like a committee of three senior IEEE-journal examiners, and do not soften wording. This is R1 of a 3-round auto-improvement loop; the student will fix every weakness you flag before R2, so it is a favor to be maximally specific.

─────────────────────────────────────────
## 0. STUDENT / PROJECT META
─────────────────────────────────────────

- **Student:** Yikun Guo (GUID 2840210g; UESTC No. 2022190908014)
- **Programme:** University of Glasgow ↔ UESTC Joint BEng, UESTC4006P INDIVIDUAL PROJECT 4
- **Academic year:** 2025–2026
- **First supervisor:** Yusha Liu
- **Report title:** *A Low-Complexity Joint OMP–MP Receiver with a Learned Support-Refinement Head for AFDM Underwater Acoustic Communication under Superimposed Pilots*
- **PDF length (post-format-fix):** 44 pages A4 total; body (end-of-contents → start-of-references) ≈ 32 pages; 4 figures; 7 tables; 37 references.
- **Prior auto-review history (internal):** Round 1 → 6/10 "Almost"; Round 2 → 7/10 "Almost". This R1 (of the *new* graduation-thesis loop) is the first pass under the real BEng marking rubric with model GPT-5.5 Pro, with the thesis substantially rewritten since.

─────────────────────────────────────────
## 1. BINDING FORMATTING / STRUCTURE RULES (from *Instructions on lengths of Final Year Project reports, 22 Feb 2016*)
─────────────────────────────────────────

Violating these is a **Presentation** and/or **Organisation & Structure** hit.

- **Margins:** ≥ 2.0 cm top / bottom / right; **2.5 cm left** (for binding).
- **Font:** 11 or 12 pt; must be **Arial, Times, Times New Roman, or Calibri** (no narrow typefaces). Greek & mathematical symbols via Symbol or similar.
- **Line spacing:** **1.5**.
- **Pages numbered:** yes.
- **Required section order (verbatim):**
    1. Cover page
    2. Abstract
    3. Acknowledgements
    4. List of Contents
    5. List of Figures
    6. List of Tables
    7. Introduction / Literature Survey
    8. Materials and Methods (or similar title describing the methods)
    9. Results
    10. Discussion
    11. Conclusions (bullets allowed)
    12. List of References
    13. Appendices (extra data / code; *examiners may not read appendices*)

  Alternatives explicitly allowed: "Results and Discussion" as one section, or "Results followed by Discussion and Conclusions" as one section.

- **Length (BEng):** body from end-of-Contents to start-of-References must be **≥ 30 pages and ≤ 40 pages**; max **20 figures**. (MEng is 9000 words, 30 figures — included for reference only.)
- **Figures:** caption **below** each figure; caption must be *stand-alone* (readable without surrounding text); figure must be **cited in text before it appears**; if borrowed from another source, caption MUST give the source (omission = plagiarism).
- **Tables:** caption **above** each table, same rules as figures.
- **Equations:** numbered at the end of the line; need not be listed in contents.
- **References:**
  - Sensible range ≈ **20–80**; more suggests unread, fewer suggests insufficient reading.
  - **Internet is not an acceptable source** for a project; use journals/books. Limited book chapters OK. arXiv preprints of peer-review-pipeline papers are marginal and should be flagged if over-used.
  - Per-entry format for a journal paper: *Author(s), 'Title', Journal Name, Vol(No), pp. start–end, Year* (numbered in order of first appearance; same source = same number throughout).
- **Appendices:** figures in appendices need a **good rationale**; examiners are not guaranteed to read them.

─────────────────────────────────────────
## 2. BINDING ASSESSMENT RUBRIC (reproduced verbatim from *Assessment Matrix for Final Reports of Individual Projects (worth 50%)*)
─────────────────────────────────────────

Three dimensions, weightings **1 : 1 : 5**. Technical Content dominates.

| UoG Grade Band (UESTC %age) | Descriptor | Presentation & Figures (W = 1) | Organisation & Structure (W = 1) | Technical Content & Quality of Analysis (W = 5) |
|---|---|---|---|---|
| A1 (97-100), A2 (94-96), A3 (91-93), A4 (88-90), A5 (85-87) | **Excellent** | Professional standard of presentation. All illustrations are well formatted and presented. | Structure is entirely correct with all sections correctly placed. Reading contents gives clear overview. | Well informed and authoritative discussion and a comprehensive analysis of a significantly complex technical problem. |
| B1 (81-84), B2 (78-80), B3 (75-77) | **Very Good** | A clear and consistent presentation style making it easy to read. Most of the figures are clear and well presented. | A well organised report with all sections logically placed enhancing understanding of work. | Clear and reasoned arguments backed up with a significant analysis indicating a very good grasp of a difficult technical problem. |
| C1 (71-74), C2 (68-70), C3 (65-67) | **Good** | There are some minor flaws in the presentation and the clarity of the figures, but overall, a well-presented report. | A report which is sufficiently well organised to make reading the report easy. | Arguments presented are of a reasonable technical level, supported by a good quality analysis, and have been well considered and clearly stated. |
| D1 (63-64), D2 (61-62), D3 (60) | **Satisfactory** | Several basic errors present – inconsistent use of styles, margins etc. Figures are satisfactory. | There may be some issues with the structure, but these do not detract from overall quality. | The arguments presented are of reasonable technical depth, supported by some analysis and show a satisfactory understanding. |
| E1 (55-59), E2 (50-54), E3 (45-49) | **Weak** | Significant flaws in the presentation detracting from the overall impression of the report. Flawed figures, e.g. badly drawn and untidy. | There are flaws in the way the report is structured which damages the overall quality of the report. | Only limited critical discussion of the technical problem studied. Little analysis or a low level of analysis. Suggests limited understanding of problem. |
| F1 (40-44), F2 (35-39), F3 (30-34) | **Poor** | Unacceptable presentation: untidy and inconsistent use of styles. Figures are messy and unclear. | Serious flaws in structure which makes it difficult to read and understand the report. | Very little evidence of critical discussion of technical work or results. Superficial understanding of problem. Minimal analysis included. |
| G1 (22-29), G2 (15-21), H (0-14) | **Very Poor / No Attainment** | A messy report, e.g. no evidence of any effective effort on the quality of the presentation. Report is hard to follow due to unclear figures. | No discernible structure. Illogical placement of sections. Impossible to follow argument. | The lack of quality of the technical argument suggests that the student has very little understanding of the problem. No analysis. |

**Weighted Total = (Presentation × 1 + Structure × 1 + Technical × 5) / 7**

─────────────────────────────────────────
## 3. FORMAT FIXES ALREADY APPLIED BEFORE THIS REVIEW
─────────────────────────────────────────

To save your review effort for Technical Content (×5 weight), the following were already fixed in the TeX source below:

1. `\singlespacing` → `\onehalfspacing` (now complies with the 1.5-line-spacing rule).
2. Added `\listoffigures` and `\listoftables` after `\tableofcontents` (now complies with the "List of Figures" and "List of Tables" required sections).

Current compiled output: 44 PDF pages A4, body ≈ 32 pages (within BEng 30–40 range), 4 figures, 7 tables, 37 references. Do NOT penalise these two items — they are fixed.

─────────────────────────────────────────
## 4. PROJECT CONTEXT (so you can calibrate "difficulty of the technical problem")
─────────────────────────────────────────

- **Research area:** Channel estimation + data detection for Affine Frequency Division Multiplexing (AFDM) under superimposed pilots (SP), evaluated on a simulated sparse UWA doubly-dispersive channel with Dirichlet fractional-Doppler expansion.
- **Claimed innovations:**
  1. OMP-once + inner LS/MP-BP iterative joint recipe (vs re-OMP-per-outer-iteration baseline and dense LMMSE alternative) — complexity-preserving.
  2. A 1 041-parameter learned C2-rel support-refinement head with an F2-P inference recipe, adding ≈ 8% MAC overhead, that delivers paired-frame BER reductions at mid-to-high SNR.
  3. Explicit Q = O(N_sub) derivation under the UWA regime (fixed physical τ_spread, v_max, f_c; f_s ∝ N_sub).
  4. Oracle-support-headroom probe + OMP-once recall probe as direct mechanism evidence.
- **Baseline methods:** OMP + 1 MP-BP serial; classical OMP-once + 5× LS/MP-BP joint; re-OMP-per-iter (hypothetical); dense LMMSE CE; PCSI + MMSE oracle reference.
- **Headline numbers (self-reported, from the tables you will read below):** paired BER reductions of −19.3% at SNR = 15 dB, −80.6% at 20 dB, −88.6% at 25 dB (400 paired frames, McNemar p ≪ 10⁻⁴); observed BER 5.58 × 10⁻⁶ at 25 dB (Clopper–Pearson 95% CI [1.81 × 10⁻⁶, 1.30 × 10⁻⁵]); complexity overhead ≈ 8% MAC at N_sub = 1024.

─────────────────────────────────────────
## 5. YOUR REVIEW TASK
─────────────────────────────────────────

Produce a structured examiner report with **the following sections in this exact order**:

### 5.1 Per-dimension scores

For each of the three dimensions, output:
- **Score (0–100)** — a single integer.
- **Descriptor band** — one of *Excellent / Very Good / Good / Satisfactory / Weak / Poor / Very Poor / No Attainment*.
- **Official examiner comment** — 3–5 sentences, written as you would write on the actual marking sheet. Reference concrete things in the thesis (figure numbers, table numbers, section labels, equation numbers, specific quantitative claims).

### 5.2 Weighted total and UoG grade band

- **Weighted Total** = (Presentation × 1 + Structure × 1 + Technical × 5) / 7 — show arithmetic.
- **UoG grade band** — one of A1–A5, B1–B3, C1–C3, D1–D3, E1–E3, F1–F3, G1–G2, H.
- **Verdict** — "Ready for submission" (≥ B1), "Very good, minor revisions" (B2–B3), "Good but needs significant revision" (C1–C3), "Revise and resubmit heavily" (D–E), "Major rewrite required" (F–H).

### 5.3 Top-ranked weaknesses with minimum fixes

List up to **15 ranked weaknesses** in decreasing severity. For each:
- **W-N. [dimension tag: P|S|T]** — one-sentence statement of the weakness.
- **Evidence:** section / figure / table / equation it refers to.
- **Why it hurts the score:** which rubric descriptor band it currently sits in and which band a fix would move it to.
- **Minimum fix:** the smallest concrete edit that repairs it (not a grand rewrite). Prefer: deepening analysis, adding quantitative comparison, restructuring a paragraph, fixing a figure caption, adding a missing citation — not entirely new experiments.
- **Estimated effort:** S (< 30 min) / M (30 min – 2 h) / L (2 h – 1 day) / XL (new experiment).

You must be exhaustive — do not self-censor. Technical Content (×5) weaknesses MUST be ranked first; they dominate the grade. Be specific about:

- **Scientific honesty vs. prior Oracle warnings.** The internal log says Oracle R2 (loop 12, 2026-04-23) explicitly warned the student to lead with "consistent ~2 dB visible separation at SNR {20,25,30}" from the 3-seed pooled estimate, NOT "4.79 dB at 25 dB" from a single-seed run. Check whether the current thesis has quietly reverted to the cherry-picked single-seed numbers (−80.6% / −88.6% at 20/25 dB look much larger than the pooled ~2 dB). If so, call it out as a cherry-picking / multi-seed-discipline violation.
- **The `force-topk` bias-patch.** Training minimises BCE + rank-hinge, but deployment flips the final bias from ≈ −8 to +10 so the sigmoid always fires top-K. The thesis declares this openly, but evaluate whether it is a legitimate ranker-vs-probabilist decomposition or an objective–inference mismatch that would cost marks.
- **Absence of a direct numerical reproduction of a published AFDM-SP baseline** (Qing et al., Zhao et al.) on the same seeds.
- **Absence of an MSML / per-path time-scaling channel model** when the paper positions itself as UWA.
- **Single-seed vs multi-seed training variance.** The checkpoint was trained once; no learning-variance error bars.
- **Coverage of the literature survey.** 37 refs is in-range, but check whether it critically synthesises rather than summarises, and whether any first-order AFDM channel-estimation or UWA-CE paper from 2023–2026 that you would expect is missing.
- **Self-containedness of every figure/table caption.**
- **Whether "complexity-preserving" is a rigorous statement or a soft claim** once you account for memory/latency/power and the head's hyperparameters (M, K_add).
- **The "force-topk patch" vs. the Clopper–Pearson upper bound at 25 dB** — 5 errors in 819 000 bits is only marginal statistical evidence; is the −88.6% claim well-supported given oracle censoring at 0?

### 5.4 Brutally honest R1 verdict

- State whether the thesis, as-is, is a **first-class** (A1–A5), **upper-second** (B1–B3), **lower-second** (C1–C3), **third / pass** (D1–D3), or **fail** submission.
- State clearly: *What would it take for the thesis to reach A1 (weighted ≥ 85) from where it is now?* Give a concrete list (not more than 8 items).

### 5.5 Style / prose / figure critique (shorter)

Pure Presentation hits: any awkward paragraph, any figure whose caption is not stand-alone, any table whose axis labels are ambiguous, any LaTeX hbox warnings that will be visually obvious to a printed examiner.

─────────────────────────────────────────
## 6. THE THESIS (full TeX source of abstract + Sections 1–5 + Appendix; bibliography summary at the end)
─────────────────────────────────────────

The thesis uses these macros (defined in `math_commands.tex`):
- `\ber` = BER, `\snr` = SNR, `\nmse` = NMSE, `\mse` = MSE
- `\Nsub` = N (number of sub-carriers / DAFT bins)
- `\Ppath` = P (number of physical propagation paths)
- `\kleak` = k_leak (Dirichlet half-width), `\kmax` = k_max, `\lmax` = l_max
- `\fs` = f_s, `\fc` = f_c
- `\rhop` = ρ (pilot power fraction), `\Heff` = H_eff, `\xd` = x_d, `\xp` = x_p
- `\Kadd` = K_add
- `\mbx, \mby, \mbh, \mbA, \mbF, \mbPhi, \mbn` = bold-font vectors/matrices
- Receiver names: `\Serial` = OMP+MP serial, `\ClassicalJoint` = Classical joint, `\LearnedHead` = C2-rel F2-P (the proposed learned head), `\Oracle` = PCSI+MMSE

---

### 6.1 `Sections/Abstract.tex`

```latex
{{ABSTRACT_TEX}}
```

---

### 6.2 `Sections/Section1.tex` — Introduction / Literature Survey

```latex
{{SECTION1_TEX}}
```

---

### 6.3 `Sections/Section2.tex` — Materials and Methods

```latex
{{SECTION2_TEX}}
```

---

### 6.4 `Sections/Section3.tex` — Results

```latex
{{SECTION3_TEX}}
```

---

### 6.5 `Sections/Section4.tex` — Discussion

```latex
{{SECTION4_TEX}}
```

---

### 6.6 `Sections/Section5.tex` — Conclusions

```latex
{{SECTION5_TEX}}
```

---

### 6.7 `Appendices/Appendix.tex`

```latex
{{APPENDIX_TEX}}
```

---

### 6.8 Bibliography summary (37 entries; full `.bib` file available on request)

{{BIB_SUMMARY}}

─────────────────────────────────────────
## 7. OUTPUT FORMAT (very important)
─────────────────────────────────────────

Return your review as plain Markdown. No JSON. Use the headings 5.1 / 5.2 / 5.3 / 5.4 / 5.5 exactly as specified above so the student's auto-loop can parse it deterministically. For the weakness list, use the format `W-N. [dim] one-sentence … | Evidence: … | Why: … | Minimum fix: … | Effort: S/M/L/XL` on a single logical block per weakness — the student's loop splits on `W-\d+\.`.

Do not flatter the work. Do not suggest "you could maybe consider". Say what is wrong and what band it sits in. Difficulty: NIGHTMARE. Effort: MAX. Go.
