# BEng Final Year Project — Round 1/3 Review Request (GPT-5.5 Pro / Oracle)

You are asked to act as a strict examiner for a **UoG/UESTC joint BEng individual project final report**. This report is worth **50% of the final project grade**. I am running an autonomous review loop (`/auto-paper-improvement-loop`) that will iterate up to **3 rounds** to incorporate your feedback. Target: **weighted total ≥ 75 (Grade B3 or above)**, with a credible push toward **B2/B1**.

**Important context for this round (Round 1).** The thesis has already been through 3 prior revision rounds under a previous examiner model (`codex gpt-5.4 xhigh`). Those 3 rounds took it from **C3 (65)** → **C1 (72)** → **B3 (75)**. You should review the **current (post-R3) state** from scratch and be honest — do not give credit for the prior improvement history, just score what you see in the attached files. Your review is what determines whether we push beyond B3 into B2/B1 territory.

---

## Thesis Package (attached)

- `main.tex` — master LaTeX file
- `sections/Abstract.tex`
- `sections/Section1.tex` — Introduction
- `sections/Section2.tex` — System model + method (architecture, training objective, complexity)
- `sections/Section3.tex` — Experimental protocol + analysis (includes Probe (a) / (b) / (c))
- `sections/Section4.tex` — Results + discussion
- `sections/Section5.tex` — Conclusions + future work
- `Appendices/Appendix.tex` — Appendix A (simulator correspondence), B (CI procedures), C (Probe (a) support-recall bookkeeping), D (McNemar test)
- `references.bib` — bibliography

The project is: **learned support-refinement head on top of a classical OMP + MP-BP joint receiver for AFDM (Affine Frequency Division Multiplexing) channel estimation + data detection under UWA-style sparse doubly-dispersive simulation.** 1,041-parameter PyTorch head; 3-seed pooled evaluation; paired McNemar tests; Clopper-Pearson exact CIs at high SNR; superimposed ZC pilots.

---

## UoG/UESTC Marking Schema (strict)

Score each of THREE dimensions from **0-100**. The weighted total is:

> **Weighted Total = (Presentation × 1 + Structure × 1 + Technical × 5) / 7**

Grade bands (UESTC %):
| Grade | Range | Descriptor |
|---|---|---|
| A1-A5 | 85-100 | Excellent |
| B1-B3 | 75-84 | Very Good |
| C1-C3 | 65-74 | Good |
| D1-D3 | 60-64 | Satisfactory |
| E1-E3 | 45-59 | Weak |
| F1-F3 | 30-44 | Poor |
| G1-G2/H | 0-29 | Very Poor / No Attainment |

### Dimension 1: Presentation & Figures (weight ×1)

| Score | Band | Criteria |
|---|---|---|
| 85-100 | Excellent | Professional standard; all illustrations well formatted. |
| 75-84 | Very Good | Clear consistent style; most figures clear and well presented. |
| 65-74 | Good | Some minor flaws in presentation / figure clarity, overall well-presented. |
| 60-64 | Satisfactory | Several basic errors (style, margins); figures adequate. |
| 45-59 | Weak | Significant presentation flaws; figures badly drawn. |
| 30-44 | Poor | Unacceptable presentation; messy figures. |
| 0-29 | Very Poor | No effective effort; unclear figures. |

### Dimension 2: Organisation & Structure (weight ×1)

| Score | Band | Criteria |
|---|---|---|
| 85-100 | Excellent | Entirely correct structure; reading gives clear overview. |
| 75-84 | Very Good | Well organised; logical placement enhances understanding. |
| 65-74 | Good | Sufficiently organised for easy reading. |
| 60-64 | Satisfactory | Some structural issues, not detracting from overall. |
| 45-59 | Weak | Structural flaws damage quality. |
| 30-44 | Poor | Serious flaws; hard to read. |
| 0-29 | Very Poor | No discernible structure. |

### Dimension 3: Technical Content & Quality of Analysis (weight ×5)

| Score | Band | Criteria |
|---|---|---|
| 85-100 | Excellent | Authoritative discussion; comprehensive analysis of a significantly complex problem. |
| 75-84 | Very Good | Clear, reasoned arguments backed by significant analysis; very good grasp of a difficult problem. |
| 65-74 | Good | Reasonable technical level; good-quality analysis; well considered. |
| 60-64 | Satisfactory | Reasonable depth; some analysis; satisfactory understanding. |
| 45-59 | Weak | Limited critical discussion; low-level analysis; limited understanding. |
| 30-44 | Poor | Very little critical discussion; superficial understanding. |
| 0-29 | Very Poor | No analysis; no understanding. |

---

## Your Review Deliverable (required format)

Please produce, in this order:

### 1. Per-dimension scores
For each of the three dimensions:
- **Score (0-100)**
- **Descriptor band**
- **Official examiner comment** (2-4 sentences, as on the real marking sheet — honest, specific, referencing sections by number)

### 2. Weighted total & UoG grade band
- Show the arithmetic: `(P×1 + S×1 + T×5) / 7 = …`
- Assign grade band (A1-H)
- **Verdict** (one of): `EXCELLENT READY FOR SUBMISSION` / `VERY GOOD MINOR REVISIONS` / `GOOD MODERATE REVISIONS` / `SATISFACTORY MAJOR REVISIONS` / `WEAK — NOT READY`

### 3. Weaknesses with minimum fixes (ranked by severity)
For each weakness:
- Identifier: `W-1` [dim: P/S/T] — one-sentence statement
- Evidence: concrete quote or section reference
- Why it hurts the score: what marking-band criterion it violates
- Minimum fix: smallest-effort edit that would close it
- Estimated effort: S / M / L / XL

### 4. Brutally honest verdict
One paragraph: can this report realistically reach **B2/B1** with the remaining 2 rounds of revision, or is it capped at B3? State your reasoning. Name at most 3 fixes that would meaningfully move the needle.

### 5. Style / prose / figure critique (optional, concise)
Short paragraph on writing quality, figure usage, caption tone, if any still need tightening.

---

## Notes on what the author cares about

- **Honesty over niceness.** Previous examiner was criticised for inflating scores — don't repeat that. If the report is only borderline B3, say so; if it's actually B2-worthy, say that too.
- **Dimension 3 dominates.** It carries 5× weight, so the final grade is mostly determined by technical depth.
- **Internal consistency** in Probe (a) (support-recall bookkeeping) across §3.4 / Table `supportrecall` / Appendix C was a known issue through R1-R3; please verify whether it's now fully unified.
- **Learned-head retraining variance, prior-art baseline reproduction, and MSML/real-UWA validation** are known deferred items; flag if they continue to cap the Technical score.
- **BEng format constraints**: body should be 30-40 pages, 1.5 line spacing, 20-80 refs, ≤20 figures.

Please use **xhigh reasoning** and produce the full deliverable in one response. Thank you.
